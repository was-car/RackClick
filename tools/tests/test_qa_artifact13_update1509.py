"""1509: four contracts and one fresh genuine1149 ->1209 ->1329 chain.

Historical setup helpers only; no historical case is rerun or relabelled.
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
import unittest
from unittest.mock import patch
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'development/server/tests'))
sys.path.insert(0,str(ROOT/'tools/tests'))
sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Client
from pg_lab_recovery import sha256
from test_postgres import EvidenceResult,Tee
from test_qa_artifact13_update1389 import Native1389Acceptance,contract_chain as historical_chain,synthetic_metadata
import qa_artifact13_update1389 as historical_updater
import qa_artifact13_source1509 as contracts
import qa_artifact13_update1509 as updater
from qa_schema_switch import profile_lock,activity_watermark,require_unchanged_activity

def seal(operation,record):
    updater.save(operation/contracts.OPERATION,record)
    (operation/contracts.OPERATION_SEAL).write_text(sha256(operation/contracts.OPERATION)+'\n',encoding='ascii')

def contract_chain():
    """Extend the declared synthetic1149/1209 archive with a sealed1329 parent."""
    c=historical_chain();ancestor=c.parent
    parent=c.directory/'versions'/('artifact13-1329-'+uuid.uuid4().hex)
    record,selected=c.stage(parent,c.parent_cfg,contracts.chain.load_target(),contracts.chain.SOURCE_SHA256,'artifact13-closed1209-to1329',dict(
        parentOperation=str(ancestor),parentBindings=contracts.chain.parent_bindings(c.directory,ancestor),sourceInputHashes=contracts.chain.inventory(c.original)))
    updater.save(contracts.chain.owned_paths(c.directory,parent)['journal'],dict(state='committed',leftRunning=False,applicationStopConfirmed=True,postgresqlStopConfirmed=True))
    updater.save(c.directory/'manual-qa.json',selected)
    c.ancestor=ancestor;c.parent=parent;c.parent_record=record;c.parent_cfg=selected
    return c


class Closed1509Contracts(unittest.TestCase):
    def test_pins_and_exact_server_only_appjs_change(self):
        target=contracts.load_target();source=contracts.chain.load_target()
        self.assertEqual((target.revision,target.schema),(1449,13));self.assertEqual(target.expected['server'],source.expected['server'])
        self.assertEqual((len(target.expected['server']),len(target.expected['frontend'])),(22,18))
        self.assertNotEqual(target.expected['frontend']['app.js'],source.expected['frontend']['app.js'])
        for pin in (None,('elsewhere','0'*64),['invalid']):
            with patch.object(contracts,'TARGET1509',pin):
                with self.assertRaises(contracts.Artifact13Error):contracts.load_target()

    def test_exact_45_entries_and_no_unknown_empty_version(self):
        c=contract_chain();contracts.validate_parents(c.original,c.parent)
        (c.parent/'unexpected-empty').mkdir()
        with self.assertRaises(contracts.Artifact13Error) as denied:contracts.validate_parents(c.original,c.parent)
        self.assertEqual(denied.exception.code,'operation1389_entry_set_changed')
        (c.parent/'unexpected-empty').rmdir();(c.directory/'versions/unknown-empty').mkdir()
        with self.assertRaises(contracts.Artifact13Error) as denied:contracts.validate_parents(c.original,c.parent)
        self.assertEqual(denied.exception.code,'source1329_version_set_changed')

    def test_parent_and_pointer_bytes_and_two_fields_are_bound(self):
        c=contract_chain()
        with synthetic_metadata(c):
            source=contracts.Source1329(c.directory,c.pointer);source.unchanged()
            c.pointer.write_text(json.dumps({'directory':str(c.directory)},separators=(',',':')),encoding='utf-8')
            with self.assertRaises(contracts.Artifact13Error):contracts.Source1329(c.directory,c.pointer)
            c.pointer.write_bytes(source.pointer_bytes)
            selected=dict(c.parent_cfg,connection='different synthetic connection');updater.save(c.parent/'selected-config.json',selected)
            c.parent_record['configurationHashes']['selected-config.json']=sha256(c.parent/'selected-config.json');seal(c.parent,c.parent_record)
            with self.assertRaises(contracts.Artifact13Error) as denied:contracts.validate_parents(c.original,c.parent)
            self.assertEqual(denied.exception.code,'operation1389_only_two_config_fields_allowed')

    def test_one_explicit_descendant_and_uncertain_restore_never_rewinds(self):
        c=contract_chain();parent,bindings=contracts.validate_parents(c.original,c.parent)
        op=c.directory/'versions'/('artifact13-1449-'+uuid.uuid4().hex)
        record,selected=c.stage(op,c.parent_cfg,contracts.load_target(),contracts.SOURCE_SHA256,'artifact13-closed1329-to1449',dict(
            parentOperation=str(c.parent),parentBindings=bindings,sourceInputHashes=contracts.inventory(c.original)))
        contracts.validate_parents(c.original,c.parent,op);self.assertEqual(contracts.load_operation(c.original,op,c.parent,parent,bindings),record)
        with self.assertRaises(contracts.Artifact13Error):contracts.validate_parents(c.original,c.parent)
        updater.save(c.directory/'manual-qa.json',selected)
        with synthetic_metadata(c):
            source=contracts.Source1329(c.directory,c.pointer);source.unchanged()
            result=updater.Result1509(source,op,contracts.owned_paths(c.directory,op)['journal'])
            with patch.object(updater,'_verify_stopped',side_effect=contracts.Artifact13Error('activity_changed')):
                with self.assertRaises(contracts.Artifact13Error):updater._guarded_restore(result,record)
            self.assertEqual((c.directory/'manual-qa.json').read_bytes(),contracts.config_bytes(selected))
        runtime=updater.OwnedRuntime(c.directory,c.parent_cfg,op)
        with patch.object(updater.base,'app_stopped'),patch.object(updater.base,'pg_running',return_value=True),patch.object(updater,'start_private_pg') as start:
            with self.assertRaises(contracts.Artifact13Error):runtime.start_pg()
            runtime.stop();start.assert_not_called();self.assertFalse(runtime.owned)
        with patch.object(sys,'argv',['qa_artifact13_update1509.py','rollback']),patch.object(sys,'stderr',io.StringIO()):
            with self.assertRaises(SystemExit) as denied:updater.main()
            self.assertEqual(denied.exception.code,2)

class Native1509Acceptance(unittest.TestCase):
    outcomes=[]
    observations=[]

    def setUp(self):
        # Helpers only: genuine1149 -> initial1209; no historical case body.
        Native1389Acceptance.setUp(self)
        lab=self.source_lab
        self.fixture1329_result=historical_updater.update_operation(lab.directory,self.pointer)
        self.assertEqual(self.fixture1329_result.state,'committed')
        self.cfg=json.loads((lab.directory/'manual-qa.json').read_bytes())
        self.parent_proof.update({str(p.relative_to(lab.directory)):p.read_bytes() for p in self.fixture1329_result.operation.rglob('*') if p.is_file()})
        self.parent_proof[self.fixture1329_result.journal.name]=self.fixture1329_result.journal.read_bytes()
        # Legitimate post1329 changes precede the single new1509 baseline.
        runtime=historical_updater.OwnedRuntime(lab.directory,self.cfg,self.fixture1329_result.operation);runtime.start_pg()
        try:
            lab.sql(self.db,"UPDATE systemhaus SET name='Current1329 primary13 before1509'",sensitive=True)
            lab.sql(self.fixture1089.recovered,"UPDATE systemhaus SET name='Independent969 recovery12 before1509'",sensitive=True)
        finally:runtime.stop()
        self.source=contracts.Source1329(lab.directory,self.pointer);self.original_config=self.source.config_bytes

    def tearDown(self):Native1389Acceptance.tearDown(self)

    def test_chain_quiet_return_same_operation_resume_commit_and_cumulative_activity(self):
        lab=self.source_lab
        with profile_lock(self.pointer):
            with self.assertRaises(Exception) as denied:updater.update_operation(lab.directory,self.pointer)
        self.assertEqual(getattr(denied.exception,'code',None),'profile_busy')
        def fail_after_config(phase,result):
            if phase=='after_config':raise RuntimeError('synthetic quiet1509 failure')
        with self.assertRaises(contracts.Artifact13Error) as quiet:updater.update_operation(lab.directory,self.pointer,hook=fail_after_config)
        self.assertEqual(quiet.exception.code,'rolled_back');op=quiet.exception.result.operation
        self.assertEqual((lab.directory/'manual-qa.json').read_bytes(),self.original_config)
        record_bytes=(op/contracts.OPERATION).read_bytes();seal_bytes=(op/contracts.OPERATION_SEAL).read_bytes()
        versions=set((lab.directory/'versions').iterdir())
        # No implicit discovery: same explicit operation is required after rollback.
        with self.assertRaises(contracts.Artifact13Error):contracts.Source1329(lab.directory,self.pointer)
        source=updater.validate_operation(lab.directory,self.pointer,operation=op)
        self.assertEqual(source.revision,1329)
        result=updater.update_operation(lab.directory,self.pointer,operation=op)
        self.assertEqual(result.state,'committed');self.assertEqual(result.operation,op);self.assertFalse(result.idempotent)
        selected=(lab.directory/'manual-qa.json').read_bytes();source=contracts.Source1329(lab.directory,self.pointer)
        self.assertEqual(source.revision,1449);record=source.record
        self.assertEqual((op/contracts.OPERATION).read_bytes(),record_bytes);self.assertEqual((op/contracts.OPERATION_SEAL).read_bytes(),seal_bytes)
        self.assertEqual(set((lab.directory/'versions').iterdir()),versions)
        self.assertEqual({k:v for k,v in json.loads(selected).items() if k not in ('artifactDirectory','bundleSha256')},
            {k:v for k,v in json.loads(self.original_config).items() if k not in ('artifactDirectory','bundleSha256')})
        repeated=updater.update_operation(lab.directory,self.pointer)
        self.assertTrue(repeated.idempotent);self.assertEqual(repeated.operation,op)
        self.assertEqual((len(record['databaseStates']['databases']['primary']['snapshot']),len(record['databaseStates']['databases']['recovery969']['snapshot'])),(39,37))
        self.assertNotEqual(record['databaseStates']['databases']['primary']['snapshot']['systemhaus'],record['databaseStates']['databases']['recovery969']['snapshot']['systemhaus'])
        self.assertNotEqual(record['databaseStates']['databases']['primary']['snapshot']['systemhaus'],source.parent_record['databaseStates']['databases']['primary']['snapshot']['systemhaus'])
        self.assertGreaterEqual(len([line for line in record['databaseStates']['postgresqlRoles'].splitlines() if '"setconfig"' in line]),4)
        runtime=updater.OwnedRuntime(lab.directory,source.cfg,op);runtime.start_pg()
        try:
            server=lab.start_server(self.fixture1089.recovered,dll=lab.directory/'versions/category-colors13-source969-recovery/server/RackClick.Server.dll',frontend=lab.directory/'versions/category-colors13-source969-recovery/frontend')
            self.extra_servers.append(server)
            self.assertEqual(server.request('GET','/health/ready').json(),{'status':'ready','schemaVersion':12})
            self.assertEqual(hashlib.sha256(server.request('GET','/app.js').body).hexdigest(),source.recovery_cfg['bundleSha256']);server.close()
            updater.verify_boundary(source,record,selected,op)
        finally:runtime.stop()
        observations=[]
        for index,(role,db,cfg) in enumerate((('primary13',self.db,source.original_cfg),('recovery96912',self.fixture1089.recovered,source.recovery_cfg))):
            runtime.start_pg()
            try:
                before=source.database_states();watermark=activity_watermark(lab.directory,cfg)
                house=lab.sql(db,'SELECT id FROM systemhaus',sensitive=True);identity=str(uuid.uuid4())
                lab.sql(db,f"BEGIN;INSERT INTO customer(id,systemhaus_id,name) VALUES('{identity}','{house}','Synthetic1509 compensated');DELETE FROM customer WHERE id='{identity}';COMMIT;",sensitive=True)
                self.assertEqual(source.database_states(),before)
                self.assertGreater(int(activity_watermark(lab.directory,cfg)['xmax']),int(watermark['xmax']))
                with self.assertRaises(Exception):require_unchanged_activity(lab.directory,cfg,record['activityBaseline'])
                with self.assertRaises(Exception):updater.verify_boundary(source,record,selected,op)
                observations.append(dict(injectedRole=role,rowsHistoriesOidsGrantsSettingsExact=True,localActivityAdvanced=True,directGuardRejected=True,independentOfPriorActivity=index==0,globalWatermarkDoesNotAttributeDatabase=True))
            finally:runtime.stop()
            with self.assertRaises(contracts.Artifact13Error) as denied:updater.update_operation(lab.directory,self.pointer,operation=op)
            self.assertEqual(denied.exception.code,'recovery_required')
            self.assertEqual((lab.directory/'manual-qa.json').read_bytes(),selected);self.assertEqual(self.pointer.read_bytes(),self.pointer_bytes)
            self.assertEqual((op/contracts.OPERATION).read_bytes(),record_bytes);self.assertEqual((op/contracts.OPERATION_SEAL).read_bytes(),seal_bytes)
        runtime.start_pg()
        try:
            server=lab.start_server(self.db,dll=op/'server/RackClick.Server.dll',frontend=op/'frontend');self.extra_servers.append(server)
            client=Client(server);client.cookie,client.csrf,actor=self.seed_session
            self.assertEqual(client.request('GET','/api/v1/me').json()['user']['id'],actor)
            reply=client.request('POST','/api/v1/me/category-colors',self.category_body,{'If-Match':'"category-colors-0"','Idempotency-Key':self.category_request,'X-RackClick-Actor':actor})
            self.assertEqual(reply.status,200);self.assertEqual(reply.json(),self.category_result);server.close()
        finally:runtime.stop()
        self.assertEqual({n:(lab.directory/n).read_bytes() for n in self.parent_proof},self.parent_proof)
        self.assertEqual({n:(lab.directory/n).read_bytes() for n in self.original_prepared},self.original_prepared)
        source.unchanged()
        self.observations.append(dict(genuinePrepared1149Then1209Then1329=True,clusters=5,stagesExactly45Files=True,source39Recovery37=True,
            parent1329AndPrepared1149BytesExact=True,post1329LegitimateActivityAccepted=True,quietAfterConfigReturn=True,
            sameExplicitOperationResumedWithoutNewBaseline=True,committed1449=True,idempotentReentry=True,
            sameRootPointerOidsDataRolesSettingsAndPrivateInputs=True,onlyTwoConfigFieldsChanged=True,
            compatible13And12ReadinessAndAppjs=True,originalSessionAndReceiptPreserved=True,
            compensatedActivity=observations,recoveryRoleSecondIsCumulative=True,independentRollbackPerDatabaseClaimed=False,
            baselineRenewals=0,newDatabasesMigrationsGrantsOrSecretRotation=False,actualQaAccessed=False))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--group',choices=('contracts','native','all'),default='all');args=p.parse_args()
    sys.stdout.reconfigure(encoding='utf-8',errors='backslashreplace');args.evidence.mkdir(parents=True,exist_ok=False)
    # Fixed import-chain receipt, not discovery of QA profiles or test cases.
    receipt=ROOT/'evidence/s1-20261018/sesenta-tandas-1330-1389/qa-update/run01/SOURCE-FREEZE.json'
    sources=[ROOT/name for name in json.loads(receipt.read_bytes())]
    sources+= [Path(__file__).resolve(),ROOT/'tools/windows/qa_artifact13_source1509.py',ROOT/'tools/windows/qa_artifact13_update1509.py',contracts.TARGET_MANIFEST]
    sources=sorted(set(sources))
    def hashes():return {p.relative_to(ROOT).as_posix():sha256(p) for p in sources}
    before=hashes()
    for path in sources:
        dest=args.evidence/'sources'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    (args.evidence/'SOURCE-FREEZE.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
    suites=[]
    if args.group in ('contracts','all'):suites.append(unittest.defaultTestLoader.loadTestsFromTestCase(Closed1509Contracts))
    if args.group in ('native','all'):suites.append(unittest.defaultTestLoader.loadTestsFromTestCase(Native1509Acceptance))
    with (args.evidence/'tests.log').open('w',encoding='utf-8') as out:result=unittest.TextTestRunner(stream=Tee(sys.stdout,out),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(suites))
    data=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),group=args.group,testsRun=result.testsRun,
        successful=result.wasSuccessful(),cases=result.records,sourceHashes=before,inputsUnchanged=before==hashes(),
        labs=Native1509Acceptance.outcomes,observations=Native1509Acceptance.observations,actualQaAccessed=False)
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    return 0 if data['successful'] and data['inputsUnchanged'] and all(all(row.values()) for row in data['labs']) else 1

if __name__=='__main__':sys.exit(main())
