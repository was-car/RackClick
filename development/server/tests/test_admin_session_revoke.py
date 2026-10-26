"""Six native Windows/PostgreSQL groups: individual public-session revocation."""
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
from pg_support import DEFAULT_DLL, WORKSPACE, Lab, Client, NO_WINDOW
from test_postgres import EvidenceResult, Tee
from test_session_wait_expiry import SessionWaitPostgres


class SessionRevocationPostgres(SessionWaitPostgres):
    def revoke(self,user,sid,revision=None,key=None,cancel=False,client=None,actor=None,headers=None,payload=None):
        key=key or str(uuid.uuid4());path=f'/api/v1/admin/users/{user}/sessions/{sid}/revoke'
        if cancel:path+=f'/operations/{key}/cancel'
        return (client or self.admin).request('POST',path,{} if payload is None else payload,
            {'If-Match':f'"{revision if revision is not None else self.house_revision()}"','Idempotency-Key':key,
             'X-RackClick-Actor':actor or self.admin_id,**(headers or {})})

    def outcome(self,user,sid,key,client=None):
        return (client or self.admin).request('GET',f'/api/v1/admin/users/{user}/sessions/{sid}/revoke/operations/{key}')

    def sid(self,client):
        # Private cookie never appears in evidence or command-line arguments.
        digest=hashlib.sha256(client.cookie.split('=',1)[1].encode()).hexdigest().upper()
        return self.lab.sql(self.db,f"SELECT id FROM app_session WHERE token_hash='{digest}'",sensitive=True)

    def unchanged_account(self,user):
        return self.lab.sql(self.db,f"SELECT md5(row_to_json(u)::text) FROM app_user u WHERE id='{user}'; SELECT md5(string_agg(row_to_json(m)::text,',' ORDER BY group_id)) FROM user_group_member m WHERE user_id='{user}'; SELECT count(*) FROM permission_grant")

    def safe_records(self):
        self.assertEqual(self.lab.sql(self.db,"SELECT bool_and(NOT (row_to_json(a)::text ~ 'token_hash|csrf_hash|password|cookie|connection')) FROM audit_event a WHERE action LIKE 'user.session.revoke%'"),'t')
        self.assertEqual(self.lab.sql(self.db,"SELECT bool_and(a.before_json ?& ARRAY['userId','sessionId'] AND (SELECT count(*)=2 FROM jsonb_object_keys(a.before_json))) FROM audit_event a WHERE action LIKE 'user.session.revoke%'"),'t')
        self.assertEqual(self.lab.sql(self.db,"SELECT bool_and(NOT EXISTS(SELECT 1 FROM app_session s WHERE o.result_json::text LIKE '%'||s.token_hash||'%' OR o.result_json::text LIKE '%'||s.csrf_hash||'%')) FROM operation o"),'t')

    def test_revoke_selective_expired_inactive_persistence_public(self):
        self.initialize();user,first=self.add_user('target');second=Client(self.server);self.expect(second.login('target',self.password),200)
        selected=self.sid(first);retained=self.sid(second);invariant=self.unchanged_account(user);revision=self.house_revision();key=str(uuid.uuid4())
        made=self.expect(self.revoke(user,selected,revision,key),200).json()
        self.assertEqual(made,{'resource':{'userId':user,'sessionId':selected,'revoked':True,'wasCurrent':False},'systemhausRevision':revision+1,'requestId':key})
        self.expect(first.request('GET','/api/v1/me'),401);self.expect(second.request('GET','/api/v1/me'),200);self.assertEqual(invariant,self.unchanged_account(user))
        public=json.dumps({'action':'user.session.revoke','userId':user,'sessionId':selected,'expected':revision},separators=(',',':'))
        self.assertEqual(self.lab.sql(self.db,f"SELECT request_hash FROM operation WHERE request_id='{key}'"),hashlib.sha256(public.encode()).hexdigest().upper())
        self.server.close();self.server=self.lab.start_server(self.db)
        for client in (self.admin,first,second):client.server=self.server
        self.expect(first.request('GET','/api/v1/me'),401);self.expect(second.request('GET','/api/v1/me'),200)
        third=Client(self.server);self.expect(third.login('target',self.password),200);fresh=self.sid(third);before=self.durable()
        self.assertEqual(self.expect(self.revoke(user,selected,revision,key),200).json(),made);self.assertEqual(before,self.durable());self.expect(third.request('GET','/api/v1/me'),200)
        self.expect(self.revoke(user,selected),404,'not_found')
        self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()-interval '1 second' WHERE id='{retained}'; UPDATE app_user SET active=false WHERE id='{user}'")
        self.expect(self.revoke(user,retained),200);self.assertEqual(self.lab.sql(self.db,f"SELECT active,(SELECT count(*) FROM app_session WHERE user_id='{user}' AND id='{fresh}') FROM app_user WHERE id='{user}'"),'f|1');self.safe_records()

    def test_revoke_authorization_ids_headers_strict_body_openapi(self):
        self.initialize();user,plain=self.add_user('scoped');sid=self.sid(plain);group=self.user_group(user);customer=self.customer('Scope');cg=self.customer_group()
        self.grant(group,'security.manage',customer=customer['id']);self.grant(group,'security.manage',customer_group=cg);before=self.durable()
        for cancel in (False,True):self.expect(self.revoke(user,sid,cancel=cancel,client=plain,actor=user),403)
        self.expect(self.outcome(user,sid,str(uuid.uuid4()),plain),403);self.expect(self.revoke(user,sid,client=Client(self.server)),401)
        for headers,status in [({'Origin':'https://invalid.example'},403),({'X-RackClick-CSRF':'bad'},403),({'X-RackClick-Actor':''},422),({'X-RackClick-Actor':user},409),({'If-Match':''},428),({'Idempotency-Key':''},422)]:self.expect(self.revoke(user,sid,headers=headers),status)
        for cancel in (False,True):
            for payload in ([],{'extra':1},'null'):
                headers={'Content-Type':'application/json'} if isinstance(payload,str) else None
                self.expect(self.revoke(user,sid,cancel=cancel,payload=payload,headers=headers),422)
        self.expect(self.revoke(user,sid,cancel=True,headers={'Idempotency-Key':str(uuid.uuid4())}),422,'request_id_mismatch')
        empty=str(uuid.UUID(int=0))
        self.expect(self.revoke(empty,sid),422);self.expect(self.revoke(user,empty),422);self.expect(self.revoke(str(uuid.uuid4()),sid),404);self.expect(self.revoke(self.admin_id,sid),404);self.expect(self.revoke(user,str(uuid.uuid4())),404)
        self.expect(self.revoke(user,sid,revision=self.house_revision()+1),412);self.assertEqual(before,self.durable())
        self.lab.sql(self.db,'DROP INDEX one_systemhaus_per_installation');house=str(uuid.uuid4());foreign=str(uuid.uuid4())
        self.lab.sql(self.db,f"INSERT INTO systemhaus(id,name) VALUES('{house}','Foreign synthetic'); INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{foreign}','{house}','foreign',password_hash FROM app_user WHERE id='{user}'")
        before=self.durable();self.expect(self.revoke(foreign,sid),404);self.assertEqual(before,self.durable())
        doc=self.admin.request('GET','/api/v1/openapi.json').json();path='/api/v1/admin/users/{userId}/sessions/{sessionId}/revoke';schemas=doc['components']['schemas'];op=doc['paths'][path]['post']
        self.assertEqual(schemas['RevokeUserSession']['properties'],{});self.assertFalse(schemas['RevokeUserSession']['additionalProperties']);self.assertEqual(schemas['RevokeUserSession']['required'],[])
        self.assertEqual(set(schemas['UserSessionRevokedResource']['properties']),{'userId','sessionId','revoked','wasCurrent'})
        self.assertTrue({'userId','sessionId','If-Match','Idempotency-Key','X-RackClick-Actor','X-RackClick-CSRF'}<={p['name'] for p in op['parameters'] if p.get('required')})
        self.assertIn(path+'/operations/{requestId}',doc['paths']);self.assertIn(path+'/operations/{requestId}/cancel',doc['paths'])

    def test_revoke_recovery_fence_cross_intent_current_historical(self):
        self.initialize();user,target=self.add_user('target');sid=self.sid(target);other,alternate=self.add_user('other',admin=True);key=str(uuid.uuid4());revision=self.house_revision();self.customer('Advance')
        self.expect(self.revoke(user,sid,revision,key),412);self.assertEqual(self.outcome(user,sid,key).json()['state'],'notRecorded');now=self.house_revision()
        cancelled=self.expect(self.revoke(user,sid,revision,key,True),200).json();self.assertEqual(cancelled['state'],'cancelled');self.assertEqual(now,self.house_revision());self.expect(target.request('GET','/api/v1/me'),200)
        self.expect(self.revoke(user,sid,revision,key),409,'operation_cancelled');self.assertEqual(self.expect(self.revoke(user,sid,revision,key,True),200).json(),cancelled)
        for changeduser,changedsid,changedrev in ((other,sid,revision),(user,str(uuid.uuid4()),revision),(user,sid,revision+1)):self.expect(self.revoke(changeduser,changedsid,changedrev,key,True),409,'request_id_reused')
        self.assertEqual(self.outcome(other,sid,key).json()['state'],'notRecorded');self.assertEqual(self.outcome(user,str(uuid.uuid4()),key).json()['state'],'notRecorded');self.assertEqual(self.outcome(user,sid,key,alternate).json()['state'],'notRecorded')
        missinguser=str(uuid.uuid4());missingsid=str(uuid.uuid4());missingkey=str(uuid.uuid4());self.expect(self.revoke(missinguser,missingsid,revision,missingkey,True),200);self.assertEqual(self.outcome(missinguser,missingsid,missingkey).json()['state'],'cancelled')
        revision=self.house_revision();key=str(uuid.uuid4());made=self.expect(self.revoke(user,sid,revision,key),200).json();self.assertEqual(self.outcome(user,sid,key).json()['operation'],made);self.assertEqual(self.revoke(user,sid,revision,key,True).json()['operation'],made)
        self.expect(self.change(user,True,revision,key),409,'request_id_reused');self.assertEqual(self.admin.request('GET',f'/api/v1/admin/users/{user}/state/operations/{key}').json()['state'],'notRecorded')
        # Even the last administrator may revoke its own current session; a different same-actor login survives.
        self.lab.sql(self.db,f"UPDATE app_user SET active=false WHERE id='{other}'");second=Client(self.server);self.expect(second.login('qa-admin',self.password),200);selected=self.sid(self.admin);revision=self.house_revision();key=str(uuid.uuid4());made=self.expect(self.revoke(self.admin_id,selected,revision,key),200).json();self.assertTrue(made['resource']['wasCurrent'])
        self.expect(self.admin.request('GET','/api/v1/me'),401);self.expect(self.outcome(self.admin_id,selected,key),401);self.expect(second.request('GET','/api/v1/me'),200)
        self.renew();before=self.durable();self.assertEqual(self.outcome(self.admin_id,selected,key).json()['operation'],made);self.assertEqual(self.expect(self.revoke(self.admin_id,selected,revision,key),200).json(),made);self.assertEqual(before,self.durable());self.safe_records()

    def test_revoke_rollback_audit_and_operation_zero_partial_changes(self):
        self.initialize();user,target=self.add_user('target');sid=self.sid(target);revision=self.house_revision();key=str(uuid.uuid4());before=self.durable()
        self.lab.sql(self.db,"""CREATE FUNCTION reject_revoke_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action LIKE 'user.session.revoke%' THEN RAISE EXCEPTION 'synthetic audit failure'; END IF; RETURN NEW; END $$; CREATE TRIGGER reject_revoke_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION reject_revoke_audit();""")
        self.expect(self.revoke(user,sid,revision,key),503);self.assertEqual(before,self.durable());self.expect(target.request('GET','/api/v1/me'),200);self.expect(self.revoke(user,sid,revision,key,True),503);self.assertEqual(before,self.durable());self.assertEqual(self.outcome(user,sid,key).json()['state'],'notRecorded')
        self.lab.sql(self.db,"DROP TRIGGER reject_revoke_audit ON audit_event; CREATE FUNCTION reject_revoke_operation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic operation failure'; END $$; CREATE TRIGGER reject_revoke_operation BEFORE INSERT ON operation FOR EACH ROW EXECUTE FUNCTION reject_revoke_operation();")
        self.expect(self.revoke(user,sid,revision,key),503);self.assertEqual(before,self.durable());self.expect(target.request('GET','/api/v1/me'),200)
        self.lab.sql(self.db,'DROP TRIGGER reject_revoke_operation ON operation');self.expect(self.revoke(user,sid,revision,key),200)

    def test_revoke_concurrency_same_key_cancel_and_new_login(self):
        self.initialize();user,target=self.add_user('target');sid=self.sid(target);revision=self.house_revision();key=str(uuid.uuid4())
        with ThreadPoolExecutor(2) as pool:
            a=pool.submit(self.revoke,user,sid,revision,key);b=pool.submit(self.revoke,user,sid,revision,key);made=self.expect(a.result(),200).json();self.assertEqual(made,self.expect(b.result(),200).json())
        self.assertEqual(self.house_revision(),revision+1);self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM audit_event WHERE action='user.session.revoke'"),'1')
        self.expect(target.login('target',self.password),200);sid=self.sid(target);new=Client(self.server);revision=self.house_revision()
        with self.user_lock(user) as (blocker,pid),ThreadPoolExecutor(2) as pool:
            login=pool.submit(new.login,'target',self.password);revoke=pool.submit(self.revoke,user,sid,revision)
            try:
                self.wait_for_user_waiter(pid,'%SELECT id,password_hash,active%');self.wait_for_user_waiter(pid,'%SELECT id FROM app_user%FOR UPDATE%');self.assertFalse(login.done());self.assertFalse(revoke.done())
            finally:blocker.stdin.write('COMMIT;\n');blocker.stdin.flush()
            self.expect(login.result(timeout=10),200);self.expect(revoke.result(timeout=10),200)
        self.expect(target.request('GET','/api/v1/me'),401);self.expect(new.request('GET','/api/v1/me'),200);self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM app_session WHERE user_id='{user}'"),'1')
        sid=self.sid(new);key=str(uuid.uuid4());revision=self.house_revision()
        with ThreadPoolExecutor(2) as pool:
            a=pool.submit(self.revoke,user,sid,revision,key);b=pool.submit(self.revoke,user,sid,revision,key,True);change=a.result();terminal=self.expect(b.result(),200).json()
        if terminal['state']=='committed':self.expect(change,200);self.assertEqual(self.house_revision(),revision+1)
        else:self.expect(change,409,'operation_cancelled');self.assertEqual(self.house_revision(),revision);self.expect(new.request('GET','/api/v1/me'),200)

    @contextmanager
    def session_lock(self,sid):
        env=self.lab.environment();env['PGPASSFILE']=str(self.db.directory/'owner.pgpass')
        process=subprocess.Popen([str(self.lab.pg_bin/'psql.exe'),'-X','-w','-qAt','-v','ON_ERROR_STOP=1','-h','127.0.0.1','-p',str(self.lab.port),'-U',self.db.owner,'-d',self.db.name],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',env=env,creationflags=NO_WINDOW)
        try:
            process.stdin.write(f"BEGIN; SELECT id FROM app_session WHERE id='{sid}' FOR UPDATE; SELECT pg_backend_pid();\n");process.stdin.flush()
            with ThreadPoolExecutor(1) as reader:
                pending=reader.submit(lambda:(process.stdout.readline().strip(),process.stdout.readline().strip()))
                try:locked,pid=pending.result(timeout=8)
                except BaseException:process.kill();raise
            self.assertEqual(locked,sid);self.assertTrue(pid.isdigit());yield process,int(pid)
        finally:
            if process.poll() is None:
                process.stdin.write('ROLLBACK;\n\\q\n');process.stdin.flush()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            for pipe in (process.stdin,process.stdout,process.stderr):pipe.close()

    def test_revoke_waits_expiry_and_permission_after_last_lock(self):
        self.initialize();user,target=self.add_user('target');sid=self.sid(target)
        for kind in ('user','session'):
            self.renew();revision=self.house_revision();self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '3 seconds' WHERE user_id='{self.admin_id}'");before=self.durable()
            lock=self.user_lock(user) if kind=='user' else self.session_lock(sid)
            query='%SELECT id FROM app_user%FOR UPDATE%' if kind=='user' else '%SELECT token_hash=%FROM app_session%FOR UPDATE%'
            with lock as (blocker,pid),ThreadPoolExecutor(1) as pool:
                pending=pool.submit(self.revoke,user,sid,revision)
                try:
                    self.wait_for_user_waiter(pid,query);deadline=time.monotonic()+8
                    while self.lab.sql(self.db,f"SELECT bool_and(expires_at<=clock_timestamp()) FROM app_session WHERE user_id='{self.admin_id}'")!='t':
                        if time.monotonic()>deadline:self.fail('SQL did not observe actor expiry')
                        time.sleep(.025)
                    self.assertFalse(pending.done())
                finally:blocker.stdin.write('COMMIT;\n');blocker.stdin.flush()
                self.expect(pending.result(timeout=10),401,'authentication_required')
            self.assertEqual(before,self.durable())
        self.renew();delegated,actor=self.add_user('delegated');group=self.user_group(delegated);self.grant(group,'security.manage')
        for kind in ('user','session'):
            if kind=='session':self.grant(group,'security.manage')
            revision=self.house_revision();before=self.durable();lock=self.user_lock(user) if kind=='user' else self.session_lock(sid);query='%SELECT id FROM app_user%FOR UPDATE%' if kind=='user' else '%SELECT token_hash=%FROM app_session%FOR UPDATE%'
            with lock as (blocker,pid),ThreadPoolExecutor(1) as pool:
                pending=pool.submit(self.revoke,user,sid,revision,None,False,actor,delegated)
                try:
                    self.wait_for_user_waiter(pid,query);self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability='security.manage'");self.assertFalse(pending.done())
                finally:blocker.stdin.write('COMMIT;\n');blocker.stdin.flush()
                self.expect(pending.result(timeout=10),403,'forbidden')
            self.assertEqual(before,self.durable())
        # Initial actor lock acquisition protects status, cancel, fresh and replay too.
        self.renew();revision=self.house_revision();key=str(uuid.uuid4());made=self.expect(self.revoke(user,sid,revision,key),200).json()
        for kind in ('status','cancel','replay'):
            self.renew();send=(lambda:self.outcome(user,sid,key)) if kind=='status' else (lambda:self.revoke(user,sid,revision,key,kind=='cancel'))
            self.expired_wait(send)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--case',action='append');args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False)
    inputs=[WORKSPACE/'development/server/src/RackClick.Server'/name for name in ('AdminUserSessionRevocation.cs','Program.cs','OpenApiAdmin.cs')]+[Path(__file__).resolve()]
    hashes={str(p.relative_to(WORKSPACE)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs};dllhash=hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest();data={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'dllSha256':dllhash,'sourceHashes':hashes};lab=Lab('admin-session-revoke')
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        SessionRevocationPostgres.lab=lab;names=[n for n in unittest.defaultTestLoader.getTestCaseNames(SessionRevocationPostgres) if n.startswith('test_revoke_') and (not args.case or n in args.case)]
        if not names:raise ValueError('No selected revocation cases')
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(SessionRevocationPostgres(n) for n in names));data.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    data.update(labStopped=not lab.running,inputsUnchanged=dllhash==hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest() and hashes=={str(p.relative_to(WORKSPACE)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');return 0 if result.wasSuccessful() and data['labStopped'] and data['inputsUnchanged'] else 1

if __name__=='__main__':sys.exit(main())
