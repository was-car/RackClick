"""Read-only deployment inspection on a NEW synthetic private Windows fixture.

Stages candidate277 once and makes valid instance/TLS files; never initdb, PG,
application, service, network listener, or trust-store mutation. Raw child output
and randomly generated secrets stay in the ignored private fixture.
"""
import argparse
from contextlib import contextmanager
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import subprocess
import sys
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import protect_directory

TOOLS = ROOT / 'tools/windows'
PS = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
BASELINE = ROOT / 'evidence/s1-20261017/treinta-tandas-248-277/CANDIDATA277.json'
BASELINE_SHA = '8f47ba4e48781aa010e3f3d8f9c85eae8003eb509336b1f6bf639ceac5a82a25'
SOURCES = [Path(__file__)] + [TOOLS / name for name in (
    'RackClick.Deployment.ps1', 'Test-RackClickPrivateDeployment.ps1',
    'RackClick.Https.ps1', 'New-RackClickLabHttpsProfile.ps1',
    'RackClick.Instance.ps1', 'RackClick.Stage.ps1', 'RackClick.Backup.ps1',
    'RackClick.Process.ps1', 'Test-RuntimePrerequisites.ps1',
    'Stage-ServerDistribution.ps1', 'Test-StagedDistribution.ps1',
    'Test-ServerDistribution.ps1')]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())
write = lambda p, d: p.write_bytes((json.dumps(d, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))

DRIVER = r'''param([string]$Helper,[string]$DeploymentPath,[string]$ExpectedDeploymentSha256,[switch]$Maintenance)
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
$DotNetPath='caller-dotnet';$PostgresBinPath='caller-postgres';$RuntimeConfigPath='caller-runtime';$PostgresVersion='caller-version'
$before=@($DotNetPath,$PostgresBinPath,$RuntimeConfigPath,$PostgresVersion,$DeploymentPath,$ExpectedDeploymentSha256)-join '|'
. $Helper
$deployment=$null;$result=@{valid=$false;exitCode=2;code='probe_failed'}
try {
 if ((@($DotNetPath,$PostgresBinPath,$RuntimeConfigPath,$PostgresVersion,$DeploymentPath,$ExpectedDeploymentSha256)-join '|') -cne $before) {throw 'caller_parameters_changed'}
 $deployment=Read-RackClickPrivateDeployment -DeploymentPath $DeploymentPath -ExpectedDeploymentSha256 $ExpectedDeploymentSha256 -Maintenance:$Maintenance
 $streams=@($deployment.inputLocks)+@($deployment.instance.inputLocks)
 if ($null -ne $deployment.https) {$streams+=@($deployment.https.inputLocks)}
 $blocked=0
 foreach ($stream in $streams) {
  $writer=$null
  try {$writer=[IO.File]::Open($stream.Name,[IO.FileMode]::Open,[IO.FileAccess]::Write,[IO.FileShare]::ReadWrite)}
  catch [IO.IOException] {if (($_.Exception.HResult-band 65535) -in @(32,33)) {$blocked++} else {throw}}
  finally {if ($null -ne $writer) {$writer.Dispose()}}
 }
 if ($blocked -ne $streams.Count -or $deployment.inputLocks.Count -ne 2) {throw 'locks_invalid'}
 $tlsUnlocked=$false
 if ($Maintenance) {
  if ($null -ne $deployment.https -or $deployment.httpsValidated) {throw 'maintenance_tls_invalid'}
  $writer=[IO.File]::Open((Join-Path $DeploymentPath 'https/server.pfx'),[IO.FileMode]::Open,[IO.FileAccess]::Write,[IO.FileShare]::ReadWrite)
  try {$tlsUnlocked=$true} finally {$writer.Dispose()}
 }
 $result=@{valid=$true;exitCode=0;code='reader_locks_verified';rootLocks=$deployment.inputLocks.Count;totalLocks=$streams.Count;writeLocks=$blocked;httpsValidated=$deployment.httpsValidated;tlsUnlocked=$tlsUnlocked;callerParametersPreserved=$true}
} catch {
 foreach ($pair in @(@('deploymentCode','deploymentExit'),@('httpsCode','httpsExit'),@('instanceCode','instanceExit'),@('stageCode','stageExit'),@('code','exitCode'))) {
  if ($_.Exception.Data.Contains($pair[0])) {$result.code=$_.Exception.Data[$pair[0]];$result.exitCode=[int]$_.Exception.Data[$pair[1]];break}
 }
} finally {Close-RackClickPrivateDeployment $deployment;Close-RackClickPrivateDeployment $deployment;Close-RackClickPrivateDeployment $null}
$result|ConvertTo-Json -Compress
exit $result.exitCode
'''

HOLDER = r'''param([string]$Lock,[string]$Marker)
$stream=[IO.File]::Open($Lock,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {[IO.File]::WriteAllText($Marker,'ready');[Console]::In.ReadLine()|Out-Null} finally {$stream.Dispose()}
'''


def ps(script, args):
    command = [str(PS), '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(script)]
    for key, value in args.items():
        command.append('-' + key)
        if value is not True:
            command.append(str(value))
    return command


def invoke(command, private, expected=0, code=None):
    started = time.monotonic()
    process = subprocess.run(command, capture_output=True, timeout=100, creationflags=subprocess.CREATE_NO_WINDOW)
    tag = uuid.uuid4().hex
    (private / (tag + '.stdout')).write_bytes(process.stdout)
    (private / (tag + '.stderr')).write_bytes(process.stderr)
    data = json.loads(process.stdout.decode('utf-8-sig'))
    assert not process.stderr, 'Raw child stderr retained only in private fixture'
    assert process.returncode == data['exitCode'], data
    if expected is None:
        assert process.returncode in (1, 2) and data.get('valid') is False, data
    else:
        assert process.returncode == expected and data.get('valid') == (expected == 0), data
    if code:
        assert data['code'] == code, data
    return dict(exitCode=process.returncode, report=data, stderrEmpty=True, seconds=round(time.monotonic() - started, 3))


class DeploymentInspection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert os.name == 'nt' and sha(BASELINE) == BASELINE_SHA
        cls.home = ROOT / '.local/deployment-inspection-labs' / ('inspection288-' + uuid.uuid4().hex)
        cls.home.mkdir(parents=True, exist_ok=False)
        protect_directory(cls.home)
        cls.driver = cls.home / 'reader-probe.ps1'
        cls.driver.write_bytes(DRIVER.encode('ascii'))
        cls.calls = []
        cls.guards = {str(p): sha(p) for p in SOURCES + [BASELINE]}
        cls.deployment = cls.home / 'deployment-ascii'
        cls.deployment.mkdir()
        cls.stage = cls.deployment / 'distribution'
        cls.instance = cls.deployment / 'instance'
        cls.https = cls.deployment / 'https'
        (cls.deployment / 'logs').mkdir()
        candidate = ROOT / read(BASELINE)['candidateDirectory']
        dotnet = ROOT / '.local/dotnet-10.0.401/dotnet.exe'
        pg = ROOT / '.local/postgresql-17.11-4/pgsql/bin'
        stage = cls.call('Stage-ServerDistribution.ps1', dict(ManifestPath=BASELINE, ExpectedManifestSha256=BASELINE_SHA,
            ServerPath=candidate / 'server', FrontendPath=candidate / 'frontend', DotNetPath=dotnet,
            PostgresBinPath=pg, DestinationPath=cls.stage), code='artifacts_staged')
        cls.instance.mkdir()
        for name in ('private', 'pgdata', 'logs'):
            (cls.instance / name).mkdir()
        private = cls.instance / 'private'
        identity = str(uuid.uuid4())
        suffix = identity.replace('-', '')
        roles = {key: prefix + suffix for key, prefix in dict(database='rc_db_', owner='rc_owner_', runtime='rc_runtime_', clusterAdmin='rc_cluster_').items()}
        owner_password = secrets.token_hex(32)
        runtime_password = secrets.token_hex(32)
        for name, password in [('owner-password.txt', owner_password), ('cluster-password.txt', secrets.token_hex(32))]:
            (private / name).write_text(password, encoding='ascii')
        write(private / 'admin-login.json', dict(username='Inspector sintético', password=secrets.token_hex(32)))
        write(private / 'backup-profile.json', dict(schemaVersion=1, host='127.0.0.1', port=55561,
            database=roles['database'], user=roles['owner'], passwordFile=str(private / 'owner-password.txt')))
        connection = f"Host=127.0.0.1;Port=55561;Database={roles['database']};Username={roles['runtime']};Password={runtime_password};SSL Mode=Disable;Timeout=5;Command Timeout=15;"
        write(private / 'runtime.json', dict(connectionString=connection))
        manifest = dict(schemaVersion=1, kind='RackClickLabInstance', id=identity, rootPath=str(cls.instance), stagePath=str(cls.stage),
            stageManifestSha256=BASELINE_SHA, stageReceiptSha256=stage['receiptSha256'], dotnetPath=str(dotnet), postgresBinPath=str(pg),
            postgresPort=55561, httpPort=55562, publicOrigin='http://127.0.0.1:55562', state='initialized', developmentLoopbackHttp=True,
            secretFiles={p.name: sha(p) for p in private.iterdir()}, **roles)
        write(cls.instance / 'instance.json', manifest)
        write(cls.instance / 'instance-state.json', dict(schemaVersion=1, instanceId=identity, status='initialized'))
        (cls.instance / 'instance.lock').write_bytes(b'')
        tls = cls.call('New-RackClickLabHttpsProfile.ps1', dict(InstancePath=cls.instance,
            ExpectedInstanceSha256=sha(cls.instance / 'instance.json'), DestinationPath=cls.https), code='https_profile_created')
        deployment_id = str(uuid.uuid4())
        write(cls.deployment / 'deployment.json', dict(schemaVersion=1, kind='RackClickPrivateDeployment', state='prepared',
            id=deployment_id, rootPath=str(cls.deployment), instanceId=identity, instanceManifestSha256=sha(cls.instance / 'instance.json'),
            stageManifestSha256=BASELINE_SHA, stageReceiptSha256=stage['receiptSha256'], httpsProfileSha256=tls['profileSha256'], publicOrigin='https://127.0.0.1:55562'))
        write(cls.deployment / 'deployment-state.json', dict(schemaVersion=1, deploymentId=deployment_id, status='prepared', code='deployment_prepared'))
        cls.digest = sha(cls.deployment / 'deployment.json')
        cls.fixture_guards = {str(p): sha(p) for p in cls.deployment.rglob('*') if p.is_file()}

    @classmethod
    def tearDownClass(cls):
        cls.inputs_unchanged = all(sha(Path(p)) == digest for p, digest in {**cls.guards, **cls.fixture_guards}.items())
        assert cls.inputs_unchanged

    @classmethod
    def call(cls, name, args, expected=0, code=None):
        record = invoke(ps(TOOLS / name, args), cls.home, expected, code)
        record['script'] = name
        cls.calls.append(record)
        return record['report']

    def inspect(self, expected=0, code=None, digest=None, maintenance=False, path=None):
        args = dict(DeploymentPath=path or self.deployment, ExpectedDeploymentSha256=self.digest if digest is None else digest)
        if maintenance:
            args['Maintenance'] = True
        return self.call('Test-RackClickPrivateDeployment.ps1', args, expected, code)

    def probe(self, maintenance=False):
        args = dict(Helper=TOOLS / 'RackClick.Deployment.ps1', DeploymentPath=self.deployment, ExpectedDeploymentSha256=self.digest)
        if maintenance:
            args['Maintenance'] = True
        record = invoke(ps(self.driver, args), self.home, 0, 'reader_locks_verified')
        record['script'] = 'private reader lock probe'
        self.calls.append(record)
        return record['report']

    @contextmanager
    def mutation(self, *paths):
        original = {path: path.read_bytes() for path in paths}
        try:
            yield
        finally:
            for path, content in original.items():
                path.write_bytes(content)

    def test_01_positive_public_report_retained_locks_and_release(self):
        report = self.inspect(code='deployment_verified')
        self.assertEqual(report['url'], 'https://127.0.0.1:55562')
        self.assertTrue(report['httpsValidated'])
        self.assertEqual(set(report), {'valid', 'exitCode', 'code', 'deploymentPath', 'deploymentId', 'instanceId', 'url', 'httpsValidated', 'scope'})
        probe = self.probe()
        self.assertEqual((probe['rootLocks'], probe['totalLocks'], probe['writeLocks']), (2, 51, 51))
        self.assertTrue(probe['callerParametersPreserved'])
        for path in self.deployment.rglob('*'):
            if path.is_file():
                with path.open('r+b'):
                    pass
        public = json.dumps(self.calls)
        for path in (self.instance / 'private').glob('*password.txt'):
            self.assertTrue(path.read_text() not in public, 'Public output contains a private secret')
        self.assertTrue((self.https / 'pfx-password.txt').read_text() not in public, 'Public output contains a private secret')

    def test_02_hash_corruption_missing_extra_hidden_and_json_types(self):
        self.inspect(2, 'deployment_reference_required', digest='')
        self.inspect(2, 'deployment_hash_mismatch', digest='0' * 64)
        payload = self.stage / 'server/RackClick.Server.dll'
        with self.mutation(payload):
            payload.write_bytes(payload.read_bytes() + b'x')
            self.inspect(None)
        with self.mutation(self.https / 'server.pfx'):
            (self.https / 'server.pfx').write_bytes(b'corrupt')
            self.inspect(2, 'https_profile_file_hash_mismatch')
            maintenance = self.inspect(code='deployment_maintenance_verified', maintenance=True)
            self.assertFalse(maintenance['httpsValidated'])
            probe = self.probe(maintenance=True)
            self.assertEqual((probe['totalLocks'], probe['writeLocks']), (47, 47))
            self.assertTrue(probe['tlsUnlocked'])
        missing = self.https / 'server.pem'
        with self.mutation(missing):
            missing.unlink()
            self.inspect(2, 'https_profile_contents_invalid')
        extra = self.deployment / 'hidden-untrusted'
        try:
            extra.write_bytes(b'x')
            self.assertTrue(ctypes.windll.kernel32.SetFileAttributesW(str(extra), 2))
            self.inspect(2, 'deployment_contents_invalid')
        finally:
            extra.unlink()
        manifest_path = self.deployment / 'deployment.json'
        for value in (True, '1'):
            with self.mutation(manifest_path):
                manifest = read(manifest_path);manifest['schemaVersion'] = value;write(manifest_path, manifest)
                self.inspect(2, 'deployment_manifest_invalid', digest=sha(manifest_path))
        with self.mutation(manifest_path):
            manifest = read(manifest_path);manifest['unexpected'] = 'x';write(manifest_path, manifest)
            self.inspect(2, 'deployment_manifest_invalid', digest=sha(manifest_path))
        with self.mutation(manifest_path):
            manifest_path.write_bytes(b' ' * 32769)
            self.inspect(2, 'deployment_manifest_invalid', digest=sha(manifest_path))

    def test_03_fixed_path_bindings_traversal_identity_and_failed_state(self):
        receipt = self.deployment / 'deployment.json'
        instance = self.instance / 'instance.json'
        for field, value in [('stagePath', str(self.home / 'outside')), ('stagePath', str(self.stage) + r'\..\outside'),
                             ('rootPath', str(self.home)), ('id', str(uuid.uuid4())), ('stageReceiptSha256', '0' * 64)]:
            with self.mutation(receipt, instance):
                manifest = read(instance);manifest[field] = value;write(instance, manifest)
                deployment = read(receipt);deployment['instanceManifestSha256'] = sha(instance);write(receipt, deployment)
                self.inspect(2, 'deployment_instance_binding_invalid', digest=sha(receipt))
        for field, value in [('postgresBinPath', str(self.deployment / 'logs')), ('dotnetPath', str(self.deployment / 'dotnet.exe'))]:
            with self.mutation(receipt, instance):
                manifest = read(instance);manifest[field] = value;write(instance, manifest)
                deployment = read(receipt);deployment['instanceManifestSha256'] = sha(instance);write(receipt, deployment)
                self.inspect(2, 'deployment_paths_overlap', digest=sha(receipt))
        for field, value, code in [('rootPath', str(self.home), 'deployment_manifest_invalid'), ('publicOrigin', 'https://localhost:55562', 'deployment_origin_invalid')]:
            with self.mutation(receipt):
                deployment = read(receipt);deployment[field] = value;write(receipt, deployment)
                self.inspect(2, code, digest=sha(receipt))
        state_path = self.deployment / 'deployment-state.json'
        with self.mutation(state_path):
            state = read(state_path);state['status'] = 'failed';write(state_path, state)
            self.inspect(2, 'deployment_state_invalid')
            self.inspect(2, 'deployment_state_invalid', maintenance=True)

    def test_04_private_acl_mutable_root_junction_and_exclusive_input_lock(self):
        target = self.instance / 'private/runtime.json'
        try:
            grant = subprocess.run(['icacls.exe', str(target), '/grant', '*S-1-5-32-545:R'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertEqual(grant.returncode, 0)
            self.inspect(2, 'private_acl_required')
        finally:
            revoke = subprocess.run(['icacls.exe', str(target), '/remove:g', '*S-1-5-32-545'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertEqual(revoke.returncode, 0)
        outside = self.home / 'junction-target';outside.mkdir()
        junction = self.instance / 'pgdata';junction.rmdir()
        linked = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(junction), str(outside)], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(linked.returncode, 0)
        try:
            self.inspect(2, 'reparse_rejected')
        finally:
            junction.rmdir()
            junction.mkdir()
        holder = self.home / 'lock-holder.ps1';holder.write_bytes(HOLDER.encode('ascii'))
        marker = self.home / 'lock-ready'
        process = subprocess.Popen(ps(holder, dict(Lock=self.deployment / 'deployment-state.json', Marker=marker)),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic() + 10
            while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(.025)
            self.assertTrue(marker.exists())
            self.inspect(2, 'deployment_verification_failed')
        finally:
            process.communicate(b'\n', timeout=10)
        self.assertEqual(process.returncode, 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    snapshot = args.evidence / 'sources-before';snapshot.mkdir()
    guards = {str(path): sha(path) for path in SOURCES}
    for path in SOURCES:
        destination = snapshot / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
    started = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromNames(args.case, DeploymentInspection) if args.case else unittest.defaultTestLoader.loadTestsFromTestCase(DeploymentInspection)
    with (args.evidence / 'tests.log').open('w', encoding='utf-8') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    report = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), python=sys.version.split()[0],
        sources=guards, valid=result.wasSuccessful(), testsRun=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        calls=getattr(DeploymentInspection, 'calls', []), inputsUnchanged=getattr(DeploymentInspection, 'inputs_unchanged', False),
        privateFixture=str(getattr(DeploymentInspection, 'home', '')), seconds=round(time.monotonic() - started, 3),
        scope='Synthetic private instance/TLS files, candidate277 staged once; no initdb/PG/app/SCM/network/trust writes')
    write(args.evidence / 'result.json', report)
    print(json.dumps({key: report[key] for key in ('valid', 'testsRun', 'failures', 'errors', 'seconds')}))
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == '__main__':
    main()
