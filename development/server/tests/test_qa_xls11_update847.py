"""847: closed contracts and ONE new shared Windows PostgreSQL11 fixture.

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
import qa_xls11_source847 as contracts
import qa_xls11_candidate847 as copier
import qa_xls11_switch847 as coordinator
import qa_xls11_update847 as cli


class Closed847Contracts(unittest.TestCase):
    def test_pending_or_wrong_pin_fails_closed(self):
        with patch.object(contracts, 'TARGET847', None):
            with self.assertRaises(contracts.Schema11Error) as denied:
                contracts.load_target()
            self.assertEqual(denied.exception.code, 'target847_pin_invalid')
        for value in (('elsewhere.json', '0' * 64), ('', ''), ['not', 'a-tuple']):
            with patch.object(contracts, 'TARGET847', value):
                with self.assertRaises(contracts.Schema11Error):
                    contracts.load_target()
        self.assertEqual(contracts.SOURCE_SHA256, 'f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd')
        self.assertEqual([c.__name__ for c in contracts.Source712.__mro__], ['Source712', 'Source4', 'object'])
        source = contracts.load_source()
        self.assertEqual((source.revision, source.schema, len(source.expected['server']), len(source.expected['frontend'])), (712, 11, 20, 18))
        target = contracts.load_target()
        self.assertEqual((target.revision, target.schema, len(target.expected['server']), len(target.expected['frontend'])), (832, 11, 20, 18))
        sql = lambda d: {k:v for k,v in d.expected['server'].items() if k.startswith('database/')}
        self.assertEqual(sql(source), sql(target))
        self.assertNotEqual(source.expected['server']['RackClick.Server.dll'], target.expected['server']['RackClick.Server.dll'])

    def test_initializer_secret_must_be_sealed_unchanged_and_inside_copy(self):
        directory = ROOT / '.local' / ('static-secret847-' + uuid.uuid4().hex)
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
        arguments = ['qa_xls11_update847.py', 'rollback', '--source', str(ROOT),
                     '--pointer', str(ROOT / 'synthetic.json'), '--candidate', str(ROOT)]
        output = io.StringIO()
        with patch.object(sys, 'argv', arguments), patch.object(cli, 'rollback', return_value=SimpleNamespace(state='rolled_back')), \
                patch.object(sys, 'stdout', output):
            self.assertEqual(cli.main(), 0)
        data = json.loads(output.getvalue())
        self.assertEqual((data['sourceSchema'], data['candidateSchema'], data['selectedSchema']), (11, 11, 11))
        self.assertEqual((data['sourceRevision'], data['candidateRevision'], data['selectedRevision']), (712, 832, 712))
        errors = io.StringIO()
        with patch.object(sys, 'argv', arguments), patch.object(cli, 'rollback', side_effect=contracts.Schema11Error('recovery_required')), \
                patch.object(sys, 'stderr', errors):
            self.assertEqual(cli.main(), 1)
        self.assertIsNone(json.loads(errors.getvalue())['selectedSchema'])
        self.assertIsNone(json.loads(errors.getvalue())['selectedRevision'])
        self.assertIsNone(json.loads(errors.getvalue())['leftRunning'])


class Native847Acceptance(unittest.TestCase):
    outcomes = []
    observations = []

    def setUp(self):
        self.source_lab = None
        self.candidate = None
        self.extra_servers = []
        baseline = contracts.load_source()
        contracts.load_target()  # No native allocation while target pin is pending.
        self.source_lab = lab = Lab('manual-qa-rc9-schema11').start()
        self.addCleanup(lab.close)
        self.db = lab.create_database('manual-qa-rc9')
        self.ids, self.password = fixture(lab, self.db, baseline.server / 'RackClick.Server.dll')
        lab.grant_runtime(self.db)
        art = lab.directory
        for name in ('server', 'frontend'):
            shutil.copytree(getattr(baseline, name), art / name)
        self.cfg = dict(directory=str(lab.directory), profile='rc9', host='127.0.0.1', webPort=free_port(),
            pgPort=lab.port, database=self.db.name, connection=self.db.connection(lab.port),
            dllSha256=baseline.expected['server']['RackClick.Server.dll'], bundleSha256=baseline.expected['frontend']['app.js'],
            qaCustomerId=self.ids['customer'], qaCustomerName='Synthetic schema11 source Ω',
            restoreSourceSha256='0' * 64, restoreCounts={'customers': 2, 'racks': 2, 'devices': 3, 'ports': 6, 'connections': 1})
        copier.save(lab.directory / 'manual-qa.json', self.cfg)
        for name in PRIVATE_FILES:
            (lab.directory / name).write_text('Synthetic847 private fixture Ω; no real QA data\n', encoding='utf-8')
        (lab.directory / 'server.lock').write_bytes(b'0')
        home = lab.directory / 'xls11-home'; home.mkdir()
        self.pointer = home / 'current.json'
        copier.save(self.pointer, {'directory': str(lab.directory)})
        self.pointer_bytes = self.pointer.read_bytes()
        # Historical context deliberately NONEMPTY: no schema4 emptiness assumption.
        house, actor = lab.sql(self.db, "SELECT id FROM systemhaus;SELECT id FROM app_user WHERE username='move-admin'").splitlines()
        event, request, operation = (str(uuid.uuid4()) for _ in range(3))
        lab.sql(self.db, f"""BEGIN;
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,after_json)
              VALUES('{event}','{house}','{actor}','{request}','synthetic847.history','{house}','{{}}');
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
        # Seed existing private bytes/receipt through the closed source712 API,
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
        # Both library lines must contain real bytes and operation receipts.
        template_id = captured.json()['result']['templateId']
        detail = seed_client.request('GET', f"/api/v1/customers/{self.ids['customer']}/catalog/private-templates/{template_id}").json()['template']
        published = seed_client.request('POST', f"/api/v1/customers/{self.ids['customer']}/catalog/shared-templates",
            {'type':'publish','privateTemplateId':template_id,'definitionVersion':1,
             'definitionSha256':detail['definitionSha256'],'name':'Compartida histórica Ω'},
            {'If-Match':'"shared-templates-0"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor_id})
        self.assertEqual(published.status, 200)
        self.preference_request = str(uuid.uuid4())
        self.preference_result = seed_client.request('POST', '/api/v1/me/preferences',
            {'key':'language','value':'es'},
            {'If-Match':'"preferences-0"','Idempotency-Key':self.preference_request,'X-RackClick-Actor':actor_id})
        self.assertEqual(self.preference_result.status, 200)
        self.preference_result = self.preference_result.json()
        self.old_report_request = str(uuid.uuid4())
        self.old_report = seed_client.request('POST', f"/api/v1/customers/{self.ids['customer']}/reports/xlsx",
            {'reportKind':'ports','query':'','status':'all','family':'all','rackId':self.ids['rackA']},
            {'If-Match':f'"{source_revision}"','Idempotency-Key':self.old_report_request,'X-RackClick-Actor':actor_id})
        self.assertEqual(self.old_report.status, 200)
        self.old_report = self.old_report.json()
        self.seed_session = (seed_client.cookie, seed_client.csrf, actor_id)
        seed_server.close()
        self.source = contracts.Source712(lab.directory, self.pointer)
        self.before = snapshot(self.source.sql)
        self.history11 = self.source.check_schema11()
        self.assertGreaterEqual(self.before['audit_context']['rows'], 1)
        self.assertGreaterEqual(self.before['audit_context_object']['rows'], 1)
        self.assertEqual(len(self.before), 35)
        self.assertEqual(self.before['app_user']['rows'], 4)
        self.assertEqual(lab.sql(self.db, "SELECT count(*) FROM permission_grant WHERE capability='templates.publish'"), '1')
        self.pg_configs = {name: sha256(lab.directory / 'data' / name) for name in ('postgresql.conf', 'pg_hba.conf', 'pg_ident.conf')}
        for name in ('app_user', 'app_session', 'user_catalog_favorites', 'user_catalog_favorite', 'user_catalog_favorite_operation', 'inventory_device', 'inventory_connection', 'user_device_templates', 'user_device_template', 'user_device_template_operation', 'customer_device_templates', 'customer_device_template', 'customer_device_template_operation', 'user_preferences', 'user_preference_operation', 'operation'):
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
        with self.assertRaises(contracts.Schema11Error):
            contracts.Source712(lab.directory, self.pointer, real=True)
        self.assertNotIn('artifactDirectory', self.cfg)
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
        self.assertEqual(active.exception.code, 'source712_pg_already_active')
        self.assertTrue(coordinator.pg_running(lab.directory))
        coordinator.qa_module().control(lab.directory, 'stop')

        control = coordinator.start_private_pg847
        raised = []
        def uncertain_source(directory):
            result = control(directory)
            if directory == lab.directory and not raised:
                raised.append(True)
                raise RuntimeError('Synthetic failure after own PG really started')
            return result
        with patch.object(coordinator, 'start_private_pg847', side_effect=uncertain_source):
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
        self.assertEqual(candidate.record['candidateSnapshot'], self.before)
        self.assertEqual(candidate.record['candidateHistory'], self.history11)
        self.assertEqual((candidate.record['sourceSchema'],candidate.record['candidateSchema']), (11,11))
        self.assertEqual((candidate.record['sourceRevision'],candidate.record['candidateRevision']), (712,832))
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
        with patch.object(coordinator, 'start_private_pg847', side_effect=uncertain_target):
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
                coordinator.start_private_pg847(candidate.directory)
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
                candidate.lab.sql(candidate.database, f"BEGIN;INSERT INTO customer(id,systemhaus_id,name) VALUES('{identity}','{house}','Synthetic net-zero847');DELETE FROM customer WHERE id='{identity}';COMMIT;", sensitive=True)
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

        # Verify recovery712 with actual source712/DB11 startup and account
        # authentication ONLY in this new copy, after rollback is already blocked.
        runtime = coordinator.OwnedRuntime(candidate.directory, candidate.cfg)
        runtime.start_pg()
        try:
            self.assertEqual(snapshot(lambda q: candidate.sql(q, recovery=True)), self.before)
            self.assertEqual(history(lambda q: candidate.sql(q, recovery=True), candidate.directory / 'versions/xls11-source712-recovery/server', 11), self.history11)
            server = candidate.lab.start_server(candidate.recovered,
                dll=candidate.directory / 'versions/xls11-source712-recovery/server/RackClick.Server.dll',
                frontend=candidate.directory / 'versions/xls11-source712-recovery/frontend')
            self.extra_servers.append(server)
            self.assertEqual(server.request('GET', '/health/ready').status, 200)
            self.assertEqual(Client(server).login('move-reader', self.password).status, 200)
            server.close()
        finally:
            runtime.stop()
        # The selected NEW copy also serves the exact old session/preferences/
        # report receipt, then produces the new832 artifact. This is synthetic
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
                            newXls832BytesAndRecoveryExact=True)
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
        self.observations.append(dict(oneSourceFixture=True, actualQaTechnicalAuthentication=False, syntheticFixtureAuthenticatedToPopulateLibrary=True,
            full35TableRowsAnd11HistoryExact=True, nonemptyHistoricalContextRetained=True,
            noMigrationInvoked=True, newPostgresqlIdentities=True, compatible712StartupAndAccount=True,
            quietActivationAndExplicitRollback=True, uncertainOwnedLaunchStopped=True,
            foreignLaunchRetained=True, compensatedWriteBlocksRollback=True, allBranchesRetained=True,
            normalStartRestoresAutovacuum=True, persistentPostgresqlConfigHashesUnchanged=True,
            sourceRootArtifactsWithoutArtifactDirectorySupported=True, uncertainPidMarkerRetained=True,
            lockedApplicationRejected=True, privateAndSharedLibraryRetained=True,
            favoritesAndInventoryRetained=True, preferencesAndReportReceiptsRetained=True, **observed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--group', choices=('contracts', 'native', 'private-inputs', 'all'), default='all')
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    args.evidence.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__).resolve()] + [ROOT / 'tools/windows' / n for n in
        ('qa_xls11_source847.py', 'qa_xls11_candidate847.py', 'qa_xls11_switch847.py', 'qa_xls11_update847.py',
         'Qa-Local.py', 'qa_schema_switch.py', 'qa_schema11_source772.py', 'qa_schema6_source.py',
         'qa_schema_candidate.py', 'qa_schema5_candidate.py', 'qa_schema5_switch.py', 'qa_schema6_real_candidate.py', 'windows_job.py')]
    sources += [ROOT / 'development/server/tests/pg_support.py', ROOT / 'development/server/tests/test_inventory_movement_gui.py']
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
        suites.append(unittest.defaultTestLoader.loadTestsFromTestCase(Closed847Contracts))
    if args.group == 'private-inputs':
        suites.append(unittest.defaultTestLoader.loadTestsFromName('test_initializer_secret_must_be_sealed_unchanged_and_inside_copy', Closed847Contracts))
    if args.group in ('native', 'all'):
        suites.append(unittest.defaultTestLoader.loadTestsFromTestCase(Native847Acceptance))
    with (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(suites))
    data = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), group=args.group,
        testsRun=result.testsRun, successful=result.wasSuccessful(), cases=result.records,
        sourceHashes=before, inputsUnchanged=before == hashes(), actualQaAccessed=False,
        labs=Native847Acceptance.outcomes, observations=Native847Acceptance.observations)
    (args.evidence / 'result.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return 0 if data['successful'] and data['inputsUnchanged'] and all(all(row.values()) for row in data['labs']) else 1


if __name__ == '__main__':
    sys.exit(main())
