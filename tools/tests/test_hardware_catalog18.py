"""Commercial SQL18 compiler guards in isolated trees; no database/build process."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('commercial_compiler', ROOT/'tools/build_hardware_catalog18.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)


class CommercialCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        for name in (c.SOURCE, c.LOCK, c.FACTS, c.BASE):
            target = self.root/name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT/name, target)

    def tearDown(self): self.temp.cleanup()

    def edit(self, name, change, repin=False):
        value = c.c.load((self.root/name).read_bytes()); change(value); (self.root/name).write_bytes(c.pretty(value))
        if repin:
            lock = c.c.load((self.root/c.LOCK).read_bytes())
            lock['sourceSha256'] = c.c.sha((self.root/c.SOURCE).read_bytes())
            lock['factsSha256'] = c.c.sha((self.root/c.FACTS).read_bytes())
            lock['definitions'] = [dict(key=m['key'], revision=m['revision'], sha256=c.c.sha(c.c.canonical(m)))
                                   for m in c.c.load((self.root/c.SOURCE).read_bytes())['definitions']]
            (self.root/c.LOCK).write_bytes(c.pretty(lock))

    def reject(self, code):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(c.c.CatalogError, '^'+code+'$'): c.run(self.root, write=True)
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_reproducible_precision_and_immutable_inputs(self):
        before = {name: (self.root/name).read_bytes() for name in (c.SOURCE, c.LOCK, c.FACTS, c.BASE)}
        expected = c.compile_catalog(self.root); c.run(self.root, write=True); c.run(self.root)
        c.run(self.root, write=True)
        self.assertEqual(expected, {name: (self.root/name).read_bytes() for name in expected})
        self.assertEqual(before, {name: (self.root/name).read_bytes() for name in before})
        view = json.loads(expected[c.FRONTEND]); self.assertFalse(view['synthetic'])
        row = view['profiles'][0]; self.assertEqual(44.3, row['heightMm']); self.assertTrue(row['rearLogicalNumbering'])
        self.assertEqual(c.URL, row['source']); self.assertEqual('C6PANELUTP241UFT', row['identity']['model'])
        self.assertIn(b'44.3m', expected[c.SERVER]); self.assertIn(b'483, 44.3, 138', expected[c.SQL])

    def test_check_never_creates_outputs_and_rejects_each_stale_file(self):
        before = sorted(self.root.rglob('*'))
        with self.assertRaisesRegex(c.c.CatalogError, 'commercial_catalog_stale'): c.run(self.root)
        self.assertEqual(before, sorted(self.root.rglob('*')))
        for name in c.compile_catalog(self.root):
            with self.subTest(name=name):
                c.run(self.root, write=True); target = self.root/name; target.write_bytes(target.read_bytes()+b'\n')
                with self.assertRaisesRegex(c.c.CatalogError, 'commercial_catalog_stale'): c.run(self.root)

    def test_each_input_hash_is_pinned_and_failure_preserves_outputs(self):
        c.run(self.root, write=True)
        for name in (c.SOURCE, c.FACTS, c.BASE):
            with self.subTest(name=name):
                target = self.root/name; raw = target.read_bytes(); target.write_bytes(raw+b' ')
                self.reject('commercial_input_changed'); target.write_bytes(raw)

    def test_lock_contract_and_definition_pin(self):
        raw = (self.root/c.LOCK).read_bytes()
        for field, value, code in [('targetSchema', 16, 'commercial_target_unsupported'),
                                    ('formatVersion', True, 'commercial_target_unsupported'),
                                    ('state', 'release', 'commercial_target_unsupported'),
                                    ('definitions', [], 'commercial_definition_not_reviewed')]:
            (self.root/c.LOCK).write_bytes(raw); self.edit(c.LOCK, lambda d: d.update({field: value})); self.reject(code)

    def test_unpinned_label_cannot_change_definition(self):
        self.edit(c.SOURCE, lambda d: d['definitions'][0]['groups'][0].update(name='Other'))
        self.reject('commercial_input_changed')

    def test_repinned_extra_model_still_rejected(self):
        def change(data):
            extra = copy.deepcopy(data['definitions'][0]); extra['key'] = 'another-model'; data['definitions'].append(extra)
        self.edit(c.SOURCE, change, repin=True); self.reject('commercial_model_not_reviewed')

    def test_repinned_facts_or_geometry_cannot_disagree(self):
        self.edit(c.FACTS, lambda d: d['facts'].update(heightMm=44), repin=True); self.reject('commercial_facts_mismatch')

    def test_repinned_source_still_matches_vendor_facts(self):
        self.edit(c.SOURCE, lambda d: d['definitions'][0]['dimensionsMm'].update(height=44), repin=True)
        self.reject('commercial_facts_mismatch')

    def test_more_than_three_decimals_not_truncated(self):
        self.edit(c.SOURCE, lambda d: d['definitions'][0]['dimensionsMm'].update(height=44.3001))
        self.reject('catalog_dimensions_precision_unsupported')

    def test_unsupported_assets_url_and_tracing(self):
        raw = (self.root/c.SOURCE).read_bytes()
        for field, value, code in [('assets', ['image.svg'], 'catalog_provenance_not_reviewed'),
                                    ('source', 'https://example.test/', 'catalog_provenance_not_reviewed')]:
            (self.root/c.SOURCE).write_bytes(raw)
            self.edit(c.SOURCE, lambda d: d['definitions'][0]['provenance'].update({field: value})); self.reject(code)
        (self.root/c.SOURCE).write_bytes(raw)
        self.edit(c.SOURCE, lambda d: d['definitions'][0]['passthrough'].update(tracingAvailable=True))
        self.reject('catalog_tracing_unsupported')

    def test_sql_columns_draft_components_then_seal_and_safe_literals(self):
        sql = c.compile_catalog(self.root)[c.SQL].decode('utf-8')
        self.assertEqual(2, sql.count('ALTER COLUMN height_mm TYPE numeric'))
        self.assertEqual(2, sql.count('ALTER COLUMN depth_mm TYPE numeric'))
        self.assertIn('INSERT INTO hardware_definition (profile_key, revision,', sql)
        self.assertEqual(2, sql.count('INSERT INTO hardware_group_template ('))
        self.assertIn('INSERT INTO hardware_passthrough (', sql)
        self.assertTrue(sql.splitlines()[-1].startswith('UPDATE hardware_definition SET sealed=true WHERE profile_key='))
        self.assertNotIn('DISABLE TRIGGER', sql); self.assertNotIn('DROP ', sql)
        self.assertEqual("E'O''Brien\\\\x'", c.literal("O'Brien\\x"))

    def test_manifest_and_native_target_cover_all_inputs_and_derivatives(self):
        outputs = c.compile_catalog(self.root); manifest = json.loads(outputs[c.MANIFEST])
        self.assertEqual(18, manifest['targetSchema']); self.assertEqual(c.STATE, manifest['state'])
        self.assertEqual({c.SERVER, c.FRONTEND, c.SQL}, set(manifest['files']))
        project = ET.fromstring(outputs[c.TARGETS]); target = project.find('Target')
        self.assertEqual('CoreCompile', target.attrib['BeforeTargets'])
        hashes = {item.attrib['Include'].split('../../../../')[1]: item.find('ExpectedHash').text for item in target.find('ItemGroup')}
        self.assertEqual({c.SOURCE, c.LOCK, c.FACTS, c.BASE, c.SERVER, c.FRONTEND, c.SQL, c.MANIFEST}, set(hashes))
        for name, digest in hashes.items(): self.assertEqual(c.c.sha(outputs.get(name, b'') or (self.root/name).read_bytes()), digest)
        self.assertTrue(all(e.attrib['Code'] == 'commercial_catalog_stale' for e in target.findall('Error')))

    def test_invalid_later_output_rejected_before_first_write(self):
        (self.root/c.SQL).mkdir(); self.reject('commercial_output_invalid')
        self.assertFalse((self.root/c.SERVER).exists())

    def test_output_symlink_ancestor_rejected(self):
        external = self.root/'external'; external.mkdir(); link = (self.root/c.SERVER).parent; link.parent.mkdir(parents=True)
        try: os.symlink(external, link, target_is_directory=True)
        except OSError: self.skipTest('Symbolic-link privilege unavailable; Windows junction tested separately')
        try: self.reject('catalog_reparse_path')
        finally: link.unlink()

    @unittest.skipUnless(os.name == 'nt', 'Windows junction')
    def test_output_junction_ancestor_rejected(self):
        external = self.root/'external'; external.mkdir(); link = (self.root/c.SERVER).parent; link.parent.mkdir(parents=True)
        result = subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(link), str(external)], capture_output=True)
        self.assertEqual(0, result.returncode, result.stderr)
        try: self.reject('catalog_reparse_path')
        finally: os.rmdir(link)

    def test_cli_has_no_source_target_or_import_override(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT/'tools/build_hardware_catalog18.py'), '--check', '--source', str(self.root)], capture_output=True)
        self.assertEqual(2, result.returncode); self.assertIn(b'unrecognized arguments', result.stderr)

    def test_default_compiler_still_rejects_commercial_identity(self):
        source = c.c.load((self.root/c.SOURCE).read_bytes())
        with self.assertRaisesRegex(c.c.CatalogError, 'catalog_commercial_identity_not_reviewed'): c.c.validate(source)


if __name__ == '__main__': unittest.main()
