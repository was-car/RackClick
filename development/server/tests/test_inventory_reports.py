"""Bounded authorized CSV reports: frozen artifacts, fresh native PostgreSQL only."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import hashlib
import io
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


PORT_COLUMNS = ['port_id','device_id','device_name','device_kind','rack_id','rack_name','room_id','room_name',
    'site_id','site_name','building_id','building_name','group_id','group_name','type','family','gn','label','status','face','poe','watts','color','power_role','connected','connection_ids','peer_port_ids']


class InventoryReportsPostgres(InventoryReadViewsPostgres):
    def request(self, kind='ports', query='', status='all', family='all', rack=None):
        return {'reportKind':kind,'query':query,'status':status,'family':family,'rackId':rack}

    def generate(self, payload=None, revision=None, key=None, client=None, customer=None, status=200, headers=None):
        customer=customer or self.customer_id; client=client or self.admin
        if revision is None: revision=self.snapshot(customer)['revision']
        response=self.expect(client.request('POST',f'/api/v1/customers/{customer}/reports/csv',payload if payload is not None else self.request(),
            {'If-Match':f'"{revision}"','Idempotency-Key':key or uid(),'X-RackClick-Actor':client.actor_id,**(headers or {})}),status)
        if status!=200: return response
        value=response.json(); self.assertEqual(set(value),{'kind','customerId','revision','requestId','operationId','report'})
        self.assertEqual(value['kind'],'report'); self.assertEqual(value['customerId'],customer); self.assertEqual(value['revision'],revision)
        self.assertEqual(response.headers['etag'],f'"{revision}"')
        self.csv(value)
        return value

    def report_status(self,key,client=None,customer=None,status=200):
        customer=customer or self.customer_id
        response=self.expect((client or self.admin).request('GET',f'/api/v1/customers/{customer}/reports/operations/{key}'),status)
        if status!=200: return response
        value=response.json(); self.assertEqual(set(value),{'state','customerId','requestId','operation'})
        self.assertEqual(value['customerId'],customer); self.assertEqual(value['requestId'],key)
        return value

    def csv(self,result):
        report=result['report']
        self.assertEqual(set(report),{'reportKind','query','status','family','rackId','filename','contentType','encoding','csvValueEncoding','rowCount','byteLength','sha256','contentBase64'})
        self.assertEqual(report['contentType'],'text/csv; charset=utf-8'); self.assertEqual(report['encoding'],'utf-8-bom')
        self.assertEqual(report['csvValueEncoding'],'spreadsheet-safe-apostrophe-v1')
        self.assertEqual(report['filename'],f'rackclick-{report["reportKind"]}-{result["customerId"]}-r{result["revision"]}.csv')
        raw=base64.b64decode(report['contentBase64'],validate=True)
        self.assertTrue(raw.startswith(b'\xef\xbb\xbf')); self.assertTrue(raw.endswith(b'\r\n')); self.assertLessEqual(len(raw),4194304)
        self.assertEqual(len(raw),report['byteLength']); self.assertEqual(hashlib.sha256(raw).hexdigest(),report['sha256'])
        rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'),newline=''),strict=True))
        headers=['customer_id','source_revision']+(PORT_COLUMNS if report['reportKind']=='ports' else
            ['connection_id','note','color','patch','cross_rack']+['from_'+c for c in PORT_COLUMNS]+['to_'+c for c in PORT_COLUMNS])
        self.assertEqual(rows[0],headers); self.assertEqual(len(rows)-1,report['rowCount']); self.assertLessEqual(report['rowCount'],10000)
        self.assertTrue(all(len(row)==len(headers) for row in rows))
        def decode(value): return value[1:] if value.startswith("'") else value
        return [dict(zip(headers,[decode(c) for c in row])) for row in rows[1:]],rows,raw

    def stable_inventory(self):
        return {k:v for k,v in self.tables().items() if k not in ['operation','audit_event']}

    def test_csv_ports_connections_unicode_formulas_exact_bytes(self):
        _,_,room,rack,device,groups,ports,dose,dp,cable=self.fixture()
        forms=['=SUM(1,2)',"'literal",'+1','-2','@x','normal Ñ 😃','=X','quote"comma,']
        extra,eg,ep=self.device('Same gn groups',rack=rack['id'],groups=[{'type':'rj45','count':4},{'type':'rj45','count':4}])
        for index,port in enumerate(ep):
            group=next(g for g in eg if g['id']==port['groupId'])
            self.port_changes(extra,group,[port],{'label':forms[index]})
        self.port_changes(device,groups[0],[ports[2]],{'poe':True,'watts':17.5,'face':'rear'})
        note='\t=HYPERLINK("x,y")\r\nÑ 😃 "quoted"'
        self.command('connections.update',{'connectionId':cable['id'],'note':note})
        before=self.stable_inventory(); source=self.snapshot()
        made=self.generate(); rows,rawrows,raw=self.csv(made); byid={r['port_id']:r for r in rows}
        self.assertEqual([r['port_id'] for r in rows],sorted(p['id'] for p in source['ports']))
        for index,port in enumerate(ep): self.assertEqual(byid[port['id']]['label'],forms[index])
        self.assertEqual(byid[ports[2]['id']]['watts'],'17.5'); self.assertEqual(byid[ports[2]['id']]['face'],'rear')
        self.assertEqual(byid[dp[0]['id']]['rack_id'],''); self.assertEqual(byid[dp[0]['id']]['room_id'],room['id'])
        self.assertEqual(len({byid[p['id']]['group_id'] for p in ep if p['gn']==1}),2)
        label_index=rawrows[0].index('label'); port_index=rawrows[0].index('port_id'); encoded={row[port_index]:row for row in rawrows[1:]}
        for index,port in enumerate(ep):
            original=forms[index]; dangerous=original.startswith("'") or original.lstrip().startswith(('=','+','-','@'))
            self.assertEqual(encoded[port['id']][label_index],("'" if dangerous else '')+original)
        cables=self.generate(self.request('connections')); cable_rows,_,cable_bytes=self.csv(cables)
        self.assertEqual(cable_rows[0]['connection_id'],cable['id']); self.assertEqual(cable_rows[0]['note'],note)
        self.assertEqual(cable_rows[0]['from_port_id'],ports[0]['id']); self.assertEqual(cable_rows[0]['to_port_id'],dp[0]['id'])
        self.assertEqual(cable_rows[0]['cross_rack'],''); self.assertIn(b'""x,y""',cable_bytes)
        self.assertNotIn(b'properties',raw); self.assertEqual(self.stable_inventory(),before)

    def test_filters_racks_closed_inputs_and_limits(self):
        _,_,_,rack,device,groups,ports,_,_,_=self.fixture()
        self.assertEqual(self.generate(self.request(rack=rack['id']))['report']['rowCount'],4)
        self.assertEqual(self.generate(self.request('connections',rack=rack['id']))['report']['rowCount'],1)
        self.assertEqual(self.generate(self.request(query='CAFE\u0301',rack=rack['id']))['report']['rowCount'],4)
        self.assertEqual(self.generate(self.request(status='reserved',family='rj45'))['report']['rowCount'],1)
        self.assertEqual(self.generate(self.request(query="' OR 1=1 --"))['report']['rowCount'],0)
        other=self.customer('Other report customer')['id']; _,_,_,foreign=self.hierarchy('Foreign',customer=other)
        for payload in [self.request(rack=uid()),self.request(rack=foreign['id'])]: self.expect(self.generate(payload,status=404),404,'not_found')
        invalid=[{},self.request(status='occupied'),self.request(family='rj45_poe'),self.request(query='x'*201),self.request('search'),
            self.request('connections',status='free'),self.request(rack=str(uuid.UUID(int=0))),{**self.request(),'limit':10},{k:v for k,v in self.request().items() if k!='rackId'}]
        for payload in invalid:
            before=self.durable(); self.expect(self.generate(payload,status=422),422,'request_invalid'); self.assertEqual(self.durable(),before)
        before=self.durable()
        self.expect(self.generate(status=403,headers={'X-RackClick-CSRF':'bad'}),403,'csrf_invalid'); self.assertEqual(self.durable(),before)
        self.expect(self.generate(status=422,headers={'X-RackClick-Actor':''}),422,'actor_invalid')
        self.expect(self.generate(status=428,headers={'If-Match':''}),428,'revision_required')
        raw=b'{"reportKind":"ports","query":"","query":"x","status":"all","family":"all","rackId":null}'
        self.expect(self.generate(payload=raw,status=422,headers={'Content-Type':'application/json'}),422,'request_invalid')
        # Direct synthetic legacy rows exercise both hard limits without 10000 API setup commands.
        self.lab.sql(self.db,f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order) SELECT gen_random_uuid(),'{self.house_id}','{self.customer_id}','{device['id']}','{groups[0]['id']}','rj45',g,10000+g FROM generate_series(1,10001) g")
        before=self.durable(); self.expect(self.generate(status=422),422,'report_too_large'); self.assertEqual(self.durable(),before)
        self.lab.sql(self.db,"DELETE FROM inventory_port WHERE sort_order>=10000")
        self.lab.sql(self.db,f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label) SELECT gen_random_uuid(),'{self.house_id}','{self.customer_id}','{device['id']}','{groups[0]['id']}','rj45',g,10000+g,repeat('é',2000) FROM generate_series(1,2200) g")
        before=self.durable(); self.expect(self.generate(status=422),422,'report_too_large'); self.assertEqual(self.durable(),before)

    def test_grant_catalog_capture_audit_and_last_admin(self):
        self.fixture(); catalog=self.expect(self.admin.request('GET','/api/v1/admin/capabilities'),200).json()
        self.assertEqual(len(catalog['capabilities']),9); self.assertIn('reports.export',catalog['capabilities'])
        reader,group,_=self.add_user('explicit-report-reader',['inventory.read'],self.customer_id)
        self.expect(self.generate(client=reader,status=403),403,'forbidden')
        payload={'grantId':uid(),'capability':'reports.export','scope':'customer','targetId':self.customer_id,'assigned':True}
        house_revision=self.lab.sql(self.db,'SELECT revision FROM systemhaus')
        grant=self.expect(self.admin.request('POST',f'/api/v1/admin/user-groups/{group}/grants',payload,
            {'If-Match':f'"{house_revision}"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),200).json()
        grant_event=self.lab.sql(self.db,f"SELECT id FROM audit_event WHERE request_id='{grant['requestId']}'")
        detail=self.expect(self.admin.request('GET',f'/api/v1/admin/audit/{grant_event}/administrative-detail'),200).json()
        self.assertIn('reports.export',json.dumps(detail)); self.assertEqual(detail['detail']['status'],'available')
        before=self.stable_inventory(); revision=self.snapshot()['revision']; made=self.generate(client=reader)
        self.assertEqual(self.stable_inventory(),before); self.assertEqual(self.snapshot()['revision'],revision)
        event=json.loads(self.lab.sql(self.db,f"SELECT row_to_json(a) FROM audit_event a WHERE id='{made['operationId']}'"))
        self.assertEqual(event['action'],'reports.csv.generate'); self.assertEqual(event['resource_id'],self.customer_id)
        self.assertIsNone(event['before_json']); self.assertEqual(event['after_json']['sourceRevision'],revision)
        self.assertNotIn('revision',event['after_json']); self.assertNotIn('contentBase64',json.dumps(event)); self.assertNotIn('properties',json.dumps(event))
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_context WHERE event_id='{made['operationId']}'"),'0')
        self.assertEqual(self.poll(revision)['events'],[])
        admin_group=self.lab.sql(self.db,f"SELECT group_id FROM user_group_member WHERE user_id='{self.admin_id}'")
        security=self.lab.sql(self.db,f"SELECT id FROM permission_grant WHERE user_group_id='{admin_group}' AND capability='security.manage'")
        remove={'grantId':security,'capability':'security.manage','scope':'systemhaus','targetId':None,'assigned':False}
        before=self.durable(); house_revision=self.lab.sql(self.db,'SELECT revision FROM systemhaus')
        self.expect(self.admin.request('POST',f'/api/v1/admin/user-groups/{admin_group}/grants',remove,
            {'If-Match':f'"{house_revision}"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),409,'last_admin_required'); self.assertEqual(self.durable(),before)
        document=self.expect(self.admin.request('GET','/api/v1/openapi.json'),200).json()
        self.assertIn('reports.export',document['components']['schemas']['SetGrant']['properties']['capability']['enum'])
        self.assertFalse(document['components']['schemas']['InventoryCsvRequest']['additionalProperties'])

    def waiting_report(self,client,mutate,status,code,table='customer',identity=None):
        identity=identity or self.customer_id; revision=self.snapshot()['revision']; label='reportwait_'+uid()
        with ThreadPoolExecutor(2) as pool:
            holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT id FROM {table} WHERE id='{identity}' FOR UPDATE; SELECT pg_sleep(3); COMMIT;")
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            pending=pool.submit(self.generate,client=client,revision=revision,status=status)
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
            mutate(); self.expect(pending.result(timeout=15),status,code); holder.result(timeout=10)

    def test_revocation_expiry_and_generic_bypass(self):
        self.fixture()
        for cap,status,code in [('inventory.read',404,'not_found'),('reports.export',403,'forbidden')]:
            reader,group,_=self.add_user('revoke-'+cap,['inventory.read','reports.export'],self.customer_id)
            self.waiting_report(reader,lambda:self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability={literal(cap)}"),status,code)
        reader,_,_=self.add_user('expire-report',['inventory.read','reports.export'],self.customer_id)
        self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{reader.actor_id}'")
        self.waiting_report(reader,lambda:None,401,'authentication_required',table='app_user',identity=reader.actor_id)
        self.expect(reader.login('expire-report',self.password),200)
        self.waiting_report(reader,lambda:self.lab.sql(self.db,f"DELETE FROM app_session WHERE user_id='{reader.actor_id}'"),401,'authentication_required')
        self.expect(reader.login('expire-report',self.password),200)
        self.lab.sql(self.db,"CREATE FUNCTION slow_reports() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='reports.csv.generate' THEN PERFORM pg_sleep(3); END IF; RETURN NEW; END $$; CREATE TRIGGER slow_reports BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION slow_reports()")
        self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{reader.actor_id}'")
        before=self.durable(); self.expect(self.generate(client=reader,status=401),401,'authentication_required'); self.assertEqual(self.durable(),before)
        self.lab.sql(self.db,'DROP TRIGGER slow_reports ON audit_event; DROP FUNCTION slow_reports()')
        made=self.generate(); key=made['requestId']; report_grant=self.lab.sql(self.db,f"SELECT id FROM permission_grant WHERE capability='reports.export' AND user_group_id IN (SELECT group_id FROM user_group_member WHERE user_id='{self.admin_id}')")
        self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE id='{report_grant}'")
        self.expect(self.report_status(key,status=403),403,'forbidden'); self.expect(self.report_status(uid(),status=403),403,'forbidden')
        before=self.durable(); path=f'/api/v1/customers/{self.customer_id}/operations/{key}'
        self.expect(self.admin.request('GET',path),404,'not_found')
        self.command('site.create',{'name':'MUST NOT COMMIT'},key=key,status=404)
        revision=self.snapshot()['revision']; headers={'If-Match':f'"{revision}"','Idempotency-Key':key,'X-RackClick-Actor':self.admin_id}
        self.expect(self.admin.request('POST',path+'/cancel',{'type':'site.create','payload':{'name':'MUST NOT COMMIT'}},headers),404,'not_found')
        hr=self.lab.sql(self.db,'SELECT revision FROM systemhaus')
        self.expect(self.admin.request('PUT','/api/v1/systemhaus',{'name':'MUST NOT RENAME'},{**headers,'If-Match':f'"{hr}"'}),404,'not_found')
        adminstatus=self.expect(self.admin.request('GET',f'/api/v1/admin/users/operations/{key}'),200).json()
        self.assertEqual(adminstatus['state'],'notRecorded'); self.assertIsNone(adminstatus['operation'])
        self.assertEqual(self.durable(),before)

    def test_replay_concurrent_keys_changed_revision_new_stale(self):
        self.fixture(); revision=self.snapshot()['revision']; key=uid(); before=self.stable_inventory()
        with ThreadPoolExecutor(2) as pool:
            results=[f.result(timeout=20) for f in [pool.submit(self.generate,key=key,revision=revision) for _ in range(2)]]
        self.assertEqual(results[0],results[1]); self.assertEqual(self.stable_inventory(),before)
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{key}'"),'1')
        self.command('site.create',{'name':'New inventory revision'})
        self.assertEqual(self.generate(key=key,revision=revision),results[0])
        self.expect(self.generate(revision=revision,status=412),412,'revision_conflict')
        self.expect(self.generate(self.request(query='different'),key=key,revision=revision,status=409),409,'request_id_reused')
        self.expect(self.generate(key=key,status=409),409,'request_id_reused')
        self.assertEqual(self.report_status(key)['operation'],results[0])

    def test_atomic_rollback_audit_and_operation_failure(self):
        self.fixture()
        for table in ['audit_event','operation']:
            predicate="NEW.action='reports.csv.generate'" if table=='audit_event' else "NEW.result_json->>'kind'='report'"
            self.lab.sql(self.db,f"CREATE FUNCTION fail_reports() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF {predicate} THEN RAISE EXCEPTION 'synthetic report rollback' USING ERRCODE='23514'; END IF; RETURN NEW; END $$; CREATE TRIGGER fail_reports BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION fail_reports()")
            before=self.durable(); tables=self.tables(); key=uid()
            self.expect(self.generate(key=key,status=409),409,'report_conflict'); self.assertEqual(self.durable(),before); self.assertEqual(self.tables(),tables)
            self.assertEqual(self.report_status(key)['state'],'notRecorded')
            self.lab.sql(self.db,f'DROP TRIGGER fail_reports ON {table}; DROP FUNCTION fail_reports()')
        self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM audit_event WHERE action='reports.csv.generate'"),'0')

    def test_reread_restart_status_scope_no_artifact_leak(self):
        self.fixture(); made=self.generate(self.request('connections')); revision=self.snapshot()['revision']
        stranger,_,_=self.add_user('another-report-actor',['inventory.read','reports.export'],self.customer_id)
        plain,_,_=self.add_user('read-only-no-export',['inventory.read'],self.customer_id)
        self.assertEqual(self.report_status(made['requestId'],client=stranger)['state'],'notRecorded')
        self.expect(self.report_status(made['requestId'],client=plain,status=403),403,'forbidden')
        foreign=self.customer('Another report customer')['id']
        self.expect(self.report_status(made['requestId'],customer=foreign,status=404),404,'not_found')
        self.expect(self.report_status(uid(),customer=foreign,client=stranger,status=404),404,'not_found')
        state=self.report_status(uid()); self.assertEqual(state['state'],'notRecorded'); self.assertIsNone(state['operation'])
        before=self.tables(); self.assertEqual(self.report_status(made['requestId'])['operation'],made); self.assertEqual(self.tables(),before)
        self.server.close(); self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend); self.admin.server=self.server
        self.assertEqual(self.report_status(made['requestId'])['operation'],made); self.assertEqual(self.generate(self.request('connections'),revision=revision,key=made['requestId']),made)
        self.assertEqual(self.snapshot()['revision'],revision)


def distribution(path):
    return {p.relative_to(path).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob('*')) if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['dll','frontend','evidence']: parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',action='append',required=True); args=parser.parse_args()
    available=[n for n in InventoryReportsPostgres.__dict__ if n.startswith('test_')]
    if set(args.case)-set(available): raise ValueError('Unknown report case')
    names=[n for n in available if n in args.case]
    args.dll=args.dll.resolve(); args.frontend=args.frontend.resolve(); args.evidence.mkdir(parents=True,exist_ok=False)
    files=[p for p in (WORKSPACE/'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files+=list((WORKSPACE/'development/server/database').glob('*.sql'))
    files+=[Path(__file__).resolve()]+[WORKSPACE/'development/server/tests'/n for n in ['pg_support.py','test_postgres.py','test_inventory_changes.py','test_inventory_postgres.py','test_inventory_read_views.py','test_admin_grants.py']]
    def sources(): return {p.relative_to(WORKSPACE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original=sources(); server=distribution(args.dll.parent); frontend=distribution(args.frontend)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),
        'serverPath':str(args.dll.parent),'frontendPath':str(args.frontend),'serverHashes':server,'frontendHashes':frontend,
        'sourceHashes':original,'selectedCases':names,'schemaVersion':7,'actualQaOpened':False}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lab=Lab('inventory-reports'); InventoryReportsPostgres.lab=lab
    report['versions']={name:subprocess.run([str(path),'--version'],capture_output=True,text=True,check=True,creationflags=NO_WINDOW).stdout.strip()
        for name,path in [('dotnet',lab.dotnet),('postgres',lab.pg_bin/'postgres.exe')]}
    InventoryReportsPostgres.dll,InventoryReportsPostgres.frontend=args.dll,args.frontend
    started=time.monotonic()
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(InventoryReportsPostgres(n) for n in names))
        report.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started,3),labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers),sourcesUnchanged=original==sources(),
        serverUnchanged=server==distribution(args.dll.parent),frontendUnchanged=frontend==distribution(args.frontend))
    (args.evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(report[k] for k in ['successful','labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged']) else 1


if __name__=='__main__': sys.exit(main())
