#requires -Version 5.1
# Functions only. The caller pins this source and leases verified source packages.
function Stop-MfaCode([string]$Code) { throw ('mfa_diagnostic:code_'+$Code) }
function Get-MfaCodeHash([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Assert-MfaCodeNoReparse([string]$Path) {
    $item=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { Stop-MfaCode 'reparse' }
        if ($item -is [IO.FileInfo]) { $item=$item.Directory } else { $item=$item.Parent }
    }
}
function Assert-MfaCodeAbsolute([string]$Path) {
    if ($Path -cnotmatch '^[A-Za-z]:[\\/]' -or $Path.Substring(2).Contains(':') -or $Path -match '[\x00-\x1f"<>|?*]' -or
        $Path -match '(^|[\\/])\.\.?([\\/]|$)' -or $Path -match '[. ]([\\/]|$)') { Stop-MfaCode 'path_invalid' }
    return [IO.Path]::GetFullPath($Path).TrimEnd('\')
}
function Assert-DiagnosticCodePath([string]$Root) {
    $full=Assert-MfaCodeAbsolute $Root
    $programData=Assert-MfaCodeAbsolute $env:ProgramData
    if ([IO.Path]::GetDirectoryName($full) -ine $programData -or
        [IO.Path]::GetFileName($full) -cnotmatch '^RackClick-MFA-Code-[a-f0-9]{32}$') { Stop-MfaCode 'root_invalid' }
    Assert-MfaCodeNoReparse $programData
    return $full
}
function Assert-MfaCodeReader([string]$ReaderSid) {
    if ($ReaderSid -cnotmatch '^S-1-5-21-[1-9][0-9]*-[1-9][0-9]*-[1-9][0-9]*-[1-9][0-9]*$') { Stop-MfaCode 'reader_invalid' }
    try { $sid=New-Object Security.Principal.SecurityIdentifier($ReaderSid) } catch { Stop-MfaCode 'reader_invalid' }
    if ($sid.Value -cne $ReaderSid) { Stop-MfaCode 'reader_invalid' }
}
function Get-MfaCodeFixedPaths {
    return @('probe/RackClick.MfaServiceReadProbe.dll','probe/RackClick.Server.dll','probe/RackClick.Domain.dll',
        'probe/Npgsql.dll','probe/Otp.NET.dll','probe/RackClick.MfaServiceReadProbe.deps.json',
        'probe/RackClick.MfaServiceReadProbe.runtimeconfig.json','licenses/Npgsql-LICENSE',
        'licenses/Otp.NET-LICENSE.txt','licenses/README.txt','diagnostic/RackClick.MfaProbeExceptionDiagnostic.dll',
        'diagnostic/RackClick.MfaProbeExceptionDiagnostic.deps.json','diagnostic/RackClick.MfaProbeExceptionDiagnostic.runtimeconfig.json')
}
function Get-MfaCodeDigest($Entries) {
    $lines=@($Entries | ForEach-Object { $_.rel+'|'+([long]$_.bytes).ToString([Globalization.CultureInfo]::InvariantCulture)+'|'+$_.sha256 })
    $hash=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes(($lines -join "`n"))))).Replace('-','').ToLowerInvariant() }
    finally { $hash.Dispose() }
}
function Assert-MfaCodeManifest($Manifest) {
    if ($null -eq $Manifest -or $Manifest.count -ne 352 -or @($Manifest.entries).Count -ne 352 -or
        $Manifest.digest -cnotmatch '^[a-f0-9]{64}$') { Stop-MfaCode 'manifest_invalid' }
    $oldRoot=Assert-MfaCodeAbsolute $Manifest.oldPackage;$newRoot=Assert-MfaCodeAbsolute $Manifest.package
    $fixed=@(Get-MfaCodeFixedPaths);$seen=@{};$previous='';$runtime=0
    foreach ($entry in $Manifest.entries) {
        $rel=$entry.rel
        if ($rel -isnot [string] -or $rel -cnotmatch '^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+$' -or
            $rel -match '(^|/)\.\.?(/|$)' -or $rel -match '[. ](/|$)' -or $seen.ContainsKey($rel) -or
            ($previous -ne '' -and [string]::CompareOrdinal($previous,$rel) -ge 0) -or
            $entry.sha256 -cnotmatch '^[a-f0-9]{64}$' -or ($entry.bytes -isnot [long] -and $entry.bytes -isnot [int]) -or $entry.bytes -lt 0) { Stop-MfaCode 'manifest_entry_invalid' }
        if ($rel.StartsWith('runtime/',[StringComparison]::Ordinal)) {
            if ($rel -cnotmatch '\.(dll|exe|json)$' -and $rel -cnotin @('runtime/LICENSE.txt','runtime/ThirdPartyNotices.txt',
                'runtime/shared/Microsoft.AspNetCore.App/10.0.12/.version','runtime/shared/Microsoft.NETCore.App/10.0.12/.version')) { Stop-MfaCode 'manifest_entry_invalid' }
            $runtime++
        } elseif ($rel -cnotin $fixed) { Stop-MfaCode 'manifest_entry_invalid' }
        $sourceRoot=$oldRoot;if ($rel.StartsWith('diagnostic/')) { $sourceRoot=$newRoot }
        if ($entry.source -cne (Join-Path $sourceRoot $rel)) { Stop-MfaCode 'source_scope_invalid' }
        $seen[$rel]=$true;$previous=$rel
    }
    if ($runtime -ne 339 -or @($fixed | Where-Object {-not $seen.ContainsKey($_)}).Count -ne 0 -or
        (Get-MfaCodeDigest $Manifest.entries) -cne $Manifest.digest) { Stop-MfaCode 'manifest_digest_invalid' }
}
function Get-DiagnosticCodeManifest($Context) {
    $oldRoot=Assert-MfaCodeAbsolute $Context.oldPackage;$newRoot=Assert-MfaCodeAbsolute $Context.package
    Assert-MfaCodeNoReparse $oldRoot;Assert-MfaCodeNoReparse $newRoot
    $sums=Join-Path $oldRoot 'SHA256SUMS';Assert-MfaCodeNoReparse $sums
    if ((Get-MfaCodeHash $sums) -cne '803a8373d7c9fa8cc9d230e285f4b4e5ca0b84f222c68d10980278652f16035b') { Stop-MfaCode 'source_sums_invalid' }
    $runtime=@{};$seen=@{}
    foreach ($line in [IO.File]::ReadAllLines($sums)) {
        if ($line -cnotmatch '^([a-f0-9]{64})  ([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)$') { Stop-MfaCode 'source_sums_invalid' }
        $sha=$Matches[1];$rel=$Matches[2]
        if ($seen.ContainsKey($rel) -or $rel -match '(^|/)\.\.?(/|$)') { Stop-MfaCode 'source_sums_invalid' }
        $seen[$rel]=$sha
        if ($rel.StartsWith('runtime/',[StringComparison]::Ordinal)) { $runtime[$rel]=$sha }
    }
    if ($runtime.Count -ne 339) { Stop-MfaCode 'source_runtime_invalid' }
    [string[]]$paths=@($runtime.Keys)+@(Get-MfaCodeFixedPaths);[Array]::Sort($paths,[StringComparer]::Ordinal)
    $entries=@(foreach ($rel in $paths) {
        $base=$oldRoot;if ($rel.StartsWith('diagnostic/')) { $base=$newRoot }
        $source=Join-Path $base $rel;Assert-MfaCodeNoReparse $source
        $item=Get-Item -LiteralPath $source -Force -ErrorAction Stop
        if ($item -isnot [IO.FileInfo]) { Stop-MfaCode 'source_file_invalid' }
        $sha=Get-MfaCodeHash $source
        if (-not $rel.StartsWith('diagnostic/') -and (-not $seen.ContainsKey($rel) -or $sha -cne $seen[$rel])) { Stop-MfaCode 'source_hash_invalid' }
        [pscustomobject]@{rel=$rel;source=$source;sha256=$sha;bytes=[long]$item.Length}
    })
    $manifest=[pscustomobject]@{entries=$entries;digest=(Get-MfaCodeDigest $entries);count=$entries.Count;oldPackage=$oldRoot;package=$newRoot}
    Assert-MfaCodeManifest $manifest
    return $manifest
}
function Assert-MfaCodeAcl([string]$Path,[string]$ReaderSid,[bool]$IsRoot) {
    $item=Get-Item -LiteralPath $Path -Force -ErrorAction Stop;$directory=$item -is [IO.DirectoryInfo]
    $acl=Get-Acl -LiteralPath $Path -ErrorAction Stop
    $owners=@('S-1-5-18','S-1-5-32-544');if ($IsRoot) { $owners=@('S-1-5-32-544') }
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -cnotin $owners -or
        $acl.AreAccessRulesProtected -ne $IsRoot -or -not $acl.AreAccessRulesCanonical) { Stop-MfaCode 'acl_invalid' }
    $rules=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]));$seen=@{}
    foreach ($rule in $rules) {
        $sid=$rule.IdentityReference.Value;$rights=2032127;if ($sid -ceq $ReaderSid) { $rights=1179817 }
        $inherit=0;if ($directory) { $inherit=3 }
        if ($sid -cnotin @('S-1-5-18','S-1-5-32-544',$ReaderSid) -or $seen.ContainsKey($sid) -or
            $rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or [long]$rule.FileSystemRights -ne $rights -or
            [int]$rule.InheritanceFlags -ne $inherit -or [int]$rule.PropagationFlags -ne 0 -or $rule.IsInherited -eq $IsRoot) { Stop-MfaCode 'acl_invalid' }
        $seen[$sid]=$true
    }
    if ($rules.Count -ne 3) { Stop-MfaCode 'acl_invalid' }
}
function Add-MfaCodeLease($Leases,[string]$Path) {
    Assert-MfaCodeNoReparse $Path
    $Leases.Add([IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read))
}
function Assert-DiagnosticCodePayload([string]$Root,[string]$ReaderSid,$Manifest,$Leases) {
    $Root=Assert-DiagnosticCodePath $Root;Assert-MfaCodeReader $ReaderSid;Assert-MfaCodeManifest $Manifest
    Assert-MfaCodeNoReparse $Root;Assert-MfaCodeAcl $Root $ReaderSid $true
    $wanted=@{};$dirs=@{}
    foreach ($entry in $Manifest.entries) {
        $wanted[$entry.rel]=$entry
        $parent=$entry.rel
        while ($parent.Contains('/')) { $parent=$parent.Substring(0,$parent.LastIndexOf('/'));$dirs[$parent]=$true }
    }
    $files=0;$directoryCount=0;$pending=New-Object Collections.Generic.Queue[string];$pending.Enqueue($Root)
    while ($pending.Count -gt 0) {
        foreach ($item in @(Get-ChildItem -LiteralPath $pending.Dequeue() -Force -ErrorAction Stop)) {
            Assert-MfaCodeNoReparse $item.FullName;Assert-MfaCodeAcl $item.FullName $ReaderSid $false
            $rel=$item.FullName.Substring($Root.Length+1).Replace('\','/')
            if ($item -is [IO.DirectoryInfo]) {
                if (-not $dirs.ContainsKey($rel)) { Stop-MfaCode 'extra_directory' }
                $directoryCount++;$pending.Enqueue($item.FullName)
            } else {
                if (-not $wanted.ContainsKey($rel)) { Stop-MfaCode 'extra_file' }
                Add-MfaCodeLease $Leases $item.FullName
                $entry=$wanted[$rel]
                if ($item.Length -ne $entry.bytes -or (Get-MfaCodeHash $item.FullName) -cne $entry.sha256) { Stop-MfaCode 'payload_hash_invalid' }
                $files++
            }
        }
    }
    if ($files -ne 352 -or $directoryCount -ne $dirs.Count) { Stop-MfaCode 'payload_count_invalid' }
}
function New-DiagnosticCodePayload([string]$Root,[string]$ReaderSid,$Manifest,$Leases) {
    $Root=Assert-DiagnosticCodePath $Root;Assert-MfaCodeReader $ReaderSid;Assert-MfaCodeManifest $Manifest
    $sddl='O:BAG:SYD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FRFX;;;'+$ReaderSid+')'
    $errorCode=[RackClick.SystemReadTrial.Folder]::Create($Root,$sddl)
    if ($errorCode -eq 183) { Stop-MfaCode 'root_exists' }
    if ($errorCode -ne 0) { Stop-MfaCode 'root_create_failed' }
    Assert-MfaCodeAcl $Root $ReaderSid $true
    foreach ($entry in $Manifest.entries) {
        Add-MfaCodeLease $Leases $entry.source
        $source=Get-Item -LiteralPath $entry.source -Force -ErrorAction Stop
        if ($source -isnot [IO.FileInfo] -or $source.Length -ne $entry.bytes -or (Get-MfaCodeHash $entry.source) -cne $entry.sha256) { Stop-MfaCode 'source_changed' }
        $destination=Join-Path $Root $entry.rel;$parent=[IO.Path]::GetDirectoryName($destination)
        $missing=New-Object Collections.Generic.Stack[string]
        while (-not [IO.Directory]::Exists($parent)) { $missing.Push($parent);$parent=[IO.Path]::GetDirectoryName($parent) }
        while ($missing.Count -gt 0) {
            $directory=$missing.Pop();$result=[RackClick.SystemReadTrial.Folder]::Create($directory,'G:SY')
            if ($result -ne 0) { Stop-MfaCode 'directory_create_failed' }
            Assert-MfaCodeNoReparse $directory;Assert-MfaCodeAcl $directory $ReaderSid $false
        }
        Assert-MfaCodeNoReparse ([IO.Path]::GetDirectoryName($destination))
        $sourceStream=[IO.File]::Open($entry.source,'Open','Read','Read');$output=$null
        try {
            $output=[IO.File]::Open($destination,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
            $sourceStream.CopyTo($output);$output.Flush($true)
        } finally { if ($null -ne $output) { $output.Dispose() };$sourceStream.Dispose() }
        Add-MfaCodeLease $Leases $destination
        if ((Get-Item -LiteralPath $destination -Force).Length -ne $entry.bytes -or (Get-MfaCodeHash $destination) -cne $entry.sha256) { Stop-MfaCode 'copy_hash_invalid' }
    }
    Assert-DiagnosticCodePayload $Root $ReaderSid $Manifest $Leases
}
