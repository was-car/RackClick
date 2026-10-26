"""909: closed contracts and ONE new shared Windows PostgreSQL11 fixture.

Never reads an existing QA profile. Native execution needs the pinned root pair;
there is no manifest/digest override, implicit build or fixture reuse from disk.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import msvcrt
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
import qa_relations11_source909 as contracts
import qa_relations11_candidate909 as copier
import qa_relations11_switch909 as coordinator
import qa_relations11_update909 as cli
from test_qa_xls11_update847 import Native847Acceptance
import qa_xls11_switch847 as old_coordinator


class Closed909Contracts(unittest.TestCase):
    def test_pending_or_wrong_pin_fails_closed(self):
        with patch.object(contracts, 'TARGET909', None):
            with self.assertRaises(contracts.Schema11Error) as denied:
                contracts.load_target()
            self.assertEqual(denied.exception.code, 'target909_pin_invalid')
        for value in (('elsewhere.json', '0' * 64), ('', ''), ['not', 'a-tuple']):
            with patch.object(contracts, 'TARGET909', value):
                with self.assertRaises(contracts.Schema11Error):
                    contracts.load_target()
        self.assertEqual(contracts.SOURCE_SHA256, '511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5')
        self.assertEqual([c.__name__ for c in contracts.Source832.__mro__], ['Source832', 'Source4', 'object'])
        source = contracts.load_source()
        self.assertEqual((source.revision, source.schema, len(source.expected['server']), len(source.expected['frontend'])), (832, 11, 20, 18))
        target = contracts.load_target()
        self.assertEqual((target.revision, target.schema, len(target.expected['server']), len(target.expected['frontend'])), (849, 11, 20, 18))
        sql = lambda d: {k:v for k,v in d.expected['server'].items() if k.startswith('database/')}
        self.assertEqual(sql(source), sql(target))
        self.assertEqual(source.expected['server'],target.expected['server'])
        self.assertNotEqual(source.expected['frontend']['app.js'],target.expected['frontend']['app.js'])
        self.assertEqual({k:v for k,v in source.expected['frontend'].items() if k != 'app.js'},
                         {k:v for k,v in target.expected['frontend'].items() if k != 'app.js'})

    def test_initializer_secret_must_be_sealed_unchanged_and_inside_copy(self):
        directory = ROOT / '.local' / ('static-secret909-' + uuid.uuid4().hex)
        directory.mkdir(exist_ok=False)
        password = directory / 'init-password.txt'
        admin = directory / 'admin.pgpass'
        password.write_bytes(b'Synthetic non-operational initializer\n')
        admin.write_bytes(b'Synthetic non-operational passfile\n')
        expected = {p.name: sha256(p) for p in (password, admin)}
        copier.require_private_input_hashes(directory, expected)
        with self.assertRaises(contracts.Schema11Error):
            copier.require_private_input_hashes(directory, {'admin.pgpass':expected['admin.pgpass']})
        original = password.read_bytes()
        password.write_bytes(original + b'corrupt')
        with self.assertRaises(contracts.Schema11Error):
            copier.require_private_input_hashes(directory, expected)
        password.write_bytes(original)
        copier.require_private_input_hashes(directory, expected)
        with self.assertRaises(contracts.Schema11Error):
            copier.require_private_input_hashes(directory, {**expected, '../../AGENTS.md':sha256(ROOT / 'AGENTS.md')})
        self.assertTrue(directory.is_relative_to(ROOT / '.local'))
        self.assertFalse((directory / 'data').exists())

    def test_foreign_prelaunch_does_not_grant_ownership(self):
        runtime = coordinator.OwnedRuntime(ROOT, {'webPort': 12345})
        with patch.object(coordinator, 'app_stopped'), patch.object(coordinator, 'pg_running', return_value=True), \
                patch.object(coordinator, 'qa_module') as qa:
            with self.assertRaises(contracts.Schema11Error):
                runtime.start_pg()
            runtime.stop()
            self.assertFalse(runtime.owned)
            qa.assert_not_called()

    def test_cli_distinguishes_revisions_at_same_schema_and_unknown_failure(self):
        arguments = ['qa_relations11_update909.py', 'rollback', '--source', str(ROOT),
                     '--pointer', str(ROOT / 'synthetic.json'), '--candidate', str(ROOT)]
        output = io.StringIO()
        with patch.object(sys, 'argv', arguments), patch.object(cli, 'rollback', return_value=SimpleNamespace(state='rolled_back')), \
                patch.object(sys, 'stdout', output):
            self.assertEqual(cli.main(), 0)
        data = json.loads(output.getvalue())
        self.assertEqual((data['sourceSchema'], data['candidateSchema'], data['selectedSchema']), (11, 11, 11))
        self.assertEqual((data['sourceRevision'], data['candidateRevision'], data['selectedRevision']), (832, 849, 832))
        errors = io.StringIO()
        with patch.object(sys, 'argv', arguments), patch.object(cli, 'rollback', side_effect=contracts.Schema11Error('recovery_required')), \
                patch.object(sys, 'stderr', errors):
            self.assertEqual(cli.main(), 1)
        self.assertIsNone(json.loads(errors.getvalue())['selectedSchema'])
        self.assertIsNone(json.loads(errors.getvalue())['selectedRevision'])
        self.assertIsNone(json.loads(errors.getvalue())['leftRunning'])


class Native909Acceptance(unittest.TestCase):
    outcomes = []
    observations = []

    def setUp(self):
        # Reuse only the historical *fixture setup*, never its old test/result.
        # It creates a new712 source; a new847 copy yields the required832 main
        # plus separate712/11 recovery with genuine prepared847 inputs/seals.
        Native847Acceptance.setUp(self)
        self.seed_lab = self.source_lab
        self.fixture832 = old_coordinator.prepare_operation(self.seed_lab.directory, self.pointer).candidate
        self.source_lab = lab = self.fixture832.lab
        self.addCleanup(lab.close)
        self.db, self.cfg = self.fixture832.database, self.fixture832.cfg
        (lab.directory / 'server.lock').write_bytes(b'0')
        home = lab.directory / 'relations11-home'; home.mkdir()
        self.pointer = home / 'current.json'
        copier.save(self.pointer, {'directory':str(lab.directory)})
        self.pointer_bytes = self.pointer.read_bytes()
        runtime = old_coordinator.OwnedRuntime(lab.directory,self.cfg)
        self.addCleanup(runtime.stop)
        runtime.start_pg()
        try:
            # Source primary and old recovery intentionally diverge. New849 and
            # new recovery832 must both copy ONLY the current primary832 rows.
            lab.sql(self.db,f"UPDATE customer SET name='Current832 primary Ω' WHERE id='{self.ids['customer']}'",sensitive=True)
            lab.sql(self.fixture832.recovered,"UPDATE systemhaus SET name='Independent recovery712 Ω'",sensitive=True)
            server = lab.start_server(self.db,dll=lab.directory/'server/RackClick.Server.dll',frontend=lab.directory/'frontend')
            self.extra_servers.append(server)
            client = Client(server)
            client.cookie,client.csrf,actor = self.seed_session
            revision = client.request('GET',f"/api/v1/customers/{self.ids['customer']}/project").json()['revision']
            self.existing_xls_request = str(uuid.uuid4())
            response = client.request('POST',f"/api/v1/customers/{self.ids['customer']}/reports/xls-html",{'rackId':self.ids['rackA']},
                {'If-Match':f'"{revision}"','Idempotency-Key':self.existing_xls_request,'X-RackClick-Actor':actor})
            self.assertEqual(response.status,200)
            self.existing_xls_result = response.json()
            server.close()
        finally:
            runtime.stop()
        self.source = contracts.Source832(lab.directory,self.pointer)
        runtime.start_pg()
        try:
            self.source_states = self.source.database_states()
            self.before = self.source_states['primary']['snapshot']
            self.history11 = self.source_states['primary']['history']
            self.assertEqual(len(self.before),35)
            self.assertEqual(len(self.source_states['recovery712']['snapshot']),35)
            self.assertNotEqual(self.before,self.source_states['recovery712']['snapshot'])
        finally:
            runtime.stop()
        self.pg_configs = {name:sha256(lab.directory/'data'/name) for name in ('postgresql.conf','pg_hba.conf','pg_ident.conf')}
        self.source_static_hashes = dict(self.source.hashes)

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
        if getattr(self,'seed_lab',None) is not None:
            self.seed_lab.close()
            rows.append({'applicationStopped':not coordinator.qa_module().running(self.seed_lab.directory),
                         'postgresqlStopped':not coordinator.pg_running(self.seed_lab.directory)})
        self.outcomes.extend(rows)

    def activate(self, hook=None):
        return coordinator.activate(self.source_lab.directory, self.pointer, self.candidate.directory, hook=hook)

    def test_one_shared_copy_quiet_activation_recovery_and_negatives(self):
        lab = self.source_lab
        with self.assertRaises(contracts.Schema11Error):
            contracts.Source832(lab.directory, self.pointer, real=True)
        self.assertNotIn('artifactDirectory', self.cfg)
        for relative in ('xls11-prepared.sha256','versions/xls11-source712-recovery/frontend/app.js'):
            path = lab.directory / relative
            original = path.read_bytes()
            path.write_bytes(original + b'\nsynthetic corruption909\n')
            try:
                with self.assertRaises(contracts.Schema11Error):
                    coordinator.prepare_operation(lab.directory,self.pointer)
                self.assertFalse(coordinator.pg_running(lab.directory))
            finally:
                path.write_bytes(original)
        self.source.unchanged()
        # A stale or forged PID marker is uncertainty, never permission to stop
        # another process. Only this test actor removes its synthetic marker.
        marker = lab.directory / 'ready.json'
        copier.save(marker, {'pid': 2147483647})
        try:
            with self.assertRaises(contracts.Schema11Error):
                coordinator.prepare_operation(lab.directory, self.pointer)
            self.assertEqual(json.loads(marker.read_bytes()), {'pid': 2147483647})
            self.assertFalse((lab.directory / 'stop.request').exists())
        finally:
            marker.unlink()
        with (lab.directory / 'server.lock').open('r+b') as locked:
            msvcrt.locking(locked.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                with self.assertRaises(contracts.Schema11Error):
                    coordinator.prepare_operation(lab.directory, self.pointer)
                self.assertFalse(coordinator.pg_running(lab.directory))
            finally:
                locked.seek(0)
                msvcrt.locking(locked.fileno(), msvcrt.LK_UNLCK, 1)
        with coordinator.profile_lock(self.pointer):
            with self.assertRaises(Exception) as busy:
                coordinator.prepare_operation(lab.directory, self.pointer)
        self.assertEqual(getattr(busy.exception, 'code', None), 'profile_busy')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', self.cfg['webPort'])); listener.listen()
            with self.assertRaises(contracts.Schema11Error):
                coordinator.prepare_operation(lab.directory, self.pointer)
        coordinator.qa_module().control(lab.directory, 'start')
        with self.assertRaises(contracts.Schema11Error) as active:
            coordinator.prepare_operation(lab.directory, self.pointer)
        self.assertEqual(active.exception.code, 'source832_pg_already_active')
        self.assertTrue(coordinator.pg_running(lab.directory))
        coordinator.qa_module().control(lab.directory, 'stop')

        control = coordinator.start_private_pg909
        raised = []
        def uncertain_source(directory):
            result = control(directory)
            if directory == lab.directory and not raised:
                raised.append(True)
                raise RuntimeError('Synthetic failure after own PG really started')
            return result
        with patch.object(coordinator, 'start_private_pg909', side_effect=uncertain_source):
            with self.assertRaises(contracts.Schema11Error) as uncertain:
                coordinator.prepare_operation(lab.directory, self.pointer)
        self.assertEqual(uncertain.exception.code, 'preparation_failed')
        self.assertFalse(coordinator.pg_running(lab.directory))
        self.assertEqual(self.pointer.read_bytes(), self.pointer_bytes)

        prepared = coordinator.prepare_operation(lab.directory, self.pointer)
        self.candidate = candidate = prepared.candidate
        self.assertEqual(prepared.state, 'prepared')
        self.assertFalse(coordinator.pg_running(candidate.directory))
        self.assertEqual(candidate.record['sourceSnapshot'], self.before)
        self.assertEqual(candidate.record['sourceHistory'], self.history11)
        self.assertEqual(candidate.record['sourceDatabaseStates'],self.source_states)
        self.assertNotEqual(candidate.record['sourceSnapshot'],self.source_states['recovery712']['snapshot'])
        self.assertEqual(candidate.record['candidateSnapshot'], self.before)
        self.assertEqual(candidate.record['candidateHistory'], self.history11)
        self.assertEqual((candidate.record['sourceSchema'],candidate.record['candidateSchema']), (11,11))
        self.assertEqual((candidate.record['sourceRevision'],candidate.record['candidateRevision']), (832,849))
        self.assertFalse((candidate.directory / 'migration-private.log').exists())
        self.assertEqual(candidate.record['candidateSnapshot']['audit_context'], self.before['audit_context'])
        self.assertEqual(candidate.record['candidateSnapshot']['app_user'], self.before['app_user'])
        self.assertEqual(candidate.record['candidateSnapshot']['app_session'], self.before['app_session'])
        self.assertEqual(len(candidate.record['candidateSnapshot']), 35)
        for name in ('user_catalog_favorites', 'user_catalog_favorite', 'user_catalog_favorite_operation', 'inventory_device', 'inventory_connection', 'user_device_templates', 'user_device_template', 'user_device_template_operation', 'customer_device_templates', 'customer_device_template', 'customer_device_template_operation', 'user_preferences', 'user_preference_operation', 'operation'):
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
            with self.assertRaises(contracts.Schema11Error):
                copier.load_prepared(candidate.directory)
        finally:
            private.write_bytes(original)
        copier.save(self.pointer, {'directory': str(ROOT)})
        try:
            with self.assertRaises(contracts.Schema11Error):
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
        with patch.object(coordinator, 'start_private_pg909', side_effect=uncertain_target):
            with self.assertRaises(contracts.Schema11Error) as uncertain:
                self.activate()
        self.assertEqual(uncertain.exception.code, 'rolled_back')
        self.assertFalse(coordinator.pg_running(candidate.directory))
        self.assertEqual(self.pointer.read_bytes(), self.pointer_bytes)

        def fail_after_pointer(name, result):
            if name == 'after_pointer':
                raise RuntimeError('Synthetic failure after atomic pointer replacement')
        with self.assertRaises(contracts.Schema11Error) as rolled:
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
                coordinator.start_private_pg909(candidate.directory)
        with self.assertRaises(contracts.Schema11Error) as foreign:
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
                candidate.lab.sql(candidate.database, f"BEGIN;INSERT INTO customer(id,systemhaus_id,name) VALUES('{identity}','{house}','Synthetic net-zero909');DELETE FROM customer WHERE id='{identity}';COMMIT;", sensitive=True)
                self.assertEqual(snapshot(candidate.sql), before)
                current = copier.activity_watermark(candidate.directory, candidate.cfg)
                self.assertGreater(int(current['xmax']), int(candidate.record['candidateActivityBaseline']['xmax']))
                observed.update(netZeroRowsEqual=True, activityAdvanced=True)
                raise RuntimeError('Synthetic failure after compensated committed write')
        with self.assertRaises(contracts.Schema11Error) as changed:
            self.activate(compensated_write)
        self.assertEqual(changed.exception.code, 'recovery_required')
        selected = self.pointer.read_bytes()
        self.assertEqual(json.loads(selected), {'directory': str(candidate.directory)})
        self.assertFalse(coordinator.pg_running(candidate.directory))
        with self.assertRaises(contracts.Schema11Error) as denied:
            coordinator.rollback(lab.directory, self.pointer, candidate.directory)
        self.assertEqual(denied.exception.code, 'recovery_required')
        self.assertEqual(self.pointer.read_bytes(), selected)

        # Verify recovery832 with actual source832/DB11 startup and account
        # authentication ONLY in this new copy, after rollback is already blocked.
        runtime = coordinator.OwnedRuntime(candidate.directory, candidate.cfg)
        runtime.start_pg()
        try:
            self.assertEqual(snapshot(lambda q: candidate.sql(q, recovery=True)), self.before)
            self.assertEqual(history(lambda q: candidate.sql(q, recovery=True), candidate.directory / 'versions/relations11-source832-recovery/server', 11), self.history11)
            server = candidate.lab.start_server(candidate.recovered,
                dll=candidate.directory / 'versions/relations11-source832-recovery/server/RackClick.Server.dll',
                frontend=candidate.directory / 'versions/relations11-source832-recovery/frontend')
            self.extra_servers.append(server)
            self.assertEqual(server.request('GET', '/health/ready').status, 200)
            self.assertEqual(Client(server).login('move-reader', self.password).status, 200)
            server.close()
        finally:
            runtime.stop()
        # The selected NEW copy also serves the exact old session/preferences/
        # report receipt, then produces the new849 artifact. This is synthetic
        # application activity after rollback was already proven blocked.
        runtime.start_pg()
        try:
            server = candidate.lab.start_server(candidate.database,
                dll=candidate.directory / 'server/RackClick.Server.dll', frontend=candidate.directory / 'frontend')
            self.extra_servers.append(server)
            copied_client = Client(server)
            copied_client.cookie, copied_client.csrf, actor_id = self.seed_session
            self.assertEqual(copied_client.request('GET','/api/v1/me').json()['user']['id'], actor_id)
            preference = copied_client.request('POST','/api/v1/me/preferences',{'key':'language','value':'es'},
                {'If-Match':'"preferences-0"','Idempotency-Key':self.preference_request,'X-RackClick-Actor':actor_id})
            self.assertEqual(preference.status,200)
            self.assertEqual(preference.json(),self.preference_result)
            old_status = copied_client.request('GET',f"/api/v1/customers/{self.ids['customer']}/reports/xlsx/operations/{self.old_report_request}")
            self.assertEqual(old_status.status,200)
            self.assertEqual(old_status.json()['operation'],self.old_report)
            prior_xls = copied_client.request('GET',f"/api/v1/customers/{self.ids['customer']}/reports/xls-html/operations/{self.existing_xls_request}")
            self.assertEqual(prior_xls.status,200)
            self.assertEqual(prior_xls.json()['operation'],self.existing_xls_result)
            request = str(uuid.uuid4())
            path = f"/api/v1/customers/{self.ids['customer']}/reports/xls-html"
            revision = copied_client.request('GET',f"/api/v1/customers/{self.ids['customer']}/project").json()['revision']
            headers = {'If-Match':f'"{revision}"','Idempotency-Key':request,'X-RackClick-Actor':actor_id}
            generated = copied_client.request('POST',path,{'rackId':self.ids['rackA']},headers)
            self.assertEqual(generated.status,200)
            result = generated.json();raw = base64.b64decode(result['report']['contentBase64'],validate=True)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),result['report']['sha256'])
            self.assertEqual(raw.count(b'<table '),3)
            self.assertEqual(copied_client.request('GET',path+'/operations/'+request).json()['operation'],result)
            self.assertEqual(copied_client.request('POST',path,{'rackId':self.ids['rackA']},headers).json(),result)
            observed.update(copiedSessionRetained=True,personalPreferenceReplayExact=True,previousXlsxReceiptExact=True,
                            newXls849BytesAndRecoveryExact=True,source832XlsReceiptExact=True)
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
        self.assertEqual(self.source.hashes,self.source_static_hashes)
        self.assertEqual({n: sha256(lab.directory / 'data' / n) for n in self.pg_configs}, self.pg_configs)
        self.assertEqual({n: sha256(candidate.directory / 'data' / n) for n in target_pg_configs}, target_pg_configs)
        self.observations.append(dict(oneSourceFixture=True, actualQaTechnicalAuthentication=False, syntheticFixtureAuthenticatedToPopulateLibrary=True,
            full35TableRowsAnd11HistoryExact=True, nonemptyHistoricalContextRetained=True,
            noMigrationInvoked=True, newPostgresqlIdentities=True, compatible832StartupAndAccount=True,
            quietActivationAndExplicitRollback=True, uncertainOwnedLaunchStopped=True,
            foreignLaunchRetained=True, compensatedWriteBlocksRollback=True, allBranchesRetained=True,
            normalStartRestoresAutovacuum=True, persistentPostgresqlConfigHashesUnchanged=True,
            sourceRootArtifactsWithoutArtifactDirectorySupported=True, uncertainPidMarkerRetained=True,
            lockedApplicationRejected=True, privateAndSharedLibraryRetained=True,
            favoritesAndInventoryRetained=True, preferencesAndReportReceiptsRetained=True,
            bothSourceDatabaseStatesPreserved=True,sourcePrimaryAndRecovery712Different=True,
            sourcePrepared847SealAndRecovery712FilesPreserved=True,fixture832PreparedBy847=True, **observed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--group', choices=('contracts', 'native', 'private-inputs', 'all'), default='all')
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    args.evidence.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__).resolve()] + [ROOT / 'tools/windows' / n for n in
        ('qa_relations11_source909.py', 'qa_relations11_candidate909.py', 'qa_relations11_switch909.py', 'qa_relations11_update909.py',
         'Qa-Local.py', 'qa_schema_switch.py', 'qa_schema11_source772.py', 'qa_schema6_source.py',
         'qa_schema_candidate.py', 'qa_schema5_candidate.py', 'qa_schema5_switch.py', 'qa_schema6_real_candidate.py', 'windows_job.py',
         'qa_xls11_source847.py','qa_xls11_candidate847.py','qa_xls11_switch847.py','qa_xls11_update847.py')]
    sources += [ROOT / 'development/server/tests/pg_support.py', ROOT / 'development/server/tests/test_inventory_movement_gui.py',
                ROOT / 'development/server/tests/test_qa_xls11_update847.py']
    def hashes():
        return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources}
    before = hashes()
    frozen = args.evidence / 'sources'
    for path in sources:
        destination = frozen / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    (args.evidence / 'SOURCE-FREEZE.json').write_text(json.dumps(before, indent=2) + '\n', encoding='utf-8')
    suites = []
    if args.group in ('contracts', 'all'):
        suites.append(unittest.defaultTestLoader.loadTestsFromTestCase(Closed909Contracts))
    if args.group == 'private-inputs':
        suites.append(unittest.defaultTestLoader.loadTestsFromName('test_initializer_secret_must_be_sealed_unchanged_and_inside_copy', Closed909Contracts))
    if args.group in ('native', 'all'):
        suites.append(unittest.defaultTestLoader.loadTestsFromTestCase(Native909Acceptance))
    with (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(suites))
    data = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), group=args.group,
        testsRun=result.testsRun, successful=result.wasSuccessful(), cases=result.records,
        sourceHashes=before, inputsUnchanged=before == hashes(), actualQaAccessed=False,
        labs=Native909Acceptance.outcomes, observations=Native909Acceptance.observations)
    (args.evidence / 'result.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return 0 if data['successful'] and data['inputsUnchanged'] and all(all(row.values()) for row in data['labs']) else 1


if __name__ == '__main__':
    sys.exit(main())
