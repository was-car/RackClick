"""PostgreSQL clock after actual actor row waits; four isolated native cases."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import unittest
import uuid
from pg_support import DEFAULT_DLL, Lab, Client
from test_postgres import EvidenceResult, Tee
from test_admin_user_state import UserStatePostgres


class SessionWaitPostgres(UserStatePostgres):
    def durable(self):
        return self.snapshot()+self.lab.sql(self.db,
            "SELECT id,name,revision FROM customer ORDER BY id; SELECT id,name FROM inventory_site ORDER BY id; "
            "SELECT count(*) FROM operation_cancellation")

    def renew(self):
        self.admin=Client(self.server);self.expect(self.admin.login('qa-admin',self.password),200)

    def expired_wait(self,send):
        # Update only expiry BEFORE the lock; holding app_user itself makes no row changes.
        self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '3 seconds' WHERE user_id='{self.admin_id}'")
        before=self.durable()
        with self.user_lock(self.admin_id) as (blocker,pid),ThreadPoolExecutor(1) as pool:
            pending=pool.submit(send)
            try:
                self.wait_for_user_waiter(pid,'%SELECT s.token_hash FROM app_session%FOR SHARE%')
                deadline=time.monotonic()+8
                while self.lab.sql(self.db,f"SELECT count(*)>0 AND bool_and(expires_at<=clock_timestamp()) FROM app_session WHERE user_id='{self.admin_id}'")!='t':
                    if time.monotonic()>deadline:self.fail('SQL did not observe actor session expiry')
                    time.sleep(.025)
                self.assertFalse(pending.done(),'HTTP must remain blocked until actor row release')
            finally:blocker.stdin.write('COMMIT;\n');blocker.stdin.flush()
            response=pending.result(timeout=10)
        self.expect(response,401,'authentication_required')
        self.assertEqual(before,self.durable(),'Rejected expired request must not mutate durable state')

    def create_user(self,name,password,revision,key=None):
        return self.admin.request('POST','/api/v1/admin/users',{'username':name,'password':password},
            {'If-Match':f'"{revision}"','Idempotency-Key':key or str(uuid.uuid4()),'X-RackClick-Actor':self.admin_id})

    def test_wait_admin_repeatable_read_and_state_status(self):
        self.initialize();target,_=self.add_user('target')
        for route in ('/api/v1/admin/users',f'/api/v1/admin/users/{target}/state/operations/{uuid.uuid4()}'):
            with self.subTest(route=route):
                self.renew();self.expired_wait(lambda:self.admin.request('GET',route))

    def test_wait_admin_create_and_foundation_write(self):
        self.initialize()
        for kind in ('create','foundation'):
            with self.subTest(kind=kind):
                self.renew();revision=self.house_revision()
                send=(lambda:self.create_user('blocked-user',self.password,revision)) if kind=='create' else (lambda:self.mutate(self.admin,'POST','/api/v1/customers','Blocked customer',revision))
                self.expired_wait(send)

    def test_wait_inventory_write_and_cancel(self):
        self.initialize();customer=self.customer('Synthetic inventory');path=f"/api/v1/customers/{customer['id']}"
        for cancel in (False,True):
            with self.subTest(cancel=cancel):
                self.renew();revision=self.admin.request('GET',path+'/project').json()['revision'];key=str(uuid.uuid4())
                route=path+(f'/operations/{key}/cancel' if cancel else '/commands')
                body={'type':'site.create','payload':{'name':'Blocked site'}}
                headers={'If-Match':f'"{revision}"','Idempotency-Key':key,'X-RackClick-Actor':self.admin_id}
                self.expired_wait(lambda:self.admin.request('POST',route,body,headers))

    def test_create_unicode_openapi_and_invalid_incoming_sessions(self):
        self.initialize()
        for i,value in enumerate(('\U0001f680'*8,'\U0001f680'*512)):
            name=f'unicode-{i}';self.expect(self.create_user(name,value,self.house_revision()),201)
            self.expect(Client(self.server).login(name,value),200)
        before=self.durable()
        for value in ('\U0001f680'*513,'\U0001f680'*7):
            self.expect(self.create_user('invalid',value,self.house_revision()),422,'password_length')
        self.assertEqual(before,self.durable())
        doc=self.admin.request('GET','/api/v1/openapi.json').json();field=doc['components']['schemas']['CreateUser']['properties']['password']
        # Preserve this assertion until after behavior checks so schema mismatch cannot hide them.
        for kind in ('expired','deleted','inactive'):
            self.renew()
            if kind=='expired':self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()-interval '1 second' WHERE user_id='{self.admin_id}'")
            elif kind=='deleted':self.lab.sql(self.db,f"DELETE FROM app_session WHERE user_id='{self.admin_id}'")
            else:self.lab.sql(self.db,f"UPDATE app_user SET active=false WHERE id='{self.admin_id}'")
            before=self.durable();self.expect(self.admin.request('GET','/api/v1/admin/users'),401,'authentication_required');self.assertEqual(before,self.durable())
        self.assertEqual((field.get('x-rackclick-min-utf16-length'),field.get('x-rackclick-max-utf16-length'),field.get('writeOnly')),(16,1024,True))
        self.assertNotIn('minLength',field);self.assertNotIn('maxLength',field)
        self.assertIn('UTF-16',field['description'])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--case',action='append');args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[3];inputs=[root/'development/server/src/RackClick.Server'/name for name in ('PostgresStore.cs','OpenApiAdmin.cs')]+[Path(__file__).resolve()]
    hashes={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    data={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'dllSha256':hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest(),'sourceHashes':hashes};lab=Lab('session-wait-expiry')
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        SessionWaitPostgres.lab=lab;names=[n for n in unittest.defaultTestLoader.getTestCaseNames(SessionWaitPostgres) if n.startswith(('test_wait_','test_create_unicode_')) and (not args.case or n in args.case)]
        if not names:raise ValueError('No selected session expiry cases')
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(SessionWaitPostgres(n) for n in names));data.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    data.update(labStopped=not lab.running,inputsUnchanged=data['dllSha256']==hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest() and hashes=={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2),encoding='utf-8');return 0 if result.wasSuccessful() and data['labStopped'] and data['inputsUnchanged'] else 1


if __name__=='__main__':sys.exit(main())
