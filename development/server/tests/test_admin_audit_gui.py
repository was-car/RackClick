"""Six Edge groups on new native PostgreSQL bases; never opens Wascar QA."""
import argparse, hashlib, json, platform, secrets, sys, threading, time, uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'))
sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab, DEFAULT_DLL, toolchain, literal
from windows_job import run_isolated
from test_admin_effective_permissions_gui import durable
from audit_administration_fixture import administrative_events


def hashes():
 front=ROOT/'development/frontend'
 ps=[DEFAULT_DLL,Path(__file__),Path(__file__).with_name('audit_administration_fixture.py'),front/'tests/browser-admin-audit.mjs',front/'tests/browser-admin-audit-detail.mjs',front/'tests/browser-admin-audit-administration.mjs',front/'tests/admin-audit.test.mjs',front/'tests/admin-audit-detail.test.mjs',front/'tests/admin-audit-administration.test.mjs',front/'src/AdminAudit.jsx',front/'src/admin-audit.ts',front/'src/AdminUsers.jsx',front/'src/ServerApp.jsx',*sorted((front/'dist').rglob('*'))]
 return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in ps if p.is_file()}


def fixture(lab,db,case=None):
 password=secrets.token_urlsafe(32)
 if lab.bootstrap(db,'browser-admin',password).returncode:raise RuntimeError('Synthetic bootstrap failed; raw logs private')
 house,admin=lab.sql(db,'SELECT id FROM systemhaus; SELECT id FROM app_user').splitlines()
 group=lab.sql(db,f"SELECT group_id FROM user_group_member WHERE user_id='{admin}'")
 secondary,reader,customer,base,rg=[str(uuid.uuid4()) for _ in range(5)]
 extra_resource=str(uuid.uuid4())
 name='audit-ä-<img>-😀';ids=[str(uuid.UUID(int=i)) for i in range(104,0,-1)]
 sql=[f"INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{secondary}',systemhaus_id,{literal(name)},password_hash FROM app_user WHERE id='{admin}';",
      f"INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{reader}',systemhaus_id,'audit-reader',password_hash FROM app_user WHERE id='{admin}';",
      f"INSERT INTO user_group_member VALUES('{house}','{secondary}','{group}');",
      f"INSERT INTO customer(id,systemhaus_id,name) VALUES('{customer}','{house}','Synthetic reader client');",
      f"INSERT INTO user_group VALUES('{base}','{house}','Base reader'),('{rg}','{house}','Scoped reader');",
      f"INSERT INTO user_group_member VALUES('{house}','{admin}','{base}'),('{house}','{reader}','{base}'),('{house}','{reader}','{rg}');",
      f"INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{house}','{base}','systemhaus.read',NULL,NULL),('{uuid.uuid4()}','{house}','{rg}','inventory.read','{customer}',NULL);" ]
 names={'before':'Cliente é <img> 😀 anterior','after':'\ufeffCliente Ω <img> 😀 posterior','houseBefore':'Systemhaus Ä anterior','houseAfter':'Systemhaus β posterior'}
 administration=administrative_events(house,secondary,customer) if case=='6' else []
 for i,event in enumerate(ids):
  if case=='6' and i<len(administration):
   entry=administration[i];entry['id']=event
   before=entry['before'];after=entry['after'] | {'private':{'password':'synthetic-hidden-audit','token':'synthetic-hidden-audit'}}
   if before is not None:before=before | {'private':'synthetic-hidden-audit'}
   sql.append(f"INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json,occurred_at) VALUES('{event}','{house}','{secondary}','{entry['request']}',{literal(entry['action'])},'{entry['resource']}',{literal(json.dumps(before,ensure_ascii=False))},{literal(json.dumps(after,ensure_ascii=False))},'2026-01-01T12:34:56.123456Z');")
   continue
  if case=='5' and i<3:
   action=['customer.rename','systemhaus.rename','customer.create'][i]
   resource=house if i==1 else customer
   before=None if i==2 else ({'id':house,'name':names['houseBefore'],'revision':3} if i==1 else {'id':customer,'houseId':house,'name':names['before'],'revision':1})
   after={'id':house,'name':names['houseAfter'],'revision':4} if i==1 else {'id':customer,'houseId':house,'name':names['before'] if i==2 else names['after'],'revision':1 if i==2 else 2}
   after['secret']='synthetic-hidden-audit'
   sql.append(f"INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json,occurred_at) VALUES('{event}','{house}','{secondary}','{uuid.uuid4()}','{action}','{resource}',{literal(json.dumps(before,ensure_ascii=False))},{literal(json.dumps(after,ensure_ascii=False))},'2026-01-01T12:34:56.123456Z');")
   continue
  event_actor=admin if case=='4' and 84<=i<94 else secondary
  resource=extra_resource if case=='4' and i>=94 else customer
  sql.append(f"INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,before_json,after_json,occurred_at) VALUES('{event}','{house}','{event_actor}','{uuid.uuid4()}','synthetic.<img>','{resource}','{{\"password\":\"synthetic-hidden-audit\"}}','{{\"token\":\"synthetic-hidden-audit\"}}','2026-01-01T12:34:56.123456Z');")
 if case=='5':
  sql.append(f"UPDATE customer SET name={literal(names['after'])},revision=2 WHERE id='{customer}'; UPDATE systemhaus SET name={literal(names['houseAfter'])},revision=4 WHERE id='{house}';")
 lab.sql(db,'BEGIN;\n'+'\n'.join(sql)+'\nCOMMIT;',sensitive=True)
 return {'admin':admin,'secondary':secondary,'reader':reader,'group':group,'name':name,'ids':ids,'resource':customer,'extraResource':extra_resource,'administration':administration,'details':{'rename':ids[0],'house':ids[1],'create':ids[2],'unavailable':ids[3],'names':names}},password


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--case',choices=['1','2','3','4','5','6']);args=p.parse_args()
 args.output.mkdir(parents=True,exist_ok=False)
 if hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()!='d469e4d2ea88f7947b4753738741ea0078f507119f1d249f701ca62852fb2891':raise RuntimeError('Expected candidate DLL50')
 report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'inputSha256':hashes(),'result':'FAIL','groups':[]};started=time.monotonic();lab=Lab('audit-gui50')
 try:
  with lab:
   for case in ([args.case] if args.case else ['1','2','3','4','5','6']):
    out=args.output/('group-'+case);out.mkdir();db=lab.create_database('audit-gui50-'+case);data,password=fixture(lab,db,case);lab.grant_runtime(db);server=lab.start_server(db,frontend=ROOT/'development/frontend/dist')
    env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='browser-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(out.resolve()),RACKCLICK_FIXTURE=json.dumps(data,ensure_ascii=True),RACKCLICK_CASE=case,RACKCLICK_SIGNALS=str(db.directory))
    stop=threading.Event();errors=[]
    def monitor():
     try:
      while not stop.is_set() and not (db.directory/'readonly.begin').exists():time.sleep(.02)
      if stop.is_set():return
      before=durable(lab,db);(db.directory/'readonly.ready').write_text('ready')
      while not stop.is_set() and not (db.directory/'readonly.end').exists():time.sleep(.02)
      if stop.is_set():return
      (db.directory/'readonly.result').write_text(json.dumps({'unchanged':before==durable(lab,db)}))
     except Exception as e:errors.append(type(e).__name__)
    worker=threading.Thread(target=monitor,daemon=True);worker.start();tick=time.monotonic()
    try:
     with (out/'browser-windows.log').open('wb') as log:
      done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-admin-audit.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=240)
    finally:stop.set();worker.join(5);server.close()
    report['groups'].append({'case':case,'exitCode':done.returncode,'seconds':round(time.monotonic()-tick,3),'monitorErrors':errors})
    if done.returncode or errors:raise RuntimeError('Browser group failed; sanitized evidence retained')
   report.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'))
 except Exception as e:report['failureType']=type(e).__name__
 finally:
  report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputSha256=hashes())
  report['inputsUnchanged']=report['inputSha256']==report['finalInputSha256']
  if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
  (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
  print(json.dumps({k:v for k,v in report.items() if k not in ('inputSha256','finalInputSha256')},indent=2))
 return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
