"""Deterministic, inventory-only plan for 50 NEW RackClick laboratory customers.

This program does not connect to a server, create a database, assign an existing
UUID, generate a credential or install a profile. Commands and returned server
identities belong to the separate loader. Every optional/unknown physical fact
stays in the approved profile definition, rather than being inferred here.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
FORMAT = 'RackClickDemo50Plan-v1'
DEFAULT_SEED = 'rackclick-demo50-20261102-v1'
EXPECTED_CATALOGUE = 868
BUSINESS_LINK_NOTE = 'Enlace de laboratorio entre edificios del campus sintético; no define circuitoWAN ni módulos/transceptores instalados'
ROOM_KINDS = {'wall', 'pole', 'din', 'floor'}
KNOWN_KINDS = ROOM_KINDS | {'rack', 'desktop', 'shelf', 'rackContainer', 'sharedU', 'vertical0U'}
SCENARIOS = (
    ('office', 10, 'Oficina y comercio'),
    ('medium', 10, 'Empresa mediana'),
    ('multisite', 8, 'Empresa multisede'),
    ('education', 6, 'Centro educativo'),
    ('industrial', 6, 'Entorno industrial'),
    ('datacenter', 6, 'Centro de datos'),
    ('mixed', 4, 'Laboratorio y servicios mixtos'),
)
NAMES = (
    'Papelería El Roble', 'Büro Linden', 'Atelier Lumière', 'Café Horizonte',
    'Librería La Brújula', 'Praxis Sonnenweg', 'Boutique Mariposa', 'Taller Norte',
    'Mercado Las Fuentes', 'Agencia Cobalto', 'Ingeniería Altura', 'Druckhaus Wald',
    'Servicios Río Claro', 'Logística Andén', 'Consultoría Ámbar', 'Clínica del Alba',
    'Métropole Design', 'Metalbau Kiefer', 'Distribución Vela', 'Textil Azahar',
    'Grupo Camino', 'Handel Brücken', 'Red Costa Azul', 'Voyages Étoile',
    'Cooperativa Laurel', 'Grupo Ferrocarril', 'Servicios Bahía', 'Nordlicht Filialen',
    'Colegio Las Acacias', 'Schule am Park', 'École des Étoiles', 'Instituto Horizonte',
    'Campus del Río', 'Formación Pórtico', 'Automatización Prado', 'Werke Tannen',
    'Manufactura Cobre', 'Agroindustria Olivar', 'Atelier Industriel', 'Control Delta',
    'Datos Aurora', 'Rechenzentrum West', 'Centre de données Clair', 'Nube Cedro',
    'Infraestructura Órbita', 'Archivo Digital Faro', 'Laboratorio Mosaico',
    'Lab Netzwerk', 'Laboratoire Arc', 'Servicios Mixtos Prisma',
)


def definition_digest(value: dict) -> str:
    """Identical canonical definition bytes to the existing hardware contract."""
    raw = (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')) + '\n').encode('ascii')
    return hashlib.sha256(raw).hexdigest()


def plan_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def load_definitions(repo: Path = ROOT) -> list[dict]:
    """Reuse the reviewed authoring chain, including the separate USP revision.

    The existing authoring reader validates its pinned source formats/counts.
    It performs no PostgreSQL, HTTP, build or installation on import/call.
    Refuse a previously loaded reader belonging to another checkout.
    """
    repo = Path(repo).resolve(strict=True)
    tests = repo / 'development/server/tests'
    name = 'test_hardware_selected506l'
    prior = sys.modules.get(name)
    if prior is not None and Path(prior.__file__).resolve().parents[3] != repo:
        raise ValueError('authoring_reader_from_another_checkout')
    sys.path.insert(0, str(tests))
    try:
        module = importlib.import_module(name)
        if Path(module.ROOT).resolve() != repo:
            raise ValueError('authoring_reader_from_another_checkout')
        current, baseline, receiver, pins = module.authoring()
        for relative, digest in pins.items():
            source = repo / relative
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
                raise ValueError('authoring_source_pin_mismatch')
    finally:
        sys.path.pop(0)
    definitions = deepcopy(baseline + current + [receiver])
    _validate_definitions(definitions)
    return sorted(definitions, key=lambda row: (row['key'], row['revision']))


def _validate_definitions(definitions: list[dict]) -> None:
    pairs = [(row['key'], row['revision']) for row in definitions]
    if len(pairs) != len(set(pairs)):
        raise ValueError('catalogue_duplicate_profile_revision')
    if len(pairs) != EXPECTED_CATALOGUE:
        raise ValueError('catalogue_count_not_868')
    if sum(bool(row['identity']['manufacturer']) for row in definitions) != 862:
        raise ValueError('catalogue_commercial_revision_count_invalid')
    for row in definitions:
        if row['kind'] not in KNOWN_KINDS:
            raise ValueError('unsupported_mount_kind')
        if not isinstance(row['rackUnits'], int) or not 0 <= row['rackUnits'] <= 60:
            raise ValueError('unsupported_mount_units')
        if row['kind'] == 'rackContainer' and not 1 <= row['mounting'].get('capacityU', 0) <= 1000:
            raise ValueError('rack_container_capacity_invalid')
        group_keys = [group['key'] for group in row['groups']]
        if len(group_keys) != len(set(group_keys)):
            raise ValueError('profile_group_key_duplicate')
        for group in row['groups']:
            if not isinstance(group['count'], int) or not 1 <= group['count'] <= 512:
                raise ValueError('materialized_group_count_invalid')
            if group['type'] == 'power_dc':
                if group.get('powerRole') not in {'inlet', 'outlet'} or group.get('powerSystem') not in {'dc', 'usb-pd', 'unifi-smartpower'}:
                    raise ValueError('dc_role_or_system_invalid')


def _tie(seed: str, *parts: str) -> str:
    return hashlib.sha256(('\0'.join((seed, *parts))).encode('utf-8')).hexdigest()


def _shelf(row: dict, definitions: list[dict]) -> tuple[dict, dict]:
    choices = [(support, slot) for support in definitions if support['kind'] == 'shelf'
               for slot in support['slots'] if all(row['dimensionsMm'][axis] is not None
                   and row['dimensionsMm'][axis] <= slot['dimensionsMm'][axis]
                   for axis in ('width', 'height', 'depth'))]
    if not choices:
        raise ValueError('approved_shelf_fit_unavailable')
    return min(choices, key=lambda item: (item[0]['rackUnits'], item[0]['key'], item[0]['revision'], item[1]['key']))


def _placement(row: dict, definitions: list[dict]) -> tuple[int, dict | None]:
    if row['kind'] in ROOM_KINDS or row['kind'] == 'rackContainer':
        return 0, None
    if row['kind'] == 'desktop':
        support, slot = _shelf(row, definitions)
        return support['rackUnits'], {'profileKey': support['key'], 'profileVersion': support['revision'], 'slotKey': slot['key']}
    if row['kind'] == 'sharedU':
        allowed = row['mounting'].get('parentProfileKeys', [])
        choices = [support for support in definitions if support['kind'] == 'rack' and support['rackUnits'] > 0
                   and (not allowed or support['key'] in allowed)]
        if not choices:
            raise ValueError('shared_u_parent_unavailable')
        # The existing synthetic switch is suitable as a contract-level parent;
        # no mechanical/electrical compatibility beyond the contract is claimed.
        support = next((support for support in choices if support['key'] == 'switch-24'),
                       min(choices, key=lambda item: (item['rackUnits'], item['key'], item['revision'])))
        return support['rackUnits'], {'profileKey': support['key'], 'profileVersion': support['revision'], 'slotKey': 'shared'}
    return row['rackUnits'], None


def _category(row: dict) -> str:
    text = ' '.join(str(row['identity'].get(k) or '') for k in ('manufacturer', 'family', 'model')).lower()
    if row['kind'] in {'din', 'wall', 'pole', 'floor'}:
        return 'industrial' if row['kind'] == 'din' else 'edge'
    if row['kind'] in {'rackContainer', 'sharedU', 'vertical0U'} or not row['groups']:
        return 'infrastructure'
    if any(word in text for word in ('nas', 'synology', 'qnap', 'storage', 'netapp', 'dell power', 'proliant')):
        return 'storage'
    if any(group['type'] in {'qsfp', 'qsfpdd', 'sfpdd', 'cfp2', 'sas'} for group in row['groups']) or row['rackUnits'] >= 5:
        return 'core'
    return 'edge'


def _candidate_scenarios(category: str) -> set[str]:
    return {
        'industrial': {'industrial'},
        'infrastructure': {'medium', 'multisite', 'industrial', 'datacenter', 'mixed'},
        'storage': {'medium', 'multisite', 'datacenter', 'mixed'},
        'core': {'medium', 'education', 'datacenter', 'mixed'},
        'edge': {'office', 'medium', 'multisite', 'education', 'mixed'},
    }[category]


def _customer(index: int, scenario: str, label: str) -> dict:
    key = f'c{index:02}'
    language = ('es', 'de', 'en')[(index-1) % 3]
    site_count = (2 + index % 2) if scenario == 'multisite' else 2 if scenario == 'mixed' else 1
    sites, business_rooms = [], []
    for site_index in range(1, site_count+1):
        site_key = f'{key}.s{site_index:02}'
        building_count = 2 if scenario in {'medium', 'education', 'industrial'} else 1
        buildings = []
        for building_index in range(1, building_count+1):
            building_key = f'{site_key}.b{building_index:02}'
            technical = {'key': building_key+'.technical', 'name': f'Sala técnica {site_index}.{building_index}', 'purpose': 'infrastructure'}
            workspace = {'key': building_key+'.work', 'name': f'Área de trabajo {site_index}.{building_index}', 'purpose': 'workplace'}
            business_rooms.append((technical, workspace))
            buildings.append({'key': building_key, 'name': f'Edificio {building_index}', 'rooms': [technical, workspace]})
        sites.append({'key': site_key, 'name': f'Sede {site_index}', 'buildings': buildings})
    # Dedicated, explicitly marked catalogue room avoids pretending every model
    # is necessary for this customer's representative business infrastructure.
    showroom = {'key': f'{key}.catalogue', 'name': 'Muestras de catálogo · QA', 'purpose': 'catalogue-showcase'}
    sites[0]['buildings'][0]['rooms'].append(showroom)
    room_objects = [
        {'key': f'{key}.dose01', 'kind': 'dose', 'name': 'Dose · puesto 01', 'roomKey': business_rooms[0][1]['key'],
         'portGroups': [{'type': 'rj45', 'name': 'Tomas RJ45 de sala', 'prefix': 'D ', 'count': 2}],
         'note': 'Dos tomas sintéticas explícitas; no implica continuidad interna oculta.'},
        {'key': f'{key}.endpoint01', 'kind': 'endDevice', 'name': 'Terminal · puesto 01', 'roomKey': business_rooms[0][1]['key'],
         'portGroups': [{'type': 'rj45', 'name': 'LAN terminal', 'prefix': 'LAN ', 'count': 1}],
         'note': 'Terminal de demostración genérico; sin fabricante ni circuitos inferidos.'},
    ]
    return {'key': key, 'name': f'{index:02} · {NAMES[index-1]} · Sintético', 'scenario': scenario,
            'scenarioLabel': label, 'language': language, 'origin': 'synthetic', 'sites': sites,
            'businessRoomKey': business_rooms[0][0]['key'], 'catalogueRoomKey': showroom['key'],
            'racks': [], 'assignments': [], 'roomObjects': room_objects}


def _add_business_infrastructure(customer: dict) -> None:
    """Populate every building, without changing any catalogue assignment/key."""
    devices = []
    capacity = {'office': 6, 'medium': 12, 'multisite': 12, 'education': 12,
                'industrial': 12, 'datacenter': 24, 'mixed': 6}[customer['scenario']]
    for site in customer['sites']:
        for building in site['buildings']:
            room = next(room for room in building['rooms'] if room['purpose'] == 'infrastructure')
            rack_key, device_key = building['key']+'.businessrack', building['key']+'.businessswitch'
            customer['racks'].append({'key': rack_key, 'name': 'Rack de distribución · '+building['name'],
                'roomKey': room['key'], 'sizeU': capacity, 'reservedUnits': 1, 'verticalSides': [],
                'catalogueShowcase': False,
                'properties': {'physicalDimensionsMm': {'width': 800, 'height': round(capacity*44.45+120, 2), 'depth': 1200},
                               'synthetic': True, 'note': 'Armario genérico sintético; no representa un SKU comercial.'}})
            devices.append({'key': device_key, 'profileKey': 'switch-24', 'profileVersion': 'hw-reference-v1',
                'rackKey': rack_key, 'roomKey': room['key'], 'name': 'Switch de distribución · '+building['name'], 'mountKind': 'rack'})
    customer['businessDevices'] = devices
    customer['interBuildingLinks'] = [{'fromDeviceKey': first['key'], 'toDeviceKey': second['key'], 'note': BUSINESS_LINK_NOTE}
                                      for first, second in zip(devices, devices[1:])]


def build_plan(definitions: list[dict], seed: str = DEFAULT_SEED) -> dict:
    _validate_definitions(definitions)
    if not isinstance(seed, str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,80}', seed):
        raise ValueError('seed_invalid')
    definitions = sorted(deepcopy(definitions), key=lambda item: (item['key'], item['revision']))
    customers = []
    for scenario, count, label in SCENARIOS:
        for _ in range(count):
            customers.append(_customer(len(customers)+1, scenario, label))
    catalogue = [{'profileKey': row['key'], 'profileVersion': row['revision'],
                  'definitionSha256': definition_digest(row), 'mountKind': row['kind'],
                  'identity': deepcopy(row['identity']), 'groupCount': len(row['groups']),
                  'portCount': sum(group['count'] for group in row['groups'])}
                 for row in definitions]
    loads = Counter()
    for row in definitions:
        pool = [customer for customer in customers if customer['scenario'] in _candidate_scenarios(_category(row))]
        customer = min(pool, key=lambda value: (loads[value['key']], _tie(seed, row['key'], row['revision'], value['key'])))
        loads[customer['key']] += 1
        units, support = _placement(row, definitions)
        item = {'key': customer['key']+'.model-'+_tie('profile', row['key'], row['revision'])[:20],
                'profileKey': row['key'], 'profileVersion': row['revision'],
                'name': str(row['identity']['model'] or row['key'])[:90], 'roomKey': customer['catalogueRoomKey'],
                'mountKind': row['kind'], 'catalogueShowcase': True,
                'reservedUnitsIncludingSupport': units,
                'connectionApplicability': 'required' if row['groups'] else 'not_applicable',
                'connectionReason': None if row['groups'] else 'El perfil aprobado no materializa puertos; creación/montaje sin cables inventados.'}
        if support:
            item['support'] = support
        if row['kind'] not in ROOM_KINDS | {'rackContainer'}:
            minimum = 42 if row['kind'] == 'vertical0U' else 0
            racks = [rack for rack in customer['racks'] if rack['roomKey'] == item['roomKey']
                     and rack['sizeU'] >= minimum and rack['reservedUnits']+units <= rack['sizeU']-6
                     and (row['kind'] != 'vertical0U' or not rack['verticalSides'])]
            if not racks:
                number = len(customer['racks'])+1
                capacity = 24 if customer['scenario'] == 'office' else 42
                capacity = max(capacity, minimum, units+6)
                rack = {'key': f"{customer['key']}.rack{number:02}", 'name': f'Catálogo · rack {number:02}',
                        'roomKey': item['roomKey'], 'sizeU': capacity, 'reservedUnits': 0,
                        'verticalSides': [], 'catalogueShowcase': True,
                        'properties': {'physicalDimensionsMm': {'width': 800, 'height': round(capacity*44.45+120, 2), 'depth': 1200},
                                       'synthetic': True, 'note': 'Armario genérico sintético; no representa un SKU comercial.'}}
                customer['racks'].append(rack)
            else:
                rack = racks[0]
            item['rackKey'] = rack['key']; rack['reservedUnits'] += units
            if row['kind'] == 'vertical0U':
                item['mountSlotKey'] = 'vertical-left'; rack['verticalSides'].append('vertical-left')
        customer['assignments'].append(item)
    for customer in customers:
        _add_business_infrastructure(customer)
    digest = hashlib.sha256(plan_bytes(catalogue)).hexdigest()
    result = {'format': FORMAT, 'schemaVersion': 43, 'seed': seed, 'origin': 'synthetic',
              'catalogCount': len(catalogue), 'catalogDigest': digest, 'catalog': catalogue,
              'customers': customers, 'securityIncluded': False, 'productionDefault': False,
              'notes': ['UUID de recursos se toman sólo de respuestas confirmadas del servidor.',
                        'Cada pareja perfil/revisión tiene una asignación primaria; soportes/peers pueden añadir instancias.',
                        'Muestras de catálogo y área de negocio están separadas explícitamente.',
                        'Las conexiones se planifican por familia/físico/rol/sistema; este archivo no certifica electricidad o protocolos.']}
    validate_plan(result, definitions)
    return result


def validate_plan(plan: dict, definitions: list[dict]) -> None:
    """Validate independent scope/reference/capacity facts, not only a checksum."""
    _validate_definitions(definitions)
    keys = {'format', 'schemaVersion', 'seed', 'origin', 'catalogCount', 'catalogDigest', 'catalog',
            'customers', 'securityIncluded', 'productionDefault', 'notes'}
    if set(plan) != keys or plan['format'] != FORMAT or plan['schemaVersion'] != 43 or plan['origin'] != 'synthetic':
        raise ValueError('plan_contract_invalid')
    if plan['securityIncluded'] is not False or plan['productionDefault'] is not False:
        raise ValueError('plan_security_or_production_scope_invalid')
    if not isinstance(plan['seed'], str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,80}', plan['seed']):
        raise ValueError('seed_invalid')
    pending = [plan]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            if any(str(key).casefold() in {'password', 'passwd', 'token', 'session', 'sessions', 'factor', 'factors',
                                           'csrf', 'credentials', 'connectionstring', 'mfa'} for key in value):
                raise ValueError('plan_contains_security_fields')
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    expected = {(row['key'], row['revision']): row for row in definitions}
    catalogue = plan['catalog']
    if plan['catalogCount'] != 868 or len(catalogue) != 868 or len({(item['profileKey'], item['profileVersion']) for item in catalogue}) != 868:
        raise ValueError('plan_catalogue_count_invalid')
    if plan['catalogDigest'] != hashlib.sha256(plan_bytes(catalogue)).hexdigest():
        raise ValueError('plan_catalogue_digest_invalid')
    for item in catalogue:
        row = expected.get((item['profileKey'], item['profileVersion']))
        if row is None or item['definitionSha256'] != definition_digest(row):
            raise ValueError('plan_catalogue_definition_invalid')
        if item['identity'] != row['identity'] or item['mountKind'] != row['kind'] or item['groupCount'] != len(row['groups']) or item['portCount'] != sum(g['count'] for g in row['groups']):
            raise ValueError('plan_catalogue_summary_invalid')
    customers = plan['customers']
    if len(customers) != 50 or {c['key'] for c in customers} != {f'c{i:02}' for i in range(1, 51)}:
        raise ValueError('plan_customer_count_invalid')
    if Counter(c['scenario'] for c in customers) != Counter({scenario: count for scenario, count, _ in SCENARIOS}):
        raise ValueError('plan_scenario_distribution_invalid')
    if len({c['name'] for c in customers}) != 50 or {c['language'] for c in customers} != {'es', 'de', 'en'}:
        raise ValueError('plan_customer_names_or_languages_invalid')
    seen, logical = Counter(), set()
    for customer in customers:
        if not customer['assignments'] or customer['origin'] != 'synthetic':
            raise ValueError('plan_customer_without_profile')
        rooms = {room['key'] for site in customer['sites'] for building in site['buildings'] for room in building['rooms']}
        if customer['businessRoomKey'] not in rooms or customer['catalogueRoomKey'] not in rooms or customer['businessRoomKey'] == customer['catalogueRoomKey']:
            raise ValueError('plan_business_or_catalogue_room_invalid')
        if customer['scenario'] in {'multisite', 'mixed'} and len(customer['sites']) < 2:
            raise ValueError('plan_multisite_requires_multiple_sites')
        if customer['scenario'] in {'medium', 'education', 'industrial'} and any(len(site['buildings']) < 2 for site in customer['sites']):
            raise ValueError('plan_scenario_buildings_invalid')
        racks = {rack['key']: rack for rack in customer['racks']}
        business = customer.get('businessDevices')
        links = customer.get('interBuildingLinks')
        if not isinstance(business, list) or not isinstance(links, list):
            raise ValueError('plan_business_infrastructure_missing')
        for value in [customer, *customer['sites'], *(building for site in customer['sites'] for building in site['buildings']),
                      *(room for site in customer['sites'] for building in site['buildings'] for room in building['rooms']), *customer['racks'], *customer['assignments'], *customer['roomObjects'], *business]:
            if value['key'] in logical:
                raise ValueError('plan_logical_key_duplicate')
            logical.add(value['key'])
        reserved = Counter()
        for item in customer['assignments']:
            pair = item['profileKey'], item['profileVersion']; row = expected.get(pair)
            if row is None:
                raise ValueError('plan_unknown_profile_revision')
            seen[pair] += 1
            if item['roomKey'] not in rooms or item['mountKind'] != row['kind']:
                raise ValueError('plan_room_or_mount_reference_invalid')
            units, support = _placement(row, definitions)
            if item['reservedUnitsIncludingSupport'] != units or item.get('support') != support:
                raise ValueError('plan_support_or_capacity_invalid')
            if item['connectionApplicability'] != ('required' if row['groups'] else 'not_applicable'):
                raise ValueError('plan_connection_applicability_invalid')
            if not row['groups'] and not item['connectionReason']:
                raise ValueError('plan_connection_na_reason_required')
            room_target = row['kind'] in ROOM_KINDS | {'rackContainer'}
            if room_target and 'rackKey' in item:
                raise ValueError('plan_room_mount_has_rack')
            if not room_target:
                rack = racks.get(item.get('rackKey'))
                if rack is None or rack['roomKey'] != item['roomKey']:
                    raise ValueError('plan_rack_reference_invalid')
                reserved[rack['key']] += units
                if row['kind'] == 'vertical0U' and (item.get('mountSlotKey') != 'vertical-left'
                        or row['dimensionsMm']['height'] > rack['sizeU']*44.45):
                    raise ValueError('plan_vertical_slot_or_height_invalid')
        buildings = [building for site in customer['sites'] for building in site['buildings']]
        expected_keys = [building['key']+'.businessswitch' for building in buildings]
        if [item['key'] for item in business] != expected_keys:
            raise ValueError('plan_building_without_business_switch')
        for item, building in zip(business, buildings):
            switch = expected.get((item['profileKey'], item['profileVersion']))
            if set(item) != {'key','profileKey','profileVersion','rackKey','roomKey','name','mountKind'} or switch is None or (item['profileKey'],item['profileVersion']) != ('switch-24','hw-reference-v1') or item['mountKind'] != 'rack' or switch['rackUnits'] != 1 or sum(g['count'] for g in switch['groups'] if g['type']=='sfp') < 2:
                raise ValueError('plan_business_switch_profile_invalid')
            own_rooms = {room['key'] for room in building['rooms'] if room['purpose']=='infrastructure'}
            rack = racks.get(item['rackKey'])
            if item['roomKey'] not in own_rooms or rack is None or rack['key'] != building['key']+'.businessrack' or rack['roomKey'] != item['roomKey'] or rack['catalogueShowcase'] is not False:
                raise ValueError('plan_business_building_reference_invalid')
            reserved[rack['key']] += switch['rackUnits']
        expected_links = [{'fromDeviceKey': first, 'toDeviceKey': second, 'note': BUSINESS_LINK_NOTE}
                          for first, second in zip(expected_keys, expected_keys[1:])]
        if links != expected_links:
            raise ValueError('plan_interbuilding_chain_invalid')
        for rack in racks.values():
            margin = 6 if rack['catalogueShowcase'] else 0
            if rack['roomKey'] not in rooms or not 1 <= rack['sizeU'] <= 60 or rack['reservedUnits'] != reserved[rack['key']] or rack['reservedUnits'] > rack['sizeU']-margin:
                raise ValueError('plan_rack_capacity_invalid')
            if rack['properties'] != {'physicalDimensionsMm': {'width': 800, 'height': round(rack['sizeU']*44.45+120, 2), 'depth': 1200},
                                      'synthetic': True, 'note': 'Armario genérico sintético; no representa un SKU comercial.'}:
                raise ValueError('plan_synthetic_rack_dimensions_invalid')
        for item in customer['roomObjects']:
            if item['roomKey'] not in rooms or item['kind'] not in {'dose', 'endDevice'}:
                raise ValueError('plan_room_object_invalid')
    if set(seen) != set(expected) or any(count != 1 for count in seen.values()):
        raise ValueError('plan_profile_coverage_invalid')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--seed', default=DEFAULT_SEED)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    definitions = load_definitions(args.repo)
    plan = build_plan(definitions, args.seed); raw = plan_bytes(plan)
    if args.check:
        current = args.output.read_bytes()
        value = json.loads(current); validate_plan(value, definitions)
        if current != raw:
            raise ValueError('plan_not_reproducible_for_requested_seed')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('xb') as stream:
            stream.write(raw)
    print(json.dumps({'result': 'PLAN_CHECKED' if args.check else 'PLAN_CREATED', 'customers': 50,
                      'catalogueProfiles': plan['catalogCount'], 'catalogueDigest': plan['catalogDigest'],
                      'planSha256': hashlib.sha256(raw).hexdigest(), 'databaseAccessed': False,
                      'credentialsGenerated': False}))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, FileExistsError, FileNotFoundError) as error:
        print(json.dumps({'result': 'PLAN_REJECTED', 'code': str(error) if isinstance(error, ValueError) else type(error).__name__}))
        raise SystemExit(1)
