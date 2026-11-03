"""Closed availability for shared templates; preserve Wascar cases and QA532."""
import importlib.util,json,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('qa_guide',ROOT/'tools/windows/qa_guide.py');guide=importlib.util.module_from_spec(spec);spec.loader.exec_module(guide)
def cases(c,ctx):return json.loads(guide.render(c,ctx).split('const guide=',1)[1].split(';',1)[0])['cases']
class SharedQa592(unittest.TestCase):
    def test_previous68_exact_and_current_snapshots_never_enable_development_shared_cases(self):
        c=json.loads(guide.CATALOG.read_bytes());old=json.loads(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'show','cc61892f88dbd7cb0d0301c222f40a6f1a80de94:docs/QA-CASOS-WASCAR.json'],cwd=ROOT))
        self.assertEqual(c['cases'][:68],old['cases']);self.assertEqual(len(c['cases']),71)
        for profile,expected in [('manual',8),('rc9',68)]:
            current=cases(c,guide.context(profile=profile));self.assertEqual(sum(x['available'] for x in current.values()),expected)
            self.assertTrue(all(not current[f'QA-{n}']['available'] for n in range(69,72)))
        for item in c['cases'][68:]:
            self.assertGreaterEqual(len(item['steps']),8);self.assertIn('NO ESTÁ DISPONIBLE',item['steps'][0]);self.assertIn('Plantillas compartidas',' '.join(item['steps']));self.assertIn('Pass',item['steps'][-1])
    def test_shared_feature_requires_exact_two_hashes_configured_and_roles(self):
        c=json.loads(guide.CATALOG.read_bytes());m=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json').read_bytes())
        pair=dict(bundle=m['distributions']['frontend']['app.js'],dll=m['distributions']['server']['RackClick.Server.dll']);self.assertEqual(c['sharedTemplatesBuilds'],[pair])
        ctx=dict(configured=True,origin='',roles=True,restored=True,**pair)
        for change,want in [({},True),({'bundle':'wrong'},False),({'dll':'wrong'},False),({'roles':False},False),({'configured':False},False)]:
            result=cases(c,{**ctx,**change});self.assertTrue(all(result[f'QA-{n}']['available']==want for n in range(69,72)))
if __name__=='__main__':unittest.main()
