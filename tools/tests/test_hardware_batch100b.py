"""Fourth batch authoring: old catalogue exclusion, complete faces and rejection."""
from pathlib import Path
import copy,importlib.util,json,unittest,hashlib,xml.etree.ElementTree as ET
ROOT=Path(__file__).absolute().parents[2]
spec=importlib.util.spec_from_file_location('batch100b_tests',ROOT/'tools/build_hardware_batch100b.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

class Batch100BTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=[row for source in g.SOURCES for row in json.loads((ROOT/source).read_text(encoding='utf-8'))['models']]

    def test_hundred_new_models_not_ram_variants_or_old_keys(self):
        old=g.previous_models(ROOT);self.assertEqual(len(old),211);self.assertEqual(len(self.rows),100)
        new=[r['definition'] for r in self.rows]
        self.assertEqual(len({m['key'] for m in new}),100)
        self.assertEqual(len({(m['identity']['manufacturer'],m['identity']['model']) for m in new}),100)
        self.assertFalse({m['key'] for m in new}&{m['key'] for m in old})
        self.assertFalse({(m['identity']['manufacturer'],m['identity']['model']) for m in new}&{(m['identity']['manufacturer'],m['identity']['model']) for m in old})

    def test_two_hundred_faces_exactly_cover_all_typed_endpoints(self):
        for row in self.rows:
            with self.subTest(model=row['definition']['key']):
                self.assertIs(g.b.validate_model(row),row)
                d=row['definition'];actual=[]
                for face,v in row['visual']['faces'].items():
                    actual += [(p['groupKey'],p['ordinal'],face) for p in g.b.expand(v)]
                expected=[(p['key'],i,p['face']) for p in d['groups'] for i in range(1,p['count']+1)]
                self.assertCountEqual(actual,expected)

    def test_malformed_geometry_never_silently_maps_another_port(self):
        row=next(r for r in self.rows if r['visual']['faces']['rear']['banks'])
        for mutate in [lambda r:r['definition'].update(revision='batch50-20261030-v1'),
                       lambda r:r['definition']['provenance'].update(source=17),
                       lambda r:r['visual']['faces']['front']['decorations'].append(17),
                       lambda r:r['visual']['faces']['rear']['banks'][0].update(groupKey='unknown'),
                       lambda r:r['visual']['faces']['rear']['banks'][0].update(rows=[[1,1]]),
                       lambda r:r['visual']['faces']['rear']['banks'][0].update(x=float('nan')),
                       lambda r:r['definition']['groups'][0].update(powerRole='outlet')]:
            bad=copy.deepcopy(row);mutate(bad)
            with self.assertRaises(g.c.CatalogError):g.b.validate_model(bad)

    def test_generated_files_are_current_and_schema24_remains_verified(self):
        result=g.run(ROOT,False);self.assertEqual(result['targetSchema'],27)
        spec=importlib.util.spec_from_file_location('independent_historical_compiler',ROOT/'tools/build_hardware_batch50.py')
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        self.assertEqual(old.run(ROOT,False)['targetSchema'],24)
        spec=importlib.util.spec_from_file_location('independent_schema25_compiler',ROOT/'tools/build_hardware_batch50b.py')
        prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
        self.assertEqual(prior.run(ROOT,False)['targetSchema'],25)
        spec=importlib.util.spec_from_file_location('independent_schema26_compiler',ROOT/'tools/build_hardware_batch100.py')
        prior26=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior26)
        self.assertEqual(prior26.run(ROOT,False)['targetSchema'],26)

    def test_build_guard_reads_each_pinned_input_from_its_own_path(self):
        target=ROOT/g.TARGETS;tree=ET.fromstring(target.read_bytes())
        for item in tree.iter('_Batch100BInput'):
            include=item.attrib['Include'];self.assertTrue(include.startswith('$(MSBuildThisFileDirectory)'))
            path=(target.parent/include.removeprefix('$(MSBuildThisFileDirectory)')).resolve()
            self.assertTrue(path.is_relative_to(ROOT))
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),item.findtext('ExpectedHash'),path.relative_to(ROOT).as_posix())


if __name__=='__main__':unittest.main()
