#requires -Version 5.1
# Broker-only security primitives. Import performs no privileged operation.
function Test-SetupAdministrator {
    $p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
function Assert-SetupAdministrator {
    if (-not [Environment]::Is64BitProcess -or -not (Test-SetupAdministrator)) { throw 'setup_elevated_x64_required' }
}
function Initialize-SetupSecurityNative {
    if ('RackClickSetupSecurityNative' -as [type]) { return }
    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using System.IO;
using System.Collections.Generic;
using Microsoft.Win32.SafeHandles;
public static class RackClickSetupSecurityNative {
 [StructLayout(LayoutKind.Sequential)] struct LUID {public uint Low; public int High;}
 [StructLayout(LayoutKind.Sequential)] struct TP {public uint Count; public LUID Id; public uint Attributes;}
 [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr p);
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool OpenProcessToken(IntPtr p,uint a,out IntPtr t);
 [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool LookupPrivilegeValue(string s,string n,out LUID l);
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool AdjustTokenPrivileges(IntPtr t,bool d,ref TP n,int z,out TP old,out int ret);
 public static uint Privilege(string name,uint attributes) {
  IntPtr t; if(!OpenProcessToken(GetCurrentProcess(),0x28,out t))throw new Win32Exception();
  try {LUID id;if(!LookupPrivilegeValue(null,name,out id))throw new Win32Exception();
   TP next=new TP{Count=1,Id=id,Attributes=attributes},old;int size;
   if(!AdjustTokenPrivileges(t,false,ref next,Marshal.SizeOf(typeof(TP)),out old,out size))throw new Win32Exception();
   int e=Marshal.GetLastWin32Error();if(e!=0)throw new Win32Exception(e);
   // An already-matching privilege is omitted from PreviousState. Preserve its
   // enabled/disabled state rather than returning the zeroed output structure.
   return old.Count==0?attributes:old.Attributes;
  } finally{CloseHandle(t);}
 }
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern SafeFileHandle CreateFile(string p,uint a,uint s,IntPtr sa,uint c,uint f,IntPtr h);
 [DllImport("advapi32.dll")] static extern uint SetSecurityInfo(SafeFileHandle h,int type,uint info,IntPtr owner,IntPtr group,IntPtr dacl,IntPtr sacl);
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool GetSecurityDescriptorOwner(IntPtr sd,out IntPtr owner,out bool def);
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool GetSecurityDescriptorDacl(IntPtr sd,out bool present,out IntPtr dacl,out bool def);
 [DllImport("advapi32.dll")] static extern uint GetSecurityInfo(SafeFileHandle h,int type,uint info,out IntPtr owner,out IntPtr group,out IntPtr dacl,out IntPtr sacl,out IntPtr sd);
 [DllImport("advapi32.dll")] static extern uint GetSecurityDescriptorLength(IntPtr sd);
 [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr p);
 [StructLayout(LayoutKind.Sequential)] struct ATTRTAG {public uint Attributes;public uint Tag;}
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetFileInformationByHandleEx(SafeFileHandle h,int cls,out ATTRTAG info,uint size);
 public static void SetAcl(string path,string sddl) {
  var sd=new RawSecurityDescriptor(sddl);byte[] bytes=new byte[sd.BinaryLength];sd.GetBinaryForm(bytes,0);
  GCHandle pin=GCHandle.Alloc(bytes,GCHandleType.Pinned);
  try {IntPtr owner,dacl;bool a,b;
   if(!GetSecurityDescriptorOwner(pin.AddrOfPinnedObject(),out owner,out a)||!GetSecurityDescriptorDacl(pin.AddrOfPinnedObject(),out a,out dacl,out b))throw new Win32Exception();
   using(var h=CreateFile(path,0xE0080,7,IntPtr.Zero,3,0x02200000,IntPtr.Zero)) {
    if(h.IsInvalid)throw new Win32Exception();ATTRTAG tag;if(!GetFileInformationByHandleEx(h,9,out tag,8))throw new Win32Exception();
    if((tag.Attributes&0x400)!=0)throw new InvalidOperationException("setup_reparse_not_allowed");
    uint e=SetSecurityInfo(h,1,0x80000005,owner,IntPtr.Zero,dacl,IntPtr.Zero);if(e!=0)throw new Win32Exception((int)e);
   }
  }finally{pin.Free();}
 }
 public static byte[] ReadPrepared(string path,string sid) {
  List<SafeFileHandle> parents=new List<SafeFileHandle>();
  try {
   string parent=Path.GetDirectoryName(path);
   while(!String.IsNullOrEmpty(parent)) {
    SafeFileHandle ph=CreateFile(parent,0x81,1,IntPtr.Zero,3,0x02200000,IntPtr.Zero);
    if(ph.IsInvalid){ph.Dispose();throw new Win32Exception();}
    parents.Add(ph);ATTRTAG pt;if(!GetFileInformationByHandleEx(ph,9,out pt,8))throw new Win32Exception();
    if((pt.Attributes&0x400)!=0)throw new InvalidOperationException("setup_reparse_not_allowed");
    parent=Path.GetDirectoryName(parent);
   }
   using(SafeFileHandle h=CreateFile(path,0x20081,1,IntPtr.Zero,3,0x02200000,IntPtr.Zero)) {
    if(h.IsInvalid)throw new Win32Exception();ATTRTAG tag;if(!GetFileInformationByHandleEx(h,9,out tag,8))throw new Win32Exception();
    if((tag.Attributes&0x410)!=0)throw new InvalidOperationException("setup_prepared_file_not_regular");
    IntPtr owner,group,dacl,sacl,sd;uint e=GetSecurityInfo(h,1,5,out owner,out group,out dacl,out sacl,out sd);
    if(e!=0)throw new Win32Exception((int)e);
    try {
     uint length=GetSecurityDescriptorLength(sd);if(length==0||length>65536)throw new InvalidOperationException("setup_prepared_acl_invalid");
     byte[] raw=new byte[length];Marshal.Copy(sd,raw,0,raw.Length);RawSecurityDescriptor descriptor=new RawSecurityDescriptor(raw,0);
     if(descriptor.Owner==null || (descriptor.Owner.Value!=sid && descriptor.Owner.Value!="S-1-5-18") || descriptor.DiscretionaryAcl==null || descriptor.DiscretionaryAcl.Count==0)throw new InvalidOperationException("setup_prepared_acl_invalid");
     foreach(GenericAce ace in descriptor.DiscretionaryAcl) {
      CommonAce ca=ace as CommonAce;
      if(ca==null || ca.IsCallback || ca.AceQualifier!=AceQualifier.AccessAllowed || (ca.SecurityIdentifier.Value!=sid && ca.SecurityIdentifier.Value!="S-1-5-18"))throw new InvalidOperationException("setup_prepared_acl_invalid");
     }
    }finally{LocalFree(sd);}
    using(FileStream stream=new FileStream(h,FileAccess.Read)) {
     long length=stream.Length;if(length<=0||length>1048576)throw new InvalidOperationException("setup_prepared_file_size_invalid");
     byte[] bytes=new byte[(int)length];int read=0;while(read<bytes.Length){int n=stream.Read(bytes,read,bytes.Length-read);if(n<=0)throw new EndOfStreamException();read+=n;}
     if(stream.ReadByte()!=-1)throw new InvalidOperationException("setup_prepared_file_changed");return bytes;
    }
   }
  } finally {foreach(SafeFileHandle ph in parents)ph.Dispose();}
 }
 [StructLayout(LayoutKind.Sequential)] struct OA {public uint Length;public IntPtr Root;public IntPtr Name;public uint Attr;public IntPtr SD;public IntPtr SQ;}
 [StructLayout(LayoutKind.Sequential)] struct US {public ushort Length;public ushort Maximum;public IntPtr Buffer;}
 [DllImport("advapi32.dll")] static extern uint LsaOpenPolicy(IntPtr system,ref OA oa,uint rights,out IntPtr policy);
 [DllImport("advapi32.dll")] static extern uint LsaAddAccountRights(IntPtr policy,byte[] sid,US[] rights,uint count);
 [DllImport("advapi32.dll")] static extern uint LsaClose(IntPtr policy);
 [DllImport("advapi32.dll")] static extern uint LsaNtStatusToWinError(uint status);
 public static void Grant(byte[] sid) {
  OA oa=new OA();oa.Length=(uint)Marshal.SizeOf(typeof(OA));IntPtr policy;
  uint e=LsaOpenPolicy(IntPtr.Zero,ref oa,0x810,out policy);if(e!=0)throw new Win32Exception((int)LsaNtStatusToWinError(e));
  US[] rights=new US[2];string[] names={"SeServiceLogonRight","SeBatchLogonRight"};
  try {for(int i=0;i<2;i++){rights[i].Buffer=Marshal.StringToHGlobalUni(names[i]);rights[i].Length=(ushort)(names[i].Length*2);rights[i].Maximum=(ushort)(rights[i].Length+2);}
   e=LsaAddAccountRights(policy,sid,rights,2);if(e!=0)throw new Win32Exception((int)LsaNtStatusToWinError(e));
  }finally{foreach(var r in rights)if(r.Buffer!=IntPtr.Zero)Marshal.FreeHGlobal(r.Buffer);LsaClose(policy);}
 }
}
'@
}
function Assert-SetupPath {
    param([string]$Path,[string]$Leaf,[switch]$NativeHandleWalk)
    if ($Path -notmatch ('^C:\\ProgramData\\RackClick\\Instances\\[0-9a-fA-F-]{36}\\'+[regex]::Escape($Leaf)+'$')) { throw 'setup_path_not_allowed' }
    $id = $Path.Split('\')[4]; $parsed=[guid]::Empty
    if (-not [guid]::TryParseExact($id,'D',[ref]$parsed)) { throw 'setup_path_not_allowed' }
    if($NativeHandleWalk){return}
    $cursor=$Path
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            if (((Get-Item -LiteralPath $cursor -Force -ErrorAction Stop).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'setup_reparse_not_allowed' }
        }
        $cursor=[IO.Path]::GetDirectoryName($cursor)
    }
}
function Invoke-SetupSecurityPrivileges {
    param([scriptblock]$Action)
    Assert-SetupAdministrator; Initialize-SetupSecurityNative
    $backup=$null;$restore=$null
    try {
        $backup=[RackClickSetupSecurityNative]::Privilege('SeBackupPrivilege',2)
        $restore=[RackClickSetupSecurityNative]::Privilege('SeRestorePrivilege',2)
        & $Action
    } finally {
        if ($null -ne $restore) { $null=[RackClickSetupSecurityNative]::Privilege('SeRestorePrivilege',$restore) }
        if ($null -ne $backup) { $null=[RackClickSetupSecurityNative]::Privilege('SeBackupPrivilege',$backup) }
    }
}
function New-SetupManagementDirectory {
    param([string]$Path)
    Assert-SetupAdministrator; Assert-SetupPath $Path 'management'
    if (Test-Path -LiteralPath $Path) { throw 'setup_destination_exists' }
    if (-not [IO.Directory]::Exists([IO.Path]::GetDirectoryName($Path))) { throw 'setup_parent_missing' }
    $acl=New-Object Security.AccessControl.DirectorySecurity
    $acl.SetSecurityDescriptorSddlForm('O:BAG:SYD:P(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)')
    $null=[IO.Directory]::CreateDirectory($Path,$acl)
}
function Assert-SetupMutablePaths {
    param([string[]]$DirectoryPaths=@(),[string[]]$FilePaths=@())
    $allowedDirs=@('deployment\instance\pgdata','deployment\instance\logs','runtime\control','runtime\logs','runtime\temp','runtime\backups')
    $allowedFiles=@('deployment\instance\instance.lock')
    foreach ($p in $DirectoryPaths) { if ($p -cnotin $allowedDirs) { throw 'setup_mutable_path_not_allowed' } }
    foreach ($p in $FilePaths) { if ($p -cnotin $allowedFiles) { throw 'setup_mutable_path_not_allowed' } }
}
function Assert-SetupPreparedRelativePath {
    param([string]$RelativePath)
    if($RelativePath -cnotin @('runtime/server-profile.json','runtime/RootCA.cer','deployment/instance/private/admin-login.json','runtime/control/latest-backup.json')){throw 'setup_prepared_path_not_allowed'}
}
function Read-SetupPreparedFile {
    param([string]$InstancePath,[string]$RelativePath,[string]$ServiceSid)
    Assert-SetupAdministrator
    Assert-SetupPath $InstancePath 'instance' -NativeHandleWalk
    Assert-SetupPreparedRelativePath $RelativePath
    $sid=New-Object Security.Principal.SecurityIdentifier($ServiceSid)
    if($sid.Value-notmatch '^S-1-5-21-(\d+-){3}\d+$' -or $sid.Value.EndsWith('-500')){throw 'setup_service_sid_not_allowed'}
    $path=Join-Path $InstancePath $RelativePath.Replace('/', '\')
    $bytes=Invoke-SetupSecurityPrivileges {,[RackClickSetupSecurityNative]::ReadPrepared($path,$sid.Value)}
    return ,([byte[]]$bytes)
}
function Set-SetupServiceTreeSecurity {
    param([string]$Path,[string]$ServiceSid,[string[]]$MutableDirectoryPaths=@(),[string[]]$MutableFilePaths=@())
    Assert-SetupAdministrator; Assert-SetupPath $Path 'instance'
    $sid=New-Object Security.Principal.SecurityIdentifier($ServiceSid)
    if ($sid.Value -notmatch '^S-1-5-21-(\d+-){3}\d+$' -or $sid.Value.EndsWith('-500')) { throw 'setup_service_sid_not_allowed' }
    Assert-SetupMutablePaths $MutableDirectoryPaths $MutableFilePaths
    if (-not [IO.Directory]::Exists($Path)) { throw 'setup_instance_missing' }
    Invoke-SetupSecurityPrivileges {
        function Set-SetupTreeNode([string]$Node,[bool]$Mutable) {
            $relative=$Node.Substring($Path.Length).TrimStart('\')
            $isMutable=$Mutable -or $relative -cin $MutableDirectoryPaths
            $isLock=$relative -cin $MutableFilePaths
            $temporary='O:SYG:SYD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)'
            [RackClickSetupSecurityNative]::SetAcl($Node,$temporary)
            try {
                $item=Get-Item -LiteralPath $Node -Force -ErrorAction Stop
                if ($item.PSIsContainer) {
                    foreach ($child in @(Get-ChildItem -LiteralPath $Node -Force -ErrorAction Stop)) { Set-SetupTreeNode $child.FullName $isMutable }
                }
            } finally {
                $access=if($isMutable){'FA'}elseif($isLock){'0x12019f'}else{'FRFX'}
                $flags=if($item.PSIsContainer){'OICI'}else{''}
                [RackClickSetupSecurityNative]::SetAcl($Node,('O:SYG:SYD:P(A;'+$flags+';FA;;;SY)(A;'+$flags+';'+$access+';;;'+$sid.Value+')'))
            }
        }
        Set-SetupTreeNode $Path $false
    }
}
function Grant-SetupServiceLogonRights {
    param([string]$ServiceSid)
    Assert-SetupAdministrator; Initialize-SetupSecurityNative
    $sid=New-Object Security.Principal.SecurityIdentifier($ServiceSid)
    if ($sid.Value -notmatch '^S-1-5-21-(\d+-){3}\d+$' -or $sid.Value.EndsWith('-500')) { throw 'setup_service_sid_not_allowed' }
    $bytes=New-Object byte[] $sid.BinaryLength;$sid.GetBinaryForm($bytes,0)
    [RackClickSetupSecurityNative]::Grant($bytes)
}
function Save-SetupServiceCredential {
    param([Management.Automation.PSCredential]$Credential,[string]$ManagementPath)
    Assert-SetupAdministrator; Assert-SetupPath $ManagementPath 'management'
    Assert-SetupManagementAcl $ManagementPath
    Add-Type -AssemblyName System.Security
    $plain=$null;$pointer=[IntPtr]::Zero
    try {
        $pointer=[Runtime.InteropServices.Marshal]::SecureStringToGlobalAllocUnicode($Credential.Password)
        $plain=New-Object byte[] ($Credential.Password.Length*2)
        [Runtime.InteropServices.Marshal]::Copy($pointer,$plain,0,$plain.Length)
        $encrypted=[Security.Cryptography.ProtectedData]::Protect($plain,$null,[Security.Cryptography.DataProtectionScope]::LocalMachine)
        $record=@{schemaVersion=1;user=$Credential.UserName;password=[Convert]::ToBase64String($encrypted)}|ConvertTo-Json -Compress
        $stream=[IO.File]::Open((Join-Path $ManagementPath 'service-credential.dpapi.json'),'CreateNew','Write','None')
        try {$data=[Text.Encoding]::UTF8.GetBytes($record);$stream.Write($data,0,$data.Length);$stream.Flush($true)}finally{$stream.Dispose()}
    } finally {
        if ($null -ne $plain) {[Array]::Clear($plain,0,$plain.Length)}
        if ($pointer -ne [IntPtr]::Zero) {[Runtime.InteropServices.Marshal]::ZeroFreeGlobalAllocUnicode($pointer)}
    }
}
function Read-SetupServiceCredential {
    param([string]$ManagementPath)
    Assert-SetupAdministrator; Assert-SetupPath $ManagementPath 'management'
    Assert-SetupManagementAcl $ManagementPath
    Add-Type -AssemblyName System.Security
    $path=Join-Path $ManagementPath 'service-credential.dpapi.json'
    if (((Get-Item -LiteralPath $path -Force -ErrorAction Stop).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {throw 'setup_reparse_not_allowed'}
    Assert-SetupManagementAcl $path
    $record=[IO.File]::ReadAllText($path)|ConvertFrom-Json
    $plain=[Security.Cryptography.ProtectedData]::Unprotect([Convert]::FromBase64String($record.password),$null,[Security.Cryptography.DataProtectionScope]::LocalMachine)
    try {
        if ($plain.Length % 2) {throw 'setup_credential_invalid'}
        $secure=New-Object Security.SecureString
        for($i=0;$i -lt $plain.Length;$i+=2){$secure.AppendChar([char]([int]$plain[$i]+256*[int]$plain[$i+1]))}
        $secure.MakeReadOnly()
        return New-Object Management.Automation.PSCredential($record.user,$secure)
    } finally {[Array]::Clear($plain,0,$plain.Length)}
}
function Assert-SetupManagementAcl {
    param([string]$Path)
    $acl=Get-Acl -LiteralPath $Path -ErrorAction Stop
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin @('S-1-5-18','S-1-5-32-544',[Security.Principal.WindowsIdentity]::GetCurrent().User.Value)) {throw 'setup_management_acl_invalid'}
    foreach($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
        if ($rule.IdentityReference.Value -notin @('S-1-5-18','S-1-5-32-544') -or $rule.AccessControlType -ne 'Allow') {throw 'setup_management_acl_invalid'}
    }
    if ($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]).Count -lt 2) {throw 'setup_management_acl_invalid'}
}
function Initialize-SetupCommonDirectories {
    # Create ancestors separately: a per-instance SID must never own the shared hub.
    Assert-SetupAdministrator
    foreach($path in @('C:\ProgramData\RackClick','C:\ProgramData\RackClick\Instances','C:\Program Files\RackClick')) {
        Assert-SetupNoReparse $path
        if(-not(Test-Path -LiteralPath $path)) {
            $acl=New-Object Security.AccessControl.DirectorySecurity
            $acl.SetSecurityDescriptorSddlForm('O:BAG:SYD:P(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)(A;;FRFX;;;BU)')
            $null=[IO.Directory]::CreateDirectory($path,$acl)
        } elseif(-not[IO.Directory]::Exists($path)) {throw 'setup_common_directory_invalid'}
    }
}
function New-SetupInstanceParent {
    param([string]$Path,[string]$ServiceSid,[switch]$AllowCreate)
    Assert-SetupAdministrator
    Assert-SetupPath ($Path+'\instance') 'instance'
    $sid=New-Object Security.Principal.SecurityIdentifier($ServiceSid)
    if ($sid.Value -notmatch '^S-1-5-21-(\d+-){3}\d+$' -or $sid.Value.EndsWith('-500')) {throw 'setup_service_sid_not_allowed'}
    $access=if($AllowCreate){'0x1200ad'}else{'FRFX'}
    $acl=New-Object Security.AccessControl.DirectorySecurity
    $acl.SetSecurityDescriptorSddlForm(('O:BAG:SYD:P(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)(A;;'+$access+';;;'+$sid.Value+')'))
    if ($AllowCreate) {
        Initialize-SetupCommonDirectories
        if (Test-Path -LiteralPath $Path) {throw 'setup_destination_exists'}
        $null=[IO.Directory]::CreateDirectory($Path,$acl)
    } else {
        if (-not [IO.Directory]::Exists($Path)) {throw 'setup_parent_missing'}
        Set-Acl -LiteralPath $Path -AclObject $acl -ErrorAction Stop
    }
}
function Set-SetupPublicCodeDirectoryACL {
    param([string]$Path,[string]$ServiceSid)
    Assert-SetupAdministrator
    if ($Path -notmatch '^C:\\Program Files\\RackClick\\[0-9a-fA-F-]{36}$') {throw 'setup_path_not_allowed'}
    $parsed=[guid]::Empty
    if(-not [guid]::TryParseExact([IO.Path]::GetFileName($Path),'D',[ref]$parsed)){throw 'setup_path_not_allowed'}
    $cursor=$Path
    while($cursor){if(Test-Path -LiteralPath $cursor){if(((Get-Item -LiteralPath $cursor -Force).Attributes-band[IO.FileAttributes]::ReparsePoint)-ne 0){throw 'setup_reparse_not_allowed'}};$cursor=[IO.Path]::GetDirectoryName($cursor)}
    $sid=New-Object Security.Principal.SecurityIdentifier($ServiceSid)
    if ($sid.Value -notmatch '^S-1-5-21-(\d+-){3}\d+$' -or $sid.Value.EndsWith('-500')) {throw 'setup_service_sid_not_allowed'}
    if(Test-Path -LiteralPath $Path){throw 'setup_destination_exists'}
    Initialize-SetupCommonDirectories
    $acl=New-Object Security.AccessControl.DirectorySecurity
    $acl.SetSecurityDescriptorSddlForm(('O:BAG:SYD:P(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)(A;OICI;FRFX;;;'+$sid.Value+')'))
    $null=[IO.Directory]::CreateDirectory($Path,$acl)
}
