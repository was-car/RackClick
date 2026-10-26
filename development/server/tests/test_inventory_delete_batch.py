"""devices.delete61: explicit frozen server/frontend, fresh native Windows PostgreSQL labs only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest
import uuid

from pg_support import Client, Lab, WORKSPACE, literal
from test_postgres import EvidenceResult, Tee
from test_inventory_changes import InventoryChangesPostgres


def uid(): return str(uuid.uuid4())


class DeleteBatchPostgres(InventoryChangesPostgres):
    def raw_preview(self, payload, client=None, revision=None, customer=None):
        client = client or self.admin
        return client.request('POST', f'/api/v1/customers/{customer or self.customer_id}/commands/preview',
            {'type': 'devices.delete', 'payload': payload},
            {'If-Match': f'"{revision if revision is not None else self.snapshot()["revision"]}"',
             'X-RackClick-Actor': client.actor_id})

    def fixture(self):
        _, _, room, rack = self.hierarchy()
        first, _, ports = self.device('Selected rack equipment', rack=rack['id'])
        second, _, other = self.device('Selected Dose', room=room['id'], kind='dose')
        final, _, ends = self.device('Selected end device', room=room['id'], kind='endDevice')
        preserved_rack = self.create('rack', {'name': 'External rack', 'sizeU': 42}, 'racks')
        retained, _, peers = self.device('Retained external equipment', rack=preserved_rack['id'])
        internal = self.connect(ports[0], other[0])
        external = self.connect(ends[0], peers[0])
        return [first['id'], second['id'], final['id']], retained, [internal['id'], external['id']]

    def test_batch_union_atomic_audit_feed_and_openapi(self):
        ids, retained, links = self.fixture()
        before = self.snapshot(); durable = self.durable()
        preview = self.preview('devices.delete', {'deviceIds': ids})
        self.assertEqual(durable, self.durable())
        impact = preview['impact']
        expected = {'rackIds': [], 'deviceIds': ids,
            'groupIds': [g['id'] for g in before['portGroups'] if g['deviceId'] in ids],
            'portIds': [p['id'] for p in before['ports'] if p['deviceId'] in ids], 'connectionIds': links}
        self.assertEqual({k: set(v) for k, v in impact.items()}, {k: set(v) for k, v in expected.items()})
        payload = {'deviceIds': ids, 'confirmationToken': preview['confirmationToken']}
        made = self.command('devices.delete', payload).json()
        self.assertEqual(made['revision'], before['revision'] + 1)
        self.assertEqual(made['result'], {'resourceId': made['operationId'], 'batchId': made['operationId'], 'removedIds': impact})
        after = self.snapshot()
        self.assertEqual(after['racks'], before['racks'])
        self.assertEqual(after['devices'], [retained]); self.assertEqual(after['connections'], [])
        self.assertEqual(after['ports'], [p for p in before['ports'] if p['deviceId'] == retained['id']])
        audit = json.loads(self.lab.sql(self.db, f"SELECT jsonb_build_object('resource',resource_id,'before',before_json,'after',after_json) FROM audit_event WHERE id='{made['operationId']}'"))
        self.assertEqual(audit['resource'], made['operationId']); self.assertNotEqual(audit['resource'], made['requestId']); self.assertIsNone(audit['after']['data'])
        for collection, key in [('racks', 'rackIds'), ('devices', 'deviceIds'), ('portGroups', 'groupIds'), ('ports', 'portIds'), ('connections', 'connectionIds')]:
            self.assertEqual(audit['before']['data'][collection], [v for v in before[collection] if v['id'] in impact[key]])
        page = self.poll(before['revision'])
        self.assertFalse(page['refreshRequired']); self.assertEqual(len(page['events']), 1)
        event = page['events'][0]
        self.assertEqual((event['action'], event['resourceId'], event['context']), ('inventory.devices.delete', made['operationId'], self.no_context()))
        reader, _, _ = self.add_user('batch-feed-reader', ['inventory.read'], self.customer_id)
        self.assertEqual(self.poll(before['revision'], client=reader), page)
        self.assertEqual(self.command('devices.delete', payload, revision=before['revision'], key=made['requestId']).json(), made)
        self.assertEqual(self.poll(before['revision'], client=reader), page)
        schema = self.expect(self.admin.request('GET', '/api/v1/openapi.json'), 200).json()['components']['schemas']
        variant = next(v for v in schema['InventoryCommandRequest']['oneOf'] if v['properties']['type']['enum'] == ['devices.delete'])
        selection = variant['properties']['payload']['properties']['deviceIds']
        self.assertEqual((selection['minItems'], selection['maxItems'], selection['uniqueItems']), (1, 64, True))
        self.assertNotIn('nullable', schema['InventoryCommandResult']['properties']['result']['properties']['resourceId']); self.assertEqual(schema['InventoryCommandResult']['properties']['result']['properties']['batchId']['format'], 'uuid')
        self.assertEqual(len(schema['InventoryChangeEvent']['properties']['action']['enum']), 27)
        self.server.close(); self.server = self.lab.start_server(self.db, dll=self.dll, frontend=self.frontend); self.admin.server = self.server
        self.assertEqual(self.snapshot(), after)

    def test_batch_invalid_scope_permissions_headers_and_bound(self):
        _, _, _, rack = self.hierarchy()
        first, _, _ = self.device('Validation selected', rack=rack['id'])
        other_customer = self.customer('Other batch customer')['id']
        other_rack = self.create('rack', {'name': 'Other rack', 'sizeU': 42}, 'racks', other_customer)
        foreign, _, _ = self.device('Foreign', rack=other_rack['id'], customer=other_customer)
        editor, _, _ = self.add_user('batch-editor', ['inventory.read', 'inventory.edit'], self.customer_id)
        hidden, _, _ = self.add_user('batch-hidden', ['inventory.delete'], self.customer_id)
        for bad in ({}, {'deviceIds': []}, {'deviceIds': [first['id'], first['id']]}, {'deviceIds': [str(uuid.UUID(int=0))]},
                    {'deviceIds': ['bad']}, {'deviceIds': [uid() for _ in range(65)]}, {'deviceIds': 'bad'}):
            durable = self.durable()
            self.expect(self.raw_preview(bad), 422)
            self.command('devices.delete', bad, status=422)
            self.assertEqual(self.durable(), durable)
        for identity in (foreign['id'], uid()):
            durable = self.durable()
            self.expect(self.raw_preview({'deviceIds': [first['id'], identity]}), 404)
            self.command('devices.delete', {'deviceIds': [first['id'], identity]}, status=404)
            self.assertEqual(self.durable(), durable)
        for actor, status in ((editor, 403), (hidden, 404)):
            self.expect(self.raw_preview({'deviceIds': [first['id']]}, client=actor), status)
            self.command('devices.delete', {'deviceIds': [first['id']]}, client=actor, status=status)
        payload = {'deviceIds': [first['id']]}
        self.command('devices.delete', payload, status=409)
        self.expect(self.raw_preview(payload, revision=1), 412)
        anonymous = Client(self.server)
        for suffix in ('/commands', '/commands/preview'):
            path = f'/api/v1/customers/{self.customer_id}' + suffix
            headers = {'If-Match': f'"{self.snapshot()["revision"]}"', 'X-RackClick-Actor': self.admin_id, 'Idempotency-Key': uid()}
            self.expect(anonymous.request('POST', path, {'type': 'devices.delete', 'payload': payload}, headers), 401)
            self.expect(self.admin.request('POST', path, {'type': 'devices.delete', 'payload': payload}, {**headers, 'X-RackClick-CSRF': 'invalid'}), 403)
        # Exactly 64 real UUIDs, no groups, proves the accepted boundary without 64 HTTP commits.
        extra = [uid() for _ in range(63)]
        self.lab.sql(self.db, 'INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order) VALUES ' + ','.join(
            f"('{identity}','{self.house_id}','{self.customer_id}','rackEquipment','{rack['id']}','Synthetic boundary',1,{i+10})" for i, identity in enumerate(extra)))
        self.assertEqual(len(self.preview('devices.delete', {'deviceIds': [first['id'], *extra]})['impact']['deviceIds']), 64)

    def test_batch_tokens_stale_concurrent_and_replay(self):
        _, _, _, rack = self.hierarchy()
        first, _, _ = self.device('Token selected', rack=rack['id'])
        second, _, _ = self.device('Not selected', rack=rack['id'])
        ids = [first['id']]; preview = self.preview('devices.delete', {'deviceIds': ids}); revision = preview['revision']
        payload = {'deviceIds': ids, 'confirmationToken': preview['confirmationToken']}
        other, group, _ = self.add_user('batch-other', ['inventory.read', 'inventory.delete'], self.customer_id)
        self.command('devices.delete', payload, client=other, status=409)
        self.command('devices.delete', {**payload, 'deviceIds': [second['id']]}, status=409)
        # Changed impact without revision is a SQL-only corruption fixture, never a public API feature.
        self.lab.sql(self.db, f"INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order) VALUES('{uid()}','{self.house_id}','{self.customer_id}','{first['id']}','sfp','added','',9)")
        self.command('devices.delete', payload, status=409)
        preview = self.preview('devices.delete', {'deviceIds': ids}); payload['confirmationToken'] = preview['confirmationToken']
        self.command('device.update', {'id': second['id'], 'name': 'Concurrent change'})
        self.command('devices.delete', payload, revision=revision, status=412)
        preview = self.preview('devices.delete', {'deviceIds': ids}); payload['confirmationToken'] = preview['confirmationToken']; revision = preview['revision']
        key = uid()
        def commit(): return self.admin.request('POST', f'/api/v1/customers/{self.customer_id}/commands', {'type': 'devices.delete', 'payload': payload},
            {'If-Match': f'"{revision}"', 'X-RackClick-Actor': self.admin_id, 'Idempotency-Key': key})
        with ThreadPoolExecutor(2) as pool:
            replies = list(pool.map(lambda _: commit(), range(2)))
        self.assertTrue(all(v.status == 200 for v in replies)); self.assertEqual(replies[0].json(), replies[1].json())
        self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM audit_event WHERE request_id='{key}'"), '1')
        self.assertEqual(self.snapshot()['revision'], revision + 1)
        # Authorized replay even after permission changes is rechecked before the stored result.
        made = replies[0].json()
        self.assertEqual(self.command('devices.delete', payload, revision=revision, key=key).json(), made)
        self.command('devices.delete', {**payload, 'deviceIds': [second['id']]}, revision=revision, key=key, status=409)

    def test_batch_rollback_cancel_and_permission_replay(self):
        _, _, _, rack = self.hierarchy(); first, _, _ = self.device('Rollback selected', rack=rack['id'])
        preview = self.preview('devices.delete', {'deviceIds': [first['id']]})
        payload = {'deviceIds': [first['id']], 'confirmationToken': preview['confirmationToken']}; revision = preview['revision']
        for table in ('audit_event', 'operation'):
            self.lab.sql(self.db, f"CREATE FUNCTION fail_batch61() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic rollback61'; END; $$; CREATE TRIGGER fail_batch61 BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION fail_batch61();")
            durable = self.durable(); key = uid()
            self.command('devices.delete', payload, key=key, status=503)
            self.assertEqual(durable, self.durable()); self.assertEqual(self.operation_state(key)['state'], 'notRecorded')
            self.lab.sql(self.db, f'DROP TRIGGER fail_batch61 ON {table}; DROP FUNCTION fail_batch61()')
        key = uid(); self.assertEqual(self.cancel('devices.delete', payload, key, revision=revision).json()['state'], 'cancelled')
        durable = self.durable(); self.command('devices.delete', payload, key=key, status=409)
        self.assertEqual(durable, self.durable())
        worker, group, _ = self.add_user('batch-worker', ['inventory.read', 'inventory.delete'], self.customer_id)
        preview = self.preview('devices.delete', {'deviceIds': [first['id']]}, client=worker)
        payload['confirmationToken'] = preview['confirmationToken']; key = uid()
        made = self.command('devices.delete', payload, key=key, client=worker).json()
        self.expect(worker.login('batch-worker', self.password), 200)
        self.assertEqual(self.command('devices.delete', payload, revision=revision, key=key, client=worker).json(), made)
        self.lab.sql(self.db, f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability='inventory.delete'")
        self.command('devices.delete', payload, revision=revision, key=key, client=worker, status=403)

    def wait_preview(self, client, payload, table, identity, change, status, writer=None):
        label = 'batch_wait_' + uuid.uuid4().hex[:8]; revision = self.snapshot()['revision']
        with ThreadPoolExecutor(3) as pool:
            holder = pool.submit(self.lab.sql, self.db, f"SET application_name='{label}'; BEGIN; SELECT id FROM {table} WHERE id='{identity}' FOR UPDATE; SELECT pg_sleep(3); COMMIT;")
            self.wait_sql(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            pending = pool.submit(self.raw_preview, payload, client, revision)
            self.wait_sql(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
            self.assertFalse(holder.done()); change()
            writing = pool.submit(writer) if writer else None
            if writing:
                # Both the preview waiting on actor and writer waiting on customer must have real blockers.
                self.wait_sql(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0", minimum=2)
                self.assertFalse(writing.done())
            result = self.expect(pending.result(timeout=15), status)
            holder.result(timeout=10)
            if writing: self.expect(writing.result(timeout=15), 200)
            return result

    def wait_sql(self, sql, minimum=1):
        until = time.monotonic() + 2
        while time.monotonic() < until:
            if int(self.lab.sql(self.db, sql, admin=True)) >= minimum: return
            time.sleep(.025)
        self.fail('Expected PostgreSQL lock witness absent')

    def test_batch_preview_wait_revocation_expiry_and_stable_snapshot(self):
        _, _, _, rack = self.hierarchy(); first, _, _ = self.device('Waiting preview', rack=rack['id']); payload = {'deviceIds': [first['id']]}
        for capability, status in [('inventory.delete', 403), ('inventory.read', 404)]:
            worker, group, _ = self.add_user('wait-' + capability, ['inventory.read', 'inventory.delete'], self.customer_id)
            self.wait_preview(worker, payload, 'customer', self.customer_id,
                lambda: self.lab.sql(self.db, f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability={literal(capability)}"), status)
        worker, _, _ = self.add_user('wait-expiry-batch', ['inventory.read', 'inventory.delete'], self.customer_id)
        self.lab.sql(self.db, f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{worker.actor_id}'")
        self.wait_preview(worker, payload, 'app_user', worker.actor_id, lambda: None, 401)
        worker, _, _ = self.add_user('wait-stable-batch', ['inventory.read', 'inventory.delete'], self.customer_id)
        revision = self.snapshot()['revision']
        def writer():
            return self.admin.request('POST', f'/api/v1/customers/{self.customer_id}/commands', {'type': 'device.update', 'payload': {'id': first['id'], 'name': 'After preview'}},
                {'If-Match': f'"{revision}"', 'X-RackClick-Actor': self.admin_id, 'Idempotency-Key': uid()})
        preview = self.wait_preview(worker, payload, 'app_user', worker.actor_id, lambda: None, 200, writer=writer).json()
        self.assertEqual(preview['revision'], revision); self.assertEqual(preview['impact']['deviceIds'], [first['id']])
        self.command('devices.delete', {**payload, 'confirmationToken': preview['confirmationToken']}, client=worker, revision=revision, status=412)

    def test_regression_single_device_rack_impact(self):
        super().test_rack_delete_confirmed_impact_includes_external_cable_not_external_device()

    def test_regression_apply_idempotency(self):
        super().test_idempotency_replay_scope_body_and_stale_revision()


def distribution(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob('*')) if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True); parser.add_argument('--frontend', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True); parser.add_argument('--case', action='append')
    args = parser.parse_args()
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(DeleteBatchPostgres) if n.startswith('test_batch_') or n in ('test_regression_single_device_rack_impact', 'test_regression_apply_idempotency')]
    if args.case:
        if set(args.case) - set(names): raise ValueError('Unknown batch case')
        names = [n for n in names if n in args.case]
    args.evidence.mkdir(parents=True, exist_ok=False)
    args.dll = args.dll.resolve(); args.frontend = args.frontend.resolve()
    files = list((WORKSPACE/'development/server/src').rglob('*.cs'))
    files = [p for p in files if 'obj' not in p.parts and 'bin' not in p.parts]
    files += list((WORKSPACE/'development/server/database').glob('*.sql'))
    files += [Path(__file__).resolve(), WORKSPACE/'development/server/tests/pg_support.py', WORKSPACE/'development/server/tests/test_inventory_postgres.py', WORKSPACE/'development/server/tests/test_inventory_changes.py']
    def sources(): return {p.relative_to(WORKSPACE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original = sources(); server = distribution(args.dll.parent); frontend = distribution(args.frontend)
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(), 'python': platform.python_version(),
        'serverPath': str(args.dll.parent), 'frontendPath': str(args.frontend), 'serverHashes': server, 'frontendHashes': frontend,
        'sourceHashes': original, 'selectedCases': names, 'schemaVersion': 7, 'actualQaOpened': False,
        'transport': 'Development loopback HTTP; no production HTTPS certification'}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    lab = Lab('inventory-delete-batch61'); DeleteBatchPostgres.lab = lab
    from pg_support import NO_WINDOW
    report['versions'] = {name: subprocess.run([str(path), '--version'], capture_output=True, text=True, check=True,
        creationflags=NO_WINDOW).stdout.strip() for name, path in [('dotnet', lab.dotnet), ('postgres', lab.pg_bin/'postgres.exe')]}
    DeleteBatchPostgres.dll, DeleteBatchPostgres.frontend = args.dll, args.frontend
    started = time.monotonic()
    with lab, (args.evidence/'tests.log').open('w', encoding='utf-8') as output:
        report['tools'] = lab.metadata
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(
            unittest.TestSuite(DeleteBatchPostgres(name) for name in names))
        report.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started, 3), labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers), sourcesUnchanged=original == sources(),
        serverUnchanged=server == distribution(args.dll.parent), frontendUnchanged=frontend == distribution(args.frontend))
    # No private lab paths/config/passwords are copied; tool metadata contains public native versions and flags only.
    report.pop('tools', None)
    (args.evidence/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return 0 if all(report[k] for k in ('successful', 'labStopped', 'serversStopped', 'sourcesUnchanged', 'serverUnchanged', 'frontendUnchanged')) else 1


if __name__ == '__main__': sys.exit(main())
