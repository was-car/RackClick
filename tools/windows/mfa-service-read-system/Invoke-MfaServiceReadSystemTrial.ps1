#requires -Version 5.1
# One explicit SYSTEM task; actual key read remains impersonated by the pinned L2l02 probe.
[CmdletBinding()]
param(
    [ValidateSet('Check','Run','Worker','SelfTest')][string]$Mode='Check',
    [string]$ArchivePath='C:\MFA-Lectura02\RackClick-MFA-Lectura-L2l02.zip',
    [string]$ServiceName='RackClick',
    [string]$TrialRoot='',
    [string]$ExpectedScriptSha256='',
    [string]$PlanPath='',
    [string]$ExpectedPlanSha256=''
)
$ErrorActionPreference='Stop'
$ZipPin='c957e0c90d7af77cc01a08ccec4581af8d9d3410c0388656377409a4249551b2'
$SumsPin='803a8373d7c9fa8cc9d230e285f4b4e5ca0b84f222c68d10980278652f16035b'
$ReferenceScriptPin='b2058cfcf37a14e8892c4d299089327a8bbf778425e061fe93b34ea5f0ae190e'
$ReferenceFolder='RackClick-MFA-Lectura-L2l02'
$WorkPrefix='RackClick-MFA-SystemRead-'
$ProbeTimeout=90
$ParentTimeout=150
$TaskDacl='D:P(A;;FA;;;SY)(A;;FA;;;BA)'

function Fail([string]$Code) { throw ('system_trial:'+ $Code) }
function Error-Code($Record) {
    if ($Record.Exception.Message -match '^system_trial:([a-z0-9_]+)$') { return $Matches[1] }
    if ($Record.Exception.Message -match '^trial:([a-z0-9_]+)$') { return $Matches[1] }
    return 'unexpected_error'
}
function Hash-File([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Hash-Text([string]$Text) {
    $s=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($s.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text)))).Replace('-','').ToLowerInvariant() }
    finally { $s.Dispose() }
}
function Assert-NoReparse([string]$Path) {
    $item=Get-Item -LiteralPath $Path -Force
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { Fail 'reparse_point' }
        if ($item -is [IO.FileInfo]) { $item=$item.Directory } else { $item=$item.Parent }
    }
}
function Assert-PrivateRoot([string]$Path) {
    Assert-NoReparse $Path
    $acl=Get-Acl -LiteralPath $Path
    $owner=$acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
    if ($owner -notin @('S-1-5-18','S-1-5-32-544') -or -not $acl.AreAccessRulesProtected) { Fail 'workspace_acl_invalid' }
    foreach ($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
            $rule.IdentityReference.Value -notin @('S-1-5-18','S-1-5-32-544')) { Fail 'workspace_acl_invalid' }
    }
}
function New-PrivateRoot([string]$Path) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace RackClick.SystemReadTrial {
 public static class Folder {
  [StructLayout(LayoutKind.Sequential)] private struct SA { public int Length; public IntPtr Descriptor; public int Inherit; }
  [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] private static extern bool ConvertStringSecurityDescriptorToSecurityDescriptorW(string s,uint revision,out IntPtr d,out uint bytes);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] private static extern bool CreateDirectoryW(string p,ref SA a);
  [DllImport("kernel32.dll")] private static extern IntPtr LocalFree(IntPtr p);
  public static int Create(string path,string descriptor) {
   IntPtr d; uint bytes;
   if(!ConvertStringSecurityDescriptorToSecurityDescriptorW(descriptor,1,out d,out bytes))return Marshal.GetLastWin32Error();
   try { var a=new SA {Length=Marshal.SizeOf(typeof(SA)),Descriptor=d,Inherit=0}; return CreateDirectoryW(path,ref a)?0:Marshal.GetLastWin32Error(); }
   finally { LocalFree(d); }
  }
 }
}
'@
    $errorCode=[RackClick.SystemReadTrial.Folder]::Create($Path,'O:BAG:SYD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)')
    if ($errorCode -eq 183) { Fail 'workspace_exists' }
    if ($errorCode -ne 0) { Fail 'workspace_create_failed' }
    Assert-PrivateRoot $Path
}
function Write-NewJson([string]$Path,$Data) {
    # Parent has a protected inheritable DACL before this exclusive file creation.
    $stream=New-Object IO.FileStream($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try {
        $bytes=[Text.Encoding]::UTF8.GetBytes(($Data | ConvertTo-Json -Depth 12 -Compress))
        $stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)
    } finally { $stream.Dispose() }
}
function Assert-ServiceName([string]$Name) {
    if ($Name -cnotmatch '^RackClick[A-Za-z0-9_.-]{0,200}$') { Fail 'service_name_invalid' }
}
function Assert-Elevated {
    $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
    $principal=New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Fail 'not_elevated' }
}
function Get-Zip([string]$Path) {
    Assert-NoReparse $Path
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        $s=[Security.Cryptography.SHA256]::Create()
        try { $digest=([BitConverter]::ToString($s.ComputeHash($stream))).Replace('-','').ToLowerInvariant() } finally { $s.Dispose() }
        if ($digest -ne $ZipPin) { Fail 'archive_hash_mismatch' }
        $stream.Position=0
        Add-Type -AssemblyName System.IO.Compression
        $zip=New-Object IO.Compression.ZipArchive($stream,[IO.Compression.ZipArchiveMode]::Read,$false)
        $seen=@{};[long]$bytes=0
        foreach ($entry in $zip.Entries) {
            $name=$entry.FullName
            if ($name -notmatch ('^'+[regex]::Escape($ReferenceFolder)+'/[^:]+$') -or
                $name.Contains('\') -or $name -match '(^|/)\.\.?(/|$)' -or $seen.ContainsKey($name)) { Fail 'archive_path_invalid' }
            $seen[$name]=$true;$bytes+=$entry.Length
            if (($entry.ExternalAttributes -shr 16 -band 61440) -eq 40960) { Fail 'archive_reparse' }
        }
        if ($zip.Entries.Count -ne 356 -or $bytes -gt 500000000) { Fail 'archive_layout_invalid' }
        return $zip
    } catch { $stream.Dispose();throw }
}
function Read-ZipText($Zip,[string]$Name) {
    $entry=$Zip.GetEntry($ReferenceFolder+'/'+$Name)
    if ($null -eq $entry) { Fail 'archive_member_missing' }
    $stream=$entry.Open();$reader=New-Object IO.StreamReader($stream,[Text.Encoding]::UTF8,$true)
    try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
}
function Import-ReferenceFunctions([string]$Text) {
    if ((Hash-Text $Text) -ne $ReferenceScriptPin) { Fail 'reference_script_hash_mismatch' }
    $tokens=$null;$errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseInput($Text,[ref]$tokens,[ref]$errors)
    if ($errors.Count) { Fail 'reference_script_invalid' }
    $prefix=New-Object Collections.Generic.List[string]
    foreach ($node in $ast.EndBlock.Statements) {
        if ($node -is [Management.Automation.Language.TryStatementAst]) { break }
        $prefix.Add($node.Extent.Text)
    }
    . ([scriptblock]::Create(($prefix -join "`n")))
}
function Get-Context([string]$Explicit,[string]$Name) {
    Assert-ServiceName $Name
    $root=Resolve-TrialRoot $Explicit
    Assert-NoReparse $root
    $id=Get-InstallationId $root
    if (-not (Test-Path -LiteralPath (Join-Path $root $id) -PathType Container)) { Fail 'store_missing' }
    $service=@(Get-CimInstance Win32_Service -Filter ("Name = '"+$Name+"'"))
    if ($service.Count -ne 1 -or $service[0].State -ne 'Running' -or [uint32]$service[0].ProcessId -eq 0) { Fail 'service_not_running' }
    return [ordered]@{trialRoot=[IO.Path]::GetFullPath($root);installationId=$id;service=$Name}
}
function Confirm-SystemRead([string]$Id) {
    if ([Console]::IsInputRedirected) { Fail 'console_required' }
    $phrase='CONFIRMO LECTURA SYSTEM '+$Id
    Write-Host ('Se creara una tarea SYSTEM temporal. La lectura sigue bajo el token real del servicio. Escriba: '+$phrase)
    Assert-SystemConfirmation (Read-Host 'Confirmacion') $Id
}
function Assert-SystemConfirmation([string]$Typed,[string]$Id) {
    if ($Typed -cne ('CONFIRMO LECTURA SYSTEM '+$Id)) { Fail 'confirmation_mismatch' }
}
function Expand-PrivatePackage($Zip,[string]$Root) {
    foreach ($entry in $Zip.Entries) {
        $target=Join-Path $Root $entry.FullName.Replace('/','\')
        if ($entry.FullName.EndsWith('/')) { [void][IO.Directory]::CreateDirectory($target);continue }
        [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))
        $entryInput=$entry.Open();$output=New-Object IO.FileStream($target,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try { $entryInput.CopyTo($output) } finally { $output.Dispose();$entryInput.Dispose() }
    }
}
function Get-TaskXml([string]$Worker,[string]$Plan,[string]$PlanHash,[string]$Name) {
    $powershell=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $arguments='-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+$Worker+'" -Mode Worker -PlanPath "'+$Plan+'" -ExpectedPlanSha256 '+$PlanHash
    $exe=[Security.SecurityElement]::Escape($powershell);$argsXml=[Security.SecurityElement]::Escape($arguments)
    return @"
<Task version="1.3" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"><RegistrationInfo><Description>$Name</Description></RegistrationInfo><Triggers/><Principals><Principal id="TrialSystem"><UserId>S-1-5-18</UserId><RunLevel>HighestAvailable</RunLevel><RequiredPrivileges><Privilege>SeDebugPrivilege</Privilege><Privilege>SeImpersonatePrivilege</Privilege><Privilege>SeChangeNotifyPrivilege</Privilege></RequiredPrivileges></Principal></Principals><Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><AllowHardTerminate>true</AllowHardTerminate><StartWhenAvailable>false</StartWhenAvailable><RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable><AllowStartOnDemand>true</AllowStartOnDemand><Enabled>true</Enabled><Hidden>false</Hidden><ExecutionTimeLimit>PT4M</ExecutionTimeLimit></Settings><Actions Context="TrialSystem"><Exec><Command>$exe</Command><Arguments>$argsXml</Arguments></Exec></Actions></Task>
"@
}
function New-TaskDefinition($Scheduler,[string]$Xml) {
    # Use the documented IPrincipal2 API: the native XmlText setter rejected RequiredPrivileges in this environment.
    if (-not ('RackClick.SystemReadTrial.PrincipalInterop' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace RackClick.SystemReadTrial {
 [ComImport,Guid("248919AE-E345-4A6D-8AEB-E0D3165C904E"),InterfaceType(ComInterfaceType.InterfaceIsDual)]
 public interface IPrincipal2 {
  int ProcessTokenSidType {get;set;}
  int RequiredPrivilegeCount {get;}
  [return:MarshalAs(UnmanagedType.BStr)] string GetRequiredPrivilege(int index);
  void AddRequiredPrivilege([MarshalAs(UnmanagedType.BStr)] string privilege);
 }
 public static class PrincipalInterop {
  public static void Add(object principal,string privilege) { ((IPrincipal2)principal).AddRequiredPrivilege(privilege); }
 }
}
'@
    }
    [xml]$withoutPrivileges=$Xml
    $ns=New-Object Xml.XmlNamespaceManager($withoutPrivileges.NameTable);$ns.AddNamespace('t','http://schemas.microsoft.com/windows/2004/02/mit/task')
    $required=$withoutPrivileges.SelectSingleNode('/t:Task/t:Principals/t:Principal/t:RequiredPrivileges',$ns)
    if ($null -eq $required) { Fail 'task_privileges_invalid' }
    [void]$required.ParentNode.RemoveChild($required)
    $definition=$Scheduler.NewTask(0);$definition.XmlText=$withoutPrivileges.OuterXml
    $definition.Principal.LogonType=5
    foreach ($privilege in @('SeDebugPrivilege','SeImpersonatePrivilege','SeChangeNotifyPrivilege')) {
        [RackClick.SystemReadTrial.PrincipalInterop]::Add($definition.Principal,$privilege)
    }
    Assert-TaskContract $definition.XmlText $Xml
    return $definition
}
function New-TaskOwned($Folder,[string]$Name,[string]$Xml) {
    try { $prior=$Folder.GetTask($Name) } catch {
        $hresult=$_.Exception.HResult
        if ($null -ne $_.Exception.InnerException) { $hresult=$_.Exception.InnerException.HResult }
        if ($hresult -ne -2147024894) { throw }
        $prior=$null
    }
    if ($null -ne $prior) { Fail 'task_name_exists' }
    $definition=New-TaskDefinition $script:Scheduler $Xml
    return $Folder.RegisterTaskDefinition($Name,$definition,2,'SYSTEM',$null,5,$TaskDacl)
}
function Get-OwnTask($Folder,[string]$Name,[string]$Xml) {
    $task=$Folder.GetTask($Name)
    if ([string]$task.Xml -cne $Xml) { Fail 'task_definition_changed' }
    return $task
}
function Assert-TaskContract([string]$Actual,[string]$Expected) {
    [xml]$actualDoc=$Actual;[xml]$expectedDoc=$Expected
    $ns=New-Object Xml.XmlNamespaceManager($actualDoc.NameTable);$ns.AddNamespace('t','http://schemas.microsoft.com/windows/2004/02/mit/task')
    $ens=New-Object Xml.XmlNamespaceManager($expectedDoc.NameTable);$ens.AddNamespace('t','http://schemas.microsoft.com/windows/2004/02/mit/task')
    if ($actualDoc.SelectNodes('/t:Task/t:Principals/t:Principal',$ns).Count -ne 1 -or
        $actualDoc.SelectNodes('/t:Task/t:Actions/*',$ns).Count -ne 1 -or
        $actualDoc.SelectNodes('/t:Task/t:Triggers/*',$ns).Count -ne 0 -or
        $actualDoc.SelectNodes('/t:Task/t:Principals/t:Principal/t:GroupId',$ns).Count -ne 0 -or
        $actualDoc.SelectNodes('/t:Task/t:Principals/t:Principal/t:LogonType',$ns).Count -ne 0) { Fail 'task_contract_invalid' }
    foreach ($xpath in @('/t:Task/t:Principals/t:Principal/t:UserId','/t:Task/t:Principals/t:Principal/t:RunLevel','/t:Task/t:Actions/t:Exec/t:Command','/t:Task/t:Actions/t:Exec/t:Arguments','/t:Task/t:Settings/t:ExecutionTimeLimit','/t:Task/t:Settings/t:Enabled','/t:Task/t:RegistrationInfo/t:Description')) {
        $left=@($actualDoc.SelectNodes($xpath,$ns));$right=@($expectedDoc.SelectNodes($xpath,$ens))
        if ($left.Count -ne 1 -or $right.Count -ne 1 -or $left[0].InnerText -cne $right[0].InnerText) { Fail 'task_contract_invalid' }
    }
    $required=@($actualDoc.SelectNodes('/t:Task/t:Principals/t:Principal/t:RequiredPrivileges/t:Privilege',$ns) | ForEach-Object {$_.InnerText} | Sort-Object)
    if ($required.Count -ne 3 -or ($required -join ',') -cne 'SeChangeNotifyPrivilege,SeDebugPrivilege,SeImpersonatePrivilege') { Fail 'task_privileges_invalid' }
    if ($actualDoc.SelectNodes('/t:Task/t:Actions/t:Exec/t:WorkingDirectory',$ns).Count -gt 0) { Fail 'task_contract_invalid' }
}
function Remove-OwnTask($Folder,[string]$Name,[string]$Xml) {
    try {
        $task=Get-OwnTask $Folder $Name $Xml
        if ($task.State -eq 4 -or $task.State -eq 2) {
            $task.Stop(0)
            $until=[DateTime]::UtcNow.AddSeconds(10)
            do { Start-Sleep -Milliseconds 200;$task=Get-OwnTask $Folder $Name $Xml } while (($task.State -eq 4 -or $task.State -eq 2) -and [DateTime]::UtcNow -lt $until)
        }
        if ($task.State -eq 4 -or $task.State -eq 2) { return 'running' }
        $Folder.DeleteTask($Name,0)
        return 'removed'
    } catch { return 'preserved' }
}
function Test-StrictOutcome($Outcome,[int]$Targets) {
    if ($null -eq $Outcome -or $null -eq $Outcome.raw -or -not (Test-ProbeOutcome $Outcome)) { return $false }
    $raw=$Outcome.raw
    foreach ($flag in @('processLinked','tokenMatched','impersonationVerified','identityRestored')) {
        if ($raw.$flag -isnot [bool] -or $raw.$flag -ne $true) { return $false }
    }
    foreach ($value in @($raw.schemaVersion,$raw.store.activeVersion,$raw.store.keyBytes,$raw.writeProbe.targets,$raw.writeProbe.writeDenied,$raw.writeProbe.dacDenied,$raw.writeProbe.writeGranted,$raw.writeProbe.dacGranted,$raw.writeProbe.ownerIsReader,$raw.writeProbe.inconclusive,$Outcome.exitCode,$Outcome.stderrBytes)) {
        if ($value -isnot [int] -and $value -isnot [long]) { return $false }
    }
    return ($raw.schemaVersion -eq 1 -and $raw.verb -ceq 'read' -and [int]$raw.store.activeVersion -gt 0 -and
        $Targets -ge 5 -and [int]$raw.writeProbe.targets -eq $Targets -and
        [int]$raw.writeProbe.writeDenied -eq $Targets -and [int]$raw.writeProbe.dacDenied -eq $Targets -and
        $raw.debugPrivilege -ne 'restore_failed' -and [int]$Outcome.stderrBytes -eq 0)
}
function Invoke-ProbeWithFingerprint($Plan,[string]$PackageRoot) {
    $result=[ordered]@{schemaVersion=1;status='failed';code='probe_failed';executor='SYSTEM';reader='service_token';installationId=$Plan.installationId;fingerprintState='not_checked';outcome=$null}
    $before=$null;$after=$null
    try {
        $before=Get-StoreFingerprint $Plan.trialRoot
        if ($before.digest -cne $Plan.beforeDigest -or $before.count -ne $Plan.beforeCount) { Fail 'store_changed_before_probe' }
        $result.outcome=Invoke-ReadProbe $PackageRoot $Plan.trialRoot $Plan.installationId $Plan.service $ProbeTimeout
        if (-not (Test-StrictOutcome $result.outcome $before.count)) {
            if ($result.outcome.raw.code -is [string] -and $result.outcome.raw.code -cmatch '^[a-z][a-z0-9_]{0,99}$') { Fail $result.outcome.raw.code }
            Fail 'probe_contract_failed'
        }
        $result.status='passed';$result.code=''
    } catch { $result.code=Error-Code $_ }
    finally {
        try {
            $after=Get-StoreFingerprint $Plan.trialRoot
            if ($null -ne $before -and $before.digest -ceq $after.digest -and $before.count -eq $after.count) { $result.fingerprintState='unchanged' }
            else { $result.fingerprintState='changed';$result.status='failed';$result.code='store_state_changed' }
        } catch { $result.fingerprintState='unavailable';$result.status='failed';$result.code='fingerprint_after_failed' }
    }
    return $result
}
function Assert-ImpersonatePrivilege {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace RackClick.SystemReadTrial {
 public static class Privilege {
  [StructLayout(LayoutKind.Sequential)] private struct Luid { public uint Low; public int High; }
  [DllImport("kernel32.dll")] private static extern IntPtr GetCurrentProcess();
  [DllImport("kernel32.dll")] private static extern bool CloseHandle(IntPtr h);
  [DllImport("advapi32.dll",SetLastError=true)] private static extern bool OpenProcessToken(IntPtr p,uint a,out IntPtr t);
  [DllImport("advapi32.dll",SetLastError=true,CharSet=CharSet.Unicode)] private static extern bool LookupPrivilegeValueW(string s,string n,out Luid l);
  [DllImport("advapi32.dll",SetLastError=true)] private static extern bool GetTokenInformation(IntPtr t,int c,IntPtr b,uint n,out uint z);
  public static bool Enabled() {
   IntPtr token; if(!OpenProcessToken(GetCurrentProcess(),8,out token))return false;
   IntPtr buffer=IntPtr.Zero;
   try { Luid l;if(!LookupPrivilegeValueW(null,"SeImpersonatePrivilege",out l))return false;uint size;
    GetTokenInformation(token,3,IntPtr.Zero,0,out size);if(size<4||size>1048576)return false;
    buffer=Marshal.AllocHGlobal((int)size);if(!GetTokenInformation(token,3,buffer,size,out size))return false;
    int count=Marshal.ReadInt32(buffer);if(count<0||4L+count*12L>size)return false;
    for(int i=0;i<count;i++){int p=4+12*i;if(unchecked((uint)Marshal.ReadInt32(buffer,p))==l.Low&&Marshal.ReadInt32(buffer,p+4)==l.High)return (Marshal.ReadInt32(buffer,p+8)&2)!=0;}
    return false;
   } finally {if(buffer!=IntPtr.Zero)Marshal.FreeHGlobal(buffer);CloseHandle(token);}
  }
 }
}
'@
    if (-not [RackClick.SystemReadTrial.Privilege]::Enabled()) { Fail 'worker_impersonate_unavailable' }
}
function Invoke-Worker {
    if ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -ne 'S-1-5-18' -or
        $null -ne [Security.Principal.WindowsIdentity]::GetCurrent($true)) { Fail 'worker_not_system' }
    if ($ExpectedPlanSha256 -notmatch '^[a-f0-9]{64}$') { Fail 'plan_pin_invalid' }
    $root=[IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($PlanPath))
    if ([IO.Path]::GetDirectoryName($root) -ine [IO.Path]::GetFullPath($env:ProgramData) -or
        (Split-Path -Leaf $root) -notmatch ('^'+[regex]::Escape($WorkPrefix)+'[a-f0-9]{32}$') -or
        [IO.Path]::GetFileName($PlanPath) -cne 'plan.json') { Fail 'worker_root_invalid' }
    Assert-PrivateRoot $root;Assert-NoReparse $PlanPath
    if ((Hash-File $PlanPath) -cne $ExpectedPlanSha256) { Fail 'plan_hash_mismatch' }
    $plan=[IO.File]::ReadAllText($PlanPath) | ConvertFrom-Json
    if ($plan.schemaVersion -ne 1 -or $plan.scriptSha256 -cne (Hash-File $PSCommandPath) -or
        [IO.Path]::GetFullPath($PSCommandPath) -ine (Join-Path $root 'worker.ps1') -or
        $plan.taskName -cne (Split-Path -Leaf $root) -or $plan.zipSha256 -cne $ZipPin -or $plan.sumsSha256 -cne $SumsPin) { Fail 'plan_contract_invalid' }
    $package=Join-Path $root $ReferenceFolder
    $reference=Join-Path $package 'Invoke-MfaServiceReadTrial.ps1'
    if ((Hash-File $reference) -cne $ReferenceScriptPin) { Fail 'reference_script_hash_mismatch' }
    . Import-ReferenceFunctions ([IO.File]::ReadAllText($reference))
    $null=Test-PackageIntegrity $package $SumsPin
    Assert-ServiceName $plan.service
    # Persistent CreateNew lease: a second task start cannot repeat the key read.
    $marker=New-Object IO.FileStream((Join-Path $root 'execution.started'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $marker.Dispose()
    $result=$null
    try { Assert-ImpersonatePrivilege;$result=Invoke-ProbeWithFingerprint $plan $package }
    catch { $result=[ordered]@{schemaVersion=1;status='failed';code=(Error-Code $_);executor='SYSTEM';reader='service_token';installationId=$plan.installationId;fingerprintState='not_checked';outcome=$null} }
    Write-NewJson (Join-Path $root 'worker-result.json') $result
    if ($result.status -ne 'passed') { exit 1 }
}
function Wait-WorkerResult($Folder,[string]$Name,[string]$Xml,[string]$ResultPath,[int]$Timeout) {
    $until=[DateTime]::UtcNow.AddSeconds($Timeout)
    do {
        $task=Get-OwnTask $Folder $Name $Xml
        if (Test-Path -LiteralPath $ResultPath -PathType Leaf) {
            try { $value=[IO.File]::ReadAllText($ResultPath) | ConvertFrom-Json } catch [IO.IOException] { $value=$null }
            if ($null -ne $value -and $task.State -ne 4 -and $task.State -ne 2) { return $value }
        }
        Start-Sleep -Milliseconds 300
    } while ([DateTime]::UtcNow -lt $until)
    Fail 'worker_timeout'
}
function Get-Summary($Result,[string]$Cleanup) {
    $passed=$Result.status -ceq 'passed' -and $Result.code -ceq '' -and $Result.fingerprintState -ceq 'unchanged' -and $Cleanup -ceq 'removed'
    $operationCode=''
    if ($Result.code -is [string] -and $Result.code -cmatch '^[a-z][a-z0-9_]{0,99}$') { $operationCode=$Result.code }
    $summary=[ordered]@{schemaVersion=1;status=$(if($passed){'passed'}else{'failed'});code=$(if($passed){''}elseif($Cleanup -notin @('removed','not_registered')){'task_cleanup_incomplete'}else{$operationCode});operationCode=$operationCode;executor='SYSTEM';reader='service_token';fingerprintState=$Result.fingerprintState;taskCleanup=$Cleanup;stagingPreserved=$true;notMfaActivation=$true;probeMeasured=$false;probeCode='';processLinked=$null;tokenMatched=$null;impersonationVerified=$null;identityRestored=$null;activeVersion=$null;keyBytes=$null;targets=$null;writeDenied=$null;dacDenied=$null;writeGranted=$null;dacGranted=$null}
    if ($null -ne $Result.outcome -and $null -ne $Result.outcome.raw -and $Result.outcome.raw.schemaVersion -eq 1 -and $Result.outcome.raw.verb -ceq 'read') {
        $raw=$Result.outcome.raw;$summary.probeMeasured=$true
        if ($raw.code -is [string] -and $raw.code -cmatch '^[a-z][a-z0-9_]{0,99}$') { $summary.probeCode=$raw.code }
        foreach ($flag in @('processLinked','tokenMatched','impersonationVerified','identityRestored')) { if ($raw.$flag -is [bool]) { $summary[$flag]=$raw.$flag } }
        foreach ($field in @('activeVersion','keyBytes')) { if ($raw.store.$field -is [int] -or $raw.store.$field -is [long]) { $summary[$field]=$raw.store.$field } }
        foreach ($field in @('targets','writeDenied','dacDenied','writeGranted','dacGranted')) { if ($raw.writeProbe.$field -is [int] -or $raw.writeProbe.$field -is [long]) { $summary[$field]=$raw.writeProbe.$field } }
    }
    return $summary
}
function Invoke-CheckOrRun {
    Assert-Elevated;Assert-ServiceName $ServiceName
    if ($ExpectedScriptSha256 -notmatch '^[a-f0-9]{64}$') { Fail 'script_pin_required' }
    Assert-NoReparse $PSCommandPath
    $selfLease=[IO.File]::Open($PSCommandPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $zip=$null
    try {
        if ((Hash-File $PSCommandPath) -cne $ExpectedScriptSha256) { Fail 'script_hash_mismatch' }
        $zip=Get-Zip $ArchivePath
        . Import-ReferenceFunctions (Read-ZipText $zip 'Invoke-MfaServiceReadTrial.ps1')
        $context=Get-Context $TrialRoot $ServiceName
        $before=Get-StoreFingerprint $context.trialRoot
        if ($Mode -eq 'Check') { [ordered]@{status='ready';code='';newExecutionRoute='temporary_SYSTEM_task';taskCreated=$false;keysRead=$false} | ConvertTo-Json -Compress;return }
        Confirm-SystemRead $context.installationId
        # No filesystem writes or task registration occur before this confirmation.
        $name=$WorkPrefix+[guid]::NewGuid().ToString('N')
        $root=Join-Path $env:ProgramData $name
        New-PrivateRoot $root
        $task=$null;$folder=$null;$xml='';$cleanup='not_registered';$registrationAttempted=$false;$leases=New-Object Collections.Generic.List[IDisposable]
        $result=[ordered]@{status='failed';code='not_started';fingerprintState='not_checked';outcome=$null}
        try {
            Expand-PrivatePackage $zip $root
            $package=Join-Path $root $ReferenceFolder
            $null=Test-PackageIntegrity $package $SumsPin
            $worker=Join-Path $root 'worker.ps1'
            $source=[IO.File]::Open($PSCommandPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
            $leases.Add($source)
            $output=New-Object IO.FileStream($worker,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
            try {$source.CopyTo($output)}finally{$output.Dispose()}
            $plan=[ordered]@{schemaVersion=1;taskName=$name;scriptSha256=(Hash-File $worker);zipSha256=$ZipPin;sumsSha256=$SumsPin;trialRoot=$context.trialRoot;installationId=$context.installationId;service=$context.service;beforeDigest=$before.digest;beforeCount=$before.count}
            $planFile=Join-Path $root 'plan.json';Write-NewJson $planFile $plan
            foreach ($file in @(Get-ChildItem -LiteralPath $root -Recurse -File)) { $leases.Add([IO.File]::Open($file.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)) }
            $taskXml=Get-TaskXml $worker $planFile (Hash-File $planFile) $name
            $script:Scheduler=New-Object -ComObject Schedule.Service;$script:Scheduler.Connect();$folder=$script:Scheduler.GetFolder('\')
            $registrationAttempted=$true
            $task=New-TaskOwned $folder $name $taskXml
            $xml=[string]$task.Xml
            Assert-TaskContract $xml $taskXml
            $task=Get-OwnTask $folder $name $xml
            $null=$task.Run($null)
            $result=Wait-WorkerResult $folder $name $xml (Join-Path $root 'worker-result.json') $ParentTimeout
            if ($result.schemaVersion -ne 1 -or $result.executor -cne 'SYSTEM' -or $result.reader -cne 'service_token' -or $result.installationId -cne $context.installationId) { Fail 'worker_result_invalid' }
            if ($result.status -eq 'passed' -and (-not (Test-StrictOutcome $result.outcome $before.count) -or $result.fingerprintState -cne 'unchanged' -or $result.code -cne '')) { Fail 'worker_result_invalid' }
        } catch { $result=[ordered]@{status='failed';code=(Error-Code $_);fingerprintState='not_checked';outcome=$null} }
        finally {
            if ($null -ne $task -and $xml) { $cleanup=Remove-OwnTask $folder $name $xml }
            elseif ($registrationAttempted) { $cleanup='unconfirmed' }
            foreach ($lease in $leases) { $lease.Dispose() }
        }
        $summary=Get-Summary $result $cleanup
        try { Write-NewJson (Join-Path $root 'operator-result.json') $result;Write-NewJson (Join-Path $root 'summary-sanitized.json') $summary } catch { $summary.status='failed';$summary.code='report_write_failed' }
        $summary | ConvertTo-Json -Compress
        Write-Host ('Informe sanitizado: '+(Join-Path $root 'summary-sanitized.json'))
        if ($summary.status -ne 'passed') { exit 1 }
    } finally { if ($null -ne $zip) { $zip.Dispose() };$selfLease.Dispose() }
}
function Invoke-SelfTest {
    $xml=Get-TaskXml 'C:\private\worker.ps1' 'C:\private\plan.json' ('a'*64) 'RackClick-MFA-SystemRead-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    [xml]$parsed=$xml
    if ($xml -notmatch 'SeImpersonatePrivilege' -or $xml -notmatch 'SeDebugPrivilege' -or $xml -match '<Trigger>' -or $xml -notmatch 'PT4M') { Fail 'selftest_task_xml' }
    $bad=[ordered]@{status='passed';code='';fingerprintState='changed'}
    if ((Get-Summary $bad 'removed').status -eq 'passed') { Fail 'selftest_summary' }
    $good=[ordered]@{status='passed';code='';fingerprintState='unchanged'}
    if ((Get-Summary $good 'running').status -eq 'passed') { Fail 'selftest_cleanup' }
    [ordered]@{status='selftest_passed';checks=3;taskRegistered=$false;serviceAccessed=$false;keysRead=$false} | ConvertTo-Json -Compress
}

try {
    if ($Mode -eq 'SelfTest') { Invoke-SelfTest }
    else {
        if (($env:COMPUTERNAME -ieq 'LEAO') -or ([Environment]::MachineName -ieq 'LEAO')) { Fail 'host_excluded' }
        if ($Mode -eq 'Worker') { Invoke-Worker } else { Invoke-CheckOrRun }
    }
    exit 0
} catch {
    [ordered]@{schemaVersion=1;status='rejected';code=(Error-Code $_);taskCreated=$false;notMfaActivation=$true} | ConvertTo-Json -Compress
    exit 1
}
