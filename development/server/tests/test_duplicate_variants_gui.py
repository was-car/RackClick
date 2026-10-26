"""I-04.03 native PG/Edge copies without cables and with confirmed reservation.

Only new private .local artifacts/output; SQL seeds are preparation, not GUI creation.
No product build, host services, real QA, or modification of historical test files.
"""
import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'development/server/tests'))
sys.path.insert(0, str(ROOT/'tools/windows'))
from pg_support import Lab, Client, protect_directory, toolchain
from windows_job import run_isolated
from test_inventory_duplicate_gui import fixture as seed, canonical, atomic_state
from test_inventory_movement_gui import durable, tree, project_by_id


def inputs(dll, frontend):
    sources = [Path(__file__), Path(__file__).with_name('test_inventory_duplicate_gui.py'),
               Path(__file__).with_name('test_inventory_movement_gui.py'),
               Path(__file__).with_name('pg_support.py'), ROOT/'tools/windows/windows_job.py',
               ROOT/'development/frontend/tests/browser-quince-support.mjs',
               ROOT/'development/frontend/tests/browser-duplicate-variants.mjs']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            'server':tree(dll.parent), 'frontend':tree(frontend)}


def fixture(lab, db, dll):
    ids, password = seed(lab, db, dll)
    # Initial preparation only. Source stays unchanged for the entire browser run.
    lab.sql(db, f"UPDATE inventory_port SET status='reserved' WHERE id='{ids['pa']}'", sensitive=True)
    return ids, password


def assert_sql_variants(before, after, ids, mappings):
    """All nine tables exact, adding two complete remaps from the original source."""
    assert len(mappings) == 2 and [row['includeConnections'] for row in mappings] == [False, True]
    expected = json.loads(json.dumps(before))
    all_old = {row['id'] for rows in before.values() for row in rows if 'id' in row}
    all_new = []
    additions = {table:0 for table in before}
    source_rack = next(row for row in before['inventory_rack'] if row['id'] == ids['rackA'])
    source_devices = [row for row in before['inventory_device'] if row['rack_id'] == ids['rackA']]
    source_device_ids = {row['id'] for row in source_devices}
    source_groups = [row for row in before['inventory_port_group'] if row['device_id'] in source_device_ids]
    source_ports = [row for row in before['inventory_port'] if row['device_id'] in source_device_ids]
    source_port_ids = {row['id'] for row in source_ports}
    assert len(source_devices) == 2 and len(source_groups) == 3 and len(source_ports) == 5
    assert len([row for row in source_ports if row['device_id'] == ids['a'] and row['gn'] == 1]) == 2
    assert {row['id'] for row in source_ports if row['status'] == 'reserved'} == {ids['pa'], ids['extraPort']}
    for mapping in mappings:
        assert set(mapping['devices']) == source_device_ids
        assert set(mapping['groups']) == {row['id'] for row in source_groups}
        assert set(mapping['ports']) == source_port_ids
        assert mapping['ports'][ids['pa']] != mapping['ports'][ids['extraPort']]
        expected['inventory_rack'].append(dict(source_rack, id=mapping['rackId'], name=mapping['name']))
        for row in source_devices:
            expected['inventory_device'].append(dict(row, id=mapping['devices'][row['id']], rack_id=mapping['rackId']))
        for row in source_groups:
            expected['inventory_port_group'].append(dict(row, id=mapping['groups'][row['id']], device_id=mapping['devices'][row['device_id']]))
        for row in source_ports:
            expected['inventory_port'].append(dict(row, id=mapping['ports'][row['id']],
                device_id=mapping['devices'][row['device_id']], group_id=mapping['groups'][row['group_id']]))
        all_new.extend([mapping['rackId'], *mapping['devices'].values(), *mapping['groups'].values(), *mapping['ports'].values()])
        for table, count in [('inventory_rack',1), ('inventory_device',2), ('inventory_port_group',3), ('inventory_port',5)]:
            additions[table] += count
        if mapping['includeConnections']:
            assert mapping['connectionId'] is not None
            source = next(row for row in before['inventory_connection'] if row['id'] == ids['cable'])
            copied = next(row for row in after['inventory_connection'] if row['id'] == mapping['connectionId'])
            assert datetime.fromisoformat(copied['created_at']) > datetime.fromisoformat(source['created_at']), 'Only copied cable gets a new creation time'
            expected['inventory_connection'].append(dict(source, id=mapping['connectionId'], created_at=copied['created_at']))
            endpoints = [row for row in before['inventory_connection_endpoint'] if row['connection_id'] == ids['cable']]
            assert len(endpoints) == 2 and all(row['port_id'] in source_port_ids for row in endpoints)
            for row in endpoints:
                expected['inventory_connection_endpoint'].append(dict(row, connection_id=mapping['connectionId'], port_id=mapping['ports'][row['port_id']]))
            all_new.append(mapping['connectionId'])
            additions['inventory_connection'] += 1
            additions['inventory_connection_endpoint'] += 2
        else:
            assert mapping['connectionId'] is None
        copied_port_ids = set(mapping['ports'].values())
        connected = {row['port_id'] for row in after['inventory_connection_endpoint'] if row['port_id'] in copied_port_ids}
        wanted_connected = {mapping['ports'][ids['pa']], mapping['ports'][ids['pb']]} if mapping['includeConnections'] else set()
        assert connected == wanted_connected, 'Only new internal endpoints connected; external and loose reserved copies stay unconnected'
    assert len(all_new) == len(set(all_new)) and not set(all_new).intersection(all_old), 'Both complete UUID sets disjoint from originals and each other'
    for table, count in additions.items():
        assert len(after[table]) == len(before[table]) + count, 'Exact added rows in '+table
    assert canonical(after) == canonical(expected), 'Every original/copied SQL attribute, role, connector_family, property and endpoint exact'
    return additions


def checked_paths(args):
    private = (ROOT/'.local').resolve(strict=True)
    dll, frontend, output = args.dll.resolve(strict=True), args.frontend.resolve(strict=True), args.output.resolve()
    for label, value in [('dll',dll), ('frontend',frontend), ('output',output)]:
        if not value.is_relative_to(private) or value == private:
            raise RuntimeError(f'Explicit {label} must stay inside this workspace .local directory')
    if not dll.is_file() or dll.name != 'RackClick.Server.dll' or not (frontend/'app.js').is_file():
        raise RuntimeError('Complete explicit immutable server/frontend artifacts required')
    for artifact in [dll.parent, frontend]:
        if output.is_relative_to(artifact) or artifact.is_relative_to(output):
            raise RuntimeError('Output must be separate from immutable artifacts')
    if output.exists():
        raise RuntimeError('A new output directory is required; existing evidence remains intact')
    return dll, frontend, output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dll',type=Path,required=True)
    parser.add_argument('--frontend',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    dll, frontend, output = checked_paths(parser.parse_args())
    output.mkdir(parents=True,exist_ok=False)
    protect_directory(output)
    report = {'utc':datetime.now(timezone.utc).isoformat(), 'platform':platform.platform(),
              'inputs':inputs(dll,frontend), 'result':'FAIL', 'realQaAccessed':False, 'productModified':False,
              'fixtureCreatedBy':'SQL initial inventory with connected pa and loose extraPort reserved; two duplicates are GUI writes',
              'limits':['Two rack duplicate variants; historical API atomic/permission negatives run separately. No Dosen, drag/touch, Windows reboot, actual QA or adoption.']}
    started = time.monotonic()
    lab = None
    try:
        lab = Lab('duplicate-variants-i0403')
        with lab:
            db = lab.create_database('duplicatevariants')
            ids, password = fixture(lab,db,dll)
            lab.grant_runtime(db)
            before = durable(lab,db)
            server = lab.start_server(db,dll=dll,frontend=frontend)
            env = lab.environment()
            env.update(RACKCLICK_TEST_ORIGIN=server.origin, RACKCLICK_TEST_USERNAME='move-admin',
                       RACKCLICK_TEST_PASSWORD=password, RACKCLICK_TEST_OUTPUT=str(output), RACKCLICK_FIXTURE=json.dumps(ids))
            browser_started = time.monotonic()
            with (output/'browser-windows.log').open('wb') as log:
                done = run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-duplicate-variants.mjs')],
                                    env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=240)
            report.update(browserExitCode=done.returncode,browserSeconds=round(time.monotonic()-browser_started,3))
            if done.returncode:
                raise RuntimeError('Browser failed; sanitized evidence retained in explicit private output')
            mappings = json.loads((output/'duplicate-variant-maps.json').read_text(encoding='utf-8'))
            expected = json.loads((output/'expected-project.json').read_text(encoding='utf-8'))
            initial = json.loads((output/'initial-project.json').read_text(encoding='utf-8'))
            details = json.loads((output/'duplicate-variants-details.json').read_text(encoding='utf-8'))
            after = durable(lab,db)
            report['exactSqlAdditions'] = assert_sql_variants(before,after,ids,mappings)
            assert expected['revision'] == initial['revision'] + 2, 'Only two committed revisions'
            assert [row['name'] for row in mappings] == ['Copia sin cables Ω <img>','Copia con reserva 東京 <img>']
            assert [row['type'] for row in details['writes']] == ['rack.duplicate','rack.duplicate']
            for index, mapping in enumerate(mappings):
                assert details['writes'][index]['payload'] == {'id':ids['rackA'], 'name':mapping['name'],
                    'includeConnections':mapping['includeConnections'], 'confirmedReservedPortIds':[ids['pa']] if index else []}
            assert details['blockedSubmit'] == {'httpCommands':0,'snapshotAndRevisionUnchanged':True,'auditUnchanged':True}
            assert lab.sql(db,"SELECT count(*) FROM operation") == '2', 'Exactly two operation rows'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='inventory.rack.duplicate'") == '2', 'Exactly two duplicate audit commits'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action LIKE 'inventory.%'") == '2', 'No unexpected inventory audit commits'
            final_atomic = atomic_state(lab,db)
            report.update(sqlSourceExternalAndBothRemapsExact=True, allUuidSetsDisjoint=True,
                          requiredCheckboxBlocksWithoutHttpOrAudit=True, confirmedReservedOldPortIdsOnly=True,
                          operationRows=2, duplicateAuditCommits=2, sqlTableRowCounts={key:len(rows) for key,rows in after.items()},
                          sqlBeforeSha256=hashlib.sha256(json.dumps(canonical(before),sort_keys=True).encode()).hexdigest(),
                          sqlAfterSha256=hashlib.sha256(json.dumps(canonical(after),sort_keys=True).encode()).hexdigest())
            server.close()
            restarted = lab.start_server(db,dll=dll,frontend=frontend)
            for name in ['move-admin','move-second']:
                client = Client(restarted)
                assert client.login(name,password).status == 200, 'Synthetic login after restart succeeds'
                actual = client.request('GET',f"/api/v1/customers/{ids['customer']}/project")
                assert actual.status == 200 and actual.headers.get('etag') == f'"{expected["revision"]}"'
                assert project_by_id(actual.json()) == project_by_id(expected), 'Server restart preserves exact two-copy project for both actors'
            assert canonical(durable(lab,db)) == canonical(after), 'Server restart preserves all nine inventory tables'
            assert atomic_state(lab,db) == final_atomic, 'Restart/readback add no customer, operation or audit mutation'
            report.update(serverRestartPersistence=True,atomicReadRestartUnchanged=True,
                          postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:
        report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=lab is None or not lab.running,
                      serversStopped=lab is None or all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,frontend))
        report['inputsUnchanged'] = report['inputs'] == report['finalInputs']
        if not report['inputsUnchanged']:
            report['result'] = 'FAIL_INPUTS_CHANGED'
        (output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({key:value for key,value in report.items() if key not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result'] == 'PASS' and report['labStopped'] and report['serversStopped'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
