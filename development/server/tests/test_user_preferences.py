"""Eight bounded session-owned preference focuses; new native PostgreSQL labs only."""
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
TABLES = {'user_preferences', 'user_preference_operation'}
BASELINE_SHA256 = '0bf15fbac4083ef4e35d4a75222e3467b5bdcc35326d54a9901f385b480b7f23'


class UserPreferencesPostgres(SharedDeviceTemplatesPostgres):
    baseline = None

    def setUp(self):
        target = self.dll
        if self._testMethodName.startswith('test_01_'): self.dll = self.baseline
        try: super().setUp()
        finally: self.dll = target

    def pref_path(self, key=None, cancel=False):
        return '/api/v1/me/preferences' + (f'/operations/{key}' if key else '') + ('/cancel' if cancel else '')

    def prefs(self, client=None, status=200):
        client = client or self.admin
        response = self.expect(client.request('GET', self.pref_path()), status)
        if status != 200: return response
        value = response.json()
        self.assertEqual(set(value), {'kind', 'ownerId', 'revision', 'language', 'theme'})
        self.assertEqual(value['kind'], 'userPreferences'); self.assertEqual(value['ownerId'], client.actor_id)
        self.assertIn(value['language'], (None, 'en', 'de', 'es')); self.assertIn(value['theme'], (None, 'dark', 'light'))
        self.assertEqual(response.headers.get('etag'), f'"preferences-{value["revision"]}"')
        return value

    def set_pref(self, body=None, revision=None, key=None, client=None, status=200, headers=None):
        client = client or self.admin
        if revision is None: revision = self.prefs(client)['revision']
        response = self.expect(client.request('POST', self.pref_path(), body if body is not None else {'key':'language','value':'es'},
            {'If-Match':f'"preferences-{revision}"', 'Idempotency-Key':key or uid(), 'X-RackClick-Actor':client.actor_id,
             **(headers or {})}), status)
        if status == 200:
            value = response.json()
            self.assertEqual(set(value), {'kind','ownerId','revision','requestId','operationId','result'})
            self.assertEqual(set(value['result']), {'key','value','changed'}); self.assertIsInstance(value['result']['changed'],bool)
            self.assertEqual(value['kind'],'userPreferences'); self.assertEqual(value['ownerId'],client.actor_id)
            self.assertEqual(response.headers.get('etag'),f'"preferences-{value["revision"]}"')
        return response

    def pref_status(self, key, client=None, status=200):
        response = self.expect((client or self.admin).request('GET',self.pref_path(key)),status)
        if status == 200:
            value=response.json();self.assertEqual(set(value),{'state','ownerId','revision','requestId','operation'})
            self.assertEqual(value['ownerId'],(client or self.admin).actor_id);self.assertEqual(value['requestId'],key)
            self.assertEqual(response.headers.get('etag'),f'"preferences-{value["revision"]}"')
        return response

    def cancel_pref(self, key, body=None, revision=0, client=None, status=200, headers=None):
        client=client or self.admin
        return self.expect(client.request('POST',self.pref_path(key,True),body or {'key':'language','value':'es'},
            {'If-Match':f'"preferences-{revision}"','Idempotency-Key':key,'X-RackClick-Actor':client.actor_id,**(headers or {})}),status)

    def row_snapshots(self, database=None, tables=None):
        database=database or self.db
        if tables is None: tables=self.lab.sql(database,"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
        return {name:self.lab.sql(database,f'SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),\'[]\') FROM "{name}" t') for name in tables}

    def unchanged_core(self):
        names=self.lab.sql(self.db,"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
        return self.row_snapshots(tables=[n for n in names if n not in TABLES|{'audit_event','app_session'}])

    def once_pref(self,key,action='user.preference.set'):
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_preference_operation WHERE request_id='{key}'"),'1')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{key}' AND action='{action}'"),'1')

    def test_01_populated_schema10_to11_migration_and_strict_constraints(self):
        self.assertEqual(self.lab.sql(self.db,'SELECT max(version) FROM schema_migration'),'10')
        self.fixture(); private=self.config(); self.sh(self.publish_intent(private))
        reference=WORKSPACE/'development/catalog/rc9-catalog.json'; catalog=json.loads(reference.read_text(encoding='utf-8'))
        favorite={'presetKey':'pdu','favorite':True,'catalogVersion':catalog['catalogVersion'],'catalogSha256':hashlib.sha256(reference.read_bytes()).hexdigest()}
        self.expect(self.admin.request('POST',f'/api/v1/customers/{self.customer_id}/catalog/favorites',favorite,
            {'If-Match':'"favorites-0"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),200)
        self.server.close()
        original=self.row_snapshots(); self.assertEqual(len(original),33)
        old_history=original['schema_migration']; preserved={k:v for k,v in original.items() if k!='schema_migration'}
        self.assertGreater(sum(bool(json.loads(v)) for v in original.values()),20,'Migration fixture must contain real historical records')
        environment=self.lab.environment();environment['ConnectionStrings__RackClick']=self.db.connection(self.lab.port,runtime=False)
        for _ in range(2):
            result=subprocess.run([str(self.lab.dotnet),str(self.dll),'--migrate'],env=environment,capture_output=True,
                text=True,encoding='utf-8',timeout=45,creationflags=NO_WINDOW)
            self.assertEqual(result.returncode,0,'Explicit migration failed; credentials remain private')
            self.assertEqual(self.row_snapshots(tables=preserved),preserved)
            self.assertEqual(self.lab.sql(self.db,"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM (SELECT * FROM schema_migration WHERE version<=10) t"),old_history)
        current=self.row_snapshots();self.assertEqual(set(current),set(original)|TABLES)
        self.assertEqual(len(current),35);self.assertEqual(json.loads(current['user_preferences']),[]);self.assertEqual(json.loads(current['user_preference_operation']),[])
        self.lab.grant_runtime(self.db);self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend);self.admin.server=self.server
        self.assertEqual(self.expect(self.server.request('GET','/health/ready'),200).json()['schemaVersion'],11)
        before=self.durable(); self.assertEqual(self.prefs()['revision'],0);self.assertEqual(before,self.durable())
        receipt=self.set_pref().json();key=receipt['requestId'];owner=self.admin_id;house=self.house_id
        for sql in [f"UPDATE user_preferences SET revision={n}" for n in (-1,MAX_REVISION+1)]+[
            "UPDATE user_preferences SET language='ES'", "UPDATE user_preferences SET theme='blue'",
            f"INSERT INTO user_preferences(systemhaus_id,owner_id) VALUES('{house}','{uid()}')",
            "UPDATE user_preference_operation SET result_version=2", "UPDATE user_preference_operation SET result_sha256='"+'A'*64+"'",
            "UPDATE user_preference_operation SET request_hash='bad'", "UPDATE user_preference_operation SET revision=-1",
            "UPDATE user_preference_operation SET state='unknown'", "UPDATE user_preference_operation SET operation_id='00000000-0000-0000-0000-000000000000'",
            "UPDATE user_preference_operation SET request_id='00000000-0000-0000-0000-000000000000'"]:
            with self.assertRaises(RuntimeError):self.lab.sql(self.db,sql)
        invalid=[[],{},None,{**receipt,'kind':None},{**receipt,'ownerId':uid()},{**receipt,'revision':'1'},
            {**receipt,'result':None},{**receipt,'result':{'key':'language','value':None,'changed':True}},
            {**receipt,'result':{'key':'language','changed':True}},
            {**receipt,'result':{'key':'language','value':'es','changed':'true'}},
            {**receipt,'result':{'key':'theme','value':'es','changed':True}},
            {**receipt,'result':{'key':'language','value':'es','changed':True,'extra':1}}, {**receipt,'extra':1}]
        before=self.durable()
        for value in invalid:
            text=literal(json.dumps(value,separators=(',',':')))
            with self.assertRaises(RuntimeError):self.lab.sql(self.db,f"UPDATE user_preference_operation SET result_json={text},result_sha256=upper(encode(sha256(convert_to({text},'UTF8')),'hex')) WHERE request_id='{key}'")
            self.assertEqual(before,self.durable())
        fence=uid();self.cancel_pref(fence,revision=1)
        raw=json.loads(self.lab.sql(self.db,f"SELECT result_json FROM user_preference_operation WHERE request_id='{fence}'"))
        for value in [{**raw,'operation':{}},{**raw,'state':None},{k:v for k,v in raw.items() if k!='operation'}]:
            text=literal(json.dumps(value,separators=(',',':')))
            with self.assertRaises(RuntimeError):self.lab.sql(self.db,f"UPDATE user_preference_operation SET result_json={text},result_sha256=upper(encode(sha256(convert_to({text},'UTF8')),'hex')) WHERE request_id='{fence}'")

    def test_02_readonly_get_reader_no_customer_grants_and_owner_isolation(self):
        reader,_,_=self.add_user('prefs-reader',['inventory.read'],self.customer_id)
        no_scope,_,_=self.add_user('prefs-no-customers')
        self.assertEqual(self.expect(no_scope.request('GET','/api/v1/customers'),200).json(),[])
        before=self.durable();self.assertEqual(self.prefs(reader)['language'],None);self.assertEqual(self.prefs(no_scope)['theme'],None)
        self.assertEqual(before,self.durable());self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM user_preferences'),'0')
        grants=self.lab.sql(self.db,"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM permission_grant t")
        first=self.set_pref(client=reader).json();self.assertEqual(first['revision'],1)
        self.set_pref({'key':'theme','value':'light'},client=no_scope)
        self.assertEqual(self.prefs()['revision'],0);self.assertEqual(self.prefs(no_scope)['language'],None)
        self.assertEqual(self.prefs(reader)['theme'],None)
        self.assertEqual(self.pref_status(first['requestId'],no_scope).json()['state'],'notRecorded')
        self.assertEqual(self.lab.sql(self.db,"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM permission_grant t"),grants)
        self.expect(Client(self.server).request('GET',self.pref_path()),401)
        self.lab.sql(self.db,f"UPDATE app_user SET active=false WHERE id='{no_scope.actor_id}'")
        self.prefs(no_scope,status=401);self.set_pref(revision=1,client=no_scope,status=401)

    def test_03_closed_dto_headers_csrf_origin_and_openapi(self):
        before=self.durable();good={'key':'language','value':'es'}
        headers={'If-Match':'"preferences-0"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}
        for body in [{},[],None,{'key':'language'}, {**good,'ownerId':uid()},{**good,'customerId':self.customer_id},
            {**good,'revision':0},{'key':'language','value':None},{'key':'language','value':True},
            {'key':'theme','value':'es'},{'key':'language','value':'ES'},{'key':'language','value':' es'},
            {'key':'theme','value':'dark '},{'key':'unknown','value':'en'},{'key':None,'value':'en'},{'key':1,'value':'en'}]:
            # Explicit JSON null must have an actual body, unlike the helper's default argument.
            payload='null' if body is None else body
            self.expect(self.admin.request('POST',self.pref_path(),payload,{**headers,'Content-Type':'application/json'}),422)
        self.expect(self.admin.request('POST',self.pref_path(),'{"key":"language","value":"es","value":"en"}',{**headers,'Content-Type':'application/json'}),422)
        for etag in ['"1"','"preferences-00"','"preferences--1"','preferences-0','"preferences-9007199254740992"','W/"preferences-0"','"preferences-0", "preferences-1"']:
            self.set_pref(revision=0,status=422,headers={'If-Match':etag})
        self.expect(self.admin.request('POST',self.pref_path(),good,{'Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),428)
        self.expect(self.admin.request('POST',self.pref_path(),good,{'If-Match':'"preferences-0"','Idempotency-Key':uid()}),422)
        self.set_pref(revision=0,status=422,headers={'X-RackClick-Actor':'invalid'})
        self.set_pref(revision=0,status=409,headers={'X-RackClick-Actor':uid()})
        for request_id in ['invalid','00000000-0000-0000-0000-000000000000']:
            self.set_pref(revision=0,status=422,headers={'Idempotency-Key':request_id})
            self.expect(self.admin.request('GET',self.pref_path(request_id)),422)
            self.expect(self.admin.request('POST',self.pref_path(request_id,True),good,headers),422)
        self.set_pref(revision=0,status=403,headers={'X-RackClick-CSRF':'bad'})
        self.set_pref(revision=0,status=403,headers={'Origin':'https://wrong.invalid'})
        for path in [self.pref_path(),self.pref_path(uid())]:
            self.expect(self.admin.request('GET',path+'?ownerId='+uid()),422)
            self.expect(self.admin.request('GET',path,{'body':'forbidden'}),422)
        self.expect(self.admin.request('POST',self.pref_path()+'?customerId='+self.customer_id,good,headers),422)
        key=uid();self.cancel_pref(key,status=422,headers={'Idempotency-Key':uid()})
        self.expect(self.admin.request('POST',self.pref_path(key,True)+'?extra=1',good,{**headers,'Idempotency-Key':key}),422)
        self.assertEqual(before,self.durable())
        document=self.expect(self.admin.request('GET','/api/v1/openapi.json'),200).json()
        for name in ['UserPreferenceSet','UserPreferenceChange','UserPreferencesSnapshot','UserPreferenceResult','UserPreferenceStatus']:
            self.assertFalse(document['components']['schemas'][name]['additionalProperties'])
        for path,methods in [(self.pref_path(),['get','post']),('/api/v1/me/preferences/operations/{requestId}',['get']),('/api/v1/me/preferences/operations/{requestId}/cancel',['post'])]:
            for method in methods:
                operation=document['paths'][path][method];self.assertNotIn('404',operation['responses'])
                self.assertFalse(any(p['name']=='id' for p in operation['parameters']))
                if method=='post':self.assertTrue(next(p for p in operation['parameters'] if p['name']=='X-RackClick-Actor')['required'])

    def test_04_noops_replay_historical_receipt_and_durable_fences(self):
        first=self.set_pref().json();key=first['requestId'];original={'key':'language','value':'es'}
        self.assertEqual(first['revision'],1)
        self.set_pref({'key':'theme','value':'light'})
        noop=self.set_pref(original).json();self.assertFalse(noop['result']['changed']);self.assertEqual(noop['revision'],2)
        self.set_pref({'key':'language','value':'en'});current=self.prefs();self.assertEqual(current['revision'],3)
        self.assertEqual(self.set_pref(original,revision=0,key=key).json(),first)
        status=self.pref_status(key).json();self.assertEqual(status['revision'],3);self.assertEqual(status['operation'],first)
        self.assertEqual(self.cancel_pref(key,original,revision=0).json(),status)
        self.set_pref({'key':'language','value':'de'},revision=0,key=key,status=409)
        self.set_pref(original,revision=1,key=key,status=409)
        fence=uid();wanted={'key':'theme','value':'dark'}
        cancelled=self.cancel_pref(fence,wanted,revision=0).json();self.assertEqual(cancelled['state'],'cancelled')
        self.assertEqual(cancelled['revision'],3);self.assertIsNone(cancelled['operation'])
        self.assertEqual(self.cancel_pref(fence,wanted,revision=0).json(),cancelled)
        self.assertEqual(self.pref_status(fence).json(),cancelled)
        self.set_pref(wanted,revision=0,key=fence,status=409)
        self.set_pref(wanted,revision=3,key=fence,status=409)
        self.assertEqual(self.prefs(),current)
        for receipt in [first,noop]:self.once_pref(receipt['requestId'])
        self.once_pref(fence,'user.preference.set.cancel')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM operation WHERE request_id IN ('{key}','{fence}')"),'0')
        empty,_,_=self.add_user('prefs-empty-fence');empty_key=uid();self.cancel_pref(empty_key,client=empty)
        self.assertEqual(self.prefs(empty),{'kind':'userPreferences','ownerId':empty.actor_id,'revision':0,'language':None,'theme':None})
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_preferences WHERE owner_id='{empty.actor_id}'"),'0')

    def test_05_concurrency_stale_revision_cross_key_and_limit(self):
        key=uid();body={'key':'language','value':'es'}
        with ThreadPoolExecutor(2) as pool:
            replies=list(pool.map(lambda _:self.set_pref(body,revision=0,key=key).json(),range(2)))
        self.assertEqual(replies[0],replies[1]);first=replies[0];self.once_pref(key)
        before=self.durable();self.set_pref(body,revision=0,status=412);self.assertEqual(before,self.durable())
        with ThreadPoolExecutor(2) as pool:
            replies=list(pool.map(lambda p:self.admin.request('POST',self.pref_path(),p,
                {'If-Match':'"preferences-1"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),
                [{'key':'language','value':'de'},{'key':'theme','value':'light'}]))
        self.assertEqual(sorted(r.status for r in replies),[200,412]);self.assertEqual(self.prefs()['revision'],2)
        race=uid();body={'key':'theme','value':'dark'}
        with ThreadPoolExecutor(2) as pool:
            pending=pool.submit(self.admin.request,'POST',self.pref_path(),body,{'If-Match':'"preferences-2"','Idempotency-Key':race,'X-RackClick-Actor':self.admin_id})
            cancel=pool.submit(self.cancel_pref,race,body,2)
            set_response,cancel_response=pending.result(timeout=15),cancel.result(timeout=15)
        self.assertEqual(cancel_response.status,200)
        if cancel_response.json()['state']=='cancelled':self.expect(set_response,409,'operation_cancelled')
        else:self.expect(set_response,200);self.assertEqual(cancel_response.json()['operation'],set_response.json())
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_preference_operation WHERE request_id='{race}'"),'1')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{race}'"),'1')
        self.lab.sql(self.db,f"UPDATE user_preferences SET revision={MAX_REVISION} WHERE owner_id='{self.admin_id}'")
        snapshot=self.prefs();changed={'key':'language','value':'de' if snapshot['language']!='de' else 'en'}
        before=self.durable();self.set_pref(changed,revision=MAX_REVISION,status=409);self.assertEqual(before,self.durable())
        noop=self.set_pref({'key':'language','value':snapshot['language']},revision=MAX_REVISION).json()
        self.assertFalse(noop['result']['changed']);self.assertEqual(noop['revision'],MAX_REVISION)
        self.assertEqual(self.set_pref({'key':'language','value':'es'},revision=0,key=key).json(),first)

    def test_06_revoke_deactivate_expire_during_aggregate_or_request_wait(self):
        body={'key':'language','value':'es'}
        scenarios=[('get','session'),('set','session'),('status','session'),('cancel','session'),('set','active'),('get','expiry'),('replay','session'),('cancel','request')]
        for index,(route,change) in enumerate(scenarios):
            user,_,_=self.add_user('prefs-wait-'+str(index));key=uid();revision=0
            if route=='replay':key=self.set_pref(client=user).json()['requestId']
            label='preferences_wait_'+uid();family='user-preference-operation' if change=='request' else 'user-preferences'
            lock=f'RackClick/{family}/{self.house_id}/{user.actor_id}'+('/'+key if change=='request' else '')
            if change=='expiry':self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{user.actor_id}'")
            with ThreadPoolExecutor(2) as pool:
                holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT pg_advisory_xact_lock(hashtextextended('{lock}',0)); SELECT pg_sleep(3); COMMIT;")
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
                if route=='get':pending=pool.submit(user.request,'GET',self.pref_path())
                elif route=='status':pending=pool.submit(user.request,'GET',self.pref_path(key))
                else:pending=pool.submit(user.request,'POST',self.pref_path(key,True) if route=='cancel' else self.pref_path(),body,
                    {'If-Match':f'"preferences-{revision}"','Idempotency-Key':key,'X-RackClick-Actor':user.actor_id})
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
                if change=='active':self.lab.sql(self.db,f"UPDATE app_user SET active=false WHERE id='{user.actor_id}'")
                elif change!='expiry':self.lab.sql(self.db,f"DELETE FROM app_session WHERE user_id='{user.actor_id}'")
                self.expect(pending.result(timeout=15),401);holder.result(timeout=10)
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_preference_operation WHERE owner_id='{user.actor_id}'"),'1' if route=='replay' else '0')
        # A session row lock itself must also re-evaluate the wall clock after acquisition.
        user,_,_=self.add_user('prefs-session-row-wait');label='preferences_session_'+uid()
        with ThreadPoolExecutor(2) as pool:
            holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT 1 FROM app_session WHERE user_id='{user.actor_id}' FOR UPDATE; SELECT pg_sleep(3); DELETE FROM app_session WHERE user_id='{user.actor_id}'; COMMIT;")
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            pending=pool.submit(user.request,'GET',self.pref_path())
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
            self.expect(pending.result(timeout=15),401);holder.result(timeout=10)

    def test_07_atomic_rollback_audit_and_inventory_untouched(self):
        self.fixture();inventory=self.snapshot();before=self.unchanged_core();house=self.lab.sql(self.db,'SELECT revision FROM systemhaus')
        self.lab.sql(self.db,"CREATE FUNCTION preferences_test_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'isolated rollback witness' USING ERRCODE='23514'; END $$; CREATE TRIGGER preferences_test_failure BEFORE INSERT ON user_preference_operation FOR EACH ROW EXECUTE FUNCTION preferences_test_fail();")
        all_before=self.durable()
        try:
            self.set_pref(revision=0,status=409);self.assertEqual(all_before,self.durable())
            self.cancel_pref(uid(),status=409);self.assertEqual(all_before,self.durable())
        finally:self.lab.sql(self.db,'DROP TRIGGER preferences_test_failure ON user_preference_operation; DROP FUNCTION preferences_test_fail();')
        committed=self.set_pref().json();self.assertEqual(self.snapshot(),inventory);self.assertEqual(self.unchanged_core(),before)
        self.assertEqual(self.lab.sql(self.db,'SELECT revision FROM systemhaus'),house)
        self.assertEqual(self.poll(inventory['revision'])['events'],[])
        event=json.loads(self.lab.sql(self.db,f"SELECT row_to_json(t) FROM audit_event t WHERE id='{committed['operationId']}'"))
        self.assertEqual(event['action'],'user.preference.set');self.assertEqual(event['resource_id'],self.admin_id)
        self.assertEqual(event['before_json'],{'ownerId':self.admin_id,'revision':0,'key':'language','value':None})
        self.assertEqual(event['after_json'],{'ownerId':self.admin_id,'revision':1,'key':'language','value':'es','changed':True})
        self.assertIsNone(event.get('customer_id'));self.assertNotIn('customerId',event['after_json'])
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_context WHERE event_id='{committed['operationId']}'"),'0')

    def test_08_restart_reauthentication_isolation_and_status(self):
        other,_,_=self.add_user('prefs-restart-other')
        first=self.set_pref().json();self.set_pref({'key':'theme','value':'light'});wanted=self.prefs()
        fence=uid();self.cancel_pref(fence,{'key':'theme','value':'dark'},revision=2)
        other_first=self.set_pref({'key':'language','value':'de'},client=other).json()
        self.server.close();self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend)
        self.admin.server=other.server=self.server
        fresh=Client(self.server);fresh.actor_id=self.admin_id;self.expect(fresh.login('qa-inventory-admin',self.password),200)
        fresh_other=Client(self.server);fresh_other.actor_id=other.actor_id;self.expect(fresh_other.login('prefs-restart-other',self.password),200)
        self.assertEqual(self.prefs(fresh),wanted);self.assertEqual(self.pref_status(first['requestId'],fresh).json()['operation'],first)
        self.assertEqual(self.pref_status(fence,fresh).json()['state'],'cancelled')
        self.assertEqual(self.prefs(fresh_other)['language'],'de');self.assertIsNone(self.prefs(fresh_other)['theme'])
        self.assertEqual(self.pref_status(other_first['requestId'],fresh).json()['state'],'notRecorded')
        self.set_pref({'key':'theme','value':'dark'},revision=2,key=fence,client=fresh,status=409)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['dll','baseline-dll','frontend','evidence']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',action='append',required=True);args=parser.parse_args()
    available=[n for n in UserPreferencesPostgres.__dict__ if n.startswith('test_')]
    if set(args.case)-set(available):raise ValueError('Unknown preference focus')
    names=[n for n in available if n in args.case]
    args.dll=args.dll.resolve();args.baseline_dll=args.baseline_dll.resolve();args.frontend=args.frontend.resolve()
    if hashlib.sha256(args.baseline_dll.read_bytes()).hexdigest()!=BASELINE_SHA256 or args.baseline_dll==args.dll:raise ValueError('Distinct frozen schema10 candidate592 baseline required')
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
        'schemaVersion':11,'actualQaOpened':False,'historicalResultsReused':False}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lab=Lab('personal-preferences712');UserPreferencesPostgres.lab=lab
    UserPreferencesPostgres.dll,UserPreferencesPostgres.frontend,UserPreferencesPostgres.baseline=args.dll,args.frontend,args.baseline_dll
    report['versions']={name:subprocess.run([str(path),'--version'],capture_output=True,text=True,check=True,creationflags=NO_WINDOW).stdout.strip()
        for name,path in [('dotnet',lab.dotnet),('postgres',lab.pg_bin/'postgres.exe')]}
    started=time.monotonic()
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(UserPreferencesPostgres(n) for n in names))
        report.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started,3),labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers),sourcesUnchanged=original==sources(),
        serverUnchanged=server==distribution(args.dll.parent),frontendUnchanged=frontend==distribution(args.frontend),baselineUnchanged=baseline==distribution(args.baseline_dll.parent))
    (args.evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(report[k] for k in ['successful','labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged','baselineUnchanged']) else 1


if __name__=='__main__':sys.exit(main())
