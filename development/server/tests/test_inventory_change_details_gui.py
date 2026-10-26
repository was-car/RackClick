"""One Windows Edge/PG details scenario, explicit frozen candidate, no real QA."""
import argparse,hashlib,json,platform,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain
from windows_job import run_isolated
from test_client_changes_gui import fixture
from test_inventory_movement_gui import durable,tree,project_by_id

def inputs(dll,front):
    paths=[Path(__file__),Path(__file__).with_name('pg_support.py'),Path(__file__).with_name('test_client_changes_gui.py'),Path(__file__).with_name('test_inventory_movement_gui.py'),ROOT/'tools/windows/windows_job.py',ROOT/'development/frontend/tests/browser-client-change-details.mjs',ROOT/'development/frontend/tests/browser-client-changes-support.mjs']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'server':tree(dll.parent),'frontend':tree(front)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    dll=a.dll.resolve(strict=True);front=a.frontend.resolve(strict=True);a.output.mkdir(parents=True,exist_ok=False)
    lab=Lab('details472-gui');started=time.monotonic();report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'inputs':inputs(dll,front),'result':'FAIL','realQaAccessed':False,'fixtureCreatedBy':'Synthetic SQL bootstrap/users/inventory; changes under test real HTTP'}
    try:
        with lab:
            db=lab.create_database('details472-gui');ids,password=fixture(lab,db,dll);lab.grant_runtime(db);before=durable(lab,db)
            server=lab.start_server(db,dll=dll,frontend=front);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(a.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            with (a.output/'browser.log').open('wb') as log:r=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-client-change-details.mjs')],cwd=ROOT/'development/frontend',env=env,stdout=log,stderr=log,timeout=240)
            report['browserExitCode']=r.returncode
            if r.returncode:raise RuntimeError('Browser failed; evidence retained')
            expected=json.loads((a.output/'expected-project.json').read_text(encoding='utf-8'));after=durable(lab,db)
            assert before==after,'Nine inventory tables exactly restored by deleting only the new synthetic device'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action LIKE 'inventory.%'")=='7'
            report['inventoryAuditEvents']=7
            server.close();restart=lab.start_server(db,dll=dll,frontend=front);client=Client(restart);assert client.login('move-admin',password).status==200
            actual=client.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert actual.status==200 and project_by_id(actual.json())==project_by_id(expected)
            page=client.request('GET',f"/api/v1/customers/{ids['customer']}/changes/details?afterRevision=1");assert page.status==200 and len(page.json()['events'])==7
            assert all(e['details']['status']=='captured' for e in page.json()['events']);assert durable(lab,db)==after
            report.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'),restartHistoricalPersistence=True,nineInventoryTablesExactlyUnchanged=True)
    except Exception as error:report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,front));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (a.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
