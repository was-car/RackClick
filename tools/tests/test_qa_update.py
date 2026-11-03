"""Artifact switching in temporary fixtures only; no live QA or PostgreSQL writes."""
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/windows'))
update = importlib.import_module('Qa-Update')


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name) / 'qa'
        self.source = Path(self.temporary.name) / 'candidate'
        for base, data in [(self.directory, b'old'), (self.source, b'new')]:
            (base / 'server').mkdir(parents=True)
            (base / 'frontend').mkdir()
            (base / 'server/RackClick.Server.dll').write_bytes(data)
            (base / 'frontend/app.js').write_bytes(data)
        old = hashlib.sha256(b'old').hexdigest()
        self.new = hashlib.sha256(b'new').hexdigest()
        self.cfg = {'directory': str(self.directory), 'profile': 'rc9', 'host': '127.0.0.1',
                    'webPort': 12345, 'pgPort': 23456, 'database': 'test', 'connection': 'synthetic',
                    'dllSha256': old, 'bundleSha256': old}
        (self.directory / 'manual-qa.json').write_text(json.dumps(self.cfg))
        (self.directory / 'database-sentinel').write_bytes(b'keep')
        self.original = (self.directory / 'manual-qa.json').read_bytes()

    def install(self):
        return update.install(self.directory, self.cfg, self.source / 'server', self.source / 'frontend', self.new, self.new)

    def test_update_and_rollback_retain_originals_and_database(self):
        version = self.install()
        current = json.loads((self.directory / 'manual-qa.json').read_text())
        self.assertEqual(update.qa.artifact_directory(self.directory, current), version)
        self.assertEqual((version / 'previous-config.json').read_bytes(), self.original)
        self.assertEqual((self.directory / 'server/RackClick.Server.dll').read_bytes(), b'old')
        # A damaged new artifact must not prevent recovery to the valid previous version.
        (version / 'frontend/app.js').write_bytes(b'corrupted-new-version')
        update.rollback(self.directory, current)
        self.assertEqual(json.loads((self.directory / 'manual-qa.json').read_text()), self.cfg)
        self.assertEqual((self.directory / 'database-sentinel').read_bytes(), b'keep')

    def test_second_update_recovers_previous_active_version_not_initial_base(self):
        first = self.install()
        first_cfg = json.loads((self.directory / 'manual-qa.json').read_text())
        first_bytes = (self.directory / 'manual-qa.json').read_bytes()
        (self.source / 'frontend/app.js').write_bytes(b'latest-frontend')
        latest = hashlib.sha256(b'latest-frontend').hexdigest()
        second = update.install(self.directory, first_cfg, first / 'server',
                                self.source / 'frontend', self.new, latest)
        second_cfg = json.loads((self.directory / 'manual-qa.json').read_text())
        self.assertEqual((second / 'previous-config.json').read_bytes(), first_bytes)
        # The new frontend may be damaged: recovery must still select the prior active pair.
        (second / 'frontend/app.js').write_bytes(b'corrupted-latest')
        update.rollback(self.directory, second_cfg)
        self.assertEqual(json.loads((self.directory / 'manual-qa.json').read_text()), first_cfg)
        self.assertEqual(update.qa.artifact_directory(self.directory, first_cfg), first)
        self.assertEqual((first / 'frontend/app.js').read_bytes(), b'new')
        self.assertEqual((self.directory / 'frontend/app.js').read_bytes(), b'old')
        self.assertEqual((self.directory / 'database-sentinel').read_bytes(), b'keep')

    def test_failure_before_atomic_switch_keeps_old_configuration(self):
        with patch.object(update, 'atomic_config', side_effect=OSError('injected switch failure')):
            with self.assertRaises(OSError):
                self.install()
        self.assertEqual((self.directory / 'manual-qa.json').read_bytes(), self.original)
        self.assertEqual((self.directory / 'database-sentinel').read_bytes(), b'keep')
        with self.assertRaises(RuntimeError):
            update.install(self.directory, self.cfg, self.source / 'server', self.source / 'frontend', 'wrong', self.new)
        self.assertEqual((self.directory / 'manual-qa.json').read_bytes(), self.original)

    def test_external_artifacts_and_changed_frozen_hash_are_rejected(self):
        foreign = self.cfg | {'artifactDirectory': str(self.source)}
        with self.assertRaises(RuntimeError):
            update.qa.artifact_directory(self.directory, foreign)
        (self.directory / 'frontend/app.js').write_bytes(b'tampered')
        with self.assertRaises(RuntimeError):
            update.qa.artifact_directory(self.directory, self.cfg)

    def test_wrong_bundle_rejects_entire_pair_before_creating_version(self):
        with self.assertRaises(RuntimeError):
            update.install(self.directory, self.cfg, self.source / 'server',
                           self.source / 'frontend', self.new, 'wrong-bundle')
        self.assertFalse((self.directory / 'versions').exists())
        self.assertEqual((self.directory / 'manual-qa.json').read_bytes(), self.original)
        self.assertEqual((self.directory / 'database-sentinel').read_bytes(), b'keep')

    def test_frontend_copy_failure_does_not_switch_backend_only(self):
        copytree = update.shutil.copytree

        def partial_copy(source, destination, *args, **kwargs):
            if Path(source) == self.source / 'frontend':
                raise OSError('injected second-copy failure')
            return copytree(source, destination, *args, **kwargs)

        with patch.object(update.shutil, 'copytree', side_effect=partial_copy):
            with self.assertRaises(OSError):
                self.install()
        self.assertEqual((self.directory / 'manual-qa.json').read_bytes(), self.original)
        self.assertEqual((self.directory / 'server/RackClick.Server.dll').read_bytes(), b'old')
        self.assertEqual((self.directory / 'frontend/app.js').read_bytes(), b'old')
        self.assertEqual((self.directory / 'database-sentinel').read_bytes(), b'keep')


if __name__ == '__main__':
    unittest.main()
