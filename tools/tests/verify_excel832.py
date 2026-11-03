"""Public final checks for this block; never start or query the actual QA application."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-773-832'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads((E/p).read_bytes())
def tree(p):return {x.relative_to(p).as_posix():sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
def main():
    out=E/'VERIFICACION-FINAL.json';assert not out.exists(),'Preserve prior verification'
    start=read('INICIO.json');allowed=set(start['authorizedMutableGuards'])
    for p in ['ALCANCE-GUIA.json','ALCANCE-TESTS-GUIA.json']:allowed.update(read(p)['additionalAuthorizedMutableGuards'])
    changed={p for p,h in start['guards'].items() if sha(ROOT/p)!=h};assert changed<=allowed,changed-allowed
    assert all(sha(ROOT/p)==h for p,h in start['currentQaGuards'].items())
    m=read('CANDIDATA832-02.json');dist={part:tree(ROOT/m['candidateDirectory']/part) for part in ['server','frontend']};assert dist==m['distributions']
    sources=read('SOURCE-FREEZE-APP-02.json')['sources'];assert all(sha(ROOT/p)==h for p,h in sources.items())
    assert read('BUILD-01.json')['successful'] and read('BUILD-02.json')['successful']
    assert read('backup/native02/result.json')['successful'] and read('office/office03/result.json')['successful']
    assert read('qa-guide02/result.json')['successful'] and read('qa-guide03/result.json')['successful'] and read('QA-DISPONIBILIDAD-02.json')['successful']
    assert read('frontend/edge03/fixture.json')['result']=='PASS' and read('frontend/node03/result.json')['result']=='PASS'
    assert read('backend/INFORME.json')['successful']
    gate=read('revision/GATE-TECNICO.json');assert gate['valid'] and gate['recommendedProgress']==78
    for name,key in [('GUIA-QA-WASCAR.html','manual'),('GUIA-QA-RESTAURADO.html','rc9')]:
        data=json.loads((ROOT/name).read_text(encoding='utf-8').split('const guide=',1)[1].split(';',1)[0])
        assert len(data['cases'])==77 and sum(x['available'] for x in data['cases'].values())==(8 if key=='manual' else 74)
        assert all(not data['cases'][p]['available'] for p in ['QA-75','QA-76','QA-77'])
    catalog=json.loads((ROOT/'docs/QA-CASOS-WASCAR.json').read_bytes());old=read('QA-ANTERIOR.json')
    assert hashlib.sha256(json.dumps(catalog['cases'][:74],sort_keys=True,ensure_ascii=False).encode()).hexdigest()==old['first74CasesSha256']
    plan=json.loads((ROOT/'docs/PLAN-SESENTA-TANDAS-773-832.json').read_bytes());assert plan['completed']==60 and all(x['status']=='verified' and (ROOT/x['evidence']).is_file() and (ROOT/x['independentEvidence']).is_file() for x in plan['batches'])
    map0=json.loads((ROOT/'docs/MAPA-ENTREGA.json').read_bytes());assert map0['progress']==78 and [x['points'] for x in map0['streams']]==[18,22,14,14,9,1]
    git=str(ROOT/'.local/git-2.55.0.5/cmd/git.exe')
    assert subprocess.check_output([git,'rev-parse','HEAD'],cwd=ROOT,text=True).strip()==start['baseCommit']
    record=dict(utc=datetime.now(timezone.utc).isoformat(),successful=True,guardCount=len(start['guards']),unchangedGuards=len(start['guards'])-len(changed),authorizedChangedGuards=sorted(changed),currentQaUnchangedFiles=len(start['currentQaGuards']),candidateFileCount=m['fileCount'],candidateManifestSha256=sha(E/'CANDIDATA832-02.json'),applicationSourceCount=len(sources),applicationSourcesUnchanged=True,sqlDependencyCssVersionsUnchanged=True,qaAvailable=dict(manual=8,rc9=74),newCasesPending=['QA-75','QA-76','QA-77'],progress=78,internalMilestonesVerified=60,actualQaAccessed=False,actualQaSelected=False,manualWascarResultsWritten=False,historicalEvidenceReusedAsNew=False)
    out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record,indent=2))
if __name__=='__main__':main()
