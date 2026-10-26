param(
    [string]$NodeDirectory = (Join-Path $PSScriptRoot '../../.local/node-v24.21.0-win-x64'),
    [switch]$SkipRestore
)
$ErrorActionPreference = 'Stop'
$reference = Join-Path $PSScriptRoot 'rc9-reference/RackClick-v0.9.0-rc9-Adoptada-2026-09-28'
if (-not (Test-Path -LiteralPath $reference)) {
    $archive = Join-Path $PSScriptRoot '../../reference/RackClick-v0.9.0-rc9-Adoptada-2026-09-28.zip'
    if (-not (Test-Path -LiteralPath $archive)) { throw 'The adopted RC9 reference ZIP is required.' }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $extraction = Join-Path $PSScriptRoot 'rc9-reference'
    if (Test-Path -LiteralPath $extraction) { throw 'Incomplete reference extraction exists. Inspect it before proceeding; it will not be overwritten.' }
    [IO.Compression.ZipFile]::ExtractToDirectory((Resolve-Path -LiteralPath $archive).Path, $extraction)
}
$node = Join-Path $NodeDirectory 'node.exe'
$npm = Join-Path $NodeDirectory 'npm.cmd'
if (-not (Test-Path -LiteralPath $node) -or -not (Test-Path -LiteralPath $npm)) {
    throw 'Node 24.21.0/npm 11.19.0 required. Run the documented environment preparation first.'
}
if ((& $node --version) -ne 'v24.21.0') { throw 'Unexpected Node version; the fixed version is 24.21.0.' }
$previousPath = $env:Path
Push-Location $PSScriptRoot
try {
    $env:Path = (Resolve-Path -LiteralPath $NodeDirectory).Path + ';' + $env:Path
    if ((& $npm --version) -ne '11.19.0') { throw 'Unexpected npm version; the fixed version is 11.19.0.' }
    if (-not $SkipRestore) {
        & $npm ci --ignore-scripts --registry=https://registry.npmjs.org
        if ($LASTEXITCODE -ne 0) { throw 'Frontend locked dependency restore failed.' }
    }
    & $node build.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    & $node --test tests/api.test.mjs tests/inventory.test.mjs tests/admin-groups.test.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Frontend adapter tests failed.' }
}
finally { $env:Path = $previousPath; Pop-Location }
