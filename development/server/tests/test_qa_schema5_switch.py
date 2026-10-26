"""New synthetic Windows/PG17 selection profiles; never read or activate real QA."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/windows'))
from pg_support import Lab, Client
from pg_lab_recovery import sha256
from qa_schema5_candidate import Distribution, checked_path, prepare, snapshot
import qa_schema5_switch as coordinator
from test_inventory_movement_gui import fixture
from test_postgres import EvidenceResult, Tee


class Schema5SwitchPostgres(unittest.TestCase):
    lab = None
    baseline = None
    candidate = None
    observations = []

    def setUp(self):
        self.source = self.lab.create_database(self._testMethodName)
        self.ids, self.password = fixture(self.lab, self.source, self.baseline.dll)
        self.lab.grant_runtime(self.source)
        self.prepared = prepare(self.lab, self.source, self.baseline, self.candidate, 'case-' + self._testMethodName[-1:])
        self.pointer = coordinator.create_profile(self.lab, self.source, self.prepared)
        self.pointer_before = self.pointer.read_bytes()
        self.source_before = snapshot(self.lab, self.source)
        self.candidate_before = snapshot(self.lab, self.prepared.database)

    def expect(self, response, status):
        self.assertEqual(response.status, status, 'Unexpected HTTP status; private responses not emitted')
        return response

    def selected_schema(self):
        return json.loads(self.pointer.read_bytes())['schema']

    def assert_quiet(self):
        coordinator.quiet(self.lab, self.source, self.prepared)
        self.assertTrue(all(s.process.poll() is not None for s in self.lab.servers))

    def assert_source_unchanged(self):
        self.assertEqual(snapshot(self.lab, self.source), self.source_before)
        self.assertEqual(snapshot(self.lab, self.prepared.recovered), self.source_before)

    def test_switch_1_selection_readiness_login_write_and_restart_1(self):
        # Each case uses its own fresh Lab so the conservative cluster watermark
        # is not invalidated by another case's intentionally retained writes.
        result = coordinator.switch(self.lab, self.source, self.prepared, self.pointer)
        self.assertEqual((result.state, self.selected_schema()), ('committed', self.candidate.schema))
        self.assertEqual(snapshot(self.lab, self.prepared.database), self.candidate_before)
        server = result.server
        admin = Client(server); self.expect(admin.login('move-admin', self.password), 200)
        self.expect(admin.request('GET', f'/api/v1/customers/{self.ids["customer"]}/project'), 200)
        actor = self.expect(admin.request('GET', '/api/v1/me'), 200).json()['user']['id']
        revision = self.expect(admin.request('GET', '/api/v1/systemhaus'), 200).json()['revision']
        key = str(uuid.uuid4())
        created = self.expect(admin.request('POST', '/api/v1/admin/users',
            {'username': 'usuario seleccionado Ω', 'password': self.password},
            {'If-Match': f'"{revision}"', 'Idempotency-Key': key, 'X-RackClick-Actor': actor}), 201).json()
        event = self.lab.sql(self.prepared.database, f"SELECT id FROM audit_event WHERE request_id='{key}'")
        context = self.expect(admin.request('GET', '/api/v1/admin/audit/' + event + '/context'), 200).json()['context']
        self.assertEqual(context['status'], 'available')
        self.assertEqual(context['objects'][0]['id'], created['resource']['id'])
        server.close()
        restarted = self.lab.start_server(self.prepared.database, dll=self.prepared.candidate.dll,
                                          frontend=self.prepared.candidate.frontend)
        self.expect(restarted.request('GET', '/health/ready'), 200)
        admin.server = restarted
        self.expect(admin.request('GET', '/api/v1/me'), 200)
        users = self.expect(admin.request('GET', '/api/v1/admin/users'), 200).json()['users']
        self.assertTrue(any(user['id'] == created['resource']['id'] for user in users))
        restarted.close(); self.assert_source_unchanged(); self.assert_quiet()
        self.observations.append({'group': 1, 'selectedSchema': self.candidate.schema,
                                  'readyLoginWriteRestart': True, 'sourcePreserved': True})

    def test_switch_2_lock_and_failures_without_activity_restore4_2(self):
        with coordinator.profile_lock(self.lab, self.pointer):
            with self.assertRaises(coordinator.SwitchError) as caught:
                coordinator.switch(self.lab, self.source, self.prepared, self.pointer)
        self.assertEqual(caught.exception.code, 'profile_busy')
        self.assertEqual(self.pointer.read_bytes(), self.pointer_before)
        results = []
        for stage in ('before_pointer', 'after_start'):
            def fail(name, result):
                if name == stage: raise RuntimeError('Synthetic no-write selection failure')
            with self.assertRaises(coordinator.SwitchError) as caught:
                coordinator.switch(self.lab, self.source, self.prepared, self.pointer, hook=fail)
            self.assertEqual(caught.exception.code, 'rolled_back')
            self.assertEqual(self.pointer.read_bytes(), self.pointer_before)
            self.assertEqual(self.selected_schema(), 4)
            self.assertEqual(snapshot(self.lab, self.prepared.database), self.candidate_before)
            self.assert_source_unchanged(); self.assert_quiet()
            results.append(stage)
        # Explicit compatible4 probe after rollback; no automatic account reset.
        server = self.lab.start_server(self.source, dll=self.prepared.baseline.dll,
                                       frontend=self.prepared.baseline.frontend)
        self.expect(server.request('GET', '/health/ready'), 200)
        admin = Client(server); self.expect(admin.login('move-admin', self.password), 200)
        self.expect(admin.request('GET', f'/api/v1/customers/{self.ids["customer"]}/project'), 200)
        self.assertEqual(self.lab.sql(self.source, 'SELECT max(version) FROM schema_migration'), '4')
        server.close(); self.assert_quiet()
        self.observations.append({'group': 2, 'profileBusyRejected': True,
                                  'noWriteRollbackStages': results, 'compatible4LoginRead': True})

    def test_switch_3_compensated_dml_and_uncertainty_deny_rollback_3(self):
        observed = {}
        def compensate(name, result):
            if name == 'after_start':
                before = snapshot(self.lab, self.prepared.database)
                house = self.lab.sql(self.prepared.database, 'SELECT id FROM systemhaus')
                customer = str(uuid.uuid4())
                self.lab.sql(self.prepared.database,
                    f"BEGIN; INSERT INTO customer(id,systemhaus_id,name) VALUES('{customer}','{house}','compensado54'); DELETE FROM customer WHERE id='{customer}'; COMMIT;")
                self.assertEqual(snapshot(self.lab, self.prepared.database), before)
                journal = json.loads(result.journal.read_text(encoding='utf-8'))
                watermark = coordinator.activity_watermark(self.lab, self.prepared.database)
                self.assertGreater(int(watermark['xmax']), int(journal['activityBaseline']['xmax']))
                observed.update(rowsEqual=True, activityAdvanced=True)
                raise RuntimeError('Synthetic failure after committed net-zero DML')
        with self.assertRaises(coordinator.SwitchError) as caught:
            coordinator.switch(self.lab, self.source, self.prepared, self.pointer, hook=compensate)
        self.assertEqual(caught.exception.code, 'recovery_required')
        self.assertEqual(self.selected_schema(), self.candidate.schema)
        self.assertNotEqual(self.pointer.read_bytes(), self.pointer_before)
        self.assertEqual(snapshot(self.lab, self.prepared.database), self.candidate_before)
        self.assert_source_unchanged(); self.assert_quiet()
        pointer_after = self.pointer.read_bytes()
        with patch.object(coordinator, 'sql_read', side_effect=RuntimeError('Synthetic unconfirmed read')):
            with self.assertRaises(coordinator.SwitchError):
                coordinator.activity_watermark(self.lab, self.prepared.database)
        for value in (None, {'xmax': '123', 'xip': ['122']}, {'xmax': 'not-a-number', 'xip': []}):
            with self.assertRaises(coordinator.SwitchError):
                coordinator.require_unchanged_activity(self.lab, self.prepared.database, value)
        self.assertEqual(self.pointer.read_bytes(), pointer_after)
        self.observations.append({'group': 3, **observed, 'rollbackDenied': True,
                                  'uncertaintyHelperNegatives': True, 'candidatePreserved': True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline-dll', 'baseline-frontend', 'baseline-manifest',
                 'candidate-dll', 'candidate-frontend', 'candidate-manifest', 'evidence'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--candidate-schema', type=int, choices=(5, 6), default=5)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    for path in (args.baseline_manifest, args.candidate_manifest):
        if not checked_path(path).is_relative_to(ROOT / 'evidence'):
            raise ValueError('Only public frozen manifests are accepted')
    for path in (args.baseline_dll, args.candidate_dll):
        if path.name != 'RackClick.Server.dll' or not checked_path(path).is_file():
            raise ValueError('Explicit RackClick.Server.dll must exist')
    baseline = Distribution(args.baseline_dll.absolute().parent, args.baseline_frontend.absolute(),
        json.loads(args.baseline_manifest.read_text(encoding='utf-8'))['distributions'], 4)
    candidate = Distribution(args.candidate_dll.absolute().parent, args.candidate_frontend.absolute(),
        json.loads(args.candidate_manifest.read_text(encoding='utf-8'))['distributions'], args.candidate_schema)
    baseline.validate(); candidate.validate()
    names = unittest.defaultTestLoader.getTestCaseNames(Schema5SwitchPostgres)
    if args.case:
        if set(args.case) - set(names): raise ValueError('Unknown switch group')
        names = [n for n in names if n in args.case]
    args.evidence.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__).resolve(), ROOT / 'tools/windows/qa_schema5_switch.py',
               ROOT / 'tools/windows/qa_schema5_candidate.py', ROOT / 'tools/windows/pg_lab_recovery.py',
               ROOT / 'development/server/tests/pg_support.py', ROOT / 'development/server/tests/test_inventory_movement_gui.py']
    def inputs(): return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources}
    before = inputs()
    data = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
            'sourceHashes': before, 'baseline': baseline.expected, 'candidate': candidate.expected,
            'candidateSchema': args.candidate_schema, 'actualQaAccessed': False, 'selectedCases': names,
            'scope': 'New synthetic fixtures only; temporary ASP.NET URL, no stable-port supervisor'}
    outcomes = []
    class PerCaseLabResult(EvidenceResult):
        def startTest(self, test):
            test.lab = Lab('schema5-switch54'); test.lab.start()
            test.baseline, test.candidate = baseline, candidate
            super().startTest(test)
        def stopTest(self, test):
            try:
                test.lab.close()
                outcomes.append({'labStopped': not test.lab.running,
                    'serversStopped': all(s.process.poll() is not None for s in test.lab.servers),
                    'databases': len(test.lab.metadata['databases'])})
            finally:
                super().stopTest(test)
    with (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=PerCaseLabResult).run(
            unittest.TestSuite(Schema5SwitchPostgres(n) for n in names))
    data.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful(),
                observations=Schema5SwitchPostgres.observations, labs=outcomes,
                inputsUnchanged=before == inputs(),
                frozenInputsUnchanged=baseline.validate() == baseline.expected and candidate.validate() == candidate.expected)
    (args.evidence / 'result.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return 0 if all((data['successful'], data['inputsUnchanged'], data['frozenInputsUnchanged'],
                    all(r['labStopped'] and r['serversStopped'] for r in outcomes))) else 1


if __name__ == '__main__':
    sys.exit(main())
