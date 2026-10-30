"""Native Windows PostgreSQL grant commands, isolated databases and local secrets."""
import argparse
from concurrent.futures import ThreadPoolExecutor
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
from test_admin_permission_races import PermissionRacePostgres


class GrantPostgres(PermissionRacePostgres):
    def payload(self, capability='inventory.read', scope='systemhaus', target=None, assigned=True, grant=None):
        return {'grantId':grant or str(uuid.uuid4()),'capability':capability,'scope':scope,'targetId':target,'assigned':assigned}

    def change(self,group,payload,revision=None,key=None,cancel=False,client=None,actor=None,headers=None):
        key=key or str(uuid.uuid4());path=f'/api/v1/admin/user-groups/{group}/grants'
        if cancel:path+=f'/operations/{key}/cancel'
        return (client or self.admin).request('POST',path,payload,{'If-Match':f'"{revision if revision is not None else self.house_revision()}"',
            'Idempotency-Key':key,'X-RackClick-Actor':actor or self.admin_id,**(headers or {})})

    def outcome(self,group,key,client=None):
        return (client or self.admin).request('GET',f'/api/v1/admin/user-groups/{group}/grants/operations/{key}')

    def assert_unchanged(self,before):
        self.assertEqual(before,self.lab.sql(self.db,'SELECT revision FROM systemhaus; SELECT count(*) FROM permission_grant; SELECT count(*) FROM operation; SELECT count(*) FROM audit_event'))

    def invariant_grants(self):
        return self.lab.sql(self.db,'SELECT revision FROM systemhaus; SELECT count(*) FROM permission_grant; SELECT count(*) FROM operation; SELECT count(*) FROM audit_event')

    def test_grants_persistence_union_read_write_revocation(self):
        self.initialize();customer=self.customer('Synthetic visible');user,session=self.add_user('granted-user');group=self.user_group(user);other=self.user_group(user,'Union')
        path=f"/api/v1/customers/{customer['id']}";project=path+'/project';self.expect(session.request('GET',project),404)
        payload=self.payload(scope='customer',target=customer['id']);key=str(uuid.uuid4());rev=self.house_revision()
        made=self.expect(self.change(group,payload,rev,key),200).json()
        self.assertEqual(made['resource'],{'groupId':group,**payload});self.assertEqual(made['systemhausRevision'],rev+1)
        self.expect(session.request('GET',project),200)
        second=Client(self.server);self.expect(second.login('granted-user',self.password),200);self.expect(second.request('GET',project),200)
        self.assertEqual(self.expect(self.change(group,payload,rev,key),200).json(),made)
        self.assertEqual(self.house_revision(),rev+1)
        self.expect(self.change(group,payload),200);self.assertEqual(self.house_revision(),rev+2)
        self.expect(self.change(group,self.payload(scope='customer',target=customer['id'])),409,'grant_exists')
        self.expect(self.change(group,{**payload,'capability':'inventory.edit'}),409,'grant_intent_mismatch')
        self.expect(self.change(other,payload),404,'not_found')
        manage=self.payload('customer.manage','customer',customer['id']);self.expect(self.change(group,manage),200)
        self.expect(self.mutate(session,'PUT',path,'Written from existing session',1),200)
        union=self.payload(scope='customer',target=customer['id']);self.expect(self.change(other,union),200)
        self.expect(self.change(group,{**payload,'assigned':False}),200);self.expect(second.request('GET',project),200)
        self.expect(self.change(other,{**union,'assigned':False}),200);self.expect(second.request('GET',project),404)
        self.expect(self.mutate(session,'PUT',path,'Denied without read',2),404)
        self.expect(self.change(group,payload),200);self.expect(self.change(group,{**manage,'assigned':False}),200)
        self.expect(session.request('GET',project),200);self.expect(self.mutate(session,'PUT',path,'Denied without manage',2),403)
        snapshot=self.expect(self.admin.request('GET','/api/v1/admin/user-groups'),200).json()
        grants=next(g['grants'] for g in snapshot['groups'] if g['id']==group)
        self.assertEqual([(g['id'],g['capability'],g['scope'],g['target']['id']) for g in grants],[(payload['grantId'],'inventory.read','customer',customer['id'])])
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM permission_grant WHERE id='{payload['grantId']}'"),'1')
        def inventory(client,actor,kind,data):
            current=self.admin.request('GET',project).json()['revision']
            return client.request('POST',path+'/commands',{'type':kind,'payload':data},
                {'If-Match':f'"{current}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor})
        self.expect(inventory(self.admin,self.admin_id,'site.create',{'name':'Synthetic site'}),200)
        site=self.admin.request('GET',project).json()['sites'][0]['id']
        self.expect(inventory(self.admin,self.admin_id,'building.create',{'name':'Synthetic building','siteId':site}),200)
        building=self.admin.request('GET',project).json()['buildings'][0]['id']
        self.expect(inventory(self.admin,self.admin_id,'room.create',{'name':'Synthetic room','buildingId':building}),200)
        room=self.admin.request('GET',project).json()['rooms'][0]['id']
        edit=self.payload('inventory.edit','customer',customer['id']);self.expect(self.change(group,edit),200)
        self.expect(inventory(session,user,'rack.create',{'name':'Authorized rack','roomId':room,'sizeU':42}),200)
        self.expect(self.change(group,{**edit,'assigned':False}),200)
        intact=self.admin.request('GET',project).json();self.expect(session.request('GET',project),200)
        self.expect(inventory(session,user,'rack.create',{'name':'Denied rack','roomId':room,'sizeU':42}),403)
        self.assertEqual(self.admin.request('GET',project).json(),intact)


    def test_grants_scopes_validation_headers_catalog_global(self):
        self.initialize();customer=self.customer('Scope');user,plain=self.add_user('plain');group=self.user_group(user);cg=self.customer_group()
        self.lab.sql(self.db,f"INSERT INTO customer_group_member(systemhaus_id,customer_id,group_id) VALUES('{self.house}','{customer['id']}','{cg}')")
        scoped=self.payload('inventory.read','customerGroup',cg);self.expect(self.change(group,scoped),200)
        self.expect(plain.request('GET',f"/api/v1/customers/{customer['id']}/project"),200)
        self.expect(self.change(group,self.payload('security.manage','customer',customer['id'])),200)
        self.expect(self.change(group,self.payload('security.manage','customerGroup',cg)),200)
        self.expect(plain.request('GET','/api/v1/admin/capabilities'),403)
        self.expect(self.change(group,self.payload(),client=plain,actor=user),403)
        for field,value in [('capability','Inventory.Read'),('capability','inventory.read '),('capability',None),('scope','all'),('scope',None),('assigned',None),('grantId',str(uuid.UUID(int=0)))]:
            with self.subTest(field=field,value=value):self.expect(self.change(group,{**self.payload(),field:value}),422,'grant_invalid')
        self.expect(self.change(group,self.payload(target=customer['id'])),422,'grant_invalid')
        self.expect(self.change(group,self.payload(scope='customer')),422,'grant_invalid')
        self.expect(self.change(group,self.payload(scope='customerGroup',target=str(uuid.UUID(int=0)))),422,'grant_invalid')
        self.expect(self.change(str(uuid.uuid4()),self.payload()),404)
        self.expect(self.change(group,self.payload(scope='customer',target=str(uuid.uuid4()))),404)
        self.expect(self.change(group,self.payload(scope='customerGroup',target=str(uuid.uuid4()))),404)
        for headers,status in [({'Origin':'https://invalid.example'},403),({'X-RackClick-CSRF':'bad'},403),({'X-RackClick-Actor':''},422),({'X-RackClick-Actor':user},409),({'If-Match':''},428),({'Idempotency-Key':''},422)]:
            self.expect(self.change(group,self.payload(),headers=headers),status)
        before=self.invariant_grants();catalog=self.expect(self.admin.request('GET','/api/v1/admin/capabilities'),200).json()
        self.assertEqual(catalog['revision'],self.house_revision());self.assertEqual(len(catalog['capabilities']),9);self.assertIn('security.manage',catalog['capabilities']);self.assertIn('reports.export',catalog['capabilities']);self.assert_unchanged(before)
        omitted=self.payload('systemhaus.read');del omitted['targetId'];self.expect(self.change(group,omitted),200)
        doc=self.admin.request('GET','/api/v1/openapi.json').json();post=doc['paths']['/api/v1/admin/user-groups/{groupId}/grants']['post']
        self.assertTrue({'groupId','If-Match','Idempotency-Key','X-RackClick-Actor','X-RackClick-CSRF'} <= {p['name'] for p in post['parameters'] if p.get('required')})
        self.assertNotIn('targetId',doc['components']['schemas']['SetGrant']['required'])
        self.assertEqual(set(doc['components']['schemas']['SetGrant']['properties']['capability']['enum']),set(catalog['capabilities']))
        anonymous=Client(self.server);self.expect(anonymous.request('GET','/api/v1/admin/capabilities'),401)

    def test_grants_last_active_global_admin_and_historical_duplicates(self):
        self.initialize();group=self.lab.sql(self.db,f"SELECT group_id FROM user_group_member WHERE user_id='{self.admin_id}'")
        grant=self.lab.sql(self.db,f"SELECT id FROM permission_grant WHERE user_group_id='{group}' AND capability='security.manage'")
        remove=self.payload('security.manage',assigned=False,grant=grant);before=self.invariant_grants()
        self.expect(self.change(group,remove),409,'last_admin_required');self.assert_unchanged(before)
        inactive,_=self.add_user('inactive',admin=True);self.lab.sql(self.db,f"UPDATE app_user SET active=false WHERE id='{inactive}'")
        self.expect(self.change(group,remove),409,'last_admin_required');self.assert_unchanged(before)
        active,session=self.add_user('other-admin');other=self.user_group(active);backup=self.payload('security.manage');self.expect(self.change(other,backup),200)
        duplicate=str(uuid.uuid4());self.lab.sql(self.db,f"INSERT INTO permission_grant VALUES('{duplicate}','{self.house}','{group}','security.manage',NULL,NULL)")
        self.expect(self.change(group,remove),200)
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM permission_grant WHERE user_group_id='{group}' AND capability='security.manage'"),'1')
        self.expect(self.change(group,self.payload('security.manage',assigned=False,grant=duplicate)),200)
        self.expect(self.admin.request('GET','/api/v1/admin/capabilities'),403)
        self.expect(session.request('GET','/api/v1/admin/capabilities'),200)
        before=self.invariant_grants();self.expect(self.change(other,{**backup,'assigned':False},client=session,actor=active),409,'last_admin_required');self.assert_unchanged(before)

    def test_grants_replay_status_fence_actor_group_late(self):
        self.initialize();user,_=self.add_user('target');group=self.user_group(user);other=self.user_group(user,'Other');_,second=self.add_user('other-admin',admin=True)
        payload=self.payload();revision=self.house_revision();key=str(uuid.uuid4());self.customer('Advance')
        self.expect(self.change(group,payload,revision,key),412)
        self.assertEqual(self.outcome(group,key).json()['state'],'notRecorded')
        cancelled=self.expect(self.change(group,payload,revision,key,True),200).json();self.assertEqual(cancelled['state'],'cancelled')
        self.expect(self.change(group,payload,revision,key),409,'operation_cancelled')
        self.assertEqual(self.expect(self.change(group,payload,revision,key,True),200).json(),cancelled)
        self.expect(self.change(group,{**payload,'capability':'inventory.edit'},revision,key,True),409,'request_id_reused')
        self.assertEqual(self.outcome(other,key).json()['state'],'notRecorded');self.assertEqual(self.outcome(group,key,second).json()['state'],'notRecorded')
        absent=str(uuid.uuid4());absentPayload=self.payload('inventory.read','customer',str(uuid.uuid4()));self.expect(self.change(absent,absentPayload,revision,str(uuid.uuid4()),True),200)
        key=str(uuid.uuid4());revision=self.house_revision();made=self.expect(self.change(group,payload,revision,key),200).json()
        self.assertEqual(self.outcome(group,key).json()['operation'],made);self.assertEqual(self.expect(self.change(group,payload,revision,key,True),200).json()['operation'],made)
        self.assertEqual(self.admin.request('GET',f'/api/v1/admin/user-groups/{group}/members/operations/{key}').json()['state'],'notRecorded')
        self.expect(self.change(other,payload,revision,key),409,'request_id_reused')

    def test_grants_audit_rollback_concurrent_exact_and_cancel(self):
        self.initialize();user,_=self.add_user('target');group=self.user_group(user);payload=self.payload();key=str(uuid.uuid4());revision=self.house_revision();before=self.invariant_grants()
        self.lab.sql(self.db,"""CREATE FUNCTION reject_grant_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
            IF NEW.action LIKE 'userGroup.grant.set%' THEN RAISE EXCEPTION 'synthetic audit failure'; END IF; RETURN NEW; END $$;
            CREATE TRIGGER reject_grant_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION reject_grant_audit();""")
        self.expect(self.change(group,payload,revision,key),503);self.assert_unchanged(before)
        self.expect(self.change(group,payload,revision,key,True),503);self.assert_unchanged(before)
        self.lab.sql(self.db,'DROP TRIGGER reject_grant_audit ON audit_event')
        with ThreadPoolExecutor(2) as pool:
            a=pool.submit(self.change,group,payload,revision,key);b=pool.submit(self.change,group,payload,revision,key)
            self.assertEqual(self.expect(a.result(),200).json(),self.expect(b.result(),200).json())
        self.assertEqual(self.house_revision(),revision+1);self.assertEqual(self.lab.sql(self.db,"SELECT count(*) FROM audit_event WHERE action='userGroup.grant.set'"),'1')
        race=str(uuid.uuid4());now=self.house_revision();remove={**payload,'assigned':False}
        with ThreadPoolExecutor(2) as pool:
            a=pool.submit(self.change,group,remove,now,race);b=pool.submit(self.change,group,remove,now,race,True)
            change=a.result();terminal=self.expect(b.result(),200).json()
        if terminal['state']=='committed':self.expect(change,200);self.assertEqual(self.house_revision(),now+1)
        else:self.expect(change,409,'operation_cancelled');self.assertEqual(self.house_revision(),now)

    def test_grants_waiting_revocation_replay_and_cancel(self):
        self.initialize();user,session=self.add_user('delegated-admin');group=self.user_group(user);self.grant(group,'security.manage')
        target,_=self.add_user('target');targets=self.user_group(target)
        for kind in ('set','replay','cancel'):
            with self.subTest(kind=kind):
                if kind!='set':self.grant(group,'security.manage')
                payload=self.payload();key=str(uuid.uuid4());revision=self.house_revision()
                if kind=='replay':self.expect(self.change(targets,payload,revision,key,client=session,actor=user),200)
                before=self.invariant_grants()
                with self.house_lock() as (blocker,pid),ThreadPoolExecutor(1) as pool:
                    pending=pool.submit(self.change,targets,payload,revision,key,kind=='cancel',session,user)
                    try:
                        self.wait_for_house_waiter(pid);self.assertFalse(pending.done())
                        self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability='security.manage'")
                    finally:blocker.stdin.write('COMMIT;\n');blocker.stdin.flush()
                    self.expect(pending.result(timeout=10),403,'forbidden')
                # The fixture removed exactly one grant; no API mutation/audit/revision.
                fields=before.splitlines();fields[1]=str(int(fields[1])-1);self.assert_unchanged('\n'.join(fields))
                self.expect(self.outcome(targets,key,session),403,'forbidden')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--case',action='append');args=parser.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[3]
    inputs=[root/'development/server/src/RackClick.Server'/name for name in ('AdminGrantWrites.cs','Program.cs','OpenApiAdmin.cs')]+[Path(__file__).resolve()]
    hashes={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    data={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'dllSha256':hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest(),'sourceHashes':hashes}
    lab=Lab('admin-grants')
    with lab, (args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        GrantPostgres.lab=lab
        names=[n for n in unittest.defaultTestLoader.getTestCaseNames(GrantPostgres) if n.startswith('test_grants_') and (not args.case or n in args.case)]
        if not names:raise ValueError('No selected grant cases')
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(GrantPostgres(n) for n in names))
        data.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    data.update(labStopped=not lab.running,inputsUnchanged=data['dllSha256']==hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest() and hashes=={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    return 0 if result.wasSuccessful() and data['labStopped'] and data['inputsUnchanged'] else 1

if __name__=='__main__':sys.exit(main())
