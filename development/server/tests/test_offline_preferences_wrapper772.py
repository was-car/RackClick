"""Focused package wrapper Restore11 from an already tested ZIP and backup11.

No New installation or historical suite repeated. A third successful deployment
uses another fresh ROOT/cluster, native bundled wrapper and recover-admin11.
"""
import argparse,json,platform,subprocess,time,unittest
from datetime import datetime,timezone
from pathlib import Path
import test_offline_installation as native
from test_offline_preferences772 import OfflinePreferences772,PIN,ROOT,sha,read
from pg_support import Client,NO_WINDOW,free_port
SOURCE_RESULT=None
REMAINING_RESULT=None
class WrapperRestore772(OfflinePreferences772):
    test_schema11_transported_new_https_preferences_restart_backup_restore=None
    @classmethod
    def setUpClass(cls):
        cls.wrapper_checks=[];cls.recovery_snapshot_exact=False
        native.OfflineInstallation.setUpClass.__func__(cls)
        previous=read(SOURCE_RESULT);assert previous['successful'] and previous['recoverySnapshotExact']
        assert previous['inputsUnchanged'] and previous['ownedProcessesStopped'] and not previous['cleanupErrors']
        assert previous['archiveSha256']==native.ARCHIVE_SHA and previous['applicationManifestSha256']==PIN
        for name,digest in previous['sources'].items():assert sha(ROOT/name)==digest
        cls.original_home=Path(previous['fixture']).resolve(strict=True)
        assert cls.original_home.parent==ROOT/'.local/offline-installation-tests'
        cls.backup=cls.original_home/'backup11 instalado Ω';cls.expected_tables=previous['tableDigestsBeforeBackup'];assert len(cls.expected_tables)==35
        source=cls.original_home/'installed/deployment';assert not (source/'instance/pgdata/postmaster.pid').exists()
        cls.original_login=read(source/'instance/private/admin-login.json')
        cls.original_identity=read(source/'instance/instance.json')
        cls.source_static={p:sha(p) for p in [source/'instance/instance.json',source/'deployment.json',source/'instance/private/admin-login.json',*(cls.backup.iterdir())] if p.is_file()}
        cls.guards.update({p.relative_to(ROOT).as_posix():digest for p,digest in cls.source_static.items()})
        cls.guards.update({p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),Path(__file__).with_name('test_offline_preferences772.py'),SOURCE_RESULT]})

    def test_only_package_restore11_receipt_https_admin_preferences_and_stop(self):
        context=self.context(self.installation_root/'deployment')
        result=self.invoke('Install-RackClickOfflineBundle.ps1',dict(Mode='Restore',ArchivePath=self.archive,
            ExpectedArchiveSha256=native.ARCHIVE_SHA,DestinationPath=self.installation_root,PostgresPort=context['pg'],
            HttpPort=context['http'],BackupPath=self.backup,ExpectedBackupManifestSha256=sha(self.backup/'manifest.json'),RecoveryUser='Wrapper recuperación11 Ω😀'))
        self.assertEqual(result['code'],'installation_prepared');receipt=read(self.installation_root/'installation.json')
        self.assertEqual(receipt['schemaVersion'],2);self.assertEqual(len(receipt),12)
        self.assertEqual(receipt['recovery'],dict(backupManifestSha256=sha(self.backup/'manifest.json'),auditEventId=result['recoveryAuditEventId']))
        self.assertEqual(receipt['bundleArchiveSha256'],native.ARCHIVE_SHA);self.assertEqual(sha(self.installation_root/'installation.json'),result['installationSha256'])
        self.activate(context,result);self.assert_content();content=self.installation_root/'content'
        self.operator_tools=content/'operators';type(self).operator_tools=self.operator_tools
        self.runtime=content/'dependencies/dotnet';self.pg_bin=content/'dependencies/postgresql/bin'
        sdks=subprocess.run([str(self.runtime/'dotnet.exe'),'--list-sdks'],capture_output=True,check=True,creationflags=NO_WINDOW,env=self.poisoned_environment())
        self.assertFalse(sdks.stdout.strip() or sdks.stderr.strip());self.assertFalse((self.runtime/'sdk').exists())
        current=read(self.instance_path/'instance.json')
        for name in ['id','rootPath','database','owner','runtime','clusterAdmin','postgresPort']:self.assertNotEqual(current[name],self.original_identity[name])
        self.assertFalse((self.instance_path/'pgdata/postmaster.pid').exists())
        run=self.start(1)
        self.assertEqual(self.expect(self.server().request('GET','/health/ready'),200).json(),dict(status='ready',schemaVersion=11))
        before=self.snapshot(context,undo_recovery=True);self.assertEqual(before,{k:v for k,v in self.expected_tables.items() if k!='app_session'})
        self.assertEqual(self.sql(context,'SELECT count(*) FROM app_session'),'0');type(self).recovery_snapshot_exact=True
        rights=self.check_history_rights(context)
        self.assertTrue(list((self.instance_path/'logs').glob('*recover-admin*')))
        audit=json.loads(self.sql(context,f"SELECT after_json::text FROM audit_event WHERE id='{receipt['recovery']['auditEventId']}'"))
        self.assertEqual(audit['sourceBackupManifestSha256'],sha(self.backup/'manifest.json'));self.assertGreater(audit['revokedSessions'],0)
        credentials=read(self.instance_path/'private/admin-login.json');self.assertNotEqual(credentials['password'],self.original_login['password'])
        new=Client(self.server());self.expect(new.login(**credentials),200)
        prefs=self.prefs(new);self.assertEqual((prefs['revision'],prefs['language'],prefs['theme']),(0,None,None))
        capabilities=self.expect(new.request('GET','/api/v1/admin/capabilities'),200).json()['capabilities'];self.assertEqual(len(capabilities),10);self.assertIn('templates.publish',capabilities)
        original=Client(self.server());self.expect(original.login(**self.original_login),200)
        prefs=self.prefs(original);self.assertEqual((prefs['revision'],prefs['language'],prefs['theme']),(2,'es','light'))
        operations=json.loads(self.sql(context,f"SELECT jsonb_agg(jsonb_build_object('request',request_id,'state',state,'result',result_json)) FROM user_preference_operation WHERE owner_id='{self.actor(original)}'"))
        self.assertEqual(len(operations),3)
        for operation in operations:
            terminal=self.terminal(original,operation['request'])
            if operation['state']=='committed':self.assertEqual(terminal['operation'],json.loads(operation['result']))
            else:
                fence=json.loads(operation['result'])
                self.assertEqual(terminal,{k:fence[k] for k in ['state','ownerId','revision','requestId','operation']})
        self.stop(run);self.assert_content();self.assertTrue(all(sha(p)==h for p,h in self.source_static.items()))
        self.wrapper_checks.append(dict(mode='Restore',receiptSchema=2,wrapperReallyExecuted=True,recoverAdmin11ReallyExecuted=True,httpsReadiness11=True,runtimeWithoutSdk=True,all35TablesExactExceptExplicitRecoveryChanges=True,originalPreferencesReceiptsFenceExact=True,newAdministratorPreferencesEmpty=True,allCopiedSessionsRemovedBeforeLogin=True,revokedSessions=audit['revokedSessions'],copiedCookieHttpReplayed=False,copiedCookieLimit='Not exported from previous fixture; HTTP invalidation covered by native base protocol.',newRuntimeOwnerDatabaseAndSecrets=True,templatesPublishIncluded=True,sourceAndBackupUnchanged=True,historyAndRights=rights))

class WrapperRestore772Remaining(WrapperRestore772):
    """Only finish assertions after successful wrapper/CLI and normalized35 check."""
    test_only_package_restore11_receipt_https_admin_preferences_and_stop=None
    @classmethod
    def setUpClass(cls):
        cls.calls=[];cls.checkpoints=[];cls.contexts=[];cls.launches=[];cls.cleanup_errors=[];cls.wrapper_checks=[]
        cls.inputs_unchanged=False;cls.owned_processes_stopped=False;cls.system_crt_unchanged=False
        previous=read(REMAINING_RESULT);assert not previous['successful'] and previous['failures']==1 and previous['errors']==0
        assert previous['inputsUnchanged'] and previous['ownedProcessesStopped'] and previous['systemCrtDllsAndX64RegistryUnchanged'] and not previous['cleanupErrors']
        assert previous['recoverySnapshotExact'] and previous['archiveSha256']==native.ARCHIVE_SHA
        assert len(previous['calls'])==1 and previous['calls'][0]['script']=='Install-RackClickOfflineBundle.ps1' and previous['calls'][0]['exitCode']==0
        assert 'operationId' in REMAINING_RESULT.with_name('tests.log').read_text(encoding='utf-8')
        cls.guards=previous['sources'].copy();own=Path(__file__).relative_to(ROOT).as_posix()
        assert sha(REMAINING_RESULT.with_name('HARNESS.py'))==cls.guards[own]
        assert all(sha(ROOT/n)==h for n,h in cls.guards.items() if n!=own)
        cls.guards[own]=sha(Path(__file__));cls.guards[REMAINING_RESULT.relative_to(ROOT).as_posix()]=sha(REMAINING_RESULT)
        cls.home=Path(previous['fixture']).resolve(strict=True);assert cls.home.parent==ROOT/'.local/offline-installation-tests'
        cls.crt_before=native.system_crt_snapshot();cls.poison_port=free_port();cls.installation_root=cls.home/'installed'
        content=cls.installation_root/'content';cls.operator_tools=content/'operators';cls.bootstrap_tools=cls.home/'bootstrap copiado Ω';cls.operator_file_count=len(native.NAMES)
        cls.runtime=content/'dependencies/dotnet';cls.pg_bin=content/'dependencies/postgresql/bin'
        cls.archive=cls.home/'paquete trasladado Ω/RackClick offline Ω.zip';assert sha(cls.archive)==native.ARCHIVE_SHA
        import zipfile
        with zipfile.ZipFile(cls.archive) as archive:
            raw=archive.read('bundle.json');cls.bundle=json.loads(raw);cls.bundle_manifest_sha=__import__('hashlib').sha256(raw).hexdigest()
        source=read(SOURCE_RESULT);cls.original_home=Path(source['fixture']);cls.backup=cls.original_home/'backup11 instalado Ω'
        cls.original_login=read(cls.original_home/'installed/deployment/instance/private/admin-login.json')
        cls.source_static={ROOT/n:h for n,h in cls.guards.items() if str(cls.original_home).replace('\\','/') in str(ROOT/n).replace('\\','/')}
        dep=cls.installation_root/'deployment';manifest=read(dep/'deployment.json');instance=read(dep/'instance/instance.json')
        cls.contexts=[dict(root=dep,pg=instance['postgresPort'],http=instance['httpPort'],sha=previous['calls'][0]['report']['deploymentSha256'],instanceSha=manifest['instanceManifestSha256'])]
        assert sha(dep/'deployment.json')==cls.contexts[0]['sha'] and sha(dep/'instance/instance.json')==manifest['instanceManifestSha256']
        assert not (dep/'instance/pgdata/postmaster.pid').exists();cls.recovery_snapshot_exact=True

    def test_remaining_projected_fence_receipts_preferences_and_clean_stop(self):
        context=self.contexts[0];self.activate(context);self.assert_content();run=self.start(2)
        self.assertEqual(self.expect(self.server().request('GET','/health/ready'),200).json(),dict(status='ready',schemaVersion=11))
        original=Client(self.server());self.expect(original.login(**self.original_login),200)
        prefs=self.prefs(original);self.assertEqual((prefs['revision'],prefs['language'],prefs['theme']),(2,'es','light'))
        operations=json.loads(self.sql(context,f"SELECT jsonb_agg(jsonb_build_object('request',request_id,'state',state,'result',result_json)) FROM user_preference_operation WHERE owner_id='{self.actor(original)}'"))
        self.assertEqual(len(operations),3)
        for operation in operations:
            terminal=self.terminal(original,operation['request']);internal=json.loads(operation['result'])
            if operation['state']=='committed':self.assertEqual(terminal['operation'],internal)
            else:self.assertEqual(terminal,{k:internal[k] for k in ['state','ownerId','revision','requestId','operation']})
        new=Client(self.server());self.expect(new.login(**read(self.instance_path/'private/admin-login.json')),200)
        prefs=self.prefs(new);self.assertEqual((prefs['revision'],prefs['language'],prefs['theme']),(0,None,None))
        caps=self.expect(new.request('GET','/api/v1/admin/capabilities'),200).json()['capabilities'];self.assertEqual(len(caps),10);self.assertIn('templates.publish',caps)
        self.stop(run);self.assert_content();self.assertTrue(all(sha(p)==h for p,h in self.source_static.items()))
        self.wrapper_checks.append(dict(stage='remaining',reusedOnlyOwnStoppedPreparedFixture=True,noNewOrRestoreRepeated=True,httpsReadiness11=True,originalPreferencesReceiptsAndProjectedFenceExact=True,newAdministratorPreferencesEmpty=True,templatesPublishIncluded=True,sourceAndBackupUnchanged=True))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path,required=True);ap.add_argument('--archive-sha',required=True);ap.add_argument('--source-result',type=Path,required=True);ap.add_argument('--remaining-result',type=Path);ap.add_argument('--evidence',type=Path,required=True);a=ap.parse_args()
    global SOURCE_RESULT,REMAINING_RESULT
    SOURCE_RESULT=a.source_result.resolve(strict=True);REMAINING_RESULT=a.remaining_result.resolve(strict=True) if a.remaining_result else None;native.ARCHIVE=a.archive.resolve(strict=True);native.ARCHIVE_SHA=a.archive_sha;a.evidence.mkdir(parents=True,exist_ok=False)
    (a.evidence/'HARNESS.py').write_bytes(Path(__file__).read_bytes());started=time.monotonic();c=WrapperRestore772Remaining if REMAINING_RESULT else WrapperRestore772
    with (a.evidence/'tests.log').open('x',encoding='utf-8') as log:r=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(c))
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=r.testsRun,successful=r.wasSuccessful(),failures=len(r.failures),errors=len(r.errors),seconds=round(time.monotonic()-started,3),sources=getattr(c,'guards',{}),inputsUnchanged=c.inputs_unchanged,ownedProcessesStopped=c.owned_processes_stopped,systemCrtDllsAndX64RegistryUnchanged=c.system_crt_unchanged,cleanupErrors=c.cleanup_errors,archiveSha256=a.archive_sha,sourceResult=SOURCE_RESULT.relative_to(ROOT).as_posix(),calls=c.calls,wrapperChecks=c.wrapper_checks,recoverySnapshotExact=c.recovery_snapshot_exact,freshClustersInitialized=sum((v['root']/'instance/pgdata/PG_VERSION').is_file() for v in c.contexts),successfulOperationalRecoveries=sum(v['script']=='Install-RackClickOfflineBundle.ps1' and v['exitCode']==0 for v in c.calls),fixture=str(c.home),actualQaAccessed=False,applicationBuilds=0,frontendBuilds=0,newModeExecutions=0,limits='Focused ModeRestore11 wrapper from tested archive+backup, fresh ROOT. No repeated New, SCM, clean/other Windows, productive PKI, elevated CRT installation, Wascar QA or adoption.')
    report['continuedPreparedFixtureFromResult']=REMAINING_RESULT.relative_to(ROOT).as_posix() if REMAINING_RESULT else None
    report['wrapperModeRestoreExecutedInPreviousResult']=bool(REMAINING_RESULT)
    report['freshClustersInitializedThisRun']=0 if REMAINING_RESULT else report['freshClustersInitialized']
    report['recoverySnapshotExactObservedInPreviousResult']=bool(REMAINING_RESULT)
    native.write(a.evidence/'result.json',report);print(json.dumps({k:report[k] for k in ['testsRun','successful','failures','errors','seconds','inputsUnchanged','ownedProcessesStopped']}))
    return 0 if r.wasSuccessful() and all(report[k] for k in ['inputsUnchanged','ownedProcessesStopped','systemCrtDllsAndX64RegistryUnchanged']) and not report['cleanupErrors'] else 1
if __name__=='__main__':raise SystemExit(main())
