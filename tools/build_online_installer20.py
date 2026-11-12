"""Edition20 own-only transport from explicit reviewed artifacts and current operators.

No historical ZIP, builds, installation, credentials or provider downloads are inputs.
Only the closed application and transport pins below identify this reviewed build.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import re
import sys
import zipfile

import package_offline_bundle as bundle

ROOT = Path(__file__).resolve().parents[1]
APP_SHA = 'f7b971f31dd5f424dbce35c9c18a4c6c75c8968f31d10c5df8bbfe215e5b8a53'
APP_INVENTORY_SHA = 'f20f311fcba7ffe6d37cdc4980efa26aeebaa50d6a0e42443ab365bafcd7efff'
APP_SUMS_SHA = 'd3d7b25a4543b976884a7294d11daaa21b7640c7db2b5a87e2d4dd873a6bac9b'
APP_BYTES = 35919405
BUNDLE_SHA = 'c69a82210a4f221058c088d01e5b70a13c4ec1855386692c44774cc6ee28efea'
RECIPE_SHA = '7b47bf9d6bda91bbbfb6ec1aa177a2c8f2cae14b0db86374fb4008d0c1ea226e'
CORE20_SHA = 'b514876ed664a6a3ae7b733993e2522a70dc752651865cb7564c0a04cc5f1577'
NATIVE20_SHA = '532e966250a0a54e07aac8f3b2812813c7782c9e5872d6f0630b7eae66f53043'
DEMO_SHA = 'd7ab9469d4929af703285b0cc7eddcf13e9f245f43828cfcaee95c0e2d2e9215'
SERVICE_DLL_SHA = '130e9cc3959d414a0e00759a2e3323a0fc004d76113df56c250f319d38065c61'
SERVICE_TREE_SHA = '7f94e7d25966e8ddb3a534ab66d7be73e2ee59d513a84bc04aa6f66e16f09b63'
STAMP = (2026, 11, 12, 0, 0, 0)
STATIC_SOURCES = (
    'tools/package_offline_bundle.py', 'tools/package_server_installer.py',
    'tools/package_clean_server_installer.py',
    'tools/windows/server-reset/Start-RackClickCleanInstall.ps1',
    'development/toolchain.lock.json', 'development/offline-bundle14.sources.json',
    'development/windows-service/packages.lock.json', 'docs/INSTALADOR20-SQL-PROTEGIDO.html',
    'licenses/service-host-MIT.txt', 'licenses/service-host-THIRD-PARTY-NOTICES.txt',
)


def require(ok, code):
    if not ok:
        raise ValueError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode('ascii')


def require_pin(value):
    require(isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value), 'release_inputs_not_frozen')


def read_tree(root):
    root = bundle.clean_path(Path(root), directory=True)
    files = {}
    pending = [root]
    while pending:
        current = pending.pop()
        for path in current.iterdir():
            # Check the unmodified path before dereferencing a junction or symbolic link.
            bundle.clean_path(path, directory=path.is_dir())
            if path.is_dir():
                pending.append(path)
            else:
                name = path.relative_to(root).as_posix()
                files[name] = bundle.read_file(path)
    bundle.validate_names(list(files))
    return files


def tree_digest(files):
    return sha(json_bytes([dict(path=n, bytes=len(v), sha256=sha(v)) for n, v in sorted(files.items())]))


def members(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        inventory = bundle.archive_inventory(archive)
        require(len(inventory) == len(archive.infolist()), 'archive_directory_rejected')
        return {n: archive.read(info) for n, info in inventory.items()}


def verify_application(application):
    for pin in (APP_SHA, APP_INVENTORY_SHA, APP_SUMS_SHA):
        require_pin(pin)
    require(type(APP_BYTES) is int and APP_BYTES > 0, 'release_inputs_not_frozen')
    files = read_tree(application)
    for name, pin in (('manifest.json', APP_SHA), ('inventory.json', APP_INVENTORY_SHA), ('SHA256SUMS.txt', APP_SUMS_SHA)):
        require(name in files and sha(files[name]) == pin, 'application_metadata_pin_invalid')
    manifest = bundle.strict_json(files['manifest.json'])
    require(manifest.get('schema') == 48 and manifest.get('profileId') == 'schema48-admin-data-01' and
            manifest.get('kind') == 'RackClickDistributionManifest', 'application_profile_invalid')
    distributions = manifest.get('distributions')
    require(isinstance(distributions, dict) and set(distributions) == {'server', 'frontend'}, 'application_inventory_invalid')
    wanted = {'manifest.json', 'inventory.json', 'SHA256SUMS.txt'}
    total = 0
    for group, count in (('server', 58), ('frontend', 18)):
        entries = distributions[group]
        require(isinstance(entries, dict) and len(entries) == count, 'application_inventory_invalid')
        bundle.validate_names(list(entries))
        for name, digest in entries.items():
            relative = group + '/' + name
            require(relative in files and sha(files[relative]) == digest, 'application_content_invalid')
            wanted.add(relative)
            total += len(files[relative])
    require(set(files) == wanted and len(files) == 79, 'application_inventory_invalid')
    require(total == APP_BYTES == manifest.get('totalBytes') and manifest.get('fileCount') == 76, 'application_size_invalid')
    return files


def verify_service(service_publish):
    files = read_tree(service_publish)
    require(len(files) == 37 and not any(n.lower().endswith('.exe') for n in files), 'service_inventory_invalid')
    require(all(Path(n).suffix.lower() in {'.dll', '.pdb', '.json'} for n in files), 'service_artifact_invalid')
    require(sha(files.get('RackClick.WindowsService.dll', b'')) == SERVICE_DLL_SHA, 'service_pin_invalid')
    require(tree_digest(files) == SERVICE_TREE_SHA, 'service_tree_pin_invalid')
    return files


def verify_recipe(recipe):
    require_pin(APP_SHA)
    require_pin(BUNDLE_SHA)
    require(recipe.get('format') == 'RackClickOnline20' and recipe.get('nativeEdition') == '20' and
            recipe.get('applicationSha256') == APP_SHA and recipe.get('bundleSha256') == BUNDLE_SHA and
            recipe.get('thirdPartyRuntimeBinariesDistributed') is False, 'recipe_profile_invalid')
    # The whole canonical recipe is pinned independently; metadata cannot override
    # the reused official provider versions, digests, lengths or target paths.
    require_pin(RECIPE_SHA)
    require(sha(json_bytes(recipe)) == RECIPE_SHA, 'recipe_provider_invalid')


def collect(application, service_publish, demo):
    application_files = verify_application(application)
    service_files = verify_service(service_publish)
    demo_data = bundle.read_file(Path(demo))
    require(sha(demo_data) == DEMO_SHA, 'demo_pin_invalid')
    recipe = bundle.strict_json(bundle.read_file(ROOT / 'development/online-installer20.sources.json'))
    verify_recipe(recipe)
    files = {'application/' + n: v for n, v in application_files.items()}
    files.update({'service/' + n: v for n, v in service_files.items()})
    for name in bundle.SQL_OPERATORS:
        relative = 'tools/windows/' + name
        files['source/' + relative] = bundle.read_file(ROOT / relative)
    # The reviewed worktree is the operator source, never a previously delivered ZIP.
    from package_server_installer import NETWORK_TOOLS
    for path in (ROOT / 'tools/windows/server-install').iterdir():
        bundle.clean_path(path, directory=path.is_dir())
        if path.is_file() and path.suffix.lower() in {'.ps1', '.cmd'} and path.name not in NETWORK_TOOLS:
            require(re.fullmatch('[A-Za-z0-9.-]+\\.(?:ps1|cmd)', path.name), 'installer_operator_name_invalid')
            files['source/tools/windows/server-install/' + path.name] = bundle.read_file(path)
    for relative in (*STATIC_SOURCES, *('docs/' + n for n in bundle.MANUALS)):
        files['source/' + relative] = bundle.read_file(ROOT / relative)
    lock = bundle.strict_json(files['source/development/offline-bundle14.sources.json'])
    for row in lock['sources']:
        if row['name'] == 'vc_redist.x64.exe':
            continue
        data = bundle.read_file(ROOT / row['path'])
        require(len(data) == row['bytes'] and sha(data) == row['sha256'], 'notice_pin_invalid')
        name = 'Otp.NET-LICENSE.txt' if row['name'] == 'Otp.NET-LICENSE' else row['name']
        files['notices/' + name] = data
    files['data/RackClick-Demo50-Trilingual-03.zip'] = demo_data
    files['assemble.py'] = bundle.read_file(ROOT / 'tools/online-install/assemble20.py')
    files['recipe.json'] = json_bytes(recipe)
    require(not any(n.lower().endswith(('vc_redist.x64.exe', 'python312.dll')) or
                    'dependencies/dotnet/' in n or 'dependencies/postgresql/' in n or
                    n == 'service/RackClick.WindowsService.exe' for n in files), 'restricted_runtime_in_transport')
    bundle.validate_names(list(files))
    files['FILES.json'] = json_bytes([dict(path=n, bytes=len(v), sha256=sha(v)) for n, v in sorted(files.items())])
    return files


def write_zip(files, output, prefix=''):
    target = bundle.clean_path(Path(output), exists=False)
    require(not target.exists(), 'new_output_required')
    bundle.clean_path(target.parent, directory=True)
    bundle.validate_names([prefix + n for n in files])
    with target.open('xb') as out, zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(prefix + name, STAMP)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    return dict(path=str(target), sha256=sha(target.read_bytes()), bytes=target.stat().st_size, files=len(files))


def public_demo_files(demo):
    require(sha(demo) == DEMO_SHA, 'demo_pin_invalid')
    files = {}
    for name, data in members(demo).items():
        prefix = 'RackClick-Demo50-Trilingual-03/'
        require(name.startswith(prefix), 'demo_layout_invalid')
        relative = name[len(prefix):]
        if relative.startswith('DATOS-DEMO50/'):
            files[relative] = data
    require(len(files) == 57 and {'DATOS-DEMO50/00-LEEME.md', 'DATOS-DEMO50/SHA256SUMS.txt'} <= set(files),
            'demo_release_inventory_invalid')
    # The source03 README points to its legacy application-pinned loader. Keep
    # the data/viewer bytes, update only this edition's instructions and checksums.
    files['DATOS-DEMO50/00-LEEME.md'] = (
        '# RackClick 20 · Demo50 EN/DE/ES\n\n'
        '50 empresas ficticias: 17 EN, 17 DE y 16 ES. Los nombres propios se conservan al cambiar el idioma. '
        'Abre VER-50-CLIENTES.html para consultar los datos sin conexión.\n\n'
        'Para cargar los 50 clientes en una instalación vacía, usa Administración → Datos y copias de inventario → '
        'Cargar 50 clientes y confirma. Los JSON individuales de esta carpeta son fuentes sintéticas de inventario43, '
        'no el archivo Copia de inventario del panel. Para restaurar usa una copia descargada desde ese panel. '
        'Cuentas, permisos y MFA del destino se conservan. Consulta ../00-LEEME.html.\n\n'
        'English: load the examples using Administration → Data and inventory copies → Load 50 customers on an empty inventory. '
        'These individual source JSON files are not an Inventory copy exported by the panel. Destination accounts and MFA remain.\n\n'
        'Deutsch: Beispiele bei leerem Inventar über Administration → Daten und Inventarkopien → 50 Kunden laden importieren. '
        'Die einzelnen Quell-JSONs sind keine Inventarkopie aus dem Panel. Zielkonten und MFA bleiben erhalten.\n'
    ).encode('utf-8')
    files['DATOS-DEMO50/SHA256SUMS.txt'] = ''.join(
        sha(data) + '  ' + name.removeprefix('DATOS-DEMO50/') + '\n'
        for name, data in sorted(files.items()) if name != 'DATOS-DEMO50/SHA256SUMS.txt').encode('ascii')
    return files


def package(core, native, output):
    for pin in (CORE20_SHA, NATIVE20_SHA):
        require_pin(pin)
    core_data = bundle.read_file(Path(core))
    require(sha(core_data) == CORE20_SHA, 'core_release_pin_invalid')
    native_data = bundle.read_file(Path(native), bundle.MAX_ZIP)
    require(sha(native_data) == NATIVE20_SHA, 'native_release_pin_invalid')
    core_files = members(core_data)
    rows = json.loads(core_files['FILES.json'])
    require(set(core_files) == {r['path'] for r in rows} | {'FILES.json'} and len(rows) + 1 == len(core_files), 'core_release_inventory_invalid')
    for row in rows:
        data = core_files[row['path']]
        require(len(data) == row['bytes'] and sha(data) == row['sha256'], 'core_release_content_invalid')
    recipe = bundle.strict_json(core_files['recipe.json'])
    verify_recipe(recipe)
    template = (ROOT / 'tools/windows/online-install20/Install-RackClickOnline.ps1').read_text('utf-8')
    pins = {'@@CORE_SHA@@': CORE20_SHA, '@@NATIVE_SHA@@': NATIVE20_SHA,
            '@@PY_SHA@@': recipe['python']['digest'], '@@PY_BYTES@@': str(recipe['python']['bytes']),
            '@@RECIPE_SHA@@': sha(core_files['recipe.json'])}
    for token, value in pins.items():
        require(template.count(token) == 1, 'launcher_template_invalid')
        template = template.replace(token, value)
    require('@@' not in template, 'launcher_unresolved_pin')
    files = {'RackClick-Core20.zip': core_data,
             'Install-RackClickOnline.ps1': template.replace('\r\n', '\n').replace('\n', '\r\n').encode('ascii'),
             'INICIAR-RACKCLICK.cmd': (ROOT / 'tools/windows/online-install20/INICIAR-RACKCLICK.cmd').read_bytes(),
             '00-LEEME.html': (ROOT / 'docs/INSTALADOR20-ONLINE.html').read_bytes()}
    demo = core_files['data/RackClick-Demo50-Trilingual-03.zip']
    files.update(public_demo_files(demo))
    receipt = dict(format='RackClickWindowsOnline20', edition='20', transportRevision=1, applicationSchema=48,
                   coreSha256=CORE20_SHA, nativeSha256=NATIVE20_SHA, applicationManifestSha256=APP_SHA,
                   applicationProfileId='schema48-admin-data-01', bundleSha256=BUNDLE_SHA, demoSha256=DEMO_SHA,
                   demoCustomers=50, serviceTreeSha256=SERVICE_TREE_SHA, providerDownloads=recipe['providers'] + [recipe['python']],
                   thirdPartyRuntimeBinariesIncluded=False, productionAdopted=False)
    files['ENTREGA.json'] = json_bytes(receipt)
    files['SHA256SUMS.txt'] = ''.join(sha(v) + '  ' + n + '\n' for n, v in sorted(files.items())).encode('utf-8')
    return write_zip(files, output, 'RackClick-Windows-Online-20/')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--application', type=Path)
    parser.add_argument('--service-publish', type=Path)
    parser.add_argument('--demo', type=Path)
    parser.add_argument('--core', type=Path)
    parser.add_argument('--native', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.core and args.native and not any((args.application, args.service_publish, args.demo)):
        result = package(args.core, args.native, args.output)
    elif all((args.application, args.service_publish, args.demo)) and not any((args.core, args.native)):
        result = write_zip(collect(args.application, args.service_publish, args.demo), args.output)
    else:
        parser.error('choose --application/--service-publish/--demo OR --core/--native')
    print(json.dumps(result))
