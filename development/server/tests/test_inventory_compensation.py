"""Compensation66: frozen server/frontend; fresh Windows PostgreSQL fixtures only."""
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
from test_inventory_postgres import InventoryPostgres


def uid(): return str(uuid.uuid4())


class CompensationPostgres(InventoryChangesPostgres):
    def fixture(self, client=None):
        _, _, _, rack = self.hierarchy()
        device, groups, ports = self.device('Compensate heterogeneous', rack=rack['id'])
        self.connect(ports[0], ports[3])
        for i, port in enumerate(ports[:3]):
            self.port_changes(device, groups[0], [port], {'label': ['Ñ 原始', 'B 😃', ''][i],
                'color': [None, '#12aBcD', '#112233'][i], 'status': ['free', 'reserved', 'faulty'][i],
                'face': ['front', 'rear', 'auto'][i]})
        before = self.snapshot()
        made = self.port_changes(device, groups[0], ports[:3], {'status': 'disabled', 'label': 'Unified',
            'color': '#aabbcc', 'face': 'rear'}, client=client).json()
        return device, groups[0], ports[:3], before, made

    def undo(self, made, **options):
        return self.command('operations.compensate', {'operationId': made['operationId']}, **options)

    def stable_rejection(self, made, status, code, **options):
        before = self.durable()
        self.expect(self.undo(made, status=status, **options), status, code)
        self.assertEqual(self.durable(), before)

    def inventory_tables(self):
        names = ['inventory_site', 'inventory_building', 'inventory_room', 'inventory_rack', 'inventory_device',
                 'inventory_port_group', 'inventory_port', 'inventory_connection', 'inventory_connection_endpoint']
        return {name: json.loads(self.lab.sql(self.db, f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM {name} t")) for name in names}

    def test_compensation_heterogeneous_persistence_context_openapi(self):
        device, group, ports, before, made = self.fixture()
        tables = self.inventory_tables(); revision = made['revision']
        reader, _, _ = self.add_user('compensation-reader', ['inventory.read'], self.customer_id)
        result = self.undo(made).json()
        self.assertEqual(result['revision'], revision + 1)
        self.assertEqual(result['result'], {'resourceId': device['id'], 'changedIds': [p['id'] for p in ports], 'compensatedOperationId': made['operationId']})
        after = self.snapshot(); self.assertEqual(after['ports'], before['ports'])
        current = self.inventory_tables()
        for name in tables:
            if name != 'inventory_port': self.assertEqual(current[name], tables[name])
        feed = self.poll(revision, client=reader)
        self.assertFalse(feed['refreshRequired']); self.assertEqual(len(feed['events']), 1)
        event = feed['events'][0]
        self.assertEqual(event['action'], 'inventory.operations.compensate'); self.assertEqual(event['context']['status'], 'captured')
        self.assertEqual([p['id'] for p in event['context']['afterPorts']], [p['id'] for p in ports])
        self.assertNotIn('Unified', json.dumps(feed)); self.assertNotIn('properties', json.dumps(feed))
        audit = json.loads(self.lab.sql(self.db, f"SELECT jsonb_build_array(before_json,after_json) FROM audit_event WHERE id='{result['operationId']}'"))
        self.assertEqual([p['id'] for p in audit[0]['data']], [p['id'] for p in ports]); self.assertEqual(len(audit[1]['data']), 3)
        document = self.expect(self.admin.request('GET', '/api/v1/openapi.json'), 200).json()
        choices = document['components']['schemas']['InventoryCommandRequest']['oneOf']
        schema = next(c['properties']['payload'] for c in choices if c['properties']['type']['enum'] == ['operations.compensate'])
        self.assertFalse(schema['additionalProperties']); self.assertEqual(schema['required'], ['operationId'])
        self.server.close(); self.server = self.lab.start_server(self.db, dll=self.dll, frontend=self.frontend)
        reader.server = self.admin.server = self.server
        self.assertEqual(self.snapshot(client=reader), after)

    def test_compensation_invalid_unsupported_foreign_and_noop(self):
        device, group, ports, _, made = self.fixture()
        actor, _, _ = self.add_user('other-editor', ['inventory.read', 'inventory.edit'], self.customer_id)
        self.stable_rejection(made, 404, 'not_found', client=actor)
        self.stable_rejection({'operationId': uid()}, 404, 'not_found')
        foreign = self.customer('Other compensation customer')['id']
        self.stable_rejection(made, 404, 'not_found', customer=foreign)
        house, user, grant, customer = uid(), uid(), uid(), uid()
        self.lab.sql(self.db, f"""DROP INDEX one_systemhaus_per_installation;
            INSERT INTO systemhaus(id,name) VALUES('{house}','Foreign compensation house');
            INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{user}','{house}','foreign-compensator',password_hash FROM app_user WHERE id='{self.admin_id}';
            INSERT INTO user_group VALUES('{grant}','{house}','Foreign editors');
            INSERT INTO user_group_member VALUES('{house}','{user}','{grant}');
            INSERT INTO permission_grant VALUES('{uid()}','{house}','{grant}','inventory.read',NULL,NULL),('{uid()}','{house}','{grant}','inventory.edit',NULL,NULL);
            INSERT INTO customer(id,systemhaus_id,name) VALUES('{customer}','{house}','Foreign customer');""")
        foreign_actor = Client(self.server); foreign_actor.actor_id = user
        self.expect(foreign_actor.login('foreign-compensator', self.password), 200)
        previous = self.admin, self.admin_id, self.customer_id
        try:
            self.admin, self.admin_id, self.customer_id = foreign_actor, user, customer
            _, _, _, _, foreign_made = self.fixture()
        finally:
            self.admin, self.admin_id, self.customer_id = previous
        self.stable_rejection(foreign_made, 404, 'not_found')
        self.stable_rejection(made, 404, 'not_found', client=foreign_actor)
        for payload in ({'operationId': made['operationId'], 'before': []}, {}, {'operationId': None}, {'operationId': str(uuid.UUID(int=0))}):
            durable = self.durable(); self.command('operations.compensate', payload, status=422); self.assertEqual(self.durable(), durable)
        # Raw JSON proves duplicate keys are rejected before lazy JsonNode decoding.
        headers = {'If-Match': f'"{self.snapshot()["revision"]}"', 'Idempotency-Key': uid(), 'X-RackClick-Actor': self.admin_id, 'Content-Type': 'application/json'}
        self.expect(self.admin.request('POST', f'/api/v1/customers/{self.customer_id}/commands',
            ('{"type":"operations.compensate","payload":{"operationId":"'+made['operationId']+'","operationId":"'+uid()+'"}}').encode(), headers), 422)
        # Expanded180 scope: PoE/watts now invert exact previous per-port values.
        for changes in ({'poe': True}, {'watts': 17}):
            original_ports = self.snapshot()['ports']
            original = self.port_changes(device, group, ports, changes).json()
            self.undo(original)
            self.assertEqual(self.snapshot()['ports'], original_ports)
        for changes in ({'properties': {'extra': 'unsupported'}}, {'label': 'Unified'}):
            original = self.port_changes(device, group, ports, changes).json()
            self.stable_rejection(original, 422, 'compensation_unsupported')
        unsupported = self.command('site.create', {'name': 'Unsupported action'}).json()
        self.stable_rejection(unsupported, 422, 'compensation_unsupported')
        source = self.port_changes(device, group, ports, {'label': 'eligible again'}).json()
        operation = self.lab.sql(self.db, f"SELECT row_to_json(o) FROM operation o WHERE request_id='{source['requestId']}'")
        self.lab.sql(self.db, f"DELETE FROM operation WHERE request_id='{source['requestId']}'")
        self.stable_rejection(source, 404, 'not_found')
        self.lab.sql(self.db, f"INSERT INTO operation SELECT * FROM jsonb_populate_record(NULL::operation,{literal(operation)}::jsonb)")
        for expression in ("jsonb_set(result_json,'{revision}','0')", "jsonb_set(result_json,'{requestId}',to_jsonb('" + uid() + "'::text))"):
            self.lab.sql(self.db, f"UPDATE operation SET result_json={expression} WHERE request_id='{source['requestId']}'")
            self.stable_rejection(source, 422, 'compensation_unsupported')
            self.lab.sql(self.db, f"UPDATE operation SET result_json={literal(json.dumps(json.loads(operation)['result_json']))}::jsonb WHERE request_id='{source['requestId']}'")
        audit = self.lab.sql(self.db, f"SELECT before_json FROM audit_event WHERE id='{source['operationId']}'")
        for expression in ("before_json-'data'", "jsonb_set(before_json,'{data,0,poe}','null')",
                           "jsonb_set(before_json,'{data,0,unknown}','1')", "jsonb_set(before_json,'{data}',jsonb_build_array(before_json->'data'->0,before_json->'data'->0))",
                           "jsonb_set(before_json,'{data,0,label}',to_jsonb(repeat('a',8388609)))"):
            self.lab.sql(self.db, f"UPDATE audit_event SET before_json={expression} WHERE id='{source['operationId']}'")
            self.stable_rejection(source, 422, 'compensation_unsupported')
            self.lab.sql(self.db, f"UPDATE audit_event SET before_json={literal(audit)}::jsonb WHERE id='{source['operationId']}'")
        compensated = self.undo(source).json()
        self.stable_rejection(compensated, 422, 'compensation_unsupported')

    def test_compensation_latest_stale_tamper_atomic(self):
        device, group, ports, _, made = self.fixture()
        self.stable_rejection(made, 412, 'revision_conflict', revision=made['revision'] - 1)
        original_rows = self.inventory_tables()['inventory_port']
        # Direct isolated fixture changes a nonallowed field without advancing revision.
        self.lab.sql(self.db, f"UPDATE inventory_port SET properties='{{\"tamper\":true}}' WHERE id='{ports[1]['id']}'")
        self.stable_rejection(made, 409, 'compensation_state_conflict')
        self.lab.sql(self.db, f"UPDATE inventory_port SET properties='{{}}' WHERE id='{ports[1]['id']}'")
        self.assertEqual(self.inventory_tables()['inventory_port'], original_rows)
        self.lab.sql(self.db, f"DELETE FROM inventory_port WHERE id='{ports[2]['id']}'")
        self.stable_rejection(made, 409, 'compensation_state_conflict')
        row = next(p for p in original_rows if p['id'] == ports[2]['id']); row.pop('connector_family')
        columns = ','.join(row)
        self.lab.sql(self.db, f"INSERT INTO inventory_port({columns}) SELECT {columns} FROM jsonb_populate_record(NULL::inventory_port,{literal(json.dumps(row))}::jsonb)")
        self.command('device.update', {'id': device['id'], 'name': 'Unrelated newer revision'})
        self.stable_rejection(made, 409, 'compensation_not_latest')
        newer = self.port_changes(device, group, ports, {'label': 'ABA step'}).json()
        self.port_changes(device, group, ports, {'label': 'Unified'})
        self.stable_rejection(newer, 409, 'compensation_not_latest')

    def wait_for(self, sql):
        until = time.monotonic() + 3
        while time.monotonic() < until:
            if int(self.lab.sql(self.db, sql, admin=True)): return
            time.sleep(.025)
        self.fail('Real PostgreSQL wait witness absent')

    def waiting(self, client, made, table, identity, mutate, status, code):
        revision = self.snapshot()['revision']; label = 'compensation66_' + uid()
        with ThreadPoolExecutor(2) as pool:
            holder = pool.submit(self.lab.sql, self.db, f"SET application_name='{label}'; BEGIN; SELECT id FROM {table} WHERE id='{identity}' FOR UPDATE; SELECT pg_sleep(3); COMMIT;")
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            pending = pool.submit(self.undo, made, client=client, revision=revision, status=status)
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
            mutate(); self.assertFalse(holder.done())
            self.expect(pending.result(timeout=15), status, code); holder.result(timeout=10)

    def test_compensation_permission_session_waits_and_precommit_expiry(self):
        _, group, ports, _, _ = self.fixture()
        for capability, status, code in [('inventory.edit', 403, 'forbidden'), ('inventory.read', 404, 'not_found')]:
            worker, grant, _ = self.add_user('revoke-' + capability, ['inventory.read', 'inventory.edit'], self.customer_id)
            source = self.command('ports.update', {'deviceId': ports[0]['deviceId'], 'groupId': group['id'], 'groupType': group['type'],
                'portIds': [p['id'] for p in ports], 'changes': {'label': uid()}}, client=worker).json()
            before = self.snapshot()
            self.waiting(worker, source, 'customer', self.customer_id,
                lambda: self.lab.sql(self.db, f"DELETE FROM permission_grant WHERE user_group_id='{grant}' AND capability={literal(capability)}"), status, code)
            self.assertEqual(self.snapshot(), before)
        worker, _, _ = self.add_user('expiry-worker', ['inventory.read', 'inventory.edit'], self.customer_id)
        source = self.command('ports.update', {'deviceId': ports[0]['deviceId'], 'groupId': group['id'], 'groupType': group['type'],
            'portIds': [p['id'] for p in ports], 'changes': {'label': 'expiry source'}}, client=worker).json()
        before = self.snapshot()
        self.lab.sql(self.db, f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{worker.actor_id}'")
        self.waiting(worker, source, 'app_user', worker.actor_id, lambda: None, 401, 'authentication_required')
        self.assertEqual(self.snapshot(), before)
        self.expect(worker.login('expiry-worker', self.password), 200)
        self.waiting(worker, source, 'customer', self.customer_id,
            lambda: self.lab.sql(self.db, f"DELETE FROM app_session WHERE user_id='{worker.actor_id}'"), 401, 'authentication_required')
        self.assertEqual(self.snapshot(), before)
        # Audit trigger waits after all port updates and before the final wall-clock check.
        self.expect(worker.login('expiry-worker', self.password), 200)
        self.lab.sql(self.db, "CREATE FUNCTION slow_compensation66() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='inventory.operations.compensate' THEN PERFORM pg_sleep(3); END IF; RETURN NEW; END $$; CREATE TRIGGER slow_compensation66 BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION slow_compensation66()")
        self.lab.sql(self.db, f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{worker.actor_id}'")
        durable = self.durable(); self.expect(self.undo(source, client=worker, status=401), 401, 'authentication_required'); self.assertEqual(self.durable(), durable)

    def test_compensation_replay_cancel_rollback_concurrency(self):
        _, _, ports, _, made = self.fixture()
        payload = {'operationId': made['operationId']}; revision = made['revision']; key = uid()
        self.assertEqual(self.cancel('operations.compensate', payload, key, revision).json()['state'], 'cancelled')
        self.stable_rejection(made, 409, 'operation_cancelled', key=key, revision=revision)
        # Late audit constraint error after port writes must roll back all durable tables.
        self.lab.sql(self.db, "CREATE FUNCTION fail_compensation66() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='inventory.operations.compensate' THEN RAISE EXCEPTION 'fixture rollback' USING ERRCODE='23514'; END IF; RETURN NEW; END $$; CREATE TRIGGER fail_compensation66 BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION fail_compensation66()")
        self.stable_rejection(made, 409, 'inventory_conflict')
        self.lab.sql(self.db, 'DROP TRIGGER fail_compensation66 ON audit_event; DROP FUNCTION fail_compensation66()')
        with ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(self.admin.request, 'POST', f'/api/v1/customers/{self.customer_id}/commands',
                {'type': 'operations.compensate', 'payload': payload}, {'If-Match': f'"{revision}"', 'Idempotency-Key': uid(), 'X-RackClick-Actor': self.admin_id}) for _ in range(2)]
            responses = [f.result(timeout=15) for f in futures]
        self.assertEqual(sorted(r.status for r in responses), [200, 412])
        committed = next(r.json() for r in responses if r.status == 200)
        key = committed['requestId']
        self.assertEqual(self.cancel('operations.compensate', payload, key, revision).json()['operation'], committed)
        self.command('site.create', {'name': 'After undo'})
        durable = self.durable(); self.assertEqual(self.undo(made, key=key, revision=revision).json(), committed); self.assertEqual(self.durable(), durable)
        self.stable_rejection(made, 409, 'compensation_not_latest')
        self.command('operations.compensate', {'operationId': uid()}, key=key, revision=revision, status=409)
        self.assertEqual(self.operation_state(key)['operation'], committed)
        self.assertEqual(self.lab.sql(self.db, "SELECT count(*) FROM audit_event WHERE action='inventory.operations.compensate'"), '1')

    def test_regression_ports_update(self):
        InventoryPostgres.test_port_poe_off_preserves_watts_and_face_identity(self)


def distribution(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob('*')) if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dll', 'frontend', 'evidence'): parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--case', action='append'); args = parser.parse_args()
    names = [n for n in CompensationPostgres.__dict__ if n.startswith('test_')]
    if args.case:
        if set(args.case) - set(names): raise ValueError('Unknown compensation case')
        names = [n for n in names if n in args.case]
    args.evidence.mkdir(parents=True, exist_ok=False)
    args.dll = args.dll.resolve(); args.frontend = args.frontend.resolve()
    files = [p for p in (WORKSPACE/'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files += list((WORKSPACE/'development/server/database').glob('*.sql'))
    files += [Path(__file__).resolve()] + [WORKSPACE/'development/server/tests'/n for n in ['pg_support.py', 'test_inventory_postgres.py', 'test_inventory_changes.py']]
    def sources(): return {p.relative_to(WORKSPACE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original = sources(); server = distribution(args.dll.parent); frontend = distribution(args.frontend)
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(), 'python': platform.python_version(),
        'serverPath': str(args.dll.parent), 'frontendPath': str(args.frontend), 'serverHashes': server, 'frontendHashes': frontend,
        'sourceHashes': original, 'selectedCases': names, 'schemaVersion': 7, 'actualQaOpened': False}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    lab = Lab('inventory-compensation66'); CompensationPostgres.lab = lab
    from pg_support import NO_WINDOW
    report['versions'] = {name: subprocess.run([str(path), '--version'], capture_output=True, text=True, check=True,
        creationflags=NO_WINDOW).stdout.strip() for name, path in [('dotnet', lab.dotnet), ('postgres', lab.pg_bin/'postgres.exe')]}
    CompensationPostgres.dll, CompensationPostgres.frontend = args.dll, args.frontend
    started = time.monotonic()
    with lab, (args.evidence/'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(CompensationPostgres(name) for name in names))
        report.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started, 3), labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers), sourcesUnchanged=original == sources(),
        serverUnchanged=server == distribution(args.dll.parent), frontendUnchanged=frontend == distribution(args.frontend))
    (args.evidence/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return 0 if all(report[k] for k in ('successful','labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged')) else 1


if __name__ == '__main__': sys.exit(main())
