"""Pruebas activas del contrato de Stage y readiness para el esquema 14 (PowerShell 5.1).

Cubren: conteos cerrados por esquema, aceptación de Get-StageSchema, readiness de los dos lanzadores (extraída con el
parser de PowerShell, sin ejecutar el resto de cada script), y un stage real de la candidata 14 verificado en solo lectura.
Todo se escribe bajo .local en carpetas temporales que se borran al terminar. Las candidatas no se modifican.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POWERSHELL = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'
CANDIDATE = ROOT / '.local' / 'distribution14' / 'candidata-01'
DOTNET = ROOT / '.local' / 'dotnet-10.0.401' / 'dotnet.exe'
PG_BIN = ROOT / '.local' / 'labs' / 'mfa-m1-20261023' / 'pgsql' / 'bin'
MANIFEST_14 = '2ec9105661db0f5c9a97d58e2a7f44e69bfd7e1903493b72f0fc57cc94c4b71a'
STAGE_TEST = ROOT / 'tools' / 'windows' / 'Stage-ServerDistribution.ps1'
TEST_STAGED = ROOT / 'tools' / 'windows' / 'Test-StagedDistribution.ps1'

CONTRACT_SCRIPT = r'''
param([string]$Root,[string]$Probe)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
. (Join-Path $Root 'tools/windows/RackClick.Stage.ps1')
$out=[ordered]@{}
foreach ($schema in 9..14) {
    $out["server$schema"]=Get-StageServerFileCount $schema
    $out["verified$schema"]=Get-StageVerifiedFileCount $schema
}
foreach ($bad in @(8,15)) {
    try { $null=Get-StageServerFileCount $bad; $out["bad$bad"]='accepted' } catch { $out["bad$bad"]=[string]$_.Exception.Data['stageCode'] }
}
foreach ($schema in @(13,14,15)) {
    $dir=Join-Path $Probe "s$schema"
    New-Item -ItemType Directory -Path $dir | Out-Null
    [IO.File]::WriteAllText((Join-Path $dir 'manifest.json'),('{"schema":'+$schema+'}'),(New-Object Text.UTF8Encoding($false)))
    try { $out["schema$schema"]=Get-StageSchema $dir } catch { $out["schema$schema"]=[string]$_.Exception.Data['stageCode'] }
}
foreach ($file in @('tools/windows/server-install/Invoke-RackClickServerRuntime.ps1','tools/windows/Start-RackClickLabInstance.ps1')) {
    $tokens=$null;$errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $Root $file),[ref]$tokens,[ref]$errors)
    $definition=$ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Test-LauncherReadyBody'},$true)|Select-Object -First 1
    Invoke-Expression $definition.Extent.Text
    $name=(Split-Path $file -Leaf) -replace '\.ps1$',''
    $out["ready14_$name"]=[bool](Test-LauncherReadyBody ([pscustomobject]@{status='ready';schemaVersion=14}) 14)
    $out["ready13body_expect14_$name"]=[bool](Test-LauncherReadyBody ([pscustomobject]@{status='ready';schemaVersion=13}) 14)
    $out["ready14body_expect13_$name"]=[bool](Test-LauncherReadyBody ([pscustomobject]@{status='ready';schemaVersion=14}) 13)
    $out["ready15_$name"]=[bool](Test-LauncherReadyBody ([pscustomobject]@{status='ready';schemaVersion=15}) 15)
}
$out|ConvertTo-Json -Compress
'''


def run_ps(script: Path, *args: str) -> tuple[int, str]:
    command = [str(POWERSHELL), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(script), *args]
    completed = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
    return completed.returncode, completed.stdout.strip()


@unittest.skipUnless(sys.platform == 'win32' and POWERSHELL.exists(), 'requiere Windows PowerShell 5.1')
class StageContractTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix='rc-stage14-', dir=ROOT / '.local'))
        self.addCleanup(shutil.rmtree, self.work, True)
        self.script = self.work / 'contract.ps1'
        self.script.write_text(CONTRACT_SCRIPT, encoding='utf-8')

    def contract(self) -> dict:
        probe = self.work / 'probe'
        probe.mkdir()
        code, output = run_ps(self.script, '-Root', str(ROOT), '-Probe', str(probe))
        self.assertEqual(code, 0, output)
        return json.loads(output)

    def test_server_counts_are_closed_per_schema(self):
        result = self.contract()

        self.assertEqual({s: result[f'server{s}'] for s in range(9, 15)}, {9: 18, 10: 19, 11: 20, 12: 21, 13: 22, 14: 24})
        self.assertEqual({s: result[f'verified{s}'] for s in range(9, 15)}, {9: 36, 10: 37, 11: 38, 12: 39, 13: 40, 14: 42})

    def test_unsupported_schema_is_refused_with_stable_code(self):
        result = self.contract()

        self.assertEqual(result['bad8'], 'manifest_distribution_unsupported')
        self.assertEqual(result['bad15'], 'manifest_distribution_unsupported')
        self.assertEqual(result['schema15'], 'manifest_distribution_unsupported')

    def test_get_stage_schema_accepts_14_and_keeps_13(self):
        result = self.contract()

        self.assertEqual((result['schema13'], result['schema14']), (13, 14))

    def test_readiness_accepts_14_only_for_expected_14(self):
        result = self.contract()

        for launcher in ('Invoke-RackClickServerRuntime', 'Start-RackClickLabInstance'):
            with self.subTest(launcher=launcher):
                self.assertTrue(result[f'ready14_{launcher}'])
                self.assertFalse(result[f'ready13body_expect14_{launcher}'])
                self.assertFalse(result[f'ready14body_expect13_{launcher}'])
                self.assertFalse(result[f'ready15_{launcher}'])


@unittest.skipUnless(sys.platform == 'win32' and CANDIDATE.is_dir() and DOTNET.exists() and PG_BIN.is_dir(),
                     'requiere la candidata 14, el SDK de .NET 10 y los binarios de PostgreSQL en .local')
class StageRealRunTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix='rc-stage14-real-', dir=ROOT / '.local'))
        self.addCleanup(shutil.rmtree, self.work, True)
        self.destination = self.work / 'stage'

    def stage(self, expected: str) -> tuple[int, dict]:
        code, output = run_ps(STAGE_TEST, '-ManifestPath', str(CANDIDATE / 'manifest.json'), '-ExpectedManifestSha256', expected,
                              '-ServerPath', str(CANDIDATE / 'server'), '-FrontendPath', str(CANDIDATE / 'frontend'),
                              '-DotNetPath', str(DOTNET), '-PostgresBinPath', str(PG_BIN), '-DestinationPath', str(self.destination))
        return code, json.loads(output.splitlines()[-1])

    def test_candidate_14_stages_and_verifies_read_only(self):
        code, report = self.stage(MANIFEST_14)

        self.assertEqual((code, report['code']), (0, 'artifacts_staged'))
        self.assertEqual(report['verifiedFiles'], 42)
        # El recibo incluye stageId y la hora UTC: su digest es propio de cada ejecución, no un valor fijo.
        self.assertRegex(report['receiptSha256'], r'^[a-f0-9]{64}$')
        code, verified = run_ps(TEST_STAGED, '-DestinationPath', str(self.destination),
                                '-ExpectedManifestSha256', MANIFEST_14, '-ExpectedReceiptSha256', report['receiptSha256'])
        self.assertEqual(code, 0, verified)
        self.assertEqual(json.loads(verified)['code'], 'staging_verified')

    def test_stage_refuses_14_with_wrong_manifest_digest_before_creating_output(self):
        code, report = self.stage('1' * 64)

        self.assertEqual((code, report['code']), (2, 'integrity_manifest_untrusted'))
        self.assertFalse(self.destination.exists())


if __name__ == '__main__':
    unittest.main()
