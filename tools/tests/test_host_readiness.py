"""Bounded PS5.1 tests: declared synthetic inventory providers plus ONE real read.

No historical suite, PostgreSQL, SDK, bundle or application is executed. Real host
JSON stays under .local; committed evidence contains only counts, outcomes/hashes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'tools/windows/Get-RackClickHostReadiness.ps1'
PS = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
E = ROOT / 'evidence/s1-20261018/preparacion-cliente3-servidor/autor-host'
SHA = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
Q = lambda value: "'" + str(value).replace("'", "''") + "'"
CALLS = []
NATIVE = {}
FIXTURE = r"""
$global:fixtureProductType=1
$global:fixtureFailure=$false
function Get-CimInstance {
 [CmdletBinding()]param($ClassName,$Property,$Filter)
 if ($ClassName -ceq 'Win32_OperatingSystem') {
  if ($global:fixtureFailure) {throw 'fixture_cim_failure_sensitive_message_not_exported'}
  return [pscustomobject]@{Caption='Fixture Windows';Version='10.0.0';BuildNumber='1';OSArchitecture='64-bit';ProductType=$global:fixtureProductType;SerialNumber='DO_NOT_WRITE_SERIAL';RegisteredUser='DO_NOT_WRITE_USER'}
 }
 if ($ClassName -ceq 'Win32_ComputerSystem') {return [pscustomobject]@{TotalPhysicalMemory=17179869184L;UserName='DO_NOT_WRITE_USER'}}
 if ($ClassName -ceq 'Win32_LogicalDisk') {return [pscustomobject]@{DeviceID='C:';Size=1000000000L;FreeSpace=500000000L;VolumeSerialNumber='DO_NOT_WRITE_SERIAL'}}
 throw 'fixture_class_unexpected'
}
function Get-RackClickInventoryHostname {return 'fixture-host'}
function Get-RackClickInventoryEdition {return 'FixtureEdition'}
function Get-RackClickInventoryIPv4 {return @([ordered]@{address='192.0.2.10';prefixLength=24;interfaceIndex=1;interfaceAlias='Fixture';addressState='Preferred'})}
function Get-RackClickInventoryProfiles {return @([ordered]@{name='Fixture';interfaceIndex=1;interfaceAlias='Fixture';category='Private';ipv4Connectivity='LocalNetwork'})}
function Get-RackClickInventoryReboot {return [ordered]@{status='unknown';indicators=@();unreadableIndicators=@('windows_update')}}
function Get-RackClickInventoryEdge {return [ordered]@{status='not_found_in_checked_locations';version=$null;checkedScope='standard_local_install_locations'}}
"""


def run_ps(body=None, args=None, category='synthetic'):
    env = {key: value for key, value in os.environ.items() if key.upper() != 'PSMODULEPATH'}
    command = [str(PS), '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass']
    command += ['-File', str(SCRIPT), *args] if args is not None else ['-Command', body]
    result = subprocess.run(command, capture_output=True, env=env, timeout=90,
                            creationflags=0x08000000)
    stdout = result.stdout.decode('utf-8-sig')
    stderr = result.stderr.decode('utf-8-sig', errors='replace')
    CALLS.append(dict(category=category, exitCode=result.returncode, stderrEmpty=not stderr))
    return result.returncode, stdout, stderr


def privacy_keys(value):
    forbidden = {'serialnumber', 'volumeserialnumber', 'machineguid', 'productkey', 'password',
                 'credentials', 'environment', 'commandline', 'username', 'users', 'groups',
                 'sessions', 'databases', 'macaddress'}
    if isinstance(value, dict):
        assert not ({key.casefold() for key in value} & forbidden)
        for item in value.values():
            privacy_keys(item)
    elif isinstance(value, list):
        for item in value:
            privacy_keys(item)


class HostReadiness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not hasattr(cls, 'home'):
            cls.home = ROOT / '.local' / ('host-readiness-tests-' + uuid.uuid4().hex)
            cls.home.mkdir(parents=True, exist_ok=False)

    def test_01_synthetic_cim_logic_role_dc_optional_and_critical_failure(self):
        body = f'. {Q(SCRIPT)};' + FIXTURE + r"""
$a=Get-RackClickHostInventory 'Client3'
$global:fixtureProductType=3;$b=Get-RackClickHostInventory 'Server'
$global:fixtureProductType=2;$c=Get-RackClickHostInventory 'Server'
$global:fixtureFailure=$true;$d=Get-RackClickHostInventory 'Server'
$global:fixtureFailure=$false;$global:fixtureProductType=1;$w=Get-RackClickHostInventory 'Server'
@($a,$b,$c,$d,$w)|ConvertTo-Json -Depth 10 -Compress
"""
        code, stdout, stderr = run_ps(body)
        self.assertEqual((code, stderr), (0, ''))
        values = json.loads(stdout)
        self.assertEqual(len(values), 5)
        for value in values:
            self.assertEqual(value['readiness'], 'inventory_only')
            privacy_keys(value)
        self.assertNotIn('DO_NOT_WRITE', stdout)
        self.assertNotIn('sensitive_message', stdout)
        self.assertEqual([v['operatingSystem']['productType'] for v in values[:3]], [1, 3, 2])
        self.assertEqual(values[2]['operatingSystem']['productTypeName'], 'domain_controller')
        self.assertTrue(any(w['code'] == 'domain_controller_detected_inventory_only' for w in values[2]['warnings']))
        for value in values[:3]:
            self.assertTrue(value['valid'] and value['inventoryComplete'])
            self.assertEqual(value['exitCode'], 0)
            self.assertTrue(value['warnings'])
        self.assertFalse(values[3]['valid'])
        self.assertEqual(values[3]['exitCode'], 2)
        self.assertIsNone(values[3]['operatingSystem'])
        self.assertEqual(values[3]['errors'], [dict(area='operatingSystem', code='os_cim_inventory_failed')])
        self.assertTrue(values[4]['valid'] and values[4]['inventoryComplete'])
        self.assertEqual(values[4]['operatingSystem']['productType'], 1)
        self.assertEqual(values[4]['role'], 'Server')
        self.assertNotIn('requested_role_differs_from_product_type', [w['code'] for w in values[4]['warnings']])

    def test_02_synthetic_new_uuid_files_and_create_new_overwrite_impossible(self):
        directory = self.home / 'synthetic-output'
        directory.mkdir()
        body = f'. {Q(SCRIPT)};' + FIXTURE + f"""
$a=Get-RackClickHostInventory 'Client3';$first=Write-RackClickHostInventory $a {Q(directory)}
$blocked=$false;try{{Write-RackClickHostInventory $a {Q(directory)}|Out-Null}}catch{{$blocked=$true}}
$b=Get-RackClickHostInventory 'Client3';$second=Write-RackClickHostInventory $b {Q(directory)}
@{{first=$first;second=$second;collisionBlocked=$blocked}}|ConvertTo-Json -Compress
"""
        code, stdout, stderr = run_ps(body)
        self.assertEqual((code, stderr), (0, ''))
        value = json.loads(stdout)
        self.assertTrue(value['collisionBlocked'])
        self.assertNotEqual(value['first'], value['second'])
        self.assertEqual(len(list(directory.iterdir())), 2)
        for name in (value['first'], value['second']):
            report = json.loads((directory / name).read_bytes())
            self.assertTrue(name.startswith('RackClick-Host-Client3-'))
            self.assertIn(str(uuid.UUID(report['id'])), name)
            self.assertEqual(report['readiness'], 'inventory_only')
        # A stable first file must remain the same on another rejected write.
        original = directory / value['first']
        digest = SHA(original)
        body = f'. {Q(SCRIPT)};$report=Get-Content -LiteralPath {Q(original)} -Raw|ConvertFrom-Json;try{{Write-RackClickHostInventory $report {Q(directory)}|Out-Null;exit 9}}catch{{exit 0}}'
        code, _, stderr = run_ps(body)
        self.assertEqual((code, stderr), (0, ''))
        self.assertEqual(SHA(original), digest)

    def test_03_invalid_role_is_nonzero_honest_and_no_host_probe(self):
        directory = self.home / 'invalid-role'
        directory.mkdir()
        code, stdout, stderr = run_ps(args=['-Role', 'Other', '-OutputDirectory', str(directory)], category='invalid_input_no_cim')
        self.assertEqual((code, stderr), (2, ''))
        summary = json.loads(stdout)
        self.assertEqual(summary['readiness'], 'inventory_only')
        self.assertFalse(summary['valid'])
        report = json.loads((directory / summary['reportFileName']).read_bytes())
        self.assertIsNone(report['hostname'])
        self.assertIsNone(report['operatingSystem'])
        self.assertEqual(report['errors'], [dict(area='input', code='role_invalid')])
        failed = self.home / 'synthetic-cim-failure'
        failed.mkdir()
        body = f'. {Q(SCRIPT)};' + FIXTURE + f"$global:fixtureFailure=$true;Invoke-RackClickHostInventoryCommand 'Server' {Q(failed)}"
        code, stdout, stderr = run_ps(body, category='synthetic_cim_error_real_exit_code')
        self.assertEqual((code, stderr), (2, ''))
        summary = json.loads(stdout)
        self.assertFalse(summary['valid'])
        report = json.loads((failed / summary['reportFileName']).read_bytes())
        self.assertEqual(report['hostname'], 'fixture-host')
        self.assertIsNone(report['operatingSystem'])
        self.assertEqual(report['errors'], [dict(area='operatingSystem', code='os_cim_inventory_failed')])

    def test_04_native_ps51_read_once_current_windows(self):
        directory = self.home / 'native'
        directory.mkdir()
        code, stdout, stderr = run_ps(args=['-Role', 'Client3', '-OutputDirectory', str(directory)], category='native_current_windows_read_once')
        self.assertFalse(stderr)
        self.assertIn(code, [0, 2])
        summary = json.loads(stdout)
        report_path = directory / summary['reportFileName']
        report = json.loads(report_path.read_bytes())
        self.assertEqual(report['readiness'], 'inventory_only')
        self.assertTrue(report['powershell']['version'].startswith('5.1.'))
        self.assertTrue(report['powershell']['process64Bit'])
        self.assertEqual(code, report['exitCode'])
        self.assertEqual(report['valid'], not report['errors'])
        self.assertTrue(report['id'] and report['createdUtc'])
        privacy_keys(report)
        NATIVE.update(dict(exitCode=code, inventoryComplete=report['inventoryComplete'],
                          reportFile=report_path.relative_to(ROOT).as_posix(), reportSha256=SHA(report_path),
                          errorCount=len(report['errors']), warningCount=len(report['warnings']),
                          localDiskCount=len(report['localDisks']), ipv4Count=len(report['ipv4']),
                          profileCount=len(report['networkProfiles']), readiness=report['readiness'],
                          hostDataOutsideTrackedEvidence=True,
                          outputAclPolicy='inherits_existing_directory', encryptionProvided=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    HostReadiness.home = ROOT / '.local' / ('host-readiness-tests-' + uuid.uuid4().hex)
    HostReadiness.home.mkdir()
    baseline = json.loads((E / 'BASELINE.json').read_bytes())['guards']
    source_hashes = {str(p.relative_to(ROOT)): SHA(p) for p in [SCRIPT, Path(__file__)]}
    start = time.monotonic()
    with (args.output / 'tests.log').open('x', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(HostReadiness))
    guards = all(SHA(ROOT / name) == digest for name, digest in baseline.items())
    sources = all(SHA(ROOT / name) == digest for name, digest in source_hashes.items())
    report = dict(platform=platform.platform(), testsRun=result.testsRun, successful=result.wasSuccessful(),
                  failures=len(result.failures), errors=len(result.errors), seconds=round(time.monotonic() - start, 3),
                  sourceSha256=source_hashes, sourcesUnchanged=sources, protected200FilesUnchanged=guards,
                  syntheticTests=3, nativeCurrentHostExecutions=1, native=NATIVE, calls=CALLS,
                  actualQaSqlOrApplicationAccess=False, postgresExecuted=False, builds=0,
                  limits='Synthetic providers test logic and real new-file IO; native current host read once. No other Windows, server, topology, compatibility or installation certification.')
    (args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['testsRun', 'successful', 'seconds', 'protected200FilesUnchanged', 'sourcesUnchanged']}))
    return 0 if result.wasSuccessful() and guards and sources else 1


if __name__ == '__main__':
    raise SystemExit(main())
