"""Six native Windows/PostgreSQL focuses for new immutable private configurations."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import http.client
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest

from pg_support import Client, Lab, WORKSPACE, NO_WINDOW, Response
from test_postgres import EvidenceResult, Tee
from test_private_device_templates import PrivateDeviceTemplatesPostgres, MAX_REVISION, distribution, uid


def definition(kind='rackEquipment'):
    return {'kind':kind,'sizeU':2 if kind=='rackEquipment' else None,'poeBudget':10.50,
        'icon':'▤','color':'#aAbBcC','visualFamily':'storage','portGroups':[
            {'key':'g1','type':'rj45','name':'LAN ñ 同名','prefix':'L','sortOrder':0,'ports':[
                {'gn':1,'sortOrder':0,'type':'rj45','label':'Etiqueta ñ 同名','poe':True,'color':'#12aBcD','face':'auto','powerRole':'unspecified'},
                {'gn':2147483647,'sortOrder':1,'type':'rj45_poe','label':'Repeated family','poe':False,'color':None,'face':'rear','powerRole':'unspecified'}]},
            {'key':'g2','type':'power','name':'AC','prefix':'P','sortOrder':1,'ports':[
                {'gn':1,'sortOrder':0,'type':'power','label':'AC inlet','poe':False,'color':None,'face':'front','powerRole':'inlet'}]}]}


def wire(config, name='Configuración Café 同名 🧰', raw=None):
    raw = json.dumps(config,ensure_ascii=True) if raw is None else raw
    body='{"type":"create","name":'+json.dumps(name,ensure_ascii=True)+',"definitionVersion":1,"definition":'+raw+'}'
    compact={'type':'create','name':name,'definitionVersion':1,'inputDefinitionSha256':hashlib.sha256(raw.encode('utf-8')).hexdigest()}
    return body, compact


class PrivateTemplateConfigurationsPostgres(PrivateDeviceTemplatesPostgres):
    def config_path(self, key=None, customer=None):
        return self.path(customer)+'/configurations'+('/operations/'+key+'/cancel' if key else '')

    def config_headers(self, revision=0, key=None, client=None):
        return {'Content-Type':'application/json','If-Match':f'"templates-{revision}"',
            'Idempotency-Key':key or uid(),'X-RackClick-Actor':(client or self.admin).actor_id}

    def configure(self, config=None, name='Configuración Café 同名 🧰', revision=None, key=None, client=None,
            customer=None, body=None, status=200, headers=None):
        client=client or self.admin
        if revision is None: revision=self.templates(client,customer)['revision']
        if body is None: body=wire(config if config is not None else definition(),name)[0]
        if isinstance(body,str): body=body.encode('utf-8')
        return self.expect(client.request('POST',self.config_path(customer=customer),body,
            {**self.config_headers(revision,key,client),**(headers or {})}),status)

    def fence(self,key,compact,revision=0,client=None,customer=None,status=200):
        client=client or self.admin
        return self.expect(client.request('POST',self.config_path(key,customer),compact,
            self.config_headers(revision,key,client)),status)

    def once(self,key,cancel=False):
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_device_template_operation WHERE request_id='{key}'"),'1')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{key}' AND action='user.deviceTemplate.create{'.cancel' if cancel else ''}'"),'1')

    def test_01_unicode_persistence_immutable_source_equipment_restart_and_creation(self):
        source,_,_,room,rack,_,_=self.rich(); original=self.capture(source)
        original_id=original['result']['templateId']; original_raw=self.detail(original_id)[2]
        oldrow=self.lab.sql(self.db,f"SELECT row_to_json(t) FROM user_device_template t WHERE id='{original_id}'")
        before=self.snapshot(); house=self.lab.sql(self.db,'SELECT revision FROM systemhaus')
        d=definition(); d['portGroups'][0]['ports'][0]['label']='😀'*500
        result=self.configure(d,name=' \u00a0'+'😀'*100+'\u00a0 ').json(); new=result['result']['templateId']
        self.assertEqual((result['result']['type'],result['result']['active'],result['result']['changed']),('create',True,True))
        self.assertNotEqual(new,original_id); self.assertEqual(result['result']['name'],'😀'*100)
        detail,read,raw=self.detail(new); self.assertEqual(read,d)
        self.assertEqual(read['portGroups'][0]['ports'][1]['gn'],2147483647)
        self.assertEqual(self.snapshot(),before); self.assertEqual(self.poll(before['revision'])['events'],[])
        self.assertEqual(self.lab.sql(self.db,'SELECT revision FROM systemhaus'),house)
        self.assertEqual(self.lab.sql(self.db,f"SELECT row_to_json(t) FROM user_device_template t WHERE id='{original_id}'"),oldrow)
        self.assertEqual(self.detail(original_id)[2],original_raw); self.once(result['requestId'])
        self.server.close(); self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend); self.admin.server=self.server
        second=Client(self.server); second.actor_id=self.admin_id; self.expect(second.login('qa-inventory-admin',self.password),200)
        self.assertEqual(self.detail(new,second)[2],raw); self.assertEqual(self.outcome(result['requestId'],second).json()['operation'],result)
        created=self.command('device.createFromPrivateTemplate',self.payload(result,rack=rack['id'])).json()
        snap=self.snapshot(); created_id=created['result']['resourceId']
        self.assertTrue(any(x['id']==created_id for x in snap['devices']))
        ports=[p for p in snap['ports'] if p['deviceId']==created_id]
        self.assertEqual(sorted(p['gn'] for p in ports),[1,1,2147483647]); self.assertTrue(any(p['label']=='😀'*500 for p in ports))
        for kind in ['dose','endDevice']:
            receipt=self.configure(definition(kind),name=kind).json(); self.assertIsNone(self.detail(receipt['result']['templateId'])[0]['template']['sizeU'])
            self.command('device.createFromPrivateTemplate',self.payload(receipt,room=room['id']))
        spec=self.expect(second.request('GET','/api/v1/openapi.json'),200).json()
        for shape in ['PrivateTemplateConfigurationCreate','PrivateTemplateConfigurationCancel']:
            self.assertFalse(spec['components']['schemas'][shape]['additionalProperties'])

    def test_02_required_recursive_closed_parser_unicode_and_domain_bounds(self):
        base=definition(); bad=[]
        for key in base:
            item=deepcopy(base); del item[key]; bad.append(item)
        for key in base['portGroups'][0]:
            item=deepcopy(base); del item['portGroups'][0][key]; bad.append(item)
        for key in base['portGroups'][0]['ports'][0]:
            item=deepcopy(base); del item['portGroups'][0]['ports'][0][key]; bad.append(item)
        for key,value in [('kind','invalid'),('sizeU',0),('sizeU',1001),('sizeU',True),('poeBudget',-1),('poeBudget',1000000),
                ('visualFamily','other'),('icon','😀'*101),('color','#nope'),('portGroups',None),('properties',{}),('id',uid())]:
            item=deepcopy(base); item[key]=value; bad.append(item)
        for key,value in [('key','g2'),('sortOrder',1),('type','rj45_poe'),('name','😀'*101),('prefix','x'*101),('ports',[]),('ports',None),('id',uid())]:
            item=deepcopy(base); item['portGroups'][0][key]=value; bad.append(item)
        for key,value in [('gn',0),('gn',2147483648),('sortOrder',1),('type','power'),('label','😀'*501),('poe',None),('poe','true'),
                ('color','#invalid'),('face','other'),('powerRole','outlet'),('status','free'),('properties',{})]:
            item=deepcopy(base); item['portGroups'][0]['ports'][0][key]=value; bad.append(item)
        item=deepcopy(base); item['portGroups'][0]['ports'][1]['gn']=1; bad.append(item)
        item=deepcopy(base); item['portGroups'][1]['ports'][0]['poe']=True; bad.append(item)
        item=definition('dose'); item['sizeU']=1; bad.append(item)
        item=definition(); item['portGroups']*=17; bad.append(item)
        item=definition(); item['portGroups'][0]['ports']*=49; bad.append(item)
        before=self.durable()
        for config in bad: self.configure(config,revision=0,status=422)
        body=json.loads(wire(base)[0])
        for change in [{'definitionVersion':2},{'type':'capture'},{'ownerId':self.admin_id},{'name':'😀'*101},{'name':'  '},{'name':'bad\x01'}]:
            self.configure(body={**body,**change},revision=0,status=422)
        for scope in ['root','definition','group','port']:
            raw=wire(base)[0]
            if scope=='root': raw=raw[:-1]+',"type":"create"}'
            elif scope=='definition': raw=raw.replace('"kind": "rackEquipment"','"kind":"rackEquipment","kind":"rackEquipment"')
            elif scope=='group': raw=raw.replace('"key": "g1"','"key":"g1","key":"g1"')
            else: raw=raw.replace('"gn": 1,','"gn":1,"gn":1,',1)
            self.expect(self.configure(body=raw,revision=0,status=422),422,'payload_invalid')
        self.assertEqual(before,self.durable())
        accepted=definition(); accepted['icon']='😀'*100; accepted['portGroups'][0]['prefix']='😀'*100
        accepted['portGroups'][0]['name']='😀'*100; accepted['portGroups'][0]['ports'][0]['label']='😀'*500
        accepted['portGroups'][0]['ports'][0]['face']='front'; accepted['portGroups'][0]['ports'][1]['face']='auto'
        self.configure(accepted,revision=0)
        empty=definition('endDevice'); empty['portGroups']=[]; empty['poeBudget']=None
        self.configure(empty)

    def test_03_route_specific_body_limit_raw_definition_canonical_limit_and_chunked(self):
        config=definition(); raw=json.dumps(config); raw=raw[:-1]+' '*(1048576-len(raw))+'}'
        self.assertEqual(len(raw.encode()),1048576)
        self.configure(body=wire(config,raw=raw)[0],revision=0)
        before=self.durable()
        self.expect(self.configure(body=wire(config,raw=raw[:-1]+' }')[0],revision=1,status=422),422,'template_definition_too_large')
        # Send only headers when testing early Content-Length refusal. Sending an unread
        # complete oversized body can reset TCP during rejection/drain, obscuring HTTP413.
        connection=http.client.HTTPConnection('127.0.0.1',self.server.port,timeout=20)
        try:
            connection.putrequest('POST',self.config_path())
            for key,value in {**self.config_headers(1),'Origin':self.server.origin,'Cookie':self.admin.cookie,
                    'X-RackClick-CSRF':self.admin.csrf,'Content-Length':str(1048576+16385)}.items(): connection.putheader(key,value)
            connection.endheaders()
            response=connection.getresponse()
            self.expect(Response(response.status,{k.lower():v for k,v in response.getheaders()},response.read()),413,'request_too_large')
        finally: connection.close()
        self.expect(self.admin.request('POST',self.path(),' '*16385,self.config_headers(1)),413,'request_too_large')
        self.expect(self.admin.request('POST',self.config_path(uid()),' '*16385,self.config_headers(1)),413,'request_too_large')
        # Chunked request has no Content-Length: Kestrel's per-request feature remains the hard bound.
        for path,size in [(self.path(),16385),(self.config_path(),1048576+16385)]:
            headers={**self.config_headers(1),'Origin':self.server.origin,'Cookie':self.admin.cookie,'X-RackClick-CSRF':self.admin.csrf}
            connection=http.client.HTTPConnection('127.0.0.1',self.server.port,timeout=20)
            try:
                connection.request('POST',path,body=iter([b' '*size]),headers=headers,encode_chunked=True)
                response=connection.getresponse(); result=Response(response.status,{k.lower():v for k,v in response.getheaders()},response.read())
                self.expect(result,413,'request_too_large')
            finally: connection.close()
        self.assertEqual(before,self.durable())
        maximum=definition(); maximum['portGroups']=[]
        for i in range(32):
            group=deepcopy(config['portGroups'][0]); group.update(key='g'+str(i+1),sortOrder=i)
            group['ports']=[{**group['ports'][0],'gn':j+1,'sortOrder':j,'label':''} for j in range(96)]
            maximum['portGroups'].append(group)
        receipt=self.configure(maximum).json(); self.assertEqual(self.detail(receipt['result']['templateId'])[0]['template']['portCount'],3072)
        # Literal Unicode fits HTTP/raw limit but escapes in canonical storage exceed 1 MiB.
        for group in maximum['portGroups']:
            for port in group['ports']: port['label']='😀'*50
        raw=json.dumps(maximum,ensure_ascii=False,separators=(',',':'))
        self.assertLess(len(raw.encode()),1048576)
        before=self.durable(); self.expect(self.configure(body=wire(maximum,raw=raw)[0],status=422),422,'template_definition_too_large'); self.assertEqual(before,self.durable())

    def test_04_exact_input_replay_fence_concurrency_rollback_and_audit(self):
        config=definition(); body,compact=wire(config); key=uid()
        receipt=self.configure(body=body,revision=0,key=key).json(); self.once(key)
        self.assertEqual(self.configure(body=body,revision=0,key=key).json(),receipt)
        self.assertEqual(self.fence(key,compact,revision=0).json()['operation'],receipt)
        other_wire=wire(config,raw=json.dumps(config,separators=(',',':')))[0]
        self.expect(self.configure(body=other_wire,revision=0,key=key,status=409),409,'request_id_reused')
        self.expect(self.configure(body=body,revision=1,key=key,status=409),409,'request_id_reused')
        self.configure(name='Other'); self.assertEqual(self.outcome(key).json()['operation'],receipt)
        cancel=uid(); terminal=self.fence(cancel,compact,revision=0).json(); self.assertEqual(terminal['state'],'cancelled')
        self.assertEqual(self.fence(cancel,compact,revision=0).json(),terminal)
        self.expect(self.configure(body=body,revision=0,key=cancel,status=409),409,'operation_cancelled'); self.once(cancel,True)
        for extra in ['definition','templateId','ownerId']:
            self.fence(uid(),{**compact,extra:{}},status=422)
        for table in ['audit_event','user_device_template_operation']:
            self.lab.sql(self.db,f"CREATE FUNCTION config_failure() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'isolated configuration rollback' USING ERRCODE='23514'; END $$; CREATE TRIGGER config_fail BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION config_failure();")
            before=self.durable()
            try: self.expect(self.configure(status=409),409,'templates_conflict'); self.assertEqual(before,self.durable())
            finally: self.lab.sql(self.db,f'DROP TRIGGER config_fail ON {table}; DROP FUNCTION config_failure();')
        revision=self.templates()['revision']; shared=uid()
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda _:self.configure(body=body,revision=revision,key=shared).json(),range(2)))
        self.assertEqual(results[0],results[1]); self.once(shared)
        revision=self.templates()['revision']; race=uid()
        with ThreadPoolExecutor(2) as pool:
            create=pool.submit(self.admin.request,'POST',self.config_path(),body,self.config_headers(revision,race))
            fence=pool.submit(self.fence,race,compact,revision)
            response,terminal=create.result(timeout=15),fence.result(timeout=15).json()
        if terminal['state']=='cancelled': self.expect(response,409,'operation_cancelled'); self.once(race,True)
        else: self.expect(response,200); self.assertEqual(terminal['operation'],response.json()); self.once(race)
        event=self.lab.sql(self.db,f"SELECT row_to_json(t) FROM audit_event t WHERE request_id='{key}'")
        journal=self.lab.sql(self.db,f"SELECT row_to_json(t) FROM user_device_template_operation t WHERE request_id='{key}'")
        for forbidden in ['definitionBase64','portGroups','inputDefinitionSha256','Etiqueta']:
            self.assertNotIn(forbidden,event); self.assertNotIn(forbidden,journal)

    def test_05_owner_scope_csrf_actor_and_reauthorization_after_wait(self):
        reader,_,_=self.add_user('config-reader',['inventory.read'],self.customer_id)
        editor,_,_=self.add_user('config-editor',['inventory.read','inventory.edit'],self.customer_id)
        no_read,_,_=self.add_user('config-no-read',['inventory.edit'],self.customer_id)
        self.configure(client=reader,revision=0,status=403); self.configure(client=no_read,revision=0,status=404)
        self.configure(customer=uid(),revision=0,status=404)
        self.configure(revision=0,status=403,headers={'X-RackClick-CSRF':'wrong'})
        self.configure(revision=0,status=409,headers={'X-RackClick-Actor':editor.actor_id})
        self.configure(revision=0,status=403,headers={'Origin':'https://foreign.invalid'})
        receipt=self.configure().json(); self.detail(receipt['result']['templateId'],editor,status=404)
        self.assertEqual(self.templates(editor)['templates'],[]); self.assertEqual(self.outcome(receipt['requestId'],editor).json()['state'],'notRecorded')
        other=self.customer('Out of scope config')['id']; self.configure(client=editor,customer=other,revision=0,status=404)
        # Invalid large-but-bounded JSON still denies missing authority before parsing it.
        self.configure(client=reader,revision=0,body='{'+' '*20000,status=403)
        for mode in ['edit','read','session']:
            actor,group,_=self.add_user('config-wait-'+mode,['inventory.read','inventory.edit'],self.customer_id)
            key=uid(); label='config_wait_'+uid().replace('-',''); lock=f'RackClick/private-device-templates/{self.house_id}/{actor.actor_id}'
            if mode=='session': self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{actor.actor_id}'")
            with ThreadPoolExecutor(2) as pool:
                holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT pg_advisory_xact_lock(hashtextextended('{lock}',0)); SELECT pg_sleep(3); COMMIT;")
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
                pending=pool.submit(actor.request,'POST',self.config_path(),wire(definition())[0],self.config_headers(0,key,actor))
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
                if mode!='session': self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability='inventory.{mode}'")
                self.expect(pending.result(timeout=15),{'edit':403,'read':404,'session':401}[mode]); holder.result(timeout=10)
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_device_template_operation WHERE request_id='{key}'"),'0')
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_device_template WHERE owner_id='{actor.actor_id}'"),'0')

    def test_06_legacy_intent_digest_and_personal_limits_unchanged(self):
        _,_,_,rack=self.hierarchy(); source,_,_=self.device('Legacy source',rack=rack['id'])
        # ASCII names avoid serializer Unicode escape policy: independently compute the exact five-field legacy digest.
        capture=self.capture_intent(source,'Legacy ASCII'); key=uid(); receipt=self.change(capture,revision=0,key=key).json()
        template=receipt['result']['templateId']
        operations=[(key,capture,0),]
        rename={'type':'rename','templateId':template,'name':'Legacy renamed'}; renamekey=uid()
        self.change(rename,revision=1,key=renamekey); operations.append((renamekey,rename,1))
        deactivate={'type':'deactivate','templateId':template}; deactivatekey=uid()
        self.change(deactivate,revision=2,key=deactivatekey); operations.append((deactivatekey,deactivate,2))
        for operation,intent,expected in operations:
            normalized={'type':intent['type'],'deviceId':intent.get('deviceId'),'name':intent.get('name'),
                'sourceRevision':intent.get('sourceRevision'),'templateId':intent.get('templateId')}
            document={'family':'privateTemplates','houseId':self.house_id,'ownerId':self.admin_id,'customerId':self.customer_id,'intent':normalized,'expected':expected}
            digest=hashlib.sha256(json.dumps(document,sort_keys=True,separators=(',',':')).encode()).hexdigest().upper()
            self.assertEqual(self.lab.sql(self.db,f"SELECT request_hash FROM user_device_template_operation WHERE request_id='{operation}'"),digest)
            self.assertEqual(self.change(intent,revision=expected,key=operation).json(),self.outcome(operation).json()['operation'])
        new=self.configure().json()['result']['templateId']
        self.lab.sql(self.db,f"INSERT INTO user_device_template(id,systemhaus_id,owner_id,name,definition_version,definition_sha256,definition_json) SELECT gen_random_uuid(),systemhaus_id,owner_id,name,definition_version,definition_sha256,definition_json FROM user_device_template CROSS JOIN generate_series(1,127) WHERE id='{new}'")
        before=self.durable(); self.expect(self.configure(status=409),409,'templates_limit'); self.assertEqual(before,self.durable())
        self.change({'type':'deactivate','templateId':new}); self.configure()
        self.lab.sql(self.db,f"UPDATE user_device_templates SET revision={MAX_REVISION} WHERE owner_id='{self.admin_id}'")
        before=self.durable(); self.expect(self.configure(revision=MAX_REVISION,status=409),409,'templates_revision_exhausted'); self.assertEqual(before,self.durable())


def main():
    # Windows console defaults may be cp1252; a Unicode fixture failure must still
    # reach tests.log/result.json instead of failing inside unittest's error printer.
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8',errors='backslashreplace')
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['dll','frontend','evidence']: parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',action='append',required=True); args=parser.parse_args()
    available=[n for n in PrivateTemplateConfigurationsPostgres.__dict__ if n.startswith('test_')]
    if set(args.case)-set(available): raise ValueError('Unknown configuration focus')
    names=[n for n in available if n in args.case]; args.dll=args.dll.resolve(); args.frontend=args.frontend.resolve()
    if not args.dll.is_file() or not args.frontend.is_dir(): raise ValueError('Explicit frozen artifacts required')
    args.evidence.mkdir(parents=True,exist_ok=False)
    files=[p for p in (WORKSPACE/'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files+=list((WORKSPACE/'development/server/database').glob('*.sql'))+[Path(__file__).resolve(),WORKSPACE/'development/catalog/rc9-catalog.json']
    files+=[WORKSPACE/'development/server/tests'/n for n in ['pg_support.py','test_postgres.py','test_inventory_postgres.py','test_inventory_changes.py','test_inventory_read_views.py','test_private_device_templates.py']]
    def sources(): return {p.relative_to(WORKSPACE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original=sources(); server=distribution(args.dll.parent); frontend=distribution(args.frontend)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),
        'serverPath':str(args.dll.parent),'frontendPath':str(args.frontend),'serverHashes':server,'frontendHashes':frontend,
        'sourceHashes':original,'selectedCases':names,'schemaVersion':9,'actualQaOpened':False,'historicalResultsReused':False}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lab=Lab('private-template-configurations'); PrivateTemplateConfigurationsPostgres.lab=lab
    PrivateTemplateConfigurationsPostgres.dll,PrivateTemplateConfigurationsPostgres.frontend=args.dll,args.frontend
    report['versions']={name:subprocess.run([str(path),'--version'],capture_output=True,text=True,check=True,creationflags=NO_WINDOW).stdout.strip()
        for name,path in [('dotnet',lab.dotnet),('postgres',lab.pg_bin/'postgres.exe')]}
    started=time.monotonic()
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(PrivateTemplateConfigurationsPostgres(n) for n in names))
        report.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started,3),labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers),sourcesUnchanged=original==sources(),
        serverUnchanged=server==distribution(args.dll.parent),frontendUnchanged=frontend==distribution(args.frontend))
    (args.evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(report[k] for k in ['successful','labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged']) else 1


if __name__=='__main__': sys.exit(main())
