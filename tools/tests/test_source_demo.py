"""Guard the published demo's seed, inherited environment and build receipts."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('source_demo', ROOT / 'tools/start_demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class SourceDemoTests(unittest.TestCase):
    def test_pinned_seed_has_only_inventory_tables(self):
        self.assertEqual(demo.digest(demo.PLAN), demo.PLAN_SHA)
        seed = json.loads(demo.PLAN.read_bytes())
        self.assertEqual(set(seed['rows']), {'customer', 'inventory_site', 'inventory_building',
                         'inventory_room', 'inventory_rack', 'inventory_device', 'inventory_port_group',
                         'inventory_port', 'inventory_connection', 'inventory_connection_endpoint'})
        self.assertEqual(len(seed['rows']['customer']), 10)
        self.assertEqual(len(seed['rows']['inventory_port']), 5408)

    def test_inherited_host_settings_and_hooks_cannot_enable_mfa_or_redirect_database(self):
        before = dict(os.environ)
        values = {'MfaKeyStore__Enabled': 'true', 'MfaKeyStore__InstancesRoot': 'external',
                  'ConnectionStrings__RackClick': 'external', 'DOTNET_STARTUP_HOOKS': 'external',
                  'CORECLR_ENABLE_PROFILING': '1', 'ASPNETCORE_URLS': 'https://external',
                  'PublicOrigin': 'https://external'}
        with patch.dict(os.environ, values):
            child = demo.environment()
            self.assertEqual(child['MfaKeyStore__Enabled'], 'false')
            self.assertEqual(child['DOTNET_EnableDiagnostics'], '0')
            for name in values:
                if name != 'MfaKeyStore__Enabled':
                    self.assertNotIn(name, child)
        self.assertEqual(dict(os.environ), before)

    def fixture(self, root):
        plan = root / 'seed.json'; plan.write_bytes(demo.PLAN.read_bytes())
        output = root / 'output'; output.mkdir()
        publication = root / 'server'; publication.mkdir()
        loader = root / 'loader'; loader.mkdir()
        frontend = root / 'frontend'; frontend.mkdir()
        file = publication / 'test.dll'; file.write_bytes(b'build receipt fixture')
        (output / 'build.json').write_text(json.dumps({'files': {'server/test.dll': demo.digest(file)}}))
        return patch.multiple(demo, ROOT=root, PLAN=plan, OUTPUT=output, PUBLICATION=publication,
                              LOADER=loader / 'loader.dll', FRONTEND=frontend), file

    def test_build_receipt_accepts_original_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            context, _ = self.fixture(Path(directory))
            with context:
                demo.validate()

    def test_build_receipt_rejects_modified_or_absent_output(self):
        with tempfile.TemporaryDirectory() as directory:
            context, file = self.fixture(Path(directory))
            with context:
                file.write_bytes(b'altered')
                with self.assertRaisesRegex(RuntimeError, 'build_changed'):
                    demo.validate()
                file.unlink()
                with self.assertRaisesRegex(RuntimeError, 'build_changed'):
                    demo.validate()

    def test_build_receipt_rejects_extra_output(self):
        with tempfile.TemporaryDirectory() as directory:
            context, file = self.fixture(Path(directory))
            with context:
                file.with_name('extra.dll').write_bytes(b'extra')
                with self.assertRaisesRegex(RuntimeError, 'build_extra_file'):
                    demo.validate()

    def test_seed_tamper_rejected_before_database_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            context, _ = self.fixture(Path(directory))
            with context:
                demo.PLAN.write_bytes(b'{}')
                with self.assertRaisesRegex(RuntimeError, 'synthetic_inventory_hash_mismatch'):
                    demo.validate()


if __name__ == '__main__':
    unittest.main()
