"""Freeze the existing QA, historical evidence and unchanged product boundaries."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1150-1209'
BASE='488e6a603048d8372b0f434ca84dea4807a589f9'
GIT=ROOT/'.local/git-2.55.0.5/cmd/git.exe'
TARGET='evidence/s1-20261018/sesenta-tandas-1030-1089/CANDIDATA1089-02.json'
PIN='c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c'
MUTABLE=['development/frontend/src/AdminUsers.jsx']
NEW=['development/frontend/src/AdminUserOnboarding.jsx','development/frontend/src/admin-user-onboarding.ts','development/frontend/src/admin-user-onboarding-words.ts']

def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    out=E/'INICIO.json';assert not out.exists();E.mkdir(parents=True,exist_ok=True)
    assert subprocess.check_output([str(GIT),'rev-parse','HEAD'],text=True).strip()==BASE
    assert sha(ROOT/TARGET)==PIN
    product=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-1090-1149/SOURCE-FREEZE-APP.json').read_bytes())['sources']
    assert len(product)==190 and all(sha(ROOT/p)==h for p,h in product.items() if p not in MUTABLE)
    pointer=ROOT/'.local/qa-rc9/current.json';directory=Path(json.loads(pointer.read_bytes())['directory'])
    assert directory.name=='manual-qa-rc9-schema13-d4b6c2c16e4d4beeb12ab9319f368f15'
    cfg=json.loads((directory/'manual-qa.json').read_bytes());assert cfg['bundleSha256']=='2eeaef54bca1a3b7ada0a6002d9274b0a4a36ab9658aec4f495c66d716cb80da'
    source_files=[p for p in directory.iterdir() if p.is_file()]
    source_files+=list((directory/'versions').rglob('*'))
    guards={p.relative_to(ROOT).as_posix():sha(p) for p in source_files if p.is_file()}
    guards[pointer.relative_to(ROOT).as_posix()]=sha(pointer)
    for p in [ROOT/'RackClick-v0.9.0-rc9-Offline.html',ROOT/'development/toolchain.lock.json',ROOT/'development/server/global.json',ROOT/'development/frontend/package-lock.json',ROOT/TARGET]:guards[p.relative_to(ROOT).as_posix()]=sha(p)
    for folder in ['evidence/s1-20261018/sesenta-tandas-1090-1149','evidence/s1-20261018/sesenta-tandas-1030-1089']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file():guards[p.relative_to(ROOT).as_posix()]=sha(p)
    manifest=json.loads((ROOT/TARGET).read_bytes())
    for part,files in manifest['distributions'].items():
        for name,h in files.items():
            p=ROOT/manifest['candidateDirectory']/part/name;assert sha(p)==h;guards[p.relative_to(ROOT).as_posix()]=h
    result=dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=BASE,initialGitStatusObserved='clean before delegation',
        sourceManifest=TARGET,sourceManifestSha256=PIN,originalProductSources=product,allowedProductChanges=MUTABLE,
        allowedNewProductSources=NEW,guards=guards,qaDirectory=directory.relative_to(ROOT).as_posix(),qaSchema=13,
        originalQaRootFiles=len([p for p in directory.iterdir() if p.is_file()]),progress=78,
        scope='Guided account-creation continuation; complete development candidate only. No real QA selection, migration or Windows package update in this block.',
        serverBuilds=0,maximumPlannedFrontendBuilds=1,realQaApplicationAccess=False,manualWascarResultsWritten=False)
    with out.open('x',encoding='utf-8') as stream:stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(valid=True,guards=len(guards),sourceFiles=190,qaRootFiles=result['originalQaRootFiles'],progress=78)))

if __name__=='__main__':main()
