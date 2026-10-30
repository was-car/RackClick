#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
$ops=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\windows\server-install'))
. (Join-Path $ops 'RackClick.Setup.ps1');. (Join-Path $ops 'RackClick.Setup.Security.ps1');. (Join-Path $ops 'RackClick.Setup.Reset.ps1');. (Join-Path $ops 'RackClick.Setup.Namespace.ps1')
$checks=New-Object Collections.Generic.List[string]
function Check($Value,[string]$Name){if(-not$Value){throw $Name};$checks.Add($Name)}
function Reject([scriptblock]$Action,[string]$Name){$hit=$false;try{&$Action|Out-Null}catch{$hit=$true};Check $hit $Name}
$fixture=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot ('..\..\..\.local\namespace04-fixtures\'+[guid]::NewGuid().ToString('N'))));$null=[IO.Directory]::CreateDirectory($fixture)
$id=[guid]::NewGuid().ToString('D')
Check (Test-SetupNamespaceReference '"C:\ProgramData\RackClick\Instances\x\pgdata"' 'C:\ProgramData\RackClick') 'Quoted old data reference detected'
Check (Test-SetupNamespaceReference 'c:/program files/rackclick/old/service.dll' 'C:\Program Files\RackClick') 'Case and slash variants detected'
Check (-not(Test-SetupNamespaceReference 'C:\ProgramData\RackClick-Previous-x' 'C:\ProgramData\RackClick')) 'Archived sibling is not confused with active namespace'
Check (-not(Test-SetupNamespaceReference 'C:\ProgramData\RackClickOther' 'C:\ProgramData\RackClick')) 'Similar foreign namespace not matched'
Check (Test-SetupNamespaceReference 'C:\Program Files\Tools\..\RackClick\run.exe' 'C:\Program Files\RackClick') 'Dot segment reference normalizes to old hub'
Check (Test-SetupNamespaceReference 'C:\PROGRA~1\RackClick\missing\run.exe' 'C:\Program Files\RackClick') 'Real Windows short Program Files ancestor resolves with missing descendant'
$source=Join-Path $fixture 'native-data';$target=$source+'-Previous-'+$id
$child=Join-Path $source 'Instances\be79ed26-c5c7-432f-b187-540c755581ba\pgdata';$null=[IO.Directory]::CreateDirectory($child)
$payload=Join-Path $child 'PG_VERSION';[IO.File]::WriteAllText($payload,'17')
$sddlBefore=(Get-Acl -LiteralPath $child).Sddl;$rootBefore=(Get-Acl -LiteralPath $source).Sddl;$hashBefore=(Get-FileHash -LiteralPath $payload -Algorithm SHA256).Hash
Move-SetupNamespaceDirectory $source $target $source $id
Check (-not[IO.Directory]::Exists($source)-and[IO.Directory]::Exists($target)) 'Actual single native directory move archives entire markerless hub'
Check ((Get-Acl -LiteralPath $target).Sddl-ceq$rootBefore) 'Native move preserves root SDDL exactly'
Check ((Get-Acl -LiteralPath (Join-Path $target 'Instances\be79ed26-c5c7-432f-b187-540c755581ba\pgdata')).Sddl-ceq$sddlBefore) 'Native move preserves orphan PostgreSQL child SDDL exactly'
Check ((Get-FileHash -LiteralPath (Join-Path $target 'Instances\be79ed26-c5c7-432f-b187-540c755581ba\pgdata\PG_VERSION') -Algorithm SHA256).Hash-ceq$hashBefore) 'Native move preserves PostgreSQL fixture bytes'
Reject {Move-SetupNamespaceDirectory $target ($target+'-Previous-'+$id) $source $id} 'Different approved source rejected'
Reject {Move-SetupNamespaceHub $fixture ($fixture+'-Previous-'+$id) $id} 'Production wrapper rejects any root outside two declared hubs'
$occupied=Join-Path $fixture 'occupied';$null=[IO.Directory]::CreateDirectory($occupied);$occupiedTarget=$occupied+'-Previous-'+$id;$null=[IO.Directory]::CreateDirectory($occupiedTarget)
Reject {Move-SetupNamespaceDirectory $occupied $occupiedTarget $occupied $id} 'Existing sibling never overwritten'
Reject {Move-SetupNamespaceDirectory $occupied (Join-Path $fixture 'elsewhere') $occupied $id} 'Wrong sibling name rejected'
Reject {Move-SetupNamespaceDirectory ($fixture+'\..\outside') ($fixture+'\..\outside-Previous-'+$id) ($fixture+'\..\outside') $id} 'Noncanonical traversal rejected'
# OS inventory is substituted. Production hub strings map only to this fixture.
$script:maps=@{'C:\ProgramData\RackClick'=(Join-Path $fixture 'data');'C:\Program Files\RackClick'=(Join-Path $fixture 'code')}
foreach($path in $script:maps.Values){$null=[IO.Directory]::CreateDirectory($path)}
$script:services=@();$script:tasks=@();$script:processes=@();$script:listeners=@();$script:deny=$false;$script:failSecond=$false;$script:moves=0
$svcSid='S-1-5-21-100-200-300-1001'
function MapPath([string]$Path){foreach($root in @($script:maps.Keys)){if($Path.StartsWith($root,[StringComparison]::Ordinal)) {return $script:maps[$root]+$Path.Substring($root.Length)}};return $Path}
function Get-Item {param($LiteralPath,[switch]$Force,$ErrorAction) if($script:deny-and$LiteralPath-ceq'C:\ProgramData\RackClick'){throw [UnauthorizedAccessException]::new('fixture access denied')};return Microsoft.PowerShell.Management\Get-Item -LiteralPath (MapPath $LiteralPath) -Force -ErrorAction Stop}
function Get-Acl {param($LiteralPath,$ErrorAction) Microsoft.PowerShell.Security\Get-Acl -LiteralPath (MapPath $LiteralPath) -ErrorAction Stop}
function Get-LocalUser {param($ErrorAction) @([pscustomobject]@{Name='RackClickSvc';SID=[Security.Principal.SecurityIdentifier]::new($svcSid);Description='marker removed'},[pscustomobject]@{Name='RackClickOperador';SID=[Security.Principal.SecurityIdentifier]::new('S-1-5-21-100-200-300-1002')})}
function Assert-SetupSupportedHost {return [pscustomobject]@{valid=$true;productType=3;domainRole=2;partOfDomain=$false}}
function Get-CimInstance {param($ClassName,$ErrorAction) switch($ClassName){Win32_Service{return $script:services} Win32_Process{return $script:processes} default{throw 'Unexpected CIM fixture query'}}}
function Get-ScheduledTask {param($ErrorAction) return $script:tasks}
function Get-NetTCPConnection {param($State,$ErrorAction) return $script:listeners}
function Resolve-SetupAccountSid([string]$Account){if($Account-eq'RackClickSvc'){return $svcSid};return $Account}
function Invoke-CimMethod {param($InputObject,$MethodName,$ErrorAction) [pscustomobject]@{ReturnValue=0;Sid=$InputObject.OwnerSid}}
function Assert-SetupAdministrator {}
function Assert-SetupResetPrivilegedFile([string]$Path) {}
function Move-SetupNamespaceHub([string]$Source,[string]$Destination,[string]$Id){$script:moves++;if($script:failSecond-and$script:moves-eq2){throw 'fixture second move denied'};$mapped=MapPath $Source;Move-SetupNamespaceDirectory $mapped (MapPath $Destination) $mapped $Id}
$plan=Get-SetupNamespacePlan -Id $id
Check (@($plan.blockers).Count-eq0-and$plan.hubs.Count-eq2) 'Markerless orphan fixture and unknown old ACL need no attribution repair'
Check ($plan.preservedAccounts.Count-eq2) 'Old service account and manual operator preserved without mutation'
$again=Get-SetupNamespacePlan -Id $id;Check ($again.fingerprint-ceq$plan.fingerprint) 'Plan fingerprint stable without reading descendants'
$script:deny=$true;Reject {Get-SetupNamespacePlan -Id $id} 'Access denied propagates rather than being treated as absent';$script:deny=$false
$script:services=@([pscustomobject]@{Name='OtherService';PathName='"C:\ProgramData\RackClick\x.exe"';StartName='SYSTEM'})
Check ((Get-SetupNamespacePlan -Id $id).blockers-contains'namespace_registered_service_preserved') 'Registered service reference blocks even when stopped or foreign named'
$script:services=@([pscustomobject]@{Name='OtherService';PathName='C:\Other\x.exe';StartName='RackClickSvc'})
Check ((Get-SetupNamespacePlan -Id $id).blockers-contains'namespace_registered_service_preserved') 'Service account SID reference blocks even outside old roots'
$script:services=@();$script:tasks=@([pscustomobject]@{TaskName='Foreign';TaskPath='\';Principal=[pscustomobject]@{UserId='SYSTEM'};Actions=@([pscustomobject]@{Execute='cmd.exe';Arguments='';WorkingDirectory='C:\ProgramData\RackClick\old'})})
Check ((Get-SetupNamespacePlan -Id $id).blockers-contains'namespace_registered_task_preserved') 'Task working directory reference blocks'
$script:tasks[0].Actions[0].WorkingDirectory='';$script:tasks[0].Actions[0].Arguments='-File C:\ProgramData\RackClick\run.ps1'
Check ((Get-SetupNamespacePlan -Id $id).blockers-contains'namespace_registered_task_preserved') 'Task arguments reference blocks'
$script:tasks=@();$script:processes=@([pscustomobject]@{ProcessId=10;ExecutablePath='C:\Other\postgres.exe';CommandLine='postgres -D C:\ProgramData\RackClick\pgdata';OwnerSid='S-1-5-18'})
Check ((Get-SetupNamespacePlan -Id $id).blockers-contains'namespace_running_process_preserved') 'PostgreSQL data argument blocks without killing process'
$script:processes[0].CommandLine='outside';$script:processes[0].OwnerSid=$svcSid
Check ((Get-SetupNamespacePlan -Id $id).blockers-contains'namespace_running_process_preserved') 'Old account process blocks even outside roots'
$script:processes=@();$script:listeners=@([pscustomobject]@{LocalPort=55441})
Check ((Get-SetupNamespacePlan -Id $id).blockers-contains'namespace_install_port_in_use_55441') 'Occupied PostgreSQL port blocks before archival'
$script:listeners=@();$journal=Join-Path $fixture 'journal';$null=[IO.Directory]::CreateDirectory($journal)
Reject {Invoke-SetupNamespacePlan $plan 'C:\ProgramData\RackClick\management' -Confirm:$false} 'Journal inside archived hub rejected before mutation'
$altered=$plan|ConvertTo-Json -Depth 12|ConvertFrom-Json;$altered.hubs[0].destination='C:\Elsewhere'
Reject {Invoke-SetupNamespacePlan $altered $journal -Confirm:$false} 'Tampered archive target rejected before any move'
$preview=Invoke-SetupNamespacePlan $plan $journal -WhatIf
Check ($script:moves-eq0-and-not$preview.cleanupComplete) 'WhatIf performs no moves or account changes'
$script:failSecond=$true
Reject {Invoke-SetupNamespacePlan $plan $journal -Confirm:$false} 'Second move failure propagates and blocks installer continuation'
$partial=[IO.File]::ReadAllText((Join-Path $journal 'reset-result.json'))|ConvertFrom-Json
Check (-not$partial.cleanupComplete-and$partial.code-ceq'namespace_partial_preserved'-and$partial.actions.Count-eq1) 'Partial journal records first move and never claims success'
Check ([IO.Directory]::Exists($script:maps['C:\ProgramData\RackClick']+'-Previous-'+$id)-and[IO.Directory]::Exists($script:maps['C:\Program Files\RackClick'])) 'Both old hubs remain present after partial failure'
# A completely separate fixture checks the successful full state machine.
$script:maps=@{'C:\ProgramData\RackClick'=(Join-Path $fixture 'success-data');'C:\Program Files\RackClick'=(Join-Path $fixture 'success-code')};foreach($path in $script:maps.Values){$null=[IO.Directory]::CreateDirectory($path)}
$script:failSecond=$false;$script:moves=0;$okPlan=Get-SetupNamespacePlan -Id ([guid]::NewGuid().ToString('D'));$okJournal=Join-Path $fixture 'success-journal';$null=[IO.Directory]::CreateDirectory($okJournal)
$ok=Invoke-SetupNamespacePlan $okPlan $okJournal -Confirm:$false
Check ($ok.valid-and$ok.cleanupComplete-and$ok.exitCode-eq0-and$ok.actions.Count-eq2) 'Successful state machine verifies two actual fixture moves'
Check (@($ok.retiredAccounts).Count-eq0) 'Successful cleanup retires no Windows account'
Reject {Invoke-SetupNamespacePlan $okPlan $okJournal -Confirm:$false} 'Completed plan cannot be reused'
$result=[ordered]@{valid=$true;passed=$checks.Count;checks=@($checks.ToArray());fixtureRoot=$fixture;environment='Windows PowerShell5.1 x64, unprivileged own directories; OS inventory mocked';osAccountsChanged=0;servicesChanged=0;tasksChanged=0;productionCleanupExecuted=$false;limits=@('Native generic directory move executed with fixture siblings, preserving SDDL and bytes','Production-root wrapper binding validated; successful orchestration maps its two roots to own fixture','No elevated Windows Server installation or cleanup executed')}
if($OutputPath){[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath),($result|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 6 -Compress
