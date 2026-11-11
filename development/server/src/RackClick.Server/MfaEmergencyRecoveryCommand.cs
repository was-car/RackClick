using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security;
using System.Security.Principal;
using System.Text.Json;
using Microsoft.Win32.SafeHandles;

namespace RackClick.Server;

// F-09.01 authority helper: no configuration, stdin, SQL, keys or web host.
// F-09.04 composes this native authority with the explicit local loss-reset protocol.
internal static class MfaEmergencyRecoveryCommand
{
    internal static int Run(TextWriter output)
    {
        string? denied = AuthorizationFailure();
        output.WriteLine(JsonSerializer.Serialize(new
        {
            status = "rejected",
            code = denied ?? "mfa_emergency_transition_unavailable",
            stage = denied is null ? "transition" : "authorization",
            operationsApplied = 0,
            sessionGranted = false
        }));
        // Authorization is not a recovery receipt, an application session or a completed operation.
        return 1;
    }

    internal static string? AuthorizationFailure()
    {
        if (!OperatingSystem.IsWindows()) return "mfa_emergency_not_windows";
        try { return WindowsAuthorityFailure(); }
        catch (Exception error) when (error is SecurityException or UnauthorizedAccessException or Win32Exception)
        { return "mfa_emergency_identity_unavailable"; }
    }

    [SupportedOSPlatform("windows")]
    private static string? WindowsAuthorityFailure()
    {
        using var impersonated = WindowsIdentity.GetCurrent(ifImpersonating: true);
        if (impersonated is not null) return "mfa_emergency_impersonation_rejected";
        using var processIdentity = WindowsIdentity.GetCurrent();
        bool system = processIdentity.User?.IsWellKnown(WellKnownSidType.LocalSystemSid) == true;
        if (system) return DenialForToken(true, false, true, false, false, false);
        bool administrator = new WindowsPrincipal(processIdentity).IsInRole(WindowsBuiltInRole.Administrator);
        if (!administrator) return DenialForToken(true, false, false, false, false, false);
        bool readable = GetTokenInformation(processIdentity.AccessToken, 20, out uint elevation, sizeof(uint), out uint returned)
            && returned == sizeof(uint);
        return DenialForToken(true, false, false, true, readable, elevation != 0);
    }

    // Pure policy seam for tests; never read from DI, JSON, claims or environment in the CLI.
    private static string? DenialForToken(bool windows, bool impersonated, bool system,
        bool administrator, bool elevationReadable, bool elevated)
    {
        if (!windows) return "mfa_emergency_not_windows";
        if (impersonated) return "mfa_emergency_impersonation_rejected";
        if (system) return null;
        if (!administrator) return "mfa_emergency_not_authorized";
        if (!elevationReadable) return "mfa_emergency_token_unreadable";
        return elevated ? null : "mfa_emergency_not_authorized";
    }

    [DllImport("advapi32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetTokenInformation(SafeAccessTokenHandle token, int informationClass,
        out uint elevation, uint length, out uint returned);
}
