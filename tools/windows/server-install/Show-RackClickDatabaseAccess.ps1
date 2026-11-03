#requires -Version 5.1
[CmdletBinding()]
param([ValidateSet('RackClick','RackClick-Recovery-cb52d279')][string]$ServiceName,[switch]$FunctionsOnly)
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'RackClick.SqlSecrets.ps1')
. (Join-Path $PSScriptRoot 'RackClick.MfaRuntime.ps1')
# Standalone private viewer. Import with -FunctionsOnly does not read files or enable privileges.
function Stop-RcDatabaseAccess([string]$Code){throw (New-Object InvalidOperationException($Code))}
function Test-RcDatabaseAccessGuid([string]$Value){$id=[guid]::Empty;return ([guid]::TryParseExact($Value,'D',[ref]$id)-and$id-ne[guid]::Empty-and$id.ToString('D')-ceq$Value)}
function Get-RcDatabaseAccessHash([byte[]]$Bytes){$sha=[Security.Cryptography.SHA256]::Create();try{return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}}
function Read-RcDatabaseAccessJson([byte[]]$Bytes,[string]$Code='database_access_json_invalid'){
    try{if($null-eq$Bytes-or$Bytes.Length-eq0-or$Bytes.Length-gt1048576){throw 'invalid'};$json=(New-Object Text.UTF8Encoding($false,$true)).GetString($Bytes);if(-not$json.TrimStart().StartsWith('{',[StringComparison]::Ordinal)){throw 'invalid'};$value=ConvertFrom-Json -InputObject $json -ErrorAction Stop;if($value-isnot[pscustomobject]){throw 'invalid'};return $value}catch{Stop-RcDatabaseAccess $Code}
}
function Assert-RcDatabaseAccessHash([byte[]]$Bytes,[string]$ExpectedSha256){if($ExpectedSha256-cnotmatch'^[a-f0-9]{64}$'-or(Get-RcDatabaseAccessHash $Bytes)-cne$ExpectedSha256){Stop-RcDatabaseAccess 'database_access_hash_mismatch'}}
function Assert-RcDatabaseAccessOrigin([string]$Origin){
    $uri=$null
    if(-not[Uri]::TryCreate($Origin,[UriKind]::Absolute,[ref]$uri)-or$uri.Scheme-cne'https'-or$uri.UserInfo-ne''-or$uri.AbsolutePath-ne'/'-or$uri.Query-ne''-or$uri.Fragment-ne''-or$uri.Port-lt1024-or$uri.Port-gt65535-or$uri.HostNameType-notin@([UriHostNameType]::Dns,[UriHostNameType]::IPv4)-or$Origin-cne$uri.GetLeftPart([UriPartial]::Authority)){Stop-RcDatabaseAccess 'database_access_origin_invalid'}
}
function Get-RcDatabaseAccessBinding([string]$ServiceName,[string]$ServicePathName){
    if($ServiceName-cnotin@('RackClick','RackClick-Recovery-cb52d279')-or$ServicePathName-cnotmatch'^"C:\\ProgramData\\RackClick\\Instances\\([a-f0-9-]{36})\\instance\\content\\dependencies\\dotnet\\dotnet\.exe" '){Stop-RcDatabaseAccess 'database_access_service_binding_invalid'}
    $id=$Matches[1];if(-not(Test-RcDatabaseAccessGuid $id)-or($ServiceName-ceq'RackClick-Recovery-cb52d279'-and$id-ceq'606b8c29-41de-4dc0-b63d-ade836000d9e')){Stop-RcDatabaseAccess 'database_access_service_binding_invalid'}
    $root='C:\ProgramData\RackClick\Instances\'+$id;$code='C:\Program Files\RackClick\'+$id;$instance=$root+'\instance'
    if($ServicePathName-cne('"'+$instance+'\content\dependencies\dotnet\dotnet.exe" "'+$code+'\service\RackClick.WindowsService.dll" --config "'+$instance+'\service-config.json"')){Stop-RcDatabaseAccess 'database_access_service_binding_invalid'}
    return @{installationId=$id;serviceName=$ServiceName;codeRoot=$code;instancePath=$instance;managementPath=($root+'\management');postgresPort=$(if($ServiceName-ceq'RackClick'){55441}else{55442})}
}
function Assert-RcDatabaseAccessReceipt($Receipt,$Binding){
    foreach($name in @('installationId','serviceName','codeRoot','instancePath','managementPath','accountName','serviceSid','manifestSha256','publicOrigin','backupTaskName')){if($Receipt.$name-isnot[string]){Stop-RcDatabaseAccess 'database_access_receipt_invalid'}}
    foreach($name in @('installationId','serviceName','codeRoot','instancePath','managementPath')){if($Receipt.$name-cne$Binding[$name]){Stop-RcDatabaseAccess 'database_access_receipt_invalid'}}
    if(($Binding.serviceName-ceq'RackClick'-and$Receipt.accountName-cnotmatch'^RackClickSvc(?:[a-zA-Z0-9]{1,8})?$')-or($Binding.serviceName-ceq'RackClick-Recovery-cb52d279'-and$Receipt.accountName-cne'RackClickSvcRc9')){Stop-RcDatabaseAccess 'database_access_receipt_invalid'}
    if($Receipt.schemaVersion-isnot[int]-or$Receipt.schemaVersion-ne1-or$Receipt.manifestSha256-cnotmatch'^[a-f0-9]{64}$'-or$Receipt.serviceSid-cnotmatch'^S-1-5-21-(\d+-){3}\d+$'-or$Receipt.serviceSid.EndsWith('-500')-or$Receipt.backupTaskName-cne('RackClick-Backup-'+$Binding.installationId)){Stop-RcDatabaseAccess 'database_access_receipt_invalid'}
    Assert-RcDatabaseAccessOrigin $Receipt.publicOrigin
}
function Test-RcDatabaseAccessPrincipal([string]$Observed,[string]$ExpectedSid,[string]$LocalMachine,[string]$LocalName){
    if([string]::IsNullOrEmpty($LocalName)-or$LocalName-cmatch'[\\@\x00-\x1f\x7f]'-or[string]::IsNullOrEmpty($LocalMachine)-or$LocalMachine-cmatch'[\\@\x00-\x1f\x7f]'){return $false}
    try{$sid=(New-Object Security.Principal.SecurityIdentifier($ExpectedSid)).Value;if($Observed-cmatch'^S-1-'){return (New-Object Security.Principal.SecurityIdentifier($Observed)).Value-ceq$sid}}catch{return $false}
    $name=if($Observed.StartsWith('.\',[StringComparison]::Ordinal)){$Observed.Substring(2)}elseif($Observed.StartsWith(($LocalMachine+'\'),[StringComparison]::OrdinalIgnoreCase)){$Observed.Substring($LocalMachine.Length+1)}else{return $false}
    return [string]::Equals($name,$LocalName,[StringComparison]::OrdinalIgnoreCase)
}
function Assert-RcDatabaseAccessProfile($Profile,$Binding,$Receipt){
    if($Profile.schemaVersion-isnot[int]-or$Profile.schemaVersion-notin@(1,2)-or$Profile.profileKind-cne'RackClickProductionServer'-or-not(Test-RcDatabaseAccessGuid $Profile.profileId)-or$Profile.expectedWindowsSid-cne$Receipt.serviceSid-or$Profile.installationPath-cne$Binding.instancePath-or$Profile.runtimeRoot-cne($Binding.instancePath+'\runtime')-or$Profile.deploymentPath-cne($Binding.instancePath+'\deployment')-or$Profile.publicOrigin-cne$Receipt.publicOrigin-or$Profile.deploymentSha256-cnotmatch'^[a-f0-9]{64}$'-or$Profile.installationSha256-cnotmatch'^[a-f0-9]{64}$'){Stop-RcDatabaseAccess 'database_access_profile_invalid'}
    if($Profile.schemaVersion-eq2-and((($Profile.PSObject.Properties.Name|Sort-Object)-join',')-cne'bindAddress,certificate,createdUtc,deploymentPath,deploymentSha256,expectedWindowsSid,installationPath,installationSha256,mfa,profileId,profileKind,publicOrigin,runtimeRoot,schemaVersion')){Stop-RcDatabaseAccess 'database_access_profile_invalid'}
    try{$null=Get-ServerMfaProfile -Manifest $Profile -InstallationId $Binding.installationId}catch{Stop-RcDatabaseAccess 'database_access_profile_invalid'}
}
function Assert-RcDatabaseAccessDeployment($Deployment,$Binding){
    if($Deployment.schemaVersion-isnot[int]-or$Deployment.schemaVersion-ne1-or$Deployment.kind-cne'RackClickPrivateDeployment'-or$Deployment.state-cne'prepared'-or$Deployment.rootPath-cne($Binding.instancePath+'\deployment')-or-not(Test-RcDatabaseAccessGuid $Deployment.id)-or-not(Test-RcDatabaseAccessGuid $Deployment.instanceId)-or$Deployment.instanceManifestSha256-cnotmatch'^[a-f0-9]{64}$'){Stop-RcDatabaseAccess 'database_access_deployment_invalid'}
    Assert-RcDatabaseAccessOrigin $Deployment.publicOrigin;if(([uri]$Deployment.publicOrigin).Host-cne'127.0.0.1'){Stop-RcDatabaseAccess 'database_access_deployment_invalid'}
}
function Read-RcDatabaseAccessManifest([byte[]]$Bytes,[string]$ExpectedSha256,[string]$ExpectedRoot,[int]$ExpectedPort){
    Assert-RcDatabaseAccessHash $Bytes $ExpectedSha256;$m=Read-RcDatabaseAccessJson $Bytes 'database_access_manifest_invalid'
    if($m.schemaVersion-isnot[int]-or$m.schemaVersion-notin@(1,2,3)-or$m.kind-cne'RackClickLabInstance'-or$m.state-cne'initialized'-or-not(Test-RcDatabaseAccessGuid $m.id)-or$m.rootPath-cne$ExpectedRoot-or$m.postgresPort-isnot[int]-or$m.postgresPort-ne$ExpectedPort-or$ExpectedPort-lt1024-or$ExpectedPort-gt65535-or$m.secretFiles-isnot[pscustomobject]){Stop-RcDatabaseAccess 'database_access_manifest_invalid'}
    if($m.httpPort-isnot[int]-or$m.httpPort-lt1024-or$m.httpPort-gt65535-or$m.httpPort-eq$m.postgresPort-or$m.developmentLoopbackHttp-isnot[bool]-or-not$m.developmentLoopbackHttp-or$m.publicOrigin-cne('http://127.0.0.1:'+$m.httpPort)){Stop-RcDatabaseAccess 'database_access_manifest_invalid'}
    $suffix=$m.id.Replace('-','');foreach($pair in @(@('database','rc_db_'),@('runtime','rc_runtime_'),@('owner','rc_owner_'),@('clusterAdmin','rc_cluster_'))){if($m.($pair[0])-cne($pair[1]+$suffix)){Stop-RcDatabaseAccess 'database_access_manifest_invalid'}}
    if($m.schemaVersion-eq3-and((($m.PSObject.Properties.Name|Sort-Object)-join',')-cne'backupRole,clusterAdmin,database,developmentLoopbackHttp,dotnetPath,httpPort,id,kind,owner,postgresBinPath,postgresPort,publicOrigin,rootPath,runtime,schemaVersion,secretFiles,stageManifestSha256,stagePath,stageReceiptSha256,state')){Stop-RcDatabaseAccess 'database_access_manifest_invalid'}
    if($m.schemaVersion-eq3-and($m.backupRole-isnot[string]-or$m.backupRole-cne('rc_backup_'+$suffix))){Stop-RcDatabaseAccess 'database_access_manifest_invalid'}
    $secretNames=switch($m.schemaVersion){1{'admin-login.json,backup-profile.json,cluster-password.txt,owner-password.txt,runtime.json'}2{'admin-login.json,backup-profile.json,cluster-password.dpapi.json,cluster-profile.json,owner-password.dpapi.json,runtime.json'}3{'admin-login.json,backup-password.dpapi.json,backup-profile.json,runtime.json'}}
    if((($m.secretFiles.PSObject.Properties.Name|Sort-Object)-join',')-cne$secretNames){Stop-RcDatabaseAccess 'database_access_manifest_invalid'}
    foreach($property in $m.secretFiles.PSObject.Properties){if($property.Value-isnot[string]-or$property.Value-cnotmatch'^[a-f0-9]{64}$'){Stop-RcDatabaseAccess 'database_access_manifest_invalid'}}
    return $m
}
function Read-RcDatabaseAccessRuntime([byte[]]$Bytes,$Manifest,[byte[]]$CipherBytes=$null,[string]$ReaderSid=''){
    Assert-RcDatabaseAccessHash $Bytes $Manifest.secretFiles.'runtime.json';$value=Read-RcDatabaseAccessJson $Bytes 'database_access_runtime_invalid'
    $builder=$null;$protectedMode=$false
    try{
        $map=ConvertTo-SqlOperatorMap $value
        if($map.ContainsKey('schemaVersion')){
            $protectedMode=$true
            $definition=Get-SqlRuntimeDefinition $value $Manifest.rootPath $Manifest.id $Manifest.database $Manifest.runtime
            if($null-eq$CipherBytes){return @{sqlDefinition=$definition}}
            Assert-RcDatabaseAccessHash $CipherBytes $definition.ciphertextSha256
            $connection=Unprotect-SqlRuntimeConnection $CipherBytes $Manifest.id $ReaderSid $Manifest.database $Manifest.runtime
            $value=[pscustomobject]@{connectionString=$connection}
        }
        elseif($Manifest.schemaVersion-in@(2,3)){throw 'invalid'}
        if((@($value.PSObject.Properties.Name)-join',')-cne'connectionString'-or$value.connectionString-isnot[string]){throw 'invalid'}
        $builder=New-Object Data.Common.DbConnectionStringBuilder;$builder.set_ConnectionString($value.connectionString)
        $keys=(@($builder.Keys|ForEach-Object{$_.ToLowerInvariant()}|Sort-Object)-join',')
        $legacyKeys='command timeout,database,host,password,port,ssl mode,timeout,username'
        $protectedKeys='command timeout,database,host,include error detail,log parameters,password,persist security info,port,ssl mode,timeout,username'
        if($keys-cne$legacyKeys-and(-not$protectedMode-or$keys-cne$protectedKeys)){throw 'invalid'}
        if($keys-ceq$protectedKeys){foreach($key in @('Persist Security Info','Include Error Detail','Log Parameters')){if([string]$builder[$key]-ine'false'){throw 'invalid'}}}
        if([string]$builder['Host']-cne'127.0.0.1'-or[string]$builder['Port']-cne[string]$Manifest.postgresPort-or[string]$builder['Database']-cne$Manifest.database-or[string]$builder['Username']-cne$Manifest.runtime-or[string]$builder['Password']-cnotmatch'^[a-f0-9]{64}$'-or[string]$builder['SSL Mode']-cne'Disable'-or[string]$builder['Timeout']-cne'5'-or[string]$builder['Command Timeout']-cne'15'){throw 'invalid'}
        return @{host='127.0.0.1';port=$Manifest.postgresPort;database=$Manifest.database;username=$Manifest.runtime;password=[string]$builder['Password']}
    }catch{Stop-RcDatabaseAccess 'database_access_runtime_invalid'}finally{if($null-ne$builder){$builder.Clear()}}
}
function Read-RcDatabaseAccessLogin([byte[]]$Bytes){
    $v=Read-RcDatabaseAccessJson $Bytes 'database_access_login_invalid'
    if($Bytes.Length-gt65536-or(@($v.PSObject.Properties.Name|Sort-Object)-join',')-cne'password,username'-or$v.username-isnot[string]-or$v.password-isnot[string]-or[string]::IsNullOrWhiteSpace($v.username)-or$v.username.Length-gt256-or$v.password.Length-lt1-or$v.password.Length-gt4096-or$v.username-cmatch'[\x00-\x1f\x7f]'-or$v.password-cmatch'[\x00-\x1f\x7f]'){Stop-RcDatabaseAccess 'database_access_login_invalid'}
    return @{username=$v.username;password=$v.password}
}
function Format-RcDatabasePrivateAccess($Access){
    return Format-RcDatabaseAccessMetadata $Access
}
function Format-RcDatabaseAccessMetadata($Access){
    # Export metadata only. Neither password is read, interpolated or persisted.
    foreach($key in @('installationId','serviceName','publicOrigin','host','database','username','webUsername')){
        if($Access[$key]-isnot[string]-or[string]::IsNullOrWhiteSpace($Access[$key])-or$Access[$key].Length-gt4096-or$Access[$key]-cmatch'[\x00-\x1f\x7f]'){Stop-RcDatabaseAccess 'database_access_card_invalid'}
    }
    if(-not(Test-RcDatabaseAccessGuid $Access.installationId)-or$Access.serviceName-cnotmatch'^RackClick(?:-Recovery-[a-f0-9]{8,32})?$'-or$Access.host-cne'127.0.0.1'-or$Access.port-isnot[int]-or$Access.port-lt1024-or$Access.port-gt65535-or$Access.database-cnotmatch'^rc_db_[a-f0-9]{32}$'-or$Access.username-cnotmatch'^rc_runtime_[a-f0-9]{32}$'){Stop-RcDatabaseAccess 'database_access_card_invalid'}
    Assert-RcDatabaseAccessOrigin $Access.publicOrigin
    return (@('RACKCLICK - FICHA DE CONEXION SIN CONTRASENAS','Las contrasenas solo se consultan en la ventana privada autorizada; no se exportan.',('Instalacion: '+$Access.installationId),('Servicio: '+$Access.serviceName),('URL: '+$Access.publicOrigin),('Usuario web: '+$Access.webUsername),'HEIDISQL: PostgreSQL TCP/IP, acceso local:',('Host: '+$Access.host),('Puerto: '+$Access.port),('Base: '+$Access.database),('Usuario SQL: '+$Access.username),'LECTURA/ESCRITURA: SELECT, INSERT, UPDATE, DELETE. SQL directo no aplica los ambitos por cliente.','Restore en otra instancia requiere credenciales nuevas; esta ficha no es una copia de seguridad.')-join"`r`n")+"`r`n"
}
function Initialize-RcDatabaseAccessReader {
    if('RackClickDatabasePrivateReader'-as[type]){return}
    Add-Type -TypeDefinition @'
using System;using System.IO;using System.Collections.Generic;using System.Security.AccessControl;using System.ComponentModel;using System.Runtime.InteropServices;using Microsoft.Win32.SafeHandles;
public static class RackClickDatabasePrivateReader {
 [StructLayout(LayoutKind.Sequential)]struct LUID{public uint Low;public int High;}
 [StructLayout(LayoutKind.Sequential)]struct TP{public uint Count;public LUID Id;public uint Attributes;}
 [DllImport("kernel32.dll")]static extern IntPtr GetCurrentProcess();
 [DllImport("kernel32.dll")]static extern bool CloseHandle(IntPtr p);
 [DllImport("advapi32.dll",SetLastError=true)]static extern bool OpenProcessToken(IntPtr p,uint a,out IntPtr t);
 [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern bool LookupPrivilegeValue(string s,string n,out LUID l);
 [DllImport("advapi32.dll",SetLastError=true)]static extern bool AdjustTokenPrivileges(IntPtr t,bool d,ref TP n,int z,out TP old,out int ret);
 static uint BackupPrivilege(uint attributes){IntPtr t;if(!OpenProcessToken(GetCurrentProcess(),0x28,out t))throw new Win32Exception();try{LUID id;if(!LookupPrivilegeValue(null,"SeBackupPrivilege",out id))throw new Win32Exception();TP next=new TP{Count=1,Id=id,Attributes=attributes},old;int size;if(!AdjustTokenPrivileges(t,false,ref next,Marshal.SizeOf(typeof(TP)),out old,out size))throw new Win32Exception();int e=Marshal.GetLastWin32Error();if(e!=0)throw new Win32Exception(e);return old.Count==0?attributes:old.Attributes;}finally{CloseHandle(t);}}
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern SafeFileHandle CreateFile(string p,uint a,uint s,IntPtr sa,uint c,uint f,IntPtr t);
 [DllImport("kernel32.dll",SetLastError=true)]static extern bool GetFileInformationByHandle(SafeFileHandle h,out Info i);
 [StructLayout(LayoutKind.Sequential)]struct Info{public uint Attributes,CreationLow,CreationHigh,AccessLow,AccessHigh,WriteLow,WriteHigh,Volume,SizeHigh,SizeLow,Links,IndexHigh,IndexLow;}
 [DllImport("advapi32.dll")]static extern uint GetSecurityInfo(SafeFileHandle h,int type,uint info,out IntPtr o,out IntPtr g,out IntPtr d,out IntPtr s,out IntPtr sd);
 [DllImport("advapi32.dll")]static extern uint GetSecurityDescriptorLength(IntPtr sd);
 [DllImport("kernel32.dll")]static extern IntPtr LocalFree(IntPtr p);
 public static bool IsPrivateSddl(string sddl,string serviceSid,bool management){return IsPrivateSddlCore(sddl,serviceSid,management,false);}
 public static bool IsPrivateContainerSddl(string sddl,string serviceSid){return IsPrivateSddlCore(sddl,serviceSid,false,true);}
 static bool IsPrivateSddlCore(string sddl,string serviceSid,bool management,bool container){try{
  var sd=new RawSecurityDescriptor(sddl);string other=management?"S-1-5-32-544":serviceSid;
  if(sd.Owner==null||(sd.Owner.Value!="S-1-5-18"&&sd.Owner.Value!=other)||sd.DiscretionaryAcl==null||sd.DiscretionaryAcl.Count<2)return false;
  bool system=false,peer=false,administrativeTraversal=false;
  foreach(GenericAce raw in sd.DiscretionaryAcl){
   var a=raw as CommonAce;if(a==null||a.IsCallback||a.AceQualifier!=AceQualifier.AccessAllowed||a.AccessMask==0||(a.AceFlags&AceFlags.InheritOnly)!=0)return false;
   if(!management&&container&&a.SecurityIdentifier.Value=="S-1-5-32-544"){
    // The installer grants only attributes+traverse, on this container alone.
    // Never accept this exception for a file or an ordinary private parent.
    if(administrativeTraversal||a.AccessMask!=0xA0||a.AceFlags!=AceFlags.None)return false;
    administrativeTraversal=true;continue;
   }
   if(a.SecurityIdentifier.Value=="S-1-5-18")system=true;else if(a.SecurityIdentifier.Value==other)peer=true;else return false;
  }
  return system&&peer;
 }catch{return false;}}
 static void PrivateAcl(SafeFileHandle h,string sid,bool management){PrivateAcl(h,sid,management,false);}
 static void PrivateAcl(SafeFileHandle h,string sid,bool management,bool container){IntPtr o,g,d,s,sd;uint e=GetSecurityInfo(h,1,7,out o,out g,out d,out s,out sd);if(e!=0)throw new Win32Exception((int)e);try{uint size=GetSecurityDescriptorLength(sd);if(size==0||size>65536)throw new InvalidOperationException("database_access_private_acl_invalid");byte[] b=new byte[size];Marshal.Copy(sd,b,0,b.Length);if(!IsPrivateSddlCore(new RawSecurityDescriptor(b,0).GetSddlForm(AccessControlSections.Owner|AccessControlSections.Group|AccessControlSections.Access),sid,management,container))throw new InvalidOperationException("database_access_private_acl_invalid");}finally{LocalFree(sd);}}
 static SafeFileHandle Open(string path,bool directory){var h=CreateFile(path,directory?0x20080u:0x20081u,1,IntPtr.Zero,3,0x02200000,IntPtr.Zero);if(h.IsInvalid){int e=Marshal.GetLastWin32Error();h.Dispose();throw new Win32Exception(e);}Info i;if(!GetFileInformationByHandle(h,out i)){int e=Marshal.GetLastWin32Error();h.Dispose();throw new Win32Exception(e);}if((i.Attributes&0x400)!=0||((i.Attributes&0x10)!=0)!=directory||(!directory&&i.Links!=1)){h.Dispose();throw new InvalidOperationException("database_access_private_path_invalid");}return h;}
 static List<SafeFileHandle> Parents(string path,string root,string sid,bool management){var result=new List<SafeFileHandle>();try{for(string p=Path.GetDirectoryName(path);!String.IsNullOrEmpty(p);p=Path.GetDirectoryName(p)){var h=Open(p,true);result.Add(h);bool isRoot=String.Equals(p,root,StringComparison.Ordinal);if(isRoot||p.StartsWith(root+"\\",StringComparison.Ordinal))PrivateAcl(h,sid,management,!management&&isRoot);}return result;}catch{foreach(var h in result)h.Dispose();throw;}}
 static byte[] ReadCore(string path,string root,string sid,bool management,int maximum){if(maximum<1||maximum>1048576||!path.StartsWith(root+"\\",StringComparison.Ordinal)||(management&&!String.Equals(Path.GetDirectoryName(path),root,StringComparison.Ordinal)))throw new InvalidOperationException("database_access_private_path_invalid");var parents=Parents(path,root,sid,management);try{using(var h=Open(path,false)){PrivateAcl(h,sid,management);using(var f=new FileStream(h,FileAccess.Read)){if(f.Length<=0||f.Length>maximum)throw new InvalidOperationException("database_access_private_size_invalid");byte[] bytes=new byte[(int)f.Length];try{int at=0;while(at<bytes.Length){int n=f.Read(bytes,at,bytes.Length-at);if(n<=0)throw new EndOfStreamException();at+=n;}if(f.ReadByte()!=-1)throw new InvalidOperationException("database_access_private_read_failed");return bytes;}catch{Array.Clear(bytes,0,bytes.Length);throw;}}}}finally{foreach(var h in parents)h.Dispose();}}
 public static byte[] ReadManagement(string path,string management,int maximum){if(Path.GetFileName(path)!="server-installation.json"&&Path.GetFileName(path)!="admin-login.json")throw new InvalidOperationException("database_access_private_path_invalid");return ReadCore(path,management,null,true,maximum);}
 public static byte[] ReadPrepared(string path,string instance,string sid,int maximum){string relative=path.StartsWith(instance+"\\",StringComparison.Ordinal)?path.Substring(instance.Length+1):"";if(relative!="runtime\\server-profile.json"&&relative!="deployment\\deployment.json"&&relative!="deployment\\instance\\instance.json"&&relative!="deployment\\instance\\private\\runtime.json"&&relative!="deployment\\instance\\private\\admin-login.json"&&!System.Text.RegularExpressions.Regex.IsMatch(relative,@"\Adeployment\\instance\\sql-security\\[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\sql-secrets\\runtime\.bin\z"))throw new InvalidOperationException("database_access_private_path_invalid");uint previous=BackupPrivilege(2);try{return ReadCore(path,instance,sid,false,maximum);}finally{BackupPrivilege(previous);}}
 [StructLayout(LayoutKind.Sequential)]struct SA{public int Length;public IntPtr Descriptor;public int Inherit;}
 public static void WriteNew(string path,string management,byte[] bytes){string name=Path.GetFileName(path);Guid id;if(!String.Equals(Path.GetDirectoryName(path),management,StringComparison.Ordinal)||!name.StartsWith("ACCESO-PRIVADO-",StringComparison.Ordinal)||!name.EndsWith(".txt",StringComparison.Ordinal)||!Guid.TryParseExact(name.Substring(15,name.Length-19),"D",out id)||bytes==null||bytes.Length==0||bytes.Length>65536)throw new InvalidOperationException("database_access_private_path_invalid");var parents=Parents(path,management,null,true);try{var sd=new RawSecurityDescriptor("O:BAG:SYD:P(A;;FA;;;BA)(A;;FA;;;SY)");byte[] raw=new byte[sd.BinaryLength];sd.GetBinaryForm(raw,0);GCHandle pin=GCHandle.Alloc(raw,GCHandleType.Pinned);IntPtr attr=IntPtr.Zero;try{var sa=new SA{Length=Marshal.SizeOf(typeof(SA)),Descriptor=pin.AddrOfPinnedObject(),Inherit=0};attr=Marshal.AllocHGlobal(sa.Length);Marshal.StructureToPtr(sa,attr,false);using(var h=CreateFile(path,0x40020000u,0,attr,1,0x00200000,IntPtr.Zero)){if(h.IsInvalid)throw new Win32Exception();Info info;if(!GetFileInformationByHandle(h,out info))throw new Win32Exception();if((info.Attributes&0x410)!=0||info.Links!=1)throw new InvalidOperationException("database_access_private_path_invalid");PrivateAcl(h,null,true);using(var f=new FileStream(h,FileAccess.Write)){f.Write(bytes,0,bytes.Length);f.Flush(true);}}}finally{if(attr!=IntPtr.Zero)Marshal.FreeHGlobal(attr);pin.Free();}}finally{foreach(var h in parents)h.Dispose();}}
}
'@
}
function Write-RcDatabasePrivateAccess($Access,[string]$ManagementPath){
    Initialize-RcDatabaseAccessReader;$bytes=$null
    try{$text=Format-RcDatabaseAccessMetadata $Access;$bytes=(New-Object Text.UTF8Encoding($true)).GetPreamble()+(New-Object Text.UTF8Encoding($false)).GetBytes($text);$path=$ManagementPath+'\ACCESO-PRIVADO-'+[guid]::NewGuid().ToString('D')+'.txt';[RackClickDatabasePrivateReader]::WriteNew($path,$ManagementPath,$bytes);return $path}finally{if($null-ne$bytes){[Array]::Clear($bytes,0,$bytes.Length)};$text=$null}
}
function Get-RcDatabasePrivateAccess([string]$SelectedService){
    if($SelectedService-cnotin@('RackClick','RackClick-Recovery-cb52d279')){Stop-RcDatabaseAccess 'database_access_service_binding_invalid'}
    $services=@(Get-CimInstance Win32_Service -Filter ("Name='"+$SelectedService+"'"));if($services.Count-ne1-or$services[0].Name-cne$SelectedService){Stop-RcDatabaseAccess 'database_access_service_missing'}
    $binding=Get-RcDatabaseAccessBinding $SelectedService $services[0].PathName;Initialize-RcDatabaseAccessReader;$bytes=$null;$runtime=$null;$login=$null
    try{
        $bytes=[RackClickDatabasePrivateReader]::ReadManagement(($binding.managementPath+'\server-installation.json'),$binding.managementPath,1048576);$receipt=Read-RcDatabaseAccessJson $bytes 'database_access_receipt_invalid';Assert-RcDatabaseAccessReceipt $receipt $binding;[Array]::Clear($bytes,0,$bytes.Length)
        $sam=@(Get-LocalUser -SID (New-Object Security.Principal.SecurityIdentifier($receipt.serviceSid)));if($sam.Count-ne1-or$sam[0].SID.Value-cne$receipt.serviceSid-or-not[string]::Equals($sam[0].Name,$receipt.accountName,[StringComparison]::OrdinalIgnoreCase)-or-not(Test-RcDatabaseAccessPrincipal $services[0].StartName $receipt.serviceSid ([Environment]::MachineName) $sam[0].Name)){Stop-RcDatabaseAccess 'database_access_service_identity_invalid'}
        $bytes=[RackClickDatabasePrivateReader]::ReadPrepared(($binding.instancePath+'\runtime\server-profile.json'),$binding.instancePath,$receipt.serviceSid,1048576);Assert-RcDatabaseAccessHash $bytes $receipt.manifestSha256;$profile=Read-RcDatabaseAccessJson $bytes 'database_access_profile_invalid';Assert-RcDatabaseAccessProfile $profile $binding $receipt;[Array]::Clear($bytes,0,$bytes.Length)
        $bytes=[RackClickDatabasePrivateReader]::ReadPrepared(($binding.instancePath+'\deployment\deployment.json'),$binding.instancePath,$receipt.serviceSid,1048576);Assert-RcDatabaseAccessHash $bytes $profile.deploymentSha256;$deployment=Read-RcDatabaseAccessJson $bytes 'database_access_deployment_invalid';Assert-RcDatabaseAccessDeployment $deployment $binding;[Array]::Clear($bytes,0,$bytes.Length)
        $root=$binding.instancePath+'\deployment\instance';$bytes=[RackClickDatabasePrivateReader]::ReadPrepared(($root+'\instance.json'),$binding.instancePath,$receipt.serviceSid,32768);$manifest=Read-RcDatabaseAccessManifest $bytes $deployment.instanceManifestSha256 $root $binding.postgresPort;if($manifest.id-cne$deployment.instanceId-or([uri]$deployment.publicOrigin).Port-ne$manifest.httpPort-or([uri]$receipt.publicOrigin).Port-ne$manifest.httpPort){Stop-RcDatabaseAccess 'database_access_manifest_invalid'};[Array]::Clear($bytes,0,$bytes.Length)
        $bytes=[RackClickDatabasePrivateReader]::ReadPrepared(($root+'\private\runtime.json'),$binding.instancePath,$receipt.serviceSid,16384);$runtime=Read-RcDatabaseAccessRuntime $bytes $manifest
        if($runtime.ContainsKey('sqlDefinition')){
            $cipher=$null
            try{$cipher=[RackClickDatabasePrivateReader]::ReadPrepared($runtime.sqlDefinition.file,$binding.instancePath,$receipt.serviceSid,65536);$runtime=Read-RcDatabaseAccessRuntime $bytes $manifest $cipher $receipt.serviceSid}finally{if($null-ne$cipher){[Array]::Clear($cipher,0,$cipher.Length)}}
        }
        [Array]::Clear($bytes,0,$bytes.Length)
        $bytes=[RackClickDatabasePrivateReader]::ReadManagement(($binding.managementPath+'\admin-login.json'),$binding.managementPath,65536);Assert-RcDatabaseAccessHash $bytes $manifest.secretFiles.'admin-login.json';$login=Read-RcDatabaseAccessLogin $bytes
        $runtime.installationId=$binding.installationId;$runtime.serviceName=$SelectedService;$runtime.publicOrigin=$receipt.publicOrigin;$runtime.webUsername=$login.username;$runtime.webPassword=$login.password;$runtime.managementPath=$binding.managementPath;return $runtime
    }finally{if($null-ne$bytes){[Array]::Clear($bytes,0,$bytes.Length)};if($null-ne$login){$login.password=$null;$login.username=$null}}
}
function Get-RcDatabaseAccessFailure($ErrorRecord){
    $e=$ErrorRecord.Exception;for($i=0;$i-lt8-and$null-ne$e.InnerException;$i++){$e=$e.InnerException};$allowed=@('database_access_json_invalid','database_access_hash_mismatch','database_access_origin_invalid','database_access_service_binding_invalid','database_access_receipt_invalid','database_access_profile_invalid','database_access_deployment_invalid','database_access_manifest_invalid','database_access_runtime_invalid','database_access_login_invalid','database_access_card_invalid','database_access_private_acl_invalid','database_access_private_path_invalid','database_access_private_size_invalid','database_access_private_read_failed','database_access_service_missing','database_access_service_identity_invalid','database_access_elevated_winps51_x64_sta_required')
    return @{code=$(if($e.Message-cin$allowed){$e.Message}else{'database_access_failed'});errorHResult=$e.HResult}
}
function Show-RcDatabasePrivateAccessWindow([string]$SelectedService){
    Add-Type -AssemblyName System.Windows.Forms;Add-Type -AssemblyName System.Drawing;[Windows.Forms.Application]::EnableVisualStyles()
    $form=New-Object Windows.Forms.Form;$form.Text='RackClick - Acceso privado web y PostgreSQL';$form.StartPosition='CenterScreen';$form.ClientSize=New-Object Drawing.Size(780,610);$form.MinimumSize=$form.Size;$form.MaximizeBox=$false;$form.AutoScaleMode='Dpi';$form.Font=New-Object Drawing.Font('Segoe UI',10)
    $layout=New-Object Windows.Forms.TableLayoutPanel;$layout.Dock='Fill';$layout.Padding=New-Object Windows.Forms.Padding(18);$layout.ColumnCount=2;$layout.RowCount=14;$null=$layout.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Absolute',175)));$null=$layout.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent',100)));$form.Controls.Add($layout)
    $notice=New-Object Windows.Forms.Label;$notice.Text='Solo para la persona administradora. SQL permite LECTURA/ESCRITURA sin ambitos web.';$notice.AutoSize=$true;$notice.Dock='Fill';$layout.Controls.Add($notice,0,0);$layout.SetColumnSpan($notice,2)
    $selector=New-Object Windows.Forms.ComboBox;$selector.DropDownStyle='DropDownList';$selector.Dock='Fill';$null=$selector.Items.Add('Original (RackClick)');$null=$selector.Items.Add('Restaurada (RC9)');$layout.Controls.Add($selector,1,1);$choose=New-Object Windows.Forms.Label;$choose.Text='Instalacion';$choose.AutoSize=$true;$layout.Controls.Add($choose,0,1)
    $fields=@{};$row=2;foreach($pair in @(@('publicOrigin','URL web'),@('webUsername','Usuario web'),@('webPassword','Contrasena web'),@('host','Host PostgreSQL'),@('port','Puerto PostgreSQL'),@('database','Base de datos'),@('username','Usuario SQL aplicacion'),@('password','Contrasena PostgreSQL'))){$label=New-Object Windows.Forms.Label;$label.Text=$pair[1];$label.AutoSize=$true;$layout.Controls.Add($label,0,$row);$box=New-Object Windows.Forms.TextBox;$box.ReadOnly=$true;$box.Dock='Fill';$box.ShortcutsEnabled=$true;$box.ContextMenu=New-Object Windows.Forms.ContextMenu;if($pair[0]-in@('webPassword','password')){$box.UseSystemPasswordChar=$true;$box.ShortcutsEnabled=$false};$fields[$pair[0]]=$box;$layout.Controls.Add($box,1,$row);$row++}
    $state=@{access=$null};$status=New-Object Windows.Forms.Label;$status.AutoSize=$true;$status.Dock='Fill';$layout.Controls.Add($status,0,12);$layout.SetColumnSpan($status,2)
    $reveal=New-Object Windows.Forms.CheckBox;$reveal.Text='Mostrar contrasenas';$reveal.AutoSize=$true;$reveal.Add_CheckedChanged({$fields.password.UseSystemPasswordChar=-not$reveal.Checked;$fields.webPassword.UseSystemPasswordChar=-not$reveal.Checked;$fields.password.ShortcutsEnabled=$reveal.Checked;$fields.webPassword.ShortcutsEnabled=$reveal.Checked});$layout.Controls.Add($reveal,1,10)
    $hint=New-Object Windows.Forms.Label;$hint.Text='HeidiSQL: PostgreSQL (TCP/IP), SSL deshabilitado, en esta VM. La web puede tener otra contrasena si ya la cambiaste.';$hint.AutoSize=$true;$hint.Dock='Fill';$layout.Controls.Add($hint,0,11);$layout.SetColumnSpan($hint,2)
    $buttons=New-Object Windows.Forms.FlowLayoutPanel;$buttons.AutoSize=$true;$buttons.Dock='Fill';$save=New-Object Windows.Forms.Button;$save.Text='Guardar ficha sin contrasenas';$save.AutoSize=$true;$save.Enabled=$false;$buttons.Controls.Add($save);$close=New-Object Windows.Forms.Button;$close.Text='Cerrar';$close.AutoSize=$true;$close.Add_Click({$form.Close()});$buttons.Controls.Add($close);$layout.Controls.Add($buttons,0,13);$layout.SetColumnSpan($buttons,2);$form.CancelButton=$close
    $selector.Add_SelectedIndexChanged({
        foreach($box in $fields.Values){$box.Clear()};if($null-ne$state.access){$state.access.password=$null;$state.access.webPassword=$null};$state.access=$null;$save.Enabled=$false;$reveal.Checked=$false;$status.Text=''
        try{$selected=if($selector.SelectedIndex-eq0){'RackClick'}else{'RackClick-Recovery-cb52d279'};$state.access=Get-RcDatabasePrivateAccess $selected;foreach($key in $fields.Keys){$fields[$key].Text=[string]$state.access[$key]};$save.Enabled=$true;$status.Text='Datos privados validados. Guarda la ficha solo en un lugar protegido.'}catch{$failure=Get-RcDatabaseAccessFailure $_;$status.Text='No se pudo leer el acceso privado. Codigo: '+$failure.code;[Windows.Forms.MessageBox]::Show('No se pudieron validar los archivos privados o sus permisos. No se ha cambiado la instalacion. Codigo: '+$failure.code,'RackClick','OK','Error')|Out-Null}
    })
    $save.Add_Click({try{$path=Write-RcDatabasePrivateAccess $state.access $state.access.managementPath;$status.Text='Ficha sin contrasenas guardada: '+$path;[Windows.Forms.MessageBox]::Show('Ficha sin contrasenas guardada en:'+"`r`n"+$path,'RackClick','OK','Information')|Out-Null}catch{$failure=Get-RcDatabaseAccessFailure $_;$status.Text='No se pudo guardar. Codigo: '+$failure.code;[Windows.Forms.MessageBox]::Show('No se pudo crear la ficha privada. Comprueba los permisos administrativos. Codigo: '+$failure.code,'RackClick','OK','Error')|Out-Null}})
    try{if($SelectedService){$selector.SelectedIndex=$(if($SelectedService-ceq'RackClick'){0}else{1})};$null=$form.ShowDialog()}finally{foreach($box in $fields.Values){$box.Clear()};if($null-ne$state.access){$state.access.password=$null;$state.access.webPassword=$null};$form.Dispose()}
}
if($FunctionsOnly){return}
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$result=[ordered]@{schemaVersion=1;valid=$false;success=$false;exitCode=2;code='database_access_failed'};$exitCode=2;$modulePath=$env:PSModulePath
try{
    if($PSVersionTable.PSEdition-cne'Desktop'-or$PSVersionTable.PSVersion.Major-ne5-or-not[Environment]::Is64BitProcess-or[Threading.Thread]::CurrentThread.ApartmentState-ne'STA'-or-not(New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){Stop-RcDatabaseAccess 'database_access_elevated_winps51_x64_sta_required'}
    $env:PSModulePath=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules';Show-RcDatabasePrivateAccessWindow $ServiceName;$result.valid=$true;$result.success=$true;$result.exitCode=0;$result.code='database_access_window_closed';$exitCode=0
}catch{$failure=Get-RcDatabaseAccessFailure $_;$result.code=$failure.code;$result.errorHResult=$failure.errorHResult;try{Add-Type -AssemblyName System.Windows.Forms;[Windows.Forms.MessageBox]::Show('Abre este auxiliar como administrador con Windows PowerShell 5.1 x64. Codigo: '+$result.code,'RackClick','OK','Error')|Out-Null}catch{}}
finally{[Environment]::SetEnvironmentVariable('PSModulePath',$modulePath,'Process')}
$result|ConvertTo-Json -Compress
exit $exitCode
