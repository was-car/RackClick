"""Isolated Windows/PG/Edge personal favorites; explicit artifacts, no build or real QA."""
import argparse,hashlib,json,platform,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain
from windows_job import run_isolated
from test_inventory_catalog_gui import fixture
from test_inventory_movement_gui import durable,tree,project_by_id
from test_inventory_poe_face_gui import canonical

def inputs(dll,frontend):
    paths=[Path(__file__),Path(__file__).with_name('test_inventory_catalog_gui.py'),Path(__file__).with_name('test_inventory_movement_gui.py'),Path(__file__).with_name('test_inventory_poe_face_gui.py'),Path(__file__).with_name('pg_support.py'),ROOT/'tools/windows/windows_job.py',ROOT/'development/frontend/tests/browser-quince-support.mjs',ROOT/'development/frontend/tests/browser-catalog-favorites.mjs']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'server':tree(dll.parent),'frontend':tree(frontend)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--frontend',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file():raise RuntimeError('Complete explicit artifacts required')
    args.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();lab=Lab('favorites143')
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL','inputs':inputs(dll,frontend),'realQaAccessed':False,'productModified':False,'fixtureCreatedBy':'New synthetic SQL fixture; five favorite commits, one fence and one PDU creation exercised in GUI'}
    try:
        with lab:
            db=lab.create_database('favorites143');ids,password=fixture(lab,db,dll);lab.grant_runtime(db);before=durable(lab,db)
            before_revisions=lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))")
            server=lab.start_server(db,dll=dll,frontend=frontend);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            browser_started=time.monotonic()
            with (args.output/'browser-windows.log').open('wb') as log:done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-catalog-favorites.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=240)
            report.update(browserExitCode=done.returncode,browserSeconds=round(time.monotonic()-browser_started,3))
            if done.returncode:raise RuntimeError('Browser failed; sanitized evidence retained')
            expected=json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'));personal=json.loads((args.output/'expected-favorites.json').read_text(encoding='utf-8'));after=durable(lab,db)
            for table,rows in before.items():
                for row in rows:assert row in after[table],f'Existing {table} row changed'
            for table in ['inventory_connection','inventory_connection_endpoint']:assert canonical({table:before[table]})==canonical({table:after[table]})
            assert len(after['inventory_device'])==len(before['inventory_device'])+1
            assert lab.sql(db,'SELECT count(*) FROM operation')=='1'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='inventory.device.createFromCatalog'")=='1'
            assert lab.sql(db,"SELECT count(*) FROM user_catalog_favorite_operation WHERE state='committed'")=='5'
            assert lab.sql(db,"SELECT count(*) FROM user_catalog_favorite_operation WHERE state='cancelled'")=='1'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='user.catalogFavorite.set'")=='5'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='user.catalogFavorite.set.cancel'")=='1'
            revision_before=json.loads(before_revisions);revision_after=json.loads(lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))"))
            assert revision_after['house']==revision_before['house']
            assert revision_after['customers'][ids['other']]==revision_before['customers'][ids['other']]
            assert revision_after['customers'][ids['customer']]==revision_before['customers'][ids['customer']]+1
            for value in personal.values():
                owner=value['ownerId'];keys=json.loads(lab.sql(db,f"SELECT COALESCE(jsonb_agg(preset_key ORDER BY preset_key COLLATE \"C\"),'[]') FROM user_catalog_favorite WHERE owner_id='{owner}'"));assert keys==value['presetKeys'];assert lab.sql(db,f"SELECT revision FROM user_catalog_favorites WHERE owner_id='{owner}'")==str(value['revision'])
            assert lab.sql(db,f"SELECT count(*) FROM user_catalog_favorites WHERE owner_id='{ids['second']}'")=='0'
            report.update(existingRowsPreserved=True,connectionsExact=True,inventoryCommits=1,favoriteCommits=5,cancellationFences=1,personalRowsMatch=True,customerRevisionOnlyForDeviceCreation=True,systemhausRevisionUnchanged=True)
            server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend)
            for username,key in [('move-admin','admin'),('move-reader','reader')]:
                client=Client(restarted);assert client.login(username,password).status==200
                current=client.request('GET',f"/api/v1/customers/{ids['customer']}/catalog/favorites");assert current.status==200 and current.json()==personal[key]
                assert current.headers.get('etag')==f'"favorites-{personal[key]["revision"]}"'
                project=client.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert project.status==200 and project_by_id(project.json())==project_by_id(expected)
            assert canonical(durable(lab,db))==canonical(after)
            report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,frontend));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
