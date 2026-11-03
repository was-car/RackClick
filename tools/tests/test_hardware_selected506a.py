"""Selection identity and physical endpoint invariants for the first 17 profiles."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).absolute().parents[2]
spec = importlib.util.spec_from_file_location('selected506a_unit', ROOT/'tools/build_hardware_selected506a.py')
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)


class Selected506ATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = dict(formatVersion=1, revision=compiler.REVISION, models=[])
        for name in compiler.SOURCES:
            cls.data['models'] += json.loads((ROOT/name).read_text(encoding='utf-8'))['models']
        cls.rows = cls.data['models']

    def test_every_new_model_is_one_of_the_requested_506_without_substitution(self):
        self.assertEqual(len(compiler.selected_rows(ROOT, self.data)), 17)
        changed = copy.deepcopy(self.data)
        changed['models'][0]['definition']['identity']['model'] += ' neighbour'
        with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506a_model_substitution'):
            compiler.selected_rows(ROOT, changed)
        changed = copy.deepcopy(self.data)
        changed['models'][0]['definition']['identity']['sku'] = 'neighbour'
        with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506a_model_substitution'):
            compiler.selected_rows(ROOT, changed)

    def test_no_previous_profile_is_replaced(self):
        previous = compiler.previous_models(ROOT)
        self.assertEqual(len(previous), 411)
        self.assertTrue({m['key'] for m in previous}.isdisjoint({r['definition']['key'] for r in self.rows}))
        self.assertEqual(len({r['definition']['key'] for r in self.rows}), 17)

    def test_both_faces_bind_every_endpoint_once(self):
        for row in self.rows:
            compiler.b.validate_model(row)
            expected = [(g['key'], n, g['face']) for g in row['definition']['groups'] for n in range(1, g['count']+1)]
            actual = [(s['groupKey'], s['ordinal'], side) for side, face in row['visual']['faces'].items()
                      for s in compiler.b.expand(face)]
            self.assertCountEqual(actual, expected)
            self.assertEqual(len(set(actual)), len(actual))

    def test_local_visual_references_retain_exact_bytes(self):
        for row in self.rows:
            for asset in row['evidence']['referenceAssets']:
                path = (ROOT/asset['path']).resolve()
                self.assertTrue(path.is_relative_to(ROOT.resolve()))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset['sha256'])

    def test_invalid_mapping_never_chooses_another_socket(self):
        for mutate in (lambda r: r['visual']['faces']['front']['banks'][0].update(groupKey='not-the-original'),
                       lambda r: r['visual']['faces']['front']['banks'][0].update(rows=[[1, 1]]),
                       lambda r: r['definition']['groups'][0].update(type='qsfp'),
                       lambda r: r['definition'].update(rackUnits=0)):
            row = copy.deepcopy(next(r for r in self.rows if r['definition']['kind'] == 'rack'))
            mutate(row)
            with self.assertRaises(compiler.c.CatalogError):
                compiler.b.validate_model(row)

    def test_reproducible_compilation_and_old_schema28(self):
        one = compiler.compile_catalog(ROOT)
        self.assertEqual(one, compiler.compile_catalog(ROOT))
        self.assertEqual(compiler.run(ROOT, False)['targetSchema'], 29)
        prior_spec = importlib.util.spec_from_file_location('selected506a_previous28', ROOT/'tools/build_hardware_batch100c.py')
        prior = importlib.util.module_from_spec(prior_spec)
        prior_spec.loader.exec_module(prior)
        self.assertEqual(prior.run(ROOT, False)['targetSchema'], 28)


if __name__ == '__main__':
    unittest.main()
