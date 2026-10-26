"""Audit context52: isolated Windows/PostgreSQL schema5, two HTTP writers only; never live QA."""
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

from pg_support import Client, DEFAULT_DLL, Lab, NO_WINDOW, SERVER_ROOT, WORKSPACE
from test_postgres import EvidenceResult, Tee
from test_admin_audit_administration import AdministrativeAuditPostgres, field

BASELINE_INFO = WORKSPACE/'evidence/s1-20261017/tres-tandas-52/BASELINE.json'
BASELINE = json.loads(BASELINE_INFO.read_text(encoding='utf-8'))
BASELINE_DLL = WORKSPACE/BASELINE['serverDll']


def uid():
    return str(uuid.uuid4())


class AuditContextPostgres(AdministrativeAuditPostgres):
    def context(self, event, client=None):
        before = self.durable()
        response = (client or self.admin).request('GET', f'/api/v1/admin/audit/{event}/context')
        self.assertEqual(before, self.durable(), 'Context GET changed a public row')
        return response

    def expected(self, resource, before, cancel=False):
        return {'status': 'available', 'captureVersion': 1, 'actorId': self.admin_id,
            'scopeKind': 'systemhaus', 'scopeId': self.house, 'customerId': None,
            'revisionScope': 'systemhaus', 'revisionBefore': before,
            'revisionAfter': before if cancel else before + 1, 'outcome': 'cancelled' if cancel else 'committed',
            'objects': [{'kind': 'systemhaus' if cancel else 'user', 'id': resource,
                         'relation': 'intendedTarget' if cancel else 'target'}]}

    def not_recorded(self):
        return dict.fromkeys(('captureVersion', 'actorId', 'scopeKind', 'scopeId', 'customerId',
            'revisionScope', 'revisionBefore', 'revisionAfter', 'outcome')) | {'status': 'notRecorded', 'objects': []}

    def read(self, event, expected, client=None):
        response = self.expect(self.context(event, client), 200)
        data = response.json()
        self.assertEqual(set(data), {'revision', 'event', 'context'})
        self.assertEqual(data['revision'], self.house_revision())
        self.assertEqual(response.headers['etag'], f'"{data["revision"]}"')
        self.assertEqual(data['context'], expected)
        return data

    def migrate(self, database=None):
        database = database or self.db
        env = self.lab.environment(); env['ConnectionStrings__RackClick'] = database.connection(self.lab.port, runtime=False)
        result = subprocess.run([str(self.lab.dotnet), str(DEFAULT_DLL), '--migrate'], cwd=SERVER_ROOT,
            env=env, capture_output=True, text=True, encoding='utf-8', timeout=60, creationflags=NO_WINDOW)
        (database.directory/f'migrate-{uuid.uuid4().hex[:8]}.log').write_text(result.stdout + result.stderr, encoding='utf-8')
        return result

    def table_digest(self, database, tables=None):
        if tables is None:
            tables = self.lab.sql(database, "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename<>'schema_migration' ORDER BY tablename").splitlines()
        statements = [f"SELECT md5(COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)::text,'')) FROM public.\"{table}\" t" for table in tables]
        return tables, hashlib.sha256(self.lab.sql(database, ' UNION ALL '.join(statements)).encode()).hexdigest()

    def test_context_migration_four_five_repeat_one_five_failure_and_recovery(self):
        self.assertEqual(hashlib.sha256(BASELINE_DLL.read_bytes()).hexdigest(), BASELINE['serverSha256'])
        self.assertEqual(self.lab.bootstrap(self.db, 'qa-admin', self.password, dll=BASELINE_DLL).returncode, 0)
        self.lab.grant_runtime(self.db)
        self.server = self.lab.start_server(self.db, dll=BASELINE_DLL)
        self.admin = Client(self.server); self.expect(self.admin.login('qa-admin', self.password), 200)
        self.house = self.lab.sql(self.db, 'SELECT id FROM systemhaus')
        self.admin_id = self.lab.sql(self.db, 'SELECT id FROM app_user')
        key, made = self.write('/api/v1/admin/users', {'username': 'pre-context52', 'password': self.password}, status=201)
        event = self.event_for(key)
        second = Client(self.server); self.expect(second.login('qa-admin', self.password), 200)
        old_tables, old_digest = self.table_digest(self.db)
        history = self.lab.sql(self.db, 'SELECT row_to_json(t) FROM schema_migration t ORDER BY version')
        self.assertEqual(self.lab.sql(self.db, 'SELECT max(version) FROM schema_migration'), '4')
        self.server.close()
        # Copy/restore is solely within this new lab; the immutable50 distribution is read only.
        backup = self.db.directory/'before-context52.dump'
        env = self.lab.environment(); env['PGPASSFILE'] = str(self.db.directory/'owner.pgpass')
        dump = subprocess.run([str(self.lab.pg_bin/'pg_dump.exe'), '-h', '127.0.0.1', '-p', str(self.lab.port),
            '-U', self.db.owner, '-d', self.db.name, '-Fc', '-f', str(backup), '-w'], env=env,
            capture_output=True, timeout=60, creationflags=NO_WINDOW)
        self.assertEqual(dump.returncode, 0, 'Private lab backup failed')
        self.assertEqual(self.migrate().returncode, 0)
        self.assertEqual(self.table_digest(self.db, old_tables)[1], old_digest)
        self.assertEqual(history, self.lab.sql(self.db, 'SELECT row_to_json(t) FROM schema_migration t WHERE version<=4 ORDER BY version'))
        self.assertEqual(self.lab.sql(self.db, 'SELECT max(version) FROM schema_migration; SELECT count(*) FROM audit_context; SELECT count(*) FROM audit_context_object'), '5\n0\n0')
        history5 = self.lab.sql(self.db, 'SELECT row_to_json(t) FROM schema_migration t ORDER BY version')
        self.assertEqual(self.migrate().returncode, 0)
        self.assertEqual(history5, self.lab.sql(self.db, 'SELECT row_to_json(t) FROM schema_migration t ORDER BY version'))
        self.assertEqual(self.table_digest(self.db, old_tables)[1], old_digest)
        self.lab.grant_runtime(self.db); self.server = self.lab.start_server(self.db)
        self.admin.server = second.server = self.server
        for client in (self.admin, second):
            self.expect(client.request('GET', '/api/v1/me'), 200)
            self.read(event, self.not_recorded(), client)
        # Replaying a pre005 command must not invent context for an old committed event.
        before = self.durable()
        self.write('/api/v1/admin/users', {'username': 'pre-context52', 'password': self.password}, key=key, revision=1, status=201)
        self.assertEqual(before, self.durable()); self.read(event, self.not_recorded())
        restored = self.lab.create_database('recovered-schema4-new-target')
        restore_env = self.lab.environment(); restore_env['PGPASSFILE'] = str(restored.directory/'owner.pgpass')
        restore = subprocess.run([str(self.lab.pg_bin/'pg_restore.exe'), '-h', '127.0.0.1', '-p', str(self.lab.port),
            '-U', restored.owner, '-d', restored.name, '--no-owner', '--no-privileges', '-w', str(backup)],
            env=restore_env, capture_output=True, timeout=60, creationflags=NO_WINDOW)
        self.assertEqual(restore.returncode, 0, 'Private new-target restore failed')
        self.assertEqual(self.table_digest(restored, old_tables)[1], old_digest)
        self.assertEqual(self.lab.sql(restored, 'SELECT max(version) FROM schema_migration'), '4')
        self.lab.grant_runtime(restored)
        restored_server = self.lab.start_server(restored, dll=BASELINE_DLL)
        self.expect(restored_server.request('GET', '/health/ready'), 200)
        restored_client = Client(restored_server); self.expect(restored_client.login('qa-admin', self.password), 200)
        self.expect(restored_client.request('GET', '/api/v1/admin/audit/' + event + '/administrative-detail'), 200)
        restored_server.close()
        # A collision on the second table must roll back the first table and migration history.
        failed = self.lab.create_database('migration-five-collision')
        self.assertEqual(self.lab.bootstrap(failed, 'qa-admin', self.password, dll=BASELINE_DLL).returncode, 0)
        self.lab.sql(failed, 'CREATE TABLE audit_context_object(synthetic boolean)')
        tables, before = self.table_digest(failed)
        self.assertNotEqual(self.migrate(failed).returncode, 0)
        self.assertEqual(before, self.table_digest(failed, tables)[1])
        self.assertEqual(self.lab.sql(failed, "SELECT max(version) FROM schema_migration; SELECT to_regclass('public.audit_context') IS NULL"), '4\nt')
        self.lab.sql(failed, 'DROP TABLE audit_context_object')
        self.assertEqual(self.migrate(failed).returncode, 0)
        # Start explicitly from schema1 with its exact recorded digest, then apply2..5.
        one = self.lab.create_database('schema-one-through-five')
        source = WORKSPACE/'development/server/database/001-foundation.sql'
        text = source.read_bytes().decode('utf-8-sig')
        self.lab.sql(one, text)
        digest = hashlib.sha256(text.encode()).hexdigest().upper()
        self.lab.sql(one, f"INSERT INTO schema_migration(version,digest) VALUES(1,'{digest}')")
        self.assertEqual(self.migrate(one).returncode, 0)
        self.assertEqual(self.lab.sql(one, "SELECT string_agg(version::text,',' ORDER BY version) FROM schema_migration"), '1,2,3,4,5')
        fresh = self.lab.create_database('fresh-schema-five')
        self.assertEqual(self.lab.bootstrap(fresh, 'qa-admin', self.password).returncode, 0)
        self.assertEqual(self.lab.sql(fresh, 'SELECT max(version) FROM schema_migration'), '5')

    def test_context_create_cancel_replay_conflict_persistence(self):
        self.initialize()
        name = 'contexto-e\u0301-ä-😀'
        key, made = self.write('/api/v1/admin/users', {'username': name, 'password': self.password}, revision=1, status=201)
        event = self.event_for(key); user = made['resource']['id']
        expected = self.expected(user, 1)
        original = self.read(event, expected)
        cancelled, cancelled_result = self.write('/api/v1/admin/users', {'username': 'cancel-context52'}, cancel=True, revision=1)
        cancelled_event = self.event_for(cancelled)
        self.read(cancelled_event, self.expected(self.house, 2, cancel=True))
        before = self.durable()
        self.write('/api/v1/admin/users', {'username': name, 'password': self.password}, key=key, revision=1, status=201)
        _, outcome = self.write('/api/v1/admin/users', {'username': name}, cancel=True, key=key, revision=1)
        self.assertEqual(outcome, {'requestId': key, 'state': 'committed', 'operation': made})
        _, repeated_cancel = self.write('/api/v1/admin/users', {'username': 'cancel-context52'}, cancel=True, key=cancelled, revision=1)
        self.assertEqual(repeated_cancel, cancelled_result)
        self.write('/api/v1/admin/users', {'username': 'changed-context52', 'password': self.password}, key=key, revision=1, status=409)
        self.write('/api/v1/admin/users', {'username': 'cancel-context52', 'password': self.password}, key=cancelled, revision=1, status=409)
        self.write('/api/v1/admin/users', {'username': 'stale-context52', 'password': self.password}, revision=1, status=412)
        self.assertEqual(before, self.durable())
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM audit_context; SELECT count(*) FROM audit_context_object'), '2\n2')
        second = Client(self.server); self.expect(second.login('qa-admin', self.password), 200)
        self.assertEqual(self.read(event, expected, second), original)
        self.server.close(); self.server = self.lab.start_server(self.db)
        self.admin.server = second.server = self.server
        self.assertEqual(self.read(event, expected, second), original)
        self.read(cancelled_event, self.expected(self.house, 2, cancel=True), second)

    def test_context_atomic_rollback_context_and_object(self):
        self.initialize()
        for table in ('audit_context', 'audit_context_object'):
            for cancel in (False, True):
                key, name = uid(), f'rollback-{table}-{cancel}'
                self.lab.sql(self.db, f"""CREATE FUNCTION fail_context52() RETURNS trigger LANGUAGE plpgsql AS $$
                    BEGIN RAISE EXCEPTION 'synthetic context failure52'; END; $$;
                    CREATE TRIGGER fail_context52 BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION fail_context52();""")
                before = self.durable(); revision = self.house_revision()
                body = {'username': name} if cancel else {'username': name, 'password': self.password}
                self.write('/api/v1/admin/users', body, cancel=cancel, key=key, revision=revision, status=503)
                self.assertEqual(before, self.durable(), 'Context failure must roll back every public table')
                self.lab.sql(self.db, f'DROP TRIGGER fail_context52 ON {table}; DROP FUNCTION fail_context52()')
                _, result = self.write('/api/v1/admin/users', body, cancel=cancel, key=key, revision=revision, status=200 if cancel else 201)
                resource = self.house if cancel else result['resource']['id']
                self.read(self.event_for(key), self.expected(resource, revision, cancel))
                self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM audit_event WHERE request_id='{key}'; SELECT count(*) FROM operation WHERE request_id='{key}'"), '1\n1')

    def test_context_authority_house_uuid_expiry_readonly(self):
        self.initialize()
        key, _ = self.write('/api/v1/admin/users', {'username': 'scope-context52', 'password': self.password}, status=201)
        event = self.event_for(key)
        customer = self.customer('Scope context52')
        user, scoped = self.add_user('scoped-context52'); group = self.user_group(user)
        self.grant(group, 'security.manage', customer=customer['id'])
        cg = self.customer_group(); self.grant(group, 'security.manage', customer_group=cg)
        for event_id in ('bad', event, uid()):
            self.expect(self.context(event_id, Client(self.server)), 401, 'authentication_required')
            self.expect(self.context(event_id, scoped), 403, 'forbidden')
        for event_id in ('bad', str(uuid.UUID(int=0)), event.replace('-', ''), '%20' + event, event + '%20', '%7B' + event + '%7D'):
            self.expect(self.context(event_id), 422, 'request_invalid')
        self.expect(self.context(event.upper()), 200)
        foreign, _, _ = self.foreign(); foreign_event = uid()
        self.lab.sql(self.db, f"""INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,after_json)
            SELECT '{foreign_event}',systemhaus_id,id,'{uid()}','user.create','{uid()}','{{}}' FROM app_user WHERE id='{foreign}'""")
        missing = self.expect(self.context(uid()), 404, 'not_found')
        self.assertEqual(missing.json(), self.expect(self.context(foreign_event), 404, 'not_found').json())
        current_csrf = self.admin.csrf; self.admin.csrf = None
        self.expect(self.context(event), 200); self.admin.csrf = current_csrf
        temporary, client = self.add_user('temporary-context52'); group = self.user_group(temporary)
        grant = self.set_grant(group, 'security.manage'); self.expect(self.context(event, client), 200)
        self.set_grant(group, 'security.manage', assigned=False, grant=grant)
        self.expect(self.context('bad', client), 403, 'forbidden')
        self.expired_wait(lambda: self.admin.request('GET', f'/api/v1/admin/audit/{event}/context'))

    def test_context_coherence_redaction_and_point_regression46_50(self):
        self.initialize()
        key, made = self.write('/api/v1/admin/users', {'username': 'typed-context52', 'password': self.password}, status=201)
        event = self.event_for(key); user = made['resource']['id']; expected = self.expected(user, 1)
        self.read(event, expected)
        # Regression is a point check of46 and50, not their full existing test groups.
        self.assert_fields(event, 'user.create', [field('userId', 'uuid', None, user),
            field('userName', 'userName', None, 'typed-context52'), field('active', 'boolean', None, 'true')])
        customer = self.customer('Name regression e\u0301 😀')
        customer_event = self.lab.sql(self.db, "SELECT id FROM audit_event WHERE action='customer.create'")
        names = self.expect(self.admin.request('GET', '/api/v1/admin/audit/' + customer_event), 200).json()
        self.assertEqual(names['detail'], {'status': 'available', 'revisionScope': 'customer', 'customerId': customer['id'],
            'before': None, 'after': {'name': customer['name'], 'revision': 1}})
        self.read(customer_event, self.not_recorded())
        self.read(event, expected)  # Historical1->2 remains, envelope revision is now3.
        # Simulate future/incoherent capture without bypassing any schema constraints.
        self.lab.sql(self.db, f"UPDATE audit_context_object SET object_id='{uid()}' WHERE event_id='{event}'")
        self.read(event, self.not_recorded())
        self.lab.sql(self.db, f"UPDATE audit_context_object SET object_id='{user}',position=2 WHERE event_id='{event}'")
        self.read(event, self.not_recorded())
        self.lab.sql(self.db, f"UPDATE audit_context_object SET position=1 WHERE event_id='{event}'; INSERT INTO audit_context_object VALUES('{event}',2,'user','{uid()}','target')")
        self.read(event, self.not_recorded())
        self.lab.sql(self.db, f"DELETE FROM audit_context_object WHERE event_id='{event}' AND position=2; UPDATE audit_context SET outcome='cancelled',revision_after=revision_before WHERE event_id='{event}'")
        self.read(event, self.not_recorded())
        self.lab.sql(self.db, f"UPDATE audit_context SET outcome='committed',revision_after=revision_before+1 WHERE event_id='{event}'")
        self.read(event, expected)
        # Constraints each operate on an event with NO existing context, avoiding a PK rejection mask.
        empty_event = self.insert_event('synthetic-context52', uid(), None, {})
        columns = {'capture_version': '1', 'scope_kind': "'systemhaus'", 'revision_scope': "'systemhaus'",
                   'revision_before': '1', 'revision_after': '2', 'outcome': "'committed'"}
        invalid = [('capture_version', '2'), ('scope_kind', "'customer'"), ('revision_scope', "'customer'"),
            ('revision_before', '0'), ('revision_after', '3'), ('outcome', "'unknown'")]
        for column, value in invalid:
            candidate = columns | {column: value}
            with self.assertRaises(RuntimeError):
                self.lab.sql(self.db, f"INSERT INTO audit_context(event_id,{','.join(candidate)}) VALUES('{empty_event}',{','.join(candidate.values())})")
            self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM audit_context WHERE event_id='{empty_event}'"), '0')
        marker = 'synthetic-context52-private'
        self.lab.sql(self.db, f"UPDATE audit_event SET after_json=after_json||jsonb_build_object('password','{marker}','requestHash','{marker}','token','{marker}') WHERE id='{event}'; UPDATE app_user SET username='current-actor52' WHERE id='{self.admin_id}'")
        data = self.read(event, expected)
        self.assertEqual(data['event']['actor']['userName'], 'current-actor52')
        public = json.dumps(data)
        self.assertNotIn(marker, public); self.assertNotIn(self.password, public)
        raw_secrets = self.lab.sql(self.db, 'SELECT password_hash FROM app_user UNION ALL SELECT token_hash FROM app_session UNION ALL SELECT csrf_hash FROM app_session').splitlines()
        self.assertTrue(all(secret not in public for secret in raw_secrets), 'Identity secret leaked')
        doc = self.expect(self.admin.request('GET', '/api/v1/openapi.json'), 200).json()
        operation = doc['paths']['/api/v1/admin/audit/{eventId}/context']['get']
        self.assertEqual(operation['operationId'], 'readAdminAuditContext')
        self.assertTrue({'200', '401', '403', '404', '422'} <= set(operation['responses']))
        self.assertIn('ETag', operation['responses']['200']['headers'])
        schema = doc['components']['schemas']['AdminAuditContext']
        self.assertEqual(set(schema['required']), set(expected))
        self.assertEqual(set(schema['properties']), set(expected))
        for old in ('/api/v1/admin/audit/{eventId}', '/api/v1/admin/audit/{eventId}/administrative-detail'):
            self.assertIn(old, doc['paths'])


def main():
    global BASELINE_DLL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--case', action='append')
    parser.add_argument('--baseline-dll', type=Path,
        help='Explicit immutable50 DLL; its complete distribution must match BASELINE.json hashes.')
    args = parser.parse_args()
    if args.baseline_dll:
        BASELINE_DLL = args.baseline_dll.resolve()
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(AuditContextPostgres) if n.startswith('test_context_')]
    if args.case:
        if set(args.case) - set(names): raise ValueError('Unknown context test')
        names = [n for n in names if n in args.case]
    args.evidence.mkdir(parents=True, exist_ok=False)
    files = [WORKSPACE/'development/server/src/RackClick.Server'/name for name in
             ('AdminAuditContext.cs', 'SchemaMigrations.cs', 'AdminUsers.cs', 'Program.cs', 'OpenApiAudit.cs',
              'AdminAuditDetail.cs', 'AdminAuditAdministrativeDetail.cs')]
    files += list((WORKSPACE/'development/server/database').glob('*.sql')) + [Path(__file__).resolve(),
              WORKSPACE/'development/server/tests/pg_support.py', WORKSPACE/'development/server/tests/test_admin_audit_administration.py']
    def hashes():
        return {p.relative_to(WORKSPACE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    def baseline_hashes():
        base = BASELINE_DLL.parent
        return {name: hashlib.sha256((base/name).read_bytes()).hexdigest() for name in BASELINE['distributions']['server']}
    original = hashes(); dll = hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()
    immutable = baseline_hashes()
    if immutable != BASELINE['distributions']['server']: raise RuntimeError('Immutable50 distribution does not match baseline')
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(), 'dllSha256': dll,
              'sourceHashes': original, 'baselineDllSha256': BASELINE['serverSha256'], 'actualQaOpened': False,
              'selectedCases': names, 'newCapturedActions': ['user.create', 'user.create.cancel'],
              'regression': 'Only point checks46/50 inside selected coherence case; no full previous groups.'}
    lab = Lab('audit-context52')
    with lab, (args.evidence/'tests.log').open('w', encoding='utf-8') as output:
        AuditContextPostgres.lab = lab
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(
            unittest.TestSuite(AuditContextPostgres(n) for n in names))
        report.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    report.update(labStopped=not lab.running, serversStopped=all(s.process.poll() is not None for s in lab.servers),
                  inputsUnchanged=original == hashes() and dll == hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest(),
                  immutable50Unchanged=immutable == baseline_hashes())
    (args.evidence/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return 0 if all(report[key] for key in ('successful', 'labStopped', 'serversStopped', 'inputsUnchanged', 'immutable50Unchanged')) else 1


if __name__ == '__main__':
    sys.exit(main())
