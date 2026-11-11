#requires -Version 5.1
# Explicit native backup metadata helpers. No retirement, catalogue completeness or service control.
. (Join-Path $PSScriptRoot 'RackClick.Backup.ps1')

function Get-MfaBackupStreamHash($Stream) {
    $hash = [Security.Cryptography.SHA256]::Create()
    try { $Stream.Position = 0; return [BitConverter]::ToString($hash.ComputeHash($Stream)).Replace('-', '').ToLowerInvariant() }
    finally { $Stream.Position = 0; $hash.Dispose() }
}

function Open-MfaBackupTool([string]$Directory, [string]$ExpectedSumsSha256) {
    $Directory = Assert-BackupPath $Directory
    Assert-BackupNoReparse $Directory
    $handles = New-Object 'Collections.Generic.List[IO.FileStream]'
    try {
        if ($ExpectedSumsSha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'mfa_backup_tool_pin_invalid' }
        $sumPath = Join-Path $Directory 'SHA256SUMS'
        Assert-BackupNoReparse $sumPath
        $sum = [IO.File]::Open($sumPath, 'Open', 'Read', 'Read'); $handles.Add($sum)
        if ($sum.Length -gt 262144 -or (Get-MfaBackupStreamHash $sum) -cne $ExpectedSumsSha256) { throw 'mfa_backup_tool_pin_invalid' }
        $reader = New-Object IO.StreamReader($sum, (New-Object Text.UTF8Encoding($false,$true)), $false, 4096, $true)
        try { $lines = $reader.ReadToEnd().TrimEnd("`r", "`n").Split("`n") } finally { $reader.Dispose() }
        $expected = New-Object 'Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
        foreach ($line in $lines) {
            if ($line.TrimEnd("`r") -cnotmatch '^([a-f0-9]{64})  ([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)$') { throw 'mfa_backup_tool_content_invalid' }
            $digest = $Matches[1]; $relative = $Matches[2]
            if ($relative -eq 'SHA256SUMS' -or @($relative.Split('/') | Where-Object { $_ -in @('.', '..') }).Count -or -not $expected.Add($relative) -or $expected.Count -gt 1024) { throw 'mfa_backup_tool_content_invalid' }
            $path = Join-Path $Directory $relative
            Assert-BackupNoReparse $path
            $stream = [IO.File]::Open($path, 'Open', 'Read', 'Read'); $handles.Add($stream)
            if ((Get-MfaBackupStreamHash $stream) -cne $digest) { throw 'mfa_backup_tool_content_invalid' }
        }
        if (-not $expected.Contains('RackClick.Server.dll')) { throw 'mfa_backup_tool_content_invalid' }
        # Inspect each directory entry before descent; even an empty junction is outside the pinned layout.
        $pending=New-Object 'Collections.Generic.Stack[string]';$pending.Push($Directory)
        $directories=0
        while($pending.Count -gt 0){
            $folder=$pending.Pop();$directories++
            if($directories -gt 1024){throw 'mfa_backup_tool_content_invalid'}
            foreach($entry in (Get-Item -LiteralPath $folder -Force).GetFileSystemInfos()){
                if(($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'mfa_backup_tool_content_invalid'}
                $relative=$entry.FullName.Substring($Directory.Length+1).Replace('\','/')
                if($entry -is [IO.DirectoryInfo]){
                    $prefix=$relative+'/'
                    if(@($expected | Where-Object { $_.StartsWith($prefix,[StringComparison]::Ordinal) }).Count -eq 0){throw 'mfa_backup_tool_content_invalid'}
                    $pending.Push($entry.FullName)
                }elseif($relative -cne 'SHA256SUMS' -and -not $expected.Contains($relative)){throw 'mfa_backup_tool_content_invalid'}
            }
        }
        return [pscustomobject]@{ Directory=$Directory; Handles=$handles }
    } catch { foreach ($handle in $handles) { $handle.Dispose() }; throw }
}

function Close-MfaBackupTool($Tool) { if ($null -ne $Tool) { foreach ($handle in $Tool.Handles) { $handle.Dispose() } } }

function Set-MfaBackupChildEnvironment([Diagnostics.ProcessStartInfo]$StartInfo) {
    foreach ($name in @($StartInfo.EnvironmentVariables.Keys)) {
        if ([string]$name -match '(?i)^(PG|ConnectionStrings__|SqlSecret__|MfaKeyStore__|ASPNETCORE_|CORECLR_|COR_|DOTNET_)|PROFILER|NOTIFICATION') {
            $StartInfo.EnvironmentVariables.Remove([string]$name)
        }
    }
    $StartInfo.EnvironmentVariables['DOTNET_EnableDiagnostics']='0'
    $StartInfo.EnvironmentVariables['CORECLR_ENABLE_PROFILING']='0'
    $StartInfo.EnvironmentVariables['DOTNET_CLI_TELEMETRY_OPTOUT']='1'
}

function Start-MfaBackupProtocol([string]$DotnetPath, $Tool,
    [ValidateSet('--mfa-backup-inventory','--mfa-key-maintenance')][string]$CliMode='--mfa-backup-inventory') {
    $dotnet = Assert-BackupPath $DotnetPath
    Assert-BackupNoReparse $dotnet
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName=$dotnet
    $start.Arguments='"' + (Join-Path $Tool.Directory 'RackClick.Server.dll') + '" ' + $CliMode
    $start.WorkingDirectory=$Tool.Directory
    $start.UseShellExecute=$false; $start.CreateNoWindow=$true
    $start.RedirectStandardInput=$true; $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
    $start.StandardOutputEncoding=New-Object Text.UTF8Encoding($false)
    Set-MfaBackupChildEnvironment $start
    $process = New-Object Diagnostics.Process; $process.StartInfo=$start
    if (-not $process.Start()) { throw 'mfa_backup_process_failed' }
    # .NET Framework (PS5.1) lacks ProcessStartInfo.StandardInputEncoding; own the UTF-8 writer explicitly.
    $inputWriter=New-Object IO.StreamWriter($process.StandardInput.BaseStream, (New-Object Text.UTF8Encoding($false)))
    $inputWriter.AutoFlush=$true
    return [pscustomobject]@{ Process=$process; InputWriter=$inputWriter; Errors=$process.StandardError.ReadToEndAsync() }
}

function Read-MfaBackupResponse($Protocol, [string]$ExpectedStatus) {
    $line = $Protocol.Process.StandardOutput.ReadLineAsync()
    if (-not $line.Wait(30000)) { throw 'mfa_backup_protocol_timeout' }
    $text=$line.Result
    if ($null -eq $text -or $text.Length -gt 131072) { throw 'mfa_backup_protocol_invalid' }
    try { $result=$text | ConvertFrom-Json -ErrorAction Stop } catch { throw 'mfa_backup_protocol_invalid' }
    if ($result.status -cne $ExpectedStatus) { throw 'mfa_backup_protocol_rejected' }
    return $result
}

function Complete-MfaBackupProtocol($Protocol) {
    $Protocol.InputWriter.Close()
    if (-not $Protocol.Process.WaitForExit(15000) -or $Protocol.Process.ExitCode -ne 0 -or $Protocol.Process.StandardOutput.ReadToEnd().Length -ne 0) { throw 'mfa_backup_protocol_failed' }
}

function Close-MfaBackupProtocol($Protocol) {
    if ($null -ne $Protocol) {
        if (-not $Protocol.Process.HasExited) { $Protocol.Process.Kill(); $Protocol.Process.WaitForExit() }
        $Protocol.InputWriter.Dispose()
        $Protocol.Process.Dispose()
    }
}

function Read-MfaBackupBytes([string]$Path, [long]$Maximum) {
    $Path=Assert-BackupPath $Path; Assert-BackupNoReparse $Path
    $stream=[IO.File]::Open($Path,'Open','Read','Read')
    try {
        if ($stream.Length -lt 1 -or $stream.Length -gt $Maximum) { throw 'mfa_backup_file_invalid' }
        $bytes=New-Object byte[] ([int]$stream.Length)
        $offset=0
        while ($offset -lt $bytes.Length) {
            $count=$stream.Read($bytes,$offset,$bytes.Length-$offset)
            if ($count -eq 0) { throw 'mfa_backup_file_invalid' }; $offset+=$count
        }
        return ,$bytes
    } finally { $stream.Dispose() }
}

function Get-MfaBackupBytesHash([byte[]]$Bytes) {
    $hash=[Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($hash.ComputeHash($Bytes)).Replace('-','').ToLowerInvariant() } finally {$hash.Dispose()}
}

function Read-MfaBackupReceipt([string]$Path,[string]$ExpectedSha256) {
    $bytes=Read-MfaBackupBytes $Path 4096
    if ($ExpectedSha256 -cnotmatch '^[a-f0-9]{64}$' -or (Get-MfaBackupBytesHash $bytes) -cne $ExpectedSha256) { throw 'mfa_backup_receipt_pin_invalid' }
    try { $text=(New-Object Text.UTF8Encoding($false,$true)).GetString($bytes); $value=$text | ConvertFrom-Json -ErrorAction Stop } catch { throw 'mfa_backup_receipt_invalid' }
    $fields=@('format','formatVersion','installationId','backupId','inventorySha256','manifestSha256','dumpSha256','envelopeSha256')
    if ((@($value.PSObject.Properties.Name | Sort-Object) -join ',') -cne (($fields | Sort-Object) -join ',') -or $value.format -cne 'RackClick.MfaBackupInventoryReceipt' -or $value.formatVersion -isnot [int] -or $value.formatVersion -ne 1) { throw 'mfa_backup_receipt_invalid' }
    $canonical=[ordered]@{}
    foreach($field in $fields){$canonical[$field]=$value.$field}
    # Our producer writes a single canonical representation; duplicate keys and alternate interpretations fail closed.
    if (($canonical | ConvertTo-Json -Compress) -cne $text) { throw 'mfa_backup_receipt_invalid' }
    foreach($field in @('installationId','backupId')){
        $id=[guid]::Empty
        if (-not [guid]::TryParseExact($value.$field,'D',[ref]$id) -or $id -eq [guid]::Empty -or $value.$field -cne $id.ToString('D')) {throw 'mfa_backup_receipt_invalid'}
    }
    foreach($field in @('inventorySha256','manifestSha256','dumpSha256','envelopeSha256')) {if($value.$field -isnot [string] -or $value.$field -cnotmatch '^[a-f0-9]{64}$'){throw 'mfa_backup_receipt_invalid'}}
    return $value
}
