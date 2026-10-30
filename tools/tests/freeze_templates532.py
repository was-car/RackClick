"""Freeze new immutable template-editor artifacts; keep raw publish and prior candidates."""
import argparse,hashlib,json,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-473-532'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return {x.relative_to(p).as_posix():sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--revision',type=int,choices=(1,2,3),default=1);a=parser.parse_args()
    revision=f'{a.revision:02d}';manifest='CANDIDATA532.json' if a.revision==1 else f'CANDIDATA532-FINAL{revision}.json'
    if (E/manifest).exists():raise SystemExit('Candidate already frozen; preserve this manifest')
    if a.revision>=2:
        before=json.loads((E/f'FRONTEND-BUILD-SOURCE-{revision}.json').read_text())['sources']
        assert all(sha(ROOT/p)==h for p,h in before.items()),'Frontend source changed during coordinated build'
    baseline=ROOT/'evidence/s1-20261018/cuarenta-y-cinco-tandas-428-472/CANDIDATA472.json';old=json.loads(baseline.read_text())
    raw=json.loads((E/'BUILD-PATHS-01.json').read_text());published=ROOT/raw['server'];actual=tree(published)
    expected=set(old['distributions']['server']);extras=set(actual)-expected
    assert not expected-set(actual) and extras<= {'web.config'},'Unexpected publish files'
    candidate=ROOT/'.local/candidates'/('templates532-final-'+uuid.uuid4().hex);server=candidate/'server';server.mkdir(parents=True,exist_ok=False)
    for name in sorted(expected):
        target=server/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(published/name,target)
    shutil.copytree(ROOT/'development/frontend/dist',candidate/'frontend');dist={part:tree(candidate/part) for part in ['server','frontend']}
    assert set(dist['server'])==expected and set(dist['frontend'])==set(old['distributions']['frontend'])
    for name in ['Npgsql.dll','RackClick.Server.deps.json','RackClick.Server.runtimeconfig.json']+[x for x in expected if x.startswith('database/')]:assert dist['server'][name]==old['distributions']['server'][name],name
    assert all(h==old['distributions']['frontend'][name] for name,h in dist['frontend'].items() if name!='app.js')
    files=list((ROOT/'development/server/src').rglob('*.cs'))+list((ROOT/'development/server/database').glob('*.sql'))+list((ROOT/'development/frontend/src').rglob('*'))
    files=[p for p in files if p.is_file() and not any(part in ('obj','bin') for part in p.parts)]
    files += [ROOT/p for p in ['development/server/tests/test_private_template_configurations.py','development/server/tests/test_private_template_configurations_gui.py','development/frontend/tests/private-template-configurations.test.mjs','development/frontend/tests/browser-private-template-configurations.mjs']]
    assert all(p.is_file() for p in files),'New GUI/unit harness sources required before freeze'
    frozen={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(files))}
    (E/f'SOURCE-FREEZE-APP-{revision}.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'sources':frozen},indent=2)+'\n',encoding='utf-8')
    m={'utc':datetime.now(timezone.utc).isoformat(),'baseCommit':json.loads((E/'INICIO.json').read_text())['baseCommit'],'schema':9,'candidateDirectory':candidate.relative_to(ROOT).as_posix(),'serverDll':(server/'RackClick.Server.dll').relative_to(ROOT).as_posix(),'frontend':(candidate/'frontend').relative_to(ROOT).as_posix(),'selectedInRealQaAtFreeze':False,'sourceManifest':baseline.relative_to(ROOT).as_posix(),'sourceManifestSha256':sha(baseline),'scope':'New immutable private configuration editor plus XLSX397 and descriptive changes472; no SQL/pin changes.','distributions':dist,'fileCount':sum(map(len,dist.values())),'totalBytes':sum(p.stat().st_size for part in ['server','frontend'] for p in (candidate/part).rglob('*') if p.is_file())}
    path=E/manifest;path.write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
    (E/f'CURATION-{revision}.json').write_text(json.dumps({'rawPublish':raw['server'],'finalCandidate':m['candidateDirectory'],'excludedGeneratedIisFiles':{p:actual[p] for p in sorted(extras)},'rawPublishDeleted':False},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'manifest':manifest,'manifestSha256':sha(path),'files':m['fileCount'],'bytes':m['totalBytes'],'sources':len(frozen),'candidateDirectory':m['candidateDirectory'],'dll':dist['server']['RackClick.Server.dll'],'gui':dist['frontend']['app.js']}))
if __name__=='__main__':main()
