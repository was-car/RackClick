"""Three private native groups for conservative cluster activity rollback guard."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import unittest
import uuid
from unittest.mock import patch
from pg_support import Client, DEFAULT_DLL, WORKSPACE
from test_postgres import EvidenceResult, Tee
from test_qa_schema_candidate import BASELINE, FRONTEND
from test_qa_schema_switch import QaSchemaSwitch, NativeHttp
sys.path.insert(0, str(WORKSPACE / 'tools/windows'))
import qa_schema_switch as coordinator
from qa_schema_candidate import (sha256, snapshot, artifacts, SOURCE_DLL, SOURCE_BUNDLE,
    CANDIDATE_DLL, CANDIDATE_BUNDLE)


def observed_activity(directory, cfg):
    """Independent read-only observation, including when reproducing old31."""
    return json.loads(coordinator.read_owner(directory, cfg,
        "SELECT json_build_object('xmax',pg_snapshot_xmax(s)::text,'xip',"
        "ARRAY(SELECT pg_snapshot_xip(s)::text)) FROM (SELECT pg_current_snapshot() s) q"))


class QaActivityGuard(QaSchemaSwitch):
    outcomes = []
    observations = []

    def baseline(self, result):
        candidate = result.candidate
        journal = json.loads(result.journal.read_text(encoding='utf-8'))
        if 'activityBaseline' in journal:
            return journal['activityBaseline']
        # OLD31 reproduction only: observe the same point before preview; never
        # alter coordinator/product or any real QA profile to reproduce the gap.
        coordinator.qa_module().control(candidate.lab.directory, 'start')
        try:
            return observed_activity(candidate.lab.directory, candidate.cfg)
        finally:
            coordinator.qa_module().control(candidate.lab.directory, 'stop')

    def assert_quiet(self, result):
        self.record('retained', result)
        for directory in (self.lab.directory, result.candidate.lab.directory):
            self.assertFalse(coordinator.qa_module().running(directory))
            self.assertFalse(coordinator.pg_running(directory))

    def test_activity_1_login_logout_equal_rows_must_not_rollback(self):
        self.native_fixture()
        observed = {}

        def compensate(name, result):
            self.record(name, result)
            if name == 'prepared':
                observed['baseline'] = self.baseline(result)
            if name == 'after_start':
                candidate = result.candidate
                before = json.loads(candidate.journal.read_text(encoding='utf-8'))['candidateSnapshot']
                client = Client(NativeHttp(candidate.cfg))
                self.expect(client.login('wascar-qa', self.password), 200)
                self.expect(client.request('POST', '/api/v1/auth/logout'), 204)
                after = snapshot(lambda sql: coordinator.read_owner(candidate.lab.directory, candidate.cfg, sql))
                self.assertEqual(before, after, 'Compensated authentication leaves all public rows exactly equal')
                current = observed_activity(candidate.lab.directory, candidate.cfg)
                self.assertTrue(int(current['xmax']) > int(observed['baseline']['xmax']), 'Cluster transaction watermark must advance')
                self.assertEqual(current['xip'], [])
                observed['rowsEqual'] = True
                observed['activityAdvanced'] = True
                raise RuntimeError('Synthetic failure after compensated authentication')

        with self.assertRaises(coordinator.SwitchError) as caught:
            coordinator.switch(self.lab.directory, self.pointer, hook=compensate)
        self.assertEqual(caught.exception.code, 'recovery_required', 'OLD31 incorrectly returns rolled_back for net-zero writes')
        result = caught.exception.result
        self.assertEqual(self.current_directory(), result.candidate.lab.directory.resolve())
        self.assert_quiet(result)
        self.observations.append({'group': 1, 'rowsEqual': observed['rowsEqual'], 'activityAdvanced': observed['activityAdvanced']})

    def test_activity_2_readonly_preview_clean_restart_allows_compatible_recovery(self):
        self.native_fixture(active=False)
        observed = {}

        def readonly(name, result):
            self.record(name, result)
            if name == 'prepared':
                observed['baseline'] = self.baseline(result)
            if name == 'after_pointer':
                candidate = result.candidate
                coordinator.qa_module().control(candidate.lab.directory, 'start')
                try:
                    first = observed_activity(candidate.lab.directory, candidate.cfg)
                    self.assertEqual(first, observed['baseline'])
                    self.assertEqual(first['xip'], [])
                    coordinator.read_owner(candidate.lab.directory, candidate.cfg, 'SELECT count(*) FROM app_user')
                finally:
                    coordinator.qa_module().control(candidate.lab.directory, 'stop')
                coordinator.qa_module().control(candidate.lab.directory, 'start')
                try:
                    self.assertEqual(observed_activity(candidate.lab.directory, candidate.cfg), observed['baseline'])
                finally:
                    coordinator.qa_module().control(candidate.lab.directory, 'stop')
                observed['readonlyRestartUnchanged'] = True
                raise RuntimeError('Synthetic no-write failure after pointer commit')

        with self.assertRaises(coordinator.SwitchError) as caught:
            coordinator.switch(self.lab.directory, self.pointer, hook=readonly)
        self.assertEqual(caught.exception.code, 'rolled_back')
        self.assertEqual(self.pointer.read_bytes(), self.pointer_before)
        self.assert_quiet(caught.exception.result)
        self.observations.append({'group': 2, 'readonlyRestartUnchanged': observed['readonlyRestartUnchanged'], 'originallyStoppedRespected': True})

    def test_activity_3_compensated_sql_and_uncertain_guard_never_allow_rollback(self):
        self.native_fixture()
        observed = {}

        def compensate_sql(name, result):
            self.record(name, result)
            if name == 'prepared':
                observed['baseline'] = self.baseline(result)
            if name == 'after_start':
                candidate = result.candidate
                before = json.loads(candidate.journal.read_text(encoding='utf-8'))['candidateSnapshot']
                new_id = str(uuid.uuid4())
                candidate.lab.sql(candidate.database,
                    f"BEGIN; INSERT INTO customer(id,systemhaus_id,name) VALUES('{new_id}','{self.house}','Synthetic compensated SQL'); DELETE FROM customer WHERE id='{new_id}'; COMMIT;")
                self.assertEqual(before, snapshot(lambda sql: coordinator.read_owner(candidate.lab.directory, candidate.cfg, sql)))
                current = observed_activity(candidate.lab.directory, candidate.cfg)
                self.assertTrue(int(current['xmax']) > int(observed['baseline']['xmax']), 'Compensated committed SQL assigns a transaction ID')
                observed['rowsEqual'] = True
                observed['activityAdvanced'] = True
                raise RuntimeError('Synthetic failure after compensated SQL')

        with self.assertRaises(coordinator.SwitchError) as caught:
            coordinator.switch(self.lab.directory, self.pointer, hook=compensate_sql)
        self.assertEqual(caught.exception.code, 'recovery_required')
        result = caught.exception.result
        self.assertEqual(self.current_directory(), result.candidate.lab.directory.resolve())
        self.assert_quiet(result)
        pointer_after = self.pointer.read_bytes()
        # Cheap uncertainty negatives on the actual guard; no extra copy/restore.
        with patch('qa_schema_switch.read_owner', side_effect=coordinator.SwitchError('synthetic_activity_read_failure')):
            with self.assertRaises(coordinator.SwitchError):
                coordinator.require_unchanged_activity(result.candidate.lab.directory, result.candidate.cfg, observed['baseline'])
        with patch('qa_schema_switch.activity_watermark', return_value={'xmax': observed['baseline']['xmax'], 'xip': ['123']}):
            with self.assertRaises(coordinator.SwitchError):
                coordinator.require_unchanged_activity(result.candidate.lab.directory, result.candidate.cfg, observed['baseline'])
        with self.assertRaises(coordinator.SwitchError):
            coordinator.require_unchanged_activity(result.candidate.lab.directory, result.candidate.cfg, None)
        self.assertEqual(self.pointer.read_bytes(), pointer_after)
        self.assert_quiet(result)
        self.observations.append({'group': 3, 'rowsEqual': observed['rowsEqual'], 'activityAdvanced': observed['activityAdvanced'], 'uncertaintyRejected': True})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    inputs = [Path(__file__).resolve(), WORKSPACE / 'tools/windows/qa_schema_switch.py',
              WORKSPACE / 'tools/windows/qa_schema_candidate.py', WORKSPACE / 'tools/windows/Qa-Local.py',
              WORKSPACE / 'tools/windows/windows_job.py', WORKSPACE / 'development/server/tests/test_qa_schema_switch.py']
    hashes = {p.relative_to(WORKSPACE).as_posix(): sha256(p) for p in inputs}
    base = artifacts(BASELINE, FRONTEND, SOURCE_DLL, SOURCE_BUNDLE)
    frozen = artifacts(DEFAULT_DLL.parent, WORKSPACE / 'development/frontend/dist', CANDIDATE_DLL, CANDIDATE_BUNDLE)
    data = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), sourceHashes=hashes,
                sourceDllSha256=SOURCE_DLL, sourceBundleSha256=SOURCE_BUNDLE,
                candidateDllSha256=CANDIDATE_DLL, candidateBundleSha256=CANDIDATE_BUNDLE,
                actualQaOpened=False, globalPointerChanged=False)
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(QaActivityGuard)
             if n.startswith('test_activity_') and (not args.case or n in args.case)]
    if not names:
        raise ValueError('No activity groups selected')
    with (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2,
            resultclass=EvidenceResult).run(unittest.TestSuite(QaActivityGuard(n) for n in names))
    data.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful(),
                labs=QaActivityGuard.outcomes, observations=QaActivityGuard.observations,
                inputsUnchanged=hashes == {p.relative_to(WORKSPACE).as_posix(): sha256(p) for p in inputs}
                and base == artifacts(BASELINE, FRONTEND, SOURCE_DLL, SOURCE_BUNDLE)
                and frozen == artifacts(DEFAULT_DLL.parent, WORKSPACE / 'development/frontend/dist', CANDIDATE_DLL, CANDIDATE_BUNDLE))
    (args.evidence / 'result.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return 0 if result.wasSuccessful() and data['inputsUnchanged'] and all(
        r['sourceStoppedByCaller'] and r['candidatesStopped'] and r['nativeSupervisorsStopped'] for r in data['labs']) else 1


if __name__ == '__main__':
    sys.exit(main())
