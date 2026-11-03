"""Prepared Windows/PG17 trial for family L, schema41 ->43; no build step.

Creates NEW pg_support laboratories only. Run by the coordinator with frozen DLLs.
Raw logs, credentials and UUID/project fixtures remain under a new .local output.
The optional browser hook is browser-hardware-selected506l.mjs, supplied separately.
"""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import traceback
import uuid

from pg_support import Lab, Client, NO_WINDOW, literal, protect_directory, toolchain
from test_hardware_mounting_gui import fixture
from test_hardware_catalog17 import CATALOG, migrate, runtime_sql
from test_hardware_batch100c import BatchSession, ordered, payload, digest
from test_hardware_selected506k import authoring as k_authoring, create_model as k_create

ROOT = Path(__file__).resolve().parents[3]
REVISION = 'selected506l-20261101-v1'
SUPPORT_REVISION = 'selected506l-support-20261101-v1'
PLAN = 'evidence/s1-20261101/integracion506l/PLAN-FAMILIAS.json'
EXTENSIONS = ('hardware_profile_extension', 'hardware_group_extension')
CATALOG_TABLES = (*CATALOG, 'hardware_connector_template', *EXTENSIONS)
INVENTORY_TABLES = ('customer', 'inventory_site', 'inventory_building', 'inventory_room',
    'inventory_rack', 'inventory_device', 'inventory_port_group', 'inventory_port',
    'inventory_connection', 'inventory_connection_endpoint', 'operation', 'audit_event')
GROUP_EXTRAS = ('physicalFace', 'interfaceRole', 'signalRole', 'powerSystem')
PORT_PROPERTIES = dict(physicalConnector='hardwarePhysicalConnector', physicalFace='hardwarePhysicalFace',
    interfaceRole='hardwareInterfaceRole', signalRole='hardwareSignalRole', powerSystem='hardwarePowerSystem')
ROOM_KINDS = {'wall', 'pole', 'din', 'floor'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def authoring():
    new_k, older, k_shelf, pins = k_authoring()
    baseline = older + new_k + [k_shelf]
    assert len(baseline) == 805 and sum(bool(m['identity']['manufacturer']) for m in baseline) == 799
    plan_path = ROOT / PLAN
    plan = json.loads(plan_path.read_bytes())
    assert (plan['baselineSchema'], plan['targetSchema'], plan['models']) == (41, 43, 62)
    models = []
    pins = dict(pins)
    pins[PLAN] = sha(plan_path)
    for family, expected in plan['authoring'].items():
        path = ROOT / f'development/hardware/selected506l/{family}.json'
        data = json.loads(path.read_bytes())
        assert data['formatVersion'] == 1 and data['revision'] == REVISION
        part = [row['definition'] for row in data['models']]
        assert {m['key'] for m in part} == {'selected-' + m['id'] for m in expected}
        models.extend(part)
        pins[path.relative_to(ROOT).as_posix()] = sha(path)
    path = ROOT / 'development/hardware/selected506l/support-revisions.json'
    data = json.loads(path.read_bytes())
    assert data['revision'] == SUPPORT_REVISION and len(data['models']) == 1
    receiver = data['models'][0]['definition']
    assert receiver['identity']['sku'] == 'USW-Pro-24-POE'
    assert sum(g['count'] for g in receiver['groups']) == 28
    pins[path.relative_to(ROOT).as_posix()] = sha(path)
    assert len(models) == len({m['key'] for m in models}) == 62
    assert sum(g['count'] for m in models for g in m['groups']) == 1673
    assert len({(m['key'], m['revision']) for m in baseline + models + [receiver]}) == 868
    assert len({m['key'] for m in baseline + models + [receiver] if m['identity']['manufacturer']}) == 861
    return sorted(models, key=lambda m: m['key']), baseline, receiver, pins


def table_rows(lab, db, table, *, omit=()):
    assert table in (*INVENTORY_TABLES, *CATALOG_TABLES, 'schema_migration')
    assert all(re.fullmatch('[a-z_][a-z_0-9]*', key) for key in omit)
    expression = 'to_jsonb(t)' + ('-ARRAY[' + ','.join(literal(k) for k in omit) + ']' if omit else '')
    return json.loads(lab.sql(db, f"SELECT COALESCE(jsonb_agg({expression} ORDER BY ({expression})::text),'[]') FROM {table} t"))


def checkpoint(lab, db):
    # One psql round trip per checkpoint. Every column and row participates;
    # hashing on PG avoids repeatedly copying the growing private receipt log.
    queries = [f"SELECT '{t}' AS name,encode(sha256(convert_to(COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]')::text,'UTF8')),'hex') AS value FROM {t} t"
        for t in (*INVENTORY_TABLES, *CATALOG_TABLES, 'schema_migration')]
    return digest(json.loads(lab.sql(db, 'SELECT jsonb_object_agg(name,value) FROM ('+' UNION ALL '.join(queries)+') s')))


def columns(lab, db, table):
    assert table in INVENTORY_TABLES
    return json.loads(lab.sql(db, "SELECT jsonb_object_agg(column_name,is_nullable) FROM information_schema.columns "
        f"WHERE table_schema='public' AND table_name={literal(table)}"))


def assert_old_project(old, current):
    """Only allow NEW nullable rack metadata absent from that exact old DTO."""
    old, current = ordered(copy.deepcopy(old)), ordered(copy.deepcopy(current))
    before = {r['id']: r for r in old['racks']}
    for row in current['racks']:
        for key in ('hardwareProfileKey', 'hardwareProfileRevision'):
            if key in row and key not in before[row['id']]:
                assert row[key] is None, (row['id'], key)
                del row[key]
    assert current == old


def verify_catalog(lab, db, models, receiver):
    assert lab.sql(db, 'SELECT count(*) FROM hardware_definition') == '868'
    assert lab.sql(db, "SELECT count(*),count(DISTINCT profile_key) FROM hardware_definition WHERE manufacturer IS NOT NULL") == '862|861'
    all_rows = {t: table_rows(lab, db, t) for t in CATALOG_TABLES}
    for m in models + [receiver]:
        same = lambda r: (r['profile_key'], r['revision']) == (m['key'], m['revision'])
        row = next(r for r in all_rows['hardware_definition'] if same(r))
        assert row['sealed'] and row['definition_sha256'] == digest(m)
        assert (row['mount_kind'], row['rack_units'], row['width_mm'], row['height_mm'], row['depth_mm']) == (
            m['kind'], m['rackUnits'], m['dimensionsMm']['width'], m['dimensionsMm']['height'], m['dimensionsMm']['depth'])
        assert row['color'] == m['color']
        assert all(row[k] == m['identity'][k] for k in ('manufacturer', 'family', 'model', 'sku'))
        actual = sorted((r for r in all_rows['hardware_group_template'] if same(r)), key=lambda r: r['sort_order'])
        assert len(actual) == len(m['groups'])
        for order, (r, g) in enumerate(zip(actual, m['groups'])):
            assert (r['group_key'], r['sort_order'], r['type'], r['port_count'], r['face'], r['name'], r['prefix'], r['power_role']) == (
                g['key'], order, g['type'], g['count'], g['face'], g['name'], g['prefix'], g['powerRole'])
            pc = [r for r in all_rows['hardware_connector_template'] if same(r) and r['group_key'] == g['key']]
            assert pc == ([dict(profile_key=m['key'], revision=m['revision'], group_key=g['key'], physical_connector=g['physicalConnector'])]
                if g.get('physicalConnector') is not None else [])
            ext = [r['metadata'] for r in all_rows['hardware_group_extension'] if same(r) and r['group_key'] == g['key']]
            expected = {k: g[k] for k in GROUP_EXTRAS if k in g}
            assert ext == ([expected] if expected else [])
        ext = [r['metadata'] for r in all_rows['hardware_profile_extension'] if same(r)]
        assert ext == [dict(mounting=m['mounting'], configuration=m.get('configuration', []), continuities=m.get('continuities', []))]
        slots = sorted((r for r in all_rows['hardware_mount_slot'] if same(r)), key=lambda r: r['slot_key'])
        assert [(s['slot_key'], s['width_mm'], s['height_mm'], s['depth_mm']) for s in slots] == [
            (s['key'], s['dimensionsMm']['width'], s['dimensionsMm']['height'], s['dimensionsMm']['depth']) for s in sorted(m['slots'], key=lambda s: s['key'])]
        pt = [r for r in all_rows['hardware_passthrough'] if same(r)]
        c = m['passthrough']
        assert pt == ([dict(profile_key=m['key'], revision=m['revision'], front_group_key=c['frontGroup'], rear_group_key=c['rearGroup'], port_count=c['count'])] if c else [])


def upgrade(lab, old_dll, dll, models, baseline, receiver, out):
    db = lab.create_database('selected506l-upgrade41')
    ids, password = fixture(lab, db, old_dll)
    assert lab.sql(db, 'SELECT max(version) FROM schema_migration') == '41'
    assert lab.sql(db, 'SELECT count(*) FROM hardware_definition') == '805'
    commercial = [m for m in baseline if m['identity']['manufacturer']]
    house = lab.sql(db, 'SELECT id FROM systemhaus')
    racks = [str(uuid.uuid4()) for _ in commercial]
    statements = [f"INSERT INTO inventory_rack(id,systemhaus_id,customer_id,name,size_u) VALUES({literal(r)},{literal(house)},{literal(ids['customer'])},{literal('Preserve '+m['key'])},60);" for r, m in zip(racks, commercial)]
    lab.sql(db, 'BEGIN;\n' + '\n'.join(statements) + '\nCOMMIT;', sensitive=True)
    lab.grant_runtime(db)
    server = lab.start_server(db, dll=old_dll)
    session = BatchSession(server, ids, password)
    receipts = []
    for m, rack in zip(commercial, racks):
        receipts.append(k_create(session, m, rack, 'Previous '+m['key'][:80], baseline))
    expected = ordered(session.project())
    old_columns = {t: columns(lab, db, t) for t in INVENTORY_TABLES}
    before = {t: table_rows(lab, db, t) for t in INVENTORY_TABLES}
    old_catalog = {t: table_rows(lab, db, t) for t in (*CATALOG, 'hardware_connector_template')}
    old_pairs = {(r['profile_key'], r['revision']) for r in old_catalog['hardware_definition']}
    history = table_rows(lab, db, 'schema_migration')
    server.close()
    assert migrate(lab, db, dll, out/'migration-41-43-private.txt') == 0
    assert lab.sql(db, 'SELECT max(version) FROM schema_migration') == '43'
    additions = {}
    for table in INVENTORY_TABLES:
        after_columns = columns(lab, db, table)
        assert set(old_columns[table]) <= set(after_columns)
        added = set(after_columns)-set(old_columns[table])
        # Only the two NEW nullable rack binding columns may be ignored. Existing
        # metadata, generated columns and every old value remain compared literally.
        assert not added or table == 'inventory_rack' and added <= {'hardware_profile_key', 'hardware_profile_revision'}
        for col in added:
            assert after_columns[col] == 'YES'
            assert lab.sql(db, f'SELECT count(*) FROM {table} WHERE {col} IS NOT NULL') == '0'
        assert table_rows(lab, db, table, omit=sorted(added)) == before[table]
        if added: additions[table] = sorted(added)
    assert [r for r in table_rows(lab, db, 'schema_migration') if r['version'] <= 41] == history
    for table, old in old_catalog.items():
        assert [r for r in table_rows(lab, db, table) if (r['profile_key'], r['revision']) in old_pairs] == old
    for table in EXTENSIONS:
        assert not any((r['profile_key'], r['revision']) in old_pairs for r in table_rows(lab, db, table))
    verify_catalog(lab, db, models, receiver)
    frozen = checkpoint(lab, db)
    assert migrate(lab, db, dll, out/'migration-repeat-private.txt') == 0
    assert checkpoint(lab, db) == frozen
    lab.grant_runtime(db)
    server = lab.start_server(db, dll=dll)
    session = BatchSession(server, ids, password)
    assert_old_project(expected, session.project())
    for entry in (receipts[0], receipts[-1]):
        assert session.send(entry['request'], key=entry['requestId'], revision=entry['expectedRevision']).json() == entry['response']
        assert checkpoint(lab, db) == frozen
    second = Client(server)
    assert second.login('hardware-second', password).status == 200
    assert_old_project(expected, second.request('GET', session.route+'/project').json())
    server.close()
    return dict(sourceSchema=41, targetSchema=43, preservedDefinitions=805, preservedCommercialInstances=799,
        oldInventoryAuditOperationsReceiptsAndHistoryUnchanged=True, nullableNewColumnsOnly=additions,
        repeatedMigrationUnchanged=True, oldRevisionReplayUnchanged=True, secondSessionEqual=True)


def placement_fixture(lab, db, ids):
    house = lab.sql(db, 'SELECT id FROM systemhaus')
    keys = ('site', 'building', 'room', 'secondRoom', 'foreignCustomer', 'foreignSite', 'foreignBuilding', 'foreignRoom', 'smallRack', 'tinyRack', 'otherRack')
    ids.update({k: str(uuid.uuid4()) for k in keys})
    sql = [f"INSERT INTO customer(id,systemhaus_id,name) VALUES({literal(ids['foreignCustomer'])},{literal(house)},'Other synthetic customer');"]
    for prefix, customer in (('', ids['customer']), ('foreign', ids['foreignCustomer'])):
        site, building = ids['site' if not prefix else 'foreignSite'], ids['building' if not prefix else 'foreignBuilding']
        rooms = [ids['room'], ids['secondRoom']] if not prefix else [ids['foreignRoom']]
        sql += [f"INSERT INTO inventory_site(id,systemhaus_id,customer_id,name) VALUES({literal(site)},{literal(house)},{literal(customer)},'Synthetic site');",
            f"INSERT INTO inventory_building(id,systemhaus_id,customer_id,site_id,name) VALUES({literal(building)},{literal(house)},{literal(customer)},{literal(site)},'Synthetic building');"]
        for room in rooms: sql.append(f"INSERT INTO inventory_room(id,systemhaus_id,customer_id,building_id,name) VALUES({literal(room)},{literal(house)},{literal(customer)},{literal(building)},'Synthetic room');")
    for key, capacity in [('smallRack', 12), ('tinyRack', 4), ('otherRack', 60)]:
        sql.append(f"INSERT INTO inventory_rack(id,systemhaus_id,customer_id,room_id,name,size_u) VALUES({literal(ids[key])},{literal(house)},{literal(ids['customer'])},{literal(ids['room'])},{literal(key)},{capacity});")
    lab.sql(db, 'BEGIN;\n'+'\n'.join(sql)+'\nCOMMIT;', sensitive=True)


def fit_support(model, definitions):
    choices = [(m, s) for m in definitions if m['kind'] == 'shelf' for s in m['slots']
        if all(model['dimensionsMm'][k] is not None and model['dimensionsMm'][k] <= s['dimensionsMm'][k] for k in ('width', 'height', 'depth'))]
    assert choices, ('No real shelf fit', model['key'])
    return min(choices, key=lambda p: (p[0]['rackUnits'], p[0]['key'], p[1]['key']))


def create_model(session, model, rack, room, name, definitions, *, side='vertical-left'):
    parent = slot = support_key = None
    if model['kind'] == 'rackContainer':
        request = dict(profileKey=model['key'], profileVersion=model['revision'], roomId=room, name=name)
        kind = 'rack.createHardware'
    else:
        kind = 'device.createHardware'
        if model['kind'] == 'desktop':
            support, bay = fit_support(model, definitions)
            parent = session.send(payload(support, rack, 'Support '+name[:85])).json()['result']['resourceId']
            slot, support_key = bay['key'], support['key']
        elif model['kind'] == 'sharedU':
            allowed = model['mounting'].get('parentProfileKeys', [])
            support = next(m for m in definitions if m['kind'] == 'rack' and m['rackUnits'] > 0 and (not allowed or m['key'] in allowed))
            parent = session.send(payload(support, rack, 'Root parent '+name[:82])).json()['result']['resourceId']
            slot, support_key = 'shared', support['key']
        elif model['kind'] == 'vertical0U': slot = side
        if model['kind'] in ROOM_KINDS:
            request = dict(profileKey=model['key'], profileVersion=model['revision'], roomId=room, name=name)
        else:
            request = payload(model, rack, name, parent, slot)
            # The older helper couples slot to a parent. A vertical rack side
            # has an explicit slot and deliberately has no parent device.
            if model['kind'] == 'vertical0U': request['mountSlotKey'] = slot
    key, revision = str(uuid.uuid4()), session.revision
    try:
        response = session.send(request, kind=kind, key=key, revision=revision).json()
    except AssertionError as error:
        raise AssertionError((model['key'], model['identity']['sku'], model['kind'], request, str(error))) from error
    return dict(resourceId=response['result']['resourceId'], deviceId=None if kind == 'rack.createHardware' else response['result']['resourceId'],
        rack=rack, room=room, supportId=parent, supportKey=support_key, slot=slot, request=request,
        kind=kind, requestId=key, expectedRevision=revision, response=response)


def verify_device(project, model, entry):
    if model['kind'] == 'rackContainer':
        rack = next(r for r in project['racks'] if r['id'] == entry['resourceId'])
        assert rack['hardwareProfileKey'] == model['key']
        assert rack['roomId'] == entry['room'] and rack['sizeU'] == model['mounting']['capacityU']
        assert not any(d['rackId'] == rack['id'] for d in project['devices'])
        device, groups, ports = rack, [], []
    else:
        device = next(d for d in project['devices'] if d['id'] == entry['deviceId'])
        assert device['hardwareProfileKey'] == model['key']
        if model['kind'] in ROOM_KINDS:
            assert (device['kind'], device['rackId'], device['roomId'], device['sizeU'], device['mountParentId'], device['mountSlotKey']) == ('endDevice', None, entry['room'], None, None, None)
        else:
            assert (device['kind'], device['rackId'], device['roomId'], device['sizeU'], device['mountParentId'], device['mountSlotKey']) == (
                'rackEquipment', entry['rack'], None, model['rackUnits'], entry['supportId'], entry['slot'])
        if entry['supportId']:
            parent = next(d for d in project['devices'] if d['id'] == entry['supportId'])
            assert parent['rackId'] == entry['rack'] and parent['mountParentId'] is None and parent['sizeU'] > 0
        groups = [g for g in project['portGroups'] if g['deviceId'] == entry['deviceId']]
        ports = [p for p in project['ports'] if p['deviceId'] == entry['deviceId']]
    props = device['properties']
    assert props['hardwareProfileVersion'] == model['revision']
    assert props['hardwareIdentity'] == model['identity']
    assert props['physicalDimensionsMm'] == model['dimensionsMm']
    assert props['hardwareMounting'] == model['mounting']
    assert props['hardwareConfiguration'] == model.get('configuration', [])
    assert props['hardwareContinuities'] == model.get('continuities', [])
    assert len(groups) == len(model['groups']) and len(ports) == sum(g['count'] for g in model['groups'])
    result = {}
    for order, expected in enumerate(model['groups']):
        group = next(g for g in groups if g['sortOrder'] == order)
        assert str(uuid.UUID(group['id'])) == group['id']
        assert (group['type'], group['name'], group['prefix']) == (expected['type'], expected['name'].strip(), expected['prefix'].strip())
        actual = sorted((p for p in ports if p['groupId'] == group['id']), key=lambda p: p['gn'])
        assert [p['gn'] for p in actual] == list(range(1, expected['count']+1))
        for port in actual:
            assert str(uuid.UUID(port['id'])) == port['id'] and port['deviceId'] == entry['deviceId']
            assert (port['type'], port['face'], port['powerRole']) == (expected['type'], expected['face'], expected['powerRole'])
            assert port['properties']['hardwareGroupKey'] == expected['key']
            assert port['properties']['hardwarePortKey'] == expected['key']+':'+str(port['gn'])
            for source, target in PORT_PROPERTIES.items(): assert port['properties'].get(target) == expected.get(source)
        result[expected['key']] = actual
    assert len({p['id'] for p in ports}) == len(ports)
    return result


def verify_power_guards(lab, db, ids):
    """Real row checks: adding DC must not remove the pre-existing PoE guard."""
    cases = []
    for name, typ, role, poe, accepted, constraint in (
        ('dc_inlet', 'power_dc', 'inlet', False, True, None),
        ('data_inlet', 'rj45', 'inlet', False, False, 'inventory_port_check1'),
        ('sfp_poe', 'sfp', 'unspecified', True, False, 'inventory_port_check'),
        ('rj45_poe', 'rj45', 'unspecified', True, True, None)):
        observed = True
        try:
            lab.sql(db, f"BEGIN; UPDATE inventory_port_group SET type={literal(typ)} WHERE id={literal(ids['legacyGroup'])}; "
                f"UPDATE inventory_port SET type={literal(typ)},power_role={literal(role)},poe={'true' if poe else 'false'} "
                f"WHERE group_id={literal(ids['legacyGroup'])}; ROLLBACK;")
        except RuntimeError as error:
            observed = False
            assert constraint and f'check constraint "{constraint}"' in str(error), str(error)
        assert observed == accepted, (name, accepted, observed)
        cases.append(dict(name=name, accepted=observed))
    return cases


def fresh(lab, dll, frontend, models, baseline, receiver, out, browser):
    db = lab.create_database('selected506l-fresh43')
    ids, password = fixture(lab, db, dll)
    assert lab.sql(db, 'SELECT max(version) FROM schema_migration') == '43'
    power_guards = verify_power_guards(lab, db, ids)
    placement_fixture(lab, db, ids)
    verify_catalog(lab, db, models, receiver)
    house = lab.sql(db, 'SELECT id FROM systemhaus')
    racks = {m['key']: str(uuid.uuid4()) for m in models if m['kind'] != 'rackContainer'}
    sql = [f"INSERT INTO inventory_rack(id,systemhaus_id,customer_id,room_id,name,size_u) VALUES({literal(r)},{literal(house)},{literal(ids['customer'])},{literal(ids['room'])},{literal('L '+key)},60);" for key, r in racks.items()]
    lab.sql(db, 'BEGIN;\n'+'\n'.join(sql)+'\nCOMMIT;', sensitive=True)
    lab.grant_runtime(db)
    server = lab.start_server(db, dll=dll, frontend=frontend)
    session = BatchSession(server, ids, password)
    definitions = baseline + models + [receiver]
    entries, primary, peers = [], {}, {}
    for m in models:
        rack = racks.get(m['key'])
        a = create_model(session, m, rack, ids['room'], m['identity']['model'], definitions)
        b = create_model(session, m, rack, ids['room'], 'Peer '+m['identity']['model'], definitions, side='vertical-right') if m['groups'] else None
        primary[m['key']] = a
        if b: peers[m['key']] = b
        entries.append(dict(key=m['key'], revision=m['revision'], sku=m['identity']['sku'], kind=m['kind'],
            rack=a['resourceId'] if m['kind'] == 'rackContainer' else rack, room=ids['room'], deviceId=a['deviceId'],
            resourceId=a['resourceId'], peerId=b['deviceId'] if b else None, supportId=a['supportId'], supportKey=a['supportKey'],
            mountSlotKey=a['slot'], portCount=sum(g['count'] for g in m['groups'])))
    rps_model = next(m for m in models if m['identity']['sku'] == 'USP-RPS')
    receiver_entry = create_model(session, receiver, racks[rps_model['key']], ids['room'], 'Real USP receiver', definitions)
    receiver_peer = create_model(session, receiver, racks[rps_model['key']], ids['room'], 'Real USP receiver peer', definitions)
    duplicates = {}
    for m in models:
        if m['kind'] != 'rackContainer': continue
        source = primary[m['key']]['resourceId']
        duplicate = session.send(dict(id=source, name='Empty duplicate '+m['identity']['model'], includeConnections=False), kind='rack.duplicate').json()['result']['resourceId']
        assert str(uuid.UUID(duplicate)) == duplicate and duplicate != source
        duplicates[m['key']] = primary[m['key']] | dict(resourceId=duplicate)
        for rid in (source, duplicate):
            assert lab.sql(db, f"SELECT hardware_profile_key,hardware_profile_revision,size_u FROM inventory_rack WHERE id={literal(rid)}") == '|'.join((m['key'], m['revision'], str(m['mounting']['capacityU'])))
            assert lab.sql(db, f"SELECT count(*),COALESCE(sum(size_u),0) FROM inventory_device WHERE rack_id={literal(rid)}") == '0|0'
    project = ordered(session.project())
    own = {m['key']: verify_device(project, m, primary[m['key']]) for m in models}
    peer_ports = {m['key']: verify_device(project, m, peers[m['key']]) for m in models if m['key'] in peers}
    receiver_ports = verify_device(project, receiver, receiver_entry)
    receiver_peer_ports = verify_device(project, receiver, receiver_peer)
    for m in models:
        if m['key'] in duplicates: verify_device(project, m, duplicates[m['key']])
    for key in peer_ports:
        assert {p['id'] for ps in own[key].values() for p in ps}.isdisjoint(p['id'] for ps in peer_ports[key].values() for p in ps)
    assert sum(e['portCount'] for e in entries) == 1673
    assert sum(m['kind'] == 'rackContainer' for m in models) == 4
    used, counts, gui_pairs = set(), Counter(), []
    def connect(a, b):
        response = session.send(dict(fromPortId=a['id'], toPortId=b['id']), kind='connections.create').json()
        used.update([a['id'], b['id']]); counts[a['type']] += 1
        return response['result']['resourceId']
    # One API pair per raw type, using independent materialized instances. The
    # DC positive is deliberately the real USP outlet -> revised USW receiver.
    all_types = {g['type'] for m in models for g in m['groups']}
    for typ in sorted(all_types-{'power', 'power_dc'}):
        m = next(m for m in models if any(g['type'] == typ for g in m['groups']))
        g = next(g for g in m['groups'] if g['type'] == typ)
        connect(own[m['key']][g['key']][0], peer_ports[m['key']][g['key']][0])
    all_model_ports = [p for by in own.values() for ps in by.values() for p in ps]
    ac_in = next(p for p in all_model_ports if p['type'] == 'power' and p['powerRole'] == 'inlet')
    ac_out = next(p for p in all_model_ports if p['type'] == 'power' and p['powerRole'] == 'outlet')
    connect(ac_out, ac_in)
    rps_group = next(g for g in rps_model['groups'] if g['type'] == 'power_dc')
    receiver_group = next(g for g in receiver['groups'] if g.get('powerSystem') == 'unifi-smartpower')
    rps_ports = own[rps_model['key']][rps_group['key']]
    usp_in = receiver_ports[receiver_group['key']][0]
    connect(rps_ports[0], usp_in)
    assert set(counts) == all_types
    # Reserve spare pairs for optional native-browser Click-Click checks.
    for typ in sorted(all_types-{'power', 'power_dc'}):
        for m in models:
            if m['kind'] in ROOM_KINDS: continue
            found = False
            for g in m['groups']:
                if g['type'] != typ or m['key'] not in peer_ports: continue
                available = [(a, b) for a, b in zip(own[m['key']][g['key']], peer_ports[m['key']][g['key']]) if a['id'] not in used and b['id'] not in used]
                if available:
                    a, b = available[0]; gui_pairs.append(dict(type=typ, rack=racks[m['key']], room=ids['room'], fromPortId=a['id'], toPortId=b['id'], face=a['face'])); found = True; break
            if found: break
    gui_pairs.append(dict(type='power_dc', rack=racks[rps_model['key']], room=ids['room'], fromPortId=rps_ports[1]['id'], toPortId=receiver_peer_ports[receiver_group['key']][0]['id'], face=rps_ports[1]['face']))
    for m in models:
        if m['key'] not in peer_ports: continue
        available = [p for by in (own[m['key']], peer_ports[m['key']]) for ps in by.values() for p in ps if p['type'] == 'power' and p['id'] not in used]
        inlet = next((p for p in available if p['powerRole'] == 'inlet'), None)
        outlet = next((p for p in available if p['powerRole'] == 'outlet' and inlet and p['face'] == inlet['face']), None)
        if inlet and outlet:
            gui_pairs.append(dict(type='power', rack=racks[m['key']], room=ids['room'], fromPortId=outlet['id'], toPortId=inlet['id'], face=outlet['face']))
            break
    assert all(p['fromPortId'] not in used and p['toPortId'] not in used for p in gui_pairs)
    assert len({p[k] for p in gui_pairs for k in ('fromPortId', 'toPortId')}) == 2*len(gui_pairs)
    expected = ordered(session.project())
    frozen = checkpoint(lab, db)
    negative = []
    def reject(body, kind, status, error=None):
        response = session.send(body, kind=kind, status=status)
        if error: assert response.json()['error'] == error, (kind, error, response.body)
        assert checkpoint(lab, db) == frozen
        negative.append(dict(kind=kind, status=status, error=response.json().get('error')))
    for m in models:
        a = primary[m['key']]
        if m['kind'] in {'desktop', 'sharedU', 'vertical0U'}:
            reject(a['request'] | dict(name='Duplicate occupied mount'), 'device.createHardware', 409, 'mount_slot_occupied')
    vertical = next(m for m in models if m['kind'] == 'vertical0U')
    for rack in ('smallRack', 'tinyRack'):
        reject(primary[vertical['key']]['request'] | dict(rackId=ids[rack]), 'device.createHardware', 422, 'mount_dimensions_invalid')
    shared = next(m for m in models if m['kind'] == 'sharedU')
    reject(primary[shared['key']]['request'] | dict(rackId=ids['otherRack']), 'device.createHardware', 422, 'mount_support_invalid')
    reject(primary[shared['key']]['request'] | dict(mountParentId=primary[shared['key']]['deviceId']), 'device.createHardware', 422, 'mount_support_invalid')
    room_model = next(m for m in models if m['kind'] in ROOM_KINDS)
    reject(primary[room_model['key']]['request'] | dict(roomId=ids['foreignRoom']), 'device.createHardware', 404, 'not_found')
    reject(primary[room_model['key']]['request'] | dict(rackId=ids['otherRack']), 'device.createHardware', 422, 'mount_profile_incompatible')
    container = next(m for m in models if m['kind'] == 'rackContainer')
    reject(primary[container['key']]['request'], 'device.createHardware', 422, 'hardware_rack_command_required')
    reject(dict(profileKey=room_model['key'], profileVersion=room_model['revision'], roomId=ids['room'], name='Wrong command'), 'rack.createHardware', 422, 'hardware_profile_invalid')
    populated = next(m for m in models if m['kind'] == 'rack')
    reject(dict(id=racks[populated['key']], name='Unsupported populated duplicate', includeConnections=False), 'rack.duplicate', 422, 'hardware_duplicate_unsupported')
    dc_in = next(p for p in all_model_ports if p['type'] == 'power_dc' and p['powerRole'] == 'inlet' and p['properties'].get('hardwarePowerSystem') == 'dc')
    for a, b in [(rps_ports[2], dc_in), (rps_ports[2], rps_ports[3]), (usp_in, receiver_peer_ports[receiver_group['key']][0]), (rps_ports[2], ac_in)]:
        reject(dict(fromPortId=a['id'], toPortId=b['id']), 'connections.create', 409, 'connection_incompatible')
    reject(dict(fromPortId=rps_ports[0]['id'], toPortId=usp_in['id']), 'connections.create', 409, 'port_occupied')
    typed = {t: next(p for p in all_model_ports if p['type'] == t) for t in all_types}
    for a, b in [('sas', 'rj45'), ('fiber', 'rj45'), ('sfpdd', 'sfp'), ('qsfpdd', 'qsfp'), ('dsl', 'rj45'), ('telephony', 'rj45'), ('ipc', 'rj45')]:
        reject(dict(fromPortId=typed[a]['id'], toPortId=typed[b]['id']), 'connections.create', 409, 'connection_incompatible')
    # Reserved properties reject both replacement and JSON-null removal.
    for field in PORT_PROPERTIES.values():
        sample = next(p for p in all_model_ports if p['properties'].get(field) is not None)
        for value in ('synthetic-tamper', None):
            reject(dict(deviceId=sample['deviceId'], groupId=sample['groupId'], groupType=sample['type'], portIds=[sample['id']], changes={'properties': {field: value}}), 'ports.update', 422, 'hardware_metadata_immutable')
    sample_model = next(m for m in models if m['kind'] == 'rack')
    request = primary[sample_model['key']]['request'] | dict(name='Atomic rollback candidate')
    for field in ('hardwareMounting', 'hardwareConfiguration', 'hardwareContinuities'):
        reject(dict(id=primary[sample_model['key']]['deviceId'], properties={field: None}), 'device.update', 422, 'hardware_metadata_immutable')
    for entry in (primary[container['key']], primary[sample_model['key']]):
        assert session.send(entry['request'], kind=entry['kind'], key=entry['requestId'], revision=entry['expectedRevision']).json() == entry['response']
        assert checkpoint(lab, db) == frozen
        reject_body = entry['request'] | dict(name='Different replay body')
        response = session.send(reject_body, kind=entry['kind'], key=entry['requestId'], revision=entry['expectedRevision'], status=409)
        assert response.json().get('error') and checkpoint(lab, db) == frozen
    assert session.send(request, revision=session.revision-1, status=412).json()['error'] == 'revision_conflict'
    assert checkpoint(lab, db) == frozen
    reject(request | dict(profileVersion='latest'), 'device.createHardware', 422, 'hardware_revision_unknown')
    reader = Client(server)
    assert reader.login('hardware-reader', password).status == 200
    actor = reader.request('GET', '/api/v1/me').json()['user']['id']
    response = reader.request('POST', session.route+'/commands', {'type': 'device.createHardware', 'payload': request},
        {'X-RackClick-Actor': actor, 'If-Match': f'"{session.revision}"', 'Idempotency-Key': str(uuid.uuid4())})
    assert response.status == 403 and checkpoint(lab, db) == frozen
    hidden = reader.request('GET', f"/api/v1/customers/{ids['foreignCustomer']}/project")
    # RequireRead intentionally hides the existence of customers outside scope.
    assert hidden.status == 404 and hidden.json()['error'] == 'not_found'
    assert checkpoint(lab, db) == frozen
    # Owner mutation of either immutable extension must roll back without data/audit changes.
    for table in EXTENSIONS:
        for sql in (f'UPDATE {table} SET metadata=metadata', f'DELETE FROM {table}', f'TRUNCATE {table}'):
            try: lab.sql(db, sql)
            except RuntimeError as e: assert 'sealed' in str(e).lower() or 'immutable' in str(e).lower(), str(e)
            else: raise AssertionError('Owner extension mutation accepted: '+table)
            assert checkpoint(lab, db) == frozen
    # Intentional catalog corruption exists only briefly in this new disposable
    # fixture, using the migration owner; restore even if runtime comparison fails.
    for table, mutate in [('hardware_group_extension', lambda m: {**m, 'interfaceRole': 'management' if m.get('interfaceRole') != 'management' else 'ethernet'}),
                          ('hardware_profile_extension', lambda m: {**m, 'configuration': [{**m['configuration'][0], 'description': 'Synthetic mismatching BOM'}, *m['configuration'][1:]]})]:
        candidates = table_rows(lab, db, table)
        row = next(r for r in candidates if r['metadata'].get('configuration')) if table == 'hardware_profile_extension' else next(r for r in candidates if r['metadata'].get('interfaceRole'))
        m = next(m for m in models+[receiver] if (m['key'], m['revision']) == (row['profile_key'], row['revision']))
        target = dict(profileKey=m['key'], profileVersion=m['revision'], rackId=ids['otherRack'], name='Catalog mismatch')
        where = ' AND '.join(f'{k}={literal(row[k])}' for k in ('profile_key', 'revision', *(['group_key'] if table == 'hardware_group_extension' else [])))
        def restore(metadata):
            lab.sql(db, f"BEGIN; ALTER TABLE {table} DISABLE TRIGGER {table}_immutable; UPDATE {table} SET metadata={literal(json.dumps(metadata))}::jsonb WHERE {where}; ALTER TABLE {table} ENABLE TRIGGER {table}_immutable; COMMIT;", sensitive=True)
        try:
            restore(mutate(copy.deepcopy(row['metadata'])))
            response = session.send(target, status=409)
            assert response.json()['error'] == 'hardware_catalog_definition_mismatch'
        finally: restore(row['metadata'])
        assert checkpoint(lab, db) == frozen
    lab.sql(db, "CREATE FUNCTION selected506l_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic audit failure'; END $$; CREATE TRIGGER selected506l_fail_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION selected506l_fail_audit()")
    try:
        response = session.client.request('POST', session.route+'/commands', {'type': 'device.createHardware', 'payload': request},
            {'X-RackClick-Actor': session.actor, 'If-Match': f'"{session.revision}"', 'Idempotency-Key': str(uuid.uuid4())})
        assert response.status >= 500 and checkpoint(lab, db) == frozen
    finally: lab.sql(db, 'DROP TRIGGER selected506l_fail_audit ON audit_event; DROP FUNCTION selected506l_fail_audit()')
    for table in CATALOG_TABLES:
        rights = runtime_sql(lab, db, f"SELECT has_table_privilege(current_user,'{table}','SELECT'),has_table_privilege(current_user,'{table}','INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')")
        assert rights.returncode == 0 and rights.stdout.strip() == 't|f'
    for table in EXTENSIONS:
        assert runtime_sql(lab, db, f'UPDATE {table} SET metadata=metadata').returncode != 0
    assert runtime_sql(lab, db, 'CREATE TABLE selected506l_forbidden_ddl(id integer)').returncode != 0
    assert runtime_sql(lab, db, 'ALTER TABLE inventory_device ADD COLUMN selected506l_forbidden integer').returncode != 0
    assert checkpoint(lab, db) == frozen
    second = Client(server)
    assert second.login('hardware-second', password).status == 200
    assert ordered(second.request('GET', session.route+'/project').json()) == expected
    ids.update(selected506l=entries, guiPairs=gui_pairs, emptyRackDuplicates=[dict(key=key, sourceId=primary[key]['resourceId'], id=e['resourceId']) for key,e in duplicates.items()], uspReceiver=dict(key=receiver['key'], revision=receiver['revision'], deviceId=receiver_entry['deviceId'], peerId=receiver_peer['deviceId'], rack=racks[rps_model['key']]))
    fixture_json = json.dumps(ids, ensure_ascii=True, separators=(',', ':'))
    (out/'fixture-ids.json').write_text(fixture_json, encoding='utf-8')
    (out/'expected-project.json').write_text(json.dumps(expected, ensure_ascii=False), encoding='utf-8')
    if browser:
        env = lab.environment()
        env.update(RACKCLICK_TEST_ORIGIN=server.origin, RACKCLICK_TEST_USERNAME='hardware-admin', RACKCLICK_TEST_PASSWORD=password,
            RACKCLICK_TEST_OUTPUT=str(out), RACKCLICK_FIXTURE_PATH=str(out/'fixture-ids.json'))
        # Windows environment values are bounded. Small fixtures retain the older
        # inline hook; the file path is authoritative for the full62 fixture.
        if len(fixture_json) < 24000: env['RACKCLICK_FIXTURE'] = fixture_json
        with (out/'browser-private.log').open('wb') as log:
            done = subprocess.run([str(toolchain()['node']), str(ROOT/'development/frontend/tests/browser-hardware-selected506l.mjs')],
                cwd=ROOT/'development/frontend', env=env, stdout=log, stderr=log, timeout=1200, creationflags=NO_WINDOW)
        assert done.returncode == 0, 'Native browser hook failed; private log retained'
        expected = ordered(json.loads((out/'expected-browser-project.json').read_bytes()))
        assert ordered(session.project()) == expected
    server.close()
    server = lab.start_server(db, dll=dll, frontend=frontend)
    second = Client(server)
    assert second.login('hardware-second', password).status == 200
    assert ordered(second.request('GET', session.route+'/project').json()) == expected
    return dict(schema=43, modelsCreated=62, modelPorts=1673, receiverPorts=28, rackContainersCreated=4, emptyRackContainersDuplicated=4,
        powerRoleAndPoeGuards=power_guards,
        commercialRevisionRows=862, commercialModelKeys=861, catalogDefinitions=868,
        mountingByKind=dict(Counter(m['kind'] for m in models)), modelPortCounts=[dict(key=e['key'], count=e['portCount']) for e in entries],
        peerInstances=len(peers), cablesByType=dict(counts), connections=sum(counts.values()),
        browserPairTypes=[p['type'] for p in gui_pairs], browserPairsExecuted=len(gui_pairs) if browser else 0,
        uuidGroupsOrdinalsFacesConnectorMetadataAndBOMVerified=True, realUspReceiverConnected=True,
        rejectedCases=negative, bothExtensionTablesOwnerImmutable=True, bothExtensionTablesRuntimeSelectOnly=True,
        mismatchingProfileAndGroupMetadataRejected=True, rollbackAuditVerified=True, replayConflictAndReaderVerified=True,
        secondSessionEqual=True, restartPersistence=True, browserExecuted=browser)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dll', 'baseline-dll', 'frontend', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--browser', action='store_true')
    args = parser.parse_args()
    dll, old_dll, frontend = args.dll.resolve(strict=True), args.baseline_dll.resolve(strict=True), args.frontend.resolve(strict=True)
    out = args.output.resolve()
    assert out.is_relative_to((ROOT/'.local').resolve()) and not out.exists(), 'Use a NEW private output directory under .local'
    out.mkdir(parents=True)
    protect_directory(out)
    result = dict(result='FAIL', executed=True, vmAccessed=False, qaAccessed=False, installedServicesAccessed=False,
        sourceSchema=41, targetSchema=43, serverSha256=sha(dll), baselineServerSha256=sha(old_dll), frontendSha256=sha(frontend/'app.js'))
    start, lab, stage = time.monotonic(), None, 'authoring'
    try:
        models, baseline, receiver, pins = authoring()
        result['sourceSha256'] = pins
        stage = 'new-laboratory'
        lab = Lab('hardware-selected506l')
        with lab:
            stage = 'upgrade41-to43'
            result['upgrade'] = upgrade(lab, old_dll, dll, models, baseline, receiver, out)
            stage = 'fresh43'
            result.update(fresh(lab, dll, frontend, models, baseline, receiver, out, args.browser))
            stage = 'source-pins'
            assert all(sha(ROOT/name) == pin for name, pin in pins.items())
            assert [digest(m) for m in authoring()[1]] == [digest(m) for m in baseline]
            result.update(result='PASS', postgresql=lab.sql('postgres', 'SHOW server_version'))
    except BaseException as error:
        result.update(failureType=type(error).__name__, failureStage=stage)
        (out/'runner-private.log').write_text(traceback.format_exc(), encoding='utf-8')
    finally:
        result.update(elapsedSeconds=round(time.monotonic()-start, 3), labStopped=lab is None or not lab.running,
            serversStopped=lab is None or all(s.process.poll() is not None for s in lab.servers))
        (out/'RESULTADOS.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({k: result[k] for k in ('result', 'modelsCreated', 'modelPorts', 'connections', 'browserExecuted', 'labStopped', 'serversStopped', 'failureType', 'failureStage') if k in result}))
    return 0 if result['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
