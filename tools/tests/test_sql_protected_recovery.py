"""F-02.03: fresh Windows PG17 clusters, protected New/Restore, no SCM or VM.

Reuses the pinned application43; never builds or modifies it. Raw output, dumps
and application bootstrap credentials stay private under .local/sql-recovery-labs.
The Windows principal is the same throughout: this is not service/host acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import free_port, protect_directory

PS = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
TOOLS = ROOT / 'tools/windows'
PROBE = ROOT / 'tools/tests/sql_secrets/Invoke-SqlProtectedInstanceProbe.ps1'
ZIP_SHA = 'af1c54b288ecbf5dd42ee6db138979254817a31665a2b36e5b642ed19f554808'
MANIFEST_SHA = 'eb274f1f82deb9936c69214fae07e4188275063cf35ec775fe41d560a1806830'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())
write = lambda p, v: p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


class ProtectedRecovery(unittest.TestCase):
    @classmethod
    def call(cls, label, script, args, success=True, code=None):
        command = [str(PS), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(script)]
        for key, value in args.items():
            if isinstance(value, bool):
                if value:
                    command.append('-' + key)
            else:
                command.extend(['-' + key, str(value)])
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=240,
                              creationflags=subprocess.CREATE_NO_WINDOW)
        (cls.work / (label + '.out')).write_bytes(proc.stdout)
        (cls.work / (label + '.err')).write_bytes(proc.stderr)
        assert not proc.stderr, label + ': private stderr retained'
        value = json.loads(proc.stdout.decode('utf-8-sig'))
        assert (proc.returncode == 0) == success, (label, value)
        assert value['valid'] == success, (label, value)
        if code:
            assert value['code'] == code, (label, value)
        cls.calls.append(dict(label=label, exitCode=proc.returncode, code=value['code'], valid=value['valid']))
        return value

    @classmethod
    def setUpClass(cls):
        cls.work = ROOT / '.local/sql-recovery-labs' / ('f0203-' + uuid.uuid4().hex)
        cls.work.mkdir(parents=True, exist_ok=False)
        protect_directory(cls.work)
        cls.calls = []
        cls.sources = {str(p.relative_to(ROOT)): sha(p) for p in (
            Path(__file__), PROBE, TOOLS/'New-RackClickLabInstance.ps1',
            TOOLS/'New-RackClickRecoveredInstance.ps1', TOOLS/'RackClick.Instance.ps1',
            TOOLS/'RackClick.SqlSecrets.ps1', TOOLS/'RackClick.Backup.ps1',
            TOOLS/'RackClick.Process.ps1', TOOLS/'RackClick.Process.Gate.ps1',
            ROOT/'tools/tests/sql_secrets/Test-SqlRequestPrivacy.ps1')}
        archive = ROOT / 'RackClick-Candidata43-Revision-01.zip'
        assert sha(archive) == ZIP_SHA
        with zipfile.ZipFile(archive) as package:
            # Authenticated by the external pin, and still reject path traversal.
            for member in package.namelist():
                dest = (cls.work / 'application' / member).resolve()
                assert dest.is_relative_to(cls.work / 'application')
            package.extractall(cls.work / 'application')
        application = cls.work / 'application/RackClick-Candidata43-Revision-01/aplicacion'
        manifest = application / 'manifest.json'
        assert sha(manifest) == MANIFEST_SHA
        cls.stage = cls.work / 'stage'
        cls.dotnet = ROOT / '.local/dotnet-10.0.401/dotnet.exe'
        cls.pg = ROOT / '.local/postgresql-17.11-4/pgsql/bin'
        staged = cls.call('stage', TOOLS/'Stage-ServerDistribution.ps1', dict(
            ManifestPath=manifest, ExpectedManifestSha256=MANIFEST_SHA,
            ServerPath=application/'server', FrontendPath=application/'frontend',
            DotNetPath=cls.dotnet, PostgresBinPath=cls.pg, DestinationPath=cls.stage))
        cls.common = dict(StagePath=cls.stage, ExpectedManifestSha256=MANIFEST_SHA,
            ExpectedReceiptSha256=staged['receiptSha256'], DotNetPath=cls.dotnet,
            PostgresBinPath=cls.pg, DevelopmentLoopbackHttp=True, ProtectSqlCredentials=True)
        cls.source = cls.work / 'source'
        cls.target = cls.work / 'target'
        cls.source_args = dict(cls.common, InstancePath=cls.source, PostgresPort=free_port(),
            PublicOrigin='http://127.0.0.1:' + str(free_port()), BootstrapUser='synthetic-source',
            SystemhausName='Synthetic SQL recovery')
        src = cls.call('new-protected', TOOLS/'New-RackClickLabInstance.ps1', cls.source_args)
        cls.source_hash = src['instanceManifestSha256']
        cls.call('source-seed', PROBE, dict(InstancePath=cls.source, ExpectedInstanceSha256=cls.source_hash, Mode='Seed'))
        cls.backup = cls.work / 'export'
        backup = cls.call('source-backup', PROBE, dict(InstancePath=cls.source,
            ExpectedInstanceSha256=cls.source_hash, Mode='Backup', BackupDestination=cls.backup))
        assert sorted(p.name for p in cls.backup.iterdir()) == ['data.dump', 'manifest.json']
        cls.backup_hashes = {p.name: sha(p) for p in cls.backup.iterdir()}
        cls.target_args = dict(cls.common, InstancePath=cls.target, PostgresPort=free_port(),
            PublicOrigin='http://127.0.0.1:' + str(free_port()), RecoveryUser='synthetic-recovery',
            BackupPath=cls.backup, ExpectedBackupManifestSha256=backup['backupManifestSha256'])
        dst = cls.call('restore-protected', TOOLS/'New-RackClickRecoveredInstance.ps1', cls.target_args)
        cls.target_hash = dst['instanceManifestSha256']

    def probe(self, label, success=True, code=None):
        return self.call(label, PROBE, dict(InstancePath=self.target,
            ExpectedInstanceSha256=sha(self.target/'instance.json'), Mode='ReadOnly'), success, code)

    def test_01_new_identity_roles_and_local_ciphertext(self):
        src, dst = read(self.source/'instance.json'), read(self.target/'instance.json')
        self.assertEqual((src['schemaVersion'], dst['schemaVersion']), (2, 2))
        for key in ('id', 'database', 'owner', 'runtime', 'clusterAdmin'):
            self.assertNotEqual(src[key], dst[key])
        for name in ('owner-password.dpapi.json', 'cluster-password.dpapi.json'):
            self.assertNotEqual((self.source/'private'/name).read_bytes(), (self.target/'private'/name).read_bytes())
        for root in (self.source, self.target):
            self.assertFalse((root/'private/owner-password.txt').exists())
            self.assertFalse((root/'private/cluster-password.txt').exists())
            self.assertFalse((root/'private/initdb-password.txt').exists())
            self.assertEqual(len(list((root/'private').iterdir())), 6)
            self.assertNotIn('connectionString', read(root/'private/runtime.json'))

    def test_02_two_resumes_preserve_restored_rows_and_restricted_runtime(self):
        for n in range(2):
            result = self.call('target-resume-'+str(n), PROBE, dict(InstancePath=self.target,
                ExpectedInstanceSha256=self.target_hash, Mode='Resume'))
            self.assertEqual(result['rows'], 20)
            self.assertEqual(result['schema'], 43)
            self.assertTrue(result['runtimeDdlDenied'])
        # The source can still be resumed independently and the export never changes.
        self.call('source-unchanged', PROBE, dict(InstancePath=self.source,
            ExpectedInstanceSha256=self.source_hash, Mode='Backup', BackupDestination=self.work/'export-after'))
        self.assertEqual(self.backup_hashes, {p.name: sha(p) for p in self.backup.iterdir()})

    def test_03_existing_target_preserved(self):
        before = sha(self.target/'instance.json')
        self.call('existing-target', TOOLS/'New-RackClickRecoveredInstance.ps1', self.target_args,
                  False, 'preflight_instance_destination_exists')
        self.assertEqual(before, sha(self.target/'instance.json'))

    def test_04_missing_runtime_key_before_postgres(self):
        m = read(self.target/'instance.json')
        p = self.target/'sql-security'/m['id']/'sql-secrets/runtime.bin'
        moved = p.with_suffix('.own-test-held')
        p.rename(moved)
        try:
            value = self.probe('missing-runtime', False, 'instance_sql_ciphertext_missing')
            self.assertFalse(value['postgresStarted'])
        finally:
            moved.rename(p)

    def test_05_wrong_runtime_key_even_with_consistent_digests(self):
        manifest = self.target/'instance.json'
        original_manifest = manifest.read_bytes()
        descriptor = self.target/'private/runtime.json'
        original_descriptor = descriptor.read_bytes()
        m = read(manifest)
        p = self.target/'sql-security'/m['id']/'sql-secrets/runtime.bin'
        original = p.read_bytes()
        changed = bytearray(original)
        changed[-1] ^= 1
        try:
            p.write_bytes(changed)
            d = read(descriptor)
            d['ciphertextSha256'] = sha(p)
            write(descriptor, d)
            m['secretFiles']['runtime.json'] = sha(descriptor)
            write(manifest, m)
            result = self.probe('invalid-runtime', False, 'sql_operator_unprotect_failed')
            self.assertFalse(result['postgresStarted'])
        finally:
            p.write_bytes(original)
            descriptor.write_bytes(original_descriptor)
            manifest.write_bytes(original_manifest)

    def test_06_source_owner_ciphertext_cannot_resume_destination(self):
        manifest = self.target/'instance.json'
        original_manifest = manifest.read_bytes()
        p = self.target/'private/owner-password.dpapi.json'
        original = p.read_bytes()
        try:
            p.write_bytes((self.source/'private/owner-password.dpapi.json').read_bytes())
            m = read(manifest)
            m['secretFiles'][p.name] = sha(p)
            write(manifest, m)
            # Runtime must validate only metadata, not request privileged SQL material.
            self.call('metadata-with-foreign-owner', PROBE, dict(InstancePath=self.target,
                ExpectedInstanceSha256=sha(manifest), Mode='Metadata'))
            result = self.probe('source-owner-context', False, 'sql_operator_unprotect_failed')
            self.assertFalse(result['postgresStarted'])
        finally:
            p.write_bytes(original)
            manifest.write_bytes(original_manifest)

    def test_07_missing_owner_secret_does_not_fallback(self):
        p = self.target/'private/owner-password.dpapi.json'
        held = p.with_suffix('.own-test-held')
        p.rename(held)
        try:
            value = self.probe('missing-owner', False, 'instance_secrets_invalid')
            self.assertFalse(value['postgresStarted'])
        finally:
            held.rename(p)

    def test_08_sql_secrets_absent_from_persistent_requests_and_configuration(self):
        for name, root in (('source', self.source), ('target', self.target)):
            value = self.call('privacy-'+name, ROOT/'tools/tests/sql_secrets/Test-SqlRequestPrivacy.ps1', dict(InstancePath=root))
            self.assertEqual(value['plaintextMatches'], 0)

    @classmethod
    def tearDownClass(cls):
        assert all(sha(ROOT/p) == digest for p, digest in cls.sources.items())
        for root in (cls.source, cls.target):
            assert not (root/'pgdata/postmaster.pid').exists()
            for port in (read(root/'instance.json')['postgresPort'], read(root/'instance.json')['httpPort']):
                with socket.socket() as s:
                    assert s.connect_ex(('127.0.0.1', port)) != 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    options = parser.parse_args()
    options.evidence.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProtectedRecovery)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = dict(successful=result.wasSuccessful(), testsRun=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), seconds=round(time.monotonic()-started, 3),
        sameWindowsPrincipal=True, productSchema=43, newPgClusters=2,
        windowsServiceAcceptance=False, vmOperations=0, applicationHttpExecutions=0,
        privateFixture=getattr(ProtectedRecovery, 'work', ROOT).relative_to(ROOT).as_posix(),
        sourceHashes=getattr(ProtectedRecovery, 'sources', {}), calls=getattr(ProtectedRecovery, 'calls', []))
    write(options.evidence/'result.json', report)
    print(json.dumps({k: report[k] for k in ('successful', 'testsRun', 'failures', 'errors', 'seconds')}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
