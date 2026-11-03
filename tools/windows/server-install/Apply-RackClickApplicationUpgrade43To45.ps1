#requires -Version 5.1
[CmdletBinding()]
param([ValidateSet('Prepare','ColdCheck','Migrate','Verify')][string]$Phase,[Parameter(Mandatory=$true)][string]$PlanPath)
$ErrorActionPreference='Stop'
$upgradeChildInputs=@{phase=$Phase;plan=$PlanPath}
. (Join-Path $PSScriptRoot 'RackClick.ApplicationUpgrade.ps1')
$upgradeChildExit=1;$upgradeChildStage='input';$upgradePgProcess=$null;$upgradePgStarted=$false
$upgradeOwnerBytes=$null;$upgradeOwnerPassword=$null;$upgradeReportPath=$null
function Invoke-RcUpgradeNative([string]$File,[string]$Arguments,[hashtable]$Environment=@{},[string]$InputText='',[int]$TimeoutSeconds=120) {
    $start=New-Object Diagnostics.ProcessStartInfo
    $start.FileName=$File;$start.Arguments=$Arguments;$start.WorkingDirectory=[IO.Path]::GetDirectoryName($File)
    $start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.RedirectStandardInput=$true;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
    foreach($key in @($start.EnvironmentVariables.Keys)){
        if([string]$key-match'^(?i:PG|DOTNET|CORECLR|COR_|COMPlus_|ASPNETCORE_|ConnectionStrings__|SqlSecret__|MfaKeyStore__|RackClick__|PublicOrigin|DevelopmentLoopbackHttp|Kestrel__|Bootstrap__)'){$start.EnvironmentVariables.Remove([string]$key)}
    }
    $start.EnvironmentVariables['DOTNET_EnableDiagnostics']='0';$start.EnvironmentVariables['DOTNET_CLI_TELEMETRY_OPTOUT']='1';$start.EnvironmentVariables['DOTNET_NOLOGO']='1'
    foreach($key in $Environment.Keys){$start.EnvironmentVariables[$key]=[string]$Environment[$key]}
    $process=New-Object Diagnostics.Process;$process.StartInfo=$start
    try{
        $null=$process.Start();$stdout=$process.StandardOutput.ReadToEndAsync();$stderr=$process.StandardError.ReadToEndAsync()
        $process.StandardInput.Write($InputText);$process.StandardInput.Close()
        if(-not$process.WaitForExit($TimeoutSeconds*1000)){try{$process.Kill()}catch{};Stop-RcApplicationUpgrade 'upgrade_child_timeout'}
        $output=$stdout.GetAwaiter().GetResult();$errorText=$stderr.GetAwaiter().GetResult()
        if($output.Length-gt2097152-or$errorText.Length-gt65536){Stop-RcApplicationUpgrade 'upgrade_child_output_excessive'}
        return @{exitCode=$process.ExitCode;stdout=$output;stderr=$errorText}
    }finally{$process.Dispose();$start.EnvironmentVariables.Clear()}
}
function Read-RcUpgradeJson([string]$Path){return ([IO.File]::ReadAllText($Path,[Text.Encoding]::UTF8)|ConvertFrom-Json)}
function Get-RcUpgradeProtectedFiles($Plan,$Instance) {
    $rows=[ordered]@{}
    foreach($relative in @('RootCA.cer','server.cer','server.pfx','tls-password.txt')){
        $path=Join-Path (Join-Path $Plan.instancePath 'runtime') $relative;$rows['runtime/'+$relative]=Get-RcApplicationFileHash $path
    }
    foreach($name in @($Instance.secretFiles.PSObject.Properties.Name)){$rows['private/'+$name]=Get-RcApplicationFileHash (Join-Path (Join-Path $Instance.rootPath 'private') $name)}
    $mfa=Join-Path ('C:\ProgramData\RackClick\Instances\'+$Plan.installationId+'\security') ($Plan.installationId+'\mfa-keys')
    foreach($entry in (Get-RcApplicationTreeHashes $mfa).GetEnumerator()){$rows['mfa/'+$entry.Key]=$entry.Value}
    return $rows
}
function Assert-RcUpgradeSavedProtectedFiles($Expected,$Actual) {
    $names=@($Expected.PSObject.Properties.Name|Sort-Object)
    if(($names-join '|')-cne(@($Actual.Keys|Sort-Object)-join '|')){Stop-RcApplicationUpgrade 'upgrade_protected_files_changed'}
    foreach($name in $names){if($Expected.$name-cne$Actual[$name]){Stop-RcApplicationUpgrade 'upgrade_protected_files_changed'}}
}
function Invoke-RcUpgradeSql([string]$Sql) {
    $envPg=@{PGPASSWORD=$script:upgradeOwnerPassword;PGHOSTADDR='127.0.0.1';PGCONNECT_TIMEOUT='5';PGSSLMODE='disable';PGOPTIONS='-c statement_timeout=120000 -c lock_timeout=10000'}
    $args='-X -q -t -A --no-password --set=ON_ERROR_STOP=1 --host=127.0.0.1 --port='+$script:upgradeInstance.postgresPort+' --username='+$script:upgradeInstance.owner+' --dbname='+$script:upgradeInstance.database
    $answer=Invoke-RcUpgradeNative (Join-Path $script:upgradeInstance.postgresBinPath 'psql.exe') $args $envPg $Sql 180
    if($answer.exitCode-ne0-or$answer.stderr.Length-ne0){Stop-RcApplicationUpgrade 'upgrade_sql_failed'}
    return $answer.stdout.Trim()
}
try{
    $plan=Read-RcUpgradeJson $upgradeChildInputs.plan
    $root='C:\ProgramData\RackClick\Instances\'+$plan.installationId+'\instance'
    $currentSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    if($currentSid-cne$plan.serviceSid-or$plan.instancePath-cne$root-or$plan.codeRoot-cne('C:\Program Files\RackClick\'+$plan.installationId)-or
       $plan.workRoot-cnotmatch('^C:\\ProgramData\\RackClick\\Instances\\'+[regex]::Escape($plan.installationId)+'\\update45-[a-f0-9]{32}$')){Stop-RcApplicationUpgrade 'upgrade_child_binding_invalid'}
    $upgradeReportPath=Join-Path $plan.workRoot ($upgradeChildInputs.phase.ToLowerInvariant()+'-result.json')
    if([IO.File]::Exists($upgradeReportPath)){Stop-RcApplicationUpgrade 'upgrade_child_reentry_rejected'}
    $newOperators=Join-Path $plan.candidateCodeRoot 'operators'
    . (Join-Path $newOperators 'server-install\RackClick.ServerRuntime.ps1')
    if($upgradeChildInputs.phase-cne'ColdCheck'){
        $script:upgradeInstance=Read-RcUpgradeJson (Join-Path $root 'deployment\instance\instance.json')
        if($upgradeInstance.schemaVersion-ne1-or$upgradeInstance.rootPath-cne(Join-Path $root 'deployment\instance')-or$upgradeInstance.stagePath-cne(Join-Path $root 'deployment\distribution')-or
           $upgradeInstance.dotnetPath-cne(Join-Path $root 'content\dependencies\dotnet\dotnet.exe')-or$upgradeInstance.postgresBinPath-cne(Join-Path $root 'content\dependencies\postgresql\bin')-or
           $upgradeInstance.database-cnotmatch'^rc_db_[a-f0-9]{32}$'-or$upgradeInstance.owner-cnotmatch'^rc_owner_[a-f0-9]{32}$'){Stop-RcApplicationUpgrade 'upgrade_instance_binding_invalid'}
    }
    $upgradeContent=Join-Path $plan.workRoot 'content45';$upgradeDistribution=Join-Path $plan.workRoot 'distribution45'
    if($upgradeChildInputs.phase-ceq'Prepare'){
        $upgradeChildStage='verify_current_profile';$checked=Read-ServerProfile (Join-Path $root 'runtime\server-profile.json') $plan.expectedCurrentManifestSha256
        try{
            $original=[ordered]@{instance=$upgradeInstance;deployment=(Read-RcUpgradeJson (Join-Path $root 'deployment\deployment.json'));installation=(Read-RcUpgradeJson (Join-Path $root 'installation.json'));profile=$checked.manifest;serviceConfig=(Read-RcUpgradeJson (Join-Path $root 'service-config.json'))}
            $protected=Get-RcUpgradeProtectedFiles $plan $upgradeInstance
            $dirAcls=[ordered]@{}
            foreach($path in @($root,(Join-Path $root 'deployment'),(Join-Path $root 'content'),(Join-Path $root 'deployment\distribution'))){
                $acl=Get-Acl -LiteralPath $path
                $dirAcls[$path]=$acl.GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]::Owner-bor[Security.AccessControl.AccessControlSections]::Group-bor[Security.AccessControl.AccessControlSections]::Access)
            }
        }finally{Close-ServerProfile $checked}
        $upgradeChildStage='extract_bundle';. (Join-Path $newOperators 'RackClick.OfflineBundle.ps1')
        $bundle=Read-RackClickOfflineBundle (Join-Path $plan.candidateCodeRoot 'RackClick.zip') $plan.expectedBundleSha256
        try{
            if($bundle.manifest.versions.schema-ne45-or$bundle.manifest.applicationManifestSha256-cne$plan.expectedApplicationManifestSha256){Stop-RcApplicationUpgrade 'upgrade_bundle_binding_invalid'}
            $oldBundle=Read-RcUpgradeJson (Join-Path $root 'content\bundle.json')
            foreach($entry in $bundle.manifest.files.PSObject.Properties){
                if($entry.Name.StartsWith('dependencies/',[StringComparison]::Ordinal)-or$entry.Name.StartsWith('prerequisites/',[StringComparison]::Ordinal)){
                    $old=$oldBundle.files.PSObject.Properties[$entry.Name]
                    if($null-eq$old-or$old.Value.sha256-cne$entry.Value.sha256-or$old.Value.bytes-ne$entry.Value.bytes){Stop-RcApplicationUpgrade 'upgrade_prerequisite_changed'}
                }
            }
            if(Test-Path -LiteralPath $upgradeContent){Stop-RcApplicationUpgrade 'upgrade_staging_exists'}
            $null=[IO.Directory]::CreateDirectory($upgradeContent)
            Copy-RackClickOfflineBundleContent $bundle $upgradeContent;Assert-RackClickOfflineInstalledContent $bundle $upgradeContent
            $bundleRecord=New-RcApplicationUpgradeBundleRecord $bundle.manifest $plan.expectedBundleSha256 $bundle.manifestSha256
        }finally{Close-RackClickOfflineBundle $bundle}
        $upgradeChildStage='stage_distribution'
        $answer=@(& (Join-Path $newOperators 'Stage-ServerDistribution.ps1') -ManifestPath (Join-Path $upgradeContent 'application\manifest.json') -ExpectedManifestSha256 $plan.expectedApplicationManifestSha256 -ServerPath (Join-Path $upgradeContent 'application\server') -FrontendPath (Join-Path $upgradeContent 'application\frontend') -DotNetPath (Join-Path $upgradeContent 'dependencies\dotnet\dotnet.exe') -PostgresBinPath (Join-Path $upgradeContent 'dependencies\postgresql\bin') -DestinationPath $upgradeDistribution)
        $exit=$LASTEXITCODE;$stageAnswer=($answer-join[Environment]::NewLine)|ConvertFrom-Json
        if($exit-ne0-or-not$stageAnswer.valid-or$stageAnswer.code-cne'artifacts_staged'-or$stageAnswer.verifiedFiles-ne73){Stop-RcApplicationUpgrade 'upgrade_staging_failed'}
        $result=@{valid=$true;exitCode=0;code='upgrade_candidate_prepared';original=$original;protectedFiles=$protected;dirAcls=$dirAcls;bundle=$bundleRecord;stageReceipt=(Read-RcUpgradeJson (Join-Path $upgradeDistribution 'stage-receipt.json'));stageReceiptSha256=(Get-RcApplicationFileHash (Join-Path $upgradeDistribution 'stage-receipt.json'))}
    }elseif($upgradeChildInputs.phase-ceq'ColdCheck'){
        $upgradeChildStage='cold_source_tree_check'
        if((Get-Service -Name 'RackClick').Status-ne'Stopped'){Stop-RcApplicationUpgrade 'upgrade_service_not_stopped'}
        $trees=@{instance=$root;security=('C:\ProgramData\RackClick\Instances\'+$plan.installationId+'\security');code=$plan.codeRoot}
        $counts=[ordered]@{}
        foreach($name in @('instance','security','code')){$counts[$name]=Assert-RcApplicationTreeNoReparse $trees[$name]}
        $result=@{valid=$true;exitCode=0;code='upgrade_cold_sources_verified';sourceTreesNoReparse=$true;entries=$counts;sourceFileContentsRead=$false;keysRead=$false;postgresStarted=$false}
    }elseif($upgradeChildInputs.phase-ceq'Migrate'){
        $upgradeChildStage='migration_preflight';$saved=Read-RcUpgradeJson (Join-Path $plan.workRoot 'prepare-result.json')
        if(-not$saved.valid-or$saved.code-cne'upgrade_candidate_prepared'-or(Get-Service -Name 'RackClick').Status-ne'Stopped'){Stop-RcApplicationUpgrade 'upgrade_service_not_stopped'}
        $data=Join-Path $upgradeInstance.rootPath 'pgdata'
        if([IO.File]::Exists((Join-Path $data 'postmaster.pid'))){Stop-RcApplicationUpgrade 'upgrade_postgres_already_running'}
        foreach($node in @((Get-Item -LiteralPath $data -Force))+@(Get-ChildItem -LiteralPath $data -Recurse -Force)){
            if(($node.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){Stop-RcApplicationUpgrade 'upgrade_pgdata_reparse_rejected'}
        }
        $listeners=@([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()|ForEach-Object Port)
        if($upgradeInstance.postgresPort-in$listeners-or$upgradeInstance.httpPort-in$listeners){Stop-RcApplicationUpgrade 'upgrade_port_in_use'}
        Assert-RcUpgradeSavedProtectedFiles $saved.protectedFiles (Get-RcUpgradeProtectedFiles $plan $upgradeInstance)
        $upgradeOwnerBytes=[IO.File]::ReadAllBytes((Join-Path $upgradeInstance.rootPath 'private\owner-password.txt'))
        if((Get-RcApplicationBytesHash $upgradeOwnerBytes)-cne$upgradeInstance.secretFiles.'owner-password.txt'){Stop-RcApplicationUpgrade 'upgrade_owner_secret_changed'}
        $script:upgradeOwnerPassword=[Text.Encoding]::UTF8.GetString($upgradeOwnerBytes)
        if($upgradeOwnerPassword-cnotmatch'^[a-f0-9]{64}$'){Stop-RcApplicationUpgrade 'upgrade_owner_secret_invalid'}
        $upgradeChildStage='temporary_postgres'
        # Only this short-lived service-account child is changed. Native PostgreSQL
        # must not inherit PGOPTIONS/PGDATA and CLR profilers cannot instrument dotnet.
        foreach($name in @([Environment]::GetEnvironmentVariables('Process').Keys)){
            if([string]$name-match'^(?i:PG|DOTNET|CORECLR|COR_|COMPlus_|ASPNETCORE_|ConnectionStrings__|SqlSecret__|MfaKeyStore__|RackClick__|PublicOrigin|DevelopmentLoopbackHttp|Kestrel__|Bootstrap__)'){
                [Environment]::SetEnvironmentVariable([string]$name,$null,'Process')
            }
        }
        [Environment]::SetEnvironmentVariable('DOTNET_EnableDiagnostics','0','Process')
        $pgOut=Join-Path $plan.workRoot 'postgres-upgrade.stdout.log';$pgErr=Join-Path $plan.workRoot 'postgres-upgrade.stderr.log'
        $upgradePgProcess=Start-Process -FilePath (Join-Path $upgradeInstance.postgresBinPath 'postgres.exe') -ArgumentList @('-D',('"'+$data+'"')) -WorkingDirectory $upgradeInstance.rootPath -RedirectStandardOutput $pgOut -RedirectStandardError $pgErr -PassThru -WindowStyle Hidden
        $upgradePgStarted=$true;$deadline=[DateTime]::UtcNow.AddSeconds(40);$ready=$false
        while([DateTime]::UtcNow-lt$deadline){
            if($upgradePgProcess.HasExited){Stop-RcApplicationUpgrade 'upgrade_temporary_postgres_failed'}
            $probe=Invoke-RcUpgradeNative (Join-Path $upgradeInstance.postgresBinPath 'pg_isready.exe') ('-h 127.0.0.1 -p '+$upgradeInstance.postgresPort) @{} '' 10
            if($probe.exitCode-eq0){$ready=$true;break};Start-Sleep -Milliseconds 200
        }
        if(-not$ready){Stop-RcApplicationUpgrade 'upgrade_temporary_postgres_timeout'}
        $pidLines=[IO.File]::ReadAllLines((Join-Path $data 'postmaster.pid'))
        if([int]$pidLines[0]-ne$upgradePgProcess.Id){Stop-RcApplicationUpgrade 'upgrade_temporary_postgres_unbound'}
        $upgradeChildStage='data_snapshot_before';$before=(Invoke-RcUpgradeSql (Get-RcApplicationSnapshotSql))|ConvertFrom-Json
        if($before.migrationCount-ne43-or$before.catalogueCount-ne868){Stop-RcApplicationUpgrade 'upgrade_database_baseline_invalid'}
        Write-RcApplicationNewJson (Join-Path $plan.workRoot 'database-before.json') $before
        $upgradeChildStage='migrate'
        $ownerConnection='Host=127.0.0.1;Port='+$upgradeInstance.postgresPort+';Database='+$upgradeInstance.database+';Username='+$upgradeInstance.owner+';Password='+$upgradeOwnerPassword+';SSL Mode=Disable;Timeout=5;Command Timeout=120'
        $migrated=Invoke-RcUpgradeNative (Join-Path $upgradeContent 'dependencies\dotnet\dotnet.exe') ('"'+(Join-Path $upgradeDistribution 'server\RackClick.Server.dll')+'" --migrate') @{ConnectionStrings__RackClick=$ownerConnection;DOTNET_ROOT=(Join-Path $upgradeContent 'dependencies\dotnet');SqlSecret__Enabled='false'} '' 180
        $ownerConnection=$null
        if($migrated.exitCode-ne0-or$migrated.stderr.Length-ne0-or$migrated.stdout.Trim()-cne'Schema verified at version 45.'){Stop-RcApplicationUpgrade 'upgrade_migration_failed'}
        $upgradeChildStage='data_snapshot_after';$after=(Invoke-RcUpgradeSql (Get-RcApplicationSnapshotSql))|ConvertFrom-Json
        Write-RcApplicationNewJson (Join-Path $plan.workRoot 'database-after.json') $after
        $comparison=Test-RcApplicationSnapshots $before $after
        Assert-RcUpgradeSavedProtectedFiles $saved.protectedFiles (Get-RcUpgradeProtectedFiles $plan $upgradeInstance)
        $result=@{valid=$true;exitCode=0;code='upgrade_migration_verified';comparison=$comparison;protectedFilesUnchanged=$true;pgDataNoReparse=$true;temporaryPostgresStopped=$false}
    }else{
        $upgradeChildStage='verify_final_profile';$saved=Read-RcUpgradeJson (Join-Path $plan.workRoot 'prepare-result.json')
        if(-not(Test-RcApplicationDigest $plan.expectedNewManifestSha256)){Stop-RcApplicationUpgrade 'upgrade_new_manifest_reference_required'}
        $checked=Read-ServerProfile (Join-Path $root 'runtime\server-profile.json') $plan.expectedNewManifestSha256
        try{if((Get-StageSchema $checked.instance.stageRoot)-ne45){Stop-RcApplicationUpgrade 'upgrade_final_schema_invalid'};Assert-RcUpgradeSavedProtectedFiles $saved.protectedFiles (Get-RcUpgradeProtectedFiles $plan $upgradeInstance)}finally{Close-ServerProfile $checked}
        $result=@{valid=$true;exitCode=0;code='upgrade_final_profile_verified';protectedFilesUnchanged=$true}
    }
    $upgradeChildExit=0
}catch{
    $code='upgrade_child_failed'
    if($_.Exception.Message-cmatch'^upgrade_[a-z0-9_]{1,90}$'){$code=$_.Exception.Message}
    $result=@{valid=$false;exitCode=1;code=$code;stage=$upgradeChildStage;errorType=$_.Exception.GetType().FullName;failureLine=$_.InvocationInfo.ScriptLineNumber}
}finally{
    if($upgradePgStarted){
        try{
            $data=Join-Path $upgradeInstance.rootPath 'pgdata';$pidPath=Join-Path $data 'postmaster.pid'
            if([IO.File]::Exists($pidPath)){
                $lines=[IO.File]::ReadAllLines($pidPath)
                if([int]$lines[0]-ne$upgradePgProcess.Id){Stop-RcApplicationUpgrade 'upgrade_temporary_postgres_unbound'}
                $stopped=Invoke-RcUpgradeNative (Join-Path $upgradeInstance.postgresBinPath 'pg_ctl.exe') ('stop -D "'+$data+'" -m fast -w -t 30') @{} '' 45
                if($stopped.exitCode-ne0){Stop-RcApplicationUpgrade 'upgrade_temporary_postgres_stop_failed'}
            }
            if([IO.File]::Exists($pidPath)-or-not$upgradePgProcess.WaitForExit(10000)){Stop-RcApplicationUpgrade 'upgrade_temporary_postgres_stop_failed'}
            if($result.valid){$result.temporaryPostgresStopped=$true}
        }catch{$upgradeChildExit=1;$result=@{valid=$false;exitCode=1;code='upgrade_temporary_postgres_stop_unconfirmed';stage=$upgradeChildStage}}
        if($null-ne$upgradePgProcess){$upgradePgProcess.Dispose()}
    }
    if($null-ne$upgradeOwnerBytes){[Array]::Clear($upgradeOwnerBytes,0,$upgradeOwnerBytes.Length)};$upgradeOwnerPassword=$null
}
if($null-ne$upgradeReportPath-and-not[IO.File]::Exists($upgradeReportPath)){Write-RcApplicationNewJson $upgradeReportPath $result}
[ordered]@{valid=[bool]$result.valid;exitCode=$upgradeChildExit;code=$result.code;phase=$upgradeChildInputs.phase;stage=$upgradeChildStage}|ConvertTo-Json -Compress
exit $upgradeChildExit
