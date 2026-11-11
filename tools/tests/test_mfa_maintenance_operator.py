"""Focused PS5.1/operator and local-CLI rejection checks. No installed service/DB use."""
from pathlib import Path
import json
import os
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[2]
WRAPPER=ROOT/'tools/windows/Invoke-RackClickMfaKeyMaintenance.ps1'

class MfaMaintenanceOperatorTests(unittest.TestCase):
    def ps(self,script):
        return subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-Command',script],
            capture_output=True,text=True,encoding='utf-8',timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)

    def test_wrapper_is_ascii_and_parses_in_windows_powershell(self):
        WRAPPER.read_bytes().decode('ascii')
        result=self.ps("$e=$null;$t=$null;[void][Management.Automation.Language.Parser]::ParseFile('"+str(WRAPPER)+"',[ref]$t,[ref]$e);if($e.Count){exit 1};'parsed'")
        self.assertEqual(0,result.returncode,result.stderr);self.assertIn('parsed',result.stdout)

    def test_unelevated_wrapper_rejects_before_prompt_or_service_query(self):
        elevated=self.ps("([Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)")
        if elevated.stdout.strip()=='True':self.skipTest('negative requires unelevated caller')
        result=self.ps("function Get-CimInstance {throw 'service_was_queried'};function Read-Host {throw 'secret_was_requested'};& '"+str(WRAPPER)+"' -Action retire -ServiceName 'synthetic-must-not-be-queried';exit $LASTEXITCODE")
        self.assertEqual(1,result.returncode)
        self.assertEqual('mfa_maintenance_not_elevated',json.loads(result.stdout)['code'])
        self.assertNotIn('queried',result.stdout);self.assertNotIn('requested',result.stdout)

    def test_helper_rejects_unknown_mode_before_starting_any_process(self):
        result=self.ps("$PostgresBinPath='';. '"+str(ROOT/'tools/windows/RackClick.MfaBackupInventory.ps1')+"';try{Start-MfaBackupProtocol -DotnetPath 'invalid' -Tool $null -CliMode '--unknown';exit 2}catch [Management.Automation.ParameterBindingException]{'rejected_before_start'}")
        self.assertEqual(0,result.returncode,result.stderr);self.assertIn('rejected_before_start',result.stdout)

    def invoke(self,args):
        dll=Path(os.environ['RACKCLICK_F0602_NATIVE_DLL']).resolve()
        self.assertTrue(dll.is_relative_to((ROOT/'.local').resolve()))
        env=os.environ.copy();env.update(PublicOrigin='invalid-host-only-origin',SqlSecret__Enabled='invalid')
        return subprocess.run([str(ROOT/'.local/dotnet-10.0.401/dotnet.exe'),str(dll),*args],input='{}',capture_output=True,text=True,env=env,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)

    def test_new_mode_is_exclusive_with_all_existing_cli_modes(self):
        for mode in ['--bootstrap','--migrate','--recover-admin','--mfa-keys-init','--mfa-require-all','--mfa-backup-inventory']:
            with self.subTest(mode=mode):
                result=self.invoke(['--mfa-key-maintenance',mode]);self.assertEqual(1,result.returncode)
                self.assertEqual('cli_mode_conflict',json.loads(result.stdout)['error'])

    def test_new_mode_rejects_extra_args_without_constructing_host(self):
        result=self.invoke(['--mfa-key-maintenance','--urls','http://127.0.0.1:49998'])
        self.assertEqual(1,result.returncode);self.assertEqual('mfa_maintenance_arguments_invalid',json.loads(result.stdout)['code'])
        self.assertEqual('',result.stderr)

if __name__=='__main__':unittest.main()
