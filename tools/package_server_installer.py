"""Reproducible RackClick Windows Server QA installer; never installs or publishes."""
import argparse
import hashlib
import io
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
BUNDLE_SHA256 = 'a0df90ed3a2864492d8d9bdc2cc2e552113a6b9c81a3e603c1c2920486c26869'
SERVICE_DLL_SHA256 = '130e9cc3959d414a0e00759a2e3323a0fc004d76113df56c250f319d38065c61'
PREFIX = 'RackClick-Instalador/'
NETWORK_TOOLS = frozenset({'Set-RackClickInstanceNetwork.ps1', 'Set-RackClickServerNetwork.ps1', 'Start-RackClickHere.ps1'})
STAMP = (2026, 10, 19, 0, 0, 0)
OPERATORS = (
    'Install-RackClickOfflineBundle.ps1', 'Invoke-RackClickPrivateDeployment.ps1',
    'New-RackClickDatabaseBackup.ps1', 'New-RackClickLabHttpsProfile.ps1',
    'New-RackClickLabInstance.ps1', 'New-RackClickPrivateDeployment.ps1',
    'New-RackClickRecoveredInstance.ps1', 'RackClick.Backup.ps1',
    'RackClick.Deployment.ps1', 'RackClick.Https.ps1', 'RackClick.Instance.ps1',
    'RackClick.LaunchControl.ps1', 'RackClick.OfflineBundle.ps1',
    'RackClick.Process.Gate.ps1', 'RackClick.Process.ps1', 'RackClick.Stage.ps1',
    'Restore-RackClickPrivateDeployment.ps1', 'Stage-ServerDistribution.ps1',
    'Start-RackClickLabInstance.ps1', 'Stop-RackClickLabInstance.ps1',
    'Test-RackClickOfflineBundle.ps1', 'Test-RackClickPrivateDeployment.ps1',
    'Test-RuntimePrerequisites.ps1', 'Test-ServerDistribution.ps1',
    'Test-StagedDistribution.ps1',
)


EDITION_PATTERN = re.compile(r'[0-9]{2}')
HEX64_PATTERN = re.compile(r'[0-9a-f]{64}')


def checked_edition(edition, bundle_sha256):
    """Valida la edicion antes de crear archivos. Solo dos digitos; el bundle debe ser el que fija el instalador fuente."""
    if not isinstance(edition, str) or EDITION_PATTERN.fullmatch(edition) is None:
        raise ValueError('edition_invalid')
    if not isinstance(bundle_sha256, str) or HEX64_PATTERN.fullmatch(bundle_sha256) is None:
        raise ValueError('bundle_sha256_invalid')
    setup = checked_path(ROOT / 'tools/windows/server-install/RackClick.Setup.ps1').read_text(encoding='utf-8')
    if setup.count("'" + bundle_sha256 + "'") != 1:
        raise ValueError('edition_source_pin_mismatch')
    return edition


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_path(value, within=ROOT):
    """Check original components before resolve, so links cannot disappear during validation."""
    path = Path(value).absolute()
    if not path.is_relative_to(within):
        raise ValueError('path_outside_allowed_root')
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('reparse_path_rejected')
        if item == within:
            break
    resolved = path.resolve()
    if not resolved.is_relative_to(within.resolve()):
        raise ValueError('resolved_path_outside_root')
    return resolved


def safe_name(name):
    p = PurePosixPath(name)
    if not name or '\\' in name or ':' in name or p.is_absolute() or '..' in p.parts or '.' in p.parts:
        raise ValueError('unsafe_payload_name')
    if any(part.lower() in {'private', 'secrets', 'runtime', 'logs', 'results', '.git', '.env'} for part in p.parts):
        raise ValueError('private_payload_path_rejected')


def build(archive, service_publish, output, *, bundle_sha256, edition, stamp=STAMP):
    checked_edition(edition, bundle_sha256)
    archive = checked_path(archive)
    service_publish = checked_path(service_publish, LOCAL)
    output = checked_path(output, LOCAL)
    if output.exists() or output.suffix.lower() != '.zip' or not output.parent.is_dir():
        raise ValueError('new_zip_with_existing_parent_required')
    if not archive.is_file() or not service_publish.is_dir():
        raise ValueError('input_missing')
    source = archive.read_bytes()
    if digest(source) != bundle_sha256:
        raise ValueError('original_archive_hash_mismatch')
    payload = {'RackClick.zip': source}
    with zipfile.ZipFile(io.BytesIO(source)) as original:
        names = original.namelist()
        if len(set(names)) != len(names):
            raise ValueError('duplicate_original_member')
        actual = [name for name in names if name.startswith('operators/')]
        expected = {'operators/' + name for name in OPERATORS}
        if len(actual) != 25 or set(actual) != expected:
            raise ValueError('original_operator_inventory_mismatch')
        for name in sorted(expected):
            payload[name] = original.read(name)
        for name in sorted(n for n in names if n.startswith(('licenses/', 'docs/')) and not n.endswith('/')):
            safe_name(name)
            destination = 'LICENSES/' + name.removeprefix('licenses/') if name.startswith('licenses/') else name
            payload[destination] = original.read(name)
        payload['LICENSES/dotnet-LICENSE.txt'] = original.read('dependencies/dotnet/LICENSE.txt')
    operators = checked_path(ROOT / 'tools/windows/server-install')
    for path in sorted(operators.iterdir()):
        checked_path(path)
        if path.is_file() and path.suffix.lower() in {'.ps1', '.cmd'}:
            if not re.fullmatch(r'[A-Za-z0-9.-]+\.(?:ps1|cmd)', path.name):
                raise ValueError('invalid_installer_operator')
            # Network tools pin the frozen payload hash; listing them here would make that pin self-referential.
            if path.name in NETWORK_TOOLS:
                continue
            payload['operators/server-install/' + path.name] = path.read_bytes()
    if 'operators/server-install/INSTALAR-RACKCLICK.cmd' not in payload:
        raise ValueError('installer_entry_missing')
    all_published = sorted(service_publish.rglob('*'))
    for path in all_published:
        checked_path(path, LOCAL)
    published = [path for path in all_published if path.is_file()]
    if len(published) != 38:
        raise ValueError('service_inventory_mismatch')
    for path in published:
        checked_path(path, LOCAL)
        if not path.is_file() or path.suffix.lower() not in {'.dll', '.exe', '.json', '.pdb'}:
            raise ValueError('unexpected_service_artifact')
        payload['service/' + path.relative_to(service_publish).as_posix()] = path.read_bytes()
    if digest(payload.get('service/RackClick.WindowsService.dll', b'')) != SERVICE_DLL_SHA256:
        raise ValueError('service_dll_hash_mismatch')
    payload['docs/INSTALACION-SERVIDOR-DESDE-CERO.html'] = checked_path(ROOT / 'docs/INSTALACION-SERVIDOR-DESDE-CERO.html').read_bytes()
    if edition in {'09', '10'}:
        guide = 'docs/INSTALADOR' + edition + '-ENSAYO-MFA.md'
        payload[guide] = checked_path(ROOT / guide).read_bytes()
    payload['LICENSES/service-host-dependencies.json'] = checked_path(ROOT / 'development/windows-service/packages.lock.json').read_bytes()
    payload['LICENSES/service-host-NOTICE.txt'] = b'RackClick Windows service host dependencies: Microsoft.Extensions.Hosting.WindowsServices 10.0.12 and locked Microsoft/System transitive dependencies. MIT; see dotnet-LICENSE.txt and service-host-dependencies.json. Official source: https://www.nuget.org/packages/Microsoft.Extensions.Hosting.WindowsServices/10.0.12\n'
    payload['00-EMPEZAR-AQUI.html'] = checked_path(ROOT / 'docs/INSTALACION-SERVIDOR-DESDE-CERO.html').read_bytes()
    payload['00-ESTADO.txt'] = (
        'RACKCLICK - CANDIDATA DE INSTALACION Y QA EN WINDOWS SERVER - EDICION ' + edition + '\r\n'
        'Abre 00-EMPEZAR-AQUI.html para requisitos, cuentas y recorrido completo.\r\n'
        'INSTALAR-RACKCLICK.cmd inicia el asistente PowerShell con elevacion.\r\n'
        'La instalacion esta HABILITADA: realiza preflight y comprueba cada etapa.\r\n'
        'Requiere un servidor de aplicaciones; rechaza controladores de dominio antes de cambios.\r\n'
        'VERIFICAR-INSTALACION.cmd abre el panel de acceso, backup y reinicio.\r\n'
        'El asistente exporta automaticamente un informe sin contrasenas al finalizar.\r\n'
        'RECOPILAR-INFORME.cmd permite generar otra copia del diagnostico.\r\n'
        'Instalacion elevada/SCM/reinicio se ensayan en la VM; no se afirman previos.\r\n'
        'No borres instalaciones anteriores ni bases de datos.\r\n'
        'La adopcion del servidor requiere las pruebas y confirmacion de Wascar.\r\n'
    ).encode('ascii')
    for entry, script, extra in (
        ('INSTALAR-RACKCLICK.cmd', 'Show-RackClickInstaller.ps1', ''),
        ('VERIFICAR-INSTALACION.cmd', 'Show-RackClickInstalledServer.ps1', ' -VerifyInstallation'),
        ('RECOPILAR-INFORME.cmd', 'Collect-RackClickInstallReport.ps1', ''),
    ):
        payload[entry] = (
            '@echo off\r\nsetlocal\r\n'
            'set "RC_PS=%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"\r\n'
            'if exist "%SystemRoot%\\Sysnative\\WindowsPowerShell\\v1.0\\powershell.exe" set "RC_PS=%SystemRoot%\\Sysnative\\WindowsPowerShell\\v1.0\\powershell.exe"\r\n'
            '"%RC_PS%" -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0operators\\server-install\\' + script + '"' + extra + '\r\n'
            'set "RC_EXIT=%ERRORLEVEL%"\r\n'
            'if not "%RC_EXIT%"=="0" if not "%RC_EXIT%"=="3" pause\r\n'
            'exit /b %RC_EXIT%\r\n'
        ).encode('ascii')
    for name in payload:
        safe_name(name)
    manifest = dict(schemaVersion=1, kind='RackClickServerSetup', releaseGate='server_qa_candidate',
                    bundleArchiveSha256=bundle_sha256,
                    files=[dict(path=name, size=len(payload[name]), sha256=digest(payload[name])) for name in sorted(payload)])
    payload['payload.json'] = (json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('ascii')
    # All input validation and collection precede exclusive output creation.
    with output.open('xb') as target:
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as outer:
            for name in sorted(payload):
                info = zipfile.ZipInfo(PREFIX + name, stamp)
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                outer.writestr(info, payload[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    return dict(archive=str(output), sha256=digest(output.read_bytes()), files=len(payload),
                bundleArchiveSha256=bundle_sha256, edition=edition, releaseGate='server_qa_candidate',
                installed=False, published=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--service-publish', required=True, type=Path)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--edition', required=True)
    parser.add_argument('--bundle-sha256', required=True)
    options = parser.parse_args()
    print(json.dumps(build(options.archive, options.service_publish, options.output,
                           bundle_sha256=options.bundle_sha256, edition=options.edition), indent=2))
