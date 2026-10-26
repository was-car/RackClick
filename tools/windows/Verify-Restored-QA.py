"""Read/restart verification of the new RC9 QA, before handoff only. No data writes."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/windows'))
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from qa_guide import context
from pg_support import Client
from importlib import import_module
accounts = import_module('Qa-Accounts')
spec = importlib.util.spec_from_file_location('qa_local', ROOT / 'tools/windows/Qa-Local.py')
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--before-handoff', action='store_true', required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    original = ROOT / '.local/qa-wascar/current.json'
    original_bytes = original.read_bytes()
    qa.configure('manual')
    old_directory, old_cfg = qa.load()
    old_healthy = qa.healthy(old_cfg)
    qa.configure('rc9')
    directory, cfg = qa.load()
    if directory == old_directory or cfg['webPort'] == old_cfg['webPort']:
        raise RuntimeError('QA instances must be distinct')
    state = json.loads((directory / accounts.STATE).read_text(encoding='utf-8'))
    access = (directory / 'ACCESO-PRIVADO.txt').read_text(encoding='utf-8-sig').split(accounts.BEGIN)[0]
    fields = dict(line.split(': ', 1) for line in access.splitlines() if ': ' in line)
    server = accounts.LoopbackServer(cfg['webPort'])

    def read_counts():
        admin = Client(server)
        if admin.login(fields['Usuario'], fields['Contraseña']).status != 200:
            raise RuntimeError('Restored administrator login failed')
        response = admin.request('GET', '/api/v1/customers')
        if response.status != 200:
            raise RuntimeError('Restored customer read failed')
        customers = response.json()
        counts = {k: 0 for k in ('sites', 'buildings', 'rooms', 'racks', 'devices', 'portGroups', 'ports', 'connections')}
        for customer in customers:
            response = admin.request('GET', f"/api/v1/customers/{customer['id']}/project")
            if response.status != 200:
                raise RuntimeError('Restored project read failed')
            project = response.json()
            for key in counts:
                counts[key] += len(project[key])
        counts['customers'] = len(customers)
        if any(counts[key] != cfg['restoreCounts'][key] for key in counts):
            raise RuntimeError('Restored API counts differ from source')
        return counts

    counts = read_counts()
    # Only the explicit rc9 profile may be restarted. The original is never stopped.
    for action in ('stop', 'start'):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/windows/Qa-Local.py'), action,
            '--profile', 'rc9'], capture_output=True, timeout=180)
        if result.returncode:
            raise RuntimeError('Restored QA lifecycle verification failed')
    if read_counts() != counts:
        raise RuntimeError('Restored counts changed after restart')
    if original.read_bytes() != original_bytes or qa.healthy(old_cfg) != old_healthy:
        raise RuntimeError('Original QA state changed')
    if hashlib.sha256((ROOT / 'RackClick-backup-all.json').read_bytes()).hexdigest() != cfg['restoreSourceSha256']:
        raise RuntimeError('Source backup changed')
    if not context(profile='rc9')['restored'] or context(profile='manual')['restored']:
        raise RuntimeError('Guide environment availability incorrect')
    result = {'status': 'PASS', 'origin': server.origin, 'counts': counts,
        'restartPreserved': True, 'originalPointerUnchanged': True, 'originalReadyUnchanged': True,
        'sourceUnchanged': True, 'rolesReady': state['permissionsCommitted'],
        'dllSha256': cfg['dllSha256'], 'bundleSha256': cfg['bundleSha256'],
        'limitations': ['Read-only API checks and restart of rc9 only; visual QA remains for Wascar.']}
    (args.evidence / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('Restored QA PASS: source counts, restart, separate profiles, original preserved.')


if __name__ == '__main__':
    main()
