"""Schema44 ->45 and room repeaters on a new PG17 laboratory, never VM/QA.

The synthetic AC/DC source tests roles and persistence, not electrical fitness.
Raw logs and connection fixtures stay in a fresh ignored .local directory.
"""
import argparse,hashlib,json,traceback,uuid
from pathlib import Path
from pg_support import Client,literal,protect_directory
from test_hardware_german_cpe import TrialLab,catalogue
from test_hardware_mounting_gui import fixture
from test_hardware_catalog17 import migrate,runtime_sql
from test_hardware_batch100c import BatchSession,ordered
from test_hardware_selected506l import placement_fixture,checkpoint
ROOT=Path(__file__).resolve().parents[3]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def models():return sorted([r['definition'] for name in ('fritz','telekom','devolo','tplink') for r in json.loads((ROOT/f'development/hardware/german-repeaters/{name}.json').read_bytes())['models']],key=lambda d:d['key'])
def upgrade(lab,old,dll,out):
 db=lab.create_database('repeaters-upgrade44');ids,pw=fixture(lab,db,old)
 before=catalogue(lab,db);assert len(before['hardware_definition'])==874
 history=lab.sql(db,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t')
 inventory=lab.sql(db,'SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM inventory_device t')
 assert migrate(lab,db,dll,out/'upgrade44-private.log')==0
 after=catalogue(lab,db);assert len(after['hardware_definition'])==884
 pairs={(r['profile_key'],r['revision']) for r in before['hardware_definition']}
 for table,rows in before.items():assert [r for r in after[table] if (r['profile_key'],r['revision']) in pairs]==rows,table
 assert lab.sql(db,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t WHERE version<=44')==history
 assert lab.sql(db,'SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM inventory_device t')==inventory
 assert migrate(lab,db,dll,out/'repeat45-private.log')==0;assert catalogue(lab,db)==after
 return dict(upgrade44to45=True,prior874DefinitionsUnchanged=True,history44Unchanged=True,inventoryUnchanged=True,repeatMigrationIdempotent=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--dll',type=Path,required=True);p.add_argument('--baseline-dll',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 dll=a.dll.resolve(strict=True);old=a.baseline_dll.resolve(strict=True);out=a.output.absolute();assert out.is_relative_to((ROOT/'.local').absolute()) and not out.exists();out.mkdir(parents=True);protect_directory(out)
 result=dict(result='FAIL',vmAccessed=False,qaAccessed=False,serverSha256=sha(dll),baselineSha256=sha(old));lab=TrialLab('german-repeaters45');stage='upgrade'
 try:
  definitions=models();assert len(definitions)==10
  with lab:
   result.update(upgrade(lab,old,dll,out));stage='fresh'
   db=lab.create_database('repeaters-fresh45');ids,pw=fixture(lab,db,dll);placement_fixture(lab,db,ids)
   assert lab.sql(db,'SELECT max(version) FROM schema_migration')=='45';assert lab.sql(db,'SELECT count(*) FROM hardware_definition')=='884'
   lab.grant_runtime(db);server=lab.start_server(db,dll=dll);s=BatchSession(server,ids,pw);stage='create'
   entries=[]
   for d in definitions:
    pair=[]
    for prefix,room in (('Repeater ',ids['room']),('Peer ',ids['secondRoom'])):
     request=dict(profileKey=d['key'],profileVersion=d['revision'],roomId=room,name=prefix+d['identity']['model']);key=str(uuid.uuid4());revision=s.revision;response=s.send(request,key=key).json()
     pair.append(dict(deviceId=response['result']['resourceId'],request=request,requestId=key,expectedRevision=revision,response=response))
    entries.append((d,*pair))
   project=s.project();checks=[]
   allids=[r['id'] for k in ('devices','portGroups','ports') for r in project[k]];assert len(allids)==len(set(allids))
   for d,own,peer in entries:
    for entry in (own,peer):
     dev=next(v for v in project['devices'] if v['id']==entry['deviceId']);assert (dev['kind'],dev['rackId'],dev['roomId'],dev['sizeU'],dev['mountParentId'],dev['mountSlotKey'])==('endDevice',None,entry['request']['roomId'],None,None,None)
     assert dev['properties']['hardwareIdentity']==d['identity'];assert dev['properties']['hardwareMounting']==d['mounting']
     ports=[v for v in project['ports'] if v['deviceId']==entry['deviceId']];assert len(ports)==sum(g['count'] for g in d['groups'])
     for g in d['groups']:
      actual=sorted([v for v in ports if v['properties'].get('hardwareGroupKey')==g['key']],key=lambda v:v['gn']);assert len(actual)==g['count']
      for ordinal,v in enumerate(actual,1):
       assert (v['type'],v['gn'],v['face'],v['powerRole'])==(g['type'],ordinal,g['face'],g['powerRole'])
       for prop,source in [('hardwarePhysicalConnector','physicalConnector'),('hardwarePowerSystem','powerSystem'),('hardwareInterfaceRole','interfaceRole')]:assert v['properties'].get(prop)==g.get(source)
    checks.append(dict(key=d['key'],portCount=sum(g['count'] for g in d['groups']),twoRoomInstances=True,noRackUnitsOrParent=True,uuidGroupsFacesRolesMetadata=True))
   # Rejections must not commit commands, audit, inventory or revision changes.
   stage='negative'
   def reject(request,kind,status):
    before=checkpoint(lab,db);s.send(request,kind=kind,status=status);assert checkpoint(lab,db)==before
   for d,own,peer in entries:reject(own['request']|dict(rackId=ids['rack']),'device.createHardware',422)
   reject(entries[0][1]['request']|dict(roomId=ids['foreignRoom']),'device.createHardware',404)
   reject(entries[0][1]['request']|dict(profileVersion='latest'),'device.createHardware',422)
   # Generic synthetic outlet, created by ordinary API. No real PSU/SKU or
   # voltage/connector compatibility is asserted by this role-only fixture.
   stage='connections'
   source=s.send(dict(kind='endDevice',roomId=ids['room'],name='Synthetic AC/DC role fixture',portGroups=[dict(type='power',count=6,name='AC role outputs',prefix='AC '),dict(type='power_dc',count=4,name='DC role outputs',prefix='DC ',powerSystem='dc')]),kind='device.create').json()['result']['resourceId']
   project=s.project();source_ports=[v for v in project['ports'] if v['deviceId']==source]
   for typ in ('power','power_dc'):
    ports=[v for v in source_ports if v['type']==typ];s.send(dict(deviceId=source,groupId=ports[0]['groupId'],groupType=typ,portIds=[v['id'] for v in ports],changes=dict(powerRole='outlet')),kind='ports.update')
   project=s.project();outlets={typ:iter([v for v in project['ports'] if v['deviceId']==source and v['type']==typ]) for typ in ('power','power_dc')};cables=[]
   for d,own,peer in entries:
    aports=[v for v in project['ports'] if v['deviceId']==own['deviceId']];bports=[v for v in project['ports'] if v['deviceId']==peer['deviceId']]
    inlet=next(v for v in aports if v['type'] in ('power','power_dc'));other=next(v for v in bports if v['type']==inlet['type'])
    reject(dict(fromPortId=inlet['id'],toPortId=other['id']),'connections.create',409)
    eth=next((v for v in aports if v['type']=='rj45'),None)
    if eth:
     reject(dict(fromPortId=eth['id'],toPortId=inlet['id']),'connections.create',409)
     ep=next(v for v in bports if v['type']=='rj45');cables.append(s.send(dict(fromPortId=eth['id'],toPortId=ep['id']),kind='connections.create').json()['result']['resourceId'])
    outlet=next(outlets[inlet['type']]);cables.append(s.send(dict(fromPortId=outlet['id'],toPortId=inlet['id']),kind='connections.create').json()['result']['resourceId'])
   assert len(cables)==19
   before=ordered(s.project());stage='permissions'
   reader=Client(server);assert reader.login('hardware-reader',pw).status==200;actor=reader.request('GET','/api/v1/me').json()['user']['id'];prior=checkpoint(lab,db)
   response=reader.request('POST',s.route+'/commands',dict(type='device.createHardware',payload=entries[0][1]['request']),{'X-RackClick-Actor':actor,'If-Match':f'"{s.revision}"','Idempotency-Key':str(uuid.uuid4())});assert response.status==403;assert checkpoint(lab,db)==prior
   assert ordered(reader.request('GET',s.route+'/project').json())==before
   replay=entries[0][1];assert s.send(replay['request'],key=replay['requestId'],revision=replay['expectedRevision']).json()==replay['response'];assert ordered(s.project())==before
   second=Client(server);assert second.login('hardware-second',pw).status==200;assert ordered(second.request('GET',s.route+'/project').json())==before
   assert runtime_sql(lab,db,'CREATE TABLE forbidden_repeaters45(id integer)').returncode!=0
   assert runtime_sql(lab,db,'DELETE FROM hardware_definition').returncode!=0
   assert checkpoint(lab,db)==prior
   stage='restart';server.close();server=lab.start_server(db,dll=dll);again=Client(server);assert again.login('hardware-second',pw).status==200;assert ordered(again.request('GET',s.route+'/project').json())==before
   result.update(result='PASS',schema=45,postgresql=lab.sql('postgres','SHOW server_version'),modelsCreated=10,peerInstances=10,modelPorts=23,modelResults=checks,connections=19,ethernetConnections=9,powerRoleConnections=10,syntheticPowerFixtureNotElectricalCertification=True,reader403=True,foreignRoom404=True,wrongPlacement422NoMutation=True,reloadSecondSessionAndRestart=True,replayIdempotent=True,wrongMediaAndSamePowerRole409NoMutation=True,runtimeActualDDLAndCatalogueDMLDenied=True,mfaExplicitlyDisabledOnlyInLab=True)
 except BaseException as e:result.update(failureStage=stage,failureType=type(e).__name__);(out/'private-error.log').write_text(traceback.format_exc(),encoding='utf-8')
 finally:
  result.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers));(out/'RESULTADOS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:result[k] for k in ('result','schema','modelsCreated','modelPorts','failureStage','failureType','labStopped','serversStopped') if k in result}))
 return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
