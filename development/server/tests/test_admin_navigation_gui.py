"""One isolated Edge/PostgreSQL scenario; explicitly binds candidate DLL/frontend."""
import argparse,hashlib,json,platform,secrets,sys,threading,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'))
sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,toolchain,literal
from test_admin_effective_permissions_gui import durable
from windows_job import run_isolated

def tree(directory):
 return {p.relative_to(directory).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.rglob('*')) if p.is_file()}

def inputs(dll,frontend):
 front=ROOT/'development/frontend'
 owned=[Path(__file__),front/'tests/browser-admin-navigation.mjs',*(front/'src'/name for name in ['AdminUsers.jsx','AdminGroups.jsx','AdminSectionNavigation.jsx','server.css'])]
 return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in owned},'server':tree(dll.parent),'frontend':tree(frontend)}

def fixture(lab,db,dll):
 secret=secrets.token_urlsafe(32)
 if lab.bootstrap(db,'browser-admin',secret,dll=dll).returncode:raise RuntimeError('Synthetic bootstrap failed; raw output remains private')
 house,admin=lab.sql(db,'SELECT id FROM systemhaus; SELECT id FROM app_user').splitlines()
 ids={k:str(uuid.uuid4()) for k in ['reader','visible','hidden','readerGroup','userGroup','customerGroup']}
 sql=[f"INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{ids['reader']}',systemhaus_id,'nav-reader',password_hash FROM app_user WHERE id='{admin}';",
 f"INSERT INTO customer(id,systemhaus_id,name) VALUES('{ids['visible']}','{house}','Visible nav client'),('{ids['hidden']}','{house}','Hidden nav client');",
 f"INSERT INTO user_group VALUES('{ids['readerGroup']}','{house}','Reader navigation'),('{ids['userGroup']}','{house}','Technical nav group');",
 f"INSERT INTO user_group_member VALUES('{house}','{ids['reader']}','{ids['readerGroup']}');",
 f"INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{house}','{ids['readerGroup']}','systemhaus.read',NULL,NULL),('{uuid.uuid4()}','{house}','{ids['readerGroup']}','inventory.read','{ids['visible']}',NULL);",
 f"INSERT INTO customer_group VALUES('{ids['customerGroup']}','{house}','Customer nav group');",
 f"INSERT INTO customer_group_member VALUES('{house}','{ids['customerGroup']}','{ids['hidden']}');"]
 lab.sql(db,'BEGIN;\n'+'\n'.join(sql)+'\nCOMMIT;',sensitive=True)
 return {'readerName':'nav-reader','hiddenClient':'Hidden nav client','userGroupName':'Technical nav group','customerGroupName':'Customer nav group','newName':'navigation-user-'+uuid.uuid4().hex[:8],'newSecret':secrets.token_urlsafe(24),'resetDraft':secrets.token_urlsafe(24),'groupDraft':'Navigation draft'},secret

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--dll',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--mobile-only',action='store_true');a=p.parse_args()
 dll,frontend=a.dll.resolve(strict=True),a.frontend.resolve(strict=True)
 if not dll.is_file() or dll.name!='RackClick.Server.dll' or not (frontend/'index.html').is_file():raise SystemExit('Explicit complete distributions required')
 a.output.mkdir(parents=True,exist_ok=False)
 report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'mode':'mobile-only' if a.mobile_only else 'complete','inputSha256':inputs(dll,frontend),'result':'FAIL'};started=time.monotonic();lab=Lab('admin-navigation52');stop=threading.Event();errors=[];worker=None
 try:
  with lab:
   db=lab.create_database('admin-navigation52');data,secret=fixture(lab,db,dll);lab.grant_runtime(db);server=lab.start_server(db,dll=dll,frontend=frontend)
   def monitor():
    try:
     while not stop.is_set() and not (db.directory/'readonly.begin').exists():time.sleep(.02)
     if stop.is_set():return
     before=durable(lab,db);(db.directory/'readonly.ready').write_text('ready')
     while not stop.is_set() and not (db.directory/'readonly.end').exists():time.sleep(.02)
     if stop.is_set():return
     (db.directory/'readonly.result').write_text(json.dumps({'unchanged':before==durable(lab,db)}))
    except Exception as e:errors.append(type(e).__name__)
   worker=threading.Thread(target=monitor,daemon=True);worker.start();env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='browser-admin',RACKCLICK_TEST_PASSWORD=secret,RACKCLICK_TEST_OUTPUT=str(a.output.resolve()),RACKCLICK_SIGNALS=str(db.directory),RACKCLICK_FIXTURE=json.dumps(data))
   if a.mobile_only:env['RACKCLICK_NAVIGATION_MOBILE_ONLY']='1'
   with (a.output/'browser.log').open('wb') as log:done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-admin-navigation.mjs')],cwd=ROOT/'development/frontend',env=env,stdout=log,stderr=log,timeout=180)
   stop.set();worker.join(5);server.close();report.update(exitCode=done.returncode,monitorErrors=errors)
   if done.returncode or errors:raise RuntimeError('Scoped browser scenario failed')
   created=lab.sql(db,f"SELECT count(*) FROM app_user WHERE username={literal(data['newName'])}")
   if created!=('0' if a.mobile_only else '1'):raise RuntimeError('Unexpected persisted account count')
   report.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'),persistedNewAccounts=int(created))
 except Exception as e:report['failureType']=type(e).__name__
 finally:
  stop.set()
  if worker:worker.join(5)
  report.update(seconds=round(time.monotonic()-started,3),finalInputSha256=inputs(dll,frontend),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers))
  report['inputsUnchanged']=report['inputSha256']==report['finalInputSha256']
  if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
  (a.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputSha256','finalInputSha256']},indent=2))
 return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
