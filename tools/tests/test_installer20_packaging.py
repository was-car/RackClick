"""Native20 fixture packaging: SQL operators, no service apphost, notices and no install."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import package_server_installer as installer
import package_clean_server_installer as clean


class Installer20PackagingTests(unittest.TestCase):
    def fixture(self, root):
        local = root / '.local'; local.mkdir()
        operators = root / 'tools/windows/server-install'; operators.mkdir(parents=True)
        (operators / 'INSTALAR-RACKCLICK.cmd').write_bytes(b'fixture entry')
        (root / 'docs').mkdir()
        (root / 'docs/INSTALADOR20-SQL-PROTEGIDO.html').write_bytes(b'edition20 guide')
        for name in ('licenses/service-host-MIT.txt', 'licenses/service-host-THIRD-PARTY-NOTICES.txt',
                     'development/windows-service/packages.lock.json',
                     'tools/windows/server-reset/Start-RackClickCleanInstall.ps1'):
            dest = root / name; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes((ROOT / name).read_bytes())
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            for name in (*installer.OPERATORS, 'RackClick.SqlSecrets.ps1'):
                archive.writestr('operators/' + name, b'fixture operator')
            archive.writestr('dependencies/dotnet/LICENSE.txt', b'fixture acquired runtime notice')
        data = stream.getvalue(); pin = hashlib.sha256(data).hexdigest()
        archive = local / 'bundle.zip'; archive.write_bytes(data)
        (operators / 'RackClick.Setup.ps1').write_text("if($manifest.bundleArchiveSha256-cne'" + pin + "'){throw 'bad'}\n", 'utf-8')
        (operators / 'RackClick.Setup.Prerequisite.ps1').write_text("if($actual -cne '" + pin + "'){throw 'bad'}\n", 'utf-8')
        (operators / 'Prepare-RackClickServer.ps1').write_text(
            "if($x.Hash.ToLowerInvariant() -cne '" + pin + "'){throw 'bad'}\n$args=@('-ExpectedArchiveSha256','" + pin + "')\n", 'utf-8')
        service = local / 'service'; service.mkdir()
        for number in range(36): (service / f'dep{number}.dll').write_bytes(b'fixture library')
        (service / 'RackClick.WindowsService.dll').write_bytes(b'fixture service')
        return local, archive, service, pin

    def test_edition20_packages_sql_service37_and_package_notices(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); local, archive, service, pin = self.fixture(root)
            with patch.multiple(installer, ROOT=root, LOCAL=local,
                                SERVICE_DLL_SHA256=hashlib.sha256(b'fixture service').hexdigest()), \
                 patch.multiple(clean, ROOT=root, LOCAL=local), \
                 patch.object(installer.checked_path, '__defaults__', (root,)):
                result = clean.clean_build(archive, service, local / 'native20.zip', local / 'payload20.zip',
                                           bundle_sha256=pin, edition='20')
            self.assertEqual(result['edition'], '20'); self.assertFalse(result['installed'])
            with zipfile.ZipFile(local / 'payload20.zip') as payload:
                names = payload.namelist()
                self.assertEqual(sum(n.startswith('RackClick-Instalador/service/') for n in names), 37)
                self.assertIn('RackClick-Instalador/operators/RackClick.SqlSecrets.ps1', names)
                self.assertIn('RackClick-Instalador/LICENSES/service-host-MIT.txt', names)
                self.assertIn('RackClick-Instalador/LICENSES/service-host-THIRD-PARTY-NOTICES.txt', names)
                self.assertEqual(payload.read('RackClick-Instalador/00-EMPEZAR-AQUI.html'), b'edition20 guide')
            with zipfile.ZipFile(local / 'native20.zip') as native:
                self.assertEqual(native.read('RackClick-Servidor-20/00-LEEME.html'), b'edition20 guide')


if __name__ == '__main__': unittest.main()
