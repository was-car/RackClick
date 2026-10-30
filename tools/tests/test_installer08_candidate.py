"""Independent content checks of the generated internal 08 artifacts; no install."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'.local/instalador-08-codex'
DELIVERY=RUN/'entrega'
BASE=ROOT/'.local/instalador-07/entrega'
APP='e9c58c0c67500afc09c1ac979a7433830c96f94c2a2e4501d81286796d65d74d'
OLD_BUNDLE='6d5a3896422c308e6b086822aaaa76a5fb6cc2584cf0664666f96504709e14f8'
sha=lambda data:hashlib.sha256(data).hexdigest()


class Installer08Candidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (DELIVERY/'BUILD-08.json').is_file():
            raise unittest.SkipTest('Requires explicitly generated local 08 candidate; not an acceptance result in a clean clone')
        cls.build=json.loads((DELIVERY/'BUILD-08.json').read_text())
        cls.sources=json.loads((DELIVERY/'FUENTES-08.json').read_text())

    def test_delivery_sums(self):
        rows=(DELIVERY/'SHA256SUMS.txt').read_text().splitlines()
        self.assertEqual(len(rows),6)
        self.assertEqual({line.split('  ',1)[1] for line in rows},{p.name for p in DELIVERY.iterdir() if p.name!='SHA256SUMS.txt'})
        for line in rows:
            expected,name=line.split('  ',1)
            self.assertEqual(sha((DELIVERY/name).read_bytes()),expected,name)

    def test_frozen_application_and_dependencies_unchanged(self):
        with zipfile.ZipFile(BASE/'RackClick-Bundle-M3-14-07.zip') as old, zipfile.ZipFile(DELIVERY/'RackClick-Bundle-M3-14-08.zip') as new:
            self.assertEqual(set(old.namelist()),set(new.namelist()))
            changed=[n for n in old.namelist() if old.read(n)!=new.read(n)]
            self.assertEqual(set(changed),{'bundle.json','operators/New-RackClickRecoveredInstance.ps1'})
            app=[n for n in new.namelist() if n.startswith('application/')]
            self.assertEqual(len(app),45)
            self.assertEqual(sha(new.read('application/manifest.json')),APP)

    def test_bundle_versions_and_recovery_operator(self):
        with zipfile.ZipFile(DELIVERY/'RackClick-Bundle-M3-14-08.zip') as new:
            manifest=json.loads(new.read('bundle.json'))
            self.assertEqual(manifest['versions'],{'schema':14,'dotnetRuntime':'10.0.12','postgresql':'17.11','vcRedist':'14.51.36247.0','vcRuntimeMinimum':'14.44.35211.0'})
            self.assertEqual(len([n for n in new.namelist() if n.startswith('operators/')]),25)
            path='tools/windows/New-RackClickRecoveredInstance.ps1'
            self.assertEqual(sha(new.read('operators/New-RackClickRecoveredInstance.ps1')),self.sources['reviewedOverlays'][path])

    def test_payload_inventory_and_embedded_bundle(self):
        with zipfile.ZipFile(DELIVERY/'RackClick-Servidor-08-payload.zip') as z:
            prefix='RackClick-Instalador/'
            manifest=json.loads(z.read(prefix+'payload.json'))
            names={prefix+row['path'] for row in manifest['files']}|{prefix+'payload.json'}
            self.assertEqual(set(z.namelist()),names)
            self.assertEqual(len(z.namelist()),114)
            for row in manifest['files']:
                raw=z.read(prefix+row['path']);self.assertEqual(len(raw),row['size']);self.assertEqual(sha(raw),row['sha256'],row['path'])
            self.assertEqual(sha(z.read(prefix+'RackClick.zip')),self.build['bundle']['bundleArchiveSha256'])
            self.assertNotEqual(manifest['bundleArchiveSha256'],OLD_BUNDLE)

    def test_only_reviewed_overlays_and_declared_pin_changes(self):
        with zipfile.ZipFile(DELIVERY/'RackClick-Servidor-08-payload.zip') as z:
            for source,expected in self.sources['reviewedOverlays'].items():
                member='RackClick-Instalador/operators/'+source.removeprefix('tools/windows/')
                raw=z.read(member)
                for change in reversed(self.sources['pinChanges']):
                    if change['path']==source:
                        raw=raw.replace(change['after'].encode(),change['before'].encode())
                self.assertEqual(sha(raw),expected,source)
        self.assertEqual(len(self.sources['reviewedOverlays']),7)
        self.assertFalse(self.sources['applicationCompiled'])
        self.assertFalse(self.sources['serverSourceCopied'])
        self.assertFalse(self.sources['c2Included'])

    def test_service_publication_identical(self):
        with zipfile.ZipFile(BASE/'RackClick-Servidor-07-payload.zip') as old, zipfile.ZipFile(DELIVERY/'RackClick-Servidor-08-payload.zip') as new:
            names=[n for n in old.namelist() if n.startswith('RackClick-Instalador/service/')]
            self.assertEqual(len(names),38)
            for name in names:self.assertEqual(new.read(name),old.read(name),name)
            self.assertEqual(sha(new.read('RackClick-Instalador/service/RackClick.WindowsService.dll')),'130e9cc3959d414a0e00759a2e3323a0fc004d76113df56c250f319d38065c61')

    def test_envelope_inventory_and_payload_pin(self):
        with zipfile.ZipFile(DELIVERY/'RackClick-Servidor-08.zip') as z:
            prefix='RackClick-Servidor-08/'
            manifest=json.loads(z.read(prefix+'PAQUETE.json'))
            self.assertEqual(manifest['edition'],'08')
            self.assertEqual(set(z.namelist()),{prefix+v['path'] for v in manifest['files']}|{prefix+'PAQUETE.json'})
            for row in manifest['files']:
                raw=z.read(prefix+row['path']);self.assertEqual(sha(raw),row['sha256']);self.assertEqual(len(raw),row['size'])
            payload=sha(z.read(prefix+'Servidor.zip'))
            self.assertEqual(payload,manifest['payloadSha256'])
            self.assertIn(payload.encode(),z.read(prefix+'INICIAR.ps1'))

    def test_network_pins_and_no_circular_payload_reference(self):
        tools=('Set-RackClickInstanceNetwork.ps1','Set-RackClickServerNetwork.ps1','Start-RackClickHere.ps1')
        with zipfile.ZipFile(DELIVERY/'RackClick-Servidor-08-payload.zip') as payload:
            raw=payload.read('RackClick-Instalador/payload.json');digest=sha(raw)
            self.assertFalse(any(n.endswith('/'+tool) for n in payload.namelist() for tool in tools))
        with zipfile.ZipFile(DELIVERY/'RackClick-Cambiar-IP-08.zip') as network:
            prefix='RackClick-Cambiar-IP-08/'
            self.assertEqual(network.read(prefix+'payload.json'),raw)
            engine=network.read(prefix+'Set-RackClickInstanceNetwork.ps1')
            self.assertIn(digest.encode(),engine)
            self.assertIn(sha(engine).encode(),network.read(prefix+'Start-RackClickHere.ps1'))
            self.assertIn(digest.encode(),network.read(prefix+'Cambiar-IP-RackClick.ps1'))
            for line in network.read(prefix+'SHA256SUMS.txt').decode().splitlines():
                expected,name=line.split('  ',1);self.assertEqual(sha(network.read(prefix+name)),expected,name)

    def test_four_archives_reproducible_in_separate_roots(self):
        repeated=ROOT/'.local/instalador-08-codex-repro/entrega'
        for name in ('RackClick-Bundle-M3-14-08.zip','RackClick-Servidor-08.zip','RackClick-Servidor-08-payload.zip','RackClick-Cambiar-IP-08.zip'):
            self.assertEqual(sha((DELIVERY/name).read_bytes()),sha((repeated/name).read_bytes()),name)
        self.assertFalse(self.build['installed']);self.assertFalse(self.build['adopted']);self.assertEqual(self.build['vmOperations'],0)

    def test_recipe_rejects_parent_traversal_before_any_write(self):
        spec=importlib.util.spec_from_file_location('installer08_recipe',ROOT/'.local/build_installer08_codex.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        for path in (ROOT/'.local/../../OutsideLocal-New08',ROOT/'.local/child/../another',ROOT.parent/'OutsideLocal-New08'):
            with self.assertRaises(ValueError):module.checked(path)
        safe=ROOT/'.local/installer08-unused-path-probe'
        self.assertEqual(module.checked(safe),safe.resolve())
        self.assertFalse(safe.exists())


if __name__=='__main__':
    unittest.main()
