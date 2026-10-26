"""Native instance creation/start/stop/backup on fresh Windows fixtures only.

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
import subprocess
import time
import unittest
import uuid

from pg_support import Client, Response, WORKSPACE, free_port, protect_directory, toolchain

ROOT=WORKSPACE;TOOLS=ROOT/'tools/windows'
BASELINE=ROOT/'evidence/s1-20261017/seis-tandas-180-185/CANDIDATA185.json'
BASELINE_SHA='68aca94da20751b690af0c1c6b764a1db1004d3d63be2a12161938a3624d7706'
PS=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
write=lambda p,d:p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
NO_WINDOW=subprocess.CREATE_NO_WINDOW


class NativeServer:
    def __init__(self,origin):
        self.origin=origin;self.port=int(origin.rsplit(':',1)[1])

    def request(self,method,path,body=None,headers=None):
        fields=dict(headers or {})
        if body is not None:
            body=json.dumps(body,ensure_ascii=False).encode('utf-8');fields.setdefault('Content-Type','application/json')
        connection=http.client.HTTPConnection('127.0.0.1',self.port,timeout=15)
        try:
            connection.request(method,path,body=body,headers=fields);r=connection.getresponse()
            return Response(r.status,{k.lower():v for k,v in r.getheaders()},r.read())
        finally:connection.close()


class NativeInstanceFlow(unittest.TestCase):
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
               'RackClick.Process.ps1','RackClick.Process.Gate.ps1','Start-RackClickLabInstance.ps1','Stop-RackClickLabInstance.ps1')
        sources.extend(TOOLS/name for name in names)
        for kind,files in manifest['distributions'].items():
            for name,digest in files.items():
                p=cls.candidate/kind/name;assert sha(p)==digest;sources.append(p)
        cls.guards={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
        cls.home=ROOT/'.local/native-instance-flows'/('flow238-'+uuid.uuid4().hex)
        cls.home.mkdir(parents=True,exist_ok=False);protect_directory(cls.home)
        # initdb17.11 re-emits an absolute path to its child on Windows. Its data
        # root must be ASCII; user names, stage and backup paths remain Unicode.
        cls.instance_path=cls.home/'native-instance';cls.instance_sha=None

    @classmethod
    def tearDownClass(cls):
        for item in cls.launches:
            p=item['process']
            if p.poll() is None:
                # Request the exact native run to stop. No process lookup by name or external PG stop.
                try:
                    args=dict(InstancePath=cls.instance_path,ExpectedInstanceSha256=cls.instance_sha)
                    with (cls.home/('cleanup-'+uuid.uuid4().hex+'.log')).open('xb') as output:
                        subprocess.run(cls.command('Stop-RackClickLabInstance.ps1',args),stdout=output,stderr=output,timeout=20,creationflags=NO_WINDOW)
                    p.wait(timeout=30)
                except Exception:
                    cls.cleanup_errors.append('Native stop did not complete; exact owned launcher terminated as fallback')
                    if p.poll() is None:p.terminate()
                    p.wait(timeout=15)
            item['log'].close();item['errorLog'].close()
        cls.owned_processes_stopped=all(x['process'].poll() is not None for x in cls.launches) and not (cls.instance_path/'pgdata/postmaster.pid').exists()
        cls.inputs_unchanged=all(sha(ROOT/n)==v for n,v in cls.guards.items())
        assert cls.inputs_unchanged and cls.owned_processes_stopped and not cls.cleanup_errors

    @staticmethod
    def command(script,args):
        fields=[]
        for key,value in args.items():
            fields.append('-'+key)
            if value is not True:fields.append(str(value))
        return [str(PS),'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(TOOLS/script),*fields]

    def mark(self,number,**details):self.checkpoints.append(dict(tanda=number,passed=True,**details))

    def invoke(self,script,args,expected=0):
        t=time.monotonic();p=subprocess.run(self.command(script,args),capture_output=True,timeout=180,creationflags=NO_WINDOW)
        try:data=json.loads(p.stdout.decode('utf-8-sig'))
        except (ValueError,UnicodeError):data={'unparsed':True}
        # Export only agreed public fields; unexpected values stay in the private process memory.
        allowed={'schemaVersion','valid','success','exitCode','code','scope','instancePath','instanceId',
                 'instanceManifestSha256','manifestSha256','backupPath','destinationPath','stageId',
                 'receiptSha256','verifiedFiles','runId','event','url','requested','stopRequested','state'}
        safe={k:v for k,v in data.items() if k in allowed}
        self.calls.append(dict(script=script,exitCode=p.returncode,seconds=round(time.monotonic()-t,3),report=safe,stderrEmpty=not p.stderr))
        self.assertFalse(p.stderr,'Native command wrote stderr; no raw output exported')
        self.assertEqual(p.returncode,expected,safe);self.assertEqual(data['exitCode'],expected);self.assertEqual(data['valid'],expected==0)
        return data

    def expect(self,response,status):
        self.assertEqual(response.status,status,'Unexpected HTTP status; no bodies/tokens exported')
        return response

    def start(self,number):
        output_path=self.home/f'launcher-{number}.jsonl';error_path=self.home/f'launcher-{number}-private.log'
        output=output_path.open('xb');error=error_path.open('xb')
        # Deliberate inherited endpoint poison must not change the bound origin.
        environment=dict(os.environ)
        environment['Kestrel__Endpoints__Poison__Url']=f'http://127.0.0.1:{self.poison_port}'
        p=subprocess.Popen(self.command('Start-RackClickLabInstance.ps1',dict(InstancePath=self.instance_path,
              ExpectedInstanceSha256=self.instance_sha,StopAfterSeconds=90)),stdout=output,stderr=error,env=environment,creationflags=NO_WINDOW)
        item=dict(process=p,log=output,errorLog=error,outputPath=output_path,errorPath=error_path);self.launches.append(item)
        deadline=time.monotonic()+65
        while time.monotonic()<deadline:
            events=[]
            for line in output_path.read_bytes().splitlines():
                try:events.append(json.loads(line.decode('utf-8-sig')))
                except (ValueError,UnicodeError):pass
            ready=next((x for x in events if x.get('event')=='ready'),None)
            if ready:
                self.assertEqual(ready['url'],self.origin);item['runId']=ready['runId'];return item
            if p.poll() is not None:break
            time.sleep(.1)
        self.fail('Native launcher did not report ready; private fixture logs retained')

    def stop(self,item):
        data=self.invoke('Stop-RackClickLabInstance.ps1',dict(InstancePath=self.instance_path,ExpectedInstanceSha256=self.instance_sha))
        if 'runId' in data:self.assertEqual(data['runId'],item['runId'])
        self.assertEqual(item['process'].wait(timeout=35),0)
        events=[json.loads(x.decode('utf-8-sig')) for x in item['outputPath'].read_bytes().splitlines()]
        self.assertEqual([x['event'] for x in events],['ready','stopped'])
        self.assertTrue(events[-1]['valid']);self.assertEqual(events[-1]['exitCode'],0)
        self.assertFalse(item['errorPath'].read_bytes())
        self.assertFalse((self.instance_path/'pgdata/postmaster.pid').exists())
        for port in (self.pg_port,self.http_port):
            with socket.socket() as sock:self.assertNotEqual(sock.connect_ex(('127.0.0.1',port)),0)

    def test_native_create_lifecycle_persistence_and_backup(self):
        tools=toolchain();runtime=self.home/'runtime sin SDK Ω';runtime.mkdir()
        original=tools['dotnet'].parent
        shutil.copy2(original/'dotnet.exe',runtime/'dotnet.exe');shutil.copytree(original/'host',runtime/'host')
        for name in ('Microsoft.NETCore.App','Microsoft.AspNetCore.App'):
            shutil.copytree(original/'shared'/name,runtime/'shared'/name)
        sdks=subprocess.run([str(runtime/'dotnet.exe'),'--list-sdks'],capture_output=True,check=True,creationflags=NO_WINDOW)
        self.assertFalse(sdks.stdout.strip() or sdks.stderr.strip())
        stage=self.home/'distribución Ω';pg_bin=tools['postgresql'].parent
        staged=self.invoke('Stage-ServerDistribution.ps1',dict(ManifestPath=BASELINE,ExpectedManifestSha256=BASELINE_SHA,
             ServerPath=self.candidate/'server',FrontendPath=self.candidate/'frontend',DotNetPath=runtime/'dotnet.exe',
             PostgresBinPath=pg_bin,DestinationPath=stage))
        self.mark(238,runtimeWithoutSdk=True,stagedFiles=36)

        self.pg_port=free_port();self.http_port=free_port()
        while self.http_port==self.pg_port:self.http_port=free_port()
        self.poison_port=free_port()
        while self.poison_port in (self.pg_port,self.http_port):self.poison_port=free_port()
        self.origin=f'http://127.0.0.1:{self.http_port}'
        created=self.invoke('New-RackClickLabInstance.ps1',dict(StagePath=stage,ExpectedManifestSha256=BASELINE_SHA,
            ExpectedReceiptSha256=staged['receiptSha256'],DotNetPath=runtime/'dotnet.exe',PostgresBinPath=pg_bin,
            InstancePath=self.instance_path,PostgresPort=self.pg_port,PublicOrigin=self.origin,
            BootstrapUser='Administrador-Ω-😀',SystemhausName='Instancia nativa Ω',DevelopmentLoopbackHttp=True))
        self.__class__.instance_sha=created['instanceManifestSha256']
        self.assertEqual(sha(self.instance_path/'instance.json'),self.instance_sha)
        self.assertFalse((self.instance_path/'pgdata/postmaster.pid').exists())
        self.mark(239,nativeProvisioning=True,pythonCreatedDatabases=False,pythonBootstrap=False)

        meta=read(self.instance_path/'instance.json')
        credentials=read(self.instance_path/'private/admin-login.json')
        private_before={p.relative_to(self.instance_path/'private').as_posix():sha(p) for p in (self.instance_path/'private').rglob('*') if p.is_file()}
        self.assertGreaterEqual(len(private_before),5)
        self.assertGreaterEqual(len(credentials['password']),16)
        self.assertEqual(created['instanceId'],meta['id'])
        self.assertNotEqual(meta['owner'],meta['runtime'])
        for field in ('password','connectionString','runtimeConnectionString'):self.assertNotIn(field,meta)
        self.mark(240,newInstanceIdentity=True,privateCredentials=True,ownerRuntimeDifferent=True)

        run1=self.start(1);server=NativeServer(self.origin)
        with socket.socket() as sock:self.assertNotEqual(sock.connect_ex(('127.0.0.1',self.poison_port)),0)
        self.assertEqual(self.expect(server.request('GET','/health/ready'),200).json(),dict(status='ready',schemaVersion=9))
        self.assertEqual(self.expect(server.request('GET','/'),200).body,(stage/'frontend/index.html').read_bytes())
        first,second=Client(server),Client(server)
        self.expect(first.login(credentials['username'],credentials['password']),200)
        self.expect(second.login(credentials['username'],credentials['password']),200)
        self.mark(241,nativeLauncher=True,readinessSchema=9,guiExact=True,loginFromPrivateCredential=True,inheritedKestrelEndpointIgnored=True)

        house=self.expect(first.request('GET','/api/v1/systemhaus'),200).json()
        self.assertEqual(house['name'],'Instancia nativa Ω')
        changed=self.expect(first.request('PUT','/api/v1/systemhaus',{'name':'Systemhaus renombrado Ω 😀'},
                  {'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),200).json()
        current_house=self.expect(second.request('GET','/api/v1/systemhaus'),200).json()
        self.assertEqual(current_house['name'],'Systemhaus renombrado Ω 😀')
        key=str(uuid.uuid4())
        made=self.expect(first.request('POST','/api/v1/customers',{'name':'Cliente flujo nativo 😀'},
                {'If-Match':f'"{current_house["revision"]}"','Idempotency-Key':key}),201).json()['resource']
        customers=self.expect(second.request('GET','/api/v1/customers'),200).json()
        self.assertTrue(any(x['id']==made['id'] and x['name']==made['name'] for x in customers))
        # Customer creation advances the shared inventory revision. Capture the
        # committed house DTO now so restart is compared with the current state.
        committed_house=self.expect(second.request('GET','/api/v1/systemhaus'),200).json()
        self.assertEqual(committed_house['id'],current_house['id'])
        self.assertEqual(committed_house['name'],current_house['name'])
        self.assertEqual(committed_house['revision'],current_house['revision']+1)
        current_house=committed_house
        audit=self.expect(first.request('GET','/api/v1/admin/audit'),200).json()
        self.assertGreaterEqual(len(audit['events']),2)
        self.mark(242,systemhausLiteral=True,customerCommitConfirmed=True,otherSessionRead=True,auditAvailable=True)

        rejected=self.invoke('Start-RackClickLabInstance.ps1',dict(InstancePath=self.instance_path,
                         ExpectedInstanceSha256=self.instance_sha,StopAfterSeconds=1),expected=1)
        self.assertEqual(rejected['code'],'instance_in_use')
        self.assertEqual(self.expect(second.request('GET','/api/v1/customers'),200).json(),customers)
        self.stop(run1)
        self.mark(243,nativeStopByRunId=True,pgAndAppPortsClosed=True,postmasterPidRemoved=True,concurrentLauncherRejected=True)

        run2=self.start(2);self.assertNotEqual(run1['runId'],run2['runId'])
        self.expect(second.request('GET','/api/v1/me'),200)
        self.assertEqual(self.expect(second.request('GET','/api/v1/customers'),200).json(),customers)
        self.assertEqual(self.expect(second.request('GET','/api/v1/systemhaus'),200).json(),current_house)
        self.mark(244,sameInstanceRestart=True,originalSessionPersists=True,confirmedDataPersists=True)

        backup_dir=self.home/'backup privado Ω'
        backup=self.invoke('New-RackClickDatabaseBackup.ps1',dict(PostgresBinPath=pg_bin,
                  ProfilePath=self.instance_path/'private/backup-profile.json',DestinationPath=backup_dir))
        self.assertEqual(sha(backup_dir/'manifest.json'),backup['manifestSha256'])
        backup_meta=read(backup_dir/'manifest.json')
        self.assertEqual(sha(backup_dir/'data.dump'),backup_meta['dumpSha256'])
        listing=subprocess.run([str(pg_bin/'pg_restore.exe'),'--list','data.dump'],cwd=backup_dir,
                               capture_output=True,timeout=30,creationflags=NO_WINDOW)
        (self.home/'archive-private-list.log').write_bytes(listing.stdout+listing.stderr)
        self.assertEqual(listing.returncode,0)
        archive=listing.stdout.decode('utf-8',errors='replace')
        for table in ('schema_migration','systemhaus','customer','audit_event','app_session'):
            self.assertIn('TABLE DATA public '+table+' ',archive)
        self.mark(245,nativeBackup=True,generatedOwnerProfile=True,archiveHasApplicationTables=True,archiveSha256=backup_meta['dumpSha256'])

        self.assertEqual(self.expect(second.request('GET','/api/v1/customers'),200).json(),customers)
        self.assertEqual(self.expect(first.request('GET','/api/v1/admin/audit'),200).json(),audit)
        self.stop(run2)
        self.assertEqual(sha(self.instance_path/'instance.json'),self.instance_sha)
        private_after={p.relative_to(self.instance_path/'private').as_posix():sha(p) for p in (self.instance_path/'private').rglob('*') if p.is_file()}
        self.assertEqual(private_after,private_before)
        self.mark(246,originPreserved=True,immutablePrivateCredentials=True,instanceManifestUnchanged=True,normalNativeShutdown=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    with (args.evidence/'tests.log').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NativeInstanceFlow))
    c=NativeInstanceFlow
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,
         successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),
         sources=getattr(c,'guards',{}),inputsUnchanged=c.inputs_unchanged,ownedProcessesStopped=c.owned_processes_stopped,
         cleanupErrors=c.cleanup_errors,fixture=str(getattr(c,'home','not initialized')),calls=c.calls,checkpoints=c.checkpoints,
         actualQaAccessed=False,pythonCreatedDatabases=False,pythonBootstrap=False,newApplicationBuilds=0,
         limits='Native lab commands, not SCM/HTTPS/clean Windows/final installer/adoption. No restore or new browser traversal in this flow.')
    write(args.evidence/'result.json',report)
    print(json.dumps({k:report[k] for k in ['testsRun','successful','failures','errors','seconds','inputsUnchanged','ownedProcessesStopped']}))
    return 0 if result.wasSuccessful() and c.inputs_unchanged and c.owned_processes_stopped and not c.cleanup_errors else 1


if __name__=='__main__':raise SystemExit(main())
