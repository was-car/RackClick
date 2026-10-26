"""Private, database-only backup/recovery for newly created pg_support.Lab fixtures.

This is not a QA updater, cluster/role backup or installed-server recovery tool.
Never accepts a destination database: restore always allocates a fresh candidate.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import uuid

# The native fixture library owns cluster creation, credentials and ACLs.
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import Lab, Database, NO_WINDOW


def sha256(path):
    with Path(path).open('rb') as source:
        digest = hashlib.sha256()
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


class RecoveryError(RuntimeError):
    def __init__(self, message, candidate=None):
        super().__init__(message)
        self.candidate = candidate


class LabRecovery:
    def __init__(self, lab):
        if not isinstance(lab, Lab) or not lab.running:
            raise RecoveryError('A running newly created Lab instance is required')
        self.lab = lab
        self._validate_lab()

    def _validate_lab(self):
        lab = self.lab
        directory = lab.directory.resolve()
        if (directory.parent != (ROOT / '.local/labs').resolve() or
                not directory.name.endswith('-' + lab.id) or
                directory.name.startswith(('manual-', 'qa-')) or
                lab.data.resolve() != directory / 'data' or
                not lab.running):
            raise RecoveryError('Only the new isolated test lab is allowed')
        meta = json.loads((directory / 'lab.json').read_text(encoding='utf-8'))
        if (meta['id'] != lab.id or Path(meta['path']).resolve() != directory or
                meta['port'] != lab.port or meta['host'] != '127.0.0.1' or
                meta['databases'] != lab.metadata['databases']):
            raise RecoveryError('Lab membership does not match its private manifest')

    def _database(self, database):
        self._validate_lab()
        if not isinstance(database, Database):
            raise RecoveryError('Only a database allocated by this Lab is allowed')
        rows = self.lab.metadata['databases']
        if (database.directory.resolve() != self.lab.directory.resolve() / database.name or
                not any(r['name'] == database.name and r['owner'] == database.owner and
                        r['runtime'] == database.runtime for r in rows)):
            raise RecoveryError('Database is not a member of this lab')
        credentials = json.loads((database.directory / 'credentials.json').read_text(encoding='utf-8'))
        if credentials != dict(database=database.name, owner=database.owner,
                ownerPassword=database.owner_password, runtime=database.runtime,
                runtimePassword=database.runtime_password):
            raise RecoveryError('Database private identity differs')

    def _output(self, name):
        self._validate_lab()
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', name):
            raise RecoveryError('Output must be a simple new private name')
        parent = self.lab.directory / 'recovery'
        if parent.exists() and (parent.is_symlink() or parent.resolve() != self.lab.directory.resolve() / 'recovery'):
            raise RecoveryError('Private recovery parent cannot be redirected')
        parent.mkdir(exist_ok=True)
        target = parent / name
        if target.exists():
            raise RecoveryError('Refusing to reuse or overwrite recovery output')
        return target

    def _run(self, executable, database, args, log):
        env = self.lab.environment()
        env['PGPASSFILE'] = str(database.directory / 'owner.pgpass')
        command = [str(self.lab.pg_bin / executable), '-w', '-h', '127.0.0.1',
                   '-p', str(self.lab.port), '-U', database.owner, '-d', database.name] + args
        with log.open('xb') as output:
            return subprocess.run(command, stdout=output, stderr=output, env=env,
                                  stdin=subprocess.DEVNULL, timeout=120,
                                  creationflags=NO_WINDOW).returncode

    def backup(self, database, name):
        self._database(database)
        target = self._output(name)
        target.mkdir(exist_ok=False)
        archive = target / 'database.dump'
        code = self._run('pg_dump.exe', database,
                         ['--format=custom', '--file=' + str(archive)], target / 'dump.log')
        if code:
            raise RecoveryError('Database backup failed; private output retained')
        meta = dict(format='postgresql-custom', scope='database-only', labId=self.lab.id,
                    database=database.name, sha256=sha256(archive), bytes=archive.stat().st_size,
                    utc=datetime.now(timezone.utc).isoformat())
        (target / 'backup.json').write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')
        return target

    def _archive(self, directory):
        self._validate_lab()
        directory = Path(directory)
        recovery = self.lab.directory.resolve() / 'recovery'
        if directory.is_symlink() or directory.resolve().parent != recovery:
            raise RecoveryError('Backup must belong to this private lab recovery directory')
        archive, metadata = directory / 'database.dump', directory / 'backup.json'
        if (not archive.is_file() or not metadata.is_file() or archive.is_symlink() or metadata.is_symlink()):
            raise RecoveryError('Backup archive or private metadata is missing')
        meta = json.loads(metadata.read_text(encoding='utf-8'))
        if (meta.get('labId') != self.lab.id or meta.get('format') != 'postgresql-custom' or
                meta.get('scope') != 'database-only' or
                meta.get('database') not in {r['name'] for r in self.lab.metadata['databases']} or
                meta.get('sha256') != sha256(archive) or meta.get('bytes') != archive.stat().st_size):
            raise RecoveryError('Backup identity or SHA256 differs; no candidate created')
        # Archive structural validation also happens before allocating any database.
        with (self.lab.directory / ('archive-check-' + uuid.uuid4().hex + '.log')).open('xb') as output:
            code = subprocess.run([str(self.lab.pg_bin / 'pg_restore.exe'), '--list', str(archive)],
                    stdout=output, stderr=output, env=self.lab.environment(),
                    stdin=subprocess.DEVNULL, timeout=30, creationflags=NO_WINDOW).returncode
        if code:
            raise RecoveryError('Custom archive cannot be listed; no candidate created')
        return archive, meta

    def restore(self, backup_directory, name):
        archive, meta = self._archive(backup_directory)
        output = self._output(name)
        output.mkdir(exist_ok=False)
        candidate = self.lab.create_database('recovery-' + name)
        status = dict(labId=self.lab.id, database=candidate.name, sourceSha256=meta['sha256'],
                      state='allocated', scope='database-only')
        journal = output / 'restore.json'
        journal.write_text(json.dumps(status, indent=2) + '\n', encoding='utf-8')
        code = self._run('pg_restore.exe', candidate,
                ['--single-transaction', '--exit-on-error', '--no-owner', '--no-acl', str(archive)],
                output / 'restore.log')
        status['state'] = 'failed' if code else 'restored'
        if not code:
            try:
                self.lab.grant_runtime(candidate)
            except Exception:
                status['state'] = 'grants-failed'
                journal.write_text(json.dumps(status, indent=2) + '\n', encoding='utf-8')
                raise RecoveryError('Runtime grants failed; candidate retained', candidate) from None
        journal.write_text(json.dumps(status, indent=2) + '\n', encoding='utf-8')
        if code:
            raise RecoveryError('Restore failed atomically; private candidate retained', candidate)
        return candidate
