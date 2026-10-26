"""Record coordinator GO under existing S1 authorization after concrete independent gates."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029'
sys.path.insert(0,str(ROOT/'tools/windows'))
PIN='b589609154fed1567106ef0865972155258f0f5474128c73076f4697d43b8bda'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def main():
    from qa_port_colors12_source1029 import Source849
    from qa_port_colors12_switch1029 import OwnedRuntime
    out=E/'COORDINATOR-GO.json';assert not out.exists()
    names=['PACKAGES-02.json','SOURCE-FREEZE-OPERATORS-02.json','windows/profiles03/result.json',
        'windows/native02/result.json','qa-copy/RESUMEN-AUTOR.json','revision/target-palette-activity01/result.json',
        'revision/GATE-TECNICO.json','REAL-QA-PREFLIGHT-01.json']
    records={name:read(E/name) for name in names}
    package=records[names[0]];assert package['valid'] and package['byteIdentical'] and package['sourcesUnchanged']
    assert package['sourceManifestSha256']==PIN
    assert all(sha(ROOT/row['path'])==row['sha256'] for row in package['outputs'])
    assert all(sha(ROOT/p)==h for p,h in records[names[1]]['sources'].items())
    published=read(E/'PUBLISH-FIX02-FINAL.json');assert published['successful'] and published['publicationCount']==1 and published['frontendBuilds']==0
    assert all(sha(ROOT/p)==h for p,h in published['sourceHashes'].items())
    profiles=records[names[2]];assert profiles['successful'] and profiles['testsRun']==3
    native=records[names[3]];assert native['successful'] and native['testsRun']==1 and native['successfulOperationalRecoveries']==1
    assert all(native[k] for k in ['inputsUnchanged','ownedProcessesStopped','systemCrtDllsAndX64RegistryUnchanged','recoverySnapshotExact'])
    assert not native['cleanupErrors'] and native['freshClustersInitialized']>=2
    assert native['archiveSha256']==package['outputs'][0]['sha256'] and native['applicationManifestSha256']==PIN
    assert len(native['tableDigestsBeforeBackup'])==37
    assert len(native['frontendTransportChecks'])==2
    assert all(c['httpServedAppJsExact'] and c['personalPaletteRouteTransported'] and not c['domExecuted'] and not c['screenReaderVoiceTested'] for c in native['frontendTransportChecks'])
    by_stage={c['stage']:c for c in native['paletteChecks']}
    assert by_stage['installed']['readerWithoutClientsCanSetOwnPalette'] and by_stage['installed']['twoActorIsolation']
    assert by_stage['restart_backup']['all37SourceTablesUnchangedByBackup']
    assert all(by_stage['recovered'][key] for key in ['publicInstallerModeRestoreReallyExecuted','recoverAdmin12ReallyExecuted',
        'all37TablesExactExceptExplicitRecoveryChanges','originalOwnerPalettesPreferencesReceiptsExact','cancellationFenceSurvivesRestore','copiedSessionsRevoked'])
    copy=records[names[4]];assert copy['successful'] and copy['testsRun']==5 and copy['inputsUnchanged']
    assert copy['targetSha256']==PIN and copy['currentSourcesMatchRun']
    assert copy['labs'] and all(all(row.values()) for row in copy['labs'])
    assert len(copy['allFixtureClusters'])==4
    assert all(row['applicationStopped'] and row['postgresqlStopped'] for row in copy['allFixtureClusters'])
    assert {row['role'] for row in copy['allFixtureClusters']}=={'target12','source849','source832','source712'}
    assert copy['scope']['contracts']==4 and copy['scope']['postgresqlFocusedCompound']==1
    assert not copy['scope']['originalCompoundRepeated']
    assert all(sha(ROOT/p)==h for p,h in copy['sourceHashes'].items())
    own=records[names[5]];assert own['successful'] and own['testsRun']==2
    assert own['sourcesUnchanged'] and own['distributionsUnchanged']
    assert own['fixtureLifecycles'] and all(row['applicationStopped'] and row['postgresqlStopped'] for row in own['fixtureLifecycles'])
    gate=records[names[6]];assert gate['valid'] and gate['approved'] and not gate['openBlockingFindings']
    assert gate['targetManifestSha256']==PIN and gate['archiveSha256']==package['outputs'][0]['sha256']
    for key in ['sourceHashes','manualHashes']:assert all(sha(ROOT/p)==h for p,h in gate[key].items())
    assert all(sha(E/p)==h for p,h in gate['observedFilesSha256'].items())
    pre=records[names[7]];assert pre['valid'] and pre['sourceSchema']==11 and pre['sourceQuiet']
    pointer=ROOT/'.local/qa-rc9/current.json'
    source=Source849(ROOT/pre['sourceDirectory'],pointer,real=True)
    OwnedRuntime(source.directory,source.cfg).quiet()
    assert source.hashes==pre['sourceInputHashes'] and sha(pointer)==pre['sourcePointerSha256']
    data=dict(utc=datetime.now(timezone.utc).isoformat(),valid=True,authorizedRealQaCopySelection=True,
        scope='Existing S1 authorization; closed849/11 primary-only copy to new969/12 plus recovery849/11 after native, fixture and independent gates. No source app login/DML/manual QA/adoption.',
        sourceQuietReconfirmed=True,sourceInputsExact=True,gates={(E/name).relative_to(ROOT).as_posix():sha(E/name) for name in names},
        applicationBuilds=1,frontendBuilds=0,manualWascarResultsWritten=False,finalAdoption=False)
    with out.open('x',encoding='utf-8') as stream:stream.write(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(valid=True,gates=len(names),sourceQuietReconfirmed=True,finalAdoption=False)))


if __name__=='__main__':main()
