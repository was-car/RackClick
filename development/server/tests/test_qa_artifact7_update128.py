"""128: closed transition contracts and ONE bounded fresh Windows113 fixture."""
import argparse
from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
import platform
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools/windows'))
import qa_artifact7_update as updater
from test_qa_artifact7_update import Artifact7Acceptance
from test_qa_artifact7_update61 import TransitionContracts as PreviousContracts
from test_postgres import EvidenceResult, Tee
from pg_support import Client
from test_qa_schema6_real import NativeHttp
from pg_lab_recovery import sha256
from qa_schema_candidate import snapshot


class Transition128Contracts(PreviousContracts):
    def test_registered_identity_and_invalid_clones(self):
        self.assertIs(updater.resolve_transition('113-128'), updater.TRANSITION128)
        for transition in (updater.ApprovedTransition('113-128',113,128),
                           updater.ApprovedTransition('113-128',68,128),
                           updater.ApprovedTransition('113-129',113,129)):
            with self.assertRaises(updater.UpdateError) as denied:
                updater.require_transition(transition)
            self.assertEqual(denied.exception.code, 'transition_not_approved')
        self.assertIs(inspect.signature(updater.main).parameters['default_transition'].default, updater.LEGACY)
        self.assertIs(updater.resolve_transition('60-61'), updater.TRANSITION61)

    def test_pin128_pending_and_cross_pair_closed(self):
        with patch.object(updater, 'APPROVED128', None):
            with self.assertRaises(updater.UpdateError) as denied:
                updater.transition_pair(updater.TRANSITION128)
            self.assertEqual(denied.exception.code, 'target128_pin_pending')
        with patch.object(updater, 'APPROVED128', updater.APPROVED113):
            with self.assertRaises(updater.UpdateError) as denied:
                updater.transition_pair(updater.TRANSITION128)
            self.assertEqual(denied.exception.code, 'transition_has_no_artifact_change')

    def test_entrypoint128_defaults_and_rejects_other_registered_id(self):
        import subprocess
        entry = ROOT/'tools/windows/qa_artifact7_update128.py'
        common = [sys.executable,'-B',str(entry),'update','--source',str(ROOT)]
        default = subprocess.run(common,capture_output=True,text=True)
        self.assertEqual(default.returncode, 1)
        self.assertEqual(json.loads(default.stderr)['state'], 'explicit_pointer_required')
        for key in ('59-60','60-61','61-62','62-68','68-83','83-98','98-113'):
            denied = subprocess.run(common+['--transition',key],capture_output=True,text=True)
            self.assertEqual(denied.returncode, 1)
            self.assertEqual(json.loads(denied.stderr)['state'], 'entrypoint_transition_mismatch')


class Artifact128Acceptance(Artifact7Acceptance):
    transition = updater.TRANSITION128
    versioned_source = True
    outcomes = []
    observations = []

    def setUp(self):
        updater.require_transition(self.transition)
        super().setUp()

    def test_one_source113_bounded_transition128(self):
        item = self.create_fixture()
        with updater.profile_lock(item.pointer):
            with self.assertRaises(Exception) as busy:
                self.run_update(item)
        self.assertEqual(getattr(busy.exception,'code',None), 'profile_busy')
        updater.qa_module().control(item.lab.directory,'start')
        external_pid = (item.lab.directory/'data/postmaster.pid').read_text().splitlines()[0]
        with self.assertRaises(updater.UpdateError) as active:
            self.run_update(item)
        self.assertEqual(active.exception.code,'source7_pg_already_active')
        self.assertTrue(updater.pg_running(item.lab.directory))
        self.assertEqual((item.lab.directory/'data/postmaster.pid').read_text().splitlines()[0],external_pid)
        self.assertEqual(item.config.read_bytes(),item.original_config)
        # Explicit cleanup by the fixture actor; the updater never owns this PG.
        updater.qa_module().control(item.lab.directory,'stop')
        self.assert_immutable(item)
        success = self.run_update(item)
        self.assertEqual(success.state,'committed')
        self.assertFalse(updater.pg_running(item.lab.directory))
        self.assertFalse(updater.qa_module().running(item.lab.directory))
        selected = json.loads(item.config.read_text())
        self.assertEqual(updater.require_config_change(item.cfg,selected),updater.CHANGED_FIELDS)
        self.assertEqual((success.version/'previous-config.json').read_bytes(),item.original_config)
        self.assert_immutable(item)
        updater.qa_module().control(item.lab.directory,'start')
        self.assertEqual(snapshot(lambda q:self.owner_read(item,q)),item.before)
        self.assertEqual(updater.history(lambda q:self.owner_read(item,q),success.version/'server',7),item.history)
        self.assertEqual(self.owner_read(item,'SELECT oid FROM pg_database WHERE datname=current_database()'),item.database_oid)
        updater.qa_module().control(item.lab.directory,'stop')
        item.process = updater.start_supervisor(item.lab.directory,selected)
        client = Client(NativeHttp(selected))
        self.assertEqual(client.login('move-admin',item.password).status,200)
        actor = client.request('GET','/api/v1/me').json()['user']['id']
        revision = client.request('GET','/api/v1/systemhaus').json()['revision']
        response = client.request('POST','/api/v1/customers',{'name':'Artifact128 durable synthetic write'},
            {'If-Match':f'"{revision}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor})
        self.assertEqual(response.status,201)
        customer = response.json()['resource']['id']
        updater.stop_application(item.lab.directory,selected); item.process.wait(timeout=30)
        item.process = updater.start_supervisor(item.lab.directory,selected)
        self.assertEqual(client.request('GET','/api/v1/me').status,200)
        self.assertEqual(self.owner_read(item,f"SELECT count(*) FROM customer WHERE id='{customer}'"),'1')
        updater.stop_application(item.lab.directory,selected); item.process.wait(timeout=30)
        self.assertFalse(updater.pg_running(item.lab.directory))
        self.assert_immutable(item)
        self.observations.append(dict(singleNewSource113=True,versionedSource=True,profileLockRejected=True,
            externalPgRetained=True,fixtureActorCleanupExplicit=True,committedStopped=True,
            rowsHistoryOidPreserved=True,exactThreeConfigFields=True,privatePointerPreserved=True,
            fixtureWriteReadRestart=True,updaterSqlWrites=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',required=True,type=Path)
    parser.add_argument('--mode',choices=('contracts','native128'),required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=False)
    paths = ['tools/windows/qa_artifact7_update.py','tools/windows/qa_artifact7_update128.py',
        'tools/windows/qa_schema6_source.py','tools/windows/qa_schema6_real_candidate.py',
        'tools/windows/qa_schema_candidate.py','tools/windows/qa_schema_switch.py',
        'tools/windows/Qa-Local.py','tools/windows/windows_job.py',
        'development/server/tests/test_qa_artifact7_update.py','development/server/tests/test_qa_artifact7_update61.py',
        'development/server/tests/test_qa_artifact7_update128.py','development/server/tests/pg_support.py',
        'development/server/tests/test_inventory_movement_gui.py']
    hashes = lambda:{p:sha256(ROOT/p) for p in paths}
    frozen = hashes()
    source = updater.load_distribution(113)
    target = updater.transition_pair(updater.TRANSITION128)[1] if args.mode=='native128' else None
    suite = (unittest.defaultTestLoader.loadTestsFromTestCase(Transition128Contracts) if target is None else
             unittest.TestSuite([Artifact128Acceptance('test_one_source113_bounded_transition128')]))
    data = dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),mode=args.mode,
        sourceHashes=frozen,actualQaAccessed=False,newSyntheticSources=1 if target else 0,
        sourceManifestSha256=sha256(source.manifest),sourceDistributions=source.expected,
        targetManifestSha256=sha256(target.manifest) if target else None,
        targetDistributions=target.expected if target else None)
    with (args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(suite)
    data.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful(),
        inputsUnchanged=frozen==hashes(),sourceUnchanged=source.validate()==source.expected,
        targetUnchanged=target.validate()==target.expected if target else None,
        labs=Artifact128Acceptance.outcomes,observations=Artifact128Acceptance.observations)
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    return 0 if data['successful'] and data['inputsUnchanged'] and all(all(v.values()) for v in data['labs']) else 1


if __name__=='__main__':
    sys.exit(main())
