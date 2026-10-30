#requires -Version 5.1
[CmdletBinding()]
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
$uiRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\windows\server-install'))
$uiPassed=New-Object Collections.Generic.List[string]
foreach($name in @('Show-RackClickInstaller.ps1','Show-RackClickInstalledServer.ps1')){
    $file=Join-Path $uiRoot $name;$tokens=$null;$errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile($file,[ref]$tokens,[ref]$errors)
    if(@($errors).Count-ne0){throw ('UI syntax failed: '+$name)}
    $uiPassed.Add('PS5 syntax: '+$name)
    $text=& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -STA -ExecutionPolicy Bypass -File $file -ValidateLayout
    if($LASTEXITCODE-ne0){throw ('Layout process failed: '+$name)}
    $layout=$text|ConvertFrom-Json -ErrorAction Stop
    if($layout.valid-ne$true-or$layout.privilegedOperationsExecuted-ne0-or$layout.openInitiallyEnabled-ne$false-or$layout.accessInitiallyEnabled-ne$false-or$layout.verifyInitiallyEnabled-ne$false){throw ('Unsafe initial layout: '+$name)}
    if($name-ceq'Show-RackClickInstaller.ps1'-and($layout.inputFields-ne9-or$layout.modeCount-ne2-or$layout.trustInitiallyChecked-ne$false-or$layout.existingPanelEnabled-ne$true)){throw 'Installer controls changed'}
    $uiPassed.Add('Native PS5 STA layout, no privileged operations: '+$name)
}
$viewer=Join-Path $uiRoot 'Show-RackClickInstalledServer.ps1'
$tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($viewer,[ref]$tokens,[ref]$errors)
$definition=$ast.Find({param($node) $node-is[Management.Automation.Language.FunctionDefinitionAst]-and$node.Name-ceq'Test-InstalledReceiptBinding'},$true)
if($null-eq$definition){throw 'Receipt validator missing'}
. ([scriptblock]::Create($definition.Extent.Text))
$id='5c4b8268-a781-4c66-ae15-067499111d98';$management='C:\ProgramData\RackClick\Instances\'+$id+'\management'
$receipt=[ordered]@{schemaVersion=1;installationId=$id;managementPath=$management;instancePath=('C:\ProgramData\RackClick\Instances\'+$id+'\instance');codeRoot=('C:\Program Files\RackClick\'+$id);serviceName='RackClick';serviceSid='S-1-5-21-111-222-333-1005';manifestSha256=('a'*64);backupTaskName=('RackClick-Backup-'+$id);publicOrigin='https://192.168.250.76:5443'}
if(-not(Test-InstalledReceiptBinding ([pscustomobject]$receipt) $management)){throw 'Valid receipt rejected'}
$uiPassed.Add('Valid receipt binding for fixed production roots')
$negative=@(
 @{name='foreign management root';field='managementPath';value='C:\Users\Administrator\management'},
 @{name='foreign instance';field='instancePath';value='C:\foreign'},
 @{name='foreign code';field='codeRoot';value='C:\foreign'},
 @{name='other installation';field='installationId';value=[guid]::NewGuid().ToString('D')},
 @{name='foreign service';field='serviceName';value='PostgreSQL'},
 @{name='administrator identity';field='serviceSid';value='S-1-5-21-111-222-333-500'},
 @{name='system identity';field='serviceSid';value='S-1-5-18'},
 @{name='missing manifest pin';field='manifestSha256';value=''},
 @{name='foreign backup task';field='backupTaskName';value='OtherTask'},
 @{name='HTTP origin';field='publicOrigin';value='http://192.168.250.76:5443'},
 @{name='origin credentials';field='publicOrigin';value='https://user:password@192.168.250.76:5443'},
 @{name='origin query';field='publicOrigin';value='https://192.168.250.76:5443/?secret=1'},
 @{name='origin fragment';field='publicOrigin';value='https://192.168.250.76:5443/#token'},
 @{name='origin path';field='publicOrigin';value='https://192.168.250.76:5443/foreign'}
)
foreach($case in $negative){
    $copy=[ordered]@{};foreach($key in $receipt.Keys){$copy[$key]=$receipt[$key]};$copy[$case.field]=$case.value
    if(Test-InstalledReceiptBinding ([pscustomobject]$copy) $management){throw ('Invalid receipt accepted: '+$case.name)}
    $uiPassed.Add('Reject '+$case.name)
}
foreach($badPath in @('C:\foreign\management',($management+'\..\management'),($management+'\'),$management.Replace($id,$id.ToUpperInvariant()))){
    if(Test-InstalledReceiptBinding ([pscustomobject]$receipt) $badPath){throw 'Noncanonical receipt path accepted'}
    $uiPassed.Add('Reject noncanonical management path')
}
$exportFile=Join-Path $uiRoot 'Export-RackClickServerBackup.ps1';$tokens=$null;$errors=$null
$exportAst=[Management.Automation.Language.Parser]::ParseFile($exportFile,[ref]$tokens,[ref]$errors)
if(@($errors).Count-ne0){throw 'Export syntax failed'};$uiPassed.Add('PS5 syntax: Export-RackClickServerBackup.ps1')
foreach($functionName in @('Test-ExportBackupReceipt','Initialize-ExportBackupNative')){
    $definition=$exportAst.Find({param($node) $node-is[Management.Automation.Language.FunctionDefinitionAst]-and$node.Name-ceq$functionName},$true)
    if($null-eq$definition){throw 'Export validator missing'};. ([scriptblock]::Create($definition.Extent.Text))
}
Initialize-ExportBackupNative;$uiPassed.Add('Native backup-intent guard C# compiles; no handles opened')
$guardFixture=Join-Path ([IO.Path]::GetTempPath()) ('RackClick-Export-Guard-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($guardFixture);[IO.File]::WriteAllText((Join-Path $guardFixture 'manifest.json'),'{}');[IO.File]::WriteAllText((Join-Path $guardFixture 'data.dump'),'PGDMP')
$guardHandles=[RackClickExportBackupNative]::Hold($guardFixture)
try{
    $writeBlocked=$false;try{$guardWrite=[IO.File]::Open((Join-Path $guardFixture 'data.dump'),'Open','Write','ReadWrite');$guardWrite.Dispose()}catch [IO.IOException]{$writeBlocked=$true}
    if(-not$writeBlocked){throw 'Export source can change while guarded'};$uiPassed.Add('Native guard denies writes to dump while read-only source handles are held')
}finally{foreach($handle in $guardHandles){$handle.Dispose()}}
$source=$receipt.instancePath+'\runtime\backups\daily-20261019T123456789Z-00112233445566778899aabbccddeeff'
$latest=[ordered]@{valid=$true;success=$true;exitCode=0;code='scheduled_backup_complete';manifestSha256=('a'*64);backupPath=$source;manifestPath=($source+'\manifest.json')}
if(-not(Test-ExportBackupReceipt ([pscustomobject]$latest) $receipt.instancePath)){throw 'Valid backup receipt rejected'};$uiPassed.Add('Accept completed daily backup receipt in same installation')
foreach($case in @(
 @{field='backupPath';value='C:\foreign';name='foreign backup source'},
 @{field='backupPath';value=($source+'\..\another');name='backup traversal'},
 @{field='backupPath';value=$source.Replace('daily-','initial-');name='unpublished initial backup'},
 @{field='manifestPath';value='C:\foreign\manifest.json';name='foreign manifest'},
 @{field='manifestSha256';value='bad';name='invalid backup pin'},
 @{field='valid';value=$false;name='failed backup'},
 @{field='success';value='true';name='string success'},
 @{field='exitCode';value=1;name='nonzero backup exit'},
 @{field='code';value='backup_complete';name='wrong backup stage'}
)){
    $copy=[ordered]@{};foreach($key in $latest.Keys){$copy[$key]=$latest[$key]};$copy[$case.field]=$case.value
    if(Test-ExportBackupReceipt ([pscustomobject]$copy) $receipt.instancePath){throw ('Unsafe export accepted: '+$case.name)};$uiPassed.Add('Reject '+$case.name)
}
$result=[ordered]@{schemaVersion=1;valid=$true;passed=$uiPassed.Count;checks=$uiPassed;environment='Native Windows PowerShell 5.1 x64, WinForms STA construction, pure receipt validation and local standard-user file handle fixture';privilegedOperationsExecuted=0;serviceChangesExecuted=0;sqlExecuted=0;limits=@('No elevated installation, SCM, task registration, credential reading, robocopy /B or real reboot executed.','The actual postboot verifier must run on the target VM before the UI can report 100%.')}
if($OutputPath){$bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($result|ConvertTo-Json -Depth 6));[IO.File]::WriteAllBytes([IO.Path]::GetFullPath($OutputPath),$bytes)}
$result|ConvertTo-Json -Depth 6 -Compress
