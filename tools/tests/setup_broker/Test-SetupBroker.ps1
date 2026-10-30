#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\..\windows\server-install\RackClick.Setup.ps1')
$root=Join-Path ([IO.Path]::GetTempPath()) ('RackClick-Setup-Tests-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($root)
$path=Join-Path $root 'plan.json';$passed=New-Object Collections.Generic.List[string]
$plan=[ordered]@{schemaVersion=1;id=[guid]::NewGuid().ToString('D');bindAddress='192.168.250.76';publicHost='192.168.250.76';httpsPort=5443;postgresPort=55441;allowedSubnet='192.168.250.0/24';systemhaus='Systemhaus';bootstrapUser='Wascar';serviceName='RackClick';accountName='RackClickSvc';mode='New';backupPath='';backupManifestSha256='';trustOnServer=$true}
Write-SetupJson $path $plan
$valid=Read-SetupPlan $path
if($valid.bindAddress-cne'192.168.250.76'){throw 'valid plan rejected'};$passed.Add('Valid plan on actual server subnet')
$cases=@(
 @{name='loopback bind';key='bindAddress';value='127.0.0.1'},
 @{name='wildcard public host';key='publicHost';value='*.rackclick.local'},
 @{name='invalid port type';key='httpsPort';value='5443'},
 @{name='overlapping ports';key='postgresPort';value=5443},
 @{name='foreign subnet';key='allowedSubnet';value='192.168.178.0/24'},
 @{name='noncanonical subnet';key='allowedSubnet';value='192.168.250.76/24'},
 @{name='unbounded firewall subnet';key='allowedSubnet';value='0.0.0.0/0'},
 @{name='foreign service';key='serviceName';value='PostgreSQL'},
 @{name='privileged account name';key='accountName';value='Administrator'},
 @{name='shell quote in bootstrap';key='bootstrapUser';value='Was"car'},
 @{name='unexpected backup for New';key='backupPath';value='C:\foreign'},
 @{name='trust not consented';key='trustOnServer';value=$false}
)
foreach($case in $cases){
    $copy=[ordered]@{};foreach($key in $plan.Keys){$copy[$key]=$plan[$key]};$copy[$case.key]=$case.value
    Write-SetupJson $path $copy;$rejected=$false
    try{$null=Read-SetupPlan $path}catch{$rejected=$true}
    if(-not$rejected){throw ('Did not reject '+$case.name)};$passed.Add('Reject '+$case.name)
}
$extra=[ordered]@{};foreach($key in $plan.Keys){$extra[$key]=$plan[$key]};$extra.extra='foreign'
Write-SetupJson $path $extra;$rejected=$false;try{$null=Read-SetupPlan $path}catch{$rejected=$true}
if(-not$rejected){throw 'Extra field accepted'};$passed.Add('Reject extra plan field')
foreach($value in @('C:\bad"name',('C:\bad'+"`n"+'name'),'C:\trailing\')){
    $rejected=$false;try{$null=ConvertTo-SetupArgument $value}catch{$rejected=$true}
    if(-not$rejected){throw 'Unsafe argument accepted'};$passed.Add('Reject unsafe process argument')
}
$payload=Join-Path $root 'payload';$null=[IO.Directory]::CreateDirectory($payload)
Write-SetupJson (Join-Path $payload 'payload.json') @{schemaVersion=1;kind='RackClickServerSetup';bundleArchiveSha256='a0df90ed3a2864492d8d9bdc2cc2e552113a6b9c81a3e603c1c2920486c26869';files=@(@{path='RackClick.zip';size=1;sha256=('0'*64)})}
$rejected=$false;try{$null=Assert-SetupPayload $payload}catch{$rejected=$true}
if(-not$rejected){throw 'Missing payload accepted'};$passed.Add('Reject missing package component')
$result=@{schemaVersion=1;valid=$true;passed=$passed.Count;checks=$passed;environment='Windows PowerShell; pure validation only';temporaryFixture=$root;elevatedOperationsExecuted=0}
if($OutputPath){Write-SetupJson $OutputPath $result}
$result|ConvertTo-Json -Depth 4 -Compress
