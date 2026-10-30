"""Single focused native Edge/PostgreSQL60 scenario. New labs only, explicit immutable artifacts."""
import argparse,hashlib,json,platform,secrets,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,literal,toolchain
from windows_job import run_isolated
from test_inventory_movement_gui import fixture as seed,durable,project_by_id,tree

def inputs(dll,frontend):
    files=[Path(__file__),ROOT/'development/frontend/tests/browser-client-changes.mjs',ROOT/'development/frontend/tests/browser-client-changes-localization.mjs',ROOT/'development/frontend/tests/browser-client-changes-support.mjs',Path(__file__).with_name('pg_support.py'),Path(__file__).with_name('test_inventory_movement_gui.py'),ROOT/'tools/windows/windows_job.py']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'server':tree(dll.parent),'frontend':tree(frontend)}

def fixture(lab,db,dll):
    ids,password=seed(lab,db,dll);house,admin=lab.sql(db,"SELECT id FROM systemhaus;SELECT id FROM app_user WHERE username='move-admin'").splitlines();ids.update(house=house,admin=admin,outsider=str(uuid.uuid4()),outsiderGroup=str(uuid.uuid4()),secondName='notice-second-<img>-ω')
    lab.sql(db,f"""BEGIN;
    UPDATE app_user SET username={literal(ids['secondName'])} WHERE id='{ids['second']}';
    INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{ids['outsider']}',systemhaus_id,'notice-outsider',password_hash FROM app_user WHERE id='{admin}';
    INSERT INTO user_group VALUES('{ids['outsiderGroup']}','{house}','Outside notices only');
    INSERT INTO user_group_member VALUES('{house}','{ids['outsider']}','{ids['baseGroup']}'),('{house}','{ids['outsider']}','{ids['outsiderGroup']}');
    INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{house}','{ids['outsiderGroup']}','inventory.read','{ids['other']}',NULL);
    COMMIT;""",sensitive=True)
    ids['readerGrant']=lab.sql(db,f"SELECT id FROM permission_grant WHERE user_group_id='{ids['readerGroup']}' AND capability='inventory.read'")
    return ids,password

def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--localization-only',action='store_true');a=p.parse_args();dll=a.dll.resolve(strict=True);front=a.frontend.resolve(strict=True);a.output.mkdir(parents=True,exist_ok=False)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'inputs':inputs(dll,front),'result':'FAIL','scope':'localization and logout only' if a.localization_only else 'full scenario','realQaAccessed':False,'fixtureCreatedBy':'SQL synthetic inventory/users/grants; later writes HTTP'};lab=Lab('notice-gui60');tick=time.monotonic()
    try:
        with lab:
            db=lab.create_database('notice-gui60');ids,password=fixture(lab,db,dll);lab.grant_runtime(db);before=durable(lab,db);server=lab.start_server(db,dll=dll,frontend=front);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(a.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            with (a.output/'browser.log').open('wb') as log:done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests'/('browser-client-changes-localization.mjs' if a.localization_only else 'browser-client-changes.mjs'))],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=300)
            report['browserExitCode']=done.returncode
            if done.returncode:raise RuntimeError('Browser scenario failed; evidence retained')
            expected=json.loads((a.output/'expected-project.json').read_text(encoding='utf-8'));after=durable(lab,db)
            for table in before:
                if table not in ['inventory_port','inventory_connection','inventory_connection_endpoint']:assert before[table]==after[table],table
            wanted=json.loads(json.dumps(before['inventory_port']))
            for port in wanted:
                if port['id']==ids['pb2']:port['label']='Etiqueta es' if a.localization_only else 'Etiqueta de'
            assert sorted(wanted,key=lambda r:r['id'])==sorted(after['inventory_port'],key=lambda r:r['id'])
            assert len(after['inventory_connection'])==len(before['inventory_connection'])+(0 if a.localization_only else 1)
            server.close();restart=lab.start_server(db,dll=dll,frontend=front);reader=Client(restart);assert reader.login('move-admin',password).status==200;response=reader.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert response.headers['etag']==f'"{expected["revision"]}"';assert project_by_id(response.json())==project_by_id(expected);assert durable(lab,db)==after
            report.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'),inventoryChangesExpectedOnly=True,aspNetRestartPersistence=True)
    except Exception as e:report.update(failureType=type(e).__name__,failure=str(e))
    finally:
        report.update(seconds=round(time.monotonic()-tick,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,front));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (a.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
