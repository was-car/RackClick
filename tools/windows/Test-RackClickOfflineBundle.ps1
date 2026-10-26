#requires -Version 5.1
[CmdletBinding()]
param([string]$ArchivePath='',[string]$ExpectedArchiveSha256='')
$offlineTestInputs=@{archive=$ArchivePath;hash=$ExpectedArchiveSha256}
. (Join-Path $PSScriptRoot 'RackClick.OfflineBundle.ps1')
$bundle=$null
$report=[ordered]@{valid=$false;exitCode=2;code='bundle_invalid';bundleId='';bundleArchiveSha256='';bundleManifestSha256='';applicationManifestSha256='';versions=$null;counts=$null;verifiedFiles=0;uncompressedBytes=0}
try {
    $bundle=Read-RackClickOfflineBundle -ArchivePath $offlineTestInputs.archive -ExpectedArchiveSha256 $offlineTestInputs.hash
    $report.valid=$true;$report.exitCode=0;$report.code='bundle_verified'
    $report.bundleId=$bundle.manifest.id;$report.bundleArchiveSha256=$bundle.archiveSha256;$report.bundleManifestSha256=$bundle.manifestSha256
    $report.applicationManifestSha256=$bundle.manifest.applicationManifestSha256;$report.versions=$bundle.manifest.versions
    $report.counts=$bundle.counts;$report.verifiedFiles=$bundle.verifiedFiles;$report.uncompressedBytes=$bundle.uncompressedBytes
} catch {
    if ($_.Exception.Data.Contains('bundleCode')) {$report.code=[string]$_.Exception.Data['bundleCode'];$report.exitCode=[int]$_.Exception.Data['bundleExit']}
} finally {
    try {Close-RackClickOfflineBundle $bundle}
    catch {$report.valid=$false;$report.exitCode=2;$report.code='bundle_close_failed';$report.bundleArchiveSha256='';$report.bundleManifestSha256=''}
}
$report|ConvertTo-Json -Depth 8 -Compress
exit $report.exitCode
