#requires -Version 5.1
# A NEW deliberate diagnostic; never resumes or removes the consumed SYSTEM read.
[CmdletBinding()]
param(
    [ValidateSet('Check','Run','Worker','SelfTest')][string]$Mode='Check',
    [string]$AttemptRoot='C:\ProgramData\RackClick-MFA-SystemRead-8637bb52faee4b2a96992bcf4d7591b8',
    [string]$PackageRoot='',
    [string]$ExpectedScriptSha256='',
    [string]$ExpectedSumsSha256='',
    [string]$PlanPath='',
    [string]$ExpectedPlanSha256=''
)
$ErrorActionPreference='Stop'
$BasePin='6fa659e61e10571168cd0d8fffd21ca7f729bbacee41021d44eb9e8d62237cb9'
$ResumePin='418ad1194ef9bb33697fc29825e603859f296fe88a057acf464c2278f65c52be'
$CodeHelperPin='fc8af467e025f1a730e684c9a4df9b1fc69c39b2b19a4db465820e21dea4d632'
$ZipPin='c957e0c90d7af77cc01a08ccec4581af8d9d3410c0388656377409a4249551b2'
$SumsPin='803a8373d7c9fa8cc9d230e285f4b4e5ca0b84f222c68d10980278652f16035b'
$ReferenceScriptPin='b2058cfcf37a14e8892c4d299089327a8bbf778425e061fe93b34ea5f0ae190e'
$ReferenceFolder='RackClick-MFA-Lectura-L2l02'
$WorkPrefix='RackClick-MFA-SystemRead-'
$TaskDacl='D:P(A;;FA;;;SY)(A;;FA;;;BA)'
$DiagnosticFile='diagnostic/RackClick.MfaProbeExceptionDiagnostic.dll'
$DiagnosticRequired=@('Invoke-MfaProbeExceptionDiagnostic.ps1','Resume-MfaServiceReadSystemTrial03.ps1',
    'RackClick.MfaDiagnosticCode.ps1',
    'diagnostic/RackClick.MfaProbeExceptionDiagnostic.dll','diagnostic/RackClick.MfaProbeExceptionDiagnostic.deps.json',
    'diagnostic/RackClick.MfaProbeExceptionDiagnostic.runtimeconfig.json')
$DiagnosticTypes=@('none','argument','security','directory_missing','access_denied','io','assembly_load','invalid_operation','other')
$DiagnosticFrames=@('ReadService','ImpersonatedRead','ServiceMeasure.Measure','ServiceMeasure.QueryConfig',
    'ServiceMeasure.ResolveAccount','ImageMatch.Matches','ImageMatch.ProcessImage','TokenLink.SidOf',
    'TokenLink.DuplicateForImpersonation','Access.OpenProcess','Access.OpenToken','DebugPrivilege.EnsureEnabled',
    'DebugPrivilege.Restore','DebugPrivilege.Dispose','WriteProbe.CheckStore','WriteProbe.ProbeTarget',
    'StoreRead.ReadActiveKey','Directory.EnumerateFiles','Path.GetFullPath','WindowsIdentity.RunImpersonated')

function Stop-Diagnostic([string]$Code) { throw ('mfa_diagnostic:'+ $Code) }
function Get-DiagnosticCode($Record) {
    if ($Record.Exception.Message -cmatch '^(?:mfa_diagnostic|system_trial|resume_trial|trial):([a-z][a-z0-9_]{0,99})$') { return $Matches[1] }
    return 'diagnostic_failed'
}
function Get-DiagnosticHash([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Assert-DiagnosticNoReparse([string]$Path) {
    $item=Get-Item -LiteralPath $Path -Force
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { Stop-Diagnostic 'reparse_point' }
        if ($item -is [IO.FileInfo]) { $item=$item.Directory } else { $item=$item.Parent }
    }
}
function Assert-DiagnosticPath([string]$Path) {
    if ($Path -cnotmatch '^[A-Za-z]:[\\/]' -or $Path.Substring(2).Contains(':') -or $Path -match '[\x00-\x1f"]') { Stop-Diagnostic 'path_invalid' }
    return [IO.Path]::GetFullPath($Path)
}
function Import-DiagnosticPinnedFunctions([string]$Path,[string]$Pin,[bool]$Resume) {
    if ((Get-DiagnosticHash $Path) -cne $Pin) { Stop-Diagnostic 'helper_hash_mismatch' }
    $tokens=$null;$errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseInput([IO.File]::ReadAllText($Path),[ref]$tokens,[ref]$errors)
    if ($errors.Count) { Stop-Diagnostic 'helper_source_invalid' }
    $rename=@{'Stop-Resume'='Stop-Resume03';'Resume-HResults'='Resume-HResults03';
        'Assert-ResumeRoot'='Assert-ResumeRoot03';'Assert-ResumePlan'='Assert-ResumePlan03';
        'Read-ResumeTaskXml'='Read-ResumeTaskXml03';'Task-Scalar'='Task-Scalar03';
        'Canonical-System'='Canonical-System03';'Canonical-TaskCommand'='Canonical-TaskCommand03';
        'Assert-ResumeTask'='Assert-ResumeTask03';'Assert-RegisteredTaskSettings'='Assert-RegisteredSettings03';
        'New-ResumeDefinition'='New-ResumeDefinition03';'Get-ResumeTask'='Get-ResumeTask03'}
    $definitions=New-Object Collections.Generic.List[string]
    foreach ($node in $ast.EndBlock.Statements) {
        if ($node -isnot [Management.Automation.Language.FunctionDefinitionAst]) { continue }
        if ($Resume -and -not $rename.ContainsKey($node.Name)) { continue }
        $definition=$node.Extent.Text
        if ($Resume) {
            foreach ($name in @($rename.Keys | Sort-Object Length -Descending)) {
                $definition=[regex]::Replace($definition,'(?<![\w-])'+[regex]::Escape($name)+'(?![\w-])',$rename[$name])
            }
        }
        # Export definitions only; callers return before Worker/task code uses them.
        $definition=[regex]::Replace($definition,'\Afunction\s+','function script:')
        $definitions.Add($definition)
    }
    if (($Resume -and $definitions.Count -ne $rename.Count) -or $definitions.Count -eq 0) { Stop-Diagnostic 'helper_functions_invalid' }
    . ([scriptblock]::Create(($definitions -join "`n")))
}
function Test-DiagnosticPackage([string]$Root,[string]$Pin) {
    if ($Pin -cnotmatch '^[a-f0-9]{64}$') { Stop-Diagnostic 'sums_pin_required' }
    Assert-DiagnosticNoReparse $Root
    $sums=Join-Path $Root 'SHA256SUMS';Assert-DiagnosticNoReparse $sums
    $seen=@{}
    foreach ($line in [IO.File]::ReadAllLines($sums)) {
        $entry=ConvertFrom-SumsLine $line
        if ($entry.rel -cnotmatch '^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$' -or
            $entry.rel -match '(^|/)\.\.?(/|$)' -or $entry.rel -ieq 'SHA256SUMS' -or $seen.ContainsKey($entry.rel)) { Stop-Diagnostic 'diagnostic_sums_path_invalid' }
        $seen[$entry.rel]=$true
    }
    $RequiredRel=$DiagnosticRequired
    return (Test-PackageIntegrity $Root $Pin)
}
function Add-DiagnosticLease($Leases,[string]$Path) {
    Assert-DiagnosticNoReparse $Path
    $Leases.Add([IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read))
}
function Get-DiagnosticServiceReaderSid([string]$Name) {
    Assert-ServiceName $Name
    $serviceRows=@(Get-CimInstance Win32_Service -Filter ("Name = '"+$Name+"'"))
    if ($serviceRows.Count -ne 1 -or $serviceRows[0].State -cne 'Running' -or [uint32]$serviceRows[0].ProcessId -eq 0) { Stop-Diagnostic 'service_not_running' }
    $account=[string]$serviceRows[0].StartName
    if ([string]::IsNullOrWhiteSpace($account)) { Stop-Diagnostic 'reader_account_invalid' }
    if ($account.StartsWith('.\',[StringComparison]::Ordinal)) { $account=$env:COMPUTERNAME+'\'+$account.Substring(2) }
    try { $sid=(New-Object Security.Principal.NTAccount($account)).Translate([Security.Principal.SecurityIdentifier]).Value }
    catch { Stop-Diagnostic 'reader_account_unresolved' }
    Assert-MfaCodeReader $sid
    return $sid
}
function Read-DiagnosticContext($Leases,[string]$Source,[string]$SourcePin,[string]$NewPackage,[string]$NewSumsPin) {
    if ($SourcePin -cnotmatch '^[a-f0-9]{64}$') { Stop-Diagnostic 'script_pin_required' }
    Add-DiagnosticLease $Leases $Source
    if ((Get-DiagnosticHash $Source) -cne $SourcePin) { Stop-Diagnostic 'script_hash_mismatch' }
    $expectedAttempt=Join-Path $env:ProgramData ($WorkPrefix+'8637bb52faee4b2a96992bcf4d7591b8')
    if ((Assert-DiagnosticPath $AttemptRoot) -ine [IO.Path]::GetFullPath($expectedAttempt)) { Stop-Diagnostic 'old_attempt_invalid' }
    Assert-DiagnosticNoReparse $AttemptRoot
    $base=Join-Path $AttemptRoot 'worker.ps1';Add-DiagnosticLease $Leases $base
    Import-DiagnosticPinnedFunctions $base $BasePin $false
    Assert-Elevated;Assert-PrivateRoot $AttemptRoot
    $NewPackage=Assert-DiagnosticPath $NewPackage
    $resume=Join-Path $NewPackage 'Resume-MfaServiceReadSystemTrial03.ps1';Add-DiagnosticLease $Leases $resume
    Import-DiagnosticPinnedFunctions $resume $ResumePin $true
    Assert-ResumeRoot03 $AttemptRoot
    $codeHelper=Join-Path $NewPackage 'RackClick.MfaDiagnosticCode.ps1';Add-DiagnosticLease $Leases $codeHelper
    Import-DiagnosticPinnedFunctions $codeHelper $CodeHelperPin $false
    $oldPlanFile=Join-Path $AttemptRoot 'plan.json';Add-DiagnosticLease $Leases $oldPlanFile
    $oldPlan=[IO.File]::ReadAllText($oldPlanFile) | ConvertFrom-Json;Assert-ResumePlan03 $oldPlan $AttemptRoot
    # The read was already consumed. Its marker and result must remain present, leased and untouched.
    Add-DiagnosticLease $Leases (Join-Path $AttemptRoot 'execution.started')
    $oldResultFile=Join-Path $AttemptRoot 'worker-result.json';Add-DiagnosticLease $Leases $oldResultFile
    $oldResult=[IO.File]::ReadAllText($oldResultFile) | ConvertFrom-Json
    if ($oldResult.schemaVersion -ne 1 -or $oldResult.executor -cne 'SYSTEM' -or $oldResult.reader -cne 'service_token' -or
        $oldResult.installationId -cne $oldPlan.installationId -or $oldResult.status -cne 'failed' -or
        $oldResult.code -cne 'unexpected_error' -or $oldResult.fingerprintState -cne 'unchanged') { Stop-Diagnostic 'old_result_invalid' }
    $oldPackage=Join-Path $AttemptRoot $ReferenceFolder
    $reference=Join-Path $oldPackage 'Invoke-MfaServiceReadTrial.ps1';Add-DiagnosticLease $Leases $reference
    . Import-ReferenceFunctions ([IO.File]::ReadAllText($reference))
    # The pinned importer checks its original prefix. Export only its definitions for later calls.
    Import-DiagnosticPinnedFunctions $reference $ReferenceScriptPin $false
    $script:ChildEnvRemovePattern=$ChildEnvRemovePattern
    Assert-NoReparse $oldPackage;$null=Test-PackageIntegrity $oldPackage $SumsPin
    foreach ($file in @(Get-ChildItem -LiteralPath $oldPackage -Recurse -File -Force)) { Add-DiagnosticLease $Leases $file.FullName }
    $null=Test-PackageIntegrity $oldPackage $SumsPin
    $null=Test-DiagnosticPackage $NewPackage $NewSumsPin
    foreach ($file in @(Get-ChildItem -LiteralPath $NewPackage -Recurse -File -Force)) { Add-DiagnosticLease $Leases $file.FullName }
    $null=Test-DiagnosticPackage $NewPackage $NewSumsPin
    if ((Get-DiagnosticHash (Join-Path $NewPackage 'Invoke-MfaProbeExceptionDiagnostic.ps1')) -cne $SourcePin) { Stop-Diagnostic 'package_launcher_mismatch' }
    $context=Get-Context $oldPlan.trialRoot $oldPlan.service
    if ($context.installationId -cne $oldPlan.installationId) { Stop-Diagnostic 'context_changed' }
    $before=Get-StoreFingerprint $oldPlan.trialRoot
    if ($before.digest -cne $oldPlan.beforeDigest -or $before.count -ne $oldPlan.beforeCount) { Stop-Diagnostic 'store_changed_before_diagnostic' }
    $codeContext=[pscustomobject]@{oldPlan=$oldPlan;oldPlanSha256=(Get-DiagnosticHash $oldPlanFile);oldPackage=$oldPackage;package=$NewPackage;before=$before;
        readerSid=(Get-DiagnosticServiceReaderSid $oldPlan.service);codeRoot='';codeManifest=$null}
    $codeContext.codeManifest=Get-DiagnosticCodeManifest $codeContext
    return $codeContext
}
function Assert-DiagnosticConfirmation([string]$Typed,[string]$Id) {
    if ($Typed -cne ('CONFIRMO DIAGNOSTICO SYSTEM '+$Id)) { Stop-Diagnostic 'confirmation_mismatch' }
}
function Confirm-Diagnostic([string]$Id) {
    if ([Console]::IsInputRedirected) { Stop-Diagnostic 'console_required' }
    Write-Host ('Nuevo diagnostico SYSTEM; no activa MFA. Escriba: CONFIRMO DIAGNOSTICO SYSTEM '+$Id)
    Assert-DiagnosticConfirmation (Read-Host 'Confirmacion') $Id
}
function Assert-DiagnosticShape($Value,[string[]]$Names) {
    if ($null -eq $Value -or @($Value.PSObject.Properties.Name).Count -ne $Names.Count -or
        @($Names | Where-Object {$_ -cnotin @($Value.PSObject.Properties.Name)}).Count -ne 0) { Stop-Diagnostic 'diagnostic_contract_invalid' }
}
function Test-DiagnosticInt32($Value) { return (($Value -is [int] -or $Value -is [long]) -and $Value -ge [int]::MinValue -and $Value -le [int]::MaxValue) }
function Assert-DiagnosticOutcome($Raw) {
    Assert-DiagnosticShape $Raw @('schemaVersion','status','code','exceptionType','hresult','win32Error','frames','outcome')
    if ($Raw.schemaVersion -isnot [int] -or $Raw.schemaVersion -ne 1 -or $Raw.status -cne 'measured' -or
        $Raw.code -cnotin @('exception_captured','returned') -or $Raw.exceptionType -cnotin $DiagnosticTypes -or
        -not (Test-DiagnosticInt32 $Raw.hresult) -or -not (Test-DiagnosticInt32 $Raw.win32Error) -or
        $Raw.frames -isnot [Array] -or $Raw.frames.Count -gt 16) { Stop-Diagnostic 'diagnostic_contract_invalid' }
    foreach ($frame in $Raw.frames) { if ($frame -isnot [string] -or $frame -cnotin $DiagnosticFrames) { Stop-Diagnostic 'diagnostic_contract_invalid' } }
    if ($Raw.code -ceq 'exception_captured') {
        if ($Raw.exceptionType -ceq 'none' -or $null -ne $Raw.outcome) { Stop-Diagnostic 'diagnostic_contract_invalid' }
    } else {
        if ($Raw.exceptionType -cne 'none' -or $Raw.hresult -ne 0 -or $Raw.win32Error -ne 0 -or $Raw.frames.Count -ne 0) { Stop-Diagnostic 'diagnostic_contract_invalid' }
        if ($null -eq $Raw.outcome) { Stop-Diagnostic 'diagnostic_contract_invalid' }
        if ($null -ne $Raw.outcome) {
            Assert-DiagnosticShape $Raw.outcome @('probeCode','processLinked','tokenMatched','impersonationVerified','identityRestored','activeVersion','keyBytes')
            if ($Raw.outcome.probeCode -isnot [string] -or ($Raw.outcome.probeCode -cne '' -and $Raw.outcome.probeCode -cnotmatch '^[a-z][a-z0-9_]{0,99}$')) { Stop-Diagnostic 'diagnostic_contract_invalid' }
            foreach ($flag in @('processLinked','tokenMatched','impersonationVerified','identityRestored')) { if ($Raw.outcome.$flag -isnot [bool]) { Stop-Diagnostic 'diagnostic_contract_invalid' } }
            if (-not (Test-DiagnosticInt32 $Raw.outcome.activeVersion) -or -not (Test-DiagnosticInt32 $Raw.outcome.keyBytes)) { Stop-Diagnostic 'diagnostic_contract_invalid' }
        }
    }
}
function Invoke-DiagnosticProcess($Context,$Plan) {
    $psi=New-Object Diagnostics.ProcessStartInfo
    if ($Context.codeRoot -cne $Plan.codeRoot) { Stop-Diagnostic 'code_context_invalid' }
    $psi.FileName=Join-Path $Context.codeRoot 'runtime/dotnet.exe'
    $psi.Arguments='"'+(Join-Path $Context.codeRoot $DiagnosticFile)+'" measure --probe "'+(Join-Path $Context.codeRoot 'probe/RackClick.MfaServiceReadProbe.dll')+
        '" --instances-root "'+$Plan.trialRoot+'" --installation-id '+$Plan.installationId+' --service "'+$Plan.service+'"'
    $psi.WorkingDirectory=$Context.codeRoot;$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true
    $psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true
    Set-ProbeChildEnvironment $psi
    $process=$null
    try {
        $process=[Diagnostics.Process]::Start($psi)
        $stdoutTask=$process.StandardOutput.ReadToEndAsync();$stderrTask=$process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(90000)) { $process.Kill();$process.WaitForExit();Stop-Diagnostic 'diagnostic_timeout' }
        $process.WaitForExit();$stdout=$stdoutTask.Result;$stderr=$stderrTask.Result
        # Never print or persist raw stdout/stderr. Only the closed protocol can leave this function.
        if ($process.ExitCode -notin @(0,1) -or $stderr.Length -ne 0 -or $stdout.Length -gt 16384) { Stop-Diagnostic 'diagnostic_process_failed' }
        $lines=@($stdout -split "`r?`n" | Where-Object {$_ -cne ''})
        if ($lines.Count -ne 1) { Stop-Diagnostic 'diagnostic_output_invalid' }
        try { $raw=$lines[0] | ConvertFrom-Json } catch { Stop-Diagnostic 'diagnostic_output_invalid' }
        Assert-DiagnosticOutcome $raw
        return $raw
    } finally { if ($null -ne $process) { $process.Dispose() } }
}
function Invoke-DiagnosticFingerprint($Context,$Plan) {
    $result=[ordered]@{schemaVersion=1;status='failed';code='diagnostic_failed';executor='SYSTEM';reader='service_token';installationId=$Plan.installationId;
        fingerprintState='not_checked';beforeDigest='';afterDigest='';beforeCount=0;afterCount=0;diagnostic=$null}
    $before=$null
    try {
        $before=Get-StoreFingerprint $Plan.trialRoot;$result.beforeDigest=$before.digest;$result.beforeCount=$before.count
        if ($before.digest -cne $Plan.beforeDigest -or $before.count -ne $Plan.beforeCount) { Stop-Diagnostic 'store_changed_before_diagnostic' }
        $result.diagnostic=Invoke-DiagnosticProcess $Context $Plan
        $result.status='measured';$result.code=$result.diagnostic.code
    } catch { $result.code=Get-DiagnosticCode $_ }
    finally {
        try {
            $after=Get-StoreFingerprint $Plan.trialRoot;$result.afterDigest=$after.digest;$result.afterCount=$after.count
            if ($null -ne $before -and $before.digest -ceq $after.digest -and $before.count -eq $after.count) { $result.fingerprintState='unchanged' }
            else { $result.fingerprintState='changed';$result.status='failed';$result.code='store_state_changed' }
        } catch { $result.fingerprintState='unavailable';$result.status='failed';$result.code='fingerprint_after_failed' }
    }
    return $result
}
function Assert-DiagnosticNewRoot([string]$Root) {
    $full=Assert-DiagnosticPath $Root
    if ([IO.Path]::GetDirectoryName($full) -ine [IO.Path]::GetFullPath($env:ProgramData) -or
        [IO.Path]::GetFileName($full) -cnotmatch '^RackClick-MFA-SystemRead-[a-f0-9]{32}$' -or
        $full -ieq [IO.Path]::GetFullPath($AttemptRoot)) { Stop-Diagnostic 'new_root_invalid' }
}
function Assert-DiagnosticNotStarted([string]$Root) {
    foreach ($name in @('execution.started','worker-result.json')) { if (Test-Path -LiteralPath (Join-Path $Root $name)) { Stop-Diagnostic 'diagnostic_already_started' } }
}
function Assert-DiagnosticPlan($Plan,$Context,[string]$Root,[string]$SourceHash) {
    Assert-DiagnosticShape $Plan @('schemaVersion','taskName','scriptSha256','sumsSha256','attemptRoot','oldPlanSha256','packageRoot','trialRoot','installationId','service','beforeDigest','beforeCount',
        'codeRoot','readerSid','codeManifestSha256','codeCount')
    Assert-DiagnosticNewRoot $Root
    $expectedCodeRoot=Join-Path $env:ProgramData ('RackClick-MFA-Code-'+(Split-Path -Leaf $Root).Substring($WorkPrefix.Length))
    if ((Assert-DiagnosticCodePath $Plan.codeRoot) -cne $expectedCodeRoot -or $Plan.readerSid -cne $Context.readerSid -or
        $Plan.codeManifestSha256 -cne $Context.codeManifest.digest -or $Plan.codeCount -ne 352 -or $Plan.codeCount -ne $Context.codeManifest.count) { Stop-Diagnostic 'code_plan_invalid' }
    if ($Plan.schemaVersion -isnot [int] -or $Plan.schemaVersion -ne 1 -or $Plan.taskName -cne (Split-Path -Leaf $Root) -or
        $Plan.scriptSha256 -cne $SourceHash -or $Plan.sumsSha256 -cnotmatch '^[a-f0-9]{64}$' -or
        $Plan.attemptRoot -cne $AttemptRoot -or $Plan.oldPlanSha256 -cne $Context.oldPlanSha256 -or $Plan.packageRoot -cne $Context.package -or
        $Plan.trialRoot -cne $Context.oldPlan.trialRoot -or $Plan.installationId -cne $Context.oldPlan.installationId -or
        $Plan.service -cne $Context.oldPlan.service -or $Plan.beforeDigest -cne $Context.before.digest -or $Plan.beforeCount -ne $Context.before.count) { Stop-Diagnostic 'plan_contract_invalid' }
}
function Invoke-DiagnosticWorker {
    if ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -cne 'S-1-5-18' -or
        $null -ne [Security.Principal.WindowsIdentity]::GetCurrent($true)) { Stop-Diagnostic 'worker_not_system' }
    if ($ExpectedPlanSha256 -cnotmatch '^[a-f0-9]{64}$') { Stop-Diagnostic 'plan_pin_invalid' }
    $leases=New-Object Collections.Generic.List[IDisposable]
    try {
        $PlanPath=Assert-DiagnosticPath $PlanPath;$root=[IO.Path]::GetDirectoryName($PlanPath)
        Assert-DiagnosticNewRoot $root
        if ([IO.Path]::GetFileName($PlanPath) -cne 'plan.json' -or [IO.Path]::GetFullPath($PSCommandPath) -ine (Join-Path $root 'worker.ps1')) { Stop-Diagnostic 'worker_path_invalid' }
        Add-DiagnosticLease $leases $PlanPath
        if ((Get-DiagnosticHash $PlanPath) -cne $ExpectedPlanSha256) { Stop-Diagnostic 'plan_hash_mismatch' }
        $plan=[IO.File]::ReadAllText($PlanPath) | ConvertFrom-Json
        $context=Read-DiagnosticContext $leases $PSCommandPath $plan.scriptSha256 $plan.packageRoot $plan.sumsSha256
        Assert-PrivateRoot $root;Assert-DiagnosticPlan $plan $context $root (Get-DiagnosticHash $PSCommandPath)
        $context.codeRoot=$plan.codeRoot
        Assert-DiagnosticCodePayload $context.codeRoot $context.readerSid $context.codeManifest $leases
        Assert-DiagnosticNotStarted $root
        # Persistent CreateNew is exclusive for THIS diagnostic, never the consumed attempt.
        $marker=New-Object IO.FileStream((Join-Path $root 'execution.started'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        $marker.Dispose()
        try { Assert-ImpersonatePrivilege;$result=Invoke-DiagnosticFingerprint $context $plan }
        catch { $result=[ordered]@{schemaVersion=1;status='failed';code=(Get-DiagnosticCode $_);executor='SYSTEM';reader='service_token';installationId=$plan.installationId;
            fingerprintState='not_checked';beforeDigest='';afterDigest='';beforeCount=0;afterCount=0;diagnostic=$null} }
        Write-NewJson (Join-Path $root 'worker-result.json') $result
        if ($result.status -cne 'measured') { exit 1 }
    } finally { foreach ($lease in $leases) { $lease.Dispose() } }
}
function Get-DiagnosticSummary($Result,[string]$Cleanup) {
    $measured=$Result.status -ceq 'measured' -and $Result.fingerprintState -ceq 'unchanged' -and $Cleanup -ceq 'removed'
    $code=if($Cleanup -cnotin @('removed','not_registered')){'task_cleanup_incomplete'}else{$Result.code}
    $summary=[ordered]@{schemaVersion=1;status=$(if($measured){'measured'}else{'failed'});code=$code;
        executor='SYSTEM';reader='service_token';fingerprintState=$Result.fingerprintState;taskCleanup=$Cleanup;
        diagnosticMeasured=$measured;notMfaActivation=$true;notServiceReadAcceptance=$true;priorAttemptPreserved=$true;diagnostic=$null}
    if ($null -ne $Result.diagnostic) { Assert-DiagnosticOutcome $Result.diagnostic;$summary.diagnostic=$Result.diagnostic }
    return $summary
}
function Assert-DiagnosticWorkerResult($Result,$Plan) {
    Assert-DiagnosticShape $Result @('schemaVersion','status','code','executor','reader','installationId','fingerprintState','beforeDigest','afterDigest','beforeCount','afterCount','diagnostic')
    if ($Result.schemaVersion -ne 1 -or $Result.executor -cne 'SYSTEM' -or $Result.reader -cne 'service_token' -or
        $Result.installationId -cne $Plan.installationId -or $Result.status -cnotin @('failed','measured') -or
        $Result.code -isnot [string] -or $Result.code -cnotmatch '^[a-z][a-z0-9_]{0,99}$' -or
        $Result.fingerprintState -cnotin @('unchanged','changed','unavailable','not_checked')) { Stop-Diagnostic 'worker_result_invalid' }
    if ($Result.status -ceq 'measured') {
        Assert-DiagnosticOutcome $Result.diagnostic
        if ($Result.code -cne $Result.diagnostic.code -or $Result.fingerprintState -cne 'unchanged' -or
            $Result.beforeDigest -cne $Plan.beforeDigest -or $Result.afterDigest -cne $Plan.beforeDigest -or
            $Result.beforeCount -ne $Plan.beforeCount -or $Result.afterCount -ne $Plan.beforeCount) { Stop-Diagnostic 'worker_result_invalid' }
    }
}
function Invoke-DiagnosticCheckOrRun {
    $leases=New-Object Collections.Generic.List[IDisposable];$task=$null;$folder=$null;$xml='';$root='';$createAttempted=$false;$runAttempted=$false;$cleanup='not_registered';$stage='preflight';$hresults=@()
    $result=[ordered]@{status='failed';code='diagnostic_failed';fingerprintState='not_checked';diagnostic=$null}
    try {
        if (-not $PackageRoot) { $PackageRoot=$PSScriptRoot }
        $context=Read-DiagnosticContext $leases $PSCommandPath $ExpectedScriptSha256 $PackageRoot $ExpectedSumsSha256
        $name=$WorkPrefix+[guid]::NewGuid().ToString('N');$plannedRoot=Join-Path $env:ProgramData $name
        Assert-DiagnosticNewRoot $plannedRoot
        $plannedCodeRoot=Join-Path $env:ProgramData ('RackClick-MFA-Code-'+$name.Substring($WorkPrefix.Length))
        $null=Assert-DiagnosticCodePath $plannedCodeRoot
        $plan=[ordered]@{schemaVersion=1;taskName=$name;scriptSha256=$ExpectedScriptSha256;sumsSha256=$ExpectedSumsSha256;
            attemptRoot=$AttemptRoot;oldPlanSha256=$context.oldPlanSha256;packageRoot=$context.package;trialRoot=$context.oldPlan.trialRoot;
            installationId=$context.oldPlan.installationId;service=$context.oldPlan.service;beforeDigest=$context.before.digest;beforeCount=$context.before.count;
            codeRoot=$plannedCodeRoot;readerSid=$context.readerSid;codeManifestSha256=$context.codeManifest.digest;codeCount=$context.codeManifest.count}
        $planText=$plan | ConvertTo-Json -Depth 12 -Compress
        $planHash=Hash-Text $planText;$worker=Join-Path $plannedRoot 'worker.ps1';$planFile=Join-Path $plannedRoot 'plan.json'
        $legacyXml=Get-TaskXml $worker $planFile $planHash $name
        $stage='check_task_validation';$scheduler=New-Object -ComObject Schedule.Service;$scheduler.Connect();$folder=$scheduler.GetFolder('\')
        # The old task is never retired here. Any residue requires separate investigation.
        if ($null -ne (Get-ResumeTask03 $folder $context.oldPlan.taskName)) { Stop-Diagnostic 'old_task_residue' }
        if ($null -ne (Get-ResumeTask03 $folder $name)) { Stop-Diagnostic 'task_name_exists' }
        $definition=New-ResumeDefinition03 $scheduler $legacyXml
        $null=$folder.RegisterTaskDefinition($name,$definition,1,'SYSTEM',$null,5,$TaskDacl)
        if ($Mode -ceq 'Check') { [ordered]@{schemaVersion=1;status='ready';code='';validatedOnly=$true;taskCreated=$false;keysRead=$false;wrapperExecuted=$false;priorAttemptPreserved=$true;notMfaActivation=$true} | ConvertTo-Json -Compress;return }
        $stage='confirmation';Confirm-Diagnostic $plan.installationId
        if ((Get-DiagnosticServiceReaderSid $plan.service) -cne $plan.readerSid) { Stop-Diagnostic 'reader_account_changed' }
        Assert-DiagnosticNewRoot $plannedRoot
        if ($null -ne (Get-ResumeTask03 $folder $context.oldPlan.taskName)) { Stop-Diagnostic 'old_task_residue' }
        if ($null -ne (Get-ResumeTask03 $folder $name)) { Stop-Diagnostic 'task_name_exists' }
        $latest=Get-StoreFingerprint $plan.trialRoot
        if ($latest.digest -cne $plan.beforeDigest -or $latest.count -ne $plan.beforeCount) { Stop-Diagnostic 'store_changed_before_diagnostic' }
        $stage='workspace_create';New-PrivateRoot $plannedRoot;$root=$plannedRoot
        $source=[IO.File]::Open($PSCommandPath,'Open','Read','Read')
        try { $output=New-Object IO.FileStream($worker,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None);try{$source.CopyTo($output)}finally{$output.Dispose()} } finally { $source.Dispose() }
        Write-NewJson $planFile $plan
        if ((Hash-File $planFile) -cne $planHash) { Stop-Diagnostic 'plan_serialization_mismatch' }
        foreach ($file in @($worker,$planFile)) { Add-DiagnosticLease $leases $file }
        Assert-DiagnosticNotStarted $root
        $stage='code_payload_create'
        New-DiagnosticCodePayload $plannedCodeRoot $plan.readerSid $context.codeManifest $leases
        $context.codeRoot=$plannedCodeRoot
        $stage='task_create';$createAttempted=$true
        $task=$folder.RegisterTaskDefinition($name,$definition,2,'SYSTEM',$null,5,$TaskDacl);$xml=[string]$task.Xml
        Write-NewJson (Join-Path $root 'registered-task-private.json') @{xml=$xml}
        if ([int]$task.Definition.Principal.LogonType -ne 5) { Stop-Diagnostic 'task_logon_type_invalid' }
        Assert-ResumeTask03 $xml $legacyXml $false;Assert-RegisteredSettings03 $task;Assert-DiagnosticNotStarted $root
        $task=Get-OwnTask $folder $name $xml;Assert-RegisteredSettings03 $task
        $stage='task_run';$runAttempted=$true;$null=$task.Run($null)
        $stage='worker_wait';$result=Wait-WorkerResult $folder $name $xml (Join-Path $root 'worker-result.json') 150
        Assert-DiagnosticWorkerResult $result $plan;$stage='completed'
    } catch {
        $errorException=$_.Exception
        while ($null -ne $errorException -and $hresults.Count -lt 8) { $hresults+=([int]$errorException.HResult);$errorException=$errorException.InnerException }
        $result=[ordered]@{status='failed';code=(Get-DiagnosticCode $_);fingerprintState='not_checked';diagnostic=$null}
    }
    finally {
        if ($null -ne $task -and $xml) { $cleanup=Remove-OwnTask $folder $name $xml } elseif ($createAttempted) { $cleanup='unconfirmed' }
        foreach ($lease in $leases) { $lease.Dispose() }
    }
    $summary=Get-DiagnosticSummary $result $cleanup
    $summary['stage']=$stage;$summary['hresults']=@($hresults);$summary['taskCreateAttempted']=$createAttempted;$summary['taskRunAttempted']=$runAttempted
    if ($root) { try { Write-NewJson (Join-Path $root 'operator-result-private.json') $result;Write-NewJson (Join-Path $root 'summary-sanitized.json') $summary } catch { $summary.status='failed';$summary.code='report_write_failed';$summary.diagnosticMeasured=$false } }
    $summary | ConvertTo-Json -Depth 8 -Compress
    if ($summary.status -cne 'measured') { exit 1 }
}
function Invoke-DiagnosticSelfTest {
    $id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';Assert-DiagnosticConfirmation ('CONFIRMO DIAGNOSTICO SYSTEM '+$id) $id
    $rejected=$false;try{Assert-DiagnosticConfirmation ('CONFIRMO LECTURA SYSTEM '+$id) $id}catch{$rejected=(Get-DiagnosticCode $_) -ceq 'confirmation_mismatch'}
    if (-not $rejected) { Stop-Diagnostic 'selftest_failed' }
    $raw='{"schemaVersion":1,"status":"measured","code":"exception_captured","exceptionType":"io","hresult":-2146232800,"win32Error":0,"frames":["ReadService"],"outcome":null}' | ConvertFrom-Json
    Assert-DiagnosticOutcome $raw
    $raw.frames=@('private_path');$rejected=$false;try{Assert-DiagnosticOutcome $raw}catch{$rejected=$true}
    if (-not $rejected) { Stop-Diagnostic 'selftest_failed' }
    [ordered]@{schemaVersion=1;status='selftest_passed';checks=4;taskRegistered=$false;serviceAccessed=$false;keysRead=$false;wrapperExecuted=$false} | ConvertTo-Json -Compress
}

try {
    if ($Mode -ceq 'SelfTest') { Invoke-DiagnosticSelfTest }
    else {
        # Before files, COM, SCM, token/privilege helpers, key access or any mutation.
        if ($env:COMPUTERNAME -ieq 'LEAO' -or [Environment]::MachineName -ieq 'LEAO') { Stop-Diagnostic 'host_excluded' }
        if ($Mode -ceq 'Worker') { Invoke-DiagnosticWorker } else { Invoke-DiagnosticCheckOrRun }
    }
    exit 0
} catch {
    [ordered]@{schemaVersion=1;status='rejected';code=(Get-DiagnosticCode $_);taskCreated=$false;notMfaActivation=$true;priorAttemptPreserved=$true} | ConvertTo-Json -Compress
    exit 1
}
