"""Schema45 room repeaters: geometry, physical contracts and deterministic pins."""
import copy, importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('repeaters_test_compiler',ROOT/'tools/build_hardware_german_repeaters.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class RepeatersTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.rows=m.validated_rows(ROOT)
 def test_ten_models_four_brands_23_endpoints(self):
  self.assertEqual(len(self.rows),10);self.assertEqual(len({r['definition']['identity']['manufacturer'] for r in self.rows}),4)
  self.assertEqual(sum(g['count'] for r in self.rows for g in r['definition']['groups']),23)
 def test_600_has_no_lan_or_radio_port(self):
  d=next(r['definition'] for r in self.rows if r['definition']['key']=='fritz-repeater600-de');self.assertEqual([(g['type'],g['count']) for g in d['groups']],[('power',1)])
 def test_six_wall_four_tabletop_no_rack_consumption(self):
  self.assertEqual(sum(r['definition']['kind']=='wall' for r in self.rows),6)
  for r in self.rows:
   d=r['definition'];self.assertEqual(d['mounting'],dict(kind=d['kind'],target='room'));self.assertEqual(d['rackUnits'],0);self.assertEqual(d['slots'],[])
 def test_dc_is_not_ac_and_plug_is_not_schuko_socket(self):
  for r in self.rows:
   d=r['definition'];g=next(g for g in d['groups'] if g['type'] in ('power','power_dc'));self.assertEqual(g['powerRole'],'inlet')
   self.assertEqual((g['type'],g['physicalConnector']),('power','eu-2pin-plug') if d['kind']=='wall' else ('power_dc','dc-barrel'))
 def test_unknown_dimensions_not_asserted_or_used_for_fit(self):
  for r in self.rows:
   d=r['definition']
   if d['identity']['manufacturer']=='devolo':self.assertTrue(all(v is None for v in d['dimensionsMm'].values()))
 def test_tp_link_does_not_invent_hardware_revision(self):
  self.assertEqual({r['definition']['identity']['sku'] for r in self.rows if r['definition']['identity']['manufacturer']=='TP-Link'},{'RE605X(EU)','RE700X(EU)'})
 def test_telekom_original_article(self):self.assertEqual(next(r['definition']['identity']['sku'] for r in self.rows if r['definition']['identity']['manufacturer']=='Telekom'),'40823475')
 def test_twenty_faces_every_endpoint_exactly_once(self):
  for row in self.rows:
   actual=[(s['groupKey'],s['ordinal']) for f in row['visual']['faces'].values() for s in m.h.expand(f)]
   expected=[(g['key'],i) for g in row['definition']['groups'] for i in range(1,g['count']+1)]
   self.assertEqual(sorted(actual),sorted(expected));self.assertEqual(len(actual),len(set(actual)))
 def test_missing_bank_rejected(self):
  row=copy.deepcopy(self.rows[0]);row['visual']['faces']['rear']['banks'].pop()
  with self.assertRaises(ValueError):m.h.validate_model(row,m.REVISION)
 def test_duplicate_bank_rejected(self):
  row=copy.deepcopy(self.rows[0]);row['visual']['faces']['rear']['banks'].append(copy.deepcopy(row['visual']['faces']['rear']['banks'][0]))
  with self.assertRaises(ValueError):m.h.validate_model(row,m.REVISION)
 def test_false_plug_type_rejected(self):
  row=copy.deepcopy(next(r for r in self.rows if r['definition']['kind']=='wall'));row['definition']['groups'][-1]['physicalConnector']='dc-barrel'
  with self.assertRaises(ValueError):m.h.validate_model(row,m.REVISION)
 def test_unclassified_radio_type_rejected(self):
  row=copy.deepcopy(self.rows[0]);row['definition']['groups'][0]['type']='wifi'
  with self.assertRaises(ValueError):m.h.validate_model(row,m.REVISION)
 def test_tabletop_is_not_parent_mounted(self):
  row=copy.deepcopy(next(r for r in self.rows if r['definition']['kind']=='tabletop'));row['definition']['mounting']['target']='parent'
  with self.assertRaises(ValueError):m.h.validate_model(row,m.REVISION)
 def test_wrong_revision_rejected(self):
  with self.assertRaises(ValueError):m.h.validate_model(self.rows[0],'latest')
 def test_generator_current_deterministic(self):
  a=m.compile_catalog(ROOT);self.assertEqual(a,m.compile_catalog(ROOT))
  for n,v in a.items():self.assertEqual((ROOT/n).read_bytes(),v)
 def test_lock_tampering_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d)
   for n in [*m.input_names(ROOT),m.LOCK]:p=r/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,p)
   (r/m.LOCK).write_bytes((r/m.LOCK).read_bytes()+b' ')
   with self.assertRaisesRegex(ValueError,'lock_not_reviewed'):m.compile_catalog(r)
 def test_preserves_usb_tae_latest_classifier(self):
  sql=m.compile_catalog(ROOT)[m.SQL].decode();self.assertIn("'voice-tae'",sql);self.assertIn("'schuko-f','eu-2pin-plug'",sql);self.assertIn("'floor','tabletop'",sql);self.assertNotIn('DELETE FROM',sql);self.assertNotIn('SET sealed=false',sql)
 def test_selection506_stays506(self):self.assertEqual(len(json.loads((ROOT/'development/hardware/selected-models-506.json').read_bytes())['models']),506)
if __name__=='__main__':unittest.main()
