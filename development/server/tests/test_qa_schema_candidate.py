"""Three native groups for private QA schema copies; no actual QA pointers opened."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import socket
import sys
import unittest
import uuid
from pg_support import Lab, Client, DEFAULT_DLL, WORKSPACE, free_port
from test_postgres import FoundationPostgres, EvidenceResult, Tee
sys.path.insert(0, str(WORKSPACE / 'tools/windows'))
from qa_schema_candidate import (prepare, Source, CandidateError, snapshot, sha256,
    SOURCE_DLL, SOURCE_BUNDLE, CANDIDATE_DLL, CANDIDATE_BUNDLE, PRIVATE_FILES, artifacts)

BASELINE = WORKSPACE / '.local/baselines/sessions-26/server'
FRONTEND = WORKSPACE / '.local/baselines/schema-copy-30/frontend'


class QaSchemaCopy(FoundationPostgres):
    outcomes = []

    def setUp(self):
        self.lab = Lab('manual-qa-rc9').start()
        self.db = self.lab.create_database('manual-qa-rc9')
        self.password = uuid.uuid4().hex + uuid.uuid4().hex
        self.server = None
        self.candidates = []

    def tearDown(self):
        for candidate in reversed(self.candidates):
            candidate.close()
        self.lab.close()
        self.outcomes.append({'sourceStoppedByCaller': not self.lab.running,
                              'candidatesStopped': all(not c.lab.running for c in self.candidates)})

    def fixture(self):
        self.assertEqual(self.lab.bootstrap(self.db, 'wascar-qa', self.password,
                                           dll=BASELINE / 'RackClick.Server.dll').returncode, 0)
        self.lab.grant_runtime(self.db)
        self.server = self.lab.start_server(self.db, dll=BASELINE / 'RackClick.Server.dll')
        self.admin = Client(self.server)
        self.expect(self.admin.login('wascar-qa', self.password), 200)
        self.house = self.lab.sql(self.db, 'SELECT id FROM systemhaus')
        self.admin_id = self.lab.sql(self.db, 'SELECT id FROM app_user')
        self.visible = self.customer('Synthetic copy visible')
        self.hidden = self.customer('Synthetic copy hidden')
        self.reader_id, self.reader = self.add_user('qa-reader')
        group = self.user_group(self.reader_id, 'Synthetic copy readers')
        cg = str(uuid.uuid4())
        self.lab.sql(self.db, f"INSERT INTO customer_group VALUES('{cg}','{self.house}','Synthetic scope'); INSERT INTO customer_group_member VALUES('{self.house}','{cg}','{self.visible['id']}')")
        self.grant(group, 'systemhaus.read')
        self.grant(group, 'inventory.read', customer_group=cg)
        site, building, room, rack, device, ports, first, second, cable = [str(uuid.uuid4()) for _ in range(9)]
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
        self.server.close()
        shutil.copytree(BASELINE, self.lab.directory / 'server')
        shutil.copytree(FRONTEND, self.lab.directory / 'frontend')
        self.cfg = dict(directory=str(self.lab.directory.resolve()), profile='rc9', host='127.0.0.1',
                        webPort=free_port(), pgPort=self.lab.port, database=self.db.name,
                        connection=self.db.connection(self.lab.port), dllSha256=SOURCE_DLL,
                        bundleSha256=SOURCE_BUNDLE, qaCustomerId=self.visible['id'],
                        qaCustomerName='Synthetic copy visible', restoreSourceSha256='0' * 64,
                        restoreCounts={'customers': 2})
        self.config_path = self.lab.directory / 'manual-qa.json'
        self.config_path.write_text(json.dumps(self.cfg), encoding='utf-8')
        origin = f'http://127.0.0.1:{self.cfg["webPort"]}'
        marker = {'ready': True, 'users': [{'role': 'Administrador', 'userName': 'wascar-qa'},
                  {'role': 'Lector', 'userName': 'qa-reader'}], 'customerName': self.cfg['qaCustomerName']}
        state = {'permissionsCommitted': True, 'origin': origin, 'customer': self.visible,
                 'customerName': self.cfg['qaCustomerName'], 'users': [
                 {'role': 'Lector', 'userName': 'qa-reader', 'password': self.password}]}
        (self.lab.directory / 'ACCESO-PRIVADO.txt').write_text(
            f'URL: {origin}\nUsuario: wascar-qa\nContraseña: {self.password}\n'
            f'\n=== CUENTAS MULTIUSUARIO QA ===\nLector: qa-reader {self.password}\n', encoding='utf-8-sig')
        for name, value in [('QA-CUENTAS-ESTADO.json', marker), ('qa-accounts-private.json', state),
                            ('RESTORE-ESTADO.json', {'restored': True, 'sourceSha256': '0' * 64, 'counts': {'customers': 2}})]:
            (self.lab.directory / name).write_text(json.dumps(value), encoding='utf-8')
        (self.lab.directory / 'server.lock').write_bytes(b'0')
        self.source = Source(self.lab.directory)
        self.before = snapshot(self.source.sql)
        self.private_hashes = {f: sha256(self.lab.directory / f) for f in PRIVATE_FILES}

    def copy(self):
        candidate = prepare(self.lab.directory)
        self.candidates.append(candidate)
        self.assertTrue(self.lab.running, 'Source PG remains running and caller-owned')
        return candidate

    def source_intact(self):
        self.source.unchanged()
        self.assertEqual(self.before, snapshot(self.source.sql))
        self.assertEqual(self.lab.sql(self.db, 'SELECT max(version) FROM schema_migration'), '3')

    def access(self, lab, database, dll, frontend, current=False):
        server = lab.start_server(database, dll=dll, frontend=frontend)
        self.expect(server.request('GET', '/health/ready'), 200)
        admin, reader = Client(server), Client(server)
        admin.cookie, admin.csrf = self.admin.cookie, self.admin.csrf
        reader.cookie, reader.csrf = self.reader.cookie, self.reader.csrf
        self.expect(admin.request('GET', '/api/v1/me'), 200)
        self.expect(reader.request('GET', '/api/v1/me'), 200)
        project = self.expect(reader.request('GET', '/api/v1/customers/' + self.visible['id'] + '/project'), 200).json()
        self.assertEqual((len(project['racks']), len(project['devices']), len(project['ports']), len(project['connections'])), (1,1,2,1))
        self.expect(reader.request('GET', '/api/v1/customers/' + self.hidden['id'] + '/project'), 404)
        self.expect(reader.request('GET', '/api/v1/admin/users'), 403)
        self.expect(admin.request('GET', '/api/v1/admin/users'), 200)
        if current:
            sessions = self.expect(admin.request('GET', f'/api/v1/admin/users/{self.admin_id}/sessions'), 200).json()['sessions']
            self.assertEqual(sum(s['current'] for s in sessions), 1)
            self.assertTrue(all(set(s) == {'id', 'expiresAt', 'current'} for s in sessions))
        return server, admin

    def test_copy_1_schema_four_preserves_state_accounts_and_runtime(self):
        self.fixture()
        with self.copy() as candidate:
            lab, db = candidate.lab, candidate.database
            self.assertTrue((lab.port, db.name, db.owner, db.runtime, db.owner_password, db.runtime_password) !=
                            (self.lab.port, self.db.name, self.db.owner, self.db.runtime,
                             self.db.owner_password, self.db.runtime_password), 'New PostgreSQL identity is required')
            self.assertNotEqual(db.name, self.db.name)
            for role in ('owner', 'runtime', 'owner_password', 'runtime_password'):
                self.assertTrue(getattr(db, role) != getattr(self.db, role), 'Each PostgreSQL identity field must be new')
            sql = lambda command: lab.sql(db, command)
            self.assertEqual(snapshot(self.source.sql, True), snapshot(sql, True))
            self.assertEqual(sql('SELECT max(version) FROM schema_migration'), '4')
            journal = json.loads(candidate.journal.read_text(encoding='utf-8'))
            self.assertEqual(journal['state'], 'prepared')
            self.assertFalse(journal['activated'])
            self.assertEqual(sha256(lab.directory / 'source-schema3.dump'), journal['dumpSha256'])
            for f in PRIVATE_FILES:
                self.assertEqual(self.private_hashes[f], sha256(lab.directory / f))
            for key in ('profile', 'host', 'webPort', 'qaCustomerId', 'qaCustomerName', 'restoreSourceSha256', 'restoreCounts'):
                self.assertEqual(candidate.cfg[key], self.cfg[key])
            self.assertNotIn('artifactDirectory', candidate.cfg)
            self.assertTrue(candidate.cfg['connection'] == db.connection(lab.port), 'Private connection identity must match')
            self.assertEqual(sha256(lab.directory / 'source-manual-qa.json'), sha256(self.config_path))
            self.assertEqual(lab.metadata['databases'][0]['label'], 'manual-qa-rc9')
            # Exercise the real loader with a private fixture pointer only.
            import importlib.util
            spec = importlib.util.spec_from_file_location('qa_copy_fixture', WORKSPACE / 'tools/windows/Qa-Local.py')
            qa = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(qa)
            qa.PROFILE = 'rc9'
            qa.POINTER = lab.directory / 'fixture-pointer.json'
            qa.POINTER.write_text(json.dumps({'directory': str(lab.directory.resolve())}), encoding='utf-8')
            loaded_dir, loaded_cfg = qa.load()
            self.assertEqual(loaded_dir, lab.directory.resolve())
            self.assertTrue(loaded_cfg == candidate.cfg, 'Private QA configuration must match')
            self.assertEqual(qa.artifact_directory(loaded_dir, loaded_cfg), lab.directory.resolve())
            self.assertEqual(sql(f"SELECT NOT has_schema_privilege('{db.runtime}','public','CREATE'); SELECT bool_and(NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole) FROM pg_roles WHERE rolname IN ('{db.owner}','{db.runtime}')"), 't\nt')
            server, admin = self.access(lab, db, lab.directory / 'server/RackClick.Server.dll', lab.directory / 'frontend', True)
            self.assertEqual(snapshot(self.source.sql, True), snapshot(sql, True), 'Read-only access preserves rows')
            for name in ('wascar-qa', 'qa-reader'):
                self.expect(Client(server).login(name, self.password), 200)
            server.close()
            self.source_intact()

    def test_copy_2_source_pair_reopens_independently_after_candidate_write(self):
        self.fixture()
        with self.copy() as candidate:
            lab, db = candidate.lab, candidate.database
            server, admin = self.access(lab, db, lab.directory / 'server/RackClick.Server.dll', lab.directory / 'frontend', True)
            revision = self.house_revision(admin)
            response = self.mutate(admin, 'POST', '/api/v1/customers', 'Synthetic candidate only', revision)
            self.expect(response, 201)
            created = response.json()['resource']['id']
            self.assertEqual(lab.sql(db, f"SELECT count(*) FROM customer WHERE id='{created}'"), '1')
            self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM customer WHERE id='{created}'"), '0')
            server.close()
            self.source_intact()
            old, old_admin = self.access(self.lab, self.db, self.lab.directory / 'server/RackClick.Server.dll', self.lab.directory / 'frontend')
            self.expect(old_admin.request('GET', f'/api/v1/admin/users/{self.admin_id}/sessions'), 404)
            self.assertEqual(self.house_revision(old_admin), revision)
            old.close()
            self.source_intact()
            archive = lab.directory / 'source-schema3.dump'
            self.assertEqual(sha256(archive), json.loads(candidate.journal.read_text(encoding='utf-8'))['dumpSha256'])
            self.assertTrue(self.db.directory.is_dir() and db.directory.is_dir())
        self.assertFalse(candidate.lab.running)
        self.assertTrue(self.lab.running)

    def test_copy_3_rejects_before_allocation_and_retains_failed_migration(self):
        self.fixture()
        labs = WORKSPACE / '.local/labs'
        before_dirs = {p.name for p in labs.iterdir()}
        with self.assertRaises(CandidateError): prepare(WORKSPACE)
        config_bytes = self.config_path.read_bytes()
        for field, value in [('dllSha256', '0' * 64), ('connection', 'wrong'), ('host', '0.0.0.0')]:
            changed = dict(self.cfg, **{field: value})
            self.config_path.write_text(json.dumps(changed), encoding='utf-8')
            try:
                with self.assertRaises(CandidateError): prepare(self.lab.directory)
            finally:
                self.config_path.write_bytes(config_bytes)
        required = self.lab.directory / 'qa-accounts-private.json'
        moved = required.with_suffix('.missing')
        required.rename(moved)
        try:
            with self.assertRaises(CandidateError): prepare(self.lab.directory)
        finally:
            moved.rename(required)
        with socket.socket() as socket_server:
            socket_server.bind(('127.0.0.1', self.cfg['webPort']))
            socket_server.listen()
            with self.assertRaises(CandidateError): prepare(self.lab.directory)
        lock = (self.lab.directory / 'server.lock').open('r+b')
        import msvcrt
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            with self.assertRaises(CandidateError): prepare(self.lab.directory)
        finally:
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            lock.close()
        marker = self.lab.directory / 'ready.json'
        marker.write_text('{}', encoding='utf-8')
        try:
            with self.assertRaises(CandidateError): prepare(self.lab.directory)
        finally:
            marker.unlink()
        self.lab.sql(self.db, "INSERT INTO schema_migration(version,digest) VALUES(4,'synthetic-wrong')")
        try:
            with self.assertRaises(CandidateError): prepare(self.lab.directory)
        finally:
            self.lab.sql(self.db, 'DELETE FROM schema_migration WHERE version=4')
        self.assertEqual(before_dirs, {p.name for p in labs.iterdir()}, 'Preconditions allocate no candidate')
        self.source_intact()
        # Deterministic allocator collision, without binding or disturbing any port.
        from unittest.mock import patch
        with patch('pg_support.free_port', return_value=self.cfg['webPort']):
            with self.assertRaises(CandidateError) as collision:
                prepare(self.lab.directory)
        rejected = collision.exception.candidate
        self.assertIsNotNone(rejected)
        self.candidates.append(rejected)
        self.assertFalse(rejected.lab.running)
        self.assertFalse(rejected.lab.data.exists(), 'Collision is rejected before initdb')
        rejected_state = json.loads(rejected.journal.read_text(encoding='utf-8'))
        self.assertEqual((rejected_state['state'], rejected_state['failedAfter']), ('failed', 'allocated'))
        self.source_intact()
        self.lab.sql(self.db, """CREATE FUNCTION reject_fixture_four() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF NEW.version=4 THEN RAISE EXCEPTION 'Synthetic migration failure'; END IF; RETURN NEW; END $$;
            CREATE TRIGGER reject_fixture_four BEFORE INSERT ON schema_migration FOR EACH ROW EXECUTE FUNCTION reject_fixture_four();""")
        # Fail only the final failure-journal save, after the real SQL migration
        # has failed with candidate PostgreSQL still active. Cleanup must still run.
        import qa_schema_candidate as candidate_module
        original_save = candidate_module.save

        def fail_failure_journal(path, value):
            if value.get('state') == 'failed':
                raise OSError('Synthetic failure journal write error')
            return original_save(path, value)

        with patch('qa_schema_candidate.save', side_effect=fail_failure_journal):
            with self.assertRaises(CandidateError) as caught:
                prepare(self.lab.directory)
        candidate = caught.exception.candidate
        self.assertIsNotNone(candidate)
        self.candidates.append(candidate)
        self.assertFalse(candidate.lab.running)
        journal = json.loads(candidate.journal.read_text(encoding='utf-8'))
        self.assertEqual(journal['state'], 'restored', 'Failed journal write must not invent a recorded failure')
        self.assertNotIn('failedAfter', journal)
        self.assertIn('failure journal not confirmed', str(caught.exception))
        self.assertFalse(journal['activated'])
        self.assertFalse((candidate.lab.directory / 'manual-qa.json').exists())
        self.assertTrue((candidate.lab.directory / 'source-schema3.dump').is_file())
        self.assertTrue((candidate.lab.directory / 'migration.log').is_file())
        # Reopen only the new failed fixture cluster to prove transaction rollback.
        from pg_support import NO_WINDOW
        import subprocess
        status = subprocess.run([str(candidate.lab.pg_bin / 'pg_ctl.exe'), 'status', '-D', str(candidate.lab.data)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW, timeout=15)
        self.assertEqual(status.returncode, 3, 'Native PostgreSQL control must confirm candidate is stopped')
        with (candidate.lab.directory / 'failed-reopen.log').open('wb') as output:
            code = subprocess.run([str(candidate.lab.pg_bin / 'pg_ctl.exe'), 'start', '-D', str(candidate.lab.data),
                '-l', str(candidate.lab.directory / 'postgres.log'), '-w', '-t', '60'], stdout=output, stderr=output,
                creationflags=NO_WINDOW, timeout=90).returncode
        self.assertEqual(code, 0)
        candidate.lab.running = True
        try:
            self.assertEqual(candidate.lab.sql(candidate.database, "SELECT max(version) FROM schema_migration; SELECT count(*) FROM information_schema.columns WHERE table_name='app_session' AND column_name='id'"), '3\n0')
            self.assertEqual(self.before, snapshot(lambda command: candidate.lab.sql(candidate.database, command)))
        finally:
            candidate.close()
        self.source_intact()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    inputs = [Path(__file__).resolve(), WORKSPACE / 'tools/windows/qa_schema_candidate.py']
    hashes = {p.relative_to(WORKSPACE).as_posix(): sha256(p) for p in inputs}
    base = artifacts(BASELINE, FRONTEND, SOURCE_DLL, SOURCE_BUNDLE)
    frozen = artifacts(DEFAULT_DLL.parent, WORKSPACE / 'development/frontend/dist', CANDIDATE_DLL, CANDIDATE_BUNDLE)
    data = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), sourceHashes=hashes,
                sourceDllSha256=SOURCE_DLL, sourceBundleSha256=SOURCE_BUNDLE,
                candidateDllSha256=CANDIDATE_DLL, candidateBundleSha256=CANDIDATE_BUNDLE,
                actualQaOpened=False, pointerChanged=False)
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(QaSchemaCopy)
             if n.startswith('test_copy_') and (not args.case or n in args.case)]
    if not names:
        raise ValueError('No copy groups selected')
    with (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2,
            resultclass=EvidenceResult).run(unittest.TestSuite(QaSchemaCopy(n) for n in names))
    data.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful(),
                labs=QaSchemaCopy.outcomes,
                inputsUnchanged=hashes == {p.relative_to(WORKSPACE).as_posix(): sha256(p) for p in inputs}
                and base == artifacts(BASELINE, FRONTEND, SOURCE_DLL, SOURCE_BUNDLE)
                and frozen == artifacts(DEFAULT_DLL.parent, WORKSPACE / 'development/frontend/dist', CANDIDATE_DLL, CANDIDATE_BUNDLE))
    (args.evidence / 'result.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return 0 if result.wasSuccessful() and data['inputsUnchanged'] and all(
        r['sourceStoppedByCaller'] and r['candidatesStopped'] for r in data['labs']) else 1


if __name__ == '__main__':
    sys.exit(main())
