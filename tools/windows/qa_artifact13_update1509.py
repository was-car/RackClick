"""One explicit1329 ->1449 operation; immutable baseline and guarded in-scope return."""
import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

import qa_artifact13_update1269 as base
import qa_artifact13_source1509 as contracts
from qa_artifact13_source1509 import (ROOT,Artifact13Error,Source1329,load_target,checked_operation,checked_path,
    owned_paths,OPERATION,OPERATION_SEAL,sha256,config_bytes)

save=base.save

@dataclass
class Result1509:
    source:object
    operation:Path
    journal:Path
    state:str='validated'
    idempotent:bool=False

def start_private_pg(directory,cfg,operation):
    with owned_paths(directory,operation)['control'].open('ab') as output:
        subprocess.run([str(base.toolchain()['postgresql'].parent/'pg_ctl.exe'),'start','-D',str(directory/'data'),
            '-w','-t','60','-l',str(directory/'postgres.log'),'-o','-c autovacuum=off'],
            stdin=subprocess.DEVNULL,stdout=output,stderr=output,creationflags=base.NO_WINDOW,timeout=90,check=True)
    base.require_private_mode(directory,cfg)

class OwnedRuntime(base.OwnedRuntime):
    """Reuse quiet/stop; own entrypoint and logs preserve all parent1269 outputs."""
    def start_pg(self):
        if self.operation is None:raise Artifact13Error('explicit_operation1509_runtime_required')
        self.quiet();self.owned=True;self.launch={'kind':'pg-control','phase':'attempted'}
        start_private_pg(self.directory,self.cfg,self.operation)

    def start_app(self,*,preview=False):
        self.quiet()
        paths=owned_paths(self.directory,self.operation)
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'_supervise','--source',str(self.directory),'--operation',str(self.operation)]
        if preview:command.append('--preview')
        with paths['supervisor'].open('ab') as output:
            self.owned=True;self.launch={'kind':'job-supervisor','phase':'attempted'}
            try:self.process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=output,stderr=output,creationflags=base.NO_WINDOW)
            except Exception:self.owned=False;raise
            self.launch.update(phase='child-created',supervisorPid=self.process.pid)
        until=time.monotonic()+90
        while time.monotonic()<until:
            if self.process.poll() is not None:raise Artifact13Error('runtime1509_supervisor_failed')
            if base.qa_module().ready(self.directory,self.cfg):
                base.require_private_mode(self.directory,self.cfg);base.verify_ready(self.directory,self.cfg);return
            time.sleep(.1)
        raise Artifact13Error('runtime1509_start_timeout')

def verify_boundary_static(source,record,config,operation):
    source.unchanged(expected_config=config,hashes=record['sourceInputHashes'],operation=operation)
    if (contracts.load_operation(source.original,operation,source.parent_operation,source.parent_record,source.parent_bindings)!=record or
        hashlib.sha256(source.pointer_bytes).hexdigest()!=record['pointerSha256']):raise Artifact13Error('operation1509_record_changed')

def verify_boundary(source,record,config,operation):
    verify_boundary_static(source,record,config,operation)
    base.require_unchanged_activity(source.directory,source.original_cfg,record['activityBaseline'])
    if source.database_states()!=record['databaseStates']:raise Artifact13Error('operation1509_database_states_changed')
    base.require_unchanged_activity(source.directory,source.recovery_cfg,record['activityBaseline'])

def _verify_stopped(source,record,config,operation):
    runtime=OwnedRuntime(source.directory,source.original_cfg,operation)
    try:runtime.start_pg();verify_boundary(source,record,config,operation)
    finally:runtime.stop()
    runtime.quiet();verify_boundary_static(source,record,config,operation)

def _guarded_restore(result,record):
    source,operation=result.source,result.operation
    previous=(operation/'previous-config.json').read_bytes();selected=(operation/'selected-config.json').read_bytes()
    current=(source.directory/'manual-qa.json').read_bytes()
    if current not in (previous,selected):raise Artifact13Error('operation1509_selection_uncertain')
    _verify_stopped(source,record,current,operation)
    if current==selected:base.atomic_bytes(source.directory/'manual-qa.json',previous)
    verify_boundary_static(source,record,previous,operation)

def validate_operation(directory,pointer,*,real=False,operation=None):
    with base.profile_lock(checked_path(pointer)):
        source=Source1329(directory,pointer,real=real,operation=operation);OwnedRuntime(source.directory,source.cfg).quiet();source.unchanged()
        return source

def update_operation(directory,pointer,*,real=False,operation=None,hook=None):
    initial=Source1329(directory,pointer,real=real,operation=operation);OwnedRuntime(initial.directory,initial.cfg).quiet()
    with base.profile_lock(initial.pointer):
        source=Source1329(directory,pointer,real=real,operation=operation)
        if (source.hashes,source.config_bytes,source.pointer_bytes)!=(initial.hashes,initial.config_bytes,initial.pointer_bytes):raise Artifact13Error('source1329_changed_before_lock')
        target=load_target();fresh=source.operation is None
        operation=source.directory/'versions'/('artifact13-1449-'+uuid.uuid4().hex) if fresh else source.operation
        checked_operation(source.directory,operation);paths=owned_paths(source.directory,operation)
        result=Result1509(source,operation,paths['journal']);record=source.record
        state=dict(state='allocated',attempt=1,sourceRevision=1329,selectedRevision=1329,schema=13,baselineRenewed=False,leftRunning=None)
        runtime=OwnedRuntime(source.directory,source.source_cfg,operation)
        if not fresh:
            state=json.loads(checked_path(paths['journal']).read_bytes())
            result.state='recovery_required'
            if state.get('reentryRecoveryRequired') or state.get('state') not in ('committed','rolled_back'):raise Artifact13Error('recovery_required',result)
            if (state.get('leftRunning') is not False or state.get('applicationStopConfirmed') is not True or state.get('postgresqlStopConfirmed') is not True):raise Artifact13Error('recovery_required',result)
            if state['state']=='committed':
                result.idempotent=True
                try:
                    if source.revision!=1449:raise Artifact13Error('operation1509_committed_selection_changed')
                    _verify_stopped(source,record,source.config_bytes,operation);result.state='committed';return result
                except Exception as error:
                    state.update(reentryRecoveryRequired=True,reentryFailureCode=getattr(error,'code','verification1509_uncertain'))
                    save(paths['journal'],state);result.state='recovery_required';raise Artifact13Error('recovery_required',result) from None
            if source.revision!=1329:raise Artifact13Error('recovery_required',result)
            # Reentry after complete quiet rollback uses the SAME immutable record.
            try:_verify_stopped(source,record,source.source_config_bytes,operation)
            except Exception as error:
                state.update(state='recovery_required',failureCode=getattr(error,'code','resume1509_uncertain'))
                save(paths['journal'],state);result.state='recovery_required';raise Artifact13Error('recovery_required',result) from None
            state.update(state='resuming',attempt=state.get('attempt',1)+1)
        try:
            if fresh:
                operation.mkdir(exist_ok=False);save(paths['journal'],state)
                for name in ('server','frontend'):shutil.copytree(getattr(target,name),operation/name)
                base.atomic_bytes(operation/'previous-config.json',source.source_config_bytes)
                selected=dict(source.source_cfg,artifactDirectory=str(operation),bundleSha256=target.expected['frontend']['app.js'])
                preview=dict(selected,webPort=base.free_port())
                while preview['webPort'] in (selected['webPort'],selected['pgPort']):preview['webPort']=base.free_port()
                save(operation/'selected-config.json',selected);save(operation/'preview-config.json',preview)
                runtime.start_pg();activity=base.activity_watermark(source.directory,source.original_cfg)
                states=source.database_states();base.require_unchanged_activity(source.directory,source.recovery_cfg,activity);runtime.stop()
                record=dict(kind='artifact13-closed1329-to1449',directory=str(source.directory),operation=str(operation),
                    sourceManifestSha256=contracts.SOURCE_SHA256,targetManifestSha256=sha256(contracts.TARGET_MANIFEST),targetArtifacts=target.expected,
                    parentOperation=str(source.parent_operation),parentBindings=source.parent_bindings,
                    configurationHashes={n:sha256(operation/n) for n in ('previous-config.json','selected-config.json','preview-config.json')},
                    sourceInputHashes=source.hashes,databaseStates=states,activityBaseline=activity,pointerSha256=hashlib.sha256(source.pointer_bytes).hexdigest())
                save(operation/OPERATION,record);base.atomic_bytes(operation/OPERATION_SEAL,(sha256(operation/OPERATION)+'\n').encode('ascii'))
            state['state']='prepared';save(paths['journal'],state)
            if hook:hook('prepared',result)
            previous=(operation/'previous-config.json').read_bytes();selected_bytes=(operation/'selected-config.json').read_bytes()
            preview=json.loads((operation/'preview-config.json').read_bytes());selected=json.loads(selected_bytes)
            verify_boundary_static(source,record,previous,operation)
            runtime.cfg=preview;runtime.start_app(preview=True);runtime.stop()
            if hook:hook('after_preview',result)
            _verify_stopped(source,record,previous,operation)
            verify_boundary_static(source,record,previous,operation);OwnedRuntime(source.directory,source.source_cfg).quiet()
            base.atomic_bytes(source.directory/'manual-qa.json',selected_bytes)
            state.update(state='selected',selectedRevision=1449);save(paths['journal'],state)
            if hook:hook('after_config',result)
            runtime.cfg=selected;runtime.start_app();runtime.stop()
            if hook:hook('after_selected_stop',result)
            _verify_stopped(source,record,selected_bytes,operation);runtime.quiet()
            state.update(state='committed',leftRunning=False,applicationStopConfirmed=True,postgresqlStopConfirmed=True)
            save(paths['journal'],state);result.state='committed';return result
        except Exception as error:
            state['failureCode']=getattr(error,'code','update1509_internal_failure')
            try:
                runtime.stop();runtime.quiet()
                if record is None:source.unchanged(operation=operation);state['state']='preparation_failed'
                else:_guarded_restore(result,record);state.update(state='rolled_back',selectedRevision=1329)
                state.update(leftRunning=False,applicationStopConfirmed=True,postgresqlStopConfirmed=True)
            except Exception as blocker:
                state.update(state='recovery_required',recoveryBlocker=getattr(blocker,'code','verification1509_uncertain'),leftRunning=None)
                try:runtime.quiet();state.update(leftRunning=False,applicationStopConfirmed=True,postgresqlStopConfirmed=True)
                except Exception:pass
            result.state=state['state'];save(paths['journal'],state);raise Artifact13Error(result.state,result) from None

def worker(directory,operation,*,supervise=False,preview=False):
    directory=checked_path(directory);operation=checked_operation(directory,operation)
    # Explicit fixture pointer or real pointer is not needed by a child. Validate
    # provenance directly, including exact old/new records and full hash universe.
    original=contracts.prior.original_metadata(directory);record=contracts.read_record(directory,operation,1449)
    parent=checked_operation(directory,record['parentOperation'],1329)
    parent_record,bindings=contracts.validate_parents(original,parent,operation)
    contracts.load_operation(original,operation,parent,parent_record,bindings)
    expected=(operation/('previous-config.json' if preview else 'selected-config.json')).read_bytes()
    if (directory/'manual-qa.json').read_bytes()!=expected:raise Artifact13Error('worker1509_selection_differs')
    cfg=json.loads((operation/('preview-config.json' if preview else 'selected-config.json')).read_bytes())
    if supervise:
        cmd=[sys.executable,'-B',str(Path(__file__).resolve()),'_worker','--source',str(directory),'--operation',str(operation)]
        if preview:cmd.append('--preview')
        with owned_paths(directory,operation)['worker'].open('ab') as output:done=base.run_isolated(cmd,cwd=ROOT,stdout=output,stderr=output)
        if done.returncode:raise Artifact13Error('worker1509_failed')
    else:
        qa=base.qa_module();normal=qa.control
        def control(directory,action):
            if action=='start':start_private_pg(directory,cfg,operation)
            else:normal(directory,action)
        qa.control=control;qa.serve(directory,cfg)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    for action in ('validate','update'):
        a=sub.add_parser(action);a.add_argument('--source',type=Path,required=True);a.add_argument('--pointer',type=Path,required=True);a.add_argument('--operation',type=Path);a.add_argument('--real',action='store_true')
    for action in ('_supervise','_worker'):
        a=sub.add_parser(action);a.add_argument('--source',type=Path,required=True);a.add_argument('--operation',type=Path,required=True);a.add_argument('--preview',action='store_true')
    a=p.parse_args()
    try:
        if a.action.startswith('_'):worker(a.source,a.operation,supervise=a.action=='_supervise',preview=a.preview);return 0
        if a.action=='validate':
            s=validate_operation(a.source,a.pointer,real=a.real,operation=a.operation);v=dict(state='validated',selectedRevision=s.revision,schema=13,databaseTestExecuted=False)
        else:
            r=update_operation(a.source,a.pointer,real=a.real,operation=a.operation);v=dict(state=r.state,selectedRevision=1449,schema=13,idempotent=r.idempotent,leftRunning=False)
        print(json.dumps(v));return 0
    except Exception as error:
        print(json.dumps(dict(state=getattr(error,'code','operation1509_failed'),selectedRevision=None,schema=13,leftRunning=None)),file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
