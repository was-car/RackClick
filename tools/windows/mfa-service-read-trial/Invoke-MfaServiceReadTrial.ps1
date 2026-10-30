#requires -Version 5.1
# Comprobador de lectura L2l02 (token efectivo del servicio). NO activa MFA, no toca el servicio ni su cuenta, no escribe en el
# almacen y no emite claves. Check: solo lectura; no ejecuta el comprobador. Run: exige consola elevada, paquete verificado,
# servicio inequivoco y confirmacion escrita; ejecuta el comprobador una sola vez y compara huellas antes y despues.
# SelfTest: funciones puras; no toca el sistema. LEAO se rechaza en Check y Run antes de leer nada.
[CmdletBinding()]
param(
    [ValidateSet('Check', 'Run', 'SelfTest')][string]$Mode = 'Check',
    [string]$ServiceName = '',
    [string]$TrialRoot = '',
    [string]$ExpectedSumsSha256 = '',
    [ValidateRange(10, 300)][int]$TimeoutSeconds = 120
)
$ErrorActionPreference = 'Stop'

$PackageName = 'RackClick-MFA-Lectura-L2l02'
$TrialPrefix = 'RackClick-MFA-Ensayo-03-'
$ExcludedHosts = @('LEAO')
$HighIntegritySid = 'S-1-16-12288'
$RuntimeExeRel = 'runtime/dotnet.exe'
$ProbeDllRel = 'probe/RackClick.MfaServiceReadProbe.dll'
$RequiredRel = @(
    'LEEME-LECTURA-L2L02.txt', 'Invoke-MfaServiceReadTrial.ps1', 'BUILD-MANIFEST.json', 'SHA256SUMS',
    'runtime/dotnet.exe', 'runtime/LICENSE.txt', 'runtime/ThirdPartyNotices.txt',
    'probe/RackClick.MfaServiceReadProbe.dll', 'probe/RackClick.MfaServiceReadProbe.runtimeconfig.json',
    'probe/RackClick.Server.dll', 'licenses/Npgsql-LICENSE', 'licenses/Otp.NET-LICENSE.txt', 'licenses/README.txt'
)
# Verbos que este script puede pedir al comprobador. Los verbos selftest-* nunca se usan en Run.
$ProbeVerbForRun = 'read'

function Stop-Trial([string]$Code) { throw ('trial:' + $Code) }

function Get-TrialCodeFromError($ErrorRecord) {
    $message = [string]$ErrorRecord.Exception.Message
    if ($message -match '^trial:([a-z][a-z0-9_]{1,100})$') { return $Matches[1] }
    return 'unexpected_error'
}

function Get-ThrownTrialCode([scriptblock]$Block) {
    try { $null = & $Block } catch { return (Get-TrialCodeFromError $_) }
    return ''
}

function Write-Line([string]$Text) { Write-Host $Text }

function Get-RelPath([string]$Root, [string]$Full) {
    $prefix = $Root.TrimEnd('\') + '\'
    return $Full.Substring($prefix.Length).Replace('\', '/')
}

function Get-Sha256Hex([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-TextSha256([string]$Text) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}

function Test-LabHostExcluded {
    foreach ($name in $ExcludedHosts) {
        if (($env:COMPUTERNAME -ieq $name) -or ([Environment]::MachineName -ieq $name)) { return $true }
    }
    return $false
}

function Test-ElevationRows([string[]]$CsvLines) {
    $rows = @($CsvLines | Where-Object { $_ -match '[^\s]' } | ConvertFrom-Csv -Header 'Name', 'Type', 'Sid', 'Attributes')
    return [bool]($rows | Where-Object { $_.Sid -eq $HighIntegritySid })
}

function Read-WhoamiGroups {
    $output = & (Join-Path $env:SystemRoot 'System32\whoami.exe') /groups /fo csv
    if ($LASTEXITCODE -ne 0) { Stop-Trial 'elevation_unobservable' }
    return @($output)
}

function ConvertFrom-SumsLine([string]$Line) {
    $match = [regex]::Match($Line, '^([0-9a-f]{64})  (.+)$')
    if (-not $match.Success) { Stop-Trial 'package_sums_malformed' }
    return @{ sha256 = $match.Groups[1].Value; rel = $match.Groups[2].Value }
}

# Integridad del paquete: cada archivo listado y con su hash, sin extras ni faltantes, sin puntos de reparse.
function Test-PackageIntegrity([string]$Root, [string]$ExpectedSums) {
    $sumsPath = Join-Path $Root 'SHA256SUMS'
    if (-not (Test-Path -LiteralPath $sumsPath -PathType Leaf)) { Stop-Trial 'package_sums_missing' }
    $sumsSha = Get-Sha256Hex $sumsPath
    if ($ExpectedSums -and ($sumsSha -ne $ExpectedSums.ToLowerInvariant())) { Stop-Trial 'package_sums_mismatch' }
    $listed = @{}
    foreach ($line in [IO.File]::ReadAllLines($sumsPath)) {
        $entry = ConvertFrom-SumsLine $line
        if ($listed.ContainsKey($entry.rel)) { Stop-Trial 'package_sums_duplicate' }
        $listed[$entry.rel] = $entry.sha256
    }
    $items = @(Get-ChildItem -LiteralPath $Root -Recurse -Force)
    if (@($items | Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 }).Count -gt 0) {
        Stop-Trial 'package_reparse_point'
    }
    $seen = 0
    foreach ($item in $items) {
        if ($item.PSIsContainer) { continue }
        $rel = Get-RelPath $Root $item.FullName
        if ($rel -eq 'SHA256SUMS') { continue }
        if (-not $listed.ContainsKey($rel)) { Stop-Trial 'package_file_unlisted' }
        if ((Get-Sha256Hex $item.FullName) -ne $listed[$rel]) { Stop-Trial 'package_hash_mismatch' }
        $seen++
    }
    foreach ($rel in $listed.Keys) {
        if (-not (Test-Path -LiteralPath (Join-Path $Root $rel.Replace('/', '\')) -PathType Leaf)) { Stop-Trial 'package_file_missing' }
    }
    foreach ($rel in $RequiredRel) {
        if ($rel -eq 'SHA256SUMS') { continue }
        if (-not $listed.ContainsKey($rel)) { Stop-Trial 'package_required_missing' }
    }
    return @{ sumsSha256 = $sumsSha; fileCount = $seen }
}

# Raiz del ensayo: explicita, o la unica carpeta RackClick-MFA-Ensayo-03-<UUID> de ProgramData. Con varias, se detiene.
function Resolve-TrialRoot([string]$Explicit) {
    if ($Explicit) {
        if (-not (Test-Path -LiteralPath $Explicit -PathType Container)) { Stop-Trial 'trial_root_missing' }
        $name = Split-Path -Leaf $Explicit
        if (-not $name.StartsWith($TrialPrefix, [StringComparison]::Ordinal)) { Stop-Trial 'trial_root_name_invalid' }
        return $Explicit
    }
    $candidates = @(Get-ChildItem -LiteralPath $env:ProgramData -Directory -Filter ($TrialPrefix + '*') -ErrorAction Stop)
    if ($candidates.Count -eq 0) { Stop-Trial 'trial_root_none' }
    if ($candidates.Count -gt 1) { Stop-Trial 'trial_root_ambiguous' }
    return $candidates[0].FullName
}

function Get-InstallationId([string]$Root) {
    $leaf = Split-Path -Leaf $Root
    $guid = $leaf.Substring($TrialPrefix.Length)
    $parsed = [guid]::Empty
    if (-not [guid]::TryParseExact($guid, 'D', [ref]$parsed)) { Stop-Trial 'trial_root_name_invalid' }
    return $parsed.ToString('D')
}

# Huella del almacen: rutas, tamanos, SHA256 de cada archivo y SDDL de cada entrada (raiz incluida). No guarda contenidos.
function Get-StoreFingerprint([string]$Root) {
    $entries = @([ordered]@{ path = '.'; type = 'dir'; bytes = 0; sha256 = ''; aclSha256 = (Get-TextSha256 ((Get-Acl -LiteralPath $Root).Sddl)) })
    foreach ($item in @(Get-ChildItem -LiteralPath $Root -Recurse -Force | Sort-Object FullName)) {
        $rel = Get-RelPath $Root $item.FullName
        if ($item.PSIsContainer) {
            $type = 'dir'; $bytes = 0; $sha = ''
        } else {
            $type = 'file'; $bytes = [long]$item.Length; $sha = Get-Sha256Hex $item.FullName
        }
        $aclSha = Get-TextSha256 ((Get-Acl -LiteralPath $item.FullName).Sddl)
        $entries += [ordered]@{ path = $rel; type = $type; bytes = $bytes; sha256 = $sha; aclSha256 = $aclSha }
    }
    $canonical = (@($entries | ForEach-Object { '{0}|{1}|{2}|{3}|{4}' -f $_.path, $_.type, $_.bytes, $_.sha256, $_.aclSha256 })) -join "`n"
    return [ordered]@{ count = $entries.Count; digest = (Get-TextSha256 $canonical) }
}

# Entorno del hijo: el mismo aislamiento aprobado en el ensayo 03 (sin profiler, EventPipe, perf maps ni hooks heredados).
# Solo cambia el ProcessStartInfo del hijo; no se modifican variables globales ni la configuracion del equipo.
$ChildEnvRemovePattern = '(?i)^(CORECLR_PROFILER|COR_PROFILER|DOTNET_PROFILER|CORECLR_ENABLE_PROFILING|COR_ENABLE_PROFILING|DOTNET_ENABLE_PROFILING|DOTNET_PerfMap|DOTNET_EnableEventPipe|DOTNET_EventPipe|DOTNET_STARTUP_HOOKS|DOTNET_ADDITIONAL_DEPS|DOTNET_HOSTFXR_PATH|DOTNET_ROOT)|NOTIFICATION'

function Set-ProbeChildEnvironment($StartInfo) {
    foreach ($name in @($StartInfo.EnvironmentVariables.Keys)) {
        if ($name -match $ChildEnvRemovePattern) { [void]$StartInfo.EnvironmentVariables.Remove($name) }
    }
    $StartInfo.EnvironmentVariables['DOTNET_EnableDiagnostics'] = '0'
    $StartInfo.EnvironmentVariables['CORECLR_ENABLE_PROFILING'] = '0'
    $StartInfo.EnvironmentVariables['DOTNET_ENABLE_PROFILING'] = '0'
    $StartInfo.EnvironmentVariables['COR_ENABLE_PROFILING'] = '0'
    $StartInfo.EnvironmentVariables['DOTNET_MULTILEVEL_LOOKUP'] = '0'
    $StartInfo.EnvironmentVariables['DOTNET_NOLOGO'] = '1'
}

# Llamada unica al comprobador con el verbo read. stdout debe ser una sola linea JSON; nunca se imprime la salida cruda.
function Invoke-ReadProbe([string]$PackageRoot, [string]$InstancesRoot, [string]$InstallationId, [string]$Service, [int]$Timeout) {
    if ($ProbeVerbForRun -ne 'read') { Stop-Trial 'probe_verb_invalid' }
    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = Join-Path $PackageRoot ($RuntimeExeRel.Replace('/', '\'))
    $psi.Arguments = '"' + (Join-Path $PackageRoot ($ProbeDllRel.Replace('/', '\'))) + '" read --instances-root "' +
        $InstancesRoot + '" --installation-id ' + $InstallationId + ' --service "' + $Service + '"'
    $psi.WorkingDirectory = $PackageRoot
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    Set-ProbeChildEnvironment $psi
    $process = [Diagnostics.Process]::Start($psi)
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit($Timeout * 1000)) {
        $process.Kill()
        Stop-Trial 'probe_timeout'
    }
    $process.WaitForExit()
    $stdout = $stdoutTask.Result
    $stderr = $stderrTask.Result
    $lines = @($stdout -split "`r?`n" | Where-Object { $_ -ne '' })
    if ($lines.Count -ne 1) { Stop-Trial 'probe_output_invalid' }
    $json = $lines[0] | ConvertFrom-Json
    return [ordered]@{ exitCode = $process.ExitCode; raw = $json; stderrBytes = $stderr.Length }
}

# Veredicto puro: el comprobador debe aprobar, sin codigo, con su salida coherente y el vinculo medido.
function Test-ProbeOutcome($Outcome) {
    $raw = $Outcome.raw
    if ($Outcome.exitCode -ne 0) { return $false }
    if ($raw.status -ne 'passed' -or [string]$raw.code -ne '') { return $false }
    if ($raw.processLinked -ne $true -or $raw.tokenMatched -ne $true -or $raw.impersonationVerified -ne $true) { return $false }
    if ($raw.identityRestored -ne $true) { return $false }
    if ([int]$raw.store.keyBytes -ne 32) { return $false }
    if ([int]$raw.writeProbe.writeGranted -ne 0 -or [int]$raw.writeProbe.dacGranted -ne 0) { return $false }
    if ([int]$raw.writeProbe.inconclusive -ne 0 -or [int]$raw.writeProbe.ownerIsReader -ne 0) { return $false }
    return $true
}

function Get-TrialLecturaPhrase([string]$Uuid) { return ('CONFIRMO LECTURA L2L ' + $Uuid) }

function Confirm-LecturaWrite([string]$Uuid) {
    $expected = Get-TrialLecturaPhrase $Uuid
    Write-Line ''
    Write-Line ('Para ejecutar la comprobacion de lectura, escriba exactamente: ' + $expected)
    $typed = Read-Host 'Confirmacion'
    if ($typed -cne $expected) {
        Write-Line 'Confirmacion no coincide. No se ha ejecutado nada.'
        Stop-Trial 'confirmation_mismatch'
    }
}

# Recibo y resumen nuevos (CreateNew), con DACL solo para SYSTEM y Administradores desde su creacion.
function New-PrivateFile([string]$Path, [string]$Text) {
    $system = New-Object Security.Principal.SecurityIdentifier('S-1-5-18')
    $admins = New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')
    $full = [Security.AccessControl.FileSystemRights]::FullControl
    $allow = [Security.AccessControl.AccessControlType]::Allow
    $none = [Security.AccessControl.InheritanceFlags]::None
    $prop = [Security.AccessControl.PropagationFlags]::None
    $security = New-Object Security.AccessControl.FileSecurity
    $security.SetAccessRuleProtection($true, $false)
    $security.SetOwner($admins)
    $security.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($system, $full, $none, $prop, $allow)))
    $security.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($admins, $full, $none, $prop, $allow)))
    $stream = New-Object IO.FileStream($Path, [IO.FileMode]::CreateNew, [Security.AccessControl.FileSystemRights]::Write,
        [IO.FileShare]::None, 4096, [IO.FileOptions]::None, $security)
    $written = $false
    try {
        $bytes = (New-Object Text.UTF8Encoding($false)).GetBytes($Text)
        $stream.Write($bytes, 0, $bytes.Length)
        $written = $true
    } finally {
        $stream.Dispose()
        if (-not $written) { [IO.File]::Delete($Path) }
    }
}

function Get-LecturaSummaryText($Result) {
    $lines = @(
        'RackClick - comprobacion de lectura con el token del servicio (L2l02). No es MFA ni activacion.',
        ('Resultado: ' + $Result.status),
        ('Codigo: ' + $(if ($Result.code) { $Result.code } else { 'ninguno' })),
        ('Paquete SHA256SUMS: ' + $Result.sumsSha256),
        ('Equipo: ' + $env:COMPUTERNAME),
        ('UUID de instalacion del ensayo: ' + $Result.installationId),
        ('Servicio: ' + $Result.service),
        ('Vinculo proceso-servicio: ' + $Result.processLinked + ' | token-cuenta: ' + $Result.tokenMatched),
        ('Suplantacion verificada: ' + $Result.impersonationVerified + ' | identidad restaurada: ' + $Result.identityRestored),
        ('Version activa leida: ' + $Result.activeVersion + ' | longitud de clave: ' + $Result.keyBytes + ' (la clave no se muestra)'),
        ('Escrituras comprobadas: objetivos ' + $Result.targets + ' | escritura denegada ' + $Result.writeDenied +
            ' | WRITE_DAC denegado ' + $Result.dacDenied + ' | concesiones ' + $Result.granted),
        ('Huella del almacen antes y despues: ' + $Result.fingerprintState),
        'Limites: no acredita la activacion del proveedor dentro del host en marcha ni el login con MFA.'
    )
    return (($lines -join "`r`n") + "`r`n")
}

function Invoke-Check {
    $root = $PSScriptRoot
    Write-Line 'Modo Check: solo lectura. No ejecuta el comprobador ni lee claves.'
    $elevated = Test-ElevationRows (Read-WhoamiGroups)
    Write-Line ('Elevacion observada: ' + $(if ($elevated) { 'si' } else { 'no (Run se detendria)' }))
    $package = Test-PackageIntegrity $root $ExpectedSumsSha256
    Write-Line ('Paquete verificado: ' + $package.fileCount + ' archivos. SHA256SUMS ' + $package.sumsSha256)
    if (-not $ServiceName) { Stop-Trial 'service_name_required' }
    $service = @(Get-CimInstance -ClassName Win32_Service -Filter ("Name = '" + $ServiceName.Replace("'", "''") + "'") | Select-Object Name, State)
    if ($service.Count -ne 1) { Stop-Trial 'service_not_found' }
    Write-Line ('Servicio: ' + $service[0].Name + ' | estado: ' + $service[0].State)
    $trial = Resolve-TrialRoot $TrialRoot
    Write-Line ('Raiz del ensayo localizada (no se muestra la ruta completa): ' + (Split-Path -Leaf $trial))
    Write-Line 'Plan listo. Run ejecuta el comprobador una sola vez y compara huellas antes y despues.'
    Write-Line '{"status":"ready","code":""}'
}

function Invoke-Run {
    if (-not $ExpectedSumsSha256) { Stop-Trial 'expected_sums_required' }
    if (-not $ServiceName) { Stop-Trial 'service_name_required' }
    if ([Console]::IsInputRedirected) { Stop-Trial 'console_required' }
    if (-not (Test-ElevationRows (Read-WhoamiGroups))) { Stop-Trial 'not_elevated' }
    $root = $PSScriptRoot
    $package = Test-PackageIntegrity $root $ExpectedSumsSha256
    $trial = Resolve-TrialRoot $TrialRoot
    $installationId = Get-InstallationId $trial
    if (-not (Test-Path -LiteralPath (Join-Path $trial $installationId) -PathType Container)) { Stop-Trial 'store_missing' }
    $before = Get-StoreFingerprint $trial
    Write-Line ('Huella del almacen antes: ' + $before.count + ' entradas')
    $uuid = [guid]::NewGuid().ToString('D')
    $receipt = Join-Path $env:ProgramData ($PackageName + '-' + $uuid + '.recibo-privado.json')
    $summary = Join-Path $env:ProgramData ($PackageName + '-' + $uuid + '.resumen-sanitizado.txt')
    if ((Test-Path -LiteralPath $receipt) -or (Test-Path -LiteralPath $summary)) { Stop-Trial 'result_name_in_use' }
    Confirm-LecturaWrite $installationId

    $result = [ordered]@{ status = 'failed'; code = ''; sumsSha256 = $package.sumsSha256; installationId = $installationId
        service = $ServiceName; processLinked = $false; tokenMatched = $false; impersonationVerified = $false
        identityRestored = $false; activeVersion = 0; keyBytes = 0; targets = 0; writeDenied = 0; dacDenied = 0; granted = 0
        fingerprintState = 'no comprobada' }
    try {
        $outcome = Invoke-ReadProbe $root $trial $installationId $ServiceName $TimeoutSeconds
        $raw = $outcome.raw
        $result.processLinked = [bool]$raw.processLinked
        $result.tokenMatched = [bool]$raw.tokenMatched
        $result.impersonationVerified = [bool]$raw.impersonationVerified
        $result.identityRestored = [bool]$raw.identityRestored
        $result.activeVersion = [int]$raw.store.activeVersion
        $result.keyBytes = [int]$raw.store.keyBytes
        $result.targets = [int]$raw.writeProbe.targets
        $result.writeDenied = [int]$raw.writeProbe.writeDenied
        $result.dacDenied = [int]$raw.writeProbe.dacDenied
        $result.granted = [int]$raw.writeProbe.writeGranted + [int]$raw.writeProbe.dacGranted
        if (-not (Test-ProbeOutcome $outcome)) {
            $result.code = if ($raw.code) { [string]$raw.code } else { 'probe_failed' }
            Stop-Trial $result.code
        }
        $after = Get-StoreFingerprint $trial
        if ($before.digest -ne $after.digest) {
            $result.fingerprintState = 'cambio detectado'
            Stop-Trial 'store_state_changed'
        }
        $result.fingerprintState = 'sin cambios'
        $result.status = 'passed'
    } catch {
        $result.code = Get-TrialCodeFromError $_
    }
    $text = Get-LecturaSummaryText $result
    $saved = $true
    try { New-PrivateFile $receipt (ConvertTo-Json -InputObject $result -Depth 6) } catch { $saved = $false }
    try { New-PrivateFile $summary $text } catch { $saved = $false }
    Write-Line ''
    Write-Line $text
    if (-not $saved) { Write-Line 'Aviso: no se pudo guardar el recibo o el resumen. El texto anterior debe copiarse a mano.' }
    if ($result.status -ne 'passed') {
        Write-Line ('{"status":"failed","code":"' + $result.code + '"}')
        exit 1
    }
    Write-Line '{"status":"passed","code":""}'
}

function Invoke-SelfTest {
    $script:checks = 0
    function Assert-Same($Actual, $Expected, [string]$Name) {
        if ($Actual -cne $Expected) { throw ('selftest_failed:' + $Name) }
        $script:checks++
    }
    $good = [pscustomobject]@{ exitCode = 0; raw = [pscustomobject]@{ status = 'passed'; code = ''; processLinked = $true
        tokenMatched = $true; impersonationVerified = $true; identityRestored = $true; store = [pscustomobject]@{ activeVersion = 1; keyBytes = 32 }
        writeProbe = [pscustomobject]@{ targets = 3; writeDenied = 3; writeGranted = 0; dacDenied = 3; dacGranted = 0; ownerIsReader = 0; inconclusive = 0 } } }
    Assert-Same (Test-ProbeOutcome $good) $true 'good outcome passes'
    $granted = $good | ConvertTo-Json -Depth 6 | ConvertFrom-Json
    $granted.raw.writeProbe.writeGranted = 1
    Assert-Same (Test-ProbeOutcome $granted) $false 'granted write fails'
    $owner = $good | ConvertTo-Json -Depth 6 | ConvertFrom-Json
    $owner.raw.writeProbe.ownerIsReader = 1
    Assert-Same (Test-ProbeOutcome $owner) $false 'owner equal to reader fails'
    $short = $good | ConvertTo-Json -Depth 6 | ConvertFrom-Json
    $short.raw.store.keyBytes = 31
    Assert-Same (Test-ProbeOutcome $short) $false 'key length must be 32'
    Assert-Same (Get-TrialLecturaPhrase 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee') 'CONFIRMO LECTURA L2L aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee' 'phrase'
    Assert-Same (Get-ThrownTrialCode { Resolve-TrialRoot 'C:\no-existe-l2l' }) 'trial_root_missing' 'missing explicit root'
    Assert-Same (Get-ThrownTrialCode { Get-InstallationId 'C:\x\RackClick-MFA-Ensayo-03-no-es-guid' }) 'trial_root_name_invalid' 'invalid installation id'
    $guid = [guid]::NewGuid().ToString('D')
    Assert-Same (Get-InstallationId ('C:\x\' + $TrialPrefix + $guid)) $guid 'installation id from folder name'
    Assert-Same (ConvertFrom-SumsLine ('a' * 64 + '  probe/RackClick.MfaServiceReadProbe.dll')).rel 'probe/RackClick.MfaServiceReadProbe.dll' 'sums path'
    Assert-Same (Test-ElevationRows @('"Name","Type","Sid","Attributes"', '"Label","Label","S-1-16-12288","x"')) $true 'high integrity is elevated'
    Assert-Same (Test-ElevationRows @('"Name","Type","Sid","Attributes"', '"Label","Label","S-1-16-8192","x"')) $false 'medium integrity is not elevated'
    Write-Line ('selftest_passed ' + $script:checks)
}

try {
    if ($Mode -eq 'SelfTest') {
        Invoke-SelfTest
    } else {
        if (Test-LabHostExcluded) { Stop-Trial 'host_excluded' }
        if ($Mode -eq 'Run') { Invoke-Run } else { Invoke-Check }
    }
    exit 0
} catch {
    $code = Get-TrialCodeFromError $_
    $status = if ($code -eq 'unexpected_error') { 'failed' } else { 'rejected' }
    $type = $_.Exception.GetType().Name
    Write-Line ('{"status":"' + $status + '","code":"' + $code + '","type":"' + $type + '"}')
    exit 1
}
