"""Identity, immutable baseline and generation checks for the fifty selected B profiles."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).absolute().parents[2]
spec = importlib.util.spec_from_file_location('selected506b_unit', ROOT/'tools/build_hardware_selected506b.py')
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)


class Selected506BTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = dict(formatVersion=1, revision=compiler.REVISION, models=[])
        for name in compiler.SOURCES:
            cls.data['models'] += json.loads((ROOT/name).read_text(encoding='utf-8'))['models']
        cls.rows = cls.data['models']

    def test_fifty_exact_selected_models_and_closed_skus(self):
        self.assertEqual(len(compiler.selected_rows(ROOT, self.data)), 50)
        self.assertEqual([len(json.loads((ROOT/name).read_bytes())['models']) for name in compiler.SOURCES], [25, 25])
        for field in ('manufacturer', 'model', 'sku'):
            changed = copy.deepcopy(self.data)
            changed['models'][0]['definition']['identity'][field] += ' neighbour'
            with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506b_model_substitution'):
                compiler.selected_rows(ROOT, changed)
        changed = copy.deepcopy(self.data)
        changed['models'][0] = copy.deepcopy(changed['models'][1])
        with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506b_identity_invalid'):
            compiler.selected_rows(ROOT, changed)

    def test_previous428_including_selected_a_are_not_replaced(self):
        previous = compiler.previous_models(ROOT)
        self.assertEqual(len(previous), 428)
        self.assertEqual(sum(bool(model['identity']['manufacturer']) for model in previous), 423)
        self.assertEqual(sum(model['revision'] == 'selected506a-20261101-v1' for model in previous), 17)
        self.assertTrue({model['key'] for model in previous}.isdisjoint({r['definition']['key'] for r in self.rows}))
        self.assertEqual(len({r['definition']['key'] for r in self.rows}), 50)

    def test_both_faces_cover_the_same_physical_group_and_ordinal_once(self):
        for row in self.rows:
            compiler.b.validate_model(row)
            expected = [(g['key'], n, g['face']) for g in row['definition']['groups'] for n in range(1, g['count']+1)]
            actual = [(socket['groupKey'], socket['ordinal'], face) for face, visual in row['visual']['faces'].items()
                      for socket in compiler.b.expand(visual)]
            self.assertCountEqual(actual, expected)
            self.assertEqual(len(set(actual)), len(actual))
            self.assertTrue(all(group['count'] <= 96 for group in row['definition']['groups']))

    def test_reference_assets_keep_the_authors_bytes(self):
        for row in self.rows:
            for asset in row['evidence']['referenceAssets']:
                path = (ROOT/asset['path']).resolve()
                self.assertTrue(path.is_relative_to(ROOT.resolve()))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset['sha256'])

    def test_bad_banks_connectors_roles_revisions_and_u_never_generate(self):
        reference = next(row for row in self.rows if row['definition']['kind'] == 'rack'
                         and row['visual']['faces']['front']['banks'])
        for mutate in (
            lambda r: r['visual']['faces']['front']['banks'][0].update(groupKey='not-the-original'),
            lambda r: r['visual']['faces']['front']['banks'][0].update(rows=[[1, 1]]),
            lambda r: r['definition']['groups'][0].update(type='qsfp'),
            lambda r: r['definition']['groups'][0].update(powerRole='outlet'),
            lambda r: r['definition'].update(revision='latest'),
            lambda r: r['definition'].update(rackUnits=0)):
            row = copy.deepcopy(reference)
            mutate(row)
            with self.assertRaises(compiler.c.CatalogError):
                compiler.b.validate_model(row)

    def test_template_limit_does_not_exceed_the_materializer_limit(self):
        changed = copy.deepcopy(self.data)
        row = changed['models'][0]
        group = copy.deepcopy(next(g for g in row['definition']['groups'] if g['type'] == 'rj45'))
        group.update(count=97, face='front')
        row['definition']['groups'] = [group]
        row['visual']['faces']['front'].update(width=2000, banks=[dict(groupKey=group['key'], rows=[list(range(1, 98))],
            x=20, y=40, dx=10, dy=0, w=8, h=20)])
        row['visual']['faces']['rear']['banks'] = []
        compiler.b.validate_model(row)
        with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506b_runtime_group_limit'):
            compiler.selected_rows(ROOT, changed)

    def test_reproducible_check_and_frozen_previous_schema29(self):
        one = compiler.compile_catalog(ROOT)
        self.assertEqual(one, compiler.compile_catalog(ROOT))
        self.assertEqual(compiler.run(ROOT, False)['targetSchema'], 30)
        prior_spec = importlib.util.spec_from_file_location('selected506b_previous29', ROOT/'tools/build_hardware_selected506a.py')
        prior = importlib.util.module_from_spec(prior_spec)
        prior_spec.loader.exec_module(prior)
        self.assertEqual(prior.run(ROOT, False)['targetSchema'], 29)

    def test_tampering_source_baseline_lock_or_output_is_rejected_in_isolation(self):
        names = [*compiler.SOURCES, compiler.SELECTION, compiler.PLAN, compiler.LOCK, compiler.BASE,
                 compiler.SHARED, compiler.TOOL, *compiler.prior_names(ROOT)]
        with tempfile.TemporaryDirectory(prefix='selected506b-contract-', dir=ROOT/'.local') as temporary:
            isolated = Path(temporary).resolve()
            self.assertTrue(isolated.is_relative_to((ROOT/'.local').resolve()))
            for name in names:
                target = isolated/name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/name, target)
            self.assertEqual(compiler.run(isolated, True)['targetSchema'], 30)
            self.assertEqual(compiler.run(isolated, False)['targetSchema'], 30)
            cases = [(compiler.SOURCES[0], 'selected506b_input_changed'),
                     ('development/hardware/selected506a/aruba.json', 'selected506b_baseline_changed'),
                     (compiler.LOCK, 'selected506b_lock_not_reviewed'),
                     (compiler.FRONTEND, 'catalog_stale')]
            for name, code in cases:
                target = isolated/name
                original = target.read_bytes()
                target.write_bytes(original+b'\n')
                with self.assertRaisesRegex(compiler.c.CatalogError, code):
                    compiler.run(isolated, False)
                target.write_bytes(original)
            self.assertEqual(compiler.run(isolated, False)['targetSchema'], 30)


if __name__ == '__main__':
    unittest.main()
