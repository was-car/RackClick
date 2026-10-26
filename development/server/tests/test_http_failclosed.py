"""Run the actual compiled ASP.NET server without a database.
These are failure-path checks, NOT PostgreSQL integration. Record the actual OS per run.
Usage: python3 tests/test_http_failclosed.py /absolute/path/to/dotnet
"""
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOTNET = sys.argv.pop(1)
DLL = ROOT / 'src/RackClick.Server/bin/Release/net10.0/RackClick.Server.dll'

class HttpFailureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        cls.origin = f'http://127.0.0.1:{cls.port}'
        cls.log = tempfile.TemporaryFile()
        env = dict(os.environ, ASPNETCORE_ENVIRONMENT='Development',
                   PublicOrigin=cls.origin, DevelopmentLoopbackHttp='true',
                   ConnectionStrings__RackClick='Host=127.0.0.1;Port=1;Database=rackclick_test;Username=synthetic;Password=not-a-real-secret;Timeout=1;Pooling=false')
        cls.server = subprocess.Popen([DOTNET, str(DLL)], cwd=ROOT, env=env, stdout=cls.log, stderr=cls.log)
        for _ in range(100):
            if cls.server.poll() is not None:
                cls.log.seek(0)
                raise RuntimeError(cls.log.read().decode())
            try:
                status, _, _ = cls.request('GET', '/health/live')
                if status == 200:
                    return
            except OSError:
                pass
            time.sleep(0.1)
        cls.server.terminate()
        cls.server.wait(timeout=5)
        raise RuntimeError('Server did not start')

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.wait(timeout=10)
        cls.log.close()

    @classmethod
    def request(cls, method, path, headers=None, body=None):
        conn = http.client.HTTPConnection('127.0.0.1', cls.port, timeout=5)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            result = conn.getresponse()
            return result.status, dict(result.getheaders()), result.read().decode()
        finally:
            conn.close()

    def test_health_live_is_not_database_ready(self):
        status, headers, body = self.request('GET', '/health/live')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['status'], 'alive')
        self.assertEqual(headers['Cache-Control'], 'no-store')
        status, _, body = self.request('GET', '/health/ready')
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body)['error'], 'service_unavailable')

    def test_unauthenticated_customer_list_denied(self):
        status, _, body = self.request('GET', '/api/v1/customers')
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body)['error'], 'authentication_required')

    def test_login_without_origin_denied_before_database(self):
        status, _, body = self.request('POST', '/api/v1/auth/login', {'Content-Type': 'application/json'}, '{}')
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)['error'], 'origin_invalid')

    def test_foreign_origin_denied(self):
        status, _, body = self.request('POST', '/api/v1/auth/login', {'Origin': 'https://other.invalid'}, '{}')
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)['error'], 'origin_invalid')

    def test_foreign_host_denied(self):
        status, _, body = self.request('GET', '/health/live', {'Host': 'other.invalid'})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)['error'], 'host_invalid')

    def test_browser_protections_also_cover_rejections(self):
        for path, headers, expected in [('/health/live', {}, 200),
                                         ('/health/live', {'Host': 'other.invalid'}, 400),
                                         ('/api/v1/customers', {}, 401)]:
            with self.subTest(path=path, status=expected):
                status, response_headers, _ = self.request('GET', path, headers)
                self.assertEqual(status, expected)
                self.assertEqual(response_headers['Referrer-Policy'], 'no-referrer')
                self.assertEqual(response_headers['X-Frame-Options'], 'DENY')
                self.assertEqual(response_headers['Permissions-Policy'],
                                 'camera=(), microphone=(), geolocation=()')
                self.assertEqual(response_headers['X-Content-Type-Options'], 'nosniff')
                self.assertIn("frame-ancestors 'none'", response_headers['Content-Security-Policy'])
                self.assertNotIn('Strict-Transport-Security', response_headers)
                self.assertNotIn('Access-Control-Allow-Origin', response_headers)

    def test_database_failure_does_not_leak_secrets(self):
        status, headers, body = self.request('POST', '/api/v1/auth/login',
            {'Origin': self.origin, 'Content-Type': 'application/json'},
            json.dumps({'username': 'admin', 'password': 'synthetic-password'}))
        self.assertEqual(status, 503)
        self.assertNotIn('Set-Cookie', headers)
        for forbidden in ['synthetic', 'password', '127.0.0.1', 'Npgsql', 'rackclick_test']:
            self.assertNotIn(forbidden, body)

    def test_not_presented_as_integrated_gui(self):
        status, _, body = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)['guiIntegrated'])

    def test_http_refused_without_development_opt_in(self):
        env = dict(os.environ, ASPNETCORE_ENVIRONMENT='Production', PublicOrigin=self.origin,
                   ConnectionStrings__RackClick='Host=127.0.0.1;Database=synthetic;Username=synthetic')
        env.pop('DevelopmentLoopbackHttp', None)
        result = subprocess.run([DOTNET, str(DLL)], cwd=ROOT, env=env, capture_output=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'HTTPS is required', result.stderr)

if __name__ == '__main__':
    unittest.main(verbosity=2)
