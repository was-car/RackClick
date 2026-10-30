"""Controlled stopped RC9 schema4 -> approved6/7 selection, same URL.

Fixtures first; real restored profile is explicit and requires coordinator GO.
Reuses unchanged, previously exercised native QA supervisor/Job Object lifecycle.
"""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'development/server/tests'))
from pg_support import free_port
from pg_lab_recovery import sha256
from qa_schema6_source import Source4, PRIVATE_FILES, SOURCE_MAP, artifact_manifest
from qa_schema6_real_candidate import prepare, load_target, save
from qa_schema_candidate import snapshot
from qa_schema5_candidate import checked_path
from qa_schema5_switch import atomic_bytes
from qa_schema_switch import (profile_lock, qa_module, start_supervisor, stop_application,
    pg_running, read_owner, activity_watermark, require_unchanged_activity)
import uuid


class RealSwitchError(RuntimeError):
    def __init__(self,code,result=None):
        super().__init__(code);self.code,self.result=code,result


@dataclass
class Result:
    source:object
    candidate:object
    journal:Path
    state:str='validated'


def candidate_inputs(candidate):
    directory=candidate.lab.directory
    candidate.validate_artifacts()
    cfg=json.loads(checked_path(directory/'manual-qa.json').read_text(encoding='utf-8'))
    if cfg!=candidate.cfg:raise RealSwitchError('candidate_config_changed')
    paths=[directory/'manual-qa.json',directory/'lab.json',candidate.journal]
    for db in (candidate.database,candidate.recovered):paths += [db.directory/'credentials.json',db.directory/'owner.pgpass']
    paths += [directory/n for n in PRIVATE_FILES]
    return {p.relative_to(directory).as_posix():sha256(checked_path(p)) for p in paths}


def switch(directory,pointer,target,*,real=False,hook=None,leave_running=True):
    initial=Source4(directory,pointer,real=real)
    # Never stop an application or PG instance that was already active.
    if initial.pg_running():raise RealSwitchError('source_pg_already_active')
    target.validate()
    with profile_lock(initial.pointer):
        source=Source4(directory,pointer,real=real)
        if source.hashes!=initial.hashes or source.pointer_bytes!=initial.pointer_bytes:
            raise RealSwitchError('source_changed_before_lock')
        if source.pg_running():raise RealSwitchError('source_pg_already_active')
        journal=source.directory/('schema6-switch-'+uuid.uuid4().hex+'.json')
        result=Result(source,None,journal)
        state=dict(state='validated',sourceSchema=4,targetSchema=target.schema,activated=False,
            sourcePointerSha256=sha256(source.pointer),sourceInputHashes=source.hashes,
            targetManifestSha256=sha256(target.manifest_path),originalRunning=False)
        candidate=None;source_pg_owned=False;swapped=False;selected=None;baseline=None;inputs=None;prepared_rows=None;candidate_cfg_bytes=None
        def checkpoint(name):
            result.state=state['state']=name;save(journal,state)
            if hook:hook(name,result)
        def stop_owned_source():
            nonlocal source_pg_owned
            if source_pg_owned:
                if pg_running(source.directory):qa_module().control(source.directory,'stop')
                if pg_running(source.directory):raise RealSwitchError('source_pg_stop_unconfirmed')
                source_pg_owned=False
        try:
            checkpoint('validated')
            # Ownership begins BEFORE launch: pg_ctl may start PG and then fail
            # or time out. Its return code alone cannot prove that PG is absent.
            source_pg_owned=True
            qa_module().control(source.directory,'start')
            candidate=result.candidate=prepare(source,target)
            state['candidateDirectory']=str(candidate.lab.directory)
            prepared_rows=json.loads(candidate.journal.read_text(encoding='utf-8'))['candidateSnapshot']
            inputs=candidate_inputs(candidate);candidate_cfg_bytes=(candidate.lab.directory/'manual-qa.json').read_bytes()
            candidate.close()
            stop_owned_source()
            qa_module().control(candidate.lab.directory,'start')
            try:baseline=activity_watermark(candidate.lab.directory,candidate.cfg)
            finally:qa_module().control(candidate.lab.directory,'stop')
            state['activityBaseline']=baseline;checkpoint('prepared')
            temp=dict(candidate.cfg,webPort=free_port())
            while temp['webPort'] in (source.cfg['webPort'],source.cfg['pgPort'],candidate.cfg['pgPort']):temp['webPort']=free_port()
            save(candidate.lab.directory/'manual-qa.json',temp)
            try:
                process=start_supervisor(candidate.lab.directory,temp)
                stop_application(candidate.lab.directory,temp);process.wait(timeout=30)
            finally:atomic_bytes(candidate.lab.directory/'manual-qa.json',candidate_cfg_bytes)
            qa_module().control(candidate.lab.directory,'start')
            try:
                require_unchanged_activity(candidate.lab.directory,candidate.cfg,baseline)
                if snapshot(lambda q:read_owner(candidate.lab.directory,candidate.cfg,q))!=prepared_rows:
                    raise RealSwitchError('candidate_changed_before_selection')
                require_unchanged_activity(candidate.lab.directory,candidate.cfg,baseline)
            finally:qa_module().control(candidate.lab.directory,'stop')
            source.unchanged();target.validate()
            if candidate_inputs(candidate)!=inputs:raise RealSwitchError('candidate_inputs_changed')
            checkpoint('before_pointer')
            source.unchanged()
            selected=(json.dumps({'directory':str(candidate.lab.directory)})+'\n').encode('utf-8')
            atomic_bytes(source.pointer,selected);swapped=True;checkpoint('after_pointer')
            process=start_supervisor(candidate.lab.directory,candidate.cfg)
            checkpoint('after_start')
            if not qa_module().ready(candidate.lab.directory,candidate.cfg):raise RealSwitchError('candidate_readiness_unconfirmed')
            if candidate_inputs(candidate)!=inputs or source.pointer.read_bytes()!=selected:
                raise RealSwitchError('candidate_or_pointer_changed_after_start')
            require_unchanged_activity(candidate.lab.directory,candidate.cfg,baseline)
            if not leave_running:
                stop_application(candidate.lab.directory,candidate.cfg);process.wait(timeout=30)
            state['activated']=True;state['leftRunning']=leave_running;checkpoint('committed');return result
        except Exception as error:
            state['failureCode']=getattr(error,'code','copy_or_internal_failure')
            if candidate is None and getattr(error,'candidate',None) is not None:
                candidate=result.candidate=error.candidate
                state['candidateDirectory']=str(candidate.lab.directory)
            recovered=False;candidate_quiet=candidate is None
            try:
                if candidate:
                    if candidate.cfg is None or inputs is None:
                        candidate.close()
                        if pg_running(candidate.lab.directory):raise RealSwitchError('unfinished_copy_stop_unconfirmed')
                    else:
                        stop_application(candidate.lab.directory,candidate.cfg)
                        if inputs is None or candidate_inputs(candidate)!=inputs:raise RealSwitchError('candidate_recovery_identity_changed')
                        qa_module().control(candidate.lab.directory,'start')
                        try:
                            require_unchanged_activity(candidate.lab.directory,candidate.cfg,baseline)
                            if prepared_rows is None or snapshot(lambda q:read_owner(candidate.lab.directory,candidate.cfg,q))!=prepared_rows:
                                raise RealSwitchError('candidate_later_rows')
                            require_unchanged_activity(candidate.lab.directory,candidate.cfg,baseline)
                        finally:qa_module().control(candidate.lab.directory,'stop')
                    candidate_quiet=True
                if source_pg_owned:
                    stop_owned_source()
                if pg_running(source.directory):raise RealSwitchError('source_pg_not_quiet_for_recovery')
                source.unchanged(pointer=False)
                if source.pointer.read_bytes()!=(selected if swapped else source.pointer_bytes):
                    raise RealSwitchError('pointer_recovery_identity_changed')
                if swapped:atomic_bytes(source.pointer,source.pointer_bytes)
                recovered=True
            except Exception as blocker:
                state['recoveryBlocker']=getattr(blocker,'code','recovery_verification_uncertain')
                if source_pg_owned:
                    try:stop_owned_source()
                    except Exception:pass
            source_quiet_final=False
            try:source_quiet_final=not pg_running(source.directory)
            except Exception:pass
            if not source_quiet_final or source_pg_owned:recovered=False
            state['activated']=False;state['candidateStopConfirmed']=candidate_quiet
            state['sourcePgStopConfirmed']=source_quiet_final and not source_pg_owned
            result.state=state['state']='rolled_back' if recovered else 'recovery_required'
            try:state['observedPointerSha256']=sha256(checked_path(source.pointer));save(journal,state)
            except Exception:raise RealSwitchError('recovery_journal_unconfirmed',result) from None
            raise RealSwitchError(result.state,result) from None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--pointer',type=Path,required=True)
    parser.add_argument('--target-schema',type=int,choices=(6,7),required=True)
    parser.add_argument('--real-restored',action='store_true');parser.add_argument('--leave-stopped',action='store_true')
    args=parser.parse_args()
    try:
        result=switch(args.source,args.pointer,load_target(args.target_schema),real=args.real_restored,leave_running=not args.leave_stopped)
        print(json.dumps({'state':result.state,'targetSchema':args.target_schema,'leftRunning':not args.leave_stopped,'sourcePreserved':True}))
        return 0
    except Exception as error:
        print(json.dumps({'state':getattr(error,'code','source_validation_failed'),'activated':False}),file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
