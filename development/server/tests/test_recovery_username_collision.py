"""Reproduce the recovery-name collision with an explicit private, frozen DLL.

Fresh PostgreSQL only; no backup/VM/QA/installed service is opened or changed.
The fixture simulates a restored database's identity and pending marker.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import uuid

from pg_support import Lab, Database, WORKSPACE, NO_WINDOW, literal, protect_directory

TABLES = ('schema_migration', 'systemhaus', 'customer', 'app_user', 'user_group',
          'user_group_member', 'permission_grant', 'app_session', 'operation',
          'audit_event', 'app_mfa_user', 'app_mfa_factor', 'app_mfa_challenge',
          'app_mfa_recovery_code')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--owned-operator', action='store_true',
                        help='Run recovery through the real Windows owned-process operator as well as its commit reader')
    args = parser.parse_args()
    dll, output = args.dll.resolve(strict=True), args.output.resolve()
    if not all(p.is_relative_to(WORKSPACE / '.local') for p in (dll, output)):
        raise ValueError('Explicit private DLL and new private output required')
    output.mkdir(parents=True, exist_ok=False)
    protect_directory(output)
    dll_sha = hashlib.sha256(dll.read_bytes()).hexdigest()
    operator = WORKSPACE / 'tools/windows/New-RackClickRecoveredInstance.ps1'
    operator_sha = hashlib.sha256(operator.read_bytes()).hexdigest()
    report = dict(result='FAIL', dllSha256=dll_sha, vmTouched=False, qaTouched=False,
                  newCluster=True, backupRead=False, dotnetBuildPerformed=False,
                  ownedOperator=args.owned_operator, operatorSha256=operator_sha)
    lab, started = Lab('w02-recovery-name-collision'), time.monotonic()
    try:
        with lab:
            instance = uuid.uuid4()
            name, owner = 'rc_db_' + instance.hex, 'rc_owner_' + instance.hex
            password = secrets.token_urlsafe(32)
            directory = lab.directory / name
            directory.mkdir()
            db = Database(name, owner, password, 'unused_runtime', '', directory)
            lab.sql('postgres', f'CREATE ROLE {owner} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(password)};', sensitive=True)
            lab.sql('postgres', f"CREATE DATABASE {name} OWNER {owner} TEMPLATE template0 ENCODING 'UTF8';")
            (directory / 'owner.pgpass').write_text(f'127.0.0.1:{lab.port}:{name}:{owner}:{password}\n', encoding='utf-8')
            bootstrap = lab.bootstrap(db, 'admin-prueba', secrets.token_urlsafe(40), dll=dll)
            (output / 'bootstrap.stdout').write_text(bootstrap.stdout, encoding='utf-8')
            (output / 'bootstrap.stderr').write_text(bootstrap.stderr, encoding='utf-8')
            assert bootstrap.returncode == 0, 'Synthetic bootstrap must succeed'
            assert lab.sql(db, 'SELECT max(version) FROM schema_migration') == '14'
            backup_sha = '1' * 64
            marker = f'RackClickRecoveryPending:{instance}:{backup_sha}'
            lab.sql(db, f'COMMENT ON DATABASE {name} IS {literal(marker)};')

            def snapshot():
                rows = {}
                for table in TABLES:  # Identifiers are this internal closed list.
                    data = lab.sql(db, f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM public.{table} t")
                    rows[table] = hashlib.sha256(data.encode('utf-8')).hexdigest()
                rows['databaseMarker'] = lab.sql(db, "SELECT pg_catalog.shobj_description(oid,'pg_database') FROM pg_catalog.pg_database WHERE datname=current_database()")
                return rows

            def recover(user, label):
                env = {k: v for k, v in lab.environment().items()
                       if not k.startswith(('Recovery', 'ConnectionStrings', 'Bootstrap', 'ASPNETCORE', 'Kestrel', 'RackClick'))}
                env.update(ConnectionStrings__RackClick=db.connection(lab.port, runtime=False),
                           Recovery__User=user, Recovery__ExpectedDatabase=name,
                           Recovery__BackupSha256=backup_sha)
                stdin = secrets.token_urlsafe(40) + '\n'
                command = [str(lab.dotnet), str(dll), '--recover-admin']
                if args.owned_operator:
                    config = output / (label + '-private.json')
                    config.write_text(json.dumps(dict(dotnet=str(lab.dotnet), dll=str(dll),
                        root=str(directory), logs=str(output), user=user,
                        connection=db.connection(lab.port, runtime=False),
                        database=name, instanceId=str(instance), backupSha=backup_sha,
                        password=stdin.rstrip('\n'))), encoding='utf-8')
                    driver = output / 'owned-recovery.ps1'
                    if not driver.exists():
                        driver.write_text(r'''$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/Modules'
. (Join-Path $env:W02_OPERATOR_ROOT 'tools/windows/New-RackClickRecoveredInstance.ps1')
$cfg=[IO.File]::ReadAllText($env:W02_RECOVERY_FIXTURE)|ConvertFrom-Json
$child=New-InstanceEnvironment @{DOTNET_ROOT=[IO.Path]::GetDirectoryName($cfg.dotnet);DOTNET_NOLOGO='1';DOTNET_CLI_TELEMETRY_OPTOUT='1';ASPNETCORE_ENVIRONMENT='Development';ConnectionStrings__RackClick=$cfg.connection;Recovery__User=$cfg.user;Recovery__ExpectedDatabase=$cfg.database;Recovery__BackupSha256=$cfg.backupSha}
try{
    $result=Invoke-RecoveryOwnedChild $cfg.dotnet @($cfg.dll,'--recover-admin') $cfg.root $child $cfg.logs 'recover-admin' -InputText ($cfg.password+"`n") -TimeoutSeconds 30
    $value=Read-RecoveryCommitResult $result $cfg.instanceId
    $value|ConvertTo-Json -Compress
    exit 0
}catch{
    $code=[string]$_.Exception.Data['recoveryCode']
    if($code-cnotin@('recovery_username_exists','recover_admin_failed','recovery_output_invalid')){$code='owned_operator_failed'}
    [ordered]@{status='rejected';error=$code}|ConvertTo-Json -Compress
    exit 1
}
''', encoding='utf-8')
                    env.update(W02_OPERATOR_ROOT=str(WORKSPACE), W02_RECOVERY_FIXTURE=str(config))
                    command = [str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'),
                               '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(driver)]
                    stdin = None
                process = subprocess.run(command,
                                         input=stdin, text=True,
                                         encoding='utf-8', capture_output=True, timeout=30,
                                         env=env, creationflags=NO_WINDOW)
                (output / (label + '.stdout')).write_text(process.stdout, encoding='utf-8')
                (output / (label + '.stderr')).write_text(process.stderr, encoding='utf-8')
                assert not process.stderr, 'CLI stderr must be empty'
                return process.returncode, json.loads(process.stdout)

            before = snapshot()
            code, rejected = recover('admin-prueba', 'existing-name')
            assert code == 1 and rejected == {'status': 'rejected', 'error': 'recovery_username_exists'}
            assert snapshot() == before, 'Rejected recovery must not mutate rows or marker'
            report['existingName'] = dict(exitCode=code, **rejected, fourteenTablesAndMarkerUnchanged=True)
            code, accepted = recover('wascar', 'new-name')
            assert code == 0, 'A distinct new recovery administrator must succeed'
            assert lab.sql(db, "SELECT count(*) FROM app_user WHERE username='admin-prueba'") == '1'
            assert lab.sql(db, "SELECT count(*) FROM app_user WHERE username='wascar'") == '1'
            assert lab.sql(db, "SELECT count(*) FROM audit_event WHERE action='deployment.recover'") == '1'
            assert not snapshot()['databaseMarker'], 'Successful recovery consumes pending marker'
            report.update(result='PASS', newName=dict(exitCode=code, originalUserRetained=True,
                          newUserCreated=True, recoveryAuditCount=1, markerConsumed=True),
                          postgresql=lab.sql('postgres', 'SHOW server_version'), schema=14)
    except Exception as error:
        report.update(errorType=type(error).__name__)
        # Full diagnostics remain private; never print SQL/connection material.
        (output / 'failure-private.txt').write_text(str(error), encoding='utf-8')
    finally:
        lab.close()
        report.update(labStopped=not lab.running, inputsUnchanged=dll_sha == hashlib.sha256(dll.read_bytes()).hexdigest()
                      and operator_sha == hashlib.sha256(operator.read_bytes()).hexdigest(),
                      elapsedSeconds=round(time.monotonic() - started, 2))
        (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))
    return 0 if report['result'] == 'PASS' and report['labStopped'] and report['inputsUnchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
