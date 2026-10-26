"""Native Windows recovery into NEW deployments; existing QA is never accessed.

Provisioning, restore, accounts, session invalidation, grants and lifecycle use
copied operator commands. Python supplies HTTP assertions and read-only SQL.
Two explicit fixture-only DDL statements construct/remove an audit-failure
constraint before producing a negative archive; they are not product steps.
"""
import argparse
from datetime import datetime,timezone
import hashlib,json,os,platform,secrets,shutil,socket,ssl,subprocess,time,unittest,uuid
from pathlib import Path
from pg_support import Client,WORKSPACE,protect_directory,free_port,toolchain
from test_private_deployment_flow import PrivateDeploymentFlow,NativeServer,PS,NO_WINDOW

ROOT=WORKSPACE;TOOLS=ROOT/'tools/windows'
BASELINE=ROOT/'evidence/s1-20261017/treinta-tandas-308-337/CANDIDATA337.json'
BASELINE_SHA=None
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
write=lambda p,d:p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
NAMES=('Stage-ServerDistribution.ps1','Test-StagedDistribution.ps1','RackClick.Stage.ps1',
 'Test-RuntimePrerequisites.ps1','Test-ServerDistribution.ps1','RackClick.Backup.ps1',
 'New-RackClickDatabaseBackup.ps1','RackClick.Instance.ps1','New-RackClickLabInstance.ps1',
 'RackClick.Process.ps1','RackClick.Process.Gate.ps1','Start-RackClickLabInstance.ps1',
 'Stop-RackClickLabInstance.ps1','RackClick.LaunchControl.ps1','RackClick.Https.ps1',
 'New-RackClickLabHttpsProfile.ps1','RackClick.Deployment.ps1','Test-RackClickPrivateDeployment.ps1',
 'New-RackClickPrivateDeployment.ps1','Invoke-RackClickPrivateDeployment.ps1',
 'New-RackClickRecoveredInstance.ps1','Restore-RackClickPrivateDeployment.ps1')

class PrivateDeploymentRecovery(PrivateDeploymentFlow):
    # Reuse only the guarded command/lifecycle helpers, not the historical test.
    test_unified_create_https_operations_and_maintenance_backup=None

    @classmethod
    def setUpClass(cls):
        cls.calls=[];cls.cli_calls=[];cls.checkpoints=[];cls.launches=[];cls.cleanup_errors=[];cls.contexts=[]
        cls.inputs_unchanged=False;cls.owned_processes_stopped=False;cls.fixture_ddl=0
        manifest=read(BASELINE);assert sha(BASELINE)==BASELINE_SHA
        cls.candidate=ROOT/manifest['candidateDirectory']
        sources=[Path(__file__),BASELINE,ROOT/'development/server/tests/pg_support.py',
                 ROOT/'development/server/tests/test_private_deployment_flow.py']+[TOOLS/n for n in NAMES]
        for kind,entries in manifest['distributions'].items():
            for n,v in entries.items():
                p=cls.candidate/kind/n;assert sha(p)==v;sources.append(p)
        cls.guards={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
        cls.home=ROOT/'.local/private-deployment-recoveries'/('recovery328-'+uuid.uuid4().hex)
        cls.home.mkdir(parents=True,exist_ok=False);protect_directory(cls.home)
        cls.operator_tools=cls.home/'copied operator Ω';cls.operator_tools.mkdir()
        for n in NAMES:
            p=cls.operator_tools/n;shutil.copy2(TOOLS/n,p);cls.guards[p.relative_to(ROOT).as_posix()]=sha(p)
        cls.operator_file_count=len(NAMES);cls.instance_path=cls.home/'not-created'

    @classmethod
    def tearDownClass(cls):
        for item in cls.launches:
            p=item['process']
            if p.poll() is None:
                try:
                    args=dict(Operation='Stop',DeploymentPath=item['deploymentPath'],ExpectedDeploymentSha256=item['deploymentSha'],StopTimeoutSeconds=15)
                    with (cls.home/('cleanup-'+uuid.uuid4().hex+'.log')).open('xb') as out:
                        subprocess.run(cls.command('Invoke-RackClickPrivateDeployment.ps1',args),stdout=out,stderr=out,timeout=25,creationflags=NO_WINDOW)
                    p.wait(timeout=30)
                except Exception:
                    cls.cleanup_errors.append('Exact owned launcher fallback termination required')
                    if p.poll() is None:p.terminate()
                    p.wait(timeout=15)
            item['log'].close();item['errorLog'].close()
        cls.inputs_unchanged=all(sha(ROOT/n)==v for n,v in cls.guards.items())
        cls.owned_processes_stopped=all(x['process'].poll() is not None for x in cls.launches) and all(not (x['root']/'instance/pgdata/postmaster.pid').exists() for x in cls.contexts)
        assert cls.inputs_unchanged and cls.owned_processes_stopped and not cls.cleanup_errors

    def context(self,label,receipt=None):
        pg,http=free_port(),free_port()
        while http==pg:http=free_port()
        value=dict(root=self.home/label,pg=pg,http=http,sha=receipt)
        self.contexts.append(value);return value

    def activate(self,c):
        for n,v in dict(deployment_path=c['root'],deployment_sha=c.get('sha'),instance_path=c['root']/'instance',
                        instance_sha=c.get('instanceSha'),pg_port=c['pg'],http_port=c['http'],
                        origin=f'https://127.0.0.1:{c["http"]}',base_origin=f'http://127.0.0.1:{c["http"]}').items():
            setattr(self,n,v);setattr(type(self),n,v)

    def registered(self,c,data):
        c['sha']=data['deploymentSha256'];m=read(c['root']/'deployment.json')
        c['instanceSha']=m['instanceManifestSha256'];self.activate(c)
        self.assertEqual(sha(c['root']/'deployment.json'),c['sha'])
        self.assertEqual(sha(c['root']/'instance/instance.json'),c['instanceSha'])
        return m

    def start(self,number,mode='deployment'):
        item=super().start(number,mode)
        item.update(deploymentPath=self.deployment_path,deploymentSha=self.deployment_sha)
        return item

    def invoke(self,script,args,expected=0):
        t=time.monotonic();p=subprocess.run(self.command(script,args),capture_output=True,timeout=420,creationflags=NO_WINDOW,env=self.poisoned_environment())
        try:d=json.loads(p.stdout.decode('utf-8-sig'))
        except(ValueError,UnicodeError):d={}
        allowed={'schemaVersion','valid','exitCode','code','scope','deploymentSha256','deploymentPath','deploymentId',
                 'instanceId','instanceManifestSha256','url','httpsValidated','backupManifestSha256','dumpSha256',
                 'stopRequested','stopConfirmed','runId','state','operation','sourceBackupManifestSha256'}
        safe={k:v for k,v in d.items() if k in allowed}
        self.calls.append(dict(script=script,exitCode=p.returncode,seconds=round(time.monotonic()-t,3),report=safe,stderrEmpty=not p.stderr))
        self.assertFalse(p.stderr,'Private native stderr retained in fixture, never exported')
        self.assertEqual(p.returncode,expected,safe);self.assertEqual(d.get('exitCode'),expected,safe);self.assertEqual(d.get('valid'),expected==0,safe)
        return d

    def sql(self,c,text,runtime=False,expected=0):
        inst=c['root']/'instance';state=read(inst/'instance-state.json');suffix=state['instanceId'].replace('-','')
        user=('rc_runtime_' if runtime else 'rc_owner_')+suffix;database='rc_db_'+suffix
        if runtime:
            connection=read(inst/'private/runtime.json')['connectionString']
            password=connection.split('Password=',1)[1].split(';',1)[0]
        else:password=(inst/'private/owner-password.txt').read_text().strip()
        passfile=self.home/('sql-'+uuid.uuid4().hex+'.pgpass')
        passfile.write_bytes(f'127.0.0.1:{c["pg"]}:{database}:{user}:{password}\n'.encode('utf-8'))
        env={k:v for k,v in os.environ.items() if not k.upper().startswith('PG')}
        env.update(PGPASSFILE=str(passfile),PGCLIENTENCODING='UTF8',PGCONNECT_TIMEOUT='5')
        p=subprocess.run([str(self.pg_bin/'psql.exe'),'-X','-A','-t','-v','ON_ERROR_STOP=1','-h','127.0.0.1','-p',str(c['pg']),'-U',user,'-d',database],
                         input=text.encode('utf-8'),capture_output=True,env=env,timeout=25,creationflags=NO_WINDOW)
        (self.home/('sql-'+uuid.uuid4().hex+'-private.log')).write_bytes(p.stdout+p.stderr)
        if expected==0:self.assertEqual(p.returncode,0,'Read/fixture query failed; private log retained')
        else:self.assertNotEqual(p.returncode,0,'Restricted runtime query unexpectedly succeeded')
        return p.stdout.decode('utf-8').strip()

    def snapshot(self,c,undo_recovery=False):
        tables=self.sql(c,"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines();snap={}
        identity=c['root']/'instance/instance-state.json';instance_id=read(identity)['instanceId']
        new=None
        if undo_recovery:
            new=json.loads(self.sql(c,f"SELECT after_json::text FROM audit_event WHERE action='deployment.recover' AND after_json->>'instanceId'='{instance_id}'"))
        for table in tables:
            self.assertRegex(table,r'^[a-z][a-z0-9_]*$');where='';row='to_jsonb(t)'
            if new:
                if table=='app_session':continue
                if table=='app_user':where=f"WHERE id<>'{new['createdUserId']}'"
                if table=='user_group':where=f"WHERE id<>'{new['createdGroupId']}'"
                if table=='user_group_member':where=f"WHERE user_id<>'{new['createdUserId']}'"
                if table=='permission_grant':where=f"WHERE user_group_id<>'{new['createdGroupId']}'"
                if table=='audit_event':where=f"WHERE NOT(action='deployment.recover' AND after_json->>'instanceId'='{instance_id}')"
                if table=='systemhaus':row="jsonb_set(to_jsonb(t),'{revision}',to_jsonb(revision-1))"
            snap[table]=self.sql(c,f"SELECT md5(COALESCE(jsonb_agg(row ORDER BY row::text),'[]'::jsonb)::text) FROM (SELECT {row} row FROM public.{table} t {where}) s")
        return snap

    def cli(self,c,expected_error,**changes):
        inst=c['root']/'instance';state=read(inst/'instance-state.json');suffix=state['instanceId'].replace('-','')
        password=(inst/'private/owner-password.txt').read_text().strip()
        env={k:v for k,v in os.environ.items() if not k.startswith(('Recovery','ConnectionStrings','Bootstrap','ASPNETCORE','Kestrel','RackClick'))}
        env.update(DOTNET_ROOT=str(self.runtime),DOTNET_NOLOGO='1',ASPNETCORE_ENVIRONMENT='Development',
          ConnectionStrings__RackClick=f'Host=127.0.0.1;Port={c["pg"]};Database=rc_db_{suffix};Username=rc_owner_{suffix};Password={password};SSL Mode=Disable;',
          Recovery__User='Another recovery admin',Recovery__ExpectedDatabase='rc_db_'+suffix,Recovery__BackupSha256='1'*64)
        modes=changes.pop('modes',['--recover-admin']);stdin=changes.pop('stdin','x'*64+'\n');env.update(changes)
        p=subprocess.run([str(self.runtime/'dotnet.exe'),str(self.candidate/'server/RackClick.Server.dll'),*modes],input=stdin.encode(),capture_output=True,env=env,timeout=25,creationflags=NO_WINDOW)
        try:d=json.loads(p.stdout.decode('utf-8-sig'))
        except(ValueError,UnicodeError):d={}
        self.assertFalse(p.stderr,'CLI error leaked to stderr');self.assertEqual(p.returncode,1,d)
        self.assertEqual(d.get('error'),expected_error,d)
        self.cli_calls.append(dict(exitCode=p.returncode,status=d['status'],error=d['error'],stderrEmpty=True))

    def project(self,client,customer):return self.expect(client.request('GET',f'/api/v1/customers/{customer}/project'),200).json()

    def inventory(self,client,customer,kind,payload):
        rev=self.project(client,customer)['revision'];actor=self.expect(client.request('GET','/api/v1/me'),200).json()['user']['id']
        return self.expect(client.request('POST',f'/api/v1/customers/{customer}/commands',{'type':kind,'payload':payload},
            {'If-Match':f'"{rev}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor}),200).json()['result']['resourceId']

    def restore_args(self,c,backup,user):
        return dict(ManifestPath=BASELINE,ExpectedManifestSha256=BASELINE_SHA,ServerPath=self.candidate/'server',FrontendPath=self.candidate/'frontend',
             DotNetPath=self.runtime/'dotnet.exe',PostgresBinPath=self.pg_bin,DestinationPath=c['root'],PostgresPort=c['pg'],HttpPort=c['http'],
             BackupPath=backup,ExpectedBackupManifestSha256=sha(backup/'manifest.json'),RecoveryUser=user)

    def recover(self,c,backup,user,expected=0):
        d=self.invoke('Restore-RackClickPrivateDeployment.ps1',self.restore_args(c,backup,user),expected)
        if expected==0:self.registered(c,d)
        else:self.assertFalse((c['root']/'deployment.json').exists())
        return d

    def test_full_native_recovery_and_recovery_of_recovered_backup(self):
        tools=toolchain();self.pg_bin=tools['postgresql'].parent;self.runtime=self.home/'runtime sin SDK Ω';self.runtime.mkdir()
        original=tools['dotnet'].parent;shutil.copy2(original/'dotnet.exe',self.runtime/'dotnet.exe');shutil.copytree(original/'host',self.runtime/'host')
        for name in ('Microsoft.NETCore.App','Microsoft.AspNetCore.App'):shutil.copytree(original/'shared'/name,self.runtime/'shared'/name)
        sdks=subprocess.run([str(self.runtime/'dotnet.exe'),'--list-sdks'],capture_output=True,check=True,creationflags=NO_WINDOW)
        self.assertFalse(sdks.stdout.strip() or sdks.stderr.strip());self.poison_port=free_port()
        self.mark(328,copiedOperatorFiles=len(NAMES),runtimeWithoutSdk=True,newBuildsDuringTest=0)
        source=self.context('source');self.activate(source)
        source_args=dict(ManifestPath=BASELINE,ExpectedManifestSha256=BASELINE_SHA,
            ServerPath=self.candidate/'server',FrontendPath=self.candidate/'frontend',DotNetPath=self.runtime/'dotnet.exe',PostgresBinPath=self.pg_bin,
            DestinationPath=source['root'],PostgresPort=source['pg'],HttpPort=source['http'],BootstrapUser='Source admin Ω',SystemhausName='Recuperación completa Ω')
        self.registered(source,self.invoke('New-RackClickPrivateDeployment.ps1',source_args));source_private={p.name:sha(p) for p in (self.instance_path/'private').iterdir()}
        source_tls={p.name:sha(p) for p in (self.deployment_path/'https').iterdir()};source_login=read(self.instance_path/'private/admin-login.json')
        launched=self.start(1);server=NativeServer(self.origin,ssl.create_default_context(cafile=str(self.deployment_path/'https/server.pem')))
        admin,second=Client(server),Client(server);self.expect(admin.login(source_login['username'],source_login['password']),200);self.expect(second.login(source_login['username'],source_login['password']),200)
        house=self.expect(admin.request('GET','/api/v1/systemhaus'),200).json();actor=self.expect(admin.request('GET','/api/v1/me'),200).json()['user']['id']
        reader_password=secrets.token_hex(32);write(self.home/'fixture-reader-private.json',dict(username='Reader original Ω',password=reader_password))
        self.expect(admin.request('POST','/api/v1/admin/users',{'username':'Reader original Ω','password':reader_password},
           {'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor}),201)
        house=self.expect(admin.request('GET','/api/v1/systemhaus'),200).json()
        customer=self.expect(admin.request('POST','/api/v1/customers',{'name':'Cliente recuperado 😀'},
          {'If-Match':f'"{house["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),201).json()['resource']['id']
        site=self.inventory(admin,customer,'site.create',{'name':'Sede Ω'});building=self.inventory(admin,customer,'building.create',{'name':'Edificio Ω','siteId':site})
        room=self.inventory(admin,customer,'room.create',{'name':'Sala Ω','buildingId':building});rack=self.inventory(admin,customer,'rack.create',{'name':'Rack Ω','roomId':room,'sizeU':42})
        switch=self.inventory(admin,customer,'device.create',{'name':'Switch Ω','kind':'rackEquipment','rackId':rack,'sizeU':1,'portGroups':[{'type':'rj45','count':2}]})
        self.inventory(admin,customer,'device.create',{'name':'Dose Ω','kind':'dose','roomId':room,'portGroups':[{'type':'rj45','count':2}]})
        endpoint=self.inventory(admin,customer,'device.create',{'name':'Equipo final Ω','kind':'endDevice','roomId':room,'portGroups':[{'type':'rj45','count':1}]})
        project=self.project(admin,customer);first=next(p for p in project['ports'] if p['deviceId']==switch);last=next(p for p in project['ports'] if p['deviceId']==endpoint)
        self.inventory(admin,customer,'connections.create',{'fromPortId':first['id'],'toPortId':last['id'],'note':'Cable literal Ω','color':'#aabbcc'})
        project=self.project(second,customer);self.assertEqual(len(project['devices']),3);self.assertEqual(len(project['connections']),1)
        reader=Client(server);self.expect(reader.login('Reader original Ω',reader_password),200);self.expect(reader.request('GET','/api/v1/admin/users'),403)
        self.cli(source,'recovery_pending_marker_required');self.cli(source,'cli_mode_conflict',modes=['--recover-admin','--migrate'])
        self.cli(source,'username_invalid',Recovery__User='😀'*101);self.cli(source,'password_length',stdin='x'*15+'\n')
        self.cli(source,'recovery_database_invalid',Recovery__ExpectedDatabase='postgres')
        before=self.snapshot(source);backup=self.home/'backup original Ω';self.checked_backup(self.pg_bin,backup);self.assertEqual(self.snapshot(source),before)
        self.mark(329,hierarchyDoseEndDevicePortsAndCable=True,twoSessions=True,unprivilegedAccount=True,sourceRowsUnchangedByBackup=True)
        # Only this fixture receives test DDL; row representations remain identical.
        self.sql(source,"ALTER TABLE audit_event ADD CONSTRAINT qa_reject_recovery308 CHECK(action<>'deployment.recover')");type(self).fixture_ddl+=1
        bad_backup=self.home/'backup audit-negative Ω';self.checked_backup(self.pg_bin,bad_backup)
        self.sql(source,'ALTER TABLE audit_event DROP CONSTRAINT qa_reject_recovery308');type(self).fixture_ddl+=1
        self.assertEqual(self.snapshot(source),before);self.stop(launched)
        bad=self.context('wrong-hash');bad_args=self.restore_args(bad,backup,'New admin')
        bad_args['ExpectedBackupManifestSha256']='0'*64;self.invoke('Restore-RackClickPrivateDeployment.ps1',bad_args,2);self.assertFalse(bad['root'].exists())
        long_name=self.context('long-name');self.recover(long_name,backup,'😀'*101,2);self.assertFalse(long_name['root'].exists())
        existing_args=self.restore_args(source,backup,'New admin');self.invoke('Restore-RackClickPrivateDeployment.ps1',existing_args,1)
        self.assertEqual(sha(source['root']/'deployment.json'),source['sha'])
        self.mark(330,badReferenceRejectedBeforeCreate=True,unicode101RejectedBeforeCreate=True,existingDeploymentPreserved=True)
        failed=self.context('audit-failure');failure=self.recover(failed,bad_backup,'Rollback admin Ω',1)
        self.assertFalse((failed['root']/'instance/instance.json').exists());self.assertFalse((failed['root']/'instance/pgdata/postmaster.pid').exists())
        partial=self.inspect_failed(failed)
        self.assertEqual(partial['snapshot'],before);self.assertTrue(partial['pendingMarker']);self.assertTrue(partial['cleanStop'])
        self.assertTrue(all(partial['cliGuards'].values()));self.assertEqual(len(partial['cliGuards']),5)
        self.mark(331,auditFailureAfterMutationsRolledBack=True,allOriginalRowsAndSessionsIntact=True,noSuccessReceipt=True,partialRetained=True)
        recovered=self.context('recovered');self.recover(recovered,backup,'  R'+'😀'*99+'  ')
        self.invoke('Test-RackClickPrivateDeployment.ps1',dict(DeploymentPath=recovered['root'],ExpectedDeploymentSha256=recovered['sha']))
        recovered_private={p.name:sha(p) for p in (self.instance_path/'private').iterdir()};recovered_tls={p.name:sha(p) for p in (self.deployment_path/'https').iterdir()}
        self.assertTrue(all(v!=source_private[k] for k,v in recovered_private.items() if k!='backup-profile.json'))
        self.assertNotEqual(recovered_tls['server.pfx'],source_tls['server.pfx'])
        run=self.start(2);srv=NativeServer(self.origin,ssl.create_default_context(cafile=str(self.deployment_path/'https/server.pem')))
        restored=self.snapshot(recovered,True);self.assertEqual(restored,{k:v for k,v in before.items() if k!='app_session'})
        self.assertEqual(self.sql(recovered,'SELECT count(*) FROM app_session'),'0')
        audit=json.loads(self.sql(recovered,f"SELECT after_json::text FROM audit_event WHERE action='deployment.recover' AND after_json->>'instanceId'='{read(self.instance_path/'instance.json')['id']}'"))
        self.assertEqual(audit['revokedSessions'],3);self.assertEqual(audit['sourceBackupManifestSha256'],sha(backup/'manifest.json'))
        self.assertEqual(self.sql(recovered,"SELECT count(*) FROM pg_roles WHERE rolname LIKE 'rc_%' AND (rolsuper OR rolcreatedb OR rolcreaterole)"),'1') # cluster admin only
        self.assertEqual(self.sql(recovered,"SELECT has_schema_privilege(current_user,'public','CREATE') OR has_database_privilege(current_user,current_database(),'CREATE')",runtime=True),'f')
        self.sql(recovered,'CREATE TABLE forbidden_runtime_probe(id integer)',runtime=True,expected=1)
        self.mark(332,allPublicTablesCompared=len(before),onlyDocumentedRecoveryRowsChanged=True,newPgRolesSecretsAndTls=True,runtimeRestricted=True)
        old=Client(srv);old.cookie,old.csrf=second.cookie,second.csrf;self.expect(old.request('GET','/api/v1/me'),401)
        credentials=read(self.instance_path/'private/admin-login.json');self.assertEqual(credentials['username'],'r'+'😀'*99)
        new_admin,original=Client(srv),Client(srv);self.expect(new_admin.login('  R'+'😀'*99+'  ',credentials['password']),200);self.expect(original.login(source_login['username'],source_login['password']),200)
        inherited_reader=Client(srv);self.expect(inherited_reader.login('Reader original Ω',reader_password),200);self.expect(inherited_reader.request('GET','/api/v1/admin/users'),403)
        self.assertEqual(self.expect(inherited_reader.request('GET','/api/v1/customers'),200).json(),[])
        self.assertEqual(self.project(original,customer),project)
        stable=self.snapshot(recovered);self.cli(recovered,'recovery_already_initialized');self.assertEqual(self.snapshot(recovered),stable)
        self.mark(333,unicode100CreatedThenLogin=True,oldCookieRejected=True,originalPasswordsAndPermissionsPreserved=True,repeatedCliNoMutation=True)
        h=self.expect(new_admin.request('GET','/api/v1/systemhaus'),200).json()
        self.expect(new_admin.request('PUT','/api/v1/systemhaus',{'name':'Systemhaus después de recuperar Ω'},
           {'If-Match':f'"{h["revision"]}"','Idempotency-Key':str(uuid.uuid4())}),200)
        self.assertEqual(self.expect(original.request('GET','/api/v1/systemhaus'),200).json()['name'],'Systemhaus después de recuperar Ω')
        self.mark(334,writeConfirmedAndOtherSessionRead=True,inventoryStillExact=True)
        next_backup=self.home/'backup recovered Ω';next_before=self.snapshot(recovered);self.checked_backup(self.pg_bin,next_backup);self.assertEqual(self.snapshot(recovered),next_before);self.stop(run)
        again=self.context('recovered-again');self.recover(again,next_backup,'Second recovery Ω')
        finalrun=self.start(3);finalsrv=NativeServer(self.origin,ssl.create_default_context(cafile=str(self.deployment_path/'https/server.pem')))
        self.assertEqual(self.snapshot(again,True),{k:v for k,v in next_before.items() if k!='app_session'})
        self.assertEqual(self.sql(again,"SELECT count(*) FROM audit_event WHERE action='deployment.recover'"),'2')
        second_old=Client(finalsrv);second_old.cookie,second_old.csrf=new_admin.cookie,new_admin.csrf;self.expect(second_old.request('GET','/api/v1/me'),401)
        final_credentials=read(self.instance_path/'private/admin-login.json');finalclient=Client(finalsrv);self.expect(finalclient.login(final_credentials['username'],final_credentials['password']),200)
        self.assertEqual(self.project(finalclient,customer),project)
        self.mark(335,backupOfRecoveredAcceptedNewUuid=True,twoRecoveryAuditsPreserved=True,allPreviousRowsPreserved=True,copiedRecoveryCookieRejected=True)
        self.stop(finalrun);restart=self.start(4);self.expect(finalclient.request('GET','/api/v1/me'),200)
        self.assertEqual(self.project(finalclient,customer),project);self.stop(restart)
        self.assertEqual({p.name:sha(p) for p in (recovered['root']/'instance/private').iterdir()},recovered_private)
        self.assertEqual({p.name:sha(p) for p in (recovered['root']/'https').iterdir()},recovered_tls)
        self.assertEqual({p.name:sha(p) for p in (source['root']/'instance/private').iterdir()},source_private)
        self.assertEqual({p.name:sha(p) for p in (source['root']/'https').iterdir()},source_tls)
        self.mark(336,restartDataAndSessionPersist=True,sourceAndRecoveredPrivateInputsUnchanged=True,ownedInstancesStopped=True)

    def inspect_failed(self,c):
        # A private failed cluster is reopened in an owned Job. Six explicit test-only
        # statements temporarily change/restore its marker and migration history.
        # Account/grants/sessions never receive test SQL; final row hashes must match.
        script=self.home/'inspect-failed.ps1'
        text=r'''param([string]$Tools,[string]$Instance,[string]$Pg,[int]$Port,[string]$DotNet,[string]$Dll)
. (Join-Path $Tools 'RackClick.Instance.ps1')
$h=$null;$report=$null;$root=$Instance;$logs=New-BackupPrivateDirectory (Join-Path $root ('inspect-'+[guid]::NewGuid().ToString('N')))
try {
 $state=[IO.File]::ReadAllText((Join-Path $root 'instance-state.json'))|ConvertFrom-Json
 $suffix=$state.instanceId.Replace('-','');$db='rc_db_'+$suffix
 $profile=@{host='127.0.0.1';port=$Port;database=$db;user=('rc_owner_'+$suffix);password=[IO.File]::ReadAllText((Join-Path $root 'private/owner-password.txt')).Trim()}
 $envMap=New-InstanceEnvironment @{PGCLIENTENCODING='UTF8';PGCONNECT_TIMEOUT='5'}
 $h=Start-RackClickOwnedProcess -Executable (Join-Path $Pg 'postgres.exe') -Arguments @('-D','pgdata') -WorkingDirectory $root -Environment $envMap -LogDirectory $logs -Label 'readonly-postgres'
 $ready=$false
 for($i=0;$i -lt 60;$i++){try{Assert-BackupServerVersion $Pg $profile;$ready=$true;break}catch{Start-Sleep -Milliseconds 100}}
 if(-not $ready){throw 'failed cluster inspection readiness'}
 $argsPg=@('-X','-A','-t','-v','ON_ERROR_STOP=1')+(Get-BackupConnectionArguments $profile $db)
 $tables=(Invoke-BackupPg (Join-Path $Pg 'psql.exe') $argsPg $profile "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").Split("`n")
 $snapshot=@{}
 foreach($raw in $tables){$table=$raw.Trim();if($table -cnotmatch '^[a-z][a-z0-9_]*$'){throw 'table name invalid'}
  $snapshot[$table]=Invoke-BackupPg (Join-Path $Pg 'psql.exe') $argsPg $profile "SELECT md5(COALESCE(jsonb_agg(row ORDER BY row::text),'[]'::jsonb)::text) FROM (SELECT to_jsonb(t) row FROM public.$table t) s"
 }
 $marker=Invoke-BackupPg (Join-Path $Pg 'psql.exe') $argsPg $profile "SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()"
 if($marker -cnotmatch '^RackClickRecoveryPending:([a-f0-9-]{36}):([a-f0-9]{64})$'){throw 'marker missing'}
 $backupSha=$Matches[2]
 function Test-RecoveryCli([string]$Code,[hashtable]$Overrides=@{}) {
  $values=@{DOTNET_ROOT=[IO.Path]::GetDirectoryName($DotNet);DOTNET_NOLOGO='1';ASPNETCORE_ENVIRONMENT='Development';ConnectionStrings__RackClick=(Get-InstanceConnection $Port $db $profile.user $profile.password);Recovery__User='Another recovery admin';Recovery__ExpectedDatabase=$db;Recovery__BackupSha256=$backupSha}
  foreach($k in $Overrides.Keys){$values[$k]=$Overrides[$k]}
  $child=$null
  try{$child=Start-RackClickOwnedProcess -Executable $DotNet -Arguments @($Dll,'--recover-admin') -WorkingDirectory $root -Environment (New-InstanceEnvironment $values) -InputText ((New-InstancePassword)+"`n") -LogDirectory $logs -Label ('negative-'+[guid]::NewGuid().ToString('N'))
   $r=Wait-RackClickOwnedProcess $child -TimeoutSeconds 30
   if($r.exitCode -ne 1 -or $r.stderr.Length -ne 0){throw 'CLI rejection output invalid'}
   $v=$r.stdout|ConvertFrom-Json;if($v.error -cne $Code){throw ('CLI rejection mismatch '+$Code)};return $true
  }finally{if($null -ne $child){Stop-RackClickOwnedProcess $child;$child.Process.Dispose()}}
 }
 $guards=@{}
 $clusterPass=[IO.File]::ReadAllText((Join-Path $root 'private/cluster-password.txt')).Trim()
 $guards.owner=Test-RecoveryCli 'recovery_owner_required' @{ConnectionStrings__RackClick=(Get-InstanceConnection $Port $db ('rc_cluster_'+$suffix) $clusterPass)}
 $nameHex=Invoke-BackupPg (Join-Path $Pg 'psql.exe') $argsPg $profile "SELECT encode(convert_to(username,'UTF8'),'hex') FROM app_user ORDER BY username LIMIT 1"
 $bytes=New-Object byte[] ($nameHex.Length/2);for($i=0;$i -lt $bytes.Length;$i++){$bytes[$i]=[Convert]::ToByte($nameHex.Substring($i*2,2),16)}
 $guards.existingUser=Test-RecoveryCli 'recovery_username_exists' @{Recovery__User=[Text.Encoding]::UTF8.GetString($bytes)}
 $null=Invoke-BackupPg (Join-Path $Pg 'psql.exe') $argsPg $profile "COMMENT ON DATABASE $db IS NULL"
 $guards.pending=Test-RecoveryCli 'recovery_pending_marker_required'
 $null=Invoke-BackupPg (Join-Path $Pg 'psql.exe') $argsPg $profile "COMMENT ON DATABASE $db IS '$marker'"
 $row=Invoke-BackupPg (Join-Path $Pg 'psql.exe') $argsPg $profile 'SELECT to_jsonb(s)::text FROM schema_migration s WHERE version=9'
 $migration=$row|ConvertFrom-Json
 if($migration.digest -cnotmatch '^[a-fA-F0-9]{64}$'){throw 'migration digest invalid'}
 $null=Invoke-BackupPg (Join-Path $Pg 'psql.exe') $argsPg $profile "UPDATE schema_migration SET digest=repeat('0',64) WHERE version=9"
 $guards.digest=Test-RecoveryCli 'migration_digest_mismatch'
 $null=Invoke-BackupPg (Join-Path $Pg 'psql.exe') $argsPg $profile ("UPDATE schema_migration SET digest='"+$migration.digest+"' WHERE version=9")
 $null=Invoke-BackupPg (Join-Path $Pg 'psql.exe') $argsPg $profile 'DELETE FROM schema_migration WHERE version=9'
 $guards.history=Test-RecoveryCli 'recovery_schema_required'
 $rowLiteral=$row.Replace("'","''")
 $null=Invoke-BackupPg (Join-Path $Pg 'psql.exe') $argsPg $profile ("INSERT INTO schema_migration SELECT * FROM jsonb_populate_record(NULL::schema_migration,'"+$rowLiteral+"'::jsonb)")
 foreach($table in $snapshot.Keys){
  $after=Invoke-BackupPg (Join-Path $Pg 'psql.exe') $argsPg $profile "SELECT md5(COALESCE(jsonb_agg(row ORDER BY row::text),'[]'::jsonb)::text) FROM (SELECT to_jsonb(t) row FROM public.$table t) s"
  if($after -cne $snapshot[$table]){throw 'fixture row guard changed'}
 }
 Assert-InstanceOwnedPostgres $h (Join-Path $root 'pgdata')
 $null=Invoke-InstanceChild (Join-Path $Pg 'pg_ctl.exe') @('stop','-D','pgdata','-m','fast','-w','-t','30') $root $envMap $logs 'readonly-stop'
 $report=@{snapshot=$snapshot;pendingMarker=$marker.StartsWith('RackClickRecoveryPending:');cliGuards=$guards;fixtureMutationStatements=6;cleanStop=(-not [IO.File]::Exists((Join-Path $root 'pgdata/postmaster.pid')))}
}finally{if($null -ne $h){Stop-RackClickOwnedProcess $h;$h.Process.Dispose()}}
$report|ConvertTo-Json -Depth 4 -Compress
'''
        script.write_bytes(text.encode('utf-8'));p=subprocess.run([str(PS),'-NoProfile','-File',str(script),'-Tools',str(self.operator_tools),'-Instance',str(c['root']/'instance'),'-Pg',str(self.pg_bin),'-Port',str(c['pg']),'-DotNet',str(self.runtime/'dotnet.exe'),'-Dll',str(self.candidate/'server/RackClick.Server.dll')],capture_output=True,timeout=150,creationflags=NO_WINDOW)
        (self.home/'failed-inspection-process-private.log').write_bytes(p.stdout+p.stderr)
        self.assertFalse(p.stderr,'Failed fixture inspection stderr retained privately');self.assertEqual(p.returncode,0)
        data=json.loads(p.stdout.decode('utf-8-sig'));write(self.home/'failed-inspection-public.json',data);return data

def main():
    global BASELINE_SHA
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--manifest-sha',required=True)
    a=p.parse_args();BASELINE_SHA=a.manifest_sha;a.evidence.mkdir(parents=True,exist_ok=False);t=time.monotonic()
    with (a.evidence/'tests.log').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PrivateDeploymentRecovery))
    c=PrivateDeploymentRecovery
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),
      seconds=round(time.monotonic()-t,3),sources=getattr(c,'guards',{}),inputsUnchanged=c.inputs_unchanged,ownedProcessesStopped=c.owned_processes_stopped,cleanupErrors=c.cleanup_errors,
      fixture=str(getattr(c,'home','not initialized')),calls=c.calls,cliCalls=c.cli_calls,checkpoints=c.checkpoints,fixtureDdlStatements=c.fixture_ddl,
      actualQaAccessed=False,pythonProvisioning=False,pythonRestore=False,pythonAccountOrGrantOrSessionMutation=False,newBuildsDuringTest=0,copiedOperatorFiles=getattr(c,'operator_file_count',0),
      limits='New local private deployments only. SQL assertions read-only except two source-fixture audit constraint statements and six failed-newcluster marker/history test changes restored exactly under an owned native Job. No test SQL edits accounts/grants/sessions. No SCM/dependency installer/othermachine/productionPKI/browserQA/adoption.')
    write(a.evidence/'result.json',report)
    print(json.dumps({k:report[k] for k in ['testsRun','successful','failures','errors','seconds','inputsUnchanged','ownedProcessesStopped']}))
    return 0 if result.wasSuccessful() and c.inputs_unchanged and c.owned_processes_stopped and not c.cleanup_errors else 1

if __name__=='__main__':raise SystemExit(main())
