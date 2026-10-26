"""Authorization union/revocation with native Windows PostgreSQL lock witnesses."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
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
from pg_support import DEFAULT_DLL, Lab, NO_WINDOW
from test_admin_customer_members import CustomerMemberPostgres
from test_postgres import EvidenceResult, Tee


class PermissionRacePostgres(CustomerMemberPostgres):
    @contextmanager
    def house_lock(self):
        """Own psql session keeps the row lock until explicitly committed."""
        env = self.lab.environment()
        env['PGPASSFILE'] = str(self.db.directory / 'owner.pgpass')
        process = subprocess.Popen([str(self.lab.pg_bin / 'psql.exe'), '-X', '-w', '-qAt',
            '-v', 'ON_ERROR_STOP=1', '-h', '127.0.0.1', '-p', str(self.lab.port),
            '-U', self.db.owner, '-d', self.db.name], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
            env=env, creationflags=NO_WINDOW)
        try:
            process.stdin.write(f"BEGIN; SELECT id FROM systemhaus WHERE id='{self.house}' FOR UPDATE; SELECT pg_backend_pid();\n")
            process.stdin.flush()
            with ThreadPoolExecutor(1) as reader:
                row = reader.submit(lambda: (process.stdout.readline().strip(), process.stdout.readline().strip()))
                try:
                    locked, pid = row.result(timeout=8)
                except BaseException:
                    process.kill()
                    raise
            self.assertEqual(locked, self.house)
            self.assertTrue(pid.isdigit(), 'Lock witness must provide its PostgreSQL PID')
            yield process, int(pid)
        finally:
            if process.poll() is None:
                process.stdin.write('ROLLBACK;\n\\q\n')
                process.stdin.flush()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=5)
            for pipe in (process.stdin, process.stdout, process.stderr):
                pipe.close()

    def wait_for_house_waiter(self, pid):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            found = self.lab.sql(self.db, f"""SELECT count(*) FROM pg_stat_activity a
                WHERE a.datname='{self.db.name}' AND a.usename='{self.db.runtime}'
                AND a.state='active' AND a.wait_event_type='Lock'
                AND a.query LIKE '%SELECT revision FROM systemhaus%FOR UPDATE%'
                AND {pid}=ANY(pg_blocking_pids(a.pid))""", admin=True)
            if found == '1':
                return
            time.sleep(.025)  # polling cadence only; the pg_blocking_pids witness is proof
        self.fail('No runtime Systemhaus lock waiter witnessed in PostgreSQL')

    def invariant(self):
        return self.lab.sql(self.db, 'SELECT revision FROM systemhaus; SELECT count(*) FROM customer_group_member; '
            'SELECT count(*) FROM operation; SELECT count(*) FROM audit_event')

    def waiting_revocation(self, group, customer, assigned, revision, key, user, session, grants, cancel=False):
        before = self.invariant()
        with self.house_lock() as (blocker, pid), ThreadPoolExecutor(1) as pool:
            pending = pool.submit(self.member, group, customer, assigned, revision, key, cancel, session, user)
            try:
                self.wait_for_house_waiter(pid)
                self.assertFalse(pending.done(), 'HTTP operation must still be blocked')
                # Revocation commits while our explicit row lock still holds. HTTP cannot
                # reach its authorization re-check until the lock is released below.
                self.lab.sql(self.db, f"DELETE FROM permission_grant WHERE user_group_id='{grants}' AND capability='security.manage'")
            finally:
                blocker.stdin.write('COMMIT;\n'); blocker.stdin.flush()
            self.expect(pending.result(timeout=10), 403, 'forbidden')
        self.assertEqual(self.invariant(), before)
        self.expect(self.status(group, key, session), 403, 'forbidden')

    def test_permission_union_inventory_edit_two_customer_groups(self):
        self.initialize(); customer = self.customer('Synthetic union'); path = f"/api/v1/customers/{customer['id']}"
        user, session = self.add_user('union-editor'); users = self.user_group(user)
        groups = [self.customer_group(), self.customer_group()]
        for group in groups:
            self.grant(users, 'inventory.read', customer_group=group)
            self.grant(users, 'inventory.edit', customer_group=group)
            self.expect(self.member(group, customer['id'], True), 200)
        project = path + '/project'
        def command(client, actor, kind, payload):
            revision = self.admin.request('GET', project).json()['revision']
            return client.request('POST', path + '/commands', {'type':kind,'payload':payload},
                {'If-Match':f'"{revision}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor})
        self.expect(command(self.admin,self.admin_id,'site.create',{'name':'Synthetic site'}),200)
        site = self.admin.request('GET',project).json()['sites'][0]['id']
        self.expect(command(self.admin,self.admin_id,'building.create',{'siteId':site,'name':'Synthetic building'}),200)
        building = self.admin.request('GET',project).json()['buildings'][0]['id']
        self.expect(command(self.admin,self.admin_id,'room.create',{'buildingId':building,'name':'Synthetic room'}),200)
        room = self.admin.request('GET',project).json()['rooms'][0]['id']
        self.expect(session.request('GET',project),200)
        self.expect(command(session,user,'rack.create',{'roomId':room,'name':'Both grants','sizeU':42}),200)
        self.expect(self.member(groups[0],customer['id'],False),200)
        self.expect(session.request('GET',project),200)
        self.expect(command(session,user,'rack.create',{'roomId':room,'name':'Remaining grant','sizeU':42}),200)
        self.expect(self.member(groups[1],customer['id'],False),200)
        before = self.admin.request('GET',project).json(); invariants = self.invariant()
        self.expect(session.request('GET',project),404)
        self.expect(command(session,user,'rack.create',{'roomId':room,'name':'Denied final','sizeU':42}),404)
        self.assertEqual(self.admin.request('GET',project).json(), before)
        self.assertEqual(self.invariant(), invariants)
        self.assertEqual(len(before['racks']), 2)

    def test_permission_revoked_during_assignment_lock_wait(self):
        self.initialize(); customer=self.customer('Synthetic locked'); group=self.customer_group()
        user,session=self.add_user('security-locked'); grants=self.user_group(user); self.grant(grants,'security.manage')
        key=str(uuid.uuid4())
        self.waiting_revocation(group,customer['id'],True,self.house_revision(),key,user,session,grants)
        self.assertEqual(self.status(group,key).json()['state'],'notRecorded')

    def test_permission_revoked_during_replay_and_cancel_lock_wait(self):
        self.initialize(); customer=self.customer('Synthetic recovery'); group=self.customer_group()
        user,session=self.add_user('security-recovery'); grants=self.user_group(user); self.grant(grants,'security.manage')
        revision=self.house_revision(); key=str(uuid.uuid4())
        made=self.expect(self.member(group,customer['id'],True,revision,key,client=session,actor=user),200).json()
        self.waiting_revocation(group,customer['id'],True,revision,key,user,session,grants)
        self.grant(grants,'security.manage')
        cancel_key=str(uuid.uuid4())
        self.waiting_revocation(group,customer['id'],False,self.house_revision(),cancel_key,user,session,grants,cancel=True)
        self.assertEqual(self.status(group,cancel_key).json()['state'],'notRecorded')
        self.grant(grants,'security.manage')
        self.assertEqual(self.status(group,key,session).json()['operation'],made)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--regression',action='store_true'); args=parser.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=False)
    data={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),
        'dllSha256':hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest(),
        'testSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    lab=Lab('permission-races')
    with lab, (args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        PermissionRacePostgres.lab=lab
        names=[n for n in unittest.defaultTestLoader.getTestCaseNames(PermissionRacePostgres) if n.startswith('test_permission_')]
        if args.regression:
            names = [n for n in unittest.defaultTestLoader.getTestCaseNames(CustomerMemberPostgres) if n.startswith('test_customer_members_')]
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(
            unittest.TestSuite(PermissionRacePostgres(n) for n in names))
        data.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
        data['postgresVersion']=lab.sql('postgres','SHOW server_version')
    data.update(labStopped=not lab.running,inputsUnchanged=data['dllSha256']==hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest())
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    return 0 if result.wasSuccessful() and data['labStopped'] and data['inputsUnchanged'] else 1

if __name__=='__main__': sys.exit(main())
