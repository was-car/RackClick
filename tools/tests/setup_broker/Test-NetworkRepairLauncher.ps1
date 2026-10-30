#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot '..\..\windows\server-install\Start-RackClickNetworkRepair.ps1') -FunctionsOnly
$checks=New-Object 'Collections.Generic.List[string]'
function Assert-Launch([bool]$Value,[string]$Name){if(-not$Value){throw ('Test failed: '+$Name)};$checks.Add($Name)}
$original=(Get-Item function:Invoke-RcRepairBundleStage).ScriptBlock
$script:stages=New-Object 'Collections.Generic.List[string]'
$script:mode=''
function Invoke-RcRepairBundleStage([string]$Script,[string[]]$Arguments){
 $isRepair=$Script.EndsWith('Repair-RackClickNetworkTransaction.ps1');$script:stages.Add($(if($isRepair){'repair'}else{'network'}))
 if($isRepair){
  if($script:mode-eq'repair_failure'){return @{exitCode=2;report=@{schemaVersion=1;valid=$false;success=$false;exitCode=2;code='network_repair_preflight_failed'}}}
  return @{exitCode=0;report=@{schemaVersion=1;valid=$true;exitCode=0;code=$(if($script:mode-eq'already_repaired'){'network_repair_already_restored'}else{'network_repair_verified'})}}
 }
 if($script:mode-eq'network_failure'){return @{exitCode=2;report=@{schemaVersion=1;valid=$false;success=$false;exitCode=2;code='network_change_failed'}}}
 if($script:mode-eq'already_configured'){return @{exitCode=0;report=@{schemaVersion=1;valid=$true;success=$false;exitCode=0;code='network_already_configured'}}}
 return @{exitCode=0;report=@{schemaVersion=1;valid=$true;success=$true;exitCode=0;code='network_change_verified'}}
}
try{
 foreach($mode in @('success','repair_failure','network_failure','already_repaired','already_configured')){
  $script:mode=$mode;$script:stages.Clear();$r=Invoke-RcRepairBundleSequence 'C:\generated-fixture-only' ('a'*64)
  Assert-Launch (-not$r.productAdopted) ('No adoption for '+$mode)
  if($mode-eq'repair_failure'){Assert-Launch (($script:stages-join',')-ceq'repair'-and-not$r.success-and$r.code-ceq'network_bundle_repair_failed') 'Repair failure prevents any network mutation'}
  else{Assert-Launch (($script:stages-join',')-ceq'repair,network') ('Network change follows verified recovery for '+$mode)}
  if($mode-in@('success','already_repaired')){Assert-Launch ($r.success-and$r.valid-and$r.exitCode-eq0-and$r.code-ceq'network_bundle_verified') ('Success requires verified network change for '+$mode)}
  else{Assert-Launch (-not$r.success-and$r.exitCode-ne0) ('No phantom success for '+$mode)}
 }
}finally{Set-Item function:Invoke-RcRepairBundleStage $original}
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('RackClick-launcher-transport-'+[guid]::NewGuid().ToString('N'));$null=[IO.Directory]::CreateDirectory($fixture)
$child=Join-Path $fixture 'inert-child.ps1';$utf8=New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText($child,'param([string]$Probe) @{schemaVersion=1;valid=$true;exitCode=0;probe=$Probe}|ConvertTo-Json -Compress;exit 0',$utf8)
$transport=Invoke-RcRepairBundleStage $child @('-Probe','fixture with spaces')
Assert-Launch ($transport.exitCode-eq0-and$transport.report.probe-ceq'fixture with spaces') 'Actual inert child preserves argument boundaries and parses one JSON result'
$transport=Invoke-RcRepairBundleStage $child @('-Probe','fixture "quote" and trailing\')
Assert-Launch ($transport.exitCode-eq0-and$transport.report.probe-ceq'fixture "quote" and trailing\') 'Actual inert child preserves embedded quotes and trailing backslashes'
foreach($case in @(
 @{name='mismatched exit';body='@{schemaVersion=1;valid=$true;exitCode=0}|ConvertTo-Json -Compress;exit 2'},
 @{name='missing exit field';body='@{schemaVersion=1;valid=$true}|ConvertTo-Json -Compress;exit 0'},
 @{name='non-JSON output';body='Write-Output "not a JSON report";exit 0'},
 @{name='stderr even with valid JSON and exit0';body='[Console]::Error.WriteLine("fixture stderr must not be forwarded");@{schemaVersion=1;valid=$true;exitCode=0}|ConvertTo-Json -Compress;exit 0'}
)){
 [IO.File]::WriteAllText($child,$case.body,$utf8);$rejected=$false;try{$null=Invoke-RcRepairBundleStage $child @()}catch{$rejected=$true}
 Assert-Launch $rejected ('Reject actual child with '+$case.name)
}
$result=[ordered]@{schemaVersion=1;valid=$true;passed=$checks.Count;checks=@($checks);environment='Windows PowerShell 5.1; launcher sequence callbacks and six actual inert child processes';childProcessesExecuted=6;privilegedOperationsExecuted=0;serviceOperationsExecuted=0;databaseOperationsExecuted=0;credentialsRead=0}
if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 6 -Compress
