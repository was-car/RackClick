"""Eight native Windows/PostgreSQL focuses: immutable customer-shared copies, schema10."""
import argparse
import base64
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
from test_private_device_templates import PrivateDeviceTemplatesPostgres, MAX_REVISION, METADATA, distribution, uid
from test_private_template_configurations import definition, wire

SHARED_TABLES={'customer_device_templates','customer_device_template','customer_device_template_operation'}
SHARED_METADATA=METADATA|{'publishedById','publishedByName'}


class SharedDeviceTemplatesPostgres(PrivateDeviceTemplatesPostgres):
    def shared_path(self, customer=None, template=None, key=None, cancel=False):
        path=f'/api/v1/customers/{customer or self.customer_id}/catalog/shared-templates'
        if template: path+='/'+template
        if key: path+='/operations/'+key
        return path+('/cancel' if cancel else '')

    def shared(self,client=None,customer=None,status=200):
        response=self.expect((client or self.admin).request('GET',self.shared_path(customer)),status)
        if status!=200:return response
        value=response.json(); self.assertEqual(set(value),{'kind','customerId','revision','templates'})
        self.assertEqual(value['kind'],'sharedTemplates'); self.assertEqual(value['customerId'],customer or self.customer_id)
        self.assertEqual(response.headers['etag'],f'"shared-templates-{value["revision"]}"')
        self.assertEqual([t['id'] for t in value['templates']],sorted(t['id'] for t in value['templates']))
        for t in value['templates']:self.assertEqual(set(t),SHARED_METADATA);self.assertTrue(t['active'])
        return value

    def shared_detail(self,template,client=None,customer=None,status=200):
        response=self.expect((client or self.admin).request('GET',self.shared_path(customer,template)),status)
        if status!=200:return response
        value=response.json();self.assertEqual(set(value),{'kind','customerId','revision','template'})
        item=value['template'];self.assertEqual(set(item),SHARED_METADATA|{'definitionByteLength','definitionBase64'})
        raw=base64.b64decode(item['definitionBase64'],validate=True)
        self.assertEqual(len(raw),item['definitionByteLength']);self.assertEqual(hashlib.sha256(raw).hexdigest(),item['definitionSha256'])
        return item,json.loads(raw.decode()),raw

    def sh(self,intent,revision=None,key=None,client=None,customer=None,status=200,headers=None):
        client=client or self.admin
        if revision is None:revision=self.shared(client,customer)['revision']
        return self.expect(client.request('POST',self.shared_path(customer),intent,
            {'If-Match':f'"shared-templates-{revision}"','Idempotency-Key':key or uid(),
             'X-RackClick-Actor':client.actor_id,**(headers or {})}),status)

    def sh_cancel(self,key,intent,revision=0,client=None,customer=None,status=200):
        client=client or self.admin
        return self.expect(client.request('POST',self.shared_path(customer,key=key,cancel=True),intent,
            {'If-Match':f'"shared-templates-{revision}"','Idempotency-Key':key,'X-RackClick-Actor':client.actor_id}),status)

    def sh_status(self,key,client=None,customer=None,status=200):
        return self.expect((client or self.admin).request('GET',self.shared_path(customer,key=key)),status)

    def config(self,kind='rackEquipment',client=None,name='Own configuration'):
        client=client or self.admin;revision=self.templates(client)['revision']
        return self.expect(client.request('POST',self.path()+'/configurations',wire(definition(kind),name)[0],
            {'Content-Type':'application/json','If-Match':f'"templates-{revision}"','Idempotency-Key':uid(),
             'X-RackClick-Actor':client.actor_id}),200).json()

    def publish_intent(self,receipt,name='Publicada Café 同名 🧰'):
        return {'type':'publish','privateTemplateId':receipt['result']['templateId'],'definitionVersion':1,
            'definitionSha256':receipt['result']['definitionSha256'],'name':name}

    def once(self,key,cancel=False):
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM customer_device_template_operation WHERE request_id='{key}'"),'1')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{key}' AND action LIKE 'customer.deviceTemplate.%'"),'1')

    def test_01_exact_copy_privacy_unicode_retirement_receipt_restart(self):
        private=self.config();private_id=private['result']['templateId']
        # Deliberately noncanonical yet valid historical representation: exact TEXT/UTF8 must survive.
        raw=json.dumps(definition(),ensure_ascii=False,indent=2).replace('10.5','10.500')
        digest=hashlib.sha256(raw.encode()).hexdigest()
        self.lab.sql(self.db,f"UPDATE user_device_template SET definition_json={literal(raw)},definition_sha256='{digest}' WHERE id='{private_id}'")
        private['result']['definitionSha256']=digest;intent=self.publish_intent(private,name=' 😀'+'😀'*99+' ')
        before=self.snapshot();house=self.lab.sql(self.db,'SELECT revision FROM systemhaus');old=self.lab.sql(self.db,f"SELECT row_to_json(t) FROM user_device_template t WHERE id='{private_id}'")
        unchanged=self.durable();self.assertEqual(self.shared()['templates'],[]);self.assertEqual(self.durable(),unchanged)
        result=self.sh(intent,revision=0).json();shared_id=result['result']['templateId']
        self.assertNotEqual(shared_id,private_id);self.assertEqual(result['actorId'],self.admin_id);self.assertEqual(result['revision'],1)
        metadata,definition_read,actual=self.shared_detail(shared_id);self.assertEqual(actual,raw.encode());self.assertEqual(definition_read,definition())
        self.assertEqual(metadata['publishedById'],self.admin_id);self.assertEqual(metadata['publishedByName'],'qa-inventory-admin')
        self.assertEqual(metadata['name'],'😀'*100);self.assertEqual(self.snapshot(),before);self.assertEqual(self.poll(before['revision'])['events'],[])
        self.assertEqual(self.lab.sql(self.db,'SELECT revision FROM systemhaus'),house)
        self.assertEqual(self.lab.sql(self.db,f"SELECT row_to_json(t) FROM user_device_template t WHERE id='{private_id}'"),old)
        self.once(result['requestId']); self.assertNotIn(private_id,json.dumps(result))
        audit=self.lab.sql(self.db,f"SELECT row_to_json(t) FROM audit_event t WHERE request_id='{result['requestId']}'")
        receipt=self.lab.sql(self.db,f"SELECT row_to_json(t) FROM customer_device_template_operation t WHERE request_id='{result['requestId']}'")
        for forbidden in [private_id,'definitionBase64','definitionJson','portGroups','privateTemplateId','Etiqueta']:
            self.assertNotIn(forbidden,audit);self.assertNotIn(forbidden,receipt)
        self.change({'type':'deactivate','templateId':private_id})
        self.assertEqual(self.sh(intent,revision=0,key=result['requestId']).json(),result)
        self.sh(intent,status=409)
        retired=self.sh({'type':'deactivate','templateId':shared_id}).json()
        noop=self.sh({'type':'deactivate','templateId':shared_id}).json()
        self.assertFalse(noop['result']['changed']);self.assertEqual(noop['revision'],retired['revision']);self.assertEqual(self.shared()['templates'],[])
        self.assertEqual(self.shared_detail(shared_id)[2],raw.encode())
        self.server.close();self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend);self.admin.server=self.server
        fresh=Client(self.server);fresh.actor_id=self.admin_id;self.expect(fresh.login('qa-inventory-admin',self.password),200)
        self.assertEqual(self.shared_detail(shared_id,fresh)[2],raw.encode());self.assertEqual(self.sh_status(result['requestId'],fresh).json()['operation'],result)

    def test_02_role_union_customer_groups_isolation_csrf_closed_contract(self):
        reader,_,_=self.add_user('shared-reader',['inventory.read'],self.customer_id)
        editor,_,_=self.add_user('shared-editor',['inventory.read','inventory.edit'],self.customer_id)
        publisher,group,customer_group=self.add_user('shared-publisher',['inventory.read','inventory.edit'],self.customer_id,customer_group=True)
        own=self.config(client=publisher)
        # Different user groups union read in a customer group with publish at customer scope; no edit remains.
        self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability='inventory.edit'")
        second_group=uid();self.lab.sql(self.db,f"INSERT INTO user_group VALUES('{second_group}','{self.house_id}','Publish only'); INSERT INTO user_group_member VALUES('{self.house_id}','{publisher.actor_id}','{second_group}'); INSERT INTO permission_grant(id,systemhaus_id,user_group_id,capability,customer_id) VALUES('{uid()}','{self.house_id}','{second_group}','templates.publish','{self.customer_id}')")
        intent=self.publish_intent(own);result=self.sh(intent,client=publisher).json();template=result['result']['templateId']
        self.assertEqual(self.shared(reader)['templates'][0]['id'],template);self.shared_detail(template,reader)
        self.detail(own['result']['templateId'],reader,status=404);self.detail(own['result']['templateId'],self.admin,status=404)
        self.sh(intent,client=reader,status=403);self.sh(intent,client=editor,status=403)
        self.sh_status(result['requestId'],reader,status=403);self.sh_cancel(uid(),intent,client=reader,status=403)
        # Own private source lookup remains mandatory for new publications, even for global administrator.
        self.sh(intent,status=404)
        other=self.customer('Hidden shared customer')['id'];self.shared(reader,other,status=404);self.shared_detail(template,self.admin,other,status=404)
        _,_,room,rack=self.hierarchy();payload=self.payload(self.shared_detail(template)[0],rack=rack['id'])
        self.command('device.createFromSharedTemplate',payload,client=publisher,status=403)
        self.command('device.createFromSharedTemplate',payload,client=reader,status=403)
        self.command('device.createFromSharedTemplate',payload,client=editor)
        self.sh({'type':'deactivate','templateId':template})  # Any current scoped publisher can retire another author's copy.
        self.sh(intent,client=publisher,headers={'X-RackClick-CSRF':'bad'},status=403)
        self.sh(intent,client=publisher,headers={'X-RackClick-Actor':editor.actor_id},status=409)
        self.expect(publisher.request('GET',self.shared_path()+'?language=de'),422)
        good={'If-Match':'"shared-templates-2"','Idempotency-Key':uid(),'X-RackClick-Actor':publisher.actor_id}
        for bad in [{**intent,'ownerId':uid()},{**intent,'sourceTemplateId':uid()},{**intent,'definition':{}},
            {**intent,'definitionVersion':2},{**intent,'definitionSha256':'A'*64},{**intent,'name':'😀'*101},
            {**intent,'name':'bad\x01'},{**intent,'name':'  '},{k:v for k,v in intent.items() if k!='name'}]:
            self.sh(bad,revision=2,client=publisher,status=422)
        duplicate=json.dumps(intent)[:-1]+',"type":"publish"}'
        self.expect(publisher.request('POST',self.shared_path(),duplicate,{**good,'Content-Type':'application/json'}),422)
        for etag in ['"templates-2"','"shared-templates-02"','shared-templates-2','"shared-templates-9007199254740992"']:
            self.sh(intent,revision=2,client=publisher,headers={'If-Match':etag},status=422)
        self.expect(publisher.request('POST',self.shared_path(),intent,{'Idempotency-Key':uid(),'X-RackClick-Actor':publisher.actor_id}),428)
        spec=self.expect(self.admin.request('GET','/api/v1/openapi.json'),200).json()
        for shape in ['SharedTemplatePublish','SharedTemplateDeactivate','SharedTemplateMetadata','SharedTemplateDetail','SharedTemplateResult','SharedTemplateStatus','CreateDeviceFromSharedTemplate']:
            self.assertFalse(spec['components']['schemas'][shape]['additionalProperties'])
        self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM permission_grant WHERE capability='templates.publish' AND customer_id IS NULL AND customer_group_id IS NULL"),'1')

    def test_03_terminal_replay_fence_concurrency_no_source_dependency(self):
        private=self.config();intent=self.publish_intent(private);key=uid();first=self.sh(intent,revision=0,key=key).json()
        self.assertEqual(self.sh(intent,revision=0,key=key).json(),first)
        self.sh({**intent,'name':'different'},revision=0,key=key,status=409);self.sh(intent,revision=1,key=key,status=409)
        other=self.customer('Other context')['id'];self.sh(intent,revision=0,key=key,customer=other,status=409);self.sh_status(key,customer=other,status=404)
        self.lab.sql(self.db,f"DELETE FROM user_device_template WHERE id='{private['result']['templateId']}'")
        self.sh({'type':'deactivate','templateId':first['result']['templateId']})
        self.assertEqual(self.sh(intent,revision=0,key=key).json(),first);self.assertEqual(self.sh_cancel(key,intent,revision=0).json()['operation'],first)
        absent={**intent,'privateTemplateId':uid()};fence=uid();self.assertEqual(self.sh_cancel(fence,absent,revision=0).json()['state'],'cancelled')
        self.expect(self.sh(absent,revision=0,key=fence,status=409),409,'operation_cancelled');self.once(fence)
        self.assertEqual(self.sh_status(uid()).json()['state'],'notRecorded')
        fresh=self.config();intent=self.publish_intent(fresh);revision=self.shared()['revision'];same=uid()
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda _:self.sh(intent,revision=revision,key=same).json(),range(2)))
        self.assertEqual(results[0],results[1]);self.once(same)
        race=uid();revision=self.shared()['revision'];headers={'If-Match':f'"shared-templates-{revision}"','Idempotency-Key':race,'X-RackClick-Actor':self.admin_id}
        with ThreadPoolExecutor(2) as pool:
            apply=pool.submit(self.admin.request,'POST',self.shared_path(),intent,headers)
            cancel=pool.submit(self.sh_cancel,race,intent,revision)
            a,c=apply.result(timeout=15),cancel.result(timeout=15).json()
        if c['state']=='cancelled':self.expect(a,409,'operation_cancelled')
        else:self.expect(a,200);self.assertEqual(c['operation'],a.json())
        self.once(race)

    def test_04_atomic_publication_retirement_fence_and_inventory_rollback(self):
        private=self.config();intent=self.publish_intent(private);published=self.sh(intent).json();template=published['result']['templateId']
        _,_,room,rack=self.hierarchy();payload=self.payload(self.shared_detail(template)[0],rack=rack['id'])
        for table in ['audit_event','customer_device_template_operation']:
            self.lab.sql(self.db,f"CREATE FUNCTION shared_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'isolated shared rollback' USING ERRCODE='23514'; END $$; CREATE TRIGGER shared_failure BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION shared_fail();")
            before=self.durable()
            try:
                self.sh(intent,status=409);self.assertEqual(self.durable(),before)
                self.sh({'type':'deactivate','templateId':template},status=409);self.assertEqual(self.durable(),before)
                self.sh_cancel(uid(),intent,status=409);self.assertEqual(self.durable(),before)
            finally:self.lab.sql(self.db,f'DROP TRIGGER shared_failure ON {table}; DROP FUNCTION shared_fail();')
        self.lab.sql(self.db,"CREATE FUNCTION shared_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'isolated inventory rollback' USING ERRCODE='23514'; END $$; CREATE TRIGGER shared_failure BEFORE INSERT ON operation FOR EACH ROW EXECUTE FUNCTION shared_fail();")
        before=self.durable()
        try:self.command('device.createFromSharedTemplate',payload,status=409);self.assertEqual(self.durable(),before)
        finally:self.lab.sql(self.db,'DROP TRIGGER shared_failure ON operation; DROP FUNCTION shared_fail();')

    def test_05_instantiation_three_kinds_second_actor_reset_changes_and_retirement_race(self):
        source,_,_,room,rack,_,_=self.rich();captured=self.capture(source)
        reader,_,_=self.add_user('shared-user-edit',['inventory.read','inventory.edit'],self.customer_id)
        created=[];receipts=[]
        for kind in ['rackEquipment','dose','endDevice']:
            private=captured if kind=='rackEquipment' else self.config(kind)
            shared=self.sh(self.publish_intent(private,name=kind)).json();metadata=self.shared_detail(shared['result']['templateId'])[0]
            payload=self.payload(metadata,rack=rack['id'] if kind=='rackEquipment' else None,room=room['id'] if kind!='rackEquipment' else None)
            before=self.snapshot();receipt=self.command('device.createFromSharedTemplate',payload,client=reader).json();receipts.append((payload,receipt,before['revision']))
            entity=receipt['result']['resourceId'];created.append(entity);snapshot=self.snapshot();ports=[p for p in snapshot['ports'] if p['deviceId']==entity]
            self.assertTrue(ports);self.assertTrue(all(p['status']=='free' and p['watts'] is None and p['properties']=={} for p in ports))
            self.assertTrue(all(c['fromPortId'] not in {p['id'] for p in ports} and c['toPortId'] not in {p['id'] for p in ports} for c in snapshot['connections']))
            event=self.poll(before['revision'])['events'];self.assertEqual(len(event),1);self.assertEqual(event[0]['action'],'inventory.device.createFromSharedTemplate')
            details=self.expect(reader.request('GET',f'/api/v1/customers/{self.customer_id}/changes/details?afterRevision={before["revision"]}'),200).json()['events'][0]['details']
            self.assertEqual(details['status'],'captured');self.assertEqual(details['beforeEntities'],[]);self.assertTrue(details['afterEntities'])
            self.sh({'type':'deactivate','templateId':metadata['id']})
            self.command('device.createFromSharedTemplate',payload,client=reader,status=409)
            self.assertEqual(self.command('device.createFromSharedTemplate',payload,client=reader,revision=before['revision'],key=receipt['requestId']).json(),receipt)
        self.assertEqual(len(created),len(set(created)))
        self.server.close();self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend);self.admin.server=self.server
        second=Client(self.server);second.actor_id=reader.actor_id;self.expect(second.login('shared-user-edit',self.password),200)
        self.assertTrue(set(created).issubset({x['id'] for x in self.snapshot(client=second)['devices']}))
        for payload,receipt,revision in receipts:self.assertEqual(self.operation_state(receipt['requestId'],client=second)['operation'],receipt)
        # Discriminating race on the same customer: retire shares customer SHARE, instantiate needs UPDATE.
        shared=self.sh(self.publish_intent(captured)).json();payload=self.payload(self.shared_detail(shared['result']['templateId'])[0],rack=rack['id'])
        before=self.snapshot()['revision'];sh_revision=self.shared()['revision']
        with ThreadPoolExecutor(2) as pool:
            retire=pool.submit(self.sh,{'type':'deactivate','templateId':shared['result']['templateId']},sh_revision)
            create=pool.submit(self.admin.request,'POST',f'/api/v1/customers/{self.customer_id}/commands',{'type':'device.createFromSharedTemplate','payload':payload},
                {'If-Match':f'"{before}"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id})
            self.expect(retire.result(timeout=15),200);response=create.result(timeout=15)
        self.assertIn(response.status,[200,409]);self.assertEqual(self.snapshot()['revision'],before+(1 if response.status==200 else 0))

    def test_06_revoke_publish_and_expiry_while_waiting_all_shared_paths(self):
        for route in ['list','detail','publish','status','cancel','create']:
            actor,group,_=self.add_user('shared-wait-'+route,['inventory.read','inventory.edit','templates.publish'],self.customer_id)
            private=self.config(client=actor);intent=self.publish_intent(private)
            shared=self.sh(intent,client=actor).json();template=shared['result']['templateId'];revision=self.shared()['revision']
            _,_,room,rack=self.hierarchy();payload=self.payload(self.shared_detail(template)[0],rack=rack['id']);inventory_revision=self.snapshot()['revision']
            lock=f'RackClick/customer-device-templates/{self.house_id}/{self.customer_id}';label='shared_wait_'+uid().replace('-','')
            with ThreadPoolExecutor(2) as pool:
                holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT pg_advisory_xact_lock(hashtextextended('{lock}',0)); SELECT pg_sleep(2); COMMIT;")
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
                key=uid();headers={'If-Match':f'"shared-templates-{revision}"','Idempotency-Key':key,'X-RackClick-Actor':actor.actor_id}
                if route=='list':pending=pool.submit(actor.request,'GET',self.shared_path())
                elif route=='detail':pending=pool.submit(actor.request,'GET',self.shared_path(template=template))
                elif route=='status':pending=pool.submit(actor.request,'GET',self.shared_path(key=shared['requestId']))
                elif route=='create':pending=pool.submit(actor.request,'POST',f'/api/v1/customers/{self.customer_id}/commands',{'type':'device.createFromSharedTemplate','payload':payload},
                    {'If-Match':f'"{inventory_revision}"','Idempotency-Key':key,'X-RackClick-Actor':actor.actor_id})
                else:pending=pool.submit(actor.request,'POST',self.shared_path(key=key,cancel=True) if route=='cancel' else self.shared_path(),intent,headers)
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
                capability='inventory.read' if route in ['list','detail','create'] else 'templates.publish'
                self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability='{capability}'")
                self.expect(pending.result(timeout=15),404 if capability=='inventory.read' else 403);holder.result(timeout=10)
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM customer_device_template_operation WHERE request_id='{key}'"),'0')
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM operation WHERE request_id='{key}'"),'0')
        # Session remains row-locked while waiting; use natural clock expiry, no privileged session edit during lock.
        actor,_,_=self.add_user('shared-expiring',['inventory.read','templates.publish'],self.customer_id)
        self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '1 second' WHERE user_id='{actor.actor_id}'")
        lock=f'RackClick/customer-device-templates/{self.house_id}/{self.customer_id}';label='shared_expire_'+uid().replace('-','')
        with ThreadPoolExecutor(2) as pool:
            holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT pg_advisory_xact_lock(hashtextextended('{lock}',0)); SELECT pg_sleep(2); COMMIT;")
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            pending=pool.submit(actor.request,'GET',self.shared_path());self.expect(pending.result(timeout=15),401);holder.result(timeout=10)

    def test_07_active_revision_bounds_and_bytes_integrity(self):
        private=self.config();intent=self.publish_intent(private);first=self.sh(intent).json();template=first['result']['templateId'];raw=self.shared_detail(template)[2]
        self.lab.sql(self.db,f"INSERT INTO customer_device_template(id,systemhaus_id,customer_id,published_by_id,published_by_name,name,definition_version,definition_sha256,definition_json) SELECT gen_random_uuid(),systemhaus_id,customer_id,published_by_id,published_by_name,name,definition_version,definition_sha256,definition_json FROM customer_device_template CROSS JOIN generate_series(1,127) WHERE id='{template}'")
        self.assertEqual(len(self.shared()['templates']),128);before=self.durable()
        self.expect(self.sh(intent,status=409),409,'templates_limit');self.assertEqual(self.durable(),before)
        self.sh({'type':'deactivate','templateId':template});self.sh(intent)
        self.lab.sql(self.db,f"UPDATE customer_device_templates SET revision={MAX_REVISION}")
        active=self.shared()['templates'][0]['id'];before=self.durable()
        self.expect(self.sh({'type':'deactivate','templateId':active},status=409),409,'templates_revision_exhausted');self.assertEqual(before,self.durable())
        self.assertFalse(self.sh({'type':'deactivate','templateId':template}).json()['result']['changed']);self.assertEqual(self.shared_detail(template)[2],raw)
        for statement in [f"UPDATE customer_device_templates SET revision=-1",f"UPDATE customer_device_templates SET revision={MAX_REVISION+1}",
            f"UPDATE customer_device_template SET published_by_id='{uid()}' WHERE id='{template}'",f"UPDATE customer_device_template SET definition_version=2 WHERE id='{template}'"]:
            with self.assertRaises(RuntimeError):self.lab.sql(self.db,statement)
        self.lab.sql(self.db,f"UPDATE customer_device_template SET definition_sha256=repeat('0',64) WHERE id='{template}'")
        self.expect(self.shared_detail(template,status=409),409,'templates_conflict')

    def test_08_populated_schema9_migrate10_exact_old_rows_no_grants_recovery_guard(self):
        source=self.lab.create_database('schema9-rich-migration10');self.assertEqual(self.lab.bootstrap(source,'qa-inventory-admin',self.password,dll=self.baseline).returncode,0)
        self.assertEqual(self.lab.sql(source,'SELECT max(version) FROM schema_migration'),'9');self.lab.grant_runtime(source)
        server=self.lab.start_server(source,dll=self.baseline,frontend=self.frontend)
        saved=(self.db,self.server,self.admin,self.house_id,self.admin_id,self.customer_id)
        try:
            self.db,self.server=source,server;self.house_id=self.lab.sql(source,'SELECT id FROM systemhaus');self.admin_id=self.lab.sql(source,'SELECT id FROM app_user')
            self.admin=Client(server);self.admin.actor_id=self.admin_id;self.expect(self.admin.login('qa-inventory-admin',self.password),200)
            self.customer_id=self.customer('Schema9 rich')['id'];device,*_=self.rich();self.capture(device);self.config('dose')
            self.add_user('schema9-reader',['inventory.read'],self.customer_id,customer_group=True)
            self.assertEqual(self.lab.sql(source,"SELECT count(*) FROM permission_grant WHERE capability='templates.publish'"),'0')
        finally:server.close();self.db,self.server,self.admin,self.house_id,self.admin_id,self.customer_id=saved
        tables=self.lab.sql(source,"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines();self.assertEqual(len(tables),30)
        def rows():return {t:self.lab.sql(source,f'SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),\'[]\') FROM "{t}" t') for t in tables if t!='schema_migration'}
        before=rows();history=self.lab.sql(source,'SELECT row_to_json(t) FROM schema_migration t ORDER BY version')
        env=self.lab.environment();env['ConnectionStrings__RackClick']=source.connection(self.lab.port,runtime=False)
        for _ in range(2):
            result=subprocess.run([str(self.lab.dotnet),str(self.dll),'--migrate'],env=env,capture_output=True,text=True,encoding='utf-8',timeout=45,creationflags=NO_WINDOW)
            self.assertEqual(result.returncode,0,'Explicit new schema10 migration failed; private details not printed');self.assertEqual(rows(),before)
            self.assertEqual(self.lab.sql(source,'SELECT row_to_json(t) FROM schema_migration t WHERE version<10 ORDER BY version'),history)
        self.assertEqual(self.lab.sql(source,'SELECT max(version) FROM schema_migration'),'10')
        self.assertEqual(self.lab.sql(source,"SELECT count(*) FROM permission_grant WHERE capability='templates.publish'"),'0')
        self.assertEqual(set(self.lab.sql(source,"SELECT tablename FROM pg_tables WHERE schemaname='public'").splitlines()),set(tables)|SHARED_TABLES)
        for table in SHARED_TABLES:self.assertEqual(self.lab.sql(source,f'SELECT count(*) FROM {table}'),'0')
        self.lab.grant_runtime(source);migrated=self.lab.start_server(source,dll=self.dll,frontend=self.frontend)
        try:
            self.assertEqual(self.expect(migrated.request('GET','/health/ready'),200).json()['schemaVersion'],10)
            admin=Client(migrated);admin.actor_id=self.lab.sql(source,'SELECT id FROM app_user WHERE username=\'qa-inventory-admin\'')
            self.expect(admin.login('qa-inventory-admin',self.password),200)
            catalog=self.expect(admin.request('GET','/api/v1/admin/capabilities'),200).json()
            self.assertIn('templates.publish',catalog['capabilities']);self.assertEqual(len(catalog['capabilities']),10)
            group=self.lab.sql(source,f"SELECT group_id FROM user_group_member WHERE user_id='{admin.actor_id}'")
            grant={'grantId':uid(),'capability':'templates.publish','scope':'systemhaus','targetId':None,'assigned':True}
            request=uid();self.expect(admin.request('POST',f'/api/v1/admin/user-groups/{group}/grants',grant,
                {'If-Match':f'\"{catalog["revision"]}\"','Idempotency-Key':request,'X-RackClick-Actor':admin.actor_id}),200)
            self.assertEqual(self.lab.sql(source,"SELECT count(*) FROM permission_grant WHERE capability='templates.publish'"),'1')
        finally:migrated.close()
        # A different new fixture, with the real deployment owner/name format, remains schema9.
        # New recovery must reject it before Apply; never reinterpret an old archive as schema10.
        probe=self.lab.create_database('recovery-schema9-refusal');self.assertEqual(self.lab.bootstrap(probe,'schema9-owner',self.password,dll=self.baseline).returncode,0)
        instance=uid().replace('-','');old_name,old_owner=probe.name,probe.owner
        name,owner='rc_db_'+instance,'rc_owner_'+instance
        self.lab.sql('postgres',f'ALTER DATABASE {old_name} RENAME TO {name}; ALTER ROLE {old_owner} RENAME TO {owner};',admin=True)
        probe.name,probe.owner=name,owner
        (probe.directory/'owner.pgpass').write_text(f'127.0.0.1:{self.lab.port}:{name}:{owner}:{probe.owner_password}\n',encoding='utf-8')
        before=self.lab.sql(probe,'SELECT row_to_json(t) FROM schema_migration t ORDER BY version; SELECT count(*) FROM app_user; SELECT count(*) FROM audit_event')
        env=self.lab.environment();env.update(ConnectionStrings__RackClick=probe.connection(self.lab.port,runtime=False),Recovery__User='recover-shared',Recovery__ExpectedDatabase=name,Recovery__BackupSha256='a'*64)
        rejected=subprocess.run([str(self.lab.dotnet),str(self.dll),'--recover-admin'],input=self.password+'\n',env=env,capture_output=True,text=True,encoding='utf-8',timeout=30,creationflags=NO_WINDOW)
        self.assertEqual(rejected.returncode,1);self.assertIn('recovery_schema_required',rejected.stdout)
        self.assertEqual(self.lab.sql(probe,'SELECT row_to_json(t) FROM schema_migration t ORDER BY version; SELECT count(*) FROM app_user; SELECT count(*) FROM audit_event'),before)
        self.assertEqual(self.lab.sql(probe,"SELECT to_regclass('public.customer_device_templates') IS NULL"),'t')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['dll','baseline-dll','frontend','evidence']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',action='append');args=parser.parse_args()
    available=[n for n in SharedDeviceTemplatesPostgres.__dict__ if n.startswith('test_')];names=args.case or available
    if set(names)-set(available):raise ValueError('Unknown shared focus')
    args.dll=args.dll.resolve();args.baseline_dll=args.baseline_dll.resolve();args.frontend=args.frontend.resolve()
    args.evidence.mkdir(parents=True,exist_ok=False)
    files=[p for p in (WORKSPACE/'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files+=list((WORKSPACE/'development/server/database').glob('*.sql'))+[Path(__file__).resolve(),WORKSPACE/'development/catalog/rc9-catalog.json']
    files+=[WORKSPACE/'development/server/tests'/n for n in ['pg_support.py','test_postgres.py','test_inventory_postgres.py','test_inventory_changes.py','test_inventory_read_views.py','test_private_device_templates.py','test_private_template_configurations.py']]
    def sources():return {p.relative_to(WORKSPACE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original=sources();server=distribution(args.dll.parent);frontend=distribution(args.frontend);baseline=distribution(args.baseline_dll.parent)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),
        'serverPath':str(args.dll.parent),'frontendPath':str(args.frontend),'baselinePath':str(args.baseline_dll.parent),
        'serverHashes':server,'frontendHashes':frontend,'baselineHashes':baseline,'sourceHashes':original,'selectedCases':names,
        'schemaVersion':10,'actualQaOpened':False,'historicalResultsReused':False}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lab=Lab('shared-device-templates');SharedDeviceTemplatesPostgres.lab=lab
    SharedDeviceTemplatesPostgres.dll,SharedDeviceTemplatesPostgres.frontend,SharedDeviceTemplatesPostgres.baseline=args.dll,args.frontend,args.baseline_dll
    report['versions']={name:subprocess.run([str(path),'--version'],capture_output=True,text=True,check=True,creationflags=NO_WINDOW).stdout.strip()
        for name,path in [('dotnet',lab.dotnet),('postgres',lab.pg_bin/'postgres.exe')]}
    started=time.monotonic()
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(SharedDeviceTemplatesPostgres(n) for n in names))
        report.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),
        sourcesUnchanged=original==sources(),serverUnchanged=server==distribution(args.dll.parent),frontendUnchanged=frontend==distribution(args.frontend),baselineUnchanged=baseline==distribution(args.baseline_dll.parent))
    (args.evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(report[k] for k in ['successful','labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged','baselineUnchanged']) else 1


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8');sys.exit(main())
