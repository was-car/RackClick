"""Execute the real launchers' environment-construction blocks with synthetic inputs.

No RackClick/PG/service process is started; no profile, certificate or key is opened.
"""
import base64
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
PS = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'


class MfaRuntimeWiringTests(unittest.TestCase):
    def focus(self, body):
        setup = r'''
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=__ROOT__
. (Join-Path $repo 'tools/windows/server-install/RackClick.MfaRuntime.ps1')
. (Join-Path $repo 'tools/windows/RackClick.SqlSecrets.ps1')
$script:launcherText=[IO.File]::ReadAllText((Join-Path $repo 'tools/windows/RackClick.LaunchControl.ps1'))
$tok=$null;$err=$null
$tree=[Management.Automation.Language.Parser]::ParseInput($script:launcherText,[ref]$tok,[ref]$err)
foreach($name in @('Clear-LauncherInheritedConfiguration','Restore-LauncherInheritedConfiguration')) {
 $fun=$tree.FindAll({param($node) $node-is[Management.Automation.Language.FunctionDefinitionAst]-and$node.Name-eq$name},$true)
 if(@($fun).Count-ne1){throw 'function_missing'}
 . ([scriptblock]::Create($fun.Extent.Text))
}
$tls=$null;$control=$null;$effectiveOrigin='https://192.0.2.10:5445'
$instance=@{stageRoot='C:\synthetic\stage';runtimeConnectionString='synthetic-not-a-connection'}
$profile=@{root='C:\synthetic';origin=@{bind='192.0.2.10';port=5445};mfa=@{enabled=$false;instancesRoot=$null;installationId=$null}}
function BuildEnvironment([string]$relative) {
 $text=[IO.File]::ReadAllText((Join-Path $repo $relative))
 $first=$text.IndexOf('    $appEnvironment=@{}')
 $last=$text.IndexOf('    $app=Start-RackClickOwnedProcess',$first)
 if($first-lt0-or$last-le$first){throw 'block_missing'}
 . ([scriptblock]::Create($text.Substring($first,$last-$first)))
 return $appEnvironment
}
'''.replace('__ROOT__', "'" + str(ROOT).replace("'", "''") + "'")
        encoded = base64.b64encode((setup + body).encode('utf-16le')).decode()
        run = subprocess.run([str(PS), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                              '-EncodedCommand', encoded], capture_output=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr.decode(errors='replace'))
        return json.loads(run.stdout.decode('utf-8-sig'))

    def test_legacy_runtime_does_not_inherit_mfa_or_colon_alias(self):
        result = self.focus(r'''
[Environment]::SetEnvironmentVariable('MfaKeyStore:Enabled','true','Process')
$env:MfaKeyStore__Enabled='true';$env:MfaKeyStore__Unknown='poison'
$saved=Clear-LauncherInheritedConfiguration
try {
 $answer=BuildEnvironment 'tools/windows/server-install/Invoke-RackClickServerRuntime.ps1'
 @{enabled=$answer.MfaKeyStore__Enabled;unknownCleared=($null-eq$answer.MfaKeyStore__Unknown);colonGone=($null-eq[Environment]::GetEnvironmentVariable('MfaKeyStore:Enabled','Process'));noColonKeys=(@($answer.Keys|Where-Object{$_-like'*:*'}).Count-eq0)}|ConvertTo-Json -Compress
} finally {Restore-LauncherInheritedConfiguration $saved}
''')
        self.assertEqual(result['enabled'], 'false')
        self.assertTrue(result['unknownCleared'] and result['colonGone'] and result['noColonKeys'])

    def test_legacy_lab_launcher_also_cannot_inherit_activation(self):
        result = self.focus(r'''
[Environment]::SetEnvironmentVariable('MfaKeyStore:Enabled','true','Process')
$env:MfaKeyStore__Enabled='true';$env:MfaKeyStore__InstallationId='poison'
$saved=Clear-LauncherInheritedConfiguration
try {
 $answer=BuildEnvironment 'tools/windows/Start-RackClickLabInstance.ps1'
 @{enabled=$answer.MfaKeyStore__Enabled;idCleared=($null-eq$answer.MfaKeyStore__InstallationId);colonGone=($null-eq[Environment]::GetEnvironmentVariable('MfaKeyStore:Enabled','Process'))}|ConvertTo-Json -Compress
} finally {Restore-LauncherInheritedConfiguration $saved}
''')
        self.assertEqual(result['enabled'], 'false')
        self.assertTrue(result['idCleared'] and result['colonGone'])

    def test_profile_alone_supplies_enabled_root_and_outer_uuid(self):
        result = self.focus(r'''
$id='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
$profile.mfa=@{enabled=$true;instancesRoot=('C:\ProgramData\RackClick\Instances\'+$id+'\security');installationId=$id}
$env:MfaKeyStore__InstallationId='poison';$env:MfaKeyStore__InstancesRoot='poison'
$answer=BuildEnvironment 'tools/windows/server-install/Invoke-RackClickServerRuntime.ps1'
@{enabled=$answer.MfaKeyStore__Enabled;root=$answer.MfaKeyStore__InstancesRoot;id=$answer.MfaKeyStore__InstallationId}|ConvertTo-Json -Compress
''')
        self.assertEqual(result, dict(enabled='true', root=r'C:\ProgramData\RackClick\Instances\aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\security', id='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

    def test_changed_scripts_parse_in_windows_powershell_51(self):
        result = self.focus(r'''
$count=0
foreach($name in @('server-install/RackClick.ServerRuntime.ps1','server-install/New-RackClickServerProfile.ps1','server-install/Invoke-RackClickServerRuntime.ps1','Start-RackClickLabInstance.ps1','RackClick.LaunchControl.ps1')) {
 $tok=$null;$err=$null
 $null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $repo ('tools/windows/'+$name)),[ref]$tok,[ref]$err)
 if($err.Count-ne0){throw 'parser_failed'};$count++
}
@{parsed=$count;version=$PSVersionTable.PSVersion.Major}|ConvertTo-Json -Compress
''')
        self.assertEqual(result, dict(parsed=5, version=5))


if __name__ == '__main__':
    unittest.main()
