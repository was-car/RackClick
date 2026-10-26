"""Pruebas activas de la candidata interna del instalador 07 (esquema 14, con D14-07).

Comprueban, sin instalar nada, que la cadena de pins es coherente: bundle 14-07 -> payload -> envoltorio y CMD de IP.
Leen la entrega de .local/instalador-06/entrega y las fuentes congeladas de su copia S2. Se omiten si no existen.
"""
import hashlib
import json
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
DELIVERY = ROOT / '.local' / 'instalador-07' / 'entrega'
SOURCES = ROOT / '.local' / 'instalador-07' / 'snapshots' / 'S4' / 'tools' / 'windows'

BUNDLE_SHA = '6d5a3896422c308e6b086822aaaa76a5fb6cc2584cf0664666f96504709e14f8'
PAYLOAD_JSON_SHA = '25a764a9fa40f0e8feb39cfbc9b2b3f1f21bb1137738edd53614b257f6277ec7'
PAYLOAD_ZIP_SHA = '71469d1e084fe1927eadfc2122540868c1db8bf9ac1d22f8819574e4afef8d37'
WRAPPER_SHA = '3ca223230fc5ea1ab1e2ce7e40c9b7ca222ef65e4735412cb3fdb7cfd19ddca1'
IP_CMD_SHA = 'b36fd6d394f090d4fcbc16fa7c278132486a58ed8c774199b5001ea0030703bd'
ENGINE_SHA = '2eb1473b390f9697c698677fe97f877036f3c521ce9bdb8fe10f3e57ed89c551'
RUNTIME_SHA = 'f08466f2a7633074131ad0a261bdb98f83f5a292e5a8a366c04e76cd6cfca2ed'
STALE_PINS = ('a0df90ed', 'ffb4426c', '31a42b3e')  # no pueden quedar en ningun ficheros de la candidata 06 salvo los de servicio
PREFIX = 'RackClick-Servidor-07/'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless((DELIVERY / 'SHA256SUMS.txt').exists(), 'requiere la entrega de la candidata 06 en .local')
class InstallerCandidate06Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload_bytes = (DELIVERY / 'RackClick-Servidor-07-payload.zip').read_bytes()
        cls.payload = zipfile.ZipFile(DELIVERY / 'RackClick-Servidor-07-payload.zip')
        cls.wrapper = zipfile.ZipFile(DELIVERY / 'RackClick-Servidor-07.zip')
        cls.ip = zipfile.ZipFile(DELIVERY / 'RackClick-Cambiar-IP-07.zip')

    def test_delivery_sums_match_the_files(self):
        for line in (DELIVERY / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
            digest, name = line.split(' *', 1)
            with self.subTest(file=name):
                self.assertEqual(sha((DELIVERY / name).read_bytes()), digest)
        self.assertEqual(sha((DELIVERY / 'RackClick-Servidor-07.zip').read_bytes()), WRAPPER_SHA)
        self.assertEqual(sha((DELIVERY / 'RackClick-Cambiar-IP-07.zip').read_bytes()), IP_CMD_SHA)
        self.assertEqual(sha(self.payload_bytes), PAYLOAD_ZIP_SHA)

    def test_wrapper_launcher_pins_the_payload_and_envelope_lists_every_member(self):
        launcher = self.wrapper.read(PREFIX + 'INICIAR.ps1').decode('utf-8-sig')
        self.assertIn(PAYLOAD_ZIP_SHA, launcher)
        envelope = json.loads(self.wrapper.read(PREFIX + 'PAQUETE.json'))
        self.assertEqual((envelope['edition'], envelope['payloadSha256']), ('07', PAYLOAD_ZIP_SHA))
        for item in envelope['files']:
            with self.subTest(file=item['path']):
                data = self.wrapper.read(PREFIX + item['path'])
                self.assertEqual((len(data), sha(data)), (item['size'], item['sha256']))
        self.assertEqual(sorted(item['path'] for item in envelope['files']),
                         sorted(n.removeprefix(PREFIX) for n in self.wrapper.namelist() if n != PREFIX + 'PAQUETE.json'))

    def test_payload_manifest_pins_bundle_14_07_and_lists_every_file(self):
        manifest_bytes = self.payload.read('RackClick-Instalador/payload.json')
        self.assertEqual(sha(manifest_bytes), PAYLOAD_JSON_SHA)
        manifest = json.loads(manifest_bytes)
        self.assertEqual((manifest['kind'], manifest['bundleArchiveSha256']), ('RackClickServerSetup', BUNDLE_SHA))
        self.assertEqual(sha(self.payload.read('RackClick-Instalador/RackClick.zip')), BUNDLE_SHA)
        for item in manifest['files']:
            with self.subTest(file=item['path']):
                data = self.payload.read('RackClick-Instalador/' + item['path'])
                self.assertEqual((len(data), sha(data)), (item['size'], item['sha256']))

    def test_payload_has_no_stale_bundle_or_network_pins_outside_the_service_host(self):
        for name in self.payload.namelist():
            if not name.endswith(('.ps1', '.cmd', '.json', '.txt', '.html')) or name.startswith('RackClick-Instalador/service/'):
                continue
            text = self.payload.read(name).decode('utf-8', errors='replace')
            for stale in STALE_PINS:
                with self.subTest(file=name, stale=stale):
                    self.assertNotIn(stale, text)
        status = self.payload.read('RackClick-Instalador/00-ESTADO.txt').decode('ascii')
        self.assertIn('EDICION 07', status)

    def test_payload_operators_are_the_frozen_sources_and_install_has_no_schema14_guard(self):
        operators = [n for n in self.payload.namelist() if n.startswith('RackClick-Instalador/operators/') and n.count('/') == 2]
        self.assertEqual(len(operators), 25)
        for name in operators:
            local = name.removeprefix('RackClick-Instalador/operators/')
            with self.subTest(operator=local):
                self.assertEqual(self.payload.read(name), (SOURCES / local).read_bytes())
        install = self.payload.read('RackClick-Instalador/operators/Install-RackClickOfflineBundle.ps1')
        self.assertNotIn(b'schema14_install_not_propagated', install)

    def test_ip_change_cmd_pins_the_06_payload_and_engine(self):
        listed = dict(line.split('  ', 1)[::-1] for line in self.ip.read('RackClick-Cambiar-IP-07/SHA256SUMS.txt').decode('ascii').splitlines())
        for name, digest in listed.items():
            with self.subTest(file=name):
                self.assertEqual(sha(self.ip.read('RackClick-Cambiar-IP-07/' + name)), digest)
        self.assertEqual(sha(self.ip.read('RackClick-Cambiar-IP-07/payload.json')), PAYLOAD_JSON_SHA)
        engine = self.ip.read('RackClick-Cambiar-IP-07/Set-RackClickInstanceNetwork.ps1')
        self.assertEqual(sha(engine), ENGINE_SHA)
        self.assertIn(PAYLOAD_JSON_SHA.encode('ascii'), engine)
        for name in self.ip.namelist():
            self.assertNotIn(b'ffb4426c', self.ip.read(name))

    def test_runtime_stop_publication_is_the_atomic_one_shipped_in_payload(self):
        # D14-07: el runtime del payload debe ser la publicacion atomica de stop-request, no la escritura exclusiva original.
        runtime = self.payload.read('RackClick-Instalador/operators/server-install/Invoke-RackClickServerRuntime.ps1')
        self.assertEqual(sha(runtime), RUNTIME_SHA)
        self.assertIn(b'[IO.File]::Move($temporaryRequest,$request)', runtime)
        self.assertNotIn(b'else {Write-BackupNewText $request $value}', runtime)


if __name__ == '__main__':
    unittest.main()
