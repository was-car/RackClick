"""Resume foci. No task is registered or run: native calls use TASK_VALIDATE_ONLY=1 only.

Other cases use pure definitions, COM-shaped mock objects and own TEMP marker fixtures.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/'tools/windows/mfa-service-read-system/Resume-MfaServiceReadSystemTrial.ps1'
BASE=ROOT/'tools/windows/mfa-service-read-system/Invoke-MfaServiceReadSystemTrial.ps1'
PS=shutil.which('powershell.exe')

def env():
    value=os.environ.copy()
    value['PSModulePath']=str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/Modules')+';'+str(Path(os.environ['ProgramFiles'])/'WindowsPowerShell/Modules')
    value.update(RC_RESUME_SCRIPT=str(SCRIPT),RC_RESUME_BASE=str(BASE))
    return value

LOAD=r'''
$ErrorActionPreference='Stop'
$text=[IO.File]::ReadAllText($env:RC_RESUME_SCRIPT).Replace("`r`n","`n")
$cut=$text.LastIndexOf("`ntry {`n    if (`$Mode")
if($cut -lt 0){throw 'dispatcher_not_found'}
. ([scriptblock]::Create($text.Substring(0,$cut)))
. Import-ResumeBase $env:RC_RESUME_BASE
'''

@unittest.skipUnless(PS,'Windows PowerShell 5.1 is required')
class ResumeTests(unittest.TestCase):
    def run_script(self,body,extra=None):
        with tempfile.TemporaryDirectory(prefix='rc-resume-focus-') as directory:
            file=Path(directory)/'focus.ps1';file.write_text(body,encoding='ascii')
            environment=env();environment['RC_RESUME_FIXTURE']=directory
            if extra:environment.update(extra)
            out=subprocess.run([PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(file)],env=environment,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
        self.assertEqual(out.returncode,0,out.stdout+out.stderr)
        return json.loads(out.stdout)

    def test_native_parser(self):
        data=self.run_script(r'''
$tokens=$null;$errors=$null
$null=[Management.Automation.Language.Parser]::ParseFile($env:RC_RESUME_SCRIPT,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'parse_failed'}
@{parserErrors=0;version=$PSVersionTable.PSVersion.ToString()}|ConvertTo-Json -Compress
''')
        self.assertEqual(data['parserErrors'],0)
        self.assertTrue(data['version'].startswith('5.1'))

    def test_selftest_is_non_execution(self):
        out=subprocess.run([PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(SCRIPT),'-Mode','SelfTest'],env=env(),capture_output=True,text=True,timeout=60)
        self.assertEqual(out.returncode,0,out.stdout+out.stderr)
        self.assertFalse(json.loads(out.stdout)['taskRegistered'])
        self.assertEqual(json.loads(out.stdout)['checks'],3)

    @unittest.skipUnless(os.environ.get('COMPUTERNAME','').upper()=='LEAO','Specific host guard')
    def test_check_and_run_guard_precedes_file_or_scheduler_access(self):
        for mode in ('Check','Run'):
            with self.subTest(mode=mode):
                out=subprocess.run([PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(SCRIPT),'-Mode',mode],env=env(),capture_output=True,text=True,timeout=60)
                self.assertEqual(out.returncode,1)
                self.assertEqual(json.loads(out.stdout)['code'],'host_excluded')

    def test_pure_resume_guards_and_task_binding(self):
        data=self.run_script(LOAD+FOCI)
        self.assertGreaterEqual(len(data),12)
        self.assertTrue(all(item['passed'] for item in data),data)

    def test_validate_only_real_scheduler_system_without_privileges(self):
        data=self.run_script(LOAD+r'''
$scheduler=New-Object -ComObject Schedule.Service
$scheduler.Connect();$folder=$scheduler.GetFolder('\')
$name='RackClick-ValidateOnly-Resume-'+[guid]::NewGuid().ToString('N')
$legacy=Get-TaskXml 'C:\private\worker.ps1' 'C:\private\plan.json' ('a'*64) 'RackClick-MFA-SystemRead-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
$bad=New-TaskDefinition $scheduler $legacy
$oldRejected=$false;$oldHresults=@()
try {$null=$folder.RegisterTaskDefinition($name,$bad,1,'SYSTEM',$null,5,$TaskDacl)}catch{$oldRejected=$true;$oldHresults=@(Resume-HResults $_)}
if(-not $oldRejected -or $oldHresults -notcontains -2147216618){throw 'old_system_privileges_not_reproduced'}
$corrected=New-ResumeDefinition $scheduler $legacy
Assert-ResumeTask $corrected.XmlText $legacy $false
$null=$folder.RegisterTaskDefinition($name,$corrected,1,'SYSTEM',$null,5,$TaskDacl)
@{legacySystemRejected=$true;legacyHresults=$oldHresults;correctedSystemValidated=$true;flags=1;created=$false;ran=$false}|ConvertTo-Json -Depth 5 -Compress
''')
        self.assertTrue(data['legacySystemRejected'])
        self.assertTrue(data['correctedSystemValidated'])
        self.assertEqual(data['flags'],1)
        self.assertFalse(data['created'])

    def test_no_extraction_initialization_or_marker_removal(self):
        text=SCRIPT.read_text(encoding='ascii')
        for forbidden in ('Expand-Archive','Expand-PrivatePackage','New-PrivateRoot','--mfa-keys-init','Set-Acl','Remove-Item','execution.started\' -Force'):
            self.assertNotIn(forbidden,text)
        self.assertIn('Assert-NotStarted $AttemptRoot',text)
        self.assertLess(text.index('$definition,1,'),text.index('Confirm-SystemRead $plan.installationId'))
        self.assertLess(text.index('Confirm-SystemRead $plan.installationId'),text.index('$folder.DeleteTask'))
        self.assertLess(text.index('Confirm-SystemRead $plan.installationId'),text.index('$definition,2,'))
        self.assertIn("'worker.ps1'",text)
        self.assertIn('6fa659e61e10571168cd0d8fffd21ca7f729bbacee41021d44eb9e8d62237cb9',text)
        self.assertIn("'-receipt.json'",text)

FOCI=r'''
$rows=New-Object Collections.Generic.List[object]
function Check([string]$Name,[bool]$Ok){$rows.Add(@{name=$Name;passed=$Ok});if(-not $Ok){throw ('focus_failed:'+ $Name)}}
function Code([scriptblock]$Body){try{&$Body|Out-Null;return ''}catch{return Resume-Code $_}}
$legacy=Get-TaskXml 'C:\private\worker.ps1' 'C:\private\plan.json' ('a'*64) 'RackClick-MFA-SystemRead-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
$scheduler=New-Object -ComObject Schedule.Service
$definition=New-ResumeDefinition $scheduler $legacy
Check 'corrected_definition_has_no_privileges' ($definition.XmlText -notmatch 'RequiredPrivileges')
Check 'corrected_definition_keeps_service_account_logon' ($definition.Principal.LogonType -eq 5)
Check 'legacy_definition_rejected_for_new_execution' ((Code {Assert-ResumeTask $legacy $legacy $false}) -ceq 'system_privileges_must_be_omitted')
Check 'legacy_definition_can_be_identified_for_retirement' ((Code {Assert-ResumeTask $legacy $legacy $true}) -ceq '')
Check 'foreign_action_rejected' ((Code {Assert-ResumeTask ($definition.XmlText.Replace('worker.ps1','foreign.ps1')) $legacy $false}) -ceq 'task_contract_invalid')
Check 'foreign_principal_rejected' ((Code {Assert-ResumeTask ($definition.XmlText.Replace('S-1-5-18','S-1-5-19')) $legacy $false}) -ceq 'task_contract_invalid')
Check 'running_prior_task_rejected' ((Code {Assert-PriorStopped ([pscustomobject]@{Xml=$legacy;State=4}) $legacy}) -ceq 'prior_task_active')
Check 'queued_prior_task_rejected' ((Code {Assert-PriorStopped ([pscustomobject]@{Xml=$legacy;State=2}) $legacy}) -ceq 'prior_task_active')
Check 'unknown_prior_task_rejected' ((Code {Assert-PriorStopped ([pscustomobject]@{Xml=$legacy;State=0}) $legacy}) -ceq 'prior_task_not_stopped')
Check 'stopped_owned_task_accepted' ((Code {Assert-PriorStopped ([pscustomobject]@{Xml=$legacy;State=3}) $legacy}) -ceq '')
$fixture=$env:RC_RESUME_FIXTURE
Check 'unused_attempt_accepted' ((Code {Assert-NotStarted $fixture}) -ceq '')
[IO.File]::WriteAllText((Join-Path $fixture 'execution.started'),'retained')
Check 'started_attempt_rejected' ((Code {Assert-NotStarted $fixture}) -ceq 'attempt_already_started')
Check 'marker_preserved' ([IO.File]::ReadAllText((Join-Path $fixture 'execution.started')) -ceq 'retained')
$inner=New-Object Runtime.InteropServices.COMException('synthetic',-2147216618)
$outer=New-Object Exception('synthetic',$inner)
Check 'hresult_chain_preserves_native_error' (@(Resume-HResults ([pscustomobject]@{Exception=$outer})) -contains -2147216618)
$rows|ConvertTo-Json -Depth 5 -Compress
'''

if __name__=='__main__':unittest.main(verbosity=2)
