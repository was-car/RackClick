#requires -Version 5.1
[CmdletBinding()]
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules'
$sourceRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\windows\server-install'))
. (Join-Path $sourceRoot 'Collect-RackClickInstallReport.ps1') -FunctionsOnly
if(Test-SetupAdministrator){throw 'Non-elevated test required'}
$checks=New-Object Collections.Generic.List[string]
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('RackClick-Diagnostics-'+[guid]::NewGuid().ToString('N'))
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$acl=New-Object Security.AccessControl.DirectorySecurity
$acl.SetSecurityDescriptorSddlForm(('O:'+$sid+'G:SYD:P(A;OICI;FA;;;'+$sid+')(A;OICI;FA;;;SY)'))
$null=[IO.Directory]::CreateDirectory($fixture,$acl)
$trap='NEVER_EXPORT_THIS_PASSWORD_OR_CONNECTION_STRING'
$sample=@{schemaVersion=1;valid=$false;exitCode=2;code='preparation_child_failed';stage='prepare';failureLine=130;nativeExitCode=2;childCode='preflight_failed';password=$trap;connectionString=$trap;message=$trap}|ConvertTo-Json -Compress
$utf8=New-Object Text.UTF8Encoding($false,$true)
function Write-TestDiagnostic([string]$Name,[byte[]]$Bytes){$path=Join-Path $fixture $Name;[IO.File]::WriteAllBytes($path,$Bytes);return $path}
$normal=Write-TestDiagnostic 'result.json' $utf8.GetBytes($sample)
$observation=Get-SetupJsonDiagnostic $normal @($sid,'S-1-5-18')
if($observation.status-cne'parsed'-or$observation.fields.code-cne'preparation_child_failed'-or$observation.fields.failureLine-ne130){throw 'Valid JSON diagnostic lost'}
if(($observation|ConvertTo-Json -Depth 8)-like('*'+$trap+'*')){throw 'Secret leaked into report'}
$checks.Add('UTF8 JSON retains code/line/native exit; excludes password, connection string and raw message')
foreach($encodingName in @('utf16bom','utf16le','utf16be')){
    $encoding=New-Object Text.UnicodeEncoding(($encodingName-ceq'utf16be'),($encodingName-ceq'utf16bom'),$true)
    $bytes=$encoding.GetBytes($sample)
    if($encodingName-ceq'utf16bom'){$bytes=$encoding.GetPreamble()+$bytes}
    $path=Write-TestDiagnostic ($encodingName+'.json') $bytes
    $observation=Get-SetupJsonDiagnostic $path @($sid,'S-1-5-18')
    if($observation.status-cne'parsed'-or$observation.fields.code-cne'preparation_child_failed'){throw ('Encoding lost: '+$encodingName)}
    $checks.Add('Read '+$encodingName+' without silently omitting file')
}
$missing=Get-SetupJsonDiagnostic (Join-Path $fixture 'missing.json') @($sid,'S-1-5-18')
if($missing.status-cne'missing'){throw 'Missing file not explicitly reported'};$checks.Add('Missing file explicitly reported')
$path=Write-TestDiagnostic 'bad.json' $utf8.GetBytes(('garbage {"code":"preparation_child_output_invalid","password":"'+$trap+'"}'))
$bad=Get-SetupJsonDiagnostic $path @($sid,'S-1-5-18')
if($bad.status-cne'invalid_json'-or$bad.recoveredErrorCode-cne'preparation_child_output_invalid'-or$bad.fields.Count-ne0-or($bad|ConvertTo-Json -Depth 8)-like('*'+$trap+'*')){throw 'Malformed log omitted or raw contents leaked'}
$checks.Add('Malformed log explicitly recorded with error token only; no recovered success claim')
$path=Write-TestDiagnostic 'clixml.log' $utf8.GetBytes(('#< CLIXML'+"`r`n"+'<Objs><Obj S="progress">'+$trap+'</Obj></Objs>'))
$xml=Get-SetupJsonDiagnostic $path @($sid,'S-1-5-18')
if(-not$xml.hasClixml-or$xml.clixmlProgressRecords-ne1-or($xml|ConvertTo-Json -Depth 8)-like('*'+$trap+'*')){throw 'CLIXML summary unsafe'}
$checks.Add('CLIXML progress identified without exporting content')
$path=Write-TestDiagnostic 'oversize.log' (New-Object byte[] 1048577)
if((Get-SetupJsonDiagnostic $path @($sid,'S-1-5-18')).status-cne'too_large'){throw 'Oversized file not reported'};$checks.Add('Oversized file explicitly reported without reading body')
$lock=[IO.File]::Open($normal,'Open','ReadWrite','None')
try{if((Get-SetupJsonDiagnostic $normal @($sid,'S-1-5-18')).status-cne'read_failed'){throw 'Locked file not reported'}}finally{$lock.Dispose()}
$checks.Add('Locked file explicitly reported without swallowing read failure')
$path=Write-TestDiagnostic 'foreign.json' $utf8.GetBytes($sample)
$foreignAcl=Get-Acl -LiteralPath $path
$foreignAcl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule((New-Object Security.Principal.SecurityIdentifier('S-1-5-32-545')),'Read','Allow')))
Set-Acl -LiteralPath $path -AclObject $foreignAcl
if((Get-SetupJsonDiagnostic $path @($sid,'S-1-5-18')).status-cne'acl_rejected'){throw 'Foreign ACL accepted'};$checks.Add('Foreign reader ACL rejected; no permission changes by collector')
foreach($name in @('preparation/exception-private.log','preparation/installation-stdout.log','preparation/installation-stderr.log','preparation/profile-stdout.log','preparation/profile-stderr.log','instance/installation-state.json')){Assert-SetupPrivateDiagnosticName $name}
$checks.Add('Exactly six private diagnostic names accepted')
foreach($name in @('instance/deployment/instance/private/admin-login.json','preparation/../password.txt','C:\Windows\win.ini','preparation/unknown.log','preparation\exception-private.log')){
    $rejected=$false;try{Assert-SetupPrivateDiagnosticName $name}catch{$rejected=$true}
    if(-not$rejected){throw ('Private path escaped whitelist: '+$name)};$checks.Add('Reject private path: '+$name)
}
$privateDenied=$false;try{Read-SetupPrivateDiagnosticBytes 'be79ed26-c5c7-432f-b187-540c755581ba' 'preparation/exception-private.log' $sid}catch{if($_.Exception.Message-cne'setup_elevated_x64_required'){throw};$privateDenied=$true}
if(-not$privateDenied){throw 'Non-elevated native backup read accepted'};$checks.Add('Private diagnostic wrapper rejects non-elevated identity')
$exceptionText='System.InvalidOperationException: '+$trap+"`r`n"+'at f, C:\private\Prepare-RackClickServer.ps1: Zeile 215'+"`r`n"+'at g, C:\private\Install-RackClickOfflineBundle.ps1: line 90'+"`r`n"+'at h, C:\private\Prepare-RackClickServer.ps1: l'+[char]237+'nea 44'+"`r`n"+'at z, C:\private\SecretPassword.ps1: line 9'
$summary=Get-SetupExceptionDiagnostic $utf8.GetBytes($exceptionText)
if($summary.errorType-cne'System.InvalidOperationException'-or$summary.frames.Count-ne3-or($summary|ConvertTo-Json -Depth 8)-like('*'+$trap+'*')-or($summary|ConvertTo-Json -Depth 8)-like'*SecretPassword*'){throw 'Exception summary exported private data or lost localized line'}
$checks.Add('Exception summary retains CLR type and EN/DE/ES known-script lines only')
Initialize-SetupSecurityNative
$native=[RackClickSetupSecurityNative]::ReadPrepared($normal,$sid)
if([Convert]::ToBase64String($native)-cne[Convert]::ToBase64String([IO.File]::ReadAllBytes($normal))){throw 'Native read changed bytes'}
$checks.Add('Existing native reader reads SID/SYSTEM fixture byte-exactly without elevation or ACL changes')
$previous=[RackClickSetupSecurityNative]::Privilege('SeChangeNotifyPrivilege',2)
try{if(($previous-band2)-ne2){throw 'Already enabled process privilege would be restored as disabled'}}finally{$null=[RackClickSetupSecurityNative]::Privilege('SeChangeNotifyPrivilege',2)}
$checks.Add('Already-enabled traversal privilege preserves enabled state; no backup/restore privilege requested')
$result=[ordered]@{schemaVersion=1;valid=$true;passed=$checks.Count;checks=$checks;environment='Windows PowerShell5.1 x64 standard identity; own private fixture only';fixture=$fixture;accountsCreated=0;servicesChanged=0;privilegesEnabled=0;limits=@('No elevated collection or SeBackup read of another identity tested','Target-VM root cause remains unknown until enhanced report is collected')}
if($OutputPath){[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath),($result|ConvertTo-Json -Depth 6),$utf8)}
$result|ConvertTo-Json -Depth 6 -Compress
