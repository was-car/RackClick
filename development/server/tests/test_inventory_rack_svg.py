"""Rack SVG: explicit frozen artifacts, fresh native PostgreSQL8 labs, no real QA."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import unittest
import uuid
import xml.etree.ElementTree as ET

from pg_support import Client, Lab, WORKSPACE, NO_WINDOW, literal
from test_postgres import EvidenceResult, Tee
from test_inventory_printable_reports import InventoryPrintableReportsPostgres
from test_inventory_read_views import distribution


def uid(): return str(uuid.uuid4())


NS='http://www.w3.org/2000/svg'
TEMPLATE='rackclick-rack-svg-v1'
ROOT_ATTRS={'lang','data-template','data-customer-id','data-rack-id','data-source-revision','data-face','viewBox','role','aria-label'}
ATTRS=ROOT_ATTRS|{'x','y','x1','y1','x2','y2','cx','cy','r','rx','width','height','fill','stroke','stroke-width',
    'stroke-dasharray','d','transform','font-family','font-size','font-weight','text-anchor','opacity','data-report-row','data-id',
    'data-visible','data-device-id','data-group-id','data-from-port-id','data-to-port-id'}
TAGS={'svg','title','desc','g','rect','circle','path','text'}


class InventoryRackSvgPostgres(InventoryPrintableReportsPostgres):
    def svg_request(self,rack,face='front',language='es'):
        return {'rackId':rack,'face':face,'language':language}

    def svg_report(self,payload,revision=None,key=None,client=None,customer=None,status=200,headers=None):
        customer=customer or self.customer_id; client=client or self.admin
        if revision is None: revision=self.snapshot(customer)['revision']
        response=self.expect(client.request('POST',f'/api/v1/customers/{customer}/reports/rack-svg',payload,
            {'If-Match':f'"{revision}"','Idempotency-Key':key or uid(),'X-RackClick-Actor':client.actor_id,**(headers or {})}),status)
        if status!=200: return response
        value=response.json(); self.assertEqual(set(value),{'kind','customerId','revision','requestId','operationId','report'})
        self.assertEqual(value['kind'],'report'); self.assertEqual(value['customerId'],customer); self.assertEqual(value['revision'],revision)
        self.assertEqual(response.headers['etag'],f'"{revision}"'); self.svg(value)
        return value

    def svg_status(self,key,client=None,customer=None,status=200):
        customer=customer or self.customer_id
        response=self.expect((client or self.admin).request('GET',f'/api/v1/customers/{customer}/reports/rack-svg/operations/{key}'),status)
        if status!=200: return response
        value=response.json(); self.assertEqual(set(value),{'state','customerId','requestId','operation'})
        self.assertEqual(value['customerId'],customer); self.assertEqual(value['requestId'],key)
        if value['operation'] is not None: self.svg(value['operation'])
        return value

    def svg(self,value):
        report=value['report']; self.assertEqual(set(report),{'reportKind','rackId','face','language','filename','contentType','encoding','templateVersion','rowCount','byteLength','sha256','contentBase64'})
        self.assertEqual(report['reportKind'],'rackSvg'); self.assertIn(report['face'],['front','rear']); self.assertIn(report['language'],['en','de','es'])
        self.assertEqual(report['contentType'],'image/svg+xml; charset=utf-8'); self.assertEqual(report['encoding'],'utf-8'); self.assertEqual(report['templateVersion'],TEMPLATE)
        self.assertEqual(report['filename'],f'rackclick-rackSvg-{value["customerId"]}-{report["rackId"]}-r{value["revision"]}-{report["face"]}-{report["language"]}.svg')
        raw=base64.b64decode(report['contentBase64'],validate=True); self.assertFalse(raw.startswith(b'\xef\xbb\xbf')); self.assertTrue(raw.startswith(b'<svg '))
        self.assertEqual(len(raw),report['byteLength']); self.assertLessEqual(len(raw),4194304); self.assertEqual(hashlib.sha256(raw).hexdigest(),report['sha256'])
        source=raw.decode('utf-8',errors='strict'); self.assertNotIn('<!',source); self.assertNotIn('<?',source)
        root=ET.fromstring(source); self.assertEqual(root.tag,'{'+NS+'}svg'); self.assertEqual(set(root.attrib),ROOT_ATTRS)
        for key,expected in [('lang',report['language']),('data-template',TEMPLATE),('data-customer-id',value['customerId']),('data-rack-id',report['rackId']),('data-source-revision',str(value['revision'])),('data-face',report['face']),('role','img')]: self.assertEqual(root.attrib[key],expected)
        self.assertRegex(root.attrib['viewBox'],r'^0 0 960 [0-9]+(?:\.[0-9]+)?$')
        self.assertLessEqual(float(root.attrib['viewBox'].split()[-1]),999964)
        marks={}; kinds={'rack','device','group','port','connection'}
        for node in root.iter():
            self.assertIn(node.tag,{'{'+NS+'}'+t for t in TAGS}); self.assertTrue(set(node.attrib)<=ATTRS)
            for key,item in node.attrib.items():
                self.assertFalse(key.lower().startswith('on')); self.assertNotIn('url(',item.lower())
                if key in ['fill','stroke']: self.assertRegex(item,r'^(?:none|#[0-9A-Fa-f]{6})$')
                if key=='font-family': self.assertEqual(item,'Arial,sans-serif')
                if key.startswith('data-') and key.endswith('-id'): self.assertEqual(str(uuid.UUID(item)),item)
            if 'data-report-row' in node.attrib:
                kind=node.attrib['data-report-row']; self.assertIn(kind,kinds); identity=node.attrib['data-id']; self.assertEqual(str(uuid.UUID(identity)),identity)
                pair=(kind,identity); self.assertNotIn(pair,marks); marks[pair]=node
        self.assertEqual(len(marks),report['rowCount']); self.assertLessEqual(len(marks),10000)
        self.assertIn(('rack',report['rackId']),marks)
        return root,marks,raw

    def fingerprint(self):
        names=self.lab.sql(self.db,"SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename NOT IN('operation','audit_event') ORDER BY tablename").splitlines()
        return {name:hashlib.sha256(self.lab.sql(self.db,f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM public.\"{name}\" t").encode()).hexdigest() for name in names}

    def test_01_faces_unicode_identities_passive_geometry(self):
        _,_,room,rack,device,groups,ports,dose,dp,cable=self.fixture()
        long_customer='W'*100; long_rack='😃'*100; long_device='👩\u200d💻'*30+'e\u0301'*5
        self.assertEqual(len(long_rack.encode('utf-16-le'))//2,200)
        self.command('rack.update',{'id':rack['id'],'name':long_rack})
        self.lab.sql(self.db,f"UPDATE customer SET name={literal(long_customer)} WHERE id='{self.customer_id}'")
        extra,eg,ep=self.device(long_device,rack=rack['id'],groups=[{'type':'rj45','count':4},{'type':'rj45','count':4}])
        ep=[p for g in eg for p in sorted((p for p in ep if p['groupId']==g['id']),key=lambda p:p['gn'])]
        self.lab.sql(self.db,f"UPDATE inventory_port_group SET prefix={literal(long_device)} WHERE id='{eg[0]['id']}'")
        internal=self.connect(ep[0],ep[4],note='Internal front literal\r\nCafé 😃',color='#A1b2C3')
        self.port_changes(extra,eg[0],[ep[1]],{'face':'rear','poe':True,'watts':17.5,'label':'Rear Café 😃','status':'faulty'})
        self.port_changes(extra,eg[1],[ep[5]],{'face':'front','status':'disabled','color':'#ABCdef'})
        power,pg,pp=self.device('PDU descriptive',rack=rack['id'],groups=[{'type':'power','count':2},{'type':'mgmt','count':1}])
        pp=[p for p in pp if p['groupId']==pg[0]['id']]
        self.port_changes(power,pg[0],[pp[0]],{'powerRole':'inlet'}); self.port_changes(power,pg[0],[pp[1]],{'powerRole':'outlet'})
        _,_,_,other=self.hierarchy('Outside'); external,_,external_ports=self.device('External rack',rack=other['id'])
        crossing=self.connect(ports[2],external_ports[0],note='External note <>& 😃')
        hostile='<img src="https://invalid.example/x" onerror="alert(1)"> Ñ 😃 & </script>'
        self.command('device.update',{'id':device['id'],'name':hostile})
        self.port_changes(device,groups[0],[ports[3]],{'label':'</text><script>text only</script>'})
        self.lab.sql(self.db,f"UPDATE inventory_device SET properties='{{\"preset\":\"server\",\"private-report-marker\":\"DO-NOT-EXPORT\"}}' WHERE id='{device['id']}'")
        before=self.fingerprint(); snapshot=self.snapshot(); own_devices={d['id'] for d in snapshot['devices'] if d['rackId']==rack['id']}
        own_groups={g['id'] for g in snapshot['portGroups'] if g['deviceId'] in own_devices}; own_ports={p['id'] for p in snapshot['ports'] if p['deviceId'] in own_devices}
        own_cables={c['id'] for c in snapshot['connections'] if c['fromPortId'] in own_ports or c['toPortId'] in own_ports}
        expected={('rack',rack['id'])}|{('device',x) for x in own_devices}|{('group',x) for x in own_groups}|{('port',x) for x in own_ports}|{('connection',x) for x in own_cables}
        for language in ['en','de','es']:
            for face in ['front','rear']:
                made=self.svg_report(self.svg_request(rack['id'],face,language)); root,marks,raw=self.svg(made)
                self.assertEqual(set(marks),expected); all_text=''.join(root.itertext()); self.assertIn(hostile,all_text); self.assertIn('Internal front literal\r\nCafé 😃',all_text)
                self.assertIn(long_customer,all_text); self.assertIn(long_rack,all_text); self.assertIn(long_device,all_text)
                abbreviated=[(node.find('{'+NS+'}title').text,node.find('{'+NS+'}title').tail) for node in root.iter('{'+NS+'}text') if node.find('{'+NS+'}title') is not None]
                self.assertTrue(any(original==long_customer and displayed.endswith('…') for original,displayed in abbreviated))
                self.assertTrue(any(original==long_device and displayed.endswith('…') for original,displayed in abbreviated))
                text_nodes=list(root.iter('{'+NS+'}text'))
                face_name={'en':{'front':'Front','rear':'Rear'},'de':{'front':'Vorderseite','rear':'Rückseite'},'es':{'front':'Frontal','rear':'Trasera'}}[language][face]
                self.assertTrue(any(node.attrib.get('x')=='620' and node.text==face_name+' · 42 U' and node.find('{'+NS+'}title') is None for node in text_nodes))
                self.assertTrue(any(node.attrib.get('x')=='820' and node.text=='1 U' and node.find('{'+NS+'}title') is None for node in text_nodes))
                if face=='front': self.assertTrue(any(original.startswith(long_device) and displayed=='👩\u200d💻…' for original,displayed in abbreviated))
                self.assertNotIn('DO-NOT-EXPORT',all_text); self.assertNotIn('Laboratorio RackClick',all_text)
                for identity in [dose['id'],dp[0]['id'],external['id'],external_ports[0]['id']]: self.assertIn(identity,all_text)
                self.assertEqual(marks[('port',ep[1]['id'])].attrib['data-visible'],'true' if face=='rear' else 'false')
                self.assertEqual(marks[('port',pp[0]['id'])].attrib['data-visible'],'true' if face=='rear' else 'false')
                self.assertEqual(marks[('connection',crossing['id'])].attrib['data-visible'],'false')
                self.assertEqual(len(list(marks[('connection',crossing['id'])].iter('{'+NS+'}path'))),0)
                self.assertEqual(len(list(marks[('connection',internal['id'])].iter('{'+NS+'}path'))),1 if face=='front' else 0)
                target=self.evidence/'artifacts'; target.mkdir(exist_ok=True); (target/f'rack-{face}-{language}.svg').write_bytes(raw)
        self.assertEqual(self.fingerprint(),before)

    def test_02_closed_contract_headers_xml_and_limits(self):
        _,_,_,rack,device,groups,ports,_,_,_=self.fixture(); valid=self.svg_request(rack['id'])
        for payload in [{},[],{**valid,'unknown':True},{k:v for k,v in valid.items() if k!='face'},
            {**valid,'rackId':None},{**valid,'rackId':1},{**valid,'rackId':uid().replace('-','')},{**valid,'rackId':str(uuid.UUID(int=0))},
            {**valid,'face':'auto'},{**valid,'face':'Front'},{**valid,'language':'ES'},{**valid,'language':None}]:
            before=self.durable(); self.expect(self.svg_report(payload,status=422),422,'request_invalid'); self.assertEqual(self.durable(),before)
        raw=json.dumps(valid).replace('"face": "front"','"face":"front","face":"rear"').encode()
        self.expect(self.svg_report(raw,status=422,headers={'Content-Type':'application/json'}),422,'request_invalid')
        for headers,status,code in [({'X-RackClick-CSRF':'bad'},403,'csrf_invalid'),({'Origin':'http://invalid.example'},403,'origin_invalid'),({'X-RackClick-Actor':''},422,'actor_invalid'),({'If-Match':''},428,'revision_required'),({'If-Match':'bad'},422,'revision_invalid')]:
            before=self.durable(); self.expect(self.svg_report(valid,status=status,headers=headers),status,code); self.assertEqual(self.durable(),before)
        foreign=self.customer('Foreign SVG')['id']; _,_,_,foreign_rack=self.hierarchy('Foreign',customer=foreign)
        for identity in [uid(),foreign_rack['id']]: self.expect(self.svg_report(self.svg_request(identity),status=404),404,'not_found')
        self.lab.sql(self.db,f"UPDATE inventory_port SET label=chr(1) WHERE id='{ports[0]['id']}'")
        before=self.durable(); self.expect(self.svg_report(valid,status=422),422,'report_text_invalid'); self.assertEqual(self.durable(),before)
        self.lab.sql(self.db,f"UPDATE inventory_port SET label='' WHERE id='{ports[0]['id']}'")
        self.lab.sql(self.db,f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order) SELECT gen_random_uuid(),'{self.house_id}','{self.customer_id}','{device['id']}','{groups[0]['id']}','rj45',g,10000+g FROM generate_series(1,10001) g")
        before=self.durable(); self.expect(self.svg_report(valid,status=422),422,'report_too_large'); self.assertEqual(self.durable(),before)
        self.lab.sql(self.db,'DELETE FROM inventory_port WHERE sort_order>=10000')
        self.lab.sql(self.db,f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label) SELECT gen_random_uuid(),'{self.house_id}','{self.customer_id}','{device['id']}','{groups[0]['id']}','rj45',g,10000+g,repeat('é',2000) FROM generate_series(1,1000) g")
        before=self.durable(); self.expect(self.svg_report(valid,status=422),422,'report_too_large'); self.assertEqual(self.durable(),before)

    def waiting_svg(self,payload,client,mutate,status,code,table='customer',identity=None):
        identity=identity or self.customer_id; revision=self.snapshot()['revision']; label='svgwait_'+uid()
        with ThreadPoolExecutor(2) as pool:
            holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT id FROM {table} WHERE id='{identity}' FOR UPDATE; SELECT pg_sleep(3); COMMIT;")
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            pending=pool.submit(self.svg_report,payload,client=client,revision=revision,status=status)
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
            mutate(); self.expect(pending.result(timeout=15),status,code); holder.result(timeout=10)

    def test_03_authorization_revocation_expiry_and_generic_guards(self):
        _,_,_,rack,_,_,_,_,_,_=self.fixture(); payload=self.svg_request(rack['id'])
        reader,_,_=self.add_user('svg-read-only',['inventory.read'],self.customer_id)
        exporter,_,_=self.add_user('svg-export-only',['reports.export'],self.customer_id)
        self.expect(self.svg_report(payload,client=reader,status=403),403,'forbidden'); self.expect(self.svg_report(payload,client=exporter,status=404),404,'not_found')
        scoped,_,_=self.add_user('svg-customer-group',['inventory.read','reports.export'],self.customer_id,customer_group=True)
        self.svg_report(payload,client=scoped)
        for cap,status,code in [('inventory.read',404,'not_found'),('reports.export',403,'forbidden')]:
            actor,group,_=self.add_user('svg-revoke-'+cap,['inventory.read','reports.export'],self.customer_id)
            self.waiting_svg(payload,actor,lambda:self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability={literal(cap)}"),status,code)
        actor,_,_=self.add_user('svg-expiry',['inventory.read','reports.export'],self.customer_id)
        self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{actor.actor_id}'")
        self.waiting_svg(payload,actor,lambda:None,401,'authentication_required',table='app_user',identity=actor.actor_id)
        self.expect(actor.login('svg-expiry',self.password),200)
        self.waiting_svg(payload,actor,lambda:self.lab.sql(self.db,f"DELETE FROM app_session WHERE user_id='{actor.actor_id}'"),401,'authentication_required')
        self.expect(actor.login('svg-expiry',self.password),200)
        self.lab.sql(self.db,"CREATE FUNCTION slow_svg() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='reports.rackSvg.generate' THEN PERFORM pg_sleep(3); END IF; RETURN NEW; END $$; CREATE TRIGGER slow_svg BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION slow_svg()")
        self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{actor.actor_id}'")
        before=self.durable(); self.expect(self.svg_report(payload,client=actor,status=401),401,'authentication_required'); self.assertEqual(self.durable(),before)
        self.lab.sql(self.db,'DROP TRIGGER slow_svg ON audit_event; DROP FUNCTION slow_svg()')
        made=self.svg_report(payload); key=made['requestId']; revision=self.snapshot()['revision']
        self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE capability='reports.export' AND user_group_id IN(SELECT group_id FROM user_group_member WHERE user_id='{self.admin_id}')")
        before=self.durable()
        for identity in [key,uid()]: self.expect(self.svg_status(identity,status=403),403,'forbidden')
        self.expect(self.svg_report(payload,key=key,revision=revision,status=403),403,'forbidden')
        path=f'/api/v1/customers/{self.customer_id}/operations/{key}'
        self.expect(self.admin.request('GET',path),404,'not_found'); self.command('site.create',{'name':'MUST NOT COMMIT'},key=key,status=404)
        headers={'If-Match':f'"{revision}"','Idempotency-Key':key,'X-RackClick-Actor':self.admin_id}
        self.expect(self.admin.request('POST',path+'/cancel',{'type':'site.create','payload':{'name':'MUST NOT COMMIT'}},headers),404,'not_found')
        house_revision=self.lab.sql(self.db,'SELECT revision FROM systemhaus')
        self.expect(self.admin.request('PUT','/api/v1/systemhaus',{'name':'MUST NOT RENAME'},{**headers,'If-Match':f'"{house_revision}"'}),404,'not_found')
        self.assertEqual(self.durable(),before)

    def test_04_replay_concurrent_canonical_and_stale(self):
        _,_,_,rack,_,_,_,_,_,_=self.fixture(); revision=self.snapshot()['revision']; key=uid(); before=self.fingerprint()
        payload=self.svg_request(rack['id']); upper={**payload,'rackId':rack['id'].upper()}
        with ThreadPoolExecutor(2) as pool:
            futures=[pool.submit(self.svg_report,p,revision=revision,key=key) for p in [payload,upper]]; results=[f.result(timeout=20) for f in futures]
        self.assertEqual(results[0],results[1]); self.assertEqual(self.fingerprint(),before)
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{key}'"),'1')
        self.command('rack.update',{'id':rack['id'],'name':'New name after historical SVG'})
        self.assertEqual(self.svg_report(payload,key=key,revision=revision),results[0]); self.assertEqual(self.svg_status(key)['operation'],results[0])
        self.expect(self.svg_report(payload,revision=revision,status=412),412,'revision_conflict')
        for changed in [{**payload,'face':'rear'},{**payload,'language':'de'}]: self.expect(self.svg_report(changed,key=key,revision=revision,status=409),409,'request_id_reused')
        self.expect(self.svg_report(payload,key=key,status=409),409,'request_id_reused')

    def test_05_rollback_audit_inventory_schema_and_openapi(self):
        _,_,_,rack,_,_,_,_,_,_=self.fixture(); payload=self.svg_request(rack['id']); migrations=self.lab.sql(self.db,'SELECT version,digest FROM schema_migration ORDER BY version')
        self.assertEqual(migrations.splitlines()[-1].split('|')[0],'8')
        for table in ['audit_event','operation']:
            predicate="NEW.action='reports.rackSvg.generate'" if table=='audit_event' else "NEW.result_json->'report'->>'templateVersion'='rackclick-rack-svg-v1'"
            self.lab.sql(self.db,f"CREATE FUNCTION fail_svg() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF {predicate} THEN RAISE EXCEPTION 'synthetic SVG rollback' USING ERRCODE='23514'; END IF; RETURN NEW; END $$; CREATE TRIGGER fail_svg BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION fail_svg()")
            before=self.durable(); key=uid(); self.expect(self.svg_report(payload,key=key,status=409),409,'report_conflict'); self.assertEqual(self.durable(),before)
            self.assertEqual(self.svg_status(key)['state'],'notRecorded'); self.lab.sql(self.db,f'DROP TRIGGER fail_svg ON {table}; DROP FUNCTION fail_svg()')
        before=self.fingerprint(); revision=self.snapshot()['revision']; made=self.svg_report(payload)
        event=json.loads(self.lab.sql(self.db,f"SELECT row_to_json(t) FROM audit_event t WHERE id='{made['operationId']}'"))
        self.assertEqual(event['action'],'reports.rackSvg.generate'); self.assertEqual(event['resource_id'],self.customer_id); self.assertIsNone(event['before_json'])
        self.assertEqual(set(event['after_json']),{'customerId','sourceRevision','rackId','face','language','rowCount','byteLength','sha256','templateVersion'})
        self.assertEqual(event['after_json']['sourceRevision'],revision); self.assertNotIn('contentBase64',json.dumps(event)); self.assertNotIn('<svg',json.dumps(event))
        self.assertEqual(self.poll(revision)['events'],[]); self.assertEqual(self.fingerprint(),before)
        self.assertEqual(self.lab.sql(self.db,'SELECT version,digest FROM schema_migration ORDER BY version'),migrations)
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_context WHERE event_id='{made['operationId']}'"),'0')
        doc=self.expect(self.admin.request('GET','/api/v1/openapi.json'),200).json(); schema=doc['components']['schemas']['InventoryRackSvgRequest']
        self.assertEqual(set(schema['required']),{'rackId','face','language'}); self.assertFalse(schema['additionalProperties'])
        self.assertEqual(len(self.expect(self.admin.request('GET','/api/v1/admin/capabilities'),200).json()['capabilities']),9)

    def test_06_csv_html_regression_and_format_families(self):
        _,_,_,rack,_,_,_,_,_,_=self.fixture(); revision=self.snapshot()['revision']; payload=self.svg_request(rack['id'])
        csv=self.generate(); html=self.printable(self.printable_request('rack',[rack['id']])); svg=self.svg_report(payload)
        self.assertEqual(self.report_status(csv['requestId'])['operation'],csv); self.assertEqual(self.printable_status(html['requestId'])['operation'],html); self.assertEqual(self.svg_status(svg['requestId'])['operation'],svg)
        for foreign in [csv,html]: self.expect(self.svg_status(foreign['requestId'],status=404),404,'not_found'); self.expect(self.svg_report(payload,key=foreign['requestId'],revision=revision,status=409),409,'request_id_reused')
        self.expect(self.report_status(svg['requestId'],status=404),404,'not_found'); self.expect(self.printable_status(svg['requestId'],status=404),404,'not_found')
        self.expect(self.generate(key=svg['requestId'],revision=revision,status=409),409,'request_id_reused'); self.expect(self.printable(key=svg['requestId'],revision=revision,status=409),409,'request_id_reused')
        generic=self.command('site.create',{'name':'Generic is not SVG'}).json()['requestId']; self.expect(self.svg_status(generic,status=404),404,'not_found')

    def test_07_restart_status_scope_reauthorization(self):
        _,_,_,rack,_,_,_,_,_,_=self.fixture(); payload=self.svg_request(rack['id']); revision=self.snapshot()['revision']; made=self.svg_report(payload); key=made['requestId']
        stranger,_,_=self.add_user('svg-other-actor',['inventory.read','reports.export'],self.customer_id)
        reader,_,_=self.add_user('svg-status-read-only',['inventory.read'],self.customer_id)
        self.assertEqual(self.svg_status(key,client=stranger)['state'],'notRecorded'); self.expect(self.svg_status(key,client=reader,status=403),403,'forbidden')
        foreign=self.customer('Other status customer')['id']; self.expect(self.svg_status(key,customer=foreign,status=404),404,'not_found')
        self.expect(self.svg_status(uid(),customer=foreign,client=stranger,status=404),404,'not_found')
        unknown=self.svg_status(uid()); self.assertEqual(unknown['state'],'notRecorded'); self.assertIsNone(unknown['operation'])
        before=self.durable(); self.svg_status(key); self.assertEqual(self.durable(),before)
        self.server.close(); self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend); self.admin.server=self.server
        fresh=Client(self.server); fresh.actor_id=self.admin_id; self.expect(fresh.login('qa-inventory-admin',self.password),200)
        self.assertEqual(self.svg_status(key,client=fresh)['operation'],made); self.assertEqual(self.svg_report(payload,revision=revision,key=key,client=fresh),made)
        self.assertEqual(self.snapshot()['revision'],revision)
        self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE capability='reports.export' AND user_group_id IN(SELECT group_id FROM user_group_member WHERE user_id='{self.admin_id}')")
        self.expect(self.svg_status(key,client=fresh,status=403),403,'forbidden')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['dll','frontend','evidence']: parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',action='append',required=True); args=parser.parse_args()
    available=[n for n in InventoryRackSvgPostgres.__dict__ if n.startswith('test_')]
    if set(args.case)-set(available) or len(args.case)!=len(set(args.case)): raise ValueError('Unknown or repeated SVG case')
    names=[n for n in available if n in args.case]; args.dll=args.dll.resolve(strict=True); args.frontend=args.frontend.resolve(strict=True)
    if not args.dll.is_file() or not (args.frontend/'index.html').is_file(): raise ValueError('Explicit frozen DLL/frontend required')
    args.evidence.mkdir(parents=True,exist_ok=False)
    files=[p for p in (WORKSPACE/'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files+=list((WORKSPACE/'development/server/database').glob('*.sql'))+[Path(__file__).resolve(),WORKSPACE/'development/catalog/rc9-catalog.json']
    files+=[WORKSPACE/'development/server/tests'/n for n in ['pg_support.py','test_postgres.py','test_inventory_changes.py','test_inventory_postgres.py','test_inventory_read_views.py','test_inventory_reports.py','test_inventory_printable_reports.py']]
    def sources(): return {p.relative_to(WORKSPACE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original=sources(); server=distribution(args.dll.parent); frontend=distribution(args.frontend)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),
        'serverPath':str(args.dll.parent),'frontendPath':str(args.frontend),'serverHashes':server,'frontendHashes':frontend,'sourceHashes':original,
        'selectedCases':names,'schemaVersion':8,'actualQaOpened':False,'buildPerformedByRunner':False,'historicalResultsReused':False}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lab=Lab('inventory-rack-svg'); InventoryRackSvgPostgres.lab=lab
    InventoryRackSvgPostgres.dll,InventoryRackSvgPostgres.frontend,InventoryRackSvgPostgres.evidence=args.dll,args.frontend,args.evidence
    report['versions']={name:subprocess.run([str(path),'--version'],capture_output=True,text=True,check=True,creationflags=NO_WINDOW).stdout.strip() for name,path in [('dotnet',lab.dotnet),('postgres',lab.pg_bin/'postgres.exe')]}
    started=time.monotonic()
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(InventoryRackSvgPostgres(n) for n in names))
        report.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),
        sourcesUnchanged=original==sources(),serverUnchanged=server==distribution(args.dll.parent),frontendUnchanged=frontend==distribution(args.frontend))
    (args.evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(report[k] for k in ['successful','labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged']) else 1


if __name__=='__main__': sys.exit(main())
