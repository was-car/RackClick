#requires -Version 5.1
# Private, owned process trees. Importing defines functions only; no child is started.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

function Stop-RackClickProcessError {
    param([string]$Code)
    $failure=New-Object InvalidOperationException($Code)
    $failure.Data['code']=$Code; $failure.Data['exitCode']=2
    throw $failure
}

function Get-RackClickProcessPath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path) -or $Path -notmatch '^[A-Za-z]:[\\/]' -or $Path.Substring(2).Contains(':')) { Stop-RackClickProcessError 'process_path_invalid' }
    foreach ($part in $Path.Substring(3).Split([char[]]@('\','/'))) {
        if ($part.Length -eq 0) { continue }
        if ($part -in @('.','..') -or $part.Contains('~') -or $part.EndsWith('.') -or $part.EndsWith(' ') -or $part.IndexOfAny([IO.Path]::GetInvalidFileNameChars()) -ge 0 -or $part -match '^(?i:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\..*)?$') { Stop-RackClickProcessError 'process_path_invalid' }
    }
    $full=[IO.Path]::GetFullPath($Path).TrimEnd('\')
    if ($full.Length -le 2 -or (New-Object IO.DriveInfo($full.Substring(0,3))).DriveType -ne [IO.DriveType]::Fixed) { Stop-RackClickProcessError 'process_path_invalid' }
    return $full
}

function Assert-RackClickProcessNoReparse {
    param([string]$Path)
    $item=Get-Item -LiteralPath $Path -Force
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { Stop-RackClickProcessError 'process_reparse_rejected' }
        if ($item -is [IO.FileInfo]) { $item=$item.Directory } else { $item=$item.Parent }
    }
}

function Assert-RackClickProcessPrivateAcl {
    param([string]$Path)
    $Path=Get-RackClickProcessPath $Path
    Assert-RackClickProcessNoReparse $Path
    if ([IO.Directory]::Exists($Path)) { $acl=[IO.Directory]::GetAccessControl($Path) } else { $acl=[IO.File]::GetAccessControl($Path) }
    $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin @($sid,'S-1-5-18')) { Stop-RackClickProcessError 'process_private_acl_required' }
    $found=$false
    foreach ($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -eq [Security.AccessControl.AccessControlType]::Allow) {
            if ($rule.IdentityReference.Value -notin @($sid,'S-1-5-18')) { Stop-RackClickProcessError 'process_private_acl_required' }
            if ($rule.IdentityReference.Value -eq $sid) { $found=$true }
        }
    }
    if (-not $found) { Stop-RackClickProcessError 'process_private_acl_required' }
}

function Initialize-RackClickProcessNative {
    if ('RackClick.OwnedProcessNative' -as [type]) { return }
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace RackClick {
 public static class OwnedProcessNative {
  [StructLayout(LayoutKind.Sequential)] public struct BasicLimits {
   public long PerProcessUserTimeLimit, PerJobUserTimeLimit; public uint LimitFlags;
   public UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize; public uint ActiveProcessLimit;
   public UIntPtr Affinity; public uint PriorityClass, SchedulingClass;
  }
  [StructLayout(LayoutKind.Sequential)] public struct IoCounters {
   public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount, ReadTransferCount, WriteTransferCount, OtherTransferCount;
  }
  [StructLayout(LayoutKind.Sequential)] public struct ExtendedLimits {
   public BasicLimits BasicLimitInformation; public IoCounters IoInfo;
   public UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed;
  }
  [StructLayout(LayoutKind.Sequential)] struct SecurityAttributes { public int Length; public IntPtr Descriptor; public int Inherit; }
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] public static extern IntPtr CreateJobObject(IntPtr attributes, string name);
  [DllImport("kernel32.dll", SetLastError=true)] [return: MarshalAs(UnmanagedType.Bool)] public static extern bool SetInformationJobObject(IntPtr job, int information, ref ExtendedLimits limits, uint size);
  [DllImport("kernel32.dll", SetLastError=true)] [return: MarshalAs(UnmanagedType.Bool)] public static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
  [DllImport("kernel32.dll", SetLastError=true)] [return: MarshalAs(UnmanagedType.Bool)] public static extern bool CloseHandle(IntPtr handle);
  [DllImport("kernel32.dll", SetLastError=true)] public static extern IntPtr OpenProcess(uint access, [MarshalAs(UnmanagedType.Bool)] bool inherit, uint id);
  [DllImport("kernel32.dll", SetLastError=true)] [return: MarshalAs(UnmanagedType.Bool)] public static extern bool IsProcessInJob(IntPtr process, IntPtr job, [MarshalAs(UnmanagedType.Bool)] out bool result);
  [DllImport("kernel32.dll", EntryPoint="CreateDirectoryW", CharSet=CharSet.Unicode, SetLastError=true)] [return: MarshalAs(UnmanagedType.Bool)] static extern bool CreateDirectory(string path, ref SecurityAttributes security);
  public static int CreatePrivateDirectory(string path, byte[] descriptor) {
   var pin=GCHandle.Alloc(descriptor,GCHandleType.Pinned);
   try { var attributes=new SecurityAttributes { Length=Marshal.SizeOf(typeof(SecurityAttributes)), Descriptor=pin.AddrOfPinnedObject(), Inherit=0 };
    return CreateDirectory(path,ref attributes) ? 0 : Marshal.GetLastWin32Error();
   } finally { pin.Free(); }
  }
 }
}
'@
}

function New-RackClickProcessPrivateDirectory {
    param([string]$Path)
    $Path=Get-RackClickProcessPath $Path
    $parent=[IO.Path]::GetDirectoryName($Path)
    if (-not [IO.Directory]::Exists($parent)) { Stop-RackClickProcessError 'process_parent_missing' }
    Assert-RackClickProcessNoReparse $parent
    $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
    $acl=New-Object Security.AccessControl.DirectorySecurity
    $acl.SetOwner($sid); $acl.SetAccessRuleProtection($true,$false)
    foreach ($identity in @($sid,(New-Object Security.Principal.SecurityIdentifier('S-1-5-18')))) {
        $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($identity,'FullControl','ContainerInherit,ObjectInherit','None','Allow')))
    }
    Initialize-RackClickProcessNative
    $result=[RackClick.OwnedProcessNative]::CreatePrivateDirectory($Path,$acl.GetSecurityDescriptorBinaryForm())
    if ($result -ne 0) { Stop-RackClickProcessError 'process_private_directory_create_failed' }
    Assert-RackClickProcessPrivateAcl $Path
    return $Path
}

function ConvertTo-RackClickProcessArgument {
    param([AllowEmptyString()][string]$Value)
    if ($Value.Contains([string][char]0)) { Stop-RackClickProcessError 'process_argument_invalid' }
    $escaped=[regex]::Replace($Value,'(\\*)"','$1$1\"')
    $escaped=[regex]::Replace($escaped,'(\\+)$','$1$1')
    return '"'+$escaped+'"'
}

function Start-RackClickOwnedProcess {
    param([string]$Executable,[string[]]$Arguments=@(),[string]$WorkingDirectory,[hashtable]$Environment=@{},[AllowEmptyString()][string]$InputText='',[string]$LogDirectory,[string]$Label)
    $Executable=Get-RackClickProcessPath $Executable; $WorkingDirectory=Get-RackClickProcessPath $WorkingDirectory; $LogDirectory=Get-RackClickProcessPath $LogDirectory
    if (-not [IO.File]::Exists($Executable) -or -not [IO.Directory]::Exists($WorkingDirectory) -or -not [IO.Directory]::Exists($LogDirectory) -or $Label -notmatch '^[a-zA-Z0-9_-]{1,48}$') { Stop-RackClickProcessError 'process_input_invalid' }
    Assert-RackClickProcessNoReparse $Executable; Assert-RackClickProcessNoReparse $WorkingDirectory; Assert-RackClickProcessPrivateAcl $LogDirectory
    foreach ($key in $Environment.Keys) { if ($key -notmatch '^[a-zA-Z_][a-zA-Z0-9_]*$' -or ($null -ne $Environment[$key] -and $Environment[$key] -isnot [string])) { Stop-RackClickProcessError 'process_environment_invalid' } }
    foreach ($argument in $Arguments) { $null=ConvertTo-RackClickProcessArgument $argument }
    $private=New-RackClickProcessPrivateDirectory (Join-Path $LogDirectory ($Label+'-'+[guid]::NewGuid().ToString('N')))
    $requestPath=Join-Path $private 'request.json'; $stdoutPath=Join-Path $private 'stdout.log'; $stderrPath=Join-Path $private 'stderr.log'
    $request=@{schemaVersion=1;executable=$Executable;arguments=@($Arguments);workingDirectory=$WorkingDirectory;environment=$Environment;inputText=$InputText}
    $stream=$null
    try {
        $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($request | ConvertTo-Json -Depth 8 -Compress))
        if ($bytes.Length -gt 16777216) { Stop-RackClickProcessError 'process_request_too_large' }
        $stream=[IO.File]::Open($requestPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true)
    } finally { if ($null -ne $stream) { $stream.Dispose() } }
    Assert-RackClickProcessPrivateAcl $requestPath
    Initialize-RackClickProcessNative
    $job=[RackClick.OwnedProcessNative]::CreateJobObject([IntPtr]::Zero,$null)
    if ($job -eq [IntPtr]::Zero) { Stop-RackClickProcessError 'owned_job_create_failed' }
    $process=$null; $assigned=$false
    try {
        $limits=New-Object RackClick.OwnedProcessNative+ExtendedLimits
        $basic=New-Object RackClick.OwnedProcessNative+BasicLimits
        $basic.LimitFlags=0x2000; $limits.BasicLimitInformation=$basic
        if (-not [RackClick.OwnedProcessNative]::SetInformationJobObject($job,9,[ref]$limits,[Runtime.InteropServices.Marshal]::SizeOf($limits))) { Stop-RackClickProcessError 'owned_job_limit_failed' }
        $start=New-Object Diagnostics.ProcessStartInfo
        $start.FileName=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
        $start.Arguments=(@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Join-Path $PSScriptRoot 'RackClick.Process.Gate.ps1'),'-RequestPath',$requestPath) | ForEach-Object { ConvertTo-RackClickProcessArgument $_ }) -join ' '
        $start.UseShellExecute=$false; $start.CreateNoWindow=$true; $start.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
        $start.RedirectStandardInput=$true; $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
        $process=New-Object Diagnostics.Process; $process.StartInfo=$start
        if (-not $process.Start()) { Stop-RackClickProcessError 'owned_gate_start_failed' }
        $gateOut=$process.StandardOutput.ReadToEndAsync(); $gateErr=$process.StandardError.ReadToEndAsync()
        if (-not [RackClick.OwnedProcessNative]::AssignProcessToJobObject($job,$process.Handle)) { Stop-RackClickProcessError 'owned_job_assignment_failed' }
        $assigned=$true
        # The child cannot execute until assignment above succeeds. EOF without G exits.
        $process.StandardInput.BaseStream.WriteByte(71); $process.StandardInput.BaseStream.Flush(); $process.StandardInput.Close()
        return @{Process=$process;Job=$job;StdoutPath=$stdoutPath;StderrPath=$stderrPath;RequestPath=$requestPath;GateStdout=$gateOut;GateStderr=$gateErr}
    } catch {
        $null=[RackClick.OwnedProcessNative]::CloseHandle($job)
        if ($null -ne $process) {
            try { $process.StandardInput.Close() } catch {}
            if (-not $assigned -and -not $process.HasExited -and -not $process.WaitForExit(5000)) { $process.Kill() }
            $null=$process.WaitForExit(10000); $process.Dispose()
        }
        throw
    }
}

function Stop-RackClickOwnedProcess {
    param([hashtable]$Handle)
    if ($Handle.Job -ne [IntPtr]::Zero) {
        if (-not [RackClick.OwnedProcessNative]::CloseHandle($Handle.Job)) { Stop-RackClickProcessError 'owned_job_close_failed' }
        $Handle.Job=[IntPtr]::Zero
    }
    if (-not $Handle.Process.HasExited -and -not $Handle.Process.WaitForExit(10000)) { Stop-RackClickProcessError 'owned_stop_indeterminate' }
    if (-not $Handle.Process.HasExited) { Stop-RackClickProcessError 'owned_stop_indeterminate' }
}

function Test-RackClickOwnedProcessMembership {
    param([hashtable]$Handle,[int]$ProcessId)
    if ($ProcessId -le 0 -or $Handle.Job -eq [IntPtr]::Zero) { return $false }
    $queried=[RackClick.OwnedProcessNative]::OpenProcess(0x1000,$false,[uint32]$ProcessId)
    if ($queried -eq [IntPtr]::Zero) {
        if ([Runtime.InteropServices.Marshal]::GetLastWin32Error() -eq 87) { return $false }
        Stop-RackClickProcessError 'owned_membership_indeterminate'
    }
    try {
        $member=$false
        if (-not [RackClick.OwnedProcessNative]::IsProcessInJob($queried,$Handle.Job,[ref]$member)) { Stop-RackClickProcessError 'owned_membership_indeterminate' }
        return $member
    } finally { $null=[RackClick.OwnedProcessNative]::CloseHandle($queried) }
}

function Wait-RackClickOwnedProcess {
    param([hashtable]$Handle,[int]$TimeoutSeconds=120)
    if ($TimeoutSeconds -lt 1 -or $TimeoutSeconds -gt 86400) { Stop-RackClickProcessError 'owned_timeout_invalid' }
    $timedOut=-not $Handle.Process.WaitForExit($TimeoutSeconds*1000)
    $code=124
    if (-not $timedOut) { $code=$Handle.Process.ExitCode }
    Stop-RackClickOwnedProcess $Handle
    $stdout=''; $stderr=''
    if ([IO.File]::Exists($Handle.StdoutPath)) { $stdout=[IO.File]::ReadAllText($Handle.StdoutPath,[Text.Encoding]::UTF8) }
    if ([IO.File]::Exists($Handle.StderrPath)) { $stderr=[IO.File]::ReadAllText($Handle.StderrPath,[Text.Encoding]::UTF8) }
    if ($Handle.GateStderr.IsCompleted -and $Handle.GateStderr.Result.Length -gt 0 -and $code -eq 0) { $code=2 }
    return @{exitCode=$code;stdout=$stdout;stderr=$stderr}
}
