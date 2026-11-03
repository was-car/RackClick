"""Initialize and build the category-pair palette without touching selected QA."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import time
import uuid

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-1030-1089'
GIT=ROOT/'.local/git-2.55.0.5/cmd/git.exe'

def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def write(p,value):
    with p.open('x',encoding='utf-8') as stream:stream.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def init():
    E.mkdir(parents=True,exist_ok=True);assert not (E/'INICIO.json').exists()
    pointer=ROOT/'.local/qa-rc9/current.json';selected=Path(json.loads(pointer.read_bytes())['directory'])
    runtime={'postgres.log','manual-control.log','manual-server.log','pg_ctl.log','preview-manual-qa.json','stop.request','server.lock'}
    paths=[pointer]+[p for p in selected.iterdir() if p.is_file() and p.name not in runtime]
    previous=ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029'
    paths+=list(previous.rglob('*'))
    manifest=json.loads((previous/'CANDIDATA969-FIX02.json').read_bytes())
    paths+=list((ROOT/manifest['candidateDirectory']).rglob('*'))
    paths+=list((ROOT/'development/server/src/RackClick.Domain').rglob('*.cs'))
    paths+=list((ROOT/'development/server/database').glob('*.sql'))
    paths+=[ROOT/p for p in ['development/toolchain.lock.json','development/server/global.json',
        'development/server/Directory.Build.props','development/server/src/RackClick.Server/RackClick.Server.csproj',
        'development/frontend/build.mjs','development/frontend/package.json','development/frontend/package-lock.json']]
    paths+=list((ROOT/'development/frontend/rc9-reference').rglob('*'))
    guards={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths)) if p.is_file() and not any(v in ['bin','obj'] for v in p.parts)}
    write(E/'INICIO.json',dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=subprocess.check_output([str(GIT),'rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        guards=guards,selectedQaDirectory=selected.relative_to(ROOT).as_posix(),selectedQaRevision=969,selectedQaSchema=12,
        selectedQaRuntimeFilesExcluded=sorted(runtime),realQaMutationAuthorizedByThisBlock=False,progress=78))
    print(json.dumps(dict(protectedFiles=len(guards),selectedQaRevision=969,progress=78)))

def build(attempt,server_only=False):
    assert len(attempt)==2 and attempt.isdecimal();report=E/f'BUILD-{attempt}.json';assert not report.exists()
    files=list((ROOT/'development/server/src').rglob('*.cs'))+list((ROOT/'development/server/database').glob('*.sql'))+list((ROOT/'development/frontend/src').rglob('*'))
    files += [ROOT/p for p in ['development/server/global.json','development/server/Directory.Build.props','development/server/src/RackClick.Server/RackClick.Server.csproj','development/frontend/build.mjs','development/frontend/package.json','development/frontend/package-lock.json']]
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(files)) if p.is_file() and not any(v in ['obj','bin'] for v in p.parts)}
    write(E/f'SOURCE-FREEZE-{attempt}.json',dict(sources=sources))
    target=ROOT/'.local/candidates'/('category1089-publish-'+uuid.uuid4().hex)
    steps=[('publish',[str(ROOT/'.local/dotnet-10.0.401/dotnet.exe'),'publish','src/RackClick.Server/RackClick.Server.csproj','-c','Release','--no-restore','-o',str(target),'-p:UseAppHost=false'],ROOT/'development/server'),
        ('domain',[str(ROOT/'.local/dotnet-10.0.401/dotnet.exe'),'run','--project','tests/RackClick.Domain.Tests/RackClick.Domain.Tests.csproj','-c','Release','--no-restore'],ROOT/'development/server'),
        ('frontend',[str(ROOT/'.local/node-v24.21.0-win-x64/node.exe'),'build.mjs'],ROOT/'development/frontend')]
    if server_only:
        assert attempt!='01' and json.loads((E/'BUILD-01.json').read_bytes())['successful']
        initial=json.loads((E/'SOURCE-FREEZE-01.json').read_bytes())['sources']
        assert set(initial)==set(sources)
        assert [p for p,h in sources.items() if initial[p]!=h]==['development/server/src/RackClick.Server/InventoryStore.cs']
        steps=steps[:1]
    results=[]
    for name,command,cwd in steps:
        started=time.monotonic();log=E/f'build-{attempt}-{name}.log'
        with log.open('xb') as stream:result=subprocess.run(command,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
        results.append(dict(name=name,exitCode=result.returncode,seconds=round(time.monotonic()-started,3),command=command,log=log.relative_to(ROOT).as_posix()))
        if result.returncode:break
    unchanged=all(sha(ROOT/p)==h for p,h in sources.items())
    record=dict(utc=datetime.now(timezone.utc).isoformat(),sourcesUnchanged=unchanged,sourceCount=len(sources),rawPublish=target.relative_to(ROOT).as_posix(),steps=results,
        successful=len(results)==len(steps) and all(v['exitCode']==0 for v in results) and unchanged,actualQaAccessed=False,
        frontendReusedFromCandidate01=server_only,domain76ReusedFromBuild01=server_only)
    write(report,record);print(json.dumps(record));return 0 if record['successful'] else 1

def freeze(attempt):
    build_record=json.loads((E/f'BUILD-{attempt}.json').read_bytes());assert build_record['successful']
    sources=json.loads((E/f'SOURCE-FREEZE-{attempt}.json').read_bytes())['sources']
    assert all(sha(ROOT/p)==h for p,h in sources.items())
    target=ROOT/'.local/candidates'/('category1089-'+attempt+'-'+uuid.uuid4().hex)
    target.mkdir();shutil.copytree(ROOT/build_record['rawPublish'],target/'server',ignore=shutil.ignore_patterns('RackClick.Server.exe'))
    source_frontend=ROOT/'development/frontend/dist'
    if build_record.get('frontendReusedFromCandidate01'):
        original=json.loads((E/'CANDIDATA1089-01.json').read_bytes());source_frontend=ROOT/original['frontend']
    shutil.copytree(source_frontend,target/'frontend')
    distributions={part:{p.relative_to(target/part).as_posix():sha(p) for p in sorted((target/part).rglob('*')) if p.is_file()} for part in ['server','frontend']}
    count=sum(len(v) for v in distributions.values());assert count==40
    total=sum(p.stat().st_size for p in target.rglob('*') if p.is_file())
    manifest=dict(schema=13,candidateDirectory=target.relative_to(ROOT).as_posix(),serverDll=(target/'server/RackClick.Server.dll').relative_to(ROOT).as_posix(),
        frontend=(target/'frontend').relative_to(ROOT).as_posix(),distributions=distributions,fileCount=count,totalBytes=total,selectedInRealQa=False,
        excludedPublishAppHost='RackClick.Server.exe (distribution runs dotnet RackClick.Server.dll); raw publication retained' if (ROOT/build_record['rawPublish']/'RackClick.Server.exe').exists() else None)
    path=E/f'CANDIDATA1089-{attempt}.json';write(path,manifest)
    print(json.dumps(dict(manifest=path.relative_to(ROOT).as_posix(),sha256=sha(path),fileCount=count,totalBytes=total,selectedInRealQa=False)))

def environment():
    lock=json.loads((ROOT/'development/toolchain.lock.json').read_bytes());versions={}
    for row in lock['components']:
        command=[str(ROOT/'.local'/row['installDirectory']/row['executable']),'--version']
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,check=True)
        versions[row['id']]=dict(command=command,stdout=result.stdout.strip(),stderr=result.stderr.strip(),exitCode=result.returncode)
    write(E/'ENTORNO.json',dict(platform=platform.platform(),python=platform.python_version(),versions=versions,downloads=0,installedDependencies=0,versionChanges=0))
    print(json.dumps(versions))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['init','environment','build','build-fix','freeze']);parser.add_argument('--attempt',default='01');a=parser.parse_args()
    if a.action=='init':init();return 0
    if a.action=='environment':environment();return 0
    if a.action=='freeze':freeze(a.attempt);return 0
    return build(a.attempt,server_only=a.action=='build-fix')

if __name__=='__main__':raise SystemExit(main())
