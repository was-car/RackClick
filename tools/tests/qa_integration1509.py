"""Enable only reviewed receipt cases after the real artifact-only QA selection."""
import argparse,copy,importlib.util,json,subprocess,time,unittest
from pathlib import Path
from integration1509 import ROOT,E,ER,BASE,GIT,TARGET,PIN,sha,save,read
FEATURE='adminGroupReceiptGui';BUILDS='adminGroupReceiptBuilds'
ANCHOR=b"        'adminGroupRelationLinksGui': catalog.get('adminGroupRelationLinksBuilds', []),"
MAPPING=b"        'adminGroupReceiptGui': catalog.get('adminGroupReceiptBuilds', []),"
HELPERS=['tools/tests/test_qa_relations_status848.py','tools/tests/qa_port_colors969.py','tools/tests/qa_category_colors1089.py']
def expected_helper(raw,path):
 old=b"('rc9', 90)" if path.endswith('test_qa_relations_status848.py') else b"('rc9',90)";new=b"('rc9', 93)" if path.endswith('test_qa_relations_status848.py') else b"('rc9',93)";assert raw.count(old)==1;value=raw.replace(old,new)
 if path.endswith('test_qa_relations_status848.py'):return value
 lines=value.splitlines(keepends=True);count=0
 for i,line in enumerate(lines):
  if b"self.assertEqual((ROOT/'tools/windows/qa_guide.py').read_bytes()," not in line:continue
  ending=b'\r\n' if line.endswith(b'\r\n') else b'\n';body=line[:-len(ending)];assert body.endswith(b'))');nl=b'newline' if b'+newline+' in body else b'nl';extra=b'.replace('+repr(ANCHOR).encode('ascii')+b','+repr(ANCHOR).encode('ascii')+b'+'+nl+b'+'+repr(MAPPING).encode('ascii')+b')';lines[i]=body[:-1]+extra+b')'+ending;count+=1
 assert count==1;return b''.join(lines)
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def enable():
 actual=read(E/'REAL-QA-UPDATE-01.json');validated=read(E/'REAL-QA-VALIDATE-01.json');assert actual['valid'] and actual['state']=='committed' and validated['valid'] and validated['selectedRevision']==1449
 path=ROOT/'docs/QA-CASOS-WASCAR.json';before=path.read_bytes();original=json.loads(before);catalog=copy.deepcopy(original);assert len(catalog['cases'])==93 and BUILDS not in catalog
 m=read(ROOT/TARGET);assert sha(ROOT/TARGET)==PIN;old=read(ROOT/'evidence/s1-20261018/sesenta-tandas-1270-1329/CANDIDATA1329-01.json');pair=lambda x:dict(bundle=x['distributions']['frontend']['app.js'],dll=x['distributions']['server']['RackClick.Server.dll']);new,previous=pair(m),pair(old)
 directory=Path(read(ROOT/'.local/qa-rc9/current.json')['directory']);assert directory==(ROOT/actual['directory']).resolve();cfg=read(directory/'manual-qa.json');assert cfg['bundleSha256']==new['bundle'] and cfg['dllSha256']==new['dll']
 saved=E/'qa-guide/source-before';saved.mkdir(parents=True,exist_ok=False)
 for p in ['docs/QA-CASOS-WASCAR.json','tools/windows/qa_guide.py']+HELPERS:(saved/Path(p).name).write_bytes((ROOT/p).read_bytes())
 inherited=[]
 for key,values in catalog.items():
  if key.endswith('Builds') and isinstance(values,list) and previous in values and new not in values:
   assert all(isinstance(v,dict) and set(v)=={'bundle','dll'} for v in values);values.append(new);inherited.append(key)
 catalog[BUILDS]=[new];intros=[
 'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Interfaz1449/esquema13 seleccionada sobre el mismo laboratorio; datos y resultados conservados. INICIAR-QA-RESTAURADO.cmd abre guía y credenciales privadas. Elige Español desde Todos los clientes antes de entrar en Usuarios y usa Ctrl+F5.',
 'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Ambos tipos de grupo usan UUID confirmado. Mantén los borradores sin guardar; usa Consultar resultado del grupo para una intención pendiente. No alteres bases ni la última cuenta administradora.',
 'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Continúa con el UUID confirmado. El idioma se cambia desde Todos los clientes; salir de Administración retira el recibo temporal. Voz sin lector habitual se registra Bloqueada, sin reemplazar resultados anteriores.'
 ]
 for case,intro in zip(catalog['cases'][90:],intros):assert case['feature']=='planned';case['feature']=FEATURE;case['steps'][0]=intro
 assert catalog['cases'][:90]==original['cases'][:90];catalog['revision']='2026-10-18-bloque1450-1509';nl='\r\n' if b'\r\n' in before else '\n';path.write_bytes((json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').replace('\n',nl).encode('utf-8'))
 generator=ROOT/'tools/windows/qa_guide.py';raw=generator.read_bytes();assert raw.count(ANCHOR)==1 and MAPPING not in raw;generator.write_bytes(raw.replace(ANCHOR,ANCHOR+(b'\r\n' if b'\r\n' in raw else b'\n')+MAPPING))
 for name in HELPERS:
  p=ROOT/name;p.write_bytes(expected_helper(p.read_bytes(),name))
 save('QA-MATRIX-1509.json',dict(sourcePair=previous,pair=new,inheritedBuildLists=inherited,caseCount=93,unchangedCompleteCases=90,changedCases=['QA-91','QA-92','QA-93'],changedFields=['feature','steps[0]'],otherStepsAndExpectedUnchanged=True,beforeCatalogSha256=sha(saved/'QA-CASOS-WASCAR.json'),afterCatalogSha256=sha(path),manualWascarResultsWritten=False,qaDatabaseDml=False))
 for profile in ['manual','rc9']:subprocess.run(['C:/Python312/python.exe','-B',str(generator),'--profile',profile],cwd=ROOT,check=True)
 print(json.dumps(dict(newlyAvailable=[91,92,93],caseCount=93,resultsWritten=False)))
class Guide1509(unittest.TestCase):
 def setUp(self):
  self.matrix=read(E/'QA-MATRIX-1509.json');self.catalog=read(ROOT/'docs/QA-CASOS-WASCAR.json');self.before=read(E/'qa-guide/source-before/QA-CASOS-WASCAR.json');self.guide=load('guide1509','tools/windows/qa_guide.py')
 def available(self,ctx,catalog=None):return json.loads(self.guide.render(catalog or self.catalog,ctx).split('const guide=',1)[1].split(';',1)[0])['cases']
 def test_preserve90_cases_and_all_remaining_new_steps(self):
  self.assertEqual(self.catalog['cases'][:90],self.before['cases'][:90])
  for c,o in zip(self.catalog['cases'][90:],self.before['cases'][90:]):self.assertEqual(c,{**o,'feature':FEATURE,'steps':[c['steps'][0],*o['steps'][1:]]});self.assertNotIn('NO DISPONIBLE',c['steps'][0])
 def test_closed_pair_roles_configured_and_gate_required(self):
  ctx=dict(configured=True,roles=True,restored=True,origin='',**self.matrix['pair'])
  for delta,expected in [({},True),(self.matrix['sourcePair'],False),({'bundle':'future'},False),({'dll':'future'},False),({'configured':False},False),({'roles':False},False)]:self.assertEqual([self.available({**ctx,**delta})['QA-'+str(n)]['available'] for n in [91,92,93]],[expected]*3)
  missing={k:v for k,v in self.catalog.items() if k!=BUILDS};self.assertFalse(self.available(ctx,missing)['QA-91']['available'])
 def test_previous_build_gates_append_only_new_closed_pair(self):
  for k,v in self.before.items():
   if k in ['revision','cases']:continue
   self.assertEqual(self.catalog[k],v+[self.matrix['pair']] if k in self.matrix['inheritedBuildLists'] else v)
 def test_result_logic_exact_generator_one_ascii_mapping(self):
  before=(E/'qa-guide/source-before/qa_guide.py').read_bytes();nl=b'\r\n' if b'\r\n' in before else b'\n';self.assertEqual((ROOT/'tools/windows/qa_guide.py').read_bytes(),before.replace(ANCHOR,ANCHOR+nl+MAPPING))
 def test_existing_helpers_only_count_and_generator_expectation(self):
  for p in HELPERS:self.assertEqual((ROOT/p).read_bytes(),expected_helper((E/'qa-guide/source-before'/Path(p).name).read_bytes(),p))
 def test_both_current_guides93_and8(self):
  for profile,count in [('manual',8),('rc9',93)]:self.assertTrue(self.guide.generate(check=True,profile=profile));self.assertEqual(sum(c['available'] for c in self.available(self.guide.context(profile=profile)).values()),count)
def tests():
 assert not (E/'QA-TESTS-01.json').exists();modules=[load(n,p) for n,p in [('base1509','tools/tests/test_qa_guide.py'),('excel1509','tools/tests/test_rc9_excel_guide832.py'),('status1509','tools/tests/test_qa_relations_status848.py'),('ports1509','tools/tests/qa_port_colors969.py'),('category1509','tools/tests/qa_category_colors1089.py')]];suite=unittest.TestSuite()
 for m in modules:suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(m))
 suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Guide1509));start=time.monotonic()
 with (E/'QA-TESTS-01.log').open('x',encoding='utf-8') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
 save('QA-TESTS-01.json',dict(successful=result.wasSuccessful(),testsRun=result.testsRun,seconds=round(time.monotonic()-start,3),caseCount=93,available=dict(manual=8,rc9=93),newlyAvailable=[91,92,93],previous90CasesExact=True,manualWascarResultsWritten=False));print(json.dumps(dict(successful=result.wasSuccessful(),testsRun=result.testsRun)));return 0 if result.wasSuccessful() else 1
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['enable','tests']);a=p.parse_args()
 if a.action=='enable':enable();return 0
 return tests()
if __name__=='__main__':raise SystemExit(main())
