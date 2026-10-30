#requires -Version 5.1
<# NEW private lab deployment only: staging, native instance and external TLS profile.
   No Windows service, downloads, trust-store writes, adoption or existing-root reuse.
#>
[CmdletBinding()]
param([string]$ManifestPath='',[string]$ExpectedManifestSha256='',[string]$ServerPath='',[string]$FrontendPath='',
      [string]$DotNetPath='',[string]$PostgresBinPath='',[string]$DestinationPath='',[int]$PostgresPort=0,[int]$HttpPort=0,
      [string]$BootstrapUser='',[string]$SystemhausName='')
$creationInputs=@{manifest=$ManifestPath;manifestHash=$ExpectedManifestSha256;server=$ServerPath;frontend=$FrontendPath;
    dotnet=$DotNetPath;pg=$PostgresBinPath;destination=$DestinationPath;pgPort=$PostgresPort;httpPort=$HttpPort;user=$BootstrapUser;house=$SystemhausName}
. (Join-Path $PSScriptRoot 'RackClick.Deployment.ps1')

function Stop-CreationCheck {
    param([string]$Code,[int]$ExitCode=2)
    $failure=New-Object InvalidOperationException($Code)
    $failure.Data['creationCode']=$Code;$failure.Data['creationExit']=$ExitCode
    throw $failure
}

function Clear-CreationInheritedConfiguration {
    param([hashtable]$Original)
    # Process only, never User/Machine. Colon aliases cannot be put in Gate's env map.
    foreach ($key in [Environment]::GetEnvironmentVariables().Keys) {
        if ([string]$key -match '^(?i:Kestrel|ConnectionStrings|Bootstrap|RackClick)(:|__)' -or
            [string]$key -match '^(?i:PG|DOTNET_|ASPNETCORE_)' -or
            [string]$key -in @('URLS','HTTP_PORTS','HTTPS_PORTS','PublicOrigin','DevelopmentLoopbackHttp')) {
            $Original[[string]$key]=[Environment]::GetEnvironmentVariable([string]$key,[EnvironmentVariableTarget]::Process)
            [Environment]::SetEnvironmentVariable([string]$key,$null,[EnvironmentVariableTarget]::Process)
        }
    }
}

function Invoke-CreationChild {
    param([string]$Script,[string[]]$Arguments,[string]$Root,[string]$Logs)
    if ($Script -cnotin @('Stage-ServerDistribution.ps1','New-RackClickLabInstance.ps1','New-RackClickLabHttpsProfile.ps1')) { Stop-CreationCheck 'child_script_not_allowed' }
    $scriptPath=Join-Path $PSScriptRoot $Script;Assert-BackupNoReparse $scriptPath
    $handle=$null
    try {
        $values=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$scriptPath)+$Arguments
        $handle=Start-RackClickOwnedProcess -Executable (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -Arguments $values -WorkingDirectory $Root -Environment @{} -LogDirectory $Logs -Label $Script.Replace('.ps1','')
        $result=Wait-RackClickOwnedProcess -Handle $handle -TimeoutSeconds 240
        if ($result.exitCode -eq 124) { Stop-CreationCheck 'child_timeout' 1 }
        if ($result.stderr.Length -ne 0 -or $result.stdout.Length -gt 16384) { Stop-CreationCheck 'child_output_invalid' }
        try {$value=$result.stdout|ConvertFrom-Json} catch {Stop-CreationCheck 'child_output_invalid'}
        if ($value -isnot [Management.Automation.PSCustomObject] -or $value.exitCode -isnot [int] -or $value.valid -isnot [bool] -or
            $value.code -isnot [string] -or $value.code -cnotmatch '^[a-z][a-z0-9_]{0,79}$' -or
            $value.exitCode -ne $result.exitCode -or $value.exitCode -notin @(0,1,2) -or $value.valid -ne ($value.exitCode -eq 0)) { Stop-CreationCheck 'child_output_invalid' }
        if (-not $value.valid) {Stop-CreationCheck $value.code $value.exitCode}
        return $value
    } finally {
        if ($null -ne $handle) {
            try {Stop-RackClickOwnedProcess $handle} finally {$handle.Process.Dispose()}
        }
    }
}

$report=[ordered]@{valid=$false;exitCode=2;code='preflight_failed';deploymentPath='';deploymentId='';deploymentSha256='';instanceId='';url='';scope='Private loopback lab deployment; not Windows service or final installation acceptance'}
$phase='preflight';$owned=$false;$stateStream=$null;$state=$null;$sourceLocks=@();$instance=$null;$https=$null;$deployment=$null
$creationOriginalEnvironment=@{}
try {
    if ($creationInputs.manifestHash -notmatch '^[a-fA-F0-9]{64}$') {Stop-CreationCheck 'manifest_reference_required'}
    $paths=@{}
    foreach ($name in @('manifest','server','frontend','dotnet','pg','destination')) {$paths[$name]=Get-StageLocalPath $creationInputs[$name]}
    $root=$paths.destination;Assert-InstanceTechnicalRoot $root
    $parent=[IO.Path]::GetDirectoryName($root)
    if (-not [IO.Directory]::Exists($parent)) {Stop-CreationCheck 'destination_parent_missing' 1}
    Assert-BackupNoReparse $parent
    if ((New-Object IO.DriveInfo($root.Substring(0,3))).DriveType -ne [IO.DriveType]::Fixed) {Stop-CreationCheck 'path_not_local_fixed'}
    if ([IO.File]::Exists($root) -or [IO.Directory]::Exists($root)) {Stop-CreationCheck 'destination_exists' 1}
    foreach ($other in @($paths.manifest,$paths.server,$paths.frontend,$paths.pg,[IO.Path]::GetDirectoryName($paths.dotnet))) {
        if (Test-StageOverlap $root $other) {Stop-CreationCheck 'paths_overlap'}
    }
    foreach ($name in @('manifest','server','frontend','dotnet','pg')) {
        if (-not (Test-Path -LiteralPath $paths[$name])) {Stop-CreationCheck 'input_path_missing' 1};Assert-BackupNoReparse $paths[$name]
    }
    $user=Assert-InstanceDisplayName $creationInputs.user;$house=Assert-InstanceDisplayName $creationInputs.house
    if ($creationInputs.pgPort -eq $creationInputs.httpPort) {Stop-CreationCheck 'ports_must_differ'}
    Assert-InstancePort $creationInputs.pgPort;Assert-InstancePort $creationInputs.httpPort
    Clear-CreationInheritedConfiguration $creationOriginalEnvironment
    # Read locks bind preflight to the exact manifest and its source files being copied.
    $sourceLocks += [IO.File]::Open($paths.manifest,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $null=Invoke-StageIntegrity $paths.manifest $creationInputs.manifestHash $paths.server $paths.frontend
    $sourceManifest=[IO.File]::ReadAllText($paths.manifest,[Text.Encoding]::UTF8)|ConvertFrom-Json
    foreach ($kind in @('server','frontend')) {
        foreach ($entry in $sourceManifest.distributions.$kind.PSObject.Properties) {
            $source=Join-Path $paths[$kind] $entry.Name.Replace('/',[IO.Path]::DirectorySeparatorChar);Assert-BackupNoReparse $source
            $sourceLocks += [IO.File]::Open($source,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        }
    }
    $null=Invoke-StageIntegrity $paths.manifest $creationInputs.manifestHash $paths.server $paths.frontend
    $null=Invoke-StageRuntime $paths.dotnet $paths.pg $paths.server
    foreach ($name in @('initdb','pg_ctl','pg_isready','psql')) {
        $tool=Join-Path $paths.pg ($name+'.exe');Assert-BackupNoReparse $tool
        if (-not (Test-RuntimeX64Pe $tool)) {Stop-CreationCheck 'postgres_architecture_invalid' 1}
        $version=Invoke-RuntimeVersionProbe $tool '--version'
        if ($version.code -cne 'ok' -or $version.output.Trim() -cne ($name+' (PostgreSQL) 17.11')) {Stop-CreationCheck 'postgres_version_required_17_11' 1}
    }
    if (-not ('Security.Cryptography.X509Certificates.CertificateRequest' -as [type]) -or
        -not ('Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder' -as [type]) -or
        -not [Enum]::IsDefined([Security.Cryptography.X509Certificates.X509KeyStorageFlags],'EphemeralKeySet')) {Stop-CreationCheck 'https_framework_api_unavailable' 1}
    # Nothing has been written to the requested root before every preflight passes.
    $null=New-BackupPrivateDirectory $root;$owned=$true
    $id=[guid]::NewGuid().ToString('D');$report.deploymentPath=$root;$report.deploymentId=$id
    $state=[ordered]@{schemaVersion=1;deploymentId=$id;status='in-progress';code='components_pending'}
    $statePath=Join-Path $root 'deployment-state.json'
    $stateStream=[IO.File]::Open($statePath,[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::Read)
    Set-StageState $stateStream $state
    $logs=New-BackupPrivateDirectory (Join-Path $root 'logs')
    $distributionPath=Join-Path $root 'distribution';$instancePath=Join-Path $root 'instance';$httpsPath=Join-Path $root 'https'
    $phase='stage'
    $stage=Invoke-CreationChild 'Stage-ServerDistribution.ps1' @('-ManifestPath',$paths.manifest,'-ExpectedManifestSha256',$creationInputs.manifestHash,'-ServerPath',$paths.server,'-FrontendPath',$paths.frontend,'-DotNetPath',$paths.dotnet,'-PostgresBinPath',$paths.pg,'-DestinationPath',$distributionPath) $root $logs
    # Profiles14/15 have one additional application DLL; historical9..13 unchanged.
    $expectedVerified=if ($sourceManifest.schema -in @(14,15)) {28+$sourceManifest.schema} else {27+$sourceManifest.schema}
    if ($stage.code -cne 'artifacts_staged' -or $stage.destinationPath -cne $distributionPath -or $stage.verifiedFiles -ne $expectedVerified -or $stage.receiptSha256 -cnotmatch '^[a-f0-9]{64}$') {Stop-CreationCheck 'receipt_invalid'}
    $phase='instance'
    $created=Invoke-CreationChild 'New-RackClickLabInstance.ps1' @('-StagePath',$distributionPath,'-ExpectedManifestSha256',$creationInputs.manifestHash,'-ExpectedReceiptSha256',$stage.receiptSha256,'-DotNetPath',$paths.dotnet,'-PostgresBinPath',$paths.pg,'-InstancePath',$instancePath,'-PostgresPort',[string]$creationInputs.pgPort,'-PublicOrigin',('http://127.0.0.1:'+[string]$creationInputs.httpPort),'-BootstrapUser',$user,'-SystemhausName',$house,'-DevelopmentLoopbackHttp') $root $logs
    if ($created.code -cne 'instance_initialized' -or $created.instancePath -cne $instancePath -or $created.instanceManifestSha256 -cnotmatch '^[a-f0-9]{64}$') {Stop-CreationCheck 'receipt_invalid'}
    $instance=Read-RackClickInstance $instancePath $created.instanceManifestSha256
    if ($instance.id -cne $created.instanceId -or [IO.File]::Exists((Join-Path $instance.pgData 'postmaster.pid'))) {Stop-CreationCheck 'stopped_identity_invalid'}
    $phase='https'
    $tls=Invoke-CreationChild 'New-RackClickLabHttpsProfile.ps1' @('-InstancePath',$instancePath,'-ExpectedInstanceSha256',$created.instanceManifestSha256,'-DestinationPath',$httpsPath) $root $logs
    if ($tls.code -cne 'https_profile_created' -or $tls.profilePath -cne $httpsPath -or $tls.profileSha256 -cnotmatch '^[a-f0-9]{64}$') {Stop-CreationCheck 'receipt_invalid'}
    $https=Read-RackClickHttpsProfile -Instance $instance -ProfilePath $httpsPath -ExpectedProfileSha256 $tls.profileSha256
    if ($https.certificateSha256 -cne $tls.certificateSha256 -or [IO.File]::Exists((Join-Path $instance.pgData 'postmaster.pid'))) {Stop-CreationCheck 'stopped_identity_invalid'}
    $phase='finalize'
    $state.status='prepared';$state.code='deployment_prepared';Set-StageState $stateStream $state
    $stateStream.Dispose();$stateStream=$null
    $receipt=[ordered]@{schemaVersion=1;kind='RackClickPrivateDeployment';state='prepared';id=$id;rootPath=$root;instanceId=$instance.id;instanceManifestSha256=$created.instanceManifestSha256;stageManifestSha256=$creationInputs.manifestHash.ToLowerInvariant();stageReceiptSha256=$stage.receiptSha256;httpsProfileSha256=$tls.profileSha256;publicOrigin=$https.origin}
    $receiptPath=Join-Path $root 'deployment.json'
    Write-BackupNewText $receiptPath ($receipt|ConvertTo-Json -Depth 4 -Compress)
    $digest=Get-RuntimeConfigDigest $receiptPath
    $deployment=Read-RackClickPrivateDeployment -DeploymentPath $root -ExpectedDeploymentSha256 $digest
    if (-not $deployment.httpsValidated -or $deployment.id -cne $id -or $deployment.instance.id -cne $instance.id) {Stop-CreationCheck 'receipt_invalid'}
    $report.valid=$true;$report.exitCode=0;$report.code='deployment_prepared';$report.deploymentSha256=$digest;$report.instanceId=$instance.id;$report.url=$https.origin
} catch {
    $cause='failed';$exitValue=2
    foreach ($pair in @(@('creationCode','creationExit'),@('deploymentCode','deploymentExit'),@('httpsCode','httpsExit'),@('instanceCode','instanceExit'),@('stageCode','stageExit'),@('code','exitCode'))) {
        if ($_.Exception.Data.Contains($pair[0])) {$cause=[string]$_.Exception.Data[$pair[0]];$exitValue=[int]$_.Exception.Data[$pair[1]];break}
    }
    if ($cause -cnotmatch '^[a-z][a-z0-9_]{0,79}$' -or $exitValue -notin @(1,2)) {$cause='failed';$exitValue=2}
    $report.valid=$false;$report.exitCode=$exitValue;$report.code=$phase+'_'+$cause;$report.deploymentSha256='';$report.instanceId='';$report.url=''
    try {Close-RackClickPrivateDeployment $deployment;$deployment=$null}
    catch {$report.code=$phase+'_cleanup_failed';$report.exitCode=2}
    if ($owned -and $null -ne $state) {
        try {
            if ($null -eq $stateStream) {$stateStream=[IO.File]::Open($statePath,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::Read)}
            $state.status='failed';$state.code=$report.code;Set-StageState $stateStream $state
        } catch {$report.code='failure_state_write_failed';$report.exitCode=2}
    }
} finally {
    try {
        $cleanupFailed=$false
        foreach ($cleanup in @({Close-RackClickPrivateDeployment $deployment},{Close-RackClickHttpsProfile $https},{Close-RackClickInstance $instance},{if ($null -ne $stateStream) {$stateStream.Dispose()}})) {
            try {& $cleanup} catch {$cleanupFailed=$true}
        }
        foreach ($stream in $sourceLocks) {try {$stream.Dispose()} catch {$cleanupFailed=$true}}
        if ($cleanupFailed) {
            $report.valid=$false;$report.exitCode=2;$report.code='finalize_cleanup_failed';$report.deploymentSha256='';$report.instanceId='';$report.url=''
        }
    } finally {
        # Even an exceptional Dispose above cannot bypass Process-environment restoration.
        $restoreFailed=$false
        foreach ($key in $creationOriginalEnvironment.Keys) {
            try {[Environment]::SetEnvironmentVariable([string]$key,[string]$creationOriginalEnvironment[$key],[EnvironmentVariableTarget]::Process)}
            catch {$restoreFailed=$true}
        }
        if ($restoreFailed) {$report.valid=$false;$report.exitCode=2;$report.code='environment_restore_failed';$report.deploymentSha256='';$report.instanceId='';$report.url=''}
        if (-not $report.valid -and $owned -and $null -ne $state) {
            $failureStream=$null
            try {
                $failureStream=[IO.File]::Open($statePath,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::Read)
                $state.status='failed';$state.code=$report.code;Set-StageState $failureStream $state
            } catch {$report.code='failure_state_write_failed';$report.exitCode=2}
            finally {if ($null -ne $failureStream) {try {$failureStream.Dispose()} catch {$report.code='failure_state_write_failed';$report.exitCode=2}}}
        }
    }
}
$report|ConvertTo-Json -Compress
exit $report.exitCode
