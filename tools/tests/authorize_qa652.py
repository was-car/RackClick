"""Coordinator technical GO after final package proof; not product adoption."""
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-593-652'
sys.path.insert(0,str(ROOT/'tools/windows'))
from qa_schema10_source652 import Source532
from qa_schema10_switch652 import OwnedRuntime
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
    output=E/'COORDINATOR-GO.json'
    if output.exists():raise SystemExit('Preserve existing GO')
    gates=[E/'PACKAGES-03.json',E/'SOURCE-FREEZE-OPERATORS-03.json',E/'revision/GATE-TECNICO-02.json',E/'windows/SUMMARY.json',E/'windows/native04/result.json',E/'qa-transition/SUMMARY.json',E/'qa-transition/native01/result.json',E/'qa-transition/private-inputs02/result.json',E/'revision/source-activity01/result.json',E/'revision/readiness-http01/result.json',E/'REAL-QA-PREFLIGHT-01.json',E/'windows/native05/result.json',E/'revision/NATIVO-COMPUESTO.json']
    package=read(gates[0]);assert package['valid'] and package['byteIdentical'] and package['sourcesUnchanged']
    assert all(sha(ROOT/x['path'])==x['sha256'] for x in package['outputs'])
    frozen=read(gates[1]);assert all(sha(ROOT/p)==h for p,h in frozen['sources'].items())
    review=read(gates[2]);assert review['valid'] and review['approved'] and not review['openBlockingFindings']
    for key in ['sourceHashes','manualHashes']:assert all(sha(ROOT/p)==h for p,h in review[key].items())
    native=read(gates[4]);assert not native['successful'] and native['testsRun']==1
    assert all(native[k] for k in ['inputsUnchanged','ownedProcessesStopped','systemCrtDllsAndX64RegistryUnchanged','recoverySnapshotExact']) and not native['cleanupErrors']
    assert native['archiveSha256']==package['outputs'][0]['sha256'] and native['freshClustersInitialized']==2 and native['successfulOperationalRecoveries']==1
    summary=read(gates[3]);assert summary['valid'] and summary['compositeNativeComplete']
    continuation=read(gates[11]);assert continuation['successful']
    assert read(gates[12])['valid']
    for p in [gates[6],gates[7],gates[8],gates[9]]:
        value=read(p);assert value.get('successful',value.get('valid',value.get('success',False)))
    preflight=read(gates[10]);pointer=ROOT/'.local/qa-rc9/current.json'
    source=Source532(ROOT/preflight['sourceDirectory'],pointer,real=True);OwnedRuntime(source.directory,source.cfg).quiet()
    assert source.hashes==preflight['sourceInputHashes'] and sha(pointer)==preflight['sourcePointerSha256']
    row={'utc':datetime.now(timezone.utc).isoformat(),'valid':True,'authorizedRealQaCopySelection':True,'scope':'Coordinator operational GO under existing Wascar development authorization; not manual QA or final adoption. New lab only, original source immutable, no application login/DML.','sourceQuietReconfirmed':True,'sourceInputsExact':True,'gates':{p.relative_to(ROOT).as_posix():sha(p) for p in gates},'finalApplicationBuilds':0,'manualWascarResultsWritten':False,'finalAdoption':False}
    with output.open('x',encoding='utf-8') as f:json.dump(row,f,indent=2);f.write('\n')
    print(json.dumps({'valid':True,'gateCount':len(gates),'sourceQuietReconfirmed':True,'finalAdoption':False}))
if __name__=='__main__':main()
