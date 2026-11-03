#requires -Version 5.1
param([Parameter(Mandatory=$true)][string]$BundlePath,
      [Parameter(Mandatory=$true)][string]$ExpectedBundleSha256,
      [Parameter(Mandatory=$true)][string]$LabRoot,
      [Parameter(Mandatory=$true)][int]$PostgresPort,
      [Parameter(Mandatory=$true)][int]$HttpPort)
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules'
$workspace=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$allowed=[IO.Path]::GetFullPath((Join-Path $workspace '.local\sql-integracion-12'))+'\'
$root=[IO.Path]::GetFullPath($LabRoot)
if(-not $root.StartsWith($allowed,[StringComparison]::OrdinalIgnoreCase)-or(Test-Path -LiteralPath $root)){
    throw 'New isolated SQL lab path required.'
}
if((Get-FileHash -LiteralPath $BundlePath -Algorithm SHA256).Hash -ine $ExpectedBundleSha256){throw 'Bundle hash mismatch.'}
function New-LabPrivateDirectory([string]$Path){
    $directory=[IO.Directory]::CreateDirectory($Path)
    $acl=New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true,$false)
    $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
    $acl.SetOwner($sid)
    foreach($principal in @($sid,(New-Object Security.Principal.SecurityIdentifier('S-1-5-18')))){
        $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($principal,'FullControl','ContainerInherit,ObjectInherit','None','Allow')))
    }
    $directory.SetAccessControl($acl)
    return $directory.FullName
}
$null=New-LabPrivateDirectory $root
$operators=New-LabPrivateDirectory (Join-Path $root 'operators')
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip=[IO.Compression.ZipFile]::OpenRead($BundlePath)
try{
    $entries=@($zip.Entries|Where-Object {$_.FullName.StartsWith('operators/',[StringComparison]::Ordinal)})
    if($entries.Count-ne26){throw 'Unexpected operator count.'}
    foreach($entry in $entries){
        $leaf=$entry.FullName.Substring(10)
        if($leaf -cnotmatch '^[A-Za-z0-9.-]+\.ps1$'){throw 'Unexpected operator path.'}
        [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,(Join-Path $operators $leaf),$false)
    }
}finally{$zip.Dispose()}
$installer=Join-Path $operators 'Install-RackClickOfflineBundle.ps1'
$output=& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $installer `
    -ArchivePath $BundlePath -ExpectedArchiveSha256 $ExpectedBundleSha256 `
    -DestinationPath (Join-Path $root 'installation') -PostgresPort $PostgresPort -HttpPort $HttpPort `
    -BootstrapUser 'sql-bundle-synthetic' -SystemhausName 'SQL bundle synthetic'
$exitCode=$LASTEXITCODE
$report=($output -join "`n")|ConvertFrom-Json
if($exitCode-ne0-or-not $report.valid-or$report.code-cne'installation_prepared'){throw ('Preparation failed: '+$report.code)}
$instancePath=Join-Path $root 'installation\deployment\instance'
$manifest=Get-Content -LiteralPath (Join-Path $instancePath 'instance.json') -Raw|ConvertFrom-Json
$private=@(Get-ChildItem -LiteralPath (Join-Path $instancePath 'private') -File|ForEach-Object {$_.Name}|Sort-Object)
if($manifest.schemaVersion-ne3-or$manifest.backupRole-cne('rc_backup_'+$manifest.id.Replace('-',''))){throw 'Minimal SQL format was not selected.'}
if(($private -join ',')-cne'admin-login.json,backup-password.dpapi.json,backup-profile.json,runtime.json'){throw 'Unexpected private inventory.'}
if(Test-Path -LiteralPath (Join-Path $instancePath 'pgdata\postmaster.pid')){throw 'PostgreSQL left running.'}
$pending=@(Get-ChildItem -LiteralPath (Join-Path $instancePath 'logs') -Filter request.json -Recurse -File|
    Where-Object {(Get-Content -LiteralPath $_.FullName -Raw|ConvertFrom-Json).schemaVersion-eq2})
if($pending.Count-ne0){throw 'A protected provisioning request remains.'}
[ordered]@{valid=$true;code='sql_bundle_minimal_prepared';installationCode=$report.code;
    bundleSha256=$ExpectedBundleSha256;applicationSha256=$report.applicationManifestSha256;
    instanceSchema=$manifest.schemaVersion;privateFiles=$private;pendingProtectedRequests=$pending.Count;
    postgresStopped=$true;operatorCount=$entries.Count;windowsServicesChanged=0;rootStoreChanged=0;
    actualServiceIdentityTested=$false}|ConvertTo-Json -Depth 4 -Compress
