#requires -Version 5.1
[CmdletBinding()]
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules'
if(-not[Environment]::Is64BitProcess){throw 'Native x64 PowerShell required'}
$passed=New-Object Collections.Generic.List[string]
$sourceRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\windows\server-install'))
$tokens=$null;$errors=$null
$broker=[Management.Automation.Language.Parser]::ParseFile((Join-Path $sourceRoot 'Install-RackClickServer.ps1'),[ref]$tokens,[ref]$errors)
if(@($errors).Count){throw 'Broker syntax failed'};$passed.Add('Broker PS5 syntax')
$commands=@($broker.FindAll({param($node) $node-is[Management.Automation.Language.CommandAst]-and$node.GetCommandName()-ceq'New-LocalUser'},$true))
if($commands.Count-ne1){throw 'Expected one account creation command'}
$descriptionAst=$null
for($i=0;$i-lt$commands[0].CommandElements.Count-1;$i++){
    $element=$commands[0].CommandElements[$i]
    if($element-is[Management.Automation.Language.CommandParameterAst]-and$element.ParameterName-ceq'Description'){$descriptionAst=$commands[0].CommandElements[$i+1]}
}
if($null-eq$descriptionAst){throw 'Account description missing'}
$descriptionExpression=[scriptblock]::Create('param($setupPlan) '+$descriptionAst.Extent.Text)
$command=Get-Command New-LocalUser -ErrorAction Stop
$descriptionConstraint=@($command.Parameters.Description.Attributes|Where-Object{$_-is[Management.Automation.ValidateLengthAttribute]})
$nameConstraint=@($command.Parameters.Name.Attributes|Where-Object{$_-is[Management.Automation.ValidateLengthAttribute]})
if($descriptionConstraint.Count-ne1-or$descriptionConstraint[0].MaxLength-ne48-or$nameConstraint.Count-ne1-or$nameConstraint[0].MaxLength-ne20-or-not$command.Parameters.ContainsKey('WhatIf')){throw 'Unexpected native command constraints'}
$passed.Add('Native Windows command exposes Description max48 and Name max20 with WhatIf')
$testName='RCCheck'+[guid]::NewGuid().ToString('N').Substring(0,10)
if(Get-LocalUser -Name $testName -ErrorAction SilentlyContinue){throw 'Test identity already exists'}
function Assert-NativeDescriptionRejected([string]$Value,[string]$Label) {
    $rejected=$false
    try{New-LocalUser -Name $testName -Description $Value -NoPassword -WhatIf -ErrorAction Stop 6>$null}catch{
        if($_.Exception.GetType().FullName-cne'System.Management.Automation.ParameterBindingValidationException'-or$_.FullyQualifiedErrorId-cnotlike'ParameterArgumentValidationError,*'){throw};$rejected=$true
    }
    if(-not$rejected){throw ('Native binding accepted '+$Label)};$passed.Add($Label)
}
$id='97ff9b99-ad2a-4d7d-ae95-9638772378a0'
$old='RackClick service '+$id
if($old.Length-ne54){throw 'Reproduction fixture changed'}
Assert-NativeDescriptionRejected $old 'Reproduce previous 54-character description rejection before account creation'
Assert-NativeDescriptionRejected ('x'*49) 'Reject Description49 boundary with real cmdlet WhatIf'
New-LocalUser -Name $testName -Description ('x'*48) -NoPassword -WhatIf -ErrorAction Stop 6>$null
$passed.Add('Accept Description48 boundary with real cmdlet WhatIf')
$descriptions=@()
foreach($currentId in @($id,'00000000-0000-0000-0000-000000000000','ffffffff-ffff-ffff-ffff-ffffffffffff')){
    $description=[string](& $descriptionExpression ([pscustomobject]@{id=$currentId}))
    if($description.Length-ne46-or-not$description.EndsWith($currentId,[StringComparison]::Ordinal)){throw 'Broker description exceeds native limit or loses full installation identity'}
    New-LocalUser -Name $testName -Description $description -NoPassword -WhatIf -ErrorAction Stop 6>$null
    $descriptions+=$description;$passed.Add('Actual broker description accepted and retains full GUID: '+$currentId)
}
New-LocalUser -Name ('RC'+[guid]::NewGuid().ToString('N').Substring(0,18)) -Description $descriptions[0] -NoPassword -WhatIf -ErrorAction Stop 6>$null
$passed.Add('Accept account Name20 boundary with real cmdlet WhatIf')
$rejected=$false
try{New-LocalUser -Name ('x'*21) -NoPassword -WhatIf -ErrorAction Stop 6>$null}catch{if($_.Exception.GetType().FullName-cne'System.Management.Automation.ParameterBindingValidationException'){throw};$rejected=$true}
if(-not$rejected){throw 'Name21 accepted'};$passed.Add('Reject account Name21 boundary with real cmdlet WhatIf')
if(Get-LocalUser -Name $testName -ErrorAction SilentlyContinue){throw 'WhatIf test created an account'}
$passed.Add('Test identity absent after native WhatIf calls')
$ui=[Management.Automation.Language.Parser]::ParseFile((Join-Path $sourceRoot 'Show-RackClickInstaller.ps1'),[ref]$tokens,[ref]$errors)
if(@($errors).Count){throw 'Installer UI syntax failed'};$passed.Add('Installer UI PS5 syntax')
$definition=$ui.Find({param($node) $node-is[Management.Automation.Language.FunctionDefinitionAst]-and$node.Name-ceq'Format-SetupUiFailure'},$true)
if($null-eq$definition){throw 'Failure formatter missing'};. ([scriptblock]::Create($definition.Extent.Text))
$message=Format-SetupUiFailure ([pscustomobject]@{code='setup_stage_failed_preserved';stage='account';failureLine=78;errorMessage='NEVER_DISPLAY_RAW_EXCEPTION'}) 'C:\private-report'
if($message-notlike'*creacion de cuenta (linea 78)*'-or$message-notlike'*Informe privado: C:\private-report*'-or$message-like'*RECOPILAR-INFORME.cmd*'-or$message-like'*NEVER_DISPLAY*'){throw 'Account failure diagnostic incorrect'}
$passed.Add('Failure UI shows account stage, source line and private report path; automatic export precedes manual fallback')
$message=Format-SetupUiFailure ([pscustomobject]@{code='bad secret message';stage='secret stage';failureLine='secret line'}) 'C:\private-report'
if($message-notlike'*etapa desconocida: installer_result_not_confirmed*'-or$message-like'*secret*'){throw 'Untrusted diagnostic fields displayed'}
$passed.Add('Failure UI rejects arbitrary stage, code and line text')
$message=Format-SetupUiFailure ([pscustomobject]@{code='setup_failed';stage='scheduled_backup';failureLine=0}) 'C:\private-report'
if($message-notlike'*tareas programadas*'-or$message-like'*(linea*'){throw 'Scheduled backup failure diagnostic incorrect'}
$passed.Add('Failure UI labels scheduled backup and omits invalid line')
if((Format-SetupUiFailure $null 'C:\private-report')-notlike'*installer_result_not_confirmed*'){throw 'Missing receipt incorrectly formatted'}
$passed.Add('Failure UI handles missing receipt without claiming success')
$result=[ordered]@{schemaVersion=1;valid=$true;passed=$passed.Count;checks=$passed;environment='Native Windows PowerShell 5.1 x64; real New-LocalUser parameter binding with WhatIf only';oldDescriptionLength=54;newDescriptionLength=46;nativeMaximum=48;accountsCreated=0;servicesCreated=0;limits=@('No elevated account creation, LSA changes, SCM registration or real server reboot.','Remote failure attribution still requires the sanitized report from the VM.')}
if($OutputPath){[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath),($result|ConvertTo-Json -Depth 5),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 5 -Compress
