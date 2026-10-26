"""Closed1209 ->1329 chain; original1149 and1269 stages remain immutable.

One explicitly named successor is projected out of the historical hash universe.
No discovery, legacy validator patches, temporary config rewrite or PG launch.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'development/server/tests'))
import qa_artifact13_source1269 as prior
from qa_schema_switch import _safe_activity

Artifact13Error=prior.Artifact13Error
SOURCE_MANIFEST=prior.TARGET_MANIFEST
SOURCE_SHA256=prior.TARGET1269[1]
TARGET_MANIFEST=ROOT/'evidence/s1-20261018/sesenta-tandas-1270-1329/CANDIDATA1329-01.json'
TARGET1389=(TARGET_MANIFEST.relative_to(ROOT).as_posix(),'38bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6')
OPERATION,OPERATION_SEAL=prior.OPERATION,prior.OPERATION_SEAL
config_bytes,sha256,checked_path=prior.config_bytes,prior.sha256,prior.checked_path
RUNTIME_FILES=frozenset(('postgres.log','manual-control.log','manual-server.log','pg_ctl.log','preview-manual-qa.json','stop.request','server.lock','ready.json'))

@dataclass(frozen=True)
class Distribution1389:
    revision:int
    schema:int
    server:Path
    frontend:Path
    expected:dict
    manifest:Path

    def validate(self):
        if (self.revision!=1329 or self.schema!=13 or self.manifest!=TARGET_MANIFEST or
            TARGET1389!=(TARGET_MANIFEST.relative_to(ROOT).as_posix(),'38bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6') or
            sha256(checked_path(TARGET_MANIFEST))!=TARGET1389[1]):raise Artifact13Error('target1389_pin_invalid')
        v=json.loads(TARGET_MANIFEST.read_bytes());old=prior.load_target();old.validate()
        actual={'server':prior.artifact_manifest(self.server),'frontend':prior.artifact_manifest(self.frontend)}
        total=sum(p.stat().st_size for d in (self.server,self.frontend) for p in d.rglob('*') if p.is_file())
        if (v.get('schema')!=13 or self.server!=checked_path(ROOT/Path(v['serverDll']).parent) or
            self.frontend!=checked_path(ROOT/v['frontend']) or any(not p.is_relative_to(ROOT/'.local/candidates') for p in (self.server,self.frontend)) or
            self.expected!=v['distributions'] or actual!=self.expected or len(actual['server'])!=22 or len(actual['frontend'])!=18 or
            v.get('fileCount')!=40 or v.get('totalBytes')!=7148383 or total!=7148383 or
            actual['server']!=old.expected['server'] or
            {k:v for k,v in actual['frontend'].items() if k!='app.js'}!={k:v for k,v in old.expected['frontend'].items() if k!='app.js'} or
            actual['frontend']['app.js']==old.expected['frontend']['app.js']):raise Artifact13Error('only_reviewed1329_bundle_change_allowed')
        return actual

def load_target():
    if sha256(checked_path(TARGET_MANIFEST))!='38bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6':raise Artifact13Error('target1389_pin_invalid')
    v=json.loads(TARGET_MANIFEST.read_bytes())
    d=Distribution1389(1329,13,checked_path(ROOT/Path(v['serverDll']).parent),checked_path(ROOT/v['frontend']),v['distributions'],TARGET_MANIFEST)
    d.validate();return d

def checked_operation(directory,operation,revision=1329):
    p=checked_path(operation)
    if p.parent!=directory/'versions' or not re.fullmatch('artifact13-'+str(revision)+'-[0-9a-f]{32}',p.name):raise Artifact13Error('operation1389_directory_invalid')
    return p

def owned_paths(directory,operation):
    token=checked_operation(directory,operation).name.removeprefix('artifact13-')
    return {kind:directory/('chain1389-'+token+'-'+kind+'-private.'+('json' if kind=='journal' else 'log')) for kind in ('journal','control','supervisor','worker')}

def inventory(original,operation=None):
    hashes=prior.immutable_hashes(original,exclude=operation)
    ignored=set(owned_paths(original.directory,operation).values()) if operation is not None else set()
    for p in original.directory.iterdir():
        if p.is_file() and p.name not in RUNTIME_FILES|{'manual-qa.json'} and p not in ignored:
            hashes[p.name]=sha256(checked_path(p))
    return hashes

def read_record(directory,operation,revision):
    operation=checked_operation(directory,operation,revision)
    path=checked_path(operation/OPERATION)
    if (operation/OPERATION_SEAL).read_text(encoding='ascii').strip()!=sha256(path):raise Artifact13Error('operation1389_seal_differs')
    return json.loads(path.read_bytes())

def require_stage_entries(operation,target):
    expected={name+'/'+p for name in ('server','frontend') for p in target.expected[name]}
    expected|={'previous-config.json','selected-config.json','preview-config.json',OPERATION,OPERATION_SEAL}
    directories={p.as_posix() for name in expected for p in Path(name).parents if p!=Path('.')}
    found_files=set();found_directories=set()
    for entry in operation.rglob('*'):
        checked_path(entry)
        relative=entry.relative_to(operation).as_posix()
        if entry.is_file():found_files.add(relative)
        elif entry.is_dir():found_directories.add(relative)
        else:raise Artifact13Error('operation1389_unknown_entry')
    if len(expected)!=45 or found_files!=expected or found_directories!=directories:raise Artifact13Error('operation1389_entry_set_changed')

def require_version_entries(original,parent,operation=None):
    versions=checked_path(original.directory/'versions')
    expected={'category-colors13-source969-recovery',parent.name}
    if operation is not None:expected.add(checked_operation(original.directory,operation).name)
    entries=list(versions.iterdir())
    if any(not checked_path(p).is_dir() for p in entries) or {p.name for p in entries}!=expected:raise Artifact13Error('source1209_version_set_changed')

def validate_stage(original,operation,record,previous_bytes,target,source_pin,kind):
    directory=original.directory
    require_stage_entries(operation,target)
    if (record.get('kind')!=kind or record.get('directory')!=str(directory) or record.get('operation')!=str(operation) or
        record.get('sourceManifestSha256')!=source_pin or record.get('targetManifestSha256')!=sha256(target.manifest) or
        record.get('targetArtifacts')!=target.expected):raise Artifact13Error('operation1389_stage_identity_invalid')
    files=record.get('configurationHashes',{})
    if set(files)!={'previous-config.json','selected-config.json','preview-config.json'}:raise Artifact13Error('operation1389_config_set_invalid')
    for name,digest in files.items():
        if sha256(checked_path(operation/name))!=digest:raise Artifact13Error('operation1389_config_hash_changed')
    previous=json.loads(previous_bytes);selected=json.loads((operation/'selected-config.json').read_bytes());preview=json.loads((operation/'preview-config.json').read_bytes())
    if ((operation/'previous-config.json').read_bytes()!=previous_bytes or set(selected)!=set(previous)|{'artifactDirectory'} or
        {k:v for k,v in selected.items() if k not in ('artifactDirectory','bundleSha256')}!={k:v for k,v in previous.items() if k not in ('artifactDirectory','bundleSha256')} or
        selected.get('artifactDirectory')!=str(operation) or selected.get('bundleSha256')!=target.expected['frontend']['app.js'] or
        selected.get('dllSha256')!=target.expected['server']['RackClick.Server.dll'] or set(preview)!=set(selected) or
        {k:v for k,v in preview.items() if k!='webPort'}!={k:v for k,v in selected.items() if k!='webPort'} or
        type(preview.get('webPort')) is not int or not 1<=preview['webPort']<=65535 or preview['webPort'] in (selected['webPort'],selected['pgPort'])):
        raise Artifact13Error('operation1389_only_two_config_fields_allowed')
    if {'server':prior.artifact_manifest(operation/'server'),'frontend':prior.artifact_manifest(operation/'frontend')}!=target.expected:raise Artifact13Error('operation1389_artifacts_changed')
    states=record.get('databaseStates',{})
    if set(states)!={'databases','postgresqlRoles'} or set(states['databases'])!={'primary','recovery969'}:raise Artifact13Error('operation1389_boundary_shape_invalid')
    for role,db,schema,tables in (('primary',original.database,13,prior.TABLES13),('recovery969',original.recovered,12,prior.TABLES12)):
        s=states['databases'][role]
        if (s.get('database')!=db.name or s.get('schema')!=schema or set(s.get('snapshot',{}))!=tables or
            not isinstance(s.get('history'),list) or len(s['history'])!=schema or not isinstance(s.get('identity'),str) or not isinstance(s.get('grants'),str)):
            raise Artifact13Error('operation1389_database_boundary_invalid')
    _safe_activity(record.get('activityBaseline'))
    if not isinstance(record.get('pointerSha256'),str) or not re.fullmatch('[0-9a-f]{64}',record['pointerSha256']):raise Artifact13Error('operation1389_pointer_digest_invalid')

def parent_bindings(directory,operation):
    journal=directory/('artifact13-'+operation.name.removeprefix('artifact13-')+'-journal-private.json')
    state=json.loads(checked_path(journal).read_bytes())
    if (state.get('state')!='committed' or state.get('leftRunning') is not False or
        state.get('applicationStopConfirmed') is not True or state.get('postgresqlStopConfirmed') is not True):raise Artifact13Error('parent1209_not_committed')
    return {name:sha256(path) for name,path in (('record',operation/OPERATION),('seal',operation/OPERATION_SEAL),('journal',journal))}

def validate_parent(original,parent,operation=None):
    parent=checked_operation(original.directory,parent,1209);r=read_record(original.directory,parent,1209)
    require_version_entries(original,parent,operation)
    validate_stage(original,parent,r,config_bytes(original.cfg),prior.load_target(),prior.SOURCE_SHA256,'artifact13-closed1089-to1209')
    found=prior.immutable_hashes(original,exclude=operation);prefix=parent.relative_to(original.directory).as_posix()+'/'
    if {k:v for k,v in found.items() if not k.startswith(prefix)}!=r.get('sourceInputHashes'):raise Artifact13Error('parent1209_input_universe_changed')
    return r,parent_bindings(original.directory,parent)

def load_operation(original,operation,parent,parent_record,bindings):
    operation=checked_operation(original.directory,operation);r=read_record(original.directory,operation,1329)
    validate_stage(original,operation,r,(parent/'selected-config.json').read_bytes(),load_target(),SOURCE_SHA256,'artifact13-closed1209-to1329')
    if (r.get('parentOperation')!=str(parent) or r.get('parentBindings')!=bindings or
        r.get('sourceInputHashes')!=inventory(original,operation) or r['pointerSha256']!=parent_record['pointerSha256']):
        raise Artifact13Error('operation1389_parent_binding_changed')
    return r

class Source1209(prior.Source13):
    """Reuse READ ONLY DB/catalog logic; explicitly validate both overlay stages."""
    def __init__(self,directory,pointer,*,real=False,operation=None,quiet=True):
        try:
            self.directory=prior.checked_candidate_directory(directory);self.pointer=checked_path(pointer);self.real=real
            if self.pointer!=(ROOT/'.local/qa-rc9/current.json' if real else self.directory/'artifact13-home/current.json'):raise Artifact13Error('explicit_source1209_profile_required')
            self.pointer_bytes=self.pointer.read_bytes()
            if json.loads(self.pointer_bytes)!={'directory':str(self.directory)}:raise Artifact13Error('source1209_pointer_differs')
            self.original=prior.original_metadata(self.directory);self.original_cfg=self.original.cfg
            self.db=self.original.database;self.recovered=self.original.recovered;self.recovery_cfg=self.original.recovery_cfg
            self.config_bytes=(self.directory/'manual-qa.json').read_bytes();self.cfg=json.loads(self.config_bytes)
            self.operation=checked_operation(self.directory,operation) if operation is not None else None
            art=checked_path(self.cfg.get('artifactDirectory',''))
            if re.fullmatch('artifact13-1329-[0-9a-f]{32}',art.name):
                if self.operation is not None and self.operation!=art:raise Artifact13Error('explicit_operation1389_differs')
                self.operation=checked_operation(self.directory,art)
            if self.operation is not None:
                hint=read_record(self.directory,self.operation,1329);self.parent_operation=checked_operation(self.directory,hint['parentOperation'],1209)
            else:self.parent_operation=checked_operation(self.directory,art,1209)
            self.parent_record,self.parent_bindings=validate_parent(self.original,self.parent_operation,self.operation)
            self.source_config_bytes=(self.parent_operation/'selected-config.json').read_bytes()
            self.source_cfg=json.loads(self.source_config_bytes);self.record=None;self.revision=1209
            if self.operation is not None:
                self.record=load_operation(self.original,self.operation,self.parent_operation,self.parent_record,self.parent_bindings)
                if self.config_bytes==(self.operation/'selected-config.json').read_bytes():self.revision=1329
                elif self.config_bytes!=self.source_config_bytes:raise Artifact13Error('source1209_selected_config_differs')
            elif self.config_bytes!=self.source_config_bytes:raise Artifact13Error('source1209_selected_config_differs')
            if (hashlib.sha256(self.pointer_bytes).hexdigest()!=self.parent_record['pointerSha256'] or real and self.cfg['webPort']!=52346):raise Artifact13Error('source1209_pointer_or_real_port_changed')
            self.art=art;self.baseline=prior.load_target();self.target=load_target()
            self.pg_bin=prior.toolchain()['postgresql'].parent;self.admin_passfile=checked_path(self.directory/'admin.pgpass')
            self.hashes=inventory(self.original,self.operation);self.inputs=[self.directory/n for n in self.hashes]
            if quiet:prior.app_stopped(self.directory,self.cfg['webPort'])
        except Artifact13Error:raise
        except Exception:raise Artifact13Error('source1209_chain_validation_failed') from None

    def unchanged(self,*,expected_config=None,hashes=None,quiet=True,operation=None):
        prior._validate_original_static(self.original)
        op=self.operation if operation is None else checked_operation(self.directory,operation)
        record,bindings=validate_parent(self.original,self.parent_operation,op)
        if record!=self.parent_record or bindings!=self.parent_bindings:raise Artifact13Error('source1209_parent_changed')
        if inventory(self.original,op)!=(self.hashes if hashes is None else hashes):raise Artifact13Error('source1209_input_universe_changed')
        if self.pointer.read_bytes()!=self.pointer_bytes or (self.directory/'manual-qa.json').read_bytes()!=(self.config_bytes if expected_config is None else expected_config):raise Artifact13Error('source1209_config_or_pointer_changed')
        if quiet:prior.app_stopped(self.directory,self.cfg['webPort'])

Source13=Source1209
