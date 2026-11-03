"""Diagnostic launcher foci: pure/mocked calls only, no real Scheduler registration or service access."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/'tools/windows/mfa-service-read-system/Invoke-MfaProbeExceptionDiagnostic.ps1'
BASE=ROOT/'tools/windows/mfa-service-read-system/Invoke-MfaServiceReadSystemTrial.ps1'
RESUME=ROOT/'tools/windows/mfa-service-read-system/Resume-MfaServiceReadSystemTrial03.ps1'
REFERENCE=ROOT/'tools/windows/mfa-service-read-trial/Invoke-MfaServiceReadTrial.ps1'
CODE=ROOT/'tools/windows/mfa-service-read-system/RackClick.MfaDiagnosticCode.ps1'
PS=shutil.which('powershell.exe')
LOAD=r'''
$ErrorActionPreference='Stop'
$text=[IO.File]::ReadAllText($env:RC_DIAGNOSTIC_SCRIPT).Replace("`r`n","`n")
$cut=$text.LastIndexOf("`ntry {`n    if (`$Mode")
if($cut -lt 0){throw 'dispatcher_missing'}
. ([scriptblock]::Create($text.Substring(0,$cut)))
. Import-DiagnosticPinnedFunctions $env:RC_DIAGNOSTIC_BASE $BasePin $false
. Import-DiagnosticPinnedFunctions $env:RC_DIAGNOSTIC_RESUME $ResumePin $true
. Import-ReferenceFunctions ([IO.File]::ReadAllText($env:RC_DIAGNOSTIC_REFERENCE))
Import-DiagnosticPinnedFunctions $env:RC_DIAGNOSTIC_CODE $CodeHelperPin $false
function Code([scriptblock]$Body){try{&$Body|Out-Null;return ''}catch{return Get-DiagnosticCode $_}}
'''

def environment():
    value=os.environ.copy()
    value['PSModulePath']=str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/Modules')+';'+str(Path(os.environ['ProgramFiles'])/'WindowsPowerShell/Modules')
    value.update(RC_DIAGNOSTIC_SCRIPT=str(SCRIPT),RC_DIAGNOSTIC_BASE=str(BASE),RC_DIAGNOSTIC_RESUME=str(RESUME),RC_DIAGNOSTIC_REFERENCE=str(REFERENCE),RC_DIAGNOSTIC_CODE=str(CODE))
    return value

@unittest.skipUnless(PS,'Windows PowerShell5.1 required')
class DiagnosticTests(unittest.TestCase):
    def focus(self,tail):
        with tempfile.TemporaryDirectory(prefix='rc-probe-diagnostic-focus-') as directory:
            path=Path(directory)/'focus.ps1';path.write_text(LOAD+tail,encoding='ascii')
            env=environment();env['RC_DIAGNOSTIC_FIXTURE']=directory
            result=subprocess.run([PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(path)],env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        return json.loads(result.stdout)

    def test_parser_selftest_and_all_leao_guards(self):
        data=self.focus(r'''
$tokens=$null;$errors=$null
$null=[Management.Automation.Language.Parser]::ParseFile($env:RC_DIAGNOSTIC_SCRIPT,[ref]$tokens,[ref]$errors)
@{errors=$errors.Count;version=$PSVersionTable.PSVersion.ToString()}|ConvertTo-Json -Compress
''')
        self.assertEqual(data['errors'],0)
        self.assertTrue(data['version'].startswith('5.1'))
        test=subprocess.run([PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(SCRIPT),'-Mode','SelfTest'],env=environment(),capture_output=True,text=True,timeout=60)
        self.assertEqual(test.returncode,0,test.stdout+test.stderr)
        self.assertEqual(json.loads(test.stdout)['checks'],4)
        if os.environ.get('COMPUTERNAME','').upper()=='LEAO':
            for mode in ('Check','Run','Worker'):
                reject=subprocess.run([PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(SCRIPT),'-Mode',mode],env=environment(),capture_output=True,text=True,timeout=60)
                self.assertEqual(reject.returncode,1)
                self.assertEqual(json.loads(reject.stdout)['code'],'host_excluded')

    def test_imported_task_validator_accepts_defaults_but_not_disabled(self):
        data=self.focus(r'''
$xml=Get-TaskXml 'C:\synthetic\worker.ps1' 'C:\synthetic\plan.json' ('a'*64) 'Synthetic'
$scheduler=New-Object -ComObject Schedule.Service
$definition=New-ResumeDefinition03 $scheduler $xml
[xml]$doc=$definition.XmlText
[void]$doc.Task.Settings.RemoveChild($doc.GetElementsByTagName('Enabled')[0])
Assert-ResumeTask03 $doc.OuterXml $xml $false
$disabled=[pscustomobject]@{Enabled=$false;Definition=[pscustomobject]@{Settings=[pscustomobject]@{Enabled=$true;MultipleInstances=2}}}
@{defaultsAccepted=$true;disabledRejected=((Code {Assert-RegisteredSettings03 $disabled}) -ceq 'task_enabled_invalid');created=$false}|ConvertTo-Json -Compress
''')
        self.assertTrue(data['defaultsAccepted'])
        self.assertTrue(data['disabledRejected'])
        self.assertFalse(data['created'])

    def test_protocol_is_closed_and_never_reports_mfa_pass(self):
        data=self.focus(r'''
$good='{"schemaVersion":1,"status":"measured","code":"exception_captured","exceptionType":"io","hresult":-1,"win32Error":0,"frames":["ReadService"],"outcome":null}'
$rows=@()
foreach($case in @('control','unknown_frame','unknown_type','extra_field','nonint_error','pass_status','false_outcome','long_frames','returned_null')) {
 $raw=$good|ConvertFrom-Json
 switch($case){
 'unknown_frame'{$raw.frames=@('C:\private\secret')}
 'unknown_type'{$raw.exceptionType='user_supplied'}
 'extra_field'{$raw|Add-Member Message 'private'}
 'nonint_error'{$raw.hresult='-1'}
 'pass_status'{$raw.status='passed'}
 'false_outcome'{$raw.outcome=[pscustomobject]@{key='private'}}
 'long_frames'{$raw.frames=@('ReadService')*17}
 'returned_null'{$raw.code='returned';$raw.exceptionType='none';$raw.hresult=0;$raw.frames=@();$raw.outcome=$null}
 }
 $code=Code {Assert-DiagnosticOutcome $raw}
 $rows+=@{case=$case;passed=$(if($case -ceq 'control'){$code -ceq ''}else{$code -ceq 'diagnostic_contract_invalid'})}
}
$result=@{status='measured';code='exception_captured';fingerprintState='unchanged';diagnostic=($good|ConvertFrom-Json)}
$summary=Get-DiagnosticSummary $result 'removed'
@{rows=$rows;status=$summary.status;notAccepted=$summary.notServiceReadAcceptance;notActivation=$summary.notMfaActivation;residueFails=((Get-DiagnosticSummary $result 'unconfirmed').status -ceq 'failed')}|ConvertTo-Json -Depth 8 -Compress
''')
        self.assertTrue(all(row['passed'] for row in data['rows']),data)
        self.assertEqual(data['status'],'measured')
        self.assertTrue(data['notAccepted'] and data['notActivation'] and data['residueFails'])

    def test_manifest_and_payload_tampering_are_rejected(self):
        data=self.focus(r'''
$root=Join-Path $env:RC_DIAGNOSTIC_FIXTURE 'package';[void][IO.Directory]::CreateDirectory($root)
foreach($rel in $DiagnosticRequired){$file=Join-Path $root $rel;[void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($file));[IO.File]::WriteAllText($file,'synthetic')}
$lines=@($DiagnosticRequired|ForEach-Object{(Get-DiagnosticHash (Join-Path $root $_))+'  '+$_})
$sums=Join-Path $root 'SHA256SUMS';[IO.File]::WriteAllLines($sums,$lines,[Text.Encoding]::ASCII);$pin=Get-DiagnosticHash $sums
$valid=Test-DiagnosticPackage $root $pin
$wrongPin=(Code{Test-DiagnosticPackage $root ('0'*64)}) -ceq 'package_sums_mismatch'
[IO.File]::WriteAllText((Join-Path $root $DiagnosticRequired[0]),'altered')
$altered=(Code{Test-DiagnosticPackage $root $pin}) -ceq 'package_hash_mismatch'
[IO.File]::AppendAllText($sums,('0'*64)+'  ../outside.txt'+"`n")
$path=(Code{Test-DiagnosticPackage $root (Get-DiagnosticHash $sums)}) -ceq 'diagnostic_sums_path_invalid'
@{valid=($valid.fileCount -eq $DiagnosticRequired.Count);wrongPin=$wrongPin;altered=$altered;path=$path}|ConvertTo-Json -Compress
''')
        self.assertTrue(all(data.values()),data)

    def test_new_marker_is_exclusive_old_marker_and_confirmation_preserved(self):
        data=self.focus(r'''
$root=$env:RC_DIAGNOSTIC_FIXTURE;$old=Join-Path $root 'old';$new=Join-Path $root 'new'
[void][IO.Directory]::CreateDirectory($old);[void][IO.Directory]::CreateDirectory($new)
[IO.File]::WriteAllText((Join-Path $old 'execution.started'),'retain')
Assert-DiagnosticNotStarted $new
[IO.File]::WriteAllText((Join-Path $new 'execution.started'),'retain-new')
$reject=(Code{Assert-DiagnosticNotStarted $new}) -ceq 'diagnostic_already_started'
$phrase=(Code{Assert-DiagnosticConfirmation 'CONFIRMO LECTURA SYSTEM id' 'id'}) -ceq 'confirmation_mismatch'
@{newReject=$reject;oldUnchanged=([IO.File]::ReadAllText((Join-Path $old 'execution.started')) -ceq 'retain');confirmationRejected=$phrase}|ConvertTo-Json -Compress
''')
        self.assertTrue(all(data.values()),data)

    def test_plan_json_hash_is_exact_and_overwrite_fails(self):
        data=self.focus(r'''
$plan=[ordered]@{schemaVersion=1;taskName='synthetic';count=5};$text=$plan|ConvertTo-Json -Depth 12 -Compress
$file=Join-Path $env:RC_DIAGNOSTIC_FIXTURE 'plan.json';Write-NewJson $file $plan
$same=(Hash-File $file) -ceq (Hash-Text $text);$rejected=$false
try{Write-NewJson $file $plan}catch{$rejected=$true}
@{same=$same;overwriteRejected=$rejected}|ConvertTo-Json -Compress
''')
        self.assertTrue(all(data.values()),data)

    def test_static_order_and_no_removal_of_consumed_attempt(self):
        text=SCRIPT.read_text(encoding='ascii')
        for forbidden in ('Remove-Item','DeleteFile','Set-Acl','Expand-Archive','--mfa-keys-init'):
            self.assertNotIn(forbidden,text)
        self.assertIn('" measure --probe "',text)
        self.assertLess(text.index('$definition,1,'),text.index('Confirm-Diagnostic $plan.installationId'))
        self.assertLess(text.index('Confirm-Diagnostic $plan.installationId'),text.index('New-PrivateRoot $plannedRoot'))
        self.assertLess(text.index('Assert-RegisteredSettings03 $task'),text.index('$task.Run($null)'))
        self.assertIn("'execution.started'",text)
        self.assertIn('diagnostic_already_started',text)
        self.assertIn('Assert-DiagnosticOutcome $raw',text)

if __name__=='__main__':unittest.main(verbosity=2)
