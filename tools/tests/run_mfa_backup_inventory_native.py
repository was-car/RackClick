"""F0602 native metadata trial: new PG17 cluster only, no Windows services or installed instance.

Requires a caller-pinned isolated source build. Raw logs, synthetic envelopes and
new random credentials stay under ignored .local/labs. Does not retire a key.
"""
from pathlib import Path
import argparse
import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'development/server/tests'))
from pg_support import Lab, Database, literal, NO_WINDOW

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def quote(value):return "'"+str(value).replace("'","''")+"'"

FIXTURE=r'''
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using RackClick.Server;
var data=JsonDocument.Parse(Console.In.ReadToEnd()).RootElement;
var id=data.GetProperty("id").GetGuid();
var password=data.GetProperty("password").GetString()!;
var versions=new[]{1,7,8};
var ring=JsonSerializer.SerializeToUtf8Bytes(new { format="RackClick.MfaKeyRing",formatVersion=1,installationId=id,
 versions=versions.Select(v=>new {version=v,state=v==7?"active":"retired",createdAtUtc="2026-11-09T00:00:00Z"}) });
var keys=versions.Select(v=>(v,RandomNumberGenerator.GetBytes(32))).ToArray();
try {
 using var payload=MfaKeyRecoveryPayload.Serialize(ring,id,keys);
 var envelope=MfaKeyRecoveryEnvelope.Seal(password,payload.Bytes);
 Console.WriteLine(Convert.ToBase64String(envelope));
} finally {foreach(var key in keys)CryptographicOperations.ZeroMemory(key.Item2);}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--expected-server-sha256',required=True)
    args=p.parse_args();source=args.source_root.resolve(strict=True)
    if not source.is_relative_to((ROOT/'.local').resolve()):raise ValueError('isolated_source_required')
    server=source/'development/server';dll=server/'src/RackClick.Server/bin/Release/net10.0/RackClick.Server.dll'
    if sha(dll)!=args.expected_server_sha256:raise ValueError('server_pin_invalid')
    lab=Lab('f0602-native-inventory'); summary={}; results=[]
    original_environment=lab.environment
    def environment():
        env=original_environment()
        for key in list(env):
            if key.startswith(('ConnectionStrings__','SqlSecret__','MfaKeyStore__','RACKCLICK_TEST_','CORECLR_')) or key=='PSModulePath':env.pop(key)
        return env
    lab.environment=environment
    def run(label,command,**kwargs):
        completed=subprocess.run([str(x) for x in command],env=kwargs.pop('env',environment()),
              capture_output=True,creationflags=NO_WINDOW,timeout=kwargs.pop('timeout',180),**kwargs)
        (lab.directory/(label+'.private.log')).write_bytes(completed.stdout+completed.stderr)
        return completed
    def native(label,script,expected=0):
        # Parent may be PowerShell7; force the Windows PowerShell5.1 security module, not its inherited search-path match.
        script="Import-Module (Join-Path $PSHOME 'Modules\\Microsoft.PowerShell.Security') -ErrorAction Stop;"+script
        encoded=base64.b64encode(script.encode('utf-16le')).decode()
        result=run(label,['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-EncodedCommand',encoded])
        if result.returncode!=expected:raise RuntimeError(label+'_exit_unexpected')
        obj=json.loads(result.stdout.decode('utf-8-sig').strip())
        return obj
    def add_factor(db,version,state,label):
        user=uuid.uuid4()
        lab.sql(db,"INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT "
            f"'{user}',id,{literal(label)},{literal(secrets.token_urlsafe(32))} FROM systemhaus;"
            "INSERT INTO app_mfa_factor(systemhaus_id,user_id,state,secret_ciphertext,key_version) SELECT "
            f"id,'{user}',{literal(state)},decode('{secrets.token_hex(48)}','hex'),{version} FROM systemhaus",sensitive=True)
    def dump(db,path,snapshot=None):
        env=environment();env['PGPASSFILE']=str(db.directory/'backup.pgpass')
        command=[lab.pg_bin/'pg_dump.exe','-w','-h','127.0.0.1','-p',str(lab.port),'-U',db.runtime,'-d',db.name,
                 '-F','c','--no-owner','--no-acl','-f',path]
        if snapshot:command+=['--snapshot',snapshot]
        result=run('concurrent-dump',command,env=env)
        if result.returncode:raise RuntimeError('concurrent_dump_failed')
    try:
        lab.start();id=uuid.uuid4();suffix=id.hex
        folder=lab.directory/'native-db';folder.mkdir()
        db=Database('rc_db_'+suffix,'rc_owner_'+suffix,secrets.token_urlsafe(32),
                    'rc_backup_'+suffix,secrets.token_urlsafe(32),folder)
        lab.sql('postgres',f'CREATE ROLE {db.owner} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(db.owner_password)};'
                f'CREATE ROLE {db.runtime} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(db.runtime_password)};',sensitive=True)
        lab.sql('postgres',f'CREATE DATABASE {db.name} OWNER {db.owner} TEMPLATE template0 ENCODING \'UTF8\';')
        for kind,user,password in [('owner',db.owner,db.owner_password),('backup',db.runtime,db.runtime_password)]:
            (folder/(kind+'.pgpass')).write_text(f'127.0.0.1:{lab.port}:*:{user}:{password}\n','utf-8')
        initialized=lab.bootstrap(db,'synthetic-backup-admin',secrets.token_urlsafe(24),dll=dll)
        (folder/'bootstrap.private.log').write_text(initialized.stdout+initialized.stderr,'utf-8')
        if initialized.returncode:raise RuntimeError('native_bootstrap_failed')
        lab.sql(db,f'REVOKE CREATE ON SCHEMA public FROM PUBLIC; GRANT USAGE ON SCHEMA public TO {db.runtime};'
                   f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO {db.runtime};')
        add_factor(db,1,'pending','snapshot-pending');add_factor(db,7,'active','snapshot-active');add_factor(db,1,'disabled','snapshot-disabled')
        # A new isolated helper with the existing friend-assembly identity creates synthetic encrypted material.
        helper=lab.directory/'fixture';helper.mkdir()
        (helper/'Program.cs').write_text(FIXTURE,'utf-8')
        (helper/'Fixture.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable><AssemblyName>RackClick.Quality.Tests</AssemblyName><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup><ItemGroup><Reference Include="RackClick.Server"><HintPath>'+str(dll)+'</HintPath></Reference></ItemGroup></Project>','utf-8')
        for command,label in [(['restore','--ignore-failed-sources'],'fixture-restore'),(['build','-c','Release','--no-restore'],'fixture-build')]:
            result=run(label,[lab.dotnet,*command,f'-bl:{lab.directory}/{label}-{{}}.binlog'],cwd=helper)
            if result.returncode:raise RuntimeError(label+'_failed')
        password=secrets.token_urlsafe(24)
        generated=run('fixture-envelope',[lab.dotnet,helper/'bin/Release/net10.0/RackClick.Quality.Tests.dll'],
                      input=json.dumps(dict(id=str(id),password=password)).encode())
        if generated.returncode:raise RuntimeError('envelope_fixture_failed')
        envelope=base64.b64decode(generated.stdout.strip(),validate=True)
        envelope_path=lab.directory/'external-fixture.rckey';envelope_path.write_bytes(envelope)
        initial=dict(operation='snapshot',installationId=str(id),connectionString=db.connection(lab.port),
                     envelopeBase64=base64.b64encode(envelope).decode(),envelopePassword=password)
        negatives=[]
        for label,apply,undo,admin in [
            ('shared_database_marker',f"COMMENT ON DATABASE {db.name} IS 'RackClickRecoveryPending:synthetic';",f'COMMENT ON DATABASE {db.name} IS NULL;',False),
            ('column_write_elsewhere',f'GRANT UPDATE(username) ON public.app_user TO {db.runtime};',f'REVOKE UPDATE(username) ON public.app_user FROM {db.runtime};',False),
            ('set_role_without_inheritance',f'GRANT {db.owner} TO {db.runtime} WITH INHERIT FALSE, SET TRUE;',f'REVOKE {db.owner} FROM {db.runtime};',True),
        ]:
            lab.sql(db,apply,admin=admin)
            try:
                probe=run('negative-'+label,[lab.dotnet,dll,'--mfa-backup-inventory'],input=(json.dumps(initial)+'\n').encode())
                first=json.loads(probe.stdout.splitlines()[0])
                if first.get('status')!='rejected' or first.get('code')!='mfa_backup_identity_rejected':negatives.append(label)
            finally:lab.sql(db,undo,admin=admin)
        print(json.dumps(dict(bindingNegativesAccepted=negatives)),flush=True)
        if negatives:raise RuntimeError('database_binding_negatives_failed')
        results.extend(['shared_database_marker_rejected','column_write_elsewhere_rejected','set_role_without_inheritance_rejected'])
        # Actual child snapshot, a committed writer afterwards, actual pg_dump importing it, restored to a fresh DB.
        process=subprocess.Popen([str(lab.dotnet),str(dll),'--mfa-backup-inventory'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                  stderr=(lab.directory/'snapshot-child.private.log').open('wb'),env=environment(),creationflags=NO_WINDOW)
        try:
            process.stdin.write((json.dumps(initial)+'\n').encode());process.stdin.flush()
            ready=json.loads(process.stdout.readline())
            if ready.get('status')!='snapshot_ready':raise RuntimeError('snapshot_not_ready')
            add_factor(db,8,'disabled','after-exported-snapshot')
            archive=lab.directory/'snapshot.dump';dump(db,archive,ready['snapshot'])
            final=dict(backupId=str(uuid.uuid4()),manifestSha256='a'*64,dumpSha256=sha(archive))
            process.stdin.write((json.dumps(final)+'\n').encode());process.stdin.flush()
            response=json.loads(process.stdout.readline());process.stdin.close()
            if process.wait(timeout=20)!=0 or response.get('status')!='inventory_ready':raise RuntimeError('snapshot_inventory_failed')
            inventory=json.loads(base64.b64decode(response['inventoryBase64']))
            if inventory['factorVersions']!=[1,7]:raise RuntimeError('snapshot_census_includes_later_writer')
        finally:
            if process.poll() is None:process.kill();process.wait()
        target=lab.create_database('snapshot-restore')
        env=environment();env['PGPASSFILE']=str(target.directory/'owner.pgpass')
        restored=run('snapshot-restore',[lab.pg_bin/'pg_restore.exe','-w','-h','127.0.0.1','-p',str(lab.port),'-U',target.owner,
                   '-d',target.name,'--no-owner','--no-acl',archive],env=env)
        if restored.returncode:raise RuntimeError('snapshot_restore_failed')
        if lab.sql(target,"SELECT string_agg(key_version::text||':'||state,',' ORDER BY key_version,state) FROM app_mfa_factor")!='1:disabled,1:pending,7:active':raise RuntimeError('restored_snapshot_versions_states_or_counts_mismatch')
        if lab.sql(db,'SELECT count(*) FROM app_mfa_factor WHERE key_version=8')!='1':raise RuntimeError('concurrent_writer_missing')
        results.append('exported_snapshot_census_and_restored_dump_exclude_later_commit')
        # Pin all actual tool bytes; no hand-selected DLL-only trust.
        tool=lab.directory/'tool';shutil.copytree(dll.parent,tool)
        sums=''.join(sha(file)+'  '+file.relative_to(tool).as_posix()+'\n' for file in sorted(tool.rglob('*')) if file.is_file())
        (tool/'SHA256SUMS').write_text(sums,'ascii',newline='')
        sums_hash=sha(tool/'SHA256SUMS')
        profile=folder/'profile.json';secret=folder/'backup-password.txt';secret.write_text(db.runtime_password,'utf-8')
        profile.write_text(json.dumps(dict(schemaVersion=1,host='127.0.0.1',port=lab.port,database=db.name,user=db.runtime,passwordFile=str(secret))),'utf-8')
        registry=lab.directory/'registry';registry.mkdir()
        config=lab.directory/'operator-input.private.json'
        config.write_text(json.dumps(dict(PostgresBinPath=str(lab.pg_bin),ProfilePath=str(profile),DotnetPath=str(lab.dotnet),
            ToolDirectory=str(tool),ExpectedToolSumsSha256=sums_hash,InstallationId=str(id),DestinationPath=str(lab.directory/'complete-backup'),
            RegistryDirectory=str(registry),EnvelopePath=str(envelope_path),ExpectedEnvelopeSha256=sha(envelope_path),password=password)),'utf-8')
        fingerprint="SELECT md5(COALESCE(jsonb_agg(to_jsonb(f) ORDER BY systemhaus_id,user_id)::text,'')) FROM public.app_mfa_factor f"
        before_native=lab.sql(db,fingerprint)
        script="$c=Get-Content -LiteralPath "+quote(config)+" -Raw|ConvertFrom-Json;$p=@{};foreach($x in $c.PSObject.Properties){if($x.Name -ne 'password'){$p[$x.Name]=$x.Value}};$p.EnvelopePassword=ConvertTo-SecureString $c.password -AsPlainText -Force;& "+quote(ROOT/'tools/windows/New-RackClickMfaDatabaseBackup.ps1')+" @p;exit $LASTEXITCODE"
        created=native('native-create',script)
        if created.get('code')!='mfa_backup_inventory_created':raise RuntimeError('native_create_not_verified')
        container=Path(json.loads(config.read_text())['DestinationPath']);receipt=registry/(created['backupId']+'.json')
        common=' -DotnetPath '+quote(lab.dotnet)+' -ToolDirectory '+quote(tool)+' -ExpectedToolSumsSha256 '+quote(sums_hash)+' -BackupDirectory '+quote(container)+' -ReceiptPath '+quote(receipt)+' -ExpectedReceiptSha256 '+quote(created['receiptSha256'])
        verify='& '+quote(ROOT/'tools/windows/Test-RackClickMfaDatabaseBackup.ps1')+common+';exit $LASTEXITCODE'
        verified=native('native-verify',verify)
        if verified.get('requiredVersions')!=[1,7,8] or verified.get('retirementAuthorized') is not False:raise RuntimeError('native_inventory_versions_invalid')
        results.append('native_backup_and_external_receipt_consumer')
        changed=container/'mfa-inventory.json';original=changed.read_bytes();changed.write_bytes(original+b' ')
        rejected=native('inventory-altered',verify,1)
        if rejected['success']:raise RuntimeError('altered_inventory_accepted')
        changed.write_bytes(original);results.append('altered_inventory_rejected')
        repeated=native('destination-existing',script,1)
        if repeated['code']!='mfa_backup_destination_exists' or changed.read_bytes()!=original:raise RuntimeError('existing_backup_not_preserved')
        results.append('existing_destination_rejected_and_preserved')
        extra=container/'database/extra.json';extra.write_bytes(b'{}')
        rejected=native('historic-extra',verify,1)
        if rejected['success']:raise RuntimeError('historic_extra_accepted')
        extra.unlink();results.append('historic_third_file_rejected')
        # Fresh final facts after read-only operators, not only the same SQL snapshot.
        if lab.sql(db,'SELECT count(*) FROM app_mfa_factor')!='4' or lab.sql(db,fingerprint)!=before_native:raise RuntimeError('operator_changed_factors')
        final_verified=native('final-native-verify',verify)
        if not final_verified['success']:raise RuntimeError('final_native_verification_failed')
        summary=dict(success=True,checks=results,checkCount=len(results),productSchema=45,postgresql='17.11',
            sourceServerSha256=sha(dll),nativeOperatorExecuted=True,concurrentWriterCommitted=True,restoredSnapshotMatchesCensus=True,
            sourceFactorCount=4,sourceFactorRowsPreserved=True,servicesAccessed=False,vmAccessed=False,
            retirementExecuted=False,globalCatalogCompletenessEstablished=False,externalCustodyReal=False)
    finally:
        lab.close()
    summary['ownClusterStopped']=not lab.running
    (lab.directory/'result-sanitized.json').write_text(json.dumps(summary,indent=2)+'\n','utf-8')
    print(json.dumps(summary));return 0

if __name__=='__main__':raise SystemExit(main())
