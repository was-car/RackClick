#requires -Version 5.1
param([string]$OutputPath='',[switch]$SkipNativeAcl)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot '..\..\windows\server-install\Repair-RackClickNetworkTransaction.ps1') -FunctionsOnly
. (Join-Path $PSScriptRoot '..\..\windows\server-install\Set-RackClickServerNetwork.ps1') -FunctionsOnly
$checks=New-Object 'Collections.Generic.List[string]'
function Assert-RepairTest([bool]$Condition,[string]$Name){if(-not$Condition){throw ('Test failed: '+$Name)};$checks.Add($Name)}
function Assert-RepairReject([scriptblock]$Action,[string]$Name){$rejected=$false;try{&$Action|Out-Null}catch{$rejected=$true};Assert-RepairTest $rejected $Name}
$original='O:BAG:SYD:AI(A;ID;FA;;;BA)(A;ID;FA;;;SY)';$protected='O:BAG:SYD:PAI(A;;FA;;;BA)(A;;FA;;;SY)'
Assert-RepairTest ((Get-RcRepairAclState 'receipt' $original $original)-ceq'exact') 'Exact inherited ACL needs no repair'
foreach($key in @('receipt','managementCa')){Assert-RepairTest ((Get-RcRepairAclState $key $protected $original)-ceq'known_inheritance_change') ('Only the exact old ACL producer variant is repairable for '+$key)}
foreach($key in @('profile','config','root','public','pfx','tls-password')){Assert-RepairTest ((Get-RcRepairAclState $key $protected $original)-ceq'rejected') ('Unexpected ACL change rejected for '+$key)}
foreach($sddl in @('O:SYG:SYD:PAI(A;ID;FA;;;BA)(A;ID;FA;;;SY)','O:BAG:SYD:PAI(A;ID;FR;;;BA)(A;ID;FA;;;SY)','O:BAG:SYD:PAI(A;ID;FA;;;BA)','invalid_private_marker')){Assert-RepairTest ((Get-RcRepairAclState 'receipt' $sddl $original)-ceq'rejected') 'Owner, rights, ACE count or malformed ACL cannot be repaired blindly'}
Assert-RepairTest ((Get-RcRepairAclState 'receipt' $original $protected)-ceq'rejected') 'Reverse inheritance change is rejected'
Assert-RepairTest ((Get-RcRepairAclState 'receipt' 'O:BAG:SYD:PAI(A;ID;FA;;;BA)(A;ID;FA;;;SY)' $original)-ceq'rejected') 'Unreproduced protection-only variant is rejected'
Assert-RepairTest ((Get-RcRepairAclState 'receipt' $protected 'O:BAG:SYD:(A;ID;FA;;;BA)(A;ID;FA;;;SY)')-ceq'known_inheritance_change') 'Exact old producer also adds AutoInherited to a backup without that flag'
$sid='S-1-5-21-111-222-333-1001'
foreach($account in @($sid,'.\Svc','HOST\svc','Svc')){Assert-RepairTest (Test-RcRepairLocalPrincipal $account $sid 'HOST' 'Svc') 'SID or explicitly bound local SAM name is accepted'}
foreach($account in @('DOMAIN\Svc','Svc@example.invalid','HOST\Other','Other','S-1-5-21-111-222-333-1002')){Assert-RepairTest (-not(Test-RcRepairLocalPrincipal $account $sid 'HOST' 'Svc')) 'Foreign or mismatching principal is rejected without translation'}
Assert-RepairTest (-not(Test-RcRepairLocalPrincipal 'Svc' $sid 'HOST' '')) 'Bare principal requires a verified SAM name'
$xml='<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"><RegistrationInfo><Description>fixture</Description></RegistrationInfo><Triggers><CalendarTrigger><DaysInterval>1</DaysInterval></CalendarTrigger></Triggers><Settings><Enabled>true</Enabled><ExecutionTimeLimit>PT30M</ExecutionTimeLimit></Settings><Actions><Exec><Command>fixture.exe</Command><Arguments>fixture</Arguments></Exec></Actions></Task>'
$disabled=$xml.Replace('<Enabled>true</Enabled>','<Enabled>false</Enabled>');$comparison=Compare-RcRecoveryTaskXml $disabled $xml
Assert-RepairTest ($comparison.matchesExceptEnabled-and-not$comparison.exact-and-not$comparison.currentEnabled-and$comparison.backupEnabled) 'Disabled is the only permitted task XML difference'
$same=Compare-RcRecoveryTaskXml $xml $xml
Assert-RepairTest ($same.exact-and$same.matchesExceptEnabled-and$same.currentEnabled) 'Exact task XML is idempotent'
foreach($modified in @($disabled.Replace('fixture.exe','other.exe'),$disabled.Replace('PT30M','PT31M'),$disabled.Replace('<DaysInterval>1','<DaysInterval>2'),$disabled.Replace('<Description>fixture','<Description>changed'))){Assert-RepairTest (-not(Compare-RcRecoveryTaskXml $modified $xml).matchesExceptEnabled) 'Changes beyond Enabled are rejected before mutations'}
Assert-RepairReject {Compare-RcRecoveryTaskXml '<!DOCTYPE Task [<!ENTITY x SYSTEM "file:///C:/private_marker">]><Task>&x;</Task>' $xml} 'External entities are prohibited'
Assert-RepairReject {Compare-RcRecoveryTaskXml $xml.Replace('<Enabled>true','<Enabled>yes') $xml} 'Malformed Enabled value is rejected'
Assert-RepairReject {Compare-RcRecoveryTaskXml '<Task />' $xml} 'Wrong task namespace is rejected'
$expected=Get-RcRepairExpectedPaths 'C:\fixture';$index=@();$i=0
foreach($key in @('profile','config','root','public','pfx','tls-password','managementCa','receipt')){$index+=@(@{key=$key;path=$expected[$key];backup=('file-'+$i+'.bin');sha256=('a'*64);sddl=$original});$i++}
$parsed=Read-RcRepairIndex (ConvertTo-RcNetworkBytes $index) $expected
Assert-RepairTest ($parsed.Count-eq8-and$parsed[0]-isnot[Array]) 'Actual Network02 serializer produces a flat eight-entry index in WinPS5.1'
$history=@();foreach($stage in @('snapshot_started','infrastructure','rollback_partial')){$history+=@((@{schemaVersion=1;installationId='606b8c29-41de-4dc0-b63d-ade836000d9e';utc='2026-10-20T12:11:19.0000000Z';stage=$stage;committed=$false;rollbackStatus=$(if($stage-ceq'rollback_partial'){'rollback_partial'}else{'not_needed'})}|ConvertTo-Json -Compress))};$historyBytes=[Text.Encoding]::UTF8.GetBytes(($history-join"`n"));$historyState=Read-RcRepairJournalState $historyBytes
Assert-RepairTest (-not$historyState.alreadyClosed-and$historyState.rowCount-eq3) 'Existing failed journal is eligible for restricted recovery'
foreach($modified in @(($history-join"`n").Replace('606b8c29-41de-4dc0-b63d-ade836000d9e','11111111-1111-4111-8111-111111111111'),($history-join"`n").Replace('rollback_partial','committed'),($history-join"`n").Replace('2026-10-20T12:11:19.0000000Z','private_marker'))){Assert-RepairReject {Read-RcRepairJournalState ([Text.Encoding]::UTF8.GetBytes($modified))} 'Foreign, committed or malformed history cannot be closed'}
foreach($mutation in @('duplicate','path','backup','hash','count')){
 $copy=ConvertFrom-Json -InputObject ($index|ConvertTo-Json -Depth 8 -Compress)
 switch($mutation){duplicate{$copy[1].key=$copy[0].key}path{$copy[0].path='C:\outside\private_marker'}backup{$copy[0].backup='..\outside'}hash{$copy[0].sha256='invalid'}count{$copy=$copy[0..6]}}
 Assert-RepairReject {Read-RcRepairIndex (ConvertTo-RcNetworkBytes $copy) $expected} ('Index rejects '+$mutation)
}
function New-RepairStates{$states=@();foreach($key in $expected.Keys){$states+=@(@{key=$key;backupShaValid=$true;currentMatchesBackup=$true;aclState=$(if($key-cin@('managementCa','receipt')){'known_inheritance_change'}else{'exact'})})};return ,$states}
$states=New-RepairStates;$plan=Get-RcRecoveryRepairPlan $states $comparison
Assert-RepairTest ($plan.aclKeys.Count-eq2-and$plan.taskEnableRequired-and-not$plan.alreadyRestored) 'Plan contains exactly two ACL repairs and one Enable operation'
foreach($property in @('backupShaValid','currentMatchesBackup','aclState')){$states=New-RepairStates;$states[0][$property]=$(if($property-ceq'aclState'){'rejected'}else{$false});Assert-RepairReject {Get-RcRecoveryRepairPlan $states $comparison} ('Preflight rejects '+$property+' before mutation')}
$states=New-RepairStates;foreach($state in $states){$state.aclState='exact'};$plan=Get-RcRecoveryRepairPlan $states $same
Assert-RepairTest ($plan.alreadyRestored-and$plan.aclKeys.Count-eq0-and-not$plan.taskEnableRequired) 'Restored byte/ACL/task state yields an idempotent plan'
$badTask=@{exact=$false;matchesExceptEnabled=$false;currentEnabled=$false;backupEnabled=$true};Assert-RepairReject {Get-RcRecoveryRepairPlan (New-RepairStates) $badTask} 'Unexpected task XML aborts before changes'

# Native ACL repair operates only on a fresh user-owned file, with no privilege changes.
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('RackClick-transaction-recovery-'+[guid]::NewGuid().ToString('N'));$null=[IO.Directory]::CreateDirectory($fixture)
if(-not$SkipNativeAcl){. (Join-Path $PSScriptRoot '..\..\windows\server-install\RackClick.Setup.Security.ps1');Initialize-SetupSecurityNative;Initialize-RcNetworkNative;$file=Join-Path $fixture 'inherited.txt';[IO.File]::WriteAllText($file,'fixture unchanged');$before=[RackClickNetworkMaintenanceNative]::Snapshot($file);[RackClickSetupSecurityNative]::SetAcl($file,$before.Sddl);$oldState=[RackClickNetworkMaintenanceNative]::Snapshot($file);Assert-RepairTest ((Get-RcRepairAclState 'receipt' $oldState.Sddl $before.Sddl)-ceq'known_inheritance_change') 'Actual old native producer satisfies only the calculated known defect';Set-RcNetworkExactAcl $file $before.Sddl;$after=[RackClickNetworkMaintenanceNative]::Snapshot($file)
 Assert-RepairTest ($after.Sddl-ceq$before.Sddl-and(Get-RcRepairHash $after.Bytes)-ceq(Get-RcRepairHash $before.Bytes)) 'Actual native repair restores exact inherited ACL and preserves bytes';Set-RcNetworkExactAcl $file $before.Sddl;Assert-RepairTest (([RackClickNetworkMaintenanceNative]::Snapshot($file)).Sddl-ceq$before.Sddl) 'Actual native ACL repair is idempotent'
}
$journalPath=Join-Path $fixture 'journal.jsonl';[IO.File]::WriteAllText($journalPath,'');$journalContext=@{installationId='606b8c29-41de-4dc0-b63d-ade836000d9e';journalPath=$journalPath;stage='preflight'};Write-RcRepairJournal $journalContext 'repair_started';Write-RcRepairJournal $journalContext 'rollback_restored_service_stopped';$journalRows=@([IO.File]::ReadAllLines($journalPath)|ForEach-Object{$_|ConvertFrom-Json})
Assert-RepairTest ($journalRows.Count-eq2-and-not$journalRows[0].committed-and$journalRows[1].rollbackStatus-ceq'rollback_restored_service_stopped') 'Actual append-only journal emits finite terminal status after durable writes'

# Infrastructure callbacks are doubles; no service, task, firewall or credentials are accessed.
$saved=@{};foreach($name in @('Write-RcRepairJournal','Set-RcRepairAcl','Enable-RcRepairTask','Test-RcRepairRestored')){$saved[$name]=(Get-Item ('function:'+$name)).ScriptBlock}
$script:repairCalls=New-Object 'Collections.Generic.List[string]'
function Write-RcRepairJournal($Context,[string]$Stage){$Context.stage=$Stage;$script:repairCalls.Add($Stage);if($Context.failAt-ceq$Stage){throw 'fixture_failure_private_marker'}}
function Set-RcRepairAcl($Context){$script:repairCalls.Add('set_acl');if($Context.failAt-ceq'set_acl'){throw 'fixture_failure_private_marker'}}
function Enable-RcRepairTask($Context){$script:repairCalls.Add('enable_task');if($Context.failAt-ceq'enable_task'){throw 'fixture_failure_private_marker'}}
function Test-RcRepairRestored($Context){$script:repairCalls.Add('verify');return $Context.failAt-cne'verify'}
try{
 foreach($fault in @('','repair_started','repair_acl','set_acl','repair_task','enable_task','repair_verification','verify','rollback_restored_service_stopped')){
  $script:repairCalls.Clear();$context=@{preflightComplete=$true;plan=@{aclKeys=@('managementCa','receipt');taskEnableRequired=$true;alreadyRestored=$false};journalAlreadyClosed=$false;completed=$false;alreadyRestored=$false;mutationsStarted=$false;stage='preflight';rollbackStatus='rollback_partial';failAt=$fault};$failed=$false
  try{$null=Invoke-RcRecoveryRepairTransaction $context}catch{$failed=$true}
  if($fault-ceq''){Assert-RepairTest (-not$failed-and$context.completed-and$context.rollbackStatus-ceq'rollback_restored_service_stopped') 'Successful repair closes the existing rollback only after verification';Assert-RepairTest (($script:repairCalls-join',')-ceq'repair_started,repair_acl,set_acl,repair_task,enable_task,repair_verification,verify,rollback_restored_service_stopped') 'Journal precedes each mutation and final verification precedes closure'}
  else{Assert-RepairTest ($failed-and-not$context.completed-and$context.rollbackStatus-ceq'rollback_partial'-and$script:repairCalls[-1]-ceq'repair_failed') ('Failure at '+$fault+' never claims a completed recovery');if($fault-cin@('repair_started','repair_acl')){Assert-RepairTest (-not$script:repairCalls.Contains('set_acl')-and-not$script:repairCalls.Contains('enable_task')) 'Journal failure before mutation performs no repair'}}
 }
 $script:repairCalls.Clear();$context=@{preflightComplete=$false};Assert-RepairReject {Invoke-RcRecoveryRepairTransaction $context} 'Preflight failure prevents all journal and mutation callbacks';Assert-RepairTest ($script:repairCalls.Count-eq0) 'No callbacks run without completed preflight'
 $context=@{preflightComplete=$true;plan=@{alreadyRestored=$true;aclKeys=@();taskEnableRequired=$false};journalAlreadyClosed=$true;completed=$false;alreadyRestored=$false;rollbackStatus='rollback_partial';failAt=''};$script:repairCalls.Clear();$null=Invoke-RcRecoveryRepairTransaction $context
 Assert-RepairTest ($context.completed-and$context.alreadyRestored-and($script:repairCalls-join',')-ceq'verify') 'Repeated completed repair verifies state without journal or mutation callbacks'
}finally{foreach($name in $saved.Keys){Set-Item ('function:'+$name) $saved[$name]}}
$result=[ordered]@{schemaVersion=1;valid=$true;passed=$checks.Count;checks=@($checks);environment='Windows PowerShell 5.1; pure preflight, user-owned journal fixture and infrastructure doubles';nativeAclExecuted=(-not$SkipNativeAcl);fixture=$fixture;privilegedOperationsExecuted=0;serviceOperationsExecuted=0;taskOperationsExecuted=0;firewallOperationsExecuted=0;credentialsRead=0;authenticationAttempts=0;databaseOperationsExecuted=0}
if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 6 -Compress
