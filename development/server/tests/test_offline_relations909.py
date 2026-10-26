"""One fresh Windows ZIP/New/HTTPS/relations849/XLS/Backup/Restore protocol.

Native transported PowerShell operators own provisioning and recovery. Python
drives HTTP/assertions and read-only database snapshots; no prior test executes.
"""
import argparse,base64,hashlib,json,platform,re,secrets,ssl,subprocess,time,unittest,uuid
from datetime import datetime,timezone
from pathlib import Path
import test_offline_installation as native
from pg_support import Client,NO_WINDOW
from test_private_deployment_flow import NativeServer
from test_private_deployment_recovery import PrivateDeploymentRecovery
from test_rc9_excel_reports import Rc9ExcelPostgres

ROOT=native.ROOT;sha=native.sha;read=native.read
MANIFEST=ROOT/'evidence/s1-20261018/tanda-849/CANDIDATA849.json'
PIN='1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09'

class OfflineRelations909(native.OfflineInstallation):
    test_transported_package_install_restart_backup_restore=None
    sql=PrivateDeploymentRecovery.sql
    snapshot=PrivateDeploymentRecovery.snapshot
    project=PrivateDeploymentRecovery.project
    inventory=PrivateDeploymentRecovery.inventory
    xls=Rc9ExcelPostgres.xls

    @classmethod
    def setUpClass(cls):
        cls.frontend_checks=[];cls.excel_checks=[];cls.table_digests_before_backup={};cls.recovery_snapshot_exact=False
        super().setUpClass()
        assert cls.bundle['applicationManifestSha256']==PIN and cls.bundle['versions']['schema']==11
        sources=[Path(__file__),MANIFEST,Path(__file__).with_name('test_rc9_excel_reports.py')]
        cls.guards.update({p.relative_to(ROOT).as_posix():sha(p) for p in sources})
        assert sha(MANIFEST)==PIN

    def server(self):
        return NativeServer(self.origin,ssl.create_default_context(cafile=str(self.deployment_path/'https/server.pem')))

    def check_transported_status848(self,stage,content):
        expected=(content/'application/frontend/app.js').read_bytes()
        actual=self.expect(self.server().request('GET','/app.js'),200).body
        self.assertEqual(actual,expected)
        self.assertEqual(hashlib.sha256(actual).hexdigest(),read(MANIFEST)['distributions']['frontend']['app.js'])
        marker=b'data-relation-selection-status'
        self.assertEqual(actual.count(marker),1)
        descriptor=rb'role:\s*"status",\s*"aria-live":\s*"polite",\s*"aria-atomic":\s*"true",\s*"data-relation-selection-status":\s*true'
        self.assertRegex(actual,descriptor)
        self.frontend_checks.append(dict(stage=stage,httpServedAppJsExact=True,appJsSha256=hashlib.sha256(actual).hexdigest(),selectionStatus848MarkerExactlyOnce=True,roleStatusPoliteAtomicDescriptorPresent=True,domExecuted=False,accessibilityTreeInspected=False,screenReaderVoiceTested=False))

    def actor(self,client):
        return self.expect(client.request('GET','/api/v1/me'),200).json()['user']['id']

    def admin_write(self,client,path,body,status=200):
        house=self.expect(client.request('GET','/api/v1/systemhaus'),200).json()
        return self.expect(client.request('POST',path,body,{'X-RackClick-Actor':self.actor(client),
            'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),status).json()

    def generate(self,client,customer,rack,revision=None,key=None,status=200):
        if revision is None:revision=self.project(client,customer)['revision']
        response=self.expect(client.request('POST',f'/api/v1/customers/{customer}/reports/xls-html',{'rackId':rack},
            {'X-RackClick-Actor':self.actor(client),'If-Match':f'"{revision}"','Idempotency-Key':key or str(uuid.uuid4())}),status)
        if status!=200:return response
        value=response.json();self.assertEqual(value['kind'],'rc9ExcelReport');self.xls(value)
        return value

    def receipt(self,client,customer,key,status=200):
        response=self.expect(client.request('GET',f'/api/v1/customers/{customer}/reports/xls-html/operations/{key}'),status)
        return response.json()

    def restore_args(self,context,backup):
        return dict(Mode='Restore',ArchivePath=self.archive,ExpectedArchiveSha256=native.ARCHIVE_SHA,
            DestinationPath=context['root'].parent,
            PostgresPort=context['pg'],HttpPort=context['http'],BackupPath=backup,
            ExpectedBackupManifestSha256=sha(backup/'manifest.json'),RecoveryUser='Recuperación XLS Ω😀')

    def history_rights(self,context):
        actual=json.loads(self.sql(context,'SELECT json_object_agg(version,digest) FROM schema_migration'))
        expected={str(int(Path(n).name.split('-')[0])):digest.upper() for n,digest in read(MANIFEST)['distributions']['server'].items() if n.startswith('database/')}
        self.assertEqual({k:v.upper() for k,v in actual.items()},expected)
        instance=read(context['root']/'instance/instance.json');runtime=instance['runtime'];owner=instance['owner']
        self.assertEqual(self.sql(context,f"SELECT count(*) FROM pg_roles WHERE rolname='{runtime}' AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolbypassrls AND NOT rolreplication"),'1')
        self.assertEqual(self.sql(context,f"SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner<>'{owner}'"),'0')
        self.assertEqual(self.sql(context,f"SELECT count(*) FROM pg_tables WHERE schemaname='public' AND NOT (has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'SELECT') AND has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'INSERT') AND has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'UPDATE') AND has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'DELETE'))"),'0')
        return dict(migrations=actual,all35TablesOwnedByNewOwner=True,runtimeNoAdministrativeRoles=True,runtimeCrudAll35Tables=True)

    def test_transported_relations849_https_xls_permissions_restart_backup_restore(self):
        inspected=self.invoke('Test-RackClickOfflineBundle.ps1',dict(ArchivePath=self.archive,ExpectedArchiveSha256=native.ARCHIVE_SHA))
        self.assertEqual(inspected['code'],'bundle_verified')
        source=self.context(self.installation_root/'deployment')
        denied=self.home/'bad-hash';self.invoke('Install-RackClickOfflineBundle.ps1',self.install_args(source,ExpectedArchiveSha256='0'*64,DestinationPath=denied),2)
        self.assertFalse(denied.exists())
        existing=self.home/'existing';existing.mkdir();(existing/'keep.txt').write_bytes(b'untouched')
        self.invoke('Install-RackClickOfflineBundle.ps1',self.install_args(source,DestinationPath=existing),1)
        self.assertEqual(list(existing.iterdir()),[existing/'keep.txt']);self.assertEqual((existing/'keep.txt').read_bytes(),b'untouched')
        installed=self.invoke('Install-RackClickOfflineBundle.ps1',self.install_args(source,Mode='New'));self.assertEqual(installed['code'],'installation_prepared')
        self.activate(source,installed);self.assert_content();self.assertFalse((self.instance_path/'pgdata/postmaster.pid').exists())
        content=self.installation_root/'content';self.operator_tools=content/'operators';type(self).operator_tools=self.operator_tools
        self.runtime=content/'dependencies/dotnet';self.pg_bin=content/'dependencies/postgresql/bin'
        p=subprocess.run([str(self.runtime/'dotnet.exe'),'--list-sdks'],capture_output=True,check=True,creationflags=NO_WINDOW,env=self.poisoned_environment())
        self.assertFalse(p.stdout.strip() or p.stderr.strip());self.assertFalse((self.runtime/'sdk').exists())
        self.assertFalse((content/'dependencies/postgresql/pgAdmin 4').exists())
        self.invoke('Test-RackClickPrivateDeployment.ps1',dict(DeploymentPath=self.deployment_path,ExpectedDeploymentSha256=self.deployment_sha))
        original_login=read(self.instance_path/'private/admin-login.json');original_identity=read(self.instance_path/'instance.json')
        original_secrets={p.name:sha(p) for p in (self.instance_path/'private').iterdir() if p.is_file()};original_tls={p.name:sha(p) for p in (self.deployment_path/'https').iterdir()}
        run=self.start(1);server=self.server()
        self.assertEqual(self.expect(server.request('GET','/health/ready'),200).json(),dict(status='ready',schemaVersion=11))
        self.assertEqual(self.expect(server.request('GET','/'),200).body,(content/'application/frontend/index.html').read_bytes())
        self.check_transported_status848('installed',content)
        with self.assertRaises(ssl.SSLCertVerificationError):NativeServer(self.origin,ssl.create_default_context()).request('GET','/health/ready')
        admin,second=Client(server),Client(server)
        login=self.expect(admin.login(**original_login),200);self.assertIn('; secure',login.headers['set-cookie'].lower());self.expect(second.login(**original_login),200)
        house=self.expect(admin.request('GET','/api/v1/systemhaus'),200).json()
        self.expect(admin.request('PUT','/api/v1/systemhaus',{'name':'Instalación XLS persistente Ω😀'},{'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),200)
        self.assertEqual(self.expect(second.request('GET','/api/v1/systemhaus'),200).json()['name'],'Instalación XLS persistente Ω😀')
        customer=self.admin_write(admin,'/api/v1/customers',{'name':'Cliente XLS Ω😀'},201)['resource']['id']
        reader_login=dict(username='Lector XLS Ω😀',password=secrets.token_hex(32))
        reader_id=self.admin_write(admin,'/api/v1/admin/users',reader_login,201)['resource']['id'];reader=Client(server);self.expect(reader.login(**reader_login),200)
        self.expect(reader.request('GET','/api/v1/admin/users'),403)
        group=self.admin_write(admin,'/api/v1/admin/user-groups',{'name':'Lectores XLS'},201)['resource']['id']
        self.admin_write(admin,f'/api/v1/admin/user-groups/{group}/members',{'userId':reader_id,'assigned':True})
        grant_base=dict(scope='customer',targetId=customer,assigned=True)
        self.admin_write(admin,f'/api/v1/admin/user-groups/{group}/grants',{**grant_base,'grantId':str(uuid.uuid4()),'capability':'inventory.read'})
        site=self.inventory(admin,customer,'site.create',{'name':'Sede XLS Ω'})
        building=self.inventory(admin,customer,'building.create',{'name':'Edificio XLS Ω','siteId':site})
        room=self.inventory(admin,customer,'room.create',{'name':'Sala XLS Ω','buildingId':building})
        rack=self.inventory(admin,customer,'rack.create',{'name':'Rack XLS Ω😀','roomId':room,'sizeU':42})
        device=self.inventory(admin,customer,'device.create',{'name':'=1+1','kind':'rackEquipment','rackId':rack,'sizeU':1,'portGroups':[{'type':'rj45','count':2},{'type':'rj45','count':2}]})
        endpoint=self.inventory(admin,customer,'device.create',{'name':'000001 Ω 日本語 🐈','kind':'endDevice','roomId':room,'portGroups':[{'type':'rj45','count':1}]})
        project=self.project(admin,customer);ports=sorted([p for p in project['ports'] if p['deviceId']==device],key=lambda p:(p['groupId'],p['gn']))
        end=next(p for p in project['ports'] if p['deviceId']==endpoint)
        self.inventory(admin,customer,'connections.create',{'fromPortId':ports[0]['id'],'toPortId':end['id'],'note':'+1+1','color':'#aabbcc'})
        self.inventory(admin,customer,'connections.create',{'fromPortId':ports[1]['id'],'toPortId':ports[2]['id'],'note':'@SUM(1,2)','color':'#12aBcD'})
        source_revision=self.project(second,customer)['revision']
        self.assertEqual(self.project(reader,customer)['revision'],source_revision)
        self.generate(reader,customer,rack,status=403)
        self.admin_write(admin,f'/api/v1/admin/user-groups/{group}/grants',{**grant_base,'grantId':str(uuid.uuid4()),'capability':'reports.export'})
        key=str(uuid.uuid4());made=self.generate(admin,customer,rack,key=key);tables,raw=self.xls(made)
        (self.evidence/'synthetic-report.xls').write_bytes(raw)
        native.write(self.evidence/'synthetic-receipt.json',made)
        self.assertEqual((made['report']['deviceCount'],made['report']['connectionCount'],made['report']['summaryCount']),(1,2,10))
        self.assertEqual(tables[0][0]['values'][0],'=1+1');self.assertIn('000001 Ω 日本語 🐈',raw.decode())
        from_groups={row['attrs']['data-from-group-id'] for row in tables[1]}
        self.assertTrue(from_groups.issubset({p['groupId'] for p in ports}))
        self.assertEqual(self.receipt(second,customer,key)['operation'],made)
        self.assertEqual(self.receipt(reader,customer,key)['state'],'notRecorded')
        reader_made=self.generate(reader,customer,rack)
        self.assertEqual(self.receipt(reader,customer,reader_made['requestId'])['operation'],reader_made)
        self.assertEqual((reader_made['report']['deviceCount'],reader_made['report']['connectionCount']),(1,2))
        self.assertEqual(self.receipt(admin,customer,reader_made['requestId'])['state'],'notRecorded')
        self.expect(reader.request('POST',f'/api/v1/customers/{customer}/commands',
            {'type':'site.create','payload':{'name':'Must not create'}},
            {'X-RackClick-Actor':reader_id,'If-Match':f'"{source_revision}"','Idempotency-Key':str(uuid.uuid4())}),403)
        self.inventory(admin,customer,'device.update',{'id':device,'name':'Dispositivo actualizado Ω😀'})
        self.generate(admin,customer,rack,revision=source_revision,status=412)
        self.assertEqual(self.generate(second,customer,rack,revision=source_revision,key=key),made)
        self.assertEqual(self.project(admin,customer)['devices'],self.project(reader,customer)['devices'])
        source_rights=self.history_rights(source);copied_cookie=reader.cookie
        self.excel_checks.append(dict(stage='installed',runtimeWithoutSdk=True,httpsUntrustedRejected=True,secureCookie=True,otherSessionReadsWrites=True,readerReadWithoutExportRejected=True,explicitReportsGrantRequired=True,twoActorReceiptsIsolated=True,threeHtmlTablesValidated=True,groupIdsExplicit=True,staleNewRequestRejected=True,replayOriginalBytesTimestampAfterInventoryChange=True,historyAndRights=source_rights))
        self.stop(run);run2=self.start(2)
        self.expect(second.request('GET','/api/v1/me'),200)
        self.assertEqual(self.receipt(second,customer,key)['operation'],made)
        self.assertEqual(self.generate(second,customer,rack,revision=source_revision,key=key),made)
        before=self.snapshot(source);self.assertEqual(len(before),35);type(self).table_digests_before_backup=before
        backup=self.home/'backup XLS instalado Ω';self.checked_backup(self.pg_bin,backup)
        self.assertEqual(self.snapshot(source),before);self.stop(run2)
        self.excel_checks.append(dict(stage='restart_backup',sessionsPersistSourceRestart=True,receiptArtifactTimestampExactAfterRestart=True,all35SourceTablesUnchangedByBackup=True))
        recovered=self.context(self.home/'restored-installation/deployment')
        restored=self.invoke('Install-RackClickOfflineBundle.ps1',self.restore_args(recovered,backup))
        self.assertEqual(restored['code'],'installation_prepared')
        restore_installation=read(recovered['root'].parent/'installation.json')
        self.assertEqual(restore_installation['schemaVersion'],2)
        self.assertEqual(restore_installation['bundleArchiveSha256'],native.ARCHIVE_SHA)
        self.assertEqual(restore_installation['recovery']['backupManifestSha256'],sha(backup/'manifest.json'))
        self.assertEqual(sha(recovered['root'].parent/'installation.json'),restored['installationSha256'])
        restored_content=recovered['root'].parent/'content'
        for name,item in self.bundle['files'].items():self.assertEqual(sha(restored_content/name),item['sha256'])
        self.activate(recovered,restored)
        self.operator_tools=restored_content/'operators';type(self).operator_tools=self.operator_tools
        self.runtime=restored_content/'dependencies/dotnet';self.pg_bin=restored_content/'dependencies/postgresql/bin'
        current=read(self.instance_path/'instance.json')
        for field in ['id','rootPath','postgresPort','database','owner','runtime','clusterAdmin']:self.assertNotEqual(current[field],original_identity[field])
        for name,digest in original_secrets.items():self.assertNotEqual(sha(self.instance_path/'private'/name),digest)
        self.assertNotEqual(sha(self.deployment_path/'https/server.pfx'),original_tls['server.pfx'])
        run3=self.start(3)
        self.check_transported_status848('restored',restored_content)
        self.assertEqual(self.snapshot(recovered,undo_recovery=True),{k:v for k,v in before.items() if k!='app_session'})
        self.assertEqual(self.sql(recovered,'SELECT count(*) FROM app_session'),'0');type(self).recovery_snapshot_exact=True
        recovered_rights=self.history_rights(recovered)
        self.assertTrue(list((self.instance_path/'logs').glob('*recover-admin*')))
        old=Client(self.server());old.cookie=copied_cookie;self.expect(old.request('GET','/api/v1/me'),401)
        new_login=read(self.instance_path/'private/admin-login.json');self.assertNotEqual(new_login['password'],original_login['password'])
        new_admin=Client(self.server());self.expect(new_admin.login(**new_login),200)
        cap=self.expect(new_admin.request('GET','/api/v1/admin/capabilities'),200).json()['capabilities'];self.assertEqual(len(cap),10)
        original=Client(self.server());self.expect(original.login(**original_login),200)
        restored_reader=Client(self.server());self.expect(restored_reader.login(**reader_login),200)
        self.assertEqual(self.receipt(original,customer,key)['operation'],made)
        self.assertEqual(self.receipt(restored_reader,customer,reader_made['requestId'])['operation'],reader_made)
        self.assertEqual(self.receipt(restored_reader,customer,key)['state'],'notRecorded')
        self.assertEqual(self.generate(original,customer,rack,revision=source_revision,key=key),made)
        new_report=self.generate(restored_reader,customer,rack)
        self.assertIn('Dispositivo actualizado Ω😀',base64.b64decode(new_report['report']['contentBase64']).decode())
        self.excel_checks.append(dict(stage='recovered',publicInstallerModeRestoreReallyExecuted=True,installationSchema2ReceiptLinkedToBackupAndArchive=True,recoverAdmin11ReallyExecuted=True,all35TablesExactExceptExplicitRecoveryChanges=True,newRolesDatabaseSecretsTls=True,copiedSessionsRevoked=True,originalOwnersReportBytesTimestampReceiptsExact=True,readerGrantSurvivesRestore=True,otherActorStillNotRecorded=True,newExportReadsCommittedUpdatedInventory=True,capabilityCount=10,historyAndRights=recovered_rights))
        self.stop(run3);self.activate(source)
        self.operator_tools=content/'operators';type(self).operator_tools=self.operator_tools
        self.runtime=content/'dependencies/dotnet';self.pg_bin=content/'dependencies/postgresql/bin'
        self.assertEqual({p.name:sha(p) for p in (self.instance_path/'private').iterdir()},original_secrets)
        self.assertEqual({p.name:sha(p) for p in (self.deployment_path/'https').iterdir()},original_tls)
        run4=self.start(4);self.assertEqual(self.snapshot(source),before);self.stop(run4)
        self.assertEqual(sha(self.installation_root/'installation.json'),installed['installationSha256']);self.assert_content()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path,required=True);ap.add_argument('--archive-sha',required=True);ap.add_argument('--evidence',type=Path,required=True);args=ap.parse_args()
    native.ARCHIVE=args.archive.resolve(strict=True);native.ARCHIVE_SHA=args.archive_sha;args.evidence.mkdir(parents=True,exist_ok=False)
    (args.evidence/'HARNESS.py').write_bytes(Path(__file__).read_bytes());started=time.monotonic();cls=OfflineRelations909;cls.evidence=args.evidence
    with (args.evidence/'tests.log').open('x',encoding='utf-8') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),sources=getattr(cls,'guards',{}),inputsUnchanged=getattr(cls,'inputs_unchanged',False),ownedProcessesStopped=getattr(cls,'owned_processes_stopped',False),systemCrtDllsAndX64RegistryUnchanged=getattr(cls,'system_crt_unchanged',False),cleanupErrors=getattr(cls,'cleanup_errors',[]),archiveSha256=args.archive_sha,applicationManifestSha256=PIN,calls=getattr(cls,'calls',[]),frontendTransportChecks=cls.frontend_checks,excelChecks=cls.excel_checks,recoverySnapshotExact=cls.recovery_snapshot_exact,tableDigestsBeforeBackup=cls.table_digests_before_backup,fixture=str(getattr(cls,'home','uninitialized')),freshClustersInitialized=sum((c['root']/'instance/pgdata/PG_VERSION').is_file() for c in getattr(cls,'contexts',[])),actualQaAccessed=False,pythonProvisioning=False,pythonRestore=False,applicationBuilds=0,frontendBuilds=0,allowedRecoveryChanges=['app_session: removed','app_user: new recovery administrator','user_group/user_group_member/permission_grant: new administrator group and ten global capabilities','systemhaus: revision +1','audit_event: deployment.recover'],limits='Windows11/PowerShell5.1 isolated new native deployments from transported content. Existing compatible system CRT reused. No SCM, clean/other Windows, productive PKI, elevated CRT install, redistribution approval, manual Wascar QA or adoption. Transported JavaScript bytes and markup descriptor only; no DOM, accessibility tree, voice or manual QA claim. HTML.xls only; no new Office interoperability execution in this test.')
    report['successfulOperationalRecoveries']=sum(bool(c['script']=='Install-RackClickOfflineBundle.ps1' and c['exitCode']==0 and c['report'].get('sourceBackupManifestSha256')) for c in getattr(cls,'calls',[]))
    native.write(args.evidence/'result.json',report);print(json.dumps({k:report[k] for k in ['testsRun','successful','failures','errors','seconds','inputsUnchanged','ownedProcessesStopped']}))
    return 0 if result.wasSuccessful() and report['inputsUnchanged'] and report['ownedProcessesStopped'] and report['systemCrtDllsAndX64RegistryUnchanged'] and not report['cleanupErrors'] else 1
if __name__=='__main__':raise SystemExit(main())
