#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ManifestPath,[Parameter(Mandatory=$true)][string]$ExpectedManifestSha256,[Parameter(Mandatory=$true)][string]$StoppedRunId)
$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$entry=Join-Path $root 'tools\windows\server-install\Invoke-RackClickServerRuntime.ps1'
$hostPath=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
function Invoke-Check {
 param([string]$Name,[string]$Operation,[string]$Hash,[string]$Run,[string]$ExpectedCode,[int]$ExpectedExit)
 $arguments=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$entry,'-Operation',$Operation,'-ManifestPath',$ManifestPath,'-ExpectedManifestSha256',$Hash)
 if ($Run.Length -gt 0) {$arguments+=@('-RunId',$Run)}
 $lines=@(& $hostPath @arguments)
 $exitCode=$LASTEXITCODE
 $record=($lines -join [Environment]::NewLine)|ConvertFrom-Json
 if ($exitCode -ne $ExpectedExit -or $record.exitCode -ne $ExpectedExit -or $record.code -cne $ExpectedCode -or $record.valid -ne ($ExpectedExit -eq 0)) {throw ('Test failed: '+$Name)}
 return @{name=$Name;passed=$true;exitCode=$exitCode;code=$record.code}
}
$results=@()
$results+=Invoke-Check 'Verify pinned profile' 'Verify' $ExpectedManifestSha256 '' 'server_profile_verified' 0
$badHash=if ($ExpectedManifestSha256 -ceq ('0'*64)) {'1'*64} else {'0'*64}
$results+=Invoke-Check 'Reject wrong retained hash' 'Verify' $badHash '' 'server_manifest_hash_mismatch' 2
$results+=Invoke-Check 'Reject another run UUID' 'Stop' $ExpectedManifestSha256 ([guid]::NewGuid().ToString('D')) 'server_active_run_changed' 2
$results+=Invoke-Check 'Repeat stop of exact stopped run' 'Stop' $ExpectedManifestSha256 $StoppedRunId 'server_stopped' 0
@{valid=$true;exitCode=0;tests=$results;scope='PS5.1 native pinned-profile and exact-run guards; lifecycle is tested separately against isolated PostgreSQL'}|ConvertTo-Json -Depth 5
