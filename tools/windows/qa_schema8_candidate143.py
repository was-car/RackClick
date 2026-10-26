"""Private new-cluster copy128/schema7 ->143/schema8 plus compatible recovery7.

The caller owns the quiet source PG and the profile lock. Never activates a
pointer, authenticates to the application, deletes a branch or reuses a Lab.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import Lab, NO_WINDOW, toolchain
from pg_lab_recovery import sha256
from qa_schema5_candidate import checked_path
from qa_schema5_switch import atomic_bytes
from qa_schema_candidate import snapshot
from qa_schema6_real_candidate import history
from qa_schema6_source import PRIVATE_FILES, artifact_manifest
from qa_schema_switch import activity_watermark, require_unchanged_activity, read_owner
from qa_schema8_source143 import (Schema8Error, Source128, NEW_TABLES, load_source, load_target,
                                checked_candidate_directory, read_database)

PREPARED = 'schema8-prepared.json'
SEAL = 'schema8-prepared.sha256'


def save(path, value):
    atomic_bytes(path, (json.dumps(value, indent=2) + '\n').encode('utf-8'))


def configuration(source_cfg, directory, port, db, distribution, *, artifacts=None):
    cfg = dict(source_cfg)
    cfg.pop('artifactDirectory', None)
    cfg.update(directory=str(directory), pgPort=port, database=db.name, connection=db.connection(port),
               dllSha256=distribution.expected['server']['RackClick.Server.dll'],
               bundleSha256=distribution.expected['frontend']['app.js'])
    if artifacts is not None:
        cfg['artifactDirectory'] = str(artifacts)
    return cfg


@dataclass
class Prepared143:
    directory: Path
    cfg: dict
    recovery_cfg: dict
    database: object
    recovered: object
    record: dict
    target: object
    lab: object = None

    @property
    def journal(self):
        return self.directory / 'schema8-copy-private.json'

    def close(self):
        if self.lab is not None:
            self.lab.close()

    def sql(self, query, *, recovery=False):
        return read_owner(self.directory, self.recovery_cfg if recovery else self.cfg, query)

    def validate_static(self):
        self.target.validate()
        if load_source().expected != self.record['sourceArtifacts']:
            raise Schema8Error('prepared143_source_distribution_changed')
        expected = self.record['inputHashes']
        if {name: sha256(checked_path(self.directory / name)) for name in expected} != expected:
            raise Schema8Error('prepared143_private_inputs_changed')
        if {'server': artifact_manifest(self.directory / 'server'),
                'frontend': artifact_manifest(self.directory / 'frontend')} != self.target.expected:
            raise Schema8Error('prepared143_target_artifacts_changed')
        prior = self.directory / 'versions/schema7-recovery'
        if {'server': artifact_manifest(prior / 'server'), 'frontend': artifact_manifest(prior / 'frontend')} != self.record['sourceArtifacts']:
            raise Schema8Error('prepared143_recovery7_artifacts_changed')
        if (json.loads((self.directory / 'manual-qa.json').read_bytes()) != self.cfg or
                json.loads((self.directory / 'recovery7-manual-qa.json').read_bytes()) != self.recovery_cfg):
            raise Schema8Error('prepared143_configuration_changed')
        validate_seal(self.directory, self.record)

    def check_cluster_identity(self):
        # Bind the running PG to its exact new data directory before DB reads.
        env = dict(os.environ, PGCLIENTENCODING='UTF8', PGPASSFILE=str(self.directory / 'admin.pgpass'))
        response = subprocess.run([str(toolchain()['postgresql'].parent / 'psql.exe'), '-X', '-q', '-w', '-At',
            '-v', 'ON_ERROR_STOP=1', '-h', '127.0.0.1', '-p', str(self.cfg['pgPort']), '-U', 'rc_lab_admin', '-d', 'postgres'],
            input="BEGIN READ ONLY;SELECT current_setting('data_directory');COMMIT;", text=True, encoding='utf-8',
            capture_output=True, env=env, timeout=30, creationflags=NO_WINDOW)
        if response.returncode or checked_path(response.stdout.strip()) != checked_path(self.directory / 'data'):
            raise Schema8Error('prepared143_running_cluster_differs')
        for db, cfg in ((self.database, self.cfg), (self.recovered, self.recovery_cfg)):
            if read_owner(self.directory, cfg, 'SELECT current_database();SELECT current_user;SHOW port') != f'{db.name}\n{db.owner}\n{cfg["pgPort"]}':
                raise Schema8Error('prepared143_running_database_differs')

    def verify_rows_and_activity(self):
        self.check_cluster_identity()
        require_unchanged_activity(self.directory, self.cfg, self.record['candidateActivityBaseline'])
        if (snapshot(self.sql) != self.record['candidateSnapshot'] or
                history(self.sql, self.directory / 'server', 8) != self.record['candidateHistory'] or
                snapshot(lambda q: self.sql(q, recovery=True)) != self.record['sourceSnapshot'] or
                history(lambda q: self.sql(q, recovery=True), self.directory / 'versions/schema7-recovery/server', 7) != self.record['sourceHistory']):
            raise Schema8Error('prepared143_rows_or_history_changed')
        require_unchanged_activity(self.directory, self.cfg, self.record['candidateActivityBaseline'])


def validate_seal(directory, record=None):
    path = checked_path(directory / PREPARED)
    digest = checked_path(directory / SEAL).read_text(encoding='ascii').strip()
    if digest != sha256(path):
        raise Schema8Error('prepared143_record_seal_differs')
    found = json.loads(path.read_bytes())
    if record is not None and found != record:
        raise Schema8Error('prepared143_record_changed')
    return found


def load_prepared(directory, target=None):
    """Reconstruct metadata only; never adopts or starts an existing Lab."""
    try:
        directory = checked_candidate_directory(directory)
        target = target or load_target()
        target.validate()
        record = validate_seal(directory)
        if (record.get('state') != 'prepared' or record.get('sourceRevision') != 128 or
                record.get('sourceSchema') != 7 or record.get('candidateSchema') != 8 or
                record.get('directory') != str(directory) or record.get('targetArtifacts') != target.expected or
                record.get('targetManifestSha256') != sha256(target.manifest)):
            raise Schema8Error('prepared143_closed_identity_invalid')
        meta = json.loads(checked_path(directory / 'lab.json').read_bytes())
        if (meta.get('path') != str(directory) or meta.get('host') != '127.0.0.1' or meta.get('postgresql') != '17' or
                directory.name != 'manual-qa-rc9-schema8-' + meta.get('id', '!') or
                type(meta.get('port')) is not int or not 1 <= meta['port'] <= 65535 or len(meta['databases']) != 2):
            raise Schema8Error('prepared143_cluster_metadata_invalid')
        by_label = {r['label']: r for r in meta['databases']}
        if set(by_label) != {'manual-qa-rc9', 'schema7-compatible-recovery'}:
            raise Schema8Error('prepared143_database_membership_invalid')
        db = read_database(directory, by_label['manual-qa-rc9'], meta['port'])
        recovered = read_database(directory, by_label['schema7-compatible-recovery'], meta['port'])
        source_cfg = json.loads(checked_path(directory / 'source-manual-qa.json').read_bytes())
        cfg = configuration(source_cfg, directory, meta['port'], db, target)
        old = load_source()
        recovery_cfg = configuration(source_cfg, directory, meta['port'], recovered, old,
                                     artifacts=directory / 'versions/schema7-recovery')
        if (cfg['webPort'] in (cfg['pgPort'], source_cfg['pgPort']) or
                cfg['pgPort'] == source_cfg['pgPort'] or record['database'] != db.name or record['recoveredDatabase'] != recovered.name):
            raise Schema8Error('prepared143_connection_or_port_invalid')
        if len({db.name, recovered.name, source_cfg['database']}) != 3 or len({db.owner_password, db.runtime_password, recovered.owner_password, recovered.runtime_password}) != 4:
            raise Schema8Error('prepared143_postgresql_identity_reused')
        candidate = Prepared143(directory, cfg, recovery_cfg, db, recovered, record, target)
        candidate.validate_static()
        return candidate
    except Schema8Error:
        raise
    except Exception:
        raise Schema8Error('prepared143_validation_failed') from None


def runtime_permissions(lab, db):
    """Check new runtime permissions; never assume old audit tables are empty."""
    tables = ','.join("'" + n + "'" for n in sorted(NEW_TABLES))
    result = lab.sql(db, f"""BEGIN READ ONLY;
        SELECT bool_and(NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole)
          FROM pg_roles WHERE rolname IN ('{db.owner}','{db.runtime}');
        SELECT NOT has_schema_privilege('{db.runtime}','public','CREATE');
        SELECT NOT has_database_privilege('{db.runtime}',current_database(),'CREATE');
        SELECT count(*)=12 AND bool_and(has_table_privilege('{db.runtime}',tablename,privilege))
          FROM pg_tables CROSS JOIN unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE']) privilege
          WHERE schemaname='public' AND tablename IN ({tables});
        SELECT count(*)=0 FROM pg_tables WHERE schemaname='public' AND tableowner<>'{db.owner}';
        COMMIT;""", sensitive=True)
    if [v for v in result.splitlines() if v not in ('BEGIN', 'COMMIT')] != ['t'] * 5:
        raise Schema8Error('prepared143_runtime_permissions_differ')


def verify_source(source, record):
    source.unchanged(pointer=False)
    if source.hashes != record['sourceInputHashes'] or source.config_bytes != (Path(record['directory']) / 'source-manual-qa.json').read_bytes():
        raise Schema8Error('source128_differs_from_dump_inputs')
    require_unchanged_activity(source.directory, source.cfg, record['sourceActivityBaseline'])
    if snapshot(source.sql) != record['sourceSnapshot'] or source.check_schema7() != record['sourceHistory']:
        raise Schema8Error('source128_rows_or_history_changed')
    require_unchanged_activity(source.directory, source.cfg, record['sourceActivityBaseline'])


def prepare(source, target):
    if not isinstance(source, Source128) or target.schema != 8:
        raise Schema8Error('explicit_closed_source128_target143_required')
    source.unchanged(); target.validate()
    old_history = source.check_schema7()
    # Capture before *all* source snapshots/dump; source reads must not assign XID.
    source_activity = activity_watermark(source.directory, source.cfg)
    before = snapshot(source.sql)
    if set(before) & NEW_TABLES:
        raise Schema8Error('source128_unexpected_schema8_tables')
    lab = Lab('manual-qa-rc9-schema8')
    candidate = Prepared143(lab.directory, None, None, None, None, {}, target, lab)
    state = dict(state='allocated', sourceRevision=128, sourceSchema=7, candidateSchema=8,
        directory=str(lab.directory), sourceDirectory=str(source.directory), sourcePointer=str(source.pointer),
        sourcePointerBytes=source.pointer_bytes.decode('utf-8'), sourceInputHashes=source.hashes,
        sourceSnapshot=before, sourceHistory=old_history, sourceActivityBaseline=source_activity,
        sourceArtifacts=source.baseline.expected, targetArtifacts=target.expected,
        targetManifestSha256=sha256(target.manifest), activated=False,
        utc=datetime.now(timezone.utc).isoformat())
    save(candidate.journal, state)
    try:
        if lab.port in (source.cfg['webPort'], source.cfg['pgPort']):
            raise Schema8Error('candidate143_pg_port_collision')
        for name in ('server', 'frontend'):
            shutil.copytree(getattr(target, name), lab.directory / name)
            shutil.copytree(source.art / name, lab.directory / 'versions/schema7-recovery' / name)
        for name in PRIVATE_FILES:
            shutil.copyfile(source.directory / name, lab.directory / name)
        shutil.copyfile(source.directory / 'manual-qa.json', lab.directory / 'source-manual-qa.json')
        archive = lab.directory / 'source-schema7.dump'
        with (lab.directory / 'dump-private.log').open('xb') as output:
            code = subprocess.run([str(source.pg_bin / 'pg_dump.exe'), '-w', '-h', '127.0.0.1', '-p', str(source.cfg['pgPort']),
                '-U', source.db.owner, '-d', source.db.name, '-Fc', '-f', str(archive)], env=source.environment(),
                stdin=subprocess.DEVNULL, stdout=output, stderr=output, timeout=180, creationflags=NO_WINDOW).returncode
        if code:
            raise Schema8Error('source128_dump_failed')
        state.update(state='backed-up', dumpSha256=sha256(archive), dumpBytes=archive.stat().st_size)
        save(candidate.journal, state)
        lab.start()

        def restore(label):
            if sha256(archive) != state['dumpSha256']:
                raise Schema8Error('source128_private_dump_changed')
            db = lab.create_database(label)
            env = lab.environment(); env['PGPASSFILE'] = str(db.directory / 'owner.pgpass')
            with (db.directory / 'restore-private.log').open('xb') as output:
                code = subprocess.run([str(lab.pg_bin / 'pg_restore.exe'), '-w', '-h', '127.0.0.1', '-p', str(lab.port),
                    '-U', db.owner, '-d', db.name, '--single-transaction', '--exit-on-error', '--no-owner', '--no-acl', str(archive)],
                    env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=output, timeout=180, creationflags=NO_WINDOW).returncode
            if code:
                raise Schema8Error('candidate143_new_restore_failed')
            lab.grant_runtime(db)
            sql = lambda q: lab.sql(db, 'BEGIN READ ONLY;\n' + q + ';\nCOMMIT;', sensitive=True)
            def read(q):
                return '\n'.join(v for v in sql(q).splitlines() if v not in ('BEGIN', 'COMMIT'))
            if snapshot(read) != before or history(read, source.art / 'server', 7) != old_history:
                raise Schema8Error('candidate143_restored_rows_or_history_differ')
            return db

        candidate.database = db = restore('manual-qa-rc9')
        candidate.recovered = restore('schema7-compatible-recovery')
        env = lab.environment(); env['ConnectionStrings__RackClick'] = db.connection(lab.port, runtime=False)
        with (lab.directory / 'migration-private.log').open('xb') as output:
            code = subprocess.run([str(lab.dotnet), str(lab.directory / 'server/RackClick.Server.dll'), '--migrate'],
                cwd=lab.directory / 'server', env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                timeout=90, creationflags=NO_WINDOW).returncode
        if code:
            raise Schema8Error('candidate143_new_migration_failed')
        lab.grant_runtime(db); runtime_permissions(lab, db)
        candidate.cfg = configuration(source.cfg, lab.directory, lab.port, db, target)
        candidate.recovery_cfg = configuration(source.cfg, lab.directory, lab.port, candidate.recovered, source.baseline,
                                               artifacts=lab.directory / 'versions/schema7-recovery')
        save(lab.directory / 'manual-qa.json', candidate.cfg)
        save(lab.directory / 'recovery7-manual-qa.json', candidate.recovery_cfg)
        after = snapshot(candidate.sql)
        found = history(candidate.sql, lab.directory / 'server', 8)
        if (set(after) != set(before) | NEW_TABLES or found[:7] != old_history or
                {k: v for k, v in after.items() if k not in NEW_TABLES | {'schema_migration'}} !=
                {k: v for k, v in before.items() if k != 'schema_migration'} or
                any(after[n]['rows'] != 0 for n in NEW_TABLES)):
            raise Schema8Error('candidate143_old_rows_or_new_empty_tables_differ')
        if (snapshot(lambda q: candidate.sql(q, recovery=True)) != before or
                history(lambda q: candidate.sql(q, recovery=True), lab.directory / 'versions/schema7-recovery/server', 7) != old_history):
            raise Schema8Error('candidate143_recovery7_rows_or_history_differ')
        identities = {(d.name, d.owner, d.runtime) for d in (source.db, db, candidate.recovered)}
        secrets = {p for d in (source.db, db, candidate.recovered) for p in (d.owner_password, d.runtime_password)}
        if len(identities) != 3 or len(secrets) != 6:
            raise Schema8Error('candidate143_postgresql_identity_reused')
        # The sole target baseline is captured after every migrate/grant write.
        state.update(database=db.name, recoveredDatabase=candidate.recovered.name, candidateSnapshot=after,
            candidateHistory=found, candidateActivityBaseline=activity_watermark(lab.directory, candidate.cfg))
        candidate.record = state
        verify_source(source, state)
        if any(sha256(source.directory / n) != sha256(lab.directory / n) for n in PRIVATE_FILES):
            raise Schema8Error('candidate143_copied_private_files_differ')
        paths = ['lab.json', 'admin.pgpass', 'manual-qa.json', 'source-manual-qa.json', 'recovery7-manual-qa.json', archive.name]
        paths += list(PRIVATE_FILES)
        for database in (db, candidate.recovered):
            paths += [database.name + '/credentials.json', database.name + '/owner.pgpass']
        state['inputHashes'] = {name: sha256(checked_path(lab.directory / name)) for name in paths}
        state.update(state='prepared', sourcePreserved=True, activated=False)
        save(lab.directory / PREPARED, state)
        atomic_bytes(lab.directory / SEAL, (sha256(lab.directory / PREPARED) + '\n').encode('ascii'))
        save(candidate.journal, state)
        candidate.validate_static(); candidate.verify_rows_and_activity()
        candidate.close()
        return candidate
    except Exception as error:
        state['failedAfter'] = state['state']; state['state'] = 'failed'
        state['failureCode'] = getattr(error, 'code', 'private_copy_internal_failure')
        journal_ok = False
        try:
            save(candidate.journal, state); journal_ok = True
        except Exception:
            pass
        try:
            candidate.close()
        except Exception:
            raise Schema8Error('copy143_failed_stop_unconfirmed', candidate) from None
        if not journal_ok:
            raise Schema8Error('copy143_failed_journal_unconfirmed', candidate) from None
        raise Schema8Error('copy143_failed_private_outputs_retained', candidate) from None
