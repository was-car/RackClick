#requires -Version 5.1
<# Recover into a NEW private lab deployment: Stage -> recovered native instance -> NEW TLS.
   The source backup must be explicitly trusted; no target reuse, upgrade, service or store writes.
#>
[CmdletBinding()]
param([string]$ManifestPath='',[string]$ExpectedManifestSha256='',[string]$ServerPath='',[string]$FrontendPath='',
      [string]$DotNetPath='',[string]$PostgresBinPath='',[string]$DestinationPath='',[int]$PostgresPort=0,[int]$HttpPort=0,
      [string]$RecoveryUser='',[string]$BackupPath='',[string]$ExpectedBackupManifestSha256='')
$restoreDeploymentInputs=@{manifest=$ManifestPath;manifestHash=$ExpectedManifestSha256;server=$ServerPath;frontend=$FrontendPath;
    dotnet=$DotNetPath;pg=$PostgresBinPath;destination=$DestinationPath;pgPort=$PostgresPort;httpPort=$HttpPort;
    user=$RecoveryUser;backup=$BackupPath;backupHash=$ExpectedBackupManifestSha256}
. (Join-Path $PSScriptRoot 'RackClick.Deployment.ps1')
. (Join-Path $PSScriptRoot 'New-RackClickRecoveredInstance.ps1')

function Invoke-RestoreDeploymentChild {
    param([string]$Script,[string[]]$Arguments,[string]$Root,[string]$Logs)
    if ($Script -cnotin @('Stage-ServerDistribution.ps1','New-RackClickRecoveredInstance.ps1','New-RackClickLabHttpsProfile.ps1')) {Stop-RecoveryCheck 'child_script_not_allowed'}
    $scriptPath=Join-Path $PSScriptRoot $Script;Assert-BackupNoReparse $scriptPath
    $handle=$null
    try {
        $values=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$scriptPath)+$Arguments
        $handle=Start-RackClickOwnedProcess -Executable (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -Arguments $values -WorkingDirectory $Root -Environment @{} -LogDirectory $Logs -Label $Script.Replace('.ps1','')
        $result=Wait-RackClickOwnedProcess -Handle $handle -TimeoutSeconds 300
        if ($result.exitCode -eq 124) {Stop-RecoveryCheck 'child_timeout' 1}
        if ($result.stderr.Length -ne 0 -or $result.stdout.Length -gt 16384) {Stop-RecoveryCheck 'child_output_invalid'}
        try {$value=$result.stdout|ConvertFrom-Json} catch {Stop-RecoveryCheck 'child_output_invalid'}
        if ($value -isnot [pscustomobject] -or $value.exitCode -isnot [int] -or $value.valid -isnot [bool] -or
            $value.code -isnot [string] -or $value.code -cnotmatch '^[a-z][a-z0-9_]{0,99}$' -or
            $value.exitCode -ne $result.exitCode -or $value.exitCode -notin @(0,1,2) -or $value.valid -ne ($value.exitCode -eq 0)) {Stop-RecoveryCheck 'child_output_invalid'}
        if (-not $value.valid) {Stop-RecoveryCheck $value.code $value.exitCode}
        return $value
    } finally {
        if ($null -ne $handle) {try {Stop-RackClickOwnedProcess $handle} finally {$handle.Process.Dispose()}}
    }
}

$report=[ordered]@{valid=$false;exitCode=2;code='preflight_failed';deploymentId='';deploymentSha256='';instanceId='';url='';
    sourceBackupManifestSha256='';recoveryAuditEventId='';scope='NEW private loopback recovered deployment; not Windows service or final installation acceptance'}
$phase='preflight';$owned=$false;$stateStream=$null;$state=$null;$sourceLocks=@();$backup=$null;$instance=$null;$https=$null;$deployment=$null
$restoreDeploymentOriginalEnvironment=@{}
try {
    if ($restoreDeploymentInputs.manifestHash -notmatch '^[a-fA-F0-9]{64}$') {Stop-RecoveryCheck 'manifest_reference_required'}
    if ($restoreDeploymentInputs.backupHash -notmatch '^[a-fA-F0-9]{64}$') {Stop-RecoveryCheck 'backup_manifest_reference_required'}
    $paths=@{}
    foreach ($name in @('manifest','server','frontend','dotnet','pg','destination','backup')) {
        $paths[$name]=Get-StageLocalPath $restoreDeploymentInputs[$name]
    }
    $root=$paths.destination;Assert-InstanceTechnicalRoot $root;$parent=[IO.Path]::GetDirectoryName($root)
    if (-not [IO.Directory]::Exists($parent)) {Stop-RecoveryCheck 'destination_parent_missing' 1}
    Assert-BackupNoReparse $parent
    if ((New-Object IO.DriveInfo($root.Substring(0,3))).DriveType -ne [IO.DriveType]::Fixed) {Stop-RecoveryCheck 'path_not_local_fixed'}
    if ([IO.File]::Exists($root) -or [IO.Directory]::Exists($root)) {Stop-RecoveryCheck 'destination_exists' 1}
    foreach ($other in @($paths.manifest,$paths.server,$paths.frontend,$paths.backup,$paths.pg,[IO.Path]::GetDirectoryName($paths.dotnet))) {
        if (Test-StageOverlap $root $other) {Stop-RecoveryCheck 'paths_overlap'}
    }
    foreach ($name in @('manifest','server','frontend','dotnet','pg','backup')) {
        if (-not (Test-Path -LiteralPath $paths[$name])) {Stop-RecoveryCheck 'input_path_missing' 1};Assert-BackupNoReparse $paths[$name]
    }
    $user=Assert-InstanceDisplayName $restoreDeploymentInputs.user
    if ($restoreDeploymentInputs.pgPort -eq $restoreDeploymentInputs.httpPort) {Stop-RecoveryCheck 'ports_must_differ'}
    Assert-InstancePort $restoreDeploymentInputs.pgPort;Assert-InstancePort $restoreDeploymentInputs.httpPort
    Clear-RecoveryInheritedConfiguration $restoreDeploymentOriginalEnvironment
    # Both inputs are bound before any new ROOT exists, and retained through final validation.
    $backup=Open-RecoveryBackup $paths.backup $restoreDeploymentInputs.backupHash
    $sourceLocks += [IO.File]::Open($paths.manifest,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $null=Invoke-StageIntegrity $paths.manifest $restoreDeploymentInputs.manifestHash $paths.server $paths.frontend
    $sourceManifest=[IO.File]::ReadAllText($paths.manifest,[Text.Encoding]::UTF8)|ConvertFrom-Json
    foreach ($kind in @('server','frontend')) {
        foreach ($entry in $sourceManifest.distributions.$kind.PSObject.Properties) {
            $source=Join-Path $paths[$kind] $entry.Name.Replace('/',[IO.Path]::DirectorySeparatorChar);Assert-BackupNoReparse $source
            $sourceLocks += [IO.File]::Open($source,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        }
    }
    $null=Invoke-StageIntegrity $paths.manifest $restoreDeploymentInputs.manifestHash $paths.server $paths.frontend
    $null=Invoke-StageRuntime $paths.dotnet $paths.pg $paths.server
    Assert-RecoveryPostgresTools $paths.pg;Assert-RecoveryArchiveList $paths.pg $backup
    if (-not ('Security.Cryptography.X509Certificates.CertificateRequest' -as [type]) -or
        -not ('Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder' -as [type]) -or
        -not [Enum]::IsDefined([Security.Cryptography.X509Certificates.X509KeyStorageFlags],'EphemeralKeySet')) {Stop-RecoveryCheck 'https_framework_api_unavailable' 1}
    $null=New-BackupPrivateDirectory $root;$owned=$true
    $id=[guid]::NewGuid().ToString('D');$report.deploymentId=$id
    $state=[ordered]@{schemaVersion=1;deploymentId=$id;status='in-progress';code='components_pending'}
    $statePath=Join-Path $root 'deployment-state.json'
    $stateStream=[IO.File]::Open($statePath,[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::Read);Set-StageState $stateStream $state
    $logs=New-BackupPrivateDirectory (Join-Path $root 'logs')
    $distributionPath=Join-Path $root 'distribution';$instancePath=Join-Path $root 'instance';$httpsPath=Join-Path $root 'https'
    $phase='stage'
    $stage=Invoke-RestoreDeploymentChild 'Stage-ServerDistribution.ps1' @('-ManifestPath',$paths.manifest,'-ExpectedManifestSha256',$restoreDeploymentInputs.manifestHash,'-ServerPath',$paths.server,'-FrontendPath',$paths.frontend,'-DotNetPath',$paths.dotnet,'-PostgresBinPath',$paths.pg,'-DestinationPath',$distributionPath) $root $logs
    # 14 tiene 24 archivos de servidor (lista explícita); 9–13 siguen con 9+esquema. Total = servidor + 18 de frontend.
    $expectedVerified=if ($sourceManifest.schema -in @(14,15)) {28+$sourceManifest.schema} else {27+$sourceManifest.schema}
    if ($stage.code -cne 'artifacts_staged' -or $stage.destinationPath -cne $distributionPath -or $stage.verifiedFiles -ne $expectedVerified -or $stage.receiptSha256 -cnotmatch '^[a-f0-9]{64}$') {Stop-RecoveryCheck 'receipt_invalid'}
    $phase='instance'
    $created=Invoke-RestoreDeploymentChild 'New-RackClickRecoveredInstance.ps1' @('-StagePath',$distributionPath,'-ExpectedManifestSha256',$restoreDeploymentInputs.manifestHash,'-ExpectedReceiptSha256',$stage.receiptSha256,'-DotNetPath',$paths.dotnet,'-PostgresBinPath',$paths.pg,'-InstancePath',$instancePath,'-PostgresPort',[string]$restoreDeploymentInputs.pgPort,'-PublicOrigin',('http://127.0.0.1:'+[string]$restoreDeploymentInputs.httpPort),'-RecoveryUser',$user,'-BackupPath',$paths.backup,'-ExpectedBackupManifestSha256',$restoreDeploymentInputs.backupHash,'-DevelopmentLoopbackHttp') $root $logs
    if ($created.code -cne 'instance_initialized' -or $created.instanceManifestSha256 -cnotmatch '^[a-f0-9]{64}$' -or
        $created.sourceBackupManifestSha256 -cne $restoreDeploymentInputs.backupHash.ToLowerInvariant() -or
        $created.recoveryAuditEventId -cnotmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$') {Stop-RecoveryCheck 'receipt_invalid'}
    $instance=Read-RackClickInstance $instancePath $created.instanceManifestSha256
    if ($instance.id -cne $created.instanceId -or [IO.File]::Exists((Join-Path $instance.pgData 'postmaster.pid'))) {Stop-RecoveryCheck 'stopped_identity_invalid'}
    $phase='https'
    $tls=Invoke-RestoreDeploymentChild 'New-RackClickLabHttpsProfile.ps1' @('-InstancePath',$instancePath,'-ExpectedInstanceSha256',$created.instanceManifestSha256,'-DestinationPath',$httpsPath) $root $logs
    if ($tls.code -cne 'https_profile_created' -or $tls.profilePath -cne $httpsPath -or $tls.profileSha256 -cnotmatch '^[a-f0-9]{64}$') {Stop-RecoveryCheck 'receipt_invalid'}
    $https=Read-RackClickHttpsProfile -Instance $instance -ProfilePath $httpsPath -ExpectedProfileSha256 $tls.profileSha256
    if ($https.certificateSha256 -cne $tls.certificateSha256 -or [IO.File]::Exists((Join-Path $instance.pgData 'postmaster.pid'))) {Stop-RecoveryCheck 'stopped_identity_invalid'}
    $phase='finalize'
    $state.status='prepared';$state.code='deployment_prepared';Set-StageState $stateStream $state
    $stateStream.Dispose();$stateStream=$null
    $receipt=[ordered]@{schemaVersion=1;kind='RackClickPrivateDeployment';state='prepared';id=$id;rootPath=$root;instanceId=$instance.id;instanceManifestSha256=$created.instanceManifestSha256;stageManifestSha256=$restoreDeploymentInputs.manifestHash.ToLowerInvariant();stageReceiptSha256=$stage.receiptSha256;httpsProfileSha256=$tls.profileSha256;publicOrigin=$https.origin}
    $receiptPath=Join-Path $root 'deployment.json';Write-BackupNewText $receiptPath ($receipt|ConvertTo-Json -Depth 4 -Compress)
    $digest=Get-RuntimeConfigDigest $receiptPath
    $deployment=Read-RackClickPrivateDeployment -DeploymentPath $root -ExpectedDeploymentSha256 $digest
    if (-not $deployment.httpsValidated -or $deployment.id -cne $id -or $deployment.instance.id -cne $instance.id) {Stop-RecoveryCheck 'receipt_invalid'}
    $report.valid=$true;$report.exitCode=0;$report.code='deployment_prepared';$report.deploymentSha256=$digest;$report.instanceId=$instance.id;$report.url=$https.origin
    $report.sourceBackupManifestSha256=$restoreDeploymentInputs.backupHash.ToLowerInvariant();$report.recoveryAuditEventId=$created.recoveryAuditEventId
} catch {
    $cause='failed';$exitValue=2
    foreach ($pair in @(@('recoveryCode','recoveryExit'),@('deploymentCode','deploymentExit'),@('httpsCode','httpsExit'),@('instanceCode','instanceExit'),@('stageCode','stageExit'),@('code','exitCode'))) {
        if ($_.Exception.Data.Contains($pair[0])) {$cause=[string]$_.Exception.Data[$pair[0]];$exitValue=[int]$_.Exception.Data[$pair[1]];break}
    }
    if ($cause -cnotmatch '^[a-z][a-z0-9_]{0,99}$' -or $exitValue -notin @(1,2)) {$cause='failed';$exitValue=2}
    $report.valid=$false;$report.exitCode=$exitValue;$report.code=$phase+'_'+$cause
    try {Close-RackClickPrivateDeployment $deployment;$deployment=$null} catch {$report.code=$phase+'_cleanup_failed';$report.exitCode=2}
} finally {
    try {
        $cleanupFailed=$false
        foreach ($cleanup in @({Close-RackClickPrivateDeployment $deployment},{Close-RackClickHttpsProfile $https},{Close-RackClickInstance $instance},{if ($null -ne $stateStream) {$stateStream.Dispose();$stateStream=$null}})) {try {& $cleanup} catch {$cleanupFailed=$true}}
        foreach ($stream in $sourceLocks) {try {$stream.Dispose()} catch {$cleanupFailed=$true}}
        if ($null -ne $backup) {foreach ($stream in @($backup.dumpHandle,$backup.manifestHandle)) {try {$stream.Dispose()} catch {$cleanupFailed=$true}}}
        if ($cleanupFailed) {$report.valid=$false;$report.exitCode=2;$report.code='finalize_cleanup_failed'}
    } finally {
        # Environment restoration must happen even if any Dispose above throws.
        $restoreFailed=$false
        foreach ($key in $restoreDeploymentOriginalEnvironment.Keys) {try {[Environment]::SetEnvironmentVariable([string]$key,[string]$restoreDeploymentOriginalEnvironment[$key],[EnvironmentVariableTarget]::Process)} catch {$restoreFailed=$true}}
        if ($restoreFailed) {$report.valid=$false;$report.exitCode=2;$report.code='environment_restore_failed'}
        if (-not $report.valid) {
            $report.deploymentSha256='';$report.instanceId='';$report.url='';$report.sourceBackupManifestSha256='';$report.recoveryAuditEventId=''
            if ($owned -and $null -ne $state) {
                $failureStream=$null
                try {
                    $failureStream=[IO.File]::Open($statePath,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::Read)
                    $state.status='failed';$state.code=$report.code;Set-StageState $failureStream $state
                } catch {$report.code='failure_state_write_failed';$report.exitCode=2}
                finally {if ($null -ne $failureStream) {try {$failureStream.Dispose()} catch {$report.code='failure_state_write_failed';$report.exitCode=2}}}
            }
        }
    }
}
$report|ConvertTo-Json -Compress
exit $report.exitCode
