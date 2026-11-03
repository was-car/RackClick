"""The production catalog compiler, with isolated authoring trees and real guards."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('catalog_compiler', ROOT/'tools/build_hardware_catalog.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)


class HardwareCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        for name in (c.SOURCE, c.LOCK, c.REFERENCE):
            target = self.root/name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT/name,target)
        self.source = c.load((self.root/c.SOURCE).read_bytes())

    def tearDown(self): self.temp.cleanup()

    def save(self):
        (self.root/c.SOURCE).write_text(json.dumps(self.source, allow_nan=True),encoding='utf-8')

    def rejects(self, change, code):
        change(self.source); self.save()
        with self.assertRaisesRegex(c.CatalogError, '^'+code+'$'): c.run(self.root,write=True)
        self.assertFalse((self.root/c.SERVER).exists()); self.assertFalse((self.root/c.FRONTEND).exists())

    def test_current_tree_matches_all_derivatives(self): c.run(ROOT)

    def test_reproducible_and_frozen_reference_unchanged(self):
        before = (self.root/c.REFERENCE).read_bytes(); first = c.run(self.root,write=True)
        raw = {name:(self.root/name).read_bytes() for name in first['files']}
        self.assertEqual(raw,c.compile_catalog(self.root)); c.run(self.root); c.run(self.root,write=True)
        self.assertEqual(raw,{name:(self.root/name).read_bytes() for name in first['files']})
        self.assertEqual(before,(self.root/c.REFERENCE).read_bytes())
        self.assertEqual(json.loads(raw[c.FRONTEND]),json.loads(before))

    def test_duplicate_revision(self):
        self.rejects(lambda d:d['definitions'].append(copy.deepcopy(d['definitions'][0])),'catalog_duplicate_revision')

    def test_second_revision_does_not_expand_schema16(self):
        def change(d):
            extra=copy.deepcopy(d['definitions'][1]); extra['revision']='hw-reference-v2';d['definitions'].append(extra)
        self.rejects(change,'catalog_schema16_definition_not_reviewed')

    def test_new_key_does_not_expand_schema16(self):
        self.rejects(lambda d:d['definitions'][2].update(key='new-commercial-switch'),'catalog_schema16_definition_not_reviewed')

    def test_changed_label_cannot_silently_change_v1(self):
        self.rejects(lambda d:d['definitions'][1]['groups'][0].update(prefix='OTHER '),'catalog_schema16_definition_not_reviewed')

    def test_no_unreviewed_manufacturer_claim(self):
        self.rejects(lambda d:d['definitions'][0]['identity'].update(manufacturer='Example vendor'),'catalog_commercial_identity_not_reviewed')

    def test_no_unlicensed_assets(self):
        self.rejects(lambda d:d['definitions'][0]['provenance']['assets'].append('https://example.test/product.svg'),'catalog_provenance_not_reviewed')

    def test_bad_dimensions(self):
        for value in (0,-1,True,'1',float('inf'),float('nan'),10001,10**400):
            with self.subTest(value=value):
                data=copy.deepcopy(self.source);data['definitions'][0]['dimensionsMm']['width']=value
                with self.assertRaises(c.CatalogError):c.validate(data)

    def test_integral_backend_dimensions(self):
        self.rejects(lambda d:d['definitions'][0]['dimensionsMm'].update(height=44.5),'catalog_dimensions_precision_unsupported')

    def test_desktop_does_not_reserve_rack_units(self):
        self.rejects(lambda d:d['definitions'][1].update(rackUnits=1),'catalog_integer_invalid')

    def test_shelf_must_declare_slot(self):
        self.rejects(lambda d:d['definitions'][0].update(slots=[]),'catalog_slots_invalid')

    def test_duplicate_group_keys(self):
        self.rejects(lambda d:d['definitions'][1]['groups'][1].update(key='front-lan'),'catalog_group_duplicate')

    def test_unknown_connector_not_mapped_to_rj45(self):
        self.rejects(lambda d:d['definitions'][1]['groups'][0].update(type='unknown'),'catalog_connector_unsupported')

    def test_explicit_face_required(self):
        self.rejects(lambda d:d['definitions'][1]['groups'][0].update(face='both'),'catalog_face_invalid')

    def test_positive_bounded_count_not_bool(self):
        for count in (0,257,True,3.5):
            with self.subTest(count=count):
                data=copy.deepcopy(self.source);data['definitions'][1]['groups'][0]['count']=count
                with self.assertRaises(c.CatalogError):c.validate(data)

    def test_passthrough_must_resolve_existing_groups(self):
        self.rejects(lambda d:d['definitions'][3]['passthrough'].update(rearGroup='missing'),'catalog_passthrough_invalid')

    def test_passthrough_counts_must_agree(self):
        self.rejects(lambda d:d['definitions'][3]['passthrough'].update(count=23),'catalog_passthrough_invalid')

    def test_continuity_does_not_enable_tracing(self):
        self.rejects(lambda d:d['definitions'][3]['passthrough'].update(tracingAvailable=True),'catalog_tracing_unsupported')

    def test_unknown_fields_do_not_disappear(self):
        self.rejects(lambda d:d['definitions'][0].update(optionalPsu=True),'catalog_definition_invalid')

    def test_duplicate_json_fields_rejected(self):
        for raw in (b'{"formatVersion":1,"formatVersion":1}',b'{"nested":{"a":1,"a":2}}'):
            with self.assertRaisesRegex(c.CatalogError,'catalog_json_duplicate_field'):c.load(raw)

    def test_oversized_json_integer_has_a_controlled_diagnostic(self):
        with self.assertRaisesRegex(c.CatalogError,'catalog_json_invalid'):
            c.load(('{"value":'+('1'*5000)+'}').encode('ascii'))

    def test_missing_or_changed_reference_rejected(self):
        reference=self.root/c.REFERENCE; reference.write_bytes(reference.read_bytes()+b' ')
        with self.assertRaisesRegex(c.CatalogError,'catalog_reference_changed'):c.run(self.root,write=True)
        self.assertFalse((self.root/c.SERVER).exists());reference.unlink()
        with self.assertRaises(FileNotFoundError):c.run(self.root,write=True)

    def test_check_missing_outputs_does_not_create_anything(self):
        before=sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        with self.assertRaisesRegex(c.CatalogError,'catalog_generated_stale'):c.run(self.root)
        self.assertEqual(before,sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*')))

    def test_every_stale_derivative_is_rejected(self):
        for name in c.compile_catalog(self.root):
            with self.subTest(name=name):
                c.run(self.root,write=True);target=self.root/name;target.write_bytes(target.read_bytes()+b'\n')
                with self.assertRaisesRegex(c.CatalogError,'catalog_generated_stale'):c.run(self.root)

    def test_invalid_source_preserves_already_generated_outputs(self):
        c.run(self.root,write=True);before={p:p.read_bytes() for p in (self.root/c.SERVER,self.root/c.FRONTEND,self.root/c.MANIFEST,self.root/c.TARGETS)}
        self.source['definitions'][1]['groups'][0]['count']=0;self.save()
        with self.assertRaises(c.CatalogError):c.run(self.root,write=True)
        self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_real_node_guard_rejects_each_changed_input(self):
        node=ROOT/'.local/node-v24.21.0-win-x64/node.exe'
        if not node.exists():self.skipTest('Pinned Node unavailable; compiler tests remain runnable')
        guard=(ROOT/'development/frontend/verify-hardware-catalog.mjs').as_uri()
        js=f'import {{verifyHardwareCatalog}} from {json.dumps(guard)};await verifyHardwareCatalog(process.argv[1]);'
        def run():return subprocess.run([str(node),'--input-type=module','-e',js,str(self.root)],capture_output=True,text=True)
        c.run(self.root,write=True);self.assertEqual(0,run().returncode)
        for name in (c.SOURCE,c.LOCK,c.REFERENCE,c.SERVER,c.FRONTEND):
            target=self.root/name;raw=target.read_bytes();target.write_bytes(raw+b'\n')
            result=run();self.assertNotEqual(0,result.returncode);self.assertIn('hardware_catalog_stale',result.stderr)
            target.write_bytes(raw)


if __name__=='__main__':unittest.main()
