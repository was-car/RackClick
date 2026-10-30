#requires -Version 5.1
param()
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\..\windows\server-install\RackClick.Setup.Lifecycle.ps1')
$snapshot=@{bootCurrent='2026-10-20T07:00:00Z';bootAtInstall='2026-10-19T07:00:00Z';serviceState='Running';serviceStartMode='Auto';serviceSid='S-1-5-21-1-2-3-1001';expectedSid='S-1-5-21-1-2-3-1001';healthStatus='ready';schemaVersion=13;backupTaskState='Ready';backupTaskSid='S-1-5-21-1-2-3-1001';backupLastResult=0;backupScheduleVerified=$true}
$count=0
if(-not(Test-SetupPostbootSnapshot $snapshot).valid){throw 'valid postboot state rejected'};$count++
foreach($case in @(
    @('bootCurrent','2026-10-19T07:00:00Z','postboot_restart_not_observed'),
    @('bootCurrent','2026-10-18T07:00:00Z','postboot_restart_not_observed'),
    @('bootAtInstall','invalid','postboot_restart_not_observed'),
    @('serviceSid','S-1-5-18','postboot_service_identity_changed'),
    @('serviceState','Stopped','postboot_service_not_automatic_running'),
    @('serviceStartMode','Manual','postboot_service_not_automatic_running'),
    @('healthStatus','starting','postboot_application_not_ready'),
    @('schemaVersion',12,'postboot_application_not_ready'),
    @('backupTaskState','Disabled','postboot_backup_task_not_verified'),
    @('backupTaskSid','S-1-5-18','postboot_backup_task_not_verified'),
    @('backupLastResult',267011,'postboot_backup_task_not_verified'),
    @('backupScheduleVerified',$false,'postboot_backup_task_not_verified')
)){
    $copy=$snapshot.Clone();$copy[$case[0]]=$case[1];$answer=Test-SetupPostbootSnapshot $copy
    if($answer.valid-or$answer.code-cne$case[2]){throw ('invalid postboot accepted: '+$case[0])};$count++
}
$missing=$snapshot.Clone();$missing.Remove('bootCurrent');if((Test-SetupPostbootSnapshot $missing).code-cne'postboot_snapshot_incomplete'){throw 'incomplete snapshot accepted'};$count++
$schedule=@{enabled=$true;triggerCount=1;triggerClass='MSFT_TaskDailyTrigger';triggerEnabled=$true;daysInterval=1;startBoundary='2026-10-19T03:00:00';expectedStartBoundary='2026-10-19T03:00:00';multipleInstances=2;startWhenAvailable=$true;executionTimeLimit='PT30M'}
if(-not(Test-SetupBackupScheduleSnapshot $schedule)){throw 'valid daily schedule rejected'};$count++
foreach($case in @(@('enabled',$false),@('triggerCount',0),@('triggerClass','MSFT_TaskTimeTrigger'),@('triggerEnabled',$false),@('daysInterval',2),@('startBoundary','2026-10-19T04:00:00'),@('multipleInstances',0),@('startWhenAvailable',$false),@('executionTimeLimit','PT0S'))){$copy=$schedule.Clone();$copy[$case[0]]=$case[1];if(Test-SetupBackupScheduleSnapshot $copy){throw ('invalid daily schedule accepted '+$case[0])};$count++}
@{valid=$true;checks=$count;environment='Windows PowerShell; pure postboot policy';actualReboots=0;tasksRegistered=0;serverChanges=0}|ConvertTo-Json -Compress
