"""Record the authorized functional block before edits; keep existing QA/package intact."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-653-712'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    if (E/'INICIO.json').exists():raise SystemExit('Preserve initial evidence')
    previous=ROOT/'evidence/s1-20261018/sesenta-tandas-593-652';start=json.loads((previous/'INICIO.json').read_bytes())
    paths=set(start['guards'])
    paths.add('evidence/s1-20261018/sesenta-tandas-593-652/SHA256SUMS')
    frozen=json.loads((previous/'SOURCE-FREEZE-OPERATORS-03.json').read_bytes())['sources'];paths.update(frozen)
    paths.update(x['path'] for x in json.loads((previous/'PACKAGES-03.json').read_bytes())['outputs'])
    pointer=ROOT/'.local/qa-rc9/current.json';cfgdir=Path(json.loads(pointer.read_bytes())['directory'])
    paths.update(p.relative_to(ROOT).as_posix() for p in [cfgdir/'manual-qa.json',cfgdir/'lab.json']+[cfgdir/n for n in ['ACCESO-PRIVADO.txt','QA-CUENTAS-ESTADO.json','qa-accounts-private.json','RESTORE-ESTADO.json']])
    authorized=['development/server/src/RackClick.Server/Program.cs','development/server/src/RackClick.Server/SchemaMigrations.cs','development/server/src/RackClick.Server/RecoveryAdministrator.cs','development/frontend/src/ServerApp.jsx','docs/QA-CASOS-WASCAR.json','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html']
    E.mkdir(parents=True,exist_ok=True)
    data={'utc':datetime.now(timezone.utc).isoformat(),'baseCommit':subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'gitCleanAtFirstRead':True,'initialProgress':78,'scope':'Personal language and theme in PostgreSQL11, current RC9 controls reused. New isolated development fixtures; current selected QA592/schema10 and ZIP03 retained. Not a Windows11 installer profile or actual QA migration.','guards':{p:sha(ROOT/p) for p in sorted(paths)},'authorizedMutableGuards':authorized,'sourceQaDirectory':cfgdir.relative_to(ROOT).as_posix(),'sourceApplicationLoginPlanned':False,'sourceApplicationDmlPlanned':False,'actualQaSelectionPlanned':False,'manualWascarResultsWritten':False,'sql001_010Mutable':False,'toolchainVersionsMutable':False}
    (E/'INICIO.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');print(json.dumps({'guards':len(paths),'baseCommit':data['baseCommit'],'progress':78,'currentQaUnchangedPlanned':True}))
if __name__=='__main__':main()
