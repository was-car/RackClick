#requires -Version 5.1
# Development only: no build, application startup or database access.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$env:PSModulePath=[IO.Path]::Combine($PSHOME,'Modules')+[IO.Path]::PathSeparator+[string]$env:PSModulePath
$restoreExitCode=1
$restoreLocationEntered=$false
try {
    $restoreWorkspace=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
    $restoreServer=Join-Path $restoreWorkspace 'development/server'
    $restoreSdk=Get-Content -LiteralPath (Join-Path $restoreServer 'global.json') -Raw | ConvertFrom-Json
    $restoreLock=Get-Content -LiteralPath (Join-Path $restoreWorkspace 'development/toolchain.lock.json') -Raw | ConvertFrom-Json
    $restoreTools=@($restoreLock.components | Where-Object {$_.id -eq 'dotnet'})
    if ($restoreTools.Count -ne 1 -or $restoreTools[0].version -cne $restoreSdk.sdk.version -or $restoreSdk.sdk.rollForward -cne 'disable') {throw 'SDK pin and toolchain lock do not match.'}
    $restoreDotnet=Join-Path (Join-Path (Join-Path $restoreWorkspace '.local') $restoreTools[0].installDirectory) $restoreTools[0].executable
    if (-not [IO.File]::Exists($restoreDotnet)) {throw 'Pinned local SDK is missing. See tools/windows/Initialize-Toolchain.ps1.'}
    $env:DOTNET_ROOT=[IO.Path]::GetDirectoryName($restoreDotnet)
    $env:DOTNET_CLI_HOME=Join-Path $restoreWorkspace '.local/dotnet-home'
    $env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
    $env:DOTNET_NOLOGO='1'
    $env:DOTNET_GENERATE_ASPNET_CERTIFICATE='false'
    Push-Location -LiteralPath $restoreServer
    $restoreLocationEntered=$true
    $restoreVersion=& $restoreDotnet --version
    if ($LASTEXITCODE -ne 0 -or $restoreVersion.Trim() -cne $restoreSdk.sdk.version) {throw 'The selected SDK does not match global.json.'}
    Write-Output ('Using pinned SDK '+$restoreVersion.Trim()+' and the real RackClick.sln.')
    & $restoreDotnet restore 'RackClick.sln' --locked-mode --configfile (Join-Path $restoreWorkspace 'NuGet.Config') --packages (Join-Path $restoreWorkspace '.local/nuget/packages') --disable-parallel
    $restoreExitCode=$LASTEXITCODE
} catch {
    Write-Output ('Dependency restore failed: '+$_.Exception.Message)
} finally {
    if ($restoreLocationEntered) {Pop-Location}
}
exit $restoreExitCode
