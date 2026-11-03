#requires -Version 5.1
# Pure helpers for the bounded legacy43 -> 45 application update. No import side effects.
function Stop-RcApplicationUpgrade([string]$Code) { throw (New-Object InvalidOperationException($Code)) }
function Get-RcApplicationBytesHash([byte[]]$Bytes) {
    $algorithm=[Security.Cryptography.SHA256]::Create()
    try {return ([BitConverter]::ToString($algorithm.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant()}finally{$algorithm.Dispose()}
}
function Get-RcApplicationFileHash([string]$Path) {
    $stream=[IO.File]::Open($Path,'Open','Read','Read')
    try{$algorithm=[Security.Cryptography.SHA256]::Create();try{return ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}finally{$algorithm.Dispose()}}finally{$stream.Dispose()}
}
function ConvertTo-RcApplicationBytes($Value) {return ,((New-Object Text.UTF8Encoding($false)).GetBytes(($Value|ConvertTo-Json -Depth 30 -Compress)))}
function Copy-RcApplicationObject($Value) {return ($Value|ConvertTo-Json -Depth 30 -Compress|ConvertFrom-Json)}
function Write-RcApplicationNewJson([string]$Path,$Value) {
    $bytes=ConvertTo-RcApplicationBytes $Value;$stream=[IO.File]::Open($Path,'CreateNew','Write','None')
    try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
}
function Test-RcApplicationDigest($Value) {return ($Value-is[string]-and$Value-cmatch'^[a-f0-9]{64}$')}
function New-RcApplicationUpgradeBundleRecord {
    param($Manifest,[string]$ArchiveSha256,[string]$ManifestSha256)
    $bundleId=[guid]::Empty
    if(-not[guid]::TryParseExact($Manifest.id,'D',[ref]$bundleId)-or$Manifest.id-cne$bundleId.ToString('D')-or$bundleId-eq[guid]::Empty-or
       $Manifest.versions.schema-ne45-or-not(Test-RcApplicationDigest $Manifest.applicationManifestSha256)-or
       -not(Test-RcApplicationDigest $ArchiveSha256)-or-not(Test-RcApplicationDigest $ManifestSha256)){Stop-RcApplicationUpgrade 'upgrade_bundle_binding_invalid'}
    return @{bundleId=$Manifest.id;bundleArchiveSha256=$ArchiveSha256;bundleManifestSha256=$ManifestSha256;applicationManifestSha256=$Manifest.applicationManifestSha256;versions=$Manifest.versions}
}
function Update-RcApplicationBackupArguments([string]$Arguments,[string]$PreviousSha256,[string]$NextSha256) {
    if(-not(Test-RcApplicationDigest $PreviousSha256)-or-not(Test-RcApplicationDigest $NextSha256)){Stop-RcApplicationUpgrade 'upgrade_hash_invalid'}
    $suffix=' -ExpectedManifestSha256 '+$PreviousSha256
    if(-not$Arguments.EndsWith($suffix,[StringComparison]::Ordinal)-or([regex]::Matches($Arguments,'-ExpectedManifestSha256')).Count-ne1){Stop-RcApplicationUpgrade 'upgrade_backup_action_invalid'}
    return $Arguments.Substring(0,$Arguments.Length-$PreviousSha256.Length)+$NextSha256
}
function Get-RcApplicationUpgradeChain {
    param([string]$InstallationId,$Instance,$Deployment,$Installation,$Profile,$ServiceConfig,$Management,
          $StageReceipt,[string]$StageReceiptSha256,[string]$TargetManifestSha256,$Bundle)
    $id=[guid]::Empty
    if(-not[guid]::TryParseExact($InstallationId,'D',[ref]$id)-or$InstallationId-cne$id.ToString('D')-or$id-eq[guid]::Empty){Stop-RcApplicationUpgrade 'upgrade_installation_id_invalid'}
    $root='C:\ProgramData\RackClick\Instances\'+$InstallationId+'\instance'
    $code='C:\Program Files\RackClick\'+$InstallationId
    if($Instance.schemaVersion-ne1){Stop-RcApplicationUpgrade 'upgrade_legacy_owner_required'}
    if($Instance.rootPath-cne(Join-Path $root 'deployment\instance')-or$Instance.stagePath-cne(Join-Path $root 'deployment\distribution')-or
       $Deployment.rootPath-cne(Join-Path $root 'deployment')-or$Installation.rootPath-cne$root-or$Profile.installationPath-cne$root-or
       $Profile.runtimeRoot-cne(Join-Path $root 'runtime')-or$Management.instancePath-cne$root-or$Management.codeRoot-cne$code-or
       $Management.installationId-cne$InstallationId-or$Management.applicationSchemaVersion-ne43-or$Profile.publicOrigin-cne$Management.publicOrigin){Stop-RcApplicationUpgrade 'upgrade_record_binding_invalid'}
    if($Deployment.instanceId-cne$Instance.id-or$Installation.deploymentId-cne$Deployment.id-or$Profile.expectedWindowsSid-cne$Management.serviceSid-or
       $ServiceConfig.serverManifestSha256-cne$Management.manifestSha256-or$ServiceConfig.runtimeScriptPath-cne(Join-Path $code 'operators\server-install\Invoke-RackClickServerRuntime.ps1')-or
       $ServiceConfig.serverManifestPath-cne(Join-Path $root 'runtime\server-profile.json')-or$ServiceConfig.serviceName-cne$Management.serviceName){Stop-RcApplicationUpgrade 'upgrade_record_binding_invalid'}
    if($Profile.schemaVersion-ne2-or$Profile.mfa.enabled-ne$true-or$Profile.mfa.installationId-cne$InstallationId-or
       $Profile.mfa.instancesRoot-cne('C:\ProgramData\RackClick\Instances\'+$InstallationId+'\security')){Stop-RcApplicationUpgrade 'upgrade_mfa_binding_invalid'}
    if($StageReceipt.schemaVersion-ne1-or$StageReceipt.status-cne'artifacts-verified'-or$StageReceipt.serverFiles-ne55-or$StageReceipt.frontendFiles-ne18-or$StageReceipt.verifiedFiles-ne73-or
       $StageReceipt.manifestSha256-cne$TargetManifestSha256-or-not(Test-RcApplicationDigest $StageReceiptSha256)-or-not(Test-RcApplicationDigest $TargetManifestSha256)-or
       $Bundle.versions.schema-ne45-or$Bundle.applicationManifestSha256-cne$TargetManifestSha256){Stop-RcApplicationUpgrade 'upgrade_candidate_binding_invalid'}
    $bundleId=[guid]::Empty
    if(-not[guid]::TryParseExact($Bundle.bundleId,'D',[ref]$bundleId)-or$Bundle.bundleId-cne$bundleId.ToString('D')-or$bundleId-eq[guid]::Empty){Stop-RcApplicationUpgrade 'upgrade_candidate_binding_invalid'}
    foreach($value in @($Bundle.bundleArchiveSha256,$Bundle.bundleManifestSha256)){if(-not(Test-RcApplicationDigest $value)){Stop-RcApplicationUpgrade 'upgrade_candidate_binding_invalid'}}
    $i=Copy-RcApplicationObject $Instance;$d=Copy-RcApplicationObject $Deployment;$n=Copy-RcApplicationObject $Installation
    $p=Copy-RcApplicationObject $Profile;$s=Copy-RcApplicationObject $ServiceConfig;$m=Copy-RcApplicationObject $Management
    $i.stageManifestSha256=$TargetManifestSha256;$i.stageReceiptSha256=$StageReceiptSha256
    $d.instanceManifestSha256=Get-RcApplicationBytesHash (ConvertTo-RcApplicationBytes $i);$d.stageManifestSha256=$TargetManifestSha256;$d.stageReceiptSha256=$StageReceiptSha256
    $n.deploymentSha256=Get-RcApplicationBytesHash (ConvertTo-RcApplicationBytes $d)
    $n.bundleId=$Bundle.bundleId;$n.bundleArchiveSha256=$Bundle.bundleArchiveSha256;$n.bundleManifestSha256=$Bundle.bundleManifestSha256
    $p.installationSha256=Get-RcApplicationBytesHash (ConvertTo-RcApplicationBytes $n);$p.deploymentSha256=$n.deploymentSha256
    $nextHash=Get-RcApplicationBytesHash (ConvertTo-RcApplicationBytes $p);$s.serverManifestSha256=$nextHash
    $m.manifestSha256=$nextHash;$m.applicationSchemaVersion=45;$m.scheduledBackupVerified=$false;$m.rebootVerified=$false
    $m.backupArguments=Update-RcApplicationBackupArguments $Management.backupArguments $Management.manifestSha256 $nextHash
    return @{instance=$i;deployment=$d;installation=$n;profile=$p;serviceConfig=$s;management=$m;manifestSha256=$nextHash}
}
function Get-RcApplicationSnapshotSql {
    # Table names are obtained from the server-owned catalogue and quoted with %I;
    # values never become identifiers. No rows or authentication material leave SQL.
    return @'
CREATE OR REPLACE FUNCTION pg_temp.rc_upgrade_snapshot() RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE n text; c bigint; h text; result jsonb := '{}'::jsonb;
BEGIN
 FOR n IN SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public'
   AND tablename NOT IN ('schema_migration','hardware_definition','hardware_mount_slot','hardware_group_template',
     'hardware_passthrough','hardware_connector_template','hardware_profile_extension','hardware_group_extension') ORDER BY tablename
 LOOP
  EXECUTE format('SELECT count(*), encode(sha256(convert_to(coalesce(string_agg(to_jsonb(t)::text, E''\n'' ORDER BY to_jsonb(t)::text),''''),''UTF8'')),''hex'') FROM public.%I t',n) INTO c,h;
  result := result || jsonb_build_object(n,jsonb_build_object('count',c,'sha256',h));
 END LOOP;
 RETURN jsonb_build_object('tables',result,'migrationCount',(SELECT count(*) FROM schema_migration),
  'history43',(SELECT encode(sha256(convert_to(string_agg(version::text||':'||digest,E'\n' ORDER BY version),'UTF8')),'hex') FROM schema_migration WHERE version<=43),
  'catalogueCount',(SELECT count(*) FROM hardware_definition));
END $$;
SELECT pg_temp.rc_upgrade_snapshot()::text;
'@
}
function Test-RcApplicationSnapshots($Before,$After) {
    if($Before.migrationCount-ne43-or$After.migrationCount-ne45-or$Before.catalogueCount-ne868-or$After.catalogueCount-ne884-or$Before.history43-cne$After.history43){Stop-RcApplicationUpgrade 'upgrade_schema_or_catalogue_unexpected'}
    $beforeNames=@($Before.tables.PSObject.Properties.Name|Sort-Object);$afterNames=@($After.tables.PSObject.Properties.Name|Sort-Object)
    if(($beforeNames-join ',')-cne($afterNames-join ',')){Stop-RcApplicationUpgrade 'upgrade_data_changed'}
    foreach($name in $beforeNames){if($Before.tables.$name.count-ne$After.tables.$name.count-or$Before.tables.$name.sha256-cne$After.tables.$name.sha256){Stop-RcApplicationUpgrade 'upgrade_data_changed'}}
    return @{unchangedTables=$beforeNames.Count;schemaBefore=43;schemaAfter=45;catalogueBefore=868;catalogueAfter=884;dataAndSecurityUnchanged=$true}
}
function Assert-RcApplicationTreeNoReparse([string]$Root) {
    # A pre-copy observation, not an atomic filesystem snapshot. Never use
    # Get-ChildItem -Recurse: reject a junction BEFORE putting it on the stack.
    if($Root-cnotmatch'^[A-Za-z]:\\'-or$Root.StartsWith('\\')){Stop-RcApplicationUpgrade 'upgrade_tree_path_invalid'}
    $full=[IO.Path]::GetFullPath($Root);$cursor=$full
    while($cursor){
        $attributes=[IO.File]::GetAttributes($cursor)
        if(($attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){Stop-RcApplicationUpgrade 'upgrade_reparse_rejected'}
        $cursor=[IO.Path]::GetDirectoryName($cursor)
    }
    if(-not[IO.Directory]::Exists($full)){Stop-RcApplicationUpgrade 'upgrade_tree_root_invalid'}
    $stack=New-Object 'Collections.Generic.Stack[IO.DirectoryInfo]'
    $stack.Push((New-Object IO.DirectoryInfo($full)));$visited=1
    while($stack.Count-gt0){
        $directory=$stack.Pop()
        # Recheck the directory immediately before enumerating it.
        $directory.Refresh()
        if(($directory.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){Stop-RcApplicationUpgrade 'upgrade_reparse_rejected'}
        foreach($entry in $directory.GetFileSystemInfos()){
            $visited++
            if($visited-gt100000){Stop-RcApplicationUpgrade 'upgrade_tree_too_large'}
            if(($entry.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){Stop-RcApplicationUpgrade 'upgrade_reparse_rejected'}
            if(($entry.Attributes-band[IO.FileAttributes]::Directory)-ne0){$stack.Push([IO.DirectoryInfo]$entry)}
        }
    }
    return $visited
}
function Get-RcApplicationTreeHashes([string]$Root) {
    $result=[ordered]@{}
    foreach($file in @(Get-ChildItem -LiteralPath $Root -Recurse -Force -File|Sort-Object FullName)){
        if(($file.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){Stop-RcApplicationUpgrade 'upgrade_reparse_rejected'}
        $result[$file.FullName.Substring($Root.Length+1)]=Get-RcApplicationFileHash $file.FullName
    }
    foreach($item in @(Get-ChildItem -LiteralPath $Root -Recurse -Force -Directory)){if(($item.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){Stop-RcApplicationUpgrade 'upgrade_reparse_rejected'}}
    return $result
}
function Test-RcApplicationTreeHashes($Before,$After) {
    if((@($Before.Keys|Sort-Object)-join '|')-cne(@($After.Keys|Sort-Object)-join '|')){Stop-RcApplicationUpgrade 'upgrade_protected_files_changed'}
    foreach($name in $Before.Keys){if($Before[$name]-cne$After[$name]){Stop-RcApplicationUpgrade 'upgrade_protected_files_changed'}}
}
