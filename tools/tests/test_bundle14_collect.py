"""Pruebas activas del colector de bundle para la candidata 14 (package_offline_bundle.collect_application).

Cubren la cobertura de inventory.json y SHA256SUMS.txt, la ubicación de la candidata y los conjuntos exactos.
Cada caso trabaja sobre una copia privada bajo .local/distribution14, nunca sobre la candidata revisada.
"""
import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import package_offline_bundle as bundle  # noqa: E402

CANDIDATE = ROOT / '.local' / 'distribution14' / 'candidata-01'
SCHEMA14 = bundle.APPLICATION_SCHEMA14_SHA256
DISTRIBUTION_BYTES = 7263552


@unittest.skipUnless(CANDIDATE.is_dir(), 'requiere la candidata 14 en .local/distribution14')
class Bundle14CollectTests(unittest.TestCase):
    def setUp(self):
        # El colector exige que la candidata sea hija directa de .local/distribution14: la copia se crea allí.
        self.scratch = Path(tempfile.mkdtemp(prefix='rc-bundle14-', dir=ROOT / '.local' / 'distribution14'))
        shutil.copytree(CANDIDATE, self.scratch, dirs_exist_ok=True)
        self.manifest = self.scratch / 'manifest.json'
        self.home = Path(tempfile.mkdtemp(prefix='rc-bundle14-fuera-'))

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)
        shutil.rmtree(self.home, ignore_errors=True)

    def rejects(self, code: str, manifest: Path) -> None:
        with self.assertRaises(bundle.BundleError) as raised:
            bundle.collect_application(manifest, SCHEMA14)
        self.assertEqual(str(raised.exception), code)

    def test_positive_collects_manifest_metadata_and_exact_distribution(self):
        payloads, candidate = bundle.collect_application(self.manifest, SCHEMA14)
        paths = {p.path: p.data for p in payloads}

        self.assertEqual(candidate, self.scratch)
        self.assertEqual(bundle.application_schema(SCHEMA14), 14)
        self.assertIn('application/inventory.json', paths)
        self.assertIn('application/SHA256SUMS.txt', paths)
        self.assertEqual(len(payloads), 1 + 24 + 18 + 2)
        distribution = sum(len(p.data) for p in payloads if p.path.startswith(('application/server/', 'application/frontend/')))
        self.assertEqual(distribution, DISTRIBUTION_BYTES)
        self.assertEqual(hashlib.sha256(paths['application/inventory.json']).hexdigest(), bundle.APPLICATION_SCHEMA14_INVENTORY_SHA256)
        self.assertEqual(hashlib.sha256(paths['application/SHA256SUMS.txt']).hexdigest(), bundle.APPLICATION_SCHEMA14_SUMS_SHA256)

    def test_missing_inventory_is_rejected(self):
        (self.scratch / 'inventory.json').unlink()

        self.rejects('application_metadata_missing', self.manifest)

    def test_altered_inventory_is_untrusted(self):
        target = self.scratch / 'inventory.json'
        target.write_bytes(target.read_bytes() + b' ')

        self.rejects('application_metadata_untrusted', self.manifest)

    def test_missing_sums_is_rejected(self):
        (self.scratch / 'SHA256SUMS.txt').unlink()

        self.rejects('application_metadata_missing', self.manifest)

    def test_altered_sums_is_untrusted(self):
        target = self.scratch / 'SHA256SUMS.txt'
        target.write_bytes(target.read_bytes().replace(b'  manifest.json', b'  manifest.jsoN'))

        self.rejects('application_metadata_untrusted', self.manifest)

    def test_manifest_outside_distribution_area_is_rejected(self):
        copy = self.home / 'manifest.json'
        shutil.copyfile(self.manifest, copy)

        self.rejects('application_root_invalid', copy)

    def test_renamed_manifest_is_rejected(self):
        renamed = self.scratch / 'manifest-copia.json'
        shutil.copyfile(self.manifest, renamed)

        self.rejects('application_root_invalid', renamed)

    def test_extra_server_file_breaks_the_exact_inventory(self):
        (self.scratch / 'server' / 'extra.dll').write_bytes(b'MZ-extra')

        self.rejects('application_inventory_mismatch', self.manifest)

    def test_altered_server_file_is_untrusted(self):
        target = self.scratch / 'server' / 'RackClick.Server.dll'
        target.write_bytes(target.read_bytes() + b'\x00')

        self.rejects('application_file_untrusted', self.manifest)


if __name__ == '__main__':
    unittest.main()
