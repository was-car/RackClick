"""Seal only this block's evidence and staged non-evidence diff; preserve old seals."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-593-652'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    for name in ['CAMBIOS.patch','SHA256SUMS']:
        if (E/name).exists():raise SystemExit('Preserve existing final seal')
    assert json.loads((E/'VERIFICACION-FINAL02.json').read_bytes())['result']=='PASS'
    assert json.loads((E/'revision/METADATOS-FINALES.json').read_bytes())['valid']
    assert json.loads((E/'revision/GATE-TECNICO-02.json').read_bytes())['approved']
    patch=subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'diff','--cached','--binary','--','.',':(exclude)evidence/s1-20261018/sesenta-tandas-593-652'],cwd=ROOT)
    assert b'PLAN-SESENTA-TANDAS-593-652.json' in patch and b'qa_schema10_candidate652.py' in patch and b'package_offline_bundle.py' in patch
    (E/'CAMBIOS.patch').write_bytes(patch)
    files=sorted((p for p in E.rglob('*') if p.is_file()),key=lambda p:p.relative_to(E).as_posix())
    lines=[sha(p)+'  '+p.relative_to(E).as_posix() for p in files]
    (E/'SHA256SUMS').write_bytes(('\n'.join(lines)+'\n').encode())
    assert all(sha(E/p)==h for h,p in [line.split('  ',1) for line in lines])
    print(json.dumps({'sealedFiles':len(files),'sha256Sums':sha(E/'SHA256SUMS'),'patchBytes':len(patch),'published':False}))
if __name__=='__main__':main()
