using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.Principal;
using System.Text;
using Microsoft.Win32.SafeHandles;

namespace RackClick.Server;

internal sealed record WindowsMfaMaintenanceObservedService(uint ServiceType, uint State, uint ProcessId,
    string AccountSid, string BinaryPath);

// Read-only local SCM preflight. The native installer publishes exactly the dotnet + WindowsService.dll + --config
// topology checked here. This is an observation, not a lease preventing a later StartService; the coordinator must still
// hold its host/maintenance leases and publish its persistent fence before replacing the ring.
[SupportedOSPlatform("windows")]
internal static class WindowsMfaMaintenanceService
{
    internal static void RequireStopped(string serviceName, SecurityIdentifier expectedReaderSid, Guid installationId, string instancesRoot)
    {
        if (string.IsNullOrEmpty(serviceName) || serviceName.Length > 128 ||
            serviceName.Any(c => !char.IsAsciiLetterOrDigit(c) && c is not '-' and not '_' and not '.')) throw Failure("service_name_invalid");
        var paths = ExpectedPaths(installationId, instancesRoot);
        // Only SC_MANAGER_CONNECT, SERVICE_QUERY_CONFIG and SERVICE_QUERY_STATUS. No control/write rights are requested.
        using var manager = OpenSCManagerW(null, null, 1);
        if (manager.IsInvalid) throw NativeFailure("scm_unavailable");
        using var service = OpenServiceW(manager, serviceName, 1 | 4);
        if (service.IsInvalid) throw NativeFailure("service_unavailable");
        var observed = Observe(service);
        ValidateObservedState(observed, expectedReaderSid, installationId, instancesRoot);
        var held = new List<FileStream>();
        try
        {
            foreach (var path in paths) held.Add(HoldPhysicalFile(path));
            // Re-read after checking the bound files so a transition observed during the check rejects maintenance.
            var again = Observe(service);
            ValidateObservedState(again, expectedReaderSid, installationId, instancesRoot);
            if (observed.BinaryPath != again.BinaryPath || observed.AccountSid != again.AccountSid)
                throw Failure("service_changed_during_check");
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            throw Failure("service_binding_files_unavailable", ex);
        }
        finally { foreach (var file in held) file.Dispose(); }
    }

    internal static void ValidateObservedState(WindowsMfaMaintenanceObservedService observed,
        SecurityIdentifier expectedReaderSid, Guid installationId, string instancesRoot)
    {
        // dwProcessId is explicitly undefined by QueryServiceStatusEx for SERVICE_STOPPED. Do not infer liveness from it.
        if (observed.ServiceType != 0x10 || observed.State != 1)
            throw Failure("service_not_stopped_own_process");
        if (!StringComparer.Ordinal.Equals(observed.AccountSid, expectedReaderSid.Value)) throw Failure("service_reader_sid_mismatch");
        var expected = ExpectedPaths(installationId, instancesRoot);
        var args = ParseArguments(observed.BinaryPath);
        if (args.Length != 4 || args[2] != "--config") throw Failure("service_command_invalid");
        RequirePath(args[0], expected[0]);
        RequirePath(args[1], expected[1]);
        RequirePath(args[3], expected[2]);
    }

    private static WindowsMfaMaintenanceObservedService Observe(ServiceHandle service)
    {
        if (!QueryServiceStatusEx(service, 0, out var status, (uint)Marshal.SizeOf<ServiceStatus>(), out _))
            throw NativeFailure("service_status_unavailable");
        QueryServiceConfigW(service, IntPtr.Zero, 0, out var needed);
        if (Marshal.GetLastWin32Error() != 122 || needed < Marshal.SizeOf<ServiceConfig>() || needed > 8192)
            throw NativeFailure("service_config_size_invalid");
        var buffer = Marshal.AllocHGlobal((int)needed);
        try
        {
            if (!QueryServiceConfigW(service, buffer, needed, out _)) throw NativeFailure("service_config_unavailable");
            var config = Marshal.PtrToStructure<ServiceConfig>(buffer);
            var account = Marshal.PtrToStringUni(config.Account) ?? throw Failure("service_account_missing");
            var binary = Marshal.PtrToStringUni(config.Binary) ?? throw Failure("service_binary_missing");
            string sid;
            try
            {
                if (account.Equals("LocalSystem", StringComparison.OrdinalIgnoreCase)) sid = "S-1-5-18";
                else
                {
                    if (account.StartsWith(@".\", StringComparison.Ordinal)) account = Environment.MachineName + account[1..];
                    sid = ((SecurityIdentifier)new NTAccount(account).Translate(typeof(SecurityIdentifier))).Value;
                }
            }
            catch (IdentityNotMappedException ex) { throw Failure("service_account_unresolved", ex); }
            if (config.Type != status.Type) throw Failure("service_type_changed");
            return new(status.Type, status.State, status.ProcessId, sid, binary);
        }
        finally { Marshal.FreeHGlobal(buffer); }
    }

    private static string[] ExpectedPaths(Guid installationId, string instancesRoot)
    {
        if (installationId == Guid.Empty || string.IsNullOrWhiteSpace(instancesRoot) || !Path.IsPathFullyQualified(instancesRoot) ||
            instancesRoot.Any(c => c < 32 || c == '"') || instancesRoot.AsSpan(2).Contains(':')) throw Failure("native_root_invalid");
        var root = Path.TrimEndingDirectorySeparator(Path.GetFullPath(instancesRoot));
        var id = installationId.ToString("D");
        var instance = Path.Combine(root, id, "instance");
        return
        [
            Path.Combine(instance, "content", "dependencies", "dotnet", "dotnet.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "RackClick", id, "service", "RackClick.WindowsService.dll"),
            Path.Combine(instance, "service-config.json"),
        ];
    }

    private static string[] ParseArguments(string command)
    {
        if (string.IsNullOrWhiteSpace(command) || command.Length > 32767 || command.Any(c => c < 32)) throw Failure("service_command_invalid");
        var pointer = CommandLineToArgvW(command, out var count);
        if (pointer == IntPtr.Zero) throw NativeFailure("service_command_parse_failed");
        try
        {
            if (count != 4) throw Failure("service_command_invalid");
            var values = new string[count];
            for (var i = 0; i < count; i++) values[i] = Marshal.PtrToStringUni(Marshal.ReadIntPtr(pointer, i * IntPtr.Size)) ?? throw Failure("service_argument_missing");
            return values;
        }
        finally { LocalFree(pointer); }
    }

    private static void RequirePath(string actual, string expected)
    {
        if (!Path.IsPathFullyQualified(actual) || !StringComparer.OrdinalIgnoreCase.Equals(Path.GetFullPath(actual), actual) ||
            !StringComparer.OrdinalIgnoreCase.Equals(actual, expected)) throw Failure("service_path_binding_mismatch");
    }

    private static FileStream HoldPhysicalFile(string path)
    {
        // Check each named ancestor and the final file. The same opened file is retained through the second SCM reading.
        for (string? item = path; item is not null; item = Path.GetDirectoryName(Path.TrimEndingDirectorySeparator(item)))
        {
            if ((File.GetAttributes(item) & FileAttributes.ReparsePoint) != 0) throw Failure("service_binding_reparse");
            if (Path.GetPathRoot(item) == item) break;
        }
        var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        try
        {
            var buffer = new StringBuilder(32768);
            var length = GetFinalPathNameByHandleW(stream.SafeFileHandle, buffer, (uint)buffer.Capacity, 0);
            if (length == 0 || length >= buffer.Capacity) throw Failure("service_binding_final_path_unavailable");
            var final = buffer.ToString();
            if (final.StartsWith(@"\\?\", StringComparison.Ordinal)) final = final[4..];
            if (!StringComparer.OrdinalIgnoreCase.Equals(final, path)) throw Failure("service_binding_redirected");
            return stream;
        }
        catch { stream.Dispose(); throw; }
    }

    private static InvalidOperationException Failure(string code, Exception? inner = null) => new("mfa_maintenance_" + code, inner);
    private static InvalidOperationException NativeFailure(string code) => Failure(code, new Win32Exception(Marshal.GetLastWin32Error()));

    private sealed class ServiceHandle : SafeHandleZeroOrMinusOneIsInvalid
    {
        public ServiceHandle() : base(true) { }
        protected override bool ReleaseHandle() => CloseServiceHandle(handle);
    }
    [StructLayout(LayoutKind.Sequential)] private struct ServiceStatus
    {
        public uint Type, State, ControlsAccepted, Win32ExitCode, ServiceExitCode, CheckPoint, WaitHint, ProcessId, Flags;
    }
    [StructLayout(LayoutKind.Sequential)] private struct ServiceConfig
    {
        public uint Type, Start, ErrorControl;
        public IntPtr Binary, LoadOrderGroup;
        public uint Tag;
        public IntPtr Dependencies, Account, DisplayName;
    }
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern ServiceHandle OpenSCManagerW(string? machineName, string? databaseName, uint desiredAccess);
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern ServiceHandle OpenServiceW(ServiceHandle manager, string serviceName, uint desiredAccess);
    [DllImport("advapi32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool QueryServiceStatusEx(ServiceHandle service, uint level, out ServiceStatus status, uint size, out uint needed);
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool QueryServiceConfigW(ServiceHandle service, IntPtr buffer, uint size, out uint needed);
    [DllImport("advapi32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CloseServiceHandle(IntPtr handle);
    [DllImport("shell32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CommandLineToArgvW(string commandLine, out int count);
    [DllImport("kernel32.dll")] private static extern IntPtr LocalFree(IntPtr memory);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern uint GetFinalPathNameByHandleW(SafeFileHandle handle, StringBuilder path, uint size, uint flags);
}
