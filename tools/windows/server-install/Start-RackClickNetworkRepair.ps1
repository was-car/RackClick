#requires -Version 5.1
[CmdletBinding()]
param([switch]$FunctionsOnly)
function ConvertTo-RcRepairBundleArgument([string]$Value){
    if($Value.Contains([char]0)-or$Value.Contains("`r")-or$Value.Contains("`n")){throw 'network_bundle_child_invalid'}
    $escaped=[regex]::Replace($Value,'(\\*)"','$1$1\"');$escaped=[regex]::Replace($escaped,'(\\+)$','$1$1')
    return '"'+$escaped+'"'
}
function Invoke-RcRepairBundleStage([string]$Script,[string[]]$Arguments){
    $exe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $info=New-Object Diagnostics.ProcessStartInfo;$info.FileName=$exe;$info.UseShellExecute=$false;$info.CreateNoWindow=$true;$info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
    $parts=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$Script)+$Arguments
    $info.Arguments=($parts|ForEach-Object{ConvertTo-RcRepairBundleArgument $_})-join' '
    $child=[Diagnostics.Process]::Start($info);$stderr=$null
    try{
        $outputTask=$child.StandardOutput.ReadToEndAsync();$errorTask=$child.StandardError.ReadToEndAsync()
        $child.WaitForExit();$text=$outputTask.GetAwaiter().GetResult();$stderr=$errorTask.GetAwaiter().GetResult();$exit=$child.ExitCode
        if($stderr.Length-ne0){throw 'network_bundle_child_invalid'}
    }finally{$stderr=$null;$child.Dispose()}
    if($text.Length-gt65536){throw 'network_bundle_child_invalid'}
    try{$report=ConvertFrom-Json -InputObject $text -ErrorAction Stop}catch{throw 'network_bundle_child_invalid'}
    if($null-eq$report-or$report.schemaVersion-ne1-or$report.valid-isnot[bool]-or$report.exitCode-isnot[int]-or$report.exitCode-ne$exit){throw 'network_bundle_child_invalid'}
    return @{exitCode=$exit;report=$report}
}
function Invoke-RcRepairBundleSequence([string]$Directory,[string]$NetworkHash){
    $network=Join-Path $Directory 'RackClick-Cambiar-IP-02.ps1'
    Write-Host '1/2: Reparando el intento de red pendiente. Se conservan los datos y las cuentas.'
    $repair=Invoke-RcRepairBundleStage (Join-Path $Directory 'Repair-RackClickNetworkTransaction.ps1') @('-NetworkScriptPath',$network,'-NetworkScriptSha256',$NetworkHash)
    $answer=[ordered]@{schemaVersion=1;valid=$false;success=$false;exitCode=2;code='network_bundle_repair_failed';stage='repair';productAdopted=$false;repair=$repair.report;network=$null}
    if($repair.exitCode-ne0-or-not$repair.report.valid-or$repair.report.code-cnotin@('network_repair_verified','network_repair_already_restored')){return $answer}
    Write-Host '2/2: Aplicando 192.168.250.78/24 y comprobando servicio, HTTPS y un backup nuevo.'
    $changed=Invoke-RcRepairBundleStage $network @('-BindAddress','192.168.250.78','-AllowedSubnet','192.168.250.0/24')
    $answer.network=$changed.report;$answer.stage='network';$answer.code='network_bundle_change_failed'
    if($changed.exitCode-eq0-and$changed.report.valid-and$changed.report.success-and$changed.report.code-ceq'network_change_verified'){$answer.valid=$true;$answer.success=$true;$answer.exitCode=0;$answer.code='network_bundle_verified';$answer.stage='verified';$answer.publicOrigin='https://192.168.250.78:5443'}
    elseif($changed.exitCode-eq0-and$changed.report.valid-and$changed.report.code-ceq'network_already_configured'){$answer.valid=$true;$answer.code='network_bundle_readiness_not_checked'}
    return $answer
}
if($FunctionsOnly){return}
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$result=[ordered]@{schemaVersion=1;valid=$false;success=$false;exitCode=2;code='network_bundle_failed';stage='preflight';productAdopted=$false}
$held=New-Object Collections.ArrayList
try{
    if($PSVersionTable.PSEdition-cne'Desktop'-or$PSVersionTable.PSVersion.Major-ne5-or-not[Environment]::Is64BitProcess-or-not([Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'network_bundle_elevated_winps51_x64_required'}
    $directory=[IO.Path]::GetFullPath($PSScriptRoot);if($directory.StartsWith('\\')){throw 'network_bundle_path_invalid'}
    $pins=@{'RackClick-Cambiar-IP-02.ps1'='@@NETWORK_SHA256@@';'Repair-RackClickNetworkTransaction.ps1'='@@REPAIR_SHA256@@'}
    foreach($name in $pins.Keys){
        $path=Join-Path $directory $name;$cursor=$path
        while($cursor){$item=Get-Item -LiteralPath $cursor -Force -ErrorAction Stop;if(($item.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){throw 'network_bundle_path_invalid'};$cursor=[IO.Path]::GetDirectoryName($cursor)}
        $file=[IO.File]::Open($path,'Open','Read','Read');$held.Add($file)|Out-Null
        if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()-cne$pins[$name]){throw 'network_bundle_hash_mismatch'}
    }
    $result=Invoke-RcRepairBundleSequence $directory $pins['RackClick-Cambiar-IP-02.ps1']
}catch{if($_.Exception.Message-cin@('network_bundle_elevated_winps51_x64_required','network_bundle_path_invalid','network_bundle_hash_mismatch','network_bundle_child_invalid')){$result.code=$_.Exception.Message};$result.errorHResult=$_.Exception.HResult}
finally{foreach($file in $held){$file.Dispose()}}
$reportFile=$null
try{
    $desktop=[Environment]::GetFolderPath('DesktopDirectory')
    if([IO.Directory]::Exists($desktop)){
        $reportFile=Join-Path $desktop ('RackClick-Resultado-Red-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)+'.json')
        $result.reportPath=$reportFile;$bytes=[Text.Encoding]::UTF8.GetBytes(($result|ConvertTo-Json -Depth 12 -Compress));$out=[IO.File]::Open($reportFile,'CreateNew','Write','None');try{$out.Write($bytes,0,$bytes.Length);$out.Flush($true)}finally{$out.Dispose()}
    }
}catch{$result.reportSaved=$false}
$result|ConvertTo-Json -Depth 12 -Compress
exit $result.exitCode
