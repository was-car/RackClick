"""Four bounded personal-palette focuses; frozen artifacts and new native PG labs only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest

from pg_support import Client, Lab, WORKSPACE, NO_WINDOW, literal
from test_postgres import EvidenceResult, Tee
from test_shared_device_templates import SharedDeviceTemplatesPostgres, uid, distribution

MAX_REVISION = 9007199254740991
TABLES = {'user_port_colors', 'user_port_color_operation'}
TYPES = ['rj45','rj45_poe','sfp','sfp28','qsfp','mgmt','console','power','usb_a','usb_c']


class UserPortColors969(SharedDeviceTemplatesPostgres):
    baseline = None

    def setUp(self):
        target = self.dll
        if self._testMethodName.startswith('test_04_'): self.dll = self.baseline
        try: super().setUp()
        finally: self.dll = target

    def color_path(self, key=None, cancel=False):
        return '/api/v1/me/port-colors' + (f'/operations/{key}' if key else '') + ('/cancel' if cancel else '')

    def palette(self, client=None):
        client = client or self.admin
        response = self.expect(client.request('GET', self.color_path()), 200)
        value = response.json()
        self.assertEqual(set(value), {'kind','ownerId','revision','colors'})
        self.assertEqual(value['kind'], 'userPortColors'); self.assertEqual(value['ownerId'], client.actor_id)
        self.assertEqual(response.headers.get('etag'), f'"port-colors-{value["revision"]}"')
        return value

    def color_headers(self, client=None, revision=0, key=None):
        return {'If-Match':f'"port-colors-{revision}"', 'Idempotency-Key':key or uid(),
                'X-RackClick-Actor':(client or self.admin).actor_id}

    def colors(self, colors=None, revision=None, key=None, client=None, status=200, headers=None):
        client = client or self.admin
        if revision is None: revision = self.palette(client)['revision']
        response = self.expect(client.request('POST', self.color_path(), {'colors':colors if colors is not None else {'rj45':'#123abc'}},
            {**self.color_headers(client, revision, key), **(headers or {})}), status)
        if status == 200:
            value = response.json()
            self.assertEqual(set(value), {'kind','ownerId','revision','requestId','operationId','result'})
            self.assertEqual(set(value['result']), {'colors','changed'}); self.assertIsInstance(value['result']['changed'], bool)
            self.assertEqual(value['kind'],'userPortColors'); self.assertEqual(value['ownerId'],client.actor_id)
            self.assertEqual(response.headers.get('etag'), f'"port-colors-{value["revision"]}"')
        return response

    def color_status(self, key, client=None, status=200):
        client = client or self.admin
        response = self.expect(client.request('GET', self.color_path(key)), status)
        if status == 200:
            value=response.json(); self.assertEqual(set(value),{'state','ownerId','revision','requestId','operation'})
            self.assertEqual(value['ownerId'],client.actor_id); self.assertEqual(value['requestId'],key)
            self.assertEqual(response.headers.get('etag'),f'"port-colors-{value["revision"]}"')
        return response

    def cancel_colors(self, key, colors=None, revision=0, client=None, status=200, headers=None):
        client=client or self.admin
        return self.expect(client.request('POST', self.color_path(key,True),
            {'colors':colors if colors is not None else {'rj45':'#123abc'}},
            {**self.color_headers(client,revision,key), **(headers or {})}), status)

    def rows(self, database=None, tables=None):
        database=database or self.db
        if tables is None: tables=self.lab.sql(database,"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
        return {name:self.lab.sql(database,f'SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),\'[]\') FROM "{name}" t') for name in tables}

    def once(self,key,action='user.portColors.set'):
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_port_color_operation WHERE request_id='{key}'"),'1')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{key}' AND action='{action}'"),'1')

    def test_01_actor_isolation_full_map_reset_noop_replay_restart(self):
        self.assertEqual(self.lab.sql(self.db,'SELECT max(version) FROM schema_migration'),'12')
        self.assertEqual(len(self.rows()),37)
        self.fixture(); inventory=self.snapshot()
        reader,_,_=self.add_user('colors-reader',['inventory.read'],self.customer_id)
        empty,_,_=self.add_user('colors-no-customers')
        self.assertEqual(self.expect(empty.request('GET','/api/v1/customers'),200).json(),[])
        core=self.rows(); core={k:v for k,v in core.items() if k not in TABLES|{'audit_event','app_session'}}
        before=self.durable(); self.assertEqual(self.palette()['colors'],{}); self.assertEqual(self.palette(empty)['revision'],0)
        self.assertEqual(before,self.durable()); self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM user_port_colors'),'0')
        noop0=self.colors({},client=empty).json(); self.assertFalse(noop0['result']['changed']);self.assertEqual(noop0['revision'],0)
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_port_colors WHERE owner_id='{empty.actor_id}'"),'0')
        key=uid(); original={'rj45_poe':'#fedcba','rj45':'#123abc','usb_c':'#ffffff'}
        first=self.colors(original,key=key).json(); self.assertEqual(first['revision'],1)
        reversed_map=dict(reversed(list(original.items())))
        self.assertEqual(self.colors(reversed_map,revision=0,key=key).json(),first)
        noop=self.colors(reversed_map).json(); self.assertFalse(noop['result']['changed']); self.assertEqual(noop['revision'],1)
        self.colors({'rj45':'#123abc'}); self.assertEqual(self.palette()['colors'],{'rj45':'#123abc'})
        reset=self.colors({}).json(); self.assertEqual(reset['revision'],3); self.assertTrue(reset['result']['changed'])
        self.assertEqual(self.palette()['colors'],{})
        reader_receipt=self.colors({'rj45_poe':'#001122'},client=reader).json()
        self.assertEqual(self.palette(reader)['colors'],{'rj45_poe':'#001122'})
        self.assertEqual(self.color_status(key,reader).json()['state'],'notRecorded')
        self.assertIsNone(self.color_status(uid()).json()['operation'])
        historical=self.color_status(key).json(); self.assertEqual(historical['revision'],3);self.assertEqual(historical['operation'],first)
        self.assertEqual(self.cancel_colors(key,original,revision=0).json(),historical)
        self.colors(original,revision=1,key=key,status=409)
        self.colors({'rj45':'#111111'},revision=0,key=key,status=409)
        fence=uid(); cancelled=self.cancel_colors(fence,original,revision=0).json()
        self.assertEqual(cancelled['state'],'cancelled');self.assertIsNone(cancelled['operation']);self.assertEqual(cancelled['revision'],3)
        self.assertEqual(self.cancel_colors(fence,reversed_map,revision=0).json(),cancelled)
        self.colors(original,revision=0,key=fence,status=409)
        self.colors(original,revision=3,key=fence,status=409)
        for receipt in [first,noop,reset,noop0,reader_receipt]:self.once(receipt['requestId'])
        self.once(fence,'user.portColors.set.cancel')
        self.assertEqual(self.rows(tables=core),core); self.assertEqual(self.snapshot(),inventory)
        self.assertEqual(self.poll(inventory['revision'])['events'],[])
        event=json.loads(self.lab.sql(self.db,f"SELECT row_to_json(t) FROM audit_event t WHERE id='{first['operationId']}'"))
        self.assertEqual(event['resource_id'],self.admin_id);self.assertEqual(event['action'],'user.portColors.set')
        self.assertEqual(event['before_json'],{'ownerId':self.admin_id,'revision':0,'colors':{}})
        self.assertEqual(event['after_json'],{'ownerId':self.admin_id,'revision':1,'colors':original,'changed':True})
        self.assertIsNone(event.get('customer_id'))
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_context WHERE event_id='{first['operationId']}'"),'0')
        self.server.close(); self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend)
        fresh=Client(self.server);fresh.actor_id=self.admin_id; self.expect(fresh.login('qa-inventory-admin',self.password),200)
        fresh_reader=Client(self.server);fresh_reader.actor_id=reader.actor_id;self.expect(fresh_reader.login('colors-reader',self.password),200)
        self.assertEqual(self.palette(fresh)['colors'],{});self.assertEqual(self.palette(fresh)['revision'],3)
        self.assertEqual(self.palette(fresh_reader)['colors'],{'rj45_poe':'#001122'})
        self.assertEqual(self.color_status(key,fresh).json()['operation'],first)
        self.assertEqual(self.color_status(fence,fresh).json()['state'],'cancelled')
        self.assertEqual(self.colors(reversed_map,revision=0,key=key,client=fresh).json(),first)
        self.colors(original,revision=0,key=fence,client=fresh,status=409)
        self.expect(Client(self.server).request('GET',self.color_path()),401)

    def test_02_closed_validation_csrf_conflicts_atomicity_and_receipt_integrity(self):
        before=self.durable(); good={'colors':{'rj45':'#123abc'}}; headers=self.color_headers()
        invalid=[{},[],None,{'colors':None},{'colors':[]},{**good,'ownerId':uid()},{**good,'customerId':self.customer_id},
            {**good,'revision':0},{'colors':{'unknown':'#123abc'}},{'colors':{'RJ45':'#123abc'}}]
        invalid += [{'colors':{'rj45':v}} for v in [None,True,1,{},[], '#123ABC','123abc','#abc','#123abcd',' #123abc','#123abc ','#123abc\n','#123abg']]
        for body in invalid:
            self.expect(self.admin.request('POST',self.color_path(),'null' if body is None else body,{**headers,'Content-Type':'application/json'}),422)
        for raw in ['{"colors":{},"colors":{}}','{"colors":{"rj45":"#123abc","rj45":"#123abc"}}']:
            self.expect(self.admin.request('POST',self.color_path(),raw,{**headers,'Content-Type':'application/json'}),422)
        for tag in ['"0"','"preferences-0"','"port-colors-00"','"port-colors--1"','port-colors-0',f'"port-colors-{MAX_REVISION+1}"','W/"port-colors-0"','"port-colors-0", "port-colors-1"']:
            self.colors(revision=0,status=422,headers={'If-Match':tag})
        self.expect(self.admin.request('POST',self.color_path(),good,{'Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),428)
        self.expect(self.admin.request('POST',self.color_path(),good,{'If-Match':'"port-colors-0"','Idempotency-Key':uid()}),422)
        for bad in ['invalid','00000000-0000-0000-0000-000000000000']:
            self.colors(revision=0,status=422,headers={'Idempotency-Key':bad})
            self.expect(self.admin.request('GET',self.color_path(bad)),422)
        self.colors(revision=0,status=422,headers={'X-RackClick-Actor':'invalid'})
        self.colors(revision=0,status=409,headers={'X-RackClick-Actor':uid()})
        self.colors(revision=0,status=403,headers={'X-RackClick-CSRF':'bad'})
        self.colors(revision=0,status=403,headers={'Origin':'https://wrong.invalid'})
        for path in [self.color_path(),self.color_path(uid())]:
            self.expect(self.admin.request('GET',path+'?ownerId='+uid()),422)
            self.expect(self.admin.request('GET',path,{'forbidden':True}),422)
        self.expect(self.admin.request('POST',self.color_path()+'?extra=1',good,headers),422)
        cancel=uid();self.cancel_colors(cancel,status=422,headers={'Idempotency-Key':uid()})
        self.assertEqual(before,self.durable())
        api=self.expect(self.admin.request('GET','/api/v1/openapi.json'),200).json()
        for name in ['UserPortColorsMap','UserPortColorsSet','UserPortColorChange','UserPortColorsSnapshot','UserPortColorResult','UserPortColorStatus']:
            self.assertFalse(api['components']['schemas'][name]['additionalProperties'])
        self.assertEqual(set(api['components']['schemas']['UserPortColorsMap']['properties']),set(TYPES))
        for path,methods in [(self.color_path(),['get','post']),('/api/v1/me/port-colors/operations/{requestId}',['get']),('/api/v1/me/port-colors/operations/{requestId}/cancel',['post'])]:
            for method in methods:
                operation=api['paths'][path][method];self.assertNotIn('404',operation['responses'])
                if method=='post':self.assertTrue(next(p for p in operation['parameters'] if p['name']=='X-RackClick-Actor')['required'])
        self.lab.sql(self.db,"CREATE FUNCTION colors969_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'isolated rollback witness' USING ERRCODE='23514'; END $$; CREATE TRIGGER colors969_failure BEFORE INSERT ON user_port_color_operation FOR EACH ROW EXECUTE FUNCTION colors969_fail();")
        before=self.durable()
        try:
            self.colors(revision=0,status=409);self.assertEqual(before,self.durable())
            self.cancel_colors(uid(),status=409);self.assertEqual(before,self.durable())
        finally:self.lab.sql(self.db,'DROP TRIGGER colors969_failure ON user_port_color_operation; DROP FUNCTION colors969_fail();')
        full={key:f'#{index:06x}' for index,key in enumerate(TYPES)}
        receipt=self.colors(full).json();self.assertEqual(self.palette()['colors'],full)
        before=self.durable();self.colors(full,revision=0,status=412);self.assertEqual(before,self.durable())
        for sql in ["UPDATE user_port_colors SET colors='null'", "UPDATE user_port_colors SET colors='[]'", "UPDATE user_port_colors SET colors='{\"rj45\":\"#AAAAAA\"}'", "UPDATE user_port_colors SET colors='{\"unknown\":\"#123abc\"}'",f'UPDATE user_port_colors SET revision={MAX_REVISION+1}',"UPDATE user_port_color_operation SET result_version=2","UPDATE user_port_color_operation SET result_sha256='"+'A'*64+"'"]:
            with self.assertRaises(RuntimeError):self.lab.sql(self.db,sql)
            self.assertEqual(before,self.durable())
        key=receipt['requestId']; original=self.lab.sql(self.db,f"SELECT result_json FROM user_port_color_operation WHERE request_id='{key}'")
        damaged=original.replace('"colors":{','"colors":{"rj45":"#123abc",',1)
        def store(raw):
            self.lab.sql(self.db,f"UPDATE user_port_color_operation SET result_json={literal(raw)},result_sha256=upper(encode(sha256(convert_to({literal(raw)},'UTF8')),'hex')) WHERE request_id='{key}'")
        store(damaged);corrupt=self.durable()
        try:
            self.color_status(key,status=409);self.colors(full,revision=0,key=key,status=409)
            self.cancel_colors(key,full,revision=0,status=409);self.assertEqual(corrupt,self.durable())
        finally:store(original)
        self.assertEqual(before,self.durable())

    def test_03_concurrency_max_revision_and_revocation_after_real_waits(self):
        key=uid();body={'rj45':'#123abc'}
        with ThreadPoolExecutor(2) as pool:
            replies=list(pool.map(lambda _:self.colors(body,revision=0,key=key).json(),range(2)))
        self.assertEqual(replies[0],replies[1]);first=replies[0];self.once(key)
        with ThreadPoolExecutor(2) as pool:
            replies=list(pool.map(lambda color:self.admin.request('POST',self.color_path(),{'colors':{'rj45':color}},self.color_headers(revision=1)),['#000000','#ffffff']))
        self.assertEqual(sorted(r.status for r in replies),[200,412]);self.assertEqual(self.palette()['revision'],2)
        race=uid()
        with ThreadPoolExecutor(2) as pool:
            setting=pool.submit(self.admin.request,'POST',self.color_path(),{'colors':body},self.color_headers(revision=2,key=race))
            cancelling=pool.submit(self.cancel_colors,race,body,2)
            set_reply,cancel_reply=setting.result(timeout=15),cancelling.result(timeout=15)
        self.assertEqual(cancel_reply.status,200)
        if cancel_reply.json()['state']=='cancelled':self.expect(set_reply,409,'operation_cancelled')
        else:self.expect(set_reply,200);self.assertEqual(cancel_reply.json()['operation'],set_reply.json())
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_port_color_operation WHERE request_id='{race}'"),'1')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{race}'"),'1')
        self.lab.sql(self.db,f"UPDATE user_port_colors SET revision={MAX_REVISION} WHERE owner_id='{self.admin_id}'")
        current=self.palette()['colors'];different={'rj45':'#fefefe'}
        before=self.durable();self.colors(different,revision=MAX_REVISION,status=409);self.assertEqual(before,self.durable())
        noop=self.colors(current,revision=MAX_REVISION).json();self.assertFalse(noop['result']['changed']);self.assertEqual(noop['revision'],MAX_REVISION)
        self.assertEqual(self.colors(body,revision=0,key=key).json(),first)
        scenarios=[('get','session'),('set','session'),('status','session'),('cancel','request'),('set','active'),('get','expiry'),('replay','session')]
        for index,(route,change) in enumerate(scenarios):
            user,_,_=self.add_user('colors-wait-'+str(index));request=uid()
            if route=='replay':request=self.colors(client=user).json()['requestId']
            label='colors969_'+uid();family='user-port-color-operation' if change=='request' else 'user-port-colors'
            lock=f'RackClick/{family}/{self.house_id}/{user.actor_id}'+('/'+request if change=='request' else '')
            if change=='expiry':self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{user.actor_id}'")
            with ThreadPoolExecutor(2) as pool:
                holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT pg_advisory_xact_lock(hashtextextended('{lock}',0)); SELECT pg_sleep(3); COMMIT;")
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
                if route=='get':pending=pool.submit(user.request,'GET',self.color_path())
                elif route=='status':pending=pool.submit(user.request,'GET',self.color_path(request))
                else:pending=pool.submit(user.request,'POST',self.color_path(request,True) if route=='cancel' else self.color_path(),{'colors':body},self.color_headers(user,0,request))
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
                if change=='active':self.lab.sql(self.db,f"UPDATE app_user SET active=false WHERE id='{user.actor_id}'")
                elif change!='expiry':self.lab.sql(self.db,f"DELETE FROM app_session WHERE user_id='{user.actor_id}'")
                self.expect(pending.result(timeout=15),401);holder.result(timeout=10)
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_port_color_operation WHERE owner_id='{user.actor_id}'"),'1' if route=='replay' else '0')
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE actor_id='{user.actor_id}' AND action LIKE 'user.portColors.%'"),'1' if route=='replay' else '0')
        user,_,_=self.add_user('colors-session-row');label='colors969_session_'+uid()
        with ThreadPoolExecutor(2) as pool:
            holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT 1 FROM app_session WHERE user_id='{user.actor_id}' FOR UPDATE; SELECT pg_sleep(3); DELETE FROM app_session WHERE user_id='{user.actor_id}'; COMMIT;")
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            pending=pool.submit(user.request,'GET',self.color_path())
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
            self.expect(pending.result(timeout=15),401);holder.result(timeout=10)

    def test_04_populated_schema11_migration_twice_native37_table_backup_restore(self):
        self.assertEqual(self.lab.sql(self.db,'SELECT max(version) FROM schema_migration'),'11')
        self.fixture();private=self.config();self.sh(self.publish_intent(private))
        self.expect(self.admin.request('POST','/api/v1/me/preferences',{'key':'language','value':'es'},
            {'If-Match':'"preferences-0"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),200)
        self.server.close();original=self.rows();self.assertEqual(len(original),35)
        self.assertGreater(sum(bool(json.loads(v)) for v in original.values()),20)
        history=original['schema_migration'];preserved={k:v for k,v in original.items() if k!='schema_migration'}
        env=self.lab.environment();env['ConnectionStrings__RackClick']=self.db.connection(self.lab.port,runtime=False)
        for _ in range(2):
            result=subprocess.run([str(self.lab.dotnet),str(self.dll),'--migrate'],env=env,capture_output=True,text=True,
                encoding='utf-8',timeout=45,creationflags=NO_WINDOW)
            self.assertEqual(result.returncode,0,'Explicit migration failed; raw credentials stay private')
            self.assertEqual(self.rows(tables=preserved),preserved)
            self.assertEqual(self.lab.sql(self.db,"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM (SELECT * FROM schema_migration WHERE version<=11) t"),history)
        self.assertEqual(set(self.rows()),set(original)|TABLES)
        self.lab.grant_runtime(self.db);self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend);self.admin.server=self.server
        self.assertEqual(self.expect(self.server.request('GET','/health/ready'),200).json()['schemaVersion'],12)
        reader,_,_=self.add_user('colors-backup-reader',['inventory.read'],self.customer_id)
        receipt=self.colors({'rj45':'#123abc','rj45_poe':'#abcdef'}).json()
        self.colors({'usb_c':'#000000'},client=reader);fence=uid();self.cancel_colors(fence,{},revision=0)
        self.server.close();before=self.rows();self.assertEqual(len(before),37)
        dump=self.db.directory/'palette969.dump';env=self.lab.environment();env['PGPASSFILE']=str(self.db.directory/'owner.pgpass')
        common=['-h','127.0.0.1','-p',str(self.lab.port),'-w']
        result=subprocess.run([str(self.lab.pg_bin/'pg_dump.exe'),*common,'-U',self.db.owner,'-d',self.db.name,'--format=custom','--no-owner','--no-privileges','--file',str(dump)],env=env,capture_output=True,timeout=45,creationflags=NO_WINDOW)
        self.assertEqual(result.returncode,0,'Native dump failed; raw output stays private')
        restored=self.lab.create_database('palette969-restored');env['PGPASSFILE']=str(restored.directory/'owner.pgpass')
        result=subprocess.run([str(self.lab.pg_bin/'pg_restore.exe'),*common,'-U',restored.owner,'-d',restored.name,'--exit-on-error','--no-owner','--no-privileges',str(dump)],env=env,capture_output=True,timeout=45,creationflags=NO_WINDOW)
        self.assertEqual(result.returncode,0,'Native restore failed; raw output stays private')
        self.assertEqual(self.rows(restored),before);self.assertEqual(self.rows(),before)
        self.assertEqual(self.lab.sql(restored,f"SELECT result_json FROM user_port_color_operation WHERE request_id='{receipt['requestId']}'"),json.dumps(receipt,separators=(',',':')))
        self.assertEqual(self.lab.sql(restored,f"SELECT state FROM user_port_color_operation WHERE request_id='{fence}'"),'cancelled')
        self.__class__.backup_observation={'tableCount':37,'exactRows':True,'sourceUnchanged':True,'copiedSessionsUsed':False,
            'scope':'Native isolated database-only pg_dump/pg_restore; no operational package/update/QA selection.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['dll','baseline-dll','frontend','evidence']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--baseline-sha256',required=True);parser.add_argument('--case',action='append',required=True);args=parser.parse_args()
    available=[name for name in UserPortColors969.__dict__ if name.startswith('test_')]
    if set(args.case)-set(available):raise ValueError('Unknown palette focus')
    names=[name for name in available if name in args.case]
    args.dll=args.dll.resolve();args.baseline_dll=args.baseline_dll.resolve();args.frontend=args.frontend.resolve()
    if hashlib.sha256(args.baseline_dll.read_bytes()).hexdigest()!=args.baseline_sha256.lower() or args.baseline_dll==args.dll:
        raise ValueError('Distinct explicitly hashed frozen schema11 baseline required')
    args.evidence.mkdir(parents=True,exist_ok=False)
    files=[p for p in (WORKSPACE/'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files+=list((WORKSPACE/'development/server/database').glob('*.sql'))+[Path(__file__).resolve(),WORKSPACE/'development/catalog/rc9-catalog.json']
    support=['pg_support.py','test_postgres.py','test_inventory_postgres.py','test_inventory_changes.py','test_inventory_read_views.py','test_private_device_templates.py','test_private_template_configurations.py','test_shared_device_templates.py']
    files += [WORKSPACE/'development/server/tests'/name for name in support]
    def sources():return {p.relative_to(WORKSPACE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original=sources();server=distribution(args.dll.parent);frontend=distribution(args.frontend);baseline=distribution(args.baseline_dll.parent)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),
        'serverPath':str(args.dll.parent),'frontendPath':str(args.frontend),'baselinePath':str(args.baseline_dll.parent),
        'serverHashes':server,'frontendHashes':frontend,'baselineHashes':baseline,'sourceHashes':original,'selectedCases':names,
        'schemaVersion':12,'actualQaOpened':False,'historicalResultsReused':False}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lab=Lab('personal-port-colors969');UserPortColors969.lab=lab
    UserPortColors969.dll,UserPortColors969.frontend,UserPortColors969.baseline=args.dll,args.frontend,args.baseline_dll
    UserPortColors969.backup_observation=None
    report['versions']={name:subprocess.run([str(path),'--version'],capture_output=True,text=True,check=True,creationflags=NO_WINDOW).stdout.strip()
        for name,path in [('dotnet',lab.dotnet),('postgres',lab.pg_bin/'postgres.exe')]}
    started=time.monotonic()
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(UserPortColors969(name) for name in names))
        report.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started,3),labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers),sourcesUnchanged=original==sources(),
        serverUnchanged=server==distribution(args.dll.parent),frontendUnchanged=frontend==distribution(args.frontend),
        baselineUnchanged=baseline==distribution(args.baseline_dll.parent),backup=UserPortColors969.backup_observation)
    (args.evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(report[k] for k in ['successful','labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged','baselineUnchanged']) else 1


if __name__=='__main__':sys.exit(main())
