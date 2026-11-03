"""Real PG17 upgrade18→19/bootstrap19 plus native Edge model19, isolated only."""
import argparse,hashlib,json,uuid,subprocess
from pathlib import Path
from pg_support import Lab,Client,NO_WINDOW,protect_directory,toolchain
from test_hardware_mounting_gui import fixture
from test_hardware_catalog17 import Session,state,migrate,runtime_sql,CATALOG
ROOT=Path(__file__).resolve().parents[3]
def main():
 p=argparse.ArgumentParser()
 for n in ['dll','baseline-dll','frontend','output']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();out=a.output.resolve();assert out.is_relative_to((ROOT/'.local').resolve());out.mkdir(exist_ok=False);protect_directory(out)
 result={'result':'FAIL','checks':[],'serverSha256':hashlib.sha256(a.dll.read_bytes()).hexdigest(),'appSha256':hashlib.sha256((a.frontend/'app.js').read_bytes()).hexdigest(),'qaAccessed':False,'vmAccessed':False};lab=Lab('aruba19')
 try:
  with lab:
   old=lab.create_database('upgrade18');ids,password=fixture(lab,old,a.baseline_dll);lab.grant_runtime(old);s=lab.start_server(old,dll=a.baseline_dll);session=Session(s,ids,password)
   session.command(dict(profileKey='startech-c6panelutp241uft',profileVersion='startech-20261030-v1',rackId=ids['rack'],name='Panel previo'))
   expected=session.project();before=state(lab,old,catalog=False);defs=lab.sql(old,'SELECT jsonb_agg(to_jsonb(t) ORDER BY profile_key) FROM hardware_definition t');history=lab.sql(old,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t');s.close()
   assert migrate(lab,old,a.dll,out/'migrate-private.txt')==0;assert lab.sql(old,'SELECT max(version) FROM schema_migration')=='19';assert state(lab,old,catalog=False)==before
   assert lab.sql(old,"SELECT jsonb_agg(to_jsonb(t) ORDER BY profile_key) FROM hardware_definition t WHERE profile_key<>'aruba-jl682a'")==defs
   assert lab.sql(old,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t WHERE version<=18')==history
   lab.grant_runtime(old);s=lab.start_server(old,dll=a.dll);assert Session(s,ids,password).project()==expected;s.close();result['checks'].append('18→19 preserves StarTech instance48UUIDs, inventory/operations/audit, five definitions and digests1–18')
   db=lab.create_database('fresh19');ids,password=fixture(lab,db,a.dll);lab.grant_runtime(db);assert lab.sql(db,'SELECT max(version) FROM schema_migration')=='19';assert lab.sql(db,'SELECT count(*) FROM hardware_definition')=='6'
   house=lab.sql(db,'SELECT id FROM systemhaus');ids.update(pdu=str(uuid.uuid4()),pduGroup=str(uuid.uuid4()),pduPort=str(uuid.uuid4()))
   lab.sql(db,f"INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order) VALUES('{ids['pdu']}','{house}','{ids['customer']}','rackEquipment','{ids['rack']}','PDU sintética',1,0); INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order) VALUES('{ids['pduGroup']}','{house}','{ids['customer']}','{ids['pdu']}','power','Outlet','AC ',0); INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,face,power_role) VALUES('{ids['pduPort']}','{house}','{ids['customer']}','{ids['pdu']}','{ids['pduGroup']}','power',1,0,'rear','outlet')")
   server=lab.start_server(db,dll=a.dll,frontend=a.frontend);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='hardware-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(out),RACKCLICK_FIXTURE=json.dumps(ids))
   with (out/'browser-private.log').open('wb') as log:done=subprocess.run([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-hardware-aruba.mjs')],cwd=ROOT/'development/frontend',env=env,stdout=log,stderr=log,timeout=300,creationflags=NO_WINDOW)
   if done.returncode:raise RuntimeError('Browser failed; private log retained')
   expected=json.loads((out/'expected-project.json').read_text('utf-8'));assert len(expected['ports'])==61 and len(expected['connections'])==3
   session=Session(server,ids,password);prior=state(lab,db)
   # Replay does not allocate a second set of29ports or append audit/operation rows.
   replay_key=str(uuid.uuid4());replay_revision=session.project()['revision'];payload=dict(profileKey='aruba-jl682a',profileVersion='aruba-20261030-v1',rackId=ids['mixedRack'],name='Idempotent model')
   created=session.command(payload,key=replay_key,revision=replay_revision).json();created_state=state(lab,db)
   assert session.command(payload,key=replay_key,revision=replay_revision).json()==created and state(lab,db)==created_state
   # Keep the GUI baseline assertion separate from this extra command.
   expected=session.project()
   for key in ['sites','buildings','rooms','racks','devices','portGroups','ports','connections']:expected[key].sort(key=lambda x:x['id'])
   assert len(expected['ports'])==90 and len(expected['connections'])==3
   prior=state(lab,db)
   result['checks'].append('Exact command replay reuses result and29UUIDs without new operation/audit; retained outside GUI baseline')
   for version in [None,'latest','hw-reference-v1','aruba-20261030-v2']:
    payload=dict(profileKey='aruba-jl682a',rackId=ids['rack'],name='Wrong revision')
    if version is not None:payload['profileVersion']=version
    assert session.command(payload,422).json()['error']=='hardware_revision_unknown';assert state(lab,db)==prior
   # A failed audit insert must undo device/groups/ports/role/revision together.
   lab.sql(db,"CREATE FUNCTION aruba_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic audit failure'; END $$; CREATE TRIGGER aruba_fail_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION aruba_fail_audit()")
   response=session.client.request('POST',session.route+'/commands',{'type':'device.createHardware','payload':dict(profileKey='aruba-jl682a',profileVersion='aruba-20261030-v1',rackId=ids['mixedRack'],name='Rollback inlet')},{'X-RackClick-Actor':session.actor,'If-Match':f'"{expected["revision"]}"','Idempotency-Key':str(uuid.uuid4())})
   assert response.status>=500 and state(lab,db)==prior
   lab.sql(db,'DROP TRIGGER aruba_fail_audit ON audit_event; DROP FUNCTION aruba_fail_audit()')
   result['checks'].append('Forced audit failure rolls back new device/group/29ports/inlet role and preserves previous revision/operations')
   for table in CATALOG:
    assert runtime_sql(lab,db,f"SELECT has_table_privilege(current_user,'{table}','SELECT'),has_table_privilege(current_user,'{table}','INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')").stdout.strip()=='t|f'
    assert runtime_sql(lab,db,f'DELETE FROM {table}').returncode!=0
   assert runtime_sql(lab,db,'CREATE TABLE cannot_create(id integer)').returncode!=0;assert state(lab,db)==prior
   reader=Client(server);assert reader.login('hardware-reader',password).status==200;actor=reader.request('GET','/api/v1/me').json()['user']['id'];response=reader.request('POST',f"/api/v1/customers/{ids['customer']}/commands",{'type':'device.createHardware','payload':dict(profileKey='aruba-jl682a',profileVersion='aruba-20261030-v1',rackId=ids['rack'],name='Forbidden')},{'X-RackClick-Actor':actor,'If-Match':f'"{expected["revision"]}"','Idempotency-Key':str(uuid.uuid4())});assert response.status==403 and state(lab,db)==prior
   server.close();server=lab.start_server(db,dll=a.dll,frontend=a.frontend);client=Client(server);assert client.login('hardware-second',password).status==200;actual=client.request('GET',f"/api/v1/customers/{ids['customer']}/project").json()
   for key in ['sites','buildings','rooms','racks','devices','portGroups','ports','connections']:actual[key].sort(key=lambda x:x['id'])
   assert actual==expected;result.update(result='PASS',schema=19,postgresql=lab.sql('postgres','SHOW server_version'),ports=90,guiBaselinePorts=61,connections=3,restartPersistence=True,readerDeniedWithoutMutation=True)
   result['checks'].append('Bootstrap1→19 and Edge copper/SFP/power cables, labels/reload/another session, readonly/revision negatives/runtime catalog SELECT-only and restart persist exactly')
 finally:
  result.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers));(out/'RESULTADOS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
 return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
