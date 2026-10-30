#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot '..\..\windows\server-install\Show-RackClickRc9RestoredAccess.ps1') -FunctionsOnly
$checks=New-Object 'Collections.Generic.List[string]'
function Assert-Rc9Access([bool]$Condition,[string]$Name){if(-not$Condition){throw ('Test failed: '+$Name)};$checks.Add($Name)}
function Assert-Rc9Reject([scriptblock]$Action,[string]$Name){$failed=$false;try{&$Action|Out-Null}catch{$failed=$true};Assert-Rc9Access $failed $Name}
$id='11111111-2222-4333-8444-555555555555';$instance='C:\ProgramData\RackClick\Instances\'+$id+'\instance';$code='C:\Program Files\RackClick\'+$id
$command='"'+$instance+'\content\dependencies\dotnet\dotnet.exe" "'+$code+'\service\RackClick.WindowsService.dll" --config "'+$instance+'\service-config.json"'
$binding=Get-Rc9RestoredBinding $command
Assert-Rc9Access ($binding.installationId-ceq$id-and$binding.managementPath-ceq('C:\ProgramData\RackClick\Instances\'+$id+'\management')) 'Canonical service command binds one installation and management vault'
Assert-Rc9Access ($binding.serviceName-ceq'RackClick-Recovery-cb52d279'-and$binding.publicOrigin-ceq'https://192.168.250.78:5444') 'Viewer targets only the named RC9 service and fixed HTTPS origin'
foreach($changed in @(($command+' --other'),$command.Replace('--config','--other'),$command.Replace('service-config.json','other.json'),$command.Replace($code,'C:\outside'),$command.Replace($id,'606b8c29-41de-4dc0-b63d-ade836000d9e'),$command.Replace($id,'AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE'),$command.Trim('"'))){Assert-Rc9Reject {Get-Rc9RestoredBinding $changed} 'Foreign, unquoted or extended service command is rejected'}
$sid='S-1-5-21-111-222-333-1001'
$receipt=@{schemaVersion=1;installationId=$id;serviceName=$binding.serviceName;codeRoot=$binding.codeRoot;instancePath=$binding.instancePath;managementPath=$binding.managementPath;publicOrigin=$binding.publicOrigin;backupTaskName=$binding.backupTaskName;accountName='RackClickSvcRc9';serviceSid=$sid;manifestSha256=('a'*64)}
Assert-Rc9RestoredReceipt $receipt $binding;Assert-Rc9Access $true 'Receipt matches the service, canonical paths, SID shape, account, origin and task ID'
foreach($case in @(@{key='installationId';value='66666666-7777-4888-8999-000000000000'},@{key='serviceName';value='RackClick'},@{key='codeRoot';value='C:\outside'},@{key='instancePath';value='C:\outside'},@{key='managementPath';value='C:\outside'},@{key='publicOrigin';value='https://192.168.250.78:5443'},@{key='publicOrigin';value='https://192.168.250.78:5444/?private'},@{key='backupTaskName';value='OtherTask'},@{key='accountName';value='OtherSam'},@{key='serviceSid';value='S-1-5-18'},@{key='serviceSid';value='S-1-5-21-111-222-333-500'},@{key='manifestSha256';value='invalid'})){
 $copy=@{};foreach($key in $receipt.Keys){$copy[$key]=$receipt[$key]};$copy[$case.key]=$case.value;Assert-Rc9Reject {Assert-Rc9RestoredReceipt $copy $binding} ('Receipt rejects changed '+$case.key)
}
$copy=@{};foreach($key in $receipt.Keys){$copy[$key]=$receipt[$key]};$copy.publicOrigin=@($binding.publicOrigin);Assert-Rc9Reject {Assert-Rc9RestoredReceipt $copy $binding} 'Array instead of receipt string is rejected';$copy.publicOrigin=$binding.publicOrigin;$copy.schemaVersion='1';Assert-Rc9Reject {Assert-Rc9RestoredReceipt $copy $binding} 'String instead of numeric receipt schema is rejected'
foreach($observed in @($sid,'.\RackClickSvcRc9','HOST\rackclicksvcrc9')){Assert-Rc9Access (Test-Rc9RestoredPrincipal $observed $sid 'HOST' 'RackClickSvcRc9') 'SID or explicitly qualified local SAM account matches without translation'}
foreach($observed in @('DOMAIN\RackClickSvcRc9','RackClickSvcRc9@example.invalid','RackClickSvcRc9','.\OtherSam','HOST\OtherSam','S-1-5-21-111-222-333-1002')){Assert-Rc9Access (-not(Test-Rc9RestoredPrincipal $observed $sid 'HOST' 'RackClickSvcRc9')) 'Unexpected principal is rejected without domain lookup'}
Assert-Rc9Access (-not(Test-Rc9RestoredPrincipal $sid $sid 'HOST' 'OtherSam')) 'Correct SID still requires the dedicated restored SAM name'
Assert-Rc9Access (-not(Test-Rc9RestoredPrincipal '.\RackClickSvcRc9' $sid 'HOST' '')) 'Unavailable local SAM cannot validate the alias'
$fictitious=[Text.Encoding]::UTF8.GetBytes('{"username":"fixture-user","password":"fixture-only-never-real"}');$login=Read-Rc9RestoredLogin $fictitious
Assert-Rc9Access ($login.username-ceq'fixture-user'-and$login.password-ceq'fixture-only-never-real') 'Existing two-field login format is read only into private memory'
foreach($text in @('{"username":"fixture","password":""}','{"username":"fixture","password":"x","extra":"private_marker"}','{"username":3,"password":"private_marker"}','{"username":"fixture","password":"private_marker\n"}','[{"username":"fixture","password":"private_marker"}]','malformed_private_marker')){
 $caught=$null;try{$null=Read-Rc9RestoredLogin ([Text.Encoding]::UTF8.GetBytes($text))}catch{$caught=$_.Exception};Assert-Rc9Access ($null-ne$caught-and$caught.Message-ceq'rc9_access_login_invalid'-and$null-eq$caught.InnerException-and$caught.ToString()-notmatch'private_marker') 'Invalid login returns only a constant error without private contents'
}
Assert-Rc9Reject {Read-Rc9RestoredLogin (New-Object byte[] 65537)} 'Oversized login is rejected'
$login.password=$null;$login.username=$null;[Array]::Clear($fictitious,0,$fictitious.Length)

# Compile only the read-only reader. ACL fixtures remain in memory; no private files or native APIs are called.
Initialize-Rc9RestoredReader
Assert-Rc9Access ([RackClickRc9PrivateReader]::IsPrivateSddl('O:BAG:SYD:AI(A;ID;FA;;;BA)(A;ID;FA;;;SY)')) 'Inherited management ACL restricted to administrators and SYSTEM is valid'
Assert-Rc9Access ([RackClickRc9PrivateReader]::IsPrivateSddl('O:SYG:SYD:P(A;;FA;;;SY)(A;;FA;;;BA)')) 'Protected private ACL owned by SYSTEM is valid'
foreach($sddl in @('O:BAG:SYD:NO_ACCESS_CONTROL','O:BAG:SYD:P(A;;FA;;;WD)(A;;FA;;;SY)','O:BAG:SYD:P(D;;FA;;;BA)(A;;FA;;;SY)','O:BAG:SYD:P(A;;FA;;;BA)(A;;FR;;;BA)','O:S-1-5-21-111-222-333-1001G:SYD:P(A;;FA;;;BA)(A;;FA;;;SY)','invalid')){Assert-Rc9Access (-not[RackClickRc9PrivateReader]::IsPrivateSddl($sddl)) 'Unsafe owner, broad access, deny, missing principal or malformed ACL is rejected'}
$source=[IO.File]::ReadAllText((Join-Path $PSScriptRoot '..\..\windows\server-install\Show-RackClickRc9RestoredAccess.ps1'))
Assert-Rc9Access ($source-match'UseSystemPasswordChar=\$true'-and$source-match'ShortcutsEnabled=\$false'-and$source-match'ContextMenu=New-Object Windows.Forms.ContextMenu') 'Private fields default to masking and disabled copy shortcuts/context menu'
Assert-Rc9Access ($source-notmatch'(?i)Clipboard|Set-Acl|SetService|ProtectedData|\.Translate\(|notepad|GetNetworkCredential') 'Viewer contains no copy API, ACL setter, identity translation, DPAPI or editor dependency'
$result=[ordered]@{schemaVersion=1;valid=$true;passed=$checks.Count;checks=@($checks);environment='Windows PowerShell 5.1; fictitious bindings/login and in-memory ACL descriptors';mainExecuted=$false;windowOpened=$false;privateFilesRead=0;serviceQueries=0;samQueries=0;privilegesEnabled=0;credentialsWindowsRead=0;authenticationAttempts=0;databaseOperations=0}
if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Depth 5),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 5 -Compress
