# Internal development setup. Does not create databases, services or firewall rules.
[CmdletBinding()]
param(
    [ValidateSet('git', 'dotnet', 'postgresql', 'node')]
    [string[]]$Component = @('git', 'dotnet', 'postgresql', 'node')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$localRoot = Join-Path $workspace '.local'
$downloadRoot = Join-Path $localRoot 'downloads'
$lock = Get-Content -LiteralPath (Join-Path $workspace 'development/toolchain.lock.json') -Raw | ConvertFrom-Json
if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
    throw 'This lock supports native Windows x64 only.'
}
$sdkPin = Get-Content -LiteralPath (Join-Path $workspace 'development/server/global.json') -Raw | ConvertFrom-Json
$sdkLock = @($lock.components | Where-Object id -eq 'dotnet')[0]
if ($sdkPin.sdk.version -ne $sdkLock.version -or $sdkPin.sdk.rollForward -ne 'disable') {
    throw 'global.json and toolchain.lock.json disagree. Review pins explicitly; no automatic replacement.'
}
New-Item -ItemType Directory -Path $downloadRoot -Force | Out-Null
$results = @()
Add-Type -AssemblyName System.IO.Compression.FileSystem

foreach ($item in $lock.components | Where-Object { $_.id -in $Component }) {
    $archive = Join-Path $downloadRoot $item.archive
    if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) {
        $partial = $archive + '.' + [Guid]::NewGuid().ToString('N') + '.partial'
        & curl.exe --fail --location --silent --show-error --proto '=https' --tlsv1.2 --output $partial $item.url
        if ($LASTEXITCODE -ne 0) { throw "Download failed for $($item.id); partial preserved at $partial" }
        $downloadHash = (Get-FileHash -LiteralPath $partial -Algorithm $item.hashAlgorithm).Hash
        if ($downloadHash -ine $item.hash) { throw "Downloaded hash mismatch for $($item.id); refusing extraction." }
        Move-Item -LiteralPath $partial -Destination $archive
    }
    $actualHash = (Get-FileHash -LiteralPath $archive -Algorithm $item.hashAlgorithm).Hash.ToLowerInvariant()
    if ($actualHash -ne $item.hash) { throw "Cached archive hash mismatch for $($item.id); refusing extraction." }

    $install = [IO.Path]::GetFullPath((Join-Path $localRoot $item.installDirectory))
    $localPrefix = [IO.Path]::GetFullPath($localRoot).TrimEnd('\') + '\'
    if (-not $install.StartsWith($localPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Install path escaped .local.' }
    $executable = Join-Path $install $item.executable
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        if (Test-Path -LiteralPath $install) { throw "Incomplete or unrelated directory exists: $install. No overwrite performed." }
        $extractRoot = $install
        if ($item.archiveHasRootDirectory) { $extractRoot = $localRoot }
        $installPrefix = $install.TrimEnd('\') + '\'
        $zip = [IO.Compression.ZipFile]::OpenRead($archive)
        try {
            foreach ($entry in $zip.Entries) {
                $resolved = [IO.Path]::GetFullPath((Join-Path $extractRoot $entry.FullName))
                if ($resolved -ne $install -and -not $resolved.StartsWith($installPrefix, [StringComparison]::OrdinalIgnoreCase)) {
                    throw "ZIP entry escaped install directory: $($entry.FullName)"
                }
            }
        } finally { $zip.Dispose() }
        if (-not $item.archiveHasRootDirectory) { New-Item -ItemType Directory -Path $install | Out-Null }
        & tar.exe -xf $archive -C $extractRoot
        if ($LASTEXITCODE -ne 0) { throw "Extraction failed for $($item.id); partial directory preserved, never silently overwritten." }
    }
    # Reused installations must contain the same executable as the verified ZIP.
    # Especially important for the unsigned PostgreSQL executable.
    $zip = [IO.Compression.ZipFile]::OpenRead($archive)
    try {
        $exeEntryName = $item.executable.Replace('\', '/')
        if ($item.archiveHasRootDirectory) { $exeEntryName = $item.installDirectory + '/' + $exeEntryName }
        $exeEntry = $zip.GetEntry($exeEntryName)
        if ($null -eq $exeEntry) { throw "Executable missing from verified archive for $($item.id)." }
        $entryStream = $exeEntry.Open()
        $sha = [Security.Cryptography.SHA256]::Create()
        try { $expectedExeHash = [BitConverter]::ToString($sha.ComputeHash($entryStream)).Replace('-', '').ToLowerInvariant() }
        finally { $sha.Dispose(); $entryStream.Dispose() }
    } finally { $zip.Dispose() }
    $actualExeHash = (Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualExeHash -ne $expectedExeHash) { throw "Installed executable differs from verified archive for $($item.id)." }
    $signature = Get-AuthenticodeSignature -LiteralPath $executable
    if ($signature.Status.ToString() -ne $item.signaturePolicy) { throw "Unexpected signature status for $($item.id): $($signature.Status)" }
    $signer = $null
    if ($null -ne $signature.SignerCertificate) { $signer = $signature.SignerCertificate.Subject }
    if ($item.signaturePolicy -eq 'Valid' -and $signer -ne $item.signerSubject) { throw "Unexpected signer for $($item.id)." }
    $version = (& $executable --version | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $version -ne $item.versionOutput) { throw "Version check failed for $($item.id): $version" }
    $npmVersion = $null
    if ($item.id -eq 'node') {
        $npmVersion = (& (Join-Path $install 'npm.cmd') --version | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or $npmVersion -ne $item.npmVersion) { throw 'npm version does not match lock.' }
    }
    $results += [pscustomobject]@{
        id = $item.id; version = $version; npmVersion = $npmVersion; archiveHash = $actualHash
        algorithm = $item.hashAlgorithm; executableSha256 = $actualExeHash; signature = $signature.Status.ToString(); signer = $signer
        executable = $executable; source = $item.url; hashSource = $item.hashSource
    }
    Write-Host "$($item.id): $version; $($item.hashAlgorithm) OK; signature $($signature.Status)"
}
$evidenceRoot = Join-Path $workspace 'evidence/s1-20260928/windows'
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
$evidence = Join-Path $evidenceRoot ('toolchain-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.json')
[pscustomobject]@{
    executedUtc = [DateTime]::UtcNow.ToString('o'); os = [Environment]::OSVersion.VersionString
    powershell = $PSVersionTable.PSVersion.ToString(); components = $results
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $evidence -Encoding UTF8
Write-Host "Evidence: $evidence"
