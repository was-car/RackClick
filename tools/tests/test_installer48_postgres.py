"""Fresh NEW48 via real native operators, no services, existing DB or VM."""
import json,hashlib,subprocess,sys,uuid
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'development/server/tests'))
from pg_support import free_port,protect_directory,Lab
PS='powershell.exe'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


class New48Postgres(unittest.TestCase):
    @classmethod
    def call(cls,label,script,values):
        args=[PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script)]
        for k,v in values.items():
            args.append('-'+k)
            if v is not True:args.append(str(v))
        p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=240)
        (cls.work/(label+'.stdout')).write_bytes(p.stdout);(cls.work/(label+'.stderr')).write_bytes(p.stderr)
        if p.returncode or p.stderr:raise AssertionError(label+' failed; private logs retained')
        value=json.loads(p.stdout.decode('utf-8-sig'))
        assert value['valid'],label
        return value

    @classmethod
    def setUpClass(cls):
        cls.work=ROOT/'.local/sql-minimal-labs'/('install17-'+uuid.uuid4().hex)
        cls.work.mkdir(parents=True);protect_directory(cls.work)
        app=ROOT/'.local/distribution48/maintenance-01';tools=ROOT/'tools/windows'
        cls.pg=ROOT/'.local/postgresql-17.11-4/pgsql/bin';cls.dotnet=ROOT/'.local/dotnet-10.0.401/dotnet.exe'
        stage=cls.work/'stage';pin=sha(app/'manifest.json')
        s=cls.call('stage',tools/'Stage-ServerDistribution.ps1',dict(ManifestPath=app/'manifest.json',ExpectedManifestSha256=pin,ServerPath=app/'server',FrontendPath=app/'frontend',DotNetPath=cls.dotnet,PostgresBinPath=cls.pg,DestinationPath=stage))
        cls.instance=cls.work/'source'
        n=cls.call('new',tools/'New-RackClickLabInstance.ps1',dict(StagePath=stage,ExpectedManifestSha256=pin,ExpectedReceiptSha256=s['receiptSha256'],DotNetPath=cls.dotnet,PostgresBinPath=cls.pg,InstancePath=cls.instance,PostgresPort=free_port(),PublicOrigin='http://127.0.0.1:'+str(free_port()),BootstrapUser='install17-fixture',SystemhausName='Synthetic NEW48',DevelopmentLoopbackHttp=True,ProtectSqlCredentials=True,MinimizeSqlSecrets=True))
        cls.instance_hash=n['instanceManifestSha256']
        cls.probe=ROOT/'tools/tests/installer48/Invoke-New48Probe.ps1'
        cls.call('seed',cls.probe,dict(InstancePath=cls.instance,ExpectedInstanceSha256=cls.instance_hash,Mode='Seed'))

    def test_01_minimum3_and_full_backup(self):
        manifest=json.loads((self.instance/'instance.json').read_text())
        self.assertEqual(manifest['schemaVersion'],3)
        self.assertEqual(sorted(p.name for p in (self.instance/'private').iterdir()),['admin-login.json','backup-password.dpapi.json','backup-profile.json','runtime.json'])
        result=self.call('backup',self.probe,dict(InstancePath=self.instance,ExpectedInstanceSha256=self.instance_hash,Mode='Backup',BackupDestination=self.work/'export'))
        self.assertEqual(result['code'],'minimal_backup_complete')
        self.assertTrue(result['witnessReadOnly'] and result['privateRuntimeDenied'] and result['privateBackupReadable'])

    def test_02_restore_dump_in_separate_database(self):
        dump=self.work/'export/data.dump'
        self.assertTrue(dump.is_file())
        with Lab('install17-dump-restore') as lab:
            db=lab.create_database('restore48')
            env=lab.environment();env['PGPASSFILE']=str(lab.admin_passfile)
            p=subprocess.run([str(lab.pg_bin/'pg_restore.exe'),'-w','-h','127.0.0.1','-p',str(lab.port),'-U',lab.admin,'-d',db.name,'--no-owner','--no-acl','--exit-on-error',str(dump)],capture_output=True,env=env,timeout=120)
            (self.work/'pg_restore.stderr').write_bytes(p.stderr)
            self.assertEqual(p.returncode,0,'private restore log retained')
            self.assertEqual(lab.sql(db,"SELECT max(version) FROM schema_migration",admin=True),'48')
            self.assertEqual(lab.sql(db,"SELECT count(*) FROM information_schema.tables WHERE table_schema='rackclick_private'",admin=True),'2')


if __name__=='__main__':unittest.main(verbosity=2)
