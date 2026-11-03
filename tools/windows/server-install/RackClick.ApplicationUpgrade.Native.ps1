#requires -Version 5.1
# Exact native helper reused from Set-RackClickInstanceNetwork.ps1; no main operation.
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
