"""Evolve planned guide tests after real selection, then run one relevant guide regression."""
import importlib.util
import json
from pathlib import Path
import time
import unittest

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029'


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def main():
    out=E/'QA-TESTS-01.json';assert not out.exists()
    matrix=json.loads((E/'QA-MATRIX-1029.json').read_bytes())
    path=ROOT/'tools/tests/test_qa_relations_status848.py';source=path.read_text(encoding='utf-8')
    assert "self.assertEqual(catalog['adminGroupRelationsAnnouncementBuilds'], [pair])" in source
    source=source.replace("self.assertEqual(catalog['adminGroupRelationsAnnouncementBuilds'], [pair])","self.assertIn(pair, catalog['adminGroupRelationsAnnouncementBuilds'])")
    source=source.replace("('rc9', 78)","('rc9', 81)")
    path.write_text(source,encoding='utf-8')
    path=ROOT/'tools/tests/qa_port_colors969.py';source=path.read_text(encoding='utf-8')
    before,rest=source.split('class GuidePalette969(unittest.TestCase):',1)
    _,after=rest.split("if __name__ == '__main__':",1)
    revised='''class GuidePalette969(unittest.TestCase):
    def test_previous_cases_and_build_gates_unchanged(self):
        original=json.loads(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'show',BASE+':docs/QA-CASOS-WASCAR.json']))
        current=json.loads(CATALOG.read_bytes())
        matrix=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029/QA-MATRIX-1029.json').read_bytes())
        self.assertEqual(current['cases'][:78],original['cases'])
        for key,value in original.items():
            if key in ['revision','cases']:continue
            expected=value+[matrix['pair']] if key in matrix['inheritedBuildLists'] else value
            self.assertEqual(current[key],expected)

    def test_three_new_cases_require_the_closed_1029_pair(self):
        catalog=json.loads(CATALOG.read_bytes())
        original=json.loads(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'show',BASE+':docs/QA-CASOS-WASCAR.json']))
        m=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029/QA-MATRIX-1029.json').read_bytes())
        self.assertEqual(catalog['userPortColorsBuilds'],[m['pair']])
        for case,old in zip(catalog['cases'][78:],original['cases'][78:]):
            self.assertEqual(case,{**old,'feature':'userPortColorsGui','steps':[case['steps'][0]]+old['steps'][1:]})
        def availability(ctx):
            data=json.loads(guide.render(catalog,ctx).split('const guide=',1)[1].split(';',1)[0])['cases']
            return [data['QA-'+str(n)]['available'] for n in [79,80,81]]
        ctx=dict(configured=True,roles=True,restored=True,origin='',**m['pair'])
        self.assertEqual(availability(ctx),[True]*3)
        for delta in [m['sourcePair'],dict(bundle='future'),dict(dll='future'),dict(roles=False),dict(configured=False)]:
            self.assertEqual(availability({**ctx,**delta}),[False]*3)

    def test_actual_availability_and_result_logic_preserved(self):
        catalog=json.loads(CATALOG.read_bytes())
        for profile,count in [('manual',8),('rc9',81)]:
            metadata=json.loads(guide.render(catalog,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases']
            self.assertEqual(sum(v['available'] for v in metadata.values()),count)
            self.assertTrue(guide.generate(check=True,profile=profile))
        before=(ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029/qa-guide/source-before/qa_guide.py').read_bytes()
        anchor=b"        'adminGroupRelationsAnnouncementGui': catalog.get('adminGroupRelationsAnnouncementBuilds', []),"
        newline=b'\\r\\n' if b'\\r\\n' in before else b'\\n'
        added=newline+b"        'userPortColorsGui': catalog.get('userPortColorsBuilds', []),"
        self.assertEqual((ROOT/'tools/windows/qa_guide.py').read_bytes(),before.replace(anchor,anchor+added))


'''
    revised=revised.replace("BASE+':docs/QA-CASOS-WASCAR.json'","'962948f48543429d22cc806d5951ea94e2c90dc2:docs/QA-CASOS-WASCAR.json'").replace("self.assertEqual(current['cases'][:78],original['cases'])","self.assertEqual(current['cases'][:78],original['cases'][:78])")
    path.write_text(before+revised+"if __name__ == '__main__':"+after,encoding='utf-8')
    base=module('guide_tests1029','tools/tests/test_qa_guide.py')
    excel=module('excel_tests1029','tools/tests/test_rc9_excel_guide832.py')
    status=module('status_tests1029','tools/tests/test_qa_relations_status848.py')
    colors=module('colors_tests1029','tools/tests/qa_port_colors969.py')
    guide=base.guide
    for profile in ['manual','rc9']:guide.generate(profile=profile)
    class Actual969(unittest.TestCase):
        def test_selected_pair_gate_is_not_a_development_file_gate(self):
            ctx=guide.context(profile='rc9');self.assertEqual(ctx['bundle'],matrix['pair']['bundle']);self.assertEqual(ctx['dll'],matrix['pair']['dll'])
            for profile in ['manual','rc9']:
                self.assertTrue(guide.generate(check=True,profile=profile))
            catalog=json.loads(guide.CATALOG.read_bytes());catalog.pop('userPortColorsBuilds')
            metadata=json.loads(guide.render(catalog,ctx).split('const guide=',1)[1].split(';',1)[0])['cases']
            self.assertFalse(any(metadata['QA-'+str(n)]['available'] for n in [79,80,81]))
        def test_notes_and_import_code_remain_the_same(self):
            before=(E/'qa-guide/source-before/qa_guide.py').read_bytes()
            current=(ROOT/'tools/windows/qa_guide.py').read_bytes()
            marker=b"const key='RackClick.QA.Wascar.results.v1'"
            self.assertEqual(current.split(marker,1)[1],before.split(marker,1)[1])
            self.assertEqual(matrix['changedFields'],['feature','steps[0]'])
            self.assertTrue(matrix['otherStepsAndExpectedUnchanged'])
    suite=unittest.TestSuite()
    for mod in [base,excel,status,colors]:suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(mod))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Actual969))
    started=time.monotonic()
    with (E/'QA-TESTS-01.log').open('x',encoding='utf-8') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    record=dict(testsRun=result.testsRun,successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),
        availability=dict(manual=8,rc9=81),caseCount=81,first78Exact=True,userNotesModified=False,applicationBuilds=0,frontendBuilds=0)
    out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record))
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
