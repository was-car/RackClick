"""Read-only final verification of Windows/QA13, preserving prior evidence."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-1090-1149'
PIN='c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c'
GIT=ROOT/'.local/git-2.55.0.5/cmd/git.exe'

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def read(name):return json.loads((E/name).read_bytes())

def exact(values):assert values and all(sha(ROOT/p)==h for p,h in values.items())

def protected_inputs():
    initial=read('INICIO.json')
    runtime=read('ALCANCE-RUNTIME-FUENTE.json')['authorizedMutableRuntimeFiles']
    mutable=set(initial['authorizedMutableGuards'])|set(runtime)
    protected={p:h for p,h in initial['guards'].items() if p not in mutable};exact(protected)
    for p,row in runtime.items():
        assert initial['guards'][p]==row['sha256']
        archive=ROOT/row['privateArchive'];assert archive.stat().st_size==row['bytes'] and sha(archive)==row['sha256']
    source={p:h for p,h in initial['sourceQaGuards'].items() if p not in runtime}
    assert len(source)==21;exact(source)
    changes={p:('absent' if not (ROOT/p).exists() else sha(ROOT/p)) for p,row in runtime.items()
             if not (ROOT/p).exists() or sha(ROOT/p)!=row['sha256']}
    return initial,len(protected),len(source),changes

def current_product():
    sources=read('SOURCE-FREEZE-APP.json')['sources'];assert len(sources)==190;exact(sources)
    path=ROOT/'evidence/s1-20261018/sesenta-tandas-1030-1089/CANDIDATA1089-02.json'
    assert sha(path)==PIN;manifest=json.loads(path.read_bytes())
    artifacts=[(ROOT/manifest['candidateDirectory']/part/p,h) for part,files in manifest['distributions'].items() for p,h in files.items()]
    assert len(artifacts)==40 and all(sha(p)==h for p,h in artifacts)
    assert sum(p.stat().st_size for p,_ in artifacts)==7133395
    return manifest

def technical_gate():
    gate=read('revision/GATE-TECNICO.json')
    assert gate['valid'] and gate['approved'] and not gate['openBlockingFindings']
    assert gate['targetManifestSha256']==PIN
    for key in ['sourceHashes','manualHashes']:exact(gate[key])
    assert all(sha(E/p)==h for p,h in gate['observedFilesSha256'].items())
    return gate

def main():
    output=E/'VERIFICACION-FINAL.json';assert not output.exists()
    initial,protected,source_count,runtime_changes=protected_inputs()
    manifest=current_product();gate=technical_gate();package=read('PACKAGES-01.json')
    assert package['valid'] and package['byteIdentical'] and package['sourcesUnchanged']
    assert package['sourceManifestSha256']==PIN
    assert all(sha(ROOT/r['path'])==r['sha256'] and (ROOT/r['path']).stat().st_size==r['bytes'] for r in package['outputs'])
    exact(read('SOURCE-FREEZE-OPERATORS-01.json')['sources'])
    assert gate['archiveSha256']==package['outputs'][0]['sha256']
    for name in ['windows/profiles01/result.json','windows/native01/result.json','qa-copy/RESUMEN-AUTOR.json',
                 'revision/source-recovery849-only01/result.json','QA-TESTS-01.json']:assert read(name)['successful'],name
    native=read('windows/native01/result.json')
    assert native['ownedProcessesStopped'] and native['inputsUnchanged'] and not native['cleanupErrors']
    assert native['successfulOperationalRecoveries']==1 and native['recoverySnapshotExact']
    assert native['systemCrtDllsAndX64RegistryUnchanged'] and len(native['tableDigestsBeforeBackup'])==39
    go=read('COORDINATOR-GO.json');assert go['valid'];exact(go['gates'])
    prepared=read('REAL-QA-PREPARE-01.json');activated=read('REAL-QA-ACTIVATE-01.json');validated=read('REAL-QA-VALIDATE-01.json')
    assert prepared['valid'] and prepared['logicalTableCount']==39 and prepared['recoverySchema']==12
    assert activated['valid'] and activated['state']=='committed' and validated['valid']
    pointer=ROOT/'.local/qa-rc9/current.json';assert sha(pointer)==activated['pointerSha256']
    assert Path(json.loads(pointer.read_bytes())['directory']).resolve()==(ROOT/prepared['candidateDirectory']).resolve()
    cfg=json.loads((ROOT/prepared['candidateDirectory']/'manual-qa.json').read_bytes())
    assert cfg['dllSha256']==sha(ROOT/manifest['serverDll']) and cfg['bundleSha256']==sha(ROOT/manifest['frontend']/'app.js')
    sys.path.insert(0,str(ROOT/'tools/windows'))
    from qa_category_colors13_switch1149 import OwnedRuntime
    for directory in [ROOT/prepared['sourceDirectory'],ROOT/prepared['candidateDirectory']]:
        OwnedRuntime(directory,json.loads((directory/'manual-qa.json').read_bytes())).quiet()
    spec=importlib.util.spec_from_file_location('guide1149final',ROOT/'tools/windows/qa_guide.py')
    guide=importlib.util.module_from_spec(spec);spec.loader.exec_module(guide)
    catalog=json.loads(guide.CATALOG.read_bytes())
    baseline=json.loads(subprocess.check_output([str(GIT),'show',initial['baseCommit']+':docs/QA-CASOS-WASCAR.json']))
    assert len(catalog['cases'])==84 and catalog['cases'][:81]==baseline['cases'][:81]
    matrix=read('QA-MATRIX-1149.json')
    for key,value in baseline.items():
        if key in ['cases','revision']:continue
        expected=value+[matrix['pair']] if key in matrix['inheritedBuildLists'] else value
        assert catalog[key]==expected,key
    assert catalog['userCategoryColorsBuilds']==[matrix['pair']]
    for current,old in zip(catalog['cases'][81:],baseline['cases'][81:]):
        assert current=={**old,'feature':'userCategoryColorsGui','steps':[current['steps'][0]]+old['steps'][1:]}
    availability={}
    for profile in ['manual','rc9']:
        assert guide.generate(check=True,profile=profile)
        cases=json.loads(guide.render(catalog,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases']
        availability[profile]=sum(v['available'] for v in cases.values())
    assert availability==dict(manual=8,rc9=84)
    plan=json.loads((ROOT/'docs/PLAN-SESENTA-TANDAS-1090-1149.json').read_bytes())
    assert plan['completed']==60 and len(plan['batches'])==60
    assert all(b['status']=='verified' and (ROOT/b['evidence']).is_file() for b in plan['batches'])
    progress=json.loads((ROOT/'docs/MAPA-ENTREGA.json').read_bytes())
    assert progress['progress']==78 and [s['points'] for s in progress['streams']]==[18,22,14,14,9,1]
    assert subprocess.check_output([str(GIT),'rev-parse','HEAD'],text=True).strip()==initial['baseCommit']
    record=dict(utc=datetime.now(timezone.utc).isoformat(),successful=True,protectedFilesExact=protected,
        immutableSourceQaRootFilesExact=source_count,originalRuntimeFilesPrivatelyArchived=7,allowedRuntimeChanges=runtime_changes,
        productSourcesExact=190,candidateFilesExact=40,selectedQaRevision=1089,selectedQaSchema=13,
        recoveryRevision=969,recoverySchema=12,originalSourceRevision=969,originalSourceSchema=12,
        originalSourceRecoveryRevision=849,originalSourceRecoverySchema=11,windowsRecoveredTables=39,
        realQaPrimaryTables=39,realQaRecoveryTables=37,manualCases=84,available=availability,previous81CasesExact=True,
        originalEvidencePreserved=True,manualWascarResultsWritten=False,newApplicationPublications=0,newFrontendBuilds=0,
        processesQuiet=True,independentGateApproved=True,finalAdoption=False,progress=78)
    with output.open('x',encoding='utf-8') as stream:stream.write(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))

if __name__=='__main__':main()
