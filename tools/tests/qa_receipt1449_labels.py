"""Correct exact new manual labels; preserve earlier regressions and user results."""
import importlib.util,json,re,time,unittest
from block1449 import ROOT,E,sha,save
PATCHES=[
 (90,2,'En Tipo de grupo elige Grupos de usuarios','En Tipo de grupo elige Grupo de usuarios'),
 (91,1,'En Membresías de usuarios, Membresías de clientes y Permisos de grupos de usuarios','En Membresía de grupos de usuarios, Clientes en grupos de clientes y Permisos de grupos de usuarios'),
 (91,2,'En Crear grupo elige Grupos de clientes','En Crear grupo elige Grupo de clientes'),
 (91,4,'Consultar original','Consultar resultado del grupo'),
 (91,4,'Reintentar original','Reintentar alta original'),
 (91,4,'Cancelar original','Cancelar alta de grupo pendiente'),
 (91,5,'Consultar original','Consultar resultado del grupo')]
s=importlib.util.spec_from_file_location('guide1449labels',ROOT/'tools/windows/qa_guide.py');guide=importlib.util.module_from_spec(s);s.loader.exec_module(guide)
def updated():
 x=json.loads((E/'qa-02-before-label-fix/QA-CASOS-WASCAR.json').read_bytes())
 for c,step,old,new in PATCHES:
  assert x['cases'][c]['steps'][step].count(old)==1;x['cases'][c]['steps'][step]=x['cases'][c]['steps'][step].replace(old,new)
 return x
class Labels1449(unittest.TestCase):
 def test_only_five_new_steps_changed(self):
  now=json.loads((ROOT/'docs/QA-CASOS-WASCAR.json').read_bytes());self.assertEqual(now,updated())
  from qa_receipt1449 import CASES
  self.assertEqual(now['cases'][90:],CASES)
 def test_actual_creation_and_panel_labels(self):
  now=updated();source=(ROOT/'development/frontend/src/AdminGroupCreation.jsx').read_text(encoding='utf-8').split('es: {',1)[1].split('\n};',1)[0];steps=' '.join(now['cases'][91]['steps'][4:6])
  for key in ['check','retry','cancel']:self.assertIn(re.search(key+r":'([^']+)'",source).group(1),steps)
  for path in ['AdminGroupMembers.jsx','AdminCustomerGroupMembers.jsx','AdminGrants.jsx']:
   raw=(ROOT/'development/frontend/src'/path).read_text(encoding='utf-8');label=re.search(r"es\s*:\s*\{\s*title\s*:\s*'([^']+)'",raw).group(1);self.assertIn(label,now['cases'][91]['steps'][1])
  self.assertIn('En Tipo de grupo elige Grupo de usuarios',now['cases'][90]['steps'][2]);self.assertIn('En Crear grupo elige Grupo de clientes',now['cases'][91]['steps'][2])
 def test_generated_guides_and_unavailability(self):
  catalog=updated()
  for profile,count in [('manual',8),('rc9',90)]:
   self.assertTrue(guide.generate(check=True,profile=profile));cases=json.loads(guide.render(catalog,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases'];self.assertEqual(sum(x['available'] for x in cases.values()),count);self.assertEqual([cases['QA-'+str(i)]['available'] for i in [91,92,93]],[False]*3)
def main():
 assert not (E/'QA-FOCO-ETIQUETAS-03.json').exists();d=E/'qa-02-before-label-fix';d.mkdir(exist_ok=True)
 names=['docs/QA-CASOS-WASCAR.json','tools/tests/qa_receipt1449.py','tools/tests/qa_receipt1449_routes.py','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html']
 for name in names:
  backup=d/ROOT.joinpath(name).name
  if backup.exists():assert backup.read_bytes()==(ROOT/name).read_bytes()
  else:backup.write_bytes((ROOT/name).read_bytes())
 expected=updated();p=ROOT/'tools/tests/qa_receipt1449.py';raw=p.read_text(encoding='utf-8')
 for old,new in dict((old,new) for c,step,old,new in PATCHES).items():
  assert old in raw;raw=raw.replace(old,new)
 p.write_bytes(raw.encode('utf-8'));p=ROOT/'docs/QA-CASOS-WASCAR.json';before=p.read_bytes();nl='\r\n' if b'\r\n' in before else '\n';p.write_bytes((json.dumps(expected,ensure_ascii=False,indent=2)+'\n').replace('\n',nl).encode('utf-8'))
 for profile in ['manual','rc9']:guide.generate(profile=profile)
 start=time.monotonic()
 with (E/'QA-FOCO-ETIQUETAS-03.log').open('x',encoding='utf-8') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Labels1449))
 save('QA-FOCO-ETIQUETAS-03.json',dict(successful=r.wasSuccessful(),testsRun=r.testsRun,seconds=round(time.monotonic()-start,3),sourceHashes={p:sha(ROOT/p) for p in ['docs/QA-CASOS-WASCAR.json','tools/tests/qa_receipt1449.py','tools/tests/qa_receipt1449_labels.py','tools/windows/qa_guide.py','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html']},scope='Only five steps of new QA91/92 exact labels corrected. Other91 full cases plus unchanged parts exact, all90 beforeblock intact;50 and prior3 route tests historical, not rerun.',available=dict(manual=8,rc9=90),actualQaOperations=0,wascarResultsWritten=False));print(json.dumps(dict(successful=r.wasSuccessful(),testsRun=r.testsRun)));return 0 if r.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
