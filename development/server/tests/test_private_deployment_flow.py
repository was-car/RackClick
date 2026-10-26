"""Unified private deployment and operations from copied native tools on fresh Windows fixtures.

Python drives tests and HTTP assertions; all PostgreSQL provisioning, bootstrap
and lifecycle operations are performed by the new PowerShell operator commands.
No existing QA profile, database or service is accessed.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import ssl
import subprocess
import time
import unittest
import uuid

from pg_support import Client, Response, WORKSPACE, free_port, protect_directory, toolchain

ROOT=WORKSPACE;TOOLS=ROOT/'tools/windows'
BASELINE=ROOT/'evidence/s1-20261017/treinta-tandas-248-277/CANDIDATA277.json'
BASELINE_SHA='8f47ba4e48781aa010e3f3d8f9c85eae8003eb509336b1f6bf639ceac5a82a25'
PS=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
write=lambda p,d:p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
NO_WINDOW=subprocess.CREATE_NO_WINDOW


class NativeServer:
    def __init__(self,origin,context=None):
        self.origin=origin;self.port=int(origin.rsplit(':',1)[1]);self.context=context

    def request(self,method,path,body=None,headers=None):
        fields=dict(headers or {})
        if body is not None:
            body=json.dumps(body,ensure_ascii=False).encode('utf-8');fields.setdefault('Content-Type','application/json')
        connection=(http.client.HTTPSConnection('127.0.0.1',self.port,timeout=15,context=self.context)
                    if self.origin.startswith('https:') else http.client.HTTPConnection('127.0.0.1',self.port,timeout=15))
        try:
            connection.request(method,path,body=body,headers=fields);r=connection.getresponse()
            return Response(r.status,{k.lower():v for k,v in r.getheaders()},r.read())
        finally:connection.close()


class PrivateDeploymentFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calls=[];cls.checkpoints=[];cls.launches=[];cls.cleanup_errors=[]
        cls.inputs_unchanged=False;cls.owned_processes_stopped=False
        manifest=read(BASELINE);assert sha(BASELINE)==BASELINE_SHA
        cls.candidate=ROOT/manifest['candidateDirectory']
        sources=[Path(__file__),BASELINE,ROOT/'development/server/tests/pg_support.py']
        names=('Stage-ServerDistribution.ps1','Test-StagedDistribution.ps1','RackClick.Stage.ps1',
               'Test-RuntimePrerequisites.ps1','Test-ServerDistribution.ps1','RackClick.Backup.ps1',
               'New-RackClickDatabaseBackup.ps1','RackClick.Instance.ps1','New-RackClickLabInstance.ps1',
               'RackClick.Process.ps1','RackClick.Process.Gate.ps1','Start-RackClickLabInstance.ps1','Stop-RackClickLabInstance.ps1','RackClick.LaunchControl.ps1','RackClick.Https.ps1','New-RackClickLabHttpsProfile.ps1','RackClick.Deployment.ps1','Test-RackClickPrivateDeployment.ps1','New-RackClickPrivateDeployment.ps1','Invoke-RackClickPrivateDeployment.ps1')
        sources.extend(TOOLS/name for name in names)
        for kind,files in manifest['distributions'].items():
            for name,digest in files.items():
                p=cls.candidate/kind/name;assert sha(p)==digest;sources.append(p)
        cls.guards={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
        cls.home=ROOT/'.local/private-deployment-flows'/('flow298-'+uuid.uuid4().hex)
        cls.home.mkdir(parents=True,exist_ok=False);protect_directory(cls.home)
        # initdb17.11 re-emits an absolute path to its child on Windows. Its data
        # root must be ASCII; user names, stage and backup paths remain Unicode.
        cls.deployment_path=cls.home/'deployment';cls.deployment_sha=None
        cls.instance_path=cls.deployment_path/'instance';cls.instance_sha=None
        cls.operator_tools=cls.home/'copied operator Ω';cls.operator_tools.mkdir()
        for name in names:
            target=cls.operator_tools/name;shutil.copy2(TOOLS/name,target)
            assert sha(target)==sha(TOOLS/name)
            cls.guards[target.relative_to(ROOT).as_posix()]=sha(target)
        cls.operator_file_count=len(names)

    @classmethod
    def tearDownClass(cls):
        for item in cls.launches:
            p=item['process']
            if p.poll() is None:
                # Request the exact native run to stop. No process lookup by name or external PG stop.
                try:
                    if item.get('mode')=='native':
                        script='Stop-RackClickLabInstance.ps1';args=dict(InstancePath=cls.instance_path,ExpectedInstanceSha256=cls.instance_sha)
                    else:
                        script='Invoke-RackClickPrivateDeployment.ps1';args=dict(Operation='Stop',DeploymentPath=cls.deployment_path,ExpectedDeploymentSha256=cls.deployment_sha,StopTimeoutSeconds=15)
                    with (cls.home/('cleanup-'+uuid.uuid4().hex+'.log')).open('xb') as output:
                        subprocess.run(cls.command(script,args),stdout=output,stderr=output,timeout=25,creationflags=NO_WINDOW)
                    p.wait(timeout=30)
                except Exception:
                    cls.cleanup_errors.append('Native stop did not complete; exact owned launcher terminated as fallback')
                    if p.poll() is None:p.terminate()
                    p.wait(timeout=15)
            item['log'].close();item['errorLog'].close()
        cls.owned_processes_stopped=all(x['process'].poll() is not None for x in cls.launches) and not (cls.instance_path/'pgdata/postmaster.pid').exists()
        cls.inputs_unchanged=all(sha(ROOT/n)==v for n,v in cls.guards.items())
        assert cls.inputs_unchanged and cls.owned_processes_stopped and not cls.cleanup_errors

    @classmethod
    def command(cls,script,args):
        fields=[]
        for key,value in args.items():
            fields.append('-'+key)
            if value is not True:fields.append(str(value))
        return [str(PS),'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(cls.operator_tools/script),*fields]

    def mark(self,number,**details):self.checkpoints.append(dict(tanda=number,passed=True,**details))

    def invoke(self,script,args,expected=0):
        t=time.monotonic();environment=self.poisoned_environment()
        p=subprocess.run(self.command(script,args),capture_output=True,timeout=300,creationflags=NO_WINDOW,env=environment)
        try:data=json.loads(p.stdout.decode('utf-8-sig'))
        except (ValueError,UnicodeError):data={'unparsed':True}
        # Export only agreed public fields; unexpected values stay in the private process memory.
        allowed={'schemaVersion','valid','success','exitCode','code','scope','instancePath','instanceId',
                 'instanceManifestSha256','manifestSha256','backupPath','destinationPath','stageId',
                 'receiptSha256','verifiedFiles','runId','event','url','requested','stopRequested','state',
                 'profileSha256','certificateSha256','profilePath','deploymentSha256','deploymentPath',
                 'deploymentId','httpsValidated','operation','stopRequested','stopConfirmed','backupManifestSha256','dumpSha256'}
        safe={k:v for k,v in data.items() if k in allowed}
        self.calls.append(dict(script=script,exitCode=p.returncode,seconds=round(time.monotonic()-t,3),report=safe,stderrEmpty=not p.stderr))
        self.assertFalse(p.stderr,'Native command wrote stderr; no raw output exported')
        self.assertEqual(p.returncode,expected,safe);self.assertEqual(data['exitCode'],expected);self.assertEqual(data['valid'],expected==0)
        return data

    def expect(self,response,status):
        self.assertEqual(response.status,status,'Unexpected HTTP status; no bodies/tokens exported')
        return response

    @staticmethod
    def poisoned_environment():
        values=dict(os.environ)
        values.update({'RackClick:ShutdownPipe':'inherited-invalid-pipe','RackClick:ShutdownToken':'inherited-invalid-token',
                       'RackClick__ShutdownToken':'inherited-invalid-token','Bootstrap:User':'inherited-invalid-user',
                       'Bootstrap__User':'inherited-invalid-user','PGHOST':'invalid.example','PG:Alias':'inherited-invalid-alias'})
        return values

    def start(self,number,mode='deployment'):
        output_path=self.home/f'launcher-{number}.jsonl';error_path=self.home/f'launcher-{number}-private.log'
        output=output_path.open('xb');error=error_path.open('xb');environment=self.poisoned_environment()
        environment['Kestrel__Endpoints__Poison__Url']=f'http://127.0.0.1:{self.poison_port}'
        if mode=='deployment':
            script='Invoke-RackClickPrivateDeployment.ps1'
            arguments=dict(Operation='Start',DeploymentPath=self.deployment_path,ExpectedDeploymentSha256=self.deployment_sha,StopAfterSeconds=90)
        else:
            script='Start-RackClickLabInstance.ps1'
            arguments=dict(InstancePath=self.instance_path,ExpectedInstanceSha256=self.instance_sha,StopAfterSeconds=90,GracefulShutdown=True)
        p=subprocess.Popen(self.command(script,arguments),stdout=output,stderr=error,env=environment,creationflags=NO_WINDOW)
        item=dict(process=p,log=output,errorLog=error,outputPath=output_path,errorPath=error_path,mode=mode);self.launches.append(item)
        deadline=time.monotonic()+65
        while time.monotonic()<deadline:
            events=[]
            for line in output_path.read_bytes().splitlines():
                try:events.append(json.loads(line.decode('utf-8-sig')))
                except (ValueError,UnicodeError):pass
            ready=next((x for x in events if x.get('event')=='ready'),None)
            if ready:
                self.assertEqual(ready['url'],self.origin if mode=='deployment' else self.base_origin)
                self.assertTrue(ready['gracefulShutdown']);self.assertEqual(ready['https'],mode=='deployment')
                item['runId']=ready['runId'];return item
            if p.poll() is not None:break
            time.sleep(.1)
        self.fail('Native operation did not report ready; private fixture logs retained')

    def stop(self,item):
        if item['mode']=='native':
            data=self.invoke('Stop-RackClickLabInstance.ps1',dict(InstancePath=self.instance_path,ExpectedInstanceSha256=self.instance_sha))
        else:
            data=self.operate('Stop');self.assertTrue(data['stopConfirmed']);self.assertTrue(data['stopRequested'])
        self.assertEqual(data['runId'],item['runId'])
        self.assertEqual(item['process'].wait(timeout=35),0)
        events=[json.loads(x.decode('utf-8-sig')) for x in item['outputPath'].read_bytes().splitlines()]
        self.assertEqual([x['event'] for x in events],['ready','stopped'])
        final=events[-1];self.assertTrue(final['valid']);self.assertEqual(final['exitCode'],0)
        self.assertTrue(final['postgresCleanStop']);self.assertTrue(final['applicationGracefulExit']);self.assertFalse(final['applicationHttpDrain'])
        item['final']=final;self.assertFalse(item['errorPath'].read_bytes());self.assertFalse((self.instance_path/'pgdata/postmaster.pid').exists())
        for port in (self.pg_port,self.http_port):
            with socket.socket() as sock:self.assertNotEqual(sock.connect_ex(('127.0.0.1',port)),0)

    def operate(self,operation,expected=0,**extra):
        return self.invoke('Invoke-RackClickPrivateDeployment.ps1',dict(Operation=operation,DeploymentPath=self.deployment_path,
                          ExpectedDeploymentSha256=self.deployment_sha,**extra),expected=expected)

    def checked_backup(self,pg_bin,path):
        backup=self.operate('Backup',BackupPath=path)
        self.assertEqual(backup['code'],'deployment_backup_complete');self.assertEqual(sha(path/'manifest.json'),backup['backupManifestSha256'])
        meta=read(path/'manifest.json');self.assertEqual(sha(path/'data.dump'),meta['dumpSha256']);self.assertEqual(meta['dumpSha256'],backup['dumpSha256'])
        listing=subprocess.run([str(pg_bin/'pg_restore.exe'),'--list','data.dump'],cwd=path,capture_output=True,timeout=30,creationflags=NO_WINDOW)
        (self.home/('archive-'+uuid.uuid4().hex+'-private.log')).write_bytes(listing.stdout+listing.stderr)
        self.assertEqual(listing.returncode,0)
        archive=listing.stdout.decode('utf-8',errors='replace')
        for table in ('schema_migration','systemhaus','customer','audit_event','app_session'):self.assertIn('TABLE DATA public '+table+' ',archive)
        return meta['dumpSha256']

    def test_unified_create_https_operations_and_maintenance_backup(self):
        tools=toolchain();runtime=self.home/'runtime sin SDK Ω';runtime.mkdir();original=tools['dotnet'].parent
        shutil.copy2(original/'dotnet.exe',runtime/'dotnet.exe');shutil.copytree(original/'host',runtime/'host')
        for name in ('Microsoft.NETCore.App','Microsoft.AspNetCore.App'):shutil.copytree(original/'shared'/name,runtime/'shared'/name)
        sdks=subprocess.run([str(runtime/'dotnet.exe'),'--list-sdks'],capture_output=True,check=True,creationflags=NO_WINDOW)
        self.assertFalse(sdks.stdout.strip() or sdks.stderr.strip());self.assertEqual(self.operator_file_count,20)
        self.pg_port=free_port();self.http_port=free_port()
        while self.http_port==self.pg_port:self.http_port=free_port()
        self.poison_port=free_port()
        while self.poison_port in (self.pg_port,self.http_port):self.poison_port=free_port()
        self.base_origin=f'http://127.0.0.1:{self.http_port}';self.origin=f'https://127.0.0.1:{self.http_port}';pg_bin=tools['postgresql'].parent
        self.mark(298,copiedOperatorFiles=20,runtimeWithoutSdk=True,applicationBuilds=0)
        creation_args=dict(ManifestPath=BASELINE,ExpectedManifestSha256=BASELINE_SHA,ServerPath=self.candidate/'server',
            FrontendPath=self.candidate/'frontend',DotNetPath=runtime/'dotnet.exe',PostgresBinPath=pg_bin,
            DestinationPath=self.deployment_path,PostgresPort=self.pg_port,HttpPort=self.http_port,
            BootstrapUser='Administrador-Ω-😀',SystemhausName='Instancia unificada Ω')
        created=self.invoke('New-RackClickPrivateDeployment.ps1',creation_args)
        self.__class__.deployment_sha=created['deploymentSha256'];manifest=read(self.deployment_path/'deployment.json')
        self.__class__.instance_sha=manifest['instanceManifestSha256'];self.profile=self.deployment_path/'https'
        self.assertEqual(sha(self.deployment_path/'deployment.json'),self.deployment_sha);self.assertEqual(len(manifest),11)
        self.assertFalse((self.instance_path/'pgdata/postmaster.pid').exists());self.assertEqual(created['url'],self.origin)
        for root in (self.deployment_path,self.instance_path):
            for field in ('password','connectionString','runtimeConnectionString'):self.assertNotIn(field,read(root/('deployment.json' if root==self.deployment_path else 'instance.json')))
        private_before={p.relative_to(self.instance_path/'private').as_posix():sha(p) for p in (self.instance_path/'private').iterdir() if p.is_file()};self.assertEqual(len(private_before),5)
        tls_before={p.name:sha(p) for p in self.profile.iterdir()};self.assertEqual(len(tls_before),4)
        self.mark(299,oneCommandProvisioning=True,nativeOnly=True,receiptPublishedLast=True,privateSecretsNew=True,postgresStoppedAfterCreate=True)
        rejected=self.invoke('New-RackClickPrivateDeployment.ps1',creation_args,expected=1)
        self.assertEqual(rejected['code'],'preflight_destination_exists');self.assertEqual(sha(self.deployment_path/'deployment.json'),self.deployment_sha)
        wrong=self.invoke('Invoke-RackClickPrivateDeployment.ps1',dict(Operation='Start',DeploymentPath=self.deployment_path,
                          ExpectedDeploymentSha256='0'*64,StopAfterSeconds=1),expected=2)
        self.assertEqual(wrong['code'],'deployment_hash_mismatch');self.assertFalse((self.instance_path/'pgdata/postmaster.pid').exists())
        checked=self.invoke('Test-RackClickPrivateDeployment.ps1',dict(DeploymentPath=self.deployment_path,ExpectedDeploymentSha256=self.deployment_sha))
        self.assertTrue(checked['httpsValidated']);self.assertEqual(checked['url'],self.origin)
        self.mark(300,existingDestinationPreserved=True,wrongExternalReceiptRejected=True,fullInspectionPassed=True)
        credentials=read(self.instance_path/'private/admin-login.json');context=ssl.create_default_context(cafile=str(self.profile/'server.pem'))
        self.assertTrue(context.check_hostname);self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
        run1=self.start(1);server=NativeServer(self.origin,context)
        with self.assertRaises(ssl.SSLCertVerificationError):NativeServer(self.origin,ssl.create_default_context()).request('GET','/health/ready')
        self.assertEqual(self.expect(server.request('GET','/health/ready'),200).json(),dict(status='ready',schemaVersion=9))
        self.assertEqual(self.expect(server.request('GET','/'),200).body,(self.deployment_path/'distribution/frontend/index.html').read_bytes())
        with socket.socket() as sock:self.assertNotEqual(sock.connect_ex(('127.0.0.1',self.poison_port)),0)
        first,second=Client(server),Client(server)
        login=self.expect(first.login(credentials['username'],credentials['password']),200);self.assertIn('; secure',login.headers['set-cookie'].lower())
        self.expect(second.login(credentials['username'],credentials['password']),200)
        self.mark(301,receiptDrivenHttpsStart=True,guiExact=True,secureCookie=True,untrustedTlsRejected=True,inheritedConfigurationIgnored=True)
        house=self.expect(first.request('GET','/api/v1/systemhaus'),200).json();self.assertEqual(house['name'],'Instancia unificada Ω')
        self.expect(first.request('PUT','/api/v1/systemhaus',{'name':'Systemhaus unificado Ω 😀'},
                    {'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),200)
        updated=self.expect(second.request('GET','/api/v1/systemhaus'),200).json();self.assertEqual(updated['name'],'Systemhaus unificado Ω 😀')
        customer=self.expect(first.request('POST','/api/v1/customers',{'name':'Cliente unificado 😀'},
                    {'If-Match':f'"{updated["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),201).json()['resource']
        customers=self.expect(second.request('GET','/api/v1/customers'),200).json();self.assertTrue(any(x['id']==customer['id'] for x in customers))
        committed=self.expect(second.request('GET','/api/v1/systemhaus'),200).json();self.assertEqual(committed['revision'],updated['revision']+1)
        audit=self.expect(first.request('GET','/api/v1/admin/audit'),200).json();self.assertGreaterEqual(len(audit['events']),2)
        self.mark(302,twoSessions=True,unicodeWriteCommitted=True,otherSessionRead=True,auditAvailable=True)
        self.stop(run1)
        again=self.operate('Stop');self.assertEqual(again['code'],'deployment_already_stopped');self.assertTrue(again['stopConfirmed']);self.assertFalse(again['stopRequested'])
        self.mark(303,stopConfirmedBeyondRequest=True,exactRunId=True,portsClosed=True,alreadyStoppedIdempotent=True)
        pfx=self.profile/'server.pfx';pfx_bytes=pfx.read_bytes()
        try:
            pfx.write_bytes(b'corrupt-private-fixture')
            denied=self.operate('Start',expected=2,StopAfterSeconds=1);self.assertEqual(denied['code'],'https_profile_file_hash_mismatch')
            self.assertFalse((self.instance_path/'pgdata/postmaster.pid').exists())
            maintained=self.operate('Stop');self.assertTrue(maintained['stopConfirmed']);self.assertEqual(maintained['code'],'deployment_already_stopped')
        finally:pfx.write_bytes(pfx_bytes)
        self.assertEqual(sha(pfx),tls_before['server.pfx'])
        self.mark(304,damagedTlsCannotStart=True,maintenanceStopWithoutTlsKey=True,pfxRestoredExact=True)
        run2=self.start(2);self.expect(second.request('GET','/api/v1/me'),200)
        self.assertEqual(self.expect(second.request('GET','/api/v1/customers'),200).json(),customers)
        self.assertEqual(self.expect(second.request('GET','/api/v1/systemhaus'),200).json(),committed)
        backup_hash=self.checked_backup(pg_bin,self.home/'backup unificado Ω')
        self.assertEqual(self.expect(second.request('GET','/api/v1/customers'),200).json(),customers)
        self.assertEqual(self.expect(first.request('GET','/api/v1/admin/audit'),200).json(),audit);self.stop(run2)
        self.mark(305,restartSameInstance=True,sessionAndDataPersist=True,receiptDrivenBackup=True,archiveSha256=backup_hash)
        # An explicit old HTTP native run owns PG without locking/using the TLS files.
        # The deployment Stop refuses that unexpected origin; native Stop remains its owner.
        legacy=self.start(3,mode='native');clear=NativeServer(self.base_origin)
        self.assertEqual(self.expect(clear.request('GET','/health/ready'),200).json(),dict(status='ready',schemaVersion=9))
        try:
            pfx.write_bytes(b'corrupt-private-fixture')
            wrong_origin=self.operate('Stop',expected=2);self.assertEqual(wrong_origin['code'],'deployment_run_record_invalid');self.assertFalse(wrong_origin['stopRequested'])
            self.assertFalse((self.instance_path/'logs'/('launcher-'+legacy['runId'])/'stop-request.json').exists())
            maintained_hash=self.checked_backup(pg_bin,self.home/'backup maintenance Ω')
            self.assertEqual(self.expect(clear.request('GET','/health/ready'),200).status,200)
            self.stop(legacy)
        finally:pfx.write_bytes(pfx_bytes)
        self.mark(306,backupWithDamagedTlsAndRealPg=True,maintenanceArchiveSha256=maintained_hash,unexpectedOriginNotStopped=True,nativeOwnedCleanup=True)
        self.assertEqual(sha(self.deployment_path/'deployment.json'),self.deployment_sha);self.assertEqual(sha(self.instance_path/'instance.json'),self.instance_sha)
        self.assertEqual({p.name:sha(p) for p in self.profile.iterdir()},tls_before)
        self.assertEqual({p.name:sha(p) for p in (self.instance_path/'private').iterdir()},private_before)
        self.mark(307,receiptInstanceAndSecretsUnchanged=True,profileUnchanged=True,allOwnedPortsClosed=True,httpDrainAttested=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    with (args.evidence/'tests.log').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PrivateDeploymentFlow))
    c=PrivateDeploymentFlow
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,
         successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),
         sources=getattr(c,'guards',{}),inputsUnchanged=c.inputs_unchanged,ownedProcessesStopped=c.owned_processes_stopped,
         cleanupErrors=c.cleanup_errors,fixture=str(getattr(c,'home','not initialized')),calls=c.calls,checkpoints=c.checkpoints,
         actualQaAccessed=False,pythonCreatedDatabases=False,pythonBootstrap=False,newApplicationBuilds=0,copiedOperatorFiles=getattr(c,'operator_file_count',0),
         limits='Unified private local deployment/operation from copied native commands with external runtimes. No SCM, clean Windows, runtime installer, production PKI, complete recovery, browser QA or adoption. Maintenance backup with damaged TLS uses explicit old HTTP native fixture; no universal HTTP-drain attestation.')
    write(args.evidence/'result.json',report)
    print(json.dumps({k:report[k] for k in ['testsRun','successful','failures','errors','seconds','inputsUnchanged','ownedProcessesStopped']}))
    return 0 if result.wasSuccessful() and c.inputs_unchanged and c.owned_processes_stopped and not c.cleanup_errors else 1


if __name__=='__main__':raise SystemExit(main())
