#requires -Version 5.1
param([string]$RepositoryRoot=(Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent))
$ErrorActionPreference='Stop'
$checks=0
function Check([bool]$Condition,[string]$Name){if(-not$Condition){throw ('FAIL '+$Name)};$script:checks++;Write-Output ('PASS '+$Name)}
function Rejected([scriptblock]$Action,[string]$Code){try{&$Action;throw 'expected_rejection'}catch{if($_.Exception.Message-cne$Code){throw}}}
function Import-FocalFunctions([string]$Path,[string[]]$Names){
    $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($Path,[ref]$tokens,[ref]$errors)
    if($errors.Count){throw 'parse_failed'}
    foreach($name in $Names){$definition=$ast.Find({param($node)$node-is[Management.Automation.Language.FunctionDefinitionAst]-and$node.Name-ceq$name},$true);if($null-eq$definition){throw 'function_missing'};Invoke-Expression ($definition.Extent.Text.Replace(('function '+$name),('function script:'+ $name)))}
}
$install=Join-Path $RepositoryRoot 'tools\windows\server-install'
. (Join-Path $install 'RackClick.SetupMfa.ps1')
Import-FocalFunctions (Join-Path $RepositoryRoot 'tools\windows\New-RackClickRecoveredInstance.ps1') @('Stop-RecoveryCheck','Get-RecoverySchemaTransition','Assert-RecoveryMfaMaterial')
. (Join-Path $install 'RackClick.Setup.Lifecycle.ps1')
$id='12345678-1234-4234-8234-123456789abc';$sid='S-1-5-21-123-456-789-1012'
$profile=@{schemaVersion=2;installationPath=('C:\ProgramData\RackClick\Instances\'+$id+'\instance');mfa=@{enabled=$true;instancesRoot=('C:\ProgramData\RackClick\Instances\'+$id+'\security');installationId=$id}}
$request=Get-SetupMfaInitializationRequest $profile $id $sid
Check ((($request.Keys|Sort-Object)-join',')-ceq'installationId,instancesRoot,readerSid'-and$request.readerSid-ceq$sid-and$request.installationId-ceq$id) 'request_closed_and_bound'
Rejected {Get-SetupMfaInitializationRequest $profile ([guid]::NewGuid().ToString('D')) $sid} 'server_mfa_profile_invalid';Check $true 'cross_installation_rejected'
Rejected {Get-SetupMfaInitializationRequest $profile $id 'S-1-5-18'} 'setup_mfa_reader_invalid';Check $true 'system_reader_rejected'
Rejected {Get-SetupMfaInitializationRequest @{schemaVersion=1} $id $sid} 'setup_mfa_profile_required';Check $true 'legacy_profile_cannot_provision'
Assert-SetupMfaInitializationReceipt 0 "{`"status`":`"created`",`"residue`":`"none`"}`r`n" '';Check $true 'exact_success_receipt'
foreach($row in @(@(1,'{"status":"created","residue":"none"}',''),@(0,'{"status":"created","residue":"declared"}',''),@(0,'{"status":"created","residue":"none","valid":true}',''),@(0,'{"status":"created","residue":"none"}','warning'))){Rejected {Assert-SetupMfaInitializationReceipt $row[0] $row[1] $row[2]} 'setup_mfa_initialization_failed_preserved'};Check $true 'exit_residue_extra_and_stderr_rejected'
$start=New-Object Diagnostics.ProcessStartInfo
foreach($name in @('DOTNET_STARTUP_HOOKS','CORECLR_ENABLE_PROFILING','COR_PROFILER_PATH','COMPlus_EnableEventPipe','MfaKeyStore:Enabled','ConnectionStrings__RackClick','PGPASSWORD','ASPNETCORE_URLS')){$start.EnvironmentVariables[$name]='canary'}
Set-SetupMfaChildEnvironment $start 'C:\synthetic\dotnet'
$unsafe=@($start.EnvironmentVariables.Keys|Where-Object{$start.EnvironmentVariables[$_]-ceq'canary'})
Check ($unsafe.Count-eq0-and$start.EnvironmentVariables['DOTNET_EnableDiagnostics']-ceq'0'-and$start.EnvironmentVariables['DOTNET_ROOT']-ceq'C:\synthetic\dotnet') 'child_environment_isolated'
Check ((Get-RecoverySchemaTransition 15 ((1..13)-join','))-ceq'migrate'-and(Get-RecoverySchemaTransition 15 ((1..14)-join','))-ceq'migrate'-and(Get-RecoverySchemaTransition 15 ((1..15)-join','))-ceq'current') 'restore_13_14_15_matrix'
Rejected {Get-RecoverySchemaTransition 15 ((1..12)-join',')} 'restored_schema_required_15';Rejected {Get-RecoverySchemaTransition 15 '1,2,999'} 'restored_schema_required_15';Check $true 'unsupported_and_noncontiguous_schema_rejected'
Assert-RecoveryMfaMaterial 15 '0';Rejected {Assert-RecoveryMfaMaterial 15 '1'} 'recovery_mfa_envelope_required';Rejected {Assert-RecoveryMfaMaterial 15 '3'} 'recovery_mfa_envelope_required';Rejected {Assert-RecoveryMfaMaterial 15 'unknown'} 'recovery_mfa_envelope_required';Check $true 'all_restored_factors_require_envelope'
$snapshot=@{bootCurrent='2026-10-29T08:00:00Z';bootAtInstall='2026-10-28T08:00:00Z';serviceState='Running';serviceStartMode='Auto';serviceSid=$sid;expectedSid=$sid;healthStatus='ready';schemaVersion=14;backupTaskState='Ready';backupTaskSid=$sid;backupLastResult=0;backupScheduleVerified=$true}
Check ((Test-SetupPostbootSnapshot $snapshot).valid) 'historical14_postboot_preserved'
$snapshot.expectedSchemaVersion=15;$snapshot.schemaVersion=15
Check ((Test-SetupPostbootSnapshot $snapshot).valid) 'candidate15_postboot_accepts15'
$snapshot.schemaVersion=14;Check (-not(Test-SetupPostbootSnapshot $snapshot).valid) 'candidate15_rejects14_health'
$snapshot.expectedSchemaVersion=999;Check (-not(Test-SetupPostbootSnapshot $snapshot).valid) 'unknown_postboot_schema_rejected'
$source=[IO.File]::ReadAllText((Join-Path $install 'Install-RackClickServer.ps1'))
Check ($source.IndexOf('Set-SetupServiceTreeSecurity -Path')-lt$source.IndexOf('Set-SetupMfaContentAdministrativeRead -InstancePath')-and$source.IndexOf('Set-SetupMfaContentAdministrativeRead -InstancePath')-lt$source.IndexOf('$setupMfaResult=Initialize-SetupMfaStore')-and$source.IndexOf('$setupMfaResult=Initialize-SetupMfaStore')-lt$source.IndexOf('Start-Service -Name')) 'seal_verify_init_before_service_start'
$modified=@('Install-RackClickServer.ps1','Prepare-RackClickServer.ps1','RackClick.SetupMfa.ps1','RackClick.Setup.Lifecycle.ps1','Test-RackClickServerAfterReboot.ps1','Invoke-RackClickServerRuntime.ps1','Set-RackClickServerNetwork.ps1','Set-RackClickInstanceNetwork.ps1')
foreach($file in $modified){$tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $install $file),[ref]$tokens,[ref]$errors);if($errors.Count){throw ('parse_failed '+$file)}}
Check $true 'all_modified_server_install_scripts_parse51'
Write-Output ('FOCI_OK '+$checks)
