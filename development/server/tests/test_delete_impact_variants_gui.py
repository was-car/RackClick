"""I-04.05: exact single/mixed deletion impact and SQL-observed cancellation.

Explicit immutable artifacts, fresh Windows/PG/Edge laboratory, no QA/VM.
Browser markers pause the scenario while Python compares durable atomic state.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
sys.path.insert(0, str(ROOT / 'tools/windows'))
from pg_support import Lab, Client, toolchain
from windows_job import run_isolated
from test_room_device_move_gui import fixture as room_fixture
from test_inventory_movement_gui import durable, project_by_id, tree
from test_inventory_duplicate_gui import atomic_state
from test_rack_variants_gui import checked_paths, canonical


def inputs(dll, frontend):
    sources = [Path(__file__), ROOT / 'development/frontend/tests/browser-delete-impact-variants.mjs',
        ROOT / 'development/frontend/tests/browser-quince-support.mjs',
        ROOT / 'development/frontend/tests/browser-client-changes-support.mjs',
        ROOT / 'tools/windows/windows_job.py'] + [Path(__file__).with_name(name) for name in
        ['pg_support.py', 'test_room_device_move_gui.py', 'test_client_changes_gui.py',
         'test_inventory_movement_gui.py', 'test_inventory_duplicate_gui.py', 'test_rack_variants_gui.py']]
    return {'sources': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sources}, 'server': tree(dll.parent), 'frontend': tree(frontend)}


def fixture(lab, db, dll):
    ids, password = room_fixture(lab, db, dll)
    sql = []
    for key, left, right, color in [('batchCable', 'pb', 'pc', '#234567'),
                                  ('protectedCable', 'pa2', 'pc2', '#345678')]:
        ids[key] = str(uuid.uuid4())
        sql.extend([
            f"INSERT INTO inventory_connection(id,systemhaus_id,customer_id,note,color,patch,properties) "
            f"VALUES('{ids[key]}','{ids['house']}','{ids['customer']}','{key} literal <img> Ω','{color}',"
            f"'tested','{{\"fixtureSentinel\":\"{key}\"}}');",
            f"INSERT INTO inventory_connection_endpoint VALUES "
            f"('{ids['house']}','{ids['customer']}','{ids[key]}',0,'{ids[left]}'),"
            f"('{ids['house']}','{ids['customer']}','{ids[key]}',1,'{ids[right]}');"])
    lab.sql(db, 'BEGIN;\n' + '\n'.join(sql) + '\nCOMMIT;', sensitive=True)
    return ids, password


def deleted_inventory(before, removed):
    """Expected deletion derives from original SQL ownership and incident endpoints."""
    removed = set(removed)
    wanted = json.loads(json.dumps(before))
    ports = {row['id'] for row in before['inventory_port'] if row['device_id'] in removed}
    connections = {row['connection_id'] for row in before['inventory_connection_endpoint']
                   if row['port_id'] in ports}
    for table, foreign in [('inventory_device', 'id'), ('inventory_port_group', 'device_id'),
                           ('inventory_port', 'device_id')]:
        wanted[table] = [row for row in wanted[table] if row[foreign] not in removed]
    wanted['inventory_connection'] = [row for row in wanted['inventory_connection']
                                      if row['id'] not in connections]
    wanted['inventory_connection_endpoint'] = [row for row in wanted['inventory_connection_endpoint']
                                               if row['connection_id'] not in connections]
    return wanted, connections


def audit_counts(lab, db):
    return json.loads(lab.sql(db, "SELECT COALESCE(jsonb_object_agg(action,n),'{}') FROM "
                                  "(SELECT action,count(*) n FROM audit_event GROUP BY action) q"))


def count_delta(before, after):
    return {key: after.get(key, 0) - before.get(key, 0) for key in before.keys() | after.keys()
            if after.get(key, 0) != before.get(key, 0)}


def wait_marker(output, name, future):
    deadline = time.monotonic() + 40
    path = output / (name + '-state.json')
    while time.monotonic() < deadline:
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            # Existence can precede completion of writeFile; wait for complete JSON.
            if future.done():
                raise RuntimeError('Browser ended before complete SQL checkpoint ' + name)
            time.sleep(0.04)
    raise TimeoutError('Missing or incomplete SQL checkpoint ' + name)


def continue_browser(output, name, valid):
    destination = output / (name + '-continue.json')
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps({'valid': valid}) + '\n', encoding='utf-8')
    temporary.replace(destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--frontend', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    dll, frontend, output = checked_paths(parser.parse_args())
    output.mkdir(parents=True, exist_ok=False)
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'inputs': inputs(dll, frontend),
              'result': 'FAIL', 'realQaAccessed': False,
              'fixtureCreatedBy': 'SQL synthetic room fixture; deletion commands through GUI only',
              'limits': ['No GUI creation, physical touch hardware, Windows reboot, QA or VM.',
                         'SQL checks cover nine inventory tables plus customer/operations/audit.']}
    started = time.monotonic()
    lab = None
    try:
        lab = Lab('delete-impact-i0405')
        with lab:
            db = lab.create_database('deleteimpact')
            ids, password = fixture(lab, db, dll)
            lab.grant_runtime(db)
            before = durable(lab, db)
            single_expected, single_connections = deleted_inventory(before, [ids['end']])
            final_expected, final_connections = deleted_inventory(before, [ids['end'], ids['dose'], ids['b']])
            assert single_connections == {ids['roomCable']}
            assert final_connections == {ids['roomCable'], ids['cable'], ids['batchCable']}
            assert ids['protectedCable'] not in final_connections
            server = lab.start_server(db, dll=dll, frontend=frontend)
            env = lab.environment()
            env.update(RACKCLICK_TEST_ORIGIN=server.origin, RACKCLICK_TEST_USERNAME='move-admin',
                       RACKCLICK_TEST_PASSWORD=password, RACKCLICK_TEST_OUTPUT=str(output),
                       RACKCLICK_FIXTURE=json.dumps(ids))
            checkpoints = []
            with (output / 'browser.log').open('wb') as log, ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(run_isolated,
                    [str(toolchain()['node']), str(ROOT / 'development/frontend/tests/browser-delete-impact-variants.mjs')],
                    env=env, cwd=ROOT / 'development/frontend', stdout=log, stderr=log, timeout=240)
                baseline = post_single = None
                for name in ['ready', 'single-cancel', 'after-single', 'batch-cancel']:
                    wait_marker(output, name, future)
                    try:
                        current = atomic_state(lab, db)
                        if name == 'ready':
                            assert canonical(durable(lab, db)) == canonical(before)
                            baseline = current
                            audit_before = audit_counts(lab, db)
                            operation_before = int(lab.sql(db, 'SELECT count(*) FROM operation'))
                            revision_before = int(lab.sql(db, f"SELECT revision FROM customer WHERE id='{ids['customer']}'"))
                        elif name == 'single-cancel':
                            assert current == baseline, 'Single cancellation preserves exact durable atomic state'
                        elif name == 'after-single':
                            assert canonical(durable(lab, db)) == canonical(single_expected)
                            assert count_delta(audit_before, audit_counts(lab, db)) == {'inventory.device.delete': 1}
                            assert int(lab.sql(db, 'SELECT count(*) FROM operation')) == operation_before + 1
                            assert int(lab.sql(db, f"SELECT revision FROM customer WHERE id='{ids['customer']}'")) == revision_before + 1
                            post_single = current
                        else:
                            assert current == post_single, 'Mixed batch cancellation preserves exact durable atomic state'
                        checkpoints.append({'name': name, 'valid': True})
                        continue_browser(output, name, True)
                    except Exception:
                        continue_browser(output, name, False)
                        raise
                done = future.result()
            report.update(browserExitCode=done.returncode, sqlCheckpoints=checkpoints)
            if done.returncode:
                raise RuntimeError('Browser failed; preserve its isolated sanitized output')
            expected = json.loads((output / 'expected-project.json').read_text(encoding='utf-8'))
            details = json.loads((output / 'delete-impact-details.json').read_text(encoding='utf-8'))
            assert [row['type'] for row in details['writes']] == ['device.delete', 'devices.delete']
            assert details['writes'][0]['payload'] == {'id': ids['end']}
            assert details['writes'][1]['payload'] == {'deviceIds': [ids['dose'], ids['b']]}
            assert all(row['hasConfirmationToken'] for row in details['writes'])
            after = durable(lab, db)
            assert canonical(after) == canonical(final_expected), 'Only selected objects/dependents/incident cables removed'
            assert count_delta(audit_before, audit_counts(lab, db)) == {
                'inventory.device.delete': 1, 'inventory.devices.delete': 1}
            assert int(lab.sql(db, 'SELECT count(*) FROM operation')) == operation_before + 2
            assert expected['revision'] == revision_before + 2
            protected_before = [row for row in before['inventory_connection'] if row['id'] == ids['protectedCable']]
            protected_after = [row for row in after['inventory_connection'] if row['id'] == ids['protectedCable']]
            assert protected_before == protected_after and len(protected_after) == 1
            final_atomic = atomic_state(lab, db)
            denials = []
            for name, status in [('move-reader', 403), ('notice-outsider', 404)]:
                client = Client(server)
                assert client.login(name, password).status == 200
                for kind, payload in [('device.delete', {'id': ids['a']}),
                                      ('devices.delete', {'deviceIds': [ids['a'], ids['c']]})]:
                    headers = {'If-Match': f'"{expected["revision"]}"', 'Idempotency-Key': str(uuid.uuid4()),
                               'X-RackClick-Actor': client.request('GET', '/api/v1/me').json()['user']['id']}
                    body = {'type': kind, 'payload': payload}
                    for suffix in ['/preview', '']:
                        reply = client.request('POST', f"/api/v1/customers/{ids['customer']}/commands" + suffix,
                                               body, headers)
                        assert reply.status == status, (name, kind, suffix, reply.status)
                        assert atomic_state(lab, db) == final_atomic, 'Denied command/preview is atomic'
                    denials.append({'user': name, 'command': kind, 'previewAndCommit': status})
            server.close()
            restarted = lab.start_server(db, dll=dll, frontend=frontend)
            for name in ['move-admin', ids['secondName']]:
                client = Client(restarted)
                assert client.login(name, password).status == 200
                reply = client.request('GET', f"/api/v1/customers/{ids['customer']}/project")
                assert reply.status == 200 and reply.headers.get('etag') == f'"{expected["revision"]}"'
                assert project_by_id(reply.json()) == project_by_id(expected)
            assert atomic_state(lab, db) == final_atomic
            report.update(result='PASS', postgresql=lab.sql('postgres', 'SHOW server_version').strip(),
                          exactDeletionOnly=True, singleAndBatchCancellationAtomic=True,
                          protectedCableAndEndpointsPreserved=True, inventoryCommits=2,
                          permissionChecks=denials, serverRestartPersistence=True,
                          sqlRowCounts={key: len(rows) for key, rows in after.items()})
    except Exception as error:
        report.update(failureType=type(error).__name__, failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic() - started, 3),
                      labStopped=lab is None or not lab.running,
                      serversStopped=lab is None or all(s.process.poll() is not None for s in lab.servers),
                      finalInputs=inputs(dll, frontend))
        report['inputsUnchanged'] = report['inputs'] == report['finalInputs']
        if not report['inputsUnchanged']:
            report['result'] = 'FAIL_INPUTS_CHANGED'
        (output / 'fixture.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({key: value for key, value in report.items() if key not in ['inputs', 'finalInputs']}, indent=2))
    return 0 if report['result'] == 'PASS' and report['labStopped'] and report['serversStopped'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
