"""One isolated Windows/PG XLSX scenario with explicit frozen artifacts; no real QA."""
import argparse,base64,hashlib,io,json,platform,sys,time,uuid,zipfile,re
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,toolchain,literal
from windows_job import run_isolated
from test_inventory_read_views_gui import fixture as seed
from test_inventory_movement_gui import durable,tree,project_by_id
from test_inventory_poe_face_gui import canonical

def inputs(dll,frontend):
    paths=[Path(__file__),Path(__file__).with_name('test_inventory_read_views_gui.py'),Path(__file__).with_name('test_inventory_compensation_gui.py'),Path(__file__).with_name('test_inventory_movement_gui.py'),Path(__file__).with_name('pg_support.py'),Path(__file__).with_name('test_inventory_reports_gui.py'),ROOT/'tools/windows/windows_job.py',ROOT/'development/frontend/tests/browser-quince-support.mjs',ROOT/'development/frontend/tests/browser-inventory-spreadsheet-reports.mjs']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'server':tree(dll.parent),'frontend':tree(frontend)}

def fixture(lab,db,dll):
    ids,password=seed(lab,db,dll)
    lab.sql(db,f"""BEGIN;
    UPDATE inventory_port SET label={literal('=SUM(1,2) Ω')} WHERE id='{ids['pa']}';
    UPDATE inventory_port SET label={literal("'literal Ω\r\n東京")} WHERE id='{ids['pa2']}';
    UPDATE inventory_port SET label={literal('\t=HYPERLINK Ω')} WHERE id='{ids['endPort']}';
    INSERT INTO permission_grant(id,systemhaus_id,user_group_id,capability,customer_id)
      SELECT '{uuid.uuid4()}',systemhaus_id,'{ids['techGroup']}','inventory.edit','{ids['customer']}' FROM customer WHERE id='{ids['customer']}';
    INSERT INTO permission_grant(id,systemhaus_id,user_group_id,capability,customer_id)
      SELECT '{uuid.uuid4()}',u.systemhaus_id,m.group_id,'reports.export','{ids['customer']}' FROM app_user u JOIN user_group_member m ON m.user_id=u.id
      WHERE u.username='move-admin' AND NOT EXISTS(SELECT 1 FROM permission_grant p WHERE p.user_group_id=m.group_id AND p.capability='reports.export');
    COMMIT;""",sensitive=True)
    return ids,password


def workbook_rows(content):
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        assert set(z.namelist())=={'[Content_Types].xml','_rels/.rels','xl/workbook.xml','xl/_rels/workbook.xml.rels','xl/worksheets/sheet1.xml'}
        assert z.testzip() is None and all(i.compress_type==0 for i in z.infolist())
        sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        assert not sheet.findall('.//s:f',ns)
        def decode(text):
            return re.sub(r'_x([0-9A-Fa-f]{4})_',lambda m:chr(int(m[1],16)),text or '')
        return [[decode(c.find('s:is/s:t',ns).text) for c in row] for row in sheet.find('s:sheetData',ns)]

def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file():raise RuntimeError('Complete explicit artifacts required')
    args.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();lab=Lab('xlsx397')
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'result':'FAIL','inputs':inputs(dll,frontend),'realQaAccessed':False,'productModified':False,'fixtureCreatedBy':'SQL; synthetic only'}
    try:
        with lab:
            db=lab.create_database('xlsx397');ids,password=fixture(lab,db,dll);lab.grant_runtime(db);before=durable(lab,db);server=lab.start_server(db,dll=dll,frontend=frontend)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            with (args.output/'browser-windows.log').open('wb') as log:
                done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-inventory-spreadsheet-reports.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=180)
            report['browserExitCode']=done.returncode
            if done.returncode:raise RuntimeError('Browser failed; evidence retained')
            expected=json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'));assert canonical(durable(lab,db))==canonical(before),'All nine inventory tables exactly unchanged'
            report['sqlNineTablesUnchanged']=True
            reports=json.loads((args.output/'downloaded-reports.json').read_text(encoding='utf-8'));assert len(reports)==2
            for result in reports:
                r=result['report'];content=(args.output/'downloads'/r['filename']).read_bytes();assert content==base64.b64decode(r['contentBase64']);assert len(content)==r['byteLength'] and hashlib.sha256(content).hexdigest()==r['sha256'];assert content.startswith(b'PK\x03\x04')
                rows=workbook_rows(content);assert len(rows)==r['rowCount']+1
                if r['reportKind']=='ports':
                    labels={row[2]:row[rows[0].index('label')] for row in rows[1:]}
                    assert labels[ids['pa']]=='=SUM(1,2) Ω' and labels[ids['pa2']]=="'literal Ω\r\n東京"
                else:
                    assert len(rows)==3 and 'from_port_id' in rows[0] and 'to_port_id' in rows[0]
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='reports.xlsx.generate'")=='2'
            assert lab.sql(db,"SELECT count(*) FROM operation WHERE result_json->>'kind'='spreadsheetReport'")=='2'
            report.update(downloadsExactBytes=True,reportAuditRows=2,reportOperations=2)
            server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend);admin=Client(restarted);assert admin.login('move-admin',password).status==200
            actual=admin.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert actual.status==200 and project_by_id(actual.json())==project_by_id(expected);assert canonical(durable(lab,db))==canonical(before)
            for r in reports:
                status=admin.request('GET',f"/api/v1/customers/{ids['customer']}/reports/xlsx/operations/{r['requestId']}");assert status.status==200 and status.json()['operation']==r
            report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,frontend));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
