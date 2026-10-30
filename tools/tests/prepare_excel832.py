"""Record the immutable starting state before the RC9 XLS HTML feature edits."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-773-832'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    if (E/'INICIO.json').exists():raise SystemExit('Preserve initial evidence')
    git=str(ROOT/'.local/git-2.55.0.5/cmd/git.exe');status=subprocess.check_output([git,'status','--porcelain'],cwd=ROOT,text=True)
    assert all('prepare_excel832.py' in x for x in status.splitlines()),status
    prior=ROOT/'evidence/s1-20261018/sesenta-tandas-713-772';paths=set(json.loads((prior/'INICIO.json').read_bytes())['guards'])
    paths.update(json.loads((prior/'SOURCE-FREEZE-OPERATORS-02.json').read_bytes())['sources']);paths.add((prior/'SHA256SUMS').relative_to(ROOT).as_posix())
    paths.update(x['path'] for x in json.loads((prior/'PACKAGES-02.json').read_bytes())['outputs'])
    current=Path(json.loads((ROOT/'.local/qa-rc9/current.json').read_bytes())['directory'])
    qa_files=[p for part in ['server','frontend'] for p in (current/part).rglob('*') if p.is_file()]
    qa_files += [current/n for n in ['manual-qa.json','lab.json','ACCESO-PRIVADO.txt','QA-CUENTAS-ESTADO.json','qa-accounts-private.json','RESTORE-ESTADO.json','admin.pgpass','init-password.txt','schema11-prepared.json','schema11-prepared.sha256']]
    qa_files += [p for d in current.glob('rc_*') if d.is_dir() for p in d.iterdir() if p.is_file() and p.name in ['credentials.json','owner.pgpass']]
    qaguards={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(qa_files)};paths.update(qaguards)
    mutable=['development/server/src/RackClick.Server/Program.cs','development/server/src/RackClick.Server/OpenApiDocument.cs','development/server/src/RackClick.Server/PostgresStore.cs','development/frontend/src/InventoryPanel.jsx','docs/QA-CASOS-WASCAR.json','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html']
    E.mkdir(parents=True,exist_ok=True)
    data=dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=subprocess.check_output([git,'rev-parse','HEAD'],cwd=ROOT,text=True).strip(),initialProgress=78,gitCleanBeforePreparation=True,scope='RC9 three-table XLS HTML rack report, new closed API/GUI and Windows/PostgreSQL/Edge/Office validation. No new SQL/dependency. Current QA712/schema11 and ZIP772 retained; no actual QA application access, selection or manual results.',guards={p:sha(ROOT/p) for p in sorted(paths)},currentQaGuards=qaguards,authorizedMutableGuards=mutable,currentQaDirectory=current.relative_to(ROOT).as_posix(),actualQaLoginPlanned=False,actualQaDmlPlanned=False,actualQaSelectionPlanned=False,manualWascarResultsWritten=False,sql001_011Mutable=False,toolchainVersionsMutable=False)
    (E/'INICIO.json').write_bytes((json.dumps(data,indent=2)+'\n').encode());print(json.dumps(dict(guards=len(paths),qaGuards=len(qaguards),baseCommit=data['baseCommit'],progress=78)))
if __name__=='__main__':main()
