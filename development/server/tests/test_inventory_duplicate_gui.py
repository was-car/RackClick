"""One isolated rack-duplication GUI path plus bounded atomic/permission negatives.

Requires complete immutable artifacts. Imports52 helpers without running its main.
SQL fixtures are not GUI creation. Never accesses existing QA laboratories.
"""
import argparse, hashlib, json, platform, secrets, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/server/tests'))
sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab, Client, toolchain
from windows_job import run_isolated
from test_inventory_movement_gui import fixture as seed52, durable, tree, project_by_id

def inputs(dll,frontend):
    sources=[Path(__file__),Path(__file__).with_name('test_inventory_movement_gui.py'),
             Path(__file__).with_name('pg_support.py'),ROOT/'tools/windows/windows_job.py',
             ROOT/'development/frontend/tests/browser-inventory-duplicate.mjs']
    return {'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            'server':tree(dll.parent),'frontend':tree(frontend)}

def canonical(value):
    return {k:sorted(json.dumps(row,sort_keys=True,ensure_ascii=False) for row in rows) for k,rows in value.items()}

def atomic_state(lab,db):
    value=durable(lab,db)
    for table in ['customer','operation','audit_event']:
        value[table]=json.loads(lab.sql(db,f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM {table} t"))
    return canonical(value)

def fixture(lab,db,dll):
    ids,password=seed52(lab,db,dll)
    house=lab.sql(db,'SELECT id FROM systemhaus')
    ids.update(externalCable=str(uuid.uuid4()),extraGroup=str(uuid.uuid4()),extraPort=str(uuid.uuid4()))
    lab.sql(db,f"""BEGIN;
      UPDATE customer SET name='Duplicate QA synthetic' WHERE id='{ids['customer']}';
      UPDATE inventory_rack SET name='Rack fuente' WHERE id='{ids['rackA']}';
      UPDATE inventory_rack SET name='Rack externo' WHERE id='{ids['rackB']}';
      UPDATE inventory_device SET name='Equipo fuente A' WHERE id='{ids['a']}';
      UPDATE inventory_device SET name='Equipo fuente B' WHERE id='{ids['b']}';
      UPDATE inventory_device SET name='Equipo externo C' WHERE id='{ids['c']}';
      INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order)
      VALUES('{ids['extraGroup']}','{house}','{ids['customer']}','{ids['a']}','rj45','Grupo adicional','X',1);
      INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,properties)
      VALUES('{ids['extraPort']}','{house}','{ids['customer']}','{ids['a']}','{ids['extraGroup']}','rj45',1,0,'Extra Ω <img>','reserved',false,0,'#876543','rear','{{"sentinel":"extra-group-same-gn"}}');
      INSERT INTO inventory_connection(id,systemhaus_id,customer_id,note,color,patch,properties)
      VALUES('{ids['externalCable']}','{house}','{ids['customer']}','External unchanged Ω','#654321','planned','{{"sentinel":"external-cable"}}');
      INSERT INTO inventory_connection_endpoint VALUES
      ('{house}','{ids['customer']}','{ids['externalCable']}',0,'{ids['pa2']}'),
      ('{house}','{ids['customer']}','{ids['externalCable']}',1,'{ids['pc']}');
      COMMIT;""",sensitive=True)
    return ids,password

def assert_sql_copy(before,after,ids,mapping):
    """Every old row exact; new rows are exact mapped copies except new cable time."""
    expected=json.loads(json.dumps(before));new_id=mapping['rackId']
    maps={key:mapping[key] for key in ['devices','groups','ports']}
    all_old={row['id'] for rows in before.values() for row in rows if 'id' in row}
    all_new=[new_id,*maps['devices'].values(),*maps['groups'].values(),*maps['ports'].values(),mapping['connectionId']]
    assert len(all_new)==len(set(all_new)) and not set(all_new)&all_old,'All cloned UUIDs new and unique'
    wanted_counts={'inventory_site':0,'inventory_building':0,'inventory_room':0,'inventory_rack':1,
                   'inventory_device':2,'inventory_port_group':3,'inventory_port':5,'inventory_connection':1,'inventory_connection_endpoint':2}
    for table,count in wanted_counts.items():assert len(after[table])==len(before[table])+count,table+' exact additions'
    def find(table,id):return next(row for row in before[table] if row['id']==id)
    rack=dict(find('inventory_rack',ids['rackA']),id=new_id,name='Copia Ω <img>')
    expected['inventory_rack'].append(rack)
    old_devices=[row for row in before['inventory_device'] if row['rack_id']==ids['rackA']]
    assert set(maps['devices'])=={row['id'] for row in old_devices}
    for row in old_devices:expected['inventory_device'].append(dict(row,id=maps['devices'][row['id']],rack_id=new_id))
    old_groups=[row for row in before['inventory_port_group'] if row['device_id'] in maps['devices']]
    assert set(maps['groups'])=={row['id'] for row in old_groups}
    for row in old_groups:expected['inventory_port_group'].append(dict(row,id=maps['groups'][row['id']],device_id=maps['devices'][row['device_id']]))
    old_ports=[row for row in before['inventory_port'] if row['device_id'] in maps['devices']]
    assert set(maps['ports'])=={row['id'] for row in old_ports}
    for row in old_ports:expected['inventory_port'].append(dict(row,id=maps['ports'][row['id']],device_id=maps['devices'][row['device_id']],group_id=maps['groups'][row['group_id']]))
    source=find('inventory_connection',ids['cable'])
    copied=next(row for row in after['inventory_connection'] if row['id']==mapping['connectionId'])
    assert datetime.fromisoformat(copied['created_at'])>=datetime.fromisoformat(source['created_at']),'New cable has a valid new creation time'
    expected['inventory_connection'].append(dict(source,id=mapping['connectionId'],created_at=copied['created_at']))
    endpoints=[row for row in before['inventory_connection_endpoint'] if row['connection_id']==ids['cable']]
    assert len(endpoints)==2
    for row in endpoints:expected['inventory_connection_endpoint'].append(dict(row,connection_id=mapping['connectionId'],port_id=maps['ports'][row['port_id']]))
    assert canonical(after)==canonical(expected),'Every SQL attribute/relationship/original/foreign row exact'
    return wanted_counts

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True)
    parser.add_argument('--frontend',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();dll=args.dll.resolve(strict=True);frontend=args.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file():raise RuntimeError('Explicit complete artifacts required')
    args.output.mkdir(parents=True,exist_ok=False)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'inputs':inputs(dll,frontend),
            'result':'FAIL','realQaAccessed':False,'productModified':False,'fixtureCreatedBy':'SQL; not GUI creation'}
    started=time.monotonic();lab=Lab('inventory-duplicate53')
    try:
        with lab:
            db=lab.create_database('duplicate53');ids,password=fixture(lab,db,dll);lab.grant_runtime(db)
            before=durable(lab,db);server=lab.start_server(db,dll=dll,frontend=frontend)
            env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='move-admin',
                RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),RACKCLICK_FIXTURE=json.dumps(ids))
            tick=time.monotonic()
            with (args.output/'browser-windows.log').open('wb') as log:
                done=run_isolated([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-inventory-duplicate.mjs')],
                                  env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=150)
            report.update(browserExitCode=done.returncode,browserSeconds=round(time.monotonic()-tick,3))
            if done.returncode:raise RuntimeError('Browser failed; sanitized evidence retained')
            mapping=json.loads((args.output/'duplicate-map.json').read_text(encoding='utf-8'))
            expected=json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'))
            after=durable(lab,db)
            report['exactSqlAdditions']=assert_sql_copy(before,after,ids,mapping)
            report['sqlSourceExternalAndRemappingExact']=True
            admin=Client(server);assert admin.login('move-admin',password).status==200
            actor=lab.sql(db,"SELECT id FROM app_user WHERE username='move-admin'")
            def command(payload,client=admin,user=actor):
                return client.request('POST',f"/api/v1/customers/{ids['customer']}/commands",{'type':'rack.duplicate','payload':payload},
                    {'If-Match':f'"{expected["revision"]}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':user})
            report['atomicNegatives']=[]
            for status,confirmed,error in [('reserved',[],'reserved_confirmation_required'),
                    ('reserved',[ids['pc']],'reserved_confirmation_required'),('disabled',[],'port_blocked'),('faulty',[],'port_blocked')]:
                lab.sql(db,f"UPDATE inventory_port SET status='{status}' WHERE id='{ids['pa']}'")
                original=atomic_state(lab,db)
                response=command({'id':ids['rackA'],'name':'Rejected copy','includeConnections':True,'confirmedReservedPortIds':confirmed})
                assert response.status==409 and response.json()['error']==error,'Expected bounded duplicate refusal '+status
                assert atomic_state(lab,db)==original,'Refusal leaves no rack/device/port/cable/revision/operation/audit remnants'
                report['atomicNegatives'].append({'status':status,'confirmation':'wrong external UUID' if confirmed else 'empty','http':409,'error':error,'unchanged':True})
            lab.sql(db,f"UPDATE inventory_port SET status='free' WHERE id='{ids['pa']}'")
            assert canonical(durable(lab,db))==canonical(after),'SQL negative fixtures restored exactly'
            report['permissionChecks']=[]
            for name,key in [('move-reader','reader'),('move-technician','technician')]:
                client=Client(server);assert client.login(name,password).status==200
                original=atomic_state(lab,db)
                response=command({'id':ids['rackA'],'name':'Forbidden copy','includeConnections':True},client,ids[key])
                assert response.status==403 and atomic_state(lab,db)==original,'Server forbids ungranted duplicate without remnants'
                assert client.request('GET',f"/api/v1/customers/{ids['other']}/project").status==404
                report['permissionChecks'].append({'user':name,'write':403,'outsideRead':404,'unchanged':True})
            # Source UUID sent in a different customer is never resolved across scope.
            other_revision=admin.request('GET',f"/api/v1/customers/{ids['other']}/project").json()['revision']
            original=atomic_state(lab,db)
            response=admin.request('POST',f"/api/v1/customers/{ids['other']}/commands",{'type':'rack.duplicate','payload':{'id':ids['rackA'],'includeConnections':True}},
                {'If-Match':f'"{other_revision}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor})
            assert response.status==404 and atomic_state(lab,db)==original,'Source UUID cannot be duplicated into another customer'
            report['crossCustomerDuplicate']={'http':404,'unchanged':True}
            server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend)
            read=Client(restarted);assert read.login('move-admin',password).status==200
            persisted=read.request('GET',f"/api/v1/customers/{ids['customer']}/project")
            assert persisted.status==200 and persisted.headers['etag']==f'"{expected["revision"]}"'
            assert project_by_id(persisted.json())==project_by_id(expected),'Restart preserves complete cloned project'
            assert canonical(durable(lab,db))==canonical(after),'Restart preserves all inventory SQL rows'
            report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,
            serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,frontend))
        report['inputsUnchanged']=report['inputs']==report['finalInputs']
        if not report['inputsUnchanged']:report['result']='FAIL_INPUTS_CHANGED'
        (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1
if __name__=='__main__':raise SystemExit(main())
