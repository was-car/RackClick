#requires -Version 5.1
<# Internal validation package. New or trusted-backup Restore in a NEW private ROOT only; web is never started.
   No global installation unless the explicit switch is needed and token already elevated.
#>
[CmdletBinding()]
param([string]$ArchivePath='',[string]$ExpectedArchiveSha256='',[string]$DestinationPath='',
      [int]$PostgresPort=0,[int]$HttpPort=0,[string]$BootstrapUser='',[string]$SystemhausName='',
      [string]$Mode='New',[string]$BackupPath='',[string]$ExpectedBackupManifestSha256='',[string]$RecoveryUser='',
      [switch]$InstallPrerequisites)
$offlineInstallInputs=@{archive=$ArchivePath;hash=$ExpectedArchiveSha256;destination=$DestinationPath;pgPort=$PostgresPort;httpPort=$HttpPort;
    user=$BootstrapUser;house=$SystemhausName;mode=$Mode;backup=$BackupPath;backupHash=$ExpectedBackupManifestSha256;recoveryUser=$RecoveryUser;
    supplied=@($PSBoundParameters.Keys);installPrerequisites=[bool]$InstallPrerequisites}
. (Join-Path $PSScriptRoot 'RackClick.OfflineBundle.ps1')
# Existing definitions are pure on import; capture every caller input above because their
# nested runtime helper has a param block. The installed copy is imported before use below.
. (Join-Path $PSScriptRoot 'RackClick.Deployment.ps1')

function Clear-OfflineInheritedEnvironment {
    param([hashtable]$Original)
    # Record absence explicitly; restoration must also work with an empty initial map.
    $Original['PSModulePath']=[Environment]::GetEnvironmentVariable('PSModulePath',[EnvironmentVariableTarget]::Process)
    foreach ($key in [Environment]::GetEnvironmentVariables().Keys) {
        if ([string]$key -match '^(?i:Kestrel|ConnectionStrings|Bootstrap|Recovery|RackClick)(:|__)' -or
            [string]$key -match '^(?i:PG|DOTNET_|ASPNETCORE_)' -or
            [string]$key -in @('URLS','HTTP_PORTS','HTTPS_PORTS','PublicOrigin','DevelopmentLoopbackHttp','PSModulePath')) {
            $Original[[string]$key]=[Environment]::GetEnvironmentVariable([string]$key,[EnvironmentVariableTarget]::Process)
            [Environment]::SetEnvironmentVariable([string]$key,$null,[EnvironmentVariableTarget]::Process)
        }
    }
    [Environment]::SetEnvironmentVariable('PSModulePath',(Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules'),[EnvironmentVariableTarget]::Process)
}

function Invoke-OfflineInstallerChild {
    param([string]$Executable,[string[]]$Arguments,[string]$Root,[string]$Logs,[string]$Label,[int]$Timeout=600)
    $handle=$null
    try {
        $handle=Start-RackClickOwnedProcess -Executable $Executable -Arguments $Arguments -WorkingDirectory $Root -Environment @{} -LogDirectory $Logs -Label $Label
        $result=Wait-RackClickOwnedProcess -Handle $handle -TimeoutSeconds $Timeout
        if ($result.exitCode -eq 124) {Stop-OfflineBundleCheck 'child_timeout' 1}
        return $result
    } finally {if ($null -ne $handle) {try {Stop-RackClickOwnedProcess $handle} finally {$handle.Process.Dispose()}}}
}

function Assert-OfflineRedistributable {
    param([string]$Path)
    Assert-OfflineBundleNoReparse $Path
    $stream=$null
    try {
        $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        if ((Get-OfflineBundleStreamDigest $stream $stream.Length) -cne '843068991daaa1f73ad9f6239bce4d0f6a07a51f18c37ea2a867e9beca71295c') {Stop-OfflineBundleCheck 'prerequisite_hash_mismatch'}
        $version=[Diagnostics.FileVersionInfo]::GetVersionInfo($Path)
        $numeric=('{0}.{1}.{2}.{3}' -f $version.FileMajorPart,$version.FileMinorPart,$version.FileBuildPart,$version.FilePrivatePart)
        if ($numeric -cne '14.51.36247.0') {Stop-OfflineBundleCheck 'prerequisite_version_invalid'}
        # Explicit Windows PowerShell5 module avoids autoloading the inherited PS7 path.
        Import-Module (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1') -ErrorAction Stop
        $signature=Get-AuthenticodeSignature -LiteralPath $Path
        if ($signature.Status -ne [Management.Automation.SignatureStatus]::Valid -or $null -eq $signature.SignerCertificate -or
            $signature.SignerCertificate.Subject -notmatch '(?:^|,\s*)O=Microsoft Corporation(?:,|$)') {Stop-OfflineBundleCheck 'prerequisite_signature_invalid'}
        return $stream
    } catch {if ($null -ne $stream) {$stream.Dispose()};throw}
}

$report=[ordered]@{valid=$false;exitCode=2;code='preflight_failed';installationPath='';installationId='';installationSha256='';
    bundleId='';bundleArchiveSha256='';bundleManifestSha256='';applicationManifestSha256='';versions=$null;counts=$null;verifiedFiles=0;
    deploymentPath='';deploymentId='';deploymentSha256='';publicOrigin='';crtDecision='';rebootRequired=$false}
$bundle=$null;$backup=$null;$deployment=$null;$prerequisiteLock=$null;$stateStream=$null;$state=$null;$statePath='';$owned=$false;$phase='preflight';$originalEnvironment=@{}
if ($offlineInstallInputs.mode -ceq 'Restore') {
    $report.mode='Restore';$report.sourceBackupManifestSha256='';$report.recoveryAuditEventId=''
}
try {
    if ($offlineInstallInputs.mode -cnotin @('New','Restore')) {Stop-OfflineBundleCheck 'mode_invalid'}
    if ($offlineInstallInputs.mode -ceq 'New') {
        if (@($offlineInstallInputs.supplied|Where-Object {$_ -in @('BackupPath','ExpectedBackupManifestSha256','RecoveryUser')}).Count -ne 0) {Stop-OfflineBundleCheck 'mode_arguments_invalid'}
    } else {
        if (@($offlineInstallInputs.supplied|Where-Object {$_ -in @('BootstrapUser','SystemhausName')}).Count -ne 0) {Stop-OfflineBundleCheck 'mode_arguments_invalid'}
        if ([string]::IsNullOrWhiteSpace($offlineInstallInputs.backup) -or [string]::IsNullOrWhiteSpace($offlineInstallInputs.recoveryUser) -or
            $offlineInstallInputs.backupHash -cnotmatch '^[a-fA-F0-9]{64}$') {Stop-OfflineBundleCheck 'recovery_arguments_invalid'}
    }
    $bundle=Read-RackClickOfflineBundle -ArchivePath $offlineInstallInputs.archive -ExpectedArchiveSha256 $offlineInstallInputs.hash
    # Candidata 06: el esquema 14 se admite para la instalación de ensayo limpio. Stage, runtime, migración y Restore
    # están propagados y probados en laboratorio; la instalación completa en Windows Server aún no se ha ensayado.
    $root=Get-OfflineBundleLocalPath $offlineInstallInputs.destination -Ascii
    $parent=[IO.Path]::GetDirectoryName($root)
    if (-not [IO.Directory]::Exists($parent)) {Stop-OfflineBundleCheck 'destination_parent_missing' 1}
    Assert-OfflineBundleNoReparse $parent
    if ([IO.File]::Exists($root) -or [IO.Directory]::Exists($root)) {Stop-OfflineBundleCheck 'destination_exists' 1}
    foreach ($source in @($bundle.archivePath,[IO.Path]::GetFullPath($PSScriptRoot))) {
        if (Test-OfflineBundleOverlap $root $source) {Stop-OfflineBundleCheck 'paths_overlap'}
    }
    if ($offlineInstallInputs.pgPort -eq $offlineInstallInputs.httpPort) {Stop-OfflineBundleCheck 'ports_must_differ'}
    Assert-InstancePort $offlineInstallInputs.pgPort;Assert-InstancePort $offlineInstallInputs.httpPort
    if ($offlineInstallInputs.mode -ceq 'New') {
        $user=Assert-InstanceDisplayName $offlineInstallInputs.user;$house=Assert-InstanceDisplayName $offlineInstallInputs.house
    } else {
        $user=Assert-InstanceDisplayName $offlineInstallInputs.recoveryUser
        $backupRoot=Get-OfflineBundleLocalPath $offlineInstallInputs.backup
        foreach ($source in @($bundle.archivePath,[IO.Path]::GetFullPath($PSScriptRoot),$root)) {
            if (Test-OfflineBundleOverlap $backupRoot $source) {Stop-OfflineBundleCheck 'paths_overlap'}
        }
        foreach ($name in @('','manifest.json','data.dump')) {
            $inputPath=if ($name.Length -eq 0) {$backupRoot} else {Join-Path $backupRoot $name}
            Assert-BackupPrivateAcl $inputPath
        }
        $backup=Read-BackupManifest $backupRoot $offlineInstallInputs.backupHash
        foreach ($stream in @($backup.manifestHandle,$backup.dumpHandle)) {Assert-BackupPrivateAcl $stream.Name}
    }
    $crt=Get-RackClickCrtInventory
    $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
    $principal=New-Object Security.Principal.WindowsPrincipal($identity)
    $elevated=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    $decision=Get-RackClickCrtDecision $crt.compatible $offlineInstallInputs.installPrerequisites $elevated
    $report.crtDecision=$decision
    if ($decision -ceq 'missing') {Stop-OfflineBundleCheck 'crt_prerequisite_missing' 1}
    if ($decision -ceq 'elevation_required') {Stop-OfflineBundleCheck 'crt_elevated_token_required' 1}
    if (-not ('Security.Cryptography.X509Certificates.CertificateRequest' -as [type]) -or
        -not ('Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder' -as [type]) -or
        -not [Enum]::IsDefined([Security.Cryptography.X509Certificates.X509KeyStorageFlags],'EphemeralKeySet')) {Stop-OfflineBundleCheck 'https_framework_api_unavailable' 1}
    Clear-OfflineInheritedEnvironment $originalEnvironment
    $null=New-BackupPrivateDirectory $root;$owned=$true
    $id=[guid]::NewGuid().ToString('D');$report.installationPath=$root;$report.installationId=$id
    $state=[ordered]@{schemaVersion=1;installationId=$id;status='in-progress';code='content_pending'}
    $statePath=Join-Path $root 'installation-state.json'
    $stateStream=[IO.File]::Open($statePath,[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::Read)
    Set-StageState $stateStream $state
    $content=New-BackupPrivateDirectory (Join-Path $root 'content');$logs=New-BackupPrivateDirectory (Join-Path $root 'logs')
    $phase='extract';Copy-RackClickOfflineBundleContent $bundle $content
    Assert-RackClickOfflineInstalledContent $bundle $content
    # All subsequent operator definitions and child executable scripts come from content.
    . (Join-Path $content 'operators\RackClick.Deployment.ps1')
    if ($decision -ceq 'install') {
        $phase='prerequisite'
        $exe=Join-Path $content 'prerequisites\vc_redist.x64.exe'
        $prerequisiteLock=Assert-OfflineRedistributable $exe
        $result=Invoke-OfflineInstallerChild $exe @('/install','/quiet','/norestart','/log',(Join-Path $logs 'vc-redist.log')) $root $logs 'vc-redist'
        $exitDecision=Get-RackClickCrtExitDecision $result.exitCode
        if ($exitDecision -ceq 'reboot_required') {$report.rebootRequired=$true;Stop-OfflineBundleCheck 'reboot_required' 1}
        if ($exitDecision -ceq 'failed') {Stop-OfflineBundleCheck 'prerequisite_install_failed' 1}
        if (-not (Get-RackClickCrtInventory).compatible) {Stop-OfflineBundleCheck 'prerequisite_postcheck_failed' 1}
    }
    $phase='deployment';$deploymentRoot=Join-Path $root 'deployment'
    $manifest=Join-Path $content 'application\manifest.json';$dotnet=Join-Path $content 'dependencies\dotnet\dotnet.exe';$pg=Join-Path $content 'dependencies\postgresql\bin'
    $factory=if ($offlineInstallInputs.mode -ceq 'Restore') {'Restore-RackClickPrivateDeployment.ps1'} else {'New-RackClickPrivateDeployment.ps1'}
    $script=Join-Path $content ('operators\'+$factory)
    $arguments=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$script,
        '-ManifestPath',$manifest,'-ExpectedManifestSha256',$bundle.manifest.applicationManifestSha256,
        '-ServerPath',(Join-Path $content 'application\server'),'-FrontendPath',(Join-Path $content 'application\frontend'),
        '-DotNetPath',$dotnet,'-PostgresBinPath',$pg,'-DestinationPath',$deploymentRoot,
        '-PostgresPort',[string]$offlineInstallInputs.pgPort,'-HttpPort',[string]$offlineInstallInputs.httpPort)
    if ($offlineInstallInputs.mode -ceq 'Restore') {
        $arguments+=@('-RecoveryUser',$user,'-BackupPath',$backupRoot,'-ExpectedBackupManifestSha256',$offlineInstallInputs.backupHash.ToLowerInvariant())
    } else {$arguments+=@('-BootstrapUser',$user,'-SystemhausName',$house)}
    $result=Invoke-OfflineInstallerChild (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') $arguments $root $logs 'deployment'
    if ($result.stderr.Length -ne 0 -or $result.stdout.Length -gt 16384) {Stop-OfflineBundleCheck 'child_output_invalid'}
    try {$created=$result.stdout|ConvertFrom-Json} catch {Stop-OfflineBundleCheck 'child_output_invalid'}
    if ($created -isnot [pscustomobject] -or $created.valid -isnot [bool] -or $created.exitCode -isnot [int] -or
        $created.exitCode -ne $result.exitCode -or $created.exitCode -notin @(0,1,2) -or $created.valid -ne ($result.exitCode -eq 0) -or
        $created.code -isnot [string] -or $created.code -cnotmatch '^[a-z][a-z0-9_]{0,79}$') {Stop-OfflineBundleCheck 'child_output_invalid'}
    if (-not $created.valid) {Stop-OfflineBundleCheck $created.code $created.exitCode}
    if ($created.code -cne 'deployment_prepared' -or $created.deploymentSha256 -isnot [string] -or $created.deploymentSha256 -cnotmatch '^[a-f0-9]{64}$' -or
        $created.deploymentId -isnot [string] -or $created.deploymentId -cnotmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$') {Stop-OfflineBundleCheck 'deployment_receipt_invalid'}
    if ($offlineInstallInputs.mode -ceq 'New' -and $created.deploymentPath -cne $deploymentRoot) {Stop-OfflineBundleCheck 'deployment_receipt_invalid'}
    if ($offlineInstallInputs.mode -ceq 'Restore' -and ($created.sourceBackupManifestSha256 -isnot [string] -or
        $created.sourceBackupManifestSha256 -cne $offlineInstallInputs.backupHash.ToLowerInvariant() -or
        $created.recoveryAuditEventId -isnot [string] -or $created.recoveryAuditEventId -cnotmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')) {Stop-OfflineBundleCheck 'recovery_receipt_invalid'}
    $phase='finalize'
    $deployment=Read-RackClickPrivateDeployment -DeploymentPath $deploymentRoot -ExpectedDeploymentSha256 $created.deploymentSha256
    if (-not $deployment.httpsValidated -or $deployment.id -cne $created.deploymentId -or $deployment.instance.dotnet -cne $dotnet -or
        $deployment.instance.pgBin -cne $pg -or [IO.File]::Exists((Join-Path $deployment.instance.pgData 'postmaster.pid'))) {Stop-OfflineBundleCheck 'deployment_binding_invalid'}
    if ($offlineInstallInputs.mode -ceq 'Restore' -and ($created.instanceId -isnot [string] -or $created.instanceId -cne $deployment.instance.id -or
        $created.url -isnot [string] -or $created.url -cne $deployment.https.origin)) {Stop-OfflineBundleCheck 'recovery_binding_invalid'}
    Assert-RackClickOfflineInstalledContent $bundle $content
    $origin=$deployment.https.origin
    Close-RackClickPrivateDeployment $deployment;$deployment=$null
    $state.status='prepared';$state.code='installation_prepared';Set-StageState $stateStream $state
    # Close state writer BEFORE a reader or last receipt publication; no sharing violation.
    $stateStream.Dispose();$stateStream=$null
    $receipt=[ordered]@{schemaVersion=1;kind='RackClickPrivateInstallation';id=$id;rootPath=$root;state='prepared';bundleId=$bundle.manifest.id;
        bundleArchiveSha256=$bundle.archiveSha256;bundleManifestSha256=$bundle.manifestSha256;deploymentId=$created.deploymentId;
        deploymentSha256=$created.deploymentSha256;publicOrigin=$origin}
    if ($offlineInstallInputs.mode -ceq 'Restore') {
        $receipt.schemaVersion=2;$receipt.recovery=[ordered]@{backupManifestSha256=$created.sourceBackupManifestSha256;auditEventId=$created.recoveryAuditEventId}
    }
    $receiptPath=Join-Path $root 'installation.json'
    Write-BackupNewText $receiptPath ($receipt|ConvertTo-Json -Depth 4 -Compress)
    $receiptHash=Get-RuntimeConfigDigest $receiptPath
    $report.valid=$true;$report.exitCode=0;$report.code='installation_prepared';$report.installationSha256=$receiptHash
    $report.bundleId=$bundle.manifest.id;$report.bundleArchiveSha256=$bundle.archiveSha256;$report.bundleManifestSha256=$bundle.manifestSha256
    $report.applicationManifestSha256=$bundle.manifest.applicationManifestSha256;$report.versions=$bundle.manifest.versions;$report.counts=$bundle.counts;$report.verifiedFiles=$bundle.verifiedFiles
    $report.deploymentPath=$deploymentRoot;$report.deploymentId=$created.deploymentId;$report.deploymentSha256=$created.deploymentSha256;$report.publicOrigin=$origin
    if ($offlineInstallInputs.mode -ceq 'Restore') {$report.sourceBackupManifestSha256=$created.sourceBackupManifestSha256;$report.recoveryAuditEventId=$created.recoveryAuditEventId}
} catch {
    $cause='failed';$exitValue=2
    foreach ($pair in @(@('bundleCode','bundleExit'),@('recoveryCode','recoveryExit'),@('deploymentCode','deploymentExit'),@('instanceCode','instanceExit'),@('stageCode','stageExit'),@('code','exitCode'))) {
        if ($_.Exception.Data.Contains($pair[0])) {$cause=[string]$_.Exception.Data[$pair[0]];$exitValue=[int]$_.Exception.Data[$pair[1]];break}
    }
    if ($cause -cnotmatch '^[a-z][a-z0-9_]{0,79}$' -or $exitValue -notin @(1,2)) {$cause='failed';$exitValue=2}
    $report.valid=$false;$report.exitCode=$exitValue;$report.code=$phase+'_'+$cause
} finally {
    try {
        foreach ($cleanup in @({Close-RackClickPrivateDeployment $deployment},{Close-RackClickOfflineBundle $bundle},
            {if ($null -ne $backup) {try {$backup.dumpHandle.Dispose()} finally {$backup.manifestHandle.Dispose()}}},
            {if ($null -ne $prerequisiteLock) {$prerequisiteLock.Dispose()}},{if ($null -ne $stateStream) {$stateStream.Dispose();$stateStream=$null}})) {
            try {& $cleanup} catch {$report.valid=$false;$report.exitCode=2;$report.code='finalize_cleanup_failed'}
        }
    } finally {
        foreach ($key in $originalEnvironment.Keys) {
            try {[Environment]::SetEnvironmentVariable([string]$key,[string]$originalEnvironment[$key],[EnvironmentVariableTarget]::Process)}
            catch {$report.valid=$false;$report.exitCode=2;$report.code='environment_restore_failed'}
        }
        if (-not $report.valid) {
            $report.installationSha256='';$report.deploymentSha256='';$report.publicOrigin='';$report.bundleArchiveSha256='';$report.bundleManifestSha256=''
            if ($offlineInstallInputs.mode -ceq 'Restore') {$report.sourceBackupManifestSha256='';$report.recoveryAuditEventId=''}
            if ($owned -and $null -ne $state) {
                $failureStream=$null
                try {
                    $failureStream=[IO.File]::Open($statePath,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::Read)
                    $state.status='failed';$state.code=$report.code;Set-StageState $failureStream $state
                } catch {$report.exitCode=2;$report.code='failure_state_write_failed'}
                finally {if ($null -ne $failureStream) {try {$failureStream.Dispose()} catch {$report.exitCode=2;$report.code='failure_state_write_failed'}}}
            }
        }
    }
}
$report|ConvertTo-Json -Depth 8 -Compress
exit $report.exitCode
