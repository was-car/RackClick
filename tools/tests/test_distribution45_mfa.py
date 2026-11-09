"""Closed application45/F0401 profile; integrity only, never install or use a DB."""
import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import build_server_distribution as builder
import package_offline_bundle as bundle

PROFILE = ROOT / 'docs/DISTRIBUCION45-MFA-PERFIL.json'
CANDIDATE = ROOT / '.local/distribution45/mfa-store-01'
PIN = 'a2ec1c7d3570593297a63b672ee485489e49ed0658ff49f6d2ef585803f6a8af'
PS = Path('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')


class Distribution45MfaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='distribution45-mfa-', dir=ROOT / '.local')
        self.work = Path(self.temp.name).resolve()
        self.assertTrue(self.work.is_relative_to((ROOT / '.local').resolve()))
        self.addCleanup(self.temp.cleanup)

    def invoke(self, script):
        body = "$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);" + script
        proc = subprocess.run([str(PS), '-NoProfile', '-NonInteractive', '-EncodedCommand',
            base64.b64encode(body.encode('utf-16le')).decode()], capture_output=True,
            encoding='utf-8-sig', timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, '')
        return json.loads(proc.stdout)

    def verify(self, path=CANDIDATE, pin=PIN):
        args = [str(PS), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
            '-File', str(ROOT / 'tools/windows/Test-ServerDistribution.ps1'),
            '-ManifestPath', str(path / 'manifest.json'), '-ExpectedManifestSha256', pin,
            '-ServerPath', str(path / 'server'), '-FrontendPath', str(path / 'frontend')]
        proc = subprocess.run(args, capture_output=True, encoding='utf-8-sig', timeout=60)
        self.assertEqual(proc.stderr, '')
        value = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, value['exitCode'])
        return value

    def copy(self):
        target = self.work / 'candidate'
        shutil.copytree(CANDIDATE, target)
        return target

    def test_closed_new_profile_and_old_profile_unchanged(self):
        p = builder.load_profile(PROFILE)
        self.assertEqual((p['profileId'], p['applicationSchema'], p['serverFileCount'], p['frontendFileCount']),
            ('schema45-mfa-store-01', 45, 55, 18))
        old = builder.load_profile(builder.PROFILE45_SQL_PATH)
        self.assertEqual(old['candidate']['manifestSha256'],
            '528a03d2efc939d1cea631b1caa9f3e6a445e44257fa757f87a95691acfb6933')
        self.assertEqual(bundle.application_schema(PIN), 45)
        self.assertEqual(len(bundle.operator_names(PIN)), 26)
        self.assertEqual(bundle.APPLICATION_PROFILES[PIN]['name'], '45-sql')

    def test_copy_of_profile_does_not_authorize(self):
        copy = self.work / 'profile.json'
        shutil.copyfile(PROFILE, copy)
        with self.assertRaisesRegex(builder.DistributionError, '^profile_path_unexpected$'):
            builder.load_profile(copy)

    def test_native_new_profile(self):
        value = self.verify()
        self.assertEqual((value['code'], value['schema'], value['verifiedFiles'], value['serverFiles'], value['frontendFiles']),
            ('artifacts_verified', 45, 73, 55, 18))

    def test_native_historical45_and43_still_pass(self):
        for path, pin in [(ROOT / '.local/distribution45/sql-01', bundle.APPLICATION_SCHEMA45_SQL_SHA256),
                          (ROOT / '.local/sql-integracion-12/distribution', bundle.APPLICATION_SCHEMA43_SQL_SHA256)]:
            with self.subTest(schema=path.name):
                self.assertEqual(self.verify(path, pin)['code'], 'artifacts_verified')

    def test_wrong_external_digest_rejected(self):
        self.assertEqual(self.verify(pin='0' * 64)['code'], 'manifest_untrusted')

    def test_unknown_rehashed_manifest_rejected(self):
        copy = self.copy()
        path = copy / 'manifest.json'
        value = json.loads(path.read_text())
        value['sourceStatus'] = 'attacker supplied internally coherent manifest'
        path.write_text(json.dumps(value), encoding='utf-8')
        pin = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(self.verify(copy, pin)['code'], 'manifest_distribution_unsupported')

    def test_modified_dll_rejected(self):
        copy = self.copy()
        path = copy / 'server/RackClick.Server.dll'
        path.write_bytes(path.read_bytes() + b'changed')
        self.assertEqual(self.verify(copy)['code'], 'artifact_hash_mismatch')

    def test_extra_and_missing_files_rejected(self):
        copy = self.copy()
        extra = copy / 'server/extra.txt'
        extra.write_bytes(b'extra')
        self.assertEqual(self.verify(copy)['code'], 'distribution_files_extra')
        extra.unlink()
        (copy / 'server/database/045-german-repeaters-hardware.sql').unlink()
        self.assertEqual(self.verify(copy)['code'], 'distribution_files_missing')

    def test_collector_accepts_fixed_candidate(self):
        entries, root = bundle.collect_application(CANDIDATE / 'manifest.json', PIN)
        self.assertEqual(root, CANDIDATE)
        self.assertEqual(len(entries), 76)  # manifest + 73 application + two pinned metadata files

    def test_collector_rejects_relocated_identical_candidate(self):
        copy = self.copy()
        with self.assertRaisesRegex(bundle.BundleError, '^application_root_invalid$'):
            bundle.collect_application(copy / 'manifest.json', PIN)

    def test_collector_rejects_unknown_pin(self):
        with self.assertRaisesRegex(bundle.BundleError, '^application_pin_mismatch$'):
            bundle.collect_application(CANDIDATE / 'manifest.json', '0' * 64)

    def test_collector_rejects_missing_pinned_metadata(self):
        copy = self.work / '.local/distribution45/mfa-store-01'
        shutil.copytree(CANDIDATE, copy)
        (copy / 'inventory.json').unlink()
        with mock.patch.object(bundle, 'ROOT', self.work):
            with self.assertRaisesRegex(bundle.BundleError, '^application_metadata_missing$'):
                bundle.collect_application(copy / 'manifest.json', PIN)

    def test_collector_rejects_modified_pinned_metadata(self):
        copy = self.work / '.local/distribution45/mfa-store-01'
        shutil.copytree(CANDIDATE, copy)
        (copy / 'SHA256SUMS.txt').write_bytes(b'changed')
        with mock.patch.object(bundle, 'ROOT', self.work):
            with self.assertRaisesRegex(bundle.BundleError, '^application_metadata_untrusted$'):
                bundle.collect_application(copy / 'manifest.json', PIN)

    def test_native_profile_keeps_sql_protection_family_and_operator_inventory(self):
        result = self.invoke(". '" + str(ROOT / 'tools/windows/RackClick.OfflineBundle.ps1') + "';"
            "$p=Get-OfflineBundleApplicationProfile '" + PIN + "';"
            "@{name=$p.name;schema=(Get-OfflineBundleExpectedSchema $p);operators=@(Get-OfflineBundleOperatorNames $p).Count;sql=@(Get-OfflineBundleOperatorNames $p)-ccontains'RackClick.SqlSecrets.ps1'}|ConvertTo-Json -Compress")
        self.assertEqual(result, dict(name='45-sql', schema=45, operators=26, sql=True))


if __name__ == '__main__':
    unittest.main()
