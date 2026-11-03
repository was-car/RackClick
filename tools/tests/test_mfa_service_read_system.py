"""Focal tests for the explicit SYSTEM route. Never registers a real task or accesses a service.

PowerShell fixtures use only pure functions, COM-shaped mocks, owned TEMP files and native own-token queries.
Actual SYSTEM execution and token/key access remain for the operator's VM.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'tools/windows/mfa-service-read-system/Invoke-MfaServiceReadSystemTrial.ps1'
REFERENCE = ROOT / 'tools/windows/mfa-service-read-trial/Invoke-MfaServiceReadTrial.ps1'
ARCHIVE = ROOT / '.local/mfa-lectura-l2l02/20261027T131716Z-a83ca31a/RackClick-MFA-Lectura-L2l02.zip'
PS = shutil.which('powershell.exe')

def ps_environment():
    env = os.environ.copy()
    env['PSModulePath'] = (str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/Modules') + ';' +
                           str(Path(os.environ['ProgramFiles']) / 'WindowsPowerShell/Modules'))
    return env


@unittest.skipUnless(PS, 'Windows PowerShell 5.1 is required')
class ScriptTests(unittest.TestCase):
    def invoke(self, *args):
        return subprocess.run([PS, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File',
                               str(SCRIPT), *args], capture_output=True, text=True, encoding='utf-8',
                              errors='replace', timeout=60, env=ps_environment())

    def test_native_powershell_parser(self):
        command = "$t=$null;$e=$null;$null=[Management.Automation.Language.Parser]::ParseFile($args[0],[ref]$t,[ref]$e);if($e.Count){exit 1}"
        with tempfile.TemporaryDirectory(prefix='rc-system-parser-') as directory:
            p = Path(directory) / 'parse.ps1';p.write_text(command, encoding='ascii')
            result = subprocess.run([PS, '-NoProfile', '-NonInteractive', '-File', str(p), str(SCRIPT)], capture_output=True, timeout=60, env=ps_environment())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_selftest_only_checks_pure_contracts(self):
        out = self.invoke('-Mode', 'SelfTest')
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        data = json.loads(out.stdout)
        self.assertEqual(data['status'], 'selftest_passed')
        self.assertFalse(data['taskRegistered'])
        self.assertFalse(data['serviceAccessed'])
        self.assertFalse(data['keysRead'])

    @unittest.skipUnless(os.environ.get('COMPUTERNAME', '').upper() == 'LEAO', 'Production host guard is specific to LEAO')
    def test_all_execution_modes_reject_leao_before_any_actions(self):
        for mode in ('Check', 'Run', 'Worker'):
            with self.subTest(mode=mode):
                out = self.invoke('-Mode', mode)
                self.assertEqual(out.returncode, 1, out.stdout + out.stderr)
                data = json.loads(out.stdout)
                self.assertEqual(data['code'], 'host_excluded')
                self.assertFalse(data['taskCreated'])

    def test_confirmation_precedes_every_mutation(self):
        text = SCRIPT.read_text(encoding='ascii')
        body = text[text.index('function Invoke-CheckOrRun'):text.index('function Invoke-SelfTest')]
        self.assertLess(body.index('Confirm-SystemRead $context.installationId'), body.index('New-PrivateRoot $root'))
        self.assertLess(body.index('New-PrivateRoot $root'), body.index('New-TaskOwned $folder'))
        self.assertIn('RegisterTaskDefinition($Name,$definition,2,', text)
        self.assertNotIn('Register-ScheduledTask', text)
        self.assertNotIn('schtasks', text)
        self.assertNotIn('Set-Acl', text)
        self.assertIn('execution.started', text)
        self.assertIn('[IO.FileMode]::CreateNew', text)
        self.assertLess(body.index('Get-OwnTask $folder $name $xml'), body.index('$task.Run($null)'))

    def test_functions_and_mocked_task_protocol(self):
        with tempfile.TemporaryDirectory(prefix='rc-system-focus-') as directory:
            fixture = Path(directory)
            harness = fixture / 'foci.ps1'
            harness.write_text(FOCI, encoding='ascii')
            env = ps_environment()
            env.update(RC_SYSTEM_SCRIPT=str(SCRIPT), RC_SYSTEM_REFERENCE=str(REFERENCE), RC_SYSTEM_FIXTURE=str(fixture))
            out = subprocess.run([PS, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(harness)],
                                 capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90, env=env)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        data = json.loads(out.stdout)
        self.assertGreaterEqual(len(data), 14)
        self.assertTrue(all(item['passed'] for item in data), out.stdout)

    def test_native_task_xml_validation_in_memory_only(self):
        with tempfile.TemporaryDirectory(prefix='rc-system-xml-') as directory:
            harness=Path(directory)/'xml.ps1'
            harness.write_text(LOAD_PREFIX + r'''
$xml=Get-TaskXml 'C:\private\worker.ps1' 'C:\private\plan.json' ('a'*64) 'RackClick-MFA-SystemRead-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
$scheduler=New-Object -ComObject Schedule.Service
$definition=New-TaskDefinition $scheduler $xml
Assert-TaskContract $definition.XmlText $xml
$bad=$xml.Replace('<UserId>S-1-5-18</UserId>','<UserId>S-1-5-18</UserId><LogonType>ServiceAccount</LogonType>')
$rejected=$false
try {$definition.XmlText=$bad}catch{$rejected=$true}
if(-not $rejected){throw 'invalid_system_xml_not_rejected'}
[ordered]@{nativeXmlAccepted=$true;invalidServiceAccountLiteralRejected=$true;connected=$false;registered=$false;ran=$false}|ConvertTo-Json -Compress
''',encoding='ascii')
            env=ps_environment();env['RC_SYSTEM_SCRIPT']=str(SCRIPT)
            out=subprocess.run([PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(harness)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60,env=env)
        self.assertEqual(out.returncode,0,out.stdout+out.stderr)
        data=json.loads(out.stdout)
        self.assertTrue(data['nativeXmlAccepted'])
        self.assertTrue(data['invalidServiceAccountLiteralRejected'])
        self.assertFalse(data['registered'])

    @unittest.skipUnless(ARCHIVE.is_file(), 'The exact reviewed L2l02 archive must be present')
    def test_real_archive_import_and_integrity_without_execution(self):
        with tempfile.TemporaryDirectory(prefix='rc-system-archive-') as directory:
            fixture = Path(directory);harness = fixture / 'archive.ps1'
            harness.write_text(LOAD_PREFIX + r'''
$zip=Get-Zip $env:RC_SYSTEM_ARCHIVE
try {
 . Import-ReferenceFunctions (Read-ZipText $zip 'Invoke-MfaServiceReadTrial.ps1')
 if(-not (Get-Command Invoke-ReadProbe -ErrorAction SilentlyContinue)){throw 'function_scope_missing'}
 if($ProbeVerbForRun -cne 'read'){throw 'verb_missing'}
 Expand-PrivatePackage $zip $env:RC_SYSTEM_FIXTURE
 $package=Join-Path $env:RC_SYSTEM_FIXTURE $ReferenceFolder
 $verified=Test-PackageIntegrity $package $SumsPin
 if($verified.fileCount -ne 355){throw 'count_invalid'}
 [ordered]@{functionsVisible=$true;operatorVerb=$ProbeVerbForRun;verifiedFiles=$verified.fileCount;probeExecuted=$false;taskRegistered=$false}|ConvertTo-Json -Compress
} finally {$zip.Dispose()}
''', encoding='ascii')
            env = ps_environment();env.update(RC_SYSTEM_SCRIPT=str(SCRIPT), RC_SYSTEM_ARCHIVE=str(ARCHIVE), RC_SYSTEM_FIXTURE=str(fixture))
            out = subprocess.run([PS, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(harness)],
                                 capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90, env=env)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        data = json.loads(out.stdout)
        self.assertEqual(data['verifiedFiles'], 355)
        self.assertFalse(data['probeExecuted'])


LOAD_PREFIX = r'''
$ErrorActionPreference='Stop'
$text=[IO.File]::ReadAllText($env:RC_SYSTEM_SCRIPT).Replace("`r`n","`n")
$cut=$text.LastIndexOf("`ntry {`n    if (`$Mode")
if($cut -lt 0){throw 'dispatcher_not_found'}
. ([scriptblock]::Create($text.Substring(0,$cut)))
'''

FOCI = LOAD_PREFIX + r'''
$results=New-Object Collections.Generic.List[object]
function Check([string]$Name,[bool]$Value){$results.Add([ordered]@{name=$Name;passed=$Value});if(-not $Value){throw ('focus_failed:'+ $Name)}}
function Code([scriptblock]$Block){try{&$Block|Out-Null;return ''}catch{return (Error-Code $_)}}
. Import-ReferenceFunctions ([IO.File]::ReadAllText($env:RC_SYSTEM_REFERENCE))
Check 'original_reference_functions_visible' ([bool](Get-Command Test-ProbeOutcome -ErrorAction SilentlyContinue))
$bad=Join-Path $env:RC_SYSTEM_FIXTURE 'bad.zip';[IO.File]::WriteAllText($bad,'synthetic')
Check 'wrong_archive_hash_rejected' ((Code {Get-Zip $bad}) -ceq 'archive_hash_mismatch')
$beforeFiles=@(Get-ChildItem -LiteralPath $env:RC_SYSTEM_FIXTURE -Recurse -File).Count
Check 'wrong_confirmation_rejected' ((Code {Assert-SystemConfirmation 'NO' 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'}) -ceq 'confirmation_mismatch')
Check 'confirmation_failure_writes_nothing' (@(Get-ChildItem -LiteralPath $env:RC_SYSTEM_FIXTURE -Recurse -File).Count -eq $beforeFiles)
Check 'correct_confirmation_accepted' ((Code {Assert-SystemConfirmation 'CONFIRMO LECTURA SYSTEM aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee' 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'}) -ceq '')
$xml=Get-TaskXml 'C:\private\worker.ps1' 'C:\private\plan.json' ('a'*64) 'RackClick-MFA-SystemRead-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
Check 'task_xml_valid' ((Code {Assert-TaskContract $xml $xml}) -ceq '')
Check 'task_principal_alteration_rejected' ((Code {Assert-TaskContract ($xml.Replace('S-1-5-18','S-1-5-19')) $xml}) -ceq 'task_contract_invalid')
Check 'task_required_privilege_missing_rejected' ((Code {Assert-TaskContract ($xml.Replace('<Privilege>SeImpersonatePrivilege</Privilege>','')) $xml}) -ceq 'task_privileges_invalid')
$folder=New-Object PSObject
$folder|Add-Member ScriptMethod GetTask {param($Name) return [pscustomobject]@{Xml='changed';State=3}}
$script:registered=0;$script:deleted=0
$folder|Add-Member ScriptMethod RegisterTaskDefinition {$script:registered++;throw 'must_not_register'}
$folder|Add-Member ScriptMethod DeleteTask {$script:deleted++}
Check 'existing_task_not_adopted' ((Code {New-TaskOwned $folder 'existing' $xml}) -ceq 'task_name_exists')
Check 'existing_task_not_registered' ($script:registered -eq 0)
Check 'changed_task_preserved' ((Remove-OwnTask $folder 'changed' $xml) -ceq 'preserved' -and $script:deleted -eq 0)
$runningFolder=New-Object PSObject
$runningFolder|Add-Member NoteProperty ExpectedXml $xml
$runningFolder|Add-Member ScriptMethod GetTask {param($Name) return [pscustomobject]@{Xml=$this.ExpectedXml;State=4}}
Check 'timeout_is_not_success' ((Code {Wait-WorkerResult $runningFolder 'running' $xml (Join-Path $env:RC_SYSTEM_FIXTURE 'absent.json') 0}) -ceq 'worker_timeout')
$raw=[pscustomobject]@{schemaVersion=1;verb='read';status='passed';code='';processLinked=$true;tokenMatched=$true;impersonationVerified=$true;identityRestored=$true;debugPrivilege='not_used';store=[pscustomobject]@{activeVersion=1;keyBytes=32};writeProbe=[pscustomobject]@{targets=5;writeDenied=5;dacDenied=5;writeGranted=0;dacGranted=0;ownerIsReader=0;inconclusive=0}}
$outcome=[pscustomobject]@{exitCode=0;stderrBytes=0;raw=$raw}
Check 'complete_probe_contract_accepted' (Test-StrictOutcome $outcome 5)
$raw.schemaVersion=999
Check 'wrong_schema_rejected' (-not (Test-StrictOutcome $outcome 5))
$raw.schemaVersion=1;$raw.writeProbe.dacDenied=4
Check 'partial_denial_rejected' (-not (Test-StrictOutcome $outcome 5))
$raw.writeProbe.dacDenied=5;$raw.processLinked='true'
Check 'string_boolean_rejected' (-not (Test-StrictOutcome $outcome 5))
$raw.processLinked=$true
Check 'cleanup_incomplete_never_passes' ((Get-Summary ([pscustomobject]@{status='passed';code='';fingerprintState='unchanged';outcome=$outcome}) 'running').status -ceq 'failed')
$script:fingerprints=0
function Get-StoreFingerprint {param($Root) $script:fingerprints++;return @{count=5;digest='same'}}
function Invoke-ReadProbe {throw 'trial:probe_timeout'}
$plan=[pscustomobject]@{trialRoot='C:\synthetic';installationId='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';service='RackClick';beforeDigest='same';beforeCount=5}
$failed=Invoke-ProbeWithFingerprint $plan 'C:\synthetic-code'
Check 'probe_failure_stays_failed' ($failed.status -ceq 'failed' -and $failed.code -ceq 'probe_timeout')
Check 'fingerprint_repeated_after_probe_failure' ($script:fingerprints -eq 2 -and $failed.fingerprintState -ceq 'unchanged')
$results|ConvertTo-Json -Depth 5 -Compress
'''

if __name__ == '__main__':
    unittest.main(verbosity=2)
