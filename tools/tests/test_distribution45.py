"""Schema45 packaging negatives; no VM, installation, database or account changes."""
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
import build_server_distribution as builder
import package_offline_bundle as bundle

PROFILE = ROOT/'docs/DISTRIBUCION45-SQL-PERFIL.json'
CANDIDATE = ROOT/'.local/distribution45/sql-01'
PIN = '528a03d2efc939d1cea631b1caa9f3e6a445e44257fa757f87a95691acfb6933'
PS = Path('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')


class Distribution45Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='distribution45-', dir=ROOT/'.local')
        self.work = Path(self.temp.name).resolve()
        self.assertTrue(self.work.is_relative_to((ROOT/'.local').resolve()))
        self.addCleanup(self.temp.cleanup)

    def invoke(self, script):
        raw = ("$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"+script).encode('utf-16le')
        p = subprocess.run([str(PS), '-NoProfile', '-NonInteractive', '-EncodedCommand', base64.b64encode(raw).decode()], capture_output=True, text=True, encoding='utf-8-sig', timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, '')
        return json.loads(p.stdout)

    def verify(self, path=CANDIDATE, pin=PIN):
        args = [str(PS), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT/'tools/windows/Test-ServerDistribution.ps1'), '-ManifestPath', str(path/'manifest.json'), '-ExpectedManifestSha256', pin, '-ServerPath', str(path/'server'), '-FrontendPath', str(path/'frontend')]
        p = subprocess.run(args, capture_output=True, text=True, encoding='utf-8-sig', timeout=60)
        self.assertEqual(p.stderr, '')
        result = json.loads(p.stdout)
        self.assertEqual(p.returncode, result['exitCode'])
        return result

    def synthetic(self):
        p = json.loads(PROFILE.read_text(encoding='utf-8'))
        for folder, names in [('publish',p['serverApplicationFiles']+p['serverSqlFiles']),('front',p['frontendFiles'])]:
            for name in names:
                target=self.work/folder/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(('synthetic:'+name).encode())
        return self.work/'publish',self.work/'front'

    def build(self, pub, front, profile=PROFILE):
        return builder.build(profile,pub,front,self.work/'built','0'*40,{'dotnet':'10.0.401'},'synthetic fixture')

    def test_closed_profile45_and_historical43_unmodified(self):
        p=builder.load_profile(PROFILE)
        self.assertEqual((p['profileId'],p['applicationSchema'],p['serverFileCount'],p['frontendFileCount']),('schema45-sql-protected-01',45,55,18))
        pub,front=self.synthetic();self.assertEqual(self.build(pub,front)['fileCount'],73)
        historical=builder.load_profile(builder.PROFILE43_SQL_PATH)
        self.assertEqual(historical['candidate']['manifestSha256'],'29685419d0746df89777a5da72d25f5b7ac0e571e30decec1888787fe5f0f950')

    def test_copied_profile_cannot_authorize(self):
        pub,front=self.synthetic();copy=self.work/'profile.json';shutil.copyfile(PROFILE,copy)
        with self.assertRaisesRegex(builder.DistributionError,'^profile_path_unexpected$'):self.build(pub,front,copy)
        self.assertFalse((self.work/'built').exists())

    def test_missing_new_sql_fails_before_output(self):
        pub,front=self.synthetic()
        for name in ['044-german-cpe-hardware.sql','045-german-repeaters-hardware.sql']:
            with self.subTest(name=name):
                path=pub/'database'/name;raw=path.read_bytes();path.unlink()
                try:
                    with self.assertRaisesRegex(builder.DistributionError,'^server_sql_missing$'):self.build(pub,front)
                    self.assertFalse((self.work/'built').exists())
                finally:path.write_bytes(raw)

    def test_publish_with_apphost_rejected(self):
        pub,front=self.synthetic();(pub/'RackClick.Server.exe').write_bytes(b'MZ')
        with self.assertRaisesRegex(builder.DistributionError,'^server_application_extra$'):self.build(pub,front)
        self.assertFalse((self.work/'built').exists())

    def test_native73_files(self):
        p=self.verify();self.assertEqual((p['code'],p['schema'],p['verifiedFiles'],p['serverFiles'],p['frontendFiles']),('artifacts_verified',45,73,55,18))

    def test_wrong_external_digest(self):
        self.assertEqual(self.verify(pin='0'*64)['code'],'manifest_untrusted')

    def test_rehashed_unknown_manifest_rejected(self):
        copy=self.work/'candidate';shutil.copytree(CANDIDATE,copy)
        p=copy/'manifest.json';doc=json.loads(p.read_text());doc['scope']='changed';p.write_text(json.dumps(doc),encoding='utf-8')
        self.assertEqual(self.verify(copy,hashlib.sha256(p.read_bytes()).hexdigest())['code'],'manifest_distribution_unsupported')

    def test_modified_dll_or_frontend_rejected(self):
        copy=self.work/'candidate';shutil.copytree(CANDIDATE,copy)
        for name in ['server/RackClick.Server.dll','frontend/app.js']:
            with self.subTest(name=name):
                p=copy/name;raw=p.read_bytes();p.write_bytes(raw+b'changed')
                try:self.assertEqual(self.verify(copy)['code'],'artifact_hash_mismatch')
                finally:p.write_bytes(raw)

    def test_real_missing_sql_and_extra_apphost_rejected(self):
        copy=self.work/'candidate';shutil.copytree(CANDIDATE,copy)
        p=copy/'server/database/045-german-repeaters-hardware.sql';raw=p.read_bytes();p.unlink()
        self.assertEqual(self.verify(copy)['code'],'distribution_files_missing');p.write_bytes(raw)
        (copy/'server/RackClick.Server.exe').write_bytes(b'MZ');self.assertEqual(self.verify(copy)['code'],'distribution_files_extra')

    def test_operator_profile45_remains_sql_protected(self):
        self.assertEqual(bundle.application_schema(PIN),45)
        self.assertEqual(len(bundle.operator_names(PIN)),26)
        self.assertIn('RackClick.SqlSecrets.ps1',bundle.operator_names(PIN))
        actual=self.invoke(". '"+str(ROOT/'tools/windows/RackClick.Instance.ps1')+"'; $role='rc_runtime_'+('a'*32); $owner='rc_owner_'+('a'*32); @{count=(Get-StageVerifiedFileCount 45);grants=(Get-InstanceRuntimeGrantsSql $role 45);missing=(Get-InstanceMissingTableRightsSql $role $owner 45)}|ConvertTo-Json -Compress")
        self.assertEqual(actual['count'],73)
        self.assertIn('REVOKE ALL PRIVILEGES ON TABLE public.hardware_definition',actual['grants'])
        self.assertIn('GRANT SELECT ON TABLE public.hardware_definition',actual['grants'])
        self.assertIn('NOT has_table_privilege',actual['missing'])

    def test_native_historical43_still_valid(self):
        p=self.verify(ROOT/'.local/sql-integracion-12/distribution','29685419d0746df89777a5da72d25f5b7ac0e571e30decec1888787fe5f0f950')
        self.assertEqual((p['code'],p['schema'],p['verifiedFiles']),('artifacts_verified',43,71))

    def test_native_parser_owned_scripts(self):
        names=json.loads((ROOT/'evidence/s1-20261103/actualizacion45/package/BEFORE.json').read_text())
        scripts=[str(ROOT/n).replace("'","''") for n in names if n.endswith('.ps1')]
        result=self.invoke("$failed=@();foreach($f in @("+','.join("'"+s+"'" for s in scripts)+")){$tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile($f,[ref]$tokens,[ref]$errors);if($errors.Count){$failed+=$f}};@{scripts="+str(len(scripts))+";failed=$failed}|ConvertTo-Json -Compress")
        self.assertEqual(result['failed'],[])


if __name__=='__main__':unittest.main(verbosity=2)
