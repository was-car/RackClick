"""State context54: explicit schema6 DLL/frontend, isolated PostgreSQL labs, no live QA."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest
import uuid

from pg_support import Client, Lab, NO_WINDOW, SERVER_ROOT, WORKSPACE
from test_postgres import EvidenceResult, Tee
from test_admin_audit_context import AuditContextPostgres

BASELINE_INFO = WORKSPACE/'evidence/s1-20261017/tres-tandas-54/BASELINE.json'
BASELINE = json.loads(BASELINE_INFO.read_text(encoding='utf-8'))


def uid():
    return str(uuid.uuid4())


class AuditStateContextPostgres(AuditContextPostgres):
    dll = frontend = baseline_dll = None

    def initialize(self, username='qa-admin', baseline=False):
        dll = self.baseline_dll if baseline else self.dll
        self.assertEqual(self.lab.bootstrap(self.db, username, self.password, dll=dll).returncode, 0)
        self.lab.grant_runtime(self.db)
        self.house = self.lab.sql(self.db, 'SELECT id FROM systemhaus')
        self.admin_id = self.lab.sql(self.db, 'SELECT id FROM app_user')
        self.server = self.lab.start_server(self.db, dll=dll, frontend=self.frontend)
        self.admin = Client(self.server); self.expect(self.admin.login(username, self.password), 200)
        return self.admin

    def state(self, user, active, cancel=False, key=None, revision=None, status=200):
        return self.write(f'/api/v1/admin/users/{user}/state', {'active': active}, cancel=cancel,
            key=key, revision=revision, status=status)

    def state_expected(self, user, before, cancel=False):
        expected = self.expected(user, before, cancel)
        expected['objects'][0]['kind'] = 'user'
        return expected

    def migrate(self, database=None):
        database = database or self.db
        env = self.lab.environment(); env['ConnectionStrings__RackClick'] = database.connection(self.lab.port, runtime=False)
        result = subprocess.run([str(self.lab.dotnet), str(self.dll), '--migrate'], cwd=SERVER_ROOT,
            env=env, capture_output=True, text=True, encoding='utf-8', timeout=60, creationflags=NO_WINDOW)
        (database.directory/f'migrate-six-{uuid.uuid4().hex[:8]}.log').write_text(result.stdout + result.stderr, encoding='utf-8')
        return result

    def test_state_context_migration_five_six_preserves_repeat_and_atomic_failure(self):
        self.initialize(baseline=True)
        self.assertEqual(self.lab.sql(self.db, 'SELECT max(version) FROM schema_migration'), '5')
        create_key, made = self.write('/api/v1/admin/users', {'username': 'before-six', 'password': self.password}, status=201)
        user = made['resource']['id']; create_event = self.event_for(create_key)
        cancel_key, _ = self.write('/api/v1/admin/users', {'username': 'cancel-before-six'}, cancel=True, revision=1)
        cancel_event = self.event_for(cancel_key)
        state_key, _ = self.state(user, True)
        old_state_event = self.event_for(state_key)
        self.read(create_event, self.expected(user, 1))
        self.read(cancel_event, self.expected(self.house, 2, True))
        self.read(old_state_event, self.not_recorded())
        tables, before = self.table_digest(self.db)
        history = self.lab.sql(self.db, 'SELECT row_to_json(t) FROM schema_migration t ORDER BY version')
        self.server.close()
        self.assertEqual(self.migrate().returncode, 0)
        self.assertEqual(before, self.table_digest(self.db, tables)[1])
        self.assertEqual(history, self.lab.sql(self.db, 'SELECT row_to_json(t) FROM schema_migration t WHERE version<=5 ORDER BY version'))
        history6 = self.lab.sql(self.db, 'SELECT row_to_json(t) FROM schema_migration t ORDER BY version')
        self.assertEqual(self.lab.sql(self.db, 'SELECT max(version) FROM schema_migration'), '6')
        self.assertEqual(self.migrate().returncode, 0)
        self.assertEqual(history6, self.lab.sql(self.db, 'SELECT row_to_json(t) FROM schema_migration t ORDER BY version'))
        self.assertEqual(before, self.table_digest(self.db, tables)[1])
        self.server = self.lab.start_server(self.db, dll=self.dll, frontend=self.frontend)
        self.admin.server = self.server
        self.read(create_event, self.expected(user, 1))
        self.read(cancel_event, self.expected(self.house, 2, True))
        self.read(old_state_event, self.not_recorded())
        snapshot = self.durable()
        self.state(user, True, key=state_key, revision=2)
        self.assertEqual(snapshot, self.durable(), 'Replay must not backfill pre006 state context')
        self.read(old_state_event, self.not_recorded())
        key, _ = self.state(uid(), False, cancel=True, revision=1)
        self.read(self.event_for(key), self.state_expected(
            self.lab.sql(self.db, f"SELECT resource_id FROM audit_event WHERE request_id='{key}'"), 3, True))
        # A second-statement collision verifies DROP of the005 check also rolls back.
        failed = self.lab.create_database('migration-six-atomic-collision')
        self.assertEqual(self.lab.bootstrap(failed, 'qa-admin', self.password, dll=self.baseline_dll).returncode, 0)
        self.lab.sql(failed, 'ALTER TABLE audit_context_object ADD CONSTRAINT audit_context_object_kind_relation_check CHECK (true)')
        old_tables, old = self.table_digest(failed)
        old_checks = self.lab.sql(failed, "SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='audit_context_object'::regclass ORDER BY conname")
        self.assertNotEqual(self.migrate(failed).returncode, 0)
        self.assertEqual(old, self.table_digest(failed, old_tables)[1])
        self.assertEqual(old_checks, self.lab.sql(failed, "SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='audit_context_object'::regclass ORDER BY conname"))
        self.assertEqual(self.lab.sql(failed, 'SELECT max(version) FROM schema_migration'), '5')
        self.lab.sql(failed, 'ALTER TABLE audit_context_object DROP CONSTRAINT audit_context_object_kind_relation_check')
        self.assertEqual(self.migrate(failed).returncode, 0)

    def test_state_context_commit_noop_cancel_replay_and_persistence(self):
        self.initialize()
        user, old = self.add_user('state-context54')
        second_target = Client(self.server); self.expect(second_target.login('state-context54', self.password), 200)
        key, made = self.state(user, False, revision=1)
        event = self.event_for(key); expected = self.state_expected(user, 1)
        self.read(event, expected)
        for client in (old, second_target): self.expect(client.request('GET', '/api/v1/me'), 401)
        noop, _ = self.state(user, False)
        self.read(self.event_for(noop), self.state_expected(user, 2))
        self.state(user, True)
        fresh = Client(self.server); self.expect(fresh.login('state-context54', self.password), 200)
        before = self.durable()
        _, replay = self.state(user, False, key=key, revision=1)
        self.assertEqual(replay, made)
        self.assertEqual(before, self.durable())
        self.expect(fresh.request('GET', '/api/v1/me'), 200)
        self.read(event, expected)
        target = uid()
        cancel_key, cancelled = self.state(target, False, cancel=True, revision=1)
        cancel_event = self.event_for(cancel_key); cancelled_expected = self.state_expected(target, 4, True)
        self.read(cancel_event, cancelled_expected)
        before = self.durable()
        _, repeated = self.state(target, False, cancel=True, key=cancel_key, revision=1)
        self.assertEqual(repeated, cancelled)
        _, committed = self.state(user, False, cancel=True, key=key, revision=1)
        self.assertEqual(committed, {'requestId': key, 'state': 'committed', 'operation': made})
        self.state(target, False, key=cancel_key, revision=1, status=409)
        self.state(user, True, key=key, revision=1, status=409)
        self.state(user, False, revision=1, status=412)
        self.state(self.admin_id, False, status=409)  # Last active global administrator still protected.
        self.assertEqual(before, self.durable())
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM audit_context; SELECT count(*) FROM audit_context_object'), '4\n4')
        second_admin = Client(self.server); self.expect(second_admin.login('qa-admin', self.password), 200)
        self.read(event, expected, second_admin); self.read(cancel_event, cancelled_expected, second_admin)
        self.server.close(); self.server = self.lab.start_server(self.db, dll=self.dll, frontend=self.frontend)
        self.admin.server = second_admin.server = fresh.server = self.server
        self.read(event, expected, second_admin); self.read(cancel_event, cancelled_expected, second_admin)
        self.expect(fresh.request('GET', '/api/v1/me'), 200)

    def test_state_context_rollback_both_tables_state_sessions_and_cancel(self):
        self.initialize()
        user, _ = self.add_user('rollback-state54')
        for table in ('audit_context', 'audit_context_object'):
            for cancel in (False, True):
                self.lab.sql(self.db, f"UPDATE app_user SET active=true WHERE id='{user}'")
                session = Client(self.server); self.expect(session.login('rollback-state54', self.password), 200)
                revision, key = self.house_revision(), uid()
                self.lab.sql(self.db, f"""CREATE FUNCTION fail_state_context54() RETURNS trigger LANGUAGE plpgsql AS $$
                    BEGIN RAISE EXCEPTION 'synthetic state context failure54'; END; $$;
                    CREATE TRIGGER fail_state_context54 BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION fail_state_context54();""")
                before = self.durable()
                self.state(user, False, cancel=cancel, key=key, revision=revision, status=503)
                self.assertEqual(before, self.durable(), 'Context failure must restore account/sessions and every durable row')
                self.expect(session.request('GET', '/api/v1/me'), 200)
                self.lab.sql(self.db, f'DROP TRIGGER fail_state_context54 ON {table}; DROP FUNCTION fail_state_context54()')
                self.state(user, False, cancel=cancel, key=key, revision=revision)
                self.read(self.event_for(key), self.state_expected(user, revision, cancel))
                self.expect(session.request('GET', '/api/v1/me'), 200 if cancel else 401)
                self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM audit_event WHERE request_id='{key}'; SELECT count(*) FROM operation WHERE request_id='{key}'"), '1\n1')

    def test_state_context_authority_coherence_and_creation_point_regression(self):
        self.initialize()
        user, plain = self.add_user('authority-state54')
        key, _ = self.state(user, True)
        self.read(self.event_for(key), self.state_expected(user, 1))
        customer = self.customer('Scoped state54'); group = self.user_group(user)
        self.grant(group, 'security.manage', customer=customer['id'])
        cg = self.customer_group(); self.grant(group, 'security.manage', customer_group=cg)
        before = self.durable()
        for cancel in (False, True):
            request = uid(); path = f'/api/v1/admin/users/{user}/state'
            if cancel: path += f'/operations/{request}/cancel'
            self.expect(plain.request('POST', path, {'active': False}, {'If-Match': '"1"',
                'Idempotency-Key': request, 'X-RackClick-Actor': user}), 403, 'forbidden')
        self.expect(self.context('bad', plain), 403, 'forbidden')
        self.expect(self.context('bad', Client(self.server)), 401, 'authentication_required')
        self.assertEqual(before, self.durable())
        foreign, _, _ = self.foreign(); foreign_event = uid()
        self.lab.sql(self.db, f"""INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,after_json)
            SELECT '{foreign_event}',systemhaus_id,id,'{uid()}','user.state.set','{uid()}','{{}}' FROM app_user WHERE id='{foreign}'""")
        missing = self.expect(self.context(uid()), 404, 'not_found')
        self.assertEqual(missing.json(), self.expect(self.context(foreign_event), 404, 'not_found').json())
        for raw in ('bad', str(uuid.UUID(int=0)), key.replace('-', '')):
            self.expect(self.context(raw), 422, 'request_invalid')
        target = uid(); cancel_key, _ = self.state(target, False, cancel=True, revision=1)
        event = self.event_for(cancel_key); expected = self.state_expected(target, 3, True)
        self.read(event, expected)
        for kind, relation in [('systemhaus', 'intendedTarget'), ('user', 'target')]:
            self.lab.sql(self.db, f"UPDATE audit_context_object SET kind='{kind}',relation='{relation}' WHERE event_id='{event}'")
            self.read(event, self.not_recorded())
        self.lab.sql(self.db, f"UPDATE audit_context_object SET kind='user',relation='intendedTarget',object_id='{uid()}' WHERE event_id='{event}'")
        self.read(event, self.not_recorded())
        self.lab.sql(self.db, f"UPDATE audit_context_object SET object_id='{target}',position=2 WHERE event_id='{event}'")
        self.read(event, self.not_recorded())
        self.lab.sql(self.db, f"UPDATE audit_context_object SET position=1 WHERE event_id='{event}'")
        self.read(event, expected)
        # This pre-existing pair is checked only at points; no prior groups are rerun.
        create_key, made = self.write('/api/v1/admin/users', {'username': 'creation-regression54', 'password': self.password}, status=201)
        self.read(self.event_for(create_key), self.expected(made['resource']['id'], 3))
        create_cancel, _ = self.write('/api/v1/admin/users', {'username': 'creation-cancel-regression54'}, cancel=True, revision=1)
        self.read(self.event_for(create_cancel), self.expected(self.house, 4, True))
        # New check broadens only the user/intendedTarget pair; House/target remains invalid.
        with self.assertRaises(RuntimeError):
            self.lab.sql(self.db, f"UPDATE audit_context_object SET kind='systemhaus',relation='target' WHERE event_id='{event}'")
        self.read(event, expected)
        public = json.dumps(self.read(event, expected))
        self.assertNotIn(self.password, public)
        secrets = self.lab.sql(self.db, 'SELECT password_hash FROM app_user UNION ALL SELECT token_hash FROM app_session UNION ALL SELECT csrf_hash FROM app_session').splitlines()
        self.assertTrue(all(secret not in public for secret in secrets), 'Identity secret leaked')
        self.assertNotIn('sessions', public)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--frontend', type=Path, required=True)
    parser.add_argument('--baseline-dll', type=Path, default=WORKSPACE/BASELINE['serverDll'])
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    names = [name for name in unittest.defaultTestLoader.getTestCaseNames(AuditStateContextPostgres) if name.startswith('test_state_context_')]
    if args.case:
        if set(args.case) - set(names): raise ValueError('Unknown state context case')
        names = [name for name in names if name in args.case]
    args.evidence.mkdir(parents=True, exist_ok=False)
    args.dll = args.dll.resolve(); args.frontend = args.frontend.resolve(); args.baseline_dll = args.baseline_dll.resolve()
    files = [WORKSPACE/'development/server/src/RackClick.Server'/name for name in
        ('AdminAuditContext.cs', 'AdminUserState.cs', 'SchemaMigrations.cs', 'OpenApiAudit.cs', 'AdminUsers.cs')]
    files += list((WORKSPACE/'development/server/database').glob('*.sql')) + [Path(__file__).resolve(),
        WORKSPACE/'development/server/tests/test_admin_audit_context.py', WORKSPACE/'development/server/tests/pg_support.py']
    def hashes(): return {path.relative_to(WORKSPACE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    def distribution(path, expected): return {name: hashlib.sha256((path/name).read_bytes()).hexdigest() for name in expected}
    immutable = {'server': distribution(args.baseline_dll.parent, BASELINE['distributions']['server']),
                 'frontend': distribution(args.frontend, BASELINE['distributions']['frontend'])}
    if immutable != BASELINE['distributions']: raise RuntimeError('Immutable53 server/frontend distribution mismatch')
    original = hashes(); dll = hashlib.sha256(args.dll.read_bytes()).hexdigest()
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(), 'dllSha256': dll,
        'sourceHashes': original, 'actualQaOpened': False, 'selectedCases': names,
        'frontendSha256': immutable['frontend']['app.js'], 'baselineDllSha256': immutable['server']['RackClick.Server.dll'],
        'capturedActions': ['user.create', 'user.create.cancel', 'user.state.set', 'user.state.set.cancel'],
        'schemaVersion': 6, 'regression': 'Creation pair point checks only, no old suite groups.'}
    lab = Lab('audit-state-context54')
    AuditStateContextPostgres.dll, AuditStateContextPostgres.frontend, AuditStateContextPostgres.baseline_dll = args.dll, args.frontend, args.baseline_dll
    with lab, (args.evidence/'tests.log').open('w', encoding='utf-8') as output:
        AuditStateContextPostgres.lab = lab
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(
            unittest.TestSuite(AuditStateContextPostgres(name) for name in names))
        report.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    report.update(labStopped=not lab.running, serversStopped=all(server.process.poll() is not None for server in lab.servers),
        inputsUnchanged=original == hashes() and dll == hashlib.sha256(args.dll.read_bytes()).hexdigest(),
        immutable53Unchanged=immutable == {'server': distribution(args.baseline_dll.parent, BASELINE['distributions']['server']),
                                         'frontend': distribution(args.frontend, BASELINE['distributions']['frontend'])})
    (args.evidence/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return 0 if all(report[key] for key in ('successful', 'labStopped', 'serversStopped', 'inputsUnchanged', 'immutable53Unchanged')) else 1


if __name__ == '__main__':
    sys.exit(main())
