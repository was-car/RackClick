"""Real PG17 tests for the pinned original-data loader; never an installed DB.

Run with --publication <approved schema15 or45 server folder>, --loader <tool DLL>
and --plan <canonical demo-plan.json>. No tools are installed or existing bases
reused. Logs/credentials remain in the new private .local/labs directory.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys
import unittest
import uuid

from pg_support import Lab, NO_WINDOW, Client

OPTIONS = None
SOURCE_SHA = 'cb52d27990a82d3f2dc12bf731bcbe6c1586575643f301e4b040b250f31374d0'


class Rc9DemoLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lab = Lab('rc9-demo-loader').start()
        cls.publication = OPTIONS.publication
        cls.loader = OPTIONS.loader
        cls.plan = OPTIONS.plan
        cls.plan_data = json.loads(cls.plan.read_bytes())

    @classmethod
    def tearDownClass(cls):
        cls.lab.close()

    def setUp(self):
        self.db = self.lab.create_database(self._testMethodName)
        self.password = secrets.token_urlsafe(32)
        result = self.lab.bootstrap(self.db, 'demo-admin', self.password,
                                    dll=self.publication / 'RackClick.Server.dll')
        self.assertEqual(result.returncode, 0, 'Private bootstrap failed')
        self.lab.grant_runtime(self.db)
        self.house = self.lab.sql(self.db, 'SELECT id FROM systemhaus')
        self.revision = int(self.lab.sql(self.db, 'SELECT revision FROM systemhaus'))
        self.actor = self.lab.sql(self.db, 'SELECT id FROM app_user')
        # Opaque synthetic factor material: tests preservation, not TOTP validity.
        self.lab.sql(self.db, "INSERT INTO app_mfa_factor(systemhaus_id,user_id,state,secret_ciphertext,key_version) "
                     "SELECT systemhaus_id,id,'active',decode('010203040506','hex'),7 FROM app_user; "
                     "INSERT INTO app_mfa_user(systemhaus_id,user_id,mfa_required) SELECT systemhaus_id,id,true FROM app_user;")
        self.security = self.fingerprint()

    def fingerprint(self):
        tables = ['app_user', 'user_group', 'user_group_member', 'permission_grant', 'app_session',
                  'app_mfa_user', 'app_mfa_factor', 'app_mfa_challenge', 'app_mfa_recovery_code', 'app_mfa_policy']
        return tuple(self.lab.sql(self.db, "SELECT md5(COALESCE(string_agg(to_jsonb(t)::text,E'\\n' ORDER BY to_jsonb(t)::text),'')) FROM "
                                  + table + ' t', sensitive=True) for table in tables)

    def invoke(self, mode='apply', request=None, plan=None, **overrides):
        data = dict(mode=mode, connectionString=self.db.connection(self.lab.port), actorName='demo-admin',
                    expectedHouseId=self.house, expectedRevision=self.revision, requestId=request or str(uuid.uuid4()))
        data.update(overrides)
        child = subprocess.run([str(self.lab.dotnet), str(self.loader), '--plan', str(plan or self.plan)],
                               input=json.dumps(data), capture_output=True, text=True, encoding='utf-8',
                               timeout=90, env=self.lab.environment(), creationflags=NO_WINDOW)
        log = self.db.directory / ('loader-' + uuid.uuid4().hex + '-private.log')
        log.write_text(child.stdout + '\n' + child.stderr, encoding='utf-8')
        self.assertFalse(child.stderr, 'Unexpected child stderr; see private log')
        result = json.loads(child.stdout)
        self.assertEqual(child.returncode, 0 if result['success'] else 1)
        return result

    def assert_untouched(self):
        self.assertEqual(self.fingerprint(), self.security, 'Security changed')
        for table in self.plan_data['rows']:
            self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM ' + table), '0', 'Inventory changed')
        self.assertEqual(int(self.lab.sql(self.db, 'SELECT revision FROM systemhaus')), self.revision)
        self.assertEqual(self.lab.sql(self.db, "SELECT count(*) FROM audit_event WHERE action='inventory.demo.import'"), '0')
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM operation'), '0')

    def test_check_is_read_only(self):
        result = self.invoke(mode='check')
        self.assertEqual(result['code'], 'demo_import_ready')
        self.assertFalse(result['committed'])
        self.assert_untouched()

    def test_all_original_rows_security_house_and_replay(self):
        request = str(uuid.uuid4())
        result = self.invoke(request=request)
        self.assertEqual(result['code'], 'demo_import_committed')
        self.assertEqual(result['sourceSha256'], SOURCE_SHA)
        self.assertEqual(self.fingerprint(), self.security, 'Security changed')
        self.assertEqual(self.lab.sql(self.db, 'SELECT name FROM systemhaus'), 'Laboratorio RackClick')
        for table, expected in self.plan_data['rows'].items():
            columns = list(expected[0])
            projection = ','.join("'" + name + "'," + name for name in columns)
            actual = json.loads(self.lab.sql(self.db, 'SELECT jsonb_agg(jsonb_build_object(' + projection + '))::text FROM ' + table, sensitive=True))
            key = (lambda row: (row['connection_id'], row['ordinal'])) if table.endswith('_endpoint') else (lambda row: row['id'])
            self.assertTrue({key(r): r for r in actual} == {key(r): r for r in expected}, 'Original attributes differ: ' + table)
        replay = self.invoke(request=request)
        self.assertEqual(replay, result)
        self.assertEqual(self.lab.sql(self.db, "SELECT count(*) FROM audit_event WHERE action='inventory.demo.import'"), '1')
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM operation'), '1')
        self.assertEqual(self.invoke()['code'], 'inventory_not_empty')
        self.assertEqual(self.fingerprint(), self.security)

    def test_revision_conflict_preserves_everything(self):
        self.assertEqual(self.invoke(expectedRevision=self.revision + 1)['code'], 'revision_conflict')
        self.assert_untouched()

    def test_wrong_house_preserves_everything(self):
        self.assertEqual(self.invoke(expectedHouseId=str(uuid.uuid4()))['code'], 'house_mismatch')
        self.assert_untouched()

    def test_missing_global_permission_preserves_everything(self):
        self.lab.sql(self.db, "DELETE FROM permission_grant WHERE capability='customer.create'")
        self.security = self.fingerprint()
        self.assertEqual(self.invoke()['code'], 'global_admin_required')
        self.assert_untouched()

    def test_modified_plan_rejected_before_connection(self):
        path = self.db.directory / 'bad-plan.json'
        path.write_bytes(self.plan.read_bytes() + b' ')
        self.assertEqual(self.invoke(plan=path, connectionString='Password=must-not-appear;Host=remote')['code'], 'plan_hash_mismatch')
        self.assert_untouched()

    def test_owner_role_rejected(self):
        self.assertEqual(self.invoke(connectionString=self.db.connection(self.lab.port, runtime=False))['code'], 'restricted_runtime_required')
        self.assert_untouched()

    def test_runtime_with_bypass_role_rejected(self):
        self.lab.sql(self.db, 'ALTER ROLE ' + self.db.runtime + ' BYPASSRLS', admin=True)
        self.assertEqual(self.invoke()['code'], 'restricted_runtime_required')
        self.assert_untouched()

    def test_migration_digest_mismatch_rejected(self):
        self.lab.sql(self.db, "UPDATE schema_migration SET digest=repeat('0',64) WHERE version=15")
        self.assertEqual(self.invoke()['code'], 'migration_digest_mismatch')
        self.assert_untouched()

    def test_unknown_schema_rejected_before_inventory_write(self):
        self.lab.sql(self.db, "INSERT INTO schema_migration(version,digest) VALUES(999,repeat('0',64))")
        self.assertEqual(self.invoke()['code'], 'schema_profile_unsupported')
        self.assert_untouched()

    def test_gap_in_schema_history_rejected_before_inventory_write(self):
        self.lab.sql(self.db, "DELETE FROM schema_migration WHERE version=14")
        self.assertEqual(self.invoke()['code'], 'schema_profile_unsupported')
        self.assert_untouched()

    def test_audit_failure_rolls_back_data_revision_and_receipt(self):
        self.lab.sql(self.db, "CREATE FUNCTION demo_test_audit_failure() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN "
                     "IF NEW.action='inventory.demo.import' THEN RAISE EXCEPTION 'synthetic audit failure'; END IF; RETURN NEW; END $$; "
                     "CREATE TRIGGER demo_audit_failure BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION demo_test_audit_failure();")
        self.assertEqual(self.invoke()['code'], 'database_rejected')
        self.assert_untouched()

    def test_concurrent_duplicate_has_single_commit(self):
        request = str(uuid.uuid4())
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.invoke(request=request), range(2)))
        self.assertTrue(all(x.get('committed') for x in results), 'Concurrent duplicate failed')
        self.assertEqual(results[0], results[1])
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM customer'), '10')
        self.assertEqual(self.lab.sql(self.db, "SELECT count(*) FROM audit_event WHERE action='inventory.demo.import'"), '1')
        self.assertEqual(self.fingerprint(), self.security)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publication', type=Path, required=True)
    parser.add_argument('--loader', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    OPTIONS, rest = parser.parse_known_args()
    unittest.main(argv=[sys.argv[0], *rest])
