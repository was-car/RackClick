"""Private, explicit RC9 laboratory restoration; not a production upload API.

Only a freshly bootstrapped Lab database with zero customers/inventory is accepted.
Original bytes and the identity mapping remain in its private directory. Public
errors contain codes/counts only, never source values, SQL or credentials.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import uuid

NAMESPACE = uuid.UUID('f4aeab6e-92b8-530d-9345-2d1c8e8f2f4d')
TYPES = {'rj45', 'rj45_poe', 'sfp', 'sfp28', 'qsfp', 'mgmt', 'console', 'power', 'usb_a', 'usb_c'}
TABLES = ['customer', 'inventory_site', 'inventory_building', 'inventory_room',
          'inventory_rack', 'inventory_device', 'inventory_port_group', 'inventory_port',
          'inventory_connection', 'inventory_connection_endpoint']


class RestoreError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def reject(code):
    raise RestoreError(code)


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            reject('duplicate_json_key')
        result[key] = value
    return result


def text(value, code, maximum=None, required=False):
    if not isinstance(value, str) or '\x00' in value or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        reject(code)
    if maximum is not None and len(value) > maximum:
        reject(code)
    if required and (not value.strip() or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value)):
        reject(code)
    return value


def integer(value, minimum, maximum, code):
    if type(value) is not int or not minimum <= value <= maximum:
        reject(code)
    return value


def number(value, maximum, code):
    if value is not None and (type(value) not in (int, float) or not 0 <= value <= maximum or not math.isfinite(value)):
        reject(code)
    return value


def color(value):
    if value is not None and (not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value)):
        reject('color_invalid')
    return value


def enum(value, choices, code):
    if not isinstance(value, str) or value not in choices:
        reject(code)
    return value


def ident(kind, *parts):
    return str(uuid.uuid5(NAMESPACE, json.dumps([kind, *parts], ensure_ascii=False, separators=(',', ':'))))


def properties(original, excluded):
    result = {key: value for key, value in original.items() if key not in excluded}
    if 'id' in original:
        result['rc9OriginalId'] = original['id']
    encoded = json.dumps(result, ensure_ascii=False, allow_nan=False)
    if len(encoded.encode('utf-8')) > 8192:
        reject('properties_too_large')
    return result


def analyze(source):
    """Return a validated plan. Contains private source data; do not print it."""
    raw = Path(source).read_bytes()
    try:
        project = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=object_pairs,
                             parse_constant=lambda _: reject('number_invalid'))
    except (UnicodeError, ValueError):
        reject('json_invalid')
    if not isinstance(project, dict) or project.get('version') != '0.8':
        reject('source_version_unsupported')
    house_name = text(project.get('rackclickSystemhaus'), 'systemhaus_name_invalid', 100, True)
    if not isinstance(project.get('racks'), list) or not isinstance(project.get('crossConns'), list):
        reject('source_shape_invalid')
    rows = {table: [] for table in TABLES}
    entities = {key: [] for key in ['customers', 'sites', 'buildings', 'rooms', 'racks', 'devices', 'portGroups', 'ports', 'connections']}
    paths = {key: {} for key in ['customers', 'sites', 'buildings', 'rooms']}
    originals = {key: {} for key in ['racks', 'devices', 'ports', 'connections']}

    def original_id(kind, obj):
        if not isinstance(obj, dict):
            reject('source_shape_invalid')
        value = text(obj.get('id'), 'original_id_invalid', required=True)
        if value in originals[kind]:
            reject('original_id_duplicate')
        originals[kind][value] = obj
        return value

    def path_entity(kind, path, parent):
        key = tuple(path)
        if key not in paths[kind]:
            target = ident(kind, *path)
            paths[kind][key] = target
            entities[kind].append({'path': path, 'id': target})
            table = {'customers': 'customer', 'sites': 'inventory_site', 'buildings': 'inventory_building', 'rooms': 'inventory_room'}[kind]
            row = {'id': target, 'name': path[-1]}
            if kind != 'customers':
                row.update(customer_id=paths['customers'][(path[0],)], properties={})
            if parent:
                row[parent[0]] = parent[1]
            rows[table].append(row)
        return paths[kind][key]

    device_info, port_info = {}, {}
    all_connections = []
    rack_locations = []
    for rack in project['racks']:
        rid = original_id('racks', rack)
        location = rack.get('rackclickLocation')
        if not isinstance(location, dict):
            reject('hierarchy_incomplete')
        path = [text(location.get(k), 'hierarchy_name_invalid', 100, True) for k in ['client', 'site', 'building', 'room']]
        rack_locations.append(location)
        customer = path_entity('customers', path[:1], None)
        site = path_entity('sites', path[:2], None)
        building = path_entity('buildings', path[:3], ('site_id', site))
        room = path_entity('rooms', path, ('building_id', building))
        rack_uuid = ident('racks', rid)
        size = integer(rack.get('size'), 1, 1000, 'rack_size_invalid')
        rows['inventory_rack'].append({'id': rack_uuid, 'customer_id': customer, 'room_id': room,
            'name': text(rack.get('name'), 'rack_name_invalid', 100, True),
            'location': text(rack.get('location', ''), 'location_invalid'), 'size_u': size,
            'properties': properties(rack, {'id', 'name', 'location', 'size', 'devs', 'conns', 'rackclickLocation'})})
        entities['racks'].append({'originalId': rid, 'id': rack_uuid, 'customerId': customer})
        if not isinstance(rack.get('devs'), list) or not isinstance(rack.get('conns'), list):
            reject('rack_shape_invalid')
        used = 0
        for order, device in enumerate(rack['devs']):
            did = original_id('devices', device)
            duuid = ident('devices', did)
            used += integer(device.get('u'), 1, 1000, 'device_size_invalid')
            budget = number(device.get('poeBudget'), 999999, 'poe_budget_invalid')
            rows['inventory_device'].append({'id': duuid, 'customer_id': customer, 'rack_id': rack_uuid,
                'room_id': None, 'kind': 'rackEquipment', 'name': text(device.get('name'), 'device_name_invalid', 100, True),
                'size_u': device['u'], 'sort_order': order, 'poe_budget': budget,
                'properties': properties(device, {'id', 'name', 'u', 'ports', 'poeBudget'})})
            entities['devices'].append({'originalId': did, 'id': duuid, 'customerId': customer, 'rackId': rack_uuid})
            device_info[did] = {'id': duuid, 'customer': customer, 'rack': rid}
            if not isinstance(device.get('ports'), list):
                reject('device_shape_invalid')
            if any(key in device for key in ('groups', 'portGroups')):
                # This v0.8 restore understands port-carried group identities,
                # not a second, potentially contradictory group definition.
                reject('group_definition_unsupported')
            groups, used_gn = {}, set()
            for porder, port in enumerate(device['ports']):
                pid = original_id('ports', port)
                ptype = enum(port.get('type'), TYPES, 'port_type_invalid')
                family = 'rj45' if ptype == 'rj45_poe' else ptype
                group_original = port.get('groupId')
                if group_original is not None:
                    text(group_original, 'group_id_invalid', required=True)
                group_key = ('explicit', group_original) if group_original is not None else ('derived', family)
                gname = text(port.get('groupName', ''), 'group_name_invalid')
                gprefix = text(port.get('groupPrefix', ''), 'group_prefix_invalid')
                if group_key not in groups:
                    gid = ident('portGroups', did, *group_key)
                    groups[group_key] = (gid, family, gname, gprefix)
                    rows['inventory_port_group'].append({'id': gid, 'customer_id': customer, 'device_id': duuid,
                        'type': family, 'name': gname, 'prefix': gprefix, 'sort_order': len(groups)-1})
                    entities['portGroups'].append({'id': gid, 'deviceId': duuid, 'type': family, 'originalId': group_original})
                gid, gfamily, prior_name, prior_prefix = groups[group_key]
                if (family, gname, gprefix) != (gfamily, prior_name, prior_prefix):
                    reject('group_ambiguous')
                gn = integer(port.get('gn'), 1, 2147483647, 'port_number_invalid')
                if (gid, gn) in used_gn:
                    reject('group_ambiguous')
                used_gn.add((gid, gn))
                status = enum(port.get('status', 'free'), {'free', 'reserved', 'disabled', 'faulty'}, 'port_status_invalid')
                face = enum(port.get('rackclickFace', 'auto'), {'auto', 'front', 'rear'}, 'port_face_invalid')
                role = enum(port.get('rackclickPowerRole', 'unspecified'), {'unspecified', 'inlet', 'outlet'}, 'power_role_invalid')
                # RC9 irPoeEnabled: a legacy rj45_poe port enables PoE unless
                # explicitly disabled; ordinary rj45 requires explicit true.
                poe = port.get('poe', ptype == 'rj45_poe')
                if type(poe) is not bool or (poe and family != 'rj45') or (ptype != 'power' and role != 'unspecified'):
                    reject('port_power_invalid')
                puuid = ident('ports', pid)
                rows['inventory_port'].append({'id': puuid, 'customer_id': customer, 'device_id': duuid, 'group_id': gid,
                    'type': ptype, 'gn': gn, 'sort_order': porder, 'label': text(port.get('label', ''), 'port_label_invalid', 100),
                    'status': status, 'poe': poe, 'watts': number(port.get('watts'), 90, 'watts_invalid'),
                    'color': color(port.get('portColor')), 'face': face, 'power_role': role,
                    'properties': properties(port, {'id', 'type', 'gn', 'label', 'status', 'poe', 'watts', 'portColor',
                        'rackclickFace', 'rackclickPowerRole', 'groupId', 'groupName', 'groupPrefix'})})
                entities['ports'].append({'originalId': pid, 'id': puuid, 'customerId': customer, 'deviceId': duuid, 'groupId': gid})
                port_info[pid] = {'id': puuid, 'device': did, 'customer': customer, 'rack': rid, 'type': ptype,
                    'status': status, 'role': role, 'poe': poe, 'watts': port.get('watts')}
            if budget is not None and sum(p['watts'] or 0 for p in port_info.values() if p['device'] == did and p['poe']) > budget:
                reject('poe_budget_exceeded')
        if used > size:
            reject('rack_capacity_exceeded')
        all_connections.extend((c, rid) for c in rack['conns'])
    if project.get('rackclickLocations', rack_locations) != rack_locations:
        reject('hierarchy_metadata_mismatch')
    all_connections.extend((c, None) for c in project['crossConns'])
    occupied = set()
    for connection, containing_rack in all_connections:
        cid = original_id('connections', connection)
        try:
            first, second = port_info[connection['fp']], port_info[connection['tp']]
        except (KeyError, TypeError):
            reject('connection_dangling')
        if connection.get('fd') != first['device'] or connection.get('td') != second['device']:
            reject('connection_owner_mismatch')
        if first['customer'] != second['customer']:
            reject('connection_cross_customer')
        if first['id'] == second['id'] or first['id'] in occupied or second['id'] in occupied:
            reject('connection_occupied')
        if containing_rack is not None and (first['rack'] != containing_rack or second['rack'] != containing_rack):
            reject('connection_rack_mismatch')
        for key, endpoint in [('rackFrom', first), ('rackTo', second)]:
            if key in connection and connection[key] != endpoint['rack']:
                reject('connection_rack_mismatch')
        if containing_rack is None and first['rack'] == second['rack']:
            reject('cross_connection_not_cross_rack')
        if any(p['status'] in ('disabled', 'faulty') for p in (first, second)):
            reject('connection_port_blocked')
        if ((first['type'] == 'power') != (second['type'] == 'power') or
            (first['type'] == 'power' and first['role'] != 'unspecified' and first['role'] == second['role'])):
            reject('connection_incompatible')
        occupied.update((first['id'], second['id']))
        cuuid = ident('connections', cid)
        rows['inventory_connection'].append({'id': cuuid, 'customer_id': first['customer'],
            'note': text(connection.get('note', ''), 'connection_note_invalid', 2000), 'color': color(connection.get('color')),
            'patch': enum(connection.get('patchStatus', 'none'), {'none', 'planned', 'progress', 'done', 'tested'}, 'patch_invalid'),
            'properties': properties(connection, {'id', 'fd', 'td', 'fp', 'tp', 'note', 'color', 'patchStatus', 'rackFrom', 'rackTo'})})
        rows['inventory_connection_endpoint'].extend({'customer_id': first['customer'], 'connection_id': cuuid,
            'ordinal': i, 'port_id': p['id']} for i, p in enumerate((first, second)))
        entities['connections'].append({'originalId': cid, 'id': cuuid, 'customerId': first['customer'],
            'fromPortId': first['id'], 'toPortId': second['id']})
    counts = {key: len(value) for key, value in entities.items()}
    counts.update(localConnections=sum(len(r['conns']) for r in project['racks']), crossConnections=len(project['crossConns']))
    return {'raw': raw, 'sourceSha256': hashlib.sha256(raw).hexdigest(), 'houseName': house_name, 'rows': rows,
            'mapping': {'format': 'rackclick-rc9-map-v1', 'entities': entities}, 'counts': counts}


def sql_value(value):
    if value is None:
        return 'NULL'
    if type(value) is bool:
        return 'TRUE' if value else 'FALSE'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return sql_value(json.dumps(value, ensure_ascii=False, allow_nan=False)) + '::jsonb'
    # Standard_conforming_strings is explicitly set for this connection.
    return "'" + str(value).replace("'", "''") + "'"


def restore(lab, database, source, actorID):
    """Restore atomically into an empty owned Lab database; return redacted report."""
    private_root = (Path(__file__).resolve().parents[2] / '.local/labs').resolve()
    directory = Path(database.directory).resolve()
    if not directory.is_relative_to(private_root) or directory != (Path(lab.directory) / database.name).resolve():
        reject('laboratory_required')
    try:
        actor = str(uuid.UUID(str(actorID)))
    except ValueError:
        reject('actor_invalid')
    plan = analyze(source)
    if lab.sql(database, 'SELECT (SELECT count(*) FROM customer)', sensitive=True) != '0':
        reject('restore_destination_not_empty')
    archive = directory / ('rc9-restore-' + plan['sourceSha256'][:12] + '-' + uuid.uuid4().hex[:8])
    archive.mkdir(exist_ok=False)
    (archive / 'original.json').write_bytes(plan['raw'])
    mapping = plan['mapping'] | {'sourceSha256': plan['sourceSha256']}
    mapping_path = archive / 'mapping.json'
    mapping_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')
    counts = plan['counts']
    report = {'format': 'rackclick-rc9-restore-v1', 'sourceSha256': plan['sourceSha256'], 'counts': counts,
              'mappingPath': str(mapping_path), 'committed': False}
    (archive / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    # Fixed identifiers only; source values are always SQL literals. All writes,
    # provenance and audit run in one psql connection and transaction.
    statements = ['BEGIN;', 'SET LOCAL standard_conforming_strings=on;',
        'LOCK TABLE systemhaus,app_user,user_group,user_group_member,permission_grant,' + ','.join(TABLES) + ' IN EXCLUSIVE MODE;',
        "DO $$ BEGIN IF (SELECT count(*) FROM systemhaus)<>1 OR EXISTS(SELECT 1 FROM customer) THEN RAISE EXCEPTION 'restore_destination_not_empty'; END IF;",
        'IF ' + ' OR '.join(f'EXISTS(SELECT 1 FROM {table})' for table in TABLES[1:]) + " THEN RAISE EXCEPTION 'restore_destination_not_empty'; END IF;",
        f"IF NOT EXISTS(SELECT 1 FROM app_user WHERE id={sql_value(actor)}::uuid AND active) THEN RAISE EXCEPTION 'restore_actor_invalid'; END IF;",
        f"IF NOT EXISTS(SELECT 1 FROM user_group_member m JOIN permission_grant g ON g.systemhaus_id=m.systemhaus_id AND g.user_group_id=m.group_id WHERE m.user_id={sql_value(actor)}::uuid AND g.capability='security.manage' AND g.customer_id IS NULL AND g.customer_group_id IS NULL) THEN RAISE EXCEPTION 'restore_actor_forbidden'; END IF; END $$;",
        'CREATE SCHEMA laboratory_restore;',
        'CREATE TABLE laboratory_restore.rc9_provenance(source_sha256 text PRIMARY KEY,counts jsonb NOT NULL,actor_id uuid NOT NULL REFERENCES app_user(id),restored_at timestamptz NOT NULL DEFAULT now());']
    for table, records in plan['rows'].items():
        if not records:
            continue
        columns = list(records[0]) + ['systemhaus_id']
        values = ["(" + ','.join(sql_value(row[k]) for k in columns[:-1]) + ',(SELECT id FROM systemhaus))' for row in records]
        statements.append(f"INSERT INTO {table}({','.join(columns)}) VALUES " + ','.join(values) + ';')
    request_id = str(uuid.uuid4())
    statements.extend([
        f"UPDATE systemhaus SET name={sql_value(plan['houseName'])},revision=revision+1;",
        f"INSERT INTO laboratory_restore.rc9_provenance(source_sha256,counts,actor_id) VALUES({sql_value(plan['sourceSha256'])},{sql_value(counts)},{sql_value(actor)});",
        f"INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json) SELECT gen_random_uuid(),id,{sql_value(actor)},{sql_value(request_id)},'laboratory.rc9.restore',id,NULL,{sql_value({'sourceSha256': plan['sourceSha256'], 'counts': counts})} FROM systemhaus;",
        'SET CONSTRAINTS ALL IMMEDIATE;', 'COMMIT;'])
    try:
        lab.sql(database, '\n'.join(statements), sensitive=True)
    except Exception:
        # Raw PostgreSQL errors are retained only by lab.sql in its private log.
        reject('restore_transaction_rejected')
    report['committed'] = True
    (archive / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
