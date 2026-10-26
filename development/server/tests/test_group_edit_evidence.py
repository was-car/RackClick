"""Native PG checks of server-owned group-edit evidence and its supported pure reduction inverse."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import unittest

import pg_support as pg
from pg_support import literal, Client
from test_inventory_postgres import InventoryPostgres, uid


class GroupEditEvidence(InventoryPostgres):
    def raw_state(self, device):
        did, house, customer = map(literal, (device['id'], self.house_id, self.customer_id))
        # Closed identifiers; all UUIDs originate in this isolated fixture.
        scoped = f"systemhaus_id={house} AND customer_id={customer}"
        value = self.lab.sql(self.db, f"""
            WITH p AS (SELECT * FROM inventory_port WHERE {scoped} AND device_id={did}),
              c AS (SELECT * FROM inventory_connection WHERE {scoped}
                AND id IN (SELECT connection_id FROM inventory_connection_endpoint WHERE {scoped} AND port_id IN (SELECT id FROM p)))
            SELECT jsonb_build_object(
              'groups',(SELECT coalesce(jsonb_agg(to_jsonb(g) ORDER BY g.id),'[]'::jsonb)
                FROM inventory_port_group g WHERE {scoped} AND device_id={did}),
              'ports',(SELECT coalesce(jsonb_agg(to_jsonb(p) ORDER BY p.id),'[]'::jsonb) FROM p),
              'connections',(SELECT coalesce(jsonb_agg(to_jsonb(c) ORDER BY c.id),'[]'::jsonb) FROM c),
              'connectionEndpoints',(SELECT coalesce(jsonb_agg(to_jsonb(e) ORDER BY e.connection_id,e.ordinal),'[]'::jsonb)
                FROM inventory_connection_endpoint e WHERE {scoped} AND connection_id IN (SELECT id FROM c)))
            """)
        return json.loads(value)

    def evidence(self, operation):
        row = json.loads(self.lab.sql(self.db, f"SELECT jsonb_build_object('before',before_json,'after',after_json) "
                                      f"FROM audit_event WHERE id={literal(operation['operationId'])}"))
        return row['before']['data']['groupEditEvidence'], row['after']['data']['groupEditEvidence']

    def assert_state(self, evidence, state, device):
        self.assertEqual((evidence['formatVersion'], evidence['complete']), (1, True))
        self.assertEqual((evidence['systemhausId'], evidence['customerId'], evidence['deviceId']),
                         (self.house_id, self.customer_id, device['id']))
        self.assertEqual({k:evidence[k] for k in ('groups', 'ports', 'connections', 'connectionEndpoints')}, state)

    def test_growth_captures_full_persisted_rows_and_scope(self):
        _, _, _, rack = self.hierarchy()
        device, groups, ports = self.device('Audit growth Ä', rack=rack['id'], groups=[{'type':'rj45_poe','count':2}])
        _, _, peer = self.device('Peer', rack=rack['id'])
        self.port_changes(device, groups[0], [ports[0]], {'label':'Puerto Ü <svg>', 'face':'rear', 'watts':0, 'color':'#aabbcc'})
        self.connect(ports[0], peer[0], note='Full cable evidence', patch='progress')
        before = self.raw_state(device)
        desired = self.desired_groups(device['id'], add=2)
        desired[0]['name'], desired[0]['prefix'] = 'Grupo nuevo', 'X'
        operation = self.command('device.editPortGroups', {'deviceId':device['id'], 'groups':desired,
                                'removedPortIds':[], 'groupEditEvidence':{'forged':True}}).json()
        left, right = self.evidence(operation)
        self.assert_state(left, before, device)
        self.assert_state(right, self.raw_state(device), device)
        self.assertEqual(len(right['ports']), 4)
        self.assertEqual(len(right['connections']), 1)
        self.assertEqual(len(right['connectionEndpoints']), 2)
        self.assertFalse(any(p['device_id'] != device['id'] for p in right['ports']))
        self.assertNotIn('forged', left)
        self.assertNotIn('forged', right)

    def test_reduction_replay_restart_and_inverse_restores_evidence(self):
        _, _, _, rack = self.hierarchy()
        device, groups, ports = self.device('Reduce', rack=rack['id'], groups=[{'type':'rj45','count':2}, {'type':'rj45','count':1}])
        _, _, peer = self.device('Peer', rack=rack['id'])
        dropped = next(p for p in ports if p['groupId'] == groups[1]['id'])
        connection = self.connect(dropped, peer[0], note='Removed cable', color='#123abc')
        before = self.raw_state(device)
        removed = [dropped['id']]
        desired = [g for g in self.desired_groups(device['id'], removed=removed) if g['id'] != groups[1]['id']]
        payload = {'deviceId':device['id'], 'groups':desired, 'removedPortIds':removed}
        payload['confirmationToken'] = self.preview('device.editPortGroups', payload)['confirmationToken']
        revision = self.snapshot()['revision']; key = uid()
        operation = self.command('device.editPortGroups', payload, key=key, revision=revision).json()
        evidence = self.evidence(operation)
        self.assert_state(evidence[0], before, device)
        self.assert_state(evidence[1], self.raw_state(device), device)
        self.assertEqual([c['id'] for c in evidence[0]['connections']], [connection['id']])
        self.assertEqual(evidence[1]['connections'], [])
        self.assertEqual(evidence[1]['connectionEndpoints'], [])
        self.assertEqual(self.command('device.editPortGroups', payload, key=key, revision=revision).json(), operation)
        self.server.close(); self.server = self.lab.start_server(self.db)
        self.admin = Client(self.server); self.admin.actor_id = self.admin_id
        self.expect(self.admin.login('qa-inventory-admin', self.password), 200)
        self.assertEqual(self.evidence(operation), evidence)
        response = self.command('operations.compensate', {'operationId':operation['operationId']}).json()
        self.assertEqual(response['result']['compensationKind'], 'groupReduction')
        self.assertEqual(response['result']['restoredConnectionIds'], [connection['id']])
        self.assertEqual(self.raw_state(device), before)

    def test_audit_failure_rolls_back_edit_and_evidence(self):
        _, _, _, rack = self.hierarchy()
        device, _, _ = self.device('Rollback', rack=rack['id'])
        before = self.raw_state(device); revision = self.snapshot()['revision']; key = uid()
        payload = {'deviceId':device['id'], 'groups':self.desired_groups(device['id'], add=1), 'removedPortIds':[]}
        self.lab.sql(self.db, "CREATE FUNCTION qa_group_evidence_fail() RETURNS trigger LANGUAGE plpgsql AS $$ "
                     "BEGIN RAISE EXCEPTION 'Synthetic audit failure'; END $$; "
                     "CREATE TRIGGER qa_group_evidence_fail BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION qa_group_evidence_fail();")
        try:
            self.command('device.editPortGroups', payload, key=key, revision=revision, status=503)
            self.assertEqual(self.raw_state(device), before)
            self.assertEqual(self.snapshot()['revision'], revision)
            self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM operation WHERE request_id={literal(key)}"), '0')
            self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM audit_event WHERE request_id={literal(key)}"), '0')
        finally:
            self.lab.sql(self.db, 'DROP TRIGGER qa_group_evidence_fail ON audit_event; DROP FUNCTION qa_group_evidence_fail();')

    def test_oversize_evidence_is_explicitly_unavailable_as_a_pair(self):
        _, _, _, rack = self.hierarchy()
        device, _, ports = self.device('Bounded evidence', rack=rack['id'])
        payload = {'deviceId':device['id'], 'groups':self.desired_groups(device['id'], add=1), 'removedPortIds':[]}
        revision = self.snapshot()['revision']
        # Administrative fixture only: avoid transporting the large value through HTTP or public logs.
        self.lab.sql(self.db, f"UPDATE inventory_port SET properties=jsonb_build_object('synthetic',repeat('x',8388608)) WHERE id={literal(ports[0]['id'])}")
        operation = self.command('device.editPortGroups', payload, revision=revision).json()
        left, right = self.evidence(operation)
        self.assertEqual(left, {'formatVersion':1, 'complete':False, 'reason':'size_limit'})
        self.assertEqual(right, left)


CASES = ('test_growth_captures_full_persisted_rows_and_scope', 'test_reduction_replay_restart_and_inverse_restores_evidence',
         'test_audit_failure_rolls_back_edit_and_evidence', 'test_oversize_evidence_is_explicitly_unavailable_as_a_pair')


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(GroupEditEvidence(name) for name in CASES)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--cases', nargs='*', choices=CASES)
    args = parser.parse_args()
    dll = args.dll.resolve(); target = args.evidence.resolve(); private = (pg.WORKSPACE/'.local').resolve()
    if not dll.is_relative_to(private) or not target.is_relative_to(private):
        raise ValueError('Private, identified build and new output required')
    target.mkdir(exist_ok=False); pg.protect_directory(target)
    pg.DEFAULT_DLL = dll
    lab = pg.Lab('c2-group-evidence')
    report = {'dllSha256':hashlib.sha256(dll.read_bytes()).hexdigest(), 'qaTouched':False, 'newCluster':True}
    try:
        with lab:
            report['postgresql'] = lab.sql('postgres', 'SHOW server_version', admin=True)
            GroupEditEvidence.lab = lab
            with (target/'tests-private.log').open('w',encoding='utf-8') as log:
                result = unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.TestSuite(GroupEditEvidence(n) for n in (args.cases or CASES)))
            report.update(testsRun=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                          skipped=len(result.skipped), successful=result.wasSuccessful())
    finally:
        lab.close(); report['labStopped'] = not lab.running
        (target/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))
    return 0 if report.get('successful') and report['labStopped'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
