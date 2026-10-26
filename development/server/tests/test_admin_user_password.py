"""Isolated Windows PostgreSQL password reset; passwords remain local to the fixture."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import secrets
import sys
import time
import unittest
import uuid
from pg_support import DEFAULT_DLL, Lab, Client
from test_postgres import EvidenceResult, Tee
from test_admin_user_state import UserStatePostgres


class UserPasswordPostgres(UserStatePostgres):
    def reset(self,user,password=None,revision=None,key=None,cancel=False,client=None,actor=None,headers=None,payload=None):
        key=key or str(uuid.uuid4());path=f'/api/v1/admin/users/{user}/password'
        if cancel:path+=f'/operations/{key}/cancel'
        body=({} if cancel else {'password':password}) if payload is None else payload
        return (client or self.admin).request('POST',path,body,
            {'If-Match':f'"{revision if revision is not None else self.house_revision()}"','Idempotency-Key':key,
             'X-RackClick-Actor':actor or self.admin_id,**(headers or {})})

    def outcome(self,user,key,client=None):
        return (client or self.admin).request('GET',f'/api/v1/admin/users/{user}/password/operations/{key}')

    def safe_durable(self,passwords):
        text=self.lab.sql(self.db,'SELECT row_to_json(a)::text FROM audit_event a; SELECT row_to_json(o)::text FROM operation o')
        self.assertTrue(all(secret not in text for secret in passwords),'Durable administrative records must exclude secrets')
        self.assertTrue(all(field not in text for field in ('password_hash','token_hash','csrf_hash','failed_logins','locked_until')),'Durable records contain public fields only')
        self.assertEqual(self.lab.sql(self.db,"SELECT bool_and((SELECT count(*)=3 FROM jsonb_object_keys(a.before_json)) AND a.before_json ?& ARRAY['id','userName','active'] AND (SELECT count(*)=4 FROM jsonb_object_keys(a.after_json)) AND a.after_json ?& ARRAY['id','userName','active','passwordReset']) FROM audit_event a WHERE action='user.password.reset'"),'t')

    def test_password_sessions_persistence_lockout_inactive_and_replay(self):
        self.initialize();user,first=self.add_user('target');second=Client(self.server);self.expect(second.login('target',self.password),200)
        group=self.user_group(user);self.grant(group,'systemhaus.read')
        invariant=self.lab.sql(self.db,f"SELECT id,username,active FROM app_user WHERE id='{user}'; SELECT count(*) FROM user_group_member WHERE user_id='{user}'; SELECT count(*) FROM permission_grant")
        oldhash=self.lab.sql(self.db,f"SELECT md5(password_hash) FROM app_user WHERE id='{user}'")
        self.lab.sql(self.db,f"UPDATE app_user SET failed_logins=8,locked_until=now()+interval '1 hour' WHERE id='{user}'")
        new=secrets.token_urlsafe(32);revision=self.house_revision();key=str(uuid.uuid4());made=self.expect(self.reset(user,new,revision,key),200).json()
        self.assertEqual(made,{'resource':{'id':user,'userName':'target','active':True,'passwordReset':True},'systemhausRevision':revision+1,'requestId':key})
        public=json.dumps({'action':'user.password.reset','userId':user,'expected':revision},separators=(',',':'))
        self.assertEqual(self.lab.sql(self.db,f"SELECT request_hash FROM operation WHERE request_id='{key}'"),hashlib.sha256(public.encode()).hexdigest().upper(),'Digest contains public intent only')
        for session in (first,second):self.expect(session.request('GET','/api/v1/me'),401)
        self.assertEqual(self.lab.sql(self.db,f"SELECT failed_logins,locked_until IS NULL,(SELECT count(*) FROM app_session WHERE user_id='{user}') FROM app_user WHERE id='{user}'"),'0|t|0')
        self.assertNotEqual(oldhash,self.lab.sql(self.db,f"SELECT md5(password_hash) FROM app_user WHERE id='{user}'"))
        self.assertEqual(invariant,self.lab.sql(self.db,f"SELECT id,username,active FROM app_user WHERE id='{user}'; SELECT count(*) FROM user_group_member WHERE user_id='{user}'; SELECT count(*) FROM permission_grant"))
        self.server.close();self.server=self.lab.start_server(self.db);self.admin=Client(self.server);self.expect(self.admin.login('qa-admin',self.password),200)
        self.expect(Client(self.server).login('target',self.password),401);fresh=Client(self.server);self.expect(fresh.login('target',new),200)
        before=self.snapshot();self.assertEqual(self.expect(self.reset(user,new,revision,key),200).json(),made);self.assertEqual(before,self.snapshot());self.expect(fresh.request('GET','/api/v1/me'),200)
        self.expect(self.reset(user,secrets.token_urlsafe(32),revision,key),409,'request_id_reused')
        # Same current password still performs a fresh reset, salting again and revoking new sessions.
        self.expect(self.reset(user,new),200);self.expect(fresh.request('GET','/api/v1/me'),401)
        later=secrets.token_urlsafe(32);self.expect(self.reset(user,later),200);before=self.snapshot()
        self.expect(self.reset(user,new,revision,key),409,'request_id_reused');self.assertEqual(self.outcome(user,key).json()['operation'],made);self.assertEqual(before,self.snapshot())
        self.lab.sql(self.db,f"UPDATE app_user SET active=false,failed_logins=9,locked_until=now()+interval '1 hour' WHERE id='{user}'")
        inactive=secrets.token_urlsafe(32);self.expect(self.reset(user,inactive),200)
        self.assertEqual(self.lab.sql(self.db,f"SELECT active,failed_logins,locked_until IS NULL FROM app_user WHERE id='{user}'"),'f|0|t')
        self.expect(Client(self.server).login('target',inactive),401)
        self.safe_durable([self.password,new,later,inactive])

    def test_password_unicode_utf16_limits_without_trimming(self):
        self.initialize();user,_=self.add_user('unicode')
        # Prefixes are random for these fixtures; supplementary chars count as TWO UTF-16 units.
        marker=secrets.token_hex(4)
        values=['\U0001f680'*8,'\U0001f680'*512,marker+'🚀'*4,marker+'a'*1016,' '+marker+'é́🚀    ']
        for value in values:
            self.expect(self.reset(user,value),200);self.expect(Client(self.server).login('unicode',value),200)
        spaced=values[-1];self.expect(Client(self.server).login('unicode',spaced.strip()),401)
        before=self.snapshot()
        for value in (None,'\U0001f680'*513,marker+'a'*7,marker+'🚀'*508+'a'):
            self.expect(self.reset(user,value),422,'password_length')
        self.expect(self.reset(user,payload={}),422,'password_length');self.assertEqual(before,self.snapshot())
        self.safe_durable([self.password,*values])

    def test_password_security_headers_scopes_ids_openapi(self):
        self.initialize();user,plain=self.add_user('scoped');group=self.user_group(user);customer=self.customer('Scope');cg=self.customer_group()
        self.grant(group,'security.manage',customer=customer['id']);self.grant(group,'security.manage',customer_group=cg)
        new=secrets.token_urlsafe(32)
        self.expect(self.reset(user,new,client=plain,actor=user),403);self.expect(self.outcome(user,str(uuid.uuid4()),plain),403)
        self.expect(self.reset(user,key=str(uuid.uuid4()),cancel=True,client=plain,actor=user),403)
        anonymous=Client(self.server);self.expect(self.reset(user,new,revision=self.house_revision(),client=anonymous),401)
        for headers,status in [({'Origin':'https://invalid.example'},403),({'X-RackClick-CSRF':'bad'},403),({'X-RackClick-Actor':''},422),({'X-RackClick-Actor':user},409),({'If-Match':''},428),({'Idempotency-Key':''},422)]:
            self.expect(self.reset(user,new,headers=headers),status)
        self.expect(self.reset(str(uuid.UUID(int=0)),new),422);self.expect(self.reset(str(uuid.uuid4()),new),404)
        self.expect(self.reset(user,key=str(uuid.uuid4()),cancel=True,payload=[]),422)
        self.expect(self.reset(user,key=str(uuid.uuid4()),cancel=True,headers={'Idempotency-Key':str(uuid.uuid4())}),422,'request_id_mismatch')
        self.lab.sql(self.db,'DROP INDEX one_systemhaus_per_installation');house=str(uuid.uuid4());foreign=str(uuid.uuid4())
        self.lab.sql(self.db,f"INSERT INTO systemhaus(id,name) VALUES('{house}','Foreign synthetic'); INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{foreign}','{house}','foreign',password_hash FROM app_user WHERE id='{user}'")
        self.expect(self.reset(foreign,new),404)
        doc=self.admin.request('GET','/api/v1/openapi.json').json();op=doc['paths']['/api/v1/admin/users/{userId}/password']['post']
        self.assertTrue({'userId','If-Match','Idempotency-Key','X-RackClick-Actor','X-RackClick-CSRF'}<={p['name'] for p in op['parameters'] if p.get('required')})
        schema=doc['components']['schemas']['ResetUserPassword'];self.assertEqual(schema['required'],['password']);field=schema['properties']['password']
        self.assertEqual((field['x-rackclick-min-utf16-length'],field['x-rackclick-max-utf16-length'],field['writeOnly']),(16,1024,True));self.assertNotIn('minLength',field);self.assertNotIn('maxLength',field)
        self.assertEqual(doc['components']['schemas']['CancelUserPasswordReset']['required'],[])

    def test_password_status_fence_cross_intent_and_self_reset(self):
        self.initialize();user,_=self.add_user('target');other,session=self.add_user('other',admin=True);new=secrets.token_urlsafe(32);revision=self.house_revision();key=str(uuid.uuid4());self.customer('Advance')
        self.expect(self.reset(user,new,revision,key),412);self.assertEqual(self.outcome(user,key).json()['state'],'notRecorded')
        before=self.snapshot();cancelled=self.expect(self.reset(user,revision=revision,key=key,cancel=True),200).json();self.assertEqual(cancelled['state'],'cancelled')
        self.assertEqual(self.house_revision(),revision+1)
        self.expect(self.reset(user,new,revision,key),409,'operation_cancelled');self.expect(self.reset(user,secrets.token_urlsafe(32),revision,key),409,'operation_cancelled')
        self.assertEqual(self.expect(self.reset(user,revision=revision,key=key,cancel=True),200).json(),cancelled)
        self.expect(self.reset(other,revision=revision,key=key,cancel=True),409,'request_id_reused');self.expect(self.reset(user,revision=revision+1,key=key,cancel=True),409,'request_id_reused')
        self.assertEqual(self.outcome(other,key).json()['state'],'notRecorded');self.assertEqual(self.outcome(user,key,session).json()['state'],'notRecorded')
        self.assertEqual(self.admin.request('GET',f'/api/v1/admin/users/{user}/state/operations/{key}').json()['state'],'notRecorded')
        self.expect(self.reset(str(uuid.uuid4()),revision=revision,key=str(uuid.uuid4()),cancel=True),200)
        key=str(uuid.uuid4());revision=self.house_revision();made=self.expect(self.reset(user,new,revision,key),200).json()
        self.assertEqual(self.expect(self.reset(user,revision=revision,key=key,cancel=True),200).json()['operation'],made)
        self.expect(self.change(user,True,revision,key),409,'request_id_reused')
        self.assertEqual(self.outcome(user,key).json()['operation'],made)
        # Last administrator can reset own password without changing active or grants.
        self.lab.sql(self.db,f"UPDATE app_user SET active=false WHERE id='{other}'")
        own=secrets.token_urlsafe(32);key=str(uuid.uuid4());revision=self.house_revision();made=self.expect(self.reset(self.admin_id,own,revision,key),200).json();self.expect(self.admin.request('GET','/api/v1/me'),401)
        fresh=Client(self.server);self.expect(fresh.login('qa-admin',own),200);self.assertEqual(self.outcome(self.admin_id,key,fresh).json()['operation'],made)
        self.expect(fresh.request('GET','/api/v1/admin/users'),200)
        self.safe_durable([self.password,new,own])

    def test_password_audit_rollback_exact_concurrency_login_and_cancel(self):
        self.initialize();user,session=self.add_user('target');self.lab.sql(self.db,f"UPDATE app_user SET failed_logins=7,locked_until=now()+interval '1 hour' WHERE id='{user}'")
        new=secrets.token_urlsafe(32);revision=self.house_revision();key=str(uuid.uuid4());before=self.snapshot()
        self.lab.sql(self.db,"""CREATE FUNCTION reject_password_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
          IF NEW.action LIKE 'user.password.reset%' THEN RAISE EXCEPTION 'synthetic audit failure'; END IF; RETURN NEW; END $$;
          CREATE TRIGGER reject_password_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION reject_password_audit();""")
        self.expect(self.reset(user,new,revision,key),503);self.assertEqual(before,self.snapshot());self.expect(session.request('GET','/api/v1/me'),200)
        self.expect(self.reset(user,revision=revision,key=key,cancel=True),503);self.assertEqual(before,self.snapshot())
        self.lab.sql(self.db,'DROP TRIGGER reject_password_audit ON audit_event')
        with ThreadPoolExecutor(2) as pool:
            a=pool.submit(self.reset,user,new,revision,key);b=pool.submit(self.reset,user,new,revision,key)
            self.assertEqual(self.expect(a.result(),200).json(),self.expect(b.result(),200).json())
        self.assertEqual(self.house_revision(),revision+1);self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM audit_event WHERE action='user.password.reset'"),'1')
        nextpw=secrets.token_urlsafe(32);fresh=Client(self.server);now=self.house_revision()
        with self.user_lock(user) as (blocker,pid),ThreadPoolExecutor(2) as pool:
            login=pool.submit(fresh.login,'target',new);reset=pool.submit(self.reset,user,nextpw,now)
            try:
                self.wait_for_user_waiter(pid,'%SELECT id,password_hash,active%');self.wait_for_user_waiter(pid,'%SELECT id,username,active,password_hash FROM app_user%FOR UPDATE%')
                self.assertFalse(login.done());self.assertFalse(reset.done())
            finally:blocker.stdin.write('COMMIT;\n');blocker.stdin.flush()
            self.expect(reset.result(timeout=10),200);self.assertIn(login.result(timeout=10).status,(200,401))
        self.expect(fresh.request('GET','/api/v1/me'),401);self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM app_session WHERE user_id='{user}'"),'0')
        race=str(uuid.uuid4());now=self.house_revision();racepw=secrets.token_urlsafe(32)
        with ThreadPoolExecutor(2) as pool:
            a=pool.submit(self.reset,user,racepw,now,race);b=pool.submit(self.reset,user,None,now,race,True)
            change=a.result();terminal=self.expect(b.result(),200).json()
        if terminal['state']=='committed':self.expect(change,200);self.assertEqual(self.house_revision(),now+1)
        else:self.expect(change,409,'operation_cancelled');self.assertEqual(self.house_revision(),now)
        self.safe_durable([self.password,new,nextpw,racepw])

    def test_password_waiting_revocation_and_expiry_on_fresh_and_replay(self):
        self.initialize();user,session=self.add_user('delegated');group=self.user_group(user);self.grant(group,'security.manage');target,_=self.add_user('target');new=secrets.token_urlsafe(32)
        for kind in ('reset','replay','cancel'):
            if kind!='reset':self.grant(group,'security.manage')
            revision=self.house_revision();key=str(uuid.uuid4())
            if kind=='replay':self.expect(self.reset(target,new,revision,key,client=session,actor=user),200)
            before=self.snapshot()
            with self.house_lock() as (blocker,pid),ThreadPoolExecutor(1) as pool:
                pending=pool.submit(self.reset,target,new,revision,key,kind=='cancel',session,user)
                try:
                    self.wait_for_house_waiter(pid);self.assertFalse(pending.done());self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability='security.manage'")
                finally:blocker.stdin.write('COMMIT;\n');blocker.stdin.flush()
                self.expect(pending.result(timeout=10),403,'forbidden')
            self.assertEqual(before,self.snapshot());self.expect(self.outcome(target,key,session),403)
        # Real expiry while blocked on final target lock, including completed replay.
        for replay in (False,True):
            self.admin=Client(self.server);self.expect(self.admin.login('qa-admin',self.password),200)
            revision=self.house_revision();key=str(uuid.uuid4())
            if replay:self.expect(self.reset(target,new,revision,key),200)
            self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '3 seconds' WHERE user_id='{self.admin_id}'")
            before=self.snapshot()
            with self.user_lock(target) as (blocker,pid),ThreadPoolExecutor(1) as pool:
                pending=pool.submit(self.reset,target,new,revision,key)
                try:
                    self.wait_for_user_waiter(pid,'%SELECT id,username,active,password_hash FROM app_user%FOR UPDATE%')
                    deadline=time.monotonic()+8
                    while self.lab.sql(self.db,f"SELECT bool_and(expires_at<=clock_timestamp()) FROM app_session WHERE user_id='{self.admin_id}'")!='t':
                        if time.monotonic()>deadline:self.fail('Actor session did not expire')
                        time.sleep(.025)
                    self.assertFalse(pending.done())
                finally:blocker.stdin.write('COMMIT;\n');blocker.stdin.flush()
                self.expect(pending.result(timeout=10),401,'authentication_required')
            self.assertEqual(before,self.snapshot())

        # The authorization check itself may wait behind actor Login's row lock.
        for kind in ('status','cancel'):
            self.admin=Client(self.server);self.expect(self.admin.login('qa-admin',self.password),200)
            revision=self.house_revision();key=str(uuid.uuid4())
            self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '3 seconds' WHERE user_id='{self.admin_id}'")
            before=self.snapshot()
            with self.user_lock(self.admin_id) as (blocker,pid),ThreadPoolExecutor(1) as pool:
                pending=pool.submit(self.outcome,target,key) if kind=='status' else pool.submit(self.reset,target,None,revision,key,True)
                try:
                    self.wait_for_user_waiter(pid,'%SELECT s.token_hash FROM app_session%FOR SHARE%')
                    deadline=time.monotonic()+8
                    while self.lab.sql(self.db,f"SELECT bool_and(expires_at<=clock_timestamp()) FROM app_session WHERE user_id='{self.admin_id}'")!='t':
                        if time.monotonic()>deadline:self.fail('Actor session did not expire behind actor row lock')
                        time.sleep(.025)
                    self.assertFalse(pending.done())
                finally:blocker.stdin.write('COMMIT;\n');blocker.stdin.flush()
                self.expect(pending.result(timeout=10),401,'authentication_required')
            self.assertEqual(before,self.snapshot())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--case',action='append');args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[3];inputs=[root/'development/server/src/RackClick.Server'/name for name in ('AdminUserPassword.cs','Program.cs','OpenApiAdmin.cs')]+[Path(__file__).resolve()]
    hashes={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    data={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'dllSha256':hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest(),'sourceHashes':hashes};lab=Lab('admin-user-password')
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        UserPasswordPostgres.lab=lab;names=[n for n in unittest.defaultTestLoader.getTestCaseNames(UserPasswordPostgres) if n.startswith('test_password_') and (not args.case or n in args.case)]
        if not names:raise ValueError('No selected password reset cases')
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(UserPasswordPostgres(n) for n in names));data.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    data.update(labStopped=not lab.running,inputsUnchanged=data['dllSha256']==hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest() and hashes=={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2),encoding='utf-8');return 0 if result.wasSuccessful() and data['labStopped'] and data['inputsUnchanged'] else 1

if __name__=='__main__':sys.exit(main())
