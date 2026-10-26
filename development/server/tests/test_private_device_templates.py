"""Seven private-template PostgreSQL focuses; explicit frozen artifacts and new Windows labs only."""
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
import uuid

from pg_support import Client, Lab, WORKSPACE, NO_WINDOW, literal
from test_postgres import EvidenceResult, Tee
from test_inventory_read_views import InventoryReadViewsPostgres


def uid(): return str(uuid.uuid4())
MAX_REVISION = 9007199254740991
TABLES = {'user_device_templates', 'user_device_template', 'user_device_template_operation'}
METADATA = {'id','name','active','definitionVersion','definitionSha256','kind','sizeU','groupCount','portCount'}


class PrivateDeviceTemplatesPostgres(InventoryReadViewsPostgres):
    baseline = None

    def path(self, customer=None, template=None, key=None, cancel=False):
        value = f'/api/v1/customers/{customer or self.customer_id}/catalog/private-templates'
        if template: value += '/' + template
        if key: value += '/operations/' + key
        return value + ('/cancel' if cancel else '')

    def templates(self, client=None, customer=None, status=200):
        client = client or self.admin
        response = self.expect(client.request('GET', self.path(customer)), status)
        if status != 200: return response
        value = response.json()
        self.assertEqual(set(value), {'kind','customerId','ownerId','revision','templates'})
        self.assertEqual(value['kind'],'privateTemplates'); self.assertEqual(value['ownerId'],client.actor_id)
        self.assertEqual(value['customerId'],customer or self.customer_id)
        self.assertEqual(response.headers.get('etag'),f'"templates-{value["revision"]}"')
        self.assertLessEqual(len(value['templates']),128)
        self.assertEqual([t['id'] for t in value['templates']],sorted(t['id'] for t in value['templates']))
        for item in value['templates']: self.assertEqual(set(item),METADATA); self.assertTrue(item['active'])
        return value

    def detail(self, template, client=None, customer=None, status=200):
        client=client or self.admin
        response=self.expect(client.request('GET',self.path(customer,template)),status)
        if status!=200: return response
        value=response.json(); self.assertEqual(set(value),{'kind','customerId','ownerId','revision','template'})
        item=value['template']; self.assertEqual(set(item),METADATA|{'definitionByteLength','definitionBase64'})
        raw=base64.b64decode(item['definitionBase64'],validate=True)
        self.assertEqual(len(raw),item['definitionByteLength']); self.assertLessEqual(len(raw),1048576)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),item['definitionSha256'])
        definition=json.loads(raw.decode('utf-8'))
        self.assertEqual(set(definition),{'kind','sizeU','poeBudget','icon','color','visualFamily','portGroups'})
        self.assertEqual(definition['kind'],item['kind']); self.assertEqual(definition['sizeU'],item['sizeU'])
        self.assertEqual(len(definition['portGroups']),item['groupCount'])
        self.assertEqual(sum(len(g['ports']) for g in definition['portGroups']),item['portCount'])
        for index,group in enumerate(definition['portGroups']):
            self.assertEqual(set(group),{'key','type','name','prefix','sortOrder','ports'})
            self.assertEqual(group['key'],'g'+str(index+1)); self.assertEqual(group['sortOrder'],index)
            for pindex,port in enumerate(group['ports']):
                self.assertEqual(set(port),{'gn','sortOrder','type','label','poe','color','face','powerRole'})
                self.assertEqual(port['sortOrder'],pindex)
        self.assertEqual(response.headers.get('etag'),f'"templates-{value["revision"]}"')
        return value,definition,raw

    def change(self, intent, revision=None, key=None, client=None, customer=None, status=200, headers=None):
        client=client or self.admin
        if revision is None: revision=self.templates(client,customer)['revision']
        response=self.expect(client.request('POST',self.path(customer),intent,{
            'If-Match':f'"templates-{revision}"','Idempotency-Key':key or uid(),'X-RackClick-Actor':client.actor_id,**(headers or {})}),status)
        if status==200:
            value=response.json(); self.assertEqual(set(value),{'kind','customerId','ownerId','revision','requestId','operationId','result'})
            self.assertEqual(set(value['result']),{'type','templateId','name','active','changed','definitionVersion','definitionSha256'})
            self.assertEqual(value['kind'],'privateTemplates'); self.assertEqual(value['ownerId'],client.actor_id)
            self.assertEqual(value['customerId'],customer or self.customer_id)
            self.assertEqual(response.headers.get('etag'),f'"templates-{value["revision"]}"')
        return response

    def capture_intent(self, device, name='Plantilla Café 同名', source_revision=None, customer=None):
        return {'type':'capture','deviceId':device['id'] if isinstance(device,dict) else device,'name':name,
            'sourceRevision':self.snapshot(customer)['revision'] if source_revision is None else source_revision}

    def capture(self, device, name='Plantilla Café 同名', **options):
        return self.change(self.capture_intent(device,name,customer=options.get('customer')),**options).json()

    def outcome(self,key,client=None,customer=None,status=200):
        return self.expect((client or self.admin).request('GET',self.path(customer,key=key)),status)

    def cancel_template(self,key,intent,revision=0,client=None,customer=None,status=200):
        client=client or self.admin
        return self.expect(client.request('POST',self.path(customer,key=key,cancel=True),intent,
            {'If-Match':f'"templates-{revision}"','Idempotency-Key':key,'X-RackClick-Actor':client.actor_id}),status)

    def payload(self, receipt, rack=None, room=None, **changes):
        if 'result' in receipt: template=self.detail(receipt['result']['templateId'])[0]['template']
        else: template=receipt
        return {'templateId':template['id'],'definitionVersion':1,'definitionSha256':template['definitionSha256'],
            'kind':template['kind'],'rackId':rack,'roomId':room,'name':'PDU nueva sin nombre fuente',
            'color':'#12aBcD','poeBudget':None,'notes':{'sn':'','model':'','ip':'','firmware':'','text':''},**changes}

    def rich(self):
        _,_,room,rack=self.hierarchy()
        device,groups,ports=self.device('SOURCE-PRIVATE-NAME',rack=rack['id'],size=2,groups=[
            {'type':'rj45','count':2,'name':'LAN ñ 同名','prefix':'L'},
            {'type':'power','count':1,'name':'AC','prefix':'P'},
            {'type':'usb_c','count':1,'name':'USB','prefix':'U'}])
        self.command('device.update',{'id':device['id'],'poeBudget':10.50,'properties':{
            'preset':'NAS SOURCE-PRIVATE-PRESET','icon':'▤','color':'#aAbBcC',
            'notes':{'sn':'SOURCE-PRIVATE-SERIAL','ip':'SOURCE-PRIVATE-IP','model':'SOURCE-PRIVATE-MODEL',
                'firmware':'SOURCE-PRIVATE-FIRMWARE','text':'SOURCE-PRIVATE-NOTES'},'token':'SOURCE-PRIVATE-TOKEN'}})
        # Real port commands; group identity is explicit and reused gn across groups is intentional.
        lan=next(g for g in groups if g['type']=='rj45'); power=next(g for g in groups if g['type']=='power')
        lp=sorted([p for p in ports if p['groupId']==lan['id']],key=lambda p:p['sortOrder'])
        self.port_changes(device,lan,[lp[0]],{'label':'Etiqueta ñ 同名','face':'auto','poe':True,'watts':3.5,'color':'#345678'})
        self.port_changes(device,lan,[lp[1]],{'status':'reserved','face':'front','label':'Otros','poe':False,'watts':0})
        self.port_changes(device,power,[p for p in ports if p['groupId']==power['id']],{'powerRole':'outlet','face':'auto'})
        dose,_,dp=self.device('Other endpoint',room=room['id'],kind='dose')
        cable=self.connect(lp[0],dp[0],note='SOURCE-PRIVATE-CABLE')
        # Both combinations are legal in the received inventory schema and the adopted irPoeEnabled rules.
        # These administrative fixture statements represent legacy/imported rows, not a new UI command.
        self.lab.sql(self.db,f"UPDATE inventory_port SET type='rj45',poe=true WHERE id='{lp[0]['id']}'; UPDATE inventory_port SET type='rj45_poe',poe=false WHERE id='{lp[1]['id']}'")
        self.lab.sql(self.db,f"UPDATE inventory_port SET properties='{{\"secret\":\"SOURCE-PRIVATE-PORT\"}}'::jsonb WHERE device_id='{device['id']}'")
        return device,groups,ports,room,rack,dose,cable

    def test_01_migrate_populated_eight_to_nine_preserving_all_old_tables(self):
        source=self.lab.create_database('schema8-rich-template-migration')
        self.assertEqual(self.lab.bootstrap(source,'qa-inventory-admin',self.password,dll=self.baseline).returncode,0)
        self.assertEqual(self.lab.sql(source,'SELECT max(version) FROM schema_migration'),'8'); self.lab.grant_runtime(source)
        source_server=self.lab.start_server(source,dll=self.baseline,frontend=self.frontend)
        saved=(self.db,self.server,self.admin,self.house_id,self.admin_id,self.customer_id)
        try:
            self.db,self.server=source,source_server
            self.house_id=self.lab.sql(source,'SELECT id FROM systemhaus'); self.admin_id=self.lab.sql(source,'SELECT id FROM app_user')
            self.admin=Client(source_server); self.admin.actor_id=self.admin_id; self.expect(self.admin.login('qa-inventory-admin',self.password),200)
            self.customer_id=self.customer('Rich schema8 source')['id']; self.rich()
            self.add_user('schema8-reader',['inventory.read'],self.customer_id,customer_group=True)
            reference=json.loads((WORKSPACE/'development/catalog/rc9-catalog.json').read_text(encoding='utf-8'))
            self.expect(self.admin.request('POST',f'/api/v1/customers/{self.customer_id}/catalog/favorites',
                {'presetKey':'pdu','catalogVersion':reference['catalogVersion'],
                 'catalogSha256':hashlib.sha256((WORKSPACE/'development/catalog/rc9-catalog.json').read_bytes()).hexdigest(),'favorite':True},
                {'If-Match':'"favorites-0"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),200)
        finally:
            source_server.close(); self.db,self.server,self.admin,self.house_id,self.admin_id,self.customer_id=saved
        original=self.lab.sql(source,"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
        def old_rows():
            return {t:self.lab.sql(source,f'SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),\'[]\') FROM "{t}" t')
                for t in original if t!='schema_migration'}
        before=old_rows(); history=self.lab.sql(source,'SELECT row_to_json(t) FROM schema_migration t ORDER BY version')
        environment=self.lab.environment(); environment['ConnectionStrings__RackClick']=source.connection(self.lab.port,runtime=False)
        for _ in range(2):
            result=subprocess.run([str(self.lab.dotnet),str(self.dll),'--migrate'],env=environment,
                capture_output=True,text=True,encoding='utf-8',timeout=45,creationflags=NO_WINDOW)
            self.assertEqual(result.returncode,0,'Explicit private migration failed; no credentials are printed')
            self.assertEqual(before,old_rows()); self.assertEqual(self.lab.sql(source,'SELECT row_to_json(t) FROM schema_migration t WHERE version<9 ORDER BY version'),history)
        self.assertEqual(self.lab.sql(source,'SELECT max(version) FROM schema_migration'),'9')
        self.assertEqual(set(self.lab.sql(source,"SELECT tablename FROM pg_tables WHERE schemaname='public'").splitlines()),set(original)|TABLES)
        for name in TABLES: self.assertEqual(self.lab.sql(source,f'SELECT count(*) FROM {name}'),'0')
        self.lab.grant_runtime(source); migrated=self.lab.start_server(source,dll=self.dll,frontend=self.frontend)
        try: self.expect(migrated.request('GET','/health/ready'),200)
        finally: migrated.close()
        self.assertEqual(self.lab.sql(source,f"SELECT has_schema_privilege('{source.runtime}','public','CREATE')"),'f')
        for statement in [f"INSERT INTO user_device_templates VALUES('{self.house_id}','{self.admin_id}',-1)",
            f"INSERT INTO user_device_templates VALUES('{self.house_id}','{self.admin_id}',{MAX_REVISION+1})",
            f"INSERT INTO user_device_templates VALUES('{self.house_id}','{uid()}',0)"]:
            with self.assertRaises(RuntimeError): self.lab.sql(self.db,statement)

    def test_02_capture_readonly_privacy_unicode_and_exact_raw_bytes(self):
        device,_,_,_,_,_,_=self.rich(); before=self.snapshot(); durable=self.durable()
        self.assertEqual(self.templates()['templates'],[]); self.assertEqual(self.templates()['revision'],0)
        self.assertEqual(self.durable(),durable); self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM user_device_templates'),'0')
        result=self.capture(device,name=' 🧰'*50); template=result['result']['templateId']
        detail,definition,raw=self.detail(template)
        self.assertEqual(definition['visualFamily'],'storage'); self.assertEqual(definition['poeBudget'],10.5)
        self.assertEqual((definition['kind'],definition['sizeU']),('rackEquipment',2))
        self.assertEqual(definition['portGroups'][0]['ports'][0]['label'],'Etiqueta ñ 同名')
        self.assertEqual(definition['portGroups'][0]['ports'][0]['face'],'auto')
        self.assertEqual([(p['type'],p['poe']) for p in definition['portGroups'][0]['ports']],[('rj45',True),('rj45_poe',False)])
        forbidden=['SOURCE-PRIVATE-',device['id'],self.customer_id,self.house_id,self.admin_id]
        for value in forbidden: self.assertNotIn(value,raw.decode('utf-8'))
        self.assertNotIn('status',raw.decode()); self.assertNotIn('watts',raw.decode()); self.assertNotIn('properties',raw.decode())
        self.assertEqual(self.snapshot(),before); self.assertEqual(self.poll(before['revision'])['events'],[])
        unchanged=self.durable(); self.detail(template); self.templates(); self.assertEqual(self.durable(),unchanged)
        for name in ['😀'*101,'bad\x01','   ']: self.change(self.capture_intent(device,name),status=422)
        self.capture(device,name='😀'*100)
        # Stored bytes (escaped Unicode and decimal lexical forms included) survive server restart exactly.
        self.server.close(); self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend); self.admin.server=self.server
        fresh=Client(self.server); fresh.actor_id=self.admin_id; self.expect(fresh.login('qa-inventory-admin',self.password),200)
        self.assertEqual(self.detail(template,client=fresh)[2],raw)
        self.assertEqual(self.outcome(result['requestId'],fresh).json()['operation'],result)
        spec=self.expect(fresh.request('GET','/api/v1/openapi.json'),200).json()
        for name in ['PrivateTemplateCapture','PrivateTemplateDeactivate','PrivateTemplateMetadata','PrivateTemplateDetail','PrivateTemplateResult','PrivateTemplateStatus','CreateDeviceFromPrivateTemplate']:
            self.assertFalse(spec['components']['schemas'][name]['additionalProperties'])

    def test_03_scope_roles_validation_csrf_revocation_and_expiry(self):
        device,_,_,_,_,_,_=self.rich(); receipt=self.capture(device); template=receipt['result']['templateId']
        reader,_,_=self.add_user('templates-reader',['inventory.read'],self.customer_id)
        editor,_,_=self.add_user('templates-other',['inventory.read','inventory.edit'],self.customer_id,customer_group=True)
        no_read,_,_=self.add_user('templates-no-read',['inventory.edit'],self.customer_id)
        self.assertEqual(self.templates(reader)['templates'],[]); self.detail(template,reader,status=404)
        intent=self.capture_intent(device)
        self.change(intent,client=reader,revision=0,status=403); self.outcome(uid(),reader,status=403)
        self.cancel_template(uid(),intent,client=reader,status=403); self.templates(no_read,status=404)
        self.detail(template,editor,status=404)
        hidden=self.customer('Hidden template context')['id']; self.templates(editor,hidden,status=404)
        other_result=self.capture(device,client=editor); self.assertEqual(self.templates()['templates'][0]['id'],template)
        self.assertNotEqual(other_result['result']['templateId'],template)
        good_headers={'If-Match':'"templates-1"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}
        bad=[{**intent,'ownerId':uid()},{k:v for k,v in intent.items() if k!='sourceRevision'},
            {**intent,'sourceRevision':True},{**intent,'sourceRevision':0},{**intent,'sourceRevision':MAX_REVISION+1},
            {'type':'deactivate','templateId':template,'active':False}]
        for value in bad: self.change(value,revision=1,status=422)
        duplicate=json.dumps(intent)[:-1]+',"deviceId":"'+device['id']+'"}'
        self.expect(self.admin.request('POST',self.path(),duplicate,{'Content-Type':'application/json',**good_headers}),422)
        for etag in ['"1"','templates-1','"templates-01"','"templates--1"','"templates-9007199254740992"']:
            self.change(intent,revision=1,status=422,headers={'If-Match':etag})
        self.expect(self.admin.request('POST',self.path(),intent,{'Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),428)
        self.expect(self.admin.request('POST',self.path(),intent,{'If-Match':'"templates-1"','Idempotency-Key':uid()}),422)
        self.change(intent,revision=1,status=403,headers={'X-RackClick-CSRF':'bad'})
        self.change(intent,revision=1,status=409,headers={'X-RackClick-Actor':uid()})
        self.expect(self.admin.request('GET',self.path()+'?language=en'),422)
        for route in ['list','capture','status','cancel','create']:
            actor,group,_=self.add_user('templates-revoke-'+route,['inventory.read','inventory.edit'],self.customer_id)
            previous_operations=0; private=None
            if route=='create':
                # Discriminating revocation witness: the pending create must otherwise own a usable template.
                owned=self.capture(device,client=actor)
                owned_detail=self.detail(owned['result']['templateId'],client=actor)[0]['template']
                self.assertEqual(owned_detail['id'],owned['result']['templateId']); self.assertTrue(owned_detail['active'])
                private=self.payload(owned_detail,rack=device['rackId']); previous_operations=1
            key=uid(); label='template_revoke_'+uuid.uuid4().hex
            lockkey=f'RackClick/private-device-templates/{self.house_id}/{actor.actor_id}'
            with ThreadPoolExecutor(2) as pool:
                holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT pg_advisory_xact_lock(hashtextextended('{lockkey}',0)); SELECT pg_sleep(3); COMMIT;")
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
                headers={'If-Match':'"templates-0"','Idempotency-Key':key,'X-RackClick-Actor':actor.actor_id}
                if route=='list': pending=pool.submit(actor.request,'GET',self.path())
                elif route=='status': pending=pool.submit(actor.request,'GET',self.path(key=key))
                elif route=='create':
                    pending=pool.submit(actor.request,'POST',f'/api/v1/customers/{self.customer_id}/commands',{'type':'device.createFromPrivateTemplate','payload':private},
                        {'If-Match':f'"{self.snapshot()["revision"]}"','Idempotency-Key':key,'X-RackClick-Actor':actor.actor_id})
                else: pending=pool.submit(actor.request,'POST',self.path(key=key,cancel=True) if route=='cancel' else self.path(),intent,headers)
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
                self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{group}'")
                self.expect(pending.result(timeout=15),404); holder.result(timeout=10)
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_device_template_operation WHERE owner_id='{actor.actor_id}'"),str(previous_operations))
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM operation WHERE actor_id='{actor.actor_id}' AND request_id='{key}'"),'0')
        expiring,_,_=self.add_user('templates-expiring',['inventory.read','inventory.edit'],self.customer_id)
        self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{expiring.actor_id}'")
        label='template_expire_'+uuid.uuid4().hex; lockkey=f'RackClick/private-device-templates/{self.house_id}/{expiring.actor_id}'
        with ThreadPoolExecutor(2) as pool:
            holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT pg_advisory_xact_lock(hashtextextended('{lockkey}',0)); SELECT pg_sleep(3); COMMIT;")
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            pending=pool.submit(expiring.request,'POST',self.path(),intent,{'If-Match':'"templates-0"','Idempotency-Key':uid(),'X-RackClick-Actor':expiring.actor_id})
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
            self.expect(pending.result(timeout=15),401); holder.result(timeout=10)

    def test_04_replay_cancel_distinct_conflicts_and_immutable_tombstone(self):
        device,_,_,_,_,_,_=self.rich(); intent=self.capture_intent(device); key=uid()
        first=self.change(intent,revision=0,key=key).json(); template=first['result']['templateId']; raw=self.detail(template)[2]
        self.change(intent,revision=0,status=412); self.expect(self.change({**intent,'sourceRevision':1},revision=1,status=412),412,'source_revision_conflict')
        self.command('device.update',{'id':device['id'],'name':'Changed since capture'})
        self.assertEqual(self.change(intent,revision=0,key=key).json(),first)
        self.change({**intent,'name':'Different'},revision=0,key=key,status=409)
        second=self.customer('Other template context')['id']
        self.change(intent,revision=0,key=key,customer=second,status=409); self.outcome(key,customer=second,status=404)
        deact={'type':'deactivate','templateId':template}; removed=self.change(deact).json()
        self.assertTrue(removed['result']['changed']); self.assertFalse(removed['result']['active'])
        self.assertEqual(self.templates()['templates'],[]); self.assertEqual(self.detail(template)[2],raw)
        noop=self.change(deact).json(); self.assertFalse(noop['result']['changed']); self.assertEqual(noop['revision'],removed['revision'])
        state=self.outcome(key).json(); self.assertEqual(state['operation'],first); self.assertEqual(state['revision'],removed['revision'])
        self.assertEqual(self.cancel_template(key,intent,revision=0).json(),state)
        cancelkey=uid(); impossible={'type':'capture','deviceId':uid(),'name':'Cancelled nonexistent source','sourceRevision':1}
        cancel=self.cancel_template(cancelkey,impossible,revision=0).json(); self.assertEqual(cancel['state'],'cancelled')
        self.assertEqual(self.cancel_template(cancelkey,impossible,revision=0).json(),cancel)
        self.expect(self.change(impossible,revision=0,key=cancelkey,status=409),409,'operation_cancelled')
        self.assertEqual(self.operation_state(key)['state'],'notRecorded')
        for request in [key,removed['requestId'],noop['requestId'],cancelkey]:
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_device_template_operation WHERE request_id='{request}'"),'1')
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{request}'"),'1')
        # Source may disappear after capture; replay and detached template remain meaningful.
        preview=self.preview('device.delete',{'id':device['id']})
        self.command('device.delete',{'id':device['id'],'confirmationToken':preview['confirmationToken']})
        self.assertEqual(self.change(intent,revision=0,key=key).json(),first); self.assertEqual(self.detail(template)[2],raw)

    def test_05_instantiate_three_kinds_new_ids_private_reset_and_change_feed(self):
        device,_,_,room,rack,dose,_=self.rich(); source=self.snapshot(); house=self.lab.sql(self.db,'SELECT revision FROM systemhaus')
        receipt=self.capture(device); template,definition,_=self.detail(receipt['result']['templateId'])
        target=self.customer('New target customer')['id']; _,_,target_room,target_rack=self.hierarchy(' Target',customer=target)
        payload=self.payload(template['template'],rack=target_rack['id']); revision=self.snapshot(target)['revision']; key=uid()
        created=self.command('device.createFromPrivateTemplate',payload,customer=target,revision=revision,key=key).json()
        self.assertEqual(self.command('device.createFromPrivateTemplate',payload,customer=target,revision=revision,key=key).json(),created)
        self.assertEqual(self.operation_state(key,target)['operation'],created)
        dest=self.snapshot(target); new=next(d for d in dest['devices'] if d['id']==created['result']['resourceId'])
        self.assertEqual(new['properties'],{'icon':'▤','color':'#12aBcD','preset':'storage','notes':payload['notes']})
        self.assertEqual(new['name'],payload['name']); self.assertEqual(new['sizeU'],2)
        self.assertEqual(dest['connections'],[]); self.assertEqual(self.snapshot(),source)
        source_ids={x['id'] for c in ['devices','portGroups','ports','connections'] for x in source[c]}
        created_ids=set(created['result']['createdIds']); self.assertFalse(source_ids & created_ids)
        new_ports=[p for p in dest['ports'] if p['deviceId']==new['id']]; new_groups=sorted([g for g in dest['portGroups'] if g['deviceId']==new['id']],key=lambda g:g['sortOrder'])
        self.assertEqual(len(created_ids),1+len(new_groups)+len(new_ports))
        for group,bluegroup in zip(new_groups,definition['portGroups']):
            self.assertEqual((group['type'],group['name'],group['prefix']),(bluegroup['type'],bluegroup['name'],bluegroup['prefix']))
            for port,blueport in zip(sorted([p for p in new_ports if p['groupId']==group['id']],key=lambda p:p['sortOrder']),bluegroup['ports']):
                for field in ['type','gn','sortOrder','label','poe','color','face','powerRole']: self.assertEqual(port[field],blueport[field])
                self.assertEqual((port['status'],port['watts'],port['properties']),('free',None,{}))
        self.assertEqual([(p['type'],p['poe']) for p in sorted(new_ports,key=lambda p:(p['groupId'],p['sortOrder'])) if p['type'] in ['rj45','rj45_poe']].count(('rj45',True)),1)
        self.assertEqual([(p['type'],p['poe']) for p in new_ports].count(('rj45_poe',False)),1)
        automatic=next(p for p in new_ports if p['poe']); self.assertEqual(automatic['face'],'auto')
        self.assertEqual(new['properties']['preset'],'storage')  # Existing RC9/SVG effective AUTO is rear regardless of new name PDU.
        reader,_,_=self.add_user('templates-destination-reader',['inventory.read'],target)
        events=self.poll(revision,client=reader,customer=target)['events']; self.assertEqual(len(events),1)
        self.assertEqual(events[0]['action'],'inventory.device.createFromPrivateTemplate'); self.assertEqual(events[0]['actor']['id'],self.admin_id)
        self.assertEqual(events[0]['resourceId'],new['id']); self.assertEqual(events[0]['revisionAfter'],revision+1)
        self.command('device.createFromPrivateTemplate',payload,customer=target,client=reader,status=403)
        for kind,source_device in [('dose',dose),('endDevice',self.device('AP secret name',room=room['id'],kind='endDevice')[0])]:
            record=self.capture(source_device); detail=self.detail(record['result']['templateId'])[0]['template']
            body=self.payload(detail,room=target_room['id']); result=self.command('device.createFromPrivateTemplate',body,customer=target).json()
            item=next(d for d in self.snapshot(target)['devices'] if d['id']==result['result']['resourceId'])
            self.assertEqual((item['kind'],item['sizeU'],item['rackId'],item['roomId']),(kind,None,None,target_room['id']))
            self.command('device.createFromPrivateTemplate',{**body,'kind':'rackEquipment','rackId':target_rack['id'],'roomId':None},customer=target,status=422)
        for body,error in [({**payload,'definitionSha256':'0'*64},'template_changed'),({**payload,'roomId':target_room['id']},'placement_invalid')]:
            expected=409 if error=='template_changed' else 422
            self.expect(self.command('device.createFromPrivateTemplate',body,customer=target,status=expected),expected,error)
        self.change({'type':'deactivate','templateId':payload['templateId']})
        self.expect(self.command('device.createFromPrivateTemplate',payload,customer=target,status=409),409,'template_inactive')
        self.assertEqual(self.command('device.createFromPrivateTemplate',payload,customer=target,revision=revision,key=key).json(),created)
        self.assertGreater(int(self.lab.sql(self.db,'SELECT revision FROM systemhaus')),int(house))  # Only explicit customer creation changes house.

    def test_06_concurrency_atomic_rollback_and_audit(self):
        device,_,_,_,rack,_,_=self.rich(); intent=self.capture_intent(device); key=uid(); inventory=self.snapshot(); house=self.lab.sql(self.db,'SELECT revision FROM systemhaus')
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda _:self.change(intent,revision=0,key=key).json(),range(2)))
        self.assertEqual(results[0],results[1]); self.assertEqual(self.templates()['revision'],1)
        template=results[0]['result']['templateId']; payload=self.payload(results[0],rack=rack['id'])
        trigger="CREATE FUNCTION templates_test_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'isolated rollback witness' USING ERRCODE='23514'; END $$; CREATE TRIGGER templates_test_failure BEFORE INSERT ON user_device_template_operation FOR EACH ROW EXECUTE FUNCTION templates_test_fail();"
        self.lab.sql(self.db,trigger); before=self.durable()
        try:
            self.change(self.capture_intent(device),revision=1,status=409); self.assertEqual(self.durable(),before)
            self.change({'type':'deactivate','templateId':template},revision=1,status=409); self.assertEqual(self.durable(),before)
            self.cancel_template(uid(),intent,revision=1,status=409); self.assertEqual(self.durable(),before)
        finally: self.lab.sql(self.db,'DROP TRIGGER templates_test_failure ON user_device_template_operation; DROP FUNCTION templates_test_fail();')
        self.lab.sql(self.db,"CREATE FUNCTION templates_inventory_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'isolated inventory rollback' USING ERRCODE='23514'; END $$; CREATE TRIGGER templates_inventory_failure BEFORE INSERT ON operation FOR EACH ROW EXECUTE FUNCTION templates_inventory_fail();")
        before=self.durable()
        try: self.command('device.createFromPrivateTemplate',payload,status=409); self.assertEqual(self.durable(),before)
        finally: self.lab.sql(self.db,'DROP TRIGGER templates_inventory_failure ON operation; DROP FUNCTION templates_inventory_fail();')
        self.assertEqual(self.snapshot(),inventory); self.assertEqual(self.lab.sql(self.db,'SELECT revision FROM systemhaus'),house)
        race=uid(); revision=self.templates()['revision']
        with ThreadPoolExecutor(2) as pool:
            apply=pool.submit(self.admin.request,'POST',self.path(),intent,{'If-Match':f'"templates-{revision}"','Idempotency-Key':race,'X-RackClick-Actor':self.admin_id})
            cancel=pool.submit(self.admin.request,'POST',self.path(key=race,cancel=True),intent,{'If-Match':f'"templates-{revision}"','Idempotency-Key':race,'X-RackClick-Actor':self.admin_id})
            a,c=apply.result(timeout=15),self.expect(cancel.result(timeout=15),200)
        if c.json()['state']=='cancelled': self.expect(a,409,'operation_cancelled')
        else: self.expect(a,200); self.assertEqual(c.json()['operation'],a.json())
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{race}'"),'1')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_device_template_operation WHERE request_id='{race}'"),'1')
        # Different customer locks still serialize one actor's collection by its personal aggregate.
        other=self.customer('Concurrency context')['id']; personal=self.templates()['revision']
        with ThreadPoolExecutor(2) as pool:
            replies=list(pool.map(lambda c:self.admin.request('POST',self.path(c),{'type':'deactivate','templateId':template},
                {'If-Match':f'"templates-{personal}"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),[self.customer_id,other]))
        self.assertEqual(sorted(r.status for r in replies),[200,412])
        event=json.loads(self.lab.sql(self.db,f"SELECT row_to_json(t) FROM audit_event t WHERE id='{results[0]['operationId']}'"))
        self.assertEqual(event['action'],'user.deviceTemplate.capture'); self.assertEqual(event['resource_id'],template)
        self.assertEqual(set(event['after_json']['template']),METADATA)
        def no_blueprint(value):
            if isinstance(value,dict):
                self.assertTrue(set(value).isdisjoint({'definition','definitionJson','definitionBase64','portGroups','ports','properties'}))
                for item in value.values(): no_blueprint(item)
            elif isinstance(value,list):
                for item in value: no_blueprint(item)
        no_blueprint(event); self.assertNotIn('SOURCE-PRIVATE',json.dumps(event))

    def test_07_bounds_revision_limit_and_catalog_favorites_regression(self):
        device,_,_,_,rack,_,_=self.rich(); first=self.capture(device); template=first['result']['templateId']; original=self.detail(template)[2]
        # Server-side active collection ceiling, with an explicit populated SQL fixture (not 127 UI captures).
        self.lab.sql(self.db,f"INSERT INTO user_device_template(id,systemhaus_id,owner_id,name,definition_version,definition_sha256,definition_json) SELECT gen_random_uuid(),systemhaus_id,owner_id,name,definition_version,definition_sha256,definition_json FROM user_device_template CROSS JOIN generate_series(1,127) WHERE id='{template}'")
        self.assertEqual(len(self.templates()['templates']),128); before=self.durable()
        self.expect(self.change(self.capture_intent(device),status=409),409,'templates_limit'); self.assertEqual(self.durable(),before)
        self.change({'type':'deactivate','templateId':template}); self.capture(device)
        self.lab.sql(self.db,f"UPDATE user_device_templates SET revision={MAX_REVISION} WHERE owner_id='{self.admin_id}'")
        before=self.durable(); active=self.templates()['templates'][0]['id']
        self.expect(self.change({'type':'deactivate','templateId':active},revision=MAX_REVISION,status=409),409,'templates_revision_exhausted')
        self.assertEqual(before,self.durable())
        self.assertFalse(self.change({'type':'deactivate','templateId':template},revision=MAX_REVISION).json()['result']['changed'])
        self.assertEqual(self.detail(template)[2],original)
        # Bounds are rejected, never silently truncated. Dedicated actor avoids the collection cap.
        actor,_,_=self.add_user('templates-limits',['inventory.read','inventory.edit'],self.customer_id)
        self.lab.sql(self.db,f"UPDATE inventory_port SET label=repeat('x',501) WHERE device_id='{device['id']}'")
        self.change(self.capture_intent(device),client=actor,revision=0,status=422)
        self.lab.sql(self.db,f"UPDATE inventory_port SET label='valid' WHERE device_id='{device['id']}'")
        # The database and API both forbid PoE on non-RJ45 families. No generic type normalization is introduced.
        with self.assertRaises(RuntimeError):
            self.lab.sql(self.db,f"UPDATE inventory_port SET poe=true WHERE device_id='{device['id']}' AND type='power'")
        usb_group=next(g for g in self.snapshot()['portGroups'] if g['deviceId']==device['id'] and g['type']=='usb_c')
        usb_port=next(p for p in self.snapshot()['ports'] if p['groupId']==usb_group['id'])
        self.port_changes(device,usb_group,[usb_port],{'poe':True},status=422)
        self.lab.sql(self.db,f"INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order) SELECT gen_random_uuid(),'{self.house_id}','{self.customer_id}','{device['id']}','rj45','','',100+n FROM generate_series(1,30) n")
        self.change(self.capture_intent(device),client=actor,revision=0,status=422)
        # A fresh maximum-shape fixture with valid Unicode labels exceeds the explicit byte ceiling.
        huge=uid()
        self.lab.sql(self.db,f"INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order) VALUES('{huge}','{self.house_id}','{self.customer_id}','rackEquipment','{rack['id']}','Bounded bytes',1,100); INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,sort_order) SELECT gen_random_uuid(),'{self.house_id}','{self.customer_id}','{huge}','rj45',n FROM generate_series(0,31) n; INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label) SELECT gen_random_uuid(),g.systemhaus_id,g.customer_id,g.device_id,g.id,'rj45',n+1,n,repeat('😀',500) FROM inventory_port_group g CROSS JOIN generate_series(0,95) n WHERE g.device_id='{huge}'")
        self.expect(self.change(self.capture_intent(huge),client=actor,revision=0,status=422),422,'template_definition_too_large')
        # BASE reference and personal favorites still use their unchanged independent API/revision family.
        revision=self.snapshot()['revision']; reference=self.expect(self.admin.request('GET',f'/api/v1/customers/{self.customer_id}/catalog?language=es',headers={'If-Match':f'"{revision}"'}),200).json()
        self.assertEqual(len(reference['presets']),33)
        favorite_path=f'/api/v1/customers/{self.customer_id}/catalog/favorites'
        favorite=self.expect(self.admin.request('POST',favorite_path,{'presetKey':'pdu','catalogVersion':reference['catalogVersion'],
            'catalogSha256':reference['catalogSha256'],'favorite':True},{'If-Match':'"favorites-0"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),200).json()
        self.assertEqual(favorite['revision'],1); self.assertEqual(self.templates()['revision'],MAX_REVISION)
        self.assertEqual(self.expect(self.admin.request('GET',favorite_path),200).json()['presetKeys'],['pdu'])


def distribution(path):
    return {p.relative_to(path).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob('*')) if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['dll','baseline-dll','frontend','evidence']: parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',action='append',required=True); args=parser.parse_args()
    available=[n for n in PrivateDeviceTemplatesPostgres.__dict__ if n.startswith('test_')]
    if set(args.case)-set(available): raise ValueError('Unknown private-template focus')
    names=[n for n in available if n in args.case]
    args.dll=args.dll.resolve(); args.baseline_dll=args.baseline_dll.resolve(); args.frontend=args.frontend.resolve()
    if not args.baseline_dll.is_file() or args.baseline_dll==args.dll: raise ValueError('Distinct frozen schema8 baseline DLL required')
    args.evidence.mkdir(parents=True,exist_ok=False)
    files=[p for p in (WORKSPACE/'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files+=list((WORKSPACE/'development/server/database').glob('*.sql'))+[Path(__file__).resolve(),WORKSPACE/'development/catalog/rc9-catalog.json']
    files+=[WORKSPACE/'development/server/tests'/n for n in ['pg_support.py','test_postgres.py','test_inventory_postgres.py','test_inventory_changes.py','test_inventory_read_views.py']]
    def sources(): return {p.relative_to(WORKSPACE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original=sources(); server=distribution(args.dll.parent); frontend=distribution(args.frontend); baseline=distribution(args.baseline_dll.parent)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),
        'serverPath':str(args.dll.parent),'frontendPath':str(args.frontend),'baselinePath':str(args.baseline_dll.parent),
        'serverHashes':server,'frontendHashes':frontend,'baselineHashes':baseline,'sourceHashes':original,'selectedCases':names,
        'schemaVersion':9,'actualQaOpened':False,'historicalResultsReused':False}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lab=Lab('private-device-templates'); PrivateDeviceTemplatesPostgres.lab=lab
    PrivateDeviceTemplatesPostgres.dll,PrivateDeviceTemplatesPostgres.frontend,PrivateDeviceTemplatesPostgres.baseline=args.dll,args.frontend,args.baseline_dll
    report['versions']={name:subprocess.run([str(path),'--version'],capture_output=True,text=True,check=True,creationflags=NO_WINDOW).stdout.strip()
        for name,path in [('dotnet',lab.dotnet),('postgres',lab.pg_bin/'postgres.exe')]}
    started=time.monotonic()
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(PrivateDeviceTemplatesPostgres(n) for n in names))
        report.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started,3),labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers),sourcesUnchanged=original==sources(),
        serverUnchanged=server==distribution(args.dll.parent),frontendUnchanged=frontend==distribution(args.frontend),baselineUnchanged=baseline==distribution(args.baseline_dll.parent))
    (args.evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(report[k] for k in ['successful','labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged','baselineUnchanged']) else 1


if __name__=='__main__': sys.exit(main())
