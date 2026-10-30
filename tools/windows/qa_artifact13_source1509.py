"""Closed1329 ->1449 chain; original1149,1209 and1329 remain immutable.

Projection names only the explicit recorded ancestors and this one successor.
No historical validator patch, temporary config rewrite, discovery or PG launch.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

import qa_artifact13_source1389 as chain

ROOT=chain.ROOT
prior=chain.prior
Artifact13Error=chain.Artifact13Error
SOURCE_MANIFEST=chain.TARGET_MANIFEST
SOURCE_SHA256=chain.TARGET1389[1]
TARGET_MANIFEST=ROOT/'evidence/s1-20261018/sesenta-tandas-1390-1449/CANDIDATA1449-01.json'
TARGET1509=(TARGET_MANIFEST.relative_to(ROOT).as_posix(),'55bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6')
OPERATION,OPERATION_SEAL=chain.OPERATION,chain.OPERATION_SEAL
config_bytes,sha256,checked_path=chain.config_bytes,chain.sha256,chain.checked_path
read_record,validate_stage=chain.read_record,chain.validate_stage

@dataclass(frozen=True)
class Distribution1509:
    revision:int
    schema:int
    server:Path
    frontend:Path
    expected:dict
    manifest:Path

    def validate(self):
        if (self.revision!=1449 or self.schema!=13 or self.manifest!=TARGET_MANIFEST or
            TARGET1509!=(TARGET_MANIFEST.relative_to(ROOT).as_posix(),'55bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6') or
            sha256(checked_path(TARGET_MANIFEST))!=TARGET1509[1]):raise Artifact13Error('target1509_pin_invalid')
        v=json.loads(TARGET_MANIFEST.read_bytes());old=chain.load_target()
        actual={'server':prior.artifact_manifest(self.server),'frontend':prior.artifact_manifest(self.frontend)}
        total=sum(p.stat().st_size for d in (self.server,self.frontend) for p in d.rglob('*') if p.is_file())
        if (v.get('schema')!=13 or self.server!=checked_path(ROOT/Path(v['serverDll']).parent) or
            self.frontend!=checked_path(ROOT/v['frontend']) or any(not p.is_relative_to(ROOT/'.local/candidates') for p in (self.server,self.frontend)) or
            self.expected!=v['distributions'] or actual!=self.expected or len(actual['server'])!=22 or len(actual['frontend'])!=18 or
            v.get('fileCount')!=40 or v.get('totalBytes')!=7159235 or total!=7159235 or
            actual['server']!=old.expected['server'] or
            {k:v for k,v in actual['frontend'].items() if k!='app.js'}!={k:v for k,v in old.expected['frontend'].items() if k!='app.js'} or
            actual['frontend']['app.js']==old.expected['frontend']['app.js']):raise Artifact13Error('only_reviewed1449_bundle_change_allowed')
        return actual

def load_target():
    if TARGET1509!=(TARGET_MANIFEST.relative_to(ROOT).as_posix(),'55bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6') or sha256(checked_path(TARGET_MANIFEST))!=TARGET1509[1]:raise Artifact13Error('target1509_pin_invalid')
    v=json.loads(TARGET_MANIFEST.read_bytes())
    d=Distribution1509(1449,13,checked_path(ROOT/Path(v['serverDll']).parent),checked_path(ROOT/v['frontend']),v['distributions'],TARGET_MANIFEST)
    d.validate();return d

def checked_operation(directory,operation,revision=1449):return chain.checked_operation(directory,operation,revision)

def owned_paths(directory,operation):
    token=checked_operation(directory,operation).name.removeprefix('artifact13-')
    return {kind:directory/('chain1509-'+token+'-'+kind+'-private.'+('json' if kind=='journal' else 'log')) for kind in ('journal','control','supervisor','worker')}

def project_successor(original,hashes,operation):
    if operation is None:return hashes
    operation=checked_operation(original.directory,operation)
    prefix=operation.relative_to(original.directory).as_posix()+'/'
    owned={p.name for p in owned_paths(original.directory,operation).values()}
    return {k:v for k,v in hashes.items() if not k.startswith(prefix) and k not in owned}

def inventory(original,operation=None):
    return project_successor(original,chain.inventory(original),operation)

def require_version_entries(original,parent1209,parent1329,operation=None):
    expected={'category-colors13-source969-recovery',parent1209.name,parent1329.name}
    if operation is not None:expected.add(checked_operation(original.directory,operation).name)
    entries=list(checked_path(original.directory/'versions').iterdir())
    if any(not checked_path(p).is_dir() for p in entries) or {p.name for p in entries}!=expected:raise Artifact13Error('source1329_version_set_changed')

def parent_bindings(directory,parent):
    path=chain.owned_paths(directory,parent)['journal'];state=json.loads(checked_path(path).read_bytes())
    if (state.get('state')!='committed' or state.get('reentryRecoveryRequired') is True or
        state.get('leftRunning') is not False or state.get('applicationStopConfirmed') is not True or
        state.get('postgresqlStopConfirmed') is not True):raise Artifact13Error('parent1329_not_committed_and_quiet')
    return {name:sha256(path) for name,path in (('record',parent/OPERATION),('seal',parent/OPERATION_SEAL),('journal',path))}

def validate_parents(original,parent,operation=None):
    """Validate two archives without asking old closed validators to admit1449."""
    parent=checked_operation(original.directory,parent,1329);record=read_record(original.directory,parent,1329)
    ancestor=checked_operation(original.directory,record['parentOperation'],1209)
    require_version_entries(original,ancestor,parent,operation)
    old=read_record(original.directory,ancestor,1209)
    validate_stage(original,ancestor,old,config_bytes(original.cfg),prior.load_target(),prior.SOURCE_SHA256,'artifact13-closed1089-to1209')
    prefixes=[p.relative_to(original.directory).as_posix()+'/' for p in (ancestor,parent)]
    if operation is not None:prefixes.append(checked_operation(original.directory,operation).relative_to(original.directory).as_posix()+'/')
    first={k:v for k,v in prior.immutable_hashes(original).items() if not any(k.startswith(prefix) for prefix in prefixes)}
    if first!=old.get('sourceInputHashes'):raise Artifact13Error('ancestor1209_input_universe_changed')
    old_bindings=chain.parent_bindings(original.directory,ancestor)
    validate_stage(original,parent,record,(ancestor/'selected-config.json').read_bytes(),chain.load_target(),chain.SOURCE_SHA256,'artifact13-closed1209-to1329')
    if (record.get('parentBindings')!=old_bindings or record.get('pointerSha256')!=old['pointerSha256'] or
        record.get('sourceInputHashes')!=project_successor(original,chain.inventory(original,parent),operation)):
        raise Artifact13Error('parent1329_ancestor_binding_changed')
    return record,parent_bindings(original.directory,parent)

def load_operation(original,operation,parent,parent_record,bindings):
    operation=checked_operation(original.directory,operation);record=read_record(original.directory,operation,1449)
    validate_stage(original,operation,record,(parent/'selected-config.json').read_bytes(),load_target(),SOURCE_SHA256,'artifact13-closed1329-to1449')
    if (record.get('parentOperation')!=str(parent) or record.get('parentBindings')!=bindings or
        record.get('sourceInputHashes')!=inventory(original,operation) or record['pointerSha256']!=parent_record['pointerSha256']):
        raise Artifact13Error('operation1509_parent_binding_changed')
    return record

class Source1329(chain.Source1209):
    """Inherit READ ONLY39/37 database/catalog logic; validate three stages here."""
    def __init__(self,directory,pointer,*,real=False,operation=None,quiet=True):
        try:
            self.directory=prior.checked_candidate_directory(directory);self.pointer=checked_path(pointer);self.real=real
            if self.pointer!=(ROOT/'.local/qa-rc9/current.json' if real else self.directory/'artifact13-home/current.json'):raise Artifact13Error('explicit_source1329_profile_required')
            self.pointer_bytes=self.pointer.read_bytes()
            if json.loads(self.pointer_bytes)!={'directory':str(self.directory)}:raise Artifact13Error('source1329_pointer_differs')
            self.original=prior.original_metadata(self.directory);self.original_cfg=self.original.cfg
            self.db=self.original.database;self.recovered=self.original.recovered;self.recovery_cfg=self.original.recovery_cfg
            self.config_bytes=(self.directory/'manual-qa.json').read_bytes();self.cfg=json.loads(self.config_bytes)
            self.operation=checked_operation(self.directory,operation) if operation is not None else None
            art=checked_path(self.cfg.get('artifactDirectory',''))
            if re.fullmatch('artifact13-1449-[0-9a-f]{32}',art.name):
                if self.operation is not None and self.operation!=art:raise Artifact13Error('explicit_operation1509_differs')
                self.operation=checked_operation(self.directory,art)
            if self.operation is not None:
                hint=read_record(self.directory,self.operation,1449);self.parent_operation=checked_operation(self.directory,hint['parentOperation'],1329)
            else:self.parent_operation=checked_operation(self.directory,art,1329)
            self.parent_record,self.parent_bindings=validate_parents(self.original,self.parent_operation,self.operation)
            self.source_config_bytes=(self.parent_operation/'selected-config.json').read_bytes()
            self.source_cfg=json.loads(self.source_config_bytes);self.record=None;self.revision=1329
            if self.operation is not None:
                self.record=load_operation(self.original,self.operation,self.parent_operation,self.parent_record,self.parent_bindings)
                if self.config_bytes==(self.operation/'selected-config.json').read_bytes():self.revision=1449
                elif self.config_bytes!=self.source_config_bytes:raise Artifact13Error('source1329_selected_config_differs')
            elif self.config_bytes!=self.source_config_bytes:raise Artifact13Error('source1329_selected_config_differs')
            if (hashlib.sha256(self.pointer_bytes).hexdigest()!=self.parent_record['pointerSha256'] or real and self.cfg['webPort']!=52346):raise Artifact13Error('source1329_pointer_or_real_port_changed')
            self.art=art;self.baseline=chain.load_target();self.target=load_target()
            self.pg_bin=prior.toolchain()['postgresql'].parent;self.admin_passfile=checked_path(self.directory/'admin.pgpass')
            self.hashes=inventory(self.original,self.operation);self.inputs=[self.directory/n for n in self.hashes]
            if quiet:prior.app_stopped(self.directory,self.cfg['webPort'])
        except Artifact13Error:raise
        except Exception:raise Artifact13Error('source1329_chain_validation_failed') from None

    def unchanged(self,*,expected_config=None,hashes=None,quiet=True,operation=None):
        prior._validate_original_static(self.original)
        op=self.operation if operation is None else checked_operation(self.directory,operation)
        record,bindings=validate_parents(self.original,self.parent_operation,op)
        if record!=self.parent_record or bindings!=self.parent_bindings:raise Artifact13Error('source1329_parent_changed')
        if inventory(self.original,op)!=(self.hashes if hashes is None else hashes):raise Artifact13Error('source1329_input_universe_changed')
        if self.pointer.read_bytes()!=self.pointer_bytes or (self.directory/'manual-qa.json').read_bytes()!=(self.config_bytes if expected_config is None else expected_config):raise Artifact13Error('source1329_config_or_pointer_changed')
        if quiet:prior.app_stopped(self.directory,self.cfg['webPort'])

Source13=Source1329
