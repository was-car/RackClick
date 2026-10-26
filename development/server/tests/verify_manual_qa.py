"""Pre-handoff test ONLY for the dedicated manual QA lab; stops/restarts it.

Do not run during Wascar's QA session. Leaves one fictitious client and QA running.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'tools/windows/Qa-Local.py'
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location('qa_local', SCRIPT)
qa = importlib.util.module_from_spec(spec); spec.loader.exec_module(qa)
from pg_support import Client, Server, NO_WINDOW


def command(action, expected=0):
    result = subprocess.run([sys.executable, str(SCRIPT), action], capture_output=True, timeout=150,
                            creationflags=NO_WINDOW)
    assert result.returncode == expected, f'{action}: unexpected exit code {result.returncode}'
    return json.loads(result.stdout) if not expected else None


def listening(port):
    with socket.socket() as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(('127.0.0.1', port)) == 0


def wait(condition):
    for _ in range(120):
        if condition(): return
        time.sleep(0.5)
    raise RuntimeError('Condition timed out')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=False)
    result = {'utc': datetime.now(timezone.utc).isoformat(), 'checks': [], 'status': 'FAIL',
              'scriptSha256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest()}
    child = None
    try:
        directory, cfg = qa.load()
        initial = command('start'); again = command('start')
        assert initial['running'] and initial == again
        result['checks'].append('Repeated start preserves same instance and snapshot')
        access = (directory / 'ACCESO-PRIVADO.txt').read_text(encoding='utf-8-sig').splitlines()
        username = next(s.split(': ',1)[1] for s in access if s.startswith('Usuario:'))
        password = next(s.split(': ',1)[1] for s in access if s.startswith('Contrase'))
        server = Server.__new__(Server); server.port = cfg['webPort']; server.origin = initial['origin']
        client = Client(server)
        assert client.login(username, password).status == 200
        assert server.request('GET', '/').status == 200
        house = client.request('GET', '/api/v1/systemhaus')
        created = client.request('POST', '/api/v1/customers', {'name': 'Cliente de ejemplo QA'},
            {'If-Match': house.headers['etag'], 'Idempotency-Key': str(uuid.uuid4())})
        assert created.status == 201
        customer = created.json()['resource']
        command('stop')
        assert not listening(cfg['webPort']) and not listening(cfg['pgPort'])
        command('start')
        second = Client(server); assert second.login(username, password).status == 200
        assert any(c['id'] == customer['id'] for c in second.request('GET', '/api/v1/customers').json())
        result['checks'].append('Login, GUI HTTP200, committed client survives full stop/start and second session')
        command('stop')

        class Occupied(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.end_headers(); self.wfile.write(b'foreign')
            def log_message(self, *_): pass
        fake = ThreadingHTTPServer(('127.0.0.1', cfg['webPort']), Occupied)
        thread = threading.Thread(target=fake.serve_forever, daemon=True); thread.start()
        try:
            command('start', expected=1)
            wait(lambda: not qa.running(directory))
            assert listening(cfg['webPort']) and not listening(cfg['pgPort'])
            assert command('status')['running'] is False
            result['checks'].append('Foreign HTTP200 on occupied port is rejected and foreign listener survives')
        finally:
            fake.shutdown(); fake.server_close(); thread.join()

        # Own handle, not a discovered PID: terminate only our newly launched supervisor.
        with (directory / 'crash-verification.log').open('ab') as output:
            child = subprocess.Popen([sys.executable, str(SCRIPT), '_serve'], cwd=ROOT,
                stdout=output, stderr=output, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
        wait(lambda: qa.ready(directory, cfg))
        child.kill(); child.wait(timeout=15)
        wait(lambda: not listening(cfg['webPort']) and not listening(cfg['pgPort']))
        assert not qa.running(directory)
        command('start')
        third = Client(server); assert third.login(username, password).status == 200
        assert any(c['id'] == customer['id'] for c in third.request('GET', '/api/v1/customers').json())
        result['checks'].append('Supervisor termination closes owned descendants; restart recovers committed client')
        result.update(status='PASS', origin=initial['origin'], dllSha256=cfg['dllSha256'],
                      bundleSha256=cfg['bundleSha256'], labLeftRunningForWascar=True)
    finally:
        if child is not None and child.poll() is None:
            child.kill(); child.wait(timeout=15)
        result['scriptUnchanged'] = result['scriptSha256'] == hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
        (args.output / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
