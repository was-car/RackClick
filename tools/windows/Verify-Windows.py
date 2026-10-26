"""Reproducible developer verification. This is not a product installer.

Each run has a new evidence directory, stops on the first failing command, and
records the actual Windows environment and input hashes. No old result is reused.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import uuid
from windows_job import run_isolated

ROOT = Path(__file__).resolve().parents[2]
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def utc():
    return datetime.now(timezone.utc).isoformat()


def source_hashes():
    paths = [ROOT / 'development/toolchain.lock.json', ROOT / 'development/server/global.json']
    for directory in ('tools', 'development/server/src', 'development/server/database',
                      'development/server/tests', 'development/frontend'):
        paths.extend(p for p in (ROOT / directory).rglob('*') if p.is_file()
                     and not {'bin', 'obj', 'node_modules', '__pycache__', 'dist', 'generated', 'rc9-reference'}.intersection(p.parts))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', choices=('foundation', 'inventory'), default='inventory')
    parser.add_argument('--evidence', type=Path, help='New directory beneath workspace/evidence')
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('Native Windows execution is required; Linux results must be recorded separately')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    evidence = (args.evidence or ROOT / 'evidence' / ('windows-verification-' + run_id)).resolve()
    if not evidence.is_relative_to((ROOT / 'evidence').resolve()) or evidence == (ROOT / 'evidence').resolve():
        parser.error('Evidence must be a new child directory beneath workspace/evidence')
    if evidence.exists():
        parser.error('Evidence directory already exists and will not be overwritten')
    evidence.mkdir(parents=True, exist_ok=False)
    record = {'runId': run_id, 'startedUtc': utc(), 'platform': platform.platform(),
              'python': platform.python_version(), 'scope': args.scope, 'preflightOnly': args.preflight_only,
              'historicalResultsReused': False, 'commands': [], 'status': 'FAIL'}
    environment = dict(os.environ)
    exit_code = 1

    def run(label, command, cwd=ROOT, timeout=900):
        logfile = evidence / (label + '.log')
        item = {'label': label, 'command': [str(a) for a in command], 'cwd': str(cwd), 'startedUtc': utc()}
        record['commands'].append(item)
        print(f'Running {label}', flush=True)
        with logfile.open('xb') as stream:
            result = run_isolated(command, cwd=cwd, env=environment, stdout=stream, stderr=stream, timeout=timeout)
        item.update(exitCode=result.returncode, finishedUtc=utc(), log=logfile.name)
        if result.returncode:
            raise RuntimeError(f'{label} returned {result.returncode}')

    try:
        lock = json.loads((ROOT / 'development/toolchain.lock.json').read_text(encoding='utf-8-sig'))
        components = {row['id']: row for row in lock['components']}
        paths = {key: ROOT / '.local' / value['installDirectory'] / value['executable']
                 for key, value in components.items()}
        if any(not p.is_file() for p in paths.values()):
            raise RuntimeError('Run tools/windows/Initialize-Toolchain.ps1 first')
        pinned_sdk = json.loads((ROOT / 'development/server/global.json').read_text())['sdk']['version']
        if pinned_sdk != components['dotnet']['version']:
            raise RuntimeError('SDK lock/global.json mismatch')
        environment.update(DOTNET_ROOT=str(paths['dotnet'].parent),
                           DOTNET_CLI_HOME=str(ROOT / '.local/dotnet-home'),
                           DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_NOLOGO='1',
                           DOTNET_GENERATE_ASPNET_CERTIFICATE='false',
                           DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='1',
                           NUGET_PACKAGES=str(ROOT / '.local/nuget/packages'),
                           PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', PGCLIENTENCODING='UTF8')
        environment['PATH'] = os.pathsep.join(str(p.parent) for p in paths.values()) + os.pathsep + environment['PATH']
        record['versions'] = {}
        for key, executable in paths.items():
            output = subprocess.check_output([str(executable), '--version'], env=environment,
                                             cwd=ROOT / 'development/server', creationflags=NO_WINDOW, timeout=30).decode().strip()
            record['versions'][key] = output
            if output != components[key]['versionOutput']:
                raise RuntimeError(f'Unexpected {key} version')
        record['sourceSha256Before'] = source_hashes()
        if not args.preflight_only:
            run('hash-helper', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tools/tests', '-v'])
            run('server-build', [str(paths['dotnet']), 'msbuild', 'RackClick.sln', '-t:Restore,Build',
                '-p:Configuration=Release', '-p:RestoreLockedMode=true',
                '-p:RestoreSources=https://api.nuget.org/v3/index.json', '-m:1', '-nr:false', '-v:minimal'], ROOT / 'development/server')
            run('domain', [str(paths['dotnet']), 'development/server/tests/RackClick.Domain.Tests/bin/Release/net10.0/RackClick.Domain.Tests.dll'])
            run('http-failclosed', [sys.executable, '-B', 'development/server/tests/test_http_failclosed.py', str(paths['dotnet'])])
            run('postgres-foundation', [sys.executable, '-B', 'development/server/tests/test_postgres.py', '--evidence', str(evidence / 'postgres-foundation')])
            if args.scope == 'inventory':
                run('postgres-inventory', [sys.executable, '-B', 'development/server/tests/test_inventory_postgres.py', '--evidence', str(evidence / 'postgres-inventory')])
                run('postgres-admin', [sys.executable, '-B', 'development/server/tests/test_admin_users.py', '--evidence', str(evidence / 'postgres-admin')])
            run('frontend-build', ['powershell.exe', '-NoProfile', '-File', str(ROOT / 'development/frontend/Build-Frontend.ps1')])
            run('browser-foundation', [sys.executable, '-B', 'development/server/tests/run_frontend_smoke.py', '--output', str(evidence / 'browser-foundation')])
            if args.scope == 'inventory':
                run('browser-inventory', [sys.executable, '-B', 'development/server/tests/run_frontend_smoke.py',
                    '--scenario', 'browser-inventory.mjs', '--output', str(evidence / 'browser-inventory')])
                run('browser-recovery', [sys.executable, '-B', 'development/server/tests/run_frontend_smoke.py',
                    '--scenario', 'browser-recovery.mjs', '--output', str(evidence / 'browser-recovery')])
                run('browser-impact', [sys.executable, '-B', 'development/server/tests/run_frontend_smoke.py',
                    '--scenario', 'browser-impact.mjs', '--output', str(evidence / 'browser-impact')])
                run('browser-power', [sys.executable, '-B', 'development/server/tests/run_frontend_smoke.py',
                    '--scenario', 'browser-power.mjs', '--output', str(evidence / 'browser-power')])
                run('browser-admin', [sys.executable, '-B', 'development/server/tests/run_frontend_smoke.py',
                    '--scenario', 'browser-admin.mjs', '--output', str(evidence / 'browser-admin')])
                run('browser-admin-groups', [sys.executable, '-B', 'development/server/tests/run_frontend_smoke.py',
                    '--scenario', 'browser-admin-groups.mjs', '--output', str(evidence / 'browser-admin-groups')])
            record['serverDllSha256'] = hashlib.sha256((ROOT / 'development/server/src/RackClick.Server/bin/Release/net10.0/RackClick.Server.dll').read_bytes()).hexdigest()
        record['sourcesUnchanged'] = record['sourceSha256Before'] == source_hashes()
        if not record['sourcesUnchanged']:
            raise RuntimeError('Sources changed during verification; this run cannot certify one build')
        record['status'] = 'PREFLIGHT_PASS' if args.preflight_only else 'PASS'
        exit_code = 0
    except Exception as error:
        # All commands here have public arguments; never capture a fixture's environment.
        record['failureType'] = type(error).__name__
        record['failure'] = str(error)
    finally:
        record['finishedUtc'] = utc()
        (evidence / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'status': record['status'], 'evidence': str(evidence)}, indent=2), flush=True)
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
