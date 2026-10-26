"""Administrative audit50: real HTTP writers and explicit SQL historical fixtures, new labs only."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import secrets
import sys
import unittest
import uuid

from pg_support import Client, DEFAULT_DLL, Lab, WORKSPACE
from test_postgres import EvidenceResult, Tee
from test_admin_audit_detail import AuditDetailPostgres


def uid():
    return str(uuid.uuid4())


def field(name, kind, before, after):
    return {'field': name, 'type': kind, 'before': before, 'after': after}


class AdministrativeAuditPostgres(AuditDetailPostgres):
    def detail(self, event, client=None):
        before = self.durable()
        response = (client or self.admin).request('GET', f'/api/v1/admin/audit/{event}/administrative-detail')
        self.assertEqual(before, self.durable(), 'Administrative detail GET changed a public row')
        return response

    def write(self, path, body, cancel=False, key=None, revision=None, status=200):
        key = key or uid()
        if cancel:
            path += f'/operations/{key}/cancel'
        response = self.admin.request('POST', path, body,
            {'If-Match': f'"{revision if revision is not None else self.house_revision()}"',
             'Idempotency-Key': key, 'X-RackClick-Actor': self.admin_id})
        self.expect(response, status)
        return key, response.json()

    def assert_fields(self, event, action, expected):
        response = self.expect(self.detail(event), 200)
        result = response.json()
        self.assertEqual(set(result), {'revision', 'event', 'detail'})
        self.assertEqual(result['revision'], self.house_revision())
        self.assertEqual(response.headers['etag'], f'"{result["revision"]}"')
        self.assertEqual(result['event']['action'], action)
        self.assertEqual(result['detail'], {'status': 'available', 'fields': expected})
        return result

    def test_administrative_all_eighteen_http_writers(self):
        self.initialize()
        name = 'histórico-e\u0301-ä-😀'
        key, made = self.write('/api/v1/admin/users', {'username': name, 'password': self.password}, status=201)
        user = made['resource']['id']
        user_fields = [field('userId', 'uuid', None, user), field('userName', 'userName', None, name),
                       field('active', 'boolean', None, 'true')]
        self.assert_fields(self.event_for(key), 'user.create', user_fields)
        groups = []
        for path, kind in [('user-groups', 'userGroup'), ('customer-groups', 'customerGroup')]:
            group_name = f'{kind} Ω e\u0301 <b>😀</b>'
            key, made = self.write('/api/v1/admin/' + path, {'name': group_name}, status=201)
            group = made['resource']['id']; groups.append(group)
            self.assert_fields(self.event_for(key), kind + '.create', [field('groupId', 'uuid', None, group),
                field('name', 'name', None, group_name), field('groupKind', 'groupKind', None, kind)])
        ug, cg = groups
        customer = self.customer('HTTP audit target')['id']
        for path, member, member_id, action in [('user-groups', 'userId', user, 'userGroup.member.set'),
                                               ('customer-groups', 'customerId', customer, 'customerGroup.member.set')]:
            group = ug if member == 'userId' else cg
            for previous, assigned in [(False, True), (True, True), (True, False)]:
                key, _ = self.write(f'/api/v1/admin/{path}/{group}/members', {member: member_id, 'assigned': assigned})
                self.assert_fields(self.event_for(key), action, [field('groupId', 'uuid', group, group),
                    field(member, 'uuid', member_id, member_id),
                    field('assigned', 'boolean', str(previous).lower(), str(assigned).lower())])
        capabilities = ['systemhaus.read', 'systemhaus.manage', 'customer.create', 'customer.manage',
                        'inventory.read', 'inventory.edit', 'inventory.delete', 'security.manage']
        for index, capability in enumerate(capabilities):
            scope, target = [('systemhaus', None), ('customer', customer), ('customerGroup', cg)][index % 3]
            grant = uid()
            body = {'grantId': grant, 'capability': capability, 'scope': scope, 'targetId': target, 'assigned': True}
            key, _ = self.write(f'/api/v1/admin/user-groups/{ug}/grants', body)
            self.assert_fields(self.event_for(key), 'userGroup.grant.set', [field('groupId', 'uuid', ug, ug),
                field('grantId', 'uuid', grant, grant), field('capability', 'capability', capability, capability),
                field('scope', 'scope', scope, scope), field('targetId', 'uuid', target, target),
                field('assigned', 'boolean', 'false', 'true')])
        # State no-op is still a real committed writer action.
        key, _ = self.write(f'/api/v1/admin/users/{user}/state', {'active': True})
        steady = [field('userId', 'uuid', user, user), field('userName', 'userName', name, name),
                  field('active', 'boolean', 'true', 'true')]
        self.assert_fields(self.event_for(key), 'user.state.set', steady)
        new_password = secrets.token_urlsafe(32)
        key, _ = self.write(f'/api/v1/admin/users/{user}/password', {'password': new_password})
        reset = self.assert_fields(self.event_for(key), 'user.password.reset', steady + [field('passwordReset', 'boolean', None, 'true')])
        self.assertNotIn(new_password, json.dumps(reset))
        target_client = Client(self.server); self.expect(target_client.login(name, new_password), 200)
        sid = self.lab.sql(self.db, f"SELECT id FROM app_session WHERE user_id='{user}'")
        key, _ = self.write(f'/api/v1/admin/users/{user}/sessions/{sid}/revoke', {})
        self.assert_fields(self.event_for(key), 'user.session.revoke', [field('userId', 'uuid', user, user),
            field('sessionId', 'uuid', sid, sid), field('revoked', 'boolean', None, 'true'),
            field('wasCurrent', 'boolean', None, 'false')])
        # Cancellation fixtures are also HTTP writes; targets need not currently exist.
        missing_user, missing_group, missing_customer, missing_sid = uid(), uid(), uid(), uid()
        cases = [('/api/v1/admin/users', {'username': 'cancelled account'}, 'user.create'),
            ('/api/v1/admin/user-groups', {'name': 'cancelled users'}, 'userGroup.create'),
            ('/api/v1/admin/customer-groups', {'name': 'cancelled customers'}, 'customerGroup.create'),
            (f'/api/v1/admin/user-groups/{missing_group}/members', {'userId': missing_user, 'assigned': True}, 'userGroup.member.set'),
            (f'/api/v1/admin/customer-groups/{missing_group}/members', {'customerId': missing_customer, 'assigned': True}, 'customerGroup.member.set'),
            (f'/api/v1/admin/user-groups/{missing_group}/grants', {'grantId': uid(), 'capability': 'inventory.read', 'scope': 'customer', 'targetId': missing_customer, 'assigned': True}, 'userGroup.grant.set'),
            (f'/api/v1/admin/users/{missing_user}/state', {'active': False}, 'user.state.set'),
            (f'/api/v1/admin/users/{missing_user}/password', {}, 'user.password.reset'),
            (f'/api/v1/admin/users/{missing_user}/sessions/{missing_sid}/revoke', {}, 'user.session.revoke')]
        before_revision = self.house_revision()
        for path, body, action in cases:
            key, _ = self.write(path, body, cancel=True, revision=1)
            expected = [field('requestId', 'uuid', None, key), field('state', 'state', None, 'cancelled')]
            if action == 'user.session.revoke':
                expected = [field('userId', 'uuid', missing_user, None), field('sessionId', 'uuid', missing_sid, None)] + expected
            self.assert_fields(self.event_for(key), action + '.cancel', expected)
        self.assertEqual(before_revision, self.house_revision())
        actions = self.lab.sql(self.db, "SELECT DISTINCT action FROM audit_event WHERE action NOT LIKE 'customer.%' ORDER BY action").splitlines()
        expected_actions = [r[2] for r in cases]
        self.assertEqual(set(actions), set(expected_actions + [a + '.cancel' for a in expected_actions]))
        doc = self.expect(self.admin.request('GET', '/api/v1/openapi.json'), 200).json()
        op = doc['paths']['/api/v1/admin/audit/{eventId}/administrative-detail']['get']
        self.assertEqual(op['operationId'], 'readAdminAuditAdministrativeDetail')
        self.assertEqual({p['name'] for p in op['parameters']}, {'eventId'})
        self.assertTrue({'200', '401', '403', '404', '422'} <= set(op['responses']))
        self.assertIn('ETag', op['responses']['200']['headers'])
        schemas = doc['components']['schemas']
        for schema, required in [('AuditAdministrativeField', ['field', 'type', 'before', 'after']),
                                  ('AdminAuditAdministrativeDetail', ['status', 'fields']),
                                  ('AdminAuditAdministrativeDetailSnapshot', ['revision', 'event', 'detail'])]:
            self.assertEqual(schemas[schema]['required'], required)
            self.assertEqual(set(schemas[schema]['properties']), set(required))

    def test_administrative_authority_isolation_expiry_readonly(self):
        self.initialize()
        key, _ = self.write('/api/v1/admin/user-groups', {'name': 'Authority event'}, status=201)
        event = self.event_for(key)
        customer = self.customer('Scoped authority')
        user, scoped = self.add_user('scoped-administrative-detail')
        group = self.user_group(user)
        self.grant(group, 'security.manage', customer=customer['id'])
        cg = self.customer_group(); self.grant(group, 'security.manage', customer_group=cg)
        for value in ('bad', event, uid()):
            self.expect(self.detail(value, scoped), 403, 'forbidden')
            self.expect(self.detail(value, Client(self.server)), 401, 'authentication_required')
        for value in ('bad', str(uuid.UUID(int=0)), event.replace('-', ''), '%7B' + event + '%7D', '%20' + event, event + '%20'):
            self.expect(self.detail(value), 422, 'request_invalid')
        foreign, _, _ = self.foreign(); foreign_event = uid()
        self.lab.sql(self.db, f"""INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,after_json)
            SELECT '{foreign_event}',systemhaus_id,id,'{uid()}','user.create','{uid()}','{{}}'
            FROM app_user WHERE id='{foreign}'""")
        absent = self.expect(self.detail(uid()), 404, 'not_found')
        self.assertEqual(absent.json(), self.expect(self.detail(foreign_event), 404, 'not_found').json())
        self.expect(self.detail(event.upper()), 200)
        # No mutation CSRF requirement, while cookie and live global capability remain mandatory.
        csrf = self.admin.csrf; self.admin.csrf = None
        self.expect(self.detail(event), 200); self.admin.csrf = csrf
        temporary, client = self.add_user('temporary-administrative-detail')
        tg = self.user_group(temporary); grant = self.set_grant(tg, 'security.manage')
        self.expect(self.detail(event, client), 200)
        self.set_grant(tg, 'security.manage', assigned=False, grant=grant)
        self.expect(self.detail('bad', client), 403, 'forbidden')
        self.expect(client.request('GET', '/api/v1/me'), 200)
        self.expired_wait(lambda: self.admin.request('GET', f'/api/v1/admin/audit/{event}/administrative-detail'))

    def test_administrative_historical_fixtures_shapes_redaction_bounds(self):
        self.initialize()
        marker = 'synthetic-private50-never-publish'
        user, group, member, grant, sid = [uid() for _ in range(5)]
        username = 'LEGACY e\u0301 Ä <script>😀</script>'
        account = {'id': user, 'userName': username, 'active': True}
        member_data = {'groupId': group, 'userId': member, 'assigned': False}
        customer_member = {'groupId': group, 'customerId': member, 'assigned': False}
        grant_data = {'groupId': group, 'grantId': grant, 'capability': 'inventory.read', 'scope': 'systemhaus', 'targetId': None, 'assigned': False}
        session = {'userId': user, 'sessionId': sid}
        valid = [('user.create', user, None, account), ('user.state.set', user, account, account),
            ('user.password.reset', user, account, account | {'passwordReset': True}),
            ('userGroup.create', group, None, {'id': group, 'name': 'Group e\u0301 😀', 'kind': 'userGroup'}),
            ('customerGroup.create', group, None, {'id': group, 'name': 'Group e\u0301 😀', 'kind': 'customerGroup'}),
            ('userGroup.member.set', group, member_data, member_data | {'assigned': True}),
            ('customerGroup.member.set', group, customer_member, customer_member | {'assigned': True}),
            ('userGroup.grant.set', group, grant_data, grant_data | {'assigned': True}),
            ('user.session.revoke', sid, session, session | {'revoked': True, 'wasCurrent': False})]
        read_events = []
        def check(action, resource, before, after, available, match_request=False):
            event = self.insert_event(action, resource, before, after)
            if match_request:
                # Isolate each cancellation guard: every other property, including the
                # request identity of this newly inserted event, stays valid.
                self.lab.sql(self.db, f"UPDATE audit_event SET after_json=jsonb_set(after_json,'{{requestId}}',to_jsonb(request_id::text)) WHERE id='{event}'")
                self.assertEqual(self.lab.sql(self.db, f"SELECT after_json->>'requestId'=request_id::text FROM audit_event WHERE id='{event}'"), 't')
            baseline = self.durable()
            response = self.expect(self.admin.request('GET', f'/api/v1/admin/audit/{event}/administrative-detail'), 200)
            self.assertEqual(baseline, self.durable())
            detail = response.json()['detail']
            self.assertEqual(detail['status'], 'available' if available else 'unavailable', (action, before, after))
            if not available: self.assertEqual(detail, {'status': 'unavailable', 'fields': []})
            self.assertNotIn(marker, response.body.decode())
            read_events.append(event)
            return detail
        # No current resources or operation rows exist for these synthetic IDs.
        for action, resource, before, after in valid:
            extra = {'password': marker, 'password_hash': marker, 'token': marker, 'csrf': marker, 'nested': {'secret': marker}}
            result = check(action, resource, None if before is None else before | extra, after | extra, True)
            if action.startswith('user.') and 'userName' in after:
                self.assertEqual(next(f for f in result['fields'] if f['field'] == 'userName')['after'], username)
            for missing in after:
                incomplete = dict(after); del incomplete[missing]
                check(action, resource, before, incomplete, False)
            check(action, resource, before, [], False)
            check(action, uid(), before, after, False)
        cases = [
            ('user.create', user, {}, account), ('user.create', user, None, account | {'active': False}),
            ('user.create', user, None, account | {'active': 'true'}),
            ('user.create', user, None, account | {'id': user.replace('-', '')}),
            ('user.create', user, None, account | {'id': str(uuid.UUID(int=0))}),
            ('user.create', user, None, account | {'userName': ' padded '}),
            ('user.create', user, None, account | {'userName': 'bad\nname'}),
            ('user.create', user, None, account | {'userName': '😀' * 101}),
            ('user.state.set', user, account, account | {'userName': 'changed'}),
            ('user.state.set', user, None, account),
            ('user.password.reset', user, account, account | {'active': False, 'passwordReset': True}),
            ('user.password.reset', user, account, account | {'passwordReset': False}),
            ('userGroup.create', group, None, {'id': group, 'name': 'G', 'kind': 'customerGroup'}),
            ('customerGroup.create', group, None, {'id': group, 'name': ' G ', 'kind': 'customerGroup'}),
            ('userGroup.member.set', group, member_data, member_data | {'userId': uid()}),
            ('customerGroup.member.set', group, customer_member, customer_member | {'customerId': uid()}),
            ('userGroup.member.set', group, member_data, member_data | {'assigned': 1}),
            ('userGroup.grant.set', group, grant_data, grant_data | {'capability': 'unknown.capability'}),
            ('userGroup.grant.set', group, grant_data, grant_data | {'grantId': uid()}),
            ('userGroup.grant.set', group, grant_data, grant_data | {'targetId': uid()}),
            ('userGroup.grant.set', group, grant_data | {'scope': 'customer'}, grant_data | {'scope': 'customer'}),
            ('userGroup.grant.set', group, grant_data | {'scope': 'wrong'}, grant_data | {'scope': 'wrong'}),
            ('user.session.revoke', sid, session, session | {'revoked': False, 'wasCurrent': False}),
            ('user.session.revoke', sid, session, session | {'revoked': True, 'wasCurrent': True}),
            ('user.session.revoke', sid, session, session | {'sessionId': uid(), 'revoked': True, 'wasCurrent': False}),
            ('user.session.revoke', sid, session, session | {'revoked': True, 'wasCurrent': 'false'}),
            ('unknown.synthetic', user, None, account), ('systemhaus.rename', self.house, None, account)]
        for case in cases: check(*case, False)
        # Both independent JSONB textual byte limits and exact depth boundary are exercised.
        for side in ('before', 'after'):
            for size in (4096, 4097):
                before, after = deepcopy(account), deepcopy(account)
                value = before if side == 'before' else after
                value['padding'] = ''
                # PostgreSQL JSONB text includes spaces; measure that actual representation.
                event = self.insert_event('user.state.set', user, before, after)
                column = side + '_json'
                self.lab.sql(self.db, f"UPDATE audit_event SET {column}=jsonb_set({column},'{{padding}}',to_jsonb(repeat('x',{size}-octet_length({column}::text)))) WHERE id='{event}'")
                self.assertEqual(self.lab.sql(self.db, f"SELECT octet_length({column}::text) FROM audit_event WHERE id='{event}'"), str(size))
                detail = self.expect(self.detail(event), 200).json()['detail']
                self.assertEqual(detail['status'], 'available' if size == 4096 else 'unavailable')
        for depth, available in [(7, True), (8, False)]:
            nested = marker
            for _ in range(depth): nested = {'n': nested}
            check('user.create', user, None, account | {'extra': nested}, available)
        # UTF8 byte counting is not character counting, and uppercase IDs become canonical.
        check('user.create', user, None, account | {'padding': '😀' * 1100}, False)
        canonical = check('user.create', user, None, account | {'id': user.upper(), 'userName': '😀' * 100}, True)
        self.assertEqual(canonical['fields'][0]['after'], user)
        # Cancellations never infer intended target metadata from arbitrary extra properties.
        actions = [r[0] for r in valid]
        for action in actions:
            resource = self.house if action.endswith('.create') else sid if action == 'user.session.revoke' else user
            before = session if action == 'user.session.revoke' else None
            event = self.insert_event(action + '.cancel', resource, before, {})
            request = self.lab.sql(self.db, f"SELECT request_id FROM audit_event WHERE id='{event}'")
            after = {'requestId': request, 'state': 'cancelled', 'operation': None, 'name': marker, 'capability': marker}
            self.lab.sql(self.db, f"UPDATE audit_event SET after_json='{json.dumps(after)}'::jsonb WHERE id='{event}'")
            projected = self.expect(self.detail(event), 200).json()['detail']
            self.assertEqual(projected['status'], 'available')
            self.assertNotIn(marker, json.dumps(projected))
            check(action + '.cancel', resource, before, after | {'requestId': uid()}, False)
            for bad in (after | {'state': 'committed'}, after | {'operation': {}}):
                check(action + '.cancel', resource, before, bad, False, match_request=True)
            check(action + '.cancel', resource, before, [], False)
            if action != 'user.session.revoke':
                check(action + '.cancel', resource, {}, after, False, match_request=True)
        # Current actor name is explicit; historical resource names never use live joins.
        event = self.insert_event('user.create', user, None, account)
        self.lab.sql(self.db, f"UPDATE app_user SET username='current-actor50' WHERE id='{self.admin_id}'")
        result = self.expect(self.detail(event), 200).json()
        self.assertEqual(result['event']['actor']['userName'], 'current-actor50')
        self.assertEqual(result['detail']['fields'][1]['after'], username)

    def test_administrative_commit_replay_rollback_restart_and_self_session(self):
        self.initialize()
        revision, key = self.house_revision(), uid()
        body = {'username': 'commit-audit50', 'password': self.password}
        _, made = self.write('/api/v1/admin/users', body, key=key, revision=revision, status=201)
        event = self.event_for(key)
        original = self.expect(self.detail(event), 200).json()
        before = self.durable()
        self.write('/api/v1/admin/users', body, key=key, revision=revision, status=201)
        self.assertEqual(before, self.durable())
        self.write('/api/v1/admin/users', body | {'username': 'stale-audit50'}, revision=revision, status=412)
        self.assertEqual(before, self.durable())
        self.lab.sql(self.db, """CREATE FUNCTION synthetic_fail50() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'synthetic operation failure50'; END; $$;
            CREATE TRIGGER synthetic_fail50 BEFORE INSERT ON operation FOR EACH ROW EXECUTE FUNCTION synthetic_fail50();""")
        before = self.durable()
        self.write('/api/v1/admin/users', body | {'username': 'rollback-audit50'}, status=503)
        self.assertEqual(before, self.durable(), 'Account, audit, revision and operation must roll back together')
        self.lab.sql(self.db, 'DROP TRIGGER synthetic_fail50 ON operation; DROP FUNCTION synthetic_fail50()')
        second = Client(self.server); self.expect(second.login('qa-admin', self.password), 200)
        self.assertEqual(self.expect(self.detail(event, second), 200).json(), original)
        self.server.close(); self.server = self.lab.start_server(self.db)
        self.admin.server = second.server = self.server
        self.assertEqual(self.expect(self.detail(event, second), 200).json(), original)
        digest = hashlib.sha256(self.admin.cookie.split('=', 1)[1].encode()).hexdigest().upper()
        sid = self.lab.sql(self.db, f"SELECT id FROM app_session WHERE token_hash='{digest}'", sensitive=True)
        key, _ = self.write(f'/api/v1/admin/users/{self.admin_id}/sessions/{sid}/revoke', {})
        self.expect(self.admin.request('GET', '/api/v1/me'), 401)
        self.admin = second
        self.assert_fields(self.event_for(key), 'user.session.revoke', [field('userId', 'uuid', self.admin_id, self.admin_id),
            field('sessionId', 'uuid', sid, sid), field('revoked', 'boolean', None, 'true'), field('wasCurrent', 'boolean', None, 'true')])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--case', action='append')
    parser.add_argument('--include-regression', action='store_true')
    args = parser.parse_args()
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(AdministrativeAuditPostgres) if n.startswith('test_administrative_')]
    if args.case:
        if set(args.case) - set(names): raise ValueError('Unknown administrative audit test')
        names = [n for n in names if n in args.case]
    args.evidence.mkdir(parents=True, exist_ok=False)
    files = [WORKSPACE/'development/server/src/RackClick.Server'/p for p in
             ('AdminAuditAdministrativeDetail.cs', 'AdminAuditDetail.cs', 'AdminAudit.cs', 'OpenApiAudit.cs', 'Program.cs',
              'AdminUsers.cs', 'AdminGroupWrites.cs', 'AdminGroupMembers.cs', 'AdminCustomerGroupMembers.cs',
              'AdminGrantWrites.cs', 'AdminUserState.cs', 'AdminUserPassword.cs', 'AdminUserSessionRevocation.cs', 'PostgresStore.cs')]
    files += [Path(__file__).resolve(), WORKSPACE/'development/server/tests/test_admin_audit_detail.py',
              WORKSPACE/'development/server/tests/pg_support.py']
    hashes = lambda: {p.relative_to(WORKSPACE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original = hashes(); dll = hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(), 'dllSha256': dll,
              'sourceHashes': original, 'actualQaOpened': False, 'httpWriterActions': 18,
              'sqlFixtures': 'Malformed/redaction/bounds/historical shapes only; authority fixtures follow existing harness.',
              'regressionIncluded': args.include_regression}
    lab = Lab('audit-administration50')
    with lab, (args.evidence/'tests.log').open('w', encoding='utf-8') as output:
        AdministrativeAuditPostgres.lab = AuditDetailPostgres.lab = lab
        tests = [AdministrativeAuditPostgres(n) for n in names]
        if args.include_regression:
            tests += [AuditDetailPostgres(n) for n in unittest.defaultTestLoader.getTestCaseNames(AuditDetailPostgres) if n.startswith('test_detail_')]
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(tests))
        report.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    report.update(labStopped=not lab.running, serversStopped=all(s.process.poll() is not None for s in lab.servers),
                  inputsUnchanged=original == hashes() and dll == hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest())
    (args.evidence/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return 0 if report['successful'] and report['labStopped'] and report['serversStopped'] and report['inputsUnchanged'] else 1


if __name__ == '__main__':
    sys.exit(main())
