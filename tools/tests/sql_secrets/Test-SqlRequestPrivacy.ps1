#requires -Version 5.1
param([string]$InstancePath)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$project=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$root=[IO.Path]::GetFullPath($InstancePath)
if(-not$root.StartsWith((Join-Path $project '.local\sql-recovery-labs')+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'only_owned_recovery_fixture_allowed'}
. (Join-Path $project 'tools/windows/RackClick.Instance.ps1')
$m=[IO.File]::ReadAllText((Join-Path $root 'instance.json'))|ConvertFrom-Json
$passwords=@()
foreach($name in @('backup-profile.json','cluster-profile.json')){
    $profile=Read-BackupProfile (Join-Path $root ('private\'+$name));$passwords+=,$profile.password
}
$file=Join-Path $root ('sql-security\'+$m.id+'\sql-secrets\runtime.bin')
$bytes=[IO.File]::ReadAllBytes($file)
try{$connection=Unprotect-SqlRuntimeConnection $bytes $m.id ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value) $m.database $m.runtime}finally{[Array]::Clear($bytes,0,$bytes.Length)}
$builder=New-Object Data.Common.DbConnectionStringBuilder;$builder.set_ConnectionString($connection);$passwords+=,[string]$builder['Password'];$builder.Clear();$connection=$null
$matches=0;$files=0
foreach($folder in @('private','logs','sql-security')){
    foreach($item in @(Get-ChildItem -LiteralPath (Join-Path $root $folder) -File -Recurse)){
        $files++
        $data=[IO.File]::ReadAllBytes($item.FullName)
        foreach($encoding in @([Text.Encoding]::UTF8,[Text.Encoding]::Unicode)){
            $text=$encoding.GetString($data)
            foreach($password in $passwords){if($text.Contains($password)){$matches++}}
        }
    }
}
@{valid=($matches-eq0);code=$(if($matches-eq0){'no_sql_plaintext_in_fixture_files'}else{'sql_plaintext_retained'});filesChecked=$files;plaintextMatches=$matches;secretValuesIncluded=$false}|ConvertTo-Json -Compress
if($matches-ne0){exit 1}
