from pathlib import Path
import copy,importlib.util,json,tempfile,unittest,zipfile,io,hashlib
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('selected_ir_tests',ROOT/'tools/build_selected_hardware.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

def model(category='switch'):
 return dict(id='test-model',manufacturer='Example',model='A+',category=category,assets=[])
def community():return dict(sourcePath='device-types/Example/A+.yaml',sourceSha256='a'*64,sourceUrl='https://example.test/source',partNumber='A+')
def official(scope='exact'):
 return dict(sku=None,dimensionsMm=dict(width=20,height=None,depth=None),mounting={},documentedInterfaces=[],documentedPower=[],notes=[],unknowns=[],sourceRecords=[dict(url='https://example.test/spec',path=None,sha256=None,scope=scope,locator='p2 table',factPaths=['dimensionsMm.width'])])

class PreparationTests(unittest.TestCase):
 def test_partition_is_exact_frozen_462(self):
  plan=g.read(g.PLAN);parts=[g.read(g.FOLDER/f'part-{i:02}.json')for i in range(1,4)]
  self.assertEqual([154]*3,[len(x['models'])for x in parts]);ids=[m['selectionId']for p in parts for m in p['models']]
  self.assertEqual(ids,plan['selectionIds']);self.assertEqual(462,len(set(ids)))
 def test_omitted_ports_are_unknown_not_zero_equipment(self):
  row=g.dossier(model(),community(),'fixture',dict(model='A+',u_height=1))
  self.assertEqual([],row['facts']['interfaces']);self.assertTrue(any(u['path']=='/facts/interfaces'for u in row['unknowns']));self.assertEqual('blocked',row['capabilities']['cable'])
 def test_fraction_zero_and_rack_nominal_width_do_not_become_body_dimensions(self):
  for u in [0,.5]:
   row=g.dossier(model(),community(),'fixture',dict(u_height=u));self.assertEqual(u,row['facts']['mounting']['rackUnits']);self.assertEqual('unknown',row['facts']['mounting']['kind'])
  row=g.dossier(model('rack'),community(),'fixture',dict(u_height=42,width=19,outer_height=1991,outer_depth=1070,outer_unit='mm'))
  self.assertEqual(dict(kind='rackContainer',rackUnits=None,capacityU=42),row['facts']['mounting']);self.assertIsNone(row['facts']['dimensionsMm']['width']);self.assertEqual(1991,row['facts']['dimensionsMm']['height'])
 def test_source_interface_and_module_values_are_not_reinterpreted(self):
  data=dict(u_height=1,interfaces=[dict(name='qsfp',type='100gbase-x-qsfp28'),dict(name='unknown',type='other',description='combo shared')],**{'module-bays':[dict(name='PSU1',position='42')]})
  row=g.dossier(model(),community(),'fixture',data)
  self.assertEqual(data['interfaces'],row['facts']['interfaces']);self.assertEqual('42',row['facts']['moduleBays'][0]['position']);self.assertIsNone(row['visual']['front']['geometry']);self.assertTrue(any('shared_media'in u['reason']for u in row['unknowns']))
 def test_shared_media_comments_are_preserved_without_interpreting_urls(self):
  for comment,expected in [('2x Combo GbE (RJ45/SFP)',True),('4x Combo GE (RJ45)',True),('Source: https://dell.test/shared/reference',False),('Source: https://dell.test/shared/reference\nCombo ports',True)]:
   row=g.dossier(model(),community(),'fixture',dict(u_height=1,comments=comment));self.assertEqual(comment,row['facts']['sourceComments']);self.assertEqual(expected,any('shared_media'in u['reason']for u in row['unknowns']));self.assertTrue(any(c['path']=='/facts/sourceComments'for c in row['claims']))
 def test_primary_scope_and_field_source_are_preserved(self):
  row=g.dossier(model(),None,'official_required',None,official('family'));claim=next(c for c in row['claims']if c['path']=='/facts/dimensionsMm/width');self.assertEqual('family',claim['scope'])
  data=official();data['sourceRecords'].insert(0,dict(url='https://example.test/other',path=None,sha256=None,scope='unknown',locator='p1',factPaths=[]))
  row=g.dossier(model(),None,'official_required',None,data);claim=next(c for c in row['claims']if c['path']=='/facts/dimensionsMm/width');self.assertEqual('official-2',claim['sourceId'])
 def test_ambiguous_or_unlocated_official_fact_stays_unknown(self):
  for change in ['duplicate','unlocated']:
   data=official()
   if change=='duplicate':data['sourceRecords'].append(copy.deepcopy(data['sourceRecords'][0]))
   else:data['sourceRecords'][0]['locator']=''
   row=g.dossier(model(),None,'official_required',None,data);self.assertIsNone(row['facts']['dimensionsMm']['width']);self.assertTrue(any('ambiguous'in u['reason']for u in row['unknowns']))
 def test_nested_official_leaves_use_their_own_source(self):
  data=official();data['dimensionsMm']['width']=None;data['documentedPower']=[dict(availableSupplyPositions=4,minimumSupplies=2,sourceRecord=1,locator='page2')]
  data['sourceRecords']=[dict(url='https://example.test/slots',path=None,sha256=None,scope='family',locator='p1 slots',factPaths=['documentedPower.0.availableSupplyPositions']),dict(url='https://example.test/min',path=None,sha256=None,scope='exact',locator='p2 min',factPaths=['documentedPower.0.minimumSupplies'])]
  row=g.dossier(model(),None,'official_required',None,data);claims={c['path']:c for c in row['claims']};self.assertEqual('family',claims['/facts/officialDeclarations/documentedPower/0/availableSupplyPositions']['scope']);self.assertEqual('official-2',claims['/facts/officialDeclarations/documentedPower/0/minimumSupplies']['sourceId'])
 def test_unknown_schema_promotion_and_geometry_are_rejected(self):
  original=g.dossier(model(),community(),'fixture',dict(u_height=1))
  for change in [lambda x:x['facts'].update(extra=1),lambda x:x['facts']['mounting'].update(extra=1),lambda x:x['visual']['front'].update(extra=1),lambda x:x['visual']['front'].update(geometry={}),lambda x:x['promotion'].update(status='promoted',profileKey='fake'),lambda x:x['capabilities'].update(create='verified'),lambda x:x['claims'][0].update(scope='unknown',path='facts.width')]:
   row=copy.deepcopy(original);change(row)
   with self.assertRaises(ValueError):g.validate_row(row)
 def test_duplicate_and_non_finite_json_are_rejected(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d)/'bad.json'
   for text in ['{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}','{"x":1e999}']:
    p.write_text(text)
    with self.assertRaises(ValueError):g.read(p)
 def test_yaml_is_limited_safe_and_hash_verified(self):
  def parsed(raw,pin=None):
   b=io.BytesIO()
   with zipfile.ZipFile(b,'w')as z:z.writestr(g.PREFIX+'device-types/Example/A+.yaml',raw)
   b.seek(0)
   with zipfile.ZipFile(b)as z:return g.load_yaml(z,dict(sourcePath='device-types/Example/A+.yaml',sourceSha256=pin or hashlib.sha256(raw).hexdigest()))
  data,_=parsed(b'model: "<svg onload=alert(1)>"\nu_height: 0.5\n');self.assertEqual(.5,data['u_height']);self.assertIn('<svg',data['model'])
  for raw,pin in [(b'model: test\n','0'*64),(b'x: '+b'a'*(512*1024),None),(b'!!python/object/apply:os.system ["echo bad"]',None),(b'[]',None),(b'a: &a 1\nb: ['+b','.join([b'*a']*31)+b']',None)]:
   with self.assertRaises(Exception):parsed(raw,pin)

if __name__=='__main__':unittest.main()
