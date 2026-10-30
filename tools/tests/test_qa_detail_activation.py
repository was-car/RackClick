"""Offline48 invariants in synthetic files/maps only; no real QA operations."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / 'evidence/s1-20261017/qa-detalle-activacion-48/verificar_activacion.py'
spec = importlib.util.spec_from_file_location('activation48_tests', path)
activation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(activation)


class DetailActivationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.version = Path(self.temp.name) / 'version48'
        self.version.mkdir()
        self.previous = b'{"synthetic": "previous configuration"}'
        (self.version / 'previous-config.json').write_bytes(self.previous)
        old = {'directory': 'synthetic-qa', 'artifactDirectory': 'version45', 'pointer': 'pointer',
               'identity': 'identity', 'config': hashlib.sha256(self.previous).hexdigest(),
               'dll': activation.OLD_DLL, 'bundle': activation.OLD_BUNDLE, 'stopped': True,
               'rootFiles': {'credentials.private': 'private-hash'}, 'dataFiles': {'base/1': 'data-hash'},
               'serverFiles': {'RackClick.Server.dll': activation.OLD_DLL, 'Npgsql.dll': 'fixed', 'sql/schema.sql': 'fixed'},
               'frontendFiles': {'app.js': activation.OLD_BUNDLE},
               'versionFiles': {'version45/server/RackClick.Server.dll': activation.OLD_DLL}}
        self.before = {'manual': {'synthetic-original': 'unchanged'}, 'rc9': old}
        self.files = {'server': old['serverFiles'] | {'RackClick.Server.dll': activation.NEW_DLL},
                      'frontend': {'app.js': activation.NEW_BUNDLE}}
        self.after = deepcopy(self.before)
        self.after['rc9'].update(artifactDirectory=str(self.version), config='new-config',
                                 dll=activation.NEW_DLL, bundle=activation.NEW_BUNDLE,
                                 serverFiles=deepcopy(self.files['server']), frontendFiles=deepcopy(self.files['frontend']))
        self.after['rc9']['versionFiles']['version48/server/RackClick.Server.dll'] = activation.NEW_DLL

    def test_complete_pair_and_recovery_preserve_previous_version(self):
        activation.preserved(self.before, self.after, self.files, True)
        recovered = deepcopy(self.before)
        recovered['rc9']['versionFiles'] = deepcopy(self.after['rc9']['versionFiles'])
        activation.preserved(self.before, recovered, self.files, False)

    def test_private_database_identity_original_and_history_are_invariants(self):
        for key in ('directory', 'pointer', 'identity', 'rootFiles', 'dataFiles', 'stopped', 'versionFiles'):
            with self.subTest(key=key):
                changed = deepcopy(self.after)
                changed['rc9'][key] = {} if isinstance(changed['rc9'][key], dict) else 'changed'
                with self.assertRaises(RuntimeError):
                    activation.preserved(self.before, changed, self.files, True)
        changed = deepcopy(self.after)
        changed['manual'] = {'changed': True}
        with self.assertRaises(RuntimeError):
            activation.preserved(self.before, changed, self.files, True)

    def test_mixed_incomplete_pairs_and_reused_directory_are_rejected(self):
        for key in ('dll', 'bundle', 'serverFiles', 'frontendFiles', 'artifactDirectory'):
            with self.subTest(key=key):
                changed = deepcopy(self.after)
                changed['rc9'][key] = deepcopy(self.before['rc9'][key])
                with self.assertRaises(RuntimeError):
                    activation.preserved(self.before, changed, self.files, True)

    def test_previous_config_and_recovery_pointer_are_exact(self):
        (self.version / 'previous-config.json').write_bytes(b'changed')
        with self.assertRaises(RuntimeError):
            activation.preserved(self.before, self.after, self.files, True)
        recovered = deepcopy(self.before)
        recovered['rc9']['artifactDirectory'] = 'wrong-version'
        with self.assertRaises(RuntimeError):
            activation.preserved(self.before, recovered, self.files, False)

    def preflight(self, current, files, observed=None):
        baseline = Path(self.temp.name) / 'last.json'
        baseline.write_text(json.dumps({'observed': observed or self.before}), encoding='utf-8')
        with patch.object(activation, 'LAST', baseline), patch.object(activation.snapshot, 'public', side_effect=lambda p: p):
            activation.preflight(current, files)

    def test_preflight_allows_only_application_binary_changes(self):
        self.preflight(self.before, self.files)
        for key in ('Npgsql.dll', 'sql/schema.sql'):
            with self.subTest(key=key):
                files = deepcopy(self.files)
                files['server'][key] = 'changed'
                with self.assertRaises(RuntimeError):
                    self.preflight(self.before, files)
        files = deepcopy(self.files)
        files['server']['new-runtime.json'] = 'unexpected'
        with self.assertRaises(RuntimeError):
            self.preflight(self.before, files)

    def test_preflight_rejects_stale_pair_and_changed_baseline(self):
        current = deepcopy(self.before)
        current['rc9']['bundle'] = 'older-bundle'
        with self.assertRaises(RuntimeError):
            self.preflight(current, self.files, current)
        current = deepcopy(self.before)
        current['rc9']['dataFiles']['base/1'] = 'changed'
        with self.assertRaises(RuntimeError):
            self.preflight(current, self.files)

    def test_review_manifest_rejects_missing_modified_and_escaping_files(self):
        directory = Path(self.temp.name) / 'review'
        directory.mkdir()
        artifact = directory / 'result.json'
        artifact.write_bytes(b'PASS')
        manifest = directory / 'SHA256SUMS'
        expected = hashlib.sha256(b'PASS').hexdigest()
        manifest.write_text(expected + '  result.json\n', encoding='utf-8')
        activation.review_files(directory)
        artifact.write_bytes(b'FAIL')
        with self.assertRaises(RuntimeError):
            activation.review_files(directory)
        artifact.unlink()
        with self.assertRaises(FileNotFoundError):
            activation.review_files(directory)
        manifest.write_text(expected + '  ../outside.json\n', encoding='utf-8')
        with self.assertRaises(RuntimeError):
            activation.review_files(directory)


if __name__ == '__main__':
    unittest.main()
