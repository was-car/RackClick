"""Compile the fourth group of usable profiles drawn from the fixed 506-model selection.

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
spec = importlib.util.spec_from_file_location('selected506d_private_engine', ROOT/'tools/hardware_physical_v2.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
b = engine.base
c, g = engine.c, engine.g
REVISION = 'selected506d-20261101-v1'
b.REVISION = REVISION
SOURCES = ['development/hardware/selected506d/core.json', 'development/hardware/selected506d/edge.json']
COUNTS = [25, 25]
SELECTION = 'development/hardware/selected-models-506.json'
LINKS = 'development/hardware/selected-profile-links.json'
PLAN = 'evidence/s1-20261101/integracion506d/PLAN-50.json'
LOCK = 'development/hardware/catalog-schema32.lock.json'
BASE = 'development/server/database/031-selected506c-hardware.sql'
SERVER = 'development/server/src/RackClick.Server/Selected506DHardwareProfiles.Generated.cs'
FRONTEND = 'development/frontend/src/hardware-selected506d.generated.json'
SQL = 'development/server/database/032-selected506d-hardware.sql'
MANIFEST = 'development/hardware/catalog-selected506d.manifest.json'
TARGETS = 'development/server/src/RackClick.Server/Selected506DHardware.Generated.targets'
TOOL = 'tools/build_hardware_selected506d.py'
SHARED = 'tools/hardware_physical_v2.py'
CORE = 'tools/build_hardware_batch50.py'
TRANSITIVE = ['tools/build_hardware_catalog.py', *['tools/build_hardware_catalog'+str(n)+'.py' for n in range(19, 24)]]
STATE = 'curated_development_not_a_release'
EXPECTED_LOCK_SHA256 = 'bc4184da04a58e1f0dee753eb92ef979ffd3f64a00580dcffb0505d8ac8f7fd3'
SKUS = {
    'nb-1e541b78ab2e12a9': 'DCS-7160-48YC6-F',
    'nb-22b5637a0a90560a': 'DCS-7050CX3-32C-F',
    'nb-40628e190c9e9ada': 'DCS-7050SX3-48YC8-F',
    'nb-8a9952b05c0840d1': 'DCS-7280SR3-48YC8-F',
    'nb-99fbabbfd63a81ae': 'DCS-7050CX3-32S-R',
    'nb-a4126d6cef91ca26': 'DCS-7020SR-24C2-F',
    'nb-f0851cec3521e33f': 'DCS-7060CX2-32S-F',
    'nb-0981324ffcccabc6': 'CCS-720DF-48Y-2F',
    'nb-a02305d3072dc01b': 'CCS-720XP-24Y6-2F',
    'nb-4c713694453b3ee3': 'N9K-C93108TC-FX3',
    'nb-5cfeedda20abb6ba': 'N9K-C9336C-FX2',
    'nb-77e3ae7a8fab715b': 'C9500-24Y4C',
    'nb-b93fdf2565924f3e': 'C9500-48Y4C',
    'nb-c3a2a8dfb0d28694': 'N9K-C93180YC-FX',
    'nb-6ba786cfed3ab9a5': 'MS350-24P-HW',
    'nb-e83c62d66ebe38fa': 'MS225-48FP-HW',
    'nb-8f68dd201f3c0c5e': 'C9300X-24Y',
    'nb-56979e7752a9d231': 'QFX5120-48Y-AFI2',
    'nb-68e3c1e22fd81ed1': 'EX4400-48F',
    'nb-f0537901a8b1edc9': 'QFX5100-48S-6Q',
    'nb-f6e0bb626755510b': 'EX4100-48P',
    'nb-01d2c09685f7b01f': 'EX3400-48T',
    'nb-9960b794c01f49b4': 'EX3400-48P',
    'nb-9af4f14b030fd0a3': 'ACX7024-AC',
    'nb-56ae91b8f6b2852d': 'MX204',
    'nb-2b0409c6beac1731': 'ECS-Aggregation',
    'nb-41262e318167a929': 'n5860-48sc',
    'nb-4d5610318b7474da': '16790',
    'nb-58601e584ebb26d1': 'S6730-S24X6Q',
    'nb-61497bf34bd5fcfd': 'S4128F-ON',
    'nb-6d4a191cda45f6d1': 'X695-48Y-8C',
    'nb-78642bb08e8fc74c': 'FG-3001F',
    'nb-9d2017e0aa6f2f3c': 'N3248P-ON',
    'nb-a864e7299035e225': 'S6730-H24X4Y4C',
    'nb-d827296bb530c875': 'CCR2216-1G-12XS-2XQ',
    'nb-e043a5a21e4bc6c2': 'EFG',
    'nb-e5b040471a978eae': 'FG-1000F',
    'nb-e98baee54dcf5404': 'n8560-48bc',
    'nb-f48a3b395614b14f': 'FG-2600F',
    'nb-fe00cb2fcd751efc': '4120-24MW-4Y',
    'palo-alto-pa-3260': 'PA-3260',
    'palo-alto-pa-3410': 'PA-3410',
    'palo-alto-pa-3420': 'PA-3420',
    'palo-alto-pa-3430': 'PA-3430',
    'palo-alto-pa-3440': 'PA-3440',
    'palo-alto-pa-5260': 'PA-5260',
    'palo-alto-pa-5410': 'PA-5410',
    'palo-alto-pa-5420': 'PA-5420',
    'palo-alto-pa-5430': 'PA-5430',
    'palo-alto-pa-5440': 'PA-5440',
}
MOUNTS = {
    'nb-1e541b78ab2e12a9': ('rack', 1),
    'nb-22b5637a0a90560a': ('rack', 1),
    'nb-40628e190c9e9ada': ('rack', 1),
    'nb-8a9952b05c0840d1': ('rack', 1),
    'nb-99fbabbfd63a81ae': ('rack', 1),
    'nb-a4126d6cef91ca26': ('rack', 1),
    'nb-f0851cec3521e33f': ('rack', 1),
    'nb-0981324ffcccabc6': ('rack', 1),
    'nb-a02305d3072dc01b': ('rack', 1),
    'nb-4c713694453b3ee3': ('rack', 1),
    'nb-5cfeedda20abb6ba': ('rack', 1),
    'nb-77e3ae7a8fab715b': ('rack', 1),
    'nb-b93fdf2565924f3e': ('rack', 1),
    'nb-c3a2a8dfb0d28694': ('rack', 1),
    'nb-6ba786cfed3ab9a5': ('rack', 1),
    'nb-e83c62d66ebe38fa': ('rack', 1),
    'nb-8f68dd201f3c0c5e': ('rack', 1),
    'nb-56979e7752a9d231': ('rack', 1),
    'nb-68e3c1e22fd81ed1': ('rack', 1),
    'nb-f0537901a8b1edc9': ('rack', 1),
    'nb-f6e0bb626755510b': ('rack', 1),
    'nb-01d2c09685f7b01f': ('rack', 1),
    'nb-9960b794c01f49b4': ('rack', 1),
    'nb-9af4f14b030fd0a3': ('rack', 1),
    'nb-56ae91b8f6b2852d': ('rack', 1),
    'nb-2b0409c6beac1731': ('rack', 1),
    'nb-41262e318167a929': ('rack', 1),
    'nb-4d5610318b7474da': ('rack', 1),
    'nb-58601e584ebb26d1': ('rack', 1),
    'nb-61497bf34bd5fcfd': ('rack', 1),
    'nb-6d4a191cda45f6d1': ('rack', 1),
    'nb-78642bb08e8fc74c': ('rack', 2),
    'nb-9d2017e0aa6f2f3c': ('rack', 1),
    'nb-a864e7299035e225': ('rack', 1),
    'nb-d827296bb530c875': ('rack', 1),
    'nb-e043a5a21e4bc6c2': ('rack', 1),
    'nb-e5b040471a978eae': ('rack', 2),
    'nb-e98baee54dcf5404': ('rack', 1),
    'nb-f48a3b395614b14f': ('rack', 2),
    'nb-fe00cb2fcd751efc': ('rack', 1),
    'palo-alto-pa-3260': ('rack', 2),
    'palo-alto-pa-3410': ('rack', 1),
    'palo-alto-pa-3420': ('rack', 1),
    'palo-alto-pa-3430': ('rack', 1),
    'palo-alto-pa-3440': ('rack', 1),
    'palo-alto-pa-5260': ('rack', 3),
    'palo-alto-pa-5410': ('rack', 2),
    'palo-alto-pa-5420': ('rack', 2),
    'palo-alto-pa-5430': ('rack', 2),
    'palo-alto-pa-5440': ('rack', 2),
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
               'development/hardware/selected506c/firewalls.json', 'development/hardware/selected506c/edge.json']
    return sorted(result)


def previous_models(root):
    models = []
    for name in prior_names(root):
        data = c.load(c.path(root, name).read_bytes())
        models += data['definitions'] if name.endswith('-v1.json') else [row['definition'] for row in data['models']]
    c.require(len(models) == 528 and sum(bool(model['identity']['manufacturer']) for model in models) == 523,
              'selected506d_baseline_invalid')
    return models


def selected_rows(root, data):
    b.fields(data, 'formatVersion revision models')
    c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
              data['revision'] == REVISION and isinstance(data['models'], list) and len(IDS) == 50 and
              set(MOUNTS) == set(IDS) and len(data['models']) == 50,
              'selected506d_count_invalid')
    selection = c.load(c.path(root, SELECTION).read_bytes())['models']
    chosen = {row['id']: row for row in selection}
    plan = c.load(c.path(root, PLAN).read_bytes())
    c.require(type(plan['formatVersion']) is int and plan['formatVersion'] == 1 and
              plan['revision'] == REVISION and plan['targetSchema'] == 32 and
              plan['baselineDefinitions'] == 528 and plan['baselineCommercial'] == 523 and
              set(plan['authoring']) == {'core', 'edge'} and
              all(isinstance(plan['authoring'][name], list) and len(plan['authoring'][name]) == 25
                  for name in ('core', 'edge')), 'selected506d_assignment_invalid')
    planned = [row['id'] for name in ('core', 'edge') for row in plan['authoring'][name]]
    c.require(len(planned) == len(set(planned)) == 50 and set(planned) == set(IDS),
              'selected506d_assignment_invalid')
    links = c.load(c.path(root, LINKS).read_bytes())
    c.require(len(links['links']) == 7 and
              set(IDS).isdisjoint(row['selectionId'] for row in links['links']),
              'selected506d_previous_model_duplicate')
    c.require(len(chosen) == 506 and set(IDS) <= set(chosen), 'selected506d_selection_invalid')
    rows = [validate_model(row) for row in data['models']]
    c.require(all(group['count'] <= 96 for row in rows for group in row['definition']['groups']),
              'selected506d_runtime_group_limit')
    by_key = {row['definition']['key']: row for row in rows}
    c.require(len(by_key) == len(IDS) and set(by_key) == {'selected-'+identifier for identifier in IDS},
              'selected506d_identity_invalid')
    c.require(len({(row['definition']['identity']['manufacturer'].casefold(),
                    row['definition']['identity']['sku'].casefold()) for row in rows}) == 50,
              'selected506d_duplicate_sku')
    for identifier in IDS:
        definition = by_key['selected-'+identifier]['definition']
        original = chosen[identifier]
        c.require(definition['identity']['manufacturer'] == original['manufacturer'] and
                  definition['identity']['model'] == original['model'] and
                  definition['identity']['sku'].casefold() == SKUS[identifier].casefold(), 'selected506d_model_substitution')
        c.require((definition['kind'], definition['rackUnits']) == MOUNTS[identifier],
                  'selected506d_mount_substitution')
    return sorted(rows, key=lambda row: row['definition']['key'])


def compile_catalog(root):
    names = [*SOURCES, SELECTION, LINKS, PLAN, LOCK, BASE, SHARED, CORE, *TRANSITIVE, TOOL, *prior_names(root)]
    raw = {name: c.path(root, name).read_bytes() for name in names}
    lock = c.load(raw[LOCK])
    c.require(c.sha(raw[LOCK]) == EXPECTED_LOCK_SHA256, 'selected506d_lock_not_reviewed')
    c.require(lock['targetSchema'] == 32 and lock['state'] == STATE and
              lock['sourceSha256'] == {name: c.sha(raw[name]) for name in SOURCES} and
              lock['baseMigrationSha256'] == c.sha(raw[BASE]) and
              lock['sharedCompilerSha256'] == c.sha(raw[SHARED]) and lock['baseEngineSha256'] == c.sha(raw[CORE]) and
              lock['transitiveCompilerSha256'] == {name: c.sha(raw[name]) for name in TRANSITIVE} and
              lock['selectionIds'] == sorted(IDS),
              'selected506d_input_changed')
    c.require(lock['baselineSourceSha256'] == {name: c.sha(raw[name]) for name in prior_names(root)} and
              lock['selectionSha256'] == c.sha(raw[SELECTION]) and lock['planSha256'] == c.sha(raw[PLAN]) and
              lock['profileLinksSha256'] == c.sha(raw[LINKS]),
              'selected506d_baseline_changed')
    combined = dict(formatVersion=1, revision=REVISION, models=[])
    for source, count in zip(SOURCES, COUNTS):
        data = c.load(raw[source])
        b.fields(data, 'formatVersion revision models')
        c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
                  data['revision'] == REVISION and isinstance(data['models'], list) and len(data['models']) == count,
                  'selected506d_source_count_invalid')
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
                  'selected506d_previous_model_duplicate')
        if definition['kind'] == 'desktop':
            c.require(any(parent['kind'] == 'shelf' and any(all(definition['dimensionsMm'][key] <= slot['dimensionsMm'][key]
                      for key in ('width', 'height', 'depth')) for slot in parent['slots']) for parent in old),
                      'selected506d_support_unavailable')
    models = [row['definition'] for row in rows]
    pins = [dict(key=model['key'], revision=model['revision'], sha256=c.sha(c.canonical(model))) for model in models]
    c.require(pins == lock['definitions'], 'selected506d_definition_changed')
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
    server = b.server_source(models).replace(b'Batch50HardwareProfiles', b'Selected506DHardwareProfiles').replace(
        b'build_hardware_batch50.py', b'build_hardware_selected506d.py')
    sql = (b'-- Auto-generated selected506d. SQL001-031 and sealed revisions remain unchanged.\n'
           b'ALTER TABLE hardware_group_template DROP CONSTRAINT hardware_group_template_type_check;\n'
           b"ALTER TABLE hardware_group_template ADD CONSTRAINT hardware_group_template_type_check CHECK(type IN ('rj45','sfp','sfp28','qsfp','power'));\n") + b'\n'.join(
        line for line in g.sql_source(models, pins).splitlines() if not line.startswith(b'--')) + b'\n'
    outputs = {SERVER: server, FRONTEND: g.pretty(catalogues), SQL: sql}
    inputs = {name: c.sha(value) for name, value in raw.items()}
    outputs[MANIFEST] = g.pretty(dict(formatVersion=1, targetSchema=32, catalogKey='rackclick-selected506d',
                                     state=STATE, inputs=inputs, files={name: c.sha(value) for name, value in outputs.items()},
                                     selectionIds=sorted(IDS), definitions=pins))
    outputs[TARGETS] = b.targets_source({**inputs, **{name: c.sha(value) for name, value in outputs.items()}}).replace(
        b'VerifyBatch50HardwareCatalog', b'VerifySelected506DHardwareCatalog').replace(b'_Batch50', b'_Selected506D').replace(
        b'batch50_', b'selected506d_').replace(b'build_hardware_batch50.py', b'build_hardware_selected506d.py', 1)
    return outputs


def run(root, write=False):
    b.compile_catalog = compile_catalog
    result = b.run(root, write)
    result.update(targetSchema=32, commercialModels=len(IDS), selectionIds=sorted(IDS))
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
        print(json.dumps(dict(status='failed', code=str(error) if isinstance(error, c.CatalogError) else 'selected506d_io_failed')))
        return 1


if __name__ == '__main__':
    sys.exit(main())
