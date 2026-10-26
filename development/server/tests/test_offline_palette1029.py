"""One transported Windows ZIP/New/HTTPS/palette12/011/XLS/Backup/Restore protocol.

Reuses guarded909 lifecycle/HTTP/snapshot helpers, without executing its historical
test. Bundled PowerShell owns provisioning and Restore. No actual QA is accessed.
"""
import argparse,hashlib,json,platform,secrets,ssl,subprocess,time,unittest,uuid
from datetime import datetime,timezone
from pathlib import Path
import test_offline_installation as native
from pg_support import Client,NO_WINDOW
from test_private_deployment_flow import NativeServer
from test_offline_relations909 import OfflineRelations909

ROOT=native.ROOT;sha=native.sha;read=native.read
MANIFEST=ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029/CANDIDATA969-FIX02.json'
PIN='b589609154fed1567106ef0865972155258f0f5474128c73076f4697d43b8bda'
TYPES=['rj45','rj45_poe','sfp','sfp28','qsfp','mgmt','console','power','usb_a','usb_c']

class OfflinePalette1029(OfflineRelations909):
    test_transported_relations849_https_xls_permissions_restart_backup_restore=None

    @classmethod
    def setUpClass(cls):
        cls.palette_checks=[];cls.frontend_checks=[];cls.excel_checks=[];cls.table_digests_before_backup={};cls.recovery_snapshot_exact=False
        native.OfflineInstallation.setUpClass.__func__(cls)
        assert cls.bundle['applicationManifestSha256']==PIN and cls.bundle['versions']['schema']==12
        sources=[Path(__file__),MANIFEST,Path(__file__).with_name('test_offline_relations909.py'),Path(__file__).with_name('test_rc9_excel_reports.py')]
        cls.guards.update({p.relative_to(ROOT).as_posix():sha(p) for p in sources});assert sha(MANIFEST)==PIN

    def check_frontend(self,stage,content):
        expected=(content/'application/frontend/app.js').read_bytes();actual=self.expect(self.server().request('GET','/app.js'),200).body
        self.assertEqual(actual,expected);self.assertEqual(hashlib.sha256(actual).hexdigest(),read(MANIFEST)['distributions']['frontend']['app.js'])
        self.assertIn(b'/me/port-colors',actual)
        self.frontend_checks.append(dict(stage=stage,httpServedAppJsExact=True,appJsSha256=hashlib.sha256(actual).hexdigest(),personalPaletteRouteTransported=True,domExecuted=False,accessibilityTreeInspected=False,screenReaderVoiceTested=False))

    def palette(self,c):
        response=self.expect(c.request('GET','/api/v1/me/port-colors'),200);value=response.json()
        self.assertEqual(value['ownerId'],self.actor(c));self.assertEqual(value['kind'],'userPortColors')
        self.assertEqual(response.headers.get('etag'),f'"port-colors-{value["revision"]}"');return value

    def color_write(self,c,colors,revision=None,key=None,cancel=False,status=200):
        if revision is None:revision=self.palette(c)['revision']
        key=key or str(uuid.uuid4());path='/api/v1/me/port-colors'+(f'/operations/{key}/cancel' if cancel else '')
        return self.expect(c.request('POST',path,{'colors':colors},{'X-RackClick-Actor':self.actor(c),'If-Match':f'"port-colors-{revision}"','Idempotency-Key':key}),status).json()

    def color_status(self,c,key):
        return self.expect(c.request('GET',f'/api/v1/me/port-colors/operations/{key}'),200).json()

    def preference(self,c,language):
        current=self.expect(c.request('GET','/api/v1/me/preferences'),200).json();key=str(uuid.uuid4())
        value=self.expect(c.request('POST','/api/v1/me/preferences',{'key':'language','value':language},
            {'X-RackClick-Actor':self.actor(c),'If-Match':f'"preferences-{current["revision"]}"','Idempotency-Key':key}),200).json()
        return value,self.expect(c.request('GET','/api/v1/me/preferences'),200).json()

    def preference_status(self,c,key):
        return self.expect(c.request('GET',f'/api/v1/me/preferences/operations/{key}'),200).json()

    def history_rights(self,c):
        actual=json.loads(self.sql(c,'SELECT json_object_agg(version,digest) FROM schema_migration'))
        expected={str(int(Path(n).name.split('-')[0])):digest.upper() for n,digest in read(MANIFEST)['distributions']['server'].items() if n.startswith('database/')}
        self.assertEqual({k:v.upper() for k,v in actual.items()},expected)
        instance=read(c['root']/'instance/instance.json');runtime=instance['runtime'];owner=instance['owner']
        self.assertEqual(self.sql(c,f"SELECT count(*) FROM pg_roles WHERE rolname='{runtime}' AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolbypassrls AND NOT rolreplication"),'1')
        self.assertEqual(self.sql(c,f"SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner<>'{owner}'"),'0')
        self.assertEqual(self.sql(c,f"SELECT count(*) FROM pg_tables WHERE schemaname='public' AND NOT (has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'SELECT') AND has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'INSERT') AND has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'UPDATE') AND has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'DELETE'))"),'0')
        return dict(migrations=actual,all37TablesOwnedByNewOwner=True,runtimeNoAdministrativeRoles=True,runtimeCrudAll37Tables=True)

    def test_transported_palette12_public_new_restore_https_37_tables(self):
        inspected=self.invoke('Test-RackClickOfflineBundle.ps1',dict(ArchivePath=self.archive,ExpectedArchiveSha256=native.ARCHIVE_SHA));self.assertEqual(inspected['code'],'bundle_verified')
        source=self.context(self.installation_root/'deployment');denied=self.home/'bad-hash'
        self.invoke('Install-RackClickOfflineBundle.ps1',self.install_args(source,ExpectedArchiveSha256='0'*64,DestinationPath=denied),2);self.assertFalse(denied.exists())
        existing=self.home/'existing';existing.mkdir();(existing/'keep.txt').write_bytes(b'untouched')
        self.invoke('Install-RackClickOfflineBundle.ps1',self.install_args(source,DestinationPath=existing),1);self.assertEqual(list(existing.iterdir()),[existing/'keep.txt']);self.assertEqual((existing/'keep.txt').read_bytes(),b'untouched')
        installed=self.invoke('Install-RackClickOfflineBundle.ps1',self.install_args(source,Mode='New'));self.assertEqual(installed['code'],'installation_prepared')
        self.activate(source,installed);self.assert_content();self.assertFalse((self.instance_path/'pgdata/postmaster.pid').exists())
        content=self.installation_root/'content';self.operator_tools=content/'operators';type(self).operator_tools=self.operator_tools
        self.runtime=content/'dependencies/dotnet';self.pg_bin=content/'dependencies/postgresql/bin'
        p=subprocess.run([str(self.runtime/'dotnet.exe'),'--list-sdks'],capture_output=True,check=True,creationflags=NO_WINDOW,env=self.poisoned_environment())
        self.assertFalse(p.stdout.strip() or p.stderr.strip());self.assertFalse((self.runtime/'sdk').exists())
        self.invoke('Test-RackClickPrivateDeployment.ps1',dict(DeploymentPath=self.deployment_path,ExpectedDeploymentSha256=self.deployment_sha))
        original_login=read(self.instance_path/'private/admin-login.json');original_identity=read(self.instance_path/'instance.json')
        original_secrets={p.name:sha(p) for p in (self.instance_path/'private').iterdir() if p.is_file()};original_tls={p.name:sha(p) for p in (self.deployment_path/'https').iterdir()}
        run=self.start(1);server=self.server();self.assertEqual(self.expect(server.request('GET','/health/ready'),200).json(),dict(status='ready',schemaVersion=12))
        self.assertEqual(self.expect(server.request('GET','/'),200).body,(content/'application/frontend/index.html').read_bytes());self.check_frontend('installed',content)
        with self.assertRaises(ssl.SSLCertVerificationError):NativeServer(self.origin,ssl.create_default_context()).request('GET','/health/ready')
        admin,second=Client(server),Client(server);login=self.expect(admin.login(**original_login),200);self.assertIn('; secure',login.headers['set-cookie'].lower());self.expect(second.login(**original_login),200)
        reader_login=dict(username='Lector paleta Ω😀',password=secrets.token_hex(32));reader_id=self.admin_write(admin,'/api/v1/admin/users',reader_login,201)['resource']['id']
        reader=Client(server);self.expect(reader.login(**reader_login),200);self.assertEqual(self.expect(reader.request('GET','/api/v1/customers'),200).json(),[]);self.expect(reader.request('GET','/api/v1/admin/users'),403)
        self.assertEqual(self.palette(admin)['colors'],{});self.assertEqual(self.palette(reader)['colors'],{});self.assertEqual(self.sql(source,'SELECT count(*) FROM user_port_colors'),'0')
        house_before=self.expect(admin.request('GET','/api/v1/systemhaus'),200).json();core=self.snapshot(source)
        noop0=self.color_write(reader,{});self.assertFalse(noop0['result']['changed']);self.assertEqual(noop0['revision'],0);self.assertEqual(self.sql(source,'SELECT count(*) FROM user_port_colors'),'0')
        colors={kind:f'#{i+1:06x}' for i,kind in enumerate(TYPES)};color_key=str(uuid.uuid4());made=self.color_write(admin,colors,key=color_key)
        self.assertTrue(made['result']['changed']);self.assertEqual(self.palette(second)['colors'],colors);self.assertEqual(self.palette(reader)['colors'],{})
        self.assertEqual(self.color_write(second,dict(reversed(list(colors.items()))),revision=0,key=color_key),made)
        noop=self.color_write(second,colors);self.assertFalse(noop['result']['changed']);self.assertEqual(noop['revision'],1)
        subset=dict(colors);del subset['rj45'];self.color_write(admin,subset);self.assertEqual(self.palette(admin)['colors'],subset)
        reset=self.color_write(admin,{});self.assertTrue(reset['result']['changed']);self.assertEqual(self.palette(admin)['colors'],{})
        final_admin=self.color_write(admin,colors);reader_colors={'rj45_poe':'#aabbcc','usb_c':'#010203'};reader_made=self.color_write(reader,reader_colors)
        self.assertEqual(self.color_status(reader,color_key)['state'],'notRecorded');self.assertEqual(self.color_status(admin,reader_made['requestId'])['state'],'notRecorded')
        fence=str(uuid.uuid4());fenced=self.color_write(reader,{'sfp':'#112233'},revision=0,key=fence,cancel=True);self.assertEqual(fenced['state'],'cancelled');self.assertIsNone(fenced['operation'])
        self.color_write(reader,{'sfp':'#112233'},revision=0,key=fence,status=409);self.color_write(reader,{'sfp':'#112233'},revision=1,key=fence,status=409)
        self.assertEqual(self.color_status(second,color_key)['operation'],made);self.color_write(second,colors,revision=0,status=412)
        self.assertEqual(self.expect(admin.request('GET','/api/v1/systemhaus'),200).json(),house_before)
        after=self.snapshot(source);self.assertEqual({k:v for k,v in after.items() if k not in {'app_session','audit_event','user_port_colors','user_port_color_operation'}},{k:v for k,v in core.items() if k not in {'app_session','audit_event','user_port_colors','user_port_color_operation'}})
        pref_admin,pref_state=self.preference(admin,'es');pref_reader,reader_pref_state=self.preference(reader,'de');self.assertEqual(self.preference_status(reader,pref_admin['requestId'])['state'],'notRecorded')
        self.palette_checks.append(dict(stage='installed',runtimeWithoutSdk=True,httpsUntrustedRejected=True,secureCookie=True,readerWithoutClientsCanSetOwnPalette=True,getDoesNotCreatePaletteRows=True,allTenIndependentTypes=True,otherSessionReadsCommittedPalette=True,twoActorIsolation=True,replayOriginalReceipt=True,noOpRevisionStable=True,individualAndFullReset=True,staleNewRequestRejected=True,cancellationFencesLateWrites=True,coreUnchangedByPalette=True,preferences011SeparateAndOwned=True))
        customer=self.admin_write(admin,'/api/v1/customers',{'name':'Cliente paleta XLS Ω😀'},201)['resource']['id']
        self.expect(reader.request('GET',f'/api/v1/customers/{customer}/project'),404)
        group=self.admin_write(admin,'/api/v1/admin/user-groups',{'name':'Lectores paleta XLS'},201)['resource']['id'];self.admin_write(admin,f'/api/v1/admin/user-groups/{group}/members',{'userId':reader_id,'assigned':True})
        grant_base=dict(scope='customer',targetId=customer,assigned=True);self.admin_write(admin,f'/api/v1/admin/user-groups/{group}/grants',{**grant_base,'grantId':str(uuid.uuid4()),'capability':'inventory.read'})
        site=self.inventory(admin,customer,'site.create',{'name':'Sede Ω'});building=self.inventory(admin,customer,'building.create',{'name':'Edificio Ω','siteId':site});room=self.inventory(admin,customer,'room.create',{'name':'Sala Ω','buildingId':building})
        rack=self.inventory(admin,customer,'rack.create',{'name':'Rack Ω😀','roomId':room,'sizeU':42});device=self.inventory(admin,customer,'device.create',{'name':'=1+1','kind':'rackEquipment','rackId':rack,'sizeU':1,'portGroups':[{'type':'rj45','count':2},{'type':'rj45','count':2}]})
        endpoint=self.inventory(admin,customer,'device.create',{'name':'000001 Ω 日本語 🐈','kind':'endDevice','roomId':room,'portGroups':[{'type':'rj45','count':1}]})
        project=self.project(admin,customer);ports=sorted([p for p in project['ports'] if p['deviceId']==device],key=lambda p:(p['groupId'],p['gn']));end=next(p for p in project['ports'] if p['deviceId']==endpoint)
        self.inventory(admin,customer,'connections.create',{'fromPortId':ports[0]['id'],'toPortId':end['id'],'note':'+1+1','color':'#aabbcc'});self.inventory(admin,customer,'connections.create',{'fromPortId':ports[1]['id'],'toPortId':ports[2]['id'],'note':'@SUM(1,2)','color':'#12aBcD'})
        source_revision=self.project(second,customer)['revision'];self.generate(reader,customer,rack,status=403)
        self.admin_write(admin,f'/api/v1/admin/user-groups/{group}/grants',{**grant_base,'grantId':str(uuid.uuid4()),'capability':'reports.export'})
        key=str(uuid.uuid4());xls_made=self.generate(admin,customer,rack,key=key);tables,raw=self.xls(xls_made);self.assertEqual(len(tables),3)
        self.assertEqual(tables[0][0]['values'][0],'=1+1');self.assertIn('000001 Ω 日本語 🐈',raw.decode());native.write(self.evidence/'synthetic-xls-receipt.json',xls_made);(self.evidence/'synthetic-report.xls').write_bytes(raw)
        reader_xls=self.generate(reader,customer,rack);self.assertEqual(self.receipt(reader,customer,key)['state'],'notRecorded');self.assertEqual(self.receipt(admin,customer,reader_xls['requestId'])['state'],'notRecorded')
        self.expect(reader.request('POST',f'/api/v1/customers/{customer}/commands',{'type':'site.create','payload':{'name':'Denied'}},{'X-RackClick-Actor':reader_id,'If-Match':f'"{source_revision}"','Idempotency-Key':str(uuid.uuid4())}),403)
        self.inventory(admin,customer,'device.update',{'id':device,'name':'Dispositivo actualizado Ω😀'});self.generate(admin,customer,rack,revision=source_revision,status=412);self.assertEqual(self.generate(second,customer,rack,revision=source_revision,key=key),xls_made)
        source_rights=self.history_rights(source);copied_cookie=reader.cookie
        self.excel_checks.append(dict(stage='installed',threeHtmlTablesValidated=True,explicitReportsGrantRequired=True,readerCannotEditInventory=True,twoActorReceiptsIsolated=True,replayOriginalBytesTimestampAfterInventoryChange=True,historyAndRights=source_rights))
        self.stop(run);run2=self.start(2);self.expect(second.request('GET','/api/v1/me'),200)
        self.assertEqual(self.palette(second)['colors'],colors);self.assertEqual(self.palette(reader)['colors'],reader_colors);self.assertEqual(self.color_status(second,color_key)['operation'],made);self.assertEqual(self.color_status(reader,fence),fenced)
        self.assertEqual(self.expect(second.request('GET','/api/v1/me/preferences'),200).json(),pref_state);self.assertEqual(self.receipt(second,customer,key)['operation'],xls_made)
        before=self.snapshot(source);self.assertEqual(len(before),37);type(self).table_digests_before_backup=before
        backup=self.home/'backup paleta12 Ω';self.checked_backup(self.pg_bin,backup);self.assertEqual(self.snapshot(source),before);self.stop(run2)
        self.palette_checks.append(dict(stage='restart_backup',sessionsPersistSourceRestart=True,personalPalettesAndFencePersistRestart=True,preferences011PersistRestart=True,receiptArtifactTimestampExactAfterRestart=True,all37SourceTablesUnchangedByBackup=True))
        recovered=self.context(self.home/'restored-installation/deployment');restored=self.invoke('Install-RackClickOfflineBundle.ps1',self.restore_args(recovered,backup));self.assertEqual(restored['code'],'installation_prepared')
        receipt=read(recovered['root'].parent/'installation.json');self.assertEqual(receipt['schemaVersion'],2);self.assertEqual(receipt['bundleArchiveSha256'],native.ARCHIVE_SHA);self.assertEqual(receipt['recovery']['backupManifestSha256'],sha(backup/'manifest.json'));self.assertEqual(sha(recovered['root'].parent/'installation.json'),restored['installationSha256'])
        restored_content=recovered['root'].parent/'content'
        for name,item in self.bundle['files'].items():self.assertEqual(sha(restored_content/name),item['sha256'])
        self.activate(recovered,restored);self.operator_tools=restored_content/'operators';type(self).operator_tools=self.operator_tools;self.runtime=restored_content/'dependencies/dotnet';self.pg_bin=restored_content/'dependencies/postgresql/bin'
        current=read(self.instance_path/'instance.json')
        for field in ['id','rootPath','postgresPort','database','owner','runtime','clusterAdmin']:self.assertNotEqual(current[field],original_identity[field])
        for name,digest in original_secrets.items():self.assertNotEqual(sha(self.instance_path/'private'/name),digest)
        self.assertNotEqual(sha(self.deployment_path/'https/server.pfx'),original_tls['server.pfx']);run3=self.start(3);self.check_frontend('restored',restored_content)
        self.assertEqual(self.snapshot(recovered,undo_recovery=True),{k:v for k,v in before.items() if k!='app_session'});self.assertEqual(self.sql(recovered,'SELECT count(*) FROM app_session'),'0');type(self).recovery_snapshot_exact=True
        recovered_rights=self.history_rights(recovered);self.assertTrue(list((self.instance_path/'logs').glob('*recover-admin*')))
        audit=json.loads(self.sql(recovered,"SELECT after_json FROM audit_event WHERE action='deployment.recover'"));self.assertEqual(audit['sourceBackupManifestSha256'],sha(backup/'manifest.json'))
        self.assertGreater(audit['revokedSessions'],0);self.assertEqual(self.sql(recovered,"SELECT count(*) FROM audit_event WHERE action='deployment.recover'"),'1')
        old=Client(self.server());old.cookie=copied_cookie;self.expect(old.request('GET','/api/v1/me'),401)
        new_login=read(self.instance_path/'private/admin-login.json');self.assertNotEqual(new_login['password'],original_login['password']);new_admin=Client(self.server());self.expect(new_admin.login(**new_login),200)
        self.assertEqual(self.palette(new_admin)['colors'],{});cap=self.expect(new_admin.request('GET','/api/v1/admin/capabilities'),200).json()['capabilities'];self.assertEqual(len(cap),10)
        original=Client(self.server());self.expect(original.login(**original_login),200);restored_reader=Client(self.server());self.expect(restored_reader.login(**reader_login),200)
        self.assertEqual(self.palette(original),self.palette_result(final_admin,colors));self.assertEqual(self.palette(restored_reader),self.palette_result(reader_made,reader_colors))
        self.assertEqual(self.color_status(original,color_key)['operation'],made);self.assertEqual(self.color_write(original,colors,revision=0,key=color_key),made);self.assertEqual(self.color_status(restored_reader,reader_made['requestId'])['operation'],reader_made)
        self.assertEqual(self.color_status(restored_reader,color_key)['state'],'notRecorded');self.assertEqual(self.color_status(restored_reader,fence),fenced);self.color_write(restored_reader,{'sfp':'#112233'},revision=1,key=fence,status=409)
        self.assertEqual(self.expect(original.request('GET','/api/v1/me/preferences'),200).json(),pref_state);self.assertEqual(self.expect(restored_reader.request('GET','/api/v1/me/preferences'),200).json(),reader_pref_state)
        self.assertEqual(self.preference_status(original,pref_admin['requestId'])['operation'],pref_admin);self.assertEqual(self.preference_status(restored_reader,pref_reader['requestId'])['operation'],pref_reader)
        self.assertEqual(self.receipt(original,customer,key)['operation'],xls_made);self.assertEqual(self.receipt(restored_reader,customer,reader_xls['requestId'])['operation'],reader_xls);self.assertEqual(self.generate(original,customer,rack,revision=source_revision,key=key),xls_made)
        self.palette_checks.append(dict(stage='recovered',publicInstallerModeRestoreReallyExecuted=True,installationReceiptLinkedToBackupAndArchive=True,recoverAdmin12ReallyExecuted=True,all37TablesExactExceptExplicitRecoveryChanges=True,newRolesDatabaseSecretsTls=True,copiedSessionsRevoked=True,recoveryAuditBackupHashAndRevocationCountExplicit=True,originalOwnerPalettesPreferencesReceiptsExact=True,cancellationFenceSurvivesRestore=True,recoveryAdministratorPaletteInitiallyEmpty=True,historyAndRights=recovered_rights))
        self.excel_checks.append(dict(stage='recovered',originalOwnersReportBytesTimestampReceiptsExact=True,readerGrantSurvivesRestore=True,otherActorStillNotRecorded=True,capabilityCount=10))
        self.stop(run3);self.activate(source);self.operator_tools=content/'operators';type(self).operator_tools=self.operator_tools;self.runtime=content/'dependencies/dotnet';self.pg_bin=content/'dependencies/postgresql/bin'
        self.assertEqual({p.name:sha(p) for p in (self.instance_path/'private').iterdir()},original_secrets);self.assertEqual({p.name:sha(p) for p in (self.deployment_path/'https').iterdir()},original_tls)
        run4=self.start(4);self.assertEqual(self.snapshot(source),before);self.stop(run4);self.assertEqual(sha(self.installation_root/'installation.json'),installed['installationSha256']);self.assert_content()

    @staticmethod
    def palette_result(receipt,colors):
        return dict(kind='userPortColors',ownerId=receipt['ownerId'],revision=receipt['revision'],colors=colors)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path,required=True);ap.add_argument('--archive-sha',required=True);ap.add_argument('--evidence',type=Path,required=True);args=ap.parse_args()
    native.ARCHIVE=args.archive.resolve(strict=True);native.ARCHIVE_SHA=args.archive_sha;args.evidence.mkdir(parents=True,exist_ok=False)
    (args.evidence/'HARNESS.py').write_bytes(Path(__file__).read_bytes());started=time.monotonic();cls=OfflinePalette1029;cls.evidence=args.evidence
    with (args.evidence/'tests.log').open('x',encoding='utf-8') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),sources=getattr(cls,'guards',{}),inputsUnchanged=getattr(cls,'inputs_unchanged',False),ownedProcessesStopped=getattr(cls,'owned_processes_stopped',False),systemCrtDllsAndX64RegistryUnchanged=getattr(cls,'system_crt_unchanged',False),cleanupErrors=getattr(cls,'cleanup_errors',[]),archiveSha256=args.archive_sha,applicationManifestSha256=PIN,calls=getattr(cls,'calls',[]),frontendTransportChecks=cls.frontend_checks,paletteChecks=cls.palette_checks,excelChecks=cls.excel_checks,recoverySnapshotExact=cls.recovery_snapshot_exact,tableDigestsBeforeBackup=cls.table_digests_before_backup,fixture=str(getattr(cls,'home','uninitialized')),freshClustersInitialized=sum((c['root']/'instance/pgdata/PG_VERSION').is_file() for c in getattr(cls,'contexts',[])),actualQaAccessed=False,pythonProvisioning=False,pythonRestore=False,applicationBuilds=0,frontendBuilds=0,allowedRecoveryChanges=['app_session: removed','app_user: new recovery administrator','user_group/user_group_member/permission_grant: new administrator group and ten global capabilities','systemhaus: revision +1','audit_event: deployment.recover'],limits='Windows11/PowerShell5.1 isolated native new deployments from transported ZIP. Compatible host CRT reused. No SCM, clean/other Windows, productive PKI, elevated CRT install, redistribution approval, manual Wascar QA or adoption. JavaScript transport only; no DOM/AX/voice. HTML.xls only, no new Office execution.')
    report['successfulOperationalRecoveries']=sum(bool(c['script']=='Install-RackClickOfflineBundle.ps1' and c['exitCode']==0 and c['report'].get('sourceBackupManifestSha256')) for c in getattr(cls,'calls',[]))
    native.write(args.evidence/'result.json',report);print(json.dumps({k:report[k] for k in ['testsRun','successful','failures','errors','seconds','inputsUnchanged','ownedProcessesStopped']}))
    return 0 if result.wasSuccessful() and report['inputsUnchanged'] and report['ownedProcessesStopped'] and report['systemCrtDllsAndX64RegistryUnchanged'] and not report['cleanupErrors'] else 1
if __name__=='__main__':raise SystemExit(main())
