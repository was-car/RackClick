#requires -Version 5.1
param([string]$FixtureHome)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$project=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$base=Join-Path $project '.local\provisioning-labs'
$sqlFixtureHome=[IO.Path]::GetFullPath($FixtureHome)
if([IO.Path]::GetDirectoryName($sqlFixtureHome)-cne$base-or[IO.Path]::GetFileName($sqlFixtureHome)-cnotmatch'^instance218-[a-f0-9]{32}$'){throw 'only_current_test_fixture_allowed'}
$root=Join-Path $sqlFixtureHome 'positive new'
if([IO.File]::Exists((Join-Path $root 'pgdata\postmaster.pid'))){throw 'fixture_postgres_not_stopped'}
. (Join-Path $project 'tools/windows/RackClick.Instance.ps1')
$manifestPath=Join-Path $root 'instance.json'
$m=[IO.File]::ReadAllText($manifestPath)|ConvertFrom-Json
if($m.rootPath-cne$root-or$m.kind-cne'RackClickLabInstance'-or$m.state-cne'initialized'){throw 'fixture_binding_invalid'}
$runtimePath=Join-Path $root 'private\runtime.json'
$original=[IO.File]::ReadAllText($runtimePath)|ConvertFrom-Json
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
if(@($original.PSObject.Properties.Name)-ccontains'schemaVersion'){
    # Resume only this owned test fixture after a fixture assertion failure;
    # the production writer's existing-destination rejection is unchanged.
    $descriptor=$original
    $null=Get-SqlRuntimeDefinition $descriptor $root $m.id $m.database $m.runtime
}else{$descriptor=New-SqlProtectedRuntimeStore $root $m.id $sid $m.database $m.runtime $original.connectionString}
[IO.File]::WriteAllText($runtimePath,($descriptor|ConvertTo-Json -Depth 5 -Compress),(New-Object Text.UTF8Encoding($false)))
$m.secretFiles.'runtime.json'=Get-RuntimeConfigDigest $runtimePath
[IO.File]::WriteAllText($manifestPath,($m|ConvertTo-Json -Depth 5 -Compress),(New-Object Text.UTF8Encoding($false)))
$manifestHash=Get-RuntimeConfigDigest $manifestPath
$instance=$null;$writeDenied=$false
try{
    $instance=Read-RackClickInstance $root $manifestHash
    if($null-ne$instance.runtimeConnectionString-or$null-eq$instance.sqlSecret){throw 'plaintext_in_instance_result'}
    $environment=@{};Set-SqlRuntimeEnvironment $environment $instance.sqlSecret
    if($environment.SqlSecret__Enabled-cne'true'-or$null-ne$environment.ConnectionStrings__RackClick){throw 'environment_not_protected'}
    try{$stream=[IO.File]::Open($instance.sqlSecret.file,'Open','Write','None');$stream.Dispose()}catch [IO.IOException]{$writeDenied=$true}
    if(-not$writeDenied){throw 'ciphertext_not_held'}
}finally{Close-RackClickInstance $instance}
$file=Join-Path $root ('sql-security\'+$m.id+'\sql-secrets\runtime.bin')
$bytes=[IO.File]::ReadAllBytes($file)
try{
    $changed=$bytes.Clone();$changed[$changed.Length-1]=$changed[$changed.Length-1]-bxor 1;[IO.File]::WriteAllBytes($file,$changed)
    $caught=$false
    try{$bad=Read-RackClickInstance $root $manifestHash;Close-RackClickInstance $bad}catch{if($_.Exception.Message-cne'instance_sql_ciphertext_invalid'){throw};$caught=$true}
    if(-not$caught){throw 'altered_ciphertext_accepted'}
}finally{[IO.File]::WriteAllBytes($file,$bytes)}
@{result='PASS';checks=4;preparedFixtureOnly=$true;metadataOnlyInstanceResult=$true;ciphertextHeld=$writeDenied;alteredCiphertextRejected=$caught;postgresStarted=$false;legacyOwnerFilesStillPresent=$true;productionAclOrServiceTested=$false;vmOperations=0}|ConvertTo-Json -Compress
