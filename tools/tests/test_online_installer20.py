"""Own-only edition20 sources, explicit artifacts and closed integrity checks."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))


class Online20Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import build_online_installer20
        cls.builder = build_online_installer20
        spec = importlib.util.spec_from_file_location('online_assembly20', ROOT / 'tools/online-install/assemble20.py')
        cls.assembly = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.assembly)

    def fixture(self, root):
        values = {}
        for group, count in (('server', 58), ('frontend', 18)):
            values[group] = {}
            for n in range(count):
                name = f'fixture{n:02}.txt'
                path = root / group / name
                path.parent.mkdir(exist_ok=True)
                data = f'{group}/{n}'.encode()
                path.write_bytes(data)
                values[group][name] = hashlib.sha256(data).hexdigest()
        manifest = dict(kind='RackClickDistributionManifest', schema=48, profileId='schema48-admin-data-01',
                        distributions=values, fileCount=76,
                        totalBytes=sum(p.stat().st_size for p in root.rglob('*.txt')))
        (root / 'manifest.json').write_text(json.dumps(manifest), 'utf-8')
        (root / 'inventory.json').write_bytes(b'{}')
        (root / 'SHA256SUMS.txt').write_bytes(b'fixture metadata')
        return dict(APP_SHA=hashlib.sha256((root / 'manifest.json').read_bytes()).hexdigest(),
                    APP_INVENTORY_SHA=hashlib.sha256(b'{}').hexdigest(),
                    APP_SUMS_SHA=hashlib.sha256(b'fixture metadata').hexdigest(), APP_BYTES=manifest['totalBytes'])

    def test_closed_application_inventory_rejects_tamper_missing_and_root_extras(self):
        for mutation in (None, 'changed', 'missing', 'metadata', 'apphost', 'extra-root'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                r = Path(d)
                pins = self.fixture(r)
                if mutation == 'changed': (r / 'server/fixture00.txt').write_bytes(b'changed')
                elif mutation == 'missing': (r / 'frontend/fixture00.txt').unlink()
                elif mutation == 'metadata': (r / 'inventory.json').write_bytes(b'changed')
                elif mutation == 'apphost': (r / 'server/RackClick.Server.exe').write_bytes(b'extra')
                elif mutation == 'extra-root': (r / 'private.txt').write_bytes(b'extra')
                with patch.multiple(self.builder, **pins):
                    if mutation:
                        with self.assertRaises(ValueError): self.builder.verify_application(r)
                    else:
                        self.assertEqual(len(self.builder.verify_application(r)), 79)

    def test_service_artifact_is_explicit_and_checks_every_file(self):
        with tempfile.TemporaryDirectory() as d:
            r = Path(d)
            for n in range(36): (r / f'dep{n}.dll').write_bytes(str(n).encode())
            (r / 'RackClick.WindowsService.dll').write_bytes(b'host')
            files = self.builder.read_tree(r)
            with patch.multiple(self.builder, SERVICE_DLL_SHA=hashlib.sha256(b'host').hexdigest(),
                                SERVICE_TREE_SHA=self.builder.tree_digest(files)):
                self.assertEqual(len(self.builder.verify_service(r)), 37)
                (r / 'dep0.dll').write_bytes(b'altered dependency')
                with self.assertRaisesRegex(ValueError, 'service_tree_pin_invalid'): self.builder.verify_service(r)

    def test_core_member_paths_and_case_aliases_are_rejected(self):
        for name in ('../escape', '/absolute', 'a\\b', 'a:b', 'a/../b', 'CON', 'a/NUL.txt', 'a/', 'a\x00b'):
            with self.subTest(name=repr(name)), self.assertRaises(ValueError): self.assembly.safe_name(name)
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z:
            z.writestr('a.txt', b'one'); z.writestr('A.txt', b'two')
        with self.assertRaises(ValueError): self.builder.members(data.getvalue())

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'out.zip'; p.write_bytes(b'foreign')
            with self.assertRaisesRegex(ValueError, 'new_output_required'): self.builder.write_zip({'a': b'b'}, p)
            self.assertEqual(p.read_bytes(), b'foreign')

    def test_provider_urls_are_closed_and_python_never_downloads(self):
        for url in ('http://www.python.org/file', 'https://example.org/file',
                    'https://user:pass@www.python.org/file', 'https://www.python.org:8443/file'):
            with self.assertRaisesRegex(ValueError, 'provider_url_invalid'): self.assembly.check_url(url)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'provider_cache_required'):
                self.assembly.acquire({}, Path(d) / 'never-created', None)
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_core_changed_extra_missing_and_duplicate_are_rejected(self):
        for mutation in (None, 'changed', 'extra', 'missing', 'duplicate'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                r = Path(d); data = b'synthetic'
                (r / 'input.txt').write_bytes(data)
                rows = [dict(path='input.txt', bytes=len(data), sha256=hashlib.sha256(data).hexdigest())]
                if mutation == 'changed': (r / 'input.txt').write_bytes(b'changed')
                elif mutation == 'extra': (r / 'extra.txt').write_bytes(b'extra')
                elif mutation == 'missing': (r / 'input.txt').unlink()
                elif mutation == 'duplicate': rows.append(rows[0])
                (r / 'FILES.json').write_text(json.dumps(rows), 'utf-8')
                if mutation:
                    with self.assertRaises(ValueError): self.assembly.verify_core(r)
                else: self.assertEqual(self.assembly.verify_core(r), rows)

    def test_cli_rejection_never_adds_diagnostics_to_unowned_work(self):
        with tempfile.TemporaryDirectory() as d:
            r = Path(d); core = r / 'core'; core.mkdir(); work = r / 'existing'; work.mkdir()
            (work / 'keep').write_bytes(b'foreign')
            (core / 'FILES.json').write_text('[]', 'utf-8')
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/online-install/assemble20.py'),
                                     '--core-root', str(core), '--work-root', str(work)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual({p.name for p in work.iterdir()}, {'keep'})

    def test_outer_release_rejects_unknown_core_without_output(self):
        with tempfile.TemporaryDirectory() as d:
            r = Path(d); bad = r / 'bad.zip'; bad.write_bytes(b'not reviewed'); out = r / 'public.zip'
            with self.assertRaisesRegex(ValueError, 'core_release_pin_invalid|release_inputs_not_frozen'):
                self.builder.package(bad, bad, out)
            self.assertFalse(out.exists())

    def test_historical_zip_is_not_an_accepted_input(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'not-created.zip'
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/build_online_installer20.py'),
                                     '--reference18', 'historical.zip', '--output', str(target)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(target.exists())

    def test_public_demo_omits_the_old_application_pinned_loader(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            for number in range(55):
                archive.writestr(f'RackClick-Demo50-Trilingual-03/DATOS-DEMO50/file{number}.json', b'{}')
            archive.writestr('RackClick-Demo50-Trilingual-03/DATOS-DEMO50/00-LEEME.md', b'Use the old loader03')
            archive.writestr('RackClick-Demo50-Trilingual-03/DATOS-DEMO50/SHA256SUMS.txt', b'old metadata')
            archive.writestr('RackClick-Demo50-Trilingual-03/CARGAR-50-CLIENTES/Import-RackClickDemo50.ps1', b'old application pin')
            archive.writestr('RackClick-Demo50-Trilingual-03/CARGAR-50-CLIENTES/CARGAR-50-CLIENTES.cmd', b'old launcher')
        raw = data.getvalue()
        with patch.object(self.builder, 'DEMO_SHA', hashlib.sha256(raw).hexdigest()):
            files = self.builder.public_demo_files(raw)
        self.assertEqual(len(files), 57)
        self.assertTrue(all(n.startswith('DATOS-DEMO50/') for n in files))
        self.assertFalse(any(n.endswith(('.cmd', '.ps1')) for n in files))
        self.assertEqual(files['DATOS-DEMO50/file0.json'], b'{}')
        self.assertIn(b'Datos y copias de inventario', files['DATOS-DEMO50/00-LEEME.md'])
        self.assertNotIn(b'old loader03', files['DATOS-DEMO50/00-LEEME.md'])
        self.assertIn((hashlib.sha256(files['DATOS-DEMO50/00-LEEME.md']).hexdigest() + '  00-LEEME.md').encode(),
                      files['DATOS-DEMO50/SHA256SUMS.txt'])


if __name__ == '__main__': unittest.main()
