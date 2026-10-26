"""One focused Edge/PG61 scenario, new synthetic lab, explicit immutable artifacts."""
import argparse,hashlib,json,platform,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain
from windows_job import run_isolated
from test_client_changes_gui import fixture as seed
from test_inventory_movement_gui import durable,project_by_id,tree

def inputs(dll,front):
    files=[Path(__file__),ROOT/'development/frontend/tests/browser-delete-batch.mjs',ROOT/'development/frontend/tests/browser-client-changes-support.mjs',Path(__file__).with_name('test_client_changes_gui.py'),Path(__file__).with_name('test_inventory_movement_gui.py'),Path(__file__).with_name('pg_support.py'),ROOT/'tools/windows/windows_job.py']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'server':tree(dll.parent),'frontend':tree(front)}

def fixture(lab,db,dll):
    ids,password=seed(lab,db,dll)
    for key in ['site','building','room','dose','end','stale','externalCable']:ids[key]=str(uuid.uuid4())
    h,c=ids['house'],ids['customer']
    sql=[f"INSERT INTO inventory_site VALUES('{ids['site']}','{h}','{c}','Sede lote Ω','{{}}');",f"INSERT INTO inventory_building VALUES('{ids['building']}','{h}','{c}','{ids['site']}','Edificio lote Ω','{{}}');",f"INSERT INTO inventory_room VALUES('{ids['room']}','{h}','{c}','{ids['building']}','Sala lote Ω','{{}}');",f"UPDATE inventory_rack SET room_id='{ids['room']}' WHERE id IN ('{ids['rackA']}','{ids['rackB']}');"]
    for key,kind in [('dose','dose'),('end','endDevice'),('stale','endDevice')]:
        sql.append(f"INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,room_id,name,size_u,sort_order,properties) VALUES('{ids[key]}','{h}','{c}','{kind}','{ids['room']}','Sala {key} literal <img> Ω',NULL,0,'{{}}');")
    sql.extend([f"INSERT INTO inventory_connection(id,systemhaus_id,customer_id,note,color,patch,properties) VALUES('{ids['externalCable']}','{h}','{c}','Cable externo a C','#345678','none','{{}}');",f"INSERT INTO inventory_connection_endpoint VALUES('{h}','{c}','{ids['externalCable']}',0,'{ids['pb2']}'),('{h}','{c}','{ids['externalCable']}',1,'{ids['pc2']}');"])
    lab.sql(db,'BEGIN;\n'+'\n'.join(sql)+'\nCOMMIT;',sensitive=True)
    return ids,password

def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();dll=a.dll.resolve(strict=True);front=a.frontend.resolve(strict=True);a.output.mkdir(parents=True,exist_ok=False)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'inputs':inputs(dll,front),'result':'FAIL','realQaAccessed':False,'fixtureCreatedBy':'SQL synthetic users/grants/hierarchy/devices/cables; tested changes HTTP/Edge only'};lab=Lab('delete-batch-gui61');tick=time.monotonic()
    try:
        with lab:
            db=lab.create_database('delete-batch-gui61');ids,password=fixture(lab,db,dll);lab.grant_runtime(db);before=durable(lab,db);server=lab.start_server(db,dll=dll,frontend=front);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(a.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            with (a.output/'browser.log').open('wb') as log:done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-delete-batch.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=300)
            report['browserExitCode']=done.returncode
            if done.returncode:raise RuntimeError('Browser scenario failed; evidence retained')
            expected=json.loads((a.output/'expected-project.json').read_text(encoding='utf-8'));after=durable(lab,db)
            removed={ids[k] for k in ['a','b','dose','end','stale']}
            assert {r['id'] for r in after['inventory_device']}=={ids['c']}
            assert before['inventory_site']==after['inventory_site'] and before['inventory_building']==after['inventory_building'] and before['inventory_room']==after['inventory_room'] and before['inventory_rack']==after['inventory_rack']
            for table,foreign in [('inventory_device','id'),('inventory_port_group','device_id'),('inventory_port','device_id')]:assert after[table]==[r for r in before[table] if r[foreign] not in removed],table
            assert not after['inventory_connection'] and not after['inventory_connection_endpoint']
            server.close();restart=lab.start_server(db,dll=dll,frontend=front);reader=Client(restart);assert reader.login('move-reader',password).status==200;response=reader.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert response.headers['etag']==f'"{expected["revision"]}"';assert project_by_id(response.json())==project_by_id(expected);assert durable(lab,db)==after
            report.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'),exactDeletionOnly=True,externalDeviceAndPortsIntact=True,aspNetRestartPersistence=True)
    except Exception as e:report.update(failureType=type(e).__name__,failure=str(e))
    finally:
        report.update(seconds=round(time.monotonic()-tick,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,front));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (a.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
