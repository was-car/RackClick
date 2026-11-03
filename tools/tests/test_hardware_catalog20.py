"""SQL20 authoring/guard checks in isolated trees. No DB or installed files."""
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
spec=importlib.util.spec_from_file_location('fortinet_compiler',ROOT/'tools/build_hardware_catalog20.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

class FortinetCatalogTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  for n in (g.SOURCE,g.FACTS,g.LOCK,g.BASE):
   p=self.root/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,p)
 def tearDown(self):self.temp.cleanup()
 def snapshot(self):return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
 def repin(self):
  lock=g.c.load((self.root/g.LOCK).read_bytes());s=g.c.load((self.root/g.SOURCE).read_bytes())
  for n,k in [(g.SOURCE,'sourceSha256'),(g.FACTS,'factsSha256'),(g.BASE,'baseMigrationSha256')]:lock[k]=g.c.sha((self.root/n).read_bytes())
  lock['definitions']=[dict(key=m['key'],revision=m['revision'],sha256=g.c.sha(g.c.canonical(m))) for m in s['definitions']];(self.root/g.LOCK).write_bytes(g.pretty(lock))
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
 def test_ethernet_only_desktop_outputs(self):
  out=g.compile_catalog(self.root);view=json.loads(out[g.FRONTEND]);self.assertFalse(view['synthetic']);p=view['profiles'][0];self.assertEqual('fortinet-20261030-v1',view['version']);self.assertNotIn('passthrough',p)
  self.assertEqual('desktop',p['kind']);self.assertEqual(0,p['sizeU']);self.assertEqual(38.5,p['heightMm'])
  self.assertEqual([(x['key'],x['type'],x['count'],x['face'],x['powerRole']) for x in p['groups']],[('rear-lan','rj45',5,'rear','unspecified'),('rear-fortilink','rj45',2,'rear','unspecified'),('rear-dmz','rj45',1,'rear','unspecified'),('rear-wan','rj45',2,'rear','unspecified')]);self.assertNotIn(b'PowerRole = "inlet"',out[g.SERVER]);self.assertIn(b'216m, 38.5m, 160m',out[g.SERVER])
 def test_migration_only_seeds_and_preserves_schema_and_sealing(self):
  sql=g.compile_catalog(self.root)[g.SQL].decode();self.assertNotIn('ALTER TABLE',sql);self.assertNotIn('DROP ',sql);self.assertNotIn('DISABLE TRIGGER',sql);self.assertNotIn('GRANT ',sql);self.assertEqual(1,sql.count('INSERT INTO hardware_definition'));self.assertEqual(4,sql.count('INSERT INTO hardware_group_template'));self.assertNotIn('hardware_passthrough (',sql);self.assertIn('sealed=true',sql)
 def test_targets_are_parseable_and_cover_all_inputs_outputs(self):
  out=g.compile_catalog(self.root);tree=ET.fromstring(out[g.TARGETS]);items=tree.findall('.//_FortinetCatalogInput');self.assertEqual(8,len(items));self.assertTrue(all(len(i.findtext('ExpectedHash'))==64 for i in items));self.assertIn(b'BeforeTargets="CoreCompile"',out[g.TARGETS])
 def test_targets_identify_fortinet_catalog_in_rule_and_diagnostics(self):
  raw=g.compile_catalog(self.root)[g.TARGETS];tree=ET.fromstring(raw);target=tree.find('Target')
  self.assertEqual('VerifyFortinetHardwareCatalog',target.attrib['Name'])
  self.assertEqual('CoreCompile',target.attrib['BeforeTargets'])
  errors=target.findall('Error');self.assertEqual(2,len(errors))
  for error in errors:
   self.assertEqual('fortinet_catalog_stale',error.attrib['Code'])
   self.assertEqual('fortinet_catalog_stale: run tools/build_hardware_catalog20.py --check',error.attrib['Text'])
  self.assertNotIn(b'aruba_catalog_stale',raw)
 def test_check_creates_nothing(self):
  before=self.snapshot()
  with self.assertRaisesRegex(g.c.CatalogError,'fortinet_catalog_stale'):g.run(self.root)
  self.assertEqual(before,self.snapshot())
 def test_each_stale_output_rejected(self):
  for n in g.compile_catalog(self.root):
   with self.subTest(n=n):
    g.run(self.root,True);p=self.root/n;p.write_bytes(p.read_bytes()+b' ')
    with self.assertRaisesRegex(g.c.CatalogError,'fortinet_catalog_stale'):g.run(self.root)
 def test_wrong_target_rejected(self):self.edit(g.LOCK,lambda v:v.update(targetSchema=18));self.reject('fortinet_target_unsupported')
 def test_bool_target_rejected(self):self.edit(g.LOCK,lambda v:v.update(targetSchema=True));self.reject('fortinet_target_unsupported')
 def test_unknown_lock_field_rejected(self):self.edit(g.LOCK,lambda v:v.update(force=True));self.reject('fortinet_lock_invalid')
 def test_source_edit_without_pin_rejected(self):self.edit(g.SOURCE,lambda v:v.update(catalogKey='changed'));self.reject('fortinet_input_changed')
 def test_facts_edit_without_pin_rejected(self):self.edit(g.FACTS,lambda v:v.update(model='FG-61F'));self.reject('fortinet_input_changed')
 def test_base_migration_edit_rejected(self):p=self.root/g.BASE;p.write_bytes(p.read_bytes()+b'\n');self.reject('fortinet_input_changed')
 def test_definition_pin_rejected(self):self.edit(g.LOCK,lambda v:v['definitions'][0].update(sha256='0'*64));self.reject('fortinet_definition_not_reviewed')
 def test_repin_does_not_authorize_another_sku(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['identity'].update(sku='FG-61F'),True);self.reject('fortinet_model_not_reviewed')
 def test_repin_does_not_move_network_ports_to_front(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['groups'][1].update(face='front'),True);self.reject('fortinet_model_not_reviewed')
 def test_repin_does_not_invent_poe_or_extra_ports(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['groups'][0].update(count=48),True);self.reject('fortinet_model_not_reviewed')
 def test_repin_does_not_add_a_network_power_role(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['groups'][0].update(powerRole='inlet'),True);self.reject('fortinet_model_not_reviewed')
 def test_repin_does_not_change_source_authority(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['provenance'].update(source='https://invalid.example/model'),True);self.reject('fortinet_model_not_reviewed')
 def test_repin_does_not_change_verified_facts(self):self.edit(g.FACTS,lambda v:v['facts'].update(poe=True),True);self.reject('fortinet_facts_mismatch')
 def test_repin_does_not_claim_physical_revision(self):self.edit(g.FACTS,lambda v:v.update(hardwareRevision='v2'),True);self.reject('fortinet_facts_mismatch')
 def test_json_duplicate_rejected(self):p=self.root/g.SOURCE;p.write_bytes(p.read_bytes().replace(b'"formatVersion": 1',b'"formatVersion": 1, "formatVersion": 1'));self.reject('catalog_json_duplicate_field')
 def test_unknown_source_field_rejected_even_repin(self):self.edit(g.SOURCE,lambda v:v.update(force=True),True);self.reject('fortinet_model_not_reviewed')
 def test_output_directory_rejects_without_partial_write(self):
  p=self.root/g.SQL;p.parent.mkdir(parents=True,exist_ok=True);p.mkdir();before=self.snapshot()
  with self.assertRaisesRegex(g.c.CatalogError,'fortinet_output_invalid'):g.run(self.root,True)
  self.assertEqual(before,self.snapshot())
 @unittest.skipUnless(os.name=='nt','Windows junction')
 def test_output_junction_rejected(self):
  external=self.root/'external';external.mkdir();junction=self.root/'development/frontend';junction.parent.mkdir(parents=True,exist_ok=True)
  q=lambda p:str(p).replace("'","''")
  p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',"New-Item -ItemType Junction -Path '"+q(junction)+"' -Target '"+q(external)+"' | Out-Null"],capture_output=True)
  self.assertEqual(p.returncode,0)
  try:
   with self.assertRaisesRegex(g.c.CatalogError,'catalog_reparse_path'):g.run(self.root,True)
   self.assertEqual([],list(external.iterdir()))
  finally:os.rmdir(junction)
 def test_native_frontend_guard_positive_and_changed_file(self):
  g.run(self.root,True);node=ROOT/'.local/node-v24.21.0-win-x64/node.exe';script="import {verifyFortinetHardwareCatalog as check} from "+json.dumps((ROOT/'development/frontend/verify-hardware-catalog.mjs').as_uri())+";await check(process.argv[1]);"
  p=subprocess.run([str(node),'--input-type=module','-e',script,str(self.root)],capture_output=True);self.assertEqual(0,p.returncode,p.stderr.decode())
  target=self.root/g.FRONTEND;target.write_bytes(target.read_bytes()+b' ');before=self.snapshot();p=subprocess.run([str(node),'--input-type=module','-e',script,str(self.root)],capture_output=True);self.assertNotEqual(0,p.returncode);self.assertIn(b'fortinet_catalog_stale',p.stderr);self.assertEqual(before,self.snapshot())
 def test_repin_cannot_make_the_device_one_u_rack(self):self.edit(g.SOURCE,lambda v:v['definitions'][0].update(kind='rack',rackUnits=1),True);self.reject('fortinet_model_not_reviewed')
 def test_repin_cannot_make_console_an_ethernet_group(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['groups'].append(dict(key='rear-console',type='rj45',count=1,face='rear',name='Console',prefix='CON ',powerRole='unspecified')),True);self.reject('fortinet_model_not_reviewed')
 def test_repin_cannot_add_dc_as_a_generic_power_port(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['groups'].append(dict(key='rear-power',type='power',count=1,face='rear',name='DC',prefix='DC ',powerRole='inlet')),True);self.reject('fortinet_model_not_reviewed')
 def test_repin_cannot_remove_the_dc_scope_warning(self):self.edit(g.FACTS,lambda v:v.update(scope='All connectors supported'),True);self.reject('fortinet_facts_mismatch')
if __name__=='__main__':unittest.main()
