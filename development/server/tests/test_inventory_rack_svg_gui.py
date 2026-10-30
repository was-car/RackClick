"""One NEW Windows/PG/Edge rack SVG scenario; explicit frozen pair, no build or real QA."""
import argparse,base64,hashlib,json,platform,sys,time,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain,literal
from windows_job import run_isolated
from test_inventory_printable_reports_gui import fixture as seed
from test_inventory_movement_gui import durable,tree,project_by_id
from test_inventory_poe_face_gui import canonical

def inputs(dll,frontend):
    names=['test_inventory_printable_reports_gui.py','test_inventory_reports_gui.py','test_inventory_read_views_gui.py','test_inventory_compensation_gui.py','test_inventory_movement_gui.py','test_inventory_poe_face_gui.py','pg_support.py']
    paths=[Path(__file__),*[Path(__file__).with_name(n) for n in names],ROOT/'tools/windows/windows_job.py',ROOT/'development/frontend/tests/browser-quince-support.mjs',ROOT/'development/frontend/tests/browser-inventory-rack-svg.mjs']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'server':tree(dll.parent),'frontend':tree(frontend)}

def fixture(lab,db,dll):
    ids,password=seed(lab,db,dll)
    ids.update(longCustomer=('Cliente Ω '+'漢🙂'*100)[:100],longDevice=('Equipo Ω '+'長🙂'*100)[:100],hostileRack=('Rack Ω <img src="https://invalid.example/x" onerror="globalThis.svgPwned=1"> '+'漢🙂'*100)[:100])
    lab.sql(db,f"""BEGIN;
    UPDATE customer SET name={literal(ids['longCustomer'])} WHERE id='{ids['customer']}';
    UPDATE inventory_rack SET name={literal(ids['hostileRack'])} WHERE customer_id='{ids['customer']}';
    UPDATE inventory_device SET name={literal(ids['longDevice'])} WHERE id='{ids['a']}';
    UPDATE inventory_port SET face='rear',status='reserved',poe=false,watts=17.5 WHERE id='{ids['pa']}';
    UPDATE inventory_port SET face='front',status='disabled',poe=true,watts=0 WHERE id='{ids['pa2']}';
    UPDATE inventory_port SET face='front',status='free',poe=true,watts=3.5 WHERE id='{ids['pb']}';
    UPDATE inventory_port SET face='rear',status='faulty',poe=false,watts=NULL WHERE id='{ids['pb2']}';
    UPDATE inventory_device SET properties=jsonb_set(properties,'{{preset}}','"Server"'::jsonb) WHERE id='{ids['a']}';
    COMMIT;""",sensitive=True)
    return ids,password

def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not(frontend/'app.js').is_file():raise RuntimeError('Complete explicit frozen artifacts required')
    args.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();lab=Lab('rack-svg158')
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL','inputs':inputs(dll,frontend),'realQaAccessed':False,'productModified':False,'fixtureCreatedBy':'New synthetic SQL fixture; three SVG commits and one personal favorite through GUI'}
    try:
        with lab:
            db=lab.create_database('rack_svg158');ids,password=fixture(lab,db,dll);lab.grant_runtime(db);before=durable(lab,db)
            revisions=lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))")
            server=lab.start_server(db,dll=dll,frontend=frontend);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids));browser_started=time.monotonic()
            with(args.output/'browser-windows.log').open('wb')as log:done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-inventory-rack-svg.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=240)
            report.update(browserExitCode=done.returncode,browserSeconds=round(time.monotonic()-browser_started,3))
            if done.returncode:raise RuntimeError('Browser failed; synthetic evidence retained')
            expected=json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'));personal=json.loads((args.output/'expected-favorites.json').read_text(encoding='utf-8'));reports=json.loads((args.output/'downloaded-rack-svg-reports.json').read_text(encoding='utf-8'));assert len(reports)==3
            assert canonical(durable(lab,db))==canonical(before),'All nine inventory tables exactly unchanged'
            assert revisions==lab.sql(db,"SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))")
            for result in reports:
                r=result['report'];content=(args.output/'downloads'/r['filename']).read_bytes();assert content==base64.b64decode(r['contentBase64']);assert len(content)==r['byteLength'] and hashlib.sha256(content).hexdigest()==r['sha256'];assert not content.startswith(b'\xef\xbb\xbf');root=ET.fromstring(content)
                assert root.tag=='{http://www.w3.org/2000/svg}svg' and root.attrib['data-rack-id']==r['rackId'] and root.attrib['data-face']==r['face'];rows=[e for e in root.iter()if'data-report-row'in e.attrib];assert len(rows)==r['rowCount'] and len({(e.attrib['data-report-row'],e.attrib['data-id'])for e in rows})==len(rows)
                assert all(e.tag.rsplit('}',1)[-1]in['svg','title','desc','g','rect','circle','path','text']for e in root.iter())
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='reports.rackSvg.generate'")=='3';assert lab.sql(db,"SELECT count(*) FROM operation WHERE result_json->'report'->>'reportKind'='rackSvg'")=='3'
            assert lab.sql(db,"SELECT count(*) FROM user_catalog_favorite_operation WHERE state='committed'")=='1'
            report.update(sqlNineTablesUnchanged=True,allRevisionsUnchanged=True,downloadsExactBytes=True,passiveXmlParsed=True,reportAuditRows=3,reportOperations=3,favoriteCommits=1)
            server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend);admin=Client(restarted);assert admin.login('move-admin',password).status==200
            actual=admin.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert actual.status==200 and project_by_id(actual.json())==project_by_id(expected)
            assert canonical(durable(lab,db))==canonical(before)
            assert admin.request('GET',f"/api/v1/customers/{ids['customer']}/catalog/favorites").json()==personal
            for r in reports:
                status=admin.request('GET',f"/api/v1/customers/{ids['customer']}/reports/rack-svg/operations/{r['requestId']}");assert status.status==200 and status.json()['operation']==r
            report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll()is not None for s in lab.servers),finalInputs=inputs(dll,frontend));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items()if k not in['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS'and report['labStopped']and report['serversStopped']else 1
if __name__=='__main__':raise SystemExit(main())
