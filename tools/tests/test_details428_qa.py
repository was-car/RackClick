"""Real QA remains unchanged; future details cases require the exact artifact pair."""
import hashlib,importlib.util,json,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('qa_guide',ROOT/'tools/windows/qa_guide.py');guide=importlib.util.module_from_spec(spec);spec.loader.exec_module(guide)
def metadata(c,ctx):return json.loads(guide.render(c,ctx).split('const guide=',1)[1].split(';',1)[0])['cases']
class DetailsQa(unittest.TestCase):
    def test_previous_cases_and_observations_are_not_rewritten(self):
        old=json.loads(subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'show','69eb63def2a33f5012c9728d21d82c634fcb9b99:docs/QA-CASOS-WASCAR.json'],cwd=ROOT))
        now=json.loads(guide.CATALOG.read_text(encoding='utf-8'));self.assertEqual(now['cases'][:62],old['cases']);self.assertGreaterEqual(len(now['cases']),65)
        # The guide generator reads snapshots; it never imports or writes user result files.
        for profile in ['manual','rc9']:
            ctx=guide.context(profile=profile)
            selected532=profile=='rc9' and any(ctx['bundle']==p['bundle'] and ctx['dll']==p['dll'] for p in now.get('privateConfigurationBuilds',[]))
            cases=metadata(now,ctx);self.assertEqual(sum(c['available'] for c in cases.values()),68 if selected532 else 59 if profile=='rc9' else 8)
            self.assertTrue(all(cases[f'QA-{n}']['available']==selected532 for n in range(60,66)))
    def test_future_pair_is_exact_and_roles_required(self):
        c=json.loads(guide.CATALOG.read_text(encoding='utf-8'));pair=c['inventoryChangeDetailsBuilds'][0]
        ctx={'configured':True,'origin':'','roles':True,'restored':True,**pair}
        for edits,wanted in [({},True),({'bundle':'old'},False),({'dll':'old'},False),({'roles':False},False),({'configured':False},False)]:
            actual=metadata(c,{**ctx,**edits})
            self.assertTrue(all(actual[f'QA-{n}']['available']==wanted for n in range(63,66)))
if __name__=='__main__':unittest.main()
