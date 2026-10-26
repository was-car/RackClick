"""Four isolated native groups for read-only administrative permission snapshots."""
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
from test_session_wait_expiry import SessionWaitPostgres


class EffectivePermissionsPostgres(SessionWaitPostgres):
    def get(self, user, client=None, headers=None):
        return (client or self.admin).request('GET',
            f'/api/v1/admin/users/{user}/effective-permissions', headers=headers)

    def durable(self):
        # Every public table, including inventory and secret-bearing identity tables.
        # Raw rows/hashes never leave PostgreSQL: only an aggregate digest is returned.
        tables = self.lab.sql(self.db, "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
        statements = [f"SELECT md5(COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)::text,'')) FROM public.\"{table}\" t" for table in tables]
        return hashlib.sha256(self.lab.sql(self.db, ' UNION ALL '.join(statements)).encode()).hexdigest()

    def readonly(self, user, client=None, headers=None):
        before = self.durable()
        response = self.get(user, client, headers)
        self.assertEqual(before, self.durable(), 'Permission GET must not alter any public row')
        return response

    def foreign(self):
        house, user, customer, group = [str(uuid.uuid4()) for _ in range(4)]
        self.lab.sql(self.db, f"""DROP INDEX one_systemhaus_per_installation;
            INSERT INTO systemhaus(id,name) VALUES('{house}','Foreign synthetic');
            INSERT INTO app_user(id,systemhaus_id,username,password_hash)
              SELECT '{user}','{house}','foreign-synthetic',password_hash FROM app_user WHERE id='{self.admin_id}';
            INSERT INTO customer(id,systemhaus_id,name) VALUES('{customer}','{house}','Foreign customer');
            INSERT INTO user_group(id,systemhaus_id,name) VALUES('{group}','{house}','Foreign group');
            INSERT INTO user_group_member VALUES('{house}','{user}','{group}');
            INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{house}','{group}','inventory.read',NULL,NULL);
            """
        )
        return user, customer, group

    def set_grant(self, group, capability, scope='systemhaus', target=None, assigned=True, grant=None):
        payload = {'grantId': grant or str(uuid.uuid4()), 'capability': capability,
                   'scope': scope, 'targetId': target, 'assigned': assigned}
        result = self.admin.request('POST', f'/api/v1/admin/user-groups/{group}/grants', payload,
            {'If-Match': f'"{self.house_revision()}"', 'Idempotency-Key': str(uuid.uuid4()),
             'X-RackClick-Actor': self.admin_id})
        self.expect(result, 200)
        return payload['grantId']

    def set_user_member(self, group, user, assigned):
        self.expect(self.admin.request('POST', f'/api/v1/admin/user-groups/{group}/members',
            {'userId': user, 'assigned': assigned},
            {'If-Match': f'"{self.house_revision()}"', 'Idempotency-Key': str(uuid.uuid4()),
             'X-RackClick-Actor': self.admin_id}), 200)

    def assert_projection(self, user, session, expected_customers=None):
        response = self.expect(self.readonly(user), 200)
        data = response.json()
        self.assertEqual(data['permissions'], self.expect(session.request('GET', '/api/v1/me'), 200).json()['permissions'])
        if expected_customers is not None:
            self.assertEqual({c['customerId'] for c in data['permissions']['customers']}, set(expected_customers))
        return data['permissions']

    def test_effective_authorization_readonly(self):
        self.initialize()
        target, _ = self.add_user('target')
        customer = self.customer('Authorization scope')
        clients = []
        for name, capabilities in (('technician', ['inventory.read', 'inventory.edit']),
                                   ('reader', ['inventory.read']), ('scoped-security', ['security.manage'])):
            user, client = self.add_user(name)
            group = self.user_group(user)
            for capability in capabilities:
                self.grant(group, capability, customer=customer['id'])
            clients.append(client)
        cg = self.customer_group()
        self.grant(group, 'security.manage', customer_group=cg)
        foreign, _, _ = self.foreign()
        missing, empty = str(uuid.uuid4()), str(uuid.UUID(int=0))
        before = self.durable()
        for user in (target, foreign, missing, empty):
            self.expect(self.get(user, Client(self.server)), 401, 'authentication_required')
            for client in clients:
                self.expect(self.get(user, client), 403, 'forbidden')
        for user in (foreign, missing):
            self.expect(self.get(user), 404, 'not_found')
        self.expect(self.get(empty), 422, 'request_invalid')
        self.expect(self.get(target), 200)
        self.assertEqual(before, self.durable())
        # GET is safe without a mutation CSRF token; the current session is still mandatory.
        self.expect(self.readonly(target, headers={'X-RackClick-CSRF': ''}), 200)
        self.lab.sql(self.db, f"UPDATE app_session SET expires_at=clock_timestamp()-interval '1 second' WHERE user_id='{self.admin_id}'")
        self.expect(self.readonly(target), 401, 'authentication_required')

    def test_effective_composition_matches_me(self):
        self.initialize()
        customers = [self.customer(name)['id'] for name in ('Direct A', 'Overlap B', 'Grouped C', 'Unread D')]
        user, session = self.add_user('multi-group')
        direct = self.user_group(user, 'Direct readers')
        grouped = self.user_group(user, 'Grouped technicians')
        cgs = [self.customer_group(), self.customer_group()]
        for cg, members in zip(cgs, (customers[:2], customers[1:3])):
            for customer in members:
                self.lab.sql(self.db, f"INSERT INTO customer_group_member VALUES('{self.house}','{cg}','{customer}')")
        self.grant(direct, 'systemhaus.read')
        self.grant(grouped, 'systemhaus.read')
        self.grant(direct, 'inventory.read', customer=customers[0])
        self.grant(direct, 'customer.manage', customer=customers[3])
        self.grant(direct, 'security.manage', customer=customers[0])
        self.grant(grouped, 'inventory.read', customer_group=cgs[0])
        self.grant(grouped, 'inventory.read', customer_group=cgs[1])
        self.grant(grouped, 'inventory.edit', customer_group=cgs[0])
        self.grant(grouped, 'customer.manage', customer_group=cgs[1])
        # Projection is not the mutable API grant catalogue: legacy strings stay explainable.
        self.grant(grouped, 'legacy.synthetic', customer_group=cgs[1])
        unrelated, _ = self.add_user('unrelated')
        excluded = self.user_group(unrelated, 'Unrelated grants')
        self.grant(excluded, 'customer.create')
        _, foreign_customer, foreign_group = self.foreign()
        permissions = self.assert_projection(user, session, customers[:3])
        self.assertEqual(permissions['systemhausCapabilities'], ['systemhaus.read'])
        actual = {c['customerId']: c['capabilities'] for c in permissions['customers']}
        self.assertEqual(set(actual[customers[0]]), {'systemhaus.read', 'inventory.read', 'inventory.edit', 'security.manage'})
        self.assertEqual(set(actual[customers[1]]), {'systemhaus.read', 'inventory.read', 'inventory.edit', 'customer.manage', 'legacy.synthetic'})
        self.assertEqual(set(actual[customers[2]]), {'systemhaus.read', 'inventory.read', 'customer.manage', 'legacy.synthetic'})
        for capabilities in actual.values():
            self.assertEqual(capabilities, sorted(set(capabilities)))
        sources = permissions['sources']
        self.assertEqual({s['userGroupId'] for s in sources}, {direct, grouped})
        self.assertNotIn(foreign_group, {s['userGroupId'] for s in sources})
        self.assertEqual({s['scopeType'] for s in sources}, {'systemhaus', 'customer', 'customerGroup'})
        self.assertEqual({s['scopeId'] for s in sources if s['scopeType'] == 'customerGroup'}, set(cgs))
        self.assertTrue(any(s['scopeId'] == customers[3] for s in sources))
        self.assertTrue(all((s['scopeId'] is None) == (s['scopeType'] == 'systemhaus') for s in sources))
        self.assertEqual({s['userGroupName'] for s in sources}, {'Direct readers', 'Grouped technicians'})
        self.assertEqual(len(sources), 10)
        self.expect(self.get(user, session), 403, 'forbidden')  # scoped security cannot become global authority
        self.grant(direct, 'inventory.read')
        global_permissions = self.assert_projection(user, session, customers)
        self.assertEqual(global_permissions['systemhausCapabilities'], ['inventory.read', 'systemhaus.read'])
        self.assertNotIn(foreign_customer, {c['customerId'] for c in global_permissions['customers']})

    def test_effective_fresh_changes_inactive_dto_openapi(self):
        self.initialize()
        customer = self.customer('Fresh permission')['id']
        second = self.customer('Fresh group member')['id']
        user, session = self.add_user('changing-target')
        group = self.user_group(user, 'Changing memberships')
        self.assert_projection(user, session, [])
        read_grant = self.set_grant(group, 'inventory.read', 'customer', customer)
        self.assert_projection(user, session, [customer])
        self.set_grant(group, 'inventory.edit', 'customer', customer)
        self.assertIn('inventory.edit', self.assert_projection(user, session, [customer])['customers'][0]['capabilities'])
        self.set_grant(group, 'inventory.read', 'customer', customer, False, read_grant)
        self.assert_projection(user, session, [])  # edit without read does not expose customer
        cg = self.customer_group()
        self.set_grant(group, 'inventory.read', 'customerGroup', cg)
        self.expect(self.member(cg, second, True), 200)
        self.assert_projection(user, session, [second])
        self.expect(self.member(cg, second, False), 200)
        self.assert_projection(user, session, [])
        self.expect(self.member(cg, second, True), 200)
        self.set_user_member(group, user, False)
        self.assert_projection(user, session, [])
        self.set_user_member(group, user, True)
        self.assert_projection(user, session, [second])
        self.expect(self.change(user, False), 200)
        response = self.expect(self.readonly(user), 200)
        data = response.json()
        self.assertEqual(data['user'], {'id': user, 'userName': 'changing-target', 'active': False})
        self.assertEqual(data['permissions'], {'systemhausCapabilities': [], 'customers': [], 'sources': []})
        self.assertEqual(response.headers['etag'], f'"{self.house_revision()}"')
        self.assertEqual(data['revision'], self.house_revision())
        self.assertEqual(set(data), {'revision', 'user', 'permissions'})
        self.expect(session.request('GET', '/api/v1/me'), 401)
        doc = self.expect(self.admin.request('GET', '/api/v1/openapi.json'), 200).json()
        operation = doc['paths']['/api/v1/admin/users/{userId}/effective-permissions']['get']
        schemas = doc['components']['schemas']
        self.assertEqual(operation['operationId'], 'readUserEffectivePermissions')
        self.assertEqual(operation['responses']['200']['content']['application/json']['schema']['$ref'], '#/components/schemas/AdminEffectivePermissionsSnapshot')
        self.assertTrue({'200', '401', '403', '404', '422'} <= set(operation['responses']))
        self.assertIn('ETag', operation['responses']['200']['headers'])
        self.assertEqual(operation['parameters'], [{'in': 'path', 'name': 'userId', 'required': True, 'schema': {'type': 'string', 'format': 'uuid'}}])
        self.assertEqual(set(schemas['AdminEffectivePermissionsSnapshot']['properties']), set(data))
        self.assertEqual(set(schemas['AdminEffectivePermissionsSnapshot']['required']), set(data))
        self.assertEqual(schemas['AdminEffectivePermissionsSnapshot']['properties']['permissions']['$ref'], '#/components/schemas/EffectivePermissions')
        self.assertEqual(set(schemas['EffectivePermissions']['properties']), {'systemhausCapabilities', 'customers', 'sources'})
        self.assertEqual(set(schemas['PermissionSource']['properties']), {'userGroupId', 'userGroupName', 'capability', 'scopeType', 'scopeId'})
        self.assertEqual(set(schemas['CustomerPermissions']['properties']), {'customerId', 'capabilities'})
        active = self.expect(self.readonly(self.admin_id), 200).json()
        self.assertEqual(set(active['user']), {'id', 'userName', 'active'})
        for source in active['permissions']['sources']:
            self.assertEqual(set(source), set(schemas['PermissionSource']['properties']))
        for item in active['permissions']['customers']:
            self.assertEqual(set(item), {'customerId', 'capabilities'})
        public = json.dumps(active)
        self.assertTrue(all(word not in public for word in ('password', 'csrf', 'cookie', 'token', 'connection')))
        secret_values = self.lab.sql(self.db, 'SELECT password_hash FROM app_user UNION ALL SELECT token_hash FROM app_session UNION ALL SELECT csrf_hash FROM app_session').splitlines()
        self.assertTrue(all(secret not in public for secret in secret_values), 'Public permission DTO must exclude identity secrets')
        actor, actor_session = self.add_user('revoked-administrator')
        actor_group = self.user_group(actor, 'Temporary administrator')
        grant = self.set_grant(actor_group, 'security.manage')
        self.expect(self.readonly(user, actor_session), 200)
        self.set_grant(actor_group, 'security.manage', assigned=False, grant=grant)
        self.expect(self.readonly(user, actor_session), 403, 'forbidden')
        self.expect(actor_session.request('GET', '/api/v1/me'), 200)  # session lives; authority does not

    def test_effective_actor_expiry_after_wait(self):
        self.initialize()
        self.expired_wait(lambda: self.get(self.admin_id))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(EffectivePermissionsPostgres) if n.startswith('test_effective_')]
    if args.case:
        if set(args.case) - set(names):
            raise ValueError('Unknown effective permission case')
        names = [n for n in names if n in args.case]
    args.evidence.mkdir(parents=True, exist_ok=False)
    paths = [WORKSPACE/'development/server/src/RackClick.Server'/name for name in
             ('PostgresStore.cs', 'Program.cs', 'OpenApiAdmin.cs', 'AdminEffectivePermissions.cs', 'AdminUsers.cs')]
    paths += [Path(__file__).resolve(), WORKSPACE/'development/server/tests/pg_support.py', WORKSPACE/'development/server/tests/test_session_wait_expiry.py']
    def hashes():
        return {str(p.relative_to(WORKSPACE)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    original = hashes()
    dllhash = hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()
    data = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
            'dllSha256': dllhash, 'sourceHashes': original, 'actualQaOpened': False,
            'globalPointerChanged': False}
    lab = Lab('admin-effective-permissions')
    with lab, (args.evidence/'tests.log').open('w', encoding='utf-8') as output:
        EffectivePermissionsPostgres.lab = lab
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(
            unittest.TestSuite(EffectivePermissionsPostgres(n) for n in names))
        data.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    data.update(labStopped=not lab.running, serversStopped=all(s.process.poll() is not None for s in lab.servers),
                inputsUnchanged=original == hashes() and dllhash == hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest())
    (args.evidence/'result.json').write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
    return 0 if result.wasSuccessful() and data['labStopped'] and data['serversStopped'] and data['inputsUnchanged'] else 1


if __name__ == '__main__':
    sys.exit(main())
