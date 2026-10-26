"""One new isolated Windows/PG/Edge shared-template scenario, frozen artifacts; never real QA/build."""
import argparse,hashlib,json,platform,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain,literal
from windows_job import run_isolated
from test_private_templates_gui import fixture as seed
from test_inventory_movement_gui import durable,tree,project_by_id
from test_inventory_poe_face_gui import canonical

def inputs(dll,frontend):
    paths=[Path(__file__),Path(__file__).with_name('test_private_templates_gui.py'),Path(__file__).with_name('test_inventory_catalog_gui.py'),Path(__file__).with_name('test_inventory_movement_gui.py'),Path(__file__).with_name('test_inventory_poe_face_gui.py'),Path(__file__).with_name('pg_support.py'),ROOT/'tools/windows/windows_job.py',ROOT/'development/frontend/tests/browser-quince-support.mjs',ROOT/'development/frontend/tests/browser-shared-templates.mjs',ROOT/'development/frontend/tests/shared-templates.test.mjs']
    paths.extend(ROOT/'development/frontend/src'/n for n in ['InventoryPanel.jsx','InventorySharedTemplates.jsx','shared-templates.ts','shared-templates-journal.ts','shared-template-words.ts','admin-grants.ts','admin-audit.ts','AdminGroups.jsx','AdminGroupRelations.jsx','AdminEffectivePermissions.jsx','inventory-api.ts'])
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'server':tree(dll.parent),'frontend':tree(frontend)}

def revisions(lab,db):return json.loads(lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))"))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--frontend',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file():raise RuntimeError('Complete explicit artifacts required')
    args.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();lab=Lab('shared592')
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL','inputs':inputs(dll,frontend),'realQaAccessed':False,'productModified':False,'fixtureCreatedBy':'New synthetic SQL fixture and4 HTTP private configurations setup; GUI publication/recovery/retirement and3 equipment creations. No source QA data touched.'}
    try:
        with lab:
            db=lab.create_database('shared592');ids,password=seed(lab,db,dll);lab.grant_runtime(db);server=lab.start_server(db,dll=dll,frontend=frontend);admin=Client(server);assert admin.login('move-admin',password).status==200
            actor=admin.request('GET','/api/v1/me').json()['user']['id'];house=lab.sql(db,'SELECT id FROM systemhaus');ids['owner']=actor;ids['publisher']=str(uuid.uuid4());ids['publisherGroup']=str(uuid.uuid4())
            admin_group=lab.sql(db,f"SELECT group_id FROM user_group_member WHERE user_id='{actor}'")
            lab.sql(db,f"BEGIN; DELETE FROM user_group_member WHERE user_id='{ids['second']}'; INSERT INTO user_group_member VALUES('{house}','{ids['second']}','{ids['baseGroup']}'),('{house}','{ids['second']}','{ids['techGroup']}'); INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{house}','{ids['techGroup']}','inventory.edit','{ids['customer']}',NULL); INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{ids['publisher']}',systemhaus_id,'move-publisher',password_hash FROM app_user WHERE id='{actor}'; INSERT INTO user_group VALUES('{ids['publisherGroup']}','{house}','Synthetic publisher without edit'); INSERT INTO user_group_member VALUES('{house}','{ids['publisher']}','{ids['baseGroup']}'),('{house}','{ids['publisher']}','{ids['publisherGroup']}'); INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{house}','{ids['publisherGroup']}','inventory.read','{ids['customer']}',NULL),('{uuid.uuid4()}','{house}','{ids['publisherGroup']}','templates.publish','{ids['customer']}',NULL),('{uuid.uuid4()}','{house}','{ids['publisherGroup']}','inventory.edit','{ids['customer']}',NULL); COMMIT;",sensitive=True)
            base=f"/api/v1/customers/{ids['customer']}/catalog/private-templates";originals={}
            definition={'kind':'rackEquipment','sizeU':1,'poeBudget':12,'icon':'▦','color':'#123456','visualFamily':'switch','portGroups':[{'key':'g1','type':'rj45','name':'A Ω','prefix':'A','sortOrder':0,'ports':[{'gn':1,'sortOrder':0,'type':'rj45','label':'Literal <img> 東京','poe':True,'color':None,'face':'front','powerRole':'unspecified'}]},{'key':'g2','type':'rj45','name':'B Ω','prefix':'B','sortOrder':1,'ports':[{'gn':1,'sortOrder':0,'type':'rj45_poe','label':'PoE independent','poe':False,'color':None,'face':'rear','powerRole':'unspecified'}]}]}
            for index,kind in enumerate(['rackEquipment','dose','endDevice']):
                value=dict(definition,kind=kind,sizeU=1 if kind=='rackEquipment' else None)
                created=admin.request('POST',base+'/configurations',{'type':'create','name':'Private '+kind,'definitionVersion':1,'definition':value},{'X-RackClick-Actor':actor,'If-Match':f'"templates-{index}"','Idempotency-Key':str(uuid.uuid4())});assert created.status==200
                ids['template_'+kind]=created.json()['result']['templateId'];originals[kind]=admin.request('GET',base+'/'+ids['template_'+kind]).json()['template']
            publisher=Client(server);assert publisher.login('move-publisher',password).status==200
            created=publisher.request('POST',base+'/configurations',{'type':'create','name':'Private publisher Ω','definitionVersion':1,'definition':definition},{'X-RackClick-Actor':ids['publisher'],'If-Match':'"templates-0"','Idempotency-Key':str(uuid.uuid4())});assert created.status==200;ids['publisherTemplate']=created.json()['result']['templateId']
            lab.sql(db,f"DELETE FROM permission_grant WHERE user_group_id='{ids['publisherGroup']}' AND capability='inventory.edit'",sensitive=True)
            before=durable(lab,db);before_revisions=revisions(lab,db)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids));browser_started=time.monotonic()
            with (args.output/'browser-windows.log').open('wb') as log:done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-shared-templates.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=240)
            report.update(browserExitCode=done.returncode,browserSeconds=round(time.monotonic()-browser_started,3))
            if done.returncode:raise RuntimeError('Browser failed; sanitized evidence retained')
            expected=json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'));shared=json.loads((args.output/'expected-shared.json').read_text(encoding='utf-8'));after=durable(lab,db)
            for table,rows in before.items():
                for row in rows:assert row in after[table],f'Existing {table} row changed'
            for table in ['inventory_connection','inventory_connection_endpoint']:assert canonical({table:before[table]})==canonical({table:after[table]})
            assert len(after['inventory_device'])==len(before['inventory_device'])+3
            assert len(after['inventory_port_group'])==len(before['inventory_port_group'])+6
            assert len(after['inventory_port'])==len(before['inventory_port'])+6
            assert lab.sql(db,'SELECT count(*) FROM operation')=='3'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='inventory.device.createFromSharedTemplate'")=='3'
            assert lab.sql(db,'SELECT count(*) FROM user_device_template')=='4'
            for kind,original in originals.items():assert admin.request('GET',base+'/'+ids['template_'+kind]).json()['template']==original
            revision_after=revisions(lab,db);assert revision_after['house']==before_revisions['house'];assert revision_after['customers'][ids['other']]==before_revisions['customers'][ids['other']];assert revision_after['customers'][ids['customer']]==before_revisions['customers'][ids['customer']]+3
            report.update(existingRowsPreserved=True,connectionsExact=True,inventoryCommits=3,originalPrivateTemplatesExact=True,customerRevisionOnlyForNewEquipment=True,systemhausRevisionUnchanged=True)
            server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend);admin=Client(restarted);assert admin.login('move-admin',password).status==200
            current=admin.request('GET',f"/api/v1/customers/{ids['customer']}/catalog/shared-templates");assert current.status==200 and current.json()==shared;assert current.headers.get('etag')==f'"shared-templates-{shared["revision"]}"'
            for kind,original in originals.items():assert admin.request('GET',base+'/'+ids['template_'+kind]).json()['template']==original
            project=admin.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert project.status==200 and project_by_id(project.json())==project_by_id(expected);assert canonical(durable(lab,db))==canonical(after)
            report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,frontend));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
