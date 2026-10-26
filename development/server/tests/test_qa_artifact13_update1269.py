"""1269:5 closed contracts +1 genuine1149 same-cluster artifact update.

Historical setup helpers create fresh fixtures; no historical cases are rerun.
No actual QA profile is discovered, launched or modified by this test entrypoint.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import shutil
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Client
from pg_lab_recovery import sha256
from test_postgres import EvidenceResult,Tee
from test_qa_category_colors13_update1149 import Native1149Acceptance
import qa_category_colors13_switch1149 as old_coordinator
import qa_artifact13_source1269 as contracts
import qa_artifact13_update1269 as updater
from qa_schema_switch import profile_lock,activity_watermark,require_unchanged_activity

class Closed1269Contracts(unittest.TestCase):
    def test_manifest_pins_only_appjs_changes_and_no_schema_transition(self):
        target=contracts.load_target();source=contracts.load_baseline()
        self.assertEqual((target.revision,target.schema),(1209,13))
        self.assertEqual(target.expected['server'],source.expected['server'])
        self.assertEqual((len(target.expected['server']),len(target.expected['frontend'])),(22,18))
        self.assertNotEqual(target.expected['frontend']['app.js'],source.expected['frontend']['app.js'])
        self.assertEqual({k:v for k,v in target.expected['frontend'].items() if k!='app.js'},
                         {k:v for k,v in source.expected['frontend'].items() if k!='app.js'})
        for pin in (None,('elsewhere.json','0'*64),('', ''),['not-a-tuple']):
            with patch.object(contracts,'TARGET1269',pin):
                with self.assertRaises(contracts.Artifact13Error):contracts.load_target()

    def test_overlay_requires_three_exact_configs_and_only_two_selected_fields(self):
        directory=ROOT/'.local/labs'/('manual-qa-rc9-schema13-'+uuid.uuid4().hex)
        operation=directory/'versions'/('artifact13-1209-'+uuid.uuid4().hex)
        operation.mkdir(parents=True)
        target=contracts.load_target()
        for name in ('server','frontend'):shutil.copytree(getattr(target,name),operation/name)
        previous=dict(directory=str(directory),profile='rc9',host='127.0.0.1',webPort=52345,pgPort=54321,
            database='synthetic',connection='Synthetic non-operational connection',
            dllSha256=target.expected['server']['RackClick.Server.dll'],bundleSha256='0'*64)
        selected=dict(previous,artifactDirectory=str(operation),bundleSha256=target.expected['frontend']['app.js'])
        preview=dict(selected,webPort=52347)
        for name,value in (('previous-config.json',previous),('selected-config.json',selected),('preview-config.json',preview)):
            updater.save(operation/name,value)
        record=dict(kind='artifact13-closed1089-to1209',directory=str(directory),operation=str(operation),
            sourceManifestSha256=contracts.SOURCE_SHA256,targetManifestSha256=sha256(contracts.TARGET_MANIFEST),targetArtifacts=target.expected,
            configurationHashes={n:sha256(operation/n) for n in ('previous-config.json','selected-config.json','preview-config.json')},
            sourceInputHashes={},databaseStates=dict(databases={role:dict(database=role,schema=schema,snapshot={n:{} for n in tables},history=[{}]*schema,identity='synthetic',grants='synthetic') for role,schema,tables in (('primary',13,contracts.TABLES13),('recovery969',12,contracts.TABLES12))},postgresqlRoles=''),pointerSha256='0'*64,activityBaseline={'xmax':'1','xip':[]})
        def seal():
            updater.save(operation/contracts.OPERATION,record)
            (operation/contracts.OPERATION_SEAL).write_text(sha256(operation/contracts.OPERATION)+'\n',encoding='ascii')
        seal()
        with patch.object(contracts,'original_metadata',return_value=SimpleNamespace(cfg=previous,database=SimpleNamespace(name='primary'),recovered=SimpleNamespace(name='recovery969'))),patch.object(contracts,'immutable_hashes',return_value={}):
            self.assertEqual(contracts.load_operation(directory,operation),record)
            # A sealed but altered connection remains forbidden.
            selected['connection']='A different synthetic connection';updater.save(operation/'selected-config.json',selected)
            record['configurationHashes']['selected-config.json']=sha256(operation/'selected-config.json');seal()
            with self.assertRaises(contracts.Artifact13Error):contracts.load_operation(directory,operation)

    def test_foreign_pg_does_not_become_owned_and_cli_has_no_rollback(self):
        runtime=updater.OwnedRuntime(ROOT,{'webPort':12345})
        with patch.object(updater,'app_stopped'),patch.object(updater,'pg_running',return_value=True),patch.object(updater,'start_private_pg') as start:
            with self.assertRaises(contracts.Artifact13Error):runtime.start_pg()
            runtime.stop();self.assertFalse(runtime.owned);start.assert_not_called()
        with patch.object(sys,'argv',['qa_artifact13_update1269.py','rollback']),patch.object(sys,'stderr',io.StringIO()):
            with self.assertRaises(SystemExit) as denied:updater.main()
            self.assertEqual(denied.exception.code,2)

    def test_uncertain_boundary_never_rewinds_configuration(self):
        directory=ROOT/'.local'/('guard1269-'+uuid.uuid4().hex);operation=directory/'version';operation.mkdir(parents=True)
        previous=b'{"synthetic":"previous"}\n';selected=b'{"synthetic":"selected"}\n'
        (operation/'previous-config.json').write_bytes(previous);(operation/'selected-config.json').write_bytes(selected)
        (directory/'manual-qa.json').write_bytes(selected)
        result=SimpleNamespace(source=SimpleNamespace(directory=directory),operation=operation)
        with patch.object(updater,'_verify_stopped',side_effect=contracts.Artifact13Error('candidate_activity_changed')):
            with self.assertRaises(contracts.Artifact13Error):updater._guarded_restore(result,{})
        self.assertEqual((directory/'manual-qa.json').read_bytes(),selected)

    def test_source_overlay_rejects_same_pointer_json_with_different_bytes(self):
        directory=ROOT/'.local/labs'/('manual-qa-rc9-schema13-'+uuid.uuid4().hex)
        home=directory/'artifact13-home';home.mkdir(parents=True)
        pointer=home/'current.json';updater.save(pointer,{'directory':str(directory)})
        original_pointer=pointer.read_bytes()
        operation=directory/'versions'/('artifact13-1209-'+uuid.uuid4().hex);operation.mkdir(parents=True)
        previous=dict(directory=str(directory),webPort=52345,pgPort=54321,bundleSha256='0'*64)
        selected=dict(previous,artifactDirectory=str(operation),bundleSha256='1'*64)
        updater.save(operation/'previous-config.json',previous);updater.save(operation/'selected-config.json',selected)
        updater.save(directory/'manual-qa.json',selected);updater.save(directory/'lab.json',{})
        original=SimpleNamespace(cfg=previous,database=object(),recovered=object(),recovery_cfg=previous)
        record={'pointerSha256':hashlib.sha256(original_pointer).hexdigest()}
        with patch.object(contracts,'original_metadata',return_value=original),patch.object(contracts,'load_operation',return_value=record),\
                patch.object(contracts,'immutable_hashes',return_value={}),patch.object(contracts,'app_stopped'):
            self.assertEqual(contracts.Source13(directory,pointer).revision,1209)
            pointer.write_text(json.dumps({'directory':str(directory)},separators=(',',':')),encoding='utf-8')
            self.assertEqual(json.loads(pointer.read_bytes()),json.loads(original_pointer))
            self.assertNotEqual(pointer.read_bytes(),original_pointer)
            with self.assertRaises(contracts.Artifact13Error) as denied:contracts.Source13(directory,pointer)
            self.assertEqual(denied.exception.code,'source13_pointer_bytes_changed')

class Native1269Acceptance(unittest.TestCase):
    outcomes=[]
    observations=[]

    def setUp(self):
        Native1149Acceptance.setUp(self)
        self.fixture1089=old_coordinator.prepare_operation(self.source_lab.directory,self.pointer).candidate
        self.candidate=self.fixture1089;self.addCleanup(self.fixture1089.close)
        self.source_lab=lab=self.fixture1089.lab;self.cfg=self.fixture1089.cfg;self.db=self.fixture1089.database
        home=lab.directory/'artifact13-home';home.mkdir();self.pointer=home/'current.json'
        updater.save(self.pointer,{'directory':str(lab.directory)});self.pointer_bytes=self.pointer.read_bytes()
        (lab.directory/'server.lock').write_bytes(b'0')
        self.original_prepared={n:(lab.directory/n).read_bytes() for n in ('category-colors13-prepared.json','category-colors13-prepared.sha256')}
        runtime=updater.OwnedRuntime(lab.directory,self.cfg);self.addCleanup(runtime.stop);runtime.start_pg()
        try:
            # Legitimate post1149 activity before the NEW operation boundary.
            lab.sql(self.db,"UPDATE systemhaus SET name='Legitimate1089 primary13 after1149'",sensitive=True)
            lab.sql(self.fixture1089.recovered,"UPDATE systemhaus SET name='Independent969 recovery12 after1149'",sensitive=True)
            server=lab.start_server(self.db,dll=lab.directory/'server/RackClick.Server.dll',frontend=lab.directory/'frontend')
            self.extra_servers.append(server);client=Client(server);client.cookie,client.csrf,actor=self.seed_session
            self.category_request=str(uuid.uuid4());self.category_body={'colors':{'Patch Panel↔Switch':'#3b82f6'}}
            reply=client.request('POST','/api/v1/me/category-colors',self.category_body,
                {'If-Match':'"category-colors-0"','Idempotency-Key':self.category_request,'X-RackClick-Actor':actor})
            self.assertEqual(reply.status,200);self.category_result=reply.json();server.close()
            # Before the first operation boundary, seed harmless but NONEMPTY
            # role-global, database-only and role+database runtime defaults.
            lab.sql('postgres',f"ALTER ROLE {self.db.runtime} SET idle_in_transaction_session_timeout='0';ALTER DATABASE {self.db.name} SET idle_in_transaction_session_timeout='0';ALTER ROLE {self.db.runtime} IN DATABASE {self.db.name} SET idle_in_transaction_session_timeout='0';ALTER ROLE {self.fixture1089.recovered.runtime} IN DATABASE {self.fixture1089.recovered.name} SET idle_in_transaction_session_timeout='0';",admin=True,sensitive=True)
            catalog=contracts.Source13(lab.directory,self.pointer)
            columns=catalog.admin_read("SELECT attname FROM pg_attribute WHERE attrelid='pg_catalog.pg_authid'::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum")
            self.assertNotIn('rolconfig',columns.splitlines())
            setting_columns=catalog.admin_read("SELECT attname FROM pg_attribute WHERE attrelid='pg_catalog.pg_db_role_setting'::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum")
            self.assertEqual(setting_columns.splitlines(),['setdatabase','setrole','setconfig'])
            settings=catalog.admin_read('SELECT row_to_json(t) FROM (SELECT setdatabase,setrole,setconfig FROM pg_db_role_setting ORDER BY setdatabase,setrole)t')
            setting_rows=[json.loads(line) for line in settings.splitlines()]
            self.assertGreaterEqual(len(setting_rows),4)
            self.assertTrue(any(int(row['setdatabase'])==0 and int(row['setrole'])!=0 for row in setting_rows))
            self.assertTrue(any(int(row['setdatabase'])!=0 and int(row['setrole'])==0 for row in setting_rows))
            self.assertTrue(any(int(row['setdatabase'])!=0 and int(row['setrole'])!=0 for row in setting_rows))
            updater.save(lab.directory/'artifact13-role-settings-seed-private.json',dict(localPg17CatalogConfirmed=True,settings=setting_rows,seededBeforeOperationBoundary=True))
        finally:runtime.stop()
        self.assertEqual({n:(lab.directory/n).read_bytes() for n in self.original_prepared},self.original_prepared)
        self.source=contracts.Source13(lab.directory,self.pointer)
        self.original_config=self.source.config_bytes

    def tearDown(self):Native1149Acceptance.tearDown(self)

    def test_same_cluster_update_quiet_rollback_success_idempotency_and_net_zero_guards(self):
        lab=self.source_lab
        # Profile lock prevents any allocation/control attempt.
        with profile_lock(self.pointer):
            with self.assertRaises(Exception) as denied:updater.update_operation(lab.directory,self.pointer)
        self.assertEqual(getattr(denied.exception,'code',None),'profile_busy')
        with patch.object(updater,'pg_running',return_value=True):
            with self.assertRaises(contracts.Artifact13Error):updater.update_operation(lab.directory,self.pointer)
        def fail_after_config(phase,result):
            if phase=='after_config':raise RuntimeError('synthetic quiet failure')
        with self.assertRaises(contracts.Artifact13Error) as quiet:
            updater.update_operation(lab.directory,self.pointer,hook=fail_after_config)
        self.assertEqual(quiet.exception.code,'rolled_back')
        self.assertEqual((lab.directory/'manual-qa.json').read_bytes(),self.original_config)
        self.assertEqual(self.pointer.read_bytes(),self.pointer_bytes)
        result=updater.update_operation(lab.directory,self.pointer)
        self.assertEqual(result.state,'committed');self.assertFalse(result.idempotent)
        operation=result.operation;record=contracts.load_operation(lab.directory,operation)
        seal_hash=sha256(operation/contracts.OPERATION_SEAL);record_bytes=(operation/contracts.OPERATION).read_bytes()
        selected=(lab.directory/'manual-qa.json').read_bytes();source=contracts.Source13(lab.directory,self.pointer)
        self.assertEqual(source.revision,1209)
        self.assertEqual((len(record['databaseStates']['databases']['primary']['snapshot']),len(record['databaseStates']['databases']['recovery969']['snapshot'])),(39,37))
        self.assertNotEqual(record['databaseStates']['databases']['primary']['snapshot']['systemhaus'],record['databaseStates']['databases']['recovery969']['snapshot']['systemhaus'])
        self.assertEqual(record['databaseStates']['databases']['primary']['snapshot']['user_category_colors']['rows'],1)
        recorded_settings=[json.loads(line) for line in record['databaseStates']['postgresqlRoles'].splitlines() if '"setconfig"' in line]
        self.assertGreaterEqual(len(recorded_settings),4)
        self.assertTrue(all(row['setconfig']==['idle_in_transaction_session_timeout=0'] for row in recorded_settings))
        self.assertEqual({k:v for k,v in json.loads(selected).items() if k not in ('artifactDirectory','bundleSha256')},
                         {k:v for k,v in json.loads(self.original_config).items() if k not in ('artifactDirectory','bundleSha256')})
        versions=set((lab.directory/'versions').iterdir())
        repeated=updater.update_operation(lab.directory,self.pointer)
        self.assertEqual(repeated.state,'committed');self.assertTrue(repeated.idempotent);self.assertEqual(repeated.operation,operation)
        self.assertEqual(set((lab.directory/'versions').iterdir()),versions)
        # Compatibility12 is observed on the separate existing recoveryDB only.
        runtime=updater.OwnedRuntime(lab.directory,self.cfg);runtime.start_pg()
        try:
            server=lab.start_server(self.fixture1089.recovered,
                dll=lab.directory/'versions/category-colors13-source969-recovery/server/RackClick.Server.dll',
                frontend=lab.directory/'versions/category-colors13-source969-recovery/frontend')
            self.extra_servers.append(server)
            self.assertEqual(server.request('GET','/health/ready').json(),{'status':'ready','schemaVersion':12})
            self.assertEqual(hashlib.sha256(server.request('GET','/app.js').body).hexdigest(),source.recovery_cfg['bundleSha256']);server.close()
            updater.verify_boundary(source,record,selected,operation)
        finally:runtime.stop()
        observations=[]
        for index,(role,db,cfg) in enumerate((('primary13',self.db,source.original_cfg),('recovery96912',self.fixture1089.recovered,source.recovery_cfg))):
            runtime.start_pg()
            try:
                before=source.database_states();xid_before=activity_watermark(lab.directory,cfg)
                house=lab.sql(db,'SELECT id FROM systemhaus',sensitive=True);identity=str(uuid.uuid4())
                lab.sql(db,f"BEGIN;INSERT INTO customer(id,systemhaus_id,name) VALUES('{identity}','{house}','Synthetic1269 compensated');DELETE FROM customer WHERE id='{identity}';COMMIT;",sensitive=True)
                self.assertEqual(source.database_states(),before)
                xid_after=activity_watermark(lab.directory,cfg);self.assertGreater(int(xid_after['xmax']),int(xid_before['xmax']))
                with self.assertRaises(Exception):require_unchanged_activity(lab.directory,cfg,record['activityBaseline'])
                with self.assertRaises(Exception):updater.verify_boundary(source,record,selected,operation)
                observations.append(dict(injectedRole=role,rowsHistoriesOidsGrantsExact=True,localActivityAdvanced=True,
                    operationGuardRejected=True,independentOfPriorActivity=index==0,globalWatermarkDoesNotAttributeDatabase=True))
            finally:runtime.stop()
            with self.assertRaises(contracts.Artifact13Error) as rejected:
                updater.update_operation(lab.directory,self.pointer)
            self.assertEqual(rejected.exception.code,'recovery_required')
            self.assertEqual((lab.directory/'manual-qa.json').read_bytes(),selected)
            self.assertEqual(self.pointer.read_bytes(),self.pointer_bytes)
            self.assertEqual((operation/contracts.OPERATION).read_bytes(),record_bytes)
            self.assertEqual(sha256(operation/contracts.OPERATION_SEAL),seal_hash)
        # Only after return is already prohibited: authenticate with the copied
        # existing session and replay the original13 receipt; no new login.
        runtime.start_pg()
        try:
            server=lab.start_server(self.db,dll=operation/'server/RackClick.Server.dll',frontend=operation/'frontend')
            self.extra_servers.append(server);client=Client(server);client.cookie,client.csrf,actor=self.seed_session
            self.assertEqual(client.request('GET','/api/v1/me').json()['user']['id'],actor)
            reply=client.request('POST','/api/v1/me/category-colors',self.category_body,
                {'If-Match':'"category-colors-0"','Idempotency-Key':self.category_request,'X-RackClick-Actor':actor})
            self.assertEqual(reply.status,200);self.assertEqual(reply.json(),self.category_result);server.close()
        finally:runtime.stop()
        self.assertEqual({n:(lab.directory/n).read_bytes() for n in self.original_prepared},self.original_prepared)
        contracts.Source13(lab.directory,self.pointer).unchanged()
        self.observations.append(dict(genuinePrepared1149Fixture=True,clusters=5,source39Recovery37=True,
            originalPrepared1149SealExact=True,post1149LegitimateDataAccepted=True,onlyTwoConfigFieldsChanged=True,
            sameDatabaseOidsHistoriesGrantsAndPrivateInputs=True,quietAfterConfigFailureRolledBack=True,
            committedSuccess=True,idempotentReentryWithoutNewBaseline=True,compatible13And12Startup=True,
            localPg17RoleCatalogConfirmed=True,nonemptyGlobalRoleDatabaseSettingsPreserved=True,
            originalSessionAndCategory13ReceiptRetained=True,compensatedActivity=observations,
            recoveryRoleSecondIsCumulative=True,independentRecoveryRollbackClaimed=False,
            baselineRenewals=0,migrationsOrNewDatabasesOrGrantsOrSecretRotation=False,actualQaAccessed=False))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--group',choices=('contracts','native','all'),default='all');args=p.parse_args()
    sys.stdout.reconfigure(encoding='utf-8',errors='backslashreplace');args.evidence.mkdir(parents=True,exist_ok=False)
    # Exact import chain frozen, including setup helpers; never a claim that
    # their historical test bodies/results were executed anew.
    sources=[ROOT/p for p in (
        'development/server/tests/pg_support.py',
        'development/server/tests/test_inventory_movement_gui.py',
        'development/server/tests/test_postgres.py',
        'development/server/tests/test_qa_artifact13_update1269.py',
        'development/server/tests/test_qa_category_colors13_update1149.py',
        'development/server/tests/test_qa_port_colors12_update1029.py',
        'development/server/tests/test_qa_relations11_update909.py',
        'development/server/tests/test_qa_xls11_update847.py',
        'development/toolchain.lock.json',
        'evidence/s1-20261018/sesenta-tandas-1030-1089/CANDIDATA1089-02.json',
        'evidence/s1-20261018/sesenta-tandas-1150-1209/CANDIDATA1209-01.json',
        'evidence/s1-20261018/sesenta-tandas-970-1029/CANDIDATA969-FIX02.json',
        'tools/windows/Qa-Local.py',
        'tools/windows/pg_lab_recovery.py',
        'tools/windows/qa_artifact13_source1269.py',
        'tools/windows/qa_artifact13_update1269.py',
        'tools/windows/qa_category_colors13_candidate1149.py',
        'tools/windows/qa_category_colors13_source1149.py',
        'tools/windows/qa_category_colors13_switch1149.py',
        'tools/windows/qa_category_colors13_update1149.py',
        'tools/windows/qa_port_colors12_candidate1029.py',
        'tools/windows/qa_port_colors12_source1029.py',
        'tools/windows/qa_port_colors12_switch1029.py',
        'tools/windows/qa_port_colors12_update1029.py',
        'tools/windows/qa_relations11_candidate909.py',
        'tools/windows/qa_relations11_source909.py',
        'tools/windows/qa_relations11_switch909.py',
        'tools/windows/qa_relations11_update909.py',
        'tools/windows/qa_schema11_candidate772.py',
        'tools/windows/qa_schema11_source772.py',
        'tools/windows/qa_schema11_switch772.py',
        'tools/windows/qa_schema11_update772.py',
        'tools/windows/qa_schema5_candidate.py',
        'tools/windows/qa_schema5_switch.py',
        'tools/windows/qa_schema6_real_candidate.py',
        'tools/windows/qa_schema6_source.py',
        'tools/windows/qa_schema_candidate.py',
        'tools/windows/qa_schema_switch.py',
        'tools/windows/qa_xls11_candidate847.py',
        'tools/windows/qa_xls11_source847.py',
        'tools/windows/qa_xls11_switch847.py',
        'tools/windows/qa_xls11_update847.py',
        'tools/windows/windows_job.py',
    )]
    sources=sorted(set(sources))
    def hashes():return {p.relative_to(ROOT).as_posix():sha256(p) for p in sources}
    before=hashes()
    for path in sources:
        dest=args.evidence/'sources'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    (args.evidence/'SOURCE-FREEZE.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
    suites=[]
    if args.group in ('contracts','all'):suites.append(unittest.defaultTestLoader.loadTestsFromTestCase(Closed1269Contracts))
    if args.group in ('native','all'):suites.append(unittest.defaultTestLoader.loadTestsFromTestCase(Native1269Acceptance))
    with (args.evidence/'tests.log').open('w',encoding='utf-8') as out:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,out),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(suites))
    data=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),group=args.group,testsRun=result.testsRun,
        successful=result.wasSuccessful(),cases=result.records,sourceHashes=before,inputsUnchanged=before==hashes(),
        labs=Native1269Acceptance.outcomes,observations=Native1269Acceptance.observations,actualQaAccessed=False)
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    return 0 if data['successful'] and data['inputsUnchanged'] and all(all(row.values()) for row in data['labs']) else 1

if __name__=='__main__':sys.exit(main())
