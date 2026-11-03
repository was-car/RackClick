#requires -Version 5.1
param([string]$InstancePath,[string]$ExpectedInstanceSha256,[ValidateSet('Seed','Resume','Backup','ReadOnly')][string]$Mode='ReadOnly',[string]$BackupDestination='')
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$project=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$root=[IO.Path]::GetFullPath($InstancePath)
if(-not$root.StartsWith((Join-Path $project '.local\sql-minimal-labs')+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'only_owned_minimal_fixture_allowed'}
. (Join-Path $project 'tools/windows/RackClick.Instance.ps1')
$instance=$null;$pgHandle=$null;$phase='inputs';$report=@{valid=$false;code='minimal_probe_failed';postgresStarted=$false}
try {
    $instance=Read-RackClickInstance $root $ExpectedInstanceSha256
    $manifest=[IO.File]::ReadAllText($instance.manifestPath)|ConvertFrom-Json
    if($manifest.schemaVersion-ne3){throw 'minimal_manifest_required'}
    $backup=Read-BackupProfile (Join-Path $instance.privateRoot 'backup-profile.json')
    if($backup.user-cne$manifest.backupRole){throw 'backup_identity_invalid'}
    $bytes=[IO.File]::ReadAllBytes($instance.sqlSecret.file)
    try{$connection=Unprotect-SqlRuntimeConnection $bytes $instance.id ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value) $instance.database $instance.runtime}
    finally{[Array]::Clear($bytes,0,$bytes.Length)}
    $builder=New-Object Data.Common.DbConnectionStringBuilder;$builder.set_ConnectionString($connection)
    $runtime=@{host='127.0.0.1';port=$instance.pgPort;database=$instance.database;user=$instance.runtime;password=[string]$builder['Password']};$builder.Clear();$connection=$null
    $privates=@(Get-ChildItem -LiteralPath $instance.privateRoot -File)
    if($privates.Count-ne4){throw 'minimal_private_count_invalid'}
    foreach($request in @(Get-ChildItem -LiteralPath $instance.logRoot -Recurse -Filter 'request.json' -File)){
        $record=[IO.File]::ReadAllText($request.FullName)|ConvertFrom-Json
        if($record.schemaVersion-eq2){throw 'maintenance_request_retained'}
    }
    foreach($file in @($privates)+@(Get-Item -LiteralPath $instance.sqlSecret.file)+@(Get-ChildItem -LiteralPath $instance.logRoot -File -Recurse)){
        $text=[Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($file.FullName))
        if($text.Contains($backup.password)-or$text.Contains($runtime.password)){throw 'minimal_plaintext_retained'}
    }
    if($Mode-ceq'ReadOnly'){$report=@{valid=$true;code='minimal_inputs_verified';postgresStarted=$false}}
    else{
        $environment=New-InstanceEnvironment @{PGCLIENTENCODING='UTF8';PGCONNECT_TIMEOUT='5'}
        $pgHandle=Start-RackClickOwnedProcess -Executable (Join-Path $instance.pgBin 'postgres.exe') -Arguments @('-D','pgdata') -WorkingDirectory $root -Environment $environment -LogDirectory $instance.logRoot -Label ('minimal-'+[guid]::NewGuid().ToString('N'))
        $report.postgresStarted=$true;$ready=$false
        for($i=0;$i-lt100;$i++){try{Assert-BackupServerVersion $instance.pgBin $backup;$ready=$true;break}catch{Start-Sleep -Milliseconds 100}}
        if(-not$ready){throw 'minimal_pg_not_ready'}
        Assert-InstanceOwnedPostgres $pgHandle $instance.pgData
        $runtimeArgs=@('-X','-A','-t','-v','ON_ERROR_STOP=1')+(Get-BackupConnectionArguments $runtime $runtime.database)
        $backupArgs=@('-X','-A','-t','-v','ON_ERROR_STOP=1')+(Get-BackupConnectionArguments $backup $backup.database)
        if($Mode-ceq'Seed'){
            $phase='seed'
            $null=Invoke-BackupPg (Join-Path $instance.pgBin 'psql.exe') $runtimeArgs $runtime "INSERT INTO customer(id,systemhaus_id,name) SELECT gen_random_uuid(),s.id,'Synthetic SQL '||i::text FROM systemhaus s CROSS JOIN generate_series(1,20) i;"
        }
        $phase='count'
        $rows=Invoke-BackupPg (Join-Path $instance.pgBin 'psql.exe') $backupArgs $backup 'SELECT count(*) FROM customer;'
        if($rows-cne'20'){throw 'minimal_payload_invalid'}
        $phase='privileges'
        $rights=Invoke-BackupPg (Join-Path $instance.pgBin 'psql.exe') $backupArgs $backup "SELECT count(*) FROM pg_roles WHERE rolname=current_user AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication AND NOT rolbypassrls AND NOT has_database_privilege(current_user,current_database(),'CREATE') AND NOT has_database_privilege(current_user,current_database(),'TEMP') AND NOT has_schema_privilege(current_user,'public','CREATE') AND has_table_privilege(current_user,'customer','SELECT') AND NOT has_table_privilege(current_user,'customer','INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER');"
        if($rights-cne'1'){throw 'backup_privileges_invalid'}
        $phase='negatives'
        foreach($case in @(@($backupArgs,$backup,'DELETE FROM customer;'),@($runtimeArgs,$runtime,'CREATE TABLE runtime_must_not_create(id int);'))){
            $denied=$false
            try{$null=Invoke-BackupPg (Join-Path $instance.pgBin 'psql.exe') $case[0] $case[1] $case[2]}
            catch{if($_.Exception.Data['code']-cne'postgres_command_failed'){throw};$denied=$true}
            if(-not$denied){throw 'sql_privilege_was_granted'}
        }
        $report=@{valid=$true;code='minimal_resumed';postgresStarted=$true;rows=20;runtimeDdlDenied=$true;backupWriteDenied=$true;privilegedPasswordsPersisted=$false}
        if($Mode-ceq'Backup'){
            $result=Invoke-StageChild (Join-Path $project 'tools/windows/New-RackClickDatabaseBackup.ps1') @('-PostgresBinPath',$instance.pgBin,'-ProfilePath',(Join-Path $instance.privateRoot 'backup-profile.json'),'-DestinationPath',$BackupDestination)
            if(-not$result.valid){throw 'minimal_backup_failed'}
            $report.backupManifestSha256=$result.manifestSha256;$report.code='minimal_backup_complete'
        }
        $null=Invoke-InstanceChild (Join-Path $instance.pgBin 'pg_ctl.exe') @('stop','-D','pgdata','-m','fast','-w','-t','30') $root $environment $instance.logRoot ('minimal-stop-'+[guid]::NewGuid().ToString('N'))
        Stop-RackClickOwnedProcess $pgHandle;$pgHandle=$null
    }
}catch{
    $code='minimal_probe_failed'
    foreach($key in @('code','instanceCode','stageCode')){if($_.Exception.Data.Contains($key)){$code=[string]$_.Exception.Data[$key];break}}
    $report.valid=$false;$report.code=$code;$report.phase=$phase
}finally{if($null-ne$pgHandle){Stop-RackClickOwnedProcess $pgHandle};Close-RackClickInstance $instance}
$report|ConvertTo-Json -Compress
if(-not$report.valid){exit 1}
