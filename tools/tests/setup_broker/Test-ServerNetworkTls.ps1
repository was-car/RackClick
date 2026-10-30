#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\..\windows\server-install\Set-RackClickServerNetwork.ps1') -FunctionsOnly
$checks=New-Object 'Collections.Generic.List[string]'
function Assert-TlsTest([bool]$Condition,[string]$Name){if(-not$Condition){throw ('Test failed: '+$Name)};$checks.Add($Name)}
$password='generated-test-fixture-password-not-a-real-secret'
$pwBytes=[Text.Encoding]::UTF8.GetBytes($password)
$plan=Get-RcNetworkPlan -InstallationId '606b8c29-41de-4dc0-b63d-ade836000d9e' -BindAddress '192.168.250.78' -AllowedSubnet '192.168.250.0/24' -PublicHost ''
$ctx=@{plan=$plan;entries=@(@{key='tls-password';snapshot=@{Bytes=$pwBytes}})}
$tls=New-RcNetworkTls $ctx
$server=$null;$root=$null;$chain=$null
try{
 $server=New-Object Security.Cryptography.X509Certificates.X509Certificate2($tls.data['server.pfx'],$password,([Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet))
 $root=New-Object Security.Cryptography.X509Certificates.X509Certificate2(,$tls.data['RootCA.cer'])
 Assert-TlsTest $server.HasPrivateKey 'Generated PFX retains a private key and uses the existing TLS password'
 Assert-TlsTest (-not$root.HasPrivateKey) 'Distributed CA file contains no private key'
 Assert-TlsTest ($tls.rootThumbprint-ceq$root.Thumbprint-and$tls.thumbprint-ceq$server.Thumbprint-and$tls.rootThumbprint-cne$tls.thumbprint) 'CA and server thumbprints are distinct and accurately reported'
 $rsa=[Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPublicKey($server)
 try{Assert-TlsTest ($rsa.KeySize-ge3072) 'Server uses RSA of at least 3072 bits'}finally{$rsa.Dispose()}
 $san=@($server.Extensions|Where-Object{$_.Oid.Value-ceq'2.5.29.17'})
 Assert-TlsTest ($san.Count-eq1-and([BitConverter]::ToString($san[0].RawData))-ceq'30-06-87-04-C0-A8-FA-4E') 'Certificate SAN encodes exactly the selected IPv4 address'
 $bc=@($root.Extensions|Where-Object{$_.Oid.Value-ceq'2.5.29.19'})
 $rootConstraints=New-Object Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($bc[0],$bc[0].Critical)
 Assert-TlsTest $rootConstraints.CertificateAuthority 'Generated issuer is a certificate authority'
 $leafBc=@($server.Extensions|Where-Object{$_.Oid.Value-ceq'2.5.29.19'})
 $leafConstraints=New-Object Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($leafBc[0],$leafBc[0].Critical)
 Assert-TlsTest (-not$leafConstraints.CertificateAuthority) 'Server certificate cannot act as a CA'
 $eku=@($server.Extensions|Where-Object{$_.Oid.Value-ceq'2.5.29.37'})
 $usage=New-Object Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension($eku[0],$eku[0].Critical)
 Assert-TlsTest ('1.3.6.1.5.5.7.3.1'-in@($usage.EnhancedKeyUsages|ForEach-Object{$_.Value})) 'Server authentication EKU present'
 Assert-TlsTest ($server.NotBefore.ToUniversalTime()-le[DateTime]::UtcNow-and$server.NotAfter.ToUniversalTime()-gt[DateTime]::UtcNow.AddDays(89)) 'Certificate is currently valid and lasts about 90 days'
 $chain=New-Object Security.Cryptography.X509Certificates.X509Chain
 $null=$chain.ChainPolicy.ExtraStore.Add($root)
 $chain.ChainPolicy.RevocationMode=[Security.Cryptography.X509Certificates.X509RevocationMode]::NoCheck
 $chain.ChainPolicy.VerificationFlags=[Security.Cryptography.X509Certificates.X509VerificationFlags]::AllowUnknownCertificateAuthority
 Assert-TlsTest ($chain.Build($server)-and$chain.ChainElements[$chain.ChainElements.Count-1].Certificate.Thumbprint-ceq$root.Thumbprint) 'Generated server certificate chains to generated CA without altering a trust store'
 foreach($name in @('RootCA.cer','server.cer','server.pfx')){Assert-TlsTest ($tls.files[$name]-ceq(Get-RcNetworkHash $tls.data[$name])) ('Exact hash for '+$name)}
 Assert-TlsTest ($tls.files['tls-password.txt']-ceq(Get-RcNetworkHash $pwBytes)) 'Password-file hash remains unchanged'
}finally{foreach($item in @($chain,$server,$root)){if($null-ne$item){$item.Dispose()}}}

# Native file helper runs only against a newly created user-owned test fixture.
Initialize-RcNetworkNative
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('RackClick-network-fixture-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($fixture)
$file=Join-Path $fixture 'sealed-config-fixture.json'
[IO.File]::WriteAllText($file,'original fixture bytes',(New-Object Text.UTF8Encoding($false)))
$before=[RackClickNetworkMaintenanceNative]::Snapshot($file)
$replacement=[Text.Encoding]::UTF8.GetBytes('{"fixture":"replacement"}')
[RackClickNetworkMaintenanceNative]::WriteExisting($file,$replacement)
$after=[RackClickNetworkMaintenanceNative]::Snapshot($file)
Assert-TlsTest ((Get-RcNetworkHash $after.Bytes)-ceq(Get-RcNetworkHash $replacement)-and$after.Sddl-ceq$before.Sddl) 'Native replacement preserves original file security descriptor'
[RackClickNetworkMaintenanceNative]::WriteExisting($file,$before.Bytes)
$restored=[RackClickNetworkMaintenanceNative]::Snapshot($file)
Assert-TlsTest ((Get-RcNetworkHash $restored.Bytes)-ceq(Get-RcNetworkHash $before.Bytes)-and$restored.Sddl-ceq$before.Sddl) 'Original file bytes and security descriptor can be restored'
$result=[ordered]@{schemaVersion=1;valid=$true;passed=$checks.Count;checks=@($checks);environment='Windows PowerShell 5.1; generated certificates and user-owned native file fixture';fixture=$fixture;trustStoreChanges=0;privilegedOperationsExecuted=0;serviceOperationsExecuted=0;databaseOperationsExecuted=0}
if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 6 -Compress
