#requires -Version 5.1
<# Request a stop for the current run ID only. Launcher confirms actual shutdown.
   No PID lookup, process-name selection or service control.
#>
[CmdletBinding()]
param([string]$InstancePath='',[string]$ExpectedInstanceSha256='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
$stopInputs=@{path=$InstancePath;sha=$ExpectedInstanceSha256}
. (Join-Path $PSScriptRoot 'RackClick.Instance.ps1')

function Read-RackClickActiveRunRecord {
    param([string]$Path)
    Assert-RackClickProcessPrivateAcl $Path
    $stream=$null; $reader=$null
    try {
        # Keep a consistent old snapshot while allowing the launcher to atomically replace it.
        $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::Read -bor [IO.FileShare]::Delete))
        if ($stream.Length -gt 16384) { Stop-InstanceCheck 'active_run_invalid' }
        $reader=New-Object IO.StreamReader($stream,[Text.Encoding]::UTF8,$true)
        return ($reader.ReadToEnd() | ConvertFrom-Json)
    } finally {
        if ($null -ne $reader) { $reader.Dispose() } elseif ($null -ne $stream) { $stream.Dispose() }
    }
}

function Publish-RackClickStopRequest {
    param([string]$Directory,[string]$RunId,[string]$InstanceId)
    Assert-RackClickProcessPrivateAcl $Directory
    $requestPath=Join-Path $Directory 'stop-request.json'
    function Confirm-ExistingStopRequest {
        Assert-RackClickProcessPrivateAcl $requestPath
        try { $existing=[IO.File]::ReadAllText($requestPath) | ConvertFrom-Json }
        catch { Stop-InstanceCheck 'stop_request_invalid' }
        if ($existing.schemaVersion -ne 1 -or $existing.runId -cne $RunId -or $existing.instanceId -cne $InstanceId) { Stop-InstanceCheck 'stop_request_invalid' }
        return 'stop_already_requested'
    }
    if ([IO.File]::Exists($requestPath)) { return (Confirm-ExistingStopRequest) }
    $temporary=Join-Path $Directory ('stop-request-'+[guid]::NewGuid().ToString('N')+'.tmp')
    $stream=$null
    try {
        $request=@{schemaVersion=1;runId=$RunId;instanceId=$InstanceId}
        $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($request | ConvertTo-Json -Compress))
        $stream=[IO.File]::Open($temporary,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true); $stream.Dispose(); $stream=$null
        Assert-RackClickProcessPrivateAcl $temporary
        # Same private directory/volume: final name appears only after the writer is closed.
        # Move never overwrites; a concurrent winner must contain precisely this run identity.
        try { [IO.File]::Move($temporary,$requestPath) }
        catch [IO.IOException] {
            if ([IO.File]::Exists($requestPath)) { return (Confirm-ExistingStopRequest) }
            Stop-InstanceCheck 'stop_request_publish_failed'
        }
        return 'stop_requested'
    } finally { if ($null -ne $stream) { $stream.Dispose() } }
}

$instance=$null
$report=[ordered]@{schemaVersion=1;valid=$false;exitCode=2;code='stop_request_failed';runId='';instanceId='';scope='Stop requested only; wait for launcher stopped event to confirm'}
try {
    $instance=Read-RackClickInstance -InstancePath $stopInputs.path -ExpectedInstanceSha256 $stopInputs.sha
    $report.instanceId=$instance.id
    $activePath=Join-Path $instance.logRoot 'active-run.json'
    if (-not [IO.File]::Exists($activePath)) { Stop-InstanceCheck 'no_active_launcher' 1 }
    $active=Read-RackClickActiveRunRecord -Path $activePath
    $runId=[guid]::ParseExact($active.runId,'D').ToString('D')
    if ($active.schemaVersion -ne 1 -or $active.instanceId -cne $instance.id -or $active.status -notin @('starting','ready') -or $active.runId -cne $runId -or $active.requestRelativePath -cne ('launcher-'+$runId+'/stop-request.json')) { Stop-InstanceCheck 'no_active_launcher' 1 }
    # A free lock means an old run record, not a currently owned controller.
    $free=$null; $inUse=$false
    try { $free=[IO.File]::Open($instance.lockPath,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None) }
    catch [IO.IOException] { $inUse=(($_.Exception.HResult -band 0xffff) -in @(32,33)) }
    finally { if ($null -ne $free) { $free.Dispose() } }
    if (-not $inUse) { Stop-InstanceCheck 'no_active_launcher' 1 }
    $directory=Join-Path $instance.logRoot ('launcher-'+$runId)
    Assert-RackClickProcessPrivateAcl $directory
    $report.code=Publish-RackClickStopRequest -Directory $directory -RunId $runId -InstanceId $instance.id
    $report.runId=$runId; $report.valid=$true; $report.exitCode=0
} catch {
    if ($_.Exception.Data.Contains('instanceCode')) { $report.code=$_.Exception.Data['instanceCode']; $report.exitCode=$_.Exception.Data['instanceExit'] }
    elseif ($_.Exception.Data.Contains('code')) { $report.code=$_.Exception.Data['code']; $report.exitCode=$_.Exception.Data['exitCode'] }
} finally {
    if ($null -ne $instance) { Close-RackClickInstance -Instance $instance }
}
$report | ConvertTo-Json -Compress
exit $report.exitCode
