"""One fresh Windows/PG/Edge printable-report scenario, explicit frozen artifacts; no real QA."""
import argparse,base64,hashlib,json,platform,sys,time
from datetime import datetime,timezone
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain,literal
from windows_job import run_isolated
from test_inventory_reports_gui import fixture as seed
from test_inventory_movement_gui import durable,tree,project_by_id
from test_inventory_poe_face_gui import canonical

def inputs(dll,frontend):
    paths=[Path(__file__),*[Path(__file__).with_name(n) for n in ['test_inventory_reports_gui.py','test_inventory_read_views_gui.py','test_inventory_compensation_gui.py','test_inventory_movement_gui.py','test_inventory_poe_face_gui.py','pg_support.py']],ROOT/'tools/windows/windows_job.py',ROOT/'development/frontend/tests/browser-quince-support.mjs',ROOT/'development/frontend/tests/browser-inventory-printable-reports.mjs']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'server':tree(dll.parent),'frontend':tree(frontend)}

def fixture(lab,db,dll):
    ids,password=seed(lab,db,dll)
    ids.update(hostileRack='Rack <img src="https://invalid.example/x" onerror="globalThis.printPwned=1"> Ω',hostileLabel='<img src="https://invalid.example/x" onerror="globalThis.printPwned=1"> Ω',hostileNote='<script>globalThis.printPwned=1</script> Ω\r\n東京')
    lab.sql(db,f"""BEGIN;
    UPDATE inventory_rack SET name={literal(ids['hostileRack'])} WHERE customer_id='{ids['customer']}';
    UPDATE inventory_port SET label={literal(ids['hostileLabel'])} WHERE id='{ids['pa']}';
    UPDATE inventory_connection SET note={literal(ids['hostileNote'])} WHERE id='{ids['cable']}';
    COMMIT;""",sensitive=True)
    return ids,password

class PassiveHtml(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.rows=0;self.active=[]
    def handle_starttag(self,tag,attrs):
        if tag in ['script','iframe','object','embed','img','form','link','svg']:self.active.append(tag)
        for key,value in attrs:
            if key.startswith('on') or key in ['src','href','srcdoc','action']:self.active.append(key)
            if key=='data-report-row':self.rows+=1

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--frontend',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file():raise RuntimeError('Complete explicit artifacts required')
    args.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();lab=Lab('printable113')
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL','inputs':inputs(dll,frontend),'realQaAccessed':False,'productModified':False,'fixtureCreatedBy':'SQL; synthetic only','pdfSource':'Edge Page.printToPDF; not server generation'}
    try:
        with lab:
            db=lab.create_database('printable113');ids,password=fixture(lab,db,dll);lab.grant_runtime(db);before=durable(lab,db);server=lab.start_server(db,dll=dll,frontend=frontend)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            with (args.output/'browser-windows.log').open('wb') as log:
                done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-inventory-printable-reports.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=240)
            report['browserExitCode']=done.returncode
            if done.returncode:raise RuntimeError('Browser failed; evidence retained')
            expected=json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'));assert canonical(durable(lab,db))==canonical(before),'All nine inventory tables exactly unchanged'
            reports=json.loads((args.output/'downloaded-printable-reports.json').read_text(encoding='utf-8'));assert len(reports)==3
            for result in reports:
                r=result['report'];content=(args.output/'downloads'/r['filename']).read_bytes();assert content==base64.b64decode(r['contentBase64']);assert len(content)==r['byteLength'] and hashlib.sha256(content).hexdigest()==r['sha256'];assert content.startswith(b'<!doctype html>') and not content.startswith(b'\xef\xbb\xbf')
                parsed=PassiveHtml();parsed.feed(content.decode('utf-8'));assert parsed.rows==r['rowCount'] and not parsed.active
                assert (args.output/(r['reportKind']+'-browser-print.pdf')).read_bytes().startswith(b'%PDF-')
                metrics=json.loads((args.output/(r['reportKind']+'-print-metrics.json')).read_text(encoding='utf-8'));assert metrics['mediaPrint'] and metrics['viewportWidth']==703 and metrics['documentWidth']<=704
                assert metrics['horizontalCellOverflow']==0 and metrics['verticalCellClipping']==0 and metrics['hiddenPortRows']==0
                if r['reportKind']!='rackLabels':
                    device_ids={d['id'] for d in expected['devices'] if r['reportKind']=='client' or d['rackId']==r['rackIds'][0]}
                    port_ids=sorted(p['id'] for p in expected['ports'] if p['deviceId'] in device_ids)
                    assert sorted(metrics['portRowIds'])==port_ids and len(metrics['portColumnWidths'])==4
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='reports.printable.generate'")=='3'
            assert lab.sql(db,"SELECT count(*) FROM operation WHERE result_json->>'kind'='report'")=='3'
            report.update(sqlNineTablesUnchanged=True,downloadsExactBytes=True,passiveHtmlParsed=True,a4PrintWidthPixels=703,allPortIdsInPrint=True,noPrintCellClipping=True,reportAuditRows=3,reportOperations=3)
            server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend);admin=Client(restarted);assert admin.login('move-admin',password).status==200
            actual=admin.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert actual.status==200 and project_by_id(actual.json())==project_by_id(expected);assert canonical(durable(lab,db))==canonical(before)
            for r in reports:
                status=admin.request('GET',f"/api/v1/customers/{ids['customer']}/reports/printable/operations/{r['requestId']}");assert status.status==200 and status.json()['operation']==r
            report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,frontend));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
