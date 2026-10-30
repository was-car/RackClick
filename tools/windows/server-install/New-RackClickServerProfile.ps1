#requires -Version 5.1
[CmdletBinding()]
param([string]$InstallationPath='',[string]$ExpectedInstallationSha256='',[string]$DestinationPath='',
      [string]$PublicOrigin='',[string]$BindAddress='',[string]$PfxPath='',[string]$RootCertificatePath='',[switch]$EnableMfa)
$serverProfileInputs=@{installation=$InstallationPath;sha=$ExpectedInstallationSha256;destination=$DestinationPath;origin=$PublicOrigin;bind=$BindAddress;pfx=$PfxPath;ca=$RootCertificatePath;mfa=[bool]$EnableMfa}
. (Join-Path $PSScriptRoot 'RackClick.ServerRuntime.ps1')
$report=[ordered]@{valid=$false;exitCode=2;code='server_profile_failed';manifestPath='';manifestSha256='';publicOrigin='';rootCertificatePath='';certificateExpiresUtc='';mutableDirectoryPaths=@();mutableFilePaths=@()}
$profile=$null;$certificate=$null;$ca=$null;$rsa=$null;$caRsa=$null;$unsigned=$null;$lock=$null
try {
    $input=$serverProfileInputs
    $installation=Get-StageLocalPath $input.installation;$root=Get-StageLocalPath $input.destination
    if ($root -cne (Join-Path $installation 'runtime') -or [IO.Directory]::Exists($root) -or [IO.File]::Exists($root)) {Stop-ServerCheck 'server_profile_destination_invalid'}
    if ($input.sha -cnotmatch '^[a-fA-F0-9]{64}$') {Stop-ServerCheck 'server_installation_reference_required'}
    $receiptPath=Join-Path $installation 'installation.json';Assert-BackupPrivateAcl $receiptPath
    $lock=[IO.File]::Open($receiptPath,'Open','Read','Read')
    if ((Get-RuntimeConfigDigest $receiptPath) -cne $input.sha.ToLowerInvariant()) {Stop-ServerCheck 'server_installation_hash_mismatch'}
    $receipt=Read-DeploymentJson $lock 'server_installation_invalid'
    if ($receipt.kind -cne 'RackClickPrivateInstallation' -or $receipt.state -cne 'prepared' -or $receipt.rootPath -cne $installation) {Stop-ServerCheck 'server_installation_not_prepared'}
    $mfaDefinition=$null
    if ($input.mfa) {
        $windowsInstallationId=[IO.Path]::GetFileName([IO.Path]::GetDirectoryName($installation))
        $mfaDefinition=@{enabled=$true;instancesRoot=('C:\ProgramData\RackClick\Instances\'+$windowsInstallationId+'\security');installationId=$windowsInstallationId}
        $mfaCandidate=[pscustomobject]@{schemaVersion=2;installationPath=$installation;mfa=[pscustomobject]$mfaDefinition}
        $null=Get-ServerMfaProfile -Manifest $mfaCandidate -InstallationId $windowsInstallationId
    }
    $origin=Get-ServerOrigin $input.origin $input.bind
    $deployment=Read-RackClickPrivateDeployment (Join-Path $installation 'deployment') $receipt.deploymentSha256 -Maintenance
    try {
        if ($deployment.instance.httpPort -ne $origin.port -or [IO.File]::Exists((Join-Path $deployment.instance.pgData 'postmaster.pid'))) {Stop-ServerCheck 'server_instance_not_stopped'}
        $instanceLock=[IO.File]::Open($deployment.instance.lockPath,'OpenOrCreate','ReadWrite','None')
        $instanceLock.Dispose()
    } finally {Close-RackClickPrivateDeployment $deployment}
    $null=New-BackupPrivateDirectory $root
    foreach ($directory in @('control','logs','temp','backups')) {$null=New-BackupPrivateDirectory (Join-Path $root $directory)}
    $password=New-InstancePassword
    if ($input.pfx.Length -gt 0) {
        $pfx=Get-StageLocalPath $input.pfx;$caPath=Get-StageLocalPath $input.ca
        Assert-BackupNoReparse $pfx;Assert-BackupNoReparse $caPath
        $secure=Read-Host 'Password del certificado PFX (no se mostrara)' -AsSecureString
        try {$certificate=New-Object Security.Cryptography.X509Certificates.X509Certificate2($pfx,$secure,([Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet -bor [Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable))} finally {$secure.Dispose()}
        $ca=New-Object Security.Cryptography.X509Certificates.X509Certificate2($caPath)
        $bc=@($ca.Extensions|Where-Object {$_.Oid.Value -eq '2.5.29.19'})
        if ($bc.Count -ne 1 -or -not (New-Object Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($bc[0],$bc[0].Critical)).CertificateAuthority) {Stop-ServerCheck 'server_root_certificate_invalid'}
    } else {
        if ($input.ca.Length -gt 0) {Stop-ServerCheck 'server_pfx_required'}
        $caRsa=New-Object Security.Cryptography.RSACng(3072)
        $caRequest=New-Object Security.Cryptography.X509Certificates.CertificateRequest((New-Object Security.Cryptography.X509Certificates.X500DistinguishedName('CN=RackClick Private CA '+[guid]::NewGuid().ToString('N'))),$caRsa,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)
        $caRequest.CertificateExtensions.Add((New-Object Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($true,$true,0,$true)))
        $caRequest.CertificateExtensions.Add((New-Object Security.Cryptography.X509Certificates.X509KeyUsageExtension([Security.Cryptography.X509Certificates.X509KeyUsageFlags]6,$true)))
        $now=[DateTimeOffset]::UtcNow;$ca=$caRequest.CreateSelfSigned($now.AddMinutes(-5),$now.AddDays(91))
        $rsa=New-Object Security.Cryptography.RSACng(3072)
        $request=New-Object Security.Cryptography.X509Certificates.CertificateRequest((New-Object Security.Cryptography.X509Certificates.X500DistinguishedName('CN=RackClick Server')),$rsa,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)
        $request.CertificateExtensions.Add((New-Object Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($false,$false,0,$true)))
        $request.CertificateExtensions.Add((New-Object Security.Cryptography.X509Certificates.X509KeyUsageExtension([Security.Cryptography.X509Certificates.X509KeyUsageFlags]160,$true)))
        $oids=New-Object Security.Cryptography.OidCollection;$null=$oids.Add((New-Object Security.Cryptography.Oid('1.3.6.1.5.5.7.3.1')))
        $request.CertificateExtensions.Add((New-Object Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension($oids,$false)))
        $san=New-Object Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder;$ip=$null
        if ([Net.IPAddress]::TryParse($origin.host,[ref]$ip)) {$san.AddIpAddress($ip)} else {$san.AddDnsName($origin.host)}
        $request.CertificateExtensions.Add($san.Build($false))
        $serial=New-Object byte[] 16;$rng=[Security.Cryptography.RandomNumberGenerator]::Create();try {$rng.GetBytes($serial)} finally {$rng.Dispose()};$serial[0]=$serial[0] -band 127;$serial[0]=$serial[0] -bor 1
        $unsigned=$request.Create($ca,$now.AddMinutes(-5),$now.AddDays(90),$serial)
        $certificate=[Security.Cryptography.X509Certificates.RSACertificateExtensions]::CopyWithPrivateKey($unsigned,$rsa)
    }
    $metadata=Assert-ServerCertificate $certificate $origin.host
    Write-HttpsNewBytes (Join-Path $root 'server.pfx') ($certificate.Export([Security.Cryptography.X509Certificates.X509ContentType]::Pfx,$password))
    Write-HttpsNewBytes (Join-Path $root 'server.cer') $certificate.RawData
    Write-HttpsNewBytes (Join-Path $root 'RootCA.cer') $ca.RawData
    Write-HttpsNewBytes (Join-Path $root 'tls-password.txt') ([Text.Encoding]::UTF8.GetBytes($password))
    $files=[ordered]@{};foreach ($name in @('RootCA.cer','server.cer','server.pfx','tls-password.txt')) {$files[$name]=Get-RuntimeConfigDigest (Join-Path $root $name)}
    $manifest=[ordered]@{schemaVersion=1;profileKind='RackClickProductionServer';profileId=[guid]::NewGuid().ToString('D');installationPath=$installation;installationSha256=$input.sha.ToLowerInvariant();deploymentPath=(Join-Path $installation 'deployment');deploymentSha256=$receipt.deploymentSha256;expectedWindowsSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value;publicOrigin=$origin.origin;bindAddress=$origin.bind;runtimeRoot=$root;createdUtc=[DateTime]::UtcNow.ToString('o');certificate=@{certificateSha256=$metadata.sha256;thumbprint=$metadata.thumbprint;expiresUtc=$metadata.expiresUtc;files=$files}}
    if ($null -ne $mfaDefinition) {$manifest.schemaVersion=2;$manifest.mfa=$mfaDefinition}
    $manifestPath=Join-Path $root 'server-profile.json';Write-HttpsNewBytes $manifestPath ([Text.Encoding]::UTF8.GetBytes(($manifest|ConvertTo-Json -Depth 6 -Compress)))
    $hash=Get-RuntimeConfigDigest $manifestPath;$profile=Read-ServerProfile $manifestPath $hash
    $report.valid=$true;$report.exitCode=0;$report.code='server_profile_prepared';$report.manifestPath=$manifestPath;$report.manifestSha256=$hash;$report.publicOrigin=$origin.origin;$report.rootCertificatePath=Join-Path $root 'RootCA.cer';$report.certificateExpiresUtc=$metadata.expiresUtc
    $report.mutableDirectoryPaths=@((Join-Path $installation 'deployment\instance\pgdata'),(Join-Path $installation 'deployment\instance\logs'))+@('control','logs','temp','backups'|ForEach-Object {Join-Path $root $_})
    $report.mutableFilePaths=@((Join-Path $installation 'deployment\instance\instance.lock'))
} catch {
    foreach ($pair in @(@('serverCode','serverExit'),@('deploymentCode','deploymentExit'),@('instanceCode','instanceExit'),@('stageCode','stageExit'),@('code','exitCode'))) {if ($_.Exception.Data.Contains($pair[0])) {$report.code=$_.Exception.Data[$pair[0]];$report.exitCode=[int]$_.Exception.Data[$pair[1]];break}}
} finally {
    Close-ServerProfile $profile
    foreach ($item in @($certificate,$ca,$rsa,$caRsa,$unsigned,$lock)) {if ($null -ne $item) {$item.Dispose()}}
}
$report|ConvertTo-Json -Compress
exit $report.exitCode
