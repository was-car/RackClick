#requires -Version 5.1
param([string]$RepositoryRoot=(Split-Path (Split-Path $PSScriptRoot -Parent) -Parent))
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $RepositoryRoot 'tools\windows\server-install\RackClick.ApplicationUpgrade.ps1')
$script:results=New-Object Collections.Generic.List[object]
function Assert-True([bool]$Value,[string]$Label){if(-not$Value){throw ('assertion_failed_'+$Label)}}
function Fresh {
 $id='11111111-1111-4111-8111-111111111111';$db='22222222-2222-4222-8222-222222222222';$dep='33333333-3333-4333-8333-333333333333';$root='C:\ProgramData\RackClick\Instances\'+$id+'\instance';$code='C:\Program Files\RackClick\'+$id;$sid='S-1-5-21-1-2-3-1000';$old=('1'*64);$next=('2'*64)
 return @{
 InstallationId=$id;TargetManifestSha256=$next;StageReceiptSha256=('3'*64)
 Instance=[pscustomobject]@{schemaVersion=1;rootPath=(Join-Path $root 'deployment\instance');stagePath=(Join-Path $root 'deployment\distribution');id=$db;stageManifestSha256=$old;stageReceiptSha256=('4'*64);secretFiles=[pscustomobject]@{unchanged='opaque-hash'};owner='rc_owner_example';runtime='rc_runtime_example';database='rc_db_example'}
 Deployment=[pscustomobject]@{rootPath=(Join-Path $root 'deployment');instanceId=$db;id=$dep;instanceManifestSha256=('5'*64);stageManifestSha256=$old;stageReceiptSha256=('4'*64);httpsProfileSha256=('6'*64);publicOrigin='https://127.0.0.1:5443'}
 Installation=[pscustomobject]@{rootPath=$root;deploymentId=$dep;id='44444444-4444-4444-8444-444444444444';deploymentSha256=('7'*64);bundleId='old';bundleArchiveSha256=('8'*64);bundleManifestSha256=('9'*64)}
 Profile=[pscustomobject]@{schemaVersion=2;installationPath=$root;runtimeRoot=(Join-Path $root 'runtime');expectedWindowsSid=$sid;installationSha256=('a'*64);deploymentSha256=('7'*64);publicOrigin='https://192.0.2.1:5443';certificate=[pscustomobject]@{immutable='certificate-files'};mfa=[pscustomobject]@{enabled=$true;installationId=$id;instancesRoot=('C:\ProgramData\RackClick\Instances\'+$id+'\security')}}
 ServiceConfig=[pscustomobject]@{serverManifestSha256=$old;runtimeScriptPath=(Join-Path $code 'operators\server-install\Invoke-RackClickServerRuntime.ps1');serverManifestPath=(Join-Path $root 'runtime\server-profile.json');serviceName='RackClick'}
 Management=[pscustomobject]@{installationId=$id;instancePath=$root;codeRoot=$code;applicationSchemaVersion=43;serviceSid=$sid;serviceName='RackClick';publicOrigin='https://192.0.2.1:5443';manifestSha256=$old;scheduledBackupVerified=$true;rebootVerified=$true;backupArguments=('-NoProfile -File "'+$code+'\operators\server-install\Invoke-RackClickScheduledBackup.ps1" -ExpectedManifestSha256 '+$old)}
 StageReceipt=[pscustomobject]@{schemaVersion=1;status='artifacts-verified';serverFiles=55;frontendFiles=18;verifiedFiles=73;manifestSha256=$next}
 Bundle=[pscustomobject]@{versions=[pscustomobject]@{schema=45};applicationManifestSha256=$next;bundleId='55555555-5555-4555-8555-555555555555';bundleArchiveSha256=('b'*64);bundleManifestSha256=('c'*64)}
 }
}
function Case([string]$Name,[scriptblock]$Action){&$Action;$script:results.Add(@{name=$Name;result='PASS'})}
function Reject([string]$Name,[scriptblock]$Mutate,[string]$Code){
 Case $Name { $v=Fresh;&$Mutate $v;$rejected=$false;try{$null=Get-RcApplicationUpgradeChain @v}catch{if($_.Exception.Message-ceq$Code){$rejected=$true}else{throw}};Assert-True $rejected $Name }
}
Case 'bottom_up_hashes_and_preserved_identity' {
 $v=Fresh;$before=$v|ConvertTo-Json -Depth 30 -Compress;$c=Get-RcApplicationUpgradeChain @v
 Assert-True (($v|ConvertTo-Json -Depth 30 -Compress)-ceq$before) 'inputs_not_mutated'
 Assert-True ($c.deployment.instanceManifestSha256-ceq(Get-RcApplicationBytesHash (ConvertTo-RcApplicationBytes $c.instance))) 'instance_link'
 Assert-True ($c.installation.deploymentSha256-ceq(Get-RcApplicationBytesHash (ConvertTo-RcApplicationBytes $c.deployment))) 'deployment_link'
 Assert-True ($c.profile.installationSha256-ceq(Get-RcApplicationBytesHash (ConvertTo-RcApplicationBytes $c.installation))) 'installation_link'
 Assert-True ($c.manifestSha256-ceq(Get-RcApplicationBytesHash (ConvertTo-RcApplicationBytes $c.profile))) 'profile_link'
 Assert-True ($c.serviceConfig.serverManifestSha256-ceq$c.manifestSha256-and$c.management.manifestSha256-ceq$c.manifestSha256) 'scm_and_receipt'
 foreach($name in @('mfa','certificate')){Assert-True (($c.profile.$name|ConvertTo-Json -Depth 10 -Compress)-ceq($v.Profile.$name|ConvertTo-Json -Depth 10 -Compress)) $name}
 foreach($name in @('id','secretFiles','database','owner','runtime')){Assert-True (($c.instance.$name|ConvertTo-Json -Depth 10 -Compress)-ceq($v.Instance.$name|ConvertTo-Json -Depth 10 -Compress)) $name}
 Assert-True ($c.management.applicationSchemaVersion-eq45-and-not$c.management.scheduledBackupVerified-and-not$c.management.rebootVerified) 'schema_backup_and_reboot_recheck'
}
Reject 'wrong_uuid' {$args[0].InstallationId='not-a-uuid'} 'upgrade_installation_id_invalid'
Reject 'noncanonical_uuid' {$args[0].InstallationId='11111111-1111-4111-8111-11111111111A'} 'upgrade_installation_id_invalid'
Reject 'protected_sql_without_owner_unsupported' {$args[0].Instance.schemaVersion=3} 'upgrade_legacy_owner_required'
Reject 'wrong_instance_path' {$args[0].Instance.rootPath='C:\other'} 'upgrade_record_binding_invalid'
Reject 'wrong_source_schema' {$args[0].Management.applicationSchemaVersion=45} 'upgrade_record_binding_invalid'
Reject 'wrong_origin' {$args[0].Profile.publicOrigin='https://192.0.2.2:5443'} 'upgrade_record_binding_invalid'
Reject 'wrong_sid' {$args[0].Profile.expectedWindowsSid='S-1-5-18'} 'upgrade_record_binding_invalid'
Reject 'wrong_database_uuid' {$args[0].Deployment.instanceId='wrong'} 'upgrade_record_binding_invalid'
Reject 'wrong_service_manifest' {$args[0].ServiceConfig.serverManifestSha256=('0'*64)} 'upgrade_record_binding_invalid'
Reject 'mfa_disabled' {$args[0].Profile.mfa.enabled=$false} 'upgrade_mfa_binding_invalid'
Reject 'mfa_other_root' {$args[0].Profile.mfa.instancesRoot='C:\other'} 'upgrade_mfa_binding_invalid'
Reject 'mfa_other_installation' {$args[0].Profile.mfa.installationId='other'} 'upgrade_mfa_binding_invalid'
Reject 'candidate_schema_999' {$args[0].Bundle.versions.schema=999} 'upgrade_candidate_binding_invalid'
Reject 'candidate_wrong_server_count' {$args[0].StageReceipt.serverFiles=54} 'upgrade_candidate_binding_invalid'
Reject 'candidate_wrong_front_count' {$args[0].StageReceipt.frontendFiles=17} 'upgrade_candidate_binding_invalid'
Reject 'candidate_wrong_digest' {$args[0].StageReceipt.manifestSha256=('0'*64)} 'upgrade_candidate_binding_invalid'
Reject 'candidate_bundle_wrong_digest' {$args[0].Bundle.applicationManifestSha256=('0'*64)} 'upgrade_candidate_binding_invalid'
Reject 'candidate_no_bundle_sha' {$args[0].Bundle.bundleArchiveSha256=''} 'upgrade_candidate_binding_invalid'
Reject 'candidate_no_bundle_id' {$args[0].Bundle.bundleId=$null} 'upgrade_candidate_binding_invalid'
Case 'bundle_manifest_id_maps_to_receipt_bundle_id' {
 $m=[pscustomobject]@{id='55555555-5555-4555-8555-555555555555';versions=[pscustomobject]@{schema=45};applicationManifestSha256=('2'*64)}
 $b=New-RcApplicationUpgradeBundleRecord $m ('a'*64) ('b'*64)
 Assert-True ($b.bundleId-ceq$m.id) 'bundle_id_mapping'
}
Reject 'backup_action_duplicate_argument' {$args[0].Management.backupArguments+=' -ExpectedManifestSha256 '+('1'*64)} 'upgrade_backup_action_invalid'
Case 'snapshot_same_data' {
 $b=[pscustomobject]@{migrationCount=43;catalogueCount=868;history43='same';tables=[pscustomobject]@{app_user=[pscustomobject]@{count=2;sha256='same'};app_mfa_user=[pscustomobject]@{count=1;sha256='same'}}}
 $a=Copy-RcApplicationObject $b;$a.migrationCount=45;$a.catalogueCount=884;$answer=Test-RcApplicationSnapshots $b $a
 Assert-True ($answer.dataAndSecurityUnchanged-and$answer.unchangedTables-eq2) 'snapshot_positive'
 $a.tables.app_mfa_user.sha256='changed';$rejected=$false;try{$null=Test-RcApplicationSnapshots $b $a}catch{$rejected=$_.Exception.Message-ceq'upgrade_data_changed'};Assert-True $rejected 'mfa_change_rejected'
}
$temporaryBase=[IO.Path]::GetTempPath()
$temporaryRoot=Join-Path $temporaryBase ('RackClick-Upgrade45-NoReparse-'+[guid]::NewGuid().ToString('N'))
$link=Join-Path $temporaryRoot 'source\link';$held=$null
try{
 $null=[IO.Directory]::CreateDirectory((Join-Path $temporaryRoot 'source\nested'))
 $null=[IO.Directory]::CreateDirectory((Join-Path $temporaryRoot 'target\nested'))
 $marker=Join-Path $temporaryRoot 'source\nested\locked.txt';[IO.File]::WriteAllText($marker,'Synthetic fixture. Content must not be read.')
 $held=[IO.File]::Open($marker,'Open','ReadWrite','None')
 Case 'tree_attributes_only_with_file_locked_exclusively' {
  Assert-True ((Assert-RcApplicationTreeNoReparse (Join-Path $temporaryRoot 'source'))-eq3) 'file_contents_not_opened'
 }
 $null=New-Item -ItemType Junction -Path $link -Target (Join-Path $temporaryRoot 'target') -ErrorAction Stop
 Case 'junction_rejected_before_traversal' {
  $rejected=$false;try{$null=Assert-RcApplicationTreeNoReparse (Join-Path $temporaryRoot 'source')}catch{$rejected=$_.Exception.Message-ceq'upgrade_reparse_rejected'};Assert-True $rejected 'junction_rejected'
 }
 Case 'ancestor_junction_rejected' {
  $rejected=$false;try{$null=Assert-RcApplicationTreeNoReparse (Join-Path $link 'nested')}catch{$rejected=$_.Exception.Message-ceq'upgrade_reparse_rejected'};Assert-True $rejected 'ancestor_junction_rejected'
 }
}finally{
 if($null-ne$held){$held.Dispose()}
 # Delete the junction itself, then only our checked, link-free temporary tree.
 if([IO.Directory]::Exists($link)){[IO.Directory]::Delete($link)}
 $absolute=[IO.Path]::GetFullPath($temporaryRoot)
 if(-not$absolute.StartsWith($temporaryBase,[StringComparison]::OrdinalIgnoreCase)-or[IO.Path]::GetFileName($absolute)-cnotmatch'^RackClick-Upgrade45-NoReparse-[a-f0-9]{32}$'){throw 'fixture_cleanup_path_invalid'}
 if([IO.Directory]::Exists($absolute)){$null=Assert-RcApplicationTreeNoReparse $absolute;[IO.Directory]::Delete($absolute,$true)}
}
@{result='PASS';tests=$script:results.Count;cases=$script:results;vmAccessed=$false;servicesChanged=$false}|ConvertTo-Json -Depth 5 -Compress
