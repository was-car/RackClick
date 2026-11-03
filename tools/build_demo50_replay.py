"""Create the optional Windows Demo50 API replay; inventory only, no credentials.

Development inputs are explicit: the accepted private command receipts and the
public Demo50 inventory package. The output never includes actor/session/receipt
security metadata. It is NOT a generic JSON importer or a PostgreSQL backup.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
KINDS = frozenset({'site.create', 'building.create', 'room.create', 'rack.create',
    'rack.createHardware', 'device.create', 'device.createHardware',
    'connections.createBatch', 'ports.update', 'device.update'})
COLLECTIONS = ('sites','buildings','rooms','racks','devices','portGroups','ports','connections')
UUID = re.compile(r'^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$')
COUNTS = {'sites':66,'buildings':88,'rooms':226,'racks':180,'devices':1563,
          'portGroups':2869,'ports':20665,'connections':2207}

def encode(value):
    return (json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'))+'\n').encode('ascii')

def build(receipts: Path, portable: Path) -> dict:
    manifest=json.loads((portable/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('format')!='RackClickDemo50Inventory-v1' or manifest.get('schemaVersion')!=43 or manifest.get('securityIncluded') is not False:
        raise ValueError('demo_manifest_invalid')
    source=json.loads(receipts.read_text(encoding='utf-8'))
    if len(source)!=50 or len(manifest['customers'])!=50:
        raise ValueError('demo_customer_count_invalid')
    result={'format':'RackClickDemo50Replay-v1','schemaVersion':43,'securityIncluded':False,
            'productionDefault':False,'counts':COUNTS,'customers':[]}
    seen=set()
    for index,(entry,meta) in enumerate(zip(source,manifest['customers']),1):
        if entry['key']!=meta['key'] or meta['key']!=f'c{index:02}' or entry['customerId']!=meta['customerId']:
            raise ValueError('demo_source_binding_invalid')
        if meta['file']!=f'c{index:02}.inventory.json': raise ValueError('demo_file_invalid')
        raw=(portable/meta['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=meta['sha256'] or len(raw)!=meta['bytes']:
            raise ValueError('demo_inventory_hash_invalid')
        exported=json.loads(raw)
        inventory=copy.deepcopy(exported['inventory'])
        if set(inventory)!=set(COLLECTIONS): raise ValueError('demo_inventory_shape_invalid')
        for rows in inventory.values():
            for row in rows:
                if not UUID.fullmatch(row['id']) or row['id'] in seen: raise ValueError('demo_source_id_invalid')
                seen.add(row['id'])
        commands=[]; wired=set()
        original_names={}
        for receipt in entry['receipts']:
            kind=receipt['kind']; payload=copy.deepcopy(receipt['payload']); response=receipt['response']['result']
            if kind not in KINDS or kind=='device.update': raise ValueError('demo_command_invalid')
            created=list(response.get('createdIds',[]))
            if any(not UUID.fullmatch(v) for v in created): raise ValueError('demo_created_id_invalid')
            resource=response['resourceId']
            if not UUID.fullmatch(resource): raise ValueError('demo_resource_id_invalid')
            commands.append({'type':kind,'payload':payload,'sourceResourceId':resource,'sourceCreatedIds':created})
            if kind.startswith('device.create'): original_names[resource]=payload['name']
            if kind=='connections.createBatch':
                if len(created)!=len(payload['pairs']): raise ValueError('demo_connections_count_invalid')
                wired.update(created)
        # The accepted final exports include the ten concurrent terminal renames
        # and three GUI connections made AFTER the original replay receipts.
        for device in inventory['devices']:
            if device['id'] in original_names and original_names[device['id']]!=device['name']:
                commands.append({'type':'device.update','payload':{'id':device['id'],'name':device['name']},
                                 'sourceResourceId':device['id'],'sourceCreatedIds':[]})
        for connection in inventory['connections']:
            if connection['id'] not in wired:
                pair={k:connection[k] for k in ('fromPortId','toPortId','note','color','patch')}
                commands.append({'type':'connections.createBatch','payload':{'pairs':[pair]},
                                 'sourceResourceId':connection['id'],'sourceCreatedIds':[connection['id']]})
            # Time belongs to the newly committed connection, not the old lab.
            connection.pop('createdAt',None)
        result['customers'].append({'key':meta['key'],'name':meta['name'],'sourceCustomerId':meta['customerId'],
                                   'commands':commands,'expected':inventory})
    actual={k:sum(len(c['expected'][k]) for c in result['customers']) for k in COLLECTIONS}
    if actual!=COUNTS: raise ValueError('demo_total_count_invalid')
    return result

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipts',required=True,type=Path)
    parser.add_argument('--portable',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    if args.output.exists(): raise ValueError('demo_replay_output_exists')
    data=encode(build(args.receipts,args.portable))
    with args.output.open('xb') as stream: stream.write(data)
    print(json.dumps({'result':'PASS','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                      'customers':50,'securityIncluded':False}))
    return 0

if __name__=='__main__': sys.exit(main())
