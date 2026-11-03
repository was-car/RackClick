"""Bounded archive contracts; no installation, credentials, PG or VM."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import package_windows43 as package

def archive(names):
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as z:
        for name,value in names:z.writestr(name,value)
    return data.getvalue()

class Windows43Package(unittest.TestCase):
    def test_closed_delivery_constants(self):
        self.assertEqual(package.APP_SHA,'d352c04381cd4f1954aa43735e540970b295f231106560c5c9880c7ee1dc78db')
        self.assertEqual(package.DEMO_SHA,'f89d8c7a5d796133cfe6b13812b885a124ee5fd21431a3c5271fd1a23d8a3447')

    def test_zip_members_keep_exact_bytes(self):
        self.assertEqual(package.members(archive([('P/a.txt',b'abc')]),'P/'),{'a.txt':b'abc'})

    def test_paths_and_case_collisions_rejected(self):
        for names in [['Q/a'],['P/../a'],['P/./a'],['P/a:stream'],['P/a.'],['P/a','P/A']]:
            with self.subTest(names=names),self.assertRaises(ValueError):
                package.members(archive([(n,b'a') for n in names]),'P/')
        # ZipInfo normalizes backslashes while producing a ZIP on Windows.
        # Mutate both raw names so the negative really contains a backslash.
        altered=archive([('P/a_b',b'a')]).replace(b'P/a_b',b'P/a\\b')
        with self.assertRaises(ValueError):package.members(altered,'P/')

    def test_symlink_member_rejected(self):
        d=io.BytesIO()
        with zipfile.ZipFile(d,'w') as z:
            info=zipfile.ZipInfo('P/link');info.create_system=3;info.external_attr=0o120777<<16;z.writestr(info,b'other')
        with self.assertRaises(ValueError):package.members(d.getvalue(),'P/')

    def test_record_hash_missing_extra_and_duplicate_fail(self):
        entries={'a':b'abc','M':b'{}'};m={'files':[{'path':'a','size':3,'sha256':package.sha(b'abc')}]}
        package.records_match(entries,m,'M')
        for bad in [{'files':[]},{'files':m['files']*2},{'files':[dict(m['files'][0],sha256='0'*64)]},
                    {'files':[dict(m['files'][0],size=4)]}]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):package.records_match(entries,bad,'M')

    def test_wrapper_alteration_rejected_before_any_output(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);w=d/'wrapper.zip';w.write_bytes(b'altered');output=d/'output.zip'
            with self.assertRaisesRegex(ValueError,'wrapper_pin_invalid'):
                package.build(w,d/'network',d/'demo',d/'plan',output)
            self.assertFalse(output.exists())

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);p=d/'output.zip';p.write_bytes(b'prior')
            with self.assertRaisesRegex(ValueError,'output_exists'):package.build(d,d,d,d,p)
            self.assertEqual(p.read_bytes(),b'prior')

    def test_external_hash_required_before_reading_zip(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'x.zip';p.write_bytes(b'not a zip')
            with self.assertRaisesRegex(ValueError,'archive_pin_invalid'):package.verify(p,'0'*64)

    def test_delivery_manifest_alteration_detected(self):
        body={'a':b'abc'};m={'schemaVersion':1,'kind':'RackClickCompleteWindowsCandidate','edition':'11','applicationSchema':43,
          'adopted':False,'vmTested':False,'files':[{'path':'a','size':3,'sha256':package.sha(b'abc')}]}
        body['ENTREGA.json']=json.dumps(m).encode();body['SHA256SUMS.txt']=''.join(f'{package.sha(v)}  {k}\n' for k,v in sorted(body.items())).encode()
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'x.zip';p.write_bytes(archive([(package.PREFIX+k,v) for k,v in body.items()]))
            with self.assertRaisesRegex(ValueError,'delivery_tree_not_authorized'):
                package.verify(p,package.sha(p.read_bytes()))
            body['a']=b'bad';p.write_bytes(archive([(package.PREFIX+k,v) for k,v in body.items()]))
            with self.assertRaisesRegex(ValueError,'content_mismatch'):package.verify(p,package.sha(p.read_bytes()))

if __name__=='__main__':unittest.main()
