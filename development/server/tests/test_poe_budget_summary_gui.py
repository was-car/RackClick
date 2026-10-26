"""One isolated native PoE summary scenario; artifacts supplied by coordinator, no build/install/QA reuse."""
import argparse,hashlib,json,platform,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'))
sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain
from windows_job import run_isolated
from test_inventory_movement_gui import fixture as seed,durable,tree,project_by_id
from test_inventory_poe_face_gui import canonical

def inputs(dll,frontend):
    paths=[Path(__file__),Path(__file__).with_name('test_inventory_movement_gui.py'),
           Path(__file__).with_name('test_inventory_poe_face_gui.py'),Path(__file__).with_name('pg_support.py'),
           ROOT/'tools/windows/windows_job.py',ROOT/'development/frontend/tests/browser-quince-support.mjs',
           ROOT/'development/frontend/tests/browser-poe-budget-summary.mjs']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            'server':tree(dll.parent),'frontend':tree(frontend)}

def fixture(lab,db,dll):
    ids,password=seed(lab,db,dll)
    power_group=str(uuid.uuid4())
    lab.sql(db,f"""BEGIN;
    UPDATE customer SET name='PoE summary synthetic' WHERE id='{ids['customer']}';
    UPDATE inventory_device SET name='PoE literal Ω <img>',poe_budget=NULL WHERE id='{ids['a']}';
    UPDATE inventory_device SET name='PoE literal Ω <img>',poe_budget=0 WHERE id='{ids['b']}';
    UPDATE inventory_device SET name='PoE fault and AC',poe_budget=2 WHERE id='{ids['c']}';
    UPDATE inventory_port SET watts=NULL WHERE id='{ids['pa']}';
    UPDATE inventory_port SET watts=0 WHERE id='{ids['pa2']}';
    UPDATE inventory_port SET watts=5,status='disabled' WHERE id='{ids['pb']}';
    UPDATE inventory_port SET watts=9.5,poe=false WHERE id='{ids['pb2']}';
    UPDATE inventory_port SET watts=2.5,status='faulty' WHERE id='{ids['pc']}';
    INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order)
    SELECT '{power_group}',systemhaus_id,customer_id,device_id,'power','AC','AC',1 FROM inventory_port_group WHERE id='{ids['gc']}';
    UPDATE inventory_port SET group_id='{power_group}',type='power',poe=false,watts=90 WHERE id='{ids['pc2']}';
    COMMIT;""",sensitive=True)
    return ids,password

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True)
    parser.add_argument('--frontend',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file():raise RuntimeError('Complete explicit artifacts required')
    args.output.mkdir(parents=True,exist_ok=False)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL',
            'inputs':inputs(dll,frontend),'realQaAccessed':False,'productModified':False,'fixtureCreatedBy':'SQL; not GUI creation'}
    started=time.monotonic();lab=Lab('poe-summary65')
    try:
        with lab:
            db=lab.create_database('poe-summary65');ids,password=fixture(lab,db,dll);lab.grant_runtime(db)
            before=durable(lab,db);server=lab.start_server(db,dll=dll,frontend=frontend)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',
                RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            with (args.output/'browser-windows.log').open('wb') as log:
                done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-poe-budget-summary.mjs')],
                    env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=180)
            report['browserExitCode']=done.returncode
            if done.returncode:raise RuntimeError('Browser failed; evidence retained')
            expected=json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'))
            wanted=json.loads(json.dumps(before));after=durable(lab,db)
            for row in wanted['inventory_port']:
                if row['id']==ids['pb2']:row.update(poe=True,type='rj45_poe')
            for row in wanted['inventory_device']:
                if row['id']==ids['b']:row.update(poe_budget=14.5)
            assert canonical(after)==canonical(wanted),'Nine SQL tables exact except target ON flag/type and budget'
            report['sqlExactChangesOnly']=True
            reader=Client(server);assert reader.login('move-reader',password).status==200
            assert reader.request('GET',f"/api/v1/customers/{ids['other']}/project").status==404
            report['outsideScopeRead']=404
            server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend)
            admin=Client(restarted);assert admin.login('move-admin',password).status==200
            response=admin.request('GET',f"/api/v1/customers/{ids['customer']}/project")
            assert response.status==200 and response.headers['etag']==f'"{expected["revision"]}"'
            assert project_by_id(response.json())==project_by_id(expected)
            assert canonical(durable(lab,db))==canonical(after)
            report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,
            serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,frontend))
        report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
