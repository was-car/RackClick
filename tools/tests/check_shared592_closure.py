"""Final read-only consistency checks; no new application, browser or PostgreSQL tests."""
import argparse,hashlib,importlib.util,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-533-592'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads((E/p).read_bytes())
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    if a.output.exists():raise SystemExit('Preserve existing verification evidence')
    checks={}
    def check(k,v):checks[k]=bool(v)
    start=read('INICIO.json');allow=set(start['authorizedMutableGuards'])|{'development/server/src/RackClick.Server/RecoveryAdministrator.cs'}
    changed=[p for p,h in start['guards'].items() if sha(ROOT/p)!=h]
    check('209 initial guards: only five authorized changes and204 exact',len(start['guards'])==209 and set(changed)==allow)
    check('Recovery10 initial policy omission recorded without altering initial record',read('ALCANCE-RECOVERY-10.json')['initialRecordOverwritten'] is False)
    m=read('CANDIDATA592-FINAL02.json');old=read('CANDIDATA592.json')
    actual={part:{p.relative_to(ROOT/m['candidateDirectory']/part).as_posix():sha(p) for p in (ROOT/m['candidateDirectory']/part).rglob('*') if p.is_file()} for part in ['server','frontend']}
    check('FINAL02 closed37files/schema10/6939574bytes',m['schema']==10 and m['fileCount']==37 and actual==m['distributions'] and sum(map(len,actual.values()))==37 and m['totalBytes']==6939574
          and sum(p.stat().st_size for part in actual for p in (ROOT/m['candidateDirectory']/part).rglob('*') if p.is_file())==6939574
          and sha(E/'CANDIDATA592-FINAL02.json')=='66426b3c4fdf8c75b8c1faae4572066754934000eb2567881d93407f4ae5e9f9')
    check('All19server files identical to original592; only app.js delta',m['distributions']['server']==old['distributions']['server'] and [p for p,h in actual['frontend'].items() if h!=old['distributions']['frontend'][p]]==['app.js'])
    source=read('SOURCE-FREEZE-APP-02.json')['sources'];check('157 final product sources exact',len(source)==157 and all(sha(ROOT/p)==h for p,h in source.items()))
    baseline=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-473-532/CANDIDATA532-FINAL03.json').read_bytes())
    check('Historical SQL1-9 and17frontend non-app files exact',all(actual['server'][p]==h for p,h in baseline['distributions']['server'].items() if p.startswith('database/')) and all(actual['frontend'][p]==h for p,h in baseline['distributions']['frontend'].items() if p!='app.js'))
    for path,count in [('backend/postgres01/result.json',8),('revision/pg-own01/result.json',2),('legacy-private01/result.json',1)]:
        d=read(path);check(path+' native pass/stopped/isolated',d['testsRun']==count and all(d[k] for k in ['successful','labStopped','serversStopped']) and d.get('actualQaOpened',False) is False)
    for path in ['frontend/gui02/fixture.json','frontend/gui-notice03/fixture.json']:
        d=read(path);check(path+' Edge pass/restart/stopped',d['result']=='PASS' and all(d[k] for k in ['labStopped','serversStopped','inputsUnchanged','serverRestartPersistence']) and not d['realQaAccessed'])
    d=read('native-backup02/result.json');check('native database-only restore33exact, source preserved, no application recovery',d['successful'] and d['observations']['tableCount']==33 and d['observations']['restoreExact'] and d['observations']['originalSourceUnchanged'] and not d['applicationRecovered'] and not d['actualQaAccessed'] and all(d[k] for k in ['sourcesUnchanged','artifactsUnchanged','labStopped','serversStopped']))
    check('Original root backup failure retained and corrected harness source archived',not read('native-backup01/result.json')['successful'] and (E/'native-backup01/HARNESS.py').is_file())
    check('Functional GUI failure retained before successful focus',read('frontend/gui01/fixture.json')['result']!='PASS')
    review=read('revision/METADATOS-FINALES.json');check('Independent15file contrasts pass, no new app/QA run in metadata',review['successful'] and review['checkCount']==15 and not review['newApplicationTestsExecuted'] and not review['actualQaApplicationAccess'])
    catalog=json.loads((ROOT/'docs/QA-CASOS-WASCAR.json').read_bytes())
    previous=json.loads(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'show',start['baseCommit']+':docs/QA-CASOS-WASCAR.json'],cwd=ROOT))
    check('Prior68cases exactly preserved;71total/progress78',catalog['cases'][:68]==previous['cases'] and len(catalog['cases'])==71 and catalog['globalProgressEstimate']==78)
    spec=importlib.util.spec_from_file_location('q',ROOT/'tools/windows/qa_guide.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
    for profile,count in [('manual',8),('rc9',68)]:
        html=q.render(catalog,q.context(profile=profile));metadata=json.loads(html.split('const guide=',1)[1].split(';',1)[0])['cases']
        check(profile+' exact guide, prior availability and new cases disabled',q.guide_path(profile).read_text(encoding='utf-8')==html and sum(x['available'] for x in metadata.values())==count and all(not metadata[f'QA-{i}']['available'] for i in range(69,72)))
    plan=json.loads((ROOT/'docs/PLAN-SESENTA-TANDAS-533-592.json').read_bytes());check('60milestones evidence and independent report exist',plan['completed']==60 and [b['id'] for b in plan['batches']]==list(range(533,593)) and all(b['status']=='verified' and (ROOT/b['evidence']).is_file() and (ROOT/b['independentEvidence']).is_file() for b in plan['batches']))
    mp=json.loads((ROOT/'docs/MAPA-ENTREGA.json').read_bytes());p=(ROOT/'docs/PROGRESO-GLOBAL.md').read_text(encoding='utf-8')
    check('78scope points with unchanged weights and current prose table',mp['progress']==plan['finalProgress']==78 and [s['points'] for s in mp['streams']]==[18,22,14,14,9,1] and sum(s['weight'] for s in mp['streams'])==100 and '| **Total** | **100** | **78** |' in p and '| Jerarquía e inventario compartido | 25 | 22 |' in p)
    report=dict(utc=datetime.now(timezone.utc).isoformat(),checks=checks,passed=sum(checks.values()),total=len(checks),result='PASS' if all(checks.values()) else 'FAIL',
        authorizedMutableGuards=changed,immutableGuardCount=204,scope='Read-only files/metadata, not a new PG/Edge/application/manual QA run.')
    a.output.write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps(dict(result=report['result'],passed=report['passed'],total=report['total'],failed=[k for k,v in checks.items() if not v])))
    return 0 if all(checks.values()) else 1
if __name__=='__main__':raise SystemExit(main())
