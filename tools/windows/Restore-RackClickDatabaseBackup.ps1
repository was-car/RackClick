#requires -Version 5.1
[CmdletBinding()]
param([string]$PostgresBinPath = '', [string]$ProfilePath = '', [string]$BackupPath = '', [string]$ExpectedManifestSha256 = '', [string]$NewDatabaseName = '')
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
. (Join-Path $PSScriptRoot 'RackClick.Backup.ps1')
$report = [ordered]@{ schemaVersion = 1; valid = $false; success = $false; exitCode = 2; code = 'restore_failed'; newDatabaseName = $NewDatabaseName; newDatabaseCreated = $false; applicationStartAllowed = $false; scope = 'new isolated database only; application/session recovery acceptance remains separate' }
$backup = $null
try {
    if ($NewDatabaseName -cnotmatch '^rc_restore_[a-z0-9_]{1,48}$') { Stop-RackClickBackup 'new_database_name_invalid' }
    $backup = Read-BackupManifest $BackupPath $ExpectedManifestSha256
    $profile = Read-BackupProfile $ProfilePath
    $bin = Assert-BackupPostgresTools $PostgresBinPath
    Assert-BackupServerVersion $bin $profile
    $arguments = @('-X', '-A', '-t', '-v', 'ON_ERROR_STOP=1') + (Get-BackupConnectionArguments $profile $profile.database)
    $permitted = Invoke-BackupPg (Join-Path $bin 'psql.exe') $arguments $profile 'SELECT rolcreatedb FROM pg_roles WHERE rolname = current_user;'
    if ($permitted -cne 't') { Stop-RackClickBackup 'createdb_permission_required' 1 }
    $exists = Invoke-BackupPg (Join-Path $bin 'psql.exe') $arguments $profile ("SELECT count(*) FROM pg_database WHERE datname = '$NewDatabaseName';")
    if ($exists -cne '0') { Stop-RackClickBackup 'new_database_exists' 1 }
    # SQL identifiers are restricted ASCII; no input accepts SQL fragments. CREATE has no overwrite path.
    $null = Invoke-BackupPg (Join-Path $bin 'psql.exe') $arguments $profile ("CREATE DATABASE $NewDatabaseName OWNER $($profile.user) TEMPLATE template0 ENCODING 'UTF8';")
    $report.newDatabaseCreated = $true
    $null = Invoke-BackupPg (Join-Path $bin 'psql.exe') $arguments $profile ("REVOKE ALL ON DATABASE $NewDatabaseName FROM PUBLIC;")
    $restoreArguments = (Get-BackupConnectionArguments $profile $NewDatabaseName) + @('--single-transaction', '--exit-on-error', '--no-owner', '--no-acl', 'data.dump')
    $null = Invoke-BackupPg (Join-Path $bin 'pg_restore.exe') $restoreArguments $profile -WorkingDirectory ([IO.Path]::GetDirectoryName($backup.path))
    # No runtime grants or session revocation are guessed here; the new DB stays an isolated restore.
    $report.valid = $true; $report.success = $true; $report.exitCode = 0; $report.code = 'restore_complete_isolated'
} catch {
    if ($_.Exception.Data.Contains('code')) { $report.code = $_.Exception.Data['code']; $report.exitCode = $_.Exception.Data['exitCode'] }
} finally {
    if ($null -ne $backup) { $backup.dumpHandle.Dispose(); $backup.manifestHandle.Dispose() }
}
$report | ConvertTo-Json -Compress
exit $report.exitCode
