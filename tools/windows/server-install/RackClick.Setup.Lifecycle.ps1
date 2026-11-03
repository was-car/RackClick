#requires -Version 5.1
# Pure on import. Scheduled-task registration is explicit and administrator-only.
function Test-SetupUtcTimestamp($Value) {
    if($Value-isnot[string]-or$Value-cnotmatch'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,7})?Z$'){return $false}
    $parsed=[DateTimeOffset]::MinValue
    return [DateTimeOffset]::TryParse($Value,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::None,[ref]$parsed)
}
function Get-SetupRecordedInstallationState {
    param($Receipt,$Verification,$CurrentBootUtc,$ObservedUtc)
    # A protected receipt is evidence of a completed check, not a new health probe.
    # Never rewrite the original broker result or infer product adoption here.
    $state=[ordered]@{schemaVersion=1;status='unconfirmed';code='postboot_context_invalid';source='postboot-verification.json';rebootVerified=$false;currentHealthVerified=$false;productAdopted=$false}
    if($null-eq$Receipt-or($Receipt-isnot[Collections.IDictionary]-and$Receipt-isnot[pscustomobject])){return $state}
    $id=[guid]::Empty
    if(($Receipt.schemaVersion-isnot[int]-and$Receipt.schemaVersion-isnot[long])-or$Receipt.schemaVersion-ne1-or$Receipt.installationId-isnot[string]-or-not[guid]::TryParseExact($Receipt.installationId,'D',[ref]$id)-or$Receipt.installationId-cne$id.ToString('D')){return $state}
    $times=@{}
    foreach($entry in @(@('bootAtInstall',$Receipt.bootAtInstall),@('installedUtc',$Receipt.installedUtc),@('bootCurrent',$CurrentBootUtc),@('observedUtc',$ObservedUtc))){
        if(-not(Test-SetupUtcTimestamp $entry[1])){return $state}
        $times[$entry[0]]=[DateTimeOffset]::Parse($entry[1],[Globalization.CultureInfo]::InvariantCulture)
    }
    if($times.installedUtc-lt$times.bootAtInstall-or$times.observedUtc-lt$times.bootCurrent-or$times.observedUtc-lt$times.installedUtc){return $state}
    $state.installationId=$Receipt.installationId;$state.observedUtc=$ObservedUtc
    if($null-eq$Verification){$state.status='pending';$state.code='postboot_not_recorded';return $state}
    $state.code='postboot_record_invalid'
    if($Verification-isnot[Collections.IDictionary]-and$Verification-isnot[pscustomobject]){return $state}
    if(($Verification.schemaVersion-isnot[int]-and$Verification.schemaVersion-isnot[long])-or$Verification.schemaVersion-ne1-or$Verification.valid-isnot[bool]-or-not$Verification.valid-or$Verification.success-isnot[bool]-or-not$Verification.success-or($Verification.exitCode-isnot[int]-and$Verification.exitCode-isnot[long])-or$Verification.exitCode-ne0-or$Verification.code-isnot[string]-or$Verification.code-cne'postboot_verified'-or$Verification.rebootVerified-isnot[bool]-or-not$Verification.rebootVerified-or$Verification.productAdopted-isnot[bool]-or$Verification.productAdopted){return $state}
    if($Verification.installationId-isnot[string]-or$Verification.installationId-cne$Receipt.installationId){$state.code='postboot_installation_mismatch';return $state}
    if(-not(Test-SetupUtcTimestamp $Verification.bootUtc)-or-not(Test-SetupUtcTimestamp $Verification.checkedUtc)){return $state}
    $boot=[DateTimeOffset]::Parse($Verification.bootUtc,[Globalization.CultureInfo]::InvariantCulture)
    $checked=[DateTimeOffset]::Parse($Verification.checkedUtc,[Globalization.CultureInfo]::InvariantCulture)
    if($checked-lt$boot-or$checked-lt$times.installedUtc-or$checked-gt$times.observedUtc-or$boot-le$times.bootAtInstall){return $state}
    $state.bootUtc=$Verification.bootUtc;$state.checkedUtc=$Verification.checkedUtc
    if($boot-ne$times.bootCurrent){$state.status='stale';$state.code='postboot_record_from_other_boot';return $state}
    $state.status='recorded';$state.code='postboot_verification_recorded';$state.rebootVerified=$true
    return $state
}
function Test-SetupBackupScheduleSnapshot {
    param([hashtable]$Snapshot)
    foreach($key in @('enabled','triggerCount','triggerClass','triggerEnabled','daysInterval','startBoundary','expectedStartBoundary','multipleInstances','startWhenAvailable','executionTimeLimit')){if(-not$Snapshot.ContainsKey($key)){return $false}}
    return ($Snapshot.enabled-eq$true-and$Snapshot.triggerCount-eq1-and$Snapshot.triggerClass-ceq'MSFT_TaskDailyTrigger'-and$Snapshot.triggerEnabled-eq$true-and$Snapshot.daysInterval-eq1-and$Snapshot.startBoundary-ceq$Snapshot.expectedStartBoundary-and$Snapshot.startBoundary-cmatch'^\d{4}-\d{2}-\d{2}T03:00:00$'-and$Snapshot.multipleInstances-eq2-and$Snapshot.startWhenAvailable-eq$true-and$Snapshot.executionTimeLimit-ceq'PT30M')
}
function Test-SetupPostbootSnapshot {
    param([hashtable]$Snapshot)
    $required=@('bootCurrent','bootAtInstall','serviceState','serviceStartMode','serviceSid','expectedSid','healthStatus','schemaVersion','backupTaskState','backupTaskSid','backupLastResult','backupScheduleVerified')
    foreach($key in $required){if(-not$Snapshot.ContainsKey($key)){return @{valid=$false;code='postboot_snapshot_incomplete'}}}
    $old=[DateTimeOffset]::MinValue;$current=[DateTimeOffset]::MinValue
    # Receipt timestamps are written in invariant form; parsing with the server culture (for example de-DE) fails.
    if(-not[DateTimeOffset]::TryParse([string]$Snapshot.bootAtInstall,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::None,[ref]$old)-or-not[DateTimeOffset]::TryParse([string]$Snapshot.bootCurrent,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::None,[ref]$current)-or$current-le$old){return @{valid=$false;code='postboot_restart_not_observed'}}
    if($Snapshot.expectedSid-cnotmatch'^S-1-5-21-(\d+-){3}\d+$'-or$Snapshot.serviceSid-cne$Snapshot.expectedSid){return @{valid=$false;code='postboot_service_identity_changed'}}
    if($Snapshot.serviceState-cne'Running'-or$Snapshot.serviceStartMode-cne'Auto'){return @{valid=$false;code='postboot_service_not_automatic_running'}}
    $expectedSchema=14
    if($Snapshot.ContainsKey('expectedSchemaVersion')){
        if($Snapshot.expectedSchemaVersion-isnot[int]-or$Snapshot.expectedSchemaVersion-notin@(14,15,43,45)){return @{valid=$false;code='postboot_expected_schema_invalid'}}
        $expectedSchema=$Snapshot.expectedSchemaVersion
    }
    if($Snapshot.healthStatus-cne'ready'-or$Snapshot.schemaVersion-isnot[int]-or$Snapshot.schemaVersion-ne$expectedSchema){return @{valid=$false;code='postboot_application_not_ready'}}
    if($Snapshot.backupTaskState-cnotin@('Ready','Running')-or$Snapshot.backupTaskSid-cne$Snapshot.expectedSid-or$Snapshot.backupLastResult-ne0-or$Snapshot.backupScheduleVerified-ne$true){return @{valid=$false;code='postboot_backup_task_not_verified'}}
    return @{valid=$true;code='postboot_verified'}
}
function Resolve-SetupAccountSid([string]$Account) {
    try {
        if($Account-match'^S-1-'){return (New-Object Security.Principal.SecurityIdentifier($Account)).Value}
        # SCM may return the literal local alias even when registration used MACHINE\.
        if($Account.StartsWith('.\',[StringComparison]::Ordinal)){$Account=[Environment]::MachineName+'\'+$Account.Substring(2)}
        return (New-Object Security.Principal.NTAccount($Account)).Translate([Security.Principal.SecurityIdentifier]).Value
    }catch{
        # Identity translation messages may contain the account name; never propagate them.
        throw (New-Object InvalidOperationException('setup_account_sid_unresolved'))
    }
}
function Register-SetupLifecycleTasks {
    param([Management.Automation.PSCredential]$Credential,[string]$InstallationId,[string]$CodeRoot,[string]$ManifestPath,[string]$ManifestSha256,[string]$ManagementPath)
    Assert-SetupAdministrator
    $id=[guid]::Empty
    if(-not[guid]::TryParseExact($InstallationId,'D',[ref]$id)-or$InstallationId-cne$id.ToString('D')-or$CodeRoot-cne('C:\Program Files\RackClick\'+$InstallationId)-or$ManagementPath-cne('C:\ProgramData\RackClick\Instances\'+$InstallationId+'\management')-or$ManifestPath-cne('C:\ProgramData\RackClick\Instances\'+$InstallationId+'\instance\runtime\server-profile.json')-or$ManifestSha256-cnotmatch'^[a-f0-9]{64}$'){throw 'setup_task_binding_invalid'}
    Assert-SetupNoReparse $CodeRoot;Assert-SetupNoReparse $ManagementPath
    $backupName='RackClick-Backup-'+$InstallationId;$verifyName='RackClick-Verify-'+$InstallationId
    foreach($name in @($backupName,$verifyName)){if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'setup_task_already_exists'}}
    $exe="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $backupScript=Join-Path $CodeRoot 'operators\server-install\Invoke-RackClickScheduledBackup.ps1'
    $verifyScript=Join-Path $CodeRoot 'operators\server-install\Test-RackClickServerAfterReboot.ps1'
    foreach($file in @($backupScript,$verifyScript)){if(-not[IO.File]::Exists($file)){throw 'setup_task_script_missing'}}
    $backupArgs='-NoProfile -NonInteractive -ExecutionPolicy Bypass -File '+(ConvertTo-SetupArgument $backupScript)+' -ManifestPath '+(ConvertTo-SetupArgument $ManifestPath)+' -ExpectedManifestSha256 '+$ManifestSha256
    $verifyArgs='-NoProfile -NonInteractive -ExecutionPolicy Bypass -File '+(ConvertTo-SetupArgument $verifyScript)+' -ManagementPath '+(ConvertTo-SetupArgument $ManagementPath)
    $settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
    $backupTrigger=New-ScheduledTaskTrigger -Daily -At '03:00'
    # An unqualified local boundary follows the server's local clock through DST.
    $backupTrigger.StartBoundary=(Get-Date).Date.AddHours(3).ToString('yyyy-MM-ddTHH:mm:ss',[Globalization.CultureInfo]::InvariantCulture)
    $password=$null
    try {
        # The password exists only in process memory for the Task Scheduler API, never argv/files/logs.
        $password=$Credential.GetNetworkCredential().Password
        $null=Register-ScheduledTask -TaskName $backupName -Action (New-ScheduledTaskAction -Execute $exe -Argument $backupArgs) -Trigger $backupTrigger -Settings $settings -User $Credential.UserName -Password $password -RunLevel Limited -Description 'RackClick: verified PostgreSQL backup, no automatic deletion.'
    }finally{$password=$null}
    $verifySettings=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)
    $null=Register-ScheduledTask -TaskName $verifyName -Action (New-ScheduledTaskAction -Execute $exe -Argument $verifyArgs) -Trigger (New-ScheduledTaskTrigger -AtStartup) -Settings $verifySettings -User 'SYSTEM' -RunLevel Highest -Description 'RackClick: verify real reboot, service identity and HTTPS readiness.'
    return @{backupTaskName=$backupName;postbootTaskName=$verifyName;backupExecutable=$exe;backupArguments=$backupArgs;backupStartBoundary=$backupTrigger.StartBoundary}
}
