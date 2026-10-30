"""Check/stage reviewed category-palette changes and seal their local evidence."""
import argparse
import base64
import json
from pathlib import Path
import subprocess
from close_category1089 import ROOT,E,GIT,PIN,guards,results,read,sha,write

def git(*args):return subprocess.check_output([str(GIT),*args],cwd=ROOT)

def checks():
 guards();results();assert read('VERIFICACION-FINAL.json')['successful']
 gate=read('revision/GATE-TECNICO.json');assert gate['targetManifestSha256']==PIN
 for key in ['sourceHashes','manualHashes']:assert all(sha(ROOT/p)==h for p,h in gate[key].items())
 assert all(sha(E/p)==h for p,h in gate['observedFilesSha256'].items())

def stage():
 paths=[p for p in git('ls-files','-m','-o','--exclude-standard','-z').decode().split('\0') if p]
 prefixes=['docs/','development/server/src/','development/server/tests/','development/server/database/',
  'development/frontend/src/','development/frontend/tests/','tools/tests/',E.relative_to(ROOT).as_posix()+'/']
 exact=['CHANGELOG.md','GUIA-QA-RESTAURADO.html','GUIA-QA-WASCAR.html','development/server/README.md','development/frontend/README.md']
 assert paths and all(p in exact or any(p.startswith(prefix) for prefix in prefixes) for p in paths)
 git('add','--',*paths)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true');parser.add_argument('--review-sha256');a=parser.parse_args()
 checks()
 if a.check_only:
  assert not (E/'DIFF-CHECK-RAW.json').exists();stage()
  check=subprocess.run([str(GIT),'diff','--cached','--check'],cwd=ROOT,capture_output=True)
  record=dict(exitCode=check.returncode,stdoutBase64=base64.b64encode(check.stdout).decode(),stderrBase64=base64.b64encode(check.stderr).decode())
  write(E/'DIFF-CHECK-RAW.json',record);assert check.returncode==0,record
  print('Git diff --cached --check: PASS');return
 assert a.review_sha256
 review=E/'revision/CIERRE-REVISADO.json';assert sha(review)==a.review_sha256
 approved=json.loads(review.read_bytes());assert approved['approved'] and approved['progress']==78 and not approved['finalAdoption']
 assert all(sha(ROOT/p)==h for p,h in approved['files'].items());stage()
 subprocess.run([str(GIT),'diff','--cached','--check'],cwd=ROOT,check=True,capture_output=True)
 patch=E/'CAMBIOS.patch'
 with patch.open('xb') as stream:stream.write(git('diff','--cached','--binary','--','.',':(exclude)evidence/**'))
 manifest=E/'SHA256SUMS';entries=[(sha(p),p.relative_to(E).as_posix()) for p in sorted(E.rglob('*')) if p.is_file() and p!=manifest]
 with manifest.open('x',encoding='utf-8',newline='\n') as stream:stream.write(''.join(h+'  '+p+'\n' for h,p in entries))
 git('add','--',E.relative_to(ROOT).as_posix())
 subprocess.run([str(GIT),'diff','--cached','--check','--','.',':(exclude)'+patch.relative_to(ROOT).as_posix()],cwd=ROOT,check=True,capture_output=True)
 print(json.dumps(dict(evidenceFiles=len(entries),manifestSha256=sha(manifest),publicDiffBytes=patch.stat().st_size,published=False)))

if __name__=='__main__':main()
