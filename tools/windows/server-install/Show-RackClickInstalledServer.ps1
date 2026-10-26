#requires -Version 5.1
[CmdletBinding()]
param([string]$ManagementPath='', [switch]$OpenPrivateAccess, [switch]$VerifyInstallation, [switch]$ValidateLayout, [switch]$FunctionsOnly)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'RackClick.Setup.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.Security.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.Lifecycle.ps1')
. (Join-Path $PSScriptRoot 'RackClick.Setup.Diagnostics.ps1')
if(-not $ValidateLayout -and -not $FunctionsOnly -and -not(Test-SetupAdministrator)){
    try{
        $uiArguments=@('-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',(ConvertTo-SetupArgument $PSCommandPath))
        if($ManagementPath){$uiArguments+=@('-ManagementPath',(ConvertTo-SetupArgument $ManagementPath))}
        if($OpenPrivateAccess){$uiArguments+='-OpenPrivateAccess'}
        if($VerifyInstallation){$uiArguments+='-VerifyInstallation'}
        $uiElevated=Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList $uiArguments -Verb RunAs -Wait -PassThru
        exit $uiElevated.ExitCode
    }catch{Write-Error 'No se pudo abrir el panel con permisos de administrador.';exit 1}
}
if(-not$FunctionsOnly-and(-not[Environment]::Is64BitProcess-or[Threading.Thread]::CurrentThread.ApartmentState-ne'STA')){throw 'installed_panel_requires_windows_x64_sta'}
function Test-InstalledReceiptBinding($Receipt,[string]$Path){
    $id=[guid]::Empty
    if($Path-cnotmatch'^C:\\ProgramData\\RackClick\\Instances\\([a-f0-9-]{36})\\management$'){return $false}
    $textId=$Matches[1]
    if(-not[guid]::TryParseExact($textId,'D',[ref]$id)-or$id.ToString('D')-cne$textId){return $false}
    $parent='C:\ProgramData\RackClick\Instances\'+$textId
    if($null-eq$Receipt-or$Receipt.schemaVersion-ne1-or$Receipt.installationId-cne$textId-or$Receipt.managementPath-cne$Path-or$Receipt.instancePath-cne($parent+'\instance')-or$Receipt.codeRoot-cne('C:\Program Files\RackClick\'+$textId)-or$Receipt.serviceName-cnotmatch'^RackClick(?:-Recovery-[a-f0-9]{8,32})?$'-or$Receipt.serviceSid-cnotmatch'^S-1-5-21-(\d+-){3}\d+$'-or$Receipt.serviceSid.EndsWith('-500')-or$Receipt.manifestSha256-cnotmatch'^[a-f0-9]{64}$'-or$Receipt.backupTaskName-cne('RackClick-Backup-'+$textId)){return $false}
    $uri=$null
    if(-not[Uri]::TryCreate([string]$Receipt.publicOrigin,[UriKind]::Absolute,[ref]$uri)-or$uri.Scheme-cne'https'-or$uri.HostNameType-notin@([UriHostNameType]::Dns,[UriHostNameType]::IPv4)-or$uri.UserInfo-ne''-or$uri.AbsolutePath-ne'/'-or$uri.Query-ne''-or$uri.Fragment-ne''){return $false}
    return $true
}
function Assert-InstalledProtectedCode([string]$Path,[string]$CodeRoot){
    Assert-SetupNoReparse $Path
    if($Path-cne$CodeRoot-and-not$Path.StartsWith($CodeRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'installed_code_path_invalid'}
    $cursor=$Path
    while($cursor-and$cursor.StartsWith($CodeRoot,[StringComparison]::OrdinalIgnoreCase)){
        if(-not(Test-Path -LiteralPath $cursor)){throw 'installed_code_missing'}
        $acl=Get-Acl -LiteralPath $cursor -ErrorAction Stop
        if($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value-notin@('S-1-5-18','S-1-5-32-544')){throw 'installed_code_owner_invalid'}
        $writeMask=[int64]([Security.AccessControl.FileSystemRights]::Write -bor [Security.AccessControl.FileSystemRights]::Delete -bor [Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles -bor [Security.AccessControl.FileSystemRights]::ChangePermissions -bor [Security.AccessControl.FileSystemRights]::TakeOwnership)
        foreach($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
            if($rule.AccessControlType-ne'Allow'-or(($rule.FileSystemRights.value__-band$writeMask)-ne0-and$rule.IdentityReference.Value-notin@('S-1-5-18','S-1-5-32-544'))){throw 'installed_code_acl_invalid'}
        }
        if($cursor-ceq$CodeRoot){break};$cursor=[IO.Path]::GetDirectoryName($cursor)
    }
}
function Read-InstalledServerReceipt([string]$Path){
    Assert-SetupAdministrator;Assert-SetupPath $Path 'management';Assert-SetupManagementAcl $Path
    $file=Join-Path $Path 'server-installation.json';Assert-SetupNoReparse $file;Assert-SetupManagementAcl $file
    $stream=[IO.File]::Open($file,'Open','Read','Read')
    try{
        if($stream.Length-le0-or$stream.Length-gt1048576){throw 'installed_receipt_size_invalid'}
        $reader=New-Object IO.StreamReader($stream,(New-Object Text.UTF8Encoding($false,$true)),$true,4096,$true)
        try{$receipt=$reader.ReadToEnd()|ConvertFrom-Json -ErrorAction Stop}finally{$reader.Dispose()}
        if(-not(Test-InstalledReceiptBinding $receipt $Path)){throw 'installed_receipt_binding_invalid'}
        foreach($script in @('Test-RackClickServerAfterReboot.ps1','RackClick.Setup.ps1','RackClick.Setup.Security.ps1','RackClick.Setup.Lifecycle.ps1','RackClick.Setup.Diagnostics.ps1')){Assert-InstalledProtectedCode (Join-Path $receipt.codeRoot ('operators\server-install\'+$script)) $receipt.codeRoot}
        Assert-InstalledProtectedCode (Join-Path $receipt.codeRoot 'service\RackClick.WindowsService.dll') $receipt.codeRoot
        $service=Get-CimInstance Win32_Service -Filter ("Name='"+$receipt.serviceName+"'") -ErrorAction Stop
        $expected=(ConvertTo-SetupArgument (Join-Path $receipt.instancePath 'content\dependencies\dotnet\dotnet.exe'))+' '+(ConvertTo-SetupArgument (Join-Path $receipt.codeRoot 'service\RackClick.WindowsService.dll'))+' --config '+(ConvertTo-SetupArgument (Join-Path $receipt.instancePath 'service-config.json'))
        if($null-eq$service-or$service.PathName-cne$expected-or(Resolve-SetupAccountSid $service.StartName)-cne$receipt.serviceSid){throw 'installed_service_binding_invalid'}
        $manifest=Read-SetupPreparedFile -InstancePath $receipt.instancePath -RelativePath 'runtime/server-profile.json' -ServiceSid $receipt.serviceSid
        $sha=[Security.Cryptography.SHA256]::Create()
        try{$digest=([BitConverter]::ToString($sha.ComputeHash($manifest))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
        if($digest-cne$receipt.manifestSha256){throw 'installed_manifest_changed'}
        return $receipt
    }finally{$stream.Dispose()}
}
function Get-InstalledRecordedVerification($Receipt,$CurrentBootUtc,$ObservedUtc){
    $observation=Get-SetupJsonDiagnostic (Join-Path $Receipt.managementPath 'postboot-verification.json') @('S-1-5-18','S-1-5-32-544')
    $verification=$null
    if($observation.status-ceq'parsed'){$verification=$observation.fields}
    elseif($observation.status-cne'missing'){return @{status='unconfirmed';rebootVerified=$false;currentHealthVerified=$false;productAdopted=$false}}
    return Get-SetupRecordedInstallationState -Receipt $Receipt -Verification $verification -CurrentBootUtc $CurrentBootUtc -ObservedUtc $ObservedUtc
}
function Test-InstalledPostbootCompletion($Receipt,$Result,$NativeExitCode,$CurrentBootUtc,$ObservedUtc,$VerificationStartedUtc){
    if($NativeExitCode-isnot[int]-or$NativeExitCode-ne0){return $false}
    $state=Get-SetupRecordedInstallationState -Receipt $Receipt -Verification $Result -CurrentBootUtc $CurrentBootUtc -ObservedUtc $ObservedUtc
    if($state.status-cne'recorded'-or$state.rebootVerified-ne$true-or-not(Test-SetupUtcTimestamp $VerificationStartedUtc)){return $false}
    $started=[DateTimeOffset]::Parse($VerificationStartedUtc,[Globalization.CultureInfo]::InvariantCulture)
    $checked=[DateTimeOffset]::Parse($state.checkedUtc,[Globalization.CultureInfo]::InvariantCulture)
    return ($checked-ge$started)
}
if($FunctionsOnly){return}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()
$panelForm=New-Object Windows.Forms.Form
$panelForm.Text='RackClick - Servidor instalado';$panelForm.Size=New-Object Drawing.Size(790,510);$panelForm.MinimumSize=$panelForm.Size;$panelForm.StartPosition='CenterScreen';$panelForm.AutoScaleMode='Dpi';$panelForm.Font=New-Object Drawing.Font('Segoe UI',10)
$panelHeader=New-Object Windows.Forms.Label;$panelHeader.Location=New-Object Drawing.Point(18,14);$panelHeader.Size=New-Object Drawing.Size(735,55);$panelHeader.Text='Abrir RackClick, consultar el acceso privado o verificar el arranque despues de reiniciar Windows. Este panel no instala otra instancia ni cambia contrasenas.';$panelForm.Controls.Add($panelHeader)
$panelChoose=New-Object Windows.Forms.ComboBox;$panelChoose.Location=New-Object Drawing.Point(18,75);$panelChoose.Size=New-Object Drawing.Size(735,28);$panelChoose.DropDownStyle='DropDownList';$panelForm.Controls.Add($panelChoose)
$panelDetails=New-Object Windows.Forms.Label;$panelDetails.Location=New-Object Drawing.Point(18,116);$panelDetails.Size=New-Object Drawing.Size(735,95);$panelDetails.Text='Selecciona una instalacion confirmada por su recibo privado.';$panelForm.Controls.Add($panelDetails)
$panelOpen=New-Object Windows.Forms.Button;$panelOpen.Text='Abrir RackClick';$panelOpen.Location=New-Object Drawing.Point(18,219);$panelOpen.Size=New-Object Drawing.Size(175,36);$panelOpen.Enabled=$false;$panelForm.Controls.Add($panelOpen)
$panelAccess=New-Object Windows.Forms.Button;$panelAccess.Text='Acceso privado';$panelAccess.Location=New-Object Drawing.Point(205,219);$panelAccess.Size=New-Object Drawing.Size(175,36);$panelAccess.Enabled=$false;$panelForm.Controls.Add($panelAccess)
$panelVerify=New-Object Windows.Forms.Button;$panelVerify.Text='Verificar instalacion';$panelVerify.Location=New-Object Drawing.Point(392,219);$panelVerify.Size=New-Object Drawing.Size(190,36);$panelVerify.Enabled=$false;$panelForm.Controls.Add($panelVerify)
$panelExport=New-Object Windows.Forms.Button;$panelExport.Text='Exportar backup';$panelExport.Location=New-Object Drawing.Point(594,219);$panelExport.Size=New-Object Drawing.Size(159,36);$panelExport.Enabled=$false;$panelForm.Controls.Add($panelExport)
$panelProgress=New-Object Windows.Forms.ProgressBar;$panelProgress.Location=New-Object Drawing.Point(18,270);$panelProgress.Size=New-Object Drawing.Size(735,23);$panelForm.Controls.Add($panelProgress)
$panelStatus=New-Object Windows.Forms.Label;$panelStatus.Location=New-Object Drawing.Point(18,307);$panelStatus.Size=New-Object Drawing.Size(735,125);$panelStatus.Text='No se ha verificado el reinicio. El 100% exige un arranque nuevo y comprobaciones actuales de servicio, HTTPS y backup. La adopcion final del producto sigue pendiente de QA.';$panelForm.Controls.Add($panelStatus)
$panelState=@{receipt=$null;process=$null;stdout='';exitCode=0;paths=@();verificationStartedUtc=''}
$panelTimer=New-Object Windows.Forms.Timer;$panelTimer.Interval=500
$panelChoose.Add_SelectedIndexChanged({
    if($panelState.process){return}
    $panelState.receipt=$null;$panelOpen.Enabled=$false;$panelAccess.Enabled=$false;$panelVerify.Enabled=$false;$panelExport.Enabled=$false;$panelProgress.Value=0
    try{
        $selected=$panelState.paths[$panelChoose.SelectedIndex];$receipt=Read-InstalledServerReceipt $selected;$panelState.receipt=$receipt
        $panelDetails.Text='URL: '+$receipt.publicOrigin+"`r`nServicio: "+$receipt.serviceName+"`r`nInstancia: "+$receipt.installationId
        $panelOpen.Enabled=$true;$panelAccess.Enabled=$true;$panelVerify.Enabled=$true;$panelExport.Enabled=$true;$panelProgress.Value=95
        $boot=(Get-CimInstance Win32_OperatingSystem -ErrorAction Stop).LastBootUpTime.ToUniversalTime().ToString('o')
        $registered=Get-InstalledRecordedVerification $receipt $boot ([DateTime]::UtcNow.ToString('o'))
        if($registered.status-ceq'recorded'){$panelStatus.Text='Reinicio registrado como verificado para este arranque. Pulsa Verificar instalacion para comprobar de nuevo el servicio, HTTPS y backup. El 100% exige esa comprobacion actual.'}
        elseif($registered.status-ceq'stale'){$panelStatus.Text='Hay una verificacion de un arranque anterior. Pulsa Verificar instalacion para comprobar este arranque.'}
        else{$panelStatus.Text='Instancia identificada. Pulsa Verificar instalacion para comprobar el arranque, servicio, HTTPS y backup. Si falta reiniciar Windows, la verificacion te lo indicara.'}
    }catch{$panelState.exitCode=1;$panelStatus.Text='No se pudo validar la instancia. Conserva sus archivos y el recibo; no la reinstales encima.'}
})
$panelOpen.Add_Click({
    try{$receipt=Read-InstalledServerReceipt $panelState.receipt.managementPath;Start-Process $receipt.publicOrigin}catch{[Windows.Forms.MessageBox]::Show('No se pudo validar la instalacion antes de abrir su URL.','RackClick','OK','Error')|Out-Null}
})
$panelAccess.Add_Click({
    try{
        $receipt=Read-InstalledServerReceipt $panelState.receipt.managementPath;$file=Join-Path $receipt.managementPath 'admin-login.json'
        Assert-SetupNoReparse $file;Assert-SetupManagementAcl $file
        $null=Start-Process -FilePath "$env:SystemRoot\System32\notepad.exe" -ArgumentList (ConvertTo-SetupArgument $file)
    }catch{[Windows.Forms.MessageBox]::Show('No se pudo abrir el acceso privado. No copies contrasenas al chat ni cambies permisos de la carpeta.','RackClick','OK','Error')|Out-Null}
})
$panelExport.Add_Click({
    try{
        $receipt=Read-InstalledServerReceipt $panelState.receipt.managementPath
        $file=Join-Path $receipt.codeRoot 'operators\server-install\Export-RackClickServerBackup.ps1';Assert-InstalledProtectedCode $file $receipt.codeRoot
        $arguments=@('-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',(ConvertTo-SetupArgument $file),'-ManagementPath',(ConvertTo-SetupArgument $receipt.managementPath))
        $null=Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList $arguments -WindowStyle Hidden
    }catch{[Windows.Forms.MessageBox]::Show('No se pudo iniciar la exportacion. Conserva el backup privado original.','RackClick','OK','Error')|Out-Null}
})
$panelVerify.Add_Click({
    $panelProgress.Value=95;$panelState.exitCode=1;$panelState.verificationStartedUtc=''
    try{
        $receipt=Read-InstalledServerReceipt $panelState.receipt.managementPath
        $run=[guid]::NewGuid().ToString('N');$panelState.stdout=Join-Path $receipt.managementPath ('verify-ui-'+$run+'.stdout.log')
        $stderr=Join-Path $receipt.managementPath ('verify-ui-'+$run+'.stderr.log')
        $arguments=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(ConvertTo-SetupArgument (Join-Path $receipt.codeRoot 'operators\server-install\Test-RackClickServerAfterReboot.ps1')),'-ManagementPath',(ConvertTo-SetupArgument $receipt.managementPath))
        $panelState.verificationStartedUtc=[DateTime]::UtcNow.ToString('o')
        $panelState.process=Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList $arguments -WindowStyle Hidden -RedirectStandardOutput $panelState.stdout -RedirectStandardError $stderr -PassThru
        $panelVerify.Enabled=$false;$panelChoose.Enabled=$false;$panelStatus.Text='Verificando reinicio, identidad del servicio, HTTPS y tarea de backup...';$panelTimer.Start()
    }catch{$panelState.exitCode=1;$panelStatus.Text='No se pudo iniciar la verificacion. Conserva el informe privado de la instancia.'}
})
$panelTimer.Add_Tick({
    if(-not$panelState.process-or-not$panelState.process.HasExited){return}
    $panelTimer.Stop()
    try{
        $receipt=Read-InstalledServerReceipt $panelState.receipt.managementPath
        Assert-SetupNoReparse $panelState.stdout;Assert-SetupManagementAcl $panelState.stdout
        $result=[IO.File]::ReadAllText($panelState.stdout)|ConvertFrom-Json -ErrorAction Stop
        $boot=(Get-CimInstance Win32_OperatingSystem -ErrorAction Stop).LastBootUpTime.ToUniversalTime().ToString('o')
        if(Test-InstalledPostbootCompletion $receipt $result $panelState.process.ExitCode $boot ([DateTime]::UtcNow.ToString('o')) $panelState.verificationStartedUtc){
            $panelProgress.Value=100;$panelState.exitCode=0;$panelStatus.Text='100% de instalacion tecnica comprobada: reinicio real, servicio automatico, HTTPS y backup. Puedes continuar con las pruebas de interfaz. La adopcion del producto corresponde a Wascar.'
        }else{
            $panelProgress.Value=95;$panelState.exitCode=1;$code='postboot_result_not_confirmed'
            if([string]$result.code-cmatch'^postboot_[a-z0-9_]{1,90}$'){$code=$result.code}
            if($code-ceq'postboot_restart_not_observed'){$panelStatus.Text='Falta reiniciar Windows. Reinicia cuando te convenga, vuelve a abrir este panel y pulsa Verificar instalacion.'}else{$panelStatus.Text='Verificacion pendiente: '+$code+'. Informe privado: '+$receipt.managementPath}
        }
    }catch{$panelState.exitCode=1;$panelProgress.Value=95;$panelStatus.Text='No se pudo confirmar el resultado de la verificacion. Conserva los informes privados.'}
    finally{$panelState.process.Dispose();$panelState.process=$null;$panelVerify.Enabled=$true;$panelChoose.Enabled=$true}
})
$panelForm.Add_FormClosing({param($sender,$eventArgs) if($panelState.process-and-not$panelState.process.HasExited){$eventArgs.Cancel=$true;[Windows.Forms.MessageBox]::Show('Espera a que termine la verificacion antes de cerrar.','RackClick')|Out-Null}})
if($ValidateLayout){
    @{valid=$true;existingInstallPanel=$true;openInitiallyEnabled=$panelOpen.Enabled;accessInitiallyEnabled=$panelAccess.Enabled;verifyInitiallyEnabled=$panelVerify.Enabled;exportInitiallyEnabled=$panelExport.Enabled;privilegedOperationsExecuted=0}|ConvertTo-Json -Compress
    $panelTimer.Dispose();$panelForm.Dispose();return
}
try{
    if($ManagementPath){$candidatePaths=@($ManagementPath)}else{
        $instances='C:\ProgramData\RackClick\Instances';Assert-SetupNoReparse $instances
        $candidatePaths=@()
        if([IO.Directory]::Exists($instances)){
            foreach($directory in @(Get-ChildItem -LiteralPath $instances -Directory -Force -ErrorAction Stop)){
                if($directory.Name-cmatch'^[a-f0-9-]{36}$'-and($directory.Attributes-band[IO.FileAttributes]::ReparsePoint)-eq0){$candidatePaths+=Join-Path $directory.FullName 'management'}
            }
        }
    }
    foreach($path in $candidatePaths){
        try{$receipt=Read-InstalledServerReceipt $path;$panelState.paths+=,$path;$null=$panelChoose.Items.Add(($receipt.serviceName+' / '+$receipt.publicOrigin+' / '+$receipt.installationId))}catch{}
    }
    if($panelChoose.Items.Count-gt0){$panelChoose.SelectedIndex=0;if($OpenPrivateAccess){$panelAccess.PerformClick()};if($VerifyInstallation){$panelVerify.PerformClick()}}else{$panelState.exitCode=1;$panelStatus.Text='No se encontro una instalacion confirmada con recibo, servicio y permisos validos. No se ha cambiado nada. Conserva las carpetas y los informes del intento anterior.'}
    $null=$panelForm.ShowDialog()
}finally{$panelTimer.Dispose();$panelForm.Dispose()}
exit $panelState.exitCode
