#requires -Version 5.1
[CmdletBinding()]
param([string]$InstancePath='',[string]$ExpectedInstanceSha256='',[string]$DestinationPath='')
$httpsInputs=@{instance=$InstancePath;instanceHash=$ExpectedInstanceSha256;destination=$DestinationPath}
. (Join-Path $PSScriptRoot 'RackClick.Https.ps1')
$report=[ordered]@{valid=$false;exitCode=2;code='https_profile_creation_failed';profilePath='';profileSha256='';certificateSha256=''}
$instance=$null;$instanceLock=$null;$profile=$null
try {
    $root=Get-StageLocalPath $httpsInputs.destination
    $instance=Read-RackClickInstance $httpsInputs.instance $httpsInputs.instanceHash
    Assert-HttpsProfileDisjoint $root $instance
    if ([IO.File]::Exists($root) -or [IO.Directory]::Exists($root)) { Stop-HttpsProfileCheck 'https_destination_exists' 1 }
    try { $instanceLock=[IO.File]::Open($instance.lockPath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None) }
    catch [IO.IOException] {
        $native=($_.Exception.HResult-band 65535)
        if ($native -in @(32,33)) { Stop-HttpsProfileCheck 'https_instance_in_use' 1 };throw
    }
    if ([IO.File]::Exists((Join-Path $instance.pgData 'postmaster.pid'))) { Stop-HttpsProfileCheck 'https_instance_postmaster_present' 1 }
    $null=New-BackupPrivateDirectory $root
    $id=[guid]::NewGuid().ToString('D')
    $metadata=New-HttpsCertificateFiles $root $id
    $files=[ordered]@{}
    foreach ($name in @('pfx-password.txt','server.pem','server.pfx')) { $files[$name]=Get-RuntimeConfigDigest (Join-Path $root $name) }
    $manifest=[ordered]@{schemaVersion=1;kind='RackClickLoopbackHttpsProfile';id=$id;instanceId=$instance.id;instanceManifestSha256=(Get-RuntimeConfigDigest $instance.manifestPath);publicOrigin=('https://127.0.0.1:'+[string]$instance.httpPort);certificateSha256=$metadata.sha256;notBeforeUtc=$metadata.notBeforeUtc;notAfterUtc=$metadata.notAfterUtc;files=$files}
    $manifestPath=Join-Path $root 'tls.json'
    Write-HttpsNewBytes $manifestPath ([Text.Encoding]::UTF8.GetBytes(($manifest|ConvertTo-Json -Depth 5 -Compress)))
    $digest=Get-RuntimeConfigDigest $manifestPath
    $profile=Read-RackClickHttpsProfile -Instance $instance -ProfilePath $root -ExpectedProfileSha256 $digest
    $report.valid=$true;$report.exitCode=0;$report.code='https_profile_created';$report.profilePath=$root;$report.profileSha256=$digest;$report.certificateSha256=$metadata.sha256
} catch {
    foreach ($pair in @(@('httpsCode','httpsExit'),@('instanceCode','instanceExit'),@('stageCode','stageExit'),@('code','exitCode'))) {
        if ($_.Exception.Data.Contains($pair[0])) {$report.code=$_.Exception.Data[$pair[0]];$report.exitCode=[int]$_.Exception.Data[$pair[1]];break}
    }
} finally {
    Close-RackClickHttpsProfile $profile
    if ($null -ne $instanceLock) {$instanceLock.Dispose()}
    Close-RackClickInstance $instance
}
$report|ConvertTo-Json -Compress
exit $report.exitCode
