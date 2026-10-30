"""Seal new public evidence only after the independent closure metadata is valid."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-773-832';E=ROOT/ER;GIT=str(ROOT/'.local/git-2.55.0.5/cmd/git.exe')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--review-seal-sha256',required=True);a=ap.parse_args()
    assert not (E/'SHA256SUMS').exists() and not (E/'CAMBIOS.patch').exists(),'Preserve prior seal'
    assert sha(E/'revision/SEAL-REVISION.json')==a.review_seal_sha256
    closing=json.loads((E/'revision/METADATOS-CIERRE.json').read_bytes());assert closing['valid'] and (E/'revision/ADENDA-CIERRE.md').is_file()
    for p,h in closing['observedFilesSha256'].items():assert sha(E/p)==h,p
    for p,h in closing['continuityDocumentsSha256'].items():assert sha(ROOT/p)==h,p
    for p,d in closing['guides'].items():assert sha(ROOT/p)==d['sha256'],p
    gate=json.loads((E/'revision/GATE-TECNICO.json').read_bytes());assert gate['valid']
    for p,h in gate['sourceHashes'].items():assert sha(ROOT/p)==h,p
    for p,h in gate['observedFilesSha256'].items():assert sha(E/p)==h,p
    assert json.loads((E/'VERIFICACION-FINAL.json').read_bytes())['successful']
    exceptions=json.loads((E/'EXCEPCION-DIFF-CHECK.json').read_bytes())['paths']
    for p,h in exceptions.items():assert sha(ROOT/p)==h,p
    changed=subprocess.check_output([GIT,'ls-files','-m','-o','--exclude-standard','-z'],cwd=ROOT)
    paths=[p.decode() for p in changed.split(b'\0') if p]
    allowed=('development/','docs/',ER+'/','tools/tests/','tools/windows/qa_guide.py')
    assert all(p.startswith(allowed) or p in ['CHANGELOG.md','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html'] for p in paths)
    subprocess.run([GIT,'add','--',*paths],cwd=ROOT,check=True)
    excludes=[':(exclude)'+p for p in exceptions]
    subprocess.run([GIT,'diff','--cached','--check','--','.',*excludes],cwd=ROOT,check=True)
    patch=subprocess.check_output([GIT,'diff','--cached','--binary','--','.',':(exclude)'+ER+'/**'],cwd=ROOT);assert b'diff --git' in patch
    (E/'CAMBIOS.patch').write_bytes(patch)
    files=sorted(p for p in E.rglob('*') if p.is_file() and p.name!='SHA256SUMS')
    (E/'SHA256SUMS').write_bytes(('\n'.join(sha(p)+'  '+p.relative_to(E).as_posix() for p in files)+'\n').encode())
    subprocess.run([GIT,'add','--',ER],cwd=ROOT,check=True)
    subprocess.run([GIT,'diff','--cached','--check','--','.',*excludes,':(exclude)'+ER+'/CAMBIOS.patch'],cwd=ROOT,check=True)
    print(json.dumps(dict(files=len(files),sha256Sums=sha(E/'SHA256SUMS'),publicDiffBytes=len(patch),published=False)))
if __name__=='__main__':main()
