"""Native PS5.1 loopback TLS sidecar tests. Synthetic instance files; no PG/app startup."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import socket
import ssl
import subprocess
import sys
import time
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'development/server/tests'))
from pg_support import protect_directory
TOOLS=ROOT/'tools/windows'
PS=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
BASELINE=ROOT/'evidence/s1-20261017/seis-tandas-180-185/CANDIDATA185.json'
BASELINE_SHA='68aca94da20751b690af0c1c6b764a1db1004d3d63be2a12161938a3624d7706'
SOURCES=[Path(__file__)]+[TOOLS/name for name in ('RackClick.Https.ps1','New-RackClickLabHttpsProfile.ps1',
    'RackClick.Instance.ps1','RackClick.Stage.ps1','RackClick.Backup.ps1','RackClick.Process.ps1',
    'Test-RuntimePrerequisites.ps1','Stage-ServerDistribution.ps1','Test-StagedDistribution.ps1','Test-ServerDistribution.ps1')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
write=lambda p,d:p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))

DRIVER=r'''param([string]$Mode,[string]$Helper,[string]$PrivateRoot,[string]$InstancePath,[string]$InstanceHash,[string]$ProfilePath,[string]$ProfileHash)
$ProgressPreference='SilentlyContinue';$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
. $Helper
function Read-Stores {
 $records=@();$count=0
 foreach ($location in [Enum]::GetValues([Security.Cryptography.X509Certificates.StoreLocation])) {
  foreach ($name in [Enum]::GetValues([Security.Cryptography.X509Certificates.StoreName])) {
   $store=New-Object Security.Cryptography.X509Certificates.X509Store($name,$location)
   try {
    $store.Open([Security.Cryptography.X509Certificates.OpenFlags]'ReadOnly,OpenExistingOnly')
    foreach ($cert in $store.Certificates) {
     try {$records += ([string]$location+'/'+[string]$name+'/'+(Get-HttpsBytesSha256 $cert.RawData));$count++} finally {$cert.Dispose()}
    }
   } catch {$records += ([string]$location+'/'+[string]$name+'/not-readable')}
   finally {$store.Dispose()}
  }
 }
 return @{digest=(Get-HttpsBytesSha256 ([Text.Encoding]::UTF8.GetBytes((($records|Sort-Object)-join "`n"))));count=$count}
}
$instance=$null;$profile=$null;$cert=$null;$result=@{valid=$false;exitCode=2;code='probe_failed'}
try {
 if ($Mode -eq 'Stores') {$result=@{valid=$true;exitCode=0;code='store_snapshot';snapshot=(Read-Stores)}}
 elseif ($Mode -eq 'Api') {
  $null=New-BackupPrivateDirectory $PrivateRoot;$id=[guid]::NewGuid().ToString('D')
  $before=Read-Stores;$metadata=New-HttpsCertificateFiles $PrivateRoot $id;$after=Read-Stores
  if ($before.digest -cne $after.digest) {throw 'store_changed'}
  $wrongPasswordRejected=$false
  try {$cert=New-Object Security.Cryptography.X509Certificates.X509Certificate2((Join-Path $PrivateRoot 'server.pfx'),'invalid',[Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet)} catch {$wrongPasswordRejected=$true}
  if (-not $wrongPasswordRejected) {throw 'wrong_password_accepted'}
  $result=@{valid=$true;exitCode=0;code='framework_api_verified';certificateSha256=$metadata.sha256;keySize=$metadata.keySize;wrongPasswordRejected=$true;storesUnchanged=$true;storeSnapshot=$before}
 } else {
  $instance=Read-RackClickInstance $InstancePath $InstanceHash
  $profile=Read-RackClickHttpsProfile -Instance $instance -ProfilePath $ProfilePath -ExpectedProfileSha256 $ProfileHash
  $blocked=0
  foreach ($name in @('tls.json','server.pfx','pfx-password.txt','server.pem')) {
   $writer=$null
   try {$writer=[IO.File]::Open((Join-Path $ProfilePath $name),[IO.FileMode]::Open,[IO.FileAccess]::Write,[IO.FileShare]::ReadWrite)}
   catch [IO.IOException] {if (($_.Exception.HResult-band 65535) -in @(32,33)) {$blocked++} else {throw}}
   finally {if ($null -ne $writer) {$writer.Dispose()}}
  }
  if ($blocked -ne 4 -or $profile.inputLocks.Count -ne 4) {throw 'locks_invalid'}
  $result=@{valid=$true;exitCode=0;code='https_profile_verified';origin=$profile.origin;certificateSha256=$profile.certificateSha256;writeLocks=$blocked;inputLocks=$profile.inputLocks.Count;passwordFormat=($profile.password -cmatch '^[a-f0-9]{64}$')}
 }
} catch {
 foreach ($pair in @(@('httpsCode','httpsExit'),@('instanceCode','instanceExit'),@('stageCode','stageExit'),@('code','exitCode'))) {
  if ($_.Exception.Data.Contains($pair[0])) {$result.code=$_.Exception.Data[$pair[0]];$result.exitCode=[int]$_.Exception.Data[$pair[1]];break}
 }
 # Private raw errors stay only in the newly generated lab fixture.
 if ([IO.Directory]::Exists($PrivateRoot)) {[IO.File]::AppendAllText((Join-Path $PrivateRoot 'probe-errors.log'),($_|Out-String))}
} finally {if ($null -ne $cert) {$cert.Dispose()};Close-RackClickHttpsProfile $profile;Close-RackClickInstance $instance}
$result|ConvertTo-Json -Depth 5 -Compress
exit $result.exitCode
'''


def invoke(command,private,expected=0,code=None):
    started=time.monotonic()
    p=subprocess.run(command,capture_output=True,timeout=100,creationflags=subprocess.CREATE_NO_WINDOW)
    tag=uuid.uuid4().hex
    (private/(tag+'.stdout')).write_bytes(p.stdout);(private/(tag+'.stderr')).write_bytes(p.stderr)
    try:data=json.loads(p.stdout.decode('utf-8-sig'))
    except (UnicodeError,ValueError):data={'unparsed':True}
    record=dict(exitCode=p.returncode,report=data,stderrEmpty=not p.stderr,seconds=round(time.monotonic()-started,3))
    assert not p.stderr,'Raw native stderr retained only in private fixture'
    assert p.returncode==expected,(p.returncode,data)
    assert data.get('exitCode')==expected and data.get('valid')==(expected==0),data
    if code:assert data['code']==code,data
    return record


def ps(script,args):
    command=[str(PS),'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script)]
    for key,value in args.items():command+=['-'+key,str(value)]
    return command


def new_private():
    path=ROOT/'.local/https-profile-labs'/('tls258-'+uuid.uuid4().hex)
    path.mkdir(parents=True,exist_ok=False);protect_directory(path)
    (path/'driver.ps1').write_bytes(DRIVER.encode('ascii'))
    return path


class HttpsProfile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert os.name=='nt' and sha(BASELINE)==BASELINE_SHA
        cls.home=new_private();cls.driver=cls.home/'driver.ps1';cls.calls=[]
        cls.guards={str(p):sha(p) for p in SOURCES+[BASELINE]}
        cls.stores_before=cls.driver_call('Stores')['snapshot']
        cls.stage=cls.home/'stage Ω';cls.instance=cls.home/'instance-ascii'
        baseline=read(BASELINE);candidate=ROOT/baseline['candidateDirectory']
        cls.dotnet=ROOT/'.local/dotnet-10.0.401/dotnet.exe';cls.pg=ROOT/'.local/postgresql-17.11-4/pgsql/bin'
        stage=cls.call('Stage-ServerDistribution.ps1',dict(ManifestPath=BASELINE,ExpectedManifestSha256=BASELINE_SHA,
            ServerPath=candidate/'server',FrontendPath=candidate/'frontend',DotNetPath=cls.dotnet,PostgresBinPath=cls.pg,DestinationPath=cls.stage))
        cls.instance.mkdir()
        for name in ('private','pgdata','logs'):(cls.instance/name).mkdir()
        identity=str(uuid.uuid4());suffix=identity.replace('-','')
        roles={key:prefix+suffix for key,prefix in dict(database='rc_db_',owner='rc_owner_',runtime='rc_runtime_',clusterAdmin='rc_cluster_').items()}
        private=cls.instance/'private';owner_password=secrets.token_hex(32);runtime_password=secrets.token_hex(32)
        for name,password in [('owner-password.txt',owner_password),('cluster-password.txt',secrets.token_hex(32))]:(private/name).write_text(password,encoding='ascii')
        write(private/'admin-login.json',dict(username='ädmin ω',password=secrets.token_hex(32)))
        write(private/'backup-profile.json',dict(schemaVersion=1,host='127.0.0.1',port=55431,database=roles['database'],user=roles['owner'],passwordFile=str(private/'owner-password.txt')))
        connection=f"Host=127.0.0.1;Port=55431;Database={roles['database']};Username={roles['runtime']};Password={runtime_password};SSL Mode=Disable;Timeout=5;Command Timeout=15;"
        write(private/'runtime.json',dict(connectionString=connection))
        manifest=dict(schemaVersion=1,kind='RackClickLabInstance',id=identity,rootPath=str(cls.instance),stagePath=str(cls.stage),
            stageManifestSha256=BASELINE_SHA,stageReceiptSha256=stage['receiptSha256'],dotnetPath=str(cls.dotnet),postgresBinPath=str(cls.pg),
            postgresPort=55431,httpPort=55432,publicOrigin='http://127.0.0.1:55432',state='initialized',developmentLoopbackHttp=True,
            secretFiles={p.name:sha(p) for p in private.iterdir()},**roles)
        write(cls.instance/'instance.json',manifest);cls.instance_hash=sha(cls.instance/'instance.json')
        write(cls.instance/'instance-state.json',dict(schemaVersion=1,instanceId=identity,status='initialized'))
        (cls.instance/'instance.lock').write_bytes(b'')
        cls.base_guards={str(p):sha(p) for p in cls.instance.rglob('*') if p.is_file()}

    @classmethod
    def tearDownClass(cls):
        cls.stores_after=cls.driver_call('Stores')['snapshot']
        cls.stores_unchanged=cls.stores_before==cls.stores_after
        cls.inputs_unchanged=all(sha(Path(p))==digest for p,digest in {**cls.guards,**cls.base_guards}.items())
        assert cls.stores_unchanged and cls.inputs_unchanged

    @classmethod
    def call(cls,name,args,expected=0,code=None):
        record=invoke(ps(TOOLS/name,args),cls.home,expected,code);record['script']=name;cls.calls.append(record)
        return record['report']

    @classmethod
    def driver_call(cls,mode,profile=None,digest=None,expected=0,code=None,instance=None,instance_hash=None):
        args=dict(Mode=mode,Helper=TOOLS/'RackClick.Https.ps1',PrivateRoot=cls.home,InstancePath=instance or getattr(cls,'instance',''),
            InstanceHash=instance_hash or getattr(cls,'instance_hash',''),ProfilePath=profile or '',ProfileHash=digest or '')
        record=invoke(ps(cls.driver,args),cls.home,expected,code);record['script']='private TLS reader probe';cls.calls.append(record)
        return record['report']

    def generate(self,label):
        path=self.home/(label+' TLS Ω')
        data=self.call('New-RackClickLabHttpsProfile.ps1',dict(InstancePath=self.instance,ExpectedInstanceSha256=self.instance_hash,DestinationPath=path),code='https_profile_created')
        self.assertEqual(data['profileSha256'],sha(path/'tls.json'));return path,data

    def clone_profile(self,path,label):
        import shutil
        target=self.home/label;shutil.copytree(path,target);return target

    def rehash_manifest(self,path):
        manifest=read(path/'tls.json')
        manifest['files']={name:sha(path/name) for name in manifest['files']}
        write(path/'tls.json',manifest);return sha(path/'tls.json')

    def test_01_certificate_files_reader_locks_and_isolated_context(self):
        path,data=self.generate('positive')
        checked=self.driver_call('Read',path,data['profileSha256'],code='https_profile_verified')
        self.assertEqual(checked['writeLocks'],4);self.assertTrue(checked['passwordFormat'])
        self.assertEqual(checked['origin'],'https://127.0.0.1:55432')
        cert=ssl._ssl._test_decode_cert(str(path/'server.pem'))
        self.assertEqual(set(cert['subjectAltName']),{('DNS','localhost'),('IP Address','127.0.0.1')})
        context=ssl.create_default_context(cafile=str(path/'server.pem'))
        self.assertTrue(context.check_hostname);self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
        self.assertEqual(set(p.name for p in path.iterdir()),{'tls.json','server.pfx','server.pem','pfx-password.txt'})
        # Release was effective; a new writer can acquire each file without modifying any byte.
        for p in path.iterdir():
            with p.open('r+b'):pass
        public=json.dumps(self.calls,ensure_ascii=False)
        self.assertNotIn((path/'pfx-password.txt').read_text(),public)

    def test_02_existing_overlap_running_and_base_hash(self):
        target=self.home/'existing';target.mkdir();(target/'sentinel').write_bytes(b'preserve')
        args=dict(InstancePath=self.instance,ExpectedInstanceSha256=self.instance_hash,DestinationPath=target)
        self.call('New-RackClickLabHttpsProfile.ps1',args,1,'https_destination_exists')
        self.assertEqual((target/'sentinel').read_bytes(),b'preserve')
        args['DestinationPath']=self.instance/'inside-private'
        self.call('New-RackClickLabHttpsProfile.ps1',args,2,'https_paths_overlap');self.assertFalse(Path(args['DestinationPath']).exists())
        args['DestinationPath']=self.home/'wrong-base';args['ExpectedInstanceSha256']='0'*64
        self.call('New-RackClickLabHttpsProfile.ps1',args,2,'instance_hash_mismatch');self.assertFalse(Path(args['DestinationPath']).exists())
        args['ExpectedInstanceSha256']=self.instance_hash;args['DestinationPath']=self.home/'pid-present'
        pid=self.instance/'pgdata/postmaster.pid';pid.write_text('999999999\n',encoding='ascii')
        try:self.call('New-RackClickLabHttpsProfile.ps1',args,1,'https_instance_postmaster_present')
        finally:pid.unlink()
        self.assertFalse(Path(args['DestinationPath']).exists())

    def test_03_external_hash_corruption_and_identity_binding(self):
        path,data=self.generate('tamper-source')
        self.driver_call('Read',path,'0'*64,2,'https_profile_hash_mismatch')
        corrupt=self.clone_profile(path,'corrupt-pfx');(corrupt/'server.pfx').write_bytes(b'corrupt')
        self.driver_call('Read',corrupt,sha(corrupt/'tls.json'),2,'https_profile_file_hash_mismatch')
        password=self.clone_profile(path,'wrong-password');(password/'pfx-password.txt').write_text('b'*64,encoding='ascii')
        digest=self.rehash_manifest(password)
        self.driver_call('Read',password,digest,2,'https_profile_pfx_invalid')
        binding=self.clone_profile(path,'wrong-binding');manifest=read(binding/'tls.json');manifest['instanceId']=str(uuid.uuid4());write(binding/'tls.json',manifest)
        self.driver_call('Read',binding,sha(binding/'tls.json'),2,'https_profile_manifest_invalid')
        extra=self.clone_profile(path,'extra-file');(extra/'untrusted').write_bytes(b'x')
        self.driver_call('Read',extra,sha(extra/'tls.json'),2,'https_profile_contents_invalid')

    def test_04_private_acl_reparse_and_in_use_fence(self):
        path,data=self.generate('acl-source')
        broad=self.clone_profile(path,'broad-acl')
        grant=subprocess.run(['icacls',str(broad/'server.pfx'),'/grant','*S-1-5-32-545:R'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(grant.returncode,0)
        self.driver_call('Read',broad,sha(broad/'tls.json'),2,'private_acl_required')
        junction=self.home/'junction'
        linked=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(junction),str(path)],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(linked.returncode,0)
        self.driver_call('Read',junction,data['profileSha256'],2,'reparse_rejected')
        # Hold the exact native exclusive instance lock while a child attempts generation.
        holder=self.home/'lock-holder.ps1';marker=self.home/'lock-ready'
        holder.write_bytes(r'''param([string]$Lock,[string]$Marker)
$stream=[IO.File]::Open($Lock,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {[IO.File]::WriteAllText($Marker,'ready');[Console]::In.ReadLine()|Out-Null} finally {$stream.Dispose()}
'''.encode('ascii'))
        process=subprocess.Popen(ps(holder,dict(Lock=self.instance/'instance.lock',Marker=marker)),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline=time.monotonic()+10
            while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.025)
            self.assertTrue(marker.exists())
            target=self.home/'busy-instance'
            self.call('New-RackClickLabHttpsProfile.ps1',dict(InstancePath=self.instance,ExpectedInstanceSha256=self.instance_hash,DestinationPath=target),1,'https_instance_in_use')
            self.assertFalse(target.exists())
        finally:
            process.communicate(b'\n',timeout=10)
        self.assertEqual(process.returncode,0)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--api-probe',action='store_true');parser.add_argument('--case',action='append')
    args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False)
    snapshot=args.evidence/'sources-before';snapshot.mkdir()
    guards={str(p):sha(p) for p in SOURCES}
    for p in SOURCES:
        dest=snapshot/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    started=time.monotonic();report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),python=sys.version.split()[0],sources=guards,scope='TLS sidecar only; synthetic instance files; no PG/app/service/store writes')
    if args.api_probe:
        home=new_private()
        try:
            record=invoke(ps(home/'driver.ps1',dict(Mode='Api',Helper=TOOLS/'RackClick.Https.ps1',PrivateRoot=home/'api-only')),home,0,'framework_api_verified')
            report.update(valid=True,apiProbe=record,privateFixture=str(home))
        except BaseException as error:
            report.update(valid=False,errorType=type(error).__name__,privateFixture=str(home));raise
        finally:
            report.update(seconds=round(time.monotonic()-started,3),inputsUnchanged=all(sha(Path(p))==digest for p,digest in guards.items()));write(args.evidence/'result.json',report)
    else:
        suite=unittest.defaultTestLoader.loadTestsFromNames(args.case,HttpsProfile) if args.case else unittest.defaultTestLoader.loadTestsFromTestCase(HttpsProfile)
        with (args.evidence/'tests.log').open('w',encoding='utf-8') as log:
            result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
        report.update(valid=result.wasSuccessful(),testsRun=result.testsRun,failures=len(result.failures),errors=len(result.errors),calls=getattr(HttpsProfile,'calls',[]),
            inputsUnchanged=getattr(HttpsProfile,'inputs_unchanged',False),storesUnchanged=getattr(HttpsProfile,'stores_unchanged',False),privateFixture=str(getattr(HttpsProfile,'home','')),seconds=round(time.monotonic()-started,3))
        write(args.evidence/'result.json',report)
        print(json.dumps({key:report[key] for key in ('valid','testsRun','failures','errors','seconds')}))
        if not result.wasSuccessful():raise SystemExit(1)


if __name__=='__main__':main()
