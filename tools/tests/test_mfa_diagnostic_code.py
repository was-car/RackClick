"""Diagnostic public-code contract; own TEMP fixtures only, no elevation/SCM/key.

Native creation and positive ACLs are fixture doubles. ACL validation itself is
tested using real .NET descriptors supplied by a Get-Acl double; no claim about
creating Administrators-owned files or using an actual service identity.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'tools/windows/mfa-service-read-system/RackClick.MfaDiagnosticCode.ps1'
PS = shutil.which('powershell.exe')
SID = 'S-1-5-21-111-222-333-1001'

PRELUDE = r'''
$ErrorActionPreference='Stop'
. $env:RC_CODE_SOURCE
$env:ProgramData=$env:RC_CODE_FIXTURE
$reader='S-1-5-21-111-222-333-1001'
$root=Join-Path $env:ProgramData ('RackClick-MFA-Code-'+('a'*32))
function Must-Fail([scriptblock]$Action,[string]$Code) {
    try { & $Action } catch { if ($_.Exception.Message -ceq ('mfa_diagnostic:code_'+$Code)) { return };throw }
    throw ('expected_failure_'+$Code)
}
'''

FIXTURE = r'''
$old=Join-Path $env:ProgramData 'old';$new=Join-Path $env:ProgramData 'new'
[void][IO.Directory]::CreateDirectory($old);[void][IO.Directory]::CreateDirectory($new)
$lines=@()
foreach($i in 1..339) {
    $rel='runtime/shared/fixture/'+$i.ToString('D3')+'.dll'
    $file=Join-Path $old $rel;[void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($file))
    [IO.File]::WriteAllText($file,('fixture-'+$i))
    $lines+=((Get-MfaCodeHash $file)+'  '+$rel)
}
foreach($rel in @(Get-MfaCodeFixedPaths)) {
    $base=$old;if($rel.StartsWith('diagnostic/')){$base=$new}
    $file=Join-Path $base $rel;[void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($file))
    [IO.File]::WriteAllText($file,('public-fixture-'+$rel))
    if(-not $rel.StartsWith('diagnostic/')){$lines+=((Get-MfaCodeHash $file)+'  '+$rel)}
}
[IO.File]::WriteAllLines((Join-Path $old 'SHA256SUMS'),$lines)
# Fixture replaces only the old SUMS pin. Every actual source/destination hash runs.
function Get-MfaCodeHash([string]$Path) {
    if([IO.Path]::GetFileName($Path) -ceq 'SHA256SUMS') { return '803a8373d7c9fa8cc9d230e285f4b4e5ca0b84f222c68d10980278652f16035b' }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
$context=[pscustomobject]@{oldPackage=$old;package=$new}
$manifest=Get-DiagnosticCodeManifest $context
'''

PAYLOAD_DOUBLE = r'''
# Exclusive creation semantics in TEMP; deliberately no claim about real BA ACL.
Add-Type -TypeDefinition @'
using System.IO;
namespace RackClick.SystemReadTrial { public static class Folder {
 public static int Create(string path,string descriptor) {
  if(Directory.Exists(path)||File.Exists(path))return 183;
  Directory.CreateDirectory(path);return 0;
 }
} }
'@
function Assert-MfaCodeAcl([string]$Path,[string]$ReaderSid,[bool]$IsRoot) {
    if(-not (Test-Path -LiteralPath $Path)){throw 'fixture_path_absent'}
}
$leases=New-Object Collections.Generic.List[IDisposable]
'''


@unittest.skipUnless(PS, 'Windows PowerShell 5.1 required')
class DiagnosticCodeTests(unittest.TestCase):
    def run_ps(self, body):
        with tempfile.TemporaryDirectory(prefix='rc-code-contract-') as directory:
            script = Path(directory) / 'test.ps1'
            script.write_text(PRELUDE + body, encoding='ascii')
            env = os.environ.copy()
            env.update(RC_CODE_SOURCE=str(SOURCE), RC_CODE_FIXTURE=directory)
            env['PSModulePath'] = str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/Modules')
            result = subprocess.run([PS, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                     '-File', str(script)], env=env, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_functions_only_parse_and_no_acl_or_external_mutation_commands(self):
        self.run_ps(r'''
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($env:RC_CODE_SOURCE,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'parse_error'}
foreach($node in $ast.EndBlock.Statements) {
    if($node -isnot [Management.Automation.Language.FunctionDefinitionAst]){throw 'top_level_execution'}
}
$commands=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst]},$true)|ForEach-Object{$_.GetCommandName()})
foreach($command in @('Set-Acl','Remove-Item','Copy-Item','Start-Process','Get-CimInstance','Register-ScheduledTask','Start-Service')) {
    if($command -in $commands){throw 'forbidden_command'}
}
''')

    def test_programdata_sibling_exact_prefix_and_reader_sid(self):
        self.run_ps(r'''
if((Assert-DiagnosticCodePath $root) -cne $root){throw 'root_mismatch'}
foreach($path in @((Join-Path $root 'child'),(Join-Path $env:ProgramData 'RackClick-MFA-Code-short'),
    (Join-Path $env:ProgramData ('RackClick-MFA-Code-'+('A'*32))),
    (Join-Path $env:ProgramData ('Other-'+('a'*32))))) { Must-Fail { Assert-DiagnosticCodePath $path } 'root_invalid' }
foreach($path in @('C:\ProgramData\..\bad','C:\ProgramData\bad:ads','C:\ProgramData\bad.','\\server\share\x')) {
    Must-Fail { Assert-DiagnosticCodePath $path } 'path_invalid'
}
Assert-MfaCodeReader $reader
foreach($sid in @('S-1-5-18','S-1-5-32-544','S-1-5-32-545','S-1-5-80-123','S-1-5-21-1-2-3-01','S-1-5-21-1-2-3-4294967296')) {
    Must-Fail { Assert-MfaCodeReader $sid } 'reader_invalid'
}
''')

    def test_manifest_exact_352_digest_exclusions_and_source_scope(self):
        self.run_ps(FIXTURE + r'''
if($manifest.count -ne 352){throw 'count'}
$rel=@($manifest.entries.rel)
if(@($rel|Where-Object{$_ -match '\.(pdb|ps1)$|BUILD|key|plan|state'}).Count){throw 'private_entry'}
$original=$manifest.entries[0].source
$manifest.entries[0].source=Join-Path $old $manifest.entries[0].rel
Must-Fail { Assert-MfaCodeManifest $manifest } 'source_scope_invalid'
$manifest.entries[0].source=$original
$manifest.entries[0].sha256='a'*64
Must-Fail { Assert-MfaCodeManifest $manifest } 'manifest_digest_invalid'
''')

    def test_manifest_rejects_duplicate_invalid_profile_and_runtime_source_tamper(self):
        self.run_ps(FIXTURE + r'''
$saved=$manifest.entries[1].rel;$manifest.entries[1].rel=$manifest.entries[0].rel
Must-Fail { Assert-MfaCodeManifest $manifest } 'manifest_entry_invalid'
$manifest.entries[1].rel=$saved
$runtime=@($manifest.entries|Where-Object{$_.rel.StartsWith('runtime/')})[0]
$saved=$runtime.rel;$runtime.rel='runtime/private.ps1'
Must-Fail { Assert-MfaCodeManifest $manifest } 'manifest_entry_invalid'
$runtime.rel=$saved
[IO.File]::WriteAllText($runtime.source,'changed')
Must-Fail { Get-DiagnosticCodeManifest $context } 'source_hash_invalid'
''')

    def test_acl_real_descriptors_root_child_owner_masks_and_unsafe_aces(self):
        self.run_ps(r'''
$directory=Join-Path $env:ProgramData 'acl-dir';[void][IO.Directory]::CreateDirectory($directory)
$file=Join-Path $directory 'file';[IO.File]::WriteAllText($file,'fixture')
function Get-Acl { param([string]$LiteralPath) return $script:fixtureAcl }
function Fixture-Acl([string]$Sddl) {
    $script:fixtureAcl=New-Object Security.AccessControl.DirectorySecurity
    $script:fixtureAcl.SetSecurityDescriptorSddlForm($Sddl)
}
$rootSddl='O:BAG:SYD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FRFX;;;'+$reader+')'
Fixture-Acl $rootSddl;Assert-MfaCodeAcl $directory $reader $true
Fixture-Acl ('O:SYG:SYD:(A;OICIID;FA;;;SY)(A;OICIID;FA;;;BA)(A;OICIID;FRFX;;;'+$reader+')')
Assert-MfaCodeAcl $directory $reader $false
Fixture-Acl ('O:SYG:SYD:(A;ID;FA;;;SY)(A;ID;FA;;;BA)(A;ID;FRFX;;;'+$reader+')')
Assert-MfaCodeAcl $file $reader $false
foreach($sddl in @($rootSddl.Replace('O:BA','O:SY'),$rootSddl.Replace('O:BA',('O:'+$reader)),
 $rootSddl.Replace('FRFX','FA'),$rootSddl.Replace('FRFX','FR'),$rootSddl.Replace('D:P','D:'),
 ($rootSddl+'(A;OICI;FR;;;BU)'),$rootSddl.Replace('(A;OICI;FA;;;SY)',''),
 $rootSddl.Replace('(A;OICI;FRFX','(D;OICI;FRFX'),$rootSddl.Replace('(A;OICI;FRFX','(A;OICINP;FRFX'))) {
    Fixture-Acl $sddl;Must-Fail { Assert-MfaCodeAcl $directory $reader $true } 'acl_invalid'
}
''')

    def test_fixture_copy_exclusive_hash_leases_and_extra_file_rejection(self):
        self.run_ps(FIXTURE + PAYLOAD_DOUBLE + r'''
try {
    New-DiagnosticCodePayload $root $reader $manifest $leases
    if(@(Get-ChildItem -LiteralPath $root -Recurse -File).Count -ne 352){throw 'count'}
    Must-Fail { New-DiagnosticCodePayload $root $reader $manifest $leases } 'root_exists'
    $target=Join-Path $root $manifest.entries[0].rel
    $blocked=$false
    try{$write=[IO.File]::Open($target,'Open','Write','Read');$write.Dispose()}catch{$blocked=$true}
    if(-not $blocked){throw 'lease_write_not_blocked'}
    [IO.File]::WriteAllText((Join-Path $root 'private.pdb'),'extra')
    Must-Fail { Assert-DiagnosticCodePayload $root $reader $manifest $leases } 'extra_file'
} finally { foreach($lease in $leases){$lease.Dispose()} }
''')

    def test_payload_rejects_corruption_missing_extra_directory_and_source_changed(self):
        self.run_ps(FIXTURE + PAYLOAD_DOUBLE + r'''
try { New-DiagnosticCodePayload $root $reader $manifest $leases }
finally {foreach($lease in $leases){$lease.Dispose()};$leases.Clear()}
$target=Join-Path $root $manifest.entries[0].rel
$original=[IO.File]::ReadAllBytes($target)
[IO.File]::WriteAllBytes($target,([byte[]](0)*$original.Length))
try { Must-Fail { Assert-DiagnosticCodePayload $root $reader $manifest $leases } 'payload_hash_invalid' }
finally {foreach($lease in $leases){$lease.Dispose()};$leases.Clear()}
[IO.File]::WriteAllBytes($target,$original)
[IO.File]::Delete($target)
try { Must-Fail { Assert-DiagnosticCodePayload $root $reader $manifest $leases } 'payload_count_invalid' }
finally {foreach($lease in $leases){$lease.Dispose()};$leases.Clear()}
[IO.File]::WriteAllBytes($target,$original)
[void][IO.Directory]::CreateDirectory((Join-Path $root 'extra'))
try { Must-Fail { Assert-DiagnosticCodePayload $root $reader $manifest $leases } 'extra_directory' }
finally {foreach($lease in $leases){$lease.Dispose()};$leases.Clear()}
$root=Join-Path $env:ProgramData ('RackClick-MFA-Code-'+('b'*32))
[IO.File]::WriteAllText($manifest.entries[0].source,'changed')
try {Must-Fail { New-DiagnosticCodePayload $root $reader $manifest $leases } 'source_changed'}
finally {foreach($lease in $leases){$lease.Dispose()}}
''')

    def test_reparse_point_rejected_with_owned_junction(self):
        self.run_ps(r'''
$target=Join-Path $env:ProgramData 'target';[void][IO.Directory]::CreateDirectory($target)
$junction=Join-Path $env:ProgramData 'junction'
$null=New-Item -ItemType Junction -Path $junction -Target $target
try {Must-Fail { Assert-MfaCodeNoReparse $junction } 'reparse'}
finally {[IO.Directory]::Delete($junction)}
''')


if __name__ == '__main__':
    unittest.main(verbosity=2)
