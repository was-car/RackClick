#requires -Version 5.1
[CmdletBinding()]
param([switch]$FunctionsOnly,[switch]$Elevated)

function Stop-RcHere([string]$Code){throw (New-Object InvalidOperationException($Code))}
function Assert-RcHereNoReparse([string]$Path){
    $cursor=[IO.Path]::GetFullPath($Path)
    while($cursor){$item=Get-Item -LiteralPath $cursor -Force -ErrorAction Stop;if(($item.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){Stop-RcHere 'here_path_invalid'};$cursor=[IO.Path]::GetDirectoryName($cursor)}
}
function ConvertTo-RcHereCandidate($Service,$Receipt){
    $id=[guid]::Empty
    if(-not[guid]::TryParseExact([string]$Receipt.installationId,'D',[ref]$id)-or$id.ToString('D')-cne$Receipt.installationId){Stop-RcHere 'here_receipt_invalid'}
    $parent='C:\ProgramData\RackClick\Instances\'+$Receipt.installationId
    $instance=Join-Path $parent 'instance';$code='C:\Program Files\RackClick\'+$Receipt.installationId
    $origin=$null
    if($Receipt.schemaVersion-ne1-or$Receipt.managementPath-cne(Join-Path $parent 'management')-or$Receipt.instancePath-cne$instance-or$Receipt.codeRoot-cne$code-or$Receipt.serviceName-cnotmatch'^RackClick(?:-Recovery-[a-f0-9]{8,32})?$'-or$Service.Name-cne$Receipt.serviceName){Stop-RcHere 'here_receipt_invalid'}
    if(-not[Uri]::TryCreate([string]$Receipt.publicOrigin,[UriKind]::Absolute,[ref]$origin)-or$origin.Scheme-cne'https'-or$origin.AbsolutePath-cne'/'-or$origin.Query-or$origin.Fragment-or$origin.UserInfo-or$origin.Port-cnotin@(5443,5444)){Stop-RcHere 'here_receipt_invalid'}
    $expected='"'+(Join-Path $instance 'content\dependencies\dotnet\dotnet.exe')+'" "'+(Join-Path $code 'service\RackClick.WindowsService.dll')+'" --config "'+(Join-Path $instance 'service-config.json')+'"'
    if($Service.PathName-cne$expected-or$Service.State-cnotin@('Running','Stopped')){Stop-RcHere 'here_service_invalid'}
    $restored=$origin.Port-eq5444
    return [pscustomobject]@{id=$Receipt.installationId;serviceName=$Receipt.serviceName;httpsPort=$origin.Port;postgresPort=$(if($restored){55442}else{55441});origin=$origin.GetLeftPart([UriPartial]::Authority);restored=$restored;label=$(if($restored){'Restaurada - tus datos (5444)'}else{'Original (5443)'})+' - '+$Receipt.serviceName}
}
function Get-RcHereCandidates {
    $answer=@()
    foreach($service in @(Get-CimInstance Win32_Service -Filter "Name LIKE 'RackClick%'") ){
        if($service.Name-cnotmatch'^RackClick(?:-Recovery-[a-f0-9]{8,32})?$'){continue}
        $match=[regex]::Match([string]$service.PathName,' --config "C:\\ProgramData\\RackClick\\Instances\\([a-f0-9-]{36})\\instance\\service-config\.json"$')
        if(-not$match.Success){continue}
        $receiptPath='C:\ProgramData\RackClick\Instances\'+$match.Groups[1].Value+'\management\server-installation.json'
        try{
            Assert-RcHereNoReparse $receiptPath
            $acl=Get-Acl -LiteralPath $receiptPath -ErrorAction Stop
            if($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value-cnotin@('S-1-5-18','S-1-5-32-544')){continue}
            $file=[IO.File]::Open($receiptPath,'Open','Read','Read')
            try{if($file.Length-gt65536){continue};$reader=New-Object IO.StreamReader($file,(New-Object Text.UTF8Encoding($false,$true)),$true,4096,$true);try{$receipt=$reader.ReadToEnd()|ConvertFrom-Json -ErrorAction Stop}finally{$reader.Dispose()}}finally{$file.Dispose()}
            $candidate=ConvertTo-RcHereCandidate $service $receipt
            if($candidate.id-cne$match.Groups[1].Value){continue}
            $answer+=@($candidate)
        }catch{continue}
    }
    return @($answer|Sort-Object @{Expression='restored';Descending=$true},serviceName)
}
function Select-RcHereNetworks($Addresses,$Adapters,$Routes,$Interfaces){
    $answer=@();$seen=@{}
    foreach($address in @($Addresses)){
        $ip=$null;$text=[string]$address.IPAddress
        if([string]$address.AddressState-cne'Preferred'-or-not[Net.IPAddress]::TryParse($text,[ref]$ip)-or$ip.AddressFamily-ne[Net.Sockets.AddressFamily]::InterNetwork-or$ip.ToString()-cne$text){continue}
        $bytes=$ip.GetAddressBytes()
        if($bytes[0]-ne192-or$bytes[1]-ne168-or$bytes[2]-notin@(178,250)-or$bytes[3]-in@(0,255)-or$seen.ContainsKey($text)){continue}
        if(@($Adapters|Where-Object{$_.InterfaceIndex-eq$address.InterfaceIndex-and[string]$_.Status-eq'Up'}).Count-ne1){continue}
        $route=@($Routes|Where-Object{$_.InterfaceIndex-eq$address.InterfaceIndex-and$_.DestinationPrefix-ceq'0.0.0.0/0'}|Sort-Object RouteMetric|Select-Object -First 1)
        $iface=@($Interfaces|Where-Object{$_.InterfaceIndex-eq$address.InterfaceIndex}|Select-Object -First 1)
        $score=100000
        if($route.Count-eq1){$score=[int]$route[0].RouteMetric;if($iface.Count-eq1){$score+=[int]$iface[0].InterfaceMetric}}
        $subnet='192.168.'+[string]$bytes[2]+'.0/24';$seen[$text]=$true
        $answer+=@([pscustomobject]@{ip=$text;subnet=$subnet;score=$score;label=$text+'   (red '+$subnet+')'})
    }
    return @($answer|Sort-Object score,ip)
}
function ConvertTo-RcHereArgument([string]$Value){
    if($Value.Contains([char]0)-or$Value.Contains("`r")-or$Value.Contains("`n")){Stop-RcHere 'here_argument_invalid'}
    return '"'+([regex]::Replace(([regex]::Replace($Value,'(\\*)"','$1$1\"')),'(\\+)$','$1$1'))+'"'
}
function Assert-RcHereResult($Report,[int]$ExitCode,$Candidate,$Network){
    $wanted='https://'+$Network.ip+':'+$Candidate.httpsPort
    if($null-eq$Report-or$Report.schemaVersion-ne1-or$Report.exitCode-isnot[int]-or$Report.exitCode-ne$ExitCode-or$Report.valid-isnot[bool]-or$Report.success-isnot[bool]-or$Report.installationId-cne$Candidate.id){Stop-RcHere 'here_engine_result_invalid'}
    if($ExitCode-eq0-and(-not$Report.valid-or-not$Report.success-or$Report.code-cnotin@('network_change_verified','network_existing_verified')-or$Report.readiness-cne'ready'-or$Report.publicOrigin-cne$wanted-or$Report.httpsPort-ne$Candidate.httpsPort-or$Report.postgresPort-ne$Candidate.postgresPort)){Stop-RcHere 'here_engine_result_invalid'}
    return $Report
}
function Invoke-RcHereEngine($Candidate,$Network,[string]$Script,[string]$ExpectedHash,[scriptblock]$Pulse){
    Assert-RcHereNoReparse $Script
    $lock=[IO.File]::Open($Script,'Open','Read','Read')
    try{
        if($ExpectedHash-cnotmatch'^[a-f0-9]{64}$'-or(Get-FileHash -LiteralPath $Script -Algorithm SHA256).Hash.ToLowerInvariant()-cne$ExpectedHash){Stop-RcHere 'here_engine_hash_mismatch'}
        $arguments=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$Script,'-InstallationId',$Candidate.id,'-HttpsPort',[string]$Candidate.httpsPort,'-PostgresPort',[string]$Candidate.postgresPort,'-BindAddress',$Network.ip,'-AllowedSubnet',$Network.subnet,'-EnsureRunning')
        $info=New-Object Diagnostics.ProcessStartInfo;$info.FileName=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe';$info.UseShellExecute=$false;$info.CreateNoWindow=$true;$info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
        $info.Arguments=($arguments|ForEach-Object{ConvertTo-RcHereArgument $_})-join' '
        $child=[Diagnostics.Process]::Start($info);$null=$child.Handle
        try{
            $stdout=$child.StandardOutput.ReadToEndAsync();$stderr=$child.StandardError.ReadToEndAsync();$watch=[Diagnostics.Stopwatch]::StartNew()
            while(-not$child.WaitForExit(200)){
                if($null-ne$Pulse){& $Pulse ([int]$watch.Elapsed.TotalSeconds)}
                if($watch.Elapsed.TotalSeconds-gt720){Stop-RcHere 'here_operation_pending_do_not_repeat'}
            }
            $text=$stdout.GetAwaiter().GetResult();$errors=$stderr.GetAwaiter().GetResult();$child.Refresh();$exit=$child.ExitCode
            if($null-eq$exit-or$text.Length-gt131072-or$errors.Length-ne0){Stop-RcHere 'here_engine_result_invalid'}
            try{$report=$text|ConvertFrom-Json -ErrorAction Stop}catch{Stop-RcHere 'here_engine_result_invalid'}
            return Assert-RcHereResult $report $exit $Candidate $Network
        }finally{$child.Dispose()}
    }finally{$lock.Dispose()}
}
function Save-RcHereReport($Report){
    $desktop=[Environment]::GetFolderPath('DesktopDirectory')
    if(-not[IO.Directory]::Exists($desktop)){return ''}
    $path=Join-Path $desktop ('RackClick-Conexion-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)+'.json')
    $bytes=[Text.Encoding]::UTF8.GetBytes(($Report|ConvertTo-Json -Depth 8 -Compress))
    $file=[IO.File]::Open($path,'CreateNew','Write','None');try{$file.Write($bytes,0,$bytes.Length);$file.Flush($true)}finally{$file.Dispose()}
    return $path
}
function Export-RcHerePublicCertificate($Candidate,[string]$InstancesRoot='C:\ProgramData\RackClick\Instances',[string]$DesktopDirectory=[Environment]::GetFolderPath('DesktopDirectory')){
    # Optional convenience after a verified start. Only public DER is exported;
    # no PFX, TLS password, application or PostgreSQL credential is accessed.
    $parsedId=[guid]::Empty;if(-not[guid]::TryParseExact([string]$Candidate.id,'D',[ref]$parsedId)-or$parsedId.ToString('D')-cne$Candidate.id){Stop-RcHere 'here_public_certificate_invalid'}
    $management=Join-Path (Join-Path $InstancesRoot $Candidate.id) 'management'
    $source=Join-Path $management 'RootCA.cer';$receiptPath=Join-Path $management 'server-installation.json'
    foreach($path in @($source,$receiptPath)){
        Assert-RcHereNoReparse $path;$acl=Get-Acl -LiteralPath $path
        if($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value-cnotin@('S-1-5-18','S-1-5-32-544')-or(Get-Item -LiteralPath $path).Length-gt65536){Stop-RcHere 'here_public_certificate_invalid'}
    }
    $receipt=[IO.File]::ReadAllText($receiptPath)|ConvertFrom-Json
    if($receipt.installationId-cne$Candidate.id-or$receipt.serviceName-cne$Candidate.serviceName){Stop-RcHere 'here_public_certificate_invalid'}
    $sourceBytes=[IO.File]::ReadAllBytes($source)
    if([Security.Cryptography.X509Certificates.X509Certificate2]::GetCertContentType($sourceBytes)-ne[Security.Cryptography.X509Certificates.X509ContentType]::Cert){Stop-RcHere 'here_public_certificate_invalid'}
    $certificate=New-Object Security.Cryptography.X509Certificates.X509Certificate2(,$sourceBytes)
    try{
        if($certificate.HasPrivateKey-or$certificate.Thumbprint-cne$receipt.trustedCaThumbprint){Stop-RcHere 'here_public_certificate_invalid'}
        $bytes=$certificate.Export([Security.Cryptography.X509Certificates.X509ContentType]::Cert)
        if(-not[IO.Directory]::Exists($DesktopDirectory)){return ''}
        $destination=Join-Path $DesktopDirectory ('RackClick-CA-'+$Candidate.id.Substring(0,8)+'-'+$certificate.Thumbprint.Substring(0,12)+'.cer')
        if([IO.File]::Exists($destination)){
            Assert-RcHereNoReparse $destination;if((Get-Item -LiteralPath $destination).Length-gt65536){Stop-RcHere 'here_public_certificate_invalid'}
            $existing=[IO.File]::ReadAllBytes($destination)
            if([Convert]::ToBase64String($existing)-cne[Convert]::ToBase64String($bytes)){Stop-RcHere 'here_public_certificate_invalid'}
        }else{$file=[IO.File]::Open($destination,'CreateNew','Write','None');try{$file.Write($bytes,0,$bytes.Length);$file.Flush($true)}finally{$file.Dispose()}}
        return $destination
    }finally{$certificate.Dispose()}
}
function Select-RcHereErrorText([string]$Code){
    switch($Code){
        'here_no_installations' {return 'No encuentro una instancia instalada de RackClick compatible con este acceso.'}
        'here_no_authorized_network' {return 'La VM no tiene una IPv4 activa de las redes 192.168.178.x o 192.168.250.x. Conecta su tarjeta a la red de casa o trabajo y vuelve a abrir este acceso.'}
        'here_engine_hash_mismatch' {return 'El archivo de mantenimiento no coincide con el paquete. Extrae de nuevo este ZIP en otra carpeta.'}
        'here_operation_pending_do_not_repeat' {return 'La operacion sigue pendiente. No la repitas ni cierres servicios manualmente. Conserva el informe del Escritorio.'}
        default {return 'No se pudo completar la conexion. Conserva el informe del Escritorio. Codigo: '+$Code}
    }
}

if($FunctionsOnly){return}
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$hereExit=2
try{
    if($PSVersionTable.PSEdition-cne'Desktop'-or$PSVersionTable.PSVersion.Major-ne5-or-not[Environment]::Is64BitProcess){Stop-RcHere 'here_winps51_x64_required'}
    $principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if(-not$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
        if($Elevated){Stop-RcHere 'here_administrator_required'}
        $parts=@('-STA','-NoProfile','-ExecutionPolicy','Bypass','-File',$PSCommandPath,'-Elevated')
        $process=Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -ArgumentList (($parts|ForEach-Object{ConvertTo-RcHereArgument $_})-join' ') -Verb RunAs -WindowStyle Hidden -PassThru
        $null=$process.Handle;$process.WaitForExit();$process.Refresh();$answer=$process.ExitCode;$process.Dispose();if($null-eq$answer){Stop-RcHere 'here_elevation_result_unknown'};exit $answer
    }
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    [Windows.Forms.Application]::EnableVisualStyles()
    $candidates=@(Get-RcHereCandidates)
    if($candidates.Count-eq0){Stop-RcHere 'here_no_installations'}
    $networks=@(Select-RcHereNetworks @(Get-NetIPAddress -AddressFamily IPv4) @(Get-NetAdapter) @(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue) @(Get-NetIPInterface -AddressFamily IPv4))
    if($networks.Count-eq0){Stop-RcHere 'here_no_authorized_network'}
    $form=New-Object Windows.Forms.Form;$form.Text='RackClick - conectar aqui';$form.Size=New-Object Drawing.Size(760,370);$form.StartPosition='CenterScreen';$form.FormBorderStyle='FixedDialog';$form.MaximizeBox=$false
    $intro=New-Object Windows.Forms.Label;$intro.Text='Usa la red actual de la VM, adapta RackClick y abre la web. Las bases y las cuentas se conservan.';$intro.Location=New-Object Drawing.Point(20,20);$intro.Size=New-Object Drawing.Size(700,45);$form.Controls.Add($intro)
    $instances=New-Object Windows.Forms.ComboBox;$instances.DropDownStyle='DropDownList';$instances.Location=New-Object Drawing.Point(20,80);$instances.Size=New-Object Drawing.Size(700,28);$instances.DisplayMember='label';foreach($candidate in $candidates){$null=$instances.Items.Add($candidate)};$instances.SelectedIndex=0;$form.Controls.Add($instances)
    $addresses=New-Object Windows.Forms.ComboBox;$addresses.DropDownStyle='DropDownList';$addresses.Location=New-Object Drawing.Point(20,125);$addresses.Size=New-Object Drawing.Size(700,28);$addresses.DisplayMember='label';foreach($network in $networks){$null=$addresses.Items.Add($network)};$addresses.SelectedIndex=0;$form.Controls.Add($addresses)
    $connect=New-Object Windows.Forms.Button;$connect.Text='Conectar y abrir RackClick';$connect.Location=New-Object Drawing.Point(20,175);$connect.Size=New-Object Drawing.Size(280,42);$form.Controls.Add($connect)
    $progress=New-Object Windows.Forms.ProgressBar;$progress.Location=New-Object Drawing.Point(20,230);$progress.Size=New-Object Drawing.Size(700,16);$form.Controls.Add($progress)
    $status=New-Object Windows.Forms.Label;$status.Text='Instancia restaurada seleccionada cuando existe. Pulsa Conectar.';$status.Location=New-Object Drawing.Point(20,260);$status.Size=New-Object Drawing.Size(700,65);$form.Controls.Add($status)
    $state=@{busy=$false;exitCode=2}
    $form.Add_FormClosing({param($sender,$event)if($state.busy){$event.Cancel=$true}})
    $connect.Add_Click({
        $state.busy=$true;$connect.Enabled=$false;$instances.Enabled=$false;$addresses.Enabled=$false;$progress.Style='Marquee';$status.Text='Preparando acceso seguro. El cambio de red puede tardar unos minutos.';[Windows.Forms.Application]::DoEvents()
        try{
            $candidate=$instances.SelectedItem;$network=$addresses.SelectedItem
            $pulse={param($seconds)$status.Text='Conectando '+$network.ip+' - '+$seconds+' s. Espera a que termine.';[Windows.Forms.Application]::DoEvents()}
            $report=Invoke-RcHereEngine $candidate $network (Join-Path $PSScriptRoot 'Set-RackClickInstanceNetwork.ps1') '@@ENGINE_SHA256@@' $pulse
            if($report.success){$publicCertificate='';try{$publicCertificate=Export-RcHerePublicCertificate $candidate}catch{};$report|Add-Member -NotePropertyName publicCertificatePath -NotePropertyValue $publicCertificate}
            $path=Save-RcHereReport $report
            if(-not$report.success){$status.Text=(Select-RcHereErrorText $report.code)+"`r`nInforme: "+$path;return}
            $status.Text='Listo: '+$report.publicOrigin;$state.exitCode=0
            Start-Process -FilePath $report.publicOrigin
            $state.busy=$false;$form.Close()
        }catch{
            $state.exitCode=2
            $code=if($_.Exception.Message-cmatch'^(?:here|network)_[a-z0-9_]+$'){$_.Exception.Message}else{'here_operation_failed'}
            $report=[ordered]@{schemaVersion=1;valid=$false;success=$false;exitCode=2;code=$code;stage='launcher';windowsNetworkChanged=$false;databasesChanged=$false};$path='';try{$path=Save-RcHereReport $report}catch{}
            $status.Text=(Select-RcHereErrorText $code)+"`r`nInforme: "+$path
        }finally{$state.busy=$false;$progress.Style='Blocks'}
    })
    $null=$form.ShowDialog();$hereExit=$state.exitCode;$form.Dispose()
}catch{
    $code=if($_.Exception.Message-cmatch'^here_[a-z0-9_]+$'){$_.Exception.Message}else{'here_start_failed'}
    $path='';try{$path=Save-RcHereReport ([ordered]@{schemaVersion=1;valid=$false;success=$false;exitCode=2;code=$code;stage='discovery';windowsNetworkChanged=$false;databasesChanged=$false})}catch{}
    try{Add-Type -AssemblyName System.Windows.Forms;$null=[Windows.Forms.MessageBox]::Show(((Select-RcHereErrorText $code)+"`r`nInforme: "+$path),'RackClick',[Windows.Forms.MessageBoxButtons]::OK,[Windows.Forms.MessageBoxIcon]::Error)}catch{}
}
exit $hereExit
