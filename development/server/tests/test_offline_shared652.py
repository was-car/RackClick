"""Native schema10 package, immutable publications and operational recovery.

Bundled PowerShell operators own provisioning/backup/restore. Python only drives
HTTP assertions and read-only SQL. The base installation scenario is copied as
source below, with its readiness expectation explicitly changed to schema10.
Historical logs are not inputs and actual QA is never accessed.
"""
import argparse,base64,json,platform,secrets,ssl,subprocess,time,unittest,uuid
from datetime import datetime,timezone
from pathlib import Path
import test_offline_installation as native
sha=native.sha;read=native.read
from pg_support import Client,free_port,NO_WINDOW
from test_private_deployment_flow import NativeServer
from test_private_deployment_recovery import PrivateDeploymentRecovery
from test_private_template_configurations import definition,wire
RESUME_RESULT=None
REMAINING_RESULT=None

class OfflineShared652(native.OfflineInstallation):
    test_transported_package_install_restart_backup_restore=None
    sql=PrivateDeploymentRecovery.sql
    snapshot=PrivateDeploymentRecovery.snapshot

    @classmethod
    def setUpClass(cls):
        cls.calls=[];cls.checkpoints=[];cls.contexts=[];cls.cleanup_errors=[]
        cls.inputs_unchanged=False;cls.owned_processes_stopped=False;cls.system_crt_unchanged=False
        cls.shared_checks=[];cls.negative_checks=[];cls.recovery_snapshot_exact=False;cls.table_digests_before_backup={}
        if RESUME_RESULT is None:
            super().setUpClass()
        else:
            previous=native.read(RESUME_RESULT)
            assert previous['archiveSha256']==native.ARCHIVE_SHA and previous['testsRun']==1
            assert not previous['successful'] and previous['errors']==1 and not previous['failures']
            assert previous['inputsUnchanged'] and previous['ownedProcessesStopped'] and previous['systemCrtDllsAndX64RegistryUnchanged']
            assert not previous['cleanupErrors'] and previous['freshClustersInitialized']==1
            assert previous['calls'][-1]['report']['code']=='installation_prepared'
            assert previous['sharedChecks']==[] and previous['baseProtocolCheckpoints'][-1]['tanda']==359
            assert "NameError: name 'NO_WINDOW' is not defined" in RESUME_RESULT.with_name('tests.log').read_text(encoding='utf-8')
            cls.home=Path(previous['fixture']).resolve(strict=True)
            assert cls.home.parent==native.ROOT/'.local/offline-installation-tests'
            cls.guards=previous['sources'].copy()
            own=Path(__file__).relative_to(native.ROOT).as_posix()
            assert native.sha(RESUME_RESULT.with_name('HARNESS.py'))==cls.guards[own]
            assert all(native.sha(native.ROOT/name)==digest for name,digest in cls.guards.items() if name!=own)
            cls.guards[own]=native.sha(Path(__file__))
            cls.guards[RESUME_RESULT.relative_to(native.ROOT).as_posix()]=native.sha(RESUME_RESULT)
            cls.calls=[];cls.checkpoints=[];cls.launches=[];cls.contexts=[];cls.cleanup_errors=[]
            cls.inputs_unchanged=False;cls.owned_processes_stopped=False;cls.system_crt_unchanged=False
            cls.crt_before=native.system_crt_snapshot();cls.poison_port=free_port()
            cls.installation_root=cls.home/'installed';cls.operator_tools=cls.home/'bootstrap copiado Ω'
            cls.bootstrap_tools=cls.operator_tools;cls.operator_file_count=len(native.NAMES)
            cls.archive=cls.home/'paquete trasladado Ω/RackClick offline Ω.zip'
            assert native.sha(cls.archive)==native.ARCHIVE_SHA
            import zipfile
            with zipfile.ZipFile(cls.archive) as archive:
                cls.bundle=json.loads(archive.read('bundle.json'))
                cls.bundle_manifest_sha=__import__('hashlib').sha256(archive.read('bundle.json')).hexdigest()
            assert not (cls.installation_root/'deployment/instance/pgdata/postmaster.pid').exists()
        cls.shared_checks=[];cls.negative_checks=[]
        cls.recovery_snapshot_exact=False;cls.table_digests_before_backup={}
        for name in ['test_offline_shared652.py','test_private_template_configurations.py']:
            path=Path(__file__).with_name(name);cls.guards[path.relative_to(native.ROOT).as_posix()]=native.sha(path)
        assert cls.bundle['versions']['schema']==10

    def server(self):
        return NativeServer(self.origin,ssl.create_default_context(cafile=str(self.deployment_path/'https/server.pem')))

    def identity(self,client):
        return self.expect(client.request('GET','/api/v1/me'),200).json()['user']['id']

    def admin_write(self,client,path,body,status=200):
        house=self.expect(client.request('GET','/api/v1/systemhaus'),200).json()
        return self.expect(client.request('POST',path,body,{'X-RackClick-Actor':self.identity(client),
            'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),status).json()

    def project(self,client):
        return self.expect(client.request('GET',f'/api/v1/customers/{self.customer_id}/project'),200).json()

    def inventory(self,client,kind,payload,status=200):
        project=self.project(client)
        return self.expect(client.request('POST',f'/api/v1/customers/{self.customer_id}/commands',
            {'type':kind,'payload':payload},{'X-RackClick-Actor':self.identity(client),
            'If-Match':f'"{project["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),status).json()

    def shared_write(self,client,intent,status=200):
        lib=self.expect(client.request('GET',self.shared_path),200).json()
        return self.expect(client.request('POST',self.shared_path,intent,{'X-RackClick-Actor':self.identity(client),
            'If-Match':f'"shared-templates-{lib["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),status).json()

    def checked_backup(self,pg_bin,path):
        self.original_login=native.read(self.instance_path/'private/admin-login.json')
        admin=Client(self.server());self.expect(admin.login(**self.original_login),200)
        self.customer_id=self.expect(admin.request('GET','/api/v1/customers'),200).json()[0]['id']
        self.private_path=f'/api/v1/customers/{self.customer_id}/catalog/private-templates'
        self.shared_path=f'/api/v1/customers/{self.customer_id}/catalog/shared-templates'
        lib=self.expect(admin.request('GET',self.private_path),200).json()
        body,_=wire(definition('dose'),'Configuración transportada Ω😀')
        self.private_receipt=self.expect(admin.request('POST',self.private_path+'/configurations',json.loads(body),
            {'X-RackClick-Actor':self.identity(admin),'If-Match':f'"templates-{lib["revision"]}"',
             'Idempotency-Key':str(uuid.uuid4())}),200).json()
        self.private_id=self.private_receipt['result']['templateId']
        detail=self.expect(admin.request('GET',self.private_path+'/'+self.private_id),200).json()['template']
        self.template_bytes=base64.b64decode(detail['definitionBase64']);self.template_sha=detail['definitionSha256']
        self.assertEqual(json.loads(self.template_bytes),definition('dose'))
        self.technician_login=dict(username='Técnico desde paquete Ω😀',password=secrets.token_hex(32))
        user=self.admin_write(admin,'/api/v1/admin/users',self.technician_login,201)['resource']['id']
        group=self.admin_write(admin,'/api/v1/admin/user-groups',{'name':'Técnicos cliente desde ZIP'},201)['resource']['id']
        self.admin_write(admin,f'/api/v1/admin/user-groups/{group}/members',{'userId':user,'assigned':True})
        for cap in ['inventory.read','inventory.edit']:
            self.admin_write(admin,f'/api/v1/admin/user-groups/{group}/grants',{'grantId':str(uuid.uuid4()),
                'capability':cap,'scope':'customer','targetId':self.customer_id,'assigned':True})
        technician=Client(self.server());self.expect(technician.login(**self.technician_login),200)
        self.expect(technician.request('GET',self.private_path+'/'+self.private_id),404)
        intent=dict(type='publish',privateTemplateId=self.private_id,definitionVersion=1,
            definitionSha256=self.template_sha,name='Compartida activa Ω😀')
        self.shared_write(technician,intent,403)
        self.publications=[]
        for label in ['activa','retirada']:
            result=self.shared_write(admin,{**intent,'name':'Compartida '+label+' Ω😀'})
            self.publications.append(result)
            shared=self.expect(technician.request('GET',self.shared_path+'/'+result['result']['templateId']),200).json()['template']
            self.assertEqual(base64.b64decode(shared['definitionBase64']),self.template_bytes)
        site=self.inventory(technician,'site.create',{'name':'Sitio paquete'})['result']['resourceId']
        building=self.inventory(technician,'building.create',{'name':'Edificio paquete','siteId':site})['result']['resourceId']
        room=self.inventory(technician,'room.create',{'name':'Sala paquete','buildingId':building})['result']['resourceId']
        self.active_id=self.publications[0]['result']['templateId'];self.retired_id=self.publications[1]['result']['templateId']
        payload=dict(templateId=self.active_id,definitionVersion=1,definitionSha256=self.template_sha,kind='dose',
            roomId=room,rackId=None,name='Dose desde otra cuenta Ω😀',color='#12aBcD',poeBudget=None,
            notes=dict(sn='',model='',ip='',firmware='',text=''))
        self.instantiated=self.inventory(technician,'device.createFromSharedTemplate',payload)
        self.shared_write(admin,dict(type='deactivate',templateId=self.retired_id))
        self.inventory(technician,'device.createFromSharedTemplate',{**payload,'templateId':self.retired_id},409)
        project=self.project(technician);device=self.instantiated['result']['resourceId']
        self.assertTrue(any(d['id']==device for d in project['devices']))
        self.assertEqual(self.expect(admin.request('GET',self.private_path+'/'+self.private_id),200).json()['template'],detail)
        self.copied_cookie=technician.cookie
        self.source_identity=native.read(self.instance_path/'instance.json')
        self.source_secrets={p.name:native.sha(p) for p in (self.instance_path/'private').iterdir() if p.is_file()}
        self.source_tls=native.sha(self.deployment_path/'https/server.pfx')
        self.recovery_before=self.snapshot(self.contexts[0]);self.assertEqual(len(self.recovery_before),33)
        self.__class__.table_digests_before_backup=self.recovery_before
        self.assertEqual(self.sql(self.contexts[0],'SELECT string_agg(version::text,\',\' ORDER BY version) FROM schema_migration'),'1,2,3,4,5,6,7,8,9,10')
        self.__class__.shared_checks.append(dict(stage='before_backup',tableCount=33,tenMigrationsExact=True,
            privateDefinitionExact=True,privateOwnerSeparation=True,publishPermissionEnforced=True,
            secondActorInstantiated=True,retiredCopyRejected=True,immutableSourceExact=True))
        return super().checked_backup(pg_bin,path)

    def start(self,number,mode='deployment'):
        process=super().start(number,mode)
        if self.deployment_path.name=='recovered' and hasattr(self,'active_id'):
            current=native.read(self.instance_path/'instance.json')
            for key in ['id','rootPath','postgresPort','database','owner','runtime','clusterAdmin']:
                self.assertNotEqual(current[key],self.source_identity[key])
            for name,digest in self.source_secrets.items():self.assertNotEqual(native.sha(self.instance_path/'private'/name),digest)
            self.assertNotEqual(native.sha(self.deployment_path/'https/server.pfx'),self.source_tls)
            # Snapshot before any login: recovery changes only explicit identity,
            # session removal, house revision and recovery audit rows.
            after=self.snapshot(self.contexts[-1],undo_recovery=True)
            expected={k:v for k,v in self.recovery_before.items() if k!='app_session'}
            self.assertEqual(after,expected)
            self.__class__.recovery_snapshot_exact=True
            old=Client(self.server());old.cookie=self.copied_cookie;self.expect(old.request('GET','/api/v1/me'),401)
            recovered=native.read(self.instance_path/'private/admin-login.json');new_admin=Client(self.server())
            self.expect(new_admin.login(**recovered),200)
            capabilities=self.expect(new_admin.request('GET','/api/v1/admin/capabilities'),200).json()['capabilities']
            self.assertEqual(len(capabilities),10);self.assertIn('templates.publish',capabilities)
            original=Client(self.server());self.expect(original.login(**self.original_login),200)
            tech=Client(self.server());self.expect(tech.login(**self.technician_login),200)
            for publication in self.publications:
                item=self.expect(tech.request('GET',self.shared_path+'/'+publication['result']['templateId']),200).json()['template']
                self.assertEqual(base64.b64decode(item['definitionBase64']),self.template_bytes)
                state=self.expect(original.request('GET',self.shared_path+'/operations/'+publication['requestId']),200).json()
                self.assertEqual(state['state'],'committed');self.assertEqual(state['operation'],publication)
            visible=self.expect(tech.request('GET',self.shared_path),200).json()['templates']
            self.assertEqual([t['id'] for t in visible],[self.active_id])
            self.assertEqual(self.expect(new_admin.request('GET',self.private_path),200).json()['templates'],[])
            self.expect(tech.request('GET',self.private_path+'/'+self.private_id),404)
            self.__class__.shared_checks.append(dict(stage='after_recovery',tableCount=33,
                allRowsExactExceptExplicitRecoveryChanges=True,copiedSessionRevoked=True,
                originalAccountsAndPublicationReceiptsPreserved=True,definitionsByteExact=True,
                activeAndRetiredStateExact=True,newAdminCapabilityCount=10,newAdminPrivateLibrarySeparate=True))
        return process

    def negative_schema9_restore(self):
        # Existing schema9 backup is read-only input, never a live historical DB.
        source=native.ROOT/'evidence/s1-20261018/sesenta-tandas-473-532/packaging/native04/result.json'
        historical=native.read(source);self.assertTrue(historical['successful'])
        backup=Path(historical['fixture'])/'backup instalado Ω'
        self.assertTrue(backup.is_dir());before={p.name:native.sha(p) for p in backup.iterdir() if p.is_file()}
        content=self.installation_root/'content';negative=self.context(self.home/'schema9-rejected')
        args=dict(ManifestPath=content/'application/manifest.json',ExpectedManifestSha256=self.bundle['applicationManifestSha256'],
            ServerPath=content/'application/server',FrontendPath=content/'application/frontend',DotNetPath=self.runtime/'dotnet.exe',
            PostgresBinPath=self.pg_bin,DestinationPath=negative['root'],PostgresPort=negative['pg'],HttpPort=negative['http'],
            BackupPath=backup,ExpectedBackupManifestSha256=native.sha(backup/'manifest.json'),RecoveryUser='No debe crearse')
        denied=self.invoke('Restore-RackClickPrivateDeployment.ps1',args,1)
        self.assertEqual(denied['code'],'instance_restore_restored_schema_required_10')
        self.assertFalse((negative['root']/'deployment.json').exists())
        self.assertFalse((negative['root']/'instance/instance.json').exists())
        self.assertFalse((negative['root']/'instance/pgdata/postmaster.pid').exists())
        self.assertFalse(list((negative['root']/'instance/logs').glob('*recover-admin*')))
        self.assertEqual(before,{p.name:native.sha(p) for p in backup.iterdir() if p.is_file()})
        self.__class__.negative_checks.append(dict(schema9BackupAgainstStage10Rejected=True,
            rejectionAfterPgRestoreBeforeRecoverAdmin=True,partialPreservedWithoutReceipts=True,
            sourceBackupUnchanged=True,ownedPostgresStopped=True,implicitMigration=False))

    def test_transported_schema10_install_restart_shared_backup_restore(self):
        if RESUME_RESULT is None:
            inspected=self.invoke('Test-RackClickOfflineBundle.ps1',dict(ArchivePath=self.archive,ExpectedArchiveSha256=native.ARCHIVE_SHA))
            self.assertEqual(inspected['code'],'bundle_verified');self.assertEqual(inspected['bundleManifestSha256'],self.bundle_manifest_sha)
            source=self.context(self.installation_root/'deployment')
            self.mark(358,transportedZipUnicodePath=True,externalArchiveSha256=native.ARCHIVE_SHA,bootstrapOperators=25,builds=0)
            denied=self.home/'bad-hash';self.invoke('Install-RackClickOfflineBundle.ps1',
                self.install_args(source,ExpectedArchiveSha256='0'*64,DestinationPath=denied),2)
            self.assertFalse(denied.exists())
            sentinel=self.home/'existing';sentinel.mkdir();(sentinel/'keep.txt').write_bytes(b'preserved')
            self.invoke('Install-RackClickOfflineBundle.ps1',self.install_args(source,DestinationPath=sentinel),1)
            self.assertEqual(list(sentinel.iterdir()),[sentinel/'keep.txt']);self.assertEqual((sentinel/'keep.txt').read_bytes(),b'preserved')
            self.mark(359,wrongExternalHashRejectedBeforeCreate=True,existingDestinationUnchanged=True)
            installed=self.invoke('Install-RackClickOfflineBundle.ps1',self.install_args(source))
            self.assertEqual(installed['code'],'installation_prepared');self.assertFalse(installed['rebootRequired'])
            receipt=read(self.installation_root/'installation.json');state=read(self.installation_root/'installation-state.json')
            self.assertEqual(len(receipt),11);self.assertEqual(len(state),4)
            self.assertEqual(state,dict(schemaVersion=1,installationId=receipt['id'],status='prepared',code='installation_prepared'))
            self.assertEqual(receipt['bundleArchiveSha256'],native.ARCHIVE_SHA);self.assertEqual(receipt['bundleManifestSha256'],self.bundle_manifest_sha)
            self.assertEqual(sha(self.installation_root/'installation.json'),installed['installationSha256'])
            self.assertEqual(receipt['deploymentSha256'],installed['deploymentSha256'])
            self.assertEqual(set(p.name for p in self.installation_root.iterdir()),{'content','deployment','logs','installation-state.json','installation.json'})
        else:
            receipt=read(self.installation_root/'installation.json')
            instance=read(self.installation_root/'deployment/instance/instance.json')
            state=read(self.installation_root/'installation-state.json')
            self.assertEqual(state['status'],'prepared')
            self.assertEqual(receipt['bundleArchiveSha256'],native.ARCHIVE_SHA)
            self.assertEqual(receipt['bundleManifestSha256'],self.bundle_manifest_sha)
            source=self.context(self.installation_root/'deployment')
            source.update(pg=instance['postgresPort'],http=instance['httpPort'])
            import socket
            for port in [source['pg'],source['http']]:
                with socket.socket() as connection:self.assertNotEqual(connection.connect_ex(('127.0.0.1',port)),0)
            installed=dict(deploymentSha256=receipt['deploymentSha256'],installationSha256=sha(self.installation_root/'installation.json'),crtDecision='reuse')
        self.activate(source,installed);self.assert_content()
        self.assertFalse((self.instance_path/'pgdata/postmaster.pid').exists())
        content=self.installation_root/'content';self.operator_tools=content/'operators';type(self).operator_tools=self.operator_tools
        self.runtime=content/'dependencies/dotnet';self.pg_bin=content/'dependencies/postgresql/bin'
        p=subprocess.run([str(self.runtime/'dotnet.exe'),'--list-sdks'],capture_output=True,check=True,creationflags=NO_WINDOW,env=self.poisoned_environment())
        self.assertFalse(p.stdout.strip() or p.stderr.strip());self.assertFalse((self.runtime/'sdk').exists())
        self.assertFalse((content/'dependencies/postgresql/pgAdmin 4').exists())
        self.invoke('Test-RackClickPrivateDeployment.ps1',dict(DeploymentPath=self.deployment_path,ExpectedDeploymentSha256=self.deployment_sha))
        deployment=read(self.deployment_path/'deployment.json');instance=read(self.instance_path/'instance.json')
        self.assertEqual(Path(deployment['rootPath']),self.deployment_path)
        self.assertEqual(Path(instance['dotnetPath']),self.runtime/'dotnet.exe')
        self.assertEqual(Path(instance['postgresBinPath']),self.pg_bin)
        self.mark(360,installedOnlyPaths=True,pgStoppedAfterPrepare=True,runtimeWithoutSdk=True,contentHashesExact=True,
            freshPrivateDeployment=True,crtDecision=installed['crtDecision'],realElevatedCrtInstallerExecuted=False)
        credentials=read(self.instance_path/'private/admin-login.json');private_before={p.name:sha(p) for p in (self.instance_path/'private').iterdir()}
        tls_before={p.name:sha(p) for p in (self.deployment_path/'https').iterdir()}
        run=self.start(1);server=NativeServer(self.origin,ssl.create_default_context(cafile=str(self.deployment_path/'https/server.pem')))
        self.assertEqual(self.expect(server.request('GET','/'),200).body,(content/'application/frontend/index.html').read_bytes())
        self.assertEqual(self.expect(server.request('GET','/health/ready'),200).json(),dict(status='ready',schemaVersion=10))
        with self.assertRaises(ssl.SSLCertVerificationError):NativeServer(self.origin,ssl.create_default_context()).request('GET','/health/ready')
        first,second=Client(server),Client(server)
        login=self.expect(first.login(credentials['username'],credentials['password']),200)
        self.assertIn('; secure',login.headers['set-cookie'].lower());self.expect(second.login(credentials['username'],credentials['password']),200)
        self.mark(361,httpsReadiness=True,guiExactPackaged=True,
            guiBundleSha256=sha(content/'application/frontend/app.js'),
            applicationManifestSha256=self.bundle['applicationManifestSha256'],
            unicodeLoginSecureCookie=True,untrustedTlsRejected=True)
        house=self.expect(first.request('GET','/api/v1/systemhaus'),200).json()
        self.expect(first.request('PUT','/api/v1/systemhaus',{'name':'Paquete instalado persistente Ω 😀'},
                    {'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),200)
        house=self.expect(second.request('GET','/api/v1/systemhaus'),200).json();self.assertEqual(house['name'],'Paquete instalado persistente Ω 😀')
        customer=self.expect(first.request('POST','/api/v1/customers',{'name':'Cliente desde ZIP Ω 😀'},
                    {'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),201).json()['resource']
        customers=self.expect(second.request('GET','/api/v1/customers'),200).json();self.assertTrue(any(c['id']==customer['id'] for c in customers))
        self.mark(362,serverCommittedUnicode=True,otherSessionReads=True)
        house=self.expect(first.request('GET','/api/v1/systemhaus'),200).json();actor=self.expect(first.request('GET','/api/v1/me'),200).json()['user']['id']
        reader_password=secrets.token_hex(32)
        self.expect(first.request('POST','/api/v1/admin/users',{'username':'Lectura paquete Ω','password':reader_password},
                    {'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor}),201)
        restricted=Client(server);self.expect(restricted.login('Lectura paquete Ω',reader_password),200)
        self.expect(restricted.request('GET','/api/v1/admin/users'),403)
        self.expect(restricted.request('GET','/api/v1/customers/'+customer['id']+'/project'),404)
        audit=self.expect(first.request('GET','/api/v1/admin/audit'),200).json();self.assertGreaterEqual(len(audit['events']),3)
        committed=self.expect(second.request('GET','/api/v1/systemhaus'),200).json()
        self.mark(363,authorizationOnServer=True,unprivilegedAccountDenied=True,auditPersisted=True)
        self.stop(run);run2=self.start(2)
        self.expect(second.request('GET','/api/v1/me'),200)
        self.assertEqual(self.expect(second.request('GET','/api/v1/systemhaus'),200).json(),committed)
        self.assertEqual(self.expect(second.request('GET','/api/v1/customers'),200).json(),customers)
        self.assertEqual(self.expect(first.request('GET','/api/v1/admin/audit'),200).json(),audit)
        backup=self.home/'backup instalado Ω';self.checked_backup(self.pg_bin,backup)
        # The shared-template hook creates hierarchy/equipment and advances the
        # customer revision. Compare recovery with that committed state.
        customers=self.expect(second.request('GET','/api/v1/customers'),200).json()
        self.stop(run2)
        self.mark(364,confirmedStopRestart=True,sessionDataAuditPersisted=True,bundledPgDumpAndRestoreList=True)
        recovered=self.context(self.home/'recovered')
        args=dict(ManifestPath=content/'application/manifest.json',ExpectedManifestSha256=self.bundle['applicationManifestSha256'],
            ServerPath=content/'application/server',FrontendPath=content/'application/frontend',DotNetPath=self.runtime/'dotnet.exe',PostgresBinPath=self.pg_bin,
            DestinationPath=recovered['root'],PostgresPort=recovered['pg'],HttpPort=recovered['http'],
            BackupPath=backup,ExpectedBackupManifestSha256=sha(backup/'manifest.json'),RecoveryUser='Recuperación paquete Ω')
        restored=self.invoke('Restore-RackClickPrivateDeployment.ps1',args);self.activate(recovered,restored)
        run3=self.start(3);restored_server=NativeServer(self.origin,ssl.create_default_context(cafile=str(self.deployment_path/'https/server.pem')))
        old_cookie=Client(restored_server);old_cookie.cookie=second.cookie;self.expect(old_cookie.request('GET','/api/v1/me'),401)
        new_credentials=read(self.instance_path/'private/admin-login.json');new_admin=Client(restored_server)
        self.expect(new_admin.login(new_credentials['username'],new_credentials['password']),200)
        self.assertFalse(new_credentials['password']==credentials['password'],'Recovery must generate a fresh credential')
        self.assertEqual(self.expect(new_admin.request('GET','/api/v1/customers'),200).json(),customers)
        self.assertEqual(self.expect(new_admin.request('GET','/api/v1/systemhaus'),200).json()['name'],committed['name'])
        original=Client(restored_server);self.expect(original.login(credentials['username'],credentials['password']),200)
        self.stop(run3);self.assert_content()
        self.mark(365,bundledPgRestoreIntoNewCluster=True,newAdminAndTls=True,copiedSessionRevoked=True,originalDataAndAccountPreserved=True)
        self.activate(source)
        self.assertEqual({p.name:sha(p) for p in (self.instance_path/'private').iterdir()},private_before)
        self.assertEqual({p.name:sha(p) for p in (self.deployment_path/'https').iterdir()},tls_before)
        self.assertEqual(sha(self.installation_root/'installation.json'),installed['installationSha256'])

        source_again=self.start(4)
        self.assertEqual(self.snapshot(self.contexts[0]),self.recovery_before)
        self.stop(source_again)
        self.__class__.shared_checks.append(dict(stage='source_after_recovery',all33SourceTablesExact=True,
            originalSecretsTlsReceiptsPreserved=True,originalClusterStopped=True))
        self.negative_schema9_restore()


class OfflineShared652Remaining(OfflineShared652):
    """Only the remaining assertions after native04's successful recovery."""
    test_transported_schema10_install_restart_shared_backup_restore=None

    @classmethod
    def setUpClass(cls):
        cls.calls=[];cls.checkpoints=[];cls.contexts=[];cls.cleanup_errors=[];cls.launches=[]
        cls.inputs_unchanged=False;cls.owned_processes_stopped=False;cls.system_crt_unchanged=False
        cls.shared_checks=[];cls.negative_checks=[];cls.recovery_snapshot_exact=False;cls.table_digests_before_backup={}
        previous=native.read(REMAINING_RESULT)
        assert previous['archiveSha256']==native.ARCHIVE_SHA and previous['testsRun']==1
        assert not previous['successful'] and previous['failures']==1 and not previous['errors']
        assert previous['inputsUnchanged'] and previous['ownedProcessesStopped'] and previous['systemCrtDllsAndX64RegistryUnchanged']
        assert not previous['cleanupErrors'] and previous['freshClustersInitialized']==2
        assert previous['recoverySnapshotExact'] and [v['stage'] for v in previous['sharedChecks']]==['before_backup','after_recovery']
        assert previous['calls'][-1]['report']['code']=='deployment_prepared'
        assert 'Lists differ:' in REMAINING_RESULT.with_name('tests.log').read_text(encoding='utf-8')
        cls.home=Path(previous['fixture']).resolve(strict=True)
        assert cls.home.parent==native.ROOT/'.local/offline-installation-tests'
        cls.guards=previous['sources'].copy();own=Path(__file__).relative_to(native.ROOT).as_posix()
        assert native.sha(REMAINING_RESULT.with_name('HARNESS.py'))==cls.guards[own]
        assert all(native.sha(native.ROOT/name)==digest for name,digest in cls.guards.items() if name!=own)
        cls.guards[own]=native.sha(Path(__file__))
        cls.guards[REMAINING_RESULT.relative_to(native.ROOT).as_posix()]=native.sha(REMAINING_RESULT)
        cls.crt_before=native.system_crt_snapshot();cls.poison_port=free_port()
        cls.installation_root=cls.home/'installed';content=cls.installation_root/'content'
        cls.operator_tools=content/'operators';cls.bootstrap_tools=cls.home/'bootstrap copiado Ω';cls.operator_file_count=len(native.NAMES)
        cls.runtime=content/'dependencies/dotnet';cls.pg_bin=content/'dependencies/postgresql/bin'
        cls.archive=cls.home/'paquete trasladado Ω/RackClick offline Ω.zip'
        assert native.sha(cls.archive)==native.ARCHIVE_SHA
        import zipfile,hashlib,socket
        with zipfile.ZipFile(cls.archive) as archive:
            cls.bundle=json.loads(archive.read('bundle.json'));cls.bundle_manifest_sha=hashlib.sha256(archive.read('bundle.json')).hexdigest()
        installed=next(v['report'] for v in previous['calls'] if v['script']=='Install-RackClickOfflineBundle.ps1' and v['exitCode']==0)
        assert native.sha(cls.installation_root/'installation.json')==installed['installationSha256']
        for folder,receipt in [(cls.installation_root/'deployment',installed),(cls.home/'recovered',previous['calls'][-1]['report'])]:
            assert native.sha(folder/'deployment.json')==receipt['deploymentSha256']
            deployment=native.read(folder/'deployment.json');instance=native.read(folder/'instance/instance.json')
            assert native.sha(folder/'instance/instance.json')==deployment['instanceManifestSha256']
            assert native.read(folder/'deployment-state.json')['status']=='prepared'
            assert not (folder/'instance/pgdata/postmaster.pid').exists()
            for port in [instance['postgresPort'],instance['httpPort']]:
                with socket.socket() as connection:assert connection.connect_ex(('127.0.0.1',port))!=0
            cls.contexts.append(dict(root=folder,pg=instance['postgresPort'],http=instance['httpPort'],
                sha=receipt['deploymentSha256'],instanceSha=deployment['instanceManifestSha256']))
        cls.table_digests_before_backup=previous['tableDigestsBeforeBackup'];assert len(cls.table_digests_before_backup)==33

    def test_remaining_recovered_admin_original_account_source_and_schema_negative(self):
        self.assert_content()
        source,recovered=self.contexts
        self.activate(recovered)
        self.invoke('Test-RackClickPrivateDeployment.ps1',dict(DeploymentPath=self.deployment_path,ExpectedDeploymentSha256=self.deployment_sha))
        run=self.start(10)
        admin=Client(self.server());credentials=native.read(self.instance_path/'private/admin-login.json')
        self.expect(admin.login(**credentials),200)
        customers=self.expect(admin.request('GET','/api/v1/customers'),200).json()
        expected=json.loads(self.sql(recovered,"SELECT jsonb_agg(jsonb_build_object('id',id,'houseId',systemhaus_id,'name',name,'revision',revision) ORDER BY id) FROM customer"))
        self.assertEqual(sorted(customers,key=lambda x:x['id']),expected)
        old=native.read(source['root']/'instance/private/admin-login.json');original=Client(self.server())
        self.expect(original.login(**old),200)
        self.assertEqual(self.expect(original.request('GET','/api/v1/customers'),200).json(),customers)
        self.stop(run)
        self.shared_checks.append(dict(stage='remaining_recovered_reads',newAdminAndOriginalAccountLogin=True,
            customersMatchCurrentCommittedRows=True,sourceRevisionCapturedBeforeSharedHookWasObsolete=True))
        self.activate(source)
        self.invoke('Test-RackClickPrivateDeployment.ps1',dict(DeploymentPath=self.deployment_path,ExpectedDeploymentSha256=self.deployment_sha))
        source_run=self.start(11)
        self.assertEqual(self.snapshot(source),self.table_digests_before_backup)
        source_customers=json.loads(self.sql(source,"SELECT jsonb_agg(jsonb_build_object('id',id,'houseId',systemhaus_id,'name',name,'revision',revision) ORDER BY id) FROM customer"))
        self.assertEqual(sorted(customers,key=lambda x:x['id']),source_customers)
        self.stop(source_run)
        self.shared_checks.append(dict(stage='source_after_recovery',all33SourceTablesExact=True,
            originalSecretsTlsReceiptsPreserved=True,originalClusterStopped=True))
        self.negative_schema9_restore()
        self.assert_content()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--archive-sha',required=True);parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--resume-result',type=Path)
    parser.add_argument('--remaining-result',type=Path)
    global RESUME_RESULT,REMAINING_RESULT
    args=parser.parse_args();native.ARCHIVE=args.archive.resolve(strict=True);native.ARCHIVE_SHA=args.archive_sha
    RESUME_RESULT=args.resume_result.resolve(strict=True) if args.resume_result else None
    REMAINING_RESULT=args.remaining_result.resolve(strict=True) if args.remaining_result else None
    assert not (RESUME_RESULT and REMAINING_RESULT)
    args.evidence.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    with (args.evidence/'tests.log').open('w',encoding='utf-8') as log:
        cls=OfflineShared652Remaining if REMAINING_RESULT else OfflineShared652
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,
        successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),
        sources=getattr(cls,'guards',{}),inputsUnchanged=cls.inputs_unchanged,ownedProcessesStopped=cls.owned_processes_stopped,
        systemCrtDllsAndX64RegistryUnchanged=cls.system_crt_unchanged,cleanupErrors=cls.cleanup_errors,
        archiveSha256=args.archive_sha,resumedFromResult=RESUME_RESULT.relative_to(native.ROOT).as_posix() if RESUME_RESULT else None,
        initialNewInstallationExecutedInPreviousResult=bool(RESUME_RESULT),calls=cls.calls,sharedChecks=cls.shared_checks,negativeChecks=cls.negative_checks,
        continuedPreparedFixturesFromResult=REMAINING_RESULT.relative_to(native.ROOT).as_posix() if REMAINING_RESULT else None,
        newClustersInitializedThisRun=1 if REMAINING_RESULT else None,
        successfulNewInstallCommandsThisRun=sum(v['script']=='Install-RackClickOfflineBundle.ps1' and v['exitCode']==0 for v in cls.calls),
        successfulOperationalRecoveryCommandsThisRun=sum(v['script']=='Restore-RackClickPrivateDeployment.ps1' and v['exitCode']==0 for v in cls.calls),
        recoverySnapshotExact=cls.recovery_snapshot_exact,tableDigestsBeforeBackup=cls.table_digests_before_backup,
        allowedRecoveryChanges=['app_session: copied sessions removed','app_user: new recovery administrator',
            'user_group/user_group_member/permission_grant: new recovery group with ten global capabilities',
            'systemhaus: revision +1, identity and name preserved','audit_event: one deployment.recover record'],
        baseProtocolCheckpoints=cls.checkpoints,
        freshClustersInitialized=sum((v['root']/'instance/pgdata/PG_VERSION').is_file() for v in getattr(cls,'contexts',[])),
        successfulOperationalRecoveries=max(0,sum((v['root']/'instance/instance.json').is_file() for v in getattr(cls,'contexts',[]))-1),
        fixture=str(getattr(cls,'home','uninitialized')),actualQaAccessed=False,pythonProvisioning=False,pythonRestore=False,
        limits='Native Windows11/PowerShell5.1/PG17.11/runtime from content without SDK/dev PATH. Compatible existing system CRT. Two new operational clusters plus one rejected schema9 restore in its own partial cluster before recover-admin. No SCM, clean/other Windows, elevated CRT installation, productive PKI, whole-host recovery, redistribution clearance, manual Wascar QA or adoption.')
    native.write(args.evidence/'result.json',report)
    print(json.dumps({key:report[key] for key in ['testsRun','successful','failures','errors','seconds','inputsUnchanged','ownedProcessesStopped']}))
    return 0 if result.wasSuccessful() and cls.inputs_unchanged and cls.owned_processes_stopped and cls.system_crt_unchanged and not cls.cleanup_errors else 1


if __name__=='__main__':raise SystemExit(main())
