"""One new isolated Windows/PG/Edge shared-template notice focus, frozen artifacts; never real QA/build."""
import argparse,hashlib,json,platform,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain
from windows_job import run_isolated
from test_private_templates_gui import fixture as seed
from test_inventory_movement_gui import durable,tree,project_by_id
from test_inventory_poe_face_gui import canonical

def inputs(dll,frontend):
    paths=[Path(__file__),Path(__file__).with_name('test_private_templates_gui.py'),Path(__file__).with_name('test_inventory_catalog_gui.py'),Path(__file__).with_name('test_inventory_movement_gui.py'),Path(__file__).with_name('test_inventory_poe_face_gui.py'),Path(__file__).with_name('pg_support.py'),ROOT/'tools/windows/windows_job.py',ROOT/'development/frontend/tests/browser-quince-support.mjs',ROOT/'development/frontend/tests/browser-shared-template-notice.mjs',ROOT/'development/frontend/tests/client-change-details.test.mjs']
    paths.extend(ROOT/'development/frontend/src'/n for n in ['InventoryPanel.jsx','InventorySharedTemplates.jsx','shared-templates.ts','shared-templates-journal.ts','shared-template-words.ts','inventory-api.ts','client-changes.ts','client-change-details.ts','ClientChangeNotice.jsx'])
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'server':tree(dll.parent),'frontend':tree(frontend)}

def revisions(lab,db):return json.loads(lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))"))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--frontend',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file():raise RuntimeError('Complete explicit artifacts required')
    args.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();lab=Lab('shared-notice592')
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL','inputs':inputs(dll,frontend),'realQaAccessed':False,'productModified':False,'fixtureCreatedBy':'New synthetic SQL fixture and HTTP capture/publication setup; one foreign inventory command triggers real GUI notice, explicit refresh and restart. No source QA touched.'}
    try:
        with lab:
            db=lab.create_database('sharednotice592');ids,password=seed(lab,db,dll);lab.grant_runtime(db);server=lab.start_server(db,dll=dll,frontend=frontend);admin=Client(server);assert admin.login('move-admin',password).status==200
            actor=admin.request('GET','/api/v1/me').json()['user']['id'];base=f"/api/v1/customers/{ids['customer']}/catalog/private-templates";source=admin.request('GET',f"/api/v1/customers/{ids['customer']}/project").json()
            setup=admin.request('POST',base,{'type':'capture','deviceId':ids['a'],'name':'Notice private Ω','sourceRevision':source['revision']},{'X-RackClick-Actor':actor,'If-Match':'"templates-0"','Idempotency-Key':str(uuid.uuid4())});assert setup.status==200;ids['template']=setup.json()['result']['templateId']
            original=admin.request('GET',base+'/'+ids['template']).json()['template'];shared_base=f"/api/v1/customers/{ids['customer']}/catalog/shared-templates"
            setup=admin.request('POST',shared_base,{'type':'publish','privateTemplateId':ids['template'],'name':'Notice shared Ω','definitionVersion':1,'definitionSha256':original['definitionSha256']},{'X-RackClick-Actor':actor,'If-Match':'"shared-templates-0"','Idempotency-Key':str(uuid.uuid4())});assert setup.status==200;ids['shared']=setup.json()['result']['templateId'];ids['sharedHash']=original['definitionSha256'];shared_original=admin.request('GET',shared_base+'/'+ids['shared']).json()['template']
            before=durable(lab,db);before_revisions=revisions(lab,db)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids));browser_started=time.monotonic()
            with (args.output/'browser-windows.log').open('wb') as log:done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-shared-template-notice.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=240)
            report.update(browserExitCode=done.returncode,browserSeconds=round(time.monotonic()-browser_started,3))
            if done.returncode:raise RuntimeError('Browser failed; sanitized evidence retained')
            expected=json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'));after=durable(lab,db)
            for table,rows in before.items():
                for row in rows:assert row in after[table],f'Existing {table} row changed'
            for table in ['inventory_connection','inventory_connection_endpoint']:assert canonical({table:before[table]})==canonical({table:after[table]})
            assert len(after['inventory_device'])==len(before['inventory_device'])+1
            assert lab.sql(db,'SELECT count(*) FROM operation')=='1'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='inventory.device.createFromSharedTemplate'")=='1'
            revision_after=revisions(lab,db);assert revision_after['house']==before_revisions['house'];assert revision_after['customers'][ids['other']]==before_revisions['customers'][ids['other']];assert revision_after['customers'][ids['customer']]==before_revisions['customers'][ids['customer']]+1
            assert admin.request('GET',base+'/'+ids['template']).json()['template']==original
            assert admin.request('GET',shared_base+'/'+ids['shared']).json()['template']==shared_original
            report.update(existingRowsPreserved=True,connectionsExact=True,inventoryCommits=1,originalTemplateExact=True,sharedCopyExact=True,customerRevisionOnlyForNewEquipment=True,systemhausRevisionUnchanged=True)
            server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend);admin=Client(restarted);assert admin.login('move-admin',password).status==200
            assert admin.request('GET',shared_base+'/'+ids['shared']).json()['template']==shared_original
            assert admin.request('GET',base+'/'+ids['template']).json()['template']==original
            project=admin.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert project.status==200 and project_by_id(project.json())==project_by_id(expected);assert canonical(durable(lab,db))==canonical(after)
            report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,frontend));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
