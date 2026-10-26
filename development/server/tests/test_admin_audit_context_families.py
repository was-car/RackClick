"""Five separately frozen backend families55..59; explicit DLL/frontend, new PostgreSQL labs only."""
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

from pg_support import Client, Lab, NO_WINDOW, SERVER_ROOT, WORKSPACE
from test_postgres import EvidenceResult, Tee
from test_admin_audit_context import AuditContextPostgres


def uid(): return str(uuid.uuid4())
def obj(kind, identity, relation='target'): return {'kind': kind, 'id': identity, 'relation': relation}


class ContextFamiliesPostgres(AuditContextPostgres):
    dll = frontend = baseline_dll = None

    def initialize(self, username='qa-admin', baseline=False):
        dll = self.baseline_dll if baseline else self.dll
        self.assertEqual(self.lab.bootstrap(self.db, username, self.password, dll=dll).returncode, 0)
        self.lab.grant_runtime(self.db)
        self.house = self.lab.sql(self.db, 'SELECT id FROM systemhaus')
        self.admin_id = self.lab.sql(self.db, 'SELECT id FROM app_user')
        self.server = self.lab.start_server(self.db, dll=dll, frontend=self.frontend)
        self.admin = Client(self.server); self.expect(self.admin.login(username, self.password), 200)

    def expected_refs(self, before, objects, cancel=False, customer=None, customer_before=None, customer_after=None):
        return {'status': 'available', 'captureVersion': 1, 'actorId': self.admin_id,
            'scopeKind': 'customer' if customer else 'systemhaus', 'scopeId': customer or self.house,
            'customerId': customer, 'revisionScope': 'systemhaus', 'revisionBefore': before,
            'revisionAfter': before if cancel else before + 1,
            'customerRevisionBefore': customer_before, 'customerRevisionAfter': customer_after,
            'outcome': 'cancelled' if cancel else 'committed', 'objects': objects}

    def not_recorded(self):
        return super().not_recorded() | {'customerRevisionBefore': None, 'customerRevisionAfter': None}

    def recorded(self, key, before, objects, cancel=False, **kwargs):
        return self.read(self.event_for(key), self.expected_refs(before, objects, cancel, **kwargs))

    def sid(self, client):
        digest = hashlib.sha256(client.cookie.split('=', 1)[1].encode()).hexdigest().upper()
        return self.lab.sql(self.db, f"SELECT id FROM app_session WHERE token_hash='{digest}'", sensitive=True)

    def restart(self):
        self.server.close(); self.server = self.lab.start_server(self.db, dll=self.dll, frontend=self.frontend)
        self.admin.server = self.server

    def migration(self):
        env = self.lab.environment(); env['ConnectionStrings__RackClick'] = self.db.connection(self.lab.port, runtime=False)
        result = subprocess.run([str(self.lab.dotnet), str(self.dll), '--migrate'], cwd=SERVER_ROOT, env=env,
            capture_output=True, text=True, encoding='utf-8', timeout=60, creationflags=NO_WINDOW)
        (self.db.directory/f'migrate-seven-{uid()}.log').write_text(result.stdout + result.stderr, encoding='utf-8')
        return result

    def trigger(self, table, second=False, position=None):
        position = position or (2 if second else None)
        when = f' WHEN (NEW.position={position})' if position and table == 'audit_context_object' else ''
        self.lab.sql(self.db, f"""CREATE FUNCTION fail_context_family() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'synthetic family context failure'; END; $$;
            CREATE TRIGGER fail_context_family BEFORE INSERT ON {table} FOR EACH ROW{when} EXECUTE FUNCTION fail_context_family();""")

    def untrigger(self, table):
        self.lab.sql(self.db, f'DROP TRIGGER fail_context_family ON {table}; DROP FUNCTION fail_context_family()')

    def test_55_flow_password_and_public_session(self):
        self.initialize()
        user, old = self.add_user('family55')
        new = secrets.token_urlsafe(32)
        reset_path = f'/api/v1/admin/users/{user}/password'
        reset, result = self.write(reset_path, {'password': new})
        self.recorded(reset, 1, [obj('user', user)])
        self.expect(old.request('GET', '/api/v1/me'), 401)
        fresh = Client(self.server); self.expect(fresh.login('family55', new), 200)
        sid = self.sid(fresh); revoke_path = f'/api/v1/admin/users/{user}/sessions/{sid}/revoke'
        revoke, _ = self.write(revoke_path, {})
        self.recorded(revoke, 2, [obj('user', user), obj('session', sid)])
        self.expect(fresh.request('GET', '/api/v1/me'), 401)
        retained = Client(self.server); self.expect(retained.login('family55', new), 200)
        before = self.durable()
        self.assertEqual(self.write(reset_path, {'password': new}, key=reset, revision=1)[1], result)
        self.write(revoke_path, {}, key=revoke, revision=2)
        self.assertEqual(before, self.durable()); self.expect(retained.request('GET', '/api/v1/me'), 200)
        missing, missing_sid = uid(), uid()
        for path, objects in [(f'/api/v1/admin/users/{missing}/password', [obj('user', missing, 'intendedTarget')]),
            (f'/api/v1/admin/users/{missing}/sessions/{missing_sid}/revoke', [obj('user', missing, 'intendedTarget'), obj('session', missing_sid, 'intendedTarget')])]:
            key, cancelled = self.write(path, {}, cancel=True, revision=1)
            self.recorded(key, 3, objects, True)
            before = self.durable(); self.assertEqual(self.write(path, {}, cancel=True, key=key, revision=1)[1], cancelled)
            self.assertEqual(before, self.durable())
        before = self.durable()
        self.write(reset_path, {'password': new}, revision=1, status=412)
        self.write(reset_path, {'password': secrets.token_urlsafe(32)}, key=reset, revision=1, status=409)
        self.assertEqual(before, self.durable())
        second = Client(self.server); self.expect(second.login('qa-admin', self.password), 200)
        self.read(self.event_for(revoke), self.expected_refs(2, [obj('user', user), obj('session', sid)]), second)
        self.restart(); second.server = self.server
        public = self.read(self.event_for(reset), self.expected_refs(1, [obj('user', user)]), second)
        self.assertNotIn(new, json.dumps(public)); self.assertNotIn('passwordReset', json.dumps(public['context']))

    def test_55_atomic_password_and_session(self):
        self.initialize()
        for table in ('audit_context', 'audit_context_object'):
            for kind in ('password', 'session'):
                for cancel in (False, True):
                    user, session = self.add_user('atomic55-' + uid())
                    sid = self.sid(session); password = secrets.token_urlsafe(32)
                    path = f'/api/v1/admin/users/{user}/password' if kind == 'password' else f'/api/v1/admin/users/{user}/sessions/{sid}/revoke'
                    body = {} if cancel or kind == 'session' else {'password': password}
                    revision, key = self.house_revision(), uid()
                    self.trigger(table, second=kind == 'session')
                    before = self.durable(); self.write(path, body, cancel=cancel, key=key, revision=revision, status=503)
                    self.assertEqual(before, self.durable()); self.expect(session.request('GET', '/api/v1/me'), 200)
                    self.untrigger(table); self.write(path, body, cancel=cancel, key=key, revision=revision)
                    relation = 'intendedTarget' if cancel else 'target'
                    objects = [obj('user', user, relation)] + ([obj('session', sid, relation)] if kind == 'session' else [])
                    self.recorded(key, revision, objects, cancel)
                    self.expect(session.request('GET', '/api/v1/me'), 200 if cancel else 401)

    def test_55_migration_legacy_four_and_atomic_007(self):
        self.initialize(baseline=True)
        create, made = self.write('/api/v1/admin/users', {'username': 'legacy-seven', 'password': self.password}, status=201)
        user = made['resource']['id']
        state, _ = self.write(f'/api/v1/admin/users/{user}/state', {'active': True})
        cancel_create, _ = self.write('/api/v1/admin/users', {'username': 'old-cancel'}, cancel=True, revision=1)
        cancel_state, _ = self.write(f'/api/v1/admin/users/{uid()}/state', {'active': False}, cancel=True, revision=1)
        old = {key: self.expect(self.context(self.event_for(key)), 200).json() for key in (create, state, cancel_create, cancel_state)}
        tables, _ = self.table_digest(self.db)
        tables = [table for table in tables if table != 'audit_context']
        before = self.table_digest(self.db, tables)[1]
        legacy_context_sql = "SELECT md5(COALESCE(jsonb_agg(to_jsonb(t)-ARRAY['scope_id','customer_id','customer_revision_before','customer_revision_after'] ORDER BY event_id)::text,'')) FROM audit_context t"
        old_context = self.lab.sql(self.db, legacy_context_sql)
        history = self.lab.sql(self.db, 'SELECT row_to_json(t) FROM schema_migration t ORDER BY version')
        self.server.close()
        # Collision after ADD COLUMN and replacement of the scope enum must roll back all of them.
        self.lab.sql(self.db, 'ALTER TABLE audit_context ADD CONSTRAINT audit_context_scope_customer_check CHECK (true)')
        self.assertNotEqual(self.migration().returncode, 0)
        self.assertEqual(before, self.table_digest(self.db, tables)[1])
        self.assertEqual(self.lab.sql(self.db, "SELECT max(version) FROM schema_migration; SELECT count(*) FROM information_schema.columns WHERE table_name='audit_context' AND column_name='scope_id'"), '6\n0')
        self.lab.sql(self.db, 'ALTER TABLE audit_context DROP CONSTRAINT audit_context_scope_customer_check')
        self.assertEqual(self.migration().returncode, 0)
        self.assertEqual(before, self.table_digest(self.db, tables)[1])
        self.assertEqual(old_context, self.lab.sql(self.db, legacy_context_sql))
        self.assertEqual(history, self.lab.sql(self.db, 'SELECT row_to_json(t) FROM schema_migration t WHERE version<=6 ORDER BY version'))
        history7 = self.lab.sql(self.db, 'SELECT row_to_json(t) FROM schema_migration t ORDER BY version')
        self.assertEqual(self.migration().returncode, 0)
        self.assertEqual(history7, self.lab.sql(self.db, 'SELECT row_to_json(t) FROM schema_migration t ORDER BY version'))
        self.lab.grant_runtime(self.db); self.server = self.lab.start_server(self.db, dll=self.dll, frontend=self.frontend); self.admin.server = self.server
        for key, prior in old.items():
            now = self.expect(self.context(self.event_for(key)), 200).json()
            prior['context'].update(customerRevisionBefore=None, customerRevisionAfter=None)
            self.assertEqual(now, prior)
        before = self.durable()
        self.write('/api/v1/admin/users', {'username': 'legacy-seven', 'password': self.password}, key=create, revision=1, status=201)
        self.assertEqual(before, self.durable())


    def test_56_flow_group_creations(self):
        self.initialize()
        for path, kind in [('user-groups', 'userGroup'), ('customer-groups', 'customerGroup')]:
            route = '/api/v1/admin/' + path; before = self.house_revision()
            body = {'name': kind + ' e\u0301 <b>😀</b>'}
            key, result = self.write(route, body, status=201)
            self.recorded(key, before, [obj(kind, result['resource']['id'])])
            snapshot = self.durable(); self.assertEqual(self.write(route, body, key=key, revision=before, status=201)[1], result)
            self.write(route, {'name': 'conflict'}, key=key, revision=before, status=409)
            self.write(route, {'name': 'stale'}, revision=before, status=412)
            self.assertEqual(snapshot, self.durable())
            cancel_key, cancelled = self.write(route, {'name': 'cancelled group'}, cancel=True, revision=1)
            self.recorded(cancel_key, before + 1, [obj('systemhaus', self.house, 'intendedTarget')], True)
            snapshot = self.durable()
            self.assertEqual(self.write(route, {'name': 'cancelled group'}, cancel=True, key=cancel_key, revision=1)[1], cancelled)
            self.write(route, {'name': 'cancelled group'}, key=cancel_key, revision=1, status=409)
            self.assertEqual(snapshot, self.durable())
            # Invalid-name fences retain only House, not a fabricated group/name.
            invalid, _ = self.write(route, {'name': '\n'}, cancel=True, revision=1)
            self.recorded(invalid, before + 1, [obj('systemhaus', self.house, 'intendedTarget')], True)
        second = Client(self.server); self.expect(second.login('qa-admin', self.password), 200)
        self.restart(); second.server = self.server
        self.read(self.event_for(key), self.expected_refs(before, [obj(kind, result['resource']['id'])]), second)

    def test_56_atomic_group_creations(self):
        self.initialize()
        for table in ('audit_context', 'audit_context_object'):
            for path, kind in [('user-groups', 'userGroup'), ('customer-groups', 'customerGroup')]:
                for cancel in (False, True):
                    route = '/api/v1/admin/' + path; body = {'name': 'atomic-' + uid()}
                    before, key = self.house_revision(), uid(); self.trigger(table)
                    snapshot = self.durable(); self.write(route, body, cancel=cancel, key=key, revision=before, status=503)
                    self.assertEqual(snapshot, self.durable()); self.untrigger(table)
                    _, result = self.write(route, body, cancel=cancel, key=key, revision=before, status=200 if cancel else 201)
                    identity = self.house if cancel else result['resource']['id']
                    self.recorded(key, before, [obj('systemhaus' if cancel else kind, identity, 'intendedTarget' if cancel else 'target')], cancel)


    def member_fixture(self, customer=False):
        group = uid()
        if customer:
            self.lab.sql(self.db, f"INSERT INTO customer_group VALUES('{group}','{self.house}','Synthetic member fixture')")
            member = self.customer('Member fixture')['id']
        else:
            self.lab.sql(self.db, f"INSERT INTO user_group VALUES('{group}','{self.house}','Synthetic member fixture')")
            member, _ = self.add_user('member-' + uid())
        return group, member

    def test_57_flow_memberships(self):
        self.initialize()
        for customer in (False, True):
            group, member = self.member_fixture(customer)
            group_kind, member_kind = ('customerGroup', 'customer') if customer else ('userGroup', 'user')
            route = f'/api/v1/admin/{"customer-groups" if customer else "user-groups"}/{group}/members'
            field = 'customerId' if customer else 'userId'
            for assigned in (True, True, False):
                before = self.house_revision(); body = {field: member, 'assigned': assigned}
                key, result = self.write(route, body)
                self.recorded(key, before, [obj(group_kind, group), obj(member_kind, member, 'member')])
                snapshot = self.durable()
                self.assertEqual(self.write(route, body, key=key, revision=before)[1], result)
                self.write(route, body | {'assigned': not assigned}, key=key, revision=before, status=409)
                self.assertEqual(snapshot, self.durable())
            missing_group, missing_member = uid(), uid()
            missing_route = route.replace(group, missing_group); body = {field: missing_member, 'assigned': True}
            before = self.house_revision(); cancelled, _ = self.write(missing_route, body, cancel=True, revision=1)
            self.recorded(cancelled, before, [obj(group_kind, missing_group, 'intendedTarget'), obj(member_kind, missing_member, 'intendedMember')], True)
            snapshot = self.durable(); self.write(missing_route, body, key=cancelled, revision=1, status=409)
            self.write(route, {field: member, 'assigned': True}, revision=1, status=412)
            self.assertEqual(snapshot, self.durable())
            # A valid enum on the wrong side is still incoherent and cannot be published.
            event = self.event_for(key)
            self.lab.sql(self.db, f"UPDATE audit_context_object SET relation='intendedMember' WHERE event_id='{event}' AND position=2")
            self.read(event, self.not_recorded())
            self.lab.sql(self.db, f"UPDATE audit_context_object SET relation='member' WHERE event_id='{event}' AND position=2")
        second = Client(self.server); self.expect(second.login('qa-admin', self.password), 200)
        self.restart(); second.server = self.server
        self.read(self.event_for(cancelled), self.expected_refs(before,
            [obj(group_kind, missing_group, 'intendedTarget'), obj(member_kind, missing_member, 'intendedMember')], True), second)

    def test_57_atomic_memberships(self):
        self.initialize()
        for table in ('audit_context', 'audit_context_object'):
            for customer in (False, True):
                for cancel in (False, True):
                    group, member = self.member_fixture(customer)
                    route = f'/api/v1/admin/{"customer-groups" if customer else "user-groups"}/{group}/members'
                    body = {'customerId' if customer else 'userId': member, 'assigned': True}
                    before, key = self.house_revision(), uid(); self.trigger(table, second=True)
                    snapshot = self.durable(); self.write(route, body, cancel=cancel, key=key, revision=before, status=503)
                    self.assertEqual(snapshot, self.durable()); self.untrigger(table)
                    self.write(route, body, cancel=cancel, key=key, revision=before)
                    self.recorded(key, before, [obj('customerGroup' if customer else 'userGroup', group, 'intendedTarget' if cancel else 'target'),
                        obj('customer' if customer else 'user', member, 'intendedMember' if cancel else 'member')], cancel)


    def grant_fixture(self):
        user, _ = self.add_user('grant-' + uid())
        group = self.user_group(user)
        customer = self.customer('Grant scope')['id']; customers = self.customer_group()
        return group, customer, customers

    def test_58_flow_grants(self):
        self.initialize(); group, customer, customers = self.grant_fixture()
        route = f'/api/v1/admin/user-groups/{group}/grants'
        for scope, target in [('systemhaus', None), ('customer', customer), ('customerGroup', customers)]:
            grant = uid(); body = {'grantId': grant, 'capability': 'inventory.read', 'scope': scope, 'targetId': target, 'assigned': True}
            refs = [obj('userGroup', group), obj('grant', grant), obj(scope, target or self.house, 'scope')]
            before = self.house_revision(); key, result = self.write(route, body)
            self.recorded(key, before, refs)
            noop_before = self.house_revision(); noop, _ = self.write(route, body)
            self.recorded(noop, noop_before, refs)
            removed_before = self.house_revision(); removed, _ = self.write(route, body | {'assigned': False})
            self.recorded(removed, removed_before, refs)
            snapshot = self.durable(); self.assertEqual(self.write(route, body, key=key, revision=before)[1], result)
            self.assertEqual(snapshot, self.durable())
            self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM permission_grant WHERE id='{grant}'"), '0')
            self.recorded(key, before, refs)  # Deleted grant remains a valid historical direct reference.
            missing_group, missing_grant = uid(), uid(); missing_target = None if scope == 'systemhaus' else uid()
            missing_route = route.replace(group, missing_group)
            missing_body = body | {'grantId': missing_grant, 'targetId': missing_target}
            cancel_before = self.house_revision(); cancel_key, _ = self.write(missing_route, missing_body, cancel=True, revision=1)
            cancel_refs = [obj('userGroup', missing_group, 'intendedTarget'), obj('grant', missing_grant, 'intendedTarget'),
                obj(scope, missing_target or self.house, 'intendedScope')]
            self.recorded(cancel_key, cancel_before, cancel_refs, True)
            snapshot = self.durable(); self.write(missing_route, missing_body, key=cancel_key, revision=1, status=409)
            self.write(route, body | {'grantId': uid()}, revision=1, status=412)
            self.assertEqual(snapshot, self.durable())
        second = Client(self.server); self.expect(second.login('qa-admin', self.password), 200)
        self.restart(); second.server = self.server
        self.read(self.event_for(cancel_key), self.expected_refs(cancel_before, cancel_refs, True), second)

    def test_58_atomic_grants(self):
        self.initialize(); group, _, customers = self.grant_fixture()
        route = f'/api/v1/admin/user-groups/{group}/grants'
        capabilities = iter(('inventory.read', 'inventory.edit', 'customer.manage', 'systemhaus.read'))
        for table in ('audit_context', 'audit_context_object'):
            for cancel in (False, True):
                grant, key = uid(), uid()
                # Each variant needs a valid fresh intent: a successful prior variant
                # must not reject the next at grant_exists before reaching its trigger.
                body = {'grantId': grant, 'capability': next(capabilities), 'scope': 'customerGroup', 'targetId': customers, 'assigned': True}
                before = self.house_revision(); self.trigger(table, position=3)
                snapshot = self.durable(); self.write(route, body, cancel=cancel, key=key, revision=before, status=503)
                self.assertEqual(snapshot, self.durable()); self.untrigger(table)
                self.write(route, body, cancel=cancel, key=key, revision=before)
                self.recorded(key, before, [obj('userGroup', group, 'intendedTarget' if cancel else 'target'),
                    obj('grant', grant, 'intendedTarget' if cancel else 'target'),
                    obj('customerGroup', customers, 'intendedScope' if cancel else 'scope')], cancel)


    def name_write(self, action, name, customer=None, revision=None, key=None, status=200):
        key = key or uid()
        path = '/api/v1/systemhaus' if action == 'systemhaus.rename' else '/api/v1/customers' + ('/' + customer if customer else '')
        if revision is None:
            revision = int(self.lab.sql(self.db, f"SELECT revision FROM customer WHERE id='{customer}'")) if customer else self.house_revision()
        response = self.mutate(self.admin, 'POST' if action == 'customer.create' else 'PUT', path, name, revision, key)
        return key, self.expect(response, status).json()

    def test_59_flow_names(self):
        self.initialize()
        name = 'Nombre e\u0301 <b>😀</b>'
        house_before = self.house_revision(); house_key, result = self.name_write('systemhaus.rename', name)
        self.recorded(house_key, house_before, [obj('systemhaus', self.house)])
        before = self.durable(); self.assertEqual(self.name_write('systemhaus.rename', name, revision=house_before, key=house_key)[1], result)
        self.assertEqual(before, self.durable())
        noop_before = self.house_revision(); noop, _ = self.name_write('systemhaus.rename', name)
        self.recorded(noop, noop_before, [obj('systemhaus', self.house)])
        create_before = self.house_revision(); create_key, created = self.name_write('customer.create', name, status=201)
        customer = created['resource']['id']
        self.recorded(create_key, create_before, [obj('customer', customer)], customer=customer, customer_after=1)
        before = self.durable(); self.assertEqual(self.name_write('customer.create', name, revision=create_before, key=create_key, status=201)[1], created)
        self.assertEqual(before, self.durable())
        rename_before = self.house_revision(); rename_key, renamed = self.name_write('customer.rename', 'Otro Ω', customer)
        expected = self.expected_refs(rename_before, [obj('customer', customer)], customer=customer, customer_before=1, customer_after=2)
        self.read(self.event_for(rename_key), expected)
        noop_before = self.house_revision(); noop, _ = self.name_write('customer.rename', 'Otro Ω', customer)
        self.recorded(noop, noop_before, [obj('customer', customer)], customer=customer, customer_before=2, customer_after=3)
        before = self.durable(); self.assertEqual(self.name_write('customer.rename', 'Otro Ω', customer, revision=1, key=rename_key)[1], renamed)
        self.name_write('customer.rename', 'Stale', customer, revision=1, status=412)
        self.name_write('customer.rename', 'Conflict', customer, revision=1, key=rename_key, status=409)
        self.assertEqual(before, self.durable())
        # Existing46 retains its exact before/after name and customer revision projection.
        detail = self.expect(self.admin.request('GET', '/api/v1/admin/audit/' + self.event_for(rename_key)), 200).json()['detail']
        self.assertEqual(detail['before'], {'name': name, 'revision': 1}); self.assertEqual(detail['after'], {'name': 'Otro Ω', 'revision': 2})
        # Point regression of the four original52/54 captures, using HTTP writes on the final DLL.
        legacy_name = 'legacy-final-' + uid()
        legacy_before = self.house_revision()
        legacy_create, made = self.write('/api/v1/admin/users', {'username': legacy_name, 'password': self.password}, status=201)
        user = made['resource']['id']; self.recorded(legacy_create, legacy_before, [obj('user', user)])
        administrative = self.expect(self.admin.request('GET', '/api/v1/admin/audit/' + self.event_for(legacy_create) + '/administrative-detail'), 200).json()['detail']
        self.assertEqual(administrative, {'status': 'available', 'fields': [
            {'field': 'userId', 'type': 'uuid', 'before': None, 'after': user},
            {'field': 'userName', 'type': 'userName', 'before': None, 'after': legacy_name},
            {'field': 'active', 'type': 'boolean', 'before': None, 'after': 'true'}]})
        legacy_before = self.house_revision()
        legacy_state, _ = self.write(f'/api/v1/admin/users/{user}/state', {'active': False})
        self.recorded(legacy_state, legacy_before, [obj('user', user)])
        legacy_before = self.house_revision()
        legacy_cancel, _ = self.write('/api/v1/admin/users', {'username': 'cancel-final'}, cancel=True, revision=1)
        self.recorded(legacy_cancel, legacy_before, [obj('systemhaus', self.house, 'intendedTarget')], True)
        target = uid()
        legacy_cancel_state, _ = self.write(f'/api/v1/admin/users/{target}/state', {'active': False}, cancel=True, revision=1)
        self.recorded(legacy_cancel_state, legacy_before, [obj('user', target, 'intendedTarget')], True)
        second = Client(self.server); self.expect(second.login('qa-admin', self.password), 200)
        self.restart(); second.server = self.server
        self.read(self.event_for(rename_key), expected, second)

    def test_59_atomic_names(self):
        self.initialize()
        customer = self.customer('Atomic name')['id']
        for table in ('audit_context', 'audit_context_object'):
            for action in ('systemhaus.rename', 'customer.create', 'customer.rename'):
                before, key = self.house_revision(), uid()
                customer_before = int(self.lab.sql(self.db, f"SELECT revision FROM customer WHERE id='{customer}'"))
                target = customer if action == 'customer.rename' else None
                revision = customer_before if target else before
                name = 'Atomic ' + uid()
                self.trigger(table); snapshot = self.durable()
                self.name_write(action, name, target, revision=revision, key=key, status=503)
                self.assertEqual(snapshot, self.durable()); self.untrigger(table)
                # Same request uses the identical name/metadata; no old partial operation exists.
                _, made = self.name_write(action, name, target, revision=revision, key=key,
                    status=201 if action == 'customer.create' else 200)
                identity = made['resource']['id']
                self.recorded(key, before, [obj('systemhaus' if action == 'systemhaus.rename' else 'customer', identity)],
                    customer=identity if action != 'systemhaus.rename' else None,
                    customer_before=customer_before if action == 'customer.rename' else None,
                    customer_after=customer_before + 1 if action == 'customer.rename' else 1 if action == 'customer.create' else None)

    def test_59_authority_customer_coherence_and_redaction(self):
        self.initialize(); customer = self.customer('Scoped historical')['id']
        user, scoped = self.add_user('scoped-history'); group = self.user_group(user)
        self.grant(group, 'inventory.read', customer=customer); self.grant(group, 'customer.manage', customer=customer)
        key = uid()
        self.expect(self.mutate(scoped, 'PUT', '/api/v1/customers/' + customer, 'Scoped Ω', 1, key), 200)
        event = self.event_for(key)
        expected = self.expected_refs(2, [obj('customer', customer)], customer=customer, customer_before=1, customer_after=2)
        expected['actorId'] = user
        self.read(event, expected)
        self.expect(self.context('bad', scoped), 403, 'forbidden')
        self.expect(self.context(event, Client(self.server)), 401, 'authentication_required')
        for invalid in ('bad', str(uuid.UUID(int=0)), event.replace('-', '')):
            self.expect(self.context(invalid), 422, 'request_invalid')
        foreign, _, _ = self.foreign(); foreign_event = uid()
        self.lab.sql(self.db, f"""INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,after_json)
            SELECT '{foreign_event}',systemhaus_id,id,'{uid()}','customer.rename','{uid()}','{{}}' FROM app_user WHERE id='{foreign}'""")
        self.assertEqual(self.expect(self.context(foreign_event), 404).json(), self.expect(self.context(uid()), 404).json())
        # Valid database types and succession for create are incoherent for a rename.
        self.lab.sql(self.db, f"UPDATE audit_context SET customer_revision_before=NULL,customer_revision_after=1 WHERE event_id='{event}'")
        self.read(event, self.not_recorded())
        self.lab.sql(self.db, f"UPDATE audit_context SET customer_revision_before=1,customer_revision_after=2 WHERE event_id='{event}'")
        marker = 'synthetic-context-secret-not-published'
        self.lab.sql(self.db, f"UPDATE audit_event SET after_json=after_json||jsonb_build_object('password','{marker}','token','{marker}') WHERE id='{event}'")
        public = self.read(event, expected); self.assertNotIn(marker, json.dumps(public))
        secrets_in_db = self.lab.sql(self.db, 'SELECT password_hash FROM app_user UNION ALL SELECT token_hash FROM app_session UNION ALL SELECT csrf_hash FROM app_session').splitlines()
        self.assertTrue(all(secret not in json.dumps(public) for secret in secrets_in_db), 'Identity secret leaked')
        self.expired_wait(lambda: self.admin.request('GET', '/api/v1/admin/audit/' + event + '/context'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family', choices=['55', '56', '57', '58', '59', 'final'], required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--frontend', type=Path, required=True)
    parser.add_argument('--baseline-dll', type=Path, required=True)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    names = [name for name in unittest.defaultTestLoader.getTestCaseNames(ContextFamiliesPostgres)
        if (name.startswith('test_' + args.family + '_') if args.family != 'final' else
            any(name.startswith('test_' + family + '_') for family in ('55', '56', '57', '58', '59'))
            and (bool(args.case) or '_flow_' in name))]
    if args.case:
        if set(args.case) - set(names): raise ValueError('Unknown family case')
        names = [name for name in names if name in args.case]
    if not names: raise ValueError('No selected family cases')
    args.evidence.mkdir(parents=True, exist_ok=False)
    args.dll = args.dll.resolve(); args.frontend = args.frontend.resolve(); args.baseline_dll = args.baseline_dll.resolve()
    files = list((WORKSPACE/'development/server/src/RackClick.Server').glob('*.cs')) + list((WORKSPACE/'development/server/database').glob('*.sql'))
    files += [Path(__file__).resolve(), WORKSPACE/'development/server/tests/pg_support.py']
    def hashes(): return {path.relative_to(WORKSPACE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    def distribution(path): return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}
    original = hashes(); dll = hashlib.sha256(args.dll.read_bytes()).hexdigest()
    immutable = {'baseline': distribution(args.baseline_dll.parent), 'frontend': distribution(args.frontend)}
    if immutable['baseline']['RackClick.Server.dll'] != '919fb34cfb3cc5a030bab88130420479f774d077e7fe811ecee4900ab782c3ee':
        raise RuntimeError('Expected immutable schema6 baseline54 DLL')
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(), 'family': args.family,
        'dllSha256': dll, 'frontendSha256': immutable['frontend']['app.js'], 'sourceHashes': original,
        'actualQaOpened': False, 'selectedCases': names, 'schemaVersion': 7}
    lab = Lab('context-families-' + args.family)
    ContextFamiliesPostgres.dll, ContextFamiliesPostgres.frontend, ContextFamiliesPostgres.baseline_dll = args.dll, args.frontend, args.baseline_dll
    with lab, (args.evidence/'tests.log').open('w', encoding='utf-8') as output:
        ContextFamiliesPostgres.lab = lab
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(
            unittest.TestSuite(ContextFamiliesPostgres(name) for name in names))
        report.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    report.update(labStopped=not lab.running, serversStopped=all(s.process.poll() is not None for s in lab.servers),
        inputsUnchanged=original == hashes() and dll == hashlib.sha256(args.dll.read_bytes()).hexdigest(),
        immutableUnchanged=immutable == {'baseline': distribution(args.baseline_dll.parent), 'frontend': distribution(args.frontend)})
    (args.evidence/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return 0 if all(report[key] for key in ('successful', 'labStopped', 'serversStopped', 'inputsUnchanged', 'immutableUnchanged')) else 1


if __name__ == '__main__': sys.exit(main())
