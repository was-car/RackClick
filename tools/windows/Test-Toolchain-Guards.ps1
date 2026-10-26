[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$fixture = Join-Path $workspace ('.local/toolchain-guards-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path (Join-Path $fixture 'tools/windows'), (Join-Path $fixture 'development/server'), (Join-Path $fixture '.local/downloads') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Initialize-Toolchain.ps1') -Destination (Join-Path $fixture 'tools/windows/Initialize-Toolchain.ps1')
$sourceLock = Join-Path $workspace 'development/toolchain.lock.json'
$fixtureLock = Join-Path $fixture 'development/toolchain.lock.json'
$fixtureGlobal = Join-Path $fixture 'development/server/global.json'
Copy-Item -LiteralPath $sourceLock -Destination $fixtureLock
Copy-Item -LiteralPath (Join-Path $workspace 'development/server/global.json') -Destination $fixtureGlobal
$results = @()

function Assert-Rejected([string]$Name, [string]$Expected) {
    $log = Join-Path $fixture ($Name + '.log')
    $process = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-File', ('"' + (Join-Path $fixture 'tools/windows/Initialize-Toolchain.ps1') + '"'), '-Component', 'git') -Wait -PassThru -WindowStyle Hidden -RedirectStandardOutput ($log + '.out') -RedirectStandardError ($log + '.err')
    $output = (Get-Content -LiteralPath ($log + '.out'), ($log + '.err') -Raw | Out-String)
    if ($process.ExitCode -eq 0 -or $output -notmatch $Expected) { throw "Guard test failed: $Name, exit $($process.ExitCode). See $log.*" }
    [pscustomobject]@{ name = $Name; exitCode = $process.ExitCode; expected = $Expected; result = 'PASS' }
}

Set-Content -LiteralPath $fixtureGlobal -Encoding UTF8 -Value '{"sdk":{"version":"0.0.0","rollForward":"disable"}}'
$results += Assert-Rejected 'sdk-pin-mismatch' 'global.json and toolchain.lock.json disagree'
Copy-Item -LiteralPath (Join-Path $workspace 'development/server/global.json') -Destination $fixtureGlobal
$git = (Get-Content -LiteralPath $fixtureLock -Raw | ConvertFrom-Json).components | Where-Object id -eq 'git'
$fixtureArchive = Join-Path (Join-Path $fixture '.local/downloads') $git.archive
Set-Content -LiteralPath $fixtureArchive -Encoding ASCII -Value 'intentionally corrupt cached archive'
$results += Assert-Rejected 'corrupt-cache' 'Cached archive hash mismatch'

# A disposable ZIP allows exercising non-overwrite without downloading tools.
$zipSource = Join-Path $fixture 'zip-source'
New-Item -ItemType Directory -Path $zipSource | Out-Null
Set-Content -LiteralPath (Join-Path $zipSource 'marker.txt') -Value 'fixture'
$fixtureGoodZip = Join-Path $fixture '.local/downloads/guard-fixture.zip'
Compress-Archive -LiteralPath (Join-Path $zipSource 'marker.txt') -DestinationPath $fixtureGoodZip
$fixtureData = Get-Content -LiteralPath $fixtureLock -Raw | ConvertFrom-Json
$fixtureGit = $fixtureData.components | Where-Object id -eq 'git'
$fixtureGit.archive = 'guard-fixture.zip'
$fixtureGit.hash = (Get-FileHash -LiteralPath $fixtureGoodZip -Algorithm SHA256).Hash.ToLowerInvariant()
$fixtureData | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $fixtureLock -Encoding UTF8
$partialInstall = Join-Path (Join-Path $fixture '.local') $git.installDirectory
New-Item -ItemType Directory -Path $partialInstall | Out-Null
$marker = Join-Path $partialInstall 'preserve.txt'
Set-Content -LiteralPath $marker -Value 'existing files must survive'
$markerHash = (Get-FileHash -LiteralPath $marker).Hash
$results += Assert-Rejected 'partial-install-preserved' 'Incomplete or unrelated directory exists'
if ((Get-FileHash -LiteralPath $marker).Hash -ne $markerHash) { throw 'Existing marker was modified.' }

$evidenceRoot = Join-Path $workspace 'evidence/s1-20260928/windows'
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
$evidence = Join-Path $evidenceRoot ('toolchain-guards-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.json')
[pscustomobject]@{ executedUtc = [DateTime]::UtcNow.ToString('o'); os = [Environment]::OSVersion.VersionString; fixture = $fixture; results = $results } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $evidence -Encoding UTF8
$results | Format-Table -AutoSize
Write-Host "Evidence: $evidence"
