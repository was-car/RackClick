"""Pruebas activas de la candidata interna del instalador 06 (esquema 14).

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
DELIVERY = ROOT / '.local' / 'instalador-06' / 'entrega'
SOURCES = ROOT / '.local' / 'instalador-06' / 'snapshots' / 'S2' / 'tools' / 'windows'

BUNDLE_SHA = '6d5a3896422c308e6b086822aaaa76a5fb6cc2584cf0664666f96504709e14f8'
PAYLOAD_JSON_SHA = '31a42b3e9c7abfd757dc51ffb5e85abaa3d5b76600e4b66e72092447727417c9'
PAYLOAD_ZIP_SHA = '6994870ed2734d3659ec733162618c9b5bd187366d2022260b4b4855e13d6b3d'
WRAPPER_SHA = 'd6b67ae2e7b2179393d46dbc6015f6f991203fbf18d088e653fc36c30bfd2681'
IP_CMD_SHA = 'b1a95d414a503575afae7863e7007116ba5a224253987d41059a96828658c4ae'
ENGINE_SHA = 'a05b61e4e58b45ae644d73c559088ee39a83f34fc170db34e3a3b2b1bce2b94c'
STALE_PINS = ('a0df90ed', 'ffb4426c', '130e9cc3ab')  # no pueden quedar en ningun ficheros de la candidata 06 salvo los de servicio
PREFIX = 'RackClick-Servidor-06/'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless((DELIVERY / 'SHA256SUMS.txt').exists(), 'requiere la entrega de la candidata 06 en .local')
class InstallerCandidate06Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload_bytes = (DELIVERY / 'RackClick-Servidor-06-payload.zip').read_bytes()
        cls.payload = zipfile.ZipFile(DELIVERY / 'RackClick-Servidor-06-payload.zip')
        cls.wrapper = zipfile.ZipFile(DELIVERY / 'RackClick-Servidor-06.zip')
        cls.ip = zipfile.ZipFile(DELIVERY / 'RackClick-Cambiar-IP-06.zip')

    def test_delivery_sums_match_the_files(self):
        for line in (DELIVERY / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
            digest, name = line.split(' *', 1)
            with self.subTest(file=name):
                self.assertEqual(sha((DELIVERY / name).read_bytes()), digest)
        self.assertEqual(sha((DELIVERY / 'RackClick-Servidor-06.zip').read_bytes()), WRAPPER_SHA)
        self.assertEqual(sha((DELIVERY / 'RackClick-Cambiar-IP-06.zip').read_bytes()), IP_CMD_SHA)
        self.assertEqual(sha(self.payload_bytes), PAYLOAD_ZIP_SHA)

    def test_wrapper_launcher_pins_the_payload_and_envelope_lists_every_member(self):
        launcher = self.wrapper.read(PREFIX + 'INICIAR.ps1').decode('utf-8-sig')
        self.assertIn(PAYLOAD_ZIP_SHA, launcher)
        envelope = json.loads(self.wrapper.read(PREFIX + 'PAQUETE.json'))
        self.assertEqual((envelope['edition'], envelope['payloadSha256']), ('06', PAYLOAD_ZIP_SHA))
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
        self.assertIn('EDICION 06', status)

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
        listed = dict(line.split('  ', 1)[::-1] for line in self.ip.read('RackClick-Cambiar-IP-06/SHA256SUMS.txt').decode('ascii').splitlines())
        for name, digest in listed.items():
            with self.subTest(file=name):
                self.assertEqual(sha(self.ip.read('RackClick-Cambiar-IP-06/' + name)), digest)
        self.assertEqual(sha(self.ip.read('RackClick-Cambiar-IP-06/payload.json')), PAYLOAD_JSON_SHA)
        engine = self.ip.read('RackClick-Cambiar-IP-06/Set-RackClickInstanceNetwork.ps1')
        self.assertEqual(sha(engine), ENGINE_SHA)
        self.assertIn(PAYLOAD_JSON_SHA.encode('ascii'), engine)
        for name in self.ip.namelist():
            self.assertNotIn(b'ffb4426c', self.ip.read(name))


if __name__ == '__main__':
    unittest.main()
