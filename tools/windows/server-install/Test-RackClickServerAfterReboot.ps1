#requires -Version 5.1
[CmdletBinding()]
param([string]$ManagementPath='')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'RackClick.Setup.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.Security.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.Lifecycle.ps1')
$postbootResult=[ordered]@{schemaVersion=1;valid=$false;success=$false;exitCode=1;code='postboot_failed';checkedUtc=[DateTime]::UtcNow.ToString('o');rebootVerified=$false;productAdopted=$false}
$postbootWritable=$false;$postbootStream=$null
try {
    Assert-SetupAdministrator;Assert-SetupPath $ManagementPath 'management';Assert-SetupManagementAcl $ManagementPath
    $postbootPath=Join-Path $ManagementPath 'server-installation.json';Assert-SetupNoReparse $postbootPath;Assert-SetupManagementAcl $postbootPath
    $postbootStream=[IO.File]::Open($postbootPath,'Open','Read','Read')
    if($postbootStream.Length-gt65536){throw 'postboot_receipt_invalid'}
    $postbootReader=New-Object IO.StreamReader($postbootStream,(New-Object Text.UTF8Encoding($false,$true)),$true,4096,$true)
    try{$postbootReceipt=$postbootReader.ReadToEnd()|ConvertFrom-Json -ErrorAction Stop}finally{$postbootReader.Dispose()}
    $postbootId=[IO.Path]::GetFileName([IO.Path]::GetDirectoryName($ManagementPath))
    if($postbootReceipt.schemaVersion-ne1-or$postbootReceipt.installationId-cne$postbootId-or$postbootReceipt.managementPath-cne$ManagementPath-or$postbootReceipt.instancePath-cne('C:\ProgramData\RackClick\Instances\'+$postbootId+'\instance')-or$postbootReceipt.codeRoot-cne('C:\Program Files\RackClick\'+$postbootId)-or$postbootReceipt.serviceName-cnotmatch'^RackClick(?:-Recovery-[a-f0-9]{8,32})?$'-or$postbootReceipt.manifestSha256-cnotmatch'^[a-f0-9]{64}$'-or$postbootReceipt.backupTaskName-cne('RackClick-Backup-'+$postbootId)){throw 'postboot_receipt_binding_invalid'}
    $postbootWritable=$true
    # Read-SetupPreparedFile checks every parent and the file itself with native handles that open reparse points.
    # A path-based Get-Item walk here fails for an elevated administrator who cannot read the instance folder attributes.
    $postbootBytes=Read-SetupPreparedFile -InstancePath $postbootReceipt.instancePath -RelativePath 'runtime/server-profile.json' -ServiceSid $postbootReceipt.serviceSid
    $postbootSha=[Security.Cryptography.SHA256]::Create()
    try{$postbootDigest=([BitConverter]::ToString($postbootSha.ComputeHash($postbootBytes))).Replace('-','').ToLowerInvariant()}finally{$postbootSha.Dispose()}
    if($postbootDigest-cne$postbootReceipt.manifestSha256){throw 'postboot_manifest_changed'}
    $postbootService=Get-CimInstance Win32_Service -Filter ("Name='"+$postbootReceipt.serviceName+"'")
    $postbootExpectedBinary=(ConvertTo-SetupArgument (Join-Path $postbootReceipt.instancePath 'content\dependencies\dotnet\dotnet.exe'))+' '+(ConvertTo-SetupArgument (Join-Path $postbootReceipt.codeRoot 'service\RackClick.WindowsService.dll'))+' --config '+(ConvertTo-SetupArgument (Join-Path $postbootReceipt.instancePath 'service-config.json'))
    if($null-eq$postbootService-or$postbootService.PathName-cne$postbootExpectedBinary){throw 'postboot_service_binary_changed'}
    $postbootTask=Get-ScheduledTask -TaskName $postbootReceipt.backupTaskName -ErrorAction Stop
    $postbootTaskInfo=Get-ScheduledTaskInfo -TaskName $postbootReceipt.backupTaskName -ErrorAction Stop
    if(@($postbootTask.Triggers).Count-ne1){throw 'postboot_backup_schedule_changed'}
    $postbootTrigger=$postbootTask.Triggers[0]
    $postbootSchedule=Test-SetupBackupScheduleSnapshot @{enabled=$postbootTask.Settings.Enabled;triggerCount=@($postbootTask.Triggers).Count;triggerClass=$postbootTrigger.CimClass.CimClassName;triggerEnabled=$postbootTrigger.Enabled;daysInterval=$postbootTrigger.DaysInterval;startBoundary=$postbootTrigger.StartBoundary;expectedStartBoundary=$postbootReceipt.backupStartBoundary;multipleInstances=[int]$postbootTask.Settings.MultipleInstances;startWhenAvailable=$postbootTask.Settings.StartWhenAvailable;executionTimeLimit=$postbootTask.Settings.ExecutionTimeLimit}
    if(-not$postbootSchedule){throw 'postboot_backup_schedule_changed'}
    if($postbootReceipt.scheduledBackupVerified-ne$true-or$postbootTask.Principal.LogonType-ne'Password'-or$postbootTask.Principal.RunLevel-ne'Limited'-or@($postbootTask.Actions).Count-ne1-or$postbootTask.Actions[0].Execute-cne$postbootReceipt.backupExecutable-or$postbootTask.Actions[0].Arguments-cne$postbootReceipt.backupArguments-or$postbootTaskInfo.LastRunTime.ToUniversalTime()-lt([DateTime]::Parse($postbootReceipt.installedUtc,[Globalization.CultureInfo]::InvariantCulture).ToUniversalTime().AddSeconds(-2))){throw 'postboot_backup_task_changed_or_never_ran'}
    $postbootUri=$null
    if(-not[Uri]::TryCreate($postbootReceipt.publicOrigin,[UriKind]::Absolute,[ref]$postbootUri)-or$postbootUri.Scheme-cne'https'-or$postbootUri.UserInfo-ne''-or$postbootUri.AbsolutePath-ne'/'-or$postbootUri.Query-ne''-or$postbootUri.Fragment-ne''){throw 'postboot_https_origin_invalid'}
    # Normal Windows TLS validation; never bypass certificate or hostname checks.
    try{$postbootHealth=Invoke-RestMethod -Uri ($postbootReceipt.publicOrigin+'/health/ready') -TimeoutSec 10 -UseBasicParsing}catch{throw 'postboot_https_health_failed'}
    $postbootSnapshot=@{bootCurrent=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o');bootAtInstall=$postbootReceipt.bootAtInstall;serviceState=$postbootService.State;serviceStartMode=$postbootService.StartMode;serviceSid=(Resolve-SetupAccountSid $postbootService.StartName);expectedSid=$postbootReceipt.serviceSid;healthStatus=$postbootHealth.status;schemaVersion=$postbootHealth.schemaVersion;backupTaskState=[string]$postbootTask.State;backupTaskSid=(Resolve-SetupAccountSid $postbootTask.Principal.UserId);backupLastResult=$postbootTaskInfo.LastTaskResult;backupScheduleVerified=$postbootSchedule}
    if($null-ne$postbootReceipt.PSObject.Properties['applicationSchemaVersion']){$postbootSnapshot.expectedSchemaVersion=$postbootReceipt.applicationSchemaVersion}
    $postbootVerdict=Test-SetupPostbootSnapshot $postbootSnapshot
    if(-not$postbootVerdict.valid){throw $postbootVerdict.code}
    $postbootResult.valid=$true;$postbootResult.success=$true;$postbootResult.exitCode=0;$postbootResult.code='postboot_verified';$postbootResult.rebootVerified=$true
    $postbootResult.installationId=$postbootId;$postbootResult.bootUtc=$postbootSnapshot.bootCurrent
}catch{
    if($_.Exception.Message-cmatch'^postboot_[a-z0-9_]+$'){$postbootResult.code=$_.Exception.Message}
}finally{
    if($null-ne$postbootStream){$postbootStream.Dispose()}
    if($postbootWritable){try{Write-SetupJson (Join-Path $ManagementPath 'postboot-verification.json') $postbootResult}catch{$postbootResult.valid=$false;$postbootResult.success=$false;$postbootResult.exitCode=1;$postbootResult.code='postboot_result_write_failed'}}
}
$postbootResult|ConvertTo-Json -Compress
exit $postbootResult.exitCode
