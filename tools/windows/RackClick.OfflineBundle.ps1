#requires -Version 5.1
# Pure function definitions. No probes, imports, processes or filesystem writes on dot-source.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

function Stop-OfflineBundleCheck {
    param([string]$Code,[int]$ExitCode=2)
    $failure=New-Object InvalidOperationException($Code)
    $failure.Data['bundleCode']=$Code;$failure.Data['bundleExit']=$ExitCode
    throw $failure
}

function Assert-OfflineBundleKeys {
    param($Value,[string]$Keys)
    if ($Value -isnot [pscustomobject] -or ((@($Value.PSObject.Properties|ForEach-Object {$_.Name}|Sort-Object))-join ',') -cne $Keys) {Stop-OfflineBundleCheck 'manifest_schema_invalid'}
}

function Assert-OfflineBundleName {
    param([string]$Name)
    if ([string]::IsNullOrEmpty($Name) -or $Name.Length -gt 240 -or $Name -cmatch '[^\x20-\x7e]' -or
        $Name.Contains('\') -or $Name.Contains(':') -or $Name.StartsWith('/') -or $Name.EndsWith('/')) {Stop-OfflineBundleCheck 'entry_name_invalid'}
    foreach ($segment in $Name.Split('/')) {
        if ($segment.Length -eq 0 -or $segment -in @('.','..') -or $segment.EndsWith('.') -or $segment.EndsWith(' ') -or
            $segment.Contains('~') -or $segment.IndexOfAny([char[]]'<>"|?*') -ge 0 -or
            $segment -match '^(?i:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\..*)?$') {Stop-OfflineBundleCheck 'entry_name_invalid'}
    }
}

function Get-OfflineBundleLocalPath {
    param([string]$Path,[switch]$Ascii)
    if ([string]::IsNullOrWhiteSpace($Path) -or $Path -notmatch '^[A-Za-z]:[\\/]' -or $Path.Substring(2).Contains(':') -or
        ($Ascii -and $Path -match '[^\x20-\x7e]')) {Stop-OfflineBundleCheck 'path_invalid'}
    $tail=$Path.Substring(3).Replace('\','/').TrimEnd('/')
    # The archive's LOCAL path may contain Unicode. ZIP entry names remain ASCII
    # through Assert-OfflineBundleName; the technical destination opts into -Ascii.
    if ($tail.Length -eq 0 -or $tail.Length -gt 240) {Stop-OfflineBundleCheck 'path_invalid'}
    foreach ($segment in $tail.Split('/')) {
        if ($segment.Length -eq 0 -or $segment -in @('.','..') -or $segment.EndsWith('.') -or $segment.EndsWith(' ') -or
            $segment.Contains('~') -or $segment.IndexOfAny([IO.Path]::GetInvalidFileNameChars()) -ge 0 -or $segment -match '\p{Cc}' -or
            $segment -match '^(?i:CON|PRN|AUX|NUL|COM[0-9\u00b9\u00b2\u00b3]|LPT[0-9\u00b9\u00b2\u00b3])(?:\..*)?$') {Stop-OfflineBundleCheck 'path_invalid'}
    }
    $full=[IO.Path]::GetFullPath($Path).TrimEnd('\')
    if ((New-Object IO.DriveInfo($full.Substring(0,3))).DriveType -ne [IO.DriveType]::Fixed) {Stop-OfflineBundleCheck 'path_not_local_fixed'}
    return $full
}

function Assert-OfflineBundleNoReparse {
    param([string]$Path)
    $item=Get-Item -LiteralPath $Path -Force
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {Stop-OfflineBundleCheck 'reparse_rejected'}
        if ($item -is [IO.FileInfo]) {$item=$item.Directory} else {$item=$item.Parent}
    }
}

function Test-OfflineBundleOverlap {
    param([string]$First,[string]$Second)
    return $First.Equals($Second,[StringComparison]::OrdinalIgnoreCase) -or $First.StartsWith($Second+'\',[StringComparison]::OrdinalIgnoreCase) -or $Second.StartsWith($First+'\',[StringComparison]::OrdinalIgnoreCase)
}

function Get-OfflineBundleStreamDigest {
    param([IO.Stream]$Stream,[long]$ExpectedLength=-1,[IO.Stream]$Target=$null,[long]$Maximum=268435456)
    $algorithm=[Security.Cryptography.SHA256]::Create();$buffer=New-Object byte[] 65536;$total=0L
    try {
        while (($read=$Stream.Read($buffer,0,$buffer.Length)) -gt 0) {
            $total+=$read
            if ($total -gt $Maximum -or ($ExpectedLength -ge 0 -and $total -gt $ExpectedLength)) {Stop-OfflineBundleCheck 'entry_size_invalid'}
            $null=$algorithm.TransformBlock($buffer,0,$read,$buffer,0)
            if ($null -ne $Target) {$Target.Write($buffer,0,$read)}
        }
        if ($ExpectedLength -ge 0 -and $total -ne $ExpectedLength) {Stop-OfflineBundleCheck 'entry_size_invalid'}
        $null=$algorithm.TransformFinalBlock($buffer,0,0)
        return [BitConverter]::ToString($algorithm.Hash).Replace('-','').ToLowerInvariant()
    } finally {$algorithm.Dispose()}
}

function Read-OfflineBundleEntryJson {
    param($Entry,[long]$Maximum=8388608)
    if ($Entry.Length -le 0 -or $Entry.Length -gt $Maximum) {Stop-OfflineBundleCheck 'manifest_size_invalid'}
    $stream=$null;$memory=New-Object IO.MemoryStream
    try {
        $stream=$Entry.Open();$null=Get-OfflineBundleStreamDigest $stream $Entry.Length $memory $Maximum
        $utf8=New-Object Text.UTF8Encoding($false,$true)
        try {$value=$utf8.GetString($memory.ToArray())|ConvertFrom-Json} catch {Stop-OfflineBundleCheck 'manifest_json_invalid'}
        return $value
    } finally {if ($null -ne $stream) {$stream.Dispose()};$memory.Dispose()}
}

function Get-OfflineBundleOperatorNames {
    return @('Invoke-RackClickPrivateDeployment.ps1','New-RackClickDatabaseBackup.ps1','New-RackClickLabHttpsProfile.ps1',
        'New-RackClickLabInstance.ps1','New-RackClickPrivateDeployment.ps1','New-RackClickRecoveredInstance.ps1',
        'RackClick.Backup.ps1','RackClick.Deployment.ps1','RackClick.Https.ps1','RackClick.Instance.ps1',
        'RackClick.LaunchControl.ps1','RackClick.Process.Gate.ps1','RackClick.Process.ps1','RackClick.Stage.ps1',
        'Test-StagedDistribution.ps1','Restore-RackClickPrivateDeployment.ps1','Stage-ServerDistribution.ps1',
        'Start-RackClickLabInstance.ps1','Stop-RackClickLabInstance.ps1','Test-RackClickPrivateDeployment.ps1',
        'Test-RuntimePrerequisites.ps1','Test-ServerDistribution.ps1','RackClick.OfflineBundle.ps1',
        'Test-RackClickOfflineBundle.ps1','Install-RackClickOfflineBundle.ps1')
}

function Get-OfflineBundleApplicationProfile {
    param([string]$ManifestSha256)
    # Closed, reviewed profiles. The archive still requires its independent external hash.
    switch -CaseSensitive ($ManifestSha256) {
        'b7b26834ac5186792a01014b7221f4ba94940da19efafb84546ca635f868fa00' {return @{name='337';server=18;frontend=18;bytes=6578061L}}
        'cf51b03c80ddec460944295daf09705f3dbdec0cd83e054f5bfc6592fb081685' {return @{name='397';server=18;frontend=18;bytes=6653702L}}
        'c818294e27a40c94fe2ebf603709c94263820af1facca9a7d5c288cb70e8158e' {return @{name='532';server=18;frontend=18;bytes=6794984L}}
        '66426b3c4fdf8c75b8c1faae4572066754934000eb2567881d93407f4ae5e9f9' {return @{name='592';server=19;frontend=18;bytes=6939574L}}
        'f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd' {return @{name='712';server=20;frontend=18;bytes=7028507L}}
        '511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5' {return @{name='832';server=20;frontend=18;bytes=7108267L}}
        '1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09' {return @{name='849';server=20;frontend=18;bytes=7108622L}}
        'b589609154fed1567106ef0865972155258f0f5474128c73076f4697d43b8bda' {return @{name='969';server=21;frontend=18;bytes=7037914L}}
        'c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c' {return @{name='1089';server=22;frontend=18;bytes=7133395L}}
        'dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b' {return @{name='1209';server=22;frontend=18;bytes=7146303L}}
        '38bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6' {return @{name='1329';server=22;frontend=18;bytes=7148383L}}
        '55bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6' {return @{name='1449';server=22;frontend=18;bytes=7159235L}}
        '2ec9105661db0f5c9a97d58e2a7f44e69bfd7e1903493b72f0fc57cc94c4b71a' {return @{name='14';server=24;frontend=18;bytes=7263552L;metadata=@{'inventory.json'='9303ebd4d1e2075cbf144ae868ec10568b02f754eb4f3d95f33faffa91094086';'SHA256SUMS.txt'='47089172d9b7a13adb409b38289fc0ecee98866f0345810762de008e16b19b50'};notices=@{'licenses/Otp.NET-LICENSE.txt'='0bc32be0ce13330ba88d208548582a641f95b1f66bb19be91f5acc1436c52472'}}}
        'e9c58c0c67500afc09c1ac979a7433830c96f94c2a2e4501d81286796d65d74d' {return @{name='14';server=24;frontend=18;bytes=7489372L;metadata=@{'inventory.json'='9303ebd4d1e2075cbf144ae868ec10568b02f754eb4f3d95f33faffa91094086';'SHA256SUMS.txt'='932588056beb49fb1a7d1627b41a85829833f029f2429a0d695a5cb77c1bf31b'};notices=@{'licenses/Otp.NET-LICENSE.txt'='0bc32be0ce13330ba88d208548582a641f95b1f66bb19be91f5acc1436c52472'}}}
        default {Stop-OfflineBundleCheck 'application_pin_mismatch'}
    }
}

function Get-OfflineBundleExpectedSchema {
    param([hashtable]$Profile)
    # Un único lugar para el esquema esperado de cada perfil; lo usan la validación de diseño y la lectura del ZIP.
    if ($Profile.name -ceq '14') {return 14}
    if ($Profile.name -ceq '592') {return 10}
    if ($Profile.name -cin @('712','832','849')) {return 11}
    if ($Profile.name -ceq '969') {return 12}
    if ($Profile.name -cin @('1089','1209','1329','1449')) {return 13}
    return 9
}

function Assert-OfflineBundleLayout {
    param($Manifest,[hashtable]$Entries)
    Assert-OfflineBundleKeys $Manifest 'applicationManifestSha256,files,id,kind,platform,schemaVersion,versions'
    Assert-OfflineBundleKeys $Manifest.versions 'dotnetRuntime,postgresql,schema,vcRedist,vcRuntimeMinimum'
    foreach ($field in @('kind','platform','applicationManifestSha256')) {
        if ($Manifest.$field -isnot [string]) {Stop-OfflineBundleCheck 'manifest_schema_invalid'}
    }
    foreach ($field in @('dotnetRuntime','postgresql','vcRedist','vcRuntimeMinimum')) {
        if ($Manifest.versions.$field -isnot [string]) {Stop-OfflineBundleCheck 'manifest_schema_invalid'}
    }
    if ($Manifest.schemaVersion -isnot [int] -or $Manifest.schemaVersion -ne 1 -or $Manifest.kind -cne 'RackClickOfflineBundle' -or
        $Manifest.platform -cne 'win-x64' -or $Manifest.id -isnot [string] -or $Manifest.id -cnotmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$' -or
        $Manifest.versions.schema -isnot [int] -or $Manifest.versions.schema -notin @(9,10,11,12,13,14) -or
        $Manifest.versions.dotnetRuntime -cne '10.0.12' -or $Manifest.versions.postgresql -cne '17.11' -or
        $Manifest.versions.vcRedist -cne '14.51.36247.0' -or $Manifest.versions.vcRuntimeMinimum -cne '14.44.35211.0' -or
        $Manifest.files -isnot [pscustomobject]) {Stop-OfflineBundleCheck 'manifest_schema_invalid'}
    $profile=Get-OfflineBundleApplicationProfile $Manifest.applicationManifestSha256
    $expectedSchema=Get-OfflineBundleExpectedSchema $profile
    if ($Manifest.versions.schema -ne $expectedSchema) {Stop-OfflineBundleCheck 'application_schema_mismatch'}
    $files=@($Manifest.files.PSObject.Properties)
    if ($files.Count -ne $Entries.Count-1) {Stop-OfflineBundleCheck 'inventory_mismatch'}
    $operators=Get-OfflineBundleOperatorNames
    $docs=@('MANUAL-PAQUETE-WINDOWS-S1.md','CONSTRUIR-PAQUETE-WINDOWS-S1.md','OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md','RECUPERACION-DESPLIEGUE-WINDOWS-S1.md')
    $counts=@{server=0;frontend=0;operators=0;dotnet=0;postgresql=0;docs=0;licenses=0;manifest=0;prerequisites=0;metadata=0;notices=0};$applicationBytes=0L
    foreach ($file in $files) {
        $name=$file.Name;Assert-OfflineBundleName $name
        if ($name -ceq 'bundle.json' -or -not $Entries.ContainsKey($name) -or $Entries[$name].FullName -cne $name) {Stop-OfflineBundleCheck 'inventory_mismatch'}
        Assert-OfflineBundleKeys $file.Value 'bytes,sha256'
        if (($file.Value.bytes -isnot [int] -and $file.Value.bytes -isnot [long]) -or $file.Value.bytes -lt 0 -or $file.Value.bytes -gt 268435456 -or
            $file.Value.bytes -ne $Entries[$name].Length -or $file.Value.sha256 -isnot [string] -or $file.Value.sha256 -cnotmatch '^[a-f0-9]{64}$') {Stop-OfflineBundleCheck 'inventory_record_invalid'}
        if ($name -ceq 'application/manifest.json') {$counts.manifest++;continue}
        if ($name.StartsWith('application/server/',[StringComparison]::Ordinal)) {$counts.server++;$applicationBytes+=$file.Value.bytes;continue}
        if ($name.StartsWith('application/frontend/',[StringComparison]::Ordinal)) {$counts.frontend++;$applicationBytes+=$file.Value.bytes;continue}
        if ($name.StartsWith('operators/',[StringComparison]::Ordinal) -and $name.Substring(10) -cin $operators) {$counts.operators++;continue}
        if ($name -cmatch '^dependencies/dotnet/(dotnet\.exe|LICENSE\.txt|ThirdPartyNotices\.txt|host/fxr/10\.0\.12/[^/]+|shared/Microsoft\.(NETCore|AspNetCore)\.App/10\.0\.12/[^/]+)$') {$counts.dotnet++;continue}
        if ($name -cmatch '^dependencies/postgresql/(bin/[^/]+|lib/.+|share/.+|commandlinetools_3rd_party_licenses\.txt|pgAdmin_3rd_party_licenses\.txt|pgAdmin_license\.txt|server_license\.txt|StackBuilder_3rd_party_licenses\.txt)$') {$counts.postgresql++;continue}
        if ($name -ceq 'prerequisites/vc_redist.x64.exe') {$counts.prerequisites++;continue}
        if ($name.StartsWith('docs/',[StringComparison]::Ordinal) -and $name.Substring(5) -cin $docs) {$counts.docs++;continue}
        if ($name -cin @('licenses/Npgsql-LICENSE','licenses/README.txt')) {$counts.licenses++;continue}
        # Metadatos y avisos sólo existen en perfiles que los declaran; en los históricos siguen siendo entradas inválidas.
        # Las tablas de hashtable de PowerShell ignoran mayúsculas: la pertenencia se comprueba con -ccontains sobre las claves.
        $isApplication=$name.StartsWith('application/',[StringComparison]::Ordinal)
        $metadataName=if ($isApplication) {$name.Substring(12)} else {''}
        if ($profile.ContainsKey('metadata') -and $isApplication -and (@($profile.metadata.Keys) -ccontains $metadataName)) {
            if ($file.Value.sha256 -cne $profile.metadata[$metadataName]) {Stop-OfflineBundleCheck 'pinned_hash_mismatch'}
            $counts.metadata++;continue
        }
        if ($profile.ContainsKey('notices') -and (@($profile.notices.Keys) -ccontains $name)) {
            if ($file.Value.sha256 -cne $profile.notices[$name]) {Stop-OfflineBundleCheck 'pinned_hash_mismatch'}
            $counts.notices++;continue
        }
        Stop-OfflineBundleCheck 'layout_invalid'
    }
    if ($counts.server -ne $profile.server -or $counts.frontend -ne $profile.frontend -or $counts.operators -ne $operators.Count -or $counts.dotnet -ne 339 -or $counts.postgresql -ne 1568 -or
        $counts.docs -ne 4 -or $counts.manifest -ne 1 -or $counts.prerequisites -ne 1 -or $counts.licenses -ne 2) {Stop-OfflineBundleCheck 'layout_counts_invalid'}
    $expectedMetadata=0;$expectedNotices=0
    if ($profile.ContainsKey('metadata')) {$expectedMetadata=2}
    if ($profile.ContainsKey('notices')) {$expectedNotices=1}
    if ($counts.metadata -ne $expectedMetadata -or $counts.notices -ne $expectedNotices) {Stop-OfflineBundleCheck 'layout_counts_invalid'}
    if ($applicationBytes -ne $profile.bytes) {Stop-OfflineBundleCheck 'application_bytes_mismatch'}
    foreach ($required in @('application/manifest.json','dependencies/dotnet/dotnet.exe','dependencies/dotnet/LICENSE.txt','dependencies/dotnet/ThirdPartyNotices.txt',
        'dependencies/dotnet/host/fxr/10.0.12/hostfxr.dll','dependencies/dotnet/shared/Microsoft.NETCore.App/10.0.12/System.Private.CoreLib.dll',
        'dependencies/dotnet/shared/Microsoft.AspNetCore.App/10.0.12/Microsoft.AspNetCore.dll','dependencies/postgresql/bin/postgres.exe',
        'dependencies/postgresql/bin/initdb.exe','dependencies/postgresql/bin/pg_ctl.exe','dependencies/postgresql/bin/psql.exe',
        'dependencies/postgresql/bin/pg_dump.exe','dependencies/postgresql/bin/pg_restore.exe','licenses/Npgsql-LICENSE','licenses/README.txt',
        'dependencies/postgresql/commandlinetools_3rd_party_licenses.txt','dependencies/postgresql/pgAdmin_3rd_party_licenses.txt',
        'dependencies/postgresql/pgAdmin_license.txt','dependencies/postgresql/server_license.txt','dependencies/postgresql/StackBuilder_3rd_party_licenses.txt')) {
        if (-not $Entries.ContainsKey($required)) {Stop-OfflineBundleCheck 'layout_required_file_missing'}
    }
    if ($Manifest.files.'application/manifest.json'.sha256 -cne $Manifest.applicationManifestSha256 -or
        $Manifest.files.'prerequisites/vc_redist.x64.exe'.sha256 -cne '843068991daaa1f73ad9f6239bce4d0f6a07a51f18c37ea2a867e9beca71295c' -or
        $Manifest.files.'licenses/Npgsql-LICENSE'.sha256 -cne '2e1d9cc6ed4eb7fe6fa82091846c06b4f58571a2c3b54777db6baeca10dd2d74') {Stop-OfflineBundleCheck 'pinned_hash_mismatch'}
    return $counts
}

function Close-RackClickOfflineBundle {
    param([hashtable]$Bundle)
    if ($null -eq $Bundle) {return}
    try {if ($Bundle.ContainsKey('zip') -and $null -ne $Bundle.zip) {$Bundle.zip.Dispose()}}
    finally {if ($Bundle.ContainsKey('inputLocks')) {foreach ($stream in $Bundle.inputLocks) {$stream.Dispose()}}}
}

function Read-OfflineBundleRawNames {
    param([IO.FileStream]$Stream)
    # Inspect original central AND local header bytes before API decoding so the
    # closed raw-name contract does not depend on the ZIP API's name interpretation.
    # Closed bounded single-volume profile with a classic central-directory footer.
    # Local extra fields are left to the ZIP API; sizes/hashes remain independently bounded.
    $reader=New-Object IO.BinaryReader($Stream,[Text.Encoding]::ASCII,$true)
    try {
        if ($Stream.Length -lt 22) {Stop-OfflineBundleCheck 'zip_structure_invalid'}
        $start=[Math]::Max(0L,$Stream.Length-65557);$Stream.Position=$start
        $tail=$reader.ReadBytes([int]($Stream.Length-$start));$found=-1
        for ($i=$tail.Length-22;$i -ge 0;$i--) {
            if ($tail[$i] -eq 80 -and $tail[$i+1] -eq 75 -and $tail[$i+2] -eq 5 -and $tail[$i+3] -eq 6 -and
                $i+22+[BitConverter]::ToUInt16($tail,$i+20) -eq $tail.Length) {$found=$i;break}
        }
        if ($found -lt 0) {Stop-OfflineBundleCheck 'zip_structure_invalid'}
        $eocd=$start+$found;$Stream.Position=$eocd+4
        $disk=$reader.ReadUInt16();$centralDisk=$reader.ReadUInt16();$diskCount=$reader.ReadUInt16();$count=$reader.ReadUInt16()
        $size=$reader.ReadUInt32();$offset=$reader.ReadUInt32()
        if ($disk -ne 0 -or $centralDisk -ne 0 -or $diskCount -ne $count -or $count -le 1 -or $count -gt 10000 -or
            [long]$offset+[long]$size -ne $eocd) {Stop-OfflineBundleCheck 'zip_structure_invalid'}
        $names=New-Object 'Collections.Generic.List[string]';$Stream.Position=$offset
        for ($index=0;$index -lt $count;$index++) {
            if ($Stream.Position+46 -gt $eocd -or $reader.ReadUInt32() -ne 33639248) {Stop-OfflineBundleCheck 'zip_structure_invalid'}
            $record=$Stream.Position-4;$Stream.Position=$record+8
            $flags=$reader.ReadUInt16();$method=$reader.ReadUInt16()
            $Stream.Position=$record+28;$nameLength=$reader.ReadUInt16();$extraLength=$reader.ReadUInt16();$commentLength=$reader.ReadUInt16();$entryDisk=$reader.ReadUInt16()
            $Stream.Position=$record+42;$localOffset=$reader.ReadUInt32();$next=$record+46+$nameLength+$extraLength+$commentLength
            if (($flags -band 1) -ne 0 -or $method -notin @(0,8) -or $entryDisk -ne 0 -or $nameLength -le 0 -or $nameLength -gt 240 -or
                $next -gt $eocd -or [long]$localOffset+30 -gt $offset) {Stop-OfflineBundleCheck 'zip_structure_invalid'}
            $raw=$reader.ReadBytes($nameLength)
            foreach ($byte in $raw) {if ($byte -lt 32 -or $byte -gt 126) {Stop-OfflineBundleCheck 'entry_name_invalid'}}
            $name=[Text.Encoding]::ASCII.GetString($raw);Assert-OfflineBundleName $name
            $Stream.Position=$localOffset
            if ($reader.ReadUInt32() -ne 67324752) {Stop-OfflineBundleCheck 'zip_structure_invalid'}
            $Stream.Position=$localOffset+6
            if ($reader.ReadUInt16() -ne $flags -or $reader.ReadUInt16() -ne $method) {Stop-OfflineBundleCheck 'zip_structure_invalid'}
            $Stream.Position=$localOffset+26;$localNameLength=$reader.ReadUInt16();$localExtraLength=$reader.ReadUInt16()
            if ($localNameLength -ne $nameLength -or [long]$localOffset+30+$localNameLength+$localExtraLength -gt $offset) {Stop-OfflineBundleCheck 'zip_structure_invalid'}
            $localRaw=$reader.ReadBytes($localNameLength)
            if ([Convert]::ToBase64String($localRaw) -cne [Convert]::ToBase64String($raw)) {Stop-OfflineBundleCheck 'zip_structure_invalid'}
            $names.Add($name);$Stream.Position=$next
        }
        if ($Stream.Position -ne $eocd) {Stop-OfflineBundleCheck 'zip_structure_invalid'}
        return $names.ToArray()
    } finally {$reader.Dispose();$Stream.Position=0}
}

function Read-RackClickOfflineBundle {
    param([string]$ArchivePath,[string]$ExpectedArchiveSha256)
    $stream=$null;$zip=$null
    try {
        if ($ExpectedArchiveSha256 -cnotmatch '^[a-fA-F0-9]{64}$') {Stop-OfflineBundleCheck 'archive_reference_required'}
        $path=Get-OfflineBundleLocalPath $ArchivePath
        Assert-OfflineBundleNoReparse $path
        $stream=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        if ($stream.Length -le 0 -or $stream.Length -gt 536870912) {Stop-OfflineBundleCheck 'archive_size_invalid'}
        $digest=Get-OfflineBundleStreamDigest $stream $stream.Length $null 536870912
        if ($digest -cne $ExpectedArchiveSha256.ToLowerInvariant()) {Stop-OfflineBundleCheck 'archive_hash_mismatch'}
        $stream.Position=0;$rawNames=@(Read-OfflineBundleRawNames $stream)
        $assembly=[Reflection.Assembly]::LoadWithPartialName('System.IO.Compression')
        if ($null -eq $assembly) {Stop-OfflineBundleCheck 'zip_api_unavailable'}
        $zip=New-Object IO.Compression.ZipArchive($stream,[IO.Compression.ZipArchiveMode]::Read,$true)
        if ($zip.Entries.Count -le 1 -or $zip.Entries.Count -gt 10000) {Stop-OfflineBundleCheck 'entry_count_invalid'}
        $entries=@{};$directories=@{};$total=0L
        $entryIndex=0
        foreach ($entry in $zip.Entries) {
            $name=$entry.FullName;Assert-OfflineBundleName $name
            if ($entryIndex -ge $rawNames.Count -or $rawNames[$entryIndex] -cne $name) {Stop-OfflineBundleCheck 'zip_structure_invalid'}
            $entryIndex++
            $attrs=[long]$entry.ExternalAttributes;$unixType=($attrs -shr 16) -band 61440
            if ($unixType -notin @(0,32768) -or ($attrs -band 1040) -ne 0) {Stop-OfflineBundleCheck 'entry_type_invalid'}
            if ($entries.ContainsKey($name) -or $directories.ContainsKey($name)) {Stop-OfflineBundleCheck 'entry_collision'}
            $pieces=$name.Split('/');$prefix=''
            for ($i=0;$i -lt $pieces.Length-1;$i++) {
                if ($i -gt 0) {$prefix+='/'};$prefix+=$pieces[$i]
                if ($entries.ContainsKey($prefix) -or ($directories.ContainsKey($prefix) -and $directories[$prefix] -cne $prefix)) {Stop-OfflineBundleCheck 'entry_collision'}
                $directories[$prefix]=$prefix
            }
            if ($entry.Length -lt 0 -or $entry.Length -gt 268435456) {Stop-OfflineBundleCheck 'entry_size_invalid'}
            $total+=$entry.Length;if ($total -gt 1073741824) {Stop-OfflineBundleCheck 'uncompressed_size_invalid'}
            $entries[$name]=$entry
        }
        if ($entries.Count -ne $rawNames.Count) {Stop-OfflineBundleCheck 'zip_structure_invalid'}
        if (-not $entries.ContainsKey('bundle.json') -or $entries['bundle.json'].FullName -cne 'bundle.json') {Stop-OfflineBundleCheck 'manifest_missing'}
        $manifest=Read-OfflineBundleEntryJson $entries['bundle.json']
        $counts=Assert-OfflineBundleLayout $manifest $entries
        foreach ($file in $manifest.files.PSObject.Properties) {
            $entryStream=$null
            try {
                $entryStream=$entries[$file.Name].Open()
                if ((Get-OfflineBundleStreamDigest $entryStream $file.Value.bytes) -cne $file.Value.sha256) {Stop-OfflineBundleCheck 'entry_hash_mismatch'}
            } finally {if ($null -ne $entryStream) {$entryStream.Dispose()}}
        }
        $app=Read-OfflineBundleEntryJson $entries['application/manifest.json']
        $profile=Get-OfflineBundleApplicationProfile $manifest.applicationManifestSha256
        $expectedSchema=Get-OfflineBundleExpectedSchema $profile
        if ($app.schema -isnot [int] -or $app.schema -ne $expectedSchema) {Stop-OfflineBundleCheck 'application_manifest_invalid'}
        foreach ($kind in @('server','frontend')) {
            $appFiles=@($app.distributions.$kind.PSObject.Properties)
            if ($appFiles.Count -ne $profile[$kind]) {Stop-OfflineBundleCheck 'application_manifest_invalid'}
            foreach ($file in $appFiles) {
                $key='application/'+$kind+'/'+$file.Name
                if (-not $entries.ContainsKey($key) -or $manifest.files.$key.sha256 -cne $file.Value) {Stop-OfflineBundleCheck 'application_manifest_invalid'}
            }
        }
        $entryStream=$null
        try {$entryStream=$entries['bundle.json'].Open();$manifestDigest=Get-OfflineBundleStreamDigest $entryStream $entries['bundle.json'].Length $null 8388608}
        finally {if ($null -ne $entryStream) {$entryStream.Dispose()}}
        return @{zip=$zip;inputLocks=@($stream);archivePath=$path;archiveSha256=$digest;manifestSha256=$manifestDigest;manifest=$manifest;entries=$entries;counts=$counts;verifiedFiles=$entries.Count;uncompressedBytes=$total}
    } catch {
        try {if ($null -ne $zip) {$zip.Dispose()}} finally {if ($null -ne $stream) {$stream.Dispose()}}
        throw
    }
}

function Test-OfflineBundleX64Pe {
    param([string]$Path)
    $reader=$null
    try {
        $reader=New-Object IO.BinaryReader([IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read))
        if ($reader.BaseStream.Length -lt 64 -or $reader.ReadUInt16() -ne 23117) {return $false}
        $reader.BaseStream.Position=60;$offset=$reader.ReadInt32()
        if ($offset -lt 64 -or $offset -gt $reader.BaseStream.Length-6) {return $false}
        $reader.BaseStream.Position=$offset
        return $reader.ReadUInt32() -eq 17744 -and $reader.ReadUInt16() -eq 34404
    } finally {if ($null -ne $reader) {$reader.Dispose()}}
}

function Get-RackClickCrtInventory {
    $result=@{installed=$false;registryVersion='';dlls=@();compatible=$false};$base=$null;$key=$null
    if (-not [Environment]::Is64BitProcess -or -not [Environment]::Is64BitOperatingSystem) {Stop-OfflineBundleCheck 'platform_unsupported'}
    try {
        $base=[Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine,[Microsoft.Win32.RegistryView]::Registry64)
        $key=$base.OpenSubKey('SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',$false)
        if ($null -ne $key) {$result.installed=($key.GetValue('Installed',0) -eq 1);$result.registryVersion=[string]$key.GetValue('Version','')}
    } finally {if ($null -ne $key) {$key.Dispose()};if ($null -ne $base) {$base.Dispose()}}
    $ok=$result.installed
    foreach ($name in @('vcruntime140.dll','msvcp140.dll')) {
        $path=Join-Path (Join-Path $env:SystemRoot 'System32') $name;$valid=$false;$version=''
        if ([IO.File]::Exists($path)) {
            Assert-OfflineBundleNoReparse $path;$info=[Diagnostics.FileVersionInfo]::GetVersionInfo($path)
            $version=('{0}.{1}.{2}.{3}' -f $info.FileMajorPart,$info.FileMinorPart,$info.FileBuildPart,$info.FilePrivatePart)
            $valid=(Test-OfflineBundleX64Pe $path) -and [version]$version -ge [version]'14.44.35211.0'
        }
        $result.dlls+=@{name=$name;version=$version;valid=$valid};$ok=$ok -and $valid
    }
    $result.compatible=$ok;return $result
}

function Get-RackClickCrtDecision {
    param([bool]$Compatible,[bool]$InstallRequested,[bool]$Elevated)
    if ($Compatible) {return 'reuse'}
    if (-not $InstallRequested) {return 'missing'}
    if (-not $Elevated) {return 'elevation_required'}
    return 'install'
}

function Get-RackClickCrtExitDecision {
    param([int]$ExitCode)
    if ($ExitCode -eq 0) {return 'verify'}
    if ($ExitCode -eq 3010) {return 'reboot_required'}
    return 'failed'
}

function Copy-RackClickOfflineBundleContent {
    param([hashtable]$Bundle,[string]$ContentPath)
    foreach ($name in @($Bundle.entries.Keys|Sort-Object)) {
        $target=Join-Path $ContentPath $name.Replace('/',[IO.Path]::DirectorySeparatorChar)
        $parent=[IO.Path]::GetDirectoryName($target)
        if (-not [IO.Directory]::Exists($parent)) {$null=[IO.Directory]::CreateDirectory($parent)}
        Assert-OfflineBundleNoReparse $parent
        $source=$null;$output=$null
        try {
            $source=$Bundle.entries[$name].Open()
            $output=[IO.File]::Open($target,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
            $length=$Bundle.entries[$name].Length
            $expected=if ($name -ceq 'bundle.json') {$Bundle.manifestSha256} else {$Bundle.manifest.files.$name.sha256}
            $observed=Get-OfflineBundleStreamDigest $source $length $output
            $output.Flush($true)
            if ($observed -cne $expected) {Stop-OfflineBundleCheck 'extraction_hash_mismatch'}
        } finally {if ($null -ne $output) {$output.Dispose()};if ($null -ne $source) {$source.Dispose()}}
    }
}

function Assert-RackClickOfflineInstalledContent {
    param([hashtable]$Bundle,[string]$ContentPath)
    $actual=@((New-Object IO.DirectoryInfo($ContentPath)).GetFiles('*',[IO.SearchOption]::AllDirectories))
    if ($actual.Count -ne $Bundle.entries.Count) {Stop-OfflineBundleCheck 'installed_inventory_mismatch'}
    foreach ($file in $actual) {
        Assert-OfflineBundleNoReparse $file.FullName
        $relative=$file.FullName.Substring($ContentPath.Length+1).Replace('\','/')
        if (-not $Bundle.entries.ContainsKey($relative)) {Stop-OfflineBundleCheck 'installed_inventory_mismatch'}
        $stream=$null
        try {
            $stream=[IO.File]::Open($file.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
            $expected=if ($relative -ceq 'bundle.json') {$Bundle.manifestSha256} else {$Bundle.manifest.files.$relative.sha256}
            if ((Get-OfflineBundleStreamDigest $stream $Bundle.entries[$relative].Length) -cne $expected) {Stop-OfflineBundleCheck 'installed_hash_mismatch'}
        } finally {if ($null -ne $stream) {$stream.Dispose()}}
    }
}
