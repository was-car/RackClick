"""SQL-protected application43 and 26-operator profile, no bundle/installer/DB.

Native distribution checks read copied public artifacts only. The native layout
focus uses synthetic manifest/entry metadata in memory, never a fake accepted ZIP.
"""
import base64
from contextlib import ExitStack
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
import build_server_distribution as distribution
import package_offline_bundle as bundle

PROFILE = ROOT/'docs/DISTRIBUCION43-SQL-PERFIL.json'
CANDIDATE = ROOT/'.local/sql-integracion-12/distribution'
PIN = '29685419d0746df89777a5da72d25f5b7ac0e571e30decec1888787fe5f0f950'
OLD_PIN = 'd352c04381cd4f1954aa43735e540970b295f231106560c5c9880c7ee1dc78db'
PS = Path(os.environ.get('SystemRoot', r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


class SqlProtectedDistribution(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sql-distribution-', dir=ROOT/'.local')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def powershell(self, script):
        encoded = base64.b64encode(("$ProgressPreference='SilentlyContinue'\n[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)\n"+script).encode('utf-16le')).decode('ascii')
        p = subprocess.run([str(PS), '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                           capture_output=True, text=True, encoding='utf-8-sig', timeout=90)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, '')
        return json.loads(p.stdout)

    def verify(self, folder=CANDIDATE, pin=PIN):
        p = subprocess.run([str(PS), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
            '-File', str(ROOT/'tools/windows/Test-ServerDistribution.ps1'),
            '-ManifestPath', str(folder/'manifest.json'), '-ExpectedManifestSha256', pin,
            '-ServerPath', str(folder/'server'), '-FrontendPath', str(folder/'frontend')],
            capture_output=True, text=True, encoding='utf-8-sig', timeout=60)
        self.assertEqual(p.stderr, '')
        row = json.loads(p.stdout)
        self.assertEqual(p.returncode, row['exitCode'])
        return row

    def synthetic_inputs(self):
        profile = json.loads(PROFILE.read_bytes())
        pub, front = self.work/'publish', self.work/'frontend'
        for root, names in [(pub, profile['serverApplicationFiles']+profile['serverSqlFiles']),
                            (front, profile['frontendFiles'])]:
            for name in names:
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(('synthetic:'+name).encode())
        return pub, front

    def test_01_generator_has_new_profile_without_altering_historical_definitions(self):
        profile = distribution.load_profile(PROFILE)
        self.assertEqual((profile['profileId'], profile['applicationSchema'], profile['serverFileCount'], profile['frontendFileCount']),
                         ('schema43-sql-protected-01', 43, 53, 18))
        pub, front = self.synthetic_inputs()
        args = (PROFILE, pub, front, self.work/'generated', '7b4f3e8a9eb9b7278f0347b3cdd473348966e821',
                {'dotnet':'10.0.401','node':'24.21.0','npm':'11.19.0'}, 'synthetic fixture')
        result = distribution.build(*args)
        self.assertEqual((result['fileCount'], result['serverFiles'], result['frontendFiles']), (71, 53, 18))
        before = ROOT/'evidence/s1-20261102/cierre-bloqueantes-01-07/distribucion/antes/docs'
        for name in ['DISTRIBUCION43-PERFIL.json', 'DISTRIBUCION43-PUNTO3-PERFIL.json']:
            self.assertEqual((ROOT/'docs'/name).read_bytes(), (before/name).read_bytes())

    def test_02_copied_profile_cannot_authorize_a_distribution(self):
        pub, front = self.synthetic_inputs()
        copy = self.work/'profile.json'
        shutil.copyfile(PROFILE, copy)
        with self.assertRaisesRegex(distribution.DistributionError, '^profile_path_unexpected$'):
            distribution.build(copy, pub, front, self.work/'must-not-exist', '0'*40, {}, 'synthetic')
        self.assertFalse((self.work/'must-not-exist').exists())

    def test_03_native_real_candidate71_verified(self):
        row = self.verify()
        self.assertEqual((row['code'], row['schema'], row['verifiedFiles'], row['serverFiles'], row['frontendFiles']),
                         ('artifacts_verified',43,71,53,18))

    def test_04_native_unknown_external_pin_rejected(self):
        self.assertEqual(self.verify(pin='0'*64)['code'], 'manifest_untrusted')

    def test_05_native_rehashed_unknown_registration_rejected(self):
        folder = self.work/'unknown'
        folder.mkdir()
        value = json.loads((CANDIDATE/'manifest.json').read_bytes())
        value['sourceStatus'] = 'synthetic unregistered change'
        (folder/'manifest.json').write_text(json.dumps(value), encoding='utf-8')
        self.assertEqual(self.verify(folder, sha(folder/'manifest.json'))['code'], 'manifest_distribution_unsupported')

    def test_06_native_modified_artifact_rejected(self):
        folder = self.work/'changed'
        shutil.copytree(CANDIDATE, folder)
        with (folder/'server/RackClick.Server.dll').open('ab') as stream:
            stream.write(b'synthetic-mutation')
        self.assertEqual(self.verify(folder)['code'], 'artifact_hash_mismatch')

    def test_07_native_missing_sql_rejected(self):
        folder = self.work/'missing'
        shutil.copytree(CANDIDATE, folder)
        (folder/'server/database/043-selected506l-hardware.sql').unlink()
        self.assertEqual(self.verify(folder)['code'], 'distribution_files_missing')

    def test_08_collector_uses_exact_new_pin_metadata_and_application(self):
        payloads, folder = bundle.collect_application(CANDIDATE/'manifest.json', PIN)
        self.assertEqual(folder, CANDIDATE)
        self.assertEqual(len(payloads), 74)
        self.assertEqual(sum(len(p.data) for p in payloads if p.path.startswith(('application/server/', 'application/frontend/'))), 25650673)
        for name, digest in [('inventory.json','86ad16f9295fbd71c6aae78a403a2c336e15d284897ae4216d341b8d040ef40c'),
                             ('SHA256SUMS.txt','e2cb5728431bfa51bf66d2d4b17760a8d70a3d66a30595ead24bc39cf5e8baac')]:
            self.assertEqual(sha(folder/name), digest)

    def test_09_collector_cannot_read_same_manifest_from_another_local_area(self):
        copy = self.work/'manifest.json'
        shutil.copyfile(CANDIDATE/'manifest.json', copy)
        with self.assertRaisesRegex(bundle.BundleError, '^application_root_invalid$'):
            bundle.collect_application(copy, PIN)

    def test_10_current_and_historical_operator_selection_is_explicit(self):
        self.assertEqual(len(bundle.operator_names(PIN)),26)
        self.assertEqual(len(bundle.operator_names(OLD_PIN)),25)
        self.assertEqual(set(bundle.operator_names(PIN))-set(bundle.operator_names(OLD_PIN)), {'RackClick.SqlSecrets.ps1'})
        with self.assertRaisesRegex(bundle.BundleError, '^application_pin_mismatch$'):
            bundle.operator_names('0'*64)

    def test_11_missing_sql_module_fails_before_outputs_or_archives(self):
        sdk, pg, lock = [self.work/n for n in ('sdk.zip','postgres.zip','lock.json')]
        for p in (sdk, pg, lock):
            p.write_bytes(b'synthetic-unused')
        original = bundle.workspace_path
        def missing(name):
            if name == 'tools/windows/RackClick.SqlSecrets.ps1':
                raise bundle.BundleError('source_missing_or_wrong_type')
            return original(name)
        with patch.object(bundle, 'collect_locks', return_value=({}, {}, [], [], [])), \
             patch.object(bundle, 'workspace_path', side_effect=missing), \
             patch.object(bundle, 'archive_slice') as archive:
            with self.assertRaisesRegex(bundle.BundleError, '^source_missing_or_wrong_type$'):
                bundle.build(CANDIDATE/'manifest.json', PIN, sdk, pg, lock, self.work/'must-not.zip', self.work/'no-evidence')
            archive.assert_not_called()
        self.assertFalse((self.work/'must-not.zip').exists())
        self.assertFalse((self.work/'no-evidence').exists())

    def test_12_legacy_build_cannot_silently_omit_a_current_dependency(self):
        sdk, pg, lock = [self.work/n for n in ('sdk.zip','postgres.zip','lock.json')]
        for p in (sdk, pg, lock):
            p.write_bytes(b'synthetic-unused')
        source = self.work/'operator.ps1'
        source.write_bytes(b". (Join-Path $PSScriptRoot 'RackClick.SqlSecrets.ps1')")
        with patch.object(bundle, 'collect_application', return_value=([], self.work)), \
             patch.object(bundle, 'collect_locks', return_value=({}, {}, [], [], [])), \
             patch.object(bundle, 'workspace_path', return_value=source), \
             patch.object(bundle, 'archive_slice') as archive:
            with self.assertRaisesRegex(bundle.BundleError, '^operator_dependency_missing$'):
                bundle.build(CANDIDATE/'manifest.json', OLD_PIN, sdk, pg, lock, self.work/'must-not.zip', self.work/'no-evidence')
            archive.assert_not_called()
        self.assertFalse((self.work/'must-not.zip').exists())

    def test_13_historical_profile_tables_and_licenses_remain_identical(self):
        path = ROOT/'evidence/s1-20261102/cierre-bloqueantes-01-07/distribucion/antes/tools/package_offline_bundle.py'
        spec = importlib.util.spec_from_file_location('historical_bundle_sql_test', path)
        old = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = old
        spec.loader.exec_module(old)
        self.assertEqual({k:v for k,v in bundle.APPLICATION_PROFILES.items() if k != PIN}, old.APPLICATION_PROFILES)
        self.assertEqual(bundle.OPERATORS, old.OPERATORS)
        self.assertEqual(bundle.SOURCE_PINS, old.SOURCE_PINS)
        self.assertEqual(bundle.SOURCE_PINS_14, old.SOURCE_PINS_14)
        self.assertEqual(bundle.ARCHIVE_PINS, old.ARCHIVE_PINS)
        self.assertEqual(bundle.VERSIONS, old.VERSIONS)

    def test_14_frontend_is_the_current_pinned_punto3_without_regression(self):
        current = json.loads((CANDIDATE/'manifest.json').read_bytes())
        previous = json.loads((ROOT/'.local/distribution43/punto3-01/manifest.json').read_bytes())
        self.assertEqual(current['distributions']['frontend'], previous['distributions']['frontend'])
        published = ROOT/'.local/sql-integracion-12/publish'
        for rel, digest in current['distributions']['server'].items():
            self.assertEqual(sha(published/rel), digest)

    def test_15_native_layout_requires_the_new_operator_and_preserves_25_legacy(self):
        module = str(ROOT/'tools/windows/RackClick.OfflineBundle.ps1').replace("'", "''")
        script = r'''
. '__MODULE__'
function Make-Layout([string]$Pin){
 $profile=Get-OfflineBundleApplicationProfile $Pin;$files=[ordered]@{};$entries=@{}
 function Add([string]$Name,[long]$Size=1,[string]$Hash=('a'*64)){$files[$Name]=[pscustomobject]@{bytes=$Size;sha256=$Hash};$entries[$Name]=[pscustomobject]@{FullName=$Name;Length=$Size}}
 Add 'application/manifest.json' 1 $Pin
 for($i=0;$i-lt$profile.server;$i++){Add ('application/server/f'+$i+'.dll') $(if($i-eq0){$profile.bytes-$profile.server-$profile.frontend+1}else{1})}
 for($i=0;$i-lt$profile.frontend;$i++){Add ('application/frontend/f'+$i+'.js')}
 foreach($name in (Get-OfflineBundleOperatorNames $profile)){Add ('operators/'+$name)}
 $net=@('dotnet.exe','LICENSE.txt','ThirdPartyNotices.txt','host/fxr/10.0.12/hostfxr.dll','shared/Microsoft.NETCore.App/10.0.12/System.Private.CoreLib.dll','shared/Microsoft.AspNetCore.App/10.0.12/Microsoft.AspNetCore.dll')
 for($i=$net.Count;$i-lt339;$i++){$net+=('shared/Microsoft.NETCore.App/10.0.12/f'+$i+'.dll')};foreach($n in $net){Add ('dependencies/dotnet/'+$n)}
 $pg=@('bin/postgres.exe','bin/initdb.exe','bin/pg_ctl.exe','bin/psql.exe','bin/pg_dump.exe','bin/pg_restore.exe','commandlinetools_3rd_party_licenses.txt','pgAdmin_3rd_party_licenses.txt','pgAdmin_license.txt','server_license.txt','StackBuilder_3rd_party_licenses.txt')
 for($i=$pg.Count;$i-lt1568;$i++){$pg+=('bin/f'+$i+'.dll')};foreach($n in $pg){Add ('dependencies/postgresql/'+$n)}
 foreach($n in @('MANUAL-PAQUETE-WINDOWS-S1.md','CONSTRUIR-PAQUETE-WINDOWS-S1.md','OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md','RECUPERACION-DESPLIEGUE-WINDOWS-S1.md')){Add ('docs/'+$n)}
 Add 'prerequisites/vc_redist.x64.exe' 1 '843068991daaa1f73ad9f6239bce4d0f6a07a51f18c37ea2a867e9beca71295c'
 Add 'licenses/Npgsql-LICENSE' 1 '2e1d9cc6ed4eb7fe6fa82091846c06b4f58571a2c3b54777db6baeca10dd2d74';Add 'licenses/README.txt'
 foreach($n in $profile.metadata.Keys){Add ('application/'+$n) 1 $profile.metadata[$n]};foreach($n in $profile.notices.Keys){Add $n 1 $profile.notices[$n]}
 $manifest=[pscustomobject]@{schemaVersion=1;kind='RackClickOfflineBundle';platform='win-x64';id='aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee';applicationManifestSha256=$Pin;versions=[pscustomobject]@{schema=43;dotnetRuntime='10.0.12';postgresql='17.11';vcRedist='14.51.36247.0';vcRuntimeMinimum='14.44.35211.0'};files=[pscustomobject]$files}
 $entries['bundle.json']=[pscustomobject]@{FullName='bundle.json';Length=1};return @{manifest=$manifest;entries=$entries}
}
$new=Make-Layout '29685419d0746df89777a5da72d25f5b7ac0e571e30decec1888787fe5f0f950';$newCounts=Assert-OfflineBundleLayout $new.manifest $new.entries
$legacy=Make-Layout 'd352c04381cd4f1954aa43735e540970b295f231106560c5c9880c7ee1dc78db';$oldCounts=Assert-OfflineBundleLayout $legacy.manifest $legacy.entries
$new.manifest.files.PSObject.Properties.Remove('operators/RackClick.SqlSecrets.ps1');$new.entries.Remove('operators/RackClick.SqlSecrets.ps1');$missing=''
try{$null=Assert-OfflineBundleLayout $new.manifest $new.entries}catch{$missing=$_.Exception.Data['bundleCode']}
@{newOperators=$newCounts.operators;legacyOperators=$oldCounts.operators;missingModuleCode=$missing;actualZipVerified=$false}|ConvertTo-Json -Compress
'''.replace('__MODULE__', module)
        row = self.powershell(script)
        self.assertEqual((row['newOperators'], row['legacyOperators']), (26,25))
        self.assertEqual(row['missingModuleCode'], 'layout_counts_invalid')
        self.assertFalse(row['actualZipVerified'])


class SqlOfflineArchiveNative(unittest.TestCase):
    """Real ZIP negatives after the independently pinned internal bundle exists."""
    ARCHIVE = ROOT/'.local/sql-integracion-12/RackClick-Bundle-SQL-12.zip'
    ARCHIVE_PIN = '3af40fb4af7466a13452a42ccbc50b12951c832e18efeab090daaa81301f1a3e'

    def setUp(self):
        self.assertEqual(sha(self.ARCHIVE), self.ARCHIVE_PIN)
        self.temp = tempfile.TemporaryDirectory(prefix='sql-bundle-native-', dir=ROOT/'.local')
        self.work = Path(self.temp.name)
        def cleanup():
            target = self.work.resolve()
            assert target.is_relative_to(ROOT/'.local') and target.name.startswith('sql-bundle-native-')
            self.temp.cleanup()
        self.addCleanup(cleanup)

    def native(self, path, pin):
        p = subprocess.run([str(PS), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
            '-File', str(ROOT/'tools/windows/Test-RackClickOfflineBundle.ps1'),
            '-ArchivePath', str(path), '-ExpectedArchiveSha256', pin],
            capture_output=True, text=True, encoding='utf-8-sig', timeout=120)
        self.assertEqual(p.stderr, '')
        row = json.loads(p.stdout)
        self.assertEqual(p.returncode, row['exitCode'])
        return row

    def changed_archive(self, label):
        import zipfile
        out = self.work/(label+'.zip')
        with zipfile.ZipFile(self.ARCHIVE) as source:
            manifest = json.loads(source.read('bundle.json'))
            missing = 'operators/RackClick.SqlSecrets.ps1'
            target = 'application/server/RackClick.Server.dll'
            changed = None
            if label == 'missing-module':
                del manifest['files'][missing]
            else:
                changed = bytearray(source.read(target))
                changed[-1] ^= 1
                manifest['files'][target]['sha256'] = hashlib.sha256(changed).hexdigest()
            with zipfile.ZipFile(out, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as destination:
                for entry in source.infolist():
                    if label == 'missing-module' and entry.filename == missing:
                        continue
                    data = bundle.json_bytes(manifest) if entry.filename == 'bundle.json' else changed if changed is not None and entry.filename == target else source.read(entry)
                    destination.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=1)
        return out

    def test_16_real_reference_control_already_verified_without_repeating_it(self):
        evidence = ROOT/'evidence/s1-20261102/cierre-bloqueantes-01-07/distribucion'
        row = json.loads((evidence/'BUNDLE-NATIVO.json').read_text(encoding='utf-8-sig'))
        self.assertTrue(row['valid'])
        self.assertEqual(row['code'], 'bundle_verified')
        self.assertEqual(row['counts']['operators'], 26)
        self.assertEqual(row['verifiedFiles'], 2016)
        contents = json.loads((evidence/'BUNDLE-CONTENIDO.json').read_bytes())
        self.assertTrue(contents['allOperatorsMatchCurrentSources'])

    def test_17_real_zip_missing_module_with_consistent_inventory_is_rejected(self):
        path = self.changed_archive('missing-module')
        row = self.native(path, sha(path))
        self.assertFalse(row['valid'])
        self.assertEqual(row['code'], 'layout_counts_invalid')

    def test_18_real_zip_altered_dll_with_consistent_inventory_still_rejects(self):
        path = self.changed_archive('changed-dll')
        row = self.native(path, sha(path))
        self.assertFalse(row['valid'])
        self.assertEqual(row['code'], 'application_manifest_invalid')


if __name__ == '__main__':
    unittest.main(verbosity=2)
