"""NEW48 distribution and minimum SQL contracts; no VM or credential access."""
import base64
import json
import subprocess
import sys
import shutil
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
import build_server_distribution as distribution


class Installer48Tests(unittest.TestCase):
    def ps(self, text):
        body = "$ErrorActionPreference='Stop';[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);" + text
        r = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-EncodedCommand',base64.b64encode(body.encode('utf-16le')).decode()],capture_output=True,encoding='utf-8-sig',timeout=45)
        self.assertEqual(r.returncode,0,r.stderr)
        return json.loads(r.stdout)

    def test_new_profile_is_closed_and_complete(self):
        p = distribution.load_profile(ROOT/'docs/DISTRIBUCION48-PERFIL.json')
        self.assertEqual((p['applicationSchema'],p['profileId'],p['serverFileCount'],p['frontendFileCount']),(48,'schema48-maintenance-01',58,18))
        self.assertEqual(len(p['serverSqlFiles']),48)
        self.assertEqual(p['serverSqlFiles'][-1],'database/048-mfa-loss-startup.sql')

    def test_runtime48_witnesses_are_read_only_and_private_excluded(self):
        path=str(ROOT/'tools/windows/RackClick.Instance.ps1').replace("'","''")
        value=self.ps(". '"+path+"'; $s=Get-InstanceRuntimeGrantsSql ('rc_runtime_'+('a'*32)) 48; @{sql=$s;check=(Get-InstanceMissingTableRightsSql ('rc_runtime_'+('a'*32)) ('rc_owner_'+('b'*32)) 48)}|ConvertTo-Json -Compress")
        for relation in ['public.app_mfa_rotation_witness','public.app_mfa_loss_startup_witness']:
            self.assertIn(relation,value['sql'])
        self.assertIn('rackclick_private',value['sql'])
        self.assertIn("'v'",value['check'])

    def test_backup_has_only_select_on_private_relations(self):
        path=str(ROOT/'tools/windows/RackClick.Instance.ps1').replace("'","''")
        value=self.ps(". '"+path+"'; @{sql=(Get-InstanceBackupGrantsSql ('rc_backup_'+('a'*32)) 48)}|ConvertTo-Json -Compress")
        self.assertIn('GRANT USAGE ON SCHEMA rackclick_private',value['sql'])
        self.assertIn('rackclick_private.mfa_loss_factor_archive',value['sql'])
        self.assertNotIn('GRANT INSERT',value['sql'])

    def test_restore48_stops_in_parent_before_system_changes(self):
        text=(ROOT/'tools/windows/server-install/Install-RackClickServer.ps1').read_text(encoding='utf-8-sig')
        gate="throw 'schema48_restore_not_available'"
        self.assertLess(text.index('Read-RackClickOfflineBundle -ArchivePath'),text.index(gate))
        for mutation in ['Install-SetupCrt','New-LocalUser','New-Service']:
            self.assertLess(text.index(gate),text.index(mutation))

    def test_preflight_preserves_caller_strict_mode(self):
        text=(ROOT/'tools/windows/server-install/Install-RackClickServer.ps1').read_text(encoding='utf-8-sig')
        start=text.index('    $setupPayload=Assert-SetupPayload $setupPayloadRoot')
        start=text.index('\n',start)+1
        snippet=text[start:text.index("    Set-SetupProgress 'host'",start)]
        with tempfile.TemporaryDirectory(prefix='preflight48-',dir=ROOT/'.local') as tmp:
            root=Path(tmp);shutil.copytree(ROOT/'tools/windows',root/'operators')
            # Read only the approved bundle; never execute the installer.
            shutil.copyfile(ROOT/'.local/install17-20261111/RackClick-Bundle-48-17.zip',root/'RackClick.zip')
            body="Set-StrictMode -Off;$setupPayloadRoot='"+str(root).replace("'","''")+"';$setupPayload=@{bundleArchiveSha256='098392ebfc62f2fe5ec9f79909ea3bdbecbf3c565286747a5a9d9507fccd8d40'};$setupPlan=@{mode='New'}; . ([scriptblock]::Create([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+base64.b64encode(snippet.encode()).decode()+"'))));$answer=[pscustomobject]@{code='backup_complete'};try{$null=$answer.errorType;@{preserved=$true}|ConvertTo-Json -Compress}catch{@{preserved=$false}|ConvertTo-Json -Compress}"
            self.assertEqual(self.ps(body),dict(preserved=True))


if __name__=='__main__': unittest.main()
