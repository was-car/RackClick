"""Build the small read-only diagnostic kit; never install or start RackClick."""
import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
SOURCES = (
    'Collect-RackClickInstallReport.ps1', 'RackClick.Setup.ps1',
    'RackClick.Setup.Security.ps1', 'RackClick.Setup.Diagnostics.ps1',
    'RackClick.Setup.ServiceDiagnostics.ps1', 'RackClick.Setup.ServiceStatus.ps1',
)


def build(output):
    output = output.absolute()
    if not output.is_relative_to(LOCAL) or output.suffix.lower() != '.zip' or output.exists():
        raise ValueError('new_local_zip_required')
    if output.is_symlink() or output.is_junction():
        raise ValueError('reparse_path_rejected')
    for path in (output.parent, *output.parent.parents):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('reparse_path_rejected')
        if path == ROOT:
            break
    payload = {}
    for name in SOURCES:
        path = ROOT / 'tools/windows/server-install' / name
        for item in (path, *path.parents):
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('reparse_path_rejected')
            if item == ROOT:
                break
        payload['operators/' + name] = path.read_bytes()
    payload['RECUPERAR-DIAGNOSTICO.cmd'] = (
        '@echo off\r\nsetlocal\r\n'
        'set "RC_PS=%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"\r\n'
        'if exist "%SystemRoot%\\Sysnative\\WindowsPowerShell\\v1.0\\powershell.exe" set "RC_PS=%SystemRoot%\\Sysnative\\WindowsPowerShell\\v1.0\\powershell.exe"\r\n'
        '"%RC_PS%" -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0INICIAR-DIAGNOSTICO.ps1"\r\n'
        'set "RC_EXIT=%ERRORLEVEL%"\r\n'
        'if not "%RC_EXIT%"=="0" pause\r\nexit /b %RC_EXIT%\r\n'
    ).encode('ascii')
    payload['00-LEEME.html'] = '''<!doctype html><html lang="es"><meta charset="utf-8">
<title>RackClick · recuperar diagnóstico</title>
<style>body{font:18px/1.6 system-ui;max-width:850px;margin:50px auto;padding:0 24px;color:#192b3a}code{background:#eef2f5;padding:2px 5px}</style>
<h1>Recuperar el diagnóstico del intento existente</h1>
<p>Este paquete lee hasta diez intentos recientes del instalador y los separa por identificador. Así conserva el error de preparación anterior aunque después haya otro fallo de verificación. No instala RackClick, no crea cuentas o bases, no arranca servicios y no cambia permisos de las carpetas.</p>
<ol><li>En la VM Windows Server, usa la misma cuenta de Windows con la que ejecutaste el instalador. Extrae todo este ZIP en una carpeta nueva.</li>
<li>Dentro de <code>RackClick-Diagnostico</code>, haz doble clic en <strong>RECUPERAR-DIAGNOSTICO.cmd</strong>. Acepta el aviso de permisos de Windows.</li>
<li>Espera el mensaje de confirmación. En el Escritorio aparecerá un nuevo <code>RackClick-Informe-Instalacion-….zip</code>. Envía ese ZIP a Codex.</li></ol>
<p>Conserva los intentos anteriores y la aplicación tal como están. No repitas la instalación para recoger este informe.</p>
<p>El informe conserva los resultados históricos de instalación por identificador. Además toma una medición actual del servicio, último arranque y eventos relacionados de Windows, y resume los registros privados del host y del runtime y el archivo de estado de PostgreSQL. Los separa por fecha: un resultado antiguo de95% no demuestra que el servicio esté funcionando ahora.</p>
<p>No arranca ni detiene servicios, no restaura bases, no borra el archivo de PostgreSQL ni cambia permisos. Exporta únicamente campos admitidos y códigos; excluye contraseñas, variables de entorno, request.json, certificados privados y logs completos. Para leer los registros privados utiliza temporalmente el permiso de lectura de backup del administrador y restaura después su estado previo.</p>
<p>20.10.2026 · Diagnóstico05 de arranque. Se estudia el servicio que intenta arrancar y vuelve a detenerse; todavía no hay causa confirmada ni reparación acreditada. Avance global aproximado78%.</p></html>'''.encode('utf-8')
    digest = lambda data: hashlib.sha256(data).hexdigest()
    manifest = {
        'schemaVersion': 1, 'kind': 'RackClickReadOnlySetupDiagnostics',
        'diagnosticVersion': 5, 'installsApplication': False,
        'files': [{'path': n, 'size': len(payload[n]), 'sha256': digest(payload[n])}
                  for n in sorted(payload)],
    }
    payload['manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode('ascii')
    launcher = r'''#requires -Version 5.1
[CmdletBinding()]
param([switch]$VerifyOnly)
$ErrorActionPreference='Stop'
function Assert-DiagnosticKitPath([string]$Path){
    if(-not[IO.Path]::IsPathRooted($Path)-or$Path.StartsWith('\\')){throw 'diagnostic_kit_path_invalid'}
    while($Path){if(((Get-Item -LiteralPath $Path -Force -ErrorAction Stop).Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){throw 'diagnostic_kit_reparse_rejected'};$Path=[IO.Path]::GetDirectoryName($Path)}
}
function Get-DiagnosticKitHash([string]$Path){
    Assert-DiagnosticKitPath $Path
    $stream=[IO.File]::Open($Path,'Open','Read','Read');$sha=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose();$stream.Dispose()}
}
try{
    $manifestPath=Join-Path $PSScriptRoot 'manifest.json'
    if((Get-DiagnosticKitHash $manifestPath)-cne'__MANIFEST_SHA256__'){throw 'diagnostic_kit_manifest_mismatch'}
    $manifest=[IO.File]::ReadAllText($manifestPath)|ConvertFrom-Json -ErrorAction Stop
    foreach($file in $manifest.files){
        if($file.path-cnotmatch'^[a-zA-Z0-9_. /-]+$'-or$file.path-match'(^|/)\.\.?(/|$)'-or$file.path.StartsWith('/')){throw 'diagnostic_kit_path_invalid'}
        $path=Join-Path $PSScriptRoot $file.path.Replace('/','\')
        if((Get-DiagnosticKitHash $path)-cne$file.sha256-or(Get-Item -LiteralPath $path -Force).Length-ne$file.size){throw 'diagnostic_kit_file_mismatch'}
    }
    if(@(Get-ChildItem -LiteralPath $PSScriptRoot -Recurse -File -Force).Count-ne($manifest.files.Count+2)){throw 'diagnostic_kit_fileset_mismatch'}
    if($VerifyOnly){@{valid=$true;code='diagnostic_kit_verified';files=$manifest.files.Count;privilegedOperationsExecuted=0}|ConvertTo-Json -Compress;exit 0}
}catch{Write-Output 'El paquete de diagnostico esta incompleto o alterado. Extrae de nuevo el ZIP recibido. No se ha ejecutado la recopilacion.';exit 2}
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -STA -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'operators\Collect-RackClickInstallReport.ps1')
exit $LASTEXITCODE
'''
    payload['INICIAR-DIAGNOSTICO.ps1'] = launcher.replace('__MANIFEST_SHA256__', digest(payload['manifest.json'])).encode('ascii')
    with output.open('xb') as target, zipfile.ZipFile(target, 'w') as archive:
        for name in sorted(payload):
            info = zipfile.ZipInfo('RackClick-Diagnostico/' + name, (2026, 10, 20, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    return {'archive': str(output), 'sha256': digest(output.read_bytes()),
            'bytes': output.stat().st_size, 'entries': len(payload),
            'installsApplication': False, 'privilegedCollectionExecuted': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    print(json.dumps(build(parser.parse_args().output), indent=2))
