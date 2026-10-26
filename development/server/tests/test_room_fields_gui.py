"""Remaining room-object editor fields; synthetic Windows/PG/Edge laboratory.

Frozen inputs only. Power roles are documentation attributes on unconnected
logical ports, not a physical circuit or an installation into a real server.
"""
import argparse
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
from pg_support import Lab, Client, literal, toolchain
from windows_job import run_isolated
from test_room_device_move_gui import fixture as seed
from test_inventory_movement_gui import durable, project_by_id, tree
from test_inventory_duplicate_gui import atomic_state
from test_rack_variants_gui import checked_paths, canonical


def inputs(dll, frontend):
    names = ['pg_support.py', 'test_room_device_move_gui.py', 'test_client_changes_gui.py',
             'test_inventory_movement_gui.py', 'test_inventory_duplicate_gui.py', 'test_rack_variants_gui.py']
    sources = [Path(__file__), ROOT / 'development/frontend/tests/browser-room-fields.mjs',
               ROOT / 'development/frontend/tests/browser-quince-support.mjs',
               ROOT / 'tools/windows/windows_job.py'] + [Path(__file__).with_name(n) for n in names]
    return {'sources': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sources}, 'server': tree(dll.parent), 'frontend': tree(frontend)}


def fixture(lab, db, dll):
    ids, password = seed(lab, db, dll)
    ids.update({key: str(uuid.uuid4()) for key in ['gpowerDose', 'gpowerEnd', 'ppowerDose', 'ppowerEnd',
               'ppow2Dose', 'ppow2End', 'gpowerOther', 'ppowerOther']})
    ids['fieldSpec'] = {
        'dose': {'name': 'Dose campos literal <img data-room-field-injection=1> Ω', 'poeBudget': 120,
                 'notes': {'sn': 'serial-dose-Ω', 'model': 'modelo dose <img> 東京', 'ip': '192.0.2.21',
                           'firmware': 'fw-dose-1.2', 'text': 'notas Dose completas Ω'},
                 'networkChanges': {'status': 'faulty', 'poe': False, 'watts': 12.5, 'color': '#335577',
                                    'label': 'Toma literal <img data-room-field-injection=1> Ω', 'face': 'front'},
                 'powerRole': 'outlet'},
        'end': {'name': 'Final campos literal <img data-room-field-injection=1> 東京', 'poeBudget': 90,
                'notes': {'sn': 'serial-end-東京', 'model': 'modelo final Ω', 'ip': '192.0.2.22',
                          'firmware': 'fw-end-2.3', 'text': 'notas Final completas <img> 東京'},
                'networkChanges': {'status': 'disabled', 'poe': True, 'watts': None, 'color': None,
                                   'label': '', 'face': 'auto'}, 'powerRole': 'inlet'}}
    sql = [f"UPDATE inventory_port SET type='rj45',poe=false WHERE device_id IN ('{ids['dose']}','{ids['end']}');",
           f"UPDATE inventory_port SET type='rj45_poe',poe=true WHERE id='{ids['pdose']}';"]
    for key, suffix in [('dose', 'Dose'), ('end', 'End')]:
        properties = json.loads(lab.sql(db, f"SELECT properties FROM inventory_device WHERE id='{ids[key]}'"))
        properties.update(fixtureSentinel={'key': key, 'nested': [True, 7, 'retain']}, color='#112233')
        properties['notes'].update(model='before-model-' + key, ip='192.0.2.17', firmware='before-fw-' + key)
        sql.append(f"UPDATE inventory_device SET properties={literal(json.dumps(properties))}::jsonb WHERE id='{ids[key]}';")
        sql.append(f"INSERT INTO inventory_port_group VALUES('{ids['gpower'+suffix]}','{ids['house']}',"
                   f"'{ids['customer']}','{ids[key]}','power','Grupo energía {suffix}','P',1);")
        for n, port in [(1, ids['ppower'+suffix]), (2, ids['ppow2'+suffix])]:
            sql.append(f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,"
                       f"label,status,poe,watts,color,face,power_role,properties) VALUES('{port}','{ids['house']}',"
                       f"'{ids['customer']}','{ids[key]}','{ids['gpower'+suffix]}','power',{n},{n-1},'Power {suffix}{n}',"
                       f"'free',false,NULL,'#445566','front','unspecified','{{\"fixture\":\"power-{suffix}-{n}\"}}');")
    sql.extend([
        f"INSERT INTO inventory_port_group VALUES('{ids['gpowerOther']}','{ids['house']}','{ids['other']}',"
        f"'{ids['onlyRoomDevice']}','power','Otro cliente','X',0);",
        f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label) "
        f"VALUES('{ids['ppowerOther']}','{ids['house']}','{ids['other']}','{ids['onlyRoomDevice']}',"
        f"'{ids['gpowerOther']}','power',1,0,'Ajeno');"])
    lab.sql(db, 'BEGIN;\n' + '\n'.join(sql) + '\nCOMMIT;', sensitive=True)
    return ids, password


def expected_sql(before, ids):
    wanted = json.loads(json.dumps(before))
    for key in ['dose', 'end']:
        spec = ids['fieldSpec'][key]
        device = next(row for row in wanted['inventory_device'] if row['id'] == ids[key])
        device.update(name=spec['name'], poe_budget=spec['poeBudget'])
        device['properties']['notes'].update(spec['notes'])
        port = next(row for row in wanted['inventory_port'] if row['id'] == ids['p'+key])
        port.update(spec['networkChanges'])
        port['type'] = 'rj45_poe' if spec['networkChanges']['poe'] else 'rj45'
        suffix = 'Dose' if key == 'dose' else 'End'
        power = next(row for row in wanted['inventory_port'] if row['id'] == ids['ppower'+suffix])
        power['power_role'] = spec['powerRole']
    return wanted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--frontend', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    dll, frontend, output = checked_paths(parser.parse_args())
    output.mkdir(parents=True, exist_ok=False)
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'inputs': inputs(dll, frontend),
              'result': 'FAIL', 'realQaAccessed': False,
              'fixtureCreatedBy': 'SQL synthetic room inventory; all field changes through Edge GUI',
              'limits': ['Spanish, one selected RJ45 and one selected power port per room object.',
                         'Power ports unconnected: no physical circuit or voltage/power safety claim.',
                         'No VM, Windows reboot, installer or actual QA.']}
    lab = None
    started = time.monotonic()
    try:
        lab = Lab('room-fields-i0602')
        with lab:
            db = lab.create_database('roomfields')
            ids, password = fixture(lab, db, dll)
            lab.grant_runtime(db)
            before = durable(lab, db)
            server = lab.start_server(db, dll=dll, frontend=frontend)
            env = lab.environment()
            env.update(RACKCLICK_TEST_ORIGIN=server.origin, RACKCLICK_TEST_USERNAME='move-admin',
                       RACKCLICK_TEST_PASSWORD=password, RACKCLICK_TEST_OUTPUT=str(output),
                       RACKCLICK_FIXTURE=json.dumps(ids))
            with (output / 'browser.log').open('wb') as log:
                done = run_isolated([str(toolchain()['node']), str(ROOT / 'development/frontend/tests/browser-room-fields.mjs')],
                    env=env, cwd=ROOT / 'development/frontend', stdout=log, stderr=log, timeout=240)
            report['browserExitCode'] = done.returncode
            if done.returncode:
                raise RuntimeError('Room-field browser failed; preserve sanitized isolated output')
            expected = json.loads((output / 'expected-project.json').read_text(encoding='utf-8'))
            details = json.loads((output / 'room-fields-details.json').read_text(encoding='utf-8'))
            after = durable(lab, db)
            assert canonical(after) == canonical(expected_sql(before, ids)), 'Exact intended edits and complete remaining SQL'
            writes = details['writes']
            assert len(writes) == 16
            assert [row['type'] for row in writes] == ['device.update'] * 2 + ['ports.update'] * 14
            initial = json.loads((output / 'initial-project.json').read_text(encoding='utf-8'))
            assert expected['revision'] == initial['revision'] + 16
            assert lab.sql(db, 'SELECT count(*) FROM operation').strip() == '16'
            audit = {kind: int(lab.sql(db, f"SELECT count(*) FROM audit_event WHERE action='inventory.{kind}'"))
                     for kind in ['device.update', 'ports.update']}
            assert audit == {'device.update': 2, 'ports.update': 14}
            final_atomic = atomic_state(lab, db)
            admin = Client(server)
            assert admin.login('move-admin', password).status == 200

            def change(client, group, group_type, ports, changes):
                actor = client.request('GET', '/api/v1/me').json()['user']['id']
                return client.request('POST', f"/api/v1/customers/{ids['customer']}/commands",
                    {'type': 'ports.update', 'payload': {'deviceId': ids['dose'], 'groupId': group,
                        'groupType': group_type, 'portIds': ports, 'changes': changes}},
                    {'If-Match': f'"{expected["revision"]}"', 'Idempotency-Key': str(uuid.uuid4()),
                     'X-RackClick-Actor': actor})

            negatives = []
            cases = [
                ('role_on_rj45', ids['gdose'], 'rj45', [ids['pdose']], {'powerRole': 'outlet'}, 422),
                ('poe_on_power', ids['gpowerDose'], 'power', [ids['ppowerDose']], {'poe': True}, 422),
                ('mixed_groups_rollback', ids['gdose'], 'rj45', [ids['pdose'], ids['ppowerDose']], {'status': 'free'}, 422),
                ('watts_over_limit', ids['gdose'], 'rj45', [ids['pdose']], {'watts': 91}, 422),
                ('foreign_port', ids['gpowerDose'], 'power', [ids['ppowerOther']], {'powerRole': 'outlet'}, 404)]
            for name, group, family, ports, changes, status in cases:
                reply = change(admin, group, family, ports, changes)
                assert reply.status == status, (name, reply.status)
                assert atomic_state(lab, db) == final_atomic, 'Invalid field/scope leaves no partial update or operation/audit'
                negatives.append({'case': name, 'status': status, 'atomicStateUnchanged': True})
            for user, status in [('move-reader', 403), ('notice-outsider', 404)]:
                client = Client(server)
                assert client.login(user, password).status == 200
                reply = change(client, ids['gpowerDose'], 'power', [ids['ppowerDose']], {'powerRole': 'inlet'})
                assert reply.status == status
                assert atomic_state(lab, db) == final_atomic
                negatives.append({'case': user, 'status': status, 'atomicStateUnchanged': True})
            server.close()
            restarted = lab.start_server(db, dll=dll, frontend=frontend)
            for user in ['move-admin', ids['secondName']]:
                client = Client(restarted)
                assert client.login(user, password).status == 200
                reply = client.request('GET', f"/api/v1/customers/{ids['customer']}/project")
                assert reply.status == 200 and reply.headers.get('etag') == f'"{expected["revision"]}"'
                assert project_by_id(reply.json()) == project_by_id(expected)
            assert atomic_state(lab, db) == final_atomic
            report.update(result='PASS', postgresql=lab.sql('postgres', 'SHOW server_version').strip(),
                          allOfferedRoomFieldsVerified=True, repeatedGnSeparatedByGroupAndType=True,
                          sqlOnlyIntendedChanges=True, inventoryOperations=16, auditCommits=audit,
                          negativeChecks=negatives, serverRestartPersistence=True,
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
