"""Upgrade orchestration in fake transport/files; never selects a live QA."""
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/windows'))
upgrade = importlib.import_module('Upgrade-Restored-QA')


class UpgradeTests(unittest.TestCase):
    def test_snapshot_detects_attribute_change_even_when_counts_match(self):
        project = {k: [] for k in ('sites','buildings','rooms','racks','devices','portGroups','ports','connections')}
        project['ports'] = [{'id': 'synthetic-port', 'label': 'before'}]
        data = {'/api/v1/systemhaus': {'revision': 1}, '/api/v1/customers': [{'id': 'synthetic-customer', 'name': 'private-name'}],
            '/api/v1/admin/users': {}, '/api/v1/admin/user-groups': {}, '/api/v1/admin/customer-groups': {},
            '/api/v1/customers/synthetic-customer/project': project}
        class FakeClient:
            def __init__(self, server): pass
            def login(self, username, password): return SimpleNamespace(status=200)
            def request(self, method, route): return SimpleNamespace(status=200, json=lambda: data[route])
        with patch.object(upgrade, 'Client', FakeClient):
            before, counts = upgrade.snapshot(None, 'synthetic', 'not-a-secret')
            same, _ = upgrade.snapshot(None, 'synthetic', 'not-a-secret')
            project['ports'][0]['label'] = 'after'
            after, changed_counts = upgrade.snapshot(None, 'synthetic', 'not-a-secret')
        self.assertEqual(before, same)
        self.assertNotEqual(before, after)
        self.assertEqual(counts, changed_counts)
        self.assertNotIn('private-name', json.dumps((before, counts)))

    def test_failed_subprocess_after_atomic_switch_rolls_back_only_rc9(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'evidence').mkdir()
            pointer = root / '.local/qa-wascar/current.json'
            pointer.parent.mkdir(parents=True)
            pointer.write_text('{}')
            directory = root / 'restored'
            directory.mkdir()
            (directory / 'ACCESO-PRIVADO.txt').write_text('Usuario: synthetic\nContraseña: not-a-secret\n', encoding='utf-8-sig')
            dll = root / 'candidate.dll'
            dll.write_bytes(b'candidate')
            frontend = root / 'development/frontend/dist/app.js'
            frontend.parent.mkdir(parents=True)
            frontend.write_bytes(b'candidate')
            digest = hashlib.sha256(b'candidate').hexdigest()
            cfg = {'webPort': 12345, 'dllSha256': 'old', 'bundleSha256': 'old'}
            new_cfg = cfg | {'artifactDirectory': 'new-version'}
            calls = []
            def fake_command(script, *args):
                calls.append((script, args))
                if script == 'Qa-Update.py' and '--rollback' not in args:
                    raise RuntimeError('simulated lost acknowledgement after switch')
            argv = ['upgrade', '--dll-sha256', digest, '--bundle-sha256', digest,
                    '--evidence', str(root / 'evidence/run'), '--coordinated-update']
            with patch.object(upgrade, 'ROOT', root), patch.object(upgrade.qa, 'DEFAULT_DLL', dll), \
                 patch.object(upgrade.qa, 'configure'), patch.object(upgrade.qa, 'healthy', return_value=False), \
                 patch.object(upgrade.qa, 'artifact_directory'), patch.object(upgrade.qa, 'load',
                    side_effect=[(root / 'original', {}), (directory, cfg), (directory, new_cfg)]), \
                 patch.object(upgrade, 'snapshot', return_value=('unchanged', {})), \
                 patch.object(upgrade, 'command', side_effect=fake_command), patch.object(sys, 'argv', argv):
                with self.assertRaises(RuntimeError):
                    upgrade.main()
            report = json.loads((root / 'evidence/run/failure.json').read_text())
            self.assertTrue(report['artifactsChanged'])
            self.assertTrue(report['rollbackAndRestartSucceeded'])
            self.assertTrue(any('--rollback' in args for _, args in calls))
            self.assertTrue(all('rc9' in args and 'manual' not in args for _, args in calls))
            self.assertEqual(pointer.read_text(), '{}')


if __name__ == '__main__':
    unittest.main()
