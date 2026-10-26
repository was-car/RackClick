"""Five separate GUI blocks, explicit immutable artifacts, new Windows PostgreSQL labs only."""
import argparse,hashlib,json,platform,secrets,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,literal,toolchain
from windows_job import run_isolated
from test_inventory_movement_gui import fixture as seed,durable,project_by_id,tree
CASES={'55':'browser-admin-context55.mjs','56':'browser-admin-membership56.mjs','57':'browser-connections-batch57.mjs','58':'browser-connections-edit58.mjs','59':'browser-hierarchy-edit59.mjs'}

def inputs(dll,frontend):
    sources=[Path(__file__),ROOT/'development/frontend/tests/browser-quince-support.mjs',*[ROOT/'development/frontend/tests'/name for name in CASES.values()]]
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'server':tree(dll.parent),'frontend':tree(frontend)}

def fixture(lab,db,dll):
    ids,password=seed(lab,db,dll);house,admin=lab.sql(db,"SELECT id FROM systemhaus;SELECT id FROM app_user WHERE username='move-admin'").splitlines();ids.update(house=house,admin=admin)
    ids.update({k:str(uuid.uuid4()) for k in ['userA','userB','memberGroup','siteA','siteB','buildingA','buildingB','roomA','roomB']})
    sql=[f"INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{ids[k]}',systemhaus_id,{literal('Cuenta '+k+' <img> Ω')},password_hash FROM app_user WHERE id='{admin}';" for k in ['userA','userB']]
    sql+=[f"INSERT INTO user_group VALUES('{ids['memberGroup']}','{house}','Grupo de membresía <img> Ω');",f"UPDATE inventory_port SET status='reserved' WHERE id='{ids['pc']}';"]
    for key in ['A','B']:
        sql += [f"INSERT INTO inventory_site(id,systemhaus_id,customer_id,name,properties) VALUES('{ids['site'+key]}','{house}','{ids['customer']}','Sede {key}','{{}}');",f"INSERT INTO inventory_building(id,systemhaus_id,customer_id,site_id,name,properties) VALUES('{ids['building'+key]}','{house}','{ids['customer']}','{ids['site'+key]}','Edificio {key}','{{}}');",f"INSERT INTO inventory_room(id,systemhaus_id,customer_id,building_id,name,properties) VALUES('{ids['room'+key]}','{house}','{ids['customer']}','{ids['building'+key]}','Sala {key}','{{}}');"]
    lab.sql(db,'BEGIN;\n'+'\n'.join(sql)+'\nCOMMIT;',sensitive=True)
    return ids,password

def state(lab,db):
    return {t:lab.sql(db,f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM {t} t") for t in ['customer','operation','audit_event',*durable(lab,db)]}

def main():
    p=argparse.ArgumentParser();p.add_argument('--case',choices=CASES,required=True);p.add_argument('--dll',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();dll=a.dll.resolve(strict=True);front=a.frontend.resolve(strict=True);a.output.mkdir(parents=True,exist_ok=False)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'case':a.case,'inputs':inputs(dll,front),'result':'FAIL','realQaAccessed':False,'fixtureCreatedBy':'SQL; not GUI inventory creation'};lab=Lab('frontend'+a.case);tick=time.monotonic()
    try:
        with lab:
            db=lab.create_database('frontend'+a.case);ids,password=fixture(lab,db,dll);lab.grant_runtime(db);before=durable(lab,db);server=lab.start_server(db,dll=dll,frontend=front);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(a.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            with (a.output/'browser.log').open('wb') as log:r=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests'/CASES[a.case])],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=180)
            report['browserExitCode']=r.returncode
            if r.returncode:raise RuntimeError('Browser scenario failed; evidence retained')
            after=durable(lab,db)
            if a.case in ['55','56']:assert before==after,'Administration changed inventory';report['inventoryUnchanged']=True
            if a.case=='56':assert lab.sql(db,f"SELECT count(*) FROM user_group_member WHERE group_id='{ids['memberGroup']}' AND user_id='{ids['userB']}'")=='1';assert lab.sql(db,f"SELECT count(*) FROM user_group_member WHERE group_id='{ids['memberGroup']}' AND user_id='{ids['userA']}'")=='0';report['membershipCorrectTargetOnly']=True
            admin=Client(server);assert admin.login('move-admin',password).status==200
            if a.case in ['57','58','59']:
                expected=json.loads((a.output/'expected-project.json').read_text(encoding='utf-8'));response=admin.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert project_by_id(response.json())==project_by_id(expected)
                actor=ids['admin'];headers={'If-Match':f'"{expected["revision"]}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor};baseline=state(lab,db)
                if a.case=='57':
                    assert len(after['inventory_connection'])==3 and len(after['inventory_connection_endpoint'])==6
                    for table in before:
                        if table not in ['inventory_connection','inventory_connection_endpoint']:assert before[table]==after[table],table
                    payload={'type':'connections.createBatch','payload':{'pairs':[{'fromPortId':ids['pa2'],'toPortId':ids['pb2']},{'fromPortId':ids['pc'],'toPortId':ids['pc2']}]}}
                elif a.case=='58':
                    for table in before:
                        if table not in ['inventory_connection','inventory_connection_endpoint']:assert before[table]==after[table],table
                    payload={'type':'connections.createBatch','payload':{'pairs':[{'fromPortId':ids['pa'],'toPortId':ids['pb'],'patch':'invalid'}]}}
                else:
                    for table in before:
                        if table not in ['inventory_site','inventory_building','inventory_room','inventory_rack']:assert before[table]==after[table],table
                    payload={'type':'site.delete','payload':{'id':ids['siteB']}}
                rejected=admin.request('POST',f"/api/v1/customers/{ids['customer']}/commands",payload,headers);assert rejected.status in [409,422];assert state(lab,db)==baseline,'Rejected transaction mutated inventory/revision/operation/audit';report['atomicNegative']={'http':rejected.status,'error':rejected.json()['error'],'allPublicRowsUnchanged':True}
                server.close();restart=lab.start_server(db,dll=dll,frontend=front);reader=Client(restart);assert reader.login('move-admin',password).status==200;response=reader.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert project_by_id(response.json())==project_by_id(expected);assert durable(lab,db)==after;report['aspNetRestartPersistence']=True
            report.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'))
    except Exception as e:report.update(failureType=type(e).__name__,failure=str(e))
    finally:
        report.update(seconds=round(time.monotonic()-tick,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,front));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (a.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
