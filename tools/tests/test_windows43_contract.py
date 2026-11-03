"""Focused native Windows43 contracts; no installation, services or existing DBs."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PS = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
TABLES = ('hardware_definition', 'hardware_mount_slot', 'hardware_group_template', 'hardware_passthrough',
          'hardware_connector_template', 'hardware_profile_extension', 'hardware_group_extension')
PROBE = r'''
param([string]$Root,[string]$Work)
$ErrorActionPreference='Stop'
. (Join-Path $Root 'tools/windows/RackClick.Instance.ps1')
. (Join-Path $Root 'tools/windows/New-RackClickRecoveredInstance.ps1')
function Import-OneFunction([string]$File,[string]$Name) {
    $tokens=$null;$errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $Root $File),[ref]$tokens,[ref]$errors)
    if($errors.Count-ne0){throw 'syntax_invalid'}
    $fn=$ast.FindAll({param($n)$n-is[Management.Automation.Language.FunctionDefinitionAst]-and$n.Name-ceq$Name},$true)|Select-Object -First 1
    if($null-eq$fn){throw 'function_missing'}
    return $fn.Extent.Text
}
$out=@{counts=@{};schemas=@{};transitions=@{};mfa=@{};ready=@{};postboot=@{};sql=@{};sqlInvalid=@{}}
foreach($s in @(8,9,10,11,12,13,14,15,16,42,43,44)){
    try{$out.counts["$s"]=Get-StageVerifiedFileCount $s}catch{$out.counts["$s"]=[string]$_.Exception.Data['stageCode']}
    $dir=Join-Path $Work "s$s";[IO.Directory]::CreateDirectory($dir)|Out-Null
    [IO.File]::WriteAllText((Join-Path $dir 'manifest.json'),('{"schema":'+$s+'}'))
    try{$out.schemas["$s"]=Get-StageSchema $dir}catch{$out.schemas["$s"]=[string]$_.Exception.Data['stageCode']}
    try{$out.transitions["$s"]=Get-RecoverySchemaTransition 43 ((1..$s)-join ',')}catch{$out.transitions["$s"]=[string]$_.Exception.Data['recoveryCode']}
}
foreach($s in @(13,14,15,43)){
    foreach($f in @('0','1','-1','invalid')){
        try{Assert-RecoveryMfaMaterial $s $f;$out.mfa["$s/$f"]='accepted'}catch{$out.mfa["$s/$f"]=[string]$_.Exception.Data['recoveryCode']}
    }
}
foreach($file in @('tools/windows/Start-RackClickLabInstance.ps1','tools/windows/server-install/Invoke-RackClickServerRuntime.ps1')){
    Invoke-Expression (Import-OneFunction $file 'Test-LauncherReadyBody')
    $out.ready[$file]=@{}
    foreach($s in @(9,13,14,15,16,42,43,44)){
        $out.ready[$file]["$s"]=[bool](Test-LauncherReadyBody ([pscustomobject]@{status='ready';schemaVersion=$s}) $s)
    }
    $out.ready[$file].mismatch=[bool](Test-LauncherReadyBody ([pscustomobject]@{status='ready';schemaVersion=15}) 43)
}
Invoke-Expression (Import-OneFunction 'tools/windows/server-install/RackClick.Setup.Lifecycle.ps1' 'Test-SetupPostbootSnapshot')
$snapshot=@{bootCurrent='2026-11-02T11:00:00Z';bootAtInstall='2026-11-02T10:00:00Z';serviceState='Running';serviceStartMode='Auto';serviceSid='S-1-5-21-1-2-3-1001';expectedSid='S-1-5-21-1-2-3-1001';healthStatus='ready';schemaVersion=43;expectedSchemaVersion=43;backupTaskState='Ready';backupTaskSid='S-1-5-21-1-2-3-1001';backupLastResult=0;backupScheduleVerified=$true}
$out.postboot.good=Test-SetupPostbootSnapshot $snapshot
$snapshot.schemaVersion=15;$out.postboot.mismatch=Test-SetupPostbootSnapshot $snapshot
$snapshot.expectedSchemaVersion=42;$snapshot.schemaVersion=42;$out.postboot.unsupported=Test-SetupPostbootSnapshot $snapshot
foreach($s in @(13,15,43)){
    try{$out.sql["$s"]=Get-InstanceRuntimeGrantsSql ('rc_runtime_'+('a'*32)) $s}catch{$out.sql["$s"]='unavailable'}
}
foreach($role in @('x; DROP TABLE hardware_definition;','rc_runtime_a','rc_owner_'+('a'*32))){
    try{$null=Get-InstanceRuntimeGrantsSql $role 43;$out.sqlInvalid[$role]='accepted'}catch{$out.sqlInvalid[$role]='rejected'}
}
$out|ConvertTo-Json -Compress -Depth 8
'''


@unittest.skipUnless(os.name == 'nt' and PS.exists(), 'requires Windows PowerShell 5.1')
class Windows43ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = Path(tempfile.mkdtemp(prefix='windows43-contract-', dir=ROOT / '.local'))
        cls.addClassCleanup(shutil.rmtree, cls.work, True)
        script = cls.work / 'probe.ps1'
        script.write_text(PROBE, encoding='ascii')
        run = subprocess.run([str(PS), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(script),
                              '-Root', str(ROOT), '-Work', str(cls.work)], capture_output=True, text=True, encoding='utf-8', timeout=90)
        if run.returncode:
            raise AssertionError(run.stderr + run.stdout)
        cls.measured = json.loads(run.stdout)

    def test_explicit_stage_counts_and_schema(self):
        for schema in (9, 10, 11, 12, 13, 14, 15, 43):
            count = 71 if schema == 43 else 28 + schema if schema >= 14 else 27 + schema
            self.assertEqual(self.measured['counts'][str(schema)], count)
            self.assertEqual(self.measured['schemas'][str(schema)], schema)
        for schema in (8, 16, 42, 44):
            self.assertEqual(self.measured['counts'][str(schema)], 'manifest_distribution_unsupported')
            self.assertEqual(self.measured['schemas'][str(schema)], 'manifest_distribution_unsupported')

    def test_restore43_sources_are_closed(self):
        for schema in (13, 14, 15):
            self.assertEqual(self.measured['transitions'][str(schema)], 'migrate')
        self.assertEqual(self.measured['transitions']['43'], 'current')
        for schema in (8, 9, 10, 11, 12, 16, 42, 44):
            self.assertEqual(self.measured['transitions'][str(schema)], 'restored_schema_required_43')

    def test_restore43_factors_rejected_including_disabled_material(self):
        self.assertEqual(self.measured['mfa']['43/0'], 'accepted')
        for count in ('1', '-1', 'invalid'):
            self.assertEqual(self.measured['mfa']['43/' + count], 'recovery_mfa_envelope_required')

    def test_readiness43_exact_and_no_intermediates(self):
        for result in self.measured['ready'].values():
            for schema in (9, 13, 14, 15, 43):
                self.assertTrue(result[str(schema)])
            for schema in (16, 42, 44):
                self.assertFalse(result[str(schema)])
            self.assertFalse(result['mismatch'])

    def test_postboot43_contract_does_not_accept_wrong_schema(self):
        self.assertEqual(self.measured['postboot']['good'], {'valid': True, 'code': 'postboot_verified'})
        self.assertEqual(self.measured['postboot']['mismatch']['code'], 'postboot_application_not_ready')
        self.assertEqual(self.measured['postboot']['unsupported']['code'], 'postboot_expected_schema_invalid')

    def test_grants43_read_only_closed_catalogue(self):
        sql = self.measured['sql']['43']
        self.assertIn('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public', sql)
        for table in TABLES:
            self.assertIn('public.' + table, sql)
        self.assertIn('REVOKE ALL PRIVILEGES ON TABLE', sql)
        self.assertIn('GRANT SELECT ON TABLE', sql)
        self.assertNotIn('ALTER DEFAULT PRIVILEGES', sql)
        for schema in (13, 15):
            self.assertNotIn('hardware_', self.measured['sql'][str(schema)])

    def test_grants_reject_external_identifier(self):
        self.assertEqual(set(self.measured['sqlInvalid'].values()), {'rejected'})

    def test_new_restore_call_central_permission_contract(self):
        for name in ('New-RackClickLabInstance.ps1', 'New-RackClickRecoveredInstance.ps1'):
            text = (ROOT / 'tools/windows' / name).read_text(encoding='utf-8')
            self.assertNotIn('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES', text)
            self.assertIn('Get-InstanceRuntimeGrantsSql $runtime $stageSchema', text)
        for name in ('New-RackClickPrivateDeployment.ps1', 'Restore-RackClickPrivateDeployment.ps1'):
            text = (ROOT / 'tools/windows' / name).read_text(encoding='utf-8')
            self.assertIn('Get-StageVerifiedFileCount $sourceManifest.schema', text)

    def test_restore_checks_factor_material_for_43(self):
        text = (ROOT / 'tools/windows/New-RackClickRecoveredInstance.ps1').read_text(encoding='utf-8')
        self.assertRegex(text, r'if\(\$stageSchema -ge 15\)\{\s*\$restoredFactorCount=')
        self.assertIn('Assert-RecoveryMfaMaterial -TargetSchema $stageSchema -FactorCount $restoredFactorCount', text)

    def test_changed_operator_files_parse_on_powershell51(self):
        files = ('tools/windows/RackClick.Stage.ps1', 'tools/windows/RackClick.Instance.ps1',
                 'tools/windows/New-RackClickLabInstance.ps1', 'tools/windows/New-RackClickRecoveredInstance.ps1',
                 'tools/windows/New-RackClickPrivateDeployment.ps1', 'tools/windows/Restore-RackClickPrivateDeployment.ps1',
                 'tools/windows/Start-RackClickLabInstance.ps1', 'tools/windows/server-install/Invoke-RackClickServerRuntime.ps1',
                 'tools/windows/server-install/RackClick.Setup.Lifecycle.ps1', 'tools/windows/server-install/RackClick.SetupMfa.ps1')
        script = self.work / 'parser.ps1'
        paths = ','.join("'" + str(ROOT / path).replace("'", "''") + "'" for path in files)
        script.write_text("$ErrorActionPreference='Stop';foreach($p in @(" + paths + ")){$t=$null;$e=$null;"
                          "[Management.Automation.Language.Parser]::ParseFile($p,[ref]$t,[ref]$e)|Out-Null;"
                          "if($e.Count-ne0){throw 'parse_failed'}};'10 parsed'", encoding='ascii')
        run = subprocess.run([str(PS), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(script)],
                             capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.strip(), '10 parsed')


if __name__ == '__main__':
    unittest.main()
