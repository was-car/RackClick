"""Compile the final 62 selections using explicit mounting and fixed configurations.

Historical authoring, projections and SQL001..041 remain pinned. This is catalogue
data, not an installer or adoption. Unknown dimensions stay null.
"""
from __future__ import annotations
import argparse, importlib.util, json, sys
from pathlib import Path
ROOT=Path(__file__).absolute().parents[1]
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file); value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
h=module('family_l_authoring','tools/hardware_family_l.py')
k=module('family_l_previous','tools/build_hardware_selected506k.py')
c,g,b=h.c,h.g,h.base
REVISION='selected506l-20261101-v1'
FAMILIES=('mechanical-copper','storage','network')
SOURCES=[f'development/hardware/selected506l/{name}.json' for name in FAMILIES]
SUPPORT_SOURCE='development/hardware/selected506l/support-revisions.json'
SUPPORT_REVISION='selected506l-support-20261101-v1'
PLAN='evidence/s1-20261101/integracion506l/PLAN-FAMILIAS.json'
LOCK='development/hardware/catalog-schema43.lock.json'
BASE='development/server/database/042-hardware-family-l.sql'
BASELINE='development/server/database/041-selected506k-hardware.sql'
SERVER='development/server/src/RackClick.Server/Selected506LHardwareProfiles.Generated.cs'
FRONTEND='development/frontend/src/hardware-selected506l.generated.json'
SQL='development/server/database/043-selected506l-hardware.sql'
MANIFEST='development/hardware/catalog-selected506l.manifest.json'
TARGETS='development/server/src/RackClick.Server/Selected506LHardware.Generated.targets'
STATE='curated_development_not_a_release'
EXPECTED_LOCK_SHA256='fde93af0c8bb3e8567a2b4015533e0474d7ccc2b110167c58a83b8d8933316b8'
GROUP_EXTRAS=('physicalFace','interfaceRole','signalRole','powerSystem')
q=lambda value:json.dumps(value,ensure_ascii=True)
canonical=lambda value:c.canonical(value).decode('utf-8')

def input_names(root):
    old=k.prior_names(root)+k.SOURCES+[k.SUPPORT,k.LOCK,k.BASE,k.BASELINE]
    return sorted(set(SOURCES+[SUPPORT_SOURCE,PLAN,BASE,BASELINE,k.SELECTION,k.LINKS,'tools/hardware_family_l.py','tools/hardware_family_l_contract.json',
        'tools/build_hardware_selected506l.py','tools/hardware_family_v2.py',k.TOOL,k.CORE,*k.TRANSITIVE,*old]))

def validated_rows(root):
    plan=c.load(c.path(root,PLAN).read_bytes())
    c.require(plan['revision']==REVISION and plan['baselineSchema']==41 and plan['targetSchema']==43 and
        plan['foundationSchema']==42 and plan['baselineDefinitions']==805 and plan['baselineCommercial']==799 and
        plan['models']==62 and set(plan['authoring'])==set(FAMILIES),'selected506l_plan_invalid')
    selected={r['id']:r for r in c.load(c.path(root,k.SELECTION).read_bytes())['models']}
    rows=[];ids=[]
    for family,source in zip(FAMILIES,SOURCES):
        data=c.load(c.path(root,source).read_bytes());b.fields(data,'formatVersion revision models')
        expected={r['id'] for r in plan['authoring'][family]}
        c.require(data['formatVersion']==1 and data['revision']==REVISION and isinstance(data['models'],list) and
            len(data['models'])==len(expected) and {r['definition']['key'] for r in data['models']}=={'selected-'+id for id in expected},'selected506l_family_invalid')
        for row in data['models']:
            h.validate_model(row,REVISION);m=row['definition'];id=m['key'].removeprefix('selected-');original=selected.get(id)
            c.require(original and m['identity']['manufacturer']==original['manufacturer'] and m['identity']['model']==original['model'],'selected506l_identity_invalid')
            rows.append(row);ids.append(id)
    c.require(len(ids)==len(set(ids))==62,'selected506l_count_invalid')
    previous=k.previous_models(root)+[row['definition'] for source in k.SOURCES for row in c.load(c.path(root,source).read_bytes())['models']]+k.support_models(root)
    c.require(len(previous)==805 and sum(bool(m['identity']['manufacturer']) for m in previous)==799,'selected506l_baseline_invalid')
    c.require({row['definition']['key'] for row in rows}.isdisjoint(m['key'] for m in previous),'selected506l_existing_key')
    c.require(len({(row['definition']['identity']['manufacturer'].casefold(),row['definition']['identity']['sku'].casefold()) for row in rows})==62,'selected506l_duplicate_sku')
    return sorted(rows,key=lambda r:r['definition']['key'])

def support_rows(root):
    data=c.load(c.path(root,SUPPORT_SOURCE).read_bytes());b.fields(data,'formatVersion revision models')
    c.require(data['formatVersion']==1 and data['revision']==SUPPORT_REVISION and len(data['models'])==1,'selected506l_support_invalid')
    row=data['models'][0];m=row['definition'];h.validate_model(row,SUPPORT_REVISION)
    c.require(m['key']=='selected-nb-e5030fe747d79fe6' and m['identity']['sku']=='USW-Pro-24-POE' and m['kind']=='rack' and m['rackUnits']==1,'selected506l_support_substitution')
    prior=next(r['definition'] for r in c.load(c.path(root,'development/hardware/selected506a/ubiquiti.json').read_bytes())['models'] if r['definition']['key']==m['key'])
    c.require(m['identity']==prior['identity'] and m['dimensionsMm']==prior['dimensionsMm'],'selected506l_support_substitution')
    c.require(m['groups'][:-1]==prior['groups'] and m['groups'][-1]['key']=='rear-smartpower' and m['groups'][-1]['type']=='power_dc' and
        m['groups'][-1]['count']==1 and m['groups'][-1]['face']=='rear' and m['groups'][-1]['powerRole']=='inlet' and
        m['groups'][-1]['physicalConnector']==m['groups'][-1]['powerSystem']=='unifi-smartpower','selected506l_support_substitution')
    return data['models']

def server_source(models):
    lines=['// <auto-generated> tools/build_hardware_selected506l.py; do not edit. </auto-generated>',
        'namespace RackClick.Server;','using static RackClick.Server.InventoryHardwareProfiles;',
        'internal static class Selected506LHardwareProfiles','{','    internal static readonly Registry Catalog = new([']
    for m in models:
        groups=[]
        for group in m['groups']:
            args=[q(group['key']),q(group['type']),str(group['count']),q(group['face']),q(group['name']),q(group['prefix'])]
            props=['PowerRole = '+q(group['powerRole'])]
            for key in ('physicalConnector',*GROUP_EXTRAS):
                if group.get(key) is not None:props.append(key[0].upper()+key[1:]+' = '+q(group[key]))
            groups.append('new('+', '.join(args)+') { '+', '.join(props)+' }')
        dims=['null' if m['dimensionsMm'][key] is None else str(m['dimensionsMm'][key])+'m' for key in ('width','height','depth')]
        args=[q(m['key']),str(m['rackUnits']),*dims,q(m['color']),'['+', '.join(groups)+']',q(m['revision'])]
        props=['Kind = '+q(m['kind']),'DefinitionSha256 = '+q(c.sha(c.canonical(m))),
            'MountingJson = '+q(canonical(m['mounting'])),'ConfigurationJson = '+q(canonical(m.get('configuration',[]))),
            'ContinuitiesJson = '+q(canonical(m.get('continuities',[])))]
        props += [key.title()+' = '+q(value) for key,value in m['identity'].items()]
        if m['passthrough']:
            p=m['passthrough'];props+=['Passthrough = new('+', '.join((q(p['frontGroup']),q(p['rearGroup']),str(p['count'])))+')']
        if m['slots']:
            props+=['Slots = ['+', '.join('new('+', '.join([q(s['key'])]+[str(s['dimensionsMm'][x])+'m' for x in ('width','height','depth')])+')' for s in m['slots'])+']']
        lines.append('        new('+', '.join(args)+') { '+', '.join(props)+' },')
    return ('\n'.join(lines+['    ]);','}',''])).encode('ascii')

def sql_source(models,pins):
    lines=['-- Auto-generated L. SQL001..041 and historical sealed revisions are unchanged.',
        '-- Fixed population and connector classification are not protocol, circuit or fit simulation.']
    for m,pin in zip(models,pins):
        part=[line for line in g.sql_source([m],[pin]).decode().splitlines() if not line.startswith('--')]
        c.require(part[-1].startswith('UPDATE hardware_definition SET sealed=true WHERE '),'selected506l_seal_invalid')
        extra=[];pair=[m['key'],m['revision']]
        def insert(table,columns,values):extra.append('INSERT INTO '+table+' ('+columns+') VALUES ('+', '.join(map(g.literal,values))+');')
        insert('hardware_profile_extension','profile_key, revision, metadata',pair+[canonical(dict(mounting=m['mounting'],configuration=m.get('configuration',[]),continuities=m.get('continuities',[])))])
        if m['passthrough']:
            p=m['passthrough'];insert('hardware_passthrough','profile_key, revision, front_group_key, rear_group_key, port_count',pair+[p['frontGroup'],p['rearGroup'],p['count']])
        for group in m['groups']:
            if group.get('physicalConnector') is not None:insert('hardware_connector_template','profile_key, revision, group_key, physical_connector',pair+[group['key'],group['physicalConnector']])
            metadata={key:group[key] for key in GROUP_EXTRAS if key in group}
            if metadata:insert('hardware_group_extension','profile_key, revision, group_key, metadata',pair+[group['key'],canonical(metadata)])
        lines += part[:-1]+extra+part[-1:]
    return ('\n'.join(lines)+'\n').encode()

def projection(rows):
    profiles=[]
    for row in rows:
        m=row['definition'];dims=m['dimensionsMm'];p=dict(key=m['key'],kind=m['kind'],sizeU=m['rackUnits'],
            widthMm=dims['width'],heightMm=dims['height'],depthMm=dims['depth'],color=m['color'],
            groups=[{key:group[key] for key in ('key','type','count','face','powerRole','physicalConnector',*GROUP_EXTRAS) if key in group} for group in m['groups']],
            identity=m['identity'],source=m['provenance']['source'],mounting=m['mounting'],configuration=m.get('configuration',[]),continuities=m.get('continuities',[]),
            visual=row['visual'],reviewLimits=row['evidence']['limits'],referenceScope='model_reference',passthrough=m['passthrough'])
        if any('unverified' in a['match'].lower() for a in row['evidence']['referenceAssets']):p['referenceScope']='unverified_reference'
        elif any('family' in a['match'].lower() or 'shared' in a['match'].lower() for a in row['evidence']['referenceAssets']):p['referenceScope']='family_reference'
        if m['slots']:
            s=m['slots'][0];p['slot']=dict(key=s['key'],**{key+'Mm':value for key,value in s['dimensionsMm'].items()})
        profiles.append(p)
    catalogues=[]
    for row,p in zip(rows,profiles):
        version=row['definition']['revision'];found=next((v for v in catalogues if v['version']==version),None)
        if found:found['profiles'].append(p)
        else:catalogues.append(dict(version=version,synthetic=False,profiles=[p]))
    return catalogues

def compile_catalog(root):
    names=input_names(root);raw={name:c.path(root,name).read_bytes() for name in names};selected=validated_rows(root);rows=selected+support_rows(root)
    models=[r['definition'] for r in rows];pins=[dict(key=m['key'],revision=m['revision'],sha256=c.sha(c.canonical(m))) for m in models]
    lockraw=c.path(root,LOCK).read_bytes();lock=c.load(lockraw)
    expected=dict(formatVersion=1,targetSchema=43,state=STATE,inputs={name:c.sha(value) for name,value in raw.items() if name!='tools/build_hardware_selected506l.py'},definitions=pins)
    c.require(c.sha(lockraw)==EXPECTED_LOCK_SHA256 and lock==expected,'selected506l_lock_not_reviewed')
    inputs={**{name:c.sha(value) for name,value in raw.items()},LOCK:c.sha(lockraw)}
    outputs={SERVER:server_source(models),FRONTEND:g.pretty(projection(rows)),SQL:sql_source(models,pins)}
    outputs[MANIFEST]=g.pretty(dict(formatVersion=1,targetSchema=43,catalogKey='rackclick-selected506l',state=STATE,inputs=inputs,
        files={name:c.sha(value) for name,value in outputs.items()},selectionIds=sorted(r['definition']['key'].removeprefix('selected-') for r in selected),definitions=pins))
    outputs[TARGETS]=b.targets_source({**inputs,**{name:c.sha(value) for name,value in outputs.items()}}).replace(b'VerifyBatch50HardwareCatalog',b'VerifySelected506LHardwareCatalog').replace(b'_Batch50',b'_Selected506L').replace(b'batch50_',b'selected506l_').replace(b'build_hardware_batch50.py',b'build_hardware_selected506l.py',1)
    return outputs

def run(root,write=False):
    b.compile_catalog=compile_catalog
    result=b.run(root,write)
    return {**result,'targetSchema':43,'commercialModels':62}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--write',action='store_true');parser.add_argument('--check',action='store_true');args=parser.parse_args()
    try:print(json.dumps(run(args.root,args.write)))
    except (OSError,ValueError,KeyError,TypeError) as error:print(type(error).__name__+': '+str(error),file=sys.stderr);raise SystemExit(1)
