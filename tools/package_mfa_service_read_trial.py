"""Empaquetador del comprobador de lectura con el token del servicio (L2l02). No es instalador ni activa MFA.

Construye RackClick-MFA-Lectura-L2l02.zip en una carpeta nueva bajo .local/mfa-lectura-l2l02/:
1. comprobador .NET compilado desde una copia identificada de tools/mfa-service-read-probe, contra la DLL 03 aprobada;
2. runtime y avisos copiados del paquete 03 aprobado, verificados byte a byte contra su SHA256SUMS;
3. scripts (PowerShell directo, sin .cmd) y manifiesto con hashes de fuentes y del SDK fijado;
4. SHA256SUMS y verificacion del propio ZIP.

No ejecuta el comprobador, no toca servicios, cuentas ni VM, y no escribe en ProgramData.

Uso:
  python -I tools/package_mfa_service_read_trial.py build
  python -I tools/package_mfa_service_read_trial.py verify <ruta-del-zip>
"""
import hashlib
import importlib.util
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
SPEC_03 = importlib.util.spec_from_file_location('package_mfa_init_trial', ROOT / 'tools' / 'package_mfa_init_trial.py')
base = importlib.util.module_from_spec(SPEC_03)
SPEC_03.loader.exec_module(base)

PACKAGE = 'RackClick-MFA-Lectura-L2l02'
PACKAGE_RE = re.compile(r'RackClick-MFA-Lectura-L2l\d\d')
SDK_ROOT = base.SDK_ROOT
SDK_VERSION = base.SDK_VERSION
RUNTIME_VERSION = base.RUNTIME_VERSION
REF03_DIR = ROOT / '.local' / 'mfa-ensayo' / '20261027T102037Z-cf65eea8' / 'paquete' / 'RackClick-MFA-Ensayo-03'
REF03_SUMS = '51096278e330298bc5c390de190bdf1405ce1b56604c95603552ea8f18d3dd6f'
REF03_DLL = 'dfda3c93b0aa861ee8aecad144ed387fd7511991a6f9fb345f19553bdc7fb9ee'
PROBE_DIR = ROOT / 'tools' / 'mfa-service-read-probe'
PROBE_PROJECT = 'RackClick.MfaServiceReadProbe.csproj'
PROBE_SOURCES = ('Program.cs', 'Measure.cs', 'Native.cs', PROBE_PROJECT)
SCRIPTS_DIR = ROOT / 'tools' / 'windows' / 'mfa-service-read-trial'
# Guia del operador por edicion: cada paquete exige el nombre con el que se entrego. La 01 no se reconstruye.
LEEME_BY_EDITION = {'01': 'LEEME-LECTURA-L2L01.txt', '02': 'LEEME-LECTURA-L2L02.txt'}
SCRIPT_FILES = ('Invoke-MfaServiceReadTrial.ps1', LEEME_BY_EDITION[PACKAGE[-2:]])
SHARED_SERVER_FILES = ('RackClick.Server.dll', 'RackClick.Domain.dll', 'Npgsql.dll', 'Otp.NET.dll')
PROBE_RUNTIME_CONFIG = 'probe/RackClick.MfaServiceReadProbe.runtimeconfig.json'
PROBE_DLL = 'probe/RackClick.MfaServiceReadProbe.dll'
LICENSE_FILES = ('licenses/Npgsql-LICENSE', 'licenses/Otp.NET-LICENSE.txt', 'licenses/README.txt')


def required_for(edition):
    """Archivos que debe contener un paquete de la edicion indicada. Edicion desconocida: lista vacia (el verificador la rechaza)."""
    if edition not in LEEME_BY_EDITION:
        return ()
    return (
        LEEME_BY_EDITION[edition], 'Invoke-MfaServiceReadTrial.ps1', 'BUILD-MANIFEST.json', 'SHA256SUMS',
        'runtime/dotnet.exe', 'runtime/LICENSE.txt', 'runtime/ThirdPartyNotices.txt',
        PROBE_DLL, PROBE_RUNTIME_CONFIG,
        'probe/RackClick.Server.dll', 'probe/RackClick.Domain.dll', 'probe/Npgsql.dll', 'probe/Otp.NET.dll',
    ) + LICENSE_FILES
FORBIDDEN_PARTS = frozenset({'.local', '.git', '.vs', 'bin', 'obj', 'evidence', 'docs', 'tests', 'recibos'})
FORBIDDEN_SUFFIXES = ('.binlog', '.pgpass', '.pfx', '.p12', '.snk', '.key', '.rckey', '.env', '.user', '.suo', '.pem')
FORBIDDEN_NAME = re.compile(r'(?i)(pgpass|password|passwd|credential|recibo|receipt|owner\.json|^ring\.json$)')
SUMS_LINE = re.compile(r'([0-9a-f]{64})  (.+)')
ZIP_DATE = (2026, 10, 27, 0, 0, 0)
# Verbos que la sonda acepta en cada edición. La 01 se conserva tal como se entregó; la 02 añade selftest-privilege.
PROBE_VERBS_BY_EDITION = {
    '01': ['read', 'selftest-token', 'selftest-deny'],
    '02': ['read', 'selftest-token', 'selftest-deny', 'selftest-privilege'],
}
DIRTY_SCOPE = ('solo las rutas del lote L2l seleccionadas (sonda, script y pruebas del comprobador, empaquetador); '
               'no es el inventario completo del repositorio')


class PackageError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def parse_sums(path):
    entries = {}
    for line in path.read_text(encoding='ascii').splitlines():
        match = SUMS_LINE.fullmatch(line)
        if match is None or match.group(2) in entries:
            raise PackageError('ref03_sums_malformed')
        entries[match.group(2)] = match.group(1)
    return entries


def verify_reference_03():
    """El paquete 03 aprobado debe ser exactamente el de la entrega: SHA256SUMS esperado y DLL identificada."""
    sums_path = REF03_DIR / 'SHA256SUMS'
    if not sums_path.is_file() or base.sha256_file(sums_path) != REF03_SUMS:
        raise PackageError('ref03_sums_mismatch')
    entries = parse_sums(sums_path)
    if entries.get('servidor/RackClick.Server.dll') != REF03_DLL:
        raise PackageError('ref03_dll_mismatch')
    return entries


def copy_verified(source, target, expected_sha):
    if not source.is_file() or base.sha256_file(source) != expected_sha:
        raise PackageError('ref03_file_mismatch')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    if base.sha256_file(target) != expected_sha:
        raise PackageError('copy_mismatch')


def copy_runtime_from_03(entries, dest):
    files = []
    for rel, sha in sorted(entries.items()):
        if not rel.startswith('runtime/'):
            continue
        copy_verified(REF03_DIR / rel, dest / rel, sha)
        files.append(rel)
    if not files:
        raise PackageError('ref03_runtime_missing')
    return files


def copy_licenses_from_03(entries, dest):
    for rel in LICENSE_FILES:
        if rel not in entries:
            raise PackageError('ref03_license_missing')
        copy_verified(REF03_DIR / rel, dest / rel, entries[rel])


def snapshot_probe_sources(dest):
    records = []
    dest.mkdir(parents=True, exist_ok=True)
    for name in PROBE_SOURCES:
        source = PROBE_DIR / name
        if not source.is_file():
            raise PackageError('probe_source_missing')
        target = dest / name
        shutil.copyfile(source, target)
        if base.sha256_file(target) != base.sha256_file(source):
            raise PackageError('probe_source_copy_mismatch')
        records.append({'path': name, 'sha256': base.sha256_file(target), 'bytes': target.stat().st_size})
    return records


def git_head():
    git = shutil.which('git')
    if git is None:
        raise PackageError('git_unavailable')
    head = subprocess.run([git, 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=False)
    if head.returncode != 0 or not re.fullmatch(r'[0-9a-f]{40}', head.stdout.strip()):
        raise PackageError('git_head_unavailable')
    selected = ['tools/mfa-service-read-probe', 'tools/windows/mfa-service-read-trial',
                'tools/package_mfa_service_read_trial.py', 'tools/tests/test_mfa_service_read_trial.py']
    status = subprocess.run([git, 'status', '--porcelain', '--'] + selected,
                            cwd=ROOT, capture_output=True, text=True, encoding='utf-8', check=False)
    if status.returncode != 0:
        raise PackageError('git_status_unavailable')
    dirty = sorted(line[3:] for line in status.stdout.splitlines() if line.strip())
    return {'head': head.stdout.strip(), 'dirtyPaths': dirty, 'dirtyScope': DIRTY_SCOPE, 'selectedPaths': selected}


def sdk_env():
    env = base.sdk_env()
    env['DOTNET_CLI_UI_LANGUAGE'] = 'en'
    return env


def compile_probe(snapshot, out, logs, binlogs):
    exe = str(SDK_ROOT / 'dotnet.exe')
    project = snapshot / PROBE_PROJECT
    server_dir = str(REF03_DIR / 'servidor')
    restore = subprocess.run([exe, 'restore', str(project), '--locked-mode', '--disable-build-servers', '--tl:off',
                              '--verbosity', 'minimal', f'-p:RackClickServerDir={server_dir}',
                              f'-bl:{binlogs / "restore-probe.binlog"}'],
                             cwd=snapshot, env=sdk_env(), capture_output=True, text=True, encoding='utf-8', errors='replace')
    (logs / 'restore-probe.txt').write_text(restore.stdout + '\n--- stderr ---\n' + restore.stderr, encoding='utf-8')
    if restore.returncode != 0:
        raise PackageError('probe_restore_failed')
    publish = subprocess.run([exe, 'publish', str(project), '-c', 'Release', '--no-restore', '--disable-build-servers',
                              '--tl:off', '--verbosity', 'minimal', '-p:UseAppHost=false', f'-p:RackClickServerDir={server_dir}',
                              '-o', str(out), f'-bl:{binlogs / "publish-probe.binlog"}'],
                             cwd=snapshot, env=sdk_env(), capture_output=True, text=True, encoding='utf-8', errors='replace')
    (logs / 'publish-probe.txt').write_text(publish.stdout + '\n--- stderr ---\n' + publish.stderr, encoding='utf-8')
    if publish.returncode != 0:
        raise PackageError('probe_publish_failed')


def sdk_pin():
    lock = json.loads((ROOT / 'development' / 'toolchain.lock.json').read_text(encoding='utf-8'))
    pin = base.find_pin(lock)
    if pin is None or pin.get('version') != SDK_VERSION:
        raise PackageError('sdk_pin_mismatch')
    return {'id': 'dotnet', 'version': pin['version'], 'hashAlgorithm': pin.get('hashAlgorithm'), 'hash': pin.get('hash'),
            'source': 'development/toolchain.lock.json'}


def copy_probe_and_scripts(tree, probe_out):
    """probe/ y scripts. El manifiesto y SHA256SUMS los escribe build() al final."""
    shutil.copytree(probe_out, tree / 'probe')
    for name in SCRIPT_FILES:
        source = SCRIPTS_DIR / name
        if not source.is_file():
            raise PackageError('script_missing')
        shutil.copyfile(source, tree / name)


def write_sums(tree):
    lines = []
    for file in sorted(p for p in tree.rglob('*') if p.is_file()):
        rel = file.relative_to(tree).as_posix()
        if rel == 'SHA256SUMS':
            continue
        lines.append(f'{base.sha256_file(file)}  {rel}')
    (tree / 'SHA256SUMS').write_text('\n'.join(lines) + '\n', encoding='ascii')


def zip_tree(tree, zip_path):
    with zipfile.ZipFile(zip_path, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(p for p in tree.rglob('*') if p.is_file()):
            rel = file.relative_to(tree).as_posix()
            info = zipfile.ZipInfo(f'{PACKAGE}/{rel}', date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, file.read_bytes())


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
                    or not PACKAGE_RE.fullmatch(parts[0]) or any(part in ('', '.', '..') for part in parts[1:])):
                problems.append('zip_unsafe_name')
                continue
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                problems.append('zip_symlink')
            rel = '/'.join(parts[1:])
            if forbidden_reason(rel) is not None:
                problems.append(f'forbidden_entry:{rel}')
            if rel in digests:
                problems.append('zip_duplicate_entry')
                continue
            digest = hashlib.sha256()
            with archive.open(info) as stream:
                for chunk in iter(lambda: stream.read(1 << 20), b''):
                    digest.update(chunk)
            digests[rel] = digest.hexdigest()
            if rel.endswith(('.ps1', '.txt', 'SHA256SUMS', 'BUILD-MANIFEST.json', 'runtimeconfig.json')):
                contents[rel] = archive.read(info)
        edition = folder[-2:] if folder else ''
        if edition not in LEEME_BY_EDITION:
            problems.append('edition_unknown')
        for rel in required_for(edition):
            if rel not in digests:
                problems.append(f'required_missing:{rel}')
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
                    'notMfaActivation': manifest.get('notMfaActivation') is True,
                    'runtime.version': manifest.get('runtime', {}).get('version') == RUNTIME_VERSION,
                    'sdk.version': manifest.get('sdk', {}).get('version') == SDK_VERSION,
                    'package': bool(folder) and manifest.get('package') == folder,
                    'edition': bool(folder) and manifest.get('edition') == folder[-2:],
                    'probe.dll03': manifest.get('probe', {}).get('reference03DllSha256') == REF03_DLL,
                    'probe.dllSha256': manifest.get('probe', {}).get('dllSha256') == digests.get(PROBE_DLL),
                    'probe.verbs': bool(folder) and manifest.get('probe', {}).get('verbs') == PROBE_VERBS_BY_EDITION.get(folder[-2:]),
                }
                for key, ok in checks.items():
                    if not ok:
                        problems.append(f'manifest_invalid:{key}')
                for item in manifest.get('licenses', []) or []:
                    if digests.get(item.get('path')) != item.get('sha256'):
                        problems.append(f"notice_manifest_mismatch:{item.get('path')}")
    return {
        'zip': Path(zip_path).name,
        'zipSha256': base.sha256_file(zip_path),
        'entries': len(digests),
        'problems': sorted(set(problems)),
        'ok': not problems,
    }


def build():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir = ROOT / '.local' / 'mfa-lectura-l2l02' / f'{stamp}-{uuid.uuid4().hex[:8]}'
    logs = run_dir / 'logs'
    binlogs = run_dir / 'binlogs'
    logs.mkdir(parents=True)
    binlogs.mkdir()
    entries03 = verify_reference_03()
    snapshot = run_dir / 'fuente'
    probe_sources = snapshot_probe_sources(snapshot)
    git = git_head()
    sdk = {'version': SDK_VERSION, 'root': '.local/dotnet-10.0.401', 'dotnetExeSha256': base.sha256_file(SDK_ROOT / 'dotnet.exe'),
           'pin': sdk_pin()}
    probe_out = run_dir / 'probe-out'
    compile_probe(snapshot, probe_out, logs, binlogs)
    for name in SHARED_SERVER_FILES:
        if base.sha256_file(probe_out / name) != entries03['servidor/' + name]:
            raise PackageError('probe_output_dll_mismatch')

    tree = run_dir / 'paquete' / PACKAGE
    tree.mkdir(parents=True)
    copy_probe_and_scripts(tree, probe_out)
    runtime_files = copy_runtime_from_03(entries03, tree)
    copy_licenses_from_03(entries03, tree)
    manifest = {
        'schemaVersion': 1,
        'kind': 'RackClickMfaServiceReadTrialBuild',
        'package': PACKAGE,
        'edition': PACKAGE[-2:],
        'internalTrial': True,
        'notInstaller': True,
        'notUpdate': True,
        'notMfaActivation': True,
        'builtUtc': datetime.now(timezone.utc).isoformat(),
        'source': {'gitHead': git['head'], 'workingTreeDirtyPaths': git['dirtyPaths'], 'dirtyPathsScope': git['dirtyScope'],
                   'selectedPaths': git['selectedPaths'], 'probeSources': probe_sources},
        'reference03': {'package': 'RackClick-MFA-Ensayo-03', 'sumsSha256': REF03_SUMS, 'dllSha256': REF03_DLL,
                        'verificacion': 'SHA256SUMS y DLL verificados antes de copiar runtime, avisos y DLL'},
        'sdk': sdk,
        'runtime': {'version': RUNTIME_VERSION, 'fileCount': len(runtime_files),
                    'source': 'runtime del paquete 03 aprobado (copia byte a byte verificada)'},
        'probe': {'dllSha256': base.sha256_file(tree / PROBE_DLL), 'reference03DllSha256': REF03_DLL,
                  'verbs': PROBE_VERBS_BY_EDITION[PACKAGE[-2:]], 'operatorVerb': 'read',
                  'referenceCompiledAgainst': 'servidor de la publicacion 03 aprobada (sin reconstruir el arbol de producto)'},
        'licenses': [{'path': rel, 'sha256': base.sha256_file(tree / rel), 'bytes': (tree / rel).stat().st_size}
                     for rel in LICENSE_FILES],
        'scripts': {name: base.sha256_file(SCRIPTS_DIR / name) for name in SCRIPT_FILES},
        'publication': {'binlogSha256': {p.name: base.sha256_file(p) for p in sorted(binlogs.glob('*.binlog'))}},
        'excluded': ['.local/', 'binlogs', 'secretos', 'credenciales', 'recibos', 'claves y blobs'],
        'limits': [
            'Demuestra la lectura con el token del servicio solo cuando se ejecuta en la VM elevada.',
            'No demuestra la activacion del proveedor dentro del host en marcha ni el login con MFA.',
            'WRITE_DAC para un propietario que es el propio lector no se distingue de su derecho implicito: se rechaza en la lectura.',
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
