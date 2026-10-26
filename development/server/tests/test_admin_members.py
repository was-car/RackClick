"""Scoped native PostgreSQL evidence for user group membership commands."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import unittest
import uuid
from pg_support import DEFAULT_DLL, Lab, Client
from test_postgres import FoundationPostgres, EvidenceResult, Tee


class MemberPostgres(FoundationPostgres):
    def member(self, group, user, assigned, revision=None, key=None, cancel=False, client=None, actor=None, headers=None):
        key=key or str(uuid.uuid4());path=f'/api/v1/admin/user-groups/{group}/members'
        if cancel:path+=f'/operations/{key}/cancel'
        return (client or self.admin).request('POST',path,{'userId':user,'assigned':assigned},
            {'If-Match':f'"{revision if revision is not None else self.house_revision()}"','Idempotency-Key':key,
             'X-RackClick-Actor':actor or self.admin_id,**(headers or {})})

    def status(self,group,key,client=None):
        return (client or self.admin).request('GET',f'/api/v1/admin/user-groups/{group}/members/operations/{key}')

    def admin_group(self):
        return self.lab.sql(self.db,f"SELECT group_id FROM user_group_member WHERE user_id='{self.admin_id}'")

    def test_members_commit_immediate_replay_and_noop(self):
        self.initialize();customer=self.customer('Visible');user,session=self.add_user('member')
        holder,_=self.add_user('holder');group=self.user_group(holder);self.grant(group,'inventory.read',customer=customer['id'])
        self.expect(session.request('GET',f"/api/v1/customers/{customer['id']}/project"),404)
        revision=self.house_revision();key=str(uuid.uuid4())
        first=self.expect(self.member(group,user,True,revision,key),200).json()
        self.assertEqual(first['resource'],{'groupId':group,'userId':user,'assigned':True})
        self.expect(session.request('GET',f"/api/v1/customers/{customer['id']}/project"),200)
        self.assertEqual(first,self.expect(self.member(group,user,True,revision,key),200).json())
        self.expect(self.member(group,user,False,revision,key),409,'request_id_reused')
        self.assertEqual(self.status(group,key).json()['operation'],first)
        self.expect(self.member(group,user,True),200)
        self.assertEqual(self.house_revision(),revision+2)
        self.assertEqual(self.lab.sql(self.db,"SELECT before_json->>'assigned' FROM audit_event WHERE action='userGroup.member.set' ORDER BY occurred_at"),'false\ntrue')
        self.expect(self.member(group,user,False),200)
        self.expect(session.request('GET',f"/api/v1/customers/{customer['id']}/project"),404)
        other=self.user_group(user,'Union grant');self.grant(other,'inventory.read',customer=customer['id'])
        self.expect(self.member(group,user,True),200)
        self.expect(self.member(group,user,False),200)
        self.expect(session.request('GET',f"/api/v1/customers/{customer['id']}/project"),200)

    def test_members_security_validation_and_status_scope(self):
        self.initialize();user,plain=self.add_user('plain');group=self.admin_group();key=str(uuid.uuid4());revision=self.house_revision()
        for headers in ({'Origin':'https://invalid.example'},{'X-RackClick-CSRF':'bad'}):
            self.expect(self.member(group,user,True,revision,key,headers=headers),403)
        self.expect(self.member(group,user,True,revision,key,client=plain,actor=user),403)
        self.expect(self.member(group,user,True,revision,key,headers={'X-RackClick-Actor':str(uuid.uuid4())}),409)
        for target in (str(uuid.uuid4()),str(uuid.UUID(int=0))):
            self.expect(self.member(target,user,True,revision),404 if target!=str(uuid.UUID(int=0)) else 422)
        self.expect(self.member(group,str(uuid.uuid4()),True,revision),404)
        self.expect(self.member(group,user,None,revision),422,'member_invalid')
        created=self.expect(self.member(group,user,True,revision,key),200).json()
        othergroup=self.user_group(user,'another');self.assertEqual(self.status(othergroup,key).json()['state'],'notRecorded')
        self.assertEqual(self.status(group,key,plain).json()['state'],'notRecorded')
        self.expect(self.member(othergroup,user,True,revision,key),409,'request_id_reused')
        self.assertEqual(self.expect(self.member(group,user,True,revision,key,cancel=True),200).json()['operation'],created)
        doc=self.admin.request('GET','/api/v1/openapi.json').json()
        post=doc['paths']['/api/v1/admin/user-groups/{groupId}/members']['post']
        self.assertTrue({'groupId','If-Match','Idempotency-Key','X-RackClick-Actor','X-RackClick-CSRF'}<= {p['name'] for p in post['parameters'] if p.get('required')})

    def test_members_last_active_global_admin_and_self_removal(self):
        self.initialize();group=self.admin_group();revision=self.house_revision()
        inactive,_=self.add_user('inactive-admin',admin=True)
        self.lab.sql(self.db,f"UPDATE app_user SET active=false WHERE id='{inactive}'")
        scoped,session=self.add_user('scoped-admin');sg=self.user_group(scoped);customer=self.customer('Scope');self.grant(sg,'security.manage',customer=customer['id'])
        revision=self.house_revision();key=str(uuid.uuid4())
        self.expect(self.member(group,self.admin_id,False,revision,key),409,'last_admin_required')
        self.assertEqual(self.house_revision(),revision)
        self.assertEqual(self.status(group,key).json()['state'],'notRecorded')
        second,secondsession=self.add_user('second-admin',admin=True)
        self.expect(self.member(group,self.admin_id,False,revision,key),200)
        self.expect(self.member(group,self.admin_id,False,revision,key),403)
        self.expect(self.admin.request('GET','/api/v1/admin/users'),403)
        self.expect(secondsession.request('GET','/api/v1/admin/users'),200)
        # Inactive membership can be assigned without reviving the account.
        self.expect(self.member(sg,inactive,True,revision+1,client=secondsession,actor=second),200)
        self.assertEqual(self.lab.sql(self.db,f"SELECT active FROM app_user WHERE id='{inactive}'"),'f')

    def test_members_stale_cancellation_missing_targets_and_late(self):
        self.initialize();user,_=self.add_user('member');group=self.admin_group();revision=self.house_revision();key=str(uuid.uuid4())
        self.customer('Advance');self.expect(self.member(group,user,True,revision,key),412)
        terminal=self.expect(self.member(group,user,True,revision,key,cancel=True),200).json()
        self.assertEqual(terminal['state'],'cancelled')
        self.expect(self.member(group,user,True,revision,key),409,'operation_cancelled')
        self.assertEqual(self.expect(self.member(group,user,True,revision,key,cancel=True),200).json(),terminal)
        missing=str(uuid.uuid4());missinguser=str(uuid.uuid4());otherkey=str(uuid.uuid4())
        self.expect(self.member(missing,missinguser,False,revision,otherkey,cancel=True),200)
        self.expect(self.member(missing,missinguser,False,revision,otherkey),409,'operation_cancelled')
        self.assertEqual(self.house_revision(),revision+1)

    def test_members_audit_rollback_conflict_and_concurrent(self):
        from concurrent.futures import ThreadPoolExecutor
        self.initialize();user,_=self.add_user('member');group=self.admin_group();revision=self.house_revision();key=str(uuid.uuid4())
        self.lab.sql(self.db,"""CREATE FUNCTION reject_member_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
            IF NEW.action LIKE 'userGroup.member.set%' THEN RAISE EXCEPTION 'synthetic audit failure'; END IF; RETURN NEW; END $$;
            CREATE TRIGGER reject_member_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION reject_member_audit();""")
        self.expect(self.member(group,user,True,revision,key),503)
        self.expect(self.member(group,user,True,revision,key,cancel=True),503)
        self.assertEqual(self.house_revision(),revision)
        self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM operation; SELECT count(*) FROM audit_event; SELECT count(*) FROM user_group_member;'),'0\n0\n1')
        self.lab.sql(self.db,'DROP TRIGGER reject_member_audit ON audit_event')
        with ThreadPoolExecutor(2) as pool:
            made=pool.submit(self.member,group,user,True,revision,key)
            stopped=pool.submit(self.member,group,user,True,revision,key,True)
            create,cancel=made.result(),self.expect(stopped.result(),200).json()
        if cancel['state']=='committed':self.expect(create,200);self.assertEqual(self.house_revision(),revision+1)
        else:self.expect(create,409,'operation_cancelled');self.assertEqual(self.house_revision(),revision)
        self.customer('Advance');self.expect(self.member(group,user,False,revision),412)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=False)
    data={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'dllSha256':hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()}
    lab=Lab('admin-members')
    with lab, (args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        MemberPostgres.lab=lab
        names=[n for n in unittest.defaultTestLoader.getTestCaseNames(MemberPostgres) if n.startswith('test_members_')]
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(MemberPostgres(n) for n in names))
        data.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    data.update(labStopped=not lab.running,inputsUnchanged=data['dllSha256']==hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest())
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    return 0 if result.wasSuccessful() and data['labStopped'] and data['inputsUnchanged'] else 1

if __name__=='__main__':sys.exit(main())
