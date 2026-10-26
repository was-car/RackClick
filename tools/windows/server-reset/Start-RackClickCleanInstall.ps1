#requires -Version 5.1
[CmdletBinding()]
param([switch]$FunctionsOnly,[switch]$VerifyOnly)
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules'
# Replaced by the release producer, never read from a mutable sidecar.
$script:PayloadSha256='@@PAYLOAD_SHA256@@'
function Assert-CleanLocalPath([string]$Path) {
    if(-not[IO.Path]::IsPathRooted($Path)-or$Path.StartsWith('\\')-or[IO.Path]::GetFullPath($Path)-cne$Path){throw 'clean_local_path_required'}
    $cursor=$Path
    while($cursor){if(Test-Path -LiteralPath $cursor){if(((Get-Item -LiteralPath $cursor -Force -ErrorAction Stop).Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){throw 'clean_reparse_not_allowed'}};$cursor=[IO.Path]::GetDirectoryName($cursor)}
}
function New-CleanPrivateDirectory([string]$Path) {
    Assert-CleanLocalPath $Path
    if(Test-Path -LiteralPath $Path){throw 'clean_destination_exists'}
    $acl=New-Object Security.AccessControl.DirectorySecurity
    $acl.SetSecurityDescriptorSddlForm('O:BAG:SYD:P(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)')
    $null=[IO.Directory]::CreateDirectory($Path,$acl)
    return $Path
}
function Expand-CleanVerifiedPayload([string]$Archive,[string]$ExpectedSha256,[string]$Destination) {
    Assert-CleanLocalPath $Archive;Assert-CleanLocalPath $Destination
    if($ExpectedSha256-cnotmatch'^[a-f0-9]{64}$'-or(Test-Path -LiteralPath $Destination)){throw 'clean_archive_parameters_invalid'}
    Add-Type -AssemblyName System.IO.Compression
    $file=[IO.File]::Open($Archive,'Open','Read','Read')
    try{
        $sha=[Security.Cryptography.SHA256]::Create()
        try{$actual=([BitConverter]::ToString($sha.ComputeHash($file))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
        if($actual-cne$ExpectedSha256){throw 'clean_archive_hash_mismatch'}
        $file.Position=0;$zip=New-Object IO.Compression.ZipArchive($file,[IO.Compression.ZipArchiveMode]::Read,$true)
        try{
            $prefix='RackClick-Instalador/';$total=[long]0;$entries=@($zip.Entries)
            if($entries.Count-lt1-or$entries.Count-gt200){throw 'clean_archive_count_invalid'}
            $seen=New-Object 'Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
            foreach($entry in $entries){
                $name=$entry.FullName
                if(-not$name.StartsWith($prefix,[StringComparison]::Ordinal)-or$name.EndsWith('/')-or$name.IndexOf('\')-ge0){throw 'clean_archive_path_invalid'}
                $relative=$name.Substring($prefix.Length)
                if($relative-cnotmatch'^[a-zA-Z0-9_. /-]+$'-or$relative.Contains('//')-or$relative.StartsWith('/')-or$relative-match'(^|/)\.\.?(/|$)'-or$relative-match'(^|/)[^/]*[. ](/|$)'-or$relative-match'(^|/)(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|/|$)'-or-not$seen.Add($relative)){throw 'clean_archive_path_invalid'}
                $kind=($entry.ExternalAttributes-shr16)-band0xF000
                if($kind-notin@(0,0x8000)-or$entry.Length-lt0-or$entry.Length-gt250MB){throw 'clean_archive_entry_invalid'}
                $total+=$entry.Length;if($total-gt350MB){throw 'clean_archive_size_invalid'}
                $target=[IO.Path]::GetFullPath((Join-Path $Destination ($relative.Replace('/','\'))))
                if(-not$target.StartsWith($Destination+'\',[StringComparison]::Ordinal)-or$target.Length-ge250){throw 'clean_archive_target_invalid'}
            }
            # Validate everything, then create a completely new private tree.
            $null=New-CleanPrivateDirectory $Destination
            foreach($entry in $entries){
                $target=Join-Path $Destination ($entry.FullName.Substring($prefix.Length).Replace('/','\'))
                Assert-CleanLocalPath $target
                $null=[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))
                $input=$entry.Open();try{$output=[IO.File]::Open($target,'CreateNew','Write','None');try{$input.CopyTo($output);$output.Flush($true)}finally{$output.Dispose()}}finally{$input.Dispose()}
                if((Get-Item -LiteralPath $target).Length-ne$entry.Length){throw 'clean_archive_length_mismatch'}
            }
            return [pscustomobject]@{valid=$true;code='clean_payload_extracted';sha256=$actual;files=$entries.Count;bytes=$total;path=$Destination}
        }finally{$zip.Dispose()}
    }finally{$file.Dispose()}
}
function Show-CleanResetSummary($Plan) {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $form=New-Object Windows.Forms.Form;$form.Text='RackClick 05 - Preparar instalacion en servidor de aplicaciones';$form.Size=New-Object Drawing.Size(820,630);$form.StartPosition='CenterScreen';$form.MinimumSize=$form.Size
    $form.Font=New-Object Drawing.Font('Segoe UI',10)
    $text=New-Object Windows.Forms.TextBox;$text.Multiline=$true;$text.ReadOnly=$true;$text.ScrollBars='Both';$text.Location=New-Object Drawing.Point(16,16);$text.Size=New-Object Drawing.Size(770,480);$text.Anchor='Top,Bottom,Left,Right'
    $lines=New-Object Collections.Generic.List[string]
    $lines.Add('Se conservaran completas las dos carpetas anteriores de RackClick, con sus permisos y datos.')
    $lines.Add('No se necesitan marcadores de instalacion. No se borran bases ni se cambian cuentas.')
    foreach($hub in $Plan.hubs){$lines.Add('');if($hub.exists){$lines.Add('  Conservar: '+$hub.source);$lines.Add('  Como: '+$hub.destination)}else{$lines.Add('  No existe: '+$hub.source)}}
    $lines.Add('');$lines.Add('SE CONSERVA SIN MODIFICAR:')
    $lines.Add('  Todas las cuentas existentes; incluidas RackClickSvc y RackClickOperador.')
    $lines.Add('  El contenido y los permisos de las carpetas conservadas; otros programas y certificados.')
    $lines.Add('  El instalador creara carpetas, cuenta y base nuevas.')
    if(@($Plan.blockers).Count){$lines.Add('');$lines.Add('NO SE APLICARA: hay referencias o procesos que no permiten una retirada segura.');foreach($block in $Plan.blockers){$lines.Add('  '+$block)}}
    $text.Text=$lines-join[Environment]::NewLine;$form.Controls.Add($text)
    $go=New-Object Windows.Forms.Button;$go.Text='Conservar anteriores e instalar';$go.Location=New-Object Drawing.Point(16,515);$go.Size=New-Object Drawing.Size(360,46);$go.Anchor='Bottom,Left';$go.Enabled=(@($Plan.blockers).Count-eq0);$go.DialogResult='OK';$form.Controls.Add($go)
    $cancel=New-Object Windows.Forms.Button;$cancel.Text='Cerrar sin cambios';$cancel.Location=New-Object Drawing.Point(410,515);$cancel.Size=New-Object Drawing.Size(330,46);$cancel.Anchor='Bottom,Right';$cancel.DialogResult='Cancel';$form.Controls.Add($cancel);$form.CancelButton=$cancel
    try{return $form.ShowDialog()-eq'OK'}finally{$form.Dispose()}
}
function New-CleanVerificationEntry([string]$ScriptPath) {
    Assert-CleanLocalPath $ScriptPath
    if($ScriptPath-match'["\r\n]'){throw 'clean_entry_path_invalid'}
    $desktop=[Environment]::GetFolderPath('Desktop');Assert-CleanLocalPath $desktop
    $name='RackClick-VERIFICAR-05-'+[guid]::NewGuid().ToString('N').Substring(0,8)+'.cmd'
    $entry=Join-Path $desktop $name
    $literal=$ScriptPath.Replace("'","''")
    $command='$a=@(''-NoProfile'',''-STA'',''-ExecutionPolicy'',''Bypass'',''-File'',(''"''+'''+$literal+'''+''"''),''-VerifyInstallation'');Start-Process -FilePath ($env:SystemRoot+''\System32\WindowsPowerShell\v1.0\powershell.exe'') -ArgumentList $a -Verb RunAs'
    $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
    $data='@echo off'+"`r`n"+'"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -EncodedCommand '+$encoded+"`r`n"
    $file=[IO.File]::Open($entry,'CreateNew','Write','None');try{$bytes=[Text.Encoding]::ASCII.GetBytes($data);$file.Write($bytes,0,$bytes.Length);$file.Flush($true)}finally{$file.Dispose()}
    return $entry
}
function Export-CleanLauncherFailure($Record) {
    # Also works when the fixed archive cannot be opened, before any inner code runs.
    Add-Type -AssemblyName System.IO.Compression
    $desktop=[Environment]::GetFolderPath('Desktop');Assert-CleanLocalPath $desktop
    $path=Join-Path $desktop ('RackClick-Informe-Instalacion-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)+'.zip')
    $safe=[ordered]@{schemaVersion=4;kind='RackClickSanitizedInstallationReport';generatedUtc=[DateTime]::UtcNow.ToString('o');attemptCount=0;launcher=$Record}
    $file=[IO.File]::Open($path,'CreateNew','Write','None')
    try{$zip=New-Object IO.Compression.ZipArchive($file,[IO.Compression.ZipArchiveMode]::Create,$true);try{$entry=$zip.CreateEntry('INFORME.json');$stream=$entry.Open();try{$bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($safe|ConvertTo-Json -Depth 5));$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}}finally{$zip.Dispose()}}finally{$file.Dispose()}
    return $path
}
if($FunctionsOnly){return}
$principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if(-not$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
    try{if($PSCommandPath-match'["\r\n]'){throw 'clean_launcher_path_invalid'};$args=@('-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',('"'+$PSCommandPath+'"'));if($VerifyOnly){$args+='-VerifyOnly'};$p=Start-Process "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList $args -Verb RunAs -Wait -PassThru;exit $p.ExitCode}catch{exit 1}
}
if(-not[Environment]::Is64BitProcess-or[Threading.Thread]::CurrentThread.ApartmentState-ne'STA'){throw 'clean_windows_x64_sta_required'}
$session='';$operators='';$phase='verify';$reportPath=''
try{
    $archive=Join-Path $PSScriptRoot 'Servidor.zip'
    $id=[guid]::NewGuid().ToString('D')
    $session=Join-Path $env:LOCALAPPDATA ('RackClick\RecoverySessions\'+$id)
    $stage=Join-Path $env:LOCALAPPDATA ('RackClick\SetupPayloads\'+$id)
    $null=New-CleanPrivateDirectory $session
    $expanded=Expand-CleanVerifiedPayload $archive $script:PayloadSha256 $stage
    $operators=Join-Path $stage 'operators\server-install'
    . (Join-Path $operators 'RackClick.Setup.ps1')
    . (Join-Path $operators 'RackClick.Setup.Security.ps1')
    . (Join-Path $operators 'RackClick.Setup.Host.ps1')
    . (Join-Path $operators 'RackClick.Setup.Lifecycle.ps1')
    . (Join-Path $operators 'RackClick.Setup.Reset.ps1')
    . (Join-Path $operators 'RackClick.Setup.Namespace.ps1')
    $null=Assert-SetupPayload $stage
    if($VerifyOnly){Write-Output ($expanded|ConvertTo-Json -Compress);exit 0}
    $phase='host';$hostCheck=Get-SetupHostCompatibility
    Write-SetupJson (Join-Path $session 'host-result.json') $hostCheck
    if(-not$hostCheck.valid){throw ([string]$hostCheck.code)}
    $phase='inventory';$plan=Get-SetupNamespacePlan
    Write-SetupJson (Join-Path $session 'reset-plan.json') $plan
    if(-not(Show-CleanResetSummary $plan)){
        $code=if(@($plan.blockers).Count){'setup_reset_blocked_preserved'}else{'setup_reset_cancelled'}
        Write-SetupJson (Join-Path $session 'reset-result.json') @{schemaVersion=1;valid=$false;cleanupComplete=$false;exitCode=2;code=$code;remainingBlockers=$plan.blockers;preserved=$plan.preservedAccounts}
        if(@($plan.blockers).Count){throw $code}else{exit 2}
    }
    $phase='reset';$result=Invoke-SetupNamespacePlan -Plan $plan -JournalDirectory $session -Confirm:$false
    if($result.valid-ne$true-or$result.cleanupComplete-ne$true){throw 'setup_reset_not_complete'}
    $phase='install'
    $null=New-CleanVerificationEntry (Join-Path $operators 'Show-RackClickInstalledServer.ps1')
    & (Join-Path $operators 'Show-RackClickInstaller.ps1') -RecoverySessionDirectory $session
    exit $LASTEXITCODE
}catch{
    $code='clean_install_failed';if($_.Exception.Message-cmatch'^[a-z][a-z0-9_]{1,100}$'){$code=$_.Exception.Message}
    $record=@{schemaVersion=1;valid=$false;cleanupComplete=$false;exitCode=1;code=$code;stage=$phase;errorType=$_.Exception.GetType().FullName;failureLine=$_.InvocationInfo.ScriptLineNumber}
    if($session-and[IO.Directory]::Exists($session)){
        $path=Join-Path $session 'launcher-result.json';[IO.File]::WriteAllText($path,($record|ConvertTo-Json -Compress),(New-Object Text.UTF8Encoding($false)))
        if($operators-and(Test-Path -LiteralPath (Join-Path $operators 'Collect-RackClickInstallReport.ps1'))){try{$output=& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -STA -ExecutionPolicy Bypass -File (Join-Path $operators 'Collect-RackClickInstallReport.ps1') -Quiet -RecoverySessionDirectory $session;if($LASTEXITCODE-eq0){$report=($output-join"`n")|ConvertFrom-Json -ErrorAction Stop;if($report.code-ceq'report_exported'-and[IO.File]::Exists($report.zipPath)){$reportPath=$report.zipPath}}}catch{}}
    }
    if(-not$reportPath){try{$reportPath=Export-CleanLauncherFailure $record}catch{}}
    Add-Type -AssemblyName System.Windows.Forms
    $message='No se completo: '+$code+'. Los datos anteriores se conservan.'+[Environment]::NewLine
    if($code-ceq'setup_domain_controller_not_supported'){$message+='Este equipo es controlador de dominio de Active Directory. Instala RackClick en otra VM Windows Server, sin ese rol. No se ha iniciado la limpieza ni la creacion de cuentas.'+[Environment]::NewLine}
    elseif($code-ceq'setup_host_role_unverified'){$message+='No se pudo verificar el rol del equipo. No se ha iniciado la limpieza ni la creacion de cuentas.'+[Environment]::NewLine}
    if($reportPath){$message+='Informe creado en el Escritorio: '+$reportPath}else{$message+='Registro privado: '+$session}
    [Windows.Forms.MessageBox]::Show($message,'RackClick 05','OK','Error')|Out-Null
    exit 1
}
