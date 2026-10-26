#requires -Version 5.1
# Importing this helper only defines functions. It creates no users, services or privileges.
function Initialize-SetupChildProcessNative {
    if('RackClick.Setup.ChildProcessNative'-as[type]){return}
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
namespace RackClick.Setup {
    public static class ChildProcessNative {
        [DllImport("kernel32.dll", SetLastError=true)]
        public static extern SafeProcessHandle OpenProcess(uint access, bool inherit, int processId);
        [DllImport("kernel32.dll", SetLastError=true)]
        public static extern bool GetExitCodeProcess(SafeProcessHandle process, out uint exitCode);
        [DllImport("kernel32.dll", SetLastError=true)]
        public static extern uint WaitForSingleObject(SafeProcessHandle process, uint milliseconds);
        [DllImport("kernel32.dll", SetLastError=true)]
        public static extern bool GetProcessTimes(SafeProcessHandle process, out long created, out long exited, out long kernel, out long user);
    }
}
'@ -ErrorAction Stop
}
function Open-SetupChildProcess([int]$ProcessId) {
    Initialize-SetupChildProcessNative
    # QUERY_LIMITED_INFORMATION | SYNCHRONIZE; never PROCESS_ALL_ACCESS or debug privilege.
    $handle=[RackClick.Setup.ChildProcessNative]::OpenProcess(0x101000,$false,$ProcessId)
    if($handle.IsInvalid){$handle.Dispose();throw 'setup_child_process_handle_unavailable'}
    return $handle
}
function Get-SetupChildProcessStartUtc($Handle) {
    [long]$created=0;[long]$exited=0;[long]$kernel=0;[long]$user=0
    if(-not[RackClick.Setup.ChildProcessNative]::GetProcessTimes($Handle,[ref]$created,[ref]$exited,[ref]$kernel,[ref]$user)){throw 'setup_child_process_time_unavailable'}
    return [DateTime]::FromFileTimeUtc($created).ToString('o')
}
function Wait-SetupChildProcess($Handle,[int]$TimeoutSeconds) {
    if($TimeoutSeconds-lt0-or$TimeoutSeconds-gt900){throw 'setup_child_timeout_invalid'}
    $wait=[RackClick.Setup.ChildProcessNative]::WaitForSingleObject($Handle,[uint32]($TimeoutSeconds*1000))
    if($wait-eq258){return $false}
    if($wait-ne0){throw 'setup_child_process_wait_unavailable'}
    return $true
}
function Get-SetupChildProcessExitCode($Handle) {
    # An actual exit code259 is valid only when the held process handle is signalled.
    if([RackClick.Setup.ChildProcessNative]::WaitForSingleObject($Handle,0)-ne0){throw 'setup_child_process_not_exited'}
    [uint32]$nativeExitCode=0
    if(-not[RackClick.Setup.ChildProcessNative]::GetExitCodeProcess($Handle,[ref]$nativeExitCode)){throw 'setup_child_exit_code_unavailable'}
    return $nativeExitCode
}
function Read-SetupChildResult([string]$Path) {
    if(-not[IO.File]::Exists($Path)){throw 'setup_child_result_missing'}
    # Read at most1MiB plus one byte even if the file grows after opening it.
    $limit=1048576;$stream=[IO.File]::Open($Path,'Open','Read','ReadWrite');$memory=New-Object IO.MemoryStream
    try {
        $buffer=New-Object byte[] 8192
        while($memory.Length-le$limit){
            $read=$stream.Read($buffer,0,[int][Math]::Min($buffer.Length,$limit+1-$memory.Length))
            if($read-eq0){break};$memory.Write($buffer,0,$read)
        }
        if($memory.Length-gt$limit){throw 'setup_child_result_too_large'}
        $memory.Position=0;$reader=New-Object IO.StreamReader($memory,(New-Object Text.UTF8Encoding($false,$true)),$true)
        try{try{$text=$reader.ReadToEnd()}catch{throw 'setup_child_result_invalid'}}finally{$reader.Dispose()}
    } finally {$memory.Dispose();$stream.Dispose()}
    if([string]::IsNullOrWhiteSpace($text)){throw 'setup_child_result_missing'}
    $trimmed=$text.Trim()
    if(-not$trimmed.StartsWith('{',[StringComparison]::Ordinal)-or-not$trimmed.EndsWith('}',[StringComparison]::Ordinal)){throw 'setup_child_result_invalid'}
    try{$answer=$text|ConvertFrom-Json -ErrorAction Stop}catch{throw 'setup_child_result_invalid'}
    if($answer-isnot[pscustomobject]-or$answer.valid-isnot[bool]-or($answer.exitCode-isnot[int]-and$answer.exitCode-isnot[long])-or$answer.exitCode-lt0-or$answer.exitCode-gt[uint32]::MaxValue){throw 'setup_child_result_invalid'}
    return $answer
}
