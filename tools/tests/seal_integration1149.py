"""Seal reviewed public changes; no deployment, data or secret staging."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from verify_integration1149 import ROOT,E,GIT,protected_inputs,current_product,technical_gate

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def git(*args):return subprocess.check_output([str(GIT),*args],cwd=ROOT)

def public_paths():
    paths=[p for p in git('ls-files','-m','-o','--exclude-standard','-z').decode().split('\0') if p]
    prefixes=['docs/','development/server/tests/','tools/tests/','tools/windows/',E.relative_to(ROOT).as_posix()+'/']
    exact=['CHANGELOG.md','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html',
           'development/server/README.md','development/frontend/README.md','tools/package_offline_bundle.py']
    assert paths and all(p in exact or any(p.startswith(prefix) for prefix in prefixes) for p in paths)
    assert not any(p.startswith(('.local/','development/server/src/','development/frontend/src/')) for p in paths)
    return paths

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--review-sha256',required=True);args=parser.parse_args()
    review=E/'revision/CIERRE-REVISADO.json';assert sha(review)==args.review_sha256
    approved=json.loads(review.read_bytes());assert approved['approved'] and approved['progress']==78 and not approved['finalAdoption']
    assert all(sha(ROOT/p)==h for p,h in approved['files'].items())
    assert json.loads((E/'VERIFICACION-FINAL-02.json').read_bytes())['successful']
    focus=json.loads((E/'QA-FOCO-02.json').read_bytes());assert focus['successful'] and focus['testsRun']==3
    assert all(sha(ROOT/p)==h for p,h in focus['currentSourceHashes'].items())
    protected_inputs();current_product();technical_gate()
    scope=json.loads((E/'DIFF-CHECK-ALCANCE-02.json').read_bytes())
    excluded=scope['excludedArtifacts']
    for p,h in excluded.items():
        assert p.startswith(E.relative_to(ROOT).as_posix()+'/') and p.endswith('.patch') and sha(ROOT/p)==h
    git('add','--',*public_paths())
    excludes=[':(exclude)'+p for p in excluded]+[':(exclude)'+E.relative_to(ROOT).as_posix()+'/CAMBIOS.patch']
    args_check=['diff','--cached','--check','--','.']+excludes
    subprocess.run([str(GIT),*args_check],cwd=ROOT,check=True,capture_output=True)
    patch=E/'CAMBIOS.patch'
    with patch.open('xb') as stream:stream.write(git('diff','--cached','--binary','--','.',':(exclude)evidence/**'))
    entries=[(sha(p),p.relative_to(E).as_posix()) for p in sorted(E.rglob('*')) if p.is_file() and p.name!='SHA256SUMS']
    manifest=E/'SHA256SUMS'
    with manifest.open('x',encoding='utf-8',newline='\n') as stream:stream.write(''.join(h+'  '+p+'\n' for h,p in entries))
    git('add','--',E.relative_to(ROOT).as_posix())
    subprocess.run([str(GIT),*args_check],cwd=ROOT,check=True,capture_output=True)
    print(json.dumps(dict(evidenceFiles=len(entries),manifestSha256=sha(manifest),publicDiffBytes=patch.stat().st_size,published=False)))

if __name__=='__main__':main()
