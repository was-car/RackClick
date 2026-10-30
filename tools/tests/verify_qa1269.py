"""Evolve exact guide expectations, preserving non-test bytes, then one regression."""
import hashlib,importlib.util,json,subprocess,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1210-1269'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def edit(path,changes):
 p=ROOT/path;b=p.read_bytes()
 for old,new in changes:
  assert b.count(old)==1,(path,old,b.count(old));b=b.replace(old,new)
 p.write_bytes(b)
def main():
 out=E/'QA-TESTS-01.json';assert not out.exists();matrix=json.loads((E/'QA-MATRIX-1269.json').read_bytes())
 added=b"        'adminUserOnboardingGui': catalog.get('adminUserOnboardingBuilds', []),"
 category=b"        'userCategoryColorsGui': catalog.get('userCategoryColorsBuilds', []),"
 # Exact ASCII replacements only; archive originals before evolving expectations.
 edit('tools/tests/test_qa_relations_status848.py',[(b"('rc9', 84)",b"('rc9', 87)")])
 edit('tools/tests/qa_port_colors969.py',[(b"('rc9',84)",b"('rc9',87)"),
  (b'+newline+'+repr(category).encode()+b'))',b'+newline+'+repr(category).encode()+b').replace('+repr(category).encode()+b','+repr(category).encode()+b'+newline+'+repr(added).encode()+b'))')])
 edit('tools/tests/qa_category_colors1089.py',[
  (b'self.assertEqual(current[key],expected)',b"self.assertEqual(current[key][:len(expected)] if key in matrix['inheritedBuildLists'] else current[key],expected)"),
  (b"self.assertEqual(current['userCategoryColorsBuilds'],[matrix['pair']])",b"self.assertEqual(current['userCategoryColorsBuilds'][:1],[matrix['pair']])"),
  (b"('rc9',84)",b"('rc9',87)"),
  (b'+nl+b"'+category+b'"))',b'+nl+b"'+category+b'").replace('+repr(category).encode()+b','+repr(category).encode()+b'+nl+'+repr(added).encode()+b'))')])
 base=load('guide1269base','tools/tests/test_qa_guide.py');guide=base.guide
 for profile in ['manual','rc9']:guide.generate(profile=profile)
 old=json.loads((E/'qa-guide/source-before/QA-CASOS-WASCAR.json').read_bytes());current=json.loads(guide.CATALOG.read_bytes())
 class Actual1269(unittest.TestCase):
  def test_old84_complete_cases_exact(self):self.assertEqual(current['cases'][:84],old['cases'][:84])
  def test_only_availability_intro_and_feature_of85to87_changed(self):
   for c,o in zip(current['cases'][84:],old['cases'][84:]):
    self.assertEqual(c,{**o,'feature':'adminUserOnboardingGui','steps':[c['steps'][0]]+o['steps'][1:]});self.assertIn('DISPONIBLE EN TU SNAPSHOT',c['steps'][0])
  def test_all_existing_gates_preserved_and_extended_only_from1089(self):
   for k,v in old.items():
    if k not in ['revision','cases']:self.assertEqual(current[k],v+[matrix['pair']] if k in matrix['inheritedBuildLists'] else v)
   self.assertEqual(current['adminUserOnboardingBuilds'],[matrix['pair']])
  def test_closed_pair_owner_and_config_fail_closed(self):
   ctx=dict(configured=True,roles=True,restored=True,origin='',**matrix['pair'])
   def available(ctx,catalog=current):
    c=json.loads(guide.render(catalog,ctx).split('const guide=',1)[1].split(';',1)[0])['cases'];return [c['QA-'+str(n)]['available'] for n in [85,86,87]]
   self.assertEqual(available(ctx),[True]*3)
   for delta in [matrix['sourcePair'],dict(bundle='future'),dict(dll='future'),dict(roles=False),dict(configured=False)]:self.assertEqual(available({**ctx,**delta}),[False]*3)
   self.assertEqual(available(ctx,{k:v for k,v in current.items() if k!='adminUserOnboardingBuilds'}),[False]*3)
  def test_actual_selected_pair_counts_and_rendered_guides(self):
   ctx=guide.context(profile='rc9');self.assertEqual({k:ctx[k] for k in ['bundle','dll']},matrix['pair'])
   for profile,count in [('manual',8),('rc9',87)]:
    self.assertTrue(guide.generate(check=True,profile=profile));c=json.loads(guide.render(current,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases'];self.assertEqual(sum(r['available'] for r in c.values()),count)
  def test_generator_single_mapping_and_user_result_bytes_exact(self):
   before=(E/'qa-guide/source-before/qa_guide.py').read_bytes();after=(ROOT/'tools/windows/qa_guide.py').read_bytes();nl=b'\r\n' if b'\r\n' in before else b'\n'
   self.assertEqual(after,before.replace(category,category+nl+added));marker=b"const key='RackClick.QA.Wascar.results.v1'";self.assertEqual(after.split(marker,1)[1],before.split(marker,1)[1])
  def test_helper_nonclass_bytes_exact_utf8(self):
   before=(E/'qa-guide/source-before/qa_category_colors1089.py').read_bytes();after=(ROOT/'tools/tests/qa_category_colors1089.py').read_bytes();anchor=b'class CategoryGuide1089(unittest.TestCase):';tail=b"if __name__=='__main__':"
   self.assertEqual(before.split(anchor,1)[0],after.split(anchor,1)[0]);self.assertEqual(before.split(tail,1)[1],after.split(tail,1)[1]);after.decode('utf-8')
 suite=unittest.TestSuite()
 for m in [base,load('excel1269','tools/tests/test_rc9_excel_guide832.py'),load('status1269','tools/tests/test_qa_relations_status848.py'),load('ports1269','tools/tests/qa_port_colors969.py'),load('categories1269','tools/tests/qa_category_colors1089.py')]:suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(m))
 suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Actual1269));started=time.monotonic()
 with (E/'QA-TESTS-01.log').open('x',encoding='utf-8') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
 record=dict(successful=result.wasSuccessful(),testsRun=result.testsRun,failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),caseCount=87,available=dict(manual=8,rc9=87),previous84CompleteCasesExact=True,manualWascarResultsWritten=False,applicationBuilds=0,frontendBuilds=0)
 with out.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
 print(json.dumps(record));return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
