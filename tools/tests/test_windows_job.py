"""Native Windows process-tree cleanup tests, using only processes created here."""
import concurrent.futures
import ctypes
from ctypes import wintypes as w
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/windows'))
from windows_job import PrivateJob, run_isolated


@unittest.skipUnless(os.name == 'nt', 'Native Windows only')
class JobTests(unittest.TestCase):
    def setUp(self):
        self.directory = ROOT / '.local/job-tests' / uuid.uuid4().hex
        self.directory.mkdir(parents=True, exist_ok=False)
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        self.api.OpenProcess.restype = w.HANDLE
        self.api.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        self.api.WaitForSingleObject.restype = w.DWORD
        self.api.CloseHandle.argtypes = [w.HANDLE]
        self.api.CloseHandle.restype = w.BOOL

    def test_exit_code_propagates(self):
        result = run_isolated([sys.executable, '-c', 'raise SystemExit(7)'], timeout=10)
        self.assertEqual(result.returncode, 7)

    def exercise_descendant(self, timeout):
        marker, release = self.directory / 'child.pid', self.directory / 'release'
        script = self.directory / 'parent.py'
        script.write_text('''import pathlib, subprocess, sys, time
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], creationflags=subprocess.CREATE_NO_WINDOW)
pathlib.Path(sys.argv[1]).write_text(str(child.pid))
while not pathlib.Path(sys.argv[2]).exists(): time.sleep(.02)
''', encoding='utf-8')
        sentinel = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], creationflags=subprocess.CREATE_NO_WINDOW)
        handle = None
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_isolated, [sys.executable, str(script), str(marker), str(release)], timeout=3 if timeout else 15)
                deadline = time.monotonic() + 2
                while not marker.exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(marker.exists(), 'Fixture child did not start')
                # Open while the child is alive; holding this handle prevents checking a reused PID.
                handle = self.api.OpenProcess(0x00100000, False, int(marker.read_text()))
                self.assertTrue(handle)
                if timeout:
                    with self.assertRaises(subprocess.TimeoutExpired):
                        future.result(timeout=20)
                else:
                    release.write_text('release', encoding='ascii')
                    self.assertEqual(future.result(timeout=20).returncode, 0)
                self.assertEqual(self.api.WaitForSingleObject(handle, 10_000), 0, 'Owned descendant survived job close')
                self.assertIsNone(sentinel.poll(), 'Unrelated process must survive')
        finally:
            if handle:
                self.api.CloseHandle(handle)
            sentinel.terminate()
            sentinel.wait(timeout=10)

    def test_timeout_stops_descendants_and_preserves_unrelated_process(self):
        self.exercise_descendant(True)

    def test_success_stops_remaining_descendants_and_preserves_unrelated_process(self):
        self.exercise_descendant(False)

    def test_assignment_failure_never_opens_gate(self):
        marker = self.directory / 'must-not-exist'
        script = self.directory / 'must-not-run.py'
        script.write_text('import pathlib,sys; pathlib.Path(sys.argv[1]).write_text("ran")', encoding='ascii')
        with patch.object(PrivateJob, 'assign', side_effect=OSError('fixture assignment denied')):
            with self.assertRaises(OSError):
                run_isolated([sys.executable, str(script), str(marker)], timeout=10)
        self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
