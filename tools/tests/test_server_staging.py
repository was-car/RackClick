"""Native Windows staging on fresh copies. No DB, application, service or actual QA."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import threading
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT/'tools/windows/Stage-ServerDistribution.ps1'
VERIFY = ROOT/'tools/windows/Test-StagedDistribution.ps1'
HELPER = ROOT/'tools/windows/RackClick.Stage.ps1'
BASELINE = ROOT/'evidence/s1-20261017/seis-tandas-180-185/CANDIDATA185.json'
EXPECTED_BASELINE = '68aca94da20751b690af0c1c6b764a1db1004d3d63be2a12161938a3624d7706'
POWERSHELL = Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())
write_json = lambda p, data: p.write_bytes((json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
tree = lambda root: {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


class ServerStaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert os.name == 'nt' and sha(BASELINE) == EXPECTED_BASELINE
        cls.manifest = read(BASELINE)
        cls.candidate = ROOT/cls.manifest['candidateDirectory']
        protected = [STAGE, VERIFY, HELPER, Path(__file__), BASELINE,
                     ROOT/'tools/windows/Test-RuntimePrerequisites.ps1',
                     ROOT/'tools/windows/Test-ServerDistribution.ps1']
        cls.guards = {str(p): sha(p) for p in protected}
        for kind, files in cls.manifest['distributions'].items():
            assert len(files) == 18
            for name, digest in files.items():
                p = cls.candidate/kind/name
                assert sha(p) == digest
                cls.guards[str(p)] = digest
        cls.home = ROOT/'.local/staging-labs'/('stage188-'+uuid.uuid4().hex)
        cls.home.mkdir(parents=True, exist_ok=False)
        cls.runtime = cls.home/'runtime without SDK Ω'
        cls.runtime.mkdir()
        source = ROOT/'.local/dotnet-10.0.401'
        shutil.copy2(source/'dotnet.exe', cls.runtime/'dotnet.exe')
        shutil.copytree(source/'host', cls.runtime/'host')
        for name in ('Microsoft.NETCore.App', 'Microsoft.AspNetCore.App'):
            shutil.copytree(source/'shared'/name, cls.runtime/'shared'/name)
        sdks = subprocess.run([str(cls.runtime/'dotnet.exe'), '--list-sdks'], capture_output=True, check=True)
        assert not sdks.stdout.strip() and not sdks.stderr.strip()
        cls.runtime_before = tree(cls.runtime)
        cls.pg = ROOT/'.local/postgresql-17.11-4/pgsql/bin'
        cls.calls = []
        cls.fault_injections = []

    @classmethod
    def tearDownClass(cls):
        cls.inputs_unchanged = all(sha(Path(p)) == digest for p, digest in cls.guards.items())
        cls.runtime_unchanged = tree(cls.runtime) == cls.runtime_before
        assert cls.inputs_unchanged and cls.runtime_unchanged

    def fixture(self, label):
        root = self.home/(label+' copia Ω')
        root.mkdir()
        for kind in ('server', 'frontend'):
            shutil.copytree(self.candidate/kind, root/kind)
        manifest = root/'approved-manifest.json'
        shutil.copy2(BASELINE, manifest)
        return dict(ManifestPath=str(manifest), ExpectedManifestSha256=EXPECTED_BASELINE,
                    ServerPath=str(root/'server'), FrontendPath=str(root/'frontend'),
                    DotNetPath=str(self.runtime/'dotnet.exe'), PostgresBinPath=str(self.pg),
                    DestinationPath=str(root/'new staging'))

    def command(self, script, args):
        return [str(POWERSHELL), '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                '-File', str(script), *[x for key, value in args.items() for x in ('-'+key, value)]]

    def check_result(self, process, started, script, expected, code):
        try:
            data = json.loads(process.stdout.decode('utf-8-sig'))
        except (ValueError, UnicodeError):
            data = dict(rawStdout=process.stdout.decode(errors='replace'))
        self.calls.append(dict(case=self._testMethodName, script=script.name, exitCode=process.returncode,
                               seconds=round(time.monotonic()-started, 3), report=data,
                               stderr=process.stderr.decode(errors='replace')))
        self.assertFalse(process.stderr, self.calls[-1])
        self.assertEqual(process.returncode, expected, self.calls[-1])
        self.assertEqual(data['exitCode'], expected)
        self.assertEqual(data['valid'], expected == 0)
        if code is not None:
            self.assertEqual(data['code'], code)
        return data

    def run_check(self, script, args, expected, code=None):
        started = time.monotonic()
        process = subprocess.run(self.command(script, args), capture_output=True, timeout=100,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        return self.check_result(process, started, script, expected, code)

    def verify_args(self, args, receipt):
        return dict(DestinationPath=args['DestinationPath'], ExpectedManifestSha256=EXPECTED_BASELINE,
                    ExpectedReceiptSha256=receipt['receiptSha256'])

    def junction(self, link, target):
        self.assertTrue(link.is_relative_to(self.home) and target.is_relative_to(self.home))
        self.assertFalse(link.exists())
        process = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True)
        self.assertEqual(process.returncode, 0, process.stdout.decode(errors='replace'))
        self.assertTrue(link.is_junction())

    def test_01_genuine_staging_and_independent_readonly_validation(self):
        args = self.fixture('positive')
        report = self.run_check(STAGE, args, 0, 'artifacts_staged')
        target = Path(args['DestinationPath'])
        self.assertEqual(report['verifiedFiles'], 36)
        self.assertEqual(report['receiptSha256'], sha(target/'stage-receipt.json'))
        self.assertEqual(read(target/'stage-state.json')['status'], 'staged')
        self.assertEqual({p.name for p in target.iterdir()}, {'server','frontend','manifest.json','stage-state.json','stage-receipt.json'})
        before = tree(target)
        self.run_check(VERIFY, self.verify_args(args, report), 0, 'staging_verified')
        self.assertEqual(tree(target), before)

    def test_02_source_corruption_runtime_invalid_and_untrusted_manifest(self):
        args = self.fixture('source-corrupt')
        with (Path(args['FrontendPath'])/'app.js').open('ab') as output:
            output.write(b'\n/* own fixture corruption */')
        self.run_check(STAGE, args, 1, 'integrity_artifact_hash_mismatch')
        self.assertFalse(Path(args['DestinationPath']).exists())
        args = self.fixture('runtime-invalid')
        invalid_root = self.home/'invalid-runtime'; invalid_root.mkdir()
        invalid = invalid_root/'not-dotnet.exe'; invalid.write_bytes(b'not a PE executable')
        args['DotNetPath'] = str(invalid)
        self.run_check(STAGE, args, 1, 'runtime_binary_architecture_invalid')
        self.assertFalse(Path(args['DestinationPath']).exists())
        args = self.fixture('manifest-untrusted')
        args['ExpectedManifestSha256'] = '0'*64
        self.run_check(STAGE, args, 2, 'integrity_manifest_untrusted')
        self.assertFalse(Path(args['DestinationPath']).exists())

    def test_03_existing_sentinel_and_competing_creators(self):
        args = self.fixture('existing')
        target = Path(args['DestinationPath']); target.mkdir()
        (target/'sentinel.txt').write_bytes(b'never overwritten')
        before = tree(target)
        self.run_check(STAGE, args, 1, 'destination_exists')
        self.assertEqual(tree(target), before)
        args = self.fixture('concurrent')
        started = time.monotonic()
        processes = [subprocess.Popen(self.command(STAGE, args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      creationflags=subprocess.CREATE_NO_WINDOW) for _ in range(2)]
        completed = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=100)
            completed.append(subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr))
        self.assertEqual(sorted(p.returncode for p in completed), [0,1])
        for process in completed:
            result = self.check_result(process, started, STAGE, process.returncode,
                                       'artifacts_staged' if process.returncode == 0 else 'destination_exists')
            if process.returncode == 0:
                successful = result
        self.run_check(VERIFY, self.verify_args(args, successful), 0, 'staging_verified')

    def test_04_receipt_copy_and_state_tampering_are_rejected(self):
        args = self.fixture('tampering')
        report = self.run_check(STAGE, args, 0, 'artifacts_staged')
        target = Path(args['DestinationPath'])
        receipt = target/'stage-receipt.json'; original = receipt.read_bytes()
        receipt.write_bytes(original+b' ')
        self.run_check(VERIFY, self.verify_args(args, report), 2, 'receipt_untrusted')
        receipt.write_bytes(original)  # Only this new fixture, not a real staged installation.
        with (target/'frontend/app.js').open('ab') as output:
            output.write(b'\n/* staged fixture corruption */')
        self.run_check(VERIFY, self.verify_args(args, report), 1, 'integrity_artifact_hash_mismatch')
        shutil.copyfile(self.candidate/'frontend/app.js', target/'frontend/app.js')
        state = read(target/'stage-state.json'); state['status'] = 'failed'
        write_json(target/'stage-state.json', state)
        self.run_check(VERIFY, self.verify_args(args, report), 1, 'staging_not_complete')

    def test_05_reparse_overlap_and_relative_paths(self):
        args = self.fixture('overlap')
        args['DestinationPath'] = str(Path(args['ServerPath'])/'new staging')
        self.run_check(STAGE, args, 2, 'source_destination_overlap')
        args = self.fixture('relative'); args['DestinationPath'] = 'relative/staging'
        self.run_check(STAGE, args, 2, 'path_invalid')
        args = self.fixture('short-alias'); args['DestinationPath'] = str(self.home/'SHORT~1'/'staging')
        self.run_check(STAGE, args, 2, 'path_invalid')
        args = self.fixture('junction-parent')
        alias = self.home/'parent alias'; self.junction(alias, Path(args['ServerPath']).parent)
        args['DestinationPath'] = str(alias/'new staging')
        self.run_check(STAGE, args, 2, 'reparse_path_rejected')
        args = self.fixture('junction-source')
        outside = self.home/'outside-data'; outside.mkdir(); (outside/'sentinel.txt').write_bytes(b'not touched')
        self.junction(Path(args['FrontendPath'])/'external', outside)
        self.run_check(STAGE, args, 2, 'integrity_reparse_path_rejected')
        self.assertFalse(Path(args['DestinationPath']).exists())
        self.assertEqual((outside/'sentinel.txt').read_bytes(), b'not touched')

    def test_06_postcopy_failure_is_preserved_without_success_receipt(self):
        args = self.fixture('postcopy-failure')
        target = Path(args['DestinationPath'])
        stopped = threading.Event()
        injected = []
        def corrupt_owned_fixture():
            victim = target/'frontend/app.js'
            while not stopped.is_set():
                try:
                    if victim.is_file():
                        with victim.open('ab') as output:
                            output.write(b'\n/* controlled concurrent mutation of NEW fixture */')
                        injected.append(str(victim))
                        return
                except (PermissionError, FileNotFoundError):
                    pass
                stopped.wait(0.001)
        thread = threading.Thread(target=corrupt_owned_fixture, daemon=True); thread.start()
        try:
            self.run_check(STAGE, args, 1, 'integrity_artifact_hash_mismatch')
        finally:
            stopped.set(); thread.join(timeout=5)
            self.fault_injections.append(dict(case=self._testMethodName, injected=injected))
        self.assertEqual(len(injected), 1, 'Fault was not injected; no false PASS')
        self.assertTrue(target.is_dir())
        state = read(target/'stage-state.json')
        self.assertEqual(state['status'], 'failed')
        self.assertEqual(state['verifiedFiles'], 0)
        self.assertFalse((target/'stage-receipt.json').exists())
        # An incomplete staging root must not be mistaken for an accepted receipt.
        self.run_check(VERIFY, dict(DestinationPath=str(target), ExpectedManifestSha256=EXPECTED_BASELINE,
                                   ExpectedReceiptSha256='0'*64), 1, 'staging_root_contents_invalid')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--cases', nargs='*')
    options = parser.parse_args()
    evidence = Path(options.evidence).resolve(); evidence.mkdir(parents=True, exist_ok=False)
    # Persist actual exact source bytes BEFORE any product/native invocation.
    snapshots = evidence/'sources-before'; snapshots.mkdir()
    for source in (STAGE, VERIFY, HELPER, Path(__file__)):
        (snapshots/source.name).write_bytes(source.read_bytes())
    suite = (unittest.TestSuite(ServerStaging(name) for name in options.cases)
             if options.cases else unittest.defaultTestLoader.loadTestsFromTestCase(ServerStaging))
    started = time.monotonic()
    with (evidence/'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    report = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(),
                  testsRun=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                  successful=result.wasSuccessful(), seconds=round(time.monotonic()-started,3),
                  fixture=str(getattr(ServerStaging,'home','not initialized')),
                  sourceHashes=getattr(ServerStaging,'guards',{}),
                  inputsUnchanged=getattr(ServerStaging,'inputs_unchanged',False),
                  runtimeUnchanged=getattr(ServerStaging,'runtime_unchanged',False),
                  calls=getattr(ServerStaging,'calls',[]), faultInjections=getattr(ServerStaging,'fault_injections',[]),
                  databaseQueries=0, appExecutions=0, serviceOperations=0, realQaActions=0)
    write_json(evidence/'result.json', report)
    print(json.dumps({key: report[key] for key in ('testsRun','failures','errors','successful','seconds','fixture')}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
