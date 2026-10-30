"""Group receipt development block; never starts or selects the actual QA."""
import argparse,hashlib,json,shutil,subprocess,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-1390-1449';E=ROOT/ER
BASE='7fcd0f6807b962c05faf666077a491810719ecca';GIT=ROOT/'.local/git-2.55.0.5/cmd/git.exe'
TARGET='evidence/s1-20261018/sesenta-tandas-1270-1329/CANDIDATA1329-01.json';PIN='38bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6'
MUTABLE=['development/frontend/src/AdminGroupCreation.jsx','development/frontend/src/AdminGroups.jsx','development/frontend/src/AdminGroupRelations.jsx']
NEW=['development/frontend/src/AdminGroupReceipt.jsx','development/frontend/src/admin-group-receipt.ts']
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(name,data):
 with (E/name).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
def exact(values):assert values and all(sha(ROOT/p)==h for p,h in values.items())
def tree(p):return {f.relative_to(p).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def init():
 E.mkdir(parents=True,exist_ok=True);assert not (E/'INICIO.json').exists();assert subprocess.check_output([str(GIT),'rev-parse','HEAD']).decode().strip()==BASE
 assert not subprocess.check_output([str(GIT),'diff','--name-only']) and not subprocess.check_output([str(GIT),'diff','--cached','--name-only']);assert sha(ROOT/TARGET)==PIN
 previous=read(ROOT/'evidence/s1-20261018/sesenta-tandas-1330-1389/INICIO.json');old_mutable=set(previous['authorizedMutableGuards'])|set(previous['authorizedMutableRuntimeFiles']);old_guards={p:h for p,h in previous['guards'].items() if p not in old_mutable};exact(old_guards)
 sources=read(ROOT/'evidence/s1-20261018/sesenta-tandas-1330-1389/SOURCE-FREEZE-APP.json')['sources'];assert len(sources)==193;exact(sources)
 pointer=ROOT/'.local/qa-rc9/current.json';directory=Path(read(pointer)['directory']);cfg=read(directory/'manual-qa.json');assert cfg['bundleSha256']==read(ROOT/TARGET)['distributions']['frontend']['app.js']
 paths=[ROOT/p for p in old_guards]+[p for p in directory.iterdir() if p.is_file()]+[pointer]
 for part in ['server','frontend','versions']:paths.extend(p for p in (directory/part).rglob('*') if p.is_file())
 for block in ['sesenta-tandas-1330-1389','sesenta-tandas-1270-1329']:paths.extend(p for p in (ROOT/'evidence/s1-20261018'/block).rglob('*') if p.is_file())
 package=read(ROOT/'evidence/s1-20261018/sesenta-tandas-1330-1389/SOURCE-FREEZE-PACKAGE-03.json');paths.extend(ROOT/p for p in package['sources'])
 paths.append(ROOT/'tools/windows/qa_guide.py');guards={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}
 save('INICIO.json',dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=BASE,guards=guards,originalProductSources=sources,allowedProductChanges=MUTABLE,allowedNewProductSources=NEW,qaDirectory=directory.relative_to(ROOT).as_posix(),qaFrontend=1329,qaSchema=13,qaRecoveryRevision=969,qaRecoverySchema=12,qaConfigSha256=sha(directory/'manual-qa.json'),qaPointerSha256=sha(pointer),sourceManifest=TARGET,sourceManifestSha256=PIN,maximumPlannedFrontendBuilds=1,serverBuilds=0,actualQaOperations=0,progress=78))
 print(json.dumps(dict(guards=len(guards),productSources=193,actualQaOperations=0,progress=78)))
def guarded():
 i=read(E/'INICIO.json');exact({p:h for p,h in i['guards'].items() if p not in MUTABLE});exact({p:h for p,h in i['originalProductSources'].items() if p not in MUTABLE});return i
def build():
 assert not (E/'BUILD-01.json').exists();i=guarded();gate=read(E/'revision/REVISION-FUENTE.json');assert gate['approved'] and not gate['openBlockingFindings'];exact(gate['sourceHashes']);assert set(gate['sourceHashes'])==set(MUTABLE+NEW);sources={p:sha(ROOT/p) for p in i['originalProductSources']};added=[p for p in NEW if (ROOT/p).exists()];sources.update({p:sha(ROOT/p) for p in added});changed=[p for p,h in sources.items() if p in i['originalProductSources'] and h!=i['originalProductSources'][p]];assert set(changed)==set(MUTABLE)
 save('SOURCE-FREEZE-APP.json',dict(sources=sources,sourceCount=len(sources),changedExistingSources=changed,newSources=added,serverSourcesUnchanged=True))
 import time
 node=ROOT/'.local/node-v24.21.0-win-x64/node.exe';assert subprocess.check_output([str(node),'--version']).decode().strip()=='v24.21.0';started=time.monotonic()
 with (E/'frontend-build01.log').open('xb') as f:r=subprocess.run([str(node),'build.mjs'],cwd=ROOT/'development/frontend',stdout=f,stderr=subprocess.STDOUT,timeout=180)
 exact(sources);save('BUILD-01.json',dict(successful=r.returncode==0,exitCode=r.returncode,seconds=round(time.monotonic()-started,3),frontendBuilds=1,serverBuilds=0,dependencyChanges=0,actualQaOperations=0));assert r.returncode==0
 old=read(ROOT/TARGET);dest=ROOT/'.local/candidates'/('group-receipt1449-01-'+uuid.uuid4().hex);shutil.copytree(ROOT/old['candidateDirectory']/'server',dest/'server');shutil.copytree(ROOT/'development/frontend/dist',dest/'frontend');distributions={part:tree(dest/part) for part in ['server','frontend']}
 assert distributions['server']==old['distributions']['server'] and len(distributions['frontend'])==18 and {p for p,h in distributions['frontend'].items() if h!=old['distributions']['frontend'][p]}=={'app.js'}
 m=dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=BASE,schema=13,candidateDirectory=dest.relative_to(ROOT).as_posix(),serverDll=(dest/'server/RackClick.Server.dll').relative_to(ROOT).as_posix(),frontend=(dest/'frontend').relative_to(ROOT).as_posix(),sourceManifest=TARGET,sourceManifestSha256=PIN,distributions=distributions,fileCount=40,totalBytes=sum(p.stat().st_size for p in dest.rglob('*') if p.is_file()),selectedInRealQaAtFreeze=False,scope='Development distribution only; server1089/schema13 exact, only app.js differs from1329. QA1329/Windows1389 unchanged.')
 save('CANDIDATA1449-01.json',m);print(json.dumps(dict(successful=True,sourceCount=len(sources),files=40,bytes=m['totalBytes'],manifestSha256=sha(E/'CANDIDATA1449-01.json'))))
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['init','build']);a=p.parse_args();globals()[a.action]()
if __name__=='__main__':main()
