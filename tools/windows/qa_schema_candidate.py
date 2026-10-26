"""Prepare a private schema4 copy of a stopped, identified RC9 QA application.

Library only: never changes pointers, starts/stops the source or activates QA.
Source PostgreSQL remains owned by the caller. Failed candidates are retained.
"""
from datetime import datetime, timezone
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import Lab, Database, DEFAULT_DLL, NO_WINDOW, toolchain

SOURCE_DLL = 'd0a5c95783ecc8e9ae7165be9a1bcd8857ee587b643fac3f07aa6092e6bd4b81'
SOURCE_BUNDLE = '43f7a19e8ec5aea0e62bfa9d66d4e9031d3ce90207c9af23fab73db48789ce84'
CANDIDATE_DLL = '5e55ba4628b41b51d84f6ee62043dbf2ed34d84c3bb7959f905833b4c063cf4a'
CANDIDATE_BUNDLE = 'c9072f1f2847feef2987ac21b4c456eecc466589a4038f2aa5b136a11add5ea3'
CSS = 'c4e8a722d4068e35a02708614d1afb45ff2c43a89450d5457511718dc1c95e19'
PRIVATE_FILES = ('ACCESO-PRIVADO.txt', 'QA-CUENTAS-ESTADO.json',
                 'qa-accounts-private.json', 'RESTORE-ESTADO.json')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


class CandidateError(RuntimeError):
    def __init__(self, message, candidate=None):
        super().__init__(message)
        self.candidate = candidate


def checked_path(path):
    path = Path(path).absolute()
    if not path.is_relative_to(ROOT.absolute()):
        raise CandidateError('Path is outside the workspace')
    for current in (path, *path.parents):
        if current.is_symlink() or current.is_junction():
            raise CandidateError('Redirected paths are not allowed')
        if current == ROOT.absolute():
            break
    return path.resolve()


def manifest(directory):
    directory = checked_path(directory)
    if not directory.is_dir():
        raise CandidateError('Artifact directory is missing')
    result = {}
    for entry in sorted(directory.rglob('*')):
        checked_path(entry)
        if entry.is_file():
            result[entry.relative_to(directory).as_posix()] = sha256(entry)
    return result


def artifacts(server, frontend, dll_hash, bundle_hash):
    server, frontend = checked_path(server), checked_path(frontend)
    hashes = (manifest(server), manifest(frontend))
    if (hashes[0].get('RackClick.Server.dll') != dll_hash or
            hashes[1].get('app.js') != bundle_hash or hashes[1].get('app.css') != CSS or
            not all(x in hashes[0] for x in ('RackClick.Server.deps.json',
                'RackClick.Server.runtimeconfig.json', 'database/001-foundation.sql',
                'database/002-inventory.sql', 'database/003-operation-cancellation.sql')) or
            'index.html' not in hashes[1]):
        raise CandidateError('Frozen artifact hash or required file differs')
    return hashes


def app_stopped(directory, port):
    if (directory / 'ready.json').exists():
        raise CandidateError('Source application readiness marker is present')
    lock = directory / 'server.lock'
    if lock.exists():
        checked_path(lock)
        with lock.open('rb') as handle:
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise CandidateError('Source application supervisor is active') from None
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    with socket.socket() as listener:
        listener.settimeout(.5)
        if listener.connect_ex(('127.0.0.1', port)) == 0:
            raise CandidateError('Source web port is occupied')


class Source:
    """Owner read-only connection reconstructed only from a private QA manifest."""
    def __init__(self, directory):
        try:
            self.directory = checked_path(directory)
            labs = (ROOT / '.local/labs').resolve()
            if (self.directory.parent != labs or
                    not re.fullmatch(r'manual-qa-rc9-[0-9a-f]{32}', self.directory.name)):
                raise CandidateError('Source must be an identified RC9 QA lab')
            cfg_path, meta_path = self.directory / 'manual-qa.json', self.directory / 'lab.json'
            for path in (cfg_path, meta_path, self.directory / 'data',
                         *(self.directory / f for f in PRIVATE_FILES)):
                checked_path(path)
                if not path.exists():
                    raise CandidateError('Required private source file is missing')
            self.cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
            self.meta = json.loads(meta_path.read_text(encoding='utf-8'))
            c, m = self.cfg, self.meta
            if (c.get('directory') != str(self.directory) or c.get('profile') != 'rc9' or
                    c.get('host') != '127.0.0.1' or m.get('host') != '127.0.0.1' or
                    m.get('path') != str(self.directory) or m.get('postgresql') != '17' or
                    self.directory.name != 'manual-qa-rc9-' + m.get('id', '') or
                    c.get('pgPort') != m.get('port') or
                    any(type(c.get(p)) is not int or not 1 <= c[p] <= 65535 for p in ('pgPort', 'webPort'))):
                raise CandidateError('Source QA configuration identity differs')
            rows = [r for r in m['databases'] if r['name'] == c['database']]
            if len(rows) != 1 or rows[0]['label'] != 'manual-qa-rc9':
                raise CandidateError('Source database does not belong to RC9 QA')
            row = rows[0]
            if (not re.fullmatch(r'rc_[0-9a-f]{12}', row['name']) or
                    row['owner'] != 'rc_m_' + row['name'][3:] or
                    row['runtime'] != 'rc_a_' + row['name'][3:]):
                raise CandidateError('Source database role identity is invalid')
            db_dir = checked_path(self.directory / row['name'])
            credentials = checked_path(db_dir / 'credentials.json')
            passfile = checked_path(db_dir / 'owner.pgpass')
            cred = json.loads(credentials.read_text(encoding='utf-8'))
            self.db = Database(row['name'], row['owner'], cred['ownerPassword'],
                               row['runtime'], cred['runtimePassword'], db_dir)
            if (cred != dict(database=self.db.name, owner=self.db.owner,
                    ownerPassword=self.db.owner_password, runtime=self.db.runtime,
                    runtimePassword=self.db.runtime_password) or
                    c['connection'] != self.db.connection(c['pgPort']) or
                    passfile.read_text(encoding='utf-8') !=
                    f'127.0.0.1:{c["pgPort"]}:{self.db.name}:{self.db.owner}:{self.db.owner_password}\n'):
                raise CandidateError('Source private database connection differs')
            self.art = checked_path(c.get('artifactDirectory', self.directory))
            if self.art != self.directory and self.art.parent != checked_path(self.directory / 'versions'):
                raise CandidateError('Source artifact directory is outside its lab')
            if c.get('dllSha256') != SOURCE_DLL or c.get('bundleSha256') != SOURCE_BUNDLE:
                raise CandidateError('Source frozen artifact identity differs')
            self.art_hashes = artifacts(self.art / 'server', self.art / 'frontend', SOURCE_DLL, SOURCE_BUNDLE)
            self.input_paths = [cfg_path, meta_path, credentials, passfile,
                                *(self.directory / f for f in PRIVATE_FILES)]
            self.input_hashes = {str(p): sha256(p) for p in self.input_paths}
            app_stopped(self.directory, c['webPort'])
            self.pg_bin = toolchain()['postgresql'].parent
            status = subprocess.run([str(self.pg_bin / 'pg_ctl.exe'), 'status', '-D', str(self.directory / 'data')],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, creationflags=NO_WINDOW)
            if status.returncode:
                raise CandidateError('Source PostgreSQL must already be running and caller-owned')
            if self.sql('SELECT current_database(); SELECT current_user; SHOW port') != f'{self.db.name}\n{self.db.owner}\n{c["pgPort"]}':
                raise CandidateError('Source PostgreSQL connection identity differs')
            if self.sql('SELECT string_agg(version::text,\',\' ORDER BY version) FROM schema_migration') != '1,2,3':
                raise CandidateError('Only source schema3 is supported')
        except CandidateError:
            raise
        except Exception:
            raise CandidateError('Source validation failed; no candidate allocated') from None

    def environment(self):
        return dict(os.environ, PGCLIENTENCODING='UTF8', PGPASSFILE=str(self.db.directory / 'owner.pgpass'))

    def sql(self, command):
        result = subprocess.run([str(self.pg_bin / 'psql.exe'), '-X', '-w', '-At', '-v', 'ON_ERROR_STOP=1',
            '-h', '127.0.0.1', '-p', str(self.cfg['pgPort']), '-U', self.db.owner, '-d', self.db.name],
            input='BEGIN READ ONLY;\n' + command + ';\nCOMMIT;', text=True, encoding='utf-8', capture_output=True,
            env=self.environment(), timeout=60, creationflags=NO_WINDOW)
        if result.returncode:
            raise CandidateError('Source read-only query failed')
        # BEGIN/COMMIT command tags are suppressed by -q.
        rows = result.stdout.strip().splitlines()
        return '\n'.join(row for row in rows if row not in ('BEGIN', 'COMMIT'))

    def unchanged(self):
        if self.input_hashes != {str(p): sha256(p) for p in self.input_paths}:
            raise CandidateError('Source private inputs changed during preparation')
        if self.art_hashes != artifacts(self.art / 'server', self.art / 'frontend', SOURCE_DLL, SOURCE_BUNDLE):
            raise CandidateError('Source artifacts changed during preparation')
        app_stopped(self.directory, self.cfg['webPort'])


def snapshot(sql, compatible=False):
    tables = sql("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
    rows = {}
    for table in tables:
        if not re.fullmatch('[a-z_]+', table):
            raise CandidateError('Unsupported public table identifier')
        projection = 'token_hash,user_id,csrf_hash,expires_at' if compatible and table == 'app_session' else '*'
        condition = ' WHERE version<4' if compatible and table == 'schema_migration' else ''
        value = sql(f'SELECT row_to_json(t)::text FROM (SELECT {projection} FROM "{table}"{condition}) t ORDER BY row_to_json(t)::text')
        rows[table] = {'rows': len(value.splitlines()) if value else 0,
                       'sha256': hashlib.sha256(value.encode('utf-8')).hexdigest()}
    return rows


class Candidate:
    def __init__(self, lab):
        self.lab, self.database, self.cfg = lab, None, None
        self.journal = lab.directory / 'schema-copy-private.json'

    def close(self):
        self.lab.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def prepare(source_directory, server_directory=DEFAULT_DLL.parent,
            frontend_directory=ROOT / 'development/frontend/dist'):
    """Return a running private candidate; caller must close it (or use with).

    No external dump or existing destination is accepted. Validation precedes
    allocation. On failure our candidate stops and its files/journal remain.
    """
    source = Source(source_directory)
    expected = artifacts(server_directory, frontend_directory, CANDIDATE_DLL, CANDIDATE_BUNDLE)
    if 'database/004-session-identity.sql' not in expected[0]:
        raise CandidateError('Candidate migration file is missing')
    before = snapshot(source.sql)
    compatible = snapshot(source.sql, True)
    source.unchanged()
    candidate = Candidate(Lab('manual-qa-rc9-schema4'))
    lab = candidate.lab
    status = dict(state='allocated', sourceDirectory=str(source.directory),
                  sourceConfigPath=str(source.directory / 'manual-qa.json'),
                  sourceArtifactDirectory=str(source.art),
                  sourceConfigSha256=sha256(source.directory / 'manual-qa.json'),
                  sourcePrivateFiles={f: sha256(source.directory / f) for f in PRIVATE_FILES},
                  sourceSchema=3, candidateSchema=4, sourceArtifacts=source.art_hashes,
                  candidateArtifacts=expected, sourceSnapshot=before,
                  utc=datetime.now(timezone.utc).isoformat(), activated=False)
    save(candidate.journal, status)
    try:
        if lab.port == source.cfg['webPort']:
            raise CandidateError('Candidate PostgreSQL port collides with the retained web port')
        shutil.copyfile(source.directory / 'manual-qa.json', lab.directory / 'source-manual-qa.json')
        shutil.copytree(server_directory, lab.directory / 'server')
        shutil.copytree(frontend_directory, lab.directory / 'frontend')
        for name in PRIVATE_FILES:
            shutil.copyfile(source.directory / name, lab.directory / name)
        lab.start()
        db = candidate.database = lab.create_database('manual-qa-rc9')
        status.update(database=db.name, directory=str(lab.directory))
        archive = lab.directory / 'source-schema3.dump'
        with (lab.directory / 'source-dump.log').open('xb') as output:
            code = subprocess.run([str(source.pg_bin / 'pg_dump.exe'), '-w', '-h', '127.0.0.1',
                '-p', str(source.cfg['pgPort']), '-U', source.db.owner, '-d', source.db.name,
                '--format=custom', '--file=' + str(archive)], stdout=output, stderr=output,
                env=source.environment(), stdin=subprocess.DEVNULL, timeout=180, creationflags=NO_WINDOW).returncode
        if code:
            raise CandidateError('Source backup failed; private candidate retained')
        status.update(state='backed-up', dumpPath=str(archive), dumpSha256=sha256(archive), dumpBytes=archive.stat().st_size)
        save(candidate.journal, status)
        env = lab.environment()
        env['PGPASSFILE'] = str(db.directory / 'owner.pgpass')
        with (lab.directory / 'restore.log').open('xb') as output:
            code = subprocess.run([str(lab.pg_bin / 'pg_restore.exe'), '-w', '-h', '127.0.0.1',
                '-p', str(lab.port), '-U', db.owner, '-d', db.name, '--single-transaction',
                '--exit-on-error', '--no-owner', '--no-acl', str(archive)], stdout=output, stderr=output,
                env=env, stdin=subprocess.DEVNULL, timeout=180, creationflags=NO_WINDOW).returncode
        if code:
            raise CandidateError('Private candidate restore failed atomically')
        sql = lambda command: lab.sql(db, command, sensitive=True)
        if before != snapshot(sql):
            raise CandidateError('Restored rows differ from the source')
        status['state'] = 'restored'
        save(candidate.journal, status)
        env['ConnectionStrings__RackClick'] = db.connection(lab.port, runtime=False)
        with (lab.directory / 'migration.log').open('xb') as output:
            code = subprocess.run([str(lab.dotnet), str(lab.directory / 'server/RackClick.Server.dll'), '--migrate'],
                cwd=lab.directory / 'server', stdout=output, stderr=output, env=env,
                stdin=subprocess.DEVNULL, timeout=60, creationflags=NO_WINDOW).returncode
        if code:
            raise CandidateError('Private candidate migration failed atomically')
        lab.grant_runtime(db)
        if (sql("SELECT string_agg(version::text,',' ORDER BY version) FROM schema_migration") != '1,2,3,4' or
                sql("SELECT count(*)=count(DISTINCT id) AND coalesce(bool_and(id IS NOT NULL AND id<>'00000000-0000-0000-0000-000000000000'),true) FROM app_session") != 't' or
                compatible != snapshot(sql, True)):
            raise CandidateError('Migrated rows or public session identity differ')
        source.unchanged()
        if before != snapshot(source.sql):
            raise CandidateError('Source rows changed during preparation')
        if expected != artifacts(lab.directory / 'server', lab.directory / 'frontend', CANDIDATE_DLL, CANDIDATE_BUNDLE):
            raise CandidateError('Copied candidate artifact differs')
        if any(sha256(source.directory / f) != sha256(lab.directory / f) for f in PRIVATE_FILES):
            raise CandidateError('Copied private account or restore marker differs')
        if sha256(lab.directory / 'source-manual-qa.json') != status['sourceConfigSha256']:
            raise CandidateError('Retained source configuration differs')
        cfg = dict(source.cfg)
        cfg.pop('artifactDirectory', None)
        cfg.update(directory=str(lab.directory.resolve()), pgPort=lab.port, database=db.name,
                   connection=db.connection(lab.port), dllSha256=CANDIDATE_DLL, bundleSha256=CANDIDATE_BUNDLE)
        save(lab.directory / 'manual-qa.json', cfg)
        candidate.cfg = cfg
        status.update(state='prepared', dumpSha256Verified=sha256(archive) == status['dumpSha256'],
                      candidateSnapshot=snapshot(sql), configSha256=sha256(lab.directory / 'manual-qa.json'),
                      sourcePreserved=True)
        if not status['dumpSha256Verified']:
            raise CandidateError('Private backup checksum changed')
        save(candidate.journal, status)
        return candidate
    except Exception:
        status['failedAfter'] = status['state']
        status['state'] = 'failed'
        journal_confirmed = False
        close_confirmed = False
        try:
            save(candidate.journal, status)
            journal_confirmed = True
        except Exception:
            pass
        finally:
            try:
                candidate.close()
                close_confirmed = True
            except Exception:
                pass
        if not close_confirmed:
            raise CandidateError('Candidate preparation failed; stopping private copy not confirmed; '
                                 'failure journal may be incomplete', candidate) from None
        if not journal_confirmed:
            raise CandidateError('Candidate preparation failed; stopped private copy retained; '
                                 'failure journal not confirmed', candidate) from None
        raise CandidateError('Candidate preparation failed; stopped private copy retained', candidate) from None
