#requires -Version 5.1
param(
    [Parameter(Mandatory=$true)][string]$RuntimePath,
    [Parameter(Mandatory=$true)][string]$ProbeDirectory,
    [Parameter(Mandatory=$true)][string]$RequestPath,
    [Parameter(Mandatory=$true)][string]$ExpectedAssemblySha256,
    [Parameter(Mandatory=$true)][string]$ExpectedDepsSha256,
    [Parameter(Mandatory=$true)][string]$ExpectedRuntimeConfigSha256,
    [Parameter(Mandatory=$true)][string]$ExpectedRequestSha256
)
$ErrorActionPreference='Stop'
$handles=New-Object Collections.Generic.List[IO.FileStream]
$child=$null;$started=$false
try {
    if($env:COMPUTERNAME-ieq'LEAO'){throw 'host_excluded'}
    if([Security.Principal.WindowsIdentity]::GetCurrent().User.Value-cne'S-1-5-18'){throw 'system_required'}
    function Assert-ProbePath([string]$Path) {
        if(-not[IO.Path]::IsPathRooted($Path)){throw 'path_invalid'}
        $cursor=[IO.Path]::GetFullPath($Path)
        while($cursor){
            if(Test-Path -LiteralPath $cursor){
                $item=Get-Item -LiteralPath $cursor -Force
                if(($item.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){throw 'reparse_rejected'}
            }
            $cursor=[IO.Path]::GetDirectoryName($cursor)
        }
    }
    function Hold-ProbeFile([string]$Path,[string]$Expected) {
        Assert-ProbePath $Path
        if($Expected-cnotmatch'^[a-f0-9]{64}$'){throw 'hash_invalid'}
        $held=[IO.File]::Open($Path,'Open','Read','Read')
        $handles.Add($held)
        $digest=[Security.Cryptography.SHA256]::Create()
        try{$actual=([BitConverter]::ToString($digest.ComputeHash($held))).Replace('-','').ToLowerInvariant()}finally{$digest.Dispose()}
        $held.Position=0
        if($actual-cne$Expected){throw 'hash_mismatch'}
        return $held
    }
    Assert-ProbePath $RuntimePath
    $dll=Join-Path $ProbeDirectory 'RackClick.MfaAclProbe.dll'
    $null=Hold-ProbeFile $dll $ExpectedAssemblySha256
    $null=Hold-ProbeFile (Join-Path $ProbeDirectory 'RackClick.MfaAclProbe.deps.json') $ExpectedDepsSha256
    $null=Hold-ProbeFile (Join-Path $ProbeDirectory 'RackClick.MfaAclProbe.runtimeconfig.json') $ExpectedRuntimeConfigSha256
    $request=Hold-ProbeFile $RequestPath $ExpectedRequestSha256
    if($request.Length-gt65536){throw 'input_invalid'}
    $reader=New-Object IO.StreamReader($request,(New-Object Text.UTF8Encoding($false,$true)),$true,1024,$true)
    try{$inputText=$reader.ReadToEnd()}finally{$reader.Dispose()}
    $start=New-Object Diagnostics.ProcessStartInfo
    $start.FileName=$RuntimePath;$start.Arguments='"'+$dll+'" --measure'
    $start.WorkingDirectory=$ProbeDirectory
    $start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
    $start.RedirectStandardInput=$true;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
    foreach($name in @($start.EnvironmentVariables.Keys)){
        if([string]$name-match'^(?i:DOTNET_|CORECLR_|COR_|COMPlus_|OTEL_|ASPNETCORE_|APPDOMAIN_MANAGER_|ConnectionStrings|MfaKeyStore|SqlSecret|ENABLE_NOTIFICATION_PROFILER)'){
            $start.EnvironmentVariables.Remove([string]$name)
        }
    }
    $start.EnvironmentVariables['DOTNET_ROOT']=[IO.Path]::GetDirectoryName($RuntimePath)
    $start.EnvironmentVariables['DOTNET_EnableDiagnostics']='0'
    $start.EnvironmentVariables['DOTNET_MULTILEVEL_LOOKUP']='0'
    $start.EnvironmentVariables['DOTNET_ROLL_FORWARD']='Disable'
    $start.EnvironmentVariables['DOTNET_ROLL_FORWARD_TO_PRERELEASE']='0'
    $start.EnvironmentVariables['DOTNET_CLI_TELEMETRY_OPTOUT']='1'
    $start.EnvironmentVariables['DOTNET_NOLOGO']='1'
    $child=New-Object Diagnostics.Process;$child.StartInfo=$start
    if(-not$child.Start()){throw 'probe_start_failed'};$started=$true
    $output=$child.StandardOutput.ReadToEndAsync();$errorOutput=$child.StandardError.ReadToEndAsync()
    $child.StandardInput.Write($inputText);$child.StandardInput.Close()
    if(-not$child.WaitForExit(120000)){throw 'probe_timeout'}
    $child.WaitForExit()
    if(-not[string]::IsNullOrWhiteSpace($errorOutput.Result)){throw 'probe_process_failed'}
    $line=$output.Result.Trim()
    if($line.Contains("`n")-or$line.Contains("`r")){throw 'probe_output_invalid'}
    $decoded=$line|ConvertFrom-Json -ErrorAction Stop
    if($decoded.schemaVersion-ne1-or$decoded.status-cnotin@('verified','failed')){throw 'probe_output_invalid'}
    if(($child.ExitCode-eq0)-ne($decoded.status-ceq'verified')){throw 'probe_output_invalid'}
    [Console]::WriteLine($line)
    exit $child.ExitCode
} catch {
    $allowed=@('host_excluded','system_required','path_invalid','reparse_rejected','hash_invalid','hash_mismatch','input_invalid','probe_start_failed','probe_timeout','probe_process_failed','probe_output_invalid')
    $code=if($_.Exception.Message-cin$allowed){$_.Exception.Message}else{'probe_wrapper_failed'}
    [Console]::WriteLine((@{schemaVersion=1;status='failed';code=$code;serviceOperations=0;keysRead=$false;aclsChanged=0}|ConvertTo-Json -Compress))
    exit 1
} finally {
    if($null-ne$child){try{if($started-and-not$child.HasExited){$child.Kill();$null=$child.WaitForExit(5000)}}finally{$child.Dispose()}}
    foreach($handle in $handles){$handle.Dispose()}
}
