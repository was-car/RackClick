"""Explicit, stopped RC9 schema4 source for schema6 copy/switch.

Validation only. Never starts/stops, migrates, logs in, changes a pointer or reads
browser notes/results. Real restored profile requires an explicit real=True.
"""
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import re
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import Database, NO_WINDOW, toolchain
from qa_schema5_candidate import Distribution, checked_path, DLL4
from pg_lab_recovery import sha256

PRIVATE_FILES = ('ACCESO-PRIVADO.txt', 'QA-CUENTAS-ESTADO.json',
                 'qa-accounts-private.json', 'RESTORE-ESTADO.json')
BASELINE = ROOT / 'evidence/s1-20261017/tres-tandas-52/BASELINE.json'
if sha256(BASELINE) != '3dcc6107eb39da96ae0a116aebf08b355f724376974bc9f21212d251e4ef2b45':
    raise RuntimeError('Approved public source manifest differs')
SOURCE_MAP = json.loads(BASELINE.read_text(encoding='utf-8'))['distributions']


class SourceError(RuntimeError):
    pass


def artifact_manifest(directory):
    directory = checked_path(directory)
    if not directory.is_dir(): raise SourceError('artifact_directory_missing')
    result = {}
    for path in sorted(directory.rglob('*')):
        checked_path(path)
        if path.is_file(): result[path.relative_to(directory).as_posix()] = sha256(path)
    return result


def app_stopped(directory, port):
    for name in ('ready.json', 'server.lock', 'stop.request'):
        checked_path(directory / name)
    if (directory / 'ready.json').exists(): raise SourceError('source_application_not_quiet')
    lock_path = directory / 'server.lock'
    if lock_path.exists():
        with lock_path.open('rb') as lock:
            try: msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError: raise SourceError('source_application_active') from None
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
    with socket.socket() as sock:
        sock.settimeout(.5)
        if sock.connect_ex(('127.0.0.1', port)) == 0: raise SourceError('source_web_port_occupied')


class Source4:
    def __init__(self, directory, pointer, *, real=False):
        try:
            self.directory = checked_path(directory)
            self.pointer = checked_path(pointer)
            if (self.directory.parent != ROOT / '.local/labs' or
                    not re.fullmatch(r'manual-qa-rc9(?:-schema4)?-[0-9a-f]{32}', self.directory.name)):
                raise SourceError('source_directory_invalid')
            permitted = ROOT / '.local/qa-rc9/current.json' if real else self.directory / 'switch6-home/current.json'
            if self.pointer != permitted or not self.pointer.is_file(): raise SourceError('source_pointer_invalid')
            self.real = real
            self.pointer_bytes = self.pointer.read_bytes()
            if json.loads(self.pointer_bytes) != {'directory': str(self.directory)}:
                raise SourceError('source_pointer_identity_invalid')
            cfg_path, meta_path = self.directory / 'manual-qa.json', self.directory / 'lab.json'
            self.cfg = json.loads(checked_path(cfg_path).read_text(encoding='utf-8'))
            self.meta = json.loads(checked_path(meta_path).read_text(encoding='utf-8'))
            c, m = self.cfg, self.meta
            if (c.get('directory') != str(self.directory) or c.get('profile') != 'rc9' or
                    c.get('host') != '127.0.0.1' or m.get('host') != '127.0.0.1' or
                    m.get('path') != str(self.directory) or m.get('postgresql') != '17' or
                    not self.directory.name.endswith('-' + m.get('id', '!')) or
                    c.get('pgPort') != m.get('port') or
                    any(type(c.get(k)) is not int or not 1 <= c[k] <= 65535 for k in ('pgPort', 'webPort')) or
                    c['webPort'] == c['pgPort'] or real and c['webPort'] != 52346):
                raise SourceError('source_configuration_invalid')
            rows = [r for r in m['databases'] if r['name'] == c.get('database') and r['label'] == 'manual-qa-rc9']
            if len(rows) != 1: raise SourceError('source_database_membership_invalid')
            row = rows[0]
            if (not re.fullmatch(r'rc_[0-9a-f]{12}', row['name']) or
                    row['owner'] != 'rc_m_' + row['name'][3:] or row['runtime'] != 'rc_a_' + row['name'][3:]):
                raise SourceError('source_database_identity_invalid')
            dbdir = checked_path(self.directory / row['name'])
            credentials = checked_path(dbdir / 'credentials.json')
            cred = json.loads(credentials.read_text(encoding='utf-8'))
            self.db = Database(row['name'], row['owner'], cred['ownerPassword'], row['runtime'], cred['runtimePassword'], dbdir)
            if (cred != dict(database=self.db.name, owner=self.db.owner, ownerPassword=self.db.owner_password,
                    runtime=self.db.runtime, runtimePassword=self.db.runtime_password) or
                    c['connection'] != self.db.connection(c['pgPort']) or
                    checked_path(dbdir / 'owner.pgpass').read_text(encoding='utf-8') !=
                    f'127.0.0.1:{c["pgPort"]}:{self.db.name}:{self.db.owner}:{self.db.owner_password}\n'):
                raise SourceError('source_private_connection_invalid')
            self.art = checked_path(c.get('artifactDirectory', self.directory))
            if self.art != self.directory and self.art.parent != checked_path(self.directory / 'versions'):
                raise SourceError('source_artifact_path_invalid')
            if (c.get('dllSha256') != DLL4 or c.get('bundleSha256') != SOURCE_MAP['frontend']['app.js'] or
                    self.artifacts() != SOURCE_MAP):
                raise SourceError('source_complete_frozen_pair_differs')
            checked_path(self.directory / 'data')
            self.admin_passfile=checked_path(self.directory/'admin.pgpass')
            admin_lines=self.admin_passfile.read_text(encoding='utf-8').splitlines()
            if len(admin_lines)!=1 or not admin_lines[0].startswith(f'127.0.0.1:{c["pgPort"]}:*:rc_lab_admin:') or not admin_lines[0].split(':',4)[-1]:
                raise SourceError('source_cluster_admin_passfile_invalid')
            self.inputs = [cfg_path, meta_path, credentials, dbdir / 'owner.pgpass',self.admin_passfile]
            for name in PRIVATE_FILES:
                path = checked_path(self.directory / name)
                if not path.is_file(): raise SourceError('source_private_file_missing')
                self.inputs.append(path)
            self.hashes = {p.relative_to(self.directory).as_posix(): sha256(p) for p in self.inputs}
            self.pg_bin = toolchain()['postgresql'].parent
            app_stopped(self.directory, c['webPort'])
        except SourceError: raise
        except Exception: raise SourceError('source_validation_failed') from None

    def artifacts(self):
        return {'server': artifact_manifest(self.art / 'server'), 'frontend': artifact_manifest(self.art / 'frontend')}

    def pg_running(self):
        code = subprocess.run([str(self.pg_bin / 'pg_ctl.exe'), 'status', '-D', str(self.directory / 'data')],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, creationflags=NO_WINDOW).returncode
        if code not in (0, 3): raise SourceError('source_cluster_status_uncertain')
        return code == 0

    def environment(self):
        return dict(os.environ, PGCLIENTENCODING='UTF8', PGPASSFILE=str(self.db.directory / 'owner.pgpass'))

    def sql(self, command):
        response = subprocess.run([str(self.pg_bin / 'psql.exe'), '-X', '-q', '-w', '-At', '-v', 'ON_ERROR_STOP=1',
            '-h', '127.0.0.1', '-p', str(self.cfg['pgPort']), '-U', self.db.owner, '-d', self.db.name],
            input='BEGIN READ ONLY;\n' + command + ';\nCOMMIT;', text=True, encoding='utf-8', capture_output=True,
            env=self.environment(), timeout=90, creationflags=NO_WINDOW)
        if response.returncode: raise SourceError('source_readonly_query_failed')
        return response.stdout.strip()

    def check_schema(self):
        self.check_cluster_identity()
        if self.sql('SELECT current_database();SELECT current_user;SHOW port') != f'{self.db.name}\n{self.db.owner}\n{self.cfg["pgPort"]}':
            raise SourceError('source_running_database_identity_invalid')
        rows = [json.loads(r) for r in self.sql('SELECT row_to_json(t) FROM schema_migration t ORDER BY version').splitlines()]
        if [r['version'] for r in rows] != [1, 2, 3, 4]: raise SourceError('source_schema4_required')
        for row, name in zip(rows, [k for k in sorted(SOURCE_MAP['server']) if k.startswith('database/')]):
            digest = hashlib.sha256((self.art / 'server' / name).read_bytes().decode('utf-8-sig').encode()).hexdigest()
            if row['digest'].lower() != digest: raise SourceError('source_migration_digest_differs')
        return rows

    def check_cluster_identity(self):
        if not self.pg_running():raise SourceError('source_cluster_not_running')
        env=dict(os.environ,PGCLIENTENCODING='UTF8',PGPASSFILE=str(self.admin_passfile))
        response=subprocess.run([str(self.pg_bin/'psql.exe'),'-X','-q','-w','-At','-v','ON_ERROR_STOP=1',
            '-h','127.0.0.1','-p',str(self.cfg['pgPort']),'-U','rc_lab_admin','-d','postgres'],
            input="BEGIN READ ONLY;SELECT current_setting('data_directory');COMMIT;",text=True,encoding='utf-8',
            capture_output=True,env=env,timeout=30,creationflags=NO_WINDOW)
        if response.returncode:raise SourceError('source_cluster_identity_unconfirmed')
        if checked_path(response.stdout.strip())!=checked_path(self.directory/'data'):
            raise SourceError('source_sql_cluster_directory_differs')

    def unchanged(self, *, pointer=True, quiet=True):
        if self.hashes != {p.relative_to(self.directory).as_posix(): sha256(checked_path(p)) for p in self.inputs}:
            raise SourceError('source_private_inputs_changed')
        if self.artifacts() != SOURCE_MAP: raise SourceError('source_artifacts_changed')
        if pointer and checked_path(self.pointer).read_bytes() != self.pointer_bytes: raise SourceError('source_pointer_changed')
        if quiet: app_stopped(self.directory, self.cfg['webPort'])
