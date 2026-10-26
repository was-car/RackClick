"""Native PostgreSQL tests for the first administrative user routes. No real accounts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import secrets
import sys
import unittest
import uuid
from pg_support import Client, DEFAULT_DLL, Lab, WORKSPACE, literal
from test_postgres import FoundationPostgres, EvidenceResult, Tee


class AdminPostgres(FoundationPostgres):
    def group_write(self,kind,name,revision,key=None,cancel=False,client=None,headers=None):
        key=key or str(uuid.uuid4());path=f'/api/v1/admin/{kind}-groups'
        if cancel:path+=f'/operations/{key}/cancel'
        return (client or self.admin).request('POST',path,{'name':name},
            {'If-Match':f'"{revision}"','Idempotency-Key':key,'X-RackClick-Actor':self.admin_id,**(headers or {})})

    def test_admin_groupwrites_create_replay_empty_and_unicode(self):
        self.initialize();members=self.lab.sql(self.db,'SELECT count(*) FROM user_group_member; SELECT count(*) FROM permission_grant;')
        for kind in ('user','customer'):
            revision=self.house_revision();key=str(uuid.uuid4());name='  Techniker 東京 '+'\U0001f680'*87+'  '
            first=self.expect(self.group_write(kind,name,revision,key),201).json()
            self.assertEqual(first['resource']['name'],name.strip())
            self.assertEqual(first['resource']['kind'],kind+'Group')
            self.assertEqual(first,self.expect(self.group_write(kind,name,revision,key),201).json())
            self.expect(self.group_write(kind,'changed',revision,key),409,'request_id_reused')
            self.assertEqual(self.house_revision(),revision+1)
            groups=self.admin.request('GET',f'/api/v1/admin/{kind}-groups').json()['groups']
            group=next(g for g in groups if g['id']==first['resource']['id'])
            self.assertEqual(group['members' if kind=='user' else 'customers'],[])
            if kind=='user':self.assertEqual(group['grants'],[])
            self.expect(self.group_write(kind,'\U0001f680'*101,self.house_revision()),422,'name_invalid')
        self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM user_group_member; SELECT count(*) FROM permission_grant;'),members)

    def test_admin_groupwrites_cancel_stale_invalid_and_late(self):
        self.initialize()
        for kind in ('user','customer'):
            old=self.house_revision();key=str(uuid.uuid4())
            self.expect(self.group_write(kind,'Advance',old),201)
            self.expect(self.group_write(kind,'Never created',old,key),412)
            terminal=self.expect(self.group_write(kind,'Never created',old,key,cancel=True),200).json()
            self.assertEqual(terminal['state'],'cancelled')
            self.assertEqual(self.admin.request('GET',f'/api/v1/admin/{kind}-groups/operations/{key}').json(),terminal)
            self.expect(self.group_write(kind,'Never created',old,key),409,'operation_cancelled')
            self.assertEqual(self.expect(self.group_write(kind,'Never created',old,key,cancel=True),200).json(),terminal)
            invalid=str(uuid.uuid4());self.expect(self.group_write(kind,'   ',old,invalid),422,'name_required')
            self.assertEqual(self.expect(self.group_write(kind,'   ',old,invalid,cancel=True),200).json()['state'],'cancelled')
            self.expect(self.group_write(kind,'Valid',old,invalid),409,'request_id_reused')
            self.assertEqual(self.house_revision(),old+1)

    def test_admin_groupwrites_security_actor_scope_and_kind(self):
        self.initialize();revision=self.house_revision();key=str(uuid.uuid4())
        self.expect(self.group_write('user','X',revision,key,headers={'X-RackClick-CSRF':'bad'}),403)
        self.expect(self.group_write('user','X',revision,key,headers={'Origin':'https://invalid.example'}),403)
        self.expect(self.group_write('user','X',revision,key,headers={'X-RackClick-Actor':str(uuid.uuid4())}),409)
        self.expect(self.group_write('user','X',revision,key,headers={'X-RackClick-Actor':''}),422)
        first=self.expect(self.group_write('user','X',revision,key),201).json()
        self.expect(self.group_write('customer','X',revision,key),409,'request_id_reused')
        self.assertEqual(self.admin.request('GET',f'/api/v1/admin/customer-groups/operations/{key}').json()['state'],'notRecorded')
        other_id,other=self.add_user('other-administrator',admin=True)
        self.assertEqual(other.request('GET',f'/api/v1/admin/user-groups/operations/{key}').json()['state'],'notRecorded')
        committed=self.expect(self.group_write('user','X',revision,key,cancel=True),200).json()
        self.assertEqual(committed['operation'],first)
        self.expect(self.group_write('user','X',revision,key,cancel=True,headers={'Idempotency-Key':str(uuid.uuid4())}),422)
        customer=self.customer('Scoped security');scoped_id,scoped=self.add_user('group-scoped-admin')
        scoped_group=self.user_group(scoped_id);self.grant(scoped_group,'security.manage',customer=customer['id'])
        self.expect(self.group_write('customer','Denied',self.house_revision(),client=scoped,headers={'X-RackClick-Actor':scoped_id}),403)
        self.lab.sql(self.db,"DELETE FROM permission_grant WHERE capability='security.manage'")
        self.expect(self.group_write('user','X',revision,key),403)
        self.expect(self.group_write('user','X',revision,key,cancel=True),403)
        self.expect(self.admin.request('GET',f'/api/v1/admin/user-groups/operations/{key}'),403)

    def test_admin_groupwrites_audit_failure_rolls_back(self):
        self.initialize();revision=self.house_revision();key=str(uuid.uuid4())
        self.lab.sql(self.db,"""CREATE FUNCTION reject_group_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
            IF NEW.action LIKE '%Group.create%' THEN RAISE EXCEPTION 'synthetic group audit failure'; END IF; RETURN NEW; END $$;
            CREATE TRIGGER reject_group_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION reject_group_audit();""")
        self.expect(self.group_write('user','Rolled back',revision,key),503)
        self.expect(self.group_write('customer','Cancelled',revision,str(uuid.uuid4()),cancel=True),503)
        self.assertEqual(self.house_revision(),revision)
        self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM user_group'),'1')
        self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM customer_group'),'0')
        self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM audit_event; SELECT count(*) FROM operation;'),'0\n0')
        self.lab.sql(self.db,'DROP TRIGGER reject_group_audit ON audit_event')
        self.expect(self.group_write('user','Rolled back',revision,key),201)

    def test_admin_groupwrites_concurrent_and_contract(self):
        self.initialize();revision=self.house_revision();key=str(uuid.uuid4())
        with ThreadPoolExecutor(2) as pool:
            made=pool.submit(self.group_write,'customer','Race',revision,key)
            stopped=pool.submit(self.group_write,'customer','Race',revision,key,True)
            create,cancel=made.result(),self.expect(stopped.result(),200).json()
        if cancel['state']=='committed':self.expect(create,201);count='1'
        else:self.expect(create,409,'operation_cancelled');count='0'
        self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM customer_group'),count)
        self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM operation'),'1')
        doc=self.admin.request('GET','/api/v1/openapi.json').json()
        for kind in ('user','customer'):
            for route in (f'/api/v1/admin/{kind}-groups',f'/api/v1/admin/{kind}-groups/operations/{{requestId}}/cancel'):
                required={p['name'] for p in doc['paths'][route]['post']['parameters'] if p.get('required')}
                self.assertTrue({'If-Match','Idempotency-Key','X-RackClick-Actor','X-RackClick-CSRF'}<=required)

    def test_admin_groups_members_grants_and_read_only(self):
        user_id,user,a,b,hidden,direct_id,grouped_id,resource_group=self.permission_fixture()
        revision=self.house_revision()
        before=self.lab.sql(self.db,'SELECT count(*) FROM audit_event; SELECT count(*) FROM operation;')
        people=self.expect(self.admin.request('GET','/api/v1/admin/user-groups'),200).json()
        customers=self.expect(self.admin.request('GET','/api/v1/admin/customer-groups'),200).json()
        self.assertEqual(people['revision'],revision);self.assertEqual(customers['revision'],revision)
        direct=next(g for g in people['groups'] if g['name']=='Direct readers')
        self.assertEqual([u['userName'] for u in direct['members']],['qa-scoped'])
        self.assertEqual(set(direct['members'][0]),{'id','userName','active'})
        grant=next(p for p in direct['grants'] if p['capability']=='inventory.read')
        self.assertEqual(grant['scope'],'customer');self.assertEqual(grant['target'],{'id':a['id'],'name':'Visible A'})
        grouped=next(g for g in people['groups'] if g['name']=='Group technicians')
        self.assertTrue(all(p['scope']=='customerGroup' and p['target']['name']=='Customer scope B' for p in grouped['grants']))
        self.assertEqual(customers['groups'][0]['customers'],[{'id':b['id'],'name':'Visible B'}])
        self.assertEqual(self.house_revision(),revision)
        self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM audit_event; SELECT count(*) FROM operation;'),before)
        self.assertTrue('password' not in json.dumps([people,customers]).lower())

    def test_admin_groups_require_global_permission_and_revocation(self):
        self.initialize();customer=self.customer('Scoped customer');user_id,user=self.add_user('scoped-security')
        group=self.user_group(user_id);self.grant(group,'security.manage',customer=customer['id'])
        for route in ('user-groups','customer-groups'):
            self.expect(Client(self.server).request('GET','/api/v1/admin/'+route),401)
            self.expect(user.request('GET','/api/v1/admin/'+route),403)
        self.lab.sql(self.db,"DELETE FROM permission_grant WHERE capability='security.manage' AND customer_id IS NULL AND customer_group_id IS NULL")
        for route in ('user-groups','customer-groups'):
            self.expect(self.admin.request('GET','/api/v1/admin/'+route),403)

    def test_admin_groups_single_house_empty_and_contract(self):
        self.initialize();foreign=str(uuid.uuid4());ug=str(uuid.uuid4());cg=str(uuid.uuid4());empty=str(uuid.uuid4())
        # Production permits one Systemhaus per installation. Preserve that guard;
        # do not weaken the schema merely to manufacture a multi-house fixture.
        with self.assertRaises(RuntimeError) as rejected:
            self.lab.sql(self.db,f"INSERT INTO systemhaus(id,name) VALUES('{foreign}','Foreign house');")
        self.assertTrue('one_systemhaus_per_installation' in str(rejected.exception))
        self.lab.sql(self.db,f"INSERT INTO user_group VALUES('{empty}','{self.house}','Empty group');")
        people=self.expect(self.admin.request('GET','/api/v1/admin/user-groups'),200).json()
        self.assertEqual({g['name'] for g in people['groups']},{'Systemhaus Administrators','Empty group'})
        group=next(g for g in people['groups'] if g['id']==empty)
        self.assertEqual(group['members'],[]);self.assertEqual(group['grants'],[])
        self.assertEqual(self.expect(self.admin.request('GET','/api/v1/admin/customer-groups'),200).json()['groups'],[])
        doc=self.expect(self.admin.request('GET','/api/v1/openapi.json'),200).json()
        for route in ('user-groups','customer-groups'):
            self.assertEqual(set(doc['paths']['/api/v1/admin/'+route]),{'get','post'})

    def cancel(self, key, revision, name='new-user', headers=None):
        return self.admin.request('POST', f'/api/v1/admin/users/operations/{key}/cancel',
            {'username': name}, {'If-Match': f'"{revision}"', 'Idempotency-Key': key,
             'X-RackClick-Actor': self.admin_id, **(headers or {})})

    def test_admin_cancel_stale_unrecorded_fences_late_create(self):
        self.initialize(); key=str(uuid.uuid4()); old=self.house_revision()
        self.expect(self.create('another-user'),201)
        self.assertEqual(self.admin.request('GET',f'/api/v1/admin/users/operations/{key}').json()['state'],'notRecorded')
        self.expect(self.create(key=key,revision=old),412,'revision_conflict')
        cancelled=self.expect(self.cancel(key,old),200).json()
        self.assertEqual(cancelled['state'],'cancelled'); self.assertIsNone(cancelled['operation'])
        self.assertEqual(self.expect(self.cancel(key,old),200).json(),cancelled)
        self.assertEqual(self.admin.request('GET',f'/api/v1/admin/users/operations/{key}').json(),cancelled)
        self.expect(self.create(key=key,revision=old),409,'operation_cancelled')
        self.expect(self.cancel(key,old,'different-user'),409,'request_id_reused')
        self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM app_user WHERE username='new-user'"),'0')
        self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM audit_event WHERE action='user.create.cancel'"),'1')
        self.assertEqual(self.house_revision(),old+1)
        self.expect(self.create(),201) # A fresh intent can proceed after confirmed cancellation.

    def test_admin_cancel_security_and_rollback(self):
        self.initialize(); key=str(uuid.uuid4()); revision=self.house_revision()
        self.expect(self.cancel(key,revision,headers={'X-RackClick-CSRF':'bad'}),403)
        self.expect(self.cancel(key,revision,headers={'X-RackClick-Actor':str(uuid.uuid4())}),409)
        self.expect(self.cancel(key,revision,headers={'Idempotency-Key':str(uuid.uuid4())}),422)
        self.lab.sql(self.db,"""CREATE FUNCTION reject_cancel_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
            IF NEW.action='user.create.cancel' THEN RAISE EXCEPTION 'synthetic cancellation failure'; END IF; RETURN NEW; END $$;
            CREATE TRIGGER reject_cancel_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION reject_cancel_audit();""")
        self.expect(self.cancel(key,revision),503)
        self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM operation'),'0')
        self.lab.sql(self.db,'DROP TRIGGER reject_cancel_audit ON audit_event')
        self.expect(self.create(key=key,revision=revision),201)
        result=self.expect(self.cancel(key,revision),200).json()
        self.assertEqual(result['state'],'committed') # Cancellation must never undo a committed account.
        self.lab.sql(self.db,"DELETE FROM permission_grant WHERE capability='security.manage'")
        self.expect(self.cancel(key,revision),403)

    def test_admin_cancel_concurrent_create(self):
        self.initialize(); key=str(uuid.uuid4()); revision=self.house_revision()
        with ThreadPoolExecutor(2) as pool:
            create=pool.submit(self.create,key=key,revision=revision)
            cancel=pool.submit(self.cancel,key,revision)
            made,stopped=create.result(),cancel.result()
        state=self.expect(stopped,200).json()['state']
        if state=='committed':
            self.expect(made,201); count='1'
        else:
            self.assertEqual(state,'cancelled'); self.expect(made,409,'operation_cancelled'); count='0'
        self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM app_user WHERE username='new-user'"),count)
        self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM operation'),'1')
        self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM audit_event'),'1')

    def test_admin_cancel_invalid_name_intent(self):
        self.initialize(); revision=self.house_revision()
        for name in ('   ', '\U0001f680'*101):
            key=str(uuid.uuid4())
            self.expect(self.create(name,key=key,revision=revision),422,'username_invalid')
            cancelled=self.expect(self.cancel(key,revision,name),200).json()
            self.assertEqual(cancelled['state'],'cancelled')
            self.assertEqual(self.expect(self.cancel(key,revision,name),200).json(),cancelled)
            self.expect(self.create('now-valid',key=key,revision=revision),409,'request_id_reused')
        self.assertEqual(self.lab.sql(self.db,'SELECT count(*) FROM app_user'),'1')
        self.assertEqual(self.house_revision(),revision)

    def create(self, name='new-user', password=None, revision=None, key=None, client=None, headers=None):
        return (client or self.admin).request('POST', '/api/v1/admin/users',
            {'username': name, 'password': password or self.password},
            {'If-Match': f'"{revision or self.house_revision()}"', 'Idempotency-Key': key or str(uuid.uuid4()),
             'X-RackClick-Actor': self.admin_id, **(headers or {})})

    def test_admin_unicode_login_and_no_implicit_permissions(self):
        self.initialize()
        for name in ('  ÜSER 東京  ', '\U0001f680' * 100):
            result = self.expect(self.create(name), 201).json()
            self.assertEqual(set(result['resource']), {'id', 'userName', 'active'})
            user = Client(self.server); self.expect(user.login(name, self.password), 200)
            self.expect(user.request('GET', '/api/v1/admin/users'), 403, 'forbidden')
            self.assertEqual(user.request('GET', '/api/v1/customers').json(), [])
            identity = user.request('GET', '/api/v1/me').json()
            self.assertEqual(identity['permissions']['systemhausCapabilities'], [])
            self.expect(self.create('intruder', client=user, headers={'X-RackClick-Actor': identity['user']['id']}), 403, 'forbidden')
        self.expect(self.create('\U0001f680' * 101), 422, 'username_invalid')
        self.expect(self.create('short', password='x'*15), 422, 'password_length')
        listing = self.expect(self.admin.request('GET', '/api/v1/admin/users'), 200)
        self.assertEqual(listing.headers['etag'], f'"{listing.json()["revision"]}"')
        self.assertEqual(len(listing.json()['users']), 3)
        self.assertNotIn('password', json.dumps(listing.json()).lower())

    def test_admin_csrf_actor_and_revision(self):
        self.initialize()
        self.expect(Client(self.server).request('GET','/api/v1/admin/users'),401)
        self.expect(self.create(headers={'X-RackClick-CSRF':'bad'}),403,'csrf_invalid')
        self.expect(self.create(headers={'Origin':'https://invalid.example'}),403,'origin_invalid')
        self.expect(self.create(headers={'X-RackClick-Actor':str(uuid.uuid4())}),409,'actor_changed')
        self.expect(self.create(headers={'X-RackClick-Actor':''}),422,'actor_invalid')
        self.expect(self.create(headers={'If-Match':''}),428,'revision_required')
        old=self.house_revision();self.expect(self.create('first'),201)
        self.expect(self.create('stale',revision=old),412,'revision_conflict')

    def test_admin_replay_password_and_audit_no_secrets(self):
        self.initialize();key=str(uuid.uuid4());revision=self.house_revision()
        first=self.expect(self.create(key=key,revision=revision),201).json()
        self.assertEqual(self.expect(self.create(key=key,revision=revision),201).json(),first)
        self.expect(self.create(key=key,revision=revision,password=secrets.token_urlsafe(32)),409,'request_id_reused')
        self.expect(self.create('different',key=key,revision=revision),409,'request_id_reused')
        self.expect(self.create(' NEW-USER '),409,'username_exists')
        outcome=self.expect(self.admin.request('GET',f'/api/v1/admin/users/operations/{key}'),200).json()
        self.assertEqual(outcome['state'],'committed');self.assertEqual(outcome['operation'],first)
        self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM audit_event WHERE action='user.create'"),'1')
        self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM user_group_member"),'1')
        audit=self.lab.sql(self.db,"SELECT before_json::text||after_json::text FROM audit_event WHERE action='user.create'")
        operation=self.lab.sql(self.db,"SELECT result_json::text||request_hash FROM operation")
        # Do not include secret values in assertion diffs/logs.
        self.assertTrue(self.password not in audit+operation)
        self.assertTrue('password' not in (audit+operation).lower())
        self.assertEqual(self.house_revision(),revision+1)

    def test_admin_replay_revoked_and_cross_actor_status(self):
        self.initialize();key=str(uuid.uuid4());revision=self.house_revision()
        self.expect(self.create(key=key,revision=revision),201)
        other_id,other=self.add_user('second-admin',admin=True)
        status=self.expect(other.request('GET',f'/api/v1/admin/users/operations/{key}'),200).json()
        self.assertEqual(status['state'],'notRecorded');self.assertIsNone(status['operation'])
        self.lab.sql(self.db,"DELETE FROM permission_grant WHERE capability='security.manage'")
        self.expect(self.admin.request('GET','/api/v1/admin/users'),403)
        self.expect(self.admin.request('GET',f'/api/v1/admin/users/operations/{key}'),403)
        self.expect(self.create(key=key,revision=revision),403)

    def test_admin_concurrent_replay_and_username_uniqueness(self):
        self.initialize();key=str(uuid.uuid4());revision=self.house_revision()
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda _:self.create(key=key,revision=revision),range(2)))
        for result in results:self.expect(result,201)
        self.assertEqual(results[0].json(),results[1].json())
        self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM app_user WHERE username='new-user'"),'1')

    def test_admin_audit_failure_rolls_back_everything(self):
        self.initialize();revision=self.house_revision()
        self.lab.sql(self.db,"""CREATE FUNCTION reject_user_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
            IF NEW.action='user.create' THEN RAISE EXCEPTION 'synthetic audit failure'; END IF; RETURN NEW; END $$;
            CREATE TRIGGER reject_user_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION reject_user_audit();""")
        key=str(uuid.uuid4());self.expect(self.create(key=key,revision=revision),503)
        self.assertEqual(self.house_revision(),revision)
        self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM app_user"),'1')
        self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM operation"),'0')
        self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM audit_event"),'0')
        self.lab.sql(self.db,'DROP TRIGGER reject_user_audit ON audit_event')
        self.expect(self.create(key=key,revision=revision),201)

    def test_admin_contract(self):
        self.initialize();doc=self.expect(self.admin.request('GET','/api/v1/openapi.json'),200).json()
        post=doc['paths']['/api/v1/admin/users']['post']
        required={p['name'] for p in post['parameters'] if p.get('required')}
        self.assertTrue({'If-Match','Idempotency-Key','X-RackClick-Actor','X-RackClick-CSRF'}<=required)
        self.assertTrue(doc['components']['schemas']['CreateUser']['properties']['password']['writeOnly'])
        cancel=doc['paths']['/api/v1/admin/users/operations/{requestId}/cancel']['post']
        required={p['name'] for p in cancel['parameters'] if p.get('required')}
        self.assertTrue({'requestId','If-Match','Idempotency-Key','X-RackClick-Actor','X-RackClick-CSRF'}<=required)
        self.assertIn('cancelled',doc['components']['schemas']['UserCreationStatus']['properties']['state']['enum'])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--case', help='Run one explicitly named administrative test')
    parser.add_argument('--case-prefix', help='Run only administrative tests with this prefix')
    args=parser.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=False)
    data={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'dllSha256':hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()}
    lab=Lab('admin-users')
    with lab, (args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        AdminPostgres.lab=lab
        names=[name for name in unittest.defaultTestLoader.getTestCaseNames(AdminPostgres) if name.startswith('test_admin_')]
        if args.case:
            if args.case not in names: parser.error('Unknown administrative test')
            names=[args.case]
        if args.case_prefix:
            names=[name for name in names if name.startswith(args.case_prefix)]
            if not names: parser.error('No administrative tests match the prefix')
        suite=unittest.TestSuite(AdminPostgres(name) for name in names)
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(suite)
        data.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    data.update(labStopped=not lab.running,inputsUnchanged=data['dllSha256']==hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest())
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    return 0 if result.wasSuccessful() and data['labStopped'] and data['inputsUnchanged'] else 1

if __name__=='__main__':sys.exit(main())
