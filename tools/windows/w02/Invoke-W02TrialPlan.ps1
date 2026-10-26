#requires -Version 5.1
# Ayuda de W-02 (edicion 08): comprobacion previa, validacion de la hoja de 15 campos y arranque guardado
# del recorrido New/Restore en una VM Windows Server 2025 limpia y no controladora de dominio.
# Check y Plan no cambian el host. Execute solo llega al envoltorio oficial si pasan, en este orden:
# exclusiones, allowlist, nombre confirmado, Plan validado de nuevo con el validador oficial (un informe local
# no es autoridad), Check nuevo y contenido del envoltorio comparado con el ZIP oficial fijado por hash.
# No sustituye al instalador: el recorrido sigue siendo el de INICIAR.ps1 del envoltorio.
[CmdletBinding()]
param(
    [ValidateSet('Check','Plan','Execute','Reconcile')][string]$Mode='Check',
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [string]$ArtifactDirectory='',
    [string]$PlanPath='',
    [string]$WrapperDirectory='',
    [string[]]$AllowedComputerName=@(),
    [string]$ConfirmComputerName='',
    # LEAO es el equipo de desarrollo y 192.168.250.78 la VM QA: nunca reciben esta prueba.
    [string[]]$ExcludedComputerName=@('LEAO'),
    [string[]]$ExcludedAddress=@('192.168.250.78'),
    [int]$HttpsPort=0,
    [int]$PostgresPort=0,
    # Solo para Reconcile: ruta de solo lectura al result.json preboot y a la carpeta de gestion de la instalacion.
    [string]$ResultPath='',
    [string]$ManagementPath=''
)
$ErrorActionPreference='Stop'
$script:W02Field=''
# Pins de la entrega 08 (.local/instalador-08-codex/entrega/SHA256SUMS.txt; perfil docs/INSTALADOR08-PERFIL.json).
# Cambiarlos exige una edicion nueva.
$Pins=[ordered]@{
    'RackClick-Servidor-08.zip'='2855898161ed94ff36fba73b11ac2bb02e9b4d9702e4af6976e946a7307561ae'
    'RackClick-Servidor-08-payload.zip'='f1988ba75ef8f278b5d64b81d7a8fb02d99a3be451e8ce70e2f97a4452538da4'
    'RackClick-Bundle-M3-14-08.zip'='a26856cb2bf3b9ed76384ebfe40fcc1587075708d3383e6b515246bfebb6da6f'
    'RackClick-Cambiar-IP-08.zip'='c070fa06cf40808e0d43197da743bed52c00361ce05f45549ff6498b3a36c6c8'
}
$WrapperZipName='RackClick-Servidor-08.zip'
$WrapperPrefix='RackClick-Servidor-08/'
$PayloadZipName='RackClick-Servidor-08-payload.zip'
$PayloadJsonSha='0d9df32b11a1c39df66cbb444739628eb8f867b06f55d2b3b3e45681ee29baa6'
# PAQUETE.json autentico dentro del ZIP oficial (833 bytes). Un manifiesto local, aunque coherente consigo mismo, no basta.
$PackageJsonSha='1f362949398b3da539a171b1150270599fa1761a0c7e1a7649aff31bc68972ac'
$Items=New-Object System.Collections.ArrayList
$Stamp=[DateTime]::UtcNow.ToString('o')
$RunnerSha=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()

function Add-W02Item([string]$Name,[string]$Status,[string]$Code,$Detail=$null){
    [void]$Items.Add([ordered]@{name=$Name;status=$Status;code=$Code;detail=$Detail})
}
function Get-W02Sha([string]$Path){(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
function Get-W02BytesSha([byte[]]$Bytes){
    $sha=[Security.Cryptography.SHA256]::Create()
    try{([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
}
function Get-W02EntryBytes($Entry){
    if($null -eq $Entry){throw 'execute_wrapper_files_unlisted'}
    $stream=$Entry.Open()
    try{$memory=New-Object IO.MemoryStream;$stream.CopyTo($memory);return ,$memory.ToArray()}finally{$stream.Dispose()}
}
function Get-W02EntrySha($Entry){
    if($null -eq $Entry){throw 'execute_wrapper_files_unlisted'}
    $stream=$Entry.Open()
    try{
        $sha=[Security.Cryptography.SHA256]::Create()
        try{$hash=([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
    }finally{$stream.Dispose()}
    return [ordered]@{size=[long]$Entry.Length;sha=$hash}
}
function ConvertTo-W02Code([string]$Message,[string]$Fallback){
    if($Message -cmatch '^[a-z][a-z0-9_]{1,100}$'){return $Message}
    return $Fallback
}
function Write-W02Json([string]$Name,$Value){
    $path=Join-Path $OutputDirectory $Name
    [IO.File]::WriteAllText($path,($Value|ConvertTo-Json -Depth 8),(New-Object Text.UTF8Encoding($false)))
    return $path
}
function Test-W02NoReparse([string]$Path,[string]$Code){
    $cursor=[IO.Path]::GetFullPath($Path)
    while($cursor){
        if(Test-Path -LiteralPath $cursor){
            if(((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw $Code}
        }
        $cursor=[IO.Path]::GetDirectoryName($cursor)
    }
}
# Diagnostico propio antes del validador oficial: caracteres de control o invalidos para ruta se rechazan con codigo y campo.
# No sustituye al validador oficial, que sigue haciendo todas las comprobaciones de la hoja.
function Assert-W02PlanText([string]$Path){
    if(-not (Test-Path -LiteralPath $Path -PathType Leaf)){throw 'plan_file_missing'}
    $text=[IO.File]::ReadAllText($Path)
    try{$plan=$text|ConvertFrom-Json}catch{throw 'plan_json_invalid'}
    $invalidPath=[IO.Path]::GetInvalidPathChars()
    foreach($property in $plan.PSObject.Properties){
        if($property.Value -isnot [string]){continue}
        $value=[string]$property.Value
        if($value -match '[\x00-\x1f]'){$script:W02Field=$property.Name;throw 'plan_field_control_character'}
        if($property.Name -eq 'backupPath' -and $value.Length -gt 0 -and $value.IndexOfAny($invalidPath) -ge 0){$script:W02Field=$property.Name;throw 'plan_field_invalid_path_character'}
    }
}
function Invoke-W02Check([int]$Https,[int]$Postgres){
    $script:Items=New-Object System.Collections.ArrayList
    $os=Get-CimInstance -ClassName Win32_OperatingSystem
    $cs=Get-CimInstance -ClassName Win32_ComputerSystem
    $osOk=($os.Caption -cmatch '^Microsoft Windows Server 2025') -and ($os.ProductType -eq 3)
    Add-W02Item 'sistema_operativo' $(if($osOk){'pass'}else{'fail'}) 'os_not_server_2025' ([ordered]@{caption=$os.Caption;version=$os.Version;build=$os.BuildNumber;productType=$os.ProductType})
    Add-W02Item 'nombre_no_excluido' $(if(@($ExcludedComputerName) | Where-Object {$_ -ieq $env:COMPUTERNAME}){'fail'}else{'pass'}) 'host_name_excluded' ([ordered]@{computerName=$env:COMPUTERNAME})
    Add-W02Item 'no_controlador_dominio' $(if($cs.DomainRole -ge 4){'fail'}else{'pass'}) 'domain_controller_not_allowed' ([ordered]@{domainRole=$cs.DomainRole})
    $addresses=@(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | ForEach-Object {$_.IPAddress})
    $excluded=@($addresses | Where-Object {$ExcludedAddress -contains $_})
    Add-W02Item 'direccion_no_excluida' $(if($excluded.Count){'fail'}else{'pass'}) 'excluded_address_host' ([ordered]@{addresses=$addresses})
    $services=@(Get-Service -ErrorAction SilentlyContinue | Where-Object {$_.Name -like 'RackClick*'} | ForEach-Object {$_.Name})
    Add-W02Item 'sin_servicio_rackclick' $(if($services.Count){'fail'}else{'pass'}) 'rackclick_service_present' ([ordered]@{services=$services})
    if($Https -le 0 -and $Postgres -le 0){Add-W02Item 'puertos' 'info' 'ports_not_checked' $null}
    foreach($port in @($Https,$Postgres)){
        if($port -gt 0){
            $busy=@(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
            Add-W02Item ('puerto_'+$port) $(if($busy.Count){'fail'}else{'pass'}) 'port_in_use' $null
        }
    }
    if(-not $ArtifactDirectory){
        Add-W02Item 'artefactos' 'fail' 'artifact_directory_required' $null
    } else {
        $dir=[IO.Path]::GetFullPath($ArtifactDirectory)
        foreach($name in $Pins.Keys){
            $file=Join-Path $dir $name
            $ok=(Test-Path -LiteralPath $file -PathType Leaf) -and ((Get-W02Sha $file) -ceq $Pins[$name])
            Add-W02Item ('artefacto:'+$name) $(if($ok){'pass'}else{'fail'}) 'artifact_hash_mismatch' $null
        }
        $payloadZip=Join-Path $dir $PayloadZipName
        $jsonOk=$false
        if(Test-Path -LiteralPath $payloadZip -PathType Leaf){
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            $zip=[IO.Compression.ZipFile]::OpenRead($payloadZip)
            try{
                $entry=$zip.GetEntry('RackClick-Instalador/payload.json')
                if($entry){$jsonOk=((Get-W02BytesSha (Get-W02EntryBytes $entry)) -ceq $PayloadJsonSha)}
            }finally{$zip.Dispose()}
        }
        Add-W02Item 'payload_json_pin' $(if($jsonOk){'pass'}else{'fail'}) 'payload_json_pin_mismatch' $null
    }
    $tools=@('dotnet','node','python') | Where-Object {Get-Command $_ -ErrorAction SilentlyContinue}
    Add-W02Item 'herramientas_previas' 'info' 'info' ([ordered]@{found=@($tools)})
    $failed=@($Items | Where-Object {$_.status -eq 'fail'})
    return [ordered]@{schemaVersion=1;kind='RackClickW02Check';status=$(if($failed.Count){'fail'}else{'pass'});code=$(if($failed.Count){[string]$failed[0].code}else{'w02_check_pass'});computerName=$env:COMPUTERNAME;generatedUtc=$Stamp;runnerSha256=$RunnerSha;httpsPort=$Https;postgresPort=$Postgres;items=@($Items)}
}
function Invoke-W02Plan {
    if(-not $ArtifactDirectory){throw 'w02_artifact_directory_required'}
    if(-not $PlanPath){throw 'w02_plan_path_required'}
    $payloadZip=Join-Path ([IO.Path]::GetFullPath($ArtifactDirectory)) $PayloadZipName
    if(-not (Test-Path -LiteralPath $payloadZip -PathType Leaf)){throw 'w02_payload_missing'}
    if((Get-W02Sha $payloadZip) -cne $Pins[$PayloadZipName]){throw 'w02_payload_hash_mismatch'}
    $planFull=[IO.Path]::GetFullPath($PlanPath)
    Assert-W02PlanText $planFull
    $stage=Join-Path $OutputDirectory ('payload-verificado-'+[guid]::NewGuid().ToString('N'))
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $saved=$env:PSModulePath
    try{
        # El ZIP completo ya esta fijado por hash: su contenido es el que se dot-source. El validador oficial no cambia el host.
        [IO.Compression.ZipFile]::ExtractToDirectory($payloadZip,$stage)
        $root=Join-Path $stage 'RackClick-Instalador'
        . (Join-Path $root 'operators\server-install\RackClick.Setup.ps1')
        $null=Assert-SetupPayload $root
        $plan=Read-SetupPlan $planFull
        return [ordered]@{schemaVersion=1;kind='RackClickW02Plan';status='pass';code='setup_plan_valid';computerName=$env:COMPUTERNAME;generatedUtc=$Stamp;runnerSha256=$RunnerSha;planSha256=(Get-W02Sha $planFull);planId=$plan.id;mode=$plan.mode;bindAddress=$plan.bindAddress;publicHost=$plan.publicHost;httpsPort=[int]$plan.httpsPort;postgresPort=[int]$plan.postgresPort;allowedSubnet=$plan.allowedSubnet;systemhaus=$plan.systemhaus;bootstrapUser=$plan.bootstrapUser;serviceName=$plan.serviceName;accountName=$plan.accountName;trustOnServer=$plan.trustOnServer;backupPath=$plan.backupPath;backupManifestSha256=$plan.backupManifestSha256;payloadSha256=$Pins[$PayloadZipName]}
    } finally {
        $env:PSModulePath=$saved
        if(Test-Path -LiteralPath $stage){Remove-Item -LiteralPath $stage -Recurse -Force}
    }
}
# Inventario y bytes autorizados: salen del ZIP oficial fijado por hash, no del directorio del operador.
function Get-W02AuthoritativeWrapper {
    $zipPath=Join-Path ([IO.Path]::GetFullPath($ArtifactDirectory)) $WrapperZipName
    if(-not (Test-Path -LiteralPath $zipPath -PathType Leaf)){throw 'execute_wrapper_zip_missing'}
    if((Get-W02Sha $zipPath) -cne $Pins[$WrapperZipName]){throw 'execute_wrapper_zip_hash_mismatch'}
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip=[IO.Compression.ZipFile]::OpenRead($zipPath)
    try{
        $members=@($zip.Entries|Where-Object {-not $_.FullName.EndsWith('/')})
        $names=@($members|ForEach-Object {$_.FullName})
        if(@($names|Select-Object -Unique).Count -ne $names.Count){throw 'execute_wrapper_files_unlisted'}
        foreach($name in $names){
            if(-not $name.StartsWith($WrapperPrefix,[StringComparison]::Ordinal) -or $name.Substring($WrapperPrefix.Length) -cnotmatch '^[A-Za-z0-9._-]+$'){throw 'execute_wrapper_member_invalid'}
        }
        $packageBytes=Get-W02EntryBytes $zip.GetEntry($WrapperPrefix+'PAQUETE.json')
        if((Get-W02BytesSha $packageBytes) -cne $PackageJsonSha){throw 'execute_wrapper_envelope_invalid'}
        $envelope=[Text.Encoding]::UTF8.GetString($packageBytes)|ConvertFrom-Json
        if($envelope.kind -cne 'RackClickCleanStartEnvelope' -or $envelope.edition -cne '08' -or $envelope.payloadSha256 -cne $Pins[$PayloadZipName]){throw 'execute_wrapper_envelope_invalid'}
        $listed=@($envelope.files|ForEach-Object {$_.path})
        $expected=@($listed+'PAQUETE.json')|Sort-Object
        $actual=@($names|ForEach-Object {$_.Substring($WrapperPrefix.Length)})|Sort-Object
        if(@(Compare-Object $expected $actual -CaseSensitive).Count -ne 0){throw 'execute_wrapper_files_unlisted'}
        $files=@()
        foreach($item in $envelope.files){
            $info=Get-W02EntrySha $zip.GetEntry($WrapperPrefix+$item.path)
            if($info.size -ne [long]$item.size -or $info.sha -cne $item.sha256){throw 'execute_wrapper_envelope_invalid'}
            $files+=[ordered]@{path=$item.path;size=$info.size;sha256=$info.sha}
        }
        return [ordered]@{packageSha256=$PackageJsonSha;names=@($actual|ForEach-Object {$_});files=$files}
    }finally{$zip.Dispose()}
}
# Bloqueo de los ficheros validados: cada uno se abre solo para lectura y sin compartir escritura ni borrado.
# Mientras esos identificadores existen, nadie puede modificar, reemplazar ni borrar esos bytes, y ambos lanzamientos
# leen exactamente los bytes comprobados. Los hashes se calculan sobre esos mismos identificadores.
function Lock-W02WrapperFiles($Auth){
    $wrapper=[IO.Path]::GetFullPath($WrapperDirectory)
    Test-W02NoReparse $wrapper 'execute_wrapper_reparse_not_allowed'
    if(-not (Test-Path -LiteralPath $wrapper -PathType Container)){throw 'execute_wrapper_directory_missing'}
    $children=@(Get-ChildItem -LiteralPath $wrapper -Force)
    if(@($children|Where-Object {$_.PSIsContainer}).Count){throw 'execute_wrapper_files_unlisted'}
    if(@($children|Where-Object {($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0}).Count){throw 'execute_wrapper_reparse_not_allowed'}
    $expected=@($Auth.names)|Sort-Object
    $actual=@($children|ForEach-Object {$_.Name})|Sort-Object
    if(@(Compare-Object $expected $actual -CaseSensitive).Count -ne 0){throw 'execute_wrapper_files_unlisted'}
    $locks=New-Object System.Collections.ArrayList
    try{
        foreach($name in $Auth.names){
            $path=Join-Path $wrapper $name
            $stream=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
            [void]$locks.Add([ordered]@{name=$name;stream=$stream})
            if(((Get-Item -LiteralPath $path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'execute_wrapper_reparse_not_allowed'}
        }
        Assert-W02LockedFiles $locks $Auth
    }catch{
        foreach($lock in $locks){$lock.stream.Dispose()}
        throw
    }
    return ,$locks
}
function Assert-W02LockedFiles($Locks,$Auth){
    # El manifiesto autorizado se comprueba primero: una alteracion coordinada de INICIAR y PAQUETE se clasifica como package_mismatch.
    $ordered=@($Locks|Where-Object {$_.name -ceq 'PAQUETE.json'})+@($Locks|Where-Object {$_.name -cne 'PAQUETE.json'})
    foreach($lock in $ordered){
        $stream=$lock.stream
        $stream.Position=0
        $sha=[Security.Cryptography.SHA256]::Create()
        try{$hash=([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
        if($lock.name -ceq 'PAQUETE.json'){
            if($hash -cne $Auth.packageSha256){throw 'execute_wrapper_package_mismatch'}
            continue
        }
        $item=@($Auth.files|Where-Object {$_.path -ceq $lock.name})
        if($item.Count -ne 1 -or $stream.Length -ne [long]$item[0].size -or $hash -cne $item[0].sha256){throw 'execute_wrapper_hash_mismatch'}
    }
}
# Publicacion nueva y atomica: escribe un temporal y lo mueve al nombre definitivo. Nunca reemplaza un fichero existente.
function Publish-W02File([string]$Dir,[string]$Name,$Value){
    if(-not (Test-Path -LiteralPath $Dir -PathType Container)){throw 'w02_run_directory_missing'}
    $final=Join-Path $Dir $Name
    if(Test-Path -LiteralPath $final){throw 'w02_publish_exists'}
    $tmp=Join-Path $Dir ($Name+'.'+[guid]::NewGuid().ToString('N')+'.tmp')
    $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($Value|ConvertTo-Json -Depth 8))
    $stream=[IO.File]::Open($tmp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
    [IO.File]::Move($tmp,$final)
    return $final
}
function Get-W02BootUtc { (Get-CimInstance -ClassName Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o') }
# Recogida de solo lectura: lee recibos y fases existentes y publica un informe nuevo. No invoca el envoltorio, el
# instalador, la limpieza, servicios, tareas, cuentas, SQL ni cambios de red, certificados o ACL.
function Test-W02Hex([object]$v){ ($v -is [string]) -and ($v -cmatch '^[0-9a-f]{64}$') }
function Test-W02Guid([object]$v){ ($v -is [string]) -and ($v -cmatch '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$') }
function ConvertTo-W02Utc([object]$v){
    # Solo fechas UTC explicitas (sufijo Z), como las escribe el productor con ToString('o').
    if(-not ($v -is [string])){return $null}
    if(-not ($v -cmatch '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,7})?Z$')){return $null}
    $d=[DateTime]::MinValue
    if([DateTime]::TryParse($v,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::AdjustToUniversal,[ref]$d)){return $d}
    return $null
}
# Problemas de contrato del recibo. Un hash escrito en el JSON no autentica por si solo el fichero: solo se valida forma.
function Get-W02ReceiptProblems($r,[string]$dirName,[string]$computer){
    $p=New-Object System.Collections.ArrayList
    if($r.schemaVersion -isnot [int] -or $r.schemaVersion -ne 1){[void]$p.Add('schema')}
    if($r.kind -cne 'RackClickW02Receipt'){[void]$p.Add('tipo')}
    if((-not (Test-W02Guid $r.runId)) -or ($r.runId -cne $dirName)){[void]$p.Add('runId')}
    if([string]$r.computerName -ine $computer){[void]$p.Add('equipo')}
    if($null -eq (ConvertTo-W02Utc $r.startedUtc)){[void]$p.Add('startedUtc')}
    if($null -eq (ConvertTo-W02Utc $r.bootUtc)){[void]$p.Add('bootUtc')}
    foreach($h in @('planSha256','packageSha256','payloadSha256','wrapperZipSha256','runnerSha256')){
        if(-not (Test-W02Hex $r.$h)){[void]$p.Add('hash:'+$h)}
    }
    return ,@($p)
}
function Read-W02Phase([string]$dir,[string]$name){
    $f=Join-Path $dir $name
    if(-not (Test-Path -LiteralPath $f -PathType Leaf)){return $null}
    return (Get-Content -LiteralPath $f -Raw -Encoding UTF8 | ConvertFrom-Json)
}
# Veredicto de las fases: contrato de cada fase y, despues, secuencia y orden de fechas. El productor no escribe una fase
# que la anterior no permite: una verificacion con exit distinto de cero detiene el flujo antes de 02b, 03 y 04.
function Get-W02PhaseVerdict($f02,$f02b,$f03,$f04,[string]$startedUtc){
    $c=New-Object System.Collections.ArrayList
    $s=New-Object System.Collections.ArrayList
    $limite=[DateTime]::UtcNow.AddMinutes(5)
    $obs=$null;$val=$null;$ini=$null;$fin=$null
    if($f02){
        if($f02.phase -cne 'verify'){[void]$c.Add('fase02_tipo')}
        if($f02.exitCode -isnot [int]){[void]$c.Add('fase02_exit')}
        $obs=ConvertTo-W02Utc $f02.observedUtc
        if($null -eq $obs -or $obs -gt $limite){[void]$c.Add('fase02_fecha')}
    }
    if($f02b){
        if($f02b.phase -cne 'validacion'){[void]$c.Add('fase02b_tipo')}
        if($f02b.valid -isnot [bool]){[void]$c.Add('fase02b_valid')}
        if($f02b.code -isnot [string]){[void]$c.Add('fase02b_code')}
        $val=ConvertTo-W02Utc $f02b.validatedUtc
        if($null -eq $val -or $val -gt $limite){[void]$c.Add('fase02b_fecha')}
    }
    if($f03){
        if($f03.phase -cne 'interactiva'){[void]$c.Add('fase03_tipo')}
        $ini=ConvertTo-W02Utc $f03.startedUtc
        if($null -eq $ini -or $ini -gt $limite){[void]$c.Add('fase03_fecha')}
    }
    if($f04){
        if($f04.phase -cne 'interactiva'){[void]$c.Add('fase04_tipo')}
        if($f04.exitCode -isnot [int]){[void]$c.Add('fase04_exit')}
        $fin=ConvertTo-W02Utc $f04.finishedUtc
        if($null -eq $fin -or $fin -gt $limite){[void]$c.Add('fase04_fecha')}
    }
    if($c.Count -gt 0){return @{contrato=@($c);secuencia=@()}}
    if($f02b -and -not $f02){[void]$s.Add('falta_fase02')}
    if($f02 -and ($f02.exitCode -ne 0) -and ($f02b -or $f03 -or $f04)){[void]$s.Add('fase02_distinta_de_cero_con_continuacion')}
    if($f03 -and -not ($f02b -and ($f02b.valid -eq $true))){[void]$s.Add('fase03_sin_validacion_positiva')}
    if($f04 -and -not $f03){[void]$s.Add('fase04_sin_fase03')}
    $inicioRecibo=ConvertTo-W02Utc $startedUtc
    if(($null -ne $inicioRecibo) -and ($null -ne $obs) -and ($inicioRecibo -gt $obs)){[void]$s.Add('orden_recibo_fase02')}
    if(($null -ne $obs) -and ($null -ne $val) -and ($val -lt $obs)){[void]$s.Add('orden_fase02_fase02b')}
    if(($null -ne $val) -and ($null -ne $ini) -and ($ini -lt $val)){[void]$s.Add('orden_fase02b_fase03')}
    if(($null -ne $ini) -and ($null -ne $fin) -and ($fin -lt $ini)){[void]$s.Add('orden_fase03_fase04')}
    return @{contrato=@();secuencia=@($s)}
}
# Contrato del postboot que escribe Test-RackClickServerAfterReboot: tipos, resultado coherente y fechas. Un documento
# contradictorio no se clasifica como verificado aunque success y code parezcan correctos.
function Get-W02PostbootProblems($p,[DateTime]$limite){
    $c=New-Object System.Collections.ArrayList
    if($p.schemaVersion -isnot [int] -or $p.schemaVersion -ne 1){[void]$c.Add('schema')}
    foreach($b in @('valid','success','rebootVerified','productAdopted')){if($p.$b -isnot [bool]){[void]$c.Add('tipo:'+$b)}}
    if($p.exitCode -isnot [int]){[void]$c.Add('tipo:exitCode')}
    if($p.code -isnot [string]){[void]$c.Add('tipo:code')}
    if($p.productAdopted -eq $true){[void]$c.Add('productAdopted_verdadero')}
    $check=ConvertTo-W02Utc $p.checkedUtc
    if($null -eq $check){[void]$c.Add('checkedUtc')} elseif($check -gt $limite){[void]$c.Add('checkedUtc_futuro')}
    if($null -ne $p.bootUtc){
        $arranque=ConvertTo-W02Utc $p.bootUtc
        if($null -eq $arranque){[void]$c.Add('bootUtc')}
        elseif(($null -ne $check) -and ($check -lt $arranque)){[void]$c.Add('checkedUtc_anterior_al_arranque')}
    }
    if(($null -ne $p.installationId) -and -not (Test-W02Guid ([string]$p.installationId).ToLowerInvariant())){[void]$c.Add('installationId')}
    if($p.success -eq $true){
        if(-not ($p.valid -eq $true -and $p.exitCode -eq 0 -and $p.code -ceq 'postboot_verified' -and $p.rebootVerified -eq $true)){[void]$c.Add('resultado_verificado_incoherente')}
    } elseif($p.valid -eq $true -or $p.rebootVerified -eq $true -or $p.exitCode -eq 0 -or $p.code -ceq 'postboot_verified'){
        [void]$c.Add('resultado_fallido_incoherente')
    }
    return ,@($c)
}
# Recogida de solo lectura: lee recibos y fases existentes y publica un informe nuevo. No invoca el envoltorio, el
# instalador, la limpieza, servicios, tareas, cuentas, SQL ni cambios de red, certificados o ACL.
function Invoke-W02Reconcile {
    $od=[IO.Path]::GetFullPath($OutputDirectory)
    $computer=$env:COMPUTERNAME
    $boot=Get-W02BootUtc
    $runsRoot=Join-Path $od 'runs'
    $runs=New-Object System.Collections.ArrayList
    $orden=New-Object System.Collections.ArrayList
    if(Test-Path -LiteralPath $runsRoot -PathType Container){
        foreach($d in @(Get-ChildItem -LiteralPath $runsRoot -Directory | Sort-Object Name)){
            $e=[ordered]@{runId=$d.Name;estado='';motivo='';exitCode=$null;startedUtc='';referencias=@()}
            $receipt=$null
            $rp=Join-Path $d.FullName 'recibo-inicio.json'
            if(Test-Path -LiteralPath $rp -PathType Leaf){
                try{$receipt=Get-Content -LiteralPath $rp -Raw -Encoding UTF8 | ConvertFrom-Json}catch{$receipt=$null}
            }
            if($null -eq $receipt){
                $e.estado='recibo_incoherente'; $e.motivo='recibo ausente o ilegible'
                [void]$runs.Add($e); continue
            }
            $problemas=Get-W02ReceiptProblems $receipt $d.Name $computer
            if($problemas.Count -gt 0){
                $e.estado='recibo_incoherente'; $e.motivo=('contrato: '+($problemas -join ', '))
                $e.startedUtc=[string]$receipt.startedUtc
                [void]$runs.Add($e); [void]$orden.Add([pscustomobject]@{runId=$d.Name;utc=(ConvertTo-W02Utc $receipt.startedUtc);estado=$e.estado}); continue
            }
            $e.startedUtc=[string]$receipt.startedUtc
            [void]$orden.Add([pscustomobject]@{runId=$d.Name;utc=(ConvertTo-W02Utc $receipt.startedUtc);estado=''})
            # Referencias: se declaran, no se rechaza automaticamente una historia de otra version del auxiliar.
            if($receipt.wrapperZipSha256 -cne $Pins[$WrapperZipName] -or $receipt.payloadSha256 -cne $Pins[$PayloadZipName]){$e.referencias+='pins_distintos_de_referencia'}
            if($receipt.runnerSha256 -cne $RunnerSha){$e.referencias+='auxiliar_distinto_del_lector'}
            if([string]$receipt.bootUtc -cne $boot){$e.referencias+='arranque_anterior'}
            try{
                $f02=Read-W02Phase $d.FullName 'fase-02-verify.json'
                $f02b=Read-W02Phase $d.FullName 'fase-02b-validacion.json'
                $f03=Read-W02Phase $d.FullName 'fase-03-interactiva-inicio.json'
                $f04=Read-W02Phase $d.FullName 'fase-04-interactiva-fin.json'
                # Hechos individuales tal como se leyeron; se conservan aunque la secuencia resulte incoherente.
                $e.hechos=[ordered]@{fase02Exit=$(if($f02){$f02.exitCode}else{$null});fase02bValid=$(if($f02b){$f02b.valid}else{$null});fase03Inicio=$(if($f03){$f03.startedUtc}else{$null});fase04Exit=$(if($f04){$f04.exitCode}else{$null})}
                $veredicto=Get-W02PhaseVerdict $f02 $f02b $f03 $f04 ([string]$receipt.startedUtc)
                if($veredicto.contrato.Count -gt 0){throw ('contrato_incoherente: '+($veredicto.contrato -join ', '))}
                if($veredicto.secuencia.Count -gt 0){throw ('secuencia_incoherente: '+($veredicto.secuencia -join ', '))}
                if($f04){
                    $e.estado='exit_observado'; $e.exitCode=$f04.exitCode
                } elseif($f03){
                    $e.estado='unknown'; $e.motivo='fase interactiva iniciada sin salida observada'
                } elseif($f02){
                    if($f02.exitCode -ne 0){$e.estado='verificacion_fallida'; $e.exitCode=$f02.exitCode}
                    elseif(-not $f02b){$e.estado='validez_desconocida'; $e.motivo='salida nativa 0 sin validacion del JSON registrada; no es una verificacion negativa'}
                    elseif($f02b.valid -eq $true){$e.estado='interrumpido'; $e.motivo='verificacion correcta sin fase interactiva'}
                    else {$e.estado='verificacion_negativa'}
                } else {
                    $e.estado='unknown'; $e.motivo='sin verificacion observada'
                }
            } catch {
                $msg=[string]$_.Exception.Message
                if($msg -clike 'secuencia_incoherente:*'){$e.estado='secuencia_incoherente'} else {$e.estado='contrato_incoherente'}
                $e.motivo=$msg
            }
            $orden[$orden.Count-1].estado=$e.estado
            [void]$runs.Add($e)
        }
    }
    # Seleccion explicita: el intento mas reciente por fecha de inicio validada; nunca por nombre.
    $estado='evidencia_incompleta'; $ultimo=''
    if($runs.Count -gt 0){
        if(@($orden | Where-Object { $null -eq $_.utc }).Count -gt 0 -or @($orden).Count -ne $runs.Count){
            $estado='seleccion_ambigua'; $ultimo=''
        } else {
            $ordenados=@($orden | Sort-Object utc -Descending)
            if($ordenados.Count -gt 1 -and $ordenados[0].utc -eq $ordenados[1].utc){
                $estado='seleccion_ambigua'
            } else {
                $estado=[string]$ordenados[0].estado; $ultimo=[string]$ordenados[0].runId
            }
        }
    }
    # Instalacion (preboot, solo lectura: no se sobrescribe) y verificacion posterior al reinicio, por separado.
    $install=$null
    if($ResultPath){
        if(Test-Path -LiteralPath $ResultPath -PathType Leaf){
            $r=Get-Content -LiteralPath $ResultPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $id=''
            if([string]$r.managementPath -match '([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})'){$id=$matches[1].ToLowerInvariant()}
            $install=[ordered]@{origen='preboot (result.json, sin sobrescribir)';stage=$r.stage;code=$r.code;exitCode=$r.exitCode;installationId=$id}
        } else {
            $install=[ordered]@{estado='no_disponible'}
        }
    }
    $post=$null
    if($ManagementPath){
        $pp=Join-Path $ManagementPath 'postboot-verification.json'
        if(Test-Path -LiteralPath $pp -PathType Leaf){
            $p=Get-Content -LiteralPath $pp -Raw -Encoding UTF8 | ConvertFrom-Json
            $pid_=[string]$p.installationId
            $instId=''
            if($install -and $install.installationId){$instId=[string]$install.installationId}
            $post=[ordered]@{origen='postboot (postboot-verification.json)';code=[string]$p.code;success=$p.success;rebootVerified=$p.rebootVerified;installationId=$pid_;bootUtc=[string]$p.bootUtc;vinculo='parcial: el postboot no declara equipo ni ejecucion';saludActual='no_comprobada_por_reconcile'}
            $problemas=Get-W02PostbootProblems $p ([DateTime]::UtcNow.AddMinutes(5))
            if($problemas.Count -gt 0){
                $post.estado='postboot_contrato_incoherente'; $post.motivo=('contrato: '+($problemas -join ', '))
            } elseif(-not $instId -or -not $pid_ -or $null -eq $p.bootUtc){
                $post.estado='vinculo_incompleto'; $post.motivo='postboot sin installationId o bootUtc completos; no se liga a la instalacion ni al arranque'
            } elseif(-not ($pid_ -ieq $instId)){$post.estado='postboot_de_otra_instalacion'}
            elseif([string]$p.bootUtc -cne $boot){$post.estado='postboot_desfasado'}
            elseif($p.success -eq $true){$post.estado='postboot_verificado_vinculo_parcial'}
            else {$post.estado='postboot_fallido'}
            $post.verificacionRegistrada=($post.estado -ceq 'postboot_verificado_vinculo_parcial')
        } else {
            $post=[ordered]@{estado='verificacion_no_disponible'}
        }
    }
    $report=[ordered]@{schemaVersion=1;kind='RackClickW02Reconciliacion';generatedUtc=[DateTime]::UtcNow.ToString('o');computerName=$computer;bootUtc=$boot;estado=$estado;ultimoIntentoRunId=$ultimo;runs=@($runs);installacion=$install;verificacionPostboot=$post;nota='Recogida de solo lectura: no se ha invocado el envoltorio, el instalador ni ninguna accion sobre la VM. Los recibos y resultados existentes no se han modificado. Las entradas se listan con su estado individual; el estado global corresponde solo al intento mas reciente por fecha. Los pins y el auxiliar declarados en cada recibo no autentican el recibo ni prueban la procedencia de los bytes. La verificacion postboot es un registro del arranque indicado; no comprueba la salud actual del servicio.'}
    return (Publish-W02File $od ('reconciliacion-'+[guid]::NewGuid().ToString('D')+'.json') $report)
}
function Invoke-W02Execute {
    $computer=$env:COMPUTERNAME
    if(@($ExcludedComputerName) | Where-Object {$_ -ieq $computer}){throw 'execute_host_excluded'}
    if(-not (@($AllowedComputerName) | Where-Object {$_ -ieq $computer})){throw 'execute_host_not_allowlisted'}
    if($ConfirmComputerName -ine $computer){throw 'execute_confirmation_mismatch'}
    if(-not $PlanPath -or -not $ArtifactDirectory -or -not $WrapperDirectory){throw 'execute_inputs_required'}
    # El plan-report.json anterior no es autoridad: la hoja se valida de nuevo ahora y su resultado sustituye al anterior.
    try{$plan=Invoke-W02Plan}catch{
        # Un fallo de validacion tambien queda en el informe de Plan: no puede quedar un "pass" anterior a la vista.
        $planCode=ConvertTo-W02Code ([string]$_.Exception.Message) 'w02_plan_failed'
        [void](Write-W02Json 'plan-report.json' ([ordered]@{schemaVersion=1;kind='RackClickW02Plan';status='fail';code=$planCode;field=$script:W02Field;computerName=$computer;generatedUtc=[DateTime]::UtcNow.ToString('o');runnerSha256=$RunnerSha}))
        throw
    }
    [void](Write-W02Json 'plan-report.json' $plan)
    $check=Invoke-W02Check ([int]$plan.httpsPort) ([int]$plan.postgresPort)
    [void](Write-W02Json 'check-report.json' $check)
    if($check.status -cne 'pass'){throw 'execute_check_not_passed'}
    $auth=Get-W02AuthoritativeWrapper
    $wrapper=[IO.Path]::GetFullPath($WrapperDirectory)
    $entry=Join-Path $wrapper 'INICIAR.ps1'
    if($entry.Contains('"')){throw 'execute_path_invalid'}
    # Cada intento tiene su carpeta nueva, con sus diagnosticos. Nada de esta carpeta se reutiliza ni se sobrescribe.
    $runId=[guid]::NewGuid().ToString('D')
    $runDir=Join-Path (Join-Path $OutputDirectory 'runs') $runId
    New-Item -ItemType Directory -Path $runDir -ErrorAction Stop | Out-Null
    [void](Publish-W02File $runDir 'plan-validado.json' $plan)
    [void](Publish-W02File $runDir 'check-validado.json' $check)
    $locks=Lock-W02WrapperFiles $auth
    try{
        $ps=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
        $started=[DateTime]::UtcNow.ToString('o')
        $receipt=[ordered]@{schemaVersion=1;kind='RackClickW02Receipt';runId=$runId;computerName=$computer;startedUtc=$started;bootUtc=(Get-W02BootUtc);planSha256=$plan.planSha256;planId=$plan.planId;mode=$plan.mode;httpsPort=$plan.httpsPort;postgresPort=$plan.postgresPort;runnerSha256=$RunnerSha;wrapperZipSha256=$Pins[$WrapperZipName];packageSha256=$auth.packageSha256;payloadSha256=$Pins[$PayloadZipName];locked=@($auth.files|ForEach-Object {[ordered]@{path=$_.path;sha256=$_.sha256}})}
        [void](Publish-W02File $runDir 'recibo-inicio.json' $receipt)
        # Primera llamada -VerifyOnly: salida nativa observada y diagnosticos dentro de la carpeta del intento.
        $verifyOut=Join-Path $runDir 'execute-verify-salida.json'
        $verify=Start-Process -FilePath $ps -ArgumentList @('-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',('"'+$entry+'"'),'-VerifyOnly') -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $verifyOut -RedirectStandardError ($verifyOut+'.err')
        [void](Publish-W02File $runDir 'fase-02-verify.json' ([ordered]@{phase='verify';exitCode=$verify.ExitCode;observedUtc=[DateTime]::UtcNow.ToString('o')}))
        if($verify.ExitCode -ne 0){throw 'execute_verify_failed'}
        try{$verifyResult=Get-Content -LiteralPath $verifyOut -Raw|ConvertFrom-Json}catch{throw 'execute_verify_unreadable'}
        # Validacion del JSON, en su propia fase: una lectura sin validacion registrada no es una verificacion negativa.
        [void](Publish-W02File $runDir 'fase-02b-validacion.json' ([ordered]@{phase='validacion';valid=[bool]($verifyResult.valid -eq $true);code=[string]$verifyResult.code;validatedUtc=[DateTime]::UtcNow.ToString('o')}))
        if($verifyResult.valid -ne $true){throw 'execute_verify_failed'}
        # Antes de la segunda llamada, los mismos bytes bloqueados se vuelven a comprobar contra la autoridad.
        Assert-W02LockedFiles $locks $auth
        [void](Publish-W02File $runDir 'fase-03-interactiva-inicio.json' ([ordered]@{phase='interactiva';startedUtc=[DateTime]::UtcNow.ToString('o')}))
        # Flujo oficial interactivo: se registra la salida observada del proceso. Si el padre desaparece, la fase queda abierta.
        $run=Start-Process -FilePath $ps -ArgumentList @('-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',('"'+$entry+'"')) -Wait -PassThru
        [void](Publish-W02File $runDir 'fase-04-interactiva-fin.json' ([ordered]@{phase='interactiva';exitCode=$run.ExitCode;finishedUtc=[DateTime]::UtcNow.ToString('o')}))
    }finally{
        foreach($lock in $locks){$lock.stream.Dispose()}
    }
    return [ordered]@{schemaVersion=1;kind='RackClickW02Execute';status='official_flow_exited';code='w02_official_flow_exited';computerName=$computer;runId=$runId;runDir=$runDir;receipt='recibo-inicio.json';proyeccion='ultimo_estado_del_directorio';startedUtc=$started;finishedUtc=[DateTime]::UtcNow.ToString('o');exitCode=$run.ExitCode;verifyCode=[string]$verifyResult.code;runnerSha256=$RunnerSha;wrapperFiles=@($auth.files);nextStep='Si el instalador pide reinicio, reiniciar. Despues abrir RackClick-VERIFICAR-05-*.cmd del Escritorio creado por esta edicion 08 y pulsar Verificar instalacion. No repetir Execute, INICIAR ni la limpieza.'}
}

try{
    [void](New-Item -ItemType Directory -Force -Path $OutputDirectory)
    $OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
    switch($Mode){
        'Check'   {$report=Invoke-W02Check $HttpsPort $PostgresPort;$name='check-report.json'}
        'Plan'    {$report=Invoke-W02Plan;$name='plan-report.json'}
        'Execute' {$report=Invoke-W02Execute;$name='execute-report.json'}
        'Reconcile' {$path=Invoke-W02Reconcile;Write-Output ('W-02 Reconcile: lectura completada. Informe: '+$path);exit 0}
    }
    $path=Write-W02Json $name $report
    Write-Output ('W-02 '+$Mode+': '+$report.status+' ('+$report.code+'). Informe: '+$path)
    if($report.status -ceq 'fail'){exit 1}
    exit 0
}catch{
    $code=[string]$_.Exception.Message
    if($code -cnotmatch '^[a-z][a-z0-9_]{1,100}$'){$code='w02_'+$Mode.ToLowerInvariant()+'_failed'}
    $text=[string]$_.Exception.Message;if($text.Length-gt300){$text=$text.Substring(0,300)}
    $refusal=[ordered]@{schemaVersion=1;kind='RackClickW02'+$Mode;status='fail';code=$code;detail=$text;field=$script:W02Field;computerName=$env:COMPUTERNAME;generatedUtc=[DateTime]::UtcNow.ToString('o');runnerSha256=$RunnerSha}
    if($Mode -eq 'Reconcile'){
        if(Test-Path -LiteralPath $OutputDirectory){[void](Publish-W02File $OutputDirectory ('reconciliacion-error-'+[guid]::NewGuid().ToString('D')+'.json') $refusal)}
    } else {
        $name=@{Check='check-report.json';Plan='plan-report.json';Execute='execute-report.json'}[$Mode]
        if(Test-Path -LiteralPath $OutputDirectory){[void](Write-W02Json $name $refusal)}
    }
    Write-Output ('W-02 '+$Mode+': fail ('+$code+').')
    exit 1
}
