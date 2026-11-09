using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text.Json;

namespace RackClick.MfaAclProbe;

[SupportedOSPlatform("windows")]
internal static class SelfTest
{
    internal static int Run()
    {
        var results=new List<object>();var passed=0;var failed=0;
        void Case(string name,Action action)
        {
            try{action();passed++;results.Add(new{name,passed=true});}
            catch{failed++;results.Add(new{name,passed=false});}
        }
        void Require(bool condition){if(!condition)throw new InvalidOperationException();}
        var id1="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";var id2="11111111-2222-3333-4444-555555555555";
        var sample=JsonSerializer.Serialize(new{schemaVersion=1,expectedHost="TEST-E",installationIds=new[]{id1,id2},actors=new[]{
            new{label="first",serviceName="RackClick",expectedSid="S-1-5-21-1-2-3-1001",targets=Enumerable.Range(1,3).Select(i=>new{label="item"+i,path=Probe.Scope+"\\"+id1,isDirectory=true,readExpected=true}).ToArray()},
            new{label="second",serviceName="RackClickRestore",expectedSid="S-1-5-21-1-2-3-1002",targets=Enumerable.Range(1,3).Select(i=>new{label="item"+i,path=Probe.Scope+"\\"+id2,isDirectory=true,readExpected=false}).ToArray()}}});
        void Reject(string value){try{Probe.Parse(value);}catch(ProbeError){return;}throw new InvalidOperationException();}
        Case("native_information_layout",()=>Require(Marshal.SizeOf<Native.FileInfo>()==52 && Marshal.OffsetOf<Native.FileInfo>(nameof(Native.FileInfo.Links)).ToInt32()==40));
        Case("request_valid",()=>Require(Probe.Parse(sample).Actors.Length==2));
        Case("request_D_rejected",()=>Reject(sample.Replace(id1,Probe.ForbiddenInstallation,StringComparison.Ordinal)));
        Case("request_traversal_rejected",()=>Reject(sample.Replace(id1+"\"",id1+"\\\\..\\\\other\"",StringComparison.Ordinal)));
        Case("request_extra_rejected",()=>Reject(sample.Replace("\"schemaVersion\":1","\"schemaVersion\":1,\"extra\":true",StringComparison.Ordinal)));
        Case("request_duplicate_rejected",()=>Reject(sample.Replace("\"schemaVersion\":1","\"schemaVersion\":1,\"schemaVersion\":1",StringComparison.Ordinal)));
        Case("request_surrogate_rejected",()=>Reject(sample.Replace("TEST-E","\\uD800",StringComparison.Ordinal)));
        Case("request_bad_json_rejected",()=>Reject("{"));
        Case("access_denial_only_error5",()=>Require(new RightResult("read",1,false,false,5).Passed && !new RightResult("read",1,false,false,2).Passed));
        Case("unexpected_grant_detected",()=>Require(!new RightResult("write",2,false,true,0).Passed));

        var root=Path.Combine(Path.GetTempPath(),"rackclick-f0402-probe-"+Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try
        {
            var file=Path.Combine(root,"synthetic.txt");File.WriteAllText(file,"synthetic");
            var before=File.ReadAllBytes(file);
            Case("native_read_open_no_content_read",()=>Require(Probe.Open(file,false,"read",1,true).Passed));
            var me=WindowsIdentity.GetCurrent().User!;
            var acl=new FileSecurity();acl.SetAccessRuleProtection(true,false);
            acl.AddAccessRule(new FileSystemAccessRule(me,FileSystemRights.WriteData,AccessControlType.Deny));
            acl.AddAccessRule(new FileSystemAccessRule(me,FileSystemRights.FullControl,AccessControlType.Allow));
            new FileInfo(file).SetAccessControl(acl);
            Case("native_write_open_denied",()=>Require(Probe.Open(file,false,"write",2,false).Passed));
            Case("native_missing_not_denial",()=>Require(!Probe.Open(Path.Combine(root,"absent"),false,"read",1,false).Passed));
            Case("token_self_impersonation_restores",()=>
            {
                using var process=Native.OpenProcess(0x1000,false,(uint)Environment.ProcessId);
                Require(Native.OpenProcessToken(process,0xA,out var source));
                using(source)
                {
                    Require(Native.DuplicateTokenEx(source,0xE,IntPtr.Zero,2,2,out var token));
                    using(token)
                    {
                        var inside=false;
                        WindowsIdentity.RunImpersonated(token,()=>inside=WindowsIdentity.GetCurrent().User==me && Probe.Open(file,false,"write",2,false).Passed);
                        Require(inside && WindowsIdentity.GetCurrent().User==me);
                    }
                }
            });
            Case("fixture_content_unchanged",()=>Require(before.SequenceEqual(File.ReadAllBytes(file))));
        }
        finally
        {
            var full=Path.GetFullPath(root);var parent=Path.GetFullPath(Path.GetTempPath()).TrimEnd('\\')+"\\";
            if(!full.StartsWith(parent,StringComparison.OrdinalIgnoreCase)||!Path.GetFileName(full).StartsWith("rackclick-f0402-probe-",StringComparison.Ordinal))throw new ProbeError("unsafe_selftest_cleanup");
            Directory.Delete(full,true);
        }
        Console.WriteLine(JsonSerializer.Serialize(new{schemaVersion=1,status=failed==0?"passed":"failed",mode="selftest",passed,failed,results,
            serviceOperations=0,vmOperations=0,fixtureOnly=true,notRealServiceAcceptance=true}));
        return failed==0?0:1;
    }
}
