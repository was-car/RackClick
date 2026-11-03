"""Compile the third group of usable profiles drawn from the fixed 506-model selection.

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
spec = importlib.util.spec_from_file_location('selected506c_private_engine', ROOT/'tools/build_hardware_selected506b.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
b = engine.b
c, g = engine.c, engine.g
REVISION = 'selected506c-20261101-v1'
b.REVISION = REVISION
SOURCES = ['development/hardware/selected506c/firewalls.json', 'development/hardware/selected506c/edge.json']
COUNTS = [25, 25]
SELECTION = 'development/hardware/selected-models-506.json'
LINKS = 'development/hardware/selected-profile-links.json'
PLAN = 'evidence/s1-20261101/integracion506c/PLAN-50.json'
LOCK = 'development/hardware/catalog-schema31.lock.json'
BASE = 'development/server/database/030-selected506b-hardware.sql'
SERVER = 'development/server/src/RackClick.Server/Selected506CHardwareProfiles.Generated.cs'
FRONTEND = 'development/frontend/src/hardware-selected506c.generated.json'
SQL = 'development/server/database/031-selected506c-hardware.sql'
MANIFEST = 'development/hardware/catalog-selected506c.manifest.json'
TARGETS = 'development/server/src/RackClick.Server/Selected506CHardware.Generated.targets'
TOOL = 'tools/build_hardware_selected506c.py'
SHARED = 'tools/build_hardware_selected506b.py'
CORE = 'tools/build_hardware_batch50.py'
STATE = 'curated_development_not_a_release'
EXPECTED_LOCK_SHA256 = 'd8624be6d1f224d53f726624aa3cc84cf0840fa5db805ebd5c618596d096dc55'
SKUS = {
    'sophos-xg-135': 'XG 135',
    'sophos-xgs-116': 'XGS 116',
    'sophos-xgs-138': 'XGS 138',
    'nb-9b7461820cabfd63': 'XGS 126',
    'nb-60535d6487d8c516': 'XGS 136',
    'fortinet-fortigate-80f': 'FG-80F',
    'fortinet-fortigate-100f': 'FG-100F',
    'nb-9e1720811fc797a6': 'FG-50G',
    'nb-8db15759990d4860': 'FG-100E',
    'nb-908ff89d52fbb695': 'FG-200D',
    'nb-920e5812c8fd4f87': 'FG-80D',
    'nb-dfed66cafdc81794': 'FG-140E-POE',
    'nb-640a1e0ad66b9b51': 'FG-1000D',
    'nb-d18ad51e4dbe98fd': 'FG-101E',
    'nb-d71c560a21e0db1e': 'FG-201F',
    'nb-14b4f71277d991de': 'FG-310B',
    'nb-8ad4df2cb7211e53': 'FG-500D',
    'nb-1569935c143ae3b4': 'FG-100D',
    'nb-c81defef5301d096': 'FG-100EF',
    'nb-a954659fb87b4e11': 'FG-1200D',
    'nb-f9a7d60382905603': 'FG-800D',
    'nb-083677535cff6791': 'FG-400F',
    'nb-229917b69a037991': 'Firebox T25',
    'nb-6c1be13449ccaccb': 'Firebox T45',
    'nb-068b536b05b168d6': 'F80B',
    'ubiquiti-udm-pro': 'UDM-PRO',
    'nb-5f2f318828e8a714': 'UCG-Ultra',
    'nb-67a1252a6921143c': 'UDM-SE',
    'nb-1dda3b7e93aeec53': 'UDM-PRO-MAX',
    'nb-91b2bc4ecae870e8': 'UNAS-Pro',
    'nb-6c3c831ad8429c1d': 'USG-PRO-4',
    'nb-026eafe7e1684a8c': 'RB4011iGS+RM',
    'nb-9e6429de560eb723': 'TL-SG105E',
    'nb-23bca6f7679f1595': 'RB952Ui-5ac2nD-TC',
    'nb-9f034976d9130ca7': 'E62iUGS-2axD5axT',
    'nb-5a7762f3d43d50a1': 'FS6400',
    'nb-3c48ca91bd3e9e90': 'DS918+',
    'nb-bb280d4ca41dc95b': 'RS2416RP+',
    'nb-86babf3249d2b78a': 'RS3614xs+',
    'nb-87d53966e8a77039': 'RS815+',
    'nb-7a9733566074ec15': 'TS-883XU-RP',
    'nb-a121938648f6b54a': 'TVS-EC1580MU-SAS-RP',
    'cisco-isr4331': 'ISR4331/K9',
    'nb-74505fc219eccc33': 'ISR4321/K9',
    'nb-c0a3827bad315c40': 'ISR4351/K9',
    'nb-16082636813a2c65': 'C8300-1N1S-4T2X',
    'nb-ed10b6f53c36d127': 'ASR1001-X',
    'nb-f545d3718ff68f34': 'ASR1001',
    'nb-7e1f01ffe3e19e8a': 'ASR1001-HX',
    'nb-b953f55ddfc9d913': 'ASR1002X-5G-K9',
}
MOUNTS = {
    'sophos-xg-135': ('desktop', 0),
    'sophos-xgs-116': ('desktop', 0),
    'sophos-xgs-138': ('desktop', 0),
    'nb-9b7461820cabfd63': ('desktop', 0),
    'nb-60535d6487d8c516': ('desktop', 0),
    'fortinet-fortigate-80f': ('desktop', 0),
    'fortinet-fortigate-100f': ('rack', 1),
    'nb-9e1720811fc797a6': ('desktop', 0),
    'nb-8db15759990d4860': ('rack', 1),
    'nb-908ff89d52fbb695': ('rack', 1),
    'nb-920e5812c8fd4f87': ('desktop', 0),
    'nb-dfed66cafdc81794': ('rack', 1),
    'nb-640a1e0ad66b9b51': ('rack', 2),
    'nb-d18ad51e4dbe98fd': ('rack', 1),
    'nb-d71c560a21e0db1e': ('rack', 1),
    'nb-14b4f71277d991de': ('rack', 1),
    'nb-8ad4df2cb7211e53': ('rack', 1),
    'nb-1569935c143ae3b4': ('rack', 1),
    'nb-c81defef5301d096': ('rack', 1),
    'nb-a954659fb87b4e11': ('rack', 2),
    'nb-f9a7d60382905603': ('rack', 1),
    'nb-083677535cff6791': ('rack', 1),
    'nb-229917b69a037991': ('desktop', 0),
    'nb-6c1be13449ccaccb': ('desktop', 0),
    'nb-068b536b05b168d6': ('desktop', 0),
    'ubiquiti-udm-pro': ('rack', 1),
    'nb-5f2f318828e8a714': ('desktop', 0),
    'nb-67a1252a6921143c': ('rack', 1),
    'nb-1dda3b7e93aeec53': ('rack', 1),
    'nb-91b2bc4ecae870e8': ('rack', 2),
    'nb-6c3c831ad8429c1d': ('rack', 1),
    'nb-026eafe7e1684a8c': ('rack', 1),
    'nb-9e6429de560eb723': ('desktop', 0),
    'nb-23bca6f7679f1595': ('desktop', 0),
    'nb-9f034976d9130ca7': ('desktop', 0),
    'nb-5a7762f3d43d50a1': ('rack', 2),
    'nb-3c48ca91bd3e9e90': ('desktop', 0),
    'nb-bb280d4ca41dc95b': ('rack', 2),
    'nb-86babf3249d2b78a': ('rack', 2),
    'nb-87d53966e8a77039': ('rack', 1),
    'nb-7a9733566074ec15': ('rack', 2),
    'nb-a121938648f6b54a': ('rack', 2),
    'cisco-isr4331': ('rack', 1),
    'nb-74505fc219eccc33': ('rack', 1),
    'nb-c0a3827bad315c40': ('rack', 2),
    'nb-16082636813a2c65': ('rack', 1),
    'nb-ed10b6f53c36d127': ('rack', 1),
    'nb-f545d3718ff68f34': ('rack', 1),
    'nb-7e1f01ffe3e19e8a': ('rack', 1),
    'nb-b953f55ddfc9d913': ('rack', 2),
}
IDS = tuple(sorted(SKUS))


def prior_names(root):
    result = [p.relative_to(root).as_posix() for p in c.path(root, 'development/hardware').glob('catalog-*-v1.json')]
    for folder in ('batch50', 'batch50b', 'batch100', 'batch100b', 'batch100c'):
        result += [p.relative_to(root).as_posix() for p in c.path(root, 'development/hardware/'+folder).glob('*.json')]
    result += ['development/hardware/selected506a/aruba.json', 'development/hardware/selected506a/ubiquiti.json',
               'development/hardware/selected506b/core.json', 'development/hardware/selected506b/access.json']
    return sorted(result)


def previous_models(root):
    models = []
    for name in prior_names(root):
        data = c.load(c.path(root, name).read_bytes())
        models += data['definitions'] if name.endswith('-v1.json') else [row['definition'] for row in data['models']]
    c.require(len(models) == 478 and sum(bool(model['identity']['manufacturer']) for model in models) == 473,
              'selected506c_baseline_invalid')
    return models


def selected_rows(root, data):
    b.fields(data, 'formatVersion revision models')
    c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
              data['revision'] == REVISION and isinstance(data['models'], list) and len(IDS) == 50 and
              set(MOUNTS) == set(IDS) and len(data['models']) == 50,
              'selected506c_count_invalid')
    selection = c.load(c.path(root, SELECTION).read_bytes())['models']
    chosen = {row['id']: row for row in selection}
    plan = c.load(c.path(root, PLAN).read_bytes())
    c.require(type(plan['formatVersion']) is int and plan['formatVersion'] == 1 and
              plan['revision'] == REVISION and plan['targetSchema'] == 31 and
              plan['baselineDefinitions'] == 478 and plan['baselineCommercial'] == 473 and
              set(plan['authoring']) == {'firewalls', 'edge'} and
              all(isinstance(plan['authoring'][name], list) and len(plan['authoring'][name]) == 25
                  for name in ('firewalls', 'edge')), 'selected506c_assignment_invalid')
    planned = [row['id'] for name in ('firewalls', 'edge') for row in plan['authoring'][name]]
    c.require(len(planned) == len(set(planned)) == 50 and set(planned) == set(IDS),
              'selected506c_assignment_invalid')
    links = c.load(c.path(root, LINKS).read_bytes())
    c.require(len(links['links']) == 7 and
              set(IDS).isdisjoint(row['selectionId'] for row in links['links']),
              'selected506c_previous_model_duplicate')
    c.require(len(chosen) == 506 and set(IDS) <= set(chosen), 'selected506c_selection_invalid')
    rows = [b.validate_model(row) for row in data['models']]
    c.require(all(group['count'] <= 96 for row in rows for group in row['definition']['groups']),
              'selected506c_runtime_group_limit')
    by_key = {row['definition']['key']: row for row in rows}
    c.require(len(by_key) == len(IDS) and set(by_key) == {'selected-'+identifier for identifier in IDS},
              'selected506c_identity_invalid')
    c.require(len({(row['definition']['identity']['manufacturer'].casefold(),
                    row['definition']['identity']['sku'].casefold()) for row in rows}) == 50,
              'selected506c_duplicate_sku')
    for identifier in IDS:
        definition = by_key['selected-'+identifier]['definition']
        original = chosen[identifier]
        c.require(definition['identity']['manufacturer'] == original['manufacturer'] and
                  definition['identity']['model'] == original['model'] and
                  definition['identity']['sku'].casefold() == SKUS[identifier].casefold(), 'selected506c_model_substitution')
        c.require((definition['kind'], definition['rackUnits']) == MOUNTS[identifier],
                  'selected506c_mount_substitution')
    return sorted(rows, key=lambda row: row['definition']['key'])


def compile_catalog(root):
    names = [*SOURCES, SELECTION, LINKS, PLAN, LOCK, BASE, SHARED, CORE, TOOL, *prior_names(root)]
    raw = {name: c.path(root, name).read_bytes() for name in names}
    lock = c.load(raw[LOCK])
    c.require(c.sha(raw[LOCK]) == EXPECTED_LOCK_SHA256, 'selected506c_lock_not_reviewed')
    c.require(lock['targetSchema'] == 31 and lock['state'] == STATE and
              lock['sourceSha256'] == {name: c.sha(raw[name]) for name in SOURCES} and
              lock['baseMigrationSha256'] == c.sha(raw[BASE]) and
              lock['sharedCompilerSha256'] == c.sha(raw[SHARED]) and lock['baseEngineSha256'] == c.sha(raw[CORE]) and
              lock['selectionIds'] == sorted(IDS),
              'selected506c_input_changed')
    c.require(lock['baselineSourceSha256'] == {name: c.sha(raw[name]) for name in prior_names(root)} and
              lock['selectionSha256'] == c.sha(raw[SELECTION]) and lock['planSha256'] == c.sha(raw[PLAN]) and
              lock['profileLinksSha256'] == c.sha(raw[LINKS]),
              'selected506c_baseline_changed')
    combined = dict(formatVersion=1, revision=REVISION, models=[])
    for source, count in zip(SOURCES, COUNTS):
        data = c.load(raw[source])
        b.fields(data, 'formatVersion revision models')
        c.require(type(data['formatVersion']) is int and data['formatVersion'] == 1 and
                  data['revision'] == REVISION and isinstance(data['models'], list) and len(data['models']) == count,
                  'selected506c_source_count_invalid')
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
                  'selected506c_previous_model_duplicate')
        if definition['kind'] == 'desktop':
            c.require(any(parent['kind'] == 'shelf' and any(all(definition['dimensionsMm'][key] <= slot['dimensionsMm'][key]
                      for key in ('width', 'height', 'depth')) for slot in parent['slots']) for parent in old),
                      'selected506c_support_unavailable')
    models = [row['definition'] for row in rows]
    pins = [dict(key=model['key'], revision=model['revision'], sha256=c.sha(c.canonical(model))) for model in models]
    c.require(pins == lock['definitions'], 'selected506c_definition_changed')
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
    server = b.server_source(models).replace(b'Batch50HardwareProfiles', b'Selected506CHardwareProfiles').replace(
        b'build_hardware_batch50.py', b'build_hardware_selected506c.py')
    sql = b'-- Auto-generated selected506c. SQL001-030 and sealed revisions remain unchanged.\n' + b'\n'.join(
        line for line in g.sql_source(models, pins).splitlines() if not line.startswith(b'--')) + b'\n'
    outputs = {SERVER: server, FRONTEND: g.pretty(catalogues), SQL: sql}
    inputs = {name: c.sha(value) for name, value in raw.items()}
    outputs[MANIFEST] = g.pretty(dict(formatVersion=1, targetSchema=31, catalogKey='rackclick-selected506c',
                                     state=STATE, inputs=inputs, files={name: c.sha(value) for name, value in outputs.items()},
                                     selectionIds=sorted(IDS), definitions=pins))
    outputs[TARGETS] = b.targets_source({**inputs, **{name: c.sha(value) for name, value in outputs.items()}}).replace(
        b'VerifyBatch50HardwareCatalog', b'VerifySelected506CHardwareCatalog').replace(b'_Batch50', b'_Selected506C').replace(
        b'batch50_', b'selected506c_').replace(b'build_hardware_batch50.py', b'build_hardware_selected506c.py', 1)
    return outputs


def run(root, write=False):
    b.compile_catalog = compile_catalog
    result = b.run(root, write)
    result.update(targetSchema=31, commercialModels=len(IDS), selectionIds=sorted(IDS))
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
        print(json.dumps(dict(status='failed', code=str(error) if isinstance(error, c.CatalogError) else 'selected506c_io_failed')))
        return 1


if __name__ == '__main__':
    sys.exit(main())
