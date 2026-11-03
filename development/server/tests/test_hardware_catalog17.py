"""Normalized catalog17, real PG17, explicit frozen16 upgrade and atomic failures.

All databases/roles are newly created by pg_support. Never accesses VM/QA.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
from pg_support import Lab, Client, literal, protect_directory, NO_WINDOW
from test_hardware_mounting import setup, TABLES

ROOT=Path(__file__).resolve().parents[3]
CATALOG=('hardware_definition','hardware_mount_slot','hardware_group_template','hardware_passthrough')


def state(lab,db,catalog=True):
    tables=TABLES+list(CATALOG) if catalog else TABLES
    result={}
    for table in tables:
        row="to_jsonb(t)-'hardware_profile_revision'" if table=='inventory_device' else 'to_jsonb(t)'
        result[table]=lab.sql(db,f"SELECT COALESCE(jsonb_agg({row} ORDER BY ({row})::text),'[]') FROM {table} t")
    return hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()


def migrate(lab,db,dll,output):
    env=lab.environment();env['ConnectionStrings__RackClick']=db.connection(lab.port,runtime=False)
    result=subprocess.run([str(lab.dotnet),str(dll),'--migrate'],env=env,cwd=ROOT/'development/server',capture_output=True,text=True,encoding='utf-8',timeout=60,creationflags=NO_WINDOW)
    output.write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    return result.returncode


def runtime_sql(lab,db,sql):
    env=lab.environment();env['PGPASSWORD']=db.runtime_password
    return subprocess.run([str(lab.pg_bin/'psql.exe'),'-X','-w','-v','ON_ERROR_STOP=1','-h','127.0.0.1','-p',str(lab.port),'-U',db.runtime,'-d',db.name,'-At'],input=sql,env=env,capture_output=True,text=True,encoding='utf-8',timeout=30,creationflags=NO_WINDOW)


def catalog_matches_source(lab,db):
    source=json.loads((ROOT/'development/hardware/catalog-source-v1.json').read_text())
    raw=lab.sql(db,"SELECT jsonb_agg(to_jsonb(d) ORDER BY profile_key) FROM hardware_definition d")
    rows={row['profile_key']:row for row in json.loads(raw)};assert len(rows)==len(source['definitions'])==4
    for model in source['definitions']:
        actual=rows[model['key']];dimensions=model['dimensionsMm']
        assert {k:actual[k] for k in ('mount_kind','rack_units','width_mm','height_mm','depth_mm','color')}==dict(mount_kind=model['kind'],rack_units=model['rackUnits'],width_mm=dimensions['width'],height_mm=dimensions['height'],depth_mm=dimensions['depth'],color=model['color'])
        canonical=(json.dumps(model,ensure_ascii=True,sort_keys=True,separators=(',',':'))+'\n').encode('ascii')
        assert actual['sealed'] is True and actual['revision']==model['revision'] and actual['definition_sha256']==hashlib.sha256(canonical).hexdigest()
        assert all(actual[k]==model['identity'][k] for k in ('manufacturer','family','model','sku'))
        assert actual['provenance_kind']==model['provenance']['kind'] and actual['source_reference']==model['provenance']['source']
        where=f"profile_key={literal(model['key'])} AND revision={literal(model['revision'])}"
        groups=json.loads(lab.sql(db,f"SELECT COALESCE(jsonb_agg(jsonb_build_object('key',group_key,'type',type,'count',port_count,'face',face,'name',name,'prefix',prefix) ORDER BY sort_order),'[]') FROM hardware_group_template WHERE {where}"))
        slots=json.loads(lab.sql(db,f"SELECT COALESCE(jsonb_agg(jsonb_build_object('key',slot_key,'dimensionsMm',jsonb_build_object('width',width_mm,'height',height_mm,'depth',depth_mm)) ORDER BY slot_key),'[]') FROM hardware_mount_slot WHERE {where}"))
        assert groups==model['groups'] and slots==model['slots']
        passthrough=json.loads(lab.sql(db,f"SELECT COALESCE(jsonb_agg(jsonb_build_object('frontGroup',front_group_key,'rearGroup',rear_group_key,'count',port_count,'mapping','one-to-one','tracingAvailable',false)),'[]') FROM hardware_passthrough WHERE {where}"))
        assert passthrough==([model['passthrough']] if model['passthrough'] else [])


class Session:
    def __init__(self,server,ids,password):
        self.client=Client(server);assert self.client.login('hardware-admin',password).status==200
        self.route=f"/api/v1/customers/{ids['customer']}";self.actor=self.client.request('GET','/api/v1/me').json()['user']['id']
    def project(self):
        response=self.client.request('GET',self.route+'/project');assert response.status==200;return response.json()
    def command(self,payload,status=200,key=None,revision=None,kind='device.createHardware'):
        body={'type':kind,'payload':payload}
        response=self.client.request('POST',self.route+'/commands',body,{'X-RackClick-Actor':self.actor,'If-Match':f'"{self.project()["revision"] if revision is None else revision}"','Idempotency-Key':key or str(uuid.uuid4())})
        assert response.status==status,(status,response.status,response.body)
        return response
    def hardware(self,profile,rack,parent=None):
        payload=dict(profileKey=profile,profileVersion='hw-reference-v1',rackId=rack,name='Synthetic '+profile)
        if parent:payload.update(mountParentId=parent,mountSlotKey='main')
        return self.command(payload).json()['result']['resourceId']


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--baseline-dll',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    dll=a.dll.resolve(strict=True);baseline=a.baseline_dll.resolve(strict=True);a.output.mkdir(parents=True,exist_ok=False);protect_directory(a.output)
    report=dict(result='FAIL',checks=[],serverSha256=hashlib.sha256(dll.read_bytes()).hexdigest(),baselineSha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),qaAccessed=False,vmAccessed=False);lab=Lab('hardware-catalog17')
    try:
        with lab:
            old=lab.create_database('upgrade16');ids,password=setup(lab,old,baseline)
            assert lab.sql(old,'SELECT max(version) FROM schema_migration')=='16'
            server16=lab.start_server(old,dll=baseline);session16=Session(server16,ids,password)
            shelf=session16.hardware('shelf-2u',ids['rack']);child=session16.hardware('desktop-firewall-6',ids['rack'],shelf)
            switch=session16.hardware('switch-24',ids['rack']);panel=session16.hardware('patchpanel-24',ids['rack'])
            expected=session16.project();assert len(expected['ports'])==81
            def port(device,face,number):return next(p['id'] for p in session16.project()['ports'] if p['deviceId']==device and p['face']==face and p['gn']==number)
            for a_end,b_end in [((child,'front',1),(switch,'front',1)),((switch,'front',2),(panel,'front',1)),((panel,'rear',1),(child,'rear',1))]:
                session16.command(dict(fromPortId=port(*a_end),toPortId=port(*b_end)),kind='connections.create')
            expected=session16.project();assert len(expected['connections'])==3
            replay_payload=dict(profileKey='shelf-2u',profileVersion='hw-reference-v1',rackId=ids['extra'],name='Replay after migrate')
            replay_key=str(uuid.uuid4());replay_rev=expected['revision'];replay_result=session16.command(replay_payload,key=replay_key,revision=replay_rev).json();expected=session16.project()
            before=state(lab,old,catalog=False);history=lab.sql(old,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t')
            server16.close();assert migrate(lab,old,dll,a.output/'migrate-private.txt')==0
            assert lab.sql(old,'SELECT max(version) FROM schema_migration')=='17';assert state(lab,old,catalog=False)==before
            assert lab.sql(old,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t WHERE version<=16')==history
            catalog_matches_source(lab,old);lab.grant_runtime(old)
            server=lab.start_server(old,dll=dll);session=Session(server,ids,password);assert session.project()==expected
            assert session.command(replay_payload,key=replay_key,revision=replay_rev).json()==replay_result
            report['checks'].append('real16to17 upgrade preserves snapshot, UUIDs,81ports,3cables,mounts,operations/audit and migration digests1to16; old operation replays unchanged')
            before=state(lab,old);assert migrate(lab,old,dll,a.output/'migrate-repeat-private.txt')==0;assert state(lab,old)==before
            report['checks'].append('repeat migrate validates all digests without changing catalog or inventory')
            # Read-only privileges are measured and exercised using the actual runtime login.
            for table in CATALOG:
                rights=runtime_sql(lab,old,f"SELECT has_table_privilege(current_user,'{table}','SELECT'),has_table_privilege(current_user,'{table}','INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')")
                assert rights.returncode==0 and rights.stdout.strip()=='t|f'
                for sql in [f'DELETE FROM {table}',f'TRUNCATE {table}',f'UPDATE {table} SET revision=revision',f'INSERT INTO {table} SELECT * FROM {table} WHERE false']:
                    result=runtime_sql(lab,old,sql);assert result.returncode!=0
            assert runtime_sql(lab,old,'CREATE TABLE must_not_exist(id integer)').returncode!=0
            assert state(lab,old)==before
            report['checks'].append('actual runtime SELECT succeeds;16 DML/TRUNCATE attempts and DDL denied, catalog and inventory unchanged')
            def reject(sql,expected_error=None):
                prior=state(lab,old)
                try:lab.sql(old,'BEGIN;'+sql+';COMMIT;')
                except RuntimeError as error:
                    if expected_error:assert expected_error in str(error)
                else:raise AssertionError('SQL should reject')
                assert state(lab,old)==prior
            for table in CATALOG:
                reject(f'UPDATE {table} SET revision=revision','Catalog revisions are immutable')
                reject(f'DELETE FROM {table}','Catalog revisions are immutable')
                reject(f'TRUNCATE {table}') # FK rejection may precede the trigger.
            reject("INSERT INTO hardware_group_template VALUES('switch-24','hw-reference-v1','extra',2,'rj45',1,'front','extra','')",'Catalog revisions are immutable')
            reject("INSERT INTO hardware_mount_slot VALUES('shelf-2u','hw-reference-v1','extra',200,40,100)",'Catalog revisions are immutable')
            prior=state(lab,old)
            try:lab.sql(old,"BEGIN ISOLATION LEVEL REPEATABLE READ; INSERT INTO hardware_group_template VALUES('switch-24','hw-reference-v1','extra',2,'rj45',1,'front','extra',''); COMMIT;")
            except RuntimeError as error:assert 'Catalog writes require READ COMMITTED' in str(error)
            else:raise AssertionError('Stale catalog authoring isolation must reject')
            assert state(lab,old)==prior
            reject("INSERT INTO hardware_definition(profile_key,revision,mount_kind,rack_units,width_mm,height_mm,depth_mm,color,definition_sha256,provenance_kind,source_reference) SELECT profile_key,revision,mount_kind,rack_units,width_mm,height_mm,depth_mm,color,definition_sha256,provenance_kind,source_reference FROM hardware_definition WHERE profile_key='shelf-2u'",'duplicate key')
            reject(f"UPDATE inventory_device SET properties=properties-'hardwareProfileVersion' WHERE id='{child}'",'Hardware identity is immutable')
            reject(f"UPDATE inventory_device SET mount_slot_key='unknown' WHERE id='{child}'",'Invalid mounting slot')
            report['checks'].append('owner cannot rewrite/delete/truncate existing revisions; duplicate exact pair and instance-version/slot edits reject atomically')
            # A new revision can coexist, but does not become a default or a published API model.
            columns='profile_key,revision,mount_kind,rack_units,width_mm,height_mm,depth_mm,color,definition_sha256,manufacturer,family,model,sku,provenance_kind,source_reference'
            lab.sql(old,f"INSERT INTO hardware_definition({columns}) SELECT profile_key,'fixture-v2',mount_kind,rack_units,width_mm,height_mm,depth_mm,color,definition_sha256,manufacturer,family,model,sku,provenance_kind,source_reference FROM hardware_definition WHERE profile_key='shelf-2u'; INSERT INTO hardware_mount_slot SELECT profile_key,'fixture-v2',slot_key,100,height_mm,depth_mm FROM hardware_mount_slot WHERE profile_key='shelf-2u'")
            prior=state(lab,old)
            draft_insert=f"INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order,properties,hardware_profile_key) VALUES('{uuid.uuid4()}','{ids['house']}','{ids['customer']}','rackEquipment','{ids['extra']}','draft must reject',2,90,'{{\"hardwareProfileVersion\":\"fixture-v2\"}}','shelf-2u')"
            assert runtime_sql(lab,old,draft_insert).returncode!=0 and state(lab,old)==prior
            lab.sql(old,"UPDATE hardware_definition SET sealed=true WHERE revision='fixture-v2'")
            assert lab.sql(old,"SELECT count(*) FROM hardware_definition WHERE profile_key='shelf-2u'")=='2'
            prior=state(lab,old);response=session.command(dict(profileKey='shelf-2u',profileVersion='fixture-v2',rackId=ids['extra'],name='unpublished'),422);assert response.json()['error']=='hardware_revision_unknown';assert state(lab,old)==prior
            reject(f"UPDATE inventory_device SET properties=jsonb_set(properties,'{{hardwareProfileVersion}}','\"fixture-v2\"') WHERE id='{shelf}'",'Hardware identity is immutable')
            assert session.project()==expected
            report['checks'].append('two exact revisions coexist without changing original instances; unpublished revision is not selected by API')
            # Accidental provisioning with broad DML grants must fail closed in the command.
            lab.sql(old,f'GRANT UPDATE ON hardware_definition TO {old.runtime}')
            prior=state(lab,old);response=session.command(dict(profileKey='switch-24',rackId=ids['extra'],name='bad-rights'),503)
            assert response.json()['error']=='hardware_catalog_permissions_invalid' and state(lab,old)==prior
            lab.grant_runtime(old)
            # Simulated owner corruption; the app must not trust a digest string alone.
            lab.sql(old,'ALTER TABLE hardware_mount_slot DISABLE TRIGGER hardware_slot_immutable; UPDATE hardware_mount_slot SET width_mm=439 WHERE revision=\'hw-reference-v1\'; ALTER TABLE hardware_mount_slot ENABLE TRIGGER hardware_slot_immutable')
            prior=state(lab,old);response=session.command(dict(profileKey='desktop-firewall-6',rackId=ids['extra'],name='bad-catalog',mountParentId=replay_result['result']['resourceId'],mountSlotKey='main'),409)
            assert response.json()['error']=='hardware_catalog_definition_mismatch' and state(lab,old)==prior
            lab.sql(old,'ALTER TABLE hardware_mount_slot DISABLE TRIGGER hardware_slot_immutable; UPDATE hardware_mount_slot SET width_mm=440 WHERE revision=\'hw-reference-v1\'; ALTER TABLE hardware_mount_slot ENABLE TRIGGER hardware_slot_immutable')
            report['checks'].append('broad runtime grants and physical catalog drift reject atomically before materialization')
            # A separate malformed16 database demonstrates migration rollback, not auto-repair.
            invalid=lab.create_database('incomplete16');badids,badpassword=setup(lab,invalid,baseline);badserver=lab.start_server(invalid,dll=baseline);badsession=Session(badserver,badids,badpassword)
            badshelf=badsession.hardware('shelf-2u',badids['rack']);badserver.close()
            lab.sql(invalid,f"UPDATE inventory_device SET properties=properties-'hardwareProfileVersion' WHERE id='{badshelf}'")
            prior=state(lab,invalid,catalog=False);old_history=lab.sql(invalid,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t')
            assert migrate(lab,invalid,dll,a.output/'migrate-invalid-private.txt')!=0
            assert lab.sql(invalid,"SELECT to_regclass('public.hardware_definition') IS NULL")=='t'
            assert lab.sql(invalid,'SELECT max(version) FROM schema_migration')=='16' and state(lab,invalid,catalog=False)==prior
            assert lab.sql(invalid,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t')==old_history
            report['checks'].append('malformed16 revision stops upgrade and rolls back all DDL/seeds/history; no inferred version or changed rows')
            fresh=lab.create_database('fresh17');freshids,freshpassword=setup(lab,fresh,dll);catalog_matches_source(lab,fresh)
            assert lab.sql(fresh,'SELECT max(version) FROM schema_migration')=='17'
            freshserver=lab.start_server(fresh,dll=dll);freshsession=Session(freshserver,freshids,freshpassword);freshsession.hardware('switch-24',freshids['rack'])
            report['checks'].append('clean bootstrap1to17 matches all normalized authoring fields/groups/slots/continuity and creates hardware under runtime login')
            server.close();restarted=lab.start_server(old,dll=dll);other=Session(restarted,ids,password);assert other.project()==expected
            report.update(result='PASS',checksPassed=len(report['checks']),postgresql=lab.sql('postgres','SHOW server_version'),schema=17,restartPersistence=True)
    finally:
        report.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers));(a.output/'RESULTADOS.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
    return 0 if report['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
