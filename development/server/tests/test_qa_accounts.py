"""New native PostgreSQL QA for the bounded local multi-account fixture."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys
import time
import unittest
import uuid
from pg_support import Client, DEFAULT_DLL, Lab, WORKSPACE
from test_postgres import FoundationPostgres, EvidenceResult, Tee

spec = importlib.util.spec_from_file_location('qa_accounts', WORKSPACE / 'tools/windows/Qa-Accounts.py')
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


class QaAccountsPostgres(FoundationPostgres):
    laboratories = []

    def setUp(self):
        self.lab = Lab('qa-accounts').start()
        self.laboratories.append(self.lab)
        try:
            super().setUp()
        except BaseException:
            self.lab.close()
            raise

    def tearDown(self):
        self.lab.close()

    def prepared(self):
        self.initialize('wascar-qa')
        self.foreign = self.customer('Existing unrelated QA customer')
        self.foreign_user, _ = self.add_user('existing-unrelated-user')
        self.before = self.lab.sql(self.db, f"SELECT password_hash FROM app_user WHERE id='{self.admin_id}'; SELECT password_hash FROM app_user WHERE id='{self.foreign_user}';")
        self.report = qa.provision(self.lab.directory, self.server, lambda command: self.lab.sql(self.db, command), 'wascar-qa', self.password)
        self.state = json.loads((self.lab.directory / qa.STATE).read_text(encoding='utf-8'))
        return self.state['customer']['id']

    def test_accounts_roles_scope_writes_and_repeat(self):
        customer = self.prepared()
        self.assertEqual(len(self.report['users']), 4)
        self.assertNotIn('password', json.dumps(self.report).lower())
        readers = []
        for row in self.state['users']:
            client = Client(self.server)
            self.expect(client.login(row['userName'], row['password']), 200)
            self.assertEqual([c['id'] for c in client.request('GET', '/api/v1/customers').json()], [customer])
            self.expect(client.request('GET', '/api/v1/systemhaus'), 200)
            project = self.expect(client.request('GET', f'/api/v1/customers/{customer}/project'), 200).json()
            self.expect(client.request('GET', f'/api/v1/customers/{self.foreign["id"]}/project'), 404)
            headers = {'If-Match': f'"{project["revision"]}"', 'Idempotency-Key': str(uuid.uuid4()), 'X-RackClick-Actor': row['id']}
            response = client.request('POST', f'/api/v1/customers/{customer}/commands',
                                      {'type': 'site.create', 'payload': {'name': 'Site ' + row['role']}}, headers)
            self.expect(response, 403 if row['role'] == 'Lector' else 200)
            self.expect(client.request('POST', f'/api/v1/customers/{self.foreign["id"]}/commands',
                        {'type': 'site.create', 'payload': {'name': 'Denied foreign'}}, headers), 404)
            self.expect(client.request('GET', '/api/v1/admin/users'), 403)
            self.expect(client.request('GET', '/api/v1/admin/user-groups'), 403)
            self.expect(client.request('POST', '/api/v1/admin/users', {'username': 'denied', 'password': self.password}, headers), 403)
            self.expect(client.request('PUT', '/api/v1/systemhaus', {'name': 'Denied'}, headers), 403)
            self.expect(client.request('POST', '/api/v1/customers', {'name': 'Denied'}, headers), 403)
            readers.append(client)
        # Same shared project contains both technicians' committed sites from another session.
        project = readers[-1].request('GET', f'/api/v1/customers/{customer}/project').json()
        self.assertEqual(len(project['sites']), 2)
        counts = self.lab.sql(self.db, 'SELECT count(*) FROM app_user; SELECT count(*) FROM customer; SELECT count(*) FROM user_group; SELECT count(*) FROM permission_grant; SELECT revision FROM systemhaus; SELECT count(*) FROM audit_event;')
        private_before = (self.lab.directory / qa.STATE).read_bytes()
        # Keep the actual loopback login limiter (10/minute); this test deliberately performs many logins.
        time.sleep(61)
        again = qa.provision(self.lab.directory, self.server, lambda command: self.lab.sql(self.db, command), 'wascar-qa', self.password)
        self.assertEqual(again, self.report)
        self.assertTrue(private_before == (self.lab.directory / qa.STATE).read_bytes(), 'Private credentials must remain unchanged')
        self.assertEqual(counts, self.lab.sql(self.db, 'SELECT count(*) FROM app_user; SELECT count(*) FROM customer; SELECT count(*) FROM user_group; SELECT count(*) FROM permission_grant; SELECT revision FROM systemhaus; SELECT count(*) FROM audit_event;'))
        self.assertTrue(self.before == self.lab.sql(self.db, f"SELECT password_hash FROM app_user WHERE id='{self.admin_id}'; SELECT password_hash FROM app_user WHERE id='{self.foreign_user}';"), 'Unrelated account hashes must remain unchanged')
        text = (self.lab.directory / 'ACCESO-PRIVADO.txt').read_text(encoding='utf-8-sig')
        self.assertEqual(text.count(qa.BEGIN), 1)
        for row in self.state['users']:
            self.assertTrue(row['password'] in text, 'Private access file must contain each credential')

    def test_accounts_recovery_sql_rollback_and_scope_drift(self):
        self.initialize('wascar-qa')
        self.lab.sql(self.db,"CREATE FUNCTION reject_qa_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='qa.fixture.permissions' THEN RAISE EXCEPTION 'synthetic fixture rollback'; END IF; RETURN NEW; END $$; CREATE TRIGGER reject_qa_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION reject_qa_audit();")
        with self.assertRaises(RuntimeError):
            qa.provision(self.lab.directory, self.server, lambda command: self.lab.sql(self.db, command), 'wascar-qa', self.password)
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM customer_group; SELECT count(*) FROM user_group'), '0\n1')
        self.assertFalse((self.lab.directory / qa.MARKER).exists())
        self.lab.sql(self.db, 'DROP TRIGGER reject_qa_audit ON audit_event')
        # Simulate the SQL commit response being lost before any local save or verification logins.
        def lost_commit(command):
            result = self.lab.sql(self.db, command)
            if command.startswith('BEGIN;'):
                raise RuntimeError('Synthetic lost SQL commit response')
            return result
        with self.assertRaisesRegex(RuntimeError, 'Synthetic lost SQL commit response'):
            qa.provision(self.lab.directory, self.server, lost_commit, 'wascar-qa', self.password)
        state = json.loads((self.lab.directory / qa.STATE).read_text(encoding='utf-8'))
        self.assertNotIn('permissionsCommitted', state)
        count = self.lab.sql(self.db, 'SELECT count(*) FROM audit_event; SELECT revision FROM systemhaus')
        qa.provision(self.lab.directory, self.server, lambda command: self.lab.sql(self.db, command), 'wascar-qa', self.password)
        self.assertEqual(count, self.lab.sql(self.db, 'SELECT count(*) FROM audit_event; SELECT revision FROM systemhaus'))
        self.lab.sql(self.db, f"DELETE FROM permission_grant WHERE user_group_id='{state['readerGroup']}' AND capability='systemhaus.read'")
        with self.assertRaisesRegex(RuntimeError, 'HTTP 403'):
            qa.provision(self.lab.directory, self.server, lambda command: self.lab.sql(self.db, command), 'wascar-qa', self.password)
        self.assertFalse((self.lab.directory / qa.MARKER).exists())


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--case', help='Run one explicitly named account fixture test')
    args = parser.parse_args(); args.evidence.mkdir(parents=True, exist_ok=False)
    data = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(), 'dllSha256': hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest(), 'historicalResultsReused': False}
    source_files = [Path(__file__), WORKSPACE / 'tools/windows/Qa-Accounts.py']
    data['sourceSha256'] = {str(path.relative_to(WORKSPACE)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files}
    with (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        names = [name for name in unittest.defaultTestLoader.getTestCaseNames(QaAccountsPostgres) if name.startswith('test_accounts_')]
        if args.case:
            if args.case not in names: parser.error('Unknown account fixture test')
            names = [args.case]
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(QaAccountsPostgres(name) for name in names))
        data.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    data.update(labStopped=all(not lab.running for lab in QaAccountsPostgres.laboratories), inputsUnchanged=data['dllSha256'] == hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest() and all(data['sourceSha256'][str(path.relative_to(WORKSPACE))] == hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files))
    (args.evidence / 'result.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    return 0 if result.wasSuccessful() and data['labStopped'] and data['inputsUnchanged'] else 1


if __name__ == '__main__': sys.exit(main())
