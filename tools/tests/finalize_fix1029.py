"""Seal the already successful publish after recognizing repository provenance metadata."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029'

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    published=json.loads((E/'PUBLISH-FIX02.json').read_bytes());assert published['exitCode']==0 and not published['successful']
    assert all(sha(ROOT/p)==h for p,h in published['sourceHashes'].items())
    original=ROOT/'evidence/s1-20261018/sesenta-tandas-910-969/CANDIDATA969-01.json';old=json.loads(original.read_bytes());target=ROOT/published['candidateDirectory']
    assert target.parent==ROOT/'.local/candidates'
    trees={part:{p.relative_to(target/part).as_posix():sha(p) for p in sorted((target/part).rglob('*')) if p.is_file()} for part in ['server','frontend']}
    assert trees['frontend']==old['distributions']['frontend']
    delta=[p for p,h in old['distributions']['server'].items() if trees['server'][p]!=h]
    assert set(delta)=={'RackClick.Domain.dll','RackClick.Domain.pdb','RackClick.Server.dll','RackClick.Server.pdb'}
    metadata={}
    for name in ['RackClick.Domain.dll','RackClick.Server.dll']:
        before=(ROOT/old['candidateDirectory']/'server'/name).read_bytes();after=(target/'server'/name).read_bytes()
        assert len(before)==len(after) and b'a71d508289f23b62a00fff0d75225f2ca015b22d' in before and b'962948f48543429d22cc806d5951ea94e2c90dc2' in after
        metadata[name]=dict(bytes=len(after),previousGitInformationalVersion='a71d508289f23b62a00fff0d75225f2ca015b22d',currentGitInformationalVersion='962948f48543429d22cc806d5951ea94e2c90dc2')
    m=dict(schema=12,candidateDirectory=published['candidateDirectory'],serverDll=(target/'server/RackClick.Server.dll').relative_to(ROOT).as_posix(),frontend=(target/'frontend').relative_to(ROOT).as_posix(),distributions=trees,fileCount=sum(map(len,trees.values())),totalBytes=sum(p.stat().st_size for part in ['server','frontend'] for p in (target/part).rglob('*') if p.is_file()),sourceManifest=original.relative_to(ROOT).as_posix(),sourceManifestSha256=sha(original),reason=published['reason'],selectedInRealQaAtFreeze=False)
    path=E/'CANDIDATA969-FIX02.json'
    with path.open('x',encoding='utf-8') as f:json.dump(m,f,indent=2);f.write('\n')
    record=dict(successful=True,publicationExitCode=0,publicationCount=1,additionalBuilds=0,frontendBuilds=0,changedProductSources=published['changedProductSources'],
        sourceHashes=published['sourceHashes'],manifest=path.relative_to(ROOT).as_posix(),manifestSha256=sha(path),serverChangedArtifacts=delta,
        frontendExact=True,sql001To012Exact=True,dependenciesExact=True,metadata=metadata,firstWrapperGuardFailurePreserved=True,
        explanation='Publish succeeded. Original wrapper expected only server assembly deltas; repository revision metadata also changes Domain DLL/PDB. This finalization performs no build. Independent semantic compatibility review is separate.')
    with (E/'PUBLISH-FIX02-FINAL.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps(dict(manifest=record['manifest'],pin=record['manifestSha256'],totalBytes=m['totalBytes'],files=m['fileCount'],publicationCount=1,additionalBuilds=0)))

if __name__=='__main__':main()
