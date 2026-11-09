using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security.Principal;
using System.Text;
using Microsoft.Win32.SafeHandles;

namespace RackClick.MfaAclProbe;

[SupportedOSPlatform("windows")]
internal sealed record ServiceFacts(uint Pid,string AccountSid,string CommandLine)
{
    internal static ServiceFacts Read(string name)
    {
        var scm=Native.OpenSCManagerW(null,null,1);
        if(scm==IntPtr.Zero)throw new ProbeError("scm_unavailable");
        try
        {
            var service=Native.OpenServiceW(scm,name,5);
            if(service==IntPtr.Zero)throw new ProbeError("service_unavailable");
            try
            {
                if(!Native.QueryServiceStatusEx(service,0,out var state,(uint)Marshal.SizeOf<Native.ServiceStatus>(),out _) ||
                    state.CurrentState!=4 || state.ProcessId==0)throw new ProbeError("service_not_running");
                _=Native.QueryServiceConfigW(service,IntPtr.Zero,0,out var needed);
                if(needed==0 || needed>65536 || Marshal.GetLastWin32Error()!=122)throw new ProbeError("service_config_invalid");
                var memory=Marshal.AllocHGlobal((int)needed);
                try
                {
                    if(!Native.QueryServiceConfigW(service,memory,needed,out _))throw new ProbeError("service_config_invalid");
                    var config=Marshal.PtrToStructure<Native.ServiceConfig>(memory);
                    var command=Marshal.PtrToStringUni(config.BinaryPath) ?? throw new ProbeError("service_config_invalid");
                    var account=Marshal.PtrToStringUni(config.StartName) ?? throw new ProbeError("service_config_invalid");
                    if(account.StartsWith(@".\",StringComparison.Ordinal))account=Environment.MachineName+account[1..];
                    SecurityIdentifier sid;
                    try{sid=(SecurityIdentifier)new NTAccount(account).Translate(typeof(SecurityIdentifier));}
                    catch(IdentityNotMappedException){throw new ProbeError("service_account_unknown");}
                    if(sid.Value is "S-1-5-18" or "S-1-5-32-544")throw new ProbeError("service_account_privileged");
                    return new ServiceFacts(state.ProcessId,sid.Value,command);
                }
                finally{Marshal.FreeHGlobal(memory);}
            }
            finally{Native.CloseServiceHandle(service);}
        }
        finally{Native.CloseServiceHandle(scm);}
    }
    internal bool ImageMatches(SafeProcessHandle process)
    {
        var image=new StringBuilder(1024);uint capacity=(uint)image.Capacity;
        if(!Native.QueryFullProcessImageNameW(process,0,image,ref capacity))throw new ProbeError("process_image_unreadable");
        var text=CommandLine.Trim();string binary;
        if(text.StartsWith('"'))
        {
            var end=text.IndexOf('"',1);if(end<=1)return false;binary=text[1..end];
        }
        else
        {
            var end=text.IndexOf(".exe",StringComparison.OrdinalIgnoreCase);if(end<0)return false;binary=text[..(end+4)];
        }
        return string.Equals(Path.GetFullPath(Environment.ExpandEnvironmentVariables(binary)),Path.GetFullPath(image.ToString()),StringComparison.OrdinalIgnoreCase);
    }
}

internal static class Native
{
    [StructLayout(LayoutKind.Sequential)]internal struct FileTime { public uint Low, High; }
    internal static ulong ProcessStamp(SafeProcessHandle process)
    {
        if(!GetProcessTimes(process,out var created,out _,out _,out _))throw new ProbeError("process_time_unreadable");
        return ((ulong)created.High<<32)|created.Low;
    }
    [StructLayout(LayoutKind.Sequential)]internal struct ServiceStatus
    {public uint ServiceType,CurrentState,ControlsAccepted,Win32ExitCode,ServiceExitCode,CheckPoint,WaitHint,ProcessId,ServiceFlags;}
    [StructLayout(LayoutKind.Sequential)]internal struct ServiceConfig
    {public uint ServiceType,StartType,ErrorControl;public IntPtr BinaryPath,LoadGroup;public uint Tag;public IntPtr Dependencies,StartName,DisplayName;}
    // FILETIME is two DWORDs (4-byte alignment), not long fields that shift nNumberOfLinks.
    [StructLayout(LayoutKind.Sequential)]internal struct FileInfo
    {public uint Attributes,CreatedLow,CreatedHigh,AccessLow,AccessHigh,WriteLow,WriteHigh,Volume,SizeHigh,SizeLow,Links,IndexHigh,IndexLow;}

    [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)]internal static extern IntPtr OpenSCManagerW(string? machine,string? database,uint access);
    [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)]internal static extern IntPtr OpenServiceW(IntPtr scm,string name,uint access);
    [DllImport("advapi32.dll",SetLastError=true)][return:MarshalAs(UnmanagedType.Bool)]internal static extern bool QueryServiceStatusEx(IntPtr service,int level,out ServiceStatus status,uint size,out uint needed);
    [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)][return:MarshalAs(UnmanagedType.Bool)]internal static extern bool QueryServiceConfigW(IntPtr service,IntPtr config,uint size,out uint needed);
    [DllImport("advapi32.dll")][return:MarshalAs(UnmanagedType.Bool)]internal static extern bool CloseServiceHandle(IntPtr handle);
    [DllImport("kernel32.dll",SetLastError=true)]internal static extern SafeProcessHandle OpenProcess(uint access,[MarshalAs(UnmanagedType.Bool)]bool inherit,uint pid);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)][return:MarshalAs(UnmanagedType.Bool)]internal static extern bool QueryFullProcessImageNameW(SafeProcessHandle process,uint flags,StringBuilder image,ref uint size);
    [DllImport("kernel32.dll",SetLastError=true)][return:MarshalAs(UnmanagedType.Bool)]internal static extern bool GetProcessTimes(SafeProcessHandle process,out FileTime created,out FileTime exit,out FileTime kernel,out FileTime user);
    [DllImport("advapi32.dll",SetLastError=true)][return:MarshalAs(UnmanagedType.Bool)]internal static extern bool OpenProcessToken(SafeProcessHandle process,uint access,out SafeAccessTokenHandle token);
    [DllImport("advapi32.dll",SetLastError=true)][return:MarshalAs(UnmanagedType.Bool)]internal static extern bool DuplicateTokenEx(SafeAccessTokenHandle token,uint access,IntPtr attributes,int level,int type,out SafeAccessTokenHandle duplicate);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]internal static extern SafeFileHandle CreateFileW(string path,uint access,uint share,IntPtr attributes,uint disposition,uint flags,IntPtr template);
    [DllImport("kernel32.dll",SetLastError=true)][return:MarshalAs(UnmanagedType.Bool)]internal static extern bool GetFileInformationByHandle(SafeFileHandle handle,out FileInfo information);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]internal static extern uint GetFinalPathNameByHandleW(SafeFileHandle handle,StringBuilder name,uint size,uint flags);
    [DllImport("advapi32.dll",SetLastError=true)]internal static extern uint GetSecurityInfo(SafeFileHandle handle,uint type,uint information,out IntPtr owner,out IntPtr group,out IntPtr dacl,out IntPtr sacl,out IntPtr descriptor);
    [DllImport("advapi32.dll")]internal static extern uint GetSecurityDescriptorLength(IntPtr descriptor);
    [DllImport("kernel32.dll")]internal static extern IntPtr LocalFree(IntPtr memory);
}
