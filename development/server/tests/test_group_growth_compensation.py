"""Native PG contract for the API-only inverse of pure group/port growth."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import time
import unittest

import pg_support as pg
from pg_support import Client, literal
from test_inventory_postgres import uid
from test_group_edit_evidence import GroupEditEvidence


class GroupGrowthCompensation(GroupEditEvidence):
    def grow(self, client=None, extra_group=True):
        _, _, _, rack = self.hierarchy()
        device, groups, ports = self.device('Pure growth', rack=rack['id'], groups=[{'type':'rj45_poe','count':2}])
        _, _, peer = self.device('Peer', rack=rack['id'])
        self.port_changes(device, groups[0], [ports[0]], {'label':'Keep Ü', 'watts':0.3, 'face':'rear'})
        self.connect(ports[0], peer[0], note='Do not delete', color='#123abc')
        before = self.raw_state(device)
        desired = self.desired_groups(device['id'], add=2)
        if extra_group:
            desired.append({'type':'sfp','name':'Added group','prefix':'F','retainedPortIds':[], 'addCount':2})
        made = self.command('device.editPortGroups', {'deviceId':device['id'], 'groups':desired, 'removedPortIds':[]}, client=client).json()
        return device, before, made

    def undo(self, made, **options):
        return self.command('operations.compensate', {'operationId':made['operationId']}, **options)

    def stable_rejection(self, device, made, status, code, **options):
        before = self.raw_state(device); revision = self.snapshot()['revision']
        counts = self.lab.sql(self.db, 'SELECT count(*) FROM audit_event; SELECT count(*) FROM operation')
        response = self.undo(made, status=status, **options)
        self.assertEqual(response.json()['error'], code)
        self.assertEqual(self.raw_state(device), before)
        self.assertEqual(self.snapshot()['revision'], revision)
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM audit_event; SELECT count(*) FROM operation'), counts)

    def test_pure_growth_restores_exact_rows_and_feed_has_no_fake_port_updates(self):
        device, before, made = self.grow()
        after = self.raw_state(device)
        expected_ports = sorted({p['id'] for p in after['ports']} - {p['id'] for p in before['ports']})
        expected_groups = sorted({g['id'] for g in after['groups']} - {g['id'] for g in before['groups']})
        undone = self.undo(made).json()
        self.assertEqual(undone['revision'], made['revision']+1)
        self.assertEqual(undone['result'], {'resourceId':device['id'], 'compensationKind':'groupGrowth',
                          'removedPortIds':expected_ports, 'removedGroupIds':expected_groups,
                          'compensatedOperationId':made['operationId']})
        self.assertEqual(self.raw_state(device), before)
        feed = self.expect(self.admin.request('GET',f'/api/v1/customers/{self.customer_id}/changes?afterRevision={made["revision"]}'),200).json()
        event = next(e for e in feed['events'] if e['id']==undone['operationId'])
        self.assertEqual(event['action'], 'inventory.operations.compensate')
        self.assertEqual(event['context'], {'status':'notAvailable','beforePorts':[],'afterPorts':[],
                                         'beforeConnections':[],'afterConnections':[]})

    def test_replay_committed_cancel_restart_and_second_inverse(self):
        device, before, made = self.grow(extra_group=False)
        key = uid(); revision = made['revision']
        undone = self.undo(made,key=key,revision=revision).json()
        self.assertEqual(self.undo(made,key=key,revision=revision).json(), undone)
        terminal = self.cancel('operations.compensate', {'operationId':made['operationId']}, key, revision=revision).json()
        self.assertEqual(terminal['state'],'committed')
        self.assertEqual(terminal['operation'],undone)
        self.server.close();self.server=self.lab.start_server(self.db)
        self.admin=Client(self.server);self.admin.actor_id=self.admin_id
        self.expect(self.admin.login('qa-inventory-admin',self.password),200)
        self.assertEqual(self.raw_state(device),before)
        self.assertEqual(self.operation_state(key)['operation'],undone)
        self.stable_rejection(device,made,409,'compensation_not_latest')

    def test_mixed_edit_and_incomplete_or_corrupt_evidence_fail_closed(self):
        device, _, made = self.grow()
        saved=json.loads(self.lab.sql(self.db,f'SELECT before_json FROM audit_event WHERE id={literal(made["operationId"])}'))
        for mutation in ('missing','incomplete','changed_existing_group','missing_old_port'):
            value=json.loads(json.dumps(saved));e=value['data']['groupEditEvidence']
            if mutation=='missing':del value['data']['groupEditEvidence']
            elif mutation=='incomplete':e['complete']=False
            elif mutation=='changed_existing_group':e['groups'][0]['name']='Not the prior state'
            else:e['ports'].pop()
            self.lab.sql(self.db,f'UPDATE audit_event SET before_json={literal(json.dumps(value))}::jsonb WHERE id={literal(made["operationId"])}')
            self.stable_rejection(device,made,422,'compensation_unsupported')
            self.lab.sql(self.db,f'UPDATE audit_event SET before_json={literal(json.dumps(saved))}::jsonb WHERE id={literal(made["operationId"])}')
        desired=self.desired_groups(device['id'],add=1);desired[0]['name']='Mixed rename and growth'
        mixed=self.command('device.editPortGroups',{'deviceId':device['id'],'groups':desired,'removedPortIds':[]}).json()
        self.stable_rejection(device,mixed,422,'compensation_unsupported')

    def test_current_state_and_later_revision_conflicts_preserve_rows(self):
        device, _, made=self.grow()
        added=next(p for p in self.raw_state(device)['ports'] if p['id'] in made['result']['createdIds'])
        self.lab.sql(self.db,f'UPDATE inventory_port SET label=\'Out of band\' WHERE id={literal(added["id"])}')
        self.stable_rejection(device,made,409,'compensation_state_conflict')
        self.lab.sql(self.db,f'UPDATE inventory_port SET label={literal(added["label"])} WHERE id={literal(added["id"])}')
        self.command('site.create',{'name':'Later change'})
        self.stable_rejection(device,made,409,'compensation_not_latest')

    def test_actor_client_scope_permissions_and_csrf(self):
        writer,group,_=self.add_user('growth-writer',['inventory.read','inventory.edit'],self.customer_id)
        device,_,made=self.grow(client=writer)
        other,_,_=self.add_user('growth-other',['inventory.read','inventory.edit'],self.customer_id)
        self.stable_rejection(device,made,404,'not_found',client=other)
        wrong_customer=self.customer('Other customer')['id']
        # Same actor is authorized in both customers: rejection must come from the operation's scope.
        for capability in ('inventory.read','inventory.edit'):
            self.lab.sql(self.db,f"INSERT INTO permission_grant(id,systemhaus_id,user_group_id,capability,customer_id) VALUES({literal(uid())},{literal(self.house_id)},{literal(group)},{literal(capability)},{literal(wrong_customer)})")
        self.stable_rejection(device,made,404,'not_found',customer=wrong_customer,client=writer)
        before=self.raw_state(device)
        response=writer.request('POST',f'/api/v1/customers/{self.customer_id}/commands',
            {'type':'operations.compensate','payload':{'operationId':made['operationId']}},
            {'If-Match':f'"{made["revision"]}"','Idempotency-Key':uid(),'X-RackClick-Actor':writer.actor_id,'X-RackClick-CSRF':'invalid'})
        self.expect(response,403);self.assertEqual(self.raw_state(device),before)
        self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id={literal(group)} AND capability='inventory.edit'")
        self.stable_rejection(device,made,403,'forbidden',client=writer)

    def test_audit_failure_and_concurrent_attempts_are_atomic(self):
        device,_,made=self.grow()
        self.lab.sql(self.db,"CREATE FUNCTION qa_growth_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Synthetic growth failure'; END $$; CREATE TRIGGER qa_growth_fail BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION qa_growth_fail();")
        before=self.raw_state(device);key=uid()
        try:
            self.undo(made,key=key,status=503)
            self.assertEqual(self.raw_state(device),before)
            self.assertEqual(self.snapshot()['revision'],made['revision'])
        finally:self.lab.sql(self.db,'DROP TRIGGER qa_growth_fail ON audit_event; DROP FUNCTION qa_growth_fail();')
        def attempt():
            return self.admin.request('POST',f'/api/v1/customers/{self.customer_id}/commands',
                {'type':'operations.compensate','payload':{'operationId':made['operationId']}},
                {'If-Match':f'"{made["revision"]}"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}).status
        with ThreadPoolExecutor(max_workers=2) as pool:statuses=sorted(pool.map(lambda _:attempt(),range(2)))
        self.assertEqual(statuses,[200,412])
        self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM audit_event WHERE action='inventory.operations.compensate'"),'1')

    def test_permission_revoked_while_waiting_on_device_lock(self):
        writer,group,_=self.add_user('growth-wait-writer',['inventory.read','inventory.edit'],self.customer_id)
        device,_,made=self.grow(client=writer);before=self.raw_state(device);marker='growth_'+uid().replace('-','')
        with ThreadPoolExecutor(max_workers=2) as pool:
            holder=pool.submit(self.lab.sql,self.db,f"SET application_name={literal(marker)}; BEGIN; SELECT id FROM inventory_device WHERE id={literal(device['id'])} FOR UPDATE; SELECT pg_sleep(3); COMMIT;")
            deadline=time.monotonic()+2
            while self.lab.sql(self.db,f"SELECT count(*) FROM pg_stat_activity WHERE application_name={literal(marker)} AND wait_event='PgSleep'",admin=True)!='1':
                self.assertLess(time.monotonic(),deadline);time.sleep(.02)
            pending=pool.submit(self.undo,made,client=writer,status=403)
            while self.lab.sql(self.db,f"SELECT count(*) FROM pg_stat_activity WHERE datname={literal(self.db.name)} AND usename={literal(self.db.runtime)} AND wait_event_type='Lock'",admin=True)=='0':
                self.assertLess(time.monotonic(),deadline);time.sleep(.02)
            self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id={literal(group)} AND capability='inventory.edit'")
            holder.result();self.assertEqual(pending.result().json()['error'],'forbidden')
        self.assertEqual(self.raw_state(device),before)
        self.assertEqual(self.snapshot()['revision'],made['revision'])


CASES=tuple(name for name in GroupGrowthCompensation.__dict__ if name.startswith('test_'))
def load_tests(loader,tests,pattern):
    return unittest.TestSuite(GroupGrowthCompensation(name) for name in CASES)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--cases',nargs='*',choices=CASES)
    args=parser.parse_args()
    dll=args.dll.resolve();target=args.evidence.resolve();private=(pg.WORKSPACE/'.local').resolve()
    if not dll.is_file() or not dll.is_relative_to(private) or not target.is_relative_to(private):
        raise ValueError('Private identified DLL and new private evidence directory required')
    target.mkdir(exist_ok=False);pg.protect_directory(target);pg.DEFAULT_DLL=dll
    lab=pg.Lab('c2-group-growth')
    report={'dllSha256':hashlib.sha256(dll.read_bytes()).hexdigest(),'newCluster':True,'qaTouched':False}
    try:
        with lab:
            report['postgresql']=lab.sql('postgres','SHOW server_version',admin=True)
            GroupGrowthCompensation.lab=lab
            names=args.cases or CASES
            with (target/'tests-private.log').open('w',encoding='utf-8') as log:
                result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.TestSuite(GroupGrowthCompensation(n) for n in names))
            report.update(cases=list(names),testsRun=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                          skipped=len(result.skipped),successful=result.wasSuccessful())
    finally:
        lab.close();report['labStopped']=not lab.running
        (target/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))
    return 0 if report.get('successful') and report['labStopped'] else 1


if __name__=='__main__':
    raise SystemExit(main())
