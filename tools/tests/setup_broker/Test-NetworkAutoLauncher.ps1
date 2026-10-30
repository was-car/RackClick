#requires -Version 5.1
param([string]$WorkspaceRoot=([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))))
$ErrorActionPreference='Stop'
. (Join-Path $WorkspaceRoot 'tools\windows\server-install\Start-RackClickHere.ps1') -FunctionsOnly
$script:checks=0
function Check($Value,[string]$Name){if(-not$Value){throw ('Check failed: '+$Name)};$script:checks++}
function Reject([scriptblock]$Action,[string]$Code){try{& $Action;throw 'expected rejection'}catch{Check ($_.Exception.Message-ceq$Code) $Code}}
$id='11111111-2222-4333-8444-555555555555';$base='C:\ProgramData\RackClick\Instances\'+$id
function Fixture([int]$Port){
    $name=if($Port-eq5444){'RackClick-Recovery-1234abcd'}else{'RackClick'}
    $receipt=[pscustomobject]@{schemaVersion=1;installationId=$id;managementPath=($base+'\management');instancePath=($base+'\instance');codeRoot=('C:\Program Files\RackClick\'+$id);serviceName=$name;publicOrigin=('https://192.168.250.78:'+$Port)}
    $service=[pscustomobject]@{Name=$name;State='Stopped';PathName=('"'+$base+'\instance\content\dependencies\dotnet\dotnet.exe" "C:\Program Files\RackClick\'+$id+'\service\RackClick.WindowsService.dll" --config "'+$base+'\instance\service-config.json"')}
    return @{receipt=$receipt;service=$service}
}
$original=Fixture 5443;$restored=Fixture 5444
$a=ConvertTo-RcHereCandidate $original.service $original.receipt;$b=ConvertTo-RcHereCandidate $restored.service $restored.receipt
Check ($a.httpsPort-eq5443-and$a.postgresPort-eq55441-and-not$a.restored) 'original port pair'
Check ($b.httpsPort-eq5444-and$b.postgresPort-eq55442-and$b.restored) 'restored port pair'
$bad=Fixture 5444;$bad.receipt.installationId='INVALID';Reject {ConvertTo-RcHereCandidate $bad.service $bad.receipt} 'here_receipt_invalid'
$bad=Fixture 5444;$bad.service.Name='RackClick';Reject {ConvertTo-RcHereCandidate $bad.service $bad.receipt} 'here_receipt_invalid'
$bad=Fixture 5444;$bad.receipt.publicOrigin='http://192.168.250.78:5444';Reject {ConvertTo-RcHereCandidate $bad.service $bad.receipt} 'here_receipt_invalid'
$bad=Fixture 5444;$bad.receipt.publicOrigin='https://192.168.250.78:5445';Reject {ConvertTo-RcHereCandidate $bad.service $bad.receipt} 'here_receipt_invalid'
$bad=Fixture 5444;$bad.service.PathName=$bad.service.PathName.Replace($id,'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee');Reject {ConvertTo-RcHereCandidate $bad.service $bad.receipt} 'here_service_invalid'
$bad=Fixture 5444;$bad.service.State='Start Pending';Reject {ConvertTo-RcHereCandidate $bad.service $bad.receipt} 'here_service_invalid'
$bad=Fixture 5444;$bad.receipt.publicOrigin='https://user:password@example.invalid:5444';Reject {ConvertTo-RcHereCandidate $bad.service $bad.receipt} 'here_receipt_invalid'
$bad=Fixture 5444;$bad.receipt.managementPath='C:\other';Reject {ConvertTo-RcHereCandidate $bad.service $bad.receipt} 'here_receipt_invalid'
$addresses=@(
 [pscustomobject]@{IPAddress='192.168.178.141';AddressState='Preferred';InterfaceIndex=7},
 [pscustomobject]@{IPAddress='192.168.250.78';AddressState='Preferred';InterfaceIndex=8},
 [pscustomobject]@{IPAddress='192.168.250.79';AddressState='Tentative';InterfaceIndex=8},
 [pscustomobject]@{IPAddress='127.0.0.1';AddressState='Preferred';InterfaceIndex=9},
 [pscustomobject]@{IPAddress='10.1.2.3';AddressState='Preferred';InterfaceIndex=7})
$adapters=@([pscustomobject]@{InterfaceIndex=7;Status='Up'},[pscustomobject]@{InterfaceIndex=8;Status='Up'})
$routes=@([pscustomobject]@{InterfaceIndex=7;DestinationPrefix='0.0.0.0/0';RouteMetric=1},[pscustomobject]@{InterfaceIndex=8;DestinationPrefix='0.0.0.0/0';RouteMetric=20})
$interfaces=@([pscustomobject]@{InterfaceIndex=7;InterfaceMetric=1},[pscustomobject]@{InterfaceIndex=8;InterfaceMetric=10})
$networks=@(Select-RcHereNetworks $addresses $adapters $routes $interfaces)
Check ($networks.Count-eq2) 'only authorized preferred up IPv4s'
Check ($networks[0].ip-ceq'192.168.178.141'-and$networks[0].subnet-ceq'192.168.178.0/24') 'home route auto'
Check ($networks[1].subnet-ceq'192.168.250.0/24') 'work subnet bounded'
Check (@(Select-RcHereNetworks @($addresses[1]) $adapters @() @()).Count-eq1) 'network without default route still detected'
Check (@(Select-RcHereNetworks $addresses @() $routes $interfaces).Count-eq0) 'down adapters rejected'
Check (@(Select-RcHereNetworks @($addresses[0],$addresses[0]) $adapters $routes $interfaces).Count-eq1) 'addresses deduplicated'
$invalidAddress=[pscustomobject]@{IPAddress='192.168.178.255';AddressState='Preferred';InterfaceIndex=7}
Check (@(Select-RcHereNetworks @($invalidAddress) $adapters $routes $interfaces).Count-eq0) 'broadcast rejected'
$network=$networks[0]
$report=[pscustomobject]@{schemaVersion=1;valid=$true;success=$true;exitCode=0;code='network_existing_verified';readiness='ready';httpsPort=5444;postgresPort=55442;installationId=$id;publicOrigin='https://192.168.178.141:5444'}
Check ((Assert-RcHereResult $report 0 $b $network).success) 'already configured is verified'
$report.code='network_already_configured';Reject {Assert-RcHereResult $report 0 $b $network} 'here_engine_result_invalid'
$report.code='network_change_verified';$report.publicOrigin='https://192.168.178.141:5443';Reject {Assert-RcHereResult $report 0 $b $network} 'here_engine_result_invalid'
$report.publicOrigin='https://192.168.178.141:5444';$report.installationId='aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee';Reject {Assert-RcHereResult $report 0 $b $network} 'here_engine_result_invalid'
$report.installationId=$id;$report.success=$false;Reject {Assert-RcHereResult $report 0 $b $network} 'here_engine_result_invalid'
$report.success=$true;$report.readiness='not_checked';Reject {Assert-RcHereResult $report 0 $b $network} 'here_engine_result_invalid'
$report.readiness='ready';$report.postgresPort=55441;Reject {Assert-RcHereResult $report 0 $b $network} 'here_engine_result_invalid'
Reject {ConvertTo-RcHereArgument "bad`nvalue"} 'here_argument_invalid'
Check ((ConvertTo-RcHereArgument 'C:\test path\file.ps1')-ceq'"C:\test path\file.ps1"') 'child quoting spaces'
$temporary=Join-Path $WorkspaceRoot ('.local\network-launcher-fixture-'+[guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path $temporary
$fakeEngine=Join-Path $temporary 'fake-engine.ps1'
$fakeText=@'
param($InstallationId,$HttpsPort,$PostgresPort,$BindAddress,$AllowedSubnet,[switch]$EnsureRunning)
@{schemaVersion=1;valid=$true;success=$true;exitCode=0;code='network_existing_verified';readiness='ready';httpsPort=[int]$HttpsPort;postgresPort=[int]$PostgresPort;installationId=$InstallationId;publicOrigin=('https://'+$BindAddress+':'+$HttpsPort)}|ConvertTo-Json -Compress
exit 0
'@
[IO.File]::WriteAllText($fakeEngine,$fakeText,(New-Object Text.UTF8Encoding($false)))
$fakeHash=(Get-FileHash -LiteralPath $fakeEngine -Algorithm SHA256).Hash.ToLowerInvariant()
$native=Invoke-RcHereEngine $b $network $fakeEngine $fakeHash $null
Check ($native.code-ceq'network_existing_verified'-and$native.publicOrigin-ceq'https://192.168.178.141:5444') 'real WinPS child exit and result captured'
Reject {Invoke-RcHereEngine $b $network $fakeEngine ('0'*64) $null} 'here_engine_hash_mismatch'
[IO.File]::WriteAllText($fakeEngine,($fakeText.Replace("readiness='ready'","readiness='not_checked'")),(New-Object Text.UTF8Encoding($false)))
$fakeHash=(Get-FileHash -LiteralPath $fakeEngine -Algorithm SHA256).Hash.ToLowerInvariant()
Reject {Invoke-RcHereEngine $b $network $fakeEngine $fakeHash $null} 'here_engine_result_invalid'
$instanceFixture=Join-Path $temporary 'instances';$publicFixture=Join-Path $temporary 'desktop';$null=New-Item -ItemType Directory -Path (Join-Path (Join-Path $instanceFixture $id) 'management'),$publicFixture -Force
$certificateKey=New-Object Security.Cryptography.RSACng(2048);$certificateRequest=New-Object Security.Cryptography.X509Certificates.CertificateRequest('CN=RackClick synthetic public export',$certificateKey,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)
$certificate=$certificateRequest.CreateSelfSigned([DateTimeOffset]::UtcNow.AddMinutes(-5),[DateTimeOffset]::UtcNow.AddDays(1))
try{
    $fixtureManagement=Join-Path (Join-Path $instanceFixture $id) 'management';$fixturePublicCa=Join-Path $fixtureManagement 'RootCA.cer'
    [IO.File]::WriteAllBytes($fixturePublicCa,$certificate.Export([Security.Cryptography.X509Certificates.X509ContentType]::Cert))
    [IO.File]::WriteAllText((Join-Path $fixtureManagement 'server-installation.json'),(@{installationId=$id;serviceName=$b.serviceName;trustedCaThumbprint=$certificate.Thumbprint}|ConvertTo-Json -Compress),(New-Object Text.UTF8Encoding($false)))
    function Get-Acl {param($LiteralPath)$acl=New-Object PSObject;$acl|Add-Member ScriptMethod GetOwner {param($kind)New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')};return $acl}
    $publicExport=Export-RcHerePublicCertificate $b $instanceFixture $publicFixture
    $readPublic=New-Object Security.Cryptography.X509Certificates.X509Certificate2($publicExport)
    try{Check (-not$readPublic.HasPrivateKey-and$readPublic.Thumbprint-ceq$certificate.Thumbprint) 'public CER only, no private key'}finally{$readPublic.Dispose()}
    Check ((Export-RcHerePublicCertificate $b $instanceFixture $publicFixture)-ceq$publicExport) 'same public export reused without overwrite'
    [IO.File]::WriteAllBytes($fixturePublicCa,$certificate.Export([Security.Cryptography.X509Certificates.X509ContentType]::Pkcs12,''))
    Reject {Export-RcHerePublicCertificate $b $instanceFixture $publicFixture} 'here_public_certificate_invalid'
}finally{Remove-Item -LiteralPath Function:\Get-Acl;$certificate.Dispose();$certificateKey.Dispose()}
$report=[ordered]@{schemaVersion=1;passed=$checks;failed=0;scope='metadata fixtures, two real synthetic WinPS child processes and public certificate export; ACL mocked; no SCM, IP, service, TLS store or database mutation'}
$report|ConvertTo-Json -Compress
