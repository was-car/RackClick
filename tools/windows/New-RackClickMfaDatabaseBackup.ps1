#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$PostgresBinPath='', [string]$ProfilePath='', [string]$DotnetPath='',
    [string]$ToolDirectory='', [string]$ExpectedToolSumsSha256='',
    [string]$InstallationId='', [string]$DestinationPath='', [string]$RegistryDirectory='',
    [string]$EnvelopePath='', [string]$ExpectedEnvelopeSha256='', [Security.SecureString]$EnvelopePassword
)
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
$mfaRuntimeHostPath=$DotnetPath
. (Join-Path $PSScriptRoot 'RackClick.MfaBackupInventory.ps1')
$tool=$null; $protocol=$null; $passwordPointer=[IntPtr]::Zero; $destination=$null
$report=[ordered]@{schemaVersion=1;success=$false;code='mfa_backup_failed';partialDataPreserved=$true;inventorySha256='';receiptSha256='';backupId='';catalogComplete=$false;retirementAuthorized=$false}
try {
    $id=[guid]::Empty
    if (-not [guid]::TryParseExact($InstallationId,'D',[ref]$id) -or $id -eq [guid]::Empty -or $InstallationId -cne $id.ToString('D')) {throw 'mfa_backup_input_invalid'}
    $profile=Read-BackupProfile $ProfilePath
    if($profile.database -cne ('rc_db_'+$id.ToString('N')) -or $profile.user -cne ('rc_backup_'+$id.ToString('N'))){throw 'mfa_backup_identity_invalid'}
    $bin=Assert-BackupPostgresTools $PostgresBinPath
    $registry=Assert-BackupPath $RegistryDirectory
    if(-not [IO.Directory]::Exists($registry)){throw 'mfa_backup_registry_invalid'}
    Assert-BackupPrivateAcl $registry
    $dest=Assert-BackupPath $DestinationPath
    if ($registry.StartsWith($dest+'\',[StringComparison]::OrdinalIgnoreCase) -or $dest.Equals($registry,[StringComparison]::OrdinalIgnoreCase) -or $dest.StartsWith($registry+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'mfa_backup_registry_not_separate'}
    if([IO.File]::Exists($dest) -or [IO.Directory]::Exists($dest)){throw 'mfa_backup_destination_exists'}
    $envelope=Read-MfaBackupBytes $EnvelopePath 1048576
    if($ExpectedEnvelopeSha256 -cnotmatch '^[a-f0-9]{64}$' -or (Get-MfaBackupBytesHash $envelope) -cne $ExpectedEnvelopeSha256){throw 'mfa_backup_envelope_pin_invalid'}
    $tool=Open-MfaBackupTool $ToolDirectory $ExpectedToolSumsSha256
    if ($null -eq $EnvelopePassword) {$EnvelopePassword=Read-Host 'Password del sobre externo (no se copia al backup)' -AsSecureString}
    $passwordPointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($EnvelopePassword)
    $password=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    $connection='Host=127.0.0.1;Port='+$profile.port+';Database='+$profile.database+';Username='+$profile.user+';Password="'+$profile.password.Replace('"','""')+'";Include Error Detail=false;Pooling=false'
    $protocol=Start-MfaBackupProtocol $mfaRuntimeHostPath $tool
    $request=[ordered]@{operation='snapshot';installationId=$InstallationId;connectionString=$connection;envelopeBase64=[Convert]::ToBase64String($envelope);envelopePassword=$password}
    $protocol.InputWriter.WriteLine(($request | ConvertTo-Json -Compress)); $protocol.InputWriter.Flush()
    $request=$null; $password=$null; $connection=$null
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer); $passwordPointer=[IntPtr]::Zero
    $ready=Read-MfaBackupResponse $protocol 'snapshot_ready'
    if ($ready.snapshot -isnot [string] -or $ready.snapshot -cnotmatch '^[0-9A-Fa-f]+-[0-9A-Fa-f]+-[0-9]+$') {throw 'mfa_backup_snapshot_invalid'}
    # No destination is created until identity/envelope/snapshot validation succeeds.
    $destination=New-BackupPrivateDirectory $dest
    Write-BackupNewText (Join-Path $destination 'INCOMPLETE.json') '{"complete":false}'
    $database=New-BackupPrivateDirectory (Join-Path $destination 'database')
    $arguments=(Get-BackupConnectionArguments $profile $profile.database)+@('--format=custom','--no-owner','--no-acl','--snapshot',$ready.snapshot,'--file','data.dump.partial')
    $null=Invoke-BackupPg (Join-Path $bin 'pg_dump.exe') $arguments $profile -WorkingDirectory $database
    $partial=Join-Path $database 'data.dump.partial'
    if(-not [IO.File]::Exists($partial) -or (Get-Item -LiteralPath $partial).Length -lt 5){throw 'mfa_backup_dump_invalid'}
    $dumpHash=Get-RuntimeConfigDigest $partial
    [IO.File]::Move($partial,(Join-Path $database 'data.dump'))
    $manifest=[ordered]@{schemaVersion=1;kind='RackClickDatabaseBackup';postgresVersion='17.11';format='custom';dumpFile='data.dump';dumpBytes=(Get-Item -LiteralPath (Join-Path $database 'data.dump')).Length;dumpSha256=$dumpHash;createdUtc=[DateTime]::UtcNow.ToString('o')}
    Write-BackupNewText (Join-Path $database 'manifest.json') ($manifest | ConvertTo-Json -Compress)
    $manifestHash=Get-RuntimeConfigDigest (Join-Path $database 'manifest.json')
    $backupId=[guid]::NewGuid().ToString('D')
    $protocol.InputWriter.WriteLine((@{backupId=$backupId;manifestSha256=$manifestHash;dumpSha256=$dumpHash} | ConvertTo-Json -Compress));$protocol.InputWriter.Flush()
    $result=Read-MfaBackupResponse $protocol 'inventory_ready'
    Complete-MfaBackupProtocol $protocol
    $inventory=[Convert]::FromBase64String($result.inventoryBase64)
    if($inventory.Length -gt 65536 -or (Get-MfaBackupBytesHash $inventory) -cne $result.inventorySha256){throw 'mfa_backup_inventory_invalid'}
    Write-BackupNewText (Join-Path $destination 'mfa-inventory.json') ((New-Object Text.UTF8Encoding($false,$true)).GetString($inventory))
    $receipt=[ordered]@{format='RackClick.MfaBackupInventoryReceipt';formatVersion=1;installationId=$InstallationId;backupId=$backupId;inventorySha256=$result.inventorySha256;manifestSha256=$manifestHash;dumpSha256=$dumpHash;envelopeSha256=$ExpectedEnvelopeSha256}
    $receiptPath=Join-Path $registry ($backupId+'.json')
    Write-BackupNewText $receiptPath ($receipt | ConvertTo-Json -Compress)
    $receiptHash=Get-RuntimeConfigDigest $receiptPath
    # The external receipt is required by the consumer. An incomplete attempt is never a complete catalogue.
    [IO.File]::Delete((Join-Path $destination 'INCOMPLETE.json'))
    $report.success=$true;$report.code='mfa_backup_inventory_created';$report.inventorySha256=$result.inventorySha256
    $report.receiptSha256=$receiptHash;$report.backupId=$backupId
} catch {
    # Private inputs, SQL details and paths are deliberately not reflected.
    if ($_.Exception.Message -cmatch '^mfa_backup_[a-z_]+$') {$report.code=$_.Exception.Message}
} finally {
    if($passwordPointer -ne [IntPtr]::Zero){[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)}
    Close-MfaBackupProtocol $protocol; Close-MfaBackupTool $tool
}
$report | ConvertTo-Json -Compress
if($report.success){exit 0}else{exit 1}
