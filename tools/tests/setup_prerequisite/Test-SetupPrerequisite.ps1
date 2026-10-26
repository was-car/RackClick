#requires -Version 5.1
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\..\windows\server-install\RackClick.Setup.Prerequisite.ps1')
$checks=0
$ready=Get-SetupCrtPolicy $true 1 'v14.51.36247.00' '14.51.36247.0' '14.51.36247.0'
if(-not $ready.valid -or $ready.exitCode-ne 0){throw 'compatible_pair_rejected'};$checks++
foreach($fixture in @(
 @($true,1,'v14.51.36247.00','14.40.33816.0','14.51.36247.0'),
 @($true,1,'v14.51.36247.00','14.51.36247.0','14.40.33816.0'),
 @($true,0,'v14.51.36247.00','14.51.36247.0','14.51.36247.0'),
 @($false,1,'v14.51.36247.00','14.51.36247.0','14.51.36247.0'),
 @($true,1,'v14.51.36247.00','','14.51.36247.0'),
 @($true,1,'v14.51.36247.00','not-version','14.51.36247.0')
)){
 $policy=Get-SetupCrtPolicy $fixture[0] $fixture[1] $fixture[2] $fixture[3] $fixture[4]
 if($policy.valid -or $policy.exitCode-eq 0){throw 'incompatible_fixture_accepted'};$checks++
}
$sha='843068991daaa1f73ad9f6239bce4d0f6a07a51f18c37ea2a867e9beca71295c'
Assert-SetupCrtInstallerMetadata $sha '14.51.36247.0' 'Valid' 'CN=Microsoft Corporation, O=Microsoft Corporation, C=US';$checks++
foreach($fixture in @(
 @('bad','14.51.36247.0','Valid','O=Microsoft Corporation','crt_installer_hash_mismatch'),
 @($sha,'14.40.33816.0','Valid','O=Microsoft Corporation','crt_installer_version_mismatch'),
 @($sha,'14.51.36247.0','UnknownError','O=Microsoft Corporation','crt_installer_signature_invalid'),
 @($sha,'14.51.36247.0','Valid','O=Other Corporation','crt_installer_signature_invalid')
)){
 $failed=$false;try{Assert-SetupCrtInstallerMetadata $fixture[0] $fixture[1] $fixture[2] $fixture[3]}catch{if($_.Exception.Message-ne $fixture[4]){throw};$failed=$true}
 if(-not $failed){throw 'installer_fixture_accepted'};$checks++
}
$native=Test-SetupCrt
$principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
 $blocked=Install-SetupCrt -PayloadRoot 'C:\missing' -ReportDirectory 'C:\missing'
 if($blocked.code-ne 'crt_elevated_x64_required' -or $blocked.valid){throw 'missing_admin_gate'};$checks++
}
@{valid=$true;policyChecks=$checks;nativeReadOnlyInspection=$native;crtInstallationsExecuted=0;limits='No elevated installation, extraction, Authenticode of payload, reboot or repair exercised.'}|ConvertTo-Json -Depth 4 -Compress
