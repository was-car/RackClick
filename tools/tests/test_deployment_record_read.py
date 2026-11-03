"""Native marker-read IO tests; synthetic private files, no PostgreSQL or app."""
import argparse,hashlib,json,os,platform,subprocess,time,unittest,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PS=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
EVIDENCE=None
quote=lambda p:"'"+str(p).replace("'","''")+"'"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
COMMON=r'''
. (Join-Path $Workspace 'tools/windows/RackClick.Process.ps1')
function Import-ActualFunction([string]$File,[string]$Name) {
 $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($File,[ref]$tokens,[ref]$errors)
 if($errors.Count -gt 0){throw 'parse failed'}
 $node=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $Name},$true)
 return $node.Extent.Text
}
Invoke-Expression (Import-ActualFunction (Join-Path $Workspace 'tools/windows/RackClick.Deployment.ps1') 'Stop-PrivateDeploymentCheck')
Invoke-Expression (Import-ActualFunction (Join-Path $Workspace 'tools/windows/RackClick.Deployment.ps1') 'Read-DeploymentJson')
Invoke-Expression (Import-ActualFunction (Join-Path $Workspace 'tools/windows/Invoke-RackClickPrivateDeployment.ps1') 'Read-DeploymentOperationRecord')
$root=Join-Path (Join-Path $Workspace '.local') ('record-read-'+[guid]::NewGuid().ToString('N'))
$null=New-RackClickProcessPrivateDirectory $root
$path=Join-Path $root 'run-state.json';$run='22222222-2222-4222-8222-222222222222';$id='11111111-1111-4111-8111-111111111111'
$record=@{schemaVersion=1;instanceId=$id;runId=$run;requestRelativePath=('launcher-'+$run+'/stop-request.json');publicOrigin='https://127.0.0.1:54321';status='ready';code='ready';utc='2026-10-17T00:00:00Z'}
$deployment=@{instance=@{id=$id;httpPort=54321}}
function Save-Record {[IO.File]::WriteAllText($path,($record|ConvertTo-Json -Compress),(New-Object Text.UTF8Encoding($false)))}
function Read-Outcome([string]$File=$path,[string]$Expected=$run) {
 $watch=[Diagnostics.Stopwatch]::StartNew()
 try {$v=Read-DeploymentOperationRecord $File $deployment $Expected;return @{code='ok';ms=$watch.ElapsedMilliseconds;run=$v.runId}}
 catch {
  $code='untagged';foreach($key in @('deploymentCode','code')){if($_.Exception.Data.Contains($key)){$code=[string]$_.Exception.Data[$key]}}
  return @{code=$code;ms=$watch.ElapsedMilliseconds}
 }
}
'''


class RecordRead(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global EVIDENCE
        if EVIDENCE is None:
            from uuid import uuid4
            EVIDENCE = ROOT / '.local' / ('deployment-record-read-' + uuid4().hex)
            EVIDENCE.mkdir(parents=True, exist_ok=False)
    def run_ps(self,name,body):
        script=EVIDENCE/(name+'.ps1')
        script.write_bytes(("$Workspace="+quote(ROOT)+'\n'+COMMON+'\n'+body).encode())
        environment={k:v for k,v in os.environ.items() if k.upper()!='PSMODULEPATH'}
        started=time.monotonic()
        p=subprocess.run([str(PS),'-NoProfile','-NonInteractive','-File',str(script)],capture_output=True,env=environment,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
        (EVIDENCE/(name+'.log')).write_bytes(p.stdout+p.stderr)
        self.assertEqual(p.returncode,0,'Native IO probe failed; local synthetic log retained')
        self.assertFalse(p.stderr);value=json.loads(p.stdout.decode('utf-8-sig'))
        (EVIDENCE/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
        return value

    def test_01_missing_and_busy_are_bounded_then_recover(self):
        v=self.run_ps('bounded',r'''
$missing=Read-Outcome;Save-Record
$lock=[IO.File]::Open($path,'Open','ReadWrite','None')
try {$busy=Read-Outcome} finally {$lock.Dispose()}
$recovered=Read-Outcome
@{missing=$missing;busy=$busy;recovered=$recovered}|ConvertTo-Json -Depth 4 -Compress
''')
        for label in ('missing','busy'):
            self.assertEqual(v[label]['code'],'deployment_run_record_unavailable')
            self.assertGreaterEqual(v[label]['ms'],900);self.assertLess(v[label]['ms'],2500)
        self.assertEqual(v['recovered']['code'],'ok')

    def test_02_security_schema_and_identity_still_fail_closed(self):
        v=self.run_ps('validation',r'''
Save-Record;$wrongRun=Read-Outcome $path '33333333-3333-4333-8333-333333333333'
$record.status='invalid';Save-Record;$schema=Read-Outcome
$record.status='ready';Save-Record
$acl=[IO.File]::GetAccessControl($path)
$rule=New-Object Security.AccessControl.FileSystemAccessRule((New-Object Security.Principal.SecurityIdentifier('S-1-1-0')),[Security.AccessControl.FileSystemRights]::Read,[Security.AccessControl.AccessControlType]::Allow)
$acl.AddAccessRule($rule);[IO.File]::SetAccessControl($path,$acl)
$permissions=Read-Outcome
$acl.RemoveAccessRuleSpecific($rule);[IO.File]::SetAccessControl($path,$acl)
$target=Join-Path $root 'target';$null=New-RackClickProcessPrivateDirectory $target
[IO.File]::WriteAllBytes((Join-Path $target 'run-state.json'),[IO.File]::ReadAllBytes($path))
$junction=Join-Path $root 'junction';$null=New-Item -ItemType Junction -Path $junction -Value $target -ErrorAction Stop
$reparse=Read-Outcome (Join-Path $junction 'run-state.json')
@{wrongRun=$wrongRun;schema=$schema;permissions=$permissions;reparse=$reparse}|ConvertTo-Json -Depth 4 -Compress
''')
        expected=dict(wrongRun='deployment_active_run_changed',schema='deployment_run_record_invalid',permissions='process_private_acl_required',reparse='process_reparse_rejected')
        for label,code in expected.items():
            self.assertEqual(v[label]['code'],code);self.assertLess(v[label]['ms'],900)

    def test_03_leaf_is_pinned_during_acl_and_released_on_return(self):
        v=self.run_ps('pin',r'''
Save-Record;$replacement=Join-Path $root 'replacement.json'
[IO.File]::WriteAllBytes($replacement,[IO.File]::ReadAllBytes($path))
$originalAcl=Import-ActualFunction (Join-Path $Workspace 'tools/windows/RackClick.Process.ps1') 'Assert-RackClickProcessPrivateAcl'
Invoke-Expression ($originalAcl.Replace('function Assert-RackClickProcessPrivateAcl','function Assert-OriginalRecordAcl'))
$script:blocked=$false
function Assert-RackClickProcessPrivateAcl([string]$Path) {
 try {[IO.File]::Replace($replacement,$Path,[Management.Automation.Language.NullString]::Value)}
 catch [IO.IOException] {$cause=$_.Exception;while($null -ne $cause.InnerException){$cause=$cause.InnerException};$script:blocked=(($cause.HResult -band 0xffff) -eq 32)}
 Assert-OriginalRecordAcl $Path
}
$value=Read-Outcome
[IO.File]::Replace($replacement,$path,[Management.Automation.Language.NullString]::Value)
@{read=$value;replacementBlockedDuringAcl=$script:blocked;replacementAllowedAfterReturn=(-not [IO.File]::Exists($replacement))}|ConvertTo-Json -Depth 4 -Compress
''')
        self.assertEqual(v['read']['code'],'ok');self.assertTrue(v['replacementBlockedDuringAcl']);self.assertTrue(v['replacementAllowedAfterReturn'])


def main():
    global EVIDENCE
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);args=p.parse_args()
    EVIDENCE=args.evidence;EVIDENCE.mkdir(parents=True,exist_ok=False)
    files=[ROOT/'tools/windows/Invoke-RackClickPrivateDeployment.ps1',Path(__file__),ROOT/'tools/windows/RackClick.Process.ps1',ROOT/'tools/windows/RackClick.Deployment.ps1']
    before={x.relative_to(ROOT).as_posix():sha(x) for x in files};started=time.monotonic()
    with (EVIDENCE/'tests.log').open('w',encoding='utf-8') as out:
        result=unittest.TextTestRunner(stream=out,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RecordRead))
    report=dict(successful=result.wasSuccessful(),testsRun=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        seconds=round(time.monotonic()-started,3),sources=before,unchanged=all(sha(ROOT/n)==v for n,v in before.items()),
        platform=platform.platform(),databaseExecuted=False,applicationExecuted=False)
    (EVIDENCE/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
    return 0 if result.wasSuccessful() and report['unchanged'] else 1


if __name__=='__main__':raise SystemExit(main())
