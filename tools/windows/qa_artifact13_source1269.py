"""Closed1089 ->1209 artifact overlay on a genuine1149 root; no DB mutation.

Original prepared metadata is checked independently of the selected overlay.
No temporary configuration rewrite or historical validator patch is performed.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'development/server/tests'))
from pg_support import NO_WINDOW,toolchain
from pg_lab_recovery import sha256
from qa_schema5_candidate import checked_path
from qa_schema6_source import Source4,PRIVATE_FILES,artifact_manifest,app_stopped
from qa_schema_candidate import snapshot
from qa_schema6_real_candidate import history
from qa_schema_switch import read_owner,activity_watermark,require_unchanged_activity
from qa_schema_switch import _safe_activity
from qa_category_colors13_source1149 import (load_target as load_baseline,load_source as load_recovery,
    TABLES11,TABLES12,NEW_TABLES,checked_candidate_directory,read_database)
from qa_category_colors13_candidate1149 import (Prepared1149,configuration,validate_seal,additive_copy,
    require_private_input_hashes,PREPARED,SEAL)

SOURCE_MANIFEST=ROOT/'evidence/s1-20261018/sesenta-tandas-1030-1089/CANDIDATA1089-02.json'
SOURCE_SHA256='c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c'
TARGET_MANIFEST=ROOT/'evidence/s1-20261018/sesenta-tandas-1150-1209/CANDIDATA1209-01.json'
TARGET1269=(TARGET_MANIFEST.relative_to(ROOT).as_posix(),'dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b')
TABLES13=TABLES12|NEW_TABLES
OPERATION='artifact13-prepared.json'
OPERATION_SEAL='artifact13-prepared.sha256'

class Artifact13Error(RuntimeError):
    def __init__(self,code,result=None):
        super().__init__(code);self.code,self.result=code,result

@dataclass(frozen=True)
class Distribution1269:
    revision:int
    schema:int
    server:Path
    frontend:Path
    expected:dict
    manifest:Path

    def validate(self):
        if (self.revision!=1209 or self.schema!=13 or self.manifest!=TARGET_MANIFEST or
            not isinstance(TARGET1269,tuple) or len(TARGET1269)!=2 or
            TARGET1269[0]!=TARGET_MANIFEST.relative_to(ROOT).as_posix() or
            not isinstance(TARGET1269[1],str) or not re.fullmatch('[0-9a-f]{64}',TARGET1269[1]) or
            sha256(checked_path(TARGET_MANIFEST))!=TARGET1269[1]):
            raise Artifact13Error('target1269_pin_invalid')
        v=json.loads(TARGET_MANIFEST.read_bytes())
        if (v.get('schema')!=13 or self.server!=checked_path(ROOT/Path(v['serverDll']).parent) or
            self.frontend!=checked_path(ROOT/v['frontend']) or self.expected!=v['distributions'] or
            any(not p.is_relative_to(ROOT/'.local/candidates') for p in (self.server,self.frontend))):
            raise Artifact13Error('target1269_distribution_identity_invalid')
        actual={'server':artifact_manifest(self.server),'frontend':artifact_manifest(self.frontend)}
        size=sum(p.stat().st_size for d in (self.server,self.frontend) for p in d.rglob('*') if p.is_file())
        baseline=load_baseline();baseline.validate()
        if (sha256(SOURCE_MANIFEST)!=SOURCE_SHA256 or actual!=self.expected or len(actual['server'])!=22 or
            len(actual['frontend'])!=18 or v.get('fileCount')!=40 or v.get('totalBytes')!=7146303 or size!=7146303 or
            actual['server']!=baseline.expected['server'] or
            {k:v for k,v in actual['frontend'].items() if k!='app.js'}!=
                {k:v for k,v in baseline.expected['frontend'].items() if k!='app.js'} or
            actual['frontend']['app.js']==baseline.expected['frontend']['app.js']):
            raise Artifact13Error('only_reviewed1209_bundle_change_allowed')
        return actual

def load_target():
    if (not isinstance(TARGET1269,tuple) or len(TARGET1269)!=2 or
        TARGET1269[0]!=TARGET_MANIFEST.relative_to(ROOT).as_posix() or
        not isinstance(TARGET1269[1],str) or not re.fullmatch('[0-9a-f]{64}',TARGET1269[1]) or
        sha256(checked_path(TARGET_MANIFEST))!=TARGET1269[1]):
        raise Artifact13Error('target1269_pin_invalid')
    v=json.loads(TARGET_MANIFEST.read_bytes())
    d=Distribution1269(1209,13,checked_path(ROOT/Path(v['serverDll']).parent),checked_path(ROOT/v['frontend']),v['distributions'],TARGET_MANIFEST)
    d.validate();return d

def config_bytes(cfg):
    return (json.dumps(cfg,indent=2)+'\n').encode('utf-8')

def _validate_original_static(candidate):
    """The sole config exception is replaced by exact reconstruction, never skipped."""
    directory,record=candidate.directory,candidate.record
    expected=record['inputHashes']
    if ('manual-qa.json' not in expected or
        hashlib.sha256(config_bytes(candidate.cfg)).hexdigest()!=expected['manual-qa.json']):
        raise Artifact13Error('original1149_config_reconstruction_differs')
    require_private_input_hashes(directory,{k:v for k,v in expected.items() if k!='manual-qa.json'})
    if (load_recovery().expected!=record['sourceArtifacts'] or
        {'server':artifact_manifest(directory/'server'),'frontend':artifact_manifest(directory/'frontend')}!=candidate.target.expected or
        {'server':artifact_manifest(directory/'versions/category-colors13-source969-recovery/server'),
         'frontend':artifact_manifest(directory/'versions/category-colors13-source969-recovery/frontend')}!=record['sourceArtifacts'] or
        json.loads((directory/'recovery969-manual-qa.json').read_bytes())!=candidate.recovery_cfg):
        raise Artifact13Error('original1149_artifacts_or_recovery_changed')
    validate_seal(directory,record)

def original_metadata(directory):
    """Reconstruct metadata only; never adopts or starts an existing Lab."""
    try:
        directory = checked_candidate_directory(directory)
        target = load_baseline()
        target.validate()
        record = validate_seal(directory)
        if (record.get('state') != 'prepared' or record.get('sourceRevision') != 969 or record.get('candidateRevision') != 1089 or
                record.get('sourceSchema') != 12 or record.get('candidateSchema') != 13 or
                record.get('directory') != str(directory) or record.get('targetArtifacts') != target.expected or
                record.get('targetManifestSha256') != sha256(target.manifest) or
                set(record.get('sourceSnapshot', {})) != TABLES12 or
                not additive_copy(record.get('sourceSnapshot'), record.get('sourceHistory'),
                                  record.get('candidateSnapshot'), record.get('candidateHistory'))):
            raise Artifact13Error('prepared1149_closed_identity_invalid')
        states = record.get('sourceDatabaseStates')
        if (not isinstance(states, dict) or set(states) != {'primary','recovery849'} or
                states['primary'].get('snapshot') != record['sourceSnapshot'] or
                states['primary'].get('history') != record['sourceHistory'] or
                states['primary'].get('revision') != 969 or states['recovery849'].get('revision') != 849 or
                states['primary'].get('schema') != 12 or set(states['primary'].get('snapshot',{})) != TABLES12 or
                states['recovery849'].get('schema') != 11 or set(states['recovery849'].get('snapshot',{})) != TABLES11 or
                {s.get('database') for s in states.values()} != set(record.get('sourceDatabaseNames',[]))):
            raise Artifact13Error('prepared1149_complete_source_states_invalid')
        meta = json.loads(checked_path(directory / 'lab.json').read_bytes())
        if (meta.get('path') != str(directory) or meta.get('host') != '127.0.0.1' or meta.get('postgresql') != '17' or
                directory.name != 'manual-qa-rc9-schema13-' + meta.get('id', '!') or
                type(meta.get('port')) is not int or not 1 <= meta['port'] <= 65535 or len(meta['databases']) != 2):
            raise Artifact13Error('prepared1149_cluster_metadata_invalid')
        by_label = {r['label']: r for r in meta['databases']}
        if set(by_label) != {'manual-qa-rc9', 'category-colors13-source969-compatible-recovery'}:
            raise Artifact13Error('prepared1149_database_membership_invalid')
        db = read_database(directory, by_label['manual-qa-rc9'], meta['port'])
        recovered = read_database(directory, by_label['category-colors13-source969-compatible-recovery'], meta['port'])
        source_cfg = json.loads(checked_path(directory / 'source-manual-qa.json').read_bytes())
        cfg = configuration(source_cfg, directory, meta['port'], db, target)
        old = load_recovery()
        recovery_cfg = configuration(source_cfg, directory, meta['port'], recovered, old,
                                     artifacts=directory / 'versions/category-colors13-source969-recovery')
        if (cfg['webPort'] in (cfg['pgPort'], source_cfg['pgPort']) or
                cfg['pgPort'] == source_cfg['pgPort'] or record['database'] != db.name or record['recoveredDatabase'] != recovered.name):
            raise Artifact13Error('prepared1149_connection_or_port_invalid')
        admin = checked_path(directory / 'admin.pgpass').read_text(encoding='utf-8').splitlines()
        if (len(admin) != 1 or not admin[0].startswith(f'127.0.0.1:{meta["port"]}:*:rc_lab_admin:') or
                checked_path(directory / 'init-password.txt').read_text(encoding='utf-8') != admin[0].split(':', 4)[-1] + '\n'):
            raise Artifact13Error('prepared1149_administrative_identity_invalid')
        new_secrets = {db.owner_password, db.runtime_password, recovered.owner_password, recovered.runtime_password,
                       admin[0].split(':', 4)[-1]}
        if (len({db.name, recovered.name}) != 2 or
                {db.name, recovered.name} & set(record['sourceDatabaseNames']) or len(new_secrets) != 5 or
                {hashlib.sha256(v.encode('utf-8')).hexdigest() for v in new_secrets} & set(record['sourcePostgresqlSecretDigests'])):
            raise Artifact13Error('prepared1149_postgresql_identity_reused')
        candidate = Prepared1149(directory, cfg, recovery_cfg, db, recovered, record, target)
        _validate_original_static(candidate)
        return candidate
    except Artifact13Error:
        raise
    except Exception:
        raise Artifact13Error('prepared1149_validation_failed') from None

def checked_operation(directory,operation):
    operation=checked_path(operation)
    if (operation.parent!=directory/'versions' or not re.fullmatch(r'artifact13-1209-[0-9a-f]{32}',operation.name)):
        raise Artifact13Error('operation1269_directory_invalid')
    return operation

def load_operation(directory,operation):
    operation=checked_operation(directory,operation)
    path=checked_path(operation/OPERATION)
    if (operation/OPERATION_SEAL).read_text(encoding='ascii').strip()!=sha256(path):
        raise Artifact13Error('operation1269_seal_differs')
    r=json.loads(path.read_bytes());target=load_target()
    if (r.get('kind')!='artifact13-closed1089-to1209' or r.get('directory')!=str(directory) or
        r.get('operation')!=str(operation) or r.get('sourceManifestSha256')!=SOURCE_SHA256 or
        r.get('targetManifestSha256')!=sha256(TARGET_MANIFEST) or r.get('targetArtifacts')!=target.expected):
        raise Artifact13Error('operation1269_identity_invalid')
    files=r.get('configurationHashes')
    if not isinstance(files,dict) or set(files)!={'previous-config.json','selected-config.json','preview-config.json'}:
        raise Artifact13Error('operation1269_configuration_set_invalid')
    for name,digest in files.items():
        if sha256(checked_path(operation/name))!=digest:
            raise Artifact13Error('operation1269_configuration_changed')
    previous=json.loads((operation/'previous-config.json').read_bytes())
    selected=json.loads((operation/'selected-config.json').read_bytes())
    preview=json.loads((operation/'preview-config.json').read_bytes())
    if (set(selected)!=set(previous)|{'artifactDirectory'} or
        {k:v for k,v in selected.items() if k not in ('artifactDirectory','bundleSha256')}!=
            {k:v for k,v in previous.items() if k not in ('artifactDirectory','bundleSha256')} or
        selected.get('artifactDirectory')!=str(operation) or selected.get('bundleSha256')!=target.expected['frontend']['app.js'] or
        selected.get('dllSha256')!=target.expected['server']['RackClick.Server.dll'] or
        set(preview)!=set(selected) or {k:v for k,v in preview.items() if k!='webPort'}!=
            {k:v for k,v in selected.items() if k!='webPort'} or
        type(preview.get('webPort')) is not int or not 1<=preview['webPort']<=65535 or
        preview['webPort'] in (selected['webPort'],selected['pgPort'])):
        raise Artifact13Error('operation1269_only_two_config_fields_allowed')
    if {'server':artifact_manifest(operation/'server'),'frontend':artifact_manifest(operation/'frontend')}!=target.expected:
        raise Artifact13Error('operation1269_artifacts_changed')
    original=original_metadata(directory)
    if ((operation/'previous-config.json').read_bytes()!=config_bytes(original.cfg) or
        r.get('sourceInputHashes')!=immutable_hashes(original,exclude=operation) or
        r.get('pointerSha256') is None or
        set(r.get('databaseStates',{}))!={'databases','postgresqlRoles'} or
        set(r['databaseStates']['databases'])!={'primary','recovery969'}):
        raise Artifact13Error('operation1269_original_binding_differs')
    _safe_activity(r.get('activityBaseline'))
    for role,db,schema,tables in (('primary',original.database,13,TABLES13),('recovery969',original.recovered,12,TABLES12)):
        state=r['databaseStates']['databases'][role]
        if (state.get('database')!=db.name or state.get('schema')!=schema or set(state.get('snapshot',{}))!=tables or
            not isinstance(state.get('history'),list) or len(state['history'])!=schema or
            not isinstance(state.get('identity'),str) or not isinstance(state.get('grants'),str)):
            raise Artifact13Error('operation1269_database_boundary_invalid')
    return r

def immutable_hashes(original,*,exclude=None):
    directory=original.directory
    paths=[directory/n for n in original.record['inputHashes'] if n!='manual-qa.json']
    paths += [directory/PREPARED,directory/SEAL]
    paths += [p for d in (directory/'server',directory/'frontend',directory/'versions')
              for p in d.rglob('*') if p.is_file() and (exclude is None or not p.is_relative_to(exclude))]
    return {p.relative_to(directory).as_posix():sha256(checked_path(p)) for p in sorted(set(paths))}

class Source13(Source4):
    """Current39/37 rows are deliberately independent from original1149 snapshots."""
    def __init__(self,directory,pointer,*,real=False,quiet=True):
        try:
            self.directory=checked_candidate_directory(directory);self.pointer=checked_path(pointer);self.real=real
            permitted=ROOT/'.local/qa-rc9/current.json' if real else self.directory/'artifact13-home/current.json'
            if self.pointer!=permitted:
                raise Artifact13Error('explicit_source13_profile_required')
            self.pointer_bytes=self.pointer.read_bytes()
            if json.loads(self.pointer_bytes)!={'directory':str(self.directory)}:
                raise Artifact13Error('source13_pointer_differs')
            self.original=original_metadata(self.directory)
            self.original_cfg=self.original.cfg;self.db=self.original.database;self.recovered=self.original.recovered
            self.recovery_cfg=self.original.recovery_cfg;self.meta=json.loads((self.directory/'lab.json').read_bytes())
            self.config_bytes=(self.directory/'manual-qa.json').read_bytes();self.cfg=json.loads(self.config_bytes)
            if real and self.cfg['webPort']!=52346:
                raise Artifact13Error('source13_real_web_port_differs')
            self.operation=None;self.record=None;self.revision=1089
            if self.config_bytes!=config_bytes(self.original_cfg):
                self.operation=checked_operation(self.directory,self.cfg.get('artifactDirectory',''))
                self.record=load_operation(self.directory,self.operation)
                if hashlib.sha256(self.pointer_bytes).hexdigest()!=self.record['pointerSha256']:
                    raise Artifact13Error('source13_pointer_bytes_changed')
                if ((self.operation/'previous-config.json').read_bytes()!=config_bytes(self.original_cfg) or
                    self.config_bytes!=(self.operation/'selected-config.json').read_bytes()):
                    raise Artifact13Error('source13_selected_config_differs')
                self.revision=1209
            self.art=checked_path(self.cfg.get('artifactDirectory',self.directory))
            self.baseline=load_baseline();self.target=load_target()
            self.pg_bin=toolchain()['postgresql'].parent;self.admin_passfile=checked_path(self.directory/'admin.pgpass')
            self.hashes=immutable_hashes(self.original)
            self.inputs=[self.directory/n for n in self.hashes]
            if quiet:app_stopped(self.directory,self.cfg['webPort'])
        except Artifact13Error:raise
        except Exception:raise Artifact13Error('source13_static_validation_failed') from None

    def unchanged(self,*,expected_config=None,hashes=None,quiet=True):
        _validate_original_static(self.original)
        expected_config=self.config_bytes if expected_config is None else expected_config
        if (self.pointer.read_bytes()!=self.pointer_bytes or
            (self.directory/'manual-qa.json').read_bytes()!=expected_config):
            raise Artifact13Error('source13_config_or_pointer_changed')
        for name,digest in (self.hashes if hashes is None else hashes).items():
            p=checked_path(self.directory/name)
            if not p.is_relative_to(self.directory) or sha256(p)!=digest:
                raise Artifact13Error('source13_immutable_inputs_changed')
        if quiet:app_stopped(self.directory,self.cfg['webPort'])

    def sql(self,query):return read_owner(self.directory,self.original_cfg,query)

    def admin_read(self,query):
        p=subprocess.run([str(self.pg_bin/'psql.exe'),'-X','-q','-w','-At','-v','ON_ERROR_STOP=1','-h','127.0.0.1',
            '-p',str(self.original_cfg['pgPort']),'-U','rc_lab_admin','-d','postgres'],
            input='BEGIN READ ONLY;'+query+';COMMIT;',text=True,encoding='utf-8',capture_output=True,
            env=dict(os.environ,PGCLIENTENCODING='UTF8',PGPASSFILE=str(self.admin_passfile)),timeout=90,creationflags=NO_WINDOW)
        if p.returncode:raise Artifact13Error('source13_admin_read_unconfirmed')
        return p.stdout.strip()

    def database_states(self):
        self.original.check_cluster_identity()
        states={}
        for role,db,cfg,art,schema,tables in (
            ('primary',self.db,self.original_cfg,self.directory,13,TABLES13),
            ('recovery969',self.recovered,self.recovery_cfg,self.directory/'versions/category-colors13-source969-recovery',12,TABLES12)):
            read=lambda q:read_owner(self.directory,cfg,q)
            rows=snapshot(read)
            if set(rows)!=tables:raise Artifact13Error('source13_table_sets_differ')
            identity=read("SELECT row_to_json(t) FROM (SELECT oid,datname,datdba,datacl::text FROM pg_database WHERE datname=current_database())t")
            grants=read("SELECT row_to_json(t) FROM (SELECT schemaname,tablename,tableowner,c.relacl::text FROM pg_tables t JOIN pg_class c ON c.relname=t.tablename JOIN pg_namespace n ON n.oid=c.relnamespace AND n.nspname=t.schemaname WHERE schemaname='public' ORDER BY tablename)t;SELECT row_to_json(t) FROM (SELECT nspname,nspowner,nspacl::text FROM pg_namespace WHERE nspname='public')t")
            states[role]=dict(database=db.name,schema=schema,snapshot=rows,history=history(read,art/'server',schema),identity=identity,grants=grants)
        names=','.join("'"+n+"'" for n in ('rc_lab_admin',self.db.owner,self.db.runtime,self.recovered.owner,self.recovered.runtime))
        roles=self.admin_read('SELECT row_to_json(t) FROM (SELECT oid,rolname,rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,rolreplication,rolconnlimit,rolpassword,rolvaliduntil,rolbypassrls FROM pg_authid WHERE rolname IN ('+names+') ORDER BY rolname)t;SELECT row_to_json(t) FROM (SELECT roleid,member,grantor,admin_option,inherit_option,set_option FROM pg_auth_members ORDER BY roleid,member,grantor)t;SELECT row_to_json(t) FROM (SELECT setdatabase,setrole,setconfig FROM pg_db_role_setting ORDER BY setdatabase,setrole)t')
        return dict(databases=states,postgresqlRoles=roles)
