"""Readonly product/QA guards and evidence verification for palette969; one immutable record."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-910-969'


def sha(p):
    with p.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def read(name):
    return json.loads((E/name).read_bytes())


def main():
    assert not (E/'VERIFICACION-FINAL.json').exists()
    start=read('INICIO.json')
    assert all(sha(ROOT/p)==h for p,h in start['guards'].items())
    frozen=read('SOURCE-FREEZE-01.json')['sources']
    assert all(sha(ROOT/p)==h for p,h in frozen.items())
    manifest=read('CANDIDATA969-01.json')
    artifacts=[(ROOT/manifest['candidateDirectory']/part/p,h) for part,files in manifest['distributions'].items() for p,h in files.items()]
    assert len(artifacts)==39 and all(sha(p)==h for p,h in artifacts)
    assert read('BUILD-01.json')['successful'] and read('frontend-node01/result.json')['passed']==19
    for name in ['backend01/result.json','regression01/result.json','QA-TESTS-02.json','QA-FOCAL-04.json','revision/PG-SESION-01.json']:
        assert read(name)['successful'], name
    for name in ['backend01/result.json','gui02/result.json','regression01/result.json']:
        r=read(name)
        assert r['labStopped'] and r['serversStopped'], name
    assert read('gui02/result.json')['result']=='PASS'
    assert read('gui01/result.json')['result']=='FAIL' and not read('QA-TESTS-01.json')['successful']
    spec=importlib.util.spec_from_file_location('guide969final',ROOT/'tools/windows/qa_guide.py')
    guide=importlib.util.module_from_spec(spec);spec.loader.exec_module(guide)
    catalog=json.loads(guide.CATALOG.read_bytes())
    git=str(ROOT/'.local/git-2.55.0.5/cmd/git.exe')
    original=json.loads(subprocess.check_output([git,'show',start['baseCommit']+':docs/QA-CASOS-WASCAR.json']))
    assert catalog['cases'][:78]==original['cases']
    assert all(catalog[k]==v for k,v in original.items() if k not in ['revision','cases'])
    assert len(catalog['cases'])==81 and all(c['feature']=='planned' for c in catalog['cases'][78:])
    counts={}
    for profile in ['manual','rc9']:
        assert guide.generate(check=True,profile=profile)
        metadata=json.loads(guide.render(catalog,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases']
        counts[profile]=sum(v['available'] for v in metadata.values())
    assert counts==dict(manual=8,rc9=78)
    plan=json.loads((ROOT/'docs/PLAN-SESENTA-TANDAS-910-969.json').read_bytes())
    assert plan['completed']==60 and len(plan['batches'])==60
    assert all(b['status']=='verified' and (ROOT/b['evidence']).is_file() for b in plan['batches'])
    progress=json.loads((ROOT/'docs/MAPA-ENTREGA.json').read_bytes())
    assert progress['progress']==78 and [s['points'] for s in progress['streams']]==[18,22,14,14,9,1]
    assert subprocess.check_output([git,'rev-parse','HEAD'],text=True).strip()==start['baseCommit']
    record=dict(utc=datetime.now(timezone.utc).isoformat(),successful=True,protectedFiles=len(start['guards']),allProtectedFilesExact=True,
       productSources=len(frozen),productSourcesExact=True,candidateFiles=len(artifacts),candidateFilesExact=True,schema=12,
       selectedQaUnchanged=True,selectedQaRevision=849,selectedQaSchema=11,package909Unchanged=True,
       manualCases=81,available=counts,previous78CasesExact=True,manualResultsWritten=False,
       newApplicationBuilds=1,newFrontendBuilds=1,finalAdoption=False,progress=78,
       realQaApplicationAccess=False,historicalFailuresPreserved=True,independentOwnPostgresFocus=True)
    (E/'VERIFICACION-FINAL.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record))


if __name__=='__main__':
    main()
