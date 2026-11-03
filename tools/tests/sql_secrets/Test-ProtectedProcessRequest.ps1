#requires -Version 5.1
param([string]$WorkPath)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$project=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$base=Join-Path $project '.local\sql-request-labs'
$work=[IO.Path]::GetFullPath($WorkPath)
if([IO.Path]::GetDirectoryName($work)-cne$base){throw 'only_new_process_fixture_allowed'}
. (Join-Path $project 'tools/windows/RackClick.Process.ps1')
$null=New-RackClickProcessPrivateDirectory $work
$ps=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$gate=Join-Path $project 'tools/windows/RackClick.Process.Gate.ps1'
$token=[guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N')
$handle=$null;$checks=0
function Assert-Focus($Condition){if(-not$Condition){throw 'protected_process_focus_failed'};$script:checks++}
function Invoke-InvalidGate([string]$Path){
    $start=New-Object Diagnostics.ProcessStartInfo
    $start.FileName=$ps;$start.UseShellExecute=$false;$start.CreateNoWindow=$true
    $start.RedirectStandardInput=$true;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
    $start.Arguments=(@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$gate,'-RequestPath',$Path,'-ProtectedRequest')|ForEach-Object{ConvertTo-RackClickProcessArgument $_})-join' '
    $p=New-Object Diagnostics.Process;$p.StartInfo=$start
    try{
        $null=$p.Start();$out=$p.StandardOutput.ReadToEndAsync();$err=$p.StandardError.ReadToEndAsync()
        $p.StandardInput.Write('G');$p.StandardInput.Close()
        if(-not$p.WaitForExit(15000)){$p.Kill();throw 'gate_timeout'}
        Assert-Focus ($p.ExitCode-eq2-and$out.Result.Length-eq0-and$err.Result.Length-eq0)
    }finally{$p.Dispose()}
}
try{
    $script='if([Console]::ReadLine() -cne $env:RACKCLICK_REQUEST_FOCUS){exit 9};[Console]::Write("accepted")'
    $handle=Start-RackClickOwnedProcess -Executable $ps -Arguments @('-NoProfile','-Command',$script) -WorkingDirectory $work -Environment @{RACKCLICK_REQUEST_FOCUS=$token} -InputText ($token+"`n") -LogDirectory $work -Label 'protected' -ProtectRequest
    $result=Wait-RackClickOwnedProcess $handle
    Assert-Focus ($result.exitCode-eq0-and$result.stdout-ceq'accepted'-and$result.stderr.Length-eq0)
    $path=$handle.RequestPath;$text=[IO.File]::ReadAllText($path);$v=$text|ConvertFrom-Json
    Assert-Focus (-not$text.Contains($token))
    Assert-Focus ($v.schemaVersion-eq2-and$v.kind-ceq'RackClickProtectedProcessRequest')
    Assert-Focus ((($v.PSObject.Properties.Name|Sort-Object)-join',')-ceq'ciphertext,kind,schemaVersion')
    # No plaintext fallback, even when a syntactically valid legacy request is supplied.
    [IO.File]::WriteAllText($path,'{"schemaVersion":1}')
    Invoke-InvalidGate $path
    Assert-Focus ([IO.File]::ReadAllText((Join-Path ([IO.Path]::GetDirectoryName($path)) 'gate-error.log'))-ceq'protected_process_failed')
    # Intact ciphertext is not reusable at another path/operation.
    $copy=New-RackClickProcessPrivateDirectory (Join-Path $work 'foreign-context')
    $copy=Join-Path $copy 'request.json';[IO.File]::WriteAllText($copy,$text)
    Invoke-InvalidGate $copy
    # Altered envelope at its original path also rejects before any child.
    $bytes=[Convert]::FromBase64String($v.ciphertext);$bytes[$bytes.Length-1]=$bytes[$bytes.Length-1]-bxor1
    $v.ciphertext=[Convert]::ToBase64String($bytes)
    [IO.File]::WriteAllText($path,($v|ConvertTo-Json -Compress));Invoke-InvalidGate $path
    [IO.File]::WriteAllText($path,$text)
}finally{if($null-ne$handle){Stop-RackClickOwnedProcess $handle;$handle.Process.Dispose()}}
@{valid=$true;code='protected_process_focus_pass';checks=$checks;dpapi='CurrentUser';serviceOrVmUsed=$false;secretValuesIncluded=$false}|ConvertTo-Json -Compress
