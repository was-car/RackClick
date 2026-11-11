#requires -Version 5.1
[CmdletBinding()]
param([string]$PostgresBinPath='', [string]$DotnetPath='', [string]$ToolDirectory='', [string]$ExpectedToolSumsSha256='',
      [string]$BackupDirectory='', [string]$ReceiptPath='', [string]$ExpectedReceiptSha256='')
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
$mfaRuntimeHostPath=$DotnetPath
. (Join-Path $PSScriptRoot 'RackClick.MfaBackupInventory.ps1')
$tool=$null;$protocol=$null;$held=$null
$report=[ordered]@{schemaVersion=1;success=$false;code='mfa_backup_verification_failed';requiredVersions=@();catalogComplete=$false;retirementAuthorized=$false}
try{
    $receipt=Read-MfaBackupReceipt $ReceiptPath $ExpectedReceiptSha256
    $root=Assert-BackupPath $BackupDirectory;Assert-BackupNoReparse $root
    if((@(Get-ChildItem -LiteralPath $root -Force | Select-Object -ExpandProperty Name | Sort-Object) -join ',') -cne 'database,mfa-inventory.json'){throw 'mfa_backup_container_invalid'}
    $held=Read-BackupManifest (Join-Path $root 'database') $receipt.manifestSha256
    if($held.hash -cne $receipt.dumpSha256){throw 'mfa_backup_dump_pin_invalid'}
    $bytes=Read-MfaBackupBytes (Join-Path $root 'mfa-inventory.json') 65536
    $tool=Open-MfaBackupTool $ToolDirectory $ExpectedToolSumsSha256
    $protocol=Start-MfaBackupProtocol $mfaRuntimeHostPath $tool
    $request=[ordered]@{operation='verify';installationId=$receipt.installationId;inventoryBase64=[Convert]::ToBase64String($bytes);inventorySha256=$receipt.inventorySha256;manifestSha256=$receipt.manifestSha256;dumpSha256=$receipt.dumpSha256;envelopeSha256=$receipt.envelopeSha256}
    $protocol.InputWriter.WriteLine(($request | ConvertTo-Json -Compress));$protocol.InputWriter.Flush()
    $verified=Read-MfaBackupResponse $protocol 'inventory_verified'
    Complete-MfaBackupProtocol $protocol
    if($verified.backupId -cne $receipt.backupId){throw 'mfa_backup_scope_invalid'}
    $report.success=$true;$report.code='mfa_backup_inventory_verified';$report.requiredVersions=@($verified.requiredVersions)
}catch{if($_.Exception.Message -cmatch '^mfa_backup_[a-z_]+$'){$report.code=$_.Exception.Message}}
finally{
    if($null -ne $held){$held.manifestHandle.Dispose();$held.dumpHandle.Dispose()}
    Close-MfaBackupProtocol $protocol;Close-MfaBackupTool $tool
}
$report | ConvertTo-Json -Compress
if($report.success){exit 0}else{exit 1}
