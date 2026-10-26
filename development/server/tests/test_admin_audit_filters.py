"""Three new native PostgreSQL groups, plus one optional updated-contract regression.

Creates independent laboratories only. Never selects, starts or authenticates Wascar QA.
"""
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


class AuditFilterPostgres(AuditPostgres):
    def test_filters_authority_and_input(self):
        self.initialize()
        customer = self.customer('Synthetic scoped customer')
        user, scoped = self.add_user('scoped-filter-reader')
        group = self.user_group(user)
        self.grant(group, 'security.manage', customer=customer['id'])
        cg = self.customer_group()
        self.grant(group, 'security.manage', customer_group=cg)
        bad = '?actorId=bad&resourceId=bad&beforeId=bad'
        self.expect(self.audit(bad, scoped), 403, 'forbidden')
        self.expect(self.audit(bad, Client(self.server)), 401, 'authentication_required')
        sample = str(uuid.uuid4())
        for name in ('actorId', 'resourceId'):
            for value in ('', 'bad', str(uuid.UUID(int=0)), sample.replace('-', ''),
                          '%7B' + sample + '%7D', '%20' + sample, sample + '%20',
                          '%0A' + sample, sample + '&' + name + '=' + sample):
                with self.subTest(name=name, value=value):
                    self.expect(self.audit('?' + name + '=' + value), 422, 'request_invalid')
        temporary, client = self.add_user('temporary-filter-admin')
        temporary_group = self.user_group(temporary)
        grant = self.set_grant(temporary_group, 'security.manage')
        self.expect(self.audit('?actorId=' + sample, client), 200)
        self.set_grant(temporary_group, 'security.manage', assigned=False, grant=grant)
        self.expect(self.audit(bad, client), 403, 'forbidden')
        self.expect(client.request('GET', '/api/v1/me'), 200)
        # Real actor-row wait: session expires before filters/cursor may be consulted.
        self.expired_wait(lambda: self.admin.request('GET', '/api/v1/admin/audit?actorId=' + sample + '&resourceId=' + sample))

    def test_filters_scope_combination_cursor_and_literal_metadata(self):
        self.initialize()
        other, _ = self.add_user('original-synthetic-actor')
        foreign, foreign_resource, _ = self.foreign()
        resources = [str(uuid.uuid4()), str(uuid.uuid4())]  # No live resource row required.
        marker = 'synthetic-filter-secret-must-not-leak'
        specification = [(108, self.admin_id, 1), (107, other, 0), (106, other, 0),
                         (105, other, 1), (104, self.admin_id, 0), (103, other, 0),
                         (102, self.admin_id, 1), (101, other, 0)]
        values = []
        for number, actor, resource in specification:
            values.append(f"('{uuid.UUID(int=number)}','{self.house}','{actor}','{uuid.uuid4()}',"
                          f"'synthetic.filter','{resources[resource]}','{{\"password\":\"{marker}\"}}',"
                          f"'{{\"nested\":{{\"token\":\"{marker}\"}}}}','2026-01-01T12:34:56.123456Z')")
        self.lab.sql(self.db, 'INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json,occurred_at) VALUES ' + ','.join(values))
        foreign_event = str(uuid.uuid4())
        self.lab.sql(self.db, f"""INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,after_json)
            SELECT '{foreign_event}',systemhaus_id,id,'{uuid.uuid4()}','foreign.filter','{resources[0]}','{{}}'
            FROM app_user WHERE id='{foreign}';
            UPDATE app_user SET username='current-ä-<img>-😀',active=false WHERE id='{other}';""")
        def ids(query):
            response = self.expect(self.audit(query), 200)
            self.assertNotIn(marker, response.body.decode())
            for event in response.json()['events']:
                self.assertEqual(set(event), {'id', 'occurredAt', 'actor', 'requestId', 'action', 'resourceId'})
                self.assertNotEqual(event['id'], foreign_event)
                if event['actor']['id'] == other:
                    self.assertEqual(event['actor']['userName'], 'current-ä-<img>-😀')
            return [e['id'] for e in response.json()['events']]
        event_ids = lambda numbers: [str(uuid.UUID(int=n)) for n in numbers]
        self.assertEqual(ids('?actorId=' + other.upper()), event_ids([107, 106, 105, 103, 101]))
        self.assertEqual(ids('?resourceId=' + resources[0].upper()), event_ids([107, 106, 104, 103, 101]))
        query = '?actorId=' + other + '&resourceId=' + resources[0]
        self.assertEqual(ids(query), event_ids([107, 106, 103, 101]))
        first = self.expect(self.audit(query + '&limit=2'), 200).json()
        self.assertEqual([e['id'] for e in first['events']], event_ids([107, 106]))
        self.assertEqual(first['nextBeforeId'], str(uuid.UUID(int=106)))
        last = self.expect(self.audit(query + '&limit=2&beforeId=' + first['nextBeforeId']), 200).json()
        self.assertEqual([e['id'] for e in last['events']], event_ids([103, 101]))
        self.assertIsNone(last['nextBeforeId'])
        # Cursor membership uses BOTH filters. No silently skipped page when filters change.
        for cursor in (str(uuid.UUID(int=105)), str(uuid.UUID(int=104)), foreign_event, str(uuid.uuid4())):
            self.expect(self.audit(query + '&beforeId=' + cursor), 404, 'not_found')
        for query in ('?actorId=' + foreign, '?actorId=' + str(uuid.uuid4()),
                      '?resourceId=' + foreign_resource, '?resourceId=' + str(uuid.uuid4()),
                      '?actorId=' + other + '&resourceId=' + str(uuid.uuid4())):
            response = self.expect(self.audit(query), 200)
            self.assertEqual(response.json(), {'revision': self.house_revision(), 'events': [], 'nextBeforeId': None})
        self.assertEqual(len(ids('')), 8)

    def test_filters_commit_replay_rollback_reload(self):
        self.initialize()
        first, second = self.customer('First synthetic resource'), self.customer('Other synthetic resource')
        path = '/api/v1/customers/' + first['id']
        key = str(uuid.uuid4())
        self.expect(self.mutate(self.admin, 'PUT', path, 'Confirmed rename', 1, key), 200)
        query = '?actorId=' + self.admin_id + '&resourceId=' + first['id']
        original = self.expect(self.audit(query), 200).json()
        self.assertEqual({e['action'] for e in original['events']}, {'customer.create', 'customer.rename'})
        self.assertEqual(len(original['events']), 2)
        self.assertTrue(all(e['resourceId'] == first['id'] and e['resourceId'] != second['id'] for e in original['events']))
        self.expect(self.mutate(self.admin, 'PUT', path, 'Confirmed rename', 1, key), 200)
        self.expect(self.mutate(self.admin, 'PUT', path, 'Stale attempt', 1), 412, 'revision_conflict')
        self.assertEqual(self.expect(self.audit(query), 200).json(), original)
        self.lab.sql(self.db, """CREATE FUNCTION synthetic_fail_filters43() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'synthetic filtered operation failure'; END; $$;
            CREATE TRIGGER synthetic_fail_filters43 BEFORE INSERT ON operation FOR EACH ROW EXECUTE FUNCTION synthetic_fail_filters43();""")
        before = self.durable()
        self.expect(self.mutate(self.admin, 'PUT', path, 'Must roll back', 2), 503)
        self.assertEqual(self.durable(), before)
        self.assertEqual(self.expect(self.audit(query), 200).json(), original)
        self.lab.sql(self.db, 'DROP TRIGGER synthetic_fail_filters43 ON operation; DROP FUNCTION synthetic_fail_filters43()')
        another = Client(self.server)
        self.expect(another.login('qa-admin', self.password), 200)
        self.assertEqual(self.expect(self.audit(query, another), 200).json(), original)
        self.server.close()
        self.server = self.lab.start_server(self.db)
        self.admin.server = another.server = self.server
        self.assertEqual(self.expect(self.audit(query, another), 200).json(), original)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--case', action='append')
    parser.add_argument('--include-regression', action='store_true')
    args = parser.parse_args()
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(AuditFilterPostgres) if n.startswith('test_filters_')]
    if args.case:
        if set(args.case) - set(names):
            raise ValueError('Unknown filter case')
        names = [n for n in names if n in args.case]
    args.evidence.mkdir(parents=True, exist_ok=False)
    paths = [WORKSPACE/'development/server/src/RackClick.Server'/n for n in
             ('AdminAudit.cs', 'OpenApiAudit.cs', 'Program.cs', 'AdminUsers.cs', 'PostgresStore.cs')]
    paths += [Path(__file__).resolve(), WORKSPACE/'development/server/tests/test_admin_audit.py',
              WORKSPACE/'development/server/tests/pg_support.py',
              WORKSPACE/'development/server/tests/test_admin_effective_permissions.py',
              WORKSPACE/'development/server/tests/test_session_wait_expiry.py']
    hashes = lambda: {p.relative_to(WORKSPACE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    original = hashes()
    dll_hash = hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()
    data = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
            'dllSha256': dll_hash, 'sourceHashes': original, 'actualQaOpened': False,
            'regressionIncluded': args.include_regression}
    lab = Lab('audit-filters43')
    with lab, (args.evidence/'tests.log').open('w', encoding='utf-8') as output:
        AuditFilterPostgres.lab = AuditPostgres.lab = lab
        suite = [AuditFilterPostgres(n) for n in names]
        if args.include_regression:
            suite.append(AuditPostgres('test_audit_pagination_metadata_and_openapi'))
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(suite))
        data.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    data.update(labStopped=not lab.running, serversStopped=all(s.process.poll() is not None for s in lab.servers),
                inputsUnchanged=original == hashes() and dll_hash == hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest())
    (args.evidence/'result.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return 0 if data['successful'] and data['labStopped'] and data['serversStopped'] and data['inputsUnchanged'] else 1


if __name__ == '__main__':
    sys.exit(main())
