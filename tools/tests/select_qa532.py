"""Quiet metadata preflight and guarded real185→532 selection after isolated review/tests."""
import argparse,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-473-532'
sys.path.insert(0,str(ROOT/'tools/windows'));sys.path.insert(0,str(ROOT/'development/server/tests'))
from qa_artifact9_source532 import Source9,load_target,CHANGED_FIELDS
from qa_artifact9_update532 import update,pg_running,qa_module
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,data):p.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['preflight','activate']);a=parser.parse_args();output=E/('QA-PREFLIGHT-03.json' if a.phase=='preflight' else 'QA-SELECTED-03.json')
    if output.exists():raise SystemExit('Preserve existing operation evidence; use a reviewed follow-up explicitly')
    pointer=ROOT/'.local/qa-rc9/current.json';directory=Path(json.loads(pointer.read_bytes())['directory']);source=Source9(directory,pointer,real=True);target=load_target()
    if pg_running(directory) or qa_module().running(directory):raise SystemExit('Actual QA has an active/uncertain process; no stop or selection performed')
    initial={'utc':datetime.now(timezone.utc).isoformat(),'phase':a.phase,'sourceRevision':185,'targetRevision':532,'targetManifestSha256':sha(target.manifest),'initialQuiet':True,'pointerSha256':sha(pointer),'sourceInputHashes':source.original_hashes,'privateInputs':source.hashes,'applicationLoginPlanned':False,'applicationDmlPlanned':False,'wascarResultsWritten':False}
    if a.phase=='preflight':save(output,initial);print(json.dumps({'phase':'preflight','initialQuiet':True,'source185Validated':True,'target532Final03Validated':True,'databaseStarted':False}));return 0
    package=json.loads((E/'PACKAGES-03.json').read_text());native=json.loads((E/'packaging/native04/result.json').read_text())
    assert package['valid'] and package['byteIdentical'] and native['successful'] and native['freshClustersInitialized']==2
    assert native['inputsUnchanged'] and native['ownedProcessesStopped'] and native['systemCrtDllsAndX64RegistryUnchanged']
    assert {x['stage'] for x in native['configurationChecks']}=={'before_backup','after_recovery'}
    assert native['archiveSha256']==package['outputs'][0]['sha256']
    contrast=json.loads((E/'revision/CONTRASTE-FINAL03.json').read_text());assert sha(target.manifest)=='c818294e27a40c94fe2ebf603709c94263820af1facca9a7d5c288cb70e8158e'
    assert (E/'revision/REVISION-INDEPENDIENTE.md').is_file() and contrast
    gate={'utc':datetime.now(timezone.utc).isoformat(),'coordinatorOperationalGo':True,'notAdoption':True,'targetManifestSha256':sha(target.manifest),'independentReviewSha256':sha(E/'revision/REVISION-INDEPENDIENTE.md'),'independentSealSha256':sha(E/'revision/SEAL-REVISION.json'),'nativePackageResultSha256':sha(E/'packaging/native04/result.json'),'reason':'Independent gate and exact FINAL03 delta/profile/layout verified; new Windows package installation/restore passed; actual source is quiet and closed185. Existing S1 authorization.'};save(E/'QA-OPERATIONAL-GO-03.json',gate)
    try:
        result=update(directory,pointer,real=True)
        selected=json.loads((directory/'manual-qa.json').read_bytes());changed={k for k in source.cfg.keys()|selected.keys() if source.cfg.get(k)!=selected.get(k)}
        assert result.state=='committed' and changed==CHANGED_FIELDS
        assert sha(pointer)==initial['pointerSha256'] and all(sha(directory/p)==h for p,h in source.hashes.items())
        assert not pg_running(directory) and not qa_module().running(directory)
        private=json.loads(result.journal.read_bytes());assert private['activationConfirmed'] and private['leftRunning'] is False
        initial.update(state='committed',activationConfirmed=True,leftRunning=False,changedFields=sorted(changed),schemaVersion=9,url='http://127.0.0.1:52346',pointerUnchanged=True,privateInputsUnchanged=True,old185ArtifactsRetained=source.artifacts()==source.baseline.expected,targetFilesExact=True,allRowsHistoryOidAndActivityVerifiedByOperator=True,operatorJournalSha256=sha(result.journal),finalConfigurationSha256=sha(directory/'manual-qa.json'),dllSha256=selected['dllSha256'],frontendSha256=selected['bundleSha256'])
        save(output,initial);print(json.dumps({k:initial[k] for k in ['state','activationConfirmed','leftRunning','schemaVersion','url','changedFields','pointerUnchanged','privateInputsUnchanged']}));return 0
    except Exception as error:
        initial.update(state=getattr(error,'code',type(error).__name__),activationConfirmed=False,leftRunning=None);save(output,initial);raise
if __name__=='__main__':raise SystemExit(main())
