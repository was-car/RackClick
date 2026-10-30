#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot '..\..\windows\server-install\Set-RackClickServerNetwork.ps1') -FunctionsOnly
$checks=New-Object 'Collections.Generic.List[string]'
function Assert-Correction([bool]$Condition,[string]$Name){if(-not$Condition){throw ('Test failed: '+$Name)};$checks.Add($Name)}
Assert-Correction (Test-RcNetworkFirewallAddresses @('192.168.250.0/255.255.255.0') @('192.168.250.0/24')) 'Provider dotted mask equals target CIDR'
Assert-Correction (Test-RcNetworkFirewallAddresses @('192.168.250.78/255.255.255.255') @('192.168.250.78')) 'Exact host matches only its own /32'
Assert-Correction (Test-RcNetworkFirewallAddresses @('192.168.178.0/255.255.255.0') @('192.168.178.0/24')) 'Original snapshot mask can be verified during rollback'
foreach($value in @('Any','LocalSubnet','192.168.250.0/23','192.168.250.0/255.255.0.0','192.168.250.0/255.0.255.0','192.168.250.78/24','192.168.250.0/0','192.168.250.0/024','192.168.250.0/33','192.168.178.0/24','::/0','3232307712/24','192.168.250.0-192.168.250.255','192.168.250.0/24 ')){
 Assert-Correction (-not(Test-RcNetworkFirewallAddresses @($value) @('192.168.250.0/24'))) ('Reject foreign or ambiguous scope '+$value)
}
Assert-Correction (-not(Test-RcNetworkFirewallAddresses @('192.168.250.0/24','10.0.0.0/8') @('192.168.250.0/24'))) 'Additional remote range is never ignored'
Assert-Correction (-not(Test-RcNetworkFirewallAddresses @() @('192.168.250.0/24'))) 'Missing remote address is rejected'
$ctx=@{profile=@{bindAddress='192.168.250.78';publicOrigin='https://192.168.250.78:5443'};receipt=@{publicOrigin='https://192.168.250.78:5443'};plan=@{bindAddress='192.168.250.78';publicOrigin='https://192.168.250.78:5443';allowedSubnet='192.168.250.0/24'};firewall=@{local=@('192.168.250.78');remote=@('192.168.250.0/255.255.255.0')}}
Assert-Correction (Test-RcNetworkAlreadyConfigured $ctx) 'Idempotency recognizes a semantically identical firewall scope'

# These are actual native ACL operations on fresh files owned by this process,
# not a privileged test on any RackClick installation.
Initialize-RcNetworkNative
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('RackClick-network-correction-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($fixture)
$file=Join-Path $fixture 'inherited.txt';[IO.File]::WriteAllText($file,'fixture unchanged')
$original=[RackClickNetworkMaintenanceNative]::Snapshot($file)
$sd=New-Object Security.AccessControl.RawSecurityDescriptor($original.Sddl)
Assert-Correction (($sd.ControlFlags-band[Security.AccessControl.ControlFlags]::DiscretionaryAclProtected)-eq0) 'Fresh fixture starts with an inherited DACL'
$acl=Get-Acl -LiteralPath $file;$acl.SetAccessRuleProtection($true,$true);Set-Acl -LiteralPath $file -AclObject $acl
$protected=[RackClickNetworkMaintenanceNative]::Snapshot($file)
Assert-Correction ($protected.Sddl-cne$original.Sddl) 'Reproduce the protected inheritance change'
Set-RcNetworkExactAcl $file $original.Sddl

$restored=[RackClickNetworkMaintenanceNative]::Snapshot($file)
Assert-Correction ($restored.Sddl-ceq$original.Sddl-and(Get-RcNetworkHash $restored.Bytes)-ceq(Get-RcNetworkHash $original.Bytes)) 'Native restore preserves exact inherited SDDL and content'
Set-RcNetworkExactAcl $file $original.Sddl
Assert-Correction (([RackClickNetworkMaintenanceNative]::Snapshot($file)).Sddl-ceq$original.Sddl) 'Repeating an inherited ACL restoration is idempotent'
Set-RcNetworkExactAcl $file $protected.Sddl
Assert-Correction (([RackClickNetworkMaintenanceNative]::Snapshot($file)).Sddl-ceq$protected.Sddl) 'Protected ACL can also be restored exactly'
Set-RcNetworkExactAcl $file $original.Sddl

# Exercise the actual old producer, including its extra AUTO_INHERITED flag.
# A backup descriptor can legitimately omit that flag, while still carrying
# inherited ACEs. Security-only BackupWrite must restore it byte for byte.
. (Join-Path $PSScriptRoot '..\..\windows\server-install\RackClick.Setup.Security.ps1')
Initialize-SetupSecurityNative
$withoutAi=New-Object Security.AccessControl.RawSecurityDescriptor($original.Sddl)
$withoutAi.SetFlags($withoutAi.ControlFlags-band(-bnot([Security.AccessControl.ControlFlags]::DiscretionaryAclAutoInherited)) -band(-bnot([Security.AccessControl.ControlFlags]::DiscretionaryAclProtected)))
$withoutAiSddl=$withoutAi.GetSddlForm([Security.AccessControl.AccessControlSections]'Owner,Group,Access')
Set-RcNetworkExactAcl $file $withoutAiSddl
$authenticBefore=[RackClickNetworkMaintenanceNative]::Snapshot($file)
Assert-Correction ($authenticBefore.Sddl-ceq$withoutAiSddl) 'BackupWrite preserves a descriptor that originally omitted AUTO_INHERITED'
[RackClickSetupSecurityNative]::SetAcl($file,$authenticBefore.Sddl)
$authenticBroken=[RackClickNetworkMaintenanceNative]::Snapshot($file)
Assert-Correction ($authenticBroken.Sddl-cne$authenticBefore.Sddl) 'The actual old native ACL producer reproduces the defect'
$savedPrivilege=(Get-Item function:Invoke-SetupSecurityPrivileges).ScriptBlock
function Invoke-SetupSecurityPrivileges {param([scriptblock]$Action);& $Action}
try{
 Write-RcNetworkExisting @{restoring=$true} $file $authenticBefore.Bytes $authenticBefore.Sddl
 $authenticRestored=[RackClickNetworkMaintenanceNative]::Snapshot($file)
 Assert-Correction ($authenticRestored.Sddl-ceq$authenticBefore.Sddl-and(Get-RcNetworkHash $authenticRestored.Bytes)-ceq(Get-RcNetworkHash $authenticBefore.Bytes)) 'Actual old native producer followed by new WriteExisting restores exact original ACL and content'
}finally{Set-Item function:Invoke-SetupSecurityPrivileges $savedPrivilege}

# Rollback flags: a firewall readback failure occurred before Task update.
# It must not re-register an unchanged task or lose its original failure stage.
$saved=@{}
foreach($name in @('Release-RcNetworkLocks','Disable-ScheduledTask','Get-Service','Test-RcNetworkStopped','Write-RcNetworkExisting','Set-NetFirewallRule','Assert-RcNetworkFirewall','Set-RcNetworkTask','Enable-ScheduledTask','Get-ScheduledTask','Write-RcNetworkJournal')){if(Test-Path ('function:'+ $name)){$saved[$name]=(Get-Item ('function:'+ $name)).ScriptBlock}}
$script:calls=New-Object 'Collections.Generic.List[string]'
function Release-RcNetworkLocks($Context){}
function Disable-ScheduledTask {param($TaskName,$TaskPath);$script:calls.Add('disable')}
function Get-Service {param($Name);return @{Status='Stopped'}}
function Test-RcNetworkStopped($Context){}
function Write-RcNetworkExisting($Context,$Path,$Bytes,$Sddl){$script:calls.Add('file');if($Context.failFile){throw (New-Object UnauthorizedAccessException('must not leak fixture details'))}}
function Set-NetFirewallRule {param($Name,$LocalAddress,$RemoteAddress);$script:calls.Add('firewall')}
function Assert-RcNetworkFirewall($Context,$Local,$Remote){$script:calls.Add('firewall_verified')}
function Set-RcNetworkTask($Context,$Arguments){$script:calls.Add('task_update')}
function Enable-ScheduledTask {param($TaskName,$TaskPath);$script:calls.Add('enable')}
function Get-ScheduledTask {param($TaskName,$TaskPath);return @{Settings=@{Enabled=$true}}}
function Write-RcNetworkJournal($Context,$Stage){$Context.stage=$Stage}
try{
 foreach($fail in @($false,$true)){
  $script:calls.Clear();$c=@{receipt=@{serviceName='FixtureOnly';backupTaskName='FixtureOnly';firewallRule='FixtureOnly'};stopRequested=$true;filesTouched=$true;infrastructureTouched=$true;firewallTouched=$true;taskTouched=$false;unsafeChildAlive=$false;entries=@(@{key='receipt';path='fixture';snapshot=@{Bytes=@(1);Sddl='unused'}});newCaThumbprint='';firewall=@{local=@('192.168.178.141');remote=@('192.168.178.0/24')};taskWasEnabled=$true;serviceWasRunning=$false;failFile=$fail;failureStage='infrastructure'}
  Undo-RcNetworkChange $c
  Assert-Correction (-not$script:calls.Contains('task_update')) ('Never re-register untouched backup task; failure='+$fail)
  Assert-Correction ($c.failureStage-ceq'infrastructure') ('Preserve original failure phase; failure='+$fail)
  if($fail){Assert-Correction ($c.rollbackStatus-ceq'rollback_partial'-and$c.rollbackErrors.Count-eq1-and$c.rollbackErrors[0].step-ceq'file_receipt'-and-not$script:calls.Contains('enable')) 'Rollback identifies failed file and leaves backup disabled';Assert-Correction (-not(($c.rollbackErrors|ConvertTo-Json)-match'must not leak')) 'Rollback diagnostics never export raw exception text'}
  else{Assert-Correction ($c.rollbackStatus-ceq'rollback_restored_service_stopped'-and$c.rollbackErrors.Count-eq0-and$script:calls.Contains('firewall_verified')-and$script:calls.Contains('enable')) 'Successful rollback verifies restored firewall and enables original task'}
 }
}finally{foreach($name in $saved.Keys){Set-Item ('function:'+ $name) $saved[$name]}}
$result=[ordered]@{schemaVersion=1;valid=$true;passed=$checks.Count;checks=@($checks);environment='Windows PowerShell 5.1; native user-owned ACL files and callback-based infrastructure tests';fixture=$fixture;privilegedOperationsExecuted=0;serviceOperationsExecuted=0;firewallOperationsExecuted=0;authenticationAttempts=0;databaseOperationsExecuted=0}
if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 6 -Compress
