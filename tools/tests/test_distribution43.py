"""Closed application43 distribution; synthetic fixtures, no installer/DB/VM."""
import json
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
import build_server_distribution as builder

PROFILE = ROOT/'docs/DISTRIBUCION43-PERFIL.json'
CANDIDATE = ROOT/'.local/distribution43/candidata-01'
PIN = 'eb274f1f82deb9936c69214fae07e4188275063cf35ec775fe41d560a1806830'


class Distribution43Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='distribution43-', dir=ROOT/'.local')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.publish, self.frontend = self.work/'publish', self.work/'frontend'
        profile = json.loads(PROFILE.read_text(encoding='utf-8'))
        for folder, names in ((self.publish, profile['serverApplicationFiles']+profile['serverSqlFiles']),
                              (self.frontend, profile['frontendFiles'])):
            for name in names:
                p=folder/name; p.parent.mkdir(parents=True,exist_ok=True)
                p.write_bytes(('synthetic:'+name).encode('ascii'))

    def build(self, name='candidate', profile=PROFILE):
        return builder.build(profile,self.publish,self.frontend,self.work/name,'0'*40,
            {'dotnet':'10.0.401','node':'24.21.0','npm':'11.19.0'},'synthetic fixture')

    def test_closed_43_includes_mfa_policy_and_full_catalog(self):
        result=self.build()
        manifest=json.loads((self.work/'candidate/manifest.json').read_text())
        self.assertEqual((43,71,53,18),(manifest['schema'],result['fileCount'],result['serverFiles'],result['frontendFiles']))
        self.assertIn('Otp.NET.dll',manifest['distributions']['server'])
        self.assertIn('database/015-mfa-account-policy.sql',manifest['distributions']['server'])
        self.assertIn('database/042-hardware-family-l.sql',manifest['distributions']['server'])
        self.assertIn('database/043-selected506l-hardware.sql',manifest['distributions']['server'])
        self.assertNotIn('RackClick.Server.exe',manifest['distributions']['server'])

    def test_each_required_sql_missing_stops_before_output(self):
        for sql in ('014-mfa.sql','015-mfa-account-policy.sql','042-hardware-family-l.sql','043-selected506l-hardware.sql'):
            p=self.publish/'database'/sql; content=p.read_bytes();p.unlink()
            try:
                with self.assertRaisesRegex(builder.DistributionError,'^server_sql_missing$'): self.build()
                self.assertFalse((self.work/'candidate').exists())
            finally:p.write_bytes(content)

    def test_extra_sql_rejected(self):
        (self.publish/'database/044-extra.sql').write_bytes(b'fixture')
        with self.assertRaisesRegex(builder.DistributionError,'^server_sql_extra$'): self.build()
        self.assertFalse((self.work/'candidate').exists())

    def test_apphost_rejected(self):
        (self.publish/'RackClick.Server.exe').write_bytes(b'MZ')
        with self.assertRaisesRegex(builder.DistributionError,'^server_application_extra$'):self.build()
        self.assertFalse((self.work/'candidate').exists())

    def test_frontend_missing_rejected(self):
        (self.frontend/'app.js').unlink()
        with self.assertRaisesRegex(builder.DistributionError,'^frontend_missing$'):self.build()
        self.assertFalse((self.work/'candidate').exists())

    def test_destination_preserved(self):
        p=self.work/'candidate';p.mkdir();(p/'keep').write_bytes(b'preserve')
        with self.assertRaisesRegex(builder.DistributionError,'^output_exists$'):self.build()
        self.assertEqual(b'preserve',(p/'keep').read_bytes())

    def test_copied_profile_not_authoritative(self):
        p=self.work/'profile.json';shutil.copyfile(PROFILE,p)
        with self.assertRaisesRegex(builder.DistributionError,'^profile_path_unexpected$'):self.build(profile=p)
        self.assertFalse((self.work/'candidate').exists())

    def test_reproducible_manifest_from_same_inputs(self):
        self.build('one');self.build('two')
        self.assertEqual((self.work/'one/manifest.json').read_bytes(),(self.work/'two/manifest.json').read_bytes())

    def test_legacy_profiles_remain_closed(self):
        for schema in (14,15):
            p=builder.load_profile(ROOT/f'docs/DISTRIBUCION{schema}-PERFIL.json')
            self.assertEqual(schema,p['applicationSchema'])
            self.assertEqual(10+schema,p['serverFileCount'])


@unittest.skipUnless(sys.platform=='win32' and CANDIDATE.is_dir(), 'requires the explicitly built Windows candidate43')
class Distribution43NativeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='distribution43-native-',dir=ROOT/'.local')
        self.addCleanup(self.temp.cleanup)
        self.copy=Path(self.temp.name)/'copy';shutil.copytree(CANDIDATE,self.copy)

    def verify(self, folder=None, pin=PIN):
        folder=folder or self.copy
        ps=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
        p=subprocess.run([str(ps),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',
            str(ROOT/'tools/windows/Test-ServerDistribution.ps1'),'-ManifestPath',str(folder/'manifest.json'),
            '-ExpectedManifestSha256',pin,'-ServerPath',str(folder/'server'),'-FrontendPath',str(folder/'frontend')],
            capture_output=True,text=True,timeout=45)
        result=json.loads(p.stdout.strip().splitlines()[-1]);self.assertEqual(p.returncode,result['exitCode'])
        return result

    def test_candidate71_verified(self):
        data=self.verify(CANDIDATE)
        self.assertEqual(('artifacts_verified',43,71,53,18),tuple(data[k] for k in ('code','schema','verifiedFiles','serverFiles','frontendFiles')))

    def test_wrong_external_pin_rejected(self):
        self.assertEqual('manifest_untrusted',self.verify(pin='0'*64)['code'])

    def test_manifest_changed_and_rehashed_is_not_a_known_candidate(self):
        p=self.copy/'manifest.json';d=json.loads(p.read_text());d['sourceStatus']='synthetic tamper';p.write_text(json.dumps(d))
        self.assertEqual('manifest_distribution_unsupported',self.verify(pin=hashlib.sha256(p.read_bytes()).hexdigest())['code'])

    def test_missing_sql43_rejected(self):
        (self.copy/'server/database/043-selected506l-hardware.sql').unlink()
        self.assertEqual('distribution_files_missing',self.verify()['code'])

    def test_changed_mfa_policy_rejected(self):
        with (self.copy/'server/database/015-mfa-account-policy.sql').open('ab') as f:f.write(b'-- synthetic mutation')
        self.assertEqual('artifact_hash_mismatch',self.verify()['code'])

    def test_changed_frontend_rejected(self):
        with (self.copy/'frontend/app.js').open('ab') as f:f.write(b'/*synthetic*/')
        self.assertEqual('artifact_hash_mismatch',self.verify()['code'])

    def test_extra_apphost_rejected(self):
        (self.copy/'server/RackClick.Server.exe').write_bytes(b'MZ')
        self.assertEqual('distribution_files_extra',self.verify()['code'])

    def test_historical15_still_verified(self):
        legacy=ROOT/'.local/distribution15/candidata-09'
        self.assertTrue(legacy.is_dir(),'historical fixture must exist in this review environment')
        data=self.verify(legacy,'294b61577ed7aa8fe68ddb1ecd6c4f11a20b4f03935c11a22404009aec6a00fb')
        self.assertEqual(('artifacts_verified',15,43),tuple(data[k] for k in ('code','schema','verifiedFiles')))


if __name__=='__main__':unittest.main()
