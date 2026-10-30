"""Owned process/gate native tests; real instance happy path belongs to root integration."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
PS = Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
PROCESS = ROOT/'tools/windows/RackClick.Process.ps1'
GATE = ROOT/'tools/windows/RackClick.Process.Gate.ps1'
START = ROOT/'tools/windows/Start-RackClickLabInstance.ps1'
STOP = ROOT/'tools/windows/Stop-RackClickLabInstance.ps1'
SOURCES = (PROCESS,GATE,START,STOP,Path(__file__))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
write_json = lambda p,d: p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
ps_cmd = lambda script,args=(): [str(PS),'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),*map(str,args)]

DRIVER = r'''
param([string]$Mode,[string]$Helper,[string]$PrivateRoot,[string]$Python,[string]$Payload,[string]$Tree,[string]$Marker)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
. $Helper
$logs=New-RackClickProcessPrivateDirectory (Join-Path $PrivateRoot ('driver-'+[guid]::NewGuid().ToString('N')))
if ($Mode -eq 'Roundtrip') {
 $values=@($Payload,'alpha "quoted" text','backslash\','',"Unicode Ω 漢")
 $handle=Start-RackClickOwnedProcess -Executable $Python -Arguments $values -WorkingDirectory $logs -Environment @{PYTHONUTF8='1';RACKCLICK_PROCESS_TEST='synthetic marker Ω'} -InputText "Unicode input Ω 漢`nsecond line`n" -LogDirectory $logs -Label 'roundtrip'
 $result=Wait-RackClickOwnedProcess -Handle $handle -TimeoutSeconds 15
 Assert-RackClickProcessPrivateAcl $handle.RequestPath
 Assert-RackClickProcessPrivateAcl $handle.StdoutPath
 Assert-RackClickProcessPrivateAcl $handle.StderrPath
 @{exitCode=$result.exitCode;payload=($result.stdout | ConvertFrom-Json);stderrEmpty=($result.stderr.Length -eq 0);requestPath=$handle.RequestPath;stdoutPath=$handle.StdoutPath;stderrPath=$handle.StderrPath;jobClosed=($handle.Job -eq [IntPtr]::Zero)} | ConvertTo-Json -Depth 8 -Compress
} elseif ($Mode -eq 'Timeout') {
 $handle=Start-RackClickOwnedProcess -Executable $Python -Arguments @($Tree,$Marker) -WorkingDirectory $logs -Environment @{PYTHONUTF8='1'} -LogDirectory $logs -Label 'timeout'
 $gateMembership=Test-RackClickOwnedProcessMembership -Handle $handle -ProcessId $handle.Process.Id
 $outsideMembership=Test-RackClickOwnedProcessMembership -Handle $handle -ProcessId $PID
 $result=Wait-RackClickOwnedProcess -Handle $handle -TimeoutSeconds 2
 @{exitCode=$result.exitCode;gateExited=$handle.Process.HasExited;jobClosed=($handle.Job -eq [IntPtr]::Zero);requestPath=$handle.RequestPath;gateMembership=$gateMembership;outsideMembership=$outsideMembership} | ConvertTo-Json -Compress
} elseif ($Mode -eq 'Crash') {
 $handle=Start-RackClickOwnedProcess -Executable $Python -Arguments @($Tree,$Marker) -WorkingDirectory $logs -Environment @{PYTHONUTF8='1'} -LogDirectory $logs -Label 'crash'
 @{event='owned-started';gateId=$handle.Process.Id;requestPath=$handle.RequestPath} | ConvertTo-Json -Compress
 [Console]::Out.Flush()
 while ($true) { Start-Sleep -Milliseconds 100 }
} else { throw 'invalid driver mode' }
'''

PAYLOAD = """import json,os,sys
print(json.dumps(dict(arguments=sys.argv[1:],input=sys.stdin.read(),marker=os.environ.get('RACKCLICK_PROCESS_TEST'),cwd=os.getcwd()),ensure_ascii=False))
"""
HEARTBEAT = """import sys,time
with open(sys.argv[1],'ab',buffering=0) as target:
    while True:
        target.write(b'x')
        time.sleep(.025)
"""
TREE = """import subprocess,sys,time
from pathlib import Path
p=subprocess.Popen([sys.executable,str(Path(__file__).with_name('heartbeat.py')),sys.argv[1]],creationflags=subprocess.CREATE_NO_WINDOW)
print('descendant-started',flush=True)
while True: time.sleep(.1)
"""


class InstanceLauncher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert os.name == 'nt'
        cls.home = ROOT/'.local/launcher-labs'/('launcher228-'+uuid.uuid4().hex)
        cls.home.mkdir(parents=True,exist_ok=False)
        cls.private = cls.home/'private Ω'
        cls.driver = cls.home/'driver.ps1'; cls.driver.write_bytes(b'\xef\xbb\xbf'+DRIVER.encode('utf-8'))
        cls.payload = cls.home/'payload.py'; cls.payload.write_text(PAYLOAD,encoding='utf-8')
        cls.tree = cls.home/'tree.py'; cls.tree.write_text(TREE,encoding='utf-8')
        cls.heartbeat = cls.home/'heartbeat.py'; cls.heartbeat.write_text(HEARTBEAT,encoding='utf-8')
        code="$ProgressPreference='SilentlyContinue'; . '"+str(PROCESS)+"'; $null=New-RackClickProcessPrivateDirectory '"+str(cls.private)+"'"
        p=subprocess.run([str(PS),'-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(code.encode('utf-16le')).decode()],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        assert p.returncode == 0 and not p.stderr, (p.returncode,p.stderr.decode(errors='replace'))
        cls.guards = {str(p):sha(p) for p in SOURCES+(ROOT/'tools/windows/RackClick.Instance.ps1',)}
        cls.calls=[]

    @classmethod
    def tearDownClass(cls):
        cls.sources_unchanged=all(sha(Path(p))==digest for p,digest in cls.guards.items())
        assert cls.sources_unchanged

    def driver_args(self,mode,marker):
        return ['-Mode',mode,'-Helper',str(PROCESS),'-PrivateRoot',str(self.private),'-Python',sys.executable,
                '-Payload',str(self.payload),'-Tree',str(self.tree),'-Marker',str(marker)]

    def record(self,code,**values):
        self.calls.append(dict(case=self._testMethodName,code=code,**values))

    def wait_marker(self,marker,timeout=10):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if marker.exists() and marker.stat().st_size>1:
                return
            time.sleep(.025)
        self.fail('Owned fixture marker did not appear')

    def assert_stopped_marker(self,marker):
        self.wait_marker(marker)
        # A bound on observed descendant output, independent of PID/name lookups.
        time.sleep(.2); before=marker.stat().st_size
        time.sleep(.3); self.assertEqual(marker.stat().st_size,before)

    def unrelated(self):
        marker=self.private/('unrelated-'+uuid.uuid4().hex+'.bin')
        process=subprocess.Popen([sys.executable,str(self.heartbeat),str(marker)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
        self.wait_marker(marker)
        return process,marker

    def run_driver(self,mode,marker):
        began=time.monotonic()
        p=subprocess.run(ps_cmd(self.driver,self.driver_args(mode,marker)),capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        raw=self.private/(mode+'-'+uuid.uuid4().hex+'.json')
        raw.write_bytes(p.stdout)
        self.record('driver_returned',mode=mode,exitCode=p.returncode,seconds=round(time.monotonic()-began,3),rawPrivatePath=str(raw),stderrEmpty=not p.stderr)
        self.assertEqual(p.returncode,0,p.stderr.decode(errors='replace'))
        self.assertFalse(p.stderr)
        return json.loads(p.stdout.decode('utf-8-sig'))

    def test_01_gate_eof_without_G_never_reads_request(self):
        missing=self.private/'never-created-request.json'
        p=subprocess.run(ps_cmd(GATE,['-RequestPath',str(missing)]),input=b'',capture_output=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
        self.record('gate_eof_closed',exitCode=p.returncode,stdoutEmpty=not p.stdout,stderrEmpty=not p.stderr)
        self.assertEqual(p.returncode,2)
        self.assertFalse(p.stdout or p.stderr)
        self.assertFalse(missing.exists())

    def test_02_unicode_arguments_input_environment_and_private_logs(self):
        data=self.run_driver('Roundtrip',self.private/'unused-marker')
        self.assertEqual(data['exitCode'],0)
        self.assertEqual(data['payload']['arguments'],['alpha "quoted" text','backslash\\','', 'Unicode Ω 漢'])
        self.assertEqual(data['payload']['input'],'Unicode input Ω 漢\nsecond line\n')
        self.assertEqual(data['payload']['marker'],'synthetic marker Ω')
        self.assertTrue(data['stderrEmpty'] and data['jobClosed'])
        self.assertTrue(Path(data['requestPath']).is_relative_to(self.private))
        self.assertTrue(Path(data['stdoutPath']).is_file() and Path(data['stderrPath']).is_file())
        self.record('roundtrip_and_private_acl_verified',arguments=4,utf8Input=True,privateAcl=True,jobClosed=True)

    def test_03_timeout_stops_descendants_and_preserves_unrelated_process(self):
        marker=self.private/'timeout-descendant.bin'
        foreign,foreign_marker=self.unrelated()
        try:
            data=self.run_driver('Timeout',marker)
            self.assertEqual(data['exitCode'],124)
            self.assertTrue(data['gateExited'] and data['jobClosed'])
            self.assertTrue(data['gateMembership']); self.assertFalse(data['outsideMembership'])
            self.assert_stopped_marker(marker)
            before=foreign_marker.stat().st_size; time.sleep(.1)
            self.assertIsNone(foreign.poll())
            self.assertGreater(foreign_marker.stat().st_size,before)
            self.record('timeout_tree_stopped_unrelated_preserved',timeoutExit=124,descendantStopped=True,unrelatedPreserved=True)
        finally:
            foreign.kill(); foreign.wait(timeout=10)  # Exact independently-created sentinel handle only.

    def test_04_abrupt_controller_death_closes_only_owned_tree(self):
        marker=self.private/'crash-descendant.bin'
        foreign,foreign_marker=self.unrelated()
        output_path=self.private/'crash-driver.stdout'; error_path=self.private/'crash-driver.stderr'
        controller=None
        try:
            with output_path.open('wb') as out,error_path.open('wb') as err:
                controller=subprocess.Popen(ps_cmd(self.driver,self.driver_args('Crash',marker)),stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
                self.wait_marker(marker)
                controller.kill(); controller.wait(timeout=15)  # Simulate a crash by exact creator-owned handle.
            self.assert_stopped_marker(marker)
            before=foreign_marker.stat().st_size; time.sleep(.1)
            self.assertIsNone(foreign.poll()); self.assertGreater(foreign_marker.stat().st_size,before)
            self.assertFalse(error_path.read_bytes())
            events=[json.loads(line) for line in output_path.read_text(encoding='utf-8-sig').splitlines()]
            self.assertEqual(events[0]['event'],'owned-started')
            self.record('controller_crash_tree_stopped_unrelated_preserved',controllerExit=controller.returncode,descendantStopped=True,unrelatedPreserved=True,rawPrivatePath=str(output_path))
        finally:
            if controller is not None and controller.poll() is None:
                controller.kill(); controller.wait(timeout=10)
            foreign.kill(); foreign.wait(timeout=10)

    def test_05_invalid_launcher_and_stop_inputs_fail_without_process_start(self):
        for script,extra in ((START,['-StopAfterSeconds','-1']),(START,[]),(STOP,[])):
            command=ps_cmd(script,['-InstancePath',str(self.home/'missing-instance'),'-ExpectedInstanceSha256','0'*64,*extra])
            p=subprocess.run(command,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertEqual(p.returncode,2,p.stderr.decode(errors='replace')); self.assertFalse(p.stderr)
            rows=[json.loads(line) for line in p.stdout.decode('utf-8-sig').splitlines()]
            self.assertEqual(len(rows),1); self.assertFalse(rows[0]['valid'])
            if script==START:
                self.assertEqual(rows[0]['event'],'stopped')
            self.assertFalse((self.home/'missing-instance').exists())
            self.record('invalid_entry_rejected',script=script.name,exitCode=p.returncode,codeReturned=rows[0]['code'],events=1)


    def test_07_readiness_matches_only_authenticated_stage_schema(self):
        script=r"""
$ProgressPreference='SilentlyContinue'
$tokens=$null;$errors=$null
$tree=[Management.Automation.Language.Parser]::ParseFile('__START__',[ref]$tokens,[ref]$errors)
if ($errors.Count -ne 0) {throw 'syntax'}
$body=$tree.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'Test-LauncherReadyBody'},$true)
Invoke-Expression $body.Extent.Text
Set-StrictMode -Version Latest
$positive=@();foreach($version in @(9,10)){$positive+=Test-LauncherReadyBody ([pscustomobject]@{status='ready';schemaVersion=$version}) $version}
$negative=@()
foreach($pair in @(@(9,10),@(10,9),@(11,10),@(9,0),@(10,11))){$negative+=Test-LauncherReadyBody ([pscustomobject]@{status='ready';schemaVersion=$pair[0]}) $pair[1]}
foreach($value in @('10',10.0,$null)){$negative+=Test-LauncherReadyBody ([pscustomobject]@{status='ready';schemaVersion=$value}) 10}
$negative+=Test-LauncherReadyBody ([pscustomobject]@{status='Ready';schemaVersion=10}) 10
$negative+=Test-LauncherReadyBody ([pscustomobject]@{status='ready'}) 10
$negative+=Test-LauncherReadyBody $null 10
@{positive=$positive;negative=$negative;parserErrors=$errors.Count}|ConvertTo-Json -Compress
""".replace('__START__',str(START).replace("'","''"))
        environment={k:v for k,v in os.environ.items() if k.upper()!='PSMODULEPATH'}
        p=subprocess.run([str(PS),'-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode()],
            capture_output=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW,env=environment)
        self.assertEqual(p.returncode,0,p.stderr.decode(errors='replace'));self.assertFalse(p.stderr)
        result=json.loads(p.stdout.decode('utf-8-sig'))
        self.assertEqual(result,dict(positive=[True,True],negative=[False]*11,parserErrors=0))
        self.record('exact_stage_schema_readiness',positive=2,negative=11,httpRequests=0,databaseQueries=0)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--evidence',required=True); parser.add_argument('--cases',nargs='*')
    options=parser.parse_args(); evidence=Path(options.evidence).resolve(); evidence.mkdir(parents=True,exist_ok=False)
    before=evidence/'sources-before'; before.mkdir()
    for p in SOURCES:
        (before/p.name).write_bytes(p.read_bytes())
    suite=(unittest.TestSuite(InstanceLauncher(name) for name in options.cases) if options.cases else unittest.defaultTestLoader.loadTestsFromTestCase(InstanceLauncher))
    began=time.monotonic()
    with (evidence/'tests.log').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    data=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,failures=len(result.failures),errors=len(result.errors),successful=result.wasSuccessful(),seconds=round(time.monotonic()-began,3),fixture=str(getattr(InstanceLauncher,'home','not initialized')),sourceHashes=getattr(InstanceLauncher,'guards',{}),sourcesUnchanged=getattr(InstanceLauncher,'sources_unchanged',False),calls=getattr(InstanceLauncher,'calls',[]),databaseQueries=0,applicationExecutions=0,realQaActions=0,serviceOperations=0)
    write_json(evidence/'result.json',data)
    print(json.dumps({k:data[k] for k in ('testsRun','failures','errors','successful','seconds','fixture')}))
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':
    sys.exit(main())
