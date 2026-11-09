using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using Microsoft.Win32.SafeHandles;

namespace RackClick.MfaAclProbe;

internal sealed class ProbeError(string code) : Exception(code) { public string Code { get; } = code; }
internal sealed record Target(string Label, string Path, bool IsDirectory, bool ReadExpected);
internal sealed record Actor(string Label, string ServiceName, string ExpectedSid, Target[] Targets);
internal sealed record Request(string ExpectedHost, Guid[] InstallationIds, Actor[] Actors);
internal sealed record RightResult(string Right, uint Mask, bool Expected, bool Granted, int Win32Error)
{
    public bool Passed => Expected ? Granted && Win32Error == 0 : !Granted && Win32Error == 5;
}
internal sealed record TargetResult(string Label, RightResult[] Rights)
{
    public bool Passed => Rights.All(r => r.Passed);
}
internal sealed record ActorResult(string Label, bool ProcessLinked, bool SidMatchesService, bool StandardToken,
    bool ImpersonationVerified, bool IdentityRestored, TargetResult[] Targets)
{
    public bool Passed => ProcessLinked && SidMatchesService && StandardToken && ImpersonationVerified &&
                          IdentityRestored && Targets.All(t => t.Passed);
}
internal sealed record AceFact(string Kind, int Mask, int Flags, string Principal);
internal sealed record NodeSnapshot(string Label, bool Directory, uint Attributes, uint Volume, ulong FileId,
    uint Links, ulong Length, ulong WriteTime, string SecuritySha256, bool ProtectedDacl, bool OwnerFixedTrust,
    AceFact[] Aces);

[SupportedOSPlatform("windows")]
internal static partial class Probe
{
    internal const string ForbiddenInstallation = "bbd2b6c2-abaf-4964-8c12-cf8f0c4af2aa";
    internal const string Scope = @"C:\ProgramData\RackClick\Instances";
    private const string CommonRoot = @"C:\ProgramData\RackClick";
    private static readonly JsonSerializerOptions Json = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

    internal static int Main(string[] args)
    {
        try
        {
            if (!OperatingSystem.IsWindows()) throw new ProbeError("windows_required");
            if (args is ["--selftest"]) return SelfTest.Run();
            if (args is not ["--measure"]) throw new ProbeError("mode_invalid");
            // No reading stdin, SCM, paths or tokens when the host is excluded.
            if (Environment.MachineName.Equals("LEAO", StringComparison.OrdinalIgnoreCase)) throw new ProbeError("host_excluded");
            using var current = WindowsIdentity.GetCurrent();
            if (current.User?.Value != "S-1-5-18") throw new ProbeError("system_required");
            if (!Console.IsInputRedirected) throw new ProbeError("redirected_input_required");
            var input = ReadBounded(Console.In);
            var request = Parse(input);
            if (!request.ExpectedHost.Equals(Environment.MachineName, StringComparison.OrdinalIgnoreCase))
                throw new ProbeError("host_binding_invalid");
            Prewarm();
            var before = Snapshot(request);
            var actors = request.Actors.Select(Measure).ToArray();
            var after = Snapshot(request);
            var unchanged = Fingerprint(before) == Fingerprint(after);
            var passed = unchanged && actors.All(a => a.Passed);
            Console.WriteLine(JsonSerializer.Serialize(new
            {
                schemaVersion = 1, status = passed ? "verified" : "failed", code = passed ? "effective_acl_verified" : "effective_acl_failed",
                measuredUtc = DateTimeOffset.UtcNow.ToString("O"),
                requestSha256 = Hash(Encoding.UTF8.GetBytes(input)),
                fingerprintBefore = Fingerprint(before), fingerprintAfter = Fingerprint(after), fingerprintUnchanged = unchanged,
                actors, nodes = before, processIdentityRestored = WindowsIdentity.GetCurrent().User?.Value == "S-1-5-18",
                filesWritten = 0, aclsChanged = 0, keysRead = false, managementContentRead = false,
                serviceOperations = 0, privilegesChanged = false, notMfaActivation = true,
            }, Json));
            return passed ? 0 : 1;
        }
        catch (Exception ex)
        {
            var code = ex is ProbeError error ? error.Code : "probe_failed";
            Console.WriteLine(JsonSerializer.Serialize(new { schemaVersion = 1, status = "failed", code,
                filesWritten = 0, aclsChanged = 0, keysRead = false, managementContentRead = false,
                serviceOperations = 0, privilegesChanged = false, notMfaActivation = true }, Json));
            return 1;
        }
    }

    private static string ReadBounded(TextReader reader)
    {
        var buffer = new char[65537]; var length = 0;
        while (length < buffer.Length)
        {
            var count = reader.Read(buffer, length, buffer.Length - length);
            if (count == 0) break;
            length += count;
        }
        if (length == 0 || length > 65536) throw new ProbeError("input_invalid");
        return new string(buffer, 0, length);
    }

    internal static Request Parse(string input)
    {
        try
        {
            using var document = JsonDocument.Parse(input, new JsonDocumentOptions { MaxDepth = 12 });
            var root = document.RootElement;
            Keys(root, "schemaVersion", "expectedHost", "installationIds", "actors");
            if (root.GetProperty("schemaVersion").GetInt32() != 1) throw new ProbeError("input_invalid");
            var host = Text(root, "expectedHost");
            if (!HostRegex().IsMatch(host)) throw new ProbeError("input_invalid");
            var ids = root.GetProperty("installationIds").EnumerateArray().Select(x =>
            {
                var value = x.GetString();
                if (!Guid.TryParseExact(value, "D", out var id) || id == Guid.Empty || value != id.ToString("D") ||
                    value == ForbiddenInstallation) throw new ProbeError("installation_binding_invalid");
                return id;
            }).ToArray();
            if (ids.Length != 2 || ids.Distinct().Count() != 2) throw new ProbeError("installation_binding_invalid");
            var actors = root.GetProperty("actors").EnumerateArray().Select(a =>
            {
                Keys(a, "label", "serviceName", "expectedSid", "targets");
                var label = Label(Text(a, "label")); var service = Text(a, "serviceName"); var sid = Text(a, "expectedSid");
                if (!ServiceRegex().IsMatch(service) || !SidRegex().IsMatch(sid) || sid.EndsWith("-500", StringComparison.Ordinal))
                    throw new ProbeError("actor_binding_invalid");
                _ = new SecurityIdentifier(sid);
                var targets = a.GetProperty("targets").EnumerateArray().Select(t =>
                {
                    Keys(t, "label", "path", "isDirectory", "readExpected");
                    var path = Text(t, "path"); ValidatePath(path, ids);
                    return new Target(Label(Text(t, "label")), path, t.GetProperty("isDirectory").GetBoolean(),
                        t.GetProperty("readExpected").GetBoolean());
                }).ToArray();
                if (targets.Length is < 3 or > 64 || targets.Select(t => t.Label).Distinct(StringComparer.Ordinal).Count() != targets.Length)
                    throw new ProbeError("targets_invalid");
                return new Actor(label, service, sid, targets);
            }).ToArray();
            if (actors.Length != 2 || actors.Select(a => a.Label).Distinct().Count() != 2 ||
                actors.Select(a => a.ServiceName).Distinct(StringComparer.OrdinalIgnoreCase).Count() != 2 ||
                actors.Select(a => a.ExpectedSid).Distinct().Count() != 2) throw new ProbeError("actors_invalid");
            return new Request(host, ids, actors);
        }
        catch (ProbeError) { throw; }
        catch (Exception ex) when (ex is JsonException or InvalidOperationException or ArgumentException or OverflowException or KeyNotFoundException or FormatException)
        { throw new ProbeError("input_invalid"); }
    }

    private static void Keys(JsonElement element, params string[] keys)
    {
        if (element.ValueKind != JsonValueKind.Object) throw new ProbeError("input_invalid");
        var names = element.EnumerateObject().Select(p => p.Name).ToArray();
        if (names.Length != keys.Length || names.Distinct(StringComparer.Ordinal).Count() != names.Length ||
            names.Except(keys, StringComparer.Ordinal).Any()) throw new ProbeError("input_invalid");
    }
    private static string Text(JsonElement element, string key)
    {
        var value = element.GetProperty(key).GetString();
        return string.IsNullOrEmpty(value) || value.Any(char.IsControl) ? throw new ProbeError("input_invalid") : value;
    }
    private static string Label(string value) => LabelRegex().IsMatch(value) ? value : throw new ProbeError("input_invalid");
    private static void ValidatePath(string path, Guid[] ids)
    {
        if (!Path.IsPathFullyQualified(path) || path.Length > 245 || path.Contains('/') || path.Contains(ForbiddenInstallation, StringComparison.OrdinalIgnoreCase) ||
            path[2..].Contains(':') || path.Split('\\').Any(p => p is "." or "..") || path.EndsWith('\\') ||
            !string.Equals(Path.GetFullPath(path), path, StringComparison.OrdinalIgnoreCase)) throw new ProbeError("target_scope_invalid");
        if (path.Equals(CommonRoot, StringComparison.OrdinalIgnoreCase) || path.Equals(Scope, StringComparison.OrdinalIgnoreCase)) return;
        if (!ids.Any(id => path.Equals(Scope + "\\" + id.ToString("D"), StringComparison.OrdinalIgnoreCase) ||
            path.StartsWith(Scope + "\\" + id.ToString("D") + "\\", StringComparison.OrdinalIgnoreCase)))
            throw new ProbeError("target_scope_invalid");
    }

    private static void Prewarm()
    {
        // Load all managed dependencies and JIT the actual opening path before impersonation.
        _ = JsonSerializer.Serialize(new RightResult("read", 1, false, false, 5), Json);
        using var identity = WindowsIdentity.GetCurrent(); _ = identity.Groups?.Count;
        using var temp = Native.CreateFileW(@"C:\", 0x80, 7, IntPtr.Zero, 3, 0x02200000, IntPtr.Zero);
        _ = Open(@"C:\", true, "warmup", 0x80, true);
        _ = MeasureTarget(new Target("warmup", @"C:\", true, true));
        _ = new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator);
    }

    private static ActorResult Measure(Actor actor)
    {
        var facts = ServiceFacts.Read(actor.ServiceName);
        if (facts.AccountSid != actor.ExpectedSid) throw new ProbeError("service_sid_mismatch");
        using var process = Native.OpenProcess(0x1000, false, facts.Pid);
        if (process.IsInvalid) throw new ProbeError("process_open_failed");
        var processStamp = Native.ProcessStamp(process);
        if (!facts.ImageMatches(process)) throw new ProbeError("process_binding_invalid");
        if (!Native.OpenProcessToken(process, 0x000A, out var original)) throw new ProbeError("token_open_failed");
        using (original)
        {
            if (!Native.DuplicateTokenEx(original, 0x000E, IntPtr.Zero, 2, 2, out var duplicate)) throw new ProbeError("token_duplicate_failed");
            using (duplicate)
            using (var identity = new WindowsIdentity(duplicate.DangerousGetHandle()))
            {
                var matched = identity.User?.Value == actor.ExpectedSid;
                var standard = matched && identity.Groups is not null &&
                    !identity.Groups.Any(g => g.Value == "S-1-5-32-544") && identity.User?.Value != "S-1-5-18";
                if (!standard) throw new ProbeError("standard_token_required");
                var prior = WindowsIdentity.GetCurrent().User?.Value;
                TargetResult[] targets = []; var impersonated = false;
                WindowsIdentity.RunImpersonated(duplicate, () =>
                {
                    using var effective = WindowsIdentity.GetCurrent();
                    impersonated = effective.User?.Value == actor.ExpectedSid;
                    if (!impersonated) throw new ProbeError("impersonation_failed");
                    targets = actor.Targets.Select(MeasureTarget).ToArray();
                });
                var restored = WindowsIdentity.GetCurrent().User?.Value == prior;
                if (!restored) throw new ProbeError("identity_restore_failed");
                var after = ServiceFacts.Read(actor.ServiceName);
                using var afterProcess = Native.OpenProcess(0x1000,false,after.Pid);
                var linked = after.Pid == facts.Pid && after.AccountSid == facts.AccountSid && !afterProcess.IsInvalid &&
                    Native.ProcessStamp(afterProcess) == processStamp && after.ImageMatches(afterProcess);
                return new ActorResult(actor.Label, linked, matched, standard, impersonated, restored, targets);
            }
        }
    }

    internal static TargetResult MeasureTarget(Target target)
    {
        var rights = new List<RightResult> { Open(target.Path, target.IsDirectory, "read_data_or_list", 1, target.ReadExpected) };
        foreach (var (name, mask) in new (string,uint)[] { ("write_data_or_add_file",2), ("append_or_add_directory",4),
                     ("write_ea",0x10), ("write_attributes",0x100), ("delete",0x10000), ("write_dac",0x40000), ("write_owner",0x80000) })
            rights.Add(Open(target.Path, target.IsDirectory, name, mask, false));
        if (target.IsDirectory) rights.Add(Open(target.Path, true, "delete_child", 0x40, false));
        return new TargetResult(target.Label, rights.ToArray());
    }
    internal static RightResult Open(string path, bool directory, string right, uint mask, bool expected)
    {
        using var file = Native.CreateFileW(path, mask, 7, IntPtr.Zero, 3, directory ? 0x02200000u : 0x00200000u, IntPtr.Zero);
        var error = file.IsInvalid ? Marshal.GetLastWin32Error() : 0;
        return new RightResult(right, mask, expected, !file.IsInvalid, error);
    }

    private static NodeSnapshot[] Snapshot(Request request)
    {
        var paths = new Dictionary<string,(string Label,bool Directory)>(StringComparer.OrdinalIgnoreCase);
        foreach (var target in request.Actors.SelectMany(a => a.Targets))
        {
            if (paths.TryGetValue(target.Path, out var previous) && previous.Directory != target.IsDirectory)
                throw new ProbeError("target_kind_conflict");
            paths.TryAdd(target.Path, (target.Label,target.IsDirectory));
            var ancestor = Path.GetDirectoryName(target.Path);
            while (ancestor is not null)
            {
                paths.TryAdd(ancestor, ("ancestor-" + paths.Count.ToString("D3"),true));
                ancestor=Path.GetDirectoryName(ancestor);
            }
        }
        return paths.OrderBy(p => p.Key,StringComparer.OrdinalIgnoreCase).Select(p =>
            SnapshotNode(p.Key,p.Value.Label,p.Value.Directory,request)).ToArray();
    }
    private static NodeSnapshot SnapshotNode(string path,string label,bool directory,Request request)
    {
        using var handle = Native.CreateFileW(path,0x20080,7,IntPtr.Zero,3,0x02200000,IntPtr.Zero);
        if(handle.IsInvalid || !Native.GetFileInformationByHandle(handle,out var info))throw new ProbeError("metadata_unreadable");
        if((info.Attributes & 0x400)!=0 || ((info.Attributes&0x10)!=0)!=directory || (!directory && info.Links!=1))throw new ProbeError("reparse_or_kind_invalid");
        var final=new StringBuilder(512);var size=Native.GetFinalPathNameByHandleW(handle,final,(uint)final.Capacity,0);
        if(size==0 || size>=final.Capacity)throw new ProbeError("path_binding_invalid");
        var actual=final.ToString();if(actual.StartsWith(@"\\?\",StringComparison.Ordinal))actual=actual[4..];
        if(!string.Equals(Path.GetFullPath(actual),Path.GetFullPath(path),StringComparison.OrdinalIgnoreCase))throw new ProbeError("path_binding_invalid");
        if(Native.GetSecurityInfo(handle,1,5,out _,out _,out _,out _,out var sd)!=0)throw new ProbeError("metadata_unreadable");
        RawSecurityDescriptor descriptor;
        try
        {
            var length=Native.GetSecurityDescriptorLength(sd);if(length is 0 or >65536)throw new ProbeError("metadata_invalid");
            var bytes=new byte[length];Marshal.Copy(sd,bytes,0,bytes.Length);descriptor=new RawSecurityDescriptor(bytes,0);
        }
        finally{Native.LocalFree(sd);}
        if(descriptor.DiscretionaryAcl is null)throw new ProbeError("null_dacl");
        var securityHash=Hash(Encoding.UTF8.GetBytes(descriptor.GetSddlForm(AccessControlSections.Owner|AccessControlSections.Access)));
        var aces=descriptor.DiscretionaryAcl.Cast<GenericAce>().Select(a=>
        {
            if(a is not QualifiedAce q)throw new ProbeError("unsupported_ace");
            var principal=q.SecurityIdentifier.Value switch
            {
                "S-1-5-18"=>"system","S-1-5-32-544"=>"administrators",_=>
                    request.Actors.FirstOrDefault(actor=>actor.ExpectedSid==q.SecurityIdentifier.Value)?.Label ?? "other",
            };
            return new AceFact(a.AceType.ToString(),q.AccessMask,(int)a.AceFlags,principal);
        }).ToArray();
        return new NodeSnapshot(label,directory,info.Attributes,info.Volume,((ulong)info.IndexHigh<<32)|info.IndexLow,
            info.Links,((ulong)info.SizeHigh<<32)|info.SizeLow,((ulong)info.WriteHigh<<32)|info.WriteLow,
            securityHash,(descriptor.ControlFlags&ControlFlags.DiscretionaryAclProtected)!=0,
            descriptor.Owner?.Value is "S-1-5-18" or "S-1-5-32-544",aces);
    }
    private static string Fingerprint(NodeSnapshot[] nodes)=>Hash(JsonSerializer.SerializeToUtf8Bytes(nodes,Json));
    private static string Hash(byte[] bytes)=>Convert.ToHexStringLower(SHA256.HashData(bytes));
    [GeneratedRegex("^[A-Za-z0-9-]{1,63}$",RegexOptions.CultureInvariant)]private static partial Regex HostRegex();
    [GeneratedRegex("^[a-zA-Z0-9_.-]{1,64}$",RegexOptions.CultureInvariant)]private static partial Regex LabelRegex();
    [GeneratedRegex("^RackClick[A-Za-z0-9_-]{0,80}$",RegexOptions.CultureInvariant)]private static partial Regex ServiceRegex();
    [GeneratedRegex("^S-1-5-21-(?:[0-9]+-){3}[0-9]+$",RegexOptions.CultureInvariant)]private static partial Regex SidRegex();
}
