"""Run F0602 census tests against three new PostgreSQL17 databases, never an installed instance.

Requires an already-built isolated source copy under .local; restore/build is a
separate recorded step. Passwords and full logs remain in the private lab.
"""
from pathlib import Path
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
import secrets
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import Lab, NO_WINDOW, literal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--expected-tests-sha256', required=True)
    parser.add_argument('--expected-server-sha256', required=True)
    args = parser.parse_args()
    source = args.source_root.resolve(strict=True)
    if not source.is_relative_to((ROOT / '.local').resolve()):
        raise ValueError('isolated_source_root_required')
    server = source / 'development/server'
    tests = server / 'tests/RackClick.Quality.Tests/bin/Release/net10.0/RackClick.Quality.Tests.dll'
    product = server / 'src/RackClick.Server/bin/Release/net10.0/RackClick.Server.dll'
    for path, expected in [(tests, args.expected_tests_sha256), (product, args.expected_server_sha256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('f0602_binary_reference_mismatch')
    lab = Lab('f0602-key-inventory')
    saved_env = lab.environment

    def environment():
        result = saved_env()
        for name in list(result):
            if name.startswith(('ConnectionStrings__', 'Bootstrap__', 'MfaKeyStore__', 'RACKCLICK_TEST_', 'RACKCLICK_F0602_')):
                result.pop(name, None)
        result['DOTNET_CLI_HOME'] = str(lab.directory / 'dotnet-home')
        return result

    lab.environment = environment
    summary = None
    try:
        lab.start()
        if lab.sql('postgres', 'SHOW server_version_num;', admin=True) != '170011':
            raise RuntimeError('postgres17_11_required')
        databases = {}
        for label in ('POPULATED', 'EMPTY', 'INVALID_VERSION'):
            db = lab.create_database('f0602-' + label.lower())
            result = lab.bootstrap(db, 'synthetic-inventory-admin', secrets.token_urlsafe(24), dll=product)
            (db.directory / 'bootstrap.private.log').write_text(result.stdout + result.stderr, 'utf-8')
            if result.returncode:
                raise RuntimeError('f0602_bootstrap_failed')
            if lab.sql(db, 'SELECT count(*),max(version) FROM schema_migration') != '45|45':
                raise RuntimeError('schema45_fixture_required')
            if label != 'EMPTY':
                versions = [(1, 'pending'), (1, 'active'), (1, 'disabled'), (7, 'active'), (7, 'active')]
                if label == 'INVALID_VERSION':
                    versions = [(1000001, 'disabled')]
                commands = []
                for index, (version, state) in enumerate(versions):
                    user = str(uuid.uuid4())
                    commands.append("INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT "
                                    f"'{user}',id,'inventory-fixture-{index}',{literal(secrets.token_urlsafe(32))} FROM systemhaus")
                    # Census must never decrypt a factor; opaque synthetic bytes exercise metadata-only reads.
                    commands.append("INSERT INTO app_mfa_factor(systemhaus_id,user_id,state,secret_ciphertext,key_version) SELECT "
                                    f"id,'{user}','{state}',decode('{secrets.token_hex(48)}','hex'),{version} FROM systemhaus")
                lab.sql(db, ';'.join(commands), sensitive=True)
            lab.sql(db, f'REVOKE CREATE ON SCHEMA public FROM PUBLIC; GRANT USAGE ON SCHEMA public TO {db.runtime}; '
                        f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO {db.runtime};')
            databases[label] = db
        populated = databases['POPULATED']
        fingerprint = "SELECT md5(COALESCE(jsonb_agg(to_jsonb(f) ORDER BY systemhaus_id,user_id)::text,'')) FROM app_mfa_factor f"
        before = lab.sql(populated, fingerprint)
        backup = lab.directory / 'database-backup'
        metadata = lab.directory / 'separate-inventory'
        backup.mkdir(); metadata.mkdir()
        pg_env = environment()
        pg_env['PGPASSFILE'] = str(populated.directory / 'owner.pgpass')
        with (lab.directory / 'dump.private.log').open('wb') as log:
            dumped = subprocess.run([str(lab.pg_bin / 'pg_dump.exe'), '-w', '-h', '127.0.0.1', '-p', str(lab.port),
                                     '-U', populated.owner, '-F', 'c', '--no-owner', '--no-privileges', '-f', str(backup / 'data.dump'), populated.name],
                                    env=pg_env, stdout=log, stderr=subprocess.STDOUT, creationflags=NO_WINDOW, timeout=60)
        if dumped.returncode:
            raise RuntimeError('quiescent_fixture_dump_failed')
        dump = backup / 'data.dump'
        dump_hash = hashlib.sha256(dump.read_bytes()).hexdigest()
        manifest = dict(schemaVersion=1, kind='RackClickDatabaseBackup', postgresVersion='17.11', format='custom',
                        createdUtc=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), dumpFile='data.dump',
                        dumpBytes=dump.stat().st_size, dumpSha256=dump_hash)
        (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', 'utf-8')
        manifest_hash = hashlib.sha256((backup / 'manifest.json').read_bytes()).hexdigest()
        context = dict(backupDirectory=str(backup), inventoryPath=str(metadata / 'mfa-inventory.json'),
                       manifestSha256=manifest_hash, dumpSha256=dump_hash)
        context_path = lab.directory / 'backup-context.json'
        context_path.write_text(json.dumps(context, indent=2) + '\n', 'utf-8')

        def native_check(expected, label):
            quote = lambda value: "'" + str(value).replace("'", "''") + "'"
            script = "$PostgresBinPath=" + quote(lab.pg_bin) + ";. " + quote(ROOT / 'tools/windows/RackClick.Backup.ps1') + ";"
            script += "$v=$null;try{$v=Read-BackupManifest -Path " + quote(backup) + ' -ExpectedHash ' + quote(manifest_hash)
            script += ";'legacy_backup_verified'}catch{[Console]::WriteLine([string]$_.Exception.Data['code']);exit 2}finally{if($null-ne$v){$v.manifestHandle.Dispose();$v.dumpHandle.Dispose()}}"
            checked = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                      '-EncodedCommand', base64.b64encode(script.encode('utf-16le')).decode('ascii')],
                                     capture_output=True, creationflags=NO_WINDOW, timeout=30)
            (lab.directory / (label + '.private.log')).write_bytes(checked.stdout + checked.stderr)
            if checked.returncode != expected:
                raise RuntimeError('native_backup_fixture_contract_failed')
            expected_code = b'legacy_backup_verified' if expected == 0 else b'backup_files_invalid'
            if expected_code not in checked.stdout:
                raise RuntimeError('native_backup_fixture_rejection_cause_invalid')

        native_check(0, 'legacy-before')
        env = environment()
        env.update({'RACKCLICK_F0602_PG_' + label: db.connection(lab.port) for label, db in databases.items()})
        env['RACKCLICK_F0602_BACKUP_CONTEXT'] = str(context_path)
        cmd = [str(lab.dotnet), 'test', 'tests/RackClick.Quality.Tests/RackClick.Quality.Tests.csproj',
               '-c', 'Release', '--no-build', '--no-restore', '--filter', 'FullyQualifiedName~MfaFactorKeyInventoryReaderTests',
               '--logger', 'trx;LogFileName=' + str(lab.directory / 'reader.trx'),
               '-bl:' + str(lab.directory / 'reader-{}.binlog')]
        with (lab.directory / 'tests.private.log').open('wb') as log:
            result = subprocess.run(cmd, cwd=server, env=env, stdout=log, stderr=subprocess.STDOUT,
                                    creationflags=NO_WINDOW, timeout=180)
        unchanged = lab.sql(populated, fingerprint) == before
        if not unchanged:
            raise RuntimeError('census_fixture_was_modified')
        native_check(0, 'legacy-after')
        sidecar = Path(context['inventoryPath'])
        if sidecar.exists():
            unexpected = backup / 'unexpected-inventory.json'
            # Own extra file only: demonstrate the historic two-file contract still rejects extras.
            with unexpected.open('xb') as stream:
                stream.write(sidecar.read_bytes())
            try:
                native_check(2, 'legacy-extra-rejected')
            finally:
                unexpected.unlink()
            native_check(0, 'legacy-restored')
        summary = dict(success=result.returncode == 0, exitCode=result.returncode, databasesCreated=3,
                       role='new SELECT-only runtime roles', productSchema=45, installedDatabaseAccessed=False,
                       ciphertextUsedForCensus=False, sourceRootIsolated=True, serverAssemblySha256=args.expected_server_sha256,
                       testsAssemblySha256=args.expected_tests_sha256, labDirectory=str(lab.directory),
                       factorRowsUnchanged=unchanged, customDumpBytes=dump.stat().st_size, legacyBackupStillTwoFiles=True,
                       separateInventoryWritten=sidecar.exists(), historicExtraFileRejectionTested=sidecar.exists(),
                       concurrentWritersInFixture=False, realExternalCustodyTested=False)
    finally:
        lab.close()
    assert summary is not None
    summary['ownClusterStopped'] = not lab.running
    (lab.directory / 'result-sanitized.json').write_text(json.dumps(summary, indent=2) + '\n', 'utf-8')
    print(json.dumps(summary))
    return summary['exitCode']


if __name__ == '__main__':
    raise SystemExit(main())
