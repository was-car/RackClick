"""Pruebas del comprobador de lectura L2l02. No toca servicios, cuentas ni la VM.

- Verificador: arbol sintetico con el mismo layout, ZIP valido y negativos sobre copias modificadas. Incluye la 01 entregada,
  que conserva sus tres verbos, y la 02, que anade selftest-privilege.
- Script y sonda: analisis estatico (sin credenciales, verbo unico 'read', confirmacion y host antes de la sonda, recibos
  CreateNew, aislamiento del hijo antes de Start, llamada nativa con ReturnLength, verbo desconocido sin eco).
- Focos de Codex (evidence/s1-20261027/mfa-l2l01-codex): aislamiento del hijo sobre el script actual. No inician procesos.
- Host: Check solo se prueba en LEAO, donde debe rechazar con host_excluded antes de leer nada.
- Selftests de la sonda (fixtures propios, sin servicio real): solo con RACKCLICK_RUN_PROBE_SELFTEST=1 y
  RACKCLICK_L2L_PACKAGE apuntando a un paquete extraido.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'package_mfa_service_read_trial', ROOT / 'tools' / 'package_mfa_service_read_trial.py')
pkg = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pkg)
TRIAL = ROOT / 'tools' / 'windows' / 'mfa-service-read-trial'
SCRIPT = TRIAL / 'Invoke-MfaServiceReadTrial.ps1'
PROBE_DIR = ROOT / 'tools' / 'mfa-service-read-probe'
FOCUS_DIR = ROOT / 'evidence' / 's1-20261027' / 'mfa-l2l01-codex'
PS = shutil.which('powershell.exe')
PKG = pkg.PACKAGE
PKG_01 = PKG.replace('L2l02', 'L2l01')
DLL = 'probe/RackClick.MfaServiceReadProbe.dll'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def base_files(edition=PKG[-2:]):
    """Contenido minimo de cada archivo requerido; el verificador solo exige nombres, hashes y manifiesto."""
    return {
        pkg.LEEME_BY_EDITION[edition]: b'leeme sintetico\n',
        'Invoke-MfaServiceReadTrial.ps1': b'# sintetico\n',
        'runtime/dotnet.exe': b'MZ-sintetico',
        'runtime/LICENSE.txt': b'license',
        'runtime/ThirdPartyNotices.txt': b'notices',
        DLL: b'probe-sintetico',
        'probe/RackClick.MfaServiceReadProbe.runtimeconfig.json': b'{}',
        'probe/RackClick.Server.dll': b'server-sintetico',
        'probe/RackClick.Domain.dll': b'domain-sintetico',
        'probe/Npgsql.dll': b'npgsql-sintetico',
        'probe/Otp.NET.dll': b'otp-sintetico',
        'licenses/Npgsql-LICENSE': b'npgsql-license',
        'licenses/Otp.NET-LICENSE.txt': b'otp-license',
        'licenses/README.txt': b'readme',
    }


def resum(entries):
    """Recalcula SHA256SUMS sobre las entradas actuales, como write_sums; sin esto las copias modificadas quedan con sumas viejas."""
    folder = sorted(entries)[0].split('/', 1)[0]
    lines = []
    for raw, data in sorted(entries.items()):
        rel = raw.split('/', 1)[1]
        if rel != 'SHA256SUMS':
            lines.append(f'{sha(data)}  {rel}')
    entries = dict(entries)
    entries[f'{folder}/SHA256SUMS'] = ('\n'.join(lines) + '\n').encode('ascii')
    return entries


def valid_entries(folder=PKG, manifest_edition=None, reference=pkg.REF03_DLL):
    edition = folder[-2:]
    files = base_files(edition)
    manifest = {
        'internalTrial': True, 'notInstaller': True, 'notMfaActivation': True,
        'package': folder, 'edition': manifest_edition or edition,
        'runtime': {'version': pkg.RUNTIME_VERSION},
        'sdk': {'version': pkg.SDK_VERSION},
        'probe': {'dllSha256': sha(files[DLL]), 'reference03DllSha256': reference,
                  'verbs': pkg.PROBE_VERBS_BY_EDITION[edition]},
        'licenses': [{'path': rel, 'sha256': sha(files[rel])} for rel in pkg.LICENSE_FILES],
    }
    files['BUILD-MANIFEST.json'] = json.dumps(manifest, indent=2).encode('utf-8')
    entries = {f'{folder}/{rel}': data for rel, data in files.items()}
    return resum(entries)


def edit_manifest(entries, folder, edit):
    """Cambia el manifiesto con `edit` y recalcula las sumas, para aislar el fallo del campo editado."""
    key = f'{folder}/BUILD-MANIFEST.json'
    manifest = json.loads(entries[key].decode('utf-8'))
    edit(manifest)
    entries = dict(entries)
    entries[key] = json.dumps(manifest, indent=2).encode('utf-8')
    return resum(entries)


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='l2l02-verificador-'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def problems(self, entries):
        path = self.tmp / 'paquete.zip'
        with zipfile.ZipFile(path, 'x') as archive:
            for raw, data in sorted(entries.items()):
                archive.writestr(raw, data)
        return pkg.verify_zip(path)['problems']

    def test_synthetic_package_verifies(self):
        self.assertEqual(self.problems(valid_entries()), [])

    def test_edition_01_keeps_its_three_verbs(self):
        self.assertEqual(self.problems(valid_entries(folder=PKG_01)), [])

    def test_edition_01_rejects_the_verbs_of_02(self):
        entries = edit_manifest(valid_entries(folder=PKG_01), PKG_01,
                                lambda m: m['probe'].__setitem__('verbs', pkg.PROBE_VERBS_BY_EDITION['02']))
        self.assertIn('manifest_invalid:probe.verbs', self.problems(entries))

    def test_unknown_edition_is_rejected(self):
        unknown = 'RackClick-MFA-Lectura-L2l09'
        entries = {raw.replace(PKG, unknown, 1): data for raw, data in valid_entries().items()}
        self.assertIn('edition_unknown', self.problems(entries))

    def test_edition_02_requires_selftest_privilege(self):
        entries = edit_manifest(valid_entries(), PKG,
                                lambda m: m['probe'].__setitem__('verbs', pkg.PROBE_VERBS_BY_EDITION['01']))
        self.assertIn('manifest_invalid:probe.verbs', self.problems(entries))

    def test_altered_probe_is_a_hash_mismatch(self):
        entries = valid_entries()
        entries[f'{PKG}/{DLL}'] = b'alterado'
        self.assertIn(f'hash_mismatch:{DLL}', self.problems(entries))

    def test_manifest_edition_must_match_the_folder(self):
        self.assertIn('manifest_invalid:edition', self.problems(valid_entries(manifest_edition='01')))

    def test_probe_dll_must_match_the_reference_03(self):
        self.assertIn('manifest_invalid:probe.dll03', self.problems(valid_entries(reference='0' * 64)))

    def test_stale_probe_hash_in_manifest_is_rejected(self):
        entries = valid_entries()
        entries[f'{PKG}/{DLL}'] = b'otro-probe'
        self.assertIn('manifest_invalid:probe.dllSha256', self.problems(resum(entries)))

    def test_extra_unlisted_file_is_rejected(self):
        entries = valid_entries()
        entries[f'{PKG}/probe/extra.txt'] = b'extra'
        self.assertIn('sums_unlisted:probe/extra.txt', self.problems(entries))

    def test_missing_required_file_is_rejected(self):
        entries = valid_entries()
        del entries[f'{PKG}/probe/RackClick.Server.dll']
        self.assertIn('required_missing:probe/RackClick.Server.dll', self.problems(resum(entries)))

    def test_local_directory_is_forbidden(self):
        entries = resum({**valid_entries(), f'{PKG}/.local/nota.txt': b'privado'})
        self.assertIn('forbidden_entry:.local/nota.txt', self.problems(entries))

    def test_binlog_is_forbidden(self):
        entries = resum({**valid_entries(), f'{PKG}/probe/build.binlog': b'binlog'})
        self.assertIn('forbidden_entry:probe/build.binlog', self.problems(entries))

    def test_pgpass_file_is_forbidden(self):
        entries = resum({**valid_entries(), f'{PKG}/probe/clave.pgpass': b'credencial'})
        self.assertIn('forbidden_entry:probe/clave.pgpass', self.problems(entries))

    def test_key_ring_file_is_forbidden(self):
        entries = resum({**valid_entries(), f'{PKG}/probe/ring.json': b'{}'})
        self.assertIn('forbidden_entry:probe/ring.json', self.problems(entries))

    def test_path_traversal_is_rejected(self):
        entries = {**valid_entries(), f'{PKG}/../evil.txt': b'fuera'}
        self.assertIn('zip_unsafe_name', self.problems(entries))


class ScriptStaticTests(unittest.TestCase):
    def setUp(self):
        self.text = SCRIPT.read_text(encoding='utf-8')

    def test_script_is_ascii_without_bom(self):
        raw = SCRIPT.read_bytes()
        self.assertFalse(raw.startswith(b'\xef\xbb\xbf'))
        raw.decode('ascii')

    def test_no_password_or_logon_api(self):
        for token in ('LogonUser', 'Get-Credential', 'ConvertTo-SecureString', '-Credential',
                      'CreateProcessWithLogon', 'pgpass'):
            self.assertNotIn(token, self.text, token)

    def test_only_the_read_verb_is_sent_in_run(self):
        self.assertIn("$ProbeVerbForRun = 'read'", self.text)
        self.assertNotIn('selftest-token', self.text)
        self.assertNotIn('selftest-deny', self.text)
        self.assertNotIn('selftest-privilege', self.text)

    def test_probe_runs_once_after_confirmation_and_before_receipts(self):
        self.assertEqual(self.text.count('Invoke-ReadProbe $root'), 1)
        probe = self.text.index('Invoke-ReadProbe $root')
        self.assertLess(self.text.index('Confirm-LecturaWrite $installationId'), probe)
        self.assertLess(self.text.index('$before = Get-StoreFingerprint'), probe)
        self.assertLess(probe, self.text.index('New-PrivateFile $receipt'))

    def test_lab_host_is_refused_before_any_mode_runs(self):
        dispatch = self.text.rindex('if (Test-LabHostExcluded)')
        self.assertLess(dispatch, self.text.rindex('Invoke-Run'))
        self.assertLess(dispatch, self.text.rindex('Invoke-Check'))

    def test_receipts_are_created_new_and_never_overwritten(self):
        self.assertIn('[IO.FileMode]::CreateNew', self.text)
        self.assertNotIn('Set-Content', self.text)
        self.assertNotIn('Out-File', self.text)

    def test_only_one_prompt_exists_and_it_is_the_confirmation(self):
        self.assertEqual(self.text.count('Read-Host'), 1)

    def test_child_environment_is_isolated_before_start(self):
        body = self.text[self.text.index('function Invoke-ReadProbe'):]
        self.assertIn('Set-ProbeChildEnvironment $psi', body)
        self.assertLess(body.index('Set-ProbeChildEnvironment $psi'), body.index('[Diagnostics.Process]::Start($psi)'))
        self.assertIn("EnvironmentVariables['DOTNET_EnableDiagnostics'] = '0'", self.text)
        for token in ('CORECLR_PROFILER', 'DOTNET_EnableEventPipe', 'DOTNET_EventPipe', 'DOTNET_STARTUP_HOOKS', 'NOTIFICATION'):
            self.assertIn(token, self.text, token)


class ProbeStaticTests(unittest.TestCase):
    def read(self, name):
        return (PROBE_DIR / name).read_text(encoding='utf-8')

    def test_probe_sources_have_no_logon_or_password_apis(self):
        for name in ('Native.cs', 'Measure.cs', 'Program.cs'):
            text = self.read(name)
            for token in ('LogonUser', 'CreateProcessWithLogon', 'SetThreadToken', 'ImpersonateLoggedOnUser',
                          'Get-Credential', 'SecureString', 'pgpass'):
                self.assertNotIn(token, text, f'{name}:{token}')

    def test_key_is_zeroed_after_the_read(self):
        self.assertIn('CryptographicOperations.ZeroMemory', self.read('Measure.cs'))

    def test_enable_call_always_gets_a_return_length(self):
        calls = [line for line in self.read('Measure.cs').splitlines() if 'AdjustTokenPrivileges(_token, false, request' in line]
        self.assertEqual(len(calls), 1)
        self.assertIn('_returnLength', calls[0])
        self.assertNotIn('IntPtr.Zero);', calls[0])

    def test_privilege_change_is_decided_by_privilege_count_before_reading_attributes(self):
        text = self.read('Measure.cs')
        self.assertLess(text.index('Marshal.ReadInt32(_previous, 0) == 1'), text.index('Marshal.ReadInt32(_previous, 12)'))

    def test_unknown_verb_is_never_echoed(self):
        text = self.read('Program.cs')
        self.assertIn('is "read" or "selftest-token" or "selftest-deny" or "selftest-privilege"', text)
        self.assertIn('"unknown"', text)
        self.assertNotIn('verb = args[0];', text)
        self.assertNotIn('Emit(args[0]', text)

    def test_selftest_privilege_never_touches_debug_privilege(self):
        text = self.read('Program.cs')
        self.assertIn('ExercisePrivilege("SeChangeNotifyPrivilege")', text)
        self.assertIn('ExercisePrivilege("SeShutdownPrivilege")', text)
        self.assertNotIn('ExercisePrivilege("SeDebugPrivilege")', text)


@unittest.skipUnless(PS and (FOCUS_DIR / 'Probe-ChildEnvironment.ps1').is_file(),
                     'sin Windows PowerShell 5.1 o sin el foco de entorno de Codex')
class ChildEnvironmentFocusTest(unittest.TestCase):
    def test_focus_script_on_the_current_script_passes(self):
        with tempfile.TemporaryDirectory(prefix='l2l02-foco-') as fixture:
            out = subprocess.run([PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                                  str(FOCUS_DIR / 'Probe-ChildEnvironment.ps1'),
                                  '-ReferenceScript', str(SCRIPT), '-FixtureBase', fixture],
                                 capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        results = json.loads(out.stdout)
        self.assertTrue(all(item['passed'] for item in results), out.stdout)
        self.assertFalse(any(item.get('processStarted') for item in results), out.stdout)


@unittest.skipUnless(PS, 'sin Windows PowerShell 5.1')
class ScriptSelfTest(unittest.TestCase):
    def test_selftest_passes_on_windows_powershell(self):
        out = subprocess.run([PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(SCRIPT), '-Mode', 'SelfTest'],
                             capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('selftest_passed', out.stdout)


@unittest.skipUnless(PS and os.environ.get('COMPUTERNAME', '').upper() == 'LEAO', 'la negativa de host solo se prueba en LEAO')
class LabHostRefusalTest(unittest.TestCase):
    def test_check_is_refused_on_the_lab_host(self):
        out = subprocess.run([PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(SCRIPT), '-Mode', 'Check',
                              '-ServiceName', 'RackClick-Inexistente-L2l', '-ExpectedSumsSha256', '0' * 64],
                             capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('"code":"host_excluded"', out.stdout + out.stderr)


PROBE_PACKAGE = os.environ.get('RACKCLICK_L2L_PACKAGE', '')


@unittest.skipUnless(os.environ.get('RACKCLICK_RUN_PROBE_SELFTEST') == '1' and PROBE_PACKAGE and PS,
                     'selftests de la sonda solo con RACKCLICK_RUN_PROBE_SELFTEST=1 y RACKCLICK_L2L_PACKAGE')
class ProbeSelfTests(unittest.TestCase):
    def run_probe(self, *args):
        dotnet = Path(PROBE_PACKAGE) / 'runtime' / 'dotnet.exe'
        dll = Path(PROBE_PACKAGE) / DLL.replace('/', os.sep)
        return subprocess.run([str(dotnet), str(dll), *args], capture_output=True, text=True, timeout=120)

    def payload(self, out):
        return json.loads(out.stdout.strip())

    def test_impersonation_selftest_passes(self):
        out = self.run_probe('selftest-token')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('"status":"passed"', out.stdout)

    def test_deny_fixture_passes(self):
        out = self.run_probe('selftest-deny', '--variant', 'deny')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('"status":"passed"', out.stdout)

    def test_allow_fixture_is_detected_as_write_access(self):
        out = self.run_probe('selftest-deny', '--variant', 'allow')
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('unexpected_write_access', out.stdout)

    def test_privilege_selftest_passes_without_debug_privilege(self):
        out = self.run_probe('selftest-privilege')
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        data = self.payload(out)
        self.assertEqual(data['status'], 'passed')
        self.assertTrue(data['unchangedWhenEnabled'])
        self.assertTrue(data['changedAndRestoredExactly'])
        self.assertFalse(data['SeDebugUsed'])

    def test_unknown_verb_is_recorded_as_unknown_and_not_echoed(self):
        out = self.run_probe('RUTA-CANARIO-L2L02-NO-EJECUTADA')
        self.assertEqual(out.returncode, 2)
        self.assertNotIn('RUTA-CANARIO', out.stdout)
        self.assertEqual(self.payload(out)['verb'], 'unknown')

    def test_missing_store_root_is_reported_without_reading(self):
        out = self.run_probe('read', '--instances-root', str(Path(PROBE_PACKAGE) / 'no-existe'),
                             '--installation-id', '00000000-0000-0000-0000-000000000000', '--service', 'RackClick')
        self.assertIn('store_root_missing', out.stdout)


if __name__ == '__main__':
    unittest.main()
