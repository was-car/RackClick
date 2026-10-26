"""Fresh Windows installation from a transported offline ZIP, without dev dependencies.

Python only drives assertions/HTTP. Native bundled operators own provisioning,
bootstrap, lifecycle, backup and recovery. Never access actual QA or existing DBs.
"""
import argparse
from datetime import datetime,timezone
import hashlib,json,os,platform,secrets,shutil,ssl,subprocess,time,unittest,uuid,zipfile
from pathlib import Path
from pg_support import Client,WORKSPACE,protect_directory,free_port
from test_private_deployment_flow import PrivateDeploymentFlow,NativeServer,PS,NO_WINDOW
from test_private_deployment_recovery import NAMES as PREVIOUS_OPERATORS

ROOT=WORKSPACE;TOOLS=ROOT/'tools/windows';ARCHIVE=None;ARCHIVE_SHA=None
NAMES=PREVIOUS_OPERATORS+('RackClick.OfflineBundle.ps1','Test-RackClickOfflineBundle.ps1','Install-RackClickOfflineBundle.ps1')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
write=lambda p,d:p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))


def system_crt_snapshot():
    import winreg
    system=Path(os.environ['SystemRoot'])/'System32'
    value={'dlls':{n:sha(system/n) for n in ('vcruntime140.dll','msvcp140.dll')},'registry':{}}
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
                       access=winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
        for name in ('Installed','Major','Minor','Bld','Rbld','Version'):
            try:value['registry'][name]=winreg.QueryValueEx(key,name)
            except FileNotFoundError:value['registry'][name]=None
    return value


class OfflineInstallation(PrivateDeploymentFlow):
    test_unified_create_https_operations_and_maintenance_backup=None

    @classmethod
    def setUpClass(cls):
        cls.calls=[];cls.checkpoints=[];cls.launches=[];cls.contexts=[];cls.cleanup_errors=[]
        cls.inputs_unchanged=False;cls.owned_processes_stopped=False
        cls.system_crt_unchanged=False;cls.crt_before=system_crt_snapshot()
        assert ARCHIVE.is_file() and sha(ARCHIVE)==ARCHIVE_SHA
        cls.home=ROOT/'.local/offline-installation-tests'/('offline358-'+uuid.uuid4().hex)
        cls.home.mkdir(parents=True,exist_ok=False);protect_directory(cls.home)
        cls.operator_tools=cls.home/'bootstrap copiado Ω';cls.operator_tools.mkdir()
        sources=[Path(__file__),ROOT/'development/server/tests/pg_support.py',
                 ROOT/'development/server/tests/test_private_deployment_flow.py',
                 ROOT/'development/server/tests/test_private_deployment_recovery.py']+[TOOLS/n for n in NAMES]
        cls.guards={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
        for n in NAMES:
            p=cls.operator_tools/n;shutil.copy2(TOOLS/n,p);cls.guards[p.relative_to(ROOT).as_posix()]=sha(p)
        cls.bootstrap_tools=cls.operator_tools;cls.operator_file_count=len(NAMES)
        incoming=cls.home/'paquete trasladado Ω';incoming.mkdir()
        cls.archive=incoming/'RackClick offline Ω.zip';shutil.copy2(ARCHIVE,cls.archive)
        assert sha(cls.archive)==ARCHIVE_SHA
        cls.guards[cls.archive.relative_to(ROOT).as_posix()]=ARCHIVE_SHA
        with zipfile.ZipFile(cls.archive) as z:
            cls.bundle=json.loads(z.read('bundle.json'));cls.bundle_manifest_sha=hashlib.sha256(z.read('bundle.json')).hexdigest()
            for n in NAMES:
                assert hashlib.sha256(z.read('operators/'+n)).hexdigest()==sha(TOOLS/n)
        cls.installation_root=cls.home/'installed';cls.poison_port=free_port()

    @classmethod
    def tearDownClass(cls):
        for item in cls.launches:
            process=item['process']
            if process.poll() is None:
                try:
                    args=dict(Operation='Stop',DeploymentPath=item['deploymentPath'],ExpectedDeploymentSha256=item['deploymentSha'],StopTimeoutSeconds=15)
                    with (cls.home/('cleanup-'+uuid.uuid4().hex+'.log')).open('xb') as out:
                        subprocess.run(cls.command('Invoke-RackClickPrivateDeployment.ps1',args),stdout=out,stderr=out,
                                       timeout=30,creationflags=NO_WINDOW,env=cls.poisoned_environment())
                    process.wait(timeout=35)
                except Exception:
                    cls.cleanup_errors.append('Owned launcher required exact-process fallback termination')
                    if process.poll() is None:process.terminate()
                    process.wait(timeout=15)
            item['log'].close();item['errorLog'].close()
        cls.inputs_unchanged=all(sha(ROOT/n)==v for n,v in cls.guards.items())
        cls.owned_processes_stopped=all(x['process'].poll() is not None for x in cls.launches) and all(
            not (c['root']/'instance/pgdata/postmaster.pid').exists() for c in cls.contexts)
        cls.system_crt_unchanged=cls.crt_before==system_crt_snapshot()
        assert cls.inputs_unchanged and cls.owned_processes_stopped and cls.system_crt_unchanged and not cls.cleanup_errors

    @staticmethod
    def poisoned_environment():
        # PS7's module path breaks native PS5's Security autoload. Scope this repair
        # to child env only. Tool PATH deliberately contains no .local SDK/PG/Git.
        values={k:v for k,v in os.environ.items() if k.upper()!='PSMODULEPATH'}
        windows=Path(os.environ['SystemRoot'])
        values['PATH']=';'.join(str(windows/p) for p in ('System32','.','System32/Wbem','System32/WindowsPowerShell/v1.0'))
        values.update({'Bootstrap__User':'inherited-invalid-user','Bootstrap:User':'inherited-invalid-user',
                       'PGHOST':'invalid.example','RackClick__ShutdownToken':'inherited-invalid-token',
                       'DOTNET_ROOT':str(ROOT/'.local/nonexistent-toolchain'),
                       'DOTNET_ROOT_X64':str(ROOT/'.local/nonexistent-toolchain')})
        return values

    def invoke(self,script,args,expected=0):
        t=time.monotonic();p=subprocess.run(self.command(script,args),capture_output=True,timeout=420,
            creationflags=NO_WINDOW,env=self.poisoned_environment())
        # Full logs remain only in the ACL-protected fixture. Public report is allowlisted.
        (self.home/('command-'+uuid.uuid4().hex+'-private.log')).write_bytes(p.stdout+p.stderr)
        try:data=json.loads(p.stdout.decode('utf-8-sig'))
        except(ValueError,UnicodeError):data={}
        allowed={'schemaVersion','valid','exitCode','code','bundleId','bundleArchiveSha256','bundleManifestSha256',
          'applicationManifestSha256','versions','counts','verifiedFiles','uncompressedBytes',
          'installationPath','installationId','installationSha256','deploymentPath','deploymentId','deploymentSha256',
          'publicOrigin','crtDecision','rebootRequired','instanceId','url','httpsValidated',
          'backupManifestSha256','dumpSha256','stopConfirmed','stopRequested','runId','state','operation','sourceBackupManifestSha256'}
        safe={k:v for k,v in data.items() if k in allowed}
        self.calls.append(dict(script=script,operatorRoot=str(self.operator_tools),seconds=round(time.monotonic()-t,3),
                               exitCode=p.returncode,report=safe,stderrEmpty=not p.stderr))
        self.assertFalse(p.stderr,'Native stderr retained privately')
        self.assertEqual(p.returncode,expected,safe);self.assertEqual(data.get('exitCode'),expected,safe)
        self.assertEqual(data.get('valid'),expected==0,safe)
        return data

    def context(self,root):
        pg,http=free_port(),free_port()
        while http==pg:http=free_port()
        c=dict(root=root,pg=pg,http=http);self.contexts.append(c);return c

    def activate(self,c,result=None):
        if result:
            c['sha']=result['deploymentSha256'];m=read(c['root']/'deployment.json')
            c['instanceSha']=m['instanceManifestSha256']
            self.assertEqual(sha(c['root']/'deployment.json'),c['sha'])
            self.assertEqual(sha(c['root']/'instance/instance.json'),c['instanceSha'])
        for n,v in dict(deployment_path=c['root'],deployment_sha=c['sha'],instance_path=c['root']/'instance',
            instance_sha=c['instanceSha'],pg_port=c['pg'],http_port=c['http'],origin=f'https://127.0.0.1:{c["http"]}',
            base_origin=f'http://127.0.0.1:{c["http"]}').items():setattr(self,n,v);setattr(type(self),n,v)

    def start(self,number,mode='deployment'):
        count=len(self.launches)
        try:return super().start(number,mode)
        finally:
            # Even readiness failure must leave exact cleanup identity on the new item.
            for item in self.launches[count:]:
                item.update(deploymentPath=self.deployment_path,deploymentSha=self.deployment_sha)

    def install_args(self,c,**changes):
        result=dict(ArchivePath=self.archive,ExpectedArchiveSha256=ARCHIVE_SHA,DestinationPath=self.installation_root,
                    PostgresPort=c['pg'],HttpPort=c['http'],BootstrapUser='Administrador Ω 😀',SystemhausName='Paquete completo Ω')
        result.update(changes);return result

    def assert_content(self):
        content=self.installation_root/'content'
        expected=self.bundle['files'];actual={p.relative_to(content).as_posix() for p in content.rglob('*') if p.is_file()}
        self.assertEqual(actual,set(expected)|{'bundle.json'})
        self.assertEqual(sha(content/'bundle.json'),self.bundle_manifest_sha)
        for name,item in expected.items():
            p=content/name;self.assertEqual(p.stat().st_size,item['bytes']);self.assertEqual(sha(p),item['sha256'])

    def test_transported_package_install_restart_backup_restore(self):
        inspected=self.invoke('Test-RackClickOfflineBundle.ps1',dict(ArchivePath=self.archive,ExpectedArchiveSha256=ARCHIVE_SHA))
        self.assertEqual(inspected['code'],'bundle_verified');self.assertEqual(inspected['bundleManifestSha256'],self.bundle_manifest_sha)
        source=self.context(self.installation_root/'deployment')
        self.mark(358,transportedZipUnicodePath=True,externalArchiveSha256=ARCHIVE_SHA,bootstrapOperators=25,builds=0)
        denied=self.home/'bad-hash';self.invoke('Install-RackClickOfflineBundle.ps1',
            self.install_args(source,ExpectedArchiveSha256='0'*64,DestinationPath=denied),2)
        self.assertFalse(denied.exists())
        sentinel=self.home/'existing';sentinel.mkdir();(sentinel/'keep.txt').write_bytes(b'preserved')
        self.invoke('Install-RackClickOfflineBundle.ps1',self.install_args(source,DestinationPath=sentinel),1)
        self.assertEqual(list(sentinel.iterdir()),[sentinel/'keep.txt']);self.assertEqual((sentinel/'keep.txt').read_bytes(),b'preserved')
        self.mark(359,wrongExternalHashRejectedBeforeCreate=True,existingDestinationUnchanged=True)
        installed=self.invoke('Install-RackClickOfflineBundle.ps1',self.install_args(source))
        self.assertEqual(installed['code'],'installation_prepared');self.assertFalse(installed['rebootRequired'])
        receipt=read(self.installation_root/'installation.json');state=read(self.installation_root/'installation-state.json')
        self.assertEqual(len(receipt),11);self.assertEqual(len(state),4)
        self.assertEqual(state,dict(schemaVersion=1,installationId=receipt['id'],status='prepared',code='installation_prepared'))
        self.assertEqual(receipt['bundleArchiveSha256'],ARCHIVE_SHA);self.assertEqual(receipt['bundleManifestSha256'],self.bundle_manifest_sha)
        self.assertEqual(sha(self.installation_root/'installation.json'),installed['installationSha256'])
        self.assertEqual(receipt['deploymentSha256'],installed['deploymentSha256'])
        self.assertEqual(set(p.name for p in self.installation_root.iterdir()),{'content','deployment','logs','installation-state.json','installation.json'})
        self.activate(source,installed);self.assert_content()
        self.assertFalse((self.instance_path/'pgdata/postmaster.pid').exists())
        content=self.installation_root/'content';self.operator_tools=content/'operators';type(self).operator_tools=self.operator_tools
        self.runtime=content/'dependencies/dotnet';self.pg_bin=content/'dependencies/postgresql/bin'
        p=subprocess.run([str(self.runtime/'dotnet.exe'),'--list-sdks'],capture_output=True,check=True,creationflags=NO_WINDOW,env=self.poisoned_environment())
        self.assertFalse(p.stdout.strip() or p.stderr.strip());self.assertFalse((self.runtime/'sdk').exists())
        self.assertFalse((content/'dependencies/postgresql/pgAdmin 4').exists())
        self.invoke('Test-RackClickPrivateDeployment.ps1',dict(DeploymentPath=self.deployment_path,ExpectedDeploymentSha256=self.deployment_sha))
        deployment=read(self.deployment_path/'deployment.json');instance=read(self.instance_path/'instance.json')
        self.assertEqual(Path(deployment['rootPath']),self.deployment_path)
        self.assertEqual(Path(instance['dotnetPath']),self.runtime/'dotnet.exe')
        self.assertEqual(Path(instance['postgresBinPath']),self.pg_bin)
        self.mark(360,installedOnlyPaths=True,pgStoppedAfterPrepare=True,runtimeWithoutSdk=True,contentHashesExact=True,
            freshPrivateDeployment=True,crtDecision=installed['crtDecision'],realElevatedCrtInstallerExecuted=False)
        credentials=read(self.instance_path/'private/admin-login.json');private_before={p.name:sha(p) for p in (self.instance_path/'private').iterdir()}
        tls_before={p.name:sha(p) for p in (self.deployment_path/'https').iterdir()}
        run=self.start(1);server=NativeServer(self.origin,ssl.create_default_context(cafile=str(self.deployment_path/'https/server.pem')))
        self.assertEqual(self.expect(server.request('GET','/'),200).body,(content/'application/frontend/index.html').read_bytes())
        self.assertEqual(self.expect(server.request('GET','/health/ready'),200).json(),dict(status='ready',schemaVersion=9))
        with self.assertRaises(ssl.SSLCertVerificationError):NativeServer(self.origin,ssl.create_default_context()).request('GET','/health/ready')
        first,second=Client(server),Client(server)
        login=self.expect(first.login(credentials['username'],credentials['password']),200)
        self.assertIn('; secure',login.headers['set-cookie'].lower());self.expect(second.login(credentials['username'],credentials['password']),200)
        self.mark(361,httpsReadiness=True,guiExactPackaged=True,
            guiBundleSha256=sha(content/'application/frontend/app.js'),
            applicationManifestSha256=self.bundle['applicationManifestSha256'],
            unicodeLoginSecureCookie=True,untrustedTlsRejected=True)
        house=self.expect(first.request('GET','/api/v1/systemhaus'),200).json()
        self.expect(first.request('PUT','/api/v1/systemhaus',{'name':'Paquete instalado persistente Ω 😀'},
                    {'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),200)
        house=self.expect(second.request('GET','/api/v1/systemhaus'),200).json();self.assertEqual(house['name'],'Paquete instalado persistente Ω 😀')
        customer=self.expect(first.request('POST','/api/v1/customers',{'name':'Cliente desde ZIP Ω 😀'},
                    {'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),201).json()['resource']
        customers=self.expect(second.request('GET','/api/v1/customers'),200).json();self.assertTrue(any(c['id']==customer['id'] for c in customers))
        self.mark(362,serverCommittedUnicode=True,otherSessionReads=True)
        house=self.expect(first.request('GET','/api/v1/systemhaus'),200).json();actor=self.expect(first.request('GET','/api/v1/me'),200).json()['user']['id']
        reader_password=secrets.token_hex(32)
        self.expect(first.request('POST','/api/v1/admin/users',{'username':'Lectura paquete Ω','password':reader_password},
                    {'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor}),201)
        restricted=Client(server);self.expect(restricted.login('Lectura paquete Ω',reader_password),200)
        self.expect(restricted.request('GET','/api/v1/admin/users'),403)
        self.expect(restricted.request('GET','/api/v1/customers/'+customer['id']+'/project'),404)
        audit=self.expect(first.request('GET','/api/v1/admin/audit'),200).json();self.assertGreaterEqual(len(audit['events']),3)
        committed=self.expect(second.request('GET','/api/v1/systemhaus'),200).json()
        self.mark(363,authorizationOnServer=True,unprivilegedAccountDenied=True,auditPersisted=True)
        self.stop(run);run2=self.start(2)
        self.expect(second.request('GET','/api/v1/me'),200)
        self.assertEqual(self.expect(second.request('GET','/api/v1/systemhaus'),200).json(),committed)
        self.assertEqual(self.expect(second.request('GET','/api/v1/customers'),200).json(),customers)
        self.assertEqual(self.expect(first.request('GET','/api/v1/admin/audit'),200).json(),audit)
        backup=self.home/'backup instalado Ω';self.checked_backup(self.pg_bin,backup);self.stop(run2)
        self.mark(364,confirmedStopRestart=True,sessionDataAuditPersisted=True,bundledPgDumpAndRestoreList=True)
        recovered=self.context(self.home/'recovered')
        args=dict(ManifestPath=content/'application/manifest.json',ExpectedManifestSha256=self.bundle['applicationManifestSha256'],
            ServerPath=content/'application/server',FrontendPath=content/'application/frontend',DotNetPath=self.runtime/'dotnet.exe',PostgresBinPath=self.pg_bin,
            DestinationPath=recovered['root'],PostgresPort=recovered['pg'],HttpPort=recovered['http'],
            BackupPath=backup,ExpectedBackupManifestSha256=sha(backup/'manifest.json'),RecoveryUser='Recuperación paquete Ω')
        restored=self.invoke('Restore-RackClickPrivateDeployment.ps1',args);self.activate(recovered,restored)
        run3=self.start(3);restored_server=NativeServer(self.origin,ssl.create_default_context(cafile=str(self.deployment_path/'https/server.pem')))
        old_cookie=Client(restored_server);old_cookie.cookie=second.cookie;self.expect(old_cookie.request('GET','/api/v1/me'),401)
        new_credentials=read(self.instance_path/'private/admin-login.json');new_admin=Client(restored_server)
        self.expect(new_admin.login(new_credentials['username'],new_credentials['password']),200)
        self.assertFalse(new_credentials['password']==credentials['password'],'Recovery must generate a fresh credential')
        self.assertEqual(self.expect(new_admin.request('GET','/api/v1/customers'),200).json(),customers)
        self.assertEqual(self.expect(new_admin.request('GET','/api/v1/systemhaus'),200).json()['name'],committed['name'])
        original=Client(restored_server);self.expect(original.login(credentials['username'],credentials['password']),200)
        self.stop(run3);self.assert_content()
        self.mark(365,bundledPgRestoreIntoNewCluster=True,newAdminAndTls=True,copiedSessionRevoked=True,originalDataAndAccountPreserved=True)
        self.activate(source)
        self.assertEqual({p.name:sha(p) for p in (self.instance_path/'private').iterdir()},private_before)
        self.assertEqual({p.name:sha(p) for p in (self.deployment_path/'https').iterdir()},tls_before)
        self.assertEqual(sha(self.installation_root/'installation.json'),installed['installationSha256'])


def main():
    global ARCHIVE,ARCHIVE_SHA
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--archive-sha',required=True);p.add_argument('--evidence',type=Path,required=True)
    a=p.parse_args();ARCHIVE=a.archive.resolve();ARCHIVE_SHA=a.archive_sha
    a.evidence.mkdir(parents=True,exist_ok=False);t=time.monotonic()
    with (a.evidence/'tests.log').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OfflineInstallation))
    c=OfflineInstallation
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,
      successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-t,3),
      sources=getattr(c,'guards',{}),inputsUnchanged=c.inputs_unchanged,ownedProcessesStopped=c.owned_processes_stopped,
      cleanupErrors=c.cleanup_errors,fixture=str(getattr(c,'home','not initialized')),calls=c.calls,checkpoints=c.checkpoints,
      archiveSha256=ARCHIVE_SHA,actualQaAccessed=False,pythonProvisioning=False,pythonRestore=False,
      newApplicationBuilds=0,newFrontendBuilds=0,operatorFiles=25,realElevatedCrtInstallerExecuted=False,
      freshClustersInitialized=sum((v['root']/'instance/pgdata/PG_VERSION').is_file() for v in getattr(c,'contexts',[])),
      systemCrtDllsAndX64RegistryUnchanged=getattr(c,'system_crt_unchanged',False),
      limits='Local private offline package with already-compatible system CRT. Native Windows5.1/PG17; two fresh clusters, bundled runtime without SDK and no developer dependencies on PATH. No SCM, other/clean Windows, actual elevated CRT installation, productive PKI, redistribution clearance, browser QA or adoption.')
    write(a.evidence/'result.json',report)
    print(json.dumps({k:report[k] for k in ['testsRun','successful','failures','errors','seconds','inputsUnchanged','ownedProcessesStopped']}))
    return 0 if result.wasSuccessful() and c.inputs_unchanged and c.owned_processes_stopped and c.system_crt_unchanged and not c.cleanup_errors else 1


if __name__=='__main__':raise SystemExit(main())
