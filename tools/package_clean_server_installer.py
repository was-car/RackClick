"""Build the complete clean-start envelope; inner payload stays strictly verified."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from package_server_installer import build, checked_edition, checked_path, LOCAL, ROOT, STAMP


def clean_build(archive, service_publish, output, payload_output, *, bundle_sha256, edition, stamp=STAMP):
    checked_edition(edition, bundle_sha256)
    output = checked_path(output, LOCAL)
    if output.exists() or output.suffix.lower() != '.zip' or not output.parent.is_dir():
        raise ValueError('new_zip_with_existing_parent_required')
    receipt = build(archive, service_publish, payload_output, bundle_sha256=bundle_sha256, edition=edition, stamp=stamp)
    payload = checked_path(payload_output, LOCAL).read_bytes()
    launcher = checked_path(ROOT / 'tools/windows/server-reset/Start-RackClickCleanInstall.ps1').read_text(encoding='utf-8-sig')
    if launcher.count('@@PAYLOAD_SHA256@@') != 1:
        raise ValueError('launcher_pin_token_invalid')
    launcher = launcher.replace('@@PAYLOAD_SHA256@@', receipt['sha256'])
    # The historical template keeps its original labels; each new envelope names
    # its own edition without rewriting any previously delivered archive.
    launcher = launcher.replace('RackClick 05', 'RackClick ' + edition)
    launcher = launcher.replace('RackClick-VERIFICAR-05-', 'RackClick-VERIFICAR-' + edition + '-')
    entries = {
        'Servidor.zip': payload,
        'INICIAR.ps1': launcher.replace('\r\n', '\n').replace('\n', '\r\n').encode('utf-8-sig'),
        '00-LEEME.html': checked_path(ROOT / 'docs/REINICIO-LIMPIO-SERVIDOR.html').read_bytes(),
        '00-LIMPIAR-Y-REINSTALAR.cmd': (
            '@echo off\r\nsetlocal\r\n'
            'set "RC_PS=%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"\r\n'
            'if exist "%SystemRoot%\\Sysnative\\WindowsPowerShell\\v1.0\\powershell.exe" set "RC_PS=%SystemRoot%\\Sysnative\\WindowsPowerShell\\v1.0\\powershell.exe"\r\n'
            '"%RC_PS%" -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0INICIAR.ps1"\r\n'
            'set "RC_EXIT=%ERRORLEVEL%"\r\n'
            'if not "%RC_EXIT%"=="0" if not "%RC_EXIT%"=="2" if not "%RC_EXIT%"=="3" pause\r\n'
            'exit /b %RC_EXIT%\r\n'
        ).encode('ascii'),
    }
    manifest = dict(schemaVersion=1, kind='RackClickCleanStartEnvelope', edition=edition,
                    releaseGate='server_qa_candidate', payloadSha256=receipt['sha256'],
                    files=[dict(path=name, size=len(data), sha256=hashlib.sha256(data).hexdigest())
                           for name, data in sorted(entries.items())])
    entries['PAQUETE.json'] = (json.dumps(manifest, indent=2) + '\n').encode('ascii')
    with output.open('xb') as target:
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_STORED) as package:
            for name, data in sorted(entries.items()):
                info = zipfile.ZipInfo('RackClick-Servidor-' + edition + '/' + name, stamp)
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                package.writestr(info, data)
    return dict(archive=str(output), size=output.stat().st_size,
                sha256=hashlib.sha256(output.read_bytes()).hexdigest(), payload=receipt,
                edition=edition, installed=False, published=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--payload-output', required=True, type=Path)
    parser.add_argument('--service-publish', required=True, type=Path)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--edition', required=True)
    parser.add_argument('--bundle-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(clean_build(args.archive, args.service_publish, args.output, args.payload_output,
                                 bundle_sha256=args.bundle_sha256, edition=args.edition), indent=2))
