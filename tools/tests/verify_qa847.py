"""Regenerate guides and verify current snapshot availability without app login or notes."""
import importlib.util,json,sys,time,unittest
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/quince-tandas-833-847'
def main():
    out=E/'QA-TESTS-01.json';log=E/'QA-TESTS-01.log';assert not out.exists() and not log.exists()
    matrix=json.loads((E/'QA-MATRIX-847.json').read_bytes());assert matrix['detailedStepsAndExpectedUnchanged']
    spec=importlib.util.spec_from_file_location('guide_tests847',ROOT/'tools/tests/test_qa_guide.py');module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);guide=module.guide
    spec2=importlib.util.spec_from_file_location('excel_guide_tests847',ROOT/'tools/tests/test_rc9_excel_guide832.py');excel=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(excel)
    catalog=json.loads(guide.CATALOG.read_bytes())
    def cases(ctx):return json.loads(guide.render(catalog,ctx).split('const guide=',1)[1].split(';',1)[0])['cases']
    class Selected832Guide(unittest.TestCase):
        def test_current_profiles_and_exact_generated_guides(self):
            for profile,want in [('manual',8),('rc9',77)]:
                ctx=guide.context(profile=profile);meta=cases(ctx);self.assertEqual(sum(x['available'] for x in meta.values()),want)
                self.assertTrue(all(meta[f'QA-{i}']['available']==(profile=='rc9') for i in range(75,78)))
                self.assertTrue(guide.generate(check=True,profile=profile))
        def test_own_xls_gates_fail_closed_and_original_notes_logic_present(self):
            ctx=guide.context(profile='rc9')
            for delta in [dict(bundle='wrong'),dict(dll='wrong'),dict(roles=False),dict(configured=False),matrix['sourcePair']]:
                self.assertTrue(all(not cases({**ctx,**delta})[f'QA-{i}']['available'] for i in range(75,78)))
            html=guide.render(catalog,ctx);self.assertIn('records={...records,...accepted}',html);self.assertIn('conservar notas y volver a probar',html)
        def test_availability_intros_no_longer_name_obsolete_current_qa(self):
            changed=set(matrix['changedCases']);self.assertEqual(len(changed),6)
            for case in catalog['cases']:
                if case['id'] in changed:
                    self.assertIn('DISPONIBLE EN TU SNAPSHOT',case['steps'][0]);self.assertNotIn('QA185 actual',case['steps'][0]);self.assertNotIn('QA712 actual',case['steps'][0])
    for profile in ['manual','rc9']:assert guide.generate(profile=profile)
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(module),unittest.defaultTestLoader.loadTestsFromModule(excel),unittest.defaultTestLoader.loadTestsFromTestCase(Selected832Guide)]);started=time.monotonic()
    with log.open('x',encoding='utf-8') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    availability={p:sum(x['available'] for x in cases(guide.context(profile=p)).values()) for p in ['manual','rc9']}
    row=dict(utc=datetime.now(timezone.utc).isoformat(),testsRun=result.testsRun,successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),availability=availability,caseCount=77,guidesRegeneratedAndExact=all(guide.generate(check=True,profile=p) for p in ['manual','rc9']),actualQaApplicationOpened=False,manualWascarResultsWritten=False,scope='Guide metadata only; no app/PG/Edge/manual execution. Baseline normalization permits precisely three legacy availability intros.')
    out.write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8');print(json.dumps(row));return 0 if row['successful'] and availability==dict(manual=8,rc9=77) else 1
if __name__=='__main__':raise SystemExit(main())
