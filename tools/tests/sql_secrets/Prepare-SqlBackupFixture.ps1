#requires -Version 5.1
param([string]$InputPath)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$project=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$v=[IO.File]::ReadAllText($InputPath)|ConvertFrom-Json
$PostgresBinPath=$v.bin
. (Join-Path $project 'tools/windows/RackClick.Backup.ps1')
$source=New-SqlProtectedBackupProfile (Join-Path $v.work 'source-profile') $v.sourceId $v.port $v.sourceDatabase $v.sourceUser $v.sourcePassword
$target=New-SqlProtectedBackupProfile (Join-Path $v.work 'target-profile') $v.targetId $v.port 'postgres' $v.targetUser $v.targetPassword
$reject=New-SqlProtectedBackupProfile (Join-Path $v.work 'wrong-context-profile') $v.rejectId $v.port 'postgres' $v.targetUser $v.targetPassword
# Only synthetic ciphertext is copied; the receiver must reject its foreign context.
[IO.File]::WriteAllBytes((Join-Path $v.work 'wrong-context-profile\password.dpapi.json'),[IO.File]::ReadAllBytes((Join-Path $v.work 'source-profile\password.dpapi.json')))
@{source=$source;target=$target;reject=$reject}|ConvertTo-Json -Compress
