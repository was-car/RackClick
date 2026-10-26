"""Four native groups: schema3->4 and read-only public session administration."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import unittest
import uuid
from pg_support import DEFAULT_DLL, WORKSPACE, SERVER_ROOT, NO_WINDOW, Lab, Client
from test_postgres import EvidenceResult, Tee
from test_session_wait_expiry import SessionWaitPostgres

BASELINE=WORKSPACE/'.local/baselines/sessions-26/server/RackClick.Server.dll'

class UserSessionsPostgres(SessionWaitPostgres):
    def get(self,user,client=None):
        return (client or self.admin).request('GET',f'/api/v1/admin/users/{user}/sessions')

    def migration(self,dll=DEFAULT_DLL):
        env=self.lab.environment();env['ConnectionStrings__RackClick']=self.db.connection(self.lab.port,runtime=False)
        return subprocess.run([str(self.lab.dotnet),str(dll),'--migrate'],cwd=SERVER_ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=60,creationflags=NO_WINDOW)

    def private_state(self):
        return self.lab.sql(self.db,"SELECT md5(string_agg(row_to_json(t)::text,',' ORDER BY token_hash)) FROM (SELECT token_hash,user_id,csrf_hash,expires_at FROM app_session) t; SELECT md5(string_agg(row_to_json(t)::text,',' ORDER BY id)) FROM app_user t; SELECT revision FROM systemhaus; SELECT count(*) FROM audit_event; SELECT count(*) FROM operation")

    def test_sessions_migration_three_four_repeat_fresh_constraints_rollback(self):
        self.assertTrue(BASELINE.is_file(),'An isolated schema3 baseline is required')
        self.assertEqual(self.lab.bootstrap(self.db,'qa-admin',self.password,dll=BASELINE).returncode,0)
        self.assertEqual(self.lab.sql(self.db,'SELECT max(version) FROM schema_migration'),'3')
        self.lab.grant_runtime(self.db);self.server=self.lab.start_server(self.db,dll=BASELINE);old=Client(self.server);self.expect(old.login('qa-admin',self.password),200)
        second=Client(self.server);self.expect(second.login('qa-admin',self.password),200);self.server.close()
        history=self.lab.sql(self.db,'SELECT row_to_json(t) FROM schema_migration t ORDER BY version');before=self.private_state();self.assertEqual(self.migration().returncode,0);self.assertEqual(before,self.private_state());self.assertEqual(history,self.lab.sql(self.db,'SELECT row_to_json(t) FROM schema_migration t WHERE version<4 ORDER BY version'))
        self.assertEqual(self.lab.sql(self.db,"SELECT string_agg(version::text,',' ORDER BY version) FROM schema_migration; SELECT count(*)=count(DISTINCT id) AND bool_and(id IS NOT NULL AND id<>'00000000-0000-0000-0000-000000000000') FROM app_session"),'1,2,3,4\nt')
        history4=self.lab.sql(self.db,'SELECT row_to_json(t) FROM schema_migration t ORDER BY version');ids=self.lab.sql(self.db,'SELECT id FROM app_session ORDER BY id');self.assertEqual(self.migration().returncode,0);self.assertEqual(history4,self.lab.sql(self.db,'SELECT row_to_json(t) FROM schema_migration t ORDER BY version'));self.assertEqual(ids,self.lab.sql(self.db,'SELECT id FROM app_session ORDER BY id'));self.assertEqual(before,self.private_state())
        for assignment in ("id=NULL","id='00000000-0000-0000-0000-000000000000'","id=(SELECT id FROM app_session ORDER BY id LIMIT 1)"):
            with self.subTest(constraint=assignment.split('=')[0]):
                with self.assertRaises(RuntimeError):self.lab.sql(self.db,f'UPDATE app_session SET {assignment}')
                self.assertEqual(ids,self.lab.sql(self.db,'SELECT id FROM app_session ORDER BY id'))
        self.server=self.lab.start_server(self.db);old.server=self.server;second.server=self.server
        for client in (old,second):self.expect(client.request('GET','/api/v1/me'),200)
        failed=self.lab.create_database('migration-collision');original=self.db;self.db=failed
        try:
            self.assertEqual(self.lab.bootstrap(failed,'qa-admin',self.password,dll=BASELINE).returncode,0)
            self.lab.grant_runtime(failed);fixture=self.lab.start_server(failed,dll=BASELINE);self.expect(Client(fixture).login('qa-admin',self.password),200);fixture.close()
            self.lab.sql(failed,"ALTER TABLE app_session ADD CONSTRAINT app_session_public_id_unique CHECK (true)")
            state=self.private_state();self.assertNotEqual(self.migration().returncode,0)
            self.assertEqual(state,self.private_state());self.assertEqual(self.lab.sql(failed,"SELECT max(version) FROM schema_migration; SELECT count(*) FROM information_schema.columns WHERE table_name='app_session' AND column_name='id'"),'3\n0')
        finally:self.db=original
        fresh=self.lab.create_database('fresh-four');self.assertEqual(self.lab.bootstrap(fresh,'qa-admin',self.password).returncode,0);self.assertEqual(self.lab.sql(fresh,'SELECT max(version) FROM schema_migration'),'4')

    def test_sessions_list_current_filter_stability_and_zero_changes(self):
        self.initialize();otheradmin=Client(self.server);self.expect(otheradmin.login('qa-admin',self.password),200)
        target,first=self.add_user('target');second=Client(self.server);self.expect(second.login('target',self.password),200)
        self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()-interval '1 second' WHERE token_hash=(SELECT token_hash FROM app_session WHERE user_id='{target}' ORDER BY token_hash LIMIT 1)")
        before=self.durable();response=self.expect(self.get(self.admin_id),200);own=response.json()
        self.assertEqual(response.headers['etag'],f'"{self.house_revision()}"');self.assertEqual(set(own),{'revision','user','sessions'});self.assertEqual(own['user'],{'id':self.admin_id,'userName':'qa-admin','active':True})
        self.assertEqual(own['sessions'],sorted(own['sessions'],key=lambda s:(s['expiresAt'],s['id'])));self.assertEqual(len(own['sessions']),2);self.assertEqual(sum(s['current'] for s in own['sessions']),1)
        again=self.get(self.admin_id,otheradmin).json();self.assertEqual({s['id'] for s in own['sessions']},{s['id'] for s in again['sessions']});self.assertNotEqual(next(s['id'] for s in own['sessions'] if s['current']),next(s['id'] for s in again['sessions'] if s['current']))
        listed=self.expect(self.get(target),200).json();self.assertEqual(len(listed['sessions']),1);self.assertFalse(listed['sessions'][0]['current']);self.assertEqual(before,self.durable())
        persisted=json.loads(self.lab.sql(self.db,f"SELECT json_agg(json_build_object('id',id,'expiresAt',expires_at,'current',false) ORDER BY expires_at,id) FROM app_session WHERE user_id='{target}' AND expires_at>clock_timestamp()"))
        self.assertEqual([s['id'] for s in persisted],[s['id'] for s in listed['sessions']]);self.assertEqual(datetime.fromisoformat(persisted[0]['expiresAt']),datetime.fromisoformat(listed['sessions'][0]['expiresAt'].replace('Z','+00:00')))
        self.lab.sql(self.db,f"UPDATE app_user SET active=false WHERE id='{target}'");before=self.durable();inactive=self.expect(self.get(target),200).json();self.assertFalse(inactive['user']['active']);self.assertEqual(inactive['sessions'],[]);self.assertEqual(before,self.durable())

    def test_sessions_authorization_scopes_public_dto_openapi(self):
        self.initialize();target,plain=self.add_user('scoped');group=self.user_group(target);customer=self.customer('Scope');cg=self.customer_group()
        self.grant(group,'security.manage',customer=customer['id']);self.grant(group,'security.manage',customer_group=cg)
        before=self.durable();self.expect(self.get(target,plain),403);self.expect(self.get(target,Client(self.server)),401)
        self.expect(self.get(str(uuid.UUID(int=0))),422,'request_invalid');self.expect(self.get(str(uuid.uuid4())),404,'not_found');self.assertEqual(before,self.durable())
        self.lab.sql(self.db,'DROP INDEX one_systemhaus_per_installation');house=str(uuid.uuid4());foreign=str(uuid.uuid4())
        self.lab.sql(self.db,f"INSERT INTO systemhaus(id,name) VALUES('{house}','Foreign synthetic'); INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{foreign}','{house}','foreign',password_hash FROM app_user WHERE id='{target}'")
        before=self.durable();self.expect(self.get(foreign),404,'not_found');self.assertEqual(before,self.durable())
        response=self.expect(self.get(target),200).json();self.assertEqual(set(response),{'revision','user','sessions'});self.assertEqual(set(response['user']),{'id','userName','active'})
        for row in response['sessions']:self.assertEqual(set(row),{'id','expiresAt','current'});uuid.UUID(row['id'])
        doc=self.admin.request('GET','/api/v1/openapi.json').json();operation=doc['paths']['/api/v1/admin/users/{userId}/sessions']['get'];schemas=doc['components']['schemas']
        self.assertEqual(set(schemas['AdminUserSession']['properties']),{'id','expiresAt','current'});self.assertEqual(set(schemas['AdminUserSessions']['properties']),{'revision','user','sessions'});self.assertEqual(schemas['AdminUserSession']['properties']['expiresAt']['format'],'date-time')
        self.assertEqual(operation['responses']['200']['content']['application/json']['schema']['$ref'],'#/components/schemas/AdminUserSessions');self.assertIn('ETag',operation['responses']['200']['headers']);self.assertEqual(operation['parameters'][0]['name'],'userId');self.assertTrue(operation['parameters'][0]['required'])
        public=json.dumps(response)
        self.assertTrue(all(field not in public for field in ('token','csrf','cookie','password','connection')))
        secrets=self.lab.sql(self.db,'SELECT token_hash FROM app_session UNION ALL SELECT csrf_hash FROM app_session').splitlines();self.assertTrue(all(secret not in public for secret in secrets),'Public DTO must never contain session secrets')

    def test_sessions_actor_expiry_after_postgresql_wait(self):
        self.initialize();self.expired_wait(lambda:self.get(self.admin_id))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--case',action='append');args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False)
    paths=[WORKSPACE/'development/server/src/RackClick.Server'/name for name in ('AdminUserSessions.cs','SchemaMigrations.cs','Program.cs','OpenApiAdmin.cs')]+[WORKSPACE/'development/server/database/004-session-identity.sql',Path(__file__).resolve()]
    hashes={str(p.relative_to(WORKSPACE)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};dllhash=hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()
    data={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'dllSha256':dllhash,'baselineDllSha256':hashlib.sha256(BASELINE.read_bytes()).hexdigest(),'sourceHashes':hashes};lab=Lab('admin-sessions-consulta')
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        UserSessionsPostgres.lab=lab;names=[n for n in unittest.defaultTestLoader.getTestCaseNames(UserSessionsPostgres) if n.startswith('test_sessions_') and (not args.case or n in args.case)]
        if not names:raise ValueError('No selected sessions cases')
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(UserSessionsPostgres(n) for n in names));data.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    data.update(labStopped=not lab.running,inputsUnchanged=dllhash==hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest() and hashes=={str(p.relative_to(WORKSPACE)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');return 0 if result.wasSuccessful() and data['labStopped'] and data['inputsUnchanged'] else 1

if __name__=='__main__':sys.exit(main())
