"""New isolated Windows/PG/Edge personal settings scenario; no build, source QA or package."""
import argparse,hashlib,json,platform,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain
from windows_job import run_isolated
from test_inventory_movement_gui import fixture,durable,tree

def inputs(dll,frontend):
    paths=[Path(__file__),Path(__file__).with_name('test_inventory_movement_gui.py'),Path(__file__).with_name('pg_support.py'),ROOT/'tools/windows/windows_job.py',ROOT/'development/frontend/tests/browser-quince-support.mjs',ROOT/'development/frontend/tests/browser-user-preferences.mjs',ROOT/'development/frontend/tests/browser-user-preferences-visual.mjs',ROOT/'development/frontend/tests/user-preferences.test.mjs']
    paths.extend(ROOT/'development/frontend/src'/n for n in ['ServerApp.jsx','UserPreferences.jsx','user-preferences.ts','user-preferences-journal.ts','user-preferences-words.ts'])
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'server':tree(dll.parent),'frontend':tree(frontend)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--visual-only',action='store_true');a=p.parse_args()
    dll=a.dll.resolve(strict=True);frontend=a.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file():raise RuntimeError('Complete explicit artifacts required')
    a.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();lab=Lab('preferences712gui')
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL','inputs':inputs(dll,frontend),'realQaAccessed':False,'productModified':False,'visualOnly':a.visual_only,'fixtureCreatedBy':'New synthetic inventory SQL fixture; reader without edit and second user without groups/customers. Preference writes under test through real Edge and HTTP.'}
    try:
        with lab:
            db=lab.create_database('preferences712gui');ids,password=fixture(lab,db,dll);ids['none']=str(uuid.uuid4());house=lab.sql(db,'SELECT id FROM systemhaus')
            lab.sql(db,f"INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{ids['none']}',systemhaus_id,'prefs-none',password_hash FROM app_user WHERE username='move-admin';",sensitive=True)
            assert lab.sql(db,'SELECT max(version) FROM schema_migration')=='11';lab.grant_runtime(db)
            before=durable(lab,db);revisions=lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))")
            server=lab.start_server(db,dll=dll,frontend=frontend);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-reader',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(a.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids));browser_started=time.monotonic()
            browser='browser-user-preferences-visual.mjs' if a.visual_only else 'browser-user-preferences.mjs'
            with (a.output/'browser-windows.log').open('xb') as log:done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests'/browser)],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=240)
            report.update(browserExitCode=done.returncode,browserSeconds=round(time.monotonic()-browser_started,3))
            if done.returncode:raise RuntimeError('Browser failed; sanitized evidence retained')
            expected=json.loads((a.output/'expected-preferences.json').read_text(encoding='utf-8'))
            assert durable(lab,db)==before,'Inventory changed through personal settings'
            assert lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))")==revisions
            assert lab.sql(db,'SELECT count(*) FROM operation')=='0'
            commits,fences=(2,0) if a.visual_only else (10,2)
            assert lab.sql(db,'SELECT count(*) FROM user_preference_operation WHERE state=\'committed\'')==str(commits)
            assert lab.sql(db,'SELECT count(*) FROM user_preference_operation WHERE state=\'cancelled\'')==str(fences)
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='user.preference.set'")==str(commits)
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='user.preference.set.cancel'")==str(fences)
            rows=lab.sql(db,"SELECT jsonb_agg(to_jsonb(t) ORDER BY owner_id) FROM user_preferences t")
            report.update(inventoryExact=True,systemhausAndCustomerRevisionsExact=True,personalCommits=commits,cancellationFences=fences,auditExactlyOnce=True)
            server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend)
            for username,key in [('move-reader','reader'),('prefs-none','none')]:
                if key not in expected:continue
                client=Client(restarted);assert client.login(username,password).status==200
                value=client.request('GET','/api/v1/me/preferences');assert value.status==200 and value.json()==expected[key]
                assert value.headers.get('etag')==f'"preferences-{expected[key]["revision"]}"'
            assert lab.sql(db,"SELECT jsonb_agg(to_jsonb(t) ORDER BY owner_id) FROM user_preferences t")==rows
            assert durable(lab,db)==before
            report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as e:report.update(failureType=type(e).__name__,failure=str(e))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,frontend));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (a.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
