"""Enable only the three reviewed links cases after real QA selection."""
import argparse,copy,importlib.util,json,subprocess,time,unittest
from pathlib import Path
from integration1389 import ROOT,E,ER,BASE,GIT,TARGET,PIN,sha,save,read
FEATURE='adminGroupRelationLinksGui';BUILDS='adminGroupRelationLinksBuilds'
MAPPING=b"        'adminGroupRelationLinksGui': catalog.get('adminGroupRelationLinksBuilds', []),"
ANCHOR=b"        'adminUserOnboardingGui': catalog.get('adminUserOnboardingBuilds', []),"
HELPERS=['tools/tests/test_qa_relations_status848.py','tools/tests/qa_port_colors969.py','tools/tests/qa_category_colors1089.py']
def expected_helper(raw,path):
 if path.endswith('test_qa_relations_status848.py'):
  old=b"('rc9', 87)";assert raw.count(old)==1;return raw.replace(old,b"('rc9', 90)")
 old=b"('rc9',87)";assert raw.count(old)==1;value=raw.replace(old,b"('rc9',90)")
 lines=value.splitlines(keepends=True);count=0
 for i,line in enumerate(lines):
  if b"self.assertEqual((ROOT/'tools/windows/qa_guide.py').read_bytes()," not in line:continue
  ending=b'\r\n' if line.endswith(b'\r\n') else b'\n';body=line[:-len(ending)];assert body.endswith(b'))');newline=b'newline' if b'+newline+' in body else b'nl'
  addition=b'.replace('+repr(ANCHOR).encode('ascii')+b','+repr(ANCHOR).encode('ascii')+b'+'+newline+b'+'+repr(MAPPING).encode('ascii')+b')'
  lines[i]=body[:-1]+addition+b')'+ending;count+=1
 assert count==1;return b''.join(lines)
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def enable():
 actual=read(E/'REAL-QA-UPDATE-01.json');validated=read(E/'REAL-QA-VALIDATE-01.json');assert actual['valid'] and actual['state']=='committed' and validated['valid'] and validated['selectedRevision']==1329
 path=ROOT/'docs/QA-CASOS-WASCAR.json';before=path.read_bytes();original=json.loads(before);catalog=copy.deepcopy(original);assert len(catalog['cases'])==90 and BUILDS not in catalog
 m=read(ROOT/TARGET);assert sha(ROOT/TARGET)==PIN;old=read(ROOT/'evidence/s1-20261018/sesenta-tandas-1150-1209/CANDIDATA1209-01.json');pair=lambda x:dict(bundle=x['distributions']['frontend']['app.js'],dll=x['distributions']['server']['RackClick.Server.dll']);new,previous=pair(m),pair(old)
 directory=Path(read(ROOT/'.local/qa-rc9/current.json')['directory']);assert directory==(ROOT/actual['directory']).resolve();cfg=read(directory/'manual-qa.json');assert cfg['bundleSha256']==new['bundle'] and cfg['dllSha256']==new['dll']
 saved=E/'qa-guide/source-before';saved.mkdir(parents=True,exist_ok=False)
 for p in ['docs/QA-CASOS-WASCAR.json','tools/windows/qa_guide.py']+HELPERS:(saved/Path(p).name).write_bytes((ROOT/p).read_bytes())
 inherited=[]
 for key,values in catalog.items():
  if key.endswith('Builds') and isinstance(values,list) and previous in values and new not in values:
   assert all(isinstance(v,dict) and set(v)=={'bundle','dll'} for v in values);values.append(new);inherited.append(key)
 catalog[BUILDS]=[new];intros=[
 'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Interfaz1329/esquema13 seleccionada sobre el mismo laboratorio, con datos y resultados conservados. Ejecuta INICIAR-QA-RESTAURADO.cmd; usa su guía y credenciales privadas. Elige Español y pulsa Ctrl+F5.',
 'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Continúa desde QA-88 con el UUID confirmado. La navegación entre relaciones no guarda ni cambia usuarios, miembros o permisos.',
 'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Usa cuentas de laboratorio preparadas en perfiles de navegador separados; no retires acceso al último administrador. Si falta una fixture segura o lector de pantalla, registra Bloqueado para esa parte.'
 ]
 for case,intro in zip(catalog['cases'][87:],intros):assert case['feature']=='planned';case['feature']=FEATURE;case['steps'][0]=intro
 assert catalog['cases'][:87]==original['cases'][:87];catalog['revision']='2026-10-18-bloque1330-1389';nl='\r\n' if b'\r\n' in before else '\n';path.write_bytes((json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').replace('\n',nl).encode('utf-8'))
 generator=ROOT/'tools/windows/qa_guide.py';raw=generator.read_bytes();assert raw.count(ANCHOR)==1 and MAPPING not in raw;generator.write_bytes(raw.replace(ANCHOR,ANCHOR+(b'\r\n' if b'\r\n' in raw else b'\n')+MAPPING))
 for p in HELPERS:
  f=ROOT/p;f.write_bytes(expected_helper(f.read_bytes(),p))
 save('QA-MATRIX-1389.json',dict(sourcePair=previous,pair=new,inheritedBuildLists=inherited,caseCount=90,unchangedCompleteCases=87,changedCases=['QA-88','QA-89','QA-90'],changedFields=['feature','steps[0]'],otherStepsAndExpectedUnchanged=True,beforeCatalogSha256=sha(saved/'QA-CASOS-WASCAR.json'),afterCatalogSha256=sha(path),manualWascarResultsWritten=False,qaDatabaseDml=False))
 for profile in ['manual','rc9']:subprocess.run(['C:/Python312/python.exe','-B',str(generator),'--profile',profile],cwd=ROOT,check=True)
 print(json.dumps(dict(newlyAvailable=[88,89,90],caseCount=90,resultsWritten=False)))
class Guide1389(unittest.TestCase):
 def setUp(self):
  self.matrix=read(E/'QA-MATRIX-1389.json');self.catalog=read(ROOT/'docs/QA-CASOS-WASCAR.json');self.before=read(E/'qa-guide/source-before/QA-CASOS-WASCAR.json');self.guide=load('guide1389','tools/windows/qa_guide.py')
 def availability(self,ctx,catalog=None):return json.loads(self.guide.render(catalog or self.catalog,ctx).split('const guide=',1)[1].split(';',1)[0])['cases']
 def test_preserve87_complete_cases_and_new_steps_expected(self):
  self.assertEqual(self.catalog['cases'][:87],self.before['cases'][:87])
  for c,o in zip(self.catalog['cases'][87:],self.before['cases'][87:]):
   self.assertEqual(c,{**o,'feature':FEATURE,'steps':[c['steps'][0],*o['steps'][1:]]});self.assertNotIn('NO DISPONIBLE',c['steps'][0])
 def test_only_closed_pair_with_roles_configured_and_build_list(self):
  ctx=dict(configured=True,roles=True,restored=True,origin='',**self.matrix['pair'])
  for delta,expected in [({},True),(self.matrix['sourcePair'],False),({'bundle':'future'},False),({'dll':'future'},False),({'configured':False},False),({'roles':False},False)]:self.assertEqual([self.availability({**ctx,**delta})['QA-'+str(n)]['available'] for n in [88,89,90]],[expected]*3)
  missing={k:v for k,v in self.catalog.items() if k!=BUILDS};self.assertFalse(self.availability(ctx,missing)['QA-88']['available'])
 def test_previous_build_gates_keep_values_and_append_exact_pair(self):
  for k,v in self.before.items():
   if k in ['revision','cases']:continue
   self.assertEqual(self.catalog[k],v+[self.matrix['pair']] if k in self.matrix['inheritedBuildLists'] else v)
 def test_results_generator_only_one_ascii_mapping_added(self):
  before=(E/'qa-guide/source-before/qa_guide.py').read_bytes();nl=b'\r\n' if b'\r\n' in before else b'\n';self.assertEqual((ROOT/'tools/windows/qa_guide.py').read_bytes(),before.replace(ANCHOR,ANCHOR+nl+MAPPING))
 def test_helper_bytes_only_count_and_generator_expectation(self):
  for p in HELPERS:self.assertEqual((ROOT/p).read_bytes(),expected_helper((E/'qa-guide/source-before'/Path(p).name).read_bytes(),p))
 def test_both_current_guides90_and8_available(self):
  for profile,count in [('manual',8),('rc9',90)]:self.assertTrue(self.guide.generate(check=True,profile=profile));self.assertEqual(sum(c['available'] for c in self.availability(self.guide.context(profile=profile)).values()),count)
def tests():
 assert not (E/'QA-TESTS-01.json').exists();modules=[load(n,p) for n,p in [('base1389','tools/tests/test_qa_guide.py'),('excel1389','tools/tests/test_rc9_excel_guide832.py'),('status1389','tools/tests/test_qa_relations_status848.py'),('ports1389','tools/tests/qa_port_colors969.py'),('category1389','tools/tests/qa_category_colors1089.py')]];suite=unittest.TestSuite()
 for m in modules:suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(m))
 suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Guide1389));start=time.monotonic()
 with (E/'QA-TESTS-01.log').open('x',encoding='utf-8') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
 save('QA-TESTS-01.json',dict(successful=r.wasSuccessful(),testsRun=r.testsRun,seconds=round(time.monotonic()-start,3),caseCount=90,available=dict(manual=8,rc9=90),newlyAvailable=[88,89,90],previous87CasesExact=True,manualWascarResultsWritten=False));print(json.dumps(dict(successful=r.wasSuccessful(),testsRun=r.testsRun)));return 0 if r.wasSuccessful() else 1
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['enable','tests']);a=p.parse_args()
 if a.action=='enable':enable();return 0
 return tests()
if __name__=='__main__':raise SystemExit(main())
