"""Compile six explicit German CPE profiles, preserving historical catalogue43.

USB media already exist in inventory. Migration44 admits them in the immutable
hardware catalogue, and adds an explicit TAE physical descriptor for telephony.
No historical authoring, SQL, selection506 or lock is regenerated.
"""
from __future__ import annotations
import argparse, copy, hashlib, importlib.util, json, sys
from pathlib import Path
ROOT=Path(__file__).absolute().parents[1]

def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

l=module('german_cpe_previous','tools/build_hardware_selected506l.py')
h=l.h
c,g,b=h.c,h.g,h.base
# Isolated validator module instance. Historical source bytes are never edited.
h.ALLOWED_TYPES=(*h.ALLOWED_TYPES,'usb_a','usb_c')
h.PHYSICAL_CONNECTORS={**h.PHYSICAL_CONNECTORS,'telephony':(*h.PHYSICAL_CONNECTORS['telephony'],'voice-tae')}
REVISION='german-cpe-20261103-v1'
SOURCES=['development/hardware/german-cpe/fritz.json','development/hardware/german-cpe/draytek.json']
CONTRACT='development/hardware/german-cpe/contract.json'
LOCK='development/hardware/catalog-schema44.lock.json'
SERVER='development/server/src/RackClick.Server/GermanCpeHardwareProfiles.Generated.cs'
FRONTEND='development/frontend/src/hardware-german-cpe.generated.json'
SQL='development/server/database/044-german-cpe-hardware.sql'
MANIFEST='development/hardware/catalog-german-cpe.manifest.json'
TARGETS='development/server/src/RackClick.Server/GermanCpeHardware.Generated.targets'
STATE='curated_development_not_a_release'
EXPECTED_LOCK_SHA256='e46ccd87f84f0c62ffdffcb8bd7819a4f7e543155a0064d5c6278340bb92502c'
MODEL_KEYS=['draytek-vigor167','draytek-vigor2766','draytek-vigor2766ac','fritz-7530ax-de','fritz-7590ax-v2-de','fritz-7690-de']

def input_names(root):
    references=sorted(str(p.relative_to(root)).replace('\\','/') for p in (root/'development/hardware/german-cpe').glob('*-reference.md'))
    return sorted(set([*SOURCES,CONTRACT,*references,'tools/build_hardware_german_cpe.py',
        'tools/build_hardware_selected506l.py','tools/hardware_family_l.py','tools/hardware_family_l_contract.json',
        'tools/build_hardware_batch50.py','tools/hardware_physical_v3.py','tools/hardware_physical_v2.py',
        'tools/hardware_family_v2.py','development/server/database/042-hardware-family-l.sql',
        'development/server/database/043-selected506l-hardware.sql','development/hardware/catalog-schema43.lock.json']))

def validated_rows(root):
    contract=c.load(c.path(root,CONTRACT).read_bytes())
    c.require(contract['revision']==REVISION and contract['targetSchema']==44 and contract['models']==6 and contract['previousDefinitions']==868,'german_cpe_contract_invalid')
    rows=[]
    for source in SOURCES:
        data=c.load(c.path(root,source).read_bytes());b.fields(data,'formatVersion revision models')
        c.require(data['formatVersion']==1 and data['revision']==REVISION,'german_cpe_revision_invalid')
        for row in data['models']:
            h.validate_model(row,REVISION)
            for ref in row['evidence']['referenceAssets']:
                c.require(ref['path'] in input_names(root) and c.sha(c.path(root,ref['path']).read_bytes())==ref['sha256'],'german_cpe_reference_changed')
            rows.append(row)
    rows.sort(key=lambda r:r['definition']['key'])
    c.require([r['definition']['key'] for r in rows]==MODEL_KEYS,'german_cpe_models_invalid')
    c.require(len({(r['definition']['identity']['manufacturer'],r['definition']['identity']['sku']) for r in rows})==6,'german_cpe_identity_duplicate')
    # No published profile key can be shadowed by the extension.
    oldkeys={p['key'] for n in (root/'development/frontend/src').glob('hardware-*.generated.json') if n.name!='hardware-german-cpe.generated.json' for cat in ([c.load(n.read_bytes())] if isinstance(c.load(n.read_bytes()),dict) else c.load(n.read_bytes())) for p in cat['profiles']}
    c.require(oldkeys.isdisjoint(MODEL_KEYS),'german_cpe_existing_key')
    return rows

def sql_header(root):
    foundation=c.path(root,'development/server/database/042-hardware-family-l.sql').read_text(encoding='utf-8')
    start=foundation.index('CREATE OR REPLACE FUNCTION hardware_validate_connector()')
    end=foundation.index('CREATE OR REPLACE FUNCTION rackclick_user_port_colors_valid',start)
    classifier=foundation[start:end].replace("('voice-8p8c','voice-rj11')","('voice-8p8c','voice-rj11','voice-tae')")
    c.require(classifier!=foundation[start:end],'german_cpe_connector_anchor_invalid')
    return ("-- German CPE additive extension. Historical migrations001..043 stay unchanged.\n"
        "-- USB physical type already exists for manual inventory; TAE is voice, never Ethernet.\n"
        "ALTER TABLE hardware_group_template DROP CONSTRAINT hardware_group_template_type_check;\n"
        "ALTER TABLE hardware_group_template ADD CONSTRAINT hardware_group_template_type_check CHECK(type IN ('rj45','sfp','sfp28','sfp56','qsfp','qsfpdd','power','console','idc','ipc','fiber','sfpdd','cfp2','sas','dsl','telephony','isdn','expansion','power_dc','usb_a','usb_c'));\n"
        +classifier).encode()

def lock_document(root):
    rows=validated_rows(root)
    return dict(formatVersion=1,targetSchema=44,state=STATE,
        inputs={name:c.sha(c.path(root,name).read_bytes()) for name in input_names(root) if name!='tools/build_hardware_german_cpe.py'},
        definitions=[dict(key=r['definition']['key'],revision=REVISION,sha256=c.sha(c.canonical(r['definition']))) for r in rows])

def compile_catalog(root):
    rows=validated_rows(root);models=[r['definition'] for r in rows]
    lockraw=c.path(root,LOCK).read_bytes();lock=c.load(lockraw)
    c.require(c.sha(lockraw)==EXPECTED_LOCK_SHA256 and lock==lock_document(root),'german_cpe_lock_not_reviewed')
    inputs={name:c.sha(c.path(root,name).read_bytes()) for name in [*input_names(root),LOCK]}
    source=l.server_source(models).replace(b'tools/build_hardware_selected506l.py',b'tools/build_hardware_german_cpe.py').replace(b'Selected506LHardwareProfiles',b'GermanCpeHardwareProfiles')
    projected=l.projection(rows)
    for catalog in projected:
        for p in catalog['profiles']:p['referenceScope']='web_specification_schematic_visual'
    outputs={SERVER:source,FRONTEND:g.pretty(projected),SQL:sql_header(root)+l.sql_source(models,lock['definitions'])}
    outputs[MANIFEST]=g.pretty(dict(formatVersion=1,targetSchema=44,catalogKey='rackclick-german-cpe',state=STATE,inputs=inputs,
        files={name:c.sha(value) for name,value in outputs.items()},modelKeys=MODEL_KEYS,definitions=lock['definitions']))
    outputs[TARGETS]=b.targets_source({**inputs,**{name:c.sha(value) for name,value in outputs.items()}}).replace(b'VerifyBatch50HardwareCatalog',b'VerifyGermanCpeHardwareCatalog').replace(b'_Batch50',b'_GermanCpe').replace(b'batch50_',b'german_cpe_').replace(b'build_hardware_batch50.py',b'build_hardware_german_cpe.py',1)
    return outputs

def run(root,write=False):
    b.compile_catalog=compile_catalog
    return {**b.run(root,write),'targetSchema':44,'commercialModels':6}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);m=p.add_mutually_exclusive_group(required=True);m.add_argument('--write',action='store_true');m.add_argument('--check',action='store_true');a=p.parse_args()
    try:print(json.dumps(run(a.root,a.write)))
    except (ValueError,KeyError,TypeError,OSError) as error:print(type(error).__name__+': '+str(error),file=sys.stderr);raise SystemExit(1)
