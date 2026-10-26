#requires -Version 5.1
<# Read-only runtime inventory for the current framework-dependent RackClick server.
   Explicit approved paths only. No download/install/DB/service/port/app operations.
   Exit 0: requirements present; 1: absent/incompatible; 2: invalid/indeterminate.
   Dot-source only exposes functions for isolated verification; it performs no probes.
#>
[CmdletBinding()]
param(
    [string]$DotNetPath = '',
    [string]$PostgresBinPath = '',
    [string]$RuntimeConfigPath = '',
    [string]$PostgresVersion = '17.11'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-RuntimeVersionProbe {
    param([string]$Executable, [string]$Arguments, [int]$TimeoutMilliseconds = 15000)
    $process = New-Object System.Diagnostics.Process
    try {
        $start = New-Object System.Diagnostics.ProcessStartInfo
        $start.FileName = $Executable
        $start.Arguments = $Arguments
        $start.UseShellExecute = $false
        $start.CreateNoWindow = $true
        $start.RedirectStandardOutput = $true
        $start.RedirectStandardError = $true
        $start.EnvironmentVariables['DOTNET_CLI_TELEMETRY_OPTOUT'] = '1'
        $start.EnvironmentVariables['DOTNET_NOLOGO'] = '1'
        $start.EnvironmentVariables['DOTNET_SKIP_FIRST_TIME_EXPERIENCE'] = '1'
        $process.StartInfo = $start
        if (-not $process.Start()) { return @{ code = 'probe_start_failed' } }
        $output = $process.StandardOutput.ReadToEndAsync()
        $errorOutput = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutMilliseconds)) {
            # Only the exact process created above is owned; no process search/tree stop.
            $process.Kill()
            $process.WaitForExit()
            return @{ code = 'probe_timeout'; ownedProcessStopped = $process.HasExited }
        }
        if ($process.ExitCode -ne 0) { return @{ code = 'probe_failed' } }
        if ($errorOutput.Result.Length -ne 0) { return @{ code = 'probe_output_invalid' } }
        return @{ code = 'ok'; output = $output.Result }
    } catch { return @{ code = 'probe_failed' } }
    finally { $process.Dispose() }
}

function Get-RuntimeFrameworkInventory {
    param([string]$Listing)
    $observed = @()
    foreach ($line in ($Listing -split '\r?\n')) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        if ($line -notmatch '^(Microsoft\.[A-Za-z0-9.]+) ([0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?) \[.+\]$') {
            return @{ code = 'probe_output_invalid' }
        }
        $observed += @{ name = $Matches[1]; version = $Matches[2] }
    }
    $missing = @()
    foreach ($name in @('Microsoft.NETCore.App', 'Microsoft.AspNetCore.App')) {
        # Conservative current target: stable10.0 patches. No newer minor/major/prerelease fallback.
        $compatible = @($observed | Where-Object { $_.name -eq $name -and $_.version -match '^10\.0\.[0-9]+$' })
        if ($compatible.Count -eq 0) { $missing += $name }
    }
    return @{ code = 'ok'; frameworks = $observed; missing = $missing }
}

function Test-RuntimeX64Pe {
    param([string]$Path)
    $reader = $null
    try {
        $reader = New-Object System.IO.BinaryReader([System.IO.File]::OpenRead($Path))
        if ($reader.BaseStream.Length -lt 64 -or $reader.ReadUInt16() -ne 0x5a4d) { return $false }
        $reader.BaseStream.Position = 60
        $offset = $reader.ReadInt32()
        if ($offset -lt 64 -or $offset -gt $reader.BaseStream.Length - 6) { return $false }
        $reader.BaseStream.Position = $offset
        return $reader.ReadUInt32() -eq 0x00004550 -and $reader.ReadUInt16() -eq 0x8664
    } finally { if ($null -ne $reader) { $reader.Dispose() } }
}

function Get-RuntimeConfigDigest {
    param([string]$Path)
    $stream = $null; $algorithm = $null
    try {
        $stream = [System.IO.File]::OpenRead($Path)
        $algorithm = [System.Security.Cryptography.SHA256]::Create()
        return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '').ToLowerInvariant()
    } finally {
        if ($null -ne $stream) { $stream.Dispose() }
        if ($null -ne $algorithm) { $algorithm.Dispose() }
    }
}

function Get-RackClickRuntimeReadiness {
    param([string]$DotNet, [string]$PgBin, [string]$Config, [string]$PgVersion)
    $report = [ordered]@{
        schemaVersion = 1; ready = $false; exitCode = 2; code = 'input_invalid'
        scope = 'Read-only dependency inventory, not application startup or installation acceptance'
        target = 'win-x64/net10.0'; requiredFrameworkVersion = '10.0.0'; postgresRequiredVersion = $PgVersion
        frameworks = @(); postgres = @(); missing = @()
        sdkRequired = $false; nodeRequired = $false; gitRequired = $false; pythonRequired = $false
    }
    foreach ($path in @($DotNet, $PgBin, $Config)) {
        if ([string]::IsNullOrWhiteSpace($path) -or $path -notmatch '^[A-Za-z]:[\\/]' -or -not [System.IO.Path]::IsPathRooted($path)) { return $report }
    }
    if ($PgVersion -notmatch '^17\.[0-9]+$') { return $report }
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or -not [Environment]::Is64BitOperatingSystem -or -not [Environment]::Is64BitProcess) {
        $report.code = 'platform_unsupported'; return $report
    }
    if (-not [System.IO.File]::Exists($Config)) { $report.code = 'runtime_config_missing'; return $report }
    try {
        $configValue = [System.IO.File]::ReadAllText($Config) | ConvertFrom-Json
        $options = $configValue.runtimeOptions
        $required = @($options.frameworks)
        # The current build declares exactly these two10.0.0 frameworks, no roll-forward override.
        if ($options.tfm -ne 'net10.0' -or $required.Count -ne 2 -or
            @($required | Where-Object { $_.version -ne '10.0.0' }).Count -ne 0 -or
            (($required.name | Sort-Object) -join ',') -ne 'Microsoft.AspNetCore.App,Microsoft.NETCore.App' -or
            @($options.PSObject.Properties.Name | Where-Object { $_ -in @('rollForward', 'applyPatches', 'includedFrameworks', 'framework') }).Count -ne 0) {
            $report.code = 'runtime_config_unsupported'; return $report
        }
        $report['runtimeConfigSha256'] = Get-RuntimeConfigDigest $Config
    } catch { $report.code = 'runtime_config_invalid'; return $report }
    $executables = [ordered]@{ dotnet = $DotNet; postgres = (Join-Path $PgBin 'postgres.exe'); pg_dump = (Join-Path $PgBin 'pg_dump.exe'); pg_restore = (Join-Path $PgBin 'pg_restore.exe') }
    foreach ($name in $executables.Keys) {
        if (-not [System.IO.File]::Exists($executables[$name])) { $report.missing += $name }
    }
    if ($report.missing.Count -ne 0) { $report.exitCode = 1; $report.code = 'executable_missing'; return $report }
    foreach ($name in $executables.Keys) {
        if (-not (Test-RuntimeX64Pe $executables[$name])) { $report.exitCode = 1; $report.code = 'binary_architecture_invalid'; return $report }
    }
    $probe = Invoke-RuntimeVersionProbe $DotNet '--list-runtimes'
    if ($probe.code -ne 'ok') { $report.code = $probe.code; return $report }
    $inventory = Get-RuntimeFrameworkInventory $probe.output
    if ($inventory.code -ne 'ok') { $report.code = $inventory.code; return $report }
    $report.frameworks = $inventory.frameworks
    if ($inventory.missing.Count -ne 0) { $report.missing = $inventory.missing; $report.exitCode = 1; $report.code = 'framework_missing'; return $report }
    foreach ($name in @('postgres', 'pg_dump', 'pg_restore')) {
        $probe = Invoke-RuntimeVersionProbe $executables[$name] '--version'
        if ($probe.code -ne 'ok') { $report.code = $probe.code; return $report }
        if ($probe.output.Trim() -notmatch ('^' + [regex]::Escape($name) + ' \(PostgreSQL\) ([0-9]+\.[0-9]+)$')) {
            $report.code = 'probe_output_invalid'; return $report
        }
        $version = $Matches[1]; $report.postgres += @{ name = $name; version = $version }
        if ($version -ne $PgVersion) { $report.exitCode = 1; $report.code = 'postgres_version_incompatible'; return $report }
    }
    $report.ready = $true; $report.exitCode = 0; $report.code = 'requirements_present'
    return $report
}

if ($MyInvocation.InvocationName -eq '.') { return }
try { $result = Get-RackClickRuntimeReadiness $DotNetPath $PostgresBinPath $RuntimeConfigPath $PostgresVersion }
catch { $result = @{ schemaVersion = 1; ready = $false; exitCode = 2; code = 'verification_failed' } }
$result | ConvertTo-Json -Depth 8 -Compress
exit $result.exitCode
