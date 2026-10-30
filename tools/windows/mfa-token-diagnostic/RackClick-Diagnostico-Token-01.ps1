#requires -Version 5.1
# Read-only diagnosis. No key access, token duplication, impersonation or privilege changes.
[CmdletBinding()]
param(
    [switch]$SelfTest,
    [ValidatePattern('^RackClick[A-Za-z0-9_.-]{0,200}$')][string]$ServiceName = 'RackClick'
)
$ErrorActionPreference = 'Stop'
try {
    if (-not $SelfTest -and $env:COMPUTERNAME -ieq 'LEAO') { throw 'host_excluded' }
    Add-Type -TypeDefinition @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

namespace RackClick.TokenDiagnostic01
{
    public sealed class OpenResult { public bool opened; public int win32Error; }
    public sealed class PrivilegeResult { public bool present; public bool enabled; public int win32Error; }
    public sealed class Result
    {
        public bool processOpened;
        public bool processLinked;
        public int processError;
        public string code = "";
        public PrivilegeResult debugPrivilege;
        public PrivilegeResult impersonatePrivilege;
        public OpenResult query;
        public OpenResult duplicate;
        public OpenResult combined;
    }
    public static class Native
    {
        [StructLayout(LayoutKind.Sequential)] private struct Luid { public uint Low; public int High; }
        [DllImport("kernel32.dll", SetLastError=true)] private static extern IntPtr OpenProcess(uint access, bool inherit, uint pid);
        [DllImport("kernel32.dll", SetLastError=true)] private static extern bool CloseHandle(IntPtr handle);
        [DllImport("kernel32.dll")] private static extern IntPtr GetCurrentProcess();
        [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
        private static extern bool QueryFullProcessImageNameW(IntPtr process, uint flags, StringBuilder path, ref uint size);
        [DllImport("advapi32.dll", SetLastError=true)]
        private static extern bool OpenProcessToken(IntPtr process, uint access, out IntPtr token);
        [DllImport("advapi32.dll", SetLastError=true)]
        private static extern bool GetTokenInformation(IntPtr token, int informationClass, IntPtr info, uint bytes, out uint needed);
        [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
        private static extern bool LookupPrivilegeValueW(string system, string name, out Luid luid);

        private static OpenResult OpenOnly(IntPtr process, uint access)
        {
            IntPtr token;
            bool ok = OpenProcessToken(process, access, out token);
            int error = ok ? 0 : Marshal.GetLastWin32Error();
            if (ok) CloseHandle(token);
            return new OpenResult { opened=ok, win32Error=error };
        }
        private static PrivilegeResult Privilege(string name)
        {
            var result = new PrivilegeResult();
            IntPtr token;
            if (!OpenProcessToken(GetCurrentProcess(), 0x8, out token))
            { result.win32Error=Marshal.GetLastWin32Error(); return result; }
            IntPtr buffer=IntPtr.Zero;
            try
            {
                Luid luid;
                if (!LookupPrivilegeValueW(null, name, out luid))
                { result.win32Error=Marshal.GetLastWin32Error(); return result; }
                uint needed;
                bool sized=GetTokenInformation(token, 3, IntPtr.Zero, 0, out needed);
                int sizeError=sized ? 0 : Marshal.GetLastWin32Error();
                if (sizeError!=122 || needed<4 || needed>1048576)
                { result.win32Error=sizeError==0 ? -1 : sizeError; return result; }
                buffer=Marshal.AllocHGlobal((int)needed);
                if (!GetTokenInformation(token, 3, buffer, needed, out needed))
                { result.win32Error=Marshal.GetLastWin32Error(); return result; }
                int count=Marshal.ReadInt32(buffer);
                if (count<0 || 4L+12L*count>needed) { result.win32Error=-1; return result; }
                for(int i=0;i<count;i++)
                {
                    int offset=4+12*i;
                    if(unchecked((uint)Marshal.ReadInt32(buffer,offset))==luid.Low && Marshal.ReadInt32(buffer,offset+4)==luid.High)
                    { result.present=true; result.enabled=(Marshal.ReadInt32(buffer,offset+8)&2)!=0; break; }
                }
                return result;
            }
            finally { if(buffer!=IntPtr.Zero)Marshal.FreeHGlobal(buffer); CloseHandle(token); }
        }
        public static Result Measure(uint pid, string expectedImage)
        {
            var result=new Result { debugPrivilege=Privilege("SeDebugPrivilege"), impersonatePrivilege=Privilege("SeImpersonatePrivilege") };
            IntPtr process=OpenProcess(0x1400, false, pid);
            if(process==IntPtr.Zero)
            { result.processError=Marshal.GetLastWin32Error(); result.code="process_open_failed"; return result; }
            result.processOpened=true;
            try
            {
                var image=new StringBuilder(32768); uint size=(uint)image.Capacity;
                if(!QueryFullProcessImageNameW(process,0,image,ref size))
                { result.processError=Marshal.GetLastWin32Error(); result.code="process_image_unavailable"; return result; }
                result.processLinked=String.Equals(image.ToString(),expectedImage,StringComparison.OrdinalIgnoreCase);
                if(!result.processLinked) { result.code="process_image_mismatch"; return result; }
                result.query=OpenOnly(process,0x8);
                result.duplicate=OpenOnly(process,0x2);
                result.combined=OpenOnly(process,0xA);
                return result;
            }
            finally { CloseHandle(process); }
        }
        public static Result Own()
        {
            using(var p=Process.GetCurrentProcess()) return Measure((uint)p.Id,p.MainModule.FileName);
        }
        public static OpenResult InvalidHandleControl() { return OpenOnly(new IntPtr(0x7ffffffe),0x8); }
    }
}
'@
    if ($SelfTest) {
        $own = [RackClick.TokenDiagnostic01.Native]::Own()
        $invalid = [RackClick.TokenDiagnostic01.Native]::InvalidHandleControl()
        $pass = $own.processLinked -and $own.query.opened -and $own.duplicate.opened -and $own.combined.opened -and
            -not $invalid.opened -and $invalid.win32Error -eq 6
        [ordered]@{schemaVersion=1;mode='selftest';passed=[bool]$pass;own=$own;invalidHandle=$invalid;serviceAccessed=$false;keysRead=$false;privilegesChanged=$false} | ConvertTo-Json -Depth 6 -Compress
        if (-not $pass) { exit 1 }
        exit 0
    }
    $services = @(Get-CimInstance -ClassName Win32_Service -Filter ("Name = '" + $ServiceName + "'"))
    if ($services.Count -ne 1) { throw 'service_not_found' }
    $service = $services[0]
    if ($service.State -ne 'Running' -or [uint32]$service.ProcessId -eq 0) { throw 'service_not_running' }
    $command = ([string]$service.PathName).Trim()
    if ($command.StartsWith('"')) {
        $end = $command.IndexOf('"',1)
        if ($end -le 1) { throw 'service_image_invalid' }
        $image = $command.Substring(1,$end-1)
    } else {
        $end = $command.IndexOf('.exe',[StringComparison]::OrdinalIgnoreCase)
        if ($end -lt 1) { throw 'service_image_invalid' }
        $image = $command.Substring(0,$end+4)
    }
    $image = [IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($image))
    $measurement = [RackClick.TokenDiagnostic01.Native]::Measure([uint32]$service.ProcessId,$image)
    [ordered]@{schemaVersion=1;mode='diagnostic';status='measured';measurement=$measurement;tokenDuplicated=$false;impersonationPerformed=$false;keysRead=$false;privilegesChanged=$false;storeWritten=$false;reportsWritten=$false} | ConvertTo-Json -Depth 6 -Compress
    if ($measurement.code) { exit 1 }
    exit 0
} catch {
    $code = 'diagnostic_failed'
    if ($_.Exception.Message -in @('host_excluded','service_not_found','service_not_running','service_image_invalid')) { $code = $_.Exception.Message }
    [ordered]@{schemaVersion=1;status='rejected';code=$code;keysRead=$false;privilegesChanged=$false;storeWritten=$false;reportsWritten=$false} | ConvertTo-Json -Compress
    exit 1
}
