#requires -Version 5.1
[CmdletBinding()]
param(
 [ValidateSet('Check','Apply')][string]$Mode='Check',
 [Parameter(Mandatory=$true)][string]$InstallationId,
 [Parameter(Mandatory=$true)][string]$PayloadPath,
 [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$ExpectedCurrentManifestSha256
)
# Bounded maintenance operation: legacy instance1/schema43 -> application45.
# No account creation, bootstrap, MFA reset, network change or automatic DB rollback.
$ErrorActionPreference='Stop'
$upgInputs=@{mode=$Mode;id=$InstallationId;payload=$PayloadPath;oldSha=$ExpectedCurrentManifestSha256}
. (Join-Path $PSScriptRoot 'RackClick.ApplicationUpgrade.ps1')
$upgPayloadSha='59edfda54cac5e1951ca21c29926c34b4f5da9440393822ce1284aed176e364f'
$upgApplicationSha='528a03d2efc939d1cea631b1caa9f3e6a445e44257fa757f87a95691acfb6933'
$upgBundleSha='b9564d390b266cd3e03316f5981dc4f9f53aab8e4fb218c0ee43c0428b6f5df6'
$upgPayloadJsonSha='2c945d6a4b42110402b60f7de84bb75eab4249ca7f593dff90a2ecef72ccacc9'
$upgStage='input';$upgJournal='';$upgTransaction='';$upgPayloadLock=$null;$upgZip=$null;$upgCredential=$null;$upgOperationLock=$null
$upgStopped=$false;$upgExposed=$false;$upgCommitted=$false;$upgColdBackupVerified=$false;$upgMigrationStarted=$false;$upgTaskChangesAttempted=$false;$upgOldTasks=@();$upgExit=1;$upgRecord=$null
function Write-UpgJournal([string]$Stage) {
 $script:upgStage=$Stage
 if(-not$script:upgJournal){return}
 $value=@{schemaVersion=1;utc=[DateTime]::UtcNow.ToString('o');installationId=$upgInputs.id;stage=$Stage;serviceStopped=$upgStopped;listener45MayBeExposed=$upgExposed;committed=$upgCommitted}
 $b=ConvertTo-RcApplicationBytes $value;$s=[IO.File]::Open($upgJournal,'Append','Write','Read')
 try{$s.Write($b,0,$b.Length);$s.WriteByte(10);$s.Flush($true)}finally{$s.Dispose()}
}
function New-UpgFolder([string]$Path,[string]$Sddl) {
 Assert-SetupNoReparse $Path
 New-StageDirectoryExclusive $Path
 Invoke-SetupSecurityPrivileges {[RackClickSetupSecurityNative]::SetAcl($Path,$Sddl)}
}
function Read-UpgSnapshot([string]$Path) {
 return (Invoke-SetupSecurityPrivileges {[RackClickNetworkMaintenanceNative]::Snapshot($Path)})
}
function Read-UpgJson([string]$Path) {return ([Text.Encoding]::UTF8.GetString((Read-UpgSnapshot $Path).Bytes)|ConvertFrom-Json)}
function Write-UpgExisting([string]$Path,[byte[]]$Bytes) {
 $before=Read-UpgSnapshot $Path
 Invoke-SetupSecurityPrivileges {[RackClickNetworkMaintenanceNative]::WriteExisting($Path,$Bytes)}
 $after=Read-UpgSnapshot $Path
 if((Get-RcApplicationBytesHash $after.Bytes)-cne(Get-RcApplicationBytesHash $Bytes)-or$before.Sddl-cne$after.Sddl){Stop-RcApplicationUpgrade 'upgrade_metadata_write_unconfirmed'}
}
function Copy-UpgCold([string]$Source,[string]$Destination,[string]$Label) {
 if(-not$Destination.StartsWith($upgTransaction+'\',[StringComparison]::OrdinalIgnoreCase)-or(Test-Path -LiteralPath $Destination)){Stop-RcApplicationUpgrade 'upgrade_backup_destination_invalid'}
 Assert-SetupNoReparse $Source;Assert-SetupNoReparse $Destination
 $log=Join-Path $upgTransaction ($Label+'.log')
 & "$env:SystemRoot\System32\robocopy.exe" $Source $Destination /E /B /COPYALL /DCOPY:DAT /R:0 /W:0 /XJ /NFL /NDL /NJH /NJS /NP "/LOG:$log" | Out-Null
 if($LASTEXITCODE-gt7){Stop-RcApplicationUpgrade 'upgrade_cold_copy_failed'}
 & "$env:SystemRoot\System32\robocopy.exe" $Source $Destination /E /B /COPYALL /DCOPY:DAT /R:0 /W:0 /XJ /L /NFL /NDL /NJH /NJS /NP "/LOG:$(Join-Path $upgTransaction ($Label+'-compare.log'))" | Out-Null
 if($LASTEXITCODE-ne0){Stop-RcApplicationUpgrade 'upgrade_cold_copy_not_equal'}
}
function Invoke-UpgServiceChild([string]$Phase,[string]$PlanPath) {
 $scriptPath=Join-Path $PSScriptRoot 'Apply-RackClickApplicationUpgrade43To45.ps1'
 $arguments='-NoProfile -NonInteractive -ExecutionPolicy Bypass -File '+(ConvertTo-SetupArgument $scriptPath)+' -Phase '+$Phase+' -PlanPath '+(ConvertTo-SetupArgument $PlanPath)
 $stdout=Join-Path $upgTransaction ('child-'+$Phase.ToLowerInvariant()+'.stdout.log');$stderr=Join-Path $upgTransaction ('child-'+$Phase.ToLowerInvariant()+'.stderr.log')
 $saved=@{};$child=$null;$handle=$null
 try{
  foreach($item in @(Get-ChildItem Env:)){if($item.Name-match'^(?i:DOTNET|CORECLR|COR_|COMPlus_|ASPNETCORE_|ConnectionStrings__|SqlSecret__|MfaKeyStore__|PG)'){$saved[$item.Name]=$item.Value;[Environment]::SetEnvironmentVariable($item.Name,$null,'Process')}}
  [Environment]::SetEnvironmentVariable('DOTNET_EnableDiagnostics','0','Process')
  $child=Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Credential $upgCredential -LoadUserProfile -WorkingDirectory $upgCandidate -ArgumentList $arguments -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
  $handle=Open-SetupChildProcess $child.Id
  Write-UpgJournal ('child_'+$Phase.ToLowerInvariant()+'_started')
  if(-not(Wait-SetupChildProcess $handle 600)){Stop-RcApplicationUpgrade 'upgrade_child_timeout_do_not_repeat'}
  $exitCode=Get-SetupChildProcessExitCode $handle
  $report=Read-UpgJson (Join-Path $upgWork ($Phase.ToLowerInvariant()+'-result.json'))
  if($exitCode-ne0-or-not$report.valid-or$report.exitCode-ne0){Stop-RcApplicationUpgrade ('upgrade_'+$Phase.ToLowerInvariant()+'_failed')}
  return $report
 }finally{
  if($handle){$handle.Dispose()};if($child){$child.Dispose()}
  [Environment]::SetEnvironmentVariable('DOTNET_EnableDiagnostics',$null,'Process')
  foreach($key in $saved.Keys){[Environment]::SetEnvironmentVariable($key,$saved[$key],'Process')}
 }
}
function Seal-UpgNewTree([string]$Path) {
 # Only new application trees, never database, private SQL, certificates or MFA.
 if($Path-cnotin@((Join-Path $upgRoot 'content'),(Join-Path $upgRoot 'deployment\distribution'))){Stop-RcApplicationUpgrade 'upgrade_seal_target_invalid'}
 Invoke-SetupSecurityPrivileges {
  function Seal-UpgNode([string]$Node){
   Assert-SetupNoReparse $Node
   [RackClickSetupSecurityNative]::SetAcl($Node,'O:SYG:SYD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)')
   $item=Get-Item -LiteralPath $Node -Force
   if($item.PSIsContainer){foreach($entry in @(Get-ChildItem -LiteralPath $Node -Force)){Seal-UpgNode $entry.FullName}}
   $flags=if($item.PSIsContainer){'OICI'}else{''}
   [RackClickSetupSecurityNative]::SetAcl($Node,('O:SYG:SYD:P(A;'+$flags+';FA;;;SY)(A;'+$flags+';FRFX;;;'+$upgRecord.serviceSid+')'))
  }
  Seal-UpgNode $Path
 }
}
try{
 $parsed=[guid]::Empty
 if(-not[guid]::TryParseExact($upgInputs.id,'D',[ref]$parsed)-or$parsed-eq[guid]::Empty-or$upgInputs.id-cne$parsed.ToString('D')){Stop-RcApplicationUpgrade 'upgrade_installation_id_invalid'}
 $upgBase='C:\ProgramData\RackClick\Instances\'+$upgInputs.id;$upgRoot=Join-Path $upgBase 'instance';$upgCode='C:\Program Files\RackClick\'+$upgInputs.id;$upgManagement=Join-Path $upgBase 'management'
 . (Join-Path $upgCode 'operators\server-install\RackClick.Setup.Security.ps1')
 . (Join-Path $upgCode 'operators\server-install\RackClick.Setup.ps1')
 . (Join-Path $upgCode 'operators\server-install\RackClick.Setup.Process.ps1')
 . (Join-Path $upgCode 'operators\RackClick.Stage.ps1')
 Assert-SetupAdministrator;Initialize-SetupSecurityNative
 Assert-SetupManagementAcl $upgManagement
 $upgRecord=Get-Content -LiteralPath (Join-Path $upgManagement 'server-installation.json') -Raw|ConvertFrom-Json
 if($upgRecord.installationId-cne$upgInputs.id-or$upgRecord.instancePath-cne$upgRoot-or$upgRecord.codeRoot-cne$upgCode-or$upgRecord.managementPath-cne$upgManagement-or$upgRecord.applicationSchemaVersion-ne43-or$upgRecord.manifestSha256-cne$upgInputs.oldSha){Stop-RcApplicationUpgrade 'upgrade_source_binding_invalid'}
 $upgService=Get-CimInstance Win32_Service -Filter ("Name='"+$upgRecord.serviceName+"'")
 $account=New-Object Security.Principal.NTAccount($upgService.StartName.Replace('.\',($env:COMPUTERNAME+'\')))
 if($account.Translate([Security.Principal.SecurityIdentifier]).Value-cne$upgRecord.serviceSid-or$upgService.State-cne'Running'-or$upgService.StartMode-cne'Auto'){Stop-RcApplicationUpgrade 'upgrade_service_binding_invalid'}
 if($upgRecord.serviceName-cnotmatch'^RackClick(?:-Recovery-[a-f0-9]{8,32})?$'){Stop-RcApplicationUpgrade 'upgrade_service_binding_invalid'}
 if(@((Get-Service -Name $upgRecord.serviceName).DependentServices|Where-Object{$_.Status-eq'Running'}).Count){Stop-RcApplicationUpgrade 'upgrade_dependent_service_running'}
 $health=Invoke-RestMethod -UseBasicParsing -Uri ($upgRecord.publicOrigin+'/health/ready') -TimeoutSec 15
 if($health.status-cne'ready'-or$health.schemaVersion-ne43){Stop-RcApplicationUpgrade 'upgrade_source_not_ready43'}
 Assert-SetupNoReparse $upgInputs.payload
 $upgPayloadLock=[IO.File]::Open($upgInputs.payload,'Open','Read','Read')
 $algorithm=[Security.Cryptography.SHA256]::Create()
 try{$observed=([BitConverter]::ToString($algorithm.ComputeHash($upgPayloadLock))).Replace('-','').ToLowerInvariant()}finally{$algorithm.Dispose()}
 if($observed-cne$upgPayloadSha){Stop-RcApplicationUpgrade 'upgrade_payload_pin_invalid'}
 $upgPayloadLock.Position=0
 Add-Type -AssemblyName System.IO.Compression
 $upgZip=New-Object IO.Compression.ZipArchive($upgPayloadLock,[IO.Compression.ZipArchiveMode]::Read,$true)
 if($upgZip.Entries.Count-ne117){Stop-RcApplicationUpgrade 'upgrade_payload_inventory_invalid'}
 $manifestEntry=$upgZip.GetEntry('RackClick-Instalador/payload.json')
 if($null-eq$manifestEntry){Stop-RcApplicationUpgrade 'upgrade_payload_inventory_invalid'}
 $manifestStream=$manifestEntry.Open();$memory=New-Object IO.MemoryStream
 try{$manifestStream.CopyTo($memory);$payloadBytes=$memory.ToArray()}finally{$manifestStream.Dispose();$memory.Dispose()}
 if((Get-RcApplicationBytesHash $payloadBytes)-cne$upgPayloadJsonSha){Stop-RcApplicationUpgrade 'upgrade_payload_manifest_invalid'}
 $payload=[Text.Encoding]::UTF8.GetString($payloadBytes)|ConvertFrom-Json
 if($payload.bundleArchiveSha256-cne$upgBundleSha){Stop-RcApplicationUpgrade 'upgrade_bundle_pin_invalid'}
 if($upgRecord.backupTaskName-cne('RackClick-Backup-'+$upgInputs.id)-or$upgRecord.postbootTaskName-cne('RackClick-Verify-'+$upgInputs.id)){Stop-RcApplicationUpgrade 'upgrade_task_binding_invalid'}
 foreach($taskName in @($upgRecord.backupTaskName,$upgRecord.postbootTaskName)){
  $task=Get-ScheduledTask -TaskName $taskName
  if($task.State-eq'Running'){Stop-RcApplicationUpgrade 'upgrade_task_busy'}
  $upgOldTasks+=@{name=$taskName;enabled=[bool]$task.Settings.Enabled;xml=(Export-ScheduledTask -TaskName $taskName)}
 }
 if($upgInputs.mode-ceq'Check'){$upgExit=0;$answer=@{valid=$true;success=$true;exitCode=0;code='upgrade_ready';sourceSchema=43;targetSchema=45;installationId=$upgInputs.id;mutationsPerformed=$false};return}
 $tag=[guid]::NewGuid().ToString('N')
 $upgTransaction=Join-Path $upgManagement ('application-update45-'+$tag)
 New-UpgFolder $upgTransaction 'O:BAG:SYD:P(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)'
 $upgJournal=Join-Path $upgTransaction 'journal.jsonl';Write-UpgJournal 'validated'
 $upgOperationLock=[IO.File]::Open((Join-Path $upgManagement 'application-update.lock'),'OpenOrCreate','ReadWrite','None')
 $upgCandidate=Join-Path 'C:\Program Files\RackClick' ([guid]::NewGuid().ToString('D'))
 Set-SetupPublicCodeDirectoryACL -Path $upgCandidate -ServiceSid $upgRecord.serviceSid
 foreach($entry in $upgZip.Entries){
  if(-not$entry.FullName.StartsWith('RackClick-Instalador/',[StringComparison]::Ordinal)){Stop-RcApplicationUpgrade 'upgrade_payload_path_invalid'}
  $relative=$entry.FullName.Substring('RackClick-Instalador/'.Length)
  if($relative-cnotmatch'^[A-Za-z0-9_. /-]+$'-or$relative-match'(^|/)\.\.?(/|$)' -or $relative.Contains('\')){Stop-RcApplicationUpgrade 'upgrade_payload_path_invalid'}
  $target=Join-Path $upgCandidate $relative.Replace('/','\');$parent=[IO.Path]::GetDirectoryName($target)
  if(-not[IO.Directory]::Exists($parent)){$null=[IO.Directory]::CreateDirectory($parent)}
  $source=$entry.Open();$destination=[IO.File]::Open($target,'CreateNew','Write','None')
  try{$source.CopyTo($destination);$destination.Flush($true)}finally{$source.Dispose();$destination.Dispose()}
 }
 . (Join-Path $upgCandidate 'operators\server-install\RackClick.Setup.ps1')
 $null=Assert-SetupPayload $upgCandidate
 # This fourth helper is externally pinned and leased with parent/core/child.
 # The network package is separate from the installer; never import its main.
 . (Join-Path $PSScriptRoot 'RackClick.ApplicationUpgrade.Native.ps1')
 Initialize-RcNetworkNative
 $upgCredential=Read-SetupServiceCredential $upgManagement
 if((New-Object Security.Principal.NTAccount($upgCredential.UserName)).Translate([Security.Principal.SecurityIdentifier]).Value-cne$upgRecord.serviceSid){Stop-RcApplicationUpgrade 'upgrade_credential_sid_invalid'}
 $upgWork=Join-Path $upgBase ('update45-'+$tag)
 New-UpgFolder $upgWork ('O:SYG:SYD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;'+$upgRecord.serviceSid+')')
 $upgPlanPath=Join-Path $upgTransaction 'plan.json'
 $upgPlan=@{installationId=$upgInputs.id;serviceSid=$upgRecord.serviceSid;instancePath=$upgRoot;codeRoot=$upgCode;candidateCodeRoot=$upgCandidate;workRoot=$upgWork;expectedCurrentManifestSha256=$upgInputs.oldSha;expectedApplicationManifestSha256=$upgApplicationSha;expectedBundleSha256=$upgBundleSha}
 Write-SetupJson $upgPlanPath $upgPlan
 # Plan contains only bindings and pins; service gets read access, no journal write.
 Invoke-SetupSecurityPrivileges {[RackClickSetupSecurityNative]::SetAcl($upgPlanPath,('O:BAG:SYD:P(A;;FA;;;BA)(A;;FA;;;SY)(A;;FR;;;'+$upgRecord.serviceSid+')'))}
 $prepared=Invoke-UpgServiceChild 'Prepare' $upgPlanPath
 if($prepared.bundle.bundleArchiveSha256-cne$upgBundleSha-or$prepared.bundle.bundleManifestSha256-cne'3d7d2fa11125bee2c23444484068d7245127f48cf54d7efae225fb121ef71736'-or$prepared.stageReceipt.manifestSha256-cne$upgApplicationSha){Stop-RcApplicationUpgrade 'upgrade_prepared_bundle_pin_invalid'}
 Write-UpgJournal 'candidate_prepared'
 $upgTaskChangesAttempted=$true
 foreach($oldTask in $upgOldTasks){[IO.File]::WriteAllText((Join-Path $upgTransaction ($oldTask.name+'.xml')),$oldTask.xml);$null=Disable-ScheduledTask -TaskName $oldTask.name}
 Write-UpgJournal 'stopping_service'
 Stop-Service -Name $upgRecord.serviceName
 (Get-Service -Name $upgRecord.serviceName).WaitForStatus([ServiceProcess.ServiceControllerStatus]::Stopped,[TimeSpan]::FromSeconds(120))
 $upgStopped=$true
 $upgPidPresent=Invoke-SetupSecurityPrivileges {[RackClickNetworkMaintenanceNative]::Exists((Join-Path $upgRoot 'deployment\instance\pgdata\postmaster.pid'))}
 if($upgPidPresent){Stop-RcApplicationUpgrade 'upgrade_postgres_not_stopped'}
 $listeners=@([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()|ForEach-Object Port)
 if($prepared.original.instance.postgresPort-in$listeners-or$prepared.original.instance.httpPort-in$listeners){Stop-RcApplicationUpgrade 'upgrade_source_ports_busy'}
 $coldCheck=Invoke-UpgServiceChild 'ColdCheck' $upgPlanPath
 if($coldCheck.sourceTreesNoReparse-ne$true-or$coldCheck.sourceFileContentsRead-ne$false){Stop-RcApplicationUpgrade 'upgrade_cold_sources_not_verified'}
 Write-UpgJournal 'cold_backup'
 Copy-UpgCold $upgRoot (Join-Path $upgTransaction 'instance43') 'instance43'
 Copy-UpgCold (Join-Path $upgBase 'security') (Join-Path $upgTransaction 'security43') 'security43'
 Copy-UpgCold $upgCode (Join-Path $upgTransaction 'code43') 'code43'
 $upgColdBackupVerified=$true
 $originalFiles=@{}
 foreach($entry in @(@('instance','deployment\instance\instance.json'),@('deployment','deployment\deployment.json'),@('installation','installation.json'),@('profile','runtime\server-profile.json'),@('serviceConfig','service-config.json'))){$originalFiles[$entry[0]]=Read-UpgSnapshot (Join-Path $upgRoot $entry[1])}
 $originalFiles.management=Read-UpgSnapshot (Join-Path $upgManagement 'server-installation.json')
 foreach($name in @('instance','deployment','installation','profile','serviceConfig')){
  $observed=[Text.Encoding]::UTF8.GetString($originalFiles[$name].Bytes)|ConvertFrom-Json
  if((Get-RcApplicationBytesHash (ConvertTo-RcApplicationBytes $observed))-cne(Get-RcApplicationBytesHash (ConvertTo-RcApplicationBytes $prepared.original.$name))){Stop-RcApplicationUpgrade 'upgrade_source_changed_after_prepare'}
 }
 $observedManagement=[Text.Encoding]::UTF8.GetString($originalFiles.management.Bytes)|ConvertFrom-Json
 if((Get-RcApplicationBytesHash (ConvertTo-RcApplicationBytes $observedManagement))-cne(Get-RcApplicationBytesHash (ConvertTo-RcApplicationBytes $upgRecord))){Stop-RcApplicationUpgrade 'upgrade_source_changed_after_prepare'}
 $upgMigrationStarted=$true
 $migration=Invoke-UpgServiceChild 'Migrate' $upgPlanPath
 if(-not$migration.temporaryPostgresStopped-or-not$migration.protectedFilesUnchanged){Stop-RcApplicationUpgrade 'upgrade_migration_not_quiet'}
 Write-UpgJournal 'migration_verified'
 $chain=Get-RcApplicationUpgradeChain -InstallationId $upgInputs.id -Instance $prepared.original.instance -Deployment $prepared.original.deployment -Installation $prepared.original.installation -Profile $prepared.original.profile -ServiceConfig $prepared.original.serviceConfig -Management $upgRecord -StageReceipt $prepared.stageReceipt -StageReceiptSha256 $prepared.stageReceiptSha256 -TargetManifestSha256 $upgApplicationSha -Bundle $prepared.bundle
 # Preserve this operational file explicitly; it is not a payload member.
 $operational=Join-Path $upgCode 'preparation-plan.json'
 if([IO.File]::Exists($operational)){[IO.File]::Copy($operational,(Join-Path $upgCandidate 'preparation-plan.json'),$false)}
 Write-UpgJournal 'publishing_complete_trees'
 $temporaryAcl='O:SYG:SYD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)'
 $upgOldDistribution=Join-Path $upgRoot 'deployment\distribution'
 $upgRetiredDistribution=Join-Path $upgTransaction 'retired-distribution43'
 # Protected source roots need attributes/delete access as well as their parent.
 $moveRoots=@($upgRoot,(Join-Path $upgRoot 'deployment'),$upgWork,$upgOldDistribution,(Join-Path $upgWork 'distribution45'))
 try{
  Invoke-SetupSecurityPrivileges {foreach($p in $moveRoots){[RackClickSetupSecurityNative]::SetAcl($p,$temporaryAcl)}}
  [IO.Directory]::Move((Join-Path $upgRoot 'content'),(Join-Path $upgTransaction 'retired-content43'))
  [IO.Directory]::Move((Join-Path $upgWork 'content45'),(Join-Path $upgRoot 'content'))
  [IO.Directory]::Move((Join-Path $upgRoot 'deployment\distribution'),(Join-Path $upgTransaction 'retired-distribution43'))
  [IO.Directory]::Move((Join-Path $upgWork 'distribution45'),(Join-Path $upgRoot 'deployment\distribution'))
  [IO.Directory]::Move($upgCode,(Join-Path $upgTransaction 'retired-code43'))
  [IO.Directory]::Move($upgCandidate,$upgCode)
 }finally{
  Invoke-SetupSecurityPrivileges {
   foreach($p in @($upgRoot,(Join-Path $upgRoot 'deployment'))){[RackClickSetupSecurityNative]::SetAcl($p,[string]$prepared.dirAcls.$p)}
   [RackClickSetupSecurityNative]::SetAcl($upgWork,('O:SYG:SYD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;'+$upgRecord.serviceSid+')'))
   if([RackClickNetworkMaintenanceNative]::Exists($upgRetiredDistribution)){[RackClickSetupSecurityNative]::SetAcl($upgRetiredDistribution,[string]$prepared.dirAcls.$upgOldDistribution)}
   elseif([RackClickNetworkMaintenanceNative]::Exists($upgOldDistribution)){[RackClickSetupSecurityNative]::SetAcl($upgOldDistribution,[string]$prepared.dirAcls.$upgOldDistribution)}
  }
 }
 Seal-UpgNewTree (Join-Path $upgRoot 'content');Seal-UpgNewTree (Join-Path $upgRoot 'deployment\distribution')
 foreach($entry in @(@('instance','deployment\instance\instance.json'),@('deployment','deployment\deployment.json'),@('installation','installation.json'),@('profile','runtime\server-profile.json'),@('serviceConfig','service-config.json'))){Write-UpgJournal ('metadata_'+$entry[0]);Write-UpgExisting (Join-Path $upgRoot $entry[1]) (ConvertTo-RcApplicationBytes $chain[$entry[0]])}
 Write-UpgExisting (Join-Path $upgManagement 'server-installation.json') (ConvertTo-RcApplicationBytes $chain.management)
 $upgCandidate=$upgCode;$upgPlan.candidateCodeRoot=$upgCode;$upgPlan.expectedNewManifestSha256=$chain.manifestSha256
 Write-SetupJson $upgPlanPath $upgPlan
 Invoke-SetupSecurityPrivileges {[RackClickSetupSecurityNative]::SetAcl($upgPlanPath,('O:BAG:SYD:P(A;;FA;;;BA)(A;;FA;;;SY)(A;;FR;;;'+$upgRecord.serviceSid+')'))}
 $null=Invoke-UpgServiceChild 'Verify' $upgPlanPath
 $plain=$null
 try{$plain=$upgCredential.GetNetworkCredential().Password;$action=New-ScheduledTaskAction -Execute $upgRecord.backupExecutable -Argument $chain.management.backupArguments;$null=Set-ScheduledTask -TaskName $upgRecord.backupTaskName -Action $action -User $upgCredential.UserName -Password $plain}finally{$plain=$null}
 $postbootPath=Join-Path $upgManagement 'postboot-verification.json'
 if([IO.File]::Exists($postbootPath)){[IO.File]::Move($postbootPath,(Join-Path $upgTransaction 'postboot43-verification.json'))}
 Write-UpgJournal 'starting45'
 $upgExposed=$true
 Start-Service -Name $upgRecord.serviceName
 $until=[DateTime]::UtcNow.AddSeconds(150);$ready=$false
 while([DateTime]::UtcNow-lt$until){try{$current=Invoke-RestMethod -UseBasicParsing -Uri ($upgRecord.publicOrigin+'/health/ready') -TimeoutSec 5;if($current.status-ceq'ready'-and$current.schemaVersion-eq45){$ready=$true;break}}catch{};Start-Sleep -Milliseconds 500}
 if(-not$ready){Stop-RcApplicationUpgrade 'upgrade_ready45_not_confirmed'}
 Write-UpgJournal 'verifying_scheduled_backup45'
 $null=Enable-ScheduledTask -TaskName $upgRecord.backupTaskName
 $backupStart=[DateTime]::UtcNow;Start-ScheduledTask -TaskName $upgRecord.backupTaskName
 $until=[DateTime]::UtcNow.AddSeconds(300);$backupDone=$false
 while([DateTime]::UtcNow-lt$until){$task=Get-ScheduledTask -TaskName $upgRecord.backupTaskName;$info=Get-ScheduledTaskInfo -TaskName $upgRecord.backupTaskName;if($info.LastRunTime.ToUniversalTime()-ge$backupStart.AddSeconds(-2)-and$task.State-ne'Running'){if($info.LastTaskResult-ne0){Stop-RcApplicationUpgrade 'upgrade_backup45_failed'};$backupDone=$true;break};Start-Sleep -Milliseconds 500}
 if(-not$backupDone){Stop-RcApplicationUpgrade 'upgrade_backup45_unconfirmed'}
 $lastBackup=Read-UpgJson (Join-Path $upgRoot 'runtime\control\latest-backup.json')
 if(-not$lastBackup.success-or$lastBackup.exitCode-ne0-or$lastBackup.code-cne'scheduled_backup_complete'-or[DateTime]::Parse($lastBackup.createdUtc).ToUniversalTime()-lt$backupStart.AddSeconds(-2)){Stop-RcApplicationUpgrade 'upgrade_backup45_receipt_invalid'}
 $chain.management.scheduledBackupVerified=$true
 Write-UpgExisting (Join-Path $upgManagement 'server-installation.json') (ConvertTo-RcApplicationBytes $chain.management)
 foreach($oldTask in $upgOldTasks){if($oldTask.enabled){$null=Enable-ScheduledTask -TaskName $oldTask.name}else{$null=Disable-ScheduledTask -TaskName $oldTask.name}}
 $upgCommitted=$true;Write-UpgJournal 'committed'
 $upgExit=0;$answer=@{schemaVersion=1;valid=$true;success=$true;exitCode=0;code='application_update45_verified';installationId=$upgInputs.id;publicOrigin=$upgRecord.publicOrigin;schemaVersionAfter=45;dataAndSecurityUnchanged=$migration.comparison.dataAndSecurityUnchanged;unchangedTables=$migration.comparison.unchangedTables;mfaMaterialPreserved=$true;backupVerified=$true;windowsNetworkChanged=$false;accountsChanged=$false;reboot45Verified=$false;productAdopted=$false}
}catch{
 $code='application_update45_failed';if($_.Exception.Message-cmatch'^[a-z][a-z0-9_]{2,90}$'){$code=$_.Exception.Message}
 $answer=@{schemaVersion=1;valid=$false;success=$false;exitCode=1;code=$code;stage=$upgStage;installationId=$upgInputs.id;serviceStopped=$upgStopped;listener45MayBeExposed=$upgExposed;coldBackupVerified=$upgColdBackupVerified;journalPreserved=[bool]$upgTransaction;automaticDatabaseRollback=$false;errorType=$_.Exception.GetType().FullName;failureLine=$_.InvocationInfo.ScriptLineNumber;productAdopted=$false}
 if($upgJournal){try{Write-UpgJournal 'failed_preserved'}catch{}}
 if(-not$upgMigrationStarted-and-not$upgExposed){
  if($upgTaskChangesAttempted){
   try{foreach($oldTask in $upgOldTasks){if($oldTask.enabled){$null=Enable-ScheduledTask -TaskName $oldTask.name}else{$null=Disable-ScheduledTask -TaskName $oldTask.name}};$answer.sourceTaskStatesRestored=$true}catch{$answer.sourceTaskStatesRestored=$false}
  }
  if($upgStopped){try{Start-Service -Name $upgRecord.serviceName;$answer.sourceServiceRestartRequested=$true}catch{$answer.sourceServiceRestartRequested=$false}}
 }
}finally{
 if($upgCredential){$upgCredential.Password.Dispose()};if($upgZip){$upgZip.Dispose()};if($upgPayloadLock){$upgPayloadLock.Dispose()};if($upgOperationLock){$upgOperationLock.Dispose()}
 if($answer){$answer|ConvertTo-Json -Depth 5 -Compress}
}
exit $upgExit
