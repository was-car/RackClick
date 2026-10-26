# Dot-source this script to change only the current PowerShell process.
# . ./tools/windows/Use-Toolchain.ps1
$rackClickWorkspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$rackClickToolchain = Get-Content -LiteralPath (Join-Path $rackClickWorkspace 'development/toolchain.lock.json') -Raw | ConvertFrom-Json
$rackClickPaths = @()
foreach ($rackClickTool in $rackClickToolchain.components) {
    $rackClickExe = Join-Path (Join-Path (Join-Path $rackClickWorkspace '.local') $rackClickTool.installDirectory) $rackClickTool.executable
    if (-not (Test-Path -LiteralPath $rackClickExe -PathType Leaf)) { throw "Missing tool: $($rackClickTool.id). Run Initialize-Toolchain.ps1 first." }
    $rackClickPaths += Split-Path -Parent $rackClickExe
    if ($rackClickTool.id -eq 'dotnet') { $env:DOTNET_ROOT = Split-Path -Parent $rackClickExe }
}
$env:PATH = ($rackClickPaths -join ';') + ';' + $env:PATH
$env:DOTNET_CLI_HOME = Join-Path $rackClickWorkspace '.local/dotnet-home'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_NOLOGO = '1'
$env:DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE = '1'
$env:DOTNET_GENERATE_ASPNET_CERTIFICATE = 'false'
$env:NUGET_PACKAGES = Join-Path $rackClickWorkspace '.local/nuget/packages'
$env:npm_config_cache = Join-Path $rackClickWorkspace '.local/npm-cache'
