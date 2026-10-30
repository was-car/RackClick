#requires -Version 5.1
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot '..\..\windows\server-install\RackClick.Setup.ps1')
. (Join-Path $PSScriptRoot '..\..\windows\server-install\RackClick.Setup.ServiceStatus.ps1')
$id='606b8c29-41de-4dc0-b63d-ade836000d9e';$sid='S-1-5-21-111-222-333-1001';$checks=0
if($null-ne(Get-Command Resolve-SetupAccountSid -ErrorAction SilentlyContinue)){throw 'lifecycle_dependency_loaded'};$checks++
foreach($entry in @(@('S-1-5-18','sid'),@('.\PRIVATE_SECRET_SENTINEL','local_dot'),@('DOMAIN\PRIVATE_SECRET_SENTINEL','qualified'),@('PRIVATE_SECRET_SENTINEL@example.invalid','upn'),@('PRIVATE_SECRET_SENTINEL','plain'),@('','empty'),@('   ','empty'),@('./PRIVATE_SECRET_SENTINEL','plain'))){
    if((Get-SetupServiceDiagnosticAccountFormat $entry[0])-cne$entry[1]){throw 'account_format_failed'};$checks++
}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
try{
    $currentSid=$identity.User.Value;$currentName=$identity.Name
    $currentLocalAlias='.\'+$currentName.Substring($currentName.LastIndexOf('\')+1)
    if((Resolve-SetupServiceDiagnosticAccountSid $identity.User.Value)-cne$identity.User.Value){throw 'current_sid_resolution_failed'};$checks++
    if((Resolve-SetupServiceDiagnosticAccountSid $identity.Name)-cne$identity.User.Value){throw 'current_account_resolution_failed'};$checks++
    if((Resolve-SetupServiceDiagnosticAccountSid $currentLocalAlias)-cne$currentSid){throw 'current_local_alias_resolution_failed'};$checks++
}finally{$identity.Dispose()}
$unknownLocalAlias='.\rc_missing_'+[guid]::NewGuid().ToString('N').Substring(0,8)
foreach($badAccount in @('','S-1-5-PRIVATE_SECRET_SENTINEL','PRIVATE_SECRET_SENTINEL/invalid','.\PRIVATE_SECRET_SENTINEL/invalid',$unknownLocalAlias)){
    $rejected=$false
    try{$null=Resolve-SetupServiceDiagnosticAccountSid $badAccount}catch{
        if($_.Exception.Message-cne'report_service_account_unresolved'-or$_.Exception.ToString()-like'*PRIVATE_SECRET_SENTINEL*'){throw 'account_failure_not_sanitized'}
        if($_.Exception.ToString().Contains($unknownLocalAlias.Substring(2))){throw 'unknown_alias_failure_not_sanitized'}
        $data=$_.Exception.Data
        if((($data.Keys|Sort-Object)-join',')-cne'accountErrorHResult,accountErrorType,accountNameForm'-or$data['accountNameForm']-cne(Get-SetupServiceDiagnosticAccountFormat $badAccount)-or$data['accountErrorType']-cnotin@('System.Security.Principal.IdentityNotMappedException','System.ArgumentException','System.Security.SecurityException','unresolved')-or$data['accountErrorHResult']-isnot[int]){throw 'account_failure_metadata_invalid'}
        $dataJson=$data|ConvertTo-Json -Compress
        if($dataJson-like'*PRIVATE_SECRET_SENTINEL*'-or$dataJson.Contains($unknownLocalAlias.Substring(2))){throw 'account_failure_data_not_sanitized'}
        if($badAccount-eq''-and$data['accountErrorType']-cne'System.ArgumentException'){throw 'empty_account_error_type_invalid'}
        if($badAccount.StartsWith('.\',[StringComparison]::Ordinal)-and$data['accountErrorType']-cne'System.Security.Principal.IdentityNotMappedException'){throw 'local_alias_error_type_invalid'}
        $rejected=$true
    }
    if(-not$rejected){throw 'invalid_account_resolved'};$checks++
}
$xml='<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event"><System><Provider Name="Service Control Manager"/><EventID>7031</EventID><EventRecordID>17</EventRecordID><TimeCreated SystemTime="2026-10-20T12:00:00Z"/></System><EventData><Data Name="param1">RackClick '+$id+'</Data><Data Name="param2">%%1067</Data><Data Name="param3">PRIVATE_SECRET_SENTINEL</Data></EventData></Event>'
$summary=ConvertTo-SetupServiceEventSummary $xml 'RackClick' $id
if($null-eq$summary-or$summary.eventId-ne7031-or$summary.errorCodes[0]-ne1067-or$summary.correlation-cne'service_name'-or($summary|ConvertTo-Json)-like'*PRIVATE_SECRET_SENTINEL*'){throw 'event_sanitization_failed'};$checks++
foreach($bad in @($xml.Replace(('RackClick '+$id),'OtherService'),$xml.Replace('Service Control Manager','OtherProvider'),'<notxml>',('<!DOCTYPE Event [<!ENTITY probe SYSTEM "file:///C:/Windows/win.ini">]>'+ $xml),('x'*65537))){
    if($null-ne(ConvertTo-SetupServiceEventSummary $bad 'RackClick' $id)){throw 'invalid_event_exported'};$checks++
}
$app=$xml.Replace('Service Control Manager','.NET Runtime').Replace(('RackClick '+$id),'RackClick.WindowsService.dll System.InvalidOperationException PRIVATE_SECRET_SENTINEL')
$summary=ConvertTo-SetupServiceEventSummary $app 'RackClick' $id
if($summary.correlation-cne'host_executable_not_instance_specific'-or$summary.exceptionTypes[0]-cne'System.InvalidOperationException'-or($summary|ConvertTo-Json)-like'*PRIVATE_SECRET_SENTINEL*'){throw 'application_summary_failed'};$checks++
$script:cimQueries=0;$script:serviceStartName=$sid
function Get-CimInstance([string]$ClassName,[string]$Filter){
    $script:cimQueries++
    if($ClassName-ceq'Win32_OperatingSystem'){return [pscustomobject]@{LastBootUpTime=[DateTime]'2026-10-20T11:00:00Z'}}
    if($ClassName-cne'Win32_Service'-or$Filter-cne"Name='RackClick'"){throw 'unexpected_query'}
    $instance='C:\ProgramData\RackClick\Instances\'+$id+'\instance';$codeRoot='C:\Program Files\RackClick\'+$id
    $expected=(ConvertTo-SetupArgument ($instance+'\content\dependencies\dotnet\dotnet.exe'))+' '+(ConvertTo-SetupArgument ($codeRoot+'\service\RackClick.WindowsService.dll'))+' --config '+(ConvertTo-SetupArgument ($instance+'\service-config.json'))
    return [pscustomobject]@{State='Stopped';StartMode='Auto';ExitCode=[uint32]1067;ServiceSpecificExitCode=[uint32]0;ProcessId=[uint32]0;StartName=$script:serviceStartName;PathName=$expected;Password='PRIVATE_SECRET_SENTINEL'}
}
function Get-WinEvent($FilterHashtable,$MaxEvents){return @()}
function Get-SetupServicePrivateDiagnostic([string]$InstanceId,[string]$ServiceSid){return @{status='fixture';instanceId=$InstanceId}}
$snapshot=Get-SetupServiceDiagnostic $id $sid 'RackClick'
if($snapshot.service.status-cne'found'-or$snapshot.service.state-cne'Stopped'-or$snapshot.service.win32ExitCode-ne1067-or-not$snapshot.service.accountSidMatches-or-not$snapshot.service.executableBindingMatches-or$snapshot.boot.status-cne'read'-or$snapshot.private.status-cne'fixture'){throw 'snapshot_failed'};$checks++
if(($snapshot|ConvertTo-Json -Depth 10)-like'*PRIVATE_SECRET_SENTINEL*'-or$snapshot.servicesChanged-ne0-or$snapshot.databasesChanged-ne0){throw 'snapshot_secret_or_mutation_claim'};$checks++
$script:serviceStartName=$currentLocalAlias
$aliasSnapshot=Get-SetupServiceDiagnostic $id $currentSid 'RackClick'
if($aliasSnapshot.service.status-cne'found'-or$aliasSnapshot.service.accountSidMatches-ne$true-or$aliasSnapshot.service.Contains('accountSidStatus')){throw 'local_alias_snapshot_failed'};$checks++
$aliasMismatch=Get-SetupServiceDiagnostic $id $sid 'RackClick'
if($aliasMismatch.service.status-cne'found'-or$aliasMismatch.service.accountSidMatches-ne$false-or$aliasMismatch.service.Contains('accountSidStatus')){throw 'local_alias_snapshot_mismatch_failed'};$checks++
$script:serviceStartName='S-1-5-21-111-222-333-1002'
$mismatch=Get-SetupServiceDiagnostic $id $sid 'RackClick'
if($mismatch.service.status-cne'found'-or$mismatch.service.accountSidMatches-ne$false-or$mismatch.service.Contains('accountSidStatus')){throw 'account_mismatch_not_reported'};$checks++
$script:serviceStartName=$unknownLocalAlias
$unverified=Get-SetupServiceDiagnostic $id $sid 'RackClick'
$unverifiedJson=$unverified|ConvertTo-Json -Depth 10
if($unverified.service.status-cne'found'-or$unverified.service.accountSidStatus-cne'unverified'-or$unverified.service.Contains('accountSidMatches')-or$unverifiedJson-like'*PRIVATE_SECRET_SENTINEL*'-or$unverifiedJson.Contains($unknownLocalAlias.Substring(2))){throw 'unresolved_account_not_sanitized'};$checks++
$script:serviceStartName=$sid
$before=$script:cimQueries
foreach($bad in @(@($id,$sid,'OtherService'),@('../wrong',$sid,'RackClick'),@($id,'S-1-5-21-1-2-3-500','RackClick'),@($id,$sid,"RackClick' OR Name='Other"))){
    $rejected=$false;try{$null=Get-SetupServiceDiagnostic $bad[0] $bad[1] $bad[2]}catch{if($_.Exception.Message-cne'report_service_binding_invalid'){throw};$rejected=$true}
    if(-not$rejected){throw 'binding_accepted'};$checks++
}
if($script:cimQueries-ne$before){throw 'query_before_validation'};$checks++
. (Join-Path $PSScriptRoot '..\..\windows\server-install\RackClick.Setup.Diagnostics.ps1')
function Read-SetupDiagnosticBinding([string]$AttemptId){return @{id=$AttemptId;serviceSid=$sid;serviceName='RackClick'}}
function Read-SetupPrivateDiagnosticBytes {throw 'report_fixture_private_missing'}
$fixture=Join-Path ([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\.local'))) ('service-status-'+[guid]::NewGuid().ToString('N')+'\'+$id)
$null=[IO.Directory]::CreateDirectory($fixture)
$attempt=Get-SetupAttemptDiagnostic $fixture @([Security.Principal.WindowsIdentity]::GetCurrent().User.Value)
if($attempt.serviceDiagnostics.instanceId-cne$id-or$attempt.serviceDiagnostics.service.state-cne'Stopped'-or$attempt.serviceDiagnostics.private.status-cne'fixture'){throw 'attempt_missing_service_snapshot'};$checks++
if(($attempt|ConvertTo-Json -Depth 14)-like'*PRIVATE_SECRET_SENTINEL*'){throw 'attempt_exported_private_value'};$checks++
@{valid=$true;checks=$checks;cimQueries=$script:cimQueries;realAccountResolution=$true;realLocalAliasResolution=$true;realServiceQueries=0;servicesChanged=0;eventLogsChanged=0;limits='Current Windows SID/account/local alias resolved read-only; service/event snapshots mocked without Lifecycle; no VM operation or runtime root-cause reproduction.'}|ConvertTo-Json -Compress
