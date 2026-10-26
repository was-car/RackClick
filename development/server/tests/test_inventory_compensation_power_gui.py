"""One new Windows/PG/Edge six-field undo scenario; no builds or real QA."""
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
    paths=[Path(__file__),Path(__file__).with_name('test_inventory_movement_gui.py'),Path(__file__).with_name('test_inventory_poe_face_gui.py'),Path(__file__).with_name('pg_support.py'),ROOT/'tools/windows/windows_job.py',ROOT/'development/frontend/tests/browser-quince-support.mjs',ROOT/'development/frontend/tests/browser-inventory-compensation-power.mjs',ROOT/'development/frontend/tests/inventory-compensation-power.test.mjs',ROOT/'development/frontend/src/inventory-compensation.ts',ROOT/'development/frontend/src/inventory-words.ts']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'server':tree(dll.parent),'frontend':tree(frontend)}

def fixture(lab,db,dll):
    ids,password=seed(lab,db,dll);ids.update({k:str(uuid.uuid4()) for k in ['pa3','duplicateGroup','duplicatePort']})
    lab.sql(db,f"""BEGIN;
    UPDATE inventory_port SET type='rj45',poe=true,watts=NULL,label='Legacy true Ω',color=NULL,face='front' WHERE id='{ids['pa']}';
    UPDATE inventory_port SET type='rj45_poe',poe=false,watts=0,label='Legacy false 東京',color='#abcdef',face='front' WHERE id='{ids['pa2']}';
    INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,power_role,properties)
    SELECT '{ids['pa3']}',systemhaus_id,customer_id,device_id,group_id,'rj45_poe',3,2,'Decimal original 12.75','free',true,12.75,'#aabbcc','front','unspecified','{{"sentinel":"power-third"}}'::jsonb FROM inventory_port WHERE id='{ids['pa']}';
    INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order)
    SELECT '{ids['duplicateGroup']}',systemhaus_id,customer_id,device_id,'rj45','Same gn another group','A',1 FROM inventory_port_group WHERE id='{ids['ga']}';
    INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,power_role,properties)
    SELECT '{ids['duplicatePort']}',systemhaus_id,customer_id,device_id,'{ids['duplicateGroup']}','rj45',1,0,'Other group gn1','free',false,90,NULL,'front','unspecified','{{"sentinel":"other-group"}}'::jsonb FROM inventory_port WHERE id='{ids['pa']}';
    COMMIT;""",sensitive=True)
    return ids,password

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--frontend',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file():raise RuntimeError('Complete explicit artifacts required')
    args.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();lab=Lab('compensation-power185')
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL','inputs':inputs(dll,frontend),'realQaAccessed':False,'productModified':False,'fixtureCreatedBy':'New synthetic SQL seed: three heterogeneous target ports and duplicate gn in another group; planned GUI normalization/PoE/watts inverses plus explicit remote fence'}
    try:
        with lab:
            db=lab.create_database('power185');ids,password=fixture(lab,db,dll);lab.grant_runtime(db);before=durable(lab,db)
            before_revisions=json.loads(lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))"))
            server=lab.start_server(db,dll=dll,frontend=frontend);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            browser_started=time.monotonic()
            with (args.output/'browser-windows.log').open('wb') as log:done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-inventory-compensation-power.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=180)
            report.update(browserExitCode=done.returncode,browserSeconds=round(time.monotonic()-browser_started,3))
            if done.returncode:raise RuntimeError('Browser failed; sanitized evidence retained')
            expected=json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'));after=durable(lab,db);wanted=json.loads(json.dumps(before))
            for row in wanted['inventory_port']:
                if row['id'] in [ids['pa'],ids['pa2'],ids['pa3']]:row['watts']=0
            for row in wanted['inventory_rack']:
                if row['id']==ids['rackB']:row['location']='Power compensation remote fence'
            assert canonical(after)==canonical(wanted),'All nine SQL inventory tables exact except last deliberate watts0 and explicit other actor rack location'
            for table in ['inventory_connection','inventory_connection_endpoint','inventory_port_group']:assert canonical({table:before[table]})==canonical({table:after[table]})
            assert lab.sql(db,'SELECT count(*) FROM operation')=='10'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='inventory.operations.compensate'")=='4'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='inventory.ports.update'")=='5'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='inventory.rack.update'")=='1'
            after_revisions=json.loads(lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))"))
            assert after_revisions['house']==before_revisions['house'] and after_revisions['customers'][ids['other']]==before_revisions['customers'][ids['other']]
            assert after_revisions['customers'][ids['customer']]==before_revisions['customers'][ids['customer']]+10
            for row in before['inventory_port']:
                if row['id'] in [ids['pa'],ids['pa2'],ids['pa3']]:assert next(p for p in after['inventory_port'] if p['id']==row['id'])['type']==row['type']
            report.update(sqlExactChangesOnly=True,literalLegacyAliasesRestored=True,nullableZeroDecimalRestored=True,groupsConnectionsEndpointsExact=True,compensationCommits=4,portsUpdateCommits=5,otherActorFenceCommits=1,operationRows=10,replaysNotDuplicated=True,staleInverseNoWrite=True,systemhausAndOtherCustomerRevisionsUnchanged=True)
            server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend);admin=Client(restarted);assert admin.login('move-admin',password).status==200
            current=admin.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert current.status==200 and current.headers.get('etag')==f'"{expected["revision"]}"' and project_by_id(current.json())==project_by_id(expected)
            assert canonical(durable(lab,db))==canonical(after);report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,frontend));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
