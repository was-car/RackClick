"""Four bounded personal-palette focuses; frozen artifacts and new native PG labs only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from itertools import combinations_with_replacement
import uuid
import platform
import subprocess
import sys
import time
import unittest

from pg_support import Client, Lab, WORKSPACE, NO_WINDOW, literal
from test_postgres import EvidenceResult, Tee
from test_shared_device_templates import SharedDeviceTemplatesPostgres, uid, distribution

MAX_REVISION = 9007199254740991
TABLES = {'user_category_colors', 'user_category_color_operation'}
CATEGORIES = ['Patch Panel','Switch','Router','Firewall','Server','NAS/SAN','Other']
TYPES = sorted('↔'.join(sorted(pair)) for pair in combinations_with_replacement(CATEGORIES,2))
SWATCHES = ['#ffffff','#d1d5db','#fbbf24','#3b82f6','#10b981','#ef4444','#a855f7','#f97316','#06b6d4','#000000']


class UserCategoryColors1089(SharedDeviceTemplatesPostgres):
    baseline = None

    def setUp(self):
        target = self.dll
        if self._testMethodName.startswith('test_04_'): self.dll = self.baseline
        try: super().setUp()
        finally: self.dll = target

    def color_path(self, key=None, cancel=False):
        return '/api/v1/me/category-colors' + (f'/operations/{key}' if key else '') + ('/cancel' if cancel else '')

    def palette(self, client=None):
        client = client or self.admin
        response = self.expect(client.request('GET', self.color_path()), 200)
        value = response.json()
        self.assertEqual(set(value), {'kind','ownerId','revision','colors'})
        self.assertEqual(value['kind'], 'userCategoryColors'); self.assertEqual(value['ownerId'], client.actor_id)
        self.assertEqual(response.headers.get('etag'), f'"category-colors-{value["revision"]}"')
        return value

    def color_headers(self, client=None, revision=0, key=None):
        return {'If-Match':f'"category-colors-{revision}"', 'Idempotency-Key':key or uid(),
                'X-RackClick-Actor':(client or self.admin).actor_id}

    def colors(self, colors=None, revision=None, key=None, client=None, status=200, headers=None):
        client = client or self.admin
        if revision is None: revision = self.palette(client)['revision']
        response = self.expect(client.request('POST', self.color_path(), {'colors':colors if colors is not None else {'Patch Panel↔Switch':'#3b82f6'}},
            {**self.color_headers(client, revision, key), **(headers or {})}), status)
        if status == 200:
            value = response.json()
            self.assertEqual(set(value), {'kind','ownerId','revision','requestId','operationId','result'})
            self.assertEqual(set(value['result']), {'colors','changed'}); self.assertIsInstance(value['result']['changed'], bool)
            self.assertEqual(value['kind'],'userCategoryColors'); self.assertEqual(value['ownerId'],client.actor_id)
            self.assertEqual(response.headers.get('etag'), f'"category-colors-{value["revision"]}"')
        return response

    def color_status(self, key, client=None, status=200):
        client = client or self.admin
        response = self.expect(client.request('GET', self.color_path(key)), status)
        if status == 200:
            value=response.json(); self.assertEqual(set(value),{'state','ownerId','revision','requestId','operation'})
            self.assertEqual(value['ownerId'],client.actor_id); self.assertEqual(value['requestId'],key)
            self.assertEqual(response.headers.get('etag'),f'"category-colors-{value["revision"]}"')
        return response

    def cancel_colors(self, key, colors=None, revision=0, client=None, status=200, headers=None):
        client=client or self.admin
        return self.expect(client.request('POST', self.color_path(key,True),
            {'colors':colors if colors is not None else {'Patch Panel↔Switch':'#3b82f6'}},
            {**self.color_headers(client,revision,key), **(headers or {})}), status)

    def rows(self, database=None, tables=None):
        database=database or self.db
        if tables is None: tables=self.lab.sql(database,"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
        return {name:self.lab.sql(database,f'SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),\'[]\') FROM "{name}" t') for name in tables}

    def once(self,key,action='user.categoryColors.set'):
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_category_color_operation WHERE request_id='{key}'"),'1')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{key}' AND action='{action}'"),'1')

    def connection_creation_checks(self):
        """One compound focus: identities/classification, coherent batch and atomic materialization."""
        _,_,room,rack=self.hierarchy(' category1089')
        _,_,_,other_rack=self.hierarchy(' cross-rack1089')
        groups=[{'type':'rj45','count':24},{'type':'sfp','count':24}]
        devices={}; pools={}
        presets={'Patch Panel':'pp24','Switch':'sw24','Router':'rtr','Firewall':'fw','Server':'srv2u','NAS/SAN':'san','Other':'unknown-template'}
        full={key:SWATCHES[index%len(SWATCHES)] for index,key in enumerate(TYPES)}
        for index,category in enumerate(CATEGORIES):
            device,_,ports=self.device('Mismo nombre Café 同名',rack=(rack if index%2 else other_rack)['id'],groups=groups)
            self.command('device.update',{'id':device['id'],'properties':{
                'catalog':{'presetKey':presets[category]},'preset':'Etiqueta traducida','visualFamily':'switches'}})
            devices[category]=device
            # Repeated gn across two group IDs cannot identify an endpoint; take UUIDs explicitly.
            pools[category]=sorted(ports,key=lambda p:(p['gn'],p['groupId']))
        def take(category):return pools[category].pop(0)['id']
        def pair(a,b,**extra):return {'fromPortId':take(a),'toPortId':take(b),**extra}
        personal_receipt=self.colors(full).json()
        entries=[];expected=[]
        for a,b in combinations_with_replacement(CATEGORIES,2):
            entries.extend([pair(a,b),pair(b,a,color=None)])
            expected.extend([full['↔'.join(sorted([a,b]))]]*2)
        revision=self.snapshot()['revision'];key=uid();payload={'pairs':entries}
        receipt=self.command('connections.createBatch',payload,revision=revision,key=key).json()
        rows={r['id']:r for r in self.snapshot()['connections']}
        created=receipt['result']['createdIds']
        self.assertEqual([rows[x]['color'] for x in created],expected)
        self.assertEqual(len(created),56)
        event=json.loads(self.lab.sql(self.db,f"SELECT after_json FROM audit_event WHERE id='{receipt['operationId']}'"))
        self.assertEqual([r['color'] for r in event['data']],expected)
        self.assertEqual([e['id'] for e in self.poll(revision)['events']],[receipt['operationId']])
        saved={x:rows[x] for x in created};self.colors({})
        self.assertEqual(self.command('connections.createBatch',payload,revision=revision,key=key).json(),receipt)
        self.assertEqual({r['id']:r for r in self.snapshot()['connections'] if r['id'] in saved},saved)
        # Explicit valid RGB is not limited to swatches; unknown category input is ignored.
        explicit=pair('Switch','Patch Panel',color='#12aBcD',category='Server↔Server',note='explicit')
        ident=self.command('connections.create',explicit).json()['result']['resourceId']
        self.assertEqual(next(r for r in self.snapshot()['connections'] if r['id']==ident)['color'],'#12aBcD')
        automatic=pair('Switch','Patch Panel',color=None)
        self.colors({'Patch Panel↔Switch':'#3b82f6','Other↔Other':'#ef4444'})
        ident2=self.command('connections.create',automatic).json()['result']['resourceId']
        self.assertEqual(next(r for r in self.snapshot()['connections'] if r['id']==ident2)['color'],'#3b82f6')
        self.colors({'Patch Panel↔Switch':'#10b981'})
        self.command('connections.update',{'connectionId':ident2,'note':'No recolor'})
        self.command('connections.reconnect',{'connectionId':ident2,'keepPortId':automatic['fromPortId'],'newPortId':take('Switch')})
        self.assertEqual(next(r for r in self.snapshot()['connections'] if r['id']==ident2)['color'],'#3b82f6')
        self.command('connections.update',{'connectionId':ident2,'color':None})
        self.assertIsNone(next(r for r in self.snapshot()['connections'] if r['id']==ident2)['color'])
        # Missing override materializes null, despite visual labels and family looking like a switch.
        ident3=self.command('connections.create',pair('Other','Other')).json()['result']['resourceId']
        self.assertIsNone(next(r for r in self.snapshot()['connections'] if r['id']==ident3)['color'])
        # Exact catalog-key classification wins over legacy; only absence/nontext allows exact legacy keys.
        cases=[({'catalog':{'presetKey':'unknown'},'preset':'sw24'},'Other'),
               ({'catalog':{'presetKey':''},'preset':'sw24'},'Other'),
               ({'catalog':{'presetKey':None},'preset':'sw24'},'Switch'),
               ({'preset':'sw48'},'Switch'),({'preset':'Switch 24 ports','visualFamily':'switches'},'Other'),
               ({'catalog':{'presetKey':'SW24'},'preset':'sw24'},'Other'),
               ({'catalog':{'presetKey':'swsfp'},'preset':'Servidor traducido'},'Switch'),
               ({'catalog':{'presetKey':'ppf24'},'preset':'Switch traducido'},'Patch Panel'),
               ({'catalog':{'presetKey':'pp48'}},'Patch Panel'),
               ({'catalog':{'presetKey':'nas4u'}},'NAS/SAN'),
               ({'catalog':{'presetKey':'nas2u'}},'NAS/SAN'),
               ({'catalog':{'presetKey':'srv4u'}},'Server'),
               ({'catalog':{'presetKey':'srv1u'}},'Server'),
               ({'visualFamily':'switches'},'Other')]
        full={key:SWATCHES[index%len(SWATCHES)] for index,key in enumerate(TYPES)};self.colors(full)
        # Only this new isolated fixture uses direct SQL to express an absent catalog property;
        # the public merge-patch API deliberately does not remove unspecified properties.
        for properties,category in cases:
            device,_,ports=self.device('Homónimo clasificación',rack=rack['id'],groups=[{'type':'rj45','count':2}])
            self.lab.sql(self.db,f"UPDATE inventory_device SET properties={literal(json.dumps(properties))}::jsonb WHERE id='{device['id']}'")
            cid=self.command('connections.create',{'fromPortId':ports[0]['id'],'toPortId':ports[1]['id']}).json()['result']['resourceId']
            self.assertEqual(next(r for r in self.snapshot()['connections'] if r['id']==cid)['color'],full[category+'↔'+category])
        for kind in ['dose','endDevice']:
            device,_,ports=self.device('Manual '+kind,room=room['id'],kind=kind,groups=[{'type':'rj45','count':2}])
            self.command('device.update',{'id':device['id'],'properties':{'visualFamily':'switches'}})
            cid=self.command('connections.create',{'fromPortId':ports[0]['id'],'toPortId':ports[1]['id']}).json()['result']['resourceId']
            self.assertEqual(next(r for r in self.snapshot()['connections'] if r['id']==cid)['color'],full['Other↔Other'])
        # Server authorization remains authoritative: preference access never grants inventory writes.
        reader,_,_=self.add_user('category-reader-scope',['inventory.read'],self.customer_id)
        self.colors(full,client=reader)
        self.command('connections.create',pair('Router','Firewall'),client=reader,status=403)
        hidden=self.customer('Hidden category customer')['id'];_,_,_,hidden_rack=self.hierarchy(' hidden',hidden)
        _,_,foreign=self.device('Same visible label',rack=hidden_rack['id'],customer=hidden)
        self.command('connections.create',{'fromPortId':take('Router'),'toPortId':foreign[0]['id']},status=404)
        # Every validation/error leaves settings, customer revision, receipts and audit unchanged.
        def unchanged(body,status):
            before=self.durable();self.command('connections.createBatch',body,status=status);self.assertEqual(before,self.durable())
        unchanged({'pairs':[pair('Router','Firewall'),pair('Router','Firewall',color='#nothex')]},422)
        bad=pair('Router','Firewall');unchanged({'pairs':[bad,bad]},422)
        unchanged({'pairs':[pair('Router','Firewall'),{'fromPortId':take('Router'),'toPortId':foreign[1]['id']}]},404)
        unchanged({'pairs':[{'fromPortId':uid(),'toPortId':uid()}]*129},422)
        blocked=take('Router');self.lab.sql(self.db,f"UPDATE inventory_port SET status='disabled' WHERE id='{blocked}'")
        unchanged({'pairs':[{'fromPortId':blocked,'toPortId':take('Firewall')}]},409)
        reserved=take('Router');self.lab.sql(self.db,f"UPDATE inventory_port SET status='reserved' WHERE id='{reserved}'")
        destination=take('Firewall');unchanged({'pairs':[{'fromPortId':reserved,'toPortId':destination}]},409)
        self.command('connections.create',{'fromPortId':reserved,'toPortId':destination,'confirmedReservedPortIds':[reserved]})
        # A failure at the second physical insert rolls back the first insert and all journals/audit.
        self.lab.sql(self.db,"CREATE FUNCTION category1089_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.note='fail1089' THEN RAISE EXCEPTION 'isolated batch rollback' USING ERRCODE='23514'; END IF; RETURN NEW; END $$; CREATE TRIGGER category1089_failure BEFORE INSERT ON inventory_connection FOR EACH ROW EXECUTE FUNCTION category1089_fail();")
        try:unchanged({'pairs':[pair('Server','NAS/SAN'),pair('Server','NAS/SAN',note='fail1089')]},409)
        finally:self.lab.sql(self.db,'DROP TRIGGER category1089_failure ON inventory_connection; DROP FUNCTION category1089_fail();')
        # Wait after the palette was read, commit a newer preference, then release the insert.
        coherent=[pair('Server','NAS/SAN',note='coherent1089') for _ in range(2)]
        self.colors({'NAS/SAN↔Server':'#f97316'});label='categories1089_coherent_'+uid();lock=10891089
        self.lab.sql(self.db,f"CREATE FUNCTION category1089_wait() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.note='coherent1089' THEN PERFORM pg_advisory_xact_lock({lock}); END IF; RETURN NEW; END $$; CREATE TRIGGER category1089_wait BEFORE INSERT ON inventory_connection FOR EACH ROW EXECUTE FUNCTION category1089_wait();")
        revision=self.snapshot()['revision']
        try:
            with ThreadPoolExecutor(2) as pool:
                holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT pg_advisory_xact_lock({lock}); SELECT pg_sleep(3); COMMIT;")
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
                pending=pool.submit(self.command,'connections.createBatch',{'pairs':coherent},revision=revision)
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
                self.colors({'NAS/SAN↔Server':'#06b6d4'})
                made=pending.result(timeout=15).json()['result']['createdIds'];holder.result(timeout=10)
            self.assertEqual([r['color'] for r in self.snapshot()['connections'] if r['id'] in made],['#f97316']*2)
        finally:self.lab.sql(self.db,'DROP TRIGGER category1089_wait ON inventory_connection; DROP FUNCTION category1089_wait();')
        # Another installation has its own Systemhaus, account UUID and empty personal aggregate.
        separate=self.lab.create_database('category1089-other-systemhaus')
        self.assertEqual(self.lab.bootstrap(separate,'qa-inventory-admin',self.password,dll=self.dll).returncode,0)
        self.lab.grant_runtime(separate);other_server=self.lab.start_server(separate,dll=self.dll,frontend=self.frontend)
        try:
            other=Client(other_server);other.actor_id=self.lab.sql(separate,'SELECT id FROM app_user')
            self.assertNotEqual(self.lab.sql(separate,'SELECT id FROM systemhaus'),self.house_id)
            self.expect(other.login('qa-inventory-admin',self.password),200)
            current=self.palette();self.assertEqual(self.palette(other)['colors'],{})
            self.colors({'NAS/SAN↔Server':'#000000'},client=other)
            self.assertEqual(self.palette(),current)
            self.assertEqual(self.color_status(personal_receipt['requestId'],other).json()['state'],'notRecorded')
        finally:other_server.close()
        self.__class__.connection_observation={'all28PairsBothOrientations':True,'selfPairs':True,'uuidGroupsRepeatedGn':True,
            'crossRack':True,'explicitColorPrecedence':True,'translatedLabelNotIdentity':True,'legacyExactFallback':True,
            'unknownCatalogBlocksLegacyFallback':True,'manualDosenEndDevicesOther':True,'oneCommittedPalettePerBatch':True,
            'replayNoRecolor':True,'updateReconnectNoRecolor':True,'atomicRollbackSecondInsert':True,'readerCannotEditInventory':True,
            'systemhausInstallationIsolation':True}

    def test_01_actor_isolation_full_map_reset_noop_replay_restart(self):
        self.assertEqual(self.lab.sql(self.db,'SELECT max(version) FROM schema_migration'),'13')
        self.assertEqual(len(self.rows()),39)
        self.fixture(); inventory=self.snapshot()
        reader,_,_=self.add_user('colors-reader',['inventory.read'],self.customer_id)
        empty,_,_=self.add_user('colors-no-customers')
        self.assertEqual(self.expect(empty.request('GET','/api/v1/customers'),200).json(),[])
        core=self.rows(); core={k:v for k,v in core.items() if k not in TABLES|{'audit_event','app_session'}}
        before=self.durable(); self.assertEqual(self.palette()['colors'],{}); self.assertEqual(self.palette(empty)['revision'],0)
        self.assertEqual(before,self.durable()); self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM user_category_colors'),'0')
        noop0=self.colors({},client=empty).json(); self.assertFalse(noop0['result']['changed']);self.assertEqual(noop0['revision'],0)
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_category_colors WHERE owner_id='{empty.actor_id}'"),'0')
        key=uid(); original={'Patch Panel↔Patch Panel':'#fbbf24','Patch Panel↔Switch':'#3b82f6','Other↔Other':'#ffffff'}
        first=self.colors(original,key=key).json(); self.assertEqual(first['revision'],1)
        reversed_map=dict(reversed(list(original.items())))
        self.assertEqual(self.colors(reversed_map,revision=0,key=key).json(),first)
        noop=self.colors(reversed_map).json(); self.assertFalse(noop['result']['changed']); self.assertEqual(noop['revision'],1)
        self.colors({'Patch Panel↔Switch':'#3b82f6'}); self.assertEqual(self.palette()['colors'],{'Patch Panel↔Switch':'#3b82f6'})
        reset=self.colors({}).json(); self.assertEqual(reset['revision'],3); self.assertTrue(reset['result']['changed'])
        self.assertEqual(self.palette()['colors'],{})
        reader_receipt=self.colors({'Patch Panel↔Patch Panel':'#10b981'},client=reader).json()
        self.assertEqual(self.palette(reader)['colors'],{'Patch Panel↔Patch Panel':'#10b981'})
        self.assertEqual(self.color_status(key,reader).json()['state'],'notRecorded')
        self.assertIsNone(self.color_status(uid()).json()['operation'])
        historical=self.color_status(key).json(); self.assertEqual(historical['revision'],3);self.assertEqual(historical['operation'],first)
        self.assertEqual(self.cancel_colors(key,original,revision=0).json(),historical)
        self.colors(original,revision=1,key=key,status=409)
        self.colors({'Patch Panel↔Switch':'#ef4444'},revision=0,key=key,status=409)
        fence=uid(); cancelled=self.cancel_colors(fence,original,revision=0).json()
        self.assertEqual(cancelled['state'],'cancelled');self.assertIsNone(cancelled['operation']);self.assertEqual(cancelled['revision'],3)
        self.assertEqual(self.cancel_colors(fence,reversed_map,revision=0).json(),cancelled)
        self.colors(original,revision=0,key=fence,status=409)
        self.colors(original,revision=3,key=fence,status=409)
        for receipt in [first,noop,reset,noop0,reader_receipt]:self.once(receipt['requestId'])
        self.once(fence,'user.categoryColors.cancel')
        self.assertEqual(self.rows(tables=core),core); self.assertEqual(self.snapshot(),inventory)
        self.assertEqual(self.poll(inventory['revision'])['events'],[])
        event=json.loads(self.lab.sql(self.db,f"SELECT row_to_json(t) FROM audit_event t WHERE id='{first['operationId']}'"))
        self.assertEqual(event['resource_id'],self.admin_id);self.assertEqual(event['action'],'user.categoryColors.set')
        self.assertEqual(event['before_json'],{'ownerId':self.admin_id,'revision':0,'colors':{}})
        self.assertEqual(event['after_json'],{'ownerId':self.admin_id,'revision':1,'colors':original,'changed':True})
        self.assertIsNone(event.get('customer_id'))
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_context WHERE event_id='{first['operationId']}'"),'0')
        self.server.close(); self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend)
        fresh=Client(self.server);fresh.actor_id=self.admin_id; self.expect(fresh.login('qa-inventory-admin',self.password),200)
        fresh_reader=Client(self.server);fresh_reader.actor_id=reader.actor_id;self.expect(fresh_reader.login('colors-reader',self.password),200)
        self.assertEqual(self.palette(fresh)['colors'],{});self.assertEqual(self.palette(fresh)['revision'],3)
        self.assertEqual(self.palette(fresh_reader)['colors'],{'Patch Panel↔Patch Panel':'#10b981'})
        self.assertEqual(self.color_status(key,fresh).json()['operation'],first)
        self.assertEqual(self.color_status(fence,fresh).json()['state'],'cancelled')
        self.assertEqual(self.colors(reversed_map,revision=0,key=key,client=fresh).json(),first)
        self.colors(original,revision=0,key=fence,client=fresh,status=409)
        self.expect(Client(self.server).request('GET',self.color_path()),401)
        self.admin=fresh;self.connection_creation_checks()

    def test_02_closed_validation_csrf_conflicts_atomicity_and_receipt_integrity(self):
        before=self.durable(); good={'colors':{'Patch Panel↔Switch':'#3b82f6'}}; headers=self.color_headers()
        invalid=[{},[],None,{'colors':None},{'colors':[]},{**good,'ownerId':uid()},{**good,'customerId':self.customer_id},
            {**good,'revision':0},{'colors':{'unknown':'#3b82f6'}},{'colors':{'RJ45':'#3b82f6'}}]
        invalid += [{'colors':{'Patch Panel↔Switch':v}} for v in [None,True,1,{},[], '#123abc','#123ABC','123abc','#abc','#3b82f6d',' #3b82f6','#3b82f6 ','#3b82f6\n','#123abg']]
        for body in invalid:
            self.expect(self.admin.request('POST',self.color_path(),'null' if body is None else body,{**headers,'Content-Type':'application/json'}),422)
        for raw in ['{"colors":{},"colors":{}}','{"colors":{"Patch Panel↔Switch":"#3b82f6","Patch Panel↔Switch":"#3b82f6"}}']:
            self.expect(self.admin.request('POST',self.color_path(),raw.encode('utf-8'),{**headers,'Content-Type':'application/json'}),422)
        for tag in ['"0"','"preferences-0"','"category-colors-00"','"category-colors--1"','category-colors-0',f'"category-colors-{MAX_REVISION+1}"','W/"category-colors-0"','"category-colors-0", "category-colors-1"']:
            self.colors(revision=0,status=422,headers={'If-Match':tag})
        self.expect(self.admin.request('POST',self.color_path(),good,{'Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),428)
        self.expect(self.admin.request('POST',self.color_path(),good,{'If-Match':'"category-colors-0"','Idempotency-Key':uid()}),422)
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
        for name in ['UserCategoryColorsMap','UserCategoryColorsSet','UserCategoryColorChange','UserCategoryColorsSnapshot','UserCategoryColorResult','UserCategoryColorStatus']:
            self.assertFalse(api['components']['schemas'][name]['additionalProperties'])
        self.assertEqual(set(api['components']['schemas']['UserCategoryColorsMap']['properties']),set(TYPES))
        for path,methods in [(self.color_path(),['get','post']),('/api/v1/me/category-colors/operations/{requestId}',['get']),('/api/v1/me/category-colors/operations/{requestId}/cancel',['post'])]:
            for method in methods:
                operation=api['paths'][path][method];self.assertNotIn('404',operation['responses'])
                if method=='post':self.assertTrue(next(p for p in operation['parameters'] if p['name']=='X-RackClick-Actor')['required'])
        self.lab.sql(self.db,"CREATE FUNCTION categories1089_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'isolated rollback witness' USING ERRCODE='23514'; END $$; CREATE TRIGGER categories1089_failure BEFORE INSERT ON user_category_color_operation FOR EACH ROW EXECUTE FUNCTION categories1089_fail();")
        before=self.durable()
        try:
            self.colors(revision=0,status=409);self.assertEqual(before,self.durable())
            self.cancel_colors(uid(),status=409);self.assertEqual(before,self.durable())
        finally:self.lab.sql(self.db,'DROP TRIGGER categories1089_failure ON user_category_color_operation; DROP FUNCTION categories1089_fail();')
        full={key:SWATCHES[index%len(SWATCHES)] for index,key in enumerate(TYPES)}
        receipt=self.colors(full).json();self.assertEqual(self.palette()['colors'],full)
        before=self.durable();self.colors(full,revision=0,status=412);self.assertEqual(before,self.durable())
        for sql in ["UPDATE user_category_colors SET colors='null'", "UPDATE user_category_colors SET colors='[]'", "UPDATE user_category_colors SET colors='{\"Patch Panel↔Switch\":\"#AAAAAA\"}'", "UPDATE user_category_colors SET colors='{\"unknown\":\"#3b82f6\"}'",f'UPDATE user_category_colors SET revision={MAX_REVISION+1}',"UPDATE user_category_color_operation SET result_version=2","UPDATE user_category_color_operation SET result_sha256='"+'A'*64+"'"]:
            with self.assertRaises(RuntimeError):self.lab.sql(self.db,sql)
            self.assertEqual(before,self.durable())
        key=receipt['requestId']; original=self.lab.sql(self.db,f"SELECT result_json FROM user_category_color_operation WHERE request_id='{key}'")
        damaged=original.replace('"colors":{','"colors":{"Patch Panel↔Switch":"#3b82f6",',1)
        def store(raw):
            self.lab.sql(self.db,f"UPDATE user_category_color_operation SET result_json={literal(raw)},result_sha256=upper(encode(sha256(convert_to({literal(raw)},'UTF8')),'hex')) WHERE request_id='{key}'")
        store(damaged);corrupt=self.durable()
        try:
            self.color_status(key,status=409);self.colors(full,revision=0,key=key,status=409)
            self.cancel_colors(key,full,revision=0,status=409);self.assertEqual(corrupt,self.durable())
        finally:store(original)
        self.assertEqual(before,self.durable())

    def test_03_concurrency_max_revision_and_revocation_after_real_waits(self):
        key=uid();body={'Patch Panel↔Switch':'#3b82f6'}
        with ThreadPoolExecutor(2) as pool:
            replies=list(pool.map(lambda _:self.colors(body,revision=0,key=key).json(),range(2)))
        self.assertEqual(replies[0],replies[1]);first=replies[0];self.once(key)
        with ThreadPoolExecutor(2) as pool:
            replies=list(pool.map(lambda color:self.admin.request('POST',self.color_path(),{'colors':{'Patch Panel↔Switch':color}},self.color_headers(revision=1)),['#000000','#ffffff']))
        self.assertEqual(sorted(r.status for r in replies),[200,412]);self.assertEqual(self.palette()['revision'],2)
        race=uid()
        with ThreadPoolExecutor(2) as pool:
            setting=pool.submit(self.admin.request,'POST',self.color_path(),{'colors':body},self.color_headers(revision=2,key=race))
            cancelling=pool.submit(self.cancel_colors,race,body,2)
            set_reply,cancel_reply=setting.result(timeout=15),cancelling.result(timeout=15)
        self.assertEqual(cancel_reply.status,200)
        if cancel_reply.json()['state']=='cancelled':self.expect(set_reply,409,'operation_cancelled')
        else:self.expect(set_reply,200);self.assertEqual(cancel_reply.json()['operation'],set_reply.json())
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_category_color_operation WHERE request_id='{race}'"),'1')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{race}'"),'1')
        self.lab.sql(self.db,f"UPDATE user_category_colors SET revision={MAX_REVISION} WHERE owner_id='{self.admin_id}'")
        current=self.palette()['colors'];different={'Patch Panel↔Switch':'#f97316'}
        before=self.durable();self.colors(different,revision=MAX_REVISION,status=409);self.assertEqual(before,self.durable())
        noop=self.colors(current,revision=MAX_REVISION).json();self.assertFalse(noop['result']['changed']);self.assertEqual(noop['revision'],MAX_REVISION)
        self.assertEqual(self.colors(body,revision=0,key=key).json(),first)
        scenarios=[('get','session'),('set','session'),('status','session'),('cancel','request'),('set','active'),('get','expiry'),('replay','session')]
        for index,(route,change) in enumerate(scenarios):
            user,_,_=self.add_user('colors-wait-'+str(index));request=uid()
            if route=='replay':request=self.colors(client=user).json()['requestId']
            label='categories1089_'+uid();family='user-category-color-operation' if change=='request' else 'user-category-colors'
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
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_category_color_operation WHERE owner_id='{user.actor_id}'"),'1' if route=='replay' else '0')
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE actor_id='{user.actor_id}' AND action LIKE 'user.categoryColors.%'"),'1' if route=='replay' else '0')
        user,_,_=self.add_user('colors-session-row');label='categories1089_session_'+uid()
        with ThreadPoolExecutor(2) as pool:
            holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT 1 FROM app_session WHERE user_id='{user.actor_id}' FOR UPDATE; SELECT pg_sleep(3); DELETE FROM app_session WHERE user_id='{user.actor_id}'; COMMIT;")
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            pending=pool.submit(user.request,'GET',self.color_path())
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
            self.expect(pending.result(timeout=15),401);holder.result(timeout=10)

    def test_05_inventory_expiry_after_apply_wait_rolls_back(self):
        """Natural expiry after a real wait inside Apply must roll back all inventory writes."""
        _,_,_,rack=self.hierarchy(' expiry1089')
        _,_,first=self.device('Expiry source',rack=rack['id'],groups=[{'type':'rj45','count':4}])
        _,_,second=self.device('Expiry destination',rack=rack['id'],groups=[{'type':'rj45','count':4}])
        observations=[];lock=10891090
        self.lab.sql(self.db,f"CREATE FUNCTION category1089_expiry_wait() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.note='expiry1089' THEN PERFORM pg_advisory_xact_lock({lock}); END IF; RETURN NEW; END $$; CREATE TRIGGER category1089_expiry_wait BEFORE INSERT ON inventory_connection FOR EACH ROW EXECUTE FUNCTION category1089_expiry_wait();")
        try:
            for index,kind in enumerate(['connections.create','connections.createBatch']):
                actor,_,_=self.add_user('category-expiry-'+str(index),['inventory.read','inventory.edit'],self.customer_id)
                self.colors({'Other↔Other':'#fbbf24'},client=actor)
                item={'fromPortId':first[index]['id'],'toPortId':second[index]['id'],'note':'expiry1089'}
                body=item if kind=='connections.create' else {'pairs':[item,{
                    'fromPortId':first[2]['id'],'toPortId':second[2]['id'],'note':'expiry1089'}]}
                revision=self.snapshot()['revision'];key=uid();label='category1089_expiry_'+uid()
                with ThreadPoolExecutor(2) as pool:
                    holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT pg_advisory_xact_lock({lock}); SELECT pg_sleep(3); COMMIT;")
                    self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
                    self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{actor.actor_id}'")
                    before=self.durable()
                    pending=pool.submit(self.command,kind,body,revision=revision,key=key,client=actor,status=401)
                    self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
                    response=pending.result(timeout=15);holder.result(timeout=10)
                self.expect(response,401,'authentication_required')
                self.assertEqual(self.durable(),before)
                self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM operation WHERE request_id='{key}'"),'0')
                self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{key}'"),'0')
                self.assertEqual(self.snapshot()['revision'],revision)
                observations.append({'command':kind,'actualApplyWait':True,'expiredAfterAuthorization':True,
                    'status':401,'all39TablesUnchanged':True,'operationRows':0,'auditRows':0})
        finally:self.lab.sql(self.db,'DROP TRIGGER category1089_expiry_wait ON inventory_connection; DROP FUNCTION category1089_expiry_wait();')
        self.__class__.expiry_observation=observations

    def test_04_populated_schema12_migration_twice_native39_table_backup_restore(self):
        self.assertEqual(self.lab.sql(self.db,'SELECT max(version) FROM schema_migration'),'12')
        self.fixture();private=self.config();self.sh(self.publish_intent(private))
        self.expect(self.admin.request('POST','/api/v1/me/preferences',{'key':'language','value':'es'},
            {'If-Match':'"preferences-0"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),200)
        self.expect(self.admin.request('POST','/api/v1/me/port-colors',{'colors':{'rj45':'#123abc'}},
            {'If-Match':'"port-colors-0"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),200)
        self.server.close();original=self.rows();self.assertEqual(len(original),37)
        self.assertGreater(sum(bool(json.loads(v)) for v in original.values()),20)
        history=original['schema_migration'];preserved={k:v for k,v in original.items() if k!='schema_migration'}
        env=self.lab.environment();env['ConnectionStrings__RackClick']=self.db.connection(self.lab.port,runtime=False)
        for _ in range(2):
            result=subprocess.run([str(self.lab.dotnet),str(self.dll),'--migrate'],env=env,capture_output=True,text=True,
                encoding='utf-8',timeout=45,creationflags=NO_WINDOW)
            self.assertEqual(result.returncode,0,'Explicit migration failed; raw credentials stay private')
            self.assertEqual(self.rows(tables=preserved),preserved)
            self.assertEqual(self.lab.sql(self.db,"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM (SELECT * FROM schema_migration WHERE version<=12) t"),history)
        self.assertEqual(set(self.rows()),set(original)|TABLES)
        self.lab.grant_runtime(self.db);self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend);self.admin.server=self.server
        self.assertEqual(self.expect(self.server.request('GET','/health/ready'),200).json()['schemaVersion'],13)
        reader,_,_=self.add_user('colors-backup-reader',['inventory.read'],self.customer_id)
        receipt=self.colors({'Patch Panel↔Switch':'#3b82f6','Patch Panel↔Patch Panel':'#a855f7'}).json()
        self.colors({'Other↔Other':'#000000'},client=reader);fence=uid();self.cancel_colors(fence,{},revision=0)
        self.server.close();before=self.rows();self.assertEqual(len(before),39)
        dump=self.db.directory/'categories1089.dump';env=self.lab.environment();env['PGPASSFILE']=str(self.db.directory/'owner.pgpass')
        common=['-h','127.0.0.1','-p',str(self.lab.port),'-w']
        result=subprocess.run([str(self.lab.pg_bin/'pg_dump.exe'),*common,'-U',self.db.owner,'-d',self.db.name,'--format=custom','--no-owner','--no-privileges','--file',str(dump)],env=env,capture_output=True,timeout=45,creationflags=NO_WINDOW)
        self.assertEqual(result.returncode,0,'Native dump failed; raw output stays private')
        restored=self.lab.create_database('categories1089-restored');env['PGPASSFILE']=str(restored.directory/'owner.pgpass')
        result=subprocess.run([str(self.lab.pg_bin/'pg_restore.exe'),*common,'-U',restored.owner,'-d',restored.name,'--exit-on-error','--no-owner','--no-privileges',str(dump)],env=env,capture_output=True,timeout=45,creationflags=NO_WINDOW)
        self.assertEqual(result.returncode,0,'Native restore failed; raw output stays private')
        self.assertEqual(self.rows(restored),before);self.assertEqual(self.rows(),before)
        self.assertEqual(self.lab.sql(restored,f"SELECT result_json FROM user_category_color_operation WHERE request_id='{receipt['requestId']}'"),json.dumps(receipt,separators=(',',':')))
        self.assertEqual(self.lab.sql(restored,f"SELECT state FROM user_category_color_operation WHERE request_id='{fence}'"),'cancelled')
        # Exercise the local owner recovery CLI13 against the restored schema, without Windows operators.
        instance=uuid.uuid4();old_name,old_owner=restored.name,restored.owner
        restored.name,restored.owner='rc_db_'+instance.hex,'rc_owner_'+instance.hex
        self.lab.sql('postgres',f'ALTER DATABASE {old_name} RENAME TO {restored.name}; ALTER ROLE {old_owner} RENAME TO {restored.owner};',admin=True)
        (restored.directory/'owner.pgpass').write_text(f'127.0.0.1:{self.lab.port}:{restored.name}:{restored.owner}:{restored.owner_password}\n',encoding='utf-8')
        (restored.directory/'credentials.json').write_text(json.dumps({'database':restored.name,'owner':restored.owner,
            'ownerPassword':restored.owner_password,'runtime':restored.runtime,'runtimePassword':restored.runtime_password}),encoding='utf-8')
        digest=hashlib.sha256(dump.read_bytes()).hexdigest()
        self.lab.sql(restored,f"COMMENT ON DATABASE {restored.name} IS 'RackClickRecoveryPending:{instance}:{digest}'")
        env=self.lab.environment();env.update(ConnectionStrings__RackClick=restored.connection(self.lab.port,runtime=False),
            Recovery__User='category1089-recovery',Recovery__ExpectedDatabase=restored.name,Recovery__BackupSha256=digest)
        recovery=subprocess.run([str(self.lab.dotnet),str(self.dll),'--recover-admin'],input=self.password+'\n',env=env,
            capture_output=True,text=True,encoding='utf-8',timeout=30,creationflags=NO_WINDOW)
        self.assertEqual(recovery.returncode,0,'CLI13 recovery failed; private output not exported')
        self.assertFalse(recovery.stderr);self.assertEqual(json.loads(recovery.stdout)['status'],'committed')
        invariant=set(before)-{'systemhaus','app_session','app_user','user_group','user_group_member','permission_grant','audit_event'}
        self.assertEqual(self.rows(restored,invariant),{k:before[k] for k in invariant})
        self.assertEqual(self.lab.sql(restored,'SELECT count(*) FROM app_session'),'0')
        self.assertEqual(self.lab.sql(restored,"SELECT count(*) FROM audit_event WHERE action='deployment.recover'"),'1')
        self.assertEqual(self.rows(),before)
        self.__class__.backup_observation={'tableCount':39,'exactRows':True,'sourceUnchanged':True,'copiedSessionsUsed':False,
            'recoveryCli13Executed':True,'recoveryOriginalPaletteReceiptsPreferencesExact':True,'recoveryCopiedSessionsRevoked':True,
            'scope':'Native isolated pg_dump/pg_restore39 followed by explicit owner CLI13; no operational Windows package/update/QA selection.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['dll','baseline-dll','frontend','evidence']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--baseline-sha256',required=True);parser.add_argument('--case',action='append',required=True);args=parser.parse_args()
    available=[name for name in UserCategoryColors1089.__dict__ if name.startswith('test_')]
    if set(args.case)-set(available):raise ValueError('Unknown palette focus')
    names=[name for name in available if name in args.case]
    args.dll=args.dll.resolve();args.baseline_dll=args.baseline_dll.resolve();args.frontend=args.frontend.resolve()
    if hashlib.sha256(args.baseline_dll.read_bytes()).hexdigest()!=args.baseline_sha256.lower() or args.baseline_dll==args.dll:
        raise ValueError('Distinct explicitly hashed frozen schema12 baseline required')
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
        'schemaVersion':13,'actualQaOpened':False,'historicalResultsReused':False}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lab=Lab('personal-category-categories1089');UserCategoryColors1089.lab=lab
    UserCategoryColors1089.dll,UserCategoryColors1089.frontend,UserCategoryColors1089.baseline=args.dll,args.frontend,args.baseline_dll
    UserCategoryColors1089.backup_observation=None
    UserCategoryColors1089.connection_observation=None
    UserCategoryColors1089.expiry_observation=None
    report['versions']={name:subprocess.run([str(path),'--version'],capture_output=True,text=True,check=True,creationflags=NO_WINDOW).stdout.strip()
        for name,path in [('dotnet',lab.dotnet),('postgres',lab.pg_bin/'postgres.exe')]}
    started=time.monotonic()
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(UserCategoryColors1089(name) for name in names))
        report.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started,3),labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers),sourcesUnchanged=original==sources(),
        serverUnchanged=server==distribution(args.dll.parent),frontendUnchanged=frontend==distribution(args.frontend),
        baselineUnchanged=baseline==distribution(args.baseline_dll.parent),backup=UserCategoryColors1089.backup_observation,
        connectionCreation=UserCategoryColors1089.connection_observation,inventoryExpiry=UserCategoryColors1089.expiry_observation)
    (args.evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(report[k] for k in ['successful','labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged','baselineUnchanged']) else 1


if __name__=='__main__':sys.exit(main())
