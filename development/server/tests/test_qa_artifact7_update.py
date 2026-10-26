"""60-C: one bounded Windows7 group, ONLY new synthetic laboratories."""
import argparse
from datetime import datetime, timezone
import copy
import json
from pathlib import Path
import platform
import shutil
import socket
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/windows'))
from pg_support import Lab, Client, free_port
from pg_lab_recovery import sha256
from test_inventory_movement_gui import fixture
from test_qa_schema6_real import NativeHttp
from test_postgres import EvidenceResult, Tee
from qa_schema6_real_candidate import load_target
from qa_schema6_source import PRIVATE_FILES
from qa_schema_candidate import snapshot
import qa_artifact7_update as updater


class Artifact7Acceptance(unittest.TestCase):
    outcomes = []
    observations = []
    transition = updater.LEGACY
    versioned_source = False

    def setUp(self):
        self.fixtures = []

    def create_fixture(self):
        baseline = updater.load_distribution(self.transition.source)
        lab = Lab('manual-qa-rc9-schema7').start()
        item = SimpleNamespace(lab=lab, process=None, cfg=None)
        self.fixtures.append(item)
        item.db = lab.create_database('manual-qa-rc9')
        item.ids, item.password = fixture(lab, item.db, baseline.server / 'RackClick.Server.dll')
        lab.grant_runtime(item.db)
        artifacts = lab.directory
        if self.versioned_source:
            artifacts = lab.directory / 'versions' / uuid.uuid4().hex
            artifacts.mkdir(parents=True)
        for name in ('server', 'frontend'):
            shutil.copytree(getattr(baseline, name), artifacts / name)
        item.cfg = dict(directory=str(lab.directory), profile='rc9', host='127.0.0.1', webPort=free_port(),
            pgPort=lab.port, database=item.db.name, connection=item.db.connection(lab.port),
            dllSha256=baseline.expected['server']['RackClick.Server.dll'], bundleSha256=baseline.expected['frontend']['app.js'],
            qaCustomerId=item.ids['customer'], qaCustomerName='Artifact7 synthetic source', restoreSourceSha256='0'*64,
            restoreCounts={'customers': 2, 'racks': 2, 'devices': 3, 'ports': 6, 'connections': 1})
        item.config = lab.directory / 'manual-qa.json'
        if self.versioned_source:
            item.cfg['artifactDirectory'] = str(artifacts)
        updater.save(item.config, item.cfg)
        for name in PRIVATE_FILES:
            (lab.directory / name).write_text('Synthetic artifact7 private fixture; never real QA\n', encoding='utf-8')
        (lab.directory / 'server.lock').write_bytes(b'0')
        home = lab.directory / 'artifact7-home'; home.mkdir()
        item.pointer = home / 'current.json'
        updater.save(item.pointer, {'directory': str(lab.directory)})
        item.original_config = item.config.read_bytes()
        item.pointer_bytes = item.pointer.read_bytes()
        source = updater.Source7(lab.directory, item.pointer, transition=self.transition)
        item.before = snapshot(source.sql)
        item.history = source.check_schema7()
        item.database_oid = source.sql('SELECT oid FROM pg_database WHERE datname=current_database()')
        item.immutable = source.hashes
        item.database_count = len(json.loads((lab.directory / 'lab.json').read_text())['databases'])
        lab.close()
        return item

    def tearDown(self):
        for item in self.fixtures:
            if item.cfg:
                cfg = json.loads(item.config.read_text())
                if updater.qa_module().running(item.lab.directory):
                    updater.stop_application(item.lab.directory, cfg)
                if updater.pg_running(item.lab.directory):
                    updater.qa_module().control(item.lab.directory, 'stop')
                if item.process:
                    item.process.wait(timeout=30)
            item.lab.close()
            self.outcomes.append(dict(nativeStopped=not updater.pg_running(item.lab.directory),
                applicationStopped=not updater.qa_module().running(item.lab.directory),
                serversStopped=all(s.process.poll() is not None for s in item.lab.servers)))

    def run_update(self, item, hook=None):
        return updater.update(item.lab.directory, item.pointer, hook=hook, transition=self.transition)

    def assert_immutable(self, item):
        self.assertEqual(item.pointer.read_bytes(), item.pointer_bytes)
        self.assertEqual({name:sha256(item.lab.directory/name) for name in item.immutable}, item.immutable)
        self.assertEqual(len(json.loads((item.lab.directory/'lab.json').read_text())['databases']), item.database_count)

    def fixture_actor_stop_and_restore_config(self, item):
        # This is the OTHER synthetic actor's explicit cleanup after an injected
        # start. It is not automatic updater rollback, and never operates real QA.
        self.assertTrue(updater.pg_running(item.lab.directory))
        self.assertEqual(snapshot(lambda q:self.owner_read(item,q)), item.before)
        updater.qa_module().control(item.lab.directory, 'stop')
        self.assertFalse(updater.pg_running(item.lab.directory))
        updater.atomic_bytes(item.config, item.original_config)

    def owner_read(self, item, query):
        from qa_schema_switch import read_owner
        return read_owner(item.lab.directory, item.cfg, query)

    def test_artifact7_bounded_success_and_failures(self):
        _, target = updater.transition_pair(self.transition)
        item = self.create_fixture()
        with self.assertRaises(updater.UpdateError):
            updater.Source7(item.lab.directory, item.pointer, real=True)
        altered = copy.deepcopy(target.expected)
        altered['server']['database/007-audit-context-families.sql'] = '0'*64
        with self.assertRaises(updater.UpdateError) as bad_sql:
            updater.require_same_sql7(altered, load_target(7).expected)
        self.assertEqual(bad_sql.exception.code, 'schema7_sql_must_be_identical')
        pin_name = f'APPROVED{self.transition.target}'
        with patch.object(updater, pin_name, (getattr(updater, pin_name)[0], '0'*64)):
            with self.assertRaises(updater.UpdateError) as bad_manifest:
                self.run_update(item)
        self.assertEqual(bad_manifest.exception.code, f'target{self.transition.target}_manifest_not_approved')
        with updater.profile_lock(item.pointer):
            with self.assertRaises(Exception) as busy:
                self.run_update(item)
        self.assertEqual(getattr(busy.exception, 'code', None), 'profile_busy')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', item.cfg['webPort'])); listener.listen()
            with self.assertRaises(Exception):
                self.run_update(item)
        updater.qa_module().control(item.lab.directory, 'start')
        with self.assertRaises(updater.UpdateError) as active:
            self.run_update(item)
        self.assertEqual(active.exception.code, 'source7_pg_already_active')
        self.assertTrue(updater.pg_running(item.lab.directory))
        updater.qa_module().control(item.lab.directory, 'stop')
        item.process = updater.start_supervisor(item.lab.directory, item.cfg)
        with self.assertRaises(Exception):
            self.run_update(item)
        self.assertTrue(updater.qa_module().ready(item.lab.directory, item.cfg))
        updater.stop_application(item.lab.directory, item.cfg); item.process.wait(timeout=30)

        # A start that really succeeded and then reported failure remains ours.
        qa = updater.qa_module(); control = qa.control
        def uncertain_start(directory, action):
            value = control(directory, action)
            if action == 'start':
                raise RuntimeError('Synthetic failure AFTER own PG started')
            return value
        with patch.object(updater, 'qa_module', return_value=qa), patch.object(qa, 'control', side_effect=uncertain_start):
            with self.assertRaises(updater.UpdateError) as uncertain:
                self.run_update(item)
        self.assertEqual(uncertain.exception.code, 'rolled_back')
        self.assertTrue(json.loads(uncertain.exception.result.journal.read_text())['stopConfirmed'])
        self.assertFalse(updater.pg_running(item.lab.directory))

        # Another actor starts PG before each launch helper: updater must reject
        # WITHOUT stopping it, even though it holds this profile's command lock.
        for stage in ('prepared', 'after_config'):
            external = {}
            def foreign_start(name, result):
                if name == stage:
                    updater.qa_module().control(item.lab.directory, 'start')
                    external['pid'] = (item.lab.directory/'data/postmaster.pid').read_text().splitlines()[0]
            with self.assertRaises(updater.UpdateError) as foreign:
                self.run_update(item, hook=foreign_start)
            self.assertEqual(foreign.exception.code, 'recovery_required')
            self.assertTrue(updater.pg_running(item.lab.directory))
            self.assertEqual((item.lab.directory/'data/postmaster.pid').read_text().splitlines()[0], external['pid'])
            self.fixture_actor_stop_and_restore_config(item)
            self.assert_immutable(item)

        def after_selection_failure(name, result):
            if name == 'after_config':
                raise RuntimeError('Synthetic failure AFTER atomic config selection')
        with self.assertRaises(updater.UpdateError) as rollback:
            self.run_update(item, hook=after_selection_failure)
        self.assertEqual(rollback.exception.code, 'rolled_back')
        self.assertEqual(item.config.read_bytes(), item.original_config)
        self.assertTrue(rollback.exception.result.version.is_dir())
        self.assertFalse(updater.pg_running(item.lab.directory))
        self.assert_immutable(item)

        success = self.run_update(item)
        self.assertEqual(success.state, 'committed')
        selected = json.loads(item.config.read_text())
        changed = {k for k in set(selected)|set(item.cfg) if selected.get(k)!=item.cfg.get(k)}
        self.assertLessEqual(changed, updater.CHANGED_FIELDS)
        self.assertIn('artifactDirectory', changed)
        self.assertEqual((success.version/'previous-config.json').read_bytes(), item.original_config)
        self.assertFalse(updater.pg_running(item.lab.directory))
        self.assert_immutable(item)
        updater.qa_module().control(item.lab.directory, 'start')
        self.assertEqual(snapshot(lambda q:self.owner_read(item,q)), item.before)
        self.assertEqual(updater.history(lambda q:self.owner_read(item,q), success.version/'server', 7), item.history)
        updater.qa_module().control(item.lab.directory, 'stop')
        # Actual application writes/readback/restart happen ONLY in this fixture,
        # after update committed. The updater itself did not authenticate or write.
        item.process = updater.start_supervisor(item.lab.directory, selected)
        self.assertEqual(self.owner_read(item, 'SELECT oid FROM pg_database WHERE datname=current_database()'), item.database_oid)
        client = Client(NativeHttp(selected))
        self.assertEqual(client.login('move-admin', item.password).status, 200)
        actor = client.request('GET', '/api/v1/me').json()['user']['id']
        revision = client.request('GET', '/api/v1/systemhaus').json()['revision']
        response = client.request('POST', '/api/v1/customers', {'name':'Artifact7 durable fixture write'},
            {'If-Match':f'"{revision}"', 'Idempotency-Key':str(uuid.uuid4()), 'X-RackClick-Actor':actor})
        self.assertEqual(response.status, 201)
        customer = response.json()['resource']['id']
        updater.stop_application(item.lab.directory, selected); item.process.wait(timeout=30)
        item.process = updater.start_supervisor(item.lab.directory, selected)
        self.assertEqual(client.request('GET', '/api/v1/me').status, 200)
        self.assertEqual(self.owner_read(item, f"SELECT count(*) FROM customer WHERE id='{customer}'"), '1')
        updater.stop_application(item.lab.directory, selected); item.process.wait(timeout=30)
        self.assert_immutable(item)

        # Separate NEW source7 keeps the no-activity baseline honest: all rows can
        # match after compensated DML while XID activity forbids file rollback.
        second = self.create_fixture()
        observed = {}
        def compensated(name, result):
            if name == 'after_start':
                before = snapshot(lambda q:self.owner_read(second,q))
                house = self.owner_read(second, 'SELECT id FROM systemhaus'); new = str(uuid.uuid4())
                second.lab.sql(second.db, f"BEGIN;INSERT INTO customer(id,systemhaus_id,name) VALUES('{new}','{house}','net-zero60');DELETE FROM customer WHERE id='{new}';COMMIT;", sensitive=True)
                self.assertEqual(snapshot(lambda q:self.owner_read(second,q)), before)
                reference = json.loads(result.journal.read_text())['activityBaseline']
                now = updater.activity_watermark(second.lab.directory, second.cfg)
                self.assertGreater(int(now['xmax']), int(reference['xmax']))
                observed.update(allRowsEqual=True, activityAdvanced=True)
                raise RuntimeError('Synthetic failure after compensated committed DML')
        with self.assertRaises(updater.UpdateError) as blocked:
            self.run_update(second, hook=compensated)
        self.assertEqual(blocked.exception.code, 'recovery_required')
        self.assertEqual(json.loads(second.config.read_text())['artifactDirectory'], str(blocked.exception.result.version))
        self.assertTrue(blocked.exception.result.version.is_dir())
        self.assertFalse(updater.pg_running(second.lab.directory))
        self.assert_immutable(second)
        self.observations.append(dict(sqlAndManifestRejected=True, activeAppAndPgNotStopped=True,
            sameControlLockRejected=True, uncertainOwnStartStopped=True, prelaunchExternalPgRetained=['prepared','after_config'],
            fixtureActorCleanupExplicit=True, noWriteConfigRollback=True, committedSuccess=True,
            databaseNeverReconstructedByUpdate=True, databaseOidPreserved=True, fixtureWriteReloadRestart=True,
            compensatedDmlRollbackDenied=True, **observed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    files = [Path(__file__).resolve(), ROOT/'tools/windows/qa_artifact7_update.py', ROOT/'tools/windows/qa_schema6_source.py',
        ROOT/'tools/windows/qa_schema6_real_candidate.py', ROOT/'tools/windows/qa_schema_switch.py', ROOT/'tools/windows/Qa-Local.py',
        ROOT/'tools/windows/windows_job.py', ROOT/'development/server/tests/pg_support.py', ROOT/'development/server/tests/test_inventory_movement_gui.py']
    hashes = lambda: {p.relative_to(ROOT).as_posix():sha256(p) for p in files}
    frozen = hashes(); target = updater.load_target60()
    data = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), sourceHashes=frozen,
        targetManifestSha256=sha256(target.manifest), actualQaAccessed=False, newSyntheticSources=2)
    with (args.evidence/'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout,output), verbosity=2, resultclass=EvidenceResult).run(
            unittest.TestSuite([Artifact7Acceptance('test_artifact7_bounded_success_and_failures')]))
    data.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful(),
        labs=Artifact7Acceptance.outcomes, observations=Artifact7Acceptance.observations,
        inputsUnchanged=frozen==hashes(), targetUnchanged=target.validate()==target.expected)
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2)+'\n', encoding='utf-8')
    return 0 if data['successful'] and data['inputsUnchanged'] and all(all(v.values()) for v in data['labs']) else 1


if __name__ == '__main__':
    sys.exit(main())
