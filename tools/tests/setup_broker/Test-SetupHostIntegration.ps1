#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
$ops=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\windows\server-install'))
. (Join-Path $ops 'RackClick.Setup.ps1');. (Join-Path $ops 'RackClick.Setup.Security.ps1');. (Join-Path $ops 'RackClick.Setup.Reset.ps1');. (Join-Path $ops 'RackClick.Setup.Namespace.ps1')
. (Join-Path $ops 'Show-RackClickInstaller.ps1') -FunctionsOnly
. (Join-Path $ops 'RackClick.Setup.Diagnostics.ps1')
$checks=New-Object Collections.Generic.List[string]
function Check($Value,[string]$Name){if(-not$Value){throw $Name};$checks.Add($Name)}
function RejectCode([scriptblock]$Action,[string]$Code,[string]$Name){$hit=$false;try{&$Action|Out-Null}catch{if($_.Exception.Message-cne$Code){throw};$hit=$true};Check $hit $Name}
$script:accountQueries=0;$script:serviceQueries=0;$script:writeCalls=0;$script:dc=$true
function Get-CimInstance {param($ClassName,$ErrorAction) switch($ClassName){Win32_OperatingSystem{[pscustomobject]@{ProductType=2}} Win32_ComputerSystem{[pscustomobject]@{DomainRole=5;PartOfDomain=$true}} default{$script:serviceQueries++;throw 'Unexpected inventory query on DC'}}}
function Get-LocalUser {$script:accountQueries++;throw 'Accounts must not be queried on DC'}
function Write-SetupJson {$script:writeCalls++;throw 'Namespace journal must not be written on DC'}
function Assert-SetupAdministrator {}
RejectCode {Get-SetupNamespacePlan} 'setup_domain_controller_not_supported' 'DC rejected before namespace inventory, even without an existing plan'
RejectCode {Invoke-SetupNamespacePlan ([pscustomobject]@{id=[guid]::NewGuid().ToString('D')}) 'C:\must-not-be-accessed' -Confirm:$false} 'setup_domain_controller_not_supported' 'DC rejected by apply API before inspecting journal or moving directories'
Check ($script:accountQueries-eq0-and$script:serviceQueries-eq0-and$script:writeCalls-eq0) 'Blocked namespace calls perform no account inventory, service inventory or journal write'
function Parse([string]$Path){$t=$null;$e=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($Path,[ref]$t,[ref]$e);if(@($e).Count){throw ('Syntax error: '+$Path)};return $ast}
$broker=Parse (Join-Path $ops 'Install-RackClickServer.ps1')
function Position($Ast,[string]$Command){$matches=@($Ast.FindAll({param($n) $n-is[Management.Automation.Language.CommandAst]-and$n.GetCommandName()-ceq$Command},$true));if($matches.Count-ne1){throw ('Ambiguous production call: '+$Command)};return $matches[0].Extent.StartOffset}
$rolePosition=Position $broker 'Get-SetupHostCompatibility'
Check ($rolePosition-lt(Position $broker 'Install-SetupCrt')) 'Actual broker checks host role before CRT installation'
Check ($rolePosition-lt(Position $broker 'New-LocalUser')) 'Actual broker checks host role before account creation'
Check ($rolePosition-lt(Position $broker 'Set-SetupPublicCodeDirectoryACL')) 'Actual broker checks host role before filesystem ACL changes'
$launcher=[IO.Path]::GetFullPath((Join-Path $ops '..\server-reset\Start-RackClickCleanInstall.ps1'))
$launchAst=Parse $launcher
Check ((Position $launchAst 'Get-SetupHostCompatibility')-lt(Position $launchAst 'Get-SetupNamespacePlan')) 'Actual bootstrap checks host role before old namespace inventory'
Check ((Position $launchAst 'Get-SetupHostCompatibility')-lt(Position $launchAst 'Invoke-SetupNamespacePlan')) 'Actual bootstrap checks host role before any archival'
$text=[IO.File]::ReadAllText($launcher)
Check ($text.Contains("if(-not`$hostCheck.valid){throw ([string]`$hostCheck.code)}")) 'Bootstrap rejects negative role verdict before continuing'
$message=Format-SetupUiFailure ([pscustomobject]@{code='setup_domain_controller_not_supported'}) 'C:\private-fixture'
Check ($message-like'*controlador de dominio*'-and$message-like'*otra VM*') 'Installer UI explains unsupported domain-controller role rather than generic account failure'
$safe=Select-SetupDiagnosticFields ([pscustomobject]@{valid=$false;code='setup_domain_controller_not_supported';productType=2;domainRole=5;partOfDomain=$true;domainName='SECRET_SENTINEL';password='SECRET_SENTINEL'})
Check ($safe.productType-eq2-and$safe.domainRole-eq5-and$safe.partOfDomain-and($safe|ConvertTo-Json)-notlike'*SECRET_SENTINEL*') 'Diagnostic host fields retain numeric role and domain membership without domain names or secrets'
$invalid=Select-SetupDiagnosticFields ([pscustomobject]@{productType='SECRET_SENTINEL';domainRole=99;partOfDomain='true';hostProductType=0;hostDomainRole='5';hostPartOfDomain=1})
Check ($invalid.Count-eq0) 'Malformed host fields cannot export arbitrary strings or out-of-range roles'
$result=[ordered]@{valid=$true;passed=$checks.Count;checks=@($checks.ToArray());environment='Windows PowerShell5.1 x64, production functions with DC CIM mocked; source AST ordering';accountsQueried=$script:accountQueries;servicesQueried=$script:serviceQueries;namespaceJournalWrites=$script:writeCalls;osMutations=0;limits=@('Broker and bootstrap ordering checked from actual source, not an elevated installation','Actual namespace GetPlan and Invoke rejected DC fixture before OS-account/service/journal operations')}
if($OutputPath){[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath),($result|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 6 -Compress
