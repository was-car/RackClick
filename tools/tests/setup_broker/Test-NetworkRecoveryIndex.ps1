#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
$operators=Join-Path $PSScriptRoot '..\..\windows\server-install'
. (Join-Path $operators 'Set-RackClickServerNetwork.ps1') -FunctionsOnly
. (Join-Path $operators 'Get-RackClickNetworkRecoveryState.ps1') -FunctionsOnly
$checks=New-Object 'Collections.Generic.List[string]'
function Assert-IndexTest([bool]$Condition,[string]$Name){if(-not$Condition){throw ('Test failed: '+$Name)};$checks.Add($Name)}
$root=Join-Path ([IO.Path]::GetTempPath()) ('RackClick-index-contract-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($root)
$expected=@{};$entries=@();$n=0
foreach($key in @('profile','config','root','public','pfx','tls-password','managementCa','receipt')){
 $path='C:\fixture-only\'+$key;$expected[$key]=$path
 $entries+=@(@{key=$key;path=$path;snapshot=@{Bytes=[Text.Encoding]::UTF8.GetBytes('generated fixture '+$key);Sddl='O:BAG:SYD:P(A;;FA;;;BA)(A;;FA;;;SY)'}})
 $n++
}
$ctx=@{entries=$entries;receipt=@{managementPath=$root;backupTaskName='FixtureOnly';trustedCaThumbprint=('A'*40)};plan=@{installationId='606b8c29-41de-4dc0-b63d-ade836000d9e'};task=@{Actions=@(@{Arguments='fixture-only'})};firewall=@{local=@('192.168.178.141');remote=@('192.168.178.0/24')};taskWasEnabled=$true;serviceWasRunning=$false;committed=$false;rollbackStatus='not_needed';journalPath='';stage='preflight'}
# Only OS boundaries are replaced. Save-RcNetworkBackup, serializer, durable
# file IO and parser are the actual production functions.
function New-RcNetworkPrivateDirectory([string]$Path){$null=[IO.Directory]::CreateDirectory($Path)}
function Get-RcNetworkSnapshot($Context,[string]$Path){return @($Context.entries|Where-Object{$_.path-ceq$Path})[0].snapshot}
function Export-ScheduledTask([string]$TaskName,[string]$TaskPath){return '<Task><Settings/><Triggers/></Task>'}
Save-RcNetworkBackup $ctx
$bytes=[IO.File]::ReadAllBytes((Join-Path $ctx.transactionDirectory 'files.json'))
$old=@([Text.Encoding]::UTF8.GetString($bytes)|ConvertFrom-Json)
Assert-IndexTest ($old.Count-eq1-and$old[0]-is[Array]-and$old[0].Count-eq8) 'Reproduce published WinPS5 nested-array failure using the real writer'
$actual=Read-RcRecoveryIndex -Bytes $bytes -Expected $expected
Assert-IndexTest ($actual-is[Array]-and$actual.Count-eq8) 'Real writer index loads as eight entries with the new reader'
foreach($e in $actual){
 $backup=[IO.File]::ReadAllBytes((Join-Path $ctx.transactionDirectory $e.backup))
 Assert-IndexTest ((Get-RcNetworkHash $backup)-ceq$e.sha256-and$e.path-ceq$expected[$e.key]) ('Writer and reader agree on '+$e.key)
}
function Assert-RejectedIndex($Value,[string]$Name){
 $rejected=$false;try{$null=Read-RcRecoveryIndex -Bytes (ConvertTo-RcNetworkBytes $Value) -Expected $expected}catch{$rejected=$true}
 Assert-IndexTest $rejected ('Reject '+$Name)
}
Assert-RejectedIndex @($actual[0..6]) 'seven entries'
Assert-RejectedIndex @($actual+$actual[0]) 'nine entries'
Assert-RejectedIndex ([pscustomobject]@{Count=8;key='profile'}) 'object impersonating an eight-entry array'
foreach($case in @(
 @{name='duplicate key';field='key';value='profile'},
 @{name='foreign key';field='key';value='unknown'},
 @{name='foreign path';field='path';value='C:\foreign'},
 @{name='non-string path';field='path';value=42},
 @{name='duplicate backup';field='backup';value='file-0.bin'},
 @{name='backup traversal';field='backup';value='..\file-1.bin'},
 @{name='invalid hash';field='sha256';value='invalid'},
 @{name='invalid descriptor';field='sddl';value='not a descriptor'}
)){
 $copy=ConvertFrom-Json -InputObject ([Text.Encoding]::UTF8.GetString($bytes))
 $copy[1].($case.field)=$case.value
 Assert-RejectedIndex $copy $case.name
}
$result=[ordered]@{schemaVersion=1;valid=$true;passed=$checks.Count;checks=@($checks);environment='Windows PowerShell 5.1; real backup writer, serializer, durable fixture IO and index reader';fixture=$root;privilegedOperationsExecuted=0;serviceOperationsExecuted=0;authenticationAttempts=0;databaseOperationsExecuted=0;credentialsRead=0}
if($OutputPath){[IO.File]::WriteAllText($OutputPath,($result|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 6 -Compress
