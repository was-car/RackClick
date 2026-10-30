#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot '..\..\windows\server-install\Repair-RackClickNetworkTransaction.ps1') -FunctionsOnly
$checks=New-Object 'Collections.Generic.List[string]'
function Assert-TaskBinding([bool]$Condition,[string]$Name){if(-not$Condition){throw ('Test failed: '+$Name)};$checks.Add($Name)}
$ctx=@{receipt=@{serviceSid='S-1-5-21-111-222-333-1001';backupTaskName='FixtureOnly';backupExecutable='C:\fixture.exe';backupArguments='fixture arguments'};localMachine='HOST';localName='Svc'}
$xml='<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"><Principals><Principal id="Author"><UserId>Svc</UserId><LogonType>Password</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals><Settings><Enabled>true</Enabled><ExecutionTimeLimit>PT30M</ExecutionTimeLimit></Settings><Actions Context="Author"><Exec><Command>C:\fixture.exe</Command><Arguments>fixture arguments</Arguments></Exec></Actions></Task>'
$omitted=$xml.Replace('<RunLevel>LeastPrivilege</RunLevel>','')
$value=Get-RcRepairOriginalTaskBinding $ctx (ConvertTo-RcRepairTaskDocument $xml)
Assert-TaskBinding ($value.valid-and$value.runLevelRepresentation-ceq'least_privilege') 'Complete original XML verifies executable, arguments, identity, Password and LeastPrivilege together'
$value=Get-RcRepairOriginalTaskBinding $ctx (ConvertTo-RcRepairTaskDocument $omitted)
Assert-TaskBinding ($value.valid-and$value.runLevelRepresentation-ceq'omitted_default') 'Original XML accepts only the documented omitted RunLevel default'
foreach($change in @(
 @{name='empty RunLevel';xml=$xml.Replace('>LeastPrivilege<','><')},
 @{name='elevated RunLevel';xml=$xml.Replace('LeastPrivilege','HighestAvailable')},
 @{name='duplicate RunLevel';xml=$xml.Replace('</RunLevel>','</RunLevel><RunLevel>LeastPrivilege</RunLevel>')},
 @{name='unknown RunLevel';xml=$xml.Replace('LeastPrivilege','invalid')},
 @{name='missing Password';xml=$omitted.Replace('<LogonType>Password</LogonType>','')},
 @{name='S4U principal';xml=$omitted.Replace('Password','S4U')},
 @{name='foreign principal';xml=$omitted.Replace('>Svc<','>DOMAIN\Svc<')},
 @{name='foreign command';xml=$omitted.Replace('C:\fixture.exe','C:\other.exe')},
 @{name='foreign arguments';xml=$omitted.Replace('fixture arguments','different arguments')},
 @{name='additional action';xml=$omitted.Replace('</Actions>','<Exec><Command>C:\extra.exe</Command></Exec></Actions>')},
 @{name='group principal';xml=$omitted.Replace('</UserId>','</UserId><GroupId>S-1-5-32-544</GroupId>')}
)){
 $value=Get-RcRepairOriginalTaskBinding $ctx (ConvertTo-RcRepairTaskDocument $change.xml)
 Assert-TaskBinding (-not$value.valid) ('Reject original '+$change.name+' despite omitted RunLevel support')
}
function New-TaskFixture {return @{State='Disabled';Principal=@{UserId='Svc';LogonType='Password';RunLevel='Limited'};Actions=@(@{Execute='C:\fixture.exe';Arguments='fixture arguments'});Settings=@{Enabled=$false}}}
$task=New-TaskFixture
Assert-TaskBinding ((Get-RcRepairCurrentTaskBinding $ctx $task).valid) 'Current CIM task independently confirms Limited, Password, local SID and action'
foreach($fault in @('Running','Queued','Unknown','Highest','S4U','ForeignUser','ForeignExe','ForeignArgs','ExtraAction')){
 $task=New-TaskFixture
 switch($fault){Running{$task.State='Running'}Queued{$task.State='Queued'}Unknown{$task.State='Unknown'}Highest{$task.Principal.RunLevel='Highest'}S4U{$task.Principal.LogonType='S4U'}ForeignUser{$task.Principal.UserId='DOMAIN\Svc'}ForeignExe{$task.Actions[0].Execute='C:\other.exe'}ForeignArgs{$task.Actions[0].Arguments='other'}ExtraAction{$task.Actions+=@{Execute='C:\other.exe';Arguments='other'}}}
 Assert-TaskBinding (-not(Get-RcRepairCurrentTaskBinding $ctx $task).valid) ('Reject current CIM '+$fault+' independently of XML defaults')
}
$defaultEnabled=$omitted.Replace('<Enabled>true</Enabled>','')
$disabled=$xml.Replace('<Enabled>true</Enabled>','<Enabled>false</Enabled>')
$compare=Compare-RcRecoveryTaskXml $disabled $defaultEnabled
Assert-TaskBinding ($compare.matchesExceptEnabled-and-not$compare.exact-and-not$compare.currentEnabled-and$compare.backupEnabled) 'Omitted Enabled means true; explicit disabled task differs only by Enabled and equivalent RunLevel default'
$compare=Compare-RcRecoveryTaskXml $xml $defaultEnabled
Assert-TaskBinding ($compare.exact-and$compare.currentEnabled-and$compare.backupEnabled) 'Explicit true and omitted true have the same verified task meaning'
Assert-TaskBinding (-not(Compare-RcRecoveryTaskXml $disabled.Replace('PT30M','PT31M') $defaultEnabled).matchesExceptEnabled) 'Other settings are still compared exactly'
Assert-TaskBinding (-not(Compare-RcRecoveryTaskXml $disabled.Replace('LeastPrivilege','HighestAvailable') $defaultEnabled).matchesExceptEnabled) 'RunLevel elevation is never normalized away'
foreach($badXml in @($xml.Replace('<Enabled>true</Enabled>','<Enabled/>'),$xml.Replace('<Enabled>true</Enabled>','<Enabled>true</Enabled><Enabled>false</Enabled>'))){$failed=$false;try{$null=Compare-RcRecoveryTaskXml $badXml $defaultEnabled}catch{$failed=$true};Assert-TaskBinding $failed 'Malformed or duplicate Enabled remains rejected'}

# Exercise the production current-task reader and its sanitized failure report.
$script:taskFixture=New-TaskFixture;$script:taskXmlFixture=$disabled
function Get-ScheduledTask {param($TaskName,$TaskPath);return $script:taskFixture}
function Export-ScheduledTask {param($TaskName,$TaskPath);return $script:taskXmlFixture}
$ctx.originalTaskXml=$defaultEnabled
$compare=Read-RcRepairTaskState $ctx
Assert-TaskBinding ($compare.matchesExceptEnabled-and$ctx.taskValidation.current.valid-and$ctx.taskValidation.enabledMatchesXml) 'Full current-task reader accepts documented defaults after independent CIM validation'
$script:taskFixture.Principal.RunLevel='Highest';$failed=$false;try{$null=Read-RcRepairTaskState $ctx}catch{$failed=$true}
Assert-TaskBinding ($failed-and-not$ctx.taskValidation.current.limitedRunLevel-and-not$ctx.taskValidation.current.valid) 'Full reader reports the exact failed boolean before rejecting an elevated current task'
Assert-TaskBinding (-not(($ctx.taskValidation|ConvertTo-Json -Depth 8)-match'fixture arguments|DOMAIN|C:\\fixture|S-1-5')) 'Task validation report contains no raw command, account or SID'

# COM creates a real Windows task definition only in memory. No task is
# registered, no account is created, and no password is supplied.
$scheduler=$null;$definition=$null;$action=$null;$emptyDefinition=$null
try{
 $scheduler=New-Object -ComObject Schedule.Service;$scheduler.Connect();$definition=$scheduler.NewTask(0)
 $definition.Principal.UserId='Svc';$definition.Principal.LogonType=1
 $action=$definition.Actions.Create(0);$action.Path='C:\fixture.exe';$action.Arguments='fixture arguments'
 $doc=ConvertTo-RcRepairTaskDocument $definition.XmlText
 $binding=Get-RcRepairOriginalTaskBinding $ctx $doc
 Assert-TaskBinding ($definition.Principal.RunLevel-eq0-and$binding.valid) 'Actual configured Windows COM definition passes the full production XML binding validator'
 $emptyDefinition=$scheduler.NewTask(0);$defaultDoc=ConvertTo-RcRepairTaskDocument $emptyDefinition.XmlText;$levels=Get-RcRepairTaskNodes $defaultDoc '/t:Task/t:Principals/t:Principal/t:RunLevel'
 Assert-TaskBinding ($levels.Count-eq0-and$emptyDefinition.Principal.RunLevel-eq0) 'Actual untouched Windows COM default omits RunLevel while its property remains LUA0'
}finally{foreach($item in @($action,$definition,$emptyDefinition,$scheduler)){if($null-ne$item){$null=[Runtime.InteropServices.Marshal]::ReleaseComObject($item)}}}
$result=[ordered]@{schemaVersion=1;valid=$true;passed=$checks.Count;checks=@($checks);environment='Windows PowerShell 5.1; full task binding validators/read callbacks and actual unregistered COM definitions';comDefinitionsCreated=2;tasksRegistered=0;taskMutations=0;privilegedOperationsExecuted=0;serviceOperationsExecuted=0;credentialsRead=0;authenticationAttempts=0;databaseOperationsExecuted=0}
if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 6 -Compress
