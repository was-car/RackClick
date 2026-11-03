"""Initial record for shared customer templates; never overwrites an existing record."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-533-592'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    if (E/'INICIO.json').exists():raise SystemExit('Preserve existing initial record')
    git=str(ROOT/'.local/git-2.55.0.5/cmd/git.exe')
    previous=ROOT/'evidence/s1-20261018/sesenta-tandas-473-532'
    initial=json.loads((previous/'INICIO.json').read_bytes());paths=set(initial['guards'])
    paths.update(['evidence/s1-20261018/sesenta-tandas-473-532/SHA256SUMS',
                  'evidence/s1-20261018/sesenta-tandas-473-532/CANDIDATA532-FINAL03.json',
                  '.local/qa-rc9/current.json'])
    m=json.loads((previous/'CANDIDATA532-FINAL03.json').read_bytes())
    for part,files in m['distributions'].items():
        paths.update(m['candidateDirectory']+'/'+part+'/'+p for p in files)
    pointer=json.loads((ROOT/'.local/qa-rc9/current.json').read_bytes())
    profile=Path(pointer['directory']);paths.add((profile/'manual-qa.json').relative_to(ROOT).as_posix())
    E.mkdir(parents=True,exist_ok=True)
    data=dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=subprocess.check_output([git,'rev-parse','HEAD'],cwd=ROOT,text=True).strip(),gitCleanAtFirstRead=True,
        initialProgress=77,scope='Customer-scoped immutable shared publications, separate from actor-private templates. Additive schema10 and new synthetic laboratories. Existing QA532 and ZIP532 remain selected and unmodified.',
        versions=dict(sdk='10.0.401',postgresql='17.11',node='24.21.0'),
        guards={p:sha(ROOT/p) for p in sorted(paths)},
        authorizedMutableGuards=['development/server/src/RackClick.Server/Program.cs','docs/QA-CASOS-WASCAR.json','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html'],
        actualQaApplicationAccessPlanned=False,actualQaArtifactSelectionPlanned=False,wascarResultsWritten=False)
    (E/'INICIO.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(baseCommit=data['baseCommit'],guards=len(paths),initialProgress=77,qaSelectionPlanned=False)))
if __name__=='__main__':main()
