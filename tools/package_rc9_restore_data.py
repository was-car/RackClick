"""Package PRIVATE user-requested RC9 data, not a development/application bundle."""
import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
SOURCE_SHA = 'cb52d27990a82d3f2dc12bf731bcbe6c1586575643f301e4b040b250f31374d0'
MANIFEST_SHA = '16f3dec13fbbbbce05db5d2126a49d0c8746e1533686102e775d7b1c43cd4bb2'
DUMP_SHA = 'e8475d82c0c5e54211017829682d47bd087b90d0df119396011bf80bc2712e3b'


def no_reparse(path):
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('data_package_reparse_rejected')


def build(output, version=1):
    if version not in (1, 2):
        raise ValueError('data_package_version_invalid')
    output = output.absolute()
    if output.parent != LOCAL or output.suffix.lower() != '.zip' or output.exists():
        raise ValueError('new_local_zip_required')
    no_reparse(output)
    backup = LOCAL / 'rc9-server-restore-original-20261020-01/backup'
    sources = {'backup/manifest.json': backup / 'manifest.json',
               'backup/data.dump': backup / 'data.dump',
               'original/RackClick-backup-all.json': ROOT / 'RackClick-backup-all.json'}
    if {p.name for p in backup.iterdir()} != {'manifest.json', 'data.dump'}:
        raise ValueError('data_backup_inventory_invalid')
    payload = {}
    expected = {'backup/manifest.json': MANIFEST_SHA, 'backup/data.dump': DUMP_SHA,
                'original/RackClick-backup-all.json': SOURCE_SHA}
    for name, path in sources.items():
        no_reparse(path)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected[name]:
            raise ValueError('data_input_hash_mismatch')
        payload[name] = data
    manifest = json.loads(payload['backup/manifest.json'])
    if (manifest['dumpFile'] != 'data.dump' or manifest['dumpSha256'] != DUMP_SHA or
            manifest['dumpBytes'] != len(payload['backup/data.dump']) or
            manifest['postgresVersion'] != '17.11' or
            not payload['backup/data.dump'].startswith(b'PGDMP')):
        raise ValueError('data_backup_manifest_invalid')
    metadata = dict(kind='RackClickPrivateQaDataBackup', version=1,
                    applicationIncluded=False, installedOnTargetVm=False,
                    sourceSha256=SOURCE_SHA, backupManifestSha256=MANIFEST_SHA,
                    dumpSha256=DUMP_SHA, schema=13, postgresql='17.11',
                    counts=dict(customers=10, sites=15, buildings=25, rooms=68,
                                racks=68, devices=311, portGroups=633, ports=5408,
                                connections=623),
                    fullGlobalMetadataMigrationClaimed=False,
                    sourceOriginalPreserved=True,
                    files=[dict(path=n, bytes=len(payload[n]), sha256=expected[n])
                           for n in sorted(payload)])
    payload['DATOS.json'] = (json.dumps(metadata, indent=2) + '\n').encode('utf-8')
    payload['00-LEEME.html'] = ('''<!doctype html><html lang="es"><meta charset="utf-8">
<title>RackClick · datos privados de QA</title><style>body{font:18px/1.6 system-ui;max-width:900px;margin:40px auto;padding:0 24px;color:#192b3a}code{background:#eef2f5;padding:2px 5px}li{margin-bottom:12px}</style>
<h1>Datos originales preparados para restauración independiente</h1>
<p>20.10.2026. Este es un <strong>backup privado de datos solicitado por Wascar</strong>, separado del instalador. Conserva el JSON original íntegro y una conversión a PostgreSQL 17.11, esquema 13. No se ha aplicado en la VM.</p>
<p>Contiene 10 clientes, 15 sitios, 25 edificios, 68 salas, 68 racks, 311 equipos, 633 grupos de puertos, 5.408 puertos y 623 conexiones. La conversión compara las 10 tablas importadas; una revisión independiente restauró el dump en otra base nueva, comprobó 39 tablas y 13 migraciones, recuentos y 1.246 extremos, y verificó el rechazo de una base de destino existente.</p>
<p>Los metadatos globales RC9 que el servidor todavía no modela permanecen en <code>original/RackClick-backup-all.json</code>. Su conservación no significa que todas esas preferencias sean funciones activas del servidor.</p>
<h2>Estado actual</h2><p>El servicio de la instancia 606b de la VM 192.168.178.141 se detiene al arrancar. Primero recoger el diagnóstico de arranque y resolver su causa. Este ZIP no repara el servicio ni cambia la instancia existente.</p>
<h2>Restauración posterior, conservando606b</h2>
<ol><li>Copia este ZIP a la VM y usa <strong>Extraer todo</strong>. La carpeta que debe elegirse en el asistente es <code>backup</code>, que contiene únicamente <code>manifest.json</code> y <code>data.dump</code>.</li>
<li>Para crear una instancia adicional usa el asistente directo: desde el paquete completo 05 extraído, extrae también <code>Servidor.zip</code> en una carpeta nueva y abre <code>RackClick-Instalador/INSTALAR-RACKCLICK.cmd</code>. <strong>No uses 00-LIMPIAR-Y-REINSTALAR.cmd para añadirla</strong>: ese flujo archiva los hubs existentes.</li>
<li>En el asistente selecciona <strong>Restore</strong>. Propón IP/DNS 192.168.178.141, HTTPS 5444 y PostgreSQL 55442, servicio <code>RackClick-Recovery-cb52d279</code>, cuenta <code>RackClickSvcRc9</code> y administrador <code>Wascar</code>. El preflight debe confirmar que esos nombres/puertos están libres; si no, detenerse y conservar el informe. No reutilices puertos/servicio de 606b.</li>
<li>En <strong>Carpeta del backup</strong> pega la ruta de la carpeta <code>backup</code> extraída. En <strong>SHA256 del manifiesto</strong> pega:<br><code>''' + MANIFEST_SHA + '''</code></li>
<li>Revisar e instalar crea un nuevo GUID, cluster/base/cuentas/claves. La instancia 606b y su base deben conservarse. Este recorrido Restore 05 completo sigue pendiente de ejecución en esa VM; el ensayo de restauración de laboratorio no lo sustituye.</li>
<li>Consultar las nuevas credenciales de esa instancia, abrir la nueva URL y verificar los 10 clientes. Cerrar cualquier vista de credenciales antes de capturar resultados. Después comprobar escritura/recarga/otra sesión, reinicio, backup y recuperación. Registrar Pass/NotPass sin sobrescribir observaciones anteriores.</li></ol>
<p>Guarda este ZIP como datos privados. No forma parte de un paquete público de desarrollo y no contiene binarios ni archivos privados de credenciales del laboratorio.</p></html>''').encode('utf-8')
    if version == 2:
        current_sources = {
            '00-LEEME.html': ROOT / 'docs/RESTAURAR-FULL-BACKUP-VM.html',
            'Show-RackClickRc9RestoredAccess.ps1': ROOT / 'tools/windows/server-install/Show-RackClickRc9RestoredAccess.ps1',
        }
        for name, path in current_sources.items():
            no_reparse(path)
            payload[name] = path.read_bytes()
        payload['01-VER-ACCESO-RESTAURADO.cmd'] = (
            '@echo off\r\n'
            'setlocal\r\n'
            'echo RackClick - Acceso privado de la instancia restaurada en 5444\r\n'
            'echo Ejecute como administrador en la VM 192.168.250.78.\r\n'
            '"%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Show-RackClickRc9RestoredAccess.ps1"\r\n'
            'set "rackClickResult=%ERRORLEVEL%"\r\n'
            'echo Codigo final: %rackClickResult%\r\n'
            'pause\r\n'
            'exit /b %rackClickResult%\r\n').encode('ascii')
        metadata.update(version=2, accessViewerReadOnly=True,
                        targetPublicOrigin='https://192.168.250.78:5444',
                        targetService='RackClick-Recovery-cb52d279',
                        files=[dict(path=n, bytes=len(payload[n]),
                                    sha256=hashlib.sha256(payload[n]).hexdigest())
                               for n in sorted(payload) if n != 'DATOS.json'])
        payload['DATOS.json'] = (json.dumps(metadata, indent=2) + '\n').encode('utf-8')
    with output.open('xb') as stream, zipfile.ZipFile(stream, 'w') as archive:
        for name in sorted(payload):
            info = zipfile.ZipInfo(f'RackClick-Datos-QA-RC9-{version:02d}/' + name, (2026, 10, 20, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100600 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    return dict(archive=str(output), bytes=output.stat().st_size,
                sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                entries=len(payload), privateUserData=True, installedOnTargetVm=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--version', type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.version), indent=2))
