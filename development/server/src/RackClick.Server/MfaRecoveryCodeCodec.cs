using System.Security.Cryptography;
using System.Text;

namespace RackClick.Server;

// Ten high-entropy recovery codes are independent of the TOTP encryption key.
// Stored values contain a version, random salt and account-bound hash only.
internal static class MfaRecoveryCodeCodec
{
    internal const int CodeCount = 10;

    internal static string NewCode()
    {
        byte[] random = RandomNumberGenerator.GetBytes(16);
        try
        {
            string hex = Convert.ToHexString(random);
            return string.Join("-", Enumerable.Range(0, 8).Select(index => hex.Substring(index * 4, 4)));
        }
        finally { CryptographicOperations.ZeroMemory(random); }
    }

    internal static string Hash(string code, Guid house, Guid user)
    {
        string normalized = Normalize(code) ?? throw new ArgumentException("Invalid recovery code format.", nameof(code));
        byte[] salt = RandomNumberGenerator.GetBytes(16);
        try
        {
            byte[] hash = Derive(normalized, salt, house, user);
            try { return "rck1$" + Convert.ToHexString(salt) + "$" + Convert.ToHexString(hash); }
            finally { CryptographicOperations.ZeroMemory(hash); }
        }
        finally { CryptographicOperations.ZeroMemory(salt); }
    }

    internal static bool Matches(string? code, string stored, Guid house, Guid user)
    {
        string? normalized = Normalize(code);
        if (normalized is null || stored.Length != 102) return false;
        string[] parts = stored.Split('$');
        if (parts.Length != 3 || parts[0] != "rck1" || parts[1].Length != 32 || parts[2].Length != 64) return false;
        byte[] salt, expected;
        try { salt = Convert.FromHexString(parts[1]); expected = Convert.FromHexString(parts[2]); }
        catch (FormatException) { return false; }
        try
        {
            byte[] actual = Derive(normalized, salt, house, user);
            try { return CryptographicOperations.FixedTimeEquals(actual, expected); }
            finally { CryptographicOperations.ZeroMemory(actual); }
        }
        finally { CryptographicOperations.ZeroMemory(salt); CryptographicOperations.ZeroMemory(expected); }
    }

    private static string? Normalize(string? code)
    {
        if (code is null || code.Length > 80) return null;
        string value = code.Trim().Replace("-", "", StringComparison.Ordinal).ToUpperInvariant();
        return value.Length == 32 && value.All(c => c is >= '0' and <= '9' or >= 'A' and <= 'F') ? value : null;
    }

    private static byte[] Derive(string normalized, byte[] salt, Guid house, Guid user)
    {
        byte[] input = Encoding.UTF8.GetBytes("RackClick-recovery-code-v1\0" + house.ToString("D") + "\0" + user.ToString("D") + "\0" + normalized);
        try
        {
            using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
            hash.AppendData(salt); hash.AppendData(input);
            return hash.GetHashAndReset();
        }
        finally { CryptographicOperations.ZeroMemory(input); }
    }
}
