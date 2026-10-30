"""One coordinated Windows build of the RC9 Excel HTML application sources."""
import argparse,hashlib,json,subprocess,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-773-832'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--revision',default='01');ap.add_argument('--skip-domain',action='store_true');a=ap.parse_args()
    assert a.revision in ['01','02','03']
    report=E/f'BUILD-{a.revision}.json';freeze=E/f'BUILD-SOURCES-{a.revision}.json'
    assert not report.exists() and not freeze.exists(),'Preserve prior build evidence'
    files=list((ROOT/'development/server/src').rglob('*.cs'))+list((ROOT/'development/server/database').glob('*.sql'))+list((ROOT/'development/frontend/src').rglob('*'))
    files += [ROOT/p for p in ['development/server/global.json','development/server/Directory.Build.props','development/server/src/RackClick.Server/RackClick.Server.csproj','development/frontend/build.mjs','development/frontend/package.json','development/frontend/package-lock.json']]
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(files)) if p.is_file() and not any(x in ['obj','bin'] for x in p.parts)}
    freeze.write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'sources':sources},indent=2)+'\n',encoding='utf-8')
    target=ROOT/'.local/candidates'/('excel832-publish-'+uuid.uuid4().hex)
    steps=[('publish',[str(ROOT/'.local/dotnet-10.0.401/dotnet.exe'),'publish','src/RackClick.Server/RackClick.Server.csproj','-c','Release','--no-restore','-o',str(target)],ROOT/'development/server'),('domain',[str(ROOT/'.local/dotnet-10.0.401/dotnet.exe'),'run','--project','tests/RackClick.Domain.Tests/RackClick.Domain.Tests.csproj','-c','Release','--no-restore'],ROOT/'development/server'),('frontend',[str(ROOT/'.local/node-v24.21.0-win-x64/node.exe'),'build.mjs'],ROOT/'development/frontend')]
    if a.skip_domain:
        assert a.revision!='01' and json.loads((E/'BUILD-01.json').read_bytes())['successful']
        initial=json.loads((E/'BUILD-SOURCES-01.json').read_bytes())['sources']
        assert all(sha(ROOT/p)==h for p,h in initial.items() if p.startswith('development/server/src/RackClick.Domain/'))
        steps=[x for x in steps if x[0]!='domain']
    results=[]
    for name,cmd,cwd in steps:
        start=time.monotonic();log=E/f'build-{a.revision}-{name}.log'
        with log.open('xb') as f:r=subprocess.run(cmd,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=180)
        results.append(dict(name=name,exitCode=r.returncode,seconds=round(time.monotonic()-start,3),command=cmd,log=log.relative_to(ROOT).as_posix()))
        if r.returncode:break
    unchanged=all(sha(ROOT/p)==h for p,h in sources.items())
    record=dict(utc=datetime.now(timezone.utc).isoformat(),sourcesUnchanged=unchanged,sourceCount=len(sources),rawPublish=target.relative_to(ROOT).as_posix(),steps=results,successful=len(results)==len(steps) and all(x['exitCode']==0 for x in results) and unchanged,actualQaAccessed=False,domainReusedFrom='BUILD-01.json; unchanged domain sources,76 PASS' if a.skip_domain else None)
    report.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record,indent=2));return 0 if record['successful'] else 1
if __name__=='__main__':raise SystemExit(main())
