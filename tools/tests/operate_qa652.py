"""Coordinator-only real QA steps; no login or application DML in the real lab."""
import argparse,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-593-652'
sys.path.insert(0,str(ROOT/'tools/windows'))
from qa_schema10_source652 import Source532
from qa_schema10_switch652 import OwnedRuntime,prepare_operation,activate,validate_operation
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['preflight','prepare','activate','validate']);args=ap.parse_args()
    out=E/('REAL-QA-'+args.action.upper()+'-01.json')
    if out.exists():raise SystemExit('Preserve existing coordinator step evidence')
    pointer=ROOT/'.local/qa-rc9/current.json'
    row={'utc':datetime.now(timezone.utc).isoformat(),'action':args.action,'realRestored':True,'sourceApplicationLogin':False,'sourceApplicationDml':False,'manualWascarResultsWritten':False}
    if args.action=='preflight':
        source=Source532(Path(json.loads(pointer.read_bytes())['directory']),pointer,real=True)
        OwnedRuntime(source.directory,source.cfg).quiet()
        row.update(valid=True,sourceDirectory=source.directory.relative_to(ROOT).as_posix(),sourceConfigSha256=sha(source.directory/'manual-qa.json'),sourcePointerSha256=sha(pointer),sourceSchema=9,sourceQuiet=True,sourceDatabaseProfiles=len(source.databases),sourceInputHashes=source.hashes,postgresqlStarted=False)
    else:
        go=json.loads((E/'COORDINATOR-GO.json').read_bytes())
        assert go['authorizedRealQaCopySelection'] is True and go['valid'] is True
        for p,h in go['gates'].items():assert sha(ROOT/p)==h
        row['goSha256']=sha(E/'COORDINATOR-GO.json')
        preflight=json.loads((E/'REAL-QA-PREFLIGHT-01.json').read_bytes());source=ROOT/preflight['sourceDirectory']
        if args.action=='prepare':
            assert sha(source/'manual-qa.json')==preflight['sourceConfigSha256'] and sha(pointer)==preflight['sourcePointerSha256']
            result=prepare_operation(source,pointer,real=True)
            row.update(valid=result.state=='prepared',state=result.state,sourceDirectory=source.relative_to(ROOT).as_posix(),candidateDirectory=result.candidate.directory.relative_to(ROOT).as_posix(),sourceSchema=9,candidateSchema=10,selectedSchema=9,leftRunning=False,sourcePreserved=True,logicalTableCount=len(result.candidate.record['candidateSnapshot']),newSharedTablesEmpty=True,originalPermissionGrantsPreserved=True)
        else:
            prepared=json.loads((E/'REAL-QA-PREPARE-01.json').read_bytes());candidate=ROOT/prepared['candidateDirectory']
            if args.action=='activate':
                result=activate(source,pointer,candidate,real=True)
                row.update(valid=result.state=='committed',state=result.state,sourceDirectory=source.relative_to(ROOT).as_posix(),candidateDirectory=candidate.relative_to(ROOT).as_posix(),sourceSchema=9,selectedSchema=10,leftRunning=False,sourcePreserved=True,activationJournalSha256=sha(result.journal),pointerSha256=sha(pointer))
            else:
                current=validate_operation(source,pointer,candidate,real=True,selected=True)
                row.update(valid=True,state='static_validated',selectedSchema=10,candidateDirectory=candidate.relative_to(ROOT).as_posix(),databaseTestExecuted=False,leftRunning=False,sourceConfigSha256=sha(source/'manual-qa.json'),currentConfigSha256=sha(candidate/'manual-qa.json'),currentBundleSha256=current.cfg['bundleSha256'],currentDllSha256=current.cfg['dllSha256'])
    write(out,row);print(json.dumps(row,indent=2));return 0 if row['valid'] else 1
if __name__=='__main__':raise SystemExit(main())
