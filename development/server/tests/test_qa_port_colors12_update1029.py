"""1029: closed contracts and ONE new Windows PostgreSQL11->12 fixture chain.

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
import re
import shutil
import socket
import sys
import traceback
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
import qa_port_colors12_source1029 as contracts
import qa_port_colors12_candidate1029 as copier
import qa_port_colors12_switch1029 as coordinator
import qa_port_colors12_update1029 as cli
from test_qa_relations11_update909 import Native909Acceptance
import qa_relations11_switch909 as old_coordinator


class Closed1029Contracts(unittest.TestCase):
    def test_pending_or_wrong_pin_fails_closed(self):
        with patch.object(contracts, 'TARGET1029', None):
            with self.assertRaises(contracts.Schema12Error) as denied:
                contracts.load_target()
            self.assertEqual(denied.exception.code, 'target1029_pin_invalid')
        for value in (('elsewhere.json', '0' * 64), ('', ''), ['not', 'a-tuple']):
            with patch.object(contracts, 'TARGET1029', value):
                with self.assertRaises(contracts.Schema12Error):
                    contracts.load_target()
        self.assertEqual(contracts.SOURCE_SHA256, '1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09')
        self.assertEqual([c.__name__ for c in contracts.Source849.__mro__], ['Source849', 'Source4', 'object'])
        source = contracts.load_source()
        self.assertEqual((source.revision, source.schema, len(source.expected['server']), len(source.expected['frontend'])), (849, 11, 20, 18))
        target = contracts.load_target()
        self.assertEqual((target.revision, target.schema, len(target.expected['server']), len(target.expected['frontend'])), (969, 12, 21, 18))
        sql = lambda d: {k:v for k,v in d.expected['server'].items() if k.startswith('database/')}
        self.assertEqual(sql(source),{k:v for k,v in sql(target).items() if not k.startswith('database/012-')})
        self.assertEqual(set(sql(target))-set(sql(source)),{'database/012-user-port-colors.sql'})
        for name in ('Npgsql.dll','RackClick.Server.deps.json','RackClick.Server.runtimeconfig.json'):
            self.assertEqual(source.expected['server'][name],target.expected['server'][name])
        self.assertIs(contracts.PortColors12Error,contracts.Schema12Error)
        self.assertNotEqual(source.expected['frontend']['app.js'],target.expected['frontend']['app.js'])
        self.assertEqual({k:v for k,v in source.expected['frontend'].items() if k != 'app.js'},
                         {k:v for k,v in target.expected['frontend'].items() if k != 'app.js'})

    def test_initializer_secret_must_be_sealed_unchanged_and_inside_copy(self):
        directory = ROOT / '.local' / ('static-secret1029-' + uuid.uuid4().hex)
        directory.mkdir(exist_ok=False)
        password = directory / 'init-password.txt'
        admin = directory / 'admin.pgpass'
        password.write_bytes(b'Synthetic non-operational initializer\n')
        admin.write_bytes(b'Synthetic non-operational passfile\n')
        expected = {p.name: sha256(p) for p in (password, admin)}
        copier.require_private_input_hashes(directory, expected)
        with self.assertRaises(contracts.Schema12Error):
            copier.require_private_input_hashes(directory, {'admin.pgpass':expected['admin.pgpass']})
        original = password.read_bytes()
        password.write_bytes(original + b'corrupt')
        with self.assertRaises(contracts.Schema12Error):
            copier.require_private_input_hashes(directory, expected)
        password.write_bytes(original)
        copier.require_private_input_hashes(directory, expected)
        with self.assertRaises(contracts.Schema12Error):
            copier.require_private_input_hashes(directory, {**expected, '../../AGENTS.md':sha256(ROOT / 'AGENTS.md')})
        self.assertTrue(directory.is_relative_to(ROOT / '.local'))
        self.assertFalse((directory / 'data').exists())

    def test_foreign_prelaunch_does_not_grant_ownership(self):
        runtime = coordinator.OwnedRuntime(ROOT, {'webPort': 12345})
        with patch.object(coordinator, 'app_stopped'), patch.object(coordinator, 'pg_running', return_value=True), \
                patch.object(coordinator, 'qa_module') as qa:
            with self.assertRaises(contracts.Schema12Error):
                runtime.start_pg()
            runtime.stop()
            self.assertFalse(runtime.owned)
            qa.assert_not_called()

    def test_cli_reports_schema_and_revision_or_unknown_failure(self):
        arguments = ['qa_port_colors12_update1029.py', 'rollback', '--source', str(ROOT),
                     '--pointer', str(ROOT / 'synthetic.json'), '--candidate', str(ROOT)]
        output = io.StringIO()
        with patch.object(sys, 'argv', arguments), patch.object(cli, 'rollback', return_value=SimpleNamespace(state='rolled_back')), \
                patch.object(sys, 'stdout', output):
            self.assertEqual(cli.main(), 0)
        data = json.loads(output.getvalue())
        self.assertEqual((data['sourceSchema'], data['candidateSchema'], data['selectedSchema']), (11, 12, 11))
        self.assertEqual((data['sourceRevision'], data['candidateRevision'], data['selectedRevision']), (849, 969, 849))
        for action, selected, state in (('activate',False,'committed'),('validate',False,None),('validate',True,None)):
            argv = ['qa_port_colors12_update1029.py',action,'--source',str(ROOT),'--pointer',str(ROOT/'synthetic.json'),
                    '--candidate',str(ROOT)] + (['--selected'] if selected else [])
            output = io.StringIO()
            with patch.object(sys,'argv',argv), patch.object(cli,action if action != 'validate' else 'validate_operation',
                    return_value=SimpleNamespace(state=state)), patch.object(sys,'stdout',output):
                self.assertEqual(cli.main(),0)
            value = json.loads(output.getvalue())
            self.assertEqual((value['selectedSchema'],value['selectedRevision']),
                             (12,969) if action == 'activate' or selected else (11,849))
            if action == 'validate':
                self.assertFalse(value['databaseTestExecuted'])
        errors = io.StringIO()
        with patch.object(sys, 'argv', arguments), patch.object(cli, 'rollback', side_effect=contracts.Schema12Error('recovery_required')), \
                patch.object(sys, 'stderr', errors):
            self.assertEqual(cli.main(), 1)
        self.assertIsNone(json.loads(errors.getvalue())['selectedSchema'])
        self.assertIsNone(json.loads(errors.getvalue())['selectedRevision'])
        self.assertIsNone(json.loads(errors.getvalue())['leftRunning'])


class Native1029Acceptance(unittest.TestCase):
    outcomes = []
    observations = []

    def setUp(self):
        # Reuse only the historical *fixture setup*, never its old test/result.
        # It creates a new832 source; a new909 copy yields the required849 main
        # plus separate832/11 recovery with genuine prepared909 inputs/seals.
        Native909Acceptance.setUp(self)
        self.seed_lab = self.source_lab
        self.fixture849 = old_coordinator.prepare_operation(self.seed_lab.directory, self.pointer).candidate
        self.source_lab = lab = self.fixture849.lab
        self.addCleanup(lab.close)
        self.db, self.cfg = self.fixture849.database, self.fixture849.cfg
        (lab.directory / 'server.lock').write_bytes(b'0')
        home = lab.directory / 'port-colors12-home'; home.mkdir()
        self.pointer = home / 'current.json'
        copier.save(self.pointer, {'directory':str(lab.directory)})
        self.pointer_bytes = self.pointer.read_bytes()
        runtime = old_coordinator.OwnedRuntime(lab.directory,self.cfg)
        self.addCleanup(runtime.stop)
        runtime.start_pg()
        try:
            # Source primary and old recovery intentionally diverge. New969 and
            # new recovery849 must both copy ONLY the current primary849 rows.
            lab.sql(self.db,f"UPDATE customer SET name='Current849 primary Ω' WHERE id='{self.ids['customer']}'",sensitive=True)
            lab.sql(self.fixture849.recovered,"UPDATE systemhaus SET name='Independent recovery832 Ω'",sensitive=True)
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
        self.source = contracts.Source849(lab.directory,self.pointer)
        runtime.start_pg()
        try:
            self.source_states = self.source.database_states()
            self.before = self.source_states['primary']['snapshot']
            self.history11 = self.source_states['primary']['history']
            self.assertEqual(len(self.before),35)
            self.assertEqual(len(self.source_states['recovery832']['snapshot']),35)
            self.assertNotEqual(self.before,self.source_states['recovery832']['snapshot'])
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
        with self.assertRaises(contracts.Schema12Error):
            contracts.Source849(lab.directory, self.pointer, real=True)
        self.assertNotIn('artifactDirectory', self.cfg)
        for relative in ('relations11-prepared.sha256','versions/relations11-source832-recovery/frontend/app.js'):
            path = lab.directory / relative
            original = path.read_bytes()
            path.write_bytes(original + b'\nsynthetic corruption1029\n')
            try:
                with self.assertRaises(contracts.Schema12Error):
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
            with self.assertRaises(contracts.Schema12Error):
                coordinator.prepare_operation(lab.directory, self.pointer)
            self.assertEqual(json.loads(marker.read_bytes()), {'pid': 2147483647})
            self.assertFalse((lab.directory / 'stop.request').exists())
        finally:
            marker.unlink()
        with (lab.directory / 'server.lock').open('r+b') as locked:
            msvcrt.locking(locked.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                with self.assertRaises(contracts.Schema12Error):
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
            with self.assertRaises(contracts.Schema12Error):
                coordinator.prepare_operation(lab.directory, self.pointer)
        coordinator.qa_module().control(lab.directory, 'start')
        with self.assertRaises(contracts.Schema12Error) as active:
            coordinator.prepare_operation(lab.directory, self.pointer)
        self.assertEqual(active.exception.code, 'source849_pg_already_active')
        self.assertTrue(coordinator.pg_running(lab.directory))
        coordinator.qa_module().control(lab.directory, 'stop')

        control = coordinator.start_private_pg1029
        raised = []
        def uncertain_source(directory):
            result = control(directory)
            if directory == lab.directory and not raised:
                raised.append(True)
                raise RuntimeError('Synthetic failure after own PG really started')
            return result
        with patch.object(coordinator, 'start_private_pg1029', side_effect=uncertain_source):
            with self.assertRaises(contracts.Schema12Error) as uncertain:
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
        self.assertNotEqual(candidate.record['sourceSnapshot'],self.source_states['recovery832']['snapshot'])
        self.assertTrue(copier.additive_copy(self.before,self.history11,candidate.record['candidateSnapshot'],candidate.record['candidateHistory']))
        self.assertEqual(candidate.record['candidateHistory'][:11], self.history11)
        self.assertEqual(len(candidate.record['candidateHistory']),12)
        self.assertEqual((candidate.record['sourceSchema'],candidate.record['candidateSchema']), (11,12))
        self.assertEqual((candidate.record['sourceRevision'],candidate.record['candidateRevision']), (849,969))
        self.assertTrue((candidate.directory / 'migration-private.log').is_file())
        self.assertEqual(candidate.record['candidateSnapshot']['audit_context'], self.before['audit_context'])
        self.assertEqual(candidate.record['candidateSnapshot']['app_user'], self.before['app_user'])
        self.assertEqual(candidate.record['candidateSnapshot']['app_session'], self.before['app_session'])
        self.assertEqual(len(candidate.record['candidateSnapshot']), 37)
        self.assertTrue(all(candidate.record['candidateSnapshot'][name]['rows'] == 0 for name in contracts.NEW_TABLES))
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
        # Even a newly resealed record cannot excuse a modified old migration
        # stamp. Restore the exact fixture bytes; no DB/baseline is rewritten.
        prepared_path, seal_path = candidate.directory / copier.PREPARED, candidate.directory / copier.SEAL
        prepared_bytes, seal_bytes = prepared_path.read_bytes(), seal_path.read_bytes()
        tampered = json.loads(prepared_bytes)
        tampered['candidateHistory'][0]['applied_at'] = '1999-01-01T00:00:00+00:00'
        try:
            copier.save(prepared_path,tampered)
            seal_path.write_text(sha256(prepared_path)+'\n',encoding='ascii')
            with self.assertRaises(contracts.Schema12Error):
                copier.load_prepared(candidate.directory)
        finally:
            prepared_path.write_bytes(prepared_bytes); seal_path.write_bytes(seal_bytes)
        private = candidate.directory / PRIVATE_FILES[0]
        original = private.read_bytes()
        private.write_bytes(original + b'Synthetic corrupt copy')
        try:
            with self.assertRaises(contracts.Schema12Error):
                copier.load_prepared(candidate.directory)
        finally:
            private.write_bytes(original)
        copier.save(self.pointer, {'directory': str(ROOT)})
        try:
            with self.assertRaises(contracts.Schema12Error):
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
        with patch.object(coordinator, 'start_private_pg1029', side_effect=uncertain_target):
            with self.assertRaises(contracts.Schema12Error) as uncertain:
                self.activate()
        self.assertEqual(uncertain.exception.code, 'rolled_back')
        self.assertFalse(coordinator.pg_running(candidate.directory))
        self.assertEqual(self.pointer.read_bytes(), self.pointer_bytes)

        for checkpoint in ('before_pointer','after_pointer'):
            def fail_pointer(name, result):
                if name == checkpoint:
                    raise RuntimeError('Synthetic pointer checkpoint failure')
            with self.assertRaises(contracts.Schema12Error) as rolled:
                self.activate(fail_pointer)
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
                coordinator.start_private_pg1029(candidate.directory)
        with self.assertRaises(contracts.Schema12Error) as foreign:
            self.activate(foreign_start)
        self.assertEqual(foreign.exception.code, 'recovery_required')
        self.assertTrue(coordinator.pg_running(candidate.directory))
        self.assertEqual(self.pointer.read_bytes(), self.pointer_bytes)
        coordinator.qa_module().control(candidate.directory, 'stop')  # Explicit fixture actor cleanup.

        observed = {}
        def compensated_write(name, result):
            if name == 'after_start':
                # Only source.recovery832 changes XID; primary/source snapshots
                # and the new candidate stay identical. Return must still fail.
                # Explicit synthetic fixture actor: the selected destination
                # legitimately occupies the shared web port. Product quiet()
                # remains strict; this test starts only the new source PG.
                self.assertFalse(coordinator.pg_running(lab.directory))
                try:
                    coordinator.start_private_pg1029(lab.directory)
                    before = self.source.database_states()
                    secondary = self.source.prepared909.recovered
                    identity = str(uuid.uuid4())
                    house = self.source.sql('SELECT id FROM systemhaus')
                    lab.sql(secondary, f"BEGIN;INSERT INTO customer(id,systemhaus_id,name) VALUES('{identity}','{house}','Synthetic recovery832 net-zero1029');DELETE FROM customer WHERE id='{identity}';COMMIT;", sensitive=True)
                    self.assertEqual(self.source.database_states(), before)
                    current = copier.activity_watermark(lab.directory,self.cfg)
                    self.assertGreater(int(current['xmax']), int(candidate.record['sourceActivityBaseline']['xmax']))
                    candidate.verify_rows_and_activity()
                    observed.update(netZeroRowsEqual=True, activityAdvanced=True,sourceRecovery832OnlyBlocksReturn=True,
                                    candidateUnchangedWhenSourceRecoveryActivityBlocksReturn=True)
                finally:
                    if coordinator.pg_running(lab.directory):
                        coordinator.qa_module().control(lab.directory,'stop')
                    self.assertFalse(coordinator.pg_running(lab.directory))
                raise RuntimeError('Synthetic failure after source recovery832 compensated commit')
        with self.assertRaises(contracts.Schema12Error) as changed:
            self.activate(compensated_write)
        self.assertEqual(changed.exception.code, 'recovery_required')
        selected = self.pointer.read_bytes()
        self.assertEqual(json.loads(selected), {'directory': str(candidate.directory)})
        self.assertFalse(coordinator.pg_running(candidate.directory))
        with self.assertRaises(contracts.Schema12Error) as denied:
            coordinator.rollback(lab.directory, self.pointer, candidate.directory)
        self.assertEqual(denied.exception.code, 'recovery_required')
        self.assertEqual(self.pointer.read_bytes(), selected)

        # Verify recovery849 with actual source849/DB11 startup and account
        # authentication ONLY in this new copy, after rollback is already blocked.
        runtime = coordinator.OwnedRuntime(candidate.directory, candidate.cfg)
        runtime.start_pg()
        try:
            self.assertEqual(snapshot(lambda q: candidate.sql(q, recovery=True)), self.before)
            self.assertEqual(history(lambda q: candidate.sql(q, recovery=True), candidate.directory / 'versions/port-colors12-source849-recovery/server', 11), self.history11)
            server = candidate.lab.start_server(candidate.recovered,
                dll=candidate.directory / 'versions/port-colors12-source849-recovery/server/RackClick.Server.dll',
                frontend=candidate.directory / 'versions/port-colors12-source849-recovery/frontend')
            self.extra_servers.append(server)
            self.assertEqual(server.request('GET', '/health/ready').status, 200)
            self.assertEqual(Client(server).login('move-reader', self.password).status, 200)
            server.close()
        finally:
            runtime.stop()
        # The selected NEW copy also serves the exact old session/preferences/
        # report receipt, then produces the new969 artifact. This is synthetic
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
                            newXls969BytesAndRecoveryExact=True,source849XlsReceiptExact=True)
            server.close()
        finally:
            runtime.stop()
        source_runtime = coordinator.OwnedRuntime(lab.directory, self.cfg)
        source_runtime.start_pg()
        try:
            self.assertEqual(self.source.database_states(), candidate.record['sourceDatabaseStates'])
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
            full35SourceAnd37TargetRowsAndHistoryExact=True, nonemptyHistoricalContextRetained=True,
            only012NewPrimaryMigration=True, newPostgresqlIdentities=True, compatible849StartupAndAccount=True,
            quietActivationAndExplicitRollback=True, uncertainOwnedLaunchStopped=True,
            foreignLaunchRetained=True, compensatedWriteBlocksRollback=True, allBranchesRetained=True,
            normalStartRestoresAutovacuum=True, persistentPostgresqlConfigHashesUnchanged=True,
            sourceRootArtifactsWithoutArtifactDirectorySupported=True, uncertainPidMarkerRetained=True,
            lockedApplicationRejected=True, privateAndSharedLibraryRetained=True,
            favoritesAndInventoryRetained=True, preferencesAndReportReceiptsRetained=True,
            bothSourceDatabaseStatesPreserved=True,sourcePrimaryAndRecovery832Different=True,
            sourcePrepared909SealAndRecovery832FilesPreserved=True,fixture849PreparedBy909=True, **observed))



class Focused1029Acceptance(Native1029Acceptance):
    """Fresh fixture; postcommit return and the still-unexecuted activity/tail.

    Does not repeat the full compound's preflight/tamper/uncertain-start cases.
    Previous failures remain failures; no activity boundary is ever renewed.
    """
    def test_focused_postcommit_and_pending_tail(self):
        original = coordinator._guarded_restore
        def diagnostic_guard(*args, **kwargs):
            try:
                return original(*args, **kwargs)
            except Exception as error:
                # This fixture-only interception observes the original exception
                # before the product's closed recovery_required mapping. No SQL
                # retry, no messages/locals/secrets and no journal modification.
                code = getattr(error, 'code', None)
                if code is None and re.fullmatch(r'[a-z0-9_]{1,100}', str(error)):
                    code = str(error)
                if not isinstance(code, str) or not re.fullmatch(r'[a-z0-9_]{1,100}', code):
                    code = None
                frames = traceback.extract_tb(error.__traceback__)
                frame = frames[-1] if frames else None
                value = dict(exceptionClass=type(error).__module__ + '.' + type(error).__qualname__, code=code,
                    lastSymbol=None if frame is None else dict(file=Path(frame.filename).name, function=frame.name, line=frame.lineno))
                try:
                    copier.save(args[1].directory / ('port-colors12-diagnostic-private-' + uuid.uuid4().hex + '.json'), value)
                except Exception:
                    pass  # Diagnostics must not alter the original failure/guard.
                raise
        with patch.object(coordinator, '_guarded_restore', side_effect=diagnostic_guard):
            self._run_focused_postcommit_and_pending_tail()

    def _run_focused_postcommit_and_pending_tail(self):
        lab = self.source_lab
        prepared = coordinator.prepare_operation(lab.directory,self.pointer)
        self.candidate = candidate = prepared.candidate
        self.assertEqual(prepared.state,'prepared')
        self.assertTrue(copier.additive_copy(self.before,self.history11,candidate.record['candidateSnapshot'],candidate.record['candidateHistory']))
        self.assertEqual(candidate.record['sourceDatabaseStates'],self.source_states)
        self.assertEqual((len(candidate.record['candidateSnapshot']),len(candidate.record['sourceSnapshot'])),(37,35))
        target_pg_configs = {name:sha256(candidate.directory/'data'/name) for name in self.pg_configs}
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
                coordinator.start_private_pg1029(candidate.directory)
        with self.assertRaises(contracts.Schema12Error) as foreign:
            self.activate(foreign_start)
        self.assertEqual(foreign.exception.code, 'recovery_required')
        self.assertTrue(coordinator.pg_running(candidate.directory))
        self.assertEqual(self.pointer.read_bytes(), self.pointer_bytes)
        coordinator.qa_module().control(candidate.directory, 'stop')  # Explicit fixture actor cleanup.

        observed = {}
        def compensated_write(name, result):
            if name == 'after_start':
                # Only source.recovery832 changes XID; primary/source snapshots
                # and the new candidate stay identical. Return must still fail.
                # Explicit synthetic fixture actor: the selected destination
                # legitimately occupies the shared web port. Product quiet()
                # remains strict; this test starts only the new source PG.
                self.assertFalse(coordinator.pg_running(lab.directory))
                try:
                    coordinator.start_private_pg1029(lab.directory)
                    before = self.source.database_states()
                    secondary = self.source.prepared909.recovered
                    identity = str(uuid.uuid4())
                    house = self.source.sql('SELECT id FROM systemhaus')
                    lab.sql(secondary, f"BEGIN;INSERT INTO customer(id,systemhaus_id,name) VALUES('{identity}','{house}','Synthetic recovery832 net-zero1029');DELETE FROM customer WHERE id='{identity}';COMMIT;", sensitive=True)
                    self.assertEqual(self.source.database_states(), before)
                    current = copier.activity_watermark(lab.directory,self.cfg)
                    self.assertGreater(int(current['xmax']), int(candidate.record['sourceActivityBaseline']['xmax']))
                    candidate.verify_rows_and_activity()
                    observed.update(netZeroRowsEqual=True, activityAdvanced=True,sourceRecovery832OnlyBlocksReturn=True,
                                    candidateUnchangedWhenSourceRecoveryActivityBlocksReturn=True)
                finally:
                    if coordinator.pg_running(lab.directory):
                        coordinator.qa_module().control(lab.directory,'stop')
                    self.assertFalse(coordinator.pg_running(lab.directory))
                raise RuntimeError('Synthetic failure after source recovery832 compensated commit')
        with self.assertRaises(contracts.Schema12Error) as changed:
            self.activate(compensated_write)
        self.assertEqual(changed.exception.code, 'recovery_required')
        selected = self.pointer.read_bytes()
        self.assertEqual(json.loads(selected), {'directory': str(candidate.directory)})
        self.assertFalse(coordinator.pg_running(candidate.directory))
        with self.assertRaises(contracts.Schema12Error) as denied:
            coordinator.rollback(lab.directory, self.pointer, candidate.directory)
        self.assertEqual(denied.exception.code, 'recovery_required')
        self.assertEqual(self.pointer.read_bytes(), selected)

        # Verify recovery849 with actual source849/DB11 startup and account
        # authentication ONLY in this new copy, after rollback is already blocked.
        runtime = coordinator.OwnedRuntime(candidate.directory, candidate.cfg)
        runtime.start_pg()
        try:
            self.assertEqual(snapshot(lambda q: candidate.sql(q, recovery=True)), self.before)
            self.assertEqual(history(lambda q: candidate.sql(q, recovery=True), candidate.directory / 'versions/port-colors12-source849-recovery/server', 11), self.history11)
            server = candidate.lab.start_server(candidate.recovered,
                dll=candidate.directory / 'versions/port-colors12-source849-recovery/server/RackClick.Server.dll',
                frontend=candidate.directory / 'versions/port-colors12-source849-recovery/frontend')
            self.extra_servers.append(server)
            self.assertEqual(server.request('GET', '/health/ready').status, 200)
            self.assertEqual(Client(server).login('move-reader', self.password).status, 200)
            server.close()
        finally:
            runtime.stop()
        # The selected NEW copy also serves the exact old session/preferences/
        # report receipt, then produces the new969 artifact. This is synthetic
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
                            newXls969BytesAndRecoveryExact=True,source849XlsReceiptExact=True)
            server.close()
        finally:
            runtime.stop()
        source_runtime = coordinator.OwnedRuntime(lab.directory, self.cfg)
        source_runtime.start_pg()
        try:
            self.assertEqual(self.source.database_states(), candidate.record['sourceDatabaseStates'])
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
        self.observations.append(dict(focusedFreshFixture=True,fullCompoundRepeated=False,
            prepareAndQuietActivationAndExplicitRollback=True,foreignLaunchRetained=True,
            compensatedSourceRecovery832BlocksRollback=True,sourcePrimaryAndRecovery832Different=True,
            newPrimary37AndRecovery35Tables=True,only012NewPrimaryMigration=True,
            runtimePermissionsVerifiedByPrepare=True,allBranchesRetained=True,
            normalStartRestoresAutovacuum=True,persistentPostgresqlConfigHashesUnchanged=True,
            copiedPrivateFilesAndSourcePrepared909Unchanged=True,
            compatible849RecoveryStartupAndAccount=True, **observed))



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--group', choices=('contracts', 'native', 'focused', 'all'), default='all')
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    args.evidence.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__).resolve()] + [ROOT / 'tools/windows' / n for n in
        ('qa_port_colors12_source1029.py','qa_port_colors12_candidate1029.py','qa_port_colors12_switch1029.py','qa_port_colors12_update1029.py',
         'qa_relations11_source909.py','qa_relations11_candidate909.py','qa_relations11_switch909.py','qa_relations11_update909.py',
         'qa_xls11_source847.py','qa_xls11_candidate847.py','qa_xls11_switch847.py','qa_xls11_update847.py',
         'qa_schema11_source772.py','qa_schema11_candidate772.py','qa_schema11_switch772.py','qa_schema11_update772.py',
         'Qa-Local.py','qa_schema_switch.py','qa_schema6_source.py','qa_schema_candidate.py','qa_schema5_candidate.py',
         'qa_schema5_switch.py','qa_schema6_real_candidate.py','windows_job.py')]
    sources += [ROOT / 'development/server/tests' / n for n in
        ('pg_support.py','test_inventory_movement_gui.py','test_qa_relations11_update909.py','test_qa_xls11_update847.py',
         'test_qa_schema11_update772.py')]
    sources += [contracts.SOURCE_MANIFEST, contracts.TARGET_MANIFEST]
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
    if args.group in ('contracts', 'focused', 'all'):
        suites.append(unittest.defaultTestLoader.loadTestsFromTestCase(Closed1029Contracts))
    if args.group in ('native', 'all'):
        suites.append(unittest.defaultTestLoader.loadTestsFromTestCase(Native1029Acceptance))
    if args.group == 'focused':
        suites.append(unittest.defaultTestLoader.loadTestsFromName('test_focused_postcommit_and_pending_tail', Focused1029Acceptance))
    with (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(suites))
    data = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), group=args.group,
        testsRun=result.testsRun, successful=result.wasSuccessful(), cases=result.records,
        sourceHashes=before, inputsUnchanged=before == hashes(), actualQaAccessed=False,
        labs=Native1029Acceptance.outcomes, observations=Native1029Acceptance.observations)
    (args.evidence / 'result.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return 0 if data['successful'] and data['inputsUnchanged'] and all(all(row.values()) for row in data['labs']) else 1


if __name__ == '__main__':
    sys.exit(main())
