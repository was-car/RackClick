"""Native PostgreSQL customer-group membership commands; isolated fixtures only."""
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

class CustomerMemberPostgres(FoundationPostgres):
    def member(self, group, customer, assigned, revision=None, key=None, cancel=False, client=None, actor=None, headers=None):
        key=key or str(uuid.uuid4());path=f'/api/v1/admin/customer-groups/{group}/members'
        if cancel:path+=f'/operations/{key}/cancel'
        return (client or self.admin).request('POST',path,{'customerId':customer,'assigned':assigned},
            {'If-Match':f'"{revision if revision is not None else self.house_revision()}"','Idempotency-Key':key,
             'X-RackClick-Actor':actor or self.admin_id,**(headers or {})})

    def status(self,group,key,client=None):
        return (client or self.admin).request('GET',f'/api/v1/admin/customer-groups/{group}/members/operations/{key}')

    def customer_group(self):
        group=str(uuid.uuid4())
        self.lab.sql(self.db,f"INSERT INTO customer_group VALUES('{group}','{self.house}','Synthetic scope')")
        return group

    def test_customer_members_commit_read_write_union_replay(self):
        self.initialize();customer=self.customer('Visible');user,session=self.add_user('scoped');group=self.customer_group()
        users=self.user_group(user);self.grant(users,'inventory.read',customer_group=group);self.grant(users,'customer.manage',customer_group=group);self.grant(users,'inventory.edit',customer_group=group)
        path=f"/api/v1/customers/{customer['id']}";project=path+'/project'
        self.expect(session.request('GET',project),404)
        self.expect(self.mutate(session,'PUT',path,'Denied',1),404)
        revision=self.house_revision();key=str(uuid.uuid4())
        first=self.expect(self.member(group,customer['id'],True,revision,key),200).json()
        self.assertEqual(first['resource'],{'groupId':group,'customerId':customer['id'],'assigned':True})
        self.expect(session.request('GET',project),200)
        self.expect(self.mutate(session,'PUT',path,'Allowed',1),200)
        def inventory(client,actor,kind,payload):
            current=self.admin.request('GET',project).json()['revision']
            return client.request('POST',path+'/commands',{'type':kind,'payload':payload},
                {'If-Match':f'"{current}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor})
        self.expect(inventory(self.admin,self.admin_id,'site.create',{'name':'Site'}),200)
        site=self.admin.request('GET',project).json()['sites'][0]['id']
        self.expect(inventory(self.admin,self.admin_id,'building.create',{'name':'Building','siteId':site}),200)
        building=self.admin.request('GET',project).json()['buildings'][0]['id']
        self.expect(inventory(self.admin,self.admin_id,'room.create',{'name':'Room','buildingId':building}),200)
        room=self.admin.request('GET',project).json()['rooms'][0]['id']
        self.expect(inventory(session,user,'rack.create',{'name':'Authorized rack','roomId':room,'sizeU':42}),200)
        self.assertEqual(len(self.admin.request('GET',project).json()['racks']),1)
        self.assertEqual(first,self.expect(self.member(group,customer['id'],True,revision,key),200).json())
        self.expect(self.member(group,customer['id'],False,revision,key),409,'request_id_reused')
        self.assertEqual(self.status(group,key).json()['operation'],first)
        before_noop=self.house_revision()
        self.expect(self.member(group,customer['id'],True),200)
        self.assertEqual(self.house_revision(),before_noop+1)
        self.assertEqual(self.lab.sql(self.db,"SELECT before_json->>'assigned' FROM audit_event WHERE action='customerGroup.member.set' ORDER BY occurred_at"),'false\ntrue')
        self.expect(self.member(group,customer['id'],False),200)
        self.expect(session.request('GET',project),404)
        current=self.admin.request('GET',project).json()['revision']
        self.expect(self.mutate(session,'PUT',path,'Denied after removal',current),404)
        before_inventory=self.admin.request('GET',project).json()
        self.expect(inventory(session,user,'rack.create',{'name':'Denied rack','roomId':room,'sizeU':42}),404)
        self.assertEqual(self.admin.request('GET',project).json(),before_inventory)
        other=self.user_group(user,'Union');self.grant(other,'inventory.read',customer=customer['id']);self.grant(other,'customer.manage',customer=customer['id'])
        self.expect(self.member(group,customer['id'],True),200);self.expect(self.member(group,customer['id'],False),200)
        self.expect(session.request('GET',project),200);self.expect(self.mutate(session,'PUT',path,'Union allowed',current),200)
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM customer; SELECT count(*) FROM permission_grant WHERE user_group_id IN ('{users}','{other}')"),'1\n5')

    def test_customer_members_security_targets_and_snapshot(self):
        self.initialize();customer=self.customer('Visible');group=self.customer_group();user,plain=self.add_user('plain')
        key=str(uuid.uuid4());revision=self.house_revision()
        for headers in ({'Origin':'https://invalid.example'},{'X-RackClick-CSRF':'bad'}):
            self.expect(self.member(group,customer['id'],True,revision,key,headers=headers),403)
        self.expect(self.member(group,customer['id'],True,revision,key,client=plain,actor=user),403)
        self.expect(self.member(group,customer['id'],True,revision,key,actor=user),409)
        self.expect(self.member(group,customer['id'],True,revision,key,headers={'X-RackClick-Actor':''}),422)
        scoped=self.user_group(user);self.grant(scoped,'security.manage',customer=customer['id'])
        self.expect(self.member(group,customer['id'],True,revision,key,client=plain,actor=user),403)
        self.expect(plain.request('GET','/api/v1/admin/customers'),403)
        self.expect(self.member(str(uuid.uuid4()),customer['id'],True,revision),404)
        self.expect(self.member(group,str(uuid.uuid4()),True,revision),404)
        self.expect(self.member(group,customer['id'],None,revision),422,'member_invalid')
        security,security_session=self.add_user('security-only');sg=self.user_group(security);self.grant(sg,'security.manage')
        before=self.lab.sql(self.db,'SELECT revision FROM systemhaus; SELECT count(*) FROM audit_event')
        snapshot=self.expect(security_session.request('GET','/api/v1/admin/customers'),200).json()
        self.assertEqual(snapshot,{'revision':revision,'customers':[{'id':customer['id'],'name':'Visible'}]})
        self.expect(security_session.request('GET',f"/api/v1/customers/{customer['id']}/project"),404)
        self.assertEqual(before,self.lab.sql(self.db,'SELECT revision FROM systemhaus; SELECT count(*) FROM audit_event'))
        self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{sg}'")
        self.expect(security_session.request('GET','/api/v1/admin/customers'),403)
        doc=self.admin.request('GET','/api/v1/openapi.json').json()
        post=doc['paths']['/api/v1/admin/customer-groups/{groupId}/members']['post']
        self.assertTrue({'groupId','If-Match','Idempotency-Key','X-RackClick-Actor','X-RackClick-CSRF'} <= {p['name'] for p in post['parameters'] if p.get('required')})
        self.assertIn('/api/v1/admin/customers',doc['paths'])

    def test_customer_members_status_actor_group_action(self):
        self.initialize();customer=self.customer('Visible');group=self.customer_group();other=self.customer_group();second,session=self.add_user('second',admin=True)
        key=str(uuid.uuid4());revision=self.house_revision()
        made=self.expect(self.member(group,customer['id'],True,revision,key),200).json()
        self.assertEqual(self.status(other,key).json()['state'],'notRecorded')
        self.assertEqual(self.status(group,key,session).json()['state'],'notRecorded')
        self.assertEqual(self.admin.request('GET',f'/api/v1/admin/user-groups/{group}/members/operations/{key}').json()['state'],'notRecorded')
        self.expect(self.member(other,customer['id'],True,revision,key),409,'request_id_reused')
        response=self.admin.request('POST',f'/api/v1/admin/user-groups/{group}/members',{'userId':self.admin_id,'assigned':True},
            {'If-Match':f'"{revision}"','Idempotency-Key':key,'X-RackClick-Actor':self.admin_id})
        self.expect(response,409,'request_id_reused')
        self.assertEqual(self.expect(self.member(group,customer['id'],True,revision,key,cancel=True),200).json()['operation'],made)
        self.assertEqual(self.lab.sql(self.db,f"SELECT revision FROM customer WHERE id='{customer['id']}'"),'1')

    def test_customer_members_stale_fence_missing_targets_late(self):
        self.initialize();customer=self.customer('Visible');group=self.customer_group();revision=self.house_revision();key=str(uuid.uuid4())
        self.customer('Advance');self.expect(self.member(group,customer['id'],True,revision,key),412)
        terminal=self.expect(self.member(group,customer['id'],True,revision,key,cancel=True),200).json()
        self.assertEqual(terminal['state'],'cancelled')
        self.expect(self.member(group,customer['id'],True,revision,key),409,'operation_cancelled')
        self.assertEqual(self.expect(self.member(group,customer['id'],True,revision,key,cancel=True),200).json(),terminal)
        missing=str(uuid.uuid4());target=str(uuid.uuid4());missingkey=str(uuid.uuid4())
        self.expect(self.member(missing,target,False,revision,missingkey,cancel=True),200)
        self.expect(self.member(missing,target,False,revision,missingkey),409,'operation_cancelled')
        self.assertEqual(self.house_revision(),revision+1)
        self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM customer_group_member'),'0')

    def test_customer_members_audit_rollback_concurrent_exact(self):
        from concurrent.futures import ThreadPoolExecutor
        self.initialize();customer=self.customer('Visible');group=self.customer_group();revision=self.house_revision();key=str(uuid.uuid4())
        baseline=self.lab.sql(self.db,'SELECT count(*) FROM operation; SELECT count(*) FROM audit_event')
        self.lab.sql(self.db,"""CREATE FUNCTION reject_member_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
            IF NEW.action LIKE 'customerGroup.member.set%' THEN RAISE EXCEPTION 'synthetic audit failure'; END IF; RETURN NEW; END $$;
            CREATE TRIGGER reject_member_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION reject_member_audit();""")
        self.expect(self.member(group,customer['id'],True,revision,key),503)
        self.expect(self.member(group,customer['id'],True,revision,key,cancel=True),503)
        self.assertEqual(self.house_revision(),revision)
        self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM operation; SELECT count(*) FROM audit_event'),baseline)
        self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM customer_group_member'),'0')
        self.lab.sql(self.db,'DROP TRIGGER reject_member_audit ON audit_event')
        with ThreadPoolExecutor(2) as pool:
            first=pool.submit(self.member,group,customer['id'],True,revision,key)
            second=pool.submit(self.member,group,customer['id'],True,revision,key)
            self.assertEqual(self.expect(first.result(),200).json(),self.expect(second.result(),200).json())
        self.assertEqual(self.house_revision(),revision+1)
        self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM audit_event WHERE action='customerGroup.member.set'"),'1')
        race=str(uuid.uuid4());now=self.house_revision()
        with ThreadPoolExecutor(2) as pool:
            made=pool.submit(self.member,group,customer['id'],False,now,race)
            stopped=pool.submit(self.member,group,customer['id'],False,now,race,True)
            change,cancel=made.result(),self.expect(stopped.result(),200).json()
        if cancel['state']=='committed':self.expect(change,200);self.assertEqual(self.house_revision(),now+1)
        else:self.expect(change,409,'operation_cancelled');self.assertEqual(self.house_revision(),now)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=False)
    data={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'dllSha256':hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()}
    lab=Lab('admin-customer-members')
    with lab, (args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        CustomerMemberPostgres.lab=lab
        names=[n for n in unittest.defaultTestLoader.getTestCaseNames(CustomerMemberPostgres) if n.startswith('test_customer_members_')]
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(CustomerMemberPostgres(n) for n in names))
        data.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    data.update(labStopped=not lab.running,inputsUnchanged=data['dllSha256']==hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest())
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    return 0 if result.wasSuccessful() and data['labStopped'] and data['inputsUnchanged'] else 1

if __name__=='__main__':sys.exit(main())
