"""Identity, immutable baseline and generation checks for the five selected I profiles."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).absolute().parents[2]
spec = importlib.util.spec_from_file_location('selected506i_unit', ROOT/'tools/build_hardware_selected506i.py')
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)


class Selected506ITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = dict(formatVersion=1, revision=compiler.REVISION, models=[])
        for name in compiler.SOURCES:
            cls.data['models'] += json.loads((ROOT/name).read_text(encoding='utf-8'))['models']
        cls.rows = cls.data['models']

    def test_five_exact_selected_models_and_closed_skus(self):
        self.assertEqual(len(compiler.selected_rows(ROOT, self.data)), 5)
        self.assertEqual([len(json.loads((ROOT/name).read_bytes())['models']) for name in compiler.SOURCES], [3, 2])
        for field in ('manufacturer', 'model', 'sku'):
            changed = copy.deepcopy(self.data)
            changed['models'][0]['definition']['identity'][field] += ' neighbour'
            with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506i_model_substitution'):
                compiler.selected_rows(ROOT, changed)
        changed = copy.deepcopy(self.data)
        definition = changed['models'][0]['definition']
        definition.update(kind='desktop' if definition['kind'] == 'rack' else 'rack',
                          rackUnits=0 if definition['kind'] == 'rack' else 1)
        with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506i_mount_substitution'):
            compiler.selected_rows(ROOT, changed)
        # The selected PA-5580 occupies three U; the Huawei occupies one U.
        # Their historical inventory heights must never replace the closed map.
        for identifier, expected_u, wrong_u in [('palo-alto-pa-5580', 3, 1), ('nb-5bbf29fdc1f2fb3c', 1, 2)]:
            row = next(r for r in self.rows if r['definition']['key'] == 'selected-'+identifier)
            self.assertEqual(row['definition']['rackUnits'], expected_u)
            changed = copy.deepcopy(self.data)
            next(r for r in changed['models'] if r['definition']['key'] == 'selected-'+identifier)['definition']['rackUnits'] = wrong_u
            with self.assertRaises(compiler.c.CatalogError):
                compiler.selected_rows(ROOT, changed)
        changed = copy.deepcopy(self.data)
        for field in ('manufacturer', 'sku'):
            changed['models'][0]['definition']['identity'][field] = changed['models'][1]['definition']['identity'][field]
        with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506i_duplicate_sku'):
            compiler.selected_rows(ROOT, changed)
        changed = copy.deepcopy(self.data)
        changed['models'][0] = copy.deepcopy(changed['models'][1])
        with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506i_identity_invalid'):
            compiler.selected_rows(ROOT, changed)

    def test_previous734_including_selected_a_and_b_are_not_replaced(self):
        previous = compiler.previous_models(ROOT)
        self.assertEqual(len(previous), 734)
        self.assertEqual(sum(bool(model['identity']['manufacturer']) for model in previous), 729)
        self.assertEqual(sum(model['revision'] == 'selected506a-20261101-v1' for model in previous), 17)
        self.assertEqual(sum(model['revision'] == 'selected506b-20261101-v1' for model in previous), 50)
        self.assertEqual(sum(model['revision'] == 'selected506c-20261101-v1' for model in previous), 50)
        self.assertEqual(sum(model['revision'] == 'selected506d-20261101-v1' for model in previous), 50)
        self.assertEqual(sum(model['revision'] == 'selected506e-20261101-v1' for model in previous), 50)
        self.assertEqual(sum(model['revision'] == 'selected506f-20261101-v1' for model in previous), 50)
        self.assertEqual(sum(model['revision'] == 'selected506g-20261101-v1' for model in previous), 50)
        self.assertEqual(sum(model['revision'] == 'selected506h-20261101-v1' for model in previous), 6)
        self.assertTrue({model['key'] for model in previous}.isdisjoint({r['definition']['key'] for r in self.rows}))
        self.assertEqual(len({r['definition']['key'] for r in self.rows}), 5)

    def test_both_faces_cover_the_same_physical_group_and_ordinal_once(self):
        for row in self.rows:
            compiler.validate_model(row)
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
            lambda r: r['definition']['groups'][0].update(type='qsfp_dd'),
            lambda r: r['definition']['groups'][0].update(powerRole='outlet'),
            lambda r: r['definition'].update(revision='latest'),
            lambda r: r['definition'].update(rackUnits=0),
            lambda r: r['definition'].update(kind='rackContainer')):
            row = copy.deepcopy(reference)
            mutate(row)
            with self.assertRaises(compiler.c.CatalogError):
                compiler.validate_model(row)

        # Raw Unicode scalar boundary at the actual Domain.Names group limit.
        for name in ('A'*100, '\U0001f600'*100, 'e\u0301'*50):
            row = copy.deepcopy(reference)
            row['definition']['groups'][0]['name'] = name
            before = copy.deepcopy(row)
            self.assertIs(compiler.validate_model(row), row)
            self.assertEqual(row, before)
        for name in ('A'*101, '\U0001f600'*101):
            row = copy.deepcopy(reference)
            row['definition']['groups'][0]['name'] = name
            with self.assertRaisesRegex(compiler.c.CatalogError, 'physical_v3_group_name_invalid'):
                compiler.validate_model(row)
        for name in ('', '   ', 'A\x7fB', 'A\x85B', 'A\x1fB', '\ud800'):
            row = copy.deepcopy(reference)
            row['definition']['groups'][0]['name'] = name
            with self.assertRaises(compiler.c.CatalogError):
                compiler.validate_model(row)

    def test_v3_retains_real_types_without_mutation_and_legacy_stays_closed(self):
        reference = copy.deepcopy(self.rows[0])
        group_index = next(i for i, group in enumerate(reference['definition']['groups']) if group['type'] != 'power')
        for kind in ('sfp56', 'qsfpdd'):
            row = copy.deepcopy(reference)
            row['definition']['groups'][group_index]['type'] = kind
            before = copy.deepcopy(row)
            self.assertIs(compiler.validate_model(row), row)
            self.assertEqual(row, before)
            self.assertEqual(row['definition']['groups'][group_index]['type'], kind)
            with self.assertRaises(compiler.b.c.CatalogError):
                compiler.b.validate_model(row)
        for kind in ('qsfp_dd', 'usb_a', 'console', 'rj45_poe', 'unknown'):
            row = copy.deepcopy(reference)
            row['definition']['groups'][group_index]['type'] = kind
            with self.assertRaisesRegex(compiler.c.CatalogError, 'physical_v3_connector_unsupported'):
                compiler.validate_model(row)
        prior_spec = importlib.util.spec_from_file_location('physical_v2_old_wrapper', ROOT/'tools/build_hardware_selected506c.py')
        prior = importlib.util.module_from_spec(prior_spec)
        prior_spec.loader.exec_module(prior)
        prior_data = dict(formatVersion=1, revision=prior.REVISION, models=[])
        for name in prior.SOURCES:
            prior_data['models'] += json.loads((ROOT/name).read_bytes())['models']
        prior_data['models'][0]['definition']['groups'][0]['type'] = 'qsfp'
        with self.assertRaises(prior.c.CatalogError):
            prior.selected_rows(ROOT, prior_data)
        row = copy.deepcopy(next(r for r in self.rows if any(g['type'] == 'rj45' for g in r['definition']['groups'])))
        group = copy.deepcopy(next(g for g in row['definition']['groups'] if g['type'] == 'rj45'))
        group.update(count=97, face='front')
        row['definition']['groups'] = [group]
        row['visual']['faces']['front'].update(width=2000, banks=[dict(groupKey=group['key'], rows=[list(range(1, 98))],
            x=20, y=40, dx=10, dy=0, w=8, h=20)])
        row['visual']['faces']['rear']['banks'] = []
        compiler.b.validate_model(row)
        before = copy.deepcopy(row)
        with self.assertRaisesRegex(compiler.c.CatalogError, 'physical_v2_runtime_group_limit'):
            compiler.validate_model(row)
        self.assertEqual(row, before)

    def test_reproducible_check_and_frozen_catalog37(self):
        one = compiler.compile_catalog(ROOT)
        self.assertEqual(one, compiler.compile_catalog(ROOT))
        sql = one[compiler.SQL].decode('utf-8')
        self.assertNotIn('ALTER TABLE', sql)
        self.assertNotIn('CONSTRAINT', sql)
        profiles = {p['key']: p for cat in json.loads(one[compiler.FRONTEND]) for p in cat['profiles']}
        types = set()
        for row in self.rows:
            model = row['definition']
            self.assertEqual([g['type'] for g in profiles[model['key']]['groups']], [g['type'] for g in model['groups']])
            for group in model['groups']:
                types.add(group['type'])
                self.assertIn(('new('+json.dumps(group['key'])+', '+json.dumps(group['type'])+',').encode(), one[compiler.SERVER])
        for kind in types:
            self.assertIn("E'"+kind+"'", sql[sql.index('INSERT INTO hardware_definition'):])

        self.assertEqual(compiler.run(ROOT, False)['targetSchema'], 38)
        prior_spec = importlib.util.spec_from_file_location('selected506i_previous37', ROOT/'tools/build_hardware_selected506h.py')
        prior = importlib.util.module_from_spec(prior_spec)
        prior_spec.loader.exec_module(prior)
        self.assertEqual(prior.run(ROOT, False)['targetSchema'], 37)

    def test_tampering_source_baseline_lock_or_output_is_rejected_in_isolation(self):
        names = [*compiler.SOURCES, compiler.SELECTION, compiler.LINKS, compiler.PLAN, compiler.LOCK, compiler.BASE,
                 compiler.SHARED, compiler.CORE, *compiler.TRANSITIVE, compiler.TOOL, *compiler.prior_names(ROOT)]
        (ROOT/'.local').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='selected506i-contract-', dir=ROOT/'.local') as temporary:
            isolated = Path(temporary).resolve()
            self.assertTrue(isolated.is_relative_to((ROOT/'.local').resolve()))
            for name in names:
                target = isolated/name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/name, target)
            self.assertEqual(compiler.run(isolated, True)['targetSchema'], 38)
            self.assertEqual(compiler.run(isolated, False)['targetSchema'], 38)
            cases = [(compiler.SOURCES[0], 'selected506i_input_changed'),
                     ('development/hardware/selected506h/aruba.json', 'selected506i_baseline_changed'),
                     (compiler.LOCK, 'selected506i_lock_not_reviewed'),
                     (compiler.FRONTEND, 'catalog_stale')]
            for name, code in cases:
                target = isolated/name
                original = target.read_bytes()
                target.write_bytes(original+b'\n')
                with self.assertRaisesRegex(compiler.c.CatalogError, code):
                    compiler.run(isolated, False)
                target.write_bytes(original)
            self.assertEqual(compiler.run(isolated, False)['targetSchema'], 38)


if __name__ == '__main__':
    unittest.main()
