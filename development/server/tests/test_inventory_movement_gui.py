"""One isolated Windows Edge/PG movement path. Fixtures are SQL, writes under test GUI.

Explicit immutable --dll/--frontend are required; no build or real QA access.
"""
import argparse, hashlib, json, platform, secrets, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'development/server/tests'))
sys.path.insert(0, str(ROOT/'tools/windows'))
from pg_support import Lab, Client, literal, toolchain
from windows_job import run_isolated

TABLES = ['inventory_site','inventory_building','inventory_room','inventory_rack',
          'inventory_device','inventory_port_group','inventory_port',
          'inventory_connection','inventory_connection_endpoint']

def tree(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob('*')) if p.is_file()}

def inputs(dll, frontend):
    sources = [Path(__file__), ROOT/'development/frontend/tests/browser-inventory-movement.mjs',
               Path(__file__).with_name('pg_support.py'), ROOT/'tools/windows/windows_job.py']
    return {'sources': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            'server': tree(dll.parent), 'frontend': tree(frontend)}

def durable(lab, db):
    return {table: json.loads(lab.sql(db, f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM {table} t")) for table in TABLES}

def project_by_id(project):
    # Collection transport order is not identity. sortOrder itself stays compared.
    value = json.loads(json.dumps(project))
    for collection in ['sites','buildings','rooms','racks','devices','portGroups','ports','connections']:
        value[collection].sort(key=lambda row: row['id'])
    return value

def fixture(lab, db, dll):
    password = secrets.token_urlsafe(32)
    if lab.bootstrap(db, 'move-admin', password, dll=dll).returncode:
        raise RuntimeError('Synthetic bootstrap failed; raw logs private')
    house, admin = lab.sql(db, 'SELECT id FROM systemhaus; SELECT id FROM app_user').splitlines()
    ids = {key: str(uuid.uuid4()) for key in ['customer','other','rackA','rackB','a','b','c','ga','gb','gc','pa','pb','pc','pa2','pb2','pc2','cable','second','reader','technician','baseGroup','readerGroup','techGroup']}
    admin_group = lab.sql(db, f"SELECT group_id FROM user_group_member WHERE user_id='{admin}'")
    q = [f"INSERT INTO customer(id,systemhaus_id,name) VALUES('{ids['customer']}','{house}','Movement QA synthetic'),('{ids['other']}','{house}','Outside edit scope');",
         f"INSERT INTO inventory_rack(id,systemhaus_id,customer_id,name,size_u,location,properties) VALUES('{ids['rackA']}','{house}','{ids['customer']}','Rack origen',12,'Origen Ω','{{\"sentinel\":\"rack-a\"}}'),('{ids['rackB']}','{house}','{ids['customer']}','Rack destino',12,'Destino 東京','{{\"sentinel\":\"rack-b\"}}');"]
    for index, key in enumerate(['a','b','c']):
        rack = ids['rackA'] if key != 'c' else ids['rackB']
        order = 1 if key == 'b' else 0
        name = {'a':'Equipo móvil Ä','b':'Equipo origen B','c':'Equipo previo C'}[key]
        q.append(f"INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order,poe_budget,properties) VALUES('{ids[key]}','{house}','{ids['customer']}','rackEquipment','{rack}',{literal(name)},1,{order},90,'{{\"notes\":{{\"sn\":\"serial-{key}\",\"text\":\"literal <img> Ω\"}},\"color\":\"#123456\"}}');")
        q.append(f"INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order) VALUES('{ids['g'+key]}','{house}','{ids['customer']}','{ids[key]}','rj45','Grupo {key}','{key.upper()}',0);")
        for n in [1,2]:
            port = ids['p'+key+('2' if n == 2 else '')]
            q.append(f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,properties) VALUES('{port}','{house}','{ids['customer']}','{ids[key]}','{ids['g'+key]}','rj45',{n},{n-1},'Puerto {key}{n} Ω','free',true,17.5,'#654321','front','{{\"sentinel\":\"port-{key}{n}\"}}');")
    q.extend([f"INSERT INTO inventory_connection(id,systemhaus_id,customer_id,note,color,patch,properties) VALUES('{ids['cable']}','{house}','{ids['customer']}','Cable literal <img> 東京','#abcdef','tested','{{\"sentinel\":\"cable\"}}');",
              f"INSERT INTO inventory_connection_endpoint VALUES('{house}','{ids['customer']}','{ids['cable']}',0,'{ids['pa']}'),('{house}','{ids['customer']}','{ids['cable']}',1,'{ids['pb']}');"])
    for key, name in [('second','move-second'),('reader','move-reader'),('technician','move-technician')]:
        q.append(f"INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{ids[key]}',systemhaus_id,'{name}',password_hash FROM app_user WHERE id='{admin}';")
    q.append(f"INSERT INTO user_group_member VALUES('{house}','{ids['second']}','{admin_group}');")
    for key in ['baseGroup','readerGroup','techGroup']:
        q.append(f"INSERT INTO user_group VALUES('{ids[key]}','{house}','Synthetic {key}');")
    for user in ['reader','technician']:
        for group in ['baseGroup', 'readerGroup' if user == 'reader' else 'techGroup']:
            q.append(f"INSERT INTO user_group_member VALUES('{house}','{ids[user]}','{ids[group]}');")
    q.append(f"INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{house}','{ids['baseGroup']}','systemhaus.read',NULL,NULL);")
    for group in ['readerGroup','techGroup']:
        q.append(f"INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{house}','{ids[group]}','inventory.read','{ids['customer']}',NULL);")
    q.append(f"INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{house}','{ids['techGroup']}','inventory.edit','{ids['other']}',NULL);")
    lab.sql(db, 'BEGIN;\n'+'\n'.join(q)+'\nCOMMIT;', sensitive=True)
    return ids, password

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--frontend', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    dll, frontend = args.dll.resolve(strict=True), args.frontend.resolve(strict=True)
    if not dll.is_file() or not (frontend/'app.js').is_file(): raise RuntimeError('Complete explicit artifacts required')
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),
              'inputs':inputs(dll,frontend),'result':'FAIL','fixtureCreatedBy':'SQL; not GUI creation',
              'realQaAccessed':False,'productModified':False}
    started = time.monotonic(); lab = Lab('inventory-movement52')
    try:
        with lab:
            db = lab.create_database('movement52'); ids,password = fixture(lab,db,dll)
            lab.grant_runtime(db); before = durable(lab,db)
            server = lab.start_server(db,dll=dll,frontend=frontend)
            env = lab.environment(); env.update(RACKCLICK_TEST_ORIGIN=server.origin,
                RACKCLICK_TEST_USERNAME='move-admin', RACKCLICK_TEST_PASSWORD=password,
                RACKCLICK_TEST_OUTPUT=str(args.output.resolve()), RACKCLICK_FIXTURE=json.dumps(ids))
            browser_started = time.monotonic()
            with (args.output/'browser-windows.log').open('wb') as log:
                done = run_isolated([str(toolchain()['node']), str(ROOT/'development/frontend/tests/browser-inventory-movement.mjs')],
                                    env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=180)
            report['browserExitCode'] = done.returncode
            report['browserSeconds'] = round(time.monotonic()-browser_started,3)
            if done.returncode: raise RuntimeError('Browser failed; sanitized evidence retained')
            expected = json.loads((args.output/'expected-project.json').read_text(encoding='utf-8'))
            after = durable(lab,db); wanted = json.loads(json.dumps(before))
            for row in wanted['inventory_device']:
                if row['id'] == ids['a']: row.update(rack_id=ids['rackB'],sort_order=0)
                elif row['id'] == ids['b']: row['sort_order']=0
                elif row['id'] == ids['c']: row['sort_order']=1
            # SQL row aggregation sorts the full object; compare rows as multisets.
            canonical = lambda value: {k:sorted(json.dumps(r,sort_keys=True,ensure_ascii=False) for r in v) for k,v in value.items()}
            assert canonical(after) == canonical(wanted), 'Exact SQL identity/attributes/endpoints/rest preservation'
            report['sqlExactPlacementAndOrderOnly'] = True
            report['sqlTableRowCounts'] = {k:len(v) for k,v in before.items()}
            report['sqlBeforeSha256'] = hashlib.sha256(json.dumps(canonical(before),sort_keys=True).encode()).hexdigest()
            report['sqlAfterSha256'] = hashlib.sha256(json.dumps(canonical(after),sort_keys=True).encode()).hexdigest()
            admin = Client(server); assert admin.login('move-admin',password).status == 200
            for name,key in [('move-reader','reader'),('move-technician','technician')]:
                client = Client(server); assert client.login(name,password).status == 200
                assert client.request('GET',f"/api/v1/customers/{ids['customer']}/project").status == 200
                response = client.request('POST',f"/api/v1/customers/{ids['customer']}/commands",
                    {'type':'device.move','payload':{'id':ids['a'],'rackId':ids['rackA']}},
                    {'If-Match':f'"{expected["revision"]}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':ids[key]})
                assert response.status == 403, 'Server denies scoped/read-only write'
                assert client.request('GET',f"/api/v1/customers/{ids['other']}/project").status == 404
            assert canonical(durable(lab,db)) == canonical(after), 'Denied writes preserve inventory'
            report['permissionChecks'] = {'readerWrite':403,'technicianEditOtherCustomerWrite':403,'outsideRead':404,'inventoryUnchanged':True}
            server.close(); restarted = lab.start_server(db,dll=dll,frontend=frontend)
            restarted_admin = Client(restarted); assert restarted_admin.login('move-admin',password).status == 200
            persisted = restarted_admin.request('GET',f"/api/v1/customers/{ids['customer']}/project")
            assert persisted.status == 200, 'Restarted project read succeeds'
            assert persisted.headers.get('etag') == f'"{expected["revision"]}"', 'Restarted revision ETag'
            assert project_by_id(persisted.json()) == project_by_id(expected), 'Restarted exact project identities/attributes'
            assert canonical(durable(lab,db)) == canonical(after)
            report.update(serverRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'),result='PASS')
    except Exception as error:
        report.update(failureType=type(error).__name__,failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3),labStopped=not lab.running,
            serversStopped=all(s.process.poll() is not None for s in lab.servers),finalInputs=inputs(dll,frontend))
        report['inputsUnchanged'] = report['inputs'] == report['finalInputs']
        if not report['inputsUnchanged']: report['result']='FAIL_INPUTS_CHANGED'
        (args.output/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','finalInputs']},indent=2))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1

if __name__=='__main__': raise SystemExit(main())
