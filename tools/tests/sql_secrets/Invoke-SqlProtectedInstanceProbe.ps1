#requires -Version 5.1
param([string]$InstancePath,[string]$ExpectedInstanceSha256,[ValidateSet('Seed','Backup','Resume','ReadOnly','Metadata')][string]$Mode='ReadOnly',[string]$BackupDestination='')
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$project=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$base=Join-Path $project '.local\sql-recovery-labs'
$root=[IO.Path]::GetFullPath($InstancePath)
if(-not$root.StartsWith($base+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'only_owned_recovery_fixture_allowed'}
. (Join-Path $project 'tools/windows/RackClick.Instance.ps1')
$instance=$null;$pgHandle=$null;$result=@{valid=$false;code='probe_failed';postgresStarted=$false}
try {
    $instance=Read-RackClickInstance $root $ExpectedInstanceSha256
    if($null-eq$instance.sqlSecret-or$null-ne$instance.runtimeConnectionString){throw 'fixture_not_protected'}
    if($Mode-ceq'Metadata'){
        $result=@{valid=$true;code='metadata_verified_without_owner_decryption';postgresStarted=$false}
    }else{
    # Deliberate maintenance probe, distinct from the metadata-only runtime reader.
    $profile=Read-BackupProfile (Join-Path $instance.privateRoot 'backup-profile.json')
    $null=Read-BackupProfile (Join-Path $instance.privateRoot 'cluster-profile.json')
    $bytes=[IO.File]::ReadAllBytes($instance.sqlSecret.file)
    try {
        $connection=Unprotect-SqlRuntimeConnection $bytes $instance.id ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value) $instance.database $instance.runtime
    } finally {[Array]::Clear($bytes,0,$bytes.Length)}
    $builder=New-Object Data.Common.DbConnectionStringBuilder;$builder.set_ConnectionString($connection)
    $runtime=@{host='127.0.0.1';port=$instance.pgPort;database=$instance.database;user=$instance.runtime;password=[string]$builder['Password']}
    $builder.Clear();$connection=$null
    if($Mode-ceq'ReadOnly'){$result=@{valid=$true;code='protected_inputs_verified';postgresStarted=$false}}
    else {
        $environment=New-InstanceEnvironment @{PGCLIENTENCODING='UTF8';PGCONNECT_TIMEOUT='5'}
        $pgHandle=Start-RackClickOwnedProcess -Executable (Join-Path $instance.pgBin 'postgres.exe') -Arguments @('-D','pgdata') -WorkingDirectory $root -Environment $environment -LogDirectory $instance.logRoot -Label ('sql-recovery-'+[guid]::NewGuid().ToString('N'))
        $result.postgresStarted=$true;$ready=$false
        for($i=0;$i-lt100;$i++){try{Assert-BackupServerVersion $instance.pgBin $profile;$ready=$true;break}catch{Start-Sleep -Milliseconds 100}}
        if(-not$ready){Stop-InstanceCheck 'fixture_postgres_not_ready'}
        Assert-InstanceOwnedPostgres $pgHandle $instance.pgData
        $ownerArgs=@('-X','-A','-t','-v','ON_ERROR_STOP=1')+(Get-BackupConnectionArguments $profile $profile.database)
        if($Mode-ceq'Seed'){
            $null=Invoke-BackupPg (Join-Path $instance.pgBin 'psql.exe') $ownerArgs $profile "CREATE TABLE fixture_payload(id integer PRIMARY KEY,value text NOT NULL); INSERT INTO fixture_payload SELECT i,'synthetic' FROM generate_series(1,20) i; GRANT SELECT ON fixture_payload TO $($instance.runtime);"
        }
        $runtimeArgs=@('-X','-A','-t','-v','ON_ERROR_STOP=1')+(Get-BackupConnectionArguments $runtime $runtime.database)
        $rows=Invoke-BackupPg (Join-Path $instance.pgBin 'psql.exe') $runtimeArgs $runtime 'SELECT count(*) FROM fixture_payload;'
        if($rows-cne'20'){throw 'restored_payload_invalid'}
        $rights=Invoke-BackupPg (Join-Path $instance.pgBin 'psql.exe') $ownerArgs $profile (Get-InstanceMissingTableRightsSql $instance.runtime $instance.owner 43)
        # Seed added one SELECT-only fixture table: check product privileges only on Resume.
        if($Mode-ceq'Resume'-and$rights-cne'0'){throw 'restored_grants_invalid'}
        $denied=$false
        try{$null=Invoke-BackupPg (Join-Path $instance.pgBin 'psql.exe') $runtimeArgs $runtime 'CREATE TABLE runtime_must_not_create(id integer);'}catch{if($_.Exception.Data['code']-cne'postgres_command_failed'){throw};$denied=$true}
        if(-not$denied){throw 'runtime_ddl_allowed'}
        $schema=Invoke-BackupPg (Join-Path $instance.pgBin 'psql.exe') $ownerArgs $profile 'SELECT max(version) FROM schema_migration;'
        $sessions=Invoke-BackupPg (Join-Path $instance.pgBin 'psql.exe') $ownerArgs $profile 'SELECT count(*) FROM app_session;'
        if($schema-cne'43'-or$sessions-cne'0'){throw 'product_state_invalid'}
        $result=@{valid=$true;code='resumed';postgresStarted=$true;rows=[int]$rows;schema=[int]$schema;runtimeDdlDenied=$denied;sqlCredentialsWrittenToReport=$false}
        if($Mode-ceq'Backup'){
            $backup=Invoke-StageChild (Join-Path $project 'tools/windows/New-RackClickDatabaseBackup.ps1') @('-PostgresBinPath',$instance.pgBin,'-ProfilePath',(Join-Path $instance.privateRoot 'backup-profile.json'),'-DestinationPath',$BackupDestination)
            if(-not$backup.valid){throw 'backup_failed'}
            $result.backupManifestSha256=$backup.manifestSha256;$result.code='backup_complete'
        }
        $null=Invoke-InstanceChild (Join-Path $instance.pgBin 'pg_ctl.exe') @('stop','-D','pgdata','-m','fast','-w','-t','30') $root $environment $instance.logRoot ('sql-stop-'+[guid]::NewGuid().ToString('N'))
        Stop-RackClickOwnedProcess $pgHandle;$pgHandle=$null
    }
    }
} catch {
    $code='probe_failed'
    foreach($key in @('instanceCode','code','stageCode')){if($_.Exception.Data.Contains($key)){$code=[string]$_.Exception.Data[$key];break}}
    $result.valid=$false;$result.code=$code
} finally {
    if($null-ne$pgHandle){Stop-RackClickOwnedProcess $pgHandle}
    Close-RackClickInstance $instance
}
$result|ConvertTo-Json -Compress
if(-not$result.valid){exit 1}
