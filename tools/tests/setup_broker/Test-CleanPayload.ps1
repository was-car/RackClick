#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\..\windows\server-reset\Start-RackClickCleanInstall.ps1') -FunctionsOnly
Add-Type -AssemblyName System.IO.Compression
$checks=New-Object Collections.Generic.List[string]
function Check($Value,[string]$Name){if(-not$Value){throw $Name};$checks.Add($Name)}
function Reject([scriptblock]$Action,[string]$Name){$rejected=$false;try{&$Action|Out-Null}catch{$rejected=$true};Check $rejected $Name}
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('RackClick-CleanFixture-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($fixture)
# The production directory owner is Administrators/SYSTEM. These unprivileged
# extraction tests substitute ONLY creation of the test-owned fresh directory.
function New-CleanPrivateDirectory([string]$Path){Assert-CleanLocalPath $Path;if(Test-Path -LiteralPath $Path){throw 'clean_destination_exists'};$null=[IO.Directory]::CreateDirectory($Path);return $Path}
function MakeArchive([string[]]$Names,[int]$Attributes=0){
    $path=Join-Path $fixture ([guid]::NewGuid().ToString('N')+'.zip')
    $file=[IO.File]::Open($path,'CreateNew','Write','None');try{$zip=New-Object IO.Compression.ZipArchive($file,[IO.Compression.ZipArchiveMode]::Create,$true);try{foreach($name in $Names){$entry=$zip.CreateEntry($name);$entry.ExternalAttributes=$Attributes;$stream=$entry.Open();try{$bytes=[Text.Encoding]::UTF8.GetBytes('fixture, not application data');$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}}}finally{$zip.Dispose()}}finally{$file.Dispose()}
    return $path
}
$source=MakeArchive @('RackClick-Instalador/payload.json','RackClick-Instalador/operators/a.ps1')
$hash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
$target=Join-Path $fixture 'new';$result=Expand-CleanVerifiedPayload $source $hash $target
Check ($result.valid-and$result.files-eq2) 'Valid fixed hash archive extracted to fresh tree'
Check ([IO.File]::ReadAllText((Join-Path $target 'operators\a.ps1'))-ceq'fixture, not application data') 'Extracted bytes preserved'
Reject {Expand-CleanVerifiedPayload $source $hash $target} 'Existing destination never overwritten'
Reject {Expand-CleanVerifiedPayload $source ('0'*64) (Join-Path $fixture 'wrong')} 'Wrong hash rejected'
Check (-not(Test-Path -LiteralPath (Join-Path $fixture 'wrong'))) 'Wrong hash creates no destination'
Reject {Assert-CleanLocalPath '\\server\share\file.zip'} 'UNC rejected'
Reject {Assert-CleanLocalPath ($fixture+'\..\other')} 'Noncanonical parent path rejected'
$bad=@('RackClick-Instalador/../escape','Other/file','RackClick-Instalador/a\b','RackClick-Instalador/a.','RackClick-Instalador/a /b','RackClick-Instalador/CON.txt','RackClick-Instalador/a//b','RackClick-Instalador//absolute','RackClick-Instalador/a:b','RackClick-Instalador/')
foreach($name in $bad){$zipPath=MakeArchive @($name);$sha=(Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant();$dest=Join-Path $fixture ([guid]::NewGuid().ToString('N'));Reject {Expand-CleanVerifiedPayload $zipPath $sha $dest} ('Invalid ZIP member rejected: '+$name);Check (-not(Test-Path -LiteralPath $dest)) 'Invalid ZIP rejected before creating destination'}
$dup=MakeArchive @('RackClick-Instalador/A','RackClick-Instalador/a');$sha=(Get-FileHash -LiteralPath $dup -Algorithm SHA256).Hash.ToLowerInvariant()
Reject {Expand-CleanVerifiedPayload $dup $sha (Join-Path $fixture 'dup')} 'Case alias duplicate rejected'
$sym=MakeArchive @('RackClick-Instalador/link') (-1610612736);$sha=(Get-FileHash -LiteralPath $sym -Algorithm SHA256).Hash.ToLowerInvariant()
Reject {Expand-CleanVerifiedPayload $sym $sha (Join-Path $fixture 'link')} 'Unix special file rejected'
# Import exactly the production dependency set, not mocked identity resolution.
$ops=Join-Path $PSScriptRoot '..\..\windows\server-install'
. (Join-Path $ops 'RackClick.Setup.ps1');. (Join-Path $ops 'RackClick.Setup.Security.ps1');. (Join-Path $ops 'RackClick.Setup.Lifecycle.ps1');. (Join-Path $ops 'RackClick.Setup.Reset.ps1')
Check ($null-ne(Get-Command Resolve-SetupAccountSid -ErrorAction Stop)) 'Reset production dependency resolves account SID without mocks'
$acl=New-Object Security.AccessControl.DirectorySecurity;$acl.SetSecurityDescriptorSddlForm('O:BAG:SYD:P(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)(A;;FRFX;;;BU)')
$user=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])|Where-Object{$_.IdentityReference.Value-ceq'S-1-5-32-545'})
Check ($user.Count-eq1-and$user[0].InheritanceFlags-eq'None'-and([int]$user[0].FileSystemRights-band0xD0156)-eq0) 'Common ancestor Users RX is direct and cannot grant child private data access'
$record=@{valid=$true;passed=$checks.Count;checks=@($checks.ToArray());environment='Windows PowerShell 5.1, unprivileged own fixture';fixturePath=$fixture;elevatedInstallExecuted=$false;creationAclSubstitutedForOwnFixture=$true}
if($OutputPath){[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath),($record|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))}
$record|ConvertTo-Json -Depth 6
