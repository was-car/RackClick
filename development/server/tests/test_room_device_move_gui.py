"""Native room move62: synthetic new PG/Edge lab; frozen artifact inputs only."""
import argparse,hashlib,json,platform,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,literal,toolchain
from windows_job import run_isolated
from test_client_changes_gui import fixture as seed
from test_inventory_movement_gui import durable,project_by_id,tree

def inputs(dll,front):
    files=[Path(__file__),ROOT/'development/frontend/tests/browser-room-device-move.mjs',ROOT/'development/frontend/tests/browser-client-changes-support.mjs',Path(__file__).with_name('test_client_changes_gui.py'),Path(__file__).with_name('test_inventory_movement_gui.py'),Path(__file__).with_name('pg_support.py'),ROOT/'tools/windows/windows_job.py']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'server':tree(dll.parent),'frontend':tree(front)}

def fixture(lab,db,dll):
    ids,password=seed(lab,db,dll);h,c=ids['house'],ids['customer']
    for key in ['siteA','siteB','buildingA','buildingB','roomA','roomB','dose','end','gdose','gend','pdose','pdose2','pdose3','pend','roomCable','otherSite','otherBuilding','otherRoom','prior','onlyRoomDevice'] :ids[key]=str(uuid.uuid4())
    sql=[]
    for suffix in ['A','B']:
        sql.extend([f"INSERT INTO inventory_site VALUES('{ids['site'+suffix]}','{h}','{c}','Sede {suffix} literal <img> Ω','{{}}');",f"INSERT INTO inventory_building VALUES('{ids['building'+suffix]}','{h}','{c}','{ids['site'+suffix]}','Edificio {suffix} 東京','{{}}');",f"INSERT INTO inventory_room VALUES('{ids['room'+suffix]}','{h}','{c}','{ids['building'+suffix]}','Sala homónima Ω','{{}}');"])
    sql.extend([f"UPDATE inventory_rack SET room_id='{ids['roomA']}' WHERE customer_id='{c}';",f"DELETE FROM inventory_connection WHERE id='{ids['cable']}';"])
    for order,(key,kind) in enumerate([('dose','dose'),('end','endDevice')]):
        sql.append(f"INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,room_id,name,size_u,sort_order,poe_budget,properties) VALUES('{ids[key]}','{h}','{c}','{kind}','{ids['roomA']}','Objeto {key} literal <img> Ω',NULL,{5+order*3},25,'{{\"notes\":{{\"sn\":\"serial-{key}\",\"text\":\"nota literal 東京\"}}}}');")
        sql.append(f"INSERT INTO inventory_port_group VALUES('{ids['g'+key]}','{h}','{c}','{ids[key]}','rj45','Grupo {key}','{key}',0);")
        for n in range(1,4 if key=='dose' else 2):
            port=ids['p'+key+(str(n) if n>1 else '')]
            sql.append(f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,power_role,properties) VALUES('{port}','{h}','{c}','{ids[key]}','{ids['g'+key]}','rj45',{n},{n-1},'Puerto {key}{n} Ω','free',true,17.5,'#654321','rear','unspecified','{{\"sentinel\":\"port-{key}{n}\"}}');")
    for key,left,right in [('cable','pa','pdose'),('roomCable','pdose2','pend')]:
        sql.extend([f"INSERT INTO inventory_connection(id,systemhaus_id,customer_id,note,color,patch,properties) VALUES('{ids[key]}','{h}','{c}','Cable {key} literal Ω','#123456','tested','{{}}');",f"INSERT INTO inventory_connection_endpoint VALUES('{h}','{c}','{ids[key]}',0,'{ids[left]}'),('{h}','{c}','{ids[key]}',1,'{ids[right]}');"])
    sql.extend([f"INSERT INTO inventory_site VALUES('{ids['otherSite']}','{h}','{ids['other']}','Otro sitio','{{}}');",f"INSERT INTO inventory_building VALUES('{ids['otherBuilding']}','{h}','{ids['other']}','{ids['otherSite']}','Otro edificio','{{}}');",f"INSERT INTO inventory_room VALUES('{ids['otherRoom']}','{h}','{ids['other']}','{ids['otherBuilding']}','Sala homónima Ω','{{}}');"])
    sql.append(f"INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,room_id,name,sort_order,properties) VALUES('{ids['prior']}','{h}','{c}','endDevice','{ids['roomB']}','Objeto ya en destino',3,'{{}}'),('{ids['onlyRoomDevice']}','{h}','{ids['other']}','dose','{ids['otherRoom']}','Sin otro destino',0,'{{}}');")
    lab.sql(db,'BEGIN;\n'+'\n'.join(sql)+'\nCOMMIT;',sensitive=True)
    return ids,password

def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();dll=a.dll.resolve(strict=True);front=a.frontend.resolve(strict=True);a.output.mkdir(parents=True,exist_ok=False)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'inputs':inputs(dll,front),'result':'FAIL','realQaAccessed':False,'fixtureCreatedBy':'SQL synthetic inventory/accounts; tested moves GUI only'};lab=Lab('room-move-gui62');tick=time.monotonic()
    try:
        with lab:
            db=lab.create_database('room-move-gui62');ids,password=fixture(lab,db,dll);lab.grant_runtime(db);before=durable(lab,db);server=lab.start_server(db,dll=dll,frontend=front);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(a.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            with (a.output/'browser.log').open('wb') as log:done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-room-device-move.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=240)
            report['browserExitCode']=done.returncode
            if done.returncode:raise RuntimeError('Browser scenario failed; evidence retained')
            expected=json.loads((a.output/'expected-project.json').read_text(encoding='utf-8'));after=durable(lab,db);wanted=json.loads(json.dumps(before))
            for row in wanted['inventory_device']:
                if row['id'] in [ids['dose'],ids['end']]:row.update(room_id=ids['roomB'],sort_order=4 if row['id']==ids['dose'] else 5)
            canonical=lambda data:{k:sorted(json.dumps(r,sort_keys=True) for r in rows) for k,rows in data.items()}
            assert canonical(after)==canonical(wanted),'Only room_id and destination max+1 sort_order changed across nine tables'
            report['sqlOnlyRoomIdAndDocumentaryOrderChanged']=True
            admin=Client(server);assert admin.login('move-admin',password).status==200
            route=f"/api/v1/customers/{ids['customer']}/commands"
            def move(client,payload):return client.request('POST',route,{'type':'device.move','payload':payload},{'If-Match':f'"{expected["revision"]}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':client.request('GET','/api/v1/me').json()['user']['id']})
            negatives={}
            for user in ['move-reader','notice-outsider']:
                client=Client(server);assert client.login(user,password).status==200
                response=move(client,{'id':ids['dose'],'roomId':ids['roomA']});assert response.status==(403 if user=='move-reader' else 404);negatives[user]=response.status
            for name,payload,status in [('foreignRoom',{'id':ids['dose'],'roomId':ids['otherRoom']},404),('missingRoom',{'id':ids['dose'],'roomId':str(uuid.uuid4())},404),('invalidUUID',{'id':ids['dose'],'roomId':'invalid'},422),('roomToRack',{'id':ids['dose'],'rackId':ids['rackA']},422),('roomWithU',{'id':ids['end'],'roomId':ids['roomA'],'sizeU':1},422)]:
                response=move(admin,payload);assert response.status==status,(name,response.status);negatives[name]=status
            assert canonical(durable(lab,db))==canonical(after),'Rejected moves leave all nine tables intact'
            server.close();restart=lab.start_server(db,dll=dll,frontend=front);reader=Client(restart);assert reader.login('move-reader',password).status==200;response=reader.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert response.headers['etag']==f'"{expected["revision"]}"';assert project_by_id(response.json())==project_by_id(expected);assert canonical(durable(lab,db))==canonical(after)
            report.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'),negativeStatuses=negatives,aspNetRestartPersistence=True,sqlRowCounts={k:len(v) for k,v in after.items()},sqlBeforeSha256=hashlib.sha256(json.dumps(canonical(before),sort_keys=True).encode()).hexdigest(),sqlAfterSha256=hashlib.sha256(json.dumps(canonical(after),sort_keys=True).encode()).hexdigest())
    except Exception as e:report.update(failureType=type(e).__name__,failure=str(e))
    finally:
        report.update(seconds=round(time.monotonic()-tick,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,front));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (a.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
