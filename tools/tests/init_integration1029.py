"""Freeze the integration baseline and derive an immutable Windows manifest; no build."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def main():
    E.mkdir(parents=True,exist_ok=True)
    source=ROOT/'evidence/s1-20261018/sesenta-tandas-910-969/CANDIDATA969-01.json'
    source_sha='a74c88607a5471a19f317f685a6defbfa68f01f86bfd19789a01d1000c873030'
    assert sha(source)==source_sha
    m=json.loads(source.read_bytes())
    total=0
    for part,files in m['distributions'].items():
        for name,h in files.items():
            p=ROOT/m['candidateDirectory']/part/name
            assert sha(p)==h
            total+=p.stat().st_size
    assert m['schema']==12 and m['fileCount']==39
    m.update(totalBytes=total,sourceManifest=source.relative_to(ROOT).as_posix(),sourceManifestSha256=source_sha,
        integrationScope='Derived manifest adds aggregate bytes only; all39 artifacts unchanged. Operational support is verified separately.')
    target=E/'CANDIDATA969-WINDOWS.json';write(target,m)
    guards={};paths=[];qa_guards={}
    for pointer in [ROOT/'.local/qa-rc9/current.json',ROOT/'.local/qa-wascar/current.json']:
        paths.append(pointer)
        directory=Path(json.loads(pointer.read_bytes())['directory'])
        for p in directory.iterdir():
            if p.is_file():
                paths.append(p)
                if 'qa-rc9' in pointer.parts:qa_guards[p.relative_to(ROOT).as_posix()]=sha(p)
    paths.extend(p for base in ['evidence/s1-20261018/sesenta-tandas-850-909','evidence/s1-20261018/sesenta-tandas-910-969'] for p in (ROOT/base).rglob('*') if p.is_file())
    for mf in [source,ROOT/'evidence/s1-20261018/tanda-849/CANDIDATA849.json']:
        value=json.loads(mf.read_bytes());paths.append(mf)
        paths.extend(ROOT/value['candidateDirectory']/part/name for part,files in value['distributions'].items() for name in files)
    paths.extend(p for p in (ROOT/'tools/windows').iterdir() if p.is_file())
    paths.extend(ROOT/p for p in ['tools/package_offline_bundle.py','development/toolchain.lock.json','development/offline-bundle.sources.json',
        'development/server/global.json','development/frontend/package-lock.json','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html','docs/QA-CASOS-WASCAR.json'])
    manuals=['MANUAL-PAQUETE-WINDOWS-S1.md','CONSTRUIR-PAQUETE-WINDOWS-S1.md','OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md','RECUPERACION-DESPLIEGUE-WINDOWS-S1.md']
    paths.extend(ROOT/'docs'/p for p in manuals)
    for p in sorted(set(paths)):guards[p.relative_to(ROOT).as_posix()]=sha(p)
    mutable=['tools/package_offline_bundle.py','tools/windows/Test-ServerDistribution.ps1','tools/windows/RackClick.OfflineBundle.ps1',
        'tools/windows/RackClick.Instance.ps1','tools/windows/qa_guide.py','.local/qa-rc9/current.json',
        'GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html','docs/QA-CASOS-WASCAR.json']+['docs/'+p for p in manuals]
    base=subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'rev-parse','HEAD'],text=True).strip()
    write(E/'INICIO.json',dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=base,guards=guards,sourceQaGuards=qa_guards,
        authorizedMutableGuards=mutable,targetManifest=target.relative_to(ROOT).as_posix(),targetManifestSha256=sha(target),
        originalManifestSha256=source_sha,progress=78,applicationBuilds=0,frontendBuilds=0))
    print(json.dumps(dict(base=base,guards=len(guards),sourceQaFiles=len(qa_guards),manifest=target.relative_to(ROOT).as_posix(),pin=sha(target),
        bytes=total,serverFiles=len(m['distributions']['server']),frontendFiles=len(m['distributions']['frontend']))))


if __name__=='__main__':main()
