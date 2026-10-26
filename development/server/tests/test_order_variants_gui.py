"""I-04.04: real Windows Edge/PG ordering, drag and emulated touch.

Requires explicit immutable local artifacts. Never builds, accesses QA or a VM.
Initial inventory is SQL seeded; successful commands under test come from GUI.
"""
import argparse
import hashlib
import json
import platform
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
sys.path.insert(0, str(ROOT / 'tools/windows'))
from pg_support import Lab, Client, toolchain
from windows_job import run_isolated
from test_inventory_movement_gui import fixture, durable, tree, project_by_id
from test_rack_variants_gui import checked_paths, canonical
from test_inventory_duplicate_gui import atomic_state


def inputs(dll, frontend):
    sources = [Path(__file__),
        ROOT / 'development/frontend/tests/browser-order-variants.mjs',
        ROOT / 'development/frontend/tests/browser-quince-support.mjs',
        Path(__file__).with_name('test_inventory_movement_gui.py'),
        Path(__file__).with_name('test_rack_variants_gui.py'),
        Path(__file__).with_name('test_inventory_duplicate_gui.py'),
        Path(__file__).with_name('pg_support.py'), ROOT / 'tools/windows/windows_job.py']
    return {'sources': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sources}, 'server': tree(dll.parent), 'frontend': tree(frontend)}


def assert_order_sql(before, after, ids):
    """Only b changes rack; a/c keep their intended new order; all attributes/endpoints are exact."""
    wanted = json.loads(json.dumps(before))
    for row in wanted['inventory_device']:
        if row['id'] == ids['a']:
            row['sort_order'] = 1
        elif row['id'] == ids['b']:
            row.update(rack_id=ids['rackB'], sort_order=0)
        elif row['id'] == ids['c']:
            row['sort_order'] = 1
    assert canonical(after) == canonical(wanted), 'Exact nine SQL tables, including metadata/UUIDs/cables'
    assert after['inventory_connection'] == before['inventory_connection']
    assert after['inventory_connection_endpoint'] == before['inventory_connection_endpoint']
    assert sorted(row['id'] for row in after['inventory_device']) == sorted(
        row['id'] for row in before['inventory_device'])
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--frontend', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    dll, frontend, output = checked_paths(args)
    output.mkdir(parents=True, exist_ok=False)
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
              'inputs': inputs(dll, frontend), 'result': 'FAIL', 'realQaAccessed': False,
              'fixtureCreatedBy': 'SQL initial inventory/accounts; order/move writes through Edge GUI',
              'limits': ['Touch emulated in Edge/CDP, not physical touchscreen hardware.',
                         'Documentary sortOrder, not a persisted physical U position.',
                         'No Windows reboot, actual QA/VM or complete inventory parity.']}
    lab = None
    started = time.monotonic()
    try:
        lab = Lab('order-variants-i0404')
        with lab:
            db = lab.create_database('ordervariants')
            ids, password = fixture(lab, db, dll)
            lab.grant_runtime(db)
            before = durable(lab, db)
            server = lab.start_server(db, dll=dll, frontend=frontend)
            env = lab.environment()
            env.update(RACKCLICK_TEST_ORIGIN=server.origin, RACKCLICK_TEST_USERNAME='move-admin',
                       RACKCLICK_TEST_PASSWORD=password, RACKCLICK_TEST_OUTPUT=str(output),
                       RACKCLICK_FIXTURE=json.dumps(ids))
            browser_started = time.monotonic()
            with (output / 'browser-windows.log').open('wb') as log:
                done = run_isolated([str(toolchain()['node']),
                    str(ROOT / 'development/frontend/tests/browser-order-variants.mjs')],
                    env=env, cwd=ROOT / 'development/frontend', stdout=log, stderr=log, timeout=240)
            report.update(browserExitCode=done.returncode,
                          browserSeconds=round(time.monotonic() - browser_started, 3))
            if done.returncode:
                raise RuntimeError('Browser failed; keep original sanitized failure and isolated output')
            expected = json.loads((output / 'expected-project.json').read_text(encoding='utf-8'))
            initial = json.loads((output / 'initial-project.json').read_text(encoding='utf-8'))
            details = json.loads((output / 'order-variants-details.json').read_text(encoding='utf-8'))
            after = durable(lab, db)
            report['exactSqlPlacementAndOrderOnly'] = assert_order_sql(before, after, ids)
            assert expected['revision'] == initial['revision'] + 5, 'Exactly five confirmed GUI commits'
            writes = details['writes']
            assert [w['type'] for w in writes] == [
                'device.reorder', 'device.reorder', 'device.reorder', 'device.move', 'device.reorder']
            assert [w['payload'] for w in writes] == [
                {'rackId': ids['rackA'], 'deviceIds': [ids['b'], ids['a']]},
                {'rackId': ids['rackA'], 'deviceIds': [ids['a'], ids['b']]},
                {'rackId': ids['rackA'], 'deviceIds': [ids['b'], ids['a']]},
                {'id': ids['b'], 'rackId': ids['rackB']},
                {'rackId': ids['rackB'], 'deviceIds': [ids['b'], ids['c']]}], 'Only UUID-based offered commands'
            audit = {kind: int(lab.sql(db,
                f"SELECT count(*) FROM audit_event WHERE action='inventory.{kind}'"))
                for kind in ['device.reorder', 'device.move']}
            assert audit == {'device.reorder': 4, 'device.move': 1}
            assert lab.sql(db, 'SELECT count(*) FROM operation') == '5'
            assert lab.sql(db, "SELECT count(*) FROM audit_event WHERE action LIKE 'inventory.%'") == '5'
            final_atomic = atomic_state(lab, db)
            permission = []
            for name, key in [('move-reader', 'reader'), ('move-technician', 'technician')]:
                client = Client(server)
                assert client.login(name, password).status == 200
                assert client.request('GET', f"/api/v1/customers/{ids['customer']}/project").status == 200
                response = client.request('POST', f"/api/v1/customers/{ids['customer']}/commands",
                    {'type': 'device.reorder', 'payload': {'rackId': ids['rackB'],
                                                         'deviceIds': [ids['c'], ids['b']]}},
                    {'If-Match': f'"{expected["revision"]}"',
                     'Idempotency-Key': str(uuid.uuid4()),
                     'X-RackClick-Actor': ids[key]})
                assert response.status == 403, 'Server denies reordering without this customer edit scope'
                assert client.request('GET', f"/api/v1/customers/{ids['other']}/project").status == 404
                assert atomic_state(lab, db) == final_atomic, 'Denied command changes no inventory/revision/operation/audit'
                permission.append({'user': name, 'write': 403, 'outsideRead': 404, 'atomicStateUnchanged': True})
            report.update(sqlTableRowCounts={key: len(rows) for key, rows in after.items()},
                          operationRows=5, auditCommits=audit, permissionChecks=permission,
                          sqlBeforeSha256=hashlib.sha256(json.dumps(canonical(before), sort_keys=True).encode()).hexdigest(),
                          sqlAfterSha256=hashlib.sha256(json.dumps(canonical(after), sort_keys=True).encode()).hexdigest())
            server.close()
            restarted = lab.start_server(db, dll=dll, frontend=frontend)
            for name in ['move-admin', 'move-second']:
                client = Client(restarted)
                assert client.login(name, password).status == 200
                response = client.request('GET', f"/api/v1/customers/{ids['customer']}/project")
                assert response.status == 200 and response.headers.get('etag') == f'"{expected["revision"]}"'
                assert project_by_id(response.json()) == project_by_id(expected), 'Exact snapshot after restart, both actors'
            assert canonical(durable(lab, db)) == canonical(after)
            assert atomic_state(lab, db) == final_atomic, 'Read/restart adds no inventory revision/operation/audit'
            report.update(serverRestartPersistence=True, atomicReadRestartUnchanged=True,
                          postgresql=lab.sql('postgres', 'SHOW server_version'), result='PASS')
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
