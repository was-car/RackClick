"""Catalog23 authoring/guards in isolated trees. No DB, services or installed files."""
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
spec=importlib.util.spec_from_file_location('qnap_compiler',ROOT/'tools/build_hardware_catalog23.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

class QnapCatalogTests(unittest.TestCase):
 def test_exact_sku_body_dimensions_and_connectors(self):
  out=g.compile_catalog(self.root);view=json.loads(out[g.FRONTEND]);self.assertEqual('qnap-20261030-v1',view['version']);self.assertFalse(view['synthetic']);p=view['profiles'][0]
  self.assertEqual(dict(manufacturer='QNAP',family='TS-x64',model='TS-464',sku='TS-464-8G'),p['identity']);self.assertEqual(('desktop',0,170,165,226.5),(p['kind'],p['sizeU'],p['widthMm'],p['heightMm'],p['depthMm']))
  self.assertEqual([dict(key='rear-lan',type='rj45',count=2,face='rear',powerRole='unspecified')],p['groups']);self.assertNotIn('slot',p);self.assertNotIn('passthrough',p);self.assertTrue(p['source'].endswith('TS-464-8G.pdf'))
  self.assertIn(b'170m, 165m, 226.5m',out[g.SERVER]);self.assertNotIn(b'PowerRole = "inlet"',out[g.SERVER]);self.assertEqual(23,json.loads(out[g.MANIFEST])['targetSchema'])
 def test_migration_only_seeds_one_model_and_no_new_support(self):
  sql=g.compile_catalog(self.root)[g.SQL].decode()
  for forbidden in ('ALTER TABLE','DROP ','DISABLE TRIGGER','GRANT ','DELETE FROM','INSERT INTO hardware_mount_slot','INSERT INTO hardware_passthrough'):self.assertNotIn(forbidden,sql)
  self.assertEqual(1,sql.count('INSERT INTO hardware_definition'));self.assertEqual(1,sql.count('INSERT INTO hardware_group_template'));self.assertEqual(1,sql.count('SET sealed=true'));self.assertNotIn("E'shelf-5u'",sql)
 def test_exact_dimensions_exclude_feet_and_old_guide_is_not_silently_merged(self):
  facts=g.c.load((self.root/g.FACTS).read_bytes());self.assertTrue(facts['facts']['dimensionsExcludeFootPad']);self.assertIsNone(facts['facts']['totalHeightWithFeetMm']);self.assertEqual((170,168,226),tuple(facts['olderGuideDimensionsMm'][k] for k in ('width','height','depth')))
  self.assertIsNone(facts['pdfSha256']);self.assertEqual(64,len(facts['guide']['pdfSha256']));self.assertIn('unknown',facts['mountScope']);self.assertIn('private references',facts['photographScope'])
 def test_repin_cannot_replace_nominal_height_with_old_guide(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['dimensionsMm'].update(height=168,depth=226),True);self.reject('qnap_model_not_reviewed')
 def test_repin_cannot_claim_measured_height_with_feet(self):self.edit(g.FACTS,lambda v:v['facts'].update(totalHeightWithFeetMm=195),True);self.reject('qnap_facts_mismatch')
 def test_repin_cannot_claim_downloaded_specification_pdf(self):self.edit(g.FACTS,lambda v:v.update(pdfSha256='0'*64),True);self.reject('qnap_facts_mismatch')
 def test_repin_cannot_make_it_a_rack_or_storage_topology(self):self.edit(g.SOURCE,lambda v:v['definitions'][0].update(kind='rack',rackUnits=4),True);self.reject('qnap_model_not_reviewed')
 def test_repin_cannot_remove_adapter_scope(self):self.edit(g.FACTS,lambda v:v.update(scope='All connectors enabled'),True);self.reject('qnap_facts_mismatch')
 def test_repin_cannot_claim_mechanical_certification(self):self.edit(g.FACTS,lambda v:v.update(mountScope='Certified rack accessory with guaranteed ventilation'),True);self.reject('qnap_facts_mismatch')
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
 def test_targets_have_own_module_name_and_diagnostics(self):
  raw=g.compile_catalog(self.root)[g.TARGETS];tree=ET.fromstring(raw);self.assertEqual(8,len(tree.findall('.//_QnapCatalogInput')));target=tree.find('Target');self.assertEqual('VerifyQnapHardwareCatalog',target.attrib['Name']);self.assertEqual('CoreCompile',target.attrib['BeforeTargets'])
  for error in target.findall('Error'):
   self.assertEqual('qnap_catalog_stale',error.attrib['Code']);self.assertEqual('qnap_catalog_stale: run tools/build_hardware_catalog23.py --check',error.attrib['Text'])
  for donor in (b'aruba_catalog',b'fortinet_catalog',b'synology_catalog',b'diskstation_catalog',b'build_hardware_catalog22.py'):self.assertNotIn(donor,raw)
 def test_check_creates_nothing(self):
  before=self.snapshot()
  with self.assertRaisesRegex(g.c.CatalogError,'qnap_catalog_stale'):g.run(self.root)
  self.assertEqual(before,self.snapshot())
 def test_each_stale_output_rejected(self):
  for n in g.compile_catalog(self.root):
   with self.subTest(n=n):
    g.run(self.root,True);p=self.root/n;p.write_bytes(p.read_bytes()+b' ')
    with self.assertRaisesRegex(g.c.CatalogError,'qnap_catalog_stale'):g.run(self.root)
 def test_wrong_target_rejected(self):self.edit(g.LOCK,lambda v:v.update(targetSchema=21));self.reject('qnap_target_unsupported')
 def test_bool_target_rejected(self):self.edit(g.LOCK,lambda v:v.update(targetSchema=True));self.reject('qnap_target_unsupported')
 def test_unknown_lock_field_rejected(self):self.edit(g.LOCK,lambda v:v.update(force=True));self.reject('qnap_lock_invalid')
 def test_source_edit_without_pin_rejected(self):self.edit(g.SOURCE,lambda v:v.update(catalogKey='changed'));self.reject('qnap_input_changed')
 def test_facts_edit_without_pin_rejected(self):self.edit(g.FACTS,lambda v:v.update(model='TS-664'));self.reject('qnap_input_changed')
 def test_base_migration_edit_rejected(self):p=self.root/g.BASE;p.write_bytes(p.read_bytes()+b'\n');self.reject('qnap_input_changed')
 def test_definition_pin_rejected(self):self.edit(g.LOCK,lambda v:v['definitions'][0].update(sha256='0'*64));self.reject('qnap_definition_not_reviewed')
 def test_definition_pin_is_required(self):self.edit(g.LOCK,lambda v:v['definitions'].pop());self.reject('qnap_definition_not_reviewed')
 def test_repin_does_not_authorize_another_sku(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['identity'].update(sku='TS-464-4G'),True);self.reject('qnap_model_not_reviewed')
 def test_repin_does_not_move_lan_to_front(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['groups'][0].update(face='front'),True);self.reject('qnap_model_not_reviewed')
 def test_repin_does_not_invent_extra_ports(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['groups'][0].update(count=4),True);self.reject('qnap_model_not_reviewed')
 def test_repin_does_not_add_network_power_role(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['groups'][0].update(powerRole='inlet'),True);self.reject('qnap_model_not_reviewed')
 def test_repin_does_not_add_dc_as_generic_ac_power(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['groups'].append(dict(key='rear-power',type='power',count=1,face='rear',name='DC',prefix='DC ',powerRole='inlet')),True);self.reject('qnap_model_not_reviewed')
 def test_repin_does_not_change_source_authority(self):self.edit(g.SOURCE,lambda v:v['definitions'][0]['provenance'].update(source='https://invalid.example/model'),True);self.reject('qnap_model_not_reviewed')
 def test_repin_does_not_change_verified_facts(self):self.edit(g.FACTS,lambda v:v['facts'].update(poe=True),True);self.reject('qnap_facts_mismatch')
 def test_repin_does_not_claim_physical_revision(self):self.edit(g.FACTS,lambda v:v.update(hardwareRevision='v2'),True);self.reject('qnap_facts_mismatch')
 def test_json_duplicate_rejected(self):p=self.root/g.SOURCE;p.write_bytes(p.read_bytes().replace(b'"formatVersion": 1',b'"formatVersion": 1, "formatVersion": 1'));self.reject('catalog_json_duplicate_field')
 def test_unknown_source_field_rejected_even_repin(self):self.edit(g.SOURCE,lambda v:v.update(force=True),True);self.reject('qnap_model_not_reviewed')
 def test_output_directory_rejects_without_partial_write(self):
  p=self.root/g.SQL;p.parent.mkdir(parents=True,exist_ok=True);p.mkdir();before=self.snapshot()
  with self.assertRaisesRegex(g.c.CatalogError,'qnap_output_invalid'):g.run(self.root,True)
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
  g.run(self.root,True);node=ROOT/'.local/node-v24.21.0-win-x64/node.exe';script="import {verifyQnapHardwareCatalog as check} from "+json.dumps((ROOT/'development/frontend/verify-hardware-catalog.mjs').as_uri())+";await check(process.argv[1]);"
  p=subprocess.run([str(node),'--input-type=module','-e',script,str(self.root)],capture_output=True);self.assertEqual(0,p.returncode,p.stderr.decode())
  target=self.root/g.FRONTEND;target.write_bytes(target.read_bytes()+b' ');before=self.snapshot();p=subprocess.run([str(node),'--input-type=module','-e',script,str(self.root)],capture_output=True);self.assertNotEqual(0,p.returncode);self.assertIn(b'qnap_catalog_stale',p.stderr);self.assertEqual(before,self.snapshot())
if __name__=='__main__':unittest.main()
