#requires -Version 5.1
<# Pure native Windows contract tests. Real production functions are loaded by AST;
   owned process calls are simulated. No installer, PostgreSQL, UI, VM or service. #>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ResultPath)
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/Modules'
$root=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$checks=New-Object Collections.Generic.List[string]
function Import-TestFunctions([string]$Path){
    $errors=$null;$tokens=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile($Path,[ref]$tokens,[ref]$errors)
    if($errors.Count-ne0){throw 'source_parse_failed'}
    foreach($statement in $ast.EndBlock.Statements){
        if($statement-is[Management.Automation.Language.FunctionDefinitionAst]){
            $definition=$statement.Extent.Text -replace '^function\s+', 'function script:'
            . ([scriptblock]::Create($definition))
        }
    }
}
Import-TestFunctions (Join-Path $root 'tools/windows/New-RackClickRecoveredInstance.ps1')
Import-TestFunctions (Join-Path $root 'tools/windows/server-install/Prepare-RackClickServer.ps1')
Import-TestFunctions (Join-Path $root 'tools/windows/server-install/Show-RackClickInstaller.ps1')
$script:stopped=0;$script:disposed=0
function Start-RackClickOwnedProcess {
    $process=[pscustomobject]@{}
    Add-Member -InputObject $process -MemberType ScriptMethod -Name Dispose -Value {$script:disposed++}
    return @{Process=$process}
}
function Wait-RackClickOwnedProcess {return $script:childResult}
function Stop-RackClickOwnedProcess {$script:stopped++}
function Assert-Equal($Actual,$Expected,[string]$Name){
    if($Actual-cne$Expected){throw ('assertion_failed_'+$Name)}
    $checks.Add($Name)
}
function Get-ChildFailure([hashtable]$Result,[string]$Label='recover-admin'){
    $script:childResult=$Result
    try{
        $null=Invoke-RecoveryOwnedChild 'fixture' @() 'fixture' @{} 'fixture' $Label
        return 'returned'
    }catch{
        if($_.Exception.Data.Contains('recoveryCode')){return [string]$_.Exception.Data['recoveryCode']}
        throw
    }
}
$known='{"status":"rejected","error":"recovery_username_exists"}'
Assert-Equal (Get-ChildFailure @{exitCode=1;stdout=$known+"`r`n";stderr=''}) 'recovery_username_exists' 'known_rejection_preserved'
Assert-Equal $script:stopped 1 'owned_child_stopped'
Assert-Equal $script:disposed 1 'owned_handle_disposed'
foreach($case in @(
    @{name='unknown_error';text='{"status":"rejected","error":"private_diagnostic_sentinel"}'},
    @{name='case_changed';text='{"status":"rejected","error":"RECOVERY_USERNAME_EXISTS"}'},
    @{name='extra_property';text='{"status":"rejected","error":"recovery_username_exists","detail":"private_diagnostic_sentinel"}'},
    @{name='duplicate_property';text='{"status":"rejected","error":"private_diagnostic_sentinel","error":"recovery_username_exists"}'},
    @{name='nested_object';text='{"result":{"status":"rejected","error":"recovery_username_exists"}}'},
    @{name='invalid_json';text=$known+'private_diagnostic_sentinel'},
    @{name='failed_status';text='{"status":"failed","error":"recovery_username_exists"}'},
    @{name='oversized_output';text=('x'*17000)+$known}
)){
    Assert-Equal (Get-ChildFailure @{exitCode=1;stdout=$case.text;stderr=''}) 'recover_admin_failed' $case.name
}
Assert-Equal (Get-ChildFailure @{exitCode=2;stdout=$known;stderr=''}) 'recover_admin_failed' 'wrong_native_exit'
Assert-Equal (Get-ChildFailure @{exitCode=1;stdout=$known;stderr='private_diagnostic_sentinel'}) 'recover_admin_failed' 'stderr_not_promoted'
Assert-Equal (Get-ChildFailure @{exitCode=1;stdout=$known;stderr=''} 'migrate') 'migrate_failed' 'other_command_not_promoted'
$result=@{exitCode=0;stdout=$known;stderr=''}
Assert-Equal (Get-ChildFailure $result) 'returned' 'zero_exit_retains_existing_flow'
$rejected=$false;try{$null=Read-RecoveryCommitResult $result '11111111-1111-4111-8111-111111111111'}catch{$rejected=$_.Exception.Data['recoveryCode']-ceq'recovery_output_invalid'}
Assert-Equal $rejected $true 'zero_exit_rejection_not_committed'

function Get-PreparationFailure([string]$Text,[int]$Exit=1,[string]$Err='', [string]$Label='installation'){
    try{$null=Read-PreparationChildResult $Text $Err $Exit $Label 'installation_prepared';return 'returned'}catch{return $_.Exception.Message}
}
$report='{"valid":false,"exitCode":1,"code":"deployment_instance_administrator_recovery_username_exists"}'
Assert-Equal (Get-PreparationFailure $report) 'preparation_recovery_username_exists' 'preparation_exact_failure'
Assert-Equal (Get-PreparationFailure $report 2) 'preparation_child_failed' 'preparation_exit_disagreement'
Assert-Equal (Get-PreparationFailure $report 1 'private_diagnostic_sentinel') 'preparation_child_output_invalid' 'preparation_stderr_rejected'
Assert-Equal (Get-PreparationFailure $report 1 '' 'unrelated') 'preparation_child_failed' 'preparation_wrong_label'
Assert-Equal (Get-PreparationFailure $report.Replace('false','true')) 'preparation_child_failed' 'preparation_valid_flag_not_failure'
Assert-Equal (Get-PreparationFailure $report.Replace('recovery_username_exists','unknown_error')) 'preparation_child_failed' 'preparation_unknown_code'
Assert-Equal (Get-PreparationFailure $report.Replace('false','"false"')) 'preparation_child_failed' 'preparation_boolean_type'
Assert-Equal (Get-PreparationFailure $report.Replace('"deployment_instance_administrator_recovery_username_exists"','["deployment_instance_administrator_recovery_username_exists"]')) 'preparation_child_failed' 'preparation_failure_code_array'
Assert-Equal (Get-PreparationFailure '{"valid":true,"exitCode":0,"code":["installation_prepared"]}' 0) 'preparation_child_failed' 'preparation_success_code_array'
Assert-Equal (Get-PreparationFailure '{invalid') 'preparation_child_json_invalid' 'preparation_invalid_json'
Assert-Equal (Get-PreparationFailure '{"valid":true,"exitCode":0,"code":"installation_prepared"}' 0) 'returned' 'preparation_success_unchanged'

$ui=[pscustomobject]@{code='setup_child_failed_preserved';stage='prepare';childCode='preparation_recovery_username_exists';failureLine=0}
$message=Format-SetupUiFailure $ui 'fixture-report'
Assert-Equal ($message.Contains('nombre nuevo')-and$message.Contains('administrador')-and-not$message.Contains('private_diagnostic_sentinel')) $true 'gui_actionable_fixed_message'
foreach($change in @(@{property='stage';value='account'},@{property='code';value='unrelated_failure'},@{property='childCode';value='private_diagnostic_sentinel'})){
    $copy=[pscustomobject]@{code=$ui.code;stage=$ui.stage;childCode=$ui.childCode;failureLine=0};$copy.($change.property)=$change.value
    $text=Format-SetupUiFailure $copy 'fixture-report'
    Assert-Equal ($text.Contains('nombre nuevo')-or$text.Contains('private_diagnostic_sentinel')) $false ('gui_no_promotion_'+$change.property)
}
foreach($field in @('code','stage','childCode')){
    $copy=[pscustomobject]@{code=$ui.code;stage=$ui.stage;childCode=$ui.childCode;failureLine=0}
    $copy.$field=@($copy.$field)
    Assert-Equal ((Format-SetupUiFailure $copy 'fixture-report').Contains('nombre nuevo')) $false ('gui_no_array_'+$field)
}
$answer=[ordered]@{result='PASS';checks=$checks.Count;names=@($checks);scope='AST-loaded production helpers; child processes simulated; no SQL/UI/installer/VM';processesLaunched=0}
$bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($answer|ConvertTo-Json -Depth 4))
$stream=[IO.File]::Open($ResultPath,'CreateNew','Write','None')
try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
$answer|ConvertTo-Json -Depth 4 -Compress
