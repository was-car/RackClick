#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\..\windows\server-install\Collect-RackClickInstallReport.ps1') -FunctionsOnly
if(Test-SetupAdministrator){throw 'Standard identity required'}
$checks=New-Object Collections.Generic.List[string]
$root=Join-Path ([IO.Path]::GetTempPath()) ('RackClick-Attempts-'+[guid]::NewGuid().ToString('N'))
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$acl=New-Object Security.AccessControl.DirectorySecurity
$acl.SetSecurityDescriptorSddlForm(('O:'+$sid+'G:SYD:P(A;OICI;FA;;;'+$sid+')(A;OICI;FA;;;SY)'))
$null=[IO.Directory]::CreateDirectory($root,$acl)
$oldId=[guid]::NewGuid().ToString('D');$newId=[guid]::NewGuid().ToString('D')
$utf8=New-Object Text.UTF8Encoding($false)
foreach($case in @(@{id=$oldId;code='setup_child_failed_preserved';stage='prepare';percent=25;age=2},@{id=$newId;code='setup_payload_unlisted_file';stage='verify';percent=2;age=1})){
    $folder=Join-Path $root $case.id;$null=[IO.Directory]::CreateDirectory($folder)
    [IO.File]::WriteAllText((Join-Path $folder 'result.json'),(@{valid=$false;exitCode=1;code=$case.code;stage=$case.stage;installationPercent=$case.percent;password='DO_NOT_EXPORT_TEST_PASSWORD'}|ConvertTo-Json -Compress),$utf8)
    if($case.id-ceq$oldId){[IO.File]::WriteAllText((Join-Path $folder 'prepare.stdout.log'),' {"valid":false,"exitCode":2,"code":"preparation_test_error"}',$utf8)}
    [IO.Directory]::SetLastWriteTimeUtc($folder,[DateTime]::UtcNow.AddMinutes(-$case.age))
}
$selected=@(Get-SetupDiagnosticFolders $root)
if($selected.Count-ne2-or$selected[0].Name-cne$newId-or$selected[1].Name-cne$oldId){throw 'Recent attempt selection lost older preparation'}
$checks.Add('Select latest verification and preceding preparation, separated by UUID')
$records=@(foreach($folder in $selected){Get-SetupAttemptDiagnostic $folder.FullName @($sid,'S-1-5-18')})
if($records[0].reports['result.json'].code-cne'setup_payload_unlisted_file'-or$records[1].reports['result.json'].code-cne'setup_child_failed_preserved'-or$records[1].reports['prepare.stdout.log'].code-cne'preparation_test_error'){throw 'Diagnostic attempts mixed or omitted'}
$checks.Add('Keep distinct results and original preparer code in their own attempt')
if($records[0].observations['prepare.stdout.log'].status-cne'missing'){throw 'Latest attempt pretends preparation ran'}
$checks.Add('Explicitly distinguish missing preparation in early verification failure')
if(($records|ConvertTo-Json -Depth 10)-like'*DO_NOT_EXPORT_TEST_PASSWORD*'){throw 'Private field exported'}
$checks.Add('Multiple attempt collection still filters secret fields')
$target=@(Get-SetupDiagnosticFolders $root $oldId)
if($target.Count-ne1-or$target[0].Name-cne$oldId){throw 'Explicit original attempt not selected'}
$checks.Add('Explicit UUID selector preserves targeted original attempt')
foreach($bad in @('..\other','not-a-guid',$oldId.ToUpperInvariant())){
    $rejected=$false;try{$null=Get-SetupDiagnosticFolders $root $bad}catch{$rejected=$true}
    if(-not$rejected){throw 'Invalid explicit selector accepted'}
}
$checks.Add('Reject traversal, malformed and noncanonical explicit selectors')
for($i=0;$i-lt12;$i++){$folder=Join-Path $root ([guid]::NewGuid().ToString('D'));$null=[IO.Directory]::CreateDirectory($folder)}
$null=[IO.Directory]::CreateDirectory((Join-Path $root ('-'*36)))
$selected=@(Get-SetupDiagnosticFolders $root)
if($selected.Count-ne10){throw 'Recent attempts not bounded to10'}
foreach($folder in $selected){$id=[guid]::Empty;if(-not[guid]::TryParseExact($folder.Name,'D',[ref]$id)){throw 'Malformed folder selected'}}
$checks.Add('Collection bounded to ten canonical attempt directories')
$result=@{valid=$true;passed=$checks.Count;checks=$checks;fixture=$root;environment='Windows PowerShell5.1 x64, standard identity, isolated own fixtures';privilegedOperationsExecuted=0;installationsExecuted=0}
if($OutputPath){[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath),($result|ConvertTo-Json -Depth 5),$utf8)}
$result|ConvertTo-Json -Depth 5 -Compress
