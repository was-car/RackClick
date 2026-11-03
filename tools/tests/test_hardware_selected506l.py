"""L catalogue negatives; no DB, package adoption, VM or installed service."""
import copy,importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('family_l_test',ROOT/'tools/hardware_family_l.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
REV='selected506l-20261101-v1'
def rows():return [row for source in ('mechanical-copper','storage','network') for row in json.loads((ROOT/f'development/hardware/selected506l/{source}.json').read_text())['models']]
class LAuthoringTests(unittest.TestCase):
 def setUp(self):self.rows=rows()
 def reject(self,row,change):
  value=copy.deepcopy(row);change(value)
  with self.assertRaises(h.CatalogError):h.validate_model(value,REV)
 def test_all_62_are_exact_originals(self):
  self.assertEqual(len(self.rows),62)
  for row in self.rows:self.assertIs(h.validate_model(row,REV),row)
 def test_partial_rack_dimensions_stay_unknown(self):
  row=next(row for row in self.rows if row['definition']['kind']=='rack');value=copy.deepcopy(row);value['definition']['dimensionsMm']['depth']=None
  self.assertIs(h.validate_model(value,REV),value)
 def test_unknown_dimensions_never_prove_shelf_fit(self):
  row=next(row for row in self.rows if row['definition']['kind']=='desktop')
  self.reject(row,lambda v:v['definition']['dimensionsMm'].update(depth=None))
 def test_container_is_capacity_not_occupied_u(self):
  row=next(row for row in self.rows if row['definition']['kind']=='rackContainer')
  self.reject(row,lambda v:v['definition'].update(rackUnits=42))
  self.reject(row,lambda v:v['definition']['mounting'].update(target='rack'))
  self.reject(row,lambda v:v['definition']['mounting'].update(capacityU=0))
 def test_vertical_and_room_mounts_cannot_acquire_u(self):
  for kind in ('vertical0U','sharedU','wall','din'):
   self.reject(next(row for row in self.rows if row['definition']['kind']==kind),lambda v:v['definition'].update(rackUnits=1))
 def test_smartpower_is_not_ac_or_usb_pd(self):
  row=next(row for row in self.rows if any(g.get('powerSystem')=='unifi-smartpower' for g in row['definition']['groups']))
  def change(v):next(g for g in v['definition']['groups'] if g.get('powerSystem')=='unifi-smartpower')['powerSystem']='usb-pd'
  self.reject(row,change)
 def test_physical_connector_is_typed(self):
  row=next(row for row in self.rows if any(g['type']=='rj45' for g in row['definition']['groups']))
  self.reject(row,lambda v:next(g for g in v['definition']['groups'] if g['type']=='rj45').update(physicalConnector='serial-de9'))
 def test_same_face_continuity_is_explicit_and_not_tracing(self):
  row=next(row for row in self.rows if any(c for c in row['definition'].get('continuities',[]) if next(g for g in row['definition']['groups'] if g['key']==c['fromGroup'])['face']==next(g for g in row['definition']['groups'] if g['key']==c['toGroup'])['face']))
  self.reject(row,lambda v:v['definition']['continuities'][0].update(tracingAvailable=True))
  self.reject(row,lambda v:v['definition']['continuities'][0].update(toGroup=v['definition']['continuities'][0]['fromGroup']))
 def test_large_group_limit_does_not_hide_missing_sockets(self):
  row=next(row for row in self.rows if any(g['count']==320 for g in row['definition']['groups']))
  self.reject(row,lambda v:next(g for g in v['definition']['groups'] if g['count']==320).update(count=513))
  self.reject(row,lambda v:v['visual']['faces']['front']['banks'].clear())
 def test_bom_slots_cannot_duplicate(self):
  row=next(row for row in self.rows if row['definition'].get('configuration'))
  self.reject(row,lambda v:v['definition']['configuration'].append(copy.deepcopy(v['definition']['configuration'][0])))
 def test_no_unknown_physical_face_or_role(self):
  row=next(row for row in self.rows if row['definition']['groups'])
  self.reject(row,lambda v:v['definition']['groups'][0].update(physicalFace='guessed'))
  self.reject(row,lambda v:v['definition']['groups'][0].update(interfaceRole='generic-network'))
if __name__=='__main__':unittest.main()
