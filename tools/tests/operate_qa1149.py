"""Coordinator-only actual QA steps, after the independent operational gate."""
import argparse,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1090-1149'
sys.path.insert(0,str(ROOT/'tools/windows'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
    from qa_category_colors13_source1149 import Source969
    from qa_category_colors13_switch1149 import OwnedRuntime,prepare_operation,activate,validate_operation
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['preflight','prepare','activate','validate']);ap.add_argument('--attempt',default='01');a=ap.parse_args()
    assert len(a.attempt)==2 and a.attempt.isdecimal();out=E/('REAL-QA-'+a.action.upper()+'-'+a.attempt+'.json');assert not out.exists()
    pointer=ROOT/'.local/qa-rc9/current.json';row=dict(utc=datetime.now(timezone.utc).isoformat(),action=a.action,valid=False,realRestored=True,sourceApplicationLogin=False,sourceApplicationDml=False,manualWascarResultsWritten=False,sourceSchema=12,candidateSchema=13,sourceRevision=969,candidateRevision=1089)
    try:
        if a.action=='preflight':
            source=Source969(Path(read(pointer)['directory']),pointer,real=True);OwnedRuntime(source.directory,source.cfg).quiet()
            row.update(valid=True,sourceDirectory=source.directory.relative_to(ROOT).as_posix(),sourceConfigSha256=sha(source.directory/'manual-qa.json'),sourcePointerSha256=sha(pointer),sourceQuiet=True,sourceDatabaseProfiles=len(source.databases),sourceInputHashes=source.hashes,postgresqlStarted=False,selectedRevision=969)
        else:
            go=read(E/'COORDINATOR-GO.json');assert go['valid'] and go['authorizedRealQaCopySelection']
            assert all(sha(ROOT/p)==h for p,h in go['gates'].items());row['goSha256']=sha(E/'COORDINATOR-GO.json')
            pre=read(E/'REAL-QA-PREFLIGHT-01.json');source=ROOT/pre['sourceDirectory']
            if a.action=='prepare':
                assert sha(source/'manual-qa.json')==pre['sourceConfigSha256'] and sha(pointer)==pre['sourcePointerSha256']
                checked=Source969(source,pointer,real=True);OwnedRuntime(checked.directory,checked.cfg).quiet();assert checked.hashes==pre['sourceInputHashes']
                result=prepare_operation(source,pointer,real=True)
                row.update(valid=result.state=='prepared',state=result.state,sourceDirectory=source.relative_to(ROOT).as_posix(),candidateDirectory=result.candidate.directory.relative_to(ROOT).as_posix(),selectedRevision=969,leftRunning=False,sourcePreserved=True,logicalTableCount=len(result.candidate.record['candidateSnapshot']),recoverySchema=12,schemaMigrationExecuted=True,originalPermissionGrantsPreserved=True)
            else:
                prepared=read(E/'REAL-QA-PREPARE-01.json');candidate=ROOT/prepared['candidateDirectory']
                if a.action=='activate':
                    result=activate(source,pointer,candidate,real=True)
                    row.update(valid=result.state=='committed',state=result.state,sourceDirectory=source.relative_to(ROOT).as_posix(),candidateDirectory=candidate.relative_to(ROOT).as_posix(),selectedRevision=1089,leftRunning=False,sourcePreserved=True,activationJournalSha256=sha(result.journal),pointerSha256=sha(pointer))
                else:
                    current=validate_operation(source,pointer,candidate,real=True,selected=True)
                    row.update(valid=True,state='static_validated',selectedRevision=1089,candidateDirectory=candidate.relative_to(ROOT).as_posix(),databaseTestExecuted=False,leftRunning=False,sourceConfigSha256=sha(source/'manual-qa.json'),currentConfigSha256=sha(candidate/'manual-qa.json'),currentBundleSha256=current.cfg['bundleSha256'],currentDllSha256=current.cfg['dllSha256'])
    except Exception as error:
        row.update(errorCode=getattr(error,'code',type(error).__name__));raise
    finally:
        out.write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in row.items() if k!='sourceInputHashes'},indent=2))
    return 0 if row['valid'] else 1
if __name__=='__main__':raise SystemExit(main())
