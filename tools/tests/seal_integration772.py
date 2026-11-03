"""Seal the public integration diff and evidence after independent closing review."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-713-772';E=ROOT/ER;GIT=str(ROOT/'.local/git-2.55.0.5/cmd/git.exe')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--verification',default='VERIFICACION-FINAL-01.json');a=ap.parse_args()
    assert (E/a.verification).resolve().is_relative_to(E.resolve())
    for name in ['CAMBIOS.patch','SHA256SUMS']:
        if (E/name).exists():raise SystemExit('Preserve previous seal')
    assert json.loads((E/a.verification).read_bytes())['successful']
    closing=json.loads((E/'revision/METADATOS-CIERRE.json').read_bytes());assert closing['valid'] and (E/'revision/ADENDA-CIERRE.md').is_file()
    assert all(sha(E/p)==h for p,h in closing['observedFilesSha256'].items())
    assert all(sha(ROOT/p)==h for p,h in closing['continuityDocumentsSha256'].items())
    if 'guides' in closing:assert all(sha(ROOT/p)==d['sha256'] for p,d in closing['guides'].items())
    output=subprocess.check_output([GIT,'ls-files','-m','-o','--exclude-standard','-z'],cwd=ROOT);paths=[p.decode() for p in output.split(b'\0') if p]
    allowed=('development/','docs/',ER+'/','tools/tests/','tools/windows/','tools/package_offline_bundle.py')
    assert all(p.startswith(allowed) or p in ['CHANGELOG.md','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html'] for p in paths)
    assert not any(p.startswith('.local/') for p in paths)
    if paths:subprocess.run([GIT,'add','--',*paths],cwd=ROOT,check=True)
    # Raw output from this block's failed profiles01 retains its original whitespace.
    raw_log=':(exclude)'+ER+'/windows/profiles01/tests.log'
    subprocess.run([GIT,'diff','--cached','--check','--','.',raw_log],cwd=ROOT,check=True)
    diff=subprocess.check_output([GIT,'diff','--cached','--binary','--','.',':(exclude)'+ER+'/**'],cwd=ROOT)
    assert diff and b'diff --git' in diff
    with (E/'CAMBIOS.patch').open('xb') as f:f.write(diff)
    files=sorted(p for p in E.rglob('*') if p.is_file() and p.name!='SHA256SUMS')
    with (E/'SHA256SUMS').open('xb') as f:f.write(('\n'.join(sha(p)+'  '+p.relative_to(E).as_posix() for p in files)+'\n').encode())
    subprocess.run([GIT,'add','--',ER],cwd=ROOT,check=True)
    subprocess.run([GIT,'diff','--cached','--check','--','.',raw_log,':(exclude)'+ER+'/CAMBIOS.patch'],cwd=ROOT,check=True)
    print(json.dumps(dict(evidenceFiles=len(files),sha256Sums=sha(E/'SHA256SUMS'),publicDiffBytes=len(diff),published=False)))
if __name__=='__main__':main()
