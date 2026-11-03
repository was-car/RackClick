"""Compile the fifth group of usable profiles drawn from the fixed 506-model selection.

Reuses the reviewed catalogue engine without rewriting historical sources.
This compiler publishes only fifty individually authored configurations.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).absolute().parents[1]
spec = importlib.util.spec_from_file_location('selected506e_private_engine', ROOT/'tools/hardware_physical_v2.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
b = engine.base
c, g = engine.c, engine.g
REVISION = 'selected506e-20261101-v1'
b.REVISION = REVISION
SOURCES = ['development/hardware/selected506e/core.json', 'development/hardware/selected506e/edge.json']
COUNTS = [25, 25]
SELECTION = 'development/hardware/selected-models-506.json'
LINKS = 'development/hardware/selected-profile-links.json'
PLAN = 'evidence/s1-20261101/integracion506e/PLAN-50.json'
LOCK = 'development/hardware/catalog-schema33.lock.json'
BASE = 'development/server/database/032-selected506d-hardware.sql'
SERVER = 'development/server/src/RackClick.Server/Selected506EHardwareProfiles.Generated.cs'
FRONTEND = 'development/frontend/src/hardware-selected506e.generated.json'
SQL = 'development/server/database/033-selected506e-hardware.sql'
MANIFEST = 'development/hardware/catalog-selected506e.manifest.json'
TARGETS = 'development/server/src/RackClick.Server/Selected506EHardware.Generated.targets'
TOOL = 'tools/build_hardware_selected506e.py'
SHARED = 'tools/hardware_physical_v2.py'
CORE = 'tools/build_hardware_batch50.py'
TRANSITIVE = ['tools/build_hardware_catalog.py', *['tools/build_hardware_catalog'+str(n)+'.py' for n in range(19, 24)]]
STATE = 'curated_development_not_a_release'
EXPECTED_LOCK_SHA256 = '02da7332037e4f4652385430034bfd70ef98f4ea4b90441c9c920761f1a38c24'
SKUS = {
    'cisco-c9200l-24t-4g': 'C9200L-24T-4G',
    'cisco-c9200l-48p-4g': 'C9200L-48P-4G',
    'nb-56d658406c3821e4': 'C1300-24P-4X',
    'nb-c6ac814fdd7b9934': 'C9200L-24P-4G',
    'nb-59ffa19030bec2db': 'C9200L-48T-4G',
    'nb-5e6bc5b25105aac2': 'C9300-24P',
    'nb-9d22e570931da32f': 'C9300-48T',
    'nb-703a133fe021a249': 'C9300L-48P-4X',
    'nb-3a0dec7f06699680': 'MS125-48FP-HW',
    'nb-24e436f8efc76877': 'ASR1002',
    'nb-ba797213d2a5841a': 'ASR1002-HX',
    'nb-f05a32f1a3f1d292': 'FPR2110-NGFW-K9',
    'nb-823b267b5cd72e2c': 'FPR3110-NGFW-K9',
    'nb-44d618c14f1ee6e3': 'FPR4112-NGFW-K9',
    'nb-6de5e10b8660c81a': 'JL626A',
    'nb-75adec80da5ff093': 'JL704C',
    'nb-0e6accdf31d7d113': 'JL319A',
    'nb-cd1c3bbe082c129d': 'JL321A',
    'nb-e2f5cc04c6ef0ee3': 'JL322A',
    'nb-b68b49db7fee9c88': 'CCS-720DT-48S-2F',
    'nb-0355b604a6794595': 'DCS-7020TR-48-F',
    'nb-857386ff2603fa07': 'DCS-7020TRA-48-F',
    'nb-e4457af07a020f38': '3HE15622AA',
    'nb-63eb4152092cd08f': '3HE17645AA',
    'nb-89d64c27c959137e': '3HE15623AA',
    'nb-00de5627d2ff4666': 'CRS328-24P-4S+RM',
    'nb-1adb46683cc91954': '02353HUB',
    'nb-3b6043083efdc428': '02353174',
    'nb-520f1d7a35b7e950': '02352QPP',
    'nb-53d11b15f96aebfd': '4220-4MW-20P-4X',
    'nb-66c3ee1f91a9421d': 'N2048',
    'nb-69510e57b0827c16': '4220-8MW-40P-4X',
    'nb-7d81ebcda392315d': 'GS752TX',
    'nb-858c4b2d8df65bb9': 'GS728TXP',
    'nb-8daa73dfc2be1ec5': 'CRS309-1G-8S+',
    'nb-99ab5630f088ba2c': '02350DLX',
    'nb-b00080f2380582f6': '16533',
    'nb-c0ac0f175a7366e6': '98012120',
    'nb-c8a9b3d42f78ee94': '4220-12T-4X',
    'nb-cf0f597e804145ae': '4220-48T-4X',
    'nb-dc19eda57299b02a': '4220-4MW-8P-4X',
    'nb-dd10d7331f22b8bf': '4120-48MW-4Y',
    'nb-e94a1bc6fc227b74': 'ECS-24-PoE',
    'nb-e9dabe5202e7c565': '4220-48P-4X',
    'nb-ec11fe6fea97c18d': 'SRX380-P-SYS-JB-AC',
    'nb-f390c56e840a7483': 'CRS317-1G-16S+',
    'palo-alto-pa-1410': 'PA-1410',
    'palo-alto-pa-1420': 'PA-1420',
    'palo-alto-pa-3220': 'PA-3220',
    'ubiquiti-usw-24-poe': 'USW-24-POE',
}
MOUNTS = {
    'cisco-c9200l-24t-4g': ('rack', 1),
    'cisco-c9200l-48p-4g': ('rack', 1),
    'nb-56d658406c3821e4': ('rack', 1),
    'nb-c6ac814fdd7b9934': ('rack', 1),
    'nb-59ffa19030bec2db': ('rack', 1),
    'nb-5e6bc5b25105aac2': ('rack', 1),
    'nb-9d22e570931da32f': ('rack', 1),
    'nb-703a133fe021a249': ('rack', 1),
    'nb-3a0dec7f06699680': ('rack', 1),
    'nb-24e436f8efc76877': ('rack', 2),
    'nb-ba797213d2a5841a': ('rack', 2),
    'nb-f05a32f1a3f1d292': ('rack', 1),
    'nb-823b267b5cd72e2c': ('rack', 1),
    'nb-44d618c14f1ee6e3': ('rack', 1),
    'nb-6de5e10b8660c81a': ('rack', 1),
    'nb-75adec80da5ff093': ('rack', 1),
    'nb-0e6accdf31d7d113': ('rack', 1),
    'nb-cd1c3bbe082c129d': ('rack', 1),
    'nb-e2f5cc04c6ef0ee3': ('rack', 1),
    'nb-b68b49db7fee9c88': ('rack', 1),
    'nb-0355b604a6794595': ('rack', 1),
    'nb-857386ff2603fa07': ('rack', 1),
    'nb-e4457af07a020f38': ('rack', 1),
    'nb-63eb4152092cd08f': ('rack', 1),
    'nb-89d64c27c959137e': ('rack', 1),
    'nb-00de5627d2ff4666': ('rack', 1),
    'nb-1adb46683cc91954': ('rack', 1),
    'nb-3b6043083efdc428': ('rack', 1),
    'nb-520f1d7a35b7e950': ('rack', 1),
    'nb-53d11b15f96aebfd': ('rack', 1),
    'nb-66c3ee1f91a9421d': ('rack', 1),
    'nb-69510e57b0827c16': ('rack', 1),
    'nb-7d81ebcda392315d': ('rack', 1),
    'nb-858c4b2d8df65bb9': ('rack', 1),
    'nb-8daa73dfc2be1ec5': ('rack', 1),
    'nb-99ab5630f088ba2c': ('rack', 1),
    'nb-b00080f2380582f6': ('rack', 1),
    'nb-c0ac0f175a7366e6': ('rack', 1),
    'nb-c8a9b3d42f78ee94': ('rack', 1),
    'nb-cf0f597e804145ae': ('rack', 1),
    'nb-dc19eda57299b02a': ('rack', 1),
    'nb-dd10d7331f22b8bf': ('rack', 1),
    'nb-e94a1bc6fc227b74': ('rack', 1),
    'nb-e9dabe5202e7c565': ('rack', 1),
    'nb-ec11fe6fea97c18d': ('rack', 1),
    'nb-f390c56e840a7483': ('rack', 1),
    'palo-alto-pa-1410': ('rack', 1),
    'palo-alto-pa-1420': ('rack', 1),
    'palo-alto-pa-3220': ('rack', 2),
    'ubiquiti-usw-24-poe': ('rack', 1),
}
IDS = tuple(sorted(SKUS))


def validate_model(row):
    return engine.validate_model(row, REVISION)


def prior_names(root):
    result = [p.relative_to(root).as_posix() for p in c.path(root, 'development/hardware').glob('catalog-*-v1.json')]
    for folder in ('batch50', 'batch50b', 'batch100', 'batch100b', 'batch100c'):
        result += [p.relative_to(root).as_posix() for p in c.path(root, 'development/hardware/'+folder).glob('*.json')]
    result += ['development/hardware/selected506a/aruba.json', 'development/hardware/selected506a/ubiquiti.json',
               'development/hardware/selected506b/core.json', 'development/hardware/selected506b/access.json',
               'development/hardware/selected506c/firewalls.json', 'development/hardware/selected506c/edge.json',
               'development/hardware/selected506d/core.json', 'development/hardware/selected506d/edge.json']
    return sorted(result)


def previous_models(root):
    models = []
    for name in prior_names(root):
        data = c.load(c.path(root, name).read_bytes())
        models += data['definitions'] if name.endswith('-v1.json') else [row['definition'] for row in data['models']]
    c.require(len(models) == 578 and sum(bool(model['identity']['manufacturer']) for model in models) == 573,
              'selected506e_baseline_invalid')
    return models


def selected_rows(root, data):
    b.fields(data, 'formatVersion revision models')
    c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
              data['revision'] == REVISION and isinstance(data['models'], list) and len(IDS) == 50 and
              set(MOUNTS) == set(IDS) and len(data['models']) == 50,
              'selected506e_count_invalid')
    selection = c.load(c.path(root, SELECTION).read_bytes())['models']
    chosen = {row['id']: row for row in selection}
    plan = c.load(c.path(root, PLAN).read_bytes())
    c.require(type(plan['formatVersion']) is int and plan['formatVersion'] == 1 and
              plan['revision'] == REVISION and plan['targetSchema'] == 33 and
              plan['baselineDefinitions'] == 578 and plan['baselineCommercial'] == 573 and
              set(plan['authoring']) == {'core', 'edge'} and
              all(isinstance(plan['authoring'][name], list) and len(plan['authoring'][name]) == 25
                  for name in ('core', 'edge')), 'selected506e_assignment_invalid')
    planned = [row['id'] for name in ('core', 'edge') for row in plan['authoring'][name]]
    c.require(len(planned) == len(set(planned)) == 50 and set(planned) == set(IDS),
              'selected506e_assignment_invalid')
    links = c.load(c.path(root, LINKS).read_bytes())
    c.require(len(links['links']) == 7 and
              set(IDS).isdisjoint(row['selectionId'] for row in links['links']),
              'selected506e_previous_model_duplicate')
    c.require(len(chosen) == 506 and set(IDS) <= set(chosen), 'selected506e_selection_invalid')
    rows = [validate_model(row) for row in data['models']]
    c.require(all(group['count'] <= 96 for row in rows for group in row['definition']['groups']),
              'selected506e_runtime_group_limit')
    by_key = {row['definition']['key']: row for row in rows}
    c.require(len(by_key) == len(IDS) and set(by_key) == {'selected-'+identifier for identifier in IDS},
              'selected506e_identity_invalid')
    c.require(len({(row['definition']['identity']['manufacturer'].casefold(),
                    row['definition']['identity']['sku'].casefold()) for row in rows}) == 50,
              'selected506e_duplicate_sku')
    for identifier in IDS:
        definition = by_key['selected-'+identifier]['definition']
        original = chosen[identifier]
        c.require(definition['identity']['manufacturer'] == original['manufacturer'] and
                  definition['identity']['model'] == original['model'] and
                  definition['identity']['sku'].casefold() == SKUS[identifier].casefold(), 'selected506e_model_substitution')
        c.require((definition['kind'], definition['rackUnits']) == MOUNTS[identifier],
                  'selected506e_mount_substitution')
    return sorted(rows, key=lambda row: row['definition']['key'])


def compile_catalog(root):
    names = [*SOURCES, SELECTION, LINKS, PLAN, LOCK, BASE, SHARED, CORE, *TRANSITIVE, TOOL, *prior_names(root)]
    raw = {name: c.path(root, name).read_bytes() for name in names}
    lock = c.load(raw[LOCK])
    c.require(c.sha(raw[LOCK]) == EXPECTED_LOCK_SHA256, 'selected506e_lock_not_reviewed')
    c.require(lock['targetSchema'] == 33 and lock['state'] == STATE and
              lock['sourceSha256'] == {name: c.sha(raw[name]) for name in SOURCES} and
              lock['baseMigrationSha256'] == c.sha(raw[BASE]) and
              lock['sharedCompilerSha256'] == c.sha(raw[SHARED]) and lock['baseEngineSha256'] == c.sha(raw[CORE]) and
              lock['transitiveCompilerSha256'] == {name: c.sha(raw[name]) for name in TRANSITIVE} and
              lock['selectionIds'] == sorted(IDS),
              'selected506e_input_changed')
    c.require(lock['baselineSourceSha256'] == {name: c.sha(raw[name]) for name in prior_names(root)} and
              lock['selectionSha256'] == c.sha(raw[SELECTION]) and lock['planSha256'] == c.sha(raw[PLAN]) and
              lock['profileLinksSha256'] == c.sha(raw[LINKS]),
              'selected506e_baseline_changed')
    combined = dict(formatVersion=1, revision=REVISION, models=[])
    for source, count in zip(SOURCES, COUNTS):
        data = c.load(raw[source])
        b.fields(data, 'formatVersion revision models')
        c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
                  data['revision'] == REVISION and isinstance(data['models'], list) and len(data['models']) == count,
                  'selected506e_source_count_invalid')
        combined['models'] += data['models']
    rows = selected_rows(root, combined)
    old = previous_models(root)
    keys = {model['key'] for model in old}
    identities = {(model['identity']['manufacturer'], model['identity']['model']) for model in old}
    previous_skus = {(model['identity']['manufacturer'].casefold(), model['identity']['sku'].casefold())
                     for model in old if model['identity']['manufacturer'] and model['identity']['sku']}
    for row in rows:
        definition = row['definition']
        c.require(definition['key'] not in keys and
                  (definition['identity']['manufacturer'], definition['identity']['model']) not in identities and
                  (definition['identity']['manufacturer'].casefold(), definition['identity']['sku'].casefold()) not in previous_skus,
                  'selected506e_previous_model_duplicate')
        if definition['kind'] == 'desktop':
            c.require(any(parent['kind'] == 'shelf' and any(all(definition['dimensionsMm'][key] <= slot['dimensionsMm'][key]
                      for key in ('width', 'height', 'depth')) for slot in parent['slots']) for parent in old),
                      'selected506e_support_unavailable')
    models = [row['definition'] for row in rows]
    pins = [dict(key=model['key'], revision=model['revision'], sha256=c.sha(c.canonical(model))) for model in models]
    c.require(pins == lock['definitions'], 'selected506e_definition_changed')
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
        prior = next((item for item in catalogues if item['version'] == projection['version']), None)
        if prior:
            prior['profiles'] += projection['profiles']
        else:
            catalogues.append(projection)
    server = b.server_source(models).replace(b'Batch50HardwareProfiles', b'Selected506EHardwareProfiles').replace(
        b'build_hardware_batch50.py', b'build_hardware_selected506e.py')
    sql = b'-- Auto-generated selected506e. SQL001-032 and sealed revisions remain unchanged.\n' + b'\n'.join(
        line for line in g.sql_source(models, pins).splitlines() if not line.startswith(b'--')) + b'\n'
    outputs = {SERVER: server, FRONTEND: g.pretty(catalogues), SQL: sql}
    inputs = {name: c.sha(value) for name, value in raw.items()}
    outputs[MANIFEST] = g.pretty(dict(formatVersion=1, targetSchema=33, catalogKey='rackclick-selected506e',
                                     state=STATE, inputs=inputs, files={name: c.sha(value) for name, value in outputs.items()},
                                     selectionIds=sorted(IDS), definitions=pins))
    outputs[TARGETS] = b.targets_source({**inputs, **{name: c.sha(value) for name, value in outputs.items()}}).replace(
        b'VerifyBatch50HardwareCatalog', b'VerifySelected506EHardwareCatalog').replace(b'_Batch50', b'_Selected506E').replace(
        b'batch50_', b'selected506e_').replace(b'build_hardware_batch50.py', b'build_hardware_selected506e.py', 1)
    return outputs


def run(root, write=False):
    b.compile_catalog = compile_catalog
    result = b.run(root, write)
    result.update(targetSchema=33, commercialModels=len(IDS), selectionIds=sorted(IDS))
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
        print(json.dumps(dict(status='failed', code=str(error) if isinstance(error, c.CatalogError) else 'selected506e_io_failed')))
        return 1


if __name__ == '__main__':
    sys.exit(main())
