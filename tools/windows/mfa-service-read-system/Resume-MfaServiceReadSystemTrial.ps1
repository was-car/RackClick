#requires -Version 5.1
# Resume only the retained failed attempt. The old pinned worker and payload are never overwritten.
[CmdletBinding()]
param(
    [ValidateSet('Check','Run','SelfTest')][string]$Mode='Check',
    [string]$AttemptRoot='C:\ProgramData\RackClick-MFA-SystemRead-8637bb52faee4b2a96992bcf4d7591b8',
    [string]$ExpectedScriptSha256=''
)
$ErrorActionPreference='Stop'
$BasePin='6fa659e61e10571168cd0d8fffd21ca7f729bbacee41021d44eb9e8d62237cb9'
$ResumeStage='preflight'
function Stop-Resume([string]$Code) { throw ('resume_trial:'+$Code) }
function Resume-Code($Record) {
    if ($Record.Exception.Message -match '^(?:resume_trial|system_trial|trial):([a-z0-9_]+)$') { return $Matches[1] }
    return 'resume_failed'
}
function Resume-HResults($Record) {
    $values=New-Object Collections.Generic.List[int];$exception=$Record.Exception
    while ($null -ne $exception -and $values.Count -lt 8) { $values.Add([int]$exception.HResult);$exception=$exception.InnerException }
    return $values.ToArray()
}
function Resume-Hash([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Assert-ResumeRoot([string]$Root) {
    $full=[IO.Path]::GetFullPath($Root)
    if ([IO.Path]::GetDirectoryName($full) -ine [IO.Path]::GetFullPath($env:ProgramData) -or
        [IO.Path]::GetFileName($full) -cnotmatch '^RackClick-MFA-SystemRead-[a-f0-9]{32}$') { Stop-Resume 'attempt_root_invalid' }
    $item=Get-Item -LiteralPath $full -Force
    while ($null -ne $item) { if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { Stop-Resume 'reparse_point' };$item=$item.Parent }
    $acl=Get-Acl -LiteralPath $full
    if (-not $acl.AreAccessRulesProtected -or $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin @('S-1-5-18','S-1-5-32-544')) { Stop-Resume 'workspace_acl_invalid' }
    foreach ($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or $rule.IdentityReference.Value -notin @('S-1-5-18','S-1-5-32-544')) { Stop-Resume 'workspace_acl_invalid' }
    }
}
function Import-ResumeBase([string]$Path) {
    if ((Resume-Hash $Path) -cne $BasePin) { Stop-Resume 'worker_hash_mismatch' }
    $text=[IO.File]::ReadAllText($Path);$tokens=$null;$errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$errors)
    if ($errors.Count) { Stop-Resume 'worker_source_invalid' }
    $nodes=@();foreach ($node in $ast.EndBlock.Statements) { if ($node -is [Management.Automation.Language.TryStatementAst]) { break };$nodes+=$node.Extent.Text }
    . ([scriptblock]::Create(($nodes -join "`n")))
}
function Assert-NotStarted([string]$Root) {
    if ((Test-Path -LiteralPath (Join-Path $Root 'execution.started')) -or (Test-Path -LiteralPath (Join-Path $Root 'worker-result.json'))) { Stop-Resume 'attempt_already_started' }
}
function Assert-ResumePlan($Plan,[string]$Root) {
    $fields=@('schemaVersion','taskName','scriptSha256','zipSha256','sumsSha256','trialRoot','installationId','service','beforeDigest','beforeCount')
    $names=@($Plan.PSObject.Properties.Name)
    if ($names.Count -ne $fields.Count -or @($fields | Where-Object {$_ -cnotin $names}).Count -ne 0 -or
        $Plan.schemaVersion -isnot [int] -or $Plan.schemaVersion -ne 1 -or $Plan.taskName -cne (Split-Path -Leaf $Root) -or
        $Plan.scriptSha256 -cne $BasePin -or $Plan.zipSha256 -cne $ZipPin -or $Plan.sumsSha256 -cne $SumsPin -or
        $Plan.beforeDigest -cnotmatch '^[a-f0-9]{64}$' -or ($Plan.beforeCount -isnot [int] -and $Plan.beforeCount -isnot [long]) -or $Plan.beforeCount -lt 5) { Stop-Resume 'plan_contract_invalid' }
    Assert-ServiceName $Plan.service
    $parsed=[guid]::Empty
    if (-not [guid]::TryParseExact($Plan.installationId,'D',[ref]$parsed) -or
        [IO.Path]::GetFileName([string]$Plan.trialRoot) -cne ('RackClick-MFA-Ensayo-03-'+$parsed.ToString('D')) -or
        [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($Plan.trialRoot)) -ine [IO.Path]::GetFullPath($env:ProgramData)) { Stop-Resume 'plan_context_invalid' }
}
function Assert-ResumeTask([string]$Actual,[string]$LegacyExpected,[bool]$AllowLegacy) {
    [xml]$doc=$Actual;[xml]$expected=$LegacyExpected
    $ns=New-Object Xml.XmlNamespaceManager($doc.NameTable);$ns.AddNamespace('t','http://schemas.microsoft.com/windows/2004/02/mit/task')
    $ens=New-Object Xml.XmlNamespaceManager($expected.NameTable);$ens.AddNamespace('t','http://schemas.microsoft.com/windows/2004/02/mit/task')
    $node=$doc.SelectSingleNode('/t:Task/t:Principals/t:Principal/t:RequiredPrivileges',$ns)
    if ($null -ne $node -and -not $AllowLegacy) { Stop-Resume 'system_privileges_must_be_omitted' }
    if ($null -eq $node) {
        $template=$expected.SelectSingleNode('/t:Task/t:Principals/t:Principal/t:RequiredPrivileges',$ens)
        [void]$doc.SelectSingleNode('/t:Task/t:Principals/t:Principal',$ns).AppendChild($doc.ImportNode($template,$true))
    }
    Assert-TaskContract $doc.OuterXml $LegacyExpected
}
function New-ResumeDefinition($Scheduler,[string]$LegacyXml) {
    [xml]$doc=$LegacyXml;$ns=New-Object Xml.XmlNamespaceManager($doc.NameTable);$ns.AddNamespace('t','http://schemas.microsoft.com/windows/2004/02/mit/task')
    $node=$doc.SelectSingleNode('/t:Task/t:Principals/t:Principal/t:RequiredPrivileges',$ns);[void]$node.ParentNode.RemoveChild($node)
    $definition=$Scheduler.NewTask(0);$definition.XmlText=$doc.OuterXml;$definition.Principal.LogonType=5
    Assert-ResumeTask $definition.XmlText $LegacyXml $false
    return $definition
}
function Get-ResumeTask($Folder,[string]$Name) {
    try { return $Folder.GetTask($Name) } catch {
        $errors=@(Resume-HResults $_);if ($errors -notcontains -2147024894) { throw };return $null
    }
}
function Assert-PriorStopped($Task,[string]$Expected) {
    if ($null -eq $Task) { return }
    Assert-ResumeTask ([string]$Task.Xml) $Expected $true
    if ($Task.State -eq 2 -or $Task.State -eq 4) { Stop-Resume 'prior_task_active' }
    if ($Task.State -notin @(1,3)) { Stop-Resume 'prior_task_not_stopped' }
}
function Invoke-Resume {
    $leases=New-Object Collections.Generic.List[IDisposable];$task=$null;$folder=$null;$xml='';$cleanup='not_registered';$createAttempted=$false;$runAttempted=$false;$priorRemoved=$false
    $result=[ordered]@{status='failed';code='not_started';fingerprintState='not_checked';outcome=$null};$errors=@();$stage='preflight';$reportRoot=''
    try {
        if ($ExpectedScriptSha256 -cnotmatch '^[a-f0-9]{64}$') { Stop-Resume 'script_pin_required' }
        $leases.Add([IO.File]::Open($PSCommandPath,'Open','Read','Read'))
        if ((Resume-Hash $PSCommandPath) -cne $ExpectedScriptSha256) { Stop-Resume 'script_hash_mismatch' }
        $stage='input_integrity';Assert-ResumeRoot $AttemptRoot;$worker=Join-Path $AttemptRoot 'worker.ps1';$planFile=Join-Path $AttemptRoot 'plan.json'
        foreach ($child in @($worker,$planFile)) { if (((Get-Item -LiteralPath $child -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { Stop-Resume 'reparse_point' } }
        $leases.Add([IO.File]::Open($worker,'Open','Read','Read'));$leases.Add([IO.File]::Open($planFile,'Open','Read','Read'))
        . Import-ResumeBase $worker
        Assert-Elevated;Assert-NotStarted $AttemptRoot;Assert-NoReparse $worker;Assert-NoReparse $planFile
        $plan=[IO.File]::ReadAllText($planFile) | ConvertFrom-Json;Assert-ResumePlan $plan $AttemptRoot
        $package=Join-Path $AttemptRoot $ReferenceFolder;$reference=Join-Path $package 'Invoke-MfaServiceReadTrial.ps1'
        . Import-ReferenceFunctions ([IO.File]::ReadAllText($reference))
        $stage='package_integrity';$null=Test-PackageIntegrity $package $SumsPin
        foreach ($file in @(Get-ChildItem -LiteralPath $package -Recurse -File)) { $leases.Add([IO.File]::Open($file.FullName,'Open','Read','Read')) }
        $null=Test-PackageIntegrity $package $SumsPin
        $stage='context_validation';$context=Get-Context $plan.trialRoot $plan.service
        if ($context.installationId -cne $plan.installationId) { Stop-Resume 'plan_context_invalid' }
        $before=Get-StoreFingerprint $plan.trialRoot
        if ($before.digest -cne $plan.beforeDigest -or $before.count -ne $plan.beforeCount) { Stop-Resume 'store_changed_before_resume' }
        $planHash=Resume-Hash $planFile;$legacyXml=Get-TaskXml $worker $planFile $planHash $plan.taskName
        $stage='task_validation';$scheduler=New-Object -ComObject Schedule.Service;$scheduler.Connect();$folder=$scheduler.GetFolder('\')
        $definition=New-ResumeDefinition $scheduler $legacyXml
        $null=$folder.RegisterTaskDefinition($plan.taskName,$definition,1,'SYSTEM',$null,5,$TaskDacl)
        $prior=Get-ResumeTask $folder $plan.taskName;Assert-PriorStopped $prior $legacyXml
        if ($Mode -eq 'Check') { [ordered]@{schemaVersion=1;status='ready';stage=$stage;validatedOnly=$true;taskCreated=$false;keysRead=$false} | ConvertTo-Json -Compress;return }
        $stage='confirmation'
        if ($null -ne $prior) { Write-Host 'Se retirara solo la tarea anterior identificada y parada, conservando su definicion privada.' }
        Confirm-SystemRead $plan.installationId
        $reportRoot=Join-Path $AttemptRoot ('resume-'+[guid]::NewGuid().ToString('N'))
        Assert-NotStarted $AttemptRoot
        if ($null -ne $prior) {
            $stage='prior_task_remove';$current=Get-ResumeTask $folder $plan.taskName;Assert-PriorStopped $current $legacyXml
            if ($null -eq $current -or [string]$current.Xml -cne [string]$prior.Xml) { Stop-Resume 'prior_task_changed' }
            Write-NewJson ($reportRoot+'-prior-task.json') @{xml=[string]$prior.Xml}
            $folder.DeleteTask($plan.taskName,0);$priorRemoved=$true
        }
        $stage='task_create';$createAttempted=$true
        $task=$folder.RegisterTaskDefinition($plan.taskName,$definition,2,'SYSTEM',$null,5,$TaskDacl);$xml=[string]$task.Xml
        Assert-ResumeTask $xml $legacyXml $false;Assert-NotStarted $AttemptRoot
        $task=Get-OwnTask $folder $plan.taskName $xml;$stage='task_run';$runAttempted=$true;$null=$task.Run($null)
        $stage='worker_wait';$result=Wait-WorkerResult $folder $plan.taskName $xml (Join-Path $AttemptRoot 'worker-result.json') 150
        if ($result.schemaVersion -ne 1 -or $result.executor -cne 'SYSTEM' -or $result.reader -cne 'service_token' -or $result.installationId -cne $plan.installationId) { Stop-Resume 'worker_result_invalid' }
        if ($result.status -eq 'passed' -and (-not (Test-StrictOutcome $result.outcome $before.count) -or $result.code -cne '' -or $result.fingerprintState -cne 'unchanged')) { Stop-Resume 'worker_result_invalid' }
        $stage='completed'
    } catch { $errors=@(Resume-HResults $_);$result=[ordered]@{status='failed';code=(Resume-Code $_);fingerprintState='not_checked';outcome=$null} }
    finally {
        if ($null -ne $task -and $xml) { $cleanup=Remove-OwnTask $folder $plan.taskName $xml } elseif ($createAttempted) { $cleanup='unconfirmed' }
        foreach ($lease in $leases) { $lease.Dispose() }
    }
    if (Get-Command Get-Summary -ErrorAction SilentlyContinue) { $summary=Get-Summary $result $cleanup }
    else { $summary=[ordered]@{schemaVersion=1;status='failed';code=$result.code;operationCode=$result.code;taskCleanup=$cleanup;notMfaActivation=$true} }
    $summary['stage']=$stage;$summary['hresults']=@($errors);$summary['taskCreateAttempted']=$createAttempted;$summary['taskRunAttempted']=$runAttempted;$summary['priorTaskRemoved']=$priorRemoved
    if ($reportRoot) { try { Write-NewJson ($reportRoot+'-receipt.json') $result;Write-NewJson ($reportRoot+'-summary.json') $summary } catch { $summary.status='failed';$summary.code='resume_report_failed';$summary['hresults']=@(Resume-HResults $_) } }
    $summary | ConvertTo-Json -Depth 7 -Compress
    if ($summary.status -ne 'passed') { exit 1 }
}

try {
    if ($Mode -eq 'SelfTest') {
        $known=[pscustomobject]@{Exception=(New-Object Exception('resume_trial:fixture_error'))}
        $native=New-Object Runtime.InteropServices.COMException('synthetic',-2147216618)
        $wrapped=[pscustomobject]@{Exception=(New-Object Exception('synthetic',$native))}
        if ((Resume-Code $known) -cne 'fixture_error' -or (Resume-Code $wrapped) -cne 'resume_failed' -or @(Resume-HResults $wrapped) -notcontains -2147216618) { Stop-Resume 'selftest_failed' }
        [ordered]@{status='selftest_passed';checks=3;taskRegistered=$false;keysRead=$false} | ConvertTo-Json -Compress
    }
    else {
        if ($env:COMPUTERNAME -ieq 'LEAO' -or [Environment]::MachineName -ieq 'LEAO') { Stop-Resume 'host_excluded' }
        Invoke-Resume
    }
    exit 0
} catch { [ordered]@{schemaVersion=1;status='rejected';code=(Resume-Code $_);stage=$ResumeStage;hresults=@(Resume-HResults $_);taskCreated=$false;keysRead=$false} | ConvertTo-Json -Compress;exit 1 }
