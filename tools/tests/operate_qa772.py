"""Coordinator real QA steps after technical GO; never app login or app DML."""
import argparse,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-713-772'
sys.path.insert(0,str(ROOT/'tools/windows'))
from qa_schema11_source772 import Source592
from qa_schema11_switch772 import OwnedRuntime,prepare_operation,activate,validate_operation
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['preflight','prepare','activate','validate']);ap.add_argument('--attempt',default='01');a=ap.parse_args()
    assert len(a.attempt)==2 and a.attempt.isdecimal()
    out=E/('REAL-QA-'+a.action.upper()+'-'+a.attempt+'.json')
    if out.exists():raise SystemExit('Preserve existing coordinator evidence')
    pointer=ROOT/'.local/qa-rc9/current.json';row=dict(utc=datetime.now(timezone.utc).isoformat(),action=a.action,valid=False,realRestored=True,sourceApplicationLogin=False,sourceApplicationDml=False,manualWascarResultsWritten=False)
    try:
        if a.action=='preflight':
            source=Source592(Path(read(pointer)['directory']),pointer,real=True);OwnedRuntime(source.directory,source.cfg).quiet()
            row.update(valid=True,sourceDirectory=source.directory.relative_to(ROOT).as_posix(),sourceConfigSha256=sha(source.directory/'manual-qa.json'),sourcePointerSha256=sha(pointer),sourceSchema=10,sourceQuiet=True,sourceDatabaseProfiles=len(source.databases),sourceInputHashes=source.hashes,postgresqlStarted=False)
        else:
            go=read(E/'COORDINATOR-GO.json');assert go['authorizedRealQaCopySelection'] and go['valid']
            assert all(sha(ROOT/p)==h for p,h in go['gates'].items());row['goSha256']=sha(E/'COORDINATOR-GO.json')
            pre=read(E/'REAL-QA-PREFLIGHT-01.json');source=ROOT/pre['sourceDirectory']
            if a.action=='prepare':
                assert sha(source/'manual-qa.json')==pre['sourceConfigSha256'] and sha(pointer)==pre['sourcePointerSha256']
                checked=Source592(source,pointer,real=True);OwnedRuntime(checked.directory,checked.cfg).quiet()
                assert checked.hashes==pre['sourceInputHashes'], 'source_inputs_changed_after_preflight'
                result=prepare_operation(source,pointer,real=True)
                row.update(valid=result.state=='prepared',state=result.state,sourceDirectory=source.relative_to(ROOT).as_posix(),candidateDirectory=result.candidate.directory.relative_to(ROOT).as_posix(),sourceSchema=10,candidateSchema=11,selectedSchema=10,leftRunning=False,sourcePreserved=True,logicalTableCount=len(result.candidate.record['candidateSnapshot']),newPreferenceTablesEmpty=True,originalPermissionGrantsPreserved=True)
            else:
                prepared=read(E/'REAL-QA-PREPARE-01.json');candidate=ROOT/prepared['candidateDirectory']
                if a.action=='activate':
                    result=activate(source,pointer,candidate,real=True)
                    row.update(valid=result.state=='committed',state=result.state,sourceDirectory=source.relative_to(ROOT).as_posix(),candidateDirectory=candidate.relative_to(ROOT).as_posix(),sourceSchema=10,selectedSchema=11,leftRunning=False,sourcePreserved=True,activationJournalSha256=sha(result.journal),pointerSha256=sha(pointer))
                else:
                    current=validate_operation(source,pointer,candidate,real=True,selected=True)
                    row.update(valid=True,state='static_validated',selectedSchema=11,candidateDirectory=candidate.relative_to(ROOT).as_posix(),databaseTestExecuted=False,leftRunning=False,sourceConfigSha256=sha(source/'manual-qa.json'),currentConfigSha256=sha(candidate/'manual-qa.json'),currentBundleSha256=current.cfg['bundleSha256'],currentDllSha256=current.cfg['dllSha256'])
    except Exception as error:
        row.update(errorCode=getattr(error,'code',type(error).__name__));raise
    finally:
        with out.open('x',encoding='utf-8') as f:json.dump(row,f,indent=2);f.write('\n')
        print(json.dumps({k:v for k,v in row.items() if k not in ['sourceInputHashes']},indent=2))
    return 0 if row['valid'] else 1
if __name__=='__main__':raise SystemExit(main())
