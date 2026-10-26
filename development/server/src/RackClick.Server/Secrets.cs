using System.Security.Cryptography;
using System.Text;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Options;

namespace RackClick.Server;

public static class Secrets
{
    private static readonly PasswordHasher<string> Hasher = new(Options.Create(new PasswordHasherOptions
    {
        IterationCount = 210_000
    }));
    private static readonly string Dummy = Hasher.HashPassword("", Token());
    public static string Token() => Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
    public static string Digest(string raw) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(raw)));
    public static string Csrf(string sessionToken) => Convert.ToHexString(HMACSHA256.HashData(
        Encoding.ASCII.GetBytes(sessionToken), Encoding.ASCII.GetBytes("RackClick/CSRF/v1")));
    public static string PasswordHash(string username, string password) => Hasher.HashPassword(username, password);
    public static bool PasswordValid(string username, string? hash, string password)
    {
        var result = Hasher.VerifyHashedPassword(username, hash ?? Dummy, password);
        return hash is not null && result != PasswordVerificationResult.Failed;
    }
    public static bool Matches(string raw, string storedDigest)
    {
        var digest = Encoding.ASCII.GetBytes(Digest(raw));
        return CryptographicOperations.FixedTimeEquals(digest, Encoding.ASCII.GetBytes(storedDigest));
    }
}
