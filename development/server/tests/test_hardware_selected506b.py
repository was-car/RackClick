"""Real PostgreSQL 17 trial for fifty profiles from the fixed 506 selection.

Uses a new cluster and newly generated secrets. No installed database is opened.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import time
import traceback
import uuid

from pg_support import Lab, Client, NO_WINDOW, literal, protect_directory, toolchain
from test_hardware_mounting_gui import fixture
from test_hardware_catalog17 import state, migrate, runtime_sql, CATALOG
from test_hardware_batch100c import (BatchSession, ordered, create, create_racks,
                                    catalog_rows, verify_catalog, verify_device, first_port, payload)

ROOT = Path(__file__).resolve().parents[3]
REVISION = 'selected506b-20261101-v1'


def authoring():
    models, pins = [], {}
    for source in sorted((ROOT/'development/hardware/selected506b').glob('*.json')):
        data = json.loads(source.read_text(encoding='utf-8'))
        assert data['revision'] == REVISION
        models += [r['definition'] for r in data['models']]
        pins[source.relative_to(ROOT).as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
    models.sort(key=lambda m: m['key'])
    assert len(models) == 50 and len(pins) == 2
    baseline = []
    for path in sorted((ROOT/'development/hardware').glob('catalog-*-v1.json')):
        baseline += json.loads(path.read_text(encoding='utf-8'))['definitions']
    for folder in ('batch50', 'batch50b', 'batch100', 'batch100b', 'batch100c', 'selected506a'):
        for path in sorted((ROOT/'development/hardware'/folder).glob('*.json')):
            baseline += [r['definition'] for r in json.loads(path.read_text(encoding='utf-8'))['models']]
    assert len(baseline) == 428 and all(m['kind'] in ('rack','desktop') for m in models)
    return models, baseline, pins


def upgrade(lab, old_dll, dll, models, baseline, out):
    db = lab.create_database('selected506b-upgrade29')
    ids, password = fixture(lab, db, old_dll)
    assert lab.sql(db, 'SELECT max(version) FROM schema_migration') == '29'
    commercial = [m for m in baseline if m['identity']['manufacturer']]
    assert len(commercial) == 423
    racks = create_racks(lab, db, ids, ['Preserve '+m['key'] for m in commercial])
    lab.grant_runtime(db)
    server = lab.start_server(db, dll=old_dll)
    session = BatchSession(server, ids, password)
    for model, rack in zip(commercial, racks):
        create(session, model, rack['rack'], 'Existing '+model['key'], baseline)
    expected = ordered(session.project())
    before = state(lab, db, catalog=False)
    history = lab.sql(db, 'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t')
    stored = {table: catalog_rows(lab, db, table) for table in CATALOG}
    server.close()
    assert migrate(lab, db, dll, out/'migration-private.txt') == 0
    assert lab.sql(db, 'SELECT max(version) FROM schema_migration') == '30'
    assert state(lab, db, catalog=False) == before
    assert lab.sql(db, 'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t WHERE version<=29') == history
    for table in CATALOG:
        assert catalog_rows(lab, db, table, [m['key'] for m in baseline]) == stored[table]
    verify_catalog(lab, db, models, 478)
    checkpoint = state(lab, db)
    assert migrate(lab, db, dll, out/'migration-repeat-private.txt') == 0
    assert state(lab, db) == checkpoint
    lab.grant_runtime(db)
    server = lab.start_server(db, dll=dll)
    assert ordered(BatchSession(server, ids, password).project()) == expected
    server.close()
    return dict(sourceSchema=29, targetSchema=30, preservedDefinitions=428, preservedCommercialInstances=423,
                priorInventoryAuditAndOperationsUnchanged=True, priorMigrationHistoryUnchanged=True,
                exactSnapshotPreserved=True, repeatedMigrationUnchanged=True)


def fresh(lab, dll, frontend, models, baseline, out, browser):
    db = lab.create_database('selected506b-fresh30')
    ids, password = fixture(lab, db, dll)
    verify_catalog(lab, db, models, 478)
    racks = create_racks(lab, db, ids, ['Selection '+m['identity']['sku'] for m in models], pdu=True)
    lab.grant_runtime(db)
    server = lab.start_server(db, dll=dll, frontend=frontend)
    session = BatchSession(server, ids, password)
    rows, measurements, replay, wire_counts = [], [], [], Counter()
    companion = next(m for m in baseline if m['key'] == 'switch-24' and m['revision'] == 'hw-reference-v1')
    for model, rack in zip(models, racks):
        own = create(session, model, rack['rack'], model['identity']['model'], baseline)
        other = create(session, companion, rack['rack'], 'Synthetic peer '+model['identity']['sku'], baseline)
        project = session.project()
        ports = verify_device(project, model, own['deviceId'], rack['rack'], own['supportId'])
        peer = verify_device(project, companion, other['deviceId'], rack['rack'], None)
        cables = []
        for kind in ('rj45', 'sfp', 'power'):
            group = next((g for g in model['groups'] if g['type'] == kind), None)
            if group is None:
                continue
            sources = [p['id'] for g in model['groups'] if g['type'] == 'power' for p in ports[g['key']]] if kind == 'power' else [first_port(ports, group)]
            if kind == 'power':
                assert len(sources) <= len(rack['pduPortIds'])
            for index, source in enumerate(sources):
                target = rack['pduPortIds'][index] if kind == 'power' else first_port(peer, next(g for g in companion['groups'] if g['type'] == kind))
                response = session.send(dict(fromPortId=source, toPortId=target), kind='connections.create').json()
                cables.append(dict(id=response['result']['resourceId'], type=kind, fromPortId=source, toPortId=target))
                wire_counts[kind] += 1
        rows.append(dict(key=model['key'], rack=rack['rack'], deviceId=own['deviceId'],
                         portCount=sum(g['count'] for g in model['groups'])))
        replay.append(own)
        measurements.append(dict(key=model['key'], deviceId=own['deviceId'], connections=cables,
                                 uuidFaceRoleGroupOrdinalMatched=True, ports=rows[-1]['portCount']))
    expected = ordered(session.project())
    before = state(lab, db)
    for original in replay[:2]:
        assert session.send(original['request'], key=original['requestId'], revision=original['expectedRevision']).json() == original['response']
        assert state(lab, db) == before
    rejected = payload(models[0], racks[0]['rack'], 'Must rollback')
    lab.sql(db, "CREATE FUNCTION selected506b_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic audit failure'; END $$; CREATE TRIGGER selected506b_fail_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION selected506b_fail_audit()")
    try:
        response = session.client.request('POST', session.route+'/commands', {'type':'device.createHardware', 'payload':rejected},
            {'X-RackClick-Actor':session.actor, 'If-Match':f'"{session.revision}"', 'Idempotency-Key':str(uuid.uuid4())})
        assert response.status >= 500 and state(lab, db) == before
    finally:
        lab.sql(db, 'DROP TRIGGER selected506b_fail_audit ON audit_event; DROP FUNCTION selected506b_fail_audit()')
    for invalid in (rejected|dict(profileVersion='latest'), rejected|dict(profileVersion='batch100c-20261031-v1')):
        assert session.send(invalid, status=422).json()['error'] == 'hardware_revision_unknown'
        assert state(lab, db) == before
    conflict = session.send(rejected, revision=session.revision-1, status=412)
    assert conflict.json()['error'] == 'revision_conflict' and state(lab, db) == before
    reader = Client(server)
    assert reader.login('hardware-reader', password).status == 200
    actor = reader.request('GET', '/api/v1/me').json()['user']['id']
    response = reader.request('POST', session.route+'/commands', {'type':'device.createHardware','payload':rejected},
        {'X-RackClick-Actor':actor, 'If-Match':f'"{session.revision}"', 'Idempotency-Key':str(uuid.uuid4())})
    assert response.status == 403 and state(lab, db) == before
    for table in CATALOG:
        rights = runtime_sql(lab, db, f"SELECT has_table_privilege(current_user,'{table}','SELECT'),has_table_privilege(current_user,'{table}','INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')")
        assert rights.returncode == 0 and rights.stdout.strip() == 't|f'
    assert runtime_sql(lab, db, 'CREATE TABLE selection_must_not_exist(id integer)').returncode != 0
    assert state(lab, db) == before
    second = Client(server)
    assert second.login('hardware-second', password).status == 200
    assert ordered(second.request('GET', session.route+'/project').json()) == expected
    ids['selected506b'] = rows
    fixture_json = json.dumps(ids, ensure_ascii=True, separators=(',', ':'))
    assert len(fixture_json.encode('ascii')) < 24000
    (out/'fixture-ids.json').write_text(fixture_json, encoding='utf-8')
    (out/'expected-project.json').write_text(json.dumps(expected, ensure_ascii=True), encoding='utf-8')
    if browser:
        env = lab.environment()
        env.update(RACKCLICK_TEST_ORIGIN=server.origin, RACKCLICK_TEST_USERNAME='hardware-admin',
                   RACKCLICK_TEST_PASSWORD=password, RACKCLICK_TEST_OUTPUT=str(out), RACKCLICK_FIXTURE=fixture_json)
        with (out/'browser-private.log').open('wb') as log:
            done = subprocess.run([str(toolchain()['node']), str(ROOT/'development/frontend/tests/browser-hardware-selected506b.mjs')],
                cwd=ROOT/'development/frontend', env=env, stdout=log, stderr=log, timeout=600, creationflags=NO_WINDOW)
        assert done.returncode == 0, 'Browser trial failed; private log retained'
        expected = ordered(json.loads((out/'expected-browser-project.json').read_text(encoding='utf-8')))
        assert ordered(session.project()) == expected
    server.close()
    server = lab.start_server(db, dll=dll, frontend=frontend)
    second = Client(server)
    assert second.login('hardware-second', password).status == 200
    assert ordered(second.request('GET', session.route+'/project').json()) == expected
    return dict(schema=30, modelsCreated=len(rows), modelPorts=sum(r['portCount'] for r in rows),
                modelResults=measurements, connections=sum(wire_counts.values()), cablesByType=dict(wire_counts),
                replayVerified=True, rollbackVerified=True, conflictRejected=True, readerRejected=True,
                secondSessionEqual=True, restartPersistence=True, runtimeCatalogSelectOnly=True,
                browserExecuted=browser)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dll', 'baseline-dll', 'frontend', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--browser', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    assert out.is_relative_to((ROOT/'.local').resolve()) and not out.exists()
    out.mkdir(parents=True)
    protect_directory(out)
    models, baseline, pin = authoring()
    result = dict(result='FAIL', vmAccessed=False, qaAccessed=False, sourceSha256=pin)
    lab = None
    start = time.monotonic()
    try:
        lab = Lab('hardware-selected506b')
        with lab:
            result['upgrade'] = upgrade(lab, args.baseline_dll, args.dll, models, baseline, out)
            result.update(fresh(lab, args.dll, args.frontend, models, baseline, out, args.browser))
            for name, expected in pin.items():
                assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected
            result.update(result='PASS', postgresql=lab.sql('postgres', 'SHOW server_version'))
    except BaseException as error:
        result.update(result='FAIL', failureType=type(error).__name__)
        (out/'runner-private.log').write_text(traceback.format_exc(), encoding='utf-8')
    finally:
        result.update(elapsedSeconds=round(time.monotonic()-start, 3), labStopped=lab is None or not lab.running,
                      serversStopped=lab is None or all(server.process.poll() is not None for server in lab.servers))
        (out/'RESULTADOS.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({k:result[k] for k in ('result', 'modelsCreated', 'modelPorts', 'connections', 'browserExecuted',
                                              'labStopped', 'serversStopped', 'failureType') if k in result}))
    return 0 if result['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
