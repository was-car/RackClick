"""185 contracts and ONE fresh populated schema9 Windows artifact fixture.

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
import qa_artifact9_source185 as contracts
import qa_artifact9_update185 as updater


class Closed185Contracts(unittest.TestCase):
    def test_pending_wrong_external_pin_fails_closed(self):
        for value in (None, ('elsewhere.json', '0' * 64), ('', ''), ['not', 'a-tuple']):
            with patch.object(contracts, 'TARGET185', value):
                with self.assertRaises(contracts.UpdateError):
                    contracts.load_target()
        self.assertEqual(contracts.SOURCE_SHA256, '45631b5a820be45be447aa6ecb81584fcdcb9262584052d6f86de34569aadfd5')
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
        runtime = updater.OwnedRuntime185(ROOT, {'webPort': 12345}, ROOT / 'synthetic-pointer')
        with patch.object(updater, 'app_stopped'), patch.object(updater, 'pg_running', return_value=True), \
                patch.object(updater, 'qa_module') as qa:
            with self.assertRaises(contracts.UpdateError):
                runtime.start_pg()
            runtime.stop()
            self.assertFalse(runtime.owned)
            qa.assert_not_called()

    def test_cli_failure_is_unknown_and_has_no_later_rollback(self):
        arguments = ['qa_artifact9_update185.py', 'update', '--source', str(ROOT), '--pointer', str(ROOT / 'synthetic.json')]
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


class Native185Acceptance(unittest.TestCase):
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
            qaCustomerId=self.ids['customer'], qaCustomerName='Artifact185 synthetic source Ω', restoreSourceSha256='0' * 64,
            restoreCounts={'customers': 2, 'racks': 2, 'devices': 3, 'ports': 6, 'connections': 1})
        self.config = lab.directory / 'manual-qa.json'
        updater.save(self.config, self.cfg)
        for name in PRIVATE_FILES:
            (lab.directory / name).write_text('Synthetic185 private fixture Ω; never real QA\n', encoding='utf-8')
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
              VALUES('{event}','{house}','{actor}','{request}','synthetic185.history','{house}','{{}}');
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
        # Seed the private library through the BASELINE179 API in this NEW fixture.
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

    def test_one_source9_focal_update_power_compensation_restart(self):
        # New focal185 execution. Broad runtime-negative/rollback179 cases remain historical.
        source = contracts.Source9(self.lab.directory, self.pointer)
        result = self.run_update()
        self.assertEqual(result.state, 'committed')
        state = json.loads(result.journal.read_bytes())
        self.assertTrue(state['activationConfirmed']); self.assertFalse(state['leftRunning'])
        selected = json.loads(self.config.read_bytes())
        self.assertEqual({k for k in selected if selected[k] != self.cfg.get(k)}, contracts.CHANGED_FIELDS)
        self.assertEqual(source.artifacts(), contracts.load_source().expected)
        self.assertEqual((result.version/'previous-config.json').read_bytes(), self.original_config)
        self.assertEqual({'server':updater.artifact_manifest(result.version/'server'),'frontend':updater.artifact_manifest(result.version/'frontend')}, contracts.load_target().expected)
        updater.start_private_pg173(self.lab.directory)
        self.assertEqual(snapshot(source.sql), self.before)
        self.assertEqual(source.check_schema9(), self.history9)
        self.assertEqual(source.sql('SELECT oid FROM pg_database WHERE datname=current_database()'), self.oid)
        updater.qa_module().control(self.lab.directory, 'stop')
        self.immutable()
        self.process = start_supervisor(self.lab.directory, selected)
        client = Client(NativeHttp(selected))
        self.assertEqual(client.login('move-admin', self.password).status, 200)
        actor = client.request('GET', '/api/v1/me').json()['user']['id']
        path = f"/api/v1/customers/{self.ids['customer']}"
        before = client.request('GET', path+'/project').json()
        def send(body,revision):
            reply = client.request('POST',path+'/commands',body,{'If-Match':f'"{revision}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor})
            self.assertEqual(reply.status,200);return reply.json()
        changed=send({'type':'ports.update','payload':{'deviceId':self.ids['a'],'groupId':self.ids['ga'],'groupType':'rj45','portIds':[self.ids['pa'],self.ids['pa2']],'changes':{'poe':False,'watts':0}}},before['revision'])
        undo=send({'type':'operations.compensate','payload':{'operationId':changed['operationId']}},changed['revision'])
        restored=client.request('GET',path+'/project').json()
        for collection in ['ports','connections','devices','portGroups','racks','sites','buildings','rooms']:
            self.assertEqual(sorted(restored[collection],key=lambda x:x['id']),sorted(before[collection],key=lambda x:x['id']))
        self.assertEqual(restored['revision'],before['revision']+2)
        self.assertEqual(undo['result']['compensatedOperationId'],changed['operationId'])
        self.assertEqual(client.request('GET',path+'/catalog/favorites').json()['presetKeys'],['pdu'])
        self.assertEqual(client.request('GET',path+'/catalog/private-templates').json()['templates'][0]['id'],self.template_id)
        updater.stop_application(self.lab.directory,selected);self.process.wait(timeout=30)
        self.process=start_supervisor(self.lab.directory,selected)
        self.assertEqual(client.request('GET',path+'/project').json(),restored)
        self.assertEqual(read_owner(self.lab.directory,selected,'SHOW autovacuum'),'on')
        updater.stop_application(self.lab.directory,selected);self.process.wait(timeout=30)
        self.immutable()
        self.observations.append(dict(oneNewPopulatedSchema9Fixture=True,sameDatabaseOid=True,
            allRowsAndHistoryPreservedBeforeWrites=True,exactThreeConfigFields=True,source179PairRetained=True,
            pointerAndEightInputsRetained=True,fourPrivateFilesRetained=True,persistentPgConfigUnchanged=True,
            target185Exact=True,poeWattsAndLegacyTypeRestored=True,inventoryAndCablesExact=True,
            favoritesAndPrivateTemplateRetained=True,fixtureLoginWriteReadRestart=True,normalAutovacuumOn=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--group', choices=('contracts', 'native'), required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__).resolve()] + [ROOT / 'tools/windows' / n for n in
        ('qa_artifact9_source185.py', 'qa_artifact9_update185.py', 'qa_schema9_source173.py', 'qa_schema9_switch173.py',
         'qa_schema6_source.py', 'qa_schema_switch.py', 'Qa-Local.py', 'windows_job.py')]
    sources += [ROOT / 'development/server/tests' / n for n in ('pg_support.py', 'test_inventory_movement_gui.py')]
    def hashes():
        return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources}
    before = hashes()
    baseline = contracts.load_source()
    target = contracts.load_target() if args.group == 'native' else None
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Closed185Contracts if target is None else Native185Acceptance)
    with (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(suite)
    data = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), group=args.group,
        testsRun=result.testsRun, successful=result.wasSuccessful(), cases=result.records,
        sourceHashes=before, inputsUnchanged=before == hashes(), actualQaAccessed=False,
        sourceUnchanged=baseline.validate() == baseline.expected,
        targetUnchanged=target.validate() == target.expected if target else None,
        sourceManifestSha256=sha256(baseline.manifest), targetManifestSha256=sha256(target.manifest) if target else None,
        labs=Native185Acceptance.outcomes, observations=Native185Acceptance.observations)
    (args.evidence / 'result.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return 0 if data['successful'] and data['inputsUnchanged'] and all(all(row.values()) for row in data['labs']) else 1


if __name__ == '__main__':
    sys.exit(main())
