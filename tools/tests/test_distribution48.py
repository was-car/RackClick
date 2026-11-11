"""Closed NEW48 application profile. Uses copies only; never installs."""
import hashlib,json,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/'.local/distribution48/maintenance-01'
PIN='a7b622f917404bbe3ea2560e1fcc2dad008910395c6ab5fa8bc6875be2c88112'


class Distribution48Tests(unittest.TestCase):
    def verify(self,path=APP,pin=PIN):
        r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(ROOT/'tools/windows/Test-ServerDistribution.ps1'),'-ManifestPath',str(path/'manifest.json'),'-ExpectedManifestSha256',pin,'-ServerPath',str(path/'server'),'-FrontendPath',str(path/'frontend')],capture_output=True,encoding='utf-8-sig',timeout=60)
        self.assertFalse(r.stderr)
        v=json.loads(r.stdout);self.assertEqual(r.returncode,v['exitCode'])
        return v
    def copy(self):
        temp=tempfile.TemporaryDirectory(prefix='distribution48-',dir=ROOT/'.local');self.addCleanup(temp.cleanup)
        path=Path(temp.name)/'candidate';shutil.copytree(APP,path);return path
    def test_native76(self):
        v=self.verify();self.assertEqual((v['code'],v['schema'],v['verifiedFiles']),('artifacts_verified',48,76))
    def test_wrong_external_digest(self):
        self.assertEqual(self.verify(pin='0'*64)['code'],'manifest_untrusted')
    def test_rehashed_manifest_not_authorized(self):
        p=self.copy();f=p/'manifest.json';v=json.loads(f.read_text());v['sourceStatus']='changed';f.write_text(json.dumps(v))
        self.assertEqual(self.verify(p,hashlib.sha256(f.read_bytes()).hexdigest())['code'],'manifest_distribution_unsupported')
    def test_missing_each_new_sql(self):
        for name in ['046-mfa-rotation-witness.sql','047-mfa-loss.sql','048-mfa-loss-startup.sql']:
            # Actual names come from the closed definition, not a directory wildcard at verification time.
            profile=json.loads((ROOT/'docs/DISTRIBUCION48-PERFIL.json').read_text())
            version=name[:3];rel=next(x for x in profile['serverSqlFiles'] if x.startswith('database/'+version+'-'))
            with self.subTest(version=version):
                p=self.copy();(p/'server'/rel).unlink();self.assertEqual(self.verify(p)['code'],'distribution_files_missing')
    def test_changed_dll(self):
        p=self.copy();f=p/'server/RackClick.Server.dll';f.write_bytes(f.read_bytes()+b'changed')
        self.assertEqual(self.verify(p)['code'],'artifact_hash_mismatch')
    def test_extra_apphost(self):
        p=self.copy();(p/'server/RackClick.Server.exe').write_bytes(b'extra')
        self.assertEqual(self.verify(p)['code'],'distribution_files_extra')


if __name__=='__main__':unittest.main()
