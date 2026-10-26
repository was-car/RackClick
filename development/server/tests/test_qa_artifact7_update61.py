"""61-C: shared engine contracts and one new native Windows60 -> 61 group."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools/windows'))
import qa_artifact7_update as updater
from test_qa_artifact7_update import Artifact7Acceptance
from test_postgres import EvidenceResult, Tee
from pg_lab_recovery import sha256


class TransitionContracts(unittest.TestCase):
    def test_legacy_defaults_and_exact_pair(self):
        self.assertEqual(updater.Source7.__init__.__kwdefaults__['transition'], updater.LEGACY)
        self.assertEqual(updater.update.__kwdefaults__['transition'], updater.LEGACY)
        self.assertEqual(updater.load_target60().expected, updater.transition_pair(updater.LEGACY)[1].expected)
        self.assertEqual(updater.load_historical59().manifest_path, ROOT/updater.APPROVED59[0])

    def test_pin_pending_closed(self):
        with patch.object(updater, 'APPROVED61', None):
            with self.assertRaises(updater.UpdateError) as denied:
                updater.transition_pair(updater.TRANSITION61)
        self.assertEqual(denied.exception.code, 'target61_pin_pending')

    def test_unregistered_or_cross_pair_closed(self):
        for transition in (updater.ApprovedTransition('60-61',59,61), updater.ApprovedTransition('59-61',59,61)):
            with self.assertRaises(updater.UpdateError):
                updater.transition_pair(transition)
        with patch.object(updater, 'APPROVED61', updater.APPROVED60):
            with self.assertRaises(updater.UpdateError) as denied:
                updater.transition_pair(updater.TRANSITION61)
        self.assertEqual(denied.exception.code, 'transition_has_no_artifact_change')

    def test_config_union_and_only_allowed_changes(self):
        previous = dict(dllSha256='a', bundleSha256='b', keep='c')
        selected = dict(previous, artifactDirectory='version', dllSha256='d', bundleSha256='e')
        self.assertEqual(updater.require_config_change(previous, selected), updater.CHANGED_FIELDS)
        self.assertEqual(updater.require_config_change(selected, dict(selected, artifactDirectory='next')), {'artifactDirectory'})
        for invalid in (dict(selected, keep='changed'), {k:v for k,v in selected.items() if k!='keep'}):
            with self.assertRaises(updater.UpdateError):
                updater.require_config_change(previous, invalid)


class Artifact61Acceptance(Artifact7Acceptance):
    transition = updater.TRANSITION61
    versioned_source = True
    outcomes = []
    observations = []

    def create_fixture(self):
        item = super().create_fixture()
        # A genuine60 source cannot enter the historical59 -> 60 contract.
        with self.assertRaises(updater.UpdateError) as denied:
            updater.Source7(item.lab.directory, item.pointer)
        self.assertEqual(denied.exception.code, 'source7_complete_pair59_differs')
        return item


class LegacyCompatibility(Artifact7Acceptance):
    outcomes = []
    observations = []

    def test_legacy_start_select_stop(self):
        item = self.create_fixture()
        result = self.run_update(item)
        self.assertEqual(result.state, 'committed')
        self.assertFalse(updater.pg_running(item.lab.directory))
        self.assert_immutable(item)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--mode', choices=('contracts','legacy','native61'), required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    files = [Path(__file__).resolve(), ROOT/'tools/windows/qa_artifact7_update.py', ROOT/'tools/windows/qa_artifact7_update61.py',
             ROOT/'development/server/tests/test_qa_artifact7_update.py']
    hashes = lambda: {p.relative_to(ROOT).as_posix():sha256(p) for p in files}
    frozen = hashes()
    if args.mode == 'contracts':
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TransitionContracts)
        owner = None
    else:
        owner = LegacyCompatibility if args.mode == 'legacy' else Artifact61Acceptance
        name = 'test_legacy_start_select_stop' if args.mode == 'legacy' else 'test_artifact7_bounded_success_and_failures'
        suite = unittest.TestSuite([owner(name)])
    target = updater.load_target60() if args.mode != 'native61' else updater.load_target61()
    data = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), sourceHashes=frozen,
                mode=args.mode, actualQaAccessed=False, targetManifestSha256=sha256(target.manifest))
    with (args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(suite)
    data.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful(), inputsUnchanged=frozen==hashes(),
                targetUnchanged=target.validate()==target.expected, labs=owner.outcomes if owner else [], observations=owner.observations if owner else [])
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    return 0 if data['successful'] and data['inputsUnchanged'] and all(all(v.values()) for v in data['labs']) else 1


if __name__ == '__main__':
    sys.exit(main())
