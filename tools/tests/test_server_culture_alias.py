"""Regresion: la verificacion del servidor debe funcionar con cultura alemana y con cuentas de servicio registradas como .\\usuario."""
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER_INSTALL = ROOT / 'tools' / 'windows' / 'server-install'
LIFECYCLE = SERVER_INSTALL / 'RackClick.Setup.Lifecycle.ps1'
POWERSHELL = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'

# Fecha/hora dependiente de la cultura: solo se acepta si pasa InvariantCulture en la misma linea.
CULTURE_SENSITIVE = re.compile(r'\[(?:DateTime|DateTimeOffset)\]::(?:Parse|TryParse)\((?![^)]*InvariantCulture)')


def run_ps(script: str) -> str:
    command = [str(POWERSHELL), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout.strip()


@unittest.skipUnless(sys.platform == 'win32' and POWERSHELL.exists(), 'requiere Windows PowerShell 5.1')
class ServerCultureAndAliasTests(unittest.TestCase):
    def test_no_culture_sensitive_date_parsing_in_server_install_scripts(self):
        offenders = []
        for path in sorted(SERVER_INSTALL.glob('*.ps1')):
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if CULTURE_SENSITIVE.search(line):
                    offenders.append(f'{path.name}:{number}')
        self.assertEqual([], offenders)

    def test_verifier_reads_profile_only_through_native_reader(self):
        # Una comprobacion por ruta (Get-Item) sobre la carpeta instance falla al administrador; la lectura nativa ya rechaza reparse points.
        text = (SERVER_INSTALL / 'Test-RackClickServerAfterReboot.ps1').read_text(encoding='utf-8')
        self.assertNotIn('Assert-SetupNoReparse $postbootManifest', text)
        self.assertIn('Read-SetupPreparedFile -InstancePath $postbootReceipt.instancePath', text)

    def test_powershell_files_parse_without_errors(self):
        changed = ['RackClick.Setup.Lifecycle.ps1', 'Test-RackClickServerAfterReboot.ps1', 'Set-RackClickInstanceNetwork.ps1', 'Set-RackClickServerNetwork.ps1']
        for name in changed:
            script = (f"$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('{SERVER_INSTALL / name}',[ref]$t,[ref]$e);"
                      "if($e.Count){$e|ForEach-Object{$_.Message};exit 1}else{'ok'}")
            self.assertEqual('ok', run_ps(script), name)

    def test_restart_is_observed_when_server_culture_is_german(self):
        script = f"""
[Threading.Thread]::CurrentThread.CurrentCulture=[Globalization.CultureInfo]::GetCultureInfo('de-DE')
[Threading.Thread]::CurrentThread.CurrentUICulture=[Globalization.CultureInfo]::GetCultureInfo('de-DE')
. '{LIFECYCLE}'
$snap=@{{bootCurrent=(Get-Date).AddHours(-1).ToUniversalTime().ToString('o');bootAtInstall='10/22/2026 20:26:01';serviceState='Running';serviceStartMode='Auto';serviceSid='S-1-5-21-1-2-3-1002';expectedSid='S-1-5-21-1-2-3-1002';healthStatus='ready';schemaVersion=14;backupTaskState='Ready';backupTaskSid='S-1-5-21-1-2-3-1002';backupLastResult=0;backupScheduleVerified=$true}}
$r=Test-SetupPostbootSnapshot $snap
[pscustomobject]@{{valid=$r.valid;code=$r.code}} | ConvertTo-Json -Compress
"""
        result = json.loads(run_ps(script))
        self.assertTrue(result['valid'], result)
        self.assertEqual('postboot_verified', result['code'])

    def test_local_alias_resolves_to_same_sid_as_computer_qualified_name(self):
        script = f"""
. '{LIFECYCLE}'
$a=Resolve-SetupAccountSid ('.\\'+$env:USERNAME)
$b=Resolve-SetupAccountSid ($env:COMPUTERNAME+'\\'+$env:USERNAME)
[pscustomobject]@{{alias=$a;qualified=$b}} | ConvertTo-Json -Compress
"""
        result = json.loads(run_ps(script))
        self.assertEqual(result['qualified'], result['alias'])
        self.assertTrue(result['alias'].startswith('S-1-5-'))


if __name__ == '__main__':
    unittest.main()
