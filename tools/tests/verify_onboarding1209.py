"""Read-only product/QA checks; write a new verification record only."""
import importlib.util
import json
import subprocess
from init_onboarding1209 import ROOT,E,BASE,GIT,sha

PIN='dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b'
def read(name):return json.loads((E/name).read_bytes())
def exact(values):assert values and all(sha(ROOT/p)==h for p,h in values.items())

def guards():
    initial=read('INICIO.json');exact(initial['guards'])
    directory=ROOT/initial['qaDirectory'];assert len([p for p in directory.iterdir() if p.is_file()])==28
    return initial

def product():
    initial=read('INICIO.json');sources=read('SOURCE-FREEZE-APP.json')['sources'];assert len(sources)==193;exact(sources)
    old=initial['originalProductSources'];assert {p for p,h in old.items() if sources[p]!=h}==set(initial['allowedProductChanges'])
    assert set(sources)-set(old)==set(initial['allowedNewProductSources'])
    path=E/'CANDIDATA1209-01.json';assert sha(path)==PIN;candidate=read(path.name)
    artifacts={}
    for part,files in candidate['distributions'].items():
        for name,h in files.items():artifacts[(ROOT/candidate['candidateDirectory']/part/name).relative_to(ROOT).as_posix()]=h
    assert len(artifacts)==40;exact(artifacts)
    assert sum((ROOT/p).stat().st_size for p in artifacts)==7146303
    baseline=json.loads((ROOT/candidate['sourceManifest']).read_bytes())
    assert candidate['distributions']['server']==baseline['distributions']['server'] and len(candidate['distributions']['server'])==22
    assert {p for p,h in candidate['distributions']['frontend'].items() if h!=baseline['distributions']['frontend'][p]}=={'app.js'}
    build=read('BUILD-01.json');assert build['successful'] and build['frontendBuilds']==1 and build['serverBuilds']==0
    return candidate

def technical_gate():
    gate=read('revision/GATE-TECNICO.json');assert gate['valid'] and gate['approved'] and not gate['openBlockingFindings']
    assert gate['targetManifestSha256']==PIN;exact(gate['sourceHashes']);exact(gate['artifactHashes']);exact(gate['guardHashes'])
    assert all(sha(E/p)==h for p,h in gate['observedFilesSha256'].items())
    return gate

def main():
    out=E/'VERIFICACION-FINAL.json';assert not out.exists()
    initial=guards();product();technical_gate()
    node=read('NODE-FINAL-02.json');assert node['successful'] and node['testsRun']==15 and node['exitCode']==0;exact(node['sourceHashes'])
    for attempt in ['01','02','03','04']:
        run=read('gui'+attempt+'/fixture.json');assert run['labStopped'] and run['serversStopped'] and run['inputsUnchanged']
        if attempt!='04':assert run['result']=='FAIL' and (E/('gui'+attempt+'/DIAGNOSTICO.json')).exists()
    native=read('gui04/fixture.json');assert native['result']=='PASS' and native['exitCode']==0
    assert native['persistedCreatedUsers']==4 and native['cancelledUserAbsent'] and native['exactUuidGroupAssignment']
    assert native['applicationRestartAndScopedLoginVerified'] and native['serverAdministrativeDenialVerified'] and native['browserChecks']==10
    exact(native['inputSha256']);assert native['inputSha256']==native['finalInputSha256']
    own=read('revision/dom01/result.json');assert own['successful'] and own['testsRun']==1
    assert all(own[k] for k in ['sourcesUnchanged','artifactsUnchanged','edgeStopped','httpStopped']) and own['postgresTests']==0
    assert not own['runtimeErrors'] and not own['unknownRoutes']
    visual=read('VISUAL-01.json');assert visual['successful'] and not visual['findings']
    assert all(sha(E/p)==h for p,h in visual['inspectedFiles'].items())
    assert read('PROCESOS-01.json')['ownedEdgeCount']==0
    qa=read('QA-TESTS-01.json');assert qa['successful'] and qa['testsRun']==50 and qa['available']==dict(manual=8,rc9=84)
    baseline=json.loads(subprocess.check_output([str(GIT),'show',BASE+':docs/QA-CASOS-WASCAR.json']))
    current=json.loads((ROOT/'docs/QA-CASOS-WASCAR.json').read_bytes())
    assert len(current['cases'])==87 and current['cases'][:84]==baseline['cases']
    assert {k:v for k,v in current.items() if k not in ['cases','revision']}=={k:v for k,v in baseline.items() if k not in ['cases','revision']}
    assert all(c['feature']=='planned' for c in current['cases'][84:])
    assert (ROOT/'tools/windows/qa_guide.py').read_bytes()==subprocess.check_output([str(GIT),'show',BASE+':tools/windows/qa_guide.py'])
    spec=importlib.util.spec_from_file_location('guide1209final',ROOT/'tools/windows/qa_guide.py');guide=importlib.util.module_from_spec(spec);spec.loader.exec_module(guide)
    for profile in ['manual','rc9']:assert guide.generate(check=True,profile=profile)
    plan=json.loads((ROOT/'docs/PLAN-SESENTA-TANDAS-1150-1209.json').read_bytes());assert plan['completed']==60 and len(plan['batches'])==60
    assert all(b['status']=='verified' and (ROOT/b['evidence']).exists() for b in plan['batches'])
    progress=json.loads((ROOT/'docs/MAPA-ENTREGA.json').read_bytes());assert progress['progress']==78 and [s['points'] for s in progress['streams']]==[18,22,14,14,9,1]
    assert subprocess.check_output([str(GIT),'rev-parse','HEAD'],text=True).strip()==BASE
    record=dict(successful=True,protectedFilesExact=len(initial['guards']),originalQaRootFilesExact=28,productSourcesExact=193,
        previousUnchangedProductSources=189,candidateFilesExact=40,unchangedServerFiles=22,changedFrontendFiles=['app.js'],
        frontendBuilds=1,serverBuilds=0,selectedQaRevision=1089,selectedQaSchema=13,qaPointerAndConfigurationExact=True,
        nativeFinal='gui04',nativeFinalChecks=10,preservedFailedWrappers=['gui01','gui02','gui03'],allFourFixtureRuntimesStopped=True,
        nodeTests=15,independentDomTests=1,independentPostgresqlTests=0,guideTests=50,manualCases=87,available=dict(manual=8,rc9=84),
        newCasesPlanned=[85,86,87],previous84CasesAndGatesExact=True,generatorAndUserResultLogicExact=True,
        completedInternalMilestones=60,progress=78,actualQaApplicationAccess=False,manualWascarResultsWritten=False,finalAdoption=False)
    out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record))

if __name__=='__main__':main()
