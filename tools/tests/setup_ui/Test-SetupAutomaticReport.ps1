#requires -Version 5.1
[CmdletBinding()]
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
if($PSVersionTable.PSEdition-cne'Desktop'-or-not[Environment]::Is64BitProcess){throw 'Native Windows PowerShell5 x64 required'}
$sourceRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\windows\server-install'))
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot ('..\..\..\.local\setup-report-fixtures\'+[guid]::NewGuid().ToString('N'))))
$null=[IO.Directory]::CreateDirectory($root);$passed=New-Object Collections.Generic.List[string]
$originalLocalData=$env:LOCALAPPDATA;$env:LOCALAPPDATA=Join-Path $root 'local-appdata';$null=[IO.Directory]::CreateDirectory($env:LOCALAPPDATA)
function New-TestPrivateDirectory([string]$Path) {
    $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $acl=New-Object Security.AccessControl.DirectorySecurity
    $acl.SetSecurityDescriptorSddlForm(('O:'+$sid+'G:SYD:P(A;OICI;FA;;;'+$sid+')(A;OICI;FA;;;SY)'))
    $null=[IO.Directory]::CreateDirectory($Path,$acl)
}
try {
    . (Join-Path $sourceRoot 'Show-RackClickInstaller.ps1') -FunctionsOnly
    if('RackClick.Setup.ChildProcessNative'-as[type]){throw 'FunctionsOnly eagerly compiled native helper'}
    $passed.Add('Installer FunctionsOnly imports without elevation, WinForms or native initialization')
    if((Get-SetupUiBrokerOutcome ([pscustomobject]@{valid=$true;exitCode=3;installedReady=$true;stage='awaiting_reboot'}) 3)-cne'awaiting_reboot'){throw 'Valid ready result rejected'}
    if((Get-SetupUiBrokerOutcome ([pscustomobject]@{valid=$true;exitCode=0;success=$true;rebootVerified=$true}) 0)-cne'verified'){throw 'Valid verified result rejected'}
    $passed.Add('Broker UI accepts matching native exit3 readiness and exit0 verified reboot receipts')
    foreach($invalid in @(@{valid='true';exitCode=3;installedReady=$true;stage='awaiting_reboot'},@{valid=$true;exitCode='3';installedReady=$true;stage='awaiting_reboot'},@{valid=$true;exitCode=0;installedReady=$true;stage='awaiting_reboot'},@{valid=$true;exitCode=3;installedReady='true';stage='awaiting_reboot'})){
        if((Get-SetupUiBrokerOutcome ([pscustomobject]$invalid) 3)-cne'failed'){throw 'Unconfirmed ready receipt accepted'}
    };$passed.Add('Broker UI rejects JSON/native mismatch and string booleans/exit codes')
    foreach($exit in @(0,2,3)){
        $fixture=Join-Path $root ('exit-'+$exit+'.ps1');[IO.File]::WriteAllText($fixture,('Start-Sleep -Milliseconds 300;exit '+$exit))
        $tracked=Start-SetupUiTrackedProcess @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(ConvertTo-SetupUiArgument $fixture)) $root (Join-Path $root ('out-'+$exit+'.log')) (Join-Path $root ('err-'+$exit+'.log'))
        try {
            $watch=[Diagnostics.Stopwatch]::StartNew();$null=Test-SetupUiTrackedProcessComplete $tracked;$watch.Stop()
            if($watch.ElapsedMilliseconds-gt500){throw 'UI polling blocked while a process was still active'}
            $deadline=[DateTime]::UtcNow.AddSeconds(10)
            while(-not(Test-SetupUiTrackedProcessComplete $tracked)-and[DateTime]::UtcNow-lt$deadline){Start-Sleep -Milliseconds 30}
            if((Get-SetupUiTrackedExitCode $tracked)-ne$exit){throw 'UI native exit code incorrect'}
        }finally{Close-SetupUiTrackedProcess $tracked}
        if($null-ne$tracked.handle-or$null-ne$tracked.process){throw 'Tracked process handle leaked'}
        $passed.Add('Real redirected UI child exit'+$exit+', nonblocking polling and handle cleanup')
    }
    $attempt=[guid]::NewGuid().ToString('D');$session=[guid]::NewGuid().ToString('D')
    $recovery=Join-Path $env:LOCALAPPDATA ('RackClick\RecoverySessions\'+$session)
    $uiState=@{attemptId=$attempt;folder=$root;reportProcess=$null;reportOutput='';exitCode=2}
    function Start-SetupUiTrackedProcess([string[]]$Arguments,[string]$WorkingDirectory,[string]$StandardOutput,[string]$StandardError){$script:launchArguments=$Arguments;return @{process=$null;handle=$null;trackingFailed=$false}}
    Start-SetupUiReportExport $uiState $recovery
    if($script:launchArguments-cnotcontains'-Quiet'-or$script:launchArguments-cnotcontains'-AttemptId'-or$script:launchArguments[$script:launchArguments.IndexOf('-AttemptId')+1]-cne$attempt-or$script:launchArguments-cnotcontains(ConvertTo-SetupUiArgument $recovery)){throw 'Automatic report not bound to exact attempt and recovery session'}
    if($uiState.exitCode-ne2){throw 'Report export replaced original installer exit'}
    $passed.Add('Automatic export requests Quiet plus exact AttemptId and recovery directory without changing installer failure')
    if((Test-SetupUiReportDeadlineExpired $uiState)-or-not(Test-SetupUiReportDeadlineExpired @{reportDeadlineUtc=[DateTime]::UtcNow.AddSeconds(-1)})-or(Test-SetupUiReportDeadlineExpired @{reportDeadlineUtc=[DateTime]::UtcNow.AddSeconds(60)})){throw 'Nonblocking report deadline incorrect'}
    $passed.Add('Automatic report deadline expires after60 seconds without blocking or stopping its child')
    $invalidRejected=$false;$uiState.attemptId='not-a-guid'
    try{Start-SetupUiReportExport $uiState $recovery}catch{if($_.Exception.Message-cne'installer_report_attempt_invalid'){throw};$invalidRejected=$true}
    if(-not$invalidRejected){throw 'Unbound automatic report accepted'};$passed.Add('Automatic export rejects invalid attempt identity')
    . (Join-Path $sourceRoot 'Collect-RackClickInstallReport.ps1') -FunctionsOnly
    New-TestPrivateDirectory $recovery
    Write-SetupJson (Join-Path $recovery 'reset-result.json') @{valid=$true;success=$false;cleanupComplete=$true;exitCode=0;code='reset_complete';quarantinePath='SECRET_SENTINEL';actions=@(@{path='SECRET_SENTINEL'});archivedInstances=@('SECRET_SENTINEL','SECRET_SENTINEL');retiredAccounts=@(@{oldName='SECRET_SENTINEL'});preserved=@(@{path='SECRET_SENTINEL'});remainingBlockers=@();password='SECRET_SENTINEL'}
    Write-SetupJson (Join-Path $recovery 'launcher-result.json') @{valid=$false;exitCode=2;code='clean_setup_failed';stage='install';errorType='System.InvalidOperationException';failureLine=15;errorMessage='SECRET_SENTINEL'}
    $record=New-SetupSanitizedReport '' $recovery
    if($record.attemptCount-ne0-or$record.recoverySession.sessionId-cne$session-or$record.recoverySession.reset.fields.cleanupComplete-ne$true-or$record.recoverySession.reset.fields.archivedInstanceCount-ne2-or$record.recoverySession.reset.fields.retiredAccountCount-ne1-or$record.recoverySession.reset.fields.preservedCount-ne1-or$record.recoverySession.reset.fields.blockerCount-ne0){throw 'Recovery-only report or counts incorrect'}
    if(($record|ConvertTo-Json -Depth 10)-like'*SECRET_SENTINEL*'){throw 'Raw recovery fields escaped sanitization'}
    $passed.Add('Recovery-only report with zero setup attempts retains sanitized status and counts, excluding secret/path/action text')
    if($record.recoverySession.launcher.fields.stage-cne'install'-or$record.recoverySession.launcher.fields.failureLine-ne15){throw 'Launcher diagnostic lost'};$passed.Add('Sanitized launcher failure retained')
    foreach($bad in @($root,($recovery+'\'),($recovery+'\..\'+$session),(Join-Path ([IO.Path]::GetDirectoryName($recovery)) 'not-guid'))){
        $rejected=$false;try{$null=Get-SetupRecoveryDiagnostic $bad @([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18','S-1-5-32-544')}catch{$rejected=$true}
        if(-not$rejected){throw 'Unbound recovery path accepted'}
    };$passed.Add('Recovery path rejects foreign, trailing slash, traversal and non-GUID directories')
    $badAcl=[IO.Directory]::GetAccessControl($recovery,[Security.AccessControl.AccessControlSections]::Access)
    $foreignRule=New-Object Security.AccessControl.FileSystemAccessRule((New-Object Security.Principal.SecurityIdentifier('S-1-1-0')),'Read','ContainerInherit,ObjectInherit','None','Allow')
    $badAcl.AddAccessRule($foreignRule);[IO.Directory]::SetAccessControl($recovery,$badAcl)
    $rejected=$false;try{$null=Get-SetupRecoveryDiagnostic $recovery @([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18','S-1-5-32-544')}catch{if($_.Exception.Message-cne'report_recovery_acl_invalid'){throw};$rejected=$true}finally{$null=$badAcl.RemoveAccessRule($foreignRule);[IO.Directory]::SetAccessControl($recovery,$badAcl)}
    if(-not$rejected){throw 'Foreign recovery reader accepted'};$passed.Add('Recovery session rejects foreign ACL readers')
    $older=[guid]::NewGuid().ToString('D');$newer=[guid]::NewGuid().ToString('D')
    foreach($id in @($older,$newer)){$folder=Join-Path $env:LOCALAPPDATA ('RackClick\Setup\'+$id);New-TestPrivateDirectory $folder;Write-SetupJson (Join-Path $folder 'result.json') @{valid=$false;exitCode=2;code='setup_fixture_failed';password='SECRET_SENTINEL'}}
    $specific=New-SetupSanitizedReport $older $recovery
    if($specific.attemptId-cne$older-or$specific.attemptCount-ne1-or$specific.additionalAttempts.Count-ne0){throw 'Specific report silently switched to another attempt'};$passed.Add('Explicit AttemptId selects only its exact fixture, never the latest attempt')
    $manual=New-SetupSanitizedReport '' $recovery
    if($manual.attemptCount-ne2-or$manual.additionalAttempts.Count-ne1){throw 'Manual multi-attempt report regressed'};$passed.Add('Manual collection retains separate recent attempts')
    $exports=Join-Path $root 'exports';$null=[IO.Directory]::CreateDirectory($exports)
    $zip=Export-SetupSanitizedReport $specific $exports
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive=[IO.Compression.ZipFile]::OpenRead($zip)
    try{if($archive.Entries.Count-ne1-or$archive.Entries[0].FullName-cne'INFORME.json'){throw 'Unexpected report ZIP entries'};$reader=New-Object IO.StreamReader($archive.Entries[0].Open());try{$json=$reader.ReadToEnd()}finally{$reader.Dispose()}}finally{$archive.Dispose()}
    if($json-like'*SECRET_SENTINEL*'-or($json|ConvertFrom-Json).attemptId-cne$older){throw 'Exported ZIP leaks raw recovery/attempt values or loses identity'};$passed.Add('Actual report ZIP has one sanitized INFORME.json with matching attempt identity')
    function Get-SetupUiDesktopPath {return $exports}
    function Get-SetupUiTrackedExitCode($Tracked){return 0}
    $reportOutput=Join-Path $root 'automatic-report-receipt.json'
    Write-SetupJson $reportOutput @{valid=$true;exitCode=0;code='report_exported';zipPath=$zip;attemptId=$older}
    $completion=@{attemptId=$older;reportOutput=$reportOutput;reportProcess=@{process=$null;handle=$null};exitCode=2}
    if(-not(Test-SetupUiReportReceiptReadable $reportOutput)){throw 'Complete automatic receipt not readable'}
    $notice=Complete-SetupUiReportExport $completion
    if($notice-notlike'*Informe automatico*'-or$notice-notlike('*'+$zip)-or$completion.exitCode-ne2-or$null-ne$completion.reportProcess){throw 'Report completion lost original failure or leaked tracked state'}
    $passed.Add('Actual UI report completion validates exported ZIP and preserves original failure; isolated Desktop resolver only')
    Write-SetupJson $reportOutput @{valid=$true;exitCode=0;code='report_exported';zipPath=$zip;attemptId=$newer}
    $completion.reportProcess=@{process=$null;handle=$null};$rejected=$false
    try{$null=Complete-SetupUiReportExport $completion}catch{if($_.Exception.Message-cne'installer_report_receipt_invalid'){throw};$rejected=$true}
    if(-not$rejected-or$null-ne$completion.reportProcess-or$completion.exitCode-ne2){throw 'Wrong-attempt report accepted or completion hid original failure'};$passed.Add('Wrong-attempt export rejected with handle cleanup and original failure preserved')
    $output=& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $sourceRoot 'Collect-RackClickInstallReport.ps1') -Quiet -RecoverySessionDirectory 'C:\invalid-report-fixture'
    if($LASTEXITCODE-ne1-or($output|ConvertFrom-Json).valid-ne$false){throw 'Quiet collector failure not machine readable'};$passed.Add('Quiet collector failure returns JSON without UAC or MessageBox')
    $output=& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $sourceRoot 'Prepare-RackClickServer.ps1') -PlanPath 'C:\SECRET_SENTINEL\invalid-plan.json' -ResultPath (Join-Path $root 'should-not-exist.json')
    if($LASTEXITCODE-ne2){throw 'Early preparation fixture unexpectedly succeeded'}
    $failure=$output|ConvertFrom-Json -ErrorAction Stop
    if($failure.valid-ne$false-or$failure.stage-cnotin@('identity','plan')-or$failure.errorType-cnotmatch'^[A-Za-z][A-Za-z0-9_.+`]{0,159}$'-or$failure.errorHResult-isnot[int]-or$failure.failureLine-isnot[int]-or$failure.failureLine-lt1-or[IO.File]::Exists((Join-Path $root 'should-not-exist.json'))-or($output-join'')-like'*SECRET_SENTINEL*'){throw 'Early preparation diagnostic absent or leaked raw input'}
    $passed.Add('Actual preparer early rejection emits stage, CLR type, HResult and line before creating private folders; no raw path')
    $result=[ordered]@{schemaVersion=1;valid=$true;passed=$passed.Count;checks=$passed;fixtureRoot=$root;environment='Native Windows PowerShell5.1 x64; real own child processes and isolated private file fixtures';accountsCreated=0;servicesCreated=0;sqlExecuted=0;elevatedOperationsExecuted=0;desktopFilesCreated=0;limits=@('No broker entrypoint, service identity launch, reset, OS account, service, database, firewall or VM operation was executed.','Automatic export wiring was inspected through the real UI helper with only the launch boundary substituted; actual ZIP writing used an isolated fixture directory.')}
    if($OutputPath){[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath),($result|ConvertTo-Json -Depth 5),(New-Object Text.UTF8Encoding($false)))}
    $result|ConvertTo-Json -Depth 5 -Compress
} finally {$env:LOCALAPPDATA=$originalLocalData}
