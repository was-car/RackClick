"""Fixed complete18 collector and final integrated delivery; never installs."""
import base64,hashlib,json,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
import package_windows48 as b
WRAPPER=ROOT/'.local/install18-20261111/packaging18/.local/RackClick-Servidor-18.zip'
DEMO=ROOT/'.local/demo50-trilingual03/entrega-01/RackClick-Demo50-Trilingual-03.zip'
FINAL=ROOT/'.local/install18-20261111/entrega-final/RackClick-Windows-Completo-18.zip'


class Complete18Tests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix='complete18-test-',dir=ROOT/'.local');self.addCleanup(t.cleanup);self.temp=Path(t.name)
    def test_wrong_wrapper_rejected_before_output(self):
        bad=self.temp/'bad.zip';bad.write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError,'wrapper_pin_mismatch'):b.build(bad,DEMO,self.temp/'out.zip')
        self.assertFalse((self.temp/'out.zip').exists())
    def test_wrong_demo_rejected_before_output(self):
        bad=self.temp/'bad.zip';bad.write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError,'demo_pin_mismatch'):b.build(WRAPPER,bad,self.temp/'out.zip')
        self.assertFalse((self.temp/'out.zip').exists())
    def test_existing_output_preserved_without_collecting(self):
        out=self.temp/'out.zip';out.write_bytes(b'keep')
        with patch.object(b,'collect',side_effect=AssertionError('must not collect')):
            with self.assertRaisesRegex(ValueError,'new_zip_required'):b.build(WRAPPER,DEMO,out)
        self.assertEqual(out.read_bytes(),b'keep')
    def test_final_members_hashes_and_sums(self):
        with zipfile.ZipFile(FINAL) as z:
            self.assertEqual(len(z.namelist()),73);self.assertEqual(len(set(z.namelist())),73)
            files={n[len(b.PREFIX):]:z.read(n) for n in z.namelist()}
        m=json.loads(files['ENTREGA.json']);self.assertEqual((m['edition'],m['applicationSchema'],m['demoCustomers']),('18',48,50))
        self.assertEqual(m['customerNameLanguages'],dict(en=17,de=17,es=16))
        self.assertEqual({v['path'] for v in m['files']},set(files)-{'ENTREGA.json','SHA256SUMS.txt'})
        for v in m['files']:self.assertEqual((len(files[v['path']]),b.sha(files[v['path']])),(v['size'],v['sha256']))
        sums=files['SHA256SUMS.txt'].decode().splitlines();self.assertEqual(len(sums),72)
        for row in sums:
            digest,name=row.split('  ',1);self.assertEqual(b.sha(files[name]),digest)
    def test_existing_server_blocks_launcher(self):
        with zipfile.ZipFile(FINAL) as z:script=z.read(b.PREFIX+'01-INSTALAR-NUEVO.ps1').decode('ascii')
        body="$ErrorActionPreference='Stop';function Get-Service{param($Name,$ErrorAction) [pscustomobject]@{Name='RackClick'}};try{& ([scriptblock]::Create([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+base64.b64encode(script.encode()).decode()+"'))));throw 'unexpected_launch'}catch{if($_.Exception.Message-cne'new_server_required_existing_rackclick_preserved'){throw};'blocked'}"
        p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(body.encode('utf-16le')).decode()],capture_output=True,encoding='utf-8-sig',timeout=30)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout.strip(),'blocked')


if __name__=='__main__':unittest.main()
