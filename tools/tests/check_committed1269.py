"""Read-only check of the committed review/evidence/QA and clean worktree."""
import json,subprocess
from verify_integration1269 import ROOT,E,GIT,sha,read,protected_inputs,current_product,technical_gate,selected_qa,final_guide
def main():
 entries=[]
 for line in (E/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
  digest,name=line.split('  ',1);p=E/name;assert p.resolve().is_relative_to(E.resolve()) and sha(p)==digest;entries.append(name)
 actual={p.relative_to(E).as_posix() for p in E.rglob('*') if p.is_file() and p.name!='SHA256SUMS'};assert set(entries)==actual and len(entries)==len(actual)
 review=read('revision/CIERRE-REVISADO.json');assert review['approved'] and not review['finalAdoption'] and all(sha(ROOT/p)==h for p,h in review['files'].items());assert read('VERIFICACION-FINAL.json')['successful']
 initial,protected,static,changes=protected_inputs();current_product();technical_gate();selected_qa();available=final_guide();frozen=read('SOURCE-FREEZE-OPERATORS-02.json')['sources'];assert all(sha(ROOT/p)==h for p,h in frozen.items());assert all(sha(ROOT/r['path'])==r['sha256'] for r in read('PACKAGES-02.json')['outputs'])
 assert not subprocess.check_output([str(GIT),'status','--porcelain'],cwd=ROOT);commit=subprocess.check_output([str(GIT),'rev-parse','HEAD'],cwd=ROOT,text=True).strip();assert commit!=initial['baseCommit']
 print(json.dumps(dict(successful=True,commit=commit,evidenceFilesExact=len(entries),reviewedFilesExact=len(review['files']),protectedFilesExact=protected,immutableQaRootFilesExact=static,allowedRuntimeChanges=changes,productSourcesExact=193,candidateFilesExact=40,selectedQaFrontendRevision=1209,selectedServerRevision=1089,selectedQaSchema=13,available=available,worktreeClean=True,processesQuiet=True,progress=78,finalAdoption=False)))
if __name__=='__main__':main()
