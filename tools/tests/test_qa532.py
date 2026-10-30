"""QA532 catalog compatibility, exact feature pair and preserved old case definitions."""
import importlib.util,json,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('qa_guide',ROOT/'tools/windows/qa_guide.py');guide=importlib.util.module_from_spec(spec);spec.loader.exec_module(guide)
def data(c,ctx):return json.loads(guide.render(c,ctx).split('const guide=',1)[1].split(';',1)[0])['cases']
class Qa532(unittest.TestCase):
    def test_previous65_are_exact_and_new_three_have_specific_steps(self):
        old=json.loads(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'show','a4cf9a8aef6310b2160d91d1a14c90ec98d6a486:docs/QA-CASOS-WASCAR.json'],cwd=ROOT));c=json.loads(guide.CATALOG.read_text(encoding='utf-8'))
        self.assertEqual(c['cases'][:65],old['cases']);self.assertGreaterEqual(len(c['cases']),68)
        for case in c['cases'][65:68]:self.assertGreaterEqual(len(case['steps']),7);self.assertIn('Mis plantillas privadas',' '.join(case['steps']));self.assertIn('Pass',case['steps'][-1])
    def test_final03_requires_both_hashes_roles_and_selection(self):
        c=json.loads(guide.CATALOG.read_text(encoding='utf-8'));m=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-473-532/CANDIDATA532-FINAL03.json').read_text());pair={'bundle':m['distributions']['frontend']['app.js'],'dll':m['distributions']['server']['RackClick.Server.dll']}
        self.assertEqual(c['privateConfigurationBuilds'],[pair]);ctx={'configured':True,'origin':'','roles':True,'restored':True,**pair}
        self.assertEqual(sum(v['available'] for v in data(c,ctx).values()),68)
        for edit in [{'bundle':'wrong'},{'dll':'wrong'},{'roles':False},{'configured':False}]:self.assertTrue(all(not data(c,{**ctx,**edit})[f'QA-{n}']['available'] for n in range(66,69)))
        old=json.loads((ROOT/'evidence/s1-20261017/seis-tandas-180-185/CANDIDATA185.json').read_text());oldctx={**ctx,'bundle':old['distributions']['frontend']['app.js'],'dll':old['distributions']['server']['RackClick.Server.dll']}
        previous=data(c,oldctx);self.assertEqual(sum(v['available'] for v in previous.values()),59);self.assertTrue(all(not previous[f'QA-{n}']['available'] for n in range(60,69)))
if __name__=='__main__':unittest.main()
