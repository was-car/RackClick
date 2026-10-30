"""Closed1089 ->1209 artifact update, within one genuine1149 root/cluster.

No migrations, new databases, grants, authentication, reset or public rollback.
All raw operation metadata/logs remain in the private laboratory directory.
"""
import argparse
from dataclasses import dataclass
import hashlib
import http.client
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'development/server/tests'))
from pg_support import NO_WINDOW,free_port,toolchain
from pg_lab_recovery import sha256
from qa_schema5_switch import atomic_bytes
from qa_schema_switch import profile_lock,qa_module,pg_running,stop_application,activity_watermark,require_unchanged_activity
from qa_schema6_source import app_stopped
from windows_job import run_isolated
from qa_artifact13_source1269 import (Source13,Artifact13Error,load_target,load_operation,checked_operation,
    checked_path,OPERATION,OPERATION_SEAL,SOURCE_SHA256,TARGET_MANIFEST,config_bytes)

def save(path,value):atomic_bytes(path,config_bytes(value))

@dataclass
class Result1269:
    source:object
    operation:Path
    journal:Path
    state:str='validated'
    idempotent:bool=False

def start_private_pg(directory):
    with (directory/'artifact13-control-private.log').open('ab') as output:
        subprocess.run([str(toolchain()['postgresql'].parent/'pg_ctl.exe'),'start','-D',str(directory/'data'),
            '-w','-t','60','-l',str(directory/'postgres.log'),'-o','-c autovacuum=off'],
            stdin=subprocess.DEVNULL,stdout=output,stderr=output,creationflags=NO_WINDOW,timeout=90,check=True)

def require_private_mode(directory,cfg):
    from qa_schema_switch import read_owner
    if read_owner(directory,cfg,'SHOW autovacuum')!='off':
        raise Artifact13Error('runtime1269_temporary_mode_unconfirmed')

def verify_ready(directory,cfg):
    if not qa_module().ready(directory,cfg):raise Artifact13Error('runtime1269_readiness_unconfirmed')
    conn=http.client.HTTPConnection('127.0.0.1',cfg['webPort'],timeout=15)
    try:
        conn.request('GET','/health/ready');reply=conn.getresponse()
        if reply.status!=200 or json.loads(reply.read())!={'status':'ready','schemaVersion':13}:
            raise Artifact13Error('runtime1269_ready_schema_differs')
        conn.request('GET','/app.js');reply=conn.getresponse()
        if reply.status!=200 or hashlib.sha256(reply.read()).hexdigest()!=cfg['bundleSha256']:
            raise Artifact13Error('runtime1269_served_bundle_differs')
    finally:conn.close()

class OwnedRuntime:
    def __init__(self,directory,cfg,operation=None):
        self.directory,self.cfg,self.operation=directory,cfg,operation
        self.owned=False;self.process=None;self.launch=None

    def quiet(self):
        app_stopped(self.directory,self.cfg['webPort'])
        if pg_running(self.directory):raise Artifact13Error('runtime1269_foreign_or_uncertain_pg_active')

    def start_pg(self):
        self.quiet();self.owned=True;self.launch={'kind':'pg-control','phase':'attempted'}
        start_private_pg(self.directory);require_private_mode(self.directory,self.cfg)

    def start_app(self,*,preview=False):
        self.quiet()
        if self.operation is None:raise Artifact13Error('runtime1269_explicit_operation_required')
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'_supervise','--source',str(self.directory),
            '--operation',str(self.operation)]
        if preview:command.append('--preview')
        with (self.directory/'artifact13-supervisor-private.log').open('ab') as output:
            self.owned=True;self.launch={'kind':'job-supervisor','phase':'attempted'}
            try:self.process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=output,stderr=output,creationflags=NO_WINDOW)
            except Exception:self.owned=False;raise
            self.launch.update(phase='child-created',supervisorPid=self.process.pid)
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            if self.process.poll() is not None:raise Artifact13Error('runtime1269_supervisor_start_failed')
            if qa_module().ready(self.directory,self.cfg):
                require_private_mode(self.directory,self.cfg);verify_ready(self.directory,self.cfg);return
            time.sleep(.1)
        raise Artifact13Error('runtime1269_supervisor_start_timeout')

    def stop(self):
        if not self.owned:return
        if self.process is not None:
            stop_application(self.directory,self.cfg);self.process.wait(timeout=30)
        else:
            app_stopped(self.directory,self.cfg['webPort'])
            if pg_running(self.directory):qa_module().control(self.directory,'stop')
        self.quiet();self.owned=False;self.process=None;self.launch['phase']='stopped-confirmed'

def verify_boundary(source,record,expected_config,operation):
    """One immutable cluster watermark, checked before/after BOTH current DBs.

    Global XID proves activity, not which database caused it. No baseline renewal.
    """
    verify_boundary_static(source,record,expected_config,operation)
    require_unchanged_activity(source.directory,source.original_cfg,record['activityBaseline'])
    if source.database_states()!=record['databaseStates']:
        raise Artifact13Error('operation1269_current_database_states_changed')
    require_unchanged_activity(source.directory,source.recovery_cfg,record['activityBaseline'])

def _verify_stopped(source,record,config,operation):
    runtime=OwnedRuntime(source.directory,source.original_cfg,operation)
    try:
        runtime.start_pg();verify_boundary(source,record,config,operation)
    finally:runtime.stop()
    runtime.quiet();source.unchanged(expected_config=config,hashes=record['sourceInputHashes'])

def _guarded_restore(result,record):
    """Only called by the failure handler while update_operation still owns scope."""
    source,operation=result.source,result.operation
    selected=(operation/'selected-config.json').read_bytes();previous=(operation/'previous-config.json').read_bytes()
    current=(source.directory/'manual-qa.json').read_bytes()
    if current not in (previous,selected):raise Artifact13Error('operation1269_selection_uncertain')
    _verify_stopped(source,record,current,operation)
    # No file rewind until process, DB activity, rows, grants and inputs confirmed.
    if current==selected:atomic_bytes(source.directory/'manual-qa.json',previous)
    source.unchanged(expected_config=previous,hashes=record['sourceInputHashes'])

def journal_path(source,operation):return source.directory/('artifact13-'+operation.name.removeprefix('artifact13-')+'-journal-private.json')

def validate_operation(directory,pointer,*,real=False):
    with profile_lock(checked_path(pointer)):
        source=Source13(directory,pointer,real=real);OwnedRuntime(source.directory,source.cfg).quiet()
        source.unchanged();load_target().validate()
        return source

def update_operation(directory,pointer,*,real=False,hook=None):
    initial=Source13(directory,pointer,real=real);OwnedRuntime(initial.directory,initial.cfg).quiet()
    with profile_lock(initial.pointer):
        source=Source13(directory,pointer,real=real)
        if source.config_bytes!=initial.config_bytes or source.hashes!=initial.hashes or source.pointer_bytes!=initial.pointer_bytes:
            raise Artifact13Error('source13_changed_before_lock')
        target=load_target()
        if source.operation is not None:
            # Reentry never creates a version/baseline or grants post-QA rollback.
            operation=source.operation;record=source.record;journal=journal_path(source,operation)
            result=Result1269(source,operation,journal,idempotent=True)
            state=json.loads(checked_path(journal).read_bytes())
            if state.get('state')!='committed':
                result.state='recovery_required';raise Artifact13Error('recovery_required',result)
            try:
                _verify_stopped(source,record,source.config_bytes,operation)
                result.state='committed';return result
            except Exception as error:
                result.state='recovery_required'
                # Keep the original success journal and baseline as evidence.
                save(source.directory/('artifact13-reentry-'+uuid.uuid4().hex+'-private.json'),
                    dict(state='recovery_required',failureCode=getattr(error,'code','reentry1269_verification_uncertain'),
                         selectedRevision=1209,baselineRenewed=False,rollbackAttempted=False))
                raise Artifact13Error('recovery_required',result) from None
        operation=source.directory/'versions'/('artifact13-1209-'+uuid.uuid4().hex)
        checked_operation(source.directory,operation);operation.mkdir(exist_ok=False)
        result=Result1269(source,operation,journal_path(source,operation))
        state=dict(state='allocated',sourceRevision=1089,selectedRevision=1089,schema=13,baselineRenewed=False,
            databaseMutationPerformed=False,leftRunning=None)
        runtime=OwnedRuntime(source.directory,source.original_cfg,operation);record=None
        try:
            save(result.journal,state)
            for name in ('server','frontend'):shutil.copytree(getattr(target,name),operation/name)
            atomic_bytes(operation/'previous-config.json',source.config_bytes)
            selected=dict(source.cfg,artifactDirectory=str(operation),bundleSha256=target.expected['frontend']['app.js'])
            preview=dict(selected,webPort=free_port())
            while preview['webPort'] in (selected['webPort'],selected['pgPort']):preview['webPort']=free_port()
            save(operation/'selected-config.json',selected);save(operation/'preview-config.json',preview)
            runtime.start_pg()
            activity=activity_watermark(source.directory,source.original_cfg)
            states=source.database_states()
            require_unchanged_activity(source.directory,source.recovery_cfg,activity)
            runtime.stop()
            record=dict(kind='artifact13-closed1089-to1209',directory=str(source.directory),operation=str(operation),
                sourceManifestSha256=SOURCE_SHA256,targetManifestSha256=sha256(TARGET_MANIFEST),targetArtifacts=target.expected,
                configurationHashes={n:sha256(operation/n) for n in ('previous-config.json','selected-config.json','preview-config.json')},
                sourceInputHashes=source.hashes,databaseStates=states,activityBaseline=activity,
                pointerSha256=hashlib.sha256(source.pointer_bytes).hexdigest())
            save(operation/OPERATION,record);atomic_bytes(operation/OPERATION_SEAL,(sha256(operation/OPERATION)+'\n').encode('ascii'))
            state['state']='prepared';save(result.journal,state)
            if hook:hook('prepared',result)
            verify_boundary_static(source,record,source.config_bytes,operation)
            runtime.cfg=preview;runtime.start_app(preview=True);verify_ready(source.directory,preview);runtime.stop()
            if hook:hook('after_preview',result)
            _verify_stopped(source,record,source.config_bytes,operation)
            state['state']='preview-verified';save(result.journal,state)
            verify_boundary_static(source,record,source.config_bytes,operation)
            OwnedRuntime(source.directory,source.original_cfg).quiet()
            atomic_bytes(source.directory/'manual-qa.json',(operation/'selected-config.json').read_bytes())
            state.update(state='selected',selectedRevision=1209);save(result.journal,state)
            if hook:hook('after_config',result)
            runtime.cfg=selected;runtime.start_app();verify_ready(source.directory,selected);runtime.stop()
            if hook:hook('after_selected_stop',result)
            _verify_stopped(source,record,(operation/'selected-config.json').read_bytes(),operation)
            verify_boundary_static(source,record,(operation/'selected-config.json').read_bytes(),operation)
            runtime.quiet()
            state.update(state='committed',leftRunning=False,applicationStopConfirmed=True,postgresqlStopConfirmed=True)
            save(result.journal,state);result.state='committed';return result
        except Exception as error:
            state['failureCode']=getattr(error,'code','update1269_internal_failure')
            try:
                runtime.stop();runtime.quiet()
                if record is None:
                    source.unchanged();state['state']='preparation_failed'
                else:
                    _guarded_restore(result,record);state.update(state='rolled_back',selectedRevision=1089)
                state.update(leftRunning=False,applicationStopConfirmed=True,postgresqlStopConfirmed=True)
            except Exception as blocker:
                state.update(state='recovery_required',recoveryBlocker=getattr(blocker,'code','update1269_verification_uncertain'),leftRunning=None)
                current=(source.directory/'manual-qa.json').read_bytes()
                state['selectedRevision']=1209 if (operation/'selected-config.json').exists() and current==(operation/'selected-config.json').read_bytes() else None
                try:
                    runtime.quiet()
                    state.update(leftRunning=False,applicationStopConfirmed=True,postgresqlStopConfirmed=True)
                except Exception:
                    state.update(applicationStopConfirmed=None,postgresqlStopConfirmed=None)
            result.state=state['state'];save(result.journal,state)
            raise Artifact13Error(result.state,result) from None

def verify_boundary_static(source,record,config,operation):
    source.unchanged(expected_config=config,hashes=record['sourceInputHashes'])
    if (load_operation(source.directory,operation)!=record or
        hashlib.sha256(source.pointer_bytes).hexdigest()!=record['pointerSha256']):
        raise Artifact13Error('operation1269_record_changed')

def worker(directory,operation,*,supervise=False,preview=False):
    directory=checked_path(directory);operation=checked_operation(directory,operation)
    record=load_operation(directory,operation)
    # Metadata-only validation; no pointer discovery and no baseline recreation.
    from qa_artifact13_source1269 import original_metadata
    original_metadata(directory)
    cfg=json.loads((operation/('preview-config.json' if preview else 'selected-config.json')).read_bytes())
    current=(directory/'manual-qa.json').read_bytes()
    expected=(operation/('previous-config.json' if preview else 'selected-config.json')).read_bytes()
    if current!=expected:raise Artifact13Error('worker1269_selection_differs')
    for name,digest in record['sourceInputHashes'].items():
        if sha256(checked_path(directory/name))!=digest:raise Artifact13Error('worker1269_inputs_changed')
    if supervise:
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'_worker','--source',str(directory),'--operation',str(operation)]
        if preview:command.append('--preview')
        with (directory/'artifact13-worker-private.log').open('ab') as output:
            done=run_isolated(command,cwd=ROOT,stdout=output,stderr=output)
        if done.returncode:raise Artifact13Error('worker1269_failed')
    else:
        qa=qa_module();normal=qa.control
        def control(directory,action):
            if action=='start':start_private_pg(directory);require_private_mode(directory,cfg)
            else:normal(directory,action)
        qa.control=control;qa.serve(directory,cfg)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    for action in ('validate','update'):
        a=sub.add_parser(action);a.add_argument('--source',type=Path,required=True);a.add_argument('--pointer',type=Path,required=True);a.add_argument('--real',action='store_true')
    for action in ('_supervise','_worker'):
        a=sub.add_parser(action);a.add_argument('--source',type=Path,required=True);a.add_argument('--operation',type=Path,required=True);a.add_argument('--preview',action='store_true')
    args=p.parse_args()
    try:
        if args.action.startswith('_'):
            worker(args.source,args.operation,supervise=args.action=='_supervise',preview=args.preview);return 0
        if args.action=='validate':
            s=validate_operation(args.source,args.pointer,real=args.real)
            value=dict(state='validated',selectedRevision=s.revision,schema=13,databaseTestExecuted=False)
        else:
            result=update_operation(args.source,args.pointer,real=args.real)
            value=dict(state=result.state,selectedRevision=1209,schema=13,leftRunning=False,idempotent=result.idempotent)
        print(json.dumps(value));return 0
    except Exception as error:
        result=getattr(error,'result',None)
        print(json.dumps(dict(state=getattr(error,'code','operation1269_failed'),selectedRevision=None,schema=13,
            leftRunning=None,operationState=None if result is None else result.state)),file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
