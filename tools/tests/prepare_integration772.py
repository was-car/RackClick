"""Freeze starting identities before schema11 operational integration edits."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-713-772';E=ROOT/ER
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    if (E/'INICIO.json').exists():raise SystemExit('Preserve initial evidence')
    git=str(ROOT/'.local/git-2.55.0.5/cmd/git.exe')
    # This preparation file and its new contract/plan are the coordinator's only initial edits.
    status=subprocess.check_output([git,'status','--porcelain'],cwd=ROOT,text=True)
    assert all('prepare_integration772.py' in x or 'INTEGRACION-ESQUEMA11' in x for x in status.splitlines()),status
    previous=ROOT/'evidence/s1-20261018/sesenta-tandas-653-712'
    paths=set(json.loads((previous/'INICIO.json').read_bytes())['guards'])
    paths.update(json.loads((previous/'GUARDAS-QA-ADICIONALES.json').read_bytes())['guards'])
    paths.update(json.loads((previous/'SOURCE-FREEZE-APP-02.json').read_bytes())['sources'])
    paths.update(json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-593-652/SOURCE-FREEZE-OPERATORS-03.json').read_bytes())['sources'])
    paths.update([str((previous/'SHA256SUMS').relative_to(ROOT)).replace('\\','/'),'.local/qa-rc9/current.json'])
    E.mkdir(parents=True,exist_ok=True)
    mutable=['tools/package_offline_bundle.py','tools/windows/Test-ServerDistribution.ps1','tools/windows/RackClick.Stage.ps1','tools/windows/RackClick.OfflineBundle.ps1','tools/windows/Start-RackClickLabInstance.ps1','tools/windows/New-RackClickRecoveredInstance.ps1','docs/MANUAL-PAQUETE-WINDOWS-S1.md','docs/CONSTRUIR-PAQUETE-WINDOWS-S1.md','docs/OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md','docs/RECUPERACION-DESPLIEGUE-WINDOWS-S1.md','docs/QA-CASOS-WASCAR.json','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html','.local/qa-rc9/current.json']
    source=json.loads((ROOT/'.local/qa-rc9/current.json').read_bytes())['directory']
    data=dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=subprocess.check_output([git,'rev-parse','HEAD'],cwd=ROOT,text=True).strip(),initialProgress=78,gitCleanBeforePreparation=True,guards={p:sha(ROOT/p) for p in sorted(paths)},authorizedMutableGuards=mutable,sourceQaDirectory=Path(source).relative_to(ROOT).as_posix(),scope='Integrate closed candidate712/schema11 into Windows New/Restore and copy QA10 to a NEW independent lab; no source login/DML; actual selection only after package, fixture and independent gates.',applicationBuildsPlanned=0,frontendBuildsPlanned=0,manualWascarResultsWritten=False,finalAdoption=False)
    (E/'INICIO.json').write_bytes((json.dumps(data,indent=2)+'\n').encode())
    print(json.dumps(dict(guards=len(paths),baseCommit=data['baseCommit'],progress=78)))
if __name__=='__main__':main()
