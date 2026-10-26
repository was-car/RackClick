using System.Security.Cryptography;
using OtpNet;

namespace RackClick.Server;

// TOTP de RFC 6238: 6 dígitos, SHA-1 y paso de 30 s, con una ventana de ±1 paso.
// Un paso ya consumido se rechaza para impedir repetir el mismo código.
// Política de MFA, desafíos y sesiones viven fuera de esta clase (M3).
public static class MfaTotp
{
    public const int SecretBytes = 20;
    public const int Digits = 6;
    public const int StepSeconds = 30;

    public static byte[] NewSecret() => RandomNumberGenerator.GetBytes(SecretBytes);

    public static string Compute(byte[] secret, DateTimeOffset utcAt) => Create(secret).ComputeTotp(utcAt.UtcDateTime);

    public static bool TryVerify(byte[] secret, string code, DateTimeOffset utcNow, long lastConsumedStep, out long matchedStep)
    {
        matchedStep = -1;
        if (secret.Length != SecretBytes || code is null || code.Length != Digits || !code.All(char.IsAsciiDigit))
        {
            return false;
        }

        if (!Create(secret).VerifyTotp(utcNow.UtcDateTime, code, out long step, new VerificationWindow(previous: 1, future: 1)))
        {
            return false;
        }

        if (step <= lastConsumedStep)
        {
            return false;
        }

        matchedStep = step;
        return true;
    }

    private static Totp Create(byte[] secret) => new(secret, step: StepSeconds, mode: OtpHashMode.Sha1, totpSize: Digits);
}
