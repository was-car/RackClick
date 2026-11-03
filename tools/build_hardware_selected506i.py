"""Compile the next five seven-media configurations of usable profiles drawn from the fixed 506-model selection.

Reuses the reviewed catalogue engine without rewriting historical sources.
This compiler publishes only five individually authored configurations.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).absolute().parents[1]
spec = importlib.util.spec_from_file_location('selected506i_private_engine', ROOT/'tools/hardware_physical_v3.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
b = engine.base
c, g = engine.c, engine.g
REVISION = 'selected506i-20261101-v1'
b.REVISION = REVISION
SOURCES = ['development/hardware/selected506i/enterprise.json', 'development/hardware/selected506i/transport.json']
COUNTS = [3, 2]
SELECTION = 'development/hardware/selected-models-506.json'
LINKS = 'development/hardware/selected-profile-links.json'
PLAN = 'evidence/s1-20261101/integracion506i/PLAN-6.json'
LOCK = 'development/hardware/catalog-schema38.lock.json'
BASE = 'development/server/database/037-selected506h-hardware.sql'
SERVER = 'development/server/src/RackClick.Server/Selected506IHardwareProfiles.Generated.cs'
FRONTEND = 'development/frontend/src/hardware-selected506i.generated.json'
SQL = 'development/server/database/038-selected506i-hardware.sql'
MANIFEST = 'development/hardware/catalog-selected506i.manifest.json'
TARGETS = 'development/server/src/RackClick.Server/Selected506IHardware.Generated.targets'
TOOL = 'tools/build_hardware_selected506i.py'
SHARED = 'tools/hardware_physical_v3.py'
CORE = 'tools/build_hardware_batch50.py'
TRANSITIVE = ['tools/hardware_physical_v2.py', 'tools/build_hardware_catalog.py', *['tools/build_hardware_catalog'+str(n)+'.py' for n in range(19, 24)]]
STATE = 'curated_development_not_a_release'
EXPECTED_LOCK_SHA256 = '31dfcdf6fb4a51ed8198753b9039baa9e51ce5afd71f736a119ccedbef83696a'
SKUS = {'palo-alto-pa-5580':'PA-5580','nb-015e42f0df73715b':'FG-3701F','nb-5bbf29fdc1f2fb3c':'02353AES',
    'nb-268313b973eee49c':'170-5171-920','nb-595b36736b9f95f2':'ACX7332',
}
MOUNTS = {'palo-alto-pa-5580':('rack',3),'nb-015e42f0df73715b':('rack',2),'nb-5bbf29fdc1f2fb3c':('rack',1),
    'nb-268313b973eee49c':('rack',2),'nb-595b36736b9f95f2':('rack',3),
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
               'development/hardware/selected506e/core.json', 'development/hardware/selected506e/edge.json',
               'development/hardware/selected506f/core.json', 'development/hardware/selected506f/edge.json',
               'development/hardware/selected506g/core.json', 'development/hardware/selected506g/edge.json',
               'development/hardware/selected506h/aruba.json', 'development/hardware/selected506h/nokia.json']
    return sorted(result)


def previous_models(root):
    models = []
    for name in prior_names(root):
        data = c.load(c.path(root, name).read_bytes())
        models += data['definitions'] if name.endswith('-v1.json') else [row['definition'] for row in data['models']]
    c.require(len(models) == 734 and sum(bool(model['identity']['manufacturer']) for model in models) == 729,
              'selected506i_baseline_invalid')
    return models


def selected_rows(root, data):
    b.fields(data, 'formatVersion revision models')
    c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
              data['revision'] == REVISION and isinstance(data['models'], list) and len(IDS) == 5 and
              set(MOUNTS) == set(IDS) and len(data['models']) == 5,
              'selected506i_count_invalid')
    selection = c.load(c.path(root, SELECTION).read_bytes())['models']
    chosen = {row['id']: row for row in selection}
    plan = c.load(c.path(root, PLAN).read_bytes())
    c.require(type(plan['formatVersion']) is int and plan['formatVersion'] == 1 and
              plan['revision'] == REVISION and plan['targetSchema'] == 38 and
              plan['baselineDefinitions'] == 734 and plan['baselineCommercial'] == 729 and
              plan['baselineSchema'] == 37 and plan['acceptedModels'] == 5 and
              plan['models'] == 5 and len(plan['reservedModels']) == 1 and
              plan['reservedModels'][0]['id'] == 'nb-fd5b5a585af75ae9' and set(plan['physicalTypes']) == set(engine.ALLOWED_TYPES) and
              set(plan['authoring']) == {'enterprise', 'transport'} and
              all(isinstance(plan['authoring'][name], list) and len(plan['authoring'][name]) == {'enterprise': 3, 'transport': 2}[name]
                  for name in ('enterprise', 'transport')), 'selected506i_assignment_invalid')
    planned = [row['id'] for name in ('enterprise', 'transport') for row in plan['authoring'][name]]
    c.require(len(planned) == len(set(planned)) == 5 and set(planned) == set(IDS),
              'selected506i_assignment_invalid')
    links = c.load(c.path(root, LINKS).read_bytes())
    c.require(len(links['links']) == 7 and
              set(IDS).isdisjoint(row['selectionId'] for row in links['links']),
              'selected506i_previous_model_duplicate')
    c.require(len(chosen) == 506 and set(IDS) <= set(chosen), 'selected506i_selection_invalid')
    rows = [validate_model(row) for row in data['models']]
    c.require(all(group['count'] <= 96 for row in rows for group in row['definition']['groups']),
              'selected506i_runtime_group_limit')
    by_key = {row['definition']['key']: row for row in rows}
    c.require(len(by_key) == len(IDS) and set(by_key) == {'selected-'+identifier for identifier in IDS},
              'selected506i_identity_invalid')
    c.require(len({(row['definition']['identity']['manufacturer'].casefold(),
                    row['definition']['identity']['sku'].casefold()) for row in rows}) == 5,
              'selected506i_duplicate_sku')
    for identifier in IDS:
        definition = by_key['selected-'+identifier]['definition']
        original = chosen[identifier]
        c.require(definition['identity']['manufacturer'] == original['manufacturer'] and
                  definition['identity']['model'] == original['model'] and
                  definition['identity']['sku'].casefold() == SKUS[identifier].casefold(), 'selected506i_model_substitution')
        c.require((definition['kind'], definition['rackUnits']) == MOUNTS[identifier],
                  'selected506i_mount_substitution')
    return sorted(rows, key=lambda row: row['definition']['key'])


def compile_catalog(root):
    names = [*SOURCES, SELECTION, LINKS, PLAN, LOCK, BASE, SHARED, CORE, *TRANSITIVE, TOOL, *prior_names(root)]
    raw = {name: c.path(root, name).read_bytes() for name in names}
    lock = c.load(raw[LOCK])
    c.require(c.sha(raw[LOCK]) == EXPECTED_LOCK_SHA256, 'selected506i_lock_not_reviewed')
    c.require(lock['targetSchema'] == 38 and lock['state'] == STATE and
              lock['sourceSha256'] == {name: c.sha(raw[name]) for name in SOURCES} and
              lock['baseMigrationSha256'] == c.sha(raw[BASE]) and
              lock['sharedCompilerSha256'] == c.sha(raw[SHARED]) and lock['baseEngineSha256'] == c.sha(raw[CORE]) and
              lock['transitiveCompilerSha256'] == {name: c.sha(raw[name]) for name in TRANSITIVE} and
              lock['selectionIds'] == sorted(IDS),
              'selected506i_input_changed')
    c.require(lock['baselineSourceSha256'] == {name: c.sha(raw[name]) for name in prior_names(root)} and
              lock['selectionSha256'] == c.sha(raw[SELECTION]) and lock['planSha256'] == c.sha(raw[PLAN]) and
              lock['profileLinksSha256'] == c.sha(raw[LINKS]),
              'selected506i_baseline_changed')
    combined = dict(formatVersion=1, revision=REVISION, models=[])
    for source, count in zip(SOURCES, COUNTS):
        data = c.load(raw[source])
        b.fields(data, 'formatVersion revision models')
        c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
                  data['revision'] == REVISION and isinstance(data['models'], list) and len(data['models']) == count,
                  'selected506i_source_count_invalid')
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
                  'selected506i_previous_model_duplicate')
        if definition['kind'] == 'desktop':
            c.require(any(parent['kind'] == 'shelf' and any(all(definition['dimensionsMm'][key] <= slot['dimensionsMm'][key]
                      for key in ('width', 'height', 'depth')) for slot in parent['slots']) for parent in old),
                      'selected506i_support_unavailable')
    models = [row['definition'] for row in rows]
    pins = [dict(key=model['key'], revision=model['revision'], sha256=c.sha(c.canonical(model))) for model in models]
    c.require(pins == lock['definitions'], 'selected506i_definition_changed')
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
    server = b.server_source(models).replace(b'Batch50HardwareProfiles', b'Selected506IHardwareProfiles').replace(
        b'build_hardware_batch50.py', b'build_hardware_selected506i.py')
    sql = b'-- Auto-generated selected506i. SQL001-037 and sealed revisions remain unchanged.\n' + b'\n'.join(
        line for line in g.sql_source(models, pins).splitlines() if not line.startswith(b'--')) + b'\n'
    outputs = {SERVER: server, FRONTEND: g.pretty(catalogues), SQL: sql}
    inputs = {name: c.sha(value) for name, value in raw.items()}
    outputs[MANIFEST] = g.pretty(dict(formatVersion=1, targetSchema=38, catalogKey='rackclick-selected506i',
                                     state=STATE, inputs=inputs, files={name: c.sha(value) for name, value in outputs.items()},
                                     selectionIds=sorted(IDS), definitions=pins))
    outputs[TARGETS] = b.targets_source({**inputs, **{name: c.sha(value) for name, value in outputs.items()}}).replace(
        b'VerifyBatch50HardwareCatalog', b'VerifySelected506IHardwareCatalog').replace(b'_Batch50', b'_Selected506I').replace(
        b'batch50_', b'selected506i_').replace(b'build_hardware_batch50.py', b'build_hardware_selected506i.py', 1)
    return outputs


def run(root, write=False):
    b.compile_catalog = compile_catalog
    result = b.run(root, write)
    result.update(targetSchema=38, commercialModels=len(IDS), selectionIds=sorted(IDS))
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
        print(json.dumps(dict(status='failed', code=str(error) if isinstance(error, c.CatalogError) else 'selected506i_io_failed')))
        return 1


if __name__ == '__main__':
    sys.exit(main())
