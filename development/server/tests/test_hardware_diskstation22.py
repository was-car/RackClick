"""Isolated PG17/Windows Edge: DS423+ upright on its explicit taller shelf."""
import argparse,hashlib,json,uuid,subprocess
from pathlib import Path
from pg_support import Lab,Client,NO_WINDOW,protect_directory,toolchain
from test_hardware_mounting_gui import fixture
from test_hardware_catalog17 import Session,state,migrate,runtime_sql,CATALOG
ROOT=Path(__file__).resolve().parents[3]
KEY='synology-ds423plus';VERSION='synology-ds423plus-20261030-v1';SUPPORT='mount-support-20261030-v1'

def ordered(project):
 for key in ['sites','buildings','rooms','racks','devices','portGroups','ports','connections']:project[key].sort(key=lambda x:x['id'])
 return project

def main():
 p=argparse.ArgumentParser()
 for n in ['dll','baseline-dll','frontend','output']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.dll=a.dll.resolve(strict=True);a.baseline_dll=a.baseline_dll.resolve(strict=True);a.frontend=a.frontend.resolve(strict=True);out=a.output.resolve();assert out.is_relative_to((ROOT/'.local').resolve());out.mkdir(exist_ok=False);protect_directory(out)
 result={'result':'FAIL','checks':[],'serverSha256':hashlib.sha256(a.dll.read_bytes()).hexdigest(),'appSha256':hashlib.sha256((a.frontend/'app.js').read_bytes()).hexdigest(),'qaAccessed':False,'vmAccessed':False};lab=Lab('diskstation22')
 try:
  with lab:
   old=lab.create_database('upgrade21');ids,password=fixture(lab,old,a.baseline_dll);lab.grant_runtime(old);s=lab.start_server(old,dll=a.baseline_dll);session=Session(s,ids,password)
   for key,version,rack in [('startech-c6panelutp241uft','startech-20261030-v1',ids['mixedRack']),('aruba-jl682a','aruba-20261030-v1',ids['mixedRack']),('shelf-2u','hw-reference-v1',ids['rack']),('synology-rs1221plus','synology-20261030-v1',ids['rack'])]:session.command(dict(profileKey=key,profileVersion=version,rackId=rack,name='Previo '+key))
   support=next(d['id'] for d in session.project()['devices'] if d['name']=='Previo shelf-2u');session.command(dict(profileKey='fortinet-fg60f',profileVersion='fortinet-20261030-v1',rackId=ids['rack'],name='Previo FG',mountParentId=support,mountSlotKey='main'))
   expected=session.project();before=state(lab,old,catalog=False);defs=lab.sql(old,'SELECT jsonb_agg(to_jsonb(t) ORDER BY profile_key) FROM hardware_definition t');history=lab.sql(old,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t');s.close()
   assert migrate(lab,old,a.dll,out/'migrate-private.txt')==0;assert lab.sql(old,'SELECT max(version) FROM schema_migration')=='22';assert state(lab,old,catalog=False)==before
   assert lab.sql(old,"SELECT jsonb_agg(to_jsonb(t) ORDER BY profile_key) FROM hardware_definition t WHERE profile_key NOT IN ('synology-ds423plus','shelf-5u')")==defs
   assert lab.sql(old,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t WHERE version<=21')==history
   lab.grant_runtime(old);s=lab.start_server(old,dll=a.dll);assert Session(s,ids,password).project()==expected;s.close();result['checks'].append('21->22 preserves all four prior commercial instances/UUIDs, generic low shelf/mount, eight definitions, inventory/audit/operations and migration history1..21')
   db=lab.create_database('fresh22');ids,password=fixture(lab,db,a.dll);lab.grant_runtime(db);assert lab.sql(db,'SELECT max(version) FROM schema_migration')=='22';assert lab.sql(db,'SELECT count(*) FROM hardware_definition')=='10';lab.sql(db,f"UPDATE inventory_rack SET size_u=10,name='Rack DiskStation 10U' WHERE id='{ids['rack']}'")
   server=lab.start_server(db,dll=a.dll,frontend=a.frontend);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='hardware-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(out),RACKCLICK_FIXTURE=json.dumps(ids))
   with (out/'browser-private.log').open('wb') as log:done=subprocess.run([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-hardware-diskstation.mjs')],cwd=ROOT/'development/frontend',env=env,stdout=log,stderr=log,timeout=360,creationflags=NO_WINDOW)
   if done.returncode:raise RuntimeError('Browser failed; private log retained')
   expected=json.loads((out/'expected-project.json').read_text('utf-8'));assert len(expected['ports'])==38 and len(expected['connections'])==2;assert lab.sql(db,f"SELECT sum(size_u) FROM inventory_device WHERE rack_id='{ids['rack']}'")=='10'
   session=Session(server,ids,password);prior=state(lab,db);low=next(d['id'] for d in expected['devices'] if d['name']=='Bandeja baja preservada');tall=next(d['id'] for d in expected['devices'] if d['name']=='Bandeja alta NAS 5U');base=dict(profileKey=KEY,profileVersion=VERSION,rackId=ids['rack'],name='Rejected DS',mountParentId=tall,mountSlotKey='main')
   assert session.command(base,409).json()['error']=='mount_slot_occupied';assert state(lab,db)==prior
   for change,error in [(dict(mountParentId=low),'mount_dimensions_invalid'),(dict(mountParentId=None),'mount_parent_required'),(dict(mountParentId=ids['legacy']),'mount_support_invalid'),(dict(mountSlotKey='other'),'mount_support_invalid')]:
    assert session.command(base|change,422).json()['error']==error;assert state(lab,db)==prior
   assert session.command(dict(profileKey='shelf-5u',profileVersion=SUPPORT,rackId=ids['rack'],name='Capacity'),409).status==409;assert state(lab,db)==prior
   for version in [None,'latest','hw-reference-v1',SUPPORT]:
    payload=base.copy();payload.pop('profileVersion')
    if version is not None:payload['profileVersion']=version
    assert session.command(payload,422).json()['error']=='hardware_revision_unknown';assert state(lab,db)==prior
   result['checks'].append('Server rejects166mmNAS in60mm old bay, missing/wrong-rack/wrong-slot/occupied support and unknown revisions without mutation; new5U root respects rack capacity')
   shelves=[]
   for name in ['Replay tall shelf','Rollback tall shelf']:
    session.command(dict(profileKey='shelf-5u',profileVersion=SUPPORT,rackId=ids['mixedRack'],name=name));shelves.append(next(d['id'] for d in session.project()['devices'] if d['name']==name))
   replay_key=str(uuid.uuid4());revision=session.project()['revision'];payload=base|dict(rackId=ids['mixedRack'],name='Idempotent DS',mountParentId=shelves[0]);created=session.command(payload,key=replay_key,revision=revision).json();created_state=state(lab,db);assert session.command(payload,key=replay_key,revision=revision).json()==created and state(lab,db)==created_state
   expected=ordered(session.project());assert len(expected['ports'])==40 and len(expected['connections'])==2;prior=state(lab,db)
   lab.sql(db,"CREATE FUNCTION ds_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic audit failure'; END $$; CREATE TRIGGER ds_fail_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION ds_fail_audit()")
   response=session.client.request('POST',session.route+'/commands',{'type':'device.createHardware','payload':base|dict(rackId=ids['mixedRack'],name='Rollback DS',mountParentId=shelves[1])},{'X-RackClick-Actor':session.actor,'If-Match':f'"{expected["revision"]}"','Idempotency-Key':str(uuid.uuid4())});assert response.status>=500 and state(lab,db)==prior
   lab.sql(db,'DROP TRIGGER ds_fail_audit ON audit_event; DROP FUNCTION ds_fail_audit()');result['checks'].append('Exact replay allocates no extraUUIDs/audit; forced audit failure rolls back child/mount/groups/2ports/revision/operation')
   for table in CATALOG:
    assert runtime_sql(lab,db,f"SELECT has_table_privilege(current_user,'{table}','SELECT'),has_table_privilege(current_user,'{table}','INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')").stdout.strip()=='t|f';assert runtime_sql(lab,db,f'DELETE FROM {table}').returncode!=0
   assert runtime_sql(lab,db,'CREATE TABLE cannot_create(id integer)').returncode!=0;assert state(lab,db)==prior
   reader=Client(server);assert reader.login('hardware-reader',password).status==200;actor=reader.request('GET','/api/v1/me').json()['user']['id'];response=reader.request('POST',f"/api/v1/customers/{ids['customer']}/commands",{'type':'device.createHardware','payload':base},{'X-RackClick-Actor':actor,'If-Match':f'"{expected["revision"]}"','Idempotency-Key':str(uuid.uuid4())});assert response.status==403 and state(lab,db)==prior
   server.close();server=lab.start_server(db,dll=a.dll,frontend=a.frontend);client=Client(server);assert client.login('hardware-second',password).status==200;actual=ordered(client.request('GET',f"/api/v1/customers/{ids['customer']}/project").json());assert actual==expected
   result.update(result='PASS',schema=22,postgresql=lab.sql('postgres','SHOW server_version'),ports=40,guiBaselinePorts=38,connections=2,desktopAdditionalUnits=0,tallShelfReservedUnits=5,readerDeniedWithoutMutation=True,restartPersistence=True,dcConnectionsTested=False)
   result['checks'].append('Bootstrap1->22 and WindowsEdge uprightDS423+ / front4trays/rear2UUIDs, actual tall-shelf filtering/captions/keyboard/labels/cross-face cables/reload/second session/reader; server restart persists exactly')
 finally:
  result.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers));(out/'RESULTADOS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
 return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
