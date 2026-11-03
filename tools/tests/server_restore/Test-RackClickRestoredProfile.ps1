#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$InstallationPath,[Parameter(Mandatory=$true)][string]$ExpectedInstallationSha256,[Parameter(Mandatory=$true)][string]$BindAddress,[Parameter(Mandatory=$true)][int]$HttpsPort,[string]$OutputPath='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
if (-not $InstallationPath.StartsWith((Join-Path $repo '.local\labs\server-restore-tests-'),[StringComparison]::OrdinalIgnoreCase)) {throw 'Only the isolated native Restore fixture is allowed'}
$hostPath=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$runtime=Join-Path $repo 'tools\windows\server-install'
$origin='https://'+$BindAddress+':'+$HttpsPort
$lines=@(& $hostPath '-NoProfile' '-NonInteractive' '-ExecutionPolicy' 'Bypass' '-File' (Join-Path $runtime 'New-RackClickServerProfile.ps1') '-InstallationPath' $InstallationPath '-ExpectedInstallationSha256' $ExpectedInstallationSha256 '-DestinationPath' (Join-Path $InstallationPath 'runtime') '-PublicOrigin' $origin '-BindAddress' $BindAddress)
$profileExit=$LASTEXITCODE;$profile=($lines -join [Environment]::NewLine)|ConvertFrom-Json
if ($profileExit -ne 0 -or $profile.exitCode -ne 0 -or -not $profile.valid -or $profile.code -cne 'server_profile_prepared') {throw 'Restored production profile creation failed'}
if ($profile.rootCertificatePath -cne (Join-Path $InstallationPath 'runtime\RootCA.cer') -or -not [IO.File]::Exists($profile.rootCertificatePath) -or $profile.publicOrigin -cne $origin -or $profile.mutableDirectoryPaths.Count -ne 6 -or $profile.mutableFilePaths.Count -ne 1) {throw 'Profile fields returned to broker are inconsistent'}
foreach ($path in $profile.mutableDirectoryPaths) {if (-not [IO.Directory]::Exists($path) -or -not $path.StartsWith($InstallationPath+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Profile mutable directory missing or outside fixture'}}
$lines=@(& $hostPath '-NoProfile' '-NonInteractive' '-ExecutionPolicy' 'Bypass' '-File' (Join-Path $runtime 'Invoke-RackClickServerRuntime.ps1') '-Operation' 'Verify' '-ManifestPath' $profile.manifestPath '-ExpectedManifestSha256' $profile.manifestSha256)
$verifyExit=$LASTEXITCODE;$verified=($lines -join [Environment]::NewLine)|ConvertFrom-Json
if ($verifyExit -ne 0 -or $verified.exitCode -ne 0 -or -not $verified.valid -or $verified.code -cne 'server_profile_verified') {throw 'Restored production profile verification failed'}
$result=[ordered]@{schemaVersion=1;valid=$true;passed=3;checks=@('Production profile from schema2 restored installation','Public CA and six mutable directories returned consistently','Pinned runtime Verify with certificate/manifest/SID guards');installationPath=$InstallationPath;profileSha256=$profile.manifestSha256;publicOrigin=$origin;environment='Windows PowerShell 5.1 standard development user';noGlobalChanges=$true;scmExecuted=$false;httpsServerStarted=$false}
if ($OutputPath) {$stream=[IO.File]::Open($OutputPath,'CreateNew','Write','None');try {$bytes=[Text.Encoding]::UTF8.GetBytes(($result|ConvertTo-Json -Depth 4 -Compress));$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally {$stream.Dispose()}}
$result|ConvertTo-Json -Depth 4 -Compress
