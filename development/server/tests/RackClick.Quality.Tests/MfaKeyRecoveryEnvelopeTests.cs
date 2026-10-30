using System.Buffers.Binary;
using System.Security.Cryptography;
using System.Text;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

// Codec del sobre RCKEY v1 (MFA-L2d) en memoria: payload sintético, contraseña de laboratorio y sin archivos. Los rechazos
// de tamaño, cabecera y contraseña se verifican con un contador de derivaciones: deben quedar en cero antes de PBKDF2.
// El coste real del perfil de 600.000 iteraciones se lee en la duración de cada prueba en esta máquina.
public sealed class MfaKeyRecoveryEnvelopeTests
{
    private const string Password = "clave-de-prueba-larga";
    private const string PayloadText = "payload sintético de prueba: anillo de ejemplo 0123456789";
    private static readonly byte[] Payload = Encoding.UTF8.GetBytes(PayloadText);
    private static readonly Lazy<byte[]> SealedEnvelope = new(() => MfaKeyRecoveryEnvelope.Seal(Password, Payload));

    [Fact]
    public void RoundTripRestoresTheSyntheticPayloadAndWritesTheProfileHeader()
    {
        var envelope = MfaKeyRecoveryEnvelope.Seal(Password, Payload);
        var opened = MfaKeyRecoveryEnvelope.Open(Password, envelope);
        try
        {
            Assert.Equal(Payload, opened);
            Assert.Equal(59 + Payload.Length, envelope.Length);
            Assert.Equal("RCKEY"u8.ToArray(), envelope.AsSpan(0, 5).ToArray());
            Assert.Equal(new byte[] { 1, 1, 1 }, envelope.AsSpan(5, 3).ToArray());
            Assert.Equal(new byte[] { 0x00, 0x09, 0x27, 0xC0 }, envelope.AsSpan(8, 4).ToArray());
            Assert.Equal(new byte[] { 16 }, envelope.AsSpan(12, 1).ToArray());
            Assert.Equal(new byte[] { 12 }, envelope.AsSpan(29, 1).ToArray());
            Assert.Equal(new byte[] { 16 }, envelope.AsSpan(42, 1).ToArray());
        }
        finally
        {
            CryptographicOperations.ZeroMemory(opened);
        }
    }

    [Fact]
    public void TwoSealsOfTheSamePayloadDifferInSaltNonceAndCiphertext()
    {
        var first = MfaKeyRecoveryEnvelope.Seal(Password, Payload);
        var second = MfaKeyRecoveryEnvelope.Seal(Password, Payload);

        Assert.NotEqual(first.AsSpan(13, 16).ToArray(), second.AsSpan(13, 16).ToArray());
        Assert.NotEqual(first.AsSpan(30, 12).ToArray(), second.AsSpan(30, 12).ToArray());
        Assert.NotEqual(first.AsSpan(59).ToArray(), second.AsSpan(59).ToArray());
    }

    [Fact]
    public void WrongPasswordIsRejectedWithoutEchoingThePasswordOrThePayload()
    {
        const string wrong = "clave-de-prueba-erronea";
        var derivations = new Derivations();

        var error = Assert.Throws<MfaRecoveryEnvelopeException>(() =>
            MfaKeyRecoveryEnvelope.Open(wrong, Copy(SealedEnvelope.Value), derivations.Hit));

        Assert.Equal(MfaRecoveryEnvelopeErrorKind.AuthenticationFailed, error.Kind);
        Assert.Equal(1, derivations.Count);
        Assert.DoesNotContain(wrong, error.Message, StringComparison.Ordinal);
        Assert.DoesNotContain(PayloadText, error.Message, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("magia")]
    [InlineData("version")]
    [InlineData("kdf")]
    [InlineData("aead")]
    [InlineData("iteraciones")]
    [InlineData("longitud-sal")]
    [InlineData("longitud-nonce")]
    [InlineData("longitud-etiqueta")]
    public void HeaderOutsideTheProfileIsRejectedBeforeDerivation(string field)
    {
        var envelope = Copy(SealedEnvelope.Value);
        switch (field)
        {
            case "magia": envelope[0] = (byte)'X'; break;
            case "version": envelope[5] = 2; break;
            case "kdf": envelope[6] = 2; break;
            case "aead": envelope[7] = 2; break;
            case "iteraciones": BinaryPrimitives.WriteUInt32BigEndian(envelope.AsSpan(8, 4), 600_001); break;
            case "longitud-sal": envelope[12] = 15; break;
            case "longitud-nonce": envelope[29] = 13; break;
            case "longitud-etiqueta": envelope[42] = 15; break;
            default: throw new ArgumentOutOfRangeException(nameof(field), field, null);
        }
        var derivations = new Derivations();

        var error = Assert.Throws<MfaRecoveryEnvelopeException>(() => MfaKeyRecoveryEnvelope.Open(Password, envelope, derivations.Hit));

        var expected = field switch
        {
            "version" => MfaRecoveryEnvelopeErrorKind.UnsupportedVersion,
            "kdf" or "aead" => MfaRecoveryEnvelopeErrorKind.UnsupportedAlgorithm,
            "iteraciones" => MfaRecoveryEnvelopeErrorKind.UnsupportedParameters,
            _ => MfaRecoveryEnvelopeErrorKind.InvalidFormat,
        };
        Assert.Equal(expected, error.Kind);
        Assert.Equal(0, derivations.Count);
    }

    [Theory]
    [InlineData("sal")]
    [InlineData("nonce")]
    [InlineData("etiqueta")]
    [InlineData("ciphertext")]
    [InlineData("truncado")]
    public void SaltNonceTagCiphertextOrTruncationFailAuthenticationAfterOneDerivation(string field)
    {
        var envelope = Copy(SealedEnvelope.Value);
        var tampered = field switch
        {
            "sal" => Flip(envelope, 13),
            "nonce" => Flip(envelope, 30),
            "etiqueta" => Flip(envelope, 43),
            "ciphertext" => Flip(envelope, 59),
            "truncado" => envelope.AsSpan(0, envelope.Length - 1).ToArray(),
            _ => throw new ArgumentOutOfRangeException(nameof(field), field, null),
        };
        var derivations = new Derivations();

        var error = Assert.Throws<MfaRecoveryEnvelopeException>(() => MfaKeyRecoveryEnvelope.Open(Password, tampered, derivations.Hit));

        Assert.Equal(MfaRecoveryEnvelopeErrorKind.AuthenticationFailed, error.Kind);
        Assert.Equal(1, derivations.Count);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(58)]
    [InlineData(59)]
    public void EnvelopesWithoutPayloadAreRejectedBeforeDerivation(int length)
    {
        var derivations = new Derivations();
        var truncated = SealedEnvelope.Value.AsSpan(0, length).ToArray();

        var error = Assert.Throws<MfaRecoveryEnvelopeException>(() => MfaKeyRecoveryEnvelope.Open(Password, truncated, derivations.Hit));

        Assert.Equal(MfaRecoveryEnvelopeErrorKind.InvalidFormat, error.Kind);
        Assert.Equal(0, derivations.Count);
    }

    [Fact]
    public void OversizedEnvelopeIsRejectedBeforeDerivation()
    {
        var derivations = new Derivations();
        var oversized = new byte[MfaKeyRecoveryEnvelope.MaxEnvelopeBytes + 1];

        var error = Assert.Throws<MfaRecoveryEnvelopeException>(() => MfaKeyRecoveryEnvelope.Open(Password, oversized, derivations.Hit));

        Assert.Equal(MfaRecoveryEnvelopeErrorKind.TooLarge, error.Kind);
        Assert.Equal(0, derivations.Count);
    }

    [Fact]
    public void OversizedOrEmptyPayloadIsRejectedBeforeDerivation()
    {
        var derivations = new Derivations();
        var tooLarge = new byte[MfaKeyRecoveryEnvelope.MaxEnvelopeBytes - 59 + 1];

        var oversized = Assert.Throws<MfaRecoveryEnvelopeException>(() => MfaKeyRecoveryEnvelope.Seal(Password, tooLarge, derivations.Hit));
        var empty = Assert.Throws<MfaRecoveryEnvelopeException>(() => MfaKeyRecoveryEnvelope.Seal(Password, Array.Empty<byte>(), derivations.Hit));

        Assert.Equal(MfaRecoveryEnvelopeErrorKind.InvalidRequest, oversized.Kind);
        Assert.Equal(MfaRecoveryEnvelopeErrorKind.InvalidRequest, empty.Kind);
        Assert.Equal(0, derivations.Count);
    }

    [Fact]
    public void MaximalPayloadRoundTripsWithinTheEnvelopeLimit()
    {
        var payload = new byte[MfaKeyRecoveryEnvelope.MaxEnvelopeBytes - 59];
        RandomNumberGenerator.Fill(payload);
        var envelope = MfaKeyRecoveryEnvelope.Seal(Password, payload);
        var opened = MfaKeyRecoveryEnvelope.Open(Password, envelope);
        try
        {
            Assert.Equal(MfaKeyRecoveryEnvelope.MaxEnvelopeBytes, envelope.Length);
            Assert.Equal(payload, opened);
        }
        finally
        {
            CryptographicOperations.ZeroMemory(opened);
        }
    }

    [Fact]
    public void PasswordOutsideTheCharacterBoundsIsRejectedBeforeDerivation()
    {
        var derivations = new Derivations();
        var eleven = new string('a', 11);
        var twoFiftySeven = new string('a', 257);
        var loneSurrogate = "contraseña" + "\uD800" + "xyz";

        foreach (var candidate in new[] { eleven, twoFiftySeven, loneSurrogate })
        {
            var error = Assert.Throws<MfaRecoveryEnvelopeException>(() => MfaKeyRecoveryEnvelope.Seal(candidate, Payload, derivations.Hit));
            Assert.Equal(MfaRecoveryEnvelopeErrorKind.InvalidRequest, error.Kind);
        }
        var openError = Assert.Throws<MfaRecoveryEnvelopeException>(() => MfaKeyRecoveryEnvelope.Open(eleven, SealedEnvelope.Value, derivations.Hit));

        Assert.Equal(MfaRecoveryEnvelopeErrorKind.InvalidRequest, openError.Kind);
        Assert.Equal(0, derivations.Count);
    }

    [Fact]
    public void PasswordBoundariesOfTwelveAndTwoHundredFiftySixCharactersAreAccepted()
    {
        var twelve = new string('k', 12);
        var twelveEnvelope = MfaKeyRecoveryEnvelope.Seal(twelve, Payload);
        var opened = MfaKeyRecoveryEnvelope.Open(twelve, twelveEnvelope);
        try
        {
            Assert.Equal(Payload, opened);
        }
        finally
        {
            CryptographicOperations.ZeroMemory(opened);
        }

        var twoFiftySix = new string('m', 256);
        var longEnvelope = MfaKeyRecoveryEnvelope.Seal(twoFiftySix, Payload);
        Assert.Equal(59 + Payload.Length, longEnvelope.Length);
    }

    [Fact]
    public void PasswordIsEncodedWithoutNormalization()
    {
        const string composed = "contraseña-de-recuperación";
        var decomposed = composed.Normalize(NormalizationForm.FormD);
        Assert.NotEqual(composed, decomposed);
        var envelope = MfaKeyRecoveryEnvelope.Seal(composed, Payload);

        var error = Assert.Throws<MfaRecoveryEnvelopeException>(() => MfaKeyRecoveryEnvelope.Open(decomposed, envelope));

        Assert.Equal(MfaRecoveryEnvelopeErrorKind.AuthenticationFailed, error.Kind);
    }

    private static byte[] Copy(byte[] envelope) => (byte[])envelope.Clone();

    private static byte[] Flip(byte[] envelope, int index)
    {
        var copy = Copy(envelope);
        copy[index] ^= 0x01;
        return copy;
    }

    // Contador de derivaciones: el punto de ensayo se invoca justo antes de PBKDF2.
    private sealed class Derivations
    {
        public int Count { get; private set; }

        public void Hit() => Count++;
    }
}
