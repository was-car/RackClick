"""Commercial model, real17→18 migration and Edge; all data/labs newly generated."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
from pg_support import Lab,Client,protect_directory,toolchain,NO_WINDOW
from test_hardware_mounting_gui import fixture
from test_hardware_catalog17 import Session,migrate,state

ROOT=Path(__file__).resolve().parents[3]


def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',type=Path,required=True);p.add_argument('--baseline-dll',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    dll=a.dll.resolve(strict=True);baseline=a.baseline_dll.resolve(strict=True);front=a.frontend.resolve(strict=True)
    a.output.mkdir(parents=True,exist_ok=False);protect_directory(a.output)
    result=dict(result='FAIL',checks=[],serverSha256=hashlib.sha256(dll.read_bytes()).hexdigest(),appSha256=hashlib.sha256((front/'app.js').read_bytes()).hexdigest(),baselineSha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),qaAccessed=False,vmAccessed=False)
    lab=Lab('hardware-commercial')
    try:
        with lab:
            db=lab.create_database('real17to18');ids,password=fixture(lab,db,baseline);lab.grant_runtime(db)
            assert lab.sql(db,'SELECT max(version) FROM schema_migration')=='17'
            server17=lab.start_server(db,dll=baseline);old=Session(server17,ids,password)
            ids['shelf']=old.hardware('shelf-2u',ids['rack']);ids['firewall']=old.hardware('desktop-firewall-6',ids['rack'],ids['shelf'])
            before=state(lab,db);snapshot=old.project();history=lab.sql(db,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t')
            server17.close();assert migrate(lab,db,dll,a.output/'migrate-private.txt')==0
            assert lab.sql(db,'SELECT max(version) FROM schema_migration')=='18'
            # Exclude the new model from the preexisting global definitions when comparing.
            assert lab.sql(db,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t WHERE version<=17')==history
            server=lab.start_server(db,dll=dll,frontend=front);current=Session(server,ids,password);assert current.project()==snapshot
            result['checks'].append('actual17to18 migration preserves previous project and migration digests; numeric height/depth retain old values')
            # Exact source facts and a sealed, read-only catalog; no IFC/IDC invented.
            model='startech-c6panelutp241uft';revision='startech-20261030-v1'
            row=lab.sql(db,f"SELECT width_mm,height_mm,depth_mm,rack_units,manufacturer,model,sealed FROM hardware_definition WHERE profile_key='{model}' AND revision='{revision}'")
            assert row=='483|44.3|138|1|StarTech.com|C6PANELUTP241UFT|t',row
            assert lab.sql(db,"SELECT count(*) FROM hardware_definition")=='5'
            before=state(lab,db)
            for bad in [None,'hw-reference-v1','latest','startech-20261030-v2']:
                payload=dict(profileKey=model,profileVersion=bad,rackId=ids['rack'],name='Rejected')
                assert current.command(payload,422).status==422 and state(lab,db)==before
            assert current.command(dict(profileKey=model,rackId=ids['rack'],name='Omitted'),422).status==422 and state(lab,db)==before
            reader=Client(server);assert reader.login('hardware-reader',password).status==200
            response=reader.request('POST',current.route+'/commands',{'type':'device.createHardware','payload':dict(profileKey=model,profileVersion=revision,rackId=ids['rack'],name='Forbidden')},{'X-RackClick-Actor':reader.request('GET','/api/v1/me').json()['user']['id'],'If-Match':f'"{snapshot["revision"]}"','Idempotency-Key':str(uuid.uuid4())})
            assert response.status==403 and state(lab,db)==before
            result['checks'].append('exact model facts483x44.3x138mm,1U; five invalid revision requests and reader403 leave rows/audit/revision unchanged')
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='hardware-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(a.output),RACKCLICK_FIXTURE=json.dumps(ids))
            with (a.output/'browser-private.log').open('wb') as log:
                done=subprocess.run([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-hardware-commercial.mjs')],cwd=ROOT/'development/frontend',env=env,stdout=log,stderr=log,timeout=300,creationflags=NO_WINDOW)
            if done.returncode:raise RuntimeError('Browser scenario failed; private log retained')
            expected=json.loads((a.output/'expected-project.json').read_text(encoding='utf-8'));assert len(expected['ports'])==105 and len(expected['connections'])==2
            assert lab.sql(db,f"SELECT sum(size_u) FROM inventory_device WHERE rack_id='{ids['rack']}'")=='4'
            server.close();restarted=lab.start_server(db,dll=dll,frontend=front);other=Session(restarted,ids,password)
            assert sorted(other.project()['ports'],key=lambda p:p['id'])==expected['ports']
            assert other.project()['devices'] and all(d['properties']['physicalDimensionsMm']['height']==44.3 for d in other.project()['devices'] if d['hardwareProfileKey']==model)
            normalized=other.project()
            for key in ['sites','buildings','rooms','racks','devices','portGroups','ports','connections']:normalized[key].sort(key=lambda x:x['id'])
            assert normalized==expected
            result['checks'].append('Edge creates2models/96ports and2cables, edits/reloads/second account/reader; full project persists after host restart')
            # A fresh bootstrap also installs all eighteen migrations and the same model.
            fresh=lab.create_database('fresh18');fresh_ids,fresh_password=fixture(lab,fresh,dll);lab.grant_runtime(fresh)
            assert lab.sql(fresh,'SELECT max(version) FROM schema_migration')=='18'
            assert lab.sql(fresh,f"SELECT height_mm FROM hardware_definition WHERE profile_key='{model}'")=='44.3'
            result.update(result='PASS',schema=18,postgresql=lab.sql('postgres','SHOW server_version'),ports=105,connections=2,restartPersistence=True,freshBootstrap=True)
    finally:
        result.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers));(a.output/'RESULTADOS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
    return 0 if result['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
