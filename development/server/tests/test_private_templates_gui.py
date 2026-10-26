"""One isolated Windows/PG/Edge private-template flow. No builds or real QA."""
import argparse,hashlib,json,platform,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain,literal
from windows_job import run_isolated
from test_inventory_catalog_gui import fixture as seed
from test_inventory_movement_gui import durable,tree,project_by_id
from test_inventory_poe_face_gui import canonical

def inputs(dll,frontend):
    paths=[Path(__file__),Path(__file__).with_name('test_inventory_catalog_gui.py'),Path(__file__).with_name('test_inventory_movement_gui.py'),Path(__file__).with_name('test_inventory_poe_face_gui.py'),Path(__file__).with_name('pg_support.py'),ROOT/'tools/windows/windows_job.py',ROOT/'development/frontend/tests/browser-quince-support.mjs',ROOT/'development/frontend/tests/browser-private-templates.mjs']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'server':tree(dll.parent),'frontend':tree(frontend)}

def fixture(lab,db,dll):
    ids,password=seed(lab,db,dll);ids.update({k:str(uuid.uuid4()) for k in ['powerGroup','powerIn','powerOut']})
    q=[f"UPDATE inventory_device SET properties=properties||'{json.dumps({'preset':'NAS storage','icon':'▤','notes':{'sn':'synthetic source serial','ip':'192.0.2.73','model':'Synthetic source model','firmware':'source firmware','text':'Source notes must never propagate'}})}'::jsonb WHERE id='{ids['a']}';",f"UPDATE inventory_port SET face='auto' WHERE id='{ids['pa2']}';",f"INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order) SELECT '{ids['powerGroup']}',systemhaus_id,customer_id,id,'power','Alimentación Ω','AC',1 FROM inventory_device WHERE id='{ids['a']}';"]
    for index,key,role in [(0,'powerIn','inlet'),(1,'powerOut','outlet')]:q.append(f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,power_role,properties) SELECT '{ids[key]}',systemhaus_id,customer_id,id,'{ids['powerGroup']}','power',{index+1},{index},{literal('AC '+role)},'reserved',false,90,'#aabbcc','rear','{role}','{{\"mustNotCopy\":true}}'::jsonb FROM inventory_device WHERE id='{ids['a']}';")
    lab.sql(db,'BEGIN;\n'+'\n'.join(q)+'\nCOMMIT;',sensitive=True);return ids,password

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--frontend',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file():raise RuntimeError('Complete explicit artifacts required')
    args.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();lab=Lab('templates173')
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL','inputs':inputs(dll,frontend),'realQaAccessed':False,'productModified':False,'fixtureCreatedBy':'New synthetic SQL fixture; GUI captures2/retires2/fences1/creates1 plus explicit concurrent rack update1'}
    try:
        with lab:
            db=lab.create_database('templates173');ids,password=fixture(lab,db,dll);lab.grant_runtime(db);before=durable(lab,db)
            before_revisions=json.loads(lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))"))
            server=lab.start_server(db,dll=dll,frontend=frontend);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            browser_started=time.monotonic()
            with (args.output/'browser-windows.log').open('wb') as log:done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-private-templates.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=240)
            report.update(browserExitCode=done.returncode,browserSeconds=round(time.monotonic()-browser_started,3))
            if done.returncode:raise RuntimeError('Browser failed; sanitized evidence retained')
            expected=json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'));personal=json.loads((args.output/'expected-templates.json').read_text(encoding='utf-8'));after=durable(lab,db)
            for table,rows in before.items():
                for row in rows:
                    wanted=dict(row)
                    if table=='inventory_rack' and row['id']==ids['rackB']:wanted['location']='Private template concurrent fixture'
                    assert wanted in after[table],f'Existing {table} row changed beyond explicit concurrent rack location'
            for table in ['inventory_connection','inventory_connection_endpoint']:assert canonical({table:before[table]})==canonical({table:after[table]})
            assert len(after['inventory_device'])==len(before['inventory_device'])+1
            assert lab.sql(db,'SELECT count(*) FROM operation')=='2'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='inventory.device.createFromPrivateTemplate'")=='1'
            assert lab.sql(db,"SELECT count(*) FROM user_device_template_operation WHERE state='committed'")=='4'
            assert lab.sql(db,"SELECT count(*) FROM user_device_template_operation WHERE state='cancelled'")=='1'
            assert lab.sql(db,'SELECT count(*) FROM user_device_template')=='2'
            assert lab.sql(db,'SELECT count(*) FROM user_device_template WHERE active')=='0'
            revision_after=json.loads(lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))"))
            assert revision_after['house']==before_revisions['house']
            assert revision_after['customers'][ids['other']]==before_revisions['customers'][ids['other']]
            assert revision_after['customers'][ids['customer']]==before_revisions['customers'][ids['customer']]+2
            report.update(existingRowsPreserved=True,connectionsExact=True,inventoryCommits=2,templateCommits=4,cancellationFences=1,personalRowsMatch=True,customerRevisionOnlyForInventoryWrites=True,systemhausRevisionUnchanged=True)
            server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend);admin=Client(restarted);assert admin.login('move-admin',password).status==200
            current=admin.request('GET',f"/api/v1/customers/{ids['customer']}/catalog/private-templates");assert current.status==200 and current.json()==personal
            assert current.headers.get('etag')==f'"templates-{personal["revision"]}"'
            project=admin.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert project.status==200 and project_by_id(project.json())==project_by_id(expected)
            assert canonical(durable(lab,db))==canonical(after)
            report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,frontend));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
