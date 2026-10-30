"""NEW isolated Windows/PG/Edge XLS HTML RC9 path; frozen artifacts only, no real QA."""
import argparse,base64,hashlib,json,platform,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain,literal
from windows_job import run_isolated
from test_inventory_reports_gui import fixture as seed
from test_inventory_movement_gui import durable,tree,project_by_id
from test_inventory_poe_face_gui import canonical

def inputs(dll,frontend):
    names=['test_inventory_reports_gui.py','test_inventory_read_views_gui.py','test_inventory_compensation_gui.py','test_inventory_movement_gui.py','test_inventory_poe_face_gui.py','pg_support.py']
    paths=[Path(__file__),*[Path(__file__).with_name(n) for n in names],ROOT/'tools/windows/windows_job.py',ROOT/'development/frontend/tests/browser-quince-support.mjs',ROOT/'development/frontend/tests/browser-rc9-excel.mjs',ROOT/'development/frontend/src/inventory-rc9-excel-reports.ts']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'server':tree(dll.parent),'frontend':tree(frontend)}

def fixture(lab,db,dll):
    ids,password=seed(lab,db,dll)
    ids.update(hostileRack='Rack 001 =+-@ Ω <img src="https://invalid.example/x" onerror="globalThis.xlsPwned=1">',literalLabel='001 =+-@ Ω🙂\t\r\n&lt;script&gt;',literalNote='=HYPERLINK("https://invalid.example/x") Ω🙂\r\n<script>globalThis.xlsPwned=1</script>')
    lab.sql(db,f"""BEGIN;
    UPDATE inventory_rack SET name={literal(ids['hostileRack'])} WHERE customer_id='{ids['customer']}';
    UPDATE inventory_port SET label={literal(ids['literalLabel'])} WHERE id='{ids['pa']}';
    UPDATE inventory_connection SET note={literal(ids['literalNote'])},properties=properties||'{{"createdAt":"2001-02-03T04:05:06Z"}}'::jsonb WHERE id='{ids['cable']}';
    UPDATE inventory_connection_endpoint SET port_id='{ids['pb']}' WHERE connection_id='{ids['roomCable']}' AND port_id='{ids['endPort']}';
    COMMIT;""",sensitive=True)
    ids['freePort']=lab.sql(db,f"SELECT id FROM inventory_port WHERE device_id='{ids['a']}' AND gn=3")
    return ids,password

def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--visual-only',action='store_true');args=p.parse_args()
    dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not(frontend/'app.js').is_file():raise RuntimeError('Complete explicit frozen artifacts required')
    args.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();lab=Lab('xls-html832')
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL','inputs':inputs(dll,frontend),'realQaAccessed':False,'productModified':False,'fixtureCreatedBy':('New synthetic SQL fixture; visual controls only, zero report commits' if args.visual_only else 'New synthetic SQL fixture; three report commits, no inventory writes'),'officeOpened':False,'visualOnly':args.visual_only}
    try:
        with lab:
            db=lab.create_database('xls_html832');ids,password=fixture(lab,db,dll);lab.grant_runtime(db);before=durable(lab,db)
            revisions=lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))")
            server=lab.start_server(db,dll=dll,frontend=frontend);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids));browser_started=time.monotonic()
            if args.visual_only:env['RACKCLICK_RC9_EXCEL_VISUAL_ONLY']='1'
            with(args.output/'browser-windows.log').open('wb')as log:done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-rc9-excel.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=240)
            report.update(browserExitCode=done.returncode,browserSeconds=round(time.monotonic()-browser_started,3))
            if done.returncode:raise RuntimeError('Browser failed; synthetic evidence retained')
            if args.visual_only:
                assert canonical(durable(lab,db))==canonical(before)
                assert revisions==lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))")
                assert lab.sql(db,"SELECT count(*) FROM operation WHERE result_json->>'kind'='rc9ExcelReport'")=='0'
                assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='reports.xlsHtml.generate'")=='0'
                report.update(sqlNineTablesUnchanged=True,allRevisionsUnchanged=True,reportOperations=0,reportAuditRows=0,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
            else:
                expected=json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'));reports=json.loads((args.output/'downloaded-rc9-excel-reports.json').read_text(encoding='utf-8'));assert len(reports)==3
                assert canonical(durable(lab,db))==canonical(before),'All nine inventory tables exactly unchanged'
                assert revisions==lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))")
                for result in reports:
                    r=result['report'];content=(args.output/'downloads'/result['requestId']/r['filename']).read_bytes();assert content==base64.b64decode(r['contentBase64']);assert len(content)==r['byteLength'] and hashlib.sha256(content).hexdigest()==r['sha256'];assert content.startswith(b'<!DOCTYPE html>') and not content.startswith(b'\xef\xbb\xbf')
                assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='reports.xlsHtml.generate'")=='3';assert lab.sql(db,"SELECT count(*) FROM operation WHERE result_json->>'kind'='rc9ExcelReport'")=='3'
                report.update(sqlNineTablesUnchanged=True,allRevisionsUnchanged=True,downloadsExactBytes=True,reportAuditRows=3,reportOperations=3)
                server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend)
                for username,result in zip(['move-admin','move-admin','move-second'],reports):
                    actor=Client(restarted);assert actor.login(username,password).status==200
                    status=actor.request('GET',f"/api/v1/customers/{ids['customer']}/reports/xls-html/operations/{result['requestId']}");assert status.status==200 and status.json()['operation']==result
                    actual=actor.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert actual.status==200 and project_by_id(actual.json())==project_by_id(expected)
                assert canonical(durable(lab,db))==canonical(before)
                report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll()is not None for s in lab.servers),finalInputs=inputs(dll,frontend));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items()if k not in['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS'and report['labStopped']and report['serversStopped']else 1
if __name__=='__main__':raise SystemExit(main())
