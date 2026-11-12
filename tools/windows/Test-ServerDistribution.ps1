#requires -Version 5.1
<# Read-only integrity inventory of schema9/10 and pinned schema11/12/13/14/15/43 artifacts.
   ExpectedManifestSha256 must come from the approved release record, not this file.
   Does not use manifest paths, execute binaries, install or access a QA profile.
#>
[CmdletBinding()]
param([string]$ManifestPath='', [string]$ExpectedManifestSha256='', [string]$ServerPath='', [string]$FrontendPath='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'Test-RuntimePrerequisites.ps1')

function Stop-DistributionCheck {
    param([string]$Code,[int]$ExitCode=2)
    $errorValue=New-Object System.InvalidOperationException($Code)
    $errorValue.Data['checkCode']=$Code; $errorValue.Data['checkExit']=$ExitCode
    throw $errorValue
}

function Assert-LocalDistributionPath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path) -or $Path -notmatch '^[A-Za-z]:[\\/]' -or $Path.Substring(2).Contains(':')) {
        Stop-DistributionCheck 'input_invalid'
    }
    foreach ($segment in $Path.Substring(3).Split([char[]]@('\','/'))) {
        if ($segment -in @('.','..') -or $segment.EndsWith('.') -or $segment.EndsWith(' ')) { Stop-DistributionCheck 'input_invalid' }
    }
    if ((New-Object IO.DriveInfo($Path.Substring(0,3))).DriveType -eq [IO.DriveType]::Network) { Stop-DistributionCheck 'input_invalid' }
}

function Assert-NoDistributionReparse {
    param([string]$Path)
    $item=Get-Item -LiteralPath $Path -Force
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { Stop-DistributionCheck 'reparse_path_rejected' }
        if ($item -is [IO.FileInfo]) { $item=$item.Directory } else { $item=$item.Parent }
    }
}

function Get-DistributionFileInventory {
    param([string]$Root)
    $result=New-Object 'System.Collections.Generic.Dictionary[string,string]' ([StringComparer]::OrdinalIgnoreCase)
    $pending=New-Object 'System.Collections.Generic.Stack[System.IO.DirectoryInfo]'
    $pending.Push((New-Object IO.DirectoryInfo($Root)))
    while ($pending.Count -ne 0) {
        $directory=$pending.Pop()
        foreach ($item in $directory.GetFileSystemInfos()) {
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { Stop-DistributionCheck 'reparse_path_rejected' }
            if (($item.Attributes -band [IO.FileAttributes]::Directory) -ne 0) { $pending.Push($item); continue }
            $relative=$item.FullName.Substring($Root.Length).TrimStart([char]'\').Replace('\','/')
            if ($result.ContainsKey($relative)) { Stop-DistributionCheck 'file_name_collision' }
            $result.Add($relative,$item.FullName)
        }
    }
    return ,$result
}

function Get-DeclaredDistribution {
    param($Value,[int]$ExpectedCount=18)
    if ($Value -isnot [Management.Automation.PSCustomObject]) { Stop-DistributionCheck 'manifest_invalid' }
    $result=New-Object 'System.Collections.Generic.Dictionary[string,string]' ([StringComparer]::OrdinalIgnoreCase)
    foreach ($property in $Value.PSObject.Properties) {
        $name=$property.Name
        if ($name -notmatch '^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$') { Stop-DistributionCheck 'manifest_path_unsafe' }
        foreach ($segment in $name.Split('/')) {
            if ($segment -in @('.','..') -or $segment.EndsWith('.') -or $segment -match '^(?i:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\..*)?$') { Stop-DistributionCheck 'manifest_path_unsafe' }
        }
        if ($result.ContainsKey($name)) { Stop-DistributionCheck 'manifest_name_collision' }
        if ($property.Value -isnot [string] -or $property.Value -notmatch '^[a-fA-F0-9]{64}$') { Stop-DistributionCheck 'manifest_invalid' }
        $result.Add($name,$property.Value.ToLowerInvariant())
    }
    if ($result.Count -ne $ExpectedCount) { Stop-DistributionCheck 'manifest_distribution_unsupported' }
    return ,$result
}

# Perfil 14 cerrado (docs/DISTRIBUCION14-PERFIL.json): 10 archivos de aplicación y 14 SQL, sin apphost.
$profile14Server=@('Npgsql.dll','Otp.NET.dll','RackClick.Domain.dll','RackClick.Domain.pdb','RackClick.Server.deps.json','RackClick.Server.dll','RackClick.Server.pdb','RackClick.Server.runtimeconfig.json','RackClick.Server.staticwebassets.endpoints.json','web.config')+@('database/001-foundation.sql','database/002-inventory.sql','database/003-operation-cancellation.sql','database/004-session-identity.sql','database/005-audit-context.sql','database/006-audit-state-intent.sql','database/007-audit-context-families.sql','database/008-user-catalog-favorites.sql','database/009-private-device-templates.sql','database/010-customer-shared-device-templates.sql','database/011-user-preferences.sql','database/012-user-port-colors.sql','database/013-user-category-colors.sql','database/014-mfa.sql')
$profile15Server=$profile14Server+@('database/015-mfa-account-policy.sql')
# Closed schema43 application candidate; operator installation is still separate.
$profile43Sql=@('database/001-foundation.sql','database/002-inventory.sql','database/003-operation-cancellation.sql','database/004-session-identity.sql','database/005-audit-context.sql','database/006-audit-state-intent.sql','database/007-audit-context-families.sql','database/008-user-catalog-favorites.sql','database/009-private-device-templates.sql','database/010-customer-shared-device-templates.sql','database/011-user-preferences.sql','database/012-user-port-colors.sql','database/013-user-category-colors.sql','database/014-mfa.sql','database/015-mfa-account-policy.sql','database/016-hardware-mounting.sql','database/017-hardware-catalog.sql','database/018-commercial-hardware.sql','database/019-aruba-hardware.sql','database/020-fortinet-hardware.sql','database/021-synology-hardware.sql','database/022-diskstation-hardware.sql','database/023-qnap-hardware.sql','database/024-batch50-hardware.sql','database/025-batch50b-hardware.sql','database/026-batch100-hardware.sql','database/027-batch100b-hardware.sql','database/028-batch100c-hardware.sql','database/029-selected506a-hardware.sql','database/030-selected506b-hardware.sql','database/031-selected506c-hardware.sql','database/032-selected506d-hardware.sql','database/033-selected506e-hardware.sql','database/034-selected506f-hardware.sql','database/035-selected506g-hardware.sql','database/036-physical-media.sql','database/037-selected506h-hardware.sql','database/038-selected506i-hardware.sql','database/039-selected506j-hardware.sql','database/040-hardware-families.sql','database/041-selected506k-hardware.sql','database/042-hardware-family-l.sql','database/043-selected506l-hardware.sql')
$profile43Server=@($profile14Server | Where-Object {-not $_.StartsWith('database/')})+$profile43Sql
$profile45Sql=$profile43Sql+@('database/044-german-cpe-hardware.sql','database/045-german-repeaters-hardware.sql')
$profile45Server=@($profile14Server | Where-Object {-not $_.StartsWith('database/')})+$profile45Sql
$profile48Sql=$profile45Sql+@('database/046-mfa-key-rotation.sql','database/047-mfa-loss-reset.sql','database/048-mfa-loss-startup.sql')
$profile48Server=@($profile14Server | Where-Object {-not $_.StartsWith('database/')})+$profile48Sql
if ($MyInvocation.InvocationName -eq '.') { return }
$report=[ordered]@{schemaVersion=1;valid=$false;exitCode=2;code='input_invalid';manifestSha256='';verifiedFiles=0;serverFiles=0;frontendFiles=0;scope='Artifact integrity only; not installation, authenticity or application acceptance'}
try {
    foreach ($path in @($ManifestPath,$ServerPath,$FrontendPath)) { Assert-LocalDistributionPath $path }
    if ($ExpectedManifestSha256 -notmatch '^[a-fA-F0-9]{64}$') { Stop-DistributionCheck 'input_invalid' }
    if (-not [IO.File]::Exists($ManifestPath)) { Stop-DistributionCheck 'manifest_missing' }
    Assert-NoDistributionReparse $ManifestPath
    # Keep the manifest read-locked through digest and parse, so both use the same bytes.
    $manifestLock=[IO.File]::Open($ManifestPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        $digest=Get-RuntimeConfigDigest $ManifestPath
        if ($digest -ne $ExpectedManifestSha256.ToLowerInvariant()) { Stop-DistributionCheck 'manifest_untrusted' }
        $report.manifestSha256=$digest
        try { $manifest=[IO.File]::ReadAllText($ManifestPath) | ConvertFrom-Json }
        catch { Stop-DistributionCheck 'manifest_invalid' }
    } finally { $manifestLock.Dispose() }
    if ($manifest.schema -isnot [int] -or $manifest.schema -notin @(9,10,11,12,13,14,15,43,45,48) -or (($manifest.distributions.PSObject.Properties.Name | Sort-Object) -join ',') -ne 'frontend,server') { Stop-DistributionCheck 'manifest_distribution_unsupported' }
    if ($manifest.schema -eq 11 -and $digest -cnotin @('f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd','511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5','1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09')) {Stop-DistributionCheck 'manifest_distribution_unsupported'}
    if ($manifest.schema -eq 12 -and $digest -cne 'b589609154fed1567106ef0865972155258f0f5474128c73076f4697d43b8bda') {Stop-DistributionCheck 'manifest_distribution_unsupported'}
    if ($manifest.schema -eq 13 -and $digest -cnotin @('c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c','dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b','38bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6','55bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6')) {Stop-DistributionCheck 'manifest_distribution_unsupported'}
    # 2ec91056 es la candidata M3 congelada (DLL f11a689e…, sin la invalidación de D14-05). e9c58c0c es la candidata D14-05 limpia (DLL 19c94d4e…).
    if ($manifest.schema -eq 14 -and $digest -cnotin @('2ec9105661db0f5c9a97d58e2a7f44e69bfd7e1903493b72f0fc57cc94c4b71a','e9c58c0c67500afc09c1ac979a7433830c96f94c2a2e4501d81286796d65d74d')) {Stop-DistributionCheck 'manifest_distribution_unsupported'}
    # Candidata15 congelada: un manifiesto distinto, aunque declare15, sigue rechazado.
    if ($manifest.schema -eq 15 -and $digest -cne '294b61577ed7aa8fe68ddb1ecd6c4f11a20b4f03935c11a22404009aec6a00fb') {Stop-DistributionCheck 'manifest_distribution_unsupported'}
    if ($manifest.schema -eq 43 -and $digest -cnotin @('eb274f1f82deb9936c69214fae07e4188275063cf35ec775fe41d560a1806830','d352c04381cd4f1954aa43735e540970b295f231106560c5c9880c7ee1dc78db','29685419d0746df89777a5da72d25f5b7ac0e571e30decec1888787fe5f0f950')) {Stop-DistributionCheck 'manifest_distribution_unsupported'}
    if ($digest -ceq '29685419d0746df89777a5da72d25f5b7ac0e571e30decec1888787fe5f0f950' -and $manifest.profileId -cne 'schema43-sql-protected-01') {Stop-DistributionCheck 'manifest_distribution_unsupported'}
    if ($manifest.schema -eq 45) {
        $profiles45=@{
            '528a03d2efc939d1cea631b1caa9f3e6a445e44257fa757f87a95691acfb6933'='schema45-sql-protected-01'
            'a2ec1c7d3570593297a63b672ee485489e49ed0658ff49f6d2ef585803f6a8af'='schema45-mfa-store-01'
        }
        if (-not $profiles45.ContainsKey($digest) -or $manifest.profileId -cne $profiles45[$digest]) {Stop-DistributionCheck 'manifest_distribution_unsupported'}
    }
    if ($manifest.schema -eq 48) {
        $profiles48=@{
            'a7b622f917404bbe3ea2560e1fcc2dad008910395c6ab5fa8bc6875be2c88112'='schema48-maintenance-01'
            'f7b971f31dd5f424dbce35c9c18a4c6c75c8968f31d10c5df8bbfe215e5b8a53'='schema48-admin-data-01'
        }
        if (-not $profiles48.ContainsKey($digest) -or $manifest.profileId -cne $profiles48[$digest]) {Stop-DistributionCheck 'manifest_distribution_unsupported'}
    }
    $serverCount=if ($manifest.schema -eq 48) {$profile48Server.Count} elseif ($manifest.schema -eq 45) {$profile45Server.Count} elseif ($manifest.schema -eq 43) {$profile43Server.Count} elseif ($manifest.schema -eq 15) {$profile15Server.Count} elseif ($manifest.schema -eq 14) {$profile14Server.Count} else {9+$manifest.schema}
    $declared=@{server=(Get-DeclaredDistribution $manifest.distributions.server $serverCount);frontend=(Get-DeclaredDistribution $manifest.distributions.frontend)}
    foreach ($name in @('RackClick.Server.dll','RackClick.Server.runtimeconfig.json','RackClick.Server.deps.json','Npgsql.dll')) {
        if (-not $declared.server.ContainsKey($name)) { Stop-DistributionCheck 'manifest_distribution_unsupported' }
    }
    if ($manifest.schema -eq 14) { foreach ($name in $declared.server.Keys) { if ($profile14Server -cnotcontains $name) { Stop-DistributionCheck 'manifest_distribution_unsupported' } } }
    if ($manifest.schema -eq 15) { foreach ($name in $declared.server.Keys) { if ($profile15Server -cnotcontains $name) { Stop-DistributionCheck 'manifest_distribution_unsupported' } } }
    if ($manifest.schema -eq 43) { foreach ($name in $declared.server.Keys) { if ($profile43Server -cnotcontains $name) { Stop-DistributionCheck 'manifest_distribution_unsupported' } } }
    if ($manifest.schema -eq 45) { foreach ($name in $declared.server.Keys) { if ($profile45Server -cnotcontains $name) { Stop-DistributionCheck 'manifest_distribution_unsupported' } } }
    if ($manifest.schema -eq 48) { foreach ($name in $declared.server.Keys) { if ($profile48Server -cnotcontains $name) { Stop-DistributionCheck 'manifest_distribution_unsupported' } } }
    foreach ($name in @('app.js','app.css','index.html')) {
        if (-not $declared.frontend.ContainsKey($name)) { Stop-DistributionCheck 'manifest_distribution_unsupported' }
    }
    $sql=@('001-foundation.sql','002-inventory.sql','003-operation-cancellation.sql','004-session-identity.sql','005-audit-context.sql','006-audit-state-intent.sql','007-audit-context-families.sql','008-user-catalog-favorites.sql','009-private-device-templates.sql')
    if ($manifest.schema -ge 10) {$sql+=@('010-customer-shared-device-templates.sql')}
    if ($manifest.schema -ge 11) {$sql+=@('011-user-preferences.sql')}
    if ($manifest.schema -ge 12) {$sql+=@('012-user-port-colors.sql')}
    if ($manifest.schema -eq 13) {$sql+=@('013-user-category-colors.sql')}
    if ($manifest.schema -ge 14) {$sql+=@('013-user-category-colors.sql','014-mfa.sql')}
    if ($manifest.schema -eq 15) {$sql+=@('015-mfa-account-policy.sql')}
    if ($manifest.schema -eq 43) {$sql=@($profile43Sql | ForEach-Object {$_.Substring(9)})}
    if ($manifest.schema -eq 45) {$sql=@($profile45Sql | ForEach-Object {$_.Substring(9)})}
    if ($manifest.schema -eq 48) {$sql=@($profile48Sql | ForEach-Object {$_.Substring(9)})}
    if (@($declared.server.Keys | Where-Object { $_.StartsWith('database/') }).Count -ne $manifest.schema) { Stop-DistributionCheck 'manifest_distribution_unsupported' }
    foreach ($name in $sql) { if (-not $declared.server.ContainsKey('database/'+$name)) { Stop-DistributionCheck 'manifest_distribution_unsupported' } }
    $roots=@{server=[IO.Path]::GetFullPath($ServerPath).TrimEnd([char]'\');frontend=[IO.Path]::GetFullPath($FrontendPath).TrimEnd([char]'\')}
    if ($roots.server.Length -le 2 -or $roots.frontend.Length -le 2) { Stop-DistributionCheck 'input_invalid' }
    if ($roots.server.Equals($roots.frontend,[StringComparison]::OrdinalIgnoreCase) -or $roots.server.StartsWith($roots.frontend+'\',[StringComparison]::OrdinalIgnoreCase) -or $roots.frontend.StartsWith($roots.server+'\',[StringComparison]::OrdinalIgnoreCase)) { Stop-DistributionCheck 'distribution_roots_overlap' }
    $inventories=@{}
    foreach ($kind in @('server','frontend')) {
        if (-not [IO.Directory]::Exists($roots[$kind])) { Stop-DistributionCheck 'distribution_directory_missing' 1 }
        Assert-NoDistributionReparse $roots[$kind]
        $inventories[$kind]=Get-DistributionFileInventory $roots[$kind]
    }
    foreach ($kind in @('server','frontend')) {
        $actual=$inventories[$kind];$expected=$declared[$kind]
        foreach ($name in $expected.Keys) { if (-not $actual.ContainsKey($name)) { Stop-DistributionCheck 'distribution_files_missing' 1 } }
        foreach ($name in $actual.Keys) { if (-not $expected.ContainsKey($name)) { Stop-DistributionCheck 'distribution_files_extra' 1 } }
        foreach ($name in $expected.Keys) {
            if ((Get-RuntimeConfigDigest $actual[$name]) -ne $expected[$name]) { Stop-DistributionCheck 'artifact_hash_mismatch' 1 }
            $report.verifiedFiles++
        }
    }
    # Early schema9 manifests predate aggregate fields; their exact tree/digests
    # still apply. Schema10/11/12/13 declare both totals, which must match actual bytes.
    $hasCount=$null -ne $manifest.PSObject.Properties['fileCount'];$hasBytes=$null -ne $manifest.PSObject.Properties['totalBytes']
    if (($manifest.schema -ge 10 -and (-not $hasCount -or -not $hasBytes)) -or
        ($hasCount -and $manifest.fileCount -ne $report.verifiedFiles) -or
        ($hasBytes -and $manifest.totalBytes -ne (@($inventories.server.Values)+@($inventories.frontend.Values)|ForEach-Object {(Get-Item -LiteralPath $_).Length}|Measure-Object -Sum).Sum)) {Stop-DistributionCheck 'manifest_totals_invalid'}
    $report.serverFiles=$serverCount;$report.frontendFiles=18;$report.valid=$true;$report.exitCode=0;$report.code='artifacts_verified';$report.schema=$manifest.schema
} catch {
    if ($_.Exception.Data.Contains('checkCode')) { $report.code=$_.Exception.Data['checkCode'];$report.exitCode=$_.Exception.Data['checkExit'] }
    else { $report.code='verification_failed' }
}
$report | ConvertTo-Json -Depth 5 -Compress
exit $report.exitCode
