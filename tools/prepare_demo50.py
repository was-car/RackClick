"""Prepare optional Demo50 in a NEW private PostgreSQL17 laboratory only.

No connection-string or existing-database input is accepted. All inventory is
created through authorized server commands. Full backups/access remain private;
portable output contains inventory only. The installed application is untouched.
"""
from __future__ import annotations
import argparse
import base64
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'development/server/tests'))
from pg_support import Lab, Client, Database, literal, protect_directory, NO_WINDOW, toolchain
from test_hardware_selected506l import CATALOG_TABLES
from build_demo50_plan import build_plan, load_definitions, validate_plan, plan_bytes, definition_digest

SERVER_SHA = 'b756c907eac9b949d14e70bea63f2f5fbc05b73cc6bc1cb1eccdf64e3d4d8ed3'
FRONTEND_SHA = '1ecb9bede2009177715a12ff0275e891f9f89475ca81560555c8f2abe9f85266'
COLLECTIONS = ('sites','buildings','rooms','racks','devices','portGroups','ports','connections')
INVENTORY_TABLES = ('customer','inventory_site','inventory_building','inventory_room','inventory_rack',
 'inventory_device','inventory_port_group','inventory_port','inventory_connection','inventory_connection_endpoint')
NS = uuid.UUID('fa421d40-8c87-45df-aefe-f77b9aa8c358')
BENCHMARK_CUSTOMERS = ('c01','c11','c21','c29','c35','c41','c47','c02','c12','c42')

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path, value): Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def canonical(value): return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',',':'))
def normalized(project):
 return {k: sorted(project[k], key=lambda row:row['id']) for k in COLLECTIONS} | {'customerId':project['customerId'],'revision':project['revision']}

class DemoLab(Lab):
 def environment(self):
  env=super().environment();env['MfaKeyStore__Enabled']='false';return env

class Rejected(RuntimeError): pass

class Session:
 def __init__(self, client, customer, seed, key):
  self.client=client;self.customer=customer;self.seed=seed;self.key=key;self.route=f'/api/v1/customers/{customer}'
  self.actor=client.request('GET','/api/v1/me').json()['user']['id'];self.revision=self.project()['revision'];self.receipts=[]
 def project(self):
  response=self.client.request('GET',self.route+'/project')
  if response.status!=200: raise Rejected('project_read_failed')
  return response.json()
 def send(self, payload, *, kind='device.createHardware', symbol=None, key=None, revision=None, status=200):
  expected=self.revision if revision is None else revision
  request=key or str(uuid.uuid5(NS,self.seed+'/'+self.key+'/'+(symbol or str(uuid.uuid4()))))
  response=self.client.request('POST',self.route+'/commands',{'type':kind,'payload':payload},
   {'X-RackClick-Actor':self.actor,'If-Match':f'"{expected}"','Idempotency-Key':request})
  if response.status!=status: raise Rejected(f'command_failed:{kind}:{status}:{response.status}:{response.json().get("error", "unavailable")}')
  if status==200:
   value=response.json();self.revision=max(self.revision,value['revision'])
   self.receipts.append({'kind':kind,'payload':payload,'requestId':request,'expectedRevision':expected,'response':value})
  return response

def clone_client(server, original):
 client=Client(server);client.cookie=original.cookie;client.csrf=original.csrf;return client

def login(server, name, password):
 client=Client(server);waited=0
 for _ in range(95):
  response=client.login(name,password)
  if response.status==200:return client,waited
  if response.status!=429:raise Rejected('laboratory_login_failed')
  time.sleep(1);waited+=1
 raise Rejected('login_rate_limit_did_not_clear')

def house_mutation(client, route, body, seed, symbol, status=200):
 revision=client.request('GET','/api/v1/systemhaus').json()['revision'];actor=client.request('GET','/api/v1/me').json()['user']['id']
 response=client.request('POST',route,body,{'X-RackClick-Actor':actor,'If-Match':f'"{revision}"','Idempotency-Key':str(uuid.uuid5(NS,seed+'/house/'+symbol))})
 if response.status!=status:raise Rejected(f'house_command_failed:{route}:{response.status}:{response.json().get("error", "unavailable")}')
 return response.json()

def add_profile(session, model, assignment, refs):
 parent=None;slot=None;support_id=None
 if assignment.get('support'):
  support=assignment['support'];support_id=session.send({'profileKey':support['profileKey'],'profileVersion':support['profileVersion'],
   'rackId':refs[assignment['rackKey']],'name':'Soporte QA '+assignment['key']},symbol=assignment['key']+'/support').json()['result']['resourceId']
  parent=support_id;slot=support['slotKey']
 payload={'profileKey':model['key'],'profileVersion':model['revision'],'name':assignment['name']}
 kind='device.createHardware';rack=refs.get(assignment.get('rackKey'));room=refs[assignment['roomKey']]
 if model['kind']=='rackContainer':payload['roomId']=room;kind='rack.createHardware'
 elif model['kind'] in {'wall','pole','floor','din'}:payload['roomId']=room
 else:
  payload['rackId']=rack
  if parent:payload.update(mountParentId=parent,mountSlotKey=slot)
  if model['kind']=='vertical0U':slot='vertical-left';payload['mountSlotKey']=slot
 resource=session.send(payload,kind=kind,symbol=assignment['key']).json()['result']['resourceId']
 return {'profileKey':model['key'],'profileVersion':model['revision'],'resourceId':resource,
  'deviceId':None if kind=='rack.createHardware' else resource,'rack':rack,'room':room,'supportId':support_id,
  'supportKey':assignment.get('support',{}).get('profileKey'),'slot':slot,'request':payload,'kind':kind,'logicalKey':assignment['key']}

def verify_instance(project, model, entry):
 """Adapt the reviewed batch/L checks across ALL historical profile shapes."""
 is_rack=model['kind']=='rackContainer';objects=project['racks'] if is_rack else project['devices']
 device=next(d for d in objects if d['id']==entry['resourceId']);props=device['properties']
 assert device['hardwareProfileKey']==model['key'] and props['hardwareProfileVersion']==model['revision']
 assert props['physicalDimensionsMm']==model['dimensionsMm'] and props['color']==model['color']
 if model['identity']['manufacturer']:assert props['hardwareIdentity']==model['identity']
 else:assert 'hardwareIdentity' not in props
 for field,target in [('mounting','hardwareMounting'),('configuration','hardwareConfiguration'),('continuities','hardwareContinuities')]:
  if field in model:assert props.get(target)==model[field]
 if is_rack:assert device['sizeU']==model['mounting']['capacityU'] and device['roomId']==entry['room']
 else:
  assert device['mountParentId']==entry['supportId'] and device['mountSlotKey']==entry['slot']
  if model['kind'] in {'wall','pole','floor','din'}:assert device['roomId']==entry['room'] and device['rackId'] is None and device['sizeU'] is None
  else:assert device['rackId']==entry['rack'] and device['roomId'] is None and device['sizeU']==model['rackUnits']
 groups=[g for g in project['portGroups'] if g['deviceId']==entry['deviceId']];ports=[p for p in project['ports'] if p['deviceId']==entry['deviceId']]
 assert len(groups)==len(model['groups']) and len(ports)==sum(g['count'] for g in model['groups'])
 for order,g in enumerate(model['groups']):
  group=next(v for v in groups if v['sortOrder']==order);actual=sorted((p for p in ports if p['groupId']==group['id']),key=lambda p:p['gn'])
  assert (group['type'],group['name'],group['prefix'])==(g['type'],g['name'].strip(),g['prefix'].strip())
  assert [p['gn'] for p in actual]==list(range(1,g['count']+1))
  for p in actual:
   assert p['type']==g['type'] and p['face']==g['face'] and p['powerRole']==g.get('powerRole','unspecified')
   assert p['properties']['hardwareGroupKey']==g['key'] and p['properties']['hardwarePortKey']==g['key']+':'+str(p['gn'])
   for field,target in [('physicalConnector','hardwarePhysicalConnector'),('physicalFace','hardwarePhysicalFace'),('interfaceRole','hardwareInterfaceRole'),('signalRole','hardwareSignalRole'),('powerSystem','hardwarePowerSystem')]:assert p['properties'].get(target)==g.get(field)
 return device,groups,ports

def connector(port):
 props=port.get('properties',{});return props.get('hardwarePhysicalConnector') or port['type']

def power_system(port):
 p=port.get('properties',{});return p.get('hardwarePowerSystem') or p.get('declaredPowerSystem') or ('dc' if port['type']=='power_dc' else None)

COUNTERPART={'iec-c14':'iec-c13','iec-c13':'iec-c14','iec-c20':'iec-c19','iec-c19':'iec-c20',
 'nema-5-15p':'nema-5-15r','nema-5-15r':'nema-5-15p','nema-5-20p':'nema-5-20r','nema-5-20r':'nema-5-20p',
 'nema-l5-30p':'nema-l5-30r','nema-l5-30r':'nema-l5-30p','nema-l6-30p':'nema-l6-30r','nema-l6-30r':'nema-l6-30p',
 'nema-l6-20p':'nema-l6-20r','nema-l6-20r':'nema-l6-20p',
 'iec60309-16a-2p-e-plug':'iec60309-16a-2p-e-connector','iec60309-16a-2p-e-connector':'iec60309-16a-2p-e-plug',
 'iec60309-32a-2p-e-plug':'iec60309-32a-2p-e-connector','iec60309-32a-2p-e-connector':'iec60309-32a-2p-e-plug'}

def counterpart_spec(port):
 physical=connector(port);signal=port.get('properties',{}).get('hardwareSignalRole')
 return {'type':port['type'],'physicalConnector':COUNTERPART.get(physical,physical),
  'signalRole':{'tx':'rx','rx':'tx'}.get(signal,'bidi'),'powerSystem':power_system(port),
  'powerRole':{'inlet':'outlet','outlet':'inlet'}.get(port.get('powerRole'),'unspecified')}

def compatible(a,b):
 if a['deviceId']==b['deviceId'] or a['id']==b['id']:return False
 # RJ45 PoE is a flag on the copper family, not a different physical plug.
 family=lambda p:'rj45' if p['type']=='rj45_poe' else p['type']
 if family(a)!=family(b):return False
 target=counterpart_spec(a)
 if a['type'] in {'power','power_dc'}:
  if b['powerRole']!=target['powerRole'] or power_system(b)!=target['powerSystem']:return False
 signal_a=a.get('properties',{}).get('hardwareSignalRole');signal_b=b.get('properties',{}).get('hardwareSignalRole')
 if signal_a in {'tx','rx'} or signal_b in {'tx','rx'}:
  if (signal_a,signal_b) not in {('tx','rx'),('rx','tx')}:return False
 return connector(b)==target['physicalConnector'] or (family(a)=='rj45' and connector(a) in {'rj45','rj45_poe'} and connector(b) in {'rj45','rj45_poe'})

def connect_inventory(session, project, room):
 ports=project['ports'];by_group=defaultdict(list);used={v for c in project['connections'] for v in (c['fromPortId'],c['toPortId'])}
 for p in ports:by_group[p['groupId']].append(p)
 targets=[]
 for values in by_group.values():
  values.sort(key=lambda p:p['gn'])
  targets.extend(values if values[0]['type'] in {'power','power_dc'} else ([] if any(p['id'] in used for p in values) else values[:1]))
 pairs=[];missing=defaultdict(list)
 for a in targets:
  if a['id'] in used:continue
  peer=next((b for b in targets if b['id'] not in used and compatible(a,b)),None)
  if peer is None:peer=next((b for b in ports if b['id'] not in used and compatible(a,b)),None)
  if peer:
   used.update([a['id'],peer['id']]);pairs.append({'fromPortId':a['id'],'toPortId':peer['id'],'note':'Demo50 · enlace documentado de laboratorio'})
  else:missing[canonical(counterpart_spec(a))].append(a)
 fixtures=[]
 for number,(signature,values) in enumerate(sorted(missing.items())):
  spec=json.loads(signature)
  for offset in range(0,len(values),96):
   sources=values[offset:offset+96];group={'type':spec['type'],'count':len(sources),'name':'Extremos sintéticos de ensayo','prefix':'TEST '}
   if spec['type']=='power_dc':group['powerSystem']=spec['powerSystem']
   created=session.send({'kind':'endDevice','roomId':room,'name':f'Verificador QA {number+1}-{offset//96+1} · {spec["type"]}',
    'properties':{'notes':'Fixture sintético de conexión, no producto comercial; no certifica voltaje ni protocolo.','demo50Peer':spec},'portGroups':[group]},
    kind='device.create',symbol=f'peer/{number}/{offset}').json()['result']
   ids=created['createdIds'];assert len(ids)==len(sources)+2
   if spec['type'] in {'power','power_dc'}:
    for start in range(0,len(sources),64):session.send({'deviceId':created['resourceId'],'groupId':ids[1],
     'groupType':spec['type'],'portIds':ids[2+start:2+start+64],'changes':{'powerRole':spec['powerRole']}},kind='ports.update',symbol=f'peer-role/{number}/{offset}/{start}')
   for source,target in zip(sources,ids[2:]):
    used.update([source['id'],target]);pairs.append({'fromPortId':source['id'],'toPortId':target,'note':'Demo50 · extremo de ensayo '+spec['physicalConnector']})
   fixtures.append({'deviceId':created['resourceId'],'spec':spec,'ports':ids[2:]})
 # Body cap is 16KiB.32 pairs remain bounded even with full UUIDs/notes.
 for start in range(0,len(pairs),32):session.send({'pairs':pairs[start:start+32]},kind='connections.createBatch',symbol=f'cables/{start}')
 return {'pairs':len(pairs),'fixtures':fixtures,'targetPorts':len(targets)}

def load_customer(server, admin, customer, cid, definitions, seed):
 session=Session(clone_client(server,admin),cid,seed,customer['key']);refs={};models={(d['key'],d['revision']):d for d in definitions}
 for site in customer['sites']:
  refs[site['key']]=session.send({'name':site['name'],'properties':{'notes':'Ubicación ficticia Demo50'}},kind='site.create',symbol=site['key']).json()['result']['resourceId']
  for building in site['buildings']:
   refs[building['key']]=session.send({'name':building['name'],'siteId':refs[site['key']]},kind='building.create',symbol=building['key']).json()['result']['resourceId']
   for room in building['rooms']:refs[room['key']]=session.send({'name':room['name'],'buildingId':refs[building['key']]},kind='room.create',symbol=room['key']).json()['result']['resourceId']
 for rack in customer['racks']:
  refs[rack['key']]=session.send({k:rack[k] for k in ('name','sizeU','properties')}|{'roomId':refs[rack['roomKey']]},kind='rack.create',symbol=rack['key']).json()['result']['resourceId']
 entries=[add_profile(session,models[(a['profileKey'],a['profileVersion'])],a,refs) for a in customer['assignments']]
 business=[]
 for a in customer.get('businessDevices',[]):
  entry=add_profile(session,models[(a['profileKey'],a['profileVersion'])],a,refs);business.append(entry);refs[a['key']]=entry['resourceId']
 for obj in customer['roomObjects']:
  payload={k:v for k,v in obj.items() if k not in {'key','roomKey','note'}};payload['roomId']=refs[obj['roomKey']];payload['properties']={'notes':obj['note']}
  refs[obj['key']]=session.send(payload,kind='device.create',symbol=obj['key']).json()['result']['resourceId']
 project=session.project()
 for entry in entries+business:verify_instance(project,models[(entry['profileKey'],entry['profileVersion'])],entry)
 # Exercise actual capacity of the four materialized enclosures, without inventing their own connectors.
 for entry in entries:
  if entry['kind']=='rack.createHardware':session.send({'profileKey':'switch-24','profileVersion':'hw-reference-v1','rackId':entry['resourceId'],'name':'Equipo sintético dentro del armario'},symbol=entry['logicalKey']+'/occupant')
 project=session.project();links=[]
 for link in customer.get('interBuildingLinks',[]):
  def uplink(key,ordinal):return next(p for p in project['ports'] if p['deviceId']==refs[key] and p['type']=='sfp' and p['gn']==ordinal)
  a,b=uplink(link['fromDeviceKey'],2),uplink(link['toDeviceKey'],1)
  links.append({'fromPortId':a['id'],'toPortId':b['id'],'note':link['note']})
 if links:session.send({'pairs':links},kind='connections.createBatch',symbol='inter-building-links')
 wiring=connect_inventory(session,session.project(),refs[customer['catalogueRoomKey']])
 # Leave explicit, uncabled examples of all blocked/reserved states; never alter fixed physical metadata.
 project=session.project();occupied={v for c in project['connections'] for v in (c['fromPortId'],c['toPortId'])}
 unused=[p for p in project['ports'] if p['id'] not in occupied and p['type'] not in {'power','power_dc'}]
 for status,p in zip(('reserved','faulty','disabled'),unused):
  group=next(g for g in project['portGroups'] if g['id']==p['groupId'])
  session.send({'deviceId':p['deviceId'],'groupId':p['groupId'],'groupType':group['type'],'portIds':[p['id']],'changes':{'status':status}},kind='ports.update',symbol='state/'+status)
 return {'key':customer['key'],'customerId':cid,'refs':refs,'entries':entries,'businessEntries':business,'wiring':wiring,'receipts':session.receipts,'terminalId':refs[customer['roomObjects'][-1]['key']]}

def inventory_fingerprint(lab, db, tables=INVENTORY_TABLES):
 return {t:lab.sql(db,f"SELECT encode(sha256(convert_to(COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb)::text,'UTF8')),'hex') FROM {t} t") for t in tables}

def setup_users(admin, customers, seed):
 accounts=[]
 configs=[('demo.reader',None,['systemhaus.read','inventory.read'],None),('demo.technician','c01',['systemhaus.read','inventory.read','inventory.edit'],None),
  ('demo.client-admin','c01',['systemhaus.read','customer.manage','inventory.read','inventory.edit','inventory.delete','reports.export'],None),('demo.no-access',None,[],None)]
 configs += [(f'demo.load{i:02}',scope,['systemhaus.read','inventory.read','inventory.edit'],None) for i,scope in enumerate(BENCHMARK_CUSTOMERS,1)]
 for name,scope,capabilities,_ in configs:
  password=secrets.token_urlsafe(32);resource=house_mutation(admin,'/api/v1/admin/users',{'username':name,'password':password},seed,'user/'+name,201)['resource']
  if capabilities:
   gid=house_mutation(admin,'/api/v1/admin/user-groups',{'name':'Demo50 '+name},seed,'group/'+name,201)['resource']['id']
   house_mutation(admin,f'/api/v1/admin/user-groups/{gid}/members',{'userId':resource['id'],'assigned':True},seed,'member/'+name)
   for capability in capabilities:
    target=customers[scope] if scope and capability!='systemhaus.read' else None
    house_mutation(admin,f'/api/v1/admin/user-groups/{gid}/grants',{'grantId':str(uuid.uuid5(NS,seed+'/grant/'+name+'/'+capability)),
     'capability':capability,'scope':'customer' if target else 'systemhaus','targetId':target,'assigned':True},seed,'grant/'+name+'/'+capability)
  accounts.append({'username':name,'password':password,'userId':resource['id'],'scope':scope,'capabilities':capabilities})
 return accounts

def counts(lab,db):return {t:int(lab.sql(db,f'SELECT count(*) FROM {t}')) for t in INVENTORY_TABLES}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--application',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--browser',action='store_true');args=parser.parse_args()
 output=args.output.resolve();private=(ROOT/'.local').resolve()
 if not output.is_relative_to(private) or output.exists():raise Rejected('new_private_output_required')
 application=json.loads(args.application.read_text());dll=Path(application['dll']).resolve(strict=True);frontend=Path(application['frontend']).resolve(strict=True)
 if sha(dll)!=SERVER_SHA or sha(frontend/'app.js')!=FRONTEND_SHA:raise Rejected('reviewed_application_digest_required')
 definitions=load_definitions(ROOT);plan=build_plan(definitions);validate_plan(plan,definitions)
 output.mkdir(parents=True,exist_ok=False);protect_directory(output);(output/'plan.json').write_bytes(plan_bytes(plan))
 lab=DemoLab('demo50');report={'result':'FAIL','stage':'initialization','vmChanged':False,'qaChanged':False,'serverSha256':SERVER_SHA,'frontendSha256':FRONTEND_SHA,'schema':43};start=time.monotonic()
 try:
  with lab:
   db=lab.create_database('demo50');password=secrets.token_urlsafe(32);name='demo.global'
   boot=lab.bootstrap(db,name,password,dll=dll)
   (output/'bootstrap-private.log').write_text(boot.stdout+'\n'+boot.stderr,encoding='utf-8')
   if boot.returncode:raise Rejected('new_lab_bootstrap_failed')
   assert lab.sql(db,'SELECT count(*) FROM customer')=='0'
   assert lab.sql(db,'SELECT max(version) FROM schema_migration')=='43'
   actual=json.loads(lab.sql(db,"SELECT jsonb_agg(jsonb_build_object('key',profile_key,'revision',revision,'sha',definition_sha256) ORDER BY profile_key,revision) FROM hardware_definition"))
   expected=[{'key':d['key'],'revision':d['revision'],'sha':definition_digest(d)} for d in definitions]
   assert actual==expected
   lab.grant_runtime(db);server=lab.start_server(db,dll=dll,frontend=frontend);admin,_=login(server,name,password)
   customer_ids={}
   for c in plan['customers']:customer_ids[c['key']]=house_mutation(admin,'/api/v1/customers',{'name':c['name']},plan['seed'],'customer/'+c['key'],201)['resource']['id']
   accounts=setup_users(admin,customer_ids,plan['seed']);dump(output/'access-private.json',{'url':server.origin,'username':name,'password':password,'accounts':accounts,'database':db.name,'clusterDirectory':str(lab.directory)})
   report['stage']='inventory_commands';print(json.dumps({'stage':'loading_50_customers','profiles':len(definitions)}),flush=True)
   with ThreadPoolExecutor(max_workers=5) as pool:
    loaded=list(pool.map(lambda c:load_customer(server,admin,c,customer_ids[c['key']],definitions,plan['seed']),plan['customers']))
   dump(output/'loaded-private.json',loaded);report.update(customers=50,primaryProfiles=868,counts=counts(lab,db),loadSeconds=round(time.monotonic()-start,3));print(json.dumps({'stage':'inventory_loaded','counts':report['counts']}),flush=True)
   # Further validation, export, load and recovery are kept separate from population.
   sys.modules.setdefault('prepare_demo50',sys.modules[__name__])
   from demo50_validation import validate_demo50
   validation=validate_demo50(lab,db,server,admin,accounts,loaded,plan,definitions,output,dll,frontend,args.browser)
   report.update(validation);report['result']='PASS';report['stage']='verified'
 except BaseException as error:
  (output/'failure-private.log').write_text(traceback.format_exc(),encoding='utf-8');report.update(failureType=type(error).__name__,failureCode=str(error) if isinstance(error,Rejected) else 'validation_failed')
 finally:
  report.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),elapsedSeconds=round(time.monotonic()-start,3))
  dump(output/'RESULTADOS.json',report);print(json.dumps(report),flush=True)
 return 0 if report['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
