#requires -Version 5.1
[CmdletBinding()]
param([string]$OutputPath='',[switch]$Simulation)
$ErrorActionPreference='Stop'
$sourceRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\windows\server-install'))
if($Simulation) {
    # Isolated process only: no Windows privilege API is invoked by these stubs.
    Add-Type -TypeDefinition @'
using System.Collections.Generic;
public static class RackClickSetupSecurityNative {
 public static List<string> Calls=new List<string>();
 public static bool FailRestore=false;
 public static uint Privilege(string name,uint value){Calls.Add(name+":"+value);if(FailRestore&&value==0)throw new System.InvalidOperationException("NEVER_EXPORT_SIMULATED_SECRET");return 0;}
}
'@
    . (Join-Path $sourceRoot 'RackClick.Setup.Security.ps1')
    . (Join-Path $sourceRoot 'RackClick.Setup.ServiceDiagnostics.ps1')
    function Assert-SetupAdministrator {}
    function Get-SetupServicePrivateDiagnosticAtRoot([string]$Root,[string]$ServiceSid) {
        if($Root-cne'C:\ProgramData\RackClick\Instances\606b8c29-41de-4dc0-b63d-ade836000d9e\instance'){throw 'wrong root'}
        return @{status='observed'}
    }
    $sid='S-1-5-21-100-200-300-1001'
    $answer=Get-SetupServicePrivateDiagnostic '606b8c29-41de-4dc0-b63d-ade836000d9e' $sid
    if($answer.status-cne'observed'-or([RackClickSetupSecurityNative]::Calls-join',')-cne'SeBackupPrivilege:2,SeBackupPrivilege:0'){throw 'Privilege simulation did not restore previous flags'}
    [RackClickSetupSecurityNative]::Calls.Clear()
    function Get-SetupServicePrivateDiagnosticAtRoot {throw 'NEVER_EXPORT_SIMULATED_SECRET'}
    $answer=Get-SetupServicePrivateDiagnostic '606b8c29-41de-4dc0-b63d-ade836000d9e' $sid
    if($answer.status-cne'unavailable'-or($answer|ConvertTo-Json -Depth 8)-like'*NEVER_EXPORT*'-or([RackClickSetupSecurityNative]::Calls-join',')-cne'SeBackupPrivilege:2,SeBackupPrivilege:0'){throw 'Failure simulation leaked text or did not restore flags'}
    [RackClickSetupSecurityNative]::FailRestore=$true
    $answer=Get-SetupServicePrivateDiagnostic '606b8c29-41de-4dc0-b63d-ade836000d9e' $sid
    if($answer.status-cne'unavailable'-or$answer.failure.code-cne'service_privilege_restore_failed'-or($answer|ConvertTo-Json -Depth 8)-like'*NEVER_EXPORT*'){throw 'Restore failure escaped sanitized observation'}
    @{valid=$true;simulated=$true;passed=3}|ConvertTo-Json -Compress
    exit 0
}
. (Join-Path $sourceRoot 'RackClick.Setup.Security.ps1')
. (Join-Path $sourceRoot 'RackClick.Setup.ServiceDiagnostics.ps1')
if(Test-SetupAdministrator){throw 'Non-elevated test required'}
if('RackClickSetupServiceDiagnosticNative'-as[type]){throw 'Import initialized native code'}
$checks=New-Object Collections.Generic.List[string]
$checks.Add('Import is pure: native code and privileges remain uninitialized')
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('RackClick-ServiceDiagnostics-'+[guid]::NewGuid().ToString('N'))
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$acl=New-Object Security.AccessControl.DirectorySecurity
$acl.SetSecurityDescriptorSddlForm(('O:'+$sid+'G:SYD:P(A;OICI;FA;;;'+$sid+')(A;OICI;FA;;;SY)'))
$null=[IO.Directory]::CreateDirectory($fixture,$acl)
foreach($relative in @('runtime\logs','runtime\control','deployment\instance\pgdata')){$null=[IO.Directory]::CreateDirectory((Join-Path $fixture $relative))}
$utf8=New-Object Text.UTF8Encoding($false,$true)
$secret='NEVER_EXPORT_PASSWORD_CONNECTION_STRING_C:\Private\UserData'
$ids=@('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000005','00000000-0000-0000-0000-000000000006')
function Write-ServiceFixture([string]$Relative,[string]$Text) {
    $path=Join-Path $fixture $Relative
    $null=[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($path))
    [IO.File]::WriteAllText($path,$Text,$utf8)
    return $path
}
function Get-ServiceFixtureState([string]$RunId,[string]$State='failed',[string]$Code='postgres_start_failed') {
    return (@{schemaVersion=1;instanceId='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';runId=$RunId;status=$State;code=$Code;utc='2026-10-20T00:00:00.0000000Z';publicOrigin=$secret;requestRelativePath=$secret;password=$secret}|ConvertTo-Json -Compress)
}
for($i=0;$i-lt$ids.Count;$i++) {
    $record=@{timestamp='2026-10-20T00:00:00.0000000+00:00';code='runtime_unexpected_exit';runId=$ids[$i];exitCode=2;password=$secret;message=$secret}|ConvertTo-Json -Compress
    $path=Write-ServiceFixture ('runtime\logs\host-'+$ids[$i]+'.jsonl') ($record+"`n")
    [IO.File]::SetLastWriteTimeUtc($path,([datetime]'2026-10-20T00:00:00Z').AddMinutes($i))
    $null=Write-ServiceFixture ('runtime\control\launcher-'+$ids[$i]+'\run-state.json') (Get-ServiceFixtureState $ids[$i])
    $null=Write-ServiceFixture ('runtime\control\launcher-'+$ids[$i]+'\launcher-error.log') ('System.InvalidOperationException: postgres_start_failed '+$secret+"`r`n"+'at SecretScript.ps1: line 9')
}
$null=Write-ServiceFixture 'runtime\control\active-run.json' (Get-ServiceFixtureState $ids[5])
$null=Write-ServiceFixture 'deployment\instance\pgdata\postmaster.pid' ("4321`n"+$secret+"`n1792454400`n55432`n"+$secret+"`n127.0.0.1`n123456 0`nready`n")
foreach($relative in @('runtime\logs\request.json','runtime\control\environment.json','runtime\control\launcher-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa\run-state.json','runtime\control\launcher-00000000-0000-0000-0000-000000000006\request.json','private\admin-login.json','private\certificate.pfx')){$null=Write-ServiceFixture $relative $secret}
$null=Write-ServiceFixture 'runtime\logs\host-INVALID-SECRET.jsonl' $secret
$null=Write-ServiceFixture 'runtime\logs\NEVER_EXPORT_FILENAME_ONLY.jsonl' $secret
$before=(Get-Acl -LiteralPath $fixture).Sddl
$snapshot=Get-SetupServicePrivateDiagnosticAtRoot $fixture $sid
if($snapshot.status-cne'observed'-or$snapshot.hostDirectory.status-cne'enumerated'-or$snapshot.hostLogs.Count-ne5-or$snapshot.hostLogs[0].runId-cne$ids[5]-or@($snapshot.hostLogs|Where-Object {$_.runId-ceq$ids[0]}).Count-ne0){throw 'Newest five bounded host logs not selected'}
$checks.Add('Native directory enumeration and handle metadata select newest five of six host GUID logs')
if($snapshot.activeRun.fields.runId-cne$ids[5]-or$snapshot.launcherRuns.Count-ne5-or$snapshot.launcherRuns[0].runState.fields.state-cne'failed'){throw 'Related run states lost'}
$checks.Add('Active run and at most five related launcher runs are correlated by RunId; internal instance UUID may differ')
if($snapshot.launcherRuns[0].error.fields.errorType-cne'System.InvalidOperationException'-or$snapshot.launcherRuns[0].error.fields.code-cne'postgres_start_failed'){throw 'Safe error summary lost'}
$checks.Add('Launcher error exports known CLR type/code only')
if($snapshot.postmaster.status-cne'parsed'-or$snapshot.postmaster.fields.processId-ne4321-or$snapshot.postmaster.fields.port-ne55432-or$snapshot.postmaster.fields.state-cne'ready'-or$snapshot.postmaster.processLivenessVerified){throw 'Postmaster summary wrong'}
$checks.Add('Postmaster exports only PID/port/state/start time; no claim that process is alive')
$json=$snapshot|ConvertTo-Json -Depth 15 -Compress
if($json-like'*NEVER_EXPORT*'-or$json-like'*Private*UserData*'-or$json-like'*SecretScript*'-or$json-like'*aaaaaaaa-aaaa*'-or$json-like'*requestRelativePath*'-or$json-like'*publicOrigin*'){throw 'Private or unrelated data exported'}
$checks.Add('Unknown files, unrelated launchers, credentials, origins, paths and raw messages are excluded')
if((Get-Acl -LiteralPath $fixture).Sddl-cne$before){throw 'Collector modified directory ACL'}
$checks.Add('Collection leaves fixture directory security descriptor unchanged')
foreach($relative in @('../private/admin-login.json','private/admin-login.json','runtime/control/launcher-00000000-0000-0000-0000-000000000006/request.json','C:\Windows\win.ini',"runtime/logs/host-$($ids[5]).jsonl`r`nsecret",'runtime/logs/host-00000000-0000-0000-0000-000000000006.jsonl/../request.json')) {
    $denied=$false;try{$null=Read-SetupServiceDiagnosticLeaf $fixture $relative $sid}catch{if($_.Exception.Message-cne'service_relative_path_invalid'){throw};$denied=$true}
    if(-not$denied){throw 'Relative allowlist escaped'}
}
$checks.Add('Fixed leaf allowlist rejects traversal, absolute paths, requests and CRLF names before native access')
$path=Join-Path $fixture ('runtime\logs\host-'+$ids[5]+'.jsonl')
$foreign=Get-Acl -LiteralPath $path
$foreign.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule((New-Object Security.Principal.SecurityIdentifier('S-1-5-32-545')),'Read','Allow')))
Set-Acl -LiteralPath $path -AclObject $foreign
$foreignBefore=(Get-Acl -LiteralPath $path).Sddl
$obs=Get-SetupServiceHostObservation $fixture $ids[5] $sid
if($obs.status-cne'unavailable'-or$obs.failure.code-cne'setup_prepared_acl_invalid'-or(Get-Acl -LiteralPath $path).Sddl-cne$foreignBefore){throw 'Foreign file ACL accepted or changed'}
$checks.Add('Foreign file reader ACL is rejected unchanged')
$snapshot=Get-SetupServicePrivateDiagnosticAtRoot $fixture $sid
if($snapshot.hostDirectory.rejectedCandidateCount-ne1){throw 'Rejected metadata candidate omitted without counter'}
$checks.Add('Foreign candidate metadata is rejected and counted without exporting its content')
$private=New-Object Security.AccessControl.FileSecurity
$private.SetSecurityDescriptorSddlForm(('O:'+$sid+'G:SYD:P(A;;FA;;;'+$sid+')(A;;FA;;;SY)'))
Set-Acl -LiteralPath $path -AclObject $private
$record=@{timestamp='2026-10-20T00:00:00Z';code='start_failed';runId=$ids[5];exitCode=1;password=$secret}|ConvertTo-Json -Compress
$null=Write-ServiceFixture ('runtime\logs\host-'+$ids[5]+'.jsonl') ($record+"`n"+'malformed '+$secret+"`n"+(@{timestamp='2026-10-20T00:00:00Z';code=$secret;runId=$ids[5]}|ConvertTo-Json -Compress)+"`n")
$obs=Get-SetupServiceHostObservation $fixture $ids[5] $sid
if($obs.records.Count-ne1-or$obs.invalidLineCount-ne2-or($obs|ConvertTo-Json -Depth 8)-like'*NEVER_EXPORT*'){throw 'Malformed JSONL leak or wrong line count'}
$checks.Add('Malformed and unknown-code JSONL lines counted without raw error text; valid lines retained')
$null=Write-ServiceFixture ('runtime\logs\host-'+$ids[5]+'.jsonl') (($record+"`n")*1001)
if((Get-SetupServiceHostObservation $fixture $ids[5] $sid).failure.code-cne'service_line_limit'){throw 'JSONL line limit absent'}
$checks.Add('JSONL over 1000 lines is unavailable')
[IO.File]::WriteAllBytes($path,(New-Object byte[] 1048577))
if((Get-SetupServiceHostObservation $fixture $ids[5] $sid).failure.code-cne'setup_prepared_file_size_invalid'){throw 'Byte limit absent'}
$checks.Add('Native file read rejects over 1 MiB')
[IO.File]::WriteAllBytes($path,[byte[]]@(255,255))
if((Get-SetupServiceHostObservation $fixture $ids[5] $sid).failure.code-cne'service_utf8_invalid'){throw 'Invalid UTF8 accepted'}
$checks.Add('Invalid UTF8 explicitly unavailable without replacement decoding')
$null=Write-ServiceFixture ('runtime\logs\host-'+$ids[5]+'.jsonl') ('malformed '+$secret)
if((Get-SetupServiceHostObservation $fixture $ids[5] $sid).status-cne'unavailable'){throw 'Entirely invalid JSONL claimed parsed'}
$checks.Add('Host JSONL with no valid lifecycle record is unavailable')
$null=Write-ServiceFixture 'runtime\control\active-run.json' ('{"runId":"'+$ids[5]+'","password":"'+$secret+'"}')
if((Get-SetupServiceRunObservation $fixture 'runtime/control/active-run.json' $sid).status-cne'unavailable'){throw 'Untyped state accepted'}
$checks.Add('Missing schema/state/time in a run record is unavailable')
$null=Write-ServiceFixture 'runtime\control\active-run.json' (Get-ServiceFixtureState $ids[4])
if((Get-SetupServiceRunObservation $fixture 'runtime/control/active-run.json' $sid $ids[5]).status-cne'unavailable'){throw 'Unrelated run ID accepted'}
$checks.Add('Run record must match the captured expected RunId')
foreach($untrustedCode in @(('a'*64),'private_secret_sentinel','future_runtime_failure_unknown')) {
    $null=Write-ServiceFixture 'runtime\control\active-run.json' (Get-ServiceFixtureState $ids[5] 'failed' $untrustedCode)
    $obs=Get-SetupServiceRunObservation $fixture 'runtime/control/active-run.json' $sid
    $safeJson=$obs|ConvertTo-Json -Depth 8 -Compress
    if($obs.status-cne'unavailable'-or$obs.failure.code-cne'service_record_invalid'-or$safeJson.Contains($untrustedCode)){throw 'Unknown state code escaped finite vocabulary'}
    $null=Write-ServiceFixture ('runtime\control\launcher-'+$ids[5]+'\launcher-error.log') ('System.InvalidOperationException: '+$untrustedCode+' '+$secret)
    $obs=Get-SetupServiceLauncherErrorObservation $fixture $ids[5] $sid
    if($obs.fields.Contains('code')-or($obs|ConvertTo-Json -Depth 8 -Compress).Contains($untrustedCode)){throw 'Unknown exception code escaped finite vocabulary'}
}
$checks.Add('Run state and launcher error exclude 64-character hexadecimal secret token')
$checks.Add('Run state and launcher error exclude lowercase private sentinel token')
$checks.Add('Unrecognized future runtime code is unavailable or omitted without echoing its value')
foreach($knownCode in @('starting','ready','stopped','instance_stopped','launcher_failed','launcher_runtime_invalid','application_control_timeout','server_manifest_hash_mismatch')) {
    $null=Write-ServiceFixture 'runtime\control\active-run.json' (Get-ServiceFixtureState $ids[5] 'failed' $knownCode)
    $obs=Get-SetupServiceRunObservation $fixture 'runtime/control/active-run.json' $sid
    if($obs.status-cne'parsed'-or$obs.fields.code-cne$knownCode){throw 'Source-reviewed runtime code was lost'}
}
$checks.Add('Finite vocabulary preserves lifecycle, launcher, control and server constants')
$null=Write-ServiceFixture 'deployment\instance\pgdata\postmaster.pid' ("-1`n"+$secret+"`n1792454400`n70000`n"+$secret+"`n127.0.0.1`n0 0`n"+$secret)
if((Get-SetupServicePostmasterObservation $fixture $sid).status-cne'unavailable'){throw 'Malformed pid file accepted'}
$checks.Add('Postmaster invalid PID/port/state are rejected without paths from other lines')
$target=Join-Path $fixture 'junction-target';$null=[IO.Directory]::CreateDirectory($target)
$junction=Join-Path $fixture ('runtime\control\launcher-'+$ids[4])
$old=Join-Path $fixture ('retained-launcher-'+$ids[4]);Move-Item -LiteralPath $junction -Destination $old
$null=New-Item -ItemType Junction -Path $junction -Target $target
$obs=Get-SetupServiceRunObservation $fixture ('runtime/control/launcher-'+$ids[4]+'/run-state.json') $sid $ids[4]
if($obs.status-cne'unavailable'-or$obs.failure.code-cne'setup_reparse_not_allowed'){throw 'Junction ancestor accepted'}
$checks.Add('Private read rejects junction inside related launcher path without following it')
$junctionLog=Join-Path $fixture ('runtime\logs\host-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa.jsonl')
$null=New-Item -ItemType Junction -Path $junctionLog -Target $target
$snapshot=Get-SetupServicePrivateDiagnosticAtRoot $fixture $sid
if($snapshot.hostDirectory.rejectedCandidateCount-lt1-or($snapshot|ConvertTo-Json -Depth 15)-like'*NEVER_EXPORT*'){throw 'Junction metadata accepted'}
$checks.Add('Host GUID name pointing to a junction is rejected by handle metadata')
$logsPath=Join-Path $fixture 'runtime\logs';$logsAcl=Get-Acl -LiteralPath $logsPath
$logsAcl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule((New-Object Security.Principal.SecurityIdentifier('S-1-5-32-545')),'Read','Allow')))
Set-Acl -LiteralPath $logsPath -AclObject $logsAcl
$before=(Get-Acl -LiteralPath $logsPath).Sddl
$snapshot=Get-SetupServicePrivateDiagnosticAtRoot $fixture $sid
if($snapshot.hostDirectory.status-cne'unavailable'-or$snapshot.hostDirectory.failure.code-cne'service_acl_rejected'-or(Get-Acl -LiteralPath $logsPath).Sddl-cne$before){throw 'Foreign directory ACL accepted or changed'}
$checks.Add('Native directory enumeration rejects foreign directory DACL unchanged')
$limitRoot=Join-Path $fixture 'enumeration-limit';$null=[IO.Directory]::CreateDirectory($limitRoot)
for($i=0;$i-lt2050;$i++){[IO.File]::WriteAllBytes((Join-Path $limitRoot ('ignored-'+$i+'.txt')),[byte[]]@())}
$limited=$false
try{$null=[RackClickSetupServiceDiagnosticNative]::NativeEnumeratePrivateDirectory($limitRoot,$sid)}catch{if((Get-SetupServiceDiagnosticFailure $_).code-cne'service_directory_limit'){throw};$limited=$true}
if(-not$limited){throw 'Native directory entry bound absent'}
$checks.Add('Native enumeration rejects over 2048 entries without partial output')
foreach($badId in @('606B8C29-41DE-4DC0-B63D-ADE836000D9E','../../secret',($ids[5]+"`n"))) {
    if((Get-SetupServicePrivateDiagnostic $badId $sid).failure.code-cne'service_instance_id_invalid'){throw 'Public instance GUID validation escaped'}
}
$checks.Add('Public entry rejects noncanonical GUIDs, traversal and newline before privilege activation')
if((Get-SetupServicePrivateDiagnostic $ids[5] 'S-1-5-21-100-200-300-500').failure.code-cne'service_sid_invalid'){throw 'Built-in administrator service SID accepted'}
$checks.Add('Public entry rejects built-in administrator service SID')
if((Get-SetupServicePrivateDiagnostic $ids[5] $sid).failure.code-cne'setup_elevated_x64_required'){throw 'Public entry allowed non-elevated private collection'}
$checks.Add('Public production entry refuses non-elevated identity before enabling backup privilege')
$simulationText=@(& (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $PSCommandPath -Simulation)
if($LASTEXITCODE-ne0){throw 'Isolated privilege simulation failed'}
$simulationValue=($simulationText-join"`n")|ConvertFrom-Json
if(-not$simulationValue.valid-or-not$simulationValue.simulated-or$simulationValue.passed-ne3){throw 'Simulation did not return explicit result'}
$checks.Add('Isolated fake privilege API restores prior backup state on success/failure and sanitizes restore failure; no restore privilege requested')
$result=[ordered]@{schemaVersion=1;valid=$true;passed=$checks.Count;checks=$checks;environment='Windows PowerShell 5.1 x64 standard identity; own SID/SYSTEM fixtures only';fixture=$fixture;accountsCreated=0;servicesChanged=0;realPrivilegesEnabled=0;simulatedPrivilegeChecks=3;limits=@('No elevated SeBackupPrivilege read of another identity tested','No target VM, SCM, SQL, restart or root cause claim','Own private fixture and initial test failures are retained')}
if($OutputPath){[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath),($result|ConvertTo-Json -Depth 6),$utf8)}
$result|ConvertTo-Json -Depth 6 -Compress
