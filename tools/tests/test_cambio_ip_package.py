"""Regresion del cambio de IP de una instalacion RackClick 05: hashes fijados, analisis y alineacion del codigo instalado."""
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NETWORK = ROOT / 'tools' / 'windows' / 'network-change'
SERVER_INSTALL = ROOT / 'tools' / 'windows' / 'server-install'
ORCHESTRATOR = NETWORK / 'Cambiar-IP-RackClick.ps1'
POWERSHELL = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'
PAYLOAD_SHA256 = '25a764a9fa40f0e8feb39cfbc9b2b3f1f21bb1137738edd53614b257f6277ec7'


def run_ps(script: str) -> str:
    command = [str(POWERSHELL), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script]
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout.strip()


class PinsTests(unittest.TestCase):
    def test_engine_and_orchestrator_pin_the_same_frozen_payload(self):
        engine = (SERVER_INSTALL / 'Set-RackClickInstanceNetwork.ps1').read_text(encoding='utf-8')
        self.assertEqual(1, engine.count(f"'{PAYLOAD_SHA256}'"))
        self.assertIn(f"$PayloadSha256 = '{PAYLOAD_SHA256}'", ORCHESTRATOR.read_text(encoding='ascii'))

    def test_orchestrator_and_cmd_are_ascii_and_keep_engine_token(self):
        text = ORCHESTRATOR.read_text(encoding='ascii')
        self.assertEqual(1, text.count('@@ENGINE_SHA256@@'))
        cmd = (NETWORK / 'CAMBIAR-IP-RACKCLICK.cmd').read_bytes()
        self.assertTrue(all(byte < 128 for byte in cmd))
        self.assertIn(b'Cambiar-IP-RackClick.ps1', cmd)

    def test_network_tools_are_not_listed_in_frozen_payload_builder(self):
        builder = (ROOT / 'tools' / 'package_server_installer.py').read_text(encoding='utf-8')
        self.assertIn("'Set-RackClickInstanceNetwork.ps1'", builder)
        self.assertIn("if path.name in NETWORK_TOOLS:", builder)


@unittest.skipUnless(sys.platform == 'win32' and POWERSHELL.exists(), 'requiere Windows PowerShell 5.1')
class CodeAlignmentTests(unittest.TestCase):
    def test_orchestrator_parses(self):
        script = (f"$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('{ORCHESTRATOR}',[ref]$t,[ref]$e);"
                  "if($e.Count){$e|ForEach-Object{$_.Message};exit 1}else{'ok'}")
        self.assertEqual('ok', run_ps(script))

    def test_only_mismatched_operator_is_copied_and_service_binary_stops_the_change(self):
        script = f"""
$base = Join-Path ([IO.Path]::GetTempPath()) ('rc-cambio-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $base | Out-Null
Copy-Item -LiteralPath '{ORCHESTRATOR}' -Destination $base
Copy-Item -LiteralPath '{SERVER_INSTALL / 'Start-RackClickHere.ps1'}' -Destination $base
. (Join-Path $base 'Cambiar-IP-RackClick.ps1')
$root = Join-Path $base 'code'; $src = Join-Path $base 'payload'
New-Item -ItemType Directory -Path (Join-Path $root 'operators') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $root 'service') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $src 'operators') -Force | Out-Null
function TestHash([string]$p) {{ (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() }}
Set-Content -LiteralPath (Join-Path $root 'operators\\same.ps1') -Value 'same' -Encoding ASCII
Copy-Item -LiteralPath (Join-Path $root 'operators\\same.ps1') -Destination (Join-Path $src 'operators\\same.ps1')
Set-Content -LiteralPath (Join-Path $root 'operators\\old.ps1') -Value 'old' -Encoding ASCII
Set-Content -LiteralPath (Join-Path $src 'operators\\old.ps1') -Value 'new' -Encoding ASCII
Set-Content -LiteralPath (Join-Path $src 'operators\\added.ps1') -Value 'added' -Encoding ASCII
Set-Content -LiteralPath (Join-Path $root 'service\\RackClick.WindowsService.dll') -Value 'dll' -Encoding ASCII
$manifest = [pscustomobject]@{{ files = @(
  [pscustomobject]@{{ path='operators/same.ps1'; sha256=(TestHash (Join-Path $root 'operators\\same.ps1')) }},
  [pscustomobject]@{{ path='operators/old.ps1'; sha256=(TestHash (Join-Path $src 'operators\\old.ps1')) }},
  [pscustomobject]@{{ path='operators/added.ps1'; sha256=(TestHash (Join-Path $src 'operators\\added.ps1')) }}
) }}
$changes = @(Get-RcCodeChanges $manifest $root $src)
"count=" + $changes.Count + " first=" + $changes[0].path + " action=" + $changes[0].action + " second=" + $changes[1].path + " action=" + $changes[1].action
Set-Content -LiteralPath (Join-Path $root 'service\\RackClick.WindowsService.dll') -Value 'changed' -Encoding ASCII
$manifest2 = [pscustomobject]@{{ files = @([pscustomobject]@{{ path='service/RackClick.WindowsService.dll'; sha256=(TestHash (Join-Path $src 'operators\\old.ps1')) }}) }}
try {{ Get-RcCodeChanges $manifest2 $root $src | Out-Null; 'no-error' }} catch {{ $_.Exception.Message }}
Remove-Item -LiteralPath $base -Recurse -Force
"""
        output = run_ps(script).splitlines()
        self.assertEqual('count=2 first=operators/old.ps1 action=replace second=operators/added.ps1 action=add', output[0])
        self.assertEqual('cambio_service_binary_changed', output[1])


if __name__ == '__main__':
    unittest.main()
