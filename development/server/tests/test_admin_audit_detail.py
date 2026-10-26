"""Typed historical audit detail on new native PostgreSQL labs only; no Wascar QA."""
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
from test_admin_audit import AuditPostgres


class AuditDetailPostgres(AuditPostgres):
    def detail(self, event, client=None):
        before = self.durable()
        response = (client or self.admin).request('GET', '/api/v1/admin/audit/' + event)
        self.assertEqual(before, self.durable(), 'Detail GET changed a public table')
        return response

    def event_for(self, key):
        return self.lab.sql(self.db, f"SELECT id FROM audit_event WHERE request_id='{key}'")

    def insert_event(self, action, resource, before, after):
        event, key = str(uuid.uuid4()), str(uuid.uuid4())
        def text(value):
            return "'" + json.dumps(value, ensure_ascii=False).replace("'", "''") + "'::jsonb"
        self.lab.sql(self.db, f"""INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json)
            VALUES('{event}','{self.house}','{self.admin_id}','{key}','{action}','{resource}',{text(before)},{text(after)})""")
        return event

    def test_detail_authority_id_isolation_and_expiry(self):
        self.initialize()
        customer = self.customer('Synthetic detail authority')
        event = self.expect(self.audit(), 200).json()['events'][0]['id']
        user, scoped = self.add_user('scoped-detail')
        group = self.user_group(user)
        self.grant(group, 'security.manage', customer=customer['id'])
        cg = self.customer_group()
        self.grant(group, 'security.manage', customer_group=cg)
        for value in ('bad', event, str(uuid.uuid4())):
            self.expect(self.detail(value, scoped), 403, 'forbidden')
            self.expect(self.detail(value, Client(self.server)), 401, 'authentication_required')
        for value in ('bad', str(uuid.UUID(int=0)), event.replace('-', ''),
                      '%7B' + event + '%7D', '%20' + event, event + '%20'):
            self.expect(self.detail(value), 422, 'request_invalid')
        foreign, _, _ = self.foreign()
        foreign_event = str(uuid.uuid4())
        self.lab.sql(self.db, f"""INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,after_json)
            SELECT '{foreign_event}',systemhaus_id,id,'{uuid.uuid4()}','customer.create','{uuid.uuid4()}','{{}}'
            FROM app_user WHERE id='{foreign}'""")
        missing = self.expect(self.detail(str(uuid.uuid4())), 404, 'not_found')
        hidden = self.expect(self.detail(foreign_event), 404, 'not_found')
        self.assertEqual(missing.json(), hidden.json())
        self.expect(self.detail(event.upper()), 200)
        temporary, client = self.add_user('temporary-detail-admin')
        temporary_group = self.user_group(temporary)
        grant = self.set_grant(temporary_group, 'security.manage')
        self.expect(self.detail(event, client), 200)
        self.set_grant(temporary_group, 'security.manage', assigned=False, grant=grant)
        self.expect(self.detail('bad', client), 403, 'forbidden')
        self.expect(client.request('GET', '/api/v1/me'), 200)
        self.expired_wait(lambda: self.admin.request('GET', '/api/v1/admin/audit/' + event))

    def test_detail_typed_names_bounds_redaction_and_contract(self):
        self.initialize()
        name = 'Cliente e\u0301 <b>😀</b>'
        customer = self.customer(name)
        create_event = self.expect(self.audit(), 200).json()['events'][0]
        first = self.expect(self.detail(create_event['id']), 200)
        data = first.json()
        self.assertEqual(set(data), {'revision', 'event', 'detail'})
        self.assertEqual(data['event'], create_event)
        self.assertEqual(first.headers['etag'], f'"{data["revision"]}"')
        self.assertEqual(data['detail'], {'status': 'available', 'revisionScope': 'customer',
            'customerId': customer['id'], 'before': None, 'after': {'name': name, 'revision': 1}})
        key = str(uuid.uuid4())
        self.expect(self.mutate(self.admin, 'PUT', '/api/v1/customers/' + customer['id'], 'Cliente Ω', 1, key), 200)
        renamed = self.expect(self.detail(self.event_for(key)), 200).json()['detail']
        self.assertEqual(renamed['before'], {'name': name, 'revision': 1})
        self.assertEqual(renamed['after'], {'name': 'Cliente Ω', 'revision': 2})
        same = str(uuid.uuid4())
        self.expect(self.mutate(self.admin, 'PUT', '/api/v1/customers/' + customer['id'], 'Cliente Ω', 2, same), 200)
        no_name_delta = self.expect(self.detail(self.event_for(same)), 200).json()['detail']
        self.assertEqual(no_name_delta['status'], 'available')
        self.assertEqual((no_name_delta['before']['revision'], no_name_delta['after']['revision']), (2, 3))
        self.assertEqual(no_name_delta['before']['name'], no_name_delta['after']['name'])
        house = self.expect(self.admin.request('GET', '/api/v1/systemhaus'), 200).json()
        house_key = str(uuid.uuid4())
        self.expect(self.mutate(self.admin, 'PUT', '/api/v1/systemhaus', 'Systemhaus Ä 😀', house['revision'], house_key), 200)
        house_detail = self.expect(self.detail(self.event_for(house_key)), 200).json()['detail']
        self.assertEqual(house_detail, {'status': 'available', 'revisionScope': 'systemhaus', 'customerId': None,
            'before': {'name': house['name'], 'revision': house['revision']},
            'after': {'name': 'Systemhaus Ä 😀', 'revision': house['revision'] + 1}})
        marker = 'synthetic-detail-secret-never-project'
        resource = str(uuid.uuid4())  # No current customer row or operation needed.
        valid = {'id': resource, 'houseId': self.house, 'name': '历史 e\u0301 😀', 'revision': 1}
        extra = valid | {'password': marker, 'nested': {'token': marker}}
        safe_event = self.insert_event('customer.create', resource, None, extra)
        safe = self.expect(self.detail(safe_event), 200)
        self.assertEqual(safe.json()['detail']['after'], {'name': valid['name'], 'revision': 1})
        self.assertNotIn(marker, safe.body.decode())
        unavailable = {'status': 'unavailable', 'revisionScope': None, 'customerId': None, 'before': None, 'after': None}
        cases = [
            ('user.password.reset', None, extra),
            ('customer.create', {}, valid), ('customer.create', None, []),
            ('customer.create', None, valid | {'id': str(uuid.uuid4())}),
            ('customer.create', None, valid | {'houseId': str(uuid.uuid4())}),
            ('customer.create', None, valid | {'revision': '1'}),
            ('customer.create', None, valid | {'revision': 1.0}),
            ('customer.create', None, valid | {'revision': 0}),
            ('customer.create', None, valid | {'revision': 2}),
            ('customer.create', None, valid | {'revision': 9223372036854775808}),
            ('customer.create', None, valid | {'name': ''}),
            ('customer.create', None, valid | {'name': ' spaced '}),
            ('customer.create', None, valid | {'name': '😀' * 101}),
            ('customer.create', None, valid | {'extra': 'x' * 4097, 'token': marker}),
            ('customer.create', {'extra': 'x' * 4097}, valid),
            ('customer.create', None, valid | {'extra': [[[[[[[[[marker]]]]]]]]]}),
            ('customer.rename', valid, valid | {'revision': 3}),
            ('customer.rename', valid | {'revision': 9223372036854775807}, valid | {'revision': 9223372036854775807}),
            ('systemhaus.rename', valid, valid | {'revision': 2})]
        for action, before, after in cases:
            with self.subTest(action=action, index=cases.index((action, before, after))):
                event = self.insert_event(action, resource, before, after)
                response = self.expect(self.detail(event), 200)
                self.assertEqual(response.json()['detail'], unavailable)
                self.assertNotIn(marker, response.body.decode())
        zero = str(uuid.UUID(int=0))
        zero_event = self.insert_event('customer.create', zero, None, valid | {'id': zero})
        self.assertEqual(self.expect(self.detail(zero_event), 200).json()['detail'], unavailable)
        limit_event = self.insert_event('customer.create', resource, None, valid | {'name': '😀' * 100})
        self.assertEqual(self.expect(self.detail(limit_event), 200).json()['detail']['after']['name'], '😀' * 100)
        self.lab.sql(self.db, f"UPDATE app_user SET username='current-ä-<img>-😀' WHERE id='{self.admin_id}'")
        self.assertEqual(self.expect(self.detail(create_event['id']), 200).json()['event']['actor']['userName'], 'current-ä-<img>-😀')
        doc = self.expect(self.admin.request('GET', '/api/v1/openapi.json'), 200).json()
        operation = doc['paths']['/api/v1/admin/audit/{eventId}']['get']
        self.assertEqual(operation['operationId'], 'readAdminAuditDetail')
        self.assertTrue({'200', '401', '403', '404', '422'} <= set(operation['responses']))
        self.assertEqual(operation['parameters'][0]['name'], 'eventId')
        self.assertTrue(operation['parameters'][0]['required'])
        self.assertIn('ETag', operation['responses']['200']['headers'])
        for schema, fields in [('AdminAuditDetailSnapshot', set(data)), ('AdminAuditDetail', set(unavailable)), ('AuditNameState', {'name', 'revision'})]:
            shape = doc['components']['schemas'][schema]
            self.assertEqual(set(shape['properties']), fields)
            self.assertEqual(set(shape['required']), fields)
        secrets = self.lab.sql(self.db, 'SELECT password_hash FROM app_user UNION ALL SELECT token_hash FROM app_session UNION ALL SELECT csrf_hash FROM app_session').splitlines()
        public = safe.body.decode()
        self.assertTrue(all(secret not in public for secret in secrets), 'Identity secret appeared in detail')

    def test_detail_commits_replay_rollback_deleted_resource_restart(self):
        self.initialize()
        customer = self.customer('Original persisted name')
        key = str(uuid.uuid4())
        path = '/api/v1/customers/' + customer['id']
        self.expect(self.mutate(self.admin, 'PUT', path, 'Confirmed historical name', 1, key), 200)
        event = self.event_for(key)
        original = self.expect(self.detail(event), 200).json()
        self.expect(self.mutate(self.admin, 'PUT', path, 'Confirmed historical name', 1, key), 200)
        self.expect(self.mutate(self.admin, 'PUT', path, 'Stale intent', 1), 412, 'revision_conflict')
        self.assertEqual(self.expect(self.detail(event), 200).json(), original)
        self.assertEqual(len(self.expect(self.audit('?resourceId=' + customer['id']), 200).json()['events']), 2)
        self.lab.sql(self.db, """CREATE FUNCTION synthetic_fail_detail46() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'synthetic detail operation failure'; END; $$;
            CREATE TRIGGER synthetic_fail_detail46 BEFORE INSERT ON operation FOR EACH ROW EXECUTE FUNCTION synthetic_fail_detail46();""")
        before = self.durable()
        self.expect(self.mutate(self.admin, 'PUT', path, 'Must roll back', 2), 503)
        self.assertEqual(self.durable(), before)
        self.assertEqual(self.expect(self.detail(event), 200).json(), original)
        self.lab.sql(self.db, 'DROP TRIGGER synthetic_fail_detail46 ON operation; DROP FUNCTION synthetic_fail_detail46()')
        self.lab.sql(self.db, f"DELETE FROM customer WHERE id='{customer['id']}'")
        self.assertEqual(self.expect(self.detail(event), 200).json(), original)
        second = Client(self.server)
        self.expect(second.login('qa-admin', self.password), 200)
        second.csrf = None
        self.assertEqual(self.expect(self.detail(event, second), 200).json(), original)
        self.server.close()
        self.server = self.lab.start_server(self.db)
        second.server = self.server
        self.admin.server = self.server
        self.assertEqual(self.expect(self.detail(event, second), 200).json(), original)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--case', action='append')
    parser.add_argument('--include-regression', action='store_true')
    args = parser.parse_args()
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(AuditDetailPostgres) if n.startswith('test_detail_')]
    if args.case:
        if set(args.case) - set(names): raise ValueError('Unknown detail test')
        names = [n for n in names if n in args.case]
    args.evidence.mkdir(parents=True, exist_ok=False)
    files = [WORKSPACE/'development/server/src/RackClick.Server'/p for p in
             ('AdminAuditDetail.cs', 'AdminAudit.cs', 'OpenApiAudit.cs', 'Program.cs', 'AdminUsers.cs', 'PostgresStore.cs')]
    files += [Path(__file__).resolve(), WORKSPACE/'development/server/tests/test_admin_audit.py',
              WORKSPACE/'development/server/tests/pg_support.py', WORKSPACE/'development/server/tests/test_admin_effective_permissions.py',
              WORKSPACE/'development/server/tests/test_session_wait_expiry.py']
    hashes = lambda: {p.relative_to(WORKSPACE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original = hashes(); dll = hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(), 'dllSha256': dll,
              'sourceHashes': original, 'actualQaOpened': False, 'regressionIncluded': args.include_regression}
    lab = Lab('audit-detail46')
    with lab, (args.evidence/'tests.log').open('w', encoding='utf-8') as output:
        AuditDetailPostgres.lab = AuditPostgres.lab = lab
        tests = [AuditDetailPostgres(n) for n in names]
        if args.include_regression: tests.append(AuditPostgres('test_audit_pagination_metadata_and_openapi'))
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(tests))
        report.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    report.update(labStopped=not lab.running, serversStopped=all(s.process.poll() is not None for s in lab.servers),
                  inputsUnchanged=original == hashes() and dll == hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest())
    (args.evidence/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return 0 if report['successful'] and report['labStopped'] and report['serversStopped'] and report['inputsUnchanged'] else 1


if __name__ == '__main__':
    sys.exit(main())
