"""Native creation factory: one complete lab, one deliberate bootstrap-load failure.
No HTTP app, SCM, trust-store changes, product builds or actual QA access.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import time
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'development/server/tests'))
from pg_support import free_port,protect_directory
TOOLS=ROOT/'tools/windows'
PS=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
BASELINE=ROOT/'evidence/s1-20261017/treinta-tandas-248-277/CANDIDATA277.json'
BASELINE_SHA='8f47ba4e48781aa010e3f3d8f9c85eae8003eb509336b1f6bf639ceac5a82a25'
FACTORY=TOOLS/'New-RackClickPrivateDeployment.ps1'
SOURCES=[FACTORY,Path(__file__)]+[TOOLS/name for name in ('RackClick.Deployment.ps1','RackClick.Https.ps1','RackClick.Instance.ps1',
    'RackClick.Stage.ps1','RackClick.Backup.ps1','RackClick.Process.ps1','RackClick.Process.Gate.ps1','Test-RuntimePrerequisites.ps1',
    'Test-ServerDistribution.ps1','Stage-ServerDistribution.ps1','Test-StagedDistribution.ps1','New-RackClickLabInstance.ps1','New-RackClickLabHttpsProfile.ps1')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
write=lambda p,d:p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
tree=lambda p:{f.relative_to(p).as_posix():sha(f) for f in p.rglob('*') if f.is_file()}

DRIVER=r'''param([string]$Helper,[string]$DeploymentPath,[string]$ExpectedDeploymentSha256)
$ProgressPreference='SilentlyContinue';$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
. $Helper
$deployment=$null;$report=@{valid=$false;exitCode=2;code='probe_failed'}
try {
 $deployment=Read-RackClickPrivateDeployment -DeploymentPath $DeploymentPath -ExpectedDeploymentSha256 $ExpectedDeploymentSha256
 $instance=$deployment.instance
 if (-not $deployment.httpsValidated -or $deployment.inputLocks.Count -ne 2 -or $instance.inputLocks.Count -ne 45 -or $deployment.https.inputLocks.Count -ne 4) {throw 'locks_count_invalid'}
 $paths=@((Join-Path $DeploymentPath 'deployment.json'),(Join-Path $DeploymentPath 'deployment-state.json'),$instance.manifestPath,(Join-Path $DeploymentPath 'https/tls.json'),(Join-Path $DeploymentPath 'https/server.pfx'))
 $blocked=0
 foreach ($path in $paths) {
  $writer=$null
  try {$writer=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Write,[IO.FileShare]::ReadWrite)}
  catch [IO.IOException] {if (($_.Exception.HResult-band 65535) -in @(32,33)) {$blocked++} else {throw}}
  finally {if ($null -ne $writer) {$writer.Dispose()}}
 }
 if ($blocked -ne 5) {throw 'writer_not_blocked'}
 if ([IO.File]::Exists((Join-Path $instance.pgData 'postmaster.pid'))) {throw 'postgres_pid_present'}
 $admin=[IO.File]::ReadAllText((Join-Path $instance.privateRoot 'admin-login.json'),[Text.Encoding]::UTF8)|ConvertFrom-Json
 $secrets=@($admin.password,[IO.File]::ReadAllText((Join-Path $instance.privateRoot 'cluster-password.txt')),[IO.File]::ReadAllText((Join-Path $instance.privateRoot 'owner-password.txt')),$deployment.https.password)
 $builder=New-Object Data.Common.DbConnectionStringBuilder;$builder.set_ConnectionString($instance.runtimeConnectionString)
 $secrets += [string]$builder['Password']
 if (@($secrets | Sort-Object -Unique).Count -ne 5 -or @($secrets | Where-Object {$_ -cnotmatch '^[a-f0-9]{64}$'}).Count -ne 0) {throw 'secrets_invalid'}
 $report=@{valid=$true;exitCode=0;code='deployment_verified';id=$deployment.id;instanceId=$instance.id;adminUser=$instance.adminUser;privateSecretCount=5;writeLocks=$blocked;httpsValidated=$true;instanceLocks=$instance.inputLocks.Count;rootLocks=$deployment.inputLocks.Count;tlsLocks=$deployment.https.inputLocks.Count;postgresStopped=$true;url=$deployment.https.origin}
} catch {
 foreach ($pair in @(@('deploymentCode','deploymentExit'),@('httpsCode','httpsExit'),@('instanceCode','instanceExit'),@('stageCode','stageExit'),@('code','exitCode'))) {
  if ($_.Exception.Data.Contains($pair[0])) {$report.code=$_.Exception.Data[$pair[0]];$report.exitCode=[int]$_.Exception.Data[$pair[1]];break}
 }
} finally {Close-RackClickPrivateDeployment $deployment}
$report|ConvertTo-Json -Compress
exit $report.exitCode
'''

SAME_PS=r'''param([string]$Factory,[string]$ArgumentsPath)
$ProgressPreference='SilentlyContinue';$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
$inputValue=[IO.File]::ReadAllText($ArgumentsPath,[Text.Encoding]::UTF8)|ConvertFrom-Json
$arguments=@{};foreach ($property in $inputValue.PSObject.Properties) {$arguments[$property.Name]=$property.Value}
$synthetic=@{'ConnectionStrings:RackClick'='synthetic-not-a-connection';'Bootstrap:User'='synthetic-invalid';'Kestrel:Endpoints:Trap:Url'='http://127.0.0.1:1';'RackClick:ShutdownToken'='synthetic-not-a-secret';'PG:fixture'='synthetic-marker';'ASPNETCORE_ENVIRONMENT'='synthetic-environment';'DOTNET_STARTUP_HOOKS'='synthetic-invalid-hook'}
foreach ($key in $synthetic.Keys) {[Environment]::SetEnvironmentVariable($key,$synthetic[$key],[EnvironmentVariableTarget]::Process)}
$beforeUser=[Environment]::GetEnvironmentVariables([EnvironmentVariableTarget]::User)
$beforeMachine=[Environment]::GetEnvironmentVariables([EnvironmentVariableTarget]::Machine)
$factoryOutput=& $Factory @arguments
$factoryExit=$LASTEXITCODE
$factoryReport=$factoryOutput|ConvertFrom-Json
$restored=$true
foreach ($key in $synthetic.Keys) {if ([Environment]::GetEnvironmentVariable($key,[EnvironmentVariableTarget]::Process) -cne $synthetic[$key]) {$restored=$false}}
$userUnchanged=$true;$machineUnchanged=$true
foreach ($pair in @(@($beforeUser,[EnvironmentVariableTarget]::User),@($beforeMachine,[EnvironmentVariableTarget]::Machine))) {
 $after=[Environment]::GetEnvironmentVariables($pair[1]);$equal=($after.Count -eq $pair[0].Count)
 foreach ($key in $pair[0].Keys) {if ($after[$key] -cne $pair[0][$key]) {$equal=$false}}
 if ($pair[1] -eq [EnvironmentVariableTarget]::User) {$userUnchanged=$equal} else {$machineUnchanged=$equal}
}
if ($factoryExit -ne 2 -or $factoryReport.valid -or $factoryReport.code -cne 'preflight_integrity_manifest_untrusted' -or -not $restored -or -not $userUnchanged -or -not $machineUnchanged) {throw 'same_ps_environment_check_failed'}
# Extract the REAL top-level finally. A private fake read handle fails Dispose;
# this is not a product switch or a second PostgreSQL run.
. (Join-Path ([IO.Path]::GetDirectoryName($Factory)) 'RackClick.Deployment.ps1')
$parseTokens=$null;$parseErrors=$null
$syntax=[Management.Automation.Language.Parser]::ParseFile($Factory,[ref]$parseTokens,[ref]$parseErrors)
if ($parseErrors.Count -ne 0) {throw 'source_parse_failed'}
$topTry=@($syntax.EndBlock.Statements|Where-Object {$_ -is [Management.Automation.Language.TryStatementAst]})
if ($topTry.Count -ne 1 -or $null -eq $topTry[0].Finally) {throw 'finally_not_found'}
$finallyText=$topTry[0].Finally.Extent.Text
$actualFinally=[scriptblock]::Create($finallyText.Substring(1,$finallyText.Length-2))
$badHandle=New-Object PSObject
$badHandle|Add-Member -MemberType ScriptMethod -Name Dispose -Value {throw 'controlled_cleanup_failure'}
$deployment=$null;$https=$null;$instance=$null;$stateStream=$null;$sourceLocks=@($badHandle);$owned=$false;$state=$null
$creationOriginalEnvironment=@{}
foreach ($key in $synthetic.Keys) {$creationOriginalEnvironment[$key]=$synthetic[$key];[Environment]::SetEnvironmentVariable($key,$null,[EnvironmentVariableTarget]::Process)}
$report=@{valid=$true;exitCode=0;code='synthetic_success';deploymentSha256=('a'*64);instanceId='synthetic';url='https://127.0.0.1:12345'}
& $actualFinally
$faultRestored=$true
foreach ($key in $synthetic.Keys) {if ([Environment]::GetEnvironmentVariable($key,[EnvironmentVariableTarget]::Process) -cne $synthetic[$key]) {$faultRestored=$false}}
if (-not $faultRestored -or $report.valid -or $report.exitCode -ne 2 -or $report.code -cne 'finalize_cleanup_failed' -or $report.deploymentSha256 -cne '') {throw 'cleanup_fault_not_closed'}
@{valid=$true;exitCode=0;code='same_ps_restoration_verified';factoryCode=$factoryReport.code;processRestored=$restored;userUnchanged=$userUnchanged;machineUnchanged=$machineUnchanged;cleanupFaultRestored=$faultRestored;cleanupFaultCode=$report.code;cleanupFaultHashEmpty=($report.deploymentSha256 -ceq '')}|ConvertTo-Json -Compress
'''


def ps(script,args):
    command=[str(PS),'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script)]
    for key,value in args.items():command+=['-'+key,str(value)]
    return command


class DeploymentCreation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert os.name=='nt' and sha(BASELINE)==BASELINE_SHA
        cls.home=ROOT/'.local/deployment-creation-labs'/('factory278-'+uuid.uuid4().hex)
        cls.home.mkdir(parents=True,exist_ok=False);protect_directory(cls.home)
        cls.driver=cls.home/'reader-probe.ps1';cls.driver.write_bytes(DRIVER.encode('ascii'))
        cls.same=cls.home/'same-ps.ps1';cls.same.write_bytes(SAME_PS.encode('ascii'))
        cls.baseline=read(BASELINE);cls.candidate=ROOT/cls.baseline['candidateDirectory'];cls.calls=[];cls.instances=[]
        cls.pg=ROOT/'.local/postgresql-17.11-4/pgsql/bin';cls.dotnet=ROOT/'.local/dotnet-10.0.401/dotnet.exe'
        cls.guards={str(p):sha(p) for p in SOURCES+[BASELINE]}
        for kind,files in cls.baseline['distributions'].items():
            for name,digest in files.items():
                path=cls.candidate/kind/name;assert sha(path)==digest;cls.guards[str(path)]=digest

    @classmethod
    def tearDownClass(cls):
        cls.inputs_unchanged=all(sha(Path(p))==digest for p,digest in cls.guards.items())
        cls.processes_stopped=True
        for args in cls.instances:
            for port in (args['PostgresPort'],args['HttpPort']):
                with socket.socket() as client:
                    if client.connect_ex(('127.0.0.1',port))==0:cls.processes_stopped=False
        assert cls.inputs_unchanged and cls.processes_stopped

    def arguments(self,label):
        pg=free_port();http=free_port()
        while http==pg:http=free_port()
        return dict(ManifestPath=BASELINE,ExpectedManifestSha256=BASELINE_SHA,ServerPath=self.candidate/'server',FrontendPath=self.candidate/'frontend',
            DotNetPath=self.dotnet,PostgresBinPath=self.pg,DestinationPath=self.home/label,PostgresPort=pg,HttpPort=http,
            BootstrapUser=' Ädmin Ω ',SystemhausName='Laboratorio ñ 漢字')

    def check(self,p,case,expected,code,started):
        tag=uuid.uuid4().hex;(self.home/(tag+'.stdout')).write_bytes(p.stdout);(self.home/(tag+'.stderr')).write_bytes(p.stderr)
        try:data=json.loads(p.stdout.decode('utf-8-sig'))
        except (UnicodeError,ValueError):data={'unparsed':True}
        self.calls.append(dict(case=case,exitCode=p.returncode,report=data,stderrEmpty=not p.stderr,seconds=round(time.monotonic()-started,3)))
        self.assertFalse(p.stderr,'Raw stderr retained in private fixture')
        self.assertEqual(p.returncode,expected,data);self.assertEqual(data.get('exitCode'),expected,data);self.assertEqual(data.get('valid'),expected==0,data)
        self.assertEqual(data.get('code'),code,data);return data

    def invoke(self,args,expected=0,code='deployment_prepared',script=FACTORY):
        started=time.monotonic();p=subprocess.run(ps(script,args),capture_output=True,timeout=400,creationflags=subprocess.CREATE_NO_WINDOW)
        return self.check(p,self._testMethodName,expected,code,started)

    def test_01_preflight_and_sentinel_no_mutation(self):
        sentinel=self.home/'parent-sentinel';sentinel.write_bytes(b'preserved')
        # Use only fresh source copies for a target rejection: even a regression
        # must never create a deployment under the original candidate directory.
        copied=self.home/'preflight-source-copy';shutil.copytree(self.candidate/'server',copied/'server');shutil.copytree(self.candidate/'frontend',copied/'frontend')
        copied_manifest=copied/'manifest.json';shutil.copy2(BASELINE,copied_manifest)
        for suffix,changes,expected,code in [
            ('missing-reference',dict(ExpectedManifestSha256=''),2,'preflight_manifest_reference_required'),
            ('invalid-user',dict(BootstrapUser='x'*101),2,'preflight_name_invalid'),
            ('unicode-root',dict(DestinationPath=self.home/'unsupported Ω'),2,'preflight_instance_root_ascii_required'),
            ('same-ports',dict(PostgresPort=24567,HttpPort=24567),2,'preflight_ports_must_differ'),
            ('wrong-hash',dict(ExpectedManifestSha256='0'*64),2,'preflight_integrity_manifest_untrusted'),
            ('overlap',dict(ManifestPath=copied_manifest,ServerPath=copied/'server',FrontendPath=copied/'frontend',DestinationPath=copied/'server/nested'),2,'preflight_paths_overlap')]:
            args=self.arguments(suffix);args.update(changes);target=Path(args['DestinationPath'])
            self.invoke(args,expected,code);self.assertFalse(target.exists())
        args=self.arguments('existing');target=Path(args['DestinationPath']);target.mkdir();(target/'sentinel').write_bytes(b'existing')
        before=tree(target);self.invoke(args,1,'preflight_destination_exists');self.assertEqual(tree(target),before)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0));listener.listen();args=self.arguments('occupied');args['PostgresPort']=listener.getsockname()[1]
            self.invoke(args,1,'preflight_port_unavailable');self.assertFalse(Path(args['DestinationPath']).exists())
        self.assertEqual(sentinel.read_bytes(),b'preserved')

    def test_02_real_creation_concurrent_rejection_receipt_and_locks(self):
        args=self.arguments('positive');self.instances.append(args);root=Path(args['DestinationPath'])
        started=time.monotonic();process=subprocess.Popen(ps(FACTORY,args),stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline=time.monotonic()+80;state=root/'deployment-state.json'
            while not state.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.025)
            self.assertTrue(state.exists());self.assertIsNone(process.poll())
            self.invoke(args,1,'preflight_destination_exists')
        finally:
            output,error=process.communicate(timeout=300)
        completed=subprocess.CompletedProcess(process.args,process.returncode,output,error)
        result=self.check(completed,self._testMethodName,0,'deployment_prepared',started)
        manifest=read(root/'deployment.json');self.assertEqual(len(manifest),11);self.assertEqual(result['deploymentSha256'],sha(root/'deployment.json'))
        self.assertEqual(set(p.name for p in root.iterdir()),{'distribution','instance','https','logs','deployment.json','deployment-state.json'})
        self.assertEqual(read(root/'deployment-state.json'),dict(schemaVersion=1,deploymentId=result['deploymentId'],status='prepared',code='deployment_prepared'))
        checked=self.invoke(dict(Helper=TOOLS/'RackClick.Deployment.ps1',DeploymentPath=root,ExpectedDeploymentSha256=result['deploymentSha256']),code='deployment_verified',script=self.driver)
        self.assertEqual(checked['adminUser'],'ädmin ω');self.assertTrue(checked['postgresStopped']);self.assertEqual(checked['writeLocks'],5)
        self.assertFalse((root/'instance/pgdata/postmaster.pid').exists())
        # The reader's retained immutable files are released afterwards.
        for name in ('deployment.json','deployment-state.json','instance/instance.json','https/tls.json','https/server.pfx'):
            with (root/name).open('r+b'):pass
        public=json.dumps(self.calls,ensure_ascii=False)
        for name in ('instance/private/owner-password.txt','instance/private/cluster-password.txt','https/pfx-password.txt'):
            self.assertNotIn((root/name).read_text(),public)

    def test_03_deliberate_deps_load_failure_preserved_no_receipt(self):
        copied=self.home/'deliberate-deps-fixture'
        # Source roots are explicit: never copy unrelated siblings such as an
        # offline deployment left in the candidate's parent by an earlier fixture.
        shutil.copytree(self.candidate/'server',copied/'server');shutil.copytree(self.candidate/'frontend',copied/'frontend')
        deps=copied/'server/RackClick.Server.deps.json';deps.write_bytes(b'{')
        manifest=copy.deepcopy(self.baseline);manifest['distributions']['server']['RackClick.Server.deps.json']=sha(deps)
        fixture_manifest=self.home/'deliberate-deps-manifest.json';write(fixture_manifest,manifest)
        fixture_guard=tree(copied);args=self.arguments('failed-stage')
        args.update(ManifestPath=fixture_manifest,ExpectedManifestSha256=sha(fixture_manifest),ServerPath=copied/'server',FrontendPath=copied/'frontend')
        self.instances.append(args);self.invoke(args,1,'instance_bootstrap_failed')
        root=Path(args['DestinationPath']);state=read(root/'deployment-state.json')
        self.assertEqual(state['status'],'failed');self.assertEqual(state['code'],'instance_bootstrap_failed')
        self.assertFalse((root/'deployment.json').exists());self.assertFalse((root/'instance/instance.json').exists());self.assertFalse((root/'https').exists())
        self.assertTrue((root/'instance/pgdata').is_dir());self.assertEqual(read(root/'instance/instance-state.json')['status'],'failed')
        self.assertEqual(tree(copied),fixture_guard)
        before=tree(root);self.invoke(args,1,'preflight_destination_exists');self.assertEqual(tree(root),before)
        self.calls.append(dict(case=self._testMethodName,fixtureManifestSha256=sha(fixture_manifest),fixtureDepsSha256=sha(deps),deliberateConfigurationFailure=True))

    def test_04_same_ps_environment_restored_and_reparse_rejected(self):
        args=self.arguments('same-ps');args['ExpectedManifestSha256']='0'*64
        arguments=self.home/'same-ps-arguments.json';write(arguments,{k:str(v) if isinstance(v,Path) else v for k,v in args.items()})
        self.invoke(dict(Factory=FACTORY,ArgumentsPath=arguments),code='same_ps_restoration_verified',script=self.same)
        self.assertFalse(Path(args['DestinationPath']).exists())
        real=self.home/'real-parent';real.mkdir();junction=self.home/'junction-parent'
        p=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(junction),str(real)],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(p.returncode,0)
        args=self.arguments('unused');args['DestinationPath']=junction/'new'
        self.invoke(args,2,'preflight_reparse_rejected');self.assertFalse((real/'new').exists())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',required=True,type=Path);parser.add_argument('--case',action='append');args=parser.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=False);snapshot=args.evidence/'sources-before';snapshot.mkdir()
    hashes={str(p):sha(p) for p in SOURCES+[BASELINE]}
    for p in SOURCES+[BASELINE]:
        target=snapshot/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
    suite=unittest.TestSuite(DeploymentCreation(name) for name in args.case) if args.case else unittest.defaultTestLoader.loadTestsFromTestCase(DeploymentCreation)
    started=time.monotonic()
    with (args.evidence/'tests.log').open('w',encoding='utf-8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),python=sys.version.split()[0],valid=result.wasSuccessful(),testsRun=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),sourceHashes=hashes,
        inputsUnchanged=getattr(DeploymentCreation,'inputs_unchanged',False),processesStopped=getattr(DeploymentCreation,'processes_stopped',False),
        privateFixture=str(getattr(DeploymentCreation,'home','')),calls=getattr(DeploymentCreation,'calls',[]),actualQaAccess=0,httpAppExecutions=0,
        scope='One successful native private creation and deliberate deps-load failure in separate new fixture; no SCM/trust-store writes/build')
    write(args.evidence/'result.json',report)
    print(json.dumps({k:report[k] for k in ('valid','testsRun','failures','errors','seconds')}))
    if not result.wasSuccessful():raise SystemExit(1)


if __name__=='__main__':main()
