"""One transported1329 Windows New/HTTPS/relationships/Backup/public Restore13 scenario.

Only lifecycle/read-only SQL helpers are reused; no historical test is executed.
No QA data, app builds, SDK installation, DOM, voice, Office or SCM work occurs.
"""
import argparse,hashlib,json,platform,secrets,ssl,subprocess,time,unittest,uuid
from datetime import datetime,timezone
from pathlib import Path
import test_offline_installation as native
from pg_support import Client,NO_WINDOW
from test_private_deployment_flow import NativeServer
from test_offline_relations909 import OfflineRelations909

ROOT=native.ROOT;sha=native.sha;read=native.read
MANIFEST=ROOT/'evidence/s1-20261018/sesenta-tandas-1270-1329/CANDIDATA1329-01.json'
PIN='38bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6'

class OfflineGroupLinks1389(OfflineRelations909):
    test_transported_relations849_https_xls_permissions_restart_backup_restore=None

    @classmethod
    def setUpClass(cls):
        cls.frontend_checks=[];cls.relationship_checks=[];cls.recovery_checks=[]
        cls.table_digests_before_backup={};cls.recovery_snapshot_exact=False
        native.OfflineInstallation.setUpClass.__func__(cls)
        assert sha(MANIFEST)==PIN and cls.bundle['applicationManifestSha256']==PIN and cls.bundle['versions']['schema']==13
        files=[Path(__file__),MANIFEST,Path(__file__).with_name('test_offline_relations909.py'),Path(__file__).with_name('test_offline_onboarding1269.py')]
        cls.guards.update({p.relative_to(ROOT).as_posix():sha(p) for p in files})

    def check_frontend(self,stage,content):
        expected=(content/'application/frontend/app.js').read_bytes()
        actual=self.expect(self.server().request('GET','/app.js'),200).body
        self.assertEqual(actual,expected);self.assertEqual(hashlib.sha256(actual).hexdigest(),read(MANIFEST)['distributions']['frontend']['app.js'])
        for marker in (b'data-relation-open-customer',b'data-relation-open-user',b'data-relation-selection-status'):
            self.assertIn(marker,actual)
        self.frontend_checks.append(dict(stage=stage,httpServedAppJsExact=True,appJsSha256=hashlib.sha256(actual).hexdigest(),relationships1329Transported=True,domExecuted=False,accessibilityTreeInspected=False,screenReaderVoiceTested=False))

    def history_rights(self,c):
        actual=json.loads(self.sql(c,'SELECT json_object_agg(version,digest) FROM schema_migration'))
        expected={str(int(Path(n).name.split('-')[0])):digest.upper() for n,digest in read(MANIFEST)['distributions']['server'].items() if n.startswith('database/')}
        self.assertEqual({k:v.upper() for k,v in actual.items()},expected)
        inst=read(c['root']/'instance/instance.json');runtime=inst['runtime'];owner=inst['owner']
        self.assertEqual(self.sql(c,"SELECT count(*) FROM pg_tables WHERE schemaname='public'"),'39')
        self.assertEqual(self.sql(c,f"SELECT count(*) FROM pg_roles WHERE rolname='{runtime}' AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolbypassrls AND NOT rolreplication"),'1')
        self.assertEqual(self.sql(c,f"SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner<>'{owner}'"),'0')
        self.assertEqual(self.sql(c,f"SELECT count(*) FROM pg_tables WHERE schemaname='public' AND NOT (has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'SELECT') AND has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'INSERT') AND has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'UPDATE') AND has_table_privilege('{runtime}',quote_ident(schemaname)||'.'||quote_ident(tablename),'DELETE'))"),'0')
        return dict(migrations=actual,all39TablesOwnedByNewOwner=True,runtimeNoAdministrativeRoles=True,runtimeCrudAll39Tables=True)

    def effective(self,admin,user):
        snapshot=self.expect(admin.request('GET',f'/api/v1/admin/users/{user}/effective-permissions'),200).json()
        self.assertEqual(snapshot['user']['id'],user);return snapshot

    def relational(self,source):
        tables=['systemhaus','customer','user_group','user_group_member','customer_group','customer_group_member','permission_grant','operation']
        return self.sql(source,' UNION ALL '.join(f"SELECT md5(COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)::text,'')) FROM {table} t" for table in tables))

    def check_relationships(self,admin,source,state,stage):
        before=self.relational(source)
        for session in [admin,state['second']]:
            users=self.expect(session.request('GET','/api/v1/admin/user-groups'),200).json()
            customers=self.expect(session.request('GET','/api/v1/admin/customer-groups'),200).json()
            self.assertEqual(users['revision'],customers['revision'])
            ug={x['id']:x for x in users['groups']};cg={x['id']:x for x in customers['groups']}
            self.assertEqual(ug[state['group']]['name'],ug[state['homonym']]['name'])
            self.assertEqual(cg[state['customerGroup']]['name'],cg[state['otherCustomerGroup']]['name'])
            for group in [state['group'],state['homonym']]:
                targets=[p['target']['id'] for p in ug[group]['grants'] if p['scope']=='customerGroup']
                self.assertEqual(targets,[state['customerGroup']])
            for group in [state['customerGroup'],state['otherCustomerGroup']]:
                self.assertEqual([x['id'] for x in cg[group]['customers']],[state['customer']])
            inverse=lambda target:sorted(g['id'] for g in ug.values() if any(p['scope']=='customerGroup' and p['target']['id']==target for p in g['grants']))
            self.assertEqual(inverse(state['customerGroup']),sorted([state['group'],state['homonym']]))
            self.assertEqual(inverse(state['otherCustomerGroup']),[])
            self.assertEqual([x['id'] for x in ug[state['group']]['members']],[state['user']])
            self.assertEqual(ug[state['homonym']]['members'],[])
        self.assertEqual(self.relational(source),before)
        self.relationship_checks.append(dict(stage=stage,twoAdminSessionsReadSameCommittedRevision=True,homonymousUserGroupsAndCustomerGroupsDistinctUuids=True,explicitCustomerGroupTargetsAndInverseSourcesExact=True,sharedCustomerDoesNotInferGrantToOtherGroup=True,eightGroupTablesUnchangedByReadStage=True,apiProtocolOnly=True,domExecuted=False))

    def exercise_administration(self,admin,second,source):
        customer=self.admin_write(admin,'/api/v1/customers',{'name':'Cliente1389 literal <b> 東京'},201)['resource']['id']
        hidden=self.admin_write(admin,'/api/v1/customers',{'name':'Cliente ajeno1389'},201)['resource']['id']
        credentials=dict(username='Lector1389 Ω東京😀',password=secrets.token_hex(32))
        made=self.admin_write(admin,'/api/v1/admin/users',credentials,201);user=made['resource']['id']
        self.assertNotIn(credentials['password'],json.dumps(made))
        account=Client(self.server());self.expect(account.login(**credentials),200)
        self.assertEqual(self.effective(admin,user)['permissions'],dict(systemhausCapabilities=[],customers=[],sources=[]))
        self.assertEqual(self.expect(account.request('GET','/api/v1/customers'),200).json(),[])
        group_name='Grupo homónimo1389 <img> 東京'
        group=self.admin_write(admin,'/api/v1/admin/user-groups',{'name':group_name},201)['resource']['id']
        homonym=self.admin_write(admin,'/api/v1/admin/user-groups',{'name':group_name},201)['resource']['id'];self.assertNotEqual(group,homonym)
        customer_group_name='Clientes homónimos1389 Ω'
        customer_group=self.admin_write(admin,'/api/v1/admin/customer-groups',{'name':customer_group_name},201)['resource']['id']
        other_customer_group=self.admin_write(admin,'/api/v1/admin/customer-groups',{'name':customer_group_name},201)['resource']['id'];self.assertNotEqual(customer_group,other_customer_group)
        for cg in [customer_group,other_customer_group]:self.admin_write(admin,f'/api/v1/admin/customer-groups/{cg}/members',dict(customerId=customer,assigned=True))
        for ug in [group,homonym]:self.admin_write(admin,f'/api/v1/admin/user-groups/{ug}/grants',dict(scope='customerGroup',targetId=customer_group,assigned=True,grantId=str(uuid.uuid4()),capability='inventory.read'))
        self.admin_write(admin,f'/api/v1/admin/user-groups/{group}/grants',dict(scope='systemhaus',targetId=None,assigned=True,grantId=str(uuid.uuid4()),capability='systemhaus.read'))
        self.admin_write(admin,f'/api/v1/admin/user-groups/{group}/grants',dict(scope='customer',targetId=customer,assigned=True,grantId=str(uuid.uuid4()),capability='inventory.read'))
        self.assertEqual(self.effective(second,user)['permissions']['sources'],[])
        self.admin_write(admin,f'/api/v1/admin/user-groups/{group}/members',dict(userId=user,assigned=True))
        effective=self.effective(second,user)
        self.assertEqual(effective['permissions']['systemhausCapabilities'],['systemhaus.read'])
        self.assertEqual(effective['permissions']['customers'],[dict(customerId=customer,capabilities=['inventory.read','systemhaus.read'])])
        state=dict(credentials=credentials,user=user,customer=customer,hidden=hidden,group=group,homonym=homonym,customerGroup=customer_group,otherCustomerGroup=other_customer_group,effective=effective,account=account,second=second)
        self.check_relationships(admin,source,state,'installed')
        self.assertEqual([x['id'] for x in self.expect(account.request('GET','/api/v1/customers'),200).json()],[customer])
        self.expect(account.request('GET',f'/api/v1/customers/{hidden}/project'),404)
        self.expect(account.request('GET','/api/v1/admin/user-groups'),403)
        self.expect(account.request('GET','/api/v1/admin/customer-groups'),403)
        self.expect(account.request('GET',f'/api/v1/admin/users/{user}/effective-permissions'),403)
        project=self.project(account,customer)
        self.expect(account.request('POST',f'/api/v1/customers/{customer}/commands',{'type':'site.create','payload':{'name':'Denied1389'}},{'X-RackClick-Actor':user,'If-Match':f'"{project["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),403)
        audit=self.expect(admin.request('GET','/api/v1/admin/audit'),200).json();self.assertNotIn(credentials['password'],json.dumps(audit));state['audit']=audit
        self.relationship_checks.append(dict(stage='server_authority',newAccountInitiallyUngroupedAndNoCapabilities=True,groupGrantAloneDoesNotAssignMembership=True,onlyExplicitMemberHasCustomerRead=True,readerBothAdminGroupApis403=True,readerWrite403=True,outsideCustomer404=True,passwordAbsentFromReceiptAndAudit=True))
        return state

    def verify_account(self,admin,account,state,revision_offset=0):
        actual=self.effective(admin,state['user']);expected=dict(state['effective']);expected['revision']+=revision_offset
        self.assertEqual(actual,expected)
        self.assertEqual([c['id'] for c in self.expect(account.request('GET','/api/v1/customers'),200).json()],[state['customer']])
        self.expect(account.request('GET',f'/api/v1/customers/{state["hidden"]}/project'),404)
        self.expect(account.request('GET','/api/v1/admin/user-groups'),403)
        self.expect(account.request('GET','/api/v1/admin/customer-groups'),403)

    def test_public_zip_new_relations_https_restart_backup_restore_39_tables(self):
        inspected=self.invoke('Test-RackClickOfflineBundle.ps1',dict(ArchivePath=self.archive,ExpectedArchiveSha256=native.ARCHIVE_SHA));self.assertEqual(inspected['code'],'bundle_verified')
        source=self.context(self.installation_root/'deployment')
        denied=self.home/'bad-hash';self.invoke('Install-RackClickOfflineBundle.ps1',self.install_args(source,ExpectedArchiveSha256='0'*64,DestinationPath=denied),2);self.assertFalse(denied.exists())
        installed=self.invoke('Install-RackClickOfflineBundle.ps1',self.install_args(source,Mode='New'));self.assertEqual(installed['code'],'installation_prepared')
        self.activate(source,installed);self.assert_content();self.assertFalse((self.instance_path/'pgdata/postmaster.pid').exists())
        content=self.installation_root/'content';self.operator_tools=content/'operators';type(self).operator_tools=self.operator_tools
        self.runtime=content/'dependencies/dotnet';self.pg_bin=content/'dependencies/postgresql/bin'
        sdks=subprocess.run([str(self.runtime/'dotnet.exe'),'--list-sdks'],capture_output=True,check=True,creationflags=NO_WINDOW,env=self.poisoned_environment())
        self.assertFalse(sdks.stdout.strip() or sdks.stderr.strip());self.assertFalse((self.runtime/'sdk').exists())
        self.invoke('Test-RackClickPrivateDeployment.ps1',dict(DeploymentPath=self.deployment_path,ExpectedDeploymentSha256=self.deployment_sha))
        original_login=read(self.instance_path/'private/admin-login.json');identity=read(self.instance_path/'instance.json')
        private_before={p.name:sha(p) for p in (self.instance_path/'private').iterdir() if p.is_file()};tls_before={p.name:sha(p) for p in (self.deployment_path/'https').iterdir()}
        run=self.start(1);server=self.server();self.assertEqual(self.expect(server.request('GET','/health/ready'),200).json(),dict(status='ready',schemaVersion=13))
        self.assertEqual(self.expect(server.request('GET','/'),200).body,(content/'application/frontend/index.html').read_bytes());self.check_frontend('installed',content)
        with self.assertRaises(ssl.SSLCertVerificationError):NativeServer(self.origin,ssl.create_default_context()).request('GET','/health/ready')
        admin,second=Client(server),Client(server);login=self.expect(admin.login(**original_login),200);self.assertIn('; secure',login.headers['set-cookie'].lower());self.expect(second.login(**original_login),200)
        state=self.exercise_administration(admin,second,source);rights=self.history_rights(source);copied_cookie=state['account'].cookie
        self.stop(run);run2=self.start(2);self.expect(second.request('GET','/api/v1/me'),200);self.verify_account(second,state['account'],state)
        self.assertEqual(self.expect(admin.request('GET','/api/v1/admin/audit'),200).json(),state['audit']);self.check_relationships(admin,source,state,'restarted')
        before=self.snapshot(source);self.assertEqual(len(before),39);type(self).table_digests_before_backup=before
        backup=self.home/'backup relationships1389 Ω';self.checked_backup(self.pg_bin,backup);self.assertEqual(self.snapshot(source),before);self.stop(run2)
        self.relationship_checks.append(dict(stage='restart_backup',sessionsPersistSourceRestart=True,accountsMembershipGrantAndEffectivePermissionsPersist=True,auditExactAfterRestart=True,all39SourceTablesUnchangedByBackup=True,historyAndRights=rights))
        recovered=self.context(self.home/'restored-installation/deployment')
        restored=self.invoke('Install-RackClickOfflineBundle.ps1',self.restore_args(recovered,backup));self.assertEqual(restored['code'],'installation_prepared')
        receipt=read(recovered['root'].parent/'installation.json');self.assertEqual(receipt['schemaVersion'],2);self.assertEqual(receipt['bundleArchiveSha256'],native.ARCHIVE_SHA)
        self.assertEqual(receipt['recovery']['backupManifestSha256'],sha(backup/'manifest.json'));self.assertEqual(sha(recovered['root'].parent/'installation.json'),restored['installationSha256'])
        restored_content=recovered['root'].parent/'content'
        for name,item in self.bundle['files'].items():self.assertEqual(sha(restored_content/name),item['sha256'])
        self.activate(recovered,restored);self.operator_tools=restored_content/'operators';type(self).operator_tools=self.operator_tools;self.runtime=restored_content/'dependencies/dotnet';self.pg_bin=restored_content/'dependencies/postgresql/bin'
        current=read(self.instance_path/'instance.json')
        for field in ['id','rootPath','postgresPort','database','owner','runtime','clusterAdmin']:self.assertNotEqual(current[field],identity[field])
        for name,digest in private_before.items():self.assertNotEqual(sha(self.instance_path/'private'/name),digest)
        self.assertNotEqual(sha(self.deployment_path/'https/server.pfx'),tls_before['server.pfx'])
        run3=self.start(3);self.check_frontend('restored',restored_content)
        self.assertEqual(self.snapshot(recovered,undo_recovery=True),{k:v for k,v in before.items() if k!='app_session'});self.assertEqual(self.sql(recovered,'SELECT count(*) FROM app_session'),'0');type(self).recovery_snapshot_exact=True
        recovered_rights=self.history_rights(recovered);self.assertTrue(list((self.instance_path/'logs').glob('*recover-admin*')))
        audit=json.loads(self.sql(recovered,"SELECT after_json FROM audit_event WHERE action='deployment.recover'"));self.assertEqual(audit['sourceBackupManifestSha256'],sha(backup/'manifest.json'));self.assertGreater(audit['revokedSessions'],0)
        old=Client(self.server());old.cookie=copied_cookie;self.expect(old.request('GET','/api/v1/me'),401)
        new_login=read(self.instance_path/'private/admin-login.json');self.assertNotEqual(new_login['password'],original_login['password'])
        recovery_admin=Client(self.server());self.expect(recovery_admin.login(**new_login),200)
        original=Client(self.server());self.expect(original.login(**original_login),200)
        account=Client(self.server());self.expect(account.login(**state['credentials']),200);self.verify_account(original,account,state,revision_offset=1);state['second']=recovery_admin;self.check_relationships(original,recovered,state,'restored')
        self.assertEqual(len(self.expect(recovery_admin.request('GET','/api/v1/admin/capabilities'),200).json()['capabilities']),10)
        self.recovery_checks.append(dict(publicInstallerModeRestoreReallyExecuted=True,installationReceiptLinkedToBackupAndArchive=True,recoverAdmin13ReallyExecuted=True,all39TablesExactExceptExplicitRecoveryChanges=True,newRolesDatabaseSecretsTls=True,copiedSessionsRevoked=True,recoveryAuditBackupHashAndRevocationCountExplicit=True,originalAccountsCredentialsMembershipsGrantsAndEffectivePermissionsPreserved=True,recoveryAdministratorTenCapabilities=True,historyAndRights=recovered_rights))
        self.stop(run3);self.activate(source);self.operator_tools=content/'operators';type(self).operator_tools=self.operator_tools;self.runtime=content/'dependencies/dotnet';self.pg_bin=content/'dependencies/postgresql/bin'
        self.assertEqual({p.name:sha(p) for p in (self.instance_path/'private').iterdir() if p.is_file()},private_before);self.assertEqual({p.name:sha(p) for p in (self.deployment_path/'https').iterdir()},tls_before)
        run4=self.start(4);self.assertEqual(self.snapshot(source),before);self.stop(run4)
        self.assertEqual(sha(self.installation_root/'installation.json'),installed['installationSha256']);self.assert_content()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path,required=True);ap.add_argument('--archive-sha',required=True);ap.add_argument('--evidence',type=Path,required=True);args=ap.parse_args()
    native.ARCHIVE=args.archive.resolve(strict=True);native.ARCHIVE_SHA=args.archive_sha;args.evidence.mkdir(parents=True,exist_ok=False)
    (args.evidence/'HARNESS.py').write_bytes(Path(__file__).read_bytes());started=time.monotonic();cls=OfflineGroupLinks1389;cls.evidence=args.evidence
    with (args.evidence/'tests.log').open('x',encoding='utf-8') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),sources=getattr(cls,'guards',{}),inputsUnchanged=getattr(cls,'inputs_unchanged',False),ownedProcessesStopped=getattr(cls,'owned_processes_stopped',False),systemCrtDllsAndX64RegistryUnchanged=getattr(cls,'system_crt_unchanged',False),cleanupErrors=getattr(cls,'cleanup_errors',[]),archiveSha256=args.archive_sha,applicationManifestSha256=PIN,calls=getattr(cls,'calls',[]),frontendTransportChecks=cls.frontend_checks,relationshipChecks=cls.relationship_checks,recoveryChecks=cls.recovery_checks,recoverySnapshotExact=cls.recovery_snapshot_exact,tableDigestsBeforeBackup=cls.table_digests_before_backup,fixture=str(getattr(cls,'home','uninitialized')),freshClustersInitialized=sum((c['root']/'instance/pgdata/PG_VERSION').is_file() for c in getattr(cls,'contexts',[])),actualQaAccessed=False,pythonProvisioning=False,pythonRestore=False,applicationBuilds=0,frontendBuilds=0,allowedRecoveryChanges=['app_session: removed','app_user: new recovery administrator','user_group/user_group_member/permission_grant: new administrator group and ten global capabilities','systemhaus: revision +1','audit_event: deployment.recover'],limits='Windows11/PowerShell5.1 isolated native New/public Restore13 from transported ZIP. Compatible host CRT reused. No SCM, clean/other Windows, productive PKI, elevated CRT install, redistribution approval, manual Wascar QA or adoption. JavaScript transport only; no DOM/AX/voice/Office. Native lifecycle helpers1269 reused; relations scenario new. Prior onboarding/palettes/expiry suites not rerun: server1089/schema13/SQL/deps exact.')
    report['successfulOperationalRecoveries']=sum(bool(c['script']=='Install-RackClickOfflineBundle.ps1' and c['exitCode']==0 and c['report'].get('sourceBackupManifestSha256')) for c in getattr(cls,'calls',[]))
    native.write(args.evidence/'result.json',report);print(json.dumps({k:report[k] for k in ['testsRun','successful','failures','errors','seconds','inputsUnchanged','ownedProcessesStopped']}))
    return 0 if result.wasSuccessful() and report['inputsUnchanged'] and report['ownedProcessesStopped'] and report['systemCrtDllsAndX64RegistryUnchanged'] and not report['cleanupErrors'] else 1
if __name__=='__main__':raise SystemExit(main())
