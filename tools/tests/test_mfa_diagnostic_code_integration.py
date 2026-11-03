"""Parent/code binding foci with CIM mock or own account translation only; no task or product key."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('diagnostic_foci',ROOT/'tools/tests/test_mfa_probe_exception_diagnostic.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)

class CodeIntegrationTests(unittest.TestCase):
    def focus(self,body):return previous.DiagnosticTests().focus(body)

    def test_plan_binds_code_root_account_manifest_and_count(self):
        data=self.focus(r'''
$id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';$name='RackClick-MFA-SystemRead-'+('b'*32)
$root=Join-Path $env:ProgramData $name;$code=Join-Path $env:ProgramData ('RackClick-MFA-Code-'+('b'*32))
$trial=Join-Path $env:ProgramData ('RackClick-MFA-Ensayo-03-'+$id)
$context=[pscustomobject]@{oldPlanSha256=('a'*64);package='C:\synthetic\package';oldPlan=@{trialRoot=$trial;installationId=$id;service='RackClick'};before=@{digest=('b'*64);count=5};readerSid='S-1-5-21-1-2-3-1000';codeManifest=@{digest=('c'*64);count=352}}
$base=@{schemaVersion=1;taskName=$name;scriptSha256=('d'*64);sumsSha256=('e'*64);attemptRoot=$AttemptRoot;oldPlanSha256=$context.oldPlanSha256;packageRoot=$context.package;trialRoot=$trial;installationId=$id;service='RackClick';beforeDigest=('b'*64);beforeCount=5;codeRoot=$code;readerSid=$context.readerSid;codeManifestSha256=('c'*64);codeCount=352}
$rows=@()
foreach($case in @('valid','other_root','other_reader','other_manifest','other_count')) {
 $plan=[pscustomobject]$base.Clone()
 switch($case){
  'other_root'{$plan.codeRoot=Join-Path $env:ProgramData ('RackClick-MFA-Code-'+('f'*32))}
  'other_reader'{$plan.readerSid='S-1-5-21-1-2-3-1001'}
  'other_manifest'{$plan.codeManifestSha256=('f'*64)}
  'other_count'{$plan.codeCount=353}
 }
 $errorCode=Code {Assert-DiagnosticPlan $plan $context $root ('d'*64)}
 $rows+=@{case=$case;passed=$(if($case -ceq 'valid'){$errorCode -ceq ''}else{$errorCode -ceq 'code_plan_invalid'})}
}
$rows|ConvertTo-Json -Depth 6 -Compress
''')
        self.assertTrue(all(row['passed'] for row in data),data)

    def test_service_account_sid_is_resolved_from_exact_cim_record(self):
        data=self.focus(r'''
$script:fixtureOwn=[Security.Principal.WindowsIdentity]::GetCurrent()
function Get-CimInstance([string]$ClassName,[string]$Filter){return [pscustomobject]@{Name='RackClick';State='Running';ProcessId=42;StartName=$script:fixtureOwn.Name}}
$resolved=Get-DiagnosticServiceReaderSid 'RackClick'
$same=$resolved -ceq $script:fixtureOwn.User.Value
function Get-CimInstance([string]$ClassName,[string]$Filter){return [pscustomobject]@{Name='RackClick';State='Stopped';ProcessId=0;StartName='LocalSystem'}}
$reject=(Code{Get-DiagnosticServiceReaderSid 'RackClick'}) -ceq 'service_not_running'
@{sameAccount=$same;stoppedRejected=$reject;realCimQueried=$false}|ConvertTo-Json -Compress
''')
        self.assertTrue(data['sameAccount'] and data['stoppedRejected'])
        self.assertFalse(data['realCimQueried'])

    def test_process_uses_only_code_payload_and_creation_follows_confirmation(self):
        text=previous.SCRIPT.read_text(encoding='ascii')
        body=text[text.index('function Invoke-DiagnosticProcess'):text.index('function Invoke-DiagnosticFingerprint')]
        self.assertNotIn('$Context.oldPackage',body)
        self.assertNotIn('$Context.package',body)
        self.assertIn('$psi.WorkingDirectory=$Context.codeRoot',body)
        self.assertIn("$psi.FileName=Join-Path $Context.codeRoot 'runtime/dotnet.exe'",body)
        self.assertLess(text.index('Confirm-Diagnostic $plan.installationId'),text.index('New-DiagnosticCodePayload $plannedCodeRoot'))
        self.assertLess(text.index('New-PrivateRoot $plannedRoot'),text.index('New-DiagnosticCodePayload $plannedCodeRoot'))
        self.assertIn('Assert-DiagnosticCodePayload $context.codeRoot $context.readerSid $context.codeManifest $leases',text)
        self.assertIn('reader_account_changed',text)
        self.assertIn('codeManifestSha256',text)

if __name__=='__main__':unittest.main(verbosity=2)
