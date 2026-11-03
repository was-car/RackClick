"""Compile the first usable profiles drawn from the fixed 506-model selection.

Reuses the reviewed catalogue engine without rewriting historical sources.
This compiler publishes only seventeen individually authored configurations.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).absolute().parents[1]
spec = importlib.util.spec_from_file_location('selected506a_private_engine', ROOT/'tools/build_hardware_batch50.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
c, g = b.c, b.g
REVISION = 'selected506a-20261101-v1'
b.REVISION = REVISION
SOURCES = ['development/hardware/selected506a/aruba.json', 'development/hardware/selected506a/ubiquiti.json']
COUNTS = [12, 5]
SELECTION = 'development/hardware/selected-models-506.json'
PLAN = 'development/hardware/selection462/plan.json'
LOCK = 'development/hardware/catalog-schema29.lock.json'
BASE = 'development/server/database/028-batch100c-hardware.sql'
SERVER = 'development/server/src/RackClick.Server/Selected506AHardwareProfiles.Generated.cs'
FRONTEND = 'development/frontend/src/hardware-selected506a.generated.json'
SQL = 'development/server/database/029-selected506a-hardware.sql'
MANIFEST = 'development/hardware/catalog-selected506a.manifest.json'
TARGETS = 'development/server/src/RackClick.Server/Selected506AHardware.Generated.targets'
TOOL = 'tools/build_hardware_selected506a.py'
SHARED = 'tools/build_hardware_batch50.py'
STATE = 'curated_development_not_a_release'
EXPECTED_LOCK_SHA256 = '63a3575af2fb7e24adeef032b274704c2570b14b159abc98f232ea7a09e35e1d'
IDS = ('aruba-jl675a', 'aruba-r9y04a', 'nb-7b81ceb62353c88e', 'nb-90ee2ca04fd0e2d5',
       'nb-f505dfd941515251', 'nb-842ab89f3df610f2', 'nb-4f13830c6517574d', 'nb-a77e3ed47a30e394',
       'nb-adf2142c84f07df9', 'nb-f6915d5d3881b84d', 'nb-b331c13345891559', 'nb-3af5a2fcbefac97c',
       'nb-0c303ce9bca6c601', 'nb-d064231ab7e45734', 'nb-e5030fe747d79fe6', 'nb-eaa7b5f1797fad5b', 'nb-f83ce1b7723518c4')
SKUS = {'aruba-jl675a':'JL675A', 'aruba-r9y04a':'R9Y04A', 'nb-3af5a2fcbefac97c':'JL679A',
        'nb-4f13830c6517574d':'R9Y03A', 'nb-7b81ceb62353c88e':'R8N88A', 'nb-842ab89f3df610f2':'R8N85A',
        'nb-90ee2ca04fd0e2d5':'R8N87A', 'nb-a77e3ed47a30e394':'R8N89A', 'nb-adf2142c84f07df9':'JL676A',
        'nb-b331c13345891559':'JL677A', 'nb-f505dfd941515251':'R8N86A', 'nb-f6915d5d3881b84d':'JL678A',
        'nb-0c303ce9bca6c601':'USW-Enterprise-24-PoE', 'nb-d064231ab7e45734':'USW-Pro-48-PoE',
        'nb-e5030fe747d79fe6':'USW-Pro-24-PoE', 'nb-eaa7b5f1797fad5b':'USW-Pro-Max-24-PoE',
        'nb-f83ce1b7723518c4':'USW-Pro-Max-48-PoE'}


def prior_names(root):
    result = [p.relative_to(root).as_posix() for p in c.path(root, 'development/hardware').glob('catalog-*-v1.json')]
    for folder in ('batch50', 'batch50b', 'batch100', 'batch100b', 'batch100c'):
        result += [p.relative_to(root).as_posix() for p in c.path(root, 'development/hardware/'+folder).glob('*.json')]
    return sorted(result)


def previous_models(root):
    models = []
    for name in prior_names(root):
        data = c.load(c.path(root, name).read_bytes())
        models += data['definitions'] if name.endswith('-v1.json') else [row['definition'] for row in data['models']]
    c.require(len(models) == 411, 'selected506a_baseline_invalid')
    return models


def selected_rows(root, data):
    b.fields(data, 'formatVersion revision models')
    c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
              data['revision'] == REVISION and isinstance(data['models'], list) and len(data['models']) == len(IDS),
              'selected506a_count_invalid')
    selection = c.load(c.path(root, SELECTION).read_bytes())['models']
    chosen = {row['id']: row for row in selection}
    c.require(len(chosen) == 506 and set(IDS) <= set(chosen), 'selected506a_selection_invalid')
    rows = [b.validate_model(row) for row in data['models']]
    by_key = {row['definition']['key']: row for row in rows}
    c.require(len(by_key) == len(IDS) and set(by_key) == {'selected-'+identifier for identifier in IDS},
              'selected506a_identity_invalid')
    for identifier in IDS:
        definition = by_key['selected-'+identifier]['definition']
        original = chosen[identifier]
        c.require(definition['identity']['manufacturer'] == original['manufacturer'] and
                  definition['identity']['model'] == original['model'] and
                  definition['identity']['sku'].casefold() == SKUS[identifier].casefold(), 'selected506a_model_substitution')
    return sorted(rows, key=lambda row: row['definition']['key'])


def compile_catalog(root):
    names = [*SOURCES, SELECTION, PLAN, LOCK, BASE, SHARED, TOOL, *prior_names(root)]
    raw = {name: c.path(root, name).read_bytes() for name in names}
    lock = c.load(raw[LOCK])
    c.require(c.sha(raw[LOCK]) == EXPECTED_LOCK_SHA256, 'selected506a_lock_not_reviewed')
    c.require(lock['targetSchema'] == 29 and lock['state'] == STATE and
              lock['sourceSha256'] == {name: c.sha(raw[name]) for name in SOURCES} and
              lock['baseMigrationSha256'] == c.sha(raw[BASE]) and
              lock['sharedCompilerSha256'] == c.sha(raw[SHARED]) and lock['selectionIds'] == sorted(IDS),
              'selected506a_input_changed')
    combined = dict(formatVersion=1, revision=REVISION, models=[])
    for source, count in zip(SOURCES, COUNTS):
        data = c.load(raw[source])
        b.fields(data, 'formatVersion revision models')
        c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
                  data['revision'] == REVISION and isinstance(data['models'], list) and len(data['models']) == count,
                  'selected506a_source_count_invalid')
        combined['models'] += data['models']
    rows = selected_rows(root, combined)
    old = previous_models(root)
    keys = {model['key'] for model in old}
    identities = {(model['identity']['manufacturer'], model['identity']['model']) for model in old}
    for row in rows:
        definition = row['definition']
        c.require(definition['key'] not in keys and
                  (definition['identity']['manufacturer'], definition['identity']['model']) not in identities,
                  'selected506a_previous_model_duplicate')
        if definition['kind'] == 'desktop':
            c.require(any(parent['kind'] == 'shelf' and any(all(definition['dimensionsMm'][key] <= slot['dimensionsMm'][key]
                      for key in ('width', 'height', 'depth')) for slot in parent['slots']) for parent in old),
                      'selected506a_support_unavailable')
    models = [row['definition'] for row in rows]
    pins = [dict(key=model['key'], revision=model['revision'], sha256=c.sha(c.canonical(model))) for model in models]
    c.require(pins == lock['definitions'], 'selected506a_definition_changed')
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
    server = b.server_source(models).replace(b'Batch50HardwareProfiles', b'Selected506AHardwareProfiles').replace(
        b'build_hardware_batch50.py', b'build_hardware_selected506a.py')
    sql = b'-- Auto-generated selected506a. SQL001-028 and sealed revisions remain unchanged.\n' + b'\n'.join(
        line for line in g.sql_source(models, pins).splitlines() if not line.startswith(b'--')) + b'\n'
    outputs = {SERVER: server, FRONTEND: g.pretty(catalogues), SQL: sql}
    inputs = {name: c.sha(value) for name, value in raw.items()}
    outputs[MANIFEST] = g.pretty(dict(formatVersion=1, targetSchema=29, catalogKey='rackclick-selected506a',
                                     state=STATE, inputs=inputs, files={name: c.sha(value) for name, value in outputs.items()},
                                     selectionIds=sorted(IDS), definitions=pins))
    outputs[TARGETS] = b.targets_source({**inputs, **{name: c.sha(value) for name, value in outputs.items()}}).replace(
        b'VerifyBatch50HardwareCatalog', b'VerifySelected506AHardwareCatalog').replace(b'_Batch50', b'_Selected506A').replace(
        b'batch50_', b'selected506a_').replace(b'build_hardware_batch50.py', b'build_hardware_selected506a.py', 1)
    return outputs


def run(root, write=False):
    b.compile_catalog = compile_catalog
    result = b.run(root, write)
    result.update(targetSchema=29, commercialModels=len(IDS), selectionIds=sorted(IDS))
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
        print(json.dumps(dict(status='failed', code=str(error) if isinstance(error, c.CatalogError) else 'selected506a_io_failed')))
        return 1


if __name__ == '__main__':
    sys.exit(main())
