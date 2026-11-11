"""Metadata-only Demo50 edition03; no DB, VM or installed instance."""
import copy
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
SPEC = importlib.util.spec_from_file_location('demo50_trilingual', ROOT / 'tools/build_demo50_trilingual.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class TrilingualData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, cls.replay = builder.read_base()
        cls.files, cls.renamed = builder.transform(cls.base, cls.replay)

    def test_50_unique_fixed_names_and_language_distribution(self):
        names = builder.name_map()
        self.assertEqual(list(names), [f'c{i:02}' for i in range(1, 51)])
        self.assertEqual(len({x['name'] for x in names.values()}), 50)
        self.assertEqual({lang: sum(x['language'] == lang for x in names.values()) for lang in ('en', 'de', 'es')}, {'en': 17, 'de': 17, 'es': 16})
        self.assertIn('Büro', names['c02']['name'])
        self.assertIn('Papelería', names['c03']['name'])

    def test_only_company_name_language_metadata_changed(self):
        for name in ('manifest.json', 'plan.json'):
            old = builder.parse(self.base[name])
            new = builder.parse(self.files[name])
            for before, after in zip(old['customers'], new['customers'], strict=True):
                after['name'] = before['name']
                after['language'] = before['language']
            self.assertEqual(old, new)
        for name, data in self.base.items():
            if name.endswith('.inventory.json') or name in ('coverage-matrix.json', 'COBERTURA-868.csv'):
                self.assertEqual(data, self.files[name], name)

    def test_replay_only_name_changed_and_topology_kept(self):
        reverted = copy.deepcopy(self.renamed)
        for before, after in zip(self.replay['customers'], reverted['customers'], strict=True):
            after['name'] = before['name']
        self.assertEqual(reverted, self.replay)
        self.assertEqual(sum(len(c['commands']) for c in self.renamed['customers']), 2553)
        self.assertEqual(self.renamed['counts'], builder.COUNTS)
        self.assertEqual(self.renamed['schemaVersion'], 43)
        self.assertFalse(self.renamed['securityIncluded'])

    def test_overlay_missing_extra_duplicate_or_changed_structure_rejected(self):
        names = builder.name_map()
        for change in ('missing', 'extra', 'duplicate', 'field', 'language'):
            with self.subTest(change=change):
                altered = copy.deepcopy(names)
                if change == 'missing':
                    altered.pop('c50')
                elif change == 'extra':
                    altered['c51'] = copy.deepcopy(altered['c50'])
                elif change == 'duplicate':
                    altered['c02']['name'] = altered['c01']['name']
                elif change == 'field':
                    altered['c01']['commands'] = []
                else:
                    altered['c01']['language'] = 'fr'
                with self.assertRaises(ValueError):
                    builder.transform(self.base, self.replay, altered)

    def test_mutated_inventory_command_or_customer_id_rejected(self):
        for change in ('inventory', 'command', 'id', 'extra'):
            with self.subTest(change=change):
                base = dict(self.base)
                replay = copy.deepcopy(self.replay)
                if change == 'inventory':
                    base['c01.inventory.json'] += b' '
                elif change == 'command':
                    replay['customers'][0]['commands'][0]['payload']['unexpected'] = 'changed'
                elif change == 'id':
                    replay['customers'][0]['sourceCustomerId'] = replay['customers'][1]['sourceCustomerId']
                else:
                    base['extra.txt'] = b'extra'
                with self.assertRaises(ValueError):
                    builder.transform(base, replay)

    def test_reproducible_package_and_verified_closed_members(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.local') as temporary:
            a = builder.build(Path(temporary) / 'one')
            b = builder.build(Path(temporary) / 'two')
            self.assertEqual(a['zipSha256'], b['zipSha256'])
            report = builder.verify(Path(a['zipPath']))
            self.assertEqual(report['customers'], 50)
            self.assertEqual(report['targetSchema'], 48)
            with zipfile.ZipFile(a['zipPath']) as archive:
                self.assertEqual(len(archive.namelist()), len(set(archive.namelist())))
                loader = archive.read(builder.PREFIX + 'CARGAR-50-CLIENTES/Import-RackClickDemo50.ps1')
                self.assertIn(a['replaySha256'].encode(), loader)
                self.assertIn(b"demo_schema48_required", loader)
            with self.assertRaisesRegex(ValueError, 'output_exists'):
                builder.build(Path(temporary) / 'one')

    def test_package_tamper_extra_unknown_digest_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.local') as temporary:
            result = builder.build(Path(temporary) / 'build')
            source = Path(result['zipPath'])
            for change in ('bytes', 'extra', 'self_rehashed'):
                altered = Path(temporary) / (change + '.zip')
                with zipfile.ZipFile(source) as z:
                    members = {n: z.read(n) for n in z.namelist()}
                if change == 'extra':
                    members[builder.PREFIX + 'extra.txt'] = b'extra'
                else:
                    key = builder.PREFIX + 'DATOS-DEMO50/c01.inventory.json'
                    members[key] += b' '
                    if change == 'self_rehashed':
                        sumskey = builder.PREFIX + 'SHA256SUMS.txt'
                        members[sumskey] = builder.sums({n.removeprefix(builder.PREFIX): v for n, v in members.items() if n != sumskey})
                builder.write_zip(altered, {n.removeprefix(builder.PREFIX): v for n, v in members.items()})
                with self.assertRaises(ValueError):
                    builder.verify(altered)
            with self.assertRaisesRegex(ValueError, 'zip_digest_mismatch'):
                builder.verify(source, '0' * 64)

    def test_historical_base_still_pinned(self):
        files, replay = builder.read_base()
        self.assertEqual(hashlib.sha256(files['SHA256SUMS.txt']).hexdigest(), builder.BASE_SUMS_SHA)
        self.assertEqual(hashlib.sha256(builder.BASE_REPLAY.read_bytes()).hexdigest(), builder.BASE_REPLAY_SHA)

    def test_loader_security_unchanged_besides_explicit_pin_and_target(self):
        old = (ROOT / 'tools/windows/demo50/Import-RackClickDemo50.ps1').read_text(encoding='ascii')
        new = (ROOT / 'tools/windows/demo50-v3/Import-RackClickDemo50.ps1').read_text(encoding='ascii')
        expected = old.replace('<# Optional inventory-only Demo50 loader. No SQL, account changes or MFA bypass.', '<# Demo50 edition03: fixed EN/DE/ES names, source43 to target48 only.\n   Optional inventory-only loader. No SQL, account changes or MFA bypass.')
        expected = expected.replace(builder.BASE_REPLAY_SHA, '44f7fca5dd78b10de1a5efbb51f34cff488974ed264bfcf9ea72059b1194216d')
        expected = expected.replace("$health.status-cne'ready'-or$health.schemaVersion-ne43", "$health.status-cne'ready'-or$health.schemaVersion-isnot[int]-or$health.schemaVersion-ne48")
        expected = expected.replace('demo_schema43_required', 'demo_schema48_required')
        self.assertEqual(new, expected)
        command = (ROOT / 'tools/windows/demo50-v3/CARGAR-50-CLIENTES.cmd').read_bytes()
        self.assertEqual(command.count(b'\r\n'), command.count(b'\n'))

    def test_viewer_escapes_name_as_data(self):
        names = builder.name_map()
        names['c01']['name'] = '<script>alert("synthetic fixture")</script>'
        files, _ = builder.transform(self.base, self.replay, names)
        viewer = files['VER-50-CLIENTES.html']
        self.assertNotIn(names['c01']['name'].encode(), viewer)
        self.assertIn(b'\\u003cscript\\u003e', viewer)
        self.assertIn(b'td.textContent=String(v)', viewer)

    def test_native_loader_ascii_and_powershell51_parser(self):
        path = ROOT / 'tools/windows/demo50-v3/Import-RackClickDemo50.ps1'
        self.assertTrue(path.read_bytes().isascii())
        command = "$tokens=$null;$errors=$null;[Management.Automation.Language.Parser]::ParseFile('" + str(path) + "',[ref]$tokens,[ref]$errors)|Out-Null;if($errors.Count){exit 1}"
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command], capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))

    def test_native_only_typed_target48_reaches_authentication(self):
        path = ROOT / 'tools/windows/demo50-v3/Import-RackClickDemo50.ps1'
        code = ". '" + str(path) + "';" + r'''
function Read-Demo50Plan {return @{customers=@()}}
function Invoke-Demo50Http($Context,[string]$Method,[string]$Route,$Body=$null,[hashtable]$Headers=@{},[int[]]$Expected=@(200)) {
 if($Route-ceq'/health/ready'){return @{data=@{status='ready';schemaVersion=$script:fixtureSchema}}}
 throw 'demo_fixture_auth_reached'
}
$secure=New-Object Security.SecureString;foreach($character in 'fixture-not-a-real-password'.ToCharArray()){$secure.AppendChar($character)}
$credential=[Management.Automation.PSCredential]::new('fixture',$secure)
$results=@()
foreach($s in @(43,45,48,999,'48',48.0)) {
 $script:fixtureSchema=$s
 try{$null=Invoke-Demo50Import -Origin 'https://demo.invalid' -PlanPath 'unused' -ExpectedPlanSha256 'unused' -Credential $credential;$results+='unexpected_success'}
 catch{$results+=$_.Exception.Message}
}
$secure.Dispose()
ConvertTo-Json -InputObject $results -Compress
'''
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', base64.b64encode(code.encode('utf-16le')).decode()], capture_output=True, timeout=35)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        output = result.stdout.decode('utf-8-sig')
        values = json.loads(output[output.rfind('\n['):].strip() if '\n[' in output else output.strip())
        self.assertEqual(values, ['demo_schema48_required', 'demo_schema48_required', 'demo_fixture_auth_reached', 'demo_schema48_required', 'demo_schema48_required', 'demo_schema48_required'])


if __name__ == '__main__':
    unittest.main()
