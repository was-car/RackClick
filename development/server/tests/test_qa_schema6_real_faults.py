"""58: bounded negative acceptance of real-shape RC9 fixtures, not real QA."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import platform
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/windows'))
from pg_support import Lab
from pg_lab_recovery import sha256
from qa_schema6_source import Source4,SourceError
from qa_schema6_real_candidate import load_target
import qa_schema6_real_switch as coordinator
from qa_schema_candidate import snapshot
from test_qa_schema6_real import RealAdapterFixture
from test_postgres import EvidenceResult,Tee


class RealAdapterFaults(RealAdapterFixture):
    observations=[]

    def test_58_cluster_binding_lock_failures_and_compensated_dml(self):
        # A real second cluster with its own credentials must not pass a source
        # claim merely because the SQL connection points to that other port.
        foreign=Lab('schema6-foreign-identity').start()
        paths=[self.config,self.lab.directory/'lab.json',self.db.directory/'owner.pgpass',self.lab.directory/'admin.pgpass']
        original={p:p.read_bytes() for p in paths}
        try:
            cfg=dict(self.cfg,pgPort=foreign.port,connection=self.db.connection(foreign.port))
            self.config.write_text(json.dumps(cfg),encoding='utf-8')
            meta=json.loads(original[self.lab.directory/'lab.json']);meta['port']=foreign.port
            (self.lab.directory/'lab.json').write_text(json.dumps(meta),encoding='utf-8')
            (self.db.directory/'owner.pgpass').write_text(f'127.0.0.1:{foreign.port}:{self.db.name}:{self.db.owner}:{self.db.owner_password}\n',encoding='utf-8')
            (self.lab.directory/'admin.pgpass').write_text(f'127.0.0.1:{foreign.port}:*:rc_lab_admin:{foreign.admin_password}\n',encoding='utf-8')
            false_source=Source4(self.lab.directory,self.pointer)
            with self.assertRaises(SourceError) as caught:false_source.check_cluster_identity()
            self.assertEqual(str(caught.exception),'source_sql_cluster_directory_differs')
        finally:
            for path,content in original.items():path.write_bytes(content)
            foreign.close()
            self.outcomes.append({'sourceStopped':not foreign.running,'serversStopped':True,'foreignFixture':True})
        self.source.unchanged();self.source.check_cluster_identity();self.lab.close()
        pointer_bytes=self.pointer.read_bytes()
        # Real own-cluster start followed by a synthetic control error reproduces
        # an uncertain pg_ctl outcome without another copy or any QA operation.
        qa=coordinator.qa_module();real_control=qa.control
        def uncertain_start(directory,action):
            result=real_control(directory,action)
            if directory==self.lab.directory and action=='start':
                raise RuntimeError('Synthetic pg_ctl failure after own PG really started')
            return result
        with patch.object(coordinator,'qa_module',return_value=qa),patch.object(qa,'control',side_effect=uncertain_start):
            with self.assertRaises(coordinator.RealSwitchError) as uncertain:self.select()
        self.assertEqual(uncertain.exception.code,'rolled_back')
        self.assertIsNone(uncertain.exception.result.candidate)
        self.assertFalse(coordinator.pg_running(self.lab.directory))
        self.assertTrue(json.loads(uncertain.exception.result.journal.read_text())['sourcePgStopConfirmed'])
        self.assertEqual(self.pointer.read_bytes(),pointer_bytes)
        with coordinator.profile_lock(self.pointer):
            with self.assertRaises(Exception) as caught:coordinator.switch(self.lab.directory,self.pointer,load_target(self.target_schema))
        self.assertEqual(getattr(caught.exception,'code',None),'profile_busy')
        self.assertEqual(self.pointer.read_bytes(),pointer_bytes)
        retained=[]
        for stage in ('before_pointer','after_pointer'):
            def fail(name,result):
                if name==stage:raise RuntimeError('Synthetic no-write switch failure')
            with self.assertRaises(coordinator.RealSwitchError) as caught:self.select(hook=fail)
            self.assertEqual(caught.exception.code,'rolled_back')
            self.assertEqual(self.pointer.read_bytes(),pointer_bytes)
            candidate=caught.exception.result.candidate;retained.append(candidate)
            self.assertFalse(coordinator.pg_running(candidate.lab.directory))
            self.assertFalse(coordinator.qa_module().running(candidate.lab.directory))
            self.assertFalse(coordinator.pg_running(self.lab.directory))
        observed={}
        def compensate(name,result):
            if name=='after_start':
                candidate=result.candidate;lab,db=candidate.lab,candidate.database
                before=snapshot(lambda q:coordinator.read_owner(lab.directory,candidate.cfg,q))
                house=coordinator.read_owner(lab.directory,candidate.cfg,'SELECT id FROM systemhaus');new=str(uuid.uuid4())
                lab.sql(db,f"BEGIN;INSERT INTO customer(id,systemhaus_id,name) VALUES('{new}','{house}','net-zero58');DELETE FROM customer WHERE id='{new}';COMMIT;",sensitive=True)
                self.assertEqual(before,snapshot(lambda q:coordinator.read_owner(lab.directory,candidate.cfg,q)))
                reference=json.loads(result.journal.read_text())['activityBaseline']
                now=coordinator.activity_watermark(lab.directory,candidate.cfg)
                self.assertGreater(int(now['xmax']),int(reference['xmax']))
                observed.update(allRowsEqual=True,activityAdvanced=True)
                raise RuntimeError('Synthetic post-start failure after net-zero committed DML')
        with self.assertRaises(coordinator.RealSwitchError) as caught:self.select(hook=compensate)
        self.assertEqual(caught.exception.code,'recovery_required')
        candidate=caught.exception.result.candidate;retained.append(candidate)
        self.assertEqual(json.loads(self.pointer.read_text())['directory'],str(candidate.lab.directory))
        self.assertFalse(coordinator.pg_running(candidate.lab.directory));self.assertFalse(coordinator.qa_module().running(candidate.lab.directory))
        self.assertFalse(coordinator.pg_running(self.lab.directory))
        pointer_after=self.pointer.read_bytes()
        with patch('qa_schema_switch.read_owner',side_effect=RuntimeError('Synthetic uncertain read')):
            with self.assertRaises(Exception):coordinator.activity_watermark(candidate.lab.directory,candidate.cfg)
        with self.assertRaises(Exception):coordinator.require_unchanged_activity(candidate.lab.directory,candidate.cfg,None)
        self.assertEqual(self.pointer.read_bytes(),pointer_after)
        coordinator.qa_module().control(self.lab.directory,'start')
        try:self.assertEqual(snapshot(self.source.sql),self.before);self.source.check_schema()
        finally:coordinator.qa_module().control(self.lab.directory,'stop')
        self.assertTrue(all(c.lab.directory.is_dir() for c in retained))
        self.observations.append({'sourceClusterBindingNegative':True,'sameProfileBusyRejected':True,
            'uncertainOwnSourceStartStoppedAndVerified':True,
            'noWriteStagesRolledBack':['before_pointer','after_pointer'],**observed,'rollbackDenied':True,
            'uncertaintyHelperNegatives':True,'allBranchesRetained':True})


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--target-schema',type=int,choices=(6,7),default=6)
    parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=False)
    files=[Path(__file__).resolve(),ROOT/'development/server/tests/test_qa_schema6_real.py']+[ROOT/'tools/windows'/f for f in
        ['qa_schema6_source.py','qa_schema6_real_candidate.py','qa_schema6_real_switch.py','qa_schema_switch.py','Qa-Local.py','windows_job.py']]
    def hashes():return {p.relative_to(ROOT).as_posix():sha256(p) for p in files}
    before=hashes();target=load_target(args.target_schema);RealAdapterFaults.target_schema=args.target_schema
    data={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'sourceHashes':before,
        'targetSchema':args.target_schema,'targetManifestSha256':sha256(target.manifest_path),'actualQaAccessed':False}
    with (args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(
            unittest.TestSuite([RealAdapterFaults('test_58_cluster_binding_lock_failures_and_compensated_dml')]))
    data.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful(),labs=RealAdapterFaults.outcomes,
        observations=RealAdapterFaults.observations,inputsUnchanged=before==hashes(),frozenTargetUnchanged=target.validate()==target.expected)
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    return 0 if data['successful'] and data['inputsUnchanged'] and all(v['sourceStopped'] and v['serversStopped'] and v.get('nativeStopped',True) for v in data['labs']) else 1


if __name__=='__main__':sys.exit(main())
