#requires -Version 5.1
# Pure helpers for a bounded, credentialed read check of an existing installation.
function Get-SetupProbeCodeSddl([string]$ServiceSid) {
    $sid=New-Object Security.Principal.SecurityIdentifier($ServiceSid)
    if($sid.Value-cne$ServiceSid-or$ServiceSid-cnotmatch'^S-1-5-21-(\d+-){3}\d+$'-or$ServiceSid.EndsWith('-500')){throw 'probe_service_sid_invalid'}
    return 'O:BAG:SYD:P(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)(A;OICI;FRFX;;;'+$ServiceSid+')'
}
function New-SetupProbeFileLaunch([string]$ScriptPath,$Binding,[string]$Executable) {
    if($Binding.sha-cnotmatch'^[a-f0-9]{64}$'){throw 'probe_launch_binding_invalid'}
    $null=Get-SetupProbeCodeSddl $Binding.serviceSid
    $values=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(ConvertTo-SetupArgument $ScriptPath),'-ProbeCodeRoot',(ConvertTo-SetupArgument $Binding.codeRoot),'-ProbeManifest',(ConvertTo-SetupArgument $Binding.manifest),'-ProbeSha',$Binding.sha,'-ProbeSid',$Binding.serviceSid)
    $arguments=$values-join' '
    # CreateProcessWithLogonW has a 1024-character limit, unlike CreateProcessW.
    $characters=((ConvertTo-SetupArgument $Executable)+' '+$arguments).Length+1
    if($characters-gt1024){throw 'probe_command_too_long'}
    return @{arguments=$arguments;commandLineCharactersIncludingNull=$characters;limit=1024}
}
function Select-SetupProbeFailureLocation($ErrorRecord) {
    $safe=[ordered]@{}
    $type=$ErrorRecord.Exception.GetType().FullName
    if($type-cin@('System.InvalidOperationException','System.UnauthorizedAccessException','System.IO.IOException','System.Management.Automation.RuntimeException','System.Management.Automation.ParameterBindingException','System.Management.Automation.PSArgumentException','System.Management.Automation.MethodInvocationException','System.Management.Automation.CommandNotFoundException')){$safe.errorType=$type}
    $invocation=$ErrorRecord.InvocationInfo
    if($null-ne$invocation){
        if([IO.Path]::GetFileName($invocation.ScriptName)-ceq'Test-RackClickExistingAccount.ps1'){$safe.failureFile='Test-RackClickExistingAccount.ps1';$safe.failureLine=[int]$invocation.ScriptLineNumber}
        if($null-ne$invocation.MyCommand-and$invocation.MyCommand.Name-cin@('Start-Process','Initialize-SetupChildProcessNative','Open-SetupChildProcess','Wait-SetupChildProcess','Read-SetupChildResult','ConvertTo-SetupProbeSummary','New-SetupProbeFileLaunch')){$safe.failureCommand=$invocation.MyCommand.Name}
    }
    return $safe
}
function Select-SetupProbeAccountFailure($ErrorRecord) {
    $safe=[ordered]@{};$data=$ErrorRecord.Exception.Data
    if($data.Contains('accountNameForm')-and$data['accountNameForm']-cin@('sid','local_dot','qualified','upn','plain','empty')){$safe.accountNameForm=[string]$data['accountNameForm']}
    if($data.Contains('accountErrorType')-and$data['accountErrorType']-cin@('System.Security.Principal.IdentityNotMappedException','System.ArgumentException','System.Security.SecurityException','unresolved')){$safe.errorType=[string]$data['accountErrorType']}
    if($data.Contains('accountErrorHResult')-and($data['accountErrorHResult']-is[int]-or$data['accountErrorHResult']-is[long])-and$data['accountErrorHResult']-ge[int]::MinValue-and$data['accountErrorHResult']-le[int]::MaxValue){$safe.errorHResult=$data['accountErrorHResult']}
    return $safe
}
function Assert-SetupProbeCodeAcl([string]$Path) {
    Assert-SetupNoReparse $Path
    $acl=Get-Acl -LiteralPath $Path -ErrorAction Stop
    if($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value-cnotin@('S-1-5-18','S-1-5-32-544')){throw 'probe_code_owner_invalid'}
    $writes=[Security.AccessControl.FileSystemRights]'Write,Delete,DeleteSubdirectoriesAndFiles,ChangePermissions,TakeOwnership'
    $rules=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
    if($rules.Count-eq0){throw 'probe_code_acl_invalid'}
    foreach($rule in $rules){if($rule.AccessControlType-eq'Allow'-and($rule.FileSystemRights-band$writes)-ne0-and$rule.IdentityReference.Value-cnotin@('S-1-5-18','S-1-5-32-544')){throw 'probe_code_acl_invalid'}}
}
function Read-SetupProbeReceipt([string]$AttemptId) {
    $id=[guid]::Empty
    if(-not[guid]::TryParseExact($AttemptId,'D',[ref]$id)-or$AttemptId-cne$id.ToString('D')){throw 'probe_attempt_invalid'}
    $management='C:\ProgramData\RackClick\Instances\'+$AttemptId+'\management'
    Assert-SetupPath $management 'management';Assert-SetupManagementAcl $management
    $path=Join-Path $management 'server-installation.json';Assert-SetupNoReparse $path;Assert-SetupManagementAcl $path
    $stream=[IO.File]::Open($path,'Open','Read','Read')
    try {
        if($stream.Length-gt65536){throw 'probe_receipt_invalid'}
        $reader=New-Object IO.StreamReader($stream,(New-Object Text.UTF8Encoding($false,$true)),$true,4096,$true)
        try{$receipt=$reader.ReadToEnd()|ConvertFrom-Json -ErrorAction Stop}finally{$reader.Dispose()}
        $codeRoot='C:\Program Files\RackClick\'+$AttemptId;$instance='C:\ProgramData\RackClick\Instances\'+$AttemptId+'\instance'
        if($receipt.schemaVersion-ne1-or$receipt.installationId-cne$AttemptId-or$receipt.managementPath-cne$management-or$receipt.codeRoot-cne$codeRoot-or$receipt.instancePath-cne$instance-or$receipt.serviceSid-cnotmatch'^S-1-5-21-(\d+-){3}\d+$'-or$receipt.serviceSid.EndsWith('-500')-or$receipt.serviceName-cnotmatch'^RackClick(?:-Recovery-[a-f0-9]{8,32})?$'-or$receipt.manifestSha256-cnotmatch'^[a-f0-9]{64}$'){throw 'probe_receipt_binding_invalid'}
        return @{id=$AttemptId;management=$management;codeRoot=$codeRoot;instance=$instance;serviceSid=$receipt.serviceSid;serviceName=$receipt.serviceName;sha=$receipt.manifestSha256;manifest=(Join-Path $instance 'runtime\server-profile.json')}
    }finally{$stream.Dispose()}
}
function Open-SetupProbeCodeLocks([string]$CodeRoot,$Pins) {
    Assert-SetupProbeCodeAcl $CodeRoot
    $locks=New-Object Collections.ArrayList;$seen=New-Object 'Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
    try {
        foreach($pin in $Pins){
            if($pin.path-cnotmatch'^operators/(?:server-install/)?[A-Za-z0-9_.-]+\.ps1$'-or$pin.sha256-cnotmatch'^[a-f0-9]{64}$'-or-not$seen.Add($pin.path)){throw 'probe_pin_invalid'}
            $path=Join-Path $CodeRoot $pin.path.Replace('/','\');Assert-SetupProbeCodeAcl $path
            $cursor=[IO.Path]::GetDirectoryName($path)
            while($cursor.Length-gt$CodeRoot.Length){Assert-SetupProbeCodeAcl $cursor;$cursor=[IO.Path]::GetDirectoryName($cursor)}
            $stream=[IO.File]::Open($path,'Open','Read','Read');$null=$locks.Add($stream)
            $sha=[Security.Cryptography.SHA256]::Create()
            try{$hash=([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
            if($hash-cne$pin.sha256){throw 'probe_installed_code_mismatch'}
        }
        if(-not$seen.Contains('operators/server-install/RackClick.ServerRuntime.ps1')-or-not$seen.Contains('operators/RackClick.LaunchControl.ps1')-or-not$seen.Contains('operators/RackClick.Process.ps1')){throw 'probe_pins_incomplete'}
        return ,$locks
    }catch{foreach($stream in $locks){$stream.Dispose()};throw}
}
function ConvertTo-SetupProbeSummary($Value,[uint32]$NativeExit,$Contract) {
    $allowedStages=@('identity','import','profile','launch_control','schema','instance_acl','process_compiler','complete')
    if($Value-isnot[pscustomobject]-or$Value.schemaVersion-ne1-or$Value.valid-isnot[bool]-or$Value.exitCode-notin@(0,2)-or$Value.exitCode-ne$NativeExit-or$Value.stage-cnotin$allowedStages-or$Value.environment-cne'credentialed_logon_with_user_profile_not_SCM'-or$Value.startsRuntime-ne$false-or$Value.databasesChanged-ne0-or$Value.servicesChanged-ne0){throw 'probe_child_result_invalid'}
    $code=if($Value.code-cin$Contract.codes){[string]$Value.code}else{'probe_unlisted_failure'}
    if($Value.valid-and($code-cne'probe_read_checks_passed'-or$Value.stage-cne'complete'-or$NativeExit-ne0)){throw 'probe_child_result_invalid'}
    if(-not$Value.valid-and($NativeExit-ne2-or$code-ceq'probe_read_checks_passed')){throw 'probe_child_result_invalid'}
    $safe=[ordered]@{valid=$Value.valid;exitCode=$NativeExit;code=$code;stage=$Value.stage;environment='credentialed_logon_with_user_profile_not_SCM';startsRuntime=$false;databasesChanged=0;servicesChanged=0}
    foreach($name in @('errorHResult','nativeErrorCode','failureLine','schemaVersionObserved')){
        $prop=$Value.PSObject.Properties[$name]
        if($null-ne$prop-and($prop.Value-is[int]-or$prop.Value-is[long])-and$prop.Value-ge[int]::MinValue-and$prop.Value-le[uint32]::MaxValue){$safe[$name]=$prop.Value}
    }
    $prop=$Value.PSObject.Properties['errorType']
    if($null-ne$prop-and$prop.Value-cin$Contract.errorTypes){$safe.errorType=[string]$prop.Value}
    $prop=$Value.PSObject.Properties['failureFile']
    if($null-ne$prop-and$prop.Value-cin$Contract.files){$safe.failureFile=[string]$prop.Value}
    return $safe
}
function New-SetupProbeEncodedCommand([string]$Body,$Binding) {
    # Same-user fixtures only. Credentialed production uses New-SetupProbeFileLaunch.
    $arguments=@($Binding.codeRoot,$Binding.manifest,$Binding.sha,$Binding.serviceSid)|ForEach-Object {"'"+([string]$_).Replace("'","''")+"'"}
    $command="& {`r`n"+$Body+"`r`n} "+($arguments-join' ')
    $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
    if($encoded.Length-gt29000){throw 'probe_command_too_long'}
    return $encoded
}
