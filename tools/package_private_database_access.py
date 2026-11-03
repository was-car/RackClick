"""Package public code for LOCAL private access sheets; never read real credentials."""
import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
PREFIX = 'RackClick-Acceso-PostgreSQL-01/'


def checked(path):
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('access_package_reparse_rejected')
    return path


def build(output):
    output = output.absolute()
    if output.parent != LOCAL or output.suffix.lower() != '.zip' or output.exists():
        raise ValueError('new_local_zip_required')
    checked(output)
    sources = {
        '00-LEEME.html': ROOT / 'docs/ACCESO-PRIVADO-POSTGRESQL.html',
        'Show-RackClickDatabaseAccess.ps1': ROOT / 'tools/windows/server-install/Show-RackClickDatabaseAccess.ps1',
    }
    payload = {name: checked(path).read_bytes() for name, path in sources.items()}
    for name, service in (('01-ACCESO-ORIGINAL.cmd', 'RackClick'),
                          ('02-ACCESO-RESTAURADO.cmd', 'RackClick-Recovery-cb52d279')):
        payload[name] = (
            '@echo off\r\nsetlocal\r\n'
            'echo RackClick - Ficha privada web y PostgreSQL\r\n'
            'echo Ejecute como administrador EN LA VM del servidor.\r\n'
            '"%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" '
            '-NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Show-RackClickDatabaseAccess.ps1" '
            f'-ServiceName "{service}"\r\n'
            'set "rackClickAccessExit=%ERRORLEVEL%"\r\n'
            'echo Codigo final: %rackClickAccessExit%\r\npause\r\n'
            'exit /b %rackClickAccessExit%\r\n').encode('ascii')
    metadata = dict(schemaVersion=1, kind='RackClickPrivateAccessGenerator',
                    realCredentialsIncluded=False, databasesChanged=False,
                    existingInstallationChanged=False,
                    privateFileCreatedOnlyOnUserClick=True,
                    services=['RackClick', 'RackClick-Recovery-cb52d279'],
                    files=[dict(path=n, bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
                           for n, b in sorted(payload.items())])
    payload['PAQUETE.json'] = (json.dumps(metadata, indent=2) + '\n').encode('utf-8')
    with output.open('xb') as stream, zipfile.ZipFile(stream, 'w') as archive:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(PREFIX + name, (2026, 10, 21, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100600 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    return dict(bytes=output.stat().st_size,
                sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                entries=len(payload), realCredentialsIncluded=False,
                vmExecuted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(build(parser.parse_args().output), indent=2))
