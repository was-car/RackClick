using System.Diagnostics;
using System.Reflection;
using System.Runtime.Versioning;
using System.Security.Principal;
using System.Text.Json;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

[SupportedOSPlatform("windows")]
public sealed class MfaEmergencyProcessTests
{
    [Theory]
    [InlineData("--bootstrap")]
    [InlineData("--migrate")]
    [InlineData("--recover-admin")]
    [InlineData("--mfa-keys-init")]
    [InlineData("--mfa-require-all")]
    [InlineData("--mfa-backup-inventory")]
    [InlineData("--mfa-key-maintenance")]
    public async Task EmergencyModeCannotBeCombinedWithAnotherCliAuthority(string otherMode)
    {
        var run = await Run("--mfa-emergency-recovery", otherMode);
        Assert.Equal(1, run.ExitCode);
        using var body = JsonDocument.Parse(run.Output);
        Assert.Equal("cli_mode_conflict", body.RootElement.GetProperty("error").GetString());
        Assert.Equal("", run.Error);
    }

    [Theory]
    [InlineData("--urls", "http://127.0.0.1:1")]
    [InlineData("--mfa-emergency-recovery", "")]
    public async Task ExtraArgumentsCannotTurnEmergencyIntoAHost(string first, string second)
    {
        var arguments = second.Length == 0
            ? new[] { "--mfa-emergency-recovery", first }
            : new[] { "--mfa-emergency-recovery", first, second };
        var run = await Run(arguments);
        Assert.Equal(1, run.ExitCode);
        using var body = JsonDocument.Parse(run.Output);
        Assert.Equal("mfa_emergency_arguments_invalid", body.RootElement.GetProperty("code").GetString());
        Assert.Equal("", run.Error);
    }

    [Fact]
    public async Task EmergencyEntryRejectsWithoutReadingPoisonedHostConfigurationOrGrantingASession()
    {
        var run = await Run("--mfa-emergency-recovery");
        Assert.Equal(1, run.ExitCode);
        Assert.Equal("", run.Error);
        var line = Assert.Single(run.Output.Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries));
        using var body = JsonDocument.Parse(line);
        var json = body.RootElement;
        Assert.Equal("rejected", json.GetProperty("status").GetString());
        using var identity = WindowsIdentity.GetCurrent();
        string? nativeDenial = !identity.IsSystem && !new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator)
            ? "mfa_emergency_not_authorized"
            : (string?)typeof(MfaKeyRing).Assembly.GetType("RackClick.Server.MfaEmergencyRecoveryCommand", true)!
                .GetMethod("AuthorizationFailure", BindingFlags.NonPublic | BindingFlags.Static)!.Invoke(null, null);
        Assert.Equal(nativeDenial ?? "mfa_emergency_transition_unavailable", json.GetProperty("code").GetString());
        Assert.Equal(0, json.GetProperty("operationsApplied").GetInt32());
        Assert.False(json.GetProperty("sessionGranted").GetBoolean());
        Assert.DoesNotContain("untrusted-marker", run.Output, StringComparison.Ordinal);
        Assert.DoesNotContain("listening", run.Output, StringComparison.OrdinalIgnoreCase);
    }

    private static async Task<ServerRun> Run(params string[] arguments)
    {
        var start = new ProcessStartInfo(Path.Combine(AppContext.BaseDirectory, "RackClick.Server.exe"))
        {
            UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true,
            WorkingDirectory = AppContext.BaseDirectory,
        };
        foreach (var name in start.Environment.Keys.Where(name => name.StartsWith("CORECLR_", StringComparison.OrdinalIgnoreCase)
            || name.StartsWith("COR_", StringComparison.OrdinalIgnoreCase)
            || name.StartsWith("DOTNET_", StringComparison.OrdinalIgnoreCase) && !name.Equals("DOTNET_ROOT", StringComparison.OrdinalIgnoreCase)).ToArray())
            start.Environment.Remove(name);
        start.Environment["DOTNET_EnableDiagnostics"] = "0";
        start.Environment["ASPNETCORE_ENVIRONMENT"] = "Production";
        start.Environment["ConnectionStrings__RackClick"] = "untrusted-marker-not-a-connection";
        start.Environment["PublicOrigin"] = "untrusted-marker-not-an-origin";
        start.Environment["MfaKeyStore__Enabled"] = "untrusted-marker-not-a-boolean";
        start.Environment["MfaEmergency__Elevated"] = "true";
        start.Environment["MfaEmergency__System"] = "true";
        start.Environment["MfaEmergency__Authorized"] = "true";
        foreach (var argument in arguments) start.ArgumentList.Add(argument);
        using var process = Process.Start(start) ?? throw new InvalidOperationException("Synthetic child unavailable.");
        var output = process.StandardOutput.ReadToEndAsync(); var error = process.StandardError.ReadToEndAsync();
        await process.StandardInput.WriteAsync("untrusted-marker-never-used-as-password");
        process.StandardInput.Close();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        try { await process.WaitForExitAsync(timeout.Token); }
        catch (OperationCanceledException) { if (!process.HasExited) process.Kill(entireProcessTree: true); throw; }
        return new(process.ExitCode, await output, await error);
    }

    private sealed record ServerRun(int ExitCode, string Output, string Error);
}
