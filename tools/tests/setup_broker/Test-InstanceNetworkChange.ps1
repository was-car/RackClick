#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot '..\..\windows\server-install\Set-RackClickInstanceNetwork.ps1'
. $source -FunctionsOnly
$checks=New-Object 'Collections.Generic.List[string]'
function Assert-NetworkTest([bool]$Condition,[string]$Name){if(-not$Condition){throw ('Test failed: '+$Name)};$checks.Add($Name)}
$id='606b8c29-41de-4dc0-b63d-ade836000d9e'
$p=Get-RcNetworkPlan -InstallationId $id -BindAddress '192.168.250.78' -AllowedSubnet '192.168.250.0/24' -PublicHost '' -HttpsPort 5443 -PostgresPort 55441
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
 try{$null=Get-RcNetworkPlan -InstallationId $id -BindAddress $case.ip -AllowedSubnet $case.net -PublicHost $case.hostName -HttpsPort 5443 -PostgresPort 55441}catch{$rejected=$true}
 Assert-NetworkTest $rejected ('Reject '+$case.name)
}
$rejected=$false;try{$null=Get-RcNetworkPlan -InstallationId '..\foreign' -BindAddress '192.168.250.78' -AllowedSubnet '192.168.250.0/24' -PublicHost '' -HttpsPort 5443 -PostgresPort 55441}catch{$rejected=$true}
Assert-NetworkTest $rejected 'Reject foreign installation path input'
$base='C:\ProgramData\RackClick\Instances\'+$id
$profile=[pscustomobject][ordered]@{
 schemaVersion=1;profileKind='RackClickProductionServer';profileId='11111111-1111-4111-8111-111111111111'
 installationPath=($base+'\instance');installationSha256=('a'*64);deploymentPath=($base+'\instance\deployment');deploymentSha256=('b'*64)
 expectedWindowsSid='S-1-5-21-1-2-3-1001';publicOrigin='https://192.168.178.141:5443';bindAddress='192.168.178.141';runtimeRoot=($base+'\instance\runtime');createdUtc='2026-10-20T00:00:00Z'
 certificate=[pscustomobject]@{certificateSha256=('c'*64);thumbprint=('A'*40);expiresUtc='2026-11-20T00:00:00Z';files=[pscustomobject]@{'RootCA.cer'=('c'*64);'server.cer'=('c'*64);'server.pfx'=('c'*64);'tls-password.txt'=('e'*64)}}
}
$config=[pscustomobject][ordered]@{schemaVersion=1;serviceName='RackClick';runtimeScriptPath=('C:\Program Files\RackClick\'+$id+'\operators\server-install\Invoke-RackClickServerRuntime.ps1');serverManifestPath=($profile.runtimeRoot+'\server-profile.json');serverManifestSha256=('f'*64);logDirectory=($profile.runtimeRoot+'\logs')}
$receipt=[pscustomobject][ordered]@{schemaVersion=1;installationId=$id;serviceName='RackClick';serviceSid=$profile.expectedWindowsSid;instancePath=$profile.installationPath;managementPath=($base+'\management');publicOrigin=$profile.publicOrigin;manifestSha256=('f'*64);trustedCaThumbprint=('A'*40);codeRoot=('C:\Program Files\RackClick\'+$id);firewallRule=('RackClick-'+$id);backupTaskName=('RackClick-Backup-'+$id);backupExecutable=(Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe');backupArguments=('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "C:\Program Files\RackClick\'+$id+'\operators\server-install\Invoke-RackClickScheduledBackup.ps1" -ManifestPath "'+$config.serverManifestPath+'" -ExpectedManifestSha256 '+('f'*64));rebootVerified=$false;productAdopted=$false}
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

function Copy-InstanceNetworkFixture($Object){return ($Object|ConvertTo-Json -Depth 30 -Compress|ConvertFrom-Json)}
function Assert-InstanceNetworkRejected([scriptblock]$Action,[string]$Expected,[string]$Name){
 $code='';try{& $Action}catch{$code=$_.Exception.Message}
 Assert-NetworkTest ($code-ceq$Expected) $Name
}
foreach($ports in @(@(0,55441),@(5443,0),@(5443,5443),@(80,55441),@(5443,65536))){
 Assert-InstanceNetworkRejected {Get-RcNetworkPlan $id '192.168.178.141' '192.168.178.0/24' '' $ports[0] $ports[1]} 'network_ports_not_supported' ('Reject unsupported or overlapping ports '+($ports-join'/'))
}
foreach($invalidId in @($id.ToUpperInvariant(),'00000000-0000-0000-0000-000000000000',('{'+$id+'}'))){
 Assert-InstanceNetworkRejected {Get-RcNetworkPlan $invalidId '192.168.178.141' '192.168.178.0/24' '' 5443 55441} 'network_installation_not_supported' 'Reject noncanonical or empty installation identity'
}
function New-InstanceNetworkFixture([string]$Identity,[string]$Service,[int]$WebPort,[int]$PgPort,[bool]$Restored){
 $fixtureBase='C:\ProgramData\RackClick\Instances\'+$Identity
 $fixtureReceipt=Copy-InstanceNetworkFixture $receipt
 $fixtureReceipt.installationId=$Identity;$fixtureReceipt.serviceName=$Service;$fixtureReceipt.instancePath=$fixtureBase+'\instance';$fixtureReceipt.managementPath=$fixtureBase+'\management';$fixtureReceipt.codeRoot='C:\Program Files\RackClick\'+$Identity
 $fixtureReceipt.firewallRule='RackClick-'+$Identity;$fixtureReceipt.backupTaskName='RackClick-Backup-'+$Identity;$fixtureReceipt.publicOrigin='https://192.168.250.78:'+$WebPort
 $fixtureReceipt.backupArguments=Get-RcNetworkBackupArguments $fixtureReceipt $fixtureReceipt.manifestSha256
 $fixtureProfile=Copy-InstanceNetworkFixture $profile
 $fixtureProfile.installationPath=$fixtureReceipt.instancePath;$fixtureProfile.runtimeRoot=$fixtureReceipt.instancePath+'\runtime';$fixtureProfile.deploymentPath=$fixtureReceipt.instancePath+'\deployment';$fixtureProfile.publicOrigin=$fixtureReceipt.publicOrigin;$fixtureProfile.bindAddress='192.168.250.78'
 $fixtureConfig=Copy-InstanceNetworkFixture $config
 $fixtureConfig.serviceName=$Service;$fixtureConfig.runtimeScriptPath=$fixtureReceipt.codeRoot+'\operators\server-install\Invoke-RackClickServerRuntime.ps1';$fixtureConfig.serverManifestPath=$fixtureProfile.runtimeRoot+'\server-profile.json';$fixtureConfig.logDirectory=$fixtureProfile.runtimeRoot+'\logs'
 $fixtureInstallation=[pscustomobject]@{schemaVersion=$(if($Restored){2}else{1});kind='RackClickPrivateInstallation';state='prepared';rootPath=$fixtureReceipt.instancePath;deploymentId='33333333-3333-4333-8333-333333333333';deploymentSha256=$fixtureProfile.deploymentSha256}
 $fixtureDeployment=[pscustomobject]@{schemaVersion=1;kind='RackClickPrivateDeployment';state='prepared';id=$fixtureInstallation.deploymentId;rootPath=$fixtureProfile.deploymentPath;instanceId='44444444-4444-4444-8444-444444444444';stageManifestSha256=('1'*64);stageReceiptSha256=('2'*64)}
 $fixtureInstance=[pscustomobject]@{schemaVersion=1;kind='RackClickLabInstance';state='initialized';rootPath=$fixtureProfile.deploymentPath+'\instance';stagePath=$fixtureProfile.deploymentPath+'\distribution';id=$fixtureDeployment.instanceId;stageManifestSha256=$fixtureDeployment.stageManifestSha256;stageReceiptSha256=$fixtureDeployment.stageReceiptSha256;httpPort=$WebPort;postgresPort=$PgPort}
 return @{receipt=$fixtureReceipt;profile=$fixtureProfile;config=$fixtureConfig;installation=$fixtureInstallation;deployment=$fixtureDeployment;instance=$fixtureInstance;plan=(Get-RcNetworkPlan $Identity '192.168.178.141' '192.168.178.0/24' '' $WebPort $PgPort)}
}
$fixtures=@((New-InstanceNetworkFixture $id 'RackClick' 5443 55441 $false),(New-InstanceNetworkFixture '22222222-2222-4222-8222-222222222222' 'RackClick-Recovery-cb52d279' 5444 55442 $true))
foreach($fixture in $fixtures){
 $label=$fixture.receipt.serviceName
 Assert-RcNetworkReceipt $fixture.receipt $fixture.plan
 Assert-RcNetworkInstanceBinding $fixture.receipt $fixture.profile $fixture.installation $fixture.deployment $fixture.instance $fixture.plan
 Assert-NetworkTest $true ($label+' passes independent metadata preflight')
 $transformed=ConvertTo-RcNetworkConfiguration $fixture.profile $fixture.config $fixture.receipt $tls $fixture.plan
 Assert-NetworkTest ($transformed.receipt.serviceName-ceq$label-and$transformed.profile.publicOrigin-ceq('https://192.168.178.141:'+$fixture.plan.httpsPort)) ($label+' transforms only selected origin and preserves service')
 Assert-NetworkTest ($transformed.receipt.backupArguments-ceq(Get-RcNetworkBackupArguments $transformed.receipt $transformed.profileSha256)) ($label+' scheduled action remains bound to exact instance and new hash')
 Assert-NetworkTest ($transformed.receipt.serviceSid-ceq$fixture.receipt.serviceSid-and$transformed.profile.installationSha256-ceq$fixture.profile.installationSha256-and$transformed.profile.deploymentSha256-ceq$fixture.profile.deploymentSha256) ($label+' does not change credentials or offline installation')
 foreach($property in @('instancePath','managementPath','codeRoot','backupTaskName','firewallRule')){
  $bad=Copy-InstanceNetworkFixture $fixture.receipt;$bad.$property=$bad.$property+'-foreign'
  Assert-InstanceNetworkRejected {Assert-RcNetworkReceipt $bad $fixture.plan} 'network_receipt_binding_invalid' ($label+' rejects foreign '+$property)
 }
 $bad=Copy-InstanceNetworkFixture $fixture.receipt;$bad.serviceName="RackClick'; Name='Other"
 Assert-InstanceNetworkRejected {Assert-RcNetworkReceipt $bad $fixture.plan} 'network_receipt_binding_invalid' ($label+' rejects SCM query injection')
 $bad=Copy-InstanceNetworkFixture $fixture.receipt;$bad.backupArguments=$bad.backupArguments.Replace($fixture.receipt.installationId,'99999999-9999-4999-8999-999999999999')
 Assert-InstanceNetworkRejected {Assert-RcNetworkReceipt $bad $fixture.plan} 'network_backup_arguments_invalid' ($label+' rejects cross-instance backup action')
 $bad=Copy-InstanceNetworkFixture $fixture.receipt;$bad.publicOrigin='http://192.168.250.78:'+$fixture.plan.httpsPort
 Assert-InstanceNetworkRejected {Assert-RcNetworkReceipt $bad $fixture.plan} 'network_configuration_binding_invalid' ($label+' rejects HTTP origin')
 $bad=Copy-InstanceNetworkFixture $fixture.instance;$bad.httpPort++
 Assert-InstanceNetworkRejected {Assert-RcNetworkInstanceBinding $fixture.receipt $fixture.profile $fixture.installation $fixture.deployment $bad $fixture.plan} 'network_ports_not_supported' ($label+' rejects HTTPS port mismatch')
 $bad=Copy-InstanceNetworkFixture $fixture.instance;$bad.postgresPort++
 Assert-InstanceNetworkRejected {Assert-RcNetworkInstanceBinding $fixture.receipt $fixture.profile $fixture.installation $fixture.deployment $bad $fixture.plan} 'network_ports_not_supported' ($label+' rejects PostgreSQL port mismatch')
 $bad=Copy-InstanceNetworkFixture $fixture.instance;$bad.rootPath=$fixtures[0].instance.rootPath+'-other'
 Assert-InstanceNetworkRejected {Assert-RcNetworkInstanceBinding $fixture.receipt $fixture.profile $fixture.installation $fixture.deployment $bad $fixture.plan} 'network_installation_hash_mismatch' ($label+' rejects cross-instance database root')
 $bad=Copy-InstanceNetworkFixture $fixture.deployment;$bad.instanceId='55555555-5555-4555-8555-555555555555'
 Assert-InstanceNetworkRejected {Assert-RcNetworkInstanceBinding $fixture.receipt $fixture.profile $fixture.installation $bad $fixture.instance $fixture.plan} 'network_installation_hash_mismatch' ($label+' rejects mismatched deployment identity')
}

# Import only the production validator's function ASTs for native certificate
# fixtures. This does not execute script initialization or modify trust stores.
foreach($selection in @(@{file='RackClick.ServerRuntime.ps1';names=@('Stop-ServerCheck','Assert-ServerCertificate')},@{file='..\RackClick.Https.ps1';names=@('Get-HttpsDerElement','Get-HttpsBytesSha256')})){
 $tokens=$null;$parseErrors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path (Split-Path $source -Parent) $selection.file),[ref]$tokens,[ref]$parseErrors)
 Assert-NetworkTest ($parseErrors.Count-eq0) ('Certificate fixture validator parses '+$selection.file)
 foreach($name in $selection.names){$definition=@($ast.FindAll({param($node)$node-is[Management.Automation.Language.FunctionDefinitionAst]},$false)|Where-Object{$_.Name-ceq$name});. ([scriptblock]::Create($definition[0].Extent.Text))}
}
$script:instanceNetworkRootTrust=$true
function Test-RcNetworkRootTrusted([string]$Thumbprint,[string]$RootHash){return $script:instanceNetworkRootTrust}
$fixturePasswordBytes=[Text.Encoding]::UTF8.GetBytes(('fixture-only-'+[guid]::NewGuid().ToString('N')))
$tlsContext=@{plan=$fixtures[0].plan;entries=@(@{key='tls-password';snapshot=@{Bytes=$fixturePasswordBytes}})}
$generated=New-RcNetworkTls $tlsContext
$tlsContext.receipt=[pscustomobject]@{trustedCaThumbprint=$generated.rootThumbprint}
$tlsContext.profile=[pscustomobject]@{certificate=[pscustomobject]@{certificateSha256=$generated.certificateSha256;thumbprint=$generated.thumbprint;expiresUtc=$generated.expiresUtc;files=[pscustomobject]$generated.files}}
foreach($pair in @(@('root','RootCA.cer'),@('public','server.cer'),@('pfx','server.pfx'))){$tlsContext.entries+=@(@{key=$pair[0];snapshot=@{Bytes=$generated.data[$pair[1]]}})}
$reusable=Get-RcNetworkReusableTls $tlsContext
Assert-NetworkTest ($null-ne$reusable-and$reusable.reused-and$reusable.rootThumbprint-ceq$generated.rootThumbprint-and(Get-RcNetworkHash $reusable.data['server.pfx'])-ceq(Get-RcNetworkHash $generated.data['server.pfx'])) 'Valid TLS reuses exact PFX and root CA rather than rotating keys'
$tlsContext.plan=Get-RcNetworkPlan $id '192.168.250.78' '192.168.250.0/24' '' 5443 55441
Assert-NetworkTest ($null-ne(Get-RcNetworkReusableTls $tlsContext)) 'One generated certificate covers the two explicitly configured home and work IPs'
$tlsContext.plan=Get-RcNetworkPlan $id '192.168.250.79' '192.168.250.0/24' '' 5443 55441
Assert-NetworkTest ($null-eq(Get-RcNetworkReusableTls $tlsContext)) 'A different IP is not implicitly accepted by TLS reuse'
$tlsContext.plan=$fixtures[0].plan;$script:instanceNetworkRootTrust=$false
Assert-NetworkTest ($null-eq(Get-RcNetworkReusableTls $tlsContext)) 'Untrusted root is never treated as reusable TLS'
$script:instanceNetworkRootTrust=$true
$publicEntry=@($tlsContext.entries|Where-Object{$_.key-ceq'public'})[0];$originalPublic=$publicEntry.snapshot.Bytes;$publicEntry.snapshot.Bytes=$generated.data['RootCA.cer']
Assert-NetworkTest ($null-eq(Get-RcNetworkReusableTls $tlsContext)) 'Public certificate and PFX must contain the same leaf certificate'
$publicEntry.snapshot.Bytes=$originalPublic
$fixtureExpiredKey=New-Object Security.Cryptography.RSACng(3072);$fixtureExpiredCertificate=$null
try{
 $request=New-Object Security.Cryptography.X509Certificates.CertificateRequest('CN=RackClick expired test fixture',$fixtureExpiredKey,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)
 $fixtureExpiredCertificate=$request.CreateSelfSigned([DateTimeOffset]::UtcNow.AddDays(-3),[DateTimeOffset]::UtcNow.AddDays(-2))
 $pfxEntry=@($tlsContext.entries|Where-Object{$_.key-ceq'pfx'})[0];$originalPfx=$pfxEntry.snapshot.Bytes
 $pfxEntry.snapshot.Bytes=$fixtureExpiredCertificate.Export([Security.Cryptography.X509Certificates.X509ContentType]::Pfx,[Text.Encoding]::UTF8.GetString($fixturePasswordBytes))
 Assert-NetworkTest ($null-eq(Get-RcNetworkReusableTls $tlsContext)) 'Expired native certificate is rejected for reuse'
 $pfxEntry.snapshot.Bytes=$originalPfx
}finally{if($fixtureExpiredCertificate){$fixtureExpiredCertificate.Dispose()};$fixtureExpiredKey.Dispose()}

# Only mocked functions below may emulate SCM and HTTPS. No real service,
# scheduled task, firewall, account, certificate-store or database is touched.
$script:instanceNetworkMock=@{calls=(New-Object 'Collections.Generic.List[string]');ready=$true;service='';state='Stopped';binary='fixture-binary';badBinary=$false}
function Get-CimInstance([string]$ClassName,[string]$Filter){$script:instanceNetworkMock.calls.Add('query:'+$Filter);return [pscustomobject]@{PathName=$(if($script:instanceNetworkMock.badBinary){'changed'}else{$script:instanceNetworkMock.binary});StartName='S-1-5-21-1-2-3-1001';State=$script:instanceNetworkMock.state}}
function Start-Service([string]$Name){$script:instanceNetworkMock.calls.Add('start:'+$Name);$script:instanceNetworkMock.state='Running'}
function Stop-Service([string]$Name){$script:instanceNetworkMock.calls.Add('stop:'+$Name);$script:instanceNetworkMock.state='Stopped'}
function Get-Service([string]$Name){$mockService=[pscustomobject]@{Status=$(if($script:instanceNetworkMock.ready){$script:instanceNetworkMock.state}else{'Stopped'})};$mockService|Add-Member ScriptMethod WaitForStatus {param($Status,$Timeout)};return $mockService}
function Invoke-RestMethod([string]$Uri,[int]$TimeoutSec,[switch]$UseBasicParsing){$script:instanceNetworkMock.calls.Add('https:'+$Uri);return [pscustomobject]@{status='ready';schemaVersion=$(if($script:instanceNetworkMock.ready){13}else{12})}}
foreach($fixture in $fixtures){
 $script:instanceNetworkMock.calls.Clear();$script:instanceNetworkMock.ready=$true;$script:instanceNetworkMock.badBinary=$false;$script:instanceNetworkMock.state='Stopped'
 $context=@{receipt=$fixture.receipt;plan=$fixture.plan;serviceWasRunning=$false;serviceBinary=$script:instanceNetworkMock.binary;rollbackStatus='not_needed'}
 Start-RcNetworkExisting $context
 Assert-NetworkTest ($script:instanceNetworkMock.calls.Contains('start:'+$fixture.receipt.serviceName)-and$script:instanceNetworkMock.calls.Contains('https:'+$fixture.plan.publicOrigin+'/health/ready')) ($fixture.receipt.serviceName+' matching network starts only selected instance and requires HTTPS ready')
 Assert-NetworkTest ($script:instanceNetworkMock.calls.Contains("query:Name='"+$fixture.receipt.serviceName+"'")) ($fixture.receipt.serviceName+' validates SCM entry before start')
 $script:instanceNetworkMock.calls.Clear();$context.serviceWasRunning=$true
 Start-RcNetworkExisting $context
 Assert-NetworkTest (@($script:instanceNetworkMock.calls|Where-Object{$_.StartsWith('start:')}).Count-eq0) ($fixture.receipt.serviceName+' already running still verifies without restarting')
 $script:instanceNetworkMock.calls.Clear();$script:instanceNetworkMock.badBinary=$true
 Assert-InstanceNetworkRejected {Start-RcNetworkExisting $context} 'network_preflight_state_changed' ($fixture.receipt.serviceName+' refuses changed SCM executable')
 Assert-NetworkTest (@($script:instanceNetworkMock.calls|Where-Object{$_.StartsWith('start:')}).Count-eq0) ($fixture.receipt.serviceName+' preflight mismatch causes no start')
 $script:instanceNetworkMock.calls.Clear();$script:instanceNetworkMock.badBinary=$false;$script:instanceNetworkMock.ready=$false;$script:instanceNetworkMock.state='Stopped';$context.serviceWasRunning=$false
 Assert-InstanceNetworkRejected {Start-RcNetworkExisting $context} 'network_service_start_failed' ($fixture.receipt.serviceName+' cannot report readiness on wrong schema and stopped service')
 Assert-NetworkTest ($script:instanceNetworkMock.calls.Contains('stop:'+$fixture.receipt.serviceName)) ($fixture.receipt.serviceName+' failed attempted start preserves initially stopped state')
}

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

# The parent launcher rejects any child stderr. Reproduce actual redirected
# WinPS progress serialization, then exercise the exact entry-point assignment.
function Invoke-InstanceNetworkStreamFixture([string]$Body){
 $info=New-Object Diagnostics.ProcessStartInfo
 $info.FileName=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
 $info.Arguments='-NoProfile -NonInteractive -EncodedCommand '+[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Body))
 $info.UseShellExecute=$false;$info.CreateNoWindow=$true;$info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
 $process=New-Object Diagnostics.Process;$process.StartInfo=$info
 try{
  $null=$process.Start();$stdout=$process.StandardOutput.ReadToEndAsync();$stderr=$process.StandardError.ReadToEndAsync()
  if(-not$process.WaitForExit(20000)){$process.Kill();throw 'instance_network_stream_fixture_timeout'}
  $process.WaitForExit()
  return @{exitCode=$process.ExitCode;stdout=$stdout.Result;stderr=$stderr.Result}
 }finally{$process.Dispose()}
}
$tokens=$null;$parseErrors=$null;$engineAst=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$parseErrors)
$progressStatements=@($engineAst.EndBlock.Statements|Where-Object{$_-is[Management.Automation.Language.AssignmentStatementAst]-and$_.Left.Extent.Text-ceq'$ProgressPreference'})
Assert-NetworkTest ($progressStatements.Count-eq1-and$progressStatements[0].Right.Extent.Text-ceq"'SilentlyContinue'") 'Execution entry suppresses progress without relaxing error handling'
$streamBody='Write-Progress -Activity ''RackClick isolated stream fixture'' -Status ''fixture''; [ordered]@{valid=$true;code=''stream_fixture''}|ConvertTo-Json -Compress'
$negative=Invoke-InstanceNetworkStreamFixture ('$ProgressPreference=''Continue''; '+$streamBody)
Assert-NetworkTest ($negative.exitCode-eq0-and$negative.stderr.Contains('#< CLIXML')-and$negative.stderr.Contains('S="progress"')) 'Negative control reproduces native WinPS CLIXML progress on stderr'
$positive=Invoke-InstanceNetworkStreamFixture ($progressStatements[0].Extent.Text+'; '+$streamBody)
$streamResult=$positive.stdout|ConvertFrom-Json
Assert-NetworkTest ($positive.exitCode-eq0-and$positive.stderr-ceq''-and$streamResult.valid-and$streamResult.code-ceq'stream_fixture') 'Actual entry preference preserves JSON stdout and empty redirected stderr'
$sourceLiteral="'"+([IO.Path]::GetFullPath($source)).Replace("'","''")+"'"
$importOnly=Invoke-InstanceNetworkStreamFixture ('$ProgressPreference=''Continue''; . '+$sourceLiteral+' -FunctionsOnly; [ordered]@{progress=[string]$ProgressPreference}|ConvertTo-Json -Compress')
Assert-NetworkTest ($importOnly.exitCode-eq0-and($importOnly.stdout|ConvertFrom-Json).progress-ceq'Continue') 'FunctionsOnly import preserves caller progress preference'
$invalidInput=Invoke-InstanceNetworkStreamFixture ('& '+$sourceLiteral+' -InstallationId ''invalid-fixture-identity''; exit $LASTEXITCODE')
$invalidResult=$invalidInput.stdout|ConvertFrom-Json
Assert-NetworkTest ($invalidInput.exitCode-eq2-and$invalidInput.stderr-ceq''-and-not$invalidResult.valid-and$invalidResult.code-cin@('network_installation_not_supported','network_elevated_winps51_x64_required')) 'Actual engine preflight failure emits only JSON stdout and no stderr'
$result=[ordered]@{schemaVersion=1;valid=$true;passed=$checks.Count;checks=@($checks);environment='Windows PowerShell 5.1; isolated original/restored metadata and fault-injected callbacks';privilegedOperationsExecuted=0;authenticationExecuted=0;databaseOperationsExecuted=0}
if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 6 -Compress
