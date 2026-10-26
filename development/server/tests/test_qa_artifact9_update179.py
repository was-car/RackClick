"""179 contracts and ONE fresh populated schema9 Windows artifact fixture.

No implicit build, installation, source QA profile or user results access.
"""
import argparse
import copy
from datetime import datetime, timezone
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

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/windows'))
from pg_support import Lab, Client, free_port
from pg_lab_recovery import sha256
from test_inventory_movement_gui import fixture
from test_qa_schema6_real import NativeHttp
from test_postgres import EvidenceResult, Tee
from qa_schema_candidate import snapshot
from qa_schema6_source import PRIVATE_FILES
from qa_schema_switch import start_supervisor, read_owner
import qa_artifact9_source179 as contracts
import qa_artifact9_update179 as updater


class Closed179Contracts(unittest.TestCase):
    def test_pending_wrong_external_pin_fails_closed(self):
        for value in (None, ('elsewhere.json', '0' * 64), ('', ''), ['not', 'a-tuple']):
            with patch.object(contracts, 'TARGET179', value):
                with self.assertRaises(contracts.UpdateError):
                    contracts.load_target()
        self.assertEqual(contracts.SOURCE_SHA256, '324201ffc1e7cde6870114e76e37c0b381c9869ff05fcf2aaa34ad013fb54df7')
        self.assertNotIn('Source7', [c.__name__ for c in contracts.Source9.__mro__])

    def test_sql9_exact_and_only_artifact_config_fields(self):
        baseline = contracts.load_source().expected
        changed = copy.deepcopy(baseline)
        name = next(n for n in changed['server'] if n.startswith('database/009-'))
        changed['server'][name] = '0' * 64
        with self.assertRaises(contracts.UpdateError):
            contracts.require_same_sql9(changed, baseline)
        previous = dict(connection='synthetic', artifactDirectory='old', dllSha256='old', bundleSha256='old')
        selected = dict(previous, artifactDirectory='new', dllSha256='new', bundleSha256='new')
        self.assertEqual(contracts.require_config_change(previous, selected), contracts.CHANGED_FIELDS)
        for field in ('connection', 'database', 'pgPort', 'webPort'):
            with self.assertRaises(contracts.UpdateError):
                contracts.require_config_change(previous, dict(selected, **{field: 'changed'}))

    def test_foreign_prelaunch_never_grants_stop_ownership(self):
        runtime = updater.OwnedRuntime179(ROOT, {'webPort': 12345}, ROOT / 'synthetic-pointer')
        with patch.object(updater, 'app_stopped'), patch.object(updater, 'pg_running', return_value=True), \
                patch.object(updater, 'qa_module') as qa:
            with self.assertRaises(contracts.UpdateError):
                runtime.start_pg()
            runtime.stop()
            self.assertFalse(runtime.owned)
            qa.assert_not_called()

    def test_cli_failure_is_unknown_and_has_no_later_rollback(self):
        arguments = ['qa_artifact9_update179.py', 'update', '--source', str(ROOT), '--pointer', str(ROOT / 'synthetic.json')]
        errors = io.StringIO()
        with patch.object(sys, 'argv', arguments), \
                patch.object(updater, 'update', side_effect=contracts.UpdateError('recovery_required')), \
                patch.object(sys, 'stderr', errors):
            self.assertEqual(updater.main(), 1)
        value = json.loads(errors.getvalue())
        self.assertFalse(value['activationConfirmed'])
        self.assertIsNone(value['leftRunning'])
        with patch.object(sys, 'argv', [*arguments[:1], 'rollback', *arguments[2:]]), \
                patch.object(sys, 'stderr', io.StringIO()):
            with self.assertRaises(SystemExit) as denied:
                updater.main()
        self.assertEqual(denied.exception.code, 2)


class Native179Acceptance(unittest.TestCase):
    outcomes = []
    observations = []

    def setUp(self):
        self.lab = None
        self.process = None
        self.cfg = None
        baseline = contracts.load_source()
        self.lab = lab = Lab('manual-qa-rc9-schema9').start()
        self.db = lab.create_database('manual-qa-rc9')
        self.ids, self.password = fixture(lab, self.db, baseline.server / 'RackClick.Server.dll')
        lab.grant_runtime(self.db)
        art = lab.directory / 'versions' / uuid.uuid4().hex
        for name in ('server', 'frontend'):
            shutil.copytree(getattr(baseline, name), art / name)
        self.cfg = dict(directory=str(lab.directory), profile='rc9', host='127.0.0.1', webPort=free_port(),
            pgPort=lab.port, database=self.db.name, connection=self.db.connection(lab.port), artifactDirectory=str(art),
            dllSha256=baseline.expected['server']['RackClick.Server.dll'], bundleSha256=baseline.expected['frontend']['app.js'],
            qaCustomerId=self.ids['customer'], qaCustomerName='Artifact179 synthetic source Ω', restoreSourceSha256='0' * 64,
            restoreCounts={'customers': 2, 'racks': 2, 'devices': 3, 'ports': 6, 'connections': 1})
        self.config = lab.directory / 'manual-qa.json'
        updater.save(self.config, self.cfg)
        for name in PRIVATE_FILES:
            (lab.directory / name).write_text('Synthetic179 private fixture Ω; never real QA\n', encoding='utf-8')
        (lab.directory / 'server.lock').write_bytes(b'0')
        home = lab.directory / 'artifact9-home'; home.mkdir()
        self.pointer = home / 'current.json'
        updater.save(self.pointer, {'directory': str(lab.directory)})
        self.pointer_bytes = self.pointer.read_bytes()
        self.original_config = self.config.read_bytes()
        house, actor = lab.sql(self.db, "SELECT id FROM systemhaus;SELECT id FROM app_user WHERE username='move-admin'").splitlines()
        event, request, operation = (str(uuid.uuid4()) for _ in range(3))
        lab.sql(self.db, f"""BEGIN;
            INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,after_json)
              VALUES('{event}','{house}','{actor}','{request}','synthetic179.history','{house}','{{}}');
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
        # Seed the private library through the BASELINE173 API in this NEW fixture.
        # The actual Wascar profile is never opened by this test.
        seed_server = lab.start_server(self.db, dll=baseline.server / 'RackClick.Server.dll', frontend=baseline.frontend)
        seed_client = Client(seed_server)
        self.assertEqual(seed_client.login('move-admin', self.password).status, 200)
        actor_id = seed_client.request('GET', '/api/v1/me').json()['user']['id']
        source_revision = seed_client.request('GET', f"/api/v1/customers/{self.ids['customer']}/project").json()['revision']
        captured = seed_client.request('POST', f"/api/v1/customers/{self.ids['customer']}/catalog/private-templates",
            {'type':'capture','deviceId':self.ids['a'],'name':'Plantilla histórica Ω','sourceRevision':source_revision},
            {'If-Match':'"templates-0"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor_id})
        self.assertEqual(captured.status, 200)
        self.template_id = captured.json()['result']['templateId']
        self.template_hash = captured.json()['result']['definitionSha256']
        seed_server.close()
        source = contracts.Source9(lab.directory, self.pointer)
        self.before = snapshot(source.sql)
        self.history9 = source.check_schema9()
        self.oid = source.sql('SELECT oid FROM pg_database WHERE datname=current_database()')
        self.immutable_hashes = source.hashes
        self.pg_configs = {name: sha256(lab.directory / 'data' / name) for name in ('postgresql.conf', 'pg_hba.conf', 'pg_ident.conf')}
        self.database_count = len(source.meta['databases'])
        for name in ('audit_context', 'audit_context_object', 'app_session', 'user_catalog_favorites',
                     'user_catalog_favorite', 'user_catalog_favorite_operation', 'user_device_templates',
                     'user_device_template', 'user_device_template_operation'):
            self.assertGreater(self.before[name]['rows'], 0)
        lab.close()

    def tearDown(self):
        if self.lab:
            cfg = json.loads(self.config.read_bytes()) if self.cfg else None
            if cfg and updater.qa_module().running(self.lab.directory):
                updater.stop_application(self.lab.directory, cfg)
            if updater.pg_running(self.lab.directory):
                updater.qa_module().control(self.lab.directory, 'stop')
            if self.process:
                self.process.wait(timeout=30)
            self.lab.close()
            self.outcomes.append(dict(applicationStopped=not updater.qa_module().running(self.lab.directory),
                postgresqlStopped=not updater.pg_running(self.lab.directory),
                testServersStopped=all(s.process.poll() is not None for s in self.lab.servers)))

    def immutable(self):
        self.assertEqual(self.pointer.read_bytes(), self.pointer_bytes)
        self.assertEqual({n: sha256(self.lab.directory / n) for n in self.immutable_hashes}, self.immutable_hashes)
        self.assertEqual({n: sha256(self.lab.directory / 'data' / n) for n in self.pg_configs}, self.pg_configs)
        self.assertEqual(len(json.loads((self.lab.directory / 'lab.json').read_bytes())['databases']), self.database_count)

    def run_update(self, hook=None):
        return updater.update(self.lab.directory, self.pointer, hook=hook)

    def test_one_source9_favorites_quiet_update_recovery_and_activity(self):
        lab = self.lab
        with self.assertRaises(contracts.UpdateError):
            contracts.Source9(lab.directory, self.pointer, real=True)
        with updater.profile_lock(self.pointer):
            with self.assertRaises(Exception) as busy:
                self.run_update()
        self.assertEqual(getattr(busy.exception, 'code', None), 'profile_busy')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', self.cfg['webPort'])); listener.listen()
            with self.assertRaises(contracts.UpdateError):
                self.run_update()
        updater.qa_module().control(lab.directory, 'start')
        foreign_pid = (lab.directory / 'data/postmaster.pid').read_text().splitlines()[0]
        with self.assertRaises(contracts.UpdateError) as foreign:
            self.run_update()
        self.assertEqual(foreign.exception.code, 'source9_pg_already_active')
        self.assertEqual((lab.directory / 'data/postmaster.pid').read_text().splitlines()[0], foreign_pid)
        updater.qa_module().control(lab.directory, 'stop')  # Explicit fixture actor.

        control = updater.start_private_pg173
        raised = []
        def uncertain(directory):
            result = control(directory)
            if not raised:
                raised.append(True)
                raise RuntimeError('Synthetic failure AFTER owned PG really started')
            return result
        with patch.object(updater, 'start_private_pg173', side_effect=uncertain):
            with self.assertRaises(contracts.UpdateError) as owned:
                self.run_update()
        self.assertEqual(owned.exception.code, 'rolled_back')
        self.assertFalse(updater.pg_running(lab.directory))
        self.assertEqual(self.config.read_bytes(), self.original_config)

        for stage in ('prepared', 'after_config'):
            external = {}
            def other_actor(name, result):
                if name == stage:
                    updater.start_private_pg173(lab.directory)
                    external['pid'] = (lab.directory / 'data/postmaster.pid').read_text().splitlines()[0]
            with self.assertRaises(contracts.UpdateError) as active:
                self.run_update(other_actor)
            self.assertEqual(active.exception.code, 'recovery_required')
            self.assertTrue(updater.pg_running(lab.directory))
            self.assertEqual((lab.directory / 'data/postmaster.pid').read_text().splitlines()[0], external['pid'])
            updater.qa_module().control(lab.directory, 'stop')  # Fixture actor owns its foreign injection.
            updater.atomic_bytes(self.config, self.original_config)  # Synthetic actor resets only its fixture config.
            self.immutable()

        def fail_after_selection(name, result):
            if name == 'after_config':
                raise RuntimeError('Synthetic failure after atomic artifact selection')
        with self.assertRaises(contracts.UpdateError) as quiet:
            self.run_update(fail_after_selection)
        self.assertEqual(quiet.exception.code, 'rolled_back')
        self.assertEqual(self.config.read_bytes(), self.original_config)
        self.assertFalse(updater.pg_running(lab.directory))
        self.immutable()

        success = self.run_update()
        self.assertEqual(success.state, 'committed')
        selected = json.loads(self.config.read_bytes())
        self.assertEqual(contracts.require_config_change(self.cfg, selected), contracts.CHANGED_FIELDS)
        self.assertEqual((success.version / 'previous-config.json').read_bytes(), self.original_config)
        proof = json.loads(success.journal.read_bytes())
        self.assertEqual(proof['rows'], self.before)
        self.assertEqual(proof['history'], self.history9)
        self.assertEqual(proof['databaseOid'], self.oid)
        self.assertTrue(proof['stopConfirmed'])
        self.immutable()

        # Only this fixture actor resets to173 while absolutely quiet, before any
        # login/write. This is not a later rollback API or a post-QA guarantee.
        updater.atomic_bytes(self.config, self.original_config)
        observed = {}
        def net_zero(name, result):
            if name == 'after_start':
                before = snapshot(lambda q: read_owner(lab.directory, self.cfg, q))
                house = read_owner(lab.directory, self.cfg, 'SELECT id FROM systemhaus')
                identity = str(uuid.uuid4())
                lab.sql(self.db, f"BEGIN;INSERT INTO customer(id,systemhaus_id,name) VALUES('{identity}','{house}','Synthetic netzero179');DELETE FROM customer WHERE id='{identity}';COMMIT;", sensitive=True)
                self.assertEqual(snapshot(lambda q: read_owner(lab.directory, self.cfg, q)), before)
                reference = json.loads(result.journal.read_bytes())['activityBaseline']
                now = updater.activity_watermark(lab.directory, self.cfg)
                self.assertGreater(int(now['xmax']), int(reference['xmax']))
                observed.update(netZeroRowsEqual=True, activityAdvanced=True)
                raise RuntimeError('Synthetic committed activity must prevent automatic rollback')
        with self.assertRaises(contracts.UpdateError) as changed:
            self.run_update(net_zero)
        self.assertEqual(changed.exception.code, 'recovery_required')
        selected = json.loads(self.config.read_bytes())
        self.assertEqual(selected['artifactDirectory'], str(changed.exception.result.version))
        self.assertFalse(updater.pg_running(lab.directory))
        self.immutable()

        # Actual source179 startup/auth/write/readback only in this NEW fixture,
        # after the guarded update/negative. No automatic downgrade is attempted.
        self.process = start_supervisor(lab.directory, selected)
        client = Client(NativeHttp(selected))
        self.assertEqual(client.login('move-admin', self.password).status, 200)
        self.assertEqual(client.request('GET', f"/api/v1/customers/{self.ids['customer']}/catalog/favorites").json()['presetKeys'], ['pdu'])
        actor = client.request('GET', '/api/v1/me').json()['user']['id']
        personal = client.request('GET', f"/api/v1/customers/{self.ids['customer']}/catalog/private-templates").json()
        self.assertEqual(personal['templates'][0]['id'], self.template_id)
        raw_before = client.request('GET', f"/api/v1/customers/{self.ids['customer']}/catalog/private-templates/{self.template_id}").json()['template']['definitionBase64']
        renamed = client.request('POST', f"/api/v1/customers/{self.ids['customer']}/catalog/private-templates",
            {'type':'rename','templateId':self.template_id,'name':'Nombre nuevo después de actualizar Ω'},
            {'If-Match':f'"templates-{personal["revision"]}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor})
        self.assertEqual(renamed.status, 200)
        self.assertEqual(renamed.json()['result']['definitionSha256'], self.template_hash)
        self.assertEqual(client.request('GET', f"/api/v1/customers/{self.ids['customer']}/catalog/private-templates/{self.template_id}").json()['template']['definitionBase64'], raw_before)
        revision = client.request('GET', '/api/v1/systemhaus').json()['revision']
        response = client.request('POST', '/api/v1/customers', {'name': 'Artifact179 durable synthetic write'},
            {'If-Match': f'"{revision}"', 'Idempotency-Key': str(uuid.uuid4()), 'X-RackClick-Actor': actor})
        self.assertEqual(response.status, 201)
        customer = response.json()['resource']['id']
        updater.stop_application(lab.directory, selected); self.process.wait(timeout=30)
        self.process = start_supervisor(lab.directory, selected)
        self.assertEqual(client.request('GET', '/api/v1/me').status, 200)
        self.assertEqual(client.request('GET', f"/api/v1/customers/{self.ids['customer']}/catalog/private-templates").json()['templates'][0]['name'], 'Nombre nuevo después de actualizar Ω')
        self.assertEqual(read_owner(lab.directory, selected, f"SELECT count(*) FROM customer WHERE id='{customer}'"), '1')
        self.assertEqual(read_owner(lab.directory, selected, 'SHOW autovacuum'), 'on')
        updater.stop_application(lab.directory, selected); self.process.wait(timeout=30)
        self.immutable()
        self.observations.append(dict(oneNewSchema9Fixture=True, sameDatabaseOid=True, allSchema9RowsHistoryPreserved=True,
            favoritesSessionsAuditInitiallyNonempty=True, exactThreeConfigFields=True, pointerAndEightInputsRetained=True,
            fourApplicationPrivateFilesRetained=True, persistentPgConfigUnchanged=True, source173PairRetained=True,
            profileLockAndPortRejected=True, foreignPgRetained=True, uncertainOwnLaunchStopped=True,
            quietAutomaticRollback=True, compensatedWriteBlocksAutomaticRollback=True, selected179RetainedAfterActivity=True,
            fixtureFavoriteLoginWriteReadRestart=True, privateLibraryInitiallyPopulated=True,
            privateRenameAfterUpdateAndRestart=True, normalStartRestoresAutovacuum=True, **observed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--group', choices=('contracts', 'native'), required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__).resolve()] + [ROOT / 'tools/windows' / n for n in
        ('qa_artifact9_source179.py', 'qa_artifact9_update179.py', 'qa_schema9_source173.py', 'qa_schema9_switch173.py',
         'qa_schema6_source.py', 'qa_schema_switch.py', 'Qa-Local.py', 'windows_job.py')]
    sources += [ROOT / 'development/server/tests' / n for n in ('pg_support.py', 'test_inventory_movement_gui.py')]
    def hashes():
        return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources}
    before = hashes()
    baseline = contracts.load_source()
    target = contracts.load_target() if args.group == 'native' else None
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Closed179Contracts if target is None else Native179Acceptance)
    with (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(suite)
    data = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), group=args.group,
        testsRun=result.testsRun, successful=result.wasSuccessful(), cases=result.records,
        sourceHashes=before, inputsUnchanged=before == hashes(), actualQaAccessed=False,
        sourceUnchanged=baseline.validate() == baseline.expected,
        targetUnchanged=target.validate() == target.expected if target else None,
        sourceManifestSha256=sha256(baseline.manifest), targetManifestSha256=sha256(target.manifest) if target else None,
        labs=Native179Acceptance.outcomes, observations=Native179Acceptance.observations)
    (args.evidence / 'result.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return 0 if data['successful'] and data['inputsUnchanged'] and all(all(row.values()) for row in data['labs']) else 1


if __name__ == '__main__':
    sys.exit(main())
