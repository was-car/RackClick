"""One new native schema11 ZIP/New/HTTPS/Restart/Backup/Restore protocol.

Reuses guarded command, lifecycle and read-only snapshot helpers. No historical
test is inherited/executed. Operators from transported content own all provisioning,
restore, credentials/TLS and recover-admin11. Actual QA is never accessed.
"""
import argparse,base64,hashlib,json,platform,secrets,ssl,subprocess,time,unittest,uuid
from datetime import datetime,timezone
from pathlib import Path
import test_offline_installation as native
from pg_support import Client,NO_WINDOW
from test_private_deployment_flow import NativeServer
from test_private_deployment_recovery import PrivateDeploymentRecovery
from test_private_template_configurations import definition,wire
ROOT=native.ROOT;sha=native.sha;read=native.read
MANIFEST=ROOT/'evidence/s1-20261018/sesenta-tandas-653-712/CANDIDATA712-FINAL02.json'
PIN='f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd'
OLD=ROOT/'evidence/s1-20261018/sesenta-tandas-593-652/windows/native05/result.json'

class OfflinePreferences772(native.OfflineInstallation):
    test_transported_package_install_restart_backup_restore=None
    sql=PrivateDeploymentRecovery.sql
    snapshot=PrivateDeploymentRecovery.snapshot
    @classmethod
    def setUpClass(cls):
        cls.preferences_checks=[];cls.negative_checks=[];cls.table_digests_before_backup={};cls.recovery_snapshot_exact=False
        super().setUpClass()
        assert cls.bundle['applicationManifestSha256']==PIN and cls.bundle['versions']['schema']==11
        sources=[Path(__file__),MANIFEST,OLD,Path(__file__).with_name('test_private_template_configurations.py')]
        cls.guards.update({p.relative_to(ROOT).as_posix():sha(p) for p in sources})
        assert sha(MANIFEST)==PIN

    def server(self):
        return NativeServer(self.origin,ssl.create_default_context(cafile=str(self.deployment_path/'https/server.pem')))
    def actor(self,c):
        return self.expect(c.request('GET','/api/v1/me'),200).json()['user']['id']
    def admin_write(self,c,path,body,status=200):
        house=self.expect(c.request('GET','/api/v1/systemhaus'),200).json()
        return self.expect(c.request('POST',path,body,{'X-RackClick-Actor':self.actor(c),
            'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),status).json()
    def prefs(self,c):
        return self.expect(c.request('GET','/api/v1/me/preferences'),200).json()
    def pref_write(self,c,key,value,revision=None,request=None,suffix='',status=200):
        if revision is None:revision=self.prefs(c)['revision']
        request=request or str(uuid.uuid4())
        return self.expect(c.request('POST','/api/v1/me/preferences'+suffix,{'key':key,'value':value},
            {'X-RackClick-Actor':self.actor(c),'If-Match':f'"preferences-{revision}"','Idempotency-Key':request}),status).json()
    def terminal(self,c,request):
        return self.expect(c.request('GET','/api/v1/me/preferences/operations/'+request),200).json()
    def restore_args(self,c,backup):
        content=self.installation_root/'content'
        return dict(ManifestPath=content/'application/manifest.json',ExpectedManifestSha256=PIN,
            ServerPath=content/'application/server',FrontendPath=content/'application/frontend',
            DotNetPath=self.runtime/'dotnet.exe',PostgresBinPath=self.pg_bin,DestinationPath=c['root'],
            PostgresPort=c['pg'],HttpPort=c['http'],BackupPath=backup,
            ExpectedBackupManifestSha256=sha(backup/'manifest.json'),RecoveryUser='Recuperación11 Ω😀')

    def check_history_rights(self,c):
        actual=json.loads(self.sql(c,"SELECT json_object_agg(version,digest) FROM schema_migration"))
        expected={str(int(Path(n).name.split('-')[0])):digest.upper() for n,digest in read(MANIFEST)['distributions']['server'].items() if n.startswith('database/')}
        self.assertEqual({k:v.upper() for k,v in actual.items()},expected)
        instance=read(c['root']/'instance/instance.json');runtime=instance['runtime'];owner=instance['owner']
        self.assertEqual(self.sql(c,f"SELECT count(*) FROM pg_roles WHERE rolname='{runtime}' AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolbypassrls AND NOT rolreplication"),'1')
        self.assertEqual(self.sql(c,f"SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner<>'{owner}'"),'0')
        self.assertEqual(self.sql(c,f"SELECT count(*) FROM pg_tables WHERE schemaname='public' AND NOT (has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'SELECT') AND has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'INSERT') AND has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'UPDATE') AND has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'DELETE'))"),'0')
        return dict(migrations=actual,all35TablesOwnedByNewOwner=True,runtimeNoAdministrativeRoles=True,runtimeCrudAll35Tables=True)

    def test_schema11_transported_new_https_preferences_restart_backup_restore(self):
        inspected=self.invoke('Test-RackClickOfflineBundle.ps1',dict(ArchivePath=self.archive,ExpectedArchiveSha256=native.ARCHIVE_SHA))
        self.assertEqual(inspected['code'],'bundle_verified')
        source=self.context(self.installation_root/'deployment')
        denied=self.home/'bad-hash';self.invoke('Install-RackClickOfflineBundle.ps1',self.install_args(source,ExpectedArchiveSha256='0'*64,DestinationPath=denied),2)
        self.assertFalse(denied.exists())
        existing=self.home/'existing';existing.mkdir();(existing/'keep.txt').write_bytes(b'untouched')
        self.invoke('Install-RackClickOfflineBundle.ps1',self.install_args(source,DestinationPath=existing),1)
        self.assertEqual(list(existing.iterdir()),[existing/'keep.txt']);self.assertEqual((existing/'keep.txt').read_bytes(),b'untouched')
        installed=self.invoke('Install-RackClickOfflineBundle.ps1',self.install_args(source));self.assertEqual(installed['code'],'installation_prepared')
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
        with self.assertRaises(ssl.SSLCertVerificationError):NativeServer(self.origin,ssl.create_default_context()).request('GET','/health/ready')
        first,second=Client(server),Client(server)
        login=self.expect(first.login(**original_login),200);self.assertIn('; secure',login.headers['set-cookie'].lower());self.expect(second.login(**original_login),200)
        house=self.expect(first.request('GET','/api/v1/systemhaus'),200).json()
        self.expect(first.request('PUT','/api/v1/systemhaus',{'name':'Instalación11 persistente Ω😀'},{'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),200)
        house=self.expect(second.request('GET','/api/v1/systemhaus'),200).json();self.assertEqual(house['name'],'Instalación11 persistente Ω😀')
        customer=self.admin_write(first,'/api/v1/customers',{'name':'Cliente11 Ω😀'},201)['resource']['id']
        self.assertTrue(any(c['id']==customer for c in self.expect(second.request('GET','/api/v1/customers'),200).json()))
        reader_login=dict(username='Lector11 Ω😀',password=secrets.token_hex(32))
        reader_id=self.admin_write(first,'/api/v1/admin/users',reader_login,201)['resource']['id'];reader=Client(server);self.expect(reader.login(**reader_login),200)
        self.assertEqual(self.expect(reader.request('GET','/api/v1/customers'),200).json(),[])
        self.expect(reader.request('GET','/api/v1/admin/users'),403)
        self.expect(reader.request('GET',f'/api/v1/customers/{customer}/project'),404)
        blank=self.prefs(reader);self.assertEqual((blank['revision'],blank['language'],blank['theme']),(0,None,None))
        self.assertEqual(self.sql(source,'SELECT count(*) FROM user_preferences'),'0')
        language=self.pref_write(first,'language','es');theme=self.pref_write(first,'theme','light')
        reader_receipt=self.pref_write(reader,'language','de')
        self.assertEqual(self.prefs(second)['language'],'es');self.assertEqual(self.prefs(reader)['language'],'de')
        self.assertIsNone(self.prefs(reader)['theme']);self.assertEqual(self.prefs(reader)['ownerId'],reader_id)
        self.assertEqual(self.terminal(reader,language['requestId'])['state'],'notRecorded')
        self.pref_write(second,'theme','dark',revision=0,status=412)
        fence=str(uuid.uuid4());cancelled=self.pref_write(first,'theme','dark',revision=0,request=fence,suffix='/operations/'+fence+'/cancel')
        self.assertEqual(cancelled['state'],'cancelled');self.assertEqual(self.terminal(second,fence),cancelled)
        # Now grant only customer read. Preferences never confer edit or publication.
        group=self.admin_write(first,'/api/v1/admin/user-groups',{'name':'Lectores11'},201)['resource']['id']
        self.admin_write(first,f'/api/v1/admin/user-groups/{group}/members',{'userId':reader_id,'assigned':True})
        self.admin_write(first,f'/api/v1/admin/user-groups/{group}/grants',{'grantId':str(uuid.uuid4()),'capability':'inventory.read','scope':'customer','targetId':customer,'assigned':True})
        project=self.expect(first.request('GET',f'/api/v1/customers/{customer}/project'),200).json()
        intent={'type':'site.create','payload':{'name':'Sitio11'}}
        self.expect(reader.request('POST',f'/api/v1/customers/{customer}/commands',intent,{'X-RackClick-Actor':reader_id,'If-Match':f'"{project["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),403)
        self.expect(first.request('POST',f'/api/v1/customers/{customer}/commands',intent,{'X-RackClick-Actor':self.actor(first),'If-Match':f'"{project["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),200)
        private=f'/api/v1/customers/{customer}/catalog/private-templates';shared=f'/api/v1/customers/{customer}/catalog/shared-templates'
        body,_=wire(definition('dose'),'Configuración ZIP11 Ω😀')
        private_receipt=self.expect(first.request('POST',private+'/configurations',json.loads(body),{'X-RackClick-Actor':self.actor(first),'If-Match':'"templates-0"','Idempotency-Key':str(uuid.uuid4())}),200).json()
        detail=self.expect(first.request('GET',private+'/'+private_receipt['result']['templateId']),200).json()['template']
        publication=dict(type='publish',privateTemplateId=detail['id'],definitionVersion=1,definitionSha256=detail['definitionSha256'],name='Compartida ZIP11 Ω😀')
        headers={'X-RackClick-Actor':self.actor(first),'If-Match':'"shared-templates-0"','Idempotency-Key':str(uuid.uuid4())}
        published=self.expect(first.request('POST',shared,publication,headers),200).json()
        self.expect(reader.request('POST',shared,publication,{**headers,'X-RackClick-Actor':reader_id,'If-Match':'"shared-templates-1"','Idempotency-Key':str(uuid.uuid4())}),403)
        copy=self.expect(reader.request('GET',shared+'/'+published['result']['templateId']),200).json()['template']
        self.assertEqual(base64.b64decode(copy['definitionBase64']),base64.b64decode(detail['definitionBase64']))
        saved={self.actor(first):self.prefs(first),reader_id:self.prefs(reader)};copied_cookie=reader.cookie
        source_rights=self.check_history_rights(source)
        self.preferences_checks.append(dict(stage='installed',httpsUntrustedRejected=True,secureCookie=True,runtimeWithoutSdk=True,otherSessionReadsCommittedWrites=True,readerWithoutCustomersCanSetOwnPreferences=True,readOnlyGetDidNotInsert=True,ownersIsolated=True,readerCannotEditOrPublish=True,staleRevisionRejected=True,terminalFenceDurable=True,sharedDefinitionExact=True,historyAndRights=source_rights))
        self.stop(run);run2=self.start(2)
        self.expect(second.request('GET','/api/v1/me'),200);self.assertEqual(self.prefs(second),saved[self.actor(first)])
        self.assertEqual(self.prefs(reader),saved[reader_id]);self.assertEqual(self.terminal(first,language['requestId'])['operation'],language)
        self.assertEqual(self.terminal(first,fence),cancelled)
        before=self.snapshot(source);self.assertEqual(len(before),35);type(self).table_digests_before_backup=before
        backup=self.home/'backup11 instalado Ω';self.checked_backup(self.pg_bin,backup)
        self.assertEqual(self.snapshot(source),before);self.stop(run2)
        self.preferences_checks.append(dict(stage='restart_backup',preferencesAndReceiptsSurviveRestart=True,sessionsPersistSourceRestart=True,all35SourceTablesUnchangedByBackup=True))
        recovered=self.context(self.home/'recovered');restored=self.invoke('Restore-RackClickPrivateDeployment.ps1',self.restore_args(recovered,backup))
        self.activate(recovered,restored)
        current=read(self.instance_path/'instance.json')
        for field in ['id','rootPath','postgresPort','database','owner','runtime','clusterAdmin']:self.assertNotEqual(current[field],original_identity[field])
        for name,digest in original_secrets.items():self.assertNotEqual(sha(self.instance_path/'private'/name),digest)
        self.assertNotEqual(sha(self.deployment_path/'https/server.pfx'),original_tls['server.pfx'])
        run3=self.start(3)
        normalized=self.snapshot(recovered,undo_recovery=True);self.assertEqual(normalized,{k:v for k,v in before.items() if k!='app_session'})
        self.assertEqual(self.sql(recovered,'SELECT count(*) FROM app_session'),'0');type(self).recovery_snapshot_exact=True
        recovered_rights=self.check_history_rights(recovered)
        self.assertTrue(list((self.instance_path/'logs').glob('*recover-admin*')),'Operational recover-admin11 must really execute')
        old=Client(self.server());old.cookie=copied_cookie;self.expect(old.request('GET','/api/v1/me'),401)
        new_login=read(self.instance_path/'private/admin-login.json');self.assertNotEqual(new_login['password'],original_login['password'])
        new_admin=Client(self.server());self.expect(new_admin.login(**new_login),200)
        cap=self.expect(new_admin.request('GET','/api/v1/admin/capabilities'),200).json()['capabilities'];self.assertEqual(len(cap),10);self.assertIn('templates.publish',cap)
        self.assertEqual((self.prefs(new_admin)['revision'],self.prefs(new_admin)['language'],self.prefs(new_admin)['theme']),(0,None,None))
        self.assertEqual(self.expect(new_admin.request('GET',private),200).json()['templates'],[])
        original=Client(self.server());self.expect(original.login(**original_login),200)
        restored_reader=Client(self.server());self.expect(restored_reader.login(**reader_login),200)
        self.assertEqual(self.prefs(original),saved[self.actor(original)]);self.assertEqual(self.prefs(restored_reader),saved[reader_id])
        for receipt,c in [(language,original),(theme,original),(reader_receipt,restored_reader)]:
            self.assertEqual(self.terminal(c,receipt['requestId'])['operation'],receipt)
        self.assertEqual(self.terminal(original,fence),cancelled)
        self.assertEqual(self.expect(original.request('GET',private+'/'+detail['id']),200).json()['template'],detail)
        self.assertEqual(base64.b64decode(self.expect(restored_reader.request('GET',shared+'/'+published['result']['templateId']),200).json()['template']['definitionBase64']),base64.b64decode(detail['definitionBase64']))
        self.preferences_checks.append(dict(stage='recovered',recoverAdmin11ReallyExecuted=True,all35TablesExactExceptExplicitRecoveryChanges=True,newRolesDatabaseSecretsTls=True,copiedSessionsRevoked=True,originalOwnersPreferencesReceiptsAndFenceExact=True,newAdministratorDoesNotInheritPreferencesOrPrivateTemplates=True,capabilityCount=10,templatesPublishIncluded=True,historyAndRights=recovered_rights))
        self.stop(run3);self.activate(source)
        self.assertEqual({p.name:sha(p) for p in (self.instance_path/'private').iterdir()},original_secrets)
        self.assertEqual({p.name:sha(p) for p in (self.deployment_path/'https').iterdir()},original_tls)
        run4=self.start(4);self.assertEqual(self.snapshot(source),before);self.stop(run4)
        self.assertEqual(sha(self.installation_root/'installation.json'),installed['installationSha256']);self.assert_content()
        # Immutable prior schema10 archive only; never access its cluster or app.
        previous=read(OLD);self.assertTrue(previous['successful']);old_backup=Path(previous['fixture'])/'backup instalado Ω'
        old_hashes={p.name:sha(p) for p in old_backup.iterdir() if p.is_file()}
        self.guards.update({p.relative_to(ROOT).as_posix():sha(p) for p in old_backup.iterdir() if p.is_file()})
        negative=self.context(self.home/'schema10-rejected');denied=self.invoke('Restore-RackClickPrivateDeployment.ps1',self.restore_args(negative,old_backup),1)
        self.assertEqual(denied['code'],'instance_restore_restored_schema_required_11')
        self.assertFalse((negative['root']/'deployment.json').exists());self.assertFalse((negative['root']/'instance/instance.json').exists())
        self.assertTrue((negative['root']/'instance/pgdata/PG_VERSION').exists());self.assertFalse((negative['root']/'instance/pgdata/postmaster.pid').exists())
        self.assertFalse(list((negative['root']/'instance/logs').glob('*recover-admin*')))
        self.assertEqual(old_hashes,{p.name:sha(p) for p in old_backup.iterdir() if p.is_file()})
        self.negative_checks.append(dict(schema10BackupStage11Rejected=True,partialNewClusterPreserved=True,noSuccessReceipts=True,refusedAfterPgRestoreBeforeRecoverAdmin=True,sourceBackupExact=True,ownedPostgresStopped=True,implicitMigration=False))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path,required=True);ap.add_argument('--archive-sha',required=True);ap.add_argument('--evidence',type=Path,required=True);a=ap.parse_args()
    native.ARCHIVE=a.archive.resolve(strict=True);native.ARCHIVE_SHA=a.archive_sha;a.evidence.mkdir(parents=True,exist_ok=False)
    # Save exact harness before execution, including failed attempts.
    (a.evidence/'HARNESS.py').write_bytes(Path(__file__).read_bytes());started=time.monotonic();c=OfflinePreferences772
    with (a.evidence/'tests.log').open('x',encoding='utf-8') as log:r=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(c))
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=r.testsRun,successful=r.wasSuccessful(),failures=len(r.failures),errors=len(r.errors),seconds=round(time.monotonic()-started,3),sources=getattr(c,'guards',{}),inputsUnchanged=getattr(c,'inputs_unchanged',False),ownedProcessesStopped=getattr(c,'owned_processes_stopped',False),systemCrtDllsAndX64RegistryUnchanged=getattr(c,'system_crt_unchanged',False),cleanupErrors=getattr(c,'cleanup_errors',[]),archiveSha256=a.archive_sha,applicationManifestSha256=PIN,calls=getattr(c,'calls',[]),preferencesChecks=c.preferences_checks,negativeChecks=c.negative_checks,recoverySnapshotExact=c.recovery_snapshot_exact,tableDigestsBeforeBackup=c.table_digests_before_backup,fixture=str(getattr(c,'home','uninitialized')),freshClustersInitialized=sum((v['root']/'instance/pgdata/PG_VERSION').is_file() for v in getattr(c,'contexts',[])),actualQaAccessed=False,pythonProvisioning=False,pythonRestore=False,applicationBuilds=0,frontendBuilds=0,allowedRecoveryChanges=['app_session: removed','app_user: new recovery administrator','user_group/user_group_member/permission_grant: new administrator group and ten global capabilities','systemhaus: revision +1','audit_event: deployment.recover'],limits='Windows11/PowerShell5.1 isolated new native deployments from transported content. Existing compatible system CRT reused. No SCM, clean/other Windows, productive PKI, elevated CRT install, redistribution approval, manual Wascar QA or adoption.')
    report['successfulOperationalRecoveries']=sum(v['script']=='Restore-RackClickPrivateDeployment.ps1' and v['exitCode']==0 for v in getattr(c,'calls',[]))
    native.write(a.evidence/'result.json',report);print(json.dumps({k:report[k] for k in ['testsRun','successful','failures','errors','seconds','inputsUnchanged','ownedProcessesStopped']}))
    return 0 if r.wasSuccessful() and report['inputsUnchanged'] and report['ownedProcessesStopped'] and report['systemCrtDllsAndX64RegistryUnchanged'] and not report['cleanupErrors'] else 1
if __name__=='__main__':raise SystemExit(main())
