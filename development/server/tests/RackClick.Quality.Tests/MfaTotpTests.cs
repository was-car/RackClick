using System.Text;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

public sealed class MfaTotpTests
{
    // Clave de prueba de RFC 6238 (SHA-1, ASCII "12345678901234567890"). Los valores son los seis últimos dígitos de los vectores de la RFC.
    private static readonly byte[] Rfc6238Secret = Encoding.ASCII.GetBytes("12345678901234567890");

    [Theory]
    [InlineData(59, "287082")]
    [InlineData(1111111109, "081804")]
    [InlineData(1111111111, "050471")]
    [InlineData(1234567890, "005924")]
    [InlineData(2000000000, "279037")]
    [InlineData(20000000000, "353130")]
    public void ComputeMatchesRfc6238Sha1Vectors(long unixSeconds, string expected)
    {
        var at = DateTimeOffset.FromUnixTimeSeconds(unixSeconds);

        Assert.Equal(expected, MfaTotp.Compute(Rfc6238Secret, at));
    }

    [Fact]
    public void VerifyAcceptsCurrentStepAndRecordsIt()
    {
        var now = DateTimeOffset.FromUnixTimeSeconds(1111111111);
        var code = MfaTotp.Compute(Rfc6238Secret, now);

        var accepted = MfaTotp.TryVerify(Rfc6238Secret, code, now, lastConsumedStep: -1, out long step);

        Assert.True(accepted);
        Assert.Equal(1111111111L / MfaTotp.StepSeconds, step);
    }

    [Fact]
    public void VerifyRejectsReplayOfAlreadyConsumedStep()
    {
        var now = DateTimeOffset.FromUnixTimeSeconds(1111111111);
        var code = MfaTotp.Compute(Rfc6238Secret, now);
        Assert.True(MfaTotp.TryVerify(Rfc6238Secret, code, now, -1, out long consumed));

        var replayed = MfaTotp.TryVerify(Rfc6238Secret, code, now, consumed, out _);

        Assert.False(replayed);
    }

    [Fact]
    public void VerifyAcceptsPreviousStepInsideWindowButNotTwoStepsBack()
    {
        var now = DateTimeOffset.FromUnixTimeSeconds(1111111111);
        var previous = MfaTotp.Compute(Rfc6238Secret, now.AddSeconds(-MfaTotp.StepSeconds));
        var twoBack = MfaTotp.Compute(Rfc6238Secret, now.AddSeconds(-2 * MfaTotp.StepSeconds));

        Assert.True(MfaTotp.TryVerify(Rfc6238Secret, previous, now, -1, out _));
        Assert.False(MfaTotp.TryVerify(Rfc6238Secret, twoBack, now, -1, out _));
    }

    [Theory]
    [InlineData("")]
    [InlineData("12345")]
    [InlineData("1234567")]
    [InlineData("12345a")]
    [InlineData("12 456")]
    public void VerifyRejectsMalformedCodes(string code)
    {
        var now = DateTimeOffset.FromUnixTimeSeconds(1111111111);

        Assert.False(MfaTotp.TryVerify(Rfc6238Secret, code, now, -1, out _));
    }

    [Fact]
    public void VerifyRejectsSecretOfWrongLength()
    {
        var now = DateTimeOffset.FromUnixTimeSeconds(1111111111);
        var code = MfaTotp.Compute(Rfc6238Secret, now);

        Assert.False(MfaTotp.TryVerify(new byte[19], code, now, -1, out _));
    }

    [Fact]
    public void NewSecretHasExpectedLengthAndVariesBetweenCalls()
    {
        var first = MfaTotp.NewSecret();
        var second = MfaTotp.NewSecret();

        Assert.Equal(MfaTotp.SecretBytes, first.Length);
        Assert.NotEqual(first, second);
    }
}
