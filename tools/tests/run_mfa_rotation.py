"""Pinned Windows/PG17 rotation tests. Fresh owned clusters/DBs only; no installed services or VM operations."""
from pathlib import Path
import argparse,hashlib,json,os,secrets,subprocess,sys,time,uuid,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'development/server/tests'))
from pg_support import Lab,Database,literal,NO_WINDOW

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--source-root',type=Path,required=True)
 p.add_argument('--expected-server-sha256',required=True);p.add_argument('--expected-tests-sha256',required=True)
 p.add_argument('--mode',choices=['database','crashes','negatives','regression'],default='database')
 p.add_argument('--only-cut',default=None)
 a=p.parse_args();source=a.source_root.resolve(strict=True)
 if not source.is_relative_to((ROOT/'.local').resolve()):raise ValueError('isolated_source_required')
 server=source/'development/server';dll=server/'src/RackClick.Server/bin/Release/net10.0/RackClick.Server.dll'
 tests=server/'tests/RackClick.Quality.Tests/bin/Release/net10.0/RackClick.Quality.Tests.dll'
 if sha(dll)!=a.expected_server_sha256 or sha(tests)!=a.expected_tests_sha256:raise ValueError('rotation_binary_pin_invalid')
 lab=Lab('f0603-rotation');base_env=lab.environment;rows=[]
 def environment():
  env=base_env()
  for key in list(env):
   if key.startswith(('RACKCLICK_TEST_','RACKCLICK_F060','ConnectionStrings__','MfaKeyStore__','SqlSecret__','CORECLR_','DOTNET_STARTUP_','DOTNET_Diagnostic','DOTNET_EnableEvent','DOTNET_EnableProfil')):env.pop(key)
  env['DOTNET_EnableDiagnostics']='0'
  return env
 lab.environment=environment
 def new_database():
  id=uuid.uuid4();private=lab.directory/('native-'+id.hex);private.mkdir()
  db=Database('rc_db_'+id.hex,'rc_owner_'+id.hex,secrets.token_urlsafe(32),'rc_runtime_'+id.hex,secrets.token_urlsafe(32),private)
  lab.sql('postgres',f'CREATE ROLE {db.owner} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(db.owner_password)}; CREATE ROLE {db.runtime} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(db.runtime_password)};',sensitive=True)
  lab.sql('postgres',f"CREATE DATABASE {db.name} OWNER {db.owner} TEMPLATE template0 ENCODING 'UTF8';")
  (private/'owner.pgpass').write_text(f'127.0.0.1:{lab.port}:*:{db.owner}:{db.owner_password}\n','utf-8')
  boot=lab.bootstrap(db,'synthetic-rotation-admin',secrets.token_urlsafe(32),dll=dll)
  (private/'bootstrap.private.log').write_text(boot.stdout+boot.stderr,'utf-8')
  if boot.returncode or lab.sql(db,'SELECT count(*),max(version) FROM schema_migration')!='46|46':raise RuntimeError('rotation_bootstrap46_failed')
  lab.grant_runtime(db)
  lab.sql(db,f'REVOKE ALL ON public.app_mfa_rotation_witness FROM {db.runtime}; GRANT SELECT ON public.app_mfa_rotation_witness TO {db.runtime};')
  # Historical F0602 fixtures add UUID/staging levels; keep their owned root short instead of changing the writer.
  fixtures=(lab.directory/'f') if a.mode=='regression' else private/'fixtures';fixtures.mkdir()
  return id,db,private,fixtures
 def run(context,selection,label):
  if sha(dll)!=a.expected_server_sha256 or sha(tests)!=a.expected_tests_sha256:raise ValueError('rotation_binary_changed_before_execution')
  env=environment();env['RACKCLICK_F0603_CONTEXT']=str(context)
  if a.mode=='regression':
   env['RACKCLICK_TEST_PG_ADMIN']=f'Host=127.0.0.1;Port={lab.port};Database=postgres;Username={lab.admin};Password={lab.admin_password};Pooling=false;SSL Mode=Disable'
   env['RACKCLICK_F0602_MAINT_CONTEXT']=str(context)
  cmd=[str(lab.dotnet),'test','tests/RackClick.Quality.Tests/RackClick.Quality.Tests.csproj','-c','Release','--no-build','--no-restore','--filter',selection,
       '--logger','trx;LogFileName='+str(lab.directory/(label+'.trx')),'-bl:'+str(lab.directory/(label+'-{}.binlog'))]
  with (lab.directory/(label+'.private.log')).open('wb') as log:
   if not label.startswith('cut-'):return subprocess.run(cmd,cwd=server,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240,creationflags=NO_WINDOW).returncode
   value=json.loads(context.read_text('utf-8'));marker=Path(value['marker'])
   process=subprocess.Popen(cmd,cwd=server,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=NO_WINDOW)
   try:
    deadline=time.monotonic()+60
    while process.poll() is None and not marker.is_file() and time.monotonic()<deadline:time.sleep(.1)
    if not marker.is_file():return process.wait(timeout=5)
    # Kill ONLY this Popen-owned test invocation and its descendants, never a service/VM or a PID supplied as input.
    killed=subprocess.run(['taskkill.exe','/PID',str(process.pid),'/T','/F'],stdout=log,stderr=log,creationflags=NO_WINDOW)
    if killed.returncode:raise RuntimeError('owned_trial_tree_termination_failed')
    return process.wait(timeout=15)
   finally:
    if process.poll() is None:
     subprocess.run(['taskkill.exe','/PID',str(process.pid),'/T','/F'],stdout=log,stderr=log,creationflags=NO_WINDOW)
     process.wait(timeout=15)
 def restore_trial(db,value,index):
  # Restore the observed database AFTER the cut, before any source reconciliation, into another new cluster.
  target=Lab('f0603-restore');dump=lab.directory/(f'cut-{index}.dump')
  source_counts=lab.sql(db,"SELECT (SELECT count(*) FROM app_mfa_rotation_witness),(SELECT md5(string_agg(encode(secret_ciphertext,'hex'),',' ORDER BY user_id)) FROM app_mfa_factor)")
  def pg(executable,database,port,args,passfile,label):
   env=environment()
   for name in list(env):
    if name.startswith('PG'):env.pop(name)
   env['PGPASSFILE']=str(passfile)
   with (lab.directory/(label+'.private.log')).open('wb') as out:
    rc=subprocess.run([str(lab.pg_bin/executable),'-w','-h','127.0.0.1','-p',str(port),'-U',database.owner,*args],env=env,stdout=out,stderr=subprocess.STDOUT,creationflags=NO_WINDOW,timeout=60).returncode
   if rc:raise RuntimeError('rotation_dump_or_restore_failed')
  try:
   pg('pg_dump.exe',db,lab.port,['-d',db.name,'-F','c','--no-owner','--no-acl','-f',str(dump)],db.directory/'owner.pgpass',f'dump-{index}')
   target.start();private=target.directory/'restored';private.mkdir()
   copy=Database(db.name,db.owner,secrets.token_urlsafe(32),db.runtime,secrets.token_urlsafe(32),private)
   target.sql('postgres',f'CREATE ROLE {copy.owner} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(copy.owner_password)}; CREATE ROLE {copy.runtime} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(copy.runtime_password)};',sensitive=True)
   target.sql('postgres',f"CREATE DATABASE {copy.name} OWNER {copy.owner} TEMPLATE template0 ENCODING 'UTF8';")
   (private/'owner.pgpass').write_text(f'127.0.0.1:{target.port}:*:{copy.owner}:{copy.owner_password}\n','utf-8')
   pg('pg_restore.exe',copy,target.port,['--single-transaction','--exit-on-error','--no-owner','--no-acl','-d',copy.name,str(dump)],private/'owner.pgpass',f'restore-{index}')
   target.grant_runtime(copy);target.sql(copy,f'REVOKE ALL ON public.app_mfa_rotation_witness FROM {copy.runtime}; GRANT SELECT ON public.app_mfa_rotation_witness TO {copy.runtime};')
   restored=dict(value,stage='restore-verify',ownerConnection=copy.connection(target.port,False),runtimeConnection=copy.connection(target.port))
   context=private/'context.private.json';context.write_text(json.dumps(restored),'utf-8')
   rc=run(context,'FullyQualifiedName~MfaRotationProcessTests.Worker',f'restore-verify-{index}')
   if rc:raise RuntimeError('rotation_restored_reconciliation_failed')
   if lab.sql(db,"SELECT (SELECT count(*) FROM app_mfa_rotation_witness),(SELECT md5(string_agg(encode(secret_ciphertext,'hex'),',' ORDER BY user_id)) FROM app_mfa_factor)")!=source_counts:raise RuntimeError('restore_modified_source_database')
   return dict(realCustomDump=True,singleTransactionRestore=True,sourceDatabaseUnchanged=True,verifyExitCode=rc,clusterIndependent=True)
  finally:target.close()
 try:
  lab.start()
  if a.mode in ['database','regression']:
   id,db,private,fixtures=new_database();context=private/'context.private.json'
   context.write_text(json.dumps(dict(installationId=str(id),ownerConnection=db.connection(lab.port,False),runtimeConnection=db.connection(lab.port),fixtureRoot=str(fixtures),ownerPgpass=str(private/'owner.pgpass'),postgresBin=str(lab.pg_bin))),'utf-8')
   selected='FullyQualifiedName~MfaRotationDatabaseTests'
   if a.mode=='regression':selected+='|FullyQualifiedName~WindowsMfaRotationStoreTests|FullyQualifiedName~WindowsMfaRotationStartupReceiptTests|FullyQualifiedName~MfaRotationContractTests|FullyQualifiedName~WindowsMfaMaintenanceStoreTests|FullyQualifiedName~MfaBackupCatalogTests|FullyQualifiedName~MfaMaintenanceCommandTests|FullyQualifiedName~MfaWindowsHostHttpTests|FullyQualifiedName~MfaWindowsHostCompositionTests|FullyQualifiedName~MfaMaintenancePostgresTests|FullyQualifiedName~MfaMaintenanceAdmissionTests|FullyQualifiedName~WindowsMfaMaintenanceServiceTests|FullyQualifiedName~MfaKeyRetentionTests|FullyQualifiedName~MfaBackupInventoryCommandTests|FullyQualifiedName~MfaKeyStoreInitCommandTests|FullyQualifiedName~WindowsMfaKeyStoreWriterTests'
   rc=run(context,selected,'tests');counts=ET.parse(lab.directory/'tests.trx').find('.//{*}Counters').attrib
   rows.append(dict(mode=a.mode,exitCode=rc,counts=counts));success=rc==0 and int(counts['notExecuted'])==0
  elif a.mode=='negatives':
   for i,negative in enumerate(['lease_data_verified','lease_before_rotation_complete','receipt_collision']):
    id,db,private,fixtures=new_database();context=private/'context.private.json'
    context.write_text(json.dumps(dict(installationId=str(id),ownerConnection=db.connection(lab.port,False),runtimeConnection=db.connection(lab.port),fixtureRoot=str(fixtures),caseState=str(private/'state.private.json'),marker=str(private/'unused-marker.json'),cut=negative,stage='cut')),'utf-8')
    rc=run(context,'FullyQualifiedName~MfaRotationProcessTests.Worker',f'negative-{i}')
    counts=ET.parse(lab.directory/(f'negative-{i}.trx')).find('.//{*}Counters').attrib
    rows.append(dict(negative=negative,exitCode=rc,counts=counts))
    if rc or int(counts['notExecuted']):raise RuntimeError('rotation_negative_failed')
   success=True
  else:
   cuts=['planned','before_key_publish','after_key_publish','before_additive_publish','after_additive_publish','material_ready','before_db_commit','after_db_commit','before_final_publish','after_final_publish','data_verified','before_startup_receipt','after_startup_receipt','before_rotation_complete','after_rotation_complete']
   if a.only_cut:
    if a.only_cut not in cuts:raise ValueError('unknown_cut')
    cuts=[a.only_cut]
   for i,cut in enumerate(cuts):
    id,db,private,fixtures=new_database();context=private/'context.private.json';state=private/'state.private.json'
    value=dict(installationId=str(id),ownerConnection=db.connection(lab.port,False),runtimeConnection=db.connection(lab.port),fixtureRoot=str(fixtures),caseState=str(state),marker=str(private/'cut-marker.json'),cut=cut,stage='cut')
    context.write_text(json.dumps(value),'utf-8');first=run(context,'FullyQualifiedName~MfaRotationProcessTests.Worker',f'cut-{i}')
    if first==0 or not Path(value['marker']).is_file():raise RuntimeError('requested_process_cut_not_observed')
    observed=json.loads(Path(value['marker']).read_text('utf-8'))
    if observed.get('phase')!=cut or observed.get('pid',0)<=0:raise RuntimeError('wrong_cut_marker')
    restored=restore_trial(db,value,i) if cut in ['before_db_commit','after_db_commit'] else None
    value['stage']='source-guard-reject' if cut=='before_db_commit' else 'resume'
    context.write_text(json.dumps(value),'utf-8');second=run(context,'FullyQualifiedName~MfaRotationProcessTests.Worker',f'resume-{i}')
    counts=ET.parse(lab.directory/(f'resume-{i}.trx')).find('.//{*}Counters').attrib
    rows.append(dict(phase=cut,terminatedTestHost=True,cutExitCode=first,resumeExitCode=second,resumeCounts=counts,restore=restored))
    if second or int(counts['notExecuted']):raise RuntimeError('rotation_resume_test_failed')
   success=True
 finally:lab.close()
 if sha(dll)!=a.expected_server_sha256 or sha(tests)!=a.expected_tests_sha256:raise ValueError('rotation_binary_changed_during_trial')
 result=dict(success=success,postgresql='17.11',schema=46,mode=a.mode,serverSha256=sha(dll),testsSha256=sha(tests),cases=rows,
             ownClusterStopped=not lab.running,vmOperations=0,installedServiceOperations=0,powerFailureTested=False,privateLab=str(lab.directory))
 (lab.directory/'result-sanitized.json').write_text(json.dumps(result,indent=2)+'\n','utf-8');print(json.dumps(result));return 0 if success else 1

if __name__=='__main__':raise SystemExit(main())
