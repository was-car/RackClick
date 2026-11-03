"""One visual shell, fresh PostgreSQL17/runtime role and actual Windows Edge."""
import argparse
import hashlib
import json
import uuid
from pathlib import Path
import subprocess
from pg_support import Lab, Client, NO_WINDOW, protect_directory, toolchain
from test_hardware_mounting_gui import fixture
from test_hardware_catalog17 import Session, state

ROOT=Path(__file__).resolve().parents[3]

def main():
    parser=argparse.ArgumentParser()
    for name in ['dll','frontend','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--private-photo',action='store_true')
    parser.add_argument('--flat-front',action='store_true')
    a=parser.parse_args();dll=a.dll.resolve(strict=True);front=a.frontend.resolve(strict=True);out=a.output.resolve()
    if not out.is_relative_to((ROOT/'.local').resolve()):raise RuntimeError('Private output required')
    out.mkdir(parents=True,exist_ok=False);protect_directory(out)
    result=dict(result='FAIL',checks=[],serverSha256=hashlib.sha256(dll.read_bytes()).hexdigest(),appSha256=hashlib.sha256((front/'app.js').read_bytes()).hexdigest(),cssSha256=hashlib.sha256((front/'app.css').read_bytes()).hexdigest(),qaAccessed=False,vmAccessed=False)
    lab=Lab('hardware-shell-lot1')
    try:
        with lab:
            db=lab.create_database('shell');ids,password=fixture(lab,db,dll);lab.grant_runtime(db)
            assert lab.sql(db,'SELECT max(version) FROM schema_migration')=='18'
            server=lab.start_server(db,dll=dll,frontend=front)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='hardware-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(out),RACKCLICK_FIXTURE=json.dumps(ids))
            with (out/'browser-private.log').open('wb') as log:
                scenario='browser-hardware-flat.mjs' if a.flat_front else 'browser-hardware-photo.mjs' if a.private_photo else 'browser-hardware-shells.mjs'
                done=subprocess.run([str(toolchain()['node']),str(ROOT/'development/frontend/tests'/scenario)],cwd=ROOT/'development/frontend',env=env,stdout=log,stderr=log,timeout=300,creationflags=NO_WINDOW)
            if done.returncode:raise RuntimeError('Browser failed; private log retained')
            expected=json.loads((out/'expected-project.json').read_text('utf-8'));assert len(expected['ports'])==98 and len(expected['connections'])==2
            reader=Client(server);assert reader.login('hardware-reader',password).status==200
            # Authorization is checked by the server even if a caller bypasses UI.
            before=state(lab,db)
            response=reader.request('POST',f"/api/v1/customers/{ids['customer']}/commands",dict(type='device.createHardware',payload=dict(profileKey='startech-c6panelutp241uft',profileVersion='startech-20261030-v1',rackId=ids['rack'],name='Forbidden')),{'X-RackClick-Actor':reader.request('GET','/api/v1/me').json()['user']['id'],'If-Match':f'"{expected["revision"]}"','Idempotency-Key':str(uuid.uuid4())})
            assert response.status==403
            assert state(lab,db)==before
            server.close();restarted=lab.start_server(db,dll=dll,frontend=front);client=Client(restarted)
            assert client.login('hardware-second',password).status==200
            actual=client.request('GET',f"/api/v1/customers/{ids['customer']}/project").json()
            for key in ['sites','buildings','rooms','racks','devices','portGroups','ports','connections']:actual[key].sort(key=lambda x:x['id'])
            assert actual==expected
            result.update(result='PASS',schema=18,postgresql=lab.sql('postgres','SHOW server_version'),ports=98,connections=2,restartPersistence=True,readerDeniedWithoutMutation=True)
    finally:
        result.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers));(out/'RESULTADOS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
    return 0 if result['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
