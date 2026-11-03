"""No new user approval: record coordinator GO after concrete technical gates pass."""
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/quince-tandas-833-847'
sys.path.insert(0,str(ROOT/'tools/windows'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
    from qa_xls11_source847 import Source712
    from qa_xls11_switch847 import OwnedRuntime
    out=E/'COORDINATOR-GO.json';assert not out.exists()
    relative=['PACKAGES-01.json','SOURCE-FREEZE-OPERATORS-01.json','windows/profiles01/result.json','windows/native01/result.json','qa-copy/all01/result.json','revision/recovery-activity01/result.json','revision/GATE-TECNICO.json','REAL-QA-PREFLIGHT-01.json']
    records={p:read(E/p) for p in relative};package=records['PACKAGES-01.json'];assert package['valid'] and package['sourcesUnchanged'] and package['byteIdentical']
    assert all(sha(ROOT/x['path'])==x['sha256'] for x in package['outputs'])
    assert all(sha(ROOT/p)==h for p,h in records['SOURCE-FREEZE-OPERATORS-01.json']['sources'].items())
    native=records['windows/native01/result.json'];assert native['successful'] and native['testsRun']==1 and native['successfulOperationalRecoveries']==1
    assert all(native[k] for k in ['inputsUnchanged','ownedProcessesStopped','systemCrtDllsAndX64RegistryUnchanged','recoverySnapshotExact']) and not native['cleanupErrors']
    assert native['archiveSha256']==package['outputs'][0]['sha256'] and native['applicationManifestSha256']=='511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5'
    assert native['freshClustersInitialized']>=2
    assert len(native['tableDigestsBeforeBackup'])==35 and any(x.get('publicInstallerModeRestoreReallyExecuted') and x.get('originalOwnersReportBytesTimestampReceiptsExact') and x.get('all35TablesExactExceptExplicitRecoveryChanges') for x in native['excelChecks'])
    transition=records['qa-copy/all01/result.json'];assert transition['successful'] and transition['inputsUnchanged']
    assert transition['labs'] and all(all(row.values()) for row in transition['labs'])
    assert all(sha(ROOT/p)==h for p,h in transition['sourceHashes'].items())
    own=records['revision/recovery-activity01/result.json'];assert own['successful'] and own['testsRun']==1
    assert own['sourcesUnchanged'] and own['distributionsUnchanged'] and own['fixtureLifecycles'] and all(all(row.values()) for row in own['fixtureLifecycles'])
    assert own['sourceManifestSha256']=='f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd' and own['targetManifestSha256']=='511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5'
    gate=records['revision/GATE-TECNICO.json'];assert gate['valid'] and gate['approved'] and not gate['openBlockingFindings']
    for key in ['sourceHashes','manualHashes']:assert all(sha(ROOT/p)==h for p,h in gate[key].items())
    pre=records['REAL-QA-PREFLIGHT-01.json'];assert pre['valid'] and pre['sourceSchema']==11 and pre['sourceQuiet']
    pointer=ROOT/'.local/qa-rc9/current.json';source=Source712(ROOT/pre['sourceDirectory'],pointer,real=True);OwnedRuntime(source.directory,source.cfg).quiet()
    assert source.hashes==pre['sourceInputHashes'] and sha(pointer)==pre['sourcePointerSha256']
    data=dict(utc=datetime.now(timezone.utc).isoformat(),valid=True,authorizedRealQaCopySelection=True,scope='Existing Wascar S1 authorization; closed same-schema copy712→832 to new lab only after native/fixture/independent gates. No source app login/DML/manual QA/adoption.',sourceQuietReconfirmed=True,sourceInputsExact=True,gates={(E/p).relative_to(ROOT).as_posix():sha(E/p) for p in relative},applicationBuilds=0,frontendBuilds=0,manualWascarResultsWritten=False,finalAdoption=False)
    out.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(valid=True,gateCount=len(relative),sourceQuietReconfirmed=True,finalAdoption=False)))
if __name__=='__main__':main()
