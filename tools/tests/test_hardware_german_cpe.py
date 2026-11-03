"""Focused new catalogue44 negatives; no VM, installed database or credentials."""
import copy, importlib.util, json, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('german_cpe_test_compiler',ROOT/'tools/build_hardware_german_cpe.py')
compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)

class GermanCpeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=compiler.validated_rows(ROOT)
    def test_six_explicit_models_and_51_real_endpoints(self):
        self.assertEqual(len(self.rows),6)
        self.assertEqual(sum(g['count'] for r in self.rows for g in r['definition']['groups']),51)
    def test_prior_506_selection_not_redefined(self):
        selected=json.loads((ROOT/'development/hardware/selected-models-506.json').read_bytes())
        self.assertEqual(len(selected['models']),506)
        self.assertTrue(all(not r['definition']['key'].startswith('selected-') for r in self.rows))
    def test_7590_v2_has_no_invented_isdn(self):
        d=next(r['definition'] for r in self.rows if r['definition']['key']=='fritz-7590ax-v2-de')
        self.assertEqual(d['identity']['sku'],'20002998')
        self.assertFalse(any(g['type']=='isdn' for g in d['groups']))
    def test_usb_not_console_and_dsl_not_ethernet(self):
        for r in self.rows:
            groups=r['definition']['groups']
            self.assertTrue(any(g['type']=='dsl' for g in groups))
            self.assertFalse(any(g['type']=='console' for g in groups))
            for g in groups:
                if g['key'].startswith('usb'):self.assertEqual(g['type'],'usb_a')
                if g['type']=='dsl':self.assertTrue(g['physicalConnector'].startswith('dsl-'))
    def test_tae_is_explicit_voice_and_lines_not_doubled(self):
        for r in self.rows:
            for g in r['definition']['groups']:
                if g.get('physicalConnector')=='voice-tae':
                    self.assertEqual(g['type'],'telephony')
                    self.assertTrue(any('alternativ' in x.lower() for x in r['evidence']['limits']))
    def test_all_fronts_have_no_invented_network_ports(self):
        for r in self.rows:self.assertEqual(r['visual']['faces']['front']['banks'],[])
    def test_port_missing_rejected(self):
        r=copy.deepcopy(self.rows[-1]);r['visual']['faces']['rear']['banks'].pop()
        with self.assertRaises(ValueError):compiler.h.validate_model(r,compiler.REVISION)
    def test_duplicate_port_geometry_rejected(self):
        r=copy.deepcopy(self.rows[0]);f=r['visual']['faces']['rear'];f['banks'].append(copy.deepcopy(f['banks'][0]))
        with self.assertRaises(ValueError):compiler.h.validate_model(r,compiler.REVISION)
    def test_false_dsl_descriptor_rejected(self):
        r=copy.deepcopy(self.rows[0]);next(g for g in r['definition']['groups'] if g['type']=='dsl')['physicalConnector']='voice-rj11'
        with self.assertRaises(ValueError):compiler.h.validate_model(r,compiler.REVISION)
    def test_wrong_power_role_rejected(self):
        r=copy.deepcopy(self.rows[0]);next(g for g in r['definition']['groups'] if g['type']=='power_dc')['powerRole']='unspecified'
        with self.assertRaises(ValueError):compiler.h.validate_model(r,compiler.REVISION)
    def test_incomplete_dimension_rejected(self):
        r=copy.deepcopy(self.rows[0]);r['definition']['dimensionsMm']['depth']=None
        with self.assertRaises(ValueError):compiler.h.validate_model(r,compiler.REVISION)
    def test_wrong_revision_rejected(self):
        with self.assertRaises(ValueError):compiler.h.validate_model(self.rows[0],'latest')
    def test_generator_deterministic_and_current(self):
        first=compiler.compile_catalog(ROOT);second=compiler.compile_catalog(ROOT)
        self.assertEqual(first,second)
        for n,v in first.items():self.assertEqual((ROOT/n).read_bytes(),v)
    def test_migration_is_additive_usb_and_tae(self):
        sql=compiler.compile_catalog(ROOT)[compiler.SQL].decode()
        self.assertIn("'usb_a','usb_c'",sql)
        self.assertIn("'voice-rj11','voice-tae'",sql)
        self.assertNotIn('DELETE FROM',sql)
        self.assertNotIn('UPDATE hardware_definition SET sealed=false',sql)

if __name__=='__main__':unittest.main()
