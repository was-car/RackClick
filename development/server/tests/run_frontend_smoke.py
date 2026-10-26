"""Run the RC9 browser scenario on a new native PostgreSQL fixture, without CLI secrets."""
import argparse
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import platform
import secrets
import subprocess
import sys
from pg_support import Lab, WORKSPACE, DEFAULT_DLL, toolchain, NO_WINDOW
sys.path.insert(0, str(WORKSPACE / 'tools/windows'))
from windows_job import run_isolated


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scenario', default='browser-smoke.mjs', help='Script under development/frontend/tests')
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    frontend = WORKSPACE / 'development/frontend'
    scenario = (frontend / 'tests' / args.scenario).resolve()
    if not scenario.is_relative_to((frontend / 'tests').resolve()) or not scenario.is_file() or scenario.suffix != '.mjs':
        parser.error('Scenario must be an existing .mjs under frontend/tests')
    if args.timeout < 1:
        parser.error('Timeout must be positive')
    if args.output.exists():
        parser.error('Evidence directory already exists; choose a new one')
    args.output.mkdir(parents=True)
    assert (frontend / 'dist/index.html').is_file(), 'Build the frontend first'
    def hashes():
        paths = [DEFAULT_DLL, scenario, *sorted((frontend / 'dist').rglob('*'))]
        return {str(p.relative_to(WORKSPACE)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in paths if p.is_file()}
    data = {'utc': datetime.now(timezone.utc).isoformat(), 'system': platform.platform(),
            'command': f'node tests/{args.scenario} (credentials only in process environment)',
            'inputSha256': hashes(), 'exit_code': 1, 'result': 'FAIL'}
    lab = Lab('frontend')
    try:
        with lab:
            database = lab.create_database('browser-two-sessions')
            data.update(lab_id=lab.id, database=database.name,
                        postgresql=lab.sql('postgres', 'SHOW server_version;'))
            username, password = 'browser-admin', secrets.token_urlsafe(24)
            initial = lab.bootstrap(database, username, password)
            if initial.returncode != 0:
                raise RuntimeError('Bootstrap failed; inspect private lab logs')
            lab.grant_runtime(database)
            server = lab.start_server(database, frontend=frontend / 'dist')
            data['origin'] = server.origin
            environment = lab.environment()
            environment.update(RACKCLICK_TEST_ORIGIN=server.origin,
                               RACKCLICK_TEST_USERNAME=username, RACKCLICK_TEST_PASSWORD=password,
                               RACKCLICK_TEST_OUTPUT=str(args.output.resolve()))
            node = toolchain()['node']
            with (args.output / 'browser-windows.log').open('wb') as log:
                completed = run_isolated([str(node), str(scenario)],
                                           env=environment, cwd=frontend, stdout=log, stderr=log,
                                           timeout=args.timeout)
            data['scenarioExitCode'] = completed.returncode
            data['exit_code'] = completed.returncode
            data['result'] = 'PASS' if completed.returncode == 0 else 'FAIL'
            data['finalInputSha256'] = hashes()
            data['inputsUnchanged'] = data['inputSha256'] == data['finalInputSha256']
            if not data['inputsUnchanged']:
                data.update(exit_code=1, result='FAIL_INPUTS_CHANGED')
    except Exception as error:
        # No exception text: process arguments/environment can contain local secrets.
        data.update(exit_code=1, result='FAIL')
        data['failureType'] = type(error).__name__
    finally:
        if 'finalInputSha256' not in data:
            try:
                data['finalInputSha256'] = hashes()
                data['inputsUnchanged'] = data['inputSha256'] == data['finalInputSha256']
            except Exception as error:
                data.update(exit_code=1, result='FAIL', hashFailureType=type(error).__name__)
        data['labStopped'] = not lab.running
        data['finishedUtc'] = datetime.now(timezone.utc).isoformat()
        (args.output / 'fixture.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(data, indent=2))
    return data['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
