using System.Buffers.Binary;
using System.Security.Cryptography;
using System.Text;

namespace RackClick.Server;

// Sobre portable de recuperación RCKEY v1 (MFA, D2 v2 §4). Codec en memoria para un payload opaco: cifra con una clave derivada
// de la contraseña de recuperación y descifra. No guarda archivos, no exporta el almacén real y no conoce el anillo.
// Investigación previa: evidence/s1-20261026/mfa-l2d-claude/INVESTIGACION-PREVIA.md.
//
// Formato (bytes): magia "RCKEY" (0-4); versión 1 (5); KDF 1 = PBKDF2-HMAC-SHA256 (6); AEAD 1 = AES-256-GCM (7); iteraciones
// uint32 big-endian, sólo 600000 (8-11); longitud de la sal, 16 (12); sal (13-28); longitud del nonce, 12 (29); nonce (30-41);
// longitud de la etiqueta, 16 (42); etiqueta (43-58); ciphertext hasta el final (59..., mínimo 1 byte).
// La longitud del ciphertext se deduce del tamaño del contenedor: no hay campo de longitud ni contenido extra posible.
// AAD = bytes 0-42: autentica magia, versión, algoritmos, iteraciones, sal, nonce y longitudes (no la etiqueta).
//
// Límites: sobre de hasta 1 MiB; payload de 1 a 1 MiB menos la cabecera; contraseña de 12 a 256 caracteres (puntos de código
// Unicode), UTF-8 sin normalización. Todo rechazo de tamaño, cabecera o contraseña ocurre antes de PBKDF2.
//
// Contrato: Open devuelve el texto claro en un arreglo nuevo. El llamador debe ponerlo a cero tras usarlo.
// Límite: la contraseña recibida como string no puede borrarse de la memoria administrada; sólo se ponen a cero las copias en bytes.
internal static class MfaKeyRecoveryEnvelope
{
    public const int MaxEnvelopeBytes = 1024 * 1024;
    public const int Iterations = 600_000;
    public const int MinPasswordCharacters = 12;
    public const int MaxPasswordCharacters = 256;

    private const int MagicLength = 5;
    private const int SaltBytes = 16;
    private const int NonceBytes = 12;
    private const int TagBytes = 16;
    private const int KeyBytes = 32;
    private const byte FormatVersion = 1;
    private const byte KdfPbkdf2Sha256 = 1;
    private const byte AeadAes256Gcm = 1;

    private const int VersionOffset = 5;
    private const int KdfOffset = 6;
    private const int AeadOffset = 7;
    private const int IterationsOffset = 8;
    private const int SaltLengthOffset = 12;
    private const int SaltOffset = 13;
    private const int NonceLengthOffset = 29;
    private const int NonceOffset = 30;
    private const int TagLengthOffset = 42;
    private const int TagOffset = 43;
    private const int HeaderBytes = 59;
    private const int AadBytes = 43;
    private const int MaxPayloadBytes = MaxEnvelopeBytes - HeaderBytes;

    private static readonly UTF8Encoding StrictUtf8 = new(false, true);

    private static ReadOnlySpan<byte> Magic => "RCKEY"u8;

    // Sella un payload no vacío con la contraseña. Devuelve el sobre completo.
    public static byte[] Seal(string password, byte[] payload) => Seal(password, payload, onDerive: null);

    // onDerive: punto de ensayo interno, llamado justo antes de PBKDF2. Las pruebas lo usan para verificar que un rechazo no deriva.
    internal static byte[] Seal(string password, byte[] payload, Action? onDerive)
    {
        if (payload is null || payload.Length is < 1 or > MaxPayloadBytes)
            throw Error(MfaRecoveryEnvelopeErrorKind.InvalidRequest, "payload fuera de los límites del sobre");
        var passwordBytes = PasswordBytes(password);
        try
        {
            var salt = RandomNumberGenerator.GetBytes(SaltBytes);
            var nonce = RandomNumberGenerator.GetBytes(NonceBytes);
            var envelope = new byte[HeaderBytes + payload.Length];
            WriteHeader(envelope, salt, nonce);
            var key = Derive(passwordBytes, salt, onDerive);
            try
            {
                using var aes = new AesGcm(key, TagBytes);
                aes.Encrypt(nonce, payload, envelope.AsSpan(HeaderBytes), envelope.AsSpan(TagOffset, TagBytes), envelope.AsSpan(0, AadBytes));
                return envelope;
            }
            finally
            {
                CryptographicOperations.ZeroMemory(key);
            }
        }
        finally
        {
            CryptographicOperations.ZeroMemory(passwordBytes);
        }
    }

    // Abre un sobre. El texto claro devuelto es responsabilidad del llamador: debe ponerlo a cero tras usarlo.
    public static byte[] Open(string password, byte[] envelope) => Open(password, envelope, onDerive: null);

    internal static byte[] Open(string password, byte[] envelope, Action? onDerive)
    {
        if (envelope is null) throw Error(MfaRecoveryEnvelopeErrorKind.InvalidRequest, "sobre ausente");
        if (envelope.Length > MaxEnvelopeBytes)
            throw Error(MfaRecoveryEnvelopeErrorKind.TooLarge, "el sobre supera el límite de 1 MiB");
        if (envelope.Length <= HeaderBytes)
            throw Error(MfaRecoveryEnvelopeErrorKind.InvalidFormat, "sobre truncado o sin payload");
        RequireHeader(envelope);
        var passwordBytes = PasswordBytes(password);
        try
        {
            var salt = envelope.AsSpan(SaltOffset, SaltBytes).ToArray();
            var nonce = envelope.AsSpan(NonceOffset, NonceBytes).ToArray();
            var key = Derive(passwordBytes, salt, onDerive);
            var plaintext = new byte[envelope.Length - HeaderBytes];
            try
            {
                using var aes = new AesGcm(key, TagBytes);
                aes.Decrypt(nonce, envelope.AsSpan(HeaderBytes), envelope.AsSpan(TagOffset, TagBytes), plaintext, envelope.AsSpan(0, AadBytes));
                return plaintext;
            }
            catch (CryptographicException)
            {
                CryptographicOperations.ZeroMemory(plaintext);
                throw Error(MfaRecoveryEnvelopeErrorKind.AuthenticationFailed, "contraseña incorrecta o sobre alterado");
            }
            catch (Exception)
            {
                CryptographicOperations.ZeroMemory(plaintext);
                throw;
            }
            finally
            {
                CryptographicOperations.ZeroMemory(key);
            }
        }
        finally
        {
            CryptographicOperations.ZeroMemory(passwordBytes);
        }
    }

    private static void RequireHeader(byte[] envelope)
    {
        if (!envelope.AsSpan(0, MagicLength).SequenceEqual(Magic))
            throw Error(MfaRecoveryEnvelopeErrorKind.InvalidFormat, "magia RCKEY no válida");
        if (envelope[VersionOffset] != FormatVersion)
            throw Error(MfaRecoveryEnvelopeErrorKind.UnsupportedVersion, "versión de formato no soportada");
        if (envelope[KdfOffset] != KdfPbkdf2Sha256)
            throw Error(MfaRecoveryEnvelopeErrorKind.UnsupportedAlgorithm, "KDF no soportado");
        if (envelope[AeadOffset] != AeadAes256Gcm)
            throw Error(MfaRecoveryEnvelopeErrorKind.UnsupportedAlgorithm, "AEAD no soportado");
        if (BinaryPrimitives.ReadUInt32BigEndian(envelope.AsSpan(IterationsOffset, 4)) != (uint)Iterations)
            throw Error(MfaRecoveryEnvelopeErrorKind.UnsupportedParameters, "iteraciones fuera del perfil v1");
        if (envelope[SaltLengthOffset] != SaltBytes || envelope[NonceLengthOffset] != NonceBytes || envelope[TagLengthOffset] != TagBytes)
            throw Error(MfaRecoveryEnvelopeErrorKind.InvalidFormat, "longitudes fuera del perfil v1");
    }

    private static void WriteHeader(byte[] envelope, byte[] salt, byte[] nonce)
    {
        Magic.CopyTo(envelope);
        envelope[VersionOffset] = FormatVersion;
        envelope[KdfOffset] = KdfPbkdf2Sha256;
        envelope[AeadOffset] = AeadAes256Gcm;
        BinaryPrimitives.WriteUInt32BigEndian(envelope.AsSpan(IterationsOffset, 4), (uint)Iterations);
        envelope[SaltLengthOffset] = SaltBytes;
        salt.CopyTo(envelope, SaltOffset);
        envelope[NonceLengthOffset] = NonceBytes;
        nonce.CopyTo(envelope, NonceOffset);
        envelope[TagLengthOffset] = TagBytes;
    }

    // La cuenta de caracteres se hace antes de codificar. No hay normalización: la contraseña se usa tal cual llega.
    private static byte[] PasswordBytes(string password)
    {
        if (password is null) throw Error(MfaRecoveryEnvelopeErrorKind.InvalidRequest, "contraseña ausente");
        var characters = password.EnumerateRunes().Count();
        if (characters is < MinPasswordCharacters or > MaxPasswordCharacters)
            throw Error(MfaRecoveryEnvelopeErrorKind.InvalidRequest, "la contraseña debe tener entre 12 y 256 caracteres");
        try
        {
            return StrictUtf8.GetBytes(password);
        }
        catch (EncoderFallbackException)
        {
            throw Error(MfaRecoveryEnvelopeErrorKind.InvalidRequest, "la contraseña contiene caracteres no válidos");
        }
    }

    private static byte[] Derive(byte[] passwordBytes, byte[] salt, Action? onDerive)
    {
        onDerive?.Invoke();
        return Rfc2898DeriveBytes.Pbkdf2(passwordBytes, salt, Iterations, HashAlgorithmName.SHA256, KeyBytes);
    }

    private static MfaRecoveryEnvelopeException Error(MfaRecoveryEnvelopeErrorKind kind, string detail) =>
        new(kind, "mfa_recovery_envelope: " + detail);
}

internal enum MfaRecoveryEnvelopeErrorKind
{
    InvalidRequest,
    TooLarge,
    InvalidFormat,
    UnsupportedVersion,
    UnsupportedAlgorithm,
    UnsupportedParameters,
    AuthenticationFailed,
}

// El mensaje describe el fallo. Nunca contiene la contraseña, el payload ni claves.
internal sealed class MfaRecoveryEnvelopeException(MfaRecoveryEnvelopeErrorKind kind, string message) : Exception(message)
{
    public MfaRecoveryEnvelopeErrorKind Kind { get; } = kind;
}
