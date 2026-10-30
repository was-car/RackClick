"""Native Windows provisioning of NEW private instances, no existing QA/SCM/HTTPS."""
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
from pg_support import free_port, protect_directory
TOOLS=ROOT/'tools/windows'
PS=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
BASELINE=ROOT/'evidence/s1-20261017/seis-tandas-180-185/CANDIDATA185.json'
BASELINE_SHA='68aca94da20751b690af0c1c6b764a1db1004d3d63be2a12161938a3624d7706'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
write=lambda p,d:p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))


class InstanceProvisioning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert os.name=='nt' and sha(BASELINE)==BASELINE_SHA
        cls.calls=[]; cls.instances=[]
        cls.home=ROOT/'.local/provisioning-labs'/('instance218-'+uuid.uuid4().hex)
        cls.home.mkdir(parents=True,exist_ok=False); protect_directory(cls.home)
        cls.pg=ROOT/'.local/postgresql-17.11-4/pgsql/bin'
        cls.dotnet=ROOT/'.local/dotnet-10.0.401/dotnet.exe'
        cls.manifest=read(BASELINE); cls.candidate=ROOT/cls.manifest['candidateDirectory']
        sources=[Path(__file__),BASELINE]+[TOOLS/name for name in ('RackClick.Instance.ps1','New-RackClickLabInstance.ps1',
            'RackClick.Process.ps1','RackClick.Process.Gate.ps1','RackClick.Backup.ps1','RackClick.Stage.ps1',
            'Test-RuntimePrerequisites.ps1','Test-ServerDistribution.ps1','Stage-ServerDistribution.ps1','Test-StagedDistribution.ps1')]
        for kind,files in cls.manifest['distributions'].items():
            for name,digest in files.items():
                p=cls.candidate/kind/name; assert sha(p)==digest; sources.append(p)
        cls.guards={str(p):sha(p) for p in sources}
        cls.stage=cls.home/'stage Ω'
        cls.receipt=cls.invoke('setup-stage','Stage-ServerDistribution.ps1',dict(ManifestPath=BASELINE,ExpectedManifestSha256=BASELINE_SHA,
            ServerPath=cls.candidate/'server',FrontendPath=cls.candidate/'frontend',DotNetPath=cls.dotnet,PostgresBinPath=cls.pg,DestinationPath=cls.stage))['receiptSha256']

    @classmethod
    def tearDownClass(cls):
        cls.inputs_unchanged=all(sha(Path(p))==digest for p,digest in cls.guards.items())
        cls.processes_stopped=True
        for item in cls.instances:
            for port in (item['postgresPort'],item['httpPort']):
                with socket.socket() as connection:
                    if connection.connect_ex(('127.0.0.1',port))==0: cls.processes_stopped=False
        assert cls.inputs_unchanged and cls.processes_stopped

    @classmethod
    def invoke(cls,case,name,args,expected=0,code=None):
        command=[str(PS),'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(TOOLS/name)]
        for k,v in args.items():
            if isinstance(v,bool):
                if v:command.append('-'+k)
            else:command.extend(['-'+k,str(v)])
        started=time.monotonic(); p=subprocess.run(command,capture_output=True,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
        try:data=json.loads(p.stdout.decode('utf-8-sig'))
        except (UnicodeError,ValueError):data=dict(unparsed=True)
        cls.calls.append(dict(case=case,script=name,exitCode=p.returncode,seconds=round(time.monotonic()-started,3),report=data,stderrEmpty=not p.stderr))
        assert not p.stderr,'Native stderr retained privately; never export raw credentials'
        assert p.returncode==expected,(p.returncode,data)
        assert data['exitCode']==expected and data['valid']==(expected==0),data
        if code:assert data['code']==code,data
        return data

    def args(self,label):
        pgport=free_port();httpport=free_port()
        while httpport==pgport:httpport=free_port()
        return dict(StagePath=self.stage,ExpectedManifestSha256=BASELINE_SHA,ExpectedReceiptSha256=self.receipt,
            DotNetPath=self.dotnet,PostgresBinPath=self.pg,InstancePath=self.home/(label+' new'),PostgresPort=pgport,
            PublicOrigin='http://127.0.0.1:'+str(httpport),BootstrapUser=' Ädmin Ω ',SystemhausName='Laboratorio ñ 漢字',DevelopmentLoopbackHttp=True)

    def native_probe(self,args,digest,expected=0,code=None,inspect=False):
        script=self.home/('probe-'+uuid.uuid4().hex+'.ps1')
        script.write_bytes(r'''param([string]$InstancePath,[string]$ExpectedInstanceSha256,[string]$Helper,[switch]$Inspect)
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
$PostgresBinPath=''
. $Helper
$value=$null;$pgHandle=$null
$report=@{valid=$false;exitCode=2;code='probe_failed'}
try {
 $value=Read-RackClickInstance $InstancePath $ExpectedInstanceSha256
 if ($Inspect) {
  $env=New-InstanceEnvironment @{PGCLIENTENCODING='UTF8';PGCONNECT_TIMEOUT='5'}
  $pgHandle=Start-RackClickOwnedProcess -Executable (Join-Path $value.pgBin 'postgres.exe') -Arguments @('-D','pgdata') -WorkingDirectory $value.root -Environment $env -LogDirectory $value.logRoot -Label 'test-inspect'
  $profile=Read-BackupProfile (Join-Path $value.privateRoot 'backup-profile.json')
  $ready=$false
  for ($i=0;$i -lt 60;$i++) { try { Assert-BackupServerVersion $value.pgBin $profile;$ready=$true;break } catch { Start-Sleep -Milliseconds 100 } }
  if (-not $ready) { Stop-InstanceCheck 'inspect_not_ready' }
  $args=@('-X','-A','-t','-v','ON_ERROR_STOP=1')+(Get-BackupConnectionArguments $profile $profile.database)
  $sql="SELECT (SELECT max(version) FROM schema_migration),(SELECT count(*) FROM app_user),(SELECT count(*) FROM pg_roles WHERE rolname IN ('$($value.owner)','$($value.runtime)') AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole),(SELECT has_schema_privilege('$($value.runtime)','public','CREATE')),(SELECT setting FROM pg_settings WHERE name='data_checksums');"
  $checks=Invoke-BackupPg (Join-Path $value.pgBin 'psql.exe') $args $profile $sql
  if ($checks -cne '9|1|2|f|on') { Stop-InstanceCheck 'inspect_checks_failed' }
  Assert-InstanceOwnedPostgres $pgHandle $value.pgData
  $null=Invoke-InstanceChild (Join-Path $value.pgBin 'pg_ctl.exe') @('stop','-D','pgdata','-m','fast','-w','-t','30') $value.root $env $value.logRoot 'test-inspect-stop'
  Stop-RackClickOwnedProcess $pgHandle;$pgHandle=$null
 }
 $report=@{valid=$true;exitCode=0;code='instance_verified';id=$value.id;adminUser=$value.adminUser;inspectionPassed=[bool]$Inspect}
} catch { if ($_.Exception.Data.Contains('instanceCode')) { $report.code=$_.Exception.Data['instanceCode'] } elseif ($_.Exception.Data.Contains('code')) { $report.code=$_.Exception.Data['code'] } }
finally { if ($null -ne $pgHandle) { Stop-RackClickOwnedProcess $pgHandle };if ($null -ne $value) { Close-RackClickInstance $value } }
$report|ConvertTo-Json -Compress
exit $report.exitCode
'''.encode('utf-8'))
        command=[str(PS),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),'-InstancePath',str(args['InstancePath']),
            '-ExpectedInstanceSha256',digest,'-Helper',str(TOOLS/'RackClick.Instance.ps1')]
        if inspect:command.append('-Inspect')
        p=subprocess.run(command,capture_output=True,timeout=100,creationflags=subprocess.CREATE_NO_WINDOW)
        try:data=json.loads(p.stdout.decode('utf-8-sig'))
        except (UnicodeError,ValueError):data=dict(unparsed=True)
        self.calls.append(dict(case=self._testMethodName,script='private instance validation probe',exitCode=p.returncode,report=data,stderrEmpty=not p.stderr))
        self.assertFalse(p.stderr);self.assertEqual(p.returncode,expected,data)
        if code:self.assertEqual(data['code'],code)
        return data

    def provision(self,label):
        args=self.args(label)
        result=self.invoke(self._testMethodName,'New-RackClickLabInstance.ps1',args,0,'instance_initialized')
        manifest=read(Path(args['InstancePath'])/'instance.json');self.instances.append(manifest)
        self.assertEqual(result['instanceManifestSha256'],sha(Path(args['InstancePath'])/'instance.json'))
        return args,result,manifest

    def test_01_provision_schema9_unicode_scram_roles_and_stopped(self):
        args,result,manifest=self.provision('positive')
        data=self.native_probe(args,result['instanceManifestSha256'],inspect=True)
        self.assertEqual(data['adminUser'],'ädmin ω');self.assertTrue(data['inspectionPassed'])
        root=Path(args['InstancePath']);self.assertFalse((root/'pgdata/postmaster.pid').exists())
        hba=(root/'pgdata/pg_hba.conf').read_text(encoding='utf-8')
        active=[line for line in hba.splitlines() if line.strip() and not line.lstrip().startswith('#')]
        self.assertTrue(active);self.assertTrue(all('scram-sha-256' in line for line in active))
        self.assertEqual(len(manifest['secretFiles']),5)
        # No actual secret bytes in public report/evidence.
        public=json.dumps(self.calls,ensure_ascii=False)
        admin=read(root/'private/admin-login.json')
        for secret in [admin['password'],(root/'private/owner-password.txt').read_text(),(root/'private/cluster-password.txt').read_text()]:self.assertNotIn(secret,public)

    def test_02_existing_optin_origin_and_busy_port(self):
        args=self.args('existing');root=Path(args['InstancePath']);root.mkdir();(root/'sentinel').write_bytes(b'existing')
        self.invoke(self._testMethodName,'New-RackClickLabInstance.ps1',args,1,'instance_destination_exists');self.assertEqual((root/'sentinel').read_bytes(),b'existing')
        args=self.args('no-optin');args['DevelopmentLoopbackHttp']=False
        self.invoke(self._testMethodName,'New-RackClickLabInstance.ps1',args,2,'development_loopback_optin_required')
        args=self.args('remote');args['PublicOrigin']='http://192.0.2.1:55555'
        self.invoke(self._testMethodName,'New-RackClickLabInstance.ps1',args,2,'origin_invalid')
        args=self.args('occupied')
        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1',args['PostgresPort']));occupied.listen()
            self.invoke(self._testMethodName,'New-RackClickLabInstance.ps1',args,1,'port_unavailable')
        self.assertFalse(Path(args['InstancePath']).exists())

    def test_03_expected_stage_hash_rejected_before_creation(self):
        args=self.args('bad-stage');args['ExpectedReceiptSha256']='0'*64
        self.invoke(self._testMethodName,'New-RackClickLabInstance.ps1',args,1,'stage_receipt_untrusted')
        self.assertFalse(Path(args['InstancePath']).exists())

    def test_04_bootstrap_failure_preserved_no_manifest_no_reuse(self):
        broken=self.home/'broken-fixture-release';shutil.copytree(self.candidate,broken)
        sql=broken/'server/database/001-foundation.sql';sql.write_bytes(sql.read_bytes()+b'\nSELECT intentionally_missing_fixture_function();\n')
        manifest=copy.deepcopy(self.manifest);manifest['distributions']['server']['database/001-foundation.sql']=sha(sql)
        path=self.home/'broken-fixture-manifest.json';write(path,manifest);digest=sha(path)
        stage=self.home/'broken-stage'
        receipt=self.invoke(self._testMethodName,'Stage-ServerDistribution.ps1',dict(ManifestPath=path,ExpectedManifestSha256=digest,
            ServerPath=broken/'server',FrontendPath=broken/'frontend',DotNetPath=self.dotnet,PostgresBinPath=self.pg,DestinationPath=stage))['receiptSha256']
        args=self.args('bootstrap-failure');args.update(StagePath=stage,ExpectedManifestSha256=digest,ExpectedReceiptSha256=receipt)
        self.invoke(self._testMethodName,'New-RackClickLabInstance.ps1',args,1,'bootstrap_failed')
        root=Path(args['InstancePath']);self.assertTrue((root/'pgdata').is_dir());self.assertFalse((root/'instance.json').exists())
        self.assertEqual(read(root/'instance-state.json')['status'],'failed')
        with socket.socket() as connection:self.assertNotEqual(connection.connect_ex(('127.0.0.1',args['PostgresPort'])),0)
        self.invoke(self._testMethodName,'New-RackClickLabInstance.ps1',args,1,'instance_destination_exists')

    def test_05_unicode_name_limits_preflight(self):
        for i,name in enumerate(('x'*101,'bad\x01control','   ')):
            args=self.args('invalid-name'+str(i));args['BootstrapUser']=name
            self.invoke(self._testMethodName,'New-RackClickLabInstance.ps1',args,2,'name_invalid')
            self.assertFalse(Path(args['InstancePath']).exists())

    def test_06_unicode_technical_root_rejected_without_creation(self):
        args=self.args('unicode-root');args['InstancePath']=self.home/'unsupported Ω'
        sentinel=self.home/'parent-sentinel.txt';sentinel.write_bytes(b'parent preserved')
        before=sorted(p.name for p in self.home.iterdir())
        self.invoke(self._testMethodName,'New-RackClickLabInstance.ps1',args,2,'instance_root_ascii_required')
        self.assertFalse(Path(args['InstancePath']).exists())
        self.assertEqual(before,sorted(p.name for p in self.home.iterdir()))
        self.assertEqual(sentinel.read_bytes(),b'parent preserved')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',required=True);parser.add_argument('--cases',nargs='*');options=parser.parse_args()
    evidence=Path(options.evidence).resolve();evidence.mkdir(parents=True,exist_ok=False)
    suite=(unittest.TestSuite(InstanceProvisioning(name) for name in options.cases) if options.cases else unittest.defaultTestLoader.loadTestsFromTestCase(InstanceProvisioning))
    started=time.monotonic()
    with (evidence/'tests.log').open('w',encoding='utf-8') as output:result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,failures=len(result.failures),errors=len(result.errors),successful=result.wasSuccessful(),seconds=round(time.monotonic()-started,3),fixture=str(getattr(InstanceProvisioning,'home','not initialized')),sourceHashes=getattr(InstanceProvisioning,'guards',{}),inputsUnchanged=getattr(InstanceProvisioning,'inputs_unchanged',False),processesStopped=getattr(InstanceProvisioning,'processes_stopped',False),calls=getattr(InstanceProvisioning,'calls',[]),realQaAccess=0,appHttpExecutions=0)
    write(evidence/'result.json',report);print(json.dumps({k:report[k] for k in ('testsRun','failures','errors','successful','seconds','fixture')}))
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':sys.exit(main())
