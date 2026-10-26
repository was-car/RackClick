"""Catalog114-128: seven bounded native PG focuses; explicit frozen distributions, new labs only."""
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


class InventoryCatalogPostgres(InventoryReadViewsPostgres):
    def catalog(self, language='en', revision=None, customer=None, client=None, status=200, query=None, headers=None):
        customer = customer or self.customer_id
        if revision is None: revision = self.snapshot(customer)['revision']
        response = self.expect((client or self.admin).request('GET', f'/api/v1/customers/{customer}/catalog?' +
            (query if query is not None else 'language=' + language), headers={'If-Match': f'"{revision}"', **(headers or {})}), status)
        if status != 200: return response
        value = response.json()
        self.assertEqual(set(value), {'customerId','revision','language','catalogVersion','catalogSha256','categories','presets'})
        self.assertEqual(value['customerId'], customer); self.assertEqual(value['revision'], revision)
        self.assertEqual(response.headers['etag'], f'"{revision}"'); self.assertEqual(value['language'], language)
        return value

    def payload(self, preset, rack=None, room=None, kind='rackEquipment', language='en', **changes):
        catalog = self.catalog(language)
        definition = next(p for p in catalog['presets'] if p['key'] == preset)
        return {'presetKey':preset, 'catalogVersion':catalog['catalogVersion'], 'catalogSha256':catalog['catalogSha256'],
            'language':language, 'kind':kind, 'rackId':rack, 'roomId':room, 'name':'Literal Ω ' + preset,
            'color':definition['color'], 'poeBudget':None, 'notes':{'sn':'','model':'','ip':'','firmware':'','text':''}, **changes}

    def create_catalog(self, payload, **options):
        return self.command('device.createFromCatalog', payload, **options)

    def assert_created(self, result, payload):
        project = self.snapshot(); device = next(d for d in project['devices'] if d['id'] == result['result']['resourceId'])
        definition = next(p for p in self.catalog(payload['language'])['presets'] if p['key'] == payload['presetKey'])
        self.assertEqual(device['kind'], payload['kind']); self.assertEqual(device['name'], payload['name'].strip())
        self.assertEqual(device['rackId'], payload['rackId']); self.assertEqual(device['roomId'], payload['roomId'])
        self.assertEqual(device['sizeU'], definition['sizeU'] if payload['kind'] == 'rackEquipment' else None)
        self.assertEqual(device['poeBudget'], payload['poeBudget']); self.assertEqual(device['properties']['notes'], payload['notes'])
        self.assertEqual(device['properties']['color'], payload['color']); self.assertEqual(device['properties']['icon'], definition['icon'])
        self.assertEqual(device['properties']['preset'], definition['label'])
        self.assertEqual(device['properties']['catalog'], {'presetKey':payload['presetKey'],'version':payload['catalogVersion'],
            'sha256':payload['catalogSha256'],'language':payload['language']})
        groups = sorted([g for g in project['portGroups'] if g['deviceId'] == device['id']], key=lambda g:g['sortOrder'])
        self.assertEqual(len(groups), len(definition['portGroups'])); created = [device['id']]
        for actual, expected in zip(groups, definition['portGroups']):
            self.assertEqual({k:actual[k] for k in ['type','name','prefix','sortOrder']}, {k:expected[k] for k in ['type','name','prefix','sortOrder']})
            ports = sorted([p for p in project['ports'] if p['groupId'] == actual['id']], key=lambda p:p['sortOrder'])
            self.assertEqual(len(ports), len(expected['ports'])); created.append(actual['id'])
            for port, canonical in zip(ports, expected['ports']):
                self.assertEqual(port['deviceId'], device['id']); self.assertEqual({k:port[k] for k in canonical}, canonical)
                created.append(port['id'])
        self.assertEqual(result['result']['createdIds'], created); self.assertEqual(len(created), len(set(created)))
        for identity in created: uuid.UUID(identity)
        return device, groups

    def test_catalog_33_by_3_readonly_and_rich_instantiation(self):
        raw = (WORKSPACE/'development/catalog/rc9-catalog.json').read_bytes(); reference = json.loads(raw)
        _,_,room,rack = self.hierarchy(); before = self.durable()
        for language in ['en','de','es']:
            value = self.catalog(language)
            self.assertEqual(value['catalogVersion'], 'rc9-base-v1'); self.assertEqual(value['catalogSha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(value['categories'], reference['languages'][language]['categories'])
            self.assertEqual(value['presets'], reference['languages'][language]['presets'])
            self.assertEqual(len(value['presets']), 33); self.assertEqual(len(value['categories']), 7)
        self.assertEqual(before, self.durable())
        # Covers every connector type actually present, both power roles, zero ports and all languages.
        found = set()
        for key, language in [('sw24p','en'),('srv4u','de'),('ups','es'),('pdu','de'),('sw8','en'),('bl1u','en'),('nas1u','es'),('ap','es')]:
            payload = self.payload(key, room=room['id'], kind='endDevice', language=language) if key == 'ap' else self.payload(key, rack=rack['id'], language=language)
            result = self.create_catalog(payload).json(); self.assert_created(result, payload)
            found.update(p['type'] for p in self.snapshot()['ports'])
        expected = {p['type'] for d in reference['languages']['en']['presets'] for g in d['portGroups'] for p in g['ports']}
        self.assertEqual(found, expected); self.assertEqual(self.snapshot()['connections'], [])
        document = self.expect(self.admin.request('GET','/api/v1/openapi.json'),200).json()
        endpoint = document['paths']['/api/v1/customers/{id}/catalog']['get']
        self.assertEqual([p['name'] for p in endpoint['parameters'] if p['in']=='header'], ['If-Match'])
        self.assertFalse(document['components']['schemas']['CreateDeviceFromCatalog']['additionalProperties'])

    def test_closed_inputs_limits_ap_and_placement(self):
        _,_,room,rack = self.hierarchy(); valid = self.payload('sw24p', rack=rack['id'])
        invalid = [{**valid,key:value} for key,value in [('ports',[]),('portGroups',[]),('id',uid()),('properties',{}),
            ('language','EN'),('kind','device'),('color',None),('color','#xyz123'),('poeBudget',-1),('poeBudget',1000000),
            ('poeBudget','0'),('name',''),('name','a'*101),('name','bad\x00'),('roomId',room['id']),('rackId',None),('presetKey','missing')]]
        invalid += [{k:v for k,v in valid.items() if k!='roomId'}, {**valid,'notes':{}},
            {**valid,'notes':{**valid['notes'],'extra':''}}, {**valid,'notes':{**valid['notes'],'sn':'x'*2001}},
            {**valid,'notes':{k:'x'*1700 for k in valid['notes']}}]
        invalid += [self.payload('ap', rack=rack['id']), self.payload('ap', room=room['id'], kind='dose')]
        for payload in invalid:
            before = self.durable(); self.create_catalog(payload,status=422); self.assertEqual(before,self.durable())
        raw = json.dumps({'type':'device.createFromCatalog','payload':valid}).replace('"presetKey": "sw24p"', '"presetKey":"sw24p","presetKey":"pdu"').encode()
        before = self.durable()
        self.expect(self.admin.request('POST',f'/api/v1/customers/{self.customer_id}/commands',raw,
            {'Content-Type':'application/json','If-Match':f'"{self.snapshot()["revision"]}"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),422)
        self.assertEqual(before,self.durable())
        for query in ['','language=en&language=de','language=en&extra=1','language=fr','Language=en']:
            self.catalog(query=query,status=422)
        self.catalog(headers={'If-Match':''},status=428); self.catalog(headers={'If-Match':'bad'},status=422)
        for kind in ['dose','endDevice']:
            payload = self.payload('pdu',room=room['id'],kind=kind,poeBudget=0)
            self.assert_created(self.create_catalog(payload).json(),payload)
        payload = self.payload('bl1u',rack=rack['id'],name='😀'*100,poeBudget=None)
        self.assert_created(self.create_catalog(payload).json(),payload)
        small = self.create('rack',{'name':'Small','roomId':room['id'],'sizeU':1},'racks')
        before=self.durable(); self.create_catalog(self.payload('srv4u',rack=small['id']),status=409); self.assertEqual(before,self.durable())

    def test_authorization_headers_foreign_and_revoke_after_wait(self):
        _,_,_,rack=self.hierarchy(); payload=self.payload('pdu',rack=rack['id'])
        reader,_,_=self.add_user('catalog-reader',['inventory.read'],self.customer_id)
        editor,_,_=self.add_user('catalog-edit-only',['inventory.edit'],self.customer_id)
        self.catalog(client=reader); self.catalog(client=editor,status=404)
        self.create_catalog(payload,client=reader,status=403); self.create_catalog(payload,client=editor,status=404)
        foreign=self.customer('Hidden catalog customer')['id']; _,_,_,foreign_rack=self.hierarchy('Foreign',customer=foreign)
        self.catalog(customer=foreign,client=reader,status=404)
        before=self.durable(); self.create_catalog({**payload,'rackId':foreign_rack['id']},status=404); self.assertEqual(before,self.durable())
        path=f'/api/v1/customers/{self.customer_id}/commands'; revision=self.snapshot()['revision']
        headers={'If-Match':f'"{revision}"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}
        body={'type':'device.createFromCatalog','payload':payload}
        self.expect(self.admin.request('POST',path,body,{**headers,'X-RackClick-CSRF':'bad'}),403,'csrf_invalid')
        self.expect(self.admin.request('POST',path,body,{**headers,'X-RackClick-Actor':reader.actor_id}),409,'actor_changed')
        anonymous=Client(self.server); self.catalog(client=anonymous,status=401)
        for mode in ['read','edit','session']:
            client,group,_=self.add_user('catalog-wait-'+mode,['inventory.read','inventory.edit'],self.customer_id)
            label='catalogwait_'+uid()
            with ThreadPoolExecutor(2) as pool:
                holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT id FROM customer WHERE id='{self.customer_id}' FOR UPDATE; SELECT pg_sleep(3); COMMIT;")
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
                pending=pool.submit(client.request,'GET',f'/api/v1/customers/{self.customer_id}/catalog?language=en',None,{'If-Match':f'"{revision}"'}) if mode=='read' else pool.submit(client.request,'POST',path,body,{**headers,'Idempotency-Key':uid(),'X-RackClick-Actor':client.actor_id})
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
                self.lab.sql(self.db,f"DELETE FROM app_session WHERE user_id='{client.actor_id}'" if mode=='session' else f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability='inventory.{mode}'")
                self.expect(pending.result(timeout=15), {'read':404,'edit':403,'session':401}[mode]); holder.result(timeout=10)

    def test_replay_concurrency_stale_and_digest(self):
        _,_,_,rack=self.hierarchy(); payload=self.payload('pdu',rack=rack['id']); revision=self.snapshot()['revision']; key=uid()
        with ThreadPoolExecutor(2) as pool:
            replies=list(pool.map(lambda _:self.create_catalog(payload,revision=revision,key=key).json(),range(2)))
        self.assertEqual(replies[0],replies[1]); self.assert_created(replies[0],payload)
        self.command('device.update',{'id':replies[0]['result']['resourceId'],'name':'Later user change'})
        before=self.durable(); self.assertEqual(self.create_catalog(payload,revision=revision,key=key).json(),replies[0]); self.assertEqual(before,self.durable())
        self.expect(self.create_catalog({**payload,'catalogSha256':'0'*64},revision=revision,key=key,status=409),409,'request_id_reused')
        self.catalog(revision=revision,status=412); self.create_catalog(payload,revision=revision,status=412)
        revision=self.snapshot()['revision']; path=f'/api/v1/customers/{self.customer_id}/commands'
        with ThreadPoolExecutor(2) as pool:
            replies=list(pool.map(lambda n:self.admin.request('POST',path,{'type':'device.createFromCatalog','payload':{**payload,'name':'Concurrent '+str(n)}},
                {'If-Match':f'"{revision}"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),range(2)))
        self.assertEqual(sorted(r.status for r in replies),[200,412])

    def test_partial_insert_rollback_single_audit_and_change_feed(self):
        _,_,_,rack=self.hierarchy(); payload=self.payload('pdu',rack=rack['id']); revision=self.snapshot()['revision']
        self.lab.sql(self.db,"CREATE FUNCTION catalog_test_reject_second() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.gn=2 THEN RAISE EXCEPTION 'isolated fixture failure' USING ERRCODE='23514'; END IF; RETURN NEW; END $$; CREATE TRIGGER catalog_test_failure BEFORE INSERT ON inventory_port FOR EACH ROW EXECUTE FUNCTION catalog_test_reject_second();")
        try:
            before=self.durable(); self.create_catalog(payload,status=409); self.assertEqual(before,self.durable())
        finally: self.lab.sql(self.db,'DROP TRIGGER catalog_test_failure ON inventory_port; DROP FUNCTION catalog_test_reject_second();')
        result=self.create_catalog(payload).json(); self.assert_created(result,payload)
        self.assertEqual(self.snapshot()['revision'],revision+1)
        row=json.loads(self.lab.sql(self.db,f"SELECT row_to_json(t) FROM audit_event t WHERE request_id='{result['requestId']}'"))
        self.assertEqual(row['id'],result['operationId']); self.assertEqual(row['action'],'inventory.device.createFromCatalog')
        self.assertEqual(row['before_json']['revision'],revision); self.assertEqual(row['after_json']['revision'],revision+1)
        self.assertEqual(row['resource_id'],result['result']['resourceId']); self.assertEqual(row['after_json']['data']['createdIds'],result['result']['createdIds'])
        self.assertEqual(int(self.lab.sql(self.db,f"SELECT count(*) FROM operation WHERE request_id='{result['requestId']}'")),1)
        feed=self.poll(revision); self.assertFalse(feed['refreshRequired']); self.assertEqual(len(feed['events']),1)
        self.assertEqual(feed['events'][0]['action'],'inventory.device.createFromCatalog'); self.assertEqual(feed['events'][0]['context'],self.no_context())

    def test_manual_groups_compatibility_catalog_stale_and_cancellation(self):
        _,_,room,rack=self.hierarchy()
        device,groups,ports=self.device('Manual unchanged',rack=rack['id'],groups=[{'type':'rj45','count':2,'name':'A'},{'type':'rj45','count':1,'name':'B'}])
        self.assertEqual(sorted(p['gn'] for p in ports),[1,1,2])
        self.port_changes(device,groups[0],[p for p in ports if p['groupId']==groups[0]['id']],{'face':'rear','label':'Literal','color':'#aBcD12','poe':True,'watts':0})
        old={p['id']:p for p in self.snapshot()['ports']}; desired={'deviceId':device['id'],'groups':self.desired_groups(device['id'],add=1),'removedPortIds':[]}
        preview=self.preview('device.editPortGroups',desired); self.command('device.editPortGroups',{**desired,'confirmationToken':preview['confirmationToken']})
        now={p['id']:p for p in self.snapshot()['ports']}
        for identity,port in old.items(): self.assertEqual(now[identity],port)
        payload=self.payload('ap',room=room['id'],kind='endDevice')
        for patch in [{'catalogVersion':'old-reference'},{'catalogSha256':'0'*64}]:
            before=self.durable(); self.expect(self.create_catalog({**payload,**patch},status=409),409,'catalog_changed'); self.assertEqual(before,self.durable())
        revision=self.snapshot()['revision']; key=uid()
        response=self.expect(self.admin.request('POST',f'/api/v1/customers/{self.customer_id}/operations/{key}/cancel',
            {'type':'device.createFromCatalog','payload':payload},{'If-Match':f'"{revision}"','Idempotency-Key':key,'X-RackClick-Actor':self.admin_id}),200)
        self.assertEqual(response.json()['state'],'cancelled'); before=self.durable()
        self.expect(self.create_catalog(payload,revision=revision,key=key,status=409),409,'operation_cancelled'); self.assertEqual(before,self.durable())

    def test_restart_persistence_other_actor_and_operation_recovery(self):
        _,_,room,rack=self.hierarchy(); payload=self.payload('ups',rack=rack['id'],language='de',poeBudget=0)
        result=self.create_catalog(payload).json(); self.assert_created(result,payload)
        other,_,_=self.add_user('catalog-second',['inventory.read','inventory.edit'],self.customer_id)
        before=self.snapshot(); expected_catalog=self.catalog('de')
        self.assertEqual(self.snapshot(client=other),before); self.assertEqual(self.catalog('de',client=other),expected_catalog)
        self.server.close(); self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend)
        self.admin.server=self.server; other.server=self.server
        self.assertEqual(self.snapshot(client=other),before); self.assertEqual(self.catalog('de'),expected_catalog)
        recovered=self.expect(self.admin.request('GET',f'/api/v1/customers/{self.customer_id}/operations/{result["requestId"]}'),200).json()
        self.assertEqual(recovered['state'],'committed'); self.assertEqual(recovered['operation'],result)
        payload2=self.payload('ap',room=room['id'],kind='endDevice',language='es')
        created=self.create_catalog(payload2,client=other).json(); self.assert_created(created,payload2)
        self.assertFalse(set(created['result']['createdIds']) & set(result['result']['createdIds']))


def distribution(path):
    return {p.relative_to(path).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob('*')) if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['dll','frontend','evidence']: parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',action='append',required=True); args=parser.parse_args()
    available=[n for n in InventoryCatalogPostgres.__dict__ if n.startswith('test_')]
    if set(args.case)-set(available): raise ValueError('Unknown catalog case')
    names=[n for n in available if n in args.case]
    args.dll=args.dll.resolve(); args.frontend=args.frontend.resolve(); args.evidence.mkdir(parents=True,exist_ok=False)
    files=[p for p in (WORKSPACE/'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files+=list((WORKSPACE/'development/server/database').glob('*.sql'))
    files+=[WORKSPACE/'development/catalog/rc9-catalog.json',Path(__file__).resolve()]
    files+=[WORKSPACE/'development/server/tests'/n for n in ['pg_support.py','test_postgres.py','test_inventory_changes.py','test_inventory_postgres.py','test_inventory_read_views.py']]
    def sources(): return {p.relative_to(WORKSPACE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original=sources(); server=distribution(args.dll.parent); frontend=distribution(args.frontend)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),
        'serverPath':str(args.dll.parent),'frontendPath':str(args.frontend),'serverHashes':server,'frontendHashes':frontend,
        'sourceHashes':original,'selectedCases':names,'schemaVersion':7,'actualQaOpened':False}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lab=Lab('inventory-catalog'); InventoryCatalogPostgres.lab=lab
    report['versions']={name:subprocess.run([str(path),'--version'],capture_output=True,text=True,check=True,creationflags=NO_WINDOW).stdout.strip()
        for name,path in [('dotnet',lab.dotnet),('postgres',lab.pg_bin/'postgres.exe')]}
    InventoryCatalogPostgres.dll,InventoryCatalogPostgres.frontend=args.dll,args.frontend
    started=time.monotonic()
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(InventoryCatalogPostgres(n) for n in names))
        report.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started,3),labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers),sourcesUnchanged=original==sources(),
        serverUnchanged=server==distribution(args.dll.parent),frontendUnchanged=frontend==distribution(args.frontend))
    (args.evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(report[k] for k in ['successful','labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged']) else 1


if __name__=='__main__': sys.exit(main())
