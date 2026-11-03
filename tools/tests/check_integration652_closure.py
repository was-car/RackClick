"""Read-only final integrity/catalog checks; no new PG/app/Edge/manual QA run."""
import argparse,hashlib,importlib.util,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-593-652'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads((E/p).read_bytes())
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    if a.output.exists():raise SystemExit('Preserve existing final verification')
    checks={}
    def check(k,v):checks[k]=bool(v)
    start=read('INICIO.json');changed=[p for p,h in start['guards'].items() if sha(ROOT/p)!=h]
    allowed={'.local/qa-rc9/current.json','GUIA-QA-RESTAURADO.html','GUIA-QA-WASCAR.html','docs/QA-CASOS-WASCAR.json'}|{'tools/windows/'+n for n in ['New-RackClickLabInstance.ps1','New-RackClickPrivateDeployment.ps1','New-RackClickRecoveredInstance.ps1','RackClick.Instance.ps1','RackClick.Stage.ps1','Restore-RackClickPrivateDeployment.ps1','Stage-ServerDistribution.ps1','Start-RackClickLabInstance.ps1','Test-ServerDistribution.ps1','Test-StagedDistribution.ps1']}
    check('248 initial guards: exactly10 authorized operators, pointer, catalog and2guides changed',len(start['guards'])==248 and set(changed)==allowed)
    previous=ROOT/'evidence/s1-20261018/sesenta-tandas-533-592'
    sources=json.loads((previous/'SOURCE-FREEZE-APP-02.json').read_bytes())['sources']
    check('157 application and GUI sources unchanged, no new builds',len(sources)==157 and all(sha(ROOT/p)==h for p,h in sources.items()))
    for path,schema,count,total,pin in [
        ('evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json',10,37,6939574,'66426b3c4fdf8c75b8c1faae4572066754934000eb2567881d93407f4ae5e9f9'),
        ('evidence/s1-20261018/sesenta-tandas-473-532/CANDIDATA532-FINAL03.json',9,36,6794984,'c818294e27a40c94fe2ebf603709c94263820af1facca9a7d5c288cb70e8158e')]:
        p=ROOT/path;m=json.loads(p.read_bytes());home=ROOT/m['candidateDirectory']
        actual={part:{p.relative_to(home/part).as_posix():sha(p) for p in (home/part).rglob('*') if p.is_file()} for part in ['server','frontend']}
        check('Candidate'+str(schema)+' complete tree, hashes and byte totals immutable',sha(p)==pin and m['schema']==schema and m['fileCount']==count and m['totalBytes']==total and actual==m['distributions'] and sum(p.stat().st_size for part in actual for p in (home/part).rglob('*') if p.is_file())==total)
    freeze=read('SOURCE-FREEZE-OPERATORS-03.json')['sources']
    check('33 packaged source hashes exact',len(freeze)==33 and all(sha(ROOT/p)==h for p,h in freeze.items()))
    packages=read('PACKAGES-03.json')
    check('Two new ZIPs byte-identical, exact external hashes and sizes',packages['valid'] and packages['sourcesUnchanged'] and packages['byteIdentical'] and all(sha(ROOT/x['path'])==x['sha256'] and (ROOT/x['path']).stat().st_size==x['bytes'] for x in packages['outputs']) and packages['outputs'][0]['sha256']==packages['outputs'][1]['sha256'])
    report=json.loads((ROOT/packages['outputs'][0]['report']).read_bytes())
    check('Package10 contains1978 files,37app/25operators/4manuals, dependencies unchanged',report['valid'] and report['files']==1978 and report['versions']['schema']==10 and report['slices']['application']['files']==37 and report['slices']['operators']['files']==25 and report['slices']['manuals']['files']==4 and report['versions']['dotnetRuntime']=='10.0.12' and report['versions']['postgresql']=='17.11')
    gate=read('COORDINATOR-GO.json')
    check('Coordinator gates unchanged after approval',gate['valid'] and all(sha(ROOT/p)==h for p,h in gate['gates'].items()))
    technical=read('revision/GATE-TECNICO-02.json')
    check('Independent technical approval and source/manual pins exact',technical['valid'] and technical['approved'] and all(sha(ROOT/p)==h for p,h in technical['sourceHashes'].items()) and all(sha(ROOT/p)==h for p,h in technical['manualHashes'].items()))
    for name in ['REAL-QA-PREFLIGHT-01.json','REAL-QA-PREPARE-01.json','REAL-QA-ACTIVATE-01.json','REAL-QA-VALIDATE-01.json']:
        d=read(name);check(name+' valid/no actual application login or DML',d['valid'] and not d['sourceApplicationLogin'] and not d['sourceApplicationDml'] and not d['manualWascarResultsWritten'])
    pre=read('REAL-QA-PREFLIGHT-01.json');selection=read('REAL-QA-ACTIVATE-01.json');validation=read('REAL-QA-VALIDATE-01.json')
    source=ROOT/pre['sourceDirectory'];target=ROOT/selection['candidateDirectory']
    check('Original source all12 private/config/PG inputs exact',all(sha(source/p)==h for p,h in pre['sourceInputHashes'].items()) and sha(source/'manual-qa.json')==start['sourceQaConfigSha256'])
    check('Real selected10 new lab, source distinct, quiet static validated',selection['state']=='committed' and selection['selectedSchema']==10 and selection['leftRunning'] is False and validation['valid'] and not validation['databaseTestExecuted'] and source!=target and json.loads((ROOT/'.local/qa-rc9/current.json').read_bytes())=={'directory':str(target)})
    catalog=json.loads((ROOT/'docs/QA-CASOS-WASCAR.json').read_bytes())
    old=json.loads(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'show',start['baseCommit']+':docs/QA-CASOS-WASCAR.json'],cwd=ROOT))
    expected=json.loads(json.dumps(old['cases'],ensure_ascii=False))
    c67=next(x for x in expected if x['id']=='QA-67');c67['steps'][-2]=c67['steps'][-2].replace('la compartición/publicación sigue pendiente.','la publicación compartida se verifica por separado con QA-69–71; aquí comprueba que las privadas no se heredan.')
    for case,new in zip(expected[-3:],catalog['cases'][-3:]):case['steps'][0]=new['steps'][0]
    check('Only QA67 ownership clarification and QA69–71 availability introduction changed',catalog['cases']==expected and len(catalog['cases'])==71)
    spec=importlib.util.spec_from_file_location('guide',ROOT/'tools/windows/qa_guide.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
    for profile,want in [('manual',8),('rc9',71)]:
        html=q.render(catalog,q.context(profile=profile));metadata=json.loads(html.split('const guide=',1)[1].split(';',1)[0])['cases']
        check(profile+' guide exact, available'+str(want),q.guide_path(profile).read_text(encoding='utf-8')==html and sum(x['available'] for x in metadata.values())==want)
    ctx=q.context(profile='rc9')
    for delta in [{'bundle':'wrong'},{'dll':'wrong'},{'roles':False},{'configured':False}]:
        meta=json.loads(q.render(catalog,{**ctx,**delta}).split('const guide=',1)[1].split(';',1)[0])['cases']
        check('Shared QA fail closed '+str(delta),all(not meta[f'QA-{i}']['available'] for i in range(69,72)))
    check('Guide keeps user notes and warns of changed snapshot/case',all(s in q.render(catalog,ctx) for s in ['conservar notas y volver a probar','localStorage.getItem','records={...records,...accepted}']))
    plan=json.loads((ROOT/'docs/PLAN-SESENTA-TANDAS-593-652.json').read_bytes())
    check('60 milestones evidence and independent review recorded',plan['completed']==60 and [x['id'] for x in plan['batches']]==list(range(593,653)) and all(x['status']=='verified' and (ROOT/x['evidence']).is_file() and (ROOT/x['independentEvidence']).is_file() for x in plan['batches']))
    m=json.loads((ROOT/'docs/MAPA-ENTREGA.json').read_bytes());p=(ROOT/'docs/PROGRESO-GLOBAL.md').read_text(encoding='utf-8')
    check('Global78 unchanged; component weights/points and visible total coherent',m['progress']==plan['finalProgress']==78 and [x['points'] for x in m['streams']]==[18,22,14,14,9,1] and sum(x['weight'] for x in m['streams'])==100 and '| **Total** | **100** | **78** |' in p and catalog['globalProgressEstimate']==78)
    data={'utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'passed':sum(checks.values()),'total':len(checks),'result':'PASS' if all(checks.values()) else 'FAIL','changedAuthorizedGuards':changed,'immutableGuardCount':len(start['guards'])-len(changed),'scope':'Read-only integrity and metadata; no new app/PG/Edge/manual QA run.'}
    with a.output.open('x',encoding='utf-8') as f:json.dump(data,f,indent=2);f.write('\n')
    print(json.dumps({'result':data['result'],'passed':data['passed'],'total':data['total'],'failed':[k for k,v in checks.items() if not v]}));return 0 if all(checks.values()) else 1
if __name__=='__main__':raise SystemExit(main())
