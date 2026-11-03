"""Compile ten explicit German repeaters profiles, preserving historical catalogue44.

Migration45 adds room tabletop mounting and a descriptive EU two-pin inlet.
It derives the classifier from44, preserving USB and TAE without editing history.
No historical authoring, SQL, selection506 or lock is regenerated.
"""
from __future__ import annotations
import argparse, copy, hashlib, importlib.util, json, sys
from pathlib import Path
ROOT=Path(__file__).absolute().parents[1]

def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

l=module('german_repeaters_previous','tools/build_hardware_selected506l.py')
h=l.h
c,g,b=h.c,h.g,h.base
h.MOUNT_TARGETS={**h.MOUNT_TARGETS,'tabletop':'room'}
# Isolated validator module instance. Historical source bytes are never edited.
h.ALLOWED_TYPES=(*h.ALLOWED_TYPES,'usb_a','usb_c')
h.PHYSICAL_CONNECTORS={**h.PHYSICAL_CONNECTORS,'telephony':(*h.PHYSICAL_CONNECTORS['telephony'],'voice-tae')}
h.PHYSICAL_CONNECTORS={**h.PHYSICAL_CONNECTORS,'power':(*h.PHYSICAL_CONNECTORS['power'],'eu-2pin-plug')}
REVISION='german-repeaters-20261103-v1'
SOURCES=['development/hardware/german-repeaters/fritz.json','development/hardware/german-repeaters/telekom.json','development/hardware/german-repeaters/devolo.json','development/hardware/german-repeaters/tplink.json']
CONTRACT='development/hardware/german-repeaters/contract.json'
LOCK='development/hardware/catalog-schema45.lock.json'
SERVER='development/server/src/RackClick.Server/GermanRepeatersHardwareProfiles.Generated.cs'
FRONTEND='development/frontend/src/hardware-german-repeaters.generated.json'
SQL='development/server/database/045-german-repeaters-hardware.sql'
MANIFEST='development/hardware/catalog-german-repeaters.manifest.json'
TARGETS='development/server/src/RackClick.Server/GermanRepeatersHardware.Generated.targets'
STATE='curated_development_not_a_release'
EXPECTED_LOCK_SHA256='001910359d94f4d7079746c1b0d2e0a7e850c1e33d7cec6384547a350d0b004e'
MODEL_KEYS=['devolo-wifi6-repeater3000-eu', 'devolo-wifi6-repeater5400-eu', 'fritz-repeater1200ax-de', 'fritz-repeater2400-de', 'fritz-repeater3000ax-de', 'fritz-repeater600-de', 'fritz-repeater6000-de', 'telekom-speedhome-wlan-2021', 'tplink-re605x-eu', 'tplink-re700x-eu']

def input_names(root):
    references=sorted(str(p.relative_to(root)).replace('\\','/') for p in (root/'development/hardware/german-repeaters').glob('*-reference.md'))
    return sorted(set([*SOURCES,CONTRACT,*references,'tools/build_hardware_german_repeaters.py',
        'tools/build_hardware_selected506l.py','tools/hardware_family_l.py','tools/hardware_family_l_contract.json',
        'tools/build_hardware_batch50.py','tools/hardware_physical_v3.py','tools/hardware_physical_v2.py',
        'tools/hardware_family_v2.py','development/server/database/042-hardware-family-l.sql',
        'development/server/database/043-selected506l-hardware.sql','development/hardware/catalog-schema43.lock.json',
        'development/server/database/044-german-cpe-hardware.sql','development/hardware/catalog-schema44.lock.json']))

def validated_rows(root):
    contract=c.load(c.path(root,CONTRACT).read_bytes())
    c.require(contract['revision']==REVISION and contract['targetSchema']==45 and contract['models']==10 and contract['previousDefinitions']==874,'german_repeaters_contract_invalid')
    rows=[]
    for source in SOURCES:
        data=c.load(c.path(root,source).read_bytes());b.fields(data,'formatVersion revision models')
        c.require(data['formatVersion']==1 and data['revision']==REVISION,'german_repeaters_revision_invalid')
        for row in data['models']:
            h.validate_model(row,REVISION)
            for ref in row['evidence']['referenceAssets']:
                c.require(ref['path'] in input_names(root) and c.sha(c.path(root,ref['path']).read_bytes())==ref['sha256'],'german_repeaters_reference_changed')
            rows.append(row)
    for row in rows:
        d=row['definition'];groups=d['groups'];plug=d['kind']=='wall'
        c.require(d['kind'] in ('wall','tabletop') and d['mounting']==dict(kind=d['kind'],target='room') and d['rackUnits']==0 and d['slots']==[],'repeaters_mount_invalid')
        c.require(all(g['type'] in ('rj45','power','power_dc') for g in groups),'repeaters_radio_not_a_port')
        power=[g for g in groups if g['type'] in ('power','power_dc')]
        c.require(len(power)==1 and power[0]['count']==1 and power[0]['powerRole']=='inlet','repeaters_power_invalid')
        c.require((power[0]['type'],power[0].get('physicalConnector'))==(('power','eu-2pin-plug') if plug else ('power_dc','dc-barrel')),'repeaters_power_invalid')
        c.require(row['visual']['faces']['front']['banks']==[],'repeaters_front_ports_invented')
    c.require(sum(g['count'] for r in rows for g in r['definition']['groups'])==23,'repeaters_population_invalid')
    rows.sort(key=lambda r:r['definition']['key'])
    c.require([r['definition']['key'] for r in rows]==MODEL_KEYS,'german_repeaters_models_invalid')
    c.require(len({(r['definition']['identity']['manufacturer'],r['definition']['identity']['sku']) for r in rows})==10,'german_repeaters_identity_duplicate')
    # No published profile key can be shadowed by the extension.
    oldkeys={p['key'] for n in (root/'development/frontend/src').glob('hardware-*.generated.json') if n.name!='hardware-german-repeaters.generated.json' for cat in ([c.load(n.read_bytes())] if isinstance(c.load(n.read_bytes()),dict) else c.load(n.read_bytes())) for p in cat['profiles']}
    c.require(oldkeys.isdisjoint(MODEL_KEYS),'german_repeaters_existing_key')
    return rows

def sql_header(root):
    # Preserve the latest USB/TAE classifier verbatim, extending power only.
    latest=c.path(root,'development/server/database/044-german-cpe-hardware.sql').read_text(encoding='utf-8')
    start=latest.index('CREATE OR REPLACE FUNCTION hardware_validate_connector()')
    end=latest.index('INSERT INTO hardware_definition',start)
    classifier=latest[start:end]
    # SQL044 contains catalogue INSERTs after the classifier: use its first function terminator.
    classifier=classifier[:classifier.index('END $$;')+len('END $$;')]
    c.require("'schuko-f'" in classifier and "'voice-tae'" in classifier,'repeaters_latest_classifier_invalid')
    classifier=classifier.replace("'schuko-f'", "'schuko-f','eu-2pin-plug'")
    foundation=c.path(root,'development/server/database/042-hardware-family-l.sql').read_text(encoding='utf-8')
    start=foundation.index('CREATE OR REPLACE FUNCTION inventory_validate_mount()')
    mount=foundation[start:]
    c.require("d.mount_kind IN ('wall','pole','din','floor')" in mount,'repeaters_mount_anchor_invalid')
    mount=mount.replace("d.mount_kind IN ('wall','pole','din','floor')", "d.mount_kind IN ('wall','pole','din','floor','tabletop')")
    return ("-- Additive German repeaters45; historical SQL001..044 remains unchanged.\n"
        "-- tabletop is room equipment, never a rack shelf or floor container.\n"
        "ALTER TABLE hardware_definition DROP CONSTRAINT hardware_definition_mount_kind_check;\n"
        "ALTER TABLE hardware_definition ADD CONSTRAINT hardware_definition_mount_kind_check CHECK(mount_kind IN ('rack','desktop','shelf','rackContainer','vertical0U','sharedU','wall','pole','din','floor','tabletop'));\n"
        +classifier+'\n'+mount+'\n').encode()

def lock_document(root):
    rows=validated_rows(root)
    return dict(formatVersion=1,targetSchema=45,state=STATE,
        inputs={name:c.sha(c.path(root,name).read_bytes()) for name in input_names(root) if name!='tools/build_hardware_german_repeaters.py'},
        definitions=[dict(key=r['definition']['key'],revision=REVISION,sha256=c.sha(c.canonical(r['definition']))) for r in rows])

def compile_catalog(root):
    rows=validated_rows(root);models=[r['definition'] for r in rows]
    lockraw=c.path(root,LOCK).read_bytes();lock=c.load(lockraw)
    c.require(c.sha(lockraw)==EXPECTED_LOCK_SHA256 and lock==lock_document(root),'german_repeaters_lock_not_reviewed')
    inputs={name:c.sha(c.path(root,name).read_bytes()) for name in [*input_names(root),LOCK]}
    source=l.server_source(models).replace(b'tools/build_hardware_selected506l.py',b'tools/build_hardware_german_repeaters.py').replace(b'Selected506LHardwareProfiles',b'GermanRepeatersHardwareProfiles')
    projected=l.projection(rows)
    for catalog in projected:
        for p in catalog['profiles']:p['referenceScope']='web_specification_schematic_visual'
    outputs={SERVER:source,FRONTEND:g.pretty(projected),SQL:sql_header(root)+l.sql_source(models,lock['definitions'])}
    outputs[MANIFEST]=g.pretty(dict(formatVersion=1,targetSchema=45,catalogKey='rackclick-german-repeaters',state=STATE,inputs=inputs,
        files={name:c.sha(value) for name,value in outputs.items()},modelKeys=MODEL_KEYS,definitions=lock['definitions']))
    outputs[TARGETS]=b.targets_source({**inputs,**{name:c.sha(value) for name,value in outputs.items()}}).replace(b'VerifyBatch50HardwareCatalog',b'VerifyGermanRepeatersHardwareCatalog').replace(b'_Batch50',b'_GermanRepeaters').replace(b'batch50_',b'german_repeaters_').replace(b'build_hardware_batch50.py',b'build_hardware_german_repeaters.py',1)
    return outputs

def run(root,write=False):
    b.compile_catalog=compile_catalog
    return {**b.run(root,write),'targetSchema':45,'commercialModels':10}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);m=p.add_mutually_exclusive_group(required=True);m.add_argument('--write',action='store_true');m.add_argument('--check',action='store_true');a=p.parse_args()
    try:print(json.dumps(run(a.root,a.write)))
    except (ValueError,KeyError,TypeError,OSError) as error:print(type(error).__name__+': '+str(error),file=sys.stderr);raise SystemExit(1)
