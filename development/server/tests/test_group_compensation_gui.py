"""Isolated Windows Edge/PostgreSQL check of the structural GUI inverse.

Supply immutable DLL and frontend explicitly. No build, install or QA access.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'))
sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,literal,toolchain,protect_directory
from windows_job import run_isolated
from test_inventory_movement_gui import fixture as seed,durable,tree,project_by_id


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dll','frontend','output'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();dll=a.dll.resolve(strict=True);front=a.frontend.resolve(strict=True);out=a.output.resolve()
    if not dll.is_relative_to(ROOT/'.local') or not front.is_relative_to(ROOT/'.local') or not out.is_relative_to(ROOT/'.local'):
        raise ValueError('Only private explicit artifacts and a new private result path are allowed')
    out.mkdir(parents=True,exist_ok=False);protect_directory(out)
    before_inputs={'dll':tree(dll.parent),'frontend':tree(front)}
    report={'result':'FAIL','qaTouched':False,'vmTouched':False,'newCluster':True,'fixture':'SQL synthetic; writes under test use GUI',
        'dllSha256':hashlib.sha256(dll.read_bytes()).hexdigest(),'browserScriptSha256':hashlib.sha256((ROOT/'development/frontend/tests/browser-group-compensation.mjs').read_bytes()).hexdigest()}
    lab=Lab('group-compensation-gui');started=time.monotonic()
    try:
        with lab:
            db=lab.create_database('group-compensation');ids,password=seed(lab,db,dll)
            ids.update({key:str(uuid.uuid4()) for key in ('undoPort','undoGroup','undoCable')})
            lab.sql(db,f"""BEGIN;
                INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order)
                SELECT '{ids['undoGroup']}',systemhaus_id,customer_id,device_id,'rj45','Grupo a','A',1 FROM inventory_port_group WHERE id='{ids['ga']}';
                INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,properties)
                SELECT '{ids['undoPort']}',systemhaus_id,customer_id,device_id,'{ids['undoGroup']}','rj45',1,0,'Original Ω', 'free',false,0.3,NULL,'rear','{{"fixture":"original"}}'::jsonb FROM inventory_port WHERE id='{ids['pa']}';
                INSERT INTO inventory_connection(id,systemhaus_id,customer_id,note,color,patch,properties)
                SELECT '{ids['undoCable']}',systemhaus_id,customer_id,'Restore literal <img> 東京',NULL,'tested','{{"fixture":"original"}}'::jsonb FROM inventory_connection WHERE id='{ids['cable']}';
                INSERT INTO inventory_connection_endpoint SELECT systemhaus_id,customer_id,'{ids['undoCable']}',0,'{ids['undoPort']}' FROM inventory_connection WHERE id='{ids['cable']}';
                INSERT INTO inventory_connection_endpoint SELECT systemhaus_id,customer_id,'{ids['undoCable']}',1,'{ids['pc2']}' FROM inventory_connection WHERE id='{ids['cable']}';
                COMMIT;""",sensitive=True)
            lab.grant_runtime(db);before=durable(lab,db);server=lab.start_server(db,dll=dll,frontend=front)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(out),RACKCLICK_FIXTURE=json.dumps(ids))
            with (out/'browser-private.log').open('wb') as log:
                result=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-group-compensation.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=180)
            report['browserExitCode']=result.returncode
            if result.returncode:raise RuntimeError('Browser scenario failed; private evidence preserved')
            assert durable(lab,db)==before,'All nine tables, including cable timestamps/endpoints, must match exactly'
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
