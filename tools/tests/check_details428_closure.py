"""Read-only closure verification, new result file; never runs against actual QA."""
import argparse,hashlib,importlib.util,json,platform,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/cuarenta-y-cinco-tandas-428-472'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    if a.output.exists():raise SystemExit('Refuse to overwrite verification evidence')
    checks={}
    def check(name,value):checks[name]=bool(value)
    start=read('INICIO.json');excluded={'docs/QA-CASOS-WASCAR.json','development/server/src/RackClick.Server/Program.cs','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html'}
    guards={p:h for p,h in start['guards'].items() if p not in excluded};check('163 immutable guards plus four explicitly authorized mutable guards',len(guards)==163 and all(sha(ROOT/p)==h for p,h in guards.items()))
    frozen=read('SOURCE-FREEZE-01.json')['sources'];check('148 frozen product sources and focal test sources',len(frozen)==148 and all(sha(ROOT/p)==h for p,h in frozen.items()))
    m=read('CANDIDATA472.json');distributions={part:{p.relative_to(ROOT/m['candidateDirectory']/part).as_posix():sha(p) for p in (ROOT/m['candidateDirectory']/part).rglob('*') if p.is_file()} for part in ['server','frontend']}
    check('36 candidate files and exact distributions',distributions==m['distributions'] and m['fileCount']==36 and sum(map(len,distributions.values()))==36)
    check('6723506 exact candidate bytes',m['totalBytes']==6723506 and sum(p.stat().st_size for part in ['server','frontend'] for p in (ROOT/m['candidateDirectory']/part).rglob('*') if p.is_file())==6723506)
    old=json.loads((ROOT/'evidence/s1-20261017/treinta-tandas-368-397/CANDIDATA397.json').read_text());check('nine SQL and 17 frontend assets unchanged',all(h==old['distributions']['server'][p] for p,h in distributions['server'].items() if p.startswith('database/')) and all(h==old['distributions']['frontend'][p] for p,h in distributions['frontend'].items() if p!='app.js'))
    pg=read('backend/postgres01/result.json');check('backend four native focuses pass, exact sources and stopped',pg['testsRun']==4 and all(pg[k] for k in ['successful','labStopped','serversStopped','inputsUnchanged','frontendUnchanged']))
    legacy=read('legacy01/result.json');check('legacy seven native regression cases pass and stopped',legacy['testsRun']==7 and all(legacy[k] for k in ['successful','labStopped','serversStopped','inputsUnchanged','immutableUnchanged']))
    check('legacy schema7 metadata explicitly attributed',legacy['schemaVersion']==7 and read('LEGACY-METADATA-NOTE.json')['labelIsHardcodedNotDatabaseObservation'] and m['schema']==9)
    gui=read('gui01/fixture.json');check('Edge real seven events, nine tables, restart and stopped',gui['result']=='PASS' and gui['inventoryAuditEvents']==7 and all(gui[k] for k in ['restartHistoricalPersistence','nineInventoryTablesExactlyUnchanged','labStopped','serversStopped','inputsUnchanged']))
    independent=read('revision/postgres01/result.json');check('independent own PG focus pass and stopped',independent['testsRun']==1 and all(independent[k] for k in ['successful','labStopped','serversStopped','sourceInputsUnchanged','candidateInputsUnchanged']))
    current=json.loads((ROOT/'docs/QA-CASOS-WASCAR.json').read_text());prior=json.loads(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'show',start['baseCommit']+':docs/QA-CASOS-WASCAR.json'],cwd=ROOT));check('62 previous QA definitions intact and 65 total',current['cases'][:62]==prior['cases'] and len(current['cases'])==65)
    pair={'bundle':distributions['frontend']['app.js'],'dll':distributions['server']['RackClick.Server.dll']};check('future details feature pair exact',current['inventoryChangeDetailsBuilds']==[pair])
    spec=importlib.util.spec_from_file_location('guide',ROOT/'tools/windows/qa_guide.py');guide=importlib.util.module_from_spec(spec);spec.loader.exec_module(guide)
    for profile,count in [('manual',8),('rc9',59)]:
        html=guide.render(current,guide.context(profile=profile));metadata=json.loads(html.split('const guide=',1)[1].split(';',1)[0]);check(profile+' guide generated exactly and availability unchanged',guide.guide_path(profile).read_text(encoding='utf-8')==html and sum(c['available'] for c in metadata['cases'].values())==count and all(not metadata['cases'][f'QA-{n}']['available'] for n in range(60,66)))
    plan=json.loads((ROOT/'docs/PLAN-CUARENTA-Y-CINCO-TANDAS-428-472.json').read_text());check('45 scoped milestones evidence exists',plan['completed']==45 and [b['id'] for b in plan['batches']]==list(range(428,473)) and all(b['status']=='verified' and (ROOT/b['evidence']).is_file() and (ROOT/b['independentEvidence']).is_file() for b in plan['batches']))
    mp=json.loads((ROOT/'docs/MAPA-ENTREGA.json').read_text());check('weighted global progress remains 76 not tests or count',mp['progress']==76 and sum(s['points'] for s in mp['streams'])==76 and sum(s['weight'] for s in mp['streams'])==100 and plan['finalProgress']==76)
    check('candidate not real QA selected',m['selectedInRealQaAtFreeze'] is False and start['qaMutationsPlanned'] is False and gui['realQaAccessed'] is False and pg['actualQaOpened'] is False and legacy['actualQaOpened'] is False and independent['realQaOpened'] is False)
    # Assembly build provenance is recorded without asserting unchanged binary bytes.
    old_domain=ROOT/old['candidateDirectory']/'server/RackClick.Domain.dll';new_domain=ROOT/m['candidateDirectory']/'server/RackClick.Domain.dll'
    build_provenance={'oldContains397SourceRevision':old['baseCommit'].encode() in old_domain.read_bytes(),'newContains472SourceRevision':start['baseCommit'].encode() in new_domain.read_bytes(),'domainSourceChangedInWorkingTree':bool(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'diff','--name-only','--','development/server/src/RackClick.Domain'],cwd=ROOT).strip())}
    check('Domain assembly revision recorded and source unchanged',all(build_provenance[k] for k in ['oldContains397SourceRevision','newContains472SourceRevision']) and not build_provenance['domainSourceChangedInWorkingTree'])
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'checks':checks,'passed':sum(checks.values()),'total':len(checks),'domainBuildProvenance':build_provenance,'result':'PASS' if all(checks.values()) else 'FAIL','scope':'Read-only metadata/sha checks; no new PG, browser, install or Wascar QA run.'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2));return 0 if all(checks.values()) else 1
if __name__=='__main__':raise SystemExit(main())
