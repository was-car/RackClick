"""Inventory read views in one NEW Windows/PG cluster; explicit frozen artifacts only."""
import argparse,hashlib,json,platform,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'))
sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain
from windows_job import run_isolated
from test_inventory_compensation_gui import fixture as seed
from test_inventory_movement_gui import durable,tree,project_by_id
from test_inventory_poe_face_gui import canonical

def inputs(dll,frontend):
    paths=[Path(__file__),Path(__file__).with_name('test_inventory_compensation_gui.py'),Path(__file__).with_name('test_inventory_movement_gui.py'),Path(__file__).with_name('pg_support.py'),ROOT/'tools/windows/windows_job.py',ROOT/'development/frontend/tests/browser-quince-support.mjs',ROOT/'development/frontend/tests/browser-inventory-read-views.mjs']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'server':tree(dll.parent),'frontend':tree(frontend)}

def fixture(lab,db,dll):
    ids,password=seed(lab,db,dll)
    for k in ['site','building','roomA','roomB','dose','end','doseGroup','endGroup','dosePort','endPort','roomCable']:ids[k]=str(uuid.uuid4())
    q=[f"UPDATE inventory_rack SET name='Homónimo Ω <img>' WHERE customer_id='{ids['customer']}';",
       f"INSERT INTO inventory_site(id,systemhaus_id,customer_id,name) SELECT '{ids['site']}',systemhaus_id,id,'Sitio 東京' FROM customer WHERE id='{ids['customer']}';",
       f"INSERT INTO inventory_building(id,systemhaus_id,customer_id,site_id,name) SELECT '{ids['building']}',systemhaus_id,id,'{ids['site']}','Edificio Ω' FROM customer WHERE id='{ids['customer']}';"]
    for room in ['roomA','roomB']:
        q.append(f"INSERT INTO inventory_room(id,systemhaus_id,customer_id,building_id,name) SELECT '{ids[room]}',systemhaus_id,id,'{ids['building']}','Sala homónima 東京' FROM customer WHERE id='{ids['customer']}';")
    q.append(f"UPDATE inventory_rack SET room_id='{ids['roomA']}' WHERE customer_id='{ids['customer']}';")
    for key,kind in [('dose','dose'),('end','endDevice')]:
        q.append(f"INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,room_id,name,sort_order) SELECT '{ids[key]}',systemhaus_id,id,'{kind}','{ids['roomA']}','Objeto homónimo Ω',0 FROM customer WHERE id='{ids['customer']}';")
        q.append(f"INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order) SELECT '{ids[key+'Group']}',systemhaus_id,id,'{ids[key]}','rj45','Grupo Ω','',0 FROM customer WHERE id='{ids['customer']}';")
        q.append(f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,face) SELECT '{ids[key+'Port']}',systemhaus_id,id,'{ids[key]}','{ids[key+'Group']}','rj45',1,0,'Puerto 東京','free',false,'auto' FROM customer WHERE id='{ids['customer']}';")
    for n in range(3,66):
        q.append(f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,properties) SELECT '{uuid.uuid4()}',systemhaus_id,customer_id,device_id,group_id,type,{n},{n-1},'Paginado Ω {n}','free',false,NULL,NULL,'auto','{{}}'::jsonb FROM inventory_port WHERE id='{ids['pa']}';")
    # Existing cable becomes cross-rack; room endpoints form a separate cable without a circuit claim.
    q.append(f"UPDATE inventory_connection_endpoint SET port_id='{ids['pc']}' WHERE connection_id='{ids['cable']}' AND port_id='{ids['pb']}';")
    q.append(f"INSERT INTO inventory_connection(id,systemhaus_id,customer_id,note,color,patch) SELECT '{ids['roomCable']}',systemhaus_id,id,'Room literal <img> Ω',NULL,'none' FROM customer WHERE id='{ids['customer']}';")
    for order,key in enumerate(['dosePort','endPort']):
        q.append(f"INSERT INTO inventory_connection_endpoint SELECT systemhaus_id,id,'{ids['roomCable']}',{order},'{ids[key]}' FROM customer WHERE id='{ids['customer']}';")
    lab.sql(db,'BEGIN;\n'+'\n'.join(q)+'\nCOMMIT;',sensitive=True)
    return ids,password

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--frontend',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file():raise RuntimeError('Complete explicit artifacts required')
    args.output.mkdir(parents=True,exist_ok=False)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL','inputs':inputs(dll,frontend),'realQaAccessed':False,'fixtureCreatedBy':'SQL; no production data'}
    started=time.monotonic();lab=Lab('readviews83')
    try:
        with lab:
            db=lab.create_database('readviews83');ids,password=fixture(lab,db,dll);lab.grant_runtime(db);before=durable(lab,db)
            server=lab.start_server(db,dll=dll,frontend=frontend)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            with (args.output/'browser-windows.log').open('wb') as log:
                done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-inventory-read-views.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=180)
            report['browserExitCode']=done.returncode
            if done.returncode:raise RuntimeError('Browser failed; evidence retained')
            expected=json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'))
            wanted=json.loads(json.dumps(before));after=durable(lab,db)
            for row in wanted['inventory_device']:
                if row['id']==ids['dose']:row.update(name='Renombrado 東京 <img>',room_id=ids['roomB'])
            assert canonical(after)==canonical(wanted),'Nine SQL tables exact except explicit other actor rename/move'
            report['sqlNineTablesExact']=True
            reader=Client(server);assert reader.login('move-reader',password).status==200
            for view in ['search','ports','connections']:
                assert reader.request('GET',f"/api/v1/customers/{ids['other']}/inventory/{view}",headers={'If-Match':'"1"'}).status==404
            report['outsideScopeAllViews']=404
            server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend);admin=Client(restarted);assert admin.login('move-admin',password).status==200
            response=admin.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert response.status==200 and project_by_id(response.json())==project_by_id(expected)
            assert canonical(durable(lab,db))==canonical(after)
            report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,frontend));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
