"""Windows5.1 native dependency checks; no DB, app, network or actual QA profile."""
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
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'tools/windows/Test-RuntimePrerequisites.ps1'
BASELINE = ROOT / 'evidence/s1-20261017/seis-tandas-180-185/CANDIDATA185.json'
POWERSHELL = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
tree = lambda p: {x.relative_to(p).as_posix(): sha(x) for x in sorted(p.rglob('*')) if x.is_file()}


class RuntimePrerequisites(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = read(BASELINE)
        cls.config = ROOT / Path(cls.manifest['serverDll']).parent / 'RackClick.Server.runtimeconfig.json'
        cls.source_dotnet = ROOT / '.local/dotnet-10.0.401'
        cls.pg = ROOT / '.local/postgresql-17.11-4/pgsql/bin'
        cls.home = ROOT / '.local/runtime-preflight-labs' / ('runtime186-' + uuid.uuid4().hex)
        cls.home.mkdir(parents=True, exist_ok=False)
        cls.runtime = cls.home / 'runtime without SDK Ω'
        cls.runtime.mkdir()
        shutil.copy2(cls.source_dotnet / 'dotnet.exe', cls.runtime / 'dotnet.exe')
        shutil.copytree(cls.source_dotnet / 'host', cls.runtime / 'host')
        for name in ('Microsoft.NETCore.App', 'Microsoft.AspNetCore.App'):
            shutil.copytree(cls.source_dotnet / 'shared' / name, cls.runtime / 'shared' / name)
        cls.runtime_before = tree(cls.runtime)
        sdks = subprocess.run([str(cls.runtime / 'dotnet.exe'), '--list-sdks'], capture_output=True, check=True)
        assert not sdks.stdout.strip() and not sdks.stderr.strip()
        cls.calls = []

    @classmethod
    def tearDownClass(cls):
        cls.runtime_unchanged = tree(cls.runtime) == cls.runtime_before
        assert cls.runtime_unchanged

    def run_ps(self, args, expected, code=None):
        started = time.monotonic()
        p = subprocess.run([str(POWERSHELL), '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', *args],
                           capture_output=True, timeout=40, creationflags=subprocess.CREATE_NO_WINDOW)
        # Reports use ASCII codes/versions; no raw tool output or exception strings are published.
        self.assertFalse(p.stderr, p.stderr.decode(errors='replace'))
        data = json.loads(p.stdout.decode('utf-8-sig'))
        self.calls.append(dict(case=self._testMethodName, exitCode=p.returncode,
                               seconds=round(time.monotonic()-started,3), report=data))
        self.assertEqual(p.returncode, expected)
        if code is not None:
            self.assertEqual(data['exitCode'], expected)
            self.assertEqual(data['code'], code)
        return data

    def command(self, **overrides):
        values = dict(DotNetPath=str(self.runtime / 'dotnet.exe'), PostgresBinPath=str(self.pg), RuntimeConfigPath=str(self.config))
        values.update(overrides)
        return ['-File', str(SCRIPT), *[v for k, val in values.items() for v in ('-'+k, val)]]

    def test_01_real_runtime_without_sdk_and_three_pg_tools(self):
        data = self.run_ps(self.command(), 0, 'requirements_present')
        self.assertTrue(data['ready'])
        self.assertEqual({f['name'] for f in data['frameworks']}, {'Microsoft.NETCore.App','Microsoft.AspNetCore.App'})
        self.assertEqual({p['name'] for p in data['postgres']}, {'postgres','pg_dump','pg_restore'})
        self.assertTrue(all(p['version']=='17.11' for p in data['postgres']))
        self.assertEqual(data['runtimeConfigSha256'], sha(self.config))
        for key in ['sdkRequired','nodeRequired','gitRequired','pythonRequired']:
            self.assertFalse(data[key])
        self.assertFalse((self.runtime/'sdk').exists())

    def test_02_absent_aspnet_is_blocked_with_core_present(self):
        source = (self.runtime/'shared/Microsoft.AspNetCore.App').resolve()
        target = (self.home/'held-aspnet').resolve()
        # Only this freshly created private fixture is moved; never the approved source runtime.
        self.assertTrue(source.is_relative_to(self.home.resolve()) and target.is_relative_to(self.home.resolve()))
        self.assertFalse(target.exists())
        source.rename(target)
        try:
            data = self.run_ps(self.command(), 1, 'framework_missing')
            self.assertEqual(data['missing'], ['Microsoft.AspNetCore.App'])
            self.assertFalse(data['ready'])
        finally:
            target.rename(source)

    def test_03_pg_version_mismatch_is_blocked(self):
        data = self.run_ps(self.command(PostgresVersion='17.10'), 1, 'postgres_version_incompatible')
        self.assertEqual(data['postgres'][0]['version'], '17.11')
        self.assertFalse(data['ready'])

    def test_04_missing_dump_and_missing_host_are_blocked(self):
        incomplete = self.home/'incomplete-pg'; incomplete.mkdir()
        for name in ['postgres.exe','pg_restore.exe']:
            shutil.copy2(self.pg/name,incomplete/name)
        data=self.run_ps(self.command(PostgresBinPath=str(incomplete)),1,'executable_missing')
        self.assertEqual(data['missing'],['pg_dump'])
        data=self.run_ps(self.command(DotNetPath=str(self.home/'absent.exe')),1,'executable_missing')
        self.assertEqual(data['missing'],['dotnet'])
        bad=self.home/'x86-header.exe'
        import struct
        header=bytearray(128);struct.pack_into('<H',header,0,0x5a4d);struct.pack_into('<I',header,60,64)
        struct.pack_into('<IH',header,64,0x00004550,0x014c);bad.write_bytes(header)
        self.run_ps(self.command(DotNetPath=str(bad)),1,'binary_architecture_invalid')
        # Read failures are indeterminate, not evidence of an incompatible architecture.
        locked=self.home/'locked-copy-dotnet.exe';shutil.copy2(self.runtime/'dotnet.exe',locked)
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        kernel.CreateFileW.restype=wintypes.HANDLE
        kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
        handle=kernel.CreateFileW(str(locked),0x80000000,0,None,3,0x80,None)
        self.assertNotEqual(handle,ctypes.c_void_p(-1).value)
        try:
            self.run_ps(self.command(DotNetPath=str(locked)),2,'verification_failed')
        finally:
            self.assertTrue(kernel.CloseHandle(handle))

    def test_05_invalid_config_and_relative_input_are_indeterminate(self):
        invalid=self.home/'invalid.runtimeconfig.json';invalid.write_text('{bad',encoding='utf-8')
        self.run_ps(self.command(RuntimeConfigPath=str(invalid)),2,'runtime_config_invalid')
        unsupported=self.home/'unsupported.runtimeconfig.json'
        config=read(self.config);config['runtimeOptions']['rollForward']='Major'
        unsupported.write_text(json.dumps(config),encoding='utf-8')
        self.run_ps(self.command(RuntimeConfigPath=str(unsupported)),2,'runtime_config_unsupported')
        self.run_ps(self.command(DotNetPath='dotnet.exe'),2,'input_invalid')
        self.run_ps(self.command(DotNetPath='C:dotnet.exe'),2,'input_invalid')
        self.run_ps(self.command(DotNetPath=r'\\unreachable-test\share\dotnet.exe'),2,'input_invalid')

    def test_06_parser_does_not_accept_prerelease_or_new_minor(self):
        helper=self.home/'parser.ps1'
        helper.write_text(". '"+SCRIPT.as_posix()+"'\n"+'''$results=@()
foreach($listing in @(
  "Microsoft.NETCore.App 10.0.12 [C:\\core]`nMicrosoft.AspNetCore.App 10.0.12 [C:\\web]",
  "Microsoft.NETCore.App 10.0.12 [C:\\core]`nMicrosoft.AspNetCore.App 10.1.0 [C:\\web]",
  "Microsoft.NETCore.App 10.0.12 [C:\\core]`nMicrosoft.AspNetCore.App 10.0.13-preview.1 [C:\\web]",
  "not a runtime listing")) { $results+=Get-RuntimeFrameworkInventory $listing }
@{results=$results}|ConvertTo-Json -Depth 8 -Compress
''',encoding='utf-8')
        results=self.run_ps(['-File',str(helper)],0)['results']
        self.assertEqual(results[0]['missing'],[])
        self.assertEqual(results[1]['missing'],['Microsoft.AspNetCore.App'])
        self.assertEqual(results[2]['missing'],['Microsoft.AspNetCore.App'])
        self.assertEqual(results[3]['code'],'probe_output_invalid')

    def test_07_timeout_stops_only_its_own_probe(self):
        helper=self.home/'timeout.ps1'
        helper.write_text(". '"+SCRIPT.as_posix()+"'\nInvoke-RuntimeVersionProbe '"+POWERSHELL.as_posix()+"' '-NoProfile -NonInteractive -Command Start-Sleep -Seconds 5' 200 | ConvertTo-Json -Compress\n",encoding='utf-8')
        data=self.run_ps(['-File',str(helper)],0)
        self.assertEqual(data['code'],'probe_timeout');self.assertTrue(data['ownedProcessStopped'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--case',action='append')
    args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False)
    sources=[SCRIPT,Path(__file__),ROOT/'development/toolchain.lock.json',BASELINE]
    inputs={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
    started=time.monotonic()
    suite=unittest.TestSuite(RuntimePrerequisites(n) for n in args.case) if args.case else unittest.defaultTestLoader.loadTestsFromTestCase(RuntimePrerequisites)
    with (args.evidence/'tests.log').open('w',encoding='utf-8') as out:
        result=unittest.TextTestRunner(stream=out,verbosity=2).run(suite)
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,
                successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),
                seconds=round(time.monotonic()-started,3),inputs=inputs,
                inputsUnchanged=inputs=={p.relative_to(ROOT).as_posix():sha(p) for p in sources},
                sdkFreeFixtureRuntimeUnchanged=getattr(RuntimePrerequisites,'runtime_unchanged',False),
                actualQaAccessed=False,databaseStarted=False,applicationStarted=False,
                fixtureDirectory=getattr(RuntimePrerequisites,'home',ROOT).relative_to(ROOT).as_posix(),
                calls=getattr(RuntimePrerequisites,'calls',[]))
    (args.evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['testsRun','successful','failures','errors','seconds','inputsUnchanged','sdkFreeFixtureRuntimeUnchanged']}))
    return 0 if report['successful'] and report['inputsUnchanged'] and report['sdkFreeFixtureRuntimeUnchanged'] else 1


if __name__=='__main__':
    sys.exit(main())
