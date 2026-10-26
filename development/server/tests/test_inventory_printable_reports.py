"""Seven focused HTML-report/CSV regression cases; explicit frozen artifacts, new native PostgreSQL labs only."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest
import uuid

from pg_support import Lab, WORKSPACE, NO_WINDOW, literal
from test_postgres import EvidenceResult, Tee
from test_inventory_reports import InventoryReportsPostgres, distribution


def uid(): return str(uuid.uuid4())


CSP = "default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; img-src 'none'; font-src 'none'; connect-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'"


class PassiveHtml(HTMLParser):
    def __init__(self, value):
        super().__init__(convert_charrefs=True)
        self.tags=[]; self.rows=[]; self.text=[]; self.current=None; self.declarations=[]
        self.feed(value); self.close()

    def handle_decl(self, value): self.declarations.append(value.lower())

    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs); self.tags.append((tag,attrs))
        if 'data-report-row' in attrs:
            self.current={'tag':tag,'kind':attrs['data-report-row'],'id':attrs.get('data-id'),'text':[],'cells':0}
            self.rows.append(self.current)
        if tag=='td' and self.current is not None: self.current['cells']+=1

    def handle_endtag(self, tag):
        if self.current is not None and self.current['tag']==tag: self.current=None

    def handle_data(self, value):
        self.text.append(value)
        if self.current is not None: self.current['text'].append(value)


class InventoryPrintableReportsPostgres(InventoryReportsPostgres):
    evidence=None

    def printable_request(self, kind='client', racks=None, language='es'):
        return {'reportKind':kind,'language':language,'rackIds':racks or []}

    def printable(self, payload=None, revision=None, key=None, client=None, customer=None, status=200, headers=None):
        customer=customer or self.customer_id; client=client or self.admin
        if revision is None: revision=self.snapshot(customer)['revision']
        response=self.expect(client.request('POST',f'/api/v1/customers/{customer}/reports/printable',
            self.printable_request() if payload is None else payload,
            {'If-Match':f'"{revision}"','Idempotency-Key':key or uid(),'X-RackClick-Actor':client.actor_id,**(headers or {})}),status)
        if status!=200: return response
        value=response.json(); self.assertEqual(set(value),{'kind','customerId','revision','requestId','operationId','report'})
        self.assertEqual(value['kind'],'report'); self.assertEqual(value['customerId'],customer); self.assertEqual(value['revision'],revision)
        self.assertEqual(response.headers['etag'],f'"{revision}"'); self.html(value)
        return value

    def printable_status(self, key, client=None, customer=None, status=200):
        customer=customer or self.customer_id
        response=self.expect((client or self.admin).request('GET',f'/api/v1/customers/{customer}/reports/printable/operations/{key}'),status)
        if status!=200: return response
        value=response.json(); self.assertEqual(set(value),{'state','customerId','requestId','operation'})
        self.assertEqual(value['customerId'],customer); self.assertEqual(value['requestId'],key)
        if value['operation'] is not None: self.html(value['operation'])
        return value

    def html(self, value):
        report=value['report']; self.assertEqual(set(report),{'reportKind','language','rackIds','filename','contentType','encoding','templateVersion','rowCount','byteLength','sha256','contentBase64'})
        self.assertEqual(report['contentType'],'text/html; charset=utf-8'); self.assertEqual(report['encoding'],'utf-8')
        self.assertEqual(report['templateVersion'],'rackclick-print-v1'); self.assertEqual(report['rackIds'],sorted(report['rackIds']))
        self.assertEqual(report['filename'],f'rackclick-{report["reportKind"]}-{value["customerId"]}-r{value["revision"]}-{report["language"]}.html')
        raw=base64.b64decode(report['contentBase64'],validate=True); self.assertFalse(raw.startswith(b'\xef\xbb\xbf'))
        self.assertEqual(len(raw),report['byteLength']); self.assertLessEqual(len(raw),4194304)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),report['sha256'])
        parsed=PassiveHtml(raw.decode('utf-8',errors='strict')); self.assertEqual(parsed.declarations,['doctype html'])
        self.assertEqual(len(parsed.rows),report['rowCount']); self.assertLessEqual(len(parsed.rows),10000)
        tags=parsed.tags; self.assertEqual([a['lang'] for t,a in tags if t=='html'],[report['language']])
        self.assertEqual([a['data-report-kind'] for t,a in tags if t=='body'],[report['reportKind']])
        self.assertEqual([a['content'] for t,a in tags if t=='meta' and a.get('name')=='rackclick-template'],['rackclick-print-v1'])
        self.assertEqual([a['content'] for t,a in tags if t=='meta' and a.get('http-equiv','').lower()=='content-security-policy'],[CSP])
        allowed={'html','head','meta','title','style','body','main','header','b','h1','p','section','div','span','br','footer','small','h2','table','thead','tr','th','tbody','td'}
        self.assertTrue(all(t in allowed for t,a in tags)); self.assertEqual(sum(t=='style' for t,a in tags),1)
        self.assertFalse(any(k.lower().startswith('on') or k.lower() in ['src','href','action','formaction','srcdoc','style'] for t,a in tags for k in a))
        self.assertNotIn('url(',raw.decode('utf-8').lower()); self.assertNotIn('@import',raw.decode('utf-8').lower())
        for row in parsed.rows: self.assertEqual(str(uuid.UUID(row['id'])),row['id'])
        return parsed,raw

    def test_printable_three_kinds_unicode_context_csp_identity(self):
        _,_,room,rack,device,groups,ports,dose,dp,cable=self.fixture()
        _,_,_,other=self.hierarchy('External'); external,_,ep=self.device('External rack endpoint',rack=other['id'])
        cross=self.connect(ports[2],ep[0],note='Cross rack literal')
        final,_,fp=self.device('Room-only final',room=room['id'],kind='endDevice')
        self.connect(dp[1],fp[0],note='Room-only cable, no internal Dose circuit')
        hostile='<img src=https://invalid.example/x onerror=alert(1)> Ñ 😃 & " </script>'
        self.command('device.update',{'id':device['id'],'name':hostile})
        self.port_changes(device,groups[0],[ports[3]],{'label':'</td><script>window.X=1</script> Café','face':'rear'})
        self.lab.sql(self.db,f"UPDATE inventory_device SET properties='{{\"private-report-marker\":\"DO-NOT-EXPORT\"}}' WHERE id='{device['id']}'")
        before=self.stable_inventory(); source=self.snapshot()
        for language in ['en','de','es']:
            for kind,racks in [('rack',[rack['id']]),('client',[]),('rackLabels',[other['id'],rack['id']])]:
                made=self.printable(self.printable_request(kind,racks,language)); parsed,raw=self.html(made)
                text=''.join(parsed.text); rows={(r['kind'],r['id']):''.join(r['text']) for r in parsed.rows}
                self.assertNotIn('DO-NOT-EXPORT',text); self.assertNotIn('Laboratorio RackClick',text)
                self.assertIn(self.customer_id,text); self.assertIn('Synthetic changes customer',text)
                if kind!='rackLabels':
                    self.assertIn(hostile,text); self.assertIn('</td><script>window.X=1</script> Café',text)
                    source_ports={p['id']:p for p in source['ports']}
                    for row in [r for r in parsed.rows if r['kind']=='port']:
                        self.assertEqual(row['cells'],4)
                        for identity in ['id','deviceId','groupId']: self.assertIn(source_ports[row['id']][identity],''.join(row['text']))
                    self.assertIn(('connection',cross['id']),rows); self.assertIn(external['id'],rows[('connection',cross['id'])])
                    self.assertIn(ep[0]['id'],rows[('connection',cross['id'])]); self.assertIn(dp[0]['id'],rows[('connection',cable['id'])])
                    self.assertIn(room['name'],rows[('connection',cable['id'])]); self.assertIn('rack: —',rows[('connection',cable['id'])])
                if kind=='rack':
                    self.assertNotIn(('device',final['id']),rows); self.assertNotIn(('device',external['id']),rows)
                    expected=1+1+len(groups)+len(ports)+2
                    self.assertEqual(made['report']['rowCount'],expected)
                elif kind=='client':
                    self.assertIn(('device',final['id']),rows); self.assertIn(('device',dose['id']),rows)
                    self.assertEqual(made['report']['rowCount'],sum(len(source[k]) for k in ['sites','buildings','rooms','racks','devices','portGroups','ports','connections']))
                else:
                    self.assertEqual(set(rows),{('rack-label',rack['id']),('rack-label',other['id'])})
                    self.assertIn(room['name'],rows[('rack-label',rack['id'])]); self.assertIn('336px',text)
                target=self.evidence/'artifacts'; target.mkdir(exist_ok=True)
                (target/f'{kind}-{language}.html').write_bytes(raw)
        self.assertEqual(self.stable_inventory(),before)

    def test_printable_inputs_ids_and_limits(self):
        _,_,room,rack,device,groups,ports,_,_,_=self.fixture(); valid=self.printable_request('rack',[rack['id']])
        empty=self.customer('Empty or room-only customer')['id']
        self.assertEqual(self.printable(customer=empty)['report']['rowCount'],0)
        site=self.create('site',{'name':'No-rack site'},'sites',empty)
        building=self.create('building',{'name':'No-rack building','siteId':site['id']},'buildings',empty)
        only_room=self.create('room',{'name':'No-rack room','buildingId':building['id']},'rooms',empty)
        final,_,_=self.device('No-rack final',room=only_room['id'],kind='endDevice',customer=empty)
        parsed,_=self.html(self.printable(customer=empty))
        self.assertIn(('device',final['id']),{(r['kind'],r['id']) for r in parsed.rows})
        self.assertNotIn('rack',{r['kind'] for r in parsed.rows})
        invalid=[{},[],{**valid,'unknown':True},{k:v for k,v in valid.items() if k!='language'},
            {**valid,'reportKind':'portLabels'},{**valid,'language':'EN'},{**valid,'rackIds':None},{**valid,'rackIds':rack['id']},
            {**valid,'rackIds':[0]},{**valid,'rackIds':['bad']},{**valid,'rackIds':[str(uuid.UUID(int=0))]},
            self.printable_request('rack',[]),self.printable_request('client',[rack['id']]),self.printable_request('rackLabels',[]),
            self.printable_request('rackLabels',[rack['id'],rack['id'].upper()]),self.printable_request('rackLabels',[uid() for _ in range(65)])]
        for payload in invalid:
            before=self.durable(); self.expect(self.printable(payload,status=422),422,'request_invalid'); self.assertEqual(self.durable(),before)
        raw=b'{"reportKind":"client","language":"en","language":"es","rackIds":[]}'
        self.expect(self.printable(raw,status=422,headers={'Content-Type':'application/json'}),422,'request_invalid')
        for headers,status,code in [({'X-RackClick-CSRF':'bad'},403,'csrf_invalid'),({'X-RackClick-Actor':''},422,'actor_invalid'),({'If-Match':''},428,'revision_required'),({'If-Match':'bad'},422,'revision_invalid')]:
            before=self.durable(); self.expect(self.printable(valid,status=status,headers=headers),status,code); self.assertEqual(self.durable(),before)
        foreign=self.customer('Foreign printable customer')['id']; _,_,_,foreign_rack=self.hierarchy('Foreign',customer=foreign)
        for identity in [uid(),foreign_rack['id']]: self.expect(self.printable(self.printable_request('rack',[identity]),status=404),404,'not_found')
        self.lab.sql(self.db,f"INSERT INTO inventory_rack(id,systemhaus_id,customer_id,room_id,name,size_u) SELECT gen_random_uuid(),'{self.house_id}','{self.customer_id}','{room['id']}','Limit rack '||g,42 FROM generate_series(1,19) g")
        self.printable()  # Exactly twenty racks is permitted, with no truncation.
        self.lab.sql(self.db,f"INSERT INTO inventory_rack(id,systemhaus_id,customer_id,room_id,name,size_u) VALUES(gen_random_uuid(),'{self.house_id}','{self.customer_id}','{room['id']}','Rack twenty-one',42)")
        before=self.durable(); self.expect(self.printable(status=422),422,'report_too_large'); self.assertEqual(self.durable(),before)
        self.lab.sql(self.db,f"INSERT INTO inventory_rack(id,systemhaus_id,customer_id,room_id,name,size_u) SELECT gen_random_uuid(),'{self.house_id}','{self.customer_id}','{room['id']}','Label rack '||g,42 FROM generate_series(1,43) g")
        ids=sorted(r['id'] for r in self.snapshot()['racks']); self.assertEqual(len(ids),64)
        self.assertEqual(self.printable(self.printable_request('rackLabels',list(reversed(ids))))['report']['rowCount'],64)
        self.lab.sql(self.db,f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order) SELECT gen_random_uuid(),'{self.house_id}','{self.customer_id}','{device['id']}','{groups[0]['id']}','rj45',g,10000+g FROM generate_series(1,10001) g")
        before=self.durable(); self.expect(self.printable(valid,status=422),422,'report_too_large'); self.assertEqual(self.durable(),before)
        self.lab.sql(self.db,"DELETE FROM inventory_port WHERE sort_order>=10000")
        self.lab.sql(self.db,f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label) SELECT gen_random_uuid(),'{self.house_id}','{self.customer_id}','{device['id']}','{groups[0]['id']}','rj45',g,10000+g,repeat('é',2000) FROM generate_series(1,600) g")
        before=self.durable(); self.expect(self.printable(valid,status=422),422,'report_too_large'); self.assertEqual(self.durable(),before)

    def waiting_printable(self,client,mutate,status,code,table='customer',identity=None):
        identity=identity or self.customer_id; revision=self.snapshot()['revision']; label='printwait_'+uid()
        with ThreadPoolExecutor(2) as pool:
            holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT id FROM {table} WHERE id='{identity}' FOR UPDATE; SELECT pg_sleep(3); COMMIT;")
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            pending=pool.submit(self.printable,client=client,revision=revision,status=status)
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
            mutate(); self.expect(pending.result(timeout=15),status,code); holder.result(timeout=10)

    def test_printable_authorization_revocation_expiry_generic_guards(self):
        self.fixture()
        reader,_,_=self.add_user('print-read-only',['inventory.read'],self.customer_id)
        exporter,_,_=self.add_user('print-export-only',['reports.export'],self.customer_id)
        self.expect(self.printable(client=reader,status=403),403,'forbidden'); self.expect(self.printable(client=exporter,status=404),404,'not_found')
        scoped,_,_=self.add_user('print-scoped',['inventory.read','reports.export'],self.customer_id,customer_group=True)
        self.printable(client=scoped)  # No systemhaus.read or security.manage is required.
        for cap,status,code in [('inventory.read',404,'not_found'),('reports.export',403,'forbidden')]:
            actor,group,_=self.add_user('print-revoke-'+cap,['inventory.read','reports.export'],self.customer_id)
            self.waiting_printable(actor,lambda:self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability={literal(cap)}"),status,code)
        actor,_,_=self.add_user('print-expiry',['inventory.read','reports.export'],self.customer_id)
        self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{actor.actor_id}'")
        self.waiting_printable(actor,lambda:None,401,'authentication_required',table='app_user',identity=actor.actor_id)
        self.expect(actor.login('print-expiry',self.password),200)
        self.waiting_printable(actor,lambda:self.lab.sql(self.db,f"DELETE FROM app_session WHERE user_id='{actor.actor_id}'"),401,'authentication_required')
        self.expect(actor.login('print-expiry',self.password),200)
        self.lab.sql(self.db,"CREATE FUNCTION slow_printable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='reports.printable.generate' THEN PERFORM pg_sleep(3); END IF; RETURN NEW; END $$; CREATE TRIGGER slow_printable BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION slow_printable()")
        self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{actor.actor_id}'")
        before=self.durable(); self.expect(self.printable(client=actor,status=401),401,'authentication_required'); self.assertEqual(self.durable(),before)
        self.lab.sql(self.db,'DROP TRIGGER slow_printable ON audit_event; DROP FUNCTION slow_printable()')
        made=self.printable(); key=made['requestId']; revision=self.snapshot()['revision']
        self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE capability='reports.export' AND user_group_id IN(SELECT group_id FROM user_group_member WHERE user_id='{self.admin_id}')")
        before=self.durable()
        for k in [key,uid()]: self.expect(self.printable_status(k,status=403),403,'forbidden')
        self.expect(self.printable(revision=revision,key=key,status=403),403,'forbidden')
        path=f'/api/v1/customers/{self.customer_id}/operations/{key}'
        self.expect(self.admin.request('GET',path),404,'not_found'); self.command('site.create',{'name':'MUST NOT COMMIT'},key=key,status=404)
        headers={'If-Match':f'"{revision}"','Idempotency-Key':key,'X-RackClick-Actor':self.admin_id}
        self.expect(self.admin.request('POST',path+'/cancel',{'type':'site.create','payload':{'name':'MUST NOT COMMIT'}},headers),404,'not_found')
        house_revision=self.lab.sql(self.db,'SELECT revision FROM systemhaus')
        self.expect(self.admin.request('PUT','/api/v1/systemhaus',{'name':'MUST NOT RENAME'},{**headers,'If-Match':f'"{house_revision}"'}),404,'not_found')
        admin_status=self.expect(self.admin.request('GET',f'/api/v1/admin/users/operations/{key}'),200).json()
        self.assertEqual(admin_status['state'],'notRecorded'); self.assertIsNone(admin_status['operation']); self.assertEqual(self.durable(),before)

    def test_printable_replay_concurrent_canonical_and_stale(self):
        _,_,_,rack,_,_,_,_,_,_=self.fixture(); _,_,_,other=self.hierarchy('Canonical')
        revision=self.snapshot()['revision']; key=uid(); before=self.stable_inventory()
        payload=self.printable_request('rackLabels',[other['id'].upper(),rack['id']])
        canonical=self.printable_request('rackLabels',sorted([other['id'],rack['id']]))
        with ThreadPoolExecutor(2) as pool:
            futures=[pool.submit(self.printable,p,revision=revision,key=key) for p in [payload,canonical]]
            results=[f.result(timeout=20) for f in futures]
        self.assertEqual(results[0],results[1]); self.assertEqual(self.stable_inventory(),before)
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{key}'"),'1')
        self.command('rack.update',{'id':rack['id'],'name':'Name changed after report'})
        self.assertEqual(self.printable(canonical,key=key,revision=revision),results[0])
        self.expect(self.printable(canonical,revision=revision,status=412),412,'revision_conflict')
        self.expect(self.printable({**canonical,'language':'de'},key=key,revision=revision,status=409),409,'request_id_reused')
        self.expect(self.printable(canonical,key=key,status=409),409,'request_id_reused')
        self.assertEqual(self.printable_status(key)['operation'],results[0])

    def test_printable_atomic_rollback_audit_schema_unchanged(self):
        self.fixture(); migrations=self.lab.sql(self.db,'SELECT version,digest FROM schema_migration ORDER BY version')
        self.assertEqual(migrations.splitlines()[-1].split('|')[0],'7')
        for table in ['audit_event','operation']:
            predicate="NEW.action='reports.printable.generate'" if table=='audit_event' else "NEW.result_json->'report'->>'templateVersion'='rackclick-print-v1'"
            self.lab.sql(self.db,f"CREATE FUNCTION fail_printable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF {predicate} THEN RAISE EXCEPTION 'synthetic printable rollback' USING ERRCODE='23514'; END IF; RETURN NEW; END $$; CREATE TRIGGER fail_printable BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION fail_printable()")
            before=self.durable(); tables=self.tables(); key=uid()
            self.expect(self.printable(key=key,status=409),409,'report_conflict'); self.assertEqual(self.durable(),before); self.assertEqual(self.tables(),tables)
            self.assertEqual(self.printable_status(key)['state'],'notRecorded')
            self.lab.sql(self.db,f'DROP TRIGGER fail_printable ON {table}; DROP FUNCTION fail_printable()')
        before=self.stable_inventory(); revision=self.snapshot()['revision']; made=self.printable()
        event=json.loads(self.lab.sql(self.db,f"SELECT row_to_json(a) FROM audit_event a WHERE id='{made['operationId']}'"))
        self.assertEqual(event['action'],'reports.printable.generate'); self.assertEqual(event['resource_id'],self.customer_id); self.assertIsNone(event['before_json'])
        self.assertEqual(set(event['after_json']),{'customerId','sourceRevision','reportKind','language','rackIds','rowCount','byteLength','sha256','templateVersion'})
        self.assertEqual(event['after_json']['sourceRevision'],revision); self.assertNotIn('contentBase64',json.dumps(event)); self.assertNotIn('<html',json.dumps(event))
        self.assertEqual(self.poll(revision)['events'],[]); self.assertEqual(self.stable_inventory(),before)
        self.assertEqual(self.lab.sql(self.db,'SELECT version,digest FROM schema_migration ORDER BY version'),migrations)
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_context WHERE event_id='{made['operationId']}'"),'0')
        document=self.expect(self.admin.request('GET','/api/v1/openapi.json'),200).json()
        schema=document['components']['schemas']['InventoryPrintableRequest']; self.assertEqual(set(schema['required']),{'reportKind','language','rackIds'}); self.assertFalse(schema['additionalProperties'])
        self.assertEqual(len(self.expect(self.admin.request('GET','/api/v1/admin/capabilities'),200).json()['capabilities']),9)

    def test_csv_regression_and_format_families(self):
        super().test_csv_ports_connections_unicode_formulas_exact_bytes()
        revision=self.snapshot()['revision']; csv=self.generate(); html=self.printable()
        self.assertEqual(self.report_status(csv['requestId'])['operation'],csv); self.assertEqual(self.printable_status(html['requestId'])['operation'],html)
        self.expect(self.report_status(html['requestId'],status=404),404,'not_found')
        self.expect(self.printable_status(csv['requestId'],status=404),404,'not_found')
        self.expect(self.generate(key=html['requestId'],revision=revision,status=409),409,'request_id_reused')
        self.expect(self.printable(key=csv['requestId'],revision=revision,status=409),409,'request_id_reused')
        mutation=self.command('site.create',{'name':'Generic operation is not a report'})
        self.expect(self.printable_status(mutation.json()['requestId'],status=404),404,'not_found')

    def test_printable_restart_status_scope(self):
        _,_,_,rack,_,_,_,_,_,_=self.fixture(); payload=self.printable_request('rack',[rack['id']])
        revision=self.snapshot()['revision']; made=self.printable(payload); key=made['requestId']
        stranger,_,_=self.add_user('print-other-actor',['inventory.read','reports.export'],self.customer_id)
        plain,_,_=self.add_user('print-status-read-only',['inventory.read'],self.customer_id)
        self.assertEqual(self.printable_status(key,client=stranger)['state'],'notRecorded')
        self.expect(self.printable_status(key,client=plain,status=403),403,'forbidden')
        foreign=self.customer('Other status customer')['id']; self.expect(self.printable_status(key,customer=foreign,status=404),404,'not_found')
        self.expect(self.printable_status(uid(),customer=foreign,client=stranger,status=404),404,'not_found')
        state=self.printable_status(uid()); self.assertEqual(state['state'],'notRecorded'); self.assertIsNone(state['operation'])
        before=self.tables(); self.assertEqual(self.printable_status(key)['operation'],made); self.assertEqual(self.tables(),before)
        self.server.close(); self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend); self.admin.server=self.server
        self.assertEqual(self.printable_status(key)['operation'],made); self.assertEqual(self.printable(payload,revision=revision,key=key),made)
        self.assertEqual(self.snapshot()['revision'],revision)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['dll','frontend','evidence']: parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',action='append',required=True); args=parser.parse_args()
    available=[n for n in InventoryPrintableReportsPostgres.__dict__ if n.startswith('test_')]
    if set(args.case)-set(available) or len(args.case)!=len(set(args.case)): raise ValueError('Unknown or repeated printable case')
    names=[n for n in available if n in args.case]
    args.dll=args.dll.resolve(strict=True); args.frontend=args.frontend.resolve(strict=True)
    if not args.dll.is_file() or not (args.frontend/'index.html').is_file(): raise ValueError('Explicit frozen DLL/frontend required')
    args.evidence.mkdir(parents=True,exist_ok=False)
    files=[p for p in (WORKSPACE/'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files+=list((WORKSPACE/'development/server/database').glob('*.sql'))
    files+=[Path(__file__).resolve()]+[WORKSPACE/'development/server/tests'/n for n in ['pg_support.py','test_postgres.py','test_inventory_changes.py','test_inventory_postgres.py','test_inventory_read_views.py','test_inventory_reports.py']]
    def sources(): return {p.relative_to(WORKSPACE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original=sources(); server=distribution(args.dll.parent); frontend=distribution(args.frontend)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),
        'serverPath':str(args.dll.parent),'frontendPath':str(args.frontend),'serverHashes':server,'frontendHashes':frontend,
        'sourceHashes':original,'selectedCases':names,'schemaVersion':7,'actualQaOpened':False,'buildPerformedByRunner':False}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lab=Lab('inventory-printable-reports'); InventoryPrintableReportsPostgres.lab=lab
    report['versions']={name:subprocess.run([str(path),'--version'],capture_output=True,text=True,check=True,creationflags=NO_WINDOW).stdout.strip()
        for name,path in [('dotnet',lab.dotnet),('postgres',lab.pg_bin/'postgres.exe')]}
    InventoryPrintableReportsPostgres.dll,InventoryPrintableReportsPostgres.frontend=args.dll,args.frontend
    InventoryPrintableReportsPostgres.evidence=args.evidence
    started=time.monotonic()
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(InventoryPrintableReportsPostgres(n) for n in names))
        report.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started,3),labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers),sourcesUnchanged=original==sources(),
        serverUnchanged=server==distribution(args.dll.parent),frontendUnchanged=frontend==distribution(args.frontend))
    (args.evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(report[k] for k in ['successful','labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged']) else 1


if __name__=='__main__': sys.exit(main())
