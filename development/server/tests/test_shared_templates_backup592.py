"""Schema10 data roundtrip through existing native isolated backup/restore operators.

Not an installation, live upgrade, runtime session recovery or QA operation.
"""
import argparse,base64,hashlib,json,os,platform,secrets,subprocess,time,unittest,uuid
from datetime import datetime,timezone
from pathlib import Path
from pg_support import Lab,Client,literal,NO_WINDOW
from test_private_templates_gui import fixture
from test_inventory_movement_gui import tree

ROOT=Path(__file__).resolve().parents[3]
OPS=ROOT/'tools/windows'
PS=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))


class SharedBackup592(unittest.TestCase):
    def expect(self,response,status=200):
        self.assertEqual(response.status,status,'Unexpected HTTP response; credentials remain private')
        return response

    def profile(self,label,database,user,password):
        folder=self.home/label;folder.mkdir();secret=folder/'secret.txt';secret.write_bytes(password.encode())
        path=folder/'profile.json';write(path,dict(schemaVersion=1,host='127.0.0.1',port=self.lab.port,
            database=database,user=user,passwordFile=str(secret)))
        return path

    def call(self,script,args,expected=0):
        env={k:v for k,v in os.environ.items() if k.upper()!='PSMODULEPATH'}
        env.update(PGHOSTADDR='192.0.2.1',PGHOST='untrusted.invalid',PGDATABASE='other',PGUSER='other',
            PGPORT='1',PGPASSWORD='POISON-NOT-A-SECRET',PGSERVICE='must-not-load',PGOPTIONS='-c invalid_option=true')
        cmd=[str(PS),'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(OPS/script),
            '-PostgresBinPath',str(self.lab.pg_bin),*[x for k,v in args.items() for x in ('-'+k,str(v))]]
        started=time.monotonic();p=subprocess.run(cmd,env=env,capture_output=True,timeout=150,creationflags=NO_WINDOW)
        data=json.loads(p.stdout.decode('utf-8-sig'))
        self.assertFalse(p.stderr,'Native operator wrote unexpected stderr')
        self.assertEqual(p.returncode,expected,data);self.assertEqual(data['valid'],expected==0)
        self.assertFalse(any(secret in json.dumps(data) for secret in [self.db.owner_password,self.restore_password]))
        self.calls.append(dict(script=script,exitCode=p.returncode,seconds=round(time.monotonic()-started,3),
            report=data,childEnvironmentPoisoned=True))
        return data

    def snapshot(self,db):
        tables=self.lab.sql(db,"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
        self.assertTrue(all(name.replace('_','').isalnum() for name in tables))
        values={}
        for table in tables:
            raw=self.lab.sql(db,f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM public.{table} t")
            values[table]=dict(rows=len(json.loads(raw)),sha256=hashlib.sha256(raw.encode()).hexdigest())
        return values

    def test_native_backup_restore_shared_data_and_reject_existing_database(self):
        self.lab=self.__class__.lab;self.home=self.lab.directory/'native shared copia Ω';self.home.mkdir()
        self.db=self.lab.create_database('shared-native-backup592');ids,password=fixture(self.lab,self.db,self.dll)
        self.lab.grant_runtime(self.db);server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend)
        client=Client(server);self.expect(client.login('move-admin',password));client.actor_id=self.expect(client.request('GET','/api/v1/me')).json()['user']['id'];customer=ids['customer']
        private=f'/api/v1/customers/{customer}/catalog/private-templates';shared=f'/api/v1/customers/{customer}/catalog/shared-templates'
        project=self.expect(client.request('GET',f'/api/v1/customers/{customer}/project')).json()
        captured=self.expect(client.request('POST',private,dict(type='capture',deviceId=ids['a'],
            name='Privada backup Ω😀',sourceRevision=project['revision']),{'X-RackClick-Actor':client.actor_id,
            'If-Match':'"templates-0"','Idempotency-Key':str(uuid.uuid4())})).json()
        template=self.expect(client.request('GET',private+'/'+captured['result']['templateId'])).json()['template']
        raw=base64.b64decode(template['definitionBase64']);published=[]
        for n in range(2):
            key=str(uuid.uuid4());intent=dict(type='publish',privateTemplateId=template['id'],definitionVersion=1,
                definitionSha256=template['definitionSha256'],name='Compartida backup Ω😀 '+str(n))
            result=self.expect(client.request('POST',shared,intent,{'X-RackClick-Actor':client.actor_id,
                'If-Match':f'"shared-templates-{n}"','Idempotency-Key':key})).json();published.append(result['result']['templateId'])
            detail=self.expect(client.request('GET',shared+'/'+published[-1])).json()['template']
            self.assertTrue(base64.b64decode(detail['definitionBase64'])==raw)
            self.assertEqual(detail['definitionSha256'],hashlib.sha256(raw).hexdigest())
        self.expect(client.request('POST',shared,dict(type='deactivate',templateId=published[0]),
            {'X-RackClick-Actor':client.actor_id,'If-Match':'"shared-templates-2"','Idempotency-Key':str(uuid.uuid4())}))
        server.close()
        before=self.snapshot(self.db);self.assertEqual(before['schema_migration']['rows'],10)
        self.assertEqual(len(before),33,'Expected30historical+3shared tables')
        self.restore_password=secrets.token_urlsafe(32);restore_user='rc_restore_shared_'+uuid.uuid4().hex[:10]
        self.lab.sql('postgres',f'CREATE ROLE {restore_user} LOGIN NOSUPERUSER CREATEDB NOCREATEROLE PASSWORD {literal(self.restore_password)}',sensitive=True)
        source_profile=self.profile('source',self.db.name,self.db.owner,self.db.owner_password)
        restore_profile=self.profile('restore','postgres',restore_user,self.restore_password)
        destination=self.home/('backup-'+uuid.uuid4().hex)
        backup=self.call('New-RackClickDatabaseBackup.ps1',dict(ProfilePath=source_profile,DestinationPath=destination))
        self.assertEqual(backup['manifestSha256'],sha(destination/'manifest.json'))
        restored='rc_restore_shared_'+uuid.uuid4().hex[:16]
        args=dict(ProfilePath=restore_profile,BackupPath=destination,ExpectedManifestSha256=backup['manifestSha256'],NewDatabaseName=restored)
        result=self.call('Restore-RackClickDatabaseBackup.ps1',args)
        self.assertTrue(result['newDatabaseCreated']);self.assertFalse(result['applicationStartAllowed'])
        restored_snapshot=self.snapshot(restored)
        self.assertTrue(before==restored_snapshot,'Isolated native restore must preserve every row; raw credentials stay private')
        again=self.call('Restore-RackClickDatabaseBackup.ps1',args,expected=1)
        self.assertEqual(again['code'],'new_database_exists');self.assertFalse(again['newDatabaseCreated'])
        self.assertTrue(self.snapshot(restored)==restored_snapshot and self.snapshot(self.db)==before)
        self.__class__.observations=dict(tableCount=len(before),tableRowsAndDigests=before,newDatabaseOwnedByDifferentRole=True,
            originalSourceUnchanged=True,restoreExact=True,existingRestoreUnchanged=True,
            applicationStartAllowed=False,copiedSessionsNotUsed=True,sharedCopies=len(published),privateAndPublicBytesExact=True,
            limits='Database-isolated restore only. No runtime grants/start/login/session recovery, complete Windows install or QA update.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    m=json.loads(a.manifest.read_bytes());assert m['schema']==10
    a.output.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    paths=[Path(__file__),OPS/'New-RackClickDatabaseBackup.ps1',OPS/'Restore-RackClickDatabaseBackup.ps1',OPS/'RackClick.Backup.ps1',
        OPS/'Test-RuntimePrerequisites.ps1',Path(__file__).with_name('pg_support.py'),Path(__file__).with_name('test_private_templates_gui.py'),
        Path(__file__).with_name('test_inventory_catalog_gui.py'),Path(__file__).with_name('test_inventory_movement_gui.py')]
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in paths};c=SharedBackup592
    c.dll=ROOT/m['serverDll'];c.frontend=ROOT/m['frontend'];before={part:tree(ROOT/m['candidateDirectory']/part) for part in ['server','frontend']}
    assert before==m['distributions'];c.calls=[];c.observations={};c.lab=Lab('shared-native-backup592')
    try:
        with c.lab:
            with (a.output/'tests.log').open('w',encoding='utf-8') as log:
                result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(c))
    finally:
        c.lab.close()
    after={part:tree(ROOT/m['candidateDirectory']/part) for part in ['server','frontend']}
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,successful=result.wasSuccessful(),
        seconds=round(time.monotonic()-started,3),sources=sources,sourcesUnchanged=all(sha(ROOT/p)==h for p,h in sources.items()),
        artifactsUnchanged=before==after,manifestSha256=sha(a.manifest),calls=c.calls,observations=c.observations,
        labStopped=not c.lab.running,serversStopped=all(s.process.poll() is not None for s in c.lab.servers),
        actualQaAccessed=False,applicationRecovered=False,package532Changed=False)
    write(a.output/'result.json',report);print(json.dumps({k:report[k] for k in ['testsRun','successful','seconds','sourcesUnchanged','artifactsUnchanged','labStopped','serversStopped']}))
    return 0 if report['successful'] and all(report[k] for k in ['sourcesUnchanged','artifactsUnchanged','labStopped','serversStopped']) else 1
if __name__=='__main__':raise SystemExit(main())
