"""Native Windows/PostgreSQL foundation QA. Run from any directory with Python 3.

This is development evidence, not a product installer or the historical R3 suite.
Each test creates a new database; all local secrets stay in pg_support's private
lab. Administrative users/groups/revocations are explicit SQL fixtures because
the corresponding administration API is not implemented yet.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import subprocess
import sys
import threading
import time
import unittest
import uuid

from pg_support import Client, DEFAULT_DLL, Lab, NO_WINDOW, WORKSPACE, literal


def uid():
    return str(uuid.uuid4())


class FoundationPostgres(unittest.TestCase):
    lab = None

    def setUp(self):
        self.db = self.lab.create_database(self._testMethodName)
        self.password = secrets.token_urlsafe(32)
        self.server = None

    def initialize(self, username='qa-admin'):
        result = self.lab.bootstrap(self.db, username, self.password)
        self.assertEqual(result.returncode, 0, 'Bootstrap must succeed; raw output stays private')
        self.lab.grant_runtime(self.db)
        self.house = self.lab.sql(self.db, 'SELECT id FROM systemhaus')
        self.admin_id = self.lab.sql(self.db, 'SELECT id FROM app_user')
        self.server = self.lab.start_server(self.db)
        client = Client(self.server)
        response = client.login(username, self.password)
        self.expect(response, 200)
        self.admin = client
        return client

    def tearDown(self):
        if self.server:
            self.server.close()

    def expect(self, response, status, error=None):
        # Never include whole HTTP responses: login/me contain CSRF tokens.
        self.assertEqual(response.status, status, 'Unexpected HTTP status')
        if error is not None:
            self.assertEqual(response.json().get('error'), error)
        return response

    def house_revision(self, client=None):
        response = self.expect((client or self.admin).request('GET', '/api/v1/systemhaus'), 200)
        return response.json()['revision']

    def mutate(self, client, method, path, name, revision, key=None):
        return client.request(method, path, {'name': name},
                              {'If-Match': f'"{revision}"', 'Idempotency-Key': key or uid()})

    def customer(self, name):
        response = self.mutate(self.admin, 'POST', '/api/v1/customers', name, self.house_revision())
        return self.expect(response, 201).json()['resource']

    def add_user(self, name, admin=False):
        user_id = uid()
        # Clone a synthetic password hash inside DB, never emit it to logs.
        self.lab.sql(self.db, f"INSERT INTO app_user(id,systemhaus_id,username,password_hash) "
                     f"SELECT '{user_id}',systemhaus_id,{literal(name)},password_hash "
                     f"FROM app_user WHERE id='{self.admin_id}';")
        if admin:
            self.lab.sql(self.db, f"INSERT INTO user_group_member SELECT systemhaus_id,'{user_id}',group_id "
                         f"FROM user_group_member WHERE user_id='{self.admin_id}';")
        client = Client(self.server)
        self.expect(client.login(name, self.password), 200)
        return user_id, client

    def user_group(self, user_id, name='fixture user group'):
        group = uid()
        self.lab.sql(self.db, f"INSERT INTO user_group VALUES('{group}','{self.house}',{literal(name)}); "
                     f"INSERT INTO user_group_member VALUES('{self.house}','{user_id}','{group}');")
        return group

    def grant(self, group, capability, customer=None, customer_group=None):
        def sql_id(value):
            return literal(value) if value else 'NULL'
        self.lab.sql(self.db, f"INSERT INTO permission_grant VALUES('{uid()}','{self.house}','{group}',"
                     f"{literal(capability)},{sql_id(customer)},{sql_id(customer_group)});")

    def permission_fixture(self):
        self.initialize()
        a, b, hidden = [self.customer(name) for name in ('Visible A', 'Visible B', 'Hidden C')]
        user_id, client = self.add_user('qa-scoped')
        direct = self.user_group(user_id, 'Direct readers')
        grouped = self.user_group(user_id, 'Group technicians')
        resource_group = uid()
        self.lab.sql(self.db, f"INSERT INTO customer_group VALUES('{resource_group}','{self.house}','Customer scope B'); "
                     f"INSERT INTO customer_group_member VALUES('{self.house}','{resource_group}','{b['id']}');")
        self.grant(direct, 'systemhaus.read')
        self.grant(direct, 'inventory.read', customer=a['id'])
        self.grant(grouped, 'inventory.read', customer_group=resource_group)
        self.grant(grouped, 'customer.manage', customer_group=resource_group)
        self.grant(grouped, 'inventory.edit', customer_group=resource_group)
        self.grant(direct, 'customer.manage', customer=hidden['id'])
        return user_id, client, a, b, hidden, direct, grouped, resource_group

    def test_d007_bootstrap_login_51_supplementary_unicode(self):
        self.initialize('\U0001f9f0' * 51)
        response = self.expect(self.admin.request('GET', '/api/v1/me'), 200)
        self.assertEqual(response.json()['user']['userName'], '\U0001f9f0' * 51)

    def test_d007_bootstrap_login_100_supplementary_unicode(self):
        self.initialize('\U0001f9f0' * 100)
        self.assertEqual(self.lab.sql(self.db, 'SELECT length(username) FROM app_user'), '100')

    def test_d007_bootstrap_login_one_and_100_bmp_boundaries(self):
        for index, username in enumerate(('Ä', 'Ö' * 100)):
            with self.subTest(boundary=len(username)):
                if index:
                    self.server.close()
                    self.db = self.lab.create_database('username-boundary-100')
                self.initialize(username)
                self.expect(Client(self.server).login('  ' + username.lower() + '  ', self.password), 200)

    def test_d007_bootstrap_rejects_empty_overlimit_controls(self):
        invalid = ('', '   ', 'x' * 101, '\U0001f9f0' * 101, 'qa\tadmin', 'qa\x7fadmin')
        for index, username in enumerate(invalid):
            with self.subTest(case=index):
                db = self.db if not index else self.lab.create_database(f'invalid-username-{index}')
                result = self.lab.bootstrap(db, username, self.password)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('username_invalid', result.stderr)
                self.assertEqual(self.lab.sql(db, "SELECT to_regclass('public.systemhaus') IS NULL"), 't')

    def test_d007_login_invalid_unicode_limits_no_session(self):
        self.initialize()
        count = self.lab.sql(self.db, 'SELECT count(*) FROM app_session')
        for username in ('', ' ', 'x' * 101, '\U0001f9f0' * 101, 'qa\tadmin', 'qa\x7fadmin'):
            self.expect(Client(self.server).login(username, self.password), 401, 'login_failed')
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM app_session'), count)

    def test_login_malformed_json_unicode_rejected_without_session(self):
        self.initialize()
        count = self.lab.sql(self.db, 'SELECT count(*) FROM app_session')
        # A lone surrogate cannot form a valid Unicode scalar. ASP.NET rejects
        # the JSON DTO at binding (400), before username policy runs (401).
        self.expect(Client(self.server).login('\ud800', self.password), 400)
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM app_session'), count)

    def test_username_no_silent_nfc_alias(self):
        self.initialize('Caf\u00e9')
        self.expect(Client(self.server).login('Cafe\u0301', self.password), 401, 'login_failed')
        self.expect(Client(self.server).login('  CAF\u00c9  ', self.password), 200)

    def test_bootstrap_repeat_preserves_identity_and_data(self):
        self.initialize()
        created = self.customer('Preserved client')
        before = self.lab.sql(self.db, 'SELECT id::text || name || revision::text FROM systemhaus; '
                             'SELECT id::text || username FROM app_user; SELECT count(*) FROM audit_event')
        result = self.lab.bootstrap(self.db, 'replacement-admin', secrets.token_urlsafe(32))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('already_initialized', result.stderr)
        self.assertEqual(self.lab.sql(self.db, 'SELECT id::text || name || revision::text FROM systemhaus; '
                         'SELECT id::text || username FROM app_user; SELECT count(*) FROM audit_event'), before)
        self.assertEqual(self.admin.request('GET', '/api/v1/customers').json()[0]['id'], created['id'])

    def test_persistence_restart_other_user_session_and_sql(self):
        self.initialize()
        self.expect(self.mutate(self.admin, 'PUT', '/api/v1/systemhaus', 'Systemhaus QA \u00d1', 1), 200)
        created = self.customer('Cliente persistente \U0001f9f0')
        self.expect(self.mutate(self.admin, 'PUT', '/api/v1/customers/' + created['id'], 'Cliente final', 1), 200)
        _, second = self.add_user('qa-second', admin=True)
        self.server.close()
        self.server = self.lab.start_server(self.db)
        second.server = self.server
        self.assertEqual(self.expect(second.request('GET', '/api/v1/systemhaus'), 200).json()['name'], 'Systemhaus QA \u00d1')
        customers = self.expect(second.request('GET', '/api/v1/customers'), 200).json()
        self.assertEqual([(c['id'], c['name'], c['revision']) for c in customers], [(created['id'], 'Cliente final', 2)])
        self.assertEqual(self.lab.sql(self.db, "SELECT name || ':' || revision::text FROM customer"), 'Cliente final:2')
        fresh = Client(self.server)
        self.expect(fresh.login('qa-second', self.password), 200)
        self.assertEqual(self.expect(fresh.request('GET', '/api/v1/customers'), 200).json(), customers)

    def test_customer_isolation_direct_and_group_union_read_write(self):
        _, client, a, b, hidden, *_ = self.permission_fixture()
        visible = self.expect(client.request('GET', '/api/v1/customers'), 200).json()
        self.assertEqual({item['id'] for item in visible}, {a['id'], b['id']})
        self.expect(self.mutate(client, 'PUT', '/api/v1/customers/' + a['id'], 'Denied A', 1), 403, 'forbidden')
        self.expect(self.mutate(client, 'PUT', '/api/v1/customers/' + hidden['id'], 'Denied hidden', 1), 404, 'not_found')
        self.expect(self.mutate(client, 'PUT', '/api/v1/customers/' + uid(), 'Absent', 1), 404, 'not_found')
        self.expect(self.mutate(client, 'PUT', '/api/v1/customers/' + b['id'], 'Allowed B', 1), 200)
        self.assertEqual(self.lab.sql(self.db, f"SELECT name FROM customer WHERE id='{hidden['id']}'"), 'Hidden C')
        self.expect(self.mutate(client, 'POST', '/api/v1/customers', 'Denied create', self.house_revision()), 403)
        self.expect(self.mutate(client, 'PUT', '/api/v1/systemhaus', 'Denied house', self.house_revision()), 403)

    def test_me_effective_permissions_only_readable_customers_and_own_sources(self):
        _, client, a, b, hidden, direct, grouped, resource_group = self.permission_fixture()
        response = self.expect(client.request('GET', '/api/v1/me'), 200).json()
        self.assertTrue(response['csrf'] == client.csrf, 'me must renew the same session CSRF without logging it')
        permissions = response['permissions']
        self.assertEqual(permissions['systemhausCapabilities'], ['systemhaus.read'])
        customers = {row['customerId']: set(row['capabilities']) for row in permissions['customers']}
        self.assertEqual(set(customers), {a['id'], b['id']})
        self.assertEqual(customers[a['id']], {'inventory.read', 'systemhaus.read'})
        self.assertEqual(customers[b['id']], {'inventory.read', 'inventory.edit', 'customer.manage', 'systemhaus.read'})
        self.assertEqual({row['userGroupId'] for row in permissions['sources']}, {direct, grouped})
        self.assertTrue(any(row['scopeType'] == 'customerGroup' and row['scopeId'] == resource_group
                            for row in permissions['sources']))

    def test_group_membership_revocation_immediate_without_logout(self):
        user, client, a, b, _, _, grouped, _ = self.permission_fixture()
        self.lab.sql(self.db, f"DELETE FROM user_group_member WHERE user_id='{user}' AND group_id='{grouped}'")
        self.assertEqual([row['id'] for row in self.expect(client.request('GET', '/api/v1/customers'), 200).json()], [a['id']])
        self.expect(self.mutate(client, 'PUT', '/api/v1/customers/' + b['id'], 'Revoked', 1), 404)
        self.assertEqual([row['customerId'] for row in client.request('GET', '/api/v1/me').json()['permissions']['customers']], [a['id']])

    def test_customer_group_membership_revocation_and_replay_authorization(self):
        _, client, _, b, _, _, _, resource_group = self.permission_fixture()
        key = uid()
        self.expect(self.mutate(client, 'PUT', '/api/v1/customers/' + b['id'], 'Before revoke', 1, key), 200)
        self.lab.sql(self.db, f"DELETE FROM customer_group_member WHERE group_id='{resource_group}'")
        self.expect(self.mutate(client, 'PUT', '/api/v1/customers/' + b['id'], 'Before revoke', 1, key), 404)
        self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM audit_event WHERE request_id='{key}'"), '1')

    def test_no_membership_me_empty_and_all_customer_reads_filtered(self):
        self.initialize()
        self.customer('Hidden to no groups')
        _, client = self.add_user('qa-no-groups')
        self.assertEqual(self.expect(client.request('GET', '/api/v1/customers'), 200).json(), [])
        self.expect(client.request('GET', '/api/v1/systemhaus'), 403)
        self.assertEqual(client.request('GET', '/api/v1/me').json()['permissions'],
                         {'systemhausCapabilities': [], 'customers': [], 'sources': []})

    def test_logout_invalidates_only_current_session(self):
        self.initialize()
        second = Client(self.server)
        self.expect(second.login('qa-admin', self.password), 200)
        self.expect(self.admin.request('POST', '/api/v1/auth/logout'), 204)
        self.expect(self.admin.request('GET', '/api/v1/me'), 401)
        self.expect(second.request('GET', '/api/v1/me'), 200)
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM app_session'), '1')

    def test_expired_session_rejected(self):
        self.initialize()
        self.lab.sql(self.db, "UPDATE app_session SET expires_at=now()-interval '1 second'")
        self.expect(self.admin.request('GET', '/api/v1/me'), 401)
        self.expect(self.mutate(self.admin, 'PUT', '/api/v1/systemhaus', 'Expired', 1), 401)

    def test_disabled_user_session_and_login_rejected(self):
        self.initialize()
        self.lab.sql(self.db, 'UPDATE app_user SET active=false')
        self.expect(self.admin.request('GET', '/api/v1/me'), 401)
        self.expect(Client(self.server).login('qa-admin', self.password), 401, 'login_failed')
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM app_session'), '1')

    def test_csrf_valid_session_missing_foreign_correct_and_origin(self):
        self.initialize()
        other = Client(self.server)
        self.expect(other.login('qa-admin', self.password), 200)
        headers = {'Cookie': self.admin.cookie, 'Origin': self.server.origin, 'If-Match': '"1"', 'Idempotency-Key': uid()}
        path, body = '/api/v1/systemhaus', {'name': 'CSRF confirmed'}
        self.expect(self.server.request('PUT', path, body, headers), 403, 'csrf_invalid')
        self.expect(self.server.request('PUT', path, body, {**headers, 'X-RackClick-CSRF': other.csrf}), 403, 'csrf_invalid')
        self.expect(self.server.request('PUT', path, body, {**headers, 'X-RackClick-CSRF': self.admin.csrf,
                                                         'Origin': 'http://different.invalid'}), 403, 'origin_invalid')
        no_origin = {k: v for k, v in headers.items() if k != 'Origin'}
        self.expect(self.server.request('PUT', path, body, {**no_origin, 'X-RackClick-CSRF': self.admin.csrf}), 403, 'origin_invalid')
        self.assertEqual(self.lab.sql(self.db, 'SELECT revision FROM systemhaus'), '1')
        self.expect(self.server.request('PUT', path, body, {**headers, 'X-RackClick-CSRF': self.admin.csrf}), 200)
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM audit_event'), '1')

    def test_login_failure_lockout_and_ip_rate_limit(self):
        self.initialize()
        for _ in range(5):
            self.expect(Client(self.server).login('qa-admin', 'incorrect synthetic password'), 401, 'login_failed')
        self.expect(Client(self.server).login('qa-admin', self.password), 401, 'login_failed')
        self.assertEqual(self.lab.sql(self.db, 'SELECT (failed_logins=5 AND locked_until>now()) FROM app_user'), 't')
        for _ in range(3):
            self.expect(Client(self.server).login('qa-absent', self.password), 401)
        self.expect(Client(self.server).login('qa-absent', self.password), 429)
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM app_session'), '1')

    def test_revision_required_invalid_stale_and_missing_idempotency_key(self):
        self.initialize()
        body = {'name': 'Invalid request cannot mutate'}
        self.expect(self.admin.request('PUT', '/api/v1/systemhaus', body, {'Idempotency-Key': uid()}), 428, 'revision_required')
        self.expect(self.admin.request('PUT', '/api/v1/systemhaus', body, {'If-Match': '1', 'Idempotency-Key': uid()}), 422, 'revision_invalid')
        self.expect(self.admin.request('PUT', '/api/v1/systemhaus', body, {'If-Match': '"1"'}), 422, 'request_id_invalid')
        self.expect(self.mutate(self.admin, 'PUT', '/api/v1/systemhaus', 'First committed', 1), 200)
        self.expect(self.mutate(self.admin, 'PUT', '/api/v1/systemhaus', 'Stale overwrite', 1), 412, 'revision_conflict')
        self.assertEqual(self.lab.sql(self.db, "SELECT name || ':' || revision::text FROM systemhaus"), 'First committed:2')
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM operation; SELECT count(*) FROM audit_event'), '1\n1')

    def test_idempotent_replay_same_body_different_body_and_revision(self):
        self.initialize()
        key = uid()
        first = self.expect(self.mutate(self.admin, 'POST', '/api/v1/customers', 'One customer', 1, key), 201)
        replay = self.expect(self.mutate(self.admin, 'POST', '/api/v1/customers', 'One customer', 1, key), 201)
        self.assertEqual(replay.json(), first.json())
        self.expect(self.mutate(self.admin, 'POST', '/api/v1/customers', 'Different body', 1, key), 409, 'request_id_reused')
        self.expect(self.mutate(self.admin, 'POST', '/api/v1/customers', 'One customer', 2, key), 409, 'request_id_reused')
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM customer; SELECT count(*) FROM operation; SELECT count(*) FROM audit_event'), '1\n1\n1')

    def test_original_actor_guard_prevents_cross_identity_retry(self):
        self.initialize()
        _, second = self.add_user('qa-other-actor', admin=True)
        headers = {'If-Match': '"1"', 'Idempotency-Key': uid(), 'X-RackClick-Actor': self.admin_id}
        body = {'name': 'Actor bound client'}
        self.expect(second.request('POST', '/api/v1/customers', body, headers), 409, 'actor_changed')
        self.expect(self.admin.request('POST', '/api/v1/customers', body,
                                       {**headers, 'X-RackClick-Actor': 'invalid'}), 422, 'actor_invalid')
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM customer; SELECT count(*) FROM operation; SELECT count(*) FROM audit_event; SELECT revision FROM systemhaus'), '0\n0\n0\n1')
        committed = self.expect(self.admin.request('POST', '/api/v1/customers', body, headers), 201)
        self.expect(second.request('POST', '/api/v1/customers', body, headers), 409, 'actor_changed')
        replay = self.expect(self.admin.request('POST', '/api/v1/customers', body, headers), 201)
        self.assertEqual(committed.json(), replay.json())
        customer = committed.json()['resource']
        for method, path, revision in [('PUT', '/api/v1/systemhaus', 2),
                                       ('PUT', '/api/v1/customers/' + customer['id'], 1)]:
            self.expect(second.request(method, path, {'name': 'Wrong actor rename'},
                                       {**headers, 'If-Match': f'"{revision}"', 'Idempotency-Key': uid()}), 409, 'actor_changed')
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM operation; SELECT count(*) FROM audit_event; SELECT revision FROM systemhaus'), '1\n1\n2')

    def parallel_mutations(self, names, keys):
        barrier = threading.Barrier(len(names))
        def submit(index):
            barrier.wait(timeout=10)
            return self.mutate(self.admin, 'POST', '/api/v1/customers', names[index], 1, keys[index])
        with ThreadPoolExecutor(max_workers=len(names)) as executor:
            return list(executor.map(submit, range(len(names))))

    def test_concurrent_same_revision_exactly_one_commit(self):
        self.initialize()
        responses = self.parallel_mutations(['Concurrent A', 'Concurrent B'], [uid(), uid()])
        self.assertEqual(sorted(r.status for r in responses), [201, 412])
        winner = next(r for r in responses if r.status == 201).json()['resource']
        self.assertEqual(self.lab.sql(self.db, 'SELECT id FROM customer'), winner['id'])
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM customer; SELECT count(*) FROM operation; SELECT count(*) FROM audit_event; SELECT revision FROM systemhaus'), '1\n1\n1\n2')

    def test_concurrent_same_idempotency_key_one_operation(self):
        self.initialize()
        key = uid()
        responses = self.parallel_mutations(['Same request', 'Same request'], [key, key])
        self.assertEqual([r.status for r in responses], [201, 201])
        self.assertEqual(responses[0].json(), responses[1].json())
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM customer; SELECT count(*) FROM operation; SELECT count(*) FROM audit_event; SELECT revision FROM systemhaus'), '1\n1\n1\n2')

    def test_concurrent_same_key_different_body_conflict(self):
        self.initialize()
        key = uid()
        responses = self.parallel_mutations(['Body A', 'Body B'], [key, key])
        self.assertEqual(sorted(r.status for r in responses), [201, 409])
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM operation; SELECT count(*) FROM audit_event'), '1\n1')

    def test_audit_contains_before_after_actor_and_request(self):
        self.initialize()
        created = self.customer('Before name')
        key = uid()
        result = self.expect(self.mutate(self.admin, 'PUT', '/api/v1/customers/' + created['id'], 'After name', 1, key), 200).json()
        row = json.loads(self.lab.sql(self.db, f"SELECT json_build_object('actor',actor_id,'request',request_id,'resource',resource_id,"
                         f"'action',action,'before',before_json,'after',after_json)::text FROM audit_event WHERE request_id='{key}'"))
        self.assertEqual((row['actor'], row['request'], row['resource'], row['action']),
                         (self.admin_id, key, created['id'], 'customer.rename'))
        self.assertEqual(row['before'], created)
        self.assertEqual(row['after'], result['resource'])
        self.assertEqual(row['after']['revision'], 2)
        operation = json.loads(self.lab.sql(self.db, f"SELECT result_json::text FROM operation WHERE request_id='{key}'"))
        self.assertEqual(operation, result)

    def test_audit_failure_rolls_back_customer_revision_operation_and_retry(self):
        self.initialize()
        created = self.customer('Before forced rollback')
        revision = self.house_revision()
        key = uid()
        self.lab.sql(self.db, "CREATE FUNCTION qa_reject_audit() RETURNS trigger LANGUAGE plpgsql AS $$ "
                     "BEGIN RAISE EXCEPTION 'QA injected audit failure'; END $$; "
                     "CREATE TRIGGER qa_reject_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION qa_reject_audit();")
        self.expect(self.mutate(self.admin, 'PUT', '/api/v1/customers/' + created['id'], 'Must rollback', 1, key), 503, 'service_unavailable')
        # Each sql() invocation is a separate psql process/connection after HTTP returned.
        self.assertEqual(self.lab.sql(self.db, f"SELECT name || ':' || revision::text FROM customer WHERE id='{created['id']}'"), 'Before forced rollback:1')
        self.assertEqual(self.lab.sql(self.db, 'SELECT revision FROM systemhaus'), str(revision))
        self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM operation WHERE request_id='{key}'; SELECT count(*) FROM audit_event WHERE request_id='{key}'"), '0\n0')
        self.lab.sql(self.db, 'DROP TRIGGER qa_reject_audit ON audit_event; DROP FUNCTION qa_reject_audit();')
        self.expect(self.mutate(self.admin, 'PUT', '/api/v1/customers/' + created['id'], 'Must rollback', 1, key), 200)
        self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM operation WHERE request_id='{key}'; SELECT count(*) FROM audit_event WHERE request_id='{key}'"), '1\n1')

    def test_operation_failure_rolls_back_prior_audit_and_insert(self):
        self.initialize()
        key = uid()
        self.lab.sql(self.db, "CREATE FUNCTION qa_reject_operation() RETURNS trigger LANGUAGE plpgsql AS $$ "
                     "BEGIN RAISE EXCEPTION 'QA injected operation failure'; END $$; "
                     "CREATE TRIGGER qa_reject_operation BEFORE INSERT ON operation FOR EACH ROW EXECUTE FUNCTION qa_reject_operation();")
        self.expect(self.mutate(self.admin, 'POST', '/api/v1/customers', 'Must not exist', 1, key), 503)
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM customer; SELECT count(*) FROM operation; SELECT count(*) FROM audit_event; SELECT revision FROM systemhaus'), '0\n0\n0\n1')

    def test_runtime_role_separate_minimum_privileges_no_ddl(self):
        self.initialize()
        result = self.lab.sql(self.db, f"SELECT rolname <> '{self.db.owner}' AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolbypassrls FROM pg_roles WHERE rolname='{self.db.runtime}'; "
                              f"SELECT has_database_privilege('{self.db.runtime}',current_database(),'CONNECT') AND NOT has_database_privilege('{self.db.runtime}',current_database(),'CREATE') AND NOT has_database_privilege('{self.db.runtime}',current_database(),'TEMP'); "
                              f"SELECT NOT has_schema_privilege('{self.db.runtime}','public','CREATE'); "
                              f"SELECT bool_and(has_table_privilege('{self.db.runtime}',tablename,'SELECT,INSERT,UPDATE,DELETE')) FROM pg_tables WHERE schemaname='public';")
        self.assertEqual(result, 't\nt\nt\nt')
        self.lab.sql(self.db, f"BEGIN; SET LOCAL ROLE {self.db.runtime}; DO $$ BEGIN "
                     "BEGIN CREATE TABLE public.qa_forbidden_table(id integer); RAISE EXCEPTION 'QA DDL unexpectedly allowed'; "
                     "EXCEPTION WHEN insufficient_privilege THEN NULL; END; "
                     "BEGIN ALTER TABLE public.customer ADD COLUMN qa_forbidden integer; RAISE EXCEPTION 'QA ALTER unexpectedly allowed'; "
                     "EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$; ROLLBACK;", admin=True)

    def test_database_foreign_keys_reject_unknown_scope_and_both_scopes(self):
        self.initialize()
        created = self.customer('Constraint fixture')
        group = self.lab.sql(self.db, 'SELECT id FROM user_group LIMIT 1')
        self.lab.sql(self.db, f"DO $$ BEGIN BEGIN INSERT INTO user_group_member VALUES('{uid()}','{self.admin_id}','{group}'); "
                     "RAISE EXCEPTION 'QA invalid scope accepted'; EXCEPTION WHEN foreign_key_violation THEN NULL; END; END $$;")
        resource_group = uid()
        self.lab.sql(self.db, f"INSERT INTO customer_group VALUES('{resource_group}','{self.house}','Scope fixture'); "
                     f"DO $$ BEGIN BEGIN INSERT INTO permission_grant VALUES('{uid()}','{self.house}','{group}','inventory.read','{created['id']}','{resource_group}'); "
                     "RAISE EXCEPTION 'QA ambiguous scope accepted'; EXCEPTION WHEN check_violation THEN NULL; END; END $$;")

    def validate_schema(self, value, schema, schemas):
        if '$ref' in schema:
            schema = schemas[schema['$ref'].rsplit('/', 1)[-1]]
        if value is None and schema.get('nullable'):
            return
        kind = schema.get('type')
        if kind == 'object':
            self.assertIsInstance(value, dict)
            self.assertTrue(set(schema.get('required', [])) <= set(value), 'DTO missing declared required fields')
            for key, field in schema.get('properties', {}).items():
                if key in value:
                    self.validate_schema(value[key], field, schemas)
        elif kind == 'array':
            self.assertIsInstance(value, list)
            for item in value:
                self.validate_schema(item, schema['items'], schemas)
        elif kind == 'string':
            self.assertIsInstance(value, str)
            if schema.get('format') == 'uuid':
                uuid.UUID(value)
        elif kind == 'integer':
            self.assertIsInstance(value, int)
            self.assertGreaterEqual(value, schema.get('minimum', value))
        if 'enum' in schema:
            self.assertIn(value, schema['enum'])

    def test_openapi_routes_and_live_dtos_align(self):
        self.initialize()
        document = self.expect(self.admin.request('GET', '/api/v1/openapi.json'), 200).json()
        self.assertEqual(document['openapi'], '3.0.3')
        expected = {'/api/v1/auth/login': {'post'}, '/api/v1/auth/logout': {'post'},
                    '/api/v1/me': {'get'}, '/api/v1/openapi.json': {'get'},
                    '/api/v1/systemhaus': {'get', 'put'}, '/api/v1/customers': {'get', 'post'},
                    '/api/v1/customers/{id}': {'put'}}
        # Inventory adds routes; foundation routes and their methods must stay exact.
        for path, methods in expected.items():
            self.assertIn(path, document['paths'])
            self.assertEqual(set(document['paths'][path]), methods)
        schemas = document['components']['schemas']
        def check(response, path, method, status):
            self.expect(response, status)
            schema = document['paths'][path][method]['responses'][str(status)]['content']['application/json']['schema']
            self.validate_schema(response.json(), schema, schemas)
        check(Client(self.server).login('qa-admin', self.password), '/api/v1/auth/login', 'post', 200)
        check(self.admin.request('GET', '/api/v1/me'), '/api/v1/me', 'get', 200)
        house = self.admin.request('GET', '/api/v1/systemhaus')
        check(house, '/api/v1/systemhaus', 'get', 200)
        self.assertEqual(house.headers['etag'], '"1"')
        check(self.mutate(self.admin, 'PUT', '/api/v1/systemhaus', 'Contract house', 1), '/api/v1/systemhaus', 'put', 200)
        created = self.mutate(self.admin, 'POST', '/api/v1/customers', 'Contract client', 2)
        check(created, '/api/v1/customers', 'post', 201)
        check(self.admin.request('GET', '/api/v1/customers'), '/api/v1/customers', 'get', 200)
        check(self.mutate(self.admin, 'PUT', '/api/v1/customers/' + created.json()['resource']['id'], 'Renamed contract', 1), '/api/v1/customers/{id}', 'put', 200)
        self.expect(self.admin.request('POST', '/api/v1/login', {'username': 'qa-admin', 'password': self.password}), 404)
        self.expect(self.admin.request('POST', '/api/v1/logout'), 404)
        self.expect(self.admin.request('POST', '/api/v1/auth/logout'), 204)


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def startTest(self, test):
        self.started = time.monotonic()
        super().startTest(test)

    def _record(self, test, status):
        self.records.append({'test': test.id(), 'status': status,
                             'elapsedSeconds': round(time.monotonic() - self.started, 3)})

    def addSuccess(self, test):
        self._record(test, 'passed')
        super().addSuccess(test)

    def addFailure(self, test, err):
        self._record(test, 'failed')
        super().addFailure(test, err)

    def addError(self, test, err):
        self._record(test, 'error')
        super().addError(test, err)


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=WORKSPACE / 'evidence/s1-20260928/postgres-qa')
    parser.add_argument('--filter', default='', help='Run only test names containing this text')
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    run_id = started.strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    logfile = args.evidence / f'{run_id}.log'
    metadata = {'runId': run_id, 'startedUtc': started.isoformat(), 'platform': platform.platform(),
                'python': platform.python_version(), 'dllSha256': hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest(),
                'dllPath': str(DEFAULT_DLL.relative_to(WORKSPACE)), 'filter': args.filter,
                'historicalResultsReused': False, 'fixtureAdminOperations': 'Explicit SQL fixtures; no administration endpoints implied',
                'transport': 'Explicit Development loopback HTTP; production HTTPS not certified here'}
    with logfile.open('w', encoding='utf-8') as output, Lab('native-qa') as lab:
        FoundationPostgres.lab = lab
        metadata['labId'] = lab.id
        metadata['postgresVersion'] = lab.sql('postgres', 'SHOW server_version')
        metadata['sdkVersion'] = subprocess.run([str(lab.dotnet), '--version'], cwd=WORKSPACE / 'development/server',
                                                env=lab.environment(), capture_output=True, text=True,
                                                check=True, creationflags=NO_WINDOW).stdout.strip()
        names = [name for name in unittest.defaultTestLoader.getTestCaseNames(FoundationPostgres) if args.filter in name]
        suite = unittest.TestSuite(FoundationPostgres(name) for name in names)
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(suite)
        metadata.update(testsRun=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                        successful=result.wasSuccessful(), cases=result.records,
                        databases=[{'name': row['name'], 'label': row['label']} for row in lab.metadata['databases']])
    metadata['finishedUtc'] = datetime.now(timezone.utc).isoformat()
    metadata['labStopped'] = not lab.running
    (args.evidence / f'{run_id}.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Evidence: {logfile.resolve()}')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
