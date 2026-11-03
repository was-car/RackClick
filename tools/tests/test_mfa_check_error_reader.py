"""Read-only inspector tests. Synthetic child script only; no actual product Check/SCM/task/key."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'tools/windows/mfa-service-read-system/Read-MfaDiagnosticCheckError.ps1'
PS=shutil.which('powershell.exe')
LOAD=r'''
$ErrorActionPreference='Stop'
$text=[IO.File]::ReadAllText($env:RC_READER_SOURCE).Replace("`r`n","`n")
$cut=$text.LastIndexOf("`ntry {")
if($cut -lt 0){throw 'dispatcher_missing'}
. ([scriptblock]::Create($text.Substring(0,$cut)))
'''
def environment():
    env=os.environ.copy();env['RC_READER_SOURCE']=str(SOURCE)
    env['PSModulePath']=str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/Modules')
    return env

@unittest.skipUnless(PS,'Windows PowerShell5.1 required')
class ReaderTests(unittest.TestCase):
    def focus(self,body):
        with tempfile.TemporaryDirectory(prefix='rc-check-reader-') as directory:
            file=Path(directory)/'focus.ps1';file.write_text(LOAD+body,encoding='ascii')
            env=environment();env['RC_READER_FIXTURE']=directory
            result=subprocess.run([PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(file)],env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        return json.loads(result.stdout)

    def test_real_caught_cast_survives_child_exit_without_message_leak(self):
        data=self.focus(r'''
$child=Join-Path $env:RC_READER_FIXTURE 'child.ps1'
[IO.File]::WriteAllText($child,"try { [int]'PRIVATE_SENTINEL' } catch { 'translated' }; exit 1",[Text.Encoding]::ASCII)
$Error.Clear()
$null=& $child
$exitCode=$LASTEXITCODE;$record=$Error[0]
$safe=Get-CheckErrorMetadata $record
$serialized=$safe|ConvertTo-Json -Depth 6 -Compress
@{childExit=$exitCode;metadata=$safe;noLeak=($serialized -notmatch 'PRIVATE_SENTINEL|rc-check-reader|child.ps1|[A-Za-z]:\\')}|ConvertTo-Json -Depth 8 -Compress
''')
        self.assertEqual(data['childExit'],1)
        self.assertIn('System.Management.Automation.PSInvalidCastException',data['metadata']['exceptionTypes'])
        self.assertTrue(data['noLeak'])

    def test_localized_frames_and_unknown_names_are_filtered(self):
        data=self.focus(r'''
$rows=@()
foreach($prefix in @('at','bei','en')) {
 $record=[pscustomobject]@{Exception=(New-Object InvalidCastException('PRIVATE_SENTINEL'));ScriptStackTrace=($prefix+' Read-DiagnosticContext, C:\PRIVATE_SENTINEL.ps1: line 117'+"`r`n"+$prefix+' UnexpectedPrivateName, C:\PRIVATE_SENTINEL.ps1: line 99');InvocationInfo=[pscustomobject]@{MyCommand=[pscustomobject]@{Name='Get-CimInstance'}}}
 $safe=Get-CheckErrorMetadata $record
 $rows+=@{prefix=$prefix;passed=($safe.frames.Count -eq 1 -and $safe.frames[0].function -ceq 'Read-DiagnosticContext' -and $safe.frames[0].line -eq 117 -and $safe.command -ceq 'Get-CimInstance' -and ($safe|ConvertTo-Json -Depth 7 -Compress) -notmatch 'PRIVATE_SENTINEL|UnexpectedPrivateName')}
}
$rows|ConvertTo-Json -Depth 8 -Compress
''')
        self.assertTrue(all(item['passed'] for item in data),data)

    def test_selftest_parser_and_host_guard(self):
        result=subprocess.run([PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(SOURCE),'-Mode','SelfTest'],env=environment(),capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stdout)['checks'],4)
        if os.environ.get('COMPUTERNAME','').upper()=='LEAO':
            result=subprocess.run([PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(SOURCE)],env=environment(),capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,1)
            self.assertEqual(json.loads(result.stdout)['code'],'host_excluded')

    def test_only_pinned_check_can_be_invoked(self):
        text=SOURCE.read_text(encoding='ascii')
        self.assertIn("[ValidateSet('Check','SelfTest')]",text)
        self.assertIn('& $file.FullName -Mode Check',text)
        self.assertIn('e2cb1ab8c3d1d92ec1ec2335476f2cf94fd3428ac86dc49508329f55fc99a0b4',text)
        for forbidden in ('-Mode Run','-Mode Worker','RegisterTaskDefinition','Remove-Item','WriteAllText','Set-Acl','ReadAllBytes'):
            self.assertNotIn(forbidden,text)
        self.assertLess(text.index('$scriptLease=[IO.File]::Open'),text.index('& $file.FullName -Mode Check'))

if __name__=='__main__':unittest.main(verbosity=2)
