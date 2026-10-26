"""Windows-only synthetic native fixture for password reset GUI; no existing QA lab."""
import argparse, hashlib, json, platform, secrets, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'))
sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab, DEFAULT_DLL, toolchain
from windows_job import run_isolated
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
if args.output.exists():raise SystemExit('Choose a fresh evidence directory')
args.output.mkdir(parents=True)
front=ROOT/'development/frontend';scenario=front/'tests/browser-admin-password.mjs'
def hashes():return {str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in [DEFAULT_DLL,scenario,*sorted((front/'dist').rglob('*'))] if p.is_file()}
assert hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()=='d0a5c95783ecc8e9ae7165be9a1bcd8857ee587b643fac3f07aa6092e6bd4b81'
report={'utc':datetime.now(timezone.utc).isoformat(),'system':platform.platform(),'inputSha256':hashes(),'result':'FAIL','exit_code':1}
lab=Lab('password-gui24')
try:
 with lab:
  db=lab.create_database('password-gui');password=secrets.token_urlsafe(24)
  assert lab.bootstrap(db,'browser-admin',password).returncode==0
  house=lab.sql(db,'SELECT id FROM systemhaus');admin=lab.sql(db,"SELECT id FROM app_user WHERE username='browser-admin'")
  target,second=[str(uuid.uuid4()) for _ in range(2)]
  sql=f"""BEGIN;
  INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{target}',systemhaus_id,'password-reader',password_hash FROM app_user WHERE id='{admin}';
  INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{second}',systemhaus_id,'second-admin',password_hash FROM app_user WHERE id='{admin}';
  INSERT INTO user_group_member(systemhaus_id,user_id,group_id) SELECT systemhaus_id,'{second}',group_id FROM user_group_member WHERE user_id='{admin}';
  COMMIT;"""
  lab.sql(db,sql,sensitive=True);lab.grant_runtime(db);server=lab.start_server(db,frontend=front/'dist')
  env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='browser-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_NEW_PASSWORD=secrets.token_urlsafe(24),RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE_TARGET=target,RACKCLICK_FIXTURE_ADMIN=admin)
  with (args.output/'browser-windows.log').open('wb') as log:
   done=run_isolated([str(toolchain()['node']),str(scenario)],env=env,cwd=front,stdout=log,stderr=log,timeout=300)
  report.update(exit_code=done.returncode,result='PASS' if done.returncode==0 else 'FAIL',lab_id=lab.id,database=db.name,postgresql=lab.sql('postgres','SHOW server_version;'),origin=server.origin)
except Exception as e:report['failureType']=type(e).__name__
finally:
 report.update(finalInputSha256=hashes(),labStopped=not lab.running);report['inputsUnchanged']=report['inputSha256']==report['finalInputSha256']
 if not report['inputsUnchanged']:report.update(result='FAIL_INPUTS_CHANGED',exit_code=1)
 (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
raise SystemExit(report['exit_code'])
