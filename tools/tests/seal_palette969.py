"""Seal reviewed palette evidence and stage only this block's public files; never publish."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-910-969'
GIT=ROOT/'.local/git-2.55.0.5/cmd/git.exe'


def sha(p):
    with p.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def git(*args):
    return subprocess.check_output([str(GIT),*args],cwd=ROOT)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-sha256',required=True)
    args=parser.parse_args()
    review=E/'revision/CIERRE-REVISADO.json'
    assert sha(review)==args.review_sha256
    approved=json.loads(review.read_bytes())
    assert approved['approved'] and approved['progress']==78
    assert all(sha(ROOT/p)==h for p,h in approved['files'].items())
    assert json.loads((E/'VERIFICACION-FINAL.json').read_bytes())['successful']
    initial=json.loads((E/'INICIO.json').read_bytes())
    assert all(sha(ROOT/p)==h for p,h in initial['guards'].items())
    product=json.loads((E/'SOURCE-FREEZE-01.json').read_bytes())['sources']
    assert all(sha(ROOT/p)==h for p,h in product.items())
    paths=git('ls-files','-m','-o','--exclude-standard','-z').decode().split('\0')
    paths=[p for p in paths if p]
    prefixes=['docs/','development/frontend/src/','development/frontend/tests/','development/server/src/',
              'development/server/tests/','development/server/database/','tools/tests/',E.relative_to(ROOT).as_posix()+'/']
    exact=['CHANGELOG.md','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html','development/server/README.md','development/frontend/README.md']
    assert paths and all(p in exact or any(p.startswith(prefix) for prefix in prefixes) for p in paths)
    git('add','--',*paths)
    subprocess.run([str(GIT),'diff','--cached','--check'],cwd=ROOT,check=True,capture_output=True)
    patch=E/'CAMBIOS.patch'
    with patch.open('xb') as stream:
        stream.write(git('diff','--cached','--binary','--','.',':(exclude)evidence/**'))
    entries=[(sha(p),p.relative_to(E).as_posix()) for p in sorted(E.rglob('*')) if p.is_file() and p.name!='SHA256SUMS']
    manifest=E/'SHA256SUMS'
    with manifest.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(''.join(h+'  '+p+'\n' for h,p in entries))
    git('add','--',str(E.relative_to(ROOT)))
    subprocess.run([str(GIT),'diff','--cached','--check','--','.',':(exclude)**/CAMBIOS.patch'],cwd=ROOT,check=True,capture_output=True)
    print(json.dumps(dict(evidenceFiles=len(entries),manifestSha256=sha(manifest),publicDiffBytes=patch.stat().st_size,published=False)))


if __name__=='__main__':
    main()
