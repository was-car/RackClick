#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
$sourceRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\windows\server-install'))
. (Join-Path $sourceRoot 'RackClick.Setup.ps1')
. (Join-Path $sourceRoot 'RackClick.Setup.Security.ps1')
. (Join-Path $sourceRoot 'RackClick.Setup.Lifecycle.ps1')
. (Join-Path $sourceRoot 'Collect-RackClickInstallReport.ps1') -FunctionsOnly
$checks=New-Object Collections.Generic.List[string]
$id='6b2066c6-0c38-43bc-8d62-202052605965'
$receipt=[pscustomobject]@{schemaVersion=1;installationId=$id;bootAtInstall='2026-10-24T07:00:00.0000000Z';installedUtc='2026-10-24T07:10:00.0000000Z'}
$verified=[pscustomobject]@{schemaVersion=1;valid=$true;success=$true;exitCode=0;code='postboot_verified';rebootVerified=$true;productAdopted=$false;installationId=$id;bootUtc='2026-10-25T07:00:00.0000000Z';checkedUtc='2026-10-25T07:01:00.0000000Z';password='DO_NOT_EXPORT_POSTBOOT_SECRET'}
$boot='2026-10-25T07:00:00.0000000Z';$now='2026-10-25T07:02:00.0000000Z'
$started='2026-10-25T07:00:59.0000000Z'
# Reproduces the received product defect before testing the new projection:
# the real sanitizer currently drops the UUID and both verification timestamps.
$safe=Select-SetupDiagnosticFields $verified
foreach($field in @('installationId','bootUtc','checkedUtc')){
    if(-not$safe.Contains($field)-or$safe[$field]-cne$verified.$field){throw ('Postboot report loses binding metadata: '+$field)}
    $checks.Add('Actual sanitizer retains exact typed '+$field)
}
function State($r=$receipt,$v=$verified,$b=$boot,$n=$now){Get-SetupRecordedInstallationState -Receipt $r -Verification $v -CurrentBootUtc $b -ObservedUtc $n}
$state=State
if($state.status-cne'recorded'-or-not$state.rebootVerified-or$state.currentHealthVerified-or$state.productAdopted-or$state.installationId-cne$id){throw 'Valid current-boot verification was not recorded safely'}
$checks.Add('Matching postboot records reboot verification only, never current health or adoption')
foreach($case in @(
    @('installationId','91f5c48a-1c98-46bb-a248-7190f07c2a27'),@('installationId',$id.ToUpperInvariant()),
    @('schemaVersion','1'),@('schemaVersion',2),@('valid','true'),@('valid',@($true,$false)),
    @('success',1),@('exitCode','0'),@('exitCode',1),@('code',@('postboot_verified','other')),
    @('rebootVerified','true'),@('productAdopted',$true),@('bootUtc','2026-10-24T08:00:00Z'),
    @('checkedUtc','2026-10-25T06:59:59Z'),@('checkedUtc','2026-10-25T07:03:00Z'),
    @('bootUtc','25.10.2026 07:00'),@('checkedUtc',@('2026-10-25T07:01:00Z'))
)){
    $copy=$verified|ConvertTo-Json -Depth 4|ConvertFrom-Json;$copy.($case[0])=$case[1]
    $answer=State $receipt $copy
    if($answer.rebootVerified-or$answer.currentHealthVerified-or$answer.productAdopted){throw ('Unsafe record accepted: '+$case[0])}
    $checks.Add('Rejects verification variant '+$case[0]+' #'+$checks.Count)
}
foreach($field in @('installationId','bootUtc','checkedUtc','rebootVerified')){
    $copy=$verified|ConvertTo-Json|ConvertFrom-Json;$copy.PSObject.Properties.Remove($field)
    if((State $receipt $copy).rebootVerified){throw ('Missing metadata accepted: '+$field)}
    $checks.Add('Missing '+$field+' never confirms reboot')
}
$stale=State $receipt $verified '2026-10-25T07:30:00Z' '2026-10-25T07:31:00Z'
if($stale.status-cne'stale'-or$stale.rebootVerified){throw 'Earlier-boot receipt accepted for new boot'}
$checks.Add('Earlier boot receipt explicitly stale, not current green')
$pending=State $receipt $null
if($pending.status-cne'pending'-or$pending.rebootVerified){throw 'Missing verification accepted'}
$checks.Add('Absent record stays pending')
$negative=[pscustomobject]@{schemaVersion=1;valid=$false;success=$false;exitCode=1;code='postboot_https_health_failed';rebootVerified=$false;productAdopted=$false}
if((State $receipt $negative).rebootVerified){throw 'Last failed verification restored an earlier green'}
$checks.Add('Last failed verification cannot resurrect prior green')
$mismatched=$receipt|ConvertTo-Json|ConvertFrom-Json;$mismatched.installationId='NOT-A-GUID'
if((State $mismatched).rebootVerified){throw 'Invalid receipt accepted'}
$checks.Add('Invalid receipt identity cannot bind a postboot record')
$oldCulture=[Threading.Thread]::CurrentThread.CurrentCulture
try{[Threading.Thread]::CurrentThread.CurrentCulture=[Globalization.CultureInfo]::GetCultureInfo('de-DE');if((State).status-cne'recorded'){throw 'Invariant UTC parsing regressed in de-DE'}}finally{[Threading.Thread]::CurrentThread.CurrentCulture=$oldCulture}
$checks.Add('Invariant UTC comparison works under de-DE')
. (Join-Path $sourceRoot 'Show-RackClickInstalledServer.ps1') -FunctionsOnly
foreach($exitCode in @(1,3,99)){
    if(Test-InstalledPostbootCompletion $receipt $verified $exitCode $boot $now $started){throw 'Nonzero native exit promoted to 100 percent'}
    $checks.Add('Live panel rejects native exit '+$exitCode)
}
if(-not(Test-InstalledPostbootCompletion $receipt $verified 0 $boot $now $started)){throw 'Live current verified result rejected'}
$checks.Add('Live panel accepts exact positive with native exit zero')
if(Test-InstalledPostbootCompletion $receipt $verified 0 '2026-10-25T07:30:00Z' '2026-10-25T07:31:00Z' '2026-10-25T07:30:59Z'){throw 'Live panel accepts stale boot'}
$checks.Add('Live panel rejects stale boot even with native exit zero')
if(Test-InstalledPostbootCompletion $receipt $verified 0 $boot $now '2026-10-25T07:01:01Z'){throw 'Recorded success from before current verification was replayed'}
$checks.Add('Live panel rejects same-boot success older than this verification launch')
if(Test-InstalledPostbootCompletion $receipt $verified 0 $boot $now ''){throw 'Live verification without start time accepted'}
$checks.Add('Live panel requires a valid timestamp for its own verification launch')
$tokens=$null;$errors=$null;$uiAst=[Management.Automation.Language.Parser]::ParseFile((Join-Path $sourceRoot 'Show-RackClickInstalledServer.ps1'),[ref]$tokens,[ref]$errors)
if(@($errors).Count){throw 'Installed panel does not parse'}
$click=$uiAst.Find({param($n) $n-is[Management.Automation.Language.InvokeMemberExpressionAst]-and$n.Member.Value-ceq'Add_Click'-and$n.Expression.Extent.Text-ceq'$panelVerify'},$true)
if($null-eq$click){throw 'Verification click handler not found'}
$handler=$click.Arguments[0].ScriptBlock.GetScriptBlock()
$panelProgress=[pscustomobject]@{Value=100};$panelStatus=[pscustomobject]@{Text='previous verified state'}
$panelState=@{receipt=@{managementPath='C:\fixture-management'};exitCode=0;process=$null;stdout='';verificationStartedUtc='previous'}
function Read-InstalledServerReceipt {param($Path) [pscustomobject]@{managementPath='C:\fixture-management';codeRoot='C:\fixture-code'}}
function Start-Process {throw 'deliberate_start_failure_no_process_created'}
& $handler
if($panelProgress.Value-ne95-or$panelState.exitCode-ne1){throw 'Failed verification launch left stale 100 percent displayed'}
$checks.Add('Actual click handler clears previous 100 percent even when the child cannot start; no launch')
$fake=[pscustomobject]@{installationId=$id;checkedUtc='RAW_SECRET';bootUtc=@('RAW_SECRET');bootAtInstall='RAW_SECRET';installedUtc='RAW_SECRET';password='RAW_SECRET'}
$filtered=Select-SetupDiagnosticFields $fake
if(($filtered|ConvertTo-Json)-like'*RAW_SECRET*'){throw 'Unbounded metadata escaped sanitizer'}
$checks.Add('Malformed dates, arrays and secrets stay out of sanitized metadata')
# Native file integration: only the fixed production namespace, expected admin
# ACL boundary and CIM boot source are substituted. The reader, file ACL checks,
# decoding, sanitizer and complete attempt collector body remain real.
$script:reportFixture=Join-Path ([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\.local'))) ('postboot-recorded-files-'+[guid]::NewGuid().ToString('N'))
$script:fixtureSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$acl=New-Object Security.AccessControl.DirectorySecurity
$acl.SetSecurityDescriptorSddlForm(('O:'+$script:fixtureSid+'G:SYD:P(A;OICI;FA;;;'+$script:fixtureSid+')(A;OICI;FA;;;SY)'))
$null=[IO.Directory]::CreateDirectory($script:reportFixture,$acl)
$attempt=Join-Path $script:reportFixture ('profile\RackClick\Setup\'+$id);$null=[IO.Directory]::CreateDirectory($attempt)
$management=Join-Path $script:reportFixture ($id+'\management');$null=[IO.Directory]::CreateDirectory($management)
$historicalPath=Join-Path $attempt 'result.json';$receiptPath=Join-Path $management 'server-installation.json';$verificationPath=Join-Path $management 'postboot-verification.json'
$utf8=New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText($historicalPath,(@{schemaVersion=1;valid=$true;success=$false;exitCode=3;stage='awaiting_reboot';installationPercent=95;password='DO_NOT_EXPORT_POSTBOOT_SECRET'}|ConvertTo-Json -Compress),$utf8)
$script:fixtureBoot=[DateTime]::UtcNow.AddMinutes(-30)
$realReceipt=[pscustomobject]@{schemaVersion=1;installationId=$id;bootAtInstall=$script:fixtureBoot.AddDays(-1).ToString('o');installedUtc=$script:fixtureBoot.AddHours(-23).ToString('o')}
$realVerification=$verified|ConvertTo-Json|ConvertFrom-Json
$realVerification.bootUtc=$script:fixtureBoot.ToString('o');$realVerification.checkedUtc=$script:fixtureBoot.AddMinutes(1).ToString('o')
[IO.File]::WriteAllText($receiptPath,($realReceipt|ConvertTo-Json -Compress),$utf8)
[IO.File]::WriteAllText($verificationPath,($realVerification|ConvertTo-Json -Compress),$utf8)
$tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $sourceRoot 'RackClick.Setup.Diagnostics.ps1'),[ref]$tokens,[ref]$errors)
if(@($errors).Count){throw 'Diagnostic source does not parse'}
$definition=$ast.Find({param($n) $n-is[Management.Automation.Language.FunctionDefinitionAst]-and$n.Name-ceq'Get-SetupAttemptDiagnostic'},$true).Extent.Text
$namespaceLine=@'
$management='C:\ProgramData\RackClick\Instances\'+$id+'\management'
'@
if(-not$definition.Contains($namespaceLine)){throw 'Fixture namespace substitution no longer matches exact producer'}
$definition=$definition.Replace('function Get-SetupAttemptDiagnostic(', 'function Get-TestSetupAttemptDiagnostic(').Replace($namespaceLine,'$management=Join-Path $script:reportFixture ($id+''\management'')').Replace("@('S-1-5-18','S-1-5-32-544')",'@($script:fixtureSid,''S-1-5-18'')')
Invoke-Expression $definition
function Read-SetupDiagnosticBinding {param($AttemptId) throw 'report_fixture_no_private_instance'}
function Assert-SetupPath {param($Path,$Kind) if(-not$Path.StartsWith($script:reportFixture+'\',[StringComparison]::Ordinal)){throw 'Fixture escaped its private root'}}
function Assert-SetupManagementAcl {param($Path) if(-not$Path.StartsWith($script:reportFixture+'\',[StringComparison]::Ordinal)){throw 'Fixture escaped management root'}}
function Get-CimInstance {param($ClassName,$ErrorAction) if($ClassName-cne'Win32_OperatingSystem'){throw 'Unexpected fixture CIM query'};[pscustomobject]@{LastBootUpTime=$script:fixtureBoot}}
function Collect-Fixture {
    $before=@{};foreach($p in @($historicalPath,$receiptPath,$verificationPath)){$before[$p]=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash}
    $record=Get-TestSetupAttemptDiagnostic $attempt @($script:fixtureSid,'S-1-5-18')
    foreach($p in $before.Keys){if((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash-cne$before[$p]){throw 'Read-only collection changed original evidence'}}
    if(($record|ConvertTo-Json -Depth 15)-like'*DO_NOT_EXPORT_POSTBOOT_SECRET*'){throw 'Original file secret leaked through collector'}
    if($record.reports['result.json'].stage-cne'awaiting_reboot'-or$record.reports['result.json'].exitCode-ne3){throw 'Historical broker result was rewritten in report'}
    return $record
}
$collected=Collect-Fixture
if($collected.installationState.status-cne'recorded'-or-not$collected.installationState.rebootVerified-or$collected.installationState.currentHealthVerified-or$collected.installationState.verificationSha256-cnotmatch'^[a-f0-9]{64}$'){throw 'Real file collector lost bound current-boot record'}
$checks.Add('Native files: separate recorded state and source hashes, immutable broker result, no leaked secret')
function Get-SetupAttemptDiagnostic {param($Folder,$AllowedSids) Get-TestSetupAttemptDiagnostic $Folder $AllowedSids}
$savedLocalData=$env:LOCALAPPDATA
try{
    $env:LOCALAPPDATA=Join-Path $script:reportFixture 'profile'
    $report=New-SetupSanitizedReport $id ''
    if($report.installationState.status-cne'recorded'-or$report.reports['result.json'].stage-cne'awaiting_reboot'){throw 'Top-level sanitized report lost separate postboot state'}
    $exports=Join-Path $script:reportFixture 'exports';$null=[IO.Directory]::CreateDirectory($exports)
    $zipPath=Export-SetupSanitizedReport $report $exports
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip=[IO.Compression.ZipFile]::OpenRead($zipPath)
    try{$reader=New-Object IO.StreamReader($zip.GetEntry('INFORME.json').Open());try{$exportText=$reader.ReadToEnd()}finally{$reader.Dispose()}}finally{$zip.Dispose()}
    $exported=$exportText|ConvertFrom-Json -ErrorAction Stop
    if($exported.installationState.status-cne'recorded'-or$exported.reports.'result.json'.exitCode-ne3-or$exportText-like'*DO_NOT_EXPORT_POSTBOOT_SECRET*'){throw 'Actual report ZIP lost postboot projection or leaked original secret'}
}finally{$env:LOCALAPPDATA=$savedLocalData}
$checks.Add('Real top-level collector and ZIP preserve separate state with original exit 3 and no secret')
[IO.File]::WriteAllText($verificationPath,($negative|ConvertTo-Json -Compress),$utf8)
if((Collect-Fixture).installationState.rebootVerified){throw 'File collector resurrected prior success after latest failed check'}
$checks.Add('Native files: latest negative overwrites prior verification only and cannot restore green')
[IO.File]::WriteAllText($verificationPath,'{"valid":true BROKEN DO_NOT_EXPORT_POSTBOOT_SECRET',$utf8)
if((Collect-Fixture).installationState.rebootVerified){throw 'File collector accepted malformed verification'}
$checks.Add('Native files: malformed last record stays unavailable, original report remains exact')
[IO.File]::WriteAllText($verificationPath,($realVerification|ConvertTo-Json -Compress),$utf8)
$script:fixtureBoot=$script:fixtureBoot.AddMinutes(5)
if((Collect-Fixture).installationState.status-cne'stale'){throw 'File collector did not compare real boot source with recorded boot'}
$checks.Add('Native files: changed CIM boot marks old verification stale')
$script:fixtureBoot=$script:fixtureBoot.AddMinutes(-5)
$realReceipt.installationId='91f5c48a-1c98-46bb-a248-7190f07c2a27'
[IO.File]::WriteAllText($receiptPath,($realReceipt|ConvertTo-Json -Compress),$utf8)
if((Collect-Fixture).installationState.rebootVerified){throw 'File collector accepted cross-instance receipt'}
$checks.Add('Native files: receipt UUID must match exact attempt directory')
$result=[ordered]@{valid=$true;passed=$checks.Count;checks=$checks;fixture=$script:reportFixture;environment='Windows PowerShell 5.1; real policies/sanitizer/panel completion and native private file collector fixtures';servicesChanged=0;accountsChanged=0;sqlExecuted=0;vmActions=0;limits=@('No installation, actual reboot, live HTTPS, GUI or scheduled task was executed.','File integration substitutes only the fixed namespace, expected admin identity boundary, unavailable private instance binding and CIM boot source.','Recorded verification never asserts current health; 100 percent requires the fresh child result and native exit zero.')}
if($OutputPath){[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath),($result|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 6 -Compress
