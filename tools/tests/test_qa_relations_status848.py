"""Require the closed849 announcement pair; older QA remains blocked."""
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'evidence/s1-20261018/tanda-848'
spec = importlib.util.spec_from_file_location('guide848', ROOT / 'tools/windows/qa_guide.py')
guide = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guide)


class RelationsStatusGuide(unittest.TestCase):
    def test_previous77_cases_remain_exact(self):
        base = json.loads((E / 'INICIO.json').read_bytes())['baseCommit']
        original = json.loads(subprocess.check_output([
            str(ROOT / '.local/git-2.55.0.5/cmd/git.exe'), 'show',
            base + ':docs/QA-CASOS-WASCAR.json'], cwd=ROOT))
        current = json.loads(guide.CATALOG.read_bytes())
        self.assertEqual(current['cases'][:77], original['cases'])
        self.assertGreaterEqual(len(current['cases']), 78)

    def test_case_requires_the_closed_announcement_pair(self):
        catalog = json.loads(guide.CATALOG.read_bytes())
        case = next(c for c in catalog['cases'] if c['id'] == 'QA-78')
        self.assertEqual(case['feature'], 'adminGroupRelationsAnnouncementGui')
        manifest = json.loads((ROOT / 'evidence/s1-20261018/tanda-849/CANDIDATA849.json').read_bytes())
        pair = dict(bundle=manifest['distributions']['frontend']['app.js'], dll=manifest['distributions']['server']['RackClick.Server.dll'])
        self.assertIn(pair, catalog['adminGroupRelationsAnnouncementBuilds'])
        def available(ctx):
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']['QA-78']['available']
        ctx = dict(configured=True, roles=True, restored=True, origin='', **pair)
        self.assertTrue(available(ctx))
        for delta in [dict(bundle='future'), dict(dll='future'), dict(roles=False), dict(configured=False)]:
            self.assertFalse(available({**ctx, **delta}))
        self.assertFalse(available(guide.context(profile='manual')))

    def test_current_available_counts_and_generated_guides(self):
        catalog = json.loads(guide.CATALOG.read_bytes())
        for profile, count in [('manual', 8), ('rc9', 93)]:
            metadata = json.loads(guide.render(catalog, guide.context(profile=profile)).split('const guide=', 1)[1].split(';', 1)[0])['cases']
            self.assertEqual(sum(c['available'] for c in metadata.values()), count)
            self.assertTrue(guide.generate(check=True, profile=profile))


if __name__ == '__main__':
    unittest.main()
