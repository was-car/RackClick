"""Native PS5.1 + genuine PostgreSQL17.11, new private cluster only; no application/QA."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import subprocess
import sys
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import Lab, literal, protect_directory

WINDOWS = ROOT / 'tools/windows'
POWERSHELL = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
BASELINE = ROOT / 'evidence/s1-20261017/seis-tandas-180-185/CANDIDATA185.json'
BASELINE_SHA = '68aca94da20751b690af0c1c6b764a1db1004d3d63be2a12161938a3624d7706'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
write_json = lambda p, data: p.write_bytes((json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))


class DatabaseBackup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert os.name == 'nt' and sha(BASELINE) == BASELINE_SHA
        cls.calls = []
        cls.guards = {str(p): sha(p) for p in [Path(__file__), BASELINE,
            WINDOWS/'RackClick.Backup.ps1', WINDOWS/'New-RackClickDatabaseBackup.ps1',
            WINDOWS/'Restore-RackClickDatabaseBackup.ps1', WINDOWS/'Test-RuntimePrerequisites.ps1']}
        candidate = json.loads(BASELINE.read_bytes())
        for name, digest in candidate['distributions']['server'].items():
            p = ROOT / candidate['candidateDirectory'] / 'server' / name
            assert sha(p) == digest
            cls.guards[str(p)] = digest
        cls.lab = Lab('native-backup198').start()
        try:
            cls.home = cls.lab.directory / 'operations copia Ω'; cls.home.mkdir()
            cls.source = cls.lab.create_database('native source schema9')
            database_folder = ROOT / candidate['candidateDirectory'] / 'server/database'
            for version, p in enumerate(sorted(database_folder.glob('*.sql')), 1):
                cls.lab.sql(cls.source, p.read_text(encoding='utf-8-sig'))
                cls.lab.sql(cls.source, f"INSERT INTO schema_migration(version,digest) VALUES({version},'{sha(p)}');")
            cls.house = str(uuid.uuid4()); cls.customer = str(uuid.uuid4())
            cls.lab.sql(cls.source, f"INSERT INTO systemhaus(id,name) VALUES('{cls.house}','Systemhaus Ω');"
                        f"INSERT INTO customer(id,systemhaus_id,name) VALUES('{cls.customer}','{cls.house}','Cliente ñ 漢字');"
                        "CREATE TABLE fixture_payload(id integer PRIMARY KEY, value text NOT NULL);"
                        "INSERT INTO fixture_payload SELECT i, md5(i::text) FROM generate_series(1,4000) i;")
            suffix = uuid.uuid4().hex[:12]; cls.restore_user = 'rc_restore_owner_'+suffix
            cls.restore_password = secrets.token_urlsafe(32)+':\\'
            cls.lab.sql('postgres', f'CREATE ROLE {cls.restore_user} LOGIN NOSUPERUSER CREATEDB NOCREATEROLE PASSWORD {literal(cls.restore_password)};', sensitive=True)
            cls.backup_profile = cls.profile('source', cls.source.name, cls.source.owner, cls.source.owner_password)
            cls.restore_profile = cls.profile('restore', 'postgres', cls.restore_user, cls.restore_password)
            cls.before_source = cls.source_snapshot()
        except BaseException:
            cls.lab.close(); raise

    @classmethod
    def tearDownClass(cls):
        try:
            cls.inputs_unchanged = all(sha(Path(p)) == digest for p, digest in cls.guards.items())
            cls.source_unchanged = cls.source_snapshot() == cls.before_source
            assert cls.inputs_unchanged and cls.source_unchanged
        finally:
            cls.lab.close()

    @classmethod
    def profile(cls, label, database, user, password):
        folder = cls.home / ('profile-'+label+'-'+uuid.uuid4().hex); folder.mkdir(); protect_directory(folder)
        secret = folder/'secret.txt'; secret.write_bytes(password.encode('utf-8'))
        path = folder/'profile.json'
        write_json(path, dict(schemaVersion=1, host='127.0.0.1', port=cls.lab.port,
                            database=database, user=user, passwordFile=str(secret)))
        return path

    @classmethod
    def source_snapshot(cls):
        return cls.lab.sql(cls.source, "SELECT (SELECT count(*) FROM schema_migration),"
                           "(SELECT string_agg(name,',' ORDER BY id) FROM customer),"
                           "(SELECT md5(string_agg(value,',' ORDER BY id)) FROM fixture_payload);")

    def call(self, script, arguments, expected, code=None, poison=False):
        command = [str(POWERSHELL), '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                   '-File', str(WINDOWS/script), '-PostgresBinPath', str(self.lab.pg_bin),
                   *[x for k,v in arguments.items() for x in ('-'+k, str(v))]]
        environment = dict(os.environ)
        if poison:
            environment.update(PGHOSTADDR='192.0.2.1', PGHOST='untrusted.invalid', PGPORT='1', PGDATABASE='other',
                               PGUSER='other', PGPASSWORD='POISON-NOT-A-SECRET', PGSERVICE='must-not-load',
                               PGSERVICEFILE=str(self.home/'absent-service.conf'), PGOPTIONS='-c invalid_option=true',
                               PGPASSFILE=str(self.home/'absent-passfile'))
        started = time.monotonic()
        p = subprocess.run(command, env=environment, capture_output=True, timeout=150,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        try: data = json.loads(p.stdout.decode('utf-8-sig'))
        except (ValueError, UnicodeError): data = dict(rawStdout=p.stdout.decode(errors='replace'))
        self.calls.append(dict(case=self._testMethodName, script=script, arguments=arguments,
                               exitCode=p.returncode, seconds=round(time.monotonic()-started,3), report=data,
                               stderr=p.stderr.decode(errors='replace'), childEnvironmentPoisoned=poison))
        self.assertFalse(p.stderr, self.calls[-1]['stderr'])
        self.assertEqual(p.returncode, expected, data)
        self.assertEqual(data['exitCode'], expected); self.assertEqual(data['valid'], expected == 0)
        if code: self.assertEqual(data['code'], code)
        # Reports, commands and stderr never include the source/restore database passwords.
        serialized = json.dumps(self.calls[-1], ensure_ascii=False)
        for password in (self.source.owner_password, self.restore_password):
            self.assertNotIn(password, serialized)
        return data

    def backup(self, label):
        path = self.home/('backup-'+label+'-'+uuid.uuid4().hex)
        result = self.call('New-RackClickDatabaseBackup.ps1',
                           dict(ProfilePath=str(self.backup_profile), DestinationPath=str(path)), 0, 'backup_complete', poison=True)
        self.assertEqual(result['manifestSha256'], sha(path/'manifest.json'))
        self.assertEqual(sorted(p.name for p in path.iterdir()), ['data.dump','manifest.json'])
        return path, result['manifestSha256']

    def restore(self, path, digest, expected=0, code='restore_complete_isolated', name=None, profile=None):
        name = name or 'rc_restore_'+uuid.uuid4().hex
        result = self.call('Restore-RackClickDatabaseBackup.ps1',
                           dict(ProfilePath=str(profile or self.restore_profile), BackupPath=str(path),
                                ExpectedManifestSha256=digest, NewDatabaseName=name), expected, code, poison=True)
        self.assertFalse(result['applicationStartAllowed'])
        return name, result

    def copied_backup(self, label):
        path, _ = self.backup(label)
        altered = self.home/('altered-'+uuid.uuid4().hex)
        shutil.copytree(path, altered); protect_directory(altered)
        return altered

    def test_01_custom_backup_restore_schema9_and_env_isolation(self):
        path, digest = self.backup('roundtrip')
        name, result = self.restore(path, digest)
        self.assertTrue(result['newDatabaseCreated'])
        self.assertEqual(self.lab.sql(name, 'SELECT count(*) FROM schema_migration;'), '9')
        self.assertEqual(self.lab.sql(name, 'SELECT name FROM customer;'), 'Cliente ñ 漢字')
        self.assertEqual(self.lab.sql(name, "SELECT count(*),md5(string_agg(value,',' ORDER BY id)) FROM fixture_payload;"),
                         self.lab.sql(self.source, "SELECT count(*),md5(string_agg(value,',' ORDER BY id)) FROM fixture_payload;"))
        self.assertEqual(self.lab.sql(name, "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid JOIN pg_roles r ON c.relowner=r.oid WHERE n.nspname='public' AND r.rolname<>"+literal(self.restore_user)+';'), '0')
        self.assertEqual(self.lab.sql('postgres', "SELECT count(*) FROM pg_database d,LATERAL aclexplode(d.datacl) a WHERE d.datname="+literal(name)+" AND a.grantee=0 AND a.privilege_type='CONNECT';"), '0')

    def test_02_existing_destination_preserved(self):
        destination = self.home/('already-'+uuid.uuid4().hex); destination.mkdir()
        sentinel = destination/'sentinel.txt'; sentinel.write_bytes(b'preserve-existing')
        self.call('New-RackClickDatabaseBackup.ps1', dict(ProfilePath=str(self.backup_profile),
                  DestinationPath=str(destination)), 1, 'destination_exists')
        self.assertEqual(sentinel.read_bytes(), b'preserve-existing')
        self.assertEqual([p.name for p in destination.iterdir()], ['sentinel.txt'])

    def test_03_failed_backup_is_retained_without_manifest(self):
        profile = self.profile('wrong-password', self.source.name, self.source.owner, secrets.token_urlsafe(32))
        destination = self.home/('failed-'+uuid.uuid4().hex)
        self.call('New-RackClickDatabaseBackup.ps1', dict(ProfilePath=str(profile),
                  DestinationPath=str(destination)), 1, 'postgres_command_failed')
        self.assertTrue((destination/'INCOMPLETE.json').exists())
        self.assertFalse((destination/'manifest.json').exists())

    def test_04_integrity_and_unsafe_backup_before_sql(self):
        path, digest = self.backup('integrity')
        _, result = self.restore(path, '0'*64, 2, 'manifest_hash_mismatch')
        self.assertFalse(result['newDatabaseCreated'])
        altered = self.copied_backup('corrupt'); (altered/'data.dump').write_bytes(b'changed')
        _, result = self.restore(altered, sha(altered/'manifest.json'), 2, 'dump_hash_mismatch')
        self.assertFalse(result['newDatabaseCreated'])
        altered = self.copied_backup('path'); manifest = json.loads((altered/'manifest.json').read_bytes())
        # Int64 value must never mask an earlier invalid field via PS5 logical AND/OR precedence.
        manifest['dumpFile'] = '../outside.dump'; manifest['dumpBytes'] = 3_000_000_000
        write_json(altered/'manifest.json', manifest)
        self.restore(altered, sha(altered/'manifest.json'), 2, 'manifest_invalid')
        (path/'extra.hidden').write_bytes(b'not accepted')
        self.restore(path, digest, 2, 'backup_files_invalid')
        # Junction points only to an owned fixture and is never traversed by the checker.
        alias = self.home/('alias-'+uuid.uuid4().hex)
        p = subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(alias),str(path)], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(p.returncode,0)
        self.restore(alias, digest, 2, 'reparse_rejected')

    def test_05_existing_database_and_missing_createdb(self):
        path, digest = self.backup('collision')
        name = 'rc_restore_'+uuid.uuid4().hex
        self.lab.sql('postgres', f'CREATE DATABASE {name} OWNER {self.restore_user};')
        self.lab.sql(name, 'CREATE TABLE existing_sentinel(value integer); INSERT INTO existing_sentinel VALUES(198);')
        _, result = self.restore(path,digest,1,'new_database_exists',name=name)
        self.assertFalse(result['newDatabaseCreated'])
        self.assertEqual(self.lab.sql(name,'SELECT value FROM existing_sentinel;'),'198')
        self.restore(path,digest,1,'createdb_permission_required',profile=self.backup_profile)

    def test_06_failed_restore_rolls_back_and_keeps_new_database(self):
        altered = self.copied_backup('rollback'); dump = altered/'data.dump'
        content = dump.read_bytes(); dump.write_bytes(content[:len(content)//2])
        manifest = json.loads((altered/'manifest.json').read_bytes())
        manifest.update(dumpBytes=dump.stat().st_size,dumpSha256=sha(dump)); write_json(altered/'manifest.json',manifest)
        name, result = self.restore(altered,sha(altered/'manifest.json'),1,'postgres_command_failed')
        self.assertTrue(result['newDatabaseCreated'])
        self.assertEqual(self.lab.sql(name,"SELECT count(*) FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE n.nspname='public';"),'0')
        self.assertEqual(self.source_snapshot(),self.before_source)

    def test_07_profiles_and_password_acl_reject(self):
        profile = self.profile('bad-host',self.source.name,self.source.owner,self.source.owner_password)
        value = json.loads(profile.read_bytes()); value['host']='localhost'; write_json(profile,value)
        self.call('New-RackClickDatabaseBackup.ps1', dict(ProfilePath=str(profile),DestinationPath=str(self.home/'bad-host')),2,'profile_invalid')
        profile = self.profile('weak-acl',self.source.name,self.source.owner,self.source.owner_password)
        secret = json.loads(profile.read_bytes())['passwordFile']
        subprocess.run(['icacls.exe',secret,'/grant','*S-1-1-0:R'],capture_output=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        self.call('New-RackClickDatabaseBackup.ps1', dict(ProfilePath=str(profile),DestinationPath=str(self.home/'bad-acl')),2,'private_acl_required')
        profile = self.profile('weak-profile-acl',self.source.name,self.source.owner,self.source.owner_password)
        subprocess.run(['icacls.exe',str(profile),'/grant','*S-1-1-0:R'],capture_output=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        self.call('New-RackClickDatabaseBackup.ps1', dict(ProfilePath=str(profile),DestinationPath=str(self.home/'bad-profile-acl')),2,'private_acl_required')

    def test_08_manifest_and_dump_locked_through_restore_validation(self):
        path, digest = self.backup('locked')
        script = self.home/'check-locks.ps1'
        script.write_bytes(r'''param([string]$PostgresBinPath,[string]$Helper,[string]$BackupRoot,[string]$Expected)
. $Helper
$backup = Read-BackupManifest $BackupRoot $Expected
$locked = 0
try {
    foreach ($name in @('manifest.json','data.dump')) {
        try { $stream = [IO.File]::Open((Join-Path $BackupRoot $name),[IO.FileMode]::Open,[IO.FileAccess]::Write,[IO.FileShare]::ReadWrite); $stream.Dispose() }
        catch [IO.IOException] { $locked += 1 }
    }
} finally { $backup.dumpHandle.Dispose(); $backup.manifestHandle.Dispose() }
@{lockedFiles=$locked} | ConvertTo-Json -Compress
if ($locked -ne 2) { exit 1 }
'''.encode('utf-8'))
        p = subprocess.run([str(POWERSHELL),'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),
            '-PostgresBinPath',str(self.lab.pg_bin),'-Helper',str(WINDOWS/'RackClick.Backup.ps1'),'-BackupRoot',str(path),'-Expected',digest],
            capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        data = json.loads(p.stdout.decode('utf-8-sig'))
        self.calls.append(dict(case=self._testMethodName,script='private read-lock probe',exitCode=p.returncode,
                               report=data,stderr=p.stderr.decode(errors='replace')))
        self.assertEqual(p.returncode,0); self.assertFalse(p.stderr); self.assertEqual(data['lockedFiles'],2)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--evidence',required=True); parser.add_argument('--cases',nargs='*')
    options = parser.parse_args(); evidence = Path(options.evidence).resolve(); evidence.mkdir(parents=True,exist_ok=False)
    suite = (unittest.TestSuite(DatabaseBackup(name) for name in options.cases) if options.cases
             else unittest.defaultTestLoader.loadTestsFromTestCase(DatabaseBackup))
    started = time.monotonic()
    with (evidence/'tests.log').open('w',encoding='utf-8') as log:
        result = unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    report = dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,
                  failures=len(result.failures),errors=len(result.errors),successful=result.wasSuccessful(),
                  seconds=round(time.monotonic()-started,3),fixture=str(getattr(DatabaseBackup,'home','not initialized')),
                  sourceHashes=getattr(DatabaseBackup,'guards',{}),inputsUnchanged=getattr(DatabaseBackup,'inputs_unchanged',False),
                  sourceDatabaseUnchanged=getattr(DatabaseBackup,'source_unchanged',False),calls=getattr(DatabaseBackup,'calls',[]),
                  appExecutions=0,existingQaAccess=0)
    write_json(evidence/'result.json',report)
    print(json.dumps({k:report[k] for k in ('testsRun','failures','errors','successful','seconds','fixture')}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__': sys.exit(main())
