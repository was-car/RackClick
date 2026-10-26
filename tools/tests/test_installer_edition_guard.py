"""Negativos de la edicion del instalador: rechazo temprano sin crear ninguna salida.

La edicion se valida antes de leer entradas o crear archivos. Estos casos pasan rutas de entrada que no existen
para demostrar que el rechazo llega antes que cualquier comprobacion de entrada. Cada prueba verifica que la carpeta
de salida queda exactamente igual. No instala nada ni publica nada.
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import package_cambio_ip as cambio  # noqa: E402
import package_clean_server_installer as clean  # noqa: E402
import package_server_installer as installer  # noqa: E402

BUNDLE_07 = '6d5a3896422c308e6b086822aaaa76a5fb6cc2584cf0664666f96504709e14f8'
HISTORICAL_05_BUNDLE = 'a0df90ed3a2864492d8d9bdc2cc2e552113a6b9c81a3e603c1c2920486c26869'
PAYLOAD_JSON_06 = '31a42b3e9c7abfd757dc51ffb5e85abaa3d5b76600e4b66e72092447727417c9'
INVALID_EDITIONS = ['06/../../escape', '..', '', '6', '006', '0a', '06 ', '06\\..', '06/x', '６６', 'AA', '06\n']


class EditionGuardTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix='rc-edition-guard-', dir=ROOT / '.local'))
        self.addCleanup(shutil.rmtree, self.work, True)
        self.out = self.work / 'salida'
        self.out.mkdir()

    def snapshot(self):
        return sorted(str(p.relative_to(self.work)) for p in self.work.rglob('*'))

    def assertRejectsWithoutOutput(self, code, operation):
        before = self.snapshot()
        with self.assertRaises(ValueError) as raised:
            operation()
        self.assertEqual(str(raised.exception), code)
        self.assertEqual(self.snapshot(), before)

    def test_clean_wrapper_rejects_every_invalid_edition_before_any_file(self):
        for edition in INVALID_EDITIONS:
            with self.subTest(edition=edition):
                self.assertRejectsWithoutOutput('edition_invalid', lambda: clean.clean_build(
                    self.work / 'no-existe.zip', self.work / 'no-existe-servicio', self.out / 'RackClick-Servidor-x.zip',
                    self.out / 'payload.zip', bundle_sha256=BUNDLE_07, edition=edition))

    def test_payload_builder_rejects_every_invalid_edition_before_any_file(self):
        for edition in INVALID_EDITIONS:
            with self.subTest(edition=edition):
                self.assertRejectsWithoutOutput('edition_invalid', lambda: installer.build(
                    self.work / 'no-existe.zip', self.work / 'no-existe-servicio', self.out / 'payload.zip',
                    bundle_sha256=BUNDLE_07, edition=edition))

    def test_ip_change_cmd_rejects_every_invalid_edition_before_any_file(self):
        for edition in INVALID_EDITIONS:
            with self.subTest(edition=edition):
                self.assertRejectsWithoutOutput('edition_invalid', lambda: cambio.build(
                    self.work / 'no-existe-payload.zip', self.out / 'cambio.zip',
                    edition=edition, payload_json_sha256=PAYLOAD_JSON_06))

    def test_historical_05_is_refused_against_current_sources_without_output(self):
        # Combinacion incoherente: edicion 05 con el bundle 05 pero fuentes que fijan el bundle 07.
        self.assertRejectsWithoutOutput('edition_source_pin_mismatch', lambda: clean.clean_build(
            self.work / 'no-existe.zip', self.work / 'no-existe-servicio', self.out / 'RackClick-Servidor-05.zip',
            self.out / 'payload-05.zip', bundle_sha256=HISTORICAL_05_BUNDLE, edition='05'))
        self.assertRejectsWithoutOutput('edition_source_pin_mismatch', lambda: installer.build(
            self.work / 'no-existe.zip', self.work / 'no-existe-servicio', self.out / 'payload-05.zip',
            bundle_sha256=HISTORICAL_05_BUNDLE, edition='05'))

    def test_valid_edition_with_mismatched_bundle_pin_is_refused_without_output(self):
        self.assertRejectsWithoutOutput('edition_source_pin_mismatch', lambda: clean.clean_build(
            self.work / 'no-existe.zip', self.work / 'no-existe-servicio', self.out / 'RackClick-Servidor-06.zip',
            self.out / 'payload-06.zip', bundle_sha256=HISTORICAL_05_BUNDLE, edition='06'))

    def test_malformed_bundle_hash_is_refused_without_output(self):
        for value in ['', 'ABCDEF', BUNDLE_07.upper(), BUNDLE_07 + '0', '../' * 10]:
            with self.subTest(value=value[:12]):
                self.assertRejectsWithoutOutput('bundle_sha256_invalid', lambda: installer.build(
                    self.work / 'no-existe.zip', self.work / 'no-existe-servicio', self.out / 'payload.zip',
                    bundle_sha256=value, edition='07'))

    def test_edition_is_required_no_implicit_05_default(self):
        with self.assertRaises(TypeError):
            installer.build(self.work / 'x.zip', self.work / 'y', self.out / 'p.zip', bundle_sha256=BUNDLE_07)
        with self.assertRaises(TypeError):
            clean.clean_build(self.work / 'x.zip', self.work / 'y', self.out / 'w.zip', self.out / 'p.zip',
                              bundle_sha256=BUNDLE_07)


if __name__ == '__main__':
    unittest.main()
