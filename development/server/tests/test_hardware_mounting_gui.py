"""Fresh PG17 + actual Windows Edge hardware assembly. No installed QA/VM touched."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import uuid
from pg_support import Lab, Client, NO_WINDOW, protect_directory, toolchain

ROOT=Path(__file__).resolve().parents[3]

def fixture(lab,db,dll):
    password=secrets.token_urlsafe(32)
    if lab.bootstrap(db,'hardware-admin',password,dll=dll).returncode:
        raise RuntimeError('Fresh bootstrap rejected; raw output remains private')
    h,admin=lab.sql(db,'SELECT id FROM systemhaus; SELECT id FROM app_user').splitlines()
    group=lab.sql(db,f"SELECT group_id FROM user_group_member WHERE user_id='{admin}'")
    ids={key:str(uuid.uuid4()) for key in ['customer','rack','mixedRack','legacy','legacyGroup','legacyPort','legacyPort2','second','reader','readGroup']}
    lab.sql(db,f"""BEGIN;
    INSERT INTO customer(id,systemhaus_id,name) VALUES('{ids['customer']}','{h}','Hardware QA synthetic');
    INSERT INTO inventory_rack(id,systemhaus_id,customer_id,name,size_u) VALUES('{ids['rack']}','{h}','{ids['customer']}','Rack montaje 4U',4);
    INSERT INTO inventory_rack(id,systemhaus_id,customer_id,name,size_u) VALUES('{ids['mixedRack']}','{h}','{ids['customer']}','Rack mixto RC9',12);
    INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order,properties) VALUES('{ids['legacy']}','{h}','{ids['customer']}','rackEquipment','{ids['mixedRack']}','NAS legacy preservado',2,0,'{{"preset":"nas","color":"#123456"}}');
    INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order) VALUES('{ids['legacyGroup']}','{h}','{ids['customer']}','{ids['legacy']}','rj45','Legacy','',0);
    INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order) VALUES('{ids['legacyPort']}','{h}','{ids['customer']}','{ids['legacy']}','{ids['legacyGroup']}','rj45',1,0),('{ids['legacyPort2']}','{h}','{ids['customer']}','{ids['legacy']}','{ids['legacyGroup']}','rj45',2,1);
    INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{ids['second']}',systemhaus_id,'hardware-second',password_hash FROM app_user WHERE id='{admin}';
    INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{ids['reader']}',systemhaus_id,'hardware-reader',password_hash FROM app_user WHERE id='{admin}';
    INSERT INTO user_group_member VALUES('{h}','{ids['second']}','{group}');
    INSERT INTO user_group VALUES('{ids['readGroup']}','{h}','Hardware synthetic reader');
    INSERT INTO user_group_member VALUES('{h}','{ids['reader']}','{ids['readGroup']}');
    INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{h}','{ids['readGroup']}','systemhaus.read',NULL,NULL),('{uuid.uuid4()}','{h}','{ids['readGroup']}','inventory.read','{ids['customer']}',NULL);
    COMMIT;""",sensitive=True)
    return ids,password

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--frontend',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    dll=a.dll.resolve(strict=True);front=a.frontend.resolve(strict=True);output=a.output.absolute()
    if not output.resolve().is_relative_to((ROOT/'.local').resolve()):raise RuntimeError('Private output must be under .local')
    output.mkdir(parents=True,exist_ok=False);protect_directory(output)
    report=dict(result='FAIL',qaChanged=False,serverSha256=hashlib.sha256(dll.read_bytes()).hexdigest(),appSha256=hashlib.sha256((front/'app.js').read_bytes()).hexdigest())
    lab=Lab('hardware-mount-gui')
    try:
        with lab:
            db=lab.create_database('hardware-mount-gui');ids,password=fixture(lab,db,dll);lab.grant_runtime(db)
            server=lab.start_server(db,dll=dll,frontend=front);env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='hardware-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(output),RACKCLICK_FIXTURE=json.dumps(ids))
            with (output/'browser.log').open('wb') as log:
                done=subprocess.run([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-hardware-mounting.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=300,creationflags=NO_WINDOW)
            if done.returncode:raise RuntimeError('Browser scenario failed; private browser.log retained')
            expected=json.loads((output/'expected-project.json').read_text(encoding='utf-8'))
            assert len(expected['devices'])==6 and len(expected['ports'])==83 and len(expected['connections'])==3
            assert lab.sql(db,f"SELECT sum(size_u) FROM inventory_device WHERE rack_id='{ids['rack']}'")=='4'
            assert lab.sql(db,'SELECT count(*) FROM operation')=='10'
            server.close();restart=lab.start_server(db,dll=dll,frontend=front);reader=Client(restart);assert reader.login('hardware-reader',password).status==200
            actual=reader.request('GET',f"/api/v1/customers/{ids['customer']}/project").json()
            for k in ['sites','buildings','rooms','racks','devices','portGroups','ports','connections']:actual[k].sort(key=lambda r:r['id'])
            assert actual==expected
            report.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'),createdThroughGui=5,referenceAssemblyPorts=81,legacyPortsPreserved=2,cables=3,additionalChildUnits=0,assemblyRackUnits=4,committedCommands=10,legacyCollapseAndReorder=True,reloadAndSecondSession=True,aspNetRestartPersistence=True)
    finally:
        report.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers));(output/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
    return 0 if report['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
