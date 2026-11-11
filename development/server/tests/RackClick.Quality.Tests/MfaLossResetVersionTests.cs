using System.Reflection;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

public sealed class MfaLossResetVersionTests
{
    [Theory]
    [InlineData(new[] { 1, 7, 40 }, 3, 41)]
    [InlineData(new[] { 999999 }, 0, 1000000)]
    [InlineData(new[] { 4, 4, 2 }, 63, 5)]
    public void NewVersionExceedsEveryKnownSourceWithoutReusingOne(int[] versions, int retained, int expected)
        => Assert.Equal(expected, Invoke(versions, true, retained));

    [Theory]
    [InlineData(new int[0], true, 0)]
    [InlineData(new[] { 7 }, false, 0)]
    [InlineData(new[] { 0, 7 }, true, 0)]
    [InlineData(new[] { 1000000 }, true, 0)]
    [InlineData(new[] { 7 }, true, 64)]
    [InlineData(new[] { 7 }, true, -1)]
    public void UnknownHistoryOrExhaustedProfileCannotCreateVersionOne(int[] versions, bool complete, int retained)
    {
        var error = Assert.Throws<TargetInvocationException>(() => Invoke(versions, complete, retained));
        Assert.IsType<MfaMaintenanceException>(error.InnerException);
    }

    private static int Invoke(int[] versions, bool complete, int retained)
    {
        var type = typeof(MfaKeyRing).Assembly.GetType("RackClick.Server.MfaLossResetDatabase", throwOnError: true)!;
        return (int)type.GetMethod("NextVersion", BindingFlags.NonPublic | BindingFlags.Static)!
            .Invoke(null, [versions, complete, retained])!;
    }
}
