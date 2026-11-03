#requires -Version 5.1
param([string]$RequestPath='', [switch]$ProtectedRequest,[switch]$EphemeralRequest)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
# Crucially: no request read, executable start or helper import before the gate opens.
if ([Console]::In.Read() -ne 71) { exit 2 }
. (Join-Path $PSScriptRoot 'RackClick.Process.ps1')
$process=$null; $outStream=$null; $errStream=$null; $code=2; $private=$null;$bytes=$null
try {
    $RequestPath=Get-RackClickProcessPath $RequestPath
    Assert-RackClickProcessPrivateAcl $RequestPath
    $private=[IO.Path]::GetDirectoryName($RequestPath)
    Assert-RackClickProcessPrivateAcl $private
    if ([IO.Path]::GetFileName($RequestPath) -cne 'request.json' -or (Get-Item -LiteralPath $RequestPath).Length -gt 16777216) { Stop-RackClickProcessError 'gate_request_invalid' }
    if($EphemeralRequest){
        if(-not$ProtectedRequest){Stop-RackClickProcessError 'gate_request_invalid'}
        $requestStream=New-Object IO.FileStream($RequestPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::Read-bor[IO.FileShare]::Delete),4096,[IO.FileOptions]::DeleteOnClose)
        $requestReader=$null
        try{$requestReader=New-Object IO.StreamReader($requestStream,(New-Object Text.UTF8Encoding($false,$true)));$request=$requestReader.ReadToEnd()|ConvertFrom-Json}
        finally{if($null-ne$requestReader){$requestReader.Dispose()};$requestStream.Dispose()}
    }else{$request=[IO.File]::ReadAllText($RequestPath) | ConvertFrom-Json}
    if($ProtectedRequest){
        if((($request.PSObject.Properties.Name|Sort-Object)-join ',')-cne'ciphertext,kind,schemaVersion'-or
           $request.schemaVersion-isnot[int]-or$request.schemaVersion-ne2-or$request.kind-cne'RackClickProtectedProcessRequest'-or
           $request.ciphertext-isnot[string]-or$request.ciphertext.Length-gt16777216){Stop-RackClickProcessError 'gate_request_invalid'}
        Add-Type -AssemblyName System.Security
        $plain=$null
        try{
            $entropy=[Text.Encoding]::UTF8.GetBytes('RackClick/Process/request/v1'+"`n"+$RequestPath)
            $plain=[Security.Cryptography.ProtectedData]::Unprotect([Convert]::FromBase64String($request.ciphertext),$entropy,[Security.Cryptography.DataProtectionScope]::CurrentUser)
            if($plain.Length-gt16777216){Stop-RackClickProcessError 'gate_request_invalid'}
            $request=(New-Object Text.UTF8Encoding($false,$true)).GetString($plain)|ConvertFrom-Json
        }finally{if($null-ne$plain){[Array]::Clear($plain,0,$plain.Length)}}
    }
    if ($request.schemaVersion -ne 1) { Stop-RackClickProcessError 'gate_request_invalid' }
    $executable=Get-RackClickProcessPath $request.executable
    $working=Get-RackClickProcessPath $request.workingDirectory
    Assert-RackClickProcessNoReparse $executable; Assert-RackClickProcessNoReparse $working
    $start=New-Object Diagnostics.ProcessStartInfo
    $start.FileName=$executable; $start.WorkingDirectory=$working
    $start.Arguments=(@($request.arguments) | ForEach-Object { ConvertTo-RackClickProcessArgument $_ }) -join ' '
    $start.UseShellExecute=$false; $start.CreateNoWindow=$true; $start.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
    $start.RedirectStandardInput=$true; $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
    foreach ($property in $request.environment.PSObject.Properties) {
        if ($property.Name -notmatch '^[a-zA-Z_][a-zA-Z0-9_]*$') { Stop-RackClickProcessError 'gate_environment_invalid' }
        if ($null -eq $property.Value) { $start.EnvironmentVariables.Remove($property.Name) }
        else { $start.EnvironmentVariables[$property.Name]=[string]$property.Value }
    }
    $outStream=[IO.File]::Open((Join-Path $private 'stdout.log'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    $errStream=[IO.File]::Open((Join-Path $private 'stderr.log'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    $process=New-Object Diagnostics.Process; $process.StartInfo=$start
    if (-not $process.Start()) { Stop-RackClickProcessError 'gate_child_start_failed' }
    $copyOut=$process.StandardOutput.BaseStream.CopyToAsync($outStream)
    $copyErr=$process.StandardError.BaseStream.CopyToAsync($errStream)
    $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes([string]$request.inputText)
    if ($bytes.Length -ne 0) { $process.StandardInput.BaseStream.Write($bytes,0,$bytes.Length); $process.StandardInput.BaseStream.Flush() }
    $process.StandardInput.Close()
    $process.WaitForExit(); $copyOut.GetAwaiter().GetResult(); $copyErr.GetAwaiter().GetResult()
    $outStream.Flush($true); $errStream.Flush($true); $code=$process.ExitCode
} catch {
    if ($null -ne $private) { try { $failureText=if($ProtectedRequest){'protected_process_failed'}else{$_.Exception.ToString()};[IO.File]::WriteAllText((Join-Path $private 'gate-error.log'),$failureText,(New-Object Text.UTF8Encoding($false))) } catch {} }
} finally {
    if($ProtectedRequest-and$null-ne$bytes){[Array]::Clear($bytes,0,$bytes.Length)}
    if ($null -ne $outStream) { $outStream.Dispose() }
    if ($null -ne $errStream) { $errStream.Dispose() }
    if ($null -ne $process) { $process.Dispose() }
}
exit $code
