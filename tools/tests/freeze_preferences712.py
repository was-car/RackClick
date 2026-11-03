"""Curate immutable schema11 candidate, preserving current schema10 QA and packages."""
import argparse,hashlib,json,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-653-712'
BASE=ROOT/'evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return {x.relative_to(p).as_posix():sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--revision',choices=['01','02'],default='01');a=ap.parse_args()
    name='CANDIDATA712.json' if a.revision=='01' else 'CANDIDATA712-FINAL02.json'
    if (E/name).exists():raise SystemExit('Preserve frozen candidate')
    build=json.loads((E/f'BUILD-{a.revision}.json').read_bytes());assert build['successful'] and build['sourcesUnchanged']
    sources=json.loads((E/f'BUILD-SOURCES-{a.revision}.json').read_bytes())['sources'];assert all(sha(ROOT/p)==h for p,h in sources.items())
    old=json.loads(BASE.read_bytes());published=ROOT/build['rawPublish'];actual=tree(published)
    new_sql={p for p in actual if p.startswith('database/011-') and p.endswith('.sql')};assert len(new_sql)==1
    expected=set(old['distributions']['server'])|new_sql;extras=set(actual)-expected
    assert not expected-set(actual) and extras<={'web.config'}
    target=ROOT/'.local/candidates'/('preferences712-final-'+uuid.uuid4().hex);server=target/'server';server.mkdir(parents=True,exist_ok=False)
    for name0 in sorted(expected):
        p=server/name0;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(published/name0,p)
    shutil.copytree(ROOT/'development/frontend/dist',target/'frontend')
    distributions={part:tree(target/part) for part in ['server','frontend']}
    assert len(distributions['server'])==20 and len(distributions['frontend'])==18
    assert set(distributions['frontend'])==set(old['distributions']['frontend'])
    for p,h in old['distributions']['server'].items():
        if p.startswith('database/') or p in ['Npgsql.dll','RackClick.Server.deps.json','RackClick.Server.runtimeconfig.json']:assert distributions['server'][p]==h,p
    assert all(h==old['distributions']['frontend'][p] for p,h in distributions['frontend'].items() if p!='app.js')
    sql=next(iter(new_sql));assert distributions['server'][sql]==sha(ROOT/'development/server'/sql)
    write(E/f'SOURCE-FREEZE-APP-{a.revision}.json',{'utc':datetime.now(timezone.utc).isoformat(),'sources':sources})
    tests=list((ROOT/'development/server/tests').glob('*preferences*'))+list((ROOT/'development/frontend/tests').glob('*preferences*'))
    tests=[p for p in tests if p.is_file()]
    write(E/f'SOURCE-FREEZE-TESTS-{a.revision}.json',{'sources':{p.relative_to(ROOT).as_posix():sha(p) for p in tests},'scope':'Harness source identities are independent of immutable application build. Preserve failed sources before corrections.'})
    manifest={'utc':datetime.now(timezone.utc).isoformat(),'baseCommit':json.loads((E/'INICIO.json').read_bytes())['baseCommit'],'schema':11,
        'candidateDirectory':target.relative_to(ROOT).as_posix(),'serverDll':(server/'RackClick.Server.dll').relative_to(ROOT).as_posix(),'frontend':(target/'frontend').relative_to(ROOT).as_posix(),
        'selectedInRealQaAtFreeze':False,'sourceManifest':BASE.relative_to(ROOT).as_posix(),'sourceManifestSha256':sha(BASE),
        'scope':'Personal language/theme, SQL011. Current QA592/schema10 and Windows652 package stay unchanged; not a schema11 Windows installation or actual QA migration.',
        'distributions':distributions,'fileCount':sum(map(len,distributions.values())),'totalBytes':sum(p.stat().st_size for part in distributions for p in (target/part).rglob('*') if p.is_file())}
    write(E/name,manifest);write(E/f'CURATION-{a.revision}.json',{'rawPublish':build['rawPublish'],'excludedGeneratedIisFiles':{p:actual[p] for p in sorted(extras)},'rawPublishDeleted':False})
    print(json.dumps({'manifest':name,'sha256':sha(E/name),'files':manifest['fileCount'],'bytes':manifest['totalBytes'],'sources':len(sources),'candidateDirectory':manifest['candidateDirectory']}))
if __name__=='__main__':main()
