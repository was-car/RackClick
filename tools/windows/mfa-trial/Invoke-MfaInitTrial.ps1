#requires -Version 5.1
# Ensayo interno MFA-INIT (L2k). NO es instalador ni actualizacion.
# Check: solo lectura. Verifica el paquete, elige la cuenta de inicio de un servicio RackClick existente (solo lectura)
# y muestra el plan. No crea carpetas ni escribe nada.
# Run: exige consola, operador elevado, SHA256SUMS esperado y confirmacion escrita. Crea UNA carpeta nueva con UUID nuevo
# y ejecuta dos veces --mfa-keys-init: la primera debe crear (exit 0) y la segunda debe rechazar con exists (exit 1)
# sin cambiar nada. No reintenta, no borra por nombre y no toca servicios, cuentas, bases de datos ni la configuracion.
# SelfTest: funciones puras; no toca el sistema.
# LEAO se rechaza en Check y Run antes de leer nada.
[CmdletBinding()]
param(
    [ValidateSet('Check', 'Run', 'SelfTest')][string]$Mode = 'Check',
    [string]$ServiceName = '',
    [string]$BaseDirectory = $env:ProgramData,
    [string]$ExpectedSumsSha256 = '',
    [ValidateRange(10, 300)][int]$TimeoutSeconds = 60
)
$ErrorActionPreference = 'Stop'

$PackageName = 'RackClick-MFA-Ensayo-03'
$ExcludedHosts = @('LEAO')
$SystemSid = 'S-1-5-18'
$AdminsSid = 'S-1-5-32-544'
$HighIntegritySid = 'S-1-16-12288'
$RuntimeExeRel = 'runtime/dotnet.exe'
$ServerDllRel = 'servidor/RackClick.Server.dll'
$ServerDirRel = 'servidor'
$RequiredRel = @(
    'INICIAR-ENSAYO-MFA.cmd', 'Invoke-MfaInitTrial.ps1', 'LEEME-ENSAYO-INTERNO.txt', 'GUION-ENTRADA-SALIDA.md',
    'BUILD-MANIFEST.json', 'SHA256SUMS', 'runtime/dotnet.exe', 'runtime/LICENSE.txt', 'runtime/ThirdPartyNotices.txt',
    'servidor/RackClick.Server.dll', 'servidor/RackClick.Server.runtimeconfig.json', 'servidor/RackClick.Server.deps.json',
    'licenses/Npgsql-LICENSE', 'licenses/Otp.NET-LICENSE.txt', 'licenses/README.txt'
)
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

function Test-PlainDirectory([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return $false }
    $item = Get-Item -LiteralPath $Path -Force
    return (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0)
}

# Elevacion: el token elevado de un administrador muestra la etiqueta de integridad alta (S-1-16-12288). Se compara por SID,
# no por nombre, porque la salida de whoami va localizada. El propio --mfa-keys-init vuelve a comprobarla.
function Read-WhoamiGroups {
    $output = & (Join-Path $env:SystemRoot 'System32\whoami.exe') /groups /fo csv
    if ($LASTEXITCODE -ne 0) { Stop-Trial 'elevation_unobservable' }
    return @($output)
}

function Test-ElevationRows([string[]]$CsvLines) {
    $rows = @($CsvLines | Where-Object { $_ -match '[^\s]' } | ConvertFrom-Csv -Header 'Name', 'Type', 'Sid', 'Attributes')
    return [bool]($rows | Where-Object { $_.Sid -eq $HighIntegritySid })
}

function ConvertFrom-SumsLine([string]$Line) {
    $match = [regex]::Match($Line, '^([0-9a-f]{64})  (.+)$')
    if (-not $match.Success) { Stop-Trial 'package_sums_malformed' }
    return @{ sha256 = $match.Groups[1].Value; rel = $match.Groups[2].Value }
}

# Integridad del paquete: cada archivo debe figurar en SHA256SUMS con su hash, no debe haber archivos extra ni faltantes,
# ni puntos de reparse. Si se da -ExpectedSumsSha256, el SHA256SUMS debe coincidir con el valor entregado por Codex.
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

function Get-TrialServiceCandidates {
    return @(Get-CimInstance -ClassName Win32_Service -Filter "Name LIKE 'RackClick%'" | Select-Object Name, StartName, State)
}

function Show-ServiceChoices($Candidates) {
    foreach ($candidate in @($Candidates)) { Write-Line ('  - ' + $candidate.Name + ' (estado ' + $candidate.State + ')') }
}

# Seleccion sin ambiguedad: un solo servicio RackClick, o -ServiceName exacto. Con varios y sin nombre se para.
function Select-TrialService($Candidates, [string]$Name) {
    $list = @($Candidates)
    if ($Name) {
        $hit = @($list | Where-Object { $_.Name -eq $Name })
        if ($hit.Count -eq 0) { Stop-Trial 'service_not_found' }
        if ($hit.Count -gt 1) { Stop-Trial 'service_ambiguous' }
        return $hit[0]
    }
    if ($list.Count -eq 0) { Stop-Trial 'service_none' }
    if ($list.Count -gt 1) {
        Write-Line 'Hay varios servicios RackClick. Indique uno con -ServiceName:'
        Show-ServiceChoices $list
        Stop-Trial 'service_ambiguous'
    }
    return $list[0]
}

function Test-TrustedAccountName([string]$Name) {
    return [bool]($Name -match '(?i)^(NT AUTHORITY\\SYSTEM|LocalSystem|\.\\LocalSystem)$')
}

# Traduccion de solo lectura de la cuenta de inicio a SID. Las cuentas de confianza fija se rechazan antes de traducir.
function Resolve-ServiceAccountSid([string]$StartName) {
    if ([string]::IsNullOrWhiteSpace($StartName)) { Stop-Trial 'service_account_unknown' }
    if (Test-TrustedAccountName $StartName) { Stop-Trial 'service_account_trusted' }
    $name = $StartName
    if ($name.StartsWith('.\')) { $name = $env:COMPUTERNAME + '\' + $name.Substring(2) }
    try {
        $sid = ([Security.Principal.NTAccount]$name).Translate([Security.Principal.SecurityIdentifier]).Value
    } catch {
        Stop-Trial 'service_account_unresolved'
    }
    if (($sid -eq $SystemSid) -or ($sid -eq $AdminsSid)) { Stop-Trial 'service_account_trusted' }
    return $sid
}

function Test-FirstInitOutcome($Result) {
    return ($Result.exitCode -eq 0) -and ($Result.status -eq 'created') -and ($Result.residue -eq 'none')
}

function Test-SecondInitOutcome($Result) {
    return ($Result.exitCode -eq 1) -and ($Result.status -eq 'rejected') -and
           ($Result.code -eq 'mfa_keystore_init_exists') -and ($Result.residue -eq 'none')
}

function Get-TrialConfirmationText([string]$Uuid) { return ('CONFIRMO ENSAYO MFA-INIT ' + $Uuid) }

function Confirm-TrialWrite([string]$Uuid) {
    $expected = Get-TrialConfirmationText $Uuid
    Write-Line ''
    Write-Line ('Para escribir el ensayo, escriba exactamente: ' + $expected)
    $typed = Read-Host 'Confirmacion'
    if ($typed -cne $expected) {
        Write-Line 'Confirmacion no coincide. No se ha creado ninguna carpeta, recibo ni resumen.'
        Stop-Trial 'confirmation_mismatch'
    }
}

# Creacion exclusiva de la carpeta con su DACL desde la creacion: CreateDirectoryW (la misma API que usa el writer aprobado)
# con SECURITY_ATTRIBUTES. Devuelve 0 solo si esta llamada creo la carpeta; si ya existia, falla con ERROR_ALREADY_EXISTS y
# no se toca. DirectoryInfo.Create no sirve: sobre un directorio existente termina con exito.
$TrialNativeSource = @'
using System;
using System.Runtime.InteropServices;
namespace RackClick.Mfa
{
    public static class TrialDirectory
    {
        [StructLayout(LayoutKind.Sequential)]
        struct SECURITY_ATTRIBUTES
        {
            public int nLength;
            public IntPtr lpSecurityDescriptor;
            public int bInheritHandle;
        }

        [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        static extern bool CreateDirectoryW(string lpPathName, ref SECURITY_ATTRIBUTES lpSecurityAttributes);

        public static int CreateExclusive(string path, byte[] securityDescriptor)
        {
            GCHandle handle = GCHandle.Alloc(securityDescriptor, GCHandleType.Pinned);
            try
            {
                SECURITY_ATTRIBUTES attributes = new SECURITY_ATTRIBUTES();
                attributes.nLength = Marshal.SizeOf(typeof(SECURITY_ATTRIBUTES));
                attributes.lpSecurityDescriptor = handle.AddrOfPinnedObject();
                attributes.bInheritHandle = 0;
                if (CreateDirectoryW(path, ref attributes)) { return 0; }
                return Marshal.GetLastWin32Error();
            }
            finally { handle.Free(); }
        }
    }
}
'@

function Initialize-TrialNative {
    if (-not ('RackClick.Mfa.TrialDirectory' -as [type])) { Add-Type -TypeDefinition $TrialNativeSource -Language CSharp }
}

# La carpeta de ensayo nace ya con su DACL protegida y su propietario (SYSTEM y Administradores con control total, la cuenta
# del servicio con lectura). No se crea sin ACL ni se reescribe despues: en Windows PowerShell 5.1 sin elevacion una segunda
# escritura de ACL sobre la carpeta falla (AISLAMIENTO-ACL-5.1.txt en la evidencia).
function New-TrialRootFolder([string]$Path, [string]$ReaderSid, [string]$OwnerSid = $AdminsSid) {
    $system = New-Object Security.Principal.SecurityIdentifier($SystemSid)
    $admins = New-Object Security.Principal.SecurityIdentifier($AdminsSid)
    $reader = New-Object Security.Principal.SecurityIdentifier($ReaderSid)
    $owner = New-Object Security.Principal.SecurityIdentifier($OwnerSid)
    $inherit = [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit
    $none = [Security.AccessControl.PropagationFlags]::None
    $allow = [Security.AccessControl.AccessControlType]::Allow
    $full = [Security.AccessControl.FileSystemRights]::FullControl
    $read = [Security.AccessControl.FileSystemRights]::ReadAndExecute
    $acl = New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true, $false)
    $acl.SetOwner($owner)
    $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($system, $full, $inherit, $none, $allow)))
    $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($admins, $full, $inherit, $none, $allow)))
    $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($reader, $read, $inherit, $none, $allow)))
    Initialize-TrialNative
    $code = [RackClick.Mfa.TrialDirectory]::CreateExclusive($Path, $acl.GetSecurityDescriptorBinaryForm())
    if ($code -eq 0) { return }
    # 183 = ERROR_ALREADY_EXISTS; 80 = ERROR_FILE_EXISTS (hay un archivo con ese nombre). Ninguno se toca.
    if (($code -eq 183) -or ($code -eq 80)) { Stop-Trial 'trial_folder_exists' }
    Stop-Trial 'trial_folder_create_failed'
}

function Get-TrialAclSummary([string]$Path) {
    $acl = Get-Acl -LiteralPath $Path
    $rules = @($acl.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier]) | ForEach-Object {
        [ordered]@{ sid = $_.IdentityReference.Value; rights = [string]$_.FileSystemRights; type = [string]$_.AccessControlType; inheritance = [string]$_.InheritanceFlags }
    })
    return [ordered]@{
        protectedDacl = [bool]$acl.AreAccessRulesProtected
        owner = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
        rules = $rules
        sddlSha256 = (Get-TextSha256 $acl.Sddl)
    }
}

function Assert-TrialRootAcl($Summary, [string]$ReaderSid) {
    if (-not $Summary.protectedDacl) { Stop-Trial 'trial_acl_not_protected' }
    if ($Summary.owner -ne $AdminsSid) { Stop-Trial 'trial_owner_invalid' }
    $sids = @($Summary.rules | ForEach-Object { $_.sid } | Sort-Object -Unique)
    $expected = @($SystemSid, $AdminsSid, $ReaderSid | Sort-Object -Unique)
    if (Compare-Object -ReferenceObject $sids -DifferenceObject $expected) { Stop-Trial 'trial_acl_unexpected' }
    foreach ($rule in $Summary.rules) {
        if ($rule.type -ne 'Allow') { Stop-Trial 'trial_acl_unexpected' }
    }
}

# Huella del estado: rutas, tamanos, SHA256 de cada archivo y hash del SDDL de cada entrada. No guarda contenidos.
function Get-TrialState([string]$Root) {
    # La raiz entra en la huella: una ACL distinta solo en la raiz debe cambiar el digest aunque los hijos sean iguales.
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
    return [ordered]@{ count = $entries.Count; digest = (Get-TextSha256 $canonical); entries = $entries }
}

# Entorno del hijo: sin profiler, EventPipe, perf maps ni hooks heredados del equipo. Solo cambia el ProcessStartInfo del hijo;
# no se modifican variables globales ni la configuracion del equipo.
$ChildEnvRemovePattern = '(?i)^(CORECLR_PROFILER|COR_PROFILER|DOTNET_PROFILER|CORECLR_ENABLE_PROFILING|COR_ENABLE_PROFILING|DOTNET_ENABLE_PROFILING|DOTNET_PerfMap|DOTNET_EnableEventPipe|DOTNET_EventPipe|DOTNET_STARTUP_HOOKS|DOTNET_ADDITIONAL_DEPS|DOTNET_HOSTFXR_PATH|DOTNET_ROOT)|NOTIFICATION'

function Set-TrialChildEnvironment($StartInfo) {
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

# Invocacion de --mfa-keys-init: stdin JSON, una sola linea de salida. El entorno del hijo se aisla con Set-TrialChildEnvironment.
function Invoke-MfaKeysInit([string]$PackageRoot, [string]$InstancesRoot, [string]$InstallationId, [string]$ReaderSid, [int]$Timeout) {
    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = Join-Path $PackageRoot ($RuntimeExeRel.Replace('/', '\'))
    $psi.Arguments = '"' + (Join-Path $PackageRoot ($ServerDllRel.Replace('/', '\'))) + '" --mfa-keys-init'
    $psi.WorkingDirectory = Join-Path $PackageRoot $ServerDirRel
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    Set-TrialChildEnvironment $psi
    $payload = [ordered]@{ instancesRoot = $InstancesRoot; installationId = $InstallationId; readerSid = $ReaderSid } | ConvertTo-Json -Compress
    $bytes = (New-Object Text.UTF8Encoding($false)).GetBytes($payload)
    $process = [Diagnostics.Process]::Start($psi)
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    try {
        $process.StandardInput.BaseStream.Write($bytes, 0, $bytes.Length)
        $process.StandardInput.BaseStream.Flush()
    } catch [IO.IOException] {
        # El proceso pudo salir antes de leer stdin; la salida y el codigo de salida siguen siendo la prueba.
    }
    try { $process.StandardInput.Close() } catch [IO.IOException] { }
    if (-not $process.WaitForExit($Timeout * 1000)) {
        $process.Kill()
        Stop-Trial 'init_timeout'
    }
    $process.WaitForExit()
    $stdout = $stdoutTask.Result
    $stderr = $stderrTask.Result
    $lines = @($stdout -split "`r?`n" | Where-Object { $_ -ne '' })
    if ($lines.Count -ne 1) { Stop-Trial 'init_output_invalid' }
    $json = $lines[0] | ConvertFrom-Json
    return [ordered]@{
        exitCode = $process.ExitCode
        status = [string]$json.status
        code = [string]$json.code
        residue = [string]$json.residue
        stderrBytes = $stderr.Length
    }
}

# El archivo nace con su DACL privada y su propietario: FileStream con FileSecurity, CreateNew. No hay fase legible previa ni
# reescritura de la ACL despues. Si la escritura falla, solo se borra el archivo que esta llamada acaba de crear; nunca uno ajeno.
function New-PrivateFile([string]$Path, [string]$Text, [string]$OwnerSid = $AdminsSid) {
    $system = New-Object Security.Principal.SecurityIdentifier($SystemSid)
    $owner = New-Object Security.Principal.SecurityIdentifier($OwnerSid)
    $full = [Security.AccessControl.FileSystemRights]::FullControl
    $allow = [Security.AccessControl.AccessControlType]::Allow
    $none = [Security.AccessControl.InheritanceFlags]::None
    $prop = [Security.AccessControl.PropagationFlags]::None
    $security = New-Object Security.AccessControl.FileSecurity
    $security.SetAccessRuleProtection($true, $false)
    $security.SetOwner($owner)
    $security.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($system, $full, $none, $prop, $allow)))
    $security.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($owner, $full, $none, $prop, $allow)))
    $stream = New-Object IO.FileStream($Path, [IO.FileMode]::CreateNew, [Security.AccessControl.FileSystemRights]::Write, [IO.FileShare]::None, 4096, [IO.FileOptions]::None, $security)
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

function Invoke-Check {
    $root = $PSScriptRoot
    Write-Line 'Modo Check: solo lectura. No se crea carpeta, no se escribe recibo y no se ejecuta el servidor.'
    $elevated = Test-ElevationRows (Read-WhoamiGroups)
    Write-Line ('Elevacion observada: ' + $(if ($elevated) { 'si' } else { 'no (Run se detendria)' }))
    $package = Test-PackageIntegrity $root $ExpectedSumsSha256
    Write-Line ('Paquete verificado: ' + $package.fileCount + ' archivos. SHA256SUMS ' + $package.sumsSha256)
    $service = Select-TrialService (Get-TrialServiceCandidates) $ServiceName
    $sid = Resolve-ServiceAccountSid $service.StartName
    Write-Line ('Servicio seleccionado: ' + $service.Name + ' | cuenta de inicio: ' + $service.StartName + ' | SID: ' + $sid)
    if (-not (Test-PlainDirectory $BaseDirectory)) { Stop-Trial 'base_directory_invalid' }
    Write-Line 'Plan listo. Run exige consola, elevacion, -ExpectedSumsSha256 y la confirmacion escrita.'
    Write-Line '{"status":"ready","code":""}'
}

# Pasos del ensayo en orden. El resumen indica el ultimo paso observado y los siguientes no ejecutados.
$TrialSteps = @('crear_carpeta_protegida', 'comprobar_acl', 'init_primera', 'huella_tras_primera', 'init_segunda', 'huella_tras_segunda')
$script:TrialStep = ''

function Set-TrialStep([string]$Name) { $script:TrialStep = $Name }

function Get-TrialSummaryText($Trial) {
    $index = [array]::IndexOf($TrialSteps, [string]$Trial.observedStep)
    $notExecuted = @()
    if ($index -ge 0) { $notExecuted = @($TrialSteps | Select-Object -Skip ($index + 1)) }
    $first = 'no ejecutada'
    $second = 'no ejecutada'
    if ($Trial.runs.Count -ge 1) { $first = $Trial.runs[0].status + '/' + $Trial.runs[0].code + ' exit ' + $Trial.runs[0].exitCode }
    if ($Trial.runs.Count -ge 2) { $second = $Trial.runs[1].status + '/' + $Trial.runs[1].code + ' exit ' + $Trial.runs[1].exitCode }
    $state = 'no calculada'
    if ($Trial.state.Contains('afterSecond')) {
        $state = 'tras la segunda: ' + $Trial.state.afterSecond.count + ' entradas, sin cambios: ' + $(if ($Trial.state.afterSecond.unchanged) { 'si' } else { 'no' })
    } elseif ($Trial.state.Contains('afterFirst')) {
        $state = 'tras la primera: ' + $Trial.state.afterFirst.count + ' entradas'
    }
    $acl = 'no comprobada'
    if ($Trial.rootAcl) { $acl = 'protegida=' + $Trial.rootAcl.protectedDacl + ' propietario=' + $Trial.rootAcl.owner }
    $stop = 'ninguno'
    if ($Trial.stopCode) { $stop = $Trial.stopCode; if ($Trial.stopType) { $stop = $stop + ' (' + $Trial.stopType + ')' } }
    $lines = @(
        'RackClick - ensayo interno MFA-INIT (no es instalador ni actualizacion)',
        ('Resultado: ' + $Trial.result),
        ('Codigo de parada: ' + $stop),
        ('Paso observado: ' + $Trial.observedStep),
        ('Pasos no ejecutados: ' + $(if ($notExecuted.Count -gt 0) { $notExecuted -join ', ' } else { 'ninguno' })),
        ('Paquete SHA256SUMS: ' + $Trial.package.sumsSha256),
        ('Equipo: ' + $Trial.host.computerName),
        'Elevacion observada: si',
        ('UUID de ensayo: ' + $Trial.trialId),
        ('Servicio: ' + $Trial.service.name + ' | cuenta: ' + $Trial.service.accountName + ' | SID: ' + $Trial.service.accountSid),
        ('Raiz de ensayo: ' + $acl),
        ('Primera ejecucion: ' + $first + ' (esperado created/0)'),
        ('Segunda ejecucion: ' + $second + ' (esperado rejected/mfa_keystore_init_exists/1)'),
        ('Huella del estado: ' + $state),
        'Limites: no acredita que el servicio lea la clave; la consulta SCM no es ejecucion bajo ese SID; MFA no queda disponible para usuarios.'
    )
    return (($lines -join "`r`n") + "`r`n")
}

# Guarda recibo privado y resumen. El resumen se imprime siempre. Un fallo al guardar no oculta el fallo original.
function Save-TrialArtifacts($Trial, [string]$ReceiptPath, [string]$SummaryPath) {
    $saved = @{ receipt = $false; summary = $false }
    try {
        New-PrivateFile $ReceiptPath (ConvertTo-Json -InputObject $Trial -Depth 10)
        $saved.receipt = $true
    } catch {
        Write-Line ('recibo_no_guardado: ' + $_.Exception.GetType().Name)
    }
    try {
        $text = Get-TrialSummaryText $Trial
    } catch {
        $text = 'resumen_no_generado: ' + $_.Exception.GetType().Name + "`r`n"
    }
    try {
        New-PrivateFile $SummaryPath $text
        $saved.summary = $true
    } catch {
        Write-Line ('resumen_no_guardado: ' + $_.Exception.GetType().Name + '. El texto siguiente debe copiarse a mano.')
    }
    Write-Line ''
    Write-Line $text
    return $saved
}

function Invoke-Run {
    if (-not $ExpectedSumsSha256) { Stop-Trial 'expected_sums_required' }
    if ([Console]::IsInputRedirected) { Stop-Trial 'console_required' }
    if (-not (Test-ElevationRows (Read-WhoamiGroups))) { Stop-Trial 'not_elevated' }
    $root = $PSScriptRoot
    $package = Test-PackageIntegrity $root $ExpectedSumsSha256
    $service = Select-TrialService (Get-TrialServiceCandidates) $ServiceName
    $sid = Resolve-ServiceAccountSid $service.StartName
    if (-not (Test-PlainDirectory $BaseDirectory)) { Stop-Trial 'base_directory_invalid' }
    $uuid = [guid]::NewGuid().ToString('D')
    $trialRoot = Join-Path $BaseDirectory ($PackageName + '-' + $uuid)
    $receiptPath = $trialRoot + '.recibo-privado.json'
    $summaryPath = $trialRoot + '.resumen-sanitizado.txt'
    if ((Test-Path -LiteralPath $trialRoot) -or (Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $summaryPath)) {
        Stop-Trial 'trial_name_in_use'
    }
    Write-Line '--- PLAN DEL ENSAYO INTERNO MFA-INIT (no es instalador ni actualizacion) ---'
    Write-Line ('Equipo: ' + $env:COMPUTERNAME)
    Write-Line ('UUID de ensayo: ' + $uuid)
    Write-Line ('Carpeta nueva: ' + $trialRoot)
    Write-Line ('Servicio: ' + $service.Name + ' | cuenta: ' + $service.StartName + ' | SID: ' + $sid)
    Write-Line ('Paquete SHA256SUMS: ' + $package.sumsSha256)
    Write-Line 'No se tocan servicios, cuentas, bases de datos, configuracion ni la instalacion existente.'

    # Una confirmacion incorrecta sale aqui, antes de crear el registro, la carpeta, el recibo o el resumen: no se escribe nada.
    Confirm-TrialWrite $uuid

    $trial = [ordered]@{
        schemaVersion = 2; kind = 'RackClickMfaInitTrialPrivateReceipt'; internalTrial = $true; notInstaller = $true
        utc = [DateTime]::UtcNow.ToString('o')
        package = [ordered]@{ sumsSha256 = $package.sumsSha256; fileCount = $package.fileCount }
        host = [ordered]@{ computerName = $env:COMPUTERNAME; os = [Environment]::OSVersion.VersionString }
        elevation = [ordered]@{ observed = $true }
        trialId = $uuid; trialFolder = $trialRoot
        service = [ordered]@{ name = $service.Name; accountName = $service.StartName; accountSid = $sid }
        runs = @(); state = [ordered]@{}; rootAcl = $null; result = ''; stopCode = ''; stopType = ''; observedStep = ''
    }
    try {
        Set-TrialStep 'crear_carpeta_protegida'
        New-TrialRootFolder $trialRoot $sid
        Set-TrialStep 'comprobar_acl'
        $trial.rootAcl = Get-TrialAclSummary $trialRoot
        Assert-TrialRootAcl $trial.rootAcl $sid

        Set-TrialStep 'init_primera'
        $first = Invoke-MfaKeysInit $root $trialRoot $uuid $sid $TimeoutSeconds
        $trial.runs += [ordered]@{ ordinal = 1; expected = 'created/0'; status = $first.status; code = $first.code; residue = $first.residue; exitCode = $first.exitCode; stderrBytes = $first.stderrBytes; match = (Test-FirstInitOutcome $first) }
        if (-not (Test-FirstInitOutcome $first)) { Stop-Trial 'init_first_unexpected' }
        Set-TrialStep 'huella_tras_primera'
        $afterFirst = Get-TrialState $trialRoot
        $trial.state.afterFirst = [ordered]@{ count = $afterFirst.count; digest = $afterFirst.digest }

        Set-TrialStep 'init_segunda'
        $second = Invoke-MfaKeysInit $root $trialRoot $uuid $sid $TimeoutSeconds
        $trial.runs += [ordered]@{ ordinal = 2; expected = 'rejected/mfa_keystore_init_exists/1'; status = $second.status; code = $second.code; residue = $second.residue; exitCode = $second.exitCode; stderrBytes = $second.stderrBytes; match = (Test-SecondInitOutcome $second) }
        if (-not (Test-SecondInitOutcome $second)) { Stop-Trial 'init_second_unexpected' }
        Set-TrialStep 'huella_tras_segunda'
        $afterSecond = Get-TrialState $trialRoot
        $unchanged = ($afterFirst.digest -eq $afterSecond.digest)
        $trial.state.afterSecond = [ordered]@{ count = $afterSecond.count; digest = $afterSecond.digest; unchanged = $unchanged }
        if (-not $unchanged) { Stop-Trial 'trial_state_changed' }
        $trial.state.entries = $afterSecond.entries
        $trial.result = 'protocol_passed'
    } catch {
        $trial.result = 'stopped'
        $trial.stopCode = (Get-TrialCodeFromError $_)
        if ($trial.stopCode -eq 'unexpected_error') { $trial.stopType = $_.Exception.GetType().Name }
        $stopError = $_
    }
    $trial.observedStep = $script:TrialStep
    $saved = Save-TrialArtifacts $trial $receiptPath $summaryPath
    if ($trial.result -ne 'protocol_passed') {
        Write-Line ('Parada conservando el estado. Codigo: ' + $trial.stopCode)
        throw $stopError
    }
    if ($saved.receipt) { Write-Line ('Recibo privado (no enviar): ' + $receiptPath) }
    Write-Line '{"status":"passed","code":""}'
}

function Invoke-SelfTest {
    $script:checks = 0
    function Assert-Same($Actual, $Expected, [string]$Name) {
        if ($Actual -cne $Expected) { throw ('selftest_failed:' + $Name) }
        $script:checks++
    }
    $one = @([pscustomobject]@{ Name = 'RackClick'; StartName = '.\RackClickSvcAB12CD34'; State = 'Stopped' })
    $two = @(
        [pscustomobject]@{ Name = 'RackClick'; StartName = '.\RackClickSvcAB12CD34'; State = 'Stopped' },
        [pscustomobject]@{ Name = 'RackClick LAB2'; StartName = 'LocalSystem'; State = 'Running' }
    )
    Assert-Same (Get-ThrownTrialCode { Select-TrialService @() '' }) 'service_none' 'zero candidates'
    Assert-Same (Select-TrialService $one '').Name 'RackClick' 'one candidate'
    Assert-Same (Get-ThrownTrialCode { Select-TrialService $two '' }) 'service_ambiguous' 'two without name'
    Assert-Same (Select-TrialService $two 'RackClick LAB2').StartName 'LocalSystem' 'explicit name'
    Assert-Same (Get-ThrownTrialCode { Select-TrialService $two 'Inexistente' }) 'service_not_found' 'explicit missing'
    Assert-Same (Get-ThrownTrialCode { Select-TrialService $two 'rackclick' }) '' 'name match is case-insensitive'
    Assert-Same (Test-TrustedAccountName 'LocalSystem') $true 'LocalSystem trusted name'
    Assert-Same (Test-TrustedAccountName 'NT AUTHORITY\SYSTEM') $true 'SYSTEM trusted name'
    Assert-Same (Test-TrustedAccountName '.\RackClickSvcAB12CD34') $false 'local service account is not trusted by name'
    Assert-Same (Get-ThrownTrialCode { Resolve-ServiceAccountSid '' }) 'service_account_unknown' 'empty account'
    Assert-Same (Get-ThrownTrialCode { Resolve-ServiceAccountSid 'LocalSystem' }) 'service_account_trusted' 'LocalSystem rejected before translation'
    $elevatedCsv = @('"Name","Type","Sid","Attributes"', '"Mandatory Label\High Mandatory Level","Label","S-1-16-12288","Group integrity"')
    $mediumCsv = @('"Name","Type","Sid","Attributes"', '"Mandatory Label\Medium Mandatory Level","Label","S-1-16-8192","Group integrity"')
    Assert-Same (Test-ElevationRows $elevatedCsv) $true 'high integrity is elevated'
    Assert-Same (Test-ElevationRows $mediumCsv) $false 'medium integrity is not elevated'
    Assert-Same (Get-TrialConfirmationText 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee') 'CONFIRMO ENSAYO MFA-INIT aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee' 'confirmation text'
    $sumsLine = ConvertFrom-SumsLine ('a' * 64 + '  servidor/RackClick.Server.dll')
    Assert-Same $sumsLine.rel 'servidor/RackClick.Server.dll' 'sums path'
    Assert-Same (Get-ThrownTrialCode { ConvertFrom-SumsLine 'no-es-una-linea' }) 'package_sums_malformed' 'sums malformed'
    Assert-Same (Test-FirstInitOutcome ([pscustomobject]@{ exitCode = 0; status = 'created'; code = ''; residue = 'none' })) $true 'first init expected'
    Assert-Same (Test-FirstInitOutcome ([pscustomobject]@{ exitCode = 1; status = 'rejected'; code = 'mfa_keystore_init_exists'; residue = 'none' })) $false 'first init rejects exists'
    Assert-Same (Test-SecondInitOutcome ([pscustomobject]@{ exitCode = 1; status = 'rejected'; code = 'mfa_keystore_init_exists'; residue = 'none' })) $true 'second init expected'
    Assert-Same (Test-SecondInitOutcome ([pscustomobject]@{ exitCode = 0; status = 'created'; code = ''; residue = 'none' })) $false 'second init created is a failure'
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
