#requires -Version 5.1
<# Isolated Windows tests. Never starts SCM, registers tasks or touches a prior DB.
   NativeRestore creates only a NEW fixture and runs the original operational
   Restore; PostgreSQL is stopped by that operator before it reports success. #>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$SourceBackupPath,[string]$OutputPath='', [switch]$NativeRestore)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules'
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$preparer=Join-Path $repo 'tools\windows\server-install\Prepare-RackClickServer.ps1'
$operators=Join-Path $repo 'tools\windows'
$parserErrors=$null;$tokens=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($preparer,[ref]$tokens,[ref]$parserErrors)
if ($parserErrors.Count -ne 0) {throw 'Preparation script has parse errors'}
# Load only its pure helpers; the production entry-point guards remain intact.
foreach ($statement in $ast.EndBlock.Statements) {
 if ($statement -is [Management.Automation.Language.FunctionDefinitionAst]) {. ([scriptblock]::Create($statement.Extent.Text))}
}
$checks=New-Object Collections.Generic.List[string]
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$savedTemp=$env:TEMP;$savedTmp=$env:TMP
$native=$null
function Assert-Rejected {
 param([string]$Name,[scriptblock]$Action)
 $failed=$false;try {& $Action}catch {$failed=$true}
 if (-not $failed) {throw ('Not rejected: '+$Name)}
 $checks.Add($Name)
}
function New-TestBackupCopy {
 param([string]$Destination,[string]$Hash)
 Copy-PreparationRecoveryBackup -SourcePath $SourceBackupPath -ExpectedHash $Hash -DestinationPath $Destination -OperatorsPath $operators
}
try {
 $env:TEMP='C:\RackClick-Nonexistent-Admin-Temp-'+[guid]::NewGuid().ToString('N');$env:TMP=$env:TEMP
 $invalidInherited=$env:TEMP
 Initialize-PreparationCompilerTemporaryEnvironment $sid
 if ($env:TEMP -ceq $invalidInherited -or -not [IO.Directory]::Exists($env:TEMP) -or $env:TMP -cne $env:TEMP) {throw 'Inherited administrator temp was retained'}
 $checks.Add('Replace inaccessible inherited TEMP/TMP using actual SID profile')
 $fixture=Join-Path $repo ('.local\labs\server-restore-tests-'+[guid]::NewGuid().ToString('N'))
 New-PreparationPrivateDirectory $fixture
 $temp=Join-Path $fixture 'temp';New-PreparationPrivateDirectory $temp
 $env:TEMP=$temp;$env:TMP=$temp
 Assert-Rejected 'Private directory refuses an existing destination' {New-PreparationPrivateDirectory $fixture}
 $expectedHash=(Get-FileHash -LiteralPath (Join-Path $SourceBackupPath 'manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant()
 $destination=Join-Path $fixture 'trusted-backup'
 $copied=New-TestBackupCopy $destination $expectedHash
 if ($copied -cne $destination) {throw 'Copy returned wrong destination'}
 foreach ($name in @('manifest.json','data.dump')) {
  if ((Get-FileHash -LiteralPath (Join-Path $SourceBackupPath $name) -Algorithm SHA256).Hash -cne (Get-FileHash -LiteralPath (Join-Path $destination $name) -Algorithm SHA256).Hash) {throw 'Backup copy changed bytes'}
 }
 $checks.Add('Pinned native backup copied byte-exactly to fresh SID/SYSTEM directory')
 Assert-Rejected 'Existing private backup is never overwritten' {New-TestBackupCopy $destination $expectedHash}
 $mismatch=Join-Path $fixture 'wrong-hash'
 Assert-Rejected 'Wrong manifest pin rejected before destination creation' {New-TestBackupCopy $mismatch ('0'*64)}
 if (Test-Path -LiteralPath $mismatch) {throw 'Wrong pin created a destination'}
 $badPlan=[pscustomobject]@{codeRoot=$fixture;backupPath=$SourceBackupPath}
 Assert-Rejected 'Direct external user backup path is rejected by production binding' {Assert-PreparationRecoverySourceBinding $badPlan $sid}
 $protectedFake=Join-Path $fixture 'recovery-input'
 $null=New-TestBackupCopy $protectedFake $expectedHash
 $badOwnerPlan=[pscustomobject]@{codeRoot=$fixture;backupPath=$protectedFake}
 Assert-Rejected 'Service-owned source is rejected where administrator-protected input is required' {Assert-PreparationRecoverySourceBinding $badOwnerPlan $sid}
 $tampered=Join-Path $fixture 'tampered';$null=New-TestBackupCopy $tampered $expectedHash
 $dump=Join-Path $tampered 'data.dump';$stream=[IO.File]::Open($dump,'Open','ReadWrite','None')
 try {$stream.Position=16;$originalByte=$stream.ReadByte();$stream.Position=16;$stream.WriteByte($originalByte -bxor 1);$stream.Flush($true)}finally {$stream.Dispose()}
 $tamperedDestination=Join-Path $fixture 'tampered-destination'
 Assert-Rejected 'Changed dump rejected before destination creation' {Copy-PreparationRecoveryBackup -SourcePath $tampered -ExpectedHash $expectedHash -DestinationPath $tamperedDestination -OperatorsPath $operators}
 if (Test-Path -LiteralPath $tamperedDestination) {throw 'Changed dump created destination'}
 $extra=Join-Path $fixture 'extra-file';$null=New-TestBackupCopy $extra $expectedHash
 [IO.File]::WriteAllText((Join-Path $extra 'unexpected.txt'),'fixture')
 Assert-Rejected 'Backup with a third file rejected' {Copy-PreparationRecoveryBackup -SourcePath $extra -ExpectedHash $expectedHash -DestinationPath (Join-Path $fixture 'extra-destination') -OperatorsPath $operators}
 if ($NativeRestore) {
  $archive=Join-Path $repo '.local\offline1509-d941791809a84ee69aa0d4c62bd97484-a.zip'
  $target=Join-Path $fixture 'native-instance'
  $firstListener=New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback,0);$secondListener=New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback,0)
  try {$firstListener.Start();$secondListener.Start();$pgPort=$firstListener.LocalEndpoint.Port;$webPort=$secondListener.LocalEndpoint.Port} finally {$firstListener.Stop();$secondListener.Stop()}
  $processInfo=New-Object Diagnostics.ProcessStartInfo
  $processInfo.FileName=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
  $values=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Join-Path $operators 'Install-RackClickOfflineBundle.ps1'),'-ArchivePath',$archive,'-ExpectedArchiveSha256','a0df90ed3a2864492d8d9bdc2cc2e552113a6b9c81a3e603c1c2920486c26869','-DestinationPath',$target,'-PostgresPort',[string]$pgPort,'-HttpPort',[string]$webPort,'-Mode','Restore','-RecoveryUser','WascarRecovery','-BackupPath',$destination,'-ExpectedBackupManifestSha256',$expectedHash)
  $processInfo.Arguments=($values|ForEach-Object {Convert-PreparationArgument $_}) -join ' '
  $processInfo.WorkingDirectory=$fixture;$processInfo.UseShellExecute=$false;$processInfo.CreateNoWindow=$true;$processInfo.RedirectStandardOutput=$true;$processInfo.RedirectStandardError=$true
  $process=New-Object Diagnostics.Process;$process.StartInfo=$processInfo
  try {
   $watch=[Diagnostics.Stopwatch]::StartNew();if (-not $process.Start()) {throw 'Native Restore failed to start'}
   $stdoutTask=$process.StandardOutput.ReadToEndAsync();$stderrTask=$process.StandardError.ReadToEndAsync()
   if (-not $process.WaitForExit(900000)) {throw 'Native Restore still running; preserve fixture and inspect owned PID'}
   $stdout=$stdoutTask.Result;$stderr=$stderrTask.Result
   Write-PreparationNewText (Join-Path $fixture 'native-restore.stdout.log') $stdout
   Write-PreparationNewText (Join-Path $fixture 'native-restore.stderr.log') $stderr
   $answer=$stdout|ConvertFrom-Json
   if ($process.ExitCode -ne 0 -or $stderr.Length -ne 0 -or -not $answer.valid -or $answer.exitCode -ne 0 -or $answer.code -cne 'installation_prepared') {throw 'Native Restore did not return strict successful receipt'}
   $receiptPath=Join-Path $target 'installation.json';$receipt=Get-Content -LiteralPath $receiptPath -Raw|ConvertFrom-Json
   $receiptHash=(Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash.ToLowerInvariant()
   $state=Get-Content -LiteralPath (Join-Path $target 'installation-state.json') -Raw|ConvertFrom-Json
   if ($receipt.schemaVersion -ne 2 -or $receipt.recovery.backupManifestSha256 -cne $expectedHash -or $receipt.recovery.auditEventId -cnotmatch '^[a-f0-9-]{36}$' -or $receiptHash -cne $answer.installationSha256 -or $state.status -cne 'prepared') {throw 'Native restore persisted receipt mismatch'}
   if (Test-Path -LiteralPath (Join-Path $target 'deployment\instance\pgdata\postmaster.pid')) {throw 'Native Restore left PostgreSQL running'}
   $native=@{valid=$true;code=$answer.code;installationSha256=$receiptHash;backupManifestSha256=$expectedHash;recoveryAuditEventId=$receipt.recovery.auditEventId;elapsedSeconds=[math]::Round($watch.Elapsed.TotalSeconds,3);postgresStopped=$true;fixture=$target;postgresPort=$pgPort;httpsPort=$webPort}
   $checks.Add('Original native PostgreSQL Restore produces new installation with recovery audit and clean stop')
  } finally {$process.Dispose()}
 }
 $result=[ordered]@{schemaVersion=1;valid=$true;passed=$checks.Count;checks=@($checks);fixture=$fixture;nativeRestore=$native;environment='Windows PowerShell 5.1, development standard identity; no SCM or elevated service account';limits=@('Protected-source positive ACL requires broker under administrator and different service SID','Production entry point fixed ProgramData/ProgramFiles paths not invoked','No real service, scheduled task or reboot executed')}
 if ($OutputPath) {Write-PreparationNewText $OutputPath ($result|ConvertTo-Json -Depth 6 -Compress)}
 $result|ConvertTo-Json -Depth 6 -Compress
} finally {$env:TEMP=$savedTemp;$env:TMP=$savedTmp}
