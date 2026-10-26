#requires -Version 5.1
<# A NEW operational instance recovered from an explicitly trusted native backup.
   Dot-sourcing exposes preflight helpers only; no probes, files or processes.
   This is deliberately separate from bootstrap and the isolated rc_restore_* tool.
#>
[CmdletBinding()]
param([string]$StagePath='', [string]$ExpectedManifestSha256='', [string]$ExpectedReceiptSha256='',
      [string]$DotNetPath='', [string]$PostgresBinPath='', [string]$InstancePath='', [int]$PostgresPort=0,
      [string]$PublicOrigin='', [string]$RecoveryUser='', [string]$BackupPath='',
      [string]$ExpectedBackupManifestSha256='', [switch]$DevelopmentLoopbackHttp)
$recoveredInputs=@{stage=$StagePath;manifest=$ExpectedManifestSha256;receipt=$ExpectedReceiptSha256;dotnet=$DotNetPath;
    pg=$PostgresBinPath;root=$InstancePath;port=$PostgresPort;origin=$PublicOrigin;user=$RecoveryUser;backup=$BackupPath;
    backupHash=$ExpectedBackupManifestSha256;http=[bool]$DevelopmentLoopbackHttp}
. (Join-Path $PSScriptRoot 'RackClick.Instance.ps1')

function Stop-RecoveryCheck {
    param([string]$Code,[int]$ExitCode=2)
    $failure=New-Object InvalidOperationException($Code)
    $failure.Data['recoveryCode']=$Code;$failure.Data['recoveryExit']=$ExitCode
    throw $failure
}

function Clear-RecoveryInheritedConfiguration {
    param([hashtable]$Original)
    # Process only. Also remove colon aliases, which cannot be passed to the Gate map.
    foreach ($key in [Environment]::GetEnvironmentVariables().Keys) {
        if ([string]$key -match '^(?i:Kestrel|ConnectionStrings|Bootstrap|Recovery|RackClick)(:|__)' -or
            [string]$key -match '^(?i:PG|DOTNET_|ASPNETCORE_)' -or
            [string]$key -in @('URLS','HTTP_PORTS','HTTPS_PORTS','PublicOrigin','DevelopmentLoopbackHttp')) {
            $Original[[string]$key]=[Environment]::GetEnvironmentVariable([string]$key,[EnvironmentVariableTarget]::Process)
            [Environment]::SetEnvironmentVariable([string]$key,$null,[EnvironmentVariableTarget]::Process)
        }
    }
}

function Open-RecoveryBackup {
    param([string]$Path,[string]$ExpectedHash)
    $backup=$null
    try {
        if ($ExpectedHash -notmatch '^[a-fA-F0-9]{64}$') {Stop-RecoveryCheck 'backup_manifest_reference_required'}
        $root=Get-StageLocalPath $Path
        if (-not [IO.Directory]::Exists($root)) {Stop-RecoveryCheck 'backup_missing' 1}
        # The existing reader intentionally does not impose an ACL; this operational
        # wrapper requires the source dump (accounts/password hashes/sessions) private.
        foreach ($name in @('','manifest.json','data.dump')) {
            $inputPath=if ($name.Length -eq 0) {$root} else {Join-Path $root $name}
            Assert-BackupPrivateAcl $inputPath
        }
        $backup=Read-BackupManifest $root $ExpectedHash
        foreach ($stream in @($backup.manifestHandle,$backup.dumpHandle)) {Assert-BackupPrivateAcl $stream.Name}
        return $backup
    } catch {
        if ($null -ne $backup) {try {$backup.dumpHandle.Dispose()} finally {$backup.manifestHandle.Dispose()}}
        throw
    }
}

function Assert-RecoveryPostgresTools {
    param([string]$Bin)
    $null=Assert-BackupPostgresTools $Bin
    foreach ($name in @('initdb','pg_ctl','pg_isready')) {
        $path=Join-Path $Bin ($name+'.exe');Assert-BackupNoReparse $path
        if (-not (Test-RuntimeX64Pe $path)) {Stop-RecoveryCheck 'postgres_architecture_invalid' 1}
        $version=Invoke-RuntimeVersionProbe $path '--version'
        if ($version.code -cne 'ok' -or $version.output.Trim() -cne ($name+' (PostgreSQL) 17.11')) {Stop-RecoveryCheck 'postgres_version_required_17_11' 1}
    }
}

function Assert-RecoveryArchiveList {
    param([string]$Bin,[hashtable]$Backup)
    # No DB connection, SQL output or target-root write: validate archive parsing
    # before reserving the destination. pg_restore --list has no child server.
    $process=$null
    try {
        $start=New-Object Diagnostics.ProcessStartInfo
        $start.FileName=Join-Path $Bin 'pg_restore.exe'
        # PG17 filename argv is ANSI-sensitive; Unicode cwd plus the fixed ASCII
        # filename retains the operator's source path without aliases or copying.
        $start.Arguments=(@('--list','data.dump')|ForEach-Object {ConvertTo-RackClickProcessArgument $_}) -join ' '
        $start.WorkingDirectory=[IO.Path]::GetDirectoryName($Backup.path)
        $start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
        $start.RedirectStandardInput=$true;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
        foreach ($key in @($start.EnvironmentVariables.Keys)) {if ([string]$key -match '^(?i:PG)') {$start.EnvironmentVariables.Remove($key)}}
        $start.EnvironmentVariables['PGCLIENTENCODING']='UTF8'
        $start.EnvironmentVariables['LC_ALL']='C';$start.EnvironmentVariables['LANG']='C'
        $process=New-Object Diagnostics.Process;$process.StartInfo=$start
        if (-not $process.Start()) {Stop-RecoveryCheck 'backup_archive_list_failed' 1}
        $output=$process.StandardOutput.ReadToEndAsync();$errors=$process.StandardError.ReadToEndAsync();$process.StandardInput.Close()
        if (-not $process.WaitForExit(30000)) {$process.Kill();$null=$process.WaitForExit(5000);Stop-RecoveryCheck 'backup_archive_list_timeout' 1}
        if ($process.ExitCode -ne 0 -or $errors.Result.Length -ne 0) {Stop-RecoveryCheck 'backup_archive_invalid' 1}
        $listing=$output.Result
        if ($listing.Length -eq 0 -or $listing.Length -gt 4194304 -or
            $listing -cnotmatch '(?m)^;\s+Format: CUSTOM\r?$' -or
            $listing -cnotmatch '(?m)^;\s+Dumped from database version: 17\.11\r?$' -or
            $listing -cnotmatch '(?m)^;\s+Dumped by pg_dump version: 17\.11\r?$' -or
            $listing -cnotmatch '(?m)^;\s+TOC Entries: [1-9][0-9]*\r?$') {Stop-RecoveryCheck 'backup_archive_list_invalid' 1}
        $entries=@($listing -split '\r?\n'|Where-Object {$_.Length -gt 0 -and -not $_.StartsWith(';')})
        if ($entries.Count -eq 0 -or @($entries|Where-Object {$_ -cnotmatch '^\d+;\s+\d+\s+\d+\s+.+$'}).Count -ne 0 -or
            @($entries|Where-Object {$_ -cmatch '^\d+;\s+\d+\s+\d+\s+(?:DATABASE|TABLESPACE|SUBSCRIPTION)(?:\s|$)'}).Count -ne 0) {Stop-RecoveryCheck 'backup_archive_list_invalid' 1}
        foreach ($table in @('schema_migration','systemhaus','app_user','app_session','audit_event')) {
            if (@($entries|Where-Object {$_ -cmatch ('^\d+;\s+\d+\s+\d+\s+TABLE public '+$table+' \S+\s*$')}).Count -ne 1) {Stop-RecoveryCheck 'backup_archive_table_missing' 1}
        }
    } finally {
        if ($null -ne $process) {
            try {if (-not $process.HasExited) {$process.Kill();if (-not $process.WaitForExit(5000)) {Stop-RecoveryCheck 'backup_archive_list_cleanup_failed'}}} finally {$process.Dispose()}
        }
    }
}

function Invoke-RecoveryOwnedChild {
    param([string]$Executable,[string[]]$Arguments,[string]$Root,[hashtable]$Environment,[string]$Logs,[string]$Label,[string]$InputText='',[int]$TimeoutSeconds=300)
    $handle=$null
    try {
        $handle=Start-RackClickOwnedProcess -Executable $Executable -Arguments $Arguments -WorkingDirectory $Root -Environment $Environment -InputText $InputText -LogDirectory $Logs -Label $Label
        $result=Wait-RackClickOwnedProcess -Handle $handle -TimeoutSeconds $TimeoutSeconds
        if ($result.exitCode -ne 0) {
            # Only promote this canonical, bounded CLI rejection. Never reflect
            # arbitrary child JSON, duplicate keys, stderr or exception messages.
            if ($Label -ceq 'recover-admin' -and $result.exitCode -is [int] -and $result.exitCode -eq 1 -and
                $result.stderr -is [string] -and $result.stderr.Length -eq 0 -and
                $result.stdout -is [string] -and $result.stdout.Length -le 16384 -and
                $result.stdout.TrimEnd([char[]]"`r`n") -ceq '{"status":"rejected","error":"recovery_username_exists"}') {
                Stop-RecoveryCheck 'recovery_username_exists' 1
            }
            Stop-RecoveryCheck ($Label.Replace('-','_')+'_failed') 1
        }
        return $result
    } finally {
        if ($null -ne $handle) {try {Stop-RackClickOwnedProcess $handle} finally {$handle.Process.Dispose()}}
    }
}

function Stop-RecoveryPostgresAfterFailure {
    param([hashtable]$Handle,[string]$Bin,[string]$Root,[hashtable]$Environment,[string]$Logs)
    $pidPath=Join-Path $Root 'pgdata/postmaster.pid'
    try {
        if ([IO.File]::Exists($pidPath)) {
            Assert-InstanceOwnedPostgres $Handle (Join-Path $Root 'pgdata')
            $null=Invoke-RecoveryOwnedChild (Join-Path $Bin 'pg_ctl.exe') @('stop','-D','pgdata','-m','fast','-w','-t','30') $Root $Environment $Logs 'postgres-failure-stop' -TimeoutSeconds 45
            if ([IO.File]::Exists($pidPath)) {Stop-RecoveryCheck 'postgres_stop_unconfirmed' 1}
        }
    } finally {
        # A failed graceful stop falls back only to this owned Job. Never remove a
        # PID file or select another process from its numeric value.
        try {Stop-RackClickOwnedProcess $Handle} finally {$Handle.Process.Dispose()}
    }
    if ([IO.File]::Exists($pidPath)) {Stop-RecoveryCheck 'postgres_stop_unconfirmed' 1}
}

function Read-RecoveryCommitResult {
    param([hashtable]$Result,[string]$InstanceId)
    if ($Result.stderr.Length -ne 0 -or $Result.stdout.Length -gt 16384) {Stop-RecoveryCheck 'recovery_output_invalid'}
    try {$value=$Result.stdout|ConvertFrom-Json} catch {Stop-RecoveryCheck 'recovery_output_invalid'}
    $keys='action,auditEventId,createdGroupId,createdUserId,instanceId,requestId,revokedSessions,status,systemhausId,systemhausRevision'
    if ($value -isnot [pscustomobject] -or (($value.PSObject.Properties.Name|Sort-Object)-join ',') -cne $keys -or
        $value.status -cne 'committed' -or $value.action -cne 'deployment.recover' -or $value.instanceId -cne $InstanceId -or
        $value.revokedSessions -isnot [int] -or $value.revokedSessions -lt 0 -or
        ($value.systemhausRevision -isnot [int] -and $value.systemhausRevision -isnot [long]) -or $value.systemhausRevision -lt 2) {Stop-RecoveryCheck 'recovery_output_invalid'}
    foreach ($name in @('instanceId','systemhausId','createdUserId','createdGroupId','auditEventId','requestId')) {
        if ($value.$name -isnot [string] -or $value.$name -cnotmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$' -or
            $value.$name -ceq '00000000-0000-0000-0000-000000000000') {Stop-RecoveryCheck 'recovery_output_invalid'}
    }
    return $value
}

if ($MyInvocation.InvocationName -eq '.') {return}

$report=[ordered]@{schemaVersion=1;valid=$false;exitCode=2;code='instance_recovery_failed';instanceId='';instanceManifestSha256='';
    sourceBackupManifestSha256='';recoveryAuditEventId='';url='';scope='NEW private loopback recovered instance; not Windows service or final installation acceptance'}
$phase='preflight';$pgHandle=$null;$stateStream=$null;$state=$null;$owned=$false;$success=$false;$stageLocks=@();$backup=$null;$checkedInstance=$null
$recoveryOriginalEnvironment=@{}
try {
    if (-not $recoveredInputs.http) {Stop-RecoveryCheck 'development_loopback_optin_required'}
    $root=Get-StageLocalPath $recoveredInputs.root;$stage=Get-StageLocalPath $recoveredInputs.stage
    $dotnet=Get-StageLocalPath $recoveredInputs.dotnet;$pg=Get-StageLocalPath $recoveredInputs.pg;$backupRoot=Get-StageLocalPath $recoveredInputs.backup
    Assert-InstanceTechnicalRoot $root
    $origin=Get-InstanceOrigin $recoveredInputs.origin;$user=Assert-InstanceDisplayName $recoveredInputs.user
    if ($recoveredInputs.port -eq $origin.port) {Stop-RecoveryCheck 'ports_must_differ'}
    foreach ($other in @($stage,$backupRoot,$pg,[IO.Path]::GetDirectoryName($dotnet))) {if (Test-StageOverlap $root $other) {Stop-RecoveryCheck 'instance_paths_overlap'}}
    if ([IO.File]::Exists($root) -or [IO.Directory]::Exists($root)) {Stop-RecoveryCheck 'instance_destination_exists' 1}
    $parent=[IO.Path]::GetDirectoryName($root)
    if (-not [IO.Directory]::Exists($parent)) {Stop-RecoveryCheck 'destination_parent_missing' 1}
    Assert-BackupNoReparse $parent
    if ((New-Object IO.DriveInfo($root.Substring(0,3))).DriveType -ne [IO.DriveType]::Fixed) {Stop-RecoveryCheck 'path_not_local_fixed'}
    Assert-InstancePort $recoveredInputs.port;Assert-InstancePort $origin.port
    Clear-RecoveryInheritedConfiguration $recoveryOriginalEnvironment
    $backup=Open-RecoveryBackup $backupRoot $recoveredInputs.backupHash
    $stageLocks=Open-InstanceStageLocks $stage $recoveredInputs.manifest $recoveredInputs.receipt
    $stageSchema=Get-StageSchema $stage
    $null=Invoke-StageRuntime $dotnet $pg (Join-Path $stage 'server')
    Assert-RecoveryPostgresTools $pg;Assert-RecoveryArchiveList $pg $backup
    # Every destructive-looking step below only creates objects in this NEW root/cluster.
    $null=New-BackupPrivateDirectory $root;$owned=$true
    $id=[guid]::NewGuid().ToString('D');$suffix=$id.Replace('-','');$report.instanceId=$id
    $stateStream=[IO.File]::Open((Join-Path $root 'instance-state.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::Read)
    $state=[ordered]@{schemaVersion=1;instanceId=$id;status='in-progress';code='recovery_pending'};Set-StageState $stateStream $state
    $lockFile=[IO.File]::Open((Join-Path $root 'instance.lock'),[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None);$lockFile.Dispose()
    $private=New-BackupPrivateDirectory (Join-Path $root 'private');$logs=New-BackupPrivateDirectory (Join-Path $root 'logs')
    $cluster='rc_cluster_'+$suffix;$owner='rc_owner_'+$suffix;$runtime='rc_runtime_'+$suffix;$database='rc_db_'+$suffix
    $clusterPassword=New-InstancePassword;$ownerPassword=New-InstancePassword;$runtimePassword=New-InstancePassword;$appPassword=New-InstancePassword
    Write-BackupNewText (Join-Path $private 'cluster-password.txt') $clusterPassword
    Write-BackupNewText (Join-Path $private 'owner-password.txt') $ownerPassword
    $environment=New-InstanceEnvironment @{PGCLIENTENCODING='UTF8';PGCONNECT_TIMEOUT='5'}
    $phase='cluster'
    $null=Invoke-RecoveryOwnedChild (Join-Path $pg 'initdb.exe') @('-D','pgdata','-U',$cluster,'--pwfile=private/cluster-password.txt','--auth-host=scram-sha-256','--auth-local=scram-sha-256','--encoding=UTF8','--locale=C','--data-checksums') $root $environment $logs 'initdb'
    [IO.File]::AppendAllText((Join-Path $root 'pgdata/postgresql.conf'),("`nlisten_addresses='127.0.0.1'`nport="+[string]$recoveredInputs.port+"`npassword_encryption='scram-sha-256'`n"),(New-Object Text.UTF8Encoding($false)))
    $pgHandle=Start-RackClickOwnedProcess -Executable (Join-Path $pg 'postgres.exe') -Arguments @('-D','pgdata') -WorkingDirectory $root -Environment $environment -LogDirectory $logs -Label 'postgres'
    $clusterProfile=@{host='127.0.0.1';port=$recoveredInputs.port;database='postgres';user=$cluster;password=$clusterPassword};$ready=$false
    for ($attempt=0;$attempt -lt 60;$attempt++) {
        if ($pgHandle.Process.HasExited) {Stop-RecoveryCheck 'postgres_start_failed' 1}
        try {Assert-BackupServerVersion $pg $clusterProfile;$ready=$true;break} catch {Start-Sleep -Milliseconds 100}
    }
    if (-not $ready) {Stop-RecoveryCheck 'postgres_start_timeout' 1}
    Assert-InstanceOwnedPostgres $pgHandle (Join-Path $root 'pgdata')
    $arguments=@('-X','-A','-t','-v','ON_ERROR_STOP=1')+(Get-BackupConnectionArguments $clusterProfile 'postgres')
    $null=Invoke-BackupPg (Join-Path $pg 'psql.exe') $arguments $clusterProfile "CREATE ROLE $owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '$ownerPassword'; CREATE ROLE $runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '$runtimePassword';"
    $null=Invoke-BackupPg (Join-Path $pg 'psql.exe') $arguments $clusterProfile "CREATE DATABASE $database OWNER $owner TEMPLATE template0 ENCODING 'UTF8';"
    $null=Invoke-BackupPg (Join-Path $pg 'psql.exe') $arguments $clusterProfile "REVOKE ALL ON DATABASE $database FROM PUBLIC; GRANT CONNECT ON DATABASE $database TO $runtime;"
    $ownerProfile=@{host='127.0.0.1';port=$recoveredInputs.port;database=$database;user=$owner;password=$ownerPassword}
    $ownerArguments=@('-X','-A','-t','-v','ON_ERROR_STOP=1')+(Get-BackupConnectionArguments $ownerProfile $database)
    $identity=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "SELECT count(*) FROM pg_catalog.pg_database d JOIN pg_catalog.pg_roles r ON r.rolname=current_user WHERE d.datname=current_database() AND d.datname='$database' AND current_user='$owner' AND d.datdba=r.oid AND NOT r.rolsuper AND NOT r.rolcreatedb AND NOT r.rolcreaterole AND NOT r.rolreplication AND NOT r.rolbypassrls;"
    if ($identity -cne '1') {Stop-RecoveryCheck 'new_database_owner_invalid' 1}
    $empty=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "SELECT count(*) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p','f','v','m','S');"
    if ($empty -cne '0') {Stop-RecoveryCheck 'new_database_not_empty' 1}
    $backupHash=$recoveredInputs.backupHash.ToLowerInvariant()
    $marker='RackClickRecoveryPending:'+$id+':'+$backupHash
    $null=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "COMMENT ON DATABASE $database IS '$marker';"
    $phase='restore'
    $passfile=Join-Path $logs 'restore-password.pgpass'
    Write-BackupNewText $passfile ("127.0.0.1:"+[string]$recoveredInputs.port+":*:${owner}:$ownerPassword`n");Assert-BackupPrivateAcl $passfile
    $restoreEnvironment=New-InstanceEnvironment @{PGPASSFILE=$passfile;PGCLIENTENCODING='UTF8';PGCONNECT_TIMEOUT='5';PGAPPNAME='RackClick-native-recovery'}
    $restoreArguments=(Get-BackupConnectionArguments $ownerProfile $database)+@('--single-transaction','--exit-on-error','--no-owner','--no-acl','data.dump')
    $null=Invoke-RecoveryOwnedChild (Join-Path $pg 'pg_restore.exe') $restoreArguments $backupRoot $restoreEnvironment $logs 'pg-restore'
    $schema=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile 'SELECT string_agg(version::text,'','' ORDER BY version) FROM public.schema_migration;'
    # Restore 13→14: sólo el esquema inmediatamente anterior y sólo hacia un paquete 14. Se migra en la base nueva,
    # antes de la CLI de recuperación, que exige el esquema 14. Cualquier otro esquema sigue rechazado.
    $migrateFrom13=($stageSchema -eq 14 -and $schema -ceq ((1..13)-join ','))
    if (-not $migrateFrom13 -and $schema -cne ((1..$stageSchema)-join ',')) {Stop-RecoveryCheck ('restored_schema_required_'+[string]$stageSchema) 1}
    if ($migrateFrom13) {
        $phase='migration'
        $migrationEnvironment=New-InstanceEnvironment @{DOTNET_ROOT=[IO.Path]::GetDirectoryName($dotnet);DOTNET_CLI_TELEMETRY_OPTOUT='1';DOTNET_NOLOGO='1';DOTNET_GENERATE_ASPNET_CERTIFICATE='false';ConnectionStrings__RackClick=(Get-InstanceConnection $recoveredInputs.port $database $owner $ownerPassword);ASPNETCORE_ENVIRONMENT='Development'}
        $null=Invoke-RecoveryOwnedChild $dotnet @((Join-Path $stage 'server/RackClick.Server.dll'),'--migrate') $root $migrationEnvironment $logs 'migrate'
        # Permisos como paso separado de la migración: el rol de ejecución es dinámico y el SQL de migración no puede nombrarlo.
        $null=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "GRANT USAGE ON SCHEMA public TO $runtime; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO $runtime;"
        $schema=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile 'SELECT string_agg(version::text,'','' ORDER BY version) FROM public.schema_migration;'
        if ($schema -cne ((1..$stageSchema)-join ',')) {Stop-RecoveryCheck 'restored_migration_schema_invalid' 1}
    }
    $houseBefore=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "SELECT id::text||'|'||encode(convert_to(name,'UTF8'),'hex') FROM public.systemhaus ORDER BY id;"
    $usersBefore=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "SELECT md5(COALESCE(string_agg(row_to_json(u)::text,E'\n' ORDER BY id),'')) FROM public.app_user u;"
    $phase='administrator'
    $ownerConnection=Get-InstanceConnection $recoveredInputs.port $database $owner $ownerPassword
    $runtimeConnection=Get-InstanceConnection $recoveredInputs.port $database $runtime $runtimePassword
    $recoveryEnvironment=New-InstanceEnvironment @{DOTNET_ROOT=[IO.Path]::GetDirectoryName($dotnet);DOTNET_CLI_TELEMETRY_OPTOUT='1';DOTNET_NOLOGO='1';DOTNET_GENERATE_ASPNET_CERTIFICATE='false';ConnectionStrings__RackClick=$ownerConnection;Recovery__User=$user;Recovery__ExpectedDatabase=$database;Recovery__BackupSha256=$backupHash;ASPNETCORE_ENVIRONMENT='Development'}
    $result=Invoke-RecoveryOwnedChild $dotnet @((Join-Path $stage 'server/RackClick.Server.dll'),'--recover-admin') $root $recoveryEnvironment $logs 'recover-admin' -InputText ($appPassword+"`n")
    $commit=Read-RecoveryCommitResult $result $id
    $uid=$commit.createdUserId;$gid=$commit.createdGroupId;$aid=$commit.auditEventId;$rid=$commit.requestId;$house=$commit.systemhausId
    $phase='verify'
    $houseAfter=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "SELECT id::text||'|'||encode(convert_to(name,'UTF8'),'hex') FROM public.systemhaus ORDER BY id;"
    $usersAfter=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "SELECT md5(COALESCE(string_agg(row_to_json(u)::text,E'\n' ORDER BY id),'')) FROM public.app_user u WHERE id<>'$uid'::uuid;"
    if ($houseBefore -cne $houseAfter -or $usersBefore -cne $usersAfter) {Stop-RecoveryCheck 'restored_identity_changed' 1}
    $sessions=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile 'SELECT count(*) FROM public.app_session;'
    # La tabla MFA existe desde 014: conservar Restore histórico 9-13 sin relajar el control del destino 14.
    $openChallenges='0'
    if ($stageSchema -ge 14) {
        $openChallenges=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile 'SELECT count(*) FROM public.app_mfa_challenge WHERE consumed_at IS NULL;'
    }
    $consumed=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "SELECT pg_catalog.shobj_description(oid,'pg_database') IS NULL FROM pg_catalog.pg_database WHERE datname=current_database();"
    if ($sessions -cne '0' -or $openChallenges -cne '0' -or $consumed -cne 't') {Stop-RecoveryCheck 'recovery_not_finalized' 1}
    $auditSql="SELECT count(*) FROM public.audit_event WHERE id='$aid'::uuid AND systemhaus_id='$house'::uuid AND actor_id='$uid'::uuid AND request_id='$rid'::uuid AND action='deployment.recover' AND resource_id='$house'::uuid AND before_json IS NULL AND after_json->>'origin'='localRecovery' AND after_json->>'instanceId'='$id' AND after_json->>'sourceBackupManifestSha256'='$backupHash' AND after_json->>'createdUserId'='$uid' AND after_json->>'createdGroupId'='$gid' AND after_json->>'revokedSessions'='"+[string]$commit.revokedSessions+"';"
    if ((Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile $auditSql) -cne '1') {Stop-RecoveryCheck 'recovery_audit_invalid' 1}
    $grants=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "SELECT string_agg(g.capability,',' ORDER BY g.capability) FROM public.permission_grant g JOIN public.user_group_member m ON m.group_id=g.user_group_id AND m.systemhaus_id=g.systemhaus_id WHERE m.user_id='$uid'::uuid AND m.group_id='$gid'::uuid AND m.systemhaus_id='$house'::uuid AND g.customer_id IS NULL AND g.customer_group_id IS NULL;"
    $expectedGrants='customer.create,customer.manage,inventory.delete,inventory.edit,inventory.read,reports.export,security.manage,systemhaus.manage,systemhaus.read'
    if ($stageSchema -ge 10) {$expectedGrants+=',templates.publish'}
    if ($grants -cne $expectedGrants) {Stop-RecoveryCheck 'recovery_admin_grants_invalid' 1}
    $null=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "REVOKE ALL ON SCHEMA public FROM PUBLIC; GRANT USAGE ON SCHEMA public TO $runtime; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO $runtime;"
    $runtimeRights=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "SELECT count(*) FROM pg_catalog.pg_roles WHERE rolname='$runtime' AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication AND NOT rolbypassrls AND has_database_privilege(oid,'$database','CONNECT') AND NOT has_database_privilege(oid,'$database','CREATE') AND NOT has_database_privilege(oid,'$database','TEMP') AND has_schema_privilege(oid,'public','USAGE') AND NOT has_schema_privilege(oid,'public','CREATE');"
    $missingRights=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "SELECT count(*) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p') AND (pg_catalog.pg_get_userbyid(c.relowner)<>'$owner' OR NOT (has_table_privilege('$runtime',c.oid,'SELECT') AND has_table_privilege('$runtime',c.oid,'INSERT') AND has_table_privilege('$runtime',c.oid,'UPDATE') AND has_table_privilege('$runtime',c.oid,'DELETE')));"
    if ($runtimeRights -cne '1' -or $missingRights -cne '0') {Stop-RecoveryCheck 'runtime_permissions_invalid' 1}
    # .NET is authoritative for normalization; transfer the exact persisted username
    # as ASCII hex rather than reimplementing ToLowerInvariant in Windows PowerShell.
    $userHex=Invoke-BackupPg (Join-Path $pg 'psql.exe') $ownerArguments $ownerProfile "SELECT encode(convert_to(username,'UTF8'),'hex') FROM public.app_user WHERE id='$uid'::uuid AND systemhaus_id='$house'::uuid AND active;"
    if ($userHex -cnotmatch '^(?:[a-f0-9]{2})+$' -or $userHex.Length -gt 800) {Stop-RecoveryCheck 'recovery_identity_invalid' 1}
    $userBytes=New-Object byte[] ($userHex.Length/2)
    for ($i=0;$i -lt $userBytes.Length;$i++) {$userBytes[$i]=[Convert]::ToByte($userHex.Substring($i*2,2),16)}
    $actualUser=(New-Object Text.UTF8Encoding($false,$true)).GetString($userBytes);$null=Assert-InstanceDisplayName $actualUser
    Write-BackupNewText (Join-Path $private 'runtime.json') (@{connectionString=$runtimeConnection}|ConvertTo-Json -Compress)
    Write-BackupNewText (Join-Path $private 'admin-login.json') (@{username=$actualUser;password=$appPassword}|ConvertTo-Json -Compress)
    Write-BackupNewText (Join-Path $private 'backup-profile.json') (@{schemaVersion=1;host='127.0.0.1';port=$recoveredInputs.port;database=$database;user=$owner;passwordFile=(Join-Path $private 'owner-password.txt')}|ConvertTo-Json -Compress)
    $phase='stop'
    Assert-InstanceOwnedPostgres $pgHandle (Join-Path $root 'pgdata')
    $null=Invoke-RecoveryOwnedChild (Join-Path $pg 'pg_ctl.exe') @('stop','-D','pgdata','-m','fast','-w','-t','30') $root $environment $logs 'postgres-stop'
    Stop-RackClickOwnedProcess $pgHandle;$pgHandle.Process.Dispose();$pgHandle=$null
    if ([IO.File]::Exists((Join-Path $root 'pgdata/postmaster.pid'))) {Stop-RecoveryCheck 'postgres_stop_unconfirmed' 1}
    $phase='finalize'
    $secrets=[ordered]@{}
    foreach ($name in @('admin-login.json','backup-profile.json','cluster-password.txt','owner-password.txt','runtime.json')) {Assert-BackupPrivateAcl (Join-Path $private $name);$secrets[$name]=Get-RuntimeConfigDigest (Join-Path $private $name)}
    $manifest=[ordered]@{schemaVersion=1;kind='RackClickLabInstance';id=$id;rootPath=$root;stagePath=$stage;stageManifestSha256=$recoveredInputs.manifest.ToLowerInvariant();stageReceiptSha256=$recoveredInputs.receipt.ToLowerInvariant();dotnetPath=$dotnet;postgresBinPath=$pg;postgresPort=$recoveredInputs.port;httpPort=$origin.port;publicOrigin=$origin.value;database=$database;owner=$owner;runtime=$runtime;clusterAdmin=$cluster;state='initialized';developmentLoopbackHttp=$true;secretFiles=$secrets}
    Write-BackupNewText (Join-Path $root 'instance.json') ($manifest|ConvertTo-Json -Depth 5 -Compress)
    $digest=Get-RuntimeConfigDigest (Join-Path $root 'instance.json')
    $state.status='initialized';$state.code='instance_initialized';Set-StageState $stateStream $state
    $stateStream.Dispose();$stateStream=$null
    $checkedInstance=Read-RackClickInstance $root $digest
    if ($checkedInstance.id -cne $id -or $checkedInstance.database -cne $database) {Stop-RecoveryCheck 'recovered_instance_invalid'}
    Close-RackClickInstance $checkedInstance;$checkedInstance=$null
    $report.valid=$true;$report.exitCode=0;$report.code='instance_initialized';$report.instanceManifestSha256=$digest
    $report.sourceBackupManifestSha256=$backupHash;$report.recoveryAuditEventId=$aid;$report.url=$origin.value;$success=$true
} catch {
    $cause='failed';$exitValue=2
    foreach ($pair in @(@('recoveryCode','recoveryExit'),@('instanceCode','instanceExit'),@('stageCode','stageExit'),@('code','exitCode'))) {
        if ($_.Exception.Data.Contains($pair[0])) {$cause=[string]$_.Exception.Data[$pair[0]];$exitValue=[int]$_.Exception.Data[$pair[1]];break}
    }
    if ($cause -cnotmatch '^[a-z][a-z0-9_]{0,79}$' -or $exitValue -notin @(1,2)) {$cause='failed';$exitValue=2}
    $report.valid=$false;$report.exitCode=$exitValue;$report.code=$phase+'_'+$cause
} finally {
    try {
        $cleanupFailed=$false
        foreach ($cleanup in @({if ($null -ne $pgHandle) {Stop-RecoveryPostgresAfterFailure $pgHandle $pg $root $environment $logs}},{Close-RackClickInstance $checkedInstance},{if ($null -ne $stateStream) {$stateStream.Dispose()}})) {try {& $cleanup} catch {$cleanupFailed=$true}}
        foreach ($stream in $stageLocks) {try {$stream.Dispose()} catch {$cleanupFailed=$true}}
        if ($null -ne $backup) {foreach ($stream in @($backup.dumpHandle,$backup.manifestHandle)) {try {$stream.Dispose()} catch {$cleanupFailed=$true}}}
        if ($cleanupFailed) {$report.valid=$false;$report.exitCode=2;$report.code='finalize_cleanup_failed';$success=$false}
    } finally {
        $restoreFailed=$false
        foreach ($key in $recoveryOriginalEnvironment.Keys) {try {[Environment]::SetEnvironmentVariable([string]$key,[string]$recoveryOriginalEnvironment[$key],[EnvironmentVariableTarget]::Process)} catch {$restoreFailed=$true}}
        if ($restoreFailed) {$report.valid=$false;$report.exitCode=2;$report.code='environment_restore_failed';$success=$false}
        if (-not $report.valid) {
            $report.instanceManifestSha256='';$report.sourceBackupManifestSha256='';$report.recoveryAuditEventId='';$report.url=''
            if ($owned -and $null -ne $state) {
                $failureStream=$null
                try {
                    $failureStream=[IO.File]::Open((Join-Path $root 'instance-state.json'),[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::Read)
                    $state.status='failed';$state.code=$report.code;Set-StageState $failureStream $state
                } catch {$report.code='failure_state_write_failed';$report.exitCode=2}
                finally {if ($null -ne $failureStream) {try {$failureStream.Dispose()} catch {$report.code='failure_state_write_failed';$report.exitCode=2}}}
            }
        }
    }
}
$report|ConvertTo-Json -Compress
exit $report.exitCode
