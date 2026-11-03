"""Compile the sixth group of usable profiles drawn from the fixed 506-model selection.

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
spec = importlib.util.spec_from_file_location('selected506f_private_engine', ROOT/'tools/hardware_physical_v2.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
b = engine.base
c, g = engine.c, engine.g
REVISION = 'selected506f-20261101-v1'
b.REVISION = REVISION
SOURCES = ['development/hardware/selected506f/core.json', 'development/hardware/selected506f/edge.json']
COUNTS = [25, 25]
SELECTION = 'development/hardware/selected-models-506.json'
LINKS = 'development/hardware/selected-profile-links.json'
PLAN = 'evidence/s1-20261101/integracion506f/PLAN-50.json'
LOCK = 'development/hardware/catalog-schema34.lock.json'
BASE = 'development/server/database/033-selected506e-hardware.sql'
SERVER = 'development/server/src/RackClick.Server/Selected506FHardwareProfiles.Generated.cs'
FRONTEND = 'development/frontend/src/hardware-selected506f.generated.json'
SQL = 'development/server/database/034-selected506f-hardware.sql'
MANIFEST = 'development/hardware/catalog-selected506f.manifest.json'
TARGETS = 'development/server/src/RackClick.Server/Selected506FHardware.Generated.targets'
TOOL = 'tools/build_hardware_selected506f.py'
SHARED = 'tools/hardware_physical_v2.py'
CORE = 'tools/build_hardware_batch50.py'
TRANSITIVE = ['tools/build_hardware_catalog.py', *['tools/build_hardware_catalog'+str(n)+'.py' for n in range(19, 24)]]
STATE = 'curated_development_not_a_release'
EXPECTED_LOCK_SHA256 = 'c3feba0f2347213bb65a93acdffd2e5587a0c7d54f096b94397c313585ebfb8c'
SKUS = {
    'dell-r350': 'R350',
    'nb-ce11d1eae1be7887': 'R640',
    'nb-1949dff7c63dc370': 'R6515',
    'nb-fb93dfe85c1f7a8b': 'R7515',
    'nb-33c7e52f1cb00564': 'R7525',
    'nb-7a4f104d07cdb0f2': 'R540',
    'nb-fbdb4552eed0ee61': 'R620',
    'nb-302f3fd979788f2e': 'R630',
    'nb-73980deb1c5f24bc': 'R720',
    'hpe-dl360-gen10': 'P19766-B21',
    'nb-c1f158f64ea1ee8a': 'ProLiant DL360 Gen11',
    'nb-149a66cfbe4b740e': 'P19717-B21',
    'nb-14bfeedc875ce4de': 'P52534-B21',
    'nb-ff98cf8f1bf55eb7': 'ProLiant DL385 Gen10 Plus v2',
    'nb-c7c438542f1254b3': 'ProLiant DL360 Gen10 Plus',
    'nb-b47c684d217e4ade': '755258-B21',
    'nb-1397e3169b861f26': 'ProLiant DL20 Gen11',
    'nb-87abdfb9366e4dcc': '7D7Q',
    'nb-5ceaeace0476cada': '7Z7x',
    'nb-e9b61460b1aac8e0': '7D7x',
    'nb-d6c7e4ca54f24095': '7D2X',
    'nb-efc4c57b1d5c811d': '7X0x',
    'nb-58396084a7d0cb50': 'SYS-5019D-FN8TP',
    'nb-cb719f76ccc4e4c8': 'SYS-1027R-WRF',
    'nb-d532953f6aab1767': 'SYS-6029P-TR',
    'nb-22f6dc2225b95f69': '903715-90',
    'nb-31017da140e60303': 'S9600-32X',
    'nb-417dcd51ce56234d': 'GS1100-16',
    'nb-4b73963d18934c09': 'ZXR10 5950-28TD-L / zxr10-5950-28td-l',
    'nb-4f6f5a063ccdaf07': 'DEC2770',
    'nb-665e9fb0c5bbe24e': 'SMCGS8P-SMART',
    'nb-6a0159c3c324ded0': 'FP4ZZ7656xxxx',
    'nb-775999426472421b': 'ERS 3526T-PWR+',
    'nb-80c45eaf78955607': 'MES2308P',
    'nb-90d3445d2598509a': 'DGS-1520-52',
    'nb-9363a14b01cfb299': '8300 Security Gateway',
    'nb-949bb6f1695a8037': '02353BMU',
    'nb-a177f34a640c5260': '903713-90',
    'nb-b96a0faf83d55061': 'DES-1005P',
    'nb-c2987ad4b24bf989': 'GWN7831',
    'nb-c7a6bbe78d369445': 'OS6400-24',
    'nb-cbcbd6a95a949d7a': 'DXS-3400-24TC',
    'nb-cd689cba786b2529': 'MES2324P',
    'nb-d0eebb2cb671d40b': 'SN2201',
    'nb-d9ade587e7147b9a': 'i5600',
    'nb-f7f404654aad4d5a': 'F0PEC4654xxxx',
    'nb-fce19920137ab0c4': 'ZXR10 5950-28PD-L / zxr10-5950-28pd-l',
    'nb-fe8d278736262b7c': 'i2600',
    'palo-alto-pa-415': 'PA-415',
    'palo-alto-pa-445': 'PA-445',
}
MOUNTS = {
    'dell-r350': ('rack', 1),
    'nb-ce11d1eae1be7887': ('rack', 1),
    'nb-1949dff7c63dc370': ('rack', 1),
    'nb-fb93dfe85c1f7a8b': ('rack', 2),
    'nb-33c7e52f1cb00564': ('rack', 2),
    'nb-7a4f104d07cdb0f2': ('rack', 2),
    'nb-fbdb4552eed0ee61': ('rack', 1),
    'nb-302f3fd979788f2e': ('rack', 1),
    'nb-73980deb1c5f24bc': ('rack', 2),
    'hpe-dl360-gen10': ('rack', 1),
    'nb-c1f158f64ea1ee8a': ('rack', 1),
    'nb-149a66cfbe4b740e': ('rack', 2),
    'nb-14bfeedc875ce4de': ('rack', 2),
    'nb-ff98cf8f1bf55eb7': ('rack', 2),
    'nb-c7c438542f1254b3': ('rack', 1),
    'nb-b47c684d217e4ade': ('rack', 1),
    'nb-1397e3169b861f26': ('rack', 1),
    'nb-87abdfb9366e4dcc': ('rack', 1),
    'nb-5ceaeace0476cada': ('rack', 1),
    'nb-e9b61460b1aac8e0': ('rack', 1),
    'nb-d6c7e4ca54f24095': ('rack', 1),
    'nb-efc4c57b1d5c811d': ('rack', 2),
    'nb-58396084a7d0cb50': ('rack', 1),
    'nb-cb719f76ccc4e4c8': ('rack', 1),
    'nb-d532953f6aab1767': ('rack', 2),
    'nb-22f6dc2225b95f69': ('rack', 1),
    'nb-31017da140e60303': ('rack', 2),
    'nb-417dcd51ce56234d': ('desktop', 0),
    'nb-4b73963d18934c09': ('rack', 1),
    'nb-4f6f5a063ccdaf07': ('rack', 1),
    'nb-665e9fb0c5bbe24e': ('desktop', 0),
    'nb-6a0159c3c324ded0': ('rack', 1),
    'nb-775999426472421b': ('rack', 1),
    'nb-80c45eaf78955607': ('rack', 1),
    'nb-90d3445d2598509a': ('rack', 1),
    'nb-9363a14b01cfb299': ('rack', 1),
    'nb-949bb6f1695a8037': ('rack', 1),
    'nb-a177f34a640c5260': ('rack', 1),
    'nb-b96a0faf83d55061': ('desktop', 0),
    'nb-c2987ad4b24bf989': ('rack', 1),
    'nb-c7a6bbe78d369445': ('rack', 1),
    'nb-cbcbd6a95a949d7a': ('rack', 1),
    'nb-cd689cba786b2529': ('rack', 1),
    'nb-d0eebb2cb671d40b': ('rack', 1),
    'nb-d9ade587e7147b9a': ('rack', 1),
    'nb-f7f404654aad4d5a': ('rack', 1),
    'nb-fce19920137ab0c4': ('rack', 1),
    'nb-fe8d278736262b7c': ('rack', 1),
    'palo-alto-pa-415': ('desktop', 0),
    'palo-alto-pa-445': ('desktop', 0),
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
               'development/hardware/selected506d/core.json', 'development/hardware/selected506d/edge.json',
               'development/hardware/selected506e/core.json', 'development/hardware/selected506e/edge.json']
    return sorted(result)


def previous_models(root):
    models = []
    for name in prior_names(root):
        data = c.load(c.path(root, name).read_bytes())
        models += data['definitions'] if name.endswith('-v1.json') else [row['definition'] for row in data['models']]
    c.require(len(models) == 628 and sum(bool(model['identity']['manufacturer']) for model in models) == 623,
              'selected506f_baseline_invalid')
    return models


def selected_rows(root, data):
    b.fields(data, 'formatVersion revision models')
    c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
              data['revision'] == REVISION and isinstance(data['models'], list) and len(IDS) == 50 and
              set(MOUNTS) == set(IDS) and len(data['models']) == 50,
              'selected506f_count_invalid')
    selection = c.load(c.path(root, SELECTION).read_bytes())['models']
    chosen = {row['id']: row for row in selection}
    plan = c.load(c.path(root, PLAN).read_bytes())
    c.require(type(plan['formatVersion']) is int and plan['formatVersion'] == 1 and
              plan['revision'] == REVISION and plan['targetSchema'] == 34 and
              plan['baselineDefinitions'] == 628 and plan['baselineCommercial'] == 623 and
              set(plan['authoring']) == {'core', 'edge'} and
              all(isinstance(plan['authoring'][name], list) and len(plan['authoring'][name]) == 25
                  for name in ('core', 'edge')), 'selected506f_assignment_invalid')
    planned = [row['id'] for name in ('core', 'edge') for row in plan['authoring'][name]]
    c.require(len(planned) == len(set(planned)) == 50 and set(planned) == set(IDS),
              'selected506f_assignment_invalid')
    links = c.load(c.path(root, LINKS).read_bytes())
    c.require(len(links['links']) == 7 and
              set(IDS).isdisjoint(row['selectionId'] for row in links['links']),
              'selected506f_previous_model_duplicate')
    c.require(len(chosen) == 506 and set(IDS) <= set(chosen), 'selected506f_selection_invalid')
    rows = [validate_model(row) for row in data['models']]
    c.require(all(group['count'] <= 96 for row in rows for group in row['definition']['groups']),
              'selected506f_runtime_group_limit')
    by_key = {row['definition']['key']: row for row in rows}
    c.require(len(by_key) == len(IDS) and set(by_key) == {'selected-'+identifier for identifier in IDS},
              'selected506f_identity_invalid')
    c.require(len({(row['definition']['identity']['manufacturer'].casefold(),
                    row['definition']['identity']['sku'].casefold()) for row in rows}) == 50,
              'selected506f_duplicate_sku')
    for identifier in IDS:
        definition = by_key['selected-'+identifier]['definition']
        original = chosen[identifier]
        c.require(definition['identity']['manufacturer'] == original['manufacturer'] and
                  definition['identity']['model'] == original['model'] and
                  definition['identity']['sku'].casefold() == SKUS[identifier].casefold(), 'selected506f_model_substitution')
        c.require((definition['kind'], definition['rackUnits']) == MOUNTS[identifier],
                  'selected506f_mount_substitution')
    return sorted(rows, key=lambda row: row['definition']['key'])


def compile_catalog(root):
    names = [*SOURCES, SELECTION, LINKS, PLAN, LOCK, BASE, SHARED, CORE, *TRANSITIVE, TOOL, *prior_names(root)]
    raw = {name: c.path(root, name).read_bytes() for name in names}
    lock = c.load(raw[LOCK])
    c.require(c.sha(raw[LOCK]) == EXPECTED_LOCK_SHA256, 'selected506f_lock_not_reviewed')
    c.require(lock['targetSchema'] == 34 and lock['state'] == STATE and
              lock['sourceSha256'] == {name: c.sha(raw[name]) for name in SOURCES} and
              lock['baseMigrationSha256'] == c.sha(raw[BASE]) and
              lock['sharedCompilerSha256'] == c.sha(raw[SHARED]) and lock['baseEngineSha256'] == c.sha(raw[CORE]) and
              lock['transitiveCompilerSha256'] == {name: c.sha(raw[name]) for name in TRANSITIVE} and
              lock['selectionIds'] == sorted(IDS),
              'selected506f_input_changed')
    c.require(lock['baselineSourceSha256'] == {name: c.sha(raw[name]) for name in prior_names(root)} and
              lock['selectionSha256'] == c.sha(raw[SELECTION]) and lock['planSha256'] == c.sha(raw[PLAN]) and
              lock['profileLinksSha256'] == c.sha(raw[LINKS]),
              'selected506f_baseline_changed')
    combined = dict(formatVersion=1, revision=REVISION, models=[])
    for source, count in zip(SOURCES, COUNTS):
        data = c.load(raw[source])
        b.fields(data, 'formatVersion revision models')
        c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
                  data['revision'] == REVISION and isinstance(data['models'], list) and len(data['models']) == count,
                  'selected506f_source_count_invalid')
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
                  'selected506f_previous_model_duplicate')
        if definition['kind'] == 'desktop':
            c.require(any(parent['kind'] == 'shelf' and any(all(definition['dimensionsMm'][key] <= slot['dimensionsMm'][key]
                      for key in ('width', 'height', 'depth')) for slot in parent['slots']) for parent in old),
                      'selected506f_support_unavailable')
    models = [row['definition'] for row in rows]
    pins = [dict(key=model['key'], revision=model['revision'], sha256=c.sha(c.canonical(model))) for model in models]
    c.require(pins == lock['definitions'], 'selected506f_definition_changed')
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
    server = b.server_source(models).replace(b'Batch50HardwareProfiles', b'Selected506FHardwareProfiles').replace(
        b'build_hardware_batch50.py', b'build_hardware_selected506f.py')
    sql = b'-- Auto-generated selected506f. SQL001-033 and sealed revisions remain unchanged.\n' + b'\n'.join(
        line for line in g.sql_source(models, pins).splitlines() if not line.startswith(b'--')) + b'\n'
    outputs = {SERVER: server, FRONTEND: g.pretty(catalogues), SQL: sql}
    inputs = {name: c.sha(value) for name, value in raw.items()}
    outputs[MANIFEST] = g.pretty(dict(formatVersion=1, targetSchema=34, catalogKey='rackclick-selected506f',
                                     state=STATE, inputs=inputs, files={name: c.sha(value) for name, value in outputs.items()},
                                     selectionIds=sorted(IDS), definitions=pins))
    outputs[TARGETS] = b.targets_source({**inputs, **{name: c.sha(value) for name, value in outputs.items()}}).replace(
        b'VerifyBatch50HardwareCatalog', b'VerifySelected506FHardwareCatalog').replace(b'_Batch50', b'_Selected506F').replace(
        b'batch50_', b'selected506f_').replace(b'build_hardware_batch50.py', b'build_hardware_selected506f.py', 1)
    return outputs


def run(root, write=False):
    b.compile_catalog = compile_catalog
    result = b.run(root, write)
    result.update(targetSchema=34, commercialModels=len(IDS), selectionIds=sorted(IDS))
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
        print(json.dumps(dict(status='failed', code=str(error) if isinstance(error, c.CatalogError) else 'selected506f_io_failed')))
        return 1


if __name__ == '__main__':
    sys.exit(main())
