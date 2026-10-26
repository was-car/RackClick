"""Persistent manual QA on loopback. No installer, updates, deletion or foreign services."""
from pathlib import Path
import argparse
import hashlib
import http.client
import json
import msvcrt
import os
import secrets
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import Lab, DEFAULT_DLL, protect_directory, free_port, toolchain, NO_WINDOW
from windows_job import run_isolated

HOME = ROOT / '.local/qa-wascar'
POINTER = HOME / 'current.json'
PROFILE = 'manual'


def configure(profile):
    global HOME, POINTER, PROFILE
    if profile not in ('manual', 'rc9'):
        raise RuntimeError('Unknown QA profile')
    PROFILE = profile
    HOME = ROOT / '.local' / ('qa-rc9' if profile == 'rc9' else 'qa-wascar')
    POINTER = HOME / 'current.json'


def load():
    pointer = json.loads(POINTER.read_text(encoding='utf-8'))
    directory = Path(pointer['directory']).resolve()
    if directory.parent != (ROOT / '.local/labs').resolve() or not directory.name.startswith('manual-qa-'):
        raise RuntimeError('Invalid manual QA directory')
    cfg = json.loads((directory / 'manual-qa.json').read_text(encoding='utf-8'))
    if cfg['directory'] != str(directory) or cfg['host'] != '127.0.0.1':
        raise RuntimeError('Invalid manual QA identity')
    if cfg.get('profile', 'manual') != PROFILE:
        raise RuntimeError('QA profile identity mismatch')
    artifact_directory(directory, cfg, verify=False)
    return directory, cfg


def artifact_directory(directory, cfg, verify=True):
    artifacts = Path(cfg.get('artifactDirectory', str(directory))).resolve()
    if artifacts != directory.resolve() and artifacts.parent != (directory / 'versions').resolve():
        raise RuntimeError('Invalid QA artifact directory')
    if verify:
        for relative, key in [('server/RackClick.Server.dll', 'dllSha256'), ('frontend/app.js', 'bundleSha256')]:
            if hashlib.sha256((artifacts / relative).read_bytes()).hexdigest() != cfg[key]:
                raise RuntimeError('Frozen QA artifact hash mismatch')
    return artifacts


def prepare():
    if POINTER.exists():
        return load()
    if PROFILE == 'rc9':
        return prepare_rc9()
    lab = Lab('manual-qa')
    directory = lab.directory.resolve()
    # Freeze the proven build so later developer builds do not change Wascar's session.
    shutil.copytree(DEFAULT_DLL.parent, directory / 'server')
    shutil.copytree(ROOT / 'development/frontend/dist', directory / 'frontend')
    username, password = 'wascar-qa', secrets.token_urlsafe(24)
    try:
        lab.start()
        database = lab.create_database('manual-qa-wascar')
        result = lab.bootstrap(database, username, password, dll=directory / 'server/RackClick.Server.dll')
        if result.returncode:
            raise RuntimeError('QA bootstrap failed; retained isolated directory')
        lab.grant_runtime(database)
        cfg = {'directory': str(directory), 'host': '127.0.0.1', 'webPort': free_port(),
               'pgPort': lab.port, 'database': database.name, 'connection': database.connection(lab.port),
               'dllSha256': hashlib.sha256((directory / 'server/RackClick.Server.dll').read_bytes()).hexdigest(),
               'bundleSha256': hashlib.sha256((directory / 'frontend/app.js').read_bytes()).hexdigest()}
        (directory / 'manual-qa.json').write_text(json.dumps(cfg, indent=2), encoding='utf-8')
        (directory / 'ACCESO-PRIVADO.txt').write_text(
            f'QA local RackClick — solo este Windows\nURL: http://127.0.0.1:{cfg["webPort"]}\n'
            f'Usuario: {username}\nContraseña: {password}\nNo compartir este archivo ni incluirlo en capturas.\n', encoding='utf-8-sig')
    finally:
        lab.close()
    POINTER.write_text(json.dumps({'directory': str(directory)}), encoding='utf-8')
    return directory, cfg


def prepare_rc9():
    from rc9_restore import restore
    lab = Lab('manual-qa-rc9')
    directory = lab.directory.resolve()
    shutil.copytree(DEFAULT_DLL.parent, directory / 'server')
    shutil.copytree(ROOT / 'development/frontend/dist', directory / 'frontend')
    username, password = 'wascar-qa', secrets.token_urlsafe(24)
    try:
        lab.start()
        database = lab.create_database('manual-qa-rc9')
        initial = lab.bootstrap(database, username, password, dll=directory / 'server/RackClick.Server.dll')
        if initial.returncode:
            raise RuntimeError('New restored QA bootstrap failed; private directory retained')
        actor = lab.sql(database, "SELECT id FROM app_user WHERE username='wascar-qa';")
        report = restore(lab, database, ROOT / 'RackClick-backup-all.json', actor)
        mapping = json.loads(Path(report['mappingPath']).read_text(encoding='utf-8'))
        target = mapping['entities']['customers'][0]
        lab.grant_runtime(database)
        cfg = {'directory': str(directory), 'profile': 'rc9', 'host': '127.0.0.1', 'webPort': free_port(),
               'pgPort': lab.port, 'database': database.name, 'connection': database.connection(lab.port),
               'dllSha256': hashlib.sha256((directory / 'server/RackClick.Server.dll').read_bytes()).hexdigest(),
               'bundleSha256': hashlib.sha256((directory / 'frontend/app.js').read_bytes()).hexdigest(),
               'restoreSourceSha256': report['sourceSha256'], 'restoreCounts': report['counts'],
               'qaCustomerId': target['id'], 'qaCustomerName': target['path'][0]}
        (directory / 'manual-qa.json').write_text(json.dumps(cfg, indent=2), encoding='utf-8')
        (directory / 'RESTORE-ESTADO.json').write_text(json.dumps({
            'restored': True, 'sourceSha256': report['sourceSha256'], 'counts': report['counts']}, indent=2), encoding='utf-8')
        (directory / 'ACCESO-PRIVADO.txt').write_text(
            f'QA restaurado RC9 — base NUEVA, diferente de QA original\nURL: http://127.0.0.1:{cfg["webPort"]}\n'
            f'Usuario: {username}\nContraseña: {password}\n'
            'La contraseña es propia de esta copia. Use otro perfil/navegador para no compartir cookies con QA original.\n'
            'No compartir este archivo ni incluirlo en capturas.\n', encoding='utf-8-sig')
    finally:
        lab.close()
    POINTER.write_text(json.dumps({'directory': str(directory)}), encoding='utf-8')
    return directory, cfg


def healthy(cfg):
    try:
        conn = http.client.HTTPConnection('127.0.0.1', cfg['webPort'], timeout=2)
        conn.request('GET', '/health/ready')
        response = conn.getresponse()
        ok = response.status == 200
        response.read(); conn.close()
        return ok
    except OSError:
        return False


def owns_listener(cfg, pid):
    command = (f"$qaSockets = @(Get-NetTCPConnection -State Listen -LocalPort {int(cfg['webPort'])} "
               "-ErrorAction SilentlyContinue); "
               f"if (@($qaSockets | Where-Object {{ $_.OwningProcess -eq {int(pid)} -and "
               "$_.LocalAddress -eq '127.0.0.1' }).Count -eq 1) { exit 0 }; exit 1")
    return subprocess.run(['powershell.exe', '-NoProfile', '-Command', command],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW,
        timeout=20).returncode == 0


def ready(directory, cfg):
    marker = directory / 'ready.json'
    if not running(directory) or not marker.exists():
        return False
    record = json.loads(marker.read_text())
    return owns_listener(cfg, record['pid']) and healthy(cfg)


def control(directory, action):
    pg = toolchain()['postgresql'].parent / 'pg_ctl.exe'
    command = [str(pg), action, '-D', str(directory / 'data'), '-w', '-t', '60']
    command += ['-l', str(directory / 'postgres.log')] if action == 'start' else ['-m', 'fast']
    with (directory / 'manual-control.log').open('ab') as output:
        subprocess.run(command, stdout=output, stderr=output, stdin=subprocess.DEVNULL,
                       creationflags=NO_WINDOW, timeout=90, check=True)


def serve(directory, cfg):
    artifacts = artifact_directory(directory, cfg)
    # A process-owned Windows byte lock prevents double start; no PID-based killing.
    with (directory / 'server.lock').open('a+b') as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        stop = directory / 'stop.request'
        stop.unlink(missing_ok=True)
        marker = directory / 'ready.json'
        marker.unlink(missing_ok=True)
        process = None
        started = False
        try:
            control(directory, 'start'); started = True
            dotnet = toolchain()['dotnet']
            env = dict(os.environ)
            env.update(DOTNET_ROOT=str(dotnet.parent), DOTNET_CLI_HOME=str(ROOT / '.local/dotnet-home'),
                       DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_NOLOGO='1',
                       ASPNETCORE_ENVIRONMENT='Development', DevelopmentLoopbackHttp='true',
                       PublicOrigin=f'http://127.0.0.1:{cfg["webPort"]}',
                       ConnectionStrings__RackClick=cfg['connection'],
                       RackClick__FrontendPath=str(artifacts / 'frontend'))
            with (directory / 'manual-server.log').open('ab') as output:
                process = subprocess.Popen([str(dotnet), str(artifacts / 'server/RackClick.Server.dll')],
                    cwd=artifacts / 'server', env=env, stdout=output, stderr=output,
                    stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
                for _ in range(120):
                    if process.poll() is not None or stop.exists():
                        raise RuntimeError('QA application could not start')
                    if healthy(cfg) and owns_listener(cfg, process.pid):
                        marker.write_text(json.dumps({'pid': process.pid}), encoding='utf-8')
                        break
                    time.sleep(0.5)
                else:
                    raise RuntimeError('QA application readiness timed out')
                while process.poll() is None and not stop.exists():
                    time.sleep(0.5)
                if not stop.exists():
                    raise RuntimeError('QA application stopped unexpectedly')
        finally:
            marker.unlink(missing_ok=True)
            if process is not None and process.poll() is None:
                process.terminate(); process.wait(timeout=30)
            if started:
                control(directory, 'stop')


def running(directory):
    with (directory / 'server.lock').open('a+b') as lock:
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return True
        msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', 'stop', 'status', 'open', '_serve', '_worker'))
    parser.add_argument('--profile', choices=('manual', 'rc9'), default='manual')
    args = parser.parse_args()
    configure(args.profile)
    child_profile = ['--profile', args.profile]
    HOME.mkdir(parents=True, exist_ok=True)
    protect_directory(HOME)
    # Serialize public commands including first-time preparation.
    with (HOME / 'control.lock').open('a+b') as lock:
        lock.seek(0)
        if args.action not in ('_serve', '_worker'):
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        directory, cfg = prepare() if args.action == 'start' else load()
        if args.action == '_serve':
            # The supervisor owns a non-inherited job handle. If it crashes,
            # Windows stops only this worker's descendants, including PostgreSQL.
            with (directory / 'worker.log').open('ab') as output:
                result = run_isolated([sys.executable, str(Path(__file__).resolve()), '_worker', *child_profile],
                                      cwd=ROOT, stdout=output, stderr=output)
            if result.returncode:
                raise RuntimeError('QA worker stopped with an error')
            return
        if args.action == '_worker':
            serve(directory, cfg)
            return
        if args.action == 'start' and not running(directory):
            with (directory / 'supervisor.log').open('ab') as output:
                child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '_serve', *child_profile],
                    cwd=ROOT, stdout=output, stderr=output, stdin=subprocess.DEVNULL,
                    creationflags=NO_WINDOW)
            for _ in range(180):
                if child.poll() is not None:
                    raise RuntimeError('QA startup failed; inspect private supervisor.log')
                if ready(directory, cfg):
                    break
                time.sleep(0.5)
            else:
                (directory / 'stop.request').touch()
                raise RuntimeError('QA startup timed out')
        if args.action == 'stop':
            (directory / 'stop.request').touch()
            for _ in range(180):
                if not running(directory):
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError('QA stop timed out; no foreign process will be killed')
        active = ready(directory, cfg)
        if args.action == 'open':
            if not active:
                raise RuntimeError('Start QA before opening it')
            os.startfile(str(directory / 'ACCESO-PRIVADO.txt'))
            os.startfile(f'http://127.0.0.1:{cfg["webPort"]}')
            from qa_guide import generate, guide_path
            generate(profile=PROFILE)
            os.startfile(str(guide_path(PROFILE)))
        print(json.dumps({'running': active, 'origin': f'http://127.0.0.1:{cfg["webPort"]}',
            'accessFile': str(directory / 'ACCESO-PRIVADO.txt'), 'dataPreserved': True,
            'dllSha256': cfg['dllSha256'], 'bundleSha256': cfg['bundleSha256']}))
        if args.action == 'start' and not active:
            raise RuntimeError('QA is not ready')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'QA local failed: {type(error).__name__}; inspect private .local QA logs.', file=sys.stderr)
        sys.exit(1)
