"""Catalog22 authoring/guards in isolated trees. No DB, services or installed files."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('diskstation_compiler',ROOT/'tools/build_hardware_catalog22.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

class DiskStationCatalogTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  for n in (g.SOURCE,g.FACTS,g.LOCK,g.BASE):
   p=self.root/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,p)
 def tearDown(self):self.temp.cleanup()
 def snapshot(self):return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
 def repin(self):
  lock=g.c.load((self.root/g.LOCK).read_bytes());source=g.c.load((self.root/g.SOURCE).read_bytes())
  for n,k in [(g.SOURCE,'sourceSha256'),(g.FACTS,'factsSha256'),(g.BASE,'baseMigrationSha256')]:lock[k]=g.c.sha((self.root/n).read_bytes())
  lock['definitions']=[dict(key=m['key'],revision=m['revision'],sha256=g.c.sha(g.c.canonical(m))) for m in source['definitions']];(self.root/g.LOCK).write_bytes(g.pretty(lock))
 def edit(self,n,fn,repin=False):
  obj=g.c.load((self.root/n).read_bytes());fn(obj);(self.root/n).write_bytes(g.pretty(obj))
  if repin:self.repin()
 def reject(self,code):
  before=self.snapshot()
  with self.assertRaisesRegex(g.c.CatalogError,'^'+code+'$'):g.run(self.root,write=True)
  self.assertEqual(before,self.snapshot())
 def test_reproducible_and_inputs_unchanged(self):
  before=self.snapshot();expected=g.compile_catalog(self.root);g.run(self.root,True);g.run(self.root);g.run(self.root,True)
  self.assertEqual(expected,{n:(self.root/n).read_bytes() for n in expected})
  for n,b in before.items():self.assertEqual(b,(self.root/n).read_bytes())
 def test_exact_desktop_connectors_and_distinct_revisions(self):
  out=g.compile_catalog(self.root);views=json.loads(out[g.FRONTEND]);self.assertEqual(2,len(views));ds,shelf=views
  self.assertEqual('synology-ds423plus-20261030-v1',ds['version']);self.assertFalse(ds['synthetic']);self.assertEqual('mount-support-20261030-v1',shelf['version']);self.assertTrue(shelf['synthetic'])
  p=ds['profiles'][0];self.assertEqual('synology-ds423plus',p['key']);self.assertEqual('DS423+',p['identity']['sku']);self.assertEqual(('desktop',0,199,166,223),(p['kind'],p['sizeU'],p['widthMm'],p['heightMm'],p['depthMm']))
  self.assertEqual([dict(key='rear-lan',type='rj45',count=2,face='rear',powerRole='unspecified')],p['groups']);self.assertNotIn('slot',p);self.assertNotIn('passthrough',p)
  self.assertIn(b'199m, 166m, 223m',out[g.SERVER]);self.assertNotIn(b'PowerRole = "inlet"',out[g.SERVER])
 def test_own_support_has_no_synology_identity_and_keeps_dimensions(self):
  source=g.c.load((self.root/g.SOURCE).read_bytes());support=source['definitions'][1];self.assertEqual('own-synthetic',support['provenance']['kind']);self.assertTrue(all(v is None for v in support['identity'].values()));self.assertEqual([],support['groups'])
  view=json.loads(g.compile_catalog(self.root)[g.FRONTEND])[1]['profiles'][0];self.assertEqual(('shelf',5,482.6,222,300),(view['kind'],view['sizeU'],view['widthMm'],view['heightMm'],view['depthMm']));self.assertEqual(dict(key='main',widthMm=440,heightMm=190,depthMm=300),view['slot'])
 def test_own_support_view_does_not_publish_null_commercial_identity(self):
  view=json.loads(g.compile_catalog(self.root)[g.FRONTEND]);self.assertNotIn('identity',view[1]['profiles'][0]);self.assertEqual('DS423+',view[0]['profiles'][0]['identity']['sku'])
 def test_own_support_view_does_not_publish_a_manufacturer_link(self):
  view=json.loads(g.compile_catalog(self.root)[g.FRONTEND]);self.assertNotIn('source',view[1]['profiles'][0]);self.assertTrue(view[0]['profiles'][0]['source'].startswith('https://global.download.synology.com/'))
 def test_migration_only_seeds_and_preserves_schema_and_sealing(self):
  sql=g.compile_catalog(self.root)[g.SQL].decode()
  for forbidden in ('ALTER TABLE','DROP ','DISABLE TRIGGER','GRANT ','DELETE FROM'):self.assertNotIn(forbidden,sql)
  self.assertEqual(2,sql.count('INSERT INTO hardware_definition'));self.assertEqual(1,sql.count('INSERT INTO hardware_group_template'));self.assertEqual(1,sql.count('INSERT INTO hardware_mount_slot'));self.assertEqual(2,sql.count('SET sealed=true'));self.assertNotIn('hardware_passthrough (',sql)
 def test_targets_have_own_module_name_and_diagnostics(self):
  raw=g.compile_catalog(self.root)[g.TARGETS];tree=ET.fromstring(raw);self.assertEqual(8,len(tree.findall('.//_DiskStationCatalogInput')));target=tree.find('Target');self.assertEqual('VerifyDiskStationHardwareCatalog',target.attrib['Name']);self.assertEqual('CoreCompile',target.attrib['BeforeTargets'])
  for error in target.findall('Error'):
   self.assertEqual('diskstation_catalog_stale',error.attrib['Code']);self.assertEqual('diskstation_catalog_stale: run tools/build_hardware_catalog22.py --check',error.attrib['Text'])
  for donor in (b'aruba_catalog',b'fortinet_catalog',b'synology_catalog',b'build_hardware_catalog21.py'):self.assertNotIn(donor,raw)
 def test_check_creates_nothing(self):
  before=self.snapshot()
  with self.assertRaisesRegex(g.c.CatalogError,'diskstation_catalog_stale'):g.run(self.root)
  self.assertEqual(before,self.snapshot())
 def test_each_stale_output_rejected(self):
  for n in g.compile_catalog(self.root):
   with self.subTest(n=n):
    g.run(self.root,True);p=self.root/n;p.write_bytes(p.read_bytes()+b' ')
    with self.assertRaisesRegex(g.c.CatalogError,'diskstation_catalog_stale'):g.run(self.root)
 def test_wrong_target_rejected(self):self.edit(g.LOCK,lambda v:v.update(targetSchema=21));self.reject('diskstation_target_unsupported')
 def test_bool_target_rejected(self):self.edit(g.LOCK,lambda v:v.update(targetSchema=True));self.reject('diskstation_target_unsupported')
 def test_unknown_lock_field_rejected(self):self.edit(g.LOCK,lambda v:v.update(force=True));self.reject('diskstation_lock_invalid')
 def test_source_edit_without_pin_rejected(self):self.edit(g.SOURCE,lambda v:v.update(catalogKey='changed'));self.reject('diskstation_input_changed')
 def test_facts_edit_without_pin_rejected(self):self.edit(g.FACTS,lambda v:v.update(model='DS923+'));self.reject('diskstation_input_changed')
 def test_base_migration_edit_rejected(self):p=self.root/g.BASE;p.write_bytes(p.read_bytes()+b'\n');self.reject('diskstation_input_changed')
 def test_definition_pin_rejected(self):self.edit(g.LOCK,lambda v:v['definitions'][0].update(sha256='0'*64));self.reject('diskstation_definition_not_reviewed')
 def test_both_definition_pins_required(self):self.edit(g.LOCK,lambda v:v['definitions'].pop());self.reject('diskstation_definition_not_reviewed')
 def test_repin_does_not_authorize_another_sku(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['identity'].update(sku='DS923+'),True);self.reject('diskstation_model_not_reviewed')
 def test_repin_does_not_authorize_non_plus(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['identity'].update(model='DS423',sku='DS423'),True);self.reject('diskstation_model_not_reviewed')
 def test_repin_does_not_move_lan_to_front(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['groups'][0].update(face='front'),True);self.reject('diskstation_model_not_reviewed')
 def test_repin_does_not_invent_extra_ports(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['groups'][0].update(count=4),True);self.reject('diskstation_model_not_reviewed')
 def test_repin_does_not_add_network_power_role(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['groups'][0].update(powerRole='inlet'),True);self.reject('diskstation_model_not_reviewed')
 def test_repin_does_not_add_dc_as_generic_ac_power(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['groups'].append(dict(key='rear-power',type='power',count=1,face='rear',name='DC',prefix='DC ',powerRole='inlet')),True);self.reject('diskstation_model_not_reviewed')
 def test_repin_does_not_change_source_authority(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['provenance'].update(source='https://invalid.example/model'),True);self.reject('diskstation_model_not_reviewed')
 def test_repin_does_not_change_verified_facts(self):self.edit(g.FACTS,lambda v:v['facts'].update(poe=True),True);self.reject('diskstation_facts_mismatch')
 def test_repin_does_not_claim_physical_revision(self):self.edit(g.FACTS,lambda v:v.update(hardwareRevision='v2'),True);self.reject('diskstation_facts_mismatch')
 def test_json_duplicate_rejected(self):p=self.root/g.SOURCE;p.write_bytes(p.read_bytes().replace(b'"formatVersion": 1',b'"formatVersion": 1, "formatVersion": 1'));self.reject('catalog_json_duplicate_field')
 def test_unknown_source_field_rejected_even_repin(self):self.edit(g.SOURCE,lambda v:v.update(force=True),True);self.reject('diskstation_model_not_reviewed')
 def test_output_directory_rejects_without_partial_write(self):
  p=self.root/g.SQL;p.parent.mkdir(parents=True,exist_ok=True);p.mkdir();before=self.snapshot()
  with self.assertRaisesRegex(g.c.CatalogError,'diskstation_output_invalid'):g.run(self.root,True)
  self.assertEqual(before,self.snapshot())
 @unittest.skipUnless(os.name=='nt','Windows junction')
 def test_output_junction_rejected(self):
  external=self.root/'external';external.mkdir();junction=self.root/'development/frontend';junction.parent.mkdir(parents=True,exist_ok=True)
  q=lambda p:str(p).replace("'","''")
  p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',"New-Item -ItemType Junction -Path '"+q(junction)+"' -Target '"+q(external)+"' | Out-Null"],capture_output=True);self.assertEqual(p.returncode,0)
  try:
   with self.assertRaisesRegex(g.c.CatalogError,'catalog_reparse_path'):g.run(self.root,True)
   self.assertEqual([],list(external.iterdir()))
  finally:os.rmdir(junction)
 def test_native_frontend_guard_positive_and_changed_file(self):
  g.run(self.root,True);node=ROOT/'.local/node-v24.21.0-win-x64/node.exe';script="import {verifyDiskStationHardwareCatalog as check} from "+json.dumps((ROOT/'development/frontend/verify-hardware-catalog.mjs').as_uri())+";await check(process.argv[1]);"
  p=subprocess.run([str(node),'--input-type=module','-e',script,str(self.root)],capture_output=True);self.assertEqual(0,p.returncode,p.stderr.decode())
  target=self.root/g.FRONTEND;target.write_bytes(target.read_bytes()+b' ');before=self.snapshot();p=subprocess.run([str(node),'--input-type=module','-e',script,str(self.root)],capture_output=True);self.assertNotEqual(0,p.returncode);self.assertIn(b'diskstation_catalog_stale',p.stderr);self.assertEqual(before,self.snapshot())
 def test_repin_cannot_make_nas_directly_rack_mounted(self):self.edit(g.SOURCE,lambda v:v['definitions'][0].update(kind='rack',rackUnits=4),True);self.reject('diskstation_model_not_reviewed')
 def test_repin_cannot_expand_historical_small_support(self):self.edit(g.SOURCE,lambda v:v['definitions'][1].update(key='shelf-2u',revision='hw-reference-v1'),True);self.reject('diskstation_model_not_reviewed')
 def test_repin_cannot_brand_support_as_synology(self):self.edit(g.SOURCE,lambda v:v['definitions'][1]['identity'].update(manufacturer='Synology',model='Official shelf'),True);self.reject('diskstation_model_not_reviewed')
 def test_repin_cannot_claim_airflow_certification(self):self.edit(g.FACTS,lambda v:v['ownSyntheticSupport'].update(scope='Synology certified airflow support'),True);self.reject('diskstation_facts_mismatch')
 def test_repin_cannot_remove_adapter_warning(self):self.edit(g.FACTS,lambda v:v.update(scope='All connectors supported'),True);self.reject('diskstation_facts_mismatch')
 def test_repin_cannot_resize_support_slot(self):self.edit(g.SOURCE,lambda v:v['definitions'][1]['slots'][0]['dimensionsMm'].update(height=60),True);self.reject('diskstation_model_not_reviewed')
 def test_repin_cannot_merge_revisions(self):self.edit(g.SOURCE,lambda v:v['definitions'][1].update(revision='synology-ds423plus-20261030-v1'),True);self.reject('diskstation_model_not_reviewed')
if __name__=='__main__':unittest.main()
