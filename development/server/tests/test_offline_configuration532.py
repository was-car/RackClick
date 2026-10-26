"""New532 native package installation/backup/recovery with immutable private configuration.

Reuses the prior installation protocol as code, not its historical logs. Two new
clusters; bundled operators provision and recover. Python only drives assertions.
"""
import argparse,base64,json,platform,ssl,time,unittest,uuid
from datetime import datetime,timezone
from pathlib import Path
import test_offline_installation as native
from pg_support import Client
from test_private_deployment_flow import NativeServer
from test_private_template_configurations import definition,wire

class OfflineConfiguration532(native.OfflineInstallation):
    configuration_checks=[]
    @classmethod
    def setUpClass(cls):
        super().setUpClass();cls.configuration_checks=[]
        for p in [Path(__file__),Path(__file__).with_name('test_private_template_configurations.py')]:
            cls.guards[p.relative_to(native.ROOT).as_posix()]=native.sha(p)

    def server(self):
        return NativeServer(self.origin,ssl.create_default_context(cafile=str(self.deployment_path/'https/server.pem')))

    def checked_backup(self,pg_bin,path):
        self.original_login=native.read(self.instance_path/'private/admin-login.json')
        actor=Client(self.server());self.expect(actor.login(self.original_login['username'],self.original_login['password']),200)
        identity=self.expect(actor.request('GET','/api/v1/me'),200).json()['user']['id']
        customer=self.expect(actor.request('GET','/api/v1/customers'),200).json()[0]['id']
        self.configuration_customer=customer
        prefix=f'/api/v1/customers/{customer}/catalog/private-templates'
        library=self.expect(actor.request('GET',prefix),200).json();d=definition();body,compact=wire(d,'Configuración transportada Ω😀')
        result=self.expect(actor.request('POST',prefix+'/configurations',json.loads(body),
            {'Content-Type':'application/json','X-RackClick-Actor':identity,'If-Match':f'"templates-{library["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),200).json()
        self.configuration_id=result['result']['templateId'];self.configuration_result=result
        detail=self.expect(actor.request('GET',prefix+'/'+self.configuration_id),200).json()['template']
        self.configuration_bytes=base64.b64decode(detail['definitionBase64']);self.configuration_definition=d
        self.assertEqual(json.loads(self.configuration_bytes),d)
        self.assertEqual(detail['definitionSha256'],result['result']['definitionSha256'])
        self.expect(actor.request('GET',f'/api/v1/customers/{customer}/changes/details?afterRevision=1'),200)
        self.configuration_checks.append(dict(stage='before_backup',createdThroughPackagedApi=True,
            canonicalDefinitionExact=True,templateId=self.configuration_id,definitionSha256=detail['definitionSha256'],
            independentPoeAndTypePreserved=True,newDetailsEndpointAvailable=True))
        return super().checked_backup(pg_bin,path)

    def start(self,number,mode='deployment'):
        process=super().start(number,mode)
        if self.deployment_path.name=='recovered' and hasattr(self,'configuration_id'):
            original=Client(self.server());self.expect(original.login(self.original_login['username'],self.original_login['password']),200)
            prefix=f'/api/v1/customers/{self.configuration_customer}/catalog/private-templates'
            current=self.expect(original.request('GET',prefix+'/'+self.configuration_id),200).json()['template']
            self.assertEqual(base64.b64decode(current['definitionBase64']),self.configuration_bytes)
            self.assertEqual(current['definitionSha256'],self.configuration_result['result']['definitionSha256'])
            request=self.configuration_result['requestId'];state=self.expect(original.request('GET',prefix+'/operations/'+request),200).json()
            self.assertEqual(state['state'],'committed');self.assertEqual(state['operation'],self.configuration_result)
            recovered=native.read(self.instance_path/'private/admin-login.json');new_owner=Client(self.server())
            self.expect(new_owner.login(recovered['username'],recovered['password']),200)
            self.assertEqual(self.expect(new_owner.request('GET',prefix),200).json()['templates'],[])
            self.configuration_checks.append(dict(stage='after_recovery',originalOwnerAndDefinitionExact=True,
                operationReceiptExact=True,newRecoveryAdminHasSeparatePrivateLibrary=True,templateId=self.configuration_id))
        return process

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--archive-sha',required=True);parser.add_argument('--evidence',type=Path,required=True);a=parser.parse_args()
    native.ARCHIVE=a.archive.resolve(strict=True);native.ARCHIVE_SHA=a.archive_sha;a.evidence.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    with (a.evidence/'tests.log').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OfflineConfiguration532))
    c=OfflineConfiguration532
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,
        successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),
        sources=getattr(c,'guards',{}),inputsUnchanged=c.inputs_unchanged,ownedProcessesStopped=c.owned_processes_stopped,
        systemCrtDllsAndX64RegistryUnchanged=c.system_crt_unchanged,cleanupErrors=c.cleanup_errors,
        archiveSha256=a.archive_sha,calls=c.calls,configurationChecks=c.configuration_checks,baseProtocolCheckpoints=c.checkpoints,
        freshClustersInitialized=sum((v['root']/'instance/pgdata/PG_VERSION').is_file() for v in getattr(c,'contexts',[])),
        fixture=str(getattr(c,'home','uninitialized')),actualQaAccessed=False,pythonProvisioning=False,pythonRestore=False,
        limits='Native Windows/PowerShell5.1/PG/runtime from content without SDK or dev PATH. Existing compatible system CRT. Two new clusters; reused base checkpoint IDs identify code assertions only. No SCM, clean/other Windows, elevated CRT install, productive PKI, full host recovery or manual Wascar QA/adoption.')
    native.write(a.evidence/'result.json',report);print(json.dumps({k:report[k] for k in ['testsRun','successful','failures','errors','seconds','inputsUnchanged','ownedProcessesStopped']}))
    return 0 if result.wasSuccessful() and c.inputs_unchanged and c.owned_processes_stopped and c.system_crt_unchanged and not c.cleanup_errors else 1
if __name__=='__main__':raise SystemExit(main())
