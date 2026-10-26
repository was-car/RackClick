"""Curate immutable schema10 development candidate; no package or real QA selection."""
import argparse,hashlib,json,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-533-592'
BASE=ROOT/'evidence/s1-20261018/sesenta-tandas-473-532/CANDIDATA532-FINAL03.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return {x.relative_to(p).as_posix():sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
def save(p,v):p.write_bytes((json.dumps(v,indent=2)+'\n').encode('utf-8'))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--raw-server',type=Path,required=True);parser.add_argument('--revision',type=int,default=1);a=parser.parse_args()
    rev=f'{a.revision:02d}';manifest='CANDIDATA592.json' if a.revision==1 else f'CANDIDATA592-FINAL{rev}.json'
    if (E/manifest).exists():raise SystemExit('Preserve existing candidate/freeze evidence')
    published=a.raw_server.resolve(strict=True)
    assert published.is_relative_to((ROOT/'.local/candidates').resolve()) and published.is_dir()
    before=json.loads((E/f'FRONTEND-BUILD-SOURCE-{rev}.json').read_bytes())['sources']
    assert all(sha(ROOT/p)==h for p,h in before.items()),'Frontend source changed during coordinated build'
    old=json.loads(BASE.read_bytes());actual=tree(published);expected=set(old['distributions']['server'])
    new_sql={p for p in actual if p.startswith('database/010-') and p.endswith('.sql')}
    assert len(new_sql)==1
    expected|=new_sql;extras=set(actual)-expected
    assert not expected-set(actual) and extras<={'web.config'},'Unexpected publish layout'
    target=ROOT/'.local/candidates'/('shared592-final-'+uuid.uuid4().hex);server=target/'server';server.mkdir(parents=True,exist_ok=False)
    for name in sorted(expected):
        p=server/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(published/name,p)
    shutil.copytree(ROOT/'development/frontend/dist',target/'frontend')
    distributions={part:tree(target/part) for part in ['server','frontend']}
    assert len(distributions['server'])==19 and set(distributions['frontend'])==set(old['distributions']['frontend'])
    for p,h in old['distributions']['server'].items():
        if p.startswith('database/') or p in ['Npgsql.dll','RackClick.Server.deps.json','RackClick.Server.runtimeconfig.json']:
            assert distributions['server'][p]==h,p
    assert all(h==old['distributions']['frontend'][p] for p,h in distributions['frontend'].items() if p!='app.js')
    sql_name=next(iter(new_sql));assert distributions['server'][sql_name]==sha(ROOT/'development/server'/sql_name)
    files=list((ROOT/'development/server/src').rglob('*.cs'))+list((ROOT/'development/server/database').glob('*.sql'))
    files+=list((ROOT/'development/frontend/src').rglob('*'))
    files=[p for p in files if p.is_file() and not any(part in ['obj','bin'] for part in p.parts)]
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(files))}
    tests=list((ROOT/'development/server/tests').glob('*shared*.py'))+list((ROOT/'development/frontend/tests').glob('*shared*'))
    tests=[p for p in tests if p.is_file()]
    save(E/f'SOURCE-FREEZE-APP-{rev}.json',dict(utc=datetime.now(timezone.utc).isoformat(),sources=sources))
    save(E/f'SOURCE-FREEZE-TESTS-{rev}.json',dict(sources={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(tests)},
        note='Separate test freeze; a harness-only correction does not require rebuilding unchanged application code. Preserve each executed source/hash.'))
    m=dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=json.loads((E/'INICIO.json').read_bytes())['baseCommit'],schema=10,
        candidateDirectory=target.relative_to(ROOT).as_posix(),serverDll=(server/'RackClick.Server.dll').relative_to(ROOT).as_posix(),
        frontend=(target/'frontend').relative_to(ROOT).as_posix(),selectedInRealQaAtFreeze=False,sourceManifest=BASE.relative_to(ROOT).as_posix(),
        sourceManifestSha256=sha(BASE),scope='Customer-scoped shared template publications. Additive SQL010, no historical grants. Development laboratory candidate; QA/ZIP532 stay schema9.',
        distributions=distributions,fileCount=sum(map(len,distributions.values())),totalBytes=sum(p.stat().st_size for part in distributions for p in (target/part).rglob('*') if p.is_file()))
    save(E/manifest,m);save(E/f'CURATION-{rev}.json',dict(rawPublish=published.relative_to(ROOT).as_posix(),finalCandidate=m['candidateDirectory'],
        excludedGeneratedIisFiles={p:actual[p] for p in sorted(extras)},rawPublishDeleted=False))
    print(json.dumps(dict(manifest=manifest,manifestSha256=sha(E/manifest),files=m['fileCount'],bytes=m['totalBytes'],productSources=len(sources),testSources=len(tests),candidateDirectory=m['candidateDirectory'])))
if __name__=='__main__':main()
