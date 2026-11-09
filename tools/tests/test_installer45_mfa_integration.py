"""Exercise real PowerShell conditions/functions; never execute an installer or DB.

RACKCLICK_OP45_SOURCE_ROOT optionally selects the preserved pre-change script tree
for the red run. Shared bundle profile functions still come from the repository.
"""
import base64
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get('RACKCLICK_OP45_SOURCE_ROOT', ROOT))
PS = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
PIN15 = '294b61577ed7aa8fe68ddb1ecd6c4f11a20b4f03935c11a22404009aec6a00fb'
PIN43 = '29685419d0746df89777a5da72d25f5b7ac0e571e30decec1888787fe5f0f950'
PIN45 = '528a03d2efc939d1cea631b1caa9f3e6a445e44257fa757f87a95691acfb6933'
PIN14 = '2ec9105661db0f5c9a97d58e2a7f44e69bfd7e1903493b72f0fc57cc94c4b71a'


class Installer45MfaIntegration(unittest.TestCase):
    def invoke(self, body):
        prefix = r'''
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
Set-StrictMode -Version Latest
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$repo=__REPO__;$source=__SOURCE__
. (Join-Path $repo 'tools/windows/RackClick.OfflineBundle.ps1')
. (Join-Path $source 'tools/windows/server-install/RackClick.SetupMfa.ps1')
function Parse-Script([string]$Relative){
 $tokens=$null;$errors=$null
 $tree=[Management.Automation.Language.Parser]::ParseFile((Join-Path $source $Relative),[ref]$tokens,[ref]$errors)
 if($errors.Count-ne0){throw 'parser_failed'}
 return $tree
}
$installer=Parse-Script 'tools/windows/server-install/Install-RackClickServer.ps1'
$mfa=Parse-Script 'tools/windows/server-install/RackClick.SetupMfa.ps1'
$recovery=Parse-Script 'tools/windows/New-RackClickRecoveredInstance.ps1'
foreach($name in @('Stop-RecoveryCheck','Get-RecoverySchemaTransition','Assert-RecoveryMfaMaterial')){
 $found=@($recovery.FindAll({param($n) $n-is[Management.Automation.Language.FunctionDefinitionAst]-and$n.Name-ceq$name},$true))
 if($found.Count-ne1){throw 'recovery_helper_missing'}
 . ([scriptblock]::Create($found[0].Extent.Text))
}
function Actual-MfaSchema([string]$Pin){
 if(Get-Command Get-SetupMfaApplicationSchema -ErrorAction SilentlyContinue){return Get-SetupMfaApplicationSchema $Pin}
 # Red: execute the exact old guard, stopping before content/process provisioning.
 $bundle=@{manifest=@{applicationManifestSha256=$Pin}}
 $guard=@($mfa.FindAll({param($n) $n-is[Management.Automation.Language.IfStatementAst]-and$n.Extent.Text-like"*throw 'setup_mfa_schema_required_*"},$true))
 if($guard.Count-ne1){throw 'schema_guard_missing'}
 . ([scriptblock]::Create($guard[0].Extent.Text))
 return Get-OfflineBundleExpectedSchema (Get-OfflineBundleApplicationProfile $Pin)
}
function Actual-Readiness($Health,$Expected,[string]$State){
 $health=$Health;$setupApplicationSchema=$Expected;$setupPlan=@{serviceName='synthetic-never-queried'}
 function Get-Service {param($Name) return [pscustomobject]@{Status=$State}}
 $conditions=@($installer.FindAll({param($n) $n-is[Management.Automation.Language.IfStatementAst]-and($n.Extent.Text-like'if($health.status*'-or$n.Extent.Text-like'if(Test-SetupMfaReadiness*')},$true))
 if($conditions.Count-ne1){throw 'readiness_condition_missing'}
 $condition=$conditions[0].Clauses[0].Item1.Extent.Text
 return [bool](& ([scriptblock]::Create($condition)))
}
function Actual-InstalledReceiptSchema([int]$Expected){
 $setupApplicationSchema=$Expected;$setupReceipt=@{}
 $a=@($installer.FindAll({param($n) $n-is[Management.Automation.Language.AssignmentStatementAst]-and$n.Left.Extent.Text-ceq'$setupReceipt.applicationSchemaVersion'},$true))
 if($a.Count-ne1){throw 'receipt_assignment_missing'}
 . ([scriptblock]::Create($a[0].Extent.Text))
 return $setupReceipt.applicationSchemaVersion
}
function Actual-MfaReceiptSchema([int]$Expected){
 $applicationSchema=$Expected
 $a=@($mfa.FindAll({param($n) $n-is[Management.Automation.Language.ReturnStatementAst]-and$n.Extent.Text-like"*code='setup_mfa_store_created'*"},$true))
 if($a.Count-ne1){throw 'mfa_receipt_missing'}
 $value=& ([scriptblock]::Create($a[0].Pipeline.Extent.Text))
 if(-not$value.ContainsKey('applicationSchemaVersion')){return $null}
 return $value.applicationSchemaVersion
}
function Transition([int]$Target,[string]$Applied){
 try{return @{accepted=$true;transition=(Get-RecoverySchemaTransition $Target $Applied)}}
 catch{return @{accepted=$false;code=[string]$_.Exception.Data['recoveryCode']}}
}
'''.replace('__REPO__', "'"+str(ROOT).replace("'", "''")+"'").replace('__SOURCE__', "'"+str(SOURCE).replace("'", "''")+"'")
        encoded = base64.b64encode((prefix + body).encode('utf-16le')).decode()
        p = subprocess.run([str(PS), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                            '-EncodedCommand', encoded], capture_output=True, timeout=45)
        self.assertEqual(p.returncode, 0, p.stderr.decode(errors='replace'))
        self.assertFalse(p.stderr)
        return json.loads(p.stdout.decode('utf-8-sig'))

    def test_01_pinned45_is_admitted(self):
        r=self.invoke("try{@{accepted=$true;schema=(Actual-MfaSchema '"+PIN45+"')}|ConvertTo-Json -Compress}catch{@{accepted=$false}|ConvertTo-Json -Compress}")
        self.assertEqual(r, dict(accepted=True,schema=45))

    def test_02_historical15_and43_are_admitted(self):
        r=self.invoke("@{v15=(Actual-MfaSchema '"+PIN15+"');v43=(Actual-MfaSchema '"+PIN43+"')}|ConvertTo-Json -Compress")
        self.assertEqual(r, dict(v15=15,v43=43))

    def test_03_unknown_pin_and_pre_mfa_schema_rejected(self):
        r=self.invoke("$out=@();foreach($pin in @('"+'0'*64+"','"+PIN14+"')){try{$null=Actual-MfaSchema $pin;$out+=@{accepted=$true}}catch{$out+=@{accepted=$false}}};ConvertTo-Json -InputObject $out -Compress")
        self.assertEqual(r,[dict(accepted=False),dict(accepted=False)])

    def test_04_each_supported_readiness_matches_its_pinned_schema(self):
        r=self.invoke("$out=@();foreach($s in @(15,43,45)){$out+=Actual-Readiness ([pscustomobject]@{status='ready';schemaVersion=$s}) $s 'Running'};ConvertTo-Json -InputObject $out -Compress")
        self.assertEqual(r,[True,True,True])

    def test_05_other_schema_and_nonrunning_service_never_succeed(self):
        r=self.invoke("@{oldForNew=(Actual-Readiness ([pscustomobject]@{status='ready';schemaVersion=43}) 45 'Running');newForOld=(Actual-Readiness ([pscustomobject]@{status='ready';schemaVersion=45}) 43 'Running');stopped=(Actual-Readiness ([pscustomobject]@{status='ready';schemaVersion=45}) 45 'Stopped')}|ConvertTo-Json -Compress")
        self.assertEqual(r,dict(oldForNew=False,newForOld=False,stopped=False))

    def test_06_untyped_or_unsupported_readiness_rejected(self):
        r=self.invoke("$out=@();foreach($v in @('43','45',45.0,-1,0,44,999)){$out+=Actual-Readiness ([pscustomobject]@{status='ready';schemaVersion=$v}) 45 'Running'};$out+=Actual-Readiness ([pscustomobject]@{status='Ready';schemaVersion=45}) 45 'Running';$out+=Actual-Readiness ([pscustomobject]@{status='ready';schemaVersion=44}) 44 'Running';ConvertTo-Json -InputObject $out -Compress")
        self.assertEqual(r,[False]*9)

    def test_07_installed_receipt_uses_the_observed_pinned_version(self):
        r=self.invoke("@{v43=(Actual-InstalledReceiptSchema 43);v45=(Actual-InstalledReceiptSchema 45)}|ConvertTo-Json -Compress")
        self.assertEqual(r,dict(v43=43,v45=45))

    def test_08_mfa_success_receipt_carries_its_pinned_application_version(self):
        r=self.invoke("@{v43=(Actual-MfaReceiptSchema 43);v45=(Actual-MfaReceiptSchema 45)}|ConvertTo-Json -Compress")
        self.assertEqual(r,dict(v43=43,v45=45))

    def test_09_restore45_migrates_only_explicit_supported_sources(self):
        r=self.invoke("$out=@();foreach($s in @(13,14,15,43)){$out+=Transition 45 ((1..$s)-join ',')};$out+=Transition 45 ((1..45)-join ',');ConvertTo-Json -InputObject $out -Compress")
        self.assertEqual([v.get('transition') for v in r],['migrate']*4+['current'])

    def test_10_invalid_histories_downgrades_and44_rejected(self):
        r=self.invoke("$out=@();foreach($s in @(((1..44)-join ','),'1,2,4',(((1..43)-join ',')+',43'),(((1..43)-join ',')+',999'))){$out+=Transition 45 $s};$out+=Transition 44 ((1..44)-join ',');$out+=Transition 43 ((1..45)-join ',');ConvertTo-Json -InputObject $out -Compress")
        self.assertEqual([v['accepted'] for v in r],[False]*6)

    def test_11_recovery_mfa_guard_retained_for_any_nonzero_material(self):
        r=self.invoke("$out=@();foreach($v in @('0','1','2','-1','00',' 0','')){try{Assert-RecoveryMfaMaterial 45 $v;$out+=@{accepted=$true}}catch{$out+=@{accepted=$false;code=[string]$_.Exception.Data['recoveryCode']}}};ConvertTo-Json -InputObject $out -Compress")
        self.assertTrue(r[0]['accepted'])
        self.assertEqual(r[1:],[dict(accepted=False,code='recovery_mfa_envelope_required')]*6)

    def test_12_historical_recovery_matrix_remains_closed(self):
        r=self.invoke("$out=@();foreach($s in @(9,10,11,12,13,14,15,43)){$out+=Transition $s ((1..$s)-join ',')};$out+=Transition 14 ((1..13)-join ',');$out+=Transition 15 ((1..14)-join ',');$out+=Transition 43 ((1..15)-join ',');ConvertTo-Json -InputObject $out -Compress")
        self.assertEqual([v.get('transition') for v in r],['current']*8+['migrate']*3)

    def test_13_receipt_input_type_is_checked_before_service_creation(self):
        text=(SOURCE/'tools/windows/server-install/Install-RackClickServer.ps1').read_text(encoding='utf-8-sig')
        gate="throw 'setup_mfa_schema_receipt_invalid'"
        self.assertIn(gate,text)
        self.assertLess(text.index(gate),text.index('New-Service -Name'))
        self.assertIn('$setupMfaResult.applicationSchemaVersion -isnot [int]',text)

    def test_14_real_mfa_setup_derives_version_after_archive_verification(self):
        text=(SOURCE/'tools/windows/server-install/RackClick.SetupMfa.ps1').read_text(encoding='utf-8-sig')
        start=text.index('function Initialize-SetupMfaStore')
        block=text[start:]
        assignment='$applicationSchema=Get-SetupMfaApplicationSchema $bundle.manifest.applicationManifestSha256'
        self.assertIn(assignment,block)
        self.assertLess(block.index('Read-RackClickOfflineBundle -ArchivePath'),block.index(assignment))
        self.assertLess(block.index(assignment),block.index('$process.Start()'))

    def test_15_changed_scripts_parse_on_windows_powershell51(self):
        r=self.invoke("@{major=$PSVersionTable.PSVersion.Major;parsed=3}|ConvertTo-Json -Compress")
        self.assertEqual(r,dict(major=5,parsed=3))


if __name__ == '__main__':
    unittest.main()
