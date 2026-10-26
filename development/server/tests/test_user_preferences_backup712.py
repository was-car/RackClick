"""Native isolated database backup/restore of populated schema11; no operational upgrade."""
import argparse,hashlib,json,platform,secrets,time,unittest,uuid
from datetime import datetime,timezone
from pathlib import Path
from pg_support import Lab,Client,literal
from test_private_templates_gui import fixture
from test_inventory_movement_gui import tree
from test_shared_templates_backup592 import SharedBackup592,ROOT,OPS,sha,write

class PreferencesBackup712(SharedBackup592):
    # Do not inherit the old test itself: schema10 results remain historical.
    test_native_backup_restore_shared_data_and_reject_existing_database=None

    def post(self,client,path,body,tag,request=None):
        key=request or str(uuid.uuid4())
        return self.expect(client.request('POST',path,body,{'X-RackClick-Actor':client.actor_id,
            'If-Match':tag,'Idempotency-Key':key})).json()

    def test_native35_table_roundtrip_new_roles_and_existing_database_rejected(self):
        self.lab=self.__class__.lab;self.home=self.lab.directory/'native preferencias Ω';self.home.mkdir()
        self.db=self.lab.create_database('preferences-backup712');ids,password=fixture(self.lab,self.db,self.dll)
        self.lab.grant_runtime(self.db);server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend)
        clients=[]
        for name in ['move-admin','move-reader']:
            c=Client(server);self.expect(c.login(name,password));c.actor_id=self.expect(c.request('GET','/api/v1/me')).json()['user']['id'];clients.append(c)
        admin,reader=clients;path='/api/v1/me/preferences'
        self.post(admin,path,{'key':'language','value':'es'},'"preferences-0"')
        self.post(admin,path,{'key':'theme','value':'light'},'"preferences-1"')
        self.post(reader,path,{'key':'language','value':'de'},'"preferences-0"')
        cancelled=str(uuid.uuid4());terminal=self.post(admin,path+'/operations/'+cancelled+'/cancel',
            {'key':'theme','value':'dark'},'"preferences-2"',cancelled)
        self.assertEqual(terminal['state'],'cancelled')
        customer=ids['customer'];project=self.expect(admin.request('GET',f'/api/v1/customers/{customer}/project')).json()
        private=f'/api/v1/customers/{customer}/catalog/private-templates';shared=f'/api/v1/customers/{customer}/catalog/shared-templates'
        captured=self.post(admin,private,{'type':'capture','deviceId':ids['a'],'name':'Privada Ω😀 backup712','sourceRevision':project['revision']},'"templates-0"')
        detail=self.expect(admin.request('GET',private+'/'+captured['result']['templateId'])).json()['template']
        self.post(admin,shared,{'type':'publish','privateTemplateId':detail['id'],'definitionVersion':1,
            'definitionSha256':detail['definitionSha256'],'name':'Compartida Ω😀 backup712'},'"shared-templates-0"')
        server.close();before=self.snapshot(self.db)
        self.assertEqual(len(before),35);self.assertEqual(before['schema_migration']['rows'],11)
        self.assertEqual(before['user_preferences']['rows'],2);self.assertEqual(before['user_preference_operation']['rows'],4)
        self.restore_password=secrets.token_urlsafe(32);restore_user='rc_restore_prefs_'+uuid.uuid4().hex[:10]
        self.lab.sql('postgres',f'CREATE ROLE {restore_user} LOGIN NOSUPERUSER CREATEDB NOCREATEROLE PASSWORD {literal(self.restore_password)}',sensitive=True)
        source_profile=self.profile('source',self.db.name,self.db.owner,self.db.owner_password)
        restore_profile=self.profile('restore','postgres',restore_user,self.restore_password)
        destination=self.home/('backup-'+uuid.uuid4().hex)
        backup=self.call('New-RackClickDatabaseBackup.ps1',dict(ProfilePath=source_profile,DestinationPath=destination))
        self.assertEqual(backup['manifestSha256'],sha(destination/'manifest.json'))
        restored='rc_restore_prefs_'+uuid.uuid4().hex[:16]
        args=dict(ProfilePath=restore_profile,BackupPath=destination,ExpectedManifestSha256=backup['manifestSha256'],NewDatabaseName=restored)
        receipt=self.call('Restore-RackClickDatabaseBackup.ps1',args)
        self.assertTrue(receipt['newDatabaseCreated']);self.assertFalse(receipt['applicationStartAllowed'])
        after=self.snapshot(restored);self.assertEqual(before,after)
        rejected=self.call('Restore-RackClickDatabaseBackup.ps1',args,1);self.assertEqual(rejected['code'],'new_database_exists')
        self.assertFalse(rejected['newDatabaseCreated']);self.assertEqual(self.snapshot(restored),after);self.assertEqual(self.snapshot(self.db),before)
        self.__class__.observations=dict(tableCount=35,tableRowsAndDigests=before,restoreExact=True,
            newDatabaseOwnedByDifferentRole=True,originalSourceUnchanged=True,existingRestoreUnchanged=True,
            personalPreferencesAndTerminalFenceExact=True,privateAndSharedRowsExact=True,
            applicationStartAllowed=False,copiedSessionsNotUsed=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    m=json.loads(a.manifest.read_bytes());assert m['schema']==11;a.output.mkdir(parents=True,exist_ok=False)
    paths=[Path(__file__),OPS/'New-RackClickDatabaseBackup.ps1',OPS/'Restore-RackClickDatabaseBackup.ps1',OPS/'RackClick.Backup.ps1',
        OPS/'Test-RuntimePrerequisites.ps1',Path(__file__).with_name('test_shared_templates_backup592.py'),Path(__file__).with_name('pg_support.py'),
        Path(__file__).with_name('test_private_templates_gui.py'),Path(__file__).with_name('test_inventory_catalog_gui.py'),Path(__file__).with_name('test_inventory_movement_gui.py')]
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in paths};c=PreferencesBackup712
    c.dll=ROOT/m['serverDll'];c.frontend=ROOT/m['frontend'];before={part:tree(ROOT/m['candidateDirectory']/part) for part in ['server','frontend']};assert before==m['distributions']
    c.calls=[];c.observations={};c.lab=Lab('preferences-native-backup712');started=time.monotonic()
    try:
        with c.lab:
            with (a.output/'tests.log').open('x',encoding='utf-8') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(c))
    finally:c.lab.close()
    after={part:tree(ROOT/m['candidateDirectory']/part) for part in ['server','frontend']}
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,successful=result.wasSuccessful(),
        seconds=round(time.monotonic()-started,3),sources=sources,sourcesUnchanged=all(sha(ROOT/p)==h for p,h in sources.items()),
        artifactsUnchanged=before==after,manifestSha256=sha(a.manifest),calls=c.calls,observations=c.observations,
        labStopped=not c.lab.running,serversStopped=all(s.process.poll() is not None for s in c.lab.servers),
        actualQaAccessed=False,applicationRecovered=False,windowsPackage10Changed=False,
        limits='Database-only isolated native restore, not installation/runtime grants/session recovery/QA selection or Windows11 package support.')
    write(a.output/'result.json',report);print(json.dumps({k:report[k] for k in ['testsRun','successful','seconds','sourcesUnchanged','artifactsUnchanged','labStopped','serversStopped']}))
    return 0 if report['successful'] and all(report[k] for k in ['sourcesUnchanged','artifactsUnchanged','labStopped','serversStopped']) else 1
if __name__=='__main__':raise SystemExit(main())
