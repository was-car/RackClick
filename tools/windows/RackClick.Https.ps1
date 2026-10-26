#requires -Version 5.1
# Private loopback TLS sidecar. Imports never create a certificate or touch a store.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'RackClick.Instance.ps1')

function Stop-HttpsProfileCheck {
    param([string]$Code,[int]$ExitCode=2)
    $failure=New-Object InvalidOperationException($Code)
    $failure.Data['httpsCode']=$Code; $failure.Data['httpsExit']=$ExitCode
    throw $failure
}

function Assert-HttpsProfileDisjoint {
    param([string]$Root,[hashtable]$Instance)
    foreach ($other in @($Instance.root,$Instance.stageRoot,$Instance.pgBin,[IO.Path]::GetDirectoryName($Instance.dotnet))) {
        if (Test-StageOverlap $Root $other) { Stop-HttpsProfileCheck 'https_paths_overlap' }
    }
}

function Write-HttpsNewBytes {
    param([string]$Path,[byte[]]$Bytes)
    Assert-BackupPrivateAcl ([IO.Path]::GetDirectoryName($Path))
    $stream=$null
    try {
        $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        $stream.Write($Bytes,0,$Bytes.Length);$stream.Flush($true)
    } finally { if ($null -ne $stream) { $stream.Dispose() } }
    Assert-BackupPrivateAcl $Path
}

function Get-HttpsBytesSha256 {
    param([byte[]]$Bytes)
    $digest=[Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($digest.ComputeHash($Bytes)).Replace('-','').ToLowerInvariant() }
    finally { $digest.Dispose() }
}

function Get-HttpsDerElement {
    param([byte[]]$Bytes,[int]$Offset,[int]$Tag)
    if ($Offset -lt 0 -or $Offset+2 -gt $Bytes.Length -or $Bytes[$Offset] -ne $Tag) { Stop-HttpsProfileCheck 'https_certificate_signature_invalid' }
    $cursor=$Offset+2;[long]$length=$Bytes[$Offset+1]
    if ($length -ge 128) {
        $count=[int]($length-band 127);$length=0
        if ($count -lt 1 -or $count -gt 4 -or $cursor+$count -gt $Bytes.Length -or $Bytes[$cursor] -eq 0) { Stop-HttpsProfileCheck 'https_certificate_signature_invalid' }
        for ($i=0;$i -lt $count;$i++) { $length=$length*256+$Bytes[$cursor];$cursor++ }
        if ($length -lt 128) { Stop-HttpsProfileCheck 'https_certificate_signature_invalid' }
    }
    if ($length -gt 65536 -or $cursor+$length -gt $Bytes.Length) { Stop-HttpsProfileCheck 'https_certificate_signature_invalid' }
    return @{offset=$Offset;content=$cursor;length=[int]$length;total=([int]$length+$cursor-$Offset)}
}

function Assert-HttpsCertificate {
    param([Security.Cryptography.X509Certificates.X509Certificate2]$Certificate,[string]$Id)
    $rsa=$null;$privateKey=$null
    try {
        if (-not $Certificate.HasPrivateKey -or $Certificate.Subject -cne ('CN=RackClick-Loopback-'+$Id.Replace('-','')) -or
            $Certificate.Subject -cne $Certificate.Issuer -or $Certificate.SignatureAlgorithm.Value -cne '1.2.840.113549.1.1.11') { Stop-HttpsProfileCheck 'https_certificate_invalid' }
        $now=[DateTime]::UtcNow;$before=$Certificate.NotBefore.ToUniversalTime();$after=$Certificate.NotAfter.ToUniversalTime()
        if ($before -gt $now -or $after -le $now -or ($after-$before).TotalDays -gt 7.01) { Stop-HttpsProfileCheck 'https_certificate_time_invalid' }
        $extensions=@($Certificate.Extensions)
        if ($extensions.Count -ne 4 -or ((@($extensions | ForEach-Object {$_.Oid.Value}) | Sort-Object)-join ',') -cne '2.5.29.15,2.5.29.17,2.5.29.19,2.5.29.37') { Stop-HttpsProfileCheck 'https_certificate_extensions_invalid' }
        foreach ($extension in $extensions) {
            switch ($extension.Oid.Value) {
                '2.5.29.19' {
                    $bc=New-Object Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($extension,$extension.Critical)
                    if (-not $extension.Critical -or $bc.CertificateAuthority -or $bc.HasPathLengthConstraint) { Stop-HttpsProfileCheck 'https_certificate_extensions_invalid' }
                }
                '2.5.29.15' {
                    $ku=New-Object Security.Cryptography.X509Certificates.X509KeyUsageExtension($extension,$extension.Critical)
                    if (-not $extension.Critical -or [int]$ku.KeyUsages -ne 160) { Stop-HttpsProfileCheck 'https_certificate_extensions_invalid' }
                }
                '2.5.29.37' {
                    $eku=New-Object Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension($extension,$extension.Critical)
                    if ($eku.EnhancedKeyUsages.Count -ne 1 -or $eku.EnhancedKeyUsages[0].Value -cne '1.3.6.1.5.5.7.3.1') { Stop-HttpsProfileCheck 'https_certificate_extensions_invalid' }
                }
                '2.5.29.17' {
                    # DER: SEQUENCE { DNS localhost, IPv4 127.0.0.1 }; never parse localized Format().
                    $expected=[byte[]]@(48,17,130,9,108,111,99,97,108,104,111,115,116,135,4,127,0,0,1)
                    if ([Convert]::ToBase64String($extension.RawData) -cne [Convert]::ToBase64String($expected)) { Stop-HttpsProfileCheck 'https_certificate_san_invalid' }
                }
            }
        }
        $rsa=[Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPublicKey($Certificate)
        $privateKey=[Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($Certificate)
        if ($null -eq $rsa -or $null -eq $privateKey -or $rsa.KeySize -lt 3072 -or $privateKey.KeySize -ne $rsa.KeySize) { Stop-HttpsProfileCheck 'https_certificate_key_invalid' }
        $raw=$Certificate.RawData;$outer=Get-HttpsDerElement $raw 0 48
        $tbs=Get-HttpsDerElement $raw $outer.content 48
        $algorithm=Get-HttpsDerElement $raw ($tbs.offset+$tbs.total) 48
        $signature=Get-HttpsDerElement $raw ($algorithm.offset+$algorithm.total) 3
        if ($outer.total -ne $raw.Length -or $signature.offset+$signature.total -ne $raw.Length -or $signature.length -lt 2 -or $raw[$signature.content] -ne 0) { Stop-HttpsProfileCheck 'https_certificate_signature_invalid' }
        $tbsBytes=New-Object byte[] $tbs.total;[Array]::Copy($raw,$tbs.offset,$tbsBytes,0,$tbs.total)
        $signatureBytes=New-Object byte[] ($signature.length-1);[Array]::Copy($raw,($signature.content+1),$signatureBytes,0,$signatureBytes.Length)
        if (-not $rsa.VerifyData($tbsBytes,$signatureBytes,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)) { Stop-HttpsProfileCheck 'https_certificate_signature_invalid' }
        $challenge=New-Object byte[] 32;$rng=[Security.Cryptography.RandomNumberGenerator]::Create()
        try { $rng.GetBytes($challenge) } finally { $rng.Dispose() }
        $proof=$privateKey.SignData($challenge,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)
        if (-not $rsa.VerifyData($challenge,$proof,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)) { Stop-HttpsProfileCheck 'https_certificate_key_invalid' }
        return @{sha256=(Get-HttpsBytesSha256 $raw);notBeforeUtc=$before.ToString('o');notAfterUtc=$after.ToString('o');keySize=$rsa.KeySize}
    } finally { if ($null -ne $rsa) {$rsa.Dispose()};if ($null -ne $privateKey) {$privateKey.Dispose()} }
}

function New-HttpsCertificateFiles {
    param([string]$Root,[string]$Id)
    $rsa=$null;$certificate=$null;$imported=$null
    try {
        if (-not ('Security.Cryptography.X509Certificates.CertificateRequest' -as [type]) -or -not ('Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder' -as [type])) { Stop-HttpsProfileCheck 'https_framework_api_unavailable' 1 }
        $rsa=New-Object Security.Cryptography.RSACng(3072)
        $subject=New-Object Security.Cryptography.X509Certificates.X500DistinguishedName('CN=RackClick-Loopback-'+$Id.Replace('-',''))
        $request=New-Object Security.Cryptography.X509Certificates.CertificateRequest($subject,$rsa,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)
        $request.CertificateExtensions.Add((New-Object Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($false,$false,0,$true)))
        $request.CertificateExtensions.Add((New-Object Security.Cryptography.X509Certificates.X509KeyUsageExtension([Security.Cryptography.X509Certificates.X509KeyUsageFlags]160,$true)))
        $oids=New-Object Security.Cryptography.OidCollection;$null=$oids.Add((New-Object Security.Cryptography.Oid('1.3.6.1.5.5.7.3.1')))
        $request.CertificateExtensions.Add((New-Object Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension($oids,$false)))
        $san=New-Object Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder
        $san.AddDnsName('localhost');$san.AddIpAddress([Net.IPAddress]::Loopback)
        $request.CertificateExtensions.Add($san.Build($false))
        $now=[DateTimeOffset]::UtcNow
        $certificate=$request.CreateSelfSigned($now.AddMinutes(-5),$now.AddDays(7))
        $password=New-InstancePassword
        Write-HttpsNewBytes (Join-Path $Root 'server.pfx') ($certificate.Export([Security.Cryptography.X509Certificates.X509ContentType]::Pfx,$password))
        Write-HttpsNewBytes (Join-Path $Root 'pfx-password.txt') ([Text.Encoding]::UTF8.GetBytes($password))
        $base64=[Convert]::ToBase64String($certificate.RawData,[Base64FormattingOptions]::InsertLineBreaks)
        $pem="-----BEGIN CERTIFICATE-----`n"+$base64.Replace("`r`n","`n")+"`n-----END CERTIFICATE-----`n"
        Write-HttpsNewBytes (Join-Path $Root 'server.pem') ([Text.Encoding]::ASCII.GetBytes($pem))
        $imported=New-Object Security.Cryptography.X509Certificates.X509Certificate2((Join-Path $Root 'server.pfx'),$password,[Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet)
        return (Assert-HttpsCertificate $imported $Id)
    } finally { if ($null -ne $imported) {$imported.Dispose()};if ($null -ne $certificate) {$certificate.Dispose()};if ($null -ne $rsa) {$rsa.Dispose()} }
}

function Close-RackClickHttpsProfile {
    param([hashtable]$Profile)
    if ($null -ne $Profile -and $Profile.ContainsKey('inputLocks')) { foreach ($stream in $Profile.inputLocks) {$stream.Dispose()} }
}

function Read-RackClickHttpsProfile {
    param([hashtable]$Instance,[string]$ProfilePath,[string]$ExpectedProfileSha256)
    $streams=@();$certificate=$null
    try {
        if ($ExpectedProfileSha256 -notmatch '^[a-fA-F0-9]{64}$') { Stop-HttpsProfileCheck 'https_reference_required' }
        $root=Get-StageLocalPath $ProfilePath;Assert-HttpsProfileDisjoint $root $Instance;Assert-BackupPrivateAcl $root
        $allowed=@('pfx-password.txt','server.pem','server.pfx','tls.json')
        $entries=@((New-Object IO.DirectoryInfo($root)).GetFileSystemInfos())
        if ($entries.Count -ne 4 -or @($entries | Where-Object {$_ -isnot [IO.FileInfo] -or $_.Name -cnotin $allowed}).Count -ne 0) { Stop-HttpsProfileCheck 'https_profile_contents_invalid' }
        foreach ($name in $allowed) {
            $path=Join-Path $root $name;Assert-BackupPrivateAcl $path
            $streams += [IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
            if ((Get-Item -LiteralPath $path).Length -gt 32768) { Stop-HttpsProfileCheck 'https_profile_size_invalid' }
        }
        $manifestPath=Join-Path $root 'tls.json'
        if ((Get-RuntimeConfigDigest $manifestPath) -cne $ExpectedProfileSha256.ToLowerInvariant()) { Stop-HttpsProfileCheck 'https_profile_hash_mismatch' }
        $manifest=[IO.File]::ReadAllText($manifestPath,[Text.Encoding]::UTF8)|ConvertFrom-Json
        if ((($manifest.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'certificateSha256,files,id,instanceId,instanceManifestSha256,kind,notAfterUtc,notBeforeUtc,publicOrigin,schemaVersion' -or
            $manifest.schemaVersion -ne 1 -or $manifest.kind -cne 'RackClickLoopbackHttpsProfile' -or
            $manifest.id -cnotmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$' -or
            $manifest.instanceId -cne $Instance.id -or $manifest.instanceManifestSha256 -cne (Get-RuntimeConfigDigest $Instance.manifestPath) -or
            $manifest.publicOrigin -cne ('https://127.0.0.1:'+[string]$Instance.httpPort) -or
            $manifest.certificateSha256 -cnotmatch '^[a-f0-9]{64}$' -or
            (($manifest.files.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'pfx-password.txt,server.pem,server.pfx') { Stop-HttpsProfileCheck 'https_profile_manifest_invalid' }
        foreach ($name in @('pfx-password.txt','server.pem','server.pfx')) {
            if ($manifest.files.$name -cnotmatch '^[a-f0-9]{64}$' -or (Get-RuntimeConfigDigest (Join-Path $root $name)) -cne $manifest.files.$name) { Stop-HttpsProfileCheck 'https_profile_file_hash_mismatch' }
        }
        $password=[IO.File]::ReadAllText((Join-Path $root 'pfx-password.txt'),[Text.Encoding]::UTF8)
        if ($password -cnotmatch '^[a-f0-9]{64}$') { Stop-HttpsProfileCheck 'https_profile_password_invalid' }
        $pem=[IO.File]::ReadAllText((Join-Path $root 'server.pem'),[Text.Encoding]::ASCII)
        if ($pem -cnotmatch '\A-----BEGIN CERTIFICATE-----\n([A-Za-z0-9+/=\n]+)\n-----END CERTIFICATE-----\n\z') { Stop-HttpsProfileCheck 'https_profile_pem_invalid' }
        $der=[Convert]::FromBase64String($Matches[1])
        if ((Get-HttpsBytesSha256 $der) -cne $manifest.certificateSha256) { Stop-HttpsProfileCheck 'https_profile_certificate_mismatch' }
        try { $certificate=New-Object Security.Cryptography.X509Certificates.X509Certificate2((Join-Path $root 'server.pfx'),$password,[Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet) }
        catch { Stop-HttpsProfileCheck 'https_profile_pfx_invalid' }
        $metadata=Assert-HttpsCertificate $certificate $manifest.id
        if ($metadata.sha256 -cne $manifest.certificateSha256 -or $metadata.notBeforeUtc -cne $manifest.notBeforeUtc -or $metadata.notAfterUtc -cne $manifest.notAfterUtc) { Stop-HttpsProfileCheck 'https_profile_certificate_mismatch' }
        return @{origin=$manifest.publicOrigin;pfxPath=(Join-Path $root 'server.pfx');password=$password;pemPath=(Join-Path $root 'server.pem');certificateSha256=$metadata.sha256;root=$root;inputLocks=$streams}
    } catch { foreach ($stream in $streams) {$stream.Dispose()};throw }
    finally { if ($null -ne $certificate) {$certificate.Dispose()} }
}
