"""Compile reviewed several physical families of usable profiles drawn from the fixed 506-model selection.

Reuses the reviewed catalogue engine without rewriting historical sources.
This compiler publishes only the accepted, individually authored configurations from its family plan.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).absolute().parents[1]
spec = importlib.util.spec_from_file_location('selected506k_private_engine', ROOT/'tools/hardware_family_v2.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
b = engine.base
c, g = engine.c, engine.g
REVISION = 'selected506k-20261101-v1'
b.REVISION = REVISION
FAMILIES = ('power', 'passive', 'mechanical', 'storage', 'serial')
SOURCES = ['development/hardware/selected506k/'+name+'.json' for name in FAMILIES]
SELECTION = 'development/hardware/selected-models-506.json'
LINKS = 'development/hardware/selected-profile-links.json'
PLAN = 'evidence/s1-20261101/integracion506k/PLAN-FAMILIAS.json'
LOCK = 'development/hardware/catalog-schema41.lock.json'
BASE = 'development/server/database/040-hardware-families.sql'
BASELINE = 'development/server/database/039-selected506j-hardware.sql'
SUPPORT = 'development/hardware/selected506k/support.json'
SERVER = 'development/server/src/RackClick.Server/Selected506KHardwareProfiles.Generated.cs'
FRONTEND = 'development/frontend/src/hardware-selected506k.generated.json'
SQL = 'development/server/database/041-selected506k-hardware.sql'
MANIFEST = 'development/hardware/catalog-selected506k.manifest.json'
TARGETS = 'development/server/src/RackClick.Server/Selected506KHardware.Generated.targets'
TOOL = 'tools/build_hardware_selected506k.py'
SHARED = 'tools/hardware_family_v2.py'
CORE = 'tools/build_hardware_batch50.py'
TRANSITIVE = ['tools/hardware_physical_v3.py', 'tools/hardware_physical_v2.py', 'tools/build_hardware_catalog.py', *['tools/build_hardware_catalog'+str(n)+'.py' for n in range(19, 24)]]
STATE = 'curated_development_not_a_release'
EXPECTED_LOCK_SHA256 = '50b83a47adb0404d88903e1d841b0a5d7e3941a8a65504655ad55430207dc489'
SKUS = {'nb-476a5e2e14826616': 'AP4421A', 'nb-d14bed6bc445f3b0': 'PDUMH15AT', 'nb-23088fe782f499ac': 'AP4422A', 'nb-a30f5454503d7402': 'PDUMH20HVAT', 'nb-2d5dd2ca4dacb1c5': 'AP4423A', 'nb-de900000f3f9295d': 'AP4424A', 'nb-503a26493f9206a4': 'AP4430A', 'nb-aa67f910589a5502': 'AP4431A', 'nb-c7a1f257de229c1c': 'AP4432A', 'nb-624f4c89a65b309a': 'AP4433', 'nb-8575f3e84e37fd0d': 'AP4433A', 'nb-ce5e88c6a9b7562d': 'AP4434A', 'nb-15a85a8a3b05a92f': 'AP6031A', 'raritan-px3-5190r': 'PX3-5190R', 'nb-1b78d3ee187d5923': 'VMR-16HD20-2', 'apc-smt1500rmi2u': 'SMT1500RMI2U', 'eaton-5px1500irt2ug2': '5PX1500IRT2UG2', 'nb-e195af6788f9b56c': 'SMT3000RMI2UC', 'nb-1157b9a10bc8e5f4': 'SMX3000RMLV2U', 'nb-f9fc50287eafd86c': 'SRT5KRMXLT', 'nb-c91a00ac9965db90': 'SMT2200RM2U', 'nb-19ed1459663d3e17': '5PX1500iRT', 'nb-f5d26f8fec76743c': '9PX3000iRT2U', 'nb-d3866e263332a4fc': '9PX3000iRT3U', 'nb-c2814dde21fa98df': 'SNR-UPS-ONRT-1000-S24', 'nb-81391abd9812b183': 'SMART1500LCD', 'nb-07e5ff352f97fad1': 'SMART1500RMXL2UA', 'nb-0ada4f1bb27f261c': 'SMART2200CRMXL', 'nb-d9eff11e7e0c11f7': 'DP24688TGY', 'nb-4b2e4c72b9d36b73': 'DP486X88TGY', 'nb-04f3c36861d3b6f5': 'DP48688TGY', 'nb-70f105515d0bf559': 'DP246X88TGY', 'nb-f060040e382de573': 'DP245E88TGY', 'nb-7ea04d02eec80c94': 'DP485E88TGY', 'startech-cabshelf1u': 'CABSHELF1U', 'nb-edde85c1a3ba283d': '691651ATS.8', 'nb-bdf6ab2dce05aee0': 'FRME1U', 'nb-29ce493b266db9c3': 'FRME2U', 'nb-a6a79509854ba38b': '760193771', 'nb-78fb5e27dc863dbc': '760231464', 'nb-93773a73e59631e4': 'FHD-1UFMT-N', 'nb-9b748f4aeb7c8a2d': '760207274', 'nb-75ff355641be29f1': '760207308', 'nb-682f01a7e3775f50': '760237046', 'nb-7dd2b21e61ad99a0': 'F2-424', 'nb-4de91d17b80dbbff': 'F6-424 Max', 'nb-908a100c3ca29495': '70001743', 'nb-21d28e7d5a06429b': 'ETS16PR', 'nb-b924dbf6777c2eb2': 'ETS32PR', 'nb-a966d159c428b1d4': 'CM8116', 'nb-08b0ee66b1eb36c8': 'CM8148', 'nb-dbdce8efed0e65d8': 'CM7132-2-DAC'}
MOUNTS = {'nb-476a5e2e14826616': ('rack', 1), 'nb-d14bed6bc445f3b0': ('rack', 1), 'nb-23088fe782f499ac': ('rack', 1), 'nb-a30f5454503d7402': ('rack', 1), 'nb-2d5dd2ca4dacb1c5': ('rack', 1), 'nb-de900000f3f9295d': ('rack', 2), 'nb-503a26493f9206a4': ('rack', 1), 'nb-aa67f910589a5502': ('rack', 2), 'nb-c7a1f257de229c1c': ('rack', 2), 'nb-624f4c89a65b309a': ('rack', 1), 'nb-8575f3e84e37fd0d': ('rack', 1), 'nb-ce5e88c6a9b7562d': ('rack', 1), 'nb-15a85a8a3b05a92f': ('rack', 1), 'raritan-px3-5190r': ('rack', 1), 'nb-1b78d3ee187d5923': ('rack', 2), 'apc-smt1500rmi2u': ('rack', 2), 'eaton-5px1500irt2ug2': ('rack', 2), 'nb-e195af6788f9b56c': ('rack', 2), 'nb-1157b9a10bc8e5f4': ('rack', 2), 'nb-f9fc50287eafd86c': ('rack', 3), 'nb-c91a00ac9965db90': ('rack', 2), 'nb-19ed1459663d3e17': ('rack', 2), 'nb-f5d26f8fec76743c': ('rack', 2), 'nb-d3866e263332a4fc': ('rack', 3), 'nb-c2814dde21fa98df': ('rack', 2), 'nb-81391abd9812b183': ('rack', 2), 'nb-07e5ff352f97fad1': ('rack', 2), 'nb-0ada4f1bb27f261c': ('rack', 4), 'nb-d9eff11e7e0c11f7': ('rack', 1), 'nb-4b2e4c72b9d36b73': ('rack', 2), 'nb-04f3c36861d3b6f5': ('rack', 2), 'nb-70f105515d0bf559': ('rack', 1), 'nb-f060040e382de573': ('rack', 1), 'nb-7ea04d02eec80c94': ('rack', 2), 'startech-cabshelf1u': ('rack', 1), 'nb-edde85c1a3ba283d': ('rack', 1), 'nb-bdf6ab2dce05aee0': ('rack', 1), 'nb-29ce493b266db9c3': ('rack', 2), 'nb-a6a79509854ba38b': ('rack', 1), 'nb-78fb5e27dc863dbc': ('rack', 4), 'nb-93773a73e59631e4': ('rack', 1), 'nb-9b748f4aeb7c8a2d': ('rack', 1), 'nb-75ff355641be29f1': ('rack', 2), 'nb-682f01a7e3775f50': ('rack', 1), 'nb-7dd2b21e61ad99a0': ('desktop', 0), 'nb-4de91d17b80dbbff': ('desktop', 0), 'nb-908a100c3ca29495': ('rack', 1), 'nb-21d28e7d5a06429b': ('rack', 1), 'nb-b924dbf6777c2eb2': ('rack', 2), 'nb-a966d159c428b1d4': ('rack', 1), 'nb-08b0ee66b1eb36c8': ('rack', 1), 'nb-dbdce8efed0e65d8': ('rack', 1)}
IDS = tuple(sorted(SKUS))


def validate_model(row):
    return engine.validate_model(row, REVISION)


def server_source(models):
    # The historical Batch50 writer discards continuity. Keep its reviewed
    # constructor shape and roles while emitting the original declared mapping.
    q = lambda value: json.dumps(value, ensure_ascii=True)
    lines = ['// <auto-generated> tools/build_hardware_selected506k.py; do not edit. </auto-generated>',
             'namespace RackClick.Server;', 'using static RackClick.Server.InventoryHardwareProfiles;',
             'internal static class Selected506KHardwareProfiles', '{', '    internal static readonly Registry Catalog = new([']
    for model in models:
        dims = model['dimensionsMm']
        groups = ', '.join('new('+', '.join([q(group['key']), q(group['type']), str(group['count']),
            q(group['face']), q(group['name']), q(group['prefix'])])+') { PowerRole = '+q(group['powerRole'])+(', PhysicalConnector = '+q(group['physicalConnector']) if group.get('physicalConnector') is not None else '')+' }'
            for group in model['groups'])
        slots = ', '.join('new('+', '.join([q(slot['key'])]+[str(slot['dimensionsMm'][key])+'m'
            for key in ('width', 'height', 'depth')])+')' for slot in model['slots'])
        continuity = model['passthrough']
        passthrough = 'new('+', '.join([q(continuity['frontGroup']), q(continuity['rearGroup']),
            str(continuity['count'])])+')' if continuity is not None else 'null'
        args = [q(model['key']), str(model['rackUnits'])]+[str(dims[key])+'m'
            for key in ('width', 'height', 'depth')]+[q(model['color']), '['+groups+']', q(model['revision'])]
        identity = ''.join(', '+key.title()+' = '+q(value) for key, value in model['identity'].items() if value is not None)
        lines.append('        new('+', '.join(args)+') { Kind = '+q(model['kind'])+
            ', DefinitionSha256 = '+q(c.sha(c.canonical(model)))+', Slots = ['+slots+'], Passthrough = '+passthrough+identity+' },')
    return ('\n'.join(lines+['    ]);', '}', ''])).encode('ascii')


def sql_source(models, pins):
    # Reuse literal escaping, identity, roles and sealing. Insert continuity
    # after its two groups and BEFORE the existing immutable-seal statement.
    lines = ['-- Auto-generated selected506k. SQL001-039 and sealed revisions remain unchanged.',
             '-- Declared same-ordinal RJ45 continuity only; tracing is not implemented.']
    for model, pin in zip(models, pins):
        part = [line for line in g.sql_source([model], [pin]).decode('utf-8').splitlines()
                if not line.startswith('--')]
        c.require(part and part[-1].startswith('UPDATE hardware_definition SET sealed=true WHERE '),
                  'selected506k_seal_generation_invalid')
        continuity = model['passthrough']
        if continuity is not None:
            values = [model['key'], model['revision'], continuity['frontGroup'], continuity['rearGroup'], continuity['count']]
            part.insert(len(part)-1, 'INSERT INTO hardware_passthrough (profile_key, revision, front_group_key, rear_group_key, port_count) VALUES ('+
                        ', '.join(map(g.literal, values))+');')
        for group in model['groups']:
            if group.get('physicalConnector') is not None:
                values = [model['key'], model['revision'], group['key'], group['physicalConnector']]
                part.insert(len(part)-1, 'INSERT INTO hardware_connector_template (profile_key, revision, group_key, physical_connector) VALUES ('+
                            ', '.join(map(g.literal, values))+');')
        lines += part
    return ('\n'.join(lines)+'\n').encode('utf-8')


def prior_names(root):
    result = [p.relative_to(root).as_posix() for p in c.path(root, 'development/hardware').glob('catalog-*-v1.json')]
    for folder in ('batch50', 'batch50b', 'batch100', 'batch100b', 'batch100c'):
        result += [p.relative_to(root).as_posix() for p in c.path(root, 'development/hardware/'+folder).glob('*.json')]
    result += ['development/hardware/selected506a/aruba.json', 'development/hardware/selected506a/ubiquiti.json',
               'development/hardware/selected506b/core.json', 'development/hardware/selected506b/access.json',
               'development/hardware/selected506c/firewalls.json', 'development/hardware/selected506c/edge.json',
               'development/hardware/selected506d/core.json', 'development/hardware/selected506d/edge.json',
               'development/hardware/selected506e/core.json', 'development/hardware/selected506e/edge.json',
               'development/hardware/selected506f/core.json', 'development/hardware/selected506f/edge.json',
               'development/hardware/selected506g/core.json', 'development/hardware/selected506g/edge.json',
               'development/hardware/selected506h/aruba.json', 'development/hardware/selected506h/nokia.json',
               'development/hardware/selected506i/enterprise.json', 'development/hardware/selected506i/transport.json',
               'development/hardware/selected506j/passive-panels.json', 'development/hardware/selected506j/access-points.json']
    return sorted(result)


def expected_support(plan):
    value = plan['support']
    return dict(key=value['key'],revision=value['revision'],identity={key:None for key in ('manufacturer','family','model','sku')},
                provenance=dict(kind='own-synthetic',source=PLAN,assets=[]),kind='shelf',rackUnits=value['rackUnits'],
                dimensionsMm=value['dimensionsMm'],color='#46505c',slots=[dict(key='main',dimensionsMm={key:value['slot'][key]
                    for key in ('width','height','depth')})],groups=[],passthrough=None)


def support_models(root):
    data = c.load(c.path(root,SUPPORT).read_bytes())
    b.fields(data,'formatVersion definitions')
    expected = expected_support(c.load(c.path(root,PLAN).read_bytes()))
    c.require(type(data['formatVersion']) is int and data['formatVersion']==1 and data['definitions']==[expected],
              'selected506k_support_invalid')
    c.require(expected['rackUnits']==7 and expected['key']=='shelf-7u-deep' and expected['revision']=='mount-support7u-20261101-v1',
              'selected506k_support_invalid')
    return data['definitions']


def previous_models(root):
    models = []
    for name in prior_names(root):
        data = c.load(c.path(root, name).read_bytes())
        models += data['definitions'] if name.endswith('-v1.json') else [row['definition'] for row in data['models']]
    c.require(len(models) == 752 and sum(bool(model['identity']['manufacturer']) for model in models) == 747,
              'selected506k_baseline_invalid')
    return models


def selected_rows(root, data):
    b.fields(data, 'formatVersion revision models')
    c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
              data['revision'] == REVISION and isinstance(data['models'], list) and len(IDS) > 0 and
              set(MOUNTS) == set(IDS) and len(data['models']) == len(IDS),
              'selected506k_count_invalid')
    selection = c.load(c.path(root, SELECTION).read_bytes())['models']
    chosen = {row['id']: row for row in selection}
    plan = c.load(c.path(root, PLAN).read_bytes())
    c.require(type(plan['formatVersion']) is int and plan['formatVersion'] == 1 and
              plan['revision'] == REVISION and plan['targetSchema'] == 41 and plan['foundationSchema'] == 40 and
              plan['baselineDefinitions'] == 752 and plan['baselineCommercial'] == 747 and
              plan['baselineSchema'] == 39 and plan['models'] == len(IDS) and
              set(plan['physicalTypes']) == set(engine.ALLOWED_TYPES) and
              set(plan['authoring']) == set(FAMILIES) and
              all(isinstance(plan['authoring'][name], list) and plan['authoring'][name] for name in FAMILIES),
              'selected506k_assignment_invalid')
    planned = [item['id'] for name in FAMILIES for item in plan['authoring'][name]]
    c.require(len(planned) == len(set(planned)) == len(IDS) and set(planned) == set(IDS),
              'selected506k_assignment_invalid')
    c.require(len(plan['reservedModels'])==4 and {item['id'] for item in plan['reservedModels']} ==
              {'nb-8311f81875534b26','nb-03c8ee9bbb014c7c','nb-1a5e040822eebdd7','nb-5bb0012c11525238'} and
              set(planned).isdisjoint(item['id'] for item in plan['reservedModels']) and
              plan['plannedCandidates']==len(IDS)+4 and plan['expectedDefinitions']==805 and plan['expectedCommercial']==799,
              'selected506k_reservations_invalid')
    links = c.load(c.path(root, LINKS).read_bytes())
    c.require(len(links['links']) == 7 and
              set(IDS).isdisjoint(row['selectionId'] for row in links['links']),
              'selected506k_previous_model_duplicate')
    c.require(len(chosen) == 506 and set(IDS) <= set(chosen), 'selected506k_selection_invalid')
    rows = [validate_model(row) for row in data['models']]
    c.require(all(group['count'] <= 96 for row in rows for group in row['definition']['groups']),
              'selected506k_runtime_group_limit')
    by_key = {row['definition']['key']: row for row in rows}
    c.require(len(by_key) == len(IDS) and set(by_key) == {'selected-'+identifier for identifier in IDS},
              'selected506k_identity_invalid')
    c.require(len({(row['definition']['identity']['manufacturer'].casefold(),
                    row['definition']['identity']['sku'].casefold()) for row in rows}) == len(IDS),
              'selected506k_duplicate_sku')
    for identifier in IDS:
        definition = by_key['selected-'+identifier]['definition']
        original = chosen[identifier]
        c.require(definition['identity']['manufacturer'] == original['manufacturer'] and
                  definition['identity']['model'] == original['model'] and
                  definition['identity']['sku'] == SKUS[identifier], 'selected506k_model_substitution')
        c.require((definition['kind'], definition['rackUnits']) == MOUNTS[identifier],
                  'selected506k_mount_substitution')
    for family in FAMILIES:
        for item in plan['authoring'][family]:
            model = by_key['selected-'+item['id']]['definition']
            c.require((model['passthrough'] is not None) == (family == 'passive'),
                      'selected506k_family_substitution')
            types = {group['type'] for group in model['groups']}
            c.require((family!='mechanical' or model['groups']==[] and model['slots']==[]) and
                      (family!='passive' or types=={'rj45','idc'}) and
                      (family!='storage' or types=={'rj45'} and sum(group['count'] for group in model['groups'])==2) and
                      (family!='serial' or 'console' in types and types<={'rj45','console','power'}) and
                      (family!='power' or 'power' in types and types<={'rj45','power'}),
                      'selected506k_family_substitution')
    return sorted(rows, key=lambda row: row['definition']['key'])


def compile_catalog(root):
    names = [*SOURCES, SELECTION, LINKS, PLAN, LOCK, BASE, BASELINE, SUPPORT, SHARED, CORE, *TRANSITIVE, TOOL, *prior_names(root)]
    raw = {name: c.path(root, name).read_bytes() for name in names}
    lock = c.load(raw[LOCK])
    c.require(c.sha(raw[LOCK]) == EXPECTED_LOCK_SHA256, 'selected506k_lock_not_reviewed')
    c.require(lock['targetSchema'] == 41 and lock['state'] == STATE and
              lock['sourceSha256'] == {name: c.sha(raw[name]) for name in SOURCES} and
              lock['baseMigrationSha256'] == c.sha(raw[BASE]) and
              lock['baselineMigrationSha256'] == c.sha(raw[BASELINE]) and lock['supportSourceSha256'] == c.sha(raw[SUPPORT]) and
              lock['sharedCompilerSha256'] == c.sha(raw[SHARED]) and lock['baseEngineSha256'] == c.sha(raw[CORE]) and
              lock['transitiveCompilerSha256'] == {name: c.sha(raw[name]) for name in TRANSITIVE} and
              lock['selectionIds'] == sorted(IDS),
              'selected506k_input_changed')
    c.require(lock['baselineSourceSha256'] == {name: c.sha(raw[name]) for name in prior_names(root)} and
              lock['selectionSha256'] == c.sha(raw[SELECTION]) and lock['planSha256'] == c.sha(raw[PLAN]) and
              lock['profileLinksSha256'] == c.sha(raw[LINKS]),
              'selected506k_baseline_changed')
    combined = dict(formatVersion=1, revision=REVISION, models=[])
    plan = c.load(raw[PLAN])
    for family, source in zip(FAMILIES, SOURCES):
        count = len(plan['authoring'][family])
        data = c.load(raw[source])
        b.fields(data, 'formatVersion revision models')
        c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
                  data['revision'] == REVISION and isinstance(data['models'], list) and len(data['models']) == count,
                  'selected506k_source_count_invalid')
        c.require(all(isinstance(row, dict) and isinstance(row.get('definition'), dict) and
                      isinstance(row['definition'].get('key'), str) for row in data['models']) and
                  {row['definition']['key'] for row in data['models']} ==
                  {'selected-'+item['id'] for item in plan['authoring'][family]},
                  'selected506k_source_family_invalid')
        combined['models'] += data['models']
    rows = selected_rows(root, combined)
    old = previous_models(root)
    support = support_models(root)
    keys = {model['key'] for model in old}
    identities = {(model['identity']['manufacturer'], model['identity']['model']) for model in old}
    previous_skus = {(model['identity']['manufacturer'].casefold(), model['identity']['sku'].casefold())
                     for model in old if model['identity']['manufacturer'] and model['identity']['sku']}
    for row in rows:
        definition = row['definition']
        c.require(definition['key'] not in keys and
                  (definition['identity']['manufacturer'], definition['identity']['model']) not in identities and
                  (definition['identity']['manufacturer'].casefold(), definition['identity']['sku'].casefold()) not in previous_skus,
                  'selected506k_previous_model_duplicate')
        if definition['kind'] == 'desktop':
            c.require(any(parent['kind'] == 'shelf' and any(all(definition['dimensionsMm'][key] <= slot['dimensionsMm'][key]
                      for key in ('width', 'height', 'depth')) for slot in parent['slots']) for parent in old+support),
                      'selected506k_support_unavailable')
    models = [row['definition'] for row in rows]+support
    pins = [dict(key=model['key'], revision=model['revision'], sha256=c.sha(c.canonical(model))) for model in models]
    c.require(pins == lock['definitions'], 'selected506k_definition_changed')
    catalogues = []
    for row in rows:
        model = row['definition']
        projection = c.projection(dict(definitions=[model]))
        projection['synthetic'] = False
        profile = projection['profiles'][0]
        evidence = row['evidence']
        unverified = any(re.search('unverified', asset['match'], re.I) for asset in evidence['referenceAssets'])
        # A family limitation in either the assets or the author's notes is
        # visible to the user; an exact model string never upgrades its scope.
        family = any(re.search('family|shared', asset['match'], re.I) for asset in evidence['referenceAssets']) or any(
            re.search('family', re.sub(r'\bSFP-family\b', 'SFP', limit, flags=re.I), re.I)
            for limit in evidence['limits'])
        profile.update(identity=model['identity'], source=model['provenance']['source'], visual=row['visual'],
                       referenceScope='unverified_reference' if unverified else 'family_reference' if family else 'model_reference',
                       reviewLimits=evidence['limits'])
        for group, original in zip(profile['groups'], model['groups']):
            group['powerRole'] = original['powerRole']
            if original.get('physicalConnector') is not None: group['physicalConnector'] = original['physicalConnector']
        prior = next((item for item in catalogues if item['version'] == projection['version']), None)
        if prior:
            prior['profiles'] += projection['profiles']
        else:
            catalogues.append(projection)
    for model in support:
        catalogues.append(c.projection(dict(definitions=[model])))
    server = server_source(models)
    sql = sql_source(models, pins)
    outputs = {SERVER: server, FRONTEND: g.pretty(catalogues), SQL: sql}
    inputs = {name: c.sha(value) for name, value in raw.items()}
    outputs[MANIFEST] = g.pretty(dict(formatVersion=1, targetSchema=41, catalogKey='rackclick-selected506k',
                                     state=STATE, inputs=inputs, files={name: c.sha(value) for name, value in outputs.items()},
                                     selectionIds=sorted(IDS), definitions=pins))
    outputs[TARGETS] = b.targets_source({**inputs, **{name: c.sha(value) for name, value in outputs.items()}}).replace(
        b'VerifyBatch50HardwareCatalog', b'VerifySelected506KHardwareCatalog').replace(b'_Batch50', b'_Selected506K').replace(
        b'batch50_', b'selected506k_').replace(b'build_hardware_batch50.py', b'build_hardware_selected506k.py', 1)
    return outputs


def run(root, write=False):
    b.compile_catalog = compile_catalog
    result = b.run(root, write)
    result.update(targetSchema=41, commercialModels=len(IDS), supportProfiles=1, selectionIds=sorted(IDS))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(run(ROOT, args.write)))
        return 0
    except (c.CatalogError, OSError) as error:
        print(json.dumps(dict(status='failed', code=str(error) if isinstance(error, c.CatalogError) else 'selected506k_io_failed')))
        return 1


if __name__ == '__main__':
    sys.exit(main())
