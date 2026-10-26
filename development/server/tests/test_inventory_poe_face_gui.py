"""Focused OFF/face GUI path on new native PostgreSQL, explicit immutable artifacts.

SQL preparation is not claimed as GUI creation. Never uses existing QA labs.
"""
import argparse,hashlib,json,platform,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'))
sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain
from windows_job import run_isolated
from test_inventory_movement_gui import fixture as seed52,durable,tree,project_by_id

def canonical(value):
    return {key:sorted(json.dumps(row,sort_keys=True,ensure_ascii=False) for row in rows) for key,rows in value.items()}

def inputs(dll,frontend):
    paths=[Path(__file__),Path(__file__).with_name('test_inventory_movement_gui.py'),
           Path(__file__).with_name('pg_support.py'),ROOT/'tools/windows/windows_job.py',
           ROOT/'development/frontend/tests/browser-inventory-poe-face.mjs']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            'server':tree(dll.parent),'frontend':tree(frontend)}

def atomic_state(lab,db):
    value=durable(lab,db)
    for table in ['customer','operation','audit_event']:
        value[table]=json.loads(lab.sql(db,f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM {table} t"))
    return canonical(value)

def fixture(lab,db,dll):
    ids,password=seed52(lab,db,dll)
    lab.sql(db,f"""BEGIN;
    UPDATE customer SET name='PoE face QA synthetic' WHERE id='{ids['customer']}';
    UPDATE inventory_rack SET name='Rack PoE y caras' WHERE id='{ids['rackA']}';
    UPDATE inventory_device SET name='Equipo PoE objetivo' WHERE id='{ids['a']}';
    UPDATE inventory_device SET name='Equipo extremo B' WHERE id='{ids['b']}';
    UPDATE inventory_port SET type='rj45_poe',poe=true,watts=17.5,face='front',label='Objetivo PoE Ω' WHERE id='{ids['pa']}';
    COMMIT;""",sensitive=True)
    return ids,password

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True)
    parser.add_argument('--frontend',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file():raise RuntimeError('Explicit complete artifacts required')
    args.output.mkdir(parents=True,exist_ok=False)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL',
            'inputs':inputs(dll,frontend),'realQaAccessed':False,'productModified':False,
            'fixtureCreatedBy':'SQL; not GUI creation'}
    started=time.monotonic();lab=Lab('inventory-poe-face54')
    try:
        with lab:
            db=lab.create_database('poe-face54');ids,password=fixture(lab,db,dll);lab.grant_runtime(db)
            before=durable(lab,db);server=lab.start_server(db,dll=dll,frontend=frontend)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',
                RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            tick=time.monotonic()
            with (args.output/'browser-windows.log').open('wb') as log:
                done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-inventory-poe-face.mjs')],
                    env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=150)
            report.update(browserExitCode=done.returncode,browserSeconds=round(time.monotonic()-tick,3))
            if done.returncode:raise RuntimeError('Browser failed; sanitized evidence retained')
            expected=json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'))
            wanted=json.loads(json.dumps(before));after=durable(lab,db)
            for row in wanted['inventory_port']:
                if row['id']==ids['pa']:row.update(poe=False,type='rj45',face='rear')
            assert canonical(after)==canonical(wanted),'All nine SQL tables exact except target poe/type/face'
            report.update(sqlExactTargetOnly=True,sqlTableRowCounts={k:len(v) for k,v in after.items()})
            admin=Client(server);assert admin.login('move-admin',password).status==200
            actor=lab.sql(db,"SELECT id FROM app_user WHERE username='move-admin'")
            payload={'deviceId':ids['a'],'groupId':ids['ga'],'groupType':'rj45','portIds':[ids['pa']],'changes':{'face':'front'}}
            def command(data,client=admin,user=actor,customer=ids['customer'],revision=expected['revision']):
                return client.request('POST',f'/api/v1/customers/{customer}/commands',{'type':'ports.update','payload':data},
                    {'If-Match':f'"{revision}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':user})
            report['atomicNegatives']=[]
            for name,data,error in [
                    ('mixed group after valid first port',dict(payload,portIds=[ids['pa'],ids['pb']]),'port_scope_invalid'),
                    ('invalid face',dict(payload,changes={'face':'side'}),'port_face_invalid')]:
                state=atomic_state(lab,db);response=command(data)
                assert response.status==422 and response.json()['error']==error,'Expected coherent port rejection '+name
                assert atomic_state(lab,db)==state,'Rejected update rolls back every row/revision/operation/audit'
                report['atomicNegatives'].append({'condition':name,'http':422,'error':error,'unchanged':True})
            report['permissionChecks']=[]
            for name,key in [('move-reader','reader'),('move-technician','technician')]:
                client=Client(server);assert client.login(name,password).status==200
                state=atomic_state(lab,db);response=command(payload,client,ids[key])
                assert response.status==403 and atomic_state(lab,db)==state,'Reader/outside edit scope denied without mutation'
                assert client.request('GET',f"/api/v1/customers/{ids['other']}/project").status==404
                report['permissionChecks'].append({'user':name,'write':403,'outsideRead':404,'unchanged':True})
            state=atomic_state(lab,db)
            other=admin.request('GET',f"/api/v1/customers/{ids['other']}/project").json()
            response=command(payload,customer=ids['other'],revision=other['revision'])
            assert response.status==404 and atomic_state(lab,db)==state,'No cross-customer device/port lookup or write'
            report['crossCustomerUpdate']={'http':404,'unchanged':True}
            server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend)
            read=Client(restarted);assert read.login('move-admin',password).status==200
            persisted=read.request('GET',f"/api/v1/customers/{ids['customer']}/project")
            assert persisted.status==200 and persisted.headers['etag']==f'"{expected["revision"]}"'
            assert project_by_id(persisted.json())==project_by_id(expected),'Restart exact project including OFF/watts/rear'
            assert canonical(durable(lab,db))==canonical(after),'Restart exact nine SQL tables'
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
