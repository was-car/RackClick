"""Freeze current QA, released inputs and historical evidence before integration edits."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/quince-tandas-833-847'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    assert not (E/'INICIO.json').exists()
    git=str(ROOT/'.local/git-2.55.0.5/cmd/git.exe');status=subprocess.check_output([git,'status','--porcelain'],cwd=ROOT,text=True)
    assert all('prepare_integration847.py' in x for x in status.splitlines()),status
    prior=ROOT/'evidence/s1-20261018/sesenta-tandas-773-832';start=json.loads((prior/'INICIO.json').read_bytes())
    paths=set(start['guards']);paths.update(start['currentQaGuards']);paths.update(json.loads((prior/'SOURCE-FREEZE-APP-02.json').read_bytes())['sources'])
    paths.update(p.relative_to(ROOT).as_posix() for p in prior.rglob('*') if p.is_file())
    operators=ROOT/'evidence/s1-20261018/sesenta-tandas-713-772/SOURCE-FREEZE-OPERATORS-02.json';paths.update(json.loads(operators.read_bytes())['sources'])
    paths.add('.local/qa-rc9/current.json');paths.add('docs/QA-CASOS-WASCAR.json')
    current=Path(json.loads((ROOT/'.local/qa-rc9/current.json').read_bytes())['directory'])
    mutable=['tools/package_offline_bundle.py','tools/windows/Test-ServerDistribution.ps1','tools/windows/RackClick.Stage.ps1','tools/windows/RackClick.OfflineBundle.ps1','tools/windows/Start-RackClickLabInstance.ps1','tools/windows/New-RackClickRecoveredInstance.ps1','docs/MANUAL-PAQUETE-WINDOWS-S1.md','docs/CONSTRUIR-PAQUETE-WINDOWS-S1.md','docs/OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md','docs/RECUPERACION-DESPLIEGUE-WINDOWS-S1.md','docs/QA-CASOS-WASCAR.json','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html','.local/qa-rc9/current.json']
    E.mkdir(parents=True,exist_ok=True)
    data=dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=subprocess.check_output([git,'rev-parse','HEAD'],cwd=ROOT,text=True).strip(),initialProgress=78,gitCleanBeforePreparation=True,guards={p:sha(ROOT/p) for p in sorted(paths)},currentQaGuards=start['currentQaGuards'],authorizedMutableGuards=mutable,sourceQaDirectory=current.relative_to(ROOT).as_posix(),candidateManifest='evidence/s1-20261018/sesenta-tandas-773-832/CANDIDATA832-02.json',candidateManifestSha256='511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5',schema=11,scope='Closed Windows profile832, reproducible package and conservative same-schema QA copy; old QA712/schema11 preserved. No application builds or schema/version changes. Actual selection only after native isolated tests and independent review; source active/uncertain means no selection.',applicationBuildsPlanned=0,frontendBuildsPlanned=0,sourceAppLoginPlanned=False,sourceAppDmlPlanned=False,manualWascarResultsWritten=False,finalAdoption=False)
    (E/'INICIO.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(guards=len(paths),qaGuards=len(start['currentQaGuards']),baseCommit=data['baseCommit'],progress=78)))
if __name__=='__main__':main()
