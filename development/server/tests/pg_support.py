"""Isolated PostgreSQL/ASP.NET Windows fixtures. Never reuses or deletes a cluster.

All passwords, connection strings and raw server logs stay under ignored .local/labs.
Use the toolchain lock; no installers/downloads or existing services are touched.
"""
from __future__ import annotations
import csv
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
import uuid
from dataclasses import dataclass

WORKSPACE = Path(__file__).resolve().parents[3]
SERVER_ROOT = WORKSPACE / 'development/server'
DEFAULT_DLL = SERVER_ROOT / 'src/RackClick.Server/bin/Release/net10.0/RackClick.Server.dll'
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def toolchain():
    lock = json.loads((WORKSPACE / 'development/toolchain.lock.json').read_text(encoding='utf-8-sig'))
    return {row['id']: WORKSPACE / '.local' / row['installDirectory'] / row['executable']
            for row in lock['components']}


def protect_directory(path):
    if os.name != 'nt':
        path.chmod(0o700)
        return
    identity = subprocess.run(['whoami.exe', '/user', '/fo', 'csv', '/nh'],
                              capture_output=True, text=True, check=True, creationflags=NO_WINDOW)
    sid = next(csv.reader(identity.stdout.splitlines()))[-1]
    result = subprocess.run(['icacls.exe', str(path), '/inheritance:r', '/grant:r',
                             f'*{sid}:(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'],
                            capture_output=True, creationflags=NO_WINDOW)
    if result.returncode:
        raise RuntimeError('Cannot restrict permissions on the new private lab directory')


@dataclass
class Database:
    name: str
    owner: str
    owner_password: str
    runtime: str
    runtime_password: str
    directory: Path

    def connection(self, port, runtime=True):
        user, password = ((self.runtime, self.runtime_password) if runtime
                          else (self.owner, self.owner_password))
        return (f'Host=127.0.0.1;Port={port};Database={self.name};Username={user};'
                f'Password={password};SSL Mode=Disable;Timeout=5;Command Timeout=15;')


@dataclass
class Response:
    status: int
    headers: dict
    body: bytes

    def json(self):
        return json.loads(self.body)


class Server:
    def __init__(self, lab, database, dll=None, frontend=None):
        self.lab, self.database = lab, database
        self.port = free_port()
        self.origin = f'http://127.0.0.1:{self.port}'
        self.log_path = database.directory / f'server-{uuid.uuid4().hex[:8]}.log'
        self.log = self.log_path.open('wb')
        environment = lab.environment()
        environment.update(ASPNETCORE_ENVIRONMENT='Development', PublicOrigin=self.origin,
                           DevelopmentLoopbackHttp='true',
                           ConnectionStrings__RackClick=database.connection(lab.port))
        if frontend is not None:
            environment['RackClick__FrontendPath'] = str(frontend)
        self.process = subprocess.Popen([str(lab.dotnet), str(dll or DEFAULT_DLL)],
                                        cwd=SERVER_ROOT, env=environment, stdout=self.log,
                                        stderr=self.log, creationflags=NO_WINDOW)
        try:
            for _ in range(150):
                if self.process.poll() is not None:
                    raise RuntimeError(f'ASP.NET stopped at startup; private log: {self.log_path}')
                try:
                    if self.request('GET', '/health/live').status == 200:
                        return
                except OSError:
                    pass
                time.sleep(.1)
            raise RuntimeError('ASP.NET startup timed out')
        except BaseException:
            self.close()
            raise

    def request(self, method, path, body=None, headers=None):
        request_headers = dict(headers or {})
        if body is not None and not isinstance(body, (bytes, str)):
            body = json.dumps(body, ensure_ascii=True).encode('utf-8')
            request_headers.setdefault('Content-Type', 'application/json')
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=20)
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            return Response(response.status, {k.lower(): v for k, v in response.getheaders()}, response.read())
        finally:
            connection.close()

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.log.close()


class Client:
    def __init__(self, server):
        self.server, self.cookie, self.csrf = server, None, None

    def login(self, username, password, route='/api/v1/auth/login'):
        response = self.server.request('POST', route, {'username': username, 'password': password},
                                       {'Origin': self.server.origin})
        if response.status == 200:
            self.cookie = response.headers['set-cookie'].split(';', 1)[0]
            self.csrf = response.json()['csrf']
        return response

    def request(self, method, path, body=None, headers=None):
        request_headers = {'Origin': self.server.origin}
        if self.cookie:
            request_headers['Cookie'] = self.cookie
        if self.csrf:
            request_headers['X-RackClick-CSRF'] = self.csrf
        request_headers.update(headers or {})
        return self.server.request(method, path, body, request_headers)


class Lab:
    def __init__(self, label='integration'):
        tools = toolchain()
        self.dotnet = tools['dotnet']
        self.pg_bin = tools['postgresql'].parent
        if not self.dotnet.is_file() or not (self.pg_bin / 'initdb.exe').is_file():
            raise RuntimeError('Run tools/windows/Initialize-Toolchain.ps1 first')
        self.id = uuid.uuid4().hex
        self.directory = WORKSPACE / '.local/labs' / f'{label}-{self.id}'
        assert self.directory.resolve().is_relative_to((WORKSPACE / '.local/labs').resolve())
        self.directory.mkdir(parents=True, exist_ok=False)
        protect_directory(self.directory)
        self.data = self.directory / 'data'
        self.port = free_port()
        self.admin = 'rc_lab_admin'
        self.admin_password = secrets.token_urlsafe(32)
        self.servers = []
        self.running = False
        self.pwfile = self.directory / 'init-password.txt'
        self.pwfile.write_text(self.admin_password + '\n', encoding='utf-8')
        self.admin_passfile = self.directory / 'admin.pgpass'
        self.admin_passfile.write_text(f'127.0.0.1:{self.port}:*:{self.admin}:{self.admin_password}\n', encoding='utf-8')
        self.metadata = {'id': self.id, 'label': label, 'path': str(self.directory), 'port': self.port,
                         'host': '127.0.0.1', 'postgresql': '17', 'databases': []}
        (self.directory / 'lab.json').write_text(json.dumps(self.metadata, indent=2), encoding='utf-8')

    def environment(self):
        environment = dict(os.environ)
        environment.update(DOTNET_ROOT=str(self.dotnet.parent),
                           DOTNET_CLI_HOME=str(WORKSPACE / '.local/dotnet-home'),
                           DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_NOLOGO='1',
                           DOTNET_GENERATE_ASPNET_CERTIFICATE='false',
                           DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='1',
                           NUGET_PACKAGES=str(WORKSPACE / '.local/nuget/packages'),
                           PGCLIENTENCODING='UTF8')
        environment['PATH'] = str(self.dotnet.parent) + os.pathsep + str(self.pg_bin) + os.pathsep + environment['PATH']
        return environment

    def start(self):
        if self.data.exists():
            raise RuntimeError('Refusing to initialize or reuse an existing data directory')
        log_path = self.directory / 'initdb.log'
        with log_path.open('wb') as log:
            result = subprocess.run([str(self.pg_bin / 'initdb.exe'), '-D', str(self.data),
                                     '-U', self.admin, '--pwfile=' + str(self.pwfile),
                                     '--auth-host=scram-sha-256', '--auth-local=scram-sha-256',
                                     '--encoding=UTF8', '--locale=C', '--data-checksums'],
                                    stdout=log, stderr=log, env=self.environment(), timeout=120,
                                    creationflags=NO_WINDOW)
        if result.returncode:
            raise RuntimeError(f'initdb failed; private log: {log_path}')
        with (self.data / 'postgresql.conf').open('a', encoding='utf-8') as config:
            config.write(f"\nlisten_addresses='127.0.0.1'\nport={self.port}\npassword_encryption='scram-sha-256'\n")
        # Windows postgres descendants may retain inherited pipe handles after pg_ctl exits.
        # A file avoids communicate() waiting for EOF from a long-lived database process.
        with (self.directory / 'pg_ctl.log').open('ab') as control_log:
            result = subprocess.run([str(self.pg_bin / 'pg_ctl.exe'), 'start', '-D', str(self.data),
                                     '-l', str(self.directory / 'postgres.log'), '-w', '-t', '60'],
                                    stdout=control_log, stderr=control_log, stdin=subprocess.DEVNULL,
                                    env=self.environment(), timeout=90, creationflags=NO_WINDOW)
        if result.returncode:
            # It is our newly-created directory, never an arbitrary external cluster.
            if (self.data / 'postmaster.pid').exists():
                self.running = True
                self.close()
            raise RuntimeError('New isolated PostgreSQL cluster failed to start; see private postgres.log')
        self.running = True
        return self

    def sql(self, database, command, admin=False, sensitive=False):
        name = database.name if isinstance(database, Database) else str(database)
        environment = self.environment()
        if admin or not isinstance(database, Database):
            user, passfile = self.admin, self.admin_passfile
        else:
            user, passfile = database.owner, database.directory / 'owner.pgpass'
        environment['PGPASSFILE'] = str(passfile)
        result = subprocess.run([str(self.pg_bin / 'psql.exe'), '-X', '-w', '-v', 'ON_ERROR_STOP=1',
                                 '-h', '127.0.0.1', '-p', str(self.port), '-U', user, '-d', name, '-At'],
                                input=command, text=True, encoding='utf-8', capture_output=True,
                                env=environment, timeout=30, creationflags=NO_WINDOW)
        if result.returncode:
            if sensitive:
                (self.directory / 'private-setup-error.log').write_text(result.stderr, encoding='utf-8')
            raise RuntimeError('Private database setup command failed' if sensitive else result.stderr)
        return result.stdout.strip()

    def create_database(self, label='fixture'):
        suffix = uuid.uuid4().hex[:12]
        name, owner, runtime = 'rc_' + suffix, 'rc_m_' + suffix, 'rc_a_' + suffix
        directory = self.directory / name
        directory.mkdir()
        database = Database(name, owner, secrets.token_urlsafe(32), runtime, secrets.token_urlsafe(32), directory)
        self.sql('postgres', f'CREATE ROLE {owner} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(database.owner_password)};'
                            f'CREATE ROLE {runtime} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(database.runtime_password)};', sensitive=True)
        self.sql('postgres', f'CREATE DATABASE {name} OWNER {owner} TEMPLATE template0 ENCODING \'UTF8\';')
        self.sql(name, f'REVOKE ALL ON DATABASE {name} FROM PUBLIC; GRANT CONNECT ON DATABASE {name} TO {runtime};', admin=True)
        (directory / 'owner.pgpass').write_text(f'127.0.0.1:{self.port}:{name}:{owner}:{database.owner_password}\n', encoding='utf-8')
        (directory / 'credentials.json').write_text(json.dumps({'database': name, 'owner': owner,
            'ownerPassword': database.owner_password, 'runtime': runtime, 'runtimePassword': database.runtime_password}), encoding='utf-8')
        self.metadata['databases'].append({'name': name, 'label': label, 'owner': owner, 'runtime': runtime})
        (self.directory / 'lab.json').write_text(json.dumps(self.metadata, indent=2), encoding='utf-8')
        return database

    def bootstrap(self, database, username, password, dll=None):
        environment = self.environment()
        environment.update(ConnectionStrings__RackClick=database.connection(self.port, runtime=False),
                           Bootstrap__User=username, Bootstrap__House='Laboratorio RackClick')
        return subprocess.run([str(self.dotnet), str(dll or DEFAULT_DLL), '--bootstrap'],
                              input=password + '\n', text=True, encoding='utf-8', capture_output=True,
                              cwd=SERVER_ROOT, env=environment, timeout=30, creationflags=NO_WINDOW)

    def grant_runtime(self, database):
        self.sql(database, f'GRANT USAGE ON SCHEMA public TO {database.runtime}; '
                           f'GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {database.runtime}; '
                           f'REVOKE CREATE ON SCHEMA public FROM PUBLIC;')
        # Global definition tables are read-only, unlike the customer's inventory.
        # The list is closed and internal; old schema fixtures have none of these.
        for table in ('hardware_definition', 'hardware_mount_slot', 'hardware_group_template', 'hardware_passthrough', 'hardware_connector_template', 'hardware_profile_extension', 'hardware_group_extension', 'app_mfa_rotation_witness'):
            if self.sql(database, f"SELECT to_regclass('public.{table}') IS NOT NULL") == 't':
                self.sql(database, f'REVOKE ALL ON {table} FROM {database.runtime}; GRANT SELECT ON {table} TO {database.runtime};')

    def start_server(self, database, dll=None, frontend=None):
        server = Server(self, database, dll=dll, frontend=frontend)
        self.servers.append(server)
        return server

    def close(self):
        for server in reversed(self.servers):
            server.close()
        if self.running:
            assert self.data.resolve().is_relative_to(self.directory.resolve())
            with (self.directory / 'pg_ctl.log').open('ab') as control_log:
                result = subprocess.run([str(self.pg_bin / 'pg_ctl.exe'), 'stop', '-D', str(self.data),
                                         '-m', 'fast', '-w', '-t', '60'], stdout=control_log,
                                        stderr=control_log, stdin=subprocess.DEVNULL,
                                        env=self.environment(), timeout=90, creationflags=NO_WINDOW)
            if result.returncode:
                raise RuntimeError(f'Could not stop this lab cluster: {self.directory}')
            self.running = False

    def __enter__(self):
        return self.start()

    def __exit__(self, *_):
        self.close()
