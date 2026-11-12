"""Separate schema48 profile; no SQL or historical definition changes."""
import json
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import build_server_distribution as distribution
import build_online_installer20 as release

APP = ROOT / '.local/distribution48/admin-data-01'


class AdminDataProfileTests(unittest.TestCase):
    def test_admin_data_has_its_own_closed_profile_with_the_same_48_sql(self):
        path = ROOT / 'docs/DISTRIBUCION48-ADMIN-DATA-PERFIL.json'
        self.assertTrue(path.is_file(), 'the new application must have a separate profile')
        actual = distribution.load_profile(path)
        previous = distribution.load_profile(ROOT / 'docs/DISTRIBUCION48-PERFIL.json')
        self.assertEqual(actual['profileId'], 'schema48-admin-data-01')
        for name in ('serverApplicationFiles', 'serverSqlFiles', 'frontendFiles', 'hosting'):
            self.assertEqual(actual[name], previous[name], name)
        self.assertEqual(actual['applicationSchema'], 48)
        self.assertNotIn('candidate', actual)


@unittest.skipUnless(APP.is_dir() and release.APP_SHA, 'requires the coordinator frozen application48 admin-data')
class FrozenAdminDataDistributionTests(unittest.TestCase):
    def verify(self, path=APP, pin=None):
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                 '-File', str(ROOT / 'tools/windows/Test-ServerDistribution.ps1'),
                                 '-ManifestPath', str(path / 'manifest.json'), '-ExpectedManifestSha256', pin or release.APP_SHA,
                                 '-ServerPath', str(path / 'server'), '-FrontendPath', str(path / 'frontend')],
                                capture_output=True, encoding='utf-8-sig', timeout=60)
        self.assertFalse(result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, report['exitCode'])
        return report

    def copy(self):
        temporary = tempfile.TemporaryDirectory(prefix='distribution48-admin-data-', dir=ROOT / '.local')
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / 'application'
        shutil.copytree(APP, path)
        return path

    def test_real_closed_application76(self):
        report = self.verify()
        self.assertEqual(report['code'], 'artifacts_verified')
        self.assertEqual((report['code'], report['schema'], report['verifiedFiles']), ('artifacts_verified', 48, 76))
        self.assertEqual(len(release.verify_application(APP)), 79)

    def test_wrong_external_digest(self):
        self.assertEqual(self.verify(pin='0' * 64)['code'], 'manifest_untrusted')

    def test_changed_manifest_cannot_authorize_itself(self):
        path = self.copy(); manifest = path / 'manifest.json'
        document = json.loads(manifest.read_text('utf-8')); document['sourceStatus'] = 'altered'
        manifest.write_text(json.dumps(document), 'utf-8')
        self.assertEqual(self.verify(path, hashlib.sha256(manifest.read_bytes()).hexdigest())['code'],
                         'manifest_distribution_unsupported')

    def test_crossing_historical_profile_is_rejected(self):
        path = self.copy(); manifest = path / 'manifest.json'
        document = json.loads(manifest.read_text('utf-8')); document['profileId'] = 'schema48-maintenance-01'
        manifest.write_text(json.dumps(document), 'utf-8')
        self.assertEqual(self.verify(path, hashlib.sha256(manifest.read_bytes()).hexdigest())['code'],
                         'manifest_distribution_unsupported')

    def test_changed_dll(self):
        path = self.copy(); target = path / 'server/RackClick.Server.dll'
        target.write_bytes(target.read_bytes() + b'altered')
        self.assertEqual(self.verify(path)['code'], 'artifact_hash_mismatch')

    def test_missing_sql48(self):
        path = self.copy(); (path / 'server/database/048-mfa-loss-startup.sql').unlink()
        self.assertEqual(self.verify(path)['code'], 'distribution_files_missing')

    def test_extra_apphost(self):
        path = self.copy(); (path / 'server/RackClick.Server.exe').write_bytes(b'extra')
        self.assertEqual(self.verify(path)['code'], 'distribution_files_extra')


if __name__ == '__main__':
    unittest.main()
