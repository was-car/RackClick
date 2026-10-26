"""Genera una distribución de servidor y frontend de esquema 14 desde un perfil cerrado.

Entradas explícitas: perfil (docs/DISTRIBUCION14-PERFIL.json), publicación del servidor sin apphost y frontend
construido. Salida: carpeta nueva con server/, frontend/, manifest.json, inventory.json y SHA256SUMS.txt.
No sobrescribe nada, no usa pruebas ni generadores históricos y no adopta ni instala el producto.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / 'docs' / 'DISTRIBUCION14-PERFIL.json'
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
SHA_LINE = re.compile(r'^[a-f0-9]{64}$')


class DistributionError(Exception):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def reject_reparse(path: Path) -> None:
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & FILE_ATTRIBUTE_REPARSE_POINT:
        raise DistributionError('reparse_path_rejected')


def reject_chain(path: Path) -> Path:
    """Rechaza enlaces y junctions en la propia ruta o en cualquier ancestro existente, sin resolverla antes."""
    absolute = Path(os.path.abspath(path))
    for item in (*reversed(absolute.parents), absolute):
        if os.path.lexists(item):
            reject_reparse(item)
    return absolute


def inventory(root: Path) -> dict:
    """Archivos relativos con '/' y ruta absoluta. Rechaza puntos de reanálisis y colisiones."""
    reject_reparse(root)
    result = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames + filenames:
            reject_reparse(Path(dirpath) / name)
        for name in filenames:
            full = Path(dirpath) / name
            rel = full.relative_to(root).as_posix()
            if rel.lower() in {key.lower() for key in result}:
                raise DistributionError('file_name_collision')
            result[rel] = full
    return result


def load_profile() -> dict:
    profile = json.loads(PROFILE_PATH.read_text(encoding='utf-8'))
    if profile.get('formatVersion') != 1 or profile.get('kind') != 'RackClickDistributionProfileDefinition':
        raise DistributionError('profile_invalid')
    if profile.get('applicationSchema') != 14 or profile.get('state') != 'definition_only_not_a_release':
        raise DistributionError('profile_invalid')
    app = profile['serverApplicationFiles']
    sql = profile['serverSqlFiles']
    front = profile['frontendFiles']
    if len(app) != 10 or len(sql) != 14 or profile['serverFileCount'] != len(app) + len(sql):
        raise DistributionError('profile_counts_invalid')
    if len(front) != 18 or profile['frontendFileCount'] != 18:
        raise DistributionError('profile_counts_invalid')
    if len(set(app + sql)) != len(app + sql) or len(set(front)) != len(front):
        raise DistributionError('profile_duplicate')
    if any(not name.startswith('database/') or not re.fullmatch(r'database/\d{3}-[a-z0-9-]+\.sql', name) for name in sql):
        raise DistributionError('profile_sql_invalid')
    if any(name.startswith('database/') for name in app):
        raise DistributionError('profile_app_invalid')
    return profile


def exact_match(found: dict, wanted: list, label: str) -> None:
    missing = sorted(set(wanted) - set(found))
    extra = sorted(set(found) - set(wanted))
    if missing:
        raise DistributionError(f'{label}_missing')
    if extra:
        raise DistributionError(f'{label}_extra')


def build(profile_path: Path, publish: Path, frontend: Path, output: Path, base_commit: str, toolchain: dict, source_status: str) -> dict:
    # Se comprueba la ruta tal como llega: resolverla antes ocultaría una junction en la entrada o en el destino.
    profile_path, publish, frontend, output = (reject_chain(profile_path), reject_chain(publish),
                                               reject_chain(frontend), reject_chain(output))
    if profile_path != PROFILE_PATH:
        raise DistributionError('profile_path_unexpected')
    if not re.fullmatch(r'[a-f0-9]{40}', base_commit):
        raise DistributionError('base_commit_invalid')
    profile = load_profile()
    if output.exists():
        raise DistributionError('output_exists')
    if not publish.is_dir() or not frontend.is_dir():
        raise DistributionError('input_missing')

    published = inventory(publish)
    app_found = {k: v for k, v in published.items() if not k.startswith('database/')}
    sql_found = {k: v for k, v in published.items() if k.startswith('database/')}
    exact_match(app_found, profile['serverApplicationFiles'], 'server_application')
    exact_match(sql_found, profile['serverSqlFiles'], 'server_sql')
    front_found = inventory(frontend)
    exact_match(front_found, profile['frontendFiles'], 'frontend')

    server_entries = {rel: published[rel] for rel in profile['serverApplicationFiles'] + profile['serverSqlFiles']}
    front_entries = {rel: front_found[rel] for rel in profile['frontendFiles']}

    output.mkdir(parents=True, exist_ok=False)
    distributions = {'server': {}, 'frontend': {}}
    total_bytes = 0
    for kind, entries in (('server', server_entries), ('frontend', front_entries)):
        for rel in sorted(entries):
            destination = output / kind / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(entries[rel], destination)
            digest = sha256_file(destination)
            if not SHA_LINE.match(digest):
                raise DistributionError('digest_invalid')
            distributions[kind][rel] = digest
            total_bytes += destination.stat().st_size

    file_count = len(server_entries) + len(front_entries)
    manifest = {
        'schema': 14,
        'profileId': profile['profileId'],
        'kind': 'RackClickDistributionManifest',
        'baseCommit': base_commit,
        'toolchain': toolchain,
        'distributions': {key: dict(sorted(value.items())) for key, value in sorted(distributions.items())},
        'fileCount': file_count,
        'totalBytes': total_bytes,
        'scope': 'Artifact integrity only; not installation, authenticity or application acceptance',
        'releaseStatus': 'draft_unapproved',
        'sourceStatus': source_status,
    }
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8')
    (output / 'manifest.json').write_bytes(manifest_bytes)

    inventory_doc = {
        'profileId': profile['profileId'],
        'hosting': profile['hosting'],
        'excludedFromServerList': ['RackClick.Server.exe (apphost; el servicio usa dotnet con la DLL)'],
        'dependencies': [
            {'name': 'Otp.NET', 'version': '1.4.1', 'license': 'MIT', 'source': 'https://github.com/kspearrin/Otp.NET',
             'noticeLocation': 'bundle licenses area'},
            {'name': 'Npgsql', 'version': '10.0.3', 'license': 'ver LICENSES/Npgsql-LICENSE del paquete', 'source': 'nuget'},
        ],
    }
    (output / 'inventory.json').write_bytes((json.dumps(inventory_doc, indent=2, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8'))

    sums = []
    for kind in ('server', 'frontend'):
        for rel in sorted(distributions[kind]):
            sums.append(f'{distributions[kind][rel]}  {kind}/{rel}')
    sums.append(f'{hashlib.sha256(manifest_bytes).hexdigest()}  manifest.json')
    (output / 'SHA256SUMS.txt').write_bytes(('\n'.join(sums) + '\n').encode('utf-8'))
    return {'output': str(output), 'manifestSha256': hashlib.sha256(manifest_bytes).hexdigest(),
            'fileCount': file_count, 'totalBytes': total_bytes, 'serverFiles': len(server_entries),
            'frontendFiles': len(front_entries), 'profileId': profile['profileId']}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, type=Path)
    parser.add_argument('--publish', required=True, type=Path)
    parser.add_argument('--frontend', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--base-commit', required=True)
    parser.add_argument('--dotnet', default='10.0.401')
    parser.add_argument('--node', default='24.21.0')
    parser.add_argument('--npm', default='11.19.0')
    parser.add_argument('--source-status', required=True)
    args = parser.parse_args(argv)
    try:
        result = build(args.profile, args.publish, args.frontend, args.output, args.base_commit,
                       {'dotnet': args.dotnet, 'node': args.node, 'npm': args.npm}, args.source_status)
    except DistributionError as error:
        print(json.dumps({'valid': False, 'code': str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({'valid': True, 'code': 'distribution_built', **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
