"""Three native supervisor/schema-switch groups, private fixture pointer only."""
import argparse
from datetime import datetime, timezone
import http.client
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest
from pg_support import Client, Response, DEFAULT_DLL, WORKSPACE
from test_postgres import EvidenceResult, Tee
from test_qa_schema_candidate import QaSchemaCopy, BASELINE, FRONTEND
sys.path.insert(0, str(WORKSPACE / 'tools/windows'))
from qa_schema_switch import (switch, SwitchError, start_supervisor, stop_application,
    pg_running, read_owner, profile_lock, qa_module)
from qa_schema_candidate import (sha256, snapshot, artifacts, SOURCE_DLL, SOURCE_BUNDLE,
    CANDIDATE_DLL, CANDIDATE_BUNDLE, PRIVATE_FILES, CandidateError)


class NativeHttp:
    def __init__(self, cfg):
        self.port = cfg['webPort']
        self.origin = f'http://127.0.0.1:{self.port}'

    def request(self, method, path, body=None, headers=None):
        headers = dict(headers or {})
        if body is not None and not isinstance(body, (bytes, str)):
            body = json.dumps(body).encode('utf-8')
            headers.setdefault('Content-Type', 'application/json')
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=20)
        try:
            connection.request(method, path, body, headers)
            response = connection.getresponse()
            return Response(response.status, {k.lower(): v for k,v in response.getheaders()}, response.read())
        finally:
            connection.close()


class QaSchemaSwitch(QaSchemaCopy):
    outcomes = []

    def setUp(self):
        super().setUp()
        self.native_dirs, self.processes = {}, []

    def tearDown(self):
        # Retained inactive branches share the stable web port with the current
        # branch. Stop all active fixture apps before checking inactive ports.
        for directory, cfg in reversed(list(self.native_dirs.items())):
            if qa_module().running(directory):
                stop_application(directory, cfg)
        for directory, cfg in reversed(list(self.native_dirs.items())):
            stop_application(directory, cfg)
        for process in self.processes:
            process.wait(timeout=30)
        super().tearDown()
        self.outcomes[-1]['nativeSupervisorsStopped'] = all(not qa_module().running(d) and not pg_running(d) for d in self.native_dirs)

    def native_fixture(self, active=True):
        self.fixture()
        self.lab.close()
        home = self.lab.directory / 'switch-home'
        home.mkdir()
        self.pointer = home / 'current.json'
        self.pointer.write_text(json.dumps({'directory': str(self.lab.directory.resolve())}), encoding='utf-8')
        self.pointer_before = self.pointer.read_bytes()
        self.native_dirs[self.lab.directory] = self.cfg
        if active:
            self.processes.append(start_supervisor(self.lab.directory, self.cfg))

    def record(self, name, result):
        if result.candidate:
            self.native_dirs[result.candidate.lab.directory] = result.candidate.cfg
            if result.candidate not in self.candidates:
                self.candidates.append(result.candidate)

    def current_directory(self):
        return Path(json.loads(self.pointer.read_text(encoding='utf-8'))['directory']).resolve()

    def old_client(self, cfg, reader=False):
        client = Client(NativeHttp(cfg))
        previous = self.reader if reader else self.admin
        client.cookie, client.csrf = previous.cookie, previous.csrf
        return client

    def test_switch_1_native_switch_same_url_and_durable_write(self):
        self.native_fixture()
        self.assertTrue(qa_module().ready(self.lab.directory, self.cfg))
        result = switch(self.lab.directory, self.pointer, hook=self.record)
        self.assertEqual(result.state, 'committed')
        candidate = result.candidate
        directory, cfg = candidate.lab.directory, candidate.cfg
        self.assertEqual(self.current_directory(), directory.resolve())
        self.assertEqual(cfg['webPort'], self.cfg['webPort'])
        self.assertFalse(qa_module().running(self.lab.directory))
        self.assertFalse(pg_running(self.lab.directory))
        self.assertTrue(qa_module().ready(directory, cfg))
        self.assertEqual(self.before, snapshot(lambda sql: read_owner(directory, cfg, sql), True))
        for name in PRIVATE_FILES:
            self.assertEqual(self.private_hashes[name], sha256(directory / name))
        admin, reader = self.old_client(cfg), self.old_client(cfg, True)
        for client in (admin, reader):
            self.expect(client.request('GET', '/api/v1/me'), 200)
        self.expect(reader.request('GET', '/api/v1/customers/' + self.hidden['id'] + '/project'), 404)
        self.expect(reader.request('GET', '/api/v1/admin/users'), 403)
        sessions = self.expect(admin.request('GET', f'/api/v1/admin/users/{self.admin_id}/sessions'), 200).json()['sessions']
        self.assertEqual(sum(row['current'] for row in sessions), 1)
        for name in ('wascar-qa', 'qa-reader'):
            self.expect(Client(NativeHttp(cfg)).login(name, self.password), 200)
        revision = self.house_revision(admin)
        created = self.expect(self.mutate(admin, 'POST', '/api/v1/customers', 'Synthetic switched write', revision), 201).json()['resource']['id']
        durable = snapshot(lambda sql: read_owner(directory, cfg, sql))
        stop_application(directory, cfg)
        self.processes.append(start_supervisor(directory, cfg))
        self.expect(admin.request('GET', '/api/v1/me'), 200)
        self.assertEqual(read_owner(directory, cfg, f"SELECT count(*) FROM customer WHERE id='{created}'"), '1')
        self.assertEqual(durable, snapshot(lambda sql: read_owner(directory, cfg, sql)))
        self.assertTrue(self.db.directory.is_dir() and candidate.database.directory.is_dir())

    def test_switch_2_precommit_and_postcommit_unwritten_compatible_recovery(self):
        self.native_fixture(active=False)

        def precommit(name, result):
            self.record(name, result)
            if name == 'before_pointer':
                raise RuntimeError('Synthetic pre-switch failure')

        with self.assertRaises(SwitchError) as caught:
            switch(self.lab.directory, self.pointer, hook=precommit)
        self.assertEqual(caught.exception.code, 'rolled_back')
        self.assertEqual(self.pointer.read_bytes(), self.pointer_before)
        self.assertFalse(qa_module().running(self.lab.directory), 'An originally stopped app stays stopped')
        self.assertFalse(pg_running(self.lab.directory))
        first_candidate = caught.exception.result.candidate
        self.assertFalse(pg_running(first_candidate.lab.directory))
        self.processes.append(start_supervisor(self.lab.directory, self.cfg))

        def postswitch(name, result):
            self.record(name, result)
            if name == 'after_pointer':
                raise RuntimeError('Synthetic failure after pointer commit, before serving')

        with self.assertRaises(SwitchError) as caught:
            switch(self.lab.directory, self.pointer, hook=postswitch)
        self.assertEqual(caught.exception.code, 'rolled_back')
        self.assertEqual(self.pointer.read_bytes(), self.pointer_before)
        self.assertTrue(qa_module().ready(self.lab.directory, self.cfg))
        self.assertFalse(pg_running(caught.exception.result.candidate.lab.directory))
        self.assertEqual(self.before, snapshot(lambda sql: read_owner(self.lab.directory, self.cfg, sql)))
        self.expect(self.old_client(self.cfg).request('GET', '/api/v1/me'), 200)
        self.expect(self.old_client(self.cfg).request('GET', f'/api/v1/admin/users/{self.admin_id}/sessions'), 404)
        self.assertTrue(first_candidate.lab.directory.is_dir() and caught.exception.result.candidate.lab.directory.is_dir())
        # Cheap retained-reference failure: reuse our already stopped candidate;
        # no additional dump/restore/migration and no helper/product alterations.
        from unittest.mock import patch
        with patch('qa_schema_switch.prepare', side_effect=CandidateError('Synthetic uncertain cleanup', first_candidate)), \
                patch.object(first_candidate, 'close', side_effect=OSError('Synthetic close failure')):
            with self.assertRaises(SwitchError) as uncertain:
                switch(self.lab.directory, self.pointer)
        self.assertEqual(uncertain.exception.code, 'recovery_required')
        self.assertIs(uncertain.exception.result.candidate, first_candidate)
        self.assertEqual(self.pointer.read_bytes(), self.pointer_before)
        self.assertFalse(qa_module().running(self.lab.directory))
        self.assertFalse(pg_running(self.lab.directory))
        self.assertFalse(pg_running(first_candidate.lab.directory))
        recorded = json.loads(uncertain.exception.result.journal.read_text(encoding='utf-8'))
        self.assertFalse(recorded['candidateCleanupConfirmed'])

    def test_switch_3_profile_lock_and_postcommit_writes_require_recovery(self):
        self.native_fixture()
        before_labs = {p.name for p in (WORKSPACE / '.local/labs').iterdir()}
        with profile_lock(self.pointer):
            with self.assertRaises(SwitchError) as busy:
                switch(self.lab.directory, self.pointer)
        self.assertEqual(busy.exception.code, 'profile_busy')
        self.assertEqual(before_labs, {p.name for p in (WORKSPACE / '.local/labs').iterdir()})
        self.assertTrue(qa_module().ready(self.lab.directory, self.cfg))
        committed = {}

        def write_then_fail(name, result):
            self.record(name, result)
            if name == 'after_start':
                cfg = result.candidate.cfg
                admin = Client(NativeHttp(cfg))
                self.expect(admin.login('wascar-qa', self.password), 200)
                revision = self.house_revision(admin)
                resource = self.expect(self.mutate(admin, 'POST', '/api/v1/customers', 'Synthetic recovery retained', revision), 201).json()['resource']
                committed['id'] = resource['id']
                committed['snapshot'] = snapshot(lambda sql: read_owner(result.candidate.lab.directory, cfg, sql))
                raise RuntimeError('Synthetic post-switch failure after writes')

        with self.assertRaises(SwitchError) as caught:
            switch(self.lab.directory, self.pointer, hook=write_then_fail)
        self.assertEqual(caught.exception.code, 'recovery_required')
        candidate = caught.exception.result.candidate
        directory, cfg = candidate.lab.directory, candidate.cfg
        self.assertEqual(self.current_directory(), directory.resolve(), 'Pointer must retain written candidate')
        for lab_dir in (self.lab.directory, directory):
            self.assertFalse(qa_module().running(lab_dir))
            self.assertFalse(pg_running(lab_dir))
        qa_module().control(directory, 'start')
        try:
            self.assertEqual(read_owner(directory, cfg, f"SELECT count(*) FROM customer WHERE id='{committed['id']}'"), '1')
            self.assertEqual(committed['snapshot'], snapshot(lambda sql: read_owner(directory, cfg, sql)))
        finally:
            qa_module().control(directory, 'stop')
        self.assertTrue(self.db.directory.is_dir() and candidate.database.directory.is_dir())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    inputs = [Path(__file__).resolve(), WORKSPACE / 'tools/windows/qa_schema_switch.py',
              WORKSPACE / 'tools/windows/qa_schema_candidate.py', WORKSPACE / 'tools/windows/Qa-Local.py',
              WORKSPACE / 'tools/windows/windows_job.py', WORKSPACE / 'development/server/tests/test_qa_schema_candidate.py']
    hashes = {p.relative_to(WORKSPACE).as_posix(): sha256(p) for p in inputs}
    base = artifacts(BASELINE, FRONTEND, SOURCE_DLL, SOURCE_BUNDLE)
    frozen = artifacts(DEFAULT_DLL.parent, WORKSPACE / 'development/frontend/dist', CANDIDATE_DLL, CANDIDATE_BUNDLE)
    data = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), sourceHashes=hashes,
                sourceDllSha256=SOURCE_DLL, sourceBundleSha256=SOURCE_BUNDLE,
                candidateDllSha256=CANDIDATE_DLL, candidateBundleSha256=CANDIDATE_BUNDLE,
                actualQaOpened=False, globalPointerChanged=False)
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(QaSchemaSwitch)
             if n.startswith('test_switch_') and (not args.case or n in args.case)]
    if not names:
        raise ValueError('No switch groups selected')
    with (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2,
            resultclass=EvidenceResult).run(unittest.TestSuite(QaSchemaSwitch(n) for n in names))
    data.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful(),
                labs=QaSchemaSwitch.outcomes, inputsUnchanged=hashes ==
                {p.relative_to(WORKSPACE).as_posix(): sha256(p) for p in inputs}
                and base == artifacts(BASELINE, FRONTEND, SOURCE_DLL, SOURCE_BUNDLE)
                and frozen == artifacts(DEFAULT_DLL.parent, WORKSPACE / 'development/frontend/dist', CANDIDATE_DLL, CANDIDATE_BUNDLE))
    (args.evidence / 'result.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return 0 if result.wasSuccessful() and data['inputsUnchanged'] and all(
        r['sourceStoppedByCaller'] and r['candidatesStopped'] and r['nativeSupervisorsStopped'] for r in data['labs']) else 1


if __name__ == '__main__':
    sys.exit(main())
