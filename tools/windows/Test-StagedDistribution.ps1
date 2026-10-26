#requires -Version 5.1
<# Read-only staging validation, using TWO externally retained expected digests.
   Never follows paths from receipt/manifest; never executes a runtime or application.
#>
[CmdletBinding()]
param([string]$DestinationPath='', [string]$ExpectedManifestSha256='', [string]$ExpectedReceiptSha256='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$stageInputs=@{destination=$DestinationPath;manifestSha=$ExpectedManifestSha256;receiptSha=$ExpectedReceiptSha256}
. (Join-Path $PSScriptRoot 'RackClick.Stage.ps1')
$report=[ordered]@{schemaVersion=1;valid=$false;exitCode=2;code='input_invalid';destinationPath='';stageId='';receiptSha256='';verifiedFiles=0;scope='Read-only staging integrity; not current runtime or installation acceptance'}
$locks=@()
try {
    foreach ($digest in @($stageInputs.manifestSha,$stageInputs.receiptSha)) { if ($digest -notmatch '^[a-fA-F0-9]{64}$') { Stop-StageCheck 'input_invalid' } }
    $root=Get-StageLocalPath $stageInputs.destination; $report.destinationPath=$root
    if (-not [IO.Directory]::Exists($root)) { Stop-StageCheck 'staging_directory_missing' 1 }
    Assert-StageNoReparse $root
    $allowed=@('server','frontend','manifest.json','stage-state.json','stage-receipt.json')
    $entries=@((New-Object IO.DirectoryInfo($root)).GetFileSystemInfos())
    if ($entries.Count -ne 5 -or @($entries | Where-Object { $_.Name -notin $allowed }).Count -ne 0) { Stop-StageCheck 'staging_root_contents_invalid' 1 }
    foreach ($entry in $entries) {
        if (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { Stop-StageCheck 'reparse_path_rejected' }
        if (($entry.Name -in @('server','frontend')) -ne (($entry.Attributes -band [IO.FileAttributes]::Directory) -ne 0)) { Stop-StageCheck 'staging_root_contents_invalid' 1 }
    }
    foreach ($name in @('manifest.json','stage-state.json','stage-receipt.json')) { $locks += [IO.File]::Open((Join-Path $root $name),[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read) }
    $integrity=Invoke-StageIntegrity (Join-Path $root 'manifest.json') $stageInputs.manifestSha (Join-Path $root 'server') (Join-Path $root 'frontend')
    $digest=Get-RuntimeConfigDigest (Join-Path $root 'stage-receipt.json')
    if ($digest -ne $stageInputs.receiptSha.ToLowerInvariant()) { Stop-StageCheck 'receipt_untrusted' }
    try {
        $receipt=[IO.File]::ReadAllText((Join-Path $root 'stage-receipt.json')) | ConvertFrom-Json
        $state=[IO.File]::ReadAllText((Join-Path $root 'stage-state.json')) | ConvertFrom-Json
        $stageGuid=[guid]::ParseExact($receipt.stageId,'D')
        $utc=[DateTime]::ParseExact($receipt.utc,'o',[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind)
        if ($receipt.schemaVersion -ne 1 -or $receipt.status -ne 'artifacts-verified' -or $receipt.target -ne 'win-x64/net10.0' -or $receipt.manifestSha256 -ne $stageInputs.manifestSha.ToLowerInvariant() -or $receipt.serverFiles -ne $integrity.serverFiles -or $receipt.frontendFiles -ne $integrity.frontendFiles -or $receipt.verifiedFiles -ne $integrity.verifiedFiles -or $receipt.postgresRequiredVersion -ne '17.11') { Stop-StageCheck 'receipt_invalid' }
        if ($state.schemaVersion -ne 1 -or $state.status -ne 'staged' -or $state.code -ne 'artifacts_staged' -or $state.stageId -ne $receipt.stageId -or $state.manifestSha256 -ne $receipt.manifestSha256 -or $state.receiptSha256 -ne $digest -or $state.verifiedFiles -ne $integrity.verifiedFiles) { Stop-StageCheck 'staging_not_complete' 1 }
        $frameworks=@($receipt.frameworks); $pg=@($receipt.postgres)
        if ($utc.Kind -ne [DateTimeKind]::Utc -or (($frameworks.name | Sort-Object -Unique) -join ',') -ne 'Microsoft.AspNetCore.App,Microsoft.NETCore.App' -or @($frameworks | Where-Object { $_.version -notmatch '^10\.0\.[0-9]+$' }).Count -ne 0 -or $pg.Count -ne 3 -or (($pg.name | Sort-Object) -join ',') -ne 'pg_dump,pg_restore,postgres' -or @($pg | Where-Object { $_.version -ne '17.11' }).Count -ne 0) { Stop-StageCheck 'receipt_runtime_invalid' }
    } catch {
        if ($_.Exception.Data.Contains('stageCode')) { throw }
        Stop-StageCheck 'receipt_invalid'
    }
    $report.valid=$true; $report.exitCode=0; $report.code='staging_verified'; $report.stageId=$stageGuid.ToString('D'); $report.receiptSha256=$digest; $report.verifiedFiles=$integrity.verifiedFiles
} catch {
    if ($_.Exception.Data.Contains('stageCode')) { $report.code=$_.Exception.Data['stageCode']; $report.exitCode=$_.Exception.Data['stageExit'] }
    else { $report.code='verification_failed' }
} finally { foreach ($stream in $locks) { $stream.Dispose() } }
$report | ConvertTo-Json -Depth 5 -Compress
exit $report.exitCode
