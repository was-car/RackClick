"""Compile the second group of usable profiles drawn from the fixed 506-model selection.

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
spec = importlib.util.spec_from_file_location('selected506b_private_engine', ROOT/'tools/build_hardware_batch50.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
c, g = b.c, b.g
REVISION = 'selected506b-20261101-v1'
b.REVISION = REVISION
SOURCES = ['development/hardware/selected506b/core.json', 'development/hardware/selected506b/access.json']
COUNTS = [25, 25]
SELECTION = 'development/hardware/selected-models-506.json'
PLAN = 'development/hardware/selection462/plan.json'
LOCK = 'development/hardware/catalog-schema30.lock.json'
BASE = 'development/server/database/029-selected506a-hardware.sql'
SERVER = 'development/server/src/RackClick.Server/Selected506BHardwareProfiles.Generated.cs'
FRONTEND = 'development/frontend/src/hardware-selected506b.generated.json'
SQL = 'development/server/database/030-selected506b-hardware.sql'
MANIFEST = 'development/hardware/catalog-selected506b.manifest.json'
TARGETS = 'development/server/src/RackClick.Server/Selected506BHardware.Generated.targets'
TOOL = 'tools/build_hardware_selected506b.py'
SHARED = 'tools/build_hardware_batch50.py'
STATE = 'curated_development_not_a_release'
EXPECTED_LOCK_SHA256 = '75dc43bc9877c70301250ee432e3d72f098ce2d04ec6044290c938fb2fb978ea'
SKUS = {
    'nb-be67a5901b5f1fb8': 'C1300-48P-4X',
    'nb-8ab74e30b670198e': 'C9200CX-12P-2X2G',
    'nb-553b794d5e1846af': 'MS120-24P-HW',
    'nb-5bd28430fbf397fc': 'C1300-12XS',
    'nb-06c19caa563462d0': 'C1300-12XT-2X',
    'nb-1e89ff3122676000': 'C1300-16P-4X',
    'nb-b332648f50e7f0ed': 'JL724A',
    'nb-fedc94752959d1f9': 'JL726A',
    'nb-4b362a024923dd51': 'JL557A',
    'nb-22ec22b8ee2c893a': 'J9777A',
    'nb-938151a02eb5e5d0': 'J9774A',
    'nb-2ffc5d29f711ec36': 'JL693A',
    'nb-1520b9b243e9bb38': 'JL258A',
    'nb-491844a78b378fad': 'EX4000-12MP',
    'nb-759e188d649a5347': 'EX4000-12P',
    'nb-06d181bdfaacef1b': 'EX4000-12T',
    'nb-0378e314e40b7a32': 'EX4000-24MP',
    'nb-fc86b47706121d42': 'EX4000-24P',
    'nb-0323789c8aa37403': 'EX4000-24T',
    'nb-ba01da0f6a8e0932': 'EX4000-48MP',
    'nb-d4d0d201f9d0e748': 'EX2300-48P',
    'nb-13db0a5351fdba7d': 'EX2300-C-12P',
    'nb-b789b2ec357d683f': 'CRS326-24G-2S+RM',
    'nb-25db6819881d422b': 'CRS112-8P-4S-IN',
    'nb-746a1ccfbf605854': 'CRS418-8P-8G-2S+RM',
    'nb-0ae02d5176e83b35': 'GS108PEv3',
    'nb-0e0d436b707c6222': 'DGS-3130-54PS',
    'nb-1629a1d59aad162f': 'CCS-720DP-48ZS-2F',
    'nb-2213f0b401bb1b4b': 'GS108PP',
    'nb-2f1c864cfa97acee': '0132600339',
    'nb-3a4c93d66b83c701': 'CCS-720DT-24S-2F',
    'nb-4b21539470f6d751': 'CCS-720DP-48S-2F',
    'nb-4bed5077703a33ad': 'ES1100-8P',
    'nb-6061e8a5e3e5a74c': 'CCS-720DP-24S-2F',
    'nb-73489c7e191a0d9b': '4220-12P-4X',
    'nb-7e1c09817aeccd5f': 'GS308EP',
    'nb-88bc04bb88386c00': 'DGS-1100-08PLV2',
    'nb-9445f595338fc17a': 'GS-108B-v3',
    'nb-98efee7ae64ea280': 'GWN7803P',
    'nb-9f4e39d04b4eef89': 'GS105',
    'nb-a82a300904414f52': 'RG-NBS3100-24GT4SFP-P',
    'nb-b3dc322f7f5ffa4d': '4220-24P-4X',
    'nb-bf7b6e396d81b183': 's5210g-24tx',
    'nb-c9dda6663d585595': 'DGS-1100-08V2',
    'nb-dc46d6be5cb5b6af': 'GS510TPP',
    'nb-dc6cdf07e279b4a0': '5320-48P-8XE',
    'nb-e6c2c9e3f06a3b7e': 'DGS-1100-08',
    'nb-edb5b19d211b3fd8': '4220-24T-4X',
    'nb-f4684dfd15513291': 'TL-SG105',
    'nb-fcc0548ac0e54478': 'CCS-720DP-24ZS-2F',
}
IDS = tuple(sorted(SKUS))


def prior_names(root):
    result = [p.relative_to(root).as_posix() for p in c.path(root, 'development/hardware').glob('catalog-*-v1.json')]
    for folder in ('batch50', 'batch50b', 'batch100', 'batch100b', 'batch100c'):
        result += [p.relative_to(root).as_posix() for p in c.path(root, 'development/hardware/'+folder).glob('*.json')]
    result += ['development/hardware/selected506a/aruba.json', 'development/hardware/selected506a/ubiquiti.json']
    return sorted(result)


def previous_models(root):
    models = []
    for name in prior_names(root):
        data = c.load(c.path(root, name).read_bytes())
        models += data['definitions'] if name.endswith('-v1.json') else [row['definition'] for row in data['models']]
    c.require(len(models) == 428 and sum(bool(model['identity']['manufacturer']) for model in models) == 423,
              'selected506b_baseline_invalid')
    return models


def selected_rows(root, data):
    b.fields(data, 'formatVersion revision models')
    c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
              data['revision'] == REVISION and isinstance(data['models'], list) and len(IDS) == 50 and len(data['models']) == 50,
              'selected506b_count_invalid')
    selection = c.load(c.path(root, SELECTION).read_bytes())['models']
    chosen = {row['id']: row for row in selection}
    c.require(len(chosen) == 506 and set(IDS) <= set(chosen), 'selected506b_selection_invalid')
    rows = [b.validate_model(row) for row in data['models']]
    c.require(all(group['count'] <= 96 for row in rows for group in row['definition']['groups']),
              'selected506b_runtime_group_limit')
    by_key = {row['definition']['key']: row for row in rows}
    c.require(len(by_key) == len(IDS) and set(by_key) == {'selected-'+identifier for identifier in IDS},
              'selected506b_identity_invalid')
    c.require(len({(row['definition']['identity']['manufacturer'].casefold(),
                    row['definition']['identity']['sku'].casefold()) for row in rows}) == 50,
              'selected506b_duplicate_sku')
    for identifier in IDS:
        definition = by_key['selected-'+identifier]['definition']
        original = chosen[identifier]
        c.require(definition['identity']['manufacturer'] == original['manufacturer'] and
                  definition['identity']['model'] == original['model'] and
                  definition['identity']['sku'].casefold() == SKUS[identifier].casefold(), 'selected506b_model_substitution')
    return sorted(rows, key=lambda row: row['definition']['key'])


def compile_catalog(root):
    names = [*SOURCES, SELECTION, PLAN, LOCK, BASE, SHARED, TOOL, *prior_names(root)]
    raw = {name: c.path(root, name).read_bytes() for name in names}
    lock = c.load(raw[LOCK])
    c.require(c.sha(raw[LOCK]) == EXPECTED_LOCK_SHA256, 'selected506b_lock_not_reviewed')
    c.require(lock['targetSchema'] == 30 and lock['state'] == STATE and
              lock['sourceSha256'] == {name: c.sha(raw[name]) for name in SOURCES} and
              lock['baseMigrationSha256'] == c.sha(raw[BASE]) and
              lock['sharedCompilerSha256'] == c.sha(raw[SHARED]) and lock['selectionIds'] == sorted(IDS),
              'selected506b_input_changed')
    c.require(lock['baselineSourceSha256'] == {name: c.sha(raw[name]) for name in prior_names(root)} and
              lock['selectionSha256'] == c.sha(raw[SELECTION]) and lock['planSha256'] == c.sha(raw[PLAN]),
              'selected506b_baseline_changed')
    combined = dict(formatVersion=1, revision=REVISION, models=[])
    for source, count in zip(SOURCES, COUNTS):
        data = c.load(raw[source])
        b.fields(data, 'formatVersion revision models')
        c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
                  data['revision'] == REVISION and isinstance(data['models'], list) and len(data['models']) == count,
                  'selected506b_source_count_invalid')
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
                  'selected506b_previous_model_duplicate')
        if definition['kind'] == 'desktop':
            c.require(any(parent['kind'] == 'shelf' and any(all(definition['dimensionsMm'][key] <= slot['dimensionsMm'][key]
                      for key in ('width', 'height', 'depth')) for slot in parent['slots']) for parent in old),
                      'selected506b_support_unavailable')
    models = [row['definition'] for row in rows]
    pins = [dict(key=model['key'], revision=model['revision'], sha256=c.sha(c.canonical(model))) for model in models]
    c.require(pins == lock['definitions'], 'selected506b_definition_changed')
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
    server = b.server_source(models).replace(b'Batch50HardwareProfiles', b'Selected506BHardwareProfiles').replace(
        b'build_hardware_batch50.py', b'build_hardware_selected506b.py')
    sql = b'-- Auto-generated selected506b. SQL001-029 and sealed revisions remain unchanged.\n' + b'\n'.join(
        line for line in g.sql_source(models, pins).splitlines() if not line.startswith(b'--')) + b'\n'
    outputs = {SERVER: server, FRONTEND: g.pretty(catalogues), SQL: sql}
    inputs = {name: c.sha(value) for name, value in raw.items()}
    outputs[MANIFEST] = g.pretty(dict(formatVersion=1, targetSchema=30, catalogKey='rackclick-selected506b',
                                     state=STATE, inputs=inputs, files={name: c.sha(value) for name, value in outputs.items()},
                                     selectionIds=sorted(IDS), definitions=pins))
    outputs[TARGETS] = b.targets_source({**inputs, **{name: c.sha(value) for name, value in outputs.items()}}).replace(
        b'VerifyBatch50HardwareCatalog', b'VerifySelected506BHardwareCatalog').replace(b'_Batch50', b'_Selected506B').replace(
        b'batch50_', b'selected506b_').replace(b'build_hardware_batch50.py', b'build_hardware_selected506b.py', 1)
    return outputs


def run(root, write=False):
    b.compile_catalog = compile_catalog
    result = b.run(root, write)
    result.update(targetSchema=30, commercialModels=len(IDS), selectionIds=sorted(IDS))
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
        print(json.dumps(dict(status='failed', code=str(error) if isinstance(error, c.CatalogError) else 'selected506b_io_failed')))
        return 1


if __name__ == '__main__':
    sys.exit(main())
