#requires -Version 5.1
# Explicit elevated provisioning only. Importing this file has no side effects.
function Get-SetupMfaInitializationRequest {
    param($Manifest,[string]$InstallationId,[string]$ServiceSid)
    . (Join-Path $PSScriptRoot 'RackClick.MfaRuntime.ps1')
    $mfa=Get-ServerMfaProfile -Manifest $Manifest -InstallationId $InstallationId
    if(-not$mfa.enabled){throw 'setup_mfa_profile_required'}
    $reader=$null
    try{$reader=New-Object Security.Principal.SecurityIdentifier($ServiceSid)}catch{throw 'setup_mfa_reader_invalid'}
    if($reader.Value-cne$ServiceSid-or$ServiceSid-cnotmatch'^S-1-5-21-(\d+-){3}\d+$'-or$ServiceSid.EndsWith('-500')){throw 'setup_mfa_reader_invalid'}
    return @{instancesRoot=$mfa.instancesRoot;installationId=$mfa.installationId;readerSid=$ServiceSid}
}
function Set-SetupMfaChildEnvironment {
    param([Diagnostics.ProcessStartInfo]$StartInfo,[string]$DotNetRoot)
    # A provisioning child must not inherit startup hooks, profilers, configuration
    # aliases, PG credentials or diagnostic endpoints from the interactive shell.
    foreach($name in @($StartInfo.EnvironmentVariables.Keys)){
        if([string]$name-match'^(?i:DOTNET_|COMPlus_|COR_|CORECLR_|ASPNETCORE_|PG)' -or
           [string]$name-match'^(?i:ConnectionStrings|Bootstrap|Recovery|RackClick|MfaKeyStore|Kestrel)(?::|__|$)' -or
           [string]$name-in@('URLS','HTTP_PORTS','HTTPS_PORTS','PublicOrigin','DevelopmentLoopbackHttp')){
            $StartInfo.EnvironmentVariables.Remove([string]$name)
        }
    }
    $StartInfo.EnvironmentVariables['DOTNET_ROOT']=$DotNetRoot
    $StartInfo.EnvironmentVariables['DOTNET_MULTILEVEL_LOOKUP']='0'
    $StartInfo.EnvironmentVariables['DOTNET_EnableDiagnostics']='0'
    $StartInfo.EnvironmentVariables['DOTNET_CLI_TELEMETRY_OPTOUT']='1'
    $StartInfo.EnvironmentVariables['DOTNET_NOLOGO']='1'
    $StartInfo.EnvironmentVariables['DOTNET_GENERATE_ASPNET_CERTIFICATE']='false'
}
function Assert-SetupMfaInitializationReceipt {
    param([int]$ExitCode,[string]$StandardOutput,[string]$StandardError)
    # The approved CLI's success representation is a closed one-line contract.
    # Do not echo a failure body, paths or the exception into the public result.
    if($ExitCode-ne0-or$StandardError.Length-ne0-or$StandardOutput.Length-gt4096-or
       $StandardOutput.TrimEnd([char[]]"`r`n")-cne'{"status":"created","residue":"none"}'){
        throw 'setup_mfa_initialization_failed_preserved'
    }
}
function Set-SetupMfaContentAdministrativeRead {
    param([string]$InstancePath,[string]$ServiceSid)
    Assert-SetupAdministrator;Assert-SetupPath $InstancePath 'instance' -NativeHandleWalk
    # Only the public, immutable bundle content receives BA RX. Database files,
    # credentials and the separate security root keep their existing private ACL.
    $sid=New-Object Security.Principal.SecurityIdentifier($ServiceSid)
    if($sid.Value-cne$ServiceSid-or$ServiceSid-cnotmatch'^S-1-5-21-(\d+-){3}\d+$'-or$ServiceSid.EndsWith('-500')){throw 'setup_mfa_reader_invalid'}
    $content=Join-Path $InstancePath 'content'
    # Reuse the native ancestor/handle validation rather than a Get-Item walk:
    # immediately after sealing, BA cannot even read the instance attributes.
    $null=Read-SetupPreparedFile -InstancePath $InstancePath -RelativePath 'runtime/server-profile.json' -ServiceSid $ServiceSid
    Invoke-SetupSecurityPrivileges {
        # Non-inheriting attributes+traverse on the container only. This grants
        # neither directory listing nor data access to any private child.
        [RackClickSetupSecurityNative]::SetAcl($InstancePath,('O:SYG:SYD:P(A;OICI;FA;;;SY)(A;;0xA0;;;BA)(A;OICI;FRFX;;;'+$ServiceSid+')'))
        function Set-SetupMfaContentNode([string]$Path){
            [RackClickSetupSecurityNative]::SetAcl($Path,('O:SYG:SYD:P(A;OICI;FA;;;SY)(A;OICI;FRFX;;;BA)(A;OICI;FRFX;;;'+$ServiceSid+')'))
            $node=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
            if(($node.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){throw 'setup_mfa_content_reparse'}
            if($node.PSIsContainer){foreach($child in @(Get-ChildItem -LiteralPath $Path -Force -ErrorAction Stop)){Set-SetupMfaContentNode $child.FullName}}
        }
        Set-SetupMfaContentNode $content
    }
}
function Initialize-SetupMfaStore {
    param([string]$InstancePath,[string]$CodeRoot,[string]$InstallationId,[string]$ServiceSid,
          [string]$ExpectedManifestSha256,[string]$ExpectedBundleSha256)
    Assert-SetupAdministrator
    if($InstancePath-cne('C:\ProgramData\RackClick\Instances\'+$InstallationId+'\instance')-or
       $CodeRoot-cne('C:\Program Files\RackClick\'+$InstallationId)-or
       $ExpectedManifestSha256-cnotmatch'^[a-f0-9]{64}$'-or$ExpectedBundleSha256-cnotmatch'^[a-f0-9]{64}$'){
        throw 'setup_mfa_binding_invalid'
    }
    Assert-SetupNoReparse $CodeRoot;Assert-SetupNoReparse $InstancePath
    $profileBytes=Read-SetupPreparedFile -InstancePath $InstancePath -RelativePath 'runtime/server-profile.json' -ServiceSid $ServiceSid
    $digest=[Security.Cryptography.SHA256]::Create()
    try{$actual=([BitConverter]::ToString($digest.ComputeHash($profileBytes))).Replace('-','').ToLowerInvariant()}finally{$digest.Dispose()}
    if($actual-cne$ExpectedManifestSha256){throw 'setup_mfa_manifest_changed'}
    try{$profile=(New-Object Text.UTF8Encoding($false,$true)).GetString($profileBytes)|ConvertFrom-Json -ErrorAction Stop}catch{throw 'setup_mfa_profile_invalid'}
    $request=Get-SetupMfaInitializationRequest -Manifest $profile -InstallationId $InstallationId -ServiceSid $ServiceSid
    # Keep the source ZIP locked, and recheck every sealed content byte against its
    # pinned manifest. This happens after the standard account lost write access.
    . (Join-Path $PSScriptRoot '..\RackClick.OfflineBundle.ps1')
    $bundle=$null;$process=$null;$started=$false
    try{
        $bundle=Read-RackClickOfflineBundle -ArchivePath (Join-Path $CodeRoot 'RackClick.zip') -ExpectedArchiveSha256 $ExpectedBundleSha256
        if((Get-OfflineBundleExpectedSchema (Get-OfflineBundleApplicationProfile $bundle.manifest.applicationManifestSha256))-notin@(15,43)){throw 'setup_mfa_schema_required_15_or_43'}
        $content=Join-Path $InstancePath 'content'
        Assert-RackClickOfflineInstalledContent -Bundle $bundle -ContentPath $content
        $dotnet=Join-Path $content 'dependencies\dotnet\dotnet.exe'
        $assembly=Join-Path $content 'application\server\RackClick.Server.dll'
        $start=New-Object Diagnostics.ProcessStartInfo
        $start.FileName=$dotnet;$start.Arguments=(ConvertTo-SetupArgument $assembly)+' --mfa-keys-init'
        $start.WorkingDirectory=[IO.Path]::GetDirectoryName($assembly)
        $start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
        $start.RedirectStandardInput=$true;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
        Set-SetupMfaChildEnvironment -StartInfo $start -DotNetRoot ([IO.Path]::GetDirectoryName($dotnet))
        $process=New-Object Diagnostics.Process;$process.StartInfo=$start
        if(-not$process.Start()){throw 'setup_mfa_process_start_failed'};$started=$true
        $output=$process.StandardOutput.ReadToEndAsync();$errors=$process.StandardError.ReadToEndAsync()
        $process.StandardInput.WriteLine(($request|ConvertTo-Json -Compress));$process.StandardInput.Close()
        if(-not$process.WaitForExit(120000)){throw 'setup_mfa_initialization_timeout_preserved'}
        $process.WaitForExit()
        Assert-SetupMfaInitializationReceipt -ExitCode $process.ExitCode -StandardOutput $output.Result -StandardError $errors.Result
        return @{schemaVersion=1;valid=$true;exitCode=0;code='setup_mfa_store_created';residue='none';policy='grace_45_days';keysDisclosed=$false}
    }finally{
        if($null-ne$process){try{if($started-and-not$process.HasExited){$process.Kill();$null=$process.WaitForExit(5000)}}finally{$process.Dispose()}}
        if($null-ne$bundle){Close-RackClickOfflineBundle $bundle}
    }
}
