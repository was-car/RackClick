#requires -Version 5.1
param([string]$OutputPath='')
$ErrorActionPreference='Stop'
$source=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\windows\server-reset\Start-RackClickCleanInstall.ps1'))
. $source -FunctionsOnly
$script:verificationFixture=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot ('..\..\..\.local\verification-entry-fixture-'+[guid]::NewGuid().ToString('N'))))
$null=[IO.Directory]::CreateDirectory($script:verificationFixture)
$tokens=$null;$parseErrors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$parseErrors)
$definition=$ast.Find({param($node) $node-is[Management.Automation.Language.FunctionDefinitionAst]-and$node.Name-ceq'New-CleanVerificationEntry'},$true).Extent.Text.Replace('function New-CleanVerificationEntry(', 'function New-TestVerificationEntry(').Replace("[Environment]::GetFolderPath('Desktop')", '$script:verificationFixture')
# Only Desktop resolution is substituted. Never execute a real UAC process.
Invoke-Expression $definition
$verifyScript="C:\RackClick_SVR\.local\a user's fixture\Show-RackClickInstalledServer.ps1"
$cmdPath=New-TestVerificationEntry $verifyScript
$content=[IO.File]::ReadAllText($cmdPath)
$encoded=[regex]::Match($content,'-EncodedCommand ([A-Za-z0-9+/=]+)').Groups[1].Value
$decoded=[Text.Encoding]::Unicode.GetString([Convert]::FromBase64String($encoded))
$tokens=$null;$parseErrors=$null
$null=[Management.Automation.Language.Parser]::ParseInput($decoded,[ref]$tokens,[ref]$parseErrors)
if(@($parseErrors).Count){throw 'Generated verification command does not parse'}
function Start-Process {param($FilePath,$ArgumentList,$Verb) $script:captured=@{FilePath=$FilePath;ArgumentList=$ArgumentList;Verb=$Verb}}
Invoke-Expression $decoded
if($script:captured.Verb-cne'RunAs'-or$script:captured.ArgumentList[5]-cne('"'+$verifyScript+'"')-or$script:captured.ArgumentList[-1]-cne'-VerifyInstallation'){throw 'Generated verification command lost quoting or elevation'}
$result=@{valid=$true;passed=3;environment='Windows PowerShell5.1 x64; own fixture; Desktop and process launch boundaries substituted';checks=@('Actual generated CMD written only in own fixture','Encoded verification command parses with space and apostrophe in path','Decoded command requests RunAs with exact quoted script and VerifyInstallation; no launch');fixture=$script:verificationFixture;desktopFilesCreated=0;privilegedOperationsExecuted=0}
if($OutputPath){[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath),($result|ConvertTo-Json -Depth 4),(New-Object Text.UTF8Encoding($false)))}
$result|ConvertTo-Json -Depth 4 -Compress
