"""Activation45 invariant checks on synthetic maps/files. Never operates real QA."""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / 'evidence/s1-20261017/qa-filtros-activacion-45/verificar_activacion.py'
spec = importlib.util.spec_from_file_location('activation45_tests', path)
activation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(activation)


class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        version = Path(self.temp.name) / 'version45'
        version.mkdir()
        original = b'{"synthetic": "previous configuration"}'
        (version / 'previous-config.json').write_bytes(original)
        old = {'directory': 'synthetic-qa', 'artifactDirectory': 'version42', 'pointer': 'pointer',
               'identity': 'identity', 'config': hashlib.sha256(original).hexdigest(),
               'dll': activation.OLD_DLL, 'bundle': activation.OLD_BUNDLE, 'stopped': True,
               'rootFiles': {'credentials.private': 'private-hash'}, 'dataFiles': {'base/1': 'data-hash'},
               'serverFiles': {'RackClick.Server.dll': activation.OLD_DLL},
               'frontendFiles': {'app.js': activation.OLD_BUNDLE},
               'versionFiles': {'version42/server/RackClick.Server.dll': activation.OLD_DLL}}
        self.before = {'manual': {'synthetic-original': 'unchanged'}, 'rc9': old}
        self.files = {'server': {'RackClick.Server.dll': activation.NEW_DLL},
                      'frontend': {'app.js': activation.NEW_BUNDLE}}
        self.after = deepcopy(self.before)
        self.after['rc9'].update(artifactDirectory=str(version), config='new-config',
                                 dll=activation.NEW_DLL, bundle=activation.NEW_BUNDLE,
                                 serverFiles=deepcopy(self.files['server']),
                                 frontendFiles=deepcopy(self.files['frontend']))
        self.after['rc9']['versionFiles']['version45/server/RackClick.Server.dll'] = activation.NEW_DLL

    def test_pair_switch_and_recovery_preserve_prior_artifacts(self):
        activation.preserved(self.before, self.after, self.files, True)
        recovered = deepcopy(self.before)
        recovered['rc9']['versionFiles'] = deepcopy(self.after['rc9']['versionFiles'])
        activation.preserved(self.before, recovered, self.files, False)

    def test_private_database_identity_and_prior_versions_must_remain_equal(self):
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

    def test_mixed_or_incomplete_artifact_pairs_are_rejected(self):
        for key in ('dll', 'bundle', 'serverFiles', 'frontendFiles'):
            with self.subTest(key=key):
                changed = deepcopy(self.after)
                changed['rc9'][key] = deepcopy(self.before['rc9'][key])
                with self.assertRaises(RuntimeError):
                    activation.preserved(self.before, changed, self.files, True)

    def test_previous_configuration_and_recovery_pointer_are_checked(self):
        (Path(self.after['rc9']['artifactDirectory']) / 'previous-config.json').write_bytes(b'changed')
        with self.assertRaises(RuntimeError):
            activation.preserved(self.before, self.after, self.files, True)
        recovered = deepcopy(self.before)
        recovered['rc9']['artifactDirectory'] = 'wrong-version'
        with self.assertRaises(RuntimeError):
            activation.preserved(self.before, recovered, self.files, False)


if __name__ == '__main__':
    unittest.main()
