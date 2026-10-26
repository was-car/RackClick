"""Seal staged product/document diff and the new evidence without replacing old seals."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-533-592'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    for name in ['CAMBIOS.patch','SHA256SUMS']:
        if (E/name).exists():raise SystemExit('Preserve existing final evidence')
    assert json.loads((E/'VERIFICACION-FINAL.json').read_bytes())['result']=='PASS'
    assert json.loads((E/'revision/METADATOS-FINALES.json').read_bytes())['successful']
    assert sha(E/'revision/SEAL-REVISION.json')=='5c853091994d882b8cb7e8cae06deaededa2748e042f7e225bd814e5a3cf2606'
    patch=subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'diff','--cached','--binary','--','.',':(exclude)evidence/s1-20261018/sesenta-tandas-533-592'],cwd=ROOT)
    assert b'SharedDeviceTemplates.cs' in patch and b'PLAN-SESENTA-TANDAS-533-592.json' in patch
    (E/'CAMBIOS.patch').write_bytes(patch)
    files=sorted((p for p in E.rglob('*') if p.is_file()),key=lambda p:p.relative_to(E).as_posix())
    lines=[sha(p)+'  '+p.relative_to(E).as_posix() for p in files]
    (E/'SHA256SUMS').write_bytes(('\n'.join(lines)+'\n').encode())
    assert all(sha(E/p)==h for h,p in [line.split('  ',1) for line in lines])
    print(json.dumps(dict(sealedFiles=len(files),sha256Sums=sha(E/'SHA256SUMS'),patchBytes=len(patch),published=False)))
if __name__=='__main__':main()
