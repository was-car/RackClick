"""Validation/export/recovery for the optional Demo50 isolated laboratory."""
from __future__ import annotations
import base64
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
import math
from pathlib import Path
import secrets
import subprocess
import threading
import time
import uuid
from prepare_demo50 import (ROOT,NS,COLLECTIONS,INVENTORY_TABLES,Rejected,Session,sha,dump,canonical,
 normalized,login,clone_client,counts,inventory_fingerprint,verify_instance,compatible,counterpart_spec,house_mutation,BENCHMARK_CUSTOMERS)
from pg_support import Client,Database,literal,NO_WINDOW,toolchain

def permissions_and_negatives(lab,db,server,admin,accounts,loaded,seed):
 sessions={};waits=0;bykey={row['key']:row for row in loaded};a=bykey['c01'];b=bykey['c02']
 for name in ('demo.reader','demo.technician','demo.client-admin','demo.no-access'):
  info=next(v for v in accounts if v['username']==name);sessions[name],wait=login(server,name,info['password']);waits+=wait
 assert len(sessions['demo.reader'].request('GET','/api/v1/customers').json())==50
 for name in ('demo.technician','demo.client-admin'):
  assert len(sessions[name].request('GET','/api/v1/customers').json())==1
  assert sessions[name].request('GET',f'/api/v1/customers/{b["customerId"]}/project').status==404
 assert sessions['demo.no-access'].request('GET',f'/api/v1/customers/{a["customerId"]}/project').status==404
 session=Session(admin,a['customerId'],seed,'negative');pa=session.project();pb=admin.request('GET',f'/api/v1/customers/{b["customerId"]}/project').json()
 fingerprint=lambda:inventory_fingerprint(lab,db,INVENTORY_TABLES+('systemhaus','operation','audit_event'))
 before=fingerprint();negative=[]
 def rejected(payload,kind,status,client=admin,revision=None):
  actor=client.request('GET','/api/v1/me').json()['user']['id'];revision=session.revision if revision is None else revision
  response=client.request('POST',session.route+'/commands',{'type':kind,'payload':payload},
   {'X-RackClick-Actor':actor,'If-Match':f'"{revision}"','Idempotency-Key':str(uuid.uuid4())})
  assert response.status==status,(kind,status,response.status)
  assert fingerprint()==before
  negative.append({'kind':kind,'status':status,'error':response.json().get('error')})
 rejected({'name':'Should not be created'},'site.create',403,sessions['demo.reader'])
 first=pa['ports'][0];foreign=pb['ports'][0]
 rejected({'fromPortId':first['id'],'toPortId':foreign['id']},'connections.create',404)
 existing=pa['connections'][0];rejected({'fromPortId':existing['fromPortId'],'toPortId':existing['toPortId']},'connections.create',409)
 power=next(p for p in pa['ports'] if p['type']=='power');copper=next(p for p in pa['ports'] if p['type']=='rj45')
 rejected({'fromPortId':power['id'],'toPortId':copper['id']},'connections.create',409)
 rejected({'name':'Stale write'},'site.create',412,revision=session.revision-1)
 mounted=next(v for row in loaded for v in row['entries'] if v['supportId'])
 owner=next(row for row in loaded if mounted in row['entries'])
 # Use the matching customer's revision/route without changing the rejected source.
 other=Session(admin,owner['customerId'],seed,'mount-negative');request=mounted['request']|{'name':'Occupied slot'}
 response=admin.request('POST',other.route+'/commands',{'type':'device.createHardware','payload':request},
  {'X-RackClick-Actor':other.actor,'If-Match':f'"{other.revision}"','Idempotency-Key':str(uuid.uuid4())})
 assert response.status==409 and fingerprint()==before;negative.append({'kind':'mount occupied','status':409})
 # Demonstrate rollback after the inventory write but before audit/commit.
 lab.sql(db,"CREATE FUNCTION demo50_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='inventory.site.create' OR NEW.action='site.create' THEN RAISE EXCEPTION 'synthetic rollback'; END IF; RETURN NEW; END $$; CREATE TRIGGER demo50_fail_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION demo50_fail_audit()")
 try:rejected({'name':'Deliberate rollback'},'site.create',503)
 finally:lab.sql(db,'DROP TRIGGER demo50_fail_audit ON audit_event; DROP FUNCTION demo50_fail_audit()')
 # Original request and response survive later writes without another command.
 record=a['receipts'][0];replay=admin.request('POST',f'/api/v1/customers/{a["customerId"]}/commands',{'type':record['kind'],'payload':record['payload']},
  {'X-RackClick-Actor':session.actor,'If-Match':f'"{record["expectedRevision"]}"','Idempotency-Key':record['requestId']})
 assert replay.status==200 and replay.json()==record['response'] and fingerprint()==before
 return {'negativeCases':negative,'idempotentReplayNoMutation':True,'readerAll50TechnicianAndClientAdminSingleScope':True,'noAccessHidden':True,'loginRateLimitWaitSeconds':waits}

def percentile(values,p):return sorted(values)[max(0,math.ceil(len(values)*p)-1)]

def process_sample(server):
 # Own child PID, closed integer; no enumeration or change to another service.
 pid=int(server.process.pid)
 code=f'$procDemo=Get-Process -Id {pid} -ErrorAction Stop; [pscustomobject]@{{cpuSeconds=$procDemo.CPU;workingSetBytes=$procDemo.WorkingSet64;privateBytes=$procDemo.PrivateMemorySize64}} | ConvertTo-Json -Compress'
 result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',code],capture_output=True,text=True,creationflags=NO_WINDOW,timeout=15)
 assert result.returncode==0;return json.loads(result.stdout)

def measure(lab,db,server,admin,accounts,loaded,seed):
 barrier=threading.Barrier(10);rows=[];clients=[];waits=0
 bykey={x['key']:x for x in loaded}
 for i in range(1,11):
  account=next(x for x in accounts if x['username']==f'demo.load{i:02}');client,wait=login(server,account['username'],account['password']);waits+=wait
  clients.append((client,bykey[account['scope']]))
 def worker(item):
  client,target=item;actor=client.request('GET','/api/v1/me').json()['user']['id'];barrier.wait(timeout=30);samples=[]
  for _ in range(3):
   started=time.perf_counter();response=client.request('GET',f'/api/v1/customers/{target["customerId"]}/project');elapsed=(time.perf_counter()-started)*1000
   assert response.status==200;samples.append({'kind':'read','milliseconds':elapsed,'bytes':len(response.body)});project=response.json()
  payload={'type':'device.update','payload':{'id':target['terminalId'],'name':'Terminal · carga concurrente '+target['key']}}
  started=time.perf_counter();response=client.request('POST',f'/api/v1/customers/{target["customerId"]}/commands',payload,
   {'X-RackClick-Actor':actor,'If-Match':f'"{project["revision"]}"','Idempotency-Key':str(uuid.uuid5(NS,seed+'/load/'+target['key']))});elapsed=(time.perf_counter()-started)*1000
  assert response.status==200;samples.append({'kind':'write','milliseconds':elapsed,'bytes':len(response.body)})
  return samples
 process_before=process_sample(server)
 transaction_before=lab.sql(db,"SELECT xact_commit,xact_rollback FROM pg_stat_database WHERE datname=current_database()")
 with ThreadPoolExecutor(max_workers=10) as pool:
  for samples in pool.map(worker,clients):rows.extend(samples)
 result={'concurrentDistinctUsers':10,'simultaneousStartBarrier':True,'workloadCustomers':list(BENCHMARK_CUSTOMERS),'readBudgetP95Milliseconds':5000,'writeBudgetP95Milliseconds':10000,'samples':rows,'loginRateLimitWaitSeconds':waits}
 for kind in ('read','write'):
  values=[x['milliseconds'] for x in rows if x['kind']==kind];result[kind]={'samples':len(values),'p50Milliseconds':round(percentile(values,.5),3),'p95Milliseconds':round(percentile(values,.95),3),'maxMilliseconds':round(max(values),3)}
 assert result['read']['p95Milliseconds']<5000 and result['write']['p95Milliseconds']<10000
 distinct=lab.sql(db,"SELECT count(DISTINCT a.actor_id),count(DISTINCT a.after_json->>'customerId') FROM audit_event a JOIN app_user u ON u.id=a.actor_id WHERE a.action='inventory.device.update' AND u.username ~ '^demo[.]load[0-9]{2}$'")
 assert distinct=='10|10';result['persistedDistinctWritingActors']=10;result['persistedDistinctWrittenCustomers']=10
 started=time.perf_counter();response=admin.request('GET','/api/v1/customers');assert response.status==200 and len(response.json())==50
 result['customerListMilliseconds']=round((time.perf_counter()-started)*1000,3);result['customerListBytes']=len(response.body)
 result['serverProcessBefore']=process_before;result['serverProcessAfter']=process_sample(server)
 result['postgresTransactionStatistics']={'before':transaction_before,'after':lab.sql(db,"SELECT xact_commit,xact_rollback FROM pg_stat_database WHERE datname=current_database()"),'asynchronousCountersNotAQueryTrace':True}
 return result

def verify_matrix(lab,db,admin,loaded,plan,definitions):
 models={(m['key'],m['revision']):m for m in definitions};projects={};matrix=[];connected=set();all_ids=[]
 for row in loaded:
  response=admin.request('GET',f'/api/v1/customers/{row["customerId"]}/project');assert response.status==200
  p=response.json();projects[row['key']]=p;used={v for c in p['connections'] for v in (c['fromPortId'],c['toPortId'])};connected|=used
  assert len(used)==2*len(p['connections'])
  for collection in COLLECTIONS:all_ids.extend(x['id'] for x in p[collection])
  groups={g['id']:g for g in p['portGroups']}
  for entry in row['entries']:
   model=models[(entry['profileKey'],entry['profileVersion'])];device,gs,ps=verify_instance(p,model,entry)
   # At least one cable for EVERY operational group, and EVERY materialized power end.
   covered=[g['id'] for g in gs if any(x['groupId']==g['id'] and x['id'] in used for x in ps)]
   power=[v for v in ps if v['type'] in {'power','power_dc'}]
   assert len(covered)==len(gs) and all(x['id'] in used for x in power)
   matrix.append({'profileKey':model['key'],'profileVersion':model['revision'],'customerKey':row['key'],'customerId':row['customerId'],
    'resourceId':entry['resourceId'],'deviceId':entry['deviceId'],'rackId':entry['resourceId'] if model['kind']=='rackContainer' else entry['rack'],
    'roomId':entry['room'],'supportId':entry['supportId'],'groupIds':[g['id'] for g in gs],'portIds':[v['id'] for v in ps],
    'groupCount':len(gs),'portCount':len(ps),'powerEnds':len(power),'powerEndsConnected':len(power),
    'connectionIds':[c['id'] for c in p['connections'] if c['fromPortId'] in {v['id'] for v in ps} or c['toPortId'] in {v['id'] for v in ps}],
    'connectionApplicability':'tested' if gs else 'not_applicable','reason':None if gs else 'No materialized own connectors in approved profile; mount/capacity checked without invented ports.'})
  for rack in p['racks']:
   occupied=sum(d['sizeU'] or 0 for d in p['devices'] if d['rackId']==rack['id']);assert occupied<=rack['sizeU']
  # Helpers may be generic, but all their declared power ends are also covered.
  assert all(v['id'] in used for v in p['ports'] if v['type'] in {'power','power_dc'})
 assert len(matrix)==868 and len({(m['profileKey'],m['profileVersion']) for m in matrix})==868
 assert len(all_ids)==len(set(all_ids)) and sum(m['portCount'] for m in matrix)==16928
 persisted=counts(lab,db);assert persisted['customer']==50
 assert persisted['inventory_port']==sum(len(p['ports']) for p in projects.values())
 assert persisted['inventory_connection_endpoint']==2*persisted['inventory_connection']
 assert int(lab.sql(db,"SELECT count(*) FROM inventory_device WHERE kind='dose'"))==50
 return projects,matrix,persisted

def export_portable(admin,projects,plan,output):
 directory=output/'portable';directory.mkdir();exports=[]
 for customer in plan['customers']:
  key=customer['key'];project=projects[key];cid=project['customerId'];actor=admin.request('GET','/api/v1/me').json()['user']['id'];request=str(uuid.uuid5(NS,plan['seed']+'/export/'+key))
  response=admin.request('POST',f'/api/v1/customers/{cid}/exports/inventory-json',{'formatVersion':1,'scope':'customer'},
   {'X-RackClick-Actor':actor,'If-Match':f'"{project["revision"]}"','Idempotency-Key':request})
  assert response.status==200,(key,response.status)
  receipt=response.json();archive=receipt['archive'];content=base64.b64decode(archive['contentBase64'],validate=True)
  assert len(content)==archive['byteLength'] and hashlib.sha256(content).hexdigest()==archive['sha256']
  document=json.loads(content);assert set(document)=={'formatVersion','kind','scope','customerId','revision','inventory'} and set(document['inventory'])==set(COLLECTIONS)
  assert normalized(dict(customerId=cid,revision=document['revision'],**document['inventory']))==normalized(project)
  name=key+'.inventory.json';(directory/name).write_bytes(content)
  exports.append({'key':key,'name':customer['name'],'scenario':customer['scenario'],'language':customer['language'],'customerId':cid,'file':name,'sha256':archive['sha256'],'bytes':len(content),'revision':document['revision']})
 dump(directory/'manifest.json',{'format':'RackClickDemo50Inventory-v1','schemaVersion':43,'inventoryOnly':True,'securityIncluded':False,'productionDefault':False,'customers':exports})
 (directory/'plan.json').write_bytes(__import__('build_demo50_plan').plan_bytes(plan))
 return directory,exports

def recover_new(lab,db,dll,frontend,output,expected_fingerprint):
 backup=output/'backup-private';backup.mkdir();archive=backup/'data.dump';env=lab.environment();env['PGPASSFILE']=str(db.directory/'owner.pgpass')
 with (backup/'pg_dump-private.log').open('wb') as log:
  process=subprocess.run([str(lab.pg_bin/'pg_dump.exe'),'-h','127.0.0.1','-p',str(lab.port),'-U',db.owner,'-w','-d',db.name,'-Fc','--no-owner','--no-acl','-f',str(archive)],env=env,stdout=log,stderr=log,creationflags=NO_WINDOW,timeout=180)
 assert process.returncode==0
 instance=uuid.uuid4();name='rc_db_'+instance.hex;owner='rc_owner_'+instance.hex;runtime='rc_run_'+instance.hex;directory=lab.directory/name;directory.mkdir()
 restored=Database(name,owner,secrets.token_urlsafe(32),runtime,secrets.token_urlsafe(32),directory)
 # Only closed UUID-derived SQL identifiers in our NEW cluster; values are generated private credentials.
 lab.sql('postgres',f'CREATE ROLE {owner} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(restored.owner_password)}; CREATE ROLE {runtime} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(restored.runtime_password)};',sensitive=True)
 lab.sql('postgres',f"CREATE DATABASE {name} OWNER {owner} TEMPLATE template0 ENCODING 'UTF8';")
 lab.sql(name,f'REVOKE ALL ON DATABASE {name} FROM PUBLIC; GRANT CONNECT ON DATABASE {name} TO {runtime};',admin=True)
 (directory/'owner.pgpass').write_text(f'127.0.0.1:{lab.port}:{name}:{owner}:{restored.owner_password}\n')
 env['PGPASSFILE']=str(directory/'owner.pgpass')
 with (backup/'pg_restore-private.log').open('wb') as log:
  process=subprocess.run([str(lab.pg_bin/'pg_restore.exe'),'-h','127.0.0.1','-p',str(lab.port),'-U',owner,'-w','-d',name,'--no-owner','--no-acl','--single-transaction',str(archive)],env=env,stdout=log,stderr=log,creationflags=NO_WINDOW,timeout=180)
 assert process.returncode==0 and inventory_fingerprint(lab,restored)==expected_fingerprint
 digest=sha(archive);lab.sql(name,f"COMMENT ON DATABASE {name} IS {literal('RackClickRecoveryPending:'+str(instance)+':'+digest)};",admin=True)
 pending=int(lab.sql(restored,'SELECT count(*) FROM app_session'))
 env.update(ConnectionStrings__RackClick=restored.connection(lab.port,runtime=False),Recovery__User='demo.recovered',Recovery__ExpectedDatabase=name,Recovery__BackupSha256=digest)
 password=secrets.token_urlsafe(32)
 with (backup/'recover-admin-private.log').open('w',encoding='utf-8') as log:
  result=subprocess.run([str(lab.dotnet),str(dll),'--recover-admin'],input=password+'\n',env=env,text=True,encoding='utf-8',stdout=log,stderr=log,creationflags=NO_WINDOW,timeout=120,cwd=ROOT/'development/server')
 assert result.returncode==0 and lab.sql(restored,'SELECT count(*) FROM app_session')=='0'
 assert lab.sql(restored,'SELECT count(*) FROM app_mfa_challenge WHERE consumed_at IS NULL')=='0'
 assert inventory_fingerprint(lab,restored)==expected_fingerprint
 lab.grant_runtime(restored);server=lab.start_server(restored,dll=dll,frontend=frontend);client,_=login(server,'demo.recovered',password)
 assert len(client.request('GET','/api/v1/customers').json())==50
 dump(backup/'manifest.json',{'schema':43,'dumpSha256':digest,'dumpBytes':archive.stat().st_size,'restoredToNewDatabase':True,'nativeRecoveryExecuted':True,'sessionsRevoked':pending,'inventoryFingerprintPreserved':True,'securityIncluded':True})
 dump(backup/'recovered-access-private.json',{'url':server.origin,'username':'demo.recovered','password':password,'connectionString':restored.connection(lab.port)})
 # Product invariant: ONE Systemhaus per database. Exercise the other tenant
 # in another NEW database/host, never remove the invariant for a test.
 foreign=lab.create_database('demo50-foreign-systemhaus');foreign_password=secrets.token_urlsafe(32)
 boot=lab.bootstrap(foreign,'demo.foreign',foreign_password,dll=dll)
 (backup/'foreign-bootstrap-private.log').write_text(boot.stdout+'\n'+boot.stderr,encoding='utf-8');assert boot.returncode==0
 lab.grant_runtime(foreign);foreign_server=lab.start_server(foreign,dll=dll);foreign_client,_=login(foreign_server,'demo.foreign',foreign_password)
 foreign_customer=house_mutation(foreign_client,'/api/v1/customers',{'name':'Foreign synthetic customer'},'demo50-foreign','customer',201)['resource']['id']
 assert foreign_client.request('GET',f'/api/v1/customers/{foreign_customer}/project').status==200
 assert client.request('GET',f'/api/v1/customers/{foreign_customer}/project').status==404
 invalid=clone_client(foreign_server,client);assert invalid.request('GET',f'/api/v1/customers/{foreign_customer}/project').status==401
 assert lab.sql(restored,'SELECT count(*) FROM systemhaus')=='1'
 return {'backupCustomBytes':archive.stat().st_size,'backupSha256':digest,'restoredNewDatabase':True,'nativeRecoveryRevokedSessions':pending,'restoreInventoryExact':True,'foreignSystemhausHidden':True,'foreignSystemhausSeparateDatabase':True,'otherTenantSessionRejected':True}

def validate_demo50(lab,db,server,admin,accounts,loaded,plan,definitions,output,dll,frontend,browser):
 access=permissions_and_negatives(lab,db,server,admin,accounts,loaded,plan['seed']);dump(output/'ACCESS-AND-NEGATIVES.json',access)
 performance=measure(lab,db,server,admin,accounts,loaded,plan['seed']);dump(output/'PERFORMANCE.json',performance)
 projects,matrix,persisted=verify_matrix(lab,db,admin,loaded,plan,definitions);dump(output/'coverage-matrix.json',matrix)
 if browser:
  gui_pairs=[]
  for key in ('c01','c11','c21'):
   p=projects[key];used={v for c in p['connections'] for v in (c['fromPortId'],c['toPortId'])};devices={d['id']:d for d in p['devices']}
   candidates=[v for v in p['ports'] if v['id'] not in used and v['status']=='free' and v['type']=='rj45' and devices[v['deviceId']]['rackId']]
   found=next(((a,b) for a in candidates for b in candidates if devices[a['deviceId']]['rackId']==devices[b['deviceId']]['rackId'] and a['face']==b['face'] and compatible(a,b)),None)
   assert found,'No native GUI pair for '+key
   a,b=found;gui_pairs.append({'customerKey':key,'customerId':p['customerId'],'rackId':devices[a['deviceId']]['rackId'],'face':a['face'],'fromPortId':a['id'],'toPortId':b['id']})
  fixture={'customer':loaded[0]['customerId'],'customers':[{'key':c['key'],'name':c['name'],'language':c['language'],'id':row['customerId']} for c,row in zip(plan['customers'],loaded)],'guiPairs':gui_pairs,'projects':[{ 'key':k,'customerId':p['customerId'],'racks':[r['id'] for r in p['racks']]} for k,p in projects.items()]}
  dump(output/'browser-fixture-private.json',fixture);env=lab.environment();private=json.loads((output/'access-private.json').read_text());env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME=private['username'],RACKCLICK_TEST_PASSWORD=private['password'],RACKCLICK_TEST_OUTPUT=str(output/'browser'),RACKCLICK_FIXTURE_PATH=str(output/'browser-fixture-private.json'))
  with (output/'browser-private.log').open('wb') as log:
   process=subprocess.run([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-demo50.mjs')],env=env,cwd=ROOT/'development/frontend',stdout=log,stderr=log,creationflags=NO_WINDOW,timeout=300)
  assert process.returncode==0,'Demo50 browser failed; private log retained'
  projects,matrix,persisted=verify_matrix(lab,db,admin,loaded,plan,definitions);dump(output/'coverage-matrix.json',matrix)
 directory,exports=export_portable(admin,projects,plan,output)
 dump(directory/'coverage-matrix.json',matrix)
 expected={k:normalized(p) for k,p in projects.items()};server.close();restarted=lab.start_server(db,dll=dll,frontend=frontend);private=json.loads((output/'access-private.json').read_text());second,_=login(restarted,private['username'],private['password'])
 for key,project in projects.items():assert normalized(second.request('GET',f'/api/v1/customers/{project["customerId"]}/project').json())==expected[key]
 before=inventory_fingerprint(lab,db);recovery=recover_new(lab,db,dll,frontend,output,before)
 return {'accessAndNegatives':access,'tenUserPerformance':{k:v for k,v in performance.items() if k!='samples'},'finalCounts':persisted,
  'primaryProfilesVerified':len(matrix),'primaryPortsVerified':sum(m['portCount'] for m in matrix),'operationalProfiles':sum(m['connectionApplicability']=='tested' for m in matrix),
  'noOwnPortsNotApplicable':sum(m['connectionApplicability']=='not_applicable' for m in matrix),'portableCustomers':len(exports),'sourceRestartExact':True,'browserExecuted':browser,'recovery':recovery,
  'postgresql':lab.sql('postgres','SHOW server_version'),'mfaProvider':'explicitly_disabled_in_source_laboratory','windowsInstallOrRebootTested':False}
