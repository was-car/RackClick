"""Seal reviewed local integration changes; never stage private laboratory files."""
import argparse,json,subprocess
from verify_integration1269 import ROOT,E,GIT,sha,read,protected_inputs,current_product,technical_gate,selected_qa,final_guide
def git(*args):return subprocess.check_output([str(GIT),*args],cwd=ROOT)
def public_paths():
 paths=[p for p in git('ls-files','-m','-o','--exclude-standard','-z').decode().split('\0') if p]
 prefixes=['docs/','development/server/tests/','tools/tests/','tools/windows/',E.relative_to(ROOT).as_posix()+'/'];allowed=['CHANGELOG.md','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html','development/server/README.md','development/frontend/README.md','tools/package_offline_bundle.py']
 assert paths and all(p in allowed or any(p.startswith(v) for v in prefixes) for p in paths);assert not any(p.startswith(('.local/','development/server/src/','development/frontend/src/')) for p in paths);return paths
def stage():
 paths=public_paths()
 for start in range(0,len(paths),50):git('add','--',*paths[start:start+50])
def main():
 p=argparse.ArgumentParser();p.add_argument('--review-sha256',required=True);args=p.parse_args();review=E/'revision/CIERRE-REVISADO.json';assert sha(review)==args.review_sha256
 approved=json.loads(review.read_bytes());assert approved['approved'] and approved['progress']==78 and not approved['finalAdoption'] and all(sha(ROOT/p)==h for p,h in approved['files'].items());assert read('VERIFICACION-FINAL.json')['successful']
 protected_inputs();current_product();technical_gate();selected_qa();final_guide();scope=read('DIFF-CHECK-ALCANCE.json');excluded=scope['excludedArtifacts']
 for p,h in excluded.items():assert p.startswith(E.relative_to(ROOT).as_posix()+'/') and p.endswith('.patch') and sha(ROOT/p)==h
 stage();excludes=[':(exclude)'+p for p in excluded]+[':(exclude)'+E.relative_to(ROOT).as_posix()+'/CAMBIOS.patch'];command=['diff','--cached','--check','--','.']+excludes;subprocess.run([str(GIT),*command],cwd=ROOT,capture_output=True,check=True)
 patch=E/'CAMBIOS.patch'
 with patch.open('xb') as f:f.write(git('diff','--cached','--binary','--','.',':(exclude)evidence/**'))
 entries=[(sha(p),p.relative_to(E).as_posix()) for p in sorted(E.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'];manifest=E/'SHA256SUMS'
 with manifest.open('x',encoding='utf-8',newline='\n') as f:f.write(''.join(h+'  '+n+'\n' for h,n in entries))
 git('add','--',E.relative_to(ROOT).as_posix());subprocess.run([str(GIT),*command],cwd=ROOT,capture_output=True,check=True);print(json.dumps(dict(evidenceFiles=len(entries),manifestSha256=sha(manifest),publicDiffBytes=patch.stat().st_size,published=False)))
if __name__=='__main__':main()
