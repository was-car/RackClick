#requires -Version 5.1
param([Parameter(Mandatory=$true)][string]$ArchivePath,[Parameter(Mandatory=$true)][string]$ExpectedSha256,[ValidateSet('03','04','05')][string]$Edition='05',[string]$OutputPath='')
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.IO.Compression
$checks=New-Object Collections.Generic.List[string]
function Check($Value,[string]$Name){if(-not$Value){throw $Name};$checks.Add($Name)}
function Reject([scriptblock]$Action,[string]$Name){$rejected=$false;try{&$Action|Out-Null}catch{$rejected=$true};Check $rejected $Name}
$fixture=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot ('..\..\..\.local\clean-release-fixtures\'+[guid]::NewGuid().ToString('N'))))
$null=[IO.Directory]::CreateDirectory($fixture)
Check ((Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()-ceq$ExpectedSha256) 'Full envelope matches announced SHA256'
$file=[IO.File]::Open($ArchivePath,'Open','Read','Read')
try{$zip=New-Object IO.Compression.ZipArchive($file,[IO.Compression.ZipArchiveMode]::Read,$true);try{
    $expected=@('00-LEEME.html','00-LIMPIAR-Y-REINSTALAR.cmd','INICIAR.ps1','PAQUETE.json','Servidor.zip')
    Check ($zip.Entries.Count-eq$expected.Count) 'Envelope contains only five declared entries'
    foreach($name in $expected){$entry=$zip.GetEntry('RackClick-Servidor-'+$Edition+'/'+$name);Check ($null-ne$entry) ('Envelope entry present: '+$name);$input=$entry.Open();try{$output=[IO.File]::Open((Join-Path $fixture $name),'CreateNew','Write','None');try{$input.CopyTo($output)}finally{$output.Dispose()}}finally{$input.Dispose()}}
}finally{$zip.Dispose()}}finally{$file.Dispose()}
$package=Get-Content -LiteralPath (Join-Path $fixture 'PAQUETE.json') -Raw|ConvertFrom-Json -ErrorAction Stop
Check ($package.kind-ceq'RackClickCleanStartEnvelope'-and$package.edition-ceq$Edition) ('Envelope edition'+$Edition+' and kind match')
foreach($entry in $package.files){Check ((Get-FileHash -LiteralPath (Join-Path $fixture $entry.path) -Algorithm SHA256).Hash.ToLowerInvariant()-ceq$entry.sha256) ('Envelope member hash: '+$entry.path)}
$launcher=Join-Path $fixture 'INICIAR.ps1'
$tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($launcher,[ref]$tokens,[ref]$errors)
Check (@($errors).Count-eq0) 'Packaged bootstrap parses in Windows PowerShell5'
. $launcher -FunctionsOnly
Check ($script:PayloadSha256-ceq$package.payloadSha256) 'Bootstrap fixed payload hash matches package receipt'
# Unprivileged fixture: production BA/SYSTEM directory creation is substituted,
# while the packaged ZIP verification/extraction code executes unchanged.
function New-CleanPrivateDirectory([string]$Path){Assert-CleanLocalPath $Path;if(Test-Path -LiteralPath $Path){throw 'clean_destination_exists'};$null=[IO.Directory]::CreateDirectory($Path);return $Path}
$stage=Join-Path $fixture 'stage';$inner=Join-Path $fixture 'Servidor.zip'
$expanded=Expand-CleanVerifiedPayload $inner $script:PayloadSha256 $stage
Check ($expanded.valid-and$expanded.files-gt90) 'Packaged full payload extracts through actual bootstrap'
$ops=Join-Path $stage 'operators\server-install'
. (Join-Path $ops 'RackClick.Setup.ps1');. (Join-Path $ops 'RackClick.Setup.Security.ps1');. (Join-Path $ops 'RackClick.Setup.Lifecycle.ps1');. (Join-Path $ops 'RackClick.Setup.Reset.ps1')
$null=Assert-SetupPayload $stage;$checks.Add('Strict packaged payload inventory, hashes and frozen application bundle accepted')
foreach($name in @('RackClick.Setup.Reset.ps1','RackClick.Setup.Namespace.ps1','RackClick.Setup.Host.ps1','RackClick.Setup.Process.ps1','RackClick.Setup.Security.ps1','Install-RackClickServer.ps1','Show-RackClickInstaller.ps1','Collect-RackClickInstallReport.ps1','Prepare-RackClickServer.ps1')){
    $source=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot ('..\..\windows\server-install\'+$name)))
    Check ((Get-FileHash -LiteralPath (Join-Path $ops $name) -Algorithm SHA256).Hash-ceq(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash) ('Packaged latest source exact: '+$name)
}
Check ($null-ne(Get-Command Resolve-SetupAccountSid -ErrorAction Stop)) 'Packaged reset loads all identity dependencies'
if($Edition-cin@('04','05')){
    . (Join-Path $ops 'RackClick.Setup.Namespace.ps1')
    Check ($null-ne(Get-Command Get-SetupNamespacePlan -ErrorAction Stop)) 'Packaged orphan recovery module loads'
    $entryText=[IO.File]::ReadAllText($launcher)
    Check ($entryText.Contains('$plan=Get-SetupNamespacePlan')-and$entryText.Contains('Invoke-SetupNamespacePlan -Plan')-and-not$entryText.Contains('$plan=Get-SetupResetPlan')) 'Packaged main path uses namespace recovery rather than marker-dependent retirement'
}
if($Edition-ceq'05'){
    Check ($null-ne(Get-Command Get-SetupHostCompatibility -ErrorAction Stop)) 'Packaged host compatibility helper loads without running checks'
    Check ($entryText.IndexOf('$hostCheck=Get-SetupHostCompatibility')-lt$entryText.IndexOf('$plan=Get-SetupNamespacePlan')-and$entryText.Contains('setup_domain_controller_not_supported')) 'Packaged bootstrap checks and explains DC rejection before recovery'
}
Reject {Expand-CleanVerifiedPayload $inner ('0'*64) (Join-Path $fixture 'wrong')} 'Corrupt or incorrect inner hash cannot create a new stage'
Reject {Expand-CleanVerifiedPayload $inner $script:PayloadSha256 $stage} 'Existing full stage cannot be reused or overwritten'
$extra=Join-Path $stage 'unexpected.txt';[IO.File]::WriteAllText($extra,'fixture')
Reject {Assert-SetupPayload $stage} 'Extra payload file still rejected'
# This exact test-owned file was created just above; no recursive removal.
if([IO.Path]::GetDirectoryName($extra)-cne$stage){throw 'fixture_binding_lost'};[IO.File]::Delete($extra)
$manifest=Join-Path $stage 'payload.json';$casePath=Join-Path $stage 'PAYLOAD.JSON';[IO.File]::Move($manifest,($manifest+'.case'));[IO.File]::Move(($manifest+'.case'),$casePath)
$null=Assert-SetupPayload $stage;$checks.Add('Manifest filename casing accepted without relaxing inventory')
$mutable=Join-Path $ops 'RackClick.Setup.Reset.ps1';[IO.File]::AppendAllText($mutable,"`r`n# deliberately altered fixture")
Reject {Assert-SetupPayload $stage} 'Altered known source rejected by packaged manifest'
$result=[ordered]@{valid=$true;passed=$checks.Count;checks=@($checks.ToArray());archiveSha256=$ExpectedSha256;payloadSha256=$script:PayloadSha256;fixtureRoot=$fixture;environment='Windows PowerShell5.1 x64, unprivileged full release extraction';elevatedOperationsExecuted=0;cleanupExecuted=$false;sqlExecuted=$false;productionAclCreationSubstituted=$true}
if($OutputPath){[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath),($result|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 6 -Compress
