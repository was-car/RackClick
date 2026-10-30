"""Coordinator operational GO after native installation/recovery and independent review."""
import argparse,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-713-772'
sys.path.insert(0,str(ROOT/'tools/windows'))
from qa_schema11_source772 import Source592
from qa_schema11_switch772 import OwnedRuntime
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--package-attempt',default='02');ap.add_argument('--native',default='windows/native02/result.json');ap.add_argument('--wrapper',default='windows/WRAPPER-COMPOSITE.json');ap.add_argument('--transition',default='qa-transition/all01/result.json');ap.add_argument('--independent',default='revision/source-activity01/result.json');a=ap.parse_args()
    output=E/'COORDINATOR-GO.json'
    if output.exists():raise SystemExit('Preserve GO evidence')
    def checked(relative):
        p=(E/relative).resolve(strict=True);assert p.is_relative_to(E.resolve());return p
    package_path=checked(f'PACKAGES-{a.package_attempt}.json');freeze_path=checked(f'SOURCE-FREEZE-OPERATORS-{a.package_attempt}.json');native_path=checked(a.native);wrapper_path=checked(a.wrapper);transition_path=checked(a.transition);own_path=checked(a.independent);review_path=checked('revision/GATE-TECNICO.json');pre_path=checked('REAL-QA-PREFLIGHT-01.json')
    package=read(package_path);assert package['valid'] and package['byteIdentical'] and package['sourcesUnchanged']
    assert all(sha(ROOT/x['path'])==x['sha256'] for x in package['outputs'])
    assert all(sha(ROOT/p)==h for p,h in read(freeze_path)['sources'].items())
    native=read(native_path);assert native['successful'] and native['testsRun']==1
    assert all(native[k] for k in ['inputsUnchanged','ownedProcessesStopped','systemCrtDllsAndX64RegistryUnchanged','recoverySnapshotExact']) and not native['cleanupErrors']
    assert native['archiveSha256']==package['outputs'][0]['sha256'] and native['freshClustersInitialized']>=3
    assert any(x.get('recoverAdmin11ReallyExecuted') and x.get('all35TablesExactExceptExplicitRecoveryChanges') for x in native['preferencesChecks'])
    composite=read(wrapper_path);assert composite['valid'] and composite['compositeComplete']
    wrapper_original=checked(composite['original']);wrapper_remainder=checked(composite['remainder']);wrapper=read(wrapper_original);remainder=read(wrapper_remainder)
    assert not wrapper['successful'] and wrapper['testsRun']==1 and wrapper['failures']==1 and wrapper['errors']==0
    assert remainder['successful'] and remainder['testsRun']==1
    for value in [wrapper,remainder]:
        assert all(value[k] for k in ['inputsUnchanged','ownedProcessesStopped','systemCrtDllsAndX64RegistryUnchanged']) and not value['cleanupErrors']
    assert wrapper['recoverySnapshotExact'] and wrapper['archiveSha256']==package['outputs'][0]['sha256']
    assert any(x['script']=='Install-RackClickOfflineBundle.ps1' and x['exitCode']==0 for x in wrapper['calls'])
    assert composite['archiveSha256']==wrapper['archiveSha256']
    transition=read(transition_path);assert transition['successful'] and transition['inputsUnchanged'] and all(all(row.values()) for row in transition['labs'])
    own=read(own_path);assert own['successful'] and own['testsRun']==1 and own['sourcesUnchanged'] and own['distributionsUnchanged']
    assert all(all(row.values()) for row in own['fixtureLifecycles'])
    review=read(review_path);assert review['valid'] and review['approved'] and not review['openBlockingFindings']
    for key in ['sourceHashes','manualHashes']:assert all(sha(ROOT/p)==h for p,h in review[key].items())
    pre=read(pre_path);assert pre['valid'] and pre['sourceSchema']==10 and pre['sourceQuiet']
    pointer=ROOT/'.local/qa-rc9/current.json';source=Source592(ROOT/pre['sourceDirectory'],pointer,real=True);OwnedRuntime(source.directory,source.cfg).quiet()
    assert source.hashes==pre['sourceInputHashes'] and sha(pointer)==pre['sourcePointerSha256']
    gates=[package_path,freeze_path,native_path,wrapper_path,wrapper_original,wrapper_remainder,transition_path,own_path,review_path,pre_path]
    data=dict(utc=datetime.now(timezone.utc).isoformat(),valid=True,authorizedRealQaCopySelection=True,scope='Technical coordinator GO under existing Wascar S1 authorization; new lab copy only, source10 immutable, no app login/DML or manual Wascar QA/adoption',sourceQuietReconfirmed=True,sourceInputsExact=True,gates={p.relative_to(ROOT).as_posix():sha(p) for p in gates},applicationBuilds=0,frontendBuilds=0,manualWascarResultsWritten=False,finalAdoption=False)
    with output.open('x',encoding='utf-8') as f:json.dump(data,f,indent=2);f.write('\n')
    print(json.dumps(dict(valid=True,gateCount=len(gates),sourceQuietReconfirmed=True,finalAdoption=False)))
if __name__=='__main__':main()
