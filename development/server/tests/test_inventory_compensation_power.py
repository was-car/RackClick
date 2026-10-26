"""Three PoE compensation focuses and two affected regressions; fresh Windows PostgreSQL only."""
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

from pg_support import Client, Lab, WORKSPACE, NO_WINDOW, literal
from test_postgres import EvidenceResult, Tee
from test_inventory_compensation import CompensationPostgres, distribution, uid


class PowerCompensationPostgres(CompensationPostgres):
    def power_fixture(self, client=None):
        _,_,_,rack=self.hierarchy()
        device,groups,ports=self.device('PoE exact inversion',rack=rack['id'],groups=[
            {'type':'rj45','count':4,'name':'Selected group'},
            {'type':'rj45','count':1,'name':'Duplicate gn other group'},
            {'type':'power','count':2,'name':'Unrelated AC'}])
        group=next(g for g in groups if g['name']=='Selected group')
        chosen=sorted([p for p in ports if p['groupId']==group['id']],key=lambda p:p['sortOrder'])
        other=next(p for p in ports if p['groupId']!=group['id'] and p['type']=='rj45')
        self.connect(chosen[0],other,note='Connection must stay exact')
        # Populated legacy fixtures permitted by existing SQL/RC9; no new normalization command.
        for port,kind,poe,watts in zip(chosen,['rj45','rj45_poe','rj45_poe','rj45'],[True,False,True,False],['NULL','0','0.1','90']):
            self.lab.sql(self.db,f"UPDATE inventory_port SET type='{kind}',poe={'true' if poe else 'false'},watts={watts} WHERE id='{port['id']}'")
        before=self.snapshot(); tables=self.inventory_tables()
        made=self.port_changes(device,group,chosen,{'poe':True,'watts':0.3,'label':'Unified Δ','status':'reserved',
            'color':'#aAbBcC','face':'rear'},client=client).json()
        return device,group,chosen,before,tables,made

    def audit(self, made):
        return json.loads(self.lab.sql(self.db,f"SELECT jsonb_build_array(before_json,after_json) FROM audit_event WHERE id='{made['operationId']}'"))

    def replace_audit(self, made, before, after):
        self.lab.sql(self.db,f"UPDATE audit_event SET before_json={literal(json.dumps(before))}::jsonb,after_json={literal(json.dumps(after))}::jsonb WHERE id='{made['operationId']}'")

    def test_01_heterogeneous_null_zero_legacy_normalization_and_restart(self):
        device,group,ports,before,tables,made=self.power_fixture()
        result=self.undo(made).json(); restored=self.snapshot()
        self.assertEqual(result['revision'],made['revision']+1); self.assertEqual(restored['ports'],before['ports'])
        self.assertEqual(self.inventory_tables(),tables)
        expected=[('rj45',True,None),('rj45_poe',False,0),('rj45_poe',True,0.1),('rj45',False,90)]
        byid={p['id']:p for p in restored['ports']}
        self.assertEqual([(byid[p['id']]['type'],byid[p['id']]['poe'],byid[p['id']]['watts']) for p in ports],expected)
        self.assertEqual(self.lab.sql(self.db,f"SELECT watts::text FROM inventory_port WHERE id='{ports[2]['id']}'"),'0.1')
        # Alias normalization alone is real, despite boolean equality; invert literal original type.
        for port,poe in [(ports[0],True),(ports[1],False)]:
            old=self.snapshot()['ports']; original=self.port_changes(device,group,[port],{'poe':poe}).json()
            pair=self.audit(original); a,b=pair[0]['data'][0],pair[1]['data'][0]
            self.assertEqual(a['poe'],b['poe']); self.assertNotEqual(a['type'],b['type'])
            self.assertEqual({k for k in a if a[k]!=b[k]},{'type'})
            self.undo(original); self.assertEqual(self.snapshot()['ports'],old)
        # Without poe in changes, a legacy alias is untouched and remains invertible.
        for changes in [{'watts':None},{'watts':0},{'watts':90}]:
            old=self.snapshot()['ports']; original=self.port_changes(device,group,ports[:2],changes).json()
            self.assertTrue(any(a['watts']!=b['watts'] for a,b in zip(*[w['data'] for w in self.audit(original)])))
            self.undo(original); self.assertEqual(self.snapshot()['ports'],old)
        # Watts remain a stored nullable field on other families too; no PoE/circuit is invented.
        ac_group=next(g for g in self.snapshot()['portGroups'] if g['deviceId']==device['id'] and g['type']=='power')
        ac=next(p for p in self.snapshot()['ports'] if p['groupId']==ac_group['id']); old=self.snapshot()['ports']
        original=self.port_changes(device,ac_group,[ac],{'watts':0.1}).json(); self.undo(original)
        self.assertEqual(self.snapshot()['ports'],old)
        after=self.snapshot(); self.server.close(); self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend)
        fresh=Client(self.server); fresh.actor_id=self.admin_id; self.expect(fresh.login('qa-inventory-admin',self.password),200)
        self.admin.server=self.server; self.assertEqual(self.snapshot(client=fresh),after)
        self.assertEqual(self.operation_state(result['requestId'],client=fresh)['operation'],result)

    def test_02_scope_locks_csrf_conflicts_noop_corrupt_alias_and_limits(self):
        device,group,ports,_,_,made=self.power_fixture(); expected_audit=self.audit(made)
        reader,_,_=self.add_user('power-undo-reader',['inventory.read'],self.customer_id)
        other,_,_=self.add_user('power-undo-other',['inventory.read','inventory.edit'],self.customer_id)
        self.stable_rejection(made,403,'forbidden',client=reader); self.stable_rejection(made,404,'not_found',client=other)
        self.stable_rejection(made,412,'revision_conflict',revision=made['revision']-1)
        headers={'If-Match':f'"{made["revision"]}"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}
        body={'type':'operations.compensate','payload':{'operationId':made['operationId']}}
        for change,status in [({'X-RackClick-CSRF':'invalid'},403),({'Origin':'https://foreign.invalid'},403),({'X-RackClick-Actor':other.actor_id},409)]:
            before=self.durable(); self.expect(self.admin.request('POST',f'/api/v1/customers/{self.customer_id}/commands',body,{**headers,**change}),status)
            self.assertEqual(self.durable(),before)
        # Corrupt authoritative evidence, not a client-supplied inverse. Every case fails before updates.
        # Row1 changed poe false→true: the wrong after alias remains impossible for UpdatePorts.
        # Row0 had poe=true already; removing its type diff could describe a valid unrelated edit.
        mutations=[('after','type','rj45',1),('before','connector_family','sfp',0),('before','type','sfp',0),
            ('before','properties',{'forbidden':True},0),('before','power_role','outlet',0),('before','group_id',uid(),0),
            ('before','poe',None,0),('before','watts',-0.1,0),('before','watts',90.1,0),('before','watts','0',0)]
        for side,column,value,index in mutations:
            saved=json.loads(json.dumps(expected_audit)); saved[0 if side=='before' else 1]['data'][index][column]=value
            self.replace_audit(made,*saved); self.stable_rejection(made,422,'compensation_unsupported')
            self.replace_audit(made,*expected_audit)
        rows=self.inventory_tables()['inventory_port']
        self.lab.sql(self.db,f"UPDATE inventory_port SET poe=false WHERE id='{ports[0]['id']}'")
        self.stable_rejection(made,409,'compensation_state_conflict')
        self.lab.sql(self.db,f"UPDATE inventory_port SET poe=true WHERE id='{ports[0]['id']}'")
        self.assertEqual(self.inventory_tables()['inventory_port'],rows)
        no_op=self.port_changes(device,group,ports,{'poe':True,'watts':0.3}).json()
        self.stable_rejection(no_op,422,'compensation_unsupported'); self.stable_rejection(made,409,'compensation_not_latest')
        for capability,status,code in [('inventory.edit',403,'forbidden'),('inventory.read',404,'not_found')]:
            actor,grant,_=self.add_user('power-undo-revoke-'+capability,['inventory.read','inventory.edit'],self.customer_id)
            changes={'poe':False,'watts':0.1} if capability=='inventory.edit' else {'poe':True,'watts':0.2}
            own=self.port_changes(device,group,ports,changes,client=actor).json(); before=self.snapshot()
            evidence=self.audit(own); self.assertNotEqual(evidence[0]['data'],evidence[1]['data'])
            self.waiting(actor,own,'customer',self.customer_id,
                lambda:self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{grant}' AND capability={literal(capability)}"),status,code)
            self.assertEqual(self.snapshot(),before)
        # Revalidate wall-clock session expiry after the writes/audit, not only entry.
        actor,_,_=self.add_user('power-undo-expiry',['inventory.read','inventory.edit'],self.customer_id)
        own=self.port_changes(device,group,ports,{'poe':True,'watts':0.3},client=actor).json()
        self.lab.sql(self.db,"CREATE FUNCTION slow_power_compensation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='inventory.operations.compensate' THEN PERFORM pg_sleep(3); END IF; RETURN NEW; END $$; CREATE TRIGGER slow_power_compensation BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION slow_power_compensation();")
        self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{actor.actor_id}'")
        before=self.durable(); self.expect(self.undo(own,client=actor,status=401),401,'authentication_required'); self.assertEqual(self.durable(),before)

    def test_03_replay_cancel_race_atomic_rollback_and_audit_feed(self):
        device,group,ports,before,tables,made=self.power_fixture(); payload={'operationId':made['operationId']}; revision=made['revision']
        cancelkey=uid(); self.assertEqual(self.cancel('operations.compensate',payload,cancelkey,revision).json()['state'],'cancelled')
        self.stable_rejection(made,409,'operation_cancelled',key=cancelkey,revision=revision)
        for table,condition in [('audit_event',"IF NEW.action='inventory.operations.compensate' THEN RAISE EXCEPTION 'power undo fixture' USING ERRCODE='23514'; END IF;"),
            ('operation',"IF NEW.result_json->'result' ? 'compensatedOperationId' THEN RAISE EXCEPTION 'power undo journal fixture' USING ERRCODE='23514'; END IF;")]:
            self.lab.sql(self.db,f"CREATE FUNCTION fail_power_compensation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN {condition} RETURN NEW; END $$; CREATE TRIGGER fail_power_compensation BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION fail_power_compensation();")
            self.stable_rejection(made,409,'inventory_conflict')
            self.lab.sql(self.db,f'DROP TRIGGER fail_power_compensation ON {table}; DROP FUNCTION fail_power_compensation();')
        key=uid()
        with ThreadPoolExecutor(2) as pool:
            values=list(pool.map(lambda _:self.undo(made,key=key,revision=revision).json(),range(2)))
        committed=values[0]; self.assertEqual(values[0],values[1]); self.assertEqual(committed['revision'],revision+1)
        self.assertEqual(self.snapshot()['ports'],before['ports']); self.assertEqual(self.inventory_tables(),tables)
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM operation WHERE request_id='{key}'"),'1')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{key}'"),'1')
        self.assertEqual(self.cancel('operations.compensate',payload,key,revision).json()['operation'],committed)
        reader,_,_=self.add_user('power-undo-feed-reader',['inventory.read'],self.customer_id)
        feed=self.poll(revision,client=reader); self.assertEqual(len(feed['events']),1)
        event=feed['events'][0]; self.assertEqual(event['action'],'inventory.operations.compensate')
        self.assertEqual(event['actor']['id'],self.admin_id); self.assertEqual(event['context']['status'],'captured')
        aftertypes={p['id']:p['type'] for p in event['context']['afterPorts']}
        beforebyid={p['id']:p for p in before['ports']}
        self.assertEqual(aftertypes,{p['id']:beforebyid[p['id']]['type'] for p in ports})
        self.assertNotIn('Unified Δ',json.dumps(feed,ensure_ascii=False)); self.assertNotIn('properties',json.dumps(feed))
        audit=self.audit(committed); self.assertEqual(audit[0]['revision'],revision); self.assertEqual(audit[1]['revision'],revision+1)
        expected={p['id']:p for p in self.audit(made)[0]['data']}
        self.assertEqual({p['id']:p for p in audit[1]['data']},expected)
        self.command('site.create',{'name':'Commit after inverse'})
        durable=self.durable(); self.assertEqual(self.undo(made,key=key,revision=revision).json(),committed); self.assertEqual(self.durable(),durable)
        self.assertEqual(self.operation_state(key)['operation'],committed)
        self.stable_rejection(made,409,'compensation_not_latest')
        self.command('operations.compensate',{'operationId':uid()},revision=revision,key=key,status=409)
        # A different source latest again: cancellation and commit serialize on one original key.
        source=self.port_changes(device,group,ports,{'poe':True,'watts':0}).json(); rev=source['revision']; race=uid(); body={'operationId':source['operationId']}
        with ThreadPoolExecutor(2) as pool:
            apply=pool.submit(self.admin.request,'POST',f'/api/v1/customers/{self.customer_id}/commands',{'type':'operations.compensate','payload':body},
                {'If-Match':f'"{rev}"','Idempotency-Key':race,'X-RackClick-Actor':self.admin_id})
            cancel=pool.submit(self.cancel,'operations.compensate',body,race,rev)
            a,c=apply.result(timeout=15),cancel.result(timeout=15).json()
        if c['state']=='cancelled': self.expect(a,409,'operation_cancelled')
        else: self.expect(a,200); self.assertEqual(c['operation'],a.json())
        # Different keys on one revision never both apply.
        source=self.port_changes(device,group,ports,{'poe':False,'watts':90}).json(); rev=source['revision']
        with ThreadPoolExecutor(2) as pool:
            replies=list(pool.map(lambda _:self.admin.request('POST',f'/api/v1/customers/{self.customer_id}/commands',
                {'type':'operations.compensate','payload':{'operationId':source['operationId']}},
                {'If-Match':f'"{rev}"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),range(2)))
        self.assertEqual(sorted(r.status for r in replies),[200,412])

    def test_regression_four_fields_context(self):
        CompensationPostgres.test_compensation_heterogeneous_persistence_context_openapi(self)

    def test_regression_updated_unsupported_expectations(self):
        CompensationPostgres.test_compensation_invalid_unsupported_foreign_and_noop(self)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['dll','frontend','evidence']: parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',action='append',required=True); args=parser.parse_args()
    available=[n for n in PowerCompensationPostgres.__dict__ if n.startswith('test_')]
    if set(args.case)-set(available): raise ValueError('Unknown PoE compensation focus')
    names=[n for n in available if n in args.case]; args.dll=args.dll.resolve(); args.frontend=args.frontend.resolve()
    if not args.dll.is_file() or not args.frontend.is_dir(): raise ValueError('Explicit frozen artifacts required')
    args.evidence.mkdir(parents=True,exist_ok=False)
    files=[p for p in (WORKSPACE/'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files+=list((WORKSPACE/'development/server/database').glob('*.sql'))+[Path(__file__).resolve()]
    files+=[WORKSPACE/'development/server/tests'/n for n in ['pg_support.py','test_postgres.py','test_inventory_postgres.py','test_inventory_changes.py','test_inventory_compensation.py']]
    def sources(): return {p.relative_to(WORKSPACE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original=sources(); server=distribution(args.dll.parent); frontend=distribution(args.frontend)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),
        'serverPath':str(args.dll.parent),'frontendPath':str(args.frontend),'serverHashes':server,'frontendHashes':frontend,
        'sourceHashes':original,'selectedCases':names,'schemaVersion':9,'actualQaOpened':False,'historicalResultsReused':False}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lab=Lab('inventory-compensation-power'); PowerCompensationPostgres.lab=lab
    PowerCompensationPostgres.dll,PowerCompensationPostgres.frontend=args.dll,args.frontend
    report['versions']={name:subprocess.run([str(path),'--version'],capture_output=True,text=True,check=True,creationflags=NO_WINDOW).stdout.strip()
        for name,path in [('dotnet',lab.dotnet),('postgres',lab.pg_bin/'postgres.exe')]}
    started=time.monotonic()
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(PowerCompensationPostgres(n) for n in names))
        report.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started,3),labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers),sourcesUnchanged=original==sources(),
        serverUnchanged=server==distribution(args.dll.parent),frontendUnchanged=frontend==distribution(args.frontend))
    (args.evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(report[k] for k in ['successful','labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged']) else 1


if __name__=='__main__': sys.exit(main())
