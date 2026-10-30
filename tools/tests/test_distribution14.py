"""Pruebas activas de la distribución 14: generador de producción y verificador Test-ServerDistribution.ps1.

Positivo: la candidata generada se verifica con su digest de perfil. Negativos: digest incorrecto, SQL 014 ausente,
apphost extra, archivo modificado, conjunto incompleto, perfil desconocido, salida existente, publicación con extras,
y rutas con junction en la raíz de publicación, en un ancestro del frontend o en el destino.
No modifican las candidatas históricas ni sus evidencias: todo se copia a carpetas temporales privadas bajo .local.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import build_server_distribution as builder  # noqa: E402

PROFILE = ROOT / 'docs' / 'DISTRIBUCION14-PERFIL.json'
PUBLISH = ROOT / '.local' / 'dist14-publish'
FRONTEND = ROOT / 'development' / 'frontend' / 'dist'
CANDIDATE = ROOT / '.local' / 'distribution14' / 'candidata-01'
PINNED = '2ec9105661db0f5c9a97d58e2a7f44e69bfd7e1903493b72f0fc57cc94c4b71a'
POWERSHELL = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'
VERIFIER = ROOT / 'tools' / 'windows' / 'Test-ServerDistribution.ps1'
BASE = '7b4f3e8a9eb9b7278f0347b3cdd473348966e821'
# Mismos argumentos que la candidata revisada: así el manifiesto debe reproducir el digest fijado.
SOURCE_STATUS = 'HEAD 7b4f3e8; arbol de trabajo con cambios sin commit (M3 y distribucion 14)'
TOOLCHAIN = {'dotnet': '10.0.401', 'node': '24.21.0', 'npm': '11.19.0'}
AUXILIARY = ('manifest.json', 'inventory.json', 'SHA256SUMS.txt')


def verify(manifest: Path, pinned: str, server: Path, frontend: Path) -> dict:
    command = [str(POWERSHELL), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(VERIFIER),
               '-ManifestPath', str(manifest), '-ExpectedManifestSha256', pinned, '-ServerPath', str(server), '-FrontendPath', str(frontend)]
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
    return json.loads(result.stdout.strip().splitlines()[-1])


def run_generator(publish: Path, frontend: Path, output: Path) -> tuple[int, dict]:
    """Ejecuta la CLI real, que es la entrada que usa el operador, y devuelve su código y su JSON."""
    argv = ['--profile', str(PROFILE), '--publish', str(publish), '--frontend', str(frontend), '--output', str(output),
            '--base-commit', BASE, '--source-status', 'prueba']
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = builder.main(argv)
    return code, json.loads(buffer.getvalue())


def make_junction(link: Path, target: Path) -> None:
    subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], check=True, capture_output=True)
    if not os.path.isjunction(link):
        raise RuntimeError('junction_fixture_failed')


@unittest.skipUnless(sys.platform == 'win32' and PUBLISH.is_dir() and CANDIDATE.is_dir(), 'requiere la publicación y la candidata de esquema 14 en .local')
class Distribution14Tests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix='rc-dist14-', dir=ROOT / '.local'))
        self.links: list[Path] = []

    def tearDown(self):
        for link in self.links:
            if os.path.isjunction(link):
                os.rmdir(link)  # Quita solo el enlace; nunca recorre su destino.
        shutil.rmtree(self.work, ignore_errors=True)

    def junction(self, link: Path, target: Path) -> None:
        make_junction(link, target)
        self.links.append(link)

    def copy_candidate(self) -> Path:
        target = self.work / 'candidata'
        shutil.copytree(CANDIDATE, target)
        return target

    def test_positive_candidate_verifies_with_profile_digest(self):
        result = verify(CANDIDATE / 'manifest.json', PINNED, CANDIDATE / 'server', CANDIDATE / 'frontend')

        self.assertTrue(result['valid'], result)
        self.assertEqual('artifacts_verified', result['code'])
        self.assertEqual((42, 24, 18), (result['verifiedFiles'], result['serverFiles'], result['frontendFiles']))

    def test_wrong_pinned_digest_is_untrusted(self):
        result = verify(CANDIDATE / 'manifest.json', '0' * 64, CANDIDATE / 'server', CANDIDATE / 'frontend')

        self.assertEqual('manifest_untrusted', result['code'])

    def test_altered_manifest_is_untrusted(self):
        copy = self.copy_candidate()
        manifest = copy / 'manifest.json'
        manifest.write_text(manifest.read_text(encoding='utf-8').replace('"fileCount": 42', '"fileCount": 43'), encoding='utf-8')

        result = verify(manifest, PINNED, copy / 'server', copy / 'frontend')

        self.assertEqual('manifest_untrusted', result['code'])

    def test_missing_sql_014_is_detected(self):
        copy = self.copy_candidate()
        (copy / 'server' / 'database' / '014-mfa.sql').unlink()

        result = verify(CANDIDATE / 'manifest.json', PINNED, copy / 'server', copy / 'frontend')

        self.assertEqual('distribution_files_missing', result['code'])

    def test_apphost_extra_is_rejected(self):
        copy = self.copy_candidate()
        (copy / 'server' / 'RackClick.Server.exe').write_bytes(b'MZ-extra')

        result = verify(CANDIDATE / 'manifest.json', PINNED, copy / 'server', copy / 'frontend')

        self.assertEqual('distribution_files_extra', result['code'])

    def test_modified_application_file_is_detected(self):
        copy = self.copy_candidate()
        target = copy / 'server' / 'RackClick.Server.dll'
        target.write_bytes(target.read_bytes() + b'\x00')

        result = verify(CANDIDATE / 'manifest.json', PINNED, copy / 'server', copy / 'frontend')

        self.assertEqual('artifact_hash_mismatch', result['code'])

    def test_missing_frontend_file_breaks_the_count(self):
        copy = self.copy_candidate()
        (copy / 'frontend' / 'app.css').unlink()

        result = verify(CANDIDATE / 'manifest.json', PINNED, copy / 'server', copy / 'frontend')

        self.assertEqual('distribution_files_missing', result['code'])

    def test_unknown_schema_profile_is_rejected(self):
        copy = self.copy_candidate()
        manifest = copy / 'manifest.json'
        data = json.loads(manifest.read_text(encoding='utf-8'))
        data['schema'] = 15
        manifest.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')
        digest = builder.sha256_file(manifest)

        result = verify(manifest, digest, copy / 'server', copy / 'frontend')

        self.assertEqual('manifest_distribution_unsupported', result['code'])

    def test_generator_refuses_existing_output(self):
        existing = self.work / 'ya-existe'
        existing.mkdir()

        with self.assertRaises(builder.DistributionError) as raised:
            builder.build(PROFILE, PUBLISH, FRONTEND, existing, BASE, TOOLCHAIN, 'prueba')

        self.assertEqual('output_exists', str(raised.exception))

    def test_generator_refuses_publication_with_apphost(self):
        publish = self.work / 'publicacion'
        shutil.copytree(PUBLISH, publish)
        (publish / 'RackClick.Server.exe').write_bytes(b'MZ-extra')

        with self.assertRaises(builder.DistributionError) as raised:
            builder.build(PROFILE, publish, FRONTEND, self.work / 'salida', BASE, TOOLCHAIN, 'prueba')

        self.assertEqual('server_application_extra', str(raised.exception))

    def test_generator_refuses_publication_without_sql_014(self):
        publish = self.work / 'publicacion'
        shutil.copytree(PUBLISH, publish)
        (publish / 'database' / '014-mfa.sql').unlink()

        with self.assertRaises(builder.DistributionError) as raised:
            builder.build(PROFILE, publish, FRONTEND, self.work / 'salida', BASE, TOOLCHAIN, 'prueba')

        self.assertEqual('server_sql_missing', str(raised.exception))

    def test_generator_reproduces_manifest_and_every_auxiliary_file(self):
        first = builder.build(PROFILE, PUBLISH, FRONTEND, self.work / 'uno', BASE, TOOLCHAIN, SOURCE_STATUS)
        second = builder.build(PROFILE, PUBLISH, FRONTEND, self.work / 'dos', BASE, TOOLCHAIN, SOURCE_STATUS)

        self.assertEqual(first['manifestSha256'], PINNED)
        self.assertEqual(second['manifestSha256'], PINNED)
        for name in AUXILIARY:
            with self.subTest(file=name):
                self.assertEqual((Path(first['output']) / name).read_bytes(), (Path(second['output']) / name).read_bytes())

    def test_publication_junction_root_is_rejected_before_output(self):
        real = self.work / 'publicacion-real'
        shutil.copytree(PUBLISH, real)
        link = self.work / 'publicacion-enlace'
        self.junction(link, real)
        output = self.work / 'salida-raiz'

        code, result = run_generator(link, FRONTEND, output)

        self.assertEqual((code, result['code']), (2, 'reparse_path_rejected'))
        self.assertFalse(output.exists())

    def test_frontend_ancestor_junction_is_rejected_before_output(self):
        real = self.work / 'frontal-real'
        shutil.copytree(FRONTEND, real / 'dist')
        link = self.work / 'frontal-enlace'
        self.junction(link, real)
        output = self.work / 'salida-frontal'

        code, result = run_generator(PUBLISH, link / 'dist', output)

        self.assertEqual((code, result['code']), (2, 'reparse_path_rejected'))
        self.assertFalse(output.exists())

    def test_output_under_junction_is_rejected_before_creation(self):
        real = self.work / 'destino-real'
        real.mkdir()
        link = self.work / 'destino-enlace'
        self.junction(link, real)

        code, result = run_generator(PUBLISH, FRONTEND, link / 'salida')

        self.assertEqual((code, result['code']), (2, 'reparse_path_rejected'))
        self.assertFalse((real / 'salida').exists())


if __name__ == '__main__':
    unittest.main()
