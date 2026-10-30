#requires -Version 5.1
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\..\windows\server-install\RackClick.Setup.Security.ps1')
Initialize-SetupSecurityNative
if(Test-SetupAdministrator){throw 'test_requires_non_elevated_session'}
$cases=@(
    {New-SetupManagementDirectory 'C:\Users'},
    {Set-SetupServiceTreeSecurity 'C:\' 'S-1-5-18'},
    {Grant-SetupServiceLogonRights 'S-1-5-18'},
    {Read-SetupServiceCredential 'C:\Users'},
    {New-SetupInstanceParent 'C:\Users' 'S-1-5-18' -AllowCreate},
    {Set-SetupPublicCodeDirectoryACL 'C:\Users' 'S-1-5-18'},
    {Read-SetupPreparedFile 'C:\Users' 'runtime/server-profile.json' 'S-1-5-18'}
)
$passed=0
foreach($case in $cases){
    $failed=$false
    try{& $case}catch{if($_.Exception.Message -ne 'setup_elevated_x64_required'){throw};$failed=$true}
    if(-not $failed){throw 'expected_admin_rejection_missing'};$passed++
}
foreach($path in @('C:\','C:\Users','C:\ProgramData\Other\Instances\00000000-0000-0000-0000-000000000000\instance','C:\ProgramData\RackClick\Instances\00000000-0000-0000-0000-000000000000\..\instance')){
    $failed=$false;try{Assert-SetupPath $path 'instance'}catch{$failed=$true}
    if(-not $failed){throw 'expected_path_rejection_missing'};$passed++
}
Assert-SetupMutablePaths -DirectoryPaths @('deployment\instance\pgdata','deployment\instance\logs','runtime\control','runtime\logs','runtime\temp','runtime\backups') -FilePaths @('deployment\instance\instance.lock')
foreach($path in @('instance\pgdata','logs','temp','backups','runtime\..\logs','C:\Windows','deployment\instance\private')){
    $failed=$false;try{Assert-SetupMutablePaths -DirectoryPaths @($path)}catch{if($_.Exception.Message-ne 'setup_mutable_path_not_allowed'){throw};$failed=$true}
    if(-not $failed){throw 'expected_mutable_rejection_missing'};$passed++
}
foreach($path in @('runtime/server-profile.json','runtime/RootCA.cer','deployment/instance/private/admin-login.json','runtime/control/latest-backup.json')){Assert-SetupPreparedRelativePath $path}
foreach($path in @('runtime/../private/admin-login.json','runtime/server.pfx','deployment/instance/private/owner-password.txt','C:\Windows','runtime\RootCA.cer')){
    $failed=$false;try{Assert-SetupPreparedRelativePath $path}catch{if($_.Exception.Message-ne 'setup_prepared_path_not_allowed'){throw};$failed=$true}
    if(-not $failed){throw 'expected_prepared_path_rejection_missing'};$passed++
}
@{valid=$true;nativeCompiled=$true;nonElevatedNegativeChecks=$passed;mutableLayoutAccepted=$true;preparedPathsAccepted=4;privilegedOperationsExecuted=0;limits='No elevated ACL, LSA, DPAPI or SCM execution. Not installation acceptance.'}|ConvertTo-Json -Compress
