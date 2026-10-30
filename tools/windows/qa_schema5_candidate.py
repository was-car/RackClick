"""Schema4 -> schema5/6 preparation/recovery ONLY in a newly allocated Lab fixture.

Library only. No QA metadata, existing cluster, pointer, supervisor or activation.
The caller owns quiescence and the Lab lifetime. Failed private copies are retained.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import NO_WINDOW
from pg_lab_recovery import LabRecovery, RecoveryError, sha256

SQL_FILES = ('001-foundation.sql', '002-inventory.sql',
             '003-operation-cancellation.sql', '004-session-identity.sql',
             '005-audit-context.sql', '006-audit-state-intent.sql')
DLL4 = 'd469e4d2ea88f7947b4753738741ea0078f507119f1d249f701ca62852fb2891'
DLL5 = '2ebfc2c875a519e91a9338dab1762202f4dfa001834a4c80dcfc3c13dafd5f91'
DLL6 = '919fb34cfb3cc5a030bab88130420479f774d077e7fe811ecee4900ab782c3ee'
SQL5 = '614e7dbe6cc69331d782175122f5241d2ec5fbf4567f675d73b471329f001d25'
SQL6 = '7494e4e44073e198756ec4ae73b138ce6972aa885eb2d5281c915e52ecc37961'
NEW_TABLES = {'audit_context', 'audit_context_object'}


class CandidateError(RuntimeError):
    def __init__(self, message, candidate=None):
        super().__init__(message)
        self.candidate = candidate


def checked_path(path):
    """Reject lexical escapes and every redirected ancestor before reading files."""
    path = Path(os.path.abspath(path))
    root = ROOT.absolute()
    if not path.is_relative_to(root):
        raise CandidateError('Path is outside the workspace')
    for current in (path, *path.parents):
        if current.is_symlink() or current.is_junction():
            raise CandidateError('Redirected paths are not allowed')
        if current == root:
            break
    return path.resolve()


def manifest(directory):
    directory = checked_path(directory)
    if not directory.is_dir():
        raise CandidateError('Complete artifact directory is missing')
    result = {}
    for entry in sorted(directory.rglob('*')):
        checked_path(entry)
        if entry.is_file():
            result[entry.relative_to(directory).as_posix()] = sha256(entry)
    return result


@dataclass(frozen=True)
class Distribution:
    server: Path
    frontend: Path
    expected: dict
    schema: int

    @property
    def dll(self):
        return self.server / 'RackClick.Server.dll'

    def validate(self):
        expected_dll = {4: DLL4, 5: DLL5, 6: DLL6}.get(self.schema)
        if not expected_dll:
            raise CandidateError('Only exactly pinned frozen schema4/5/6 distributions are supported')
        for directory in (self.server, self.frontend):
            directory = checked_path(directory)
            labs = ROOT / '.local/labs'
            in_fixture = (directory.is_relative_to(labs) and
                not directory.relative_to(labs).parts[0].startswith(('manual-', 'qa-')))
            if not directory.is_relative_to(ROOT / '.local/candidates') and not in_fixture:
                raise CandidateError('Artifacts must belong to a frozen candidate or synthetic fixture')
        actual = {'server': manifest(self.server), 'frontend': manifest(self.frontend)}
        if (actual != self.expected or actual['server'].get('RackClick.Server.dll') != expected_dll or
                not {'RackClick.Server.deps.json', 'RackClick.Server.runtimeconfig.json'} <= actual['server'].keys() or
                not {'app.js', 'app.css', 'index.html'} <= actual['frontend'].keys() or
                not all('database/' + f in actual['server'] for f in SQL_FILES[:self.schema])):
            raise CandidateError('Complete frozen distribution differs')
        if self.schema >= 5 and actual['server'].get('database/' + SQL_FILES[4]) != SQL5:
            raise CandidateError('Migration005 differs from the reviewed frozen file')
        if self.schema == 6 and actual['server'].get('database/' + SQL_FILES[5]) != SQL6:
            raise CandidateError('Migration006 differs from the reviewed frozen file')
        if any('database/' + filename in actual['server'] for filename in SQL_FILES[self.schema:]):
            raise CandidateError('Distribution unexpectedly includes a later migration')
        return actual


def sql_read(lab, db, statement):
    value = lab.sql(db, 'BEGIN READ ONLY;\n' + statement + ';\nCOMMIT;', sensitive=True)
    return '\n'.join(row for row in value.splitlines() if row not in ('BEGIN', 'COMMIT'))


def history(lab, db, distribution):
    rows = sql_read(lab, db, 'SELECT row_to_json(t)::text FROM schema_migration t ORDER BY version')
    values = [json.loads(row) for row in rows.splitlines()]
    if [r['version'] for r in values] != list(range(1, distribution.schema + 1)):
        raise CandidateError('Migration history is not the exact supported sequence')
    for row, filename in zip(values, SQL_FILES):
        # .NET File.ReadAllText consumes a BOM but preserves newlines; do not use read_text universal newlines.
        text = (distribution.server / 'database' / filename).read_bytes().decode('utf-8-sig')
        digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
        if row['digest'].lower() != digest:
            raise CandidateError('Migration history digest differs')
    return values


def snapshot(lab, db):
    tables = sql_read(lab, db, "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
    rows = {}
    for table in tables:
        if not re.fullmatch('[a-z_]+', table):
            raise CandidateError('Unsupported public table identifier')
        value = sql_read(lab, db, f'SELECT row_to_json(t)::text FROM "{table}" t ORDER BY row_to_json(t)::text')
        rows[table] = {'rows': len(value.splitlines()) if value else 0,
                       'sha256': hashlib.sha256(value.encode('utf-8')).hexdigest()}
    return rows


def runtime_permissions(lab, db):
    # This file and SQL output never leave the ACL-restricted new Lab directory.
    passfile = checked_path(db.directory / 'schema5-runtime.pgpass')
    passfile.write_text(f'127.0.0.1:{lab.port}:{db.name}:{db.runtime}:{db.runtime_password}\n', encoding='utf-8')
    env = lab.environment(); env['PGPASSFILE'] = str(passfile)
    statement = "SELECT current_user; SELECT count(*) FROM audit_context; SELECT count(*) FROM audit_context_object"
    result = subprocess.run([str(lab.pg_bin / 'psql.exe'), '-X', '-w', '-At', '-v', 'ON_ERROR_STOP=1',
        '-h', '127.0.0.1', '-p', str(lab.port), '-U', db.runtime, '-d', db.name],
        input=statement, text=True, encoding='utf-8', capture_output=True, env=env,
        timeout=30, creationflags=NO_WINDOW)
    if result.returncode or result.stdout.strip() != db.runtime + '\n0\n0':
        raise CandidateError('Runtime cannot read the new empty context tables')
    checks = sql_read(lab, db, f"""SELECT bool_and(NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole)
        FROM pg_roles WHERE rolname IN ('{db.owner}','{db.runtime}');
        SELECT NOT has_schema_privilege('{db.runtime}','public','CREATE');
        SELECT NOT has_database_privilege('{db.runtime}',current_database(),'CREATE');
        SELECT bool_and(has_table_privilege('{db.runtime}',tablename,privilege))
        FROM pg_tables CROSS JOIN unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE']) privilege
        WHERE schemaname='public' AND tablename IN ('audit_context','audit_context_object');
        SELECT count(*)=0 FROM pg_tables WHERE schemaname='public' AND tableowner<>'{db.owner}'""")
    if checks != 't\nt\nt\nt\nt':
        raise CandidateError('Runtime or owner permissions differ from the isolated fixture policy')


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


@dataclass
class PreparedCopy:
    lab: object
    database: object = None
    recovered: object = None
    directory: Path = None
    baseline: Distribution = None
    candidate: Distribution = None


def validate_source(lab, source, baseline, candidate):
    checked_path(lab.directory)
    for entry in lab.directory.rglob('*'):
        checked_path(entry)
    recovery = LabRecovery(lab)
    recovery._database(source)  # The existing helper enforces newly allocated Lab membership and credentials.
    if (not re.fullmatch(r'rc_[0-9a-f]{12}', source.name) or
            source.owner != 'rc_m_' + source.name[3:] or source.runtime != 'rc_a_' + source.name[3:]):
        raise CandidateError('Source database/roles do not match generated fixture identities')
    if any(s.database.name == source.name and s.process.poll() is None for s in lab.servers):
        raise CandidateError('Source fixture application must be stopped by its caller')
    if baseline.schema != 4 or candidate.schema not in (5, 6):
        raise CandidateError('Only exactly pinned4 ->5/6 fixture transitions are supported')
    baseline.validate(); candidate.validate()
    for filename in SQL_FILES[:4]:
        if sha256(baseline.server / 'database' / filename) != sha256(candidate.server / 'database' / filename):
            raise CandidateError('Historical migrations001-004 differ between distributions')
    history(lab, source, baseline)
    if sql_read(lab, source, "SELECT to_regclass('public.audit_context') IS NULL AND to_regclass('public.audit_context_object') IS NULL") != 't':
        raise CandidateError('Schema4 source unexpectedly contains context tables')
    return recovery


def prepare(lab, source, baseline, candidate, name):
    """Create5/6 plus a compatible4 recovery, each with NEW DB/roles/credentials.

    Accepts neither QA directories nor a destination database. Source app must be
    caller-stopped; caller must exclusively own this synthetic Lab during all work.
    No HTTP/login or activation is implicit. Caller retains and closes the Lab.
    """
    recovery = validate_source(lab, source, baseline, candidate)
    target_schema = candidate.schema
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,35}', name):
        raise CandidateError('Preparation must use a simple new name')
    for suffix in ('backup4', f'candidate{target_schema}', 'recovered4'):
        if (lab.directory / 'recovery' / f'{name}-{suffix}').exists():
            raise CandidateError('Refusing to reuse any preparation output')
    output = checked_path(lab.directory / (f'schema{target_schema}-' + name))
    if output.exists():
        raise CandidateError('Refusing to overwrite a prepared or failed copy')
    before = snapshot(lab, source)
    old_history = history(lab, source, baseline)
    source_private = sha256(source.directory / 'credentials.json')
    output.mkdir()
    prepared = PreparedCopy(lab, directory=output)
    status = dict(state='allocated', sourceSchema=4, candidateSchema=target_schema, activated=False,
                  scope='new-synthetic-lab-only', utc=datetime.now(timezone.utc).isoformat(),
                  sourceDatabase=source.name, sourceSnapshot=before)
    journal = output / 'preparation-private.json'
    save(journal, status)
    try:
        for label, dist in [('baseline4', baseline), (f'candidate{target_schema}', candidate)]:
            target = output / label
            shutil.copytree(dist.server, target / 'server')
            shutil.copytree(dist.frontend, target / 'frontend')
            copy = Distribution(target / 'server', target / 'frontend', dist.expected, dist.schema)
            copy.validate()
            setattr(prepared, 'baseline' if dist.schema == 4 else 'candidate', copy)
        backup = recovery.backup(source, name + '-backup4')
        status.update(state='backed-up', dumpSha256=sha256(backup / 'database.dump'))
        save(journal, status)
        recovered = prepared.recovered = recovery.restore(backup, name + '-recovered4')
        if snapshot(lab, recovered) != before or history(lab, recovered, prepared.baseline) != old_history:
            raise CandidateError('New schema4 recovery differs from the retained source')
        status['state'] = 'recovered4'; save(journal, status)
        database = prepared.database = recovery.restore(backup, name + f'-candidate{target_schema}')
        if snapshot(lab, database) != before:
            raise CandidateError('New pre-migration copy differs from the source')
        status['state'] = 'restored4'; save(journal, status)
        env = lab.environment(); env['ConnectionStrings__RackClick'] = database.connection(lab.port, runtime=False)
        with (output / 'migration-private.log').open('xb') as log:
            code = subprocess.run([str(lab.dotnet), str(prepared.candidate.dll), '--migrate'],
                cwd=prepared.candidate.server, env=env, stdout=log, stderr=log,
                stdin=subprocess.DEVNULL, timeout=60, creationflags=NO_WINDOW).returncode
        if code:
            raise CandidateError(f'Schema{target_schema} migration failed; source4 and new recovery4 retained')
        status['state'] = f'migrated{target_schema}'; save(journal, status)
        lab.grant_runtime(database)
        history5 = history(lab, database, prepared.candidate)
        after = snapshot(lab, database)
        compatible = {k: v for k, v in after.items() if k not in NEW_TABLES and k != 'schema_migration'}
        old_rows = {k: v for k, v in before.items() if k != 'schema_migration'}
        if (set(after) != set(before) | NEW_TABLES or compatible != old_rows or
                history5[:4] != old_history or any(after[t]['rows'] != 0 for t in NEW_TABLES)):
            raise CandidateError('Target schema changed prior rows/history or invented historical context')
        runtime_permissions(lab, database)
        identities = {(d.name, d.owner, d.runtime) for d in (source, database, recovered)}
        passwords = {secret for d in (source, database, recovered) for secret in (d.owner_password, d.runtime_password)}
        if len(identities) != 3 or len(passwords) != 6:
            raise CandidateError('Destination identities or generated secrets were reused')
        validate_source(lab, source, baseline, candidate)
        if (snapshot(lab, source) != before or snapshot(lab, recovered) != before or
                source_private != sha256(source.directory / 'credentials.json') or
                sha256(backup / 'database.dump') != status['dumpSha256']):
            raise CandidateError('Source, recovery, credentials or private dump changed')
        prepared.baseline.validate(); prepared.candidate.validate()
        status.update(state='prepared', database=database.name, recovered=recovered.name,
                      sourcePreserved=True, recoveryPreserved=True, historyPreserved=True,
                      candidateSnapshot=after, runtime005Verified=True)
        save(journal, status)
        return prepared
    except Exception:
        status['failedAfter'] = status['state']; status['state'] = 'failed'
        try:
            save(journal, status)
        except Exception:
            raise CandidateError('Preparation failed; private copies retained, journal not confirmed', prepared) from None
        raise CandidateError('Preparation failed; source and private copies retained', prepared) from None
