"""Build and run a fresh, loopback-only synthetic RackClick lab on Windows.

Reuses the reviewed PostgreSQL fixture and inventory loader. Each invocation
creates a NEW database/cluster, keeps it on disk and stops only its own children.
This is not a Windows service installer or a backup of security/MFA material.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import Lab, Client, NO_WINDOW, protect_directory, toolchain

PLAN = ROOT / 'development/examples/demo-original.inventory.json'
PLAN_SHA = 'cbfe4b43a0148299f6f4c24a21dfcb5e21a8efd5ca2d08d552119ac0cd292bd7'
OUTPUT = ROOT / '.local/source-demo'
PUBLICATION = OUTPUT / 'server'
LOADER = OUTPUT / 'loader/RackClick.Rc9DemoLoad.dll'
FRONTEND = ROOT / 'development/frontend/dist'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def environment():
    # Child-local isolation; never change the operator's environment.
    env = dict(os.environ)
    for key in list(env):
        upper = key.upper()
        if upper.startswith(('COR_', 'CORECLR_', 'COMPLUS_', 'DOTNET_',
                             'ASPNETCORE_', 'CONNECTIONSTRINGS__', 'MFAKEYSTORE__',
                             'BOOTSTRAP__', 'RACKCLICK__')) or upper in {'PUBLICORIGIN', 'DEVELOPMENTLOOPBACKHTTP'}:
            env.pop(key)
    tools = toolchain()
    env.update(DOTNET_ROOT=str(tools['dotnet'].parent),
               DOTNET_CLI_HOME=str(ROOT / '.local/dotnet-home'),
               NUGET_PACKAGES=str(ROOT / '.local/nuget/packages'),
               DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_NOLOGO='1',
               DOTNET_GENERATE_ASPNET_CERTIFICATE='false',
               DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='1',
               DOTNET_EnableDiagnostics='0', MfaKeyStore__Enabled='false')
    env['PATH'] = str(tools['dotnet'].parent) + os.pathsep + str(tools['node'].parent) + os.pathsep + env['PATH']
    return env


class DemoLab(Lab):
    def environment(self):
        env = environment()
        env['PGCLIENTENCODING'] = 'UTF8'
        env['PATH'] = str(self.pg_bin) + os.pathsep + env['PATH']
        return env


def run_build(args, cwd, name):
    log = OUTPUT / 'logs' / (name + '-' + uuid.uuid4().hex + '.log')
    with log.open('wb') as stream:
        result = subprocess.run(args, cwd=cwd, env=environment(), stdout=stream,
                                stderr=stream, creationflags=NO_WINDOW)
    if result.returncode:
        raise RuntimeError('build_failed: consult the private log ' + str(log))


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    protect_directory(OUTPUT)
    (OUTPUT / 'logs').mkdir(exist_ok=True)
    dotnet = str(toolchain()['dotnet'])
    server_root = ROOT / 'development/server'
    project = server_root / 'src/RackClick.Server/RackClick.Server.csproj'
    # Every MSBuild invocation has a distinct private binary log.
    def msbuild(command, target, extra, name, cwd=server_root):
        run_build([dotnet, command, str(target), *extra,
                   '-bl:' + str(OUTPUT / 'logs' / (name + '-' + uuid.uuid4().hex + '.binlog'))], cwd, name)
    msbuild('restore', project, ['--locked-mode', '--source', 'https://api.nuget.org/v3/index.json'], 'restore-server')
    msbuild('publish', project, ['-c', 'Release', '--no-restore', '-p:UseAppHost=false', '-o', str(PUBLICATION)], 'publish-server')
    loader_project = ROOT / 'tools/rc9-demo-load/RackClick.Rc9DemoLoad.csproj'
    loader_props = ['-p:RackClickServerDir=' + str(PUBLICATION)]
    msbuild('restore', loader_project, ['--locked-mode', '--source', 'https://api.nuget.org/v3/index.json', *loader_props], 'restore-loader', ROOT)
    msbuild('publish', loader_project, ['-c', 'Release', '--no-restore', '-o', str(LOADER.parent), *loader_props], 'publish-loader', ROOT)
    run_build(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
               '-File', str(ROOT / 'development/frontend/Build-Frontend.ps1')], ROOT, 'frontend')
    files = [*PUBLICATION.rglob('*'), *LOADER.parent.rglob('*'), *FRONTEND.rglob('*')]
    rows = {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in files if p.is_file()}
    if not rows or not LOADER.is_file() or not (FRONTEND / 'index.html').is_file():
        raise RuntimeError('build_outputs_missing')
    (OUTPUT / 'build.json').write_text(json.dumps({'files': rows, 'planSha256': PLAN_SHA}, indent=2) + '\n', encoding='utf-8')
    print('Compilacion lista. Registros privados en .local/source-demo/logs.')


def validate():
    if not PLAN.is_file() or digest(PLAN) != PLAN_SHA:
        raise RuntimeError('synthetic_inventory_hash_mismatch')
    manifest = json.loads((OUTPUT / 'build.json').read_text(encoding='utf-8'))
    for name, expected in manifest['files'].items():
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT.resolve()) or not path.is_file() or digest(path) != expected:
            raise RuntimeError('build_changed: repeat --build-only')
    for directory in [PUBLICATION, LOADER.parent, FRONTEND]:
        for path in directory.rglob('*'):
            if path.is_file() and path.relative_to(ROOT).as_posix() not in manifest['files']:
                raise RuntimeError('build_extra_file: inspect the private build directory')


def load_inventory(lab, database, actor):
    payload = {'mode': 'check', 'connectionString': database.connection(lab.port),
               'actorName': actor, 'expectedHouseId': '00000000-0000-0000-0000-000000000000',
               'expectedRevision': 0, 'requestId': str(uuid.uuid4())}
    def invoke():
        result = subprocess.run([str(lab.dotnet), str(LOADER), '--plan', str(PLAN)],
                                input=json.dumps(payload), text=True, encoding='utf-8', capture_output=True,
                                env=lab.environment(), timeout=120, creationflags=NO_WINDOW)
        answer = json.loads(result.stdout)
        if result.returncode or not answer.get('success'):
            raise RuntimeError('inventory_load_failed: ' + answer.get('code', 'no_receipt'))
        return answer
    checked = invoke()
    payload.update(mode='apply', expectedHouseId=checked['systemhausId'], expectedRevision=checked['expectedRevision'])
    return invoke()


def start(smoke=False):
    validate()
    lab = DemoLab('source-demo')
    try:
        lab.start()
        db = lab.create_database('synthetic-original')
        password = secrets.token_urlsafe(32)
        actor = 'demo-admin'
        boot = lab.bootstrap(db, actor, password, dll=PUBLICATION / 'RackClick.Server.dll')
        if boot.returncode:
            (lab.directory / 'bootstrap-private.log').write_text(boot.stdout + boot.stderr, encoding='utf-8')
            raise RuntimeError('bootstrap_failed')
        lab.grant_runtime(db)
        loaded = load_inventory(lab, db, actor)
        server = lab.start_server(db, dll=PUBLICATION / 'RackClick.Server.dll', frontend=FRONTEND)
        access = lab.directory / 'ACCESO-PRIVADO.json'
        access.write_text(json.dumps({'url': server.origin, 'usuario': actor, 'password': password,
                                     'mfaEnabled': False, 'scope': 'local synthetic development lab'}, indent=2), encoding='utf-8')
        client = Client(server)
        if client.login(actor, password).status != 200:
            raise RuntimeError('demo_login_failed')
        response = client.request('GET', '/api/v1/customers')
        if response.status != 200 or len(response.json()) != 10:
            raise RuntimeError('demo_customer_count_failed')
        if server.request('GET', '/').status != 200:
            raise RuntimeError('demo_frontend_failed')
        count = int(lab.sql(db, 'SELECT count(*) FROM inventory_port'))
        if count != 5408:
            raise RuntimeError('demo_port_count_failed')
        receipt = {'success': True, 'customers': 10, 'ports': count, 'frontend': 'served',
                   'runtimeDmlOnly': True, 'mfaEnabled': False, 'inventoryCommitted': loaded.get('committed')}
        (lab.directory / 'demo-result.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        print(json.dumps(receipt))
        if not smoke:
            print('Abrir en este equipo: ' + server.origin)
            print('Usuario y contrasena en el archivo privado: ' + str(access))
            print('Esta demo usa HTTP en loopback y no activa MFA. Para terminar: Ctrl+C.')
            print('La siguiente ejecucion crea OTRO laboratorio; esta base se conserva en disco.')
            while server.process.poll() is None:
                time.sleep(1)
            raise RuntimeError('demo_server_stopped')
    finally:
        lab.close()
        print('Procesos del laboratorio detenidos; archivos conservados en ' + str(lab.directory))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--build-only', action='store_true')
    mode.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    if os.name != 'nt' or sys.version_info < (3, 12):
        parser.error('Requires Windows x64 and Python 3.12 or later')
    if ctypes.windll.shell32.IsUserAnAdmin():
        parser.error('Open a normal PowerShell, not an administrator session')
    try:
        if args.build_only:
            build()
        else:
            start(args.smoke)
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as error:
        # Do not expose SQL, environment or child stdout on an error.
        print('Demo interrumpida (' + type(error).__name__ + '). Consulte los registros privados.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
