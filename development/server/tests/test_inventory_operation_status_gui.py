"""Pending inventory status through real Edge/HTTP and a new PostgreSQL laboratory.

Requires immutable private DLL/frontend and a new private output directory.
No build, installed services, existing QA, or VM is accessed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'))
sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain,protect_directory
from windows_job import run_isolated
from test_inventory_movement_gui import fixture,durable,tree,project_by_id

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dll','frontend','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--scenario',choices=('status','context','eligibility','instant','write-permission','delete-permission'),default='status')
    a=parser.parse_args();dll=a.dll.resolve(strict=True);front=a.frontend.resolve(strict=True);out=a.output.resolve()
    if not all(p.is_relative_to(ROOT/'.local') for p in (dll,front,out)):
        raise ValueError('Only explicit private artifacts and a new private output path are allowed')
    out.mkdir(parents=True,exist_ok=False);protect_directory(out)
    before_inputs={'dll':tree(dll.parent),'frontend':tree(front)}
    browser_script=ROOT/'development/frontend/tests'/{'status':'browser-inventory-operation-status.mjs','context':'browser-inventory-context.mjs','eligibility':'browser-inventory-eligibility.mjs','instant':'browser-inventory-instant.mjs','write-permission':'browser-inventory-write-permission.mjs','delete-permission':'browser-inventory-delete-permission.mjs'}[a.scenario]
    report={'result':'FAIL','scenario':a.scenario,'qaTouched':False,'vmTouched':False,'newCluster':True,
            'dllSha256':hashlib.sha256(dll.read_bytes()).hexdigest(),
            'browserScriptSha256':hashlib.sha256(browser_script.read_bytes()).hexdigest()}
    lab=Lab('inventory-operation-status');started=time.monotonic()
    try:
        with lab:
            db=lab.create_database('operation-status');ids,password=fixture(lab,db,dll)
            lab.grant_runtime(db);before=durable(lab,db);server=lab.start_server(db,dll=dll,frontend=front)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(out),RACKCLICK_FIXTURE=json.dumps(ids))
            with (out/'browser-private.log').open('wb') as log:
                result=run_isolated([str(toolchain()['node']),str(browser_script)],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=180)
            report['browserExitCode']=result.returncode
            if result.returncode:raise RuntimeError('Browser scenario failed; private evidence preserved')
            assert durable(lab,db)==before,'All nine inventory tables, timestamps and endpoints must be restored exactly'
            report['nineSqlTablesExactlyRestored']=True
            expected=json.loads((out/'expected-project.json').read_bytes());server.close();restarted=lab.start_server(db,dll=dll,frontend=front)
            admin=Client(restarted);assert admin.login('move-admin',password).status==200
            actual=admin.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert actual.status==200
            assert project_by_id(actual.json())==project_by_id(expected);assert durable(lab,db)==before
            report.update(result='PASS',persistenceAfterServerRestart=True,postgresql=lab.sql('postgres','SHOW server_version'))
    except Exception as error:
        report.update(errorType=type(error).__name__,error=str(error))
    finally:
        lab.close();report.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),elapsedSeconds=round(time.monotonic()-started,2),inputsUnchanged=before_inputs=={'dll':tree(dll.parent),'frontend':tree(front)})
        (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False));return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] and report['inputsUnchanged'] else 1

if __name__=='__main__':raise SystemExit(main())
