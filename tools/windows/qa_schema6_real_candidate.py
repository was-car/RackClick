"""New-cluster RC9 schema4 -> approved6/7 copy. No pointer or activation changes."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'development/server/tests'))
from pg_support import Lab, NO_WINDOW
from pg_lab_recovery import sha256
from qa_schema5_candidate import checked_path, runtime_permissions, SQL5, SQL6
from qa_schema_candidate import snapshot
from qa_schema5_switch import atomic_bytes
from qa_schema6_source import Source4, SOURCE_MAP, PRIVATE_FILES, artifact_manifest

APPROVED = {
    6: ('evidence/s1-20261017/tres-tandas-54/CANDIDATA6.json', '2b4dd5f20ceb2b43d208716c021617c6933097c48a2da3b6b744259bd3db83eb'),
    7: ('evidence/s1-20261017/quince-tandas-55-59/CANDIDATA7.json', 'c5447d77c903bb5a9fc51d7add3ba6f3295ae37904e69a0db08ab26d9716d332'),
}


class CopyError(RuntimeError):
    def __init__(self, code, candidate=None):
        super().__init__(code); self.code, self.candidate = code, candidate


def save(path, value):
    atomic_bytes(path, (json.dumps(value,indent=2)+'\n').encode('utf-8'))


@dataclass
class Target:
    schema: int
    server: Path
    frontend: Path
    expected: dict
    manifest_path: Path

    def validate(self):
        approved = APPROVED.get(self.schema)
        if not approved or self.manifest_path != ROOT/approved[0] or sha256(checked_path(self.manifest_path)) != approved[1]:
            raise CopyError('target_manifest_not_approved')
        value = json.loads(self.manifest_path.read_text(encoding='utf-8'))
        if self.expected != value['distributions']: raise CopyError('target_maps_changed')
        if checked_path(self.server) != ROOT/Path(value['serverDll']).parent or checked_path(self.frontend) != ROOT/value['frontend']:
            raise CopyError('target_artifact_path_changed')
        actual = {'server':artifact_manifest(self.server),'frontend':artifact_manifest(self.frontend)}
        if actual != self.expected: raise CopyError('target_complete_artifacts_differ')
        sqls = [n for n in sorted(actual['server']) if n.startswith('database/') and n.endswith('.sql')]
        if [int(Path(n).name[:3]) for n in sqls] != list(range(1,self.schema+1)):
            raise CopyError('target_sql_sequence_differs')
        for name,value in SOURCE_MAP['server'].items():
            if name.startswith('database/') and actual['server'].get(name) != value:
                raise CopyError('target_historical_sql_differs')
        if actual['server'].get('database/005-audit-context.sql') != SQL5 or actual['server'].get('database/006-audit-state-intent.sql') != SQL6:
            raise CopyError('target_sql005006_differ')
        return actual


def load_target(schema=6):
    approved = APPROVED.get(schema)
    if not approved: raise CopyError('target_schema_not_approved')
    path=ROOT/approved[0]
    if sha256(checked_path(path)) != approved[1]: raise CopyError('target_manifest_not_approved')
    value=json.loads(path.read_text(encoding='utf-8'))
    target=Target(schema, ROOT/Path(value['serverDll']).parent, ROOT/value['frontend'], value['distributions'], path)
    target.validate(); return target


def history(sql, server, schema):
    values=[json.loads(r) for r in sql('SELECT row_to_json(t) FROM schema_migration t ORDER BY version').splitlines()]
    files=sorted((server/'database').glob('*.sql'))
    if [r['version'] for r in values] != list(range(1,schema+1)) or len(files)!=schema:
        raise CopyError('target_history_sequence_differs')
    for row,path in zip(values,files):
        digest=hashlib.sha256(path.read_bytes().decode('utf-8-sig').encode()).hexdigest()
        if row['digest'].lower()!=digest: raise CopyError('target_history_digest_differs')
    return values


@dataclass
class Candidate:
    lab: object
    target: object
    database: object=None
    recovered: object=None
    cfg: dict=None
    journal: Path=None

    def close(self): self.lab.close()

    def validate_artifacts(self):
        expected=self.target.expected
        actual={'server':artifact_manifest(self.lab.directory/'server'),'frontend':artifact_manifest(self.lab.directory/'frontend')}
        if actual!=expected: raise CopyError('candidate_complete_artifacts_differ')


def prepare(source, target):
    """Caller exclusively owns running source PG and keeps its APP stopped.

    Always allocates a NEW cluster,6/7 database and separate compatible4 database.
    Failed outputs stay private. Caller must close a successful Candidate.
    """
    if not isinstance(source,Source4): raise CopyError('explicit_validated_source_required')
    source.unchanged(); target.validate(); old_history=source.check_schema(); before=snapshot(source.sql)
    candidate=Candidate(Lab(f'manual-qa-rc9-schema{target.schema}'),target)
    lab=candidate.lab; candidate.journal=lab.directory/'schema6-copy-private.json'
    state=dict(state='allocated',sourceDirectory=str(source.directory),sourceDatabase=source.db.name,
        sourceSchema=4,candidateSchema=target.schema,sourceSnapshot=before,sourceHistory=old_history,
        sourceInputHashes=source.hashes,sourceArtifacts=SOURCE_MAP,targetArtifacts=target.expected,
        targetManifestSha256=sha256(target.manifest_path),activated=False,utc=datetime.now(timezone.utc).isoformat())
    save(candidate.journal,state)
    try:
        if lab.port==source.cfg['webPort']: raise CopyError('candidate_pg_port_collision')
        for name in ('server','frontend'): shutil.copytree(getattr(target,name),lab.directory/name)
        prior=lab.directory/'versions/schema4-recovery'
        for name in ('server','frontend'): shutil.copytree(source.art/name,prior/name)
        for name in PRIVATE_FILES: shutil.copyfile(source.directory/name,lab.directory/name)
        shutil.copyfile(source.directory/'manual-qa.json',lab.directory/'source-manual-qa.json')
        archive=lab.directory/'source-schema4.dump'
        with (lab.directory/'dump-private.log').open('xb') as output:
            code=subprocess.run([str(source.pg_bin/'pg_dump.exe'),'-w','-h','127.0.0.1','-p',str(source.cfg['pgPort']),
                '-U',source.db.owner,'-d',source.db.name,'-Fc','-f',str(archive)],env=source.environment(),
                stdin=subprocess.DEVNULL,stdout=output,stderr=output,timeout=180,creationflags=NO_WINDOW).returncode
        if code: raise CopyError('source_dump_failed')
        state.update(state='backed-up',dumpSha256=sha256(archive),dumpBytes=archive.stat().st_size);save(candidate.journal,state)
        lab.start()
        def restore(label):
            if sha256(archive)!=state['dumpSha256']: raise CopyError('private_dump_changed')
            db=lab.create_database(label)
            env=lab.environment();env['PGPASSFILE']=str(db.directory/'owner.pgpass')
            with (db.directory/'restore-private.log').open('xb') as output:
                code=subprocess.run([str(lab.pg_bin/'pg_restore.exe'),'-w','-h','127.0.0.1','-p',str(lab.port),
                    '-U',db.owner,'-d',db.name,'--single-transaction','--exit-on-error','--no-owner','--no-acl',str(archive)],
                    env=env,stdin=subprocess.DEVNULL,stdout=output,stderr=output,timeout=180,creationflags=NO_WINDOW).returncode
            if code: raise CopyError('new_database_restore_failed')
            lab.grant_runtime(db)
            if snapshot(lambda q:lab.sql(db,q,sensitive=True))!=before: raise CopyError('restored_rows_differ')
            return db
        candidate.database=restore('manual-qa-rc9'); candidate.recovered=restore('schema4-compatible-recovery')
        db=candidate.database; sql=lambda q:lab.sql(db,q,sensitive=True)
        env=lab.environment();env['ConnectionStrings__RackClick']=db.connection(lab.port,runtime=False)
        with (lab.directory/'migration-private.log').open('xb') as output:
            code=subprocess.run([str(lab.dotnet),str(lab.directory/'server/RackClick.Server.dll'),'--migrate'],
                cwd=lab.directory/'server',env=env,stdin=subprocess.DEVNULL,stdout=output,stderr=output,
                timeout=90,creationflags=NO_WINDOW).returncode
        if code: raise CopyError('new_candidate_migration_failed')
        lab.grant_runtime(db); runtime_permissions(lab,db)
        after=snapshot(sql); found=history(sql,lab.directory/'server',target.schema)
        old_rows={k:v for k,v in before.items() if k!='schema_migration'}
        compatible={k:v for k,v in after.items() if k not in ('schema_migration','audit_context','audit_context_object')}
        if (compatible!=old_rows or set(after)!=set(before)|{'audit_context','audit_context_object'} or
                found[:4]!=old_history or any(after[k]['rows'] for k in ('audit_context','audit_context_object'))):
            raise CopyError('migrated_rows_history_or_empty_context_differ')
        cfg=dict(source.cfg);cfg.pop('artifactDirectory',None)
        cfg.update(directory=str(lab.directory),pgPort=lab.port,database=db.name,connection=db.connection(lab.port),
            dllSha256=target.expected['server']['RackClick.Server.dll'],bundleSha256=target.expected['frontend']['app.js'])
        candidate.cfg=cfg;save(lab.directory/'manual-qa.json',cfg)
        recovery_cfg=dict(cfg,database=candidate.recovered.name,connection=candidate.recovered.connection(lab.port),
            artifactDirectory=str(prior),dllSha256=SOURCE_MAP['server']['RackClick.Server.dll'],bundleSha256=SOURCE_MAP['frontend']['app.js'])
        save(lab.directory/'recovery4-manual-qa.json',recovery_cfg)
        candidate.validate_artifacts();target.validate();source.unchanged()
        if snapshot(source.sql)!=before or any(sha256(source.directory/n)!=sha256(lab.directory/n) for n in PRIVATE_FILES):
            raise CopyError('source_rows_or_copied_private_files_changed')
        identities={(d.name,d.owner,d.runtime) for d in (source.db,db,candidate.recovered)}
        secrets={p for d in (source.db,db,candidate.recovered) for p in (d.owner_password,d.runtime_password)}
        if len(identities)!=3 or len(secrets)!=6: raise CopyError('postgresql_identity_reused')
        state.update(state='prepared',database=db.name,recoveredDatabase=candidate.recovered.name,candidateSnapshot=after,
            configSha256=sha256(lab.directory/'manual-qa.json'),sourcePreserved=True)
        save(candidate.journal,state);return candidate
    except Exception:
        state['failedAfter']=state['state'];state['state']='failed'
        journal_ok=False
        try:save(candidate.journal,state);journal_ok=True
        except Exception:pass
        try:candidate.close()
        except Exception:raise CopyError('copy_failed_stop_unconfirmed',candidate) from None
        if not journal_ok:raise CopyError('copy_failed_journal_unconfirmed',candidate) from None
        raise CopyError('copy_failed_private_outputs_retained',candidate) from None
