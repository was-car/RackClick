using System.Security.Cryptography;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

public sealed class MfaSecretCipherTests
{
    private static readonly Guid Installation = Guid.Parse("11111111-1111-4111-8111-111111111111");
    private static readonly Guid UserA = Guid.Parse("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");
    private static readonly Guid UserB = Guid.Parse("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb");

    [Fact]
    public void RoundTripRecoversSecretForSameContext()
    {
        var key = RandomNumberGenerator.GetBytes(MfaSecretCipher.KeyBytes);
        var secret = MfaTotp.NewSecret();

        var sealedSecret = MfaSecretCipher.Seal(key, 1, secret, Installation, UserA);
        var opened = MfaSecretCipher.Open(key, 1, sealedSecret, Installation, UserA);

        Assert.Equal(secret, opened);
    }

    [Fact]
    public void SameSecretSealsDifferentlyEachTime()
    {
        var key = RandomNumberGenerator.GetBytes(MfaSecretCipher.KeyBytes);
        var secret = MfaTotp.NewSecret();

        var first = MfaSecretCipher.Seal(key, 1, secret, Installation, UserA);
        var second = MfaSecretCipher.Seal(key, 1, secret, Installation, UserA);

        Assert.NotEqual(first, second);
    }

    [Fact]
    public void OpenFailsForAnotherUser()
    {
        var key = RandomNumberGenerator.GetBytes(MfaSecretCipher.KeyBytes);
        var sealedSecret = MfaSecretCipher.Seal(key, 1, MfaTotp.NewSecret(), Installation, UserA);

        Assert.Throws<AuthenticationTagMismatchException>(() => MfaSecretCipher.Open(key, 1, sealedSecret, Installation, UserB));
    }

    [Fact]
    public void OpenFailsForAnotherKeyVersion()
    {
        var key = RandomNumberGenerator.GetBytes(MfaSecretCipher.KeyBytes);
        var sealedSecret = MfaSecretCipher.Seal(key, 1, MfaTotp.NewSecret(), Installation, UserA);

        Assert.Throws<AuthenticationTagMismatchException>(() => MfaSecretCipher.Open(key, 2, sealedSecret, Installation, UserA));
    }

    [Fact]
    public void OpenFailsForAnotherInstallation()
    {
        var key = RandomNumberGenerator.GetBytes(MfaSecretCipher.KeyBytes);
        var sealedSecret = MfaSecretCipher.Seal(key, 1, MfaTotp.NewSecret(), Installation, UserA);

        Assert.Throws<AuthenticationTagMismatchException>(() => MfaSecretCipher.Open(key, 1, sealedSecret, Guid.NewGuid(), UserA));
    }

    [Fact]
    public void OpenFailsForTamperedCiphertext()
    {
        var key = RandomNumberGenerator.GetBytes(MfaSecretCipher.KeyBytes);
        var sealedSecret = MfaSecretCipher.Seal(key, 1, MfaTotp.NewSecret(), Installation, UserA);
        sealedSecret[^1] ^= 0x01;

        Assert.Throws<AuthenticationTagMismatchException>(() => MfaSecretCipher.Open(key, 1, sealedSecret, Installation, UserA));
    }

    [Fact]
    public void OpenFailsForTruncatedInput()
    {
        var key = RandomNumberGenerator.GetBytes(MfaSecretCipher.KeyBytes);

        var error = Assert.Throws<CryptographicException>(() => MfaSecretCipher.Open(key, 1, new byte[20], Installation, UserA));
        Assert.Equal("mfa_secret_invalid", error.Message);
    }

    [Theory]
    [InlineData(16)]
    [InlineData(31)]
    [InlineData(33)]
    public void RejectsKeysThatAreNotAes256(int length)
    {
        var key = new byte[length];

        Assert.Throws<ArgumentException>(() => MfaSecretCipher.Seal(key, 1, MfaTotp.NewSecret(), Installation, UserA));
    }
}
