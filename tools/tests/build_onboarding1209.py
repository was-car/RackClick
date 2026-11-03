"""Build the bounded frontend once and copy the unchanged schema13 server."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
import time
import uuid
from init_onboarding1209 import ROOT,E,BASE,TARGET,PIN,MUTABLE,NEW,sha

def tree(path):return {p.relative_to(path).as_posix():sha(p) for p in sorted(path.rglob('*')) if p.is_file()}
def save(name,data):
    with (E/name).open('x',encoding='utf-8') as stream:stream.write(json.dumps(data,indent=2)+'\n')

def main():
    assert not (E/'BUILD-01.json').exists()
    initial=json.loads((E/'INICIO.json').read_bytes());assert initial['baseCommit']==BASE and sha(ROOT/TARGET)==PIN
    old=json.loads((ROOT/TARGET).read_bytes());original=initial['originalProductSources']
    assert all(sha(ROOT/p)==h for p,h in initial['guards'].items())
    assert all(sha(ROOT/p)==h for p,h in original.items() if p not in MUTABLE)
    assert tree(ROOT/old['candidateDirectory']/'server')==old['distributions']['server']
    sources={p:sha(ROOT/p) for p in list(original)+NEW}
    assert len(sources)==193 and {p for p,h in original.items() if sources[p]!=h}==set(MUTABLE)
    save('SOURCE-FREEZE-APP.json',dict(sources=sources,sourceCount=193,changedExistingSources=MUTABLE,newSources=NEW,serverSourcesUnchanged=True))
    node=ROOT/'.local/node-v24.21.0-win-x64/node.exe';assert subprocess.check_output([str(node),'--version'],text=True).strip()=='v24.21.0'
    started=time.monotonic()
    with (E/'frontend-build01.log').open('xb') as stream:
        done=subprocess.run([str(node),'build.mjs'],cwd=ROOT/'development/frontend',stdout=stream,stderr=subprocess.STDOUT,timeout=180)
    unchanged=all(sha(ROOT/p)==h for p,h in sources.items())
    record=dict(utc=datetime.now(timezone.utc).isoformat(),successful=done.returncode==0 and unchanged,exitCode=done.returncode,
        seconds=round(time.monotonic()-started,3),sourcesUnchanged=unchanged,frontendBuilds=1,serverBuilds=0,dependencyChanges=0,actualQaAccessed=False)
    save('BUILD-01.json',record);assert record['successful']
    target=ROOT/'.local/candidates'/('onboarding1209-01-'+uuid.uuid4().hex)
    shutil.copytree(ROOT/old['candidateDirectory']/'server',target/'server');shutil.copytree(ROOT/'development/frontend/dist',target/'frontend')
    distributions={part:tree(target/part) for part in ['server','frontend']}
    assert distributions['server']==old['distributions']['server'] and len(distributions['server'])==22 and len(distributions['frontend'])==18
    assert set(distributions['frontend'])==set(old['distributions']['frontend'])
    assert {p for p,h in distributions['frontend'].items() if h!=old['distributions']['frontend'][p]}=={'app.js'}
    manifest=dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=BASE,schema=13,candidateDirectory=target.relative_to(ROOT).as_posix(),
        serverDll=(target/'server/RackClick.Server.dll').relative_to(ROOT).as_posix(),frontend=(target/'frontend').relative_to(ROOT).as_posix(),
        sourceManifest=TARGET,sourceManifestSha256=PIN,distributions=distributions,fileCount=40,
        totalBytes=sum(p.stat().st_size for p in target.rglob('*') if p.is_file()),selectedInRealQaAtFreeze=False,
        scope='Complete development distribution; unchanged1089-02 server/schema13. Only app.js changed. Not a Windows bundle profile or selected QA.')
    save('CANDIDATA1209-01.json',manifest)
    print(json.dumps(dict(successful=True,files=40,manifestSha256=sha(E/'CANDIDATA1209-01.json'),bytes=manifest['totalBytes'],frontendBuilds=1,serverBuilds=0)))

if __name__=='__main__':main()
