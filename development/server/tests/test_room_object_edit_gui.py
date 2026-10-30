"""Edicion GUI de Dose y dispositivo final de sala: laboratorio PG nuevo, datos sinteticos, solo entradas del laboratorio.

Comprueba por GUI nombre/notas y el estado de un puerto por objeto; luego BD, otra cuenta autorizada, recarga, rechazos de
usuarios sin permiso y persistencia tras reiniciar el servidor. No toca VM, QA ni instaladores.
"""
import argparse,hashlib,json,platform,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'development/server/tests'));sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab,Client,literal,toolchain
from windows_job import run_isolated
from test_room_device_move_gui import fixture as move_fixture
from test_inventory_movement_gui import durable,project_by_id,tree,TABLES
from test_inventory_duplicate_gui import atomic_state

NAMES={'dose':'Dose editada literal <img> Ω 東京','end':'Dispositivo final editado literal <img> Ω'}
SNS={'dose':'serial-dose-editado','end':'serial-end-editado'}
NOTES={'dose':'nota editada de dose Ω','end':'nota editada de end 東京'}
PORT_STATUS='reserved'

def inputs(dll,front):
    files=[Path(__file__),ROOT/'development/frontend/tests/browser-room-object-edit.mjs',ROOT/'development/frontend/tests/browser-client-changes-support.mjs',Path(__file__).with_name('test_room_device_move_gui.py'),Path(__file__).with_name('test_client_changes_gui.py'),Path(__file__).with_name('test_inventory_duplicate_gui.py'),Path(__file__).with_name('test_inventory_movement_gui.py'),Path(__file__).with_name('pg_support.py'),ROOT/'tools/windows/windows_job.py']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'server':tree(dll.parent),'frontend':tree(front)}

def canonical(data):
    return {k:sorted(json.dumps(r,sort_keys=True) for r in rows) for k,rows in data.items()}

def rows_by_id(data,table):
    return {r['id']:r for r in data[table]}

def check_database(before,after,ids):
    wanted=json.loads(json.dumps(before))
    for key in ['dose','end']:
        row=next(r for r in wanted['inventory_device'] if r['id']==ids[key])
        row['name']=NAMES[key]
        notes=row['properties'].setdefault('notes',{})
        notes.update(sn=SNS[key],text=NOTES[key])
        for field in ['model','ip','firmware']:notes.setdefault(field,'')
    for row in wanted['inventory_port']:
        if row['id'] in (ids['pdose'],ids['pend']):row['status']=PORT_STATUS
    assert canonical(after)==canonical(wanted),'Exact nine tables, including all unedited properties/notes/UUIDs/cables'


def audit_counts(lab,db):
    return json.loads(lab.sql(db,"SELECT COALESCE(jsonb_object_agg(action,n),'{}') FROM (SELECT action,count(*) n FROM audit_event GROUP BY action) q"))


def audit_delta(before,after):
    return {key:after.get(key,0)-before.get(key,0) for key in before.keys()|after.keys() if after.get(key,0)!=before.get(key,0)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    dll=a.dll.resolve(strict=True);front=a.frontend.resolve(strict=True);a.output.mkdir(parents=True,exist_ok=False)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'inputs':inputs(dll,front),'result':'FAIL','realQaAccessed':False,'fixtureCreatedBy':'SQL synthetic inventory/accounts from move-test fixture; edited only through GUI'}
    lab=Lab('room-object-edit-gui');tick=time.monotonic()
    try:
        with lab:
            db=lab.create_database('room-object-edit-gui');ids,password=move_fixture(lab,db,dll);lab.grant_runtime(db)
            # Strengthen the fixture: known unedited notes and unrelated metadata must survive GUI edits.
            for key in ['dose','end']:
                props=json.loads(lab.sql(db,f"SELECT properties FROM inventory_device WHERE id='{ids[key]}'"))
                props.update(color='#a1b2c3',fixtureSentinel={'kind':key,'nested':['retain',17]})
                props['notes'].update(model='model-'+key,ip='192.0.2.17',firmware='firmware-'+key)
                lab.sql(db,f"UPDATE inventory_device SET properties={literal(json.dumps(props))}::jsonb WHERE id='{ids[key]}'",sensitive=True)
            before=durable(lab,db);audit_before=audit_counts(lab,db)
            server=lab.start_server(db,dll=dll,frontend=front)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(a.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            with (a.output/'browser.log').open('wb') as log:
                done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-room-object-edit.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=300)
            report['browserExitCode']=done.returncode
            if done.returncode:raise RuntimeError('Browser scenario failed; evidence retained')
            expected=json.loads((a.output/'expected-project.json').read_text(encoding='utf-8'))
            after=durable(lab,db);check_database(before,after,ids);report['databaseEditsOnlyNameNotesAndPortStatus']=True
            audit_after=audit_counts(lab,db);delta=audit_delta(audit_before,audit_after)
            assert delta=={'inventory.device.update':2,'inventory.ports.update':2,'user.preference.set':1},delta
            assert lab.sql(db,'SELECT count(*) FROM operation').strip()=='4'
            report.update(auditActionsAdded=delta,inventoryCommandAuditEvents=4,languagePreferenceAuditEvents=1,inventoryOperationRows=4)
            admin=Client(server);assert admin.login('move-admin',password).status==200
            route=f"/api/v1/customers/{ids['customer']}/commands"
            def command(client,payload):
                return client.request('POST',route,{'type':'device.update','payload':payload},{'If-Match':f'"{expected["revision"]}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':client.request('GET','/api/v1/me').json()['user']['id']})
            negatives={}
            revision_pre_neg=admin.request('GET',f"/api/v1/customers/{ids['customer']}/project").json()['revision']
            audit_pre_neg=int(lab.sql(db,'SELECT count(*) FROM audit_event').strip());state_pre_neg=canonical(durable(lab,db));atomic_pre_neg=atomic_state(lab,db)
            for user,status in [('move-reader',403),('notice-outsider',404)]:
                client=Client(server);assert client.login(user,password).status==200
                response=command(client,{'id':ids['dose'],'name':'intento sin permiso'})
                assert response.status==status,(user,response.status);negatives[user]=response.status
            response=command(admin,{'id':ids['dose'],'name':''});assert response.status==422,response.status;negatives['emptyName']=response.status
            assert canonical(durable(lab,db))==state_pre_neg,'rejected commands leave the nine tables intact'
            assert int(lab.sql(db,'SELECT count(*) FROM audit_event').strip())==audit_pre_neg,'rejected commands add no audit event'
            assert admin.request('GET',f"/api/v1/customers/{ids['customer']}/project").json()['revision']==revision_pre_neg,'rejected commands keep the revision'
            assert atomic_state(lab,db)==atomic_pre_neg,'rejected commands leave exact customer/operation/audit rows unchanged'
            report['rejectedAtomicStateUnchanged']=True
            report['revisionUnchangedByRejections']=True
            server.close();restart=lab.start_server(db,dll=dll,frontend=front)
            reader=Client(restart);assert reader.login('move-reader',password).status==200
            response=reader.request('GET',f"/api/v1/customers/{ids['customer']}/project");assert response.status==200
            assert project_by_id(response.json())==project_by_id(expected),'persisted project after restart matches the GUI state'
            assert canonical(durable(lab,db))==canonical(after),'database unchanged by reads after restart'
            report.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version').strip(),negativeStatuses=negatives,restartPersistence=True,sqlRowCounts={k:len(v) for k,v in after.items()})
    except Exception as e:report.update(failureType=type(e).__name__,failure=str(e))
    finally:
        report.update(seconds=round(time.monotonic()-tick,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,front));report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (a.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1

if __name__=='__main__':raise SystemExit(main())
