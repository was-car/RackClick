import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('probe_package', ROOT / 'tools/package_runtime_account_probe.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class PackageGuards(unittest.TestCase):
    def test_traversal_output_rejected(self):
        with self.assertRaisesRegex(ValueError, 'new_local_zip_required'):
            package.build(ROOT / '.local/../probe-must-not-be-created.zip')

    def test_output_outside_local_rejected(self):
        with self.assertRaisesRegex(ValueError, 'new_local_zip_required'):
            package.build(ROOT / 'probe-must-not-be-created.zip')

    def test_existing_output_preserved(self):
        with tempfile.NamedTemporaryFile(dir=ROOT / '.local', suffix='.zip', delete=False) as output:
            output.write(b'preserve')
            path = Path(output.name)
        with self.assertRaisesRegex(ValueError, 'new_local_zip_required'):
            package.build(path)
        self.assertEqual(path.read_bytes(), b'preserve')

    def test_wrong_frozen_source_rejected(self):
        with patch.object(package, 'FROZEN_SHA', '0' * 64):
            with self.assertRaisesRegex(ValueError, 'frozen_payload_changed'):
                package.contract()

    def test_contract_matches_frozen_operators(self):
        contract = package.contract()
        self.assertEqual(len(contract['pins']), 47)
        self.assertIn('server_manifest_hash_mismatch', contract['codes'])
        self.assertIn('server_bind_not_local', contract['codes'])
        self.assertNotIn('private_secret_sentinel', contract['codes'])


if __name__ == '__main__':
    unittest.main()
