"""Pin the final layout pair, regenerate current guides, and verify closed availability."""
import hashlib,importlib.util,json,subprocess,sys,time,unittest
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-653-712'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    for name in ['QA-PAIR-FINAL02.json','QA-TESTS-01.json','QA-TESTS-01.log']:
        if (E/name).exists():raise SystemExit('Preserve previous QA evidence')
    old=json.loads((E/'CANDIDATA712.json').read_bytes());m=json.loads((E/'CANDIDATA712-FINAL02.json').read_bytes())
    assert old['distributions']['server']==m['distributions']['server']
    assert [p for p,h in m['distributions']['frontend'].items() if old['distributions']['frontend'][p]!=h]==['app.js']
    pair={'bundle':m['distributions']['frontend']['app.js'],'dll':m['distributions']['server']['RackClick.Server.dll']}
    path=ROOT/'docs/QA-CASOS-WASCAR.json';c=json.loads(path.read_bytes());before=c['userPreferencesBuilds']
    assert before==[json.loads((E/'QA-MATRIX-712.json').read_bytes())['candidatePair']]
    c['userPreferencesBuilds']=[pair];path.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (E/'QA-PAIR-FINAL02.json').write_text(json.dumps({'before':before,'after':[pair],'purpose':'Only final visual class pair replaces provisional development pair; case definitions unchanged','finalManifestSha256':sha(E/'CANDIDATA712-FINAL02.json'),'realQaSelectedSchema':10,'newCasesAvailableInCurrentQa':False,'manualWascarResultsWritten':False},indent=2)+'\n',encoding='utf-8')
    test=ROOT/'tools/tests/test_qa_guide.py';data=test.read_bytes();old_ids=b"'QA-69','QA-70','QA-71'))";new_ids=b"'QA-69','QA-70','QA-71','QA-72','QA-73','QA-74'))"
    assert data.count(old_ids)==2;test.write_bytes(data.replace(old_ids,new_ids))
    spec=importlib.util.spec_from_file_location('guide_test712',test);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);guide=module.guide
    baseline=json.loads(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'show',json.loads((E/'INICIO.json').read_bytes())['baseCommit']+':docs/QA-CASOS-WASCAR.json'],cwd=ROOT))
    def cases(ctx,catalog=c):return json.loads(guide.render(catalog,ctx).split('const guide=',1)[1].split(';',1)[0])['cases']
    class CurrentPreferencesQa(unittest.TestCase):
        def test_previous71_exact_and_new3_detailed_but_not_in_retained_qa(self):
            self.assertEqual(c['cases'][:71],baseline['cases']);self.assertEqual(len(c['cases']),74)
            for profile,want in [('manual',8),('rc9',71)]:
                result=cases(guide.context(profile=profile));self.assertEqual(sum(x['available'] for x in result.values()),want)
                self.assertTrue(all(not result[f'QA-{i}']['available'] for i in range(72,75)))
            for case in c['cases'][-3:]:self.assertGreaterEqual(len(case['steps']),8);self.assertIn('NO ESTÁ DISPONIBLE',case['steps'][0]);self.assertIn('Pass',case['steps'][-1])
        def test_exact_pair_configured_and_role_fixture_gates(self):
            ctx=dict(configured=True,roles=True,restored=True,origin='',**pair)
            self.assertTrue(all(cases(ctx)[f'QA-{i}']['available'] for i in range(72,75)))
            for delta in [{'bundle':'wrong'},{'dll':'wrong'},{'roles':False},{'configured':False}]:
                self.assertTrue(all(not cases({**ctx,**delta})[f'QA-{i}']['available'] for i in range(72,75)))
        def test_no_fallback_from_unrelated_feature_or_provisional_pair(self):
            ctx=dict(configured=True,roles=True,restored=True,origin='',**before[0]);self.assertTrue(all(not cases(ctx)[f'QA-{i}']['available'] for i in range(72,75)))
            missing=dict(c);missing.pop('userPreferencesBuilds');self.assertTrue(all(not cases(dict(configured=True,roles=True,restored=True,origin='',**pair),missing)[f'QA-{i}']['available'] for i in range(72,75)))
    for profile in ['manual','rc9']:assert guide.generate(profile=profile)
    started=time.monotonic();suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(module),unittest.defaultTestLoader.loadTestsFromTestCase(CurrentPreferencesQa)])
    with (E/'QA-TESTS-01.log').open('x',encoding='utf-8') as output:result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    exact=all(guide.generate(check=True,profile=p) for p in ['manual','rc9'])
    data={'utc':datetime.now(timezone.utc).isoformat(),'testsRun':result.testsRun,'successful':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'seconds':round(time.monotonic()-started,3),'guidesRegeneratedAndExact':exact,'availability':{'manual':8,'rc9':71},'caseCount':74,'newCasesAvailableInCurrentQa':False,'previous71CasesExact':True,'actualQaApplicationOpened':False,'manualWascarResultsWritten':False,'scope':'Guide unit/metadata only; no HTTP/SQL/Edge/manual QA against current lab.'}
    (E/'QA-TESTS-01.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');print(json.dumps(data));return 0 if result.wasSuccessful() and exact else 1
if __name__=='__main__':main()
