"""Native PostgreSQL checks for the API-only inverse of pure group reduction."""
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
from test_group_growth_compensation import GroupGrowthCompensation


class GroupReductionCompensation(GroupGrowthCompensation):
    def reduce(self, client=None, cables=True, remove_group=True):
        _,_,_,rack=self.hierarchy()
        device,groups,ports=self.device('Pure reduction',rack=rack['id'],groups=[{'type':'rj45_poe','count':3},{'type':'rj45','count':1}])
        peer,peer_groups,peer_ports=self.device('Remote endpoint',rack=rack['id'])
        first=sorted((p for p in ports if p['groupId']==groups[0]['id']),key=lambda p:p['sortOrder'])
        last=next(p for p in ports if p['groupId']==groups[1]['id'])
        self.port_changes(device,groups[0],[first[-1]],{'label':'Puerto Ü <svg>','watts':0.3,'face':'rear','properties':{'nested':{'original':True}}})
        self.port_changes(device,groups[1],[last],{'label':'Zero','watts':0,'color':'#a1b2c3','properties':{'keep':'原始'}})
        if cables:
            self.connect(first[-1],peer_ports[0],note='Removed Ü cable',color='#123abc',patch='tested',properties={'original':{'x':True}})
            self.connect(last,peer_ports[1],note='Second removed cable')
            self.connect(first[0],peer_ports[2],note='Keep this cable')
        before=self.raw_state(device);removed=[first[-1]['id']]+([last['id']] if remove_group else [])
        desired=[g for g in self.desired_groups(device['id'],removed=removed) if not remove_group or g['id']!=groups[1]['id']]
        payload={'deviceId':device['id'],'groups':desired,'removedPortIds':removed}
        payload['confirmationToken']=self.preview('device.editPortGroups',payload,client=client)['confirmationToken']
        made=self.command('device.editPortGroups',payload,client=client).json()
        self.remote=(peer,peer_groups,peer_ports)
        return device,before,made

    def test_restores_exact_ids_rows_cables_dates_and_unavailable_feed_context(self):
        device,before,made=self.reduce();after=self.raw_state(device)
        undone=self.undo(made).json()
        self.assertEqual(undone['result'],{'resourceId':device['id'],'compensationKind':'groupReduction',
            'restoredPortIds':sorted({p['id'] for p in before['ports']}-{p['id'] for p in after['ports']}),
            'restoredGroupIds':sorted({g['id'] for g in before['groups']}-{g['id'] for g in after['groups']}),
            'restoredConnectionIds':sorted({c['id'] for c in before['connections']}-{c['id'] for c in after['connections']}),
            'compensatedOperationId':made['operationId']})
        self.assertEqual(self.raw_state(device),before)
        self.assertEqual(undone['revision'],made['revision']+1)
        feed=self.expect(self.admin.request('GET',f'/api/v1/customers/{self.customer_id}/changes?afterRevision={made["revision"]}'),200).json()
        event=next(e for e in feed['events'] if e['id']==undone['operationId'])
        self.assertEqual(event['context'],{'status':'notAvailable','beforePorts':[],'afterPorts':[],'beforeConnections':[],'afterConnections':[]})

    def test_no_cables_replay_committed_cancel_restart_and_latest_fence(self):
        device,before,made=self.reduce(cables=False,remove_group=False);key=uid();revision=made['revision']
        undone=self.undo(made,key=key,revision=revision).json()
        self.assertEqual(undone['result']['restoredConnectionIds'],[])
        self.assertEqual(undone['result']['restoredGroupIds'],[])
        self.assertEqual(self.undo(made,key=key,revision=revision).json(),undone)
        terminal=self.cancel('operations.compensate',{'operationId':made['operationId']},key,revision=revision).json()
        self.assertEqual(terminal['state'],'committed');self.assertEqual(terminal['operation'],undone)
        self.server.close();self.server=self.lab.start_server(self.db)
        self.admin=Client(self.server);self.admin.actor_id=self.admin_id
        self.expect(self.admin.login('qa-inventory-admin',self.password),200)
        self.assertEqual(self.raw_state(device),before);self.assertEqual(self.operation_state(key)['operation'],undone)
        self.stable_rejection(device,made,409,'compensation_not_latest')

    def test_missing_incomplete_corrupt_evidence_and_mixed_rename_fail_closed(self):
        device,_,made=self.reduce()
        saved=json.loads(self.lab.sql(self.db,f'SELECT before_json FROM audit_event WHERE id={literal(made["operationId"])}'))
        for mutation in ('missing','incomplete','endpoint_missing','duplicate_ordinal','bad_timestamp','unknown_port_field'):
            value=json.loads(json.dumps(saved));e=value['data']['groupEditEvidence']
            if mutation=='missing':del value['data']['groupEditEvidence']
            elif mutation=='incomplete':e['complete']=False
            elif mutation=='endpoint_missing':e['connectionEndpoints'].pop()
            elif mutation=='duplicate_ordinal':e['connectionEndpoints'][0]['ordinal']=e['connectionEndpoints'][1]['ordinal']
            elif mutation=='bad_timestamp':e['connections'][0]['created_at']='invalid'
            else:e['ports'][0]['unknown']=True
            self.lab.sql(self.db,f'UPDATE audit_event SET before_json={literal(json.dumps(value))}::jsonb WHERE id={literal(made["operationId"])}')
            self.stable_rejection(device,made,422,'compensation_unsupported')
            self.lab.sql(self.db,f'UPDATE audit_event SET before_json={literal(json.dumps(saved))}::jsonb WHERE id={literal(made["operationId"])}')
        # A second reduction that renames a retained group is not a pure inverse candidate.
        current=self.snapshot();ports=[p for p in current['ports'] if p['deviceId']==device['id']]
        dropped=max(ports,key=lambda p:p['sortOrder'])['id']
        desired=self.desired_groups(device['id'],removed=[dropped]);desired[0]['name']='Mixed rename'
        payload={'deviceId':device['id'],'groups':desired,'removedPortIds':[dropped]}
        payload['confirmationToken']=self.preview('device.editPortGroups',payload)['confirmationToken']
        mixed=self.command('device.editPortGroups',payload).json()
        self.stable_rejection(device,mixed,422,'compensation_unsupported')

    def test_changed_rows_reused_ids_and_later_revision_conflict_without_overwrite(self):
        device,before,made=self.reduce(cables=False);after=self.raw_state(device)
        port=after['ports'][0]
        self.lab.sql(self.db,f"UPDATE inventory_port SET label='Out of band' WHERE id={literal(port['id'])}")
        self.stable_rejection(device,made,409,'compensation_state_conflict')
        self.lab.sql(self.db,f"UPDATE inventory_port SET label={literal(port['label'])} WHERE id={literal(port['id'])}")
        missing=next(p['id'] for p in before['ports'] if p['id'] not in {p['id'] for p in after['ports']})
        remote=self.remote[2][0]
        self.lab.sql(self.db,f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order) SELECT {literal(missing)},systemhaus_id,customer_id,device_id,group_id,type,9000,9000 FROM inventory_port WHERE id={literal(remote['id'])}")
        self.stable_rejection(device,made,409,'compensation_state_conflict')
        self.lab.sql(self.db,f'DELETE FROM inventory_port WHERE id={literal(missing)}')
        self.command('site.create',{'name':'Newer customer change'})
        self.stable_rejection(device,made,409,'compensation_not_latest')

    def test_remote_reserved_blocked_occupied_or_missing_is_not_displaced(self):
        device,_,made=self.reduce();remote=self.remote[2][0];free=self.remote[2][3]
        for status in ('reserved','disabled','faulty'):
            self.lab.sql(self.db,f'UPDATE inventory_port SET status={literal(status)} WHERE id={literal(remote["id"])}')
            self.stable_rejection(device,made,409,'compensation_state_conflict')
            self.assertEqual(self.lab.sql(self.db,f'SELECT status FROM inventory_port WHERE id={literal(remote["id"])}'),status)
        self.lab.sql(self.db,f"UPDATE inventory_port SET status='free' WHERE id={literal(remote['id'])}")
        connection=uid()
        self.lab.sql(self.db,f"BEGIN; INSERT INTO inventory_connection(id,systemhaus_id,customer_id) VALUES({literal(connection)},{literal(self.house_id)},{literal(self.customer_id)}); INSERT INTO inventory_connection_endpoint VALUES({literal(self.house_id)},{literal(self.customer_id)},{literal(connection)},0,{literal(remote['id'])}),({literal(self.house_id)},{literal(self.customer_id)},{literal(connection)},1,{literal(free['id'])}); COMMIT;")
        self.stable_rejection(device,made,409,'compensation_state_conflict')
        self.assertEqual(self.lab.sql(self.db,f'SELECT count(*) FROM inventory_connection_endpoint WHERE connection_id={literal(connection)}'),'2')
        self.lab.sql(self.db,f'DELETE FROM inventory_connection WHERE id={literal(connection)}')
        self.lab.sql(self.db,f'DELETE FROM inventory_port WHERE id={literal(remote["id"])}')
        self.stable_rejection(device,made,409,'compensation_state_conflict')

    def test_actor_customer_scope_csrf_and_revoked_permission(self):
        writer,group,_=self.add_user('reduce-writer',['inventory.read','inventory.edit'],self.customer_id)
        device,_,made=self.reduce(client=writer)
        other,_,_=self.add_user('reduce-other',['inventory.read','inventory.edit'],self.customer_id)
        self.stable_rejection(device,made,404,'not_found',client=other)
        foreign=self.customer('Other customer')['id']
        for capability in ('inventory.read','inventory.edit'):
            self.lab.sql(self.db,f"INSERT INTO permission_grant VALUES({literal(uid())},{literal(self.house_id)},{literal(group)},{literal(capability)},{literal(foreign)},NULL)")
        self.stable_rejection(device,made,404,'not_found',customer=foreign,client=writer)
        response=writer.request('POST',f'/api/v1/customers/{self.customer_id}/commands',{'type':'operations.compensate','payload':{'operationId':made['operationId']}},
            {'If-Match':f'"{made["revision"]}"','Idempotency-Key':uid(),'X-RackClick-Actor':writer.actor_id,'X-RackClick-CSRF':'invalid'})
        self.expect(response,403)
        self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id={literal(group)} AND capability='inventory.edit'")
        self.stable_rejection(device,made,403,'forbidden',client=writer)

    def test_audit_failure_rolls_back_restoration_and_concurrent_attempts_commit_once(self):
        device,_,made=self.reduce();before=self.raw_state(device);key=uid()
        self.lab.sql(self.db,"CREATE FUNCTION qa_reduce_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Synthetic restore failure'; END $$; CREATE TRIGGER qa_reduce_fail BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION qa_reduce_fail();")
        try:
            self.undo(made,key=key,status=503);self.assertEqual(self.raw_state(device),before)
            self.assertEqual(self.snapshot()['revision'],made['revision'])
            self.assertEqual(self.lab.sql(self.db,f'SELECT count(*) FROM operation WHERE request_id={literal(key)}'),'0')
        finally:self.lab.sql(self.db,'DROP TRIGGER qa_reduce_fail ON audit_event; DROP FUNCTION qa_reduce_fail();')
        def attempt():
            return self.admin.request('POST',f'/api/v1/customers/{self.customer_id}/commands',{'type':'operations.compensate','payload':{'operationId':made['operationId']}},
                {'If-Match':f'"{made["revision"]}"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}).status
        with ThreadPoolExecutor(2) as pool:statuses=sorted(pool.map(lambda _:attempt(),range(2)))
        self.assertEqual(statuses,[200,412]);self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM audit_event WHERE action='inventory.operations.compensate'"),'1')

    def test_session_expiring_during_device_wait_blocks_restoration(self):
        writer,_,_=self.add_user('reduce-expiring',['inventory.read','inventory.edit'],self.customer_id)
        device,_,made=self.reduce(client=writer);before=self.raw_state(device);marker='reduce_'+uid().replace('-','')
        with ThreadPoolExecutor(2) as pool:
            holder=pool.submit(self.lab.sql,self.db,f"SET application_name={literal(marker)}; BEGIN; SELECT id FROM inventory_device WHERE id={literal(device['id'])} FOR UPDATE; SELECT pg_sleep(3); COMMIT;")
            deadline=time.monotonic()+2
            while self.lab.sql(self.db,f"SELECT count(*) FROM pg_stat_activity WHERE application_name={literal(marker)} AND wait_event='PgSleep'",admin=True)!='1':
                self.assertLess(time.monotonic(),deadline);time.sleep(.02)
            self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '1 second' WHERE user_id={literal(writer.actor_id)}")
            pending=pool.submit(self.undo,made,client=writer,status=401)
            while self.lab.sql(self.db,f"SELECT count(*) FROM pg_stat_activity WHERE datname={literal(self.db.name)} AND usename={literal(self.db.runtime)} AND wait_event_type='Lock'",admin=True)=='0':
                self.assertLess(time.monotonic(),deadline);time.sleep(.02)
            holder.result();self.assertEqual(pending.result().json()['error'],'authentication_required')
        self.assertEqual(self.raw_state(device),before);self.assertEqual(self.snapshot()['revision'],made['revision'])

    def test_all_groups_removed_power_pair_revalidated_before_exact_restore(self):
        _,_,_,rack=self.hierarchy()
        device,groups,ports=self.device('Power source',rack=rack['id'],groups=[{'type':'power','count':2}])
        _,peer_groups,peer_ports=self.device('Power sink',rack=rack['id'],groups=[{'type':'power','count':1}])
        self.port_changes(device,groups[0],[ports[0]],{'powerRole':'outlet','label':'AC original'})
        peer_device=next(d for d in self.snapshot()['devices'] if d['id']==peer_ports[0]['deviceId'])
        self.port_changes(peer_device,peer_groups[0],peer_ports,{'powerRole':'inlet'})
        self.connect(ports[0],peer_ports[0],note='Original AC link')
        before=self.raw_state(device)
        payload={'deviceId':device['id'],'groups':[],'removedPortIds':[p['id'] for p in ports]}
        payload['confirmationToken']=self.preview('device.editPortGroups',payload)['confirmationToken']
        made=self.command('device.editPortGroups',payload).json()
        self.assertEqual(self.raw_state(device),{'groups':[],'ports':[],'connections':[],'connectionEndpoints':[]})
        self.lab.sql(self.db,f"UPDATE inventory_port SET power_role='outlet' WHERE id={literal(peer_ports[0]['id'])}")
        self.stable_rejection(device,made,409,'compensation_state_conflict')
        self.lab.sql(self.db,f"UPDATE inventory_port SET power_role='inlet' WHERE id={literal(peer_ports[0]['id'])}")
        undone=self.undo(made).json()
        self.assertEqual(undone['result']['compensationKind'],'groupReduction')
        self.assertEqual(self.raw_state(device),before)


CASES=tuple(name for name in GroupReductionCompensation.__dict__ if name.startswith('test_'))
def load_tests(loader,tests,pattern):return unittest.TestSuite(GroupReductionCompensation(n) for n in CASES)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--cases',nargs='*',choices=CASES);args=parser.parse_args()
    dll=args.dll.resolve();target=args.evidence.resolve();private=(pg.WORKSPACE/'.local').resolve()
    if not dll.is_file() or not dll.is_relative_to(private) or not target.is_relative_to(private):raise ValueError('Private DLL and new private evidence required')
    target.mkdir(exist_ok=False);pg.protect_directory(target);pg.DEFAULT_DLL=dll;lab=pg.Lab('c2-reduction')
    report={'dllSha256':hashlib.sha256(dll.read_bytes()).hexdigest(),'newCluster':True,'qaTouched':False}
    try:
        with lab:
            report['postgresql']=lab.sql('postgres','SHOW server_version',admin=True);GroupReductionCompensation.lab=lab
            with (target/'tests-private.log').open('w',encoding='utf-8') as log:
                result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.TestSuite(GroupReductionCompensation(n) for n in (args.cases or CASES)))
            report.update(cases=list(args.cases or CASES),testsRun=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),successful=result.wasSuccessful())
    finally:
        lab.close();report['labStopped']=not lab.running;(target/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report));return 0 if report.get('successful') and report['labStopped'] else 1

if __name__=='__main__':raise SystemExit(main())
