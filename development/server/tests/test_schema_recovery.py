"""Three native lab-only backup/recovery groups; no existing QA is opened."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest
import uuid
from pg_support import DEFAULT_DLL, WORKSPACE, SERVER_ROOT, NO_WINDOW, Lab, Client, literal
from test_postgres import FoundationPostgres, EvidenceResult, Tee
sys.path.insert(0, str(WORKSPACE / 'tools/windows'))
from pg_lab_recovery import LabRecovery, RecoveryError, sha256

BASELINE = WORKSPACE / '.local/baselines/sessions-26/server/RackClick.Server.dll'
EXPECTED_DLL = '5e55ba4628b41b51d84f6ee62043dbf2ed34d84c3bb7959f905833b4c063cf4a'
EXPECTED_BASELINE = 'd0a5c95783ecc8e9ae7165be9a1bcd8857ee587b643fac3f07aa6092e6bd4b81'


class SchemaRecoveryPostgres(FoundationPostgres):
    def fixture(self):
        self.assertEqual(self.lab.bootstrap(self.db, 'qa-admin', self.password, dll=BASELINE).returncode, 0)
        self.lab.grant_runtime(self.db)
        self.server = self.lab.start_server(self.db, dll=BASELINE)
        self.admin = Client(self.server)
        self.expect(self.admin.login('qa-admin', self.password), 200)
        self.house = self.lab.sql(self.db, 'SELECT id FROM systemhaus')
        self.admin_id = self.lab.sql(self.db, 'SELECT id FROM app_user')
        self.visible = self.customer('Synthetic recovery visible')
        self.hidden = self.customer('Synthetic recovery hidden')
        self.reader_id, self.reader = self.add_user('qa-reader')
        group = self.user_group(self.reader_id, 'Synthetic recovery readers')
        cg = str(uuid.uuid4())
        self.lab.sql(self.db, f"INSERT INTO customer_group VALUES('{cg}','{self.house}','Synthetic scope'); INSERT INTO customer_group_member VALUES('{self.house}','{cg}','{self.visible['id']}')")
        self.grant(group, 'systemhaus.read')
        self.grant(group, 'inventory.read', customer_group=cg)
        ids = [str(uuid.uuid4()) for _ in range(9)]
        site, building, room, rack, device, ports, first, second, cable = ids
        h, c = self.house, self.visible['id']
        self.lab.sql(self.db, f"""BEGIN;
          INSERT INTO inventory_site(id,systemhaus_id,customer_id,name) VALUES('{site}','{h}','{c}','Synthetic site');
          INSERT INTO inventory_building(id,systemhaus_id,customer_id,site_id,name) VALUES('{building}','{h}','{c}','{site}','Synthetic building');
          INSERT INTO inventory_room(id,systemhaus_id,customer_id,building_id,name) VALUES('{room}','{h}','{c}','{building}','Synthetic room');
          INSERT INTO inventory_rack(id,systemhaus_id,customer_id,room_id,name,size_u) VALUES('{rack}','{h}','{c}','{room}','Synthetic rack',42);
          INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order) VALUES('{device}','{h}','{c}','rackEquipment','{rack}','Synthetic switch',1,0);
          INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,sort_order) VALUES('{ports}','{h}','{c}','{device}','rj45',0);
          INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order) VALUES('{first}','{h}','{c}','{device}','{ports}','rj45',1,0),('{second}','{h}','{c}','{device}','{ports}','rj45',2,1);
          INSERT INTO inventory_connection(id,systemhaus_id,customer_id,note) VALUES('{cable}','{h}','{c}','Synthetic cable');
          INSERT INTO inventory_connection_endpoint VALUES('{h}','{c}','{cable}',0,'{first}'),('{h}','{c}','{cable}',1,'{second}');
          COMMIT;""")
        self.recovery = LabRecovery(self.lab)
        self.server.close()
        return self.recovery.backup(self.db, 'backup-three-' + uuid.uuid4().hex[:8])

    def snapshot(self, database, full_session=False):
        tables = self.lab.sql(database, "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
        values = []
        for table in tables:
            projection = '*' if table != 'app_session' or full_session else 'token_hash,user_id,csrf_hash,expires_at'
            row = self.lab.sql(database, f"SELECT count(*),md5(coalesce(string_agg(row_to_json(t)::text,',' ORDER BY row_to_json(t)::text),'')) FROM (SELECT {projection} FROM {table}) t")
            if table == 'schema_migration' and not full_session:
                row = self.lab.sql(database, "SELECT count(*),md5(string_agg(row_to_json(t)::text,',' ORDER BY version)) FROM (SELECT * FROM schema_migration WHERE version<4) t")
            values.append(table + ':' + row)
        return hashlib.sha256('\n'.join(values).encode()).hexdigest()

    def migrate(self):
        env = self.lab.environment()
        env['ConnectionStrings__RackClick'] = self.db.connection(self.lab.port, runtime=False)
        with (self.db.directory / 'migration-four.log').open('wb') as log:
            result = subprocess.run([str(self.lab.dotnet), str(DEFAULT_DLL), '--migrate'],
                    cwd=SERVER_ROOT, env=env, stdout=log, stderr=log, timeout=60, creationflags=NO_WINDOW)
        self.assertEqual(result.returncode, 0, 'Migration failed; private log retained')

    def ready(self, server):
        self.expect(server.request('GET', '/health/ready'), 200)

    def access(self, server, old_cookie=True):
        admin, reader = Client(server), Client(server)
        if old_cookie:
            admin.cookie, admin.csrf = self.admin.cookie, self.admin.csrf
            reader.cookie, reader.csrf = self.reader.cookie, self.reader.csrf
        else:
            self.expect(admin.login('qa-admin', self.password), 200)
            self.expect(reader.login('qa-reader', self.password), 200)
        self.expect(admin.request('GET', '/api/v1/me'), 200)
        self.expect(reader.request('GET', '/api/v1/me'), 200)
        path = '/api/v1/customers/' + self.visible['id'] + '/project'
        project = self.expect(reader.request('GET', path), 200).json()
        self.assertEqual((len(project['racks']), len(project['devices']), len(project['ports']), len(project['connections'])), (1,1,2,1))
        self.expect(reader.request('GET', '/api/v1/customers/' + self.hidden['id'] + '/project'), 404)
        self.expect(reader.request('GET', '/api/v1/admin/users'), 403)
        self.expect(admin.request('GET', '/api/v1/admin/users'), 200)
        return admin

    def runtime_sql(self, database, command):
        env = self.lab.environment()
        passfile = database.directory / 'runtime-recovery.pgpass'
        passfile.write_text(f'127.0.0.1:{self.lab.port}:{database.name}:{database.runtime}:{database.runtime_password}\n', encoding='utf-8')
        env['PGPASSFILE'] = str(passfile)
        result = subprocess.run([str(self.lab.pg_bin / 'psql.exe'), '-X', '-w', '-At', '-v', 'ON_ERROR_STOP=1',
                '-h', '127.0.0.1', '-p', str(self.lab.port), '-U', database.runtime, '-d', database.name],
                input=command, text=True, encoding='utf-8', capture_output=True, env=env,
                timeout=30, creationflags=NO_WINDOW)
        if result.returncode:
            (database.directory / ('runtime-error-' + uuid.uuid4().hex + '.log')).write_text(result.stderr, encoding='utf-8')
        return result

    def roles(self, database):
        self.assertEqual(self.runtime_sql(database, "SELECT current_user; SELECT count(*)>0 FROM app_user").stdout.strip(), database.runtime + '\nt')
        self.assertEqual(self.lab.sql(database, f"SELECT bool_and(NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole) FROM pg_roles WHERE rolname IN ('{database.owner}','{database.runtime}'); SELECT count(*)=0 FROM pg_tables WHERE schemaname='public' AND tableowner<>'{database.owner}'; SELECT NOT has_schema_privilege('{database.runtime}','public','CREATE')"), 't\nt\nt')
        self.assertNotEqual(self.runtime_sql(database, 'CREATE TABLE public.runtime_must_not_create(id integer)').returncode, 0)
        self.assertEqual(self.lab.sql(database, "SELECT to_regclass('public.runtime_must_not_create') IS NULL"), 't')

    def test_recovery_1_backup_three_migrate_four_preserves_state(self):
        backup = self.fixture()
        before = self.snapshot(self.db)
        self.migrate()
        self.assertEqual(before, self.snapshot(self.db))
        self.assertEqual(self.lab.sql(self.db, 'SELECT max(version) FROM schema_migration; SELECT count(*)=count(DISTINCT id) AND bool_and(id IS NOT NULL) FROM app_session'), '4\nt')
        server = self.lab.start_server(self.db)
        self.ready(server); self.access(server)
        self.assertEqual(before, self.snapshot(self.db))
        self.assertTrue((backup / 'database.dump').is_file())

    def test_recovery_2_restore_three_and_four_new_runtime_databases(self):
        backup3 = self.fixture(); before3 = self.snapshot(self.db, True)
        self.migrate(); before4 = self.snapshot(self.db, True)
        recovered3 = self.recovery.restore(backup3, 'restore-three')
        self.assertEqual(before3, self.snapshot(recovered3, True))
        self.assertEqual(before4, self.snapshot(self.db, True))
        self.assertNotEqual((recovered3.owner,recovered3.runtime),(self.db.owner,self.db.runtime))
        server3 = self.lab.start_server(recovered3, dll=BASELINE)
        self.ready(server3); self.roles(recovered3); self.access(server3)
        self.assertEqual(before3, self.snapshot(recovered3, True))
        self.access(server3, False)
        self.assertEqual(self.lab.sql(recovered3, 'SELECT max(version) FROM schema_migration'), '3')
        server3.close()
        backup4 = self.recovery.backup(self.db, 'backup-four')
        recovered4 = self.recovery.restore(backup4, 'restore-four')
        self.assertEqual(before4, self.snapshot(recovered4, True))
        self.assertEqual(before4, self.snapshot(self.db, True))
        server4 = self.lab.start_server(recovered4)
        self.ready(server4); self.roles(recovered4)
        admin = self.access(server4)
        original_ids = self.lab.sql(self.db, 'SELECT id FROM app_session ORDER BY id')
        restored_ids = self.lab.sql(recovered4, 'SELECT id FROM app_session ORDER BY id')
        self.assertEqual(original_ids, restored_ids)
        sessions = self.expect(admin.request('GET', f'/api/v1/admin/users/{self.admin_id}/sessions'), 200).json()['sessions']
        self.assertTrue(sessions and all(set(s)=={'id','expiresAt','current'} for s in sessions))
        self.assertEqual(before4, self.snapshot(recovered4, True))
        self.access(server4, False)
        self.assertEqual(before4, self.snapshot(self.db, True))
        server4.close()

    def test_recovery_3_negative_validation_and_atomic_failed_restore(self):
        backup = self.fixture(); before = self.snapshot(self.db, True)
        database_count = len(self.lab.metadata['databases'])
        archive = backup / 'database.dump'; moved = backup / 'absent.dump'
        archive.rename(moved)
        try:
            with self.assertRaises(RecoveryError): self.recovery.restore(backup, 'missing-archive')
        finally: moved.rename(archive)
        metadata = backup / 'backup.json'; original = metadata.read_bytes(); value=json.loads(original)
        value['sha256']='0'*64; metadata.write_text(json.dumps(value), encoding='utf-8')
        try:
            with self.assertRaises(RecoveryError): self.recovery.restore(backup, 'bad-sha')
        finally: metadata.write_bytes(original)
        with self.assertRaises(RecoveryError): self.recovery.restore(WORKSPACE, 'foreign-path')
        with self.assertRaises(RecoveryError): self.recovery.backup(self.db, backup.name)
        occupied = self.lab.directory / 'recovery/occupied'; occupied.mkdir(); marker=occupied/'marker'; marker.write_bytes(b'preserved')
        with self.assertRaises(RecoveryError): self.recovery.restore(backup, 'occupied')
        self.assertEqual(marker.read_bytes(), b'preserved')
        for name in ('../outside', 'C:/RackClick_SVR', 'bad/name'):
            with self.assertRaises(RecoveryError): self.recovery.backup(self.db, name)
        with self.assertRaises(TypeError): self.recovery.restore(backup, 'external-target', database=self.db)
        self.assertEqual(len(self.lab.metadata['databases']), database_count)
        self.assertEqual(before, self.snapshot(self.db, True))
        broken = self.lab.create_database('valid-archive-sql-error')
        self.lab.sql(broken, f"CREATE TABLE candidate_probe(id integer CHECK(current_user={literal(broken.owner)})); INSERT INTO candidate_probe VALUES(1)")
        broken_before = self.lab.sql(broken, 'SELECT count(*) FROM candidate_probe')
        bad_archive = self.recovery.backup(broken, 'valid-sql-error')
        with self.assertRaises(RecoveryError) as caught: self.recovery.restore(bad_archive, 'failed-candidate')
        candidate = caught.exception.candidate
        self.assertIsNotNone(candidate)
        self.assertEqual(self.lab.sql(candidate, "SELECT count(*) FROM pg_tables WHERE schemaname='public'"), '0')
        self.assertEqual(self.lab.sql(broken, 'SELECT count(*) FROM candidate_probe'), broken_before)
        self.assertEqual(before, self.snapshot(self.db, True))
        self.assertEqual(json.loads((self.lab.directory / 'recovery/failed-candidate/restore.json').read_text(encoding='utf-8'))['state'], 'failed')
        self.assertTrue(candidate.directory.is_dir())


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--evidence', type=Path, required=True); parser.add_argument('--case', action='append'); args=parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    inputs=[Path(__file__).resolve(), WORKSPACE/'tools/windows/pg_lab_recovery.py']
    hashes={str(p.relative_to(WORKSPACE)).replace('\\','/'):sha256(p) for p in inputs}
    if sha256(DEFAULT_DLL)!=EXPECTED_DLL or sha256(BASELINE)!=EXPECTED_BASELINE:
        raise ValueError('Frozen current/baseline DLL differs; no lab started')
    data=dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(),
              dllSha256=sha256(DEFAULT_DLL), baselineDllSha256=sha256(BASELINE), sourceHashes=hashes)
    lab=Lab('schema-recovery')
    with lab, (args.evidence/'tests.log').open('w', encoding='utf-8') as output:
        SchemaRecoveryPostgres.lab=lab
        names=[n for n in unittest.defaultTestLoader.getTestCaseNames(SchemaRecoveryPostgres) if n.startswith('test_recovery_') and (not args.case or n in args.case)]
        if not names: raise ValueError('No recovery groups selected')
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output), verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(SchemaRecoveryPostgres(n) for n in names))
        data.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    data.update(labStopped=not lab.running, inputsUnchanged=data['dllSha256']==sha256(DEFAULT_DLL) and data['baselineDllSha256']==sha256(BASELINE) and hashes=={str(p.relative_to(WORKSPACE)).replace('\\','/'):sha256(p) for p in inputs})
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2)+'\n', encoding='utf-8')
    return 0 if result.wasSuccessful() and data['labStopped'] and data['inputsUnchanged'] else 1

if __name__=='__main__': sys.exit(main())
