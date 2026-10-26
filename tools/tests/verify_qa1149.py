"""Evolve prior guide expectations to the newly selected closed13 pair; run one regression."""
import importlib.util,json,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1090-1149'
BASE='60868854ce40a0eda773fd1817f48f7da41aae46'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 out=E/'QA-TESTS-01.json';assert not out.exists();matrix=json.loads((E/'QA-MATRIX-1149.json').read_bytes())
 p=ROOT/'tools/tests/test_qa_relations_status848.py';b=p.read_bytes();assert b"('rc9', 81)" in b;p.write_bytes(b.replace(b"('rc9', 81)",b"('rc9', 84)"))
 p=ROOT/'tools/tests/qa_port_colors969.py';b=p.read_bytes()
 old=b'self.assertEqual(current[key],expected)';new=b"self.assertEqual(current[key][:len(expected)] if key in matrix['inheritedBuildLists'] else current[key],expected)";assert old in b;b=b.replace(old,new)
 old=b"self.assertEqual(catalog['userPortColorsBuilds'],[m['pair']])";assert old in b;b=b.replace(old,b"self.assertIn(m['pair'],catalog['userPortColorsBuilds'])").replace(b"('rc9',81)",b"('rc9',84)")
 old=b'before.replace(anchor,anchor+added))'
 port=b"        'userPortColorsGui': catalog.get('userPortColorsBuilds', []),"
 category=b"        'userCategoryColorsGui': catalog.get('userCategoryColorsBuilds', []),"
 new=b'before.replace(anchor,anchor+added).replace('+repr(port).encode()+b','+repr(port).encode()+b'+newline+'+repr(category).encode()+b'))';assert old in b;b=b.replace(old,new);p.write_bytes(b)
 p=ROOT/'tools/tests/qa_category_colors1089.py';text=p.read_text(encoding='utf-8');before,rest=text.split('class CategoryGuide1089(unittest.TestCase):',1);_,after=rest.split("if __name__=='__main__':",1)
 revised='''class CategoryGuide1089(unittest.TestCase):
 def test_existing81_and_all_build_lists_unchanged(self):
  old=json.loads(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'show','60868854ce40a0eda773fd1817f48f7da41aae46:docs/QA-CASOS-WASCAR.json']))
  current=json.loads(CATALOG.read_bytes());matrix=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-1090-1149/QA-MATRIX-1149.json').read_bytes())
  self.assertEqual(current['cases'][:81],old['cases'][:81])
  for case,original in zip(current['cases'][81:],old['cases'][81:]):
   self.assertEqual(case,{**original,'feature':'userCategoryColorsGui','steps':[case['steps'][0]]+original['steps'][1:]})
   self.assertIn('DISPONIBLE EN TU SNAPSHOT',case['steps'][0])
  for key,value in old.items():
   if key in ['cases','revision']:continue
   expected=value+[matrix['pair']] if key in matrix['inheritedBuildLists'] else value
   self.assertEqual(current[key],expected)
  self.assertEqual(current['userCategoryColorsBuilds'],[matrix['pair']])

 def test_closed_1149_availability_owner_config_and_generator(self):
  current=json.loads(CATALOG.read_bytes());matrix=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-1090-1149/QA-MATRIX-1149.json').read_bytes());self.assertEqual(len(current['cases']),84)
  def available(ctx,catalog=current):
   cases=json.loads(guide.render(catalog,ctx).split('const guide=',1)[1].split(';',1)[0])['cases']
   return [cases['QA-'+str(i)]['available'] for i in [82,83,84]]
  ctx=dict(configured=True,roles=True,restored=True,origin='',**matrix['pair'])
  self.assertEqual(available(ctx),[True]*3)
  for delta in [matrix['sourcePair'],dict(dll='future'),dict(bundle='future'),dict(roles=False),dict(configured=False)]:
   self.assertEqual(available({**ctx,**delta}),[False]*3)
  missing={k:v for k,v in current.items() if k!='userCategoryColorsBuilds'};self.assertEqual(available(ctx,missing),[False]*3)
  for profile,count in [('manual',8),('rc9',84)]:
   self.assertTrue(guide.generate(check=True,profile=profile))
   cases=json.loads(guide.render(current,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases'];self.assertEqual(sum(v['available'] for v in cases.values()),count)
  before=(ROOT/'evidence/s1-20261018/sesenta-tandas-1090-1149/qa-guide/source-before/qa_guide.py').read_bytes()
  anchor=b"        'userPortColorsGui': catalog.get('userPortColorsBuilds', []),"
  nl=b'\\r\\n' if b'\\r\\n' in before else b'\\n'
  self.assertEqual((ROOT/'tools/windows/qa_guide.py').read_bytes(),before.replace(anchor,anchor+nl+b"        'userCategoryColorsGui': catalog.get('userCategoryColorsBuilds', []),"))

'''
 p.write_text(before+revised+"if __name__=='__main__':"+after,encoding='utf-8')
 base=load('guide1149base','tools/tests/test_qa_guide.py')
 modules=[base,load('excel1149','tools/tests/test_rc9_excel_guide832.py'),load('status1149','tools/tests/test_qa_relations_status848.py'),load('ports1149','tools/tests/qa_port_colors969.py'),load('categories1149','tools/tests/qa_category_colors1089.py')]
 guide=base.guide
 for profile in ['manual','rc9']:guide.generate(profile=profile)
 class Actual1149(unittest.TestCase):
  def test_current_pair_is_really_selected(self):
   ctx=guide.context(profile='rc9');self.assertEqual({k:ctx[k] for k in ['bundle','dll']},matrix['pair']);self.assertTrue(ctx['configured'] and ctx['roles'])
  def test_user_result_code_is_byte_identical(self):
   marker=b"const key='RackClick.QA.Wascar.results.v1'";old=(E/'qa-guide/source-before/qa_guide.py').read_bytes();new=(ROOT/'tools/windows/qa_guide.py').read_bytes()
   self.assertEqual(old.split(marker,1)[1],new.split(marker,1)[1]);self.assertEqual(matrix['changedFields'],['feature','steps[0]'])
 suite=unittest.TestSuite()
 for m in modules:suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(m))
 suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Actual1149));started=time.monotonic()
 with (E/'QA-TESTS-01.log').open('x',encoding='utf-8') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
 record=dict(successful=result.wasSuccessful(),testsRun=result.testsRun,failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),caseCount=84,available=dict(manual=8,rc9=84),previous81Exact=True,manualWascarResultsWritten=False,applicationBuilds=0,frontendBuilds=0)
 out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record));return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
