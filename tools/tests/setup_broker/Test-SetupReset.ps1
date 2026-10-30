#requires -Version 5.1
[CmdletBinding()]param([string]$OutputPath='')
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\windows\server-install'))
. (Join-Path $root 'RackClick.Setup.ps1')
. (Join-Path $root 'RackClick.Setup.Reset.ps1')
$passed=New-Object Collections.Generic.List[string]
function Check([bool]$Ok,[string]$Label){if(-not$Ok){throw ('FAIL '+$Label)};$passed.Add($Label)}
function Reject([scriptblock]$Action,[string]$Label){$failed=$false;try{&$Action}catch{$failed=$true};Check $failed $Label}
$id='97ff9b99-ad2a-4d7d-ae95-9638772378a0';$sid='S-1-5-21-11-22-33-1001'
$paths=Get-SetupResetPaths $id
Check ($paths.codeRoot-ceq('C:\Program Files\RackClick\'+$id)-and$paths.instance-ceq('C:\ProgramData\RackClick\Instances\'+$id+'\instance')) 'Closed production roots derived only from canonical GUID'
foreach($bad in @('..\Windows','97FF9B99-AD2A-4D7D-AE95-9638772378A0','{97ff9b99-ad2a-4d7d-ae95-9638772378a0}','C:\Windows','')){Reject {Get-SetupResetPaths $bad} ('Reject invalid ID '+$bad)}
$account=[pscustomobject]@{Name='RackClickSvc';Description=('RackClick '+$id);Sid=$sid}
Check (Test-SetupResetAccountSnapshot $account $id 'S-1-5-21-11-22-33-1002') 'Recognize exact installer account description with local SID'
$account.Name='RackClickSvc97ff9b99';Check (Test-SetupResetAccountSnapshot $account $id '') 'Recognize installer collision suffix'
foreach($name in @('Administrator','RackClickOperador','RackClickSvcOther','RC-Old-97ff9b99')){$account.Name=$name;Check (-not(Test-SetupResetAccountSnapshot $account $id '')) ('Preserve non-installer account '+$name)}
$account.Name='RackClickSvc';$account.Description='RackClick';Check (-not(Test-SetupResetAccountSnapshot $account $id '')) 'Name alone does not establish ownership'
$account.Description='RackClick '+$id;Check (-not(Test-SetupResetAccountSnapshot $account $id $sid)) 'Never retire invoking identity'
foreach($badSid in @('S-1-5-21-11-22-33-500','S-1-5-21-11-22-33-501','S-1-5-18','S-1-5-32-544')){$account.Sid=$badSid;Check (-not(Test-SetupResetAccountSnapshot $account $id '')) ('Preserve protected/nonlocal SID '+$badSid)}
$service=[pscustomobject]@{Name='RackClick';DisplayName=('RackClick '+$id);Sid=$sid;PathName=('"'+$paths.instance+'\content\dependencies\dotnet\dotnet.exe" "'+$paths.codeRoot+'\service\RackClick.WindowsService.dll" --config "'+$paths.instance+'\service-config.json"')}
Check (Test-SetupResetServiceSnapshot $service $paths $sid) 'Service requires exact executable DLL config display GUID and SID'
$originalPath=$service.PathName;$service.PathName+=' --extra';Check (-not(Test-SetupResetServiceSnapshot $service $paths $sid)) 'Refuse altered service command line';$service.PathName=$originalPath
$service.Sid='S-1-5-18';Check (-not(Test-SetupResetServiceSnapshot $service $paths $sid)) 'Refuse service running as SYSTEM';$service.Sid=$sid
$service.DisplayName='RackClick';Check (-not(Test-SetupResetServiceSnapshot $service $paths $sid)) 'Refuse display name without installation GUID'
$otherId='bc824ac5-bb03-478f-ae49-830671805bbe';$otherPaths=Get-SetupResetPaths $otherId
$otherService=[pscustomobject]@{Name='RackClick';DisplayName=('RackClick '+$otherId);Sid='S-1-5-21-11-22-33-1002';PathName=('"'+$otherPaths.instance+'\content\dependencies\dotnet\dotnet.exe" "'+$otherPaths.codeRoot+'\service\RackClick.WindowsService.dll" --config "'+$otherPaths.instance+'\service-config.json"')}
Check (Test-SetupResetServiceSnapshot $otherService $otherPaths $otherService.Sid) 'Second attributed stopped installation has exact independent service binding'
Check (-not(Test-SetupResetServiceCandidateReference $otherService $id 'RackClick' $sid $paths @{'RackClick'=$otherId})) 'Verified service from another GUID does not block first historical attempt by shared name'
Check (Test-SetupResetServiceCandidateReference $otherService $id 'RackClick' $sid $paths @{}) 'Same-name service without verified other GUID remains a blocker'
Check (Test-SetupResetServiceCandidateReference $otherService $otherId 'RackClick' $otherService.Sid $otherPaths @{'RackClick'=$otherId}) 'Verified service remains attributable to its own GUID'
$task=[pscustomobject]@{TaskName=('RackClick-Backup-'+$id);TaskPath='\';Execute=($env:SystemRoot+'\System32\WindowsPowerShell\v1.0\powershell.exe');Arguments=('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$paths.codeRoot+'\operators\server-install\Invoke-RackClickScheduledBackup.ps1" -ManifestPath "'+$paths.instance+'\runtime\server-profile.json" -ExpectedManifestSha256 '+('a'*64));ActionCount=1;Sid=$sid}
Check (Test-SetupResetTaskSnapshot $task $paths $sid) 'Daily backup task attributed by exact action and identity'
$task.ActionCount=2;Check (-not(Test-SetupResetTaskSnapshot $task $paths $sid)) 'Additional task action refused';$task.ActionCount=1
$task.Arguments+=' -Extra';Check (-not(Test-SetupResetTaskSnapshot $task $paths $sid)) 'Altered scheduled action refused'
$task.TaskName='RackClick-Verify-'+$id;$task.Arguments='-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$paths.codeRoot+'\operators\server-install\Test-RackClickServerAfterReboot.ps1" -ManagementPath "'+$paths.parent+'\management"';$task.Sid='S-1-5-18'
Check (Test-SetupResetTaskSnapshot $task $paths $sid) 'Postboot task requires exact SYSTEM action and management binding'
$acl=[pscustomobject]@{owner='S-1-5-32-544';rules=@([pscustomobject]@{sid='S-1-5-18';type='Allow';rights=2032127},[pscustomobject]@{sid=$sid;type='Allow';rights=1179785})}
Check (Test-SetupResetCommonAclSnapshot $acl @($sid)) 'Common ACL with known old service SID can be repaired'
Check (-not(Test-SetupResetCommonAclSnapshot $acl @())) 'Unknown service ACL is preserved'
$acl.rules[1].sid='S-1-5-32-545';$acl.rules[1].rights=1179817;Check (Test-SetupResetCommonAclSnapshot $acl @()) 'Common Users read and execute accepted'
$acl.rules[1].rights=2032127;Check (-not(Test-SetupResetCommonAclSnapshot $acl @())) 'Users write permissions block common ACL mutation'
$acl.rules[1].type='Deny';Check (-not(Test-SetupResetCommonAclSnapshot $acl @())) 'Deny entries block common ACL mutation'
$retiredAcl=[pscustomobject]@{owner='S-1-5-32-544';protected=$true;rules=@([pscustomobject]@{sid='S-1-5-18';type='Allow';rights=2032127},[pscustomobject]@{sid='S-1-5-32-544';type='Allow';rights=2032127})}
Check (Test-SetupResetRetiredAclSnapshot $retiredAcl) 'Protected private BA and SYSTEM quarantine is allowed as preserved child'
$retiredAcl.protected=$false;Check (-not(Test-SetupResetRetiredAclSnapshot $retiredAcl)) 'Unprotected quarantine blocks inheritable common ACL repair';$retiredAcl.protected=$true
$retiredChild=[pscustomobject]@{name='Retired';path='C:\ProgramData\RackClick\Retired';isDirectory=$true;reparse=$false;acl=$retiredAcl}
$instancesChild=[pscustomobject]@{name='Instances';path='C:\ProgramData\RackClick\Instances';isDirectory=$true;reparse=$false;acl=$null}
Check (Test-SetupResetCommonChildrenSnapshot 'DataRoot' @($instancesChild,$retiredChild) @()) 'DataRoot allows only checked Instances hub and protected quarantine'
$unknownFile=[pscustomobject]@{name='notes.txt';path='C:\ProgramData\RackClick\notes.txt';isDirectory=$false;reparse=$false;acl=$null}
Check (-not(Test-SetupResetCommonChildrenSnapshot 'DataRoot' @($instancesChild,$unknownFile) @())) 'Extra file in common root blocks ACL repair'
$knownChild=[pscustomobject]@{name=$id;path=$paths.parent;isDirectory=$true;reparse=$false;acl=$null}
Check (Test-SetupResetCommonChildrenSnapshot 'Instances' @($knownChild) @($paths.parent)) 'Attributed instance may leave common root before repair'
Check (-not(Test-SetupResetCommonChildrenSnapshot 'Instances' @($knownChild) @())) 'Unattributed remaining instance blocks ACL repair'
$knownChild.reparse=$true;Check (-not(Test-SetupResetCommonChildrenSnapshot 'Instances' @($knownChild) @($paths.parent))) 'Reparse child blocks common ACL repair even when path is allowlisted'
$fixture=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot ('..\..\..\.local\reset-fixture-'+[guid]::NewGuid().ToString('N'))))
$source=Join-Path $fixture 'instance';$destParent=Join-Path $fixture 'retired';$dest=Join-Path $destParent 'instance'
[IO.Directory]::CreateDirectory($source)|Out-Null;[IO.Directory]::CreateDirectory($destParent)|Out-Null
$data=New-Object byte[] 128;for($i=0;$i-lt$data.Length;$i++){$data[$i]=[byte]$i};[IO.File]::WriteAllBytes((Join-Path $source 'database.fixture'),$data)
$sha=(Get-FileHash -LiteralPath (Join-Path $source 'database.fixture') -Algorithm SHA256).Hash
Reject {Move-SetupResetDirectory $source $dest (Join-Path $fixture 'foreign') $destParent} 'Move refuses unmatched source allowlist'
Reject {Move-SetupResetDirectory $source (Join-Path $fixture 'outside') $source $destParent} 'Move refuses destination outside quarantine parent'
Reject {Move-SetupResetDirectory $source (Join-Path $destParent '..\outside') $source $destParent} 'Move refuses noncanonical traversal'
Move-SetupResetDirectory $source $dest $source $destParent
Check ((-not[IO.Directory]::Exists($source))-and[IO.Directory]::Exists($dest)-and(Get-FileHash -LiteralPath (Join-Path $dest 'database.fixture') -Algorithm SHA256).Hash-ceq$sha) 'Actual Windows directory archival preserves bytes and removes only original name'
[IO.Directory]::CreateDirectory($source)|Out-Null
Reject {Move-SetupResetDirectory $source $dest $source $destParent} 'Existing quarantine destination is never overwritten'
Check ([IO.Directory]::Exists($source)) 'Rejected overwrite leaves source intact'
$junction=Join-Path $fixture 'junction';$junctionTarget=Join-Path $fixture 'junction-target';[IO.Directory]::CreateDirectory($junctionTarget)|Out-Null
New-Item -Path $junction -ItemType Junction -Value $junctionTarget -ErrorAction Stop|Out-Null
Reject {Move-SetupResetDirectory $junction (Join-Path $destParent 'junction') $junction $destParent} 'Actual Windows junction is refused without moving target'
Check ([IO.Directory]::Exists($junctionTarget)-and[IO.Directory]::Exists($junction)) 'Rejected reparse preserves both link and original target'
$unknownDirectory=Join-Path $fixture 'unknown-unprotected';[IO.Directory]::CreateDirectory($unknownDirectory)|Out-Null
$unknownAcl=Get-Acl -LiteralPath $unknownDirectory;$unknownAcl.SetAccessRuleProtection($false,$true);Set-Acl -LiteralPath $unknownDirectory -AclObject $unknownAcl
$unknownBefore=(Get-Acl -LiteralPath $unknownDirectory).Sddl
$unknownChild=[pscustomobject]@{name='unknown-unprotected';path=$unknownDirectory;isDirectory=$true;reparse=$false;acl=$null}
Check (-not(Test-SetupResetCommonChildrenSnapshot 'CodeRoot' @($unknownChild) @())) 'Real unprotected unknown fixture child blocks common ACL repair'
Check ((Get-Acl -LiteralPath $unknownDirectory).Sddl-ceq$unknownBefore) 'Unknown unprotected child retains identical SDDL after refused preflight'
$tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $root 'RackClick.Setup.Reset.ps1'),[ref]$tokens,[ref]$errors)
Check (@($errors).Count-eq0) 'PS5 parser accepts reset module'
$dangerous=@($ast.FindAll({param($n)$n-is[Management.Automation.Language.CommandAst]-and$n.GetCommandName()-in@('Remove-Item','Remove-LocalUser','Stop-Process','Remove-LocalGroupMember')},$true))
Check ($dangerous.Count-eq0) 'No recursive deletion account deletion guessed process kill or group removal commands'
$invoke=@($ast.FindAll({param($n)$n-is[Management.Automation.Language.FunctionDefinitionAst]-and$n.Name-ceq'Invoke-SetupResetPlan'},$true))[0]
Check ($invoke.Extent.Text.Contains('SupportsShouldProcess=$true')) 'Apply supports WhatIf and explicit UI confirmation'
Check ($invoke.Extent.Text.Contains('Get-SetupResetPlan')-and$invoke.Extent.Text.Contains('setup_reset_plan_changed')) 'Apply inventories again and rejects changed plan before mutations'
Check ($invoke.Extent.Text.Contains('setup_reset_journal_already_used')) 'Existing reset journal prevents blind replay'
# Exercise the host inventory through command mocks. Native account/SCM/task APIs
# are replaced only in this test process, never by an apply bypass in product code.
$mockRoot=Join-Path $fixture 'mock-user';$mockReports=Join-Path $mockRoot ('RackClick\Setup\'+$id);[IO.Directory]::CreateDirectory($mockReports)|Out-Null
$mockPlan=[ordered]@{schemaVersion=1;id=$id;bindAddress='192.168.178.140';publicHost='192.168.178.140';httpsPort=5443;postgresPort=55441;allowedSubnet='192.168.178.0/24';systemhaus='Systemhaus';bootstrapUser='Wascar';serviceName='RackClick';accountName='RackClickSvc';mode='New';backupPath='';backupManifestSha256='';trustOnServer=$true}
[IO.File]::WriteAllText((Join-Path $mockReports 'plan.json'),($mockPlan|ConvertTo-Json -Compress))
$script:mockAccount=[pscustomobject]@{Name='RackClickSvc';Description=('RackClick '+$id);SID=(New-Object Security.Principal.SecurityIdentifier($sid))}
$script:mockProcesses=@();$script:mockServices=@();$script:mockTasks=@();$script:mockCommon=@();$script:mockCalls=0;$script:mockCommonBlocked=$false
function Get-LocalUser {param($ErrorAction)return $script:mockAccount}
function Get-LocalGroupMember {param($SID,$ErrorAction)return @()}
function Get-CimInstance {param($ClassName,$Filter,$ErrorAction)if($ClassName-eq'Win32_Service'){return $script:mockServices};if($ClassName-eq'Win32_Process'){return $script:mockProcesses};throw 'Unexpected mock class'}
function Get-ScheduledTask {param($ErrorAction)return $script:mockTasks}
function Get-NetFirewallRule {param($PolicyStore,$ErrorAction)return @()}
function Assert-SetupResetPrivilegedFile {param($Path,$ReadSid)Assert-SetupNoReparse $Path}
function Get-SetupResetCommonPaths {param($KnownServiceSids,$AllowedArchiveTargets)if($script:mockCommonBlocked){throw 'setup_reset_common_children_unattributed_preserved'};return $script:mockCommon}
function Resolve-SetupAccountSid {param($Account)return $Account}
function Invoke-CimMethod {param($InputObject,$MethodName,$ErrorAction)return [pscustomobject]@{ReturnValue=0;Sid=$InputObject.OwnerSid}}
function Assert-SetupAdministrator {}
function Rename-LocalUser {$script:mockCalls++;throw 'Unexpected mutation'}
function Disable-LocalUser {$script:mockCalls++;throw 'Unexpected mutation'}
function Disable-ScheduledTask {$script:mockCalls++;throw 'Unexpected mutation'}
function Unregister-ScheduledTask {$script:mockCalls++;throw 'Unexpected mutation'}
function Stop-Service {$script:mockCalls++;throw 'Unexpected mutation'}
function Remove-NetFirewallRule {$script:mockCalls++;throw 'Unexpected mutation'}
$oldLocal=$env:LOCALAPPDATA;$env:LOCALAPPDATA=$mockRoot
try {
    $inventory=Get-SetupResetPlan
    Check (@($inventory.instances|Where-Object{$_.id-ceq$id}).Count-eq1) 'Inventory finds attributed failed attempt from validated UI plan'
    $repeat=Get-SetupResetPlan;Check ($inventory.fingerprint-ceq$repeat.fingerprint) 'Read-only inventory has stable fingerprint across repeat calls'
    $preview=Invoke-SetupResetPlan -Plan $inventory -JournalDirectory $mockReports -WhatIf
    Check (-not$preview.cleanupComplete-and$script:mockCalls-eq0-and-not[IO.File]::Exists((Join-Path $mockReports 'reset-result.json'))) 'Apply WhatIf performs no host mutation or journal write'
    $script:mockCommonBlocked=$true;$unsafeCommon=Get-SetupResetPlan
    Check ($unsafeCommon.blockers-ccontains'setup_reset_common_children_unattributed_preserved') 'Inventory exposes explicit blocker for unattributed common child'
    Reject {Invoke-SetupResetPlan -Plan $unsafeCommon -JournalDirectory $mockReports -Confirm:$false} 'Unknown common child prevents apply before any OS mutation'
    Check ((Get-Acl -LiteralPath $unknownDirectory).Sddl-ceq$unknownBefore) 'Blocked inventory and apply preserve real unknown child SDDL identically'
    $script:mockCommonBlocked=$false
    foreach($taskState in @('Running','Queued')){
        $script:mockTasks=@([pscustomobject]@{TaskName=('RackClick-Backup-'+$id);TaskPath='\';State=$taskState;Principal=[pscustomobject]@{UserId=$sid};Actions=@([pscustomobject]@{Execute=($env:SystemRoot+'\System32\WindowsPowerShell\v1.0\powershell.exe');Arguments=('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$paths.codeRoot+'\operators\server-install\Invoke-RackClickScheduledBackup.ps1" -ManifestPath "'+$paths.instance+'\runtime\server-profile.json" -ExpectedManifestSha256 '+('a'*64))})})
        $taskBusy=Get-SetupResetPlan
        Check (@($taskBusy.blockers|Where-Object{$_-like'*running_task_preserved'}).Count-eq1) ('Owned '+$taskState+' scheduled task blocks before a process exists')
        Reject {Invoke-SetupResetPlan -Plan $taskBusy -JournalDirectory $mockReports -Confirm:$false} ('Owned '+$taskState+' task prevents apply before any OS mutation')
    }
    $script:mockTasks=@()
    $changed=$inventory|ConvertTo-Json -Depth 16|ConvertFrom-Json;$changed.instances[0].retiredAccountName='Administrator'
    Reject {Invoke-SetupResetPlan -Plan $changed -JournalDirectory $mockReports -Confirm:$false} 'Tampered account retirement target rejected before mutation'
    $script:mockProcesses=@([pscustomobject]@{ExecutablePath=($paths.instance+'\content\dependencies\postgresql\bin\postgres.exe');OwnerSid=$sid})
    $busy=Get-SetupResetPlan;Check (@($busy.blockers|Where-Object{$_-like'*running_process_preserved'}).Count-ge1) 'Active PostgreSQL process blocks archival without process kill'
    Reject {Invoke-SetupResetPlan -Plan $busy -JournalDirectory $mockReports -Confirm:$false} 'Busy instance cannot apply cleanup'
    $script:mockProcesses=@([pscustomobject]@{ExecutablePath=$null;OwnerSid=$sid})
    $hidden=Get-SetupResetPlan;Check (@($hidden.blockers|Where-Object{$_-like'*running_process_preserved'}).Count-ge1) 'Owner SID blocks process with hidden executable path'
    $script:mockProcesses=@();$script:mockServices=@([pscustomobject]@{Name='OtherApp';DisplayName='Other application';StartName=$sid;PathName='C:\Other\App.exe'})
    $foreign=Get-SetupResetPlan;Check (@($foreign.blockers|Where-Object{$_-like'*foreign_service_reference'}).Count-ge1) 'Foreign service using installation SID blocks account retirement'
    $script:mockServices=@();$script:mockAccount.Description='Manual user without installer identity'
    $unknown=Get-SetupResetPlan;Check (@($unknown.preserved|Where-Object{$_.reason-ceq'account_without_valid_installation_marker'}).Count-eq1) 'Unattributed RackClick-named account is reported and preserved'
    Wait-SetupResetServiceAbsent 'RackClick' 0;Check $true 'Service absence is confirmed by exact-name CIM query'
    $script:mockServices=@([pscustomobject]@{Name='RackClick'})
    $pending=$false;try{Wait-SetupResetServiceAbsent 'RackClick' 0}catch{if($_.Exception.Message-ceq'setup_reset_service_removal_pending'){$pending=$true}else{throw}}
    Check $pending 'Marked-for-deletion service still visible in SCM blocks completion'
    Reject {Wait-SetupResetServiceAbsent 'Spooler' 0} 'SCM wait never queries an unrelated service name'
    Check ($script:mockCalls-eq0) 'Mock inventory negative cases invoke no OS mutation command'
}finally{$env:LOCALAPPDATA=$oldLocal}
$result=[ordered]@{valid=$true;passed=$passed.Count;checks=@($passed.ToArray());environment='Windows native; unprivileged, own fixture only';osAccountsChanged=$false;servicesChanged=$false;tasksChanged=$false;fixturePath=$fixture;limitations=@('No elevated account/service/task/firewall retirement executed','No server VM cleanup claimed')}
if($OutputPath){[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath),($result|ConvertTo-Json -Depth 8),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 8
