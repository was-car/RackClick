#requires -Version 5.1
[CmdletBinding()]
param([string]$PlanPath,[string]$ReportDirectory)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'RackClick.Setup.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.Host.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.Security.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.Prerequisite.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.Lifecycle.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.Recovery.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.Process.ps1')
. (Join-Path $PSScriptRoot 'RackClick.SetupMfa.ps1')
$setupExit=1;$setupStage='preflight';$setupWritable=$false;$setupCredential=$null;$setupAccount=$null
$setupResult=[ordered]@{schemaVersion=1;success=$false;valid=$false;exitCode=1;code='setup_failed';stage=$setupStage;installationPercent=0;globalProjectEstimate=$null;rebootVerified=$false;productAdopted=$false}
function Set-SetupProgress([string]$Stage,[int]$Percent,[string]$Message) {
    $script:setupStage=$Stage;$script:setupResult.stage=$Stage;$script:setupResult.installationPercent=$Percent
    Write-SetupJson (Join-Path $ReportDirectory 'progress.json') @{stage=$Stage;percent=$Percent;message=$Message;complete=$false;success=$false}
}
function Invoke-SetupServiceChild([string]$Script,[string[]]$Arguments,[string]$Label,[int]$Timeout=900) {
    Initialize-SetupChildProcessNative
    foreach($key in @('nativeExitCode','childCode','childErrorType','childFailureLine')){if($script:setupResult.Contains($key)){$script:setupResult.Remove($key)}}
    $stdout=Join-Path $ReportDirectory ($Label+'.stdout.log');$stderr=Join-Path $ReportDirectory ($Label+'.stderr.log')
    $args=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(ConvertTo-SetupArgument $Script))+$Arguments
    $proc=Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Credential $script:setupCredential -LoadUserProfile -WorkingDirectory $script:setupParent -ArgumentList $args -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Hidden
    $handle=$null;$processExited=$false
    try {
        # Windows PS5 can return ExitCode=$null after redirected Start-Process.
        # Hold a native handle immediately; Refresh/ExitCode is not authoritative.
        $handle=Open-SetupChildProcess $proc.Id
        Write-SetupJson (Join-Path $ReportDirectory ($Label+'.process.json')) @{schemaVersion=1;pid=$proc.Id;startedUtc=(Get-SetupChildProcessStartUtc $handle);expectedExecutable="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe";expectedSid=$script:setupAccount.SID.Value;instanceId=$script:setupPlan.id;complete=$false}
        if(-not(Wait-SetupChildProcess $handle $Timeout)){
            $script:setupResult.processState='indeterminate_child_may_be_running';$script:setupResult.childPid=$proc.Id
            $script:setupResult.retryAllowed=$false
            throw 'setup_child_still_running_do_not_retry'
        }
        $processExited=$true
        # WaitForExit() without a timeout drains asynchronous redirected output.
        $proc.WaitForExit()
        $nativeExitCode=Get-SetupChildProcessExitCode $handle
        $script:setupResult.nativeExitCode=$nativeExitCode
        $answer=Read-SetupChildResult $stdout
        if($answer.code-is[string]-and$answer.code-cmatch'^[a-z][a-z0-9_]{0,95}$'){$script:setupResult.childCode=$answer.code}
        if($answer.errorType-is[string]-and$answer.errorType-cmatch'^[A-Za-z][A-Za-z0-9_.+`]{0,159}$'){$script:setupResult.childErrorType=$answer.errorType}
        if(($answer.failureLine-is[int]-or$answer.failureLine-is[long])-and$answer.failureLine-ge1-and$answer.failureLine-le1000000){$script:setupResult.childFailureLine=$answer.failureLine}
        if($nativeExitCode-ne[uint32]$answer.exitCode){throw 'setup_child_exit_code_mismatch'}
        if($nativeExitCode-ne0-or-not$answer.valid){throw 'setup_child_failed_preserved'}
        return $answer
    } catch {
        if(-not$processExited){$script:setupResult.processState='indeterminate_child_may_be_running';$script:setupResult.childPid=$proc.Id;$script:setupResult.retryAllowed=$false}
        throw
    } finally {if($null-ne$handle){$handle.Dispose()};$proc.Dispose()}
}
try {
    Assert-SetupAdministrator
    Assert-SetupNoReparse $PlanPath;Assert-SetupNoReparse $ReportDirectory
    $ReportDirectory=[IO.Path]::GetFullPath($ReportDirectory)
    if([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($PlanPath))-cne$ReportDirectory-or-not[IO.Directory]::Exists($ReportDirectory)){throw 'setup_report_path_invalid'}
    foreach($path in @($ReportDirectory,$PlanPath)){
        $acl=Get-Acl -LiteralPath $path
        if($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value-notin@([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18','S-1-5-32-544')){throw 'setup_plan_acl_invalid'}
        foreach($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){if($rule.AccessControlType-ne'Allow'-or$rule.IdentityReference.Value-notin@([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18','S-1-5-32-544')){throw 'setup_plan_acl_invalid'}}
    }
    if(Test-Path -LiteralPath (Join-Path $ReportDirectory 'result.json')){throw 'setup_report_already_used'}
    $setupWritable=$true
    Set-SetupProgress 'verify' 2 'Verificando plan y archivos; sin cambios del sistema.'
    $setupPlan=Read-SetupPlan $PlanPath
    $setupPayloadRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
    $setupPayload=Assert-SetupPayload $setupPayloadRoot
    Set-SetupProgress 'host' 3 'Comprobando que el servidor permite cuentas locales.'
    $setupHost=Get-SetupHostCompatibility
    Write-SetupJson (Join-Path $ReportDirectory 'host-result.json') $setupHost
    $setupResult.hostProductType=$setupHost.productType;$setupResult.hostDomainRole=$setupHost.domainRole;$setupResult.hostPartOfDomain=$setupHost.partOfDomain
    if(-not$setupHost.valid){throw ([string]$setupHost.code)}
    # This candidate is enabled for the user's first real server installation/QA.
    # Runtime checks below decide success; it does not claim previous elevated validation.
    if($setupPayload.releaseGate-cne'server_qa_candidate'){throw 'setup_package_not_enabled_for_server_qa'}
    $setupParent='C:\ProgramData\RackClick\Instances\'+$setupPlan.id
    $setupInstance=Join-Path $setupParent 'instance';$setupManagement=Join-Path $setupParent 'management'
    $setupCode='C:\Program Files\RackClick\'+$setupPlan.id
    Assert-SetupNoReparse $setupParent;Assert-SetupNoReparse $setupCode
    if((Test-Path -LiteralPath $setupParent)-or(Test-Path -LiteralPath $setupCode)){throw 'setup_destination_exists'}
    if(Get-LocalUser -Name $setupPlan.accountName -ErrorAction SilentlyContinue){
        if($setupPlan.accountName-ceq'RackClickSvc'){$setupPlan.accountName='RackClickSvc'+$setupPlan.id.Replace('-','').Substring(0,8)}else{throw 'setup_account_exists'}
        if(Get-LocalUser -Name $setupPlan.accountName -ErrorAction SilentlyContinue){throw 'setup_account_exists'}
    }
    if(Get-Service -Name $setupPlan.serviceName -ErrorAction SilentlyContinue){throw 'setup_service_exists'}
    if(([IO.DriveInfo]::new('C')).AvailableFreeSpace-lt2147483648){throw 'setup_disk_space_insufficient'}
    $setupAddresses=@(Get-NetIPAddress -AddressFamily IPv4|Where-Object{$_.IPAddress-ceq$setupPlan.bindAddress-and$_.AddressState-eq'Preferred'})
    if($setupAddresses.Count-ne1){throw 'setup_bind_not_local'}
    $setupPorts=@([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()|ForEach-Object{$_.Port})
    if($setupPlan.httpsPort-in$setupPorts-or$setupPlan.postgresPort-in$setupPorts){throw 'setup_port_busy'}
    Set-SetupProgress 'prerequisite' 6 'Comprobando e instalando Visual C++ solamente si falta.'
    $setupCrt=Install-SetupCrt -PayloadRoot $setupPayloadRoot -ReportDirectory $ReportDirectory
    Write-SetupJson (Join-Path $ReportDirectory 'prerequisite-result.json') $setupCrt
    if($setupCrt.rebootRequired){$setupResult.rebootRequired=$true;throw 'setup_crt_restart_required'}
    if(-not$setupCrt.valid-or$setupCrt.exitCode-ne0){throw 'setup_crt_prerequisite_failed'}
    Set-SetupProgress 'account' 10 'Creando identidad de servicio nueva y claves locales.'
    $setupRandom=New-Object byte[] 36;$setupRng=[Security.Cryptography.RandomNumberGenerator]::Create()
    try{$setupRng.GetBytes($setupRandom)}finally{$setupRng.Dispose()}
    $setupPassword=ConvertTo-SecureString ('Rc!9'+[Convert]::ToBase64String($setupRandom)) -AsPlainText -Force
    [Array]::Clear($setupRandom,0,$setupRandom.Length)
    # New-LocalUser limits Description to 48 characters. Prefix plus full GUID = 46.
    $setupAccount=New-LocalUser -Name $setupPlan.accountName -Password $setupPassword -Description ('RackClick '+$setupPlan.id) -PasswordNeverExpires -UserMayNotChangePassword
    $setupCredential=New-Object Management.Automation.PSCredential(($env:COMPUTERNAME+'\'+$setupPlan.accountName),$setupPassword)
    if(-not @(Get-LocalGroupMember -SID 'S-1-5-32-545'|Where-Object{$_.SID.Value-eq$setupAccount.SID.Value}).Count){Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $setupAccount}
    if(@(Get-LocalGroupMember -SID 'S-1-5-32-544'|Where-Object{$_.SID.Value-eq$setupAccount.SID.Value}).Count){throw 'setup_service_account_privileged'}
    Grant-SetupServiceLogonRights $setupAccount.SID.Value
    New-SetupInstanceParent -Path $setupParent -ServiceSid $setupAccount.SID.Value -AllowCreate
    New-SetupManagementDirectory $setupManagement
    Save-SetupServiceCredential -Credential $setupCredential -ManagementPath $setupManagement
    Set-SetupPublicCodeDirectoryACL -Path $setupCode -ServiceSid $setupAccount.SID.Value
    Set-SetupProgress 'copy' 18 'Copiando programa verificado a Program Files.'
    foreach($item in @(Get-ChildItem -LiteralPath $setupPayloadRoot -Force)){Copy-Item -LiteralPath $item.FullName -Destination $setupCode -Recurse -ErrorAction Stop}
    $null=Assert-SetupPayload $setupCode
    $setupRestorePath=''
    if($setupPlan.mode-ceq'Restore'){$setupRestorePath=Copy-SetupRecoveryInput -BackupPath $setupPlan.backupPath -ExpectedManifestSha256 $setupPlan.backupManifestSha256 -DestinationPath (Join-Path $setupCode 'recovery-input')}
    $setupPreparationPlan=@{schemaVersion=1;id=$setupPlan.id;instancePath=$setupInstance;codeRoot=$setupCode;serviceSid=$setupAccount.SID.Value;publicOrigin=('https://'+$setupPlan.publicHost+':'+$setupPlan.httpsPort);bindAddress=$setupPlan.bindAddress;httpsPort=$setupPlan.httpsPort;postgresPort=$setupPlan.postgresPort;bootstrapUser=$setupPlan.bootstrapUser;systemhaus=$setupPlan.systemhaus;mode=$setupPlan.mode;backupPath=$setupRestorePath;backupManifestSha256=$setupPlan.backupManifestSha256;serviceName=$setupPlan.serviceName}
    $setupPreparationPath=Join-Path $setupCode 'preparation-plan.json';Write-SetupJson $setupPreparationPath $setupPreparationPlan
    Set-SetupProgress 'prepare' 25 'Preparando PostgreSQL nuevo bajo la cuenta estandar.'
    $setupPrepared=Invoke-SetupServiceChild (Join-Path $setupCode 'operators\server-install\Prepare-RackClickServer.ps1') @('-PlanPath',(ConvertTo-SetupArgument $setupPreparationPath),'-ResultPath',(ConvertTo-SetupArgument (Join-Path $setupInstance 'runtime\control\preparation-result.json'))) 'prepare'
    if($setupPrepared.code-cne'server_prepared'-or$setupPrepared.manifestSha256-cnotmatch'^[a-f0-9]{64}$'){throw 'setup_preparation_receipt_invalid'}
    $setupManifest=Join-Path $setupInstance 'runtime\server-profile.json'
    $setupManifestBytes=Read-SetupPreparedFile -InstancePath $setupInstance -RelativePath 'runtime/server-profile.json' -ServiceSid $setupAccount.SID.Value
    $setupSha=[Security.Cryptography.SHA256]::Create()
    try{$setupManifestDigest=([BitConverter]::ToString($setupSha.ComputeHash($setupManifestBytes))).Replace('-','').ToLowerInvariant()}finally{$setupSha.Dispose()}
    if($setupManifestDigest-cne$setupPrepared.manifestSha256){throw 'setup_preparation_hash_mismatch'}
    $setupCaBytes=Read-SetupPreparedFile -InstancePath $setupInstance -RelativePath 'runtime/RootCA.cer' -ServiceSid $setupAccount.SID.Value
    [IO.File]::WriteAllBytes((Join-Path $setupManagement 'RootCA.cer'),$setupCaBytes)
    # Preserve bootstrap credentials in the administrative recovery vault before sealing.
    $setupLoginBytes=Read-SetupPreparedFile -InstancePath $setupInstance -RelativePath 'deployment/instance/private/admin-login.json' -ServiceSid $setupAccount.SID.Value
    try{[IO.File]::WriteAllBytes((Join-Path $setupManagement 'admin-login.json'),$setupLoginBytes)}finally{[Array]::Clear($setupLoginBytes,0,$setupLoginBytes.Length)}
    Set-SetupProgress 'permissions' 55 'Separando programa inmutable y datos privados del servicio.'
    $setupRelativeDirs=@($setupPrepared.mutableDirectoryPaths|ForEach-Object{if(-not$_.StartsWith($setupInstance+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'setup_mutable_path_invalid'};$_.Substring($setupInstance.Length+1)})
    $setupRelativeFiles=@($setupPrepared.mutableFilePaths|ForEach-Object{if(-not$_.StartsWith($setupInstance+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'setup_mutable_path_invalid'};$_.Substring($setupInstance.Length+1)})
    Set-SetupServiceTreeSecurity -Path $setupInstance -ServiceSid $setupAccount.SID.Value -MutableDirectoryPaths $setupRelativeDirs -MutableFilePaths $setupRelativeFiles
    New-SetupInstanceParent -Path $setupParent -ServiceSid $setupAccount.SID.Value
    Set-SetupProgress 'mfa_keys' 60 'Preparando custodia MFA privada; politica de 45 dias sin bloquear cuentas existentes.'
    Set-SetupMfaContentAdministrativeRead -InstancePath $setupInstance -ServiceSid $setupAccount.SID.Value
    $setupMfaResult=Initialize-SetupMfaStore -InstancePath $setupInstance -CodeRoot $setupCode -InstallationId $setupPlan.id -ServiceSid $setupAccount.SID.Value -ExpectedManifestSha256 $setupPrepared.manifestSha256 -ExpectedBundleSha256 $setupPayload.bundleArchiveSha256
    Write-SetupJson (Join-Path $ReportDirectory 'mfa-initialization.json') $setupMfaResult
    Set-SetupProgress 'service' 65 'Registrando servicio Windows y acceso HTTPS de la red autorizada.'
    $setupDotnet=Join-Path $setupInstance 'content\dependencies\dotnet\dotnet.exe'
    $setupBinary=(ConvertTo-SetupArgument $setupDotnet)+' '+(ConvertTo-SetupArgument (Join-Path $setupCode 'service\RackClick.WindowsService.dll'))+' --config '+(ConvertTo-SetupArgument (Join-Path $setupInstance 'service-config.json'))
    $null=New-Service -Name $setupPlan.serviceName -BinaryPathName $setupBinary -Credential $setupCredential -StartupType Automatic -DisplayName ('RackClick '+$setupPlan.id)
    $setupFirewallName='RackClick-'+$setupPlan.id
    $null=New-NetFirewallRule -Name $setupFirewallName -DisplayName $setupFirewallName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $setupPlan.httpsPort -LocalAddress $setupPlan.bindAddress -RemoteAddress $setupPlan.allowedSubnet -Program $setupDotnet -Profile Any
    $setupTrusted=Import-Certificate -FilePath (Join-Path $setupManagement 'RootCA.cer') -CertStoreLocation 'Cert:\LocalMachine\Root'
    Start-Service -Name $setupPlan.serviceName
    Set-SetupProgress 'readiness' 80 'Comprobando servicio y readiness HTTPS; no basta que el proceso exista.'
    $setupReady=$false;$setupWatch=[Diagnostics.Stopwatch]::StartNew()
    while($setupWatch.Elapsed.TotalSeconds-lt120){
        try{$health=Invoke-RestMethod -Uri ($setupPreparationPlan.publicOrigin+'/health/ready') -TimeoutSec 5 -UseBasicParsing;if($health.status-eq'ready'-and$health.schemaVersion-eq15-and(Get-Service $setupPlan.serviceName).Status-eq'Running'){$setupReady=$true;break}}catch{}
        Start-Sleep -Milliseconds 500
    }
    if(-not$setupReady){throw 'setup_https_readiness_failed'}
    Set-SetupProgress 'backup' 88 'Creando la primera copia PostgreSQL online.'
    $setupBackup=Join-Path $setupInstance ('runtime\backups\initial-'+[guid]::NewGuid().ToString('N'))
    $setupBackupResult=Invoke-SetupServiceChild (Join-Path $setupCode 'operators\server-install\Invoke-RackClickServerRuntime.ps1') @('-Operation','Backup','-ManifestPath',(ConvertTo-SetupArgument $setupManifest),'-ExpectedManifestSha256',$setupPrepared.manifestSha256,'-BackupPath',(ConvertTo-SetupArgument $setupBackup)) 'initial-backup'
    $setupReceipt=@{schemaVersion=1;installationId=$setupPlan.id;installedUtc=[DateTime]::UtcNow.ToString('o');bootAtInstall=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o');serviceName=$setupPlan.serviceName;serviceSid=$setupAccount.SID.Value;accountName=$setupPlan.accountName;codeRoot=$setupCode;instancePath=$setupInstance;managementPath=$setupManagement;publicOrigin=$setupPreparationPlan.publicOrigin;manifestSha256=$setupPrepared.manifestSha256;firewallRule=$setupFirewallName;trustedCaThumbprint=$setupTrusted.Thumbprint;initialBackup=$setupBackup;backupResult=$setupBackupResult;rebootVerified=$false;productAdopted=$false}
    $setupReceipt.applicationSchemaVersion=15
    Set-SetupProgress 'scheduled_backup' 90 'Registrando backup diario y comprobacion automatica del proximo arranque.'
    $setupTasks=Register-SetupLifecycleTasks -Credential $setupCredential -InstallationId $setupPlan.id -CodeRoot $setupCode -ManifestPath $setupManifest -ManifestSha256 $setupPrepared.manifestSha256 -ManagementPath $setupManagement
    foreach($key in $setupTasks.Keys){$setupReceipt[$key]=$setupTasks[$key]}
    Write-SetupJson (Join-Path $setupManagement 'server-installation.json') $setupReceipt
    # Execute the real scheduled task once; registering a task alone is not success.
    $setupTaskStart=Get-Date
    Start-ScheduledTask -TaskName $setupTasks.backupTaskName
    $setupTaskWatch=[Diagnostics.Stopwatch]::StartNew();$setupTaskVerified=$false
    while($setupTaskWatch.Elapsed.TotalSeconds-lt300){
        $setupTask=Get-ScheduledTask -TaskName $setupTasks.backupTaskName
        $setupTaskInfo=Get-ScheduledTaskInfo -TaskName $setupTasks.backupTaskName
        if($setupTaskInfo.LastRunTime-ge$setupTaskStart.AddSeconds(-2)-and$setupTask.State-eq'Ready'){
            if($setupTaskInfo.LastTaskResult-ne0){throw 'setup_scheduled_backup_failed'}
            $setupTaskVerified=$true;break
        }
        Start-Sleep -Milliseconds 500
    }
    if(-not$setupTaskVerified){throw 'setup_scheduled_backup_not_confirmed'}
    $setupReceipt.scheduledBackupVerified=$true
    Write-SetupJson (Join-Path $setupManagement 'server-installation.json') $setupReceipt
    # Reboot and restore acceptance cannot be inferred from registration or an exit code.
    $setupResult.valid=$true;$setupResult.installedReady=$true
    $setupResult.code='setup_ready_reboot_verification_pending';$setupResult.stage='awaiting_reboot';$setupResult.installationPercent=95
    $setupResult.managementPath=$setupManagement;$setupResult.publicOrigin=$setupPreparationPlan.publicOrigin
    $setupResult.exitCode=3;$setupExit=3
} catch {
    $setupResult.errorType=$_.Exception.GetType().FullName
    $setupResult.errorHResult=$_.Exception.HResult
    $setupResult.failureLine=$_.InvocationInfo.ScriptLineNumber
    $setupCodeValue=[string]$_.Exception.Message
    if($setupCodeValue-cnotmatch'^setup_[a-z0-9_]{1,100}$'){$setupCodeValue='setup_stage_failed_preserved'}
    $setupResult.code=$setupCodeValue;$setupResult.exitCode=1;$setupExit=1
} finally {
    if($setupWritable){
        try{Write-SetupJson (Join-Path $ReportDirectory 'result.json') $setupResult;Write-SetupJson (Join-Path $ReportDirectory 'progress.json') @{stage=$setupResult.stage;percent=$setupResult.installationPercent;message=$setupResult.code;complete=$true;success=$setupResult.success}}catch{$setupExit=1}
    }
    if($null-ne$setupCredential){$setupCredential.Password.Dispose()}
}
$setupResult|ConvertTo-Json -Depth 4 -Compress
exit $setupExit
