"""Regenerate both guides and run guide tests once after actual QA11 selection."""
import importlib.util,json,sys,time,unittest
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-713-772'
def main():
    receipt=E/'QA-TESTS-01.json';log=E/'QA-TESTS-01.log'
    if receipt.exists() or log.exists():raise SystemExit('Preserve existing guide evidence')
    matrix=json.loads((E/'QA-MATRIX-772.json').read_bytes());assert matrix['previous71Exact']
    spec=importlib.util.spec_from_file_location('guide_tests772',ROOT/'tools/tests/test_qa_guide.py');module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);guide=module.guide
    catalog=json.loads(guide.CATALOG.read_bytes())
    def cases(ctx):return json.loads(guide.render(catalog,ctx).split('const guide=',1)[1].split(';',1)[0])['cases']
    class QA11Guide(unittest.TestCase):
        def test_current_profiles_exact_and_new_preferences_available(self):
            for profile,want in [('manual',8),('rc9',74)]:
                meta=cases(guide.context(profile=profile));self.assertEqual(sum(x['available'] for x in meta.values()),want)
                self.assertTrue(all(meta[f'QA-{i}']['available']==(profile=='rc9') for i in range(72,75)))
                self.assertTrue(guide.generate(check=True,profile=profile))
        def test_preference_and_inherited_gates_fail_closed(self):
            ctx=guide.context(profile='rc9')
            for delta in [dict(bundle='wrong'),dict(dll='wrong'),dict(roles=False),dict(configured=False)]:
                self.assertTrue(all(not cases({**ctx,**delta})[f'QA-{i}']['available'] for i in range(72,75)))
            self.assertTrue(all(not cases({**ctx,**matrix['sourcePair']})[f'QA-{i}']['available'] for i in range(72,75)))
        def test_changed_instructions_only_availability_intros(self):
            self.assertEqual(len(catalog['cases']),74)
            for c in catalog['cases'][-3:]:
                self.assertIn('DISPONIBLE EN TU SNAPSHOT',c['steps'][0]);self.assertNotIn('todavía NO ESTÁ',c['steps'][0]);self.assertGreaterEqual(len(c['steps']),8)
            html=guide.render(catalog,guide.context(profile='rc9'));self.assertIn('records={...records,...accepted}',html);self.assertIn('conservar notas y volver a probar',html)
    for profile in ['manual','rc9']:assert guide.generate(profile=profile)
    started=time.monotonic();suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(module),unittest.defaultTestLoader.loadTestsFromTestCase(QA11Guide)])
    with log.open('x',encoding='utf-8') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    availability={p:sum(x['available'] for x in cases(guide.context(profile=p)).values()) for p in ['manual','rc9']}
    row=dict(utc=datetime.now(timezone.utc).isoformat(),testsRun=result.testsRun,successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),availability=availability,caseCount=74,guidesRegeneratedAndExact=all(guide.generate(check=True,profile=p) for p in ['manual','rc9']),actualQaApplicationOpened=False,manualWascarResultsWritten=False,scope='Guide metadata only, no app/PG/Edge/manual QA run')
    receipt.write_bytes((json.dumps(row,indent=2)+'\n').encode());print(json.dumps(row));return 0 if row['successful'] and availability==dict(manual=8,rc9=74) else 1
if __name__=='__main__':raise SystemExit(main())
