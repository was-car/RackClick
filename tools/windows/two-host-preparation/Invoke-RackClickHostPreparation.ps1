#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateSet('Server','Client3')][string]$Role)
$ErrorActionPreference='Stop'
# Prefer the Windows PowerShell modules when the caller inherited a PS7 path.
# This changes only this process and keeps all existing module paths.
$nativeModules=[IO.Path]::Combine($PSHOME,'Modules')
$env:PSModulePath=$nativeModules+[IO.Path]::PathSeparator+[string]$env:PSModulePath
try {
    if (-not [Environment]::Is64BitProcess) {throw 'Use Windows PowerShell x64.'}
    $manifest=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'MANIFIESTO.json') -Raw | ConvertFrom-Json
    $names=@('01-DATOS-SERVIDOR.cmd','02-DATOS-WINDOWS11-SERVIDOR.cmd','Get-RackClickHostReadiness.ps1','Invoke-RackClickHostPreparation.ps1','LEEME-PRIMERO.html','PLAN-PENDIENTE.json')
    if ($manifest.schemaVersion -ne 1 -or $manifest.kind -cne 'RackClickHostPreparation' -or @($manifest.files.PSObject.Properties).Count -ne $names.Count) {throw 'Invalid preparation manifest.'}
    foreach ($name in $names) {
        $entry=$manifest.files.PSObject.Properties | Where-Object {$_.Name -ceq $name}
        if (@($entry).Count -ne 1 -or [string]$entry.Value -cnotmatch '^[a-f0-9]{64}$') {throw 'Invalid preparation file reference.'}
        $path=Join-Path $PSScriptRoot $name
        if ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint) {throw 'Preparation file must not be a reparse point.'}
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$entry.Value) {throw ('Preparation file changed: '+$name)}
    }
    $reports=Join-Path $PSScriptRoot 'resultados'
    if (-not (Test-Path -LiteralPath $reports)) {$null=New-Item -ItemType Directory -Path $reports}
    if (-not (Test-Path -LiteralPath $reports -PathType Container) -or ((Get-Item -LiteralPath $reports).Attributes -band [IO.FileAttributes]::ReparsePoint)) {throw 'Invalid report directory.'}
    Write-Output ('Carpeta de informes: '+$reports)
    & (Join-Path $PSScriptRoot 'Get-RackClickHostReadiness.ps1') -Role $Role -OutputDirectory $reports
    exit $LASTEXITCODE
} catch {
    Write-Output 'Preparation failed; no installation or network configuration was performed.'
    Write-Output $_.Exception.Message
    exit 2
}
