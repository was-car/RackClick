#requires -Version 5.1
# Read-only private service diagnostics. Import only defines functions. The public
# entry point derives every path from a canonical installation GUID and trusted SID.
function Initialize-SetupServiceDiagnosticNative {
    if ('RackClickSetupServiceDiagnosticNative' -as [type]) { return }
    Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.ComponentModel;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using Microsoft.Win32.SafeHandles;
public sealed class RackClickSetupDiagnosticMetadata {
 public long Length;
 public DateTime LastWriteUtc;
}
public static class RackClickSetupServiceDiagnosticNative {
 [StructLayout(LayoutKind.Sequential)] struct AttrTag {public uint Attributes;public uint Tag;}
 [StructLayout(LayoutKind.Sequential)] struct BasicInfo {public long Creation,Access,Write,Change;public uint Attributes;}
 [StructLayout(LayoutKind.Sequential)] struct IoStatus {public IntPtr Status;public UIntPtr Information;}
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern SafeFileHandle CreateFile(string p,uint a,uint s,IntPtr sa,uint c,uint f,IntPtr template);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetFileInformationByHandleEx(SafeFileHandle h,int cls,out AttrTag info,uint size);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetFileInformationByHandleEx(SafeFileHandle h,int cls,out BasicInfo info,uint size);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetFileSizeEx(SafeFileHandle h,out long size);
 [DllImport("advapi32.dll")] static extern uint GetSecurityInfo(SafeFileHandle h,int type,uint info,out IntPtr owner,out IntPtr group,out IntPtr dacl,out IntPtr sacl,out IntPtr sd);
 [DllImport("advapi32.dll")] static extern uint GetSecurityDescriptorLength(IntPtr sd);
 [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr p);
 [DllImport("ntdll.dll")] static extern int NtQueryDirectoryFile(SafeFileHandle h,IntPtr ev,IntPtr apc,IntPtr context,out IoStatus io,IntPtr buffer,uint length,int cls,[MarshalAs(UnmanagedType.U1)]bool single,IntPtr filter,[MarshalAs(UnmanagedType.U1)]bool restart);
 [DllImport("ntdll.dll")] static extern uint RtlNtStatusToDosError(int status);
 static SafeFileHandle Open(string path,uint access) {
  // BACKUP_SEMANTICS | OPEN_REPARSE_POINT, no write/delete sharing. Retaining
  // these handles pins each ancestor while a leaf is enumerated/read.
  SafeFileHandle h=CreateFile(path,access,1,IntPtr.Zero,3,0x02200000,IntPtr.Zero);
  if(h.IsInvalid){int error=Marshal.GetLastWin32Error();h.Dispose();throw new Win32Exception(error);}
  return h;
 }
 static void CheckTag(SafeFileHandle h,bool directory) {
  AttrTag t;if(!GetFileInformationByHandleEx(h,9,out t,8))throw new Win32Exception();
  if((t.Attributes&0x400)!=0)throw new InvalidOperationException("service_reparse_rejected");
  if(((t.Attributes&0x10)!=0)!=directory)throw new InvalidOperationException("service_file_kind_invalid");
 }
 static List<SafeFileHandle> Parents(string path) {
  var held=new List<SafeFileHandle>();
  try {
   for(string parent=Path.GetDirectoryName(path);!String.IsNullOrEmpty(parent);parent=Path.GetDirectoryName(parent)) {
    SafeFileHandle h=Open(parent,0x80);held.Add(h);CheckTag(h,true);
   }
   return held;
  } catch {foreach(var h in held)h.Dispose();throw;}
 }
 static void CheckAcl(SafeFileHandle h,string sid) {
  IntPtr o,g,d,s,sd;uint result=GetSecurityInfo(h,1,5,out o,out g,out d,out s,out sd);
  if(result!=0)throw new Win32Exception((int)result);
  try {
   uint length=GetSecurityDescriptorLength(sd);
   if(length==0||length>65536)throw new InvalidOperationException("service_acl_rejected");
   byte[] bytes=new byte[length];Marshal.Copy(sd,bytes,0,bytes.Length);
   var descriptor=new RawSecurityDescriptor(bytes,0);
   if(descriptor.Owner==null||(descriptor.Owner.Value!=sid&&descriptor.Owner.Value!="S-1-5-18")||descriptor.DiscretionaryAcl==null||descriptor.DiscretionaryAcl.Count==0)throw new InvalidOperationException("service_acl_rejected");
   foreach(GenericAce ace in descriptor.DiscretionaryAcl) {
    CommonAce ca=ace as CommonAce;
    if(ca==null||ca.IsCallback||ca.AceQualifier!=AceQualifier.AccessAllowed||(ca.SecurityIdentifier.Value!=sid&&ca.SecurityIdentifier.Value!="S-1-5-18"))throw new InvalidOperationException("service_acl_rejected");
   }
  } finally {LocalFree(sd);}
 }
 public static string[] NativeEnumeratePrivateDirectory(string path,string sid) {
  var held=Parents(path);
  try {using(SafeFileHandle h=Open(path,0x20081)) {
   CheckTag(h,true);CheckAcl(h,sid);
   IntPtr buffer=Marshal.AllocHGlobal(65536);
   try {
    var names=new List<string>();int scanned=0,total=0;bool first=true;
    for(int call=0;call<64;call++) {
     IoStatus io;int status=NtQueryDirectoryFile(h,IntPtr.Zero,IntPtr.Zero,IntPtr.Zero,out io,buffer,65536,12,false,IntPtr.Zero,first);first=false;
     if(status==unchecked((int)0x80000006))return names.ToArray();
     if(status!=0)throw new Win32Exception((int)RtlNtStatusToDosError(status));
     ulong used=io.Information.ToUInt64();
     if(used==0||used>65536)throw new InvalidOperationException("service_directory_invalid");
     total+=(int)used;if(total>1048576)throw new InvalidOperationException("service_directory_limit");
     int offset=0;
     while(true) {
      if(offset>(int)used-12)throw new InvalidOperationException("service_directory_invalid");
      int next=Marshal.ReadInt32(buffer,offset),length=Marshal.ReadInt32(buffer,offset+8);
      if(length<=0||length>510||(length&1)!=0||length>(int)used-offset-12)throw new InvalidOperationException("service_directory_invalid");
      if(++scanned>2048)throw new InvalidOperationException("service_directory_limit");
      string name=Marshal.PtrToStringUni(IntPtr.Add(buffer,offset+12),length/2);
      // Unknown names never become paths until the PowerShell allowlist matches.
      if(name!="."&&name!="..")names.Add(name);
      if(next==0)break;
      if(next<12+length||(next&3)!=0||next>(int)used-offset-12)throw new InvalidOperationException("service_directory_invalid");
      offset+=next;
     }
    }
    throw new InvalidOperationException("service_directory_limit");
   } finally {Marshal.FreeHGlobal(buffer);}
  }} finally {foreach(var h in held)h.Dispose();}
 }
 public static RackClickSetupDiagnosticMetadata GetPrivateFileMetadata(string path,string sid) {
  var held=Parents(path);
  try {using(SafeFileHandle h=Open(path,0x20080)) {
   CheckTag(h,false);CheckAcl(h,sid);BasicInfo basic;long length;
   if(!GetFileInformationByHandleEx(h,0,out basic,(uint)Marshal.SizeOf(typeof(BasicInfo)))||!GetFileSizeEx(h,out length))throw new Win32Exception();
   return new RackClickSetupDiagnosticMetadata {Length=length,LastWriteUtc=DateTime.FromFileTimeUtc(basic.Write)};
  }} finally {foreach(var h in held)h.Dispose();}
 }
}
'@
}
function Get-SetupServiceDiagnosticFailure($ErrorRecord) {
    $exception=$ErrorRecord.Exception
    for($i=0;$i-lt8-and$null-ne$exception.InnerException;$i++){$exception=$exception.InnerException}
    $safe=[ordered]@{errorType=$exception.GetType().FullName;errorHResult=$exception.HResult;code='service_diagnostic_unavailable'}
    if($exception-is[ComponentModel.Win32Exception]){$safe.nativeErrorCode=$exception.NativeErrorCode}
    if($exception.Message-cin@('service_reparse_rejected','service_file_kind_invalid','service_acl_rejected','service_directory_limit','service_directory_invalid','service_utf8_invalid','service_json_invalid','service_line_limit','service_record_invalid','service_postmaster_invalid','service_relative_path_invalid','service_root_invalid','service_instance_id_invalid','service_sid_invalid','setup_elevated_x64_required','setup_prepared_acl_invalid','setup_prepared_file_not_regular','setup_reparse_not_allowed','setup_prepared_file_size_invalid','setup_prepared_file_changed')){$safe.code=$exception.Message}
    return $safe
}
function ConvertTo-SetupServiceUtc($Value) {
    if($Value-isnot[string]-or$Value.Length-gt48-or$Value-cnotmatch'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,7})?(Z|[+-]\d{2}:\d{2})$'){return $null}
    $parsed=[DateTimeOffset]::MinValue
    if(-not[DateTimeOffset]::TryParse($Value,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::None,[ref]$parsed)){return $null}
    return $parsed.UtcDateTime.ToString('o',[Globalization.CultureInfo]::InvariantCulture)
}
function Test-SetupServiceRunId($Value) {
    return ($Value-is[string]-and$Value-cmatch'\A[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\z')
}
function Get-SetupServiceKnownRuntimeCodes {
    # Finite source-reviewed vocabulary from Invoke-RackClickServerRuntime,
    # ServerRuntime and LaunchControl. Never learn codes from private files or
    # accept a token merely because its spelling resembles a machine code.
    return @(
        'starting','ready','stopped','instance_stopped','launcher_failed',
        'stop_after_invalid','instance_in_use','instance_lock_unavailable',
        'launcher_port_in_use','launcher_runtime_unavailable','launcher_runtime_invalid',
        'launcher_postgres_tool_missing','launcher_postgres_tool_architecture','launcher_postgres_tool_version',
        'postgres_start_failed','postgres_readiness_timeout','postgres_pid_file_exists',
        'application_start_failed','application_readiness_timeout','owned_process_ended',
        'application_graceful_stop_failed','postgres_ownership_unverified','postgres_clean_stop_failed',
        'owned_shutdown_failed','owned_stop_indeterminate','run_state_write_failed',
        'stop_request_invalid','launcher_environment_restore_failed',
        'application_control_owner_invalid','application_control_timeout','application_control_ack_invalid',
        'application_ended_before_control','application_graceful_stop_timeout','application_graceful_exit_failed',
        'server_active_run_changed','server_run_not_stoppable','server_stop_request_invalid',
        'server_stop_failed','server_stop_timeout','server_backup_paths_overlap','server_backup_failed','server_operation_failed',
        'server_origin_invalid','server_bind_invalid','server_bind_not_local','server_public_bind_mismatch','server_dns_bind_mismatch',
        'server_certificate_invalid','server_certificate_key_invalid','server_certificate_extensions_invalid',
        'server_certificate_san_mismatch','server_certificate_manifest_invalid','server_certificate_file_hash_mismatch',
        'server_public_certificate_mismatch','server_certificate_chain_invalid','server_certificate_binding_invalid',
        'server_manifest_reference_required','server_manifest_hash_mismatch','server_manifest_invalid','server_manifest_binding_invalid',
        'server_installation_hash_mismatch','server_installation_not_prepared','server_deployment_binding_invalid'
    )
}
function Read-SetupServiceDiagnosticLeaf([string]$Root,[string]$Relative,[string]$ServiceSid) {
    if($Relative-cnotmatch'\A(?:runtime/logs/host-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\.jsonl|runtime/control/active-run\.json|runtime/control/launcher-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/(?:run-state\.json|launcher-error\.log)|deployment/instance/pgdata/postmaster\.pid)\z'){throw 'service_relative_path_invalid'}
    return ,[RackClickSetupSecurityNative]::ReadPrepared((Join-Path $Root $Relative.Replace('/','\')),$ServiceSid)
}
function ConvertFrom-SetupServiceDiagnosticUtf8([byte[]]$Bytes) {
    if($Bytes.Length-gt1048576){throw 'setup_prepared_file_size_invalid'}
    try{$decoded=(New-Object Text.UTF8Encoding($false,$true)).GetString($Bytes)}catch{throw 'service_utf8_invalid'}
    if($decoded.Length-gt0-and$decoded[0]-eq[char]0xFEFF){$decoded=$decoded.Substring(1)}
    return $decoded
}
function Get-SetupServiceRunObservation([string]$Root,[string]$Relative,[string]$ServiceSid,[string]$ExpectedRunId='') {
    try {
        $bytes=Read-SetupServiceDiagnosticLeaf $Root $Relative $ServiceSid
        try{$value=(ConvertFrom-SetupServiceDiagnosticUtf8 $bytes)|ConvertFrom-Json -ErrorAction Stop}catch{throw 'service_json_invalid'}
        if($value-isnot[pscustomobject]){throw 'service_record_invalid'}
        $run=$value.PSObject.Properties['runId'];$state=$value.PSObject.Properties['status'];$code=$value.PSObject.Properties['code'];$utc=$value.PSObject.Properties['utc'];$schema=$value.PSObject.Properties['schemaVersion']
        if($null-eq$run-or-not(Test-SetupServiceRunId $run.Value)-or($ExpectedRunId-and$run.Value-cne$ExpectedRunId)-or$null-eq$schema-or$schema.Value-isnot[int]-or$schema.Value-ne1-or$null-eq$state-or$state.Value-cnotin@('starting','ready','stopped','failed')-or$null-eq$code-or$code.Value-isnot[string]-or$code.Value-cnotin@(Get-SetupServiceKnownRuntimeCodes)-or$null-eq$utc){throw 'service_record_invalid'}
        $time=ConvertTo-SetupServiceUtc $utc.Value;if($null-eq$time){throw 'service_record_invalid'}
        return [ordered]@{status='parsed';fields=[ordered]@{schemaVersion=1;runId=$run.Value;state=$state.Value;code=$code.Value;utc=$time}}
    } catch {return [ordered]@{status='unavailable';failure=(Get-SetupServiceDiagnosticFailure $_)}}
}
function Get-SetupServiceHostObservation([string]$Root,[string]$RunId,[string]$ServiceSid) {
    try {
        $bytes=Read-SetupServiceDiagnosticLeaf $Root ('runtime/logs/host-'+$RunId+'.jsonl') $ServiceSid
        $text=ConvertFrom-SetupServiceDiagnosticUtf8 $bytes
        $lines=$text.Split([char]10);$count=$lines.Length
        if($count-gt0-and$lines[$count-1].Length-eq0){$count--}
        if($count-gt1000){throw 'service_line_limit'}
        $records=New-Object Collections.Generic.List[object];$invalid=0
        for($i=0;$i-lt$count;$i++) {
            try {
                $value=$lines[$i]|ConvertFrom-Json -ErrorAction Stop
                if($value-isnot[pscustomobject]){throw 'service_record_invalid'}
                $run=$value.PSObject.Properties['runId'];$code=$value.PSObject.Properties['code'];$stamp=$value.PSObject.Properties['timestamp'];$exit=$value.PSObject.Properties['exitCode']
                if($null-eq$run-or$run.Value-cne$RunId-or$null-eq$code-or$code.Value-cnotin@('start_requested','runtime_started','runtime_unexpected_exit','start_failed','stop_requested','runtime_stopped','stop_failed')-or$null-eq$stamp){throw 'service_record_invalid'}
                $time=ConvertTo-SetupServiceUtc $stamp.Value;if($null-eq$time){throw 'service_record_invalid'}
                $record=[ordered]@{timestamp=$time;code=$code.Value;runId=$RunId}
                if($null-ne$exit-and$null-ne$exit.Value){if(($exit.Value-isnot[int]-and$exit.Value-isnot[long])-or$exit.Value-lt[int]::MinValue-or$exit.Value-gt[int]::MaxValue){throw 'service_record_invalid'};$record.exitCode=[int]$exit.Value}
                $records.Add($record)
            } catch {$invalid++}
        }
        if($records.Count-eq0){throw 'service_record_invalid'}
        return [ordered]@{status='parsed';runId=$RunId;bytes=$bytes.Length;lineCount=$count;invalidLineCount=$invalid;records=@($records.ToArray())}
    } catch {return [ordered]@{status='unavailable';runId=$RunId;failure=(Get-SetupServiceDiagnosticFailure $_)}}
}
function Get-SetupServiceLauncherErrorObservation([string]$Root,[string]$RunId,[string]$ServiceSid) {
    try {
        $text=ConvertFrom-SetupServiceDiagnosticUtf8 (Read-SetupServiceDiagnosticLeaf $Root ('runtime/control/launcher-'+$RunId+'/launcher-error.log') $ServiceSid)
        $fields=[ordered]@{}
        $match=[regex]::Match($text,'\A(?:System\.(?:InvalidOperationException|ArgumentException|UnauthorizedAccessException|IO\.(?:IOException|FileNotFoundException|DirectoryNotFoundException)|ComponentModel\.Win32Exception|Management\.Automation\.(?:RuntimeException|MethodInvocationException|CommandNotFoundException|ActionPreferenceStopException)))(?=:)')
        if($match.Success){$fields.errorType=$match.Value}
        # Runtime-owned error codes only. Never recover arbitrary words, full
        # messages, stack frames, paths or serialized exception.Data.
        $known=(@(Get-SetupServiceKnownRuntimeCodes|Where-Object {$_-cnotin@('starting','ready','stopped')}|ForEach-Object {[regex]::Escape($_)}))-join'|'
        $match=[regex]::Match($text,'(?<![A-Za-z0-9_])(?:'+$known+')(?![A-Za-z0-9_])')
        if($match.Success){$fields.code=$match.Value}
        return [ordered]@{status='summarized';fields=$fields}
    } catch {return [ordered]@{status='unavailable';failure=(Get-SetupServiceDiagnosticFailure $_)}}
}
function Get-SetupServicePostmasterObservation([string]$Root,[string]$ServiceSid) {
    try {
        $text=ConvertFrom-SetupServiceDiagnosticUtf8 (Read-SetupServiceDiagnosticLeaf $Root 'deployment/instance/pgdata/postmaster.pid' $ServiceSid)
        $lines=$text.Split([char]10)
        if($lines.Length-lt8-or$lines.Length-gt10){throw 'service_postmaster_invalid'}
        $process=0;$port=0;$epoch=[long]0
        if($lines[0].Trim()-cnotmatch'\A[1-9][0-9]{0,9}\z'-or-not[int]::TryParse($lines[0].Trim(),[ref]$process)-or$lines[2].Trim()-cnotmatch'\A[1-9][0-9]{0,10}\z'-or-not[long]::TryParse($lines[2].Trim(),[ref]$epoch)-or$epoch-gt253402300799-or$lines[3].Trim()-cnotmatch'\A[1-9][0-9]{0,4}\z'-or-not[int]::TryParse($lines[3].Trim(),[ref]$port)-or$port-gt65535-or$lines[7].Trim()-cnotin@('starting','stopping','ready','standby')){throw 'service_postmaster_invalid'}
        $start=[DateTimeOffset]::FromUnixTimeSeconds($epoch).UtcDateTime.ToString('o',[Globalization.CultureInfo]::InvariantCulture)
        return [ordered]@{status='parsed';fields=[ordered]@{processId=$process;port=$port;state=$lines[7].Trim();startedUtc=$start};processLivenessVerified=$false}
    } catch {return [ordered]@{status='unavailable';failure=(Get-SetupServiceDiagnosticFailure $_)}}
}
function Get-SetupServicePrivateDiagnosticAtRoot([string]$Root,[string]$ServiceSid) {
    # Internal fixture seam; no privilege activation. Leaf paths still pass the
    # same fixed allowlist and native no-reparse/SID/SYSTEM validation.
    $result=[ordered]@{status='observed';hostDirectory=[ordered]@{status='unavailable'};hostLogs=@();activeRun=[ordered]@{status='unavailable'};launcherRuns=@();postmaster=[ordered]@{status='unavailable'}}
    try {
        if(-not[IO.Path]::IsPathRooted($Root)-or$Root.StartsWith('\\')-or$Root.IndexOf(':',2)-ge0-or[IO.Path]::GetFullPath($Root).TrimEnd('\')-cne$Root.TrimEnd('\')){throw 'service_root_invalid'}
        Initialize-SetupSecurityNative;Initialize-SetupServiceDiagnosticNative
        $runs=New-Object Collections.Generic.List[string]
        $result.activeRun=Get-SetupServiceRunObservation $Root 'runtime/control/active-run.json' $ServiceSid
        if($result.activeRun.status-ceq'parsed'){$runs.Add($result.activeRun.fields.runId)}
        try {
            $names=[RackClickSetupServiceDiagnosticNative]::NativeEnumeratePrivateDirectory((Join-Path $Root 'runtime\logs'),$ServiceSid)
            $candidates=New-Object Collections.Generic.List[object];$rejected=0
            foreach($name in $names) {
                if($name-cnotmatch'\Ahost-([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\.jsonl\z'){continue}
                $run=$Matches[1]
                try {$meta=[RackClickSetupServiceDiagnosticNative]::GetPrivateFileMetadata((Join-Path (Join-Path $Root 'runtime\logs') $name),$ServiceSid);$candidates.Add([pscustomobject]@{runId=$run;lastWriteUtc=$meta.LastWriteUtc})}catch{$rejected++}
            }
            $result.hostDirectory=[ordered]@{status='enumerated';candidateCount=$candidates.Count;rejectedCandidateCount=$rejected}
            $logs=New-Object Collections.Generic.List[object]
            foreach($candidate in @($candidates|Sort-Object -Property @{Expression='lastWriteUtc';Descending=$true},@{Expression='runId';Descending=$false}|Select-Object -First 5)) {
                $logs.Add((Get-SetupServiceHostObservation $Root $candidate.runId $ServiceSid))
                if($runs.Count-lt5-and-not$runs.Contains($candidate.runId)){$runs.Add($candidate.runId)}
            }
            $result.hostLogs=@($logs.ToArray())
        } catch {$result.hostDirectory=[ordered]@{status='unavailable';failure=(Get-SetupServiceDiagnosticFailure $_)}}
        $launchers=New-Object Collections.Generic.List[object]
        foreach($run in $runs){$launchers.Add([ordered]@{runId=$run;runState=(Get-SetupServiceRunObservation $Root ('runtime/control/launcher-'+$run+'/run-state.json') $ServiceSid $run);error=(Get-SetupServiceLauncherErrorObservation $Root $run $ServiceSid)})}
        $result.launcherRuns=@($launchers.ToArray())
        $result.postmaster=Get-SetupServicePostmasterObservation $Root $ServiceSid
    } catch {$result.status='unavailable';$result.failure=Get-SetupServiceDiagnosticFailure $_}
    return $result
}
function Get-SetupServicePrivateDiagnostic([string]$InstanceId,[string]$ServiceSid) {
    $previous=$null;$result=$null
    try {
        if(-not(Test-SetupServiceRunId $InstanceId)){throw 'service_instance_id_invalid'}
        $sid=New-Object Security.Principal.SecurityIdentifier($ServiceSid)
        if($sid.Value-cnotmatch'\AS-1-5-21-(\d+-){3}\d+\z'-or$sid.Value.EndsWith('-500')){throw 'service_sid_invalid'}
        Assert-SetupAdministrator;Initialize-SetupSecurityNative;Initialize-SetupServiceDiagnosticNative
        $previous=[RackClickSetupSecurityNative]::Privilege('SeBackupPrivilege',2)
        $result=Get-SetupServicePrivateDiagnosticAtRoot ('C:\ProgramData\RackClick\Instances\'+$InstanceId+'\instance') $sid.Value
    } catch {$result=[ordered]@{status='unavailable';failure=(Get-SetupServiceDiagnosticFailure $_)}}
    finally {
        if($null-ne$previous){
            try {$null=[RackClickSetupSecurityNative]::Privilege('SeBackupPrivilege',$previous)}
            catch {$result=[ordered]@{status='unavailable';failure=(Get-SetupServiceDiagnosticFailure $_)};$result.failure.code='service_privilege_restore_failed'}
        }
    }
    return $result
}
