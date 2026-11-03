#requires -Version 5.1
[CmdletBinding()]
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
if($PSVersionTable.PSEdition-cne'Desktop'-or-not[Environment]::Is64BitProcess){throw 'Native Windows PowerShell5 x64 required'}
$sourceRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\windows\server-install'))
. (Join-Path $sourceRoot 'RackClick.Setup.ps1')
. (Join-Path $sourceRoot 'RackClick.Setup.Process.ps1')
$passed=New-Object Collections.Generic.List[string]
$tokens=$null;$errors=$null
$broker=[Management.Automation.Language.Parser]::ParseFile((Join-Path $sourceRoot 'Install-RackClickServer.ps1'),[ref]$tokens,[ref]$errors)
if(@($errors).Count){throw 'Broker syntax invalid'}
$definition=$broker.Find({param($node) $node-is[Management.Automation.Language.FunctionDefinitionAst]-and$node.Name-ceq'Invoke-SetupServiceChild'},$true)
if($null-eq$definition){throw 'Real broker child function absent'}
. ([scriptblock]::Create($definition.Extent.Text))
$passed.Add('Execute actual broker child function extracted from source AST; no broker entrypoint')
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot ('..\..\..\.local\setup-child-process-fixtures\'+[guid]::NewGuid().ToString('N'))))
$null=[IO.Directory]::CreateDirectory($root)
$ReportDirectory=$root;$script:setupParent=$root;$script:setupCredential=$null
$script:setupAccount=[pscustomobject]@{SID=[pscustomobject]@{Value=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value}}
$script:setupPlan=[pscustomobject]@{id=[guid]::NewGuid().ToString('D')}
$script:setupTestLaunches=New-Object Collections.Generic.List[object]
# Replace only the launch boundary: real redirected child processes, same current identity.
# Credentials, users, LSA, services, SQL and the broker entrypoint are never exercised.
function Start-Process {
    [CmdletBinding()]
    param([string]$FilePath,[Management.Automation.PSCredential]$Credential,[switch]$LoadUserProfile,[string]$WorkingDirectory,[string[]]$ArgumentList,[string]$RedirectStandardOutput,[string]$RedirectStandardError,[switch]$PassThru,[string]$WindowStyle)
    if($null-ne$Credential){throw 'Fixture must never use credentials'}
    $child=Microsoft.PowerShell.Management\Start-Process -FilePath $FilePath -WorkingDirectory $WorkingDirectory -ArgumentList $ArgumentList -RedirectStandardOutput $RedirectStandardOutput -RedirectStandardError $RedirectStandardError -PassThru -WindowStyle Hidden
    $script:setupTestLaunches.Add([pscustomobject]@{pid=$child.Id;file=$FilePath;script=$ArgumentList[-1]})
    return $child
}
function Invoke-ChildFixture([string]$Name,[string]$Body,[string]$ExpectedError='',[int]$ExpectedNative=0,[int]$Timeout=10) {
    $fixture=Join-Path $root ($Name+'.ps1');[IO.File]::WriteAllText($fixture,$Body,(New-Object Text.UTF8Encoding($false)))
    $script:setupResult=[ordered]@{};$caught='';$result=$null
    try{$result=Invoke-SetupServiceChild -Script $fixture -Arguments @() -Label $Name -Timeout $Timeout}catch{$caught=$_.Exception.Message}
    if($caught-cne$ExpectedError){throw ('Unexpected error for '+$Name+': '+$caught)}
    if($ExpectedNative-ge0-and($null-eq$script:setupResult.nativeExitCode-or$script:setupResult.nativeExitCode-ne$ExpectedNative)){throw ('Native exit mismatch for '+$Name)}
    $passed.Add($Name)
    return $result
}
$answer=Invoke-ChildFixture 'native_exit0_json0' "'{`"valid`":true,`"exitCode`":0,`"code`":`"server_prepared`"}';exit 0"
if(-not$answer.valid-or$answer.code-cne'server_prepared'){throw 'Successful child rejected'}
$null=Invoke-ChildFixture 'native_exit2_json2' "'{`"valid`":false,`"exitCode`":2,`"code`":`"preparation_test_failure`",`"errorType`":`"System.UnauthorizedAccessException`",`"failureLine`":42}';exit 2" 'setup_child_failed_preserved' 2
if($script:setupResult.childCode-cne'preparation_test_failure'-or$script:setupResult.childErrorType-cne'System.UnauthorizedAccessException'-or$script:setupResult.childFailureLine-ne42){throw 'Child diagnostics not preserved before wrapper failure'}
$passed.Add('Failed child retains bounded code, CLR type and source line')
$null=Invoke-ChildFixture 'native_exit259_after_signalled' "'{`"valid`":false,`"exitCode`":259}';exit 259" 'setup_child_failed_preserved' 259
$null=Invoke-ChildFixture 'native_exit2_json0_mismatch' "'{`"valid`":true,`"exitCode`":0,`"code`":`"server_prepared`"}';exit 2" 'setup_child_exit_code_mismatch' 2
$null=Invoke-ChildFixture 'native_exit0_json2_mismatch' "'{`"valid`":false,`"exitCode`":2}';exit 0" 'setup_child_exit_code_mismatch' 0
$null=Invoke-ChildFixture 'json_false_exit0' "'{`"valid`":false,`"exitCode`":0}';exit 0" 'setup_child_failed_preserved' 0
$null=Invoke-ChildFixture 'malformed_json' "'not-json';exit 0" 'setup_child_result_invalid' 0
$null=Invoke-ChildFixture 'empty_stdout' 'exit 0' 'setup_child_result_missing' 0
$null=Invoke-ChildFixture 'string_boolean_rejected' "'{`"valid`":`"true`",`"exitCode`":0}';exit 0" 'setup_child_result_invalid' 0
$null=Invoke-ChildFixture 'string_exit_rejected' "'{`"valid`":true,`"exitCode`":`"0`"}';exit 0" 'setup_child_result_invalid' 0
$null=Invoke-ChildFixture 'array_rejected' "'[{`"valid`":true,`"exitCode`":0},{`"valid`":true,`"exitCode`":0}]';exit 0" 'setup_child_result_invalid' 0
$null=Invoke-ChildFixture 'single_element_array_rejected' "'[{`"valid`":true,`"exitCode`":0}]';exit 0" 'setup_child_result_invalid' 0
$null=Invoke-ChildFixture 'oversized_stdout' "[Console]::Out.Write(('x'*1048577));exit 0" 'setup_child_result_too_large' 0
$null=Invoke-ChildFixture 'unsafe_metadata_excluded' "'{`"valid`":false,`"exitCode`":2,`"code`":`"secret value`",`"errorType`":`"raw exception text`",`"failureLine`":`"password`"}';exit 2" 'setup_child_failed_preserved' 2
foreach($key in @('childCode','childErrorType','childFailureLine')){if($script:setupResult.Contains($key)){throw 'Unsafe child metadata retained'}}
$passed.Add('Untrusted free-text diagnostic fields excluded')
# A short-lived own fixture outlives timeout. The broker must neither kill nor retry it.
$marker=Join-Path $root 'timeout-completed.txt'
$body="Start-Sleep -Seconds 2;[IO.File]::WriteAllText('"+$marker.Replace("'","''")+"','completed');'{`"valid`":true,`"exitCode`":0}';exit 0"
$null=Invoke-ChildFixture 'timeout_indeterminate' $body 'setup_child_still_running_do_not_retry' -1 0
if($script:setupResult.processState-cne'indeterminate_child_may_be_running'-or$script:setupResult.retryAllowed-ne$false-or$script:setupResult.childPid-ne$script:setupTestLaunches[-1].pid){throw 'Timeout not retained as indeterminate'}
$deadline=[DateTime]::UtcNow.AddSeconds(10)
while(-not[IO.File]::Exists($marker)-and[DateTime]::UtcNow-lt$deadline){Start-Sleep -Milliseconds 100}
if(-not[IO.File]::Exists($marker)){throw 'Timed-out fixture did not finish independently'}
$ownChild=$null
try{$ownChild=[Diagnostics.Process]::GetProcessById($script:setupTestLaunches[-1].pid)}catch [ArgumentException]{}
if($null-ne$ownChild){try{if(-not$ownChild.WaitForExit(10000)){throw 'Own timed-out fixture did not exit independently'}}finally{$ownChild.Dispose()}}
$passed.Add('Timed-out own child continues and finishes independently without Stop-Process or retry')
$missingRejected=$false
try{$null=Read-SetupChildResult (Join-Path $root 'never-created.json')}catch{if($_.Exception.Message-cne'setup_child_result_missing'){throw};$missingRejected=$true}
if(-not$missingRejected){throw 'Missing output file accepted'};$passed.Add('Missing output file rejected')
$result=[ordered]@{schemaVersion=1;valid=$true;passed=$passed.Count;checks=$passed;environment='Native Windows PowerShell5.1 x64; actual redirected child processes under current identity';fixtureRoot=$root;processesLaunched=$script:setupTestLaunches.Count;accountsCreated=0;servicesCreated=0;processAccessMask='0x101000 QUERY_LIMITED_INFORMATION|SYNCHRONIZE';limits=@('No elevated or cross-account child launch; no user, LSA, SCM, PostgreSQL or VM mutation.','The real Windows Server administrator-to-service-account installation still requires confirmation on that server.')}
if($OutputPath){[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath),($result|ConvertTo-Json -Depth 5),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 5 -Compress
