"""Seven bounded personal-favorite PostgreSQL focuses; frozen DLLs and new labs only."""
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
import uuid

from pg_support import Client, Lab, WORKSPACE, NO_WINDOW
from test_postgres import EvidenceResult, Tee
from test_inventory_read_views import InventoryReadViewsPostgres


def uid(): return str(uuid.uuid4())
MAX_REVISION = 9007199254740991
TABLES = {'user_catalog_favorites', 'user_catalog_favorite', 'user_catalog_favorite_operation'}


class CatalogFavoritesPostgres(InventoryReadViewsPostgres):
    baseline = None

    def path(self, customer=None, key=None, cancel=False):
        value = f'/api/v1/customers/{customer or self.customer_id}/catalog/favorites'
        return value + (f'/operations/{key}' if key else '') + ('/cancel' if cancel else '')

    def payload(self, preset='pdu', favorite=True, **changes):
        reference = json.loads((WORKSPACE/'development/catalog/rc9-catalog.json').read_text(encoding='utf-8'))
        return {'presetKey':preset, 'catalogVersion':reference['catalogVersion'],
            'catalogSha256':hashlib.sha256((WORKSPACE/'development/catalog/rc9-catalog.json').read_bytes()).hexdigest(),
            'favorite':favorite, **changes}

    def favs(self, client=None, customer=None, status=200):
        client = client or self.admin
        response = self.expect(client.request('GET', self.path(customer)), status)
        if status != 200: return response
        value = response.json()
        self.assertEqual(set(value), {'kind','customerId','ownerId','revision','catalogVersion','catalogSha256','presetKeys'})
        self.assertEqual(value['kind'], 'catalogFavorites'); self.assertEqual(value['ownerId'], client.actor_id)
        self.assertEqual(value['customerId'], customer or self.customer_id)
        self.assertEqual(response.headers.get('etag'), f'"favorites-{value["revision"]}"')
        self.assertEqual(value['presetKeys'], sorted(set(value['presetKeys'])))
        return value

    def set_fav(self, payload=None, revision=None, key=None, client=None, customer=None, status=200, headers=None):
        client = client or self.admin
        if revision is None: revision = self.favs(client,customer)['revision']
        response = self.expect(client.request('POST', self.path(customer), payload if payload is not None else self.payload(),
            {'If-Match':f'"favorites-{revision}"','Idempotency-Key':key or uid(),'X-RackClick-Actor':client.actor_id, **(headers or {})}),status)
        if status == 200:
            value = response.json()
            self.assertEqual(set(value), {'kind','ownerId','revision','requestId','operationId','result'})
            self.assertEqual(set(value['result']), {'presetKey','favorite','changed','catalogVersion','catalogSha256'})
            self.assertEqual(value['ownerId'], client.actor_id); self.assertEqual(value['kind'],'catalogFavorites')
            self.assertEqual(response.headers.get('etag'),f'"favorites-{value["revision"]}"')
        return response

    def outcome(self, key, client=None, customer=None, status=200):
        return self.expect((client or self.admin).request('GET',self.path(customer,key)),status)

    def cancel_fav(self, key, payload=None, revision=0, client=None, customer=None, status=200):
        client = client or self.admin
        return self.expect(client.request('POST',self.path(customer,key,True),payload or self.payload(),
            {'If-Match':f'"favorites-{revision}"','Idempotency-Key':key,'X-RackClick-Actor':client.actor_id}),status)

    def core(self):
        tables = self.lab.sql(self.db,"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
        # Session timestamps are operational; favorites may add only their own tables and audit rows.
        tables = [t for t in tables if t not in TABLES | {'audit_event','app_session'}]
        values = [self.lab.sql(self.db,f'SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),\'[]\') FROM "{t}" t') for t in tables]
        return hashlib.sha256('\n'.join(values).encode()).hexdigest()

    def test_01_new_database_migration_seven_to_eight_and_constraints(self):
        source = self.lab.create_database('fresh-schema7-migration')
        self.assertEqual(self.lab.bootstrap(source,'migration-seven',self.password,dll=self.baseline).returncode,0)
        self.assertEqual(self.lab.sql(source,'SELECT max(version) FROM schema_migration'),'7')
        original_names = self.lab.sql(source,"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
        def unchanged_rows():
            return {t:self.lab.sql(source,f'SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),\'[]\') FROM "{t}" t')
                    for t in original_names if t != 'schema_migration'}
        before = unchanged_rows(); history = self.lab.sql(source,'SELECT row_to_json(t) FROM schema_migration t ORDER BY version')
        environment = self.lab.environment(); environment['ConnectionStrings__RackClick'] = source.connection(self.lab.port,runtime=False)
        for _ in range(2):
            result = subprocess.run([str(self.lab.dotnet),str(self.dll),'--migrate'],env=environment,
                capture_output=True,text=True,encoding='utf-8',timeout=45,creationflags=NO_WINDOW)
            self.assertEqual(result.returncode,0,'Explicit migration failed; private configuration is not logged')
            self.assertTrue(before == unchanged_rows(),'Migration changed pre-existing rows')
            self.assertEqual(self.lab.sql(source,'SELECT row_to_json(t) FROM schema_migration t WHERE version<8 ORDER BY version'),history)
            self.assertEqual(self.lab.sql(source,'SELECT max(version) FROM schema_migration'),'8')
        names = set(self.lab.sql(source,"SELECT tablename FROM pg_tables WHERE schemaname='public'").splitlines())
        self.assertEqual(names,set(original_names)|TABLES)
        for name in TABLES: self.assertEqual(self.lab.sql(source,f'SELECT count(*) FROM {name}'),'0')
        self.lab.grant_runtime(source)
        self.assertEqual(self.lab.sql(source,f"SELECT has_schema_privilege('{source.runtime}','public','CREATE')"),'f')
        migrated = self.lab.start_server(source,dll=self.dll,frontend=self.frontend)
        try: self.assertEqual(migrated.request('GET','/health/ready').status,200)
        finally: migrated.close()
        self.lab.sql(self.db,f"INSERT INTO user_catalog_favorites(systemhaus_id,owner_id) VALUES('{self.house_id}','{self.admin_id}')")
        invalid = [f"UPDATE user_catalog_favorites SET revision={n}" for n in [-1,MAX_REVISION+1]]
        invalid += [f"INSERT INTO user_catalog_favorite VALUES('{self.house_id}','{self.admin_id}','{key}')" for key in ['', 'UPPER','x'*65]]
        invalid += [f"INSERT INTO user_catalog_favorite VALUES('{self.house_id}','{uid()}','pdu')"]
        for statement in invalid:
            with self.assertRaises(RuntimeError): self.lab.sql(self.db,statement)
        base = f"'{self.house_id}','{self.admin_id}','{uid()}','"+'A'*64+f"','committed','{uid()}',0,'{{}}'"
        for values in [base.replace("'committed'","'unknown'"),base.replace("'"+'A'*64+"'","'bad'"),
                       base.replace("0,'{}'", "-1,'{}'"),base.replace("'{}'","'[]'"),base.replace("'committed'", "'cancelled'").replace("'{}'", "'null'")]:
            with self.assertRaises(RuntimeError): self.lab.sql(self.db,'INSERT INTO user_catalog_favorite_operation(systemhaus_id,owner_id,request_id,request_hash,state,operation_id,revision,result_json) VALUES('+values+')')
        self.lab.sql(self.db,'INSERT INTO user_catalog_favorite_operation(systemhaus_id,owner_id,request_id,request_hash,state,operation_id,revision,result_json) VALUES('+base+')')
        with self.assertRaises(RuntimeError): self.lab.sql(self.db,'INSERT INTO user_catalog_favorite_operation(systemhaus_id,owner_id,request_id,request_hash,state,operation_id,revision,result_json) VALUES('+base.replace("'committed'","'cancelled'")+')')

    def test_02_empty_get_reader_scope_and_personal_isolation(self):
        reader,_,_ = self.add_user('favorite-reader',['inventory.read'],self.customer_id,customer_group=True)
        second,_,_ = self.add_user('favorite-second',['inventory.read'],self.customer_id)
        editor,_,_ = self.add_user('favorite-no-read',['inventory.edit'],self.customer_id)
        before = self.durable()
        self.assertEqual(self.favs(reader)['revision'],0); self.assertEqual(self.favs(reader)['presetKeys'],[])
        self.assertEqual(before,self.durable()); self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM user_catalog_favorites'),'0')
        result = self.set_fav(client=reader).json(); self.assertTrue(result['result']['changed']); self.assertEqual(result['revision'],1)
        self.assertEqual(self.favs(second)['presetKeys'],[]); self.assertEqual(self.favs()['presetKeys'],[])
        self.assertEqual(self.outcome(result['requestId'],second).json()['state'],'notRecorded')
        self.favs(editor,status=404); self.set_fav(client=editor,revision=0,status=404)
        hidden = self.customer('Hidden favorite context')['id']
        self.favs(reader,hidden,status=404); self.set_fav(client=reader,customer=hidden,revision=1,status=404)
        self.outcome(result['requestId'],reader,hidden,status=404); self.cancel_fav(result['requestId'],client=reader,customer=hidden,revision=0,status=404)
        self.favs(customer=uid(),status=404)
        anonymous = Client(self.server); self.expect(anonymous.request('GET',self.path()),401)
        spec = self.expect(self.admin.request('GET','/api/v1/openapi.json'),200).json()
        for name in ['UserCatalogFavoriteSet','UserCatalogFavoriteResult','UserCatalogFavoritesSnapshot','UserCatalogFavoriteStatus']:
            self.assertFalse(spec['components']['schemas'][name]['additionalProperties'])
        headers = spec['paths']['/api/v1/customers/{id}/catalog/favorites']['post']['parameters']
        self.assertTrue(next(p for p in headers if p['name']=='X-RackClick-Actor')['required'])

    def test_03_closed_validation_csrf_revocation_and_expiry_during_wait(self):
        good = self.payload(); headers = {'If-Match':'"favorites-0"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}
        invalid = [{**good,'ownerId':uid()}, {k:v for k,v in good.items() if k!='favorite'},
            {**good,'favorite':None},{**good,'favorite':1},{**good,'favorite':'true'}, {**good,'presetKey':'PDU'},
            {**good,'catalogSha256':'A'*64},{**good,'catalogVersion':None}]
        before = self.durable()
        for body in invalid: self.set_fav(body,revision=0,status=422)
        duplicate = json.dumps(good)[:-1]+',"favorite":false}'
        self.expect(self.admin.request('POST',self.path(),duplicate,{'Content-Type':'application/json',**headers}),422)
        for etag in ['"0"','"favorites-00"','"favorites--1"','favorites-0','"favorites-9007199254740992"']:
            self.set_fav(good,revision=0,status=422,headers={'If-Match':etag})
        self.expect(self.admin.request('POST',self.path(),good,{'Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),428)
        self.expect(self.admin.request('POST',self.path(),good,{'If-Match':'"favorites-0"','Idempotency-Key':uid()}),422)
        self.set_fav(good,revision=0,status=403,headers={'X-RackClick-CSRF':'bad'})
        self.set_fav(good,revision=0,status=409,headers={'X-RackClick-Actor':uid()})
        self.expect(self.admin.request('GET',self.path()+'?language=en'),422)
        self.set_fav(self.payload(preset='unknown'),revision=0,status=422)
        self.set_fav(self.payload(catalogVersion='old'),revision=0,status=409)
        self.assertEqual(before,self.durable())
        for route in ['get','set','status','cancel']:
            reader,group,_=self.add_user('favorites-revoke-'+route,['inventory.read'],self.customer_id)
            key = uid(); label = 'favorites_'+uid()
            lockkey = f'RackClick/catalog-favorites/{self.house_id}/{reader.actor_id}'
            with ThreadPoolExecutor(2) as pool:
                holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT pg_advisory_xact_lock(hashtextextended('{lockkey}',0)); SELECT pg_sleep(3); COMMIT;")
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
                if route=='get': pending=pool.submit(reader.request,'GET',self.path())
                elif route=='status': pending=pool.submit(reader.request,'GET',self.path(key=key))
                else: pending=pool.submit(reader.request,'POST',self.path(key=key,cancel=True) if route=='cancel' else self.path(),good,
                    {'If-Match':'"favorites-0"','Idempotency-Key':key,'X-RackClick-Actor':reader.actor_id})
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
                self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{group}'")
                self.expect(pending.result(timeout=15),404); holder.result(timeout=10)
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_catalog_favorite_operation WHERE owner_id='{reader.actor_id}'"),'0')
        # Expiration while an aggregate lock is held must be re-evaluated using wall clock.
        expired,_,_=self.add_user('favorites-expiring',['inventory.read'],self.customer_id)
        self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{expired.actor_id}'")
        label='favorites_expire_'+uid(); lockkey=f'RackClick/catalog-favorites/{self.house_id}/{expired.actor_id}'
        with ThreadPoolExecutor(2) as pool:
            holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT pg_advisory_xact_lock(hashtextextended('{lockkey}',0)); SELECT pg_sleep(3); COMMIT;")
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            pending=pool.submit(expired.request,'POST',self.path(),good,{'If-Match':'"favorites-0"','Idempotency-Key':uid(),'X-RackClick-Actor':expired.actor_id})
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
            self.expect(pending.result(timeout=15),401); holder.result(timeout=10)
        revoked,_,_=self.add_user('favorites-session-revoked',['inventory.read'],self.customer_id)
        label='favorites_session_'+uid()
        with ThreadPoolExecutor(2) as pool:
            holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT 1 FROM app_session WHERE user_id='{revoked.actor_id}' FOR UPDATE; SELECT pg_sleep(3); DELETE FROM app_session WHERE user_id='{revoked.actor_id}'; COMMIT;")
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            pending=pool.submit(revoked.request,'GET',self.path())
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
            self.expect(pending.result(timeout=15),401); holder.result(timeout=10)

    def test_04_noops_replay_cross_context_status_and_cancellation(self):
        second=self.customer('Second favorite context')['id']; before=self.core()
        noop=self.set_fav(self.payload(favorite=False)).json(); self.assertFalse(noop['result']['changed']); self.assertEqual(noop['revision'],0)
        first=self.set_fav().json(); original=self.payload(); key=first['requestId']
        self.set_fav(self.payload('ups')); self.set_fav(self.payload('pdu',False))
        current=self.favs()['revision']; self.assertEqual(current,3)
        replay=self.set_fav(original,revision=0,key=key,customer=second).json(); self.assertEqual(replay,first)
        status=self.outcome(key,customer=second).json(); self.assertEqual(status['revision'],current); self.assertEqual(status['operation'],first)
        self.assertEqual(self.cancel_fav(key,original,revision=0,customer=second).json(),status)
        self.set_fav({**original,'catalogSha256':'0'*64},revision=0,key=key,status=409)
        self.set_fav(original,revision=1,key=key,status=409)
        cancel_key=uid(); stale=self.payload(catalogVersion='old',catalogSha256='0'*64)
        cancelled=self.cancel_fav(cancel_key,stale,revision=0,customer=second).json()
        self.assertEqual(cancelled['state'],'cancelled'); self.assertIsNone(cancelled['operation']); self.assertEqual(cancelled['revision'],current)
        self.assertEqual(self.cancel_fav(cancel_key,stale,revision=0).json(),cancelled)
        self.assertEqual(self.outcome(cancel_key).json(),cancelled)
        self.set_fav(stale,revision=0,key=cancel_key,status=409)
        self.set_fav(original,revision=0,key=cancel_key,status=409)
        self.assertEqual(self.favs()['presetKeys'],['ups']); self.assertEqual(before,self.core())
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{key}'"),'1')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{cancel_key}'"),'1')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM operation WHERE request_id IN ('{key}','{cancel_key}')"),'0')
        # Neither generic inventory recovery nor a second actor sees this own-family journal.
        self.assertEqual(self.expect(self.admin.request('GET',f'/api/v1/customers/{self.customer_id}/operations/{key}'),200).json()['state'],'notRecorded')

    def test_05_stale_same_key_concurrency_and_revision_limit(self):
        good=self.payload(); key=uid()
        with ThreadPoolExecutor(2) as pool:
            replies=list(pool.map(lambda _:self.set_fav(good,revision=0,key=key).json(),range(2)))
        self.assertEqual(replies[0],replies[1]); self.assertEqual(self.favs()['revision'],1)
        before=self.durable(); self.set_fav(good,revision=0,status=412); self.assertEqual(before,self.durable())
        second=self.customer('Concurrent other context')['id']
        with ThreadPoolExecutor(2) as pool:
            replies=list(pool.map(lambda p:self.admin.request('POST',self.path(p[0]),self.payload(p[1]),
                {'If-Match':'"favorites-1"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),[(self.customer_id,'ups'),(second,'sw8')]))
        self.assertEqual(sorted(r.status for r in replies),[200,412])
        race=uid(); revision=self.favs()['revision']
        with ThreadPoolExecutor(2) as pool:
            set_pending=pool.submit(self.admin.request,'POST',self.path(),self.payload('shelf'),{'If-Match':f'"favorites-{revision}"','Idempotency-Key':race,'X-RackClick-Actor':self.admin_id})
            cancel_pending=pool.submit(self.admin.request,'POST',self.path(key=race,cancel=True),self.payload('shelf'),{'If-Match':f'"favorites-{revision}"','Idempotency-Key':race,'X-RackClick-Actor':self.admin_id})
            set_response,cancel_response=set_pending.result(timeout=15),cancel_pending.result(timeout=15)
        self.assertEqual(cancel_response.status,200)
        if cancel_response.json()['state']=='cancelled': self.expect(set_response,409,'operation_cancelled')
        else: self.expect(set_response,200); self.assertEqual(cancel_response.json()['operation'],set_response.json())
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_catalog_favorite_operation WHERE request_id='{race}'"),'1')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{race}'"),'1')
        self.lab.sql(self.db,f"UPDATE user_catalog_favorites SET revision={MAX_REVISION} WHERE owner_id='{self.admin_id}'")
        before=self.durable(); self.set_fav(self.payload('ap'),revision=MAX_REVISION,status=409); self.assertEqual(before,self.durable())
        self.assertFalse(self.set_fav(good,revision=MAX_REVISION).json()['result']['changed'])

    def test_06_rollback_audit_and_inventory_revision_untouched(self):
        self.fixture(); inventory=self.snapshot(); before=self.core(); revision=inventory['revision']
        self.lab.sql(self.db,"CREATE FUNCTION favorites_test_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'isolated rollback witness' USING ERRCODE='23514'; END $$; CREATE TRIGGER favorites_test_failure BEFORE INSERT ON user_catalog_favorite_operation FOR EACH ROW EXECUTE FUNCTION favorites_test_fail();")
        all_before=self.durable()
        try:
            self.set_fav(revision=0,status=409); self.assertEqual(all_before,self.durable())
            self.cancel_fav(uid(),revision=0,status=409); self.assertEqual(all_before,self.durable())
        finally: self.lab.sql(self.db,'DROP TRIGGER favorites_test_failure ON user_catalog_favorite_operation; DROP FUNCTION favorites_test_fail();')
        committed=self.set_fav().json(); after=self.snapshot()
        self.assertEqual(after,inventory); self.assertEqual(before,self.core())
        event=json.loads(self.lab.sql(self.db,f"SELECT row_to_json(t) FROM audit_event t WHERE id='{committed['operationId']}'"))
        self.assertEqual(event['action'],'user.catalogFavorite.set'); self.assertEqual(event['resource_id'],self.admin_id)
        self.assertEqual(event['before_json']['revision'],0); self.assertEqual(event['after_json']['revision'],1)
        self.assertNotIn('customerId',event['before_json']); self.assertNotIn('customerId',event['after_json'])
        self.assertEqual(self.poll(revision)['events'],[])

    def test_07_restart_new_login_recovery_and_other_actor(self):
        _,_,_,rack=self.hierarchy(); self.device('Preserved inventory',rack=rack['id'])
        other,_,_=self.add_user('favorite-other',['inventory.read'],self.customer_id)
        first=self.set_fav().json(); self.set_fav(self.payload('ap')); inventory=self.snapshot(); wanted=self.favs()
        self.assertEqual(self.favs(other)['presetKeys'],[])
        cancel_key=uid(); self.cancel_fav(cancel_key,self.payload('ups'),revision=2)
        self.server.close(); self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend)
        self.admin.server=other.server=self.server
        fresh=Client(self.server); fresh.actor_id=self.admin_id; self.expect(fresh.login('qa-inventory-admin',self.password),200)
        self.assertEqual(self.favs(fresh),wanted); self.assertEqual(self.snapshot(client=other),inventory)
        self.assertEqual(self.outcome(first['requestId'],fresh).json()['operation'],first)
        self.assertEqual(self.outcome(cancel_key,fresh).json()['state'],'cancelled')
        self.set_fav(self.payload('ups'),revision=2,key=cancel_key,client=fresh,status=409)
        self.assertEqual(self.favs(other)['presetKeys'],[])


def distribution(path):
    return {p.relative_to(path).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob('*')) if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['dll','baseline-dll','frontend','evidence']: parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',action='append',required=True); args=parser.parse_args()
    available=[n for n in CatalogFavoritesPostgres.__dict__ if n.startswith('test_')]
    if set(args.case)-set(available): raise ValueError('Unknown favorite focus')
    names=[n for n in available if n in args.case]
    args.dll=args.dll.resolve(); args.baseline_dll=args.baseline_dll.resolve(); args.frontend=args.frontend.resolve()
    if not args.baseline_dll.is_file() or args.baseline_dll==args.dll: raise ValueError('Distinct frozen schema7 baseline DLL required')
    args.evidence.mkdir(parents=True,exist_ok=False)
    files=[p for p in (WORKSPACE/'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files+=list((WORKSPACE/'development/server/database').glob('*.sql'))+[Path(__file__).resolve(),WORKSPACE/'development/catalog/rc9-catalog.json']
    files+=[WORKSPACE/'development/server/tests'/n for n in ['pg_support.py','test_postgres.py','test_inventory_postgres.py','test_inventory_changes.py','test_inventory_read_views.py']]
    def sources(): return {p.relative_to(WORKSPACE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original=sources(); server=distribution(args.dll.parent); frontend=distribution(args.frontend); baseline=distribution(args.baseline_dll.parent)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),
        'serverPath':str(args.dll.parent),'frontendPath':str(args.frontend),'baselinePath':str(args.baseline_dll.parent),
        'serverHashes':server,'frontendHashes':frontend,'baselineHashes':baseline,'sourceHashes':original,'selectedCases':names,
        'schemaVersion':8,'actualQaOpened':False,'historicalResultsReused':False}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lab=Lab('personal-catalog-favorites'); CatalogFavoritesPostgres.lab=lab
    CatalogFavoritesPostgres.dll,CatalogFavoritesPostgres.frontend,CatalogFavoritesPostgres.baseline=args.dll,args.frontend,args.baseline_dll
    report['versions']={name:subprocess.run([str(path),'--version'],capture_output=True,text=True,check=True,creationflags=NO_WINDOW).stdout.strip()
        for name,path in [('dotnet',lab.dotnet),('postgres',lab.pg_bin/'postgres.exe')]}
    started=time.monotonic()
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(CatalogFavoritesPostgres(n) for n in names))
        report.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started,3),labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers),sourcesUnchanged=original==sources(),
        serverUnchanged=server==distribution(args.dll.parent),frontendUnchanged=frontend==distribution(args.frontend),baselineUnchanged=baseline==distribution(args.baseline_dll.parent))
    (args.evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(report[k] for k in ['successful','labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged','baselineUnchanged']) else 1


if __name__=='__main__': sys.exit(main())
