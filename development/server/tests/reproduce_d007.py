"""Compare the received baseline with the fix against native PostgreSQL.

Usage: python -B tests/reproduce_d007.py --baseline-dll PATH --output NEW.json
All database fixtures are new; credentials and raw logs remain private.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import secrets
from pg_support import Lab, Client, DEFAULT_DLL


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-dll', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.baseline_dll = args.baseline_dll.resolve()
    if args.output.exists():
        parser.error('Refusing to overwrite evidence')
    if not args.baseline_dll.is_file() or not DEFAULT_DLL.is_file():
        parser.error('Both baseline and current Release builds are required')
    result = {'utc': datetime.now(timezone.utc).isoformat(), 'system': platform.platform(),
              'python': platform.python_version(), 'baseline_commit': '2edcf3e9985203d081c3b9d455c0ee0e65b0a888',
              'postgresql': None, 'cases': [], 'status': 'RUNNING'}
    for label, dll in [('baseline', args.baseline_dll), ('fixed', DEFAULT_DLL)]:
        result[label + '_dll_sha256'] = hashlib.sha256(dll.read_bytes()).hexdigest()
    try:
        with Lab('d007') as lab:
            result['postgresql'] = lab.sql('postgres', 'SHOW server_version;')
            result['lab_id'] = lab.id
            for count in (51, 100):
                username = '\U0001f680' * count
                for label, dll, route, expected in (
                    ('baseline', args.baseline_dll, '/api/v1/login', 401),
                    ('fixed', DEFAULT_DLL, '/api/v1/auth/login', 200)):
                    database = lab.create_database(f'{label}-unicode-{count}')
                    password = secrets.token_urlsafe(24)
                    bootstrap = lab.bootstrap(database, username, password, dll=dll)
                    assert bootstrap.returncode == 0, f'{label} bootstrap failed: {bootstrap.stderr}'
                    lab.grant_runtime(database)
                    server = lab.start_server(database, dll=dll)
                    client = Client(server)
                    login = client.login(username, password, route=route)
                    assert login.status == expected, f'{label} login {login.status}, expected {expected}'
                    if label == 'fixed':
                        identity = client.request('GET', '/api/v1/me')
                        assert identity.status == 200
                        assert identity.json()['user']['userName'] == username
                    case = {'version': label, 'unicode_scalars': count, 'utf16_units': count * 2,
                            'bootstrap_exit': bootstrap.returncode, 'login_status': login.status,
                            'expected_login_status': expected, 'result': 'PASS'}
                    result['cases'].append(case)
                    print(f"PASS {label}: bootstrap + login, {count} Unicode scalars => HTTP {login.status}", flush=True)
                    server.close()
            result['status'] = 'PASS_BASELINE_DEFECT_REPRODUCED_AND_FIXED'
    except BaseException:
        result['status'] = 'FAIL'
        raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as report:
            json.dump(result, report, ensure_ascii=False, indent=2)
            report.write('\n')


if __name__ == '__main__':
    main()
