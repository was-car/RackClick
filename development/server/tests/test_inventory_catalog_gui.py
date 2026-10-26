"""One isolated Windows/PG/Edge RC9 catalogue scenario; explicit artifacts, no build or real QA."""
import argparse,hashlib,json,platform,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain
from windows_job import run_isolated
from test_inventory_movement_gui import fixture as seed,durable,tree,project_by_id
from test_inventory_poe_face_gui import canonical

def inputs(dll,frontend):
    paths=[Path(__file__),Path(__file__).with_name('test_inventory_movement_gui.py'),Path(__file__).with_name('test_inventory_poe_face_gui.py'),Path(__file__).with_name('pg_support.py'),ROOT/'tools/windows/windows_job.py',ROOT/'development/frontend/tests/browser-quince-support.mjs',ROOT/'development/frontend/tests/browser-inventory-catalog.mjs',ROOT/'development/catalog/rc9-catalog.json']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'server':tree(dll.parent),'frontend':tree(frontend)}

def fixture(lab,db,dll):
    ids,password=seed(lab,db,dll)
    ids.update({key:str(uuid.uuid4()) for key in ['site','building','roomA','roomB']})
    q=[f"UPDATE customer SET name='Catalogue QA synthetic' WHERE id='{ids['customer']}';",f"INSERT INTO inventory_site(id,systemhaus_id,customer_id,name) SELECT '{ids['site']}',systemhaus_id,id,'Sitio catálogo Ω' FROM customer WHERE id='{ids['customer']}';",f"INSERT INTO inventory_building(id,systemhaus_id,customer_id,site_id,name) SELECT '{ids['building']}',systemhaus_id,id,'{ids['site']}','Edificio catálogo' FROM customer WHERE id='{ids['customer']}';"]
    for key in ['roomA','roomB']:q.append(f"INSERT INTO inventory_room(id,systemhaus_id,customer_id,building_id,name) SELECT '{ids[key]}',systemhaus_id,id,'{ids['building']}','Sala catálogo {key}' FROM customer WHERE id='{ids['customer']}';")
    q.append(f"UPDATE inventory_rack SET room_id='{ids['roomA']}' WHERE customer_id='{ids['customer']}';")
    lab.sql(db,'BEGIN;\n'+'\n'.join(q)+'\nCOMMIT;',sensitive=True)
    return ids,password

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--frontend',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file():raise RuntimeError('Complete explicit artifacts required')
    args.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();lab=Lab('catalog128')
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL','inputs':inputs(dll,frontend),'realQaAccessed':False,'productModified':False,'fixtureCreatedBy':'SQL; seven creations under test are GUI, six catalogue and one manual'}
    try:
        with lab:
            db=lab.create_database('catalog128');ids,password=fixture(lab,db,dll);lab.grant_runtime(db);before=durable(lab,db);server=lab.start_server(db,dll=dll,frontend=frontend)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            browser_started=time.monotonic()
            with (args.output/'browser-windows.log').open('wb') as log:done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-inventory-catalog.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=240)
            report.update(browserExitCode=done.returncode,browserSeconds=round(time.monotonic()-browser_started,3))
            if done.returncode:raise RuntimeError('Browser failed; sanitized evidence retained')
            expected=json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'));after=durable(lab,db)
            for table,rows in before.items():
                for row in rows:
                    wanted=dict(row)
                    if table=='inventory_rack' and row['id']==ids['rackB']:wanted['location']='Concurrent catalogue fixture'
                    assert wanted in after[table],f'Existing {table} row changed beyond explicit second actor rack location'
            assert canonical({'connections':after['inventory_connection'],'endpoints':after['inventory_connection_endpoint']})==canonical({'connections':before['inventory_connection'],'endpoints':before['inventory_connection_endpoint']})
            assert len(after['inventory_device'])==len(before['inventory_device'])+7
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='inventory.device.createFromCatalog'")=='6'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='inventory.device.create'")=='1'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='inventory.rack.update'")=='2'
            assert lab.sql(db,'SELECT count(*) FROM operation')=='9'
            report.update(existingRowsPreserved=True,connectionsExact=True,catalogueCommits=6,manualCommits=1,otherActorCommits=2,operationRows=9,lostResponseNoDuplicate=True,initialCatalog412Recovered=True)
            server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend);admin=Client(restarted);assert admin.login('move-admin',password).status==200
            actual=admin.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert actual.status==200 and project_by_id(actual.json())==project_by_id(expected);assert canonical(durable(lab,db))==canonical(after)
            report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,frontend));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
