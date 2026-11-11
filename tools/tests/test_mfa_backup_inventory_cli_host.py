"""Process checks use an explicitly selected isolated build, not an installed host."""
from pathlib import Path
import json
import os
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[2]

class MfaBackupInventoryCliHostTests(unittest.TestCase):
    def invoke(self,args,stdin='{}\n'):
        dll=Path(os.environ['RACKCLICK_F0602_NATIVE_DLL'])
        self.assertTrue(dll.resolve().is_relative_to((ROOT/'.local').resolve()))
        env=os.environ.copy()
        for key in list(env):
            if key.startswith(('ConnectionStrings__','SqlSecret__','MfaKeyStore__','DOTNET_STARTUP_','CORECLR_')):env.pop(key)
        # Explicit invalid host-only settings: local protocol must return before composing the host.
        env.update(PublicOrigin='not-an-origin',SqlSecret__Enabled='invalid',MfaKeyStore__Enabled='invalid')
        return subprocess.run([str(ROOT/'.local/dotnet-10.0.401/dotnet.exe'),str(dll),*args],input=stdin,
                              capture_output=True,text=True,env=env,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)

    def test_rejects_invalid_input_before_host_configuration(self):
        p=self.invoke(['--mfa-backup-inventory'])
        self.assertEqual(1,p.returncode)
        self.assertEqual('rejected',json.loads(p.stdout)['status'])
        self.assertNotIn('Exception',p.stderr)

    def test_mode_conflicts_with_every_existing_cli(self):
        for mode in ['--bootstrap','--migrate','--recover-admin','--mfa-keys-init','--mfa-require-all','--mfa-key-maintenance']:
            with self.subTest(mode=mode):
                p=self.invoke(['--mfa-backup-inventory',mode])
                self.assertEqual(1,p.returncode)
                self.assertEqual('cli_mode_conflict',json.loads(p.stdout)['error'])

    def test_unknown_cli_argument_cannot_be_host_configuration(self):
        p=self.invoke(['--mfa-backup-inventory','--urls','http://127.0.0.1:49999'])
        self.assertEqual(1,p.returncode)
        self.assertEqual('mfa_backup_arguments_invalid',json.loads(p.stdout)['code'])

if __name__=='__main__':unittest.main()
