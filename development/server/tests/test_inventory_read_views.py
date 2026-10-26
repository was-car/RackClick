"""Inventory screen queries: explicit frozen artifacts and fresh PostgreSQL labs."""
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
from urllib.parse import urlencode
import uuid

from pg_support import Lab, WORKSPACE, NO_WINDOW, literal
from test_postgres import EvidenceResult, Tee
from test_inventory_changes import InventoryChangesPostgres


def uid(): return str(uuid.uuid4())


class InventoryReadViewsPostgres(InventoryChangesPostgres):
    def fixture(self):
        site, building, room, rack = self.hierarchy()
        device, groups, ports = self.device('Café 同名', rack=rack['id'])
        dose, dg, dp = self.device('Café 同名', room=room['id'], kind='dose')
        cable = self.connect(ports[0], dp[0], note='Nota ñ literal %_ SQL', color='#12aBcD', patch='tested')
        self.port_changes(device, groups[0], [ports[1]], {'status': 'reserved', 'label': 'Étiquette'})
        return site, building, room, rack, device, groups, ports, dose, dp, cable

    def view(self, view='search', query=None, revision=None, customer=None, client=None, status=200, raw=None):
        customer = customer or self.customer_id
        if revision is None: revision = self.snapshot(customer)['revision']
        path = f'/api/v1/customers/{customer}/inventory/{view}'
        encoded = raw if raw is not None else urlencode(query or {})
        response = self.expect((client or self.admin).request('GET', path + ('?' + encoded if encoded else ''),
            headers={'If-Match': f'"{revision}"'}), status)
        if status != 200: return response
        value = response.json()
        self.assertEqual(set(value), {'customerId','revision','query','kind','status','family','offset','limit','total','nextOffset','items'})
        self.assertEqual(value['customerId'], customer); self.assertEqual(value['revision'], revision)
        self.assertEqual(response.headers['etag'], f'"{revision}"')
        self.assertTrue(all(item['customerId'] == customer for item in value['items']))
        self.assertEqual([p['id'] for p in value['items']], sorted(p['id'] for p in value['items']))
        return value

    def tables(self):
        names = ['customer','inventory_site','inventory_building','inventory_room','inventory_rack','inventory_device',
            'inventory_port_group','inventory_port','inventory_connection','inventory_connection_endpoint','operation','audit_event',
            'audit_context','audit_context_object']
        existing = set(self.lab.sql(self.db, "SELECT tablename FROM pg_tables WHERE schemaname='public'").splitlines())
        return {name: self.lab.sql(self.db, f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM {name} t")
            for name in names if name in existing}

    def test_search_unicode_homonyms_input_readonly(self):
        self.fixture(); before = self.tables()
        result = self.view(query={'query': 'CAFE\u0301', 'kind': 'device'})
        self.assertEqual(result['total'], 2); self.assertEqual(len({p['id'] for p in result['items']}), 2)
        self.assertEqual([p['name'] for p in result['items']], ['Café 同名'] * 2)
        self.assertEqual(self.view(query={'kind':'connection','query':'%_'})['total'], 1)
        self.assertEqual(self.view(query={'query': "' OR 1=1 --"})['total'], 0)
        for view, raw in [('search','kind=devices'),('search','offset=-1'),('search','offset=1000001'),('search','limit=0'),
            ('search','limit=101'),('search','limit=1&limit=2'),('search','query='+('x'*201)),('search','q=term'),
            ('ports','family=rj45_poe'),('ports','status=occupied'),('connections','kind=all'),('search','query=%00')]:
            self.expect(self.view(view, raw=raw, status=422), 422, 'request_invalid')
        self.assertEqual(self.view(query={'offset':1000000,'limit':100})['items'], [])
        revision = self.snapshot()['revision']
        for view in ['search','ports','connections']:
            self.expect(self.admin.request('GET',f'/api/v1/customers/{self.customer_id}/inventory/{view}'),428,'revision_required')
            self.expect(self.admin.request('GET',f'/api/v1/customers/{self.customer_id}/inventory/{view}',headers={'If-Match':'bad'}),422,'revision_invalid')
            self.assertEqual(self.view(view)['revision'], revision)
        self.assertEqual(self.tables(), before)
        document = self.expect(self.admin.request('GET','/api/v1/openapi.json'),200).json()
        for view in ['search','ports','connections']:
            operation = document['paths'][f'/api/v1/customers/{{id}}/inventory/{view}']['get']
            headers = [p['name'] for p in operation['parameters'] if p['in']=='header']
            self.assertEqual(headers,['If-Match']); self.assertIn('412',operation['responses'])

    def test_pagination_stale_rename_move_paths(self):
        _,_,room,rack,device,_,ports,_,_,_ = self.fixture()
        revision = self.snapshot()['revision']; ids=[]; offset=0
        while True:
            page=self.view('ports',{'limit':3,'offset':offset},revision=revision)
            ids += [i['id'] for i in page['items']]
            if page['nextOffset'] is None: break
            offset=page['nextOffset']
        self.assertEqual(ids,sorted(p['id'] for p in self.snapshot()['ports']))
        self.command('device.update',{'id':device['id'],'name':'Renamed literal'})
        for view in ['search','ports','connections']: self.expect(self.view(view,revision=revision,status=412),412,'revision_conflict')
        current=self.view('ports',{'query':'Renamed literal'})
        self.assertEqual(len(current['items']),4)
        self.assertTrue(all(p['path'][-2]['name']=='Renamed literal' and p['rackId']==rack['id'] and p['roomId']==room['id'] for p in current['items']))
        _,_,other,other_rack=self.hierarchy('Moved')
        self.command('device.move',{'id':device['id'],'rackId':other_rack['id']})
        rows=self.view('ports',{'query':'Renamed literal'})['items']
        self.assertTrue(all(p['rackId']==other_rack['id'] and p['roomId']==other['id'] for p in rows))

    def test_ports_connections_exact_context_no_ghosts(self):
        _,_,room,rack,device,groups,ports,dose,dp,cable=self.fixture()
        _,_,_,second_rack=self.hierarchy('Second')
        second,sg,sp=self.device('Second physical rack',rack=second_rack['id'])
        cross=self.connect(ports[2],sp[0]); local=self.connect(ports[3],ports[1],confirmedReservedPortIds=[ports[1]['id']])
        before=self.tables(); all_ports=self.view('ports')['items']; by_id={p['id']:p for p in all_ports}
        self.assertEqual(len(all_ports),len(self.snapshot()['ports']))
        first=by_id[ports[0]['id']]
        self.assertEqual(first['connectionIds'],[cable['id']]); self.assertEqual(first['peerPortIds'],[dp[0]['id']]); self.assertTrue(first['connected'])
        self.assertEqual(first['groupId'],groups[0]['id']); self.assertEqual(first['roomId'],room['id']); self.assertEqual(first['rackId'],rack['id'])
        self.assertFalse(by_id[dp[1]['id']]['connected']); self.assertIsNone(by_id[dp[1]['id']]['rackId'])
        self.assertEqual(len(self.view('ports',{'status':'reserved','family':'rj45'})['items']),1)
        cables={c['id']:c for c in self.view('connections')['items']}
        self.assertEqual(set(cables),{cable['id'],cross['id'],local['id']})
        self.assertIsNone(cables[cable['id']]['crossRack']); self.assertTrue(cables[cross['id']]['crossRack']); self.assertFalse(cables[local['id']]['crossRack'])
        for c in cables.values():
            self.assertEqual(c['from'],by_id[c['from']['id']]); self.assertEqual(c['to'],by_id[c['to']['id']])
        self.assertEqual(cables[cable['id']]['note'],'Nota ñ literal %_ SQL')
        self.assertEqual(cables[cable['id']]['color'],'#12aBcD'); self.assertEqual(cables[cable['id']]['patch'],'tested')
        encoded=json.dumps([self.view(),all_ports,list(cables.values())]); self.assertNotIn('properties',encoded); self.assertNotIn('password',encoded)
        self.assertEqual(self.tables(),before)

    def test_groups_scope_and_foreign_customer(self):
        self.fixture(); foreign=self.customer('Foreign hidden customer')['id']
        direct,_,_=self.add_user('view-reader',['inventory.read'],self.customer_id)
        editor,_,_=self.add_user('no-reader',['inventory.edit'],self.customer_id)
        grouped,grant,_=self.add_user('group-reader',[],None)
        group=uid()
        self.lab.sql(self.db,f"INSERT INTO customer_group VALUES('{group}','{self.house_id}','Visible customer group'); INSERT INTO customer_group_member VALUES('{self.house_id}','{group}','{self.customer_id}'); INSERT INTO permission_grant VALUES('{uid()}','{self.house_id}','{grant}','inventory.read',NULL,'{group}')")
        for view in ['search','ports','connections']:
            expected=self.view(view)
            self.assertEqual(self.view(view,client=direct),expected); self.assertEqual(self.view(view,client=grouped),expected)
            self.expect(self.view(view,client=direct,customer=foreign,status=404),404,'not_found')
            self.expect(self.view(view,client=editor,status=404),404,'not_found')
            self.expect(self.view(view,customer=uid(),revision=1,status=404),404,'not_found')

    def wait_for(self, sql):
        until=time.monotonic()+4
        while time.monotonic()<until:
            if int(self.lab.sql(self.db,sql,admin=True)): return
            time.sleep(.025)
        self.fail('Real PostgreSQL lock witness absent')

    def wait_read(self, client, view, mutate, status, table='customer', identity=None):
        identity=identity or self.customer_id; revision=self.snapshot()['revision']; label='readviews_'+uid()
        with ThreadPoolExecutor(2) as pool:
            holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT id FROM {table} WHERE id='{identity}' FOR UPDATE; SELECT pg_sleep(3); COMMIT;")
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            if view=='project': pending=pool.submit(client.request,'GET',f'/api/v1/customers/{self.customer_id}/project')
            else: pending=pool.submit(client.request,'GET',f'/api/v1/customers/{self.customer_id}/inventory/{view}',None,{'If-Match':f'"{revision}"'})
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
            mutate(); self.assertFalse(holder.done()); self.expect(pending.result(timeout=15),status,'not_found' if status==404 else 'authentication_required'); holder.result(timeout=10)

    def test_capability_session_revocation_expiry_after_wait(self):
        self.fixture()
        for view in ['search','ports','connections','project']:
            reader,grant,_=self.add_user('revoke-'+view,['inventory.read'],self.customer_id)
            before=self.tables()
            self.wait_read(reader,view,lambda:self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{grant}' AND capability='inventory.read'"),404)
            self.assertEqual(self.tables(),before)
        for mode in ['revoked','expired']:
            reader,_,_=self.add_user('session-'+mode,['inventory.read'],self.customer_id)
            if mode=='expired': self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{reader.actor_id}'")
            self.wait_read(reader,'ports',lambda:self.lab.sql(self.db,f"DELETE FROM app_session WHERE user_id='{reader.actor_id}'") if mode=='revoked' else None,401,
                table='customer' if mode=='revoked' else 'app_user',identity=None if mode=='revoked' else reader.actor_id)

    def test_writer_reader_orders_and_project_regression(self):
        _,_,_,_,device,_,_,_,_,_=self.fixture(); revision=self.snapshot()['revision']
        # Writer first: real API transaction sleeps in audit after data/revision changes; reader sees only its committed version.
        self.lab.sql(self.db,"CREATE FUNCTION slow_readviews() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN PERFORM pg_sleep(2); RETURN NEW; END $$; CREATE TRIGGER slow_readviews BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION slow_readviews()")
        with ThreadPoolExecutor(2) as pool:
            writer=pool.submit(self.command,'device.update',{'id':device['id'],'name':'Committed name'},revision=revision)
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND wait_event='PgSleep'")
            reader=pool.submit(self.view,'ports',revision=revision,status=412)
            self.expect(reader.result(timeout=12),412,'revision_conflict'); self.assertEqual(writer.result(timeout=10).status,200)
        self.lab.sql(self.db,'DROP TRIGGER slow_readviews ON audit_event; DROP FUNCTION slow_readviews()')
        # Reader first: hold actor row, witness reader owning customer SHARE while waiting for actor.
        revision=self.snapshot()['revision']; label='readerfirst_'+uid()
        with ThreadPoolExecutor(3) as pool:
            holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT id FROM app_user WHERE id='{self.admin_id}' FOR UPDATE; SELECT pg_sleep(3); COMMIT;")
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            reader=pool.submit(self.view,'ports',revision=revision)
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND query LIKE '%FOR SHARE OF s,u%' AND cardinality(pg_blocking_pids(pid))>0")
            writer=pool.submit(self.command,'device.update',{'id':device['id'],'name':'After coherent read'},revision=revision)
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND query LIKE '%customer%FOR UPDATE%' AND cardinality(pg_blocking_pids(pid))>0")
            page=reader.result(timeout=15); holder.result(timeout=10); self.assertEqual(writer.result(timeout=10).status,200)
        self.assertTrue(any(p['deviceName']=='Committed name' for p in page['items']))
        current=self.snapshot(); self.assertEqual(current['revision'],revision+1)
        self.assertTrue(any(d['name']=='After coherent read' for d in current['devices']))
        self.server.close(); self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend); self.admin.server=self.server
        self.assertEqual(self.snapshot(),current)

    def test_final_recheck_after_snapshot_wait(self):
        self.fixture()
        # Hold inventory relation after the first session/read check. Final checks must run after snapshot/projection.
        for mode in ['expired','capability']:
            reader,grant,_=self.add_user('final-'+mode,['inventory.read'],self.customer_id)
            revision=self.snapshot()['revision']; label='snapshotwait_'+uid(); before=self.tables()
            if mode=='expired': self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{reader.actor_id}'")
            with ThreadPoolExecutor(2) as pool:
                holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; LOCK TABLE inventory_port IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(3); COMMIT;",admin=True)
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
                pending=pool.submit(reader.request,'GET',f'/api/v1/customers/{self.customer_id}/inventory/connections',None,{'If-Match':f'"{revision}"'})
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND query LIKE '%jsonb_build_object%' AND cardinality(pg_blocking_pids(pid))>0")
                if mode=='capability': self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{grant}'")
                self.expect(pending.result(timeout=15),401 if mode=='expired' else 404,'authentication_required' if mode=='expired' else 'not_found'); holder.result(timeout=10)
            self.assertEqual(self.tables(),before)


def distribution(path):
    return {p.relative_to(path).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob('*')) if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['dll','frontend','evidence']: parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',action='append',required=True); args=parser.parse_args()
    available=[n for n in InventoryReadViewsPostgres.__dict__ if n.startswith('test_')]
    if set(args.case)-set(available): raise ValueError('Unknown read view case')
    names=[n for n in available if n in args.case]
    args.dll=args.dll.resolve(); args.frontend=args.frontend.resolve(); args.evidence.mkdir(parents=True,exist_ok=False)
    files=[p for p in (WORKSPACE/'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files+=list((WORKSPACE/'development/server/database').glob('*.sql'))
    files+=[Path(__file__).resolve()]+[WORKSPACE/'development/server/tests'/n for n in ['pg_support.py','test_inventory_changes.py','test_inventory_postgres.py']]
    def sources(): return {p.relative_to(WORKSPACE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original=sources(); server=distribution(args.dll.parent); frontend=distribution(args.frontend)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),
        'serverPath':str(args.dll.parent),'frontendPath':str(args.frontend),'serverHashes':server,'frontendHashes':frontend,
        'sourceHashes':original,'selectedCases':names,'schemaVersion':7,'actualQaOpened':False}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lab=Lab('inventory-read-views'); InventoryReadViewsPostgres.lab=lab
    report['versions']={name:subprocess.run([str(path),'--version'],capture_output=True,text=True,check=True,creationflags=NO_WINDOW).stdout.strip()
        for name,path in [('dotnet',lab.dotnet),('postgres',lab.pg_bin/'postgres.exe')]}
    InventoryReadViewsPostgres.dll,InventoryReadViewsPostgres.frontend=args.dll,args.frontend
    started=time.monotonic()
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(InventoryReadViewsPostgres(n) for n in names))
        report.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started,3),labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers),sourcesUnchanged=original==sources(),
        serverUnchanged=server==distribution(args.dll.parent),frontendUnchanged=frontend==distribution(args.frontend))
    (args.evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(report[k] for k in ['successful','labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged']) else 1


if __name__=='__main__': sys.exit(main())
