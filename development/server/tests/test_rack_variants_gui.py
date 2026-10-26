"""I-04.02 isolated Windows/PG/Edge rack edits and one genuine sw8p edit.

Requires explicit frozen .local artifacts/output; never builds or reuses QA.
Only synthetic initial inventory is SQL seeded; catalogue creation/edit use GUI.
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
sys.path.insert(0, str(ROOT/'development/server/tests'))
sys.path.insert(0, str(ROOT/'tools/windows'))
from pg_support import Lab, Client, toolchain
from windows_job import run_isolated
from test_inventory_movement_gui import fixture as seed, durable, tree, project_by_id


def canonical(value):
    return {key: sorted(json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows)
            for key, rows in value.items()}


def inputs(dll, frontend):
    sources = [Path(__file__), Path(__file__).with_name('test_inventory_movement_gui.py'),
               Path(__file__).with_name('pg_support.py'), ROOT/'tools/windows/windows_job.py',
               ROOT/'development/frontend/tests/browser-quince-support.mjs',
               ROOT/'development/frontend/tests/browser-rack-variants.mjs']
    return {'sources': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sources}, 'server': tree(dll.parent), 'frontend': tree(frontend)}


def fixture(lab, db, dll):
    ids, password = seed(lab, db, dll)
    ids.update({key: str(uuid.uuid4()) for key in
                ['siteA', 'siteB', 'buildingA', 'buildingB', 'roomA', 'roomB']})
    statements = [f"UPDATE customer SET name='Rack variants QA synthetic' WHERE id='{ids['customer']}';"]
    for suffix in ['A', 'B']:
        statements.extend([
            f"INSERT INTO inventory_site(id,systemhaus_id,customer_id,name,properties) SELECT '{ids['site'+suffix]}',systemhaus_id,id,'room','{{\"sentinel\":\"site-{suffix}\"}}' FROM customer WHERE id='{ids['customer']}';",
            f"INSERT INTO inventory_building(id,systemhaus_id,customer_id,site_id,name,properties) SELECT '{ids['building'+suffix]}',systemhaus_id,id,'{ids['site'+suffix]}','room','{{\"sentinel\":\"building-{suffix}\"}}' FROM customer WHERE id='{ids['customer']}';",
            f"INSERT INTO inventory_room(id,systemhaus_id,customer_id,building_id,name,properties) SELECT '{ids['room'+suffix]}',systemhaus_id,id,'{ids['building'+suffix]}','room','{{\"sentinel\":\"room-{suffix}\"}}' FROM customer WHERE id='{ids['customer']}';",
            f"UPDATE inventory_rack SET name='room',room_id='{ids['room'+suffix]}' WHERE id='{ids['rack'+suffix]}';",
        ])
    lab.sql(db, 'BEGIN;\n'+'\n'.join(statements)+'\nCOMMIT;', sensitive=True)
    assert len(set(ids.values())) == len(ids), 'All synthetic fixture UUIDs are unique'
    return ids, password


def new_sql_rows(project, device_id, house):
    """Complete SQL rows from the server snapshot; no guessed template identity."""
    customer = project['customerId']
    device = next(row for row in project['devices'] if row['id'] == device_id)
    groups = [row for row in project['portGroups'] if row['deviceId'] == device_id]
    ports = [row for row in project['ports'] if row['deviceId'] == device_id]
    base = {'systemhaus_id': house, 'customer_id': customer}
    device_row = dict(base, **{column: device[key] for column, key in {
        'id':'id', 'kind':'kind', 'rack_id':'rackId', 'room_id':'roomId', 'name':'name',
        'size_u':'sizeU', 'sort_order':'sortOrder', 'poe_budget':'poeBudget', 'properties':'properties'}.items()})
    group_rows = [dict(base, **{column: row[key] for column, key in {
        'id':'id', 'device_id':'deviceId', 'type':'type', 'name':'name', 'prefix':'prefix',
        'sort_order':'sortOrder'}.items()}) for row in groups]
    port_rows = [dict(base, connector_family='rj45' if row['type'] == 'rj45_poe' else row['type'],
        **{column: row[key] for column, key in {
            'id':'id', 'device_id':'deviceId', 'group_id':'groupId', 'type':'type', 'gn':'gn',
            'sort_order':'sortOrder', 'label':'label', 'status':'status', 'poe':'poe',
            'watts':'watts', 'color':'color', 'face':'face', 'power_role':'powerRole',
            'properties':'properties'}.items()}) for row in ports]
    return {'inventory_device':[device_row], 'inventory_port_group':group_rows, 'inventory_port':port_rows}


def checked_paths(args):
    private = (ROOT/'.local').resolve(strict=True)
    dll, frontend = args.dll.resolve(strict=True), args.frontend.resolve(strict=True)
    output = args.output.resolve()
    for label, value in [('dll', dll), ('frontend', frontend), ('output', output)]:
        if not value.is_relative_to(private) or value == private:
            raise RuntimeError(f'Explicit {label} must be inside this workspace .local directory')
    if not dll.is_file() or dll.name != 'RackClick.Server.dll' or not (frontend/'app.js').is_file():
        raise RuntimeError('Complete explicit server/frontend artifacts required')
    for artifact in [dll.parent, frontend]:
        if output.is_relative_to(artifact) or artifact.is_relative_to(output):
            raise RuntimeError('Output must be separate from immutable input artifacts')
    if output.exists():
        raise RuntimeError('Output must be a new directory, preserving earlier evidence')
    return dll, frontend, output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--frontend', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    dll, frontend, output = checked_paths(args)
    output.mkdir(parents=True, exist_ok=False)
    report = {'utc':datetime.now(timezone.utc).isoformat(), 'platform':platform.platform(),
              'inputs':inputs(dll, frontend), 'result':'FAIL', 'realQaAccessed':False,
              'productModified':False, 'fixtureCreatedBy':'SQL initial inventory; genuine sw8p creation and edits through Edge GUI',
              'limits':['One sw8p preset; no33-preset matrix, Dosen, drag/touch, Windows reboot, actual QA or adoption.']}
    started = time.monotonic()
    lab = None
    try:
        lab = Lab('rack-variants-i0402')
        with lab:
            db = lab.create_database('rackvariants')
            ids, password = fixture(lab, db, dll)
            lab.grant_runtime(db)
            before = durable(lab, db)
            server = lab.start_server(db, dll=dll, frontend=frontend)
            env = lab.environment()
            env.update(RACKCLICK_TEST_ORIGIN=server.origin, RACKCLICK_TEST_USERNAME='move-admin',
                       RACKCLICK_TEST_PASSWORD=password, RACKCLICK_TEST_OUTPUT=str(output),
                       RACKCLICK_FIXTURE=json.dumps(ids))
            browser_started = time.monotonic()
            with (output/'browser-windows.log').open('wb') as log:
                done = run_isolated([str(toolchain()['node']), str(ROOT/'development/frontend/tests/browser-rack-variants.mjs')],
                                    env=env, cwd=ROOT/'development/frontend', stdout=log, stderr=log, timeout=240)
            report.update(browserExitCode=done.returncode, browserSeconds=round(time.monotonic()-browser_started, 3))
            if done.returncode:
                raise RuntimeError('Browser failed; sanitized evidence retained under explicit .local output')
            expected = json.loads((output/'expected-project.json').read_text(encoding='utf-8'))
            created = json.loads((output/'created-project.json').read_text(encoding='utf-8'))
            details = json.loads((output/'rack-variants-details.json').read_text(encoding='utf-8'))
            catalogue = json.loads((output/'catalogue-reference.json').read_text(encoding='utf-8'))
            after = durable(lab, db)
            device_id = details['createdDeviceId']
            house = before['inventory_rack'][0]['systemhaus_id']
            wanted = json.loads(json.dumps(before))
            for row in wanted['inventory_rack']:
                if row['id'] == ids['rackA']:
                    row.update(room_id=ids['roomB'], size_u=2, location=details['location'])
            additions = new_sql_rows(expected, device_id, house)
            for table, rows in additions.items():
                wanted[table].extend(rows)
            assert canonical(after) == canonical(wanted), 'Exact SQL rows: only intended rack edit and genuine preset additions'
            assert len(after['inventory_device']) == 4
            assert len(after['inventory_port_group']) == 5
            assert len(after['inventory_port']) == 16
            assert after['inventory_connection'] == before['inventory_connection']
            assert after['inventory_connection_endpoint'] == before['inventory_connection_endpoint']
            created_device = next(row for row in created['devices'] if row['id'] == device_id)
            final_device = next(row for row in expected['devices'] if row['id'] == device_id)
            immutable_properties = {key:value for key,value in created_device['properties'].items() if key != 'notes'}
            assert immutable_properties == {key:value for key,value in final_device['properties'].items() if key != 'notes'}
            assert immutable_properties == {
                'preset':catalogue['preset']['label'], 'icon':catalogue['preset']['icon'], 'color':catalogue['preset']['color'],
                'catalog':{'presetKey':'sw8p', 'version':catalogue['catalogVersion'],
                           'sha256':catalogue['catalogSha256'], 'language':'es'}}
            assert len(catalogue['catalogSha256']) == 64 and int(catalogue['catalogSha256'], 16) >= 0
            assert created_device['properties']['notes'] == details['initialNotes']
            assert final_device['properties']['notes'] == details['editedNotes']
            assert created_device['kind'] == final_device['kind'] == 'rackEquipment'
            assert created_device['rackId'] == final_device['rackId'] == ids['rackB']
            assert final_device['name'] == details['editedName'] and final_device['sizeU'] == 2 and final_device['poeBudget'] == 0
            for key in ['portGroups', 'ports', 'connections']:
                assert project_by_id(created)[key] == project_by_id(expected)[key], f'Exact {key} after preset edit'
            actions = {action:int(lab.sql(db, f"SELECT count(*) FROM audit_event WHERE action='inventory.{action}'"))
                       for action in ['rack.update', 'device.createFromCatalog', 'device.update', 'device.move']}
            assert actions == {'rack.update':1, 'device.createFromCatalog':1, 'device.update':1, 'device.move':0}
            report.update(sqlExactOriginalRowsAndIntendedChanges=True, sqlExactPresetRows=True,
                          presetCatalogAndNonNotePropertiesPreserved=True, groupsPortsCablesExactAfterEdit=True,
                          sqlTableRowCounts={key:len(rows) for key, rows in after.items()}, auditCommits=actions,
                          sqlBeforeSha256=hashlib.sha256(json.dumps(canonical(before),sort_keys=True).encode()).hexdigest(),
                          sqlAfterSha256=hashlib.sha256(json.dumps(canonical(after),sort_keys=True).encode()).hexdigest())
            server.close()
            restarted = lab.start_server(db, dll=dll, frontend=frontend)
            for name in ['move-admin', 'move-second']:
                client = Client(restarted)
                assert client.login(name, password).status == 200, 'Synthetic login after restart succeeds'
                actual = client.request('GET', f"/api/v1/customers/{ids['customer']}/project")
                assert actual.status == 200, 'Restarted project read succeeds'
                assert actual.headers.get('etag') == f'"{expected["revision"]}"', 'Restarted revision ETag'
                assert project_by_id(actual.json()) == project_by_id(expected), 'Restarted exact full snapshot for both actors'
            assert canonical(durable(lab, db)) == canonical(after), 'Restart preserves exact durable rows'
            report.update(serverRestartPersistence=True, postgresql=lab.sql('postgres', 'SHOW server_version'), result='PASS')
    except Exception as error:
        report.update(failureType=type(error).__name__, failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started, 3), labStopped=lab is None or not lab.running,
                      serversStopped=lab is None or all(s.process.poll() is not None for s in lab.servers),
                      finalInputs=inputs(dll, frontend))
        report['inputsUnchanged'] = report['inputs'] == report['finalInputs']
        if not report['inputsUnchanged']:
            report['result'] = 'FAIL_INPUTS_CHANGED'
        (output/'fixture.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({key:value for key,value in report.items() if key not in ['inputs','finalInputs']}, indent=2))
    return 0 if report['result'] == 'PASS' and report['labStopped'] and report['serversStopped'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
