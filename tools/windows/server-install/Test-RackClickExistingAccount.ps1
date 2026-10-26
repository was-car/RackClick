#requires -Version 5.1
[CmdletBinding()]
param([string]$AttemptId='606b8c29-41de-4dc0-b63d-ade836000d9e',[switch]$Quiet)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'RackClick.Setup.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.Security.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.Process.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.ServiceStatus.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.RuntimeProbe.ps1')
if(-not(Test-SetupAdministrator)){
    if($Quiet){@{valid=$false;exitCode=2;code='probe_administrator_required'}|ConvertTo-Json -Compress;exit 2}
    try{
        $id=[guid]::Empty;if(-not[guid]::TryParseExact($AttemptId,'D',[ref]$id)-or$AttemptId-cne$id.ToString('D')){throw 'probe_attempt_invalid'}
        $args=@('-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',(ConvertTo-SetupArgument $PSCommandPath),'-AttemptId',$AttemptId)
        $process=Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList $args -Verb RunAs -Wait -PassThru
        exit $process.ExitCode
    }catch{exit 2}
}
$probeRecord=[ordered]@{schemaVersion=1;probeVersion=8;kind='RackClickExistingAccountReadCheck';attemptId=$AttemptId;generatedUtc=[DateTime]::UtcNow.ToString('o');valid=$false;exitCode=2;code='probe_failed';stage='preflight';repairPerformed=$false;servicesChanged=0;databasesChanged=0;scmEnvironmentReproduced=$false}
$probeCredential=$null;$probeLocks=@();$probeHandle=$null;$probeProcess=$null;$probeDirectory='';$probeScriptLock=$null
try {
    Assert-SetupAdministrator
    $binding=Read-SetupProbeReceipt $AttemptId
    $probeRecord.stage='service_binding'
    $service=@(Get-CimInstance Win32_Service -Filter ("Name='"+$binding.serviceName+"'") -ErrorAction Stop)
    if($service.Count-ne1){throw 'probe_service_missing'}
    $expected=(ConvertTo-SetupArgument ($binding.instance+'\content\dependencies\dotnet\dotnet.exe'))+' '+(ConvertTo-SetupArgument ($binding.codeRoot+'\service\RackClick.WindowsService.dll'))+' --config '+(ConvertTo-SetupArgument ($binding.instance+'\service-config.json'))
    $probeRecord.executableBindingMatches=$service[0].PathName-ceq$expected
    if(-not$probeRecord.executableBindingMatches){throw 'probe_service_binding_changed'}
    $probeRecord.accountNameForm=Get-SetupServiceDiagnosticAccountFormat $service[0].StartName
    $probeRecord.accountSidMatches=(Resolve-SetupServiceDiagnosticAccountSid $service[0].StartName)-ceq$binding.serviceSid
    if(-not$probeRecord.accountSidMatches){throw 'probe_service_binding_changed'}
    if($service[0].State-cne'Stopped'-or$service[0].ProcessId-ne0){throw 'probe_service_must_be_stopped'}
    $probeRecord.stage='code_integrity'
    $contract=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'runtime-probe-contract.json'))|ConvertFrom-Json
    $probeLocks=Open-SetupProbeCodeLocks $binding.codeRoot $contract.pins
    $probeRecord.stage='credential'
    $probeCredential=Read-SetupServiceCredential $binding.management
    if((Resolve-SetupServiceDiagnosticAccountSid $probeCredential.UserName)-cne$binding.serviceSid){throw 'probe_credential_identity_changed'}
    # New, admin-only output directory. No existing ACL or instance file is changed.
    $probeDirectory=Join-Path $binding.management ('boot-probe-'+[guid]::NewGuid().ToString('N'))
    Assert-SetupNoReparse $probeDirectory
    $acl=New-Object Security.AccessControl.DirectorySecurity
    $acl.SetSecurityDescriptorSddlForm('O:BAG:SYD:P(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)')
    $null=[IO.Directory]::CreateDirectory($probeDirectory,$acl)
    $stdout=Join-Path $probeDirectory 'stdout-private.log';$stderr=Join-Path $probeDirectory 'stderr-private.log'
    $probeRecord.stage='child_code_stage'
    # A new sibling of instance/management: the service already has traverse/read
    # on the sealed GUID parent. Existing trees and ACL are never rewritten.
    $probeCodeDirectory=Join-Path ([IO.Path]::GetDirectoryName($binding.management)) ('probe-code-'+[guid]::NewGuid().ToString('N'))
    Assert-SetupNoReparse $probeCodeDirectory
    if(Test-Path -LiteralPath $probeCodeDirectory){throw 'probe_code_destination_exists'}
    $probeCodeAcl=New-Object Security.AccessControl.DirectorySecurity
    $probeCodeAcl.SetSecurityDescriptorSddlForm((Get-SetupProbeCodeSddl $binding.serviceSid))
    $null=[IO.Directory]::CreateDirectory($probeCodeDirectory,$probeCodeAcl)
    $probeScript=Join-Path $probeCodeDirectory 'read-check.ps1'
    $probeBytes=[IO.File]::ReadAllBytes((Join-Path $PSScriptRoot 'Probe-RackClickRuntimeRead.ps1'))
    $probeFileAcl=New-Object Security.AccessControl.FileSecurity
    $probeFileAcl.SetSecurityDescriptorSddlForm((Get-SetupProbeCodeSddl $binding.serviceSid).Replace(';OICI;',';;'))
    $probeWriter=[IO.FileStream]::new($probeScript,[IO.FileMode]::CreateNew,[Security.AccessControl.FileSystemRights]::Write,[IO.FileShare]::None,4096,[IO.FileOptions]::None,$probeFileAcl)
    try{$probeWriter.Write($probeBytes,0,$probeBytes.Length);$probeWriter.Flush($true)}finally{$probeWriter.Dispose()}
    Assert-SetupProbeCodeAcl $probeCodeDirectory;Assert-SetupProbeCodeAcl $probeScript
    $probeScriptLock=[IO.File]::Open($probeScript,'Open','Read','Read')
    $probeExe="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $launch=New-SetupProbeFileLaunch $probeScript $binding $probeExe
    $probeRecord.childLaunch=@{mode='file';commandLineCharactersIncludingNull=$launch.commandLineCharactersIncludingNull;limit=$launch.limit}
    $probeRecord.stage='child_native_init'
    Initialize-SetupChildProcessNative
    $probeRecord.stage='child_start'
    $probeProcess=Start-Process -FilePath $probeExe -Credential $probeCredential -LoadUserProfile -WorkingDirectory $binding.codeRoot -ArgumentList $launch.arguments -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
    $probeRecord.stage='child_handle'
    $probeHandle=Open-SetupChildProcess $probeProcess.Id
    $probeRecord.stage='child_wait'
    if(-not(Wait-SetupChildProcess $probeHandle 90)){throw 'probe_child_timeout_do_not_repeat'}
    $probeProcess.WaitForExit()
    $native=Get-SetupChildProcessExitCode $probeHandle
    $probeRecord.stage='child_result'
    $answer=Read-SetupChildResult $stdout
    $probeRecord.stage='child_summary'
    $probeRecord.check=ConvertTo-SetupProbeSummary $answer $native $contract
    $probeRecord.valid=$probeRecord.check.valid;$probeRecord.exitCode=[int]$native;$probeRecord.code=$probeRecord.check.code;$probeRecord.stage=$probeRecord.check.stage
}catch{
    # Export only a fixed vocabulary, numeric error data and known exception types.
    $probeKnown=@('probe_attempt_invalid','probe_receipt_invalid','probe_receipt_binding_invalid','probe_code_owner_invalid','probe_code_acl_invalid','probe_pin_invalid','probe_installed_code_mismatch','probe_pins_incomplete','probe_service_missing','probe_service_binding_changed','probe_service_must_be_stopped','probe_credential_identity_changed','probe_command_too_long','probe_child_result_invalid','probe_child_timeout_do_not_repeat','probe_service_sid_invalid','probe_code_destination_exists','probe_launch_binding_invalid','setup_child_process_handle_unavailable','setup_child_process_wait_unavailable','setup_child_exit_code_unavailable','setup_child_result_missing','setup_child_result_too_large','setup_child_result_invalid','setup_reparse_not_allowed','setup_management_acl_invalid','setup_credential_invalid','setup_elevated_x64_required','report_service_account_unresolved')
    if($_.Exception.Message-cin$probeKnown){$probeRecord.code=$_.Exception.Message}
    $probeAccountFailure=Select-SetupProbeAccountFailure $_
    if($probeAccountFailure.Count-gt0){$probeRecord.accountResolutionFailure=$probeAccountFailure}
    $probeLocation=Select-SetupProbeFailureLocation $_
    if($probeLocation.Count-gt0){$probeRecord.failureLocation=$probeLocation}
    $probeCause=$_.Exception
    for($index=0;$index-lt8-and$null-ne$probeCause.InnerException;$index++){$probeCause=$probeCause.InnerException}
    $probeRecord.errorHResult=$probeCause.HResult
    if($probeCause-is[ComponentModel.Win32Exception]){$probeRecord.nativeErrorCode=$probeCause.NativeErrorCode}
}finally{
    if($null-ne$probeHandle){$probeHandle.Dispose()};if($null-ne$probeProcess){$probeProcess.Dispose()}
    foreach($stream in $probeLocks){$stream.Dispose()}
    if($null-ne$probeCredential){$probeCredential.Password.Dispose()}
    if($null-ne$probeScriptLock){$probeScriptLock.Dispose()}
}
try {
    Add-Type -AssemblyName System.IO.Compression
    $desktop=[Environment]::GetFolderPath('Desktop');Assert-SetupNoReparse $desktop
    $zipPath=Join-Path $desktop ('RackClick-Informe-Arranque-Cuenta-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)+'.zip')
    $output=[IO.File]::Open($zipPath,'CreateNew','Write','None')
    try{$zip=New-Object IO.Compression.ZipArchive($output,[IO.Compression.ZipArchiveMode]::Create,$true);try{$entry=$zip.CreateEntry('INFORME.json');$stream=$entry.Open();try{$bytes=[Text.Encoding]::UTF8.GetBytes(($probeRecord|ConvertTo-Json -Depth 8));$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}}finally{$zip.Dispose()}}finally{$output.Dispose()}
    if(-not$Quiet){Add-Type -AssemblyName System.Windows.Forms;[Windows.Forms.MessageBox]::Show(('Comprobacion terminada: '+$probeRecord.code+[Environment]::NewLine+'Envia este ZIP del Escritorio: '+$zipPath+[Environment]::NewLine+'La herramienta no ha reparado ni reinstalado RackClick.'),'RackClick','OK','Information')|Out-Null}
    @{valid=$probeRecord.valid;exitCode=$probeRecord.exitCode;code=$probeRecord.code;zipPath=$zipPath}|ConvertTo-Json -Compress
}catch{Write-Output 'No se pudo exportar el informe. Conserva esta ventana y comunica este mensaje.';exit 2}
exit $probeRecord.exitCode
