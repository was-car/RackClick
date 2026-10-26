"""One NEW Windows/PostgreSQL/Edge rename flow; explicit frozen pair, no real QA/build."""
import argparse,hashlib,json,platform,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain
from windows_job import run_isolated
from test_inventory_movement_gui import fixture as seed,durable,tree
from test_inventory_poe_face_gui import canonical

def inputs(dll,frontend):
    paths=[Path(__file__),Path(__file__).with_name('test_inventory_movement_gui.py'),Path(__file__).with_name('test_inventory_poe_face_gui.py'),Path(__file__).with_name('pg_support.py'),ROOT/'tools/windows/windows_job.py',ROOT/'development/frontend/tests/browser-quince-support.mjs',ROOT/'development/frontend/tests/browser-private-template-rename.mjs',ROOT/'development/frontend/tests/private-template-rename.test.mjs']
    paths.extend(ROOT/'development/frontend/src'/name for name in ['private-templates.ts','InventoryPrivateTemplates.jsx','private-template-words.ts'])
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'server':tree(dll.parent),'frontend':tree(frontend)}

def personal(lab,db):
    return json.loads(lab.sql(db,"SELECT jsonb_build_object('aggregates',(SELECT jsonb_agg(to_jsonb(t) ORDER BY owner_id) FROM user_device_templates t),'templates',(SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM user_device_template t))"))

def revisions(lab,db):
    return json.loads(lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))"))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--frontend',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file():raise RuntimeError('Complete explicit artifacts required')
    args.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();lab=Lab('template-rename179')
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL','inputs':inputs(dll,frontend),'realQaAccessed':False,'productModified':False,'fixtureCreatedBy':'New synthetic movement seed; original template capture via HTTP setup and reader own clone via SQL; four GUI rename commits, zero inventory writes'}
    try:
        with lab:
            db=lab.create_database('rename179');ids,password=seed(lab,db,dll);lab.grant_runtime(db);server=lab.start_server(db,dll=dll,frontend=frontend)
            admin=Client(server);assert admin.login('move-admin',password).status==200
            me=admin.request('GET','/api/v1/me').json();actor=me['user']['id'];base=f"/api/v1/customers/{ids['customer']}/catalog/private-templates"
            source=admin.request('GET',f"/api/v1/customers/{ids['customer']}/project").json()
            capture=admin.request('POST',base,{'type':'capture','deviceId':ids['a'],'name':'QA Plantilla origen Ω','sourceRevision':source['revision']},{'X-RackClick-Actor':actor,'If-Match':'"templates-0"','Idempotency-Key':str(uuid.uuid4())})
            assert capture.status==200;ids['template']=capture.json()['result']['templateId'];ids['readerTemplate']=str(uuid.uuid4())
            lab.sql(db,f"INSERT INTO user_device_templates(systemhaus_id,owner_id,revision) SELECT systemhaus_id,'{ids['reader']}',1 FROM app_user WHERE id='{actor}'; INSERT INTO user_device_template(id,systemhaus_id,owner_id,name,active,definition_version,definition_sha256,definition_json) SELECT '{ids['readerTemplate']}',systemhaus_id,'{ids['reader']}','Reader owned synthetic',active,definition_version,definition_sha256,definition_json FROM user_device_template WHERE id='{ids['template']}';",sensitive=True)
            before=durable(lab,db);private_before=personal(lab,db);before_revisions=revisions(lab,db)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            browser_started=time.monotonic()
            with (args.output/'browser-windows.log').open('wb') as log:done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-private-template-rename.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=180)
            report.update(browserExitCode=done.returncode,browserSeconds=round(time.monotonic()-browser_started,3))
            if done.returncode:raise RuntimeError('Browser failed; sanitized evidence retained')
            expected=json.loads((args.output/'expected-templates.json').read_text(encoding='utf-8'));after=durable(lab,db);private_after=personal(lab,db)
            assert canonical(before)==canonical(after),'No inventory field/ID/group/port/cable/endpoint may change'
            assert before_revisions==revisions(lab,db),'Private rename must not change house/customer revisions'
            wanted=json.loads(json.dumps(private_before))
            for row in wanted['templates']:
                if row['id']==ids['template']:row['name']='QA Respuesta perdida Ω'
            for row in wanted['aggregates']:
                if row['owner_id']==actor:row['revision']+=3
            assert wanted==private_after,'Only three real name changes and personal revision increments allowed'
            assert lab.sql(db,'SELECT count(*) FROM operation')=='0'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action LIKE 'inventory.%'")=='0'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='user.deviceTemplate.rename'")=='4'
            assert lab.sql(db,'SELECT count(*) FROM user_device_template_operation')=='5','One setup capture and four rename commits; no duplicates after lost replay'
            assert lab.sql(db,"SELECT count(*) FROM user_device_template_operation WHERE result_json->'result'->>'type'='rename' AND result_json->'result'->>'changed'='false'")=='1'
            before_hash=hashlib.sha256(json.dumps(canonical(before),sort_keys=True).encode()).hexdigest();after_hash=hashlib.sha256(json.dumps(canonical(after),sort_keys=True).encode()).hexdigest()
            report.update(inventoryExact=True,inventoryBeforeSha256=before_hash,inventoryAfterSha256=after_hash,allRevisionsExceptOwnTemplatesUnchanged=True,templateOnlyNameChanges=True,immutableDefinitionIdsBytesHashVersionExact=True,renameCommits=4,realNameChanges=3,noOpCommits=1,renameAudits=4,inventoryCommits=0,readerTemplateExact=True,lostReplyReplayNoDuplicate=True)
            server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend);admin=Client(restarted);assert admin.login('move-admin',password).status==200
            current=admin.request('GET',base);assert current.status==200 and current.json()==expected
            assert current.headers.get('etag')==f'"templates-{expected["revision"]}"'
            assert canonical(durable(lab,db))==canonical(after) and personal(lab,db)==private_after
            detail=admin.request('GET',base+'/'+ids['template']);assert detail.status==200;metadata=detail.json()['template'];metadata.pop('name')
            assert metadata==json.loads((args.output/'template-immutable-before.json').read_text(encoding='utf-8'))
            report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,frontend));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
