"""Real PG17/API trial for batch100; optional browser on the same isolated database.

Run only with final schema27 and frozen schema26 builds. All secrets/raw logs stay
under .local; no VM, installed service or QA database is opened. This script does
not build .NET, alter source files or infer successful checks from old evidence.
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
from test_hardware_catalog17 import Session, state, migrate, runtime_sql, CATALOG

ROOT = Path(__file__).resolve().parents[3]
PROJECT_COLLECTIONS = ('sites', 'buildings', 'rooms', 'racks', 'devices', 'portGroups', 'ports', 'connections')


def ordered(project):
    for key in PROJECT_COLLECTIONS:
        project[key].sort(key=lambda row: row['id'])
    return project


def digest(value):
    return hashlib.sha256((json.dumps(value, ensure_ascii=True, sort_keys=True,
                                     separators=(',', ':')) + '\n').encode('ascii')).hexdigest()


def load_definitions():
    """Read final authoring files once; later changes are detected at trial end."""
    sources = sorted((ROOT/'development/hardware/batch100b').glob('*.json'))
    assert len(sources) == 3, 'Exactly three completed batch100 source files required'
    models, pins = [], {}
    for source in sources:
        raw = source.read_bytes(); data = json.loads(raw)
        assert data['formatVersion'] == 1 and data['revision'] == 'batch100b-20261031-v1'
        models.extend(row['definition'] for row in data['models'])
        pins[source.relative_to(ROOT).as_posix()] = hashlib.sha256(raw).hexdigest()
    assert len(models) == 100 and len({(m['key'], m['revision']) for m in models}) == 100
    baseline = []
    for source in sorted((ROOT/'development/hardware').glob('catalog-*-v1.json')):
        baseline.extend(json.loads(source.read_text(encoding='utf-8'))['definitions'])
    for folder in ('batch50','batch50b','batch100'):
        for source in sorted((ROOT/('development/hardware/'+folder)).glob('*.json')):
            baseline.extend(row['definition'] for row in json.loads(source.read_text(encoding='utf-8'))['models'])
    assert len(baseline) == 211 and len({(m['key'], m['revision']) for m in baseline}) == 211
    assert not ({m['key'] for m in baseline} & {m['key'] for m in models})
    for model in models:
        assert model['kind'] in ('rack', 'desktop')
        assert any(g['type'] in ('rj45', 'sfp') for g in model['groups'])
    return models, baseline, pins


class BatchSession(Session):
    """Reuse HTTP/session contract, avoiding one growing snapshot per command."""
    def __init__(self, server, ids, password):
        super().__init__(server, ids, password)
        self.revision = self.project()['revision']

    def send(self, payload, *, kind='device.createHardware', status=200, key=None, revision=None):
        expected = self.revision if revision is None else revision
        response = self.client.request('POST', self.route+'/commands',
            {'type': kind, 'payload': payload}, {'X-RackClick-Actor': self.actor,
             'If-Match': f'"{expected}"', 'Idempotency-Key': key or str(uuid.uuid4())})
        assert response.status == status, (kind, status, response.status, response.body)
        if status == 200:
            self.revision = max(self.revision, response.json()['revision'])
        return response


def choose_support(model, baseline):
    if model['kind'] != 'desktop':
        return None
    candidates = []
    for support in baseline:
        if support['key'] not in ('shelf-2u', 'shelf-5u') or support['kind'] != 'shelf':
            continue
        for slot in support['slots']:
            if all(model['dimensionsMm'][k] <= slot['dimensionsMm'][k] for k in ('width', 'height', 'depth')):
                candidates.append((support, slot))
    assert candidates, 'No approved existing shelf fits nominal source dimensions: '+model['key']
    return min(candidates, key=lambda pair: (pair[0]['rackUnits'], pair[0]['key'], pair[1]['key']))


def payload(model, rack, name, parent=None, slot=None):
    result = dict(profileKey=model['key'], profileVersion=model['revision'], rackId=rack, name=name)
    if parent is not None:
        result.update(mountParentId=parent, mountSlotKey=slot)
    return result


def create(session, model, rack, name, baseline):
    parent, slot, support_key = None, None, None
    support = choose_support(model, baseline)
    if support:
        support_model, slot_model = support
        parent = session.send(payload(support_model, rack, 'Support '+name)).json()['result']['resourceId']
        slot, support_key = slot_model['key'], support_model['key']
    request = payload(model, rack, name, parent, slot)
    key, revision = str(uuid.uuid4()), session.revision
    response = session.send(request, key=key, revision=revision).json()
    return dict(deviceId=response['result']['resourceId'], supportId=parent,
                supportKey=support_key, request=request, requestId=key,
                expectedRevision=revision, response=response)


def create_racks(lab, db, ids, names, *, pdu=False):
    """Only initial, administrator-owned fixture DML. Never seeds model instances."""
    house = lab.sql(db, 'SELECT id FROM systemhaus')
    rows, statements = [], ['BEGIN;']
    for name in names:
        rack = str(uuid.uuid4()); row = dict(rack=rack, rackName=name)
        statements.append(f"INSERT INTO inventory_rack(id,systemhaus_id,customer_id,name,size_u) VALUES({literal(rack)},{literal(house)},{literal(ids['customer'])},{literal(name)},20);")
        if pdu:
            device, group, port = (str(uuid.uuid4()) for _ in range(3))
            second_port = str(uuid.uuid4())
            row.update(pduId=device, pduPortId=port, pduPortIds=[port, second_port])
            statements += [
                f"INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order,properties) VALUES({literal(device)},{literal(house)},{literal(ids['customer'])},'rackEquipment',{literal(rack)},'Synthetic two-outlet PDU',1,0,'{{\"preset\":\"pdu\",\"color\":\"#34363a\"}}');",
                f"INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order) VALUES({literal(group)},{literal(house)},{literal(ids['customer'])},{literal(device)},'power','Synthetic outlet','AC ',0);",
                f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,face,power_role) VALUES({literal(port)},{literal(house)},{literal(ids['customer'])},{literal(device)},{literal(group)},'power',1,0,'front','outlet'),({literal(second_port)},{literal(house)},{literal(ids['customer'])},{literal(device)},{literal(group)},'power',2,1,'front','outlet');"]
        rows.append(row)
    statements.append('COMMIT;'); lab.sql(db, '\n'.join(statements), sensitive=True)
    return rows


def catalog_rows(lab, db, table, keys=None):
    assert table in CATALOG
    where = '' if keys is None else ' WHERE profile_key IN ('+', '.join(literal(k) for k in keys)+')'
    return json.loads(lab.sql(db, f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM {table} t{where}"))


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
        assert not any((s['profile_key'],s['revision']) == pair for s in passthrough)


def verify_device(project, model, device_id, rack, parent):
    device = next(d for d in project['devices'] if d['id'] == device_id)
    assert str(uuid.UUID(device_id)) == device_id
    assert device['hardwareProfileKey'] == model['key'] and device['rackId'] == rack
    assert device['mountParentId'] == parent and device['sizeU'] == model['rackUnits']
    assert device['mountSlotKey'] == ('main' if parent else None)
    assert device['properties']['hardwareProfileVersion'] == model['revision']
    assert device['properties']['physicalDimensionsMm'] == model['dimensionsMm']
    assert device['properties']['color'] == model['color']
    if model['identity']['manufacturer'] is None:
        assert 'hardwareIdentity' not in device['properties']
    else:
        assert device['properties']['hardwareIdentity'] == model['identity']
    groups = [g for g in project['portGroups'] if g['deviceId'] == device_id]
    ports = [p for p in project['ports'] if p['deviceId'] == device_id]
    assert len(groups) == len(model['groups']) and len(ports) == sum(g['count'] for g in model['groups'])
    assert len({p['id'] for p in ports}) == len(ports)
    by_key = {}
    for order,expected in enumerate(model['groups']):
        matching = [g for g in groups if g['sortOrder'] == order]
        assert len(matching) == 1; group = matching[0]
        assert str(uuid.UUID(group['id'])) == group['id']
        # Existing AddGroup uses Text(), which trims API names/prefixes. The
        # sealed template retains its literal prefix; endpoint identity never
        # depends on that display whitespace.
        assert (group['type'],group['name'],group['prefix']) == (expected['type'],expected['name'].strip(),expected['prefix'].strip()), (model['key'],expected['key'])
        rows = sorted((p for p in ports if p['groupId'] == group['id']), key=lambda p:p['gn'])
        assert [p['gn'] for p in rows] == list(range(1,expected['count']+1))
        for port in rows:
            assert port['type'] == expected['type'] and port['face'] == expected['face']
            assert port['powerRole'] == expected.get('powerRole','unspecified')
            assert port['properties']['hardwareGroupKey'] == expected['key']
            assert port['properties']['hardwarePortKey'] == expected['key']+':'+str(port['gn'])
            assert str(uuid.UUID(port['id'])) == port['id']
        by_key[expected['key']] = rows
    return by_key


def upgrade_trial(lab, baseline_dll, dll, baseline, models, out, result):
    db = lab.create_database('batch100b-upgrade26')
    ids, password = fixture(lab, db, baseline_dll)
    commercial = [m for m in baseline if m['provenance']['kind'] == 'manufacturer-specification']
    assert len(commercial) == 206
    assert lab.sql(db, 'SELECT max(version) FROM schema_migration') == '26'
    assert lab.sql(db, 'SELECT count(*) FROM hardware_definition') == str(len(baseline))
    racks = create_racks(lab, db, ids, ['Prior '+m['key'] for m in commercial])
    lab.grant_runtime(db); server = lab.start_server(db, dll=baseline_dll)
    session = BatchSession(server, ids, password); prior_instances = []
    for model, row in zip(commercial, racks):
        created = create(session, model, row['rack'], 'Frozen '+model['key'], baseline)
        prior_instances.append(dict(key=model['key'], deviceId=created['deviceId'],
                                    rack=row['rack'], supportId=created['supportId']))
    expected = ordered(session.project()); frozen = state(lab, db, catalog=False)
    history = lab.sql(db, 'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t')
    before_catalog = {table: catalog_rows(lab, db, table) for table in CATALOG}
    server.close()
    assert migrate(lab, db, dll, out/'migrate-26-27-private.txt') == 0
    assert lab.sql(db, 'SELECT max(version) FROM schema_migration') == '27'
    assert state(lab, db, catalog=False) == frozen
    assert lab.sql(db, 'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t WHERE version<=26') == history
    for table in CATALOG:
        assert catalog_rows(lab, db, table, [m['key'] for m in baseline]) == before_catalog[table]
    verify_catalog(lab, db, models, len(baseline)+len(models))
    checkpoint = state(lab, db)
    assert migrate(lab, db, dll, out/'migrate-repeat-private.txt') == 0
    assert state(lab, db) == checkpoint
    lab.grant_runtime(db); restarted = lab.start_server(db, dll=dll)
    assert ordered(BatchSession(restarted, ids, password).project()) == expected
    restarted.close()
    result['upgrade'] = dict(sourceSchema=26, targetSchema=27, preservedCommercialModels=prior_instances,
                             preservedDefinitions=len(baseline), preservedMigrationHistoryThrough=26,
                             inventoryAuditOperationsUnchanged=True, snapshotPreserved=True,
                             repeatedMigrationUnchanged=True)
    result['checks'].append('26->27 preserves206 commercial instances, UUIDs/mounts, prior definitions and history1..26; repeat migration and API snapshot unchanged')


def first_port(by_key, group, ordinal=1):
    return next(p['id'] for p in by_key[group['key']] if p['gn'] == ordinal)


def fresh_trial(lab, dll, frontend, baseline, models, pins, out, browser, result):
    db = lab.create_database('batch100b-fresh27'); ids, password = fixture(lab, db, dll)
    assert lab.sql(db, 'SELECT max(version) FROM schema_migration') == '27'
    verify_catalog(lab, db, models, len(baseline)+len(models))
    racks = create_racks(lab, db, ids, ['Batch '+m['identity']['sku'] for m in models], pdu=True)
    validation_racks = create_racks(lab, db, ids, ['Batch rollback empty support', 'Batch low support rejection'])
    lab.grant_runtime(db); server = lab.start_server(db, dll=dll, frontend=frontend)
    session = BatchSession(server, ids, password)
    companion = next(m for m in baseline if m['key'] == 'switch-24' and m['revision'] == 'hw-reference-v1')
    assert sum(g['count'] for g in companion['groups']) == 26
    rows, replays = [], {}
    result['modelResults'] = rows
    for model, rack_row in zip(models, racks):
        started = time.monotonic()
        created = create(session, model, rack_row['rack'], 'Batch '+model['identity']['sku'], baseline)
        companion_id = session.send(payload(companion, rack_row['rack'], 'Companion '+model['key'])).json()['result']['resourceId']
        row = dict(key=model['key'], revision=model['revision'], rack=rack_row['rack'],
                   deviceId=created['deviceId'], supportId=created['supportId'], supportKey=created['supportKey'],
                   companionId=companion_id, pduId=rack_row['pduId'], pduPortId=rack_row['pduPortId'], pduPortIds=rack_row['pduPortIds'],
                   portCount=sum(g['count'] for g in model['groups']), createSeconds=round(time.monotonic()-started,3))
        rows.append(row)
        result['modelsCreated'] = len(rows)
        if model['kind'] not in replays:
            replays[model['kind']] = created
    project = session.project()
    all_ids = [r['id'] for k in ('devices','portGroups','ports') for r in project[k]]
    assert len(all_ids) == len(set(all_ids))
    pristine_ports = {p['id']: p for p in project['ports']}
    used_ports, cables, type_counts = set(), [], Counter()
    model_measurements = []
    for model, row in zip(models, rows):
        by_key = verify_device(project, model, row['deviceId'], row['rack'], row['supportId'])
        peer = verify_device(project, companion, row['companionId'], row['rack'], None)
        network = [g for g in model['groups'] if g['type'] in ('rj45','sfp')]
        primary = next((g for g in network if g['type'] == 'rj45'), network[0])
        selected = [primary]
        sfp = next((g for g in network if g['type'] == 'sfp'), None)
        if sfp is not None and sfp['key'] != primary['key']:
            selected.append(sfp)
        connection_rows = []
        for group in selected:
            peer_group = next(g for g in companion['groups'] if g['type'] == group['type'] and
                              g['face'] == ('front' if group['type'] == 'rj45' else 'rear'))
            source, target = first_port(by_key, group), first_port(peer, peer_group)
            data = session.send(dict(fromPortId=source, toPortId=target), kind='connections.create').json()
            cable = dict(id=data['result']['resourceId'], type=group['type'], fromPortId=source, toPortId=target)
            cables.append(cable); connection_rows.append(cable); used_ports.update((source,target)); type_counts[group['type']] += 1
        inlets = [(g, ordinal) for g in model['groups'] if g['type'] == 'power' and g.get('powerRole') == 'inlet' for ordinal in range(1, g['count'] + 1)]
        assert len(inlets) <= len(row['pduPortIds'])
        for inlet_index, (inlet, ordinal) in enumerate(inlets):
            source, target = first_port(by_key, inlet, ordinal), row['pduPortIds'][inlet_index]
            assert next(p for p in project['ports'] if p['id'] == target)['powerRole'] == 'outlet'
            data = session.send(dict(fromPortId=source, toPortId=target), kind='connections.create').json()
            cable = dict(id=data['result']['resourceId'], type='power', fromPortId=source, toPortId=target)
            cables.append(cable); connection_rows.append(cable); used_ports.update((source,target)); type_counts['power'] += 1
        model_measurements.append(row | dict(groups=[dict(key=g['key'], type=g['type'], face=g['face'],
            powerRole=g.get('powerRole','unspecified'), portIds=[p['id'] for p in by_key[g['key']]]) for g in model['groups']],
            connections=connection_rows, uuidFaceRoleGroupOrdinalMatched=True))
    expected = ordered(session.project())
    actual_cables = {c['id']: c for c in expected['connections']}
    assert len(actual_cables) == len(cables)
    for cable in cables:
        assert actual_cables[cable['id']]['fromPortId'] == cable['fromPortId']
        assert actual_cables[cable['id']]['toPortId'] == cable['toPortId']
    for port in expected['ports']:
        if port['id'] not in used_ports:
            assert port == pristine_ports[port['id']], 'Unused port changed'
    for model, row in zip(models, rows):
        verify_device(expected, model, row['deviceId'], row['rack'], row['supportId'])
    assert len(replays) >= 2, 'Need desktop and rack representatives for exact replay'
    checkpoint = state(lab, db)
    for replay in list(replays.values())[:2]:
        assert session.send(replay['request'], key=replay['requestId'], revision=replay['expectedRevision']).json() == replay['response']
        assert state(lab, db) == checkpoint
    result['checks'].append('All100 profiles created by API with exact group/UUID/face/role/ordinal; every model primary network, every available first SFP and every AC inlet connected; unused ports preserved; two exact replays unchanged')

    # Fresh empty supports for rollback and dimensional rejection, created by API.
    nas = next(m for m in models if m['kind'] == 'desktop' and m['dimensionsMm']['height'] > 60)
    support_model, slot = choose_support(nas, baseline)
    rollback_parent = session.send(payload(support_model, validation_racks[0]['rack'], 'Rollback empty shelf')).json()['result']['resourceId']
    low = next(m for m in baseline if m['key'] == 'shelf-2u' and m['revision'] == 'hw-reference-v1')
    low_parent = session.send(payload(low, validation_racks[1]['rack'], 'Unchanged60mm low shelf')).json()['result']['resourceId']
    rejected = payload(nas, validation_racks[0]['rack'], 'Must rollback', rollback_parent, slot['key'])
    prior = state(lab, db)
    lab.sql(db,"CREATE FUNCTION batch50_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic audit failure'; END $$; CREATE TRIGGER batch50_fail_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION batch50_fail_audit()")
    try:
        response = session.client.request('POST', session.route+'/commands',
            {'type':'device.createHardware','payload':rejected}, {'X-RackClick-Actor':session.actor,
             'If-Match':f'"{session.revision}"','Idempotency-Key':str(uuid.uuid4())})
        assert response.status >= 500 and state(lab, db) == prior
    finally:
        lab.sql(db,'DROP TRIGGER batch50_fail_audit ON audit_event; DROP FUNCTION batch50_fail_audit()')
    for invalid,error in [(rejected|dict(profileVersion='batch50-unknown'),'hardware_revision_unknown'),
                          (rejected|dict(rackId=validation_racks[1]['rack'],mountParentId=low_parent,mountSlotKey='main'),'mount_dimensions_invalid')]:
        assert session.send(invalid,status=422).json()['error'] == error
        assert state(lab, db) == prior
    reader = Client(server); assert reader.login('hardware-reader',password).status == 200
    actor = reader.request('GET','/api/v1/me').json()['user']['id']
    response = reader.request('POST', session.route+'/commands',{'type':'device.createHardware','payload':rejected},
        {'X-RackClick-Actor':actor,'If-Match':f'"{session.revision}"','Idempotency-Key':str(uuid.uuid4())})
    assert response.status == 403 and state(lab, db) == prior
    for table in CATALOG:
        rights = runtime_sql(lab,db,f"SELECT has_table_privilege(current_user,'{table}','SELECT'),has_table_privilege(current_user,'{table}','INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')")
        assert rights.returncode == 0 and rights.stdout.strip() == 't|f'
        assert runtime_sql(lab,db,f'SELECT count(*) FROM {table}').returncode == 0
        for sql in (f'DELETE FROM {table}',f'TRUNCATE {table}',f'UPDATE {table} SET revision=revision',
                    f'INSERT INTO {table} SELECT * FROM {table} WHERE false'):
            assert runtime_sql(lab,db,sql).returncode != 0
    assert runtime_sql(lab,db,'CREATE TABLE batch50_must_not_exist(id integer)').returncode != 0
    assert state(lab,db) == prior
    result['checks'].append('Forced audit failure rolls back device/mount/groups/ports/revision/operation; reader403, unknown revision422, NAS in60mm shelf422 and runtime catalogDML/DDL rejects without mutation')

    expected = ordered(session.project())
    (out/'expected-project.json').write_text(json.dumps(expected,ensure_ascii=True),encoding='utf-8')
    ids['batch100b'] = [{key:row[key] for key in ('key','rack','deviceId','portCount')} for row in rows]
    # Fixture variable intentionally excludes port arrays/names/snapshot and secrets.
    fixture_json = json.dumps(ids,ensure_ascii=True,separators=(',',':'))
    assert len(json.dumps(ids['batch100b'],separators=(',',':')).encode('ascii')) < 24000
    assert len(fixture_json.encode('ascii')) < 24000
    (out/'fixture-ids.json').write_text(fixture_json,encoding='utf-8')
    second = Client(server); assert second.login('hardware-second',password).status == 200
    assert ordered(second.request('GET',session.route+'/project').json()) == expected
    if browser:
        env = lab.environment(); env.update(RACKCLICK_TEST_ORIGIN=server.origin,
            RACKCLICK_TEST_USERNAME='hardware-admin',RACKCLICK_TEST_PASSWORD=password,
            RACKCLICK_TEST_OUTPUT=str(out),RACKCLICK_FIXTURE=fixture_json)
        with (out/'browser-private.log').open('wb') as log:
            done = subprocess.run([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-hardware-batch100b.mjs')],
                cwd=ROOT/'development/frontend',env=env,stdout=log,stderr=log,timeout=900,creationflags=NO_WINDOW)
        assert done.returncode == 0, 'Browser trial failed; private log retained'
        assert ordered(session.project()) == expected, 'Browser changed API baseline snapshot'
    server.close(); restarted = lab.start_server(db,dll=dll,frontend=frontend)
    other = Client(restarted); assert other.login('hardware-second',password).status == 200
    assert ordered(other.request('GET',session.route+'/project').json()) == expected
    result.update(schema=27,modelResults=model_measurements,modelsCreated=len(rows),
        modelPorts=sum(row['portCount'] for row in rows),ports=len(expected['ports']),
        connections=len(cables),cablesByType=dict(type_counts),unusedPortsUnchanged=True,
        exactReplayRepresentatives=2,readerDeniedWithoutMutation=True,rollbackVerified=True,
        secondSessionEqual=True,restartPersistence=True,browserExecuted=bool(browser),
        runtimeCatalogSelectOnly=True,dcConnectionsTested=False)
    result['checks'].append('Second authorized session and ASP.NET host restart read the exact UUID/mount/cable snapshot; optional browser runs on this same PG before restart')
    for name,expected_pin in pins.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected_pin, 'Authoring changed during trial'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dll','baseline-dll','frontend','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--browser',action='store_true',help='Run the coordinator browser script on this same fresh PG')
    args = parser.parse_args(); dll=args.dll.resolve(strict=True); baseline_dll=args.baseline_dll.resolve(strict=True)
    frontend=args.frontend.resolve(strict=True); out=args.output.resolve()
    assert out.is_relative_to((ROOT/'.local').resolve()) and not out.exists()
    out.mkdir(parents=True,exist_ok=False); protect_directory(out)
    result = dict(result='FAIL',checks=[],serverSha256=hashlib.sha256(dll.read_bytes()).hexdigest(),
        baselineSha256=hashlib.sha256(baseline_dll.read_bytes()).hexdigest(),
        appSha256=hashlib.sha256((frontend/'app.js').read_bytes()).hexdigest(),
        qaAccessed=False,vmAccessed=False,browserExecuted=False)
    lab=None; started=time.monotonic()
    try:
        models,baseline,pins=load_definitions(); result['sourcePins']=pins
        # Dimension/source checks occur before any PostgreSQL process is started.
        for model in models: choose_support(model,baseline)
        if args.browser: assert (ROOT/'development/frontend/tests/browser-hardware-batch100b.mjs').is_file()
        lab=Lab('hardware-batch100b')
        with lab:
            upgrade_trial(lab,baseline_dll,dll,baseline,models,out,result)
            fresh_trial(lab,dll,frontend,baseline,models,pins,out,args.browser,result)
            result.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'))
    except BaseException as error:
        result.update(result='FAIL',failureType=type(error).__name__)
        (out/'runner-private.log').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        result.update(elapsedSeconds=round(time.monotonic()-started,3),
            labStopped=lab is None or not lab.running,
            serversStopped=lab is None or all(server.process.poll() is not None for server in lab.servers))
        (out/'RESULTADOS.json').write_text(json.dumps(result,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:result[k] for k in ('result','modelsCreated','modelPorts','ports','connections',
            'cablesByType','browserExecuted','labStopped','serversStopped','elapsedSeconds','failureType') if k in result},indent=2))
    return 0 if result['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
