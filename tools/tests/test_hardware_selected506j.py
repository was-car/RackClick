"""Closed family identities, descriptive continuity and reproducible J generation."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).absolute().parents[2]
spec = importlib.util.spec_from_file_location('selected506j_unit', ROOT/'tools/build_hardware_selected506j.py')
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)


class Selected506JTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = dict(formatVersion=1, revision=compiler.REVISION, models=[])
        for name in compiler.SOURCES:
            cls.data['models'] += json.loads((ROOT/name).read_bytes())['models']
        cls.rows = cls.data['models']
        cls.panels = [row for row in cls.rows if row['definition']['passthrough'] is not None]
        cls.aps = [row for row in cls.rows if row['definition']['passthrough'] is None]

    def test_closed_plan_identities_skus_mounts_and_duplicates(self):
        plan = json.loads((ROOT/compiler.PLAN).read_bytes())
        self.assertEqual(len(compiler.selected_rows(ROOT, self.data)), plan['models'])
        self.assertEqual([len(json.loads((ROOT/name).read_bytes())['models']) for name in compiler.SOURCES],
                         [len(plan['authoring'][name]) for name in compiler.FAMILIES])
        for field in ('manufacturer', 'model', 'sku'):
            changed = copy.deepcopy(self.data)
            changed['models'][0]['definition']['identity'][field] += ' neighbour'
            with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506j_model_substitution'):
                compiler.selected_rows(ROOT, changed)
        for row in self.rows:
            model = row['definition']
            self.assertEqual((model['kind'], model['rackUnits']), compiler.MOUNTS[model['key'].removeprefix('selected-')])
        changed = copy.deepcopy(self.data)
        model = changed['models'][0]['definition']
        model.update(kind='desktop', rackUnits=0)
        with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506j_mount_substitution'):
            compiler.selected_rows(ROOT, changed)
        changed = copy.deepcopy(self.data)
        for field in ('manufacturer', 'sku'):
            changed['models'][0]['definition']['identity'][field] = changed['models'][1]['definition']['identity'][field]
        with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506j_duplicate_sku'):
            compiler.selected_rows(ROOT, changed)
        changed['models'][0] = copy.deepcopy(changed['models'][1])
        with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506j_identity_invalid'):
            compiler.selected_rows(ROOT, changed)

    def test_previous739_and_their_revisions_are_not_replaced(self):
        previous = compiler.previous_models(ROOT)
        self.assertEqual(len(previous), 739)
        self.assertEqual(sum(bool(model['identity']['manufacturer']) for model in previous), 734)
        self.assertEqual(sum(model['revision'] == 'selected506i-20261101-v1' for model in previous), 5)
        self.assertEqual(len({(model['key'], model['revision']) for model in previous}), 739)
        self.assertTrue({model['key'] for model in previous}.isdisjoint(row['definition']['key'] for row in self.rows))

    def test_faces_cover_each_original_group_and_ordinal_once(self):
        for row in self.rows:
            before = copy.deepcopy(row)
            self.assertIs(compiler.validate_model(row), row)
            self.assertEqual(row, before)
            expected = [(group['key'], n, group['face']) for group in row['definition']['groups'] for n in range(1, group['count']+1)]
            actual = [(socket['groupKey'], socket['ordinal'], face) for face, visual in row['visual']['faces'].items()
                      for socket in compiler.engine.expand(visual)]
            self.assertCountEqual(actual, expected)
            self.assertEqual(len(set(actual)), len(actual))
            self.assertTrue(all(group['count'] <= 96 for group in row['definition']['groups']))
            self.assertTrue(all(socket['w'] >= 24 and socket['h'] >= 24 for face in row['visual']['faces'].values()
                                for socket in compiler.engine.expand(face)))

    def test_reference_bytes_are_pinned_by_the_authors(self):
        for row in self.rows:
            for asset in row['evidence']['referenceAssets']:
                path = (ROOT/asset['path']).resolve()
                self.assertTrue(path.is_relative_to(ROOT.resolve()))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset['sha256'])

    def test_bad_geometry_names_connectors_roles_and_continuity_never_generate(self):
        reference = self.panels[0]
        changes = [
            lambda row: row['visual']['faces']['front']['banks'][0].update(groupKey='other'),
            lambda row: row['visual']['faces']['front']['banks'][0].update(rows=[[1, 1]]),
            lambda row: row['definition']['groups'][0].update(type='idc'),
            lambda row: row['definition']['groups'][0].update(powerRole='outlet'),
            lambda row: row['definition'].update(revision='latest'),
            lambda row: row['definition'].update(rackUnits=0),
            lambda row: row['definition'].update(kind='rackContainer'),
            lambda row: row['definition']['passthrough'].update(mapping='1:1'),
            lambda row: row['definition']['passthrough'].update(tracingAvailable=True),
            lambda row: row['definition']['passthrough'].update(count=1),
            lambda row: row['definition']['passthrough'].update(count=True),
            lambda row: row['definition']['passthrough'].update(count=97),
            lambda row: row['definition']['passthrough'].update(rearGroup=row['definition']['passthrough']['frontGroup']),
            lambda row: row['definition']['passthrough'].update(frontGroup=[]),
            lambda row: row['definition']['passthrough'].update(extra='unsupported'),
        ]
        for change in changes:
            row = copy.deepcopy(reference)
            change(row)
            before = copy.deepcopy(row)
            with self.assertRaises(compiler.c.CatalogError):
                compiler.validate_model(row)
            self.assertEqual(row, before)
        # Same-type matching is physical; do not turn an SFP rear into copper.
        row = copy.deepcopy(reference)
        row['definition']['groups'][1]['type'] = 'sfp'
        with self.assertRaisesRegex(compiler.c.CatalogError, 'passive_family_connector_unsupported'):
            compiler.validate_model(row)
        for field in ('name', 'prefix'):
            for value in ('A'*100, '\U0001f600'*100, 'e\u0301'*50):
                row = copy.deepcopy(reference)
                row['definition']['groups'][0][field] = value
                self.assertIs(compiler.validate_model(row), row)
            for value in ('A'*101, '\U0001f600'*101, 'A\x85B', '\ud800'):
                row = copy.deepcopy(reference)
                row['definition']['groups'][0][field] = value
                with self.assertRaises(compiler.c.CatalogError):
                    compiler.validate_model(row)

    def test_original_continuity_is_preserved_and_v3_is_still_closed(self):
        for row in self.panels:
            model = row['definition']
            continuity = model['passthrough']
            before = copy.deepcopy(row)
            self.assertIs(compiler.validate_model(row), row)
            with self.assertRaisesRegex(compiler.c.CatalogError, 'batch50_structure_unsupported'):
                compiler.engine.engine.validate_model(row, compiler.REVISION)
            self.assertEqual(row, before)
            self.assertEqual(continuity['mapping'], 'one-to-one')
            self.assertIs(continuity['tracingAvailable'], False)
            self.assertEqual(len(model['groups']), 2)
            self.assertEqual({group['type'] for group in model['groups']}, {'rj45'})
        self.assertTrue(self.panels and self.aps)
        for row in self.aps:
            self.assertIs(compiler.engine.engine.validate_model(row, compiler.REVISION), row)
            self.assertEqual((row['definition']['kind'], row['definition']['rackUnits']), ('desktop', 0))
            self.assertEqual({group['type'] for group in row['definition']['groups']}, {'rj45'})
        row = copy.deepcopy(self.aps[0])
        group = row['definition']['groups'][0]
        group.update(count=97, face='rear')
        row['visual']['faces']['front']['banks'] = []
        row['visual']['faces']['rear'].update(width=2000, banks=[dict(groupKey=group['key'], rows=[list(range(1, 98))],
            x=20, y=40, dx=10, dy=0, w=8, h=20)])
        compiler.b.validate_model(row)
        with self.assertRaisesRegex(compiler.c.CatalogError, 'physical_v2_runtime_group_limit'):
            compiler.validate_model(row)

    def test_reproducible_writers_preserve_continuity_before_sealing(self):
        one = compiler.compile_catalog(ROOT)
        self.assertEqual(one, compiler.compile_catalog(ROOT))
        sql = one[compiler.SQL].decode('utf-8')
        server = one[compiler.SERVER].decode('ascii')
        profiles = {profile['key']: profile for cat in json.loads(one[compiler.FRONTEND]) for profile in cat['profiles']}
        self.assertNotIn('ALTER TABLE', sql)
        self.assertNotIn('CONSTRAINT', sql)
        self.assertNotIn('INSERT INTO inventory_connection', sql)
        self.assertEqual(sql.count('INSERT INTO hardware_passthrough '), len(self.panels))
        for row in self.rows:
            model = row['definition']
            profile = profiles[model['key']]
            self.assertEqual(profile.get('passthrough'), model['passthrough'])
            self.assertEqual([group['powerRole'] for group in profile['groups']], [group['powerRole'] for group in model['groups']])
            self.assertIn(compiler.c.sha(compiler.c.canonical(model)), server)
            continuity = model['passthrough']
            if continuity:
                self.assertIn('Passthrough = new('+', '.join([json.dumps(continuity['frontGroup']),
                    json.dumps(continuity['rearGroup']), str(continuity['count'])])+')', server)
                marker = 'INSERT INTO hardware_passthrough (profile_key, revision, front_group_key, rear_group_key, port_count) VALUES ('+compiler.g.literal(model['key'])
                seal = 'UPDATE hardware_definition SET sealed=true WHERE profile_key='+compiler.g.literal(model['key'])
                self.assertLess(sql.index(marker), sql.index(seal))
        self.assertEqual(compiler.run(ROOT, False)['targetSchema'], 39)
        old_spec = importlib.util.spec_from_file_location('j_previous_i', ROOT/'tools/build_hardware_selected506i.py')
        old = importlib.util.module_from_spec(old_spec)
        old_spec.loader.exec_module(old)
        self.assertEqual(old.run(ROOT, False)['targetSchema'], 38)

    def test_tampered_sources_baseline_helper_lock_and_output_are_rejected(self):
        names = [*compiler.SOURCES, compiler.SELECTION, compiler.LINKS, compiler.PLAN, compiler.LOCK, compiler.BASE,
                 compiler.SHARED, compiler.CORE, *compiler.TRANSITIVE, compiler.TOOL, *compiler.prior_names(ROOT)]
        (ROOT/'.local').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='selected506j-contract-', dir=ROOT/'.local') as temporary:
            isolated = Path(temporary).resolve()
            self.assertTrue(isolated.is_relative_to((ROOT/'.local').resolve()))
            for name in names:
                target = isolated/name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/name, target)
            self.assertEqual(compiler.run(isolated, True)['targetSchema'], 39)
            self.assertEqual(compiler.run(isolated, False)['targetSchema'], 39)
            cases = [(compiler.SOURCES[0], 'selected506j_input_changed'),
                     ('development/hardware/selected506i/enterprise.json', 'selected506j_baseline_changed'),
                     (compiler.SHARED, 'selected506j_input_changed'), (compiler.LOCK, 'selected506j_lock_not_reviewed'),
                     (compiler.FRONTEND, 'catalog_stale')]
            for name, code in cases:
                target = isolated/name
                original = target.read_bytes()
                target.write_bytes(original+b'\n')
                with self.assertRaisesRegex(compiler.c.CatalogError, code):
                    compiler.run(isolated, False)
                target.write_bytes(original)
            self.assertEqual(compiler.run(isolated, False)['targetSchema'], 39)


if __name__ == '__main__':
    unittest.main()
