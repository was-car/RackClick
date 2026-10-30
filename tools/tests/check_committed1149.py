"""Read-only check of committed evidence, selected lab, sources and worktree."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from verify_integration1149 import ROOT,E,GIT,sha,read,protected_inputs,current_product,technical_gate

def main():
    entries=[]
    for line in (E/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        digest,name=line.split('  ',1);path=E/name
        assert path.resolve().is_relative_to(E.resolve()) and sha(path)==digest;entries.append(name)
    actual={p.relative_to(E).as_posix() for p in E.rglob('*') if p.is_file() and p.name!='SHA256SUMS'}
    assert set(entries)==actual and len(entries)==len(actual)
    reviewed=read('revision/CIERRE-REVISADO.json');assert reviewed['approved'] and not reviewed['finalAdoption']
    assert all(sha(ROOT/p)==h for p,h in reviewed['files'].items())
    assert read('VERIFICACION-FINAL-02.json')['successful']
    focus=read('QA-FOCO-02.json');assert focus['successful'] and focus['testsRun']==3
    assert all(sha(ROOT/p)==h for p,h in focus['currentSourceHashes'].items())
    initial,protected,source_count,changes=protected_inputs();current_product();technical_gate()
    freeze=read('SOURCE-FREEZE-OPERATORS-01.json')['sources'];assert all(sha(ROOT/p)==h for p,h in freeze.items())
    package=read('PACKAGES-01.json');assert all(sha(ROOT/r['path'])==r['sha256'] for r in package['outputs'])
    activation=read('REAL-QA-ACTIVATE-01.json');assert activation['state']=='committed'
    assert sha(ROOT/'.local/qa-rc9/current.json')==activation['pointerSha256']
    sys.path.insert(0,str(ROOT/'tools/windows'))
    from qa_category_colors13_switch1149 import OwnedRuntime
    for name in ['sourceDirectory','candidateDirectory']:
        directory=ROOT/read('REAL-QA-PREPARE-01.json')[name]
        OwnedRuntime(directory,json.loads((directory/'manual-qa.json').read_bytes())).quiet()
    spec=importlib.util.spec_from_file_location('guide1149committed',ROOT/'tools/windows/qa_guide.py')
    guide=importlib.util.module_from_spec(spec);spec.loader.exec_module(guide)
    assert all(guide.generate(check=True,profile=p) for p in ['manual','rc9'])
    assert not subprocess.check_output([str(GIT),'status','--porcelain'],cwd=ROOT)
    commit=subprocess.check_output([str(GIT),'rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert commit!=initial['baseCommit']
    print(json.dumps(dict(successful=True,commit=commit,evidenceFilesExact=len(entries),reviewedFilesExact=len(reviewed['files']),
        protectedFilesExact=protected,immutableSourceQaRootFilesExact=source_count,allowedRuntimeChanges=changes,
        productSourcesExact=190,candidateFilesExact=40,selectedQaRevision=1089,selectedQaSchema=13,
        available=dict(manual=8,rc9=84),worktreeClean=True,processesQuiet=True,progress=78,finalAdoption=False)))

if __name__=='__main__':main()
