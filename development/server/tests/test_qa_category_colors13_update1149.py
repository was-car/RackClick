"""1149:4 closed contracts +1 compact heterogeneous PostgreSQL12/11 ->13/12 fixture.

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
import qa_category_colors13_source1149 as contracts
import qa_category_colors13_candidate1149 as copier
import qa_category_colors13_switch1149 as coordinator
import qa_category_colors13_update1149 as cli
from test_qa_port_colors12_update1029 import Native1029Acceptance
import qa_port_colors12_switch1029 as old_coordinator
from qa_schema_switch import activity_watermark, require_unchanged_activity, read_owner

class Closed1149Contracts(unittest.TestCase):
    def test_pending_or_wrong_pin_fails_closed(self):
        with patch.object(contracts, 'TARGET1149', None):
            with self.assertRaises(contracts.Schema13Error) as denied:
                contracts.load_target()
            self.assertEqual(denied.exception.code, 'target1149_pin_invalid')
        for value in (('elsewhere.json', '0' * 64), ('', ''), ['not', 'a-tuple']):
            with patch.object(contracts, 'TARGET1149', value):
                with self.assertRaises(contracts.Schema13Error):
                    contracts.load_target()
        self.assertEqual(contracts.SOURCE_SHA256, 'b589609154fed1567106ef0865972155258f0f5474128c73076f4697d43b8bda')
        self.assertEqual([c.__name__ for c in contracts.Source969.__mro__], ['Source969', 'Source4', 'object'])
        source = contracts.load_source()
        self.assertEqual((source.revision, source.schema, len(source.expected['server']), len(source.expected['frontend'])), (969, 12, 21, 18))
        target = contracts.load_target()
        self.assertEqual((target.revision, target.schema, len(target.expected['server']), len(target.expected['frontend'])), (1089, 13, 22, 18))
        sql = lambda d: {k:v for k,v in d.expected['server'].items() if k.startswith('database/')}
        self.assertEqual(sql(source),{k:v for k,v in sql(target).items() if not k.startswith('database/013-')})
        self.assertEqual(set(sql(target))-set(sql(source)),{'database/013-user-category-colors.sql'})
        for name in ('Npgsql.dll','RackClick.Server.deps.json','RackClick.Server.runtimeconfig.json'):
            self.assertEqual(source.expected['server'][name],target.expected['server'][name])
        self.assertIs(contracts.CategoryColors13Error,contracts.Schema13Error)
        self.assertNotEqual(source.expected['frontend']['app.js'],target.expected['frontend']['app.js'])
        self.assertEqual({k:v for k,v in source.expected['frontend'].items() if k != 'app.js'},
                         {k:v for k,v in target.expected['frontend'].items() if k != 'app.js'})

    def test_initializer_secret_must_be_sealed_unchanged_and_inside_copy(self):
        directory = ROOT / '.local' / ('static-secret1149-' + uuid.uuid4().hex)
        directory.mkdir(exist_ok=False)
        password = directory / 'init-password.txt'
        admin = directory / 'admin.pgpass'
        password.write_bytes(b'Synthetic non-operational initializer\n')
        admin.write_bytes(b'Synthetic non-operational passfile\n')
        expected = {p.name: sha256(p) for p in (password, admin)}
        copier.require_private_input_hashes(directory, expected)
        with self.assertRaises(contracts.Schema13Error):
            copier.require_private_input_hashes(directory, {'admin.pgpass':expected['admin.pgpass']})
        original = password.read_bytes()
        password.write_bytes(original + b'corrupt')
        with self.assertRaises(contracts.Schema13Error):
            copier.require_private_input_hashes(directory, expected)
        password.write_bytes(original)
        copier.require_private_input_hashes(directory, expected)
        with self.assertRaises(contracts.Schema13Error):
            copier.require_private_input_hashes(directory, {**expected, '../../AGENTS.md':sha256(ROOT / 'AGENTS.md')})
        self.assertTrue(directory.is_relative_to(ROOT / '.local'))
        self.assertFalse((directory / 'data').exists())

    def test_foreign_prelaunch_does_not_grant_ownership(self):
        runtime = coordinator.OwnedRuntime(ROOT, {'webPort': 12345})
        with patch.object(coordinator, 'app_stopped'), patch.object(coordinator, 'pg_running', return_value=True), \
                patch.object(coordinator, 'qa_module') as qa:
            with self.assertRaises(contracts.Schema13Error):
                runtime.start_pg()
            runtime.stop()
            self.assertFalse(runtime.owned)
            qa.assert_not_called()

    def test_cli_reports_schema_and_revision_or_unknown_failure(self):
        arguments = ['qa_category_colors13_update1149.py', 'rollback', '--source', str(ROOT),
                     '--pointer', str(ROOT / 'synthetic.json'), '--candidate', str(ROOT)]
        output = io.StringIO()
        with patch.object(sys, 'argv', arguments), patch.object(cli, 'rollback', return_value=SimpleNamespace(state='rolled_back')), \
                patch.object(sys, 'stdout', output):
            self.assertEqual(cli.main(), 0)
        data = json.loads(output.getvalue())
        self.assertEqual((data['sourceSchema'], data['candidateSchema'], data['selectedSchema']), (12, 13, 12))
        self.assertEqual((data['sourceRevision'], data['candidateRevision'], data['selectedRevision']), (969, 1089, 969))
        for action, selected, state in (('activate',False,'committed'),('validate',False,None),('validate',True,None)):
            argv = ['qa_category_colors13_update1149.py',action,'--source',str(ROOT),'--pointer',str(ROOT/'synthetic.json'),
                    '--candidate',str(ROOT)] + (['--selected'] if selected else [])
            output = io.StringIO()
            with patch.object(sys,'argv',argv), patch.object(cli,action if action != 'validate' else 'validate_operation',
                    return_value=SimpleNamespace(state=state)), patch.object(sys,'stdout',output):
                self.assertEqual(cli.main(),0)
            value = json.loads(output.getvalue())
            self.assertEqual((value['selectedSchema'],value['selectedRevision']),
                             (13,1089) if action == 'activate' or selected else (12,969))
            if action == 'validate':
                self.assertFalse(value['databaseTestExecuted'])
        errors = io.StringIO()
        with patch.object(sys, 'argv', arguments), patch.object(cli, 'rollback', side_effect=contracts.Schema13Error('recovery_required')), \
                patch.object(sys, 'stderr', errors):
            self.assertEqual(cli.main(), 1)
        self.assertIsNone(json.loads(errors.getvalue())['selectedSchema'])
        self.assertIsNone(json.loads(errors.getvalue())['selectedRevision'])
        self.assertIsNone(json.loads(errors.getvalue())['leftRunning'])


class Native1149Acceptance(unittest.TestCase):
    outcomes = []
    observations = []

    def setUp(self):
        self.clusters = []
        # Genuine historical setup/preparation helpers only; no historical case
        # or historical result is executed/relabelled as a new test.
        Native1029Acceptance.setUp(self)
        self.clusters = [('source849',self.source_lab.directory,self.cfg)]
        self.fixture969 = old_coordinator.prepare_operation(self.source_lab.directory,self.pointer).candidate
        self.addCleanup(self.fixture969.close)
        self.source_lab = lab = self.fixture969.lab
        self.cfg, self.db = self.fixture969.cfg, self.fixture969.database
        self.clusters.insert(0,('source969',lab.directory,self.cfg))
        for label,record in (('source832',self.fixture849.record),('source712',self.fixture832.record)):
            directory = Path(record['sourceDirectory'])
            self.clusters.append((label,directory,json.loads((directory/'manual-qa.json').read_bytes())))
        (lab.directory/'server.lock').write_bytes(b'0')
        home = lab.directory/'category-colors13-home';home.mkdir()
        self.pointer = home/'current.json'
        copier.save(self.pointer,{'directory':str(lab.directory)})
        self.pointer_bytes = self.pointer.read_bytes()
        prior_prepared = {n:(lab.directory/n).read_bytes() for n in ('port-colors12-prepared.json','port-colors12-prepared.sha256')}
        runtime = coordinator.OwnedRuntime(lab.directory,self.cfg)
        self.addCleanup(runtime.stop)
        runtime.start_pg()
        try:
            lab.sql(self.db,"UPDATE systemhaus SET name='Current969 primary12 Ω'",sensitive=True)
            lab.sql(self.fixture969.recovered,"UPDATE systemhaus SET name='Independent849 recovery11 Ω'",sensitive=True)
            server = lab.start_server(self.db,dll=lab.directory/'server/RackClick.Server.dll',frontend=lab.directory/'frontend')
            self.extra_servers.append(server)
            client = Client(server);client.cookie,client.csrf,actor = self.seed_session
            self.palette_request = str(uuid.uuid4())
            self.palette_body = {'colors':{'rj45':'#123456','usb_c':'#654321'}}
            reply = client.request('POST','/api/v1/me/port-colors',self.palette_body,
                {'If-Match':'"port-colors-0"','Idempotency-Key':self.palette_request,'X-RackClick-Actor':actor})
            self.assertEqual(reply.status,200);self.palette_result = reply.json()
            server.close()
        finally:
            runtime.stop()
        self.assertEqual({n:(lab.directory/n).read_bytes() for n in prior_prepared},prior_prepared)
        self.source = contracts.Source969(lab.directory,self.pointer)
        runtime.start_pg()
        try:
            self.source_states = self.source.database_states()
            self.before = self.source_states['primary']['snapshot']
            self.history12 = self.source_states['primary']['history']
            self.assertEqual((len(self.before),len(self.source_states['recovery849']['snapshot'])),(37,35))
            self.assertEqual((len(self.history12),len(self.source_states['recovery849']['history'])),(12,11))
            self.assertNotEqual(self.before['systemhaus'],self.source_states['recovery849']['snapshot']['systemhaus'])
        finally:
            runtime.stop()
        self.source_static_hashes = dict(self.source.hashes)

    def tearDown(self):
        for server in reversed(getattr(self,'extra_servers',[])):
            server.close()
        clusters = list(self.clusters)
        if getattr(self,'candidate',None):
            clusters.insert(0,('target1089',self.candidate.directory,self.candidate.cfg))
        for label,directory,cfg in clusters:
            if coordinator.qa_module().running(directory):
                coordinator.stop_application(directory,cfg)
            if coordinator.pg_running(directory):
                coordinator.qa_module().control(directory,'stop')
            self.outcomes.append(dict(role=label,applicationStopped=not coordinator.qa_module().running(directory),
                                      postgresqlStopped=not coordinator.pg_running(directory)))

    def activate(self,hook=None):
        return coordinator.activate(self.source_lab.directory,self.pointer,self.candidate.directory,hook=hook)

    def test_compact_heterogeneous_copy_and_four_activity_guards(self):
        original_guard = coordinator._guarded_restore
        def diagnostic_guard(*args,**kwargs):
            try:
                return original_guard(*args,**kwargs)
            except Exception as error:
                code = getattr(error,'code',None)
                if code is None and re.fullmatch(r'[a-z0-9_]{1,100}',str(error)):
                    code = str(error)
                if not isinstance(code,str) or not re.fullmatch(r'[a-z0-9_]{1,100}',code):
                    code = None
                frames = traceback.extract_tb(error.__traceback__);frame = frames[-1] if frames else None
                try:
                    copier.save(args[1].directory/('category-colors13-diagnostic-private-'+uuid.uuid4().hex+'.json'),
                        dict(exceptionClass=type(error).__module__+'.'+type(error).__qualname__,code=code,
                             lastSymbol=None if frame is None else dict(file=Path(frame.filename).name,function=frame.name,line=frame.lineno)))
                except Exception:
                    pass
                raise
        with patch.object(coordinator,'_guarded_restore',side_effect=diagnostic_guard):
            self._run_compact()

    def _run_compact(self):
        lab = self.source_lab
        seal = lab.directory/'port-colors12-prepared.sha256';original = seal.read_bytes()
        try:
            seal.write_bytes(original+b'corrupt')
            with self.assertRaises(contracts.Schema13Error):
                contracts.Source969(lab.directory,self.pointer)
        finally:
            seal.write_bytes(original)
        with coordinator.profile_lock(self.pointer):
            with self.assertRaises(Exception) as locked:
                coordinator.prepare_operation(lab.directory,self.pointer)
        self.assertEqual(getattr(locked.exception,'code',None),'profile_busy')
        prepared = coordinator.prepare_operation(lab.directory,self.pointer)
        self.candidate = candidate = prepared.candidate
        self.assertEqual(prepared.state,'prepared')
        self.assertEqual(candidate.record['sourceDatabaseStates'],self.source_states)
        self.assertTrue(copier.additive_copy(self.before,self.history12,candidate.record['candidateSnapshot'],candidate.record['candidateHistory']))
        self.assertEqual((len(candidate.record['candidateSnapshot']),len(candidate.record['sourceSnapshot'])),(39,37))
        self.assertTrue(all(candidate.record['candidateSnapshot'][t]['rows']==0 for t in contracts.NEW_TABLES))
        self.assertEqual(copier.load_prepared(candidate.directory).cfg,candidate.cfg)
        target_record = (candidate.directory/copier.PREPARED).read_bytes()
        source_record = (lab.directory/'port-colors12-prepared.json').read_bytes()
        with self.assertRaises(contracts.Schema13Error):
            contracts.checked_candidate_directory(lab.directory)
        self.assertEqual(self.activate().state,'committed')
        coordinator.validate_operation(lab.directory,self.pointer,candidate.directory,selected=True)
        self.assertEqual(coordinator.rollback(lab.directory,self.pointer,candidate.directory).state,'rolled_back')
        self.assertEqual(self.pointer.read_bytes(),self.pointer_bytes)
        self.assertEqual(self.activate().state,'committed')
        selected = self.pointer.read_bytes()
        # Old969 is started ONLY on its separate DB12; readiness/bundle reads
        # allocate no application session and must preserve the prepared boundary.
        runtime = coordinator.OwnedRuntime(candidate.directory,candidate.cfg)
        runtime.start_pg()
        try:
            server = candidate.lab.start_server(candidate.recovered,
                dll=candidate.directory/'versions/category-colors13-source969-recovery/server/RackClick.Server.dll',
                frontend=candidate.directory/'versions/category-colors13-source969-recovery/frontend')
            self.extra_servers.append(server)
            self.assertEqual(server.request('GET','/health/ready').json(),{'status':'ready','schemaVersion':12})
            self.assertEqual(hashlib.sha256(server.request('GET','/app.js').body).hexdigest(),candidate.recovery_cfg['bundleSha256'])
            server.close();candidate.verify_rows_and_activity()
        finally:
            runtime.stop()
        source_runtime = coordinator.OwnedRuntime(lab.directory,self.cfg)
        source_runtime.start_pg();runtime.start_pg()
        observed = []
        try:
            roles = [
                ('source.primary12',lab,self.db,self.cfg,lab.directory/'server',12,37),
                ('source.recovery84911',lab,self.fixture969.recovered,self.source.recovery_cfg,self.source.recovery_art/'server',11,35),
                ('target.primary13',candidate.lab,candidate.database,candidate.cfg,candidate.directory/'server',13,39),
                ('target.recovery96912',candidate.lab,candidate.recovered,candidate.recovery_cfg,candidate.directory/'versions/category-colors13-source969-recovery/server',12,37)]
            for role,owner,db,cfg,server_path,schema,tables in roles:
                read = lambda q:read_owner(owner.directory,cfg,q)
                rows_before = snapshot(read);hist_before = history(read,server_path,schema)
                observed_before = activity_watermark(owner.directory,cfg)
                identity = str(uuid.uuid4());house = read('SELECT id FROM systemhaus')
                owner.sql(db,f"BEGIN;INSERT INTO customer(id,systemhaus_id,name) VALUES('{identity}','{house}','Synthetic1149 net-zero');DELETE FROM customer WHERE id='{identity}';COMMIT;",sensitive=True)
                self.assertEqual(snapshot(read),rows_before);self.assertEqual(history(read,server_path,schema),hist_before)
                observed_after = activity_watermark(owner.directory,cfg)
                self.assertGreater(int(observed_after['xmax']),int(observed_before['xmax']))
                with self.assertRaises(Exception) as changed:
                    require_unchanged_activity(owner.directory,cfg,observed_before)
                self.assertEqual(getattr(changed.exception,'code',None),'candidate_activity_changed')
                if role=='source.primary12':
                    with self.assertRaises(Exception):copier.verify_source(self.source,candidate.record)
                if role=='target.primary13':
                    with self.assertRaises(Exception):candidate.verify_rows_and_activity()
                observed.append(dict(role=role,schema=schema,tables=tables,rowsAndHistoryExact=True,activityAdvanced=True,
                                     directGuardRejected=True,independentRollbackClaimed=False))
        finally:
            runtime.stop();source_runtime.stop()
        with self.assertRaises(contracts.Schema13Error) as denied:
            coordinator.rollback(lab.directory,self.pointer,candidate.directory)
        self.assertEqual(denied.exception.code,'recovery_required')
        self.assertEqual(self.pointer.read_bytes(),selected)
        self.assertEqual((candidate.directory/copier.PREPARED).read_bytes(),target_record)
        self.assertEqual((lab.directory/'port-colors12-prepared.json').read_bytes(),source_record)
        self.assertEqual(self.source.hashes,self.source_static_hashes)
        runtime.start_pg()
        try:
            server = candidate.lab.start_server(candidate.database,dll=candidate.directory/'server/RackClick.Server.dll',frontend=candidate.directory/'frontend')
            self.extra_servers.append(server)
            client = Client(server);client.cookie,client.csrf,actor = self.seed_session
            self.assertEqual(client.request('GET','/api/v1/me').json()['user']['id'],actor)
            reply = client.request('POST','/api/v1/me/port-colors',self.palette_body,
                {'If-Match':'"port-colors-0"','Idempotency-Key':self.palette_request,'X-RackClick-Actor':actor})
            self.assertEqual(reply.status,200);self.assertEqual(reply.json(),self.palette_result)
            self.assertEqual(client.request('GET','/api/v1/me/category-colors').status,200)
            self.assertEqual(client.request('GET',f'/api/v1/me/port-colors/operations/{self.palette_request}').json()['operation'],self.palette_result)
            server.close()
        finally:
            runtime.stop()
        self.source.unchanged(pointer=False);candidate.validate_static()
        self.observations.append(dict(genuinePrepared1029Fixture=True,sourceHeterogeneous37And35=True,target39AndRecovery37=True,
            only013Migration=True,newPostgresqlSecretsFive=True,applicationCredentialsAndPrivateFilesPreserved=True,
            sourcePrepared1029SealProtected=True,quietActivationAndRollback=True,compatible13And12Startup=True,
            originalSessionAndPalette12ReceiptRetained=True,newCategory13RouteAvailable=True,
            fourDirectActivityGuards=observed,finalRollbackCumulative=True,fourIndependentRollbacks=False,
            baselineOrJournalRenewals=0,actualQaAccessed=False))




def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--group', choices=('contracts', 'native', 'all'), default='all')
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    args.evidence.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__).resolve()] + [ROOT/'tools/windows'/n for n in
        ('qa_category_colors13_source1149.py','qa_category_colors13_candidate1149.py','qa_category_colors13_switch1149.py','qa_category_colors13_update1149.py',
         'qa_port_colors12_source1029.py','qa_port_colors12_candidate1029.py','qa_port_colors12_switch1029.py','qa_port_colors12_update1029.py',
         'qa_relations11_source909.py','qa_relations11_candidate909.py','qa_relations11_switch909.py','qa_relations11_update909.py',
         'qa_xls11_source847.py','qa_xls11_candidate847.py','qa_xls11_switch847.py','qa_xls11_update847.py',
         'qa_schema11_source772.py','qa_schema11_candidate772.py','qa_schema11_switch772.py','qa_schema11_update772.py',
         'Qa-Local.py','qa_schema_switch.py','qa_schema6_source.py','qa_schema_candidate.py','qa_schema5_candidate.py',
         'qa_schema5_switch.py','qa_schema6_real_candidate.py','windows_job.py','pg_lab_recovery.py')]
    sources += [ROOT/'development/server/tests'/n for n in
        ('pg_support.py','test_postgres.py','test_inventory_movement_gui.py',
         'test_qa_port_colors12_update1029.py','test_qa_relations11_update909.py','test_qa_xls11_update847.py')]
    sources += [contracts.SOURCE_MANIFEST,contracts.TARGET_MANIFEST,ROOT/'development/toolchain.lock.json']
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
        suites.append(unittest.defaultTestLoader.loadTestsFromTestCase(Closed1149Contracts))
    if args.group in ('native', 'all'):
        suites.append(unittest.defaultTestLoader.loadTestsFromTestCase(Native1149Acceptance))
    with (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(unittest.TestSuite(suites))
    data = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), group=args.group,
        testsRun=result.testsRun, successful=result.wasSuccessful(), cases=result.records,
        sourceHashes=before, inputsUnchanged=before == hashes(), actualQaAccessed=False,
        labs=Native1149Acceptance.outcomes, observations=Native1149Acceptance.observations)
    (args.evidence / 'result.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return 0 if data['successful'] and data['inputsUnchanged'] and all(all(row.values()) for row in data['labs']) else 1


if __name__ == '__main__':
    sys.exit(main())
