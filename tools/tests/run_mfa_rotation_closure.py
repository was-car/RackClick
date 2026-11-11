"""F0604 pinned retained-backup generations in fresh Windows/PG17 laboratories only."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import Lab, Database, literal, NO_WINDOW


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--expected-server-sha256', required=True)
    parser.add_argument('--expected-tests-sha256', required=True)
    args = parser.parse_args()
    source = args.source_root.resolve(strict=True)
    if not source.is_relative_to((ROOT / '.local').resolve()):
        raise ValueError('isolated_source_required')
    server = source / 'development/server'
    dll = server / 'src/RackClick.Server/bin/Release/net10.0/RackClick.Server.dll'
    tests = server / 'tests/RackClick.Quality.Tests/bin/Release/net10.0/RackClick.Quality.Tests.dll'

    def pins():
        if sha(dll) != args.expected_server_sha256 or sha(tests) != args.expected_tests_sha256:
            raise ValueError('closure_binary_pin_invalid')

    pins()
    lab = Lab('f0604-closure')
    targets, phases = [], []
    base_env = lab.environment

    def environment():
        env = base_env()
        for name in list(env):
            if name.startswith(('RACKCLICK_TEST_', 'RACKCLICK_F060', 'ConnectionStrings__', 'MfaKeyStore__', 'SqlSecret__',
                                'CORECLR_', 'COR_', 'DOTNET_STARTUP_', 'DOTNET_Diagnostic', 'DOTNET_EnableEvent', 'DOTNET_EnableProfil')):
                env.pop(name)
        env['DOTNET_EnableDiagnostics'] = '0'
        return env

    lab.environment = environment

    def database(cluster, identity, bootstrap):
        private = cluster.directory / 'native'
        private.mkdir()
        db = Database('rc_db_' + identity.hex, 'rc_owner_' + identity.hex, secrets.token_urlsafe(32),
                      'rc_runtime_' + identity.hex, secrets.token_urlsafe(32), private)
        cluster.sql('postgres', f'CREATE ROLE {db.owner} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(db.owner_password)}; '
                               f'CREATE ROLE {db.runtime} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(db.runtime_password)};', sensitive=True)
        cluster.sql('postgres', f"CREATE DATABASE {db.name} OWNER {db.owner} TEMPLATE template0 ENCODING 'UTF8';")
        (private / 'owner.pgpass').write_text(f'127.0.0.1:{cluster.port}:*:{db.owner}:{db.owner_password}\n', 'utf-8')
        if bootstrap:
            boot = cluster.bootstrap(db, 'synthetic-closure-admin', secrets.token_urlsafe(32), dll=dll)
            (private / 'bootstrap.private.log').write_text(boot.stdout + boot.stderr, 'utf-8')
            if boot.returncode or cluster.sql(db, 'SELECT count(*),max(version) FROM schema_migration') != '46|46':
                raise RuntimeError('closure_bootstrap46_failed')
        return db

    def execute(context, label):
        pins()
        env = environment()
        env['RACKCLICK_F0604_CONTEXT'] = str(context)
        command = [str(lab.dotnet), 'test', 'tests/RackClick.Quality.Tests/RackClick.Quality.Tests.csproj', '-c', 'Release',
                   '--no-build', '--no-restore', '--filter', 'FullyQualifiedName~MfaRotationClosureTests',
                   '--logger', 'trx;LogFileName=' + str(lab.directory / (label + '.trx')),
                   '-bl:' + str(lab.directory / (label + '-{}.binlog'))]
        with (lab.directory / (label + '.private.log')).open('wb') as log:
            rc = subprocess.run(command, cwd=server, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180, creationflags=NO_WINDOW).returncode
        counts = ET.parse(lab.directory / (label + '.trx')).find('.//{*}Counters').attrib
        phases.append(dict(phase=label, exitCode=rc, counts=counts))
        if rc or int(counts['notExecuted']) or int(counts['passed']) != 1:
            raise RuntimeError('closure_phase_failed_' + label)
        pins()

    success = False
    try:
        lab.start()
        identity = uuid.uuid4()
        db = database(lab, identity, True)
        private = db.directory
        context = private / 'context.private.json'
        value = dict(installationId=str(identity), ownerConnection=db.connection(lab.port, False),
                     instancesRoot=str(private / 'i'), privateRoot=str(private), postgresBin=str(lab.pg_bin),
                     ownerPgpass=str(private / 'owner.pgpass'), stage='seed')
        context.write_text(json.dumps(value), 'utf-8')
        execute(context, 'seed')
        value['stage'] = 'rotate'
        context.write_text(json.dumps(value), 'utf-8')
        execute(context, 'two-rotations')
        state = json.loads((private / 'state.private.json').read_text('utf-8'))
        if len(state['backups']) != 3:
            raise RuntimeError('three_retained_generations_required')
        for index, backup in enumerate(state['backups']):
            dump = Path(backup['directory']) / 'database/data.dump'
            if sha(dump) != backup['dumpHash']:
                raise RuntimeError('backup_changed_before_restore')
            original = lab.sql(db, "SELECT md5(string_agg(encode(secret_ciphertext,'hex'),',' ORDER BY user_id)),(SELECT count(*) FROM app_mfa_rotation_witness) FROM app_mfa_factor")
            target = Lab('f0604-restore')
            targets.append(target)
            try:
                target.start()
                copy = database(target, identity, False)
                env = environment()
                for name in list(env):
                    if name.startswith('PG'):
                        env.pop(name)
                env['PGPASSFILE'] = str(copy.directory / 'owner.pgpass')
                command = [str(lab.pg_bin / 'pg_restore.exe'), '-w', '-h', '127.0.0.1', '-p', str(target.port), '-U', copy.owner,
                           '--single-transaction', '--exit-on-error', '--no-owner', '--no-acl', '-d', copy.name, str(dump)]
                with (lab.directory / (f'restore-{index}.private.log')).open('wb') as log:
                    rc = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60, creationflags=NO_WINDOW).returncode
                if rc:
                    raise RuntimeError('retained_backup_restore_failed')
                restored = dict(value, stage='restore', ownerConnection=copy.connection(target.port, False),
                                backupIndex=index, restoreRoot=str(copy.directory))
                target_context = copy.directory / 'context.private.json'
                target_context.write_text(json.dumps(restored), 'utf-8')
                execute(target_context, f'authenticate-retained-{index}')
                if lab.sql(db, "SELECT md5(string_agg(encode(secret_ciphertext,'hex'),',' ORDER BY user_id)),(SELECT count(*) FROM app_mfa_rotation_witness) FROM app_mfa_factor") != original:
                    raise RuntimeError('restore_changed_live_source')
                phases[-1].update(backupGeneration=index, factorVersions=backup['versions'], sourceUnchanged=True,
                                  actualCustomRestore=True, everyFactorAuthenticatedWithLiveAndRecoveredKeys=True)
            finally:
                target.close()
        success = True
    finally:
        lab.close()
    pins()
    result = dict(success=success, postgresql='17.11', schema=46, phases=phases,
                  serverSha256=sha(dll), testsSha256=sha(tests), retainedBackups=3, rotations=2, finalActiveVersion=9,
                  ownClustersStopped=all(not x.running for x in [lab, *targets]), clusterCount=1 + len(targets),
                  vmOperations=0, installedServiceOperations=0, publicRotation=False, powerFailureTested=False,
                  privateLab=str(lab.directory))
    (lab.directory / 'result-sanitized.json').write_text(json.dumps(result, indent=2) + '\n', 'utf-8')
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
