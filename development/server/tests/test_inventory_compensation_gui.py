"""One isolated native port compensation scenario; artifacts supplied by coordinator, no build/install/QA reuse."""
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
           ROOT/'development/frontend/tests/browser-inventory-compensation.mjs']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            'server':tree(dll.parent),'frontend':tree(frontend)}

def fixture(lab,db,dll):
    ids,password=seed(lab,db,dll)
    duplicate_group=str(uuid.uuid4());duplicate_port=str(uuid.uuid4())
    lab.sql(db,f"""BEGIN;
    UPDATE customer SET name='Compensation synthetic' WHERE id='{ids['customer']}';
    UPDATE inventory_port SET label='Before one Ω',status='free',color=NULL,face='auto' WHERE id='{ids['pa']}';
    UPDATE inventory_port SET label='Before two 東京',status='disabled',color='#abcdef',face='front' WHERE id='{ids['pa2']}';
    INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order)
    SELECT '{duplicate_group}',systemhaus_id,customer_id,device_id,'rj45','Grupo a','A',1 FROM inventory_port_group WHERE id='{ids['ga']}';
    INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,properties)
    SELECT '{duplicate_port}',systemhaus_id,customer_id,device_id,'{duplicate_group}','rj45',1,0,'same gn other group','free',false,NULL,NULL,'auto','{{}}'::jsonb FROM inventory_port WHERE id='{ids['pa']}';
    COMMIT;""",sensitive=True)
    return ids,password

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True)
    parser.add_argument('--frontend',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--focal-cancel',action='store_true')
    args=parser.parse_args();dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file():raise RuntimeError('Complete explicit artifacts required')
    args.output.mkdir(parents=True,exist_ok=False)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL',
            'inputs':inputs(dll,frontend),'realQaAccessed':False,'productModified':False,'fixtureCreatedBy':'SQL; not GUI creation','focalCancel':args.focal_cancel}
    started=time.monotonic();lab=Lab('compensation67')
    try:
        with lab:
            db=lab.create_database('compensation67');ids,password=fixture(lab,db,dll);lab.grant_runtime(db)
            before=durable(lab,db);server=lab.start_server(db,dll=dll,frontend=frontend)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',
                RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            if args.focal_cancel:env['RACKCLICK_COMPENSATION_FOCAL_CANCEL']='1'
            with (args.output/'browser-windows.log').open('wb') as log:
                done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-inventory-compensation.mjs')],
                    env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=180)
            report['browserExitCode']=done.returncode
            if done.returncode:raise RuntimeError('Browser failed; evidence retained')
            expected=json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'))
            wanted=json.loads(json.dumps(before));after=durable(lab,db)
            expected_ports={p['id']:p for p in expected['ports']}
            for row in wanted['inventory_port']:
                p=expected_ports[row['id']]
                if row['id'] in [ids['pa'],ids['pa2']]:
                    row.update(label=p['label'],poe=p['poe'],type=p['type'])
            for row in wanted['inventory_rack']:
                if row['id']==ids['rackB']:row.update(location=next(r['location'] for r in expected['racks'] if r['id']==ids['rackB']))
            assert canonical(after)==canonical(wanted),'Nine SQL tables exact except committed target labels/PoE and other actor rack location'
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
