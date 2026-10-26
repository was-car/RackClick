#requires -Version 5.1
[CmdletBinding()]
param([string]$StagePath='', [string]$ExpectedManifestSha256='', [string]$ExpectedReceiptSha256='', [string]$DotNetPath='', [string]$PostgresBinPath='', [string]$InstancePath='', [int]$PostgresPort=0, [string]$PublicOrigin='', [string]$BootstrapUser='', [string]$SystemhausName='', [switch]$DevelopmentLoopbackHttp)
$instanceInputs=@{stage=$StagePath;manifest=$ExpectedManifestSha256;receipt=$ExpectedReceiptSha256;dotnet=$DotNetPath;pg=$PostgresBinPath;root=$InstancePath;port=$PostgresPort;origin=$PublicOrigin;user=$BootstrapUser;house=$SystemhausName;http=[bool]$DevelopmentLoopbackHttp}
. (Join-Path $PSScriptRoot 'RackClick.Instance.ps1')
$report=[ordered]@{schemaVersion=1;valid=$false;exitCode=2;code='instance_provision_failed';instanceId='';instancePath='';instanceManifestSha256='';scope='New private local development HTTP instance only; no Windows service or HTTPS acceptance'}
$pgHandle=$null; $stateStream=$null; $state=$null; $owned=$false; $success=$false; $stageLocks=@()
try {
    if (-not $instanceInputs.http) { Stop-InstanceCheck 'development_loopback_optin_required' }
    $root=Get-StageLocalPath $instanceInputs.root; $stage=Get-StageLocalPath $instanceInputs.stage
    Assert-InstanceTechnicalRoot $root
    $dotnet=Get-StageLocalPath $instanceInputs.dotnet; $pg=Get-StageLocalPath $instanceInputs.pg
    $origin=Get-InstanceOrigin $instanceInputs.origin
    if ($instanceInputs.port -eq $origin.port) { Stop-InstanceCheck 'ports_must_differ' }
    $user=Assert-InstanceDisplayName $instanceInputs.user; $house=Assert-InstanceDisplayName $instanceInputs.house
    foreach ($other in @($stage,$pg,[IO.Path]::GetDirectoryName($dotnet))) { if (Test-StageOverlap $root $other) { Stop-InstanceCheck 'instance_paths_overlap' } }
    if ([IO.File]::Exists($root) -or [IO.Directory]::Exists($root)) { Stop-InstanceCheck 'instance_destination_exists' 1 }
    Assert-InstancePort $instanceInputs.port; Assert-InstancePort $origin.port
    $stageLocks=Open-InstanceStageLocks $stage $instanceInputs.manifest $instanceInputs.receipt
    $stageSchema=Get-StageSchema $stage
    $null=Invoke-StageRuntime $dotnet $pg (Join-Path $stage 'server')
    $null=Assert-BackupPostgresTools $pg
    foreach ($name in @('initdb','pg_ctl')) {
        $path=Join-Path $pg ($name+'.exe'); Assert-BackupNoReparse $path
        if (-not (Test-RuntimeX64Pe $path)) { Stop-InstanceCheck 'postgres_architecture_invalid' 1 }
        $version=Invoke-RuntimeVersionProbe $path '--version'
        if ($version.code -ne 'ok' -or $version.output.Trim() -cne ($name+' (PostgreSQL) 17.11')) { Stop-InstanceCheck 'postgres_version_invalid' 1 }
    }
    $null=New-BackupPrivateDirectory $root; $owned=$true
    $id=[guid]::NewGuid().ToString('D');$suffix=$id.Replace('-','');$report.instanceId=$id;$report.instancePath=$root
    $stateStream=[IO.File]::Open((Join-Path $root 'instance-state.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::Read)
    $state=[ordered]@{schemaVersion=1;instanceId=$id;status='in-progress';code='initialization_pending'}
    Set-StageState $stateStream $state
    $lockFile=[IO.File]::Open((Join-Path $root 'instance.lock'),[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None);$lockFile.Dispose()
    $private=New-BackupPrivateDirectory (Join-Path $root 'private');$logs=New-BackupPrivateDirectory (Join-Path $root 'logs')
    $cluster='rc_cluster_'+$suffix;$owner='rc_owner_'+$suffix;$runtime='rc_runtime_'+$suffix;$database='rc_db_'+$suffix
    $clusterPassword=New-InstancePassword;$ownerPassword=New-InstancePassword;$runtimePassword=New-InstancePassword;$appPassword=New-InstancePassword
    Write-BackupNewText (Join-Path $private 'cluster-password.txt') $clusterPassword
    Write-BackupNewText (Join-Path $private 'owner-password.txt') $ownerPassword
    $environment=New-InstanceEnvironment @{PGCLIENTENCODING='UTF8';PGCONNECT_TIMEOUT='5'}
    $null=Invoke-InstanceChild (Join-Path $pg 'initdb.exe') @('-D','pgdata','-U',$cluster,'--pwfile=private/cluster-password.txt','--auth-host=scram-sha-256','--auth-local=scram-sha-256','--encoding=UTF8','--locale=C','--data-checksums') $root $environment $logs 'initdb' -TimeoutSeconds 120
    $configuration="`nlisten_addresses='127.0.0.1'`nport=$($instanceInputs.port)`npassword_encryption='scram-sha-256'`n"
    [IO.File]::AppendAllText((Join-Path $root 'pgdata/postgresql.conf'),$configuration,(New-Object Text.UTF8Encoding($false)))
    $pgHandle=Start-RackClickOwnedProcess -Executable (Join-Path $pg 'postgres.exe') -Arguments @('-D','pgdata') -WorkingDirectory $root -Environment $environment -LogDirectory $logs -Label 'postgres'
    $clusterProfile=@{host='127.0.0.1';port=$instanceInputs.port;database='postgres';user=$cluster;password=$clusterPassword}
    $ready=$false
    for ($attempt=0;$attempt -lt 60;$attempt++) {
        if ($pgHandle.Process.HasExited) { Stop-InstanceCheck 'postgres_start_failed' 1 }
        try { Assert-BackupServerVersion $pg $clusterProfile; $ready=$true; break } catch { Start-Sleep -Milliseconds 100 }
    }
    if (-not $ready) { Stop-InstanceCheck 'postgres_start_timeout' 1 }
    $arguments=@('-X','-A','-t','-v','ON_ERROR_STOP=1')+(Get-BackupConnectionArguments $clusterProfile 'postgres')
    $sql="CREATE ROLE $owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '$ownerPassword'; CREATE ROLE $runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '$runtimePassword';"
    $null=Invoke-BackupPg (Join-Path $pg 'psql.exe') $arguments $clusterProfile $sql
    $null=Invoke-BackupPg (Join-Path $pg 'psql.exe') $arguments $clusterProfile "CREATE DATABASE $database OWNER $owner TEMPLATE template0 ENCODING 'UTF8';"
    $null=Invoke-BackupPg (Join-Path $pg 'psql.exe') $arguments $clusterProfile "REVOKE ALL ON DATABASE $database FROM PUBLIC; GRANT CONNECT ON DATABASE $database TO $runtime;"
    $ownerConnection=Get-InstanceConnection $instanceInputs.port $database $owner $ownerPassword
    $runtimeConnection=Get-InstanceConnection $instanceInputs.port $database $runtime $runtimePassword
    $bootstrapEnvironment=New-InstanceEnvironment @{DOTNET_ROOT=[IO.Path]::GetDirectoryName($dotnet);DOTNET_CLI_TELEMETRY_OPTOUT='1';DOTNET_NOLOGO='1';DOTNET_GENERATE_ASPNET_CERTIFICATE='false';ConnectionStrings__RackClick=$ownerConnection;Bootstrap__User=$user;Bootstrap__House=$house;ASPNETCORE_ENVIRONMENT='Development'}
    $null=Invoke-InstanceChild $dotnet @((Join-Path $stage 'server/RackClick.Server.dll'),'--bootstrap') $root $bootstrapEnvironment $logs 'bootstrap' -InputText ($appPassword+"`n")
    $ownerProfile=@{host='127.0.0.1';port=$instanceInputs.port;database=$database;user=$owner;password=$ownerPassword}
    $ownerArguments=@('-X','-A','-t','-v','ON_ERROR_STOP=1')+(Get-BackupConnectionArguments $ownerProfile $database)
    $null=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "GRANT USAGE ON SCHEMA public TO $runtime; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO $runtime; REVOKE CREATE ON SCHEMA public FROM PUBLIC;"
    $schema=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile 'SELECT string_agg(version::text,'','' ORDER BY version) FROM schema_migration;'
    if ($schema -cne ((1..$stageSchema)-join ',')) { Stop-InstanceCheck 'bootstrap_schema_invalid' 1 }
    # Read the authoritative normalized username via ASCII hex, avoiding system-ANSI stdout decoding.
    $userHex=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "SELECT encode(convert_to(username,'UTF8'),'hex') FROM app_user;"
    if ($userHex -notmatch '^(?:[a-f0-9]{2})+$') { Stop-InstanceCheck 'bootstrap_identity_invalid' 1 }
    $userBytes=New-Object byte[] ($userHex.Length/2)
    for ($i=0;$i -lt $userBytes.Length;$i++) { $userBytes[$i]=[Convert]::ToByte($userHex.Substring($i*2,2),16) }
    $actualUser=[Text.Encoding]::UTF8.GetString($userBytes)
    Write-BackupNewText (Join-Path $private 'runtime.json') (@{connectionString=$runtimeConnection}|ConvertTo-Json -Compress)
    Write-BackupNewText (Join-Path $private 'admin-login.json') (@{username=$actualUser;password=$appPassword}|ConvertTo-Json -Compress)
    Write-BackupNewText (Join-Path $private 'backup-profile.json') (@{schemaVersion=1;host='127.0.0.1';port=$instanceInputs.port;database=$database;user=$owner;passwordFile=(Join-Path $private 'owner-password.txt')}|ConvertTo-Json -Compress)
    Assert-InstanceOwnedPostgres $pgHandle (Join-Path $root 'pgdata')
    $null=Invoke-InstanceChild (Join-Path $pg 'pg_ctl.exe') @('stop','-D','pgdata','-m','fast','-w','-t','30') $root $environment $logs 'postgres-stop'
    Stop-RackClickOwnedProcess -Handle $pgHandle;$pgHandle=$null
    if ([IO.File]::Exists((Join-Path $root 'pgdata/postmaster.pid'))) { Stop-InstanceCheck 'postgres_stop_unconfirmed' 1 }
    $secrets=[ordered]@{}
    foreach ($name in @('admin-login.json','backup-profile.json','cluster-password.txt','owner-password.txt','runtime.json')) { $secrets[$name]=Get-RuntimeConfigDigest (Join-Path $private $name) }
    $manifest=[ordered]@{schemaVersion=1;kind='RackClickLabInstance';id=$id;rootPath=$root;stagePath=$stage;stageManifestSha256=$instanceInputs.manifest.ToLowerInvariant();stageReceiptSha256=$instanceInputs.receipt.ToLowerInvariant();dotnetPath=$dotnet;postgresBinPath=$pg;postgresPort=$instanceInputs.port;httpPort=$origin.port;publicOrigin=$origin.value;database=$database;owner=$owner;runtime=$runtime;clusterAdmin=$cluster;state='initialized';developmentLoopbackHttp=$true;secretFiles=$secrets}
    Write-BackupNewText (Join-Path $root 'instance.json') ($manifest|ConvertTo-Json -Depth 5 -Compress)
    $report.instanceManifestSha256=Get-RuntimeConfigDigest (Join-Path $root 'instance.json')
    $state.status='initialized';$state.code='instance_initialized';Set-StageState $stateStream $state
    $report.valid=$true;$report.exitCode=0;$report.code='instance_initialized';$success=$true
} catch {
    foreach ($pair in @(@('instanceCode','instanceExit'),@('code','exitCode'),@('stageCode','stageExit'))) {
        if ($_.Exception.Data.Contains($pair[0])) { $report.code=$_.Exception.Data[$pair[0]];$report.exitCode=$_.Exception.Data[$pair[1]];break }
    }
} finally {
    if ($null -ne $pgHandle) { try { Stop-RackClickOwnedProcess -Handle $pgHandle } catch { $report.code='owned_process_cleanup_failed';$report.exitCode=2;$report.valid=$false;$success=$false } }
    if ($owned -and -not $success -and $null -ne $stateStream -and $null -ne $state) {
        try { $state.status='failed';$state.code=$report.code;Set-StageState $stateStream $state } catch { $report.code='failure_state_write_failed';$report.exitCode=2 }
    }
    if ($null -ne $stateStream) { $stateStream.Dispose() }
    foreach ($stream in $stageLocks) { $stream.Dispose() }
}
$report | ConvertTo-Json -Depth 4 -Compress
exit $report.exitCode
