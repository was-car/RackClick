"""Migrate fresh schema-1 fixtures to the current schema without resetting data.

Requires an explicit baseline DLL built in an isolated checkout. Nothing connects
to a pre-existing cluster. These are development tests, not an installer.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import secrets
import subprocess
import sys
import unittest
import uuid
from pg_support import Lab, Client, WORKSPACE, DEFAULT_DLL, SERVER_ROOT, NO_WINDOW
from test_postgres import EvidenceResult, Tee


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.db = self.lab.create_database(self._testMethodName)
        self.password = secrets.token_urlsafe(24)
        initial = self.lab.bootstrap(self.db, 'migration-admin', self.password, dll=self.baseline)
        self.assertEqual(initial.returncode, 0, 'Baseline bootstrap failed; credentials remain private')
        self.assertEqual(self.lab.sql(self.db, 'SELECT version FROM schema_migration'), '1')
        self.house = self.lab.sql(self.db, 'SELECT id FROM systemhaus')
        self.customer = str(uuid.uuid4())
        self.lab.sql(self.db, f"INSERT INTO customer(id,systemhaus_id,name) VALUES('{self.customer}','{self.house}','Cliente München 東京')")
        self.original = self.lab.sql(self.db, "SELECT id::text || ':' || name || ':' || revision FROM systemhaus; "
            "SELECT id::text || ':' || name || ':' || revision FROM customer; SELECT id::text || ':' || username || ':' || password_hash FROM app_user;")

    def unchanged(self):
        # Compare privately; the assertion never includes a password hash on failure.
        current = self.lab.sql(self.db, "SELECT id::text || ':' || name || ':' || revision FROM systemhaus; "
            "SELECT id::text || ':' || name || ':' || revision FROM customer; SELECT id::text || ':' || username || ':' || password_hash FROM app_user;")
        self.assertTrue(current == self.original, 'Original identity, password hash, customer and revisions must be preserved')

    def migrate(self):
        environment = self.lab.environment()
        environment['ConnectionStrings__RackClick'] = self.db.connection(self.lab.port, runtime=False)
        return subprocess.run([str(self.lab.dotnet), str(DEFAULT_DLL), '--migrate'], cwd=SERVER_ROOT,
                              env=environment, capture_output=True, text=True, encoding='utf-8',
                              timeout=60, creationflags=NO_WINDOW)

    def test_upgrade_one_to_four_and_repeat_preserve_original(self):
        first = self.migrate()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(self.lab.sql(self.db, "SELECT string_agg(version::text,',' ORDER BY version) FROM schema_migration"), '1,2,3,4')
        self.unchanged()
        snapshot = self.lab.sql(self.db, "SELECT row_to_json(t) FROM schema_migration t ORDER BY version; "
            "SELECT row_to_json(t) FROM permission_grant t ORDER BY id;")
        second = self.migrate()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertTrue(snapshot == self.lab.sql(self.db, "SELECT row_to_json(t) FROM schema_migration t ORDER BY version; "
            "SELECT row_to_json(t) FROM permission_grant t ORDER BY id;"), 'Repeated migration changed history/grants')
        self.unchanged()
        self.lab.grant_runtime(self.db)
        server = self.lab.start_server(self.db)
        try:
            self.assertEqual(server.request('GET', '/health/ready').status, 200)
            client = Client(server)
            self.assertEqual(client.login('migration-admin', self.password).status, 200)
            project = client.request('GET', f'/api/v1/customers/{self.customer}/project')
            self.assertEqual(project.status, 200)
            self.assertEqual(project.json()['revision'], 1)
            self.assertEqual(project.json()['ports'], [])
            permissions = client.request('GET', '/api/v1/me').json()['permissions']
            self.assertIn('inventory.delete', permissions['systemhausCapabilities'])
        finally:
            server.close()

    def test_recorded_digest_mismatch_rejects_without_schema_change(self):
        self.lab.sql(self.db, "UPDATE schema_migration SET digest=repeat('0',64) WHERE version=1")
        result = self.migrate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('migration_digest_mismatch', result.stderr)
        self.assertEqual(self.lab.sql(self.db, "SELECT count(*) FROM schema_migration; SELECT to_regclass('inventory_site') IS NULL"), '1\nt')
        self.unchanged()

    def test_ddl_failure_rolls_back_new_schema_and_preserves_existing_fixture(self):
        # Deliberate collision in a brand-new isolated fixture, never a real database.
        self.lab.sql(self.db, 'CREATE TABLE inventory_site(test_witness text); INSERT INTO inventory_site VALUES(\'preserve-me\')')
        result = self.migrate()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.lab.sql(self.db, "SELECT count(*) FROM schema_migration; SELECT test_witness FROM inventory_site; "
            "SELECT to_regclass('inventory_building') IS NULL; SELECT to_regclass('operation_cancellation') IS NULL"), '1\npreserve-me\nt\nt')
        self.unchanged()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-dll', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    baseline = args.baseline_dll.resolve()
    if not baseline.is_file() or baseline == DEFAULT_DLL.resolve():
        parser.error('Provide a distinct, existing schema-1 baseline DLL')
    if args.evidence.exists():
        parser.error('Evidence directory already exists; select a new one')
    args.evidence.mkdir(parents=True)
    report = {'startedUtc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
              'historicalResultsReused': False, 'baselineDllSha256': hashlib.sha256(baseline.read_bytes()).hexdigest(),
              'currentDllSha256': hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()}
    lab = Lab('migration-qa')
    result = None
    try:
        with (args.evidence / 'tests-windows.log').open('w', encoding='utf-8') as output, lab:
            MigrationTests.lab, MigrationTests.baseline = lab, baseline
            report.update(labId=lab.id, postgresVersion=lab.sql('postgres', 'SHOW server_version'))
            result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2,
                resultclass=EvidenceResult).run(unittest.defaultTestLoader.loadTestsFromTestCase(MigrationTests))
            report.update(testsRun=result.testsRun, successful=result.wasSuccessful(), cases=result.records)
    except Exception as error:
        report.update(successful=False, failureType=type(error).__name__)
    finally:
        report.update(labStopped=not lab.running, finishedUtc=datetime.now(timezone.utc).isoformat())
        report['dllUnchanged'] = report['currentDllSha256'] == hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()
        if not report['dllUnchanged']:
            report['successful'] = False
        (args.evidence / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0 if report.get('successful') else 1


if __name__ == '__main__':
    raise SystemExit(main())
