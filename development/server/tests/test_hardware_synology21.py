"""Isolated Windows PG17/Edge: RS1221+ rack2U, no existing installation touched."""
import argparse,hashlib,json,uuid,subprocess
from pathlib import Path
from pg_support import Lab,Client,NO_WINDOW,protect_directory,toolchain
from test_hardware_mounting_gui import fixture
from test_hardware_catalog17 import Session,state,migrate,runtime_sql,CATALOG
ROOT=Path(__file__).resolve().parents[3]
KEY='synology-rs1221plus';VERSION='synology-20261030-v1'

def ordered(project):
 for key in ['sites','buildings','rooms','racks','devices','portGroups','ports','connections']:project[key].sort(key=lambda x:x['id'])
 return project

def main():
 p=argparse.ArgumentParser()
 for n in ['dll','baseline-dll','frontend','output']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.dll=a.dll.resolve(strict=True);a.baseline_dll=a.baseline_dll.resolve(strict=True);a.frontend=a.frontend.resolve(strict=True);out=a.output.resolve();assert out.is_relative_to((ROOT/'.local').resolve());out.mkdir(exist_ok=False);protect_directory(out)
 result={'result':'FAIL','checks':[],'serverSha256':hashlib.sha256(a.dll.read_bytes()).hexdigest(),'appSha256':hashlib.sha256((a.frontend/'app.js').read_bytes()).hexdigest(),'qaAccessed':False,'vmAccessed':False};lab=Lab('synology21')
 try:
  with lab:
   old=lab.create_database('upgrade20');ids,password=fixture(lab,old,a.baseline_dll);lab.grant_runtime(old);s=lab.start_server(old,dll=a.baseline_dll);session=Session(s,ids,password)
   for key,version in [('startech-c6panelutp241uft','startech-20261030-v1'),('aruba-jl682a','aruba-20261030-v1'),('shelf-2u','hw-reference-v1')]:session.command(dict(profileKey=key,profileVersion=version,rackId=ids['rack'],name='Previo '+key))
   support=next(d['id'] for d in session.project()['devices'] if d['name']=='Previo shelf-2u')
   session.command(dict(profileKey='fortinet-fg60f',profileVersion='fortinet-20261030-v1',rackId=ids['rack'],name='Previo FG',mountParentId=support,mountSlotKey='main'))
   expected=session.project();before=state(lab,old,catalog=False);defs=lab.sql(old,'SELECT jsonb_agg(to_jsonb(t) ORDER BY profile_key) FROM hardware_definition t');history=lab.sql(old,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t');s.close()
   assert migrate(lab,old,a.dll,out/'migrate-private.txt')==0;assert lab.sql(old,'SELECT max(version) FROM schema_migration')=='21';assert state(lab,old,catalog=False)==before
   assert lab.sql(old,"SELECT jsonb_agg(to_jsonb(t) ORDER BY profile_key) FROM hardware_definition t WHERE profile_key<>'synology-rs1221plus'")==defs
   assert lab.sql(old,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t WHERE version<=20')==history
   lab.grant_runtime(old);s=lab.start_server(old,dll=a.dll);assert Session(s,ids,password).project()==expected;s.close();result['checks'].append('20->21 preserves StarTech48/Aruba29/Fortinet10 UUIDs and mounting, seven definitions, inventory/operations/audit and migration history1..20')
   db=lab.create_database('fresh21');ids,password=fixture(lab,db,a.dll);lab.grant_runtime(db);assert lab.sql(db,'SELECT max(version) FROM schema_migration')=='21';assert lab.sql(db,'SELECT count(*) FROM hardware_definition')=='8'
   house=lab.sql(db,'SELECT id FROM systemhaus');ids.update(pdu=str(uuid.uuid4()),pduGroup=str(uuid.uuid4()),pduPort=str(uuid.uuid4()))
   lab.sql(db,f"UPDATE inventory_rack SET size_u=6,name='Rack NAS 6U' WHERE id='{ids['rack']}'; INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order) VALUES('{ids['pdu']}','{house}','{ids['customer']}','rackEquipment','{ids['rack']}','PDU sintética',1,0); INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order) VALUES('{ids['pduGroup']}','{house}','{ids['customer']}','{ids['pdu']}','power','Outlet','AC ',0); INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,face,power_role) VALUES('{ids['pduPort']}','{house}','{ids['customer']}','{ids['pdu']}','{ids['pduGroup']}','power',1,0,'rear','outlet')")
   server=lab.start_server(db,dll=a.dll,frontend=a.frontend);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='hardware-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(out),RACKCLICK_FIXTURE=json.dumps(ids))
   with (out/'browser-private.log').open('wb') as log:done=subprocess.run([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-hardware-synology.mjs')],cwd=ROOT/'development/frontend',env=env,stdout=log,stderr=log,timeout=300,creationflags=NO_WINDOW)
   if done.returncode:raise RuntimeError('Browser failed; private log retained')
   expected=json.loads((out/'expected-project.json').read_text('utf-8'));assert len(expected['ports'])==42 and len(expected['connections'])==3
   assert lab.sql(db,f"SELECT sum(size_u) FROM inventory_device WHERE rack_id='{ids['rack']}'")=='6'
   session=Session(server,ids,password);prior=state(lab,db);base=dict(profileKey=KEY,profileVersion=VERSION,rackId=ids['rack'],name='Rejected NAS')
   assert session.command(base,409).status==409;assert state(lab,db)==prior
   for change in [dict(mountParentId=ids['legacy']),dict(mountSlotKey='main'),dict(mountParentId=ids['legacy'],mountSlotKey='main')]:
    assert session.command(base|change,422).json()['error']=='mount_profile_incompatible';assert state(lab,db)==prior
   for version in [None,'latest','hw-reference-v1','synology-20261030-v2']:
    payload=base.copy();payload.pop('profileVersion')
    if version is not None:payload['profileVersion']=version
    assert session.command(payload,422).json()['error']=='hardware_revision_unknown';assert state(lab,db)==prior
   replay_key=str(uuid.uuid4());revision=session.project()['revision'];payload=base|dict(rackId=ids['mixedRack'],name='Idempotent NAS')
   created=session.command(payload,key=replay_key,revision=revision).json();created_state=state(lab,db)
   assert session.command(payload,key=replay_key,revision=revision).json()==created and state(lab,db)==created_state
   expected=ordered(session.project());assert len(expected['ports'])==47 and len(expected['connections'])==3;prior=state(lab,db)
   lab.sql(db,"CREATE FUNCTION nas_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic audit failure'; END $$; CREATE TRIGGER nas_fail_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION nas_fail_audit()")
   payload=base|dict(rackId=ids['mixedRack'],name='Rollback NAS')
   response=session.client.request('POST',session.route+'/commands',{'type':'device.createHardware','payload':payload},{'X-RackClick-Actor':session.actor,'If-Match':f'"{expected["revision"]}"','Idempotency-Key':str(uuid.uuid4())})
   assert response.status>=500 and state(lab,db)==prior
   lab.sql(db,'DROP TRIGGER nas_fail_audit ON audit_event; DROP FUNCTION nas_fail_audit()')
   result['checks'].append('Rack capacity rejects extra2U root; supplied shelf/slot and unknown revisions reject without mutation; replay exact five UUIDs; audit failure rolls back root/groups/ports/roles/revision')
   for table in CATALOG:
    assert runtime_sql(lab,db,f"SELECT has_table_privilege(current_user,'{table}','SELECT'),has_table_privilege(current_user,'{table}','INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')").stdout.strip()=='t|f'
    assert runtime_sql(lab,db,f'DELETE FROM {table}').returncode!=0
   assert runtime_sql(lab,db,'CREATE TABLE cannot_create(id integer)').returncode!=0;assert state(lab,db)==prior
   reader=Client(server);assert reader.login('hardware-reader',password).status==200;actor=reader.request('GET','/api/v1/me').json()['user']['id']
   response=reader.request('POST',f"/api/v1/customers/{ids['customer']}/commands",{'type':'device.createHardware','payload':base},{'X-RackClick-Actor':actor,'If-Match':f'"{expected["revision"]}"','Idempotency-Key':str(uuid.uuid4())});assert response.status==403 and state(lab,db)==prior
   server.close();server=lab.start_server(db,dll=a.dll,frontend=a.frontend);client=Client(server);assert client.login('hardware-second',password).status==200;actual=ordered(client.request('GET',f"/api/v1/customers/{ids['customer']}/project").json());assert actual==expected
   result.update(result='PASS',schema=21,postgresql=lab.sql('postgres','SHOW server_version'),ports=47,guiBaselinePorts=42,connections=3,ethernetConnections=2,powerConnections=1,restartPersistence=True,readerDeniedWithoutMutation=True)
   result['checks'].append('Bootstrap1->21 and native Edge8trays/2fans/5rearUUIDs, twoEthernet+ACinlet->outlet, keyboard/mobile/labels/reload/second session/reader persist after server restart')
 finally:
  result.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers));(out/'RESULTADOS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
 return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
