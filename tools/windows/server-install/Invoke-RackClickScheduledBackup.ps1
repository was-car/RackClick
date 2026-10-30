#requires -Version 5.1
<# Automatic DB backup under the profile's standard identity. No task registration,
   retention/deletion, service control or automatic recovery claims. #>
[CmdletBinding()]
param([string]$ManifestPath='',[string]$ExpectedManifestSha256='')
$scheduledInputs=@{manifest=$ManifestPath;sha=$ExpectedManifestSha256}
. (Join-Path $PSScriptRoot 'RackClick.ServerRuntime.ps1')
function Stop-ScheduledBackupCheck {
 param([string]$Code,[int]$ExitCode=2)
 $failure=New-Object InvalidOperationException($Code)
 $failure.Data['scheduledCode']=$Code;$failure.Data['scheduledExit']=$ExitCode
 throw $failure
}
function Get-ScheduledBackupDestination {
 param([string]$RuntimeRoot,[DateTime]$Utc,[guid]$Id)
 if ($Utc.Kind -ne [DateTimeKind]::Utc -or $Id -eq [guid]::Empty) {Stop-ScheduledBackupCheck 'scheduled_backup_identity_invalid'}
 return Join-Path (Join-Path $RuntimeRoot 'backups') ('daily-'+$Utc.ToString('yyyyMMddTHHmmssfffZ',[Globalization.CultureInfo]::InvariantCulture)+'-'+$Id.ToString('N'))
}
function Read-ScheduledBackupChildReport {
 param([string]$Stdout,[string]$Stderr,[int]$ActualExitCode,[string]$ExpectedPath)
 if ($Stdout.Length -gt 65536 -or $Stderr.Length -ne 0) {Stop-ScheduledBackupCheck 'scheduled_backup_child_output_invalid'}
 try {$value=$Stdout|ConvertFrom-Json} catch {Stop-ScheduledBackupCheck 'scheduled_backup_child_json_invalid'}
 if ($value -isnot [pscustomobject]) {Stop-ScheduledBackupCheck 'scheduled_backup_child_json_invalid'}
 foreach ($name in @('valid','success','exitCode','code','manifestSha256','backupPath')) {if ($null -eq $value.PSObject.Properties[$name]) {Stop-ScheduledBackupCheck 'scheduled_backup_child_receipt_invalid'}}
 if ($value.valid -isnot [bool] -or $value.success -isnot [bool] -or $value.exitCode -isnot [int] -or
     $ActualExitCode -ne 0 -or $value.exitCode -ne $ActualExitCode -or -not $value.valid -or -not $value.success -or $value.code -cne 'backup_complete' -or
     $value.manifestSha256 -isnot [string] -or $value.manifestSha256 -cnotmatch '^[a-f0-9]{64}$' -or $value.backupPath -cne $ExpectedPath) {Stop-ScheduledBackupCheck 'scheduled_backup_child_receipt_invalid'}
 return $value
}
function Open-ScheduledBackupLock {
 param([string]$Path)
 Assert-RackClickProcessPrivateAcl ([IO.Path]::GetDirectoryName($Path))
 if ([IO.File]::Exists($Path)) {Assert-RackClickProcessPrivateAcl $Path}
 try {$stream=[IO.File]::Open($Path,'OpenOrCreate','ReadWrite','None')}
 catch [IO.IOException] {
  $cause=$_.Exception;while ($null -ne $cause.InnerException) {$cause=$cause.InnerException}
  if (($cause.HResult -band 0xffff) -in @(32,33)) {Stop-ScheduledBackupCheck 'scheduled_backup_in_progress' 1}
  throw
 }
 try {Assert-RackClickProcessPrivateAcl $Path;return $stream} catch {$stream.Dispose();throw}
}
function Publish-ScheduledBackupReceipt {
 param([string]$Path,$Value)
 $parent=[IO.Path]::GetDirectoryName($Path);Assert-RackClickProcessPrivateAcl $parent
 if ([IO.File]::Exists($Path)) {Assert-RackClickProcessPrivateAcl $Path}
 $temporary=Join-Path $parent ('scheduled-receipt-'+[guid]::NewGuid().ToString('N')+'.tmp')
 $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($Value|ConvertTo-Json -Depth 5 -Compress)+[Environment]::NewLine)
 $stream=[IO.File]::Open($temporary,'CreateNew','Write','None')
 try {$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)} finally {$stream.Dispose()}
 Assert-RackClickProcessPrivateAcl $temporary
 if ([IO.File]::Exists($Path)) {
  # PS5.1 requires a genuine CLR null backup name, not an empty-string coercion.
  [IO.File]::Replace($temporary,$Path,[Management.Automation.Language.NullString]::Value)
 } else {[IO.File]::Move($temporary,$Path)}
 Assert-RackClickProcessPrivateAcl $Path
 if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($Path)) -cne [Convert]::ToBase64String($bytes)) {Stop-ScheduledBackupCheck 'scheduled_backup_receipt_verify_failed'}
}
$profile=$null;$lock=$null;$child=$null;$backup=$null;$runRoot='';$originalTemp=$env:TEMP;$originalTmp=$env:TMP
$report=[ordered]@{schemaVersion=1;valid=$false;success=$false;exitCode=2;code='scheduled_backup_failed';manifestPath='';manifestSha256='';createdUtc=[DateTime]::UtcNow.ToString('o');backupPath=''}
try {
 $profile=Read-ServerProfile $scheduledInputs.manifest $scheduledInputs.sha
 $lock=Open-ScheduledBackupLock (Join-Path $profile.root 'control\scheduled-backup.lock')
 $destination=Get-ScheduledBackupDestination $profile.root ([DateTime]::UtcNow) ([guid]::NewGuid())
 if (Test-Path -LiteralPath $destination) {Stop-ScheduledBackupCheck 'scheduled_backup_destination_exists'}
 $env:TEMP=Join-Path $profile.root 'temp';$env:TMP=$env:TEMP
 $runRoot=New-RackClickProcessPrivateDirectory (Join-Path $profile.root ('logs\scheduled-backup-'+[guid]::NewGuid().ToString('N')))
 $entry=Join-Path $PSScriptRoot 'Invoke-RackClickServerRuntime.ps1';Assert-RackClickProcessNoReparse $entry
 $args=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$entry,'-Operation','Backup','-ManifestPath',$scheduledInputs.manifest,'-ExpectedManifestSha256',$scheduledInputs.sha,'-BackupPath',$destination)
 $child=Start-RackClickOwnedProcess -Executable (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -Arguments $args -WorkingDirectory $profile.root -Environment @{} -LogDirectory $runRoot -Label 'database-backup'
 $result=Wait-RackClickOwnedProcess -Handle $child -TimeoutSeconds 600
 $answer=Read-ScheduledBackupChildReport $result.stdout $result.stderr $result.exitCode $destination
 $backup=Read-BackupManifest -Path $destination -ExpectedHash $answer.manifestSha256
 $report.valid=$true;$report.success=$true;$report.exitCode=0;$report.code='scheduled_backup_complete';$report.manifestPath=Join-Path $destination 'manifest.json';$report.manifestSha256=$answer.manifestSha256;$report.backupPath=$destination
} catch {
 foreach ($pair in @(@('scheduledCode','scheduledExit'),@('serverCode','serverExit'),@('deploymentCode','deploymentExit'),@('instanceCode','instanceExit'),@('code','exitCode'))) {if ($_.Exception.Data.Contains($pair[0])) {$report.code=$_.Exception.Data[$pair[0]];$report.exitCode=[int]$_.Exception.Data[$pair[1]];break}}
 if ($runRoot.Length -gt 0) {try {[IO.File]::WriteAllText((Join-Path $runRoot 'exception-private.log'),$_.Exception.ToString()+[Environment]::NewLine+$_.ScriptStackTrace,(New-Object Text.UTF8Encoding($false)))} catch {}}
} finally {
 try {
  if ($null -ne $backup) {$backup.dumpHandle.Dispose();$backup.manifestHandle.Dispose()}
  if ($null -ne $child) {try {Stop-RackClickOwnedProcess $child} finally {$child.Process.Dispose()}}
  Close-ServerProfile $profile
 } catch {$report.valid=$false;$report.success=$false;$report.exitCode=2;$report.code='scheduled_backup_cleanup_failed'}
 try {
  if ($null -ne $lock -and $null -ne $profile) {Publish-ScheduledBackupReceipt (Join-Path $profile.root 'control\latest-backup.json') $report}
 } catch {$report.valid=$false;$report.success=$false;$report.exitCode=2;$report.code='scheduled_backup_receipt_publish_failed'}
 finally {
  if ($null -ne $lock) {$lock.Dispose()}
  $env:TEMP=$originalTemp;$env:TMP=$originalTmp
 }
}
$report|ConvertTo-Json -Depth 5 -Compress
exit $report.exitCode
