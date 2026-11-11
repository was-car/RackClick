using System.ComponentModel;
using System.Runtime.Versioning;
using System.Security.Principal;
using RackClick.Server;
using Xunit;

namespace RackClick.Quality.Tests;

[SupportedOSPlatform("windows")]
public sealed class WindowsMfaMaintenanceServiceTests
{
    private static readonly Guid Installation = Guid.Parse("680fbe24-1011-4f6a-991d-d580ef20c85c");
    private static readonly SecurityIdentifier Reader = new("S-1-5-21-123456789-123456789-123456789-1001");
    private const string Root = @"C:\Synthetic RackClick\Instances";
    private static string Folder => Path.Combine(Root, Installation.ToString("D"), "instance");
    private static string Runtime => Path.Combine(Folder, "content", "dependencies", "dotnet", "dotnet.exe");
    private static string Host => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "RackClick", Installation.ToString("D"), "service", "RackClick.WindowsService.dll");
    private static string Config => Path.Combine(Folder, "service-config.json");
    private static string Binary => $"\"{Runtime}\" \"{Host}\" --config \"{Config}\"";
    private static WindowsMfaMaintenanceObservedService Valid => new(0x10, 1, 0, Reader.Value, Binary);

    [Fact]
    public void ExactInstalledCommandStoppedOwnProcessAndReaderAreAccepted()
    {
        WindowsMfaMaintenanceService.ValidateObservedState(Valid, Reader, Installation, Root);
        WindowsMfaMaintenanceService.ValidateObservedState(Valid with { BinaryPath = Binary.ToUpperInvariant().Replace("--CONFIG", "--config", StringComparison.Ordinal) }, Reader, Installation, Root);
    }

    [Fact]
    public void StoppedMayReportAResidualPidWhichWindowsDoesNotDefineAsValid() =>
        WindowsMfaMaintenanceService.ValidateObservedState(Valid with { ProcessId = 42 }, Reader, Installation, Root);

    [Theory]
    [InlineData(0u)]
    [InlineData(2u)]
    [InlineData(3u)]
    [InlineData(4u)]
    [InlineData(5u)]
    [InlineData(6u)]
    [InlineData(7u)]
    public void AnyStateOtherThanStoppedIsRejected(uint state) => Assert.Throws<InvalidOperationException>(() =>
        WindowsMfaMaintenanceService.ValidateObservedState(Valid with { State = state }, Reader, Installation, Root));

    [Fact]
    public void SharedHostAndWrongReaderAreRejected()
    {
        foreach (var value in new[] { Valid with { ServiceType = 0x20 }, Valid with { AccountSid = "S-1-5-18" } })
            Assert.Throws<InvalidOperationException>(() => WindowsMfaMaintenanceService.ValidateObservedState(value, Reader, Installation, Root));
    }

    [Theory]
    [InlineData("foreign-id")]
    [InlineData("prefix-root")]
    [InlineData("same-id-unrelated-root")]
    [InlineData("config-only")]
    [InlineData("extra-argument")]
    [InlineData("duplicate-config")]
    [InlineData("wrong-host")]
    [InlineData("wrong-exe")]
    [InlineData("relative")]
    [InlineData("dot-dot")]
    [InlineData("environment")]
    [InlineData("embedded-marker")]
    [InlineData("nul")]
    public void ArgumentsCannotOnlyContainTheInstallationMarkerOrExtraOptions(string shape)
    {
        var binary = shape switch
        {
            "foreign-id" => Binary.Replace(Installation.ToString("D"), Guid.NewGuid().ToString("D"), StringComparison.Ordinal),
            "prefix-root" => Binary.Replace(Root, Root + "-foreign", StringComparison.Ordinal),
            "same-id-unrelated-root" => Binary.Replace(Root, @"C:\Unrelated\Instances", StringComparison.Ordinal),
            "config-only" => $"\"C:\\malicious.exe\" --config \"{Config}\"",
            "extra-argument" => Binary + " --maintenance-bypass",
            "duplicate-config" => Binary + $" --config \"{Config}\"",
            "wrong-host" => Binary.Replace("RackClick.WindowsService.dll", "Other.WindowsService.dll", StringComparison.Ordinal),
            "wrong-exe" => Binary.Replace("dotnet.exe", "powershell.exe", StringComparison.Ordinal),
            "relative" => $"dotnet.exe \"{Host}\" --config \"{Config}\"",
            "dot-dot" => Binary.Replace("\\instance\\content", "\\instance\\..\\instance\\content", StringComparison.Ordinal),
            "environment" => Binary.Replace(Root, "%PROGRAMDATA%\\RackClick\\Instances", StringComparison.Ordinal),
            "embedded-marker" => $"\"C:\\malicious.exe\" \"{Binary.Replace("\"", "", StringComparison.Ordinal)}\"",
            _ => Binary + '\0',
        };
        Assert.Throws<InvalidOperationException>(() => WindowsMfaMaintenanceService.ValidateObservedState(Valid with { BinaryPath = binary }, Reader, Installation, Root));
    }

    [Fact]
    public void UnknownLocalServiceIsAReadOnlyNegative()
    {
        var name = "RackClickAbsent-" + Guid.NewGuid().ToString("N");
        var exception = Assert.Throws<InvalidOperationException>(() => WindowsMfaMaintenanceService.RequireStopped(name, Reader, Installation, Root));
        Assert.Equal(1060, Assert.IsType<Win32Exception>(exception.InnerException).NativeErrorCode);
    }

    [Theory]
    [InlineData("")]
    [InlineData("RackClick\\other")]
    [InlineData("RackClick/other")]
    [InlineData("RackClick\nother")]
    public void InvalidNamesAreRejectedBeforeScm(string name) => Assert.Throws<InvalidOperationException>(() =>
        WindowsMfaMaintenanceService.RequireStopped(name, Reader, Installation, Root));
}
