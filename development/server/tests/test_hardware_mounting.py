"""New PG17/Windows laboratory. Hardware creation uses the existing HTTP command transaction.

No QA/VM/installed database, passwords or key stores are accessed. Private raw logs stay in .local.
"""
import argparse, concurrent.futures, hashlib, json, secrets, subprocess, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'development/server/tests'))
from pg_support import Lab, Client, literal

TABLES = ['customer','inventory_rack','inventory_device','inventory_port_group','inventory_port',
          'inventory_connection','inventory_connection_endpoint','operation','audit_event']

def state(lab, db, legacy=False):
    def row(table):return "to_jsonb(t)-ARRAY['hardware_profile_key','mount_parent_id','mount_slot_key']" if legacy and table=='inventory_device' else 'to_jsonb(t)'
    values = {table:lab.sql(db, f"SELECT COALESCE(jsonb_agg({row(table)} ORDER BY ({row(table)})::text),'[]') FROM {table} t") for table in TABLES}
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()

def setup(lab, db, dll):
    password = secrets.token_urlsafe(32)
    result = lab.bootstrap(db, 'hardware-admin', password, dll=dll)
    if result.returncode:
        (db.directory/'bootstrap-private.log').write_text(result.stdout+'\n'+result.stderr, encoding='utf-8')
        raise RuntimeError('Bootstrap failed; private log retained')
    house, admin = lab.sql(db, 'SELECT id FROM systemhaus; SELECT id FROM app_user').splitlines()
    ids = {name:str(uuid.uuid4()) for name in ['customer','other','rack','extra','foreign','reader','outsider','readerGroup','outsiderGroup','baseGroup']}
    ids.update(house=house, admin=admin)
    sql = [f"INSERT INTO customer(id,systemhaus_id,name) VALUES('{ids['customer']}','{house}','Hardware synthetic'),('{ids['other']}','{house}','Other synthetic');",
        f"INSERT INTO inventory_rack(id,systemhaus_id,customer_id,name,size_u) VALUES('{ids['rack']}','{house}','{ids['customer']}','Rack 4U',4),('{ids['extra']}','{house}','{ids['customer']}','Rack 12U',12),('{ids['foreign']}','{house}','{ids['other']}','Foreign rack',12);",
        f"INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{ids['reader']}',systemhaus_id,'hardware-reader',password_hash FROM app_user WHERE id='{admin}';",
        f"INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{ids['outsider']}',systemhaus_id,'hardware-outsider',password_hash FROM app_user WHERE id='{admin}';"]
    for group in ['baseGroup','readerGroup','outsiderGroup']:
        sql.append(f"INSERT INTO user_group(id,systemhaus_id,name) VALUES('{ids[group]}','{house}','Synthetic {group}');")
    for user,group in [('reader','readerGroup'),('outsider','outsiderGroup')]:
        sql.append(f"INSERT INTO user_group_member VALUES('{house}','{ids[user]}','{ids[group]}'),('{house}','{ids[user]}','{ids['baseGroup']}');")
    sql.append(f"INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{house}','{ids['baseGroup']}','systemhaus.read',NULL,NULL);")
    sql.append(f"INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{house}','{ids['readerGroup']}','inventory.read','{ids['customer']}',NULL);")
    sql.append(f"INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{house}','{ids['outsiderGroup']}','inventory.read','{ids['other']}',NULL);")
    lab.sql(db, 'BEGIN;\n'+'\n'.join(sql)+'\nCOMMIT;', sensitive=True)
    lab.grant_runtime(db)
    return ids, password

def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',type=Path,required=True);p.add_argument('--baseline-dll',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    dll=a.dll.resolve(strict=True);a.output.mkdir(parents=True,exist_ok=False)
    report={'utc':datetime.now(timezone.utc).isoformat(),'result':'FAIL','database':'PostgreSQL17 fresh independent cluster','qaAccessed':False,'vmAccessed':False,'cases':[],'serverSha256':hashlib.sha256(dll.read_bytes()).hexdigest()}
    lab=Lab('hardware-mounting');tick=time.monotonic()
    try:
        with lab:
            db=lab.create_database('hardware-mounting');ids,password=setup(lab,db,dll)
            server=lab.start_server(db,dll=dll);client=Client(server)
            assert client.login('hardware-admin',password).status==200
            actor=client.request('GET','/api/v1/me').json()['user']['id'];route=f"/api/v1/customers/{ids['customer']}/commands";projectRoute=f"/api/v1/customers/{ids['customer']}/project"
            def project(c=client):
                response=c.request('GET',projectRoute);assert response.status==200;return response.json()
            def command(kind,payload,status=200,c=client,revision=None,key=None):
                rev=project()['revision'] if revision is None else revision
                who=c.request('GET','/api/v1/me').json()['user']['id']
                response=c.request('POST',route,{'type':kind,'payload':payload},{'If-Match':f'"{rev}"','Idempotency-Key':key or str(uuid.uuid4()),'X-RackClick-Actor':who})
                assert response.status==status,(kind,status,response.status,response.body.decode())
                return response
            def hardware(profile,rack=None,parent=None,name=None,status=200):
                payload={'profileKey':profile,'rackId':rack or ids['rack'],'name':name or profile}
                if parent:payload.update(mountParentId=parent,mountSlotKey='main')
                response=command('device.createHardware',payload,status=status)
                return response.json()['result']['resourceId'] if status==200 else response
            ids['shelf']=hardware('shelf-2u');ids['firewall']=hardware('desktop-firewall-6',parent=ids['shelf']);ids['switch']=hardware('switch-24');ids['patch']=hardware('patchpanel-24')
            snapshot=project();devices={d['id']:d for d in snapshot['devices']}
            assert sum(d['sizeU'] for d in snapshot['devices'] if d['rackId']==ids['rack'])==4
            assert devices[ids['firewall']]['sizeU']==0 and devices[ids['firewall']]['mountParentId']==ids['shelf']
            assert devices[ids['firewall']]['properties']['physicalDimensionsMm']['height']==38
            assert len(snapshot['ports'])==81 and len({p['id'] for p in snapshot['ports']})==81
            report['cases'].append('four objects: 2+0+1+1=4U; firewall has independent UUID and physical height38mm; 81 distinct port UUIDs')
            referencePath=ROOT/'development/frontend/src/hardware-reference.json'
            reference=json.loads(referencePath.read_text(encoding='utf-8'))
            assert reference['synthetic'] is True and reference['version']=='hw-reference-v1'
            for ref in reference['profiles']:
                device=next(d for d in snapshot['devices'] if d['hardwareProfileKey']==ref['key'])
                assert device['sizeU']==ref['sizeU']
                assert device['properties']['hardwareProfileVersion']==reference['version']
                assert device['properties']['physicalDimensionsMm']=={'width':ref['widthMm'],'height':ref['heightMm'],'depth':ref['depthMm']}
                actual=[(group['key'],group['type'],group['face'],len([port for port in snapshot['ports'] if port['deviceId']==device['id'] and port['properties']['hardwareGroupKey']==group['key'] and port['type']==group['type'] and port['face']==group['face']])) for group in ref['groups']]
                assert actual==[(g['key'],g['type'],g['face'],g['count']) for g in ref['groups']]
            report['referenceSha256']=hashlib.sha256(referencePath.read_bytes()).hexdigest()
            report['cases'].append('frontend reference JSON agrees with server materialization: version/dimensions/U/groups/types/faces/counts')
            patchPorts=[p for p in snapshot['ports'] if p['deviceId']==ids['patch']]
            assert len([p for p in patchPorts if p['face']=='front'])==24 and len([p for p in patchPorts if p['face']=='rear'])==24
            assert len({p['id'] for p in patchPorts if p['gn']==1})==2
            def port(device,face,gn):return next(p['id'] for p in project()['ports'] if p['deviceId']==ids[device] and p['face']==face and p['gn']==gn)
            for ends in [(('firewall','front',1),('switch','front',1)),(('switch','front',2),('patch','front',1)),(('patch','rear',1),('firewall','rear',1))]:
                command('connections.create',{'fromPortId':port(*ends[0]),'toPortId':port(*ends[1])})
            assert len(project()['connections'])==3
            report['cases'].append('three explicit connections across front/rear physical port UUIDs; no inferred patch cable')
            before=state(lab,db)
            negatives=[('device.createHardware',{'profileKey':'switch-24','rackId':ids['rack'],'name':'full'},409),
                ('device.createHardware',{'profileKey':'desktop-firewall-6','rackId':ids['rack'],'name':'occupied','mountParentId':ids['shelf'],'mountSlotKey':'main'},409),
                ('device.createHardware',{'profileKey':'unknown','rackId':ids['extra'],'name':'unknown'},422),
                ('device.createHardware',{'profileKey':'desktop-firewall-6','rackId':ids['extra'],'name':'wrongrack','mountParentId':ids['shelf'],'mountSlotKey':'main'},422),
                ('device.createHardware',{'profileKey':'desktop-firewall-6','rackId':ids['rack'],'name':'wrongparent','mountParentId':ids['switch'],'mountSlotKey':'main'},422),
                ('device.createHardware',{'profileKey':'desktop-firewall-6','rackId':ids['extra'],'name':'missingparent'},422),
                ('device.createHardware',{'profileKey':'switch-24','rackId':ids['extra'],'name':'nested','mountParentId':ids['shelf'],'mountSlotKey':'main'},422),
                ('device.move',{'id':ids['shelf'],'rackId':ids['extra']},422),
                ('device.update',{'id':ids['firewall'],'sizeU':1},422),
                ('device.update',{'id':ids['firewall'],'properties':{'physicalDimensionsMm':{'height':999}}},422),
                ('connections.create',{'fromPortId':port('switch','rear',1),'toPortId':port('firewall','front',2)},409),
                ('rack.duplicate',{'id':ids['rack'],'name':'copy','includeConnections':True},422)]
            for kind,payload,status in negatives:command(kind,payload,status=status)
            assert state(lab,db)==before
            report['cases'].append(f'{len(negatives)} HTTP negatives preserve inventory/revision/audit/operation exact state')
            for user,status in [('hardware-reader',403),('hardware-outsider',404)]:
                denied=Client(server);assert denied.login(user,password).status==200
                command('device.createHardware',{'profileKey':'shelf-2u','rackId':ids['extra'],'name':'denied'},status=status,c=denied)
            assert state(lab,db)==before
            report['cases'].append('read-only403 and out-of-scope404; no mutation')
            # Update metadata without changing profile, dimensions, mounts, port/group UUIDs or existing cables.
            payload={'id':ids['firewall'],'name':'Firewall <img> Ω','properties':{'notes':{'text':'saved literal Ω'}}}
            rev=project()['revision'];key=str(uuid.uuid4());first=command('device.update',payload,revision=rev,key=key).json();after=state(lab,db)
            replay=command('device.update',payload,revision=rev,key=key).json();assert first==replay and state(lab,db)==after
            assert len(project()['connections'])==3
            report['cases'].append('name/notes update and exact idempotent replay keep profile, mounts, identities and three cables')
            # DB constraints are tested through direct owner SQL, independent of HTTP guards.
            def sqlReject(label,sql,expected):
                previous=state(lab,db)
                try:lab.sql(db,'BEGIN;'+sql+';COMMIT;')
                except RuntimeError as error:assert any(name in str(error) for name in expected),(label,str(error))
                else:raise AssertionError('Expected DB rejection: '+label)
                assert state(lab,db)==previous
                report['cases'].append('DB rejection '+label)
            sqlReject('root0',f"UPDATE inventory_device SET size_u=0 WHERE id='{ids['switch']}'",['inventory_device_placement','inventory_hardware_profile','Invalid hardware revision or placement'])
            sqlReject('parentcrossrack',f"UPDATE inventory_device SET rack_id='{ids['extra']}' WHERE id='{ids['shelf']}'",['Occupied mounting support cannot be changed'])
            sqlReject('crosscustomer',f"UPDATE inventory_device SET customer_id='{ids['other']}',rack_id='{ids['foreign']}' WHERE id='{ids['firewall']}'",['Invalid mounting support'])
            sqlReject('cycle',f"UPDATE inventory_device SET mount_parent_id='{ids['firewall']}',mount_slot_key='main' WHERE id='{ids['shelf']}'",['Invalid mounting support','Invalid hardware revision or placement'])
            sqlReject('nullslot',f"UPDATE inventory_device SET mount_slot_key=NULL WHERE id='{ids['firewall']}'",['inventory_device_placement','Invalid mounting slot or dimensions'])
            sqlReject('nullchildprofile',f"UPDATE inventory_device SET hardware_profile_key=NULL WHERE id='{ids['firewall']}'",['inventory_device_placement','Hardware identity is immutable'])
            sqlReject('occupiedslot',f"INSERT INTO inventory_device SELECT '{uuid.uuid4()}',systemhaus_id,customer_id,kind,rack_id,room_id,name,size_u,99,poe_budget,properties,hardware_profile_key,mount_parent_id,mount_slot_key FROM inventory_device WHERE id='{ids['firewall']}'",['inventory_mount_slot'])
            sqlReject('parentdelete',f"DELETE FROM inventory_device WHERE id='{ids['shelf']}'",['inventory_mount_parent'])
            # The runtime role is neither table owner nor privileged and cannot perform DDL.
            privileges=lab.sql(db,f"SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname='{db.runtime}'; SELECT tableowner='{db.runtime}' FROM pg_tables WHERE tablename='inventory_device'")
            assert privileges.splitlines()==['f|f|f','f']
            report['cases'].append('runtime non-owner, NOSUPERUSER NOCREATEDB NOCREATEROLE')
            # Force an audit failure after materialization. The enclosing product transaction must roll back all of it.
            lab.sql(db,"CREATE FUNCTION fail_hardware_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='inventory.device.createHardware' THEN RAISE EXCEPTION 'synthetic audit fail'; END IF; RETURN NEW; END $$; CREATE TRIGGER fail_hardware_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION fail_hardware_audit();")
            before=state(lab,db)
            command('device.createHardware',{'profileKey':'switch-24','rackId':ids['extra'],'name':'rollback'},status=503)
            assert state(lab,db)==before
            lab.sql(db,'DROP TRIGGER fail_hardware_audit ON audit_event; DROP FUNCTION fail_hardware_audit()')
            report['cases'].append('forced audit failure rolls back device/groups/ports/revision/operation')
            # One customer revision serializes simultaneous slot claims. The loser cannot create another child.
            raceShelf=hardware('shelf-2u',rack=ids['extra']);revision=project()['revision']
            raceClient=Client(server);assert raceClient.login('hardware-admin',password).status==200
            def claim(c):
                who=c.request('GET','/api/v1/me').json()['user']['id']
                return c.request('POST',route,{'type':'device.createHardware','payload':{'profileKey':'desktop-firewall-6','rackId':ids['extra'],'name':'race','mountParentId':raceShelf,'mountSlotKey':'main'}},{'If-Match':f'"{revision}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':who}).status
            with concurrent.futures.ThreadPoolExecutor(2) as pool:statuses=list(pool.map(claim,[client,raceClient]))
            assert sorted(statuses)==[200,412],statuses
            assert sum(d['mountParentId']==raceShelf for d in project()['devices'])==1
            report['cases'].append('simultaneous slot claims: one200 one412 stale revision, one child')
            # Existing legacy command still works in mixed new schema; new DTO fields cannot forge mounting.
            command('device.create',{'kind':'rackEquipment','rackId':ids['extra'],'sizeU':1,'name':'Legacy','portGroups':[]})
            before=state(lab,db);command('device.create',{'kind':'rackEquipment','rackId':ids['extra'],'sizeU':1,'name':'Forged','mountParentId':raceShelf},status=422);assert state(lab,db)==before
            report['cases'].append('legacy root creation remains supported; forged mount fields rejected')
            # A support with a child requires an explicit union, never implicit destructive cascade.
            before=state(lab,db)
            preview=client.request('POST',route+'/preview',{'type':'device.delete','payload':{'id':ids['shelf']}},{'If-Match':f'"{project()["revision"]}"','X-RackClick-Actor':actor})
            assert preview.status==409 and preview.json()['error']=='mount_children_present'
            assert state(lab,db)==before
            report['cases'].append('occupied support delete preview409, child/cables preserved')
            # Read from another authorized account, then restart only this laboratory server.
            reader=Client(server);assert reader.login('hardware-reader',password).status==200
            expected=project();assert project(reader)==expected
            server.close();restart=lab.start_server(db,dll=dll);second=Client(restart);assert second.login('hardware-reader',password).status==200
            persisted=second.request('GET',projectRoute);assert persisted.status==200 and persisted.json()==expected
            report['cases'].append('reload/second account and server restart persist exact project and cables')
            if a.baseline_dll:
                baseline=a.baseline_dll.resolve(strict=True);old=lab.create_database('upgrade15to16');oldids,oldpassword=setup(lab,old,baseline)
                assert lab.sql(old,'SELECT max(version) FROM schema_migration')=='15'
                legacyDevice=str(uuid.uuid4());lab.sql(old,f"INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order) VALUES('{legacyDevice}','{oldids['house']}','{oldids['customer']}','rackEquipment','{oldids['rack']}','Existing before16',1,0)")
                oldState=state(lab,old,legacy=True)
                history=lab.sql(old,'SELECT version,digest FROM schema_migration ORDER BY version')
                securityTables=['app_user','user_group','user_group_member','permission_grant']
                def security():return hashlib.sha256('\n'.join(lab.sql(old,f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM {table} t") for table in securityTables).encode()).hexdigest()
                securityBefore=security();environment=lab.environment();environment['ConnectionStrings__RackClick']=old.connection(lab.port,runtime=False)
                migrated=subprocess.run([str(lab.dotnet),str(dll),'--migrate'],env=environment,cwd=ROOT/'development/server',capture_output=True,text=True,encoding='utf-8',timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
                (old.directory/'migrate-private.log').write_text(migrated.stdout+'\n'+migrated.stderr,encoding='utf-8')
                assert migrated.returncode==0,'Migration15to16 failed; private log retained'
                assert lab.sql(old,'SELECT max(version) FROM schema_migration')=='16'
                assert lab.sql(old,'SELECT version,digest FROM schema_migration WHERE version<=15 ORDER BY version')==history
                assert state(lab,old,legacy=True)==oldState and security()==securityBefore
                assert lab.sql(old,'SELECT count(*) FROM inventory_device WHERE hardware_profile_key IS NOT NULL OR mount_parent_id IS NOT NULL OR mount_slot_key IS NOT NULL')=='0'
                upgraded=lab.start_server(old,dll=dll);oldclient=Client(upgraded);assert oldclient.login('hardware-admin',oldpassword).status==200
                read=oldclient.request('GET',f"/api/v1/customers/{oldids['customer']}/project");assert read.status==200
                existing=next(d for d in read.json()['devices'] if d['id']==legacyDevice);assert existing['sizeU']==1 and existing['mountParentId'] is None
                report['baselineSha256']=hashlib.sha256(baseline.read_bytes()).hexdigest();report['cases'].append('actual15to16 upgrade preserves inventory/account/grants/history1to15 and legacy root IDs')
            else:report['upgrade15to16']='NOT RUN: no explicit baseline DLL supplied'
            report.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'),schema=lab.sql(db,'SELECT max(version) FROM schema_migration'),casesPassed=len(report['cases']),httpNegativeCount=len(negatives)+2,portCount=len(expected['ports']))
    except Exception as error:
        report.update(errorType=type(error).__name__,error=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-tick,3),labStopped=not lab.running,serversStopped=all(server.process.poll() is not None for server in lab.servers))
        (a.output/'RESULTADOS.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps(report,indent=2,ensure_ascii=False))
    return 0 if report['result']=='PASS' and report['labStopped'] and report['serversStopped'] else 1

if __name__=='__main__':raise SystemExit(main())
