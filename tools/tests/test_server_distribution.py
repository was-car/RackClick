"""Native Windows PowerShell5.1 artifact checks on new disposable copies; no DB/app/QA."""
import argparse
import copy
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'tools/windows/Test-ServerDistribution.ps1'
HELPER = ROOT / 'tools/windows/Test-RuntimePrerequisites.ps1'
BASELINE = ROOT / 'evidence/s1-20261017/seis-tandas-180-185/CANDIDATA185.json'
EXPECTED_BASELINE = '68aca94da20751b690af0c1c6b764a1db1004d3d63be2a12161938a3624d7706'
POWERSHELL = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())
json_write = lambda p, data: p.write_bytes((json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))


class ServerDistribution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert os.name == 'nt' and sha(BASELINE) == EXPECTED_BASELINE
        cls.manifest = read(BASELINE)
        cls.candidate = ROOT / cls.manifest['candidateDirectory']
        cls.guards = {str(p): sha(p) for p in (SCRIPT, HELPER, BASELINE, Path(__file__))}
        for kind, files in cls.manifest['distributions'].items():
            assert len(files) == 18
            for name, digest in files.items():
                p = cls.candidate / kind / name
                assert sha(p) == digest
                cls.guards[str(p)] = digest
        cls.home = ROOT / '.local/integrity-check-labs' / ('integrity187-' + uuid.uuid4().hex)
        cls.home.mkdir(parents=True, exist_ok=False)
        cls.calls = []

    @classmethod
    def tearDownClass(cls):
        cls.inputs_unchanged = all(sha(Path(p)) == digest for p, digest in cls.guards.items())
        assert cls.inputs_unchanged

    def fixture(self, label):
        target = self.home / (label + ' copia Ω')
        target.mkdir()
        for kind in ('server', 'frontend'):
            shutil.copytree(self.candidate / kind, target / kind)
        manifest = target / 'manifest.json'
        shutil.copy2(BASELINE, manifest)
        return dict(ManifestPath=str(manifest), ExpectedManifestSha256=EXPECTED_BASELINE,
                    ServerPath=str(target / 'server'), FrontendPath=str(target / 'frontend'))

    def run_check(self, args, expected, code=None):
        started = time.monotonic()
        command = [str(POWERSHELL), '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                   '-File', str(SCRIPT), *[x for name, val in args.items() for x in ('-'+name, val)]]
        p = subprocess.run(command, capture_output=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        # Persist every result, including failures, before assertions. Product reports contain ASCII codes.
        try:
            data = json.loads(p.stdout.decode('utf-8-sig'))
        except (ValueError, UnicodeError):
            data = dict(rawStdout=p.stdout.decode(errors='replace'))
        self.calls.append(dict(case=self._testMethodName, exitCode=p.returncode,
                               seconds=round(time.monotonic()-started, 3), report=data,
                               stderr=p.stderr.decode(errors='replace')))
        self.assertFalse(p.stderr, self.calls[-1]['stderr'])
        self.assertEqual(p.returncode, expected, data)
        self.assertEqual(data['exitCode'], expected)
        self.assertEqual(data['valid'], expected == 0)
        if code is not None:
            self.assertEqual(data['code'], code)
        return data

    def altered_manifest(self, args, change):
        # Self-hashes here are ONLY for synthetic negative fixtures, never release approval.
        data = copy.deepcopy(self.manifest)
        change(data)
        p = Path(args['ManifestPath'])
        json_write(p, data)
        args['ExpectedManifestSha256'] = sha(p)

    def junction(self, link, target):
        self.assertTrue(link.is_relative_to(self.home) and target.is_relative_to(self.home))
        self.assertFalse(link.exists())
        p = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True)
        self.assertEqual(p.returncode, 0, p.stdout.decode(errors='replace'))
        self.assertTrue(link.is_junction())

    def test_01_genuine_copy_and_explicit_roots(self):
        args = self.fixture('positive')
        data = self.run_check(args, 0, 'artifacts_verified')
        self.assertEqual((data['verifiedFiles'], data['serverFiles'], data['frontendFiles']), (36, 18, 18))
        self.assertEqual(data['manifestSha256'], EXPECTED_BASELINE)
        self.assertNotEqual(Path(args['ServerPath']), self.candidate / 'server')

    def test_02_corruption_missing_and_hidden_extra(self):
        args = self.fixture('corrupt')
        with (Path(args['FrontendPath'])/'app.js').open('ab') as stream:
            stream.write(b'\n/* test fixture corruption */')
        self.run_check(args, 1, 'artifact_hash_mismatch')
        args = self.fixture('missing')
        victim = Path(args['ServerPath'])/'Npgsql.dll'
        self.assertTrue(victim.is_relative_to(self.home))
        victim.unlink()  # Only one file of this new private copy, never an existing distribution.
        self.run_check(args, 1, 'distribution_files_missing')
        args = self.fixture('hidden')
        extra = Path(args['FrontendPath'])/'hidden-test.txt'
        extra.write_bytes(b'synthetic extra')
        self.assertTrue(ctypes.windll.kernel32.SetFileAttributesW(str(extra), 2))
        self.run_check(args, 1, 'distribution_files_extra')

    def test_03_untrusted_malformed_and_unsupported_manifest(self):
        args = self.fixture('untrusted')
        args['ExpectedManifestSha256'] = '0'*64
        self.run_check(args, 2, 'manifest_untrusted')
        args = self.fixture('malformed')
        p = Path(args['ManifestPath']); p.write_bytes(b'{invalid json')
        args['ExpectedManifestSha256'] = sha(p)
        self.run_check(args, 2, 'manifest_invalid')
        args = self.fixture('schema')
        self.altered_manifest(args, lambda data: data.update(schema=8))
        self.run_check(args, 2, 'manifest_distribution_unsupported')

    def test_04_unsafe_manifest_names(self):
        for index, name in enumerate(('../outside.txt', 'app.js:stream', 'app.js.', 'app.js ', 'CON.txt')):
            args = self.fixture('unsafe'+str(index))
            def change(data):
                digest = data['distributions']['frontend'].pop('app.js')
                data['distributions']['frontend'][name] = digest
            self.altered_manifest(args, change)
            self.run_check(args, 2, 'manifest_path_unsafe')
        args = self.fixture('casecollision')
        self.altered_manifest(args, lambda data: data['distributions']['frontend'].update({'APP.JS': 'a'*64}))
        self.run_check(args, 2)  # ConvertFrom-Json itself may reject the case collision on PS5.1.

    def test_05_reparse_roots_ancestors_and_descendants(self):
        args = self.fixture('childjunction')
        target = self.home/'outside-child'; target.mkdir(); (target/'sentinel.txt').write_bytes(b'not enumerated')
        self.junction(Path(args['FrontendPath'])/'external', target)
        self.run_check(args, 2, 'reparse_path_rejected')
        args = self.fixture('rootjunction')
        alias = self.home/'root-alias'; self.junction(alias, Path(args['ServerPath']))
        args['ServerPath'] = str(alias)
        self.run_check(args, 2, 'reparse_path_rejected')
        args = self.fixture('ancestorjunction')
        alias = self.home/'parent-alias'; self.junction(alias, Path(args['ServerPath']).parent)
        args['FrontendPath'] = str(alias/'frontend')
        self.run_check(args, 2, 'reparse_path_rejected')

    def test_06_invalid_inputs_overlap_and_missing_directory(self):
        args = self.fixture('relative'); args['ServerPath'] = 'relative/server'
        self.run_check(args, 2, 'input_invalid')
        args = self.fixture('overlap'); args['FrontendPath'] = args['ServerPath']
        self.run_check(args, 2, 'distribution_roots_overlap')
        args = self.fixture('absentroot'); args['FrontendPath'] = str(self.home/'does-not-exist')
        self.run_check(args, 1, 'distribution_directory_missing')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--cases', nargs='*')
    options = parser.parse_args()
    evidence = Path(options.evidence).resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    suite = (unittest.TestSuite(ServerDistribution(name) for name in options.cases)
             if options.cases else unittest.defaultTestLoader.loadTestsFromTestCase(ServerDistribution))
    started = time.monotonic()
    with (evidence/'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    report = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(),
                  testsRun=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                  successful=result.wasSuccessful(), seconds=round(time.monotonic()-started, 3),
                  fixture=str(getattr(ServerDistribution, 'home', 'not initialized')),
                  sourceHashes=getattr(ServerDistribution, 'guards', {}),
                  inputsUnchanged=getattr(ServerDistribution, 'inputs_unchanged', False),
                  calls=getattr(ServerDistribution, 'calls', []), databaseQueries=0, appExecutions=0)
    json_write(evidence/'result.json', report)
    print(json.dumps({k: report[k] for k in ('testsRun','failures','errors','successful','seconds','fixture')}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
