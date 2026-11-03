"""Real Edge/PG, unknown revision fixtures remain readable without guessing v1."""
import argparse, hashlib, json, subprocess, uuid
from pathlib import Path
from pg_support import Lab, Client, NO_WINDOW, protect_directory, toolchain, literal
from test_hardware_mounting_gui import fixture

ROOT=Path(__file__).resolve().parents[3]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--frontend',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    dll=a.dll.resolve(strict=True);front=a.frontend.resolve(strict=True);output=a.output.absolute()
    if not output.resolve().is_relative_to((ROOT/'.local').resolve()):raise RuntimeError('Raw output must remain under .local')
    output.mkdir(parents=True,exist_ok=False);protect_directory(output)
    result={'result':'FAIL','fixture':'unavailable revisions simulated only by database-owner fixture edits','qaChanged':False,'serverSha256':hashlib.sha256(dll.read_bytes()).hexdigest(),'appSha256':hashlib.sha256((front/'app.js').read_bytes()).hexdigest()};lab=Lab('hardware-revisions-gui')
    try:
        with lab:
            db=lab.create_database();ids,password=fixture(lab,db,dll);lab.grant_runtime(db);server=lab.start_server(db,dll=dll,frontend=front);admin=Client(server);assert admin.login('hardware-admin',password).status==200
            prefix=f"/api/v1/customers/{ids['customer']}";actor=admin.request('GET','/api/v1/me').json()['user']['id']
            def project():return admin.request('GET',prefix+'/project').json()
            def command(kind,payload):
                r=admin.request('POST',prefix+'/commands',{'type':kind,'payload':payload},{'X-RackClick-Actor':actor,'If-Match':f'"{project()["revision"]}"','Idempotency-Key':str(uuid.uuid4())});assert r.status==200,(r.status,r.body);return r.json()['result']['resourceId']
            ids['shelf']=command('device.createHardware',{'profileKey':'shelf-2u','profileVersion':'hw-reference-v1','rackId':ids['rack'],'name':'Recorded shelf'})
            ids['firewall']=command('device.createHardware',{'profileKey':'desktop-firewall-6','profileVersion':'hw-reference-v1','rackId':ids['rack'],'name':'Recorded firewall <literal>','mountParentId':ids['shelf'],'mountSlotKey':'main'})
            port=next(p for p in project()['ports'] if p['deviceId']==ids['firewall'] and p['face']=='front')
            command('connections.create',{'fromPortId':port['id'],'toPortId':ids['legacyPort']})
            for key in ['shelf','firewall']:
                value=literal(json.dumps('missing-'+key+'-revision'))
                lab.sql(db,f"UPDATE inventory_device SET properties=jsonb_set(properties,'{{hardwareProfileVersion}}',{value}::jsonb) WHERE id='{ids[key]}'",sensitive=True)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='hardware-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(output),RACKCLICK_FIXTURE=json.dumps(ids))
            with (output/'browser.log').open('wb') as log:
                done=subprocess.run([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-hardware-revisions.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=240,creationflags=NO_WINDOW)
            if done.returncode:raise RuntimeError('Revision browser scenario failed; private output retained')
            expected=json.loads((output/'expected-project.json').read_text(encoding='utf-8'));assert len(expected['devices'])==4 and len(expected['ports'])==35 and len(expected['connections'])==1
            server.close();restarted=lab.start_server(db,dll=dll,frontend=front);reader=Client(restarted);assert reader.login('hardware-reader',password).status==200
            actual=reader.request('GET',prefix+'/project').json()
            for k in ['sites','buildings','rooms','racks','devices','portGroups','ports','connections']:actual[k].sort(key=lambda row:row['id'])
            assert actual==expected
            result.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'),existingUnavailableRevisionsPreserved=True,exactCreationRevision=True,ports=35,cables=1,reloadAndOtherSession=True,restartPersistence=True)
    finally:
        result.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers));(output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
    return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
