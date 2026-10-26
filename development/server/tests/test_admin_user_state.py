"""Isolated Windows PostgreSQL user activation/deactivation and session revocation."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import subprocess
import time
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import unittest
import uuid
from pg_support import DEFAULT_DLL, Lab, Client, NO_WINDOW
from test_postgres import EvidenceResult, Tee
from test_admin_permission_races import PermissionRacePostgres


class UserStatePostgres(PermissionRacePostgres):
    @contextmanager
    def user_lock(self,user):
        """Own psql session keeps the row lock until explicitly committed."""
        env = self.lab.environment()
        env['PGPASSFILE'] = str(self.db.directory / 'owner.pgpass')
        process = subprocess.Popen([str(self.lab.pg_bin / 'psql.exe'), '-X', '-w', '-qAt',
            '-v', 'ON_ERROR_STOP=1', '-h', '127.0.0.1', '-p', str(self.lab.port),
            '-U', self.db.owner, '-d', self.db.name], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
            env=env, creationflags=NO_WINDOW)
        try:
            process.stdin.write(f"BEGIN; SELECT id FROM app_user WHERE id='{user}' FOR UPDATE; SELECT pg_backend_pid();\n")
            process.stdin.flush()
            with ThreadPoolExecutor(1) as reader:
                row = reader.submit(lambda: (process.stdout.readline().strip(), process.stdout.readline().strip()))
                try:
                    locked, pid = row.result(timeout=8)
                except BaseException:
                    process.kill()
                    raise
            self.assertEqual(locked, user)
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

    def wait_for_user_waiter(self,pid,query):
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            count=self.lab.sql(self.db,f"SELECT count(*) FROM pg_stat_activity a WHERE a.datname='{self.db.name}' AND a.usename='{self.db.runtime}' AND a.wait_event_type='Lock' AND a.query LIKE '{query}' AND EXISTS(WITH RECURSIVE blockers(pid) AS (SELECT unnest(pg_blocking_pids(a.pid)) UNION SELECT unnest(pg_blocking_pids(b.pid)) FROM blockers b) SELECT 1 FROM blockers WHERE pid={pid})",admin=True)
            if count=='1':return
            time.sleep(.025)
        self.fail('No target row waiter witnessed in PostgreSQL')

    def change(self,user,active,revision=None,key=None,cancel=False,client=None,actor=None,headers=None,payload=None):
        key=key or str(uuid.uuid4());path=f'/api/v1/admin/users/{user}/state'
        if cancel:path+=f'/operations/{key}/cancel'
        return (client or self.admin).request('POST',path,{'active':active} if payload is None else payload,
            {'If-Match':f'"{revision if revision is not None else self.house_revision()}"','Idempotency-Key':key,
             'X-RackClick-Actor':actor or self.admin_id,**(headers or {})})

    def outcome(self,user,key,client=None):
        return (client or self.admin).request('GET',f'/api/v1/admin/users/{user}/state/operations/{key}')

    def snapshot(self):
        # Password/token hashes compared in SQL only; never included in failure messages/evidence.
        return self.lab.sql(self.db,"SELECT md5(string_agg(row_to_json(u)::text,',' ORDER BY id)) FROM app_user u; "
            "SELECT md5(string_agg(row_to_json(s)::text,',' ORDER BY token_hash)) FROM app_session s; "
            "SELECT revision FROM systemhaus; SELECT count(*) FROM operation; SELECT count(*) FROM audit_event")

    def test_state_sessions_reactivation_noop_and_replay(self):
        self.initialize();user,first=self.add_user('target');second=Client(self.server);self.expect(second.login('target',self.password),200)
        group=self.user_group(user);self.grant(group,'systemhaus.read')
        invariant=self.lab.sql(self.db,f"SELECT md5(password_hash),failed_logins,locked_until FROM app_user WHERE id='{user}'; SELECT count(*) FROM user_group_member WHERE user_id='{user}'; SELECT count(*) FROM permission_grant")
        revision=self.house_revision();key=str(uuid.uuid4());made=self.expect(self.change(user,False,revision,key),200).json()
        self.assertEqual(made,{'resource':{'id':user,'userName':'target','active':False},'systemhausRevision':revision+1,'requestId':key})
        for client in (first,second):self.expect(client.request('GET','/api/v1/me'),401)
        self.expect(Client(self.server).login('target',self.password),401,'login_failed')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM app_session WHERE user_id='{user}'"),'0')
        self.expect(self.change(user,False),200)  # inactive no-op still audited and sessions deleted
        self.expect(self.change(user,True),200)
        for client in (first,second):self.expect(client.request('GET','/api/v1/me'),401)
        fresh=Client(self.server);self.expect(fresh.login('target',self.password),200)
        self.assertEqual(invariant,self.lab.sql(self.db,f"SELECT md5(password_hash),failed_logins,locked_until FROM app_user WHERE id='{user}'; SELECT count(*) FROM user_group_member WHERE user_id='{user}'; SELECT count(*) FROM permission_grant"))
        now=self.house_revision();self.assertEqual(self.expect(self.change(user,False,revision,key),200).json(),made)
        self.assertEqual(self.house_revision(),now);self.expect(fresh.request('GET','/api/v1/me'),200)
        self.expect(self.change(user,True),200);self.expect(fresh.request('GET','/api/v1/me'),200)
        audit=self.lab.sql(self.db,"SELECT bool_and(a.before_json ?& ARRAY['id','userName','active'] AND a.after_json ?& ARRAY['id','userName','active'] AND (SELECT count(*)=3 FROM jsonb_object_keys(a.before_json)) AND (SELECT count(*)=3 FROM jsonb_object_keys(a.after_json))) FROM audit_event a WHERE action='user.state.set'")
        self.assertEqual(audit,'t')

    def test_state_last_active_global_admin_and_self_disable(self):
        self.initialize();before=self.snapshot();self.expect(self.change(self.admin_id,False),409,'last_admin_required');self.assertEqual(before,self.snapshot())
        inactive,_=self.add_user('inactive',admin=True);self.lab.sql(self.db,f"UPDATE app_user SET active=false WHERE id='{inactive}'")
        scoped,_=self.add_user('scoped');group=self.user_group(scoped);customer=self.customer('Scope');self.grant(group,'security.manage',customer=customer['id'])
        before=self.snapshot();self.expect(self.change(self.admin_id,False),409,'last_admin_required');self.assertEqual(before,self.snapshot())
        other,session=self.add_user('other',admin=True);revision=self.house_revision();key=str(uuid.uuid4())
        self.expect(self.change(self.admin_id,False,revision,key),200);self.expect(self.admin.request('GET','/api/v1/me'),401)
        self.expect(session.request('GET','/api/v1/admin/users'),200)
        self.expect(self.change(other,False,revision+1,client=session,actor=other),409,'last_admin_required')
        self.expect(self.change(self.admin_id,True,revision+1,client=session,actor=other),200)
        self.expect(self.admin.request('GET','/api/v1/me'),401)  # reactivation never resurrects original session

    def test_state_validation_headers_global_target_openapi(self):
        self.initialize();user,plain=self.add_user('plain');group=self.user_group(user);customer=self.customer('Scoped')
        self.grant(group,'security.manage',customer=customer['id']);cg=self.customer_group();self.grant(group,'security.manage',customer_group=cg)
        self.expect(self.change(user,False,client=plain,actor=user),403)
        for payload in ({},{'active':None}):self.expect(self.change(user,None,payload=payload),422,'user_state_invalid')
        self.expect(self.change(str(uuid.UUID(int=0)),False),422,'user_state_invalid');self.expect(self.change(str(uuid.uuid4()),False),404)
        for headers,status in [({'Origin':'https://invalid.example'},403),({'X-RackClick-CSRF':'bad'},403),({'X-RackClick-Actor':''},422),({'X-RackClick-Actor':user},409),({'If-Match':''},428),({'Idempotency-Key':''},422)]:
            self.expect(self.change(user,False,headers=headers),status)
        # Own lab temporarily permits another Systemhaus solely as a cross-scope negative fixture.
        self.lab.sql(self.db,'DROP INDEX one_systemhaus_per_installation')
        other=str(uuid.uuid4());foreign=str(uuid.uuid4())
        self.lab.sql(self.db,f"INSERT INTO systemhaus(id,name) VALUES('{other}','Foreign synthetic'); INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{foreign}','{other}','foreign',password_hash FROM app_user WHERE id='{user}'")
        self.expect(self.change(foreign,False),404)
        doc=self.admin.request('GET','/api/v1/openapi.json').json();op=doc['paths']['/api/v1/admin/users/{userId}/state']['post']
        self.assertTrue({'userId','If-Match','Idempotency-Key','X-RackClick-Actor','X-RackClick-CSRF'} <= {p['name'] for p in op['parameters'] if p.get('required')})
        self.assertEqual(doc['components']['schemas']['SetUserState']['required'],['active'])

    def test_state_status_stale_fence_actor_target_action(self):
        self.initialize();user,_=self.add_user('target');other,session=self.add_user('other-admin',admin=True);key=str(uuid.uuid4());revision=self.house_revision();self.customer('Advance')
        self.expect(self.change(user,False,revision,key),412);self.assertEqual(self.outcome(user,key).json()['state'],'notRecorded')
        cancelled=self.expect(self.change(user,False,revision,key,True),200).json();self.assertEqual(cancelled['state'],'cancelled')
        self.expect(self.change(user,False,revision,key),409,'operation_cancelled')
        self.assertEqual(self.expect(self.change(user,False,revision,key,True),200).json(),cancelled)
        self.expect(self.change(user,True,revision,key,True),409,'request_id_reused')
        self.assertEqual(self.outcome(other,key).json()['state'],'notRecorded');self.assertEqual(self.outcome(user,key,session).json()['state'],'notRecorded')
        self.assertEqual(self.admin.request('GET',f'/api/v1/admin/users/operations/{key}').json()['state'],'notRecorded')
        self.expect(self.change(str(uuid.uuid4()),False,revision,str(uuid.uuid4()),True),200)
        key=str(uuid.uuid4());revision=self.house_revision();made=self.expect(self.change(user,False,revision,key),200).json()
        # A separate completed intent reusing this key must also conflict by action digest.
        self.expect(self.admin.request('POST','/api/v1/admin/users', {'username':'new-synthetic','password':self.password}, {'If-Match':f'"{revision}"','Idempotency-Key':key,'X-RackClick-Actor':self.admin_id}),409,'request_id_reused')
        self.assertEqual(self.outcome(user,key).json()['operation'],made);self.assertEqual(self.expect(self.change(user,False,revision,key,True),200).json()['operation'],made)
        self.expect(self.change(other,False,revision,key),409,'request_id_reused')

    def test_state_audit_rollback_exact_concurrency_and_cancel(self):
        self.initialize();user,session=self.add_user('target');revision=self.house_revision();key=str(uuid.uuid4());before=self.snapshot()
        self.lab.sql(self.db,"""CREATE FUNCTION reject_state_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
          IF NEW.action LIKE 'user.state.set%' THEN RAISE EXCEPTION 'synthetic audit failure'; END IF; RETURN NEW; END $$;
          CREATE TRIGGER reject_state_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION reject_state_audit();""")
        self.expect(self.change(user,False,revision,key),503);self.assertEqual(before,self.snapshot());self.expect(session.request('GET','/api/v1/me'),200)
        self.expect(self.change(user,False,revision,key,True),503);self.assertEqual(before,self.snapshot())
        self.lab.sql(self.db,'DROP TRIGGER reject_state_audit ON audit_event')
        with ThreadPoolExecutor(2) as pool:
            a=pool.submit(self.change,user,False,revision,key);b=pool.submit(self.change,user,False,revision,key)
            self.assertEqual(self.expect(a.result(),200).json(),self.expect(b.result(),200).json())
        self.assertEqual(self.house_revision(),revision+1);self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM audit_event WHERE action='user.state.set'"),'1')
        # Both real HTTP login and deactivation wait behind same target row fixture.
        self.expect(self.change(user,True),200);now=self.house_revision();fresh=Client(self.server)
        with self.user_lock(user) as (blocker,pid),ThreadPoolExecutor(2) as pool:
            login=pool.submit(fresh.login,'target',self.password)
            deactivate=pool.submit(self.change,user,False,now)
            try:
                self.wait_for_user_waiter(pid,'%SELECT id,password_hash,active%')
                self.wait_for_user_waiter(pid,'%SELECT id,username,active FROM app_user%FOR UPDATE%')
                self.assertFalse(login.done());self.assertFalse(deactivate.done())
            finally:blocker.stdin.write('COMMIT;\n');blocker.stdin.flush()
            self.expect(deactivate.result(timeout=10),200)
            self.assertIn(login.result(timeout=10).status,(200,401))
        self.expect(fresh.request('GET','/api/v1/me'),401)
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM app_session WHERE user_id='{user}'"),'0')
        race=str(uuid.uuid4());now=self.house_revision()
        with ThreadPoolExecutor(2) as pool:
            a=pool.submit(self.change,user,True,now,race);b=pool.submit(self.change,user,True,now,race,True)
            change=a.result();terminal=self.expect(b.result(),200).json()
        if terminal['state']=='committed':self.expect(change,200);self.assertEqual(self.house_revision(),now+1)
        else:self.expect(change,409,'operation_cancelled');self.assertEqual(self.house_revision(),now)

    def test_state_waiting_revocation_set_replay_cancel(self):
        self.initialize();user,session=self.add_user('delegated');group=self.user_group(user);self.grant(group,'security.manage');target,_=self.add_user('target')
        for kind in ('set','replay','cancel'):
            with self.subTest(kind=kind):
                if kind!='set':self.grant(group,'security.manage')
                revision=self.house_revision();key=str(uuid.uuid4())
                if kind=='replay':self.expect(self.change(target,True,revision,key,client=session,actor=user),200)
                before=self.snapshot()
                with self.house_lock() as (blocker,pid),ThreadPoolExecutor(1) as pool:
                    pending=pool.submit(self.change,target,False if kind!='replay' else True,revision,key,kind=='cancel',session,user)
                    try:
                        self.wait_for_house_waiter(pid);self.assertFalse(pending.done())
                        self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability='security.manage'")
                    finally:blocker.stdin.write('COMMIT;\n');blocker.stdin.flush()
                    self.expect(pending.result(timeout=10),403,'forbidden')
                self.assertEqual(before,self.snapshot());self.expect(self.outcome(target,key,session),403,'forbidden')
        # Final target wait can outlive actor session despite earlier house check.
        revision=self.house_revision();key=str(uuid.uuid4())
        self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '4 seconds' WHERE user_id='{self.admin_id}'")
        before=self.snapshot()
        with self.user_lock(target) as (blocker,pid),ThreadPoolExecutor(1) as pool:
            pending=pool.submit(self.change,target,False,revision,key)
            try:
                self.wait_for_user_waiter(pid,'%SELECT id,username,active FROM app_user%FOR UPDATE%')
                deadline=time.monotonic()+8
                while self.lab.sql(self.db,f"SELECT bool_and(expires_at<=clock_timestamp()) FROM app_session WHERE user_id='{self.admin_id}'")!='t':
                    if time.monotonic()>deadline:self.fail('Actor session did not expire')
                    time.sleep(.025)
                self.assertFalse(pending.done())
            finally:blocker.stdin.write('COMMIT;\n');blocker.stdin.flush()
            self.expect(pending.result(timeout=10),401,'authentication_required')
        self.assertEqual(before,self.snapshot())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--case',action='append');args=parser.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[3]
    inputs=[root/'development/server/src/RackClick.Server'/name for name in ('AdminUserState.cs','Program.cs','OpenApiAdmin.cs')]+[Path(__file__).resolve()]
    hashes={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    data={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'dllSha256':hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest(),'sourceHashes':hashes}
    lab=Lab('admin-user-state')
    with lab, (args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        UserStatePostgres.lab=lab
        names=[n for n in unittest.defaultTestLoader.getTestCaseNames(UserStatePostgres) if n.startswith('test_state_') and (not args.case or n in args.case)]
        if not names:raise ValueError('No selected user state cases')
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(UserStatePostgres(n) for n in names))
        data.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    data.update(labStopped=not lab.running,inputsUnchanged=data['dllSha256']==hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest() and hashes=={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    return 0 if result.wasSuccessful() and data['labStopped'] and data['inputsUnchanged'] else 1

if __name__=='__main__':sys.exit(main())
