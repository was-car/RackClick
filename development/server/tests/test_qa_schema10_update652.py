"""652: closed contracts and ONE shared freshly created Windows schema9 fixture.

Never reads an existing QA profile. Native execution needs the pinned root pair;
there is no manifest/digest override, implicit build or fixture reuse from disk.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import shutil
import socket
import sys
import unittest
from unittest.mock import patch
import uuid
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/windows'))
from pg_support import Lab, Client, free_port
from pg_lab_recovery import sha256
from test_inventory_movement_gui import fixture
from test_postgres import EvidenceResult, Tee
from qa_schema_candidate import snapshot
from qa_schema6_source import PRIVATE_FILES
from qa_schema6_real_candidate import history
import qa_schema10_source652 as contracts
import qa_schema10_candidate652 as copier
import qa_schema10_switch652 as coordinator
import qa_schema10_update652 as cli


class Closed652Contracts(unittest.TestCase):
    def test_pending_or_wrong_pin_fails_closed(self):
        with patch.object(contracts, 'TARGET652', None):
            with self.assertRaises(contracts.Schema10Error) as denied:
                contracts.load_target()
            self.assertEqual(denied.exception.code, 'target652_pin_pending')
        for value in (('elsewhere.json', '0' * 64), ('', ''), ['not', 'a-tuple']):
            with patch.object(contracts, 'TARGET652', value):
                with self.assertRaises(contracts.Schema10Error):
                    contracts.load_target()
        self.assertEqual(contracts.SOURCE_SHA256, 'c818294e27a40c94fe2ebf603709c94263820af1facca9a7d5c288cb70e8158e')
        self.assertEqual(contracts.NEW_TABLES, {'customer_device_templates', 'customer_device_template', 'customer_device_template_operation'})
        self.assertEqual([c.__name__ for c in contracts.Source532.__mro__], ['Source532', 'Source4', 'object'])
        source = contracts.load_source()
        self.assertEqual((source.schema, len(source.expected['server']), len(source.expected['frontend'])), (9, 18, 18))

    def test_initializer_secret_must_be_sealed_unchanged_and_inside_copy(self):
        directory = ROOT / '.local' / ('static-secret652-' + uuid.uuid4().hex)
        directory.mkdir(exist_ok=False)
        password = directory / 'init-password.txt'
        admin = directory / 'admin.pgpass'
        password.write_bytes(b'Synthetic non-operational initializer\n')
        admin.write_bytes(b'Synthetic non-operational passfile\n')
        expected = {p.name: sha256(p) for p in (password, admin)}
        copier.require_private_input_hashes(directory, expected)
        with self.assertRaises(contracts.Schema10Error):
            copier.require_private_input_hashes(directory, {'admin.pgpass':expected['admin.pgpass']})
        original = password.read_bytes()
        password.write_bytes(original + b'corrupt')
        with self.assertRaises(contracts.Schema10Error):
            copier.require_private_input_hashes(directory, expected)
        password.write_bytes(original)
        copier.require_private_input_hashes(directory, expected)
        with self.assertRaises(contracts.Schema10Error):
            copier.require_private_input_hashes(directory, {**expected, '../../AGENTS.md':sha256(ROOT / 'AGENTS.md')})
        self.assertTrue(directory.is_relative_to(ROOT / '.local'))
        self.assertFalse((directory / 'data').exists())

    def test_foreign_prelaunch_does_not_grant_ownership(self):
        runtime = coordinator.OwnedRuntime(ROOT, {'webPort': 12345})
        with patch.object(coordinator, 'app_stopped'), patch.object(coordinator, 'pg_running', return_value=True), \
                patch.object(coordinator, 'qa_module') as qa:
            with self.assertRaises(contracts.Schema10Error):
                runtime.start_pg()
            runtime.stop()
            self.assertFalse(runtime.owned)
            qa.assert_not_called()

    def test_cli_reports_schema9_after_rollback_and_unknown_on_failure(self):
        arguments = ['qa_schema10_update652.py', 'rollback', '--source', str(ROOT),
                     '--pointer', str(ROOT / 'synthetic.json'), '--candidate', str(ROOT)]
        output = io.StringIO()
        with patch.object(sys, 'argv', arguments), patch.object(cli, 'rollback', return_value=SimpleNamespace(state='rolled_back')), \
                patch.object(sys, 'stdout', output):
            self.assertEqual(cli.main(), 0)
        data = json.loads(output.getvalue())
        self.assertEqual((data['sourceSchema'], data['candidateSchema'], data['selectedSchema']), (9, 10, 9))
        errors = io.StringIO()
        with patch.object(sys, 'argv', arguments), patch.object(cli, 'rollback', side_effect=contracts.Schema10Error('recovery_required')), \
                patch.object(sys, 'stderr', errors):
            self.assertEqual(cli.main(), 1)
        self.assertIsNone(json.loads(errors.getvalue())['selectedSchema'])
        self.assertIsNone(json.loads(errors.getvalue())['leftRunning'])


class Native652Acceptance(unittest.TestCase):
    outcomes = []
    observations = []

    def setUp(self):
        self.source_lab = None
        self.candidate = None
        self.extra_servers = []
        baseline = contracts.load_source()
        contracts.load_target()  # No native allocation while target pin is pending.
        self.source_lab = lab = Lab('manual-qa-rc9-schema9').start()
        self.addCleanup(lab.close)
        self.db = lab.create_database('manual-qa-rc9')
        self.ids, self.password = fixture(lab, self.db, baseline.server / 'RackClick.Server.dll')
        lab.grant_runtime(self.db)
        art = lab.directory / 'versions' / uuid.uuid4().hex
        for name in ('server', 'frontend'):
            shutil.copytree(getattr(baseline, name), art / name)
        self.cfg = dict(directory=str(lab.directory), profile='rc9', host='127.0.0.1', webPort=free_port(),
            pgPort=lab.port, database=self.db.name, connection=self.db.connection(lab.port), artifactDirectory=str(art),
            dllSha256=baseline.expected['server']['RackClick.Server.dll'], bundleSha256=baseline.expected['frontend']['app.js'],
            qaCustomerId=self.ids['customer'], qaCustomerName='Synthetic schema10 source Ω',
            restoreSourceSha256='0' * 64, restoreCounts={'customers': 2, 'racks': 2, 'devices': 3, 'ports': 6, 'connections': 1})
        copier.save(lab.directory / 'manual-qa.json', self.cfg)
        for name in PRIVATE_FILES:
            (lab.directory / name).write_text('Synthetic652 private fixture Ω; no real QA data\n', encoding='utf-8')
        (lab.directory / 'server.lock').write_bytes(b'0')
        home = lab.directory / 'schema10-home'; home.mkdir()
        self.pointer = home / 'current.json'
        copier.save(self.pointer, {'directory': str(lab.directory)})
        self.pointer_bytes = self.pointer.read_bytes()
        # Historical context deliberately NONEMPTY: no schema4 emptiness assumption.
        house, actor = lab.sql(self.db, "SELECT id FROM systemhaus;SELECT id FROM app_user WHERE username='move-admin'").splitlines()
        event, request, operation = (str(uuid.uuid4()) for _ in range(3))
        lab.sql(self.db, f"""BEGIN;
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,after_json)
              VALUES('{event}','{house}','{actor}','{request}','synthetic652.history','{house}','{{}}');
            INSERT INTO audit_context(event_id,capture_version,scope_kind,revision_scope,revision_before,revision_after,outcome)
              VALUES('{event}',1,'systemhaus','systemhaus',1,2,'committed');
            INSERT INTO audit_context_object(event_id,position,kind,object_id,relation)
              VALUES('{event}',1,'user','{actor}','target');
            INSERT INTO app_session(token_hash,user_id,csrf_hash,expires_at)
              VALUES('{'1' * 64}','{actor}','{'2' * 64}','2099-01-01T00:00:00Z');
            INSERT INTO user_catalog_favorites(systemhaus_id,owner_id,revision) VALUES('{house}','{actor}',1);
            INSERT INTO user_catalog_favorite(systemhaus_id,owner_id,preset_key) VALUES('{house}','{actor}','pdu');
            INSERT INTO user_catalog_favorite_operation(systemhaus_id,owner_id,request_id,request_hash,state,operation_id,revision,result_json)
              VALUES('{house}','{actor}','{request}','{'A' * 64}','committed','{operation}',1,'{{}}');
            COMMIT;""", sensitive=True)
        # Seed existing private bytes/receipt through the closed source532 API,
        # only inside this freshly allocated fixture. Never authenticates real QA.
        seed_server = lab.start_server(self.db, dll=baseline.server / 'RackClick.Server.dll', frontend=baseline.frontend)
        seed_client = Client(seed_server)
        self.assertEqual(seed_client.login('move-admin', self.password).status, 200)
        actor_id = seed_client.request('GET', '/api/v1/me').json()['user']['id']
        source_revision = seed_client.request('GET', f"/api/v1/customers/{self.ids['customer']}/project").json()['revision']
        captured = seed_client.request('POST', f"/api/v1/customers/{self.ids['customer']}/catalog/private-templates",
            {'type':'capture','deviceId':self.ids['a'],'name':'Plantilla histórica Ω','sourceRevision':source_revision},
            {'If-Match':'"templates-0"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor_id})
        self.assertEqual(captured.status, 200)
        seed_server.close()
        self.source = contracts.Source532(lab.directory, self.pointer)
        self.before = snapshot(self.source.sql)
        self.history9 = self.source.check_schema9()
        self.assertGreaterEqual(self.before['audit_context']['rows'], 1)
        self.assertGreaterEqual(self.before['audit_context_object']['rows'], 1)
        self.assertEqual(len(self.before), 30)
        self.assertEqual(self.before['app_user']['rows'], 4)
        self.assertEqual(lab.sql(self.db, "SELECT count(*) FROM permission_grant WHERE capability='templates.publish'"), '0')
        self.pg_configs = {name: sha256(lab.directory / 'data' / name) for name in ('postgresql.conf', 'pg_hba.conf', 'pg_ident.conf')}
        for name in ('app_user', 'app_session', 'user_catalog_favorites', 'user_catalog_favorite', 'user_catalog_favorite_operation', 'inventory_device', 'inventory_connection', 'user_device_templates', 'user_device_template', 'user_device_template_operation'):
            self.assertGreater(self.before[name]['rows'], 0)
        lab.close()

    def tearDown(self):
        for server in reversed(self.extra_servers):
            server.close()
        rows = []
        for directory, cfg in ([ (self.candidate.directory, self.candidate.cfg) ] if self.candidate else []) + \
                ([ (self.source_lab.directory, self.cfg) ] if self.source_lab else []):
            # Test actor owns these newly allocated fixture directories, including
            # its explicit foreign-start injections; the product must not stop them.
            if coordinator.qa_module().running(directory):
                coordinator.stop_application(directory, cfg)
            if coordinator.pg_running(directory):
                coordinator.qa_module().control(directory, 'stop')
            rows.append({'applicationStopped': not coordinator.qa_module().running(directory),
                         'postgresqlStopped': not coordinator.pg_running(directory)})
        if self.candidate:
            self.candidate.close()
        if self.source_lab:
            self.source_lab.close()
        self.outcomes.extend(rows)

    def activate(self, hook=None):
        return coordinator.activate(self.source_lab.directory, self.pointer, self.candidate.directory, hook=hook)

    def test_one_shared_copy_quiet_activation_recovery_and_negatives(self):
        lab = self.source_lab
        with self.assertRaises(contracts.Schema10Error):
            contracts.Source532(lab.directory, self.pointer, real=True)
        with coordinator.profile_lock(self.pointer):
            with self.assertRaises(Exception) as busy:
                coordinator.prepare_operation(lab.directory, self.pointer)
        self.assertEqual(getattr(busy.exception, 'code', None), 'profile_busy')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', self.cfg['webPort'])); listener.listen()
            with self.assertRaises(contracts.Schema10Error):
                coordinator.prepare_operation(lab.directory, self.pointer)
        coordinator.qa_module().control(lab.directory, 'start')
        with self.assertRaises(contracts.Schema10Error) as active:
            coordinator.prepare_operation(lab.directory, self.pointer)
        self.assertEqual(active.exception.code, 'source532_pg_already_active')
        self.assertTrue(coordinator.pg_running(lab.directory))
        coordinator.qa_module().control(lab.directory, 'stop')

        control = coordinator.start_private_pg652
        raised = []
        def uncertain_source(directory):
            result = control(directory)
            if directory == lab.directory and not raised:
                raised.append(True)
                raise RuntimeError('Synthetic failure after own PG really started')
            return result
        with patch.object(coordinator, 'start_private_pg652', side_effect=uncertain_source):
            with self.assertRaises(contracts.Schema10Error) as uncertain:
                coordinator.prepare_operation(lab.directory, self.pointer)
        self.assertEqual(uncertain.exception.code, 'preparation_failed')
        self.assertFalse(coordinator.pg_running(lab.directory))
        self.assertEqual(self.pointer.read_bytes(), self.pointer_bytes)

        prepared = coordinator.prepare_operation(lab.directory, self.pointer)
        self.candidate = candidate = prepared.candidate
        self.assertEqual(prepared.state, 'prepared')
        self.assertFalse(coordinator.pg_running(candidate.directory))
        self.assertEqual(candidate.record['sourceSnapshot'], self.before)
        self.assertEqual(candidate.record['sourceHistory'], self.history9)
        self.assertTrue(all(candidate.record['candidateSnapshot'][n]['rows'] == 0 for n in contracts.NEW_TABLES))
        self.assertEqual(candidate.record['candidateSnapshot']['audit_context'], self.before['audit_context'])
        self.assertEqual(candidate.record['candidateSnapshot']['app_user'], self.before['app_user'])
        self.assertEqual(candidate.record['candidateSnapshot']['app_session'], self.before['app_session'])
        self.assertEqual(len(candidate.record['candidateSnapshot']), 33)
        for name in ('user_catalog_favorites', 'user_catalog_favorite', 'user_catalog_favorite_operation', 'inventory_device', 'inventory_connection', 'user_device_templates', 'user_device_template', 'user_device_template_operation'):
            self.assertEqual(candidate.record['candidateSnapshot'][name], self.before[name])
        target_pg_configs = {name: sha256(candidate.directory / 'data' / name) for name in self.pg_configs}
        self.assertEqual(candidate.cfg['webPort'], self.cfg['webPort'])
        self.assertEqual([sha256(lab.directory / n) for n in PRIVATE_FILES], [sha256(candidate.directory / n) for n in PRIVATE_FILES])
        for db in (candidate.database, candidate.recovered):
            self.assertNotIn(db.name, (self.db.name,))
            self.assertTrue(db.owner_password not in (self.db.owner_password, self.db.runtime_password), 'Owner secret must be new')
            self.assertTrue(db.runtime_password not in (self.db.owner_password, self.db.runtime_password), 'Runtime secret must be new')
        coordinator.validate_operation(lab.directory, self.pointer, candidate.directory)
        copied = copier.load_prepared(candidate.directory)
        self.assertTrue(copied.cfg == candidate.cfg, 'Reconstructed private configuration must match')
        private = candidate.directory / PRIVATE_FILES[0]
        original = private.read_bytes()
        private.write_bytes(original + b'Synthetic corrupt copy')
        try:
            with self.assertRaises(contracts.Schema10Error):
                copier.load_prepared(candidate.directory)
        finally:
            private.write_bytes(original)
        copier.save(self.pointer, {'directory': str(ROOT)})
        try:
            with self.assertRaises(contracts.Schema10Error):
                self.activate()
        finally:
            self.pointer.write_bytes(self.pointer_bytes)

        # A real target start followed by uncertainty must still be stopped.
        raised.clear()
        def uncertain_target(directory):
            result = control(directory)
            if directory == candidate.directory and not raised:
                raised.append(True)
                raise RuntimeError('Synthetic failed return after target PG start')
            return result
        with patch.object(coordinator, 'start_private_pg652', side_effect=uncertain_target):
            with self.assertRaises(contracts.Schema10Error) as uncertain:
                self.activate()
        self.assertEqual(uncertain.exception.code, 'rolled_back')
        self.assertFalse(coordinator.pg_running(candidate.directory))
        self.assertEqual(self.pointer.read_bytes(), self.pointer_bytes)

        def fail_after_pointer(name, result):
            if name == 'after_pointer':
                raise RuntimeError('Synthetic failure after atomic pointer replacement')
        with self.assertRaises(contracts.Schema10Error) as rolled:
            self.activate(fail_after_pointer)
        self.assertEqual(rolled.exception.code, 'rolled_back')
        self.assertEqual(self.pointer.read_bytes(), self.pointer_bytes)

        success = self.activate()
        self.assertEqual(success.state, 'committed')
        self.assertFalse(coordinator.pg_running(candidate.directory))
        self.assertEqual(json.loads(self.pointer.read_bytes()), {'directory': str(candidate.directory)})
        coordinator.validate_operation(lab.directory, self.pointer, candidate.directory, selected=True)
        result = coordinator.rollback(lab.directory, self.pointer, candidate.directory)
        self.assertEqual(result.state, 'rolled_back')
        self.assertEqual(self.pointer.read_bytes(), self.pointer_bytes)

        def foreign_start(name, result):
            if name == 'prepared':
                coordinator.start_private_pg652(candidate.directory)
        with self.assertRaises(contracts.Schema10Error) as foreign:
            self.activate(foreign_start)
        self.assertEqual(foreign.exception.code, 'recovery_required')
        self.assertTrue(coordinator.pg_running(candidate.directory))
        self.assertEqual(self.pointer.read_bytes(), self.pointer_bytes)
        coordinator.qa_module().control(candidate.directory, 'stop')  # Explicit fixture actor cleanup.

        observed = {}
        def compensated_write(name, result):
            if name == 'after_start':
                before = snapshot(candidate.sql)
                house = candidate.sql('SELECT id FROM systemhaus')
                identity = str(uuid.uuid4())
                candidate.lab.sql(candidate.database, f"BEGIN;INSERT INTO customer(id,systemhaus_id,name) VALUES('{identity}','{house}','Synthetic net-zero652');DELETE FROM customer WHERE id='{identity}';COMMIT;", sensitive=True)
                self.assertEqual(snapshot(candidate.sql), before)
                current = copier.activity_watermark(candidate.directory, candidate.cfg)
                self.assertGreater(int(current['xmax']), int(candidate.record['candidateActivityBaseline']['xmax']))
                observed.update(netZeroRowsEqual=True, activityAdvanced=True)
                raise RuntimeError('Synthetic failure after compensated committed write')
        with self.assertRaises(contracts.Schema10Error) as changed:
            self.activate(compensated_write)
        self.assertEqual(changed.exception.code, 'recovery_required')
        selected = self.pointer.read_bytes()
        self.assertEqual(json.loads(selected), {'directory': str(candidate.directory)})
        self.assertFalse(coordinator.pg_running(candidate.directory))
        with self.assertRaises(contracts.Schema10Error) as denied:
            coordinator.rollback(lab.directory, self.pointer, candidate.directory)
        self.assertEqual(denied.exception.code, 'recovery_required')
        self.assertEqual(self.pointer.read_bytes(), selected)

        # Verify compatible9 by actual DLL532/DB9 startup and application account
        # authentication ONLY in this new copy, after rollback is already blocked.
        runtime = coordinator.OwnedRuntime(candidate.directory, candidate.cfg)
        runtime.start_pg()
        try:
            self.assertEqual(snapshot(lambda q: candidate.sql(q, recovery=True)), self.before)
            self.assertEqual(history(lambda q: candidate.sql(q, recovery=True), candidate.directory / 'versions/schema9-recovery/server', 9), self.history9)
            server = candidate.lab.start_server(candidate.recovered,
                dll=candidate.directory / 'versions/schema9-recovery/server/RackClick.Server.dll',
                frontend=candidate.directory / 'versions/schema9-recovery/frontend')
            self.extra_servers.append(server)
            self.assertEqual(server.request('GET', '/health/ready').status, 200)
            self.assertEqual(Client(server).login('move-reader', self.password).status, 200)
            server.close()
        finally:
            runtime.stop()
        source_runtime = coordinator.OwnedRuntime(lab.directory, self.cfg)
        source_runtime.start_pg()
        try:
            copier.verify_source(self.source, candidate.record)
        finally:
            source_runtime.stop()
        self.assertEqual(self.pointer.read_bytes(), selected)
        self.assertTrue(candidate.directory.is_dir())
        # A normal historical start must restore the normal server setting.
        # Run last: no source/target baseline is renewed to accept this activity.
        for directory, cfg in ((lab.directory, self.cfg), (candidate.directory, candidate.cfg)):
            coordinator.qa_module().control(directory, 'start')
            try:
                self.assertEqual(coordinator.read_owner(directory, cfg, 'SHOW autovacuum'), 'on')
            finally:
                coordinator.qa_module().control(directory, 'stop')
        self.source.unchanged(pointer=False); candidate.validate_static()
        self.assertEqual({n: sha256(lab.directory / 'data' / n) for n in self.pg_configs}, self.pg_configs)
        self.assertEqual({n: sha256(candidate.directory / 'data' / n) for n in target_pg_configs}, target_pg_configs)
        self.observations.append(dict(oneSourceFixture=True, sourceTechnicalAuthentication=False,
            fullSchema9RowsAndHistoryCopied=True, nonemptyHistoricalContextRetained=True,
            newTablesInitiallyEmpty=True, newPostgresqlIdentities=True, compatible9StartupAndAccount=True,
            quietActivationAndExplicitRollback=True, uncertainOwnedLaunchStopped=True,
            foreignLaunchRetained=True, compensatedWriteBlocksRollback=True, allBranchesRetained=True,
            normalStartRestoresAutovacuum=True, persistentPostgresqlConfigHashesUnchanged=True, favoritesAndInventoryRetained=True, **observed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--group', choices=('contracts', 'native', 'private-inputs', 'all'), default='all')
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    args.evidence.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__).resolve()] + [ROOT / 'tools/windows' / n for n in
        ('qa_schema10_source652.py', 'qa_schema10_candidate652.py', 'qa_schema10_switch652.py', 'qa_schema10_update652.py',
         'Qa-Local.py', 'qa_schema_switch.py', 'windows_job.py')]
    sources += [ROOT / 'development/server/tests/pg_support.py', ROOT / 'development/server/tests/test_inventory_movement_gui.py']
    def hashes():
        return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources}
    before = hashes()
    suites = []
    if args.group in ('contracts', 'all'):
        suites.append(unittest.defaultTestLoader.loadTestsFromTestCase(Closed652Contracts))
    if args.group == 'private-inputs':
        suites.append(unittest.defaultTestLoader.loadTestsFromName('test_initializer_secret_must_be_sealed_unchanged_and_inside_copy', Closed652Contracts))
    if args.group in ('native', 'all'):
        suites.append(unittest.defaultTestLoader.loadTestsFromTestCase(Native652Acceptance))
    with (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(suites))
    data = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), group=args.group,
        testsRun=result.testsRun, successful=result.wasSuccessful(), cases=result.records,
        sourceHashes=before, inputsUnchanged=before == hashes(), actualQaAccessed=False,
        labs=Native652Acceptance.outcomes, observations=Native652Acceptance.observations)
    (args.evidence / 'result.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return 0 if data['successful'] and data['inputsUnchanged'] and all(all(row.values()) for row in data['labs']) else 1


if __name__ == '__main__':
    sys.exit(main())
