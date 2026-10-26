"""Coordinated, reversible rc9 artifact upgrade with logical snapshot verification."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
qa = importlib.import_module('Qa-Local')
accounts = importlib.import_module('Qa-Accounts')
from pg_support import Client


def command(script, *args):
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/windows' / script), *args],
                            capture_output=True, timeout=180)
    if result.returncode:
        raise RuntimeError('Scoped QA command failed')


def snapshot(server, username, password):
    client = Client(server)
    if client.login(username, password).status != 200:
        raise RuntimeError('QA administrator login failed')
    values = {}
    for route in ['/api/v1/systemhaus', '/api/v1/customers', '/api/v1/admin/users',
                  '/api/v1/admin/user-groups', '/api/v1/admin/customer-groups']:
        response = client.request('GET', route)
        if response.status != 200:
            raise RuntimeError('QA snapshot read failed')
        values[route] = response.json()
    counts = {k: 0 for k in ('sites', 'buildings', 'rooms', 'racks', 'devices', 'portGroups', 'ports', 'connections')}
    for customer in values['/api/v1/customers']:
        response = client.request('GET', f"/api/v1/customers/{customer['id']}/project")
        if response.status != 200:
            raise RuntimeError('QA inventory read failed')
        project = response.json()
        values[customer['id']] = project
        for key in counts:
            counts[key] += len(project[key])
    counts['customers'] = len(values['/api/v1/customers'])
    digest = hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return digest, counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll-sha256', required=True)
    parser.add_argument('--bundle-sha256', required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--coordinated-update', action='store_true', required=True)
    args = parser.parse_args()
    if hashlib.sha256(qa.DEFAULT_DLL.read_bytes()).hexdigest() != args.dll_sha256 or hashlib.sha256(
        (ROOT / 'development/frontend/dist/app.js').read_bytes()).hexdigest() != args.bundle_sha256:
        raise RuntimeError('Candidate differs from reviewed hashes; QA unchanged')
    evidence = args.evidence.resolve()
    if not evidence.is_relative_to((ROOT / 'evidence').resolve()) or evidence.exists():
        parser.error('New evidence directory within workspace required')
    evidence.mkdir(parents=True)
    original_pointer = ROOT / '.local/qa-wascar/current.json'
    original_bytes = original_pointer.read_bytes()
    qa.configure('manual')
    original_directory, original_cfg = qa.load()
    original_health = qa.healthy(original_cfg)
    qa.artifact_directory(original_directory, original_cfg)
    qa.configure('rc9')
    directory, cfg = qa.load()
    if cfg['dllSha256'] == args.dll_sha256 and cfg['bundleSha256'] == args.bundle_sha256:
        raise RuntimeError('Candidate already active; no upgrade performed')
    fields = dict(line.split(': ', 1) for line in (directory / 'ACCESO-PRIVADO.txt').read_text(
        encoding='utf-8-sig').split(accounts.BEGIN)[0].splitlines() if ': ' in line)
    server = accounts.LoopbackServer(cfg['webPort'])
    changed = False
    try:
        command('Qa-Local.py', 'start', '--profile', 'rc9')
        before, counts = snapshot(server, fields['Usuario'], fields['Contraseña'])
        command('Qa-Local.py', 'stop', '--profile', 'rc9')
        command('Qa-Update.py', '--profile', 'rc9', '--no-schema-change', '--dll-sha256',
                args.dll_sha256, '--bundle-sha256', args.bundle_sha256)
        changed = True
        command('Qa-Local.py', 'start', '--profile', 'rc9')
        after, new_counts = snapshot(server, fields['Usuario'], fields['Contraseña'])
        if before != after or counts != new_counts:
            raise RuntimeError('Logical QA snapshot differs')
        directory, current = qa.load()
        bundle = server.request('GET', '/app.js')
        if bundle.status != 200 or hashlib.sha256(bundle.body).hexdigest() != args.bundle_sha256:
            raise RuntimeError('Live frontend differs from reviewed bundle')
        if original_pointer.read_bytes() != original_bytes or qa.healthy(original_cfg) != original_health:
            raise RuntimeError('Original QA changed')
        qa.artifact_directory(original_directory, original_cfg)
        if not qa.ready(directory, current):
            raise RuntimeError('Updated QA is not ready')
        result = {'status': 'PASS', 'origin': server.origin, 'logicalSnapshotBefore': before,
            'logicalSnapshotAfter': after, 'counts': counts, 'dllSha256': current['dllSha256'],
            'bundleSha256': current['bundleSha256'], 'previousVersionRetained': True,
            'originalPointerAndHealthUnchanged': True, 'originalArtifactsMatch': True,
            'restoredReady': True, 'limitations': ['Authentication creates sessions; no inventory/account/group mutations.',
                'Artifact upgrade without schema changes; not a production installer or database backup.']}
        (evidence / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print('Restored QA upgrade PASS: logical snapshot unchanged, previous version retained.')
    except Exception as error:
        rollback_ok = False
        try:
            # A subprocess can fail after its atomic switch; inspect actual config.
            changed = qa.load()[1].get('artifactDirectory') != cfg.get('artifactDirectory')
        except Exception:
            pass
        if changed:
            try:
                command('Qa-Local.py', 'stop', '--profile', 'rc9')
                command('Qa-Update.py', '--profile', 'rc9', '--no-schema-change', '--rollback')
                command('Qa-Local.py', 'start', '--profile', 'rc9')
                rollback_ok = True
            except Exception:
                pass
        else:
            try:
                command('Qa-Local.py', 'start', '--profile', 'rc9')
                rollback_ok = True
            except Exception:
                pass
        (evidence / 'failure.json').write_text(json.dumps({'status': 'FAIL', 'errorType': type(error).__name__,
            'artifactsChanged': changed, 'rollbackAndRestartSucceeded': rollback_ok}), encoding='utf-8')
        raise


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Coordinated QA upgrade failed: ' + type(error).__name__ + '; inspect redacted evidence.')
        raise SystemExit(1)
