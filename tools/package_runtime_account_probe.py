"""Package a credentialed read check; never run it while building the archive."""
import argparse
import hashlib
import json
import re
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
FROZEN = LOCAL / 'clean-server05-payload-a.zip'
FROZEN_SHA = '73cc45d5c3df912064f675c829bc60258a682c70054ad91b776cff235ff917f3'
SOURCES = (
    'RackClick.Setup.ps1', 'RackClick.Setup.Security.ps1',
    'RackClick.Setup.Process.ps1', 'RackClick.Setup.ServiceStatus.ps1',
    'RackClick.Setup.RuntimeProbe.ps1', 'Probe-RackClickRuntimeRead.ps1',
    'Test-RackClickExistingAccount.ps1',
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def no_reparse(path):
    for item in (path, *path.parents):
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('reparse_path_rejected')
        if item == ROOT:
            break


def contract():
    no_reparse(FROZEN)
    data = FROZEN.read_bytes()
    if digest(data) != FROZEN_SHA:
        raise ValueError('frozen_payload_changed')
    with zipfile.ZipFile(FROZEN) as archive:
        manifest = json.loads(archive.read('RackClick-Instalador/payload.json'))
        pins = [f for f in manifest['files']
                if f['path'].startswith('operators/') and f['path'].endswith('.ps1')]
        codes = {'probe_check_failed', 'probe_identity_mismatch',
                 'probe_read_checks_passed', 'probe_environment_restore_failed'}
        for pin in pins:
            content = archive.read('RackClick-Instalador/' + pin['path'])
            if len(content) != pin['size'] or digest(content) != pin['sha256']:
                raise ValueError('frozen_source_changed')
            codes.update(re.findall(r"'((?:server|deployment|instance|https|stage|process|launcher|backup|runtime|bundle|offline)_[a-z0-9_]{1,85})'", content.decode('utf-8-sig')))
    return {
        'schemaVersion': 1, 'frozenPayloadSha256': FROZEN_SHA, 'pins': pins,
        'codes': sorted(codes), 'files': sorted({Path(f['path']).name for f in pins}),
        'errorTypes': ['System.InvalidOperationException', 'System.UnauthorizedAccessException',
                       'System.IO.IOException', 'System.IO.FileNotFoundException',
                       'System.IO.DirectoryNotFoundException', 'System.ArgumentException',
                       'System.ArgumentOutOfRangeException', 'System.NullReferenceException',
                       'System.Security.SecurityException', 'System.Security.Cryptography.CryptographicException',
                       'System.ComponentModel.Win32Exception', 'System.Net.Sockets.SocketException',
                       'System.Management.Automation.RuntimeException',
                       'System.Management.Automation.PropertyNotFoundException',
                       'System.Management.Automation.CommandNotFoundException',
                       'System.Management.Automation.PSSecurityException',
                       'System.Management.Automation.ParameterBindingException'],
    }


def build(output):
    output = output.absolute()
    if '..' in output.parts or not output.is_relative_to(LOCAL) or output.suffix.lower() != '.zip' or output.exists() or output.is_symlink() or output.is_junction():
        raise ValueError('new_local_zip_required')
    no_reparse(output.parent)
    payload = {}
    for name in SOURCES:
        path = ROOT / 'tools/windows/server-install' / name
        no_reparse(path)
        payload['operators/' + name] = path.read_bytes()
    payload['operators/runtime-probe-contract.json'] = (json.dumps(contract(), indent=2) + '\n').encode('ascii')
    payload['00-COMPROBAR-ARRANQUE.cmd'] = (
        '@echo off\r\nsetlocal\r\n'
        'set "RC_PS=%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"\r\n'
        'if exist "%SystemRoot%\\Sysnative\\WindowsPowerShell\\v1.0\\powershell.exe" set "RC_PS=%SystemRoot%\\Sysnative\\WindowsPowerShell\\v1.0\\powershell.exe"\r\n'
        '"%RC_PS%" -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0INICIAR-COMPROBACION.ps1"\r\n'
        'set "RC_EXIT=%ERRORLEVEL%"\r\n'
        'if not "%RC_EXIT%"=="0" pause\r\nexit /b %RC_EXIT%\r\n'
    ).encode('ascii')
    payload['00-LEEME.html'] = '''<!doctype html><html lang="es"><meta charset="utf-8">
<title>RackClick · comprobación de la cuenta existente</title>
<style>body{font:18px/1.6 system-ui;max-width:900px;margin:40px auto;padding:0 24px;color:#192b3a}code{background:#edf1f4;padding:2px 5px}li{margin:12px 0}</style>
<h1>Comprobar por qué termina el proceso de RackClick</h1>
<p>Comprobación08 para la instalación <code>606b8c29-41de-4dc0-b63d-ade836000d9e</code> del servidor <strong>192.168.178.141</strong>. El informe101202 confirma ejecutable/cuenta/SID correctos y formato local_dot. Falló después en credentialed_read_check, antes de obtener el resultado del runtime. El comprobador07 generaba una orden de más de10.000caracteres; la API con credenciales admite1.024. Corregimos ese defecto usando un archivo nuevo protegido y una orden corta; registramos por separado inicio, handle, espera y resultado. La línea exacta del fallo remoto no quedó registrada y el arranque original sigue pendiente.</p>
<ol><li>Copia este ZIP a la VM. En el Explorador, clic derecho → <strong>Extraer todo</strong>, en una carpeta nueva.</li>
<li>Abre <strong>RackClick-Comprobar-Arranque</strong> y haz doble clic en <strong>00-COMPROBAR-ARRANQUE.cmd</strong>. Acepta el aviso de administrador de Windows.</li>
<li>Espera la ventana «Comprobacion terminada». Puede indicar un error: ese dato es el resultado que buscamos. No necesitas introducir la contraseña de RackClick.</li>
<li>Envía el nuevo <strong>RackClick-Informe-Arranque-Cuenta-….zip</strong> del Escritorio. Si no aparece, conserva la ventana y comunica el mensaje que muestra.</li></ol>
<p>Requiere que RackClick esté detenido; si está funcionando, sale sin detenerlo. Lee el recibo y comprueba servicio, identidad y hashes exactos de los 47 operadores del paquete05. El prefijo local literal <code>.&#92;</code> se interpreta usando el nombre real de este equipo; se sigue exigiendo exactamente el SID del recibo. No se sustituyen cuentas de dominio. Exporta sólo el formato de cuenta y causas admitidas, sin su nombre. Usa la credencial cifrada local para un único proceso de lectura con perfil de usuario y captura validación de perfil, certificado, permisos y compilación.</p>
<p><strong>No reinstala ni repara todavía.</strong> No arranca PostgreSQL o la aplicación, no ejecuta SQL, no cambia cuentas/contraseñas/servicios/tareas/certificados ni permisos existentes. Añade una carpeta nueva de resultados privados bajo management, una carpeta nueva probe-code junto a instance/management y el ZIP saneado del Escritorio. El código nuevo es propiedad de Administradores, con escritura sólo para Administradores/SYSTEM y lectura para el SID exacto del servicio; se mantiene bloqueado durante la prueba. La compilación puede crear temporales normales en la carpeta temp ya configurada. No envíes carpetas privadas.</p>
<p>Una comprobación correcta no reproduce el entorno de arranque del administrador de servicios de Windows (SCM). Si pasa, se mantiene abierta esa diferencia y las comprobaciones adicionales de Start. Si vence el límite de90segundos, conserva el informe y no repitas: el proceso de lectura podría seguir activo.</p>
<p>Los datos originales de QA ya están preparados aparte; todavía no se han restaurado en la VM. Avance global estimado78%; adopción pendiente.</p></html>'''.encode('utf-8')
    manifest = {'schemaVersion': 1, 'kind': 'RackClickExistingAccountReadCheckKit',
                'version': 8, 'installsApplication': False,
                'files': [{'path': n, 'size': len(payload[n]), 'sha256': digest(payload[n])}
                          for n in sorted(payload)]}
    payload['manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode('ascii')
    launcher = r'''#requires -Version 5.1
[CmdletBinding()]
param([switch]$VerifyOnly)
$ErrorActionPreference='Stop'
function Assert-ProbeKitPath([string]$Path){
    if(-not[IO.Path]::IsPathRooted($Path)-or$Path.StartsWith('\\')){throw 'probe_kit_path_invalid'}
    while($Path){if(((Get-Item -LiteralPath $Path -Force -ErrorAction Stop).Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){throw 'probe_kit_reparse_rejected'};$Path=[IO.Path]::GetDirectoryName($Path)}
}
function Get-ProbeKitHash([string]$Path){
    Assert-ProbeKitPath $Path
    $stream=[IO.File]::Open($Path,'Open','Read','Read');$sha=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose();$stream.Dispose()}
}
try{
    $manifestPath=Join-Path $PSScriptRoot 'manifest.json'
    if((Get-ProbeKitHash $manifestPath)-cne'__MANIFEST_SHA256__'){throw 'probe_kit_manifest_mismatch'}
    $manifest=[IO.File]::ReadAllText($manifestPath)|ConvertFrom-Json -ErrorAction Stop
    foreach($file in $manifest.files){
        if($file.path-cnotmatch'^[a-zA-Z0-9_. /-]+$'-or$file.path-match'(^|/)\.\.?(/|$)'-or$file.path.StartsWith('/')){throw 'probe_kit_path_invalid'}
        $path=Join-Path $PSScriptRoot $file.path.Replace('/','\')
        if((Get-ProbeKitHash $path)-cne$file.sha256-or(Get-Item -LiteralPath $path -Force).Length-ne$file.size){throw 'probe_kit_file_mismatch'}
    }
    if(@(Get-ChildItem -LiteralPath $PSScriptRoot -Recurse -File -Force).Count-ne($manifest.files.Count+2)){throw 'probe_kit_fileset_mismatch'}
    if($VerifyOnly){@{valid=$true;code='probe_kit_verified';files=$manifest.files.Count;privilegedOperationsExecuted=0}|ConvertTo-Json -Compress;exit 0}
}catch{Write-Output 'Paquete incompleto o alterado. Extrae de nuevo el ZIP. No se ha ejecutado la comprobacion.';exit 2}
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -STA -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'operators\Test-RackClickExistingAccount.ps1')
exit $LASTEXITCODE
'''
    payload['INICIAR-COMPROBACION.ps1'] = launcher.replace('__MANIFEST_SHA256__', digest(payload['manifest.json'])).encode('ascii')
    with output.open('xb') as target, zipfile.ZipFile(target, 'w') as archive:
        for name, content in sorted(payload.items()):
            info = zipfile.ZipInfo('RackClick-Comprobar-Arranque/' + name, (2026, 10, 20, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    return {'archive': str(output), 'bytes': output.stat().st_size,
            'sha256': digest(output.read_bytes()), 'entries': len(payload),
            'installedOperatorsPinned': len(contract()['pins']), 'elevatedProbeExecuted': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(build(parser.parse_args().output), indent=2))
