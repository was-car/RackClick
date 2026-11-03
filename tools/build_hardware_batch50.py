"""Compile the reviewed 50-model batch; previous catalogues/migrations are immutable."""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT=Path(__file__).absolute().parents[1]
spec=importlib.util.spec_from_file_location('batch50_helpers',ROOT/'tools/build_hardware_catalog23.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
c=g.c
SOURCES=['development/hardware/batch50/'+n+'.json' for n in ('synology','qnap','network')]
COUNTS=[20,10,20]
LOCK='development/hardware/catalog-schema24.lock.json'
BASE='development/server/database/023-qnap-hardware.sql'
SERVER='development/server/src/RackClick.Server/Batch50HardwareProfiles.Generated.cs'
FRONTEND='development/frontend/src/hardware-batch50.generated.json'
SQL='development/server/database/024-batch50-hardware.sql'
MANIFEST='development/hardware/catalog-batch50.manifest.json'
TARGETS='development/server/src/RackClick.Server/Batch50Hardware.Generated.targets'
REVISION='batch50-20261030-v1'
SUPPORT_REVISION='batch50-support-20261030-v1'
EXPECTED_LOCK_SHA256='ae5ed8239ed2376c2b6f3d62fdca89ad8d27ef47ff87c62e40c9abce60b5363d'
STATE='curated_development_not_a_release'

def number(x,low=0,high=10000):
    c.require(type(x) in (int,float) and math.isfinite(x) and low<=x<=high,'batch50_number_invalid')
def color(x):c.require(isinstance(x,str) and re.fullmatch(r'#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?',x) is not None,'batch50_color_invalid')
def text(x,limit=1000):
    c.require(isinstance(x,str) and 0<len(x)<=limit and not any(ord(t)<32 for t in x),'batch50_text_invalid')
def fields(x,required,optional=''):
    c.require(isinstance(x,dict) and set(required.split())<=set(x)<=set((required+' '+optional).split()),'batch50_fields_invalid')
def rect(x,face):
    for n in ('x','y','w','h'):number(x[n],0 if n in ('x','y') else .01)
    c.require(x['x']+x['w']<=face['width'] and x['y']+x['h']<=face['height'],'batch50_bounds_invalid')
def overlaps(a,b):return min(a['x']+a['w'],b['x']+b['w'])>max(a['x'],b['x'])+.01 and min(a['y']+a['h'],b['y']+b['h'])>max(a['y'],b['y'])+.01
def expand(face):
    result=[]
    for b in face['banks']:
        for row,ordinals in enumerate(b['rows']):
            for col,ordinal in enumerate(ordinals):
                result.append(dict(groupKey=b['groupKey'],ordinal=ordinal,x=b['x']+col*b['dx'],y=b['y']+row*b['dy'],w=b['w'],h=b['h']))
    return result

def validate_model(row):
    fields(row,'definition visual evidence')
    m=row['definition'];fields(m,'key revision identity provenance kind rackUnits dimensionsMm color slots groups passthrough')
    c.key(m['key']);c.require(m['revision']==REVISION,'batch50_revision_invalid')
    fields(m['identity'],'manufacturer family model sku')
    for v in m['identity'].values():text(v,200)
    fields(m['provenance'],'kind source assets');c.require(m['provenance']['kind']=='manufacturer-specification' and m['provenance']['assets']==[],'batch50_provenance_invalid')
    c.require(isinstance(m['provenance']['source'],str) and m['provenance']['source'].startswith('https://'),'batch50_source_invalid')
    c.require(m['kind'] in ('rack','desktop') and type(m['rackUnits']) is int and (m['rackUnits']==0 if m['kind']=='desktop' else 1<=m['rackUnits']<=8),'batch50_mount_invalid')
    fields(m['dimensionsMm'],'width height depth')
    for v in m['dimensionsMm'].values():number(v,.01)
    color(m['color']);c.require(m['slots']==[] and m['passthrough'] is None,'batch50_structure_unsupported')
    groups=m['groups'];c.require(isinstance(groups,list) and 1<=len(groups)<=32,'batch50_groups_invalid');seen=set()
    for x in groups:
        fields(x,'key type count face name prefix powerRole');c.key(x['key']);c.require(x['key'] not in seen,'batch50_group_duplicate');seen.add(x['key'])
        c.require(x['type'] in ('rj45','sfp','power') and type(x['count']) is int and 1<=x['count']<=256 and x['face'] in ('front','rear'),'batch50_group_invalid')
        c.require(x['powerRole']==('inlet' if x['type']=='power' else 'unspecified'),'batch50_role_invalid');text(x['name'],200)
        c.require(isinstance(x['prefix'],str) and len(x['prefix'])<=200 and not any(ord(t)<32 for t in x['prefix']),'batch50_text_invalid')
    c.require(sum(x['count'] for x in groups)<=256,'batch50_port_limit')
    fields(row['visual'],'faces');faces=row['visual']['faces'];fields(faces,'front rear');all_sockets=[]
    for side,f in faces.items():
        fields(f,'width height plate decorations banks');number(f['width'],100,2000);number(f['height'],60,2000)
        fields(f['plate'],'x y w h fill','stroke radius');rect(f['plate'],f);color(f['plate']['fill'])
        if 'stroke' in f['plate']:color(f['plate']['stroke'])
        if 'radius' in f['plate']:number(f['plate']['radius'])
        c.require(isinstance(f['decorations'],list) and len(f['decorations'])<=400,'batch50_decorations_invalid')
        for d in f['decorations']:
            c.require(isinstance(d,dict),'batch50_decoration_invalid')
            kind=d.get('kind')
            if kind in ('rect','tray','vent'):
                requirements={'rect':('kind x y w h fill','stroke radius'),'tray':('kind x y w h','lock'),'vent':('kind x y w h count','')}
                fields(d,*requirements[kind]);rect(d,f)
                if kind=='rect':
                    color(d['fill'])
                    if 'stroke' in d:color(d['stroke'])
                    if 'radius' in d:number(d['radius'])
                if kind=='tray' and 'lock' in d:c.require(type(d['lock']) is bool,'batch50_decoration_invalid')
                if kind=='vent':c.require(type(d['count']) is int and 1<=d['count']<=100,'batch50_decoration_invalid')
            elif kind in ('circle','fan'):
                fields(d,'kind cx cy r'+(' fill' if kind=='circle' else ''),'stroke' if kind=='circle' else '')
                for key in ('cx','cy','r'):number(d[key],.01 if key=='r' else 0)
                c.require(0<=d['cx']-d['r'] and d['cx']+d['r']<=f['width'] and 0<=d['cy']-d['r'] and d['cy']+d['r']<=f['height'],'batch50_bounds_invalid')
                if kind=='circle':
                    color(d['fill'])
                    if 'stroke' in d:color(d['stroke'])
            elif kind=='text':
                fields(d,'kind x y text size fill','anchor');number(d['x'],0,f['width']);number(d['y'],0,f['height']);number(d['size'],1,80);text(d['text'],200);color(d['fill']);c.require(d.get('anchor','start') in ('start','middle','end'),'batch50_decoration_invalid')
            elif kind=='line':
                fields(d,'kind x1 y1 x2 y2 stroke','width');color(d['stroke'])
                for n in ('x1','x2'):number(d[n],0,f['width'])
                for n in ('y1','y2'):number(d[n],0,f['height'])
                if 'width' in d:number(d['width'],.01,20)
            else:raise c.CatalogError('batch50_decoration_invalid')
        c.require(isinstance(f['banks'],list) and len(f['banks'])<=64,'batch50_banks_invalid')
        for b in f['banks']:
            fields(b,'groupKey rows x y dx dy w h','labels');c.require(b['groupKey'] in seen,'batch50_bank_group_invalid')
            for n in ('x','y','dx','dy'):number(b[n])
            for n in ('w','h'):number(b[n],8,100)
            c.require(isinstance(b['rows'],list) and 1<=len(b['rows'])<=128 and all(isinstance(v,list) and 1<=len(v)<=256 and all(type(x) is int and x>=1 for x in v) for v in b['rows']),'batch50_bank_ordinals_invalid')
            if 'labels' in b:
                c.require(isinstance(b['labels'],dict) and set(b['labels'])<={str(x) for xs in b['rows'] for x in xs},'batch50_labels_invalid')
                for v in b['labels'].values():text(v,80)
        sockets=expand(f)
        for s in sockets:rect(s,f)
        c.require(not any(overlaps(a,b) for i,a in enumerate(sockets) for b in sockets[i+1:]),'batch50_sockets_overlap')
        actual=[(s['groupKey'],s['ordinal']) for s in sockets]
        expected=[(x['key'],i) for x in groups if x['face']==side for i in range(1,x['count']+1)]
        c.require(len(actual)==len(set(actual)) and set(actual)==set(expected),'batch50_socket_mapping_invalid');all_sockets+=actual
    fields(row['evidence'],'sources referenceAssets limits dimensionsBasis')
    e=row['evidence'];c.require(isinstance(e['sources'],list) and e['sources'] and all(isinstance(x,dict) for x in e['sources']) and any(x.get('url')==m['provenance']['source'] for x in e['sources']),'batch50_evidence_invalid')
    for source in e['sources']:
        fields(source,'url kind observed','sha256 bytes retrievedFrom');c.require(isinstance(source['url'],str) and source['url'].startswith('https://'),'batch50_source_invalid');text(source['observed'],5000)
        if 'retrievedFrom' in source:c.require(isinstance(source['retrievedFrom'],str) and source['retrievedFrom'].startswith('https://'),'batch50_source_invalid')
        if source.get('sha256') is not None:c.require(isinstance(source['sha256'],str) and re.fullmatch('[0-9a-f]{64}',source['sha256']) is not None,'batch50_pin_invalid')
    c.require(isinstance(e['referenceAssets'],list) and e['referenceAssets'],'batch50_reference_missing')
    for a in e['referenceAssets']:
        fields(a,'path sha256 view match');c.require(isinstance(a['path'],str) and isinstance(a['sha256'],str) and re.fullmatch('[0-9a-f]{64}',a['sha256']) is not None,'batch50_pin_invalid');text(a['match'],200);c.require(a['view'] in ('front','rear','angle'),'batch50_face_reference_missing')
    c.require({'front','rear'}<=set(x['view'] for x in e['referenceAssets']),'batch50_face_reference_missing')
    c.require(isinstance(e['limits'],list) and all(isinstance(v,str) for v in e['limits']),'batch50_limits_invalid');text(e['dimensionsBasis'],5000)
    return row

def support_definition():
    return dict(key='shelf-5u-deep',revision=SUPPORT_REVISION,identity={k:None for k in ('manufacturer','family','model','sku')},provenance=dict(kind='own-synthetic',source='docs/CONTRATO-HARDWARE-LOTE50.md',assets=[]),kind='shelf',rackUnits=5,dimensionsMm=dict(width=482.6,height=222,depth=500),color='#46505c',slots=[dict(key='main',dimensionsMm=dict(width=440,height=190,depth=500))],groups=[],passthrough=None)

def server_source(models):
    q=lambda x:json.dumps(x,ensure_ascii=True)
    lines=['// <auto-generated> tools/build_hardware_batch50.py; do not edit. </auto-generated>','namespace RackClick.Server;','using static RackClick.Server.InventoryHardwareProfiles;','internal static class Batch50HardwareProfiles','{','    internal static readonly Registry Catalog = new([']
    for m in models:
        d=m['dimensionsMm'];groups=', '.join('new('+', '.join([q(x['key']),q(x['type']),str(x['count']),q(x['face']),q(x['name']),q(x['prefix'])])+') { PowerRole = '+q(x['powerRole'])+' }' for x in m['groups'])
        slots=', '.join('new('+', '.join([q(s['key'])]+[str(s['dimensionsMm'][k])+'m' for k in ('width','height','depth')])+')' for s in m['slots'])
        args=[q(m['key']),str(m['rackUnits'])]+[str(d[k])+'m' for k in ('width','height','depth')]+[q(m['color']),'['+groups+']',q(m['revision'])]
        extra=''.join(', '+k.title()+' = '+q(v) for k,v in m['identity'].items() if v is not None)
        lines.append('        new('+', '.join(args)+') { Kind = '+q(m['kind'])+', DefinitionSha256 = '+q(c.sha(c.canonical(m)))+', Slots = ['+slots+'], Passthrough = null'+extra+' },')
    return ('\n'.join(lines+['    ]);','}',''])).encode('ascii')

def targets_source(inputs):
    parts=['<!-- Auto-generated by tools/build_hardware_batch50.py. -->','<Project>','  <Target Name="VerifyBatch50HardwareCatalog" BeforeTargets="CoreCompile">','    <ItemGroup>']
    for path,sha in inputs.items():parts.append('      <_Batch50Input Include="$(MSBuildThisFileDirectory)../../../../'+path+'"><ExpectedHash>'+sha+'</ExpectedHash></_Batch50Input>')
    parts+=['    </ItemGroup>','    <Error Condition="!Exists(\'%(_Batch50Input.Identity)\')" Code="batch50_catalog_stale" Text="batch50_catalog_stale" />','    <GetFileHash Files="@(_Batch50Input)" Algorithm="SHA256"><Output TaskParameter="Items" ItemName="_Batch50Hashed" /></GetFileHash>','    <Error Condition="\'%(_Batch50Hashed.FileHash)\' != \'%(_Batch50Hashed.ExpectedHash)\'" Code="batch50_catalog_stale" Text="batch50_catalog_stale" />','  </Target>','</Project>','']
    return '\n'.join(parts).encode('ascii')

def compile_catalog(root):
    raw={n:c.path(root,n).read_bytes() for n in [*SOURCES,LOCK,BASE,'tools/build_hardware_batch50.py']};lock=c.load(raw[LOCK])
    c.require(c.sha(raw[LOCK])==EXPECTED_LOCK_SHA256,'batch50_lock_not_reviewed')
    c.require(lock['targetSchema']==24 and lock['state']==STATE and lock['sourceSha256']=={n:c.sha(raw[n]) for n in SOURCES} and lock['baseMigrationSha256']==c.sha(raw[BASE]),'batch50_input_changed')
    rows=[]
    for source,count in zip(SOURCES,COUNTS):
        data=c.load(raw[source]);fields(data,'formatVersion revision models');c.require(type(data['formatVersion']) is int and data['formatVersion']==1 and data['revision']==REVISION and len(data['models'])==count,'batch50_count_invalid')
        rows += [validate_model(row) for row in data['models']]
    keys=[r['definition']['key'] for r in rows];identities=[tuple(r['definition']['identity'][k] for k in ('manufacturer','model','sku')) for r in rows]
    c.require(len(rows)==50 and len(set(keys))==50 and len(set(identities))==50 and sorted(keys)==lock['modelKeys'],'batch50_models_invalid')
    rows.sort(key=lambda r:r['definition']['key']);models=[r['definition'] for r in rows]
    # Add no accessory unless a reviewed desktop actually needs its depth.
    needs_deep=any(m['kind']=='desktop' and m['dimensionsMm']['depth']>300 for m in models)
    if needs_deep:models.append(support_definition())
    pins=[dict(key=m['key'],revision=m['revision'],sha256=c.sha(c.canonical(m))) for m in models]
    c.require(pins==lock['definitions'],'batch50_definition_changed')
    views=[]
    for m in models:
        v=c.projection(dict(definitions=[m]));v['synthetic']=m['kind']=='shelf';p=v['profiles'][0]
        if m['kind']!='shelf':
            row=next(x for x in rows if x['definition']['key']==m['key']);p.update(identity=m['identity'],source=m['provenance']['source'],visual=row['visual'])
            e=row['evidence'];unverified=any(re.search(r'unverified',a['match'],re.I) for a in e['referenceAssets'])
            family=any(re.search(r'family|shared',a['match'],re.I) for a in e['referenceAssets']) or any(re.search(r'family|4X.*4G|4G.*4X',v,re.I) for v in e['limits'])
            p.update(referenceScope='unverified_reference' if unverified else 'family_reference' if family else 'model_reference',reviewLimits=e['limits'])
        for group,original in zip(p['groups'],m['groups']):group['powerRole']=original['powerRole']
        views.append(v)
    catalogues=[]
    for v in views:
        prior=next((p for p in catalogues if p['version']==v['version']),None)
        if prior:prior['profiles']+=v['profiles']
        else:catalogues.append(v)
    sql=b'\n'.join(line for line in g.sql_source(models,pins).splitlines() if not line.startswith(b'--'))+b'\n'
    # SQL helper emits only immutable definitions/components and seals them.
    sql=b'-- Auto-generated reviewed batch50; SQL001-023 unchanged.\n-- Nominal dimensions do not certify physical installation or optional modules.\n'+sql
    outputs={SERVER:server_source(models),FRONTEND:g.pretty(catalogues),SQL:sql}
    inputs={n:c.sha(v) for n,v in raw.items()}
    outputs[MANIFEST]=g.pretty(dict(formatVersion=1,targetSchema=24,catalogKey='rackclick-batch50',state=STATE,inputs=inputs,files={n:c.sha(v) for n,v in outputs.items()},definitions=pins))
    outputs[TARGETS]=targets_source({**inputs,**{n:c.sha(v) for n,v in outputs.items()}})
    return outputs

def run(root,write=False):
    outputs=compile_catalog(root);targets={n:c.path(root,n) for n in outputs}
    for p in targets.values():c.require(not p.exists() or p.is_file(),'batch50_output_invalid')
    if write:
        staged={}
        try:
            for n,p in targets.items():
                p.parent.mkdir(parents=True,exist_ok=True);fd,temp=tempfile.mkstemp(prefix='.batch50-',dir=p.parent);staged[n]=temp
                with os.fdopen(fd,'wb') as stream:stream.write(outputs[n]);stream.flush();os.fsync(stream.fileno())
            for n,p in targets.items():os.replace(staged[n],p)
        finally:
            for temp in staged.values():
                if os.path.lexists(temp):os.unlink(temp)
    else:
        for n,p in targets.items():c.require(p.is_file() and p.read_bytes()==outputs[n],'batch50_catalog_stale')
    return dict(status='written' if write else 'verified',targetSchema=24,commercialModels=50,files={n:c.sha(v) for n,v in outputs.items()},databaseChanged=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--write',action='store_true');mode.add_argument('--check',action='store_true');args=parser.parse_args()
    try:print(json.dumps(run(ROOT,args.write)));return 0
    except (c.CatalogError,OSError) as error:print(json.dumps(dict(status='failed',code=str(error) if isinstance(error,c.CatalogError) else 'batch50_io_failed')));return 1
if __name__=='__main__':sys.exit(main())
