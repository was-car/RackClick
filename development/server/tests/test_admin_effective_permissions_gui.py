"""Four Edge groups on NEW native PostgreSQL databases; never opens Wascar QA."""
import argparse, hashlib, json, platform, secrets, sys, threading, time, uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'))
sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab, DEFAULT_DLL, toolchain, literal
from windows_job import run_isolated

def hashes():
 front=ROOT/'development/frontend'
 paths=[DEFAULT_DLL,Path(__file__),front/'tests/browser-admin-effective-permissions.mjs',front/'tests/admin-effective-permissions.test.mjs',front/'src/AdminUsers.jsx',front/'src/AdminEffectivePermissions.jsx',front/'src/admin-effective-permissions.ts',*sorted((front/'dist').rglob('*'))]
 return {str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}

def durable(lab,db):
 tables=lab.sql(db,"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
 queries=[f"SELECT md5(COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)::text,'')) FROM public.\"{t}\" t" for t in tables]
 return lab.sql(db,' UNION ALL '.join(queries))  # stays in process memory, never evidence

def fixture(lab,db):
 password=secrets.token_urlsafe(24)
 if lab.bootstrap(db,'browser-admin',password).returncode:raise RuntimeError('Synthetic bootstrap failed')
 house=lab.sql(db,'SELECT id FROM systemhaus');admin=lab.sql(db,"SELECT id FROM app_user WHERE username='browser-admin'")
 ids={name:str(uuid.uuid4()) for name in ['target','reader','a','b','c','d','direct','grouped','readerGroup','cg1','cg2']}
 names={'target':'permisos <img src=x onerror=alert(1)> 😀','reader':'permission-reader','a':'Cliente A <b>literal</b>','b':'Cliente B Überlap 😀','c':'Cliente C','d':'Sin lectura','direct':'Directos <script>literal</script>','grouped':'Técnicos Überlap 😀','cg1':'Grupo clientes Uno <img>','cg2':'Grupo clientes Dos 😀'}
 sql=['BEGIN;']
 for key in ['target','reader']:
  sql.append(f"INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{ids[key]}',systemhaus_id,{literal(names[key])},password_hash FROM app_user WHERE id='{admin}';")
 for key in ['a','b','c','d']:sql.append(f"INSERT INTO customer(id,systemhaus_id,name) VALUES('{ids[key]}','{house}',{literal(names[key])});")
 for key in ['direct','grouped','readerGroup']:sql.append(f"INSERT INTO user_group(id,systemhaus_id,name) VALUES('{ids[key]}','{house}',{literal(names.get(key,key))});")
 for key in ['direct','grouped']:sql.append(f"INSERT INTO user_group_member VALUES('{house}','{ids['target']}','{ids[key]}');")
 sql.append(f"INSERT INTO user_group_member VALUES('{house}','{ids['reader']}','{ids['readerGroup']}');")
 for key,members in [('cg1',['a','b']),('cg2',['b','c'])]:
  sql.append(f"INSERT INTO customer_group(id,systemhaus_id,name) VALUES('{ids[key]}','{house}',{literal(names[key])});")
  for member in members:sql.append(f"INSERT INTO customer_group_member VALUES('{house}','{ids[key]}','{ids[member]}');")
 def grant(group,cap,customer=None,cg=None):
  gid=str(uuid.uuid4());sql.append(f"INSERT INTO permission_grant VALUES('{gid}','{house}','{ids[group]}',{literal(cap)},{literal(ids[customer]) if customer else 'NULL'},{literal(ids[cg]) if cg else 'NULL'});");return gid
 grant('direct','systemhaus.read');grant('grouped','systemhaus.read')
 grant('direct','inventory.read','a');grant('direct','security.manage','a');grant('direct','customer.manage','d')
 grant('grouped','inventory.read',cg='cg1');grant('grouped','inventory.read',cg='cg2');grant('grouped','inventory.edit',cg='cg1');grant('grouped','customer.manage',cg='cg2');grant('grouped','legacy.synthetic',cg='cg2');grant('grouped','legacy.synthetic',cg='cg2')
 grant('readerGroup','systemhaus.read');grant('readerGroup','inventory.read','a')
 sql.append('COMMIT;');lab.sql(db,'\n'.join(sql),sensitive=True)
 return {'ids':{**ids,'admin':admin},'names':names},password

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--case',choices=['1','2','3','4']);args=parser.parse_args()
 if args.output.exists():raise SystemExit('Choose a fresh evidence directory')
 args.output.mkdir(parents=True)
 if hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()!='350f2b2bf9e268a87c8095b1c93951ca2bfbe225ecd03c0923ba370431adbab4':raise SystemExit('Expected frozen DLL35')
 report={'utc':datetime.now(timezone.utc).isoformat(),'system':platform.platform(),'inputSha256':hashes(),'result':'FAIL','groups':[]};started=time.monotonic();lab=Lab('effective-gui36')
 try:
  with lab:
   for case in ([args.case] if args.case else ['1','2','3','4']):
    output=args.output/('group-'+case);output.mkdir();db=lab.create_database('effective-gui36-'+case);data,password=fixture(lab,db);lab.grant_runtime(db);server=lab.start_server(db,frontend=ROOT/'development/frontend/dist')
    env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='browser-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(output.resolve()),RACKCLICK_FIXTURE=json.dumps(data,ensure_ascii=True),RACKCLICK_CASE=case,RACKCLICK_SIGNALS=str(db.directory))
    stop=threading.Event();monitor_errors=[]
    def monitor():
     try:
      while not stop.is_set() and not (db.directory/'readonly.begin').exists():time.sleep(.02)
      if stop.is_set():return
      before=durable(lab,db);(db.directory/'readonly.ready').write_text('ready')
      while not stop.is_set() and not (db.directory/'readonly.end').exists():time.sleep(.02)
      if stop.is_set():return
      same=before==durable(lab,db);(db.directory/'readonly.result').write_text(json.dumps({'unchanged':same}))
     except Exception as e:monitor_errors.append(type(e).__name__)
    worker=threading.Thread(target=monitor,daemon=True);worker.start();tick=time.monotonic()
    try:
     with (output/'browser-windows.log').open('wb') as log:
      done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-admin-effective-permissions.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=240)
    finally:stop.set();worker.join(5);server.close()
    row={'case':case,'exitCode':done.returncode,'seconds':round(time.monotonic()-tick,3),'monitorErrors':monitor_errors};report['groups'].append(row)
    if done.returncode or monitor_errors:raise RuntimeError('Browser group failed; sanitized evidence preserved')
   report.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'),lab_id=lab.id)
 except Exception as e:report['failureType']=type(e).__name__
 finally:
  report.update(seconds=round(time.monotonic()-started,3),finalInputSha256=hashes(),labStopped=not lab.running)
  report['inputsUnchanged']=report['inputSha256']==report['finalInputSha256']
  if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
  (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
 return 0 if report['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
