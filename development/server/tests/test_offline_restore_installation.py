"""Fresh parallel installation397 from a trusted snapshot of packaged337.

Native copied operators own bootstrap/restore and every cluster/process. Python
only orchestrates HTTP, ZIP/XML assertions and read-only SQL comparisons. No QA,
existing service, database, developer runtime or global installation is touched.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import platform
from pathlib import Path
import secrets
import shutil
import ssl
import time
import unittest
import uuid
import zipfile
import xml.etree.ElementTree as ET

from pg_support import Client, WORKSPACE, protect_directory, free_port
from test_offline_installation import OfflineInstallation, NAMES, system_crt_snapshot
from test_private_deployment_flow import NativeServer
from test_private_deployment_recovery import PrivateDeploymentRecovery

ROOT=WORKSPACE
SOURCE_ARCHIVE=TARGET_ARCHIVE=None
SOURCE_SHA=TARGET_SHA=None
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p: json.loads(p.read_bytes())
write=lambda p,d: p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))


class OfflineRestoreInstallation(OfflineInstallation):
    test_transported_package_install_restart_backup_restore=None
    sql=PrivateDeploymentRecovery.sql
    snapshot=PrivateDeploymentRecovery.snapshot
    project=PrivateDeploymentRecovery.project
    inventory=PrivateDeploymentRecovery.inventory

    @classmethod
    def setUpClass(cls):
        cls.calls=[];cls.checkpoints=[];cls.launches=[];cls.contexts=[];cls.cleanup_errors=[]
        cls.inputs_unchanged=cls.owned_processes_stopped=cls.system_crt_unchanged=False
        cls.crt_before=system_crt_snapshot()
        cls.home=ROOT/'.local/offline-restore-installation-tests'/('restore398-'+uuid.uuid4().hex)
        cls.home.mkdir(parents=True,exist_ok=False);protect_directory(cls.home)
        dependencies=['pg_support.py','test_private_deployment_flow.py','test_private_deployment_recovery.py','test_offline_installation.py']
        cls.guards={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),*[Path(__file__).parent/n for n in dependencies]]}
        cls.packages={}
        for label,original,expected in [('source',SOURCE_ARCHIVE,SOURCE_SHA),('target',TARGET_ARCHIVE,TARGET_SHA)]:
            assert original.is_file() and sha(original)==expected
            incoming=cls.home/(label+' trasladado Ω');incoming.mkdir()
            archive=incoming/'RackClick offline Ω.zip';shutil.copy2(original,archive)
            cls.guards[archive.relative_to(ROOT).as_posix()]=expected
            cls.guards[original.relative_to(ROOT).as_posix()]=expected
            bootstrap=incoming/'operators';bootstrap.mkdir()
            with zipfile.ZipFile(archive) as z:
                manifest_bytes=z.read('bundle.json');bundle=json.loads(manifest_bytes)
                assert {n for n in z.namelist() if n.startswith('operators/')}=={'operators/'+n for n in NAMES}
                for name in NAMES:
                    raw=z.read('operators/'+name);item=bundle['files']['operators/'+name]
                    assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
                    p=bootstrap/name;p.write_bytes(raw);cls.guards[p.relative_to(ROOT).as_posix()]=sha(p)
            cls.packages[label]=dict(archive=archive,sha=expected,bootstrap=bootstrap,bundle=bundle,
                manifestSha=hashlib.sha256(manifest_bytes).hexdigest())
        cls.operator_tools=cls.packages['source']['bootstrap'];cls.operator_file_count=25
        cls.poison_port=free_port()

    def select_package(self,label,installed=None):
        self.package=self.packages[label]
        tools=(installed/'content/operators') if installed else self.package['bootstrap']
        self.operator_tools=tools;type(self).operator_tools=tools

    def invoke(self,script,args,expected=0):
        data=super().invoke(script,args,expected)
        for name in ['mode','recoveryAuditEventId']:
            if name in data:self.calls[-1]['report'][name]=data[name]
        return data

    def activate(self,c,result=None):
        super().activate(c,result)
        self.select_package(c['package'],c['installation'])
        self.runtime=c['installation']/'content/dependencies/dotnet'
        self.pg_bin=c['installation']/'content/dependencies/postgresql/bin'

    def installation_context(self,label,package):
        installation=self.home/label
        c=self.context(installation/'deployment');c.update(installation=installation,package=package)
        return c

    def args(self,c,**changes):
        p=self.packages[c['package']]
        value=dict(ArchivePath=p['archive'],ExpectedArchiveSha256=p['sha'],DestinationPath=c['installation'],
                   PostgresPort=c['pg'],HttpPort=c['http'])
        value.update(changes);return value

    def recovery_args(self,c,backup,**changes):
        value=self.args(c,Mode='Restore',BackupPath=backup,ExpectedBackupManifestSha256=sha(backup/'manifest.json'),
                        RecoveryUser='Administrador recuperación Ω 😀')
        value.update(changes);return value

    def server(self,c):
        return NativeServer(self.origin,ssl.create_default_context(cafile=str(c['root']/'https/server.pem')))

    def admin_write(self,client,path,body,status=200):
        revision=self.expect(client.request('GET','/api/v1/systemhaus'),200).json()['revision']
        actor=self.expect(client.request('GET','/api/v1/me'),200).json()['user']['id']
        return self.expect(client.request('POST',path,body,{'If-Match':f'"{revision}"',
            'Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor}),status).json()

    def content_exact(self,c):
        root=c['installation']/'content';p=self.packages[c['package']]
        self.assertEqual({x.relative_to(root).as_posix() for x in root.rglob('*') if x.is_file()},set(p['bundle']['files'])|{'bundle.json'})
        self.assertEqual(sha(root/'bundle.json'),p['manifestSha'])
        for name,entry in p['bundle']['files'].items():
            self.assertEqual((root/name).stat().st_size,entry['bytes']);self.assertEqual(sha(root/name),entry['sha256'])

    def test_trusted_backup337_into_new_packaged397(self):
        source=self.installation_context('source337','source');self.select_package('source')
        created=self.invoke('Install-RackClickOfflineBundle.ps1',self.args(source,
            BootstrapUser='Administrador original Ω',SystemhausName='Origen snapshot Ω 😀'))
        self.assertEqual(len(read(source['installation']/'installation.json')),11)
        self.assertEqual(read(source['installation']/'installation.json')['schemaVersion'],1)
        self.activate(source,created);self.content_exact(source)
        original_private={p.name:sha(p) for p in (self.instance_path/'private').iterdir()}
        original_tls={p.name:sha(p) for p in (source['root']/'https').iterdir()}
        credentials=read(self.instance_path/'private/admin-login.json')
        run=self.start(1);server=self.server(source);admin,second=Client(server),Client(server)
        self.expect(admin.login(credentials['username'],credentials['password']),200)
        self.expect(second.login(credentials['username'],credentials['password']),200)
        self.assertEqual(self.expect(admin.request('GET','/'),200).body,
                         (source['installation']/'content/application/frontend/index.html').read_bytes())
        password=secrets.token_hex(32);write(self.home/'reader-credentials-private.json',dict(username='Técnico heredado Ω',password=password))
        user=self.admin_write(admin,'/api/v1/admin/users',{'username':'Técnico heredado Ω','password':password},201)['resource']['id']
        customer=self.admin_write(admin,'/api/v1/customers',{'name':'Cliente snapshot 😀'},201)['resource']['id']
        hidden=self.admin_write(admin,'/api/v1/customers',{'name':'Cliente fuera de ámbito'},201)['resource']['id']
        group=self.admin_write(admin,'/api/v1/admin/user-groups',{'name':'Técnicos recuperados'},201)['resource']['id']
        customer_group=self.admin_write(admin,'/api/v1/admin/customer-groups',{'name':'Ámbito heredado'},201)['resource']['id']
        self.admin_write(admin,f'/api/v1/admin/user-groups/{group}/members',{'userId':user,'assigned':True})
        self.admin_write(admin,f'/api/v1/admin/customer-groups/{customer_group}/members',{'customerId':customer,'assigned':True})
        for capability in ['inventory.read','reports.export']:
            self.admin_write(admin,f'/api/v1/admin/user-groups/{group}/grants',dict(grantId=str(uuid.uuid4()),
                capability=capability,scope='customerGroup',targetId=customer_group,assigned=True))
        site=self.inventory(admin,customer,'site.create',{'name':'Sede Ω'})
        building=self.inventory(admin,customer,'building.create',{'name':'Edificio Ω','siteId':site})
        room=self.inventory(admin,customer,'room.create',{'name':'Sala Ω','buildingId':building})
        rack=self.inventory(admin,customer,'rack.create',{'name':'Rack Ω','roomId':room,'sizeU':42})
        switch=self.inventory(admin,customer,'device.create',{'name':'Switch Ω','kind':'rackEquipment','rackId':rack,
            'sizeU':1,'portGroups':[{'type':'rj45','count':2}]})
        self.inventory(admin,customer,'device.create',{'name':'Dose Ω','kind':'dose','roomId':room,'portGroups':[{'type':'rj45','count':2}]})
        endpoint=self.inventory(admin,customer,'device.create',{'name':'Equipo final Ω','kind':'endDevice','roomId':room,
            'portGroups':[{'type':'rj45','count':1}]})
        inventory=self.project(admin,customer)
        first=next(p for p in inventory['ports'] if p['deviceId']==switch)
        last=next(p for p in inventory['ports'] if p['deviceId']==endpoint)
        self.inventory(admin,customer,'connections.create',{'fromPortId':first['id'],'toPortId':last['id'],
            'note':'Cable original literal Ω','color':'#aabbcc'})
        inventory=self.project(admin,customer);self.assertEqual(self.project(second,customer),inventory)
        limited=Client(server);self.expect(limited.login('Técnico heredado Ω',password),200)
        self.assertEqual(self.project(limited,customer),inventory)
        self.expect(limited.request('GET',f'/api/v1/customers/{hidden}/project'),404)
        self.expect(limited.request('GET','/api/v1/admin/users'),403)
        self.expect(admin.request('POST',f'/api/v1/customers/{customer}/reports/xlsx',{}),404)
        before=self.snapshot(source);self.assertGreaterEqual(len(before),30)
        backup=self.home/'backup externo Ω';self.checked_backup(self.pg_bin,backup)
        self.assertEqual(self.snapshot(source),before);backup_guards={p.name:sha(p) for p in backup.iterdir()}
        cookie,csrf=second.cookie,second.csrf;self.stop(run)
        self.mark(408,sourcePackaged337=True,oldGuiExact=True,newPrivateFixture=True,originalBootstrapSchema1=True,
                  hierarchyDoseFinalPortsCable=True,groupsAndClientGroupScope=True,sourceReadOnlySnapshotTables=len(before))
        self.select_package('target')
        invalid=self.installation_context('bad-mode','target')
        self.invoke('Install-RackClickOfflineBundle.ps1',self.args(invalid,Mode='restore'),2)
        self.assertFalse(invalid['installation'].exists())
        for label,extra in [('new-has-recovery',dict(BackupPath=backup)),('restore-has-bootstrap',dict(Mode='Restore',BootstrapUser='')),
                            ('restore-incomplete',dict(Mode='Restore',RecoveryUser='New')),('restore-invalid-hash',dict(Mode='Restore',
                             BackupPath=backup,RecoveryUser='New',ExpectedBackupManifestSha256='invalid'))]:
            c=self.installation_context(label,'target');self.invoke('Install-RackClickOfflineBundle.ps1',self.args(c,**extra),2)
            self.assertFalse(c['installation'].exists())
        for label,changes,expected in [('wrong-archive-hash',dict(ExpectedArchiveSha256='0'*64),2),
            ('wrong-backup-hash',dict(ExpectedBackupManifestSha256='0'*64),2),
            ('overlap-backup',dict(DestinationPath=backup/'new-root'),2),
            ('overlap-operators',dict(BackupPath=self.packages['target']['bootstrap']/'inside'),2)]:
            c=self.installation_context(label,'target')
            args=self.recovery_args(c,backup,**changes);self.invoke('Install-RackClickOfflineBundle.ps1',args,expected)
            self.assertFalse(Path(args['DestinationPath']).exists())
        existing=self.home/'existing-sentinel';existing.mkdir();(existing/'keep').write_bytes(b'unchanged')
        c=self.installation_context('existing-test','target')
        self.invoke('Install-RackClickOfflineBundle.ps1',self.recovery_args(c,backup,DestinationPath=existing),1)
        self.assertEqual((existing/'keep').read_bytes(),b'unchanged')
        invalid_backup=self.home/'invalid backup Ω';invalid_backup.mkdir();protect_directory(invalid_backup)
        (invalid_backup/'manifest.json').write_bytes(b'{}');(invalid_backup/'data.dump').write_bytes(b'PGDMP')
        c=self.installation_context('invalid-backup','target')
        self.invoke('Install-RackClickOfflineBundle.ps1',self.recovery_args(c,invalid_backup),2)
        self.assertFalse(c['installation'].exists())
        self.mark(409,modeCaseAndExplicitMutualExclusion=True,missingArguments=True,wrongHashes=True,
                  backupOverlapAndExistingDestinationRejected=True,malformedBackupBeforeRoot=True)
        truncated=self.home/'backup truncado Ω';truncated.mkdir();protect_directory(truncated)
        (truncated/'data.dump').write_bytes(b'PGDMP')
        write(truncated/'manifest.json',dict(schemaVersion=1,kind='RackClickDatabaseBackup',postgresVersion='17.11',
            format='custom',dumpFile='data.dump',dumpBytes=5,dumpSha256=sha(truncated/'data.dump'),
            createdUtc=datetime.now(timezone.utc).isoformat()))
        truncated_before={p.name:sha(p) for p in truncated.iterdir()}
        failed=self.installation_context('failed-after-content','target')
        rejected=self.invoke('Install-RackClickOfflineBundle.ps1',self.recovery_args(failed,truncated),1)
        self.assertEqual(rejected['code'],'deployment_preflight_backup_archive_invalid')
        self.assertEqual(rejected['installationSha256'],'');self.assertEqual(rejected['deploymentSha256'],'')
        self.assertTrue((failed['installation']/'content').is_dir())
        self.assertFalse((failed['installation']/'installation.json').exists())
        self.assertFalse(failed['root'].exists())
        self.assertEqual(read(failed['installation']/'installation-state.json')['status'],'failed')
        self.assertEqual({p.name:sha(p) for p in truncated.iterdir()},truncated_before)
        self.mark(414,partialRetainedAfterContent=True,failedStateNoSuccessReceipt=True,
                  malformedDumpRejectedBeforePostgres=True,backupUnchanged=True,transactionRollbackTestedHere=False)
        target=self.installation_context('restored397','target')
        restored=self.invoke('Install-RackClickOfflineBundle.ps1',self.recovery_args(target,backup))
        self.assertEqual(restored['mode'],'Restore')
        self.assertEqual(restored['sourceBackupManifestSha256'],sha(backup/'manifest.json'))
        receipt=read(target['installation']/'installation.json');state=read(target['installation']/'installation-state.json')
        self.assertEqual(set(receipt),{'schemaVersion','kind','id','rootPath','state','bundleId','bundleArchiveSha256',
            'bundleManifestSha256','deploymentId','deploymentSha256','publicOrigin','recovery'})
        self.assertEqual(receipt['schemaVersion'],2);self.assertEqual(receipt['recovery'],dict(
            backupManifestSha256=sha(backup/'manifest.json'),auditEventId=restored['recoveryAuditEventId']))
        self.assertEqual(state,dict(schemaVersion=1,installationId=receipt['id'],status='prepared',code='installation_prepared'))
        self.assertEqual(sha(target['installation']/'installation.json'),restored['installationSha256'])
        self.activate(target,restored);self.content_exact(target)
        self.assertFalse((self.instance_path/'pgdata/postmaster.pid').exists());self.assertFalse((self.runtime/'sdk').exists())
        fresh=read(self.instance_path/'private/admin-login.json')
        self.assertNotEqual(fresh['password'],credentials['password'])
        self.assertNotEqual(sha(target['root']/'https/server.pfx'),original_tls['server.pfx'])
        self.mark(413,restore397FromSnapshot337=True,installationSchema2ClosedRecovery=True,privateFreshSecretsTls=True,
                  sourceHashAndAuditLinked=True,postgresStoppedBeforeReceipt=True,bundledRuntimeWithoutSdk=True)
        restored_run=self.start(2);new_server=self.server(target)
        copied=Client(new_server);copied.cookie,copied.csrf=cookie,csrf;self.expect(copied.request('GET','/api/v1/me'),401)
        new_admin=Client(new_server);self.expect(new_admin.login(fresh['username'],fresh['password']),200)
        self.assertEqual(self.project(new_admin,customer),inventory)
        self.assertEqual(self.snapshot(target,True),{k:v for k,v in before.items() if k!='app_session'})
        original=Client(new_server);self.expect(original.login(credentials['username'],credentials['password']),200)
        recovered_limited=Client(new_server);self.expect(recovered_limited.login('Técnico heredado Ω',password),200)
        self.assertEqual(self.project(recovered_limited,customer),inventory)
        self.expect(recovered_limited.request('GET',f'/api/v1/customers/{hidden}/project'),404)
        self.expect(recovered_limited.request('GET','/api/v1/admin/users'),403)
        actor=self.expect(recovered_limited.request('GET','/api/v1/me'),200).json()['user']['id']
        payload=dict(reportKind='ports',query='',status='all',family='all',rackId=None)
        result=self.expect(recovered_limited.request('POST',f'/api/v1/customers/{customer}/reports/xlsx',payload,
            {'If-Match':f'"{inventory["revision"]}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor}),200).json()
        report=result['report'];raw=base64.b64decode(report['contentBase64'],validate=True)
        self.assertEqual(len(raw),report['byteLength']);self.assertEqual(hashlib.sha256(raw).hexdigest(),report['sha256'])
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertIsNone(z.testzip());sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
            self.assertEqual(len(sheet[0])-1,len(inventory['ports']))
        self.assertEqual(report['rowCount'],len(inventory['ports']))
        self.mark(416,allOriginalTableRowsMatchExceptExplicitRecoveryChanges=True,oldAccountsGrantsScopedPermissions=True,
                  copiedSessionsRevoked=True)
        self.mark(422,xlsxHttpBinaryZipXmlVerified=True,realExcelOpened=False)
        house=self.expect(new_admin.request('GET','/api/v1/systemhaus'),200).json()
        self.expect(new_admin.request('PUT','/api/v1/systemhaus',{'name':'Recuperado397 escrito Ω'},
            {'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),200)
        self.assertEqual(self.expect(original.request('GET','/api/v1/systemhaus'),200).json()['name'],'Recuperado397 escrito Ω')
        self.stop(restored_run);restart=self.start(3)
        self.expect(new_admin.request('GET','/api/v1/me'),200)
        self.assertEqual(self.expect(original.request('GET','/api/v1/systemhaus'),200).json()['name'],'Recuperado397 escrito Ω')
        self.assertEqual(self.project(new_admin,customer),inventory);self.stop(restart)
        self.mark(421,commitOtherSessionRead=True,restoredRestartKeepsDataAndNewSession=True)
        self.activate(source);back=self.start(4);old_server=self.server(source)
        preserved=Client(old_server);preserved.cookie,preserved.csrf=cookie,csrf
        self.expect(preserved.request('GET','/api/v1/me'),200)
        self.assertEqual(self.snapshot(source),before)
        self.assertEqual(self.project(preserved,customer),inventory)
        self.expect(preserved.request('POST',f'/api/v1/customers/{customer}/reports/xlsx',payload),404)
        self.stop(back);self.content_exact(source)
        self.assertEqual({p.name:sha(p) for p in (self.instance_path/'private').iterdir()},original_private)
        self.assertEqual({p.name:sha(p) for p in (source['root']/'https').iterdir()},original_tls)
        self.assertEqual({p.name:sha(p) for p in backup.iterdir()},backup_guards)
        self.content_exact(target)
        self.mark(423,source337CanRestartUnchanged=True,oldSessionAndDataPreserved=True,sourceStillNoXlsx=True,
                  noInPlaceUpgrade=True,backupAndBothPackageContentsUnchanged=True)


def main():
    global SOURCE_ARCHIVE,TARGET_ARCHIVE,SOURCE_SHA,TARGET_SHA
    parser=argparse.ArgumentParser(description=__doc__)
    for prefix in ['source','target']:
        parser.add_argument('--'+prefix+'-archive',type=Path,required=True)
        parser.add_argument('--'+prefix+'-archive-sha',required=True)
    parser.add_argument('--evidence',type=Path,required=True);a=parser.parse_args()
    SOURCE_ARCHIVE=a.source_archive.resolve();TARGET_ARCHIVE=a.target_archive.resolve()
    SOURCE_SHA=a.source_archive_sha;TARGET_SHA=a.target_archive_sha
    a.evidence.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    with (a.evidence/'tests.log').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OfflineRestoreInstallation))
    c=OfflineRestoreInstallation
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,
        successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),
        sources=getattr(c,'guards',{}),inputsUnchanged=c.inputs_unchanged,ownedProcessesStopped=c.owned_processes_stopped,
        systemCrtDllsAndX64RegistryUnchanged=c.system_crt_unchanged,cleanupErrors=c.cleanup_errors,
        fixture=str(getattr(c,'home','uninitialized')),calls=c.calls,checkpoints=c.checkpoints,
        sourceArchiveSha256=SOURCE_SHA,targetArchiveSha256=TARGET_SHA,actualQaAccessed=False,pythonProvisioning=False,
        pythonRestore=False,newApplicationBuilds=0,newFrontendBuilds=0,operatorFiles=25,
        freshClustersInitialized=sum((v['root']/'instance/pgdata/PG_VERSION').is_file() for v in getattr(c,'contexts',[])),
        limits='Parallel trusted snapshot recovery only; no freshness lock on source, no in-place upgrade/cutover, no service, clean Windows, productive PKI, elevated CRT installation, Excel opening or Wascar acceptance.')
    write(a.evidence/'result.json',report)
    print(json.dumps({k:report[k] for k in ['testsRun','successful','failures','errors','seconds','inputsUnchanged','ownedProcessesStopped']}))
    return 0 if result.wasSuccessful() and c.inputs_unchanged and c.owned_processes_stopped and c.system_crt_unchanged and not c.cleanup_errors else 1


if __name__=='__main__':raise SystemExit(main())
