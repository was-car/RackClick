#requires -Version 5.1
<# Operate a private local deployment from its externally retained receipt hash.
   Start forwards native ready/stopped events; Stop confirms the exact run marker,
   free instance lock and closed ports. No SCM or process-name/PID termination.
#>
[CmdletBinding()]
param([string]$Operation='', [string]$DeploymentPath='', [string]$ExpectedDeploymentSha256='',
      [string]$BackupPath='', [int]$StopAfterSeconds=0, [int]$StopTimeoutSeconds=90)
$deploymentOperationInputs=@{operation=$Operation;path=$DeploymentPath;sha=$ExpectedDeploymentSha256;backup=$BackupPath;stopAfter=$StopAfterSeconds;stopTimeout=$StopTimeoutSeconds}
. (Join-Path $PSScriptRoot 'RackClick.Deployment.ps1')

function Read-DeploymentOperationRecord {
    param([string]$Path,[hashtable]$Deployment,[string]$ExpectedRunId='')
    $stream=$null
    try {
        # Pin this leaf before path metadata/ACL checks. FileShare.Delete allowed
        # File.Replace to remove it between Get-Item, GetAccessControl and Open.
        # The publisher already retries sharing violations; keep this read short.
        $opening=[Diagnostics.Stopwatch]::StartNew()
        while ($true) {
            try {
                $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
                break
            } catch [IO.IOException] {
                $cause=$_.Exception
                while ($null -ne $cause.InnerException) {$cause=$cause.InnerException}
                # Only opening races with replacement are transient. Schema,
                # identity, ACL and reparse failures below never enter this retry.
                if (($cause.HResult -band 0xffff) -notin @(2,3,32,33,303) -or $opening.ElapsedMilliseconds -ge 1000) {
                    Stop-PrivateDeploymentCheck 'deployment_run_record_unavailable'
                }
                Start-Sleep -Milliseconds 10
            }
        }
        Assert-RackClickProcessPrivateAcl $Path
        if ($stream.Length -gt 16384) { Stop-PrivateDeploymentCheck 'deployment_run_record_invalid' }
        $value=Read-DeploymentJson -Stream $stream -Code 'deployment_run_record_invalid'
        if ((($value.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'code,instanceId,publicOrigin,requestRelativePath,runId,schemaVersion,status,utc' -or
            $value.schemaVersion -isnot [int] -or $value.schemaVersion -ne 1 -or
            $value.instanceId -cne $Deployment.instance.id -or $value.runId -isnot [string] -or
            $value.runId -cnotmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$' -or
            $value.requestRelativePath -cne ('launcher-'+$value.runId+'/stop-request.json') -or
            $value.publicOrigin -cne ('https://127.0.0.1:'+[string]$Deployment.instance.httpPort) -or
            $value.status -cnotin @('starting','ready','stopped','failed') -or $value.code -isnot [string] -or $value.utc -isnot [string]) {
            Stop-PrivateDeploymentCheck 'deployment_run_record_invalid'
        }
        if ($ExpectedRunId.Length -gt 0 -and $value.runId -cne $ExpectedRunId) { Stop-PrivateDeploymentCheck 'deployment_active_run_changed' }
        return $value
    } finally {
        if ($null -ne $stream) {
            $stream.Dispose()
            # Leave a short unlocked scheduling window for the atomic publisher.
            # Wait-DeploymentStopped already polls at 100ms; this also bounds a
            # tight local reader loop without extending either retry deadline.
            Start-Sleep -Milliseconds 10
        }
    }
}

function Test-DeploymentInstanceLockFree {
    param([hashtable]$Instance)
    Assert-RackClickProcessPrivateAcl $Instance.lockPath
    $stream=$null
    try {
        $stream=[IO.File]::Open($Instance.lockPath,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
        return $true
    } catch [IO.IOException] {
        $cause=$_.Exception
        while ($null -ne $cause.InnerException) { $cause=$cause.InnerException }
        if (($cause.HResult -band 0xffff) -in @(32,33)) { return $false }
        Stop-PrivateDeploymentCheck 'deployment_instance_lock_indeterminate'
    } finally { if ($null -ne $stream) { $stream.Dispose() } }
}

function Test-DeploymentPortClosed {
    param([int]$Port)
    try { $listeners=[Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() }
    catch { Stop-PrivateDeploymentCheck 'deployment_tcp_snapshot_unavailable' }
    # Conservatively include all IPv4/IPv6 addresses and wildcard listeners.
    # This is a snapshot, used together with the run marker, free lock and PID-file absence.
    foreach ($endpoint in $listeners) { if ($endpoint.Port -eq $Port) { return $false } }
    return $true
}

function Wait-DeploymentStopped {
    param([hashtable]$Deployment,[string]$RunId,[int]$TimeoutSeconds)
    $instance=$Deployment.instance
    $recordPath=Join-Path (Join-Path $instance.logRoot ('launcher-'+$RunId)) 'run-state.json'
    $activePath=Join-Path $instance.logRoot 'active-run.json'
    $watch=[Diagnostics.Stopwatch]::StartNew()
    while ($watch.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        $record=Read-DeploymentOperationRecord -Path $recordPath -Deployment $Deployment -ExpectedRunId $RunId
        $active=Read-DeploymentOperationRecord -Path $activePath -Deployment $Deployment -ExpectedRunId $RunId
        if ($record.status -ceq 'failed' -or $active.status -ceq 'failed') { Stop-PrivateDeploymentCheck 'deployment_native_stop_failed' }
        if ($record.status -ceq 'stopped' -and $record.code -ceq 'instance_stopped' -and
            $active.status -ceq 'stopped' -and $active.code -ceq 'instance_stopped' -and
            -not [IO.File]::Exists((Join-Path $instance.pgData 'postmaster.pid')) -and
            (Test-DeploymentInstanceLockFree $instance) -and
            (Test-DeploymentPortClosed $instance.pgPort) -and (Test-DeploymentPortClosed $instance.httpPort)) {
            # An intervening new run must never be mistaken for the requested one.
            $confirmed=Read-DeploymentOperationRecord -Path $activePath -Deployment $Deployment -ExpectedRunId $RunId
            if ($confirmed.status -ceq 'stopped' -and $confirmed.code -ceq 'instance_stopped') { return }
        }
        Start-Sleep -Milliseconds 100
    }
    Stop-PrivateDeploymentCheck 'deployment_stop_confirmation_timeout' 1
}

function Convert-DeploymentNativeResult {
    param($Output,[int]$ExitCode)
    try { $value=($Output -join [Environment]::NewLine)|ConvertFrom-Json }
    catch { Stop-PrivateDeploymentCheck 'deployment_child_output_invalid' }
    if ($value.exitCode -ne $ExitCode -or $value.valid -isnot [bool] -or $value.valid -ne ($ExitCode -eq 0)) { Stop-PrivateDeploymentCheck 'deployment_child_output_invalid' }
    return $value
}

function Publish-DeploymentRunStop {
    param([string]$Directory,[string]$RunId,[string]$InstanceId)
    Assert-RackClickProcessPrivateAcl $Directory
    $requestPath=Join-Path $Directory 'stop-request.json'
    function Confirm-DeploymentStopIdentity {
        Assert-RackClickProcessPrivateAcl $requestPath
        if ((Get-Item -LiteralPath $requestPath).Length -gt 1024) { Stop-PrivateDeploymentCheck 'deployment_stop_request_invalid' }
        try { $existing=[IO.File]::ReadAllText($requestPath,[Text.Encoding]::UTF8)|ConvertFrom-Json }
        catch { Stop-PrivateDeploymentCheck 'deployment_stop_request_invalid' }
        if ((($existing.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'instanceId,runId,schemaVersion' -or
            $existing.schemaVersion -isnot [int] -or $existing.schemaVersion -ne 1 -or
            $existing.runId -cne $RunId -or $existing.instanceId -cne $InstanceId) { Stop-PrivateDeploymentCheck 'deployment_stop_request_invalid' }
    }
    if ([IO.File]::Exists($requestPath)) { Confirm-DeploymentStopIdentity;return }
    $temporary=Join-Path $Directory ('stop-request-'+[guid]::NewGuid().ToString('N')+'.tmp')
    $stream=$null
    try {
        $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes((@{schemaVersion=1;runId=$RunId;instanceId=$InstanceId}|ConvertTo-Json -Compress))
        $stream=[IO.File]::Open($temporary,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        $stream.Write($bytes,0,$bytes.Length);$stream.Flush($true);$stream.Dispose();$stream=$null
        Assert-RackClickProcessPrivateAcl $temporary
        try { [IO.File]::Move($temporary,$requestPath) }
        catch [IO.IOException] {
            if (-not [IO.File]::Exists($requestPath)) { Stop-PrivateDeploymentCheck 'deployment_stop_request_publish_failed' }
            Confirm-DeploymentStopIdentity
        }
    } finally { if ($null -ne $stream) { $stream.Dispose() } }
}

function Request-DeploymentCapturedRunStop {
    param([hashtable]$Deployment,$CapturedRecord)
    $instance=$Deployment.instance
    if (Test-DeploymentInstanceLockFree $instance) { Stop-PrivateDeploymentCheck 'no_active_launcher' 1 }
    $current=Read-DeploymentOperationRecord -Path (Join-Path $instance.logRoot 'active-run.json') -Deployment $Deployment -ExpectedRunId $CapturedRecord.runId
    if ($current.status -ceq 'failed') { Stop-PrivateDeploymentCheck 'deployment_native_stop_failed' }
    if ($current.status -ceq 'stopped') { return $false }
    # Even if a different run starts after this recheck, this immutable UUID path
    # can only request the captured OLD run. Never resolve active-run again to publish.
    $directory=Join-Path $instance.logRoot ('launcher-'+$CapturedRecord.runId)
    Publish-DeploymentRunStop -Directory $directory -RunId $CapturedRecord.runId -InstanceId $instance.id
    return $true
}

$deployment=$null;$forwarded=$false;$operationExit=2
$report=[ordered]@{schemaVersion=1;valid=$false;exitCode=2;code='deployment_operation_failed';operation=$deploymentOperationInputs.operation;deploymentId='';instanceId='';runId='';stopRequested=$false;stopConfirmed=$false;backupPath='';backupManifestSha256='';dumpSha256='';scope='Private local operation; not SCM, clean Windows installation, complete recovery or adoption'}
try {
    if ($deploymentOperationInputs.operation -cnotin @('Start','Stop','Backup') -or
        $deploymentOperationInputs.stopAfter -lt 0 -or $deploymentOperationInputs.stopAfter -gt 3600 -or
        $deploymentOperationInputs.stopTimeout -lt 1 -or $deploymentOperationInputs.stopTimeout -gt 180 -or
        ($deploymentOperationInputs.operation -cne 'Start' -and $deploymentOperationInputs.stopAfter -ne 0) -or
        ($deploymentOperationInputs.operation -cne 'Backup' -and $deploymentOperationInputs.backup.Length -gt 0)) { Stop-PrivateDeploymentCheck 'deployment_operation_input_invalid' }
    $maintenance=$deploymentOperationInputs.operation -cne 'Start'
    $deployment=Read-RackClickPrivateDeployment -DeploymentPath $deploymentOperationInputs.path -ExpectedDeploymentSha256 $deploymentOperationInputs.sha -Maintenance:$maintenance
    $report.deploymentId=$deployment.id;$report.instanceId=$deployment.instance.id
    $instance=$deployment.instance
    $instanceSha=Get-RuntimeConfigDigest $instance.manifestPath
    if ($deploymentOperationInputs.operation -ceq 'Start') {
        if (-not $deployment.httpsValidated) { Stop-PrivateDeploymentCheck 'deployment_https_required' }
        $manifest=[IO.File]::ReadAllText((Join-Path $deployment.root 'deployment.json'),[Text.Encoding]::UTF8)|ConvertFrom-Json
        $forwarded=$true
        & (Join-Path $PSScriptRoot 'Start-RackClickLabInstance.ps1') -InstancePath $instance.root -ExpectedInstanceSha256 $instanceSha -GracefulShutdown -HttpsProfilePath $deployment.https.root -ExpectedHttpsProfileSha256 $manifest.httpsProfileSha256 -StopAfterSeconds $deploymentOperationInputs.stopAfter
        $operationExit=[int]$LASTEXITCODE
    } elseif ($deploymentOperationInputs.operation -ceq 'Stop') {
        $activePath=Join-Path $instance.logRoot 'active-run.json'
        if (-not [IO.File]::Exists($activePath)) { Stop-PrivateDeploymentCheck 'no_active_launcher' 1 }
        $active=Read-DeploymentOperationRecord -Path $activePath -Deployment $deployment
        $report.runId=$active.runId
        if ($active.status -ceq 'failed') { Stop-PrivateDeploymentCheck 'deployment_native_stop_failed' }
        if ($active.status -cne 'stopped') {
            $report.stopRequested=Request-DeploymentCapturedRunStop -Deployment $deployment -CapturedRecord $active
        }
        Wait-DeploymentStopped -Deployment $deployment -RunId $active.runId -TimeoutSeconds $deploymentOperationInputs.stopTimeout
        $report.valid=$true;$report.exitCode=0;$report.stopConfirmed=$true;$report.code='deployment_stopped'
        if (-not $report.stopRequested) { $report.code='deployment_already_stopped' }
        $operationExit=0
    } else {
        $destination=Get-StageLocalPath $deploymentOperationInputs.backup
        foreach ($other in @($deployment.root,$instance.pgBin,[IO.Path]::GetDirectoryName($instance.dotnet))) {
            if (Test-StageOverlap $destination $other) { Stop-PrivateDeploymentCheck 'deployment_backup_paths_overlap' }
        }
        $output=@(& (Join-Path $PSScriptRoot 'New-RackClickDatabaseBackup.ps1') -PostgresBinPath $instance.pgBin -ProfilePath (Join-Path $instance.privateRoot 'backup-profile.json') -DestinationPath $destination)
        $nativeExit=[int]$LASTEXITCODE
        $answer=Convert-DeploymentNativeResult $output $nativeExit
        if ($nativeExit -ne 0) { Stop-PrivateDeploymentCheck 'deployment_backup_failed' $nativeExit }
        $backup=$null
        try {
            $backup=Read-BackupManifest -Path $destination -ExpectedHash $answer.manifestSha256
            $report.backupPath=$destination;$report.backupManifestSha256=$answer.manifestSha256;$report.dumpSha256=$backup.hash
        } finally {
            if ($null -ne $backup) { $backup.dumpHandle.Dispose();$backup.manifestHandle.Dispose() }
        }
        $report.valid=$true;$report.exitCode=0;$report.code='deployment_backup_complete';$operationExit=0
    }
} catch {
    $forwarded=$false
    foreach ($pair in @(@('deploymentCode','deploymentExit'),@('httpsCode','httpsExit'),@('instanceCode','instanceExit'),@('stageCode','stageExit'),@('code','exitCode'))) {
        if ($_.Exception.Data.Contains($pair[0])) { $report.code=$_.Exception.Data[$pair[0]];$report.exitCode=[int]$_.Exception.Data[$pair[1]];break }
    }
    $operationExit=[int]$report.exitCode
} finally {
    try { Close-RackClickPrivateDeployment -Deployment $deployment }
    catch { $forwarded=$false;$report.valid=$false;$report.exitCode=2;$report.code='deployment_handles_close_failed';$operationExit=2 }
}
if (-not $forwarded) { $report|ConvertTo-Json -Compress }
exit $operationExit
