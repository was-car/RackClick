#requires -Version 5.1
[CmdletBinding()]
param([string]$OutputDirectory='')
$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$source=Join-Path $root 'tools\windows\server-install\Invoke-RackClickScheduledBackup.ps1'
. (Join-Path $root 'tools\windows\RackClick.Process.ps1')
$tokens=$null;$parseErrors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$parseErrors)
if ($parseErrors.Count -gt 0) {throw 'scheduled_parser_failed'}
$functions=@('Stop-ScheduledBackupCheck','Get-ScheduledBackupDestination','Read-ScheduledBackupChildReport','Open-ScheduledBackupLock','Publish-ScheduledBackupReceipt')
foreach ($node in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$false)) {if ($node.Name -in $functions) {Invoke-Expression $node.Extent.Text}}
if ($OutputDirectory.Length -eq 0) {$OutputDirectory=Join-Path $root ('.local\scheduled-backup-tests-'+[guid]::NewGuid().ToString('N'))}
$testRoot=New-RackClickProcessPrivateDirectory $OutputDirectory
$unicodeRoot=New-RackClickProcessPrivateDirectory (Join-Path $testRoot 'Pruebas-Ñ-漢字')
$results=@()
function Expect-ScheduledFailure {
 param([string]$Name,[scriptblock]$Action,[string]$Code)
 try {& $Action;throw 'unexpected_test_pass'} catch {if (-not $_.Exception.Data.Contains('scheduledCode') -or $_.Exception.Data['scheduledCode'] -cne $Code) {throw}}
 $script:results+=@{name=$Name;passed=$true;expectedCode=$Code}
}
$utc=[DateTime]::SpecifyKind([DateTime]'2026-10-19T12:34:56',[DateTimeKind]::Utc)
$path=Get-ScheduledBackupDestination $unicodeRoot $utc ([guid]'11111111-2222-3333-4444-555555555555')
if ($path -cne (Join-Path $unicodeRoot 'backups\daily-20261019T123456000Z-11111111222233334444555555555555')) {throw 'unicode_destination_failed'}
$results+=@{name='Unicode destination preserved';passed=$true}
$hash='a'*64
$valid=@{valid=$true;success=$true;exitCode=0;code='backup_complete';manifestSha256=$hash;backupPath=$path}|ConvertTo-Json -Compress
$answer=Read-ScheduledBackupChildReport $valid '' 0 $path
$results+=@{name='Coherent child JSON accepted';passed=$true}
Expect-ScheduledFailure 'Malformed child JSON rejected' {Read-ScheduledBackupChildReport '{broken' '' 0 $path} 'scheduled_backup_child_json_invalid'
Expect-ScheduledFailure 'Process failure cannot claim JSON success' {Read-ScheduledBackupChildReport $valid '' 1 $path} 'scheduled_backup_child_receipt_invalid'
$bad=@{valid=$true;success=$true;exitCode=0;code='backup_complete';manifestSha256='bad';backupPath=$path}|ConvertTo-Json -Compress
Expect-ScheduledFailure 'Invalid manifest hash rejected' {Read-ScheduledBackupChildReport $bad '' 0 $path} 'scheduled_backup_child_receipt_invalid'
Expect-ScheduledFailure 'Unexpected stderr rejected' {Read-ScheduledBackupChildReport $valid 'failure' 0 $path} 'scheduled_backup_child_output_invalid'
$lockPath=Join-Path $unicodeRoot 'scheduled-backup.lock'
$lock=Open-ScheduledBackupLock $lockPath
try {Expect-ScheduledFailure 'Concurrent backup lock rejected' {Open-ScheduledBackupLock $lockPath} 'scheduled_backup_in_progress'} finally {$lock.Dispose()}
$lock=Open-ScheduledBackupLock $lockPath;$lock.Dispose()
$results+=@{name='Lock reusable after release';passed=$true}
$receiptPath=Join-Path $unicodeRoot 'latest-backup.json'
$receipt=@{schemaVersion=1;valid=$true;success=$true;exitCode=0;code='scheduled_backup_complete';manifestPath=(Join-Path $path 'manifest.json');manifestSha256=$hash;createdUtc=$utc.ToString('o');backupPath=$path}
Publish-ScheduledBackupReceipt $receiptPath $receipt
$receipt.manifestSha256='b'*64
Publish-ScheduledBackupReceipt $receiptPath $receipt
$actual=[IO.File]::ReadAllText($receiptPath,[Text.Encoding]::UTF8)|ConvertFrom-Json
if ($actual.backupPath -cne $path -or $actual.manifestSha256 -cne ('b'*64)) {throw 'atomic_receipt_failed'}
$results+=@{name='PS5.1 atomic receipt replacement preserves Unicode';passed=$true}
$report=@{schemaVersion=1;valid=$true;exitCode=0;checks=$results;outputDirectory=$testRoot;scope='Actual PS5.1 filesystem locks/atomic replacement and pure child-report guards; no PostgreSQL, SCM, task registration or elevation'}
$report|ConvertTo-Json -Depth 6|Set-Content (Join-Path $testRoot 'test-result.json') -Encoding UTF8
$report|ConvertTo-Json -Depth 6
