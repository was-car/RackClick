"""Require concrete independent gates before copying/selecting the actual QA lab."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-1090-1149'
PIN='c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c'
sys.path.insert(0,str(ROOT/'tools/windows'))

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def read(path):return json.loads(path.read_bytes())

def exact(values):
    assert values and all(sha(ROOT/p)==h for p,h in values.items())

def main():
    from qa_category_colors13_source1149 import Source969
    from qa_category_colors13_switch1149 import OwnedRuntime
    out=E/'COORDINATOR-GO.json';assert not out.exists()
    names=['PACKAGES-01.json','SOURCE-FREEZE-OPERATORS-01.json','windows/profiles01/result.json',
        'windows/native01/result.json','qa-copy/RESUMEN-AUTOR.json','revision/source-recovery849-only01/result.json',
        'revision/GATE-TECNICO.json','REAL-QA-PREFLIGHT-01.json','revision/COMPATIBILIDAD-PRETEST.json']
    records={name:read(E/name) for name in names}
    exact(read(E/'SOURCE-FREEZE-APP.json')['sources'])
    assert len(read(E/'SOURCE-FREEZE-APP.json')['sources'])==190
    assert sha(ROOT/'evidence/s1-20261018/sesenta-tandas-1030-1089/CANDIDATA1089-02.json')==PIN
    package=records[names[0]]
    assert package['valid'] and package['byteIdentical'] and package['sourcesUnchanged']
    assert package['sourceManifestSha256']==PIN
    assert len(package['outputs'])==2 and all(sha(ROOT/r['path'])==r['sha256'] for r in package['outputs'])
    exact(records[names[1]]['sources'])
    profiles=records[names[2]];assert profiles['successful'] and profiles['testsRun']==3
    native=records[names[3]]
    assert native['successful'] and native['testsRun']==1 and native['successfulOperationalRecoveries']==1
    assert all(native[k] for k in ['inputsUnchanged','ownedProcessesStopped','systemCrtDllsAndX64RegistryUnchanged','recoverySnapshotExact'])
    assert not native['cleanupErrors'] and native['freshClustersInitialized']>=2
    assert native['archiveSha256']==package['outputs'][0]['sha256'] and native['applicationManifestSha256']==PIN
    assert len(native['tableDigestsBeforeBackup'])==39
    assert len(native['frontendTransportChecks'])==2
    assert all(c['httpServedAppJsExact'] and not c['domExecuted'] and not c['screenReaderVoiceTested'] for c in native['frontendTransportChecks'])
    stages={r['stage']:r for r in native['paletteChecks']}
    assert stages['installed']['readerWithoutClientsCanSetOwnPalette'] and stages['installed']['twoActorIsolation']
    assert stages['restart_backup']['all39SourceTablesUnchangedByBackup']
    assert all(stages['recovered'][k] for k in ['publicInstallerModeRestoreReallyExecuted','recoverAdmin13ReallyExecuted',
        'all39TablesExactExceptExplicitRecoveryChanges','originalOwnerPalettesPreferencesReceiptsExact','copiedSessionsRevoked'])
    assert len(native['inventoryExpiryChecks'])==2
    assert all(r['httpsActorRuntimeReallyWaitedDuringApply'] and r['naturalExpiryAfterAuthorization'] and r['status']==401
        and r['all39TablesExact'] and r['inventoryRevisionUnchanged'] and r['operationAndAuditRows']==0 for r in native['inventoryExpiryChecks'])
    assert native['categoryChecks'][1]['serverCategoryFromStablePresetKey'] and native['categoryChecks'][1]['replayAndExistingConnectionsDoNotRecolor']
    copy=records[names[4]]
    assert copy['successful'] and copy['testsRun']==5 and copy['inputsUnchanged']
    assert copy['targetManifestSha256']==PIN and copy['sourceHashesMatchCurrent']
    exact(copy['sourceHashes'])
    assert len(copy['labs'])==5 and {r['role'] for r in copy['labs']}=={'target1089','source969','source849','source832','source712'}
    assert all(r['applicationStopped'] and r['postgresqlStopped'] for r in copy['labs'])
    assert copy['contractsPassed']==4 and copy['postgresqlCasesPassed']==1
    assert copy['coverage']['directActivityGuardCount']==4 and copy['coverage']['finalCumulativeRollbackCount']==1
    assert not copy['coverage']['fourIndependentRollbacks'] and copy['coverage']['baselineOrJournalRenewals']==0
    own=records[names[5]];assert own['successful'] and own['testsRun']==1 and own['distributionsUnchanged']
    assert not own['sourcesUnchanged'] and not own['cleanupErrors'] and len(own['fixtureLifecycles'])==5
    assert all(r['applicationStopped'] and r['postgresqlStopped'] and r['capturedServerProcessesStopped'] for r in own['fixtureLifecycles'])
    assert len(own['observations'])==1
    observation=own['observations'][0]
    assert all(observation[k] for k in ['committedDmlOnlySourceRecovery849AfterSelection','allFourDatabaseSnapshotsAndHistoriesExact',
        'sourcePrimaryHasNoPostSelectionDml','targetPrimaryAndRecoveryHaveNoPostSelectionDml','sourceClusterActivityAdvanced',
        'targetClusterActivityExact','actualRollbackDenied','selected1089PointerRetained','noBaselineOrJournalRenewal'])
    assert observation['selectedRevision']==1089 and observation['selectedSchema']==13
    compat=records[names[8]]
    changed='development/server/tests/test_qa_category_colors13_update1149.py'
    exact({p:h for p,h in own['sourceHashes'].items() if p!=changed})
    assert compat['valid'] and compat['changedOwnInputFiles']==[changed]
    assert compat['onlyMainFreezePathRelocation'] and compat['allModuleAstOutsideMainExact'] and compat['normalizedWholeModuleAstExact']
    assert sha(ROOT/changed)==compat['currentSourceSha256'] and sha(ROOT/compat['originalSourcePath'])==compat['originalSourceSha256']
    assert sha(ROOT/compat['ownInputPath'])==compat['ownInputSha256']
    gate=records[names[6]]
    assert gate['valid'] and gate['approved'] and not gate['openBlockingFindings']
    assert gate['targetManifestSha256']==PIN and gate['archiveSha256']==package['outputs'][0]['sha256']
    for key in ['sourceHashes','manualHashes']:exact(gate[key])
    assert all(sha(E/p)==h for p,h in gate['observedFilesSha256'].items())
    pre=records[names[7]];assert pre['valid'] and pre['sourceSchema']==12 and pre['sourceQuiet']
    pointer=ROOT/'.local/qa-rc9/current.json'
    source=Source969(ROOT/pre['sourceDirectory'],pointer,real=True)
    OwnedRuntime(source.directory,source.cfg).quiet()
    assert source.hashes==pre['sourceInputHashes'] and sha(pointer)==pre['sourcePointerSha256']
    data=dict(utc=datetime.now(timezone.utc).isoformat(),valid=True,authorizedRealQaCopySelection=True,
        scope='Existing S1 authorization; source969/12 with separate recovery849/11 retained; new1089/13 with new recovery969/12. Native, fixture and independent gates required. No source application login/DML or final adoption.',
        sourceQuietReconfirmed=True,sourceInputsExact=True,gates={(E/name).relative_to(ROOT).as_posix():sha(E/name) for name in names},
        applicationBuilds=0,frontendBuilds=0,manualWascarResultsWritten=False,finalAdoption=False)
    with out.open('x',encoding='utf-8') as stream:stream.write(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(valid=True,gates=len(names),sourceQuietReconfirmed=True,finalAdoption=False)))

if __name__=='__main__':main()
