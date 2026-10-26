#requires -Version 5.1
[CmdletBinding()]
param([switch]$ValidateLayout,[switch]$FunctionsOnly,[string]$RecoverySessionDirectory='')
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules'
. (Join-Path $PSScriptRoot 'RackClick.Setup.Process.ps1')
$script:setupUiSourceRoot=$PSScriptRoot
function ConvertTo-SetupUiArgument([string]$Value) {
    if ($Value.Contains('"') -or $Value.Contains("`r") -or $Value.Contains("`n")) {throw 'invalid_process_argument'}
    return '"'+$Value+'"'
}
function Format-SetupUiFailure($Result,[string]$Folder) {
    if($null-ne$Result-and$Result.code-ceq'setup_domain_controller_not_supported'){return 'Este equipo es controlador de dominio. RackClick requiere otra VM Windows Server sin ese rol. No se ha creado ninguna cuenta por este intento. Informe privado: '+$Folder}
    if($null-ne$Result-and$Result.code-ceq'setup_host_role_unverified'){return 'No se pudo verificar el rol del equipo. No se han creado cuentas. Informe privado: '+$Folder}
    if($null-ne$Result-and$Result.code-is[string]-and$Result.code-ceq'setup_child_failed_preserved'-and
        $Result.stage-is[string]-and$Result.stage-ceq'prepare'-and
        $null-ne$Result.PSObject.Properties['childCode']-and$Result.childCode-is[string]-and$Result.childCode-ceq'preparation_recovery_username_exists'){
        return 'El administrador de recuperacion ya existe en el backup. Usa un nombre nuevo para el administrador de RackClick. Se conservan los usuarios de la copia. Informe privado: '+$Folder
    }
    $code='installer_result_not_confirmed';$where='etapa desconocida'
    if($null-ne$Result){
        if([string]$Result.code-cmatch'^[a-zA-Z0-9_\-]{1,100}$'){$code=[string]$Result.code}
        $stages=@{preflight='comprobacion inicial';verify='verificacion de archivos';prerequisite='Visual C++';account='creacion de cuenta';copy='copia del programa';prepare='preparacion de PostgreSQL';permissions='permisos';service='registro del servicio';readiness='comprobacion HTTPS';backup='backup inicial';scheduled_backup='tareas programadas';awaiting_reboot='verificacion del reinicio'}
        if($stages.ContainsKey([string]$Result.stage)){$where=$stages[[string]$Result.stage]}
        if($Result.failureLine-is[int]-and$Result.failureLine-gt0-and$Result.failureLine-le1000000){$where+=' (linea '+$Result.failureLine+')'}
    }
    return 'Fallo en '+$where+': '+$code+".`r`n"+'Informe privado: '+$Folder
}
function Test-SetupUiAdmin {
    $p=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
function Start-SetupUiTrackedProcess([string[]]$Arguments,[string]$WorkingDirectory,[string]$StandardOutput,[string]$StandardError) {
    Initialize-SetupChildProcessNative
    $process=Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -RedirectStandardOutput $StandardOutput -RedirectStandardError $StandardError -PassThru -WindowStyle Hidden
    $tracked=@{process=$process;handle=$null;trackingFailed=$false}
    try{$tracked.handle=Open-SetupChildProcess $process.Id}catch{$tracked.trackingFailed=$true}
    return $tracked
}
function Test-SetupUiTrackedProcessComplete($Tracked) {
    if($null-eq$Tracked-or$null-eq$Tracked.process){return $true}
    if($null-ne$Tracked.handle){return (Wait-SetupChildProcess $Tracked.handle 0)}
    # Never infer a success code from this fallback. It only avoids losing a
    # running process if the immediate native-handle request was denied.
    try{return $Tracked.process.HasExited}catch{return $false}
}
function Get-SetupUiTrackedExitCode($Tracked) {
    if($null-eq$Tracked-or$null-eq$Tracked.handle){throw 'installer_native_exit_unavailable'}
    return (Get-SetupChildProcessExitCode $Tracked.handle)
}
function Close-SetupUiTrackedProcess($Tracked) {
    if($null-eq$Tracked){return}
    try{if($null-ne$Tracked.handle){$Tracked.handle.Dispose();$Tracked.handle=$null}}finally{if($null-ne$Tracked.process){$Tracked.process.Dispose();$Tracked.process=$null}}
}
function Get-SetupUiBrokerOutcome($Result,[uint32]$NativeExitCode) {
    if($null-eq$Result-or$Result.valid-isnot[bool]-or-not$Result.valid-or$Result.exitCode-isnot[int]-or$Result.exitCode-ne$NativeExitCode){return 'failed'}
    if($NativeExitCode-eq0-and$Result.success-is[bool]-and$Result.success-and$Result.rebootVerified-is[bool]-and$Result.rebootVerified){return 'verified'}
    if($NativeExitCode-eq3-and$Result.installedReady-is[bool]-and$Result.installedReady-and$Result.stage-ceq'awaiting_reboot'){return 'awaiting_reboot'}
    return 'failed'
}
function Start-SetupUiReportExport($UiState,[string]$RecoveryDirectory='') {
    $id=[guid]::Empty
    if(-not[guid]::TryParseExact([string]$UiState.attemptId,'D',[ref]$id)-or$UiState.attemptId-cne$id.ToString('D')){throw 'installer_report_attempt_invalid'}
    $collector=Join-Path $script:setupUiSourceRoot 'Collect-RackClickInstallReport.ps1'
    if(-not[IO.File]::Exists($collector)){throw 'installer_report_collector_missing'}
    $arguments=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(ConvertTo-SetupUiArgument $collector),'-Quiet','-AttemptId',$UiState.attemptId)
    if($RecoveryDirectory){$arguments+=@('-RecoverySessionDirectory',(ConvertTo-SetupUiArgument $RecoveryDirectory))}
    $UiState.reportOutput=Join-Path $UiState.folder 'automatic-report.stdout.log'
    $UiState.reportExitedPolls=0
    $UiState.reportDeadlineUtc=[DateTime]::UtcNow.AddSeconds(60)
    $UiState.reportProcess=Start-SetupUiTrackedProcess $arguments $script:setupUiSourceRoot $UiState.reportOutput (Join-Path $UiState.folder 'automatic-report.stderr.log')
}
function Test-SetupUiReportDeadlineExpired($UiState) {
    return ($UiState.reportDeadlineUtc-is[DateTime]-and[DateTime]::UtcNow-ge$UiState.reportDeadlineUtc)
}
function Get-SetupUiDesktopPath {return [Environment]::GetFolderPath('Desktop')}
function Complete-SetupUiReportExport($UiState) {
    try {
        if((Get-SetupUiTrackedExitCode $UiState.reportProcess)-ne0){throw 'installer_report_export_failed'}
        # Collector publishes JSON then exits; the timer never blocks on IO drain.
        if(-not[IO.File]::Exists($UiState.reportOutput)-or(Get-Item -LiteralPath $UiState.reportOutput).Length-gt32768){throw 'installer_report_receipt_invalid'}
        $receipt=[IO.File]::ReadAllText($UiState.reportOutput)|ConvertFrom-Json -ErrorAction Stop
        $desktop=Get-SetupUiDesktopPath;$path=[string]$receipt.zipPath
        if($receipt.valid-isnot[bool]-or-not$receipt.valid-or$receipt.exitCode-isnot[int]-or$receipt.exitCode-ne0-or$receipt.code-cne'report_exported'-or$receipt.attemptId-cne$UiState.attemptId-or[IO.Path]::GetDirectoryName($path)-cne$desktop-or[IO.Path]::GetFileName($path)-cnotmatch'^RackClick-Informe-Instalacion-\d{8}T\d{6}Z-[a-f0-9]{8}\.zip$'-or-not[IO.File]::Exists($path)){throw 'installer_report_receipt_invalid'}
        return 'Informe automatico en el Escritorio: '+$path
    } finally {Close-SetupUiTrackedProcess $UiState.reportProcess;$UiState.reportProcess=$null}
}
function Test-SetupUiReportReceiptReadable([string]$Path) {
    try {
        if(-not[IO.File]::Exists($Path)){return $false}
        $length=(Get-Item -LiteralPath $Path).Length
        if($length-lt2-or$length-gt32768){return $false}
        $value=[IO.File]::ReadAllText($Path)|ConvertFrom-Json -ErrorAction Stop
        return ($value-is[pscustomobject])
    }catch{return $false}
}
if($FunctionsOnly){return}
if(-not $ValidateLayout -and -not (Test-SetupUiAdmin)) {
    try {
        $elevatedArguments=@('-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',(ConvertTo-SetupUiArgument $PSCommandPath))
        if($RecoverySessionDirectory){$elevatedArguments+=@('-RecoverySessionDirectory',(ConvertTo-SetupUiArgument $RecoverySessionDirectory))}
        $child=Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList $elevatedArguments -Verb RunAs -Wait -PassThru
        exit $child.ExitCode
    } catch {Write-Error 'No se pudo abrir el instalador con permisos de administrador.';exit 1}
}
if(-not [Environment]::Is64BitProcess -or [Threading.Thread]::CurrentThread.ApartmentState -ne 'STA') {throw 'installer_requires_windows_x64_sta'}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
function New-SetupUiPrivatePlan($Plan) {
    $root=Join-Path $env:LOCALAPPDATA 'RackClick\Setup'
    $cursor=$root
    while($cursor){if(Test-Path -LiteralPath $cursor){if(((Get-Item -LiteralPath $cursor -Force).Attributes-band[IO.FileAttributes]::ReparsePoint)-ne 0){throw 'plan_reparse_not_allowed'}};$cursor=[IO.Path]::GetDirectoryName($cursor)}
    $null=[IO.Directory]::CreateDirectory($root)
    $folder=Join-Path $root $Plan.id
    if(Test-Path -LiteralPath $folder){throw 'plan_destination_exists'}
    $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $acl=New-Object Security.AccessControl.DirectorySecurity
    $acl.SetSecurityDescriptorSddlForm(('O:'+ $sid +'G:SYD:P(A;OICI;FA;;;'+$sid+')(A;OICI;FA;;;SY)'))
    $null=[IO.Directory]::CreateDirectory($folder,$acl)
    $path=Join-Path $folder 'plan.json'
    $stream=[IO.File]::Open($path,'CreateNew','Write','None')
    try{$bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($Plan|ConvertTo-Json -Depth 4 -Compress));$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
    return @{folder=$folder;path=$path}
}
$defaultIp=''
try {$defaultIp=@(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop|Where-Object {$_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254.*' -and $_.AddressState -eq 'Preferred'}|Select-Object -ExpandProperty IPAddress)[0]}catch{}
if(-not $defaultIp){$defaultIp='192.168.250.76'}
$defaultSubnet=($defaultIp -replace '\.\d+$','.0')+'/24'
$form=New-Object Windows.Forms.Form
$form.Text='RackClick - Instalacion del servidor';$form.Size=New-Object Drawing.Size(790,825)
$form.StartPosition='CenterScreen';$form.MinimumSize=$form.Size;$form.AutoScaleMode='Dpi'
$form.Font=New-Object Drawing.Font('Segoe UI',10)
$top=New-Object Windows.Forms.Label
$top.Location=New-Object Drawing.Point(18,12);$top.Size=New-Object Drawing.Size(735,65)
$top.Text='Instalacion nueva de RackClick: aplicacion, PostgreSQL privado y servicio Windows. Los usuarios trabajan desde el navegador. No cambia IP ni DNS. Revisa el nombre y la red antes de instalar.'
$form.Controls.Add($top)
$fields=[ordered]@{
 bindAddress=@('IP de escucha del servidor',$defaultIp)
 publicHost=@('Nombre DNS o IP para el navegador',$defaultIp)
 httpsPort=@('Puerto HTTPS','5443')
 postgresPort=@('Puerto PostgreSQL local','55441')
 allowedSubnet=@('Red autorizada (propuesta editable)',$defaultSubnet)
 systemhaus=@('Nombre de Systemhaus','Systemhaus')
 bootstrapUser=@('Administrador de RackClick','Wascar')
 serviceName=@('Nombre del servicio Windows','RackClick')
 accountName=@('Cuenta Windows estandar del servicio','RackClickSvc')
}
$inputs=@{};$y=83
foreach($entry in $fields.GetEnumerator()){
 $label=New-Object Windows.Forms.Label;$label.Text=$entry.Value[0];$label.Location=New-Object Drawing.Point(18,($y+4));$label.Size=New-Object Drawing.Size(340,24)
 $box=New-Object Windows.Forms.TextBox;$box.Text=$entry.Value[1];$box.Location=New-Object Drawing.Point(365,$y);$box.Size=New-Object Drawing.Size(380,26)
 $form.Controls.Add($label);$form.Controls.Add($box);$inputs[$entry.Key]=$box;$y+=33
}
$modeLabel=New-Object Windows.Forms.Label;$modeLabel.Text='Modo';$modeLabel.Location=New-Object Drawing.Point(18,($y+4));$modeLabel.Size=New-Object Drawing.Size(100,24)
$mode=New-Object Windows.Forms.ComboBox;$mode.DropDownStyle='DropDownList';$null=$mode.Items.AddRange(@('New','Restore'));$mode.SelectedIndex=0;$mode.Location=New-Object Drawing.Point(365,$y);$mode.Width=180
$form.Controls.Add($modeLabel);$form.Controls.Add($mode);$y+=33
$backupLabel=New-Object Windows.Forms.Label;$backupLabel.Text='Carpeta del backup (Restore)';$backupLabel.Location=New-Object Drawing.Point(18,($y+4));$backupLabel.Size=New-Object Drawing.Size(340,24)
$backup=New-Object Windows.Forms.TextBox;$backup.Location=New-Object Drawing.Point(365,$y);$backup.Size=New-Object Drawing.Size(380,26);$backup.Enabled=$false
$form.Controls.Add($backupLabel);$form.Controls.Add($backup);$y+=33
$hashLabel=New-Object Windows.Forms.Label;$hashLabel.Text='SHA256 del manifiesto del backup';$hashLabel.Location=New-Object Drawing.Point(18,($y+4));$hashLabel.Size=New-Object Drawing.Size(340,24)
$backupHash=New-Object Windows.Forms.TextBox;$backupHash.Location=New-Object Drawing.Point(365,$y);$backupHash.Size=New-Object Drawing.Size(380,26);$backupHash.Enabled=$false
$form.Controls.Add($hashLabel);$form.Controls.Add($backupHash);$y+=34
$trust=New-Object Windows.Forms.CheckBox;$trust.Location=New-Object Drawing.Point(18,$y);$trust.Size=New-Object Drawing.Size(727,47)
$trust.Text='Autorizar confianza de la CA local de RackClick en ESTE servidor para verificar HTTPS. En otros equipos se importa la CA manualmente; nunca su clave privada.'
$form.Controls.Add($trust);$y+=53
$install=New-Object Windows.Forms.Button;$install.Text='Revisar e instalar';$install.Location=New-Object Drawing.Point(18,$y);$install.Size=New-Object Drawing.Size(180,34)
$open=New-Object Windows.Forms.Button;$open.Text='Abrir RackClick';$open.Location=New-Object Drawing.Point(210,$y);$open.Size=New-Object Drawing.Size(160,34);$open.Enabled=$false
$access=New-Object Windows.Forms.Button;$access.Text='Acceso privado';$access.Location=New-Object Drawing.Point(382,$y);$access.Size=New-Object Drawing.Size(160,34);$access.Enabled=$false
$verify=New-Object Windows.Forms.Button;$verify.Text='Verificar instalacion';$verify.Location=New-Object Drawing.Point(554,$y);$verify.Size=New-Object Drawing.Size(191,34);$verify.Enabled=$false
$form.Controls.Add($install);$form.Controls.Add($open);$form.Controls.Add($access);$form.Controls.Add($verify);$y+=43
$existing=New-Object Windows.Forms.Button;$existing.Text='Abrir servidor ya instalado';$existing.Location=New-Object Drawing.Point(18,$y);$existing.Size=New-Object Drawing.Size(250,32);$form.Controls.Add($existing);$y+=39
$progress=New-Object Windows.Forms.ProgressBar;$progress.Location=New-Object Drawing.Point(18,$y);$progress.Size=New-Object Drawing.Size(727,22);$form.Controls.Add($progress);$y+=28
$status=New-Object Windows.Forms.Label;$status.Location=New-Object Drawing.Point(18,$y);$status.Size=New-Object Drawing.Size(727,100);$status.Text='Preparado para revisar. No se ha instalado nada.';$form.Controls.Add($status)
$state=@{process=$null;folder='';attemptId='';url='';complete=$false;exitCode=0;managementPath='';reportProcess=$null;reportOutput='';reportBaseStatus=''}
function Open-SetupInstalledPanel([string]$Path,[switch]$PrivateAccess,[switch]$RunVerification){
 $viewer=Join-Path $PSScriptRoot 'Show-RackClickInstalledServer.ps1'
 if(-not[IO.File]::Exists($viewer)){throw 'installed_panel_missing'}
 $arguments=@('-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',(ConvertTo-SetupUiArgument $viewer))
 if($Path){$arguments+=@('-ManagementPath',(ConvertTo-SetupUiArgument $Path))}
 if($PrivateAccess){$arguments+='-OpenPrivateAccess'}
 if($RunVerification){$arguments+='-VerifyInstallation'}
 $null=Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList $arguments -WindowStyle Hidden
}
$existing.Add_Click({try{Open-SetupInstalledPanel ''}catch{[Windows.Forms.MessageBox]::Show('No se pudo abrir el panel de la instalacion existente. Conserva sus archivos.','RackClick','OK','Error')|Out-Null}})
$mode.Add_SelectedIndexChanged({$enabled=$mode.SelectedItem -eq 'Restore';$backup.Enabled=$enabled;$backupHash.Enabled=$enabled})
$timer=New-Object Windows.Forms.Timer;$timer.Interval=750
$timer.Add_Tick({
 if($state.reportProcess){
  if(Test-SetupUiReportDeadlineExpired $state){Close-SetupUiTrackedProcess $state.reportProcess;$state.reportProcess=$null;$status.Text=$state.reportBaseStatus+"`r`n"+'El informe no finalizo en 60 segundos y podria seguir activo. No repitas la instalacion. Puedes cerrar esta ventana; se conserva el resultado original.';$timer.Stop();return}
  try{if(Test-SetupUiTrackedProcessComplete $state.reportProcess){$state.reportExitedPolls++;if(-not(Test-SetupUiReportReceiptReadable $state.reportOutput)-and$state.reportExitedPolls-lt5){return};$reportMessage=Complete-SetupUiReportExport $state;$status.Text=$state.reportBaseStatus+"`r`n"+$reportMessage;$timer.Stop()}}catch{Close-SetupUiTrackedProcess $state.reportProcess;$state.reportProcess=$null;$status.Text=$state.reportBaseStatus+"`r`n"+'No se pudo crear el ZIP automatico. Ejecuta RECOPILAR-INFORME.cmd; el resultado original se conserva.';$timer.Stop()}
  return
 }
 if(-not $state.process){return}
 try {
  $progressPath=Join-Path $state.folder 'progress.json'
  if(Test-Path -LiteralPath $progressPath){
   try{$p=[IO.File]::ReadAllText($progressPath)|ConvertFrom-Json;if($p.percent -is [int] -and $p.percent-ge 0 -and $p.percent-le 100){$progress.Value=$p.percent};$status.Text=[string]$p.message}catch{}
  }
  if(Test-SetupUiTrackedProcessComplete $state.process){
   $state.complete=$true
   try{$state.exitCode=Get-SetupUiTrackedExitCode $state.process}catch{$state.exitCode=1}
   $resultPath=Join-Path $state.folder 'result.json';$result=$null
   if(Test-Path -LiteralPath $resultPath){try{$result=[IO.File]::ReadAllText($resultPath)|ConvertFrom-Json}catch{}}
   $outcome=Get-SetupUiBrokerOutcome $result $state.exitCode
   if($outcome-ceq'verified'){
    $progress.Value=100;$status.Text='Instalacion y reinicio comprobados. Informe privado: '+$resultPath;$open.Enabled=$true
    $state.managementPath=[string]$result.managementPath;$access.Enabled=$true;$verify.Enabled=$true
    }elseif($outcome-ceq'awaiting_reboot'){
     $progress.Value=95;$status.Text='Preparada: HTTPS y backup comprobados. Falta reiniciar Windows para verificar el arranque automatico. Informe privado: '+$resultPath;$open.Enabled=$true
     $state.managementPath=[string]$result.managementPath;$access.Enabled=$true;$verify.Enabled=$true
    }else{
    $state.exitCode=1
    $status.Text=Format-SetupUiFailure $result $state.folder
   }
   Close-SetupUiTrackedProcess $state.process;$state.process=$null
   $state.reportBaseStatus=$status.Text
   try{Start-SetupUiReportExport $state $RecoverySessionDirectory;$status.Text+=' Generando informe automatico en el Escritorio...'}catch{$status.Text+=' No se pudo iniciar el informe automatico. Ejecuta RECOPILAR-INFORME.cmd.';$timer.Stop()}
  }
 }catch{$timer.Stop();$state.exitCode=1;Close-SetupUiTrackedProcess $state.process;$state.process=$null;$status.Text='No se pudo consultar el resultado. El proceso podria seguir activo; no repitas la instalacion. Conserva la carpeta: '+$state.folder}
})
$install.Add_Click({
 try {
  if(-not $trust.Checked){[Windows.Forms.MessageBox]::Show('Confirma la confianza de la CA local en este servidor para continuar.','RackClick')|Out-Null;return}
  $ip=$null
  if(-not [Net.IPAddress]::TryParse($inputs.bindAddress.Text.Trim(),[ref]$ip) -or $ip.AddressFamily-ne [Net.Sockets.AddressFamily]::InterNetwork -or [Net.IPAddress]::IsLoopback($ip) -or $ip.Equals([Net.IPAddress]::Any)){throw 'invalid_bind_address'}
  $hostName=$inputs.publicHost.Text.Trim()
  if([Uri]::CheckHostName($hostName)-eq [UriHostNameType]::Unknown){throw 'invalid_public_host'}
  $https=0;$pg=0
  if(-not [int]::TryParse($inputs.httpsPort.Text,[ref]$https)-or $https-lt 1024-or $https-gt 65535){throw 'invalid_https_port'}
  if(-not [int]::TryParse($inputs.postgresPort.Text,[ref]$pg)-or $pg-lt 1024-or $pg-gt 65535-or $pg-eq $https){throw 'invalid_postgres_port'}
  $subnet=$inputs.allowedSubnet.Text.Trim()
  if($subnet-notmatch '^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$'){throw 'invalid_allowed_subnet'}
  foreach($name in @('systemhaus','bootstrapUser','serviceName','accountName')){if([string]::IsNullOrWhiteSpace($inputs[$name].Text)){throw 'required_field_missing'}}
  if($mode.SelectedItem-eq 'Restore' -and (-not [IO.Directory]::Exists($backup.Text) -or $backupHash.Text-notmatch '^[a-fA-F0-9]{64}$')){throw 'restore_reference_required'}
  $plan=[ordered]@{schemaVersion=1;id=[guid]::NewGuid().ToString('D');bindAddress=$ip.ToString();publicHost=$hostName;httpsPort=$https;postgresPort=$pg;allowedSubnet=$subnet;systemhaus=$inputs.systemhaus.Text;bootstrapUser=$inputs.bootstrapUser.Text;serviceName=$inputs.serviceName.Text;accountName=$inputs.accountName.Text;mode=[string]$mode.SelectedItem;backupPath='';backupManifestSha256='';trustOnServer=$true}
  if($plan.mode-eq 'Restore'){$plan.backupPath=$backup.Text;$plan.backupManifestSha256=$backupHash.Text.ToLowerInvariant()}
  $summary='Se instalaran las versiones fijadas del paquete: runtime .NET, PostgreSQL privado y Visual C++ si falta. Se creara una cuenta Windows estandar de servicio con clave aleatoria local cifrada, roles PostgreSQL y el administrador de RackClick. No se borran instalaciones existentes.'+"`r`n`r`n"+'URL: https://'+$hostName+':'+$https+"`r`n"+'Red: '+$subnet+"`r`n"+'Servicio: '+$plan.serviceName+' / Cuenta: '+$plan.accountName+"`r`n"+'Datos: C:\ProgramData\RackClick\Instances\'+$plan.id+'\instance'+"`r`n"+'Programa: C:\Program Files\RackClick\'+$plan.id+"`r`n`r`n"+'Continuar con esta instalacion nueva?'
  if([Windows.Forms.MessageBox]::Show($summary,'Revisar instalacion','YesNo','Question')-ne 'Yes'){return}
  $broker=Join-Path $PSScriptRoot 'Install-RackClickServer.ps1'
  if(-not [IO.File]::Exists($broker)){throw 'installer_broker_missing'}
  if(Get-Service -Name $plan.serviceName -ErrorAction SilentlyContinue){
   $status.Text='Ya existe ese servicio. Se abrira el panel para validar su recibo; no se iniciara otra instalacion.'
   Open-SetupInstalledPanel '';return
  }
  $saved=New-SetupUiPrivatePlan $plan;$state.folder=$saved.folder;$state.attemptId=$plan.id;$state.url='https://'+$hostName+':'+$https
  $arguments=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(ConvertTo-SetupUiArgument $broker),'-PlanPath',(ConvertTo-SetupUiArgument $saved.path),'-ReportDirectory',(ConvertTo-SetupUiArgument $saved.folder))
  $state.process=Start-SetupUiTrackedProcess $arguments $PSScriptRoot (Join-Path $saved.folder 'broker.stdout.log') (Join-Path $saved.folder 'broker.stderr.log')
  $install.Enabled=$false;foreach($box in $inputs.Values){$box.Enabled=$false};$mode.Enabled=$false;$backup.Enabled=$false;$backupHash.Enabled=$false;$trust.Enabled=$false
  $status.Text='Preparacion iniciada. Conserva abierta esta ventana.';$timer.Start()
 }catch{
  $state.exitCode=1;$safeCode='installer_start_failed'
  $knownCodes=@('invalid_bind_address','invalid_public_host','invalid_https_port','invalid_postgres_port','invalid_allowed_subnet','required_field_missing','restore_reference_required','installer_broker_missing','plan_reparse_not_allowed','plan_destination_exists')
  if($_.Exception.Message -cin $knownCodes){$safeCode=$_.Exception.Message}
  $status.Text='No se pudo iniciar: '+$safeCode+'. Revisa los campos y el paquete.'
  if($state.folder){$status.Text+=' Informe privado: '+$state.folder}
  if($state.folder-and-not$state.process){
   $state.reportBaseStatus=$status.Text
   try{Start-SetupUiReportExport $state $RecoverySessionDirectory;$status.Text+=' Generando informe automatico en el Escritorio...';$timer.Start()}catch{$status.Text+=' No se pudo iniciar el informe automatico. Ejecuta RECOPILAR-INFORME.cmd.'}
  }
  [Windows.Forms.MessageBox]::Show($status.Text,'RackClick','OK','Error')|Out-Null
 }
})
$open.Add_Click({if($state.complete -and $open.Enabled){Start-Process $state.url}})
$access.Add_Click({try{if($state.managementPath){Open-SetupInstalledPanel $state.managementPath -PrivateAccess}}catch{[Windows.Forms.MessageBox]::Show('No se pudo abrir el acceso privado. No copies contrasenas al chat.','RackClick','OK','Error')|Out-Null}})
$verify.Add_Click({try{if($state.managementPath){Open-SetupInstalledPanel $state.managementPath -RunVerification}}catch{[Windows.Forms.MessageBox]::Show('No se pudo abrir la verificacion. Conserva el informe privado.','RackClick','OK','Error')|Out-Null}})
$form.Add_FormClosing({param($sender,$eventArgs) if(($state.process -and -not(Test-SetupUiTrackedProcessComplete $state.process))-or$state.reportProcess){$eventArgs.Cancel=$true;[Windows.Forms.MessageBox]::Show('La instalacion o su informe siguen activos. Espera al resultado antes de cerrar.','RackClick')|Out-Null}})
if($ValidateLayout){
 @{valid=$true;inputFields=$inputs.Count;modeCount=$mode.Items.Count;trustInitiallyChecked=$trust.Checked;installEnabled=$install.Enabled;openInitiallyEnabled=$open.Enabled;accessInitiallyEnabled=$access.Enabled;verifyInitiallyEnabled=$verify.Enabled;existingPanelEnabled=$existing.Enabled;privilegedOperationsExecuted=0}|ConvertTo-Json -Compress
 $timer.Dispose();$form.Dispose();return
}
if(Get-Service -Name 'RackClick' -ErrorAction SilentlyContinue){
 $install.Enabled=$false
 $status.Text='Ya existe el servicio RackClick. Pulsa Abrir servidor ya instalado para validar su recibo y abrir el acceso privado o verificar el reinicio. No se iniciara otra instalacion.'
}
$inputs.serviceName.Add_TextChanged({
 if(-not$state.process-and-not$state.complete){
  if($inputs.serviceName.Text-cnotmatch'^RackClick(?:-Recovery-[a-f0-9]{8,32})?$'){$install.Enabled=$false;$status.Text='Nombre de servicio: RackClick o RackClick-Recovery seguido de un identificador hexadecimal.';return}
  $install.Enabled=-not[bool](Get-Service -Name $inputs.serviceName.Text -ErrorAction SilentlyContinue)
  if(-not$install.Enabled){$status.Text='Ya existe ese servicio. Pulsa Abrir servidor ya instalado; no se reinstalara encima.'}else{$status.Text='Servicio nuevo. Revisa sus datos antes de instalar; se conservaran las instalaciones existentes.'}
 }
})
[Windows.Forms.Application]::EnableVisualStyles()
try{$null=$form.ShowDialog()}finally{$timer.Dispose();Close-SetupUiTrackedProcess $state.process;Close-SetupUiTrackedProcess $state.reportProcess;$form.Dispose()}
exit $state.exitCode
