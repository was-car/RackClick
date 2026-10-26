"""Focal follow-up for new QA93 route; preserve the earlier50-run as historical."""
import importlib.util,json,time,unittest
from block1449 import ROOT,E,sha,save
from qa_receipt1449 import CASES
s=importlib.util.spec_from_file_location('guide1449routes',ROOT/'tools/windows/qa_guide.py');guide=importlib.util.module_from_spec(s);s.loader.exec_module(guide)
class Routes1449(unittest.TestCase):
 def test_only_new_qa93_language_step_changes(self):
  old=json.loads((E/'qa-01-before-route-fix/QA-CASOS-WASCAR.json').read_bytes());now=json.loads((ROOT/'docs/QA-CASOS-WASCAR.json').read_bytes());expected=json.loads(json.dumps(old));expected['cases'][-1]['steps'][3]=CASES[-1]['steps'][3];self.assertEqual(now,expected);self.assertEqual(now['cases'][90:],CASES)
 def test_language_route_uses_home_and_new_receipt(self):
  step=CASES[-1]['steps'][3]
  for phrase in ['Todos los clientes','se pierde el recibo temporal','esquina superior derecha','Vuelve a Usuarios','crea otro grupo','No busques el selector de idioma dentro de Administración']:self.assertIn(phrase,step)
 def test_both_guides_current_and_same_availability(self):
  catalog=json.loads((ROOT/'docs/QA-CASOS-WASCAR.json').read_bytes())
  for profile,count in [('manual',8),('rc9',90)]:
   self.assertTrue(guide.generate(check=True,profile=profile));cases=json.loads(guide.render(catalog,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases'];self.assertEqual(sum(c['available'] for c in cases.values()),count);self.assertEqual([cases['QA-'+str(i)]['available'] for i in [91,92,93]],[False]*3)
def main():
 assert not (E/'QA-FOCO-RUTA-02.json').exists()
 for profile in ['manual','rc9']:guide.generate(profile=profile)
 start=time.monotonic()
 with (E/'QA-FOCO-RUTA-02.log').open('x',encoding='utf-8') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Routes1449))
 save('QA-FOCO-RUTA-02.json',dict(successful=r.wasSuccessful(),testsRun=r.testsRun,seconds=round(time.monotonic()-start,3),sourceHashes={p:sha(ROOT/p) for p in ['docs/QA-CASOS-WASCAR.json','tools/tests/qa_receipt1449.py','tools/tests/qa_receipt1449_routes.py','tools/windows/qa_guide.py','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html']},scope='Only new QA93 step3 corrected; other92 full cases and all gates exact. Original50 regression not rerun.',available=dict(manual=8,rc9=90),actualQaOperations=0,wascarResultsWritten=False));print(json.dumps(dict(successful=r.wasSuccessful(),testsRun=r.testsRun)));return 0 if r.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
