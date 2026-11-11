"""Build the fixed metadata-only Demo50 edition03 for a NEW schema48 server.

No database, credential, receipt, VM, account or service is opened. Historical
inventory43 and command replay are pinned inputs, not silently regenerated.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / 'DEMO-50-CLIENTES-01'
BASE_REPLAY = ROOT / 'development/examples/demo50-replay43.json'
BASE_SUMS_SHA = 'b2630b6c1de4206144c943467edd3cda358b756658cf7a917d1c139d74efa030'
BASE_REPLAY_SHA = 'a3b44a37d8ca81f2f13d515d26905a520af8f09ffb2cfe498f97d06367bf423a'
PREFIX = 'RackClick-Demo50-Trilingual-03/'
COUNTS = dict(sites=66, buildings=88, rooms=226, racks=180, devices=1563,
              portGroups=2869, ports=20665, connections=2207)
COLLECTIONS = set(COUNTS)
# Fixed companies, not translations attached to the active interface locale.
# The visible synthetic labels avoid presenting them as real organizations.
COMPANIES = (
    ('en', 'Oakbridge Office Supplies'), ('de', 'Lindenwerk Büroservice'), ('es', 'Papelería Encinar'),
    ('en', 'Harborlight Coffee Roasters'), ('de', 'Bäckerei Morgenhain'), ('es', 'Clínica Horizonte Azul'),
    ('en', 'Northfield Design Studio'), ('de', 'Buchhandlung Sternwinkel'), ('es', 'Asesoría Puerta Clara'),
    ('en', 'Meadowbrook Travel Services'), ('de', 'Alpenbogen Logistik'), ('es', 'Distribuciones Río Verde'),
    ('en', 'Silvermaple Engineering'), ('de', 'Hafenquell Handel'), ('es', 'Servicios Costa Serena'),
    ('en', 'Cedarstone Health Partners'), ('de', 'Planungsbüro Fichtenau'), ('es', 'Editorial Sendero Abierto'),
    ('en', 'Bluehaven Regional Services'), ('de', 'Werkstatt Sonnenfeld'), ('es', 'Grupo Tiendas Alameda'),
    ('en', 'Rivergate Retail Network'), ('de', 'Nordhain Filialservice'), ('es', 'Transporte Vía del Mar'),
    ('en', 'Westbrook Branch Services'), ('de', 'Bergwinkel Mobilität'), ('es', 'Servicios Bahía Serena'),
    ('en', 'Pinecrest Campus Network'), ('de', 'Lernzentrum Lindenblick'), ('es', 'Colegio Jardín del Río'),
    ('en', 'Willowbank Learning Trust'), ('de', 'Berufsschule Eichenstern'), ('es', 'Instituto Nuevo Pórtico'),
    ('en', 'Clearwater Training Centre'), ('de', 'Tannenhain Fertigung'), ('es', 'Automatización Prado Claro'),
    ('en', 'Copperwood Manufacturing'), ('de', 'Feldbogen Agrartechnik'), ('es', 'Manufactura Cobre Azul'),
    ('en', 'Deltaforge Industrial Systems'), ('de', 'Rechenzentrum Abendstern'), ('es', 'Datos Aurora Serena'),
    ('en', 'Brightquay Data Services'), ('de', 'Wolkenhain Infrastruktur'), ('es', 'Archivo Digital Faro Norte'),
    ('en', 'Orbitvale Infrastructure'), ('de', 'Netzwerkstatt Mosaikhof'), ('es', 'Laboratorio Prisma Claro'),
    ('en', 'Stonebridge Research Works'), ('de', 'Prismenwald Systemtechnik'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result


def parse(data):
    return json.loads(data.decode('utf-8'), object_pairs_hook=unique_object)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def encode_replay(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')) + '\n').encode('ascii')


def safe_path(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError('reparse_rejected')
    return path


def name_map():
    suffix = dict(en='Synthetic', de='Fiktiv', es='Sintética')
    return {f'c{i:02}': dict(name=f'{i:02} · {company} · {suffix[language]}', language=language)
            for i, (language, company) in enumerate(COMPANIES, 1)}


def sums(files):
    return ''.join(sha(data) + '  ' + name + '\n' for name, data in sorted(files.items())).encode('ascii')


def validate_base(files, replay):
    if 'SHA256SUMS.txt' not in files or sha(files['SHA256SUMS.txt']) != BASE_SUMS_SHA:
        raise ValueError('base_sums_untrusted')
    pinned = {}
    for line in files['SHA256SUMS.txt'].decode('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_.-]+)', line)
        if not match or match[2] in pinned:
            raise ValueError('base_sums_invalid')
        pinned[match[2]] = match[1]
    if set(files) != set(pinned) | {'SHA256SUMS.txt'}:
        raise ValueError('base_members_invalid')
    for name, digest in pinned.items():
        if sha(files[name]) != digest:
            raise ValueError('base_file_digest_invalid')
    # The canonical encoder of the source replay is its historical encoder.
    historical = encode_replay(replay)
    if sha(historical) != BASE_REPLAY_SHA:
        raise ValueError('base_replay_untrusted')
    if replay['counts'] != COUNTS or replay['schemaVersion'] != 43 or replay['securityIncluded'] is not False:
        raise ValueError('base_replay_scope_invalid')
    manifest = parse(files['manifest.json'])
    for i, (meta, customer) in enumerate(zip(manifest['customers'], replay['customers'], strict=True), 1):
        if meta['key'] != f'c{i:02}' or customer['key'] != meta['key'] or customer['name'] != meta['name'] or customer['sourceCustomerId'] != meta['customerId']:
            raise ValueError('base_customer_binding_invalid')


def read_base(base_dir=BASE_DIR, base_replay=BASE_REPLAY):
    directory = safe_path(base_dir)
    files = {}
    for file in directory.iterdir():
        safe_path(file)
        if not file.is_file():
            raise ValueError('base_member_not_file')
        files[file.name] = file.read_bytes()
    raw = safe_path(base_replay).read_bytes()
    if sha(raw) != BASE_REPLAY_SHA:
        raise ValueError('base_replay_untrusted')
    replay = parse(raw)
    validate_base(files, replay)
    return files, replay


def validate_names(names):
    if not isinstance(names, dict) or list(names) != [f'c{i:02}' for i in range(1, 51)]:
        raise ValueError('names_fifty_ordered_required')
    for value in names.values():
        if set(value) != {'name', 'language'} or value['language'] not in ('en', 'de', 'es') or not isinstance(value['name'], str) or not 1 <= len(value['name']) <= 160 or any(ord(c) < 32 for c in value['name']):
            raise ValueError('name_scope_invalid')
    if len({x['name'] for x in names.values()}) != 50:
        raise ValueError('name_not_unique')
    if {lang: sum(x['language'] == lang for x in names.values()) for lang in ('en', 'de', 'es')} != dict(en=17, de=17, es=16):
        raise ValueError('language_distribution_invalid')


def transform(base, source_replay, names=None):
    validate_base(base, source_replay)
    names = name_map() if names is None else names
    validate_names(names)
    files = dict(base)
    for name in ('manifest.json', 'plan.json'):
        value = parse(base[name])
        for customer in value['customers']:
            customer.update(names[customer['key']])
        files[name] = encode(value)
    replay = copy.deepcopy(source_replay)
    for customer in replay['customers']:
        customer['name'] = names[customer['key']]['name']
    # Regenerate only the name-bearing viewer. Its React-independent DOM uses
    # textContent, and its embedded JSON is escaped by the historical generator.
    from package_demo50 import viewer
    manifest = parse(files['manifest.json'])
    summary = []
    for customer in manifest['customers']:
        inventory = parse(files[customer['file']])['inventory']
        summary.append(customer | {'counts': {key: len(inventory[key]) for key in sorted(COLLECTIONS)}})
    files['VER-50-CLIENTES.html'] = viewer(summary)
    files['00-LEEME.md'] = ("# RackClick · Demo50 trilingüe 03\n\n"
        "50 empresas enteramente ficticias: 17 nombres en inglés, 17 en alemán y 16 en español. "
        "Son nombres propios fijos; cambiar el idioma de RackClick no los traduce.\n\n"
        "Esta edición conserva los 50 inventarios, UUID de fuente, matriz y CSV de cobertura de la edición01 byte a byte. "
        "Cambia sólo nombre/idioma en los metadatos, y name en el replay. Las ubicaciones y etiquetas interiores se conservan. "
        "868 revisiones de perfil/506 modelos originales; el catálogo instalado48 tiene884 revisiones/877 modelos, "
        "por lo que los16 perfiles posteriores no quedan colocados por esta demo.\n\n"
        "Abre VER-50-CLIENTES.html para explorar sin conexión. No se conecta al servidor. "
        "Los JSON son inventario43 sin usuarios, factores MFA, sesiones ni contraseñas. "
        "Para cargarlos usa el cargador03 de la carpeta hermana sobre una instalación48 NUEVA y VACÍA. "
        "No es un backup PostgreSQL; no contiene seguridad ni cambia cuentas o MFA.\n").encode('utf-8')
    files['SHA256SUMS.txt'] = sums({k: v for k, v in files.items() if k != 'SHA256SUMS.txt'})
    return files, replay


def expected_members():
    base, replay = read_base()
    data, replay = transform(base, replay)
    replay_bytes = encode_replay(replay)
    pin = sha(replay_bytes)
    loader_dir = safe_path(ROOT / 'tools/windows/demo50-v3')
    expected_loader = {'Import-RackClickDemo50.ps1', 'CARGAR-50-CLIENTES.cmd', 'LEEME-DEMO50.txt'}
    if {p.name for p in loader_dir.iterdir()} != expected_loader:
        raise ValueError('loader_members_invalid')
    loader = {p.name: safe_path(p).read_bytes() for p in loader_dir.iterdir()}
    if pin.encode() not in loader['Import-RackClickDemo50.ps1'] or pin.encode() not in loader['CARGAR-50-CLIENTES.cmd']:
        raise ValueError('loader_replay_pin_mismatch')
    if not loader['Import-RackClickDemo50.ps1'].isascii() or not loader['CARGAR-50-CLIENTES.cmd'].isascii():
        raise ValueError('loader_encoding_invalid')
    loader['demo50-replay.json'] = replay_bytes
    loader['SHA256SUMS.txt'] = sums(loader)
    members = {'DATOS-DEMO50/' + k: v for k, v in data.items()}
    members.update({'CARGAR-50-CLIENTES/' + k: v for k, v in loader.items()})
    members['00-LEEME.md'] = ("# RackClick · Demo50 trilingüe 03\n\n"
        "1. Instala la candidata48 nueva y verifica HTTPS y el arranque.\n"
        "2. Opcionalmente abre DATOS-DEMO50/VER-50-CLIENTES.html para ver las50 empresas.\n"
        "3. Desde la VM abre CARGAR-50-CLIENTES/CARGAR-50-CLIENTES.cmd; indica la URL HTTPS, "
        "el administrador global y su contraseña privada. Si tiene MFA, introduce el TOTP en la consola, nunca por chat.\n"
        "4. Confirma CARGAR 50 CLIENTES SINTETICOS sólo sobre un servidor vacío. "
        "El resultado esperado es demo50_loaded_verified con50 clientes y2553 comandos.\n"
        "5. Si se detiene, conserva la salida y los datos parciales. No repitas ni borres por tu cuenta.\n\n"
        "No importa usuarios ni MFA; mantiene la política, TLS, CSRF, permisos y rechazo de instalaciones ocupadas. "
        "La carga usa IDs nuevos devueltos por la API, verifica las ocho colecciones y no reintenta. "
        "Los nombres son fijos EN/DE/ES, no traducciones automáticas.\n").encode('utf-8')
    members['SHA256SUMS.txt'] = sums(members)
    return members, pin


def write_zip(path, files):
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            item = zipfile.ZipInfo(PREFIX + name, date_time=(2026, 11, 11, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            archive.writestr(item, data)


def verify(path, expected_sha=None):
    path = safe_path(path)
    if expected_sha is not None and sha(path.read_bytes()) != expected_sha:
        raise ValueError('zip_digest_mismatch')
    expected, pin = expected_members()
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != {PREFIX + n for n in expected}:
            raise ValueError('package_members_invalid')
        for name, data in expected.items():
            info = archive.getinfo(PREFIX + name)
            if info.file_size != len(data) or info.flag_bits & 1:
                raise ValueError('package_member_size_or_encryption_invalid')
        if archive.testzip() is not None:
            raise ValueError('package_crc_invalid')
        for name, data in expected.items():
            if archive.read(PREFIX + name) != data:
                raise ValueError('package_content_invalid')
    return dict(result='PASS', files=len(expected), customers=50, sourceSchema=43,
                targetSchema=48, replaySha256=pin, securityIncluded=False)


def build(output):
    output = safe_path(output)
    if output.exists():
        raise ValueError('output_exists')
    if not output.parent.is_dir():
        raise ValueError('output_parent_missing')
    members, pin = expected_members()
    output.mkdir()
    directory = output / PREFIX.rstrip('/')
    for name, data in members.items():
        destination = directory / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(data)
    archive = output / 'RackClick-Demo50-Trilingual-03.zip'
    write_zip(archive, members)
    result = verify(archive)
    result.update(zipPath=str(archive), zipSha256=sha(archive.read_bytes()),
                  zipBytes=archive.stat().st_size, replaySha256=pin,
                  directory=str(directory), inventoriesPreserved=50,
                  languageCounts=dict(en=17, de=17, es=16), commands=2553, counts=COUNTS)
    with (output / 'RESULTADO.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    create = sub.add_parser('build')
    create.add_argument('--output', required=True, type=Path)
    check = sub.add_parser('verify')
    check.add_argument('--zip', required=True, type=Path)
    check.add_argument('--sha256')
    args = parser.parse_args(argv)
    result = build(args.output) if args.mode == 'build' else verify(args.zip, args.sha256)
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
