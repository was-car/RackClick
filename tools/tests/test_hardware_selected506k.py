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
spec = importlib.util.spec_from_file_location('selected506k_unit', ROOT/'tools/build_hardware_selected506k.py')
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)


class Selected506KTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = dict(formatVersion=1, revision=compiler.REVISION, models=[])
        for name in compiler.SOURCES:
            cls.data['models'] += json.loads((ROOT/name).read_bytes())['models']
        cls.rows = cls.data['models']
        cls.panels = [row for row in cls.rows if row['definition']['passthrough'] is not None]
        cls.aps = [row for row in cls.rows if row['definition']['kind']=='desktop']

    def test_closed_plan_identities_skus_mounts_and_duplicates(self):
        plan = json.loads((ROOT/compiler.PLAN).read_bytes())
        self.assertEqual(len(compiler.selected_rows(ROOT, self.data)), plan['models'])
        self.assertEqual([len(json.loads((ROOT/name).read_bytes())['models']) for name in compiler.SOURCES],
                         [len(plan['authoring'][name]) for name in compiler.FAMILIES])
        for field in ('manufacturer', 'model', 'sku'):
            changed = copy.deepcopy(self.data)
            changed['models'][0]['definition']['identity'][field] += ' neighbour'
            with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506k_model_substitution'):
                compiler.selected_rows(ROOT, changed)
        for row in self.rows:
            model = row['definition']
            self.assertEqual((model['kind'], model['rackUnits']), compiler.MOUNTS[model['key'].removeprefix('selected-')])
        changed = copy.deepcopy(self.data)
        model = changed['models'][0]['definition']
        model.update(kind='desktop', rackUnits=0)
        with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506k_mount_substitution'):
            compiler.selected_rows(ROOT, changed)
        changed = copy.deepcopy(self.data)
        for field in ('manufacturer', 'sku'):
            changed['models'][0]['definition']['identity'][field] = changed['models'][1]['definition']['identity'][field]
        with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506k_duplicate_sku'):
            compiler.selected_rows(ROOT, changed)
        changed['models'][0] = copy.deepcopy(changed['models'][1])
        with self.assertRaisesRegex(compiler.c.CatalogError, 'selected506k_identity_invalid'):
            compiler.selected_rows(ROOT, changed)

    def test_previous752_and_their_revisions_are_not_replaced(self):
        previous = compiler.previous_models(ROOT)
        self.assertEqual(len(previous), 752)
        self.assertEqual(sum(bool(model['identity']['manufacturer']) for model in previous), 747)
        self.assertEqual(sum(model['revision'] == 'selected506j-20261101-v1' for model in previous), 13)
        self.assertEqual(len({(model['key'], model['revision']) for model in previous}), 752)
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
        row['definition']['groups'][1].pop('physicalConnector', None)  # isolate continuity, not a descriptor/type mismatch
        with self.assertRaisesRegex(compiler.c.CatalogError, 'family_v2_continuity_invalid'):
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

    def test_native_types_descriptors_empty_accessories_and_legacy_limits(self):
        self.assertTrue(self.panels and self.aps)
        for row in self.panels:
            before=copy.deepcopy(row)
            self.assertIs(compiler.validate_model(row),row)
            self.assertEqual(row,before)
            rule=row['definition']['passthrough']
            groups={g['key']:g for g in row['definition']['groups']}
            self.assertEqual((groups[rule['frontGroup']]['type'],groups[rule['rearGroup']]['type']),('rj45','idc'))
            self.assertFalse(rule['tracingAvailable'])
            with self.assertRaises(compiler.c.CatalogError):
                compiler.engine.engine.validate_model(row,compiler.REVISION)
        for row in self.rows:
            for group in row['definition']['groups']:
                compiler.engine.validate_physical_connector(group['type'],group.get('physicalConnector'))
        for raw,values in compiler.engine.PHYSICAL_CONNECTORS.items():
            for value in values:self.assertEqual(compiler.engine.validate_physical_connector(raw,value),value)
        for raw,value in [('rj45','serial-8p8c'),('console','idc-110'),('idc','iec-c13'),('power','IEC-C13')]:
            with self.assertRaises(compiler.c.CatalogError):compiler.engine.validate_physical_connector(raw,value)
        empty=[r for r in self.rows if not r['definition']['groups']]
        self.assertEqual(len(empty),10)
        for row in empty:
            self.assertIs(compiler.validate_model(row),row)
            self.assertEqual(row['definition']['slots'],[])
            self.assertTrue(all(face['banks']==[] for face in row['visual']['faces'].values()))
        row=copy.deepcopy(self.aps[0]);group=row['definition']['groups'][0]
        group['count']=97
        with self.assertRaises(compiler.c.CatalogError):compiler.validate_model(row)
        self.assertEqual(compiler.support_models(ROOT)[0]['slots'][0]['dimensionsMm']['height'],280)

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
        self.assertEqual(sql.count('INSERT INTO hardware_connector_template '),sum(g.get('physicalConnector') is not None for r in self.rows for g in r['definition']['groups']))
        self.assertIn('hardware_connector_validate BEFORE INSERT OR UPDATE ON', (ROOT/compiler.BASE).read_text(encoding='utf-8'))
        for row in self.rows:
            model = row['definition']
            profile = profiles[model['key']]
            self.assertEqual(profile.get('passthrough'), model['passthrough'])
            self.assertEqual([g.get('physicalConnector') for g in profile['groups']], [g.get('physicalConnector') for g in model['groups']])
            for group in model['groups']:
                if group.get('physicalConnector') is not None:
                    self.assertIn('PhysicalConnector = '+json.dumps(group['physicalConnector']),server)
                    self.assertIn(compiler.g.literal(group['physicalConnector']),sql)
            self.assertEqual([group['powerRole'] for group in profile['groups']], [group['powerRole'] for group in model['groups']])
            self.assertIn(compiler.c.sha(compiler.c.canonical(model)), server)
            continuity = model['passthrough']
            if continuity:
                self.assertIn('Passthrough = new('+', '.join([json.dumps(continuity['frontGroup']),
                    json.dumps(continuity['rearGroup']), str(continuity['count'])])+')', server)
                marker = 'INSERT INTO hardware_passthrough (profile_key, revision, front_group_key, rear_group_key, port_count) VALUES ('+compiler.g.literal(model['key'])
                seal = 'UPDATE hardware_definition SET sealed=true WHERE profile_key='+compiler.g.literal(model['key'])
                self.assertLess(sql.index(marker), sql.index(seal))
        self.assertEqual(compiler.run(ROOT, False)['targetSchema'], 41)
        old_spec = importlib.util.spec_from_file_location('j_previous_i', ROOT/'tools/build_hardware_selected506j.py')
        old = importlib.util.module_from_spec(old_spec)
        old_spec.loader.exec_module(old)
        self.assertEqual(old.run(ROOT, False)['targetSchema'], 39)

    def test_tampered_sources_baseline_helper_lock_and_output_are_rejected(self):
        names = [*compiler.SOURCES, compiler.SELECTION, compiler.LINKS, compiler.PLAN, compiler.LOCK, compiler.BASE, compiler.BASELINE, compiler.SUPPORT,
                 compiler.SHARED, compiler.CORE, *compiler.TRANSITIVE, compiler.TOOL, *compiler.prior_names(ROOT)]
        (ROOT/'.local').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='selected506k-contract-', dir=ROOT/'.local') as temporary:
            isolated = Path(temporary).resolve()
            self.assertTrue(isolated.is_relative_to((ROOT/'.local').resolve()))
            for name in names:
                target = isolated/name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/name, target)
            self.assertEqual(compiler.run(isolated, True)['targetSchema'], 41)
            self.assertEqual(compiler.run(isolated, False)['targetSchema'], 41)
            cases = [(compiler.SOURCES[0], 'selected506k_input_changed'),
                     ('development/hardware/selected506j/access-points.json', 'selected506k_baseline_changed'),
                     (compiler.SHARED, 'selected506k_input_changed'), (compiler.LOCK, 'selected506k_lock_not_reviewed'),
                     (compiler.FRONTEND, 'catalog_stale')]
            for name, code in cases:
                target = isolated/name
                original = target.read_bytes()
                target.write_bytes(original+b'\n')
                with self.assertRaisesRegex(compiler.c.CatalogError, code):
                    compiler.run(isolated, False)
                target.write_bytes(original)
            self.assertEqual(compiler.run(isolated, False)['targetSchema'], 41)


if __name__ == '__main__':
    unittest.main()
