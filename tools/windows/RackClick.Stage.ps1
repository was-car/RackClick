#requires -Version 5.1
# Shared staging helpers. Importing defines functions; it never starts a probe.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
. (Join-Path $PSScriptRoot 'Test-RuntimePrerequisites.ps1')

function Stop-StageCheck {
    param([string]$Code,[int]$ExitCode=2)
    $failure=New-Object InvalidOperationException($Code)
    $failure.Data['stageCode']=$Code; $failure.Data['stageExit']=$ExitCode
    throw $failure
}

function Get-StageLocalPath {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value) -or $Value -notmatch '^[A-Za-z]:[\\/]' -or $Value.Substring(2).Contains(':')) { Stop-StageCheck 'path_invalid' }
    foreach ($part in $Value.Substring(3).Split([char[]]@('\','/'))) {
        if ($part.Length -eq 0) { continue }
        # Conservative boundary: disallow tilde segments, including DOS8.3 aliases,
        # so textual root disjointness cannot be bypassed through a short name.
        if ($part -in @('.','..') -or $part.Contains('~') -or $part.EndsWith('.') -or $part.EndsWith(' ') -or $part.IndexOfAny([IO.Path]::GetInvalidFileNameChars()) -ge 0 -or $part -match '^(?i:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\..*)?$') { Stop-StageCheck 'path_invalid' }
    }
    if ((New-Object IO.DriveInfo($Value.Substring(0,3))).DriveType -eq [IO.DriveType]::Network) { Stop-StageCheck 'path_invalid' }
    $full=[IO.Path]::GetFullPath($Value).TrimEnd([char]'\')
    if ($full.Length -le 2) { Stop-StageCheck 'path_invalid' }
    return $full
}

function Assert-StageNoReparse {
    param([string]$Path)
    $item=Get-Item -LiteralPath $Path -Force
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { Stop-StageCheck 'reparse_path_rejected' }
        if ($item -is [IO.FileInfo]) { $item=$item.Directory } else { $item=$item.Parent }
    }
}

function Test-StageOverlap {
    param([string]$First,[string]$Second)
    return $First.Equals($Second,[StringComparison]::OrdinalIgnoreCase) -or $First.StartsWith($Second+'\',[StringComparison]::OrdinalIgnoreCase) -or $Second.StartsWith($First+'\',[StringComparison]::OrdinalIgnoreCase)
}

function Invoke-StageChild {
    param([string]$Script,[string[]]$Values)
    $process=New-Object Diagnostics.Process
    try {
        $start=New-Object Diagnostics.ProcessStartInfo
        $start.FileName=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
        $arguments=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$Script)+$Values
        # All variable arguments are paths validated above or hexadecimal digests;
        # double quotes are forbidden by the path contract. Trailing slashes are normalized.
        $start.Arguments=($arguments | ForEach-Object { '"'+$_+'"' }) -join ' '
        $start.UseShellExecute=$false; $start.CreateNoWindow=$true
        $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
        $process.StartInfo=$start
        if (-not $process.Start()) { Stop-StageCheck 'child_start_failed' }
        $output=$process.StandardOutput.ReadToEndAsync(); $errorOutput=$process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(80000)) { $process.Kill(); $process.WaitForExit(); Stop-StageCheck 'child_timeout' }
        if ($errorOutput.Result.Length -ne 0) { Stop-StageCheck 'child_output_invalid' }
        try { $data=$output.Result | ConvertFrom-Json } catch { Stop-StageCheck 'child_output_invalid' }
        if ($data.exitCode -ne $process.ExitCode) { Stop-StageCheck 'child_output_invalid' }
        return $data
    } finally { $process.Dispose() }
}

function Get-StageServerFileCount {
    param([int]$Schema)
    # Conteo cerrado por esquema; no aceptar intermediarios sin un perfil revisado.
    if ($Schema -eq 48) {return 58}
    if ($Schema -eq 45) {return 55}
    if ($Schema -eq 43) {return 53}
    if ($Schema -eq 15) {return 25}
    if ($Schema -eq 14) {return 24}
    if ($Schema -in @(9,10,11,12,13)) {return 9+$Schema}
    Stop-StageCheck 'manifest_distribution_unsupported'
}

function Get-StageVerifiedFileCount {
    param([int]$Schema)
    return (Get-StageServerFileCount $Schema)+18
}

function Invoke-StageIntegrity {
    param([string]$Manifest,[string]$Expected,[string]$Server,[string]$Frontend)
    $value=Invoke-StageChild (Join-Path $PSScriptRoot 'Test-ServerDistribution.ps1') @('-ManifestPath',$Manifest,'-ExpectedManifestSha256',$Expected,'-ServerPath',$Server,'-FrontendPath',$Frontend)
    # El conteo esperado depende del esquema que el verificador acaba de validar, no de un rango fijo.
    if ($value.exitCode -ne 0 -or -not $value.valid -or $value.schema -isnot [int] -or $value.serverFiles -ne (Get-StageServerFileCount $value.schema) -or $value.frontendFiles -ne 18 -or $value.verifiedFiles -ne ($value.serverFiles+$value.frontendFiles)) {
        $status=2; if ($value.exitCode -eq 1) { $status=1 }
        Stop-StageCheck ('integrity_'+$value.code) $status
    }
    return $value
}

function Get-StageSchema {
    param([string]$Stage)
    # Call only while holding the externally authenticated manifest read lock.
    $manifest=[IO.File]::ReadAllText((Join-Path $Stage 'manifest.json'),[Text.Encoding]::UTF8)|ConvertFrom-Json
    if ($manifest.schema -isnot [int] -or $manifest.schema -notin @(9,10,11,12,13,14,15,43,45,48)) {Stop-StageCheck 'manifest_distribution_unsupported'}
    return [int]$manifest.schema
}

function Invoke-StageRuntime {
    param([string]$DotNet,[string]$Pg,[string]$Server)
    $value=Invoke-StageChild (Join-Path $PSScriptRoot 'Test-RuntimePrerequisites.ps1') @('-DotNetPath',$DotNet,'-PostgresBinPath',$Pg,'-RuntimeConfigPath',(Join-Path $Server 'RackClick.Server.runtimeconfig.json'),'-PostgresVersion','17.11')
    if ($value.exitCode -ne 0 -or -not $value.ready) {
        $status=2; if ($value.exitCode -eq 1) { $status=1 }
        Stop-StageCheck ('runtime_'+$value.code) $status
    }
    return $value
}

function New-StageDirectoryExclusive {
    param([string]$Path)
    if (-not ('RackClick.StageNative' -as [type])) {
        Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; namespace RackClick { public static class StageNative { [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] [return: MarshalAs(UnmanagedType.Bool)] public static extern bool CreateDirectory(string path, IntPtr security); } }'
    }
    if (-not [RackClick.StageNative]::CreateDirectory($Path,[IntPtr]::Zero)) {
        $nativeError=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
        if ($nativeError -eq 183) { Stop-StageCheck 'destination_exists' 1 }
        Stop-StageCheck 'destination_create_failed'
    }
}

function Copy-StageFileExclusive {
    param([string]$Source,[string]$Target)
    Assert-StageNoReparse $Source
    Assert-StageNoReparse ([IO.Path]::GetDirectoryName($Target))
    $inputStream=$null; $outputStream=$null
    try {
        $inputStream=[IO.File]::Open($Source,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        $outputStream=[IO.File]::Open($Target,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        $inputStream.CopyTo($outputStream); $outputStream.Flush($true)
    } finally {
        if ($null -ne $outputStream) { $outputStream.Dispose() }
        if ($null -ne $inputStream) { $inputStream.Dispose() }
    }
}

function Write-StageJsonExclusive {
    param([string]$Path,$Value)
    $stream=$null
    try {
        $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($Value | ConvertTo-Json -Depth 12 -Compress)+[Environment]::NewLine)
        $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true)
    } finally { if ($null -ne $stream) { $stream.Dispose() } }
}

function Set-StageState {
    param([IO.FileStream]$Stream,$Value)
    $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($Value | ConvertTo-Json -Depth 6 -Compress)+[Environment]::NewLine)
    $Stream.Position=0; $Stream.SetLength(0); $Stream.Write($bytes,0,$bytes.Length); $Stream.Flush($true)
}
