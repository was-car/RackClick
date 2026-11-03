"""Native PowerShell 5.1 foci for pure MFA profile/env handling; no VM, services or keys."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'tools/windows/server-install/RackClick.MfaRuntime.ps1'
PS = shutil.which('powershell.exe')
LOAD = r'''
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. $env:RC_MFA_RUNTIME_HELPER
$id='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
$instances='C:\ProgramData\RackClick\Instances'
$parent=$instances+'\'+$id
$root=$parent+'\security'
function ValidManifest {
 return @{schemaVersion=2;installationPath=($parent+'\instance');mfa=@{enabled=$true;instancesRoot=$root;installationId=$id}}
}
function Reject([scriptblock]$Body) {
 try { &$Body | Out-Null; return $false }
 catch { return ($_.Exception.Data['serverCode'] -ceq 'server_mfa_profile_invalid' -and $_.Exception.Data['serverExit'] -eq 2 -and $_.Exception.Message -ceq 'server_mfa_profile_invalid') }
}
'''


@unittest.skipUnless(PS, 'Windows PowerShell 5.1 is required')
class MfaRuntimeProfileTests(unittest.TestCase):
    def focus(self, body):
        env = os.environ.copy()
        env['RC_MFA_RUNTIME_HELPER'] = str(HELPER)
        encoded = base64.b64encode((LOAD + body).encode('utf-16-le')).decode('ascii')
        completed = subprocess.run(
            [PS, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', encoded],
            env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return json.loads(completed.stdout)

    def test_parser_is_native_51_and_script_ascii(self):
        HELPER.read_text(encoding='ascii')
        data = self.focus(r'''
$tokens=$null;$errors=$null
$null=[Management.Automation.Language.Parser]::ParseFile($env:RC_MFA_RUNTIME_HELPER,[ref]$tokens,[ref]$errors)
@{version=$PSVersionTable.PSVersion.ToString();errors=$errors.Count}|ConvertTo-Json -Compress
''')
        self.assertTrue(data['version'].startswith('5.1.'))
        self.assertEqual(data['errors'], 0)

    def test_legacy_is_disabled_with_or_without_installation_id(self):
        data = self.focus(r'''
$a=Get-ServerMfaProfile ([pscustomobject]@{schemaVersion=1})
$b=Get-ServerMfaProfile @{schemaVersion=1} $id
@{disabled=(-not$a.enabled-and-not$b.enabled);rootNull=($null-eq$a.instancesRoot);idNull=($null-eq$a.installationId)}|ConvertTo-Json -Compress
''')
        self.assertTrue(all(data.values()), data)

    def test_valid_v2_and_json_object_return_exact_bound_config(self):
        data = self.focus(r'''
$value=ValidManifest
$result=Get-ServerMfaProfile ($value|ConvertTo-Json -Depth 4|ConvertFrom-Json) $id
@{enabled=$result.enabled;root=$result.instancesRoot;id=$result.installationId;fields=($result.Keys|Sort-Object)-join ','}|ConvertTo-Json -Compress
''')
        self.assertTrue(data['enabled'])
        self.assertEqual(data['root'], r'C:\ProgramData\RackClick\Instances\aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\security')
        self.assertEqual(data['id'], 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')
        self.assertEqual(data['fields'], 'enabled,installationId,instancesRoot')

    def test_case_equivalent_windows_paths_are_canonicalized(self):
        data = self.focus(r'''
$value=ValidManifest;$value.mfa.instancesRoot=$root.ToLowerInvariant();$value.installationPath=$value.installationPath.ToUpperInvariant()
$result=Get-ServerMfaProfile $value $id
@{enabled=$result.enabled;canonical=($result.instancesRoot-ceq$root)}|ConvertTo-Json -Compress
''')
        self.assertTrue(all(data.values()), data)

    def test_unknown_versions_missing_sections_and_legacy_injection_rejected(self):
        data = self.focus(r'''
$cases=@($null,@{},@{schemaVersion='2'},@{schemaVersion=$true},@{schemaVersion=0},@{schemaVersion=3},@{schemaVersion=2},@{SchemaVersion=2;mfa=@{}},@{schemaVersion=2;MFA=@{}},@{schemaVersion=1;mfa=$null},@{schemaVersion=1;MFA=@{enabled=$true}})
@($cases|ForEach-Object{$case=$_;Reject {Get-ServerMfaProfile $case $id}})|ConvertTo-Json -Compress
''')
        self.assertEqual(len(data), 11)
        self.assertTrue(all(data), data)

    def test_mfa_field_types_extras_and_wrong_casing_rejected(self):
        data = self.focus(r'''
$rows=@()
foreach($case in @('null','string','array','false','enabled_string','root_number','id_number','extra','missing','wrong_case')) {
 $value=ValidManifest
 switch($case) {
  null {$value.mfa=$null}
  string {$value.mfa='enabled'}
  array {$value.mfa=@(1,2)}
  false {$value.mfa.enabled=$false}
  enabled_string {$value.mfa.enabled='true'}
  root_number {$value.mfa.instancesRoot=42}
  id_number {$value.mfa.installationId=42}
  extra {$value.mfa.backupRoot='ignored'}
  missing {$value.mfa.Remove('instancesRoot')}
  wrong_case {$value.mfa=[pscustomobject]@{Enabled=$true;instancesRoot=$root;installationId=$id}}
 }
 $rows+=Reject {Get-ServerMfaProfile $value $id}
}
$rows|ConvertTo-Json -Compress
''')
        self.assertEqual(len(data), 10)
        self.assertTrue(all(data), data)

    def test_noncanonical_and_unanchored_roots_rejected(self):
        data = self.focus(r'''
$roots=@(($root+'\'),($root.Replace('\','/')),($root+'\..\security'),'\\server\share',('\\?\'+$root),'C:ProgramData\RackClick\Instances',($root.Replace('C:','D:')),($root+':stream'),($root+[char]0),($root+' '),($root+'-other'))
$rows=@();foreach($candidate in $roots){$value=ValidManifest;$value.mfa.instancesRoot=$candidate;$rows+=Reject{Get-ServerMfaProfile $value $id}}
$rows|ConvertTo-Json -Compress
''')
        self.assertEqual(len(data), 11)
        self.assertTrue(all(data), data)

    def test_three_different_installation_ids_and_unbound_paths_rejected(self):
        data = self.focus(r'''
$rows=@()
foreach($case in @('other_argument','other_mfa','empty_id','zero_id','uppercase_id','missing_path','other_path','path_traversal','trailing_slash','relative_path','null_path')) {
 $value=ValidManifest;$argument=$id
 switch($case) {
  other_argument {$argument='11111111-2222-3333-4444-555555555555'}
  other_mfa {$value.mfa.installationId='11111111-2222-3333-4444-555555555555'}
  empty_id {$argument=''}
  zero_id {$argument=[guid]::Empty.ToString('D');$value.mfa.installationId=$argument}
  uppercase_id {$argument=$id.ToUpperInvariant();$value.mfa.installationId=$argument}
  missing_path {$value.Remove('installationPath')}
  other_path {$value.installationPath=$instances+'\11111111-2222-3333-4444-555555555555\instance'}
  path_traversal {$value.installationPath=$parent+'\x\..\instance'}
  trailing_slash {$value.installationPath+='\'}
  relative_path {$value.installationPath='instance'}
  null_path {$value.installationPath=$null}
 }
 $rows+=Reject {Get-ServerMfaProfile $value $argument}
}
$rows|ConvertTo-Json -Compress
''')
        self.assertEqual(len(data), 11)
        self.assertTrue(all(data), data)

    def test_disabled_env_clears_aliases_and_unknown_mfa_settings(self):
        data = self.focus(r'''
$envTable=@{MfaKeyStore__Enabled='true';MfaKeyStore__InstancesRoot='inherited';MfaKeyStore__InstallationId='inherited';'MfaKeyStore:Enabled'='true';'MfaKeyStore:Unknown'='secret';'MfaKeyStore__Unknown'='inherited';MfaKeyStore='scalar';Keep='same'}
Set-ServerMfaEnvironment $envTable (Get-ServerMfaProfile @{schemaVersion=1})
@{enabled=$envTable.MfaKeyStore__Enabled;rootNull=($null-eq$envTable.MfaKeyStore__InstancesRoot);idNull=($null-eq$envTable.MfaKeyStore__InstallationId);unknownNull=($null-eq$envTable.MfaKeyStore__Unknown);scalarNull=($null-eq$envTable.MfaKeyStore);noColon=(@($envTable.Keys|Where-Object{$_-match'^MfaKeyStore:'}).Count-eq0);keep=$envTable.Keep}|ConvertTo-Json -Compress
''')
        self.assertEqual(data.pop('enabled'), 'false')
        self.assertEqual(data.pop('keep'), 'same')
        self.assertTrue(all(data.values()), data)

    def test_enabled_env_uses_only_validated_values(self):
        data = self.focus(r'''
$envTable=@{MfaKeyStore__Enabled='false';MfaKeyStore__InstallationId='other';'mfakeystore:InstancesRoot'='other';Keep='same'}
Set-ServerMfaEnvironment $envTable (Get-ServerMfaProfile (ValidManifest) $id)
@{enabled=$envTable.MfaKeyStore__Enabled;root=$envTable.MfaKeyStore__InstancesRoot;id=$envTable.MfaKeyStore__InstallationId;noColon=(@($envTable.Keys|Where-Object{$_-match'^MfaKeyStore:'}).Count-eq0);keep=$envTable.Keep}|ConvertTo-Json -Compress
''')
        self.assertEqual(data['enabled'], 'true')
        self.assertEqual(data['root'], r'C:\ProgramData\RackClick\Instances\aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\security')
        self.assertEqual(data['id'], 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')
        self.assertTrue(data['noColon'])
        self.assertEqual(data['keep'], 'same')

    def test_invalid_environment_profile_does_not_partially_mutate_table(self):
        data = self.focus(r'''
$rows=@()
foreach($case in @('missing','extra','bad_enabled','bad_root','bad_id','disabled_root','disabled_id')) {
 $profile=Get-ServerMfaProfile (ValidManifest) $id
 switch($case){missing{$profile.Remove('enabled')};extra{$profile.extra='x'};bad_enabled{$profile.enabled='true'};bad_root{$profile.instancesRoot='C:\elsewhere'};bad_id{$profile.installationId='x'};disabled_root{$profile.enabled=$false};disabled_id{$profile.enabled=$false;$profile.instancesRoot=$null}}
 $envTable=@{MfaKeyStore__Enabled='inherited';'MfaKeyStore:Enabled'='alias';Keep='same'}
 $before=$envTable|ConvertTo-Json -Compress
 $rejected=Reject{Set-ServerMfaEnvironment $envTable $profile}
 $rows+=($rejected-and($before-ceq($envTable|ConvertTo-Json -Compress)))
}
$rows|ConvertTo-Json -Compress
''')
        self.assertEqual(len(data), 7)
        self.assertTrue(all(data), data)

    def test_shared_and_other_installation_security_roots_rejected(self):
        data = self.focus(r'''
$roots=@($instances,($instances+'\11111111-2222-3333-4444-555555555555\security'),($parent+'\instance\security'),($parent+'\security\'+$id))
$rows=@();foreach($candidate in $roots){$value=ValidManifest;$value.mfa.instancesRoot=$candidate;$rows+=Reject{Get-ServerMfaProfile $value $id}}
$rows|ConvertTo-Json -Compress
''')
        self.assertEqual(len(data), 4)
        self.assertTrue(all(data), data)

    def test_lexical_redirect_or_reparse_spellings_never_resolved(self):
        data = self.focus(r'''
$roots=@(($parent+'\link\..\security'),('\\.\'+$root),($parent+'\SECURI~1'),($parent+'\security.'),($parent+'\junction\security'))
$rows=@();foreach($candidate in $roots){$value=ValidManifest;$value.mfa.instancesRoot=$candidate;$rows+=Reject{Get-ServerMfaProfile $value $id}}
$rows|ConvertTo-Json -Compress
''')
        self.assertEqual(len(data), 5)
        self.assertTrue(all(data), data)

    def test_functions_do_not_mutate_process_environment(self):
        data = self.focus(r'''
$before=[Environment]::GetEnvironmentVariables()
$table=@{MfaKeyStore__Enabled='inherited'}
Set-ServerMfaEnvironment $table (Get-ServerMfaProfile (ValidManifest) $id)
$after=[Environment]::GetEnvironmentVariables()
$same=$before.Count-eq$after.Count
foreach($key in $before.Keys){if($before[$key]-cne$after[$key]){$same=$false}}
@{sameProcessEnvironment=$same}|ConvertTo-Json -Compress
''')
        self.assertTrue(data['sameProcessEnvironment'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
