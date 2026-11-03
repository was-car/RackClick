"""Coordinator operation on the actual QA; metadata only until reviewed GO."""
import argparse,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1210-1269'
sys.path.insert(0,str(ROOT/'tools/windows'))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
 from qa_artifact13_source1269 import Source13
 from qa_artifact13_update1269 import OwnedRuntime,update_operation,validate_operation
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['preflight','update','validate']);ap.add_argument('--attempt',default='01');a=ap.parse_args();assert len(a.attempt)==2 and a.attempt.isdecimal()
 out=E/('REAL-QA-'+a.action.upper()+'-'+a.attempt+'.json');assert not out.exists();pointer=ROOT/'.local/qa-rc9/current.json';directory=Path(read(pointer)['directory'])
 row=dict(utc=datetime.now(timezone.utc).isoformat(),action=a.action,valid=False,directory=directory.relative_to(ROOT).as_posix(),schema=13,recoverySchema=12,databaseReconstructed=False,schemaMigrationExecuted=False,applicationLogin=False,applicationDml=False,manualWascarResultsWritten=False)
 try:
  if a.action=='preflight':
   source=Source13(directory,pointer,real=True);OwnedRuntime(directory,source.cfg).quiet();assert source.revision==1089
   initial=read(E/'INICIO-02.json');assert sha(pointer)==initial['guards'][pointer.relative_to(ROOT).as_posix()]
   row.update(valid=True,sourceRevision=1089,sourceConfigSha256=sha(directory/'manual-qa.json'),pointerSha256=sha(pointer),sourceInputHashes=source.hashes,sourceQuiet=True,postgresqlStarted=False)
  else:
   go=read(E/'COORDINATOR-GO.json');assert go['valid'] and go['authorizedRealQaArtifactUpdate'];assert all(sha(ROOT/p)==h for p,h in go['gates'].items());row['goSha256']=sha(E/'COORDINATOR-GO.json')
   pre=read(E/'REAL-QA-PREFLIGHT-01.json');assert sha(pointer)==pre['pointerSha256']
   if a.action=='update':
    source=Source13(directory,pointer,real=True);OwnedRuntime(directory,source.cfg).quiet();assert source.revision==1089 and source.hashes==pre['sourceInputHashes'] and sha(directory/'manual-qa.json')==pre['sourceConfigSha256']
    result=update_operation(directory,pointer,real=True);state=read(result.journal);assert result.state=='committed'
    row.update(valid=True,state=result.state,selectedRevision=1209,serverRevision=1089,operationDirectory=result.operation.relative_to(ROOT).as_posix(),journalSha256=sha(result.journal),leftRunning=state['leftRunning'],pointerSha256=sha(pointer),idempotent=result.idempotent)
   else:
    source=validate_operation(directory,pointer,real=True);assert source.revision==1209;OwnedRuntime(directory,source.cfg,source.operation).quiet()
    old=read(ROOT/read(E/'INICIO-02.json')['originalConfigurationArchive']);current=read(directory/'manual-qa.json');changed=sorted(k for k in set(old)|set(current) if old.get(k)!=current.get(k));assert changed==['artifactDirectory','bundleSha256']
    states=source.record['databaseStates'];assert len(states['databases']['primary']['snapshot'])==39 and len(states['databases']['recovery969']['snapshot'])==37
    row.update(valid=True,state='static_validated',selectedRevision=1209,serverRevision=1089,databaseTestExecuted=False,operationDirectory=source.operation.relative_to(ROOT).as_posix(),currentConfigSha256=sha(directory/'manual-qa.json'),pointerSha256=sha(pointer),changedConfigFields=changed,leftRunning=False,primaryTables=39,recoveryTables=37,baselineRenewed=False)
 except Exception as error:
  row['errorCode']=getattr(error,'code',type(error).__name__);raise
 finally:
  with out.open('x',encoding='utf-8') as f:json.dump(row,f,indent=2);f.write('\n')
  print(json.dumps({k:v for k,v in row.items() if k!='sourceInputHashes'}))
 return 0 if row['valid'] else 1
if __name__=='__main__':raise SystemExit(main())
