"""One Windows Edge/real PostgreSQL flow, with only new synthetic fixture data."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import secrets
import sys
import threading
import time
import uuid

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain,literal
from windows_job import run_isolated

def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def inputs(dll,front):
    owned=[Path(__file__),ROOT/'development/frontend/tests/browser-admin-onboarding1209.mjs']
    freeze=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-1150-1209/SOURCE-FREEZE-APP.json').read_bytes())['sources']
    owned.extend(ROOT/p for p in freeze)
    owned.extend(p for p in dll.parent.rglob('*') if p.is_file());owned.extend(p for p in front.rglob('*') if p.is_file())
    return {p.relative_to(ROOT).as_posix():sha(p) for p in owned}

def seed(lab,db,dll):
    password=secrets.token_urlsafe(32)
    if lab.bootstrap(db,'onboarding-admin',password,dll=dll).returncode:raise RuntimeError('Synthetic bootstrap failed; output private')
    house,admin=lab.sql(db,'SELECT id FROM systemhaus; SELECT id FROM app_user').splitlines()
    ids={k:str(uuid.uuid4()) for k in ['group','homonymGroup','visible','hidden']};ids['admin']=admin
    group='Técnicos <img> 東京';visible='Cliente visible müller 東京';hidden='Cliente ajeno privado'
    statements=[f"INSERT INTO customer(id,systemhaus_id,name) VALUES('{ids['visible']}','{house}',{literal(visible)}),('{ids['hidden']}','{house}',{literal(hidden)});",
        f"INSERT INTO user_group VALUES('{ids['group']}','{house}',{literal(group)}),('{ids['homonymGroup']}','{house}',{literal(group)});",
        f"INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{house}','{ids['group']}','systemhaus.read',NULL,NULL),('{uuid.uuid4()}','{house}','{ids['group']}','inventory.read','{ids['visible']}',NULL);"]
    lab.sql(db,'BEGIN;\n'+'\n'.join(statements)+'\nCOMMIT;',sensitive=True)
    data=dict(ids=ids,newName='nuevo <img> müller 東京 '+uuid.uuid4().hex[:8],newSecret=secrets.token_urlsafe(24),
        resetDraft=secrets.token_urlsafe(24),groupName=group,visibleName=visible,hiddenName=hidden)
    return data,password

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--frontend',type=Path,required=True);a=parser.parse_args()
    dll=a.dll.resolve(strict=True);front=a.frontend.resolve(strict=True)
    assert dll.name=='RackClick.Server.dll' and (front/'index.html').is_file()
    a.output.mkdir(parents=True,exist_ok=False)
    report=dict(platform=platform.platform(),result='FAIL',inputSha256=inputs(dll,front),actualQaAccessed=False,
        scope='One new native PG fixture with real full-app Edge, controlled network loss only; no API response mocks.')
    lab=Lab('onboarding1209');started=time.monotonic();stop=threading.Event();monitor_errors=[];worker=None
    try:
        with lab:
            db=lab.create_database('onboarding1209');data,password=seed(lab,db,dll);lab.grant_runtime(db)
            server=lab.start_server(db,dll=dll,frontend=front)
            def monitor():
                try:
                    while not stop.is_set() and not (db.directory/'revoke.begin').exists():time.sleep(.03)
                    if stop.is_set():return
                    # Synthetic fixture only: bypass API to emulate external revocation, never user QA.
                    lab.sql(db,f"BEGIN; DELETE FROM user_group_member WHERE user_id='{data['ids']['admin']}'; UPDATE systemhaus SET revision=revision+1; COMMIT;",sensitive=True)
                    (db.directory/'revoke.ready').write_text('ready',encoding='ascii')
                except Exception as error:monitor_errors.append(type(error).__name__)
            worker=threading.Thread(target=monitor,daemon=True);worker.start()
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='onboarding-admin',RACKCLICK_TEST_PASSWORD=password,
                RACKCLICK_TEST_OUTPUT=str(a.output.resolve()),RACKCLICK_SIGNALS=str(db.directory),RACKCLICK_FIXTURE=json.dumps(data))
            with (a.output/'browser.log').open('xb') as log:
                done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-admin-onboarding1209.mjs')],
                    cwd=ROOT/'development/frontend',env=env,stdout=log,stderr=log,timeout=300)
            stop.set();worker.join(5);server.close();report.update(exitCode=done.returncode,monitorErrors=monitor_errors)
            if done.returncode or monitor_errors:raise RuntimeError('Scoped native onboarding flow failed')
            browser=json.loads((a.output/'browser.json').read_bytes());created=browser['createdUsers'];assert len(created)==4
            for label,user_id in created.items():
                assert lab.sql(db,f"SELECT count(*) FROM app_user WHERE id='{user_id}' AND username={literal(data['newName']+' '+label)} AND active")=='1'
            assert lab.sql(db,f"SELECT count(*) FROM app_user WHERE username={literal(data['newName']+' cancelled')}")=='0'
            assert lab.sql(db,f"SELECT count(*) FROM user_group_member WHERE user_id='{created['es']}' AND group_id='{data['ids']['group']}'")=='1'
            assert lab.sql(db,f"SELECT count(*) FROM user_group_member WHERE user_id='{created['es']}' AND group_id='{data['ids']['homonymGroup']}'")=='0'
            report['auditActionCounts']=lab.sql(db,'SELECT action,count(*) FROM audit_event GROUP BY action ORDER BY action')
            restarted=lab.start_server(db,dll=dll,frontend=front)
            client=Client(restarted)
            identity=client.login(data['newName']+' es',data['newSecret']);assert identity.status==200
            clients=client.request('GET','/api/v1/customers');assert clients.status==200
            assert data['visibleName'] in clients.body.decode('utf-8') and data['hiddenName'] not in clients.body.decode('utf-8')
            forbidden=client.request('GET','/api/v1/admin/users');assert forbidden.status==403
            restarted.close()
            report.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'),persistedCreatedUsers=4,cancelledUserAbsent=True,
                exactUuidGroupAssignment=True,applicationRestartAndScopedLoginVerified=True,serverAdministrativeDenialVerified=True,
                browserChecks=len(browser['checks']))
    except Exception as error:report['failureType']=type(error).__name__
    finally:
        stop.set()
        if worker:worker.join(5)
        report.update(seconds=round(time.monotonic()-started,3),finalInputSha256=inputs(dll,front),
            labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers))
        report['inputsUnchanged']=report['inputSha256']==report['finalInputSha256']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (a.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:v for k,v in report.items() if k not in ['inputSha256','finalInputSha256']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1

if __name__=='__main__':raise SystemExit(main())
