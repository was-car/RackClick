# Native local control and per-request TLS pinning; no global callbacks or HTTP stop route.
if (-not ('RackClickLaunchNative' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Net.Security;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using Microsoft.Win32.SafeHandles;
public static class RackClickLaunchNative {
    [DllImport("kernel32.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetNamedPipeServerProcessId(SafePipeHandle handle, out uint id);
    public static int ServerProcessId(SafePipeHandle handle) {
        uint id;
        if (!GetNamedPipeServerProcessId(handle,out id) || id==0 || id>Int32.MaxValue)
            throw new Win32Exception(Marshal.GetLastWin32Error());
        return (int)id;
    }
    public static RemoteCertificateValidationCallback PinnedValidator(string expected) {
        if (expected==null || expected.Length!=64) throw new ArgumentException("Invalid certificate pin");
        expected=expected.ToLowerInvariant();
        return (sender,certificate,chain,errors) => {
            if (certificate==null || (errors & (SslPolicyErrors.RemoteCertificateNameMismatch | SslPolicyErrors.RemoteCertificateNotAvailable))!=SslPolicyErrors.None) return false;
            try {
                using (var cert=new X509Certificate2(certificate))
                using (var digest=SHA256.Create()) {
                    var now=DateTime.UtcNow;
                    if (now<cert.NotBefore.ToUniversalTime() || now>=cert.NotAfter.ToUniversalTime()) return false;
                    var actual=BitConverter.ToString(digest.ComputeHash(cert.RawData)).Replace("-","").ToLowerInvariant();
                    return String.Equals(actual,expected,StringComparison.Ordinal);
                }
            } catch { return false; }
        };
    }
}
'@
}

function Clear-LauncherInheritedConfiguration {
    # Environment names with ':' are legal on Windows but not in the private
    # process-request schema. Remove recognized config aliases from THIS
    # launcher process before descendants inherit them; no user/machine edits.
    $original=@{}
    foreach ($key in [Environment]::GetEnvironmentVariables().Keys) {
        if ([string]$key -match '^(?i:Kestrel|ConnectionStrings|Bootstrap|RackClick):' -or
            ([string]$key -like 'PG*' -and [string]$key -notmatch '^[a-zA-Z_][a-zA-Z0-9_]*$')) {
            $original[[string]$key]=[Environment]::GetEnvironmentVariable([string]$key,[EnvironmentVariableTarget]::Process)
            [Environment]::SetEnvironmentVariable([string]$key,$null,[EnvironmentVariableTarget]::Process)
        }
    }
    return $original
}

function Restore-LauncherInheritedConfiguration {
    param([hashtable]$Original)
    foreach ($key in $Original.Keys) {
        [Environment]::SetEnvironmentVariable([string]$key,[string]$Original[$key],[EnvironmentVariableTarget]::Process)
    }
}

function Invoke-LauncherControl {
    param([hashtable]$ApplicationHandle,[hashtable]$Control,[ValidateSet('probe','stop')][string]$Action,[int]$ConnectTimeoutMilliseconds=1000)
    $pipe=$null
    try {
        $pipe=New-Object IO.Pipes.NamedPipeClientStream('.', $Control.pipe, [IO.Pipes.PipeDirection]::InOut, [IO.Pipes.PipeOptions]::Asynchronous, [Security.Principal.TokenImpersonationLevel]::Identification)
        $pipe.Connect($ConnectTimeoutMilliseconds)
        $serverId=[RackClickLaunchNative]::ServerProcessId($pipe.SafePipeHandle)
        if (-not (Test-RackClickOwnedProcessMembership -Handle $ApplicationHandle -ProcessId $serverId)) { Stop-InstanceCheck 'application_control_owner_invalid' }
        # No nonce is sent until the server process is verified as belonging to this app's Job.
        $message=@{schemaVersion=1;action=$Action;token=$Control.token} | ConvertTo-Json -Compress
        $bytes=[Text.Encoding]::ASCII.GetBytes($message+"`n")
        $written=$pipe.WriteAsync($bytes,0,$bytes.Length)
        if (-not $written.Wait(2000)) { Stop-InstanceCheck 'application_control_timeout' }
        $written.GetAwaiter().GetResult()
        $deadline=[Diagnostics.Stopwatch]::StartNew();$buffer=New-Object byte[] 1;$answer=New-Object Collections.Generic.List[byte]
        while ($answer.Count -lt 128) {
            $remaining=2500-[int]$deadline.ElapsedMilliseconds
            if ($remaining -le 0) { Stop-InstanceCheck 'application_control_timeout' }
            $read=$pipe.ReadAsync($buffer,0,1)
            if (-not $read.Wait($remaining)) { Stop-InstanceCheck 'application_control_timeout' }
            if ($read.GetAwaiter().GetResult() -ne 1 -or $buffer[0] -gt 127 -or $buffer[0] -eq 13) { Stop-InstanceCheck 'application_control_ack_invalid' }
            if ($buffer[0] -eq 10) { break }
            $answer.Add($buffer[0])
        }
        if ($answer.Count -ge 128 -or $buffer[0] -ne 10) { Stop-InstanceCheck 'application_control_ack_invalid' }
        try { $reply=[Text.Encoding]::ASCII.GetString($answer.ToArray()) | ConvertFrom-Json } catch { Stop-InstanceCheck 'application_control_ack_invalid' }
        if ((($reply.PSObject.Properties.Name | Sort-Object)-join ',') -cne 'accepted,schemaVersion' -or $reply.schemaVersion -ne 1 -or $reply.accepted -isnot [bool]) { Stop-InstanceCheck 'application_control_ack_invalid' }
        if ($reply.accepted -ne ($Action -ceq 'stop')) { Stop-InstanceCheck 'application_control_ack_invalid' }
        # The server waits for EOF after its response. Dispose before waiting for host exit.
        return [bool]$reply.accepted
    } finally { if ($null -ne $pipe) { $pipe.Dispose() } }
}

function Stop-LauncherApplication {
    param([hashtable]$ApplicationHandle,[hashtable]$Control)
    if ($null -eq $Control) { Stop-RackClickOwnedProcess $ApplicationHandle;return $false }
    if ($ApplicationHandle.Process.HasExited) { Stop-InstanceCheck 'application_ended_before_control' }
    $accepted=Invoke-LauncherControl -ApplicationHandle $ApplicationHandle -Control $Control -Action stop
    if (-not $accepted -or -not $ApplicationHandle.Process.WaitForExit(20000)) { Stop-InstanceCheck 'application_graceful_stop_timeout' }
    if ($ApplicationHandle.Process.ExitCode -ne 0) { Stop-InstanceCheck 'application_graceful_exit_failed' }
    # Release the already-exited Job/controller. This is not a forced app termination.
    Stop-RackClickOwnedProcess $ApplicationHandle
    return $true
}
