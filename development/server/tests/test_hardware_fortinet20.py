"""Fresh PG17/Windows Edge: exact FortiGate60F desktop mounting, no installed VM."""
import argparse,hashlib,json,uuid,subprocess
from pathlib import Path
from pg_support import Lab,Client,NO_WINDOW,protect_directory,toolchain
from test_hardware_mounting_gui import fixture
from test_hardware_catalog17 import Session,state,migrate,runtime_sql,CATALOG
ROOT=Path(__file__).resolve().parents[3]
KEY='fortinet-fg60f';VERSION='fortinet-20261030-v1'

def ordered(project):
 for key in ['sites','buildings','rooms','racks','devices','portGroups','ports','connections']:project[key].sort(key=lambda x:x['id'])
 return project

def main():
 p=argparse.ArgumentParser()
 for n in ['dll','baseline-dll','frontend','output']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.dll=a.dll.resolve(strict=True);a.baseline_dll=a.baseline_dll.resolve(strict=True);a.frontend=a.frontend.resolve(strict=True);out=a.output.resolve();assert out.is_relative_to((ROOT/'.local').resolve());out.mkdir(exist_ok=False);protect_directory(out)
 result={'result':'FAIL','checks':[],'serverSha256':hashlib.sha256(a.dll.read_bytes()).hexdigest(),'appSha256':hashlib.sha256((a.frontend/'app.js').read_bytes()).hexdigest(),'qaAccessed':False,'vmAccessed':False};lab=Lab('fortinet20')
 try:
  with lab:
   old=lab.create_database('upgrade19');ids,password=fixture(lab,old,a.baseline_dll);lab.grant_runtime(old);s=lab.start_server(old,dll=a.baseline_dll);session=Session(s,ids,password)
   for key,version in [('startech-c6panelutp241uft','startech-20261030-v1'),('aruba-jl682a','aruba-20261030-v1')]:session.command(dict(profileKey=key,profileVersion=version,rackId=ids['rack'],name='Previo '+key))
   expected=session.project();before=state(lab,old,catalog=False);defs=lab.sql(old,'SELECT jsonb_agg(to_jsonb(t) ORDER BY profile_key) FROM hardware_definition t');history=lab.sql(old,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t');s.close()
   assert migrate(lab,old,a.dll,out/'migrate-private.txt')==0;assert lab.sql(old,'SELECT max(version) FROM schema_migration')=='20';assert state(lab,old,catalog=False)==before
   assert lab.sql(old,"SELECT jsonb_agg(to_jsonb(t) ORDER BY profile_key) FROM hardware_definition t WHERE profile_key<>'fortinet-fg60f'")==defs
   assert lab.sql(old,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t WHERE version<=19')==history
   lab.grant_runtime(old);s=lab.start_server(old,dll=a.dll);assert Session(s,ids,password).project()==expected;s.close();result['checks'].append('19->20 preserves StarTech48/Aruba29 UUIDs, six definitions, existing inventory/operations/audit and digests1..19')
   db=lab.create_database('fresh20');ids,password=fixture(lab,db,a.dll);lab.grant_runtime(db);assert lab.sql(db,'SELECT max(version) FROM schema_migration')=='20';assert lab.sql(db,'SELECT count(*) FROM hardware_definition')=='7'
   server=lab.start_server(db,dll=a.dll,frontend=a.frontend);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='hardware-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(out),RACKCLICK_FIXTURE=json.dumps(ids))
   with (out/'browser-private.log').open('wb') as log:done=subprocess.run([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-hardware-fortinet.mjs')],cwd=ROOT/'development/frontend',env=env,stdout=log,stderr=log,timeout=300,creationflags=NO_WINDOW)
   if done.returncode:raise RuntimeError('Browser failed; private log retained')
   expected=json.loads((out/'expected-project.json').read_text('utf-8'));assert len(expected['ports'])==51 and len(expected['connections'])==3
   assert lab.sql(db,f"SELECT sum(size_u) FROM inventory_device WHERE rack_id='{ids['rack']}'")=='4'
   session=Session(server,ids,password);prior=state(lab,db);shelf=next(d['id'] for d in expected['devices'] if d['name']=='Bandeja Fortinet A')
   base=dict(profileKey=KEY,profileVersion=VERSION,rackId=ids['rack'],name='Rejected',mountParentId=shelf,mountSlotKey='main')
   assert session.command(base,409).json()['error']=='mount_slot_occupied';assert state(lab,db)==prior
   for change in [dict(mountParentId=ids['legacy']),dict(mountParentId=None),dict(mountSlotKey='other')]:
    assert session.command(base|change,422).status==422;assert state(lab,db)==prior
   for version in [None,'latest','hw-reference-v1','fortinet-20261030-v2']:
    payload=base.copy();payload.pop('profileVersion')
    if version is not None:payload['profileVersion']=version
    assert session.command(payload,422).json()['error']=='hardware_revision_unknown';assert state(lab,db)==prior
   result['checks'].append('GUI two shelves reserve4U, FG children0U; occupied/absent/wrong-rack/wrong-slot parents and unknown revisions reject without mutation')
   # Additional shelves are explicit roots; the first supports exact idempotent replay.
   shelf_ids=[]
   for name in ['Replay shelf','Rollback shelf']:
    session.command(dict(profileKey='shelf-2u',profileVersion='hw-reference-v1',rackId=ids['mixedRack'],name=name));shelf_ids.append(next(d['id'] for d in session.project()['devices'] if d['name']==name))
   replay_key=str(uuid.uuid4());revision=session.project()['revision'];payload=dict(profileKey=KEY,profileVersion=VERSION,rackId=ids['mixedRack'],name='Idempotent FG',mountParentId=shelf_ids[0],mountSlotKey='main')
   created=session.command(payload,key=replay_key,revision=revision).json();created_state=state(lab,db)
   assert session.command(payload,key=replay_key,revision=revision).json()==created and state(lab,db)==created_state
   expected=ordered(session.project());assert len(expected['ports'])==61 and len(expected['connections'])==3;prior=state(lab,db)
   lab.sql(db,"CREATE FUNCTION fg_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic audit failure'; END $$; CREATE TRIGGER fg_fail_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION fg_fail_audit()")
   payload=dict(profileKey=KEY,profileVersion=VERSION,rackId=ids['mixedRack'],name='Rollback FG',mountParentId=shelf_ids[1],mountSlotKey='main')
   response=session.client.request('POST',session.route+'/commands',{'type':'device.createHardware','payload':payload},{'X-RackClick-Actor':session.actor,'If-Match':f'"{expected["revision"]}"','Idempotency-Key':str(uuid.uuid4())})
   assert response.status>=500 and state(lab,db)==prior
   lab.sql(db,'DROP TRIGGER fg_fail_audit ON audit_event; DROP FUNCTION fg_fail_audit()')
   result['checks'].append('Replay preserves result/10UUIDs/audit; forced audit failure rolls back child/groups/ports/mount/revision together')
   for table in CATALOG:
    assert runtime_sql(lab,db,f"SELECT has_table_privilege(current_user,'{table}','SELECT'),has_table_privilege(current_user,'{table}','INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')").stdout.strip()=='t|f'
    assert runtime_sql(lab,db,f'DELETE FROM {table}').returncode!=0
   assert runtime_sql(lab,db,'CREATE TABLE cannot_create(id integer)').returncode!=0;assert state(lab,db)==prior
   reader=Client(server);assert reader.login('hardware-reader',password).status==200;actor=reader.request('GET','/api/v1/me').json()['user']['id']
   response=reader.request('POST',f"/api/v1/customers/{ids['customer']}/commands",{'type':'device.createHardware','payload':base},{'X-RackClick-Actor':actor,'If-Match':f'"{expected["revision"]}"','Idempotency-Key':str(uuid.uuid4())});assert response.status==403 and state(lab,db)==prior
   server.close();server=lab.start_server(db,dll=a.dll,frontend=a.frontend);client=Client(server);assert client.login('hardware-second',password).status==200;actual=ordered(client.request('GET',f"/api/v1/customers/{ids['customer']}/project").json());assert actual==expected
   result.update(result='PASS',schema=20,postgresql=lab.sql('postgres','SHOW server_version'),ports=61,guiBaselinePorts=51,connections=3,restartPersistence=True,readerDeniedWithoutMutation=True,dcConnectionsTested=False)
   result['checks'].append('Bootstrap1->20; Edge physical rear ports, cable anchors, labels/reload/second session/reader and server restart persist; no DC/AC or serial/USB connection claimed')
 finally:
  result.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers));(out/'RESULTADOS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
 return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
