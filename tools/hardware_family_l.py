"""Family L authoring: explicit mounting, fixed BOM, sparse dimensions and closed media.

API validate_model(row, expected_revision) returns the exact ORIGINAL unchanged.
Power form is classification only; no cord-end, voltage, pinout or circuit validation.
All historical validators are immutable. Geometry primitives come from private v3.
"""
from __future__ import annotations
import importlib.util
import re
import json
from pathlib import Path
ROOT = Path(__file__).absolute().parents[1]
_spec = importlib.util.spec_from_file_location('family_v2_private_v3', ROOT/'tools/hardware_physical_v3.py')
engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(engine)
base, c, g = engine.base, engine.c, engine.g
CatalogError, expand = engine.CatalogError, engine.expand
fields, number, color, text, rect, overlaps = base.fields, base.number, base.color, base.text, base.rect, base.overlaps
ALLOWED_TYPES = ('rj45','sfp','sfp28','sfp56','qsfp','qsfpdd','power','console','idc','ipc','fiber','sfpdd','cfp2','sas','dsl','telephony','isdn','expansion','power_dc')
PHYSICAL_CONNECTORS = {'power': ('iec-c13', 'iec-c14', 'iec-c19', 'iec-c20', 'nema-5-15p', 'nema-5-15r', 'nema-5-20p', 'nema-5-20r', 'nema-l5-30p', 'nema-l5-30r', 'nema-l6-20p', 'nema-l6-20r', 'nema-l6-30p', 'nema-l6-30r', 'iec60309-16a-2p-e-plug', 'iec60309-16a-2p-e-connector', 'iec60309-32a-2p-e-plug'), 'console': ('serial-8p8c', 'serial-10p10c', 'serial-de9', 'serial-rj12'), 'idc': ('idc-110', 'idc-dual-110-krone')}


PHYSICAL_CONNECTORS = {**PHYSICAL_CONNECTORS,
 'power': (*PHYSICAL_CONNECTORS['power'],'schuko-f'),
 'console': (*PHYSICAL_CONNECTORS['console'],'serial-mini-din8','serial-usb-c'),
 'ipc': ('belden-revconnect-core',),
 'fiber': ('lc-duplex-upc','lc-simplex-upc','sc-duplex-upc','sc-simplex-upc','sc-simplex-apc'),
 'sas': ('sff-8644','sff-8088'),
 'power_dc': ('dc-barrel','unifi-smartpower','usb-c-pd','dc-terminal-2p','dc-terminal-3p','dc-terminal-6p')}
MOUNT_TARGETS={'rack':'rack','shelf':'rack','desktop':'parent','rackContainer':'room','vertical0U':'rack','sharedU':'parent','wall':'room','pole':'room','din':'room','floor':'room'}
INTERFACE_ROLES=('ethernet','storage','cluster','ha','management','optical-line','optical-client','serial','proprietary','voice','dsl')
SIGNAL_ROLES=('tx','rx','bidi','passive')
POWER_SYSTEMS=('dc','usb-pd','unifi-smartpower')
# The new vocabulary has one reviewed source; the K module stays immutable.
_contract=json.loads((ROOT/'tools/hardware_family_l_contract.json').read_text())
PHYSICAL_CONNECTORS={**PHYSICAL_CONNECTORS,**{key:tuple(dict.fromkeys((*PHYSICAL_CONNECTORS.get(key,()),*values))) for key,values in _contract['typeDescriptors'].items()}}

def validate_mounting(m):
    mounting=m['mounting']; fields(mounting,'kind target','capacityU parentProfileKeys')
    c.require(m['kind'] in MOUNT_TARGETS and mounting['kind']==m['kind'] and mounting['target']==MOUNT_TARGETS[m['kind']], 'family_l_mount_invalid')
    c.require(type(m['rackUnits']) is int and (1<=m['rackUnits']<=60 if m['kind'] in ('rack','shelf') else m['rackUnits']==0), 'family_l_mount_invalid')
    if m['kind']=='rackContainer':
        c.require(type(mounting.get('capacityU')) is int and 1<=mounting['capacityU']<=60 and m['groups']==[], 'family_l_container_invalid')
    else: c.require('capacityU' not in mounting,'family_l_container_invalid')
    if 'parentProfileKeys' in mounting:
        keys=mounting['parentProfileKeys']; c.require(m['kind']=='sharedU' and isinstance(keys,list) and len(keys)==len(set(keys)) and all(isinstance(v,str) and v.strip() for v in keys),'family_l_parent_invalid')
    if m['kind'] in ('shelf','desktop'):
        c.require(all(v is not None for v in m['dimensionsMm'].values()),'family_l_dimensions_required')

def validate_configuration(m):
    rows=m.get('configuration',[]); c.require(isinstance(rows,list) and len(rows)<=64,'family_l_configuration_invalid')
    seen=set()
    for row in rows:
        fields(row,'slot partNumber quantity description')
        for key in ('slot','partNumber','description'): text(row[key],1000)
        c.require(row['slot'] not in seen and type(row['quantity']) is int and 1<=row['quantity']<=64,'family_l_configuration_invalid');seen.add(row['slot'])

def validate_continuities(m):
    rows=m.get('continuities',[]); c.require(isinstance(rows,list) and len(rows)<=32,'family_l_continuity_invalid')
    groups={g['key']:g for g in m['groups']}; seen=set()
    for row in rows:
        fields(row,'fromGroup toGroup count mapping tracingAvailable')
        a,b=groups.get(row['fromGroup']),groups.get(row['toGroup'])
        c.require(a is not None and b is not None and a is not b and row['mapping']=='one-to-one' and row['tracingAvailable'] is False and type(row['count']) is int and row['count']==a['count']==b['count'] and (a['type'],b['type']) in (('rj45','rj45'),('rj45','idc'),('rj45','ipc')),'family_l_continuity_invalid')
        c.require(a['key'] not in seen and b['key'] not in seen,'family_l_continuity_duplicate');seen.update((a['key'],b['key']))


def validate_physical_connector(raw_type, value):
    c.require(value is None or isinstance(value,str) and value in PHYSICAL_CONNECTORS.get(raw_type,()),
              'family_v2_physical_connector_invalid')
    return value


def validate_structure(model):
    c.require(isinstance(model['slots'],list),'family_v2_slots_invalid')
    if model['kind']=='shelf':
        c.require(len(model['slots'])==1 and model['groups']==[] and model['passthrough'] is None,'family_v2_shelf_invalid')
        slot=model['slots'][0]; fields(slot,'key dimensionsMm'); c.require(slot['key']=='main','family_v2_slot_invalid')
        fields(slot['dimensionsMm'],'width height depth')
        for key,value in slot['dimensionsMm'].items():
            number(value,.01); c.require(value<=model['dimensionsMm'][key],'family_v2_slot_bounds_invalid')
    else:
        c.require(model['slots']==[],'family_v2_slots_unsupported')


def validate_continuity(model):
    rule=model['passthrough']
    if rule is None:return
    fields(rule,'frontGroup rearGroup count mapping tracingAvailable')
    c.require(rule['mapping']=='one-to-one' and rule['tracingAvailable'] is False,'family_v2_tracing_unsupported')
    c.require(isinstance(rule['frontGroup'],str) and isinstance(rule['rearGroup'],str) and
              type(rule['count']) is int and 1<=rule['count']<=96,'family_v2_continuity_invalid')
    groups={group['key']:group for group in model['groups']}
    front,rear=groups.get(rule['frontGroup']),groups.get(rule['rearGroup'])
    c.require(front is not None and rear is not None and front is not rear and front['face']=='front' and rear['face']=='rear' and
              front['count']==rear['count']==rule['count'] and
              (front['type'],rear['type']) in (('rj45','rj45'),('rj45','idc'),('rj45','ipc')),'family_v2_continuity_invalid')


def validate_model(row, expected_revision):
    fields(row,'definition visual evidence')
    m=row['definition'];fields(m,'key revision identity provenance kind rackUnits dimensionsMm color slots groups passthrough mounting','configuration continuities')
    c.key(m['key']);c.require(m['revision']==expected_revision,'batch50_revision_invalid')
    fields(m['identity'],'manufacturer family model sku')
    for v in m['identity'].values():text(v,200)
    fields(m['provenance'],'kind source assets');c.require(m['provenance']['kind']=='manufacturer-specification' and m['provenance']['assets']==[],'batch50_provenance_invalid')
    c.require(isinstance(m['provenance']['source'],str) and m['provenance']['source'].startswith('https://'),'batch50_source_invalid')
    fields(m['dimensionsMm'],'width height depth')
    for v in m['dimensionsMm'].values():
        if v is not None:number(v,.01)
    validate_mounting(m); validate_configuration(m)
    color(m['color']); validate_structure(m)
    groups=m['groups'];c.require(isinstance(groups,list) and 0<=len(groups)<=32,'batch50_groups_invalid');seen=set()
    for x in groups:
        fields(x,'key type count face name prefix powerRole','physicalConnector physicalFace interfaceRole signalRole powerSystem');c.key(x['key']);c.require(x['key'] not in seen,'batch50_group_duplicate');seen.add(x['key'])
        c.require(x['type'] in ALLOWED_TYPES and type(x['count']) is int and 1<=x['count']<=512 and x['face'] in ('front','rear'),'batch50_group_invalid')
        c.require(x['powerRole'] in ('inlet','outlet') if x['type'] in ('power','power_dc') else x['powerRole']=='unspecified','family_v2_role_invalid');text(x['name'],200)
        validate_physical_connector(x['type'], x.get('physicalConnector'))
        if 'physicalFace' in x:c.require(x['physicalFace'] in ('front','rear','top','bottom'),'family_l_physical_face_invalid')
        if 'interfaceRole' in x:c.require(x['interfaceRole'] in INTERFACE_ROLES,'family_l_interface_role_invalid')
        if 'signalRole' in x:c.require(x['signalRole'] in SIGNAL_ROLES,'family_l_signal_role_invalid')
        if x['type']=='power_dc':
            expected='unifi-smartpower' if x.get('physicalConnector')=='unifi-smartpower' else 'usb-pd' if x.get('physicalConnector')=='usb-c-pd' else 'dc'
            c.require(x.get('powerSystem')==expected,'family_l_power_system_invalid')
        else:c.require('powerSystem' not in x,'family_l_power_system_invalid')
        for field in ('name','prefix'):
            value=x[field]
            c.require(isinstance(value,str) and len(value)<=100 and (field!='name' or bool(value.strip())) and not any(ord(t)<32 or 0x7f<=ord(t)<=0x9f or 0xd800<=ord(t)<=0xdfff for t in value),'family_v2_group_'+field+'_invalid')
        c.require(isinstance(x['prefix'],str) and len(x['prefix'])<=200 and not any(ord(t)<32 for t in x['prefix']),'batch50_text_invalid')
    c.require(sum(x['count'] for x in groups)<=1024,'batch50_port_limit')
    validate_continuity(m); validate_continuities(m)
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
