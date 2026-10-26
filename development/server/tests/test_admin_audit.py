"""Four isolated Windows/PostgreSQL groups for the administrative audit reader."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import unittest
import uuid

from pg_support import Client, DEFAULT_DLL, Lab, WORKSPACE
from test_postgres import EvidenceResult, Tee
from test_admin_effective_permissions import EffectivePermissionsPostgres


class AuditPostgres(EffectivePermissionsPostgres):
    def audit(self, query='', client=None):
        before = self.durable()
        response = (client or self.admin).request('GET', '/api/v1/admin/audit' + query)
        self.assertEqual(before, self.durable(), 'Audit GET changed a public database row')
        return response

    def test_audit_authorization_validation_isolation(self):
        self.initialize()
        self.assertEqual(self.expect(self.audit(), 200).json(),
                         {'revision': 1, 'events': [], 'nextBeforeId': None})
        customer = self.customer('Own synthetic')
        user, scoped = self.add_user('scoped-audit')
        group = self.user_group(user, 'Scoped audit')
        self.grant(group, 'security.manage', customer=customer['id'])
        self.expect(self.audit('?limit=bad&beforeId=bad', scoped), 403, 'forbidden')
        cg = self.customer_group()
        self.grant(group, 'security.manage', customer_group=cg)
        self.expect(self.audit('', scoped), 403, 'forbidden')
        self.expect(self.audit('?limit=bad', Client(self.server)), 401, 'authentication_required')
        foreign_user, _, _ = self.foreign()
        foreign_event = str(uuid.uuid4())
        self.lab.sql(self.db, f"""INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,after_json)
            SELECT '{foreign_event}',systemhaus_id,id,'{uuid.uuid4()}','foreign.synthetic','{uuid.uuid4()}','{{}}'
            FROM app_user WHERE id='{foreign_user}'""")
        self.assertEqual(len(self.expect(self.audit(), 200).json()['events']), 1)
        for cursor in (foreign_event, str(uuid.uuid4())):
            self.expect(self.audit('?beforeId=' + cursor), 404, 'not_found')
        invalid = ['?limit=', '?limit=0', '?limit=101', '?limit=-1', '?limit=%2B1', '?limit=%201',
                   '?limit=1.0', '?limit=999999999999999999999', '?limit=1&limit=1', '?limit=%D9%A1',
                   '?beforeId=', '?beforeId=bad', '?beforeId=' + str(uuid.UUID(int=0)),
                   '?beforeId=' + foreign_event + '&beforeId=' + foreign_event]
        for query in invalid:
            with self.subTest(query=query):
                self.expect(self.audit(query), 422, 'request_invalid')
        temporary, session = self.add_user('temporary-audit-admin')
        temporary_group = self.user_group(temporary, 'Temporary audit authority')
        grant = self.set_grant(temporary_group, 'security.manage')
        self.expect(self.audit('', session), 200)
        self.set_grant(temporary_group, 'security.manage', assigned=False, grant=grant)
        self.expect(self.audit('?beforeId=bad', session), 403, 'forbidden')
        self.expect(session.request('GET', '/api/v1/me'), 200)
        self.lab.sql(self.db, f"UPDATE app_session SET expires_at=clock_timestamp()-interval '1 second' WHERE user_id='{self.admin_id}'")
        self.expect(self.audit(), 401, 'authentication_required')

    def test_audit_pagination_metadata_and_openapi(self):
        self.initialize('admin-ä-😀')
        marker = 'synthetic-payload-must-stay-private'
        ids = [str(uuid.uuid4()) for _ in range(104)]
        values = ','.join(f"('{event}','{self.house}','{self.admin_id}','{uuid.uuid4()}',"
            f"'synthetic.audit','{uuid.uuid4()}','{{\"password\":\"{marker}\"}}',"
            f"'{{\"data\":{{\"token\":\"{marker}\"}},\"extra\":\"{marker}\"}}','2026-01-01T12:34:56.123456Z')" for event in ids)
        self.lab.sql(self.db, 'INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json,occurred_at) VALUES ' + values)
        expected = self.lab.sql(self.db, 'SELECT id FROM audit_event ORDER BY occurred_at DESC,id DESC').splitlines()
        seen = []
        query = ''
        page_sizes = []
        while True:
            response = self.expect(self.audit(query), 200)
            page = response.json()
            self.assertEqual(set(page), {'revision', 'events', 'nextBeforeId'})
            self.assertEqual(response.headers['etag'], f'"{page["revision"]}"')
            self.assertEqual(page['revision'], self.house_revision())
            page_sizes.append(len(page['events']))
            for event in page['events']:
                self.assertEqual(set(event), {'id', 'occurredAt', 'actor', 'requestId', 'action', 'resourceId'})
                self.assertEqual(event['actor'], {'id': self.admin_id, 'userName': 'admin-ä-😀'})
                self.assertEqual(event['action'], 'synthetic.audit')
                self.assertEqual(datetime.fromisoformat(event['occurredAt'].replace('Z', '+00:00')),
                                 datetime(2026, 1, 1, 12, 34, 56, 123456, tzinfo=timezone.utc))
                seen.append(event['id'])
            self.assertNotIn(marker, response.body.decode())
            if page['nextBeforeId'] is None:
                break
            self.assertEqual(page['nextBeforeId'], page['events'][-1]['id'])
            query = '?beforeId=' + page['nextBeforeId']
        self.assertEqual(page_sizes, [50, 50, 4])
        self.assertEqual(seen, expected)
        self.assertEqual(len(set(seen)), 104)
        self.assertEqual(len(self.expect(self.audit('?limit=100'), 200).json()['events']), 100)
        end = self.expect(self.audit('?limit=1&beforeId=' + expected[-1]), 200).json()
        self.assertEqual(end['events'], [])
        self.assertIsNone(end['nextBeforeId'])
        # Newer commits do not duplicate already-paged rows; refresh starts at new head.
        self.customer('New head')
        newest = self.expect(self.audit('?limit=1'), 200).json()['events'][0]
        self.assertEqual(newest['action'], 'customer.create')
        old_tail = self.expect(self.audit('?beforeId=' + expected[49]), 200).json()
        self.assertEqual([r['id'] for r in old_tail['events']], expected[50:100])
        # GET needs a current cookie, not mutation CSRF.
        self.admin.csrf = None
        self.expect(self.audit(), 200)
        doc = self.expect(self.admin.request('GET', '/api/v1/openapi.json'), 200).json()
        operation = doc['paths']['/api/v1/admin/audit']['get']
        self.assertEqual(operation['operationId'], 'readAdminAudit')
        self.assertTrue({'200', '401', '403', '404', '422'} <= set(operation['responses']))
        self.assertIn('ETag', operation['responses']['200']['headers'])
        self.assertEqual({p['name'] for p in operation['parameters']}, {'limit', 'beforeId', 'actorId', 'resourceId'})
        schemas = doc['components']['schemas']
        for schema, fields in [('AdminAuditSnapshot', {'revision', 'events', 'nextBeforeId'}),
                               ('AdminAuditEvent', set(newest)), ('AuditActor', {'id', 'userName'})]:
            self.assertEqual(set(schemas[schema]['required']), fields)
            self.assertEqual(set(schemas[schema]['properties']), fields)
        public = json.dumps(self.expect(self.audit(), 200).json())
        secrets = self.lab.sql(self.db, 'SELECT password_hash FROM app_user UNION ALL SELECT token_hash FROM app_session UNION ALL SELECT csrf_hash FROM app_session').splitlines()
        self.assertTrue(all(s not in public for s in secrets), 'Identity secrets leaked into public audit DTO')

    def test_audit_commits_replay_rollback_persistence(self):
        self.initialize()
        key = str(uuid.uuid4())
        revision = self.house_revision()
        made = self.expect(self.mutate(self.admin, 'POST', '/api/v1/customers', 'Committed', revision, key), 201).json()
        original = self.expect(self.audit(), 200).json()
        self.assertEqual(len(original['events']), 1)
        event = original['events'][0]
        self.assertEqual((event['requestId'], event['resourceId'], event['action']), (key, made['resource']['id'], 'customer.create'))
        self.expect(self.mutate(self.admin, 'POST', '/api/v1/customers', 'Committed', revision, key), 201)
        self.expect(self.mutate(self.admin, 'POST', '/api/v1/customers', 'Stale', revision), 412, 'revision_conflict')
        self.assertEqual(self.expect(self.audit(), 200).json(), original)
        self.lab.sql(self.db, """CREATE FUNCTION synthetic_fail_operation38() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'synthetic operation failure'; END; $$;
            CREATE TRIGGER synthetic_fail38 BEFORE INSERT ON operation FOR EACH ROW EXECUTE FUNCTION synthetic_fail_operation38();""")
        durable = self.durable()
        self.expect(self.mutate(self.admin, 'POST', '/api/v1/customers', 'Must rollback', self.house_revision()), 503)
        self.assertEqual(durable, self.durable(), 'Failed operation must roll back audit and data together')
        self.assertEqual(self.expect(self.audit(), 200).json(), original)
        self.lab.sql(self.db, 'DROP TRIGGER synthetic_fail38 ON operation; DROP FUNCTION synthetic_fail_operation38()')
        second = Client(self.server)
        self.expect(second.login('qa-admin', self.password), 200)
        self.assertEqual(self.expect(self.audit('', second), 200).json(), original)
        self.server.close()
        self.server = self.lab.start_server(self.db)
        self.admin.server = self.server
        second.server = self.server
        self.assertEqual(self.expect(self.audit('', second), 200).json(), original)

    def test_audit_actor_expiry_after_wait(self):
        self.initialize()
        self.expired_wait(lambda: self.admin.request('GET', '/api/v1/admin/audit'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(AuditPostgres) if n.startswith('test_audit_')]
    if args.case:
        if set(args.case) - set(names):
            raise ValueError('Unknown audit case')
        names = [n for n in names if n in args.case]
    args.evidence.mkdir(parents=True, exist_ok=False)
    paths = [WORKSPACE/'development/server/src/RackClick.Server'/name for name in
             ('AdminAudit.cs', 'OpenApiAudit.cs', 'OpenApiAdmin.cs', 'Program.cs', 'AdminUsers.cs', 'PostgresStore.cs')]
    paths += [Path(__file__).resolve(), WORKSPACE/'development/server/tests/pg_support.py',
              WORKSPACE/'development/server/tests/test_admin_effective_permissions.py']
    def hashes():
        return {str(p.relative_to(WORKSPACE)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    original = hashes()
    dllhash = hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()
    data = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
            'dllSha256': dllhash, 'sourceHashes': original, 'actualQaOpened': False, 'globalPointerChanged': False}
    lab = Lab('admin-audit38')
    with lab, (args.evidence/'tests.log').open('w', encoding='utf-8') as output:
        AuditPostgres.lab = lab
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(
            unittest.TestSuite(AuditPostgres(n) for n in names))
        data.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    data.update(labStopped=not lab.running, serversStopped=all(s.process.poll() is not None for s in lab.servers),
                inputsUnchanged=original == hashes() and dllhash == hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest())
    (args.evidence/'result.json').write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
    return 0 if result.wasSuccessful() and data['labStopped'] and data['serversStopped'] and data['inputsUnchanged'] else 1


if __name__ == '__main__':
    sys.exit(main())
