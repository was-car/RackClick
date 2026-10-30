#requires -Version 5.1
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot '..\..\windows\server-install\RackClick.Setup.Lifecycle.ps1')
$checks=0
function Assert-LifecycleAccountCheck([bool]$Condition,[string]$Code) {
    if(-not$Condition){throw $Code};$script:checks++
}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
try {
    $currentSid=$identity.User.Value;$currentName=$identity.Name
    Assert-LifecycleAccountCheck ($currentName.StartsWith([Environment]::MachineName+'\',[StringComparison]::OrdinalIgnoreCase)) 'fixture_requires_current_local_identity'
    $localAlias='.\'+$currentName.Substring($currentName.LastIndexOf('\')+1)
    Assert-LifecycleAccountCheck ((Resolve-SetupAccountSid $currentSid)-ceq$currentSid) 'current_sid_failed'
    Assert-LifecycleAccountCheck ((Resolve-SetupAccountSid $currentName)-ceq$currentSid) 'current_qualified_name_failed'
    Assert-LifecycleAccountCheck ((Resolve-SetupAccountSid $localAlias)-ceq$currentSid) 'current_local_alias_failed'
    $otherSid='S-1-5-21-111-222-333-1001'
    if($otherSid-ceq$currentSid){$otherSid='S-1-5-21-111-222-333-1002'}
    Assert-LifecycleAccountCheck ((Resolve-SetupAccountSid $localAlias)-cne$otherSid) 'caller_exact_sid_mismatch_failed'
    Assert-LifecycleAccountCheck ((Resolve-SetupAccountSid $otherSid)-ceq$otherSid) 'synthetic_sid_changed'
}finally{$identity.Dispose()}
Assert-LifecycleAccountCheck ((Resolve-SetupAccountSid 'S-1-5-18')-ceq'S-1-5-18') 'system_sid_failed'
$systemSid=New-Object Security.Principal.SecurityIdentifier('S-1-5-18')
$systemAccount=$systemSid.Translate([Security.Principal.NTAccount]).Value
Assert-LifecycleAccountCheck ((Resolve-SetupAccountSid $systemAccount)-ceq'S-1-5-18') 'system_qualified_name_failed'
$missingAlias='.\rc_missing_'+[guid]::NewGuid().ToString('N').Substring(0,8)
foreach($badAccount in @('','S-1-5-PRIVATE_SECRET_SENTINEL','.\PRIVATE_SECRET_SENTINEL/invalid',$missingAlias)) {
    $rejected=$false
    try{$null=Resolve-SetupAccountSid $badAccount}catch{
        Assert-LifecycleAccountCheck ($_.Exception.Message-ceq'setup_account_sid_unresolved') 'failure_code_not_sanitized'
        Assert-LifecycleAccountCheck ($null-eq$_.Exception.InnerException) 'failure_retained_inner_exception'
        $failureText=$_.Exception.ToString()+($_.Exception.Data|ConvertTo-Json -Compress)
        Assert-LifecycleAccountCheck ($failureText-notlike'*PRIVATE_SECRET_SENTINEL*'-and-not$failureText.Contains($missingAlias.Substring(2))) 'failure_exposed_account_name'
        $rejected=$true
    }
    Assert-LifecycleAccountCheck $rejected 'invalid_account_accepted'
}
# Observe translator input without resolving a foreign domain, UPN or invented account.
& {
    function New-Object([string]$TypeName,[object[]]$ArgumentList) {
        if($TypeName-cne'Security.Principal.NTAccount'-or$ArgumentList.Count-ne1){throw 'unexpected_mock_constructor'}
        $script:translatorInput=[string]$ArgumentList[0]
        $account=[pscustomobject]@{}
        $account|Add-Member -MemberType ScriptMethod -Name Translate -Value {
            param([type]$Target)
            if($Target-ne[Security.Principal.SecurityIdentifier]){throw 'unexpected_translation_target'}
            return [pscustomobject]@{Value='S-1-5-21-111-222-333-1001'}
        }
        return $account
    }
    foreach($explicitAccount in @('EXAMPLE\PRIVATE_SECRET_SENTINEL','PRIVATE_SECRET_SENTINEL@example.invalid','./PRIVATE_SECRET_SENTINEL','PRIVATE_SECRET_SENTINEL')) {
        $script:translatorInput=''
        $resolved=Resolve-SetupAccountSid $explicitAccount
        Assert-LifecycleAccountCheck ($script:translatorInput-ceq$explicitAccount) 'explicit_account_rewritten'
        Assert-LifecycleAccountCheck ($resolved-ceq'S-1-5-21-111-222-333-1001') 'explicit_translation_result_changed'
    }
    $script:translatorInput=''
    $resolved=Resolve-SetupAccountSid '.\PRIVATE_SECRET_SENTINEL'
    Assert-LifecycleAccountCheck ($script:translatorInput-ceq([Environment]::MachineName+'\PRIVATE_SECRET_SENTINEL')) 'local_prefix_not_machine_qualified'
    Assert-LifecycleAccountCheck ($resolved-ceq'S-1-5-21-111-222-333-1001') 'local_translation_result_changed'
}
[ordered]@{valid=$true;checks=$checks;powershellVersion=$PSVersionTable.PSVersion.ToString();realCurrentSidNameAlias=$true;realSystemSidAccount=$true;foreignDomainAndUpnInputChecks='mocked translator only';realServiceQueries=0;authenticationAttempts=0;accountsChanged=0;servicesChanged=0;databasesChanged=0;limits='Current identity must be local. Real read-only SID/NTAccount translation only; no foreign-domain resolution, task registration, SCM, credentials, SQL, runtime or installed-root operation.'}|ConvertTo-Json -Compress
