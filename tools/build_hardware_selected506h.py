"""Compile the first six seven-media configurations of usable profiles drawn from the fixed 506-model selection.

Reuses the reviewed catalogue engine without rewriting historical sources.
This compiler publishes only six individually authored configurations.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).absolute().parents[1]
spec = importlib.util.spec_from_file_location('selected506h_private_engine', ROOT/'tools/hardware_physical_v3.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
b = engine.base
c, g = engine.c, engine.g
REVISION = 'selected506h-20261101-v1'
b.REVISION = REVISION
SOURCES = ['development/hardware/selected506h/aruba.json', 'development/hardware/selected506h/nokia.json']
COUNTS = [3, 3]
SELECTION = 'development/hardware/selected-models-506.json'
LINKS = 'development/hardware/selected-profile-links.json'
PLAN = 'evidence/s1-20261101/integracion506h/PLAN-6.json'
LOCK = 'development/hardware/catalog-schema37.lock.json'
BASE = 'development/server/database/036-physical-media.sql'
SERVER = 'development/server/src/RackClick.Server/Selected506HHardwareProfiles.Generated.cs'
FRONTEND = 'development/frontend/src/hardware-selected506h.generated.json'
SQL = 'development/server/database/037-selected506h-hardware.sql'
MANIFEST = 'development/hardware/catalog-selected506h.manifest.json'
TARGETS = 'development/server/src/RackClick.Server/Selected506HHardware.Generated.targets'
TOOL = 'tools/build_hardware_selected506h.py'
SHARED = 'tools/hardware_physical_v3.py'
CORE = 'tools/build_hardware_batch50.py'
TRANSITIVE = ['tools/hardware_physical_v2.py', 'tools/build_hardware_catalog.py', *['tools/build_hardware_catalog'+str(n)+'.py' for n in range(19, 24)]]
STATE = 'curated_development_not_a_release'
EXPECTED_LOCK_SHA256 = 'bcbb6ebae7b1fe61fae8602fc688a081ea9ef7955056a8310c68e36f957afbc7'
SKUS = {'nb-086e891acea2817b': 'JL668A', 'nb-51dcd09a4e5de9b0': 'JL665A', 'nb-460527db3780ce3d': 'JL664A', 'nb-14eb45daaa9298fa': '3HE16425AA', 'nb-dbb1fdc53d9b42a1': '3HE19313AA', 'nb-f9014eaa7cd819dc': '3HE17750AA'}
MOUNTS = {'nb-086e891acea2817b': ('rack', 1), 'nb-51dcd09a4e5de9b0': ('rack', 1), 'nb-460527db3780ce3d': ('rack', 1), 'nb-14eb45daaa9298fa': ('rack', 1), 'nb-dbb1fdc53d9b42a1': ('rack', 1), 'nb-f9014eaa7cd819dc': ('rack', 2)}
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
               'development/hardware/selected506g/core.json', 'development/hardware/selected506g/edge.json']
    return sorted(result)


def previous_models(root):
    models = []
    for name in prior_names(root):
        data = c.load(c.path(root, name).read_bytes())
        models += data['definitions'] if name.endswith('-v1.json') else [row['definition'] for row in data['models']]
    c.require(len(models) == 728 and sum(bool(model['identity']['manufacturer']) for model in models) == 723,
              'selected506h_baseline_invalid')
    return models


def selected_rows(root, data):
    b.fields(data, 'formatVersion revision models')
    c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
              data['revision'] == REVISION and isinstance(data['models'], list) and len(IDS) == 6 and
              set(MOUNTS) == set(IDS) and len(data['models']) == 6,
              'selected506h_count_invalid')
    selection = c.load(c.path(root, SELECTION).read_bytes())['models']
    chosen = {row['id']: row for row in selection}
    plan = c.load(c.path(root, PLAN).read_bytes())
    c.require(type(plan['formatVersion']) is int and plan['formatVersion'] == 1 and
              plan['revision'] == REVISION and plan['targetSchema'] == 37 and
              plan['baselineDefinitions'] == 728 and plan['baselineCommercial'] == 723 and
              plan['baselineSchema'] == 36 and set(plan['physicalTypes']) == set(engine.ALLOWED_TYPES) and
              set(plan['authoring']) == {'aruba', 'nokia'} and
              all(isinstance(plan['authoring'][name], list) and len(plan['authoring'][name]) == 3
                  for name in ('aruba', 'nokia')), 'selected506h_assignment_invalid')
    planned = [row['id'] for name in ('aruba', 'nokia') for row in plan['authoring'][name]]
    c.require(len(planned) == len(set(planned)) == 6 and set(planned) == set(IDS),
              'selected506h_assignment_invalid')
    links = c.load(c.path(root, LINKS).read_bytes())
    c.require(len(links['links']) == 7 and
              set(IDS).isdisjoint(row['selectionId'] for row in links['links']),
              'selected506h_previous_model_duplicate')
    c.require(len(chosen) == 506 and set(IDS) <= set(chosen), 'selected506h_selection_invalid')
    rows = [validate_model(row) for row in data['models']]
    c.require(all(group['count'] <= 96 for row in rows for group in row['definition']['groups']),
              'selected506h_runtime_group_limit')
    by_key = {row['definition']['key']: row for row in rows}
    c.require(len(by_key) == len(IDS) and set(by_key) == {'selected-'+identifier for identifier in IDS},
              'selected506h_identity_invalid')
    c.require(len({(row['definition']['identity']['manufacturer'].casefold(),
                    row['definition']['identity']['sku'].casefold()) for row in rows}) == 6,
              'selected506h_duplicate_sku')
    for identifier in IDS:
        definition = by_key['selected-'+identifier]['definition']
        original = chosen[identifier]
        c.require(definition['identity']['manufacturer'] == original['manufacturer'] and
                  definition['identity']['model'] == original['model'] and
                  definition['identity']['sku'].casefold() == SKUS[identifier].casefold(), 'selected506h_model_substitution')
        c.require((definition['kind'], definition['rackUnits']) == MOUNTS[identifier],
                  'selected506h_mount_substitution')
    return sorted(rows, key=lambda row: row['definition']['key'])


def compile_catalog(root):
    names = [*SOURCES, SELECTION, LINKS, PLAN, LOCK, BASE, SHARED, CORE, *TRANSITIVE, TOOL, *prior_names(root)]
    raw = {name: c.path(root, name).read_bytes() for name in names}
    lock = c.load(raw[LOCK])
    c.require(c.sha(raw[LOCK]) == EXPECTED_LOCK_SHA256, 'selected506h_lock_not_reviewed')
    c.require(lock['targetSchema'] == 37 and lock['state'] == STATE and
              lock['sourceSha256'] == {name: c.sha(raw[name]) for name in SOURCES} and
              lock['baseMigrationSha256'] == c.sha(raw[BASE]) and
              lock['sharedCompilerSha256'] == c.sha(raw[SHARED]) and lock['baseEngineSha256'] == c.sha(raw[CORE]) and
              lock['transitiveCompilerSha256'] == {name: c.sha(raw[name]) for name in TRANSITIVE} and
              lock['selectionIds'] == sorted(IDS),
              'selected506h_input_changed')
    c.require(lock['baselineSourceSha256'] == {name: c.sha(raw[name]) for name in prior_names(root)} and
              lock['selectionSha256'] == c.sha(raw[SELECTION]) and lock['planSha256'] == c.sha(raw[PLAN]) and
              lock['profileLinksSha256'] == c.sha(raw[LINKS]),
              'selected506h_baseline_changed')
    combined = dict(formatVersion=1, revision=REVISION, models=[])
    for source, count in zip(SOURCES, COUNTS):
        data = c.load(raw[source])
        b.fields(data, 'formatVersion revision models')
        c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
                  data['revision'] == REVISION and isinstance(data['models'], list) and len(data['models']) == count,
                  'selected506h_source_count_invalid')
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
                  'selected506h_previous_model_duplicate')
        if definition['kind'] == 'desktop':
            c.require(any(parent['kind'] == 'shelf' and any(all(definition['dimensionsMm'][key] <= slot['dimensionsMm'][key]
                      for key in ('width', 'height', 'depth')) for slot in parent['slots']) for parent in old),
                      'selected506h_support_unavailable')
    models = [row['definition'] for row in rows]
    pins = [dict(key=model['key'], revision=model['revision'], sha256=c.sha(c.canonical(model))) for model in models]
    c.require(pins == lock['definitions'], 'selected506h_definition_changed')
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
    server = b.server_source(models).replace(b'Batch50HardwareProfiles', b'Selected506HHardwareProfiles').replace(
        b'build_hardware_batch50.py', b'build_hardware_selected506h.py')
    sql = b'-- Auto-generated selected506h. SQL001-036 and sealed revisions remain unchanged.\n' + b'\n'.join(
        line for line in g.sql_source(models, pins).splitlines() if not line.startswith(b'--')) + b'\n'
    outputs = {SERVER: server, FRONTEND: g.pretty(catalogues), SQL: sql}
    inputs = {name: c.sha(value) for name, value in raw.items()}
    outputs[MANIFEST] = g.pretty(dict(formatVersion=1, targetSchema=37, catalogKey='rackclick-selected506h',
                                     state=STATE, inputs=inputs, files={name: c.sha(value) for name, value in outputs.items()},
                                     selectionIds=sorted(IDS), definitions=pins))
    outputs[TARGETS] = b.targets_source({**inputs, **{name: c.sha(value) for name, value in outputs.items()}}).replace(
        b'VerifyBatch50HardwareCatalog', b'VerifySelected506HHardwareCatalog').replace(b'_Batch50', b'_Selected506H').replace(
        b'batch50_', b'selected506h_').replace(b'build_hardware_batch50.py', b'build_hardware_selected506h.py', 1)
    return outputs


def run(root, write=False):
    b.compile_catalog = compile_catalog
    result = b.run(root, write)
    result.update(targetSchema=37, commercialModels=len(IDS), selectionIds=sorted(IDS))
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
        print(json.dumps(dict(status='failed', code=str(error) if isinstance(error, c.CatalogError) else 'selected506h_io_failed')))
        return 1


if __name__ == '__main__':
    sys.exit(main())
