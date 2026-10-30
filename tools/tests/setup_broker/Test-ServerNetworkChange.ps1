#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot '..\..\windows\server-install\Set-RackClickServerNetwork.ps1'
. $source -FunctionsOnly
$checks=New-Object 'Collections.Generic.List[string]'
function Assert-NetworkTest([bool]$Condition,[string]$Name){if(-not$Condition){throw ('Test failed: '+$Name)};$checks.Add($Name)}
$id='606b8c29-41de-4dc0-b63d-ade836000d9e'
$p=Get-RcNetworkPlan -InstallationId $id -BindAddress '192.168.250.78' -AllowedSubnet '192.168.250.0/24' -PublicHost ''
Assert-NetworkTest ($p.bindAddress-ceq'192.168.250.78'-and$p.publicOrigin-ceq'https://192.168.250.78:5443') 'Target network preserves HTTPS port'
Assert-NetworkTest ($p.installationId-ceq$id-and$p.postgresPort-eq55441) 'Installation identity and database port preserved'
foreach($case in @(
 @{name='loopback';ip='127.0.0.1';net='127.0.0.0/24';hostName=''},
 @{name='all interfaces';ip='0.0.0.0';net='0.0.0.0/24';hostName=''},
 @{name='IPv6';ip='::1';net='192.168.250.0/24';hostName=''},
 @{name='link local';ip='169.254.2.3';net='169.254.2.0/24';hostName=''},
 @{name='foreign subnet';ip='192.168.250.78';net='192.168.178.0/24';hostName=''},
 @{name='subnet with host bits';ip='192.168.250.78';net='192.168.250.78/24';hostName=''},
 @{name='unbounded subnet';ip='192.168.250.78';net='0.0.0.0/0';hostName=''},
 @{name='wildcard hostname';ip='192.168.250.78';net='192.168.250.0/24';hostName='*.example.test'},
 @{name='URL instead of hostname';ip='192.168.250.78';net='192.168.250.0/24';hostName='https://example.test'},
 @{name='mismatched public IP';ip='192.168.250.78';net='192.168.250.0/24';hostName='192.168.250.79'}
)){
 $rejected=$false
 try{$null=Get-RcNetworkPlan -InstallationId $id -BindAddress $case.ip -AllowedSubnet $case.net -PublicHost $case.hostName}catch{$rejected=$true}
 Assert-NetworkTest $rejected ('Reject '+$case.name)
}
$rejected=$false;try{$null=Get-RcNetworkPlan -InstallationId '..\foreign' -BindAddress '192.168.250.78' -AllowedSubnet '192.168.250.0/24' -PublicHost ''}catch{$rejected=$true}
Assert-NetworkTest $rejected 'Reject foreign installation path input'
$base='C:\ProgramData\RackClick\Instances\'+$id
$profile=[pscustomobject][ordered]@{
 schemaVersion=1;profileKind='RackClickProductionServer';profileId='11111111-1111-4111-8111-111111111111'
 installationPath=($base+'\instance');installationSha256=('a'*64);deploymentPath=($base+'\instance\deployment');deploymentSha256=('b'*64)
 expectedWindowsSid='S-1-5-21-1-2-3-1001';publicOrigin='https://192.168.178.141:5443';bindAddress='192.168.178.141';runtimeRoot=($base+'\instance\runtime');createdUtc='2026-10-20T00:00:00Z'
 certificate=[pscustomobject]@{certificateSha256=('c'*64);thumbprint=('A'*40);expiresUtc='2026-11-20T00:00:00Z';files=[pscustomobject]@{'RootCA.cer'=('c'*64);'server.cer'=('c'*64);'server.pfx'=('c'*64);'tls-password.txt'=('e'*64)}}
}
$config=[pscustomobject][ordered]@{schemaVersion=1;serviceName='RackClick';runtimeScriptPath=('C:\Program Files\RackClick\'+$id+'\operators\server-install\Invoke-RackClickServerRuntime.ps1');serverManifestPath=($profile.runtimeRoot+'\server-profile.json');serverManifestSha256=('f'*64);logDirectory=($profile.runtimeRoot+'\logs')}
$receipt=[pscustomobject][ordered]@{schemaVersion=1;installationId=$id;serviceName='RackClick';serviceSid=$profile.expectedWindowsSid;instancePath=$profile.installationPath;managementPath=($base+'\management');publicOrigin=$profile.publicOrigin;manifestSha256=('f'*64);trustedCaThumbprint=('A'*40);backupArguments=('-NoProfile -File "C:\Program Files\RackClick\'+$id+'\operators\server-install\Invoke-RackClickScheduledBackup.ps1" -ManifestPath "'+$config.serverManifestPath+'" -ExpectedManifestSha256 '+('f'*64));rebootVerified=$false;productAdopted=$false}
$tls=[pscustomobject]@{certificateSha256=('d'*64);thumbprint=('B'*40);rootThumbprint=('C'*40);expiresUtc='2027-01-18T00:00:00Z';files=[pscustomobject]@{'RootCA.cer'=('d'*64);'server.cer'=('d'*64);'server.pfx'=('d'*64);'tls-password.txt'=('e'*64)}}
$before=@($profile,$config,$receipt)|ConvertTo-Json -Depth 12 -Compress
$changed=ConvertTo-RcNetworkConfiguration -Profile $profile -Config $config -Receipt $receipt -Tls $tls -Plan $p
Assert-NetworkTest (($before)-ceq(@($profile,$config,$receipt)|ConvertTo-Json -Depth 12 -Compress)) 'Transformation leaves source objects intact'
Assert-NetworkTest ($changed.profile.bindAddress-ceq$p.bindAddress-and$changed.profile.publicOrigin-ceq$p.publicOrigin) 'Profile binds selected IP and origin'
foreach($key in @('installationPath','installationSha256','deploymentPath','deploymentSha256','expectedWindowsSid','profileId','runtimeRoot','createdUtc')){
 Assert-NetworkTest ($changed.profile.$key-ceq$profile.$key) ('Preserve profile '+$key)
}
$sha=[Security.Cryptography.SHA256]::Create();try{$actual=([BitConverter]::ToString($sha.ComputeHash([byte[]]$changed.profileBytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
Assert-NetworkTest ($actual-ceq$changed.profileSha256) 'Profile reference hashes exact serialized bytes'
Assert-NetworkTest ($changed.config.serverManifestSha256-ceq$actual-and$changed.receipt.manifestSha256-ceq$actual) 'Config and receipt reference the same profile bytes'
Assert-NetworkTest ($changed.receipt.backupArguments.Contains('-ExpectedManifestSha256 '+$actual)-and-not$changed.receipt.backupArguments.Contains('f'*64)) 'Backup action replaces the previous profile reference'
Assert-NetworkTest ($changed.receipt.publicOrigin-ceq$p.publicOrigin-and$changed.receipt.trustedCaThumbprint-ceq$tls.rootThumbprint) 'Receipt trusts the new CA rather than the leaf certificate'
Assert-NetworkTest ($changed.receipt.serviceSid-ceq$receipt.serviceSid-and$changed.receipt.instancePath-ceq$receipt.instancePath-and-not$changed.receipt.productAdopted) 'Change does not adopt product or replace service/database identity'
Assert-NetworkTest ($changed.profile.certificate.files.'tls-password.txt'-ceq$profile.certificate.files.'tls-password.txt') 'Existing TLS password reference preserved'
$again=ConvertTo-RcNetworkConfiguration -Profile $profile -Config $config -Receipt $receipt -Tls $tls -Plan $p
Assert-NetworkTest ($changed.profileSha256-ceq$again.profileSha256) 'Same proposal produces the same profile hash'

# Fault injection verifies orchestration, not native SCM/firewall/Task Scheduler.
$originals=@{}
foreach($name in @('Save-RcNetworkBackup','Write-RcNetworkJournal','Suspend-RcNetwork','Set-RcNetworkFiles','Set-RcNetworkInfrastructure','Test-RcNetworkApplied','Complete-RcNetworkChange','Undo-RcNetworkChange')){$originals[$name]=(Get-Item ('function:'+ $name)).ScriptBlock}
$script:networkCalls=New-Object 'Collections.Generic.List[string]'
function Add-NetworkFixtureCall($Context,[string]$Name){$script:networkCalls.Add($Name);if($Context.failAt-ceq$Name){throw ('fixture_'+$Name)}}
function Save-RcNetworkBackup($Context){Add-NetworkFixtureCall $Context 'backup';$Context.backupComplete=$true}
function Write-RcNetworkJournal($Context,[string]$Stage){$script:networkCalls.Add('journal:'+$Stage)}
function Suspend-RcNetwork($Context){Add-NetworkFixtureCall $Context 'suspend';$Context.fixtureMutated=$true}
function Set-RcNetworkFiles($Context){Add-NetworkFixtureCall $Context 'files'}
function Set-RcNetworkInfrastructure($Context){Add-NetworkFixtureCall $Context 'infrastructure'}
function Test-RcNetworkApplied($Context){Add-NetworkFixtureCall $Context 'validate'}
function Complete-RcNetworkChange($Context){Add-NetworkFixtureCall $Context 'commit';$Context.committed=$true}
function Undo-RcNetworkChange($Context){$script:networkCalls.Add('rollback');$Context.fixtureMutated=$false;$Context.rollbackStatus='restored'}
try{
 foreach($fault in @('','backup','suspend','files','infrastructure','validate','commit')){
  $script:networkCalls.Clear();$ctx=@{backupComplete=$false;committed=$false;rollbackStatus='not_needed';stage='preflight';failAt=$fault;fixtureMutated=$false}
  $failed=$false;try{$null=Invoke-RcNetworkTransaction $ctx}catch{$failed=$true}
  $calls=@($script:networkCalls|Where-Object{-not$_.StartsWith('journal:')})
  if($fault-eq''){
   Assert-NetworkTest (-not$failed-and$ctx.committed-and($calls-join',')-ceq'backup,suspend,files,infrastructure,validate,commit') 'Commit occurs only after backup, changes and applied validation'
  }else{
   Assert-NetworkTest ($failed-and-not$ctx.committed) ('Failure at '+$fault+' cannot report a committed change')
   if($fault-eq'backup'){Assert-NetworkTest (-not$calls.Contains('suspend')-and-not$calls.Contains('rollback')) 'Incomplete backup prevents mutations and rollback'}
   else{Assert-NetworkTest ($calls[-1]-ceq'rollback'-and-not$ctx.fixtureMutated-and$ctx.rollbackStatus-ceq'restored') ('Failure at '+$fault+' invokes recovery')}
  }
 }
}finally{foreach($name in $originals.Keys){Set-Item ('function:'+ $name) $originals[$name]}}
$result=[ordered]@{schemaVersion=1;valid=$true;passed=$checks.Count;checks=@($checks);environment='Windows PowerShell 5.1; pure transformations and fault-injected callbacks';privilegedOperationsExecuted=0;authenticationExecuted=0;databaseOperationsExecuted=0}
if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 6 -Compress
