"""Perfil15 cerrado: fixtures sintéticos y candidata real congelada, sin instalación ni servicios."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import build_server_distribution as builder
import package_offline_bundle as bundle

PROFILE = ROOT / 'docs/DISTRIBUCION15-PERFIL.json'
CANDIDATE = ROOT / '.local/distribution15/candidata-09'
PIN = '294b61577ed7aa8fe68ddb1ecd6c4f11a20b4f03935c11a22404009aec6a00fb'
PS = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'


def native_verify(candidate, manifest=None, digest=PIN):
    process = subprocess.run([str(PS), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                              '-File', str(ROOT / 'tools/windows/Test-ServerDistribution.ps1'),
                              '-ManifestPath', str(manifest or candidate / 'manifest.json'),
                              '-ExpectedManifestSha256', digest,
                              '-ServerPath', str(candidate / 'server'), '-FrontendPath', str(candidate / 'frontend')],
                             capture_output=True, text=True, timeout=90)
    result = json.loads(process.stdout.strip().splitlines()[-1])
    if process.returncode != result['exitCode']:
        raise AssertionError('native_exit_mismatch')
    return result


class Distribution15GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rc-dist15-', dir=ROOT / '.local')
        self.work = Path(self.temp.name)
        self.publish = self.work / 'publish'
        self.frontend = self.work / 'frontend'
        profile = builder.load_profile(PROFILE)
        for folder, names in ((self.publish, profile['serverApplicationFiles'] + profile['serverSqlFiles']),
                              (self.frontend, profile['frontendFiles'])):
            for name in names:
                destination = folder / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(('fixture:' + name).encode('ascii'))

    def tearDown(self):
        self.temp.cleanup()

    def build(self, output='candidate', profile=PROFILE):
        return builder.build(profile, self.publish, self.frontend, self.work / output,
                             '0' * 40, {'dotnet': '10.0.401', 'node': '24.21.0', 'npm': '11.19.0'}, 'synthetic fixture')

    def test_explicit_15_files_and_no_apphost(self):
        result = self.build()
        manifest = json.loads((self.work / 'candidate/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual((15, 43, 25, 18), (manifest['schema'], result['fileCount'], result['serverFiles'], result['frontendFiles']))
        self.assertIn('database/015-mfa-account-policy.sql', manifest['distributions']['server'])
        self.assertNotIn('RackClick.Server.exe', manifest['distributions']['server'])

    def test_missing_sql15_rejects_before_output(self):
        (self.publish / 'database/015-mfa-account-policy.sql').unlink()
        with self.assertRaisesRegex(builder.DistributionError, '^server_sql_missing$'):
            self.build()
        self.assertFalse((self.work / 'candidate').exists())

    def test_apphost_extra_rejects_before_output(self):
        (self.publish / 'RackClick.Server.exe').write_bytes(b'MZ')
        with self.assertRaisesRegex(builder.DistributionError, '^server_application_extra$'):
            self.build()
        self.assertFalse((self.work / 'candidate').exists())

    def test_existing_destination_preserved(self):
        destination = self.work / 'candidate'
        destination.mkdir()
        (destination / 'keep').write_bytes(b'original')
        with self.assertRaisesRegex(builder.DistributionError, '^output_exists$'):
            self.build()
        self.assertEqual(b'original', (destination / 'keep').read_bytes())

    def test_copied_profile_is_not_authoritative(self):
        copied = self.work / 'profile.json'
        shutil.copyfile(PROFILE, copied)
        with self.assertRaisesRegex(builder.DistributionError, '^profile_path_unexpected$'):
            self.build(profile=copied)
        self.assertFalse((self.work / 'candidate').exists())

    def test_deterministic_manifest(self):
        first, second = self.build('first'), self.build('second')
        self.assertEqual(first['manifestSha256'], second['manifestSha256'])
        self.assertEqual((self.work / 'first/manifest.json').read_bytes(), (self.work / 'second/manifest.json').read_bytes())

    def test_legacy_profile_stays_14(self):
        legacy = builder.load_profile()
        self.assertEqual((14, 24, 18), (legacy['applicationSchema'], legacy['serverFileCount'], legacy['frontendFileCount']))
        self.assertEqual(14, bundle.application_schema(bundle.APPLICATION_SCHEMA14D05_SHA256))

    def test_unknown_digest_stays_rejected(self):
        with self.assertRaisesRegex(bundle.BundleError, '^application_pin_mismatch$'):
            bundle.application_schema('0' * 64)


@unittest.skipUnless(sys.platform == 'win32' and CANDIDATE.is_dir(), 'requiere Windows y la candidata15 congelada')
class Distribution15CandidateTests(unittest.TestCase):
    def setUp(self):
        # Ruta exclusiva, dentro del área15 exigida por el colector, nunca se modifica la candidata.
        self.temp = tempfile.TemporaryDirectory(prefix='test-', dir=ROOT / '.local/distribution15')
        self.copy = Path(self.temp.name)
        shutil.copytree(CANDIDATE, self.copy, dirs_exist_ok=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_native_positive(self):
        result = native_verify(CANDIDATE)
        self.assertTrue(result['valid'], result)
        self.assertEqual((15, 43, 25, 18), tuple(result[key] for key in ('schema', 'verifiedFiles', 'serverFiles', 'frontendFiles')))

    def test_native_missing_sql15(self):
        (self.copy / 'server/database/015-mfa-account-policy.sql').unlink()
        self.assertEqual('distribution_files_missing', native_verify(self.copy)['code'])

    def test_native_modified_dll(self):
        with (self.copy / 'server/RackClick.Server.dll').open('ab') as output:
            output.write(b'altered')
        self.assertEqual('artifact_hash_mismatch', native_verify(self.copy)['code'])

    def test_native_extra_apphost(self):
        (self.copy / 'server/RackClick.Server.exe').write_bytes(b'MZ')
        self.assertEqual('distribution_files_extra', native_verify(self.copy)['code'])

    def test_native_unknown_manifest_even_with_matching_supplied_digest(self):
        manifest = self.copy / 'manifest.json'
        value = json.loads(manifest.read_text(encoding='utf-8'))
        value['sourceStatus'] += '; modified'
        manifest.write_text(json.dumps(value), encoding='utf-8')
        self.assertEqual('manifest_distribution_unsupported', native_verify(self.copy, digest=hashlib.sha256(manifest.read_bytes()).hexdigest())['code'])

    def test_collector_positive_pins_metadata(self):
        records, location = bundle.collect_application(CANDIDATE / 'manifest.json', PIN)
        self.assertEqual(CANDIDATE, location)
        self.assertEqual(46, len(records))
        self.assertEqual(15, bundle.application_schema(PIN))

    def test_collector_missing_metadata(self):
        (self.copy / 'inventory.json').unlink()
        with self.assertRaisesRegex(bundle.BundleError, '^application_metadata_missing$'):
            bundle.collect_application(self.copy / 'manifest.json', PIN)

    def test_collector_altered_metadata(self):
        with (self.copy / 'SHA256SUMS.txt').open('ab') as output:
            output.write(b'altered')
        with self.assertRaisesRegex(bundle.BundleError, '^application_metadata_untrusted$'):
            bundle.collect_application(self.copy / 'manifest.json', PIN)


if __name__ == '__main__':
    unittest.main()
