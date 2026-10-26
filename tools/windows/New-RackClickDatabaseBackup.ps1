#requires -Version 5.1
[CmdletBinding()]
param([string]$PostgresBinPath = '', [string]$ProfilePath = '', [string]$DestinationPath = '')
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
. (Join-Path $PSScriptRoot 'RackClick.Backup.ps1')
$report = [ordered]@{ schemaVersion = 1; valid = $false; success = $false; exitCode = 2; code = 'backup_failed'; manifestSha256 = ''; backupPath = ''; scope = 'loopback database backup, not a complete Windows installation package' }
$destination = $null
try {
    $profile = Read-BackupProfile $ProfilePath
    $bin = Assert-BackupPostgresTools $PostgresBinPath
    $destination = New-BackupPrivateDirectory $DestinationPath
    $report.backupPath = $destination
    Write-BackupNewText (Join-Path $destination 'INCOMPLETE.json') '{"complete":false}'
    Assert-BackupServerVersion $bin $profile
    $partial = Join-Path $destination 'data.dump.partial'
    $arguments = (Get-BackupConnectionArguments $profile $profile.database) + @('--format=custom', '--no-owner', '--no-acl', '--file', 'data.dump.partial')
    $null = Invoke-BackupPg (Join-Path $bin 'pg_dump.exe') $arguments $profile -WorkingDirectory $destination
    if (-not [IO.File]::Exists($partial) -or (Get-Item -LiteralPath $partial).Length -lt 5) { Stop-RackClickBackup 'dump_empty' 1 }
    $digest = Get-RuntimeConfigDigest $partial
    [IO.File]::Move($partial, (Join-Path $destination 'data.dump'))
    $manifest = [ordered]@{ schemaVersion = 1; kind = 'RackClickDatabaseBackup'; postgresVersion = '17.11'; format = 'custom'; dumpFile = 'data.dump'; dumpBytes = (Get-Item -LiteralPath (Join-Path $destination 'data.dump')).Length; dumpSha256 = $digest; createdUtc = [DateTime]::UtcNow.ToString('o') }
    Write-BackupNewText (Join-Path $destination 'manifest.json') ($manifest | ConvertTo-Json -Compress)
    [IO.File]::Delete((Join-Path $destination 'INCOMPLETE.json'))
    $report.manifestSha256 = Get-RuntimeConfigDigest (Join-Path $destination 'manifest.json')
    $report.valid = $true; $report.success = $true; $report.exitCode = 0; $report.code = 'backup_complete'
} catch {
    if ($_.Exception.Data.Contains('code')) { $report.code = $_.Exception.Data['code']; $report.exitCode = $_.Exception.Data['exitCode'] }
}
$report | ConvertTo-Json -Compress
exit $report.exitCode
