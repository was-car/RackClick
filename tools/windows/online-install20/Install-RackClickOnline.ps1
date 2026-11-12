#requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet('Check','Prepare','Install')][string]$Mode='Install',
    [switch]$AcceptDownloads,
    [Alias('NoInteractive')][switch]$NonInteractive
)
# Template pins are replaced by the reviewed package producer, never by downloaded metadata.
$script:OnlineCoreSha='@@CORE_SHA@@'
$script:OnlineNativeSha='@@NATIVE_SHA@@'
$script:OnlinePythonSha='@@PY_SHA@@'
$script:OnlinePythonBytes='@@PY_BYTES@@'
$script:OnlinePythonUrl='https://www.python.org/ftp/python/3.12.3/python-3.12.3-embed-amd64.zip'
$script:OnlinePackageRoot=$PSScriptRoot

function Stop-Online([string]$Code) { throw ('online20:'+ $Code) }
function Get-OnlineErrorCode($Record) {
    if ($Record.Exception.Message -match '^online20:([a-z0-9_]+)$') {return $Matches[1]}
    return 'unexpected_error'
}
function Assert-OnlineNoReparse([string]$Path) {
    $item=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {Stop-Online 'path_reparse'}
        if ($item -is [IO.FileInfo]) {$item=$item.Directory} else {$item=$item.Parent}
    }
}
function Assert-OnlineHostFacts([int]$ProductType,[int]$DomainRole,[int]$Build,[string]$Architecture,[bool]$PartOfDomain) {
    if ($ProductType -ne 3 -or $DomainRole -notin @(2,3) -or $Build -ne 26100 -or
        $Architecture -notin @('64-bit','64 bits','64-Bit') -or $PartOfDomain -ne ($DomainRole -eq 3)) {
        Stop-Online 'host_not_supported'
    }
}
function Assert-OnlineHost {
    if (-not [Environment]::Is64BitOperatingSystem -or -not [Environment]::Is64BitProcess) {Stop-Online 'host_not_supported'}
    $os=@(Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop)
    $computer=@(Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction Stop)
    if ($os.Count -ne 1 -or $computer.Count -ne 1 -or $null -eq $os[0].ProductType -or
        $null -eq $computer[0].DomainRole -or $computer[0].PartOfDomain -isnot [bool] -or
        [string]$os[0].Version -notmatch '^10\.0\.26100(\.|$)') {Stop-Online 'host_not_supported'}
    Assert-OnlineHostFacts $os[0].ProductType $computer[0].DomainRole ([int]$os[0].BuildNumber) $os[0].OSArchitecture $computer[0].PartOfDomain
}
function Get-OnlineInstallationRoots {
    return @(
        [pscustomobject]@{path=[Environment]::GetFolderPath('CommonApplicationData');allowTransport=$true},
        [pscustomobject]@{path=[Environment]::GetFolderPath('ProgramFiles');allowTransport=$false},
        [pscustomobject]@{path=[Environment]::GetFolderPath('ProgramFilesX86');allowTransport=$false}
    )
}
function Test-OnlinePreviousTransport($Item,[string]$Base) {
    # A transport is only ignored by the installation detector. It is never resumed, adopted or changed.
    if ($Item -isnot [IO.DirectoryInfo] -or $Item.Name -cnotmatch '\ARackClick-Online20-[a-f0-9]{32}\z' -or
        -not [string]::Equals($Item.Parent.FullName,[IO.Path]::GetFullPath($Base),[StringComparison]::OrdinalIgnoreCase)) {return $false}
    try {
        Assert-OnlineNoReparse $Item.FullName
        $acl=Get-Acl -LiteralPath $Item.FullName -ErrorAction Stop
        if (-not $acl.AreAccessRulesProtected -or
            $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin @('S-1-5-32-544','S-1-5-18')) {return $false}
        $rules=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
        if ($rules.Count -ne 2) {return $false}
        $seen=@{}
        foreach ($rule in $rules) {
            $sid=$rule.IdentityReference.Value
            if ($sid -notin @('S-1-5-18','S-1-5-32-544') -or $seen.ContainsKey($sid) -or $rule.IsInherited -or
                $rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
                $rule.FileSystemRights -ne [Security.AccessControl.FileSystemRights]::FullControl -or
                [int]$rule.InheritanceFlags -ne 3 -or [int]$rule.PropagationFlags -ne 0) {return $false}
            $seen[$sid]=$true
        }
        return $true
    } catch {return $false}
}
function Assert-OnlineFreshHost {
    # Reject any RackClick account/service or previous installation; never repair or remove it.
    $services=@(Get-CimInstance -ClassName Win32_Service -ErrorAction Stop | Where-Object {
        $_.Name -like 'RackClick*' -or $_.DisplayName -like 'RackClick*' -or $_.PathName -match '(?i)RackClick'
    })
    if ($services.Count) {Stop-Online 'existing_service'}
    $accounts=@(Get-LocalUser -ErrorAction Stop | Where-Object {$_.Name -like 'RackClick*'})
    if ($accounts.Count) {Stop-Online 'existing_account'}
    foreach ($root in @(Get-OnlineInstallationRoots)) {
        $base=[string]$root.path
        if ([string]::IsNullOrWhiteSpace($base)) {continue}
        Assert-OnlineNoReparse $base
        foreach ($item in @(Get-ChildItem -LiteralPath $base -Force -ErrorAction Stop | Where-Object {$_.Name -like 'RackClick*'})) {
            if ($root.allowTransport -eq $true -and (Test-OnlinePreviousTransport $item $base)) {continue}
            Stop-Online 'existing_installation'
        }
    }
}
function Assert-OnlineAdmin {
    $principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {Stop-Online 'admin_required'}
}
function Assert-OnlinePins {
    foreach ($pin in @($script:OnlineCoreSha,$script:OnlineNativeSha,$script:OnlinePythonSha)) {
        if ($pin -cnotmatch '^[a-f0-9]{64}$') {Stop-Online 'package_pin_invalid'}
    }
    if ($script:OnlinePythonSha -cne '38b265fc0612027a126ae54d2485101f041b61893e41ef4f421dee6ac618a99e' -or
        [string]$script:OnlinePythonBytes -cne '11055461') {Stop-Online 'package_python_pin_invalid'}
}
function Get-OnlineStreamHash([IO.Stream]$Stream) {
    $hash=[Security.Cryptography.SHA256]::Create()
    try {return ([BitConverter]::ToString($hash.ComputeHash($Stream))).Replace('-','').ToLowerInvariant()}
    finally {$hash.Dispose()}
}
function Get-OnlineFileHash([string]$Path) {
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {return Get-OnlineStreamHash $stream} finally {$stream.Dispose()}
}
function Open-OnlineCore {
    $path=Join-Path $script:OnlinePackageRoot 'RackClick-Core20.zip'
    Assert-OnlineNoReparse $path
    $stream=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        if ((Get-OnlineStreamHash $stream) -cne $script:OnlineCoreSha) {Stop-Online 'core_hash_mismatch'}
        $stream.Position=0
        return $stream
    } catch {$stream.Dispose();throw}
}
function Confirm-OnlineDownloads([bool]$Accepted,[bool]$Unattended) {
    if ($Accepted) {return}
    if ($Unattended -or [Console]::IsInputRedirected) {Stop-Online 'downloads_not_accepted'}
    Write-Host 'Se adquiriran directamente Python 3.12.3 (temporal), SDK .NET 10.0.401 (solo fuente del runtime), PostgreSQL 17.11-4 y VC++ 14.51 desde sus proveedores oficiales.'
    Write-Host 'Revise el manual y sus condiciones/licencias. No se instalaran Python, SDK ni Node. Escriba ADQUIRIR para continuar.'
    if ((Read-Host 'Confirmacion') -cne 'ADQUIRIR') {Stop-Online 'downloads_not_accepted'}
}
function Initialize-OnlineNative {
    if ('RackClick.Online20.Folder' -as [type]) {return}
    Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.IO;
using System.Diagnostics;
using System.Threading;
using System.Runtime.InteropServices;
namespace RackClick.Online20 {
 public static class Folder {
  [StructLayout(LayoutKind.Sequential)] struct SA {public int Length;public IntPtr Descriptor;public int Inherit;}
  [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool ConvertStringSecurityDescriptorToSecurityDescriptorW(string s,uint r,out IntPtr d,out uint b);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CreateDirectoryW(string p,ref SA a);
  [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr p);
  public static int Create(string path) {
   IntPtr d;uint b;
   if(!ConvertStringSecurityDescriptorToSecurityDescriptorW("O:BAG:SYD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)",1,out d,out b))return Marshal.GetLastWin32Error();
   try{var a=new SA{Length=Marshal.SizeOf(typeof(SA)),Descriptor=d,Inherit=0};return CreateDirectoryW(path,ref a)?0:Marshal.GetLastWin32Error();}finally{LocalFree(d);}
  }
 }
 public sealed class ChildResult {public int ExitCode;public string Output;public bool Limited;}
 public static class Child {
  public static ChildResult Run(ProcessStartInfo info,int seconds,int limit) {
   using(var p=new Process()) {
    p.StartInfo=info;var output=new StringBuilder();int total=0;bool limited=false;
    if(!p.Start())throw new InvalidOperationException();
    ThreadStart readOut=delegate {try{int c;while((c=p.StandardOutput.Read())>=0){lock(output){if(++total>limit){limited=true;try{p.Kill();}catch{}break;}output.Append((char)c);}}}catch{limited=true;}};
    ThreadStart readErr=delegate {try{int c;while((c=p.StandardError.Read())>=0){lock(output){if(++total>limit){limited=true;try{p.Kill();}catch{}break;}}}}catch{limited=true;}};
    var a=new Thread(readOut);var b=new Thread(readErr);a.IsBackground=true;b.IsBackground=true;a.Start();b.Start();
    if(!p.WaitForExit(seconds*1000)){limited=true;try{p.Kill();}catch{}p.WaitForExit(5000);}
    if(!a.Join(5000)||!b.Join(5000))limited=true;
    return new ChildResult{ExitCode=p.HasExited?p.ExitCode:-1,Output=output.ToString(),Limited=limited};
   }
  }
 }
}
'@ -ErrorAction Stop
}
function New-OnlineStage {
    $parent=[Environment]::GetFolderPath('CommonApplicationData')
    Assert-OnlineNoReparse $parent
    Initialize-OnlineNative
    $path=Join-Path $parent ('RackClick-Online20-'+[guid]::NewGuid().ToString('N'))
    $code=[RackClick.Online20.Folder]::Create($path)
    if ($code -eq 183) {Stop-Online 'stage_exists'}
    if ($code -ne 0) {Stop-Online 'stage_create_failed'}
    $acl=Get-Acl -LiteralPath $path
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne 'S-1-5-32-544' -or -not $acl.AreAccessRulesProtected) {Stop-Online 'stage_acl_invalid'}
    $rules=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
    if ($rules.Count -ne 2) {Stop-Online 'stage_acl_invalid'}
    foreach ($rule in $rules) {
        if ($rule.IdentityReference.Value -notin @('S-1-5-18','S-1-5-32-544') -or
            $rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
            $rule.FileSystemRights -ne [Security.AccessControl.FileSystemRights]::FullControl) {Stop-Online 'stage_acl_invalid'}
    }
    return $path
}
function Assert-OnlineArtifact([string]$Path,[long]$Bytes,[string]$Sha256) {
    Assert-OnlineNoReparse $Path
    $inputStream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        if ($inputStream.Length -ne $Bytes) {Stop-Online 'download_size_mismatch'}
        if ((Get-OnlineStreamHash $inputStream) -cne $Sha256) {Stop-Online 'download_hash_mismatch'}
    } finally {$inputStream.Dispose()}
}
function Assert-OnlinePythonUri([uri]$Uri) {
    if (-not $Uri.IsAbsoluteUri -or $Uri.Scheme -cne 'https' -or $Uri.DnsSafeHost -cne 'www.python.org' -or
        $Uri.Port -ne 443 -or $Uri.UserInfo -ne '' -or $Uri.Fragment -ne '') {Stop-Online 'download_origin_invalid'}
}
function New-OnlineRequest([uri]$Uri) {
    # Windows PowerShell/.NET Framework uses the Windows TLS trust store. No trust callback is replaced.
    $request=[Net.HttpWebRequest]::Create($Uri)
    $request.AllowAutoRedirect=$false;$request.Timeout=90000;$request.ReadWriteTimeout=90000
    $request.Method='GET';$request.UserAgent='RackClick-Online20'
    return $request
}
function Receive-OnlinePython([string]$Path) {
    $uri=[uri]$script:OnlinePythonUrl
    $oldProtocol=[Net.ServicePointManager]::SecurityProtocol
    [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
    try {
        for ($redirect=0;$redirect -le 3;$redirect++) {
            Assert-OnlinePythonUri $uri
            $request=New-OnlineRequest $uri
            $response=$request.GetResponse()
            try {
                $status=[int]$response.StatusCode
                if ($status -in @(301,302,303,307,308)) {
                    if ($redirect -eq 3) {Stop-Online 'download_redirect_limit'}
                    $uri=New-Object uri($uri,[string]$response.Headers['Location'])
                    Assert-OnlinePythonUri $uri
                    continue
                }
                if ($status -ne 200) {Stop-Online 'download_http_failed'}
                if ($response.ContentLength -ge 0 -and $response.ContentLength -ne [long]$script:OnlinePythonBytes) {Stop-Online 'download_size_mismatch'}
                $source=$response.GetResponseStream()
                $target=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
                try {
                    $buffer=New-Object byte[] 65536;[long]$total=0
                    while ($true) {
                        try {$count=$source.Read($buffer,0,$buffer.Length)} catch [IO.IOException] {Stop-Online 'download_unavailable'}
                        if ($count -le 0) {break}
                        $total+=$count
                        if ($total -gt [long]$script:OnlinePythonBytes) {Stop-Online 'download_size_mismatch'}
                        $target.Write($buffer,0,$count)
                    }
                } finally {$target.Dispose();$source.Dispose()}
                Assert-OnlineArtifact $Path ([long]$script:OnlinePythonBytes) $script:OnlinePythonSha
                return
            } finally {$response.Dispose()}
        }
        Stop-Online 'download_http_failed'
    } catch [Net.WebException] {Stop-Online 'download_unavailable'}
    catch [Net.Sockets.SocketException] {Stop-Online 'download_unavailable'}
    finally {[Net.ServicePointManager]::SecurityProtocol=$oldProtocol}
}
function Assert-OnlineProviderUri([uri]$Uri,[string]$Id) {
    $hosts=@{
        sdk=@('builds.dotnet.microsoft.com','dotnetcli.blob.core.windows.net','dotnetcli.azureedge.net')
        postgresql=@('get.enterprisedb.com')
        crt=@('download.visualstudio.microsoft.com')
    }
    if ($Id -cnotin @('sdk','postgresql','crt')) {Stop-Online 'provider_profile_invalid'}
    if (-not $Uri.IsAbsoluteUri -or $Uri.Scheme -cne 'https' -or $Uri.DnsSafeHost -cnotin $hosts[$Id] -or
        $Uri.Port -ne 443 -or $Uri.UserInfo -ne '' -or $Uri.Fragment -ne '') {Stop-Online 'download_origin_invalid'}
}
function Get-OnlineProviders([string]$Core) {
    $path=Join-Path $Core 'recipe.json'
    Assert-OnlineNoReparse $path
    # Exact recipe bytes from Core20; anchored independently of JSON parsing or duplicate-property handling.
    if ((Get-OnlineFileHash $path) -cne '@@RECIPE_SHA@@') {Stop-Online 'provider_recipe_pin_invalid'}
    $recipe=[IO.File]::ReadAllText($path,[Text.Encoding]::UTF8) | ConvertFrom-Json -ErrorAction Stop
    $profiles=@{
        sdk=@('dotnet-sdk-10.0.401-win-x64.zip','sha512')
        postgresql=@('postgresql-17.11-4-windows-x64-binaries.zip','sha256')
        crt=@('vc_redist.x64.exe','sha256')
    }
    $items=@($recipe.providers);$seen=@{}
    if ($items.Count -ne 3 -or $recipe.format -cne 'RackClickOnline20' -or $recipe.nativeEdition -cne '20') {Stop-Online 'provider_profile_invalid'}
    foreach ($item in $items) {
        $keys=@($item.PSObject.Properties.Name | Sort-Object)
        if (($keys -join ',') -cne 'algorithm,bytes,digest,fileName,id,target,url' -or $item.id -cnotin @('sdk','postgresql','crt') -or
            $seen.ContainsKey($item.id)) {Stop-Online 'provider_profile_invalid'}
        $seen[$item.id]=$true;$profile=$profiles[$item.id]
        if ($item.fileName -cne $profile[0] -or $item.algorithm -cne $profile[1] -or
            $item.bytes -isnot [int] -or $item.bytes -le 0 -or $item.bytes -gt 500000000 -or
            $item.digest -cnotmatch $(if ($item.algorithm -ceq 'sha512') {'\A[a-f0-9]{128}\z'} else {'\A[a-f0-9]{64}\z'}) -or
            [string]$item.target -cnotmatch '\A\.local/downloads/[a-zA-Z0-9_.\-/]+\z' -or [string]$item.target -match '(^|/)\.\.(/|$)') {Stop-Online 'provider_profile_invalid'}
        Assert-OnlineProviderUri ([uri]$item.url) $item.id
        if ([IO.Path]::GetFileName(([uri]$item.url).AbsolutePath).ToLowerInvariant() -cne $item.fileName -or
            [IO.Path]::GetFileName([string]$item.target) -cne $item.fileName) {Stop-Online 'provider_profile_invalid'}
    }
    return $items
}
function Assert-OnlineProviderArtifact([string]$Path,$Item) {
    Assert-OnlineNoReparse $Path
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $hash=$null
    try {
        if ($stream.Length -ne [long]$Item.bytes) {Stop-Online 'download_size_mismatch'}
        if ($Item.algorithm -ceq 'sha256') {$hash=[Security.Cryptography.SHA256]::Create()}
        elseif ($Item.algorithm -ceq 'sha512') {$hash=[Security.Cryptography.SHA512]::Create()}
        else {Stop-Online 'provider_profile_invalid'}
        $digest=([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant()
        if ($digest -cne $Item.digest) {Stop-Online 'download_hash_mismatch'}
    } finally {if ($null -ne $hash) {$hash.Dispose()};$stream.Dispose()}
}
function Receive-OnlineProvider($Item,[string]$Path) {
    $uri=[uri]$Item.url
    $oldProtocol=[Net.ServicePointManager]::SecurityProtocol
    [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
    $clock=[Diagnostics.Stopwatch]::StartNew()
    try {
        for ($redirect=0;$redirect -le 3;$redirect++) {
            Assert-OnlineProviderUri $uri $Item.id
            $request=New-OnlineRequest $uri
            $response=$request.GetResponse()
            try {
                $status=[int]$response.StatusCode
                if ($status -in @(301,302,303,307,308)) {
                    if ($redirect -eq 3) {Stop-Online 'download_redirect_limit'}
                    $uri=New-Object uri($uri,[string]$response.Headers['Location'])
                    Assert-OnlineProviderUri $uri $Item.id
                    continue
                }
                if ($status -ne 200) {Stop-Online 'download_http_failed'}
                if ($response.ContentLength -ge 0 -and $response.ContentLength -ne [long]$Item.bytes) {Stop-Online 'download_size_mismatch'}
                $source=$response.GetResponseStream();$target=$null
                try {
                    $target=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
                    $buffer=New-Object byte[] 1048576;[long]$total=0
                    while ($true) {
                        if ($clock.Elapsed.TotalSeconds -gt 1800) {Stop-Online 'download_unavailable'}
                        try {$count=$source.Read($buffer,0,$buffer.Length)} catch [IO.IOException] {Stop-Online 'download_unavailable'}
                        if ($count -le 0) {break}
                        $total+=$count
                        if ($total -gt [long]$Item.bytes) {Stop-Online 'download_size_mismatch'}
                        $target.Write($buffer,0,$count)
                    }
                } finally {if ($null -ne $target) {$target.Dispose()};$source.Dispose()}
                Assert-OnlineProviderArtifact $Path $Item
                return
            } finally {$response.Dispose()}
        }
        Stop-Online 'download_http_failed'
    } catch [Net.WebException] {Stop-Online 'download_unavailable'}
    catch [Net.Sockets.SocketException] {Stop-Online 'download_unavailable'}
    finally {$clock.Stop();[Net.ServicePointManager]::SecurityProtocol=$oldProtocol}
}
function Assert-OnlineProviderCache([string]$Core,[string]$Cache) {
    $items=@(Get-OnlineProviders $Core)
    if (-not (Test-Path -LiteralPath $Cache -PathType Container)) {Stop-Online 'provider_cache_incomplete'}
    Assert-OnlineNoReparse $Cache
    $files=@(Get-ChildItem -LiteralPath $Cache -Force -ErrorAction Stop)
    if ($files.Count -ne 3 -or @($files | Where-Object {$_.PSIsContainer}).Count) {Stop-Online 'provider_cache_incomplete'}
    foreach ($item in $items) {
        $path=Join-Path $Cache $item.fileName
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {Stop-Online 'provider_cache_incomplete'}
        Assert-OnlineProviderArtifact $path $item
    }
}
function Receive-OnlineProviders([string]$Stage,[string]$Core) {
    $items=@(Get-OnlineProviders $Core)
    $cache=Join-Path $Stage 'providers'
    if (Test-Path -LiteralPath $cache) {Stop-Online 'provider_cache_exists'}
    Assert-OnlineNoReparse $Stage
    [void][IO.Directory]::CreateDirectory($cache)
    foreach ($item in $items) {Receive-OnlineProvider $item (Join-Path $cache $item.fileName)}
    Assert-OnlineProviderCache $Core $cache
}
function Assert-OnlineZipRawNames([IO.Stream]$Stream) {
    # .NET Framework normalizes DOS backslashes in FullName. Inspect original central names too.
    $reader=New-Object IO.BinaryReader($Stream,[Text.Encoding]::UTF8,$true)
    try {
        $length=$Stream.Length
        if ($length -lt 22) {Stop-Online 'archive_layout_invalid'}
        $tailLength=[int][Math]::Min($length,65557);$Stream.Position=$length-$tailLength
        $tail=$reader.ReadBytes($tailLength);$end=-1
        for ($i=$tailLength-22;$i -ge 0;$i--) {
            if ([BitConverter]::ToUInt32($tail,$i) -eq 101010256 -and $i+22+[BitConverter]::ToUInt16($tail,$i+20) -eq $tailLength) {$end=$i;break}
        }
        if ($end -lt 0 -or [BitConverter]::ToUInt16($tail,$end+4) -ne 0 -or [BitConverter]::ToUInt16($tail,$end+6) -ne 0) {Stop-Online 'archive_layout_invalid'}
        $count=[BitConverter]::ToUInt16($tail,$end+10)
        $offset=[BitConverter]::ToUInt32($tail,$end+16)
        if ($count -eq 65535 -or $offset -eq 4294967295 -or $offset -ge $length) {Stop-Online 'archive_layout_invalid'}
        $Stream.Position=$offset
        for ($n=0;$n -lt $count;$n++) {
            if ($reader.ReadUInt32() -ne 33639248) {Stop-Online 'archive_layout_invalid'}
            [void]$reader.ReadBytes(24)
            $nameLength=$reader.ReadUInt16();$extra=$reader.ReadUInt16();$comment=$reader.ReadUInt16()
            [void]$reader.ReadBytes(12)
            $name=$reader.ReadBytes($nameLength)
            if ($name.Length -ne $nameLength -or $name -contains 92 -or $name -contains 58 -or $name -contains 0) {Stop-Online 'archive_path_invalid'}
            $Stream.Position+=$extra+$comment
            if ($Stream.Position -gt $length) {Stop-Online 'archive_layout_invalid'}
        }
    } finally {$reader.Dispose();$Stream.Position=0}
}
function Expand-OnlineZip([string]$Path,[string]$Root) {
    if (Test-Path -LiteralPath $Root) {Stop-Online 'archive_destination_exists'}
    Assert-OnlineNoReparse $Path
    Assert-OnlineNoReparse ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($Root)))
    Add-Type -AssemblyName System.IO.Compression -ErrorAction Stop
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $zip=$null
    try {
        Assert-OnlineZipRawNames $stream
        $zip=New-Object IO.Compression.ZipArchive($stream,[IO.Compression.ZipArchiveMode]::Read,$true)
        $seen=@{};[long]$bytes=0
        if ($zip.Entries.Count -lt 1 -or $zip.Entries.Count -gt 100000) {Stop-Online 'archive_layout_invalid'}
        foreach ($entry in $zip.Entries) {
            $name=$entry.FullName;$leaf=$name.TrimEnd('/')
            if ($leaf -eq '' -or $name.Contains('\') -or $name.Contains(':') -or $name.StartsWith('/') -or
                $name.Contains('//') -or $seen.ContainsKey($leaf)) {Stop-Online 'archive_path_invalid'}
            foreach ($part in $leaf.Split('/')) {
                if ($part -in @('.','..') -or $part -match '[\x00-\x1f<>"|?*]' -or $part -match '[ .]$' -or
                    $part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)') {Stop-Online 'archive_path_invalid'}
            }
            $seen[$leaf]=$name.EndsWith('/')
            if (($entry.ExternalAttributes -shr 16 -band 61440) -eq 40960 -or ($entry.ExternalAttributes -band 1024) -ne 0) {Stop-Online 'archive_reparse'}
            $bytes+=$entry.Length
            if ($bytes -gt 2147483648 -or $entry.Length -gt 1073741824) {Stop-Online 'archive_size_invalid'}
        }
        foreach ($name in @($seen.Keys)) {
            $parent=$name
            while ($parent.Contains('/')) {
                $parent=$parent.Substring(0,$parent.LastIndexOf('/'))
                if ($seen.ContainsKey($parent) -and -not $seen[$parent]) {Stop-Online 'archive_path_invalid'}
            }
        }
        [void][IO.Directory]::CreateDirectory($Root)
        foreach ($entry in $zip.Entries) {
            $target=Join-Path $Root $entry.FullName.Replace('/','\')
            if ($entry.FullName.EndsWith('/')) {[void][IO.Directory]::CreateDirectory($target);continue}
            [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))
            $source=$entry.Open();$output=[IO.File]::Open($target,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
            try {$source.CopyTo($output)} finally {$output.Dispose();$source.Dispose()}
        }
    } finally {if ($null -ne $zip) {$zip.Dispose()};$stream.Dispose()}
}
function Set-OnlineChildEnvironment([Diagnostics.ProcessStartInfo]$Info,[string]$TemporaryRoot) {
    foreach ($key in @($Info.EnvironmentVariables.Keys)) {
        if ([string]$key -match '^(?i:PYTHON|COR_|CORECLR_|COMPLUS_|DOTNET_)') {$Info.EnvironmentVariables.Remove([string]$key)}
    }
    $Info.EnvironmentVariables['TEMP']=$TemporaryRoot
    $Info.EnvironmentVariables['TMP']=$TemporaryRoot
    # Keep native DLL/program resolution away from the operator's working directory and PATH.
    $Info.EnvironmentVariables['PATH']=(Join-Path $env:SystemRoot 'System32')+';'+$env:SystemRoot
}
function ConvertTo-OnlineArgument([string]$Value) {
    if ($Value -match '["\r\n\x00]' -or $Value.EndsWith('\')) {Stop-Online 'argument_invalid'}
    return '"'+$Value+'"'
}
function Invoke-OnlineAssembly([string]$Stage,[string]$Core,[string]$Python) {
    $cache=Join-Path $Stage 'providers'
    Assert-OnlineProviderCache $Core $cache
    $signature=Get-AuthenticodeSignature -LiteralPath $Python -ErrorAction Stop
    if ($signature.Status -ne 'Valid' -or $null -eq $signature.SignerCertificate -or
        $signature.SignerCertificate.GetNameInfo([Security.Cryptography.X509Certificates.X509NameType]::SimpleName,$false) -cne 'Python Software Foundation') {Stop-Online 'python_signature_invalid'}
    $work=Join-Path $Stage 'work'
    # The assembler owns exclusive creation of this child inside the already private stage.
    $info=New-Object Diagnostics.ProcessStartInfo
    $info.FileName=$Python;$info.UseShellExecute=$false;$info.CreateNoWindow=$true
    $info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true;$info.WorkingDirectory=$Core
    $info.Arguments='-I -B '+(ConvertTo-OnlineArgument (Join-Path $Core 'assemble.py'))+' --core-root '+(ConvertTo-OnlineArgument $Core)+' --work-root '+(ConvertTo-OnlineArgument $work)+' --cache '+(ConvertTo-OnlineArgument $cache)
    Set-OnlineChildEnvironment $info $Stage
    $result=[RackClick.Online20.Child]::Run($info,3600,65536)
    if ($result.Limited) {Stop-Online 'assembler_output_or_timeout_limit'}
    if ($result.ExitCode -ne 0) {Stop-Online 'assembler_failed'}
    try {$receipt=$result.Output | ConvertFrom-Json -ErrorAction Stop} catch {Stop-Online 'assembler_receipt_invalid'}
    if ($null -eq $receipt -or $receipt.success -isnot [bool] -or -not $receipt.success -or $receipt.code -cne 'online_assembled' -or
        $receipt.wrapperSha256 -cne $script:OnlineNativeSha) {Stop-Online 'assembler_receipt_invalid'}
    $wrapper=Join-Path $Stage 'work\.local\RackClick-Servidor-20.zip'
    Assert-OnlineNoReparse $wrapper
    if ((Get-OnlineFileHash $wrapper) -cne $script:OnlineNativeSha) {Stop-Online 'native_hash_mismatch'}
    # Independently verify the fixed extraction against the pinned archive. Ignore driver-returned paths.
    $native=Join-Path $Stage 'work\native20'
    Assert-OnlineExtractedTree $wrapper $native
    $launcher=Join-Path $native 'RackClick-Servidor-20\INICIAR.ps1'
    if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {Stop-Online 'native_launcher_missing'}
    return $launcher
}
function Assert-OnlineExtractedTree([string]$Archive,[string]$Root) {
    # Expand to another exclusive path first to apply all ZIP/path/reparse checks before comparison.
    $reference=Join-Path ([IO.Path]::GetDirectoryName($Root)) 'verified-native20'
    Expand-OnlineZip $Archive $reference
    Assert-OnlineNoReparse $Root
    $expectedTree=@(Get-ChildItem -LiteralPath $reference -Recurse -Force -ErrorAction Stop)
    $expected=@($expectedTree | Where-Object {-not $_.PSIsContainer})
    $actual=@(Get-ChildItem -LiteralPath $Root -Recurse -Force -ErrorAction Stop)
    foreach ($item in $actual) {Assert-OnlineNoReparse $item.FullName}
    if ($actual.Count -ne $expectedTree.Count -or @($actual | Where-Object {-not $_.PSIsContainer}).Count -ne $expected.Count) {Stop-Online 'native_tree_mismatch'}
    foreach ($directory in @($expectedTree | Where-Object {$_.PSIsContainer})) {
        $relative=$directory.FullName.Substring($reference.Length).TrimStart('\')
        if (-not (Test-Path -LiteralPath (Join-Path $Root $relative) -PathType Container)) {Stop-Online 'native_tree_mismatch'}
    }
    foreach ($item in $expected) {
        $relative=$item.FullName.Substring($reference.Length).TrimStart('\')
        $path=Join-Path $Root $relative
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
            (Get-OnlineFileHash $path) -cne (Get-OnlineFileHash $item.FullName)) {Stop-Online 'native_tree_mismatch'}
    }
}
function Invoke-OnlineNativeLauncher([string]$Launcher,[string]$Stage) {
    Assert-OnlineNoReparse $Launcher
    $info=New-Object Diagnostics.ProcessStartInfo
    $info.FileName=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $info.Arguments='-NoProfile -STA -ExecutionPolicy Bypass -File '+(ConvertTo-OnlineArgument $Launcher)
    $info.UseShellExecute=$false;$info.WorkingDirectory=[IO.Path]::GetDirectoryName($Launcher)
    Set-OnlineChildEnvironment $info $Stage
    $child=[Diagnostics.Process]::Start($info)
    if ($null -eq $child) {Stop-Online 'native_launch_failed'}
    $id=$child.Id;$child.Dispose()
    return $id
}
function Write-OnlineSummary([string]$Stage,$Summary) {
    $output=[IO.File]::Open((Join-Path $Stage 'online20-result.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try {$bytes=[Text.Encoding]::UTF8.GetBytes(($Summary|ConvertTo-Json -Compress));$output.Write($bytes,0,$bytes.Length);$output.Flush($true)} finally {$output.Dispose()}
}
function Invoke-OnlineInstall([string]$RequestedMode,[bool]$Accepted,[bool]$Unattended) {
    $coreLease=$null;$stage=$null;$confirmed=$false
    try {
        Assert-OnlineHost
        Assert-OnlineFreshHost
        Assert-OnlinePins
        if ($RequestedMode -eq 'Check') {
            $coreLease=Open-OnlineCore
            return [ordered]@{success=$true;code='online_checked';installed=$false}
        }
        Assert-OnlineAdmin
        Confirm-OnlineDownloads $Accepted $Unattended
        $confirmed=$true
        $coreLease=Open-OnlineCore
        $stage=New-OnlineStage
        $copy=Join-Path $stage 'RackClick-Core20.zip'
        $target=[IO.File]::Open($copy,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try {$coreLease.CopyTo($target)} finally {$target.Dispose()}
        if ((Get-OnlineFileHash $copy) -cne $script:OnlineCoreSha) {Stop-Online 'core_hash_mismatch'}
        $core=Join-Path $stage 'core'
        Expand-OnlineZip $copy $core
        $pythonArchive=Join-Path $stage 'python-3.12.3-embed-amd64.zip'
        Receive-OnlinePython $pythonArchive
        $pythonRoot=Join-Path $stage 'python'
        Expand-OnlineZip $pythonArchive $pythonRoot
        Receive-OnlineProviders $stage $core
        $launcher=Invoke-OnlineAssembly $stage $core (Join-Path $pythonRoot 'python.exe')
        $result=[ordered]@{success=$true;code='online_prepared';installed=$false;stage=$stage;wrapperSha256=$script:OnlineNativeSha}
        if ($RequestedMode -eq 'Install') {
            # Process creation is delegation only. The native GUI and its real result remain authoritative.
            $result.nativeProcessId=Invoke-OnlineNativeLauncher $launcher $stage
            $result.code='online_delegated'
        }
        Write-OnlineSummary $stage $result
        return $result
    } catch {
        $code=Get-OnlineErrorCode $_
        if ($confirmed -and $null -ne $stage) {
            try {Write-OnlineSummary $stage ([ordered]@{success=$false;code=$code;installed=$false;stage=$stage})} catch {}
        }
        Stop-Online $code
    } finally {if ($null -ne $coreLease -and $coreLease -is [IDisposable]) {$coreLease.Dispose()}}
}
if ($MyInvocation.InvocationName -ne '.') {
    $ErrorActionPreference='Stop'
    try {Invoke-OnlineInstall $Mode $AcceptDownloads.IsPresent $NonInteractive.IsPresent | ConvertTo-Json -Compress;exit 0}
    catch {
        $code=Get-OnlineErrorCode $_
        if ($code -eq 'admin_required') {Write-Host 'Abra PowerShell o INICIAR-RACKCLICK.cmd como administrador (Ejecutar como administrador).'}
        [ordered]@{success=$false;code=$code;installed=$false} | ConvertTo-Json -Compress
        exit 2
    }
}
