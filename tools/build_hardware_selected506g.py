"""Compile the seventh group of usable profiles drawn from the fixed 506-model selection.

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
spec = importlib.util.spec_from_file_location('selected506g_private_engine', ROOT/'tools/hardware_physical_v2.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
b = engine.base
c, g = engine.c, engine.g
REVISION = 'selected506g-20261101-v1'
b.REVISION = REVISION
SOURCES = ['development/hardware/selected506g/core.json', 'development/hardware/selected506g/edge.json']
COUNTS = [25, 25]
SELECTION = 'development/hardware/selected-models-506.json'
LINKS = 'development/hardware/selected-profile-links.json'
PLAN = 'evidence/s1-20261101/integracion506g/PLAN-50.json'
LOCK = 'development/hardware/catalog-schema35.lock.json'
BASE = 'development/server/database/034-selected506f-hardware.sql'
SERVER = 'development/server/src/RackClick.Server/Selected506GHardwareProfiles.Generated.cs'
FRONTEND = 'development/frontend/src/hardware-selected506g.generated.json'
SQL = 'development/server/database/035-selected506g-hardware.sql'
MANIFEST = 'development/hardware/catalog-selected506g.manifest.json'
TARGETS = 'development/server/src/RackClick.Server/Selected506GHardware.Generated.targets'
TOOL = 'tools/build_hardware_selected506g.py'
SHARED = 'tools/hardware_physical_v2.py'
CORE = 'tools/build_hardware_batch50.py'
TRANSITIVE = ['tools/build_hardware_catalog.py', *['tools/build_hardware_catalog'+str(n)+'.py' for n in range(19, 24)]]
STATE = 'curated_development_not_a_release'
EXPECTED_LOCK_SHA256 = 'fdf4b6fd16ae63bcdfb02ea79e68f077803142846b403d63e33eb28d6f742f49'
SKUS = {
    'nb-672799eaa4f759d6': 'R7715',
    'nb-c263db2c3b4a2925': 'R760xd2',
    'nb-ecabe45d7f7fcc48': 'R7615',
    'nb-948fad2f13709dc9': 'R7725',
    'nb-eda39086bd9e9cda': 'ProLiant DL345 Gen11',
    'nb-7b7fd92e11204896': 'AS-1124US-TNRP',
    'nb-15047e48f0df3f18': 'AS-2115HS-TNR',
    'nb-35d87f3fc5c78828': 'SSG-610P-ACR12N4H',
    'nb-32bb124abaaa021b': 'RS300-E11-RS4',
    'nb-177693053e26efa4': '8871',
    'nb-34f23e64e816971f': 'ASG-2015S-E1CR24L',
    'nb-f802ebc80b7bb96e': '7DGx',
    'nb-d3f25e78482e4bff': 'R730xd',
    'nb-e4121ee57f092985': '669257-B21',
    'nb-2cb44217d425b70f': 'SSG-6049P-E1CR36L',
    'nb-c6b1705740436107': '653200-B21',
    'nb-418d42c0d18a34a4': 'SYS-5018D-FN8T',
    'nb-0e9380b77257926e': 'ProLiant DX385 Gen10 Plus',
    'nb-2b88f84c9db567bf': '170-3926-900',
    'nb-5eb1039c16a0df6a': '170-3930-900',
    'nb-feb9fd36baf516b8': '170-3942-900',
    'nb-d7b89b29215a9708': '170-5160-900',
    'nb-4a0b0e3bbe63b84a': '170-5162-900',
    'nb-75df9fe3366f5eba': 'S0E91A',
    'nb-36567f277193e94e': '170-8114-900',
    'nb-c5937f7093956ec3': 'CPAP-SG7000-SNBT',
    'nb-79c9c5a3726513c9': 'CPAP-SG16000-PLUS-SNBT',
    'nb-5d4d2d2ec5a6b81b': 'CPAP-SG19200-PLUS-SNBT',
    'nb-765b000f7862b2a5': 'F400 Rev. C .F20',
    'nb-7a6f331eb573b567': 'BNGF380B',
    'nb-021661043dd2d49f': '2000',
    'nb-9c4abe55a270318f': 'r2600',
    'nb-f5940bcac5635cc5': 'r5600',
    'nb-ec99b9ef925f518f': 'r10600',
    'nb-18abeefcccac198a': 'LM-X1',
    'nb-2565622a0959d865': 'SN2100',
    'nb-fe8f97a3849d4e66': '909-0XXX-ZD00',
    'nb-9127f2021330b9a8': '877622-xx1',
    'nb-d45ace2059d491dd': '02354VBU',
    'nb-fb08077e5b9dd1cd': '98011295',
    'nb-22aef0e6cd06d2b7': 'S5735-L8T4X-A1',
    'sonicwall-tz370w': 'TZ370W',
    'palo-alto-pa-5445': 'PA-5445',
    'palo-alto-pa-5450': 'PA-5450',
    'nb-e54b976f708867aa': 'ACX7024X',
    'nb-b1f6fce68b44bdac': 'CCS-720XP-96ZC2-4F',
    'nb-f73dd791a2fc73e8': 'CCS-722XPM-48Y4-2F',
    'nb-a8af9348bfc46f13': 'ASR1004',
    'nb-0c237b37d9df0ddb': 'ASR1006',
    'nb-028e1d1cc36b14e6': 'N9K-C9504',
}
MOUNTS = {
    'nb-672799eaa4f759d6': ('rack', 2),
    'nb-c263db2c3b4a2925': ('rack', 2),
    'nb-ecabe45d7f7fcc48': ('rack', 2),
    'nb-948fad2f13709dc9': ('rack', 2),
    'nb-eda39086bd9e9cda': ('rack', 2),
    'nb-7b7fd92e11204896': ('rack', 1),
    'nb-15047e48f0df3f18': ('rack', 2),
    'nb-35d87f3fc5c78828': ('rack', 1),
    'nb-32bb124abaaa021b': ('rack', 1),
    'nb-177693053e26efa4': ('rack', 2),
    'nb-34f23e64e816971f': ('rack', 2),
    'nb-f802ebc80b7bb96e': ('rack', 2),
    'nb-d3f25e78482e4bff': ('rack', 2),
    'nb-e4121ee57f092985': ('rack', 2),
    'nb-2cb44217d425b70f': ('rack', 4),
    'nb-c6b1705740436107': ('rack', 2),
    'nb-418d42c0d18a34a4': ('rack', 1),
    'nb-0e9380b77257926e': ('rack', 2),
    'nb-2b88f84c9db567bf': ('rack', 1),
    'nb-5eb1039c16a0df6a': ('rack', 1),
    'nb-feb9fd36baf516b8': ('rack', 1),
    'nb-d7b89b29215a9708': ('rack', 1),
    'nb-4a0b0e3bbe63b84a': ('rack', 1),
    'nb-75df9fe3366f5eba': ('rack', 1),
    'nb-36567f277193e94e': ('rack', 2),
    'nb-c5937f7093956ec3': ('rack', 1),
    'nb-79c9c5a3726513c9': ('rack', 2),
    'nb-5d4d2d2ec5a6b81b': ('rack', 2),
    'nb-765b000f7862b2a5': ('rack', 1),
    'nb-7a6f331eb573b567': ('rack', 1),
    'nb-021661043dd2d49f': ('rack', 1),
    'nb-9c4abe55a270318f': ('rack', 1),
    'nb-f5940bcac5635cc5': ('rack', 1),
    'nb-ec99b9ef925f518f': ('rack', 1),
    'nb-18abeefcccac198a': ('rack', 1),
    'nb-2565622a0959d865': ('rack', 1),
    'nb-fe8f97a3849d4e66': ('rack', 1),
    'nb-9127f2021330b9a8': ('rack', 5),
    'nb-d45ace2059d491dd': ('rack', 1),
    'nb-fb08077e5b9dd1cd': ('desktop', 0),
    'nb-22aef0e6cd06d2b7': ('desktop', 0),
    'sonicwall-tz370w': ('desktop', 0),
    'palo-alto-pa-5445': ('rack', 2),
    'palo-alto-pa-5450': ('rack', 5),
    'nb-e54b976f708867aa': ('rack', 1),
    'nb-b1f6fce68b44bdac': ('rack', 2),
    'nb-f73dd791a2fc73e8': ('rack', 1),
    'nb-a8af9348bfc46f13': ('rack', 4),
    'nb-0c237b37d9df0ddb': ('rack', 6),
    'nb-028e1d1cc36b14e6': ('rack', 7),
}
IDS = tuple(sorted(SKUS))


def validate_model(row):
    original = engine.validate_model(row, REVISION)
    # Domain.Names defaults to 100 Unicode scalars. Authoring counts the raw
    # name without trimming; legacy C0 checks remain, and G excludes C1/surrogates.
    for group in original['definition']['groups']:
        name = group['name']
        c.require(bool(name.strip()) and len(name) <= 100 and
                  not any(0x7f <= ord(char) <= 0x9f or 0xd800 <= ord(char) <= 0xdfff
                          for char in name),
                  'selected506g_group_name_invalid')
    return original


def prior_names(root):
    result = [p.relative_to(root).as_posix() for p in c.path(root, 'development/hardware').glob('catalog-*-v1.json')]
    for folder in ('batch50', 'batch50b', 'batch100', 'batch100b', 'batch100c'):
        result += [p.relative_to(root).as_posix() for p in c.path(root, 'development/hardware/'+folder).glob('*.json')]
    result += ['development/hardware/selected506a/aruba.json', 'development/hardware/selected506a/ubiquiti.json',
               'development/hardware/selected506b/core.json', 'development/hardware/selected506b/access.json',
               'development/hardware/selected506c/firewalls.json', 'development/hardware/selected506c/edge.json',
               'development/hardware/selected506d/core.json', 'development/hardware/selected506d/edge.json',
               'development/hardware/selected506e/core.json', 'development/hardware/selected506e/edge.json',
               'development/hardware/selected506f/core.json', 'development/hardware/selected506f/edge.json']
    return sorted(result)


def previous_models(root):
    models = []
    for name in prior_names(root):
        data = c.load(c.path(root, name).read_bytes())
        models += data['definitions'] if name.endswith('-v1.json') else [row['definition'] for row in data['models']]
    c.require(len(models) == 678 and sum(bool(model['identity']['manufacturer']) for model in models) == 673,
              'selected506g_baseline_invalid')
    return models


def selected_rows(root, data):
    b.fields(data, 'formatVersion revision models')
    c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
              data['revision'] == REVISION and isinstance(data['models'], list) and len(IDS) == 50 and
              set(MOUNTS) == set(IDS) and len(data['models']) == 50,
              'selected506g_count_invalid')
    selection = c.load(c.path(root, SELECTION).read_bytes())['models']
    chosen = {row['id']: row for row in selection}
    plan = c.load(c.path(root, PLAN).read_bytes())
    c.require(type(plan['formatVersion']) is int and plan['formatVersion'] == 1 and
              plan['revision'] == REVISION and plan['targetSchema'] == 35 and
              plan['baselineDefinitions'] == 678 and plan['baselineCommercial'] == 673 and
              set(plan['authoring']) == {'core', 'edge'} and
              all(isinstance(plan['authoring'][name], list) and len(plan['authoring'][name]) == 25
                  for name in ('core', 'edge')), 'selected506g_assignment_invalid')
    planned = [row['id'] for name in ('core', 'edge') for row in plan['authoring'][name]]
    c.require(len(planned) == len(set(planned)) == 50 and set(planned) == set(IDS),
              'selected506g_assignment_invalid')
    links = c.load(c.path(root, LINKS).read_bytes())
    c.require(len(links['links']) == 7 and
              set(IDS).isdisjoint(row['selectionId'] for row in links['links']),
              'selected506g_previous_model_duplicate')
    c.require(len(chosen) == 506 and set(IDS) <= set(chosen), 'selected506g_selection_invalid')
    rows = [validate_model(row) for row in data['models']]
    c.require(all(group['count'] <= 96 for row in rows for group in row['definition']['groups']),
              'selected506g_runtime_group_limit')
    by_key = {row['definition']['key']: row for row in rows}
    c.require(len(by_key) == len(IDS) and set(by_key) == {'selected-'+identifier for identifier in IDS},
              'selected506g_identity_invalid')
    c.require(len({(row['definition']['identity']['manufacturer'].casefold(),
                    row['definition']['identity']['sku'].casefold()) for row in rows}) == 50,
              'selected506g_duplicate_sku')
    for identifier in IDS:
        definition = by_key['selected-'+identifier]['definition']
        original = chosen[identifier]
        c.require(definition['identity']['manufacturer'] == original['manufacturer'] and
                  definition['identity']['model'] == original['model'] and
                  definition['identity']['sku'].casefold() == SKUS[identifier].casefold(), 'selected506g_model_substitution')
        c.require((definition['kind'], definition['rackUnits']) == MOUNTS[identifier],
                  'selected506g_mount_substitution')
    return sorted(rows, key=lambda row: row['definition']['key'])


def compile_catalog(root):
    names = [*SOURCES, SELECTION, LINKS, PLAN, LOCK, BASE, SHARED, CORE, *TRANSITIVE, TOOL, *prior_names(root)]
    raw = {name: c.path(root, name).read_bytes() for name in names}
    lock = c.load(raw[LOCK])
    c.require(c.sha(raw[LOCK]) == EXPECTED_LOCK_SHA256, 'selected506g_lock_not_reviewed')
    c.require(lock['targetSchema'] == 35 and lock['state'] == STATE and
              lock['sourceSha256'] == {name: c.sha(raw[name]) for name in SOURCES} and
              lock['baseMigrationSha256'] == c.sha(raw[BASE]) and
              lock['sharedCompilerSha256'] == c.sha(raw[SHARED]) and lock['baseEngineSha256'] == c.sha(raw[CORE]) and
              lock['transitiveCompilerSha256'] == {name: c.sha(raw[name]) for name in TRANSITIVE} and
              lock['selectionIds'] == sorted(IDS),
              'selected506g_input_changed')
    c.require(lock['baselineSourceSha256'] == {name: c.sha(raw[name]) for name in prior_names(root)} and
              lock['selectionSha256'] == c.sha(raw[SELECTION]) and lock['planSha256'] == c.sha(raw[PLAN]) and
              lock['profileLinksSha256'] == c.sha(raw[LINKS]),
              'selected506g_baseline_changed')
    combined = dict(formatVersion=1, revision=REVISION, models=[])
    for source, count in zip(SOURCES, COUNTS):
        data = c.load(raw[source])
        b.fields(data, 'formatVersion revision models')
        c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
                  data['revision'] == REVISION and isinstance(data['models'], list) and len(data['models']) == count,
                  'selected506g_source_count_invalid')
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
                  'selected506g_previous_model_duplicate')
        if definition['kind'] == 'desktop':
            c.require(any(parent['kind'] == 'shelf' and any(all(definition['dimensionsMm'][key] <= slot['dimensionsMm'][key]
                      for key in ('width', 'height', 'depth')) for slot in parent['slots']) for parent in old),
                      'selected506g_support_unavailable')
    models = [row['definition'] for row in rows]
    pins = [dict(key=model['key'], revision=model['revision'], sha256=c.sha(c.canonical(model))) for model in models]
    c.require(pins == lock['definitions'], 'selected506g_definition_changed')
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
    server = b.server_source(models).replace(b'Batch50HardwareProfiles', b'Selected506GHardwareProfiles').replace(
        b'build_hardware_batch50.py', b'build_hardware_selected506g.py')
    sql = b'-- Auto-generated selected506g. SQL001-034 and sealed revisions remain unchanged.\n' + b'\n'.join(
        line for line in g.sql_source(models, pins).splitlines() if not line.startswith(b'--')) + b'\n'
    outputs = {SERVER: server, FRONTEND: g.pretty(catalogues), SQL: sql}
    inputs = {name: c.sha(value) for name, value in raw.items()}
    outputs[MANIFEST] = g.pretty(dict(formatVersion=1, targetSchema=35, catalogKey='rackclick-selected506g',
                                     state=STATE, inputs=inputs, files={name: c.sha(value) for name, value in outputs.items()},
                                     selectionIds=sorted(IDS), definitions=pins))
    outputs[TARGETS] = b.targets_source({**inputs, **{name: c.sha(value) for name, value in outputs.items()}}).replace(
        b'VerifyBatch50HardwareCatalog', b'VerifySelected506GHardwareCatalog').replace(b'_Batch50', b'_Selected506G').replace(
        b'batch50_', b'selected506g_').replace(b'build_hardware_batch50.py', b'build_hardware_selected506g.py', 1)
    return outputs


def run(root, write=False):
    b.compile_catalog = compile_catalog
    result = b.run(root, write)
    result.update(targetSchema=35, commercialModels=len(IDS), selectionIds=sorted(IDS))
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
        print(json.dumps(dict(status='failed', code=str(error) if isinstance(error, c.CatalogError) else 'selected506g_io_failed')))
        return 1


if __name__ == '__main__':
    sys.exit(main())
