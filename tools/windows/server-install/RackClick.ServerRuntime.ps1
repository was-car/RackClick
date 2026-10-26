#requires -Version 5.1
# Production LAN profile. Imports do not start processes or alter trust stores.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$script:ServerOperatorsRoot=Split-Path $PSScriptRoot -Parent
. (Join-Path $script:ServerOperatorsRoot 'RackClick.Deployment.ps1')

function Stop-ServerCheck {
    param([string]$Code,[int]$ExitCode=2)
    $failure=New-Object InvalidOperationException($Code)
    $failure.Data['serverCode']=$Code;$failure.Data['serverExit']=$ExitCode
    throw $failure
}
function Get-ServerOrigin {
    param([string]$Origin,[string]$BindAddress,[switch]$Maintenance)
    $uri=$null;$ip=$null
    if (-not [Uri]::TryCreate($Origin,[UriKind]::Absolute,[ref]$uri) -or $uri.Scheme -cne 'https' -or
        $uri.UserInfo -ne '' -or $uri.AbsolutePath -ne '/' -or $uri.Query -ne '' -or $uri.Fragment -ne '' -or
        $uri.Port -lt 1024 -or $uri.Port -gt 65535 -or $Origin -cne $uri.GetLeftPart([UriPartial]::Authority) -or
        $uri.HostNameType -notin @([UriHostNameType]::Dns,[UriHostNameType]::IPv4) -or $uri.Host -eq 'localhost') { Stop-ServerCheck 'server_origin_invalid' }
    if (-not [Net.IPAddress]::TryParse($BindAddress,[ref]$ip) -or $ip.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or
        $BindAddress -cne $ip.ToString() -or [Net.IPAddress]::IsLoopback($ip) -or $BindAddress -eq '0.0.0.0') { Stop-ServerCheck 'server_bind_invalid' }
    $local=@([Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces() | Where-Object {$_.OperationalStatus -eq 'Up'} | ForEach-Object {$_.GetIPProperties().UnicastAddresses} | ForEach-Object {$_.Address.ToString()})
    if (-not $Maintenance -and $BindAddress -notin $local) { Stop-ServerCheck 'server_bind_not_local' }
    if ($uri.HostNameType -eq [UriHostNameType]::IPv4 -and $uri.Host -cne $BindAddress) { Stop-ServerCheck 'server_public_bind_mismatch' }
    if (-not $Maintenance -and $uri.HostNameType -eq [UriHostNameType]::Dns -and $BindAddress -notin @([Net.Dns]::GetHostAddresses($uri.DnsSafeHost)|ForEach-Object {$_.ToString()})) { Stop-ServerCheck 'server_dns_bind_mismatch' }
    return @{host=$uri.DnsSafeHost;port=$uri.Port;origin=$Origin;bind=$BindAddress}
}
function Assert-ServerCertificate {
    param($Certificate,[string]$HostName,[switch]$Maintenance)
    if (-not $Certificate.HasPrivateKey -or (-not $Maintenance -and ($Certificate.NotBefore.ToUniversalTime() -gt [DateTime]::UtcNow -or
        $Certificate.NotAfter.ToUniversalTime() -le [DateTime]::UtcNow.AddDays(1)))) { Stop-ServerCheck 'server_certificate_invalid' }
    $rsa=[Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPublicKey($Certificate)
    try {if ($null -eq $rsa -or $rsa.KeySize -lt 3072) {Stop-ServerCheck 'server_certificate_key_invalid'}} finally {if ($null -ne $rsa) {$rsa.Dispose()}}
    $san=@($Certificate.Extensions|Where-Object {$_.Oid.Value -eq '2.5.29.17'})
    $eku=@($Certificate.Extensions|Where-Object {$_.Oid.Value -eq '2.5.29.37'})
    $bc=@($Certificate.Extensions|Where-Object {$_.Oid.Value -eq '2.5.29.19'})
    if ($san.Count -ne 1 -or $eku.Count -ne 1 -or $bc.Count -ne 1) {Stop-ServerCheck 'server_certificate_extensions_invalid'}
    $constraints=New-Object Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($bc[0],$bc[0].Critical)
    $usage=New-Object Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension($eku[0],$eku[0].Critical)
    if ($constraints.CertificateAuthority -or '1.3.6.1.5.5.7.3.1' -notin @($usage.EnhancedKeyUsages|ForEach-Object {$_.Value})) {Stop-ServerCheck 'server_certificate_extensions_invalid'}
    # Match a SAN using DER tags, never localized extension.Format().
    $bytes=$san[0].RawData;$outer=Get-HttpsDerElement $bytes 0 48;$offset=$outer.content;$matched=$false;$ip=$null
    $isIp=[Net.IPAddress]::TryParse($HostName,[ref]$ip)
    while ($offset -lt $bytes.Length) {
        $entry=Get-HttpsDerElement $bytes $offset ([int]$bytes[$offset])
        $value=New-Object byte[] $entry.length;[Array]::Copy($bytes,$entry.content,$value,0,$value.Length)
        if ($isIp -and $bytes[$offset] -eq 135 -and [Convert]::ToBase64String($value) -ceq [Convert]::ToBase64String($ip.GetAddressBytes())) {$matched=$true}
        if (-not $isIp -and $bytes[$offset] -eq 130 -and [Text.Encoding]::ASCII.GetString($value).Equals($HostName,[StringComparison]::OrdinalIgnoreCase)) {$matched=$true}
        $offset+=$entry.total
    }
    if (-not $matched) {Stop-ServerCheck 'server_certificate_san_mismatch'}
    return @{sha256=(Get-HttpsBytesSha256 $Certificate.RawData);thumbprint=$Certificate.Thumbprint;expiresUtc=$Certificate.NotAfter.ToUniversalTime().ToString('o')}
}
function Read-ServerProfile {
    param([string]$ManifestPath,[string]$ExpectedManifestSha256,[switch]$Maintenance)
    $locks=@();$deployment=$null
    try {
        $path=Get-StageLocalPath $ManifestPath
        if ($ExpectedManifestSha256 -cnotmatch '^[a-fA-F0-9]{64}$') {Stop-ServerCheck 'server_manifest_reference_required'}
        Assert-BackupPrivateAcl $path
        $locks += [IO.File]::Open($path,'Open','Read','Read')
        if ((Get-RuntimeConfigDigest $path) -cne $ExpectedManifestSha256.ToLowerInvariant()) {Stop-ServerCheck 'server_manifest_hash_mismatch'}
        $m=Read-DeploymentJson $locks[0] 'server_manifest_invalid'
        if ((($m.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'bindAddress,certificate,createdUtc,deploymentPath,deploymentSha256,expectedWindowsSid,installationPath,installationSha256,profileId,profileKind,publicOrigin,runtimeRoot,schemaVersion' -or
            $m.schemaVersion -ne 1 -or $m.profileKind -cne 'RackClickProductionServer' -or
            $m.profileId -cnotmatch '^[a-f0-9-]{36}$' -or $m.expectedWindowsSid -cne [Security.Principal.WindowsIdentity]::GetCurrent().User.Value) {Stop-ServerCheck 'server_manifest_invalid'}
        $root=[IO.Path]::GetDirectoryName($path)
        if ($m.runtimeRoot -cne $root -or $path -cne (Join-Path $root 'server-profile.json') -or
            $m.deploymentPath -cne (Join-Path $m.installationPath 'deployment')) {Stop-ServerCheck 'server_manifest_binding_invalid'}
        $origin=Get-ServerOrigin $m.publicOrigin $m.bindAddress -Maintenance:$Maintenance
        foreach ($name in @('installationSha256','deploymentSha256')) {if ($m.$name -cnotmatch '^[a-f0-9]{64}$') {Stop-ServerCheck 'server_manifest_invalid'}}
        $receiptPath=Join-Path $m.installationPath 'installation.json';Assert-BackupPrivateAcl $receiptPath
        $locks += [IO.File]::Open($receiptPath,'Open','Read','Read')
        if ((Get-RuntimeConfigDigest $receiptPath) -cne $m.installationSha256) {Stop-ServerCheck 'server_installation_hash_mismatch'}
        $receipt=Read-DeploymentJson $locks[1] 'server_installation_invalid'
        $statePath=Join-Path $m.installationPath 'installation-state.json';Assert-BackupPrivateAcl $statePath
        $locks += [IO.File]::Open($statePath,'Open','Read','Read');$state=Read-DeploymentJson $locks[2] 'server_installation_state_invalid'
        if ($receipt.kind -cne 'RackClickPrivateInstallation' -or $receipt.state -cne 'prepared' -or $receipt.rootPath -cne $m.installationPath -or
            $receipt.deploymentSha256 -cne $m.deploymentSha256 -or $state.status -cne 'prepared' -or $state.code -cne 'installation_prepared' -or $state.installationId -cne $receipt.id) {Stop-ServerCheck 'server_installation_not_prepared'}
        $deployment=Read-RackClickPrivateDeployment $m.deploymentPath $m.deploymentSha256 -Maintenance
        if ($origin.port -ne $deployment.instance.httpPort -or $receipt.deploymentId -cne $deployment.id) {Stop-ServerCheck 'server_deployment_binding_invalid'}
        if ((($m.certificate.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'certificateSha256,expiresUtc,files,thumbprint') {Stop-ServerCheck 'server_certificate_manifest_invalid'}
        if ((($m.certificate.files.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'RootCA.cer,server.cer,server.pfx,tls-password.txt') {Stop-ServerCheck 'server_certificate_manifest_invalid'}
        foreach ($name in @('RootCA.cer','server.cer','server.pfx','tls-password.txt')) {
            $file=Join-Path $root $name;Assert-BackupPrivateAcl $file;$locks += [IO.File]::Open($file,'Open','Read','Read')
            if ((Get-RuntimeConfigDigest $file) -cne $m.certificate.files.$name) {Stop-ServerCheck 'server_certificate_file_hash_mismatch'}
        }
        $password=[IO.File]::ReadAllText((Join-Path $root 'tls-password.txt'),[Text.Encoding]::UTF8)
        $cert=New-Object Security.Cryptography.X509Certificates.X509Certificate2((Join-Path $root 'server.pfx'),$password,[Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet)
        try {
            $metadata=Assert-ServerCertificate $cert $origin.host -Maintenance:$Maintenance
            $public=New-Object Security.Cryptography.X509Certificates.X509Certificate2((Join-Path $root 'server.cer'))
            $authority=New-Object Security.Cryptography.X509Certificates.X509Certificate2((Join-Path $root 'RootCA.cer'))
            $chain=New-Object Security.Cryptography.X509Certificates.X509Chain
            try {
                if ((Get-HttpsBytesSha256 $public.RawData) -cne $metadata.sha256) {Stop-ServerCheck 'server_public_certificate_mismatch'}
                $chain.ChainPolicy.RevocationMode=[Security.Cryptography.X509Certificates.X509RevocationMode]::NoCheck
                $chain.ChainPolicy.VerificationFlags=[Security.Cryptography.X509Certificates.X509VerificationFlags]::AllowUnknownCertificateAuthority
                if ($Maintenance) {$chain.ChainPolicy.VerificationFlags=$chain.ChainPolicy.VerificationFlags -bor [Security.Cryptography.X509Certificates.X509VerificationFlags]::IgnoreNotTimeValid}
                $chain.ChainPolicy.UrlRetrievalTimeout=[TimeSpan]::FromSeconds(1)
                $null=$chain.ChainPolicy.ExtraStore.Add($authority)
                if (-not $chain.Build($cert) -or $chain.ChainElements.Count -lt 2 -or
                    (Get-HttpsBytesSha256 $chain.ChainElements[$chain.ChainElements.Count-1].Certificate.RawData) -cne (Get-HttpsBytesSha256 $authority.RawData)) {Stop-ServerCheck 'server_certificate_chain_invalid'}
                foreach ($status in $chain.ChainStatus) {if ($Maintenance -and $status.Status -eq [Security.Cryptography.X509Certificates.X509ChainStatusFlags]::NotTimeValid) {continue};if ($status.Status -notin @([Security.Cryptography.X509Certificates.X509ChainStatusFlags]::NoError,[Security.Cryptography.X509Certificates.X509ChainStatusFlags]::UntrustedRoot)) {Stop-ServerCheck 'server_certificate_chain_invalid'}}
            } finally {$public.Dispose();$authority.Dispose();$chain.Dispose()}
        } finally {$cert.Dispose()}
        foreach ($name in @('sha256','thumbprint','expiresUtc')) {$key=if ($name -eq 'sha256') {'certificateSha256'} else {$name};if ($metadata[$name] -cne $m.certificate.$key) {Stop-ServerCheck 'server_certificate_binding_invalid'}}
        foreach ($name in @('control','logs','temp','backups')) {Assert-BackupPrivateAcl (Join-Path $root $name)}
        $deployment.instance.logRoot=Join-Path $root 'control'
        return @{manifest=$m;root=$root;origin=$origin;deployment=$deployment;instance=$deployment.instance;locks=$locks;password=$password;pfx=(Join-Path $root 'server.pfx');certificateSha256=$metadata.sha256;hash=$ExpectedManifestSha256.ToLowerInvariant()}
    } catch {Close-RackClickPrivateDeployment $deployment;foreach ($stream in $locks) {$stream.Dispose()};throw}
}
function Close-ServerProfile {
    param($Profile)
    if ($null -eq $Profile) {return}
    Close-RackClickPrivateDeployment $Profile.deployment
    foreach ($stream in $Profile.locks) {$stream.Dispose()}
}
