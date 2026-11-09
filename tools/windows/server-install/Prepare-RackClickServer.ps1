#requires -Version 5.1
# Standard-account preparation child. No SCM, firewall, account or trust-store changes.
[CmdletBinding()]
param([string]$PlanPath='',[string]$ResultPath='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$report=[ordered]@{schemaVersion=1;valid=$false;exitCode=2;code='server_preparation_failed';stage='identity';errorType='';errorHResult=0;failureLine=0;installationSha256='';manifestSha256='';publicOrigin='';rootCertificatePath='';certificateExpiresUtc='';mutableDirectoryPaths=@();mutableFilePaths=@();serviceConfigPath=''}
$planStream=$null;$diagnostics='';$resultValidated=$false;$profileCreated=$false
$preparationOriginalEnvironment=@{}
foreach ($environmentName in @('TEMP','TMP','PSModulePath')) {$preparationOriginalEnvironment[$environmentName]=[Environment]::GetEnvironmentVariable($environmentName,[EnvironmentVariableTarget]::Process)}
# A credentialed child can inherit the launching administrator's environment.
# Use only built-in PS5 modules and a separately created private temporary root.
[Environment]::SetEnvironmentVariable('PSModulePath',(Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules'),[EnvironmentVariableTarget]::Process)
function Set-PreparationFailureDiagnostic($Record) {
 $exception=$Record.Exception
 for($i=0;$i-lt8-and$null-ne$exception.InnerException;$i++){$exception=$exception.InnerException}
 $type=$exception.GetType().FullName
 if($type-cmatch'^[A-Za-z][A-Za-z0-9_.+`]{0,159}$'){$script:report.errorType=$type}
 $script:report.errorHResult=[int]$exception.HResult
 $line=$Record.InvocationInfo.ScriptLineNumber
 if($line-is[int]-and$line-ge1-and$line-le1000000){$script:report.failureLine=$line}
}
function Assert-PreparationServiceIdentity {
 param([string]$ExpectedSid,[string]$ActualSid)
 if ($ExpectedSid -cne $ActualSid) {throw 'preparation_service_sid_mismatch'}
}
function Assert-PreparationPlanPaths {
 param($Plan,[string]$InputPath,[string]$OutputPath)
 $parent='C:\ProgramData\RackClick\Instances\'+$Plan.id
 if ($InputPath -cne (Join-Path $Plan.codeRoot 'preparation-plan.json') -or $Plan.instancePath -cne (Join-Path $parent 'instance') -or
     $Plan.codeRoot -cne ('C:\Program Files\RackClick\'+$Plan.id) -or $OutputPath -cne (Join-Path $Plan.instancePath 'runtime\control\preparation-result.json')) {throw 'preparation_plan_binding_invalid'}
}
function Assert-PreparationNoReparse {
 param([string]$Path)
 $cursor=$Path
 while ($cursor) {
  if (Test-Path -LiteralPath $cursor) {if (((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {throw 'preparation_reparse_rejected'}}
  $cursor=[IO.Path]::GetDirectoryName($cursor)
 }
}
function Initialize-PreparationCompilerTemporaryEnvironment {
 param([string]$ServiceSid)
 # Do not trust inherited USERPROFILE/TEMP from Start-Process -Credential. The
 # profile was loaded for this SID; its registry binding supplies the initial
 # compiler temp until our exclusively created private temp exists.
 $profileKey=[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\'+$ServiceSid)
 if ($null -eq $profileKey) {throw 'preparation_service_profile_missing'}
 try {$profilePath=[Environment]::ExpandEnvironmentVariables([string]$profileKey.GetValue('ProfileImagePath','',[Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames))} finally {$profileKey.Dispose()}
 if ($profilePath -cnotmatch '^[A-Za-z]:\\' -or $profilePath -cne [IO.Path]::GetFullPath($profilePath).TrimEnd('\') -or -not [IO.Directory]::Exists($profilePath)) {throw 'preparation_service_profile_invalid'}
 # AppData\Local is the SID-bound location, unlike a shared/redirected Temp
 # with extra writers. Only fixed, non-secret C# helper code is compiled here.
 $compilerTemp=Join-Path $profilePath 'AppData\Local'
 Assert-PreparationNoReparse $compilerTemp
 if (-not [IO.Directory]::Exists($compilerTemp)) {throw 'preparation_service_profile_invalid'}
 $acl=Get-Acl -LiteralPath $compilerTemp
 if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -cnotin @('S-1-5-18','S-1-5-32-544',$ServiceSid)) {throw 'preparation_service_temp_owner_invalid'}
 $writeMask=[Security.AccessControl.FileSystemRights]::Write -bor [Security.AccessControl.FileSystemRights]::Delete -bor [Security.AccessControl.FileSystemRights]::ChangePermissions -bor [Security.AccessControl.FileSystemRights]::TakeOwnership
 foreach ($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
  if ($rule.AccessControlType -eq 'Allow' -and ($rule.FileSystemRights -band $writeMask) -ne 0 -and $rule.IdentityReference.Value -cnotin @('S-1-5-18','S-1-5-32-544',$ServiceSid)) {throw 'preparation_service_temp_acl_invalid'}
 }
 [Environment]::SetEnvironmentVariable('TEMP',$compilerTemp,[EnvironmentVariableTarget]::Process)
 [Environment]::SetEnvironmentVariable('TMP',$compilerTemp,[EnvironmentVariableTarget]::Process)
}
function Assert-PreparationProtectedInput {
 param([string]$Path,[string]$Sid)
 Assert-PreparationNoReparse $Path
 $acl=Get-Acl -LiteralPath $Path
 if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -cnotin @('S-1-5-18','S-1-5-32-544')) {throw 'preparation_input_owner_invalid'}
 $found=$false
 foreach ($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
  if ($rule.AccessControlType -eq 'Allow') {
   if ($rule.IdentityReference.Value -cnotin @('S-1-5-18','S-1-5-32-544',$Sid)) {throw 'preparation_input_acl_invalid'}
   if ($rule.IdentityReference.Value -ceq $Sid) {
    $found=$true
    $writeMask=[Security.AccessControl.FileSystemRights]::Write -bor [Security.AccessControl.FileSystemRights]::Delete -bor [Security.AccessControl.FileSystemRights]::ChangePermissions -bor [Security.AccessControl.FileSystemRights]::TakeOwnership
    if (($rule.FileSystemRights -band $writeMask) -ne 0) {throw 'preparation_input_writable'}
   }
  }
 }
 if (-not $found) {throw 'preparation_input_acl_invalid'}
}
function New-PreparationPrivateDirectory {
 param([string]$Path)
 if (Test-Path -LiteralPath $Path) {throw 'preparation_diagnostics_exists'}
 Assert-PreparationNoReparse ([IO.Path]::GetDirectoryName($Path))
 $acl=New-Object Security.AccessControl.DirectorySecurity
 $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
 $acl.SetOwner($sid);$acl.SetAccessRuleProtection($true,$false)
 foreach ($identity in @($sid,(New-Object Security.Principal.SecurityIdentifier('S-1-5-18')))) {$acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($identity,'FullControl','ContainerInherit,ObjectInherit','None','Allow')))}
 if (-not ('RackClick.PreparationNative' -as [type])) {
  Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace RackClick {
 public static class PreparationNative {
  [StructLayout(LayoutKind.Sequential)] struct Attributes { public int Length; public IntPtr Descriptor; public int Inherit; }
  [DllImport("kernel32.dll", EntryPoint="CreateDirectoryW", CharSet=CharSet.Unicode, SetLastError=true)]
  [return: MarshalAs(UnmanagedType.Bool)] static extern bool CreateDirectory(string path, ref Attributes attributes);
  public static int Create(string path, byte[] descriptor) {
   var pinned=GCHandle.Alloc(descriptor,GCHandleType.Pinned);
   try { var attributes=new Attributes {Length=Marshal.SizeOf(typeof(Attributes)),Descriptor=pinned.AddrOfPinnedObject(),Inherit=0}; return CreateDirectory(path,ref attributes)?0:Marshal.GetLastWin32Error(); }
   finally {pinned.Free();}
  }
 }
}
'@
 }
 $nativeError=[RackClick.PreparationNative]::Create($Path,$acl.GetSecurityDescriptorBinaryForm())
 if ($nativeError -eq 183) {throw 'preparation_diagnostics_exists'}
 if ($nativeError -ne 0) {throw 'preparation_private_directory_create_failed'}
}
function Write-PreparationNewText {
 param([string]$Path,[string]$Value)
 $stream=[IO.File]::Open($Path,'CreateNew','Write','None')
 try {$bytes=(New-Object Text.UTF8Encoding($false)).GetBytes($Value);$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)} finally {$stream.Dispose()}
}
function Convert-PreparationArgument {
 param([string]$Value)
 if ($Value.Contains('"') -or $Value -match '[\x00-\x1f]') {throw 'preparation_argument_invalid'}
 # Quotes are prohibited; only terminal backslashes require doubling inside quotes.
 return '"'+[regex]::Replace($Value,'(\\+)$','$1$1')+'"'
}
function Read-PreparationChildResult {
 param([string]$Stdout,[string]$Stderr,[int]$NativeExitCode,[string]$Label,[string]$RequiredCode)
 if ($Stdout.Length -gt 65536 -or $Stderr.Length -ne 0) {throw 'preparation_child_output_invalid'}
 try {$value=$Stdout|ConvertFrom-Json} catch {throw 'preparation_child_json_invalid'}
 if ($value -isnot [pscustomobject] -or $null -eq $value.PSObject.Properties['valid'] -or
     $null -eq $value.PSObject.Properties['exitCode'] -or $null -eq $value.PSObject.Properties['code'] -or
     $value.valid -isnot [bool] -or $value.exitCode -isnot [int] -or $value.code -isnot [string] -or
     $value.exitCode -ne $NativeExitCode) {throw 'preparation_child_failed'}
 # A fixed failure enum, never raw child output. The ordinary success contract
 # remains mandatory; this branch cannot turn a failed recovery into success.
 if ($Label -ceq 'installation' -and $RequiredCode -ceq 'installation_prepared' -and
     $NativeExitCode -eq 1 -and -not $value.valid -and
     $value.code -ceq 'deployment_instance_administrator_recovery_username_exists') {throw 'preparation_recovery_username_exists'}
 if ($NativeExitCode -ne 0 -or -not $value.valid -or $value.code -cne $RequiredCode) {throw 'preparation_child_failed'}
 return $value
}
function Invoke-PreparationChild {
 param([string]$Script,[string[]]$Arguments,[string]$Label,[string]$RequiredCode)
 $start=New-Object Diagnostics.ProcessStartInfo
 $start.FileName=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
 $values=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$Script)+$Arguments
 $start.Arguments=($values|ForEach-Object {Convert-PreparationArgument $_}) -join ' '
 $start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
 $start.WorkingDirectory=$diagnostics
 $process=New-Object Diagnostics.Process;$process.StartInfo=$start
 try {
  if (-not $process.Start()) {throw 'preparation_child_start_failed'}
  $outTask=$process.StandardOutput.ReadToEndAsync();$errTask=$process.StandardError.ReadToEndAsync()
  $process.WaitForExit()
  $stdout=$outTask.Result;$stderr=$errTask.Result;$exitCode=$process.ExitCode
  Write-PreparationNewText (Join-Path $diagnostics ($Label+'-stdout.log')) $stdout
  Write-PreparationNewText (Join-Path $diagnostics ($Label+'-stderr.log')) $stderr
  return (Read-PreparationChildResult $stdout $stderr $exitCode $Label $RequiredCode)
 } finally {$process.Dispose()}
}
function Assert-PreparationRecoverySourceBinding {
 param($Plan,[string]$ServiceSid)
 # Only the broker's protected, freshly staged input is accepted. A browser/user
 # backup path is never passed directly to an operational restore under this SID.
 if ($Plan.backupPath -cne (Join-Path $Plan.codeRoot 'recovery-input')) {throw 'preparation_backup_source_binding_invalid'}
 foreach ($path in @($Plan.codeRoot,$Plan.backupPath,(Join-Path $Plan.backupPath 'manifest.json'),(Join-Path $Plan.backupPath 'data.dump'))) {Assert-PreparationProtectedInput $path $ServiceSid}
 $files=@(Get-ChildItem -LiteralPath $Plan.backupPath -Force)
 if ($files.Count -ne 2 -or @($files|Where-Object {$_.PSIsContainer}).Count -ne 0 -or (($files.Name|Sort-Object)-join ',') -cne 'data.dump,manifest.json') {throw 'preparation_backup_files_invalid'}
}
function Copy-PreparationRecoveryBackup {
 param([string]$SourcePath,[string]$ExpectedHash,[string]$DestinationPath,[string]$OperatorsPath)
 # Nested original scripts contain param blocks. Preserve our inputs before
 # importing them, and use the original backup reader rather than a weaker clone.
 $preparationRecoveryInputs=@{source=$SourcePath;hash=$ExpectedHash;destination=$DestinationPath;operators=$OperatorsPath}
 $PostgresBinPath=''
 . (Join-Path $preparationRecoveryInputs.operators 'RackClick.Backup.ps1')
 $preparationSourceBackup=$null;$preparationCopiedBackup=$null
 try {
  $preparationSourceBackup=Read-BackupManifest -Path $preparationRecoveryInputs.source -ExpectedHash $preparationRecoveryInputs.hash
  # Original helper atomically creates a NEW directory with SID/SYSTEM ACL;
  # a competing/existing destination is rejected, never reused or overwritten.
  $preparationBackupRoot=New-BackupPrivateDirectory $preparationRecoveryInputs.destination
  foreach ($entry in @(@{name='manifest.json';handle=$preparationSourceBackup.manifestHandle},@{name='data.dump';handle=$preparationSourceBackup.dumpHandle})) {
   $entry.handle.Position=0
   $destinationStream=[IO.File]::Open((Join-Path $preparationBackupRoot $entry.name),'CreateNew','Write','None')
   try {$entry.handle.CopyTo($destinationStream);$destinationStream.Flush($true)} finally {$destinationStream.Dispose()}
  }
  foreach ($name in @('','manifest.json','data.dump')) {
   $privatePath=if ($name -eq '') {$preparationBackupRoot} else {Join-Path $preparationBackupRoot $name}
   Assert-BackupPrivateAcl $privatePath
  }
  # Re-read the copied bytes, with both source locks still held. Keep originals
  # and any partial copy as evidence on failure; do not remove user backups.
  $preparationCopiedBackup=Read-BackupManifest -Path $preparationBackupRoot -ExpectedHash $preparationRecoveryInputs.hash
  if ($preparationCopiedBackup.hash -cne $preparationSourceBackup.hash) {throw 'preparation_backup_copy_hash_mismatch'}
  return $preparationBackupRoot
 } finally {
  foreach ($backupValue in @($preparationCopiedBackup,$preparationSourceBackup)) {
   if ($null -ne $backupValue) {try {$backupValue.dumpHandle.Dispose()} finally {$backupValue.manifestHandle.Dispose()}}
  }
 }
}
try {
 if (-not [Environment]::Is64BitProcess) {throw 'preparation_x64_required'}
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent();$principal=New-Object Security.Principal.WindowsPrincipal($identity)
 if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {throw 'preparation_standard_account_required'}
 $report.stage='plan'
 if ($PlanPath -notmatch '^C:\\Program Files\\RackClick\\[a-f0-9-]{36}\\preparation-plan.json$') {throw 'preparation_plan_path_invalid'}
 Assert-PreparationProtectedInput $PlanPath $identity.User.Value
 $planStream=[IO.File]::Open($PlanPath,'Open','Read','Read')
 if ($planStream.Length -lt 1 -or $planStream.Length -gt 32768) {throw 'preparation_plan_invalid'}
 $reader=New-Object IO.StreamReader($planStream,(New-Object Text.UTF8Encoding($false,$true)),$true,4096,$true)
 try {$plan=$reader.ReadToEnd()|ConvertFrom-Json} finally {$reader.Dispose()}
 if ((($plan.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'backupManifestSha256,backupPath,bindAddress,bootstrapUser,codeRoot,httpsPort,id,instancePath,mode,postgresPort,publicOrigin,schemaVersion,serviceName,serviceSid,systemhaus' -or
     $plan.schemaVersion -isnot [int] -or $plan.schemaVersion -ne 1 -or $plan.id -cnotmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$') {throw 'preparation_plan_invalid'}
 foreach ($name in @('id','instancePath','codeRoot','serviceSid','publicOrigin','bindAddress','bootstrapUser','systemhaus','mode','backupPath','backupManifestSha256','serviceName')) {if ($plan.$name -isnot [string]) {throw 'preparation_plan_invalid'}; $null=Convert-PreparationArgument $plan.$name}
 Assert-PreparationServiceIdentity $plan.serviceSid $identity.User.Value
 Assert-PreparationPlanPaths $plan $PlanPath $ResultPath
 if ($plan.serviceName -cnotmatch '^RackClick(?:-Recovery-[a-f0-9]{8,32})?$') {throw 'preparation_service_name_invalid'}
 if ($plan.httpsPort -isnot [int] -or $plan.postgresPort -isnot [int] -or $plan.httpsPort -lt 1024 -or $plan.httpsPort -gt 65535 -or $plan.postgresPort -lt 1024 -or $plan.postgresPort -gt 65535 -or $plan.httpsPort -eq $plan.postgresPort) {throw 'preparation_ports_invalid'}
 if ($plan.mode -cnotin @('New','Restore') -or ($plan.mode -ceq 'New' -and ($plan.backupPath -ne '' -or $plan.backupManifestSha256 -ne '')) -or
     ($plan.mode -ceq 'Restore' -and ($plan.backupPath -eq '' -or $plan.backupManifestSha256 -cnotmatch '^[a-f0-9]{64}$'))) {throw 'preparation_mode_invalid'}
 Assert-PreparationNoReparse $plan.instancePath;Assert-PreparationNoReparse $ResultPath
 if ((Test-Path -LiteralPath $plan.instancePath) -or (Test-Path -LiteralPath $ResultPath)) {throw 'preparation_destination_exists'}
 $resultValidated=$true
 $report.stage='temporary_environment'
 Initialize-PreparationCompilerTemporaryEnvironment $identity.User.Value
 $diagnostics=Join-Path ([IO.Path]::GetDirectoryName($plan.instancePath)) 'preparation'
 New-PreparationPrivateDirectory $diagnostics
 $preparationTemp=Join-Path $diagnostics 'temp';New-PreparationPrivateDirectory $preparationTemp
 [Environment]::SetEnvironmentVariable('TEMP',$preparationTemp,[EnvironmentVariableTarget]::Process)
 [Environment]::SetEnvironmentVariable('TMP',$preparationTemp,[EnvironmentVariableTarget]::Process)
 $report.stage='payload'
 $archive=Join-Path $plan.codeRoot 'RackClick.zip';$installer=Join-Path $plan.codeRoot 'operators\Install-RackClickOfflineBundle.ps1';$profileScript=Join-Path $plan.codeRoot 'operators\server-install\New-RackClickServerProfile.ps1';$runtimeScript=Join-Path $plan.codeRoot 'operators\server-install\Invoke-RackClickServerRuntime.ps1'
 foreach ($file in @($archive,$installer,$profileScript,$runtimeScript)) {Assert-PreparationProtectedInput $file $identity.User.Value}
 if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -cne 'b9336b50e4460166595c63d4e1631eb64e206214906b047e326939d62e9dc521') {throw 'preparation_bundle_hash_mismatch'}
 $args=@('-ArchivePath',$archive,'-ExpectedArchiveSha256','b9336b50e4460166595c63d4e1631eb64e206214906b047e326939d62e9dc521','-DestinationPath',$plan.instancePath,'-PostgresPort',[string]$plan.postgresPort,'-HttpPort',[string]$plan.httpsPort,'-Mode',$plan.mode)
 if ($plan.mode -ceq 'New') {$args+=@('-BootstrapUser',$plan.bootstrapUser,'-SystemhausName',$plan.systemhaus)} else {
  $report.stage='recovery_input'
  Assert-PreparationRecoverySourceBinding $plan $identity.User.Value
  $privateRecoveryBackup=Copy-PreparationRecoveryBackup -SourcePath $plan.backupPath -ExpectedHash $plan.backupManifestSha256 -DestinationPath (Join-Path ([IO.Path]::GetDirectoryName($plan.instancePath)) 'trusted-backup') -OperatorsPath (Join-Path $plan.codeRoot 'operators')
  $args+=@('-RecoveryUser',$plan.bootstrapUser,'-BackupPath',$privateRecoveryBackup,'-ExpectedBackupManifestSha256',$plan.backupManifestSha256)
 }
 $report.stage='installation'
 $installed=Invoke-PreparationChild $installer $args 'installation' 'installation_prepared'
 $report.stage='installation_receipt'
 $receiptPath=Join-Path $plan.instancePath 'installation.json';Assert-PreparationNoReparse $receiptPath
 $installationHash=(Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash.ToLowerInvariant()
 $state=Get-Content -LiteralPath (Join-Path $plan.instancePath 'installation-state.json') -Raw|ConvertFrom-Json
 if ($installed.installationSha256 -cne $installationHash -or $installed.installationPath -cne $plan.instancePath -or $state.status -cne 'prepared' -or $state.code -cne 'installation_prepared') {throw 'preparation_installation_receipt_invalid'}
 $report.stage='profile'
 $profile=Invoke-PreparationChild $profileScript @('-InstallationPath',$plan.instancePath,'-ExpectedInstallationSha256',$installationHash,'-DestinationPath',(Join-Path $plan.instancePath 'runtime'),'-PublicOrigin',$plan.publicOrigin,'-BindAddress',$plan.bindAddress,'-EnableMfa') 'profile' 'server_profile_prepared'
 $profileCreated=$true
 if ($profile.manifestPath -cne (Join-Path $plan.instancePath 'runtime\server-profile.json') -or $profile.manifestSha256 -cnotmatch '^[a-f0-9]{64}$' -or $profile.publicOrigin -cne $plan.publicOrigin) {throw 'preparation_profile_receipt_invalid'}
 $report.stage='configuration'
 $configPath=Join-Path $plan.instancePath 'service-config.json'
 $config=[ordered]@{schemaVersion=1;serviceName=$plan.serviceName;runtimeScriptPath=$runtimeScript;serverManifestPath=$profile.manifestPath;serverManifestSha256=$profile.manifestSha256;logDirectory=(Join-Path $plan.instancePath 'runtime\logs')}
 Write-PreparationNewText $configPath ($config|ConvertTo-Json -Compress)
 $report.valid=$true;$report.exitCode=0;$report.code='server_prepared';$report.installationSha256=$installationHash;$report.manifestSha256=$profile.manifestSha256;$report.publicOrigin=$profile.publicOrigin;$report.rootCertificatePath=$profile.rootCertificatePath;$report.certificateExpiresUtc=$profile.certificateExpiresUtc;$report.mutableDirectoryPaths=$profile.mutableDirectoryPaths;$report.mutableFilePaths=$profile.mutableFilePaths;$report.serviceConfigPath=$configPath
 $report.stage='prepared'
} catch {
 Set-PreparationFailureDiagnostic $_
 $message=$_.Exception.Message
 if ($message -cmatch '^preparation_[a-z0-9_]+$') {$report.code=$message}
 if ($diagnostics -ne '') {try {Write-PreparationNewText (Join-Path $diagnostics 'exception-private.log') ($_.Exception.ToString()+[Environment]::NewLine+$_.ScriptStackTrace)} catch {}}
} finally {
 if ($null -ne $planStream) {$planStream.Dispose()}
 foreach ($environmentName in $preparationOriginalEnvironment.Keys) {[Environment]::SetEnvironmentVariable($environmentName,$preparationOriginalEnvironment[$environmentName],[EnvironmentVariableTarget]::Process)}
}
if ($profileCreated -and $resultValidated) {
 try {Write-PreparationNewText $ResultPath ($report|ConvertTo-Json -Depth 6 -Compress)} catch {$report.valid=$false;$report.exitCode=2;$report.code='preparation_result_publish_failed';$report.stage='result_publish';Set-PreparationFailureDiagnostic $_}
}
$report|ConvertTo-Json -Depth 6 -Compress
exit $report.exitCode
