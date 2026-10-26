using System.Security.Cryptography;
using System.Text;

namespace RackClick.Server;

// Cifra el secreto TOTP con AES-256-GCM. Formato: nonce (12) | etiqueta (16) | texto cifrado.
// El contexto autenticado (AAD) liga el secreto a su instalación, usuario y versión de clave:
// un secreto copiado a otro usuario o a otra versión no se descifra.
// La clave no entra aquí: su custodia está definida en docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md.
public static class MfaSecretCipher
{
    public const int KeyBytes = 32;
    private const int NonceBytes = 12;
    private const int TagBytes = 16;

    public static byte[] Seal(byte[] key, int keyVersion, byte[] secret, Guid systemhausId, Guid userId)
    {
        ArgumentNullException.ThrowIfNull(secret);
        RequireKey(key);
        var nonce = RandomNumberGenerator.GetBytes(NonceBytes);
        var cipher = new byte[secret.Length];
        var tag = new byte[TagBytes];
        using var aes = new AesGcm(key, TagBytes);
        aes.Encrypt(nonce, secret, cipher, tag, Aad(keyVersion, systemhausId, userId));

        var sealed_ = new byte[NonceBytes + TagBytes + cipher.Length];
        nonce.CopyTo(sealed_, 0);
        tag.CopyTo(sealed_, NonceBytes);
        cipher.CopyTo(sealed_, NonceBytes + TagBytes);
        return sealed_;
    }

    public static byte[] Open(byte[] key, int keyVersion, byte[] sealed_, Guid systemhausId, Guid userId)
    {
        ArgumentNullException.ThrowIfNull(sealed_);
        RequireKey(key);
        if (sealed_.Length < NonceBytes + TagBytes)
        {
            throw new CryptographicException("mfa_secret_invalid");
        }

        var nonce = sealed_.AsSpan(0, NonceBytes);
        var tag = sealed_.AsSpan(NonceBytes, TagBytes);
        var cipher = sealed_.AsSpan(NonceBytes + TagBytes);
        var secret = new byte[cipher.Length];
        using var aes = new AesGcm(key, TagBytes);
        aes.Decrypt(nonce, cipher, tag, secret, Aad(keyVersion, systemhausId, userId));
        return secret;
    }

    private static void RequireKey(byte[] key)
    {
        ArgumentNullException.ThrowIfNull(key);
        if (key.Length != KeyBytes)
        {
            throw new ArgumentException("mfa_key_length_invalid", nameof(key));
        }
    }

    private static byte[] Aad(int keyVersion, Guid systemhausId, Guid userId) =>
        Encoding.UTF8.GetBytes($"rackclick-mfa-v{keyVersion}|{systemhausId:D}|{userId:D}");
}
