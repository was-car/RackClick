#requires -Version 5.1
# Cambio automatico de IP de la instalacion RackClick 05 (un solo CMD, con confirmacion SI).
# Detecta la instancia y la IPv4 privada actual de la VM, guarda copias y aplica el cambio con el motor verificado.
# No cambia la IP de Windows, las cuentas, las credenciales de PostgreSQL ni los datos.
$ErrorActionPreference = 'Stop'
$EngineSha256 = '@@ENGINE_SHA256@@'
$PayloadSha256 = '25a764a9fa40f0e8feb39cfbc9b2b3f1f21bb1137738edd53614b257f6277ec7'
. (Join-Path $PSScriptRoot 'Start-RackClickHere.ps1') -FunctionsOnly

function Say([string]$Message) { Write-Host $Message }
function Stop-Cambio([string]$Code) { throw (New-Object InvalidOperationException($Code)) }
function Get-Sha256Bytes([byte[]]$Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() } finally { $sha.Dispose() }
}
function Get-CurrentPrivateNetwork {
    $answer = @()
    foreach ($address in @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop)) {
        $text = [string]$address.IPAddress
        if ([string]$address.AddressState -cne 'Preferred' -or $text -notmatch '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)') { continue }
        $adapter = Get-NetAdapter -InterfaceIndex $address.InterfaceIndex -ErrorAction SilentlyContinue
        if (-not $adapter -or [string]$adapter.Status -cne 'Up') { continue }
        if (@(Get-NetRoute -InterfaceIndex $address.InterfaceIndex -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue).Count -eq 0) { continue }
        $bytes = ([Net.IPAddress]::Parse($text)).GetAddressBytes()
        $answer += [pscustomobject]@{ ip = $text; subnet = ('{0}.{1}.{2}.0/24' -f $bytes[0], $bytes[1], $bytes[2]) }
    }
    return @($answer)
}
function Get-RcCodeChanges($Manifest, [string]$Root, [string]$SourceRoot) {
    # Lists only installed files whose hash differs from the reviewed package; service binaries must match exactly.
    $answer = @()
    foreach ($file in @($Manifest.files)) {
        if ($file.path -cnotmatch '^(operators/[A-Za-z0-9_./-]+\.ps1|service/[A-Za-z0-9_.-]+\.dll)$') { continue }
        $target = Join-Path $Root ($file.path.Replace('/', '\'))
        $action = 'replace'
        if (-not (Test-Path -LiteralPath $target)) {
            # Scripts added after this installation was built: only reviewed operator scripts may be added.
            if ($file.path -cnotlike 'operators/*') { Stop-Cambio 'cambio_service_file_missing' }
            $action = 'add'
        } else {
            $current = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($current -ceq [string]$file.sha256) { continue }
            if ($file.path -cnotlike 'operators/*') { Stop-Cambio 'cambio_service_binary_changed' }
        }
        $source = Join-Path $SourceRoot ($file.path.Replace('/', '\'))
        if (-not (Test-Path -LiteralPath $source)) { Stop-Cambio 'cambio_source_missing' }
        if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$file.sha256) { Stop-Cambio 'cambio_source_mismatch' }
        $answer += [pscustomobject]@{ target = $target; source = $source; path = [string]$file.path; action = $action }
    }
    return @($answer)
}
function Invoke-CambioIp {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Say 'Ejecuta este CMD como administrador. No se ha cambiado nada.'; return 1 }
    if ($PSVersionTable.PSEdition -cne 'Desktop' -or $PSVersionTable.PSVersion.Major -ne 5 -or -not [Environment]::Is64BitProcess) { Say 'Se necesita Windows PowerShell 5.1 de 64 bits. No se ha cambiado nada.'; return 1 }

    $candidates = @(Get-RcHereCandidates)
    if ($candidates.Count -eq 0) { Say 'No encuentro una instalacion RackClick 05 valida en esta VM. No se ha cambiado nada.'; return 1 }
    $candidate = $candidates[0]
    if ($candidates.Count -gt 1) { Say ('Hay varias instalaciones. Se usa: ' + $candidate.label) }

    $networks = @(Get-CurrentPrivateNetwork)
    if ($networks.Count -ne 1) { Say ('La VM debe tener exactamente una IPv4 privada activa con ruta por defecto. Encontradas: ' + $networks.Count + '. No se ha cambiado nada.'); return 1 }
    $network = $networks[0]
    $newOrigin = 'https://' + $network.ip + ':' + [string]$candidate.httpsPort

    Say ''
    Say ('Instalacion:       ' + $candidate.serviceName + ' (' + $candidate.id + ')')
    Say ('Direccion actual:  ' + $candidate.origin)
    Say ('Direccion nueva:   ' + $newOrigin)
    Say ('Red autorizada:    ' + $network.subnet)
    Say ''
    Say 'Se cambian: IP de escucha, direccion web, certificado de la CA privada, regla de firewall y servicio.'
    Say 'No se cambian: IP de Windows, cuentas, credenciales PostgreSQL ni datos.'
    Say ''
    $answer = Read-Host 'Escribe SI para continuar'
    if ($answer -cne 'SI') { Say 'Cancelado. No se ha cambiado nada.'; return 1 }

    # Alinea el codigo instalado con el paquete revisado. Solo copia archivos cuyo hash esperado coincide con el paquete.
    $payloadPath = Join-Path $PSScriptRoot 'payload.json'
    $payloadBytes = [IO.File]::ReadAllBytes($payloadPath)
    if ((Get-Sha256Bytes $payloadBytes) -cne $PayloadSha256) { Stop-Cambio 'cambio_payload_mismatch' }
    $manifest = [Text.Encoding]::UTF8.GetString($payloadBytes) | ConvertFrom-Json
    $root = 'C:\Program Files\RackClick\' + $candidate.id
    if (-not (Test-Path -LiteralPath $root)) { Stop-Cambio 'cambio_code_root_missing' }
    $changes = @(Get-RcCodeChanges $manifest $root (Join-Path $PSScriptRoot 'payload'))
    $rootPayload = Join-Path $root 'payload.json'
    $rootPayloadChanged = ((Get-FileHash -LiteralPath $rootPayload -Algorithm SHA256).Hash.ToLowerInvariant() -cne $PayloadSha256)

    $stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
    $backup = Join-Path 'C:\RackClick-Respaldo-Script' ('cambio-ip-' + $stamp)
    New-Item -ItemType Directory -Path $backup | Out-Null
    $index = 0
    foreach ($change in @($changes | Where-Object { $_.action -ceq 'replace' })) { $index++; Copy-Item -LiteralPath $change.target -Destination (Join-Path $backup ('antes-' + $index + '-' + ($change.path -replace '[/\\]', '_'))) }
    $added = @($changes | Where-Object { $_.action -ceq 'add' } | ForEach-Object { $_.path })
    if ($added.Count) { Set-Content -LiteralPath (Join-Path $backup 'agregados.txt') -Value $added -Encoding ASCII }
    if ($rootPayloadChanged) { Copy-Item -LiteralPath $rootPayload -Destination (Join-Path $backup 'antes-payload.json') }
    Say ('Copia de seguridad: ' + $backup)

    foreach ($change in $changes) { Copy-Item -LiteralPath $change.source -Destination $change.target -Force }
    if ($rootPayloadChanged) { [IO.File]::WriteAllBytes($rootPayload, $payloadBytes) }
    Say ('Codigo alineado. Archivos actualizados: ' + $changes.Count + '. Payload actualizado: ' + $rootPayloadChanged)

    $engine = Join-Path $PSScriptRoot 'Set-RackClickInstanceNetwork.ps1'
    $report = Invoke-RcHereEngine $candidate $network $engine $EngineSha256 $null
    $publicCertificate = ''
    if ($report.success) { try { $publicCertificate = Export-RcHerePublicCertificate $candidate } catch { $publicCertificate = '' } }
    $path = Save-RcHereReport $report
    Say ''
    if ($report.success) {
        Say ('Listo. Abre en el navegador: ' + $report.publicOrigin)
        Say 'En tu PC, importa el certificado de la CA (archivo RackClick-CA-*.cer del Escritorio) en Entidades de certificacion raiz de confianza.'
        Say ('Certificado CA: ' + $publicCertificate)
        Say ('Informe: ' + $path)
        return 0
    }
    Say ('No se ha completado. Codigo: ' + [string]$report.code)
    Say ('Informe: ' + $path)
    return 2
}

# Dot-sourcing (tests) loads the functions only; running the file starts the change.
if ($MyInvocation.InvocationName -ne '.') {
    try { $exitCode = Invoke-CambioIp }
    catch {
        $code = if ($_.Exception.Message -cmatch '^[a-z0-9_]+$') { $_.Exception.Message } else { 'cambio_failed' }
        Say ('No se ha completado. Codigo: ' + $code)
        Say 'Conserva el informe del Escritorio y la carpeta C:\RackClick-Respaldo-Script de este intento.'
        $exitCode = 2
    }
    exit $exitCode
}
