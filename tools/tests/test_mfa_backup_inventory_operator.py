"""Native PS5.1 checks for F0602 metadata operators; no VM or installed service."""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / 'tools/windows/RackClick.MfaBackupInventory.ps1'


class MfaBackupInventoryOperatorTests(unittest.TestCase):
    def probe(self, body):
        script = "$ErrorActionPreference='Stop'; $PostgresBinPath=''; . '" + str(LIB).replace("'", "''") + "'; " + body
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                 '-Command', script], capture_output=True, text=True, encoding='utf-8', timeout=35)
        self.assertEqual(0, result.returncode, result.stderr[-1600:])
        return result.stdout.strip()

    def fixture(self, root):
        folder = root / 'tool'; folder.mkdir()
        (folder / 'RackClick.Server.dll').write_bytes(b'synthetic-assembly')
        (folder / 'dependency.dll').write_bytes(b'synthetic-dependency')
        sums = ''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n'
                       for p in sorted(folder.iterdir()))
        (folder / 'SHA256SUMS').write_text(sums, encoding='ascii')
        return folder, hashlib.sha256((folder / 'SHA256SUMS').read_bytes()).hexdigest()

    def test_valid_tool_retains_files_until_disposed(self):
        with tempfile.TemporaryDirectory(prefix='rc-inventory-') as tmp:
            folder, digest = self.fixture(Path(tmp))
            self.assertIn('LOCKED', self.probe(f"$tool=Open-MfaBackupTool '{folder}' '{digest}'; try {{ try {{ [IO.File]::WriteAllText('{folder}/dependency.dll','attack'); throw 'write_was_allowed' }} catch [IO.IOException] {{ 'LOCKED' }} }} finally {{ Close-MfaBackupTool $tool }}"))

    def test_wrong_external_pin_rejects(self):
        with tempfile.TemporaryDirectory(prefix='rc-inventory-') as tmp:
            folder, _ = self.fixture(Path(tmp))
            self.assertEqual('mfa_backup_tool_pin_invalid', self.probe(f"try {{ Open-MfaBackupTool '{folder}' '{'0'*64}'; throw 'accepted' }} catch {{ $_.Exception.Message }}"))

    def test_changed_dependency_rejects(self):
        with tempfile.TemporaryDirectory(prefix='rc-inventory-') as tmp:
            folder, digest = self.fixture(Path(tmp))
            (folder/'dependency.dll').write_bytes(b'changed')
            self.assertEqual('mfa_backup_tool_content_invalid', self.probe(f"try {{ Open-MfaBackupTool '{folder}' '{digest}'; throw 'accepted' }} catch {{ $_.Exception.Message }}"))

    def test_extra_file_rejects(self):
        with tempfile.TemporaryDirectory(prefix='rc-inventory-') as tmp:
            folder, digest = self.fixture(Path(tmp))
            (folder/'extra.dll').write_bytes(b'extra')
            self.assertEqual('mfa_backup_tool_content_invalid', self.probe(f"try {{ Open-MfaBackupTool '{folder}' '{digest}'; throw 'accepted' }} catch {{ $_.Exception.Message }}"))

    def test_environment_isolates_only_child(self):
        result = self.probe("$env:DOTNET_STARTUP_HOOKS='synthetic'; $env:PGHOST='synthetic'; $s=New-Object Diagnostics.ProcessStartInfo; Set-MfaBackupChildEnvironment $s; if ($s.EnvironmentVariables.ContainsKey('DOTNET_STARTUP_HOOKS') -or $s.EnvironmentVariables.ContainsKey('PGHOST') -or $s.EnvironmentVariables['DOTNET_EnableDiagnostics'] -ne '0' -or $env:DOTNET_STARTUP_HOOKS -ne 'synthetic') {throw 'environment_invalid'}; 'ISOLATED'")
        self.assertEqual('ISOLATED', result)

    def test_protocol_process_start_works_on_net_framework(self):
        # whoami rejects the helper arguments without side effects; this exercises process/pipe construction on PS5.1.
        self.assertEqual('PROCESS_STARTED',self.probe("$tool=[pscustomobject]@{Directory=$env:TEMP};$p=$null;try{$p=Start-MfaBackupProtocol (Join-Path $env:SystemRoot 'System32\\whoami.exe') $tool;'PROCESS_STARTED'}finally{Close-MfaBackupProtocol $p}"))

    def test_empty_junction_is_rejected_before_recursive_enumeration(self):
        with tempfile.TemporaryDirectory(prefix='rc-inventory-') as tmp:
            root=Path(tmp);folder,digest=self.fixture(root)
            target=root/'empty';target.mkdir()
            subprocess.run(['cmd.exe','/c','mklink','/J',str(folder/'redirect'),str(target)],capture_output=True,check=True)
            self.assertEqual('mfa_backup_tool_content_invalid', self.probe(f"try {{ $tool=Open-MfaBackupTool '{folder}' '{digest}'; Close-MfaBackupTool $tool; 'accepted' }} catch {{ $_.Exception.Message }}"))

    def test_receipt_requires_its_external_pin(self):
        with tempfile.TemporaryDirectory(prefix='rc-inventory-') as tmp:
            path = Path(tmp)/'receipt.json'
            path.write_text('{}', 'ascii')
            self.assertEqual('mfa_backup_receipt_pin_invalid', self.probe(f"try {{ Read-MfaBackupReceipt '{path}' '{'0'*64}'; throw 'accepted' }} catch {{ $_.Exception.Message }}"))

    def test_receipt_exact_fields_and_canonical_ids(self):
        receipt = dict(format='RackClick.MfaBackupInventoryReceipt', formatVersion=1,
                       installationId='4dc3ead6-20d1-4830-bc5d-4f5bb7ad05cf', backupId='009c8fe5-0967-4d42-a164-32891494d4d1',
                       **{name:'1'*64 for name in ['inventorySha256','manifestSha256','dumpSha256','envelopeSha256']})
        with tempfile.TemporaryDirectory(prefix='rc-inventory-') as tmp:
            path = Path(tmp)/'receipt.json'
            for alteration in [dict(receipt, extra=True), dict(receipt, installationId='not-a-guid'), dict(receipt, formatVersion=2)]:
                path.write_text(json.dumps(alteration), 'ascii'); digest=hashlib.sha256(path.read_bytes()).hexdigest()
                self.assertEqual('mfa_backup_receipt_invalid', self.probe(f"try {{ Read-MfaBackupReceipt '{path}' '{digest}'; throw 'accepted' }} catch {{ $_.Exception.Message }}"))

    def test_scripts_parse_in_windows_powershell(self):
        self.probe("foreach($name in @('RackClick.MfaBackupInventory.ps1','New-RackClickMfaDatabaseBackup.ps1','Test-RackClickMfaDatabaseBackup.ps1')) {$tokens=$null;$errors=$null; [void][Management.Automation.Language.Parser]::ParseFile((Join-Path '" + str(ROOT/'tools/windows') + "' $name),[ref]$tokens,[ref]$errors); if($errors.Count){throw 'parse_failed'}}; 'PARSED'")


if __name__ == '__main__':
    unittest.main()
