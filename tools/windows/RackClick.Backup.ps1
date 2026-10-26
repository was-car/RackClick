#requires -Version 5.1
# Shared implementation for explicit, loopback-only native backup/restore operations.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Test-RuntimePrerequisites.ps1') -PostgresBinPath $PostgresBinPath

function Stop-RackClickBackup {
    param([string]$Code, [int]$ExitCode = 2)
    $errorValue = New-Object System.InvalidOperationException($Code)
    $errorValue.Data['code'] = $Code; $errorValue.Data['exitCode'] = $ExitCode
    throw $errorValue
}

function Assert-BackupPath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path) -or $Path -notmatch '^[A-Za-z]:[\\/]' -or
        $Path.Substring(2).Contains(':') -or $Path.Contains('"') -or $Path.IndexOfAny([char[]]"`r`n") -ge 0) {
        Stop-RackClickBackup 'path_invalid'
    }
    foreach ($segment in $Path.Substring(3).Split([char[]]@('\', '/'))) {
        if ($segment -in @('.', '..') -or $segment.EndsWith('.') -or $segment.EndsWith(' ')) { Stop-RackClickBackup 'path_invalid' }
    }
    $full = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    if ($full.Length -le 2 -or (New-Object IO.DriveInfo($full.Substring(0, 3))).DriveType -ne [IO.DriveType]::Fixed) { Stop-RackClickBackup 'path_not_local_fixed' }
    return $full
}

function Assert-BackupNoReparse {
    param([string]$Path)
    $item = Get-Item -LiteralPath $Path -Force
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { Stop-RackClickBackup 'reparse_rejected' }
        if ($item -is [IO.FileInfo]) { $item = $item.Directory } else { $item = $item.Parent }
    }
}

function New-BackupPrivateDirectory {
    param([string]$Path)
    $Path = Assert-BackupPath $Path
    if ([IO.File]::Exists($Path) -or [IO.Directory]::Exists($Path)) { Stop-RackClickBackup 'destination_exists' 1 }
    $parent = [IO.Path]::GetDirectoryName($Path)
    if (-not [IO.Directory]::Exists($parent)) { Stop-RackClickBackup 'destination_parent_missing' }
    Assert-BackupNoReparse $parent
    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $security = New-Object Security.AccessControl.DirectorySecurity
    $security.SetOwner($sid); $security.SetAccessRuleProtection($true, $false)
    foreach ($identity in @($sid, (New-Object Security.Principal.SecurityIdentifier('S-1-5-18')))) {
        $rule = New-Object Security.AccessControl.FileSystemAccessRule($identity, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
        $security.AddAccessRule($rule)
    }
    # Atomic exclusive creation with the private ACL from the first instant; never adopt a race winner.
    if (-not ('RackClick.BackupNative' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace RackClick {
    public static class BackupNative {
        [StructLayout(LayoutKind.Sequential)] struct SecurityAttributes { public int Length; public IntPtr Descriptor; public int Inherit; }
        [DllImport("kernel32.dll", EntryPoint="CreateDirectoryW", CharSet=CharSet.Unicode, SetLastError=true)]
        [return: MarshalAs(UnmanagedType.Bool)] static extern bool CreateDirectory(string path, ref SecurityAttributes security);
        public static int CreatePrivateDirectory(string path, byte[] descriptor) {
            var pinned = GCHandle.Alloc(descriptor, GCHandleType.Pinned);
            try {
                var attributes = new SecurityAttributes { Length=Marshal.SizeOf(typeof(SecurityAttributes)), Descriptor=pinned.AddrOfPinnedObject(), Inherit=0 };
                return CreateDirectory(path, ref attributes) ? 0 : Marshal.GetLastWin32Error();
            } finally { pinned.Free(); }
        }
    }
}
'@
    }
    $nativeError = [RackClick.BackupNative]::CreatePrivateDirectory($Path, $security.GetSecurityDescriptorBinaryForm())
    if ($nativeError -eq 183) { Stop-RackClickBackup 'destination_exists' 1 }
    if ($nativeError -ne 0) { Stop-RackClickBackup 'destination_create_failed' }
    Assert-BackupPrivateAcl $Path
    return $Path
}

function Assert-BackupPrivateAcl {
    param([string]$Path)
    Assert-BackupNoReparse $Path
    $current = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    if ([IO.Directory]::Exists($Path)) { $acl = [IO.Directory]::GetAccessControl($Path) }
    else { $acl = [IO.File]::GetAccessControl($Path) }
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin @($current, 'S-1-5-18')) { Stop-RackClickBackup 'private_acl_required' }
    $allowed = @($current, 'S-1-5-18'); $currentAllowed = $false
    foreach ($rule in $acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -eq [Security.AccessControl.AccessControlType]::Allow) {
            if ($rule.IdentityReference.Value -notin $allowed) { Stop-RackClickBackup 'private_acl_required' }
            if ($rule.IdentityReference.Value -eq $current) { $currentAllowed = $true }
        }
    }
    if (-not $currentAllowed) { Stop-RackClickBackup 'private_acl_required' }
}

function Read-BackupProfile {
    param([string]$Path)
    $Path = Assert-BackupPath $Path
    if (-not [IO.File]::Exists($Path)) { Stop-RackClickBackup 'profile_missing' }
    Assert-BackupPrivateAcl $Path
    if ((Get-Item -LiteralPath $Path).Length -gt 16384) { Stop-RackClickBackup 'profile_invalid' }
    try { $profile = [IO.File]::ReadAllText($Path) | ConvertFrom-Json } catch { Stop-RackClickBackup 'profile_invalid' }
    $names = @($profile.PSObject.Properties.Name | Sort-Object)
    if (($names -join ',') -ne 'database,host,passwordFile,port,schemaVersion,user' -or $profile.schemaVersion -ne 1 -or
        $profile.host -cne '127.0.0.1' -or $profile.port -isnot [int] -or $profile.port -lt 1024 -or $profile.port -gt 65535 -or
        $profile.database -isnot [string] -or $profile.database -cnotmatch '^[a-z_][a-z0-9_]{0,62}$' -or
        $profile.user -isnot [string] -or $profile.user -cnotmatch '^[a-z_][a-z0-9_]{0,62}$' -or $profile.passwordFile -isnot [string]) {
        Stop-RackClickBackup 'profile_invalid'
    }
    $secretPath = Assert-BackupPath $profile.passwordFile
    if (-not [IO.File]::Exists($secretPath)) { Stop-RackClickBackup 'password_file_missing' }
    Assert-BackupPrivateAcl $secretPath
    if ((Get-Item -LiteralPath $secretPath).Length -gt 4096) { Stop-RackClickBackup 'password_file_invalid' }
    $password = [IO.File]::ReadAllText($secretPath).TrimEnd([char[]]"`r`n")
    if ($password.Length -lt 1 -or $password.Length -gt 1024 -or $password.IndexOfAny([char[]]"`r`n`0") -ge 0) { Stop-RackClickBackup 'password_file_invalid' }
    return @{ host = '127.0.0.1'; port = [int]$profile.port; database = $profile.database; user = $profile.user; password = $password }
}

function Assert-BackupPostgresTools {
    param([string]$Path)
    $Path = Assert-BackupPath $Path
    Assert-BackupNoReparse $Path
    foreach ($name in @('postgres', 'psql', 'pg_dump', 'pg_restore')) {
        $executable = Join-Path $Path ($name + '.exe')
        if (-not [IO.File]::Exists($executable)) { Stop-RackClickBackup 'postgres_tool_missing' 1 }
        Assert-BackupNoReparse $executable
        if (-not (Test-RuntimeX64Pe $executable)) { Stop-RackClickBackup 'postgres_architecture_invalid' 1 }
        $probe = Invoke-RuntimeVersionProbe $executable '--version'
        if ($probe.code -ne 'ok' -or $probe.output.Trim() -cne ($name + ' (PostgreSQL) 17.11')) { Stop-RackClickBackup 'postgres_version_required_17_11' 1 }
    }
    return $Path
}

function Write-BackupNewText {
    param([string]$Path, [string]$Text)
    $stream = $null; $writer = $null
    try {
        $stream = New-Object IO.FileStream($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        $writer = New-Object IO.StreamWriter($stream, (New-Object Text.UTF8Encoding($false)))
        $writer.Write($Text); $writer.Flush(); $stream.Flush($true)
    } finally { if ($null -ne $writer) { $writer.Dispose() } elseif ($null -ne $stream) { $stream.Dispose() } }
}

function Invoke-BackupPg {
    param([string]$Executable, [string[]]$Arguments, [hashtable]$Profile, [string]$Sql = '', [int]$TimeoutMilliseconds = 120000, [string]$WorkingDirectory = '')
    $temporary = $null; $process = $null
    try {
        $temporary = New-BackupPrivateDirectory (Join-Path ([IO.Path]::GetTempPath()) ('rackclick-pg-' + [guid]::NewGuid().ToString('N')))
        $passfile = Join-Path $temporary 'password.pgpass'
        $escaped = $Profile.password.Replace('\', '\\').Replace(':', '\:')
        Write-BackupNewText $passfile ("127.0.0.1:$($Profile.port):*:$($Profile.user):$escaped`n")
        Assert-BackupPrivateAcl $passfile
        $start = New-Object Diagnostics.ProcessStartInfo
        $start.FileName = $Executable
        if ($WorkingDirectory.Length -gt 0) {
            $workingPath = Assert-BackupPath $WorkingDirectory
            if (-not [IO.Directory]::Exists($workingPath)) { Stop-RackClickBackup 'working_directory_missing' }
            Assert-BackupNoReparse $workingPath
            # Windows process creation accepts Unicode cwd; PG17 archive filename argv is not Unicode-safe.
            $start.WorkingDirectory = $workingPath
        }
        # All callers use fixed options, restricted identifiers and paths rejecting quotes/newlines.
        $quoted = foreach ($argument in $Arguments) { '"' + [regex]::Replace($argument, '(\\+)$', '$1$1') + '"' }
        $start.Arguments = $quoted -join ' '
        $start.UseShellExecute = $false; $start.CreateNoWindow = $true
        $start.RedirectStandardInput = $true; $start.RedirectStandardOutput = $true; $start.RedirectStandardError = $true
        foreach ($key in @($start.EnvironmentVariables.Keys)) { if ([string]$key -match '^PG') { $start.EnvironmentVariables.Remove($key) } }
        $start.EnvironmentVariables['PGPASSFILE'] = $passfile
        $start.EnvironmentVariables['PGCLIENTENCODING'] = 'UTF8'
        $start.EnvironmentVariables['PGCONNECT_TIMEOUT'] = '5'
        $start.EnvironmentVariables['PGAPPNAME'] = 'RackClick-native-backup'
        $process = New-Object Diagnostics.Process; $process.StartInfo = $start
        if (-not $process.Start()) { Stop-RackClickBackup 'postgres_start_failed' 1 }
        $output = $process.StandardOutput.ReadToEndAsync(); $errors = $process.StandardError.ReadToEndAsync()
        if ($Sql.Length -gt 0) { $process.StandardInput.Write($Sql) }
        $process.StandardInput.Close()
        if (-not $process.WaitForExit($TimeoutMilliseconds)) {
            $process.Kill(); $process.WaitForExit(); Stop-RackClickBackup 'postgres_timeout' 1
        }
        # Never propagate PostgreSQL stderr: it can contain SQL or authentication details.
        if ($process.ExitCode -ne 0) { Stop-RackClickBackup 'postgres_command_failed' 1 }
        return $output.Result.Trim()
    } finally {
        if ($null -ne $process) { $process.Dispose() }
        if ($null -ne $temporary) {
            $ownedFile = Join-Path $temporary 'password.pgpass'
            if ([IO.File]::Exists($ownedFile)) { [IO.File]::Delete($ownedFile) }
            # Exact new UUID directory only, never a recursive delete or another user's files.
            [IO.Directory]::Delete($temporary, $false)
        }
    }
}

function Get-BackupConnectionArguments {
    param([hashtable]$Profile, [string]$Database)
    return @('-w', '-h', '127.0.0.1', '-p', [string]$Profile.port, '-U', $Profile.user, '-d', $Database)
}

function Assert-BackupServerVersion {
    param([string]$Bin, [hashtable]$Profile)
    $arguments = @('-X', '-A', '-t', '-v', 'ON_ERROR_STOP=1') + (Get-BackupConnectionArguments $Profile $Profile.database)
    $version = Invoke-BackupPg (Join-Path $Bin 'psql.exe') $arguments $Profile 'SHOW server_version_num;'
    if ($version -cne '170011') { Stop-RackClickBackup 'postgres_server_version_required_17_11' 1 }
}

function Read-BackupManifest {
    param([string]$Path, [string]$ExpectedHash)
    $manifestHandle = $null; $dumpHandle = $null
    try {
    $Path = Assert-BackupPath $Path
    if ($ExpectedHash -notmatch '^[0-9a-fA-F]{64}$') { Stop-RackClickBackup 'manifest_reference_required' }
    if (-not [IO.Directory]::Exists($Path)) { Stop-RackClickBackup 'backup_missing' }
    Assert-BackupNoReparse $Path
    $files = @((Get-Item -LiteralPath $Path -Force).GetFileSystemInfos())
    foreach ($file in $files) {
        if (($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { Stop-RackClickBackup 'reparse_rejected' }
    }
    if ($files.Count -ne 2 -or @($files | Where-Object { $_ -isnot [IO.FileInfo] }).Count -ne 0 -or
        ((@($files.Name | Sort-Object)) -join ',') -cne 'data.dump,manifest.json') { Stop-RackClickBackup 'backup_files_invalid' }
    $manifestPath = Join-Path $Path 'manifest.json'
    $dumpPath = Join-Path $Path 'data.dump'
    # Deny writes/deletes from before hash/parse until pg_restore finishes (caller owns these handles).
    $manifestHandle = [IO.File]::Open($manifestPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    $dumpHandle = [IO.File]::Open($dumpPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    if ((Get-Item -LiteralPath $manifestPath).Length -gt 16384 -or (Get-RuntimeConfigDigest $manifestPath) -cne $ExpectedHash.ToLowerInvariant()) { Stop-RackClickBackup 'manifest_hash_mismatch' }
    try { $manifest = [IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json } catch { Stop-RackClickBackup 'manifest_invalid' }
    if ((($manifest.PSObject.Properties.Name | Sort-Object) -join ',') -cne 'createdUtc,dumpBytes,dumpFile,dumpSha256,format,kind,postgresVersion,schemaVersion' -or
        $manifest.schemaVersion -ne 1 -or $manifest.kind -cne 'RackClickDatabaseBackup' -or $manifest.postgresVersion -cne '17.11' -or
        $manifest.format -cne 'custom' -or $manifest.dumpFile -cne 'data.dump' -or $manifest.dumpSha256 -notmatch '^[0-9a-f]{64}$' -or
        ($manifest.dumpBytes -isnot [int] -and $manifest.dumpBytes -isnot [long]) -or $manifest.dumpBytes -lt 5 -or $manifest.createdUtc -isnot [string]) { Stop-RackClickBackup 'manifest_invalid' }
    if ((Get-Item -LiteralPath $dumpPath).Length -ne $manifest.dumpBytes -or (Get-RuntimeConfigDigest $dumpPath) -cne $manifest.dumpSha256) { Stop-RackClickBackup 'dump_hash_mismatch' }
    return @{ path = $dumpPath; hash = $manifest.dumpSha256; manifestHandle = $manifestHandle; dumpHandle = $dumpHandle }
    } catch {
        if ($null -ne $dumpHandle) { $dumpHandle.Dispose() }
        if ($null -ne $manifestHandle) { $manifestHandle.Dispose() }
        throw
    }
}
