"""Independent native PostgreSQL QA for the inventory command API.

Each test creates a new private database. SQL administrative fixtures are not
claimed as implemented administration endpoints. Run after building the exact
server DLL to be tested; output metadata records its SHA-256 and native versions.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
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
from test_postgres import EvidenceResult, Tee


def uid():
    return str(uuid.uuid4())


class InventoryPostgres(unittest.TestCase):
    lab = None

    def setUp(self):
        self.db = self.lab.create_database(self._testMethodName)
        self.password = secrets.token_urlsafe(32)
        self.server = None
        result = self.lab.bootstrap(self.db, 'qa-inventory-admin', self.password)
        self.assertEqual(result.returncode, 0, 'Bootstrap must succeed; raw output remains private')
        self.lab.grant_runtime(self.db)
        self.house_id = self.lab.sql(self.db, 'SELECT id FROM systemhaus')
        self.admin_id = self.lab.sql(self.db, 'SELECT id FROM app_user')
        self.server = self.lab.start_server(self.db)
        self.admin = Client(self.server)
        self.admin.actor_id = self.admin_id
        self.expect(self.admin.login('qa-inventory-admin', self.password), 200)
        self.customer_id = self.customer('Customer inventory QA')['id']

    def tearDown(self):
        if self.server:
            self.server.close()

    def expect(self, response, status, error=None):
        # Deliberately do not print complete response bodies: me/login has CSRF.
        actual_error = None
        if response.status >= 400 and response.body:
            try:
                actual_error = response.json().get('error')
            except (ValueError, AttributeError):
                actual_error = 'non-json-error'
        self.assertEqual(response.status, status, f'Unexpected HTTP status; error={actual_error}')
        if error is not None:
            self.assertEqual(actual_error, error)
        return response

    def customer(self, name):
        revision = self.expect(self.admin.request('GET', '/api/v1/systemhaus'), 200).json()['revision']
        response = self.admin.request('POST', '/api/v1/customers', {'name': name},
                                      {'If-Match': f'"{revision}"', 'Idempotency-Key': uid(),
                                       'X-RackClick-Actor': self.admin_id})
        return self.expect(response, 201).json()['resource']

    def snapshot(self, customer=None, client=None):
        customer = customer or self.customer_id
        response = self.expect((client or self.admin).request('GET', f'/api/v1/customers/{customer}/project'), 200)
        value = response.json()
        self.assertEqual(value['customerId'], customer)
        self.assertEqual(response.headers.get('etag'), f'"{value["revision"]}"')
        return value

    def command(self, kind, payload, customer=None, revision=None, key=None, client=None, status=200, actor=None):
        customer = customer or self.customer_id
        client = client or self.admin
        if revision is None:
            revision = self.snapshot(customer)['revision']
        headers = {'If-Match': f'"{revision}"', 'Idempotency-Key': key or uid(),
                   'X-RackClick-Actor': actor or client.actor_id}
        response = client.request('POST', f'/api/v1/customers/{customer}/commands',
                                  {'type': kind, 'payload': payload}, headers)
        self.expect(response, status)
        return response

    def create(self, kind, payload, collection, customer=None):
        before = {row['id'] for row in self.snapshot(customer)[collection]}
        self.command(kind + '.create', payload, customer=customer)
        added = [row for row in self.snapshot(customer)[collection] if row['id'] not in before]
        self.assertEqual(len(added), 1, 'Creation must add exactly one stable identity')
        uuid.UUID(added[0]['id'])
        return added[0]

    def hierarchy(self, suffix='', customer=None):
        site = self.create('site', {'name': 'Site' + suffix}, 'sites', customer)
        building = self.create('building', {'name': 'Building' + suffix, 'siteId': site['id']}, 'buildings', customer)
        room = self.create('room', {'name': 'Room' + suffix, 'buildingId': building['id']}, 'rooms', customer)
        rack = self.create('rack', {'name': 'Rack' + suffix, 'roomId': room['id'], 'sizeU': 42}, 'racks', customer)
        return site, building, room, rack

    def device(self, name, rack=None, room=None, kind='rackEquipment', groups=None, customer=None, size=1):
        payload = {'name': name, 'kind': kind, 'portGroups': groups or [{'type': 'rj45', 'count': 4}]}
        if kind == 'rackEquipment':
            payload.update(rackId=rack, sizeU=size)
        else:
            payload['roomId'] = room
        device = self.create('device', payload, 'devices', customer)
        snapshot = self.snapshot(customer)
        port_groups = [row for row in snapshot['portGroups'] if row['deviceId'] == device['id']]
        ports = [row for row in snapshot['ports'] if row['deviceId'] == device['id']]
        return device, port_groups, ports

    def port_changes(self, device, group, ports, changes, **options):
        return self.command('ports.update', {'deviceId': device['id'], 'groupId': group['id'],
                            'groupType': group['type'], 'portIds': [p['id'] for p in ports], 'changes': changes}, **options)

    def connect(self, first, second, **attributes):
        return self.create('connections', {'fromPortId': first['id'], 'toPortId': second['id'],
                                          **attributes}, 'connections')

    def reject_unchanged(self, kind, payload, customer=None, allowed=(404, 409, 422)):
        customer = customer or self.customer_id
        before = self.snapshot(customer)
        response = self.admin.request('POST', f'/api/v1/customers/{customer}/commands',
                                      {'type': kind, 'payload': payload},
                                      {'If-Match': f'"{before["revision"]}"', 'Idempotency-Key': uid(),
                                       'X-RackClick-Actor': self.admin_id})
        self.assertIn(response.status, allowed, 'Invalid domain command must reject without service errors')
        self.assertEqual(self.snapshot(customer), before, 'Rejected command changed the snapshot or revision')
        return response

    def preview(self, kind, payload, customer=None, client=None):
        customer, client = customer or self.customer_id, client or self.admin
        before = self.snapshot(customer)
        response = self.expect(client.request('POST', f'/api/v1/customers/{customer}/commands/preview',
                                {'type': kind, 'payload': payload},
                                {'If-Match': f'"{before["revision"]}"', 'X-RackClick-Actor': client.actor_id}), 200)
        value = response.json()
        self.assertEqual(value['customerId'], customer)
        self.assertEqual(value['revision'], before['revision'])
        self.assertTrue(isinstance(value.get('confirmationToken'), str) and bool(value['confirmationToken']),
                        'Preview must return a bound confirmation token; do not print it')
        self.assertEqual(self.snapshot(customer), before, 'Preview must not mutate the project')
        return value

    def desired_groups(self, device_id, removed=(), add=0):
        project = self.snapshot()
        groups = [g for g in project['portGroups'] if g['deviceId'] == device_id]
        return [{'id': g['id'], 'type': g['type'], 'name': g['name'], 'prefix': g['prefix'],
                 'retainedPortIds': [p['id'] for p in project['ports'] if p['groupId'] == g['id'] and p['id'] not in removed],
                 'addCount': add if index == 0 else 0} for index, g in enumerate(groups)]

    def cancel(self, kind, payload, key, revision=1, customer=None, client=None, status=200, actor=None):
        customer, client = customer or self.customer_id, client or self.admin
        response = client.request('POST', f'/api/v1/customers/{customer}/operations/{key}/cancel',
                                  {'type': kind, 'payload': payload},
                                  {'If-Match': f'"{revision}"', 'Idempotency-Key': key,
                                   'X-RackClick-Actor': actor or client.actor_id})
        return self.expect(response, status)

    def operation_state(self, key, customer=None, client=None):
        customer, client = customer or self.customer_id, client or self.admin
        return self.expect(client.request('GET', f'/api/v1/customers/{customer}/operations/{key}'), 200).json()

    def add_user(self, name, capabilities=(), customer=None, customer_group=False):
        user_id, group_id = uid(), uid()
        self.lab.sql(self.db, f"INSERT INTO app_user(id,systemhaus_id,username,password_hash) "
                     f"SELECT '{user_id}',systemhaus_id,{literal(name)},password_hash FROM app_user WHERE id='{self.admin_id}'; "
                     f"INSERT INTO user_group VALUES('{group_id}','{self.house_id}','QA inventory group'); "
                     f"INSERT INTO user_group_member VALUES('{self.house_id}','{user_id}','{group_id}');")
        scope_id = customer
        scope_column = 'customer_id'
        if customer_group:
            scope_id, scope_column = uid(), 'customer_group_id'
            self.lab.sql(self.db, f"INSERT INTO customer_group VALUES('{scope_id}','{self.house_id}','QA customers group'); "
                         f"INSERT INTO customer_group_member VALUES('{self.house_id}','{scope_id}','{customer}');")
        for capability in capabilities:
            columns = f'id,systemhaus_id,user_group_id,capability' + (f',{scope_column}' if scope_id else '')
            values = f"'{uid()}','{self.house_id}','{group_id}',{literal(capability)}" + (f",'{scope_id}'" if scope_id else '')
            self.lab.sql(self.db, f'INSERT INTO permission_grant({columns}) VALUES({values});')
        client = Client(self.server)
        client.actor_id = user_id
        self.expect(client.login(name, self.password), 200)
        return client, group_id, scope_id

    def test_empty_snapshot_and_required_mutation_headers(self):
        value = self.snapshot()
        self.assertEqual(value['revision'], 1)
        for collection in ('sites', 'buildings', 'rooms', 'racks', 'devices', 'portGroups', 'ports', 'connections'):
            self.assertEqual(value[collection], [])
        path = f'/api/v1/customers/{self.customer_id}/commands'
        body = {'type': 'site.create', 'payload': {'name': 'Must not exist'}}
        headers = {'Idempotency-Key': uid(), 'X-RackClick-Actor': self.admin_id}
        self.expect(self.admin.request('POST', path, body, headers), 428)
        headers = {'Idempotency-Key': uid(), 'If-Match': '"1"'}
        self.expect(self.admin.request('POST', path, body, headers), 422)
        self.expect(self.admin.request('POST', path, body, {**headers, 'X-RackClick-Actor': uid()}), 409)
        self.assertEqual(self.snapshot(), value)

    def test_hierarchy_persistence_restart_second_user(self):
        site, building, room, rack = self.hierarchy(' \u00d1')
        before = self.snapshot()
        self.assertEqual(building['siteId'], site['id'])
        self.assertEqual(room['buildingId'], building['id'])
        self.assertEqual(rack['roomId'], room['id'])
        second, _, _ = self.add_user('qa-second', ['inventory.read'], self.customer_id)
        self.assertEqual(self.snapshot(client=second), before)
        self.server.close()
        self.server = self.lab.start_server(self.db)
        self.admin.server = second.server = self.server
        self.assertEqual(self.snapshot(client=second), before)
        self.assertEqual(self.lab.sql(self.db, f"SELECT revision FROM customer WHERE id='{self.customer_id}'"), str(before['revision']))

    def test_hierarchy_crud_stable_ids_homonyms_and_occupied_parent_restrict(self):
        site, building, room, rack = self.hierarchy()
        duplicate_name = self.create('site', {'name': site['name']}, 'sites')
        self.assertNotEqual(duplicate_name['id'], site['id'])
        for kind, row in (('site', site), ('building', building), ('room', room), ('rack', rack)):
            self.command(kind + '.update', {'id': row['id'], 'name': 'Renamed ' + kind,
                                            'properties': {'unknownExtension': {'keep': 'original', 'change': 1}}})
            self.command(kind + '.update', {'id': row['id'], 'properties': {'unknownExtension': {'change': 2}}})
        current = self.snapshot()
        for collection, row in (('sites', site), ('buildings', building), ('rooms', room), ('racks', rack)):
            value = next(item for item in current[collection] if item['id'] == row['id'])
            self.assertEqual(value['properties']['unknownExtension'], {'keep': 'original', 'change': 2})
        self.reject_unchanged('site.delete', {'id': site['id']})
        self.reject_unchanged('building.delete', {'id': building['id']})
        self.reject_unchanged('room.delete', {'id': room['id']})
        self.command('rack.assignRoom', {'id': rack['id'], 'roomId': None})
        for kind, row in (('room', room), ('building', building), ('site', site), ('site', duplicate_name)):
            self.command(kind + '.delete', {'id': row['id']})
        final = self.snapshot()
        self.assertEqual(final['sites'], [])
        self.assertEqual(final['buildings'], [])
        self.assertEqual(final['rooms'], [])
        self.assertEqual(final['racks'][0]['id'], rack['id'])
        self.assertIsNone(final['racks'][0]['roomId'])

    def test_delete_requires_distinct_capability(self):
        site = self.create('site', {'name': 'Delete capability fixture'}, 'sites')
        editor, group, _ = self.add_user('qa-edit-no-delete', ['inventory.read', 'inventory.edit'], self.customer_id)
        self.command('site.update', {'id': site['id'], 'name': 'Editor can rename'}, client=editor)
        self.command('site.delete', {'id': site['id']}, client=editor, status=403)
        self.lab.sql(self.db, f"INSERT INTO permission_grant(id,systemhaus_id,user_group_id,capability,customer_id) "
                     f"VALUES('{uid()}','{self.house_id}','{group}','inventory.delete','{self.customer_id}');")
        self.command('site.delete', {'id': site['id']}, client=editor)
        self.assertEqual(self.snapshot()['sites'], [])

    def test_customer_scopes_read_write_and_group_revocation(self):
        other = self.customer('Other hidden client')['id']
        grouped, group_id, scope = self.add_user('qa-grouped', ['inventory.read', 'inventory.edit'],
                                                self.customer_id, customer_group=True)
        reader, _, _ = self.add_user('qa-reader', ['inventory.read'], self.customer_id)
        self.command('site.create', {'name': 'Scoped creation'}, client=grouped)
        self.expect(reader.request('GET', f'/api/v1/customers/{other}/project'), 404)
        self.command('site.create', {'name': 'Forbidden reader'}, client=reader, status=403)
        self.command('site.create', {'name': 'Hidden client'}, customer=other, client=grouped, status=404)
        self.lab.sql(self.db, f"DELETE FROM customer_group_member WHERE group_id='{scope}'")
        self.expect(grouped.request('GET', f'/api/v1/customers/{self.customer_id}/project'), 404)
        self.command('site.create', {'name': 'Revoked writer'}, client=grouped, status=404)
        self.assertEqual(len(self.snapshot()['sites']), 1)
        self.assertEqual(self.snapshot(other)['sites'], [])

    def test_idempotency_replay_scope_body_and_stale_revision(self):
        key = uid()
        payload = {'name': 'Single site'}
        first = self.command('site.create', payload, revision=1, key=key).json()
        self.command('site.create', {'name': 'Second site'})
        replay = self.command('site.create', payload, revision=1, key=key).json()
        self.assertEqual(first, replay)
        self.assertEqual(first['customerId'], self.customer_id)
        self.assertEqual(first['revision'], 2)
        self.assertEqual(first['requestId'], key)
        uuid.UUID(first['operationId'])
        self.command('site.create', {'name': 'Different body'}, revision=1, key=key, status=409)
        other = self.customer('Other client')['id']
        self.command('site.create', payload, customer=other, revision=1, key=key, status=409)
        self.command('site.create', {'name': 'Stale revision'}, revision=1, status=412)
        self.assertEqual(len(self.snapshot()['sites']), 2)
        self.assertEqual(self.snapshot(other)['sites'], [])
        self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM operation WHERE request_id='{key}'; SELECT count(*) FROM audit_event WHERE request_id='{key}'"), '1\n1')

    def test_idempotency_canonical_object_order_and_actor_isolation(self):
        key = uid()
        payload = {'name': 'Canonical payload', 'properties': {'z': 1, 'a': {'b': 2, 'a': 3}}}
        first = self.command('site.create', payload, revision=1, key=key).json()
        reordered = {'properties': {'a': {'a': 3, 'b': 2}, 'z': 1}, 'name': 'Canonical payload'}
        replay = self.command('site.create', reordered, revision=1, key=key).json()
        self.assertEqual(first, replay)
        other, _, _ = self.add_user('qa-other-actor', ['inventory.read', 'inventory.edit'], self.customer_id)
        self.command('site.create', payload, revision=1, key=key, client=other, actor=self.admin_id, status=409)
        self.assertEqual(len(self.snapshot()['sites']), 1)

    def test_concurrent_same_revision_exactly_one_commit(self):
        barrier = threading.Barrier(2)
        def attempt(index):
            barrier.wait(timeout=10)
            return self.admin.request('POST', f'/api/v1/customers/{self.customer_id}/commands',
                                      {'type': 'site.create', 'payload': {'name': f'Concurrent {index}'}},
                                      {'If-Match': '"1"', 'Idempotency-Key': uid(), 'X-RackClick-Actor': self.admin_id})
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(attempt, range(2)))
        self.assertEqual(sorted(r.status for r in responses), [200, 412])
        self.assertEqual(len(self.snapshot()['sites']), 1)
        self.assertEqual(self.snapshot()['revision'], 2)

    def test_concurrent_same_key_single_operation_and_audit(self):
        barrier, key = threading.Barrier(2), uid()
        def attempt(_):
            barrier.wait(timeout=10)
            return self.command('site.create', {'name': 'Concurrent replay'}, revision=1, key=key).json()
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(attempt, range(2)))
        self.assertEqual(responses[0], responses[1])
        self.assertEqual(len(self.snapshot()['sites']), 1)
        self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM operation WHERE request_id='{key}'; SELECT count(*) FROM audit_event WHERE request_id='{key}'"), '1\n1')

    def test_concurrent_same_key_different_customers_one_commit(self):
        other = self.customer('Concurrent request other scope')['id']
        barrier, key = threading.Barrier(2), uid()
        def attempt(customer):
            barrier.wait(timeout=10)
            return self.admin.request('POST', f'/api/v1/customers/{customer}/commands',
                                      {'type': 'site.create', 'payload': {'name': 'Cross scope request'}},
                                      {'If-Match': '"1"', 'Idempotency-Key': key, 'X-RackClick-Actor': self.admin_id})
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(attempt, [self.customer_id, other]))
        self.assertEqual(sorted(r.status for r in responses), [200, 409])
        self.assertEqual(len(self.snapshot()['sites']) + len(self.snapshot(other)['sites']), 1)
        self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM operation WHERE request_id='{key}'; SELECT count(*) FROM audit_event WHERE request_id='{key}'"), '1\n1')

    def test_lock_customer_a_does_not_block_customer_b(self):
        other = self.customer('Independent client B')['id']
        started = threading.Event()
        def hold_lock():
            started.set()
            return self.lab.sql(self.db, f"SET application_name='qa_inventory_customer_lock'; BEGIN; "
                                f"SELECT id FROM customer WHERE id='{self.customer_id}' FOR UPDATE; SELECT pg_sleep(6); COMMIT;")
        with ThreadPoolExecutor(max_workers=1) as pool:
            held = pool.submit(hold_lock)
            self.assertTrue(started.wait(timeout=3))
            acquired = False
            for _ in range(40):
                if self.lab.sql(self.db, "SELECT count(*) FROM pg_stat_activity WHERE application_name='qa_inventory_customer_lock' AND wait_event='PgSleep'") == '1':
                    acquired = True
                    break
                time.sleep(.05)
            self.assertTrue(acquired, 'Fixture must hold the A row lock before testing B')
            began = time.monotonic()
            self.command('site.create', {'name': 'B proceeds while A is locked'}, customer=other, revision=1)
            elapsed = time.monotonic() - began
            self.assertFalse(held.done(), 'B must commit before the A lock is released')
            self.assertLess(elapsed, 3, 'B unexpectedly waited for customer A')
            held.result(timeout=10)
        self.assertEqual(len(self.snapshot(other)['sites']), 1)
        self.assertEqual(self.snapshot()['sites'], [])

    def test_audit_failure_rolls_back_inventory_revision_operation(self):
        before, key = self.snapshot(), uid()
        self.lab.sql(self.db, "CREATE FUNCTION qa_inventory_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ "
                     "BEGIN RAISE EXCEPTION 'QA inventory audit failure'; END $$; "
                     "CREATE TRIGGER qa_inventory_fail_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION qa_inventory_fail_audit();")
        self.command('site.create', {'name': 'Rolled back site'}, revision=1, key=key, status=503)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.lab.sql(self.db, f"SELECT revision FROM customer WHERE id='{self.customer_id}'; "
                         f"SELECT count(*) FROM operation WHERE request_id='{key}'; SELECT count(*) FROM audit_event WHERE request_id='{key}'"), '1\n0\n0')
        self.lab.sql(self.db, 'DROP TRIGGER qa_inventory_fail_audit ON audit_event; DROP FUNCTION qa_inventory_fail_audit();')
        self.command('site.create', {'name': 'Rolled back site'}, revision=1, key=key)
        self.assertEqual(len(self.snapshot()['sites']), 1)

    def test_inventory_audit_identifies_actor_scope_revision_and_resource(self):
        actor, _, _ = self.add_user('qa-audited-writer', ['inventory.read', 'inventory.edit'], self.customer_id)
        key = uid()
        result = self.command('site.create', {'name': 'Audited site'}, revision=1, key=key, client=actor).json()
        resource = self.snapshot()['sites'][0]
        audit = json.loads(self.lab.sql(self.db,
            f"SELECT json_build_object('id',id,'actor',actor_id,'request',request_id,'action',action,'resource',resource_id,"
            f"'before',before_json,'after',after_json)::text FROM audit_event WHERE request_id='{key}'"))
        self.assertEqual((audit['id'], audit['actor'], audit['request'], audit['action'], audit['resource']),
                         (result['operationId'], actor.actor_id, key, 'inventory.site.create', resource['id']))
        self.assertEqual((audit['before']['customerId'], audit['before']['revision'], audit['after']['revision']),
                         (self.customer_id, 1, 2))
        self.assertEqual((audit['after']['customerId'], audit['after']['data']['id'], audit['after']['data']['name']),
                         (self.customer_id, resource['id'], 'Audited site'))
        stored = json.loads(self.lab.sql(self.db, f"SELECT result_json::text FROM operation WHERE request_id='{key}'"))
        self.assertEqual(stored, result)

    def test_cancel_before_execute_blocks_late_request_and_is_durable(self):
        key, payload = uid(), {'name': 'Must never commit'}
        self.assertEqual(self.operation_state(key)['state'], 'notRecorded')
        canceled = self.cancel('site.create', payload, key).json()
        self.assertEqual((canceled['state'], canceled['customerId'], canceled['requestId'], canceled['revision']),
                         ('cancelled', self.customer_id, key, 1))
        self.assertIsNone(canceled['operation'])
        self.expect(self.command('site.create', payload, revision=1, key=key, status=409), 409, 'operation_cancelled')
        self.server.close()
        self.server = self.lab.start_server(self.db)
        self.admin.server = self.server
        self.assertEqual(self.operation_state(key), canceled)
        self.expect(self.command('site.create', payload, revision=1, key=key, status=409), 409, 'operation_cancelled')
        self.assertEqual(self.snapshot()['sites'], [])
        self.assertEqual(self.snapshot()['revision'], 1)
        self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM operation WHERE request_id='{key}'; "
                         f"SELECT count(*) FROM operation_cancellation WHERE request_id='{key}'; "
                         f"SELECT count(*) FROM audit_event WHERE request_id='{key}' AND action='operation.cancel'"), '0\n1\n1')

    def test_cancel_replay_original_stable_different_body_revision_scope_conflict(self):
        key, payload = uid(), {'name': 'Original cancelled body'}
        canceled = self.cancel('site.create', payload, key).json()
        self.command('site.create', {'name': 'Another committed operation'})
        self.assertEqual(self.cancel('site.create', payload, key, revision=1).json(), canceled)
        self.expect(self.cancel('site.create', {'name': 'Different body'}, key, status=409), 409, 'request_id_reused')
        self.expect(self.cancel('site.create', payload, key, revision=2, status=409), 409, 'request_id_reused')
        other = self.customer('Other cancellation client')['id']
        self.expect(self.cancel('site.create', payload, key, customer=other, status=409), 409, 'request_id_reused')
        self.expect(self.command('site.create', {'name': 'Different late body'}, key=key, revision=1, status=409), 409, 'request_id_reused')
        self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM operation_cancellation WHERE request_id='{key}'; "
                         f"SELECT count(*) FROM audit_event WHERE request_id='{key}'"), '1\n1')

    def test_cancel_stale_original_revision_fences_late_request_and_checks_key_header(self):
        key, payload = uid(), {'name': 'Delayed original revision'}
        self.command('site.create', {'name': 'Unrelated newer committed site'})
        route = f'/api/v1/customers/{self.customer_id}/operations/{key}/cancel'
        headers = {'If-Match': '"1"', 'X-RackClick-Actor': self.admin_id}
        body = {'type': 'site.create', 'payload': payload}
        self.expect(self.admin.request('POST', route, body, headers), 422, 'request_id_invalid')
        self.expect(self.admin.request('POST', route, body, {**headers, 'Idempotency-Key': uid()}), 422, 'request_id_mismatch')
        before = self.snapshot()
        canceled = self.cancel('site.create', payload, key, revision=1).json()
        self.assertEqual(canceled['state'], 'cancelled')
        self.assertEqual(canceled['revision'], before['revision'])
        self.assertEqual(self.snapshot(), before)
        self.expect(self.command('site.create', payload, revision=1, key=key, status=409), 409, 'operation_cancelled')

    def test_cancel_after_commit_returns_original_without_undo(self):
        key, payload = uid(), {'name': 'Already committed'}
        committed = self.command('site.create', payload, key=key, revision=1).json()
        before = self.snapshot()
        response = self.cancel('site.create', payload, key).json()
        self.assertEqual(response['state'], 'committed')
        self.assertEqual(response['operation'], committed)
        self.assertEqual(self.snapshot(), before)
        self.expect(self.cancel('site.create', {'name': 'Different original'}, key, status=409), 409, 'request_id_reused')
        self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM operation_cancellation WHERE request_id='{key}'; "
                         f"SELECT count(*) FROM audit_event WHERE request_id='{key}'"), '0\n1')

    def test_cancel_requires_current_scope_capability_actor_and_csrf(self):
        other_customer = self.customer('Cancellation hidden client')['id']
        reader, _, _ = self.add_user('qa-cancel-reader', ['inventory.read'], self.customer_id)
        editor, _, _ = self.add_user('qa-cancel-editor', ['inventory.read', 'inventory.edit'], self.customer_id)
        payload, key = {'name': 'Cancellation permissions'}, uid()
        self.cancel('site.create', payload, key, client=reader, status=403)
        self.cancel('site.create', payload, key, customer=other_customer, client=editor, status=404)
        self.cancel('device.delete', {'id': uid()}, key, client=editor, status=403)
        self.cancel('site.create', payload, key, client=editor, actor=self.admin_id, status=409)
        route = f'/api/v1/customers/{self.customer_id}/operations/{key}/cancel'
        self.expect(self.admin.request('POST', route, {'type': 'site.create', 'payload': payload},
                                       {'If-Match': '"1"', 'Idempotency-Key': key,
                                        'X-RackClick-Actor': self.admin_id, 'X-RackClick-CSRF': ''}), 403)
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM operation_cancellation'), '0')
        self.assertEqual(self.cancel('site.create', payload, key, client=editor).json()['state'], 'cancelled')

    def test_concurrent_execute_cancel_only_one_terminal_state(self):
        key, payload, barrier = uid(), {'name': 'Execute cancel contention'}, threading.Barrier(2)
        def execute():
            barrier.wait(timeout=10)
            return self.admin.request('POST', f'/api/v1/customers/{self.customer_id}/commands',
                                      {'type': 'site.create', 'payload': payload},
                                      {'If-Match': '"1"', 'Idempotency-Key': key, 'X-RackClick-Actor': self.admin_id})
        def cancel():
            barrier.wait(timeout=10)
            return self.cancel('site.create', payload, key)
        with ThreadPoolExecutor(max_workers=2) as pool:
            execute_future, cancel_future = pool.submit(execute), pool.submit(cancel)
            executed, canceled = execute_future.result(timeout=25), cancel_future.result(timeout=25)
        state = canceled.json()['state']
        counts = self.lab.sql(self.db, f"SELECT count(*) FROM operation WHERE request_id='{key}'; "
                              f"SELECT count(*) FROM operation_cancellation WHERE request_id='{key}'; "
                              f"SELECT count(*) FROM audit_event WHERE request_id='{key}'")
        if state == 'committed':
            self.expect(executed, 200)
            self.assertEqual(canceled.json()['operation'], executed.json())
            self.assertEqual(counts, '1\n0\n1')
            self.assertEqual(len(self.snapshot()['sites']), 1)
        else:
            self.assertEqual(state, 'cancelled')
            self.expect(executed, 409, 'operation_cancelled')
            self.assertEqual(counts, '0\n1\n1')
            self.assertEqual(self.snapshot()['sites'], [])
        self.assertEqual(self.operation_state(key)['state'], state)

    def test_cancel_audit_failure_rolls_back_fence_then_execute_can_commit(self):
        key, payload = uid(), {'name': 'Failed cancellation leaves no fence'}
        self.lab.sql(self.db, "CREATE FUNCTION qa_cancel_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ "
                     "BEGIN RAISE EXCEPTION 'QA cancellation audit failure'; END $$; "
                     "CREATE TRIGGER qa_cancel_fail_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION qa_cancel_fail_audit();")
        self.cancel('site.create', payload, key, status=503)
        self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM operation_cancellation WHERE request_id='{key}'; "
                         f"SELECT count(*) FROM operation WHERE request_id='{key}'; SELECT count(*) FROM audit_event WHERE request_id='{key}'"), '0\n0\n0')
        self.assertEqual(self.operation_state(key)['state'], 'notRecorded')
        self.assertEqual(self.snapshot()['revision'], 1)
        self.lab.sql(self.db, 'DROP TRIGGER qa_cancel_fail_audit ON audit_event; DROP FUNCTION qa_cancel_fail_audit();')
        self.command('site.create', payload, key=key, revision=1)
        self.assertEqual(len(self.snapshot()['sites']), 1)

    def test_postgres_terminal_state_trigger_rejects_both_directions(self):
        canceled_key, committed_key = uid(), uid()
        self.cancel('site.create', {'name': 'SQL cancelled'}, canceled_key)
        self.command('site.create', {'name': 'SQL committed'}, key=committed_key, revision=1)
        def rejected_terminal_sql(statement):
            self.lab.sql(self.db, 'DO $$ DECLARE violated text; BEGIN BEGIN ' + statement + '; '
                         "RAISE EXCEPTION 'QA terminal state conflict was not rejected'; "
                         "EXCEPTION WHEN unique_violation THEN GET STACKED DIAGNOSTICS violated = CONSTRAINT_NAME; "
                         "IF violated <> 'operation_terminal_state_conflict' THEN RAISE; END IF; END; END $$;")
        rejected_terminal_sql('INSERT INTO operation(systemhaus_id,actor_id,request_id,request_hash,result_json) '
                              'SELECT systemhaus_id,actor_id,request_id,request_hash,result_json FROM operation_cancellation '
                              f"WHERE request_id='{canceled_key}'")
        rejected_terminal_sql('INSERT INTO operation_cancellation(systemhaus_id,actor_id,request_id,customer_id,request_hash,operation_id,result_json) '
                              f"SELECT systemhaus_id,actor_id,request_id,'{self.customer_id}',request_hash,'{uid()}',result_json "
                              f"FROM operation WHERE request_id='{committed_key}'")
        self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM operation WHERE request_id IN ('{canceled_key}','{committed_key}'); "
                         f"SELECT count(*) FROM operation_cancellation WHERE request_id IN ('{canceled_key}','{committed_key}')"), '1\n1')

    def wait_then_revoke(self, mode, revocation):
        client, group, _ = self.add_user(f'qa-wait-{mode}-{revocation}', ['inventory.read', 'inventory.edit'], self.customer_id)
        key, lock_label = uid(), 'qa_wait_' + uuid.uuid4().hex[:12]
        before = self.snapshot()
        body = {'type': 'site.create', 'payload': {'name': 'Must reject after wait'}}
        path = f'/api/v1/customers/{self.customer_id}/commands' if mode == 'execute' else \
               f'/api/v1/customers/{self.customer_id}/operations/{key}/cancel'
        headers = {'If-Match': f'"{before["revision"]}"', 'Idempotency-Key': key, 'X-RackClick-Actor': client.actor_id}
        with ThreadPoolExecutor(max_workers=2) as pool:
            holder = pool.submit(self.lab.sql, self.db, f"SET application_name='{lock_label}'; BEGIN; "
                                 f"SELECT id FROM customer WHERE id='{self.customer_id}' FOR UPDATE; SELECT pg_sleep(6); COMMIT;")
            locked = False
            for _ in range(40):
                if self.lab.sql(self.db, f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{lock_label}' AND wait_event='PgSleep'") == '1':
                    locked = True
                    break
                time.sleep(.025)
            self.assertTrue(locked, 'SQL fixture did not acquire its customer lock')
            pending = pool.submit(client.request, 'POST', path, body, headers)
            waiting = False
            for _ in range(40):
                if self.lab.sql(self.db, f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' "
                                f"AND usename='{self.db.runtime}' AND wait_event_type='Lock'", admin=True) != '0':
                    waiting = True
                    break
                time.sleep(.025)
            self.assertTrue(waiting and not holder.done(), 'Request must be waiting behind the row lock before revocation')
            if revocation == 'logout':
                self.expect(client.request('POST', '/api/v1/auth/logout'), 204)
            elif revocation == 'expiry':
                # Expiry is later than the API transaction start, earlier than
                # lock release. A stale now() transaction clock must not pass.
                self.lab.sql(self.db, f"UPDATE app_session SET expires_at=clock_timestamp()+interval '200 milliseconds' "
                             f"WHERE user_id='{client.actor_id}'")
                time.sleep(.3)
            elif revocation == 'disabled':
                self.lab.sql(self.db, f"UPDATE app_user SET active=false WHERE id='{client.actor_id}'")
            elif revocation == 'read':
                self.lab.sql(self.db, f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability='inventory.read'")
            response = pending.result(timeout=20)
            holder.result(timeout=10)
        self.expect(response, 404 if revocation == 'read' else 401,
                    'not_found' if revocation == 'read' else 'authentication_required')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM operation WHERE request_id='{key}'; "
                         f"SELECT count(*) FROM operation_cancellation WHERE request_id='{key}'; "
                         f"SELECT count(*) FROM audit_event WHERE request_id='{key}'"), '0\n0\n0')

    def test_waiting_execute_rechecks_logout_expiry_disabled_and_read_permission(self):
        for change in ('logout', 'expiry', 'disabled', 'read'):
            with self.subTest(revocation=change):
                self.wait_then_revoke('execute', change)

    def test_waiting_cancel_rechecks_logout_expiry_disabled_and_read_permission(self):
        for change in ('logout', 'expiry', 'disabled', 'read'):
            with self.subTest(revocation=change):
                self.wait_then_revoke('cancel', change)

    def test_dose_and_end_device_have_room_without_fictitious_rack_u(self):
        _, _, room, rack = self.hierarchy()
        equipment, _, _ = self.device('Rack equipment', rack=rack['id'])
        dose, dose_groups, dose_ports = self.device('Dose A', kind='dose', room=room['id'])
        final, _, final_ports = self.device('Final AP', kind='endDevice', room=room['id'])
        self.assertEqual(equipment['rackId'], rack['id'])
        self.assertIsNone(equipment['roomId'])
        for device in (dose, final):
            self.assertIsNone(device['rackId'])
            self.assertEqual(device['roomId'], room['id'])
            self.assertIsNone(device['sizeU'])
        connection = self.connect(dose_ports[0], final_ports[0])
        self.assertEqual({connection['fromPortId'], connection['toPortId']}, {dose_ports[0]['id'], final_ports[0]['id']})
        self.reject_unchanged('device.create', {'name': 'Invalid mixed placement', 'kind': 'dose',
                              'roomId': room['id'], 'rackId': rack['id'], 'sizeU': 1, 'portGroups': []})
        self.reject_unchanged('device.create', {'name': 'Final without a room', 'kind': 'endDevice', 'portGroups': []})

    def test_cross_customer_parent_and_placement_rejected(self):
        other = self.customer('Foreign inventory')['id']
        site, building, room, rack = self.hierarchy(' Foreign', customer=other)
        for kind, payload in (
            ('building.create', {'name': 'Cross site', 'siteId': site['id']}),
            ('room.create', {'name': 'Cross building', 'buildingId': building['id']}),
            ('rack.create', {'name': 'Cross room', 'roomId': room['id'], 'sizeU': 42}),
            ('device.create', {'name': 'Cross rack', 'kind': 'rackEquipment', 'rackId': rack['id'], 'sizeU': 1, 'portGroups': []}),
            ('device.create', {'name': 'Cross room final', 'kind': 'endDevice', 'roomId': room['id'], 'portGroups': []}),
        ):
            self.reject_unchanged(kind, payload)
        self.assertEqual(self.snapshot()['revision'], 1)

    def test_same_gn_batches_target_ids_and_explicit_group_type(self):
        _, _, _, rack = self.hierarchy()
        device, groups, ports = self.device('Two RJ45 groups', rack=rack['id'],
                                            groups=[{'name': 'A', 'type': 'rj45', 'count': 2},
                                                    {'name': 'B', 'type': 'rj45', 'count': 2}])
        a, b = sorted(groups, key=lambda g: g['name'])
        ap = sorted((p for p in ports if p['groupId'] == a['id']), key=lambda p: p['gn'])
        bp = sorted((p for p in ports if p['groupId'] == b['id']), key=lambda p: p['gn'])
        self.assertEqual(ap[0]['gn'], bp[0]['gn'])
        self.port_changes(device, a, [ap[0]], {'status': 'reserved', 'label': 'Selected only'})
        current = {p['id']: p for p in self.snapshot()['ports']}
        self.assertEqual(current[ap[0]['id']]['status'], 'reserved')
        self.assertEqual(current[bp[0]['id']]['status'], 'free')
        base = {'deviceId': device['id'], 'groupId': a['id'], 'groupType': 'rj45', 'changes': {'status': 'disabled'}}
        for fields in ({'portIds': [ap[0]['id'], bp[0]['id']]},
                       {'portIds': [ap[0]['id'], ap[0]['id']]}, {'portIds': []},
                       {'portIds': [ap[0]['id']], 'groupType': 'sfp'},
                       {'gnFrom': 1, 'gnTo': 1}):
            self.reject_unchanged('ports.update', {**base, **fields})

    def test_rc9_connector_types_remain_distinct_in_projection(self):
        _, _, _, rack = self.hierarchy()
        types = ['rj45', 'rj45_poe', 'sfp', 'sfp28', 'qsfp', 'mgmt', 'console', 'power', 'usb_a', 'usb_c']
        _, groups, ports = self.device('All RC9 connector types', rack=rack['id'],
                                        groups=[{'type': kind, 'name': kind, 'count': 1} for kind in types])
        self.assertEqual(len(groups), len(types))
        self.assertEqual(sorted(p['type'] for p in ports), sorted(types))
        self.assertEqual(len({p['groupId'] for p in ports}), len(types))
        self.assertEqual({p['gn'] for p in ports}, {1})

    def test_port_poe_off_preserves_watts_and_face_identity(self):
        _, _, _, rack = self.hierarchy()
        device, groups, ports = self.device('PoE fixture', rack=rack['id'], groups=[{'type': 'rj45_poe', 'count': 2}])
        port = ports[0]
        self.port_changes(device, groups[0], [port], {'poe': True, 'watts': 23.5, 'color': '#123456',
                                                    'face': 'rear', 'label': 'Label usuario Ñ'})
        self.port_changes(device, groups[0], [port], {'poe': False})
        current = next(p for p in self.snapshot()['ports'] if p['id'] == port['id'])
        self.assertFalse(current['poe'])
        self.assertEqual(current['watts'], 23.5)
        self.assertEqual((current['face'], current['color'], current['label']), ('rear', '#123456', 'Label usuario Ñ'))
        self.port_changes(device, groups[0], [port], {'watts': None})
        self.assertIsNone(next(p for p in self.snapshot()['ports'] if p['id'] == port['id'])['watts'])
        base = {'deviceId': device['id'], 'groupId': groups[0]['id'], 'groupType': groups[0]['type'], 'portIds': [port['id']]}
        self.reject_unchanged('ports.update', {**base, 'changes': {'watts': 90.1}})
        self.reject_unchanged('ports.update', {**base, 'changes': {'watts': -1}})
        self.reject_unchanged('ports.update', {**base, 'changes': {'powerRole': 'inlet'}})

    def test_connections_reserved_disabled_faulty_and_existing_cable_preserved(self):
        _, _, _, rack = self.hierarchy()
        device, groups, ports = self.device('Connection status fixture', rack=rack['id'])
        self.port_changes(device, groups[0], [ports[0]], {'status': 'reserved'})
        self.reject_unchanged('connections.create', {'fromPortId': ports[0]['id'], 'toPortId': ports[1]['id']})
        connection = self.connect(ports[0], ports[1], confirmedReservedPortIds=[ports[0]['id']],
                                  note='Cable note', color='#13579b', patch='tested')
        self.port_changes(device, groups[0], [ports[1]], {'status': 'disabled'})
        self.assertEqual(self.snapshot()['connections'], [connection])
        self.port_changes(device, groups[0], [ports[2]], {'status': 'faulty'})
        self.reject_unchanged('connections.create', {'fromPortId': ports[2]['id'], 'toPortId': ports[3]['id']})
        self.reject_unchanged('connections.create', {'fromPortId': ports[0]['id'], 'toPortId': ports[0]['id'],
                                                    'confirmedReservedPortIds': [ports[0]['id']]})

    def test_reconnect_keeps_identity_attributes_and_rejects_invalid_targets(self):
        _, _, room, rack = self.hierarchy()
        rack2 = self.create('rack', {'name': 'Remote rack', 'roomId': room['id'], 'sizeU': 42}, 'racks')
        device, groups, ports = self.device('Local ports', rack=rack['id'])
        remote, remote_groups, remote_ports = self.device('Remote ports', rack=rack2['id'])
        connection = self.connect(ports[0], ports[1], note='Keep cable note', color='#abcdef', patch='tested')
        occupied = self.connect(remote_ports[0], remote_ports[1])
        base = {'connectionId': connection['id'], 'keepPortId': ports[0]['id']}
        self.reject_unchanged('connections.reconnect', {**base, 'newPortId': remote_ports[0]['id']})
        self.port_changes(remote, remote_groups[0], [remote_ports[2]], {'status': 'faulty'})
        self.reject_unchanged('connections.reconnect', {**base, 'newPortId': remote_ports[2]['id']})
        self.port_changes(remote, remote_groups[0], [remote_ports[2]], {'status': 'reserved'})
        self.reject_unchanged('connections.reconnect', {**base, 'newPortId': remote_ports[2]['id']})
        self.reject_unchanged('connections.reconnect', {**base, 'keepPortId': ports[3]['id'], 'newPortId': remote_ports[3]['id']})
        self.command('connections.reconnect', {**base, 'newPortId': remote_ports[2]['id'],
                                               'confirmedReservedPortIds': [remote_ports[2]['id']]})
        current = next(c for c in self.snapshot()['connections'] if c['id'] == connection['id'])
        self.assertEqual({current['fromPortId'], current['toPortId']}, {ports[0]['id'], remote_ports[2]['id']})
        self.assertEqual({k: current[k] for k in ('id', 'note', 'color', 'patch')},
                         {k: connection[k] for k in ('id', 'note', 'color', 'patch')})
        self.assertIn(occupied, self.snapshot()['connections'])

    def test_connection_update_preserves_endpoints_and_all_patch_states_disconnect(self):
        _, _, _, rack = self.hierarchy()
        _, _, ports = self.device('Cable metadata', rack=rack['id'])
        connection = self.connect(ports[0], ports[1])
        endpoints = {connection['fromPortId'], connection['toPortId']}
        note = 'Nota literal <script> de QA\nSegunda línea 日本語'
        for patch in ('planned', 'progress', 'done', 'tested', 'none'):
            self.command('connections.update', {'connectionId': connection['id'], 'patch': patch,
                                                 'note': note, 'color': '#654321'})
            current = self.snapshot()['connections'][0]
            self.assertEqual(current['id'], connection['id'])
            self.assertEqual({current['fromPortId'], current['toPortId']}, endpoints)
            self.assertEqual((current['patch'], current['color'], current['note']),
                             (patch, '#654321', note))
        self.reject_unchanged('connections.update', {'connectionId': connection['id'], 'patch': True})
        self.command('connections.disconnect', {'connectionId': connection['id']})
        self.assertEqual(self.snapshot()['connections'], [])
        self.assertEqual(len(self.snapshot()['ports']), 4)
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM inventory_connection_endpoint'), '0')

    def test_power_roles_revalidate_existing_link_and_do_not_accept_poe(self):
        _, _, _, rack = self.hierarchy()
        device, groups, ports = self.device('Power fixture', rack=rack['id'],
                                            groups=[{'type': 'power', 'count': 3}, {'type': 'rj45', 'count': 1}])
        power = next(g for g in groups if g['type'] == 'power')
        power_ports = [p for p in ports if p['groupId'] == power['id']]
        data = next(p for p in ports if p['type'] == 'rj45')
        self.port_changes(device, power, power_ports[:2], {'powerRole': 'inlet'})
        self.reject_unchanged('connections.create', {'fromPortId': power_ports[0]['id'], 'toPortId': power_ports[1]['id']})
        self.reject_unchanged('connections.create', {'fromPortId': power_ports[0]['id'], 'toPortId': data['id']})
        self.port_changes(device, power, [power_ports[1]], {'powerRole': 'outlet'})
        connection = self.connect(power_ports[0], power_ports[1])
        base = {'deviceId': device['id'], 'groupId': power['id'], 'groupType': 'power', 'portIds': [power_ports[0]['id']]}
        self.reject_unchanged('ports.update', {**base, 'changes': {'powerRole': 'outlet'}})
        self.reject_unchanged('ports.update', {**base, 'changes': {'poe': True}})
        self.assertEqual(self.snapshot()['connections'], [connection])

    def test_connection_batch_is_atomic_and_rejects_repeated_port(self):
        _, _, _, rack = self.hierarchy()
        _, _, ports = self.device('Batch fixture', rack=rack['id'], groups=[{'type': 'rj45', 'count': 6}])
        first = {'fromPortId': ports[0]['id'], 'toPortId': ports[1]['id']}
        self.reject_unchanged('connections.createBatch', {'pairs': [first, {'fromPortId': ports[1]['id'], 'toPortId': ports[2]['id']}]})
        self.reject_unchanged('connections.createBatch', {'pairs': [first, {'fromPortId': ports[2]['id'], 'toPortId': uid()}]})
        self.command('connections.createBatch', {'pairs': [first, {'fromPortId': ports[2]['id'], 'toPortId': ports[3]['id']}]})
        current = self.snapshot()['connections']
        self.assertEqual(len(current), 2)
        self.assertEqual(len({p for c in current for p in (c['fromPortId'], c['toPortId'])}), 4)
        self.reject_unchanged('connections.createBatch', {'pairs': [{'fromPortId': ports[4]['id'], 'toPortId': ports[5]['id']}, first]})

    def test_connections_cross_customer_port_rejected(self):
        _, _, _, rack = self.hierarchy()
        _, _, ports = self.device('Local device', rack=rack['id'])
        other = self.customer('Foreign cable client')['id']
        _, _, _, foreign_rack = self.hierarchy(' Other', other)
        _, _, foreign_ports = self.device('Foreign device', rack=foreign_rack['id'], customer=other)
        self.reject_unchanged('connections.create', {'fromPortId': ports[0]['id'], 'toPortId': foreign_ports[0]['id']})
        self.assertEqual(self.snapshot(other)['connections'], [])

    def test_rack_capacity_is_checked_before_atomic_device_creation(self):
        rack = self.create('rack', {'name': 'Capacity rack', 'sizeU': 2}, 'racks')
        self.device('Existing one U', rack=rack['id'], size=1)
        self.reject_unchanged('device.create', {'name': 'Would exceed capacity', 'kind': 'rackEquipment',
                              'rackId': rack['id'], 'sizeU': 2,
                              'portGroups': [{'type': 'rj45', 'count': 48}]})
        self.assertEqual(len(self.snapshot()['devices']), 1)
        self.assertEqual(len(self.snapshot()['ports']), 4)

    def test_two_writers_same_port_only_one_cable_commits(self):
        _, _, _, rack = self.hierarchy()
        _, _, ports = self.device('Port contention', rack=rack['id'])
        revision, barrier = self.snapshot()['revision'], threading.Barrier(2)
        def attempt(index):
            barrier.wait(timeout=10)
            return self.admin.request('POST', f'/api/v1/customers/{self.customer_id}/commands',
                                      {'type': 'connections.create', 'payload': {'fromPortId': ports[0]['id'], 'toPortId': ports[index + 1]['id']}},
                                      {'If-Match': f'"{revision}"', 'Idempotency-Key': uid(), 'X-RackClick-Actor': self.admin_id})
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(attempt, range(2)))
        self.assertEqual(sorted(r.status for r in responses), [200, 412])
        project = self.snapshot()
        self.assertEqual(len(project['connections']), 1)
        self.assertEqual(project['revision'], revision + 1)

    def test_postgres_constraints_enforce_scope_group_placement_and_two_endpoints(self):
        _, _, room, rack = self.hierarchy()
        device, groups, ports = self.device('Constraint ports', rack=rack['id'])
        second, _, _ = self.device('Other device', rack=rack['id'])
        dose, _, _ = self.device('Constraint Dose', kind='dose', room=room['id'])
        other = self.customer('Constraint foreign client')['id']
        foreign_site = self.create('site', {'name': 'Foreign scope'}, 'sites', other)
        before = self.snapshot()
        def rejected_sql(statement, condition):
            self.lab.sql(self.db, 'DO $$ BEGIN BEGIN ' + statement + '; SET CONSTRAINTS ALL IMMEDIATE; '
                         "RAISE EXCEPTION 'QA expected database constraint was not enforced'; "
                         'EXCEPTION WHEN ' + condition + ' THEN NULL; END; END $$;')
        rejected_sql(f"INSERT INTO inventory_building(id,systemhaus_id,customer_id,site_id,name) "
                     f"VALUES('{uid()}','{self.house_id}','{self.customer_id}','{foreign_site['id']}','Cross parent')",
                     'foreign_key_violation')
        rejected_sql(f"UPDATE inventory_port SET device_id='{second['id']}' WHERE id='{ports[0]['id']}'", 'foreign_key_violation')
        rejected_sql(f"UPDATE inventory_port SET type='power' WHERE id='{ports[0]['id']}'", 'foreign_key_violation')
        rejected_sql(f"UPDATE inventory_device SET sort_order={device['sortOrder']} WHERE id='{second['id']}'", 'unique_violation')
        rejected_sql(f"UPDATE inventory_device SET rack_id='{rack['id']}',size_u=1 WHERE id='{dose['id']}'", 'check_violation')
        empty_connection = uid()
        rejected_sql(f"INSERT INTO inventory_connection(id,systemhaus_id,customer_id) "
                     f"VALUES('{empty_connection}','{self.house_id}','{self.customer_id}')", 'check_violation')
        one_connection = uid()
        rejected_sql(f"INSERT INTO inventory_connection(id,systemhaus_id,customer_id) "
                     f"VALUES('{one_connection}','{self.house_id}','{self.customer_id}'); "
                     f"INSERT INTO inventory_connection_endpoint VALUES('{self.house_id}','{self.customer_id}','{one_connection}',0,'{ports[0]['id']}')",
                     'check_violation')
        self.assertEqual(self.snapshot(), before)
        connection = self.connect(ports[0], ports[1])
        snapshot = self.snapshot()
        rejected_sql(f"DELETE FROM inventory_connection_endpoint WHERE connection_id='{connection['id']}' AND ordinal=0", 'check_violation')
        duplicate = uid()
        rejected_sql(f"INSERT INTO inventory_connection(id,systemhaus_id,customer_id) "
                     f"VALUES('{duplicate}','{self.house_id}','{self.customer_id}'); "
                     f"INSERT INTO inventory_connection_endpoint VALUES('{self.house_id}','{self.customer_id}','{duplicate}',0,'{ports[0]['id']}')",
                     'unique_violation')
        self.assertEqual(self.snapshot(), snapshot)

    def test_edit_groups_add_two_preserves_ids_attributes_and_connection(self):
        _, _, _, rack = self.hierarchy()
        device, groups, ports = self.device('Expand group', rack=rack['id'], groups=[{'type': 'rj45_poe', 'count': 2}])
        other, _, other_ports = self.device('Peer', rack=rack['id'])
        self.port_changes(device, groups[0], [ports[0]], {'watts': 18, 'color': '#aabbcc', 'label': 'Keep me', 'face': 'rear'})
        connection = self.connect(ports[0], other_ports[0], note='Keep expansion link', color='#123abc', patch='progress')
        before = {p['id']: p for p in self.snapshot()['ports'] if p['deviceId'] == device['id']}
        self.command('device.editPortGroups', {'deviceId': device['id'], 'groups': self.desired_groups(device['id'], add=2),
                                               'removedPortIds': []})
        after = {p['id']: p for p in self.snapshot()['ports'] if p['deviceId'] == device['id']}
        self.assertEqual(len(after), 4)
        for port_id, original in before.items():
            self.assertEqual(after[port_id], original)
        self.assertIn(connection, self.snapshot()['connections'])

    def test_edit_groups_reduction_requires_exact_preview_and_removes_only_impact(self):
        _, _, _, rack = self.hierarchy()
        device, _, ports = self.device('Reduce group', rack=rack['id'])
        _, _, other_ports = self.device('Reduction peer', rack=rack['id'])
        removed_link = self.connect(ports[0], other_ports[0])
        kept_link = self.connect(ports[1], other_ports[1])
        payload = {'deviceId': device['id'], 'groups': self.desired_groups(device['id'], removed=[ports[0]['id']]),
                   'removedPortIds': [ports[0]['id']]}
        self.reject_unchanged('device.editPortGroups', payload)
        preview = self.preview('device.editPortGroups', payload)
        self.assertEqual(set(preview['impact']['portIds']), {ports[0]['id']})
        self.assertEqual(set(preview['impact']['connectionIds']), {removed_link['id']})
        changed = json.loads(json.dumps(payload))
        changed['groups'][0]['name'] = 'Changed after preview'
        changed['confirmationToken'] = preview['confirmationToken']
        self.reject_unchanged('device.editPortGroups', changed, allowed=(403, 404, 409, 422))
        self.command('device.editPortGroups', {**payload, 'confirmationToken': preview['confirmationToken']})
        project = self.snapshot()
        self.assertNotIn(ports[0]['id'], {p['id'] for p in project['ports']})
        self.assertIn(ports[1]['id'], {p['id'] for p in project['ports']})
        self.assertEqual(project['connections'], [kept_link])
        self.assertIn(other_ports[0]['id'], {p['id'] for p in project['ports']})

    def test_preview_token_bound_to_revision_and_actor(self):
        _, _, _, rack = self.hierarchy()
        device, _, _ = self.device('Delete with preview', rack=rack['id'])
        payload = {'id': device['id']}
        preview = self.preview('device.delete', payload)
        original = self.snapshot()
        editor, _, _ = self.add_user('qa-delete-other', ['inventory.read', 'inventory.edit', 'inventory.delete'], self.customer_id)
        response = editor.request('POST', f'/api/v1/customers/{self.customer_id}/commands',
                                   {'type': 'device.delete', 'payload': {**payload, 'confirmationToken': preview['confirmationToken']}},
                                   {'If-Match': f'"{preview["revision"]}"', 'Idempotency-Key': uid(), 'X-RackClick-Actor': editor.actor_id})
        self.assertIn(response.status, (403, 409, 422))
        self.assertEqual(self.snapshot(), original)
        self.command('site.create', {'name': 'Changes revision after preview'})
        self.reject_unchanged('device.delete', {**payload, 'confirmationToken': preview['confirmationToken']}, allowed=(403, 409, 422))
        fresh = self.preview('device.delete', payload)
        self.command('device.delete', {**payload, 'confirmationToken': fresh['confirmationToken']})
        self.assertEqual(self.snapshot()['devices'], [])

    def test_device_update_move_reorder_preserves_ports_and_cables(self):
        _, _, room, rack = self.hierarchy()
        rack2 = self.create('rack', {'name': 'Move target', 'roomId': room['id'], 'sizeU': 42}, 'racks')
        first, _, first_ports = self.device('Move first', rack=rack['id'])
        second, _, second_ports = self.device('Keep second', rack=rack['id'])
        connection = self.connect(first_ports[0], second_ports[0], patch='done')
        self.command('device.update', {'id': first['id'], 'name': 'Renamed device', 'properties': {'serial': 'Synthetic serial'}})
        self.command('device.reorder', {'rackId': rack['id'], 'deviceIds': [second['id'], first['id']]})
        rows = [d for d in self.snapshot()['devices'] if d['rackId'] == rack['id']]
        self.assertEqual([d['id'] for d in sorted(rows, key=lambda d: d['sortOrder'])], [second['id'], first['id']])
        self.reject_unchanged('device.reorder', {'rackId': rack['id'], 'deviceIds': [first['id'], first['id']]})
        before_ports = self.snapshot()['ports']
        self.command('device.move', {'id': first['id'], 'rackId': rack2['id']})
        current = next(d for d in self.snapshot()['devices'] if d['id'] == first['id'])
        self.assertEqual((current['name'], current['rackId'], current['properties']['serial']),
                         ('Renamed device', rack2['id'], 'Synthetic serial'))
        self.assertEqual(self.snapshot()['ports'], before_ports)
        self.assertEqual(self.snapshot()['connections'], [connection])

    def test_dose_move_room_retains_identity_and_room_scope(self):
        _, building, room, _ = self.hierarchy()
        other_room = self.create('room', {'name': 'Second room', 'buildingId': building['id']}, 'rooms')
        dose, _, ports = self.device('Moving Dose', kind='dose', room=room['id'])
        final, _, peer_ports = self.device('Stationary final', kind='endDevice', room=room['id'])
        connection = self.connect(ports[0], peer_ports[0])
        self.command('device.move', {'id': dose['id'], 'roomId': other_room['id']})
        current = next(d for d in self.snapshot()['devices'] if d['id'] == dose['id'])
        self.assertEqual(current['roomId'], other_room['id'])
        self.assertIsNone(current['rackId'])
        self.assertEqual(self.snapshot()['connections'], [connection])

    def test_rack_duplicate_remaps_internal_ids_excludes_external_cable(self):
        _, _, room, rack = self.hierarchy()
        external_rack = self.create('rack', {'name': 'External rack', 'roomId': room['id'], 'sizeU': 42}, 'racks')
        first, _, first_ports = self.device('Source A', rack=rack['id'])
        second, _, second_ports = self.device('Source B', rack=rack['id'])
        external, _, external_ports = self.device('External device', rack=external_rack['id'])
        internal_link = self.connect(first_ports[0], second_ports[0], note='Internal cloned\nLínea 日本語', color='#112233', patch='tested')
        external_link = self.connect(first_ports[1], external_ports[0], note='External unchanged')
        before = self.snapshot()
        self.command('rack.duplicate', {'id': rack['id'], 'name': 'Duplicated rack', 'includeConnections': True})
        after = self.snapshot()
        new_racks = [r for r in after['racks'] if r['id'] not in {v['id'] for v in before['racks']}]
        self.assertEqual(len(new_racks), 1)
        copied_devices = [d for d in after['devices'] if d['rackId'] == new_racks[0]['id']]
        self.assertEqual(len(copied_devices), 2)
        copied_ids = {d['id'] for d in copied_devices}
        copied_ports = {p['id'] for p in after['ports'] if p['deviceId'] in copied_ids}
        self.assertEqual(len(copied_ports), 8)
        self.assertFalse(copied_ports & {p['id'] for p in before['ports']})
        self.assertIn(internal_link, after['connections'])
        self.assertIn(external_link, after['connections'])
        new_connections = [c for c in after['connections'] if c['id'] not in {v['id'] for v in before['connections']}]
        self.assertEqual(len(new_connections), 1)
        self.assertTrue({new_connections[0]['fromPortId'], new_connections[0]['toPortId']} <= copied_ports)
        self.assertEqual({k: new_connections[0][k] for k in ('note', 'color', 'patch')},
                         {k: internal_link[k] for k in ('note', 'color', 'patch')})

    def test_rack_delete_confirmed_impact_includes_external_cable_not_external_device(self):
        _, _, room, rack = self.hierarchy()
        external_rack = self.create('rack', {'name': 'Preserved rack', 'roomId': room['id'], 'sizeU': 42}, 'racks')
        inside, _, inside_ports = self.device('Inside deleted rack', rack=rack['id'])
        outside, _, outside_ports = self.device('Outside preserved rack', rack=external_rack['id'])
        link = self.connect(inside_ports[0], outside_ports[0])
        payload = {'id': rack['id']}
        self.reject_unchanged('rack.delete', payload)
        preview = self.preview('rack.delete', payload)
        self.assertEqual(set(preview['impact']['rackIds']), {rack['id']})
        self.assertEqual(set(preview['impact']['deviceIds']), {inside['id']})
        self.assertEqual(set(preview['impact']['connectionIds']), {link['id']})
        self.command('rack.delete', {**payload, 'confirmationToken': preview['confirmationToken']})
        project = self.snapshot()
        self.assertEqual({r['id'] for r in project['racks']}, {external_rack['id']})
        self.assertEqual({d['id'] for d in project['devices']}, {outside['id']})
        self.assertEqual({p['id'] for p in project['ports']}, {p['id'] for p in outside_ports})
        self.assertEqual(project['connections'], [])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=WORKSPACE / 'evidence/s1-20260928/inventory-qa')
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    names = [name for name in unittest.defaultTestLoader.getTestCaseNames(InventoryPostgres) if args.filter in name]
    if not names:
        parser.error('No test matched the filter; no laboratory was created')
    args.evidence.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    run_id = started.strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    logfile = args.evidence / f'{run_id}.log'
    metadata = {'runId': run_id, 'startedUtc': started.isoformat(), 'platform': platform.platform(),
                'python': platform.python_version(), 'dllSha256': hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest(),
                'suiteSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'dllPath': str(DEFAULT_DLL.relative_to(WORKSPACE)), 'filter': args.filter,
                'historicalResultsReused': False, 'fixtureAdminOperations': 'Explicit SQL fixtures; no administration endpoints implied',
                'transport': 'Explicit Development loopback HTTP; production HTTPS not certified here'}
    with logfile.open('w', encoding='utf-8') as output, Lab('inventory-qa') as lab:
        InventoryPostgres.lab = lab
        metadata['labId'] = lab.id
        metadata['postgresVersion'] = lab.sql('postgres', 'SHOW server_version')
        metadata['sdkVersion'] = subprocess.run([str(lab.dotnet), '--version'], cwd=WORKSPACE / 'development/server',
                                                env=lab.environment(), capture_output=True, text=True,
                                                check=True, creationflags=NO_WINDOW).stdout.strip()
        suite = unittest.TestSuite(InventoryPostgres(name) for name in names)
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(suite)
        metadata.update(testsRun=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                        successful=result.wasSuccessful(), cases=result.records,
                        databases=[{'name': row['name'], 'label': row['label']} for row in lab.metadata['databases']])
    metadata['finishedUtc'] = datetime.now(timezone.utc).isoformat()
    metadata['labStopped'] = not lab.running
    (args.evidence / f'{run_id}.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Evidence: {logfile}')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
