"""Pinned F0705 Windows/PG17 enrolment closure. Fresh owned laboratories; never VM/installed DB."""
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
    parser.add_argument('--mode', choices=['closure', 'regression'], default='closure')
    args = parser.parse_args()
    source = args.source_root.resolve(strict=True)
    if not source.is_relative_to((ROOT / '.local').resolve()):
        raise ValueError('isolated_source_required')
    server = source / 'development/server'
    dll = server / 'src/RackClick.Server/bin/Release/net10.0/RackClick.Server.dll'
    tests = server / 'tests/RackClick.Quality.Tests/bin/Release/net10.0/RackClick.Quality.Tests.dll'

    def pins():
        if sha(dll) != args.expected_server_sha256 or sha(tests) != args.expected_tests_sha256:
            raise ValueError('enrollment_binary_pin_invalid')

    pins()
    lab = Lab('f0705-enrollment')
    base_env = lab.environment

    def environment():
        env = base_env()
        for name in list(env):
            if name.startswith(('RACKCLICK_TEST_', 'RACKCLICK_F0', 'ConnectionStrings__', 'MfaKeyStore__', 'SqlSecret__',
                                'CORECLR_', 'COR_', 'DOTNET_STARTUP_', 'DOTNET_Diagnostic', 'DOTNET_EnableEvent', 'DOTNET_EnableProfil')):
                env.pop(name)
        env['DOTNET_EnableDiagnostics'] = '0'
        return env

    lab.environment = environment
    rows = []

    def execute(selection, env, label):
        pins()
        command = [str(lab.dotnet), 'test', 'tests/RackClick.Quality.Tests/RackClick.Quality.Tests.csproj', '-c', 'Release',
                   '--no-build', '--no-restore', '--filter', selection,
                   '--logger', 'trx;LogFileName=' + str(lab.directory / (label + '.trx')),
                   '-bl:' + str(lab.directory / (label + '-{}.binlog'))]
        with (lab.directory / (label + '.private.log')).open('wb') as log:
            rc = subprocess.run(command, cwd=server, env=env, stdout=log, stderr=subprocess.STDOUT,
                                timeout=240, creationflags=NO_WINDOW).returncode
        counts = ET.parse(lab.directory / (label + '.trx')).find('.//{*}Counters').attrib
        rows.append(dict(case=label, exitCode=rc, counts=counts))
        if rc or int(counts['notExecuted']) or not int(counts['passed']):
            raise RuntimeError('enrollment_case_failed_' + label)
        pins()

    try:
        lab.start()
        if args.mode == 'regression':
            env = environment()
            env['RACKCLICK_TEST_PG_ADMIN'] = (f'Host=127.0.0.1;Port={lab.port};Database=postgres;Username={lab.admin};'
                                            f'Password={lab.admin_password};Pooling=false;SSL Mode=Disable')
            execute('FullyQualifiedName~MfaEnrollmentTests|FullyQualifiedName~MfaHttpTests|FullyQualifiedName~MfaGraceEnforcementTests',
                    env, 'affected-regression')
        else:
            for label, legacy in [('new-account-due', False), ('existing-account-due', True)]:
                identity = uuid.uuid4()
                private = lab.directory / identity.hex
                private.mkdir()
                db = Database('rc_db_' + identity.hex, 'rc_owner_' + identity.hex, secrets.token_urlsafe(32),
                              'rc_runtime_' + identity.hex, secrets.token_urlsafe(32), private)
                lab.sql('postgres', f'CREATE ROLE {db.owner} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(db.owner_password)}; '
                                    f'CREATE ROLE {db.runtime} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(db.runtime_password)};', sensitive=True)
                lab.sql('postgres', f"CREATE DATABASE {db.name} OWNER {db.owner} TEMPLATE template0 ENCODING 'UTF8';")
                (private / 'owner.pgpass').write_text(f'127.0.0.1:{lab.port}:*:{db.owner}:{db.owner_password}\n', 'utf-8')
                boot = lab.bootstrap(db, 'synthetic-enrollment-admin', secrets.token_urlsafe(32), dll=dll)
                (private / 'bootstrap.private.log').write_text(boot.stdout + boot.stderr, 'utf-8')
                if boot.returncode or lab.sql(db, 'SELECT count(*),max(version) FROM schema_migration') != '46|46':
                    raise RuntimeError('enrollment_bootstrap46_failed')
                lab.grant_runtime(db)
                context = private / 'context.private.json'
                context.write_text(json.dumps(dict(installationId=str(identity), legacy=legacy, instancesRoot=str(private / 'i'),
                                                   ownerConnection=db.connection(lab.port, False), runtimeConnection=db.connection(lab.port))), 'utf-8')
                env = environment()
                env['RACKCLICK_F0705_CONTEXT'] = str(context)
                execute('FullyQualifiedName~MfaEnrollmentClosureTests.RestrictedEnrollmentWorker', env, label)
                rows[-1].update(ordinaryUser=True, graceDays=45, realWindowsProvider=True, sqlRuntimeIdentityObserved=True,
                                restrictedApiStages=3, routesPerStage=4, cookieRepresentations=2, noPreConfirmationSession=True)
    finally:
        lab.close()
    pins()
    result = dict(success=True, postgresql='17.11', schema=46 if args.mode == 'closure' else 'historical fixtures', mode=args.mode,
                  cases=rows, serverSha256=sha(dll), testsSha256=sha(tests), ownClusterStopped=not lab.running,
                  vmOperations=0, installedServiceOperations=0, httpTransport='TestServer in-memory', tlsTested=False,
                  realServiceSidTested=False, privateLab=str(lab.directory))
    (lab.directory / 'result-sanitized.json').write_text(json.dumps(result, indent=2) + '\n', 'utf-8')
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
