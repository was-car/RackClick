"""Pure guard/format checks; never creates a Lab, starts PG or changes QA."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/windows'))
spec = importlib.util.spec_from_file_location('prepare_rc9', ROOT / 'tools/windows/Prepare-Rc9ServerRestore.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PrepareGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = ROOT / '.local' / ('rc9-converter-guards-' + uuid.uuid4().hex)
        cls.fixture.mkdir(exist_ok=False)

    def reject(self, operation, code):
        with self.assertRaises(module.PreparationError) as caught:
            operation()
        self.assertEqual(str(caught.exception), code)

    def backup(self):
        directory = self.fixture / uuid.uuid4().hex
        directory.mkdir()
        dump = directory / 'data.dump'
        dump.write_bytes(b'PGDMP-inert-format-fixture')
        manifest = dict(schemaVersion=1, kind='RackClickDatabaseBackup', postgresVersion='17.11',
                        format='custom', dumpFile='data.dump', dumpBytes=dump.stat().st_size,
                        dumpSha256=module.sha256(dump), createdUtc='2026-10-20T00:00:00Z')
        module.write_new(directory / 'manifest.json', manifest)
        receipt = dict(valid=True, success=True, exitCode=0, code='backup_complete',
                       manifestSha256=module.sha256(directory / 'manifest.json'), backupPath=str(directory))
        return directory, manifest, receipt

    def test_guard_accepts_only_new_dedicated_local_directory(self):
        destination = ROOT / '.local' / ('rc9-server-restore-' + uuid.uuid4().hex)
        self.assertEqual(module.validate_output(destination), destination)
        self.reject(lambda: module.validate_output(ROOT / 'unexpected'), 'rc9_prepare_output_must_be_new_local_root')
        self.reject(lambda: module.validate_output(self.fixture / 'rc9-server-restore-nested'), 'rc9_prepare_output_must_be_new_local_root')

    def test_existing_destination_is_preserved(self):
        destination = ROOT / '.local' / ('rc9-server-restore-' + uuid.uuid4().hex)
        destination.mkdir()
        marker = destination / 'retained.txt'
        marker.write_bytes(b'keep')
        self.reject(lambda: module.validate_output(destination), 'rc9_prepare_output_exists')
        self.assertEqual(marker.read_bytes(), b'keep')

    def test_valid_native_backup_format_is_accepted(self):
        directory, manifest, receipt = self.backup()
        actual, digest = module.validate_backup(directory, receipt)
        self.assertEqual(actual, manifest)
        self.assertEqual(digest, receipt['manifestSha256'])

    def test_changed_dump_is_rejected(self):
        directory, _, receipt = self.backup()
        with (directory / 'data.dump').open('ab') as stream:
            stream.write(b'changed')
        self.reject(lambda: module.validate_backup(directory, receipt), 'rc9_prepare_backup_manifest_invalid')

    def test_wrong_receipt_hash_is_rejected(self):
        directory, _, receipt = self.backup()
        receipt['manifestSha256'] = '0' * 64
        self.reject(lambda: module.validate_backup(directory, receipt), 'rc9_prepare_backup_receipt_invalid')

    def test_extra_file_and_string_success_are_rejected(self):
        directory, _, receipt = self.backup()
        receipt['success'] = 'true'
        self.reject(lambda: module.validate_backup(directory, receipt), 'rc9_prepare_backup_receipt_invalid')
        (directory / 'unexpected.json').write_text('{}')
        self.reject(lambda: module.validate_backup(directory, receipt), 'rc9_prepare_backup_inventory_invalid')


if __name__ == '__main__':
    unittest.main()
