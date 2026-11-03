#requires -Version 5.1
param([string]$WorkPath)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$project=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$work=[IO.Path]::GetFullPath($WorkPath)
if([IO.Path]::GetDirectoryName($work)-cne(Join-Path $project '.local\sql-request-labs')){throw 'only_new_temporary_fixture_allowed'}
. (Join-Path $project 'tools/windows/RackClick.Instance.ps1')
$null=New-BackupPrivateDirectory $work
$file=Join-Path $work 'temporary-secret.txt';$script:called=0;$checks=0
function Assert-Focus($Condition){if(-not$Condition){throw 'temporary_secret_focus_failed'};$script:checks++}
Invoke-InstanceWithTemporarySecret $file 'synthetic-only' {
    Assert-Focus ([IO.File]::ReadAllText($file)-ceq'synthetic-only')
    Assert-BackupPrivateAcl $file
    $script:called++
}
Assert-Focus (-not[IO.File]::Exists($file)-and$script:called-eq1)
$failed=$false
try{Invoke-InstanceWithTemporarySecret $file 'synthetic-only' {throw 'fixture_child_failed'}}catch{if($_.Exception.Message-cne'fixture_child_failed'){throw};$failed=$true}
Assert-Focus ($failed-and-not[IO.File]::Exists($file))
[IO.File]::WriteAllText($file,'preexisting-synthetic')
$failed=$false
try{Invoke-InstanceWithTemporarySecret $file 'must-not-write' {$script:called++}}catch [IO.IOException]{$failed=$true}
Assert-Focus ($failed-and[IO.File]::ReadAllText($file)-ceq'preexisting-synthetic'-and$script:called-eq1)
@{valid=$true;code='temporary_secret_focus_pass';checks=$checks;serviceOrVmUsed=$false;preexistingPreserved=$true}|ConvertTo-Json -Compress
