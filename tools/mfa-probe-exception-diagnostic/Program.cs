using System.ComponentModel;
using System.Diagnostics;
using System.Reflection;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace RackClick.MfaProbeExceptionDiagnostic;

internal static class Program
{
    private static readonly Dictionary<string, string> Pins = new(StringComparer.Ordinal)
    {
        ["RackClick.MfaServiceReadProbe"] = "cbe28b6499b53ceb67e68f20ebef5f4d76d35dc0e88f9b30d893f920fe7934c1",
        ["RackClick.Server"] = "dfda3c93b0aa861ee8aecad144ed387fd7511991a6f9fb345f19553bdc7fb9ee",
        ["RackClick.Domain"] = "1bc5b1814a21210d91b7ed621a2f681f3dedfec64430ef83b10960a88bbbdfb7",
        ["Npgsql"] = "e2bcafe1660fe4543fe9dfcabed972ec8d32259e5ea8009462ce1de23c7034c2",
        ["Otp.NET"] = "5c211b2d746267e7830445d2243e7a71c29fd47f9eb3591cf53a5ecb63aa3745",
    };
    private static readonly HashSet<string> FrameNames = new(StringComparer.Ordinal)
    {
        "ReadService", "ImpersonatedRead", "ServiceMeasure.Measure", "ServiceMeasure.QueryConfig",
        "ServiceMeasure.ResolveAccount", "ImageMatch.Matches", "ImageMatch.ProcessImage", "TokenLink.SidOf",
        "TokenLink.DuplicateForImpersonation", "Access.OpenProcess", "Access.OpenToken", "DebugPrivilege.EnsureEnabled",
        "DebugPrivilege.Restore", "DebugPrivilege.Dispose", "WriteProbe.CheckStore", "WriteProbe.ProbeTarget",
        "StoreRead.ReadActiveKey", "Directory.EnumerateFiles", "Path.GetFullPath", "WindowsIdentity.RunImpersonated",
    };

    private static int Main(string[] args)
    {
        if (!OperatingSystem.IsWindows()) return Reject("not_windows");
        if (args.Length == 0 || args[0] is not ("measure" or "selftest")) return Reject("usage");
        if (args[0] == "measure" && Environment.MachineName.Equals("LEAO", StringComparison.OrdinalIgnoreCase))
            return Reject("host_excluded");
        try
        {
            var names = args[0] == "selftest" ? new[] { "probe" } : new[] { "probe", "instances-root", "installation-id", "service" };
            var values = Options(args, names);
            if (values is null) return Reject("usage");
            if (args[0] == "measure" && (WindowsIdentity.GetCurrent().User?.Value != "S-1-5-18" || WindowsIdentity.GetCurrent(true) is not null))
                return Reject("executor_not_system");
            if (!Path.IsPathFullyQualified(values["probe"]) || Path.GetFileName(values["probe"]) != "RackClick.MfaServiceReadProbe.dll") return Reject("probe_path_invalid");
            var folder = Path.GetDirectoryName(Path.GetFullPath(values["probe"]))!;
            var leases = new List<FileStream>();
            try
            {
                foreach (var (name, pin) in Pins)
                {
                    var stream = new FileStream(Path.Combine(folder, name + ".dll"), FileMode.Open, FileAccess.Read, FileShare.Read);
                    leases.Add(stream);
                    if (!Convert.ToHexString(SHA256.HashData(stream)).Equals(pin, StringComparison.OrdinalIgnoreCase)) return Reject("approved_assembly_hash_mismatch");
                }
                Assembly? Resolver(AssemblyLoadContext context, AssemblyName name) => name.Name is not null && Pins.ContainsKey(name.Name)
                    ? context.LoadFromAssemblyPath(Path.Combine(folder, name.Name + ".dll")) : null;
                AssemblyLoadContext.Default.Resolving += Resolver;
                try
                {
                    var assembly = AssemblyLoadContext.Default.LoadFromAssemblyPath(Path.Combine(folder, "RackClick.MfaServiceReadProbe.dll"));
                    if (args[0] == "selftest") return SelfTest(assembly);
                    if (!Path.IsPathFullyQualified(values["instances-root"]) || !Guid.TryParseExact(values["installation-id"], "D", out var id)
                        || !Regex.IsMatch(values["service"], "^[A-Za-z0-9_.-]{1,256}$", RegexOptions.CultureInvariant)) return Reject("usage");
                    var method = Method(assembly, "Program", "ReadService");
                    try
                    {
                        var evidence = method.Invoke(null, new object[] { values["service"], Path.GetFullPath(values["instances-root"]), id })
                            ?? throw new InvalidOperationException();
                        var code = Property<string>(evidence, "Code");
                        if (code.Length > 0 && !Regex.IsMatch(code, "^[a-z][a-z0-9_]{0,99}$", RegexOptions.CultureInvariant)) return Reject("returned_contract_invalid");
                        var outcome = new
                        {
                            probeCode = code, processLinked = Property<bool>(evidence, "ProcessLinked"), tokenMatched = Property<bool>(evidence, "TokenMatched"),
                            impersonationVerified = Property<bool>(evidence, "Impersonated"), identityRestored = Property<bool>(evidence, "IdentityRestored"),
                            activeVersion = Property<int>(evidence, "Version"), keyBytes = Property<int>(evidence, "KeyBytes"),
                        };
                        Emit(new { schemaVersion = 1, status = "measured", code = "returned", exceptionType = "none", hresult = 0, win32Error = 0, frames = Array.Empty<string>(), outcome });
                    }
                    catch (Exception error) { Emit(Report(error)); }
                    return 0; // A measured diagnostic is never a PASS verdict for MFA.
                }
                finally { AssemblyLoadContext.Default.Resolving -= Resolver; }
            }
            finally { foreach (var lease in leases) lease.Dispose(); }
        }
        catch (Exception error) { Emit(Report(error)); return 1; }
    }

    private static T Property<T>(object value, string name) => value.GetType().GetProperty(name)?.GetValue(value) is T typed ? typed : throw new InvalidOperationException();
    private static MethodInfo Method(Assembly assembly, string type, string method) => assembly.GetType("RackClick.MfaServiceReadProbe." + type, true)!
        .GetMethod(method, BindingFlags.Static | BindingFlags.NonPublic) ?? throw new InvalidOperationException();

    private static object Report(Exception error)
    {
        while (error is TargetInvocationException { InnerException: not null } wrapped) error = wrapped.InnerException!;
        var kind = error switch
        {
            ArgumentException => "argument", System.Security.SecurityException => "security", DirectoryNotFoundException => "directory_missing",
            UnauthorizedAccessException => "access_denied", FileNotFoundException or FileLoadException or BadImageFormatException or TypeLoadException => "assembly_load",
            IOException => "io", InvalidOperationException => "invalid_operation", _ => "other",
        };
        var frames = new List<string>();
        foreach (var frame in (new StackTrace(error, false).GetFrames() ?? Array.Empty<StackFrame>()).Take(64))
        {
            var method = frame.GetMethod(); var type = method?.DeclaringType;
            if (type is null || method is null) continue;
            var symbol = type.Name == "Program" ? method.Name : type.Name + "." + method.Name;
            var allowedType = type.Namespace == "RackClick.MfaServiceReadProbe" || type == typeof(Directory) || type == typeof(Path) || type == typeof(WindowsIdentity);
            if (allowedType && FrameNames.Contains(symbol) && !frames.Contains(symbol)) frames.Add(symbol);
            if (frames.Count == 16) break;
        }
        return new { schemaVersion = 1, status = "measured", code = "exception_captured", exceptionType = kind, hresult = error.HResult,
            win32Error = error is Win32Exception win32 ? win32.NativeErrorCode : 0, frames, outcome = (object?)null };
    }

    private static int SelfTest(Assembly assembly)
    {
        var results = new List<object>();
        object Fault(string name, MethodInfo method, object[] values, string kind, string symbol)
        {
            object? report = null;
            try { method.Invoke(null, values); } catch (Exception error) { report = Report(error); }
            using var doc = JsonDocument.Parse(JsonSerializer.Serialize(report));
            var ok = report is not null && doc.RootElement.GetProperty("exceptionType").GetString() == kind
                && doc.RootElement.GetProperty("frames").EnumerateArray().Any(value => value.GetString() == symbol);
            return new { name, passed = ok, report };
        }
        results.Add(Fault("approved_image_path_exception", Method(assembly, "ImageMatch", "Matches"), new object[] { @"C:\synthetic-no-file.exe", "\"   \"" }, "argument", "ImageMatch.Matches"));
        var temporary = Path.Combine(Path.GetTempPath(), "rackclick-probe-diagnostic-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(temporary);
        try
        {
            var own = WindowsIdentity.GetCurrent().User ?? throw new InvalidOperationException();
            results.Add(Fault("approved_missing_directory_exception", Method(assembly, "WriteProbe", "CheckStore"),
                new object[] { temporary, temporary, Path.Combine(temporary, "absent"), own }, "directory_missing", "WriteProbe.CheckStore"));
        }
        finally { Directory.Delete(temporary, false); }
        var sentinel = @"PRIVATE_SENTINEL C:\private\secret SID=synthetic base64=synthetic";
        var sanitized = JsonSerializer.Serialize(Report(new InvalidOperationException(sentinel)));
        results.Add(new { name = "no_exception_message_or_path", passed = !sanitized.Contains("PRIVATE_SENTINEL", StringComparison.Ordinal) && !sanitized.Contains("private", StringComparison.Ordinal) });
        var json = JsonSerializer.SerializeToElement(results);
        var passed = json.EnumerateArray().All(row => row.GetProperty("passed").GetBoolean());
        Emit(new { schemaVersion = 1, status = passed ? "selftest_passed" : "selftest_failed", checks = results.Count, results });
        return passed ? 0 : 1;
    }

    private static Dictionary<string, string>? Options(string[] args, string[] names)
    {
        var result = new Dictionary<string, string>(StringComparer.Ordinal);
        for (var i = 1; i < args.Length; i += 2)
            if (i + 1 >= args.Length || !args[i].StartsWith("--", StringComparison.Ordinal) || !names.Contains(args[i][2..], StringComparer.Ordinal) || !result.TryAdd(args[i][2..], args[i + 1])) return null;
        return result.Count == names.Length ? result : null;
    }
    private static void Emit(object value) => Console.WriteLine(JsonSerializer.Serialize(value));
    private static int Reject(string code) { Emit(new { schemaVersion = 1, status = "rejected", code }); return 1; }
}
