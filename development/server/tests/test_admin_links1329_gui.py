"""One new full-app Edge/PG17 relationship-links flow; no actual QA access."""
import argparse,hashlib,json,platform,secrets,sys,threading,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1270-1329'
sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain
from windows_job import run_isolated
from test_admin_group_relations_gui import fixture,relational
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def inputs(dll,front):
 files=[Path(__file__),ROOT/'development/frontend/tests/browser-admin-links1329.mjs',ROOT/'development/server/tests/test_admin_group_relations_gui.py',ROOT/'development/server/tests/pg_support.py',ROOT/'tools/windows/windows_job.py']
 files += [ROOT/p for p in json.loads((E/'SOURCE-FREEZE-APP.json').read_bytes())['sources']]
 files += [p for d in [dll.parent,front] for p in d.rglob('*') if p.is_file()]
 return {p.relative_to(ROOT).as_posix():sha(p) for p in files}
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--dll',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);a=p.parse_args();dll=a.dll.resolve(strict=True);front=a.frontend.resolve(strict=True);a.output.mkdir(parents=True,exist_ok=False)
 record=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),result='FAIL',inputSha256=inputs(dll,front),actualQaAccessed=False,scope='Fresh native Edge/PG17 fixture; historical fixture seed helpers reused, old test body not executed.')
 lab=Lab('links1329');stop=threading.Event();thread=None;started=time.monotonic();errors=[]
 try:
  with lab:
   db=lab.create_database('links1329');data,secret=fixture(lab,db,dll);lab.grant_runtime(db);before=relational(lab,db);server=lab.start_server(db,dll=dll,frontend=front)
   def monitor():
    try:
     while not stop.is_set() and not (db.directory/'revoke.begin').exists():time.sleep(.03)
     if stop.is_set():return
     if before!=relational(lab,db):raise RuntimeError('Group data changed during read-only navigation')
     record['readOnlyEightGroupTablesExact']=True
     lab.sql(db,f"BEGIN;DELETE FROM user_group_member WHERE user_id='{data['ids']['admin']}';UPDATE systemhaus SET revision=revision+1;COMMIT;",sensitive=True)
     (db.directory/'revoke.ready').write_text('ready',encoding='ascii')
    except Exception as error:errors.append(type(error).__name__)
   thread=threading.Thread(target=monitor,daemon=True);thread.start()
   env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='relations-admin',RACKCLICK_TEST_PASSWORD=secret,RACKCLICK_TEST_OUTPUT=str(a.output.resolve()),RACKCLICK_FIXTURE=json.dumps(data),RACKCLICK_SIGNALS=str(db.directory))
   try:
    with (a.output/'browser.log').open('xb') as f:r=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-admin-links1329.mjs')],cwd=ROOT/'development/frontend',env=env,stdout=f,stderr=f,timeout=240)
   finally:stop.set();thread.join(5);server.close()
   record.update(exitCode=r.returncode,monitorErrors=errors)
   if r.returncode or errors:raise RuntimeError('Native links flow failed')
   after=relational(lab,db);restarted=lab.start_server(db,dll=dll,frontend=front);reader=Client(restarted);assert reader.login('relations-reader',secret).status==200;assert reader.request('GET','/api/v1/admin/user-groups').status==403;restarted.close();assert relational(lab,db)==after
   record.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'),applicationRestartAndReaderDenialVerified=True,groupDataAfterRevocationExactOnRestart=True,browserChecks=len(json.loads((a.output/'browser.json').read_bytes())['checks']))
 except Exception as error:record['failureType']=type(error).__name__
 finally:
  stop.set()
  if thread:thread.join(5)
  record.update(seconds=round(time.monotonic()-started,3),finalInputSha256=inputs(dll,front),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers));record['inputsUnchanged']=record['inputSha256']==record['finalInputSha256']
  if not record['inputsUnchanged']:record['result']='FAIL_INPUTS_CHANGED'
  (a.output/'fixture.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in record.items() if k not in ['inputSha256','finalInputSha256']},indent=2))
 return 0 if record['result']=='PASS' and record['labStopped'] and record['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
