"""Seal only reviewed public changes; exclude private candidate/lab content."""
import argparse
import json
import subprocess
from verify_onboarding1209 import guards,product,technical_gate
from init_onboarding1209 import ROOT,E,GIT,sha

def git(*args):return subprocess.check_output([str(GIT),*args],cwd=ROOT)
def public_paths():
    paths=[p for p in git('ls-files','-m','-o','--exclude-standard','-z').decode().split('\0') if p]
    prefixes=['docs/','tools/tests/','development/frontend/tests/','development/server/tests/',E.relative_to(ROOT).as_posix()+'/']
    exact=['CHANGELOG.md','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html','development/server/README.md','development/frontend/README.md',
        'development/frontend/src/AdminUsers.jsx','development/frontend/src/AdminUserOnboarding.jsx','development/frontend/src/admin-user-onboarding.ts','development/frontend/src/admin-user-onboarding-words.ts']
    assert paths and all(p in exact or any(p.startswith(prefix) for prefix in prefixes) for p in paths)
    return paths

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--review-sha256',required=True);args=parser.parse_args()
    review=E/'revision/CIERRE-REVISADO.json';assert sha(review)==args.review_sha256
    approved=json.loads(review.read_bytes());assert approved['approved'] and approved['progress']==78 and not approved['finalAdoption']
    assert all(sha(ROOT/p)==h for p,h in approved['files'].items())
    assert json.loads((E/'VERIFICACION-FINAL.json').read_bytes())['successful']
    assert json.loads((E/'DIFF-CHECK.json').read_bytes())['exitCode']==0
    guards();product();technical_gate();git('add','--',*public_paths())
    check=['diff','--cached','--check','--','.',':(exclude)'+E.relative_to(ROOT).as_posix()+'/CAMBIOS.patch']
    subprocess.run([str(GIT),*check],cwd=ROOT,check=True,capture_output=True)
    with (E/'CAMBIOS.patch').open('xb') as stream:stream.write(git('diff','--cached','--binary','--','.',':(exclude)evidence/**'))
    entries=[(sha(p),p.relative_to(E).as_posix()) for p in sorted(E.rglob('*')) if p.is_file() and p.name!='SHA256SUMS']
    with (E/'SHA256SUMS').open('x',encoding='utf-8',newline='\n') as stream:stream.write(''.join(h+'  '+p+'\n' for h,p in entries))
    git('add','--',E.relative_to(ROOT).as_posix());subprocess.run([str(GIT),*check],cwd=ROOT,check=True,capture_output=True)
    print(json.dumps(dict(evidenceFiles=len(entries),manifestSha256=sha(E/'SHA256SUMS'),published=False)))

if __name__=='__main__':main()
