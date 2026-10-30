"""Pruebas activas de la matriz de perfiles y del aviso Otp.NET del bundle 14.

Comprueban que el registro de perfiles es exactamente la matriz literal, que el lock de 14 incluye el aviso con su
procedencia, que el lock histórico 9–13 no cambia, y que el aviso ausente, alterado o con un lock cruzado se rechaza.
Las copias de locks se crean bajo .local y se borran al terminar; el lock histórico nunca se modifica.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_offline_bundle as bundle  # noqa: E402
from offline_profile_matrix import MATRIX, HISTORICAL, NEW  # noqa: E402

LEGACY_LOCK = ROOT / 'development' / 'offline-bundle.sources.json'
LOCK_14 = ROOT / 'development' / 'offline-bundle14.sources.json'
LEGACY_LOCK_SHA256 = '76f39955267c30249417bdd5ab2f3eb9e6bd6ab42dc01d5a7d55b288feac2111'
NOTICE_SHA256 = '0bc32be0ce13330ba88d208548582a641f95b1f66bb19be91f5acc1436c52472'
BUNDLE_02 = ROOT / '.local' / 'dist14-bundle' / 'RackClick-Bundle-M3-14-02.zip'
BUNDLE_01 = ROOT / '.local' / 'dist14-bundle' / 'RackClick-Bundle-M3-14-01.zip'


class ProfileMatrixTests(unittest.TestCase):
    def test_registry_is_exactly_the_literal_matrix(self):
        self.assertEqual({row[0] for row in MATRIX}, set(bundle.APPLICATION_PROFILES))
        self.assertEqual(len(MATRIX), 14)
        self.assertEqual(len(HISTORICAL), 12)
        self.assertEqual(NEW[1], '14')

    def test_each_profile_matches_its_literal_row(self):
        for digest, name, schema, server, frontend, size in MATRIX:
            with self.subTest(profile=name):
                profile = bundle.APPLICATION_PROFILES[digest]
                self.assertEqual((profile['name'], profile['files'], profile['bytes']),
                                 (name, {'server': server, 'frontend': frontend}, size))
                self.assertEqual(bundle.application_schema(digest), schema)

    def test_only_profile_14_declares_metadata_and_notice_pins(self):
        for digest, name, *_ in MATRIX:
            with self.subTest(profile=name):
                self.assertEqual('metadata' in bundle.APPLICATION_PROFILES[digest], name == '14')


class NoticeLockTests(unittest.TestCase):
    def setUp(self):
        self.scratch = Path(tempfile.mkdtemp(prefix='rc-notice-', dir=ROOT / '.local'))
        self.addCleanup(shutil.rmtree, self.scratch, True)

    def lock_copy(self, mutate):
        data = json.loads(LOCK_14.read_bytes())
        mutate(data)
        path = self.scratch / 'lock.json'
        path.write_bytes(bundle.json_bytes(data))
        return path

    def rejects(self, code, path, pins=bundle.SOURCE_PINS_14, profile='14'):
        with self.assertRaises(bundle.BundleError) as raised:
            bundle.collect_locks(path, pins, profile)
        self.assertEqual(str(raised.exception), code)

    def test_lock_14_supplies_the_notice_with_its_provenance(self):
        _, _, payloads, report, _ = bundle.collect_locks(LOCK_14, bundle.SOURCE_PINS_14, '14')
        notice = {p.path: p.data for p in payloads}['licenses/Otp.NET-LICENSE.txt']

        self.assertEqual(hashlib.sha256(notice).hexdigest(), NOTICE_SHA256)
        self.assertEqual(len(notice), 1070)
        self.assertIn(b'MIT License', notice)
        self.assertEqual([r['name'] for r in report], ['vc_redist.x64.exe', 'Npgsql-LICENSE', 'Otp.NET-LICENSE'])

    def test_historical_lock_is_unchanged_and_still_serves_9_to_13(self):
        self.assertEqual(hashlib.sha256(LEGACY_LOCK.read_bytes()).hexdigest(), LEGACY_LOCK_SHA256)
        _, _, payloads, report, _ = bundle.collect_locks(LEGACY_LOCK)

        self.assertEqual(sorted(p.path for p in payloads), ['licenses/Npgsql-LICENSE', 'prerequisites/vc_redist.x64.exe'])
        self.assertEqual([r['name'] for r in report], ['vc_redist.x64.exe', 'Npgsql-LICENSE'])

    def test_crossed_locks_are_refused_in_both_directions(self):
        self.rejects('sources_profile_mismatch', LEGACY_LOCK, pins=bundle.SOURCE_PINS_14, profile='14')
        with self.assertRaises(bundle.BundleError) as raised:
            bundle.collect_locks(LOCK_14)
        self.assertEqual(str(raised.exception), 'sources_profile_mismatch')

    def test_notice_row_removed_is_an_inventory_mismatch(self):
        path = self.lock_copy(lambda d: d.__setitem__('sources', [r for r in d['sources'] if r['name'] != 'Otp.NET-LICENSE']))
        self.rejects('sources_inventory_invalid', path)

    def test_notice_missing_on_disk_is_refused(self):
        def point_nowhere(data):
            for row in data['sources']:
                if row['name'] == 'Otp.NET-LICENSE':
                    row['path'] = '.local/rc-notice-no-existe/Otp.NET-LICENSE.txt'
        self.rejects('source_missing_or_wrong_type', self.lock_copy(point_nowhere))

    def test_notice_altered_on_disk_is_untrusted(self):
        altered = self.scratch / 'Otp.NET-LICENSE.txt'
        altered.write_bytes((ROOT / '.local' / 'downloads' / 'offline14-otpnet' / 'Otp.NET-LICENSE.txt').read_bytes() + b' ')

        def point_at_altered(data):
            for row in data['sources']:
                if row['name'] == 'Otp.NET-LICENSE':
                    row['path'] = altered.relative_to(ROOT).as_posix()
        self.rejects('source_file_untrusted', self.lock_copy(point_at_altered))

    def test_notice_pin_changed_in_top_level_key_is_refused(self):
        self.rejects('source_pin_mismatch', self.lock_copy(lambda d: d.__setitem__('otpNetLicenseSha256', '0' * 64)))

    def test_notice_row_digest_changed_is_refused(self):
        def change_row(data):
            for row in data['sources']:
                if row['name'] == 'Otp.NET-LICENSE':
                    row['sha256'] = '1' * 64
        self.rejects('source_pin_mismatch', self.lock_copy(change_row))

    def test_notice_key_absent_from_lock_is_refused(self):
        self.rejects('source_pin_mismatch', self.lock_copy(lambda d: d.pop('otpNetLicenseSha256')))


@unittest.skipUnless(BUNDLE_02.exists(), 'requiere el bundle 14-02 generado en .local/dist14-bundle')
class BundleArtifactTests(unittest.TestCase):
    def test_bundle_02_contains_the_exact_notice_and_its_record(self):
        with zipfile.ZipFile(BUNDLE_02) as archive:
            self.assertIsNone(archive.testzip())
            notice = archive.read('licenses/Otp.NET-LICENSE.txt')
            record = json.loads(archive.read('bundle.json'))['files']['licenses/Otp.NET-LICENSE.txt']

        self.assertEqual(hashlib.sha256(notice).hexdigest(), NOTICE_SHA256)
        self.assertEqual(record, {'bytes': 1070, 'sha256': NOTICE_SHA256})

    @unittest.skipUnless(BUNDLE_01.exists(), 'requiere el bundle 14-01 para comprobar que no tiene aviso')
    def test_bundle_01_has_no_notice(self):
        with zipfile.ZipFile(BUNDLE_01) as archive:
            self.assertNotIn('licenses/Otp.NET-LICENSE.txt', archive.namelist())


POWERSHELL = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'
HISTORICAL_13 = ROOT / '.local' / 'clean-release-fixtures' / '62fcf9b2ad0f48b6a36417f610e3758e' / 'stage' / 'RackClick.zip'
HISTORICAL_13_SHA256 = 'a0df90ed3a2864492d8d9bdc2cc2e552113a6b9c81a3e603c1c2920486c26869'


def run_native(script: Path, *args: str) -> tuple[int, dict]:
    command = [str(POWERSHELL), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(script), *args]
    completed = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
    return completed.returncode, json.loads(completed.stdout.strip().splitlines()[-1])


@unittest.skipUnless(sys.platform == 'win32' and BUNDLE_02.exists(), 'requiere Windows PowerShell 5.1 y el bundle 14-02')
class NativeReaderTests(unittest.TestCase):
    VERIFY = ROOT / 'tools' / 'windows' / 'Test-RackClickOfflineBundle.ps1'
    INSTALL = ROOT / 'tools' / 'windows' / 'Install-RackClickOfflineBundle.ps1'

    def test_reader_verifies_bundle_02_with_notice_and_metadata(self):
        code, report = run_native(self.VERIFY, '-ArchivePath', str(BUNDLE_02), '-ExpectedArchiveSha256', '191acd6fc1932f74ad2db9cd5d953ab629dc7a5621bea03df03cad2488155a51')

        self.assertEqual((code, report['code']), (0, 'bundle_verified'))
        self.assertEqual((report['counts']['notices'], report['counts']['metadata']), (1, 2))
        self.assertEqual(report['verifiedFiles'], 1986)

    @unittest.skipUnless(BUNDLE_01.exists(), 'requiere el bundle 14-01')
    def test_reader_refuses_bundle_01_because_the_notice_is_missing(self):
        code, report = run_native(self.VERIFY, '-ArchivePath', str(BUNDLE_01), '-ExpectedArchiveSha256', 'f0b53f7353a427a319c9ded57c4b7bc969a48493803798e3d799ef96674ef803')

        self.assertEqual((code, report['code']), (2, 'layout_counts_invalid'))

    def test_installer_source_no_longer_refuses_schema_14_by_guard(self):
        # Esta prueba NO ejecuta el instalador: instalaría en este equipo. Solo comprueba que la guardia 06 no existe.
        source = (ROOT / 'tools' / 'windows' / 'Install-RackClickOfflineBundle.ps1').read_text(encoding='utf-8')

        self.assertNotIn('schema14_install_not_propagated', source)

    def case_variant(self, renames: dict[str, str]) -> tuple[Path, str]:
        """Copia del bundle 02 con nombres cambiados sólo de mayúsculas, en el ZIP y en bundle.json; el resto no cambia."""
        scratch = Path(tempfile.mkdtemp(prefix='rc-case14-', dir=ROOT / '.local'))
        self.addCleanup(shutil.rmtree, scratch, True)
        target = scratch / 'RackClick-Bundle-caso-mayusculas.zip'
        with zipfile.ZipFile(BUNDLE_02) as source:
            meta = json.loads(source.read('bundle.json'))
            for old, new in renames.items():
                meta['files'][new] = meta['files'].pop(old)
            meta_bytes = json.dumps(meta, indent=2, sort_keys=True).encode('ascii')
            with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as out:
                for info in source.infolist():
                    name = renames.get(info.filename, info.filename)
                    data = meta_bytes if info.filename == 'bundle.json' else source.read(info)
                    out.writestr(name, data)
        return target, hashlib.sha256(target.read_bytes()).hexdigest()

    def test_reader_refuses_case_variant_names_for_pinned_entries(self):
        for old, new in (('application/inventory.json', 'application/Inventory.json'),
                         ('licenses/Otp.NET-LICENSE.txt', 'licenses/otp.net-license.txt')):
            with self.subTest(entry=new):
                copy, digest = self.case_variant({old: new})
                code, report = run_native(self.VERIFY, '-ArchivePath', str(copy), '-ExpectedArchiveSha256', digest)

                self.assertEqual((code, report['code']), (2, 'layout_invalid'))

    @unittest.skipUnless(HISTORICAL_13.exists(), 'requiere el bundle histórico de esquema 13 en .local')
    def test_reader_still_verifies_the_historical_schema_13_bundle(self):
        code, report = run_native(self.VERIFY, '-ArchivePath', str(HISTORICAL_13), '-ExpectedArchiveSha256', HISTORICAL_13_SHA256)

        self.assertEqual((code, report['code']), (0, 'bundle_verified'))
        self.assertEqual(report['versions']['schema'], 13)
        self.assertEqual((report['counts']['notices'], report['counts']['metadata']), (0, 0))


if __name__ == '__main__':
    unittest.main()
