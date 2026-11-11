using System.Reflection;
using System.Runtime.Versioning;
using System.Security.Claims;
using System.Security.Principal;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

public sealed class MfaEmergencyAuthorizationTests
{
    public static IEnumerable<object?[]> TokenCases()
    {
        for (int mask = 0; mask < 64; mask++)
        {
            bool windows = (mask & 1) != 0, impersonated = (mask & 2) != 0, system = (mask & 4) != 0;
            bool admin = (mask & 8) != 0, readable = (mask & 16) != 0, elevated = (mask & 32) != 0;
            string? expected = !windows ? "mfa_emergency_not_windows"
                : impersonated ? "mfa_emergency_impersonation_rejected"
                : system ? null : !admin ? "mfa_emergency_not_authorized"
                : !readable ? "mfa_emergency_token_unreadable"
                : !elevated ? "mfa_emergency_not_authorized" : null;
            yield return [windows, impersonated, system, admin, readable, elevated, expected];
        }
    }

    [Theory]
    [MemberData(nameof(TokenCases))]
    public void OnlyNativeSystemOrAnElevatedEnabledAdministratorCanPassThePolicy(
        bool windows, bool impersonated, bool system, bool admin, bool readable, bool elevated, string? expected)
    {
        Assert.Equal(expected, (string?)CommandType.GetMethod("DenialForToken", BindingFlags.NonPublic | BindingFlags.Static)!
            .Invoke(null, [windows, impersonated, system, admin, readable, elevated]));
    }

    [Fact]
    [SupportedOSPlatform("windows")]
    public void ClaimsCannotReplaceTheCurrentWindowsToken()
    {
        var before = Failure(); var principal = Thread.CurrentPrincipal;
        try
        {
            Thread.CurrentPrincipal = new ClaimsPrincipal(new ClaimsIdentity(
                [new(ClaimTypes.Role, "Administrators"), new(ClaimTypes.Role, "SYSTEM"),
                 new("security.manage", "global"), new("systemhaus.manage", "global")], "forged-application-principal"));
            Assert.Equal(before, Failure());
        }
        finally { Thread.CurrentPrincipal = principal; }
    }

    [Fact]
    [SupportedOSPlatform("windows")]
    public void RealSelfImpersonationIsDeniedAndTheOriginalIdentityIsRestored()
    {
        using var identity = WindowsIdentity.GetCurrent();
        var before = Failure(); var sid = identity.User!.Value;
        WindowsIdentity.RunImpersonated(identity.AccessToken, () => Assert.Equal("mfa_emergency_impersonation_rejected", Failure()));
        using var after = WindowsIdentity.GetCurrent();
        Assert.Equal(sid, after.User!.Value);
        Assert.Equal(before, Failure());
        using var impersonated = WindowsIdentity.GetCurrent(ifImpersonating: true);
        Assert.Null(impersonated);
    }

    private static Type CommandType => typeof(MfaKeyRing).Assembly.GetType("RackClick.Server.MfaEmergencyRecoveryCommand", throwOnError: true)!;
    private static string? Failure() => (string?)CommandType.GetMethod("AuthorizationFailure", BindingFlags.NonPublic | BindingFlags.Static)!.Invoke(null, null);
}
