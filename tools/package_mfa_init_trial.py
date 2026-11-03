"""Empaquetador del ensayo interno MFA-INIT (L2k). No es instalador ni actualizacion.

Construye RackClick-MFA-Ensayo-NN.zip (NN = edicion vigente, PACKAGE) en una carpeta nueva bajo .local/mfa-ensayo/:
1. copia identificada de las fuentes del servidor (snapshot), con manifiesto SHA256;
2. restauracion con packages.lock.json (--locked-mode) y publicacion Release sin apphost, desde la copia;
3. componentes del runtime 10.0.12 que ya incluye el SDK 10.0.401 fijado, sin cambiar versiones;
4. scripts del ensayo desde tools/windows/mfa-trial, BUILD-MANIFEST.json y SHA256SUMS;
5. verificacion del propio ZIP antes de darlo por bueno.

No ejecuta el ensayo, no instala nada en el sistema y no toca servicios, cuentas ni bases de datos.
El global.json de la raiz sigue siendo ancestro de la copia (vive en .local/); su paths apunta al mismo SDK 10.0.401.

Uso:
  python -I tools/package_mfa_init_trial.py build
  python -I tools/package_mfa_init_trial.py verify <ruta-del-zip>
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'RackClick-MFA-Ensayo-03'
TRIAL_PACKAGE_RE = re.compile(r'RackClick-MFA-Ensayo-\d\d')
NOTICE_SOURCES = ROOT / 'development' / 'offline-bundle14.sources.json'
NOTICE_TARGETS = {
    'Npgsql-LICENSE': ('licenses/Npgsql-LICENSE', 'npgsqlLicenseSha256', 'npgsqlSourceCommit'),
    'Otp.NET-LICENSE': ('licenses/Otp.NET-LICENSE.txt', 'otpNetLicenseSha256', 'otpNetSourceCommit'),
}
SDK_VERSION = '10.0.401'
RUNTIME_VERSION = '10.0.12'
SDK_ROOT = ROOT / '.local' / 'dotnet-10.0.401'
SERVER_ROOT = ROOT / 'development' / 'server'
PROJECT = 'src/RackClick.Server/RackClick.Server.csproj'
SOURCE_TREES = ('src/RackClick.Server', 'src/RackClick.Domain')
SOURCE_FILES = ('Directory.Build.props',)
SOURCE_GLOBS = ('database/*.sql',)
EXCLUDED_DIRS = frozenset({'bin', 'obj', '.vs', 'TestResults'})
EXCLUDED_SUFFIXES = ('.user', '.suo')
TRIAL_SCRIPTS = ROOT / 'tools' / 'windows' / 'mfa-trial'
TRIAL_FILES = ('INICIAR-ENSAYO-MFA.cmd', 'Invoke-MfaInitTrial.ps1', 'LEEME-ENSAYO-INTERNO.txt', 'GUION-ENTRADA-SALIDA.md')
RUNTIME_ITEMS = (
    ('dotnet.exe',),
    ('LICENSE.txt',),
    ('ThirdPartyNotices.txt',),
    ('host', 'fxr', RUNTIME_VERSION),
    ('shared', 'Microsoft.NETCore.App', RUNTIME_VERSION),
    ('shared', 'Microsoft.AspNetCore.App', RUNTIME_VERSION),
)
SERVER_ENTRY = 'servidor/RackClick.Server.dll'
SERVER_RUNTIMECONFIG = 'servidor/RackClick.Server.runtimeconfig.json'
LAUNCH_COMMAND = 'runtime\\dotnet.exe servidor\\RackClick.Server.dll --mfa-keys-init'
REQUIRED = (
    'INICIAR-ENSAYO-MFA.cmd', 'Invoke-MfaInitTrial.ps1', 'LEEME-ENSAYO-INTERNO.txt', 'GUION-ENTRADA-SALIDA.md',
    'BUILD-MANIFEST.json', 'SHA256SUMS',
    'runtime/dotnet.exe', 'runtime/LICENSE.txt', 'runtime/ThirdPartyNotices.txt',
    f'runtime/host/fxr/{RUNTIME_VERSION}/hostfxr.dll',
    f'runtime/shared/Microsoft.NETCore.App/{RUNTIME_VERSION}/hostpolicy.dll',
    f'runtime/shared/Microsoft.NETCore.App/{RUNTIME_VERSION}/System.Private.CoreLib.dll',
    f'runtime/shared/Microsoft.AspNetCore.App/{RUNTIME_VERSION}/Microsoft.AspNetCore.dll',
    SERVER_ENTRY, SERVER_RUNTIMECONFIG, 'servidor/RackClick.Server.deps.json',
    'licenses/Npgsql-LICENSE', 'licenses/Otp.NET-LICENSE.txt', 'licenses/README.txt',
)
REQUIRED_FRAMEWORKS = ('Microsoft.NETCore.App', 'Microsoft.AspNetCore.App')
FORBIDDEN_PARTS = frozenset({'.local', '.git', '.vs', 'bin', 'obj', 'evidence', 'docs', 'tests', 'recibos'})
FORBIDDEN_SUFFIXES = ('.binlog', '.pgpass', '.pfx', '.p12', '.snk', '.key', '.rckey', '.env', '.user', '.suo', '.pem', '.log')
FORBIDDEN_NAME = re.compile(r'(?i)(pgpass|password|passwd|credential|recibo|receipt|owner\.json|^ring\.json$)')
DROPPED_ENV = frozenset({'DOTNET_ROOT', 'DOTNET_ROOT(X86)', 'DOTNET_HOSTFXR_PATH', 'DOTNET_ADDITIONAL_DEPS',
                         'DOTNET_STARTUP_HOOKS', 'MSBUILDSDKSPATH', 'MSBUILD_EXE_PATH', 'MSBUILDEXTENSIONSPATH'})
# Profiler, EventPipe, perf maps y hooks heredados: se retiran del entorno de cada proceso del SDK; no se tocan variables globales.
CHILD_ENV_REMOVE = re.compile(r'^(CORECLR_PROFILER|COR_PROFILER|DOTNET_PROFILER|CORECLR_ENABLE_PROFILING|COR_ENABLE_PROFILING|'
                              r'DOTNET_ENABLE_PROFILING|DOTNET_PerfMap|DOTNET_EnableEventPipe|DOTNET_EventPipe)|NOTIFICATION',
                              re.IGNORECASE)
ZIP_DATE = (2026, 10, 27, 0, 0, 0)
SUMS_LINE = re.compile(r'([0-9a-f]{64})  (.+)')


class PackageError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def sdk_env():
    env = {key: value for key, value in os.environ.items()
           if key.upper() not in DROPPED_ENV and not CHILD_ENV_REMOVE.search(key)}
    env['DOTNET_NOLOGO'] = '1'
    env['DOTNET_CLI_TELEMETRY_OPTOUT'] = '1'
    env['DOTNET_EnableDiagnostics'] = '0'
    env['CORECLR_ENABLE_PROFILING'] = '0'
    env['DOTNET_ENABLE_PROFILING'] = '0'
    return env


def run(args, cwd, log=None):
    proc = subprocess.run(args, cwd=cwd, env=sdk_env(), capture_output=True, text=True,
                          encoding='utf-8', errors='replace')
    if log is not None:
        log.write_text(proc.stdout + '\n--- stderr ---\n' + proc.stderr, encoding='utf-8')
    return proc


def copy_sources(dest_server):
    """Copia el arbol de fuentes con la disposicion relativa de development/server y registra cada archivo."""
    entries = []

    def take(src, rel):
        if src.is_symlink():
            raise PackageError('source_symlink')
        target = dest_server / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        before = sha256_file(src)
        shutil.copyfile(src, target)
        if sha256_file(target) != before:
            raise PackageError('source_copy_mismatch')
        entries.append({'path': rel, 'sha256': before, 'bytes': target.stat().st_size})

    for tree in SOURCE_TREES:
        for src in sorted((SERVER_ROOT / tree).rglob('*')):
            if src.is_dir():
                continue
            rel = src.relative_to(SERVER_ROOT)
            if any(part in EXCLUDED_DIRS for part in rel.parts[:-1]) or src.name.endswith(EXCLUDED_SUFFIXES):
                continue
            take(src, rel.as_posix())
    for name in SOURCE_FILES:
        take(SERVER_ROOT / name, name)
    for pattern in SOURCE_GLOBS:
        for src in sorted(SERVER_ROOT.glob(pattern)):
            take(src, src.relative_to(SERVER_ROOT).as_posix())
    return entries


def verify_snapshot_unchanged(snapshot, entries):
    expected = {entry['path']: entry['sha256'] for entry in entries}
    current = set()
    for tree in SOURCE_TREES:
        for src in (snapshot / tree).rglob('*'):
            if src.is_dir() or any(part in EXCLUDED_DIRS for part in src.relative_to(snapshot).parts[:-1]):
                continue
            if src.name.endswith(EXCLUDED_SUFFIXES):
                continue
            current.add(src.relative_to(snapshot).as_posix())
    for name in SOURCE_FILES:
        current.add(name)
    for pattern in SOURCE_GLOBS:
        for src in snapshot.glob(pattern):
            current.add(src.relative_to(snapshot).as_posix())
    if current != set(expected):
        raise PackageError('snapshot_changed_during_build')
    for rel, digest in expected.items():
        if sha256_file(snapshot / rel) != digest:
            raise PackageError('snapshot_changed_during_build')


def git_state():
    git = shutil.which('git')
    if git is None:
        raise PackageError('git_unavailable')
    head = subprocess.run([git, 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=False)
    if head.returncode != 0 or not re.fullmatch(r'[0-9a-f]{40}', head.stdout.strip()):
        raise PackageError('git_head_unavailable')
    status = subprocess.run([git, 'status', '--porcelain', '--', 'development/server', 'tools/windows/mfa-trial',
                             'tools/package_mfa_init_trial.py'], cwd=ROOT, capture_output=True, text=True,
                            encoding='utf-8', check=False)
    dirty = sorted(line[3:] for line in status.stdout.splitlines() if line.strip())
    return {'head': head.stdout.strip(), 'workingTreeDirtyPaths': dirty}


def find_pin(node):
    if isinstance(node, dict):
        if node.get('id') == 'dotnet':
            return node
        for value in node.values():
            found = find_pin(value)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = find_pin(value)
            if found is not None:
                return found
    return None


def sdk_identity(snapshot):
    exe = SDK_ROOT / 'dotnet.exe'
    if not exe.is_file():
        raise PackageError('sdk_missing')
    proc = run([str(exe), '--version'], cwd=snapshot)
    version = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ''
    if proc.returncode != 0 or version != SDK_VERSION:
        raise PackageError('sdk_version_mismatch')
    lock = json.loads((ROOT / 'development' / 'toolchain.lock.json').read_text(encoding='utf-8'))
    pin = find_pin(lock)
    if pin is None or pin.get('version') != SDK_VERSION:
        raise PackageError('sdk_pin_mismatch')
    return {
        'version': SDK_VERSION,
        'root': '.local/dotnet-10.0.401',
        'dotnetExeSha256': sha256_file(exe),
        'pin': {'id': 'dotnet', 'version': pin['version'], 'hashAlgorithm': pin.get('hashAlgorithm'),
                'hash': pin.get('hash'), 'source': 'development/toolchain.lock.json'},
        'globalJsonInSnapshot': False,
        'versionCheckInSnapshot': version,
    }


def restore_and_publish(snapshot, out, logs):
    exe = str(SDK_ROOT / 'dotnet.exe')
    project = snapshot / PROJECT
    binlogs = logs.parent / 'binlogs'
    binlogs.mkdir(parents=True, exist_ok=True)
    restore = run([exe, 'restore', str(project), '--locked-mode', '--disable-build-servers', '--tl:off',
                   '--verbosity', 'minimal', f'-bl:{binlogs / "restore.binlog"}'], cwd=snapshot, log=logs / 'restore.txt')
    if restore.returncode != 0:
        raise PackageError('restore_failed')
    publish = run([exe, 'publish', str(project), '-c', 'Release', '--no-restore', '--disable-build-servers',
                   '--tl:off', '--verbosity', 'minimal', '-p:UseAppHost=false', '-o', str(out),
                   f'-bl:{binlogs / "publish.binlog"}'],
                  cwd=snapshot, log=logs / 'publish.txt')
    if publish.returncode != 0:
        raise PackageError('publish_failed')
    return ['dotnet', 'restore', PROJECT, '--locked-mode'], ['dotnet', 'publish', PROJECT, '-c', 'Release',
                                                          '--no-restore', '-p:UseAppHost=false']


def copy_runtime(runtime_root, dest):
    copied = []
    for item in RUNTIME_ITEMS:
        src = runtime_root.joinpath(*item)
        if src.is_symlink():
            raise PackageError('runtime_symlink')
        if src.is_file():
            files = [src]
        elif src.is_dir():
            files = [f for f in sorted(src.rglob('*')) if not f.is_dir()]
        else:
            raise PackageError('runtime_component_missing')
        for file in files:
            if file.is_symlink():
                raise PackageError('runtime_symlink')
            rel = file.relative_to(runtime_root).as_posix()
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, target)
            copied.append(rel)
    return copied


def load_notice_pins(path=NOTICE_SOURCES):
    """Avisos Npgsql y Otp.NET desde los pins existentes. Ausente, alterado o con pines incoherentes: se detiene."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    entries = {item.get('name'): item for item in data.get('sources', [])}
    notices = []
    for name, (target, key, commit_key) in NOTICE_TARGETS.items():
        item = entries.get(name)
        if item is None or data.get(key) != item.get('sha256'):
            raise PackageError('notice_pin_inconsistent')
        source = ROOT / item['path']
        if not source.is_file() or source.stat().st_size != item.get('bytes') or sha256_file(source) != item['sha256']:
            raise PackageError('notice_source_mismatch')
        notices.append({'target': target, 'source': source, 'bytes': item['bytes'], 'sha256': item['sha256'],
                        'pinKey': key, 'commit': data.get(commit_key), 'url': item.get('resolvedUrl')})
    return notices


def copy_notices(notices, tree):
    """Copia los avisos verificados y escribe licenses/README.txt con las fuentes. Solo hechos del pin; no decide licencias."""
    entries = []
    for notice in notices:
        source = Path(notice['source'])
        if not source.is_file() or source.stat().st_size != notice['bytes'] or sha256_file(source) != notice['sha256']:
            raise PackageError('notice_source_mismatch')
        target = tree / notice['target']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if sha256_file(target) != notice['sha256']:
            raise PackageError('notice_copy_mismatch')
        entries.append({'path': notice['target'], 'sha256': notice['sha256'], 'bytes': notice['bytes'],
                        'pin': notice.get('pinKey'), 'sourceCommit': notice.get('commit'), 'sourceUrl': notice.get('url')})
    readme = [
        f'Avisos de terceros del ensayo interno {PACKAGE} (no es instalador ni actualizacion).',
        'Npgsql: licenses/Npgsql-LICENSE. Pin npgsqlLicenseSha256 y commit de development/offline-bundle14.sources.json.',
        'Otp.NET: licenses/Otp.NET-LICENSE.txt. Pin otpNetLicenseSha256 y commit de development/offline-bundle14.sources.json.',
        'Versiones del lock de RackClick.Server: Npgsql 10.0.3 y Otp.NET 1.4.1.',
        'Avisos oficiales de .NET: runtime/LICENSE.txt y runtime/ThirdPartyNotices.txt.',
    ]
    readme_path = tree / 'licenses' / 'README.txt'
    readme_path.write_text('\n'.join(readme) + '\n', encoding='ascii')
    entries.append({'path': 'licenses/README.txt', 'sha256': sha256_file(readme_path),
                    'bytes': readme_path.stat().st_size, 'pin': None, 'sourceCommit': None, 'sourceUrl': None})
    return entries


def copy_server(published, dest):
    if not (published / 'RackClick.Server.dll').is_file():
        raise PackageError('server_publish_missing')
    shutil.copytree(published, dest, symlinks=False)
    return sorted(p.relative_to(dest).as_posix() for p in dest.rglob('*') if p.is_file())


def check_runtimeconfig(text):
    data = json.loads(text)
    options = data.get('runtimeOptions', {})
    declared = [options.get('framework')] + list(options.get('frameworks', []))
    names = {item.get('name'): item.get('version') for item in declared if isinstance(item, dict)}
    for name in REQUIRED_FRAMEWORKS:
        if name not in names or not str(names[name]).startswith('10.0.'):
            return False
    return True


def forbidden_reason(rel):
    parts = PurePosixPath(rel).parts
    if any(part in FORBIDDEN_PARTS for part in parts):
        return 'part'
    name = parts[-1]
    if name.lower().endswith(FORBIDDEN_SUFFIXES):
        return 'suffix'
    if FORBIDDEN_NAME.search(name):
        return 'name'
    return None


def write_sums(tree):
    lines = []
    for file in sorted(p for p in tree.rglob('*') if p.is_file()):
        rel = file.relative_to(tree).as_posix()
        if rel == 'SHA256SUMS':
            continue
        lines.append(f'{sha256_file(file)}  {rel}')
    (tree / 'SHA256SUMS').write_text('\n'.join(lines) + '\n', encoding='ascii')


def zip_tree(tree, zip_path):
    with zipfile.ZipFile(zip_path, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(p for p in tree.rglob('*') if p.is_file()):
            rel = file.relative_to(tree).as_posix()
            info = zipfile.ZipInfo(f'{PACKAGE}/{rel}', date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, file.read_bytes())


def verify_zip(zip_path):
    problems = []
    digests = {}
    contents = {}
    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        folders = sorted({name.split('/')[0] for name in names if '/' in name})
        folder = folders[0] if len(folders) == 1 else ''
        if len(set(names)) != len(names):
            problems.append('zip_duplicate_entry')
        for info in infos:
            name = info.filename
            if name.endswith('/'):
                problems.append('zip_directory_entry')
                continue
            parts = PurePosixPath(name).parts
            if ('\\' in name or name.startswith('/') or re.match(r'^[A-Za-z]:', name) or not parts
                    or not TRIAL_PACKAGE_RE.fullmatch(parts[0]) or any(part in ('', '.', '..') for part in parts[1:])):
                problems.append('zip_unsafe_name')
                continue
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                problems.append('zip_symlink')
            rel = '/'.join(parts[1:])
            reason = forbidden_reason(rel)
            if reason is not None:
                problems.append(f'forbidden_entry:{rel}')
            if rel in digests:
                problems.append('zip_duplicate_entry')
                continue
            digest = hashlib.sha256()
            with archive.open(info) as stream:
                for chunk in iter(lambda: stream.read(1 << 20), b''):
                    digest.update(chunk)
            digests[rel] = digest.hexdigest()
            if rel.endswith(('.ps1', '.cmd', 'SHA256SUMS', 'BUILD-MANIFEST.json', 'runtimeconfig.json')):
                contents[rel] = archive.read(info)
        for rel in REQUIRED:
            if rel not in digests:
                problems.append(f'required_missing:{rel}')
        for rel in digests:
            if rel.endswith(('.ps1', '.cmd')):
                try:
                    contents[rel].decode('ascii')
                except UnicodeDecodeError:
                    problems.append(f'non_ascii_script:{rel}')
        listed = {}
        if 'SHA256SUMS' not in digests:
            problems.append('sums_missing')
        else:
            for line in contents['SHA256SUMS'].decode('ascii', errors='replace').splitlines():
                match = SUMS_LINE.fullmatch(line)
                if match is None:
                    problems.append('sums_malformed')
                    continue
                if match.group(2) in listed:
                    problems.append('sums_duplicate')
                listed[match.group(2)] = match.group(1)
        expected = set(digests) - {'SHA256SUMS'}
        for rel in sorted(expected - set(listed)):
            problems.append(f'sums_unlisted:{rel}')
        for rel in sorted(set(listed) - expected):
            problems.append(f'sums_missing_file:{rel}')
        for rel in sorted(expected & set(listed)):
            if listed[rel] != digests[rel]:
                problems.append(f'hash_mismatch:{rel}')
        if 'BUILD-MANIFEST.json' in contents:
            try:
                manifest = json.loads(contents['BUILD-MANIFEST.json'].decode('utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError):
                manifest = None
                problems.append('manifest_invalid:json')
            if manifest is not None:
                checks = {
                    'internalTrial': manifest.get('internalTrial') is True,
                    'notInstaller': manifest.get('notInstaller') is True,
                    'runtime.version': manifest.get('runtime', {}).get('version') == RUNTIME_VERSION,
                    'sdk.version': manifest.get('sdk', {}).get('version') == SDK_VERSION,
                    'server.entrypoint': manifest.get('server', {}).get('entrypoint') == SERVER_ENTRY,
                    'package': bool(folder) and manifest.get('package') == folder,
                    'edition': bool(folder) and manifest.get('edition') == folder[-2:],
                    'launch.command': manifest.get('launch', {}).get('command') == LAUNCH_COMMAND,
                }
                for key, ok in checks.items():
                    if not ok:
                        problems.append(f'manifest_invalid:{key}')
                licenses = manifest.get('licenses') or []
                if not licenses:
                    problems.append('manifest_invalid:licenses')
                for item in licenses:
                    if digests.get(item.get('path')) != item.get('sha256'):
                        problems.append(f"notice_manifest_mismatch:{item.get('path')}")
        if SERVER_RUNTIMECONFIG in contents and not check_runtimeconfig(contents[SERVER_RUNTIMECONFIG].decode('utf-8')):
            problems.append('runtimeconfig_frameworks_invalid')
    return {
        'zip': Path(zip_path).name,
        'zipSha256': sha256_file(zip_path),
        'entries': len(digests),
        'problems': sorted(set(problems)),
        'ok': not problems,
    }


def build():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir = ROOT / '.local' / 'mfa-ensayo' / f'{stamp}-{uuid.uuid4().hex[:8]}'
    logs = run_dir / 'logs'
    snapshot = run_dir / 'fuente' / 'development' / 'server'
    logs.mkdir(parents=True)
    snapshot.mkdir(parents=True)
    source_entries = copy_sources(snapshot)
    git = git_state()
    sdk = sdk_identity(snapshot)
    command_summary = restore_and_publish(snapshot, run_dir / 'servidor-publicado', logs)
    verify_snapshot_unchanged(snapshot, source_entries)
    return assemble_package(run_dir, run_dir / 'servidor-publicado', source_entries=source_entries, git=git,
                            sdk=sdk, command_summary=command_summary)


def assemble_package(run_dir, published, *, source_entries, git, sdk, command_summary,
                     runtime_root=None, scripts_root=None, notices=None):
    """Ensambla el arbol del paquete, el manifiesto, SHA256SUMS y el ZIP, y verifica el ZIP. No publica ni consulta el SDK."""
    runtime_root = runtime_root or SDK_ROOT
    scripts_root = scripts_root or TRIAL_SCRIPTS
    tree = run_dir / 'paquete' / PACKAGE
    tree.mkdir(parents=True)
    runtime_files = copy_runtime(runtime_root, tree / 'runtime')
    server_files = copy_server(published, tree / 'servidor')
    notice_entries = copy_notices(load_notice_pins() if notices is None else notices, tree)
    scripts = {}
    for name in TRIAL_FILES:
        source = scripts_root / name
        if not source.is_file():
            raise PackageError('trial_script_missing')
        shutil.copyfile(source, tree / name)
        scripts[name] = sha256_file(source)

    runtime_pins = {rel: sha256_file(tree / 'runtime' / rel)
                    for rel in ('dotnet.exe', 'LICENSE.txt', 'ThirdPartyNotices.txt',
                                f'host/fxr/{RUNTIME_VERSION}/hostfxr.dll',
                                f'shared/Microsoft.NETCore.App/{RUNTIME_VERSION}/hostpolicy.dll')}
    manifest = {
        'schemaVersion': 1,
        'kind': 'RackClickMfaInitTrialBuild',
        'package': PACKAGE,
        'internalTrial': True,
        'notInstaller': True,
        'notUpdate': True,
        'builtUtc': datetime.now(timezone.utc).isoformat(),
        'source': {
            'gitHead': git['head'],
            'workingTreeDirtyPaths': git['workingTreeDirtyPaths'],
            'note': 'Copia identificada del arbol de trabajo; los hashes por archivo son la identidad real de las fuentes.',
            'files': source_entries,
        },
        'sdk': sdk,
        'runtime': {
            'version': RUNTIME_VERSION,
            'source': 'Componentes incluidos en el SDK 10.0.401 fijado (.local/dotnet-10.0.401); no se cambia ninguna version.',
            'fileCount': len(runtime_files),
            'pins': runtime_pins,
            'notices': ['LICENSE.txt', 'ThirdPartyNotices.txt'],
        },
        'publish': {
            'project': PROJECT,
            'configuration': 'Release',
            'useAppHost': False,
            'restore': 'locked-mode (packages.lock.json)',
            'commands': [' '.join(command_summary[0]), ' '.join(command_summary[1])],
            'globalJsonCopied': False,
        },
        'server': {
            'entrypoint': SERVER_ENTRY,
            'fileCount': len(server_files),
            'dllSha256': sha256_file(tree / SERVER_ENTRY),
            'runtimeconfigSha256': sha256_file(tree / SERVER_RUNTIMECONFIG),
        },
        'trialScripts': scripts,
        'edition': PACKAGE[-2:],
        'licenses': notice_entries,
        'publication': {
            'binlogSha256': {p.name: sha256_file(p) for p in sorted((run_dir / 'binlogs').glob('*.binlog'))},
            'note': 'Binlogs privados fuera del paquete; sus hashes identifican la invocacion usada, no una reconstruccion bit a bit.',
        },
        'launch': {
            'command': LAUNCH_COMMAND,
            'argsRequired': ['--mfa-keys-init'],
            'notRun': ['host normal', 'comandos PostgreSQL', 'MfaKeyStore:Enabled', 'listener', 'firewall', 'servicios', 'bases de datos'],
        },
        'excluded': ['.local/', 'binlogs', 'secretos', 'credenciales', 'propietario y ring.json', 'recibos'],
        'limits': [
            'No acredita que el servicio lea la clave.',
            'La consulta de SID por SCM no es ejecucion bajo ese SID.',
            'MFA no queda disponible para usuarios.',
        ],
    }
    (tree / 'BUILD-MANIFEST.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + '\n', encoding='ascii')
    write_sums(tree)
    zip_path = run_dir / f'{PACKAGE}.zip'
    zip_tree(tree, zip_path)
    report = verify_zip(zip_path)
    if not report['ok']:
        raise PackageError('zip_verification_failed')
    return zip_path, report


def main(argv):
    try:
        if argv == ['build']:
            zip_path, report = build()
            print(json.dumps({'status': 'built', 'zip': str(zip_path.relative_to(ROOT)), 'report': report}, indent=2))
            return 0
        if len(argv) == 2 and argv[0] == 'verify':
            report = verify_zip(Path(argv[1]))
            print(json.dumps(report, indent=2))
            return 0 if report['ok'] else 1
        print('uso: build | verify <zip>', file=sys.stderr)
        return 2
    except PackageError as error:
        print(json.dumps({'status': 'failed', 'code': error.code}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
