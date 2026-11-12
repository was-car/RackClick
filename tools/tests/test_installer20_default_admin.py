"""Use the real UI defaults and New-plan expression without opening a form or installing."""
import base64
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PS = shutil.which('powershell.exe')


@unittest.skipUnless(PS, 'Windows PowerShell 5.1 required')
class Installer20DefaultAdminTests(unittest.TestCase):
    def test_new_plan_uses_generic_editable_administrator(self):
        source = (ROOT / 'tools/windows/server-install/Show-RackClickInstaller.ps1').read_text('utf-8-sig')
        fields = source[source.index('$fields=[ordered]@{'):source.index('$inputs=@{};')]
        expression = re.search(r'(?m)^  (\$plan=\[ordered\]@\{schemaVersion=1;[^\r\n]+)', source).group(1)
        helper = str(ROOT / 'tools/windows/server-install/RackClick.Setup.ps1').replace("'", "''")
        for editable in (None, 'MyInventoryAdmin'):
            with self.subTest(editable=editable), tempfile.TemporaryDirectory() as d:
                target = str(Path(d) / 'new-plan.json').replace("'", "''")
                body = "$ErrorActionPreference='Stop';. '" + helper + "';"
                body += "$defaultIp='192.168.250.76';$defaultSubnet='192.168.250.0/24';" + fields
                body += "$inputs=@{};foreach($entry in $fields.GetEnumerator()){$inputs[$entry.Key]=[pscustomobject]@{Text=$entry.Value[1]}};"
                if editable:
                    body += "$inputs.bootstrapUser.Text='" + editable + "';"
                body += "$ip=[Net.IPAddress]::Parse($defaultIp);$hostName=$defaultIp;$https=5443;$pg=55441;$subnet=$defaultSubnet;$mode=[pscustomobject]@{SelectedItem='New'};"
                body += expression + ";Write-SetupJson '" + target + "' $plan;$read=Read-SetupPlan '" + target + "';"
                body += "[ordered]@{bootstrapUser=$read.bootstrapUser;mode=$read.mode;systemhaus=$read.systemhaus;accountName=$read.accountName}|ConvertTo-Json -Compress"
                encoded = base64.b64encode(body.encode('utf-16le')).decode()
                result = subprocess.run([PS, '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                plan = json.loads(result.stdout)
                self.assertEqual(plan, dict(bootstrapUser=editable or 'RackClickAdmin', mode='New',
                                            systemhaus='Systemhaus', accountName='RackClickSvc'))


if __name__ == '__main__': unittest.main()
