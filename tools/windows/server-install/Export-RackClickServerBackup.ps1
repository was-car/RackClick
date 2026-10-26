#requires -Version 5.1
[CmdletBinding()]
param([string]$ManagementPath='')
$ErrorActionPreference='Stop'
$exportInputs=@{management=$ManagementPath}
. (Join-Path $PSScriptRoot 'Show-RackClickInstalledServer.ps1') -FunctionsOnly
. (Join-Path $PSScriptRoot 'RackClick.Setup.Recovery.ps1')
$ManagementPath=$exportInputs.management
if(-not(Test-SetupAdministrator)){
    try{$elevated=Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList @('-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',(ConvertTo-SetupArgument $PSCommandPath),'-ManagementPath',(ConvertTo-SetupArgument $ManagementPath)) -Verb RunAs -Wait -PassThru;exit $elevated.ExitCode}catch{Write-Error 'No se pudo abrir la exportacion como administrador.';exit 1}
}
function Test-ExportBackupReceipt($Latest,[string]$InstancePath){
    if($null-eq$Latest-or$Latest.valid-isnot[bool]-or$Latest.success-isnot[bool]-or-not$Latest.valid-or-not$Latest.success-or$Latest.exitCode-isnot[int]-or$Latest.exitCode-ne0-or$Latest.code-cne'scheduled_backup_complete'-or$Latest.manifestSha256-cnotmatch'^[a-f0-9]{64}$'){return $false}
    $prefix=$InstancePath+'\runtime\backups\'
    if($Latest.backupPath-isnot[string]-or-not$Latest.backupPath.StartsWith($prefix,[StringComparison]::Ordinal)-or$Latest.backupPath.Substring($prefix.Length)-cnotmatch'^daily-\d{8}T\d{9}Z-[a-f0-9]{32}$'-or$Latest.manifestPath-cne($Latest.backupPath+'\manifest.json')){return $false}
    return $true
}
function Initialize-ExportBackupNative {
    if('RackClickExportBackupNative'-as[type]){return}
    Add-Type -TypeDefinition @'
using System;using System.IO;using System.Collections.Generic;using System.ComponentModel;using System.Runtime.InteropServices;using Microsoft.Win32.SafeHandles;
public static class RackClickExportBackupNative {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern SafeFileHandle CreateFile(string p,uint a,uint s,IntPtr sa,uint c,uint f,IntPtr h);
 [StructLayout(LayoutKind.Sequential)]struct TAG{public uint Attributes;public uint ReparseTag;}
 [DllImport("kernel32.dll",SetLastError=true)]static extern bool GetFileInformationByHandleEx(SafeFileHandle h,int cls,out TAG info,uint size);
 static SafeFileHandle Open(string p,bool dir){var h=CreateFile(p,0x81,dir?3u:1u,IntPtr.Zero,3,0x02200000,IntPtr.Zero);if(h.IsInvalid){h.Dispose();throw new Win32Exception();}TAG t;if(!GetFileInformationByHandleEx(h,9,out t,8)||(t.Attributes&0x400)!=0||((t.Attributes&0x10)!=0)!=dir){h.Dispose();throw new InvalidOperationException("export_source_reparse_or_type_invalid");}return h;}
 public static List<SafeFileHandle> Hold(string root){var result=new List<SafeFileHandle>();try{string p=root;while(!String.IsNullOrEmpty(p)){result.Add(Open(p,true));p=Path.GetDirectoryName(p);}result.Add(Open(Path.Combine(root,"manifest.json"),false));result.Add(Open(Path.Combine(root,"data.dump"),false));return result;}catch{foreach(var h in result)h.Dispose();throw;}}
}
'@
}
$exportExit=1;$exportDestination='';$exportHandles=$null;$exportDialog=$null
$exportResult=[ordered]@{schemaVersion=1;valid=$false;success=$false;exitCode=1;code='export_failed';backupPath='';manifestSha256=''}
try{
    Assert-SetupAdministrator
    if([Threading.Thread]::CurrentThread.ApartmentState-ne'STA'){throw 'export_sta_required'}
    $receipt=Read-InstalledServerReceipt $ManagementPath
    $latestBytes=Read-SetupPreparedFile -InstancePath $receipt.instancePath -RelativePath 'runtime/control/latest-backup.json' -ServiceSid $receipt.serviceSid
    $latest=(New-Object Text.UTF8Encoding($false,$true)).GetString($latestBytes)|ConvertFrom-Json -ErrorAction Stop
    if(-not(Test-ExportBackupReceipt $latest $receipt.instancePath)){throw 'export_latest_backup_not_valid'}
    Add-Type -AssemblyName System.Windows.Forms
    $exportDialog=New-Object Windows.Forms.FolderBrowserDialog
    $exportDialog.Description='Elige una carpeta local NTFS (documentos o USB). Se creara RackClick-Backups y una copia nueva, sin borrar el backup original.'
    $exportDialog.SelectedPath=[Environment]::GetFolderPath('MyDocuments');$exportDialog.ShowNewFolderButton=$true
    if($exportDialog.ShowDialog()-ne'OK'){$exportResult.code='export_cancelled';$exportResult.exitCode=0;$exportResult|ConvertTo-Json -Compress;exit 0}
    $selected=[IO.Path]::GetFullPath($exportDialog.SelectedPath);Assert-SetupNoReparse $selected
    $drive=New-Object IO.DriveInfo([IO.Path]::GetPathRoot($selected))
    if($drive.DriveFormat-cne'NTFS'){throw 'export_local_ntfs_required'}
    $base=Join-Path $selected 'RackClick-Backups';Assert-SetupNoReparse $base
    $null=[IO.Directory]::CreateDirectory($base)
    $exportDestination=Join-Path $base ([guid]::NewGuid().ToString('D'))
    if(Test-Path -LiteralPath $exportDestination){throw 'export_destination_exists'}
    $acl=New-Object Security.AccessControl.DirectorySecurity;$acl.SetSecurityDescriptorSddlForm('O:BAG:SYD:P(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)')
    $null=[IO.Directory]::CreateDirectory($exportDestination,$acl);Assert-SetupManagementAcl $exportDestination
    Initialize-ExportBackupNative
    # Backup-intent handles validate every source ancestor and pin both regular
    # files against writes/deletion until the independently hashed copy exists.
    $exportHandles=Invoke-SetupSecurityPrivileges {,[RackClickExportBackupNative]::Hold($latest.backupPath)}
    $robocopy=Join-Path $env:SystemRoot 'System32\robocopy.exe'
    $output=Join-Path $ManagementPath ('export-'+[guid]::NewGuid().ToString('N')+'.robocopy.log')
    $args=@((ConvertTo-SetupArgument $latest.backupPath),(ConvertTo-SetupArgument $exportDestination),'manifest.json','data.dump','/B','/COPY:DAT','/R:0','/W:0','/XJ','/NFL','/NDL','/NJH','/NJS','/NP')
    $copy=Start-Process -FilePath $robocopy -ArgumentList $args -Wait -PassThru -WindowStyle Hidden -RedirectStandardOutput $output -RedirectStandardError ($output+'.stderr')
    try{if($copy.ExitCode-lt0-or$copy.ExitCode-gt7){throw 'export_copy_failed'}}finally{$copy.Dispose()}
    $files=@(Get-ChildItem -LiteralPath $exportDestination -Force)
    if($files.Count-ne2-or@($files|Where-Object{$_.PSIsContainer-or$_.Name-cnotin@('manifest.json','data.dump')}).Count){throw 'export_copy_inventory_invalid'}
    foreach($file in $files){Assert-SetupNoReparse $file.FullName;Assert-SetupManagementAcl $file.FullName}
    $manifestPath=Join-Path $exportDestination 'manifest.json';$dumpPath=Join-Path $exportDestination 'data.dump'
    if((Get-Item -LiteralPath $manifestPath).Length-gt65536-or(Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()-cne$latest.manifestSha256){throw 'export_manifest_hash_mismatch'}
    $manifest=[IO.File]::ReadAllText($manifestPath)|ConvertFrom-Json -ErrorAction Stop
    Test-SetupRecoveryManifest $manifest (Get-Item -LiteralPath $dumpPath).Length (Get-FileHash -LiteralPath $dumpPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $shaPath=$exportDestination+'.sha256.txt';$shaStream=[IO.File]::Open($shaPath,'CreateNew','Write','None')
    try{
        $shaAcl=New-Object Security.AccessControl.FileSecurity;$shaAcl.SetSecurityDescriptorSddlForm('O:BAD:P(A;;FA;;;BA)(A;;FA;;;SY)');Set-Acl -LiteralPath $shaPath -AclObject $shaAcl
        $shaBytes=(New-Object Text.UTF8Encoding($false)).GetBytes($latest.manifestSha256+[Environment]::NewLine);$shaStream.Write($shaBytes,0,$shaBytes.Length);$shaStream.Flush($true)
    }finally{$shaStream.Dispose()}
    $exportResult.valid=$true;$exportResult.success=$true;$exportResult.exitCode=0;$exportResult.code='export_complete';$exportResult.backupPath=$exportDestination;$exportResult.manifestSha256=$latest.manifestSha256;$exportExit=0
    Write-SetupJson (Join-Path $ManagementPath ('backup-export-'+[guid]::NewGuid().ToString('N')+'.json')) $exportResult
    [Windows.Forms.MessageBox]::Show(('Backup exportado y verificado.'+"`r`n`r`n"+$exportDestination+"`r`n`r`nSHA256 del manifiesto: "+$latest.manifestSha256+"`r`nCopia del SHA256: "+$shaPath+"`r`n`r`nGuarda los dos archivos del backup juntos. Contienen datos privados del laboratorio."),'RackClick','OK','Information')|Out-Null
}catch{
    if($_.Exception.Message-cmatch'^export_[a-z0-9_]{1,90}$'){$exportResult.code=$_.Exception.Message}
    if('Windows.Forms.MessageBox'-as[type]){[Windows.Forms.MessageBox]::Show(('No se confirmo la exportacion: '+$exportResult.code+'. El backup original se conserva. La carpeta parcial no se debe usar para restaurar.'),'RackClick','OK','Error')|Out-Null}
}finally{
    if($null-ne$exportHandles){foreach($handle in $exportHandles){$handle.Dispose()}}
    if($null-ne$exportDialog){$exportDialog.Dispose()}
}
$exportResult|ConvertTo-Json -Compress
exit $exportExit
