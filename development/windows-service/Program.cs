using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Hosting.WindowsServices;

try
{
    if (!OperatingSystem.IsWindows()) throw new InvalidOperationException();
    bool console = args.Contains("--console", StringComparer.Ordinal);
    string[] clean = args.Where(a => a != "--console").ToArray();
    if (clean.Length != 2 || clean[0] != "--config" || args.Count(a => a == "--console") > 1)
        throw new InvalidOperationException();
    var config = ServiceConfig.Load(clean[1], console);
    if (!console && !WindowsServiceHelpers.IsWindowsService()) throw new InvalidOperationException();
    var builder = Host.CreateApplicationBuilder(Array.Empty<string>());
    builder.Services.Configure<HostOptions>(o => o.ShutdownTimeout = TimeSpan.FromSeconds(110));
    if (!console) builder.Services.AddWindowsService(o => o.ServiceName = config.ServiceName);
    builder.Services.AddSingleton(config);
    builder.Services.AddHostedService<RuntimeSupervisor>();
    using var host = builder.Build();
    int consoleStopRequested = 0;
    if (console && Console.IsInputRedirected)
        _ = Task.Run(() => { if (Console.ReadLine() == "stop") { Interlocked.Exchange(ref consoleStopRequested, 1); host.Services.GetRequiredService<IHostApplicationLifetime>().StopApplication(); } });
    try { await host.RunAsync(); }
    catch (OperationCanceledException) when (console && Volatile.Read(ref consoleStopRequested) == 1) { }
    return Environment.ExitCode;
}
catch (Exception ex)
{
    Console.Error.WriteLine("rackclick_service_failed:" + ex.GetType().Name);
    return 1;
}

sealed record ServiceConfig(string ServiceName, string RuntimeScriptPath, string ServerManifestPath,
    string ServerManifestSha256, string LogDirectory)
{
    public bool ConsoleFixture { get; init; }
    public static ServiceConfig Load(string path, bool console)
    {
        CheckPath(path, false);
        using var document = JsonDocument.Parse(File.ReadAllBytes(path));
        var root = document.RootElement;
        string[] expected = ["schemaVersion", "serviceName", "runtimeScriptPath", "serverManifestPath", "serverManifestSha256", "logDirectory"];
        var names = root.EnumerateObject().Select(p => p.Name).ToArray();
        if (names.Length != expected.Length || !names.Order().SequenceEqual(expected.Order()) || root.GetProperty("schemaVersion").GetInt32() != 1)
            throw new InvalidOperationException();
        string Get(string name) => root.GetProperty(name).GetString() ?? throw new InvalidOperationException();
        var c = new ServiceConfig(Get("serviceName"), Get("runtimeScriptPath"), Get("serverManifestPath"), Get("serverManifestSha256"), Get("logDirectory")) { ConsoleFixture = console };
        if (!System.Text.RegularExpressions.Regex.IsMatch(c.ServiceName, @"\ARackClick(?:-Recovery-[a-f0-9]{8,32})?\z", System.Text.RegularExpressions.RegexOptions.CultureInvariant) || c.ServerManifestSha256.Length != 64 || !c.ServerManifestSha256.All(Uri.IsHexDigit))
            throw new InvalidOperationException();
        CheckCode(c.RuntimeScriptPath, console); CheckPath(c.ServerManifestPath, false); CheckPath(c.LogDirectory, true);
        if (!c.RuntimeScriptPath.EndsWith(".ps1", StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException();
        using var stream = File.OpenRead(c.ServerManifestPath);
        if (!Convert.ToHexString(SHA256.HashData(stream)).Equals(c.ServerManifestSha256, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException();
        return c;
    }
    public static void CheckPath(string path, bool directory)
    {
        CheckNoReparse(path);
        FileSystemSecurity acl = directory ? new DirectoryInfo(path).GetAccessControl() : new FileInfo(path).GetAccessControl();
        string current = WindowsIdentity.GetCurrent().User!.Value;
        string owner = (acl.GetOwner(typeof(SecurityIdentifier)) ?? throw new InvalidOperationException()).Value;
        if (owner != current && owner != "S-1-5-18") throw new InvalidOperationException();
        bool ownAccess = false;
        foreach (FileSystemAccessRule rule in acl.GetAccessRules(true, true, typeof(SecurityIdentifier)))
        {
            string sid = rule.IdentityReference.Value;
            if (rule.AccessControlType == AccessControlType.Allow && sid != current && sid != "S-1-5-18") throw new InvalidOperationException();
            if (rule.AccessControlType == AccessControlType.Allow && sid == current && (rule.FileSystemRights & FileSystemRights.Read) != 0) ownAccess = true;
        }
        if (!ownAccess) throw new InvalidOperationException();
    }
    public static void CheckCode(string path, bool consoleFixture)
    {
        if (consoleFixture) { CheckPath(path, false); return; }
        CheckNoReparse(path);
        foreach (FileSystemSecurity acl in new FileSystemSecurity[] { new FileInfo(path).GetAccessControl(), new DirectoryInfo(Path.GetDirectoryName(path)!).GetAccessControl() })
        {
            string owner = (acl.GetOwner(typeof(SecurityIdentifier)) ?? throw new InvalidOperationException()).Value;
            if (owner != "S-1-5-18" && owner != "S-1-5-32-544") throw new InvalidOperationException();
            const FileSystemRights writes = FileSystemRights.Write | FileSystemRights.Delete | FileSystemRights.DeleteSubdirectoriesAndFiles | FileSystemRights.ChangePermissions | FileSystemRights.TakeOwnership;
            foreach (FileSystemAccessRule rule in acl.GetAccessRules(true, true, typeof(SecurityIdentifier)))
                if (rule.AccessControlType == AccessControlType.Allow && (rule.FileSystemRights & writes) != 0 && rule.IdentityReference.Value != "S-1-5-18" && rule.IdentityReference.Value != "S-1-5-32-544") throw new InvalidOperationException();
        }
        using var readable = File.OpenRead(path);
    }
    static void CheckNoReparse(string path)
    {
        if (!Path.IsPathFullyQualified(path) || path.StartsWith(@"\\", StringComparison.Ordinal) || path.IndexOf(':', 2) >= 0) throw new InvalidOperationException();
        for (string? cursor = Path.GetFullPath(path); cursor != null; cursor = Path.GetDirectoryName(cursor))
            if ((File.GetAttributes(cursor) & FileAttributes.ReparsePoint) != 0) throw new InvalidOperationException();
    }
}

sealed class RuntimeSupervisor(ServiceConfig config, IHostApplicationLifetime lifetime) : BackgroundService
{
    readonly string runId = Guid.NewGuid().ToString("D");
    Process? runtime;
    Job? job;
    volatile bool stopping;
    readonly object runtimeLock = new();
    string? lifecyclePath;
    readonly object recordLock = new();
    void Record(string code, int? exit = null)
    {
        lock (recordLock)
        {
        if (lifecyclePath == null)
        {
            ServiceConfig.CheckPath(config.LogDirectory, true);
            lifecyclePath = Path.Combine(config.LogDirectory, "host-" + runId + ".jsonl");
            using (new FileStream(lifecyclePath, FileMode.CreateNew, FileAccess.Write, FileShare.Read)) { }
            var acl = new FileSecurity(); acl.SetAccessRuleProtection(true, false);
            foreach (var sid in new[] { WindowsIdentity.GetCurrent().User!, new SecurityIdentifier("S-1-5-18") })
                acl.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, AccessControlType.Allow));
            new FileInfo(lifecyclePath).SetAccessControl(acl);
            ServiceConfig.CheckPath(lifecyclePath, false);
        }
        File.AppendAllText(lifecyclePath, JsonSerializer.Serialize(new { timestamp = DateTimeOffset.UtcNow, code, runId, exitCode = exit }) + "\n");
        }
    }

    Process Launch(string operation, bool contain)
    {
        // Recheck before every command; never accept environment-selected PowerShell.
        ServiceConfig.CheckCode(config.RuntimeScriptPath, config.ConsoleFixture);
        var info = new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), @"System32\WindowsPowerShell\v1.0\powershell.exe"))
        { UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = Path.GetDirectoryName(config.RuntimeScriptPath)! };
        foreach (string arg in new[] { "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", config.RuntimeScriptPath, "-Operation", operation, "-ManifestPath", config.ServerManifestPath, "-ExpectedManifestSha256", config.ServerManifestSha256, "-RunId", runId }) info.ArgumentList.Add(arg);
        return job!.LaunchSuspended(info);
    }
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        try
        {
            lock (runtimeLock)
            {
                if (stopping || stoppingToken.IsCancellationRequested) return;
                Record("start_requested");
                job = new Job();
                runtime = Launch("Start", true);
                Record("runtime_started");
            }
            await runtime.WaitForExitAsync(CancellationToken.None);
            if (!stopping)
            {
                Record("runtime_unexpected_exit", runtime.ExitCode);
                Environment.ExitCode = 1;
                lifetime.StopApplication();
            }
        }
        catch (Exception ex) { Console.Error.WriteLine("runtime_failed:" + ex.GetType().Name); try { Record("start_failed", 1); } catch { } Environment.ExitCode = 1; lifetime.StopApplication(); }
        finally { if (!stopping) job?.Dispose(); }
    }
    public override async Task StopAsync(CancellationToken cancellationToken)
    {
        lock (runtimeLock) { stopping = true; }
        try
        {
            Record("stop_requested");
            if (runtime is { HasExited: false })
            {
                using var stop = Launch("Stop", true);
                using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
                timeout.CancelAfter(TimeSpan.FromSeconds(90));
                await stop.WaitForExitAsync(timeout.Token);
                if (stop.ExitCode != 0) throw new InvalidOperationException();
                await runtime.WaitForExitAsync(timeout.Token);
                if (runtime.ExitCode != 0) throw new InvalidOperationException();
                Record("runtime_stopped", runtime.ExitCode);
            }
        }
        catch { Environment.ExitCode = 1; try { Record("stop_failed", 1); } catch { } }
        finally { job?.Dispose(); }
        await base.StopAsync(cancellationToken);
        runtime?.Dispose();
    }
}

sealed class Job : IDisposable
{
    IntPtr handle;
    public Job()
    {
        handle = CreateJobObject(IntPtr.Zero, null);
        if (handle == IntPtr.Zero) throw new InvalidOperationException();
        var limits = new ExtendedLimits(); limits.Basic.LimitFlags = 0x2000; // KILL_ON_JOB_CLOSE
        if (!SetInformationJobObject(handle, 9, ref limits, (uint)Marshal.SizeOf<ExtendedLimits>())) { Dispose(); throw new InvalidOperationException(); }
    }
    public void Assign(Process process) { if (!AssignProcessToJobObject(handle, process.Handle)) throw new InvalidOperationException(); }
    public Process LaunchSuspended(ProcessStartInfo info)
    {
        static string Quote(string value) => "\"" + System.Text.RegularExpressions.Regex.Replace(value, "(\\\\*)\"", "$1$1\\\"").TrimEnd('\\') + new string('\\', value.Reverse().TakeWhile(c => c == '\\').Count() * 2) + "\"";
        string command = Quote(info.FileName) + " " + string.Join(" ", info.ArgumentList.Select(Quote));
        var startup = new StartupInfo { Size = Marshal.SizeOf<StartupInfo>() };
        if (!CreateProcess(info.FileName, new System.Text.StringBuilder(command), IntPtr.Zero, IntPtr.Zero, false,
            0x00000004 | 0x08000000, IntPtr.Zero, info.WorkingDirectory, ref startup, out var child)) throw new InvalidOperationException();
        try
        {
            if (!AssignProcessToJobObject(handle, child.Process)) throw new InvalidOperationException();
            var process = Process.GetProcessById((int)child.ProcessId);
            if (ResumeThread(child.Thread) == uint.MaxValue) { process.Dispose(); throw new InvalidOperationException(); }
            return process;
        }
        catch { TerminateProcess(child.Process, 1); throw; }
        finally { CloseHandle(child.Thread); CloseHandle(child.Process); }
    }
    public void Dispose() { var closing = Interlocked.Exchange(ref handle, IntPtr.Zero); if (closing != IntPtr.Zero) CloseHandle(closing); }
    [StructLayout(LayoutKind.Sequential)] struct BasicLimits { public long PerProcessUserTime, PerJobUserTime; public uint LimitFlags; public UIntPtr MinimumWorkingSet, MaximumWorkingSet; public uint ActiveProcessLimit; public UIntPtr Affinity; public uint PriorityClass, SchedulingClass; }
    [StructLayout(LayoutKind.Sequential)] struct IoCounters { public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount, ReadTransferCount, WriteTransferCount, OtherTransferCount; }
    [StructLayout(LayoutKind.Sequential)] struct ExtendedLimits { public BasicLimits Basic; public IoCounters Io; public UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed; }
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] static extern IntPtr CreateJobObject(IntPtr attributes, string? name);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool SetInformationJobObject(IntPtr job, int infoClass, ref ExtendedLimits info, uint length);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool CloseHandle(IntPtr handle);
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] struct StartupInfo
    {
        public int Size; public string? Reserved, Desktop, Title;
        public uint X, Y, XSize, YSize, XCountChars, YCountChars, FillAttribute, Flags;
        public ushort ShowWindow, Reserved2; public IntPtr ReservedPointer, Input, Output, Error;
    }
    [StructLayout(LayoutKind.Sequential)] struct ProcessInformation { public IntPtr Process, Thread; public uint ProcessId, ThreadId; }
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] static extern bool CreateProcess(string application, System.Text.StringBuilder command, IntPtr processAttributes, IntPtr threadAttributes, bool inheritHandles, uint flags, IntPtr environment, string directory, ref StartupInfo startup, out ProcessInformation process);
    [DllImport("kernel32.dll", SetLastError = true)] static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool TerminateProcess(IntPtr process, uint exitCode);
}
