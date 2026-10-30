#requires -Version 5.1
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\..\windows\server-install\RackClick.Setup.ps1')
. (Join-Path $PSScriptRoot '..\..\windows\server-install\RackClick.Setup.Recovery.ps1')
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('RackClick-Recovery-Input-'+[guid]::NewGuid().ToString('N'))
$source=Join-Path $fixture 'source';$null=[IO.Directory]::CreateDirectory($source)
$dump=Join-Path $source 'data.dump';[IO.File]::WriteAllBytes($dump,[Text.Encoding]::ASCII.GetBytes('PGDMP-fixture-only-not-a-restorable-database'))
$manifestPath=Join-Path $source 'manifest.json'
$manifest=@{schemaVersion=1;kind='RackClickDatabaseBackup';postgresVersion='17.11';format='custom';dumpFile='data.dump';dumpBytes=(Get-Item -LiteralPath $dump).Length;dumpSha256=(Get-FileHash -LiteralPath $dump).Hash.ToLowerInvariant();createdUtc=[DateTime]::UtcNow.ToString('o')}
Write-SetupJson $manifestPath $manifest;$hash=(Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant()
$target=Join-Path $fixture 'target';$answer=Copy-SetupRecoveryInput $source $hash $target
if($answer-cne$target-or(Get-FileHash -LiteralPath (Join-Path $target 'manifest.json')).Hash.ToLowerInvariant()-cne$hash){throw 'copy did not preserve bytes'}
$passed=1
function Expect-RecoveryRejection([scriptblock]$Action){$failed=$false;try{&$Action|Out-Null}catch{$failed=$true};if(-not$failed){throw 'invalid recovery input accepted'}}
Expect-RecoveryRejection {Copy-SetupRecoveryInput $source $hash $target};$passed++
Expect-RecoveryRejection {Copy-SetupRecoveryInput $source ('0'*64) (Join-Path $fixture 'wrong-hash')};$passed++
if(Test-Path -LiteralPath (Join-Path $fixture 'wrong-hash')){throw 'destination created before hash validation'};$passed++
[IO.File]::WriteAllText((Join-Path $source 'INCOMPLETE.json'),'{}')
Expect-RecoveryRejection {Copy-SetupRecoveryInput $source $hash (Join-Path $fixture 'extra-file')};$passed++
[IO.File]::Delete((Join-Path $source 'INCOMPLETE.json'))
$manifest.dumpFile='..\outside.dump';Write-SetupJson $manifestPath $manifest;$hash=(Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant()
Expect-RecoveryRejection {Copy-SetupRecoveryInput $source $hash (Join-Path $fixture 'traversal')};$passed++
$manifest.dumpFile='data.dump';$manifest.dumpSha256='0'*64;Write-SetupJson $manifestPath $manifest;$hash=(Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant()
Expect-RecoveryRejection {Copy-SetupRecoveryInput $source $hash (Join-Path $fixture 'dump-mismatch')};$passed++
@{valid=$true;checks=$passed;scope='Recovery staging policy and file copy; SQL Restore is tested separately';fixture=$fixture;elevatedOperations=0}|ConvertTo-Json -Compress
