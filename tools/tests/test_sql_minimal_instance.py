"""Protocol3 real New/Restore/backup in new clusters, no service or VM changes."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'development/server/tests'))
from pg_support import free_port,protect_directory
PS=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
TOOLS=ROOT/'tools/windows'
PROBE=ROOT/'tools/tests/sql_secrets/Invoke-MinimalSqlInstanceProbe.ps1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())


class MinimalSql(unittest.TestCase):
    @classmethod
    def call(cls,label,script,args,success=True,code=None):
        cmd=[str(PS),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script)]
        for key,value in args.items():
            if isinstance(value,bool):
                if value:cmd.append('-'+key)
            else:cmd.extend(['-'+key,str(value)])
        p=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
        (cls.work/(label+'.out')).write_bytes(p.stdout);(cls.work/(label+'.err')).write_bytes(p.stderr)
        if p.stderr:raise AssertionError(label+': private stderr retained')
        result=json.loads(p.stdout.decode('utf-8-sig'))
        assert (p.returncode==0)==success,(label,result)
        assert result['valid']==success,(label,result)
        if code:assert result['code']==code,(label,result)
        cls.calls.append(dict(label=label,code=result['code'],exit=p.returncode))
        return result

    @classmethod
    def setUpClass(cls):
        cls.work=ROOT/'.local/sql-minimal-labs'/('minimal-'+uuid.uuid4().hex)
        cls.work.mkdir(parents=True,exist_ok=False);protect_directory(cls.work);cls.calls=[]
        profile=read(ROOT/'docs/DISTRIBUCION43-SQL-PERFIL.json')
        application=ROOT/'.local/sql-integracion-12/distribution';manifest=application/'manifest.json'
        cls.manifest_hash=sha(manifest)
        # The verifier has its own closed digest; a rebuilt arbitrary manifest is not accepted.
        cls.pg=ROOT/'.local/postgresql-17.11-4/pgsql/bin';cls.dotnet=ROOT/'.local/dotnet-10.0.401/dotnet.exe'
        stage=cls.work/'stage'
        staged=cls.call('stage',TOOLS/'Stage-ServerDistribution.ps1',dict(ManifestPath=manifest,
            ExpectedManifestSha256=cls.manifest_hash,ServerPath=application/'server',FrontendPath=application/'frontend',
            DotNetPath=cls.dotnet,PostgresBinPath=cls.pg,DestinationPath=stage))
        cls.common=dict(StagePath=stage,ExpectedManifestSha256=cls.manifest_hash,ExpectedReceiptSha256=staged['receiptSha256'],
            DotNetPath=cls.dotnet,PostgresBinPath=cls.pg,DevelopmentLoopbackHttp=True,ProtectSqlCredentials=True,MinimizeSqlSecrets=True)
        cls.source=cls.work/'source';cls.target=cls.work/'target'
        src=cls.call('new',TOOLS/'New-RackClickLabInstance.ps1',dict(cls.common,InstancePath=cls.source,
            PostgresPort=free_port(),PublicOrigin='http://127.0.0.1:'+str(free_port()),BootstrapUser='minimal-source',SystemhausName='Synthetic minimal SQL'))
        cls.source_hash=src['instanceManifestSha256']
        cls.call('seed',PROBE,dict(InstancePath=cls.source,ExpectedInstanceSha256=cls.source_hash,Mode='Seed'))
        cls.backup=cls.work/'export'
        backup=cls.call('backup',PROBE,dict(InstancePath=cls.source,ExpectedInstanceSha256=cls.source_hash,Mode='Backup',BackupDestination=cls.backup))
        cls.target_args=dict(cls.common,InstancePath=cls.target,PostgresPort=free_port(),PublicOrigin='http://127.0.0.1:'+str(free_port()),
            RecoveryUser='minimal-recovered',BackupPath=cls.backup,ExpectedBackupManifestSha256=backup['backupManifestSha256'])
        dst=cls.call('restore',TOOLS/'New-RackClickRecoveredInstance.ps1',cls.target_args)
        cls.target_hash=dst['instanceManifestSha256']
        cls.guards={str(p):sha(p) for p in [PROBE,TOOLS/'RackClick.Instance.ps1',TOOLS/'New-RackClickLabInstance.ps1',TOOLS/'New-RackClickRecoveredInstance.ps1',TOOLS/'RackClick.Process.ps1',TOOLS/'RackClick.Process.Gate.ps1']}

    def test_01_fresh_roles_and_no_privileged_material(self):
        a,b=read(self.source/'instance.json'),read(self.target/'instance.json')
        for key in ['id','owner','clusterAdmin','runtime','database','backupRole']:self.assertNotEqual(a[key],b[key])
        for root in [self.source,self.target]:
            m=read(root/'instance.json');self.assertEqual(m['schemaVersion'],3)
            self.assertEqual(sorted(p.name for p in (root/'private').iterdir()),['admin-login.json','backup-password.dpapi.json','backup-profile.json','runtime.json'])
            self.assertEqual(read(root/'private/backup-profile.json')['user'],m['backupRole'])
            for p in (root/'logs').rglob('request.json'):self.assertNotEqual(read(p)['schemaVersion'],2)

    def test_02_two_resumes_and_backup_after_restore(self):
        for i in range(2):
            result=self.call('resume-'+str(i),PROBE,dict(InstancePath=self.target,ExpectedInstanceSha256=self.target_hash,Mode='Resume'))
            self.assertTrue(result['runtimeDdlDenied'] and result['backupWriteDenied']);self.assertEqual(result['rows'],20)
        self.call('backup-restored',PROBE,dict(InstancePath=self.target,ExpectedInstanceSha256=self.target_hash,Mode='Backup',BackupDestination=self.work/'export-restored'))

    def test_03_backup_secret_other_context_rejected(self):
        secret=self.target/'private/backup-password.dpapi.json';manifest=self.target/'instance.json'
        old,old_m=secret.read_bytes(),manifest.read_bytes()
        try:
            secret.write_bytes((self.source/'private/backup-password.dpapi.json').read_bytes())
            m=read(manifest);m['secretFiles'][secret.name]=sha(secret);manifest.write_text(json.dumps(m),encoding='utf-8')
            failure=self.call('wrong-backup-context',PROBE,dict(InstancePath=self.target,ExpectedInstanceSha256=sha(manifest)),False,'sql_operator_unprotect_failed')
            self.assertFalse(failure['postgresStarted'])
        finally:secret.write_bytes(old);manifest.write_bytes(old_m)

    def test_04_missing_runtime_and_existing_destination(self):
        m=read(self.target/'instance.json');file=self.target/'sql-security'/m['id']/'sql-secrets/runtime.bin';held=file.with_suffix('.own-held')
        file.rename(held)
        try:
            result=self.call('missing-runtime',PROBE,dict(InstancePath=self.target,ExpectedInstanceSha256=self.target_hash),False,'instance_sql_ciphertext_missing');self.assertFalse(result['postgresStarted'])
        finally:held.rename(file)
        self.call('existing',TOOLS/'New-RackClickRecoveredInstance.ps1',self.target_args,False,'preflight_instance_destination_exists')

    @classmethod
    def tearDownClass(cls):
        assert all(sha(Path(p))==h for p,h in cls.guards.items())
        for root in [cls.source,cls.target]:
            assert not(root/'pgdata/postmaster.pid').exists()
            m=read(root/'instance.json')
            for port in [m['postgresPort'],m['httpPort']]:
                with socket.socket() as s:assert s.connect_ex(('127.0.0.1',port))!=0


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',required=True,type=Path);args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=True)
    started=time.monotonic();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MinimalSql))
    data=dict(successful=result.wasSuccessful(),testsRun=result.testsRun,errors=len(result.errors),failures=len(result.failures),seconds=round(time.monotonic()-started,3),sameWindowsPrincipal=True,vmOperations=0,sourceHashes=getattr(MinimalSql,'guards',{}),calls=getattr(MinimalSql,'calls',[]))
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:data[k] for k in ['successful','testsRun','errors','failures','seconds']}));raise SystemExit(0 if result.wasSuccessful() else 1)
