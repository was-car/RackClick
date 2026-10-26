"""Scoped selected-user GUI scenario on a new native PostgreSQL lab only."""
import argparse,hashlib,json,platform,secrets,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'))
sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,toolchain,literal
from windows_job import run_isolated

def tree(directory):
 return {p.relative_to(directory).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.rglob('*')) if p.is_file()}

def inputs(dll,frontend):
 front=ROOT/'development/frontend';files=[Path(__file__),front/'tests/browser-admin-user-selection.mjs',*(front/'src'/name for name in ['AdminUsers.jsx','AdminSectionNavigation.jsx','AdminUserState.jsx','AdminUserPassword.jsx','AdminUserSessions.jsx','AdminEffectivePermissions.jsx'])]
 return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'server':tree(dll.parent),'frontend':tree(frontend)}

def fixture(lab,db,dll):
 secret=secrets.token_urlsafe(32)
 if lab.bootstrap(db,'selection-admin',secret,dll=dll).returncode:raise RuntimeError('Synthetic bootstrap failed; raw output private')
 house,admin=lab.sql(db,'SELECT id FROM systemhaus; SELECT id FROM app_user').splitlines()
 ids={k:str(uuid.uuid4()) for k in ['a','b','inactive','reader','group']};names={'a':'usuario a <img> überlap 😀','b':'usuario b selección','inactive':'usuario inactivo','reader':'selection-reader'}
 sql=[]
 for key in names:sql.append(f"INSERT INTO app_user(id,systemhaus_id,username,password_hash,active) SELECT '{ids[key]}',systemhaus_id,{literal(names[key])},password_hash,{'false' if key=='inactive' else 'true'} FROM app_user WHERE id='{admin}';")
 sql.extend([f"INSERT INTO user_group VALUES('{ids['group']}','{house}','Selection readers');",f"INSERT INTO user_group_member VALUES('{house}','{ids['reader']}','{ids['group']}');",f"INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{house}','{ids['group']}','systemhaus.read',NULL,NULL);"])
 lab.sql(db,'BEGIN;\n'+'\n'.join(sql)+'\nCOMMIT;',sensitive=True)
 return {'ids':{**ids,'admin':admin},'names':names,'draftSecret':secrets.token_urlsafe(24)},secret

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--dll',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);a=p.parse_args();dll=a.dll.resolve(strict=True);front=a.frontend.resolve(strict=True)
 if not dll.is_file() or dll.name!='RackClick.Server.dll' or not (front/'index.html').is_file():raise SystemExit('Explicit complete distributions required')
 a.output.mkdir(parents=True,exist_ok=False);report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'inputSha256':inputs(dll,front),'result':'FAIL'};started=time.monotonic();lab=Lab('admin-selection53')
 try:
  with lab:
   db=lab.create_database('admin-selection53');data,secret=fixture(lab,db,dll);lab.grant_runtime(db);server=lab.start_server(db,dll=dll,frontend=front)
   env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='selection-admin',RACKCLICK_TEST_PASSWORD=secret,RACKCLICK_TEST_OUTPUT=str(a.output.resolve()),RACKCLICK_FIXTURE=json.dumps(data))
   with (a.output/'browser.log').open('wb') as log:done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-admin-user-selection.mjs')],cwd=ROOT/'development/frontend',env=env,stdout=log,stderr=log,timeout=180)
   server.close();report['exitCode']=done.returncode
   if done.returncode:raise RuntimeError('Selection browser scenario failed')
   state=lab.sql(db,f"SELECT username,active FROM app_user WHERE id IN ('{data['ids']['a']}','{data['ids']['b']}','{data['ids']['inactive']}') ORDER BY username;")
   if state!=names_expected(data):raise RuntimeError('Final account states differ from the intended target')
   counts=lab.sql(db,"SELECT action,count(*) FROM audit_event GROUP BY action ORDER BY action;")
   report.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'),targetStateVerified=True,auditActionCounts=counts)
 except Exception as e:report['failureType']=type(e).__name__
 finally:
  report.update(seconds=round(time.monotonic()-started,3),finalInputSha256=inputs(dll,front),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers));report['inputsUnchanged']=report['inputSha256']==report['finalInputSha256']
  if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
  (a.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputSha256','finalInputSha256']},indent=2))
 return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1

def names_expected(data):
 return '\n'.join(data['names'][key]+'|'+('t' if key=='a' else 'f') for key in ['a','b','inactive'])
if __name__=='__main__':raise SystemExit(main())
