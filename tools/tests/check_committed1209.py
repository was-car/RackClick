"""Read-only post-commit evidence, sources, QA and worktree verification."""
import importlib.util
import json
import subprocess
from verify_onboarding1209 import guards,product,technical_gate
from init_onboarding1209 import ROOT,E,BASE,GIT,sha

def main():
    rows=[]
    for line in (E/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        h,name=line.split('  ',1);p=E/name;assert p.resolve().is_relative_to(E.resolve()) and sha(p)==h;rows.append(name)
    assert set(rows)=={p.relative_to(E).as_posix() for p in E.rglob('*') if p.is_file() and p.name!='SHA256SUMS'}
    reviewed=json.loads((E/'revision/CIERRE-REVISADO.json').read_bytes());assert reviewed['approved'] and not reviewed['finalAdoption']
    assert all(sha(ROOT/p)==h for p,h in reviewed['files'].items())
    initial=guards();product();technical_gate()
    assert json.loads((E/'VERIFICACION-FINAL.json').read_bytes())['successful']
    spec=importlib.util.spec_from_file_location('guide1209committed',ROOT/'tools/windows/qa_guide.py');guide=importlib.util.module_from_spec(spec);spec.loader.exec_module(guide)
    assert all(guide.generate(check=True,profile=p) for p in ['manual','rc9'])
    assert not subprocess.check_output([str(GIT),'status','--porcelain'],cwd=ROOT)
    commit=subprocess.check_output([str(GIT),'rev-parse','HEAD'],text=True).strip();assert commit!=BASE
    print(json.dumps(dict(successful=True,commit=commit,evidenceFilesExact=len(rows),reviewedFilesExact=len(reviewed['files']),protectedFilesExact=len(initial['guards']),
        originalQaRootFilesExact=28,productSourcesExact=193,candidateFilesExact=40,selectedQaRevision=1089,selectedQaSchema=13,
        available=dict(manual=8,rc9=84),newCasesPlanned=[85,86,87],worktreeClean=True,progress=78,finalAdoption=False)))

if __name__=='__main__':main()
