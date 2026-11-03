"""Real PostgreSQL 17 trial for two physical families from the fixed 506 selection.

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
                                    catalog_rows, digest, verify_device, first_port, payload)

ROOT = Path(__file__).resolve().parents[3]
REVISION = 'selected506j-20261101-v1'


def verify_catalog(lab, db, models, expected_total):
    assert lab.sql(db, 'SELECT count(*) FROM hardware_definition') == str(expected_total)
    keys = [m['key'] for m in models]
    definitions = {(d['profile_key'], d['revision']): d for d in catalog_rows(lab, db, 'hardware_definition', keys)}
    groups = catalog_rows(lab, db, 'hardware_group_template', keys)
    slots = catalog_rows(lab, db, 'hardware_mount_slot', keys)
    passthrough = catalog_rows(lab, db, 'hardware_passthrough', keys)
    assert len(definitions) == len(models)
    for model in models:
        pair = model['key'], model['revision']; row = definitions[pair]; dim = model['dimensionsMm']
        assert row['sealed'] is True and row['definition_sha256'] == digest(model)
        for field, expected in [('mount_kind',model['kind']),('rack_units',model['rackUnits']),
                                ('width_mm',dim['width']),('height_mm',dim['height']),('depth_mm',dim['depth']),
                                ('color',model['color']),('provenance_kind',model['provenance']['kind']),
                                ('source_reference',model['provenance']['source'])]:
            assert row[field] == expected, (pair, field)
        assert all(row[k] == model['identity'][k] for k in ('manufacturer','family','model','sku'))
        actual = sorted((g for g in groups if (g['profile_key'],g['revision']) == pair), key=lambda g:g['sort_order'])
        assert len(actual) == len(model['groups'])
        for order,(stored,expected) in enumerate(zip(actual,model['groups'])):
            assert {k:stored[k] for k in ('group_key','sort_order','type','port_count','face','name','prefix','power_role')} == dict(
                group_key=expected['key'], sort_order=order, type=expected['type'], port_count=expected['count'],
                face=expected['face'], name=expected['name'], prefix=expected['prefix'], power_role=expected.get('powerRole','unspecified'))
        assert not any((s['profile_key'],s['revision']) == pair for s in slots)
        actual_passthrough=[p for p in passthrough if (p['profile_key'],p['revision']) == pair]
        continuity=model['passthrough']
        assert actual_passthrough == ([dict(profile_key=model['key'],revision=model['revision'],
            front_group_key=continuity['frontGroup'],rear_group_key=continuity['rearGroup'],port_count=continuity['count'])] if continuity else [])



def authoring():
    from test_hardware_selected506i import authoring as prior_authoring
    i_models, earlier, _ = prior_authoring()
    baseline = earlier + i_models
    models, pins = [], {}
    for source in sorted((ROOT/'development/hardware/selected506j').glob('*.json')):
        data = json.loads(source.read_text(encoding='utf-8'))
        assert data['revision'] == REVISION
        models += [row['definition'] for row in data['models']]
        pins[source.relative_to(ROOT).as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
    assert len(models) == 13 and len(pins) == 2 and len(baseline) == 739
    assert len({(m['key'],m['revision']) for m in baseline+models}) == 752
    assert sum(m['kind']=='rack' for m in models)==6 and sum(m['kind']=='desktop' for m in models)==7
    return sorted(models,key=lambda m:m['key']),baseline,pins


def upgrade(lab, old_dll, dll, models, baseline, out):
    db = lab.create_database('selected506j-upgrade38')
    ids, password = fixture(lab, db, old_dll)
    assert lab.sql(db, 'SELECT max(version) FROM schema_migration') == '38'
    commercial = [m for m in baseline if m['identity']['manufacturer']]
    assert len(commercial) == 734
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
    assert lab.sql(db, 'SELECT max(version) FROM schema_migration') == '39'
    assert state(lab, db, catalog=False) == before
    assert lab.sql(db, 'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t WHERE version<=38') == history
    for table in CATALOG:
        assert catalog_rows(lab, db, table, [m['key'] for m in baseline]) == stored[table]
    verify_catalog(lab, db, models, 752)
    checkpoint = state(lab, db)
    assert migrate(lab, db, dll, out/'migration-repeat-private.txt') == 0
    assert state(lab, db) == checkpoint
    lab.grant_runtime(db)
    server = lab.start_server(db, dll=dll)
    assert ordered(BatchSession(server, ids, password).project()) == expected
    server.close()
    return dict(sourceSchema=38, targetSchema=39, preservedDefinitions=739, preservedCommercialInstances=734,
                priorInventoryAuditAndOperationsUnchanged=True, priorMigrationHistoryUnchanged=True,
                exactSnapshotPreserved=True, repeatedMigrationUnchanged=True)




def expand_synthetic_pdu_fixture(lab, db, racks, models):
    """Initial DML in new synthetic fixtures only; no catalogue seed is altered."""
    count = max(2, max(sum(g['count'] for g in m['groups'] if g['type']=='power') for m in models))
    statements = ['BEGIN;']
    for row in racks:
        for ordinal in range(3, count+1):
            port = str(uuid.uuid4()); row['pduPortIds'].append(port)
            statements.append(
                f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,face,power_role) "
                f"SELECT {literal(port)},systemhaus_id,customer_id,device_id,group_id,'power',{ordinal},{ordinal-1},'front','outlet' "
                f"FROM inventory_port WHERE id={literal(row['pduPortId'])};")
    statements.append('COMMIT;'); lab.sql(db, '\n'.join(statements))
    assert all(len(row['pduPortIds']) == count for row in racks)


def fresh(lab, dll, frontend, models, baseline, out, browser):
    db = lab.create_database('selected506j-fresh39')
    ids, password = fixture(lab, db, dll)
    verify_catalog(lab, db, models, 752)
    racks = create_racks(lab, db, ids, ['Selection '+m['identity']['sku'] for m in models], pdu=True)
    expand_synthetic_pdu_fixture(lab, db, racks, models)
    lab.grant_runtime(db)
    server = lab.start_server(db, dll=dll, frontend=frontend)
    session = BatchSession(server, ids, password)
    rows, measurements, replay, wire_counts = [], [], [], Counter()
    reserved_gui_ap = False
    for model, rack in zip(models, racks):
        own = create(session, model, rack['rack'], model['identity']['model'], baseline)
        other = create(session, model, rack['rack'], 'Independent peer '+model['identity']['sku'], baseline)
        project = session.project()
        ports = verify_device(project, model, own['deviceId'], rack['rack'], own['supportId'])
        peer = verify_device(project, model, other['deviceId'], rack['rack'], other['supportId'])
        continuity = model['passthrough']
        if continuity:
            assert continuity['mapping']=='one-to-one' and continuity['tracingAvailable'] is False
            device = next(d for d in project['devices'] if d['id']==own['deviceId'])
            assert device['properties']['declaredPassthrough']==dict(fromGroupKey=continuity['frontGroup'],toGroupKey=continuity['rearGroup'],rule='sameOrdinal',tracingImplemented=False)
            fronts, rears = ports[continuity['frontGroup']], ports[continuity['rearGroup']]
            assert len(fronts)==len(rears)==continuity['count'] and not ({p['id'] for p in fronts}&{p['id'] for p in rears})
            assert [(p['gn'],p['face']) for p in fronts]==[(i,'front') for i in range(1,continuity['count']+1)]
            assert [(p['gn'],p['face']) for p in rears]==[(i,'rear') for i in range(1,continuity['count']+1)]
        else:
            device = next(d for d in project['devices'] if d['id']==own['deviceId'])
            assert 'declaredPassthrough' not in device['properties']
        gui_ap = model['kind']=='desktop' and not reserved_gui_ap
        if gui_ap: reserved_gui_ap=True
        cables = []
        for kind in ('rj45', 'sfp', 'sfp28', 'qsfp', 'sfp56', 'qsfpdd', 'power'):
            group = next((g for g in model['groups'] if g['type'] == kind), None)
            if group is None or (gui_ap and kind=='rj45'):
                continue
            sources = [p['id'] for g in model['groups'] if g['type'] == 'power' for p in ports[g['key']]] if kind == 'power' else [first_port(ports, group)]
            if kind == 'power':
                assert len(sources) <= len(rack['pduPortIds'])
            for index, source in enumerate(sources):
                target = rack['pduPortIds'][index] if kind == 'power' else first_port(peer, next(g for g in model['groups'] if g['type'] == kind))
                response = session.send(dict(fromPortId=source, toPortId=target), kind='connections.create').json()
                cables.append(dict(id=response['result']['resourceId'], type=kind, fromPortId=source, toPortId=target))
                wire_counts[kind] += 1
        if continuity:
            source=first_port(ports,next(g for g in model['groups'] if g['key']==continuity['rearGroup']))
            target=first_port(peer,next(g for g in model['groups'] if g['key']==continuity['rearGroup']))
            response=session.send(dict(fromPortId=source,toPortId=target),kind='connections.create').json()
            cables.append(dict(id=response['result']['resourceId'],type='rj45-rear',fromPortId=source,toPortId=target));wire_counts['rj45-rear']+=1
        rows.append(dict(kind=model['kind'],guiCableCandidate=gui_ap,key=model['key'], rack=rack['rack'], deviceId=own['deviceId'], peerId=other['deviceId'],
                         portCount=sum(g['count'] for g in model['groups'])))
        replay.append(own)
        measurements.append(dict(key=model['key'], deviceId=own['deviceId'], connections=cables,
                                 uuidFaceRoleGroupOrdinalMatched=True, ports=rows[-1]['portCount']))
    # Existing reference equipment provides negative controls without creating
    # fake optical or AC ports on the new AP/panel configurations.
    control = next(m for m in baseline if m['key']=='switch-24')
    control_ids = create(session,control,racks[0]['rack'],'Synthetic family compatibility control',baseline)
    control_ports = verify_device(session.project(),control,control_ids['deviceId'],racks[0]['rack'],control_ids['supportId'])
    typed_rejections=0
    for wanted,forbidden in [('rj45','sfp'),('sfp','rj45'),('rj45','power'),('power','rj45')]:
        project=session.project()
        first_owner=racks[0]['pduId'] if wanted=='power' else control_ids['deviceId']
        second_owner=racks[0]['pduId'] if forbidden=='power' else control_ids['deviceId']
        first=next(p['id'] for p in project['ports'] if p['deviceId']==first_owner and p['type']==wanted)
        second=next(p['id'] for p in project['ports'] if p['deviceId']==second_owner and p['type']==forbidden)
        checkpoint=state(lab,db)
        assert session.send(dict(fromPortId=first,toPortId=second),kind='connections.create',status=409).json()['error']=='connection_incompatible'
        assert state(lab,db)==checkpoint;typed_rejections+=1
    ap=next(entry for entry in rows if entry['kind']=='desktop')
    ap_model=next(m for m in models if m['key']==ap['key'])
    occupied_request=payload(ap_model,ap['rack'],'Must not share occupied shelf')
    ap_device=next(d for d in session.project()['devices'] if d['id']==ap['deviceId'])
    occupied_request.update(mountParentId=ap_device['mountParentId'],mountSlotKey=ap_device['mountSlotKey'])
    checkpoint=state(lab,db)
    assert session.send(occupied_request,status=409).json()['error']=='mount_slot_occupied'
    assert state(lab,db)==checkpoint
    expected = ordered(session.project())
    before = state(lab, db)
    for original in replay[:2]:
        assert session.send(original['request'], key=original['requestId'], revision=original['expectedRevision']).json() == original['response']
        assert state(lab, db) == before
    rollback_index = next(i for i, model in enumerate(models) if model['kind'] == 'rack')
    rejected = payload(models[rollback_index], racks[rollback_index]['rack'], 'Must rollback')
    lab.sql(db, "CREATE FUNCTION selected506j_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic audit failure'; END $$; CREATE TRIGGER selected506j_fail_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION selected506j_fail_audit()")
    try:
        response = session.client.request('POST', session.route+'/commands', {'type':'device.createHardware', 'payload':rejected},
            {'X-RackClick-Actor':session.actor, 'If-Match':f'"{session.revision}"', 'Idempotency-Key':str(uuid.uuid4())})
        assert response.status >= 500 and state(lab, db) == before
    finally:
        lab.sql(db, 'DROP TRIGGER selected506j_fail_audit ON audit_event; DROP FUNCTION selected506j_fail_audit()')
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
    ids['selected506j'] = rows
    fixture_json = json.dumps(ids, ensure_ascii=True, separators=(',', ':'))
    assert len(fixture_json.encode('ascii')) < 24000
    (out/'fixture-ids.json').write_text(fixture_json, encoding='utf-8')
    (out/'expected-project.json').write_text(json.dumps(expected, ensure_ascii=True), encoding='utf-8')
    if browser:
        env = lab.environment()
        env.update(RACKCLICK_TEST_ORIGIN=server.origin, RACKCLICK_TEST_USERNAME='hardware-admin',
                   RACKCLICK_TEST_PASSWORD=password, RACKCLICK_TEST_OUTPUT=str(out), RACKCLICK_FIXTURE=fixture_json)
        with (out/'browser-private.log').open('wb') as log:
            done = subprocess.run([str(toolchain()['node']), str(ROOT/'development/frontend/tests/browser-hardware-selected506j.mjs')],
                cwd=ROOT/'development/frontend', env=env, stdout=log, stderr=log, timeout=600, creationflags=NO_WINDOW)
        assert done.returncode == 0, 'Browser trial failed; private log retained'
        expected = ordered(json.loads((out/'expected-browser-project.json').read_text(encoding='utf-8')))
        assert ordered(session.project()) == expected
    server.close()
    server = lab.start_server(db, dll=dll, frontend=frontend)
    second = Client(server)
    assert second.login('hardware-second', password).status == 200
    assert ordered(second.request('GET', session.route+'/project').json()) == expected
    return dict(schema=39, modelsCreated=len(rows), modelPorts=sum(r['portCount'] for r in rows),
                modelResults=measurements, connections=sum(wire_counts.values()), cablesByType=dict(wire_counts),
                replayVerified=True, rollbackVerified=True, conflictRejected=True, readerRejected=True,
                secondSessionEqual=True, restartPersistence=True, runtimeCatalogSelectOnly=True,
                browserExecuted=browser, typedCrossFamilyRejections=typed_rejections,
                independentPeerInstances=len(rows), guiConnectionsAdded=2 if browser else 0, passiveDeclarationsVerified=6, apShelfFitAndOccupiedSlotRejected=True)


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
        lab = Lab('hardware-selected506j')
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
