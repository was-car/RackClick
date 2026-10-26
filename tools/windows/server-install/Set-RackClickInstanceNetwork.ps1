#requires -Version 5.1
[CmdletBinding()]
param([string]$InstallationId='', [string]$BindAddress='', [string]$AllowedSubnet='', [string]$PublicHost='', [int]$HttpsPort=0, [int]$PostgresPort=0, [switch]$EnsureRunning, [switch]$CheckOnly, [switch]$FunctionsOnly)
# Standalone maintenance of an explicitly identified frozen 05 installation.
# Original and restored instances are validated independently. No Windows network,
# PostgreSQL credentials, database content, or installed product-code changes.
function Stop-RcNetwork([string]$Code){throw (New-Object InvalidOperationException($Code))}
function Get-RcNetworkCodes {return @('network_installation_not_supported','network_bind_invalid','network_subnet_invalid','network_subnet_not_canonical','network_subnet_excludes_bind','network_public_host_invalid','network_transform_binding_invalid','network_backup_arguments_invalid','network_account_unresolved','network_reparse_rejected','network_code_owner_invalid','network_code_acl_invalid','network_frozen_payload_mismatch','network_payload_path_invalid','network_installed_code_changed','network_helper_missing','network_helper_invalid','network_file_acl_invalid','network_file_not_regular','network_file_size_invalid','network_write_verification_failed','network_destination_exists','network_snapshot_verify_failed','network_preflight_files_changed','network_service_not_stopped','network_postgres_pid_present','network_port_in_use','network_snapshot_required','network_backup_running','network_task_update_verification_failed','network_ca_already_present','network_child_command_too_long','network_child_timeout_do_not_repeat','network_child_failed','network_scheduled_backup_failed','network_backup_timeout_do_not_repeat','network_backup_receipt_invalid','network_backup_manifest_mismatch','network_backup_manifest_invalid','network_backup_dump_mismatch','network_backup_dump_invalid','network_profile_verify_failed','network_service_start_failed','network_health_failed','network_receipt_binding_invalid','network_profile_hash_mismatch','network_configuration_binding_invalid','network_installation_hash_mismatch','network_ports_not_supported','network_tls_hash_mismatch','network_service_binding_invalid','network_target_ip_not_preferred','network_dns_binding_invalid','network_task_binding_invalid','network_firewall_binding_invalid','network_ca_binding_invalid','network_elevated_winps51_x64_required','network_recovery_required','network_preflight_state_changed')}
function Get-RcNetworkHash([byte[]]$Bytes){$s=[Security.Cryptography.SHA256]::Create();try{return ([BitConverter]::ToString($s.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant()}finally{$s.Dispose()}}
function ConvertTo-RcNetworkBytes($Value){return ,([Text.Encoding]::UTF8.GetBytes(($Value|ConvertTo-Json -Depth 30 -Compress)))}
function Get-RcNetworkPlan([string]$InstallationId,[string]$BindAddress,[string]$AllowedSubnet,[string]$PublicHost='', [int]$HttpsPort=0, [int]$PostgresPort=0){
    $id=[guid]::Empty;$ip=$null
    if(-not[guid]::TryParseExact($InstallationId,'D',[ref]$id)-or$id.ToString('D')-cne$InstallationId-or$id-eq[guid]::Empty){Stop-RcNetwork 'network_installation_not_supported'}
    if(-not[Net.IPAddress]::TryParse($BindAddress,[ref]$ip)-or$ip.AddressFamily-ne[Net.Sockets.AddressFamily]::InterNetwork-or$ip.ToString()-cne$BindAddress-or$ip.GetAddressBytes()[0]-in@(0,127)-or$ip.GetAddressBytes()[0]-ge224-or($ip.GetAddressBytes()[0]-eq169-and$ip.GetAddressBytes()[1]-eq254)){Stop-RcNetwork 'network_bind_invalid'}
    if($AllowedSubnet-cnotmatch'^([0-9.]+)/([0-9]{1,2})$'){Stop-RcNetwork 'network_subnet_invalid'}
    $base=$null;$prefix=[int]$Matches[2];$baseText=$Matches[1]
    if($prefix-lt1-or$prefix-gt32-or-not[Net.IPAddress]::TryParse($baseText,[ref]$base)-or$base.AddressFamily-ne[Net.Sockets.AddressFamily]::InterNetwork-or$base.ToString()-cne$baseText-or$AllowedSubnet-cne($baseText+'/'+$prefix)){Stop-RcNetwork 'network_subnet_invalid'}
    if($HttpsPort-lt1024-or$HttpsPort-gt65535-or$PostgresPort-lt1024-or$PostgresPort-gt65535-or$HttpsPort-eq$PostgresPort){Stop-RcNetwork 'network_ports_not_supported'}
    $a=$ip.GetAddressBytes();$b=$base.GetAddressBytes()
    for($n=0;$n-lt4;$n++){$bits=[Math]::Min(8,[Math]::Max(0,$prefix-$n*8));$mask=if($bits-eq0){0}else{256-[Math]::Pow(2,8-$bits)};if(($b[$n]-band[int]$mask)-ne$b[$n]){Stop-RcNetwork 'network_subnet_not_canonical'};if(($a[$n]-band[int]$mask)-ne$b[$n]){Stop-RcNetwork 'network_subnet_excludes_bind'}}
    if($PublicHost-ceq''){$PublicHost=$BindAddress}
    $hostIp=$null
    if([Net.IPAddress]::TryParse($PublicHost,[ref]$hostIp)){if($PublicHost-cne$BindAddress){Stop-RcNetwork 'network_public_host_invalid'}}
    elseif($PublicHost-cnotmatch'^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$'-or[Uri]::CheckHostName($PublicHost)-ne[UriHostNameType]::Dns-or$PublicHost-ieq'localhost'){Stop-RcNetwork 'network_public_host_invalid'}
    return @{installationId=$InstallationId;bindAddress=$BindAddress;publicHost=$PublicHost;allowedSubnet=$AllowedSubnet;publicOrigin=('https://'+$PublicHost+':'+$HttpsPort);httpsPort=$HttpsPort;postgresPort=$PostgresPort}
}
function ConvertTo-RcNetworkFirewallAddress([string]$Value){
    # NetSecurity may return a prefix as a dotted network mask. Compare its
    # meaning, never loosen the rule to Any or ignore extra addresses.
    if($Value-cnotmatch'^([0-9.]+)(?:/([0-9.]+))?$'){return ''}
    $addressText=$Matches[1];$suffix=$Matches[2];$address=$null
    if(-not[Net.IPAddress]::TryParse($addressText,[ref]$address)-or$address.AddressFamily-ne[Net.Sockets.AddressFamily]::InterNetwork-or$address.ToString()-cne$addressText){return ''}
    $prefix=32
    if($suffix){
        if($suffix-cmatch'^[0-9]{1,2}$'){$prefix=[int]$suffix;if($prefix-lt1-or$prefix-gt32-or[string]$prefix-cne$suffix){return ''}}
        else{$maskAddress=$null;if(-not[Net.IPAddress]::TryParse($suffix,[ref]$maskAddress)-or$maskAddress.AddressFamily-ne[Net.Sockets.AddressFamily]::InterNetwork-or$maskAddress.ToString()-cne$suffix){return ''};$prefix=0;$zeroSeen=$false;foreach($octet in $maskAddress.GetAddressBytes()){for($bit=7;$bit-ge0;$bit--){if(($octet-band(1-shl$bit))-ne0){if($zeroSeen){return ''};$prefix++}else{$zeroSeen=$true}}};if($prefix-eq0){return ''}}
    }
    $bytes=$address.GetAddressBytes();for($i=0;$i-lt4;$i++){$bits=[Math]::Min(8,[Math]::Max(0,$prefix-$i*8));$mask=if($bits-eq0){0}else{256-[Math]::Pow(2,8-$bits)};if(($bytes[$i]-band[int]$mask)-ne$bytes[$i]){return ''}}
    return $addressText+'/'+$prefix
}
function Test-RcNetworkFirewallAddresses([string[]]$Observed,[string[]]$Expected){
    if(@($Observed).Count-ne1-or@($Expected).Count-ne1){return $false}
    $a=ConvertTo-RcNetworkFirewallAddress $Observed[0];$b=ConvertTo-RcNetworkFirewallAddress $Expected[0]
    return ($a-cne''-and$b-cne''-and$a-ceq$b)
}
function Get-RcNetworkBackupArguments($Receipt,[string]$Hash){
    return '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+(Join-Path $Receipt.codeRoot 'operators\server-install\Invoke-RackClickScheduledBackup.ps1')+'" -ManifestPath "'+(Join-Path $Receipt.instancePath 'runtime\server-profile.json')+'" -ExpectedManifestSha256 '+$Hash
}
function Assert-RcNetworkReceipt($Receipt,$Plan){
    # This is deliberately pure, so original/restored and cross-instance bindings
    # are exercised without opening a credential file or operating services.
    $parent='C:\ProgramData\RackClick\Instances\'+$Plan.installationId
    if($Receipt.schemaVersion-ne1-or$Receipt.installationId-cne$Plan.installationId-or
       $Receipt.instancePath-cne(Join-Path $parent 'instance')-or$Receipt.managementPath-cne(Join-Path $parent 'management')-or
       $Receipt.codeRoot-cne('C:\Program Files\RackClick\'+$Plan.installationId)-or
       $Receipt.serviceName-cnotmatch'^RackClick(?:-Recovery-[a-f0-9]{8,32})?$'-or
       $Receipt.firewallRule-cne('RackClick-'+$Plan.installationId)-or$Receipt.backupTaskName-cne('RackClick-Backup-'+$Plan.installationId)-or
       $Receipt.manifestSha256-cnotmatch'^[a-f0-9]{64}$'-or$Receipt.serviceSid-cnotmatch'^S-1-5-21-(\d+-){3}\d+$'-or$Receipt.serviceSid.EndsWith('-500')-or
       $Receipt.backupExecutable-cne(Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe')){Stop-RcNetwork 'network_receipt_binding_invalid'}
    $origin=$null
    if(-not[uri]::TryCreate([string]$Receipt.publicOrigin,[UriKind]::Absolute,[ref]$origin)-or$origin.Scheme-cne'https'-or
       $origin.Port-ne$Plan.httpsPort-or$origin.UserInfo-cne''-or$origin.Query-cne''-or$origin.Fragment-cne''-or$origin.AbsolutePath-cne'/'-or
       $Receipt.publicOrigin-cne('https://'+$origin.Host+':'+$Plan.httpsPort)){Stop-RcNetwork 'network_configuration_binding_invalid'}
    if($Receipt.backupArguments-cne(Get-RcNetworkBackupArguments $Receipt $Receipt.manifestSha256)){Stop-RcNetwork 'network_backup_arguments_invalid'}
}
function Assert-RcNetworkInstanceBinding($Receipt,$Profile,$Installation,$Deployment,$Instance,$Plan){
    Assert-RcNetworkReceipt $Receipt $Plan
    $deploymentPath=Join-Path $Receipt.instancePath 'deployment';$instancePath=Join-Path $deploymentPath 'instance'
    if($Installation.schemaVersion-cnotin@(1,2)-or$Installation.kind-cne'RackClickPrivateInstallation'-or$Installation.state-cne'prepared'-or
       $Installation.rootPath-cne$Receipt.instancePath-or$Installation.deploymentId-cne$Deployment.id-or$Installation.deploymentSha256-cne$Profile.deploymentSha256-or
       $Deployment.schemaVersion-ne1-or$Deployment.kind-cne'RackClickPrivateDeployment'-or$Deployment.state-cne'prepared'-or
       $Deployment.rootPath-cne$deploymentPath-or$Profile.deploymentPath-cne$deploymentPath-or$Instance.rootPath-cne$instancePath-or
       $Instance.stagePath-cne(Join-Path $deploymentPath 'distribution')-or$Instance.id-cne$Deployment.instanceId-or
       $Instance.schemaVersion-ne1-or$Instance.kind-cne'RackClickLabInstance'-or$Instance.state-cne'initialized'-or
       $Instance.stageManifestSha256-cne$Deployment.stageManifestSha256-or$Instance.stageReceiptSha256-cne$Deployment.stageReceiptSha256){Stop-RcNetwork 'network_installation_hash_mismatch'}
    if(($Instance.httpPort-isnot[int]-and$Instance.httpPort-isnot[long])-or($Instance.postgresPort-isnot[int]-and$Instance.postgresPort-isnot[long])-or
       $Instance.httpPort-ne$Plan.httpsPort-or$Instance.postgresPort-ne$Plan.postgresPort-or([uri]$Profile.publicOrigin).Port-ne$Plan.httpsPort){Stop-RcNetwork 'network_ports_not_supported'}
}
function ConvertTo-RcNetworkConfiguration($Profile,$Config,$Receipt,$Tls,$Plan){
    $p=($Profile|ConvertTo-Json -Depth 30 -Compress)|ConvertFrom-Json;$c=($Config|ConvertTo-Json -Depth 30 -Compress)|ConvertFrom-Json;$r=($Receipt|ConvertTo-Json -Depth 30 -Compress)|ConvertFrom-Json
    Assert-RcNetworkReceipt $r $Plan
    if(([uri]$p.publicOrigin).Port-ne$Plan.httpsPort-or$r.installationId-cne$Plan.installationId-or$c.serverManifestSha256-cne$r.manifestSha256-or$c.serviceName-cne$r.serviceName-or$p.installationPath-cne$r.instancePath-or$p.runtimeRoot-cne(Join-Path $r.instancePath 'runtime')-or$p.expectedWindowsSid-cne$r.serviceSid-or$c.serverManifestPath-cne(Join-Path $p.runtimeRoot 'server-profile.json')){Stop-RcNetwork 'network_transform_binding_invalid'}
    $p.publicOrigin=$Plan.publicOrigin;$p.bindAddress=$Plan.bindAddress
    $p.certificate=[pscustomobject]@{certificateSha256=$Tls.certificateSha256;thumbprint=$Tls.thumbprint;expiresUtc=$Tls.expiresUtc;files=[pscustomobject]$Tls.files}
    $pb=ConvertTo-RcNetworkBytes $p;$hash=Get-RcNetworkHash $pb
    $c.serverManifestSha256=$hash;$r.publicOrigin=$Plan.publicOrigin;$r.manifestSha256=$hash;$r.trustedCaThumbprint=$Tls.rootThumbprint
    if($r.backupArguments-cnotmatch' -ExpectedManifestSha256 [a-f0-9]{64}$'){Stop-RcNetwork 'network_backup_arguments_invalid'}
    $r.backupArguments=[regex]::Replace($r.backupArguments,'(?<= -ExpectedManifestSha256 )[a-f0-9]{64}$',$hash)
    return @{profile=$p;config=$c;receipt=$r;profileBytes=$pb;profileSha256=$hash;configBytes=(ConvertTo-RcNetworkBytes $c);receiptBytes=(ConvertTo-RcNetworkBytes $r)}
}
function Resolve-RcNetworkSid([string]$Account){try{if($Account-match'^S-1-'){return (New-Object Security.Principal.SecurityIdentifier($Account)).Value};if($Account.StartsWith('.\',[StringComparison]::Ordinal)){$Account=[Environment]::MachineName+'\'+$Account.Substring(2)};return (New-Object Security.Principal.NTAccount($Account)).Translate([Security.Principal.SecurityIdentifier]).Value}catch{Stop-RcNetwork 'network_account_unresolved'}}
function Assert-RcNetworkNoReparse([string]$Path){$p=[IO.Path]::GetFullPath($Path);while($p){$item=Get-Item -LiteralPath $p -Force -ErrorAction Stop;if(($item.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){Stop-RcNetwork 'network_reparse_rejected'};$p=[IO.Path]::GetDirectoryName($p)}}
function Assert-RcNetworkCodeAcl([string]$Path){
    Assert-RcNetworkNoReparse $Path;if($Path-cnotmatch'^(C:\\Program Files\\RackClick\\[a-f0-9-]{36})(?:\\|$)'){Stop-RcNetwork 'network_code_acl_invalid'};$root=$Matches[1];$cursor=$Path
    $mask=[Security.AccessControl.FileSystemRights]'Write,Delete,DeleteSubdirectoriesAndFiles,ChangePermissions,TakeOwnership'
    while($cursor.Length-ge$root.Length){$acl=Get-Acl -LiteralPath $cursor;if($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value-cnotin@('S-1-5-18','S-1-5-32-544')){Stop-RcNetwork 'network_code_owner_invalid'};$rules=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]));if($rules.Count-eq0){Stop-RcNetwork 'network_code_acl_invalid'};foreach($rule in $rules){if($rule.AccessControlType-ne'Allow'-or(($rule.FileSystemRights-band$mask)-ne0-and$rule.IdentityReference.Value-cnotin@('S-1-5-18','S-1-5-32-544'))){Stop-RcNetwork 'network_code_acl_invalid'}};if($cursor-ceq$root){break};$cursor=[IO.Path]::GetDirectoryName($cursor)}
}
function Assert-RcNetworkManagementAcl([string]$Path){Assert-RcNetworkNoReparse $Path;$acl=Get-Acl -LiteralPath $Path;if($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value-cnotin@('S-1-5-18','S-1-5-32-544')){Stop-RcNetwork 'network_file_acl_invalid'};$rules=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]));if($rules.Count-lt2){Stop-RcNetwork 'network_file_acl_invalid'};foreach($r in $rules){if($r.AccessControlType-ne'Allow'-or$r.IdentityReference.Value-cnotin@('S-1-5-18','S-1-5-32-544')){Stop-RcNetwork 'network_file_acl_invalid'}}}
function Import-RcNetworkHelpers($Context){
    $root=$Context.receipt.codeRoot;Assert-RcNetworkCodeAcl $root;$payload=Join-Path $root 'payload.json';Assert-RcNetworkCodeAcl $payload
    $stream=[IO.File]::Open($payload,'Open','Read','Read');$Context.codeLocks.Add($stream)|Out-Null
    $bytes=[IO.File]::ReadAllBytes($payload)
    if((Get-RcNetworkHash $bytes)-cne'25a764a9fa40f0e8feb39cfbc9b2b3f1f21bb1137738edd53614b257f6277ec7'){Stop-RcNetwork 'network_frozen_payload_mismatch'}
    $manifest=[Text.Encoding]::UTF8.GetString($bytes)|ConvertFrom-Json;$seen=@{}
    foreach($file in $manifest.files){if($file.path-cmatch'^operators/[A-Za-z0-9_./-]+\.ps1$'-or$file.path-cmatch'^service/[A-Za-z0-9_.-]+\.dll$'){
        if($file.path-match'(^|/)\.\.?(/|$)'-or$seen.ContainsKey($file.path)){Stop-RcNetwork 'network_payload_path_invalid'};$seen[$file.path]=$true
        $path=Join-Path $root $file.path.Replace('/','\');Assert-RcNetworkCodeAcl $path;$h=[IO.File]::Open($path,'Open','Read','Read');$Context.codeLocks.Add($h)|Out-Null
        if($h.Length-ne$file.size-or(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()-cne$file.sha256){Stop-RcNetwork 'network_installed_code_changed'}
    }}
    foreach($name in @('RackClick.Setup.ps1','RackClick.Setup.Security.ps1','RackClick.Setup.Process.ps1')){
        if(-not$seen.ContainsKey('operators/server-install/'+$name)){Stop-RcNetwork 'network_helper_missing'}
        $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $root ('operators\server-install\'+$name)),[ref]$tokens,[ref]$errors)
        if($errors.Count){Stop-RcNetwork 'network_helper_invalid'}
        foreach($fn in $ast.FindAll({param($node)$node-is[Management.Automation.Language.FunctionDefinitionAst]},$false)){$definition=[regex]::Replace($fn.Extent.Text,'(?i)\Afunction\s+','function script:');. ([scriptblock]::Create($definition))}
    }
    # Reuse the exact installed certificate validator and DER reader, after the
    # frozen payload and every source-file hash have been checked above. Only
    # function ASTs are imported; script-level initialization is never run.
    foreach($selection in @(@{path='operators/server-install/RackClick.ServerRuntime.ps1';names=@('Stop-ServerCheck','Assert-ServerCertificate')},@{path='operators/RackClick.Https.ps1';names=@('Get-HttpsDerElement','Get-HttpsBytesSha256')})){
        if(-not$seen.ContainsKey($selection.path)){Stop-RcNetwork 'network_helper_missing'}
        $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $root $selection.path.Replace('/','\')),[ref]$tokens,[ref]$errors)
        if($errors.Count){Stop-RcNetwork 'network_helper_invalid'}
        foreach($name in $selection.names){$functions=@($ast.FindAll({param($node)$node-is[Management.Automation.Language.FunctionDefinitionAst]},$false)|Where-Object{$_.Name-ceq$name});if($functions.Count-ne1){Stop-RcNetwork 'network_helper_invalid'};$definition=[regex]::Replace($functions[0].Extent.Text,'(?i)\Afunction\s+','function script:');. ([scriptblock]::Create($definition))}
    }
}
function Initialize-RcNetworkNative {
    if('RackClickNetworkMaintenanceNative'-as[type]){return}
    Add-Type -TypeDefinition @'
using System;using System.IO;using System.Collections.Generic;using System.Runtime.InteropServices;using System.Security.AccessControl;using System.ComponentModel;using Microsoft.Win32.SafeHandles;
public sealed class RcNetworkFileSnapshot {public byte[] Bytes;public string Sddl;}
public static class RackClickNetworkMaintenanceNative {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern SafeFileHandle CreateFile(string p,uint a,uint s,IntPtr sa,uint c,uint f,IntPtr t);
 [DllImport("kernel32.dll",SetLastError=true)]static extern bool GetFileInformationByHandle(SafeFileHandle h,out Info i);
 [StructLayout(LayoutKind.Sequential)]struct Info{public uint Attributes,CreationLow,CreationHigh,AccessLow,AccessHigh,WriteLow,WriteHigh,Volume,SizeHigh,SizeLow,Links,IndexHigh,IndexLow;}
 [DllImport("advapi32.dll")]static extern uint GetSecurityInfo(SafeFileHandle h,int type,uint info,out IntPtr o,out IntPtr g,out IntPtr d,out IntPtr s,out IntPtr sd);
 [DllImport("advapi32.dll")]static extern uint GetSecurityDescriptorLength(IntPtr sd);
 [DllImport("kernel32.dll",SetLastError=true)]static extern bool BackupWrite(SafeFileHandle h,byte[] bytes,uint count,out uint written,bool abort,bool processSecurity,ref IntPtr context);
 [DllImport("kernel32.dll")]static extern IntPtr LocalFree(IntPtr p);
 static SafeFileHandle Open(string p,uint access,uint share){var h=CreateFile(p,access,share,IntPtr.Zero,3,0x02200000,IntPtr.Zero);if(h.IsInvalid){int e=Marshal.GetLastWin32Error();h.Dispose();throw new Win32Exception(e);}Info i;if(!GetFileInformationByHandle(h,out i)){int e=Marshal.GetLastWin32Error();h.Dispose();throw new Win32Exception(e);}if((i.Attributes&0x410)!=0||i.Links!=1){h.Dispose();throw new InvalidOperationException("network_file_not_regular");}return h;}
 sealed class Parents:IDisposable {readonly List<SafeFileHandle> held=new List<SafeFileHandle>();public Parents(string p){try{for(string q=Path.GetDirectoryName(p);!String.IsNullOrEmpty(q);q=Path.GetDirectoryName(q)){var h=CreateFile(q,0x80,1,IntPtr.Zero,3,0x02200000,IntPtr.Zero);if(h.IsInvalid){h.Dispose();throw new Win32Exception();}held.Add(h);Info i;if(!GetFileInformationByHandle(h,out i))throw new Win32Exception();if((i.Attributes&0x400)!=0)throw new InvalidOperationException("network_reparse_rejected");}}catch{Dispose();throw;}}public void Dispose(){foreach(var h in held)h.Dispose();}}
 public static RcNetworkFileSnapshot Snapshot(string p){using(var parents=new Parents(p))using(var h=Open(p,0x80020000,1)){IntPtr o,g,d,s,sd;uint e=GetSecurityInfo(h,1,7,out o,out g,out d,out s,out sd);if(e!=0)throw new Win32Exception((int)e);string acl;try{uint n=GetSecurityDescriptorLength(sd);if(n==0||n>65536)throw new InvalidOperationException();byte[] raw=new byte[n];Marshal.Copy(sd,raw,0,raw.Length);acl=new RawSecurityDescriptor(raw,0).GetSddlForm(AccessControlSections.Owner|AccessControlSections.Group|AccessControlSections.Access);}finally{LocalFree(sd);}using(var f=new FileStream(h,FileAccess.Read)){if(f.Length==0||f.Length>1048576)throw new InvalidOperationException("network_file_size_invalid");byte[] b=new byte[(int)f.Length];int at=0;while(at<b.Length){int n=f.Read(b,at,b.Length-at);if(n==0)throw new EndOfStreamException();at+=n;}return new RcNetworkFileSnapshot{Bytes=b,Sddl=acl};}}}
 public static void WriteExisting(string p,byte[] b){using(var parents=new Parents(p))using(var h=Open(p,0x40000000,0))using(var f=new FileStream(h,FileAccess.Write)){f.SetLength(0);f.Write(b,0,b.Length);f.Flush(true);}}
 public static void SetExactAcl(string p,string sddl){
  var sd=new RawSecurityDescriptor(sddl);if(sd.Owner==null||sd.Group==null||sd.DiscretionaryAcl==null||sd.DiscretionaryAcl.Count==0||sd.SystemAcl!=null)throw new InvalidOperationException("network_file_acl_invalid");
  // Restoring a security backup must preserve AUTO_INHERITED as well as
  // PROTECTED. SetSecurityInfo re-computes the former and is not exact.
  byte[] descriptor=new byte[sd.BinaryLength];sd.GetBinaryForm(descriptor,0);
  byte[] stream=new byte[20+descriptor.Length];Buffer.BlockCopy(BitConverter.GetBytes(3u),0,stream,0,4);Buffer.BlockCopy(BitConverter.GetBytes(2u),0,stream,4,4);Buffer.BlockCopy(BitConverter.GetBytes((long)descriptor.Length),0,stream,8,8);Buffer.BlockCopy(descriptor,0,stream,20,descriptor.Length);
  using(var parents=new Parents(p))using(var h=Open(p,0x400E0080,1)){IntPtr context=IntPtr.Zero;uint written;try{if(!BackupWrite(h,stream,(uint)stream.Length,out written,false,true,ref context))throw new Win32Exception();if(written!=stream.Length)throw new IOException("network_write_verification_failed");}finally{if(context!=IntPtr.Zero&&!BackupWrite(h,null,0,out written,true,true,ref context))throw new Win32Exception();}}
 }
 public static bool Exists(string p){using(var parents=new Parents(p)){var h=CreateFile(p,0x80,7,IntPtr.Zero,3,0x02200000,IntPtr.Zero);if(h.IsInvalid){int e=Marshal.GetLastWin32Error();h.Dispose();if(e==2||e==3)return false;throw new Win32Exception(e);}try{Info i;if(!GetFileInformationByHandle(h,out i))throw new Win32Exception();if((i.Attributes&0x400)!=0)throw new InvalidOperationException("network_reparse_rejected");return true;}finally{h.Dispose();}}}
 public static string HashFile(string p,long expectedLength){using(var parents=new Parents(p))using(var h=Open(p,0x80000000,1))using(var f=new FileStream(h,FileAccess.Read)){if(f.Length!=expectedLength||f.Length<5)throw new InvalidOperationException("network_backup_dump_invalid");byte[] head=new byte[5];if(f.Read(head,0,5)!=5||System.Text.Encoding.ASCII.GetString(head)!="PGDMP")throw new InvalidOperationException("network_backup_dump_invalid");f.Position=0;using(var sha=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(sha.ComputeHash(f)).Replace("-","").ToLowerInvariant();}}
 public static IDisposable Exclusive(string p){return Open(p,0xC0000000,0);}
}
'@
}
function Get-RcNetworkSnapshot($Context,[string]$Path){return (Invoke-SetupSecurityPrivileges {Initialize-RcNetworkNative;[RackClickNetworkMaintenanceNative]::Snapshot($Path)})}
function Assert-RcNetworkSnapshotAcl($Snapshot,[string[]]$Allowed){$sd=New-Object Security.AccessControl.RawSecurityDescriptor($Snapshot.Sddl);if($sd.Owner.Value-cnotin$Allowed-or$null-eq$sd.DiscretionaryAcl-or$sd.DiscretionaryAcl.Count-eq0){Stop-RcNetwork 'network_file_acl_invalid'};foreach($ace in $sd.DiscretionaryAcl){if($ace-isnot[Security.AccessControl.CommonAce]-or$ace.IsCallback-or$ace.AceQualifier-ne'AccessAllowed'-or$ace.SecurityIdentifier.Value-cnotin$Allowed){Stop-RcNetwork 'network_file_acl_invalid'}}}
function Set-RcNetworkExactAcl([string]$Path,[string]$Sddl){Initialize-RcNetworkNative;[RackClickNetworkMaintenanceNative]::SetExactAcl($Path,$Sddl)}
function Write-RcNetworkExisting($Context,[string]$Path,[byte[]]$Bytes,[string]$Sddl){Invoke-SetupSecurityPrivileges {if($Context.ContainsKey('restoring')-and$Context.restoring){Set-RcNetworkExactAcl $Path $Sddl};[RackClickNetworkMaintenanceNative]::WriteExisting($Path,$Bytes)};$after=Get-RcNetworkSnapshot $Context $Path;if((Get-RcNetworkHash $after.Bytes)-cne(Get-RcNetworkHash $Bytes)-or$after.Sddl-cne$Sddl){Stop-RcNetwork 'network_write_verification_failed'}}
function New-RcNetworkPrivateDirectory([string]$Path){Assert-RcNetworkNoReparse ([IO.Path]::GetDirectoryName($Path));if(Test-Path -LiteralPath $Path){Stop-RcNetwork 'network_destination_exists'};$acl=New-Object Security.AccessControl.DirectorySecurity;$acl.SetSecurityDescriptorSddlForm('O:BAG:SYD:P(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)');$null=[IO.Directory]::CreateDirectory($Path,$acl)}
function Write-RcNetworkNewFile([string]$Path,[byte[]]$Bytes){$h=[IO.File]::Open($Path,'CreateNew','Write','None');try{$h.Write($Bytes,0,$Bytes.Length);$h.Flush($true)}finally{$h.Dispose()};if((Get-RcNetworkHash ([IO.File]::ReadAllBytes($Path)))-cne(Get-RcNetworkHash $Bytes)){Stop-RcNetwork 'network_snapshot_verify_failed'}}
function Write-RcNetworkJournal($Context,[string]$Stage){$Context.stage=$Stage;if($Context.journalPath){$record=[ordered]@{schemaVersion=1;utc=[DateTime]::UtcNow.ToString('o');installationId=$Context.plan.installationId;stage=$Stage;committed=$Context.committed;rollbackStatus=$Context.rollbackStatus};$bytes=ConvertTo-RcNetworkBytes $record;$h=[IO.File]::Open($Context.journalPath,'Append','Write','Read');try{$h.Write($bytes,0,$bytes.Length);$h.WriteByte(10);$h.Flush($true)}finally{$h.Dispose()}}}
function Save-RcNetworkBackup($Context){
    $Context.transactionDirectory=Join-Path $Context.receipt.managementPath ('network-change-'+[guid]::NewGuid().ToString('N'));New-RcNetworkPrivateDirectory $Context.transactionDirectory
    $Context.journalPath=Join-Path $Context.transactionDirectory 'journal.jsonl';Write-RcNetworkJournal $Context 'snapshot_started'
    $index=@();$i=0;foreach($entry in $Context.entries){$now=Get-RcNetworkSnapshot $Context $entry.path;if((Get-RcNetworkHash $now.Bytes)-cne(Get-RcNetworkHash $entry.snapshot.Bytes)-or$now.Sddl-cne$entry.snapshot.Sddl){Stop-RcNetwork 'network_preflight_files_changed'};$entry.backup=Join-Path $Context.transactionDirectory ('file-'+$i+'.bin');Write-RcNetworkNewFile $entry.backup $entry.snapshot.Bytes;$index+=@{key=$entry.key;path=$entry.path;backup=[IO.Path]::GetFileName($entry.backup);sha256=(Get-RcNetworkHash $entry.snapshot.Bytes);sddl=$entry.snapshot.Sddl};$i++}
    Write-RcNetworkNewFile (Join-Path $Context.transactionDirectory 'files.json') (ConvertTo-RcNetworkBytes $index)
    Write-RcNetworkNewFile (Join-Path $Context.transactionDirectory 'backup-task.xml') ([Text.Encoding]::UTF8.GetBytes((Export-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\')))
    Write-RcNetworkNewFile (Join-Path $Context.transactionDirectory 'infrastructure.json') (ConvertTo-RcNetworkBytes @{firewall=$Context.firewall;taskWasEnabled=$Context.taskWasEnabled;serviceWasRunning=$Context.serviceWasRunning;taskArguments=$Context.task.Actions[0].Arguments;oldCaThumbprint=$Context.receipt.trustedCaThumbprint})
    $Context.backupComplete=$true;Write-RcNetworkJournal $Context 'snapshot_complete'
}
function Test-RcNetworkStopped($Context){
    $s=Get-CimInstance Win32_Service -Filter ("Name='"+$Context.receipt.serviceName+"'");if($s.State-cne'Stopped'-or$s.ProcessId-ne0){Stop-RcNetwork 'network_service_not_stopped'}
    Invoke-SetupSecurityPrivileges {if([RackClickNetworkMaintenanceNative]::Exists((Join-Path $Context.instanceRoot 'pgdata\postmaster.pid'))){Stop-RcNetwork 'network_postgres_pid_present'}}
    $ports=@([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()|ForEach-Object{$_.Port});if($Context.plan.httpsPort-in$ports-or$Context.plan.postgresPort-in$ports){Stop-RcNetwork 'network_port_in_use'}
    $Context.instanceLock=Invoke-SetupSecurityPrivileges {[RackClickNetworkMaintenanceNative]::Exclusive((Join-Path $Context.instanceRoot 'instance.lock'))}
    $lockPath=Join-Path $Context.runtime 'control\scheduled-backup.lock';if(Invoke-SetupSecurityPrivileges {[RackClickNetworkMaintenanceNative]::Exists($lockPath)}){$Context.backupLock=Invoke-SetupSecurityPrivileges {[RackClickNetworkMaintenanceNative]::Exclusive($lockPath)}}
}
function Suspend-RcNetwork($Context){
    if(-not$Context.backupComplete){Stop-RcNetwork 'network_snapshot_required'};$Context.changed=$true
    $null=Disable-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\'
    if((Get-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\').State-ceq'Running'){Stop-RcNetwork 'network_backup_running'}
    if($Context.serviceWasRunning){$Context.stopRequested=$true;Stop-Service -Name $Context.receipt.serviceName -ErrorAction Stop;(Get-Service -Name $Context.receipt.serviceName).WaitForStatus('Stopped',[TimeSpan]::FromSeconds(110))}
    Test-RcNetworkStopped $Context
}
function New-RcNetworkTls($Context){
    $caKey=$null;$key=$null;$ca=$null;$server=$null;$unsigned=$null
    try{
        $now=[DateTimeOffset]::UtcNow;$caKey=New-Object Security.Cryptography.RSACng(3072)
        $caRequest=New-Object Security.Cryptography.X509Certificates.CertificateRequest((New-Object Security.Cryptography.X509Certificates.X500DistinguishedName('CN=RackClick Private CA '+[guid]::NewGuid().ToString('N'))),$caKey,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)
        $caRequest.CertificateExtensions.Add((New-Object Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($true,$true,0,$true)));$caRequest.CertificateExtensions.Add((New-Object Security.Cryptography.X509Certificates.X509KeyUsageExtension([Security.Cryptography.X509Certificates.X509KeyUsageFlags]6,$true)))
        $ca=$caRequest.CreateSelfSigned($now.AddMinutes(-5),$now.AddDays(91));$key=New-Object Security.Cryptography.RSACng(3072)
        $req=New-Object Security.Cryptography.X509Certificates.CertificateRequest((New-Object Security.Cryptography.X509Certificates.X500DistinguishedName('CN=RackClick Server')),$key,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)
        $req.CertificateExtensions.Add((New-Object Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($false,$false,0,$true)));$req.CertificateExtensions.Add((New-Object Security.Cryptography.X509Certificates.X509KeyUsageExtension([Security.Cryptography.X509Certificates.X509KeyUsageFlags]160,$true)))
        $oids=New-Object Security.Cryptography.OidCollection;$null=$oids.Add((New-Object Security.Cryptography.Oid('1.3.6.1.5.5.7.3.1')));$req.CertificateExtensions.Add((New-Object Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension($oids,$false)))
        $san=New-Object Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder
        # These are the two VM addresses explicitly used by Wascar. Covering
        # both once avoids rotating the local CA on every home/work switch.
        $addresses=if($Context.plan.bindAddress-cin@('192.168.178.141','192.168.250.78')){@('192.168.178.141','192.168.250.78')}else{@($Context.plan.bindAddress)}
        foreach($address in $addresses){$san.AddIpAddress([Net.IPAddress]::Parse($address))}
        if($Context.plan.publicHost-cne$Context.plan.bindAddress){$san.AddDnsName($Context.plan.publicHost)};$req.CertificateExtensions.Add($san.Build($false))
        $serial=New-Object byte[] 16;$rng=[Security.Cryptography.RandomNumberGenerator]::Create();try{$rng.GetBytes($serial)}finally{$rng.Dispose()};$serial[0]=($serial[0]-band127)-bor1
        $unsigned=$req.Create($ca,$now.AddMinutes(-5),$now.AddDays(90),$serial);$server=[Security.Cryptography.X509Certificates.RSACertificateExtensions]::CopyWithPrivateKey($unsigned,$key)
        $password=[Text.Encoding]::UTF8.GetString(($Context.entries|Where-Object{$_.key-ceq'tls-password'}).snapshot.Bytes)
        $data=@{'RootCA.cer'=$ca.RawData;'server.cer'=$server.RawData;'server.pfx'=$server.Export([Security.Cryptography.X509Certificates.X509ContentType]::Pfx,$password)};$files=@{};foreach($name in $data.Keys){$files[$name]=Get-RcNetworkHash $data[$name]};$files['tls-password.txt']=Get-RcNetworkHash (($Context.entries|Where-Object{$_.key-ceq'tls-password'}).snapshot.Bytes)
        return @{certificateSha256=(Get-RcNetworkHash $server.RawData);thumbprint=$server.Thumbprint;rootThumbprint=$ca.Thumbprint;expiresUtc=$server.NotAfter.ToUniversalTime().ToString('o');files=$files;data=$data;reused=$false}
    }finally{foreach($item in @($caKey,$key,$ca,$server,$unsigned)){if($null-ne$item){$item.Dispose()}};$password=$null}
}
function Test-RcNetworkRootTrusted([string]$Thumbprint,[string]$RootHash){
    $store=New-Object Security.Cryptography.X509Certificates.X509Store('Root','LocalMachine')
    try{$store.Open('ReadOnly');return @($store.Certificates|Where-Object{$_.Thumbprint-ceq$Thumbprint-and(Get-RcNetworkHash $_.RawData)-ceq$RootHash}).Count-eq1}finally{$store.Close()}
}
function Get-RcNetworkReusableTls($Context){
    $server=$null;$root=$null;$public=$null;$chain=$null;$password=$null
    try{
        $data=@{};foreach($pair in @(@('root','RootCA.cer'),@('public','server.cer'),@('pfx','server.pfx'))){$matches=@($Context.entries|Where-Object{$_.key-ceq$pair[0]});if($matches.Count-ne1){return $null};$data[$pair[1]]=$matches[0].snapshot.Bytes}
        $passwordBytes=($Context.entries|Where-Object{$_.key-ceq'tls-password'}).snapshot.Bytes;$password=[Text.Encoding]::UTF8.GetString($passwordBytes)
        $server=New-Object Security.Cryptography.X509Certificates.X509Certificate2($data['server.pfx'],$password,([Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet))
        $root=New-Object Security.Cryptography.X509Certificates.X509Certificate2(,$data['RootCA.cer']);$public=New-Object Security.Cryptography.X509Certificates.X509Certificate2(,$data['server.cer'])
        $metadata=Assert-ServerCertificate $server $Context.plan.publicHost
        if($root.HasPrivateKey-or$root.Thumbprint-cne$Context.receipt.trustedCaThumbprint-or$metadata.sha256-cne$Context.profile.certificate.certificateSha256-or$metadata.thumbprint-cne$Context.profile.certificate.thumbprint-or$metadata.expiresUtc-cne$Context.profile.certificate.expiresUtc-or(Get-RcNetworkHash $public.RawData)-cne$metadata.sha256){return $null}
        $constraints=@($root.Extensions|Where-Object{$_.Oid.Value-ceq'2.5.29.19'});if($constraints.Count-ne1-or-not(New-Object Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($constraints[0],$constraints[0].Critical)).CertificateAuthority){return $null}
        $chain=New-Object Security.Cryptography.X509Certificates.X509Chain;$null=$chain.ChainPolicy.ExtraStore.Add($root)
        $chain.ChainPolicy.RevocationMode=[Security.Cryptography.X509Certificates.X509RevocationMode]::NoCheck;$chain.ChainPolicy.VerificationFlags=[Security.Cryptography.X509Certificates.X509VerificationFlags]::AllowUnknownCertificateAuthority;$chain.ChainPolicy.UrlRetrievalTimeout=[TimeSpan]::FromSeconds(1)
        if(-not$chain.Build($server)-or$chain.ChainElements.Count-ne2-or(Get-RcNetworkHash $chain.ChainElements[1].Certificate.RawData)-cne(Get-RcNetworkHash $root.RawData)){return $null}
        foreach($status in $chain.ChainStatus){if($status.Status-notin@([Security.Cryptography.X509Certificates.X509ChainStatusFlags]::NoError,[Security.Cryptography.X509Certificates.X509ChainStatusFlags]::UntrustedRoot)){return $null}}
        if(-not(Test-RcNetworkRootTrusted $root.Thumbprint (Get-RcNetworkHash $root.RawData))){return $null}
        $files=@{};foreach($name in $data.Keys){$files[$name]=Get-RcNetworkHash $data[$name];if($files[$name]-cne$Context.profile.certificate.files.$name){return $null}}
        $files['tls-password.txt']=Get-RcNetworkHash $passwordBytes;if($files['tls-password.txt']-cne$Context.profile.certificate.files.'tls-password.txt'){return $null}
        return @{certificateSha256=$metadata.sha256;thumbprint=$metadata.thumbprint;rootThumbprint=$root.Thumbprint;expiresUtc=$metadata.expiresUtc;files=$files;data=$data;reused=$true}
    }catch{return $null}finally{foreach($item in @($server,$root,$public,$chain)){if($null-ne$item){$item.Dispose()}};$password=$null}
}
function Set-RcNetworkFiles($Context){
    $Context.tls=Get-RcNetworkReusableTls $Context;if($null-eq$Context.tls){$Context.tls=New-RcNetworkTls $Context};$Context.updated=ConvertTo-RcNetworkConfiguration $Context.profile $Context.config $Context.receipt $Context.tls $Context.plan
    $writes=@{profile=$Context.updated.profileBytes;config=$Context.updated.configBytes;receipt=$Context.updated.receiptBytes;root=$Context.tls.data['RootCA.cer'];public=$Context.tls.data['server.cer'];pfx=$Context.tls.data['server.pfx'];managementCa=$Context.tls.data['RootCA.cer']}
    foreach($entry in $Context.entries){if($writes.ContainsKey($entry.key)){Write-RcNetworkJournal $Context ('write_'+$entry.key);$Context.filesTouched=$true;Write-RcNetworkExisting $Context $entry.path $writes[$entry.key] $entry.snapshot.Sddl}}
}
function Set-RcNetworkTask($Context,[string]$Arguments){
    $before=[xml](Export-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\');$plain=$null
    try{$plain=$Context.credential.GetNetworkCredential().Password;$action=New-ScheduledTaskAction -Execute $Context.receipt.backupExecutable -Argument $Arguments;$null=Set-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\' -Action $action -User $Context.credential.UserName -Password $plain}finally{$plain=$null}
    $after=[xml](Export-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\');$task=Get-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\'
    if($before.Task.Triggers.OuterXml-cne$after.Task.Triggers.OuterXml-or$before.Task.Settings.OuterXml-cne$after.Task.Settings.OuterXml-or$task.Principal.LogonType-ne'Password'-or$task.Principal.RunLevel-ne'Limited'-or(Resolve-RcNetworkSid $task.Principal.UserId)-cne$Context.receipt.serviceSid-or$task.Actions.Count-ne1-or$task.Actions[0].Arguments-cne$Arguments-or$task.Actions[0].Execute-cne$Context.receipt.backupExecutable){Stop-RcNetwork 'network_task_update_verification_failed'}
}
function Set-RcNetworkInfrastructure($Context){
    $Context.infrastructureTouched=$true
    if($Context.tls.reused){if(-not(Test-RcNetworkRootTrusted $Context.tls.rootThumbprint (Get-RcNetworkHash $Context.tls.data['RootCA.cer']))){Stop-RcNetwork 'network_ca_binding_invalid'}}
    else{$cert=New-Object Security.Cryptography.X509Certificates.X509Certificate2(,$Context.tls.data['RootCA.cer']);$store=New-Object Security.Cryptography.X509Certificates.X509Store('Root','LocalMachine');try{$store.Open('ReadWrite');if(@($store.Certificates|Where-Object{$_.Thumbprint-ceq$cert.Thumbprint}).Count-ne0){Stop-RcNetwork 'network_ca_already_present'};$Context.newCaThumbprint=$cert.Thumbprint;$store.Add($cert)}finally{$store.Close();$cert.Dispose()}}
    $Context.firewallTouched=$true;$null=Set-NetFirewallRule -Name $Context.receipt.firewallRule -LocalAddress $Context.plan.bindAddress -RemoteAddress $Context.plan.allowedSubnet
    Assert-RcNetworkFirewall $Context @($Context.plan.bindAddress) @($Context.plan.allowedSubnet)
    $Context.taskTouched=$true
    Set-RcNetworkTask $Context $Context.updated.receipt.backupArguments
}
function Assert-RcNetworkFirewall($Context,[string[]]$Local,[string[]]$Remote){
    $rules=@(Get-NetFirewallRule -Name $Context.receipt.firewallRule)
    if($rules.Count-ne1-or$rules[0].Enabled-ne'True'-or$rules[0].Profile-ne'Any'-or$rules[0].Direction-ne'Inbound'-or$rules[0].Action-ne'Allow'){Stop-RcNetwork 'network_firewall_binding_invalid'}
    $address=$rules[0]|Get-NetFirewallAddressFilter;$port=$rules[0]|Get-NetFirewallPortFilter;$app=$rules[0]|Get-NetFirewallApplicationFilter
    if(-not(Test-RcNetworkFirewallAddresses @($address.LocalAddress) $Local)-or-not(Test-RcNetworkFirewallAddresses @($address.RemoteAddress) $Remote)-or$port.Protocol-ne'TCP'-or$port.LocalPort-ne[string]$Context.plan.httpsPort-or$app.Program-cne(Join-Path $Context.receipt.instancePath 'content\dependencies\dotnet\dotnet.exe')){Stop-RcNetwork 'network_firewall_binding_invalid'}
}
function Release-RcNetworkLocks($Context){foreach($name in @('instanceLock','backupLock')){if($Context[$name]){$Context[$name].Dispose();$Context[$name]=$null}}}
function Invoke-RcNetworkChild($Context,[string]$Operation,[string]$Hash,[string]$BackupPath=''){
    if($Operation-cne'Verify'-or$BackupPath-cne''-or$Hash-cnotmatch'^[a-f0-9]{64}$'){Stop-RcNetwork 'network_child_failed'}
    $exe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe';$runtimeScript=Join-Path $Context.receipt.codeRoot 'operators\server-install\Invoke-RackClickServerRuntime.ps1'
    $folder=Join-Path ([IO.Path]::GetDirectoryName($Context.receipt.managementPath)) ('network-code-'+[guid]::NewGuid().ToString('N'));Assert-RcNetworkNoReparse ([IO.Path]::GetDirectoryName($folder));if(Test-Path -LiteralPath $folder){Stop-RcNetwork 'network_destination_exists'}
    $acl=New-Object Security.AccessControl.DirectorySecurity;$acl.SetSecurityDescriptorSddlForm(('O:BAG:SYD:P(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)(A;OICI;FRFX;;;'+$Context.receipt.serviceSid+')'));$null=[IO.Directory]::CreateDirectory($folder,$acl)
    $script=Join-Path $folder 'verify.ps1';$literal={param([string]$Text) return "'"+$Text.Replace("'","''")+"'"}
    $body='$ErrorActionPreference=''Stop''; $env:PSModulePath=Join-Path $env:SystemRoot ''System32\WindowsPowerShell\v1.0\Modules''; $env:TEMP='+(& $literal (Join-Path $Context.runtime 'temp'))+'; $env:TMP=$env:TEMP; if([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -cne '+(& $literal $Context.receipt.serviceSid)+'){[ordered]@{valid=$false;exitCode=2;code=''network_account_unresolved''}|ConvertTo-Json -Compress;exit 2}; & '+(& $literal $runtimeScript)+' -Operation Verify -ManifestPath '+(& $literal $Context.manifest)+' -ExpectedManifestSha256 '+(& $literal $Hash)+'; exit $LASTEXITCODE'
    Write-RcNetworkNewFile $script ([Text.Encoding]::UTF8.GetBytes($body));Assert-RcNetworkNoReparse $script;$scriptLock=[IO.File]::Open($script,'Open','Read','Read');$Context.codeLocks.Add($scriptLock)|Out-Null
    $args='-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$script+'"'
    if(('"'+$exe+'" '+$args).Length+1-gt1024){Stop-RcNetwork 'network_child_command_too_long'}
    $label=$Operation+'-'+[guid]::NewGuid().ToString('N');$out=Join-Path $Context.transactionDirectory ($label+'.stdout');$err=Join-Path $Context.transactionDirectory ($label+'.stderr');$p=$null;$handle=$null
    try{$p=Start-Process -FilePath $exe -Credential $Context.credential -LoadUserProfile -WorkingDirectory $Context.receipt.codeRoot -ArgumentList $args -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru;$Context.unsafeChildAlive=$true;$handle=Open-SetupChildProcess $p.Id;if(-not(Wait-SetupChildProcess $handle 600)){Stop-RcNetwork 'network_child_timeout_do_not_repeat'};$p.WaitForExit();$Context.unsafeChildAlive=$false;$exit=Get-SetupChildProcessExitCode $handle;$answer=Read-SetupChildResult $out;if($exit-ne0-or$answer.exitCode-ne0-or-not$answer.valid-or(Get-Item -LiteralPath $err).Length-ne0){Stop-RcNetwork 'network_child_failed'};return $answer}finally{if($handle){$handle.Dispose()};if($p){$p.Dispose()};$scriptLock.Dispose()}
}
function Test-RcNetworkScheduledBackup($Context){
    $previous=(Get-ScheduledTaskInfo -TaskName $Context.receipt.backupTaskName -TaskPath '\').LastRunTime;$started=[DateTime]::UtcNow;$watch=[Diagnostics.Stopwatch]::StartNew();$completed=$false
    $null=Enable-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\'
    try{
        Start-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\'
        while($watch.Elapsed.TotalSeconds-lt650){$task=Get-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\';$info=Get-ScheduledTaskInfo -TaskName $Context.receipt.backupTaskName -TaskPath '\';if($info.LastRunTime-gt$previous-and$info.LastRunTime.ToUniversalTime()-ge$started.AddSeconds(-2)-and$task.State-ne'Running'){if($info.LastTaskResult-ne0){Stop-RcNetwork 'network_scheduled_backup_failed'};$completed=$true;break};Start-Sleep -Milliseconds 500}
        if(-not$completed){$Context.unsafeChildAlive=$true;Stop-RcNetwork 'network_backup_timeout_do_not_repeat'}
    }finally{$null=Disable-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\'}
    $snap=Get-RcNetworkSnapshot $Context (Join-Path $Context.runtime 'control\latest-backup.json');$report=[Text.Encoding]::UTF8.GetString($snap.Bytes)|ConvertFrom-Json
    $backupRoot=Join-Path $Context.runtime 'backups';$stamp=[DateTimeOffset]::MinValue
    if(-not$report.valid-or-not$report.success-or$report.exitCode-ne0-or$report.code-cne'scheduled_backup_complete'-or-not[DateTimeOffset]::TryParse($report.createdUtc,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::None,[ref]$stamp)-or$stamp.UtcDateTime-lt$started-or$report.backupPath-cnotmatch('^'+[regex]::Escape($backupRoot)+'\\daily-[0-9]{8}T[0-9]{9}Z-[a-f0-9]{32}$')-or$report.manifestPath-cne(Join-Path $report.backupPath 'manifest.json')-or$report.manifestSha256-cnotmatch'^[a-f0-9]{64}$'){Stop-RcNetwork 'network_backup_receipt_invalid'}
    $manifest=Get-RcNetworkSnapshot $Context $report.manifestPath;if((Get-RcNetworkHash $manifest.Bytes)-cne$report.manifestSha256){Stop-RcNetwork 'network_backup_manifest_mismatch'};$m=[Text.Encoding]::UTF8.GetString($manifest.Bytes)|ConvertFrom-Json
    $manifestStamp=[DateTimeOffset]::MinValue
    if($m.schemaVersion-ne1-or$m.kind-cne'RackClickDatabaseBackup'-or$m.postgresVersion-cne'17.11'-or$m.format-cne'custom'-or$m.dumpFile-cne'data.dump'-or$m.dumpSha256-cnotmatch'^[a-f0-9]{64}$'-or($m.dumpBytes-isnot[int]-and$m.dumpBytes-isnot[long])-or$m.dumpBytes-lt5-or-not[DateTimeOffset]::TryParse([string]$m.createdUtc,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::None,[ref]$manifestStamp)-or$manifestStamp.UtcDateTime-lt$started){Stop-RcNetwork 'network_backup_manifest_invalid'}
    $hash=Invoke-SetupSecurityPrivileges {[RackClickNetworkMaintenanceNative]::HashFile((Join-Path $report.backupPath 'data.dump'),[long]$m.dumpBytes)};if($hash-cne$m.dumpSha256){Stop-RcNetwork 'network_backup_dump_mismatch'};$Context.verifiedBackup=$report
}
function Test-RcNetworkApplied($Context){
    Release-RcNetworkLocks $Context;$verify=Invoke-RcNetworkChild $Context 'Verify' $Context.updated.profileSha256;if($verify.code-cne'server_profile_verified'){Stop-RcNetwork 'network_profile_verify_failed'}
    Start-Service -Name $Context.receipt.serviceName;$Context.startedNew=$true;$watch=[Diagnostics.Stopwatch]::StartNew();$ready=$false
    while($watch.Elapsed.TotalSeconds-lt90){try{$body=Invoke-RestMethod -Uri ($Context.plan.publicOrigin+'/health/ready') -TimeoutSec 3 -UseBasicParsing;if($body.status-ceq'ready'-and$body.schemaVersion-eq14){$ready=$true;break}}catch{};if((Get-Service -Name $Context.receipt.serviceName).Status-ne'Running'){Stop-RcNetwork 'network_service_start_failed'};Start-Sleep -Milliseconds 500}
    if(-not$ready){Stop-RcNetwork 'network_health_failed'}
    Test-RcNetworkScheduledBackup $Context
}
function Complete-RcNetworkChange($Context){if($Context.taskWasEnabled){$null=Enable-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\'};$Context.committed=$true;try{Write-RcNetworkJournal $Context 'committed'}catch{$Context.committed=$false;throw}}
function Add-RcNetworkRollbackError($Context,[string]$Step,$Record){
    if(-not$Context.ContainsKey('rollbackErrors')){$Context.rollbackErrors=@()}
    $cause=$Record.Exception;for($i=0;$i-lt8-and$null-ne$cause.InnerException;$i++){$cause=$cause.InnerException}
    $row=[ordered]@{step=$Step;hresult=$cause.HResult}
    if($Record.Exception.Message-cin(Get-RcNetworkCodes)){$row.code=$Record.Exception.Message}
    if($cause-is[ComponentModel.Win32Exception]){$row.nativeErrorCode=$cause.NativeErrorCode}
    $Context.rollbackErrors+=@($row)
}
function Undo-RcNetworkChange($Context){
    $Context.rollbackErrors=@();Release-RcNetworkLocks $Context
    if(-not$Context.stopRequested-and-not$Context.filesTouched-and-not$Context.infrastructureTouched){
        try{if($Context.taskWasEnabled){$null=Enable-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\'};$Context.rollbackStatus=if($Context.serviceWasRunning){'rollback_restored_service_started'}else{'rollback_restored_service_stopped'}}catch{Add-RcNetworkRollbackError $Context 'task_enable' $_;$Context.rollbackStatus='rollback_partial'}
        Write-RcNetworkJournal $Context $Context.rollbackStatus;return
    }
    if($Context.unsafeChildAlive){$Context.rollbackStatus='rollback_partial';Write-RcNetworkJournal $Context 'rollback_child_indeterminate';return}
    try{$null=Disable-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\';if((Get-Service -Name $Context.receipt.serviceName).Status-ne'Stopped'){Stop-Service -Name $Context.receipt.serviceName;(Get-Service -Name $Context.receipt.serviceName).WaitForStatus('Stopped',[TimeSpan]::FromSeconds(110))};Test-RcNetworkStopped $Context}catch{Add-RcNetworkRollbackError $Context 'stop' $_}
    if($Context.rollbackErrors.Count){$Context.rollbackStatus='rollback_partial';Write-RcNetworkJournal $Context 'rollback_stop_indeterminate';return}
    if($Context.filesTouched){$Context.restoring=$true;try{foreach($entry in $Context.entries){try{Write-RcNetworkExisting $Context $entry.path $entry.snapshot.Bytes $entry.snapshot.Sddl}catch{Add-RcNetworkRollbackError $Context ('file_'+$entry.key) $_}}}finally{$Context.restoring=$false}}
    if($Context.ContainsKey('firewallTouched')-and$Context.firewallTouched){try{$null=Set-NetFirewallRule -Name $Context.receipt.firewallRule -LocalAddress $Context.firewall.local -RemoteAddress $Context.firewall.remote;Assert-RcNetworkFirewall $Context @($Context.firewall.local) @($Context.firewall.remote)}catch{Add-RcNetworkRollbackError $Context 'firewall' $_}}
    if($Context.ContainsKey('taskTouched')-and$Context.taskTouched){try{Set-RcNetworkTask $Context $Context.task.Actions[0].Arguments}catch{Add-RcNetworkRollbackError $Context 'task_action' $_}}
    if($Context.newCaThumbprint-and$Context.rollbackErrors.Count-eq0){$store=New-Object Security.Cryptography.X509Certificates.X509Store('Root','LocalMachine');try{$store.Open('ReadWrite');foreach($c in @($store.Certificates|Where-Object{$_.Thumbprint-ceq$Context.newCaThumbprint})){$store.Remove($c)}}catch{Add-RcNetworkRollbackError $Context 'ca' $_}finally{$store.Close()}}
    if($Context.rollbackErrors.Count-eq0-and$Context.taskWasEnabled){try{$null=Enable-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\';if(-not(Get-ScheduledTask -TaskName $Context.receipt.backupTaskName -TaskPath '\').Settings.Enabled){Stop-RcNetwork 'network_task_update_verification_failed'}}catch{Add-RcNetworkRollbackError $Context 'task_enable' $_}}
    Release-RcNetworkLocks $Context;$Context.rollbackStatus=if($Context.rollbackErrors.Count){'rollback_partial'}else{'rollback_restored_service_stopped'}
    if($Context.rollbackErrors.Count-eq0-and$Context.serviceWasRunning){$oldBind=$Context.profile.bindAddress;$local=@([Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces()|Where-Object{$_.OperationalStatus-eq'Up'}|ForEach-Object{$_.GetIPProperties().UnicastAddresses}|ForEach-Object{$_.Address.ToString()});if($oldBind-in$local){try{Start-Service -Name $Context.receipt.serviceName;$Context.rollbackStatus='rollback_restored_service_started'}catch{Add-RcNetworkRollbackError $Context 'service_restart' $_;$Context.rollbackStatus='rollback_partial'}}}
    Write-RcNetworkJournal $Context $Context.rollbackStatus
}
function Invoke-RcNetworkTransaction($Context){
    try{Save-RcNetworkBackup $Context;if(-not$Context.backupComplete){Stop-RcNetwork 'network_snapshot_required'};Write-RcNetworkJournal $Context 'stopping';$Context.transactionMutationsStarted=$true;Suspend-RcNetwork $Context;Write-RcNetworkJournal $Context 'files';Set-RcNetworkFiles $Context;Write-RcNetworkJournal $Context 'infrastructure';Set-RcNetworkInfrastructure $Context;Write-RcNetworkJournal $Context 'verification';Test-RcNetworkApplied $Context;Complete-RcNetworkChange $Context;return $true}
    catch{$Context.failureStage=$Context.stage;if(-not$Context.ContainsKey('transactionMutationsStarted')-or-not$Context.transactionMutationsStarted){try{Write-RcNetworkJournal $Context 'aborted_before_change'}catch{}}elseif($Context.backupComplete-and-not$Context.committed){try{Undo-RcNetworkChange $Context}catch{$Context.rollbackStatus='rollback_partial'}};throw}
}
function Get-RcNetworkContext($Plan){
    $parent='C:\ProgramData\RackClick\Instances\'+$Plan.installationId;$management=Join-Path $parent 'management';Assert-RcNetworkNoReparse $management
    $receiptPath=Join-Path $management 'server-installation.json';Assert-RcNetworkManagementAcl $receiptPath;$receipt=[IO.File]::ReadAllText($receiptPath)|ConvertFrom-Json
    Assert-RcNetworkReceipt $receipt $Plan
    $ctx=@{plan=$Plan;receipt=$receipt;codeLocks=(New-Object Collections.ArrayList);entries=@();runtime=(Join-Path $receipt.instancePath 'runtime');instanceRoot=(Join-Path $receipt.instancePath 'deployment\instance');backupComplete=$false;changed=$false;committed=$false;rollbackStatus='not_needed';stage='preflight';journalPath='';instanceLock=$null;backupLock=$null;credential=$null;newCaThumbprint='';startedNew=$false;unsafeChildAlive=$false;stopRequested=$false;filesTouched=$false;infrastructureTouched=$false;firewallTouched=$false;taskTouched=$false;rollbackErrors=@()}
    $script:rcNetworkContext=$ctx
    Import-RcNetworkHelpers $ctx;Assert-SetupManagementAcl $management;Assert-SetupManagementAcl $receiptPath
    $ctx.manifest=Join-Path $ctx.runtime 'server-profile.json'
    foreach($pair in @(@('profile',$ctx.manifest),@('config',(Join-Path $receipt.instancePath 'service-config.json')),@('root',(Join-Path $ctx.runtime 'RootCA.cer')),@('public',(Join-Path $ctx.runtime 'server.cer')),@('pfx',(Join-Path $ctx.runtime 'server.pfx')),@('tls-password',(Join-Path $ctx.runtime 'tls-password.txt')),@('managementCa',(Join-Path $management 'RootCA.cer')),@('receipt',$receiptPath))){$snap=Get-RcNetworkSnapshot $ctx $pair[1];$allowed=if($pair[0]-cin@('managementCa','receipt')){@('S-1-5-18','S-1-5-32-544')}else{@('S-1-5-18',$receipt.serviceSid)};Assert-RcNetworkSnapshotAcl $snap $allowed;$ctx.entries+=@(@{key=$pair[0];path=$pair[1];snapshot=$snap})}
    $profileBytes=($ctx.entries|Where-Object{$_.key-ceq'profile'}).snapshot.Bytes;if((Get-RcNetworkHash $profileBytes)-cne$receipt.manifestSha256){Stop-RcNetwork 'network_profile_hash_mismatch'};$ctx.profile=[Text.Encoding]::UTF8.GetString($profileBytes)|ConvertFrom-Json
    $ctx.config=[Text.Encoding]::UTF8.GetString(($ctx.entries|Where-Object{$_.key-ceq'config'}).snapshot.Bytes)|ConvertFrom-Json
    if($ctx.profile.schemaVersion-ne1-or$ctx.profile.profileKind-cne'RackClickProductionServer'-or$ctx.profile.publicOrigin-cne$receipt.publicOrigin-or$ctx.profile.expectedWindowsSid-cne$receipt.serviceSid-or$ctx.profile.runtimeRoot-cne$ctx.runtime-or$ctx.profile.installationPath-cne$receipt.instancePath-or$ctx.profile.deploymentPath-cne(Join-Path $receipt.instancePath 'deployment')-or$ctx.config.schemaVersion-ne1-or$ctx.config.serviceName-cne$receipt.serviceName-or$ctx.config.serverManifestPath-cne$ctx.manifest-or$ctx.config.serverManifestSha256-cne$receipt.manifestSha256-or$ctx.config.runtimeScriptPath-cne(Join-Path $receipt.codeRoot 'operators\server-install\Invoke-RackClickServerRuntime.ps1')-or$ctx.config.logDirectory-cne(Join-Path $ctx.runtime 'logs')){Stop-RcNetwork 'network_configuration_binding_invalid'}
    $installation=Get-RcNetworkSnapshot $ctx (Join-Path $receipt.instancePath 'installation.json');$deployment=Get-RcNetworkSnapshot $ctx (Join-Path $receipt.instancePath 'deployment\deployment.json');$instance=Get-RcNetworkSnapshot $ctx (Join-Path $ctx.instanceRoot 'instance.json');$dm=[Text.Encoding]::UTF8.GetString($deployment.Bytes)|ConvertFrom-Json
    if((Get-RcNetworkHash $installation.Bytes)-cne$ctx.profile.installationSha256-or(Get-RcNetworkHash $deployment.Bytes)-cne$ctx.profile.deploymentSha256-or(Get-RcNetworkHash $instance.Bytes)-cne$dm.instanceManifestSha256){Stop-RcNetwork 'network_installation_hash_mismatch'}
    $im=[Text.Encoding]::UTF8.GetString($instance.Bytes)|ConvertFrom-Json;$installationRecord=[Text.Encoding]::UTF8.GetString($installation.Bytes)|ConvertFrom-Json
    Assert-RcNetworkInstanceBinding $receipt $ctx.profile $installationRecord $dm $im $Plan
    foreach($pair in @(@('root','RootCA.cer'),@('public','server.cer'),@('pfx','server.pfx'),@('tls-password','tls-password.txt'))){if((Get-RcNetworkHash (($ctx.entries|Where-Object{$_.key-ceq$pair[0]}).snapshot.Bytes))-cne$ctx.profile.certificate.files.($pair[1])){Stop-RcNetwork 'network_tls_hash_mismatch'}}
    $service=@(Get-CimInstance Win32_Service -Filter ("Name='"+$receipt.serviceName+"'"));$binary='"'+(Join-Path $receipt.instancePath 'content\dependencies\dotnet\dotnet.exe')+'" "'+(Join-Path $receipt.codeRoot 'service\RackClick.WindowsService.dll')+'" --config "'+(Join-Path $receipt.instancePath 'service-config.json')+'"'
    if($service.Count-ne1-or$service[0].PathName-cne$binary-or(Resolve-RcNetworkSid $service[0].StartName)-cne$receipt.serviceSid-or$service[0].State-cnotin@('Running','Stopped')){Stop-RcNetwork 'network_service_binding_invalid'};$ctx.serviceWasRunning=$service[0].State-ceq'Running';$ctx.serviceBinary=$binary
    $addresses=@(Get-NetIPAddress -AddressFamily IPv4|Where-Object{$_.IPAddress-ceq$Plan.bindAddress-and$_.AddressState-eq'Preferred'});if($addresses.Count-ne1-or@(Get-NetAdapter|Where-Object{$_.InterfaceIndex-eq$addresses[0].InterfaceIndex-and$_.Status-eq'Up'}).Count-ne1){Stop-RcNetwork 'network_target_ip_not_preferred'}
    if($Plan.publicHost-cne$Plan.bindAddress-and$Plan.bindAddress-cnotin@([Net.Dns]::GetHostAddresses($Plan.publicHost)|ForEach-Object{$_.ToString()})){Stop-RcNetwork 'network_dns_binding_invalid'}
    $ctx.task=Get-ScheduledTask -TaskName $receipt.backupTaskName -TaskPath '\';if($ctx.task.State-ceq'Running'-or$ctx.task.Principal.LogonType-ne'Password'-or$ctx.task.Principal.RunLevel-ne'Limited'-or(Resolve-RcNetworkSid $ctx.task.Principal.UserId)-cne$receipt.serviceSid-or$ctx.task.Actions.Count-ne1-or$ctx.task.Actions[0].Execute-cne$receipt.backupExecutable-or$ctx.task.Actions[0].Arguments-cne$receipt.backupArguments){Stop-RcNetwork 'network_task_binding_invalid'};$ctx.taskWasEnabled=[bool]$ctx.task.Settings.Enabled
    $rule=@(Get-NetFirewallRule -Name $receipt.firewallRule);if($rule.Count-ne1-or$rule[0].Enabled-ne'True'-or$rule[0].Profile-ne'Any'-or$rule[0].Direction-ne'Inbound'-or$rule[0].Action-ne'Allow'){Stop-RcNetwork 'network_firewall_binding_invalid'};$port=$rule[0]|Get-NetFirewallPortFilter;$app=$rule[0]|Get-NetFirewallApplicationFilter;if($port.Protocol-ne'TCP'-or$port.LocalPort-ne[string]$Plan.httpsPort-or$app.Program-cne(Join-Path $receipt.instancePath 'content\dependencies\dotnet\dotnet.exe')){Stop-RcNetwork 'network_firewall_binding_invalid'};$filter=$rule[0]|Get-NetFirewallAddressFilter;$ctx.firewall=@{local=@($filter.LocalAddress);remote=@($filter.RemoteAddress)}
    $ca=New-Object Security.Cryptography.X509Certificates.X509Certificate2(,($ctx.entries|Where-Object{$_.key-ceq'root'}).snapshot.Bytes);try{if($ca.Thumbprint-cne$receipt.trustedCaThumbprint-or(Get-RcNetworkHash (($ctx.entries|Where-Object{$_.key-ceq'managementCa'}).snapshot.Bytes))-cne(Get-RcNetworkHash $ca.RawData)){Stop-RcNetwork 'network_ca_binding_invalid'}}finally{$ca.Dispose()}
    if(-not$ctx.serviceWasRunning){Test-RcNetworkStopped $ctx;Release-RcNetworkLocks $ctx}
    return $ctx
}
function Find-RcNetworkPendingJournal($Context){
    foreach($dir in @(Get-ChildItem -LiteralPath $Context.receipt.managementPath -Directory -Filter 'network-change-*' -Force)){
        Assert-RcNetworkManagementAcl $dir.FullName
        if($dir.Name-cnotmatch'^network-change-[a-f0-9]{32}$'){Stop-RcNetwork 'network_recovery_required'}
        $path=Join-Path $dir.FullName 'journal.jsonl';if(-not[IO.File]::Exists($path)){return $dir.FullName};Assert-RcNetworkManagementAcl $path
        if((Get-Item -LiteralPath $path).Length-gt1048576){return $dir.FullName}
        try{$lines=@([IO.File]::ReadAllLines($path)|Where-Object{$_.Length-gt0});if($lines.Count-eq0){return $dir.FullName};$last=$lines[-1]|ConvertFrom-Json;if($last.installationId-cne$Context.plan.installationId-or$last.stage-cnotin@('committed','aborted_before_change','rollback_restored_service_stopped','rollback_restored_service_started')){return $dir.FullName}}catch{return $dir.FullName}
    }
    return ''
}
function Test-RcNetworkAlreadyConfigured($Context){return ($Context.profile.bindAddress-ceq$Context.plan.bindAddress-and$Context.profile.publicOrigin-ceq$Context.plan.publicOrigin-and$Context.receipt.publicOrigin-ceq$Context.plan.publicOrigin-and(Test-RcNetworkFirewallAddresses @($Context.firewall.local) @($Context.plan.bindAddress))-and(Test-RcNetworkFirewallAddresses @($Context.firewall.remote) @($Context.plan.allowedSubnet)))}
function Assert-RcNetworkServiceUnchanged($Context){
    $observed=@(Get-CimInstance Win32_Service -Filter ("Name='"+$Context.receipt.serviceName+"'"))
    if($observed.Count-ne1-or$observed[0].PathName-cne$Context.serviceBinary-or
       (Resolve-RcNetworkSid $observed[0].StartName)-cne$Context.receipt.serviceSid-or
       ($observed[0].State-ceq'Running')-ne$Context.serviceWasRunning-or$observed[0].State-cnotin@('Running','Stopped')){Stop-RcNetwork 'network_preflight_state_changed'}
}
function Start-RcNetworkExisting($Context){
    # A matching IP alone is never reported as a usable server. Validate the
    # bound SCM entry again, then demand trusted HTTPS and the expected schema.
    Assert-RcNetworkServiceUnchanged $Context
    $started=$false
    try{
        if(-not$Context.serviceWasRunning){Start-Service -Name $Context.receipt.serviceName -ErrorAction Stop;$started=$true}
        $watch=[Diagnostics.Stopwatch]::StartNew()
        while($watch.Elapsed.TotalSeconds-lt90){
            try{$body=Invoke-RestMethod -Uri ($Context.plan.publicOrigin+'/health/ready') -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop;if($body.status-ceq'ready'-and$body.schemaVersion-eq14-and(Get-Service -Name $Context.receipt.serviceName).Status-eq'Running'){return}}catch{}
            if((Get-Service -Name $Context.receipt.serviceName).Status-ne'Running'){Stop-RcNetwork 'network_service_start_failed'}
            Start-Sleep -Milliseconds 500
        }
        Stop-RcNetwork 'network_health_failed'
    }catch{
        # Preserve an initially stopped instance if its attempted start failed.
        if($started){try{Stop-Service -Name $Context.receipt.serviceName -ErrorAction Stop;(Get-Service -Name $Context.receipt.serviceName).WaitForStatus('Stopped',[TimeSpan]::FromSeconds(110))}catch{$Context.rollbackStatus='rollback_partial'}}
        throw
    }
}
if($FunctionsOnly){return}
# WinPS 5.1 serializes progress (including module first-use progress) as CLIXML
# on redirected stderr. The launcher requires JSON stdout and empty stderr.
$ProgressPreference='SilentlyContinue'
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$result=[ordered]@{schemaVersion=1;valid=$false;success=$false;exitCode=2;code='network_change_failed';stage='preflight';installationId=$InstallationId;databaseCredentialsChanged=$false;windowsNetworkChanged=$false;rollbackStatus='not_needed';productAdopted=$false}
$context=$null;$operationLock=$null;$script:rcNetworkContext=$null;$originalModulePath=$env:PSModulePath
try{
    if($PSVersionTable.PSEdition-cne'Desktop'-or$PSVersionTable.PSVersion.Major-ne5-or-not[Environment]::Is64BitProcess-or-not(New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){Stop-RcNetwork 'network_elevated_winps51_x64_required'}
    $env:PSModulePath=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules'
    $plan=Get-RcNetworkPlan $InstallationId $BindAddress $AllowedSubnet $PublicHost $HttpsPort $PostgresPort;$management='C:\ProgramData\RackClick\Instances\'+$plan.installationId+'\management';Assert-RcNetworkManagementAcl $management
    if(-not$CheckOnly){$operationLock=[IO.File]::Open((Join-Path $management 'network-maintenance.lock'),'OpenOrCreate','ReadWrite','None')}
    $pending=Find-RcNetworkPendingJournal @{plan=$plan;receipt=@{managementPath=$management}};if($pending){$result.journalDirectory=$pending;Stop-RcNetwork 'network_recovery_required'}
    $context=Get-RcNetworkContext $plan
    $result.serviceName=$context.receipt.serviceName;$result.httpsPort=$plan.httpsPort;$result.postgresPort=$plan.postgresPort
    if($CheckOnly){$result.valid=$true;$result.exitCode=0;$result.code='network_check_passed';$result.stage='checked';$result.readiness='not_checked'}
    elseif(Test-RcNetworkAlreadyConfigured $context){
        if($EnsureRunning){Start-RcNetworkExisting $context;$result.valid=$true;$result.success=$true;$result.exitCode=0;$result.code='network_existing_verified';$result.stage='verified';$result.readiness='ready'}
        else{$result.valid=$true;$result.success=$true;$result.exitCode=0;$result.code='network_already_configured';$result.stage='checked';$result.readiness='not_checked'}
        $result.publicOrigin=$plan.publicOrigin
    }
    else{
        Assert-RcNetworkServiceUnchanged $context
        $context.credential=Read-SetupServiceCredential $context.receipt.managementPath;if((Resolve-RcNetworkSid $context.credential.UserName)-cne$context.receipt.serviceSid){Stop-RcNetwork 'network_account_unresolved'}
        $null=Invoke-RcNetworkTransaction $context;$result.valid=$true;$result.success=$true;$result.exitCode=0;$result.code='network_change_verified';$result.stage='committed';$result.publicOrigin=$plan.publicOrigin;$result.backupManifestSha256=$context.verifiedBackup.manifestSha256;$result.journalDirectory=$context.transactionDirectory;$result.rootCaChanged=-not$context.tls.reused;$result.readiness='ready'
    }
}catch{if($_.Exception.Message-cin(Get-RcNetworkCodes)){$result.code=$_.Exception.Message};if(-not$context){$context=$script:rcNetworkContext};if($context){$result.stage=$context.stage;$result.rollbackStatus=$context.rollbackStatus;if($context.ContainsKey('failureStage')){$result.failureStage=$context.failureStage};if($context.ContainsKey('rollbackErrors')){$result.rollbackErrors=$context.rollbackErrors};if($context.ContainsKey('transactionDirectory')){$result.journalDirectory=$context.transactionDirectory}};$cause=$_.Exception;for($n=0;$n-lt8-and$null-ne$cause.InnerException;$n++){$cause=$cause.InnerException};$result.errorHResult=$cause.HResult;if($cause-is[ComponentModel.Win32Exception]){$result.nativeErrorCode=$cause.NativeErrorCode};if($cause.GetType().FullName-cin@('System.InvalidOperationException','System.ArgumentException','System.IO.IOException','System.UnauthorizedAccessException','System.ComponentModel.Win32Exception','System.Security.SecurityException')){$result.errorType=$cause.GetType().FullName};$result.failureLine=$_.InvocationInfo.ScriptLineNumber}
finally{if($context){Release-RcNetworkLocks $context;foreach($h in $context.codeLocks){$h.Dispose()};if($context.credential){$context.credential.Password.Dispose()};foreach($e in $context.entries){if($e.key-cin@('tls-password','pfx')){[Array]::Clear($e.snapshot.Bytes,0,$e.snapshot.Bytes.Length)}}};if($operationLock){$operationLock.Dispose()};[Environment]::SetEnvironmentVariable('PSModulePath',$originalModulePath,'Process')}
$result|ConvertTo-Json -Depth 6 -Compress
exit $result.exitCode
