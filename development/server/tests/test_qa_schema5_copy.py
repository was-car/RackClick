"""Isolated native Windows/PG17 schema5 preparation + compatible recovery.

Explicit immutable distributions only. No builds, private QA reads or activation.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/windows'))
from pg_support import Lab, Client, NO_WINDOW
from pg_lab_recovery import LabRecovery, RecoveryError, sha256
from qa_schema5_candidate import (CandidateError, Distribution, prepare, snapshot,
                                  history, checked_path, runtime_permissions)
from test_inventory_movement_gui import fixture
from test_postgres import EvidenceResult, Tee


class Schema5CopyPostgres(unittest.TestCase):
    lab = None
    baseline = None
    candidate = None

    def setUp(self):
        self.source = self.lab.create_database(self._testMethodName)
        self.ids, self.password = fixture(self.lab, self.source, self.baseline.dll)
        self.lab.grant_runtime(self.source)
        self.server = self.lab.start_server(self.source, dll=self.baseline.dll, frontend=self.baseline.frontend)
        self.admin = Client(self.server)
        self.expect(self.admin.login('move-admin', self.password), 200)
        second = Client(self.server); self.expect(second.login('move-second', self.password), 200)
        self.house, self.actor = self.lab.sql(self.source, 'SELECT id FROM systemhaus; SELECT id FROM app_user WHERE username=\'move-admin\'').splitlines()
        revision = self.expect(self.admin.request('GET', '/api/v1/systemhaus'), 200).json()['revision']
        key = str(uuid.uuid4())
        self.expect(self.admin.request('POST', '/api/v1/admin/users',
            {'username': 'usuario previo e\u0301 東京', 'password': self.password},
            {'If-Match': f'"{revision}"', 'Idempotency-Key': key, 'X-RackClick-Actor': self.actor}), 201)
        self.event = self.lab.sql(self.source, f"SELECT id FROM audit_event WHERE request_id='{key}'")
        self.server.close()
        self.before = snapshot(self.lab, self.source)
        self.old_history = history(self.lab, self.source, self.baseline)

    def expect(self, response, status):
        self.assertEqual(response.status, status, 'Unexpected HTTP status; full response remains private')
        return response

    def runtime(self, db, sql):
        passfile = db.directory / 'test-runtime.pgpass'
        passfile.write_text(f'127.0.0.1:{self.lab.port}:{db.name}:{db.runtime}:{db.runtime_password}\n', encoding='utf-8')
        env = self.lab.environment(); env['PGPASSFILE'] = str(passfile)
        result = subprocess.run([str(self.lab.pg_bin / 'psql.exe'), '-X', '-w', '-At', '-v', 'ON_ERROR_STOP=1',
            '-h', '127.0.0.1', '-p', str(self.lab.port), '-U', db.runtime, '-d', db.name],
            input=sql, text=True, encoding='utf-8', capture_output=True, env=env,
            timeout=30, creationflags=NO_WINDOW)
        (db.directory / ('runtime-' + uuid.uuid4().hex + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
        return result

    def test_copy_1_prepare5_and_recover4_preserves_all_rows_credentials_sessions(self):
        prepared = prepare(self.lab, self.source, self.baseline, self.candidate, 'success')
        self.assertEqual(snapshot(self.lab, prepared.recovered), self.before)
        self.assertEqual(history(self.lab, prepared.recovered, prepared.baseline), self.old_history)
        self.assertEqual(snapshot(self.lab, self.source), self.before)
        candidate_before = snapshot(self.lab, prepared.database)
        runtime_permissions(self.lab, prepared.database)
        for db in (prepared.database, prepared.recovered):
            self.assertNotEqual(self.runtime(db, 'CREATE TABLE public.forbidden_schema5(id int)').returncode, 0)
            self.assertEqual(self.lab.sql(db, "SELECT to_regclass('public.forbidden_schema5') IS NULL"), 't')
        # Copied cookies are solely fidelity evidence in this synthetic lab, not production session policy.
        for db, dist in ((prepared.database, prepared.candidate), (prepared.recovered, prepared.baseline)):
            server = self.lab.start_server(db, dll=dist.dll, frontend=dist.frontend)
            self.expect(server.request('GET', '/health/ready'), 200)
            self.assertEqual(hashlib.sha256(self.expect(server.request('GET', '/app.js'), 200).body).hexdigest(), dist.expected['frontend']['app.js'])
            client = Client(server); client.cookie = self.admin.cookie; client.csrf = self.admin.csrf
            self.expect(client.request('GET', '/api/v1/me'), 200)
            self.expect(client.request('GET', f'/api/v1/customers/{self.ids["customer"]}/project'), 200)
            self.assertEqual(snapshot(self.lab, db), self.before if db is prepared.recovered else candidate_before)
            self.expect(client.login('move-admin', self.password), 200)
            self.expect(client.request('GET', f'/api/v1/admin/users/{self.actor}/sessions'), 200)
            if db is prepared.database:
                old = self.expect(client.request('GET', f'/api/v1/admin/audit/{self.event}/context'), 200).json()
                self.assertEqual(old['context']['status'], 'notRecorded')
                revision = self.expect(client.request('GET', '/api/v1/systemhaus'), 200).json()['revision']
                key = str(uuid.uuid4())
                created = self.expect(client.request('POST', '/api/v1/admin/users',
                    {'username': 'después de copia Ω', 'password': self.password},
                    {'If-Match': f'"{revision}"', 'Idempotency-Key': key, 'X-RackClick-Actor': self.actor}), 201).json()
                event = self.lab.sql(db, f"SELECT id FROM audit_event WHERE request_id='{key}'")
                context = self.expect(client.request('GET', f'/api/v1/admin/audit/{event}/context'), 200).json()['context']
                self.assertEqual(context['status'], 'available')
                self.assertEqual((context['revisionBefore'], context['revisionAfter']), (revision, revision + 1))
                self.assertEqual(context['objects'], [{'kind': 'user', 'id': created['resource']['id'], 'relation': 'target'}])
                self.assertEqual(self.lab.sql(db, 'SELECT count(*) FROM audit_context; SELECT count(*) FROM audit_context_object'), '1\n1')
            else:
                self.expect(client.request('GET', '/api/v1/admin/audit/' + self.event + '/administrative-detail'), 200)
                self.assertEqual(self.lab.sql(db, 'SELECT max(version) FROM schema_migration'), '4')
            server.close()
        self.assertEqual(snapshot(self.lab, self.source), self.before)
        self.assertEqual(history(self.lab, self.source, self.baseline), self.old_history)
        status = json.loads((prepared.directory / 'preparation-private.json').read_text(encoding='utf-8'))
        self.assertEqual(status['state'], 'prepared'); self.assertFalse(status['activated'])

    def test_copy_2_negative_inputs_history_archive_and_no_destination_reuse(self):
        count = len(self.lab.metadata['databases'])
        def rejected(baseline=None, candidate=None, name='invalid'):
            with self.assertRaises((CandidateError, RecoveryError)):
                prepare(self.lab, self.source, baseline or self.baseline, candidate or self.candidate, name)
            self.assertEqual(len(self.lab.metadata['databases']), count)
        rejected(name='../outside')
        output = self.lab.directory / 'schema5-occupied'; output.mkdir(); marker = output / 'marker'; marker.write_bytes(b'preserved')
        rejected(name='occupied'); self.assertEqual(marker.read_bytes(), b'preserved')
        modified = json.loads(json.dumps(self.candidate.expected)); modified['server']['RackClick.Server.dll'] = '0'*64
        rejected(candidate=Distribution(self.candidate.server, self.candidate.frontend, modified, 5))
        rejected(candidate=Distribution(self.candidate.server / 'absent', self.candidate.frontend, self.candidate.expected, 5))
        rejected(candidate=Distribution(ROOT / 'docs', ROOT / 'docs', self.candidate.expected, 5))
        rejected(baseline=self.candidate)
        old_digest = self.lab.sql(self.source, 'SELECT digest FROM schema_migration WHERE version=4')
        self.lab.sql(self.source, "UPDATE schema_migration SET digest='invalid53' WHERE version=4")
        rejected()
        self.lab.sql(self.source, f"UPDATE schema_migration SET digest='{old_digest}' WHERE version=4")
        self.lab.sql(self.source, 'CREATE TABLE audit_context_object(synthetic boolean)')
        rejected(); self.lab.sql(self.source, 'DROP TABLE audit_context_object')
        self.server = self.lab.start_server(self.source, dll=self.baseline.dll, frontend=self.baseline.frontend)
        rejected(); self.server.close()
        recovery = LabRecovery(self.lab); backup = recovery.backup(self.source, 'negative-backup')
        archive = backup / 'database.dump'; moved = backup / 'absent.dump'; archive.rename(moved)
        try:
            with self.assertRaises(RecoveryError): recovery.restore(backup, 'negative-missing')
        finally: moved.rename(archive)
        metadata = backup / 'backup.json'; original = metadata.read_bytes(); value = json.loads(original); value['sha256'] = '0'*64
        metadata.write_text(json.dumps(value), encoding='utf-8')
        try:
            with self.assertRaises(RecoveryError): recovery.restore(backup, 'negative-hash')
        finally: metadata.write_bytes(original)
        with self.assertRaises(RecoveryError): recovery.backup(self.source, 'negative-backup')
        self.assertEqual(len(self.lab.metadata['databases']), count)
        self.assertEqual(snapshot(self.lab, self.source), self.before)
        self.assertEqual(history(self.lab, self.source, self.baseline), self.old_history)

    def test_copy_3_missing005_runtime_grant_is_failure_with_copies_retained(self):
        original = self.lab.grant_runtime
        def insufficient(db):
            original(db)
            if self.lab.sql(db, "SELECT to_regclass('public.audit_context') IS NOT NULL") == 't':
                self.lab.sql(db, f'REVOKE INSERT ON audit_context_object FROM {db.runtime}')
        with patch.object(self.lab, 'grant_runtime', side_effect=insufficient):
            with self.assertRaises(CandidateError) as caught:
                prepare(self.lab, self.source, self.baseline, self.candidate, 'missing-grant')
        failed = caught.exception.candidate
        self.assertIsNotNone(failed); self.assertIsNotNone(failed.database); self.assertIsNotNone(failed.recovered)
        status = json.loads((failed.directory / 'preparation-private.json').read_text(encoding='utf-8'))
        self.assertEqual((status['state'], status['failedAfter'], status['activated']), ('failed', 'migrated5', False))
        self.assertNotEqual(self.runtime(failed.database, "INSERT INTO audit_context_object VALUES('00000000-0000-0000-0000-000000000001',1,'user','00000000-0000-0000-0000-000000000002','target')").returncode, 0)
        self.assertEqual(history(self.lab, failed.database, failed.candidate)[-1]['version'], 5)
        self.assertEqual(snapshot(self.lab, failed.recovered), self.before)
        self.assertEqual(snapshot(self.lab, self.source), self.before)
        with self.assertRaises(CandidateError):
            prepare(self.lab, self.source, self.baseline, self.candidate, 'missing-grant')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-dll', type=Path, required=True)
    parser.add_argument('--baseline-frontend', type=Path, required=True)
    parser.add_argument('--baseline-manifest', type=Path, required=True)
    parser.add_argument('--candidate-dll', type=Path, required=True)
    parser.add_argument('--candidate-frontend', type=Path, required=True)
    parser.add_argument('--candidate-manifest', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    for path in (args.baseline_manifest, args.candidate_manifest):
        if not checked_path(path).is_relative_to(ROOT / 'evidence'):
            raise ValueError('Only public frozen evidence manifests are accepted')
    for path in (args.baseline_dll, args.candidate_dll):
        if path.name != 'RackClick.Server.dll' or not checked_path(path).is_file():
            raise ValueError('Explicit RackClick.Server.dll must exist')
    baseline = Distribution(args.baseline_dll.absolute().parent, args.baseline_frontend.absolute(),
        json.loads(args.baseline_manifest.read_text(encoding='utf-8'))['distributions'], 4)
    candidate = Distribution(args.candidate_dll.absolute().parent, args.candidate_frontend.absolute(),
        json.loads(args.candidate_manifest.read_text(encoding='utf-8'))['distributions'], 5)
    baseline.validate(); candidate.validate()
    names = unittest.defaultTestLoader.getTestCaseNames(Schema5CopyPostgres)
    if args.case:
        if set(args.case) - set(names): raise ValueError('Unknown schema5-copy case')
        names = [n for n in names if n in args.case]
    args.evidence.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__).resolve(), ROOT / 'tools/windows/qa_schema5_candidate.py',
               ROOT / 'tools/windows/pg_lab_recovery.py', ROOT / 'development/server/tests/pg_support.py',
               ROOT / 'development/server/tests/test_inventory_movement_gui.py']
    def inputs():
        return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources}
    before = inputs()
    data = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(),
                sourceHashes=before, baseline=baseline.expected, candidate=candidate.expected,
                selectedCases=names, actualQaAccessed=False, candidateActivated=False,
                scope='New synthetic Lab; source4 plus two new databases in that same isolated cluster')
    lab = Lab('schema5-copy53')
    with lab, (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        Schema5CopyPostgres.lab, Schema5CopyPostgres.baseline, Schema5CopyPostgres.candidate = lab, baseline, candidate
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(
            unittest.TestSuite(Schema5CopyPostgres(n) for n in names))
        data.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful(),
                    databaseCount=len(lab.metadata['databases']))
    data.update(labStopped=not lab.running, serversStopped=all(s.process.poll() is not None for s in lab.servers),
                inputsUnchanged=before == inputs(), frozenInputsUnchanged=baseline.validate() == baseline.expected and candidate.validate() == candidate.expected)
    (args.evidence / 'result.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return 0 if all(data[k] for k in ('successful','labStopped','serversStopped','inputsUnchanged','frozenInputsUnchanged')) else 1


if __name__ == '__main__':
    sys.exit(main())
