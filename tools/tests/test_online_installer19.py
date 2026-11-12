"""Own-only online transport and exclusive, verified assembly; no installation."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import build_online_installer19 as builder
spec=importlib.util.spec_from_file_location('online_assembly',ROOT/'tools/online-install/assemble.py')
assembly=importlib.util.module_from_spec(spec);spec.loader.exec_module(assembly)

class Online19Tests(unittest.TestCase):
    def test_safe_names_reject_escape_devices_and_case_aliases(self):
        for name in ['../escape','/absolute','a\\b','a:b','a/../b','CON','a/NUL.txt','a/','a\x00b']:
            with self.subTest(name=repr(name)),self.assertRaises(ValueError):assembly.safe_name(name)
        self.assertEqual('application/server/database/048-mfa-loss-startup.sql',assembly.safe_name('application/server/database/048-mfa-loss-startup.sql'))
    def fixture(self,root):
        data=b'only synthetic input';(root/'input.txt').write_bytes(data)
        (root/'FILES.json').write_text(json.dumps([dict(path='input.txt',bytes=len(data),sha256=hashlib.sha256(data).hexdigest())]),'utf-8')
    def test_core_changed_extra_missing_and_duplicate_rejected(self):
        for mutation in ['changed','extra','missing','duplicate']:
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as d:
                r=Path(d);self.fixture(r)
                if mutation=='changed':(r/'input.txt').write_bytes(b'altered')
                elif mutation=='extra':(r/'extra.txt').write_bytes(b'extra')
                elif mutation=='missing':(r/'input.txt').unlink()
                else:
                    rows=json.loads((r/'FILES.json').read_text());rows.append(rows[0]);(r/'FILES.json').write_text(json.dumps(rows))
                with self.assertRaises(ValueError):assembly.verify_core(r)
    def test_valid_core_keeps_exact_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);self.fixture(r);before=(r/'input.txt').read_bytes();assembly.verify_core(r);self.assertEqual(before,(r/'input.txt').read_bytes())
    def test_wrong_provider_file_is_not_adopted(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'file.zip';p.write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError,'provider_content_invalid'):assembly.verify_provider(p,dict(bytes=4,algorithm='sha256',digest='0'*64))
            self.assertEqual(b'wrong',p.read_bytes())
    def test_redirect_and_url_contract_is_closed(self):
        for url in ['http://www.python.org/file','https://example.org/file','https://user:pass@www.python.org/file','https://www.python.org:8443/file']:
            with self.assertRaisesRegex(ValueError,'provider_url_invalid'):assembly.check_url(url)
        assembly.check_url('https://www.python.org/ftp/python/3.12.3/test.zip')
    def test_wrong_reference_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'wrong.zip';source.write_bytes(b'wrong');target=root/'out.zip'
            with self.assertRaisesRegex(ValueError,'reference18_pin_mismatch'):builder.collect(source,source,root)
            self.assertFalse(target.exists())
    def test_existing_work_directory_is_not_reused(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/'keep').write_bytes(b'owned by another operation')
            with self.assertRaisesRegex(ValueError,'new_assembly_root_required'):assembly.require_new_work(r)
            self.assertEqual(b'owned by another operation',(r/'keep').read_bytes())
    def test_cli_rejection_cannot_add_diagnostic_to_unowned_work_root(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);core=root/'core';core.mkdir();self.fixture(core)
            work=root/'existing';work.mkdir();(work/'keep').write_bytes(b'foreign')
            result=subprocess.run([sys.executable,'-B',str(ROOT/'tools/online-install/assemble.py'),'--core-root',str(core),'--work-root',str(work)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual({'keep'},{p.name for p in work.iterdir()})
    def test_outer_package_rejects_unreviewed_core_before_creating_output(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);bad=r/'bad.zip';bad.write_bytes(b'not reviewed');out=r/'public.zip'
            with self.assertRaisesRegex(ValueError,'core_release_pin_invalid'):
                builder.package(bad,bad,out)
            self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
