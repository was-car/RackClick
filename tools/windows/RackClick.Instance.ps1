#requires -Version 5.1
# Shared validation for a NEW private development-loopback instance; no imports start processes.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
# 186 declares parameters in caller scope. Preserve imports' input variables explicitly.
$instanceImportPg=Get-Variable -Name PostgresBinPath -ErrorAction SilentlyContinue
$instanceImportInputs=@{pg=if ($null -ne $instanceImportPg) { $instanceImportPg.Value } else { '' }}
. (Join-Path $PSScriptRoot 'RackClick.Stage.ps1')
$PostgresBinPath=$instanceImportInputs.pg
. (Join-Path $PSScriptRoot 'RackClick.Backup.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Process.ps1')

function Stop-InstanceCheck {
    param([string]$Code,[int]$ExitCode=2)
    $failure=New-Object InvalidOperationException($Code)
    $failure.Data['instanceCode']=$Code; $failure.Data['instanceExit']=$ExitCode
    throw $failure
}

function Get-InstanceCatalogTables {
    # Definition data is global and must never be writable by the runtime role.
    return @('public.hardware_definition','public.hardware_mount_slot','public.hardware_group_template',
             'public.hardware_passthrough','public.hardware_connector_template',
             'public.hardware_profile_extension','public.hardware_group_extension')
}

function Get-InstanceRuntimeGrantsSql {
    param([string]$Runtime,[int]$Schema)
    # Identifiers are generated internally by New/Restore, never operator input.
    if ($Runtime -cnotmatch '^rc_runtime_[a-f0-9]{32}$') {Stop-InstanceCheck 'runtime_role_invalid'}
    $null=Get-StageServerFileCount $Schema
    $sql="REVOKE ALL ON SCHEMA public FROM PUBLIC; GRANT USAGE ON SCHEMA public TO $Runtime; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO $Runtime;"
    if ($Schema -in @(43,45)) {
        $tables=(Get-InstanceCatalogTables)-join ','
        $sql+=" REVOKE ALL PRIVILEGES ON TABLE $tables FROM $Runtime; GRANT SELECT ON TABLE $tables TO $Runtime;"
    }
    return $sql
}

function Get-InstanceMissingTableRightsSql {
    param([string]$Runtime,[string]$Owner,[int]$Schema)
    if ($Runtime -cnotmatch '^rc_runtime_[a-f0-9]{32}$' -or $Owner -cnotmatch '^rc_owner_[a-f0-9]{32}$') {Stop-InstanceCheck 'runtime_role_invalid'}
    $null=Get-StageServerFileCount $Schema
    $requirements="has_table_privilege('$Runtime',c.oid,'SELECT') AND has_table_privilege('$Runtime',c.oid,'INSERT') AND has_table_privilege('$Runtime',c.oid,'UPDATE') AND has_table_privilege('$Runtime',c.oid,'DELETE')"
    if ($Schema -in @(43,45)) {
        $catalogue=((Get-InstanceCatalogTables | ForEach-Object {"'"+$_.Substring(7)+"'"})-join ',')
        $requirements="CASE WHEN c.relname IN ($catalogue) THEN has_table_privilege('$Runtime',c.oid,'SELECT') AND NOT has_table_privilege('$Runtime',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') ELSE $requirements END"
    }
    return "SELECT count(*) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p') AND (pg_catalog.pg_get_userbyid(c.relowner)<>'$Owner' OR NOT ($requirements));"
}

function Assert-InstancePort {
    param([int]$Port)
    if ($Port -lt 1024 -or $Port -gt 65535) { Stop-InstanceCheck 'port_invalid' }
    $listener=$null
    try {
        $listener=New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback,$Port)
        $listener.Start()
    } catch { Stop-InstanceCheck 'port_unavailable' 1 }
    finally { if ($null -ne $listener) { $listener.Stop() } }
}

function Assert-InstanceTechnicalRoot {
    param([string]$Root)
    # PG17.11 initdb re-emits an absolute data path to postgres through an ANSI argv boundary.
    # Fail before creation instead of silently changing the operator's chosen directory.
    if ($Root -match '[^\x00-\x7f]') { Stop-InstanceCheck 'instance_root_ascii_required' }
}

function Get-InstanceOrigin {
    param([string]$Origin)
    $uri=$null
    if (-not [Uri]::TryCreate($Origin,[UriKind]::Absolute,[ref]$uri) -or $uri.Scheme -cne 'http' -or
        $uri.Host -cne '127.0.0.1' -or $uri.Port -lt 1024 -or $uri.Port -gt 65535 -or
        $uri.AbsolutePath -ne '/' -or $uri.Query.Length -ne 0 -or $uri.Fragment.Length -ne 0 -or $uri.UserInfo.Length -ne 0) { Stop-InstanceCheck 'origin_invalid' }
    $canonical=$uri.GetLeftPart([UriPartial]::Authority)
    if ($Origin -cne $canonical -and $Origin -cne ($canonical+'/')) { Stop-InstanceCheck 'origin_invalid' }
    return @{value=$canonical;port=$uri.Port}
}

function Assert-InstanceDisplayName {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { Stop-InstanceCheck 'name_invalid' }
    $valueTrimmed=$Value.Trim(); $runes=0
    for ($i=0;$i -lt $valueTrimmed.Length;$i++) {
        $ch=$valueTrimmed[$i]
        if ([char]::IsControl($ch)) { Stop-InstanceCheck 'name_invalid' }
        if ([char]::IsHighSurrogate($ch)) {
            if ($i+1 -ge $valueTrimmed.Length -or -not [char]::IsLowSurrogate($valueTrimmed[$i+1])) { Stop-InstanceCheck 'name_invalid' }
            $i++
        } elseif ([char]::IsLowSurrogate($ch)) { Stop-InstanceCheck 'name_invalid' }
        $runes++
    }
    if ($runes -gt 100) { Stop-InstanceCheck 'name_invalid' }
    return $valueTrimmed
}

function New-InstancePassword {
    $bytes=New-Object byte[] 32; $generator=[Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes); return [BitConverter]::ToString($bytes).Replace('-','').ToLowerInvariant() }
    finally { $generator.Dispose() }
}

function New-InstanceEnvironment {
    param([hashtable]$Values)
    $environment=@{}
    foreach ($key in [Environment]::GetEnvironmentVariables().Keys) {
        if ((Test-SqlRuntimeVariableName ([string]$key)) -or [string]$key -match '^(PG|Bootstrap__|ASPNETCORE_|DOTNET_)') { $environment[[string]$key]=$null }
    }
    foreach ($key in $Values.Keys) { $environment[$key]=[string]$Values[$key] }
    return $environment
}

function Get-InstanceSecretNames([int]$Version) {
    if ($Version -eq 1) { return @('admin-login.json','backup-profile.json','cluster-password.txt','owner-password.txt','runtime.json') }
    if ($Version -eq 2) { return @('admin-login.json','backup-profile.json','cluster-password.dpapi.json','cluster-profile.json','owner-password.dpapi.json','runtime.json') }
    if ($Version -eq 3) { return @('admin-login.json','backup-password.dpapi.json','backup-profile.json','runtime.json') }
    Stop-InstanceCheck 'instance_manifest_invalid'
}

function Get-InstanceBackupGrantsSql([string]$BackupRole) {
    if($BackupRole-cnotmatch'^rc_backup_[a-f0-9]{32}$'){Stop-InstanceCheck 'backup_role_invalid'}
    return "GRANT USAGE ON SCHEMA public TO $BackupRole; GRANT SELECT ON ALL TABLES IN SCHEMA public TO $BackupRole; GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO $BackupRole;"
}

function Write-InstanceBackupProfile([string]$Private,[string]$Id,[int]$Port,[string]$Database,[string]$Role,[string]$Password) {
    $profile=[ordered]@{schemaVersion=2;installationId=$Id;host='127.0.0.1';port=$Port;database=$Database;user=$Role;passwordFile=(Join-Path $Private 'backup-password.dpapi.json')}
    $record=Protect-SqlBackupPassword $Password $profile
    Write-BackupNewText $profile.passwordFile ($record|ConvertTo-Json -Compress)
    Write-BackupNewText (Join-Path $Private 'backup-profile.json') ($profile|ConvertTo-Json -Compress)
}

function Invoke-InstanceWithTemporarySecret {
    param([string]$Path,[string]$Text,[scriptblock]$Action)
    $stream=$null;$owned=$false;$bytes=$null
    try {
        # Record ownership immediately after exclusive creation, before any write.
        $stream=[IO.File]::Open($Path,'CreateNew','Write','None');$owned=$true
        $bytes=[Text.Encoding]::UTF8.GetBytes($Text)
        $stream.Write($bytes,0,$bytes.Length);$stream.Flush($true);$stream.Dispose()
        & $Action
    } finally {
        # Even a failing Dispose must not skip our cleanup attempt. A preexisting
        # file never becomes owned and is never removed by this helper.
        try {if($null-ne$stream){$stream.Dispose()}}
        finally {
            try {if($null-ne$bytes){[Array]::Clear($bytes,0,$bytes.Length)}}
            finally {if($owned){[IO.File]::Delete($Path)}}
        }
    }
}

function Write-InstanceSqlProfiles {
    param([string]$Private,[string]$Id,[int]$Port,[string]$Database,[string]$Owner,[string]$OwnerPassword,[string]$Cluster,[string]$ClusterPassword)
    # Fresh instance only. CurrentUser material is generated by its intended operator,
    # never imported from the source backup or another Windows account.
    foreach ($item in @(@('backup-profile.json','owner-password.dpapi.json',$Database,$Owner,$OwnerPassword),
                        @('cluster-profile.json','cluster-password.dpapi.json','postgres',$Cluster,$ClusterPassword))) {
        $profile=[ordered]@{schemaVersion=2;installationId=$Id;host='127.0.0.1';port=$Port;database=$item[2];user=$item[3];passwordFile=(Join-Path $Private $item[1])}
        $protected=Protect-SqlBackupPassword $item[4] $profile
        Write-BackupNewText $profile.passwordFile ($protected|ConvertTo-Json -Compress)
        Write-BackupNewText (Join-Path $Private $item[0]) ($profile|ConvertTo-Json -Compress)
    }
}

function Read-InstanceSqlProfile {
    param([string]$Private,[string]$Name,[string]$PasswordName,[string]$Id,[int]$Port,[string]$Database,[string]$User)
    $path=Join-Path $Private $Name
    $value=[IO.File]::ReadAllText($path,[Text.Encoding]::UTF8)|ConvertFrom-Json
    $null=Get-SqlBackupContext $value
    if ($value.installationId-cne$Id -or $value.port-ne$Port -or $value.database-cne$Database -or $value.user-cne$User -or
        $value.passwordFile-cne(Join-Path $Private $PasswordName)) { Stop-InstanceCheck 'instance_backup_profile_invalid' }
    # Runtime validates bindings and pinned encrypted files only. It must NOT
    # decrypt owner/cluster credentials using its own (different) Windows token.
    return $value
}

function Get-InstanceConnection {
    param([int]$Port,[string]$Database,[string]$User,[string]$Password)
    return "Host=127.0.0.1;Port=$Port;Database=$Database;Username=$User;Password=$Password;SSL Mode=Disable;Timeout=5;Command Timeout=15;"
}

function Invoke-InstanceStageCheck {
    param([string]$Stage,[string]$ManifestHash,[string]$ReceiptHash)
    $value=Invoke-StageChild (Join-Path $PSScriptRoot 'Test-StagedDistribution.ps1') @('-DestinationPath',$Stage,'-ExpectedManifestSha256',$ManifestHash,'-ExpectedReceiptSha256',$ReceiptHash)
    if (-not $value.valid -or $value.exitCode -ne 0 -or $value.verifiedFiles -ne (Get-StageVerifiedFileCount (Get-StageSchema $Stage))) { Stop-InstanceCheck ('stage_'+$value.code) 1 }
}

function Open-InstanceStageLocks {
    param([string]$Stage,[string]$ManifestHash,[string]$ReceiptHash)
    $locks=@()
    try {
        foreach ($name in @('manifest.json','stage-state.json','stage-receipt.json')) {
            $path=Join-Path $Stage $name; Assert-BackupNoReparse $path
            $locks += [IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        }
        Invoke-InstanceStageCheck $Stage $ManifestHash $ReceiptHash
        $manifest=[IO.File]::ReadAllText((Join-Path $Stage 'manifest.json'),[Text.Encoding]::UTF8)|ConvertFrom-Json
        foreach ($kind in @('server','frontend')) {
            foreach ($entry in $manifest.distributions.$kind.PSObject.Properties) {
                $path=Join-Path (Join-Path $Stage $kind) $entry.Name.Replace('/',[IO.Path]::DirectorySeparatorChar)
                Assert-BackupNoReparse $path
                $locks += [IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
            }
        }
        # Verify once more after all immutable package handles have been acquired.
        Invoke-InstanceStageCheck $Stage $ManifestHash $ReceiptHash
        return ,$locks
    } catch { foreach ($stream in $locks) { $stream.Dispose() }; throw }
}

function Invoke-InstanceChild {
    param([string]$Executable,[string[]]$Arguments,[string]$Root,[hashtable]$Environment,[string]$LogRoot,[string]$Label,[string]$InputText='', [int]$TimeoutSeconds=60,[switch]$ProtectRequest,[switch]$EphemeralRequest)
    $handle=$null
    try {
        $handle=Start-RackClickOwnedProcess -Executable $Executable -Arguments $Arguments -WorkingDirectory $Root -Environment $Environment -InputText $InputText -LogDirectory $LogRoot -Label $Label -ProtectRequest:$ProtectRequest -EphemeralRequest:$EphemeralRequest
        $result=Wait-RackClickOwnedProcess -Handle $handle -TimeoutSeconds $TimeoutSeconds
        if ($result.exitCode -ne 0) { Stop-InstanceCheck ($Label+'_failed') 1 }
        return $result
    } finally { if ($null -ne $handle) { Stop-RackClickOwnedProcess -Handle $handle } }
}

function Assert-InstanceOwnedPostgres {
    param([hashtable]$Handle,[string]$DataPath)
    $pidPath=Join-Path $DataPath 'postmaster.pid'; Assert-BackupNoReparse $pidPath
    if ((Get-Item -LiteralPath $pidPath).Length -gt 16384) { Stop-InstanceCheck 'postgres_owned_identity_invalid' }
    $lines=[IO.File]::ReadAllLines($pidPath,[Text.Encoding]::UTF8);$pgProcessId=0
    if ($lines.Length -lt 1 -or -not [int]::TryParse($lines[0],[ref]$pgProcessId) -or $pgProcessId -le 0 -or
        -not (Test-RackClickOwnedProcessMembership -Handle $Handle -ProcessId $pgProcessId)) { Stop-InstanceCheck 'postgres_owned_identity_invalid' }
}

function Close-RackClickInstance {
    param([hashtable]$Instance)
    if ($null -ne $Instance -and $Instance.ContainsKey('inputLocks')) { foreach ($stream in $Instance.inputLocks) { $stream.Dispose() } }
}

function Read-RackClickInstance {
    param([string]$InstancePath,[string]$ExpectedInstanceSha256)
    $streams=@()
    try {
        $root=Get-StageLocalPath $InstancePath
        Assert-InstanceTechnicalRoot $root
        Assert-BackupPrivateAcl $root
        if ($ExpectedInstanceSha256 -notmatch '^[a-fA-F0-9]{64}$') { Stop-InstanceCheck 'instance_reference_required' }
        $manifestPath=Join-Path $root 'instance.json'
        Assert-BackupPrivateAcl $manifestPath
        $streams += [IO.File]::Open($manifestPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        if ((Get-Item -LiteralPath $manifestPath).Length -gt 32768 -or (Get-RuntimeConfigDigest $manifestPath) -ne $ExpectedInstanceSha256.ToLowerInvariant()) { Stop-InstanceCheck 'instance_hash_mismatch' }
        $manifest=[IO.File]::ReadAllText($manifestPath,[Text.Encoding]::UTF8) | ConvertFrom-Json
        $keys='clusterAdmin,database,developmentLoopbackHttp,dotnetPath,httpPort,id,kind,owner,postgresBinPath,postgresPort,publicOrigin,rootPath,runtime,schemaVersion,secretFiles,stageManifestSha256,stagePath,stageReceiptSha256,state'
        if($manifest.schemaVersion-eq3){$keys=(($keys.Split(',')+@('backupRole'))|Sort-Object)-join','}
        if ((($manifest.PSObject.Properties.Name | Sort-Object)-join ',') -cne $keys -or $manifest.schemaVersion -isnot [int] -or $manifest.schemaVersion -notin @(1,2,3) -or
            $manifest.kind -cne 'RackClickLabInstance' -or $manifest.state -cne 'initialized' -or $manifest.developmentLoopbackHttp -ne $true -or
            $manifest.id -cnotmatch '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' -or
            $manifest.rootPath -cne $root -or $manifest.postgresPort -isnot [int] -or $manifest.httpPort -isnot [int] -or
            $manifest.postgresPort -lt 1024 -or $manifest.postgresPort -gt 65535 -or $manifest.postgresPort -eq $manifest.httpPort) { Stop-InstanceCheck 'instance_manifest_invalid' }
        $suffix=$manifest.id.Replace('-','')
        foreach ($entry in @(@('database','rc_db_'),@('owner','rc_owner_'),@('runtime','rc_runtime_'),@('clusterAdmin','rc_cluster_'))) {
            if ($manifest.($entry[0]) -cne ($entry[1]+$suffix)) { Stop-InstanceCheck 'instance_identity_invalid' }
        }
        if($manifest.schemaVersion-eq3-and$manifest.backupRole-cne('rc_backup_'+$suffix)){Stop-InstanceCheck 'instance_identity_invalid'}
        $origin=Get-InstanceOrigin $manifest.publicOrigin
        if ($origin.port -ne $manifest.httpPort) { Stop-InstanceCheck 'instance_manifest_invalid' }
        $stage=Get-StageLocalPath $manifest.stagePath; $dotnet=Get-StageLocalPath $manifest.dotnetPath; $pg=Get-StageLocalPath $manifest.postgresBinPath
        foreach ($other in @($stage,$pg,[IO.Path]::GetDirectoryName($dotnet))) { if (Test-StageOverlap $root $other) { Stop-InstanceCheck 'instance_paths_overlap' } }
        foreach ($path in @($stage,$dotnet,$pg)) { Assert-BackupNoReparse $path }
        $streams += Open-InstanceStageLocks $stage $manifest.stageManifestSha256 $manifest.stageReceiptSha256
        $statePath=Join-Path $root 'instance-state.json'; Assert-BackupPrivateAcl $statePath
        $state=[IO.File]::ReadAllText($statePath,[Text.Encoding]::UTF8)|ConvertFrom-Json
        if ($state.schemaVersion -ne 1 -or $state.instanceId -cne $manifest.id -or $state.status -notin @('initialized','running','stopped')) { Stop-InstanceCheck 'instance_not_initialized' }
        $private=Join-Path $root 'private'; $logs=Join-Path $root 'logs'; $data=Join-Path $root 'pgdata'
        foreach ($path in @($private,$logs,$data)) { if (-not [IO.Directory]::Exists($path)) { Stop-InstanceCheck 'instance_layout_invalid' }; Assert-BackupPrivateAcl $path }
        $secretNames=@(Get-InstanceSecretNames $manifest.schemaVersion)
        if ((($manifest.secretFiles.PSObject.Properties.Name | Sort-Object)-join ',') -cne ($secretNames -join ',')) { Stop-InstanceCheck 'instance_secrets_invalid' }
        $actual=@((Get-Item -LiteralPath $private -Force).GetFileSystemInfos())
        if ($actual.Count -ne $secretNames.Count -or @($actual | Where-Object { $_ -isnot [IO.FileInfo] -or $_.Name -cnotin $secretNames }).Count -ne 0) { Stop-InstanceCheck 'instance_secrets_invalid' }
        foreach ($name in $secretNames) {
            $path=Join-Path $private $name; Assert-BackupPrivateAcl $path
            $streams += [IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
            if ((Get-Item -LiteralPath $path).Length -gt 16384 -or $manifest.secretFiles.$name -notmatch '^[a-f0-9]{64}$' -or (Get-RuntimeConfigDigest $path) -cne $manifest.secretFiles.$name) { Stop-InstanceCheck 'instance_secret_hash_mismatch' }
        }
        if ($manifest.schemaVersion-eq1) {
        foreach ($name in @('cluster-password.txt','owner-password.txt')) {
            if ([IO.File]::ReadAllText((Join-Path $private $name),[Text.Encoding]::UTF8) -cnotmatch '^[a-f0-9]{64}$') { Stop-InstanceCheck 'instance_secrets_invalid' }
        }
        $backupProfile=Read-BackupProfile (Join-Path $private 'backup-profile.json')
        $backupValue=[IO.File]::ReadAllText((Join-Path $private 'backup-profile.json'),[Text.Encoding]::UTF8)|ConvertFrom-Json
        if ($backupProfile.port -ne $manifest.postgresPort -or $backupProfile.database -cne $manifest.database -or $backupProfile.user -cne $manifest.owner -or $backupValue.passwordFile -cne (Join-Path $private 'owner-password.txt')) { Stop-InstanceCheck 'instance_backup_profile_invalid' }
        } elseif($manifest.schemaVersion-eq2) {
            $null=Read-InstanceSqlProfile $private 'backup-profile.json' 'owner-password.dpapi.json' $manifest.id $manifest.postgresPort $manifest.database $manifest.owner
            $null=Read-InstanceSqlProfile $private 'cluster-profile.json' 'cluster-password.dpapi.json' $manifest.id $manifest.postgresPort 'postgres' $manifest.clusterAdmin
        } else {
            $null=Read-InstanceSqlProfile $private 'backup-profile.json' 'backup-password.dpapi.json' $manifest.id $manifest.postgresPort $manifest.database $manifest.backupRole
        }
        $runtimeValue=[IO.File]::ReadAllText((Join-Path $private 'runtime.json'),[Text.Encoding]::UTF8) | ConvertFrom-Json
        $sqlSecret=$null;$runtimeConnection=$null
        $runtimeMap=ConvertTo-SqlOperatorMap $runtimeValue
        if($runtimeMap.ContainsKey('schemaVersion')) {
            $sqlSecret=Get-SqlRuntimeDefinition $runtimeValue $root $manifest.id $manifest.database $manifest.runtime
            if(-not[IO.File]::Exists($sqlSecret.file)){Stop-InstanceCheck 'instance_sql_ciphertext_missing'}
            Assert-BackupPrivateAcl $sqlSecret.file
            $streams += [IO.File]::Open($sqlSecret.file,'Open','Read','Read')
            if((Get-Item -LiteralPath $sqlSecret.file).Length-gt65536-or(Get-RuntimeConfigDigest $sqlSecret.file)-cne$sqlSecret.ciphertextSha256){Stop-InstanceCheck 'instance_sql_ciphertext_invalid'}
        } else {
        if($manifest.schemaVersion-in@(2,3)){Stop-InstanceCheck 'instance_connection_invalid'}
        if ((@($runtimeValue.PSObject.Properties.Name)-join ',') -cne 'connectionString') { Stop-InstanceCheck 'instance_secrets_invalid' }
        $builder=New-Object Data.Common.DbConnectionStringBuilder
        # DbConnectionStringBuilder implements IDictionary: PS5 property assignment creates a
        # dictionary entry called ConnectionString instead of invoking the CLR setter.
        $builder.set_ConnectionString($runtimeValue.connectionString)
        $expectedKeys=@('host','port','database','username','password','ssl mode','timeout','command timeout')
        if ((@($builder.Keys | ForEach-Object { $_.ToLowerInvariant() } | Sort-Object)-join ',') -cne (($expectedKeys | Sort-Object)-join ',') -or
            [string]$builder['Host'] -cne '127.0.0.1' -or [string]$builder['Port'] -cne [string]$manifest.postgresPort -or
            [string]$builder['Database'] -cne $manifest.database -or [string]$builder['Username'] -cne $manifest.runtime -or
            [string]$builder['Password'] -cnotmatch '^[0-9a-f]{64}$' -or [string]$builder['SSL Mode'] -cne 'Disable' -or
            [string]$builder['Timeout'] -cne '5' -or [string]$builder['Command Timeout'] -cne '15') { Stop-InstanceCheck 'instance_connection_invalid' }
        $runtimeConnection=$runtimeValue.connectionString
        }
        $admin=[IO.File]::ReadAllText((Join-Path $private 'admin-login.json'),[Text.Encoding]::UTF8) | ConvertFrom-Json
        if ((($admin.PSObject.Properties.Name | Sort-Object)-join ',') -cne 'password,username' -or $admin.password -cnotmatch '^[0-9a-f]{64}$') { Stop-InstanceCheck 'instance_admin_invalid' }
        $null=Assert-InstanceDisplayName $admin.username
        return @{id=$manifest.id;root=$root;stageRoot=$stage;dotnet=$dotnet;pgBin=$pg;pgPort=[int]$manifest.postgresPort;httpPort=[int]$manifest.httpPort;origin=$origin.value;database=$manifest.database;owner=$manifest.owner;runtime=$manifest.runtime;clusterAdmin=$manifest.clusterAdmin;privateRoot=$private;logRoot=$logs;pgData=$data;manifestPath=$manifestPath;statePath=(Join-Path $root 'instance-state.json');lockPath=(Join-Path $root 'instance.lock');runtimeConnectionString=$runtimeConnection;sqlSecret=$sqlSecret;adminUser=$admin.username;inputLocks=$streams}
    } catch { foreach ($stream in $streams) { $stream.Dispose() }; throw }
}
