#requires -Version 5.1
[CmdletBinding()]
param([switch]$FunctionsOnly)
# Private viewer for this RC9 restoration only. No installed helper imports or credential changes.
function Stop-Rc9RestoredAccess([string]$Code){throw (New-Object InvalidOperationException($Code))}
function Get-Rc9RestoredBinding([string]$ServicePathName){
    if($ServicePathName-cnotmatch'^"C:\\ProgramData\\RackClick\\Instances\\([a-f0-9-]{36})\\instance\\content\\dependencies\\dotnet\\dotnet\.exe" '){Stop-Rc9RestoredAccess 'rc9_access_service_binding_invalid'}
    $id=$Matches[1];$guid=[guid]::Empty
    if(-not[guid]::TryParseExact($id,'D',[ref]$guid)-or$guid.ToString('D')-cne$id-or$id-ceq'606b8c29-41de-4dc0-b63d-ade836000d9e'){Stop-Rc9RestoredAccess 'rc9_access_service_binding_invalid'}
    $root='C:\ProgramData\RackClick\Instances\'+$id;$code='C:\Program Files\RackClick\'+$id;$instance=$root+'\instance'
    $expected='"'+$instance+'\content\dependencies\dotnet\dotnet.exe" "'+$code+'\service\RackClick.WindowsService.dll" --config "'+$instance+'\service-config.json"'
    if($ServicePathName-cne$expected){Stop-Rc9RestoredAccess 'rc9_access_service_binding_invalid'}
    return @{installationId=$id;serviceName='RackClick-Recovery-cb52d279';codeRoot=$code;instancePath=$instance;managementPath=($root+'\management');publicOrigin='https://192.168.250.78:5444';backupTaskName=('RackClick-Backup-'+$id)}
}
function Assert-Rc9RestoredReceipt($Receipt,$Binding){
    foreach($name in @('installationId','serviceName','codeRoot','instancePath','managementPath','publicOrigin','backupTaskName','accountName','serviceSid','manifestSha256')){if($Receipt.$name-isnot[string]){Stop-Rc9RestoredAccess 'rc9_access_receipt_binding_invalid'}}
    if($Receipt.schemaVersion-isnot[int]){Stop-Rc9RestoredAccess 'rc9_access_receipt_binding_invalid'}
    if($null-eq$Receipt-or$Receipt.schemaVersion-ne1-or$Receipt.installationId-cne$Binding.installationId-or$Receipt.serviceName-cne$Binding.serviceName-or$Receipt.codeRoot-cne$Binding.codeRoot-or$Receipt.instancePath-cne$Binding.instancePath-or$Receipt.managementPath-cne$Binding.managementPath-or$Receipt.publicOrigin-cne$Binding.publicOrigin-or$Receipt.backupTaskName-cne$Binding.backupTaskName-or$Receipt.accountName-cne'RackClickSvcRc9'-or$Receipt.serviceSid-isnot[string]-or$Receipt.serviceSid-cnotmatch'^S-1-5-21-(\d+-){3}\d+$'-or$Receipt.serviceSid.EndsWith('-500')-or$Receipt.manifestSha256-cnotmatch'^[a-f0-9]{64}$'){Stop-Rc9RestoredAccess 'rc9_access_receipt_binding_invalid'}
}
function Test-Rc9RestoredPrincipal([string]$Observed,[string]$ExpectedSid,[string]$LocalMachine,[string]$LocalName){
    if(-not[string]::Equals($LocalName,'RackClickSvcRc9',[StringComparison]::OrdinalIgnoreCase)-or[string]::IsNullOrEmpty($LocalMachine)-or$LocalMachine.Contains('\')-or$LocalMachine.Contains('@')){return $false}
    try{$sid=(New-Object Security.Principal.SecurityIdentifier($ExpectedSid)).Value;if($Observed-cmatch'^S-1-'){return (New-Object Security.Principal.SecurityIdentifier($Observed)).Value-ceq$sid}}catch{return $false}
    $name=if($Observed.StartsWith('.\',[StringComparison]::Ordinal)){$Observed.Substring(2)}elseif($Observed.StartsWith(($LocalMachine+'\'),[StringComparison]::OrdinalIgnoreCase)){$Observed.Substring($LocalMachine.Length+1)}else{return $false}
    return [string]::Equals($name,$LocalName,[StringComparison]::OrdinalIgnoreCase)
}
function Read-Rc9RestoredLogin([byte[]]$Bytes){
    try{if($null-eq$Bytes-or$Bytes.Length-eq0-or$Bytes.Length-gt65536){throw 'invalid'};$decoder=New-Object Text.UTF8Encoding($false,$true);$value=ConvertFrom-Json -InputObject ($decoder.GetString($Bytes)) -ErrorAction Stop
        if($null-eq$value-or$value-is[Array]-or@($value.PSObject.Properties).Count-ne2-or$value.username-isnot[string]-or$value.password-isnot[string]-or$value.username.Length-lt1-or$value.username.Length-gt256-or$value.password.Length-lt1-or$value.password.Length-gt4096-or$value.username-cmatch'[\x00-\x1F\x7F]'-or$value.password-cmatch'[\x00-\x1F\x7F]'){throw 'invalid'}
        return @{username=$value.username;password=$value.password}
    }catch{Stop-Rc9RestoredAccess 'rc9_access_login_invalid'}
}
function Initialize-Rc9RestoredReader {
    if('RackClickRc9PrivateReader'-as[type]){return}
    Add-Type -TypeDefinition @'
using System;using System.IO;using System.Collections.Generic;using System.Security.AccessControl;using System.ComponentModel;using System.Runtime.InteropServices;using Microsoft.Win32.SafeHandles;
public static class RackClickRc9PrivateReader {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern SafeFileHandle CreateFile(string p,uint a,uint s,IntPtr sa,uint c,uint f,IntPtr t);
 [DllImport("kernel32.dll",SetLastError=true)]static extern bool GetFileInformationByHandle(SafeFileHandle h,out Info i);
 [StructLayout(LayoutKind.Sequential)]struct Info{public uint Attributes,CreationLow,CreationHigh,AccessLow,AccessHigh,WriteLow,WriteHigh,Volume,SizeHigh,SizeLow,Links,IndexHigh,IndexLow;}
 [DllImport("advapi32.dll")]static extern uint GetSecurityInfo(SafeFileHandle h,int type,uint info,out IntPtr o,out IntPtr g,out IntPtr d,out IntPtr s,out IntPtr sd);
 [DllImport("advapi32.dll")]static extern uint GetSecurityDescriptorLength(IntPtr sd);
 [DllImport("kernel32.dll")]static extern IntPtr LocalFree(IntPtr p);
 public static bool IsPrivateSddl(string sddl){try{var sd=new RawSecurityDescriptor(sddl);if(sd.Owner==null||(sd.Owner.Value!="S-1-5-18"&&sd.Owner.Value!="S-1-5-32-544")||sd.DiscretionaryAcl==null||sd.DiscretionaryAcl.Count<2)return false;bool system=false,admin=false;foreach(GenericAce raw in sd.DiscretionaryAcl){var a=raw as CommonAce;if(a==null||a.IsCallback||a.AceQualifier!=AceQualifier.AccessAllowed)return false;if(a.SecurityIdentifier.Value=="S-1-5-18")system=true;else if(a.SecurityIdentifier.Value=="S-1-5-32-544")admin=true;else return false;}return system&&admin;}catch{return false;}}
 static void PrivateAcl(SafeFileHandle h){IntPtr o,g,d,s,sd;uint e=GetSecurityInfo(h,1,7,out o,out g,out d,out s,out sd);if(e!=0)throw new Win32Exception((int)e);try{uint size=GetSecurityDescriptorLength(sd);if(size==0||size>65536)throw new InvalidOperationException("rc9_access_private_acl_invalid");byte[] b=new byte[size];Marshal.Copy(sd,b,0,b.Length);if(!IsPrivateSddl(new RawSecurityDescriptor(b,0).GetSddlForm(AccessControlSections.Owner|AccessControlSections.Group|AccessControlSections.Access)))throw new InvalidOperationException("rc9_access_private_acl_invalid");}finally{LocalFree(sd);}}
 static SafeFileHandle Open(string path,bool directory){var h=CreateFile(path,directory?0x20080u:0x80020000u,1,IntPtr.Zero,3,0x02200000,IntPtr.Zero);if(h.IsInvalid){int e=Marshal.GetLastWin32Error();h.Dispose();throw new Win32Exception(e);}Info i;if(!GetFileInformationByHandle(h,out i)){int e=Marshal.GetLastWin32Error();h.Dispose();throw new Win32Exception(e);}if((i.Attributes&0x400)!=0||((i.Attributes&0x10)!=0)!=directory||(!directory&&i.Links!=1)){h.Dispose();throw new InvalidOperationException("rc9_access_private_path_invalid");}return h;}
 public static byte[] Read(string path,string management,int maximum){if(!String.Equals(Path.GetDirectoryName(path),management,StringComparison.Ordinal)||maximum<1||maximum>1048576)throw new InvalidOperationException("rc9_access_private_path_invalid");var parents=new List<SafeFileHandle>();try{for(string p=Path.GetDirectoryName(path);!String.IsNullOrEmpty(p);p=Path.GetDirectoryName(p)){var h=Open(p,true);parents.Add(h);if(String.Equals(p,management,StringComparison.Ordinal))PrivateAcl(h);}using(var h=Open(path,false)){PrivateAcl(h);using(var f=new FileStream(h,FileAccess.Read)){if(f.Length<=0||f.Length>maximum)throw new InvalidOperationException("rc9_access_private_size_invalid");byte[] bytes=new byte[(int)f.Length];int at=0;while(at<bytes.Length){int n=f.Read(bytes,at,bytes.Length-at);if(n<=0)throw new EndOfStreamException();at+=n;}if(f.ReadByte()!=-1)throw new InvalidOperationException("rc9_access_private_read_failed");return bytes;}}}finally{foreach(var h in parents)h.Dispose();}}
}
'@
}
function Show-Rc9RestoredLoginWindow($Login){
    Add-Type -AssemblyName System.Windows.Forms;Add-Type -AssemblyName System.Drawing
    [Windows.Forms.Application]::EnableVisualStyles();$form=New-Object Windows.Forms.Form;$form.Text='RackClick RC9 - Acceso privado';$form.StartPosition='CenterScreen';$form.ClientSize=New-Object Drawing.Size(590,290);$form.MinimumSize=$form.Size;$form.MaximizeBox=$false;$form.AutoScaleMode='Dpi';$form.Font=New-Object Drawing.Font('Segoe UI',10)
    $layout=New-Object Windows.Forms.TableLayoutPanel;$layout.Dock='Fill';$layout.Padding=New-Object Windows.Forms.Padding(18);$layout.ColumnCount=2;$layout.RowCount=6;$layout.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Absolute',110)))|Out-Null;$layout.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent',100)))|Out-Null;$form.Controls.Add($layout)
    $notice=New-Object Windows.Forms.Label;$notice.Text='Acceso de la restauracion RC9. Conserva estos datos en privado.';$notice.AutoSize=$true;$notice.Dock='Fill';$layout.Controls.Add($notice,0,0);$layout.SetColumnSpan($notice,2)
    $url=New-Object Windows.Forms.Label;$url.Text='https://192.168.250.78:5444';$url.AutoSize=$true;$url.Dock='Fill';$layout.Controls.Add($url,0,1);$layout.SetColumnSpan($url,2)
    $usernameLabel=New-Object Windows.Forms.Label;$usernameLabel.Text='Usuario';$usernameLabel.AutoSize=$true;$layout.Controls.Add($usernameLabel,0,2)
    $username=New-Object Windows.Forms.TextBox;$username.Text=$Login.username;$username.ReadOnly=$true;$username.ShortcutsEnabled=$false;$username.ContextMenu=New-Object Windows.Forms.ContextMenu;$username.Dock='Fill';$layout.Controls.Add($username,1,2)
    $passwordLabel=New-Object Windows.Forms.Label;$passwordLabel.Text='Contrasena';$passwordLabel.AutoSize=$true;$layout.Controls.Add($passwordLabel,0,3)
    $password=New-Object Windows.Forms.TextBox;$password.Text=$Login.password;$password.ReadOnly=$true;$password.UseSystemPasswordChar=$true;$password.ShortcutsEnabled=$false;$password.ContextMenu=New-Object Windows.Forms.ContextMenu;$password.Dock='Fill';$layout.Controls.Add($password,1,3)
    $reveal=New-Object Windows.Forms.CheckBox;$reveal.Text='Mostrar contrasena';$reveal.AutoSize=$true;$reveal.Add_CheckedChanged({$password.UseSystemPasswordChar=-not$reveal.Checked});$layout.Controls.Add($reveal,1,4)
    $buttons=New-Object Windows.Forms.FlowLayoutPanel;$buttons.AutoSize=$true;$buttons.Dock='Fill';$open=New-Object Windows.Forms.Button;$open.Text='Abrir RackClick';$open.AutoSize=$true;$open.Add_Click({try{$null=Start-Process -FilePath 'https://192.168.250.78:5444'}catch{[Windows.Forms.MessageBox]::Show('No se pudo abrir RackClick.','RackClick','OK','Error')|Out-Null}});$buttons.Controls.Add($open)
    $close=New-Object Windows.Forms.Button;$close.Text='Cerrar';$close.AutoSize=$true;$close.Add_Click({$form.Close()});$buttons.Controls.Add($close);$layout.Controls.Add($buttons,0,5);$layout.SetColumnSpan($buttons,2);$form.CancelButton=$close
    try{$null=$form.ShowDialog()}finally{$password.Clear();$username.Clear();$Login.password=$null;$Login.username=$null;$form.Dispose()}
}
if($FunctionsOnly){return}
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$result=[ordered]@{schemaVersion=1;valid=$false;success=$false;exitCode=2;code='rc9_access_failed'};$exit=2;$bytes=$null;$login=$null;$modulePath=$env:PSModulePath
try{
    if($PSVersionTable.PSEdition-cne'Desktop'-or$PSVersionTable.PSVersion.Major-ne5-or-not[Environment]::Is64BitProcess-or[Threading.Thread]::CurrentThread.ApartmentState-ne'STA'-or-not(New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){Stop-Rc9RestoredAccess 'rc9_access_elevated_winps51_x64_sta_required'}
    $env:PSModulePath=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules';$services=@(Get-CimInstance Win32_Service -Filter "Name='RackClick-Recovery-cb52d279'");if($services.Count-ne1-or$services[0].Name-cne'RackClick-Recovery-cb52d279'){Stop-Rc9RestoredAccess 'rc9_access_service_missing'};$binding=Get-Rc9RestoredBinding $services[0].PathName
    Initialize-Rc9RestoredReader;$bytes=[RackClickRc9PrivateReader]::Read(($binding.managementPath+'\server-installation.json'),$binding.managementPath,1048576);$decoder=New-Object Text.UTF8Encoding($false,$true);$receipt=ConvertFrom-Json -InputObject ($decoder.GetString($bytes));Assert-Rc9RestoredReceipt $receipt $binding;[Array]::Clear($bytes,0,$bytes.Length);$bytes=$null
    $sam=@(Get-LocalUser -SID (New-Object Security.Principal.SecurityIdentifier($receipt.serviceSid)));if($sam.Count-ne1-or$sam[0].SID.Value-cne$receipt.serviceSid-or-not(Test-Rc9RestoredPrincipal $services[0].StartName $receipt.serviceSid ([Environment]::MachineName) ([string]$sam[0].Name))){Stop-Rc9RestoredAccess 'rc9_access_service_identity_invalid'}
    $bytes=[RackClickRc9PrivateReader]::Read(($binding.managementPath+'\admin-login.json'),$binding.managementPath,65536);$login=Read-Rc9RestoredLogin $bytes;[Array]::Clear($bytes,0,$bytes.Length);$bytes=$null;Show-Rc9RestoredLoginWindow $login
    $result.valid=$true;$result.success=$true;$result.exitCode=0;$result.code='rc9_access_window_closed';$exit=0
}catch{$allowed=@('rc9_access_elevated_winps51_x64_sta_required','rc9_access_service_missing','rc9_access_service_binding_invalid','rc9_access_receipt_binding_invalid','rc9_access_service_identity_invalid','rc9_access_login_invalid','rc9_access_private_acl_invalid','rc9_access_private_path_invalid','rc9_access_private_size_invalid','rc9_access_private_read_failed');$cause=$_.Exception;for($i=0;$i-lt8-and$null-ne$cause.InnerException;$i++){$cause=$cause.InnerException};if($cause.Message-cin$allowed){$result.code=$cause.Message};$result.errorHResult=$cause.HResult}
finally{if($bytes){[Array]::Clear($bytes,0,$bytes.Length)};if($login){$login.password=$null;$login.username=$null};[Environment]::SetEnvironmentVariable('PSModulePath',$modulePath,'Process')}
$result|ConvertTo-Json -Compress
exit $exit
