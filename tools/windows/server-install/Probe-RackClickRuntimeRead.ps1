#requires -Version 5.1
# Executed as an encoded command under the existing service account. No Start/Stop/SQL.
param([string]$ProbeCodeRoot,[string]$ProbeManifest,[string]$ProbeSha,[string]$ProbeSid)
$probeInput=@{root=$ProbeCodeRoot;manifest=$ProbeManifest;sha=$ProbeSha;sid=$ProbeSid}
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';Set-StrictMode -Version Latest
$probeProfile=$null;$probeSavedTemp=$env:TEMP;$probeSavedTmp=$env:TMP;$probeSavedConfig=@{}
$probeResult=[ordered]@{schemaVersion=1;valid=$false;exitCode=2;code='probe_check_failed';stage='identity';environment='credentialed_logon_with_user_profile_not_SCM';startsRuntime=$false;databasesChanged=0;servicesChanged=0}
try {
    if([Security.Principal.WindowsIdentity]::GetCurrent().User.Value-cne$probeInput.sid){throw 'probe_identity_mismatch'}
    $probeResult.stage='import'
    . (Join-Path $probeInput.root 'operators\server-install\RackClick.ServerRuntime.ps1')
    $probeResult.stage='profile'
    $probeProfile=Read-ServerProfile $probeInput.manifest $probeInput.sha
    $probeResult.stage='launch_control'
    $env:TEMP=Join-Path $probeProfile.root 'temp';$env:TMP=$env:TEMP
    . (Join-Path $probeInput.root 'operators\RackClick.LaunchControl.ps1')
    $probeSavedConfig=Clear-LauncherInheritedConfiguration
    $probeResult.stage='schema'
    $probeResult.schemaVersionObserved=Get-StageSchema $probeProfile.instance.stageRoot
    $probeResult.stage='instance_acl'
    Assert-RackClickProcessPrivateAcl $probeProfile.instance.root
    if([IO.File]::Exists($probeProfile.instance.lockPath)){Assert-RackClickProcessPrivateAcl $probeProfile.instance.lockPath}
    $probeResult.stage='process_compiler'
    Initialize-RackClickProcessNative
    $probeResult.stage='complete';$probeResult.valid=$true;$probeResult.exitCode=0;$probeResult.code='probe_read_checks_passed'
} catch {
    # No Message, ErrorDetails, command text, full paths, credentials or environment values.
    $probeError=$_;$probeException=$_.Exception
    foreach($probeKey in @('serverCode','deploymentCode','instanceCode','httpsCode','stageCode','code')){
        if($probeException.Data.Contains($probeKey)){
            $probeCandidate=[string]$probeException.Data[$probeKey]
            # The parent accepts only the finite catalogue built from the frozen sources.
            if($probeCandidate-cmatch'^[a-z][a-z0-9_]{0,95}$'){$probeResult.code=$probeCandidate;break}
        }
    }
    for($probeIndex=0;$probeIndex-lt8-and$null-ne$probeException.InnerException;$probeIndex++){$probeException=$probeException.InnerException}
    $probeResult.errorType=$probeException.GetType().FullName;$probeResult.errorHResult=$probeException.HResult
    if($probeException-is[ComponentModel.Win32Exception]){$probeResult.nativeErrorCode=$probeException.NativeErrorCode}
    $probeFrame=[IO.Path]::GetFileName($probeError.InvocationInfo.ScriptName)
    if($probeFrame-cmatch'^[A-Za-z0-9_.-]+\.ps1$'){$probeResult.failureFile=$probeFrame;$probeResult.failureLine=$probeError.InvocationInfo.ScriptLineNumber}
} finally {
    try{
        if($null-ne$probeProfile){Close-ServerProfile $probeProfile}
        if(Get-Command Restore-LauncherInheritedConfiguration -ErrorAction SilentlyContinue){Restore-LauncherInheritedConfiguration $probeSavedConfig}
        [Environment]::SetEnvironmentVariable('TEMP',$probeSavedTemp,'Process');[Environment]::SetEnvironmentVariable('TMP',$probeSavedTmp,'Process')
    }catch{$probeResult.valid=$false;$probeResult.exitCode=2;$probeResult.code='probe_environment_restore_failed'}
}
$probeResult|ConvertTo-Json -Depth 4 -Compress
exit $probeResult.exitCode
