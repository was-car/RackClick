"""Build the one-command IP change package for the frozen 05 installation; never installs or publishes."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

from package_server_installer import EDITION_PATTERN, LOCAL, ROOT, STAMP, checked_path, digest

ENGINE = ROOT / 'tools/windows/server-install/Set-RackClickInstanceNetwork.ps1'
LAUNCHER = ROOT / 'tools/windows/server-install/Start-RackClickHere.ps1'
ORCHESTRATOR = ROOT / 'tools/windows/network-change/Cambiar-IP-RackClick.ps1'
CMD = ROOT / 'tools/windows/network-change/CAMBIAR-IP-RACKCLICK.cmd'
NETWORK_TOOLS = ('Set-RackClickInstanceNetwork.ps1', 'Set-RackClickServerNetwork.ps1', 'Start-RackClickHere.ps1')
LEEME = (
    'RackClick - cambiar la IP de la instalacion (edicion 06)\r\n'
    '1. Copia esta carpeta al servidor y ejecuta CAMBIAR-IP-RACKCLICK.cmd como administrador.\r\n'
    '2. Escribe SI cuando lo pida. El CMD detecta la IP actual de la VM y la red /24 que contiene.\r\n'
    '3. No cambia la IP de Windows, las cuentas, las credenciales de PostgreSQL ni los datos.\r\n'
    '4. Guarda copias en C:\\RackClick-Respaldo-Script\\cambio-ip-<fecha>.\r\n'
    '5. Importa en tu PC el certificado RackClick-CA-*.cer que deja en el Escritorio.\r\n'
).encode('ascii')


HEX64_PATTERN = re.compile(r'[0-9a-f]{64}')


def build(payload_zip, output, *, edition, payload_json_sha256):
    if not isinstance(edition, str) or EDITION_PATTERN.fullmatch(edition) is None:
        raise ValueError('edition_invalid')
    if not isinstance(payload_json_sha256, str) or HEX64_PATTERN.fullmatch(payload_json_sha256) is None:
        raise ValueError('payload_sha256_invalid')
    prefix = 'RackClick-Cambiar-IP-' + edition + '/'
    output = checked_path(output, LOCAL)
    if output.exists() or output.suffix.lower() != '.zip' or not output.parent.is_dir():
        raise ValueError('new_zip_with_existing_parent_required')
    source = zipfile.ZipFile(checked_path(payload_zip, LOCAL))
    payload_json = source.read('RackClick-Instalador/payload.json')
    if digest(payload_json) != payload_json_sha256:
        raise ValueError('payload_hash_mismatch')
    manifest = json.loads(payload_json.decode('ascii'))
    paths = [item['path'] for item in manifest['files']]
    if any(path.endswith('/' + tool) for path in paths for tool in NETWORK_TOOLS):
        raise ValueError('network_tool_in_frozen_payload')
    engine = checked_path(ENGINE).read_bytes()
    if ("'" + payload_json_sha256 + "'").encode('ascii') not in engine:
        raise ValueError('engine_pin_mismatch')
    engine_sha = digest(engine)
    launcher = checked_path(LAUNCHER).read_bytes().replace(b'@@ENGINE_SHA256@@', engine_sha.encode('ascii'))
    orchestrator = checked_path(ORCHESTRATOR).read_text(encoding='ascii').replace('@@ENGINE_SHA256@@', engine_sha)
    if '@@' in orchestrator:
        raise ValueError('orchestrator_token_left')
    entries = {
        'CAMBIAR-IP-RACKCLICK.cmd': checked_path(CMD).read_bytes(),
        'Cambiar-IP-RackClick.ps1': orchestrator.encode('ascii'),
        'Start-RackClickHere.ps1': launcher,
        'Set-RackClickInstanceNetwork.ps1': engine,
        'payload.json': payload_json,
        'LEEME.txt': LEEME.replace(b'edicion 06', ('edicion ' + edition).encode('ascii')),
    }
    for path in paths:
        if path.startswith('operators/'):
            entries['payload/' + path] = source.read('RackClick-Instalador/' + path)
    sums = ''.join(f'{digest(data)}  {name}\n' for name, data in sorted(entries.items()))
    entries['SHA256SUMS.txt'] = sums.encode('ascii')
    with output.open('xb') as target:
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as package:
            for name in sorted(entries):
                info = zipfile.ZipInfo(prefix + name, STAMP)
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                package.writestr(info, entries[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    return dict(archive=str(output), sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                size=output.stat().st_size, files=len(entries), engineSha256=engine_sha,
                payloadSha256=payload_json_sha256, edition=edition, installed=False, published=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload-zip', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--edition', required=True)
    parser.add_argument('--payload-json-sha256', required=True)
    arguments = parser.parse_args()
    print(json.dumps(build(arguments.payload_zip, arguments.output, edition=arguments.edition,
                           payload_json_sha256=arguments.payload_json_sha256), indent=2))
