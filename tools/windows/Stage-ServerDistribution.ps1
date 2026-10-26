#requires -Version 5.1
<# Prepare a NEW local staging directory only. Never installs or starts RackClick/DB.
   SHA256 input must come from an approved external release record.
   Exit 0 staged; 1 missing/incompatible/existing; 2 invalid/indeterminate.
#>
[CmdletBinding()]
param([string]$ManifestPath='', [string]$ExpectedManifestSha256='', [string]$ServerPath='', [string]$FrontendPath='', [string]$DotNetPath='', [string]$PostgresBinPath='', [string]$DestinationPath='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
# Helpers load186 definitions only. Preserve parameters with names also declared there.
$stageInputs=@{manifest=$ManifestPath;expected=$ExpectedManifestSha256;server=$ServerPath;frontend=$FrontendPath;dotnet=$DotNetPath;pg=$PostgresBinPath;destination=$DestinationPath}
. (Join-Path $PSScriptRoot 'RackClick.Stage.ps1')
$report=[ordered]@{schemaVersion=1;valid=$false;exitCode=2;code='input_invalid';destinationPath='';stageId='';receiptSha256='';verifiedFiles=0;scope='Staging only; not installation or application acceptance'}
$owned=$false; $stateStream=$null; $state=$null; $manifestLock=$null
try {
    if ($stageInputs.expected -notmatch '^[a-fA-F0-9]{64}$') { Stop-StageCheck 'input_invalid' }
    $paths=@{}
    foreach ($name in @('manifest','server','frontend','dotnet','pg','destination')) { $paths[$name]=Get-StageLocalPath $stageInputs[$name] }
    $report.destinationPath=$paths.destination
    $parent=[IO.Path]::GetDirectoryName($paths.destination)
    if (-not [IO.Directory]::Exists($parent)) { Stop-StageCheck 'destination_parent_missing' 1 }
    Assert-StageNoReparse $parent
    if ([IO.File]::Exists($paths.destination) -or [IO.Directory]::Exists($paths.destination)) { Stop-StageCheck 'destination_exists' 1 }
    foreach ($other in @($paths.manifest,$paths.server,$paths.frontend,$paths.pg,([IO.Path]::GetDirectoryName($paths.dotnet)))) {
        if (Test-StageOverlap $paths.destination $other) { Stop-StageCheck 'source_destination_overlap' }
    }
    foreach ($name in @('manifest','server','frontend','dotnet','pg')) {
        if (-not (Test-Path -LiteralPath $paths[$name])) { Stop-StageCheck 'input_path_missing' 1 }
        Assert-StageNoReparse $paths[$name]
    }
    foreach ($name in @('postgres.exe','pg_dump.exe','pg_restore.exe')) { if ([IO.File]::Exists((Join-Path $paths.pg $name))) { Assert-StageNoReparse (Join-Path $paths.pg $name) } }
    $null=Invoke-StageIntegrity $paths.manifest $stageInputs.expected $paths.server $paths.frontend
    $null=Invoke-StageRuntime $paths.dotnet $paths.pg $paths.server
    # Atomic CreateDirectoryW returns false for an existing destination, including a race.
    Assert-StageNoReparse $parent
    New-StageDirectoryExclusive $paths.destination
    $owned=$true; $stageId=[guid]::NewGuid().ToString('D'); $report.stageId=$stageId
    Assert-StageNoReparse $paths.destination
    $stateStream=[IO.File]::Open((Join-Path $paths.destination 'stage-state.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::Read)
    $state=[ordered]@{schemaVersion=1;stageId=$stageId;status='in-progress';manifestSha256=$stageInputs.expected.ToLowerInvariant();receiptSha256='';code='copy_pending';verifiedFiles=0}
    Set-StageState $stateStream $state
    Copy-StageFileExclusive $paths.manifest (Join-Path $paths.destination 'manifest.json')
    $manifestLock=[IO.File]::Open((Join-Path $paths.destination 'manifest.json'),[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    if ((Get-RuntimeConfigDigest (Join-Path $paths.destination 'manifest.json')) -ne $stageInputs.expected.ToLowerInvariant()) { Stop-StageCheck 'manifest_changed_during_copy' 1 }
    $manifest=[IO.File]::ReadAllText((Join-Path $paths.destination 'manifest.json')) | ConvertFrom-Json
    foreach ($kind in @('server','frontend')) {
        $targetRoot=Join-Path $paths.destination $kind
        New-StageDirectoryExclusive $targetRoot
        foreach ($entry in $manifest.distributions.$kind.PSObject.Properties) {
            $target=Join-Path $targetRoot $entry.Name.Replace('/',[IO.Path]::DirectorySeparatorChar)
            $relativeParent=[IO.Path]::GetDirectoryName($entry.Name.Replace('/',[IO.Path]::DirectorySeparatorChar))
            $current=$targetRoot
            if ($relativeParent.Length -ne 0) {
                foreach ($segment in $relativeParent.Split([IO.Path]::DirectorySeparatorChar)) {
                    $current=Join-Path $current $segment
                    if (-not [IO.Directory]::Exists($current)) { New-StageDirectoryExclusive $current }
                    Assert-StageNoReparse $current
                }
            }
            Copy-StageFileExclusive (Join-Path $paths[$kind] $entry.Name.Replace('/',[IO.Path]::DirectorySeparatorChar)) $target
        }
    }
    $integrity=Invoke-StageIntegrity (Join-Path $paths.destination 'manifest.json') $stageInputs.expected (Join-Path $paths.destination 'server') (Join-Path $paths.destination 'frontend')
    $runtime=Invoke-StageRuntime $paths.dotnet $paths.pg (Join-Path $paths.destination 'server')
    $receipt=[ordered]@{schemaVersion=1;stageId=$stageId;utc=[DateTime]::UtcNow.ToString('o');status='artifacts-verified';manifestSha256=$stageInputs.expected.ToLowerInvariant();target='win-x64/net10.0';serverFiles=$integrity.serverFiles;frontendFiles=$integrity.frontendFiles;verifiedFiles=$integrity.verifiedFiles;postgresRequiredVersion='17.11';frameworks=@($runtime.frameworks | Where-Object { $_.name -in @('Microsoft.NETCore.App','Microsoft.AspNetCore.App') -and $_.version -match '^10\.0\.[0-9]+$' });postgres=@($runtime.postgres);scope='Staging only; no database, application, service or HTTPS acceptance'}
    Write-StageJsonExclusive (Join-Path $paths.destination 'stage-receipt.json') $receipt
    $digest=Get-RuntimeConfigDigest (Join-Path $paths.destination 'stage-receipt.json')
    $state.status='staged'; $state.code='artifacts_staged'; $state.receiptSha256=$digest; $state.verifiedFiles=$integrity.verifiedFiles
    Set-StageState $stateStream $state
    $report.receiptSha256=$digest; $report.verifiedFiles=$integrity.verifiedFiles; $report.valid=$true; $report.exitCode=0; $report.code='artifacts_staged'
} catch {
    if ($_.Exception.Data.Contains('stageCode')) { $report.code=$_.Exception.Data['stageCode']; $report.exitCode=$_.Exception.Data['stageExit'] }
    else { $report.code='staging_failed' }
    if ($owned -and $null -ne $stateStream -and $null -ne $state) {
        try { $state.status='failed'; $state.code=$report.code; $state.receiptSha256=''; $state.verifiedFiles=0; Set-StageState $stateStream $state }
        catch { $report.code='failure_state_write_failed'; $report.exitCode=2 }
    }
} finally {
    if ($null -ne $manifestLock) { $manifestLock.Dispose() }
    if ($null -ne $stateStream) { $stateStream.Dispose() }
}
$report | ConvertTo-Json -Depth 5 -Compress
exit $report.exitCode
