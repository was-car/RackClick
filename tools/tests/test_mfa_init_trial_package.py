"""Pruebas del empaquetador y del ensayo MFA-INIT (L2k). No compilan el servidor ni ejecutan el ensayo.

- Paquete: ensambla un arbol sintetico (runtime, servidor y scripts) con assemble_package, verifica el ZIP y sus negativos.
- Script: analisis estatico de Invoke-MfaInitTrial.ps1 y del lanzador; analisis sintactico y SelfTest con Windows PowerShell 5.1.
  SelfTest no toca el sistema; la prueba de LEAO solo corre en ese equipo.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('package_mfa_init_trial', ROOT / 'tools' / 'package_mfa_init_trial.py')
pkg = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pkg)
TRIAL = ROOT / 'tools' / 'windows' / 'mfa-trial'
SCRIPT = TRIAL / 'Invoke-MfaInitTrial.ps1'
LAUNCHER = TRIAL / 'INICIAR-ENSAYO-MFA.cmd'
PS = shutil.which('powershell.exe')
RUNTIME = pkg.RUNTIME_VERSION
PKG = pkg.PACKAGE


def make_runtime(root):
    files = {
        'dotnet.exe': b'MZ-synthetic-dotnet',
        'LICENSE.txt': b'license',
        'ThirdPartyNotices.txt': b'notices',
        f'host/fxr/{RUNTIME}/hostfxr.dll': b'fxr',
        f'shared/Microsoft.NETCore.App/{RUNTIME}/hostpolicy.dll': b'policy',
        f'shared/Microsoft.NETCore.App/{RUNTIME}/System.Private.CoreLib.dll': b'corelib',
        f'shared/Microsoft.AspNetCore.App/{RUNTIME}/Microsoft.AspNetCore.dll': b'aspnet',
    }
    for rel, data in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def make_published(root):
    root.mkdir(parents=True)
    (root / 'RackClick.Server.dll').write_bytes(b'synthetic-dll')
    config = {'runtimeOptions': {'tfm': 'net10.0',
                                 'framework': {'name': 'Microsoft.NETCore.App', 'version': '10.0.0'},
                                 'frameworks': [{'name': 'Microsoft.AspNetCore.App', 'version': '10.0.0'}]}}
    (root / 'RackClick.Server.runtimeconfig.json').write_text(json.dumps(config), encoding='ascii')
    (root / 'RackClick.Server.deps.json').write_text('{}', encoding='ascii')
    (root / 'database').mkdir()
    (root / 'database' / '001-foundation.sql').write_text('-- synthetic', encoding='ascii')


def make_scripts(root):
    root.mkdir(parents=True)
    for name in pkg.TRIAL_FILES:
        (root / name).write_bytes(('synthetic ' + name + '\n').encode('ascii'))


def sdk_info():
    return {'version': pkg.SDK_VERSION, 'root': '.local/dotnet-10.0.401', 'dotnetExeSha256': '0' * 64,
            'pin': {'id': 'dotnet', 'version': pkg.SDK_VERSION, 'hashAlgorithm': 'SHA512', 'hash': '1' * 128},
            'globalJsonInSnapshot': False, 'versionCheckInSnapshot': pkg.SDK_VERSION}


def make_notices(root):
    """Avisos sinteticos con la misma forma que load_notice_pins; los pins se calculan de estos bytes."""
    root.mkdir(parents=True, exist_ok=True)
    notices = []
    for target, body in (('licenses/Npgsql-LICENSE', b'synthetic npgsql license\n'),
                         ('licenses/Otp.NET-LICENSE.txt', b'synthetic otp license\n')):
        source = root / Path(target).name
        source.write_bytes(body)
        notices.append({'target': target, 'source': source, 'bytes': len(body),
                        'sha256': hashlib.sha256(body).hexdigest(), 'pinKey': 'synthetic',
                        'commit': 'c' * 40, 'url': 'https://example.invalid/synthetic'})
    return notices


def assemble(tmp, scripts_root=None):
    run = tmp / 'run'
    run.mkdir(exist_ok=True)
    published = tmp / 'published'
    make_published(published)
    runtime = tmp / 'runtime-src'
    make_runtime(runtime)
    if scripts_root is None:
        scripts_root = tmp / 'scripts'
        make_scripts(scripts_root)
    sources = [{'path': 'src/RackClick.Server/Program.cs', 'sha256': '2' * 64, 'bytes': 10}]
    git = {'head': 'a' * 40, 'workingTreeDirtyPaths': []}
    commands = ['dotnet restore src/RackClick.Server/RackClick.Server.csproj --locked-mode',
                'dotnet publish src/RackClick.Server/RackClick.Server.csproj -c Release --no-restore']
    return pkg.assemble_package(run, published, source_entries=sources, git=git, sdk=sdk_info(),
                                command_summary=commands, runtime_root=runtime, scripts_root=scripts_root,
                                notices=make_notices(tmp / 'notices'))


def read_entries(zip_path):
    with zipfile.ZipFile(zip_path) as archive:
        return [(info.filename, archive.read(info), info.external_attr) for info in archive.infolist()]


def write_entries(out, entries):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data, attr in entries:
                info = zipfile.ZipInfo(name, date_time=pkg.ZIP_DATE)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = attr
                archive.writestr(info, data)


def mutate(entries, *, replace=None, drop=(), add=()):
    result = []
    for name, data, attr in entries:
        if name in drop:
            continue
        if replace and name in replace:
            data = replace[name]
        result.append((name, data, attr))
    result.extend(add)
    return result


FILE_ATTR = (0o100644 & 0xFFFF) << 16


class PackageRoundTripTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rackclick-mfa-l2k-'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_synthetic_package_verifies_and_contains_the_expected_layout(self):
        zip_path, report = assemble(self.tmp)
        self.assertTrue(report['ok'], report)
        self.assertEqual(report['problems'], [])
        names = {name for name, _, _ in read_entries(zip_path)}
        for expected in (f'{PKG}/runtime/dotnet.exe', f'{PKG}/servidor/RackClick.Server.dll',
                         f'{PKG}/servidor/database/001-foundation.sql', f'{PKG}/SHA256SUMS',
                         f'{PKG}/BUILD-MANIFEST.json', f'{PKG}/INICIAR-ENSAYO-MFA.cmd'):
            self.assertIn(expected, names)

    def test_real_trial_scripts_are_packaged_and_verify(self):
        zip_path, report = assemble(self.tmp, scripts_root=TRIAL)
        self.assertTrue(report['ok'], report)

    def test_packager_never_reuses_an_existing_run_directory(self):
        assemble(self.tmp)
        with self.assertRaises(FileExistsError):
            assemble(self.tmp)

    def test_global_json_is_not_part_of_the_source_snapshot(self):
        self.assertNotIn('global.json', pkg.SOURCE_FILES)
        self.assertFalse(any(tree.endswith('development/server') for tree in pkg.SOURCE_TREES))


class PackageNegativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rackclick-mfa-l2k-neg-'))
        self.zip_path, _ = assemble(self.tmp)
        self.entries = read_entries(self.zip_path)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def verify_mutated(self, entries, name='mutated.zip'):
        out = self.tmp / name
        write_entries(out, entries)
        return pkg.verify_zip(out)

    def assertProblem(self, report, prefix):
        self.assertFalse(report['ok'])
        self.assertTrue(any(p.startswith(prefix) for p in report['problems']), report['problems'])

    def test_altered_file_is_a_hash_mismatch(self):
        report = self.verify_mutated(mutate(self.entries, replace={f'{PKG}/runtime/LICENSE.txt': b'changed'}))
        self.assertProblem(report, f'hash_mismatch:runtime/LICENSE.txt')

    def test_extra_unlisted_file_is_rejected(self):
        report = self.verify_mutated(mutate(self.entries, add=[(f'{PKG}/extra.txt', b'x', FILE_ATTR)]))
        self.assertProblem(report, 'sums_unlisted:extra.txt')

    def test_missing_listed_file_is_rejected(self):
        report = self.verify_mutated(mutate(self.entries, drop={f'{PKG}/runtime/LICENSE.txt'}))
        self.assertProblem(report, 'sums_missing_file:runtime/LICENSE.txt')
        self.assertProblem(report, 'required_missing:runtime/LICENSE.txt')

    def test_local_directory_is_forbidden(self):
        report = self.verify_mutated(mutate(self.entries, add=[(f'{PKG}/.local/notas.txt', b'x', FILE_ATTR)]))
        self.assertProblem(report, 'forbidden_entry:.local/notas.txt')

    def test_binlog_is_forbidden(self):
        report = self.verify_mutated(mutate(self.entries, add=[(f'{PKG}/servidor/build.binlog', b'x', FILE_ATTR)]))
        self.assertProblem(report, 'forbidden_entry:servidor/build.binlog')

    def test_key_ring_file_is_forbidden(self):
        report = self.verify_mutated(mutate(self.entries, add=[(f'{PKG}/servidor/mfa-keys/ring.json', b'x', FILE_ATTR)]))
        self.assertProblem(report, 'forbidden_entry:servidor/mfa-keys/ring.json')

    def test_pgpass_file_is_forbidden(self):
        report = self.verify_mutated(mutate(self.entries, add=[(f'{PKG}/servidor/pgpass.conf', b'x', FILE_ATTR)]))
        self.assertProblem(report, 'forbidden_entry:servidor/pgpass.conf')

    def test_path_traversal_is_rejected(self):
        report = self.verify_mutated(mutate(self.entries, add=[(f'{PKG}/../escape.txt', b'x', FILE_ATTR)]))
        self.assertProblem(report, 'zip_unsafe_name')

    def test_duplicate_entry_is_rejected(self):
        report = self.verify_mutated(mutate(self.entries, add=[(f'{PKG}/runtime/LICENSE.txt', b'license', FILE_ATTR)]))
        self.assertProblem(report, 'zip_duplicate_entry')

    def test_symlink_entry_is_rejected(self):
        link_attr = (0o120777 & 0xFFFF) << 16
        report = self.verify_mutated(mutate(self.entries, add=[(f'{PKG}/servidor/enlace', b'target', link_attr)]))
        self.assertProblem(report, 'zip_symlink')

    def test_non_ascii_script_is_rejected(self):
        report = self.verify_mutated(mutate(self.entries, replace={f'{PKG}/Invoke-MfaInitTrial.ps1': 'eñe\n'.encode('utf-8')}))
        self.assertProblem(report, 'non_ascii_script:Invoke-MfaInitTrial.ps1')

    def test_manifest_must_declare_an_internal_trial_and_not_an_installer(self):
        manifest = json.loads(dict((n, d) for n, d, _ in self.entries)[f'{PKG}/BUILD-MANIFEST.json'])
        manifest['internalTrial'] = False
        report = self.verify_mutated(mutate(self.entries, replace={
            f'{PKG}/BUILD-MANIFEST.json': json.dumps(manifest).encode('ascii')}))
        self.assertProblem(report, 'manifest_invalid:internalTrial')

    def test_manifest_runtime_version_must_match_the_pin(self):
        manifest = json.loads(dict((n, d) for n, d, _ in self.entries)[f'{PKG}/BUILD-MANIFEST.json'])
        manifest['runtime']['version'] = '10.0.0'
        report = self.verify_mutated(mutate(self.entries, replace={
            f'{PKG}/BUILD-MANIFEST.json': json.dumps(manifest).encode('ascii')}))
        self.assertProblem(report, 'manifest_invalid:runtime.version')

    def test_server_must_declare_both_shared_frameworks(self):
        config = {'runtimeOptions': {'framework': {'name': 'Microsoft.NETCore.App', 'version': '10.0.0'}}}
        report = self.verify_mutated(mutate(self.entries, replace={
            f'{PKG}/servidor/RackClick.Server.runtimeconfig.json': json.dumps(config).encode('ascii')}))
        self.assertProblem(report, 'runtimeconfig_frameworks_invalid')

    def test_missing_sums_file_is_rejected(self):
        report = self.verify_mutated(mutate(self.entries, drop={f'{PKG}/SHA256SUMS'}))
        self.assertProblem(report, 'sums_missing')

    def test_malformed_sums_line_is_rejected(self):
        report = self.verify_mutated(mutate(self.entries, replace={f'{PKG}/SHA256SUMS': b'no-es-una-linea\n'}))
        self.assertProblem(report, 'sums_malformed')


# Ejecuta Invoke-Run con la confirmacion rechazada y el resto simulado; el directorio base debe quedar vacio.
CONFIRM_RUNNER_PS = r'''
param([string]$Harness, [string]$Base)
. $Harness
$ExpectedSumsSha256 = 'a' * 64
$BaseDirectory = $Base
function Read-WhoamiGroups { @() }
function Test-ElevationRows { $true }
function Test-PackageIntegrity { @{ sumsSha256 = ('a' * 64); fileCount = 1 } }
function Get-TrialServiceCandidates { @([pscustomobject]@{ Name = 'RackClick_SYNTHETIC'; StartName = '.\Synthetic'; State = 'Stopped' }) }
function Resolve-ServiceAccountSid { 'S-1-5-19' }
function Confirm-TrialWrite { Stop-Trial 'confirmation_mismatch' }
# Cuenta cada intento de guardar y escribe de verdad: el resultado no depende de poder asignar el propietario Administradores.
$script:attempts = 0
function New-PrivateFile { param($Path, $Text, $OwnerSid) $script:attempts++; [IO.File]::WriteAllText($Path, $Text) }
$tk = $null; $er = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($Harness, [ref]$tk, [ref]$er)
$fn = $ast.FindAll({ param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Invoke-Run' }, $true)[0].Extent.Text
$fn = $fn.Replace("if ([Console]::IsInputRedirected) { Stop-Trial 'console_required' }", '')
. ([scriptblock]::Create($fn))
$code = ''
try { Invoke-Run } catch { $code = Get-TrialCodeFromError $_ }
Write-Output ('CODE=' + $code + ' ATTEMPTS=' + $script:attempts + ' ENTRIES=' + @(Get-ChildItem -LiteralPath $Base -Force).Count)
'''


class NoticeNegativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rackclick-mfa-l2k-notice-neg-'))
        self.zip_path, _ = assemble(self.tmp)
        self.entries = read_entries(self.zip_path)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def verify_mutated(self, entries):
        out = self.tmp / 'mutated.zip'
        write_entries(out, entries)
        return pkg.verify_zip(out)

    def test_absent_otp_notice_is_rejected(self):
        report = self.verify_mutated(mutate(self.entries, drop={f'{PKG}/licenses/Otp.NET-LICENSE.txt'}))
        self.assertIn('required_missing:licenses/Otp.NET-LICENSE.txt', report['problems'])

    def test_altered_npgsql_notice_is_rejected_against_its_pin_in_the_manifest(self):
        report = self.verify_mutated(mutate(self.entries, replace={f'{PKG}/licenses/Npgsql-LICENSE': b'cambiado'}))
        self.assertIn('hash_mismatch:licenses/Npgsql-LICENSE', report['problems'])
        self.assertIn('notice_manifest_mismatch:licenses/Npgsql-LICENSE', report['problems'])

    def test_manifest_notice_hash_must_match_the_shipped_file(self):
        manifest = json.loads(dict((n, d) for n, d, _ in self.entries)[f'{PKG}/BUILD-MANIFEST.json'])
        manifest['licenses'][1]['sha256'] = '0' * 64
        report = self.verify_mutated(mutate(self.entries, replace={
            f'{PKG}/BUILD-MANIFEST.json': json.dumps(manifest).encode('ascii')}))
        self.assertIn('notice_manifest_mismatch:licenses/Otp.NET-LICENSE.txt', report['problems'])

    def test_manifest_edition_and_package_must_match_the_folder(self):
        manifest = json.loads(dict((n, d) for n, d, _ in self.entries)[f'{PKG}/BUILD-MANIFEST.json'])
        manifest['edition'] = '02'
        report = self.verify_mutated(mutate(self.entries, replace={
            f'{PKG}/BUILD-MANIFEST.json': json.dumps(manifest).encode('ascii')}))
        self.assertIn('manifest_invalid:edition', report['problems'])

    def test_edition_01_layout_without_notices_fails_verification(self):
        legacy = []
        for name, data, attr in self.entries:
            if '/licenses/' in name:
                continue
            legacy.append((name.replace(f'{PKG}/', 'RackClick-MFA-Ensayo-01/'), data, attr))
        report = self.verify_mutated(legacy)
        self.assertFalse(report['ok'])
        self.assertIn('required_missing:licenses/Npgsql-LICENSE', report['problems'])
        self.assertIn('sums_missing_file:licenses/Npgsql-LICENSE', report['problems'])


class NoticePinTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rackclick-mfa-l2k-pins-'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_pins(self, npgsql_sha, otp_sha, npgsql_path, otp_path, npgsql_bytes, otp_bytes):
        data = {'npgsqlLicenseSha256': npgsql_sha, 'otpNetLicenseSha256': otp_sha,
                'npgsqlSourceCommit': 'c' * 40, 'otpNetSourceCommit': 'd' * 40,
                'sources': [
                    {'name': 'Npgsql-LICENSE', 'path': str(npgsql_path), 'bytes': npgsql_bytes, 'sha256': npgsql_sha},
                    {'name': 'Otp.NET-LICENSE', 'path': str(otp_path), 'bytes': otp_bytes, 'sha256': otp_sha}]}
        path = self.tmp / 'pins.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def test_real_pins_load_when_the_local_sources_exist(self):
        notices = pkg.load_notice_pins()
        self.assertEqual([n['target'] for n in notices],
                         ['licenses/Npgsql-LICENSE', 'licenses/Otp.NET-LICENSE.txt'])
        for notice in notices:
            self.assertEqual(len(notice['sha256']), 64)
            self.assertEqual(pkg.sha256_file(notice['source']), notice['sha256'])

    def test_pin_that_disagrees_with_the_sources_block_is_rejected(self):
        body = b'synthetic'
        source = self.tmp / 'npgsql'
        source.write_bytes(body)
        otp = self.tmp / 'otp'
        otp.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()
        path = self.write_pins(sha, sha, source, otp, len(body), len(body))
        data = json.loads(path.read_text(encoding='utf-8'))
        data['npgsqlLicenseSha256'] = 'f' * 64
        path.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaises(pkg.PackageError) as ctx:
            pkg.load_notice_pins(path)
        self.assertEqual(ctx.exception.code, 'notice_pin_inconsistent')

    def test_altered_local_source_is_rejected(self):
        body = b'synthetic-original'
        source = self.tmp / 'npgsql'
        source.write_bytes(body)
        otp = self.tmp / 'otp'
        otp.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()
        path = self.write_pins(sha, sha, source, otp, len(body), len(body))
        source.write_bytes(b'altered-content!!')
        with self.assertRaises(pkg.PackageError) as ctx:
            pkg.load_notice_pins(path)
        self.assertEqual(ctx.exception.code, 'notice_source_mismatch')

    def test_missing_local_source_is_rejected(self):
        body = b'synthetic'
        otp = self.tmp / 'otp'
        otp.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()
        path = self.write_pins(sha, sha, self.tmp / 'no-existe', otp, len(body), len(body))
        with self.assertRaises(pkg.PackageError) as ctx:
            pkg.load_notice_pins(path)
        self.assertEqual(ctx.exception.code, 'notice_source_mismatch')


class BuildHygieneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rackclick-mfa-l2k-hygiene-'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_binlogs_stay_outside_the_package_and_are_identified_in_the_manifest(self):
        binlog_dir = self.tmp / 'run' / 'binlogs'
        binlog_dir.mkdir(parents=True)
        (binlog_dir / 'publish.binlog').write_bytes(b'private-binlog')
        zip_path, _ = assemble(self.tmp)
        names = [name for name, _, _ in read_entries(zip_path)]
        self.assertFalse([n for n in names if 'binlog' in n.lower()])
        manifest = json.loads(dict((n, d) for n, d, _ in read_entries(zip_path))[f'{PKG}/BUILD-MANIFEST.json'])
        self.assertEqual(manifest['publication']['binlogSha256'],
                         {'publish.binlog': hashlib.sha256(b'private-binlog').hexdigest()})

    def test_sdk_environment_drops_profilers_and_keeps_profile_directories(self):
        saved = dict(os.environ)
        try:
            os.environ['CORECLR_PROFILER'] = '{11111111-1111-1111-1111-111111111111}'
            os.environ['CORECLR_PROFILER_PATH'] = 'C:\\SYNTHETIC\\profiler.dll'
            os.environ['DOTNET_PerfMapEnabled'] = '1'
            os.environ['DOTNET_EnableEventPipe'] = '1'
            os.environ['DOTNET_STARTUP_HOOKS'] = 'synthetic-hook'
            env = pkg.sdk_env()
        finally:
            os.environ.clear()
            os.environ.update(saved)
        for name in ('CORECLR_PROFILER', 'CORECLR_PROFILER_PATH', 'DOTNET_PerfMapEnabled',
                     'DOTNET_EnableEventPipe', 'DOTNET_STARTUP_HOOKS'):
            with self.subTest(name=name):
                self.assertNotIn(name, env)
        self.assertEqual(env['DOTNET_EnableDiagnostics'], '0')
        self.assertEqual(env['CORECLR_ENABLE_PROFILING'], '0')
        if 'USERPROFILE' in saved:
            self.assertIn('USERPROFILE', env)


class TrialScriptStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding='utf-8')
        cls.launcher = LAUNCHER.read_text(encoding='ascii')

    def test_script_and_launcher_are_ascii(self):
        self.assertTrue(all(byte < 128 for byte in SCRIPT.read_bytes()))
        self.assertTrue(all(byte < 128 for byte in LAUNCHER.read_bytes()))

    def test_no_service_account_or_file_mutation_commands(self):
        for token in ('New-Service', 'Set-Service', 'Start-Service', 'Stop-Service', 'Remove-Service', 'sc.exe',
                      'New-LocalUser', 'Set-LocalUser', 'Remove-LocalUser', 'net user', 'Remove-Item',
                      'Restart-Service', 'Invoke-Expression', 'Set-Acl', 'Set-TrialRootAcl'):
            with self.subTest(token=token):
                self.assertNotIn(token, self.source)

    def test_no_server_mode_other_than_mfa_keys_init_and_no_mfa_enablement(self):
        for token in ('--migrate', '--bootstrap', '--recover-admin', 'MfaKeyStore:Enabled', 'ConnectionStrings'):
            with self.subTest(token=token):
                self.assertNotIn(token, self.source)

    def test_leao_guard_runs_before_any_check_or_run(self):
        guard = self.source.index("if (Test-LabHostExcluded) { Stop-Trial 'host_excluded' }")
        dispatch = self.source.index("if ($Mode -eq 'Run') { Invoke-Run } else { Invoke-Check }")
        self.assertLess(guard, dispatch)

    def test_run_checks_console_elevation_and_expected_sums_before_writing(self):
        run_body = self.source[self.source.index('function Invoke-Run'):self.source.index('function Invoke-SelfTest')]
        first_write = run_body.index('New-TrialRootFolder $trialRoot')
        for guard in ("'expected_sums_required'", "'console_required'", "'not_elevated'", 'Confirm-TrialWrite $uuid'):
            with self.subTest(guard=guard):
                self.assertLess(run_body.index(guard), first_write)

    def test_run_invokes_the_server_exactly_twice(self):
        run_body = self.source[self.source.index('function Invoke-Run'):self.source.index('function Invoke-SelfTest')]
        self.assertEqual(run_body.count('= Invoke-MfaKeysInit $root'), 2)

    def test_selftest_never_touches_the_system(self):
        selftest = self.source[self.source.index('function Invoke-SelfTest'):self.source.index('try {\n    if ($Mode')]
        for token in ('Get-CimInstance', 'whoami', 'Get-Acl', 'New-Item', 'Invoke-MfaKeysInit', 'Read-WhoamiGroups',
                      'Read-Host', 'Set-Acl'):
            with self.subTest(token=token):
                self.assertNotIn(token, selftest)

    def test_confirmation_is_checked_before_the_trial_record_and_any_artifact(self):
        run_body = self.source[self.source.index('function Invoke-Run'):self.source.index('function Invoke-SelfTest')]
        confirm = run_body.index('Confirm-TrialWrite $uuid')
        self.assertLess(confirm, run_body.index('$trial = [ordered]@{'))
        self.assertLess(confirm, run_body.index('try {'))
        self.assertLess(run_body.index('try {'), run_body.index('Save-TrialArtifacts $trial'))

    def test_root_folder_creation_is_exclusive_and_uses_the_native_descriptor_api(self):
        self.assertIn('CreateDirectoryW', self.source)
        self.assertIn('CreateExclusive', self.source)
        self.assertIn("'trial_folder_exists'", self.source)
        self.assertNotIn('.Create($acl)', self.source)

    def test_launcher_defaults_to_check_and_requires_run_for_writing(self):
        self.assertIn('set "TRIAL_MODE=Check"', self.launcher)
        self.assertIn('if /i not "%~1"=="run" goto no_run', self.launcher)
        self.assertIn('Invoke-MfaInitTrial.ps1', self.launcher)


@unittest.skipUnless(os.name == 'nt' and PS, 'requiere Windows PowerShell 5.1')
class TrialIntegrityWindowsTests(unittest.TestCase):
    """Test-PackageIntegrity del script contra un paquete sintetico extraido. Solo lee archivos del directorio temporal."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rackclick-mfa-l2k-integrity-'))
        (self.tmp / 'built').mkdir()
        zip_path, _ = assemble(self.tmp / 'built')
        self.extracted = self.tmp / 'extracted'
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(self.extracted)
        self.root = self.extracted / PKG
        self.sums = pkg.sha256_file(self.root / 'SHA256SUMS')
        text = SCRIPT.read_text(encoding='utf-8')
        cut = text.index('\ntry {\n    if ($Mode')
        self.harness = self.tmp / 'harness.ps1'
        self.harness.write_text(text[:cut], encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def integrity(self, root, sums):
        command = (f". '{self.harness}'; try {{ $r = Test-PackageIntegrity -Root '{root}' -ExpectedSums '{sums}'; "
                   "Write-Output ('OK ' + $r.fileCount) } catch { Write-Output ('CODE=' + ($_.Exception.Message -replace '^trial:', '')) }")
        proc = subprocess.run([PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', command],
                              capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
        return proc.stdout.strip()

    def test_valid_package_passes_and_counts_files_without_sums(self):
        self.assertEqual(self.integrity(self.root, self.sums), f'OK {self.count_files()}')

    def count_files(self):
        return sum(1 for p in self.root.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')

    def test_wrong_expected_sums_is_rejected(self):
        self.assertEqual(self.integrity(self.root, '0' * 64), 'CODE=package_sums_mismatch')

    def test_altered_file_is_rejected(self):
        (self.root / 'runtime' / 'LICENSE.txt').write_bytes(b'changed')
        self.assertEqual(self.integrity(self.root, self.sums), 'CODE=package_hash_mismatch')

    def test_extra_file_is_rejected(self):
        (self.root / 'extra.txt').write_bytes(b'x')
        self.assertEqual(self.integrity(self.root, self.sums), 'CODE=package_file_unlisted')

    def test_missing_listed_file_is_rejected(self):
        (self.root / 'servidor' / 'RackClick.Server.dll').unlink()
        self.assertEqual(self.integrity(self.root, self.sums), 'CODE=package_file_missing')


@unittest.skipUnless(os.name == 'nt' and PS, 'requiere Windows PowerShell 5.1')
class TrialScriptWindowsTests(unittest.TestCase):
    def run_ps(self, *args):
        return subprocess.run([PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(SCRIPT), *args],
                              capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)

    def test_parses_with_windows_powershell(self):
        script = ("$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile("
                  f"'{SCRIPT}',[ref]$t,[ref]$e);'ERRORS='+@($e).Count")
        proc = subprocess.run([PS, '-NoProfile', '-Command', script], capture_output=True, text=True, timeout=120)
        self.assertIn('ERRORS=0', proc.stdout)

    def test_selftest_passes_without_touching_the_system(self):
        proc = self.run_ps('-Mode', 'SelfTest')
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('selftest_passed', proc.stdout)

    @unittest.skipUnless(os.environ.get('COMPUTERNAME', '').upper() == 'LEAO', 'la exclusion solo se comprueba en LEAO')
    def test_leao_refuses_check_and_run_before_reading(self):
        for mode in ('Check', 'Run'):
            with self.subTest(mode=mode):
                proc = self.run_ps('-Mode', mode, '-ExpectedSumsSha256', 'a' * 64)
                self.assertEqual(proc.returncode, 1)
                self.assertIn('"code":"host_excluded"', proc.stdout)


@unittest.skipUnless(os.name == 'nt' and PS, 'requiere Windows PowerShell 5.1')
class TrialScriptRegressionWindowsTests(unittest.TestCase):
    """Regresion de L2K-01, L2K-02 y L2K-04 en Windows PowerShell 5.1. Solo escribe en un directorio temporal propio."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rackclick-mfa-l2k-regression-'))
        text = SCRIPT.read_text(encoding='utf-8')
        cut = text.index('\ntry {\n    if ($Mode')
        self.harness = self.tmp / 'harness.ps1'
        self.harness.write_text(text[:cut], encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ps(self, body):
        command = f". '{self.harness}'; {body}"
        proc = subprocess.run([PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', command],
                              capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
        return proc.stdout.strip(), proc.stderr.strip(), proc.returncode

    def test_private_receipt_is_born_private_and_never_overwritten(self):
        target = self.tmp / 'recibo.json'
        body = (f"$u=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value; "
                f"New-PrivateFile -Path '{target}' -Text '{{}}' -OwnerSid $u; "
                f"$acl=Get-Acl -LiteralPath '{target}'; "
                "$users=@($acl.Access | Where-Object { $_.IdentityReference.Value -eq 'S-1-5-32-545' }).Count; "
                "Write-Output ('PROTECTED=' + $acl.AreAccessRulesProtected + ' USERS=' + $users)")
        out, err, rc = self.ps(body)
        self.assertEqual(rc, 0, err)
        self.assertIn('PROTECTED=True USERS=0', out)
        again = (f"$u=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value; "
                 f"try {{ New-PrivateFile -Path '{target}' -Text 'x' -OwnerSid $u; Write-Output 'OVERWRITTEN' }} "
                 "catch { Write-Output 'REJECTED' }")
        out, _, _ = self.ps(again)
        self.assertIn('REJECTED', out)

    def test_failed_owner_assignment_leaves_no_readable_file(self):
        target = self.tmp / 'sin-propietario.json'
        body = (f"try {{ New-PrivateFile -Path '{target}' -Text 'x' -OwnerSid 'S-1-5-32-544' }} catch {{ }}; "
                f"$exists = Test-Path -LiteralPath '{target}'; "
                "$users = 0; if ($exists) { $users = @((Get-Acl -LiteralPath "
                f"'{target}').Access | Where-Object {{ $_.IdentityReference.Value -eq 'S-1-5-32-545' }}).Count }}; "
                "Write-Output ('EXISTS=' + $exists + ' USERS=' + $users)")
        out, err, rc = self.ps(body)
        self.assertIn('USERS=0', out, err)

    def test_state_digest_changes_when_only_the_root_acl_changes(self):
        a = self.tmp / 'raiz-a'
        b = self.tmp / 'raiz-b'
        body = (f"$u=[Security.Principal.WindowsIdentity]::GetCurrent().User; "
                "$inh=[Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit; "
                "$users=New-Object Security.Principal.SecurityIdentifier('S-1-5-32-545'); "
                "function New-Root([string]$p,[bool]$readUsers) { "
                "$s=New-Object Security.AccessControl.DirectorySecurity; $s.SetAccessRuleProtection($true,$false); $s.SetOwner($u); "
                "$s.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($u,'FullControl',$inh,'None','Allow'))); "
                "if ($readUsers) { $s.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($users,'ReadAndExecute','None','None','Allow'))) }; "
                "(New-Object IO.DirectoryInfo $p).Create($s) }; "
                f"New-Root '{a}' $false; New-Root '{b}' $true; "
                f"foreach ($p in @('{a}','{b}')) {{ [IO.File]::WriteAllText((Join-Path $p 'x.txt'),'same') }}; "
                f"$da = (Get-TrialState '{a}').digest; $db = (Get-TrialState '{b}').digest; "
                "Write-Output ('SAME_DIGEST=' + ($da -eq $db))")
        out, err, rc = self.ps(body)
        self.assertEqual(rc, 0, err)
        self.assertIn('SAME_DIGEST=False', out)

    def test_trial_root_folder_is_born_protected_with_reader_read_only(self):
        root = self.tmp / 'ensayo-raiz'
        body = (f"$u=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value; "
                f"New-TrialRootFolder -Path '{root}' -ReaderSid 'S-1-5-19' -OwnerSid $u; "
                f"$acl=Get-Acl -LiteralPath '{root}'; "
                "$rules=@($acl.GetAccessRules($true,$false,[Security.Principal.SecurityIdentifier]) | "
                "ForEach-Object { $_.IdentityReference.Value + ':' + $_.FileSystemRights }); "
                "Write-Output ('PROTECTED=' + $acl.AreAccessRulesProtected + ' USERS=' + "
                "@($rules | Where-Object { $_ -like 'S-1-5-32-545:*' }).Count + ' READER=' + "
                "@($rules | Where-Object { $_ -like 'S-1-5-19:*' }).Count)")
        out, err, rc = self.ps(body)
        self.assertEqual(rc, 0, err)
        self.assertIn('PROTECTED=True USERS=0 READER=1', out)

    def test_existing_root_is_rejected_and_its_bytes_and_acl_are_preserved(self):
        existing = self.tmp / 'ya-existe'
        body = (f"$u=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value; "
                "$sid=New-Object Security.Principal.SecurityIdentifier($u); "
                "$s=New-Object Security.AccessControl.DirectorySecurity; $s.SetAccessRuleProtection($true,$false); $s.SetOwner($sid); "
                "$s.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow'))); "
                f"(New-Object IO.DirectoryInfo '{existing}').Create($s); "
                f"[IO.File]::WriteAllText((Join-Path '{existing}' 'sentinel.txt'),'foreign'); "
                f"$before=(Get-Acl -LiteralPath '{existing}').Sddl; "
                f"$code=Get-ThrownTrialCode {{ New-TrialRootFolder -Path '{existing}' -ReaderSid 'S-1-5-19' -OwnerSid $u }}; "
                f"$after=(Get-Acl -LiteralPath '{existing}').Sddl; "
                f"Write-Output ('CODE=' + $code + ' SAME_ACL=' + ($before -eq $after) + ' SENTINEL=' + "
                f"[IO.File]::ReadAllText((Join-Path '{existing}' 'sentinel.txt')))")
        out, err, rc = self.ps(body)
        self.assertEqual(rc, 0, err)
        self.assertIn('CODE=trial_folder_exists SAME_ACL=True SENTINEL=foreign', out)

    def test_confirmation_mismatch_writes_nothing(self):
        base = self.tmp / 'base'
        base.mkdir()
        runner = self.tmp / 'confirm-runner.ps1'
        runner.write_text(CONFIRM_RUNNER_PS, encoding='utf-8')
        proc = subprocess.run([PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(runner),
                               '-Harness', str(self.harness), '-Base', str(base)],
                              capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
        self.assertIn('CODE=confirmation_mismatch ATTEMPTS=0 ENTRIES=0', proc.stdout, proc.stderr)

    def test_child_environment_drops_profiler_and_keeps_profile_directories(self):
        body = ("$psi = New-Object Diagnostics.ProcessStartInfo 'cmd.exe'; "
                "$psi.EnvironmentVariables['CORECLR_PROFILER'] = '{x}'; "
                "$psi.EnvironmentVariables['CORECLR_PROFILER_PATH'] = 'C:\\SYNTHETIC\\profiler.dll'; "
                "$psi.EnvironmentVariables['DOTNET_PerfMapEnabled'] = '1'; "
                "$psi.EnvironmentVariables['DOTNET_STARTUP_HOOKS'] = 'synthetic-hook'; "
                "Set-TrialChildEnvironment $psi; $e = $psi.EnvironmentVariables; "
                "Write-Output ('PROFILER=' + $e.ContainsKey('CORECLR_PROFILER') + ' PATH=' + $e.ContainsKey('CORECLR_PROFILER_PATH') + "
                "' PERFMAP=' + $e.ContainsKey('DOTNET_PerfMapEnabled') + ' HOOKS=' + $e.ContainsKey('DOTNET_STARTUP_HOOKS') + "
                "' DIAG=' + $e['DOTNET_EnableDiagnostics'] + ' PROF=' + $e['CORECLR_ENABLE_PROFILING'] + "
                "' USERPROFILE=' + $e.ContainsKey('USERPROFILE'))")
        out, err, rc = self.ps(body)
        self.assertEqual(rc, 0, err)
        self.assertIn('PROFILER=False PATH=False PERFMAP=False HOOKS=False DIAG=0 PROF=0 USERPROFILE=True', out)


if __name__ == '__main__':
    unittest.main()
