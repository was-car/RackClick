"""Actual preflight prefix and pinned importers; only elevation/ACL guards mocked.

No SCM, task registration, provider/key access or changes to existing artifacts.
RC_DIAGNOSTIC_SCOPE_TARGET selects preserved01 for the red reproduction.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
TARGET=Path(os.environ.get('RC_DIAGNOSTIC_SCOPE_TARGET',str(ROOT/'tools/windows/mfa-service-read-system/Invoke-MfaProbeExceptionDiagnostic.ps1')))
BASE=ROOT/'tools/windows/mfa-service-read-system/Invoke-MfaServiceReadSystemTrial.ps1'
RESUME=ROOT/'tools/windows/mfa-service-read-system/Resume-MfaServiceReadSystemTrial03.ps1'
CODE=ROOT/'tools/windows/mfa-service-read-system/RackClick.MfaDiagnosticCode.ps1'
PS=shutil.which('powershell.exe')

@unittest.skipUnless(PS,'Windows PowerShell5.1 required')
class ImportScopeTests(unittest.TestCase):
    def test_actual_context_prefix_does_not_type_or_overwrite_callers_variables(self):
        body=r'''
$ErrorActionPreference='Stop'
$text=[IO.File]::ReadAllText($env:RC_SCOPE_SOURCE).Replace("`r`n","`n")
$cut=$text.LastIndexOf("`ntry {`n    if (`$Mode")
if($cut -lt 0){throw 'dispatcher_missing'}
. ([scriptblock]::Create($text.Substring(0,$cut)))
$env:ProgramData=$env:RC_SCOPE_FIXTURE
$AttemptRoot=Join-Path $env:ProgramData ($WorkPrefix+'8637bb52faee4b2a96992bcf4d7591b8')
[void][IO.Directory]::CreateDirectory($AttemptRoot)
[IO.File]::Copy($env:RC_SCOPE_BASE,(Join-Path $AttemptRoot 'worker.ps1'))
$package=Join-Path $env:RC_SCOPE_FIXTURE 'package';[void][IO.Directory]::CreateDirectory($package)
[IO.File]::Copy($env:RC_SCOPE_RESUME,(Join-Path $package 'Resume-MfaServiceReadSystemTrial03.ps1'))
[IO.File]::Copy($env:RC_SCOPE_CODE,(Join-Path $package 'RackClick.MfaDiagnosticCode.ps1'))
$tokens=$null;$parseErrors=$null;$ast=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$parseErrors)
$node=@($ast.EndBlock.Statements|Where-Object{$_ -is [Management.Automation.Language.FunctionDefinitionAst] -and $_.Name -ceq 'Read-DiagnosticContext'})[0]
$prefix=$node.Extent.Text.Substring(0,$node.Extent.Text.IndexOf('$oldPlanFile='))
# Preserve actual parameters and the two import calls; only avoid real elevation/ACL checks.
if(-not $prefix.Contains('Assert-Elevated;Assert-PrivateRoot $AttemptRoot') -or -not $prefix.Contains('Assert-ResumeRoot03 $AttemptRoot')){throw 'fixture_contract_changed'}
$prefix=$prefix.Replace('Read-DiagnosticContext','Read-FixtureContext').Replace('Assert-Elevated;Assert-PrivateRoot $AttemptRoot','$null=$null').Replace('Assert-ResumeRoot03 $AttemptRoot','$null=$null')
$brace=$prefix.IndexOf('{')+1
$prefix=$prefix.Insert($brace,"`n`$Path='caller-path';`$Pin='caller-pin';`$definitions='caller-definitions'`n")
$fixtureFunction=$prefix+@'
return @{passed=($resume -is [string] -and $resume -ceq (Join-Path $NewPackage 'Resume-MfaServiceReadSystemTrial03.ps1') -and $Path -ceq 'caller-path' -and $Pin -ceq 'caller-pin' -and $definitions -ceq 'caller-definitions');exportsAvailable=([bool](Get-Command Assert-ResumeTask03 -ErrorAction SilentlyContinue));leases=$Leases.Count}
}
'@
. ([scriptblock]::Create($fixtureFunction))
$leases=New-Object Collections.Generic.List[IDisposable]
try {
 $result=Read-FixtureContext $leases $env:RC_SCOPE_SOURCE (Get-DiagnosticHash $env:RC_SCOPE_SOURCE) $package ('a'*64)
 $result|ConvertTo-Json -Compress
} catch {
 $kinds=@();$codes=@();$exception=$_.Exception
 while($null -ne $exception){$kinds+=$exception.GetType().FullName;$codes+=[int]$exception.HResult;$exception=$exception.InnerException}
 @{passed=$false;types=$kinds;hresults=$codes}|ConvertTo-Json -Compress
} finally {foreach($lease in $leases){$lease.Dispose()}}
'''
        with tempfile.TemporaryDirectory(prefix='rc-diagnostic-scope-') as directory:
            path=Path(directory)/'test.ps1';path.write_text(body,encoding='ascii')
            env=os.environ.copy();env.update(RC_SCOPE_SOURCE=str(TARGET),RC_SCOPE_BASE=str(BASE),RC_SCOPE_RESUME=str(RESUME),RC_SCOPE_CODE=str(CODE),RC_SCOPE_FIXTURE=directory)
            env['PSModulePath']=str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/Modules')
            result=subprocess.run([PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(path)],env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        data=json.loads(result.stdout)
        self.assertTrue(data['passed'],data)
        self.assertTrue(data['exportsAvailable'],data)
        self.assertEqual(data['leases'],4)

if __name__=='__main__':unittest.main(verbosity=2)
