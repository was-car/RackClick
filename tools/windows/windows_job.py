"""Run a Windows test command and its descendants in a private kill-on-close job.

A small Python gate waits on stdin before starting the command. Assignment to
the job happens before the gate opens, so no child escapes a startup race.
No process is selected by name; the job handle owns only this invocation.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes as w
import os
from pathlib import Path
import subprocess
import sys


class BasicLimits(ctypes.Structure):
    _fields_ = [('PerProcessUserTimeLimit', ctypes.c_longlong), ('PerJobUserTimeLimit', ctypes.c_longlong),
                ('LimitFlags', w.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', w.DWORD),
                ('Affinity', ctypes.c_size_t), ('PriorityClass', w.DWORD), ('SchedulingClass', w.DWORD)]


class IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in ('ReadOperationCount', 'WriteOperationCount',
                'OtherOperationCount', 'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]


class ExtendedLimits(ctypes.Structure):
    _fields_ = [('BasicLimitInformation', BasicLimits), ('IoInfo', IoCounters),
                ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]


class PrivateJob:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('Windows Job Objects are required by this native test runner')
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        signatures = {
            'CreateJobObjectW': ([ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
            'SetInformationJobObject': ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
            'AssignProcessToJobObject': ([w.HANDLE, w.HANDLE], w.BOOL),
            'CloseHandle': ([w.HANDLE], w.BOOL),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = args, result
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def assign(self, process):
        # Popen's process handle avoids PID-reuse races. The gate has not opened.
        if not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            if not self.api.CloseHandle(self.handle):
                raise ctypes.WinError(ctypes.get_last_error())
            self.handle = None


def run_isolated(command, *, cwd=None, env=None, stdout=None, stderr=None, timeout=None):
    """Like subprocess.run with file output; closes all owned descendants at exit."""
    if stdout == subprocess.PIPE or stderr == subprocess.PIPE:
        raise ValueError('Use file outputs; long-lived descendants must not inherit captured pipes')
    job, process = PrivateJob(), None
    assigned = False
    try:
        process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--gate', *map(str, command)],
                                   cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                   creationflags=subprocess.CREATE_NO_WINDOW, close_fds=True)
        job.assign(process)
        assigned = True
        process.stdin.write(b'G')
        process.stdin.close()
        return subprocess.CompletedProcess(command, process.wait(timeout=timeout))
    finally:
        try:
            job.close()  # terminates this gate/command/descendants, including on timeout or parent error
        finally:
            if process is not None:
                if not assigned and process.poll() is None:
                    process.kill()  # only our unopened gate; it cannot have started the command
                if process.stdin is not None and not process.stdin.closed:
                    process.stdin.close()
                process.wait(timeout=15)


if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] != '--gate' or sys.stdin.buffer.read(1) != b'G':
        raise SystemExit(2)
    # The parent owns the non-inheritable job handle. Actual commands never see the gate's pipe.
    raise SystemExit(subprocess.run(sys.argv[2:], stdin=subprocess.DEVNULL,
                                    creationflags=subprocess.CREATE_NO_WINDOW).returncode)
