"""Native schema11 database-only roundtrip including the exact RC9 XLS HTML receipt."""
import argparse,base64,hashlib,json,platform,secrets,time,unittest,uuid
from datetime import datetime,timezone
from pathlib import Path
from pg_support import Lab,Client,literal
from test_private_templates_gui import fixture
from test_inventory_movement_gui import tree
from test_shared_templates_backup592 import SharedBackup592,ROOT,OPS,sha,write

class ExcelBackup832(SharedBackup592):
    test_native_backup_restore_shared_data_and_reject_existing_database=None

    def test_native35_tables_exact_xls_receipt_new_database_and_no_overwrite(self):
        self.lab=self.__class__.lab;self.home=self.lab.directory/'native Excel copia Ω';self.home.mkdir()
        self.db=self.lab.create_database('excel-backup832');ids,password=fixture(self.lab,self.db,self.dll)
        self.lab.grant_runtime(self.db);server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend)
        admin=Client(server);self.expect(admin.login('move-admin',password));actor=self.expect(admin.request('GET','/api/v1/me')).json()['user']['id']
        customer=ids['customer'];project=self.expect(admin.request('GET',f'/api/v1/customers/{customer}/project')).json()
        self.assertTrue(project['racks']);rack=project['racks'][0]['id'];request=str(uuid.uuid4())
        route=f'/api/v1/customers/{customer}/reports/xls-html'
        receipt=self.expect(admin.request('POST',route,{'rackId':rack},{'X-RackClick-Actor':actor,'If-Match':f'"{project["revision"]}"','Idempotency-Key':request})).json()
        self.assertEqual(receipt['kind'],'rc9ExcelReport');report=receipt['report'];artifact=base64.b64decode(report['contentBase64'],validate=True)
        self.assertEqual(len(artifact),report['byteLength']);self.assertEqual(hashlib.sha256(artifact).hexdigest(),report['sha256'])
        stored=json.loads(self.lab.sql(self.db.name,f"SELECT result_json FROM operation WHERE request_id={literal(request)}"))
        self.assertEqual(stored,receipt)
        server.close();before=self.snapshot(self.db)
        self.assertEqual(len(before),35);self.assertEqual(before['schema_migration']['rows'],11)
        self.restore_password=secrets.token_urlsafe(32);restore_user='rc_restore_excel_'+uuid.uuid4().hex[:10]
        self.lab.sql('postgres',f'CREATE ROLE {restore_user} LOGIN NOSUPERUSER CREATEDB NOCREATEROLE PASSWORD {literal(self.restore_password)}',sensitive=True)
        source=self.profile('source',self.db.name,self.db.owner,self.db.owner_password)
        restore=self.profile('restore','postgres',restore_user,self.restore_password);destination=self.home/('backup-'+uuid.uuid4().hex)
        backup=self.call('New-RackClickDatabaseBackup.ps1',dict(ProfilePath=source,DestinationPath=destination))
        self.assertEqual(backup['manifestSha256'],sha(destination/'manifest.json'))
        restored='rc_restore_excel_'+uuid.uuid4().hex[:16]
        args=dict(ProfilePath=restore,BackupPath=destination,ExpectedManifestSha256=backup['manifestSha256'],NewDatabaseName=restored)
        result=self.call('Restore-RackClickDatabaseBackup.ps1',args)
        self.assertTrue(result['newDatabaseCreated']);self.assertFalse(result['applicationStartAllowed'])
        after=self.snapshot(restored);self.assertEqual(before,after)
        copy=json.loads(self.lab.sql(restored,f"SELECT result_json FROM operation WHERE request_id={literal(request)}"))
        self.assertEqual(copy,receipt);self.assertEqual(base64.b64decode(copy['report']['contentBase64']),artifact)
        rejected=self.call('Restore-RackClickDatabaseBackup.ps1',args,1)
        self.assertEqual(rejected['code'],'new_database_exists');self.assertFalse(rejected['newDatabaseCreated'])
        self.assertEqual(self.snapshot(restored),after);self.assertEqual(self.snapshot(self.db),before)
        self.__class__.observations=dict(tableCount=35,tableRowsAndDigests=before,restoreExact=True,newDatabaseOwnedByDifferentRole=True,
            originalSourceUnchanged=True,existingRestoreUnchanged=True,receiptExact=True,artifactSha256=report['sha256'],artifactBytes=len(artifact),
            generatedAt=report['generatedAt'],applicationStartAllowed=False,copiedSessionsNotUsed=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    m=json.loads(a.manifest.read_bytes());assert m['schema']==11;a.output.mkdir(parents=True,exist_ok=False)
    paths=[Path(__file__),OPS/'New-RackClickDatabaseBackup.ps1',OPS/'Restore-RackClickDatabaseBackup.ps1',OPS/'RackClick.Backup.ps1',OPS/'Test-RuntimePrerequisites.ps1']
    paths += [Path(__file__).with_name(x) for x in ['test_shared_templates_backup592.py','pg_support.py','test_private_templates_gui.py','test_inventory_catalog_gui.py','test_inventory_movement_gui.py']]
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in paths};c=ExcelBackup832;c.dll=ROOT/m['serverDll'];c.frontend=ROOT/m['frontend']
    before={part:tree(ROOT/m['candidateDirectory']/part) for part in ['server','frontend']};assert before==m['distributions']
    c.calls=[];c.observations={};c.lab=Lab('excel-native-backup832');started=time.monotonic()
    try:
        with c.lab:
            with (a.output/'tests.log').open('x',encoding='utf-8') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(c))
    finally:c.lab.close()
    after={part:tree(ROOT/m['candidateDirectory']/part) for part in ['server','frontend']}
    record=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,successful=result.wasSuccessful(),seconds=round(time.monotonic()-started,3),sources=sources,sourcesUnchanged=all(sha(ROOT/p)==h for p,h in sources.items()),artifactsUnchanged=before==after,manifestSha256=sha(a.manifest),calls=c.calls,observations=c.observations,labStopped=not c.lab.running,serversStopped=all(s.process.poll() is not None for s in c.lab.servers),actualQaAccessed=False,applicationRecovered=False,windowsPackage772Changed=False,limits='Database-only isolated native restore. No complete installation, runtime grants/start/session recovery, real QA or Windows profile832.')
    write(a.output/'result.json',record);print(json.dumps({k:record[k] for k in ['testsRun','successful','seconds','sourcesUnchanged','artifactsUnchanged','labStopped','serversStopped']}))
    return 0 if record['successful'] and all(record[k] for k in ['sourcesUnchanged','artifactsUnchanged','labStopped','serversStopped']) else 1
if __name__=='__main__':raise SystemExit(main())
