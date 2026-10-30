#requires -Version 5.1
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\..\windows\server-install\RackClick.Setup.Diagnostics.ps1')
$utf8=New-Object Text.UTF8Encoding($false,$true)
$checks=0
function Observe($Value){return ConvertTo-SetupJsonObservation $utf8.GetBytes(($Value|ConvertTo-Json -Depth 8 -Compress))}
$sample=@{valid=$false;exitCode=1;code='crt_postcheck_failed';nativeExitCode=0;rebootRequired=$false;inspection=@{valid=$false;is64Bit=$true;registryInstalled=1;registryVersion='v14.51.36247.00';vcruntimeVersion='14.40.33816.0';msvcpVersion='14.51.36247.0';minimumVersion='14.44.35211.0';password='PRIVATE_SENTINEL';message='PRIVATE_SENTINEL';path='PRIVATE_SENTINEL'}}
$out=Observe $sample
if($out.status-cne'parsed'-or$out.fields.code-cne'crt_postcheck_failed'-or$out.fields.nativeExitCode-ne0-or$out.fields.crtInspection.Count-ne7-or$out.fields.crtInspection.vcruntimeVersion-cne'14.40.33816.0'-or$out.fields.crtInspection.valid-ne$false){throw 'crt_inspection_lost'};$checks++
if(($out|ConvertTo-Json -Depth 8)-like'*PRIVATE_SENTINEL*'){throw 'crt_secret_exported'};$checks++
foreach($invalid in @('PRIVATE_SENTINEL',@(@{valid=$true}),17)){
    $sample.inspection=$invalid;$out=Observe $sample
    if($out.fields.Contains('crtInspection')){throw 'nonobject_inspection_exported'};$checks++
}
$sample.inspection=@{valid='true';is64Bit=1;registryInstalled='1';registryVersion='PRIVATE_SENTINEL';vcruntimeVersion='C:\PRIVATE_SENTINEL';msvcpVersion=('1'*10000);minimumVersion='14.44.35211.0';extra='PRIVATE_SENTINEL'}
$out=Observe $sample
if($out.fields.crtInspection.Count-ne1-or$out.fields.crtInspection.minimumVersion-cne'14.44.35211.0'){throw 'unsafe_type_or_version_exported'};$checks++
$sample.inspection=@{valid=$false;is64Bit=$true;registryInstalled=0;registryVersion='';vcruntimeVersion='';msvcpVersion='';minimumVersion='14.44.35211.0'}
$out=Observe $sample
if($out.fields.crtInspection.Count-ne7-or$out.fields.crtInspection.registryInstalled-ne0-or$out.fields.crtInspection.vcruntimeVersion-cne''){throw 'missing_components_not_preserved'};$checks++
$sample.code='setup_stage_failed_preserved';$out=Observe $sample
if($out.fields.Contains('crtInspection')){throw 'unrelated_inspection_exported'};$checks++
Set-StrictMode -Version Latest
foreach($partial in @(@{percent=6},@{code='crt_postcheck_failed'})){
    $out=Observe $partial
    if($out.status-cne'parsed'-or$out.fields.Contains('crtInspection')){throw 'partial_diagnostic_rejected_in_strict_mode'};$checks++
}
Set-StrictMode -Off
@{valid=$true;checks=$checks;fixtureOnly=$true;crtInstallationsExecuted=0;limits='Tests sanitization only; no elevated install, repair or reboot.'}|ConvertTo-Json -Compress
