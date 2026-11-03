"""Curate a separate schema11 candidate; never select it into the real QA."""
import argparse,hashlib,json,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-773-832'
BASE=ROOT/'evidence/s1-20261018/sesenta-tandas-653-712/CANDIDATA712-FINAL02.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return {x.relative_to(p).as_posix():sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--revision',default='01');a=ap.parse_args();assert a.revision in ['01','02','03']
    name=f'CANDIDATA832-{a.revision}.json';assert not (E/name).exists(),'Preserve frozen candidate'
    build=json.loads((E/f'BUILD-{a.revision}.json').read_bytes());assert build['successful']
    sources=json.loads((E/f'BUILD-SOURCES-{a.revision}.json').read_bytes())['sources'];assert all(sha(ROOT/p)==h for p,h in sources.items())
    old=json.loads(BASE.read_bytes());published=ROOT/build['rawPublish'];actual=tree(published);expected=set(old['distributions']['server']);extras=set(actual)-expected
    assert not expected-set(actual) and extras<={'web.config'}
    target=ROOT/'.local/candidates'/('excel832-final-'+uuid.uuid4().hex);server=target/'server';server.mkdir(parents=True,exist_ok=False)
    for n in sorted(expected):
        p=server/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(published/n,p)
    shutil.copytree(ROOT/'development/frontend/dist',target/'frontend');distributions={part:tree(target/part) for part in ['server','frontend']}
    assert len(distributions['server'])==20 and len(distributions['frontend'])==18
    assert set(distributions['frontend'])==set(old['distributions']['frontend'])
    for p,h in old['distributions']['server'].items():
        if p.startswith('database/') or p in ['Npgsql.dll','RackClick.Server.deps.json','RackClick.Server.runtimeconfig.json']:assert distributions['server'][p]==h,p
    assert all(h==old['distributions']['frontend'][p] for p,h in distributions['frontend'].items() if p!='app.js')
    write(E/f'SOURCE-FREEZE-APP-{a.revision}.json',dict(utc=datetime.now(timezone.utc).isoformat(),sources=sources))
    record=dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=json.loads((E/'INICIO.json').read_bytes())['baseCommit'],schema=11,candidateDirectory=target.relative_to(ROOT).as_posix(),serverDll=(server/'RackClick.Server.dll').relative_to(ROOT).as_posix(),frontend=(target/'frontend').relative_to(ROOT).as_posix(),selectedInRealQaAtFreeze=False,sourceManifest=BASE.relative_to(ROOT).as_posix(),sourceManifestSha256=sha(BASE),scope='RC9 three-table XLS HTML rack report. No SQL/dependency change. Current QA712/schema11 and Windows ZIP772 unchanged; no integration into their operator allowlists.',distributions=distributions,fileCount=sum(map(len,distributions.values())),totalBytes=sum(p.stat().st_size for part in distributions for p in (target/part).rglob('*') if p.is_file()))
    write(E/name,record);write(E/f'CURATION-{a.revision}.json',dict(rawPublish=build['rawPublish'],excludedGeneratedIisFiles={p:actual[p] for p in sorted(extras)},rawPublishDeleted=False))
    print(json.dumps(dict(manifest=name,sha256=sha(E/name),files=record['fileCount'],bytes=record['totalBytes'],sources=len(sources),candidateDirectory=record['candidateDirectory'])))
if __name__=='__main__':main()
