"""Package the existing, pinned candidate for a first LOCAL installation on the server.

No compilation, installation, downloads or changes to the application's bundle.
"""
import argparse
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_SHA256 = 'a0df90ed3a2864492d8d9bdc2cc2e552113a6b9c81a3e603c1c2920486c26869'
FOLDER = 'RackClick-Servidor-Paso2-01'
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


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def build(bundle, output):
    bundle, output = Path(bundle).resolve(), Path(output).resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError('Choose a new destination with an existing parent; nothing is overwritten.')
    guide = (ROOT / 'docs/ALTA-SERVIDOR-PASO2.html').read_bytes()
    # Keep the source open and hash the same bytes which will be copied. The
    # copied archive is checked again before any entry is read or published.
    with bundle.open('rb') as source:
        if hashlib.file_digest(source, 'sha256').hexdigest() != BUNDLE_SHA256:
            raise ValueError('The archive is not the pinned 1449 candidate.')
        source.seek(0)
        output.mkdir(exist_ok=False)
        folder = output / FOLDER
        folder.mkdir()
        copied = folder / 'RackClick.zip'
        with copied.open('xb') as target:
            shutil.copyfileobj(source, target)
    if digest(copied) != BUNDLE_SHA256:
        raise ValueError('Archive changed during copy; preserve the partial output.')
    operators = folder / 'operators'
    operators.mkdir()
    with zipfile.ZipFile(copied) as archive:
        names = archive.namelist()
        expected = {'operators/' + name for name in OPERATORS}
        actual = [name for name in names if name.startswith('operators/')]
        if len(actual) != len(expected) or set(actual) != expected:
            raise ValueError('Operator inventory differs from the pinned delivery.')
        for name in OPERATORS:
            if not re.fullmatch(r'[A-Za-z0-9.-]+\.ps1', name):
                raise ValueError('Invalid operator name.')
            with (operators / name).open('xb') as target:
                target.write(archive.read('operators/' + name))
    with (folder / 'LEEME-PRIMERO.html').open('xb') as target:
        target.write(guide)
    files = sorted(path for path in folder.rglob('*') if path.is_file())
    manifest = {
        'schemaVersion': 1, 'kind': 'RackClickServerStep2',
        'scope': 'New local validation installation; not LAN or Windows service',
        'candidate': '1449-01', 'bundleSha256': BUNDLE_SHA256,
        'files': {path.relative_to(folder).as_posix(): digest(path) for path in files},
    }
    with (folder / 'MANIFIESTO.json').open('x', encoding='utf-8', newline='\n') as target:
        json.dump(manifest, target, ensure_ascii=True, indent=2)
        target.write('\n')
    outer = output / (FOLDER + '.zip')
    # The inner archive is already compressed; store it unchanged.
    with zipfile.ZipFile(outer, 'x', compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(path for path in folder.rglob('*') if path.is_file()):
            info = zipfile.ZipInfo(FOLDER + '/' + path.relative_to(folder).as_posix(),
                                   date_time=(2026, 10, 19, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    outer_sha = digest(outer)
    with (output / 'SHA256SUMS.txt').open('x', encoding='ascii', newline='\n') as target:
        target.write(outer_sha + '  ' + outer.name + '\n')
    return {'archive': str(outer), 'sha256': outer_sha, 'bundleSha256': BUNDLE_SHA256,
            'operators': len(OPERATORS), 'files': len(files) + 1,
            'productBuilds': 0, 'installationPerformed': False,
            'windowsServer2025Tested': False, 'lanOrServiceReady': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(build(arguments.bundle, arguments.output_directory)))
