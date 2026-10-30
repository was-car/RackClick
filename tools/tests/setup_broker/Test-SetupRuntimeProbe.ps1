#requires -Version 5.1
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$operators=Join-Path $repo 'tools\windows\server-install'
. (Join-Path $operators 'RackClick.Setup.ps1')
. (Join-Path $operators 'RackClick.Setup.RuntimeProbe.ps1')
. (Join-Path $operators 'RackClick.Setup.Process.ps1')
. (Join-Path $repo 'tools\windows\RackClick.Process.ps1')
$checks=0
$errorFixture=New-Object InvalidOperationException('PRIVATE_SECRET_SENTINEL')
$errorFixture.Data['accountNameForm']='local_dot';$errorFixture.Data['accountErrorType']='System.Security.Principal.IdentityNotMappedException';$errorFixture.Data['accountErrorHResult']=-2146233032
$safe=Select-SetupProbeAccountFailure ([pscustomobject]@{Exception=$errorFixture})
if($safe.Count-ne3-or$safe.accountNameForm-cne'local_dot'-or$safe.errorType-cne'System.Security.Principal.IdentityNotMappedException'-or($safe|ConvertTo-Json)-like'*PRIVATE_SECRET_SENTINEL*'){throw 'account_failure_summary_failed'};$checks++
$errorFixture.Data['accountNameForm']='PRIVATE_SECRET_SENTINEL';$errorFixture.Data['accountErrorType']='System.PRIVATE_SECRET_SENTINEL';$errorFixture.Data['accountErrorHResult']='PRIVATE_SECRET_SENTINEL'
if((Select-SetupProbeAccountFailure ([pscustomobject]@{Exception=$errorFixture})).Count-ne0){throw 'account_failure_free_fields_exported'};$checks++
$errorFixture.Data.Clear()
if((Select-SetupProbeAccountFailure ([pscustomobject]@{Exception=$errorFixture})).Count-ne0){throw 'empty_account_failure_changed'};$checks++
$contract=[pscustomobject]@{codes=@('probe_read_checks_passed','probe_check_failed','server_manifest_hash_mismatch');files=@('RackClick.ServerRuntime.ps1');errorTypes=@('System.InvalidOperationException')}
function New-TestProbeResult {
    return [pscustomobject]@{schemaVersion=1;valid=$false;exitCode=2;code='server_manifest_hash_mismatch';stage='profile';environment='credentialed_logon_with_user_profile_not_SCM';startsRuntime=$false;databasesChanged=0;servicesChanged=0;errorType='System.InvalidOperationException';errorHResult=-2146233079;failureFile='RackClick.ServerRuntime.ps1';failureLine=65;password='PRIVATE_SECRET_SENTINEL';message='PRIVATE_SECRET_SENTINEL'}
}
$safe=ConvertTo-SetupProbeSummary (New-TestProbeResult) 2 $contract
if($safe.code-cne'server_manifest_hash_mismatch'-or$safe.failureFile-cne'RackClick.ServerRuntime.ps1'-or($safe|ConvertTo-Json)-like'*PRIVATE_SECRET_SENTINEL*'){throw 'summary_failed'};$checks++
$bad=New-TestProbeResult;$bad.code='a'*64;$bad.errorType='System.PRIVATE_SECRET_SENTINEL';$bad.failureFile='PRIVATE_SECRET_SENTINEL.ps1'
$safe=ConvertTo-SetupProbeSummary $bad 2 $contract
if($safe.code-cne'probe_unlisted_failure'-or$safe.Contains('errorType')-or$safe.Contains('failureFile')-or($safe|ConvertTo-Json)-like'*PRIVATE_SECRET_SENTINEL*'){throw 'unknown_values_exported'};$checks++
foreach($change in @(@('exitCode',0),@('valid',$true),@('stage','unknown'),@('environment','SCM'),@('startsRuntime',$true),@('databasesChanged',1),@('servicesChanged',1))){
    $bad=New-TestProbeResult;$bad.($change[0])=$change[1];$rejected=$false
    try{$null=ConvertTo-SetupProbeSummary $bad 2 $contract}catch{if($_.Exception.Message-cne'probe_child_result_invalid'){throw};$rejected=$true}
    if(-not$rejected){throw 'invalid_result_accepted'};$checks++
}
$good=New-TestProbeResult;$good.valid=$true;$good.exitCode=0;$good.stage='complete';$good.code='probe_read_checks_passed'
if(-not(ConvertTo-SetupProbeSummary $good 0 $contract).valid){throw 'success_result_rejected'};$checks++
$beforeFunctions=@(Get-Command New-Service,Set-Service,Start-Service,Stop-Service -ErrorAction SilentlyContinue)
foreach($badId in @('','../other','606B8C29-41DE-4DC0-B63D-ADE836000D9E')){
    $rejected=$false;try{$null=Read-SetupProbeReceipt $badId}catch{if($_.Exception.Message-cne'probe_attempt_invalid'){throw};$rejected=$true}
    if(-not$rejected){throw 'invalid_id_accepted'};$checks++
}
# Actual WinPS child, actual production Read-ServerProfile, actual private file ACL.
# No PostgreSQL, service, account, or existing application data is used.
$fixture=New-RackClickProcessPrivateDirectory (Join-Path $repo ('.local\runtime-probe-native-'+[guid]::NewGuid().ToString('N')))
$code=Join-Path $fixture 'code with spaces';$null=[IO.Directory]::CreateDirectory((Join-Path $code 'operators\server-install'))
foreach($source in @(Get-ChildItem -LiteralPath (Join-Path $repo 'tools\windows') -File -Filter '*.ps1')){[IO.File]::Copy($source.FullName,(Join-Path $code ('operators\'+$source.Name)))}
[IO.File]::Copy((Join-Path $operators 'RackClick.ServerRuntime.ps1'),(Join-Path $code 'operators\server-install\RackClick.ServerRuntime.ps1'))
$manifest=Join-Path $fixture 'server-profile.json';[IO.File]::WriteAllText($manifest,'{}',(New-Object Text.UTF8Encoding($false)))
$binding=@{codeRoot=$code;manifest=$manifest;sha=('0'*64);serviceSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value}
$body=[IO.File]::ReadAllText((Join-Path $operators 'Probe-RackClickRuntimeRead.ps1'))
$probeExe="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$fileScript=Join-Path $fixture 'probe-file.ps1'
# Same secure FileStream overload as production, but fixture-only owner/current
# access substituted for the unavailable elevated Administrators token.
$fileAcl=New-Object Security.AccessControl.FileSecurity
$fileAcl.SetOwner([Security.Principal.WindowsIdentity]::GetCurrent().User)
$fileAcl.SetAccessRuleProtection($true,$false)
$fileAcl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule([Security.Principal.WindowsIdentity]::GetCurrent().User,'FullControl','Allow')))
$writer=[IO.FileStream]::new($fileScript,[IO.FileMode]::CreateNew,[Security.AccessControl.FileSystemRights]::Write,[IO.FileShare]::None,4096,[IO.FileOptions]::None,$fileAcl)
try{$bytes=[Text.Encoding]::UTF8.GetBytes($body);$writer.Write($bytes,0,$bytes.Length);$writer.Flush($true)}finally{$writer.Dispose()}
$duplicateRejected=$false;try{$writer=[IO.FileStream]::new($fileScript,[IO.FileMode]::CreateNew,[Security.AccessControl.FileSystemRights]::Write,[IO.FileShare]::None,4096,[IO.FileOptions]::None,$fileAcl);$writer.Dispose()}catch [IO.IOException]{$duplicateRejected=$true}
if(-not$duplicateRejected){throw 'staged_script_overwritten'};$checks++
$short=New-SetupProbeFileLaunch $fileScript $binding $probeExe
if($short.commandLineCharactersIncludingNull-gt1024-or$short.arguments-like'*-EncodedCommand*'){throw 'file_launch_not_short'};$checks++
$longRejected=$false;try{$null=New-SetupProbeFileLaunch ('C:\'+('a'*1024)+'.ps1') $binding $probeExe}catch{if($_.Exception.Message-cne'probe_command_too_long'){throw};$longRejected=$true}
if(-not$longRejected){throw 'over_logon_limit_accepted'};$checks++
$policy=New-Object Security.AccessControl.DirectorySecurity
$policy.SetSecurityDescriptorSddlForm((Get-SetupProbeCodeSddl $binding.serviceSid))
$rules=@($policy.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
$serviceRule=@($rules|Where-Object {$_.IdentityReference.Value-ceq$binding.serviceSid})
$writeMask=[Security.AccessControl.FileSystemRights]'Write,Delete,DeleteSubdirectoriesAndFiles,ChangePermissions,TakeOwnership'
if($policy.GetOwner([Security.Principal.SecurityIdentifier]).Value-cne'S-1-5-32-544'-or$rules.Count-ne3-or$serviceRule.Count-ne1-or($serviceRule[0].FileSystemRights-band$writeMask)-ne0){throw 'staged_code_policy_not_read_only'};$checks++
$sidRejected=$false;try{$null=Get-SetupProbeCodeSddl 'S-1-5-21-1-2-3-500'}catch{$sidRejected=$true}
if(-not$sidRejected){throw 'administrator_sid_policy_accepted'};$checks++
Initialize-SetupChildProcessNative
$fileOut=Join-Path $fixture 'file.stdout.log';$fileErr=Join-Path $fixture 'file.stderr.log'
$fileProcess=Start-Process -FilePath $probeExe -ArgumentList $short.arguments -WorkingDirectory $fixture -RedirectStandardOutput $fileOut -RedirectStandardError $fileErr -WindowStyle Hidden -PassThru
$fileHandle=Open-SetupChildProcess $fileProcess.Id
try{if(-not(Wait-SetupChildProcess $fileHandle 30)){throw 'file_child_timeout'};$fileProcess.WaitForExit();$fileExit=Get-SetupChildProcessExitCode $fileHandle}finally{$fileHandle.Dispose();$fileProcess.Dispose()}
$fileValue=[IO.File]::ReadAllText($fileOut)|ConvertFrom-Json
if($fileExit-ne2-or$fileValue.code-cne'server_manifest_hash_mismatch'-or$fileValue.stage-cne'profile'){throw 'file_child_actual_profile_error_missing'};$checks++
$fakeError=[pscustomobject]@{Exception=(New-Object InvalidOperationException('PRIVATE_SECRET_SENTINEL'));InvocationInfo=[pscustomobject]@{ScriptName='C:\PRIVATE_SECRET_SENTINEL.ps1';ScriptLineNumber=17;MyCommand=[pscustomobject]@{Name='PRIVATE_SECRET_SENTINEL'}}}
$location=Select-SetupProbeFailureLocation $fakeError
if(($location|ConvertTo-Json)-like'*PRIVATE_SECRET_SENTINEL*'-or$location.Count-ne1){throw 'failure_location_leaks'};$checks++
$fakeError.InvocationInfo.ScriptName='C:\Test-RackClickExistingAccount.ps1';$fakeError.InvocationInfo.MyCommand.Name='Start-Process'
$location=Select-SetupProbeFailureLocation $fakeError
if($location.failureLine-ne17-or$location.failureCommand-cne'Start-Process'){throw 'failure_location_not_recorded'};$checks++
$encoded=New-SetupProbeEncodedCommand $body $binding
if(((ConvertTo-SetupArgument $probeExe)+' -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand '+$encoded).Length-le1024){throw 'baseline_encoded_limit_not_reproduced'};$checks++
$stdout=Join-Path $fixture 'stdout.log';$stderr=Join-Path $fixture 'stderr.log'
Initialize-SetupChildProcessNative
$proc=Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-EncodedCommand',$encoded) -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
$handle=Open-SetupChildProcess $proc.Id
try{if(-not(Wait-SetupChildProcess $handle 30)){throw 'native_fixture_timeout'};$proc.WaitForExit();$native=Get-SetupChildProcessExitCode $handle}finally{$handle.Dispose();$proc.Dispose()}
if($native-ne2){throw ('native_expected_failure_exit_'+$native)};$checks++
$value=[IO.File]::ReadAllText($stdout)|ConvertFrom-Json -ErrorAction Stop
if($value.code-cne'server_manifest_hash_mismatch'-or$value.stage-cne'profile'-or$value.failureFile-cne'RackClick.ServerRuntime.ps1'-or$value.valid-ne$false){throw 'actual_profile_error_not_captured'};$checks++
$safe=ConvertTo-SetupProbeSummary $value $native $contract
if($safe.code-cne'server_manifest_hash_mismatch'-or[IO.File]::ReadAllText($stderr).Trim()-ne''){throw 'actual_profile_summary_failed'};$checks++
# Real early import failure is also reported; no missing output or fake success.
$binding.codeRoot=Join-Path $fixture 'absent-code'
$encoded=New-SetupProbeEncodedCommand $body $binding
$output=& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand $encoded
$native=$LASTEXITCODE;$value=($output-join[Environment]::NewLine)|ConvertFrom-Json
if($native-ne2-or$value.stage-cne'import'-or$value.code-cne'probe_check_failed'-or$value.valid-ne$false){throw 'early_import_failure_not_captured'};$checks++
# Positive path: replace only profile/schema readers in an isolated module fixture;
# the launch-control and process compilers and ACL checks remain real Windows code.
$fixtureModule=Join-Path $code 'operators\server-install\RackClick.ServerRuntime.ps1'
$originalModule=Join-Path $operators 'RackClick.ServerRuntime.ps1'
$stub=". '"+$originalModule.Replace("'","''")+"'`r`nfunction Read-ServerProfile { return @{ root='"+$fixture.Replace("'","''")+"'; instance=@{root='"+$fixture.Replace("'","''")+"';stageRoot='fixture';lockPath='"+(Join-Path $fixture 'absent.lock').Replace("'","''")+"'}} }`r`nfunction Get-StageSchema { return 13 }`r`nfunction Close-ServerProfile {}`r`n"
[IO.File]::WriteAllText($fixtureModule,$stub,(New-Object Text.UTF8Encoding($false)))
$null=[IO.Directory]::CreateDirectory((Join-Path $fixture 'temp'))
$binding.codeRoot=$code
$encoded=New-SetupProbeEncodedCommand $body $binding
$output=& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand $encoded
$native=$LASTEXITCODE;$value=($output-join[Environment]::NewLine)|ConvertFrom-Json
if($native-ne0-or$value.stage-cne'complete'-or$value.code-cne'probe_read_checks_passed'-or$value.schemaVersionObserved-ne13){throw 'native_compilers_positive_failed'};$checks++
if(-not(ConvertTo-SetupProbeSummary $value 0 $contract).valid){throw 'native_success_summary_failed'};$checks++
# Hash/lock tests use an isolated tree and mock only the administrator-owned ACL
# precondition; the file hashing, held handles and failure cleanup are native.
& {
    function Assert-SetupProbeCodeAcl([string]$Path) { Assert-SetupNoReparse $Path }
    $pins=@()
    foreach($name in @('operators/server-install/RackClick.ServerRuntime.ps1','operators/RackClick.LaunchControl.ps1','operators/RackClick.Process.ps1')){
        $file=Join-Path $code $name.Replace('/','\')
        $pins+=@([pscustomobject]@{path=$name;sha256=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()})
    }
    $held=Open-SetupProbeCodeLocks $code $pins
    try{
        $locked=$false;try{$writer=[IO.File]::Open((Join-Path $code 'operators\RackClick.Process.ps1'),'Open','Write','Read');$writer.Dispose()}catch [IO.IOException]{$locked=$true}
        if(-not$locked){throw 'code_lock_not_held'};$script:checks++
    }finally{foreach($stream in $held){$stream.Dispose()}}
    $pins[0].sha256='0'*64;$rejected=$false
    try{$null=Open-SetupProbeCodeLocks $code $pins}catch{if($_.Exception.Message-cne'probe_installed_code_mismatch'){throw};$rejected=$true}
    if(-not$rejected){throw 'corrupt_installed_code_accepted'};$script:checks++
    $writer=[IO.File]::Open((Join-Path $code 'operators\server-install\RackClick.ServerRuntime.ps1'),'Open','Write','Read');$writer.Dispose();$script:checks++
    $pins[0].path='operators/../other.ps1';$rejected=$false
    try{$null=Open-SetupProbeCodeLocks $code $pins}catch{if($_.Exception.Message-cne'probe_pin_invalid'){throw};$rejected=$true}
    if(-not$rejected){throw 'traversal_pin_accepted'};$script:checks++
}
$binding.codeRoot="C:\fixture' ; throw 'PRIVATE_SECRET_SENTINEL"
$encoded=New-SetupProbeEncodedCommand 'param($r,$m,$h,$s) $ProgressPreference="SilentlyContinue";[pscustomobject]@{root=$r}|ConvertTo-Json -Compress' $binding
$output=& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand $encoded
if($LASTEXITCODE-ne0-or(($output-join'')|ConvertFrom-Json).root-cne$binding.codeRoot){throw 'encoded_argument_injection'};$checks++
@{valid=$true;checks=$checks;nativeProfileReadChecks=3;realCredentialedProcesses=0;realServicesQueried=0;databasesChanged=0;servicesChanged=0;fixture=$fixture;limits='Native child runs under current account only, including File launch with quoted spaces; staged ACL owner is substituted in fixture. No elevated creation, credentialed API or SCM/VM reproduction.'}|ConvertTo-Json -Compress
