"""Freeze a built details candidate, with immutable schema/dependency/RC9 guards."""
import hashlib,json,shutil,subprocess,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/cuarenta-y-cinco-tandas-428-472'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return {x.relative_to(p).as_posix():digest(x) for x in sorted(p.rglob('*')) if x.is_file()}
def main():
    m=E/'CANDIDATA472.json'
    if m.exists():raise SystemExit('Candidate already frozen; use a new manifest/output for an actual correction.')
    old=json.loads((ROOT/'evidence/s1-20261017/treinta-tandas-368-397/CANDIDATA397.json').read_text())
    raw=json.loads((E/'CANDIDATE-PATHS-01.json').read_text());published=ROOT/raw['server']
    actual=tree(published);expected=set(old['distributions']['server']);extras=set(actual)-expected
    assert not expected-set(actual) and extras<= {'web.config'},'Unexpected publish output'
    candidate=ROOT/'.local/candidates'/('details472-final-'+uuid.uuid4().hex)
    server=candidate/'server';server.mkdir(parents=True,exist_ok=False)
    for name in sorted(expected):
        target=server/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(published/name,target)
    shutil.copytree(ROOT/'development/frontend/dist',candidate/'frontend')
    paths={'candidateDirectory':candidate.relative_to(ROOT).as_posix(),'server':server.relative_to(ROOT).as_posix(),'frontend':(candidate/'frontend').relative_to(ROOT).as_posix()}
    (E/'CURATION-02.json').write_text(json.dumps({'rawPublish':raw['server'],'curated':paths,'excludedGeneratedIisFiles':{name:actual[name] for name in sorted(extras)},'reason':'Preserve the established standalone Windows/runtime distribution. Generated IIS web.config is retained in raw publish, not part of this candidate. No raw output deleted or rebuilt.'},indent=2)+'\n',encoding='utf-8')
    distributions={part:tree(candidate/part) for part in ['server','frontend']}
    for part in distributions:
        assert set(distributions[part])==set(old['distributions'][part]),(part,'Distribution filenames changed')
    fixed={'server':['Npgsql.dll','RackClick.Server.deps.json','RackClick.Server.runtimeconfig.json']+[p for p in distributions['server'] if p.startswith('database/')],'frontend':[p for p in distributions['frontend'] if p!='app.js']}
    for part,names in fixed.items():
        for name in names:assert distributions[part][name]==old['distributions'][part][name],(part,name,'Pinned SQL/dependency/RC9 asset changed')
    sources=list((ROOT/'development/server/src').rglob('*.cs'))+list((ROOT/'development/server/database').glob('*.sql'))+list((ROOT/'development/frontend/src').rglob('*'))
    sources=[p for p in sources if p.is_file() and not any(x in p.parts for x in ['obj','bin'])]
    sources += [ROOT/p for p in ['development/server/tests/test_inventory_change_details.py','development/server/tests/test_inventory_change_details_gui.py','development/frontend/tests/client-change-details.test.mjs','development/frontend/tests/browser-client-change-details.mjs','tools/tests/freeze_details472.py']]
    frozen={p.relative_to(ROOT).as_posix():digest(p) for p in sorted(set(sources))}
    (E/'SOURCE-FREEZE-01.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'sources':frozen},indent=2)+'\n',encoding='utf-8')
    manifest={'utc':datetime.now(timezone.utc).isoformat(),'baseCommit':subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'schema':9,**paths,'serverDll':(candidate/'server/RackClick.Server.dll').relative_to(ROOT).as_posix(),'selectedInRealQaAtFreeze':False,'sourceManifest':'evidence/s1-20261017/treinta-tandas-368-397/CANDIDATA397.json','scope':'Versioned historical inventory details, opt-in API and GUI; no SQL/pin/QA185/offline427 change.','distributions':distributions,'fileCount':sum(map(len,distributions.values())),'totalBytes':sum(p.stat().st_size for part in ['server','frontend'] for p in (candidate/part).rglob('*') if p.is_file())}
    m.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'manifest':m.relative_to(ROOT).as_posix(),'sha256':digest(m),'files':manifest['fileCount'],'bytes':manifest['totalBytes'],'sources':len(frozen),'serverDllSha256':distributions['server']['RackClick.Server.dll'],'guiSha256':distributions['frontend']['app.js']}))
if __name__=='__main__':main()
