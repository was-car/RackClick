"""Convert the pinned ORIGINAL RC9 JSON into a private native Restore05 backup.

Creates only a new isolated Lab and a new .local output directory. Never selects
or modifies manual QA, its pointers, an installed instance, or a Windows service.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import socket
import subprocess
import sys
import traceback
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / '.local'
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import Lab, NO_WINDOW, protect_directory, toolchain
from rc9_restore import analyze, restore
from windows_job import run_isolated

SOURCE_SHA = 'cb52d27990a82d3f2dc12bf731bcbe6c1586575643f301e4b040b250f31374d0'
BUNDLE_SHA = 'a0df90ed3a2864492d8d9bdc2cc2e552113a6b9c81a3e603c1c2920486c26869'
BUNDLE_MANIFEST_SHA = '03e1b4a268250f4a98cec28a402d449cd1bfbcd589aa9f6eeb6c90bc123ca7cd'
APP_MANIFEST_SHA = '55bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6'
SERVER_SHA = '15586afdd75f0c244dd5b8123aab33a6264c43ad7f62831f8e7442404dfa0f0d'
IMPORTER_SHA = 'ca7ea948a47d1ea973ae25832c049bb8b746c79638db7e9ce314a9f7d8b5984e'
LAB_HELPER_SHA = '78488412678bdcc27cdd39e8a003f0a50c9e60d085a6801c50e91b9501d755c3'
COUNTS = dict(customers=10, sites=15, buildings=25, rooms=68, racks=68,
              devices=311, portGroups=633, ports=5408, connections=623,
              localConnections=565, crossConnections=58)
DEFAULT_BUNDLE = LOCAL / 'offline1509-d941791809a84ee69aa0d4c62bd97484-a.zip'


class PreparationError(RuntimeError):
    pass


def fail(code):
    raise PreparationError(code)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def no_reparse(path):
    for item in (Path(path), *Path(path).parents):
        if item.exists() and (item.is_symlink() or item.is_junction()):
            fail('rc9_prepare_reparse_rejected')


def validate_output(path):
    path = Path(os.path.abspath(path))
    no_reparse(path)
    if path.parent != LOCAL or not re.fullmatch(r'rc9-server-restore-[a-z0-9-]{1,64}', path.name):
        fail('rc9_prepare_output_must_be_new_local_root')
    if path.exists():
        fail('rc9_prepare_output_exists')
    return path


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as target:
        json.dump(value, target, ensure_ascii=True, indent=2)
        target.write('\n')


def validate_backup(directory, receipt):
    directory = Path(directory)
    if {p.name for p in directory.iterdir()} != {'manifest.json', 'data.dump'}:
        fail('rc9_prepare_backup_inventory_invalid')
    for path in (directory, directory / 'manifest.json', directory / 'data.dump'):
        no_reparse(path)
    manifest_path = directory / 'manifest.json'
    if manifest_path.stat().st_size > 65536:
        fail('rc9_prepare_backup_manifest_invalid')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    expected = {'schemaVersion', 'kind', 'postgresVersion', 'format', 'dumpFile',
                'dumpBytes', 'dumpSha256', 'createdUtc'}
    dump = directory / 'data.dump'
    with dump.open('rb') as stream:
        magic = stream.read(5)
    if (set(manifest) != expected or type(manifest['schemaVersion']) is not int or
            manifest['schemaVersion'] != 1 or manifest['kind'] != 'RackClickDatabaseBackup' or
            manifest['postgresVersion'] != '17.11' or manifest['format'] != 'custom' or
            manifest['dumpFile'] != 'data.dump' or type(manifest['dumpBytes']) is not int or
            manifest['dumpBytes'] != dump.stat().st_size or manifest['dumpBytes'] < 5 or
            manifest['dumpSha256'] != sha256(dump) or magic != b'PGDMP'):
        fail('rc9_prepare_backup_manifest_invalid')
    manifest_sha = sha256(manifest_path)
    if (receipt.get('valid') is not True or receipt.get('success') is not True or
            type(receipt.get('exitCode')) is not int or receipt['exitCode'] != 0 or
            receipt.get('code') != 'backup_complete' or
            receipt.get('manifestSha256') != manifest_sha or
            Path(receipt.get('backupPath', '')).resolve() != directory.resolve()):
        fail('rc9_prepare_backup_receipt_invalid')
    return manifest, manifest_sha


def frozen_artifacts(bundle, output):
    no_reparse(bundle)
    if sha256(bundle) != BUNDLE_SHA:
        fail('rc9_prepare_bundle_hash_mismatch')
    with zipfile.ZipFile(bundle) as archive:
        raw = archive.read('bundle.json')
        if hashlib.sha256(raw).hexdigest() != BUNDLE_MANIFEST_SHA:
            fail('rc9_prepare_bundle_manifest_mismatch')
        manifest = json.loads(raw)
        if (manifest['versions']['schema'] != 13 or
                manifest['versions']['postgresql'] != '17.11' or
                manifest['versions']['dotnetRuntime'] != '10.0.12' or
                hashlib.sha256(archive.read('application/manifest.json')).hexdigest() != APP_MANIFEST_SHA):
            fail('rc9_prepare_bundle_versions_mismatch')
        selected = {name: entry for name, entry in manifest['files'].items()
                    if name.startswith(('application/server/', 'operators/'))}
        if (sum(name.startswith('application/server/') for name in selected) != 22 or
                sum(name.startswith('operators/') for name in selected) != 25 or
                sum(entry['bytes'] for entry in selected.values()) > 16777216):
            fail('rc9_prepare_artifact_inventory_invalid')
        for name, entry in selected.items():
            relative = name.removeprefix('application/')
            parts = PurePosixPath(relative).parts
            if any(part in ('.', '..') or not re.fullmatch(r'[A-Za-z0-9_.-]+', part) for part in parts):
                fail('rc9_prepare_artifact_path_invalid')
            target = output.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            data = archive.read(name)
            if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
                fail('rc9_prepare_artifact_hash_mismatch')
            with target.open('xb') as stream:
                stream.write(data)
    dll = output / 'server/RackClick.Server.dll'
    if sha256(dll) != SERVER_SHA:
        fail('rc9_prepare_server_hash_mismatch')
    return dll


def verify_toolchain(output):
    global_json = json.loads((ROOT / 'development/server/global.json').read_text(encoding='utf-8-sig'))
    if global_json.get('sdk') != {'version': '10.0.401', 'rollForward': 'disable', 'allowPrerelease': False}:
        fail('rc9_prepare_sdk_pin_changed')
    tools = toolchain()
    commands = [(tools['dotnet'], '--version', '10.0.401'),
                (tools['postgresql'].parent / 'pg_dump.exe', '--version', 'pg_dump (PostgreSQL) 17.11')]
    for index, (executable, argument, expected) in enumerate(commands):
        no_reparse(executable)
        checked = subprocess.run([str(executable), argument], cwd=ROOT / 'development/server',
                                 capture_output=True, timeout=20, creationflags=NO_WINDOW)
        with (output / ('version-' + str(index) + '-private.log')).open('xb') as log:
            log.write(checked.stdout + checked.stderr)
        if checked.returncode or checked.stdout.decode('utf-8-sig').strip() != expected:
            fail('rc9_prepare_tool_version_mismatch')


def verify_rows(lab, database, plan):
    schema = lab.sql(database, 'SELECT string_agg(version::text,\',\' ORDER BY version) FROM schema_migration;', sensitive=True)
    if schema != ','.join(map(str, range(1, 14))):
        fail('rc9_prepare_schema13_required')
    table_count = int(lab.sql(database, "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p');", sensitive=True))
    if table_count != 39:
        fail('rc9_prepare_schema_table_inventory_changed')
    table_counts = {}
    for table, rows in plan['rows'].items():
        columns = list(rows[0]) if rows else []
        if not columns:
            fail('rc9_prepare_expected_rows_missing')
        projection = ','.join("'" + key + "'," + key for key in columns)
        actual = json.loads(lab.sql(database, f'SELECT jsonb_agg(jsonb_build_object({projection}))::text FROM {table}', sensitive=True))
        key = (lambda row: (row['connection_id'], row['ordinal'])) if table.endswith('_endpoint') else (lambda row: row['id'])
        if {key(row): row for row in actual} != {key(row): row for row in rows}:
            fail('rc9_prepare_persisted_rows_differ')
        table_counts[table] = len(actual)
    return table_counts, table_count


def prepare(source, bundle, destination):
    if os.name != 'nt':
        fail('rc9_prepare_windows_required')
    output = validate_output(destination)
    no_reparse(source)
    if Path(source).stat().st_size != 1299603 or sha256(source) != SOURCE_SHA:
        fail('rc9_prepare_original_source_mismatch')
    if (sha256(ROOT / 'tools/windows/rc9_restore.py') != IMPORTER_SHA or
            sha256(ROOT / 'development/server/tests/pg_support.py') != LAB_HELPER_SHA):
        fail('rc9_prepare_helper_pin_changed')
    pointers = [LOCAL / 'qa-rc9/current.json', LOCAL / 'qa-wascar/current.json']
    pointer_hashes = {str(path.relative_to(ROOT)): sha256(path) for path in pointers if path.is_file()}
    output.mkdir(exist_ok=False)
    protect_directory(output)
    lab = None
    report = {'schemaVersion': 1, 'valid': False, 'success': False, 'exitCode': 2,
              'code': 'rc9_prepare_incomplete', 'originalSourceSha256': SOURCE_SHA,
              'laboratoryStopped': False, 'qaPointersUnchanged': False,
              'targetVmModified': False, 'productAdopted': False}
    try:
        verify_toolchain(output)
        dll = frozen_artifacts(Path(bundle), output)
        snapshot = output / 'original-rc9-private.json'
        with snapshot.open('xb') as stream:
            stream.write(Path(source).read_bytes())
        if sha256(snapshot) != SOURCE_SHA:
            fail('rc9_prepare_source_changed')
        plan = analyze(snapshot)
        if plan['counts'] != COUNTS:
            fail('rc9_prepare_original_counts_changed')
        lab = Lab('rc9-server-restore')
        report['privateLabDirectory'] = str(lab.directory)
        lab.start()
        database = lab.create_database('original-rc9-export')
        boot = lab.bootstrap(database, 'rc9-import-' + uuid.uuid4().hex[:12], secrets.token_urlsafe(32), dll=dll)
        with (output / 'bootstrap-private.log').open('xb') as log:
            log.write(boot.stdout.encode('utf-8') + boot.stderr.encode('utf-8'))
        if boot.returncode:
            fail('rc9_prepare_bootstrap_failed')
        actor = lab.sql(database, 'SELECT id::text FROM app_user;', sensitive=True)
        imported = restore(lab, database, snapshot, actor)
        if not imported['committed'] or imported['sourceSha256'] != SOURCE_SHA:
            fail('rc9_prepare_import_not_confirmed')
        table_counts, table_count = verify_rows(lab, database, plan)
        profile = database.directory / 'backup-profile.json'
        password_file = database.directory / 'backup-owner-password.txt'
        with password_file.open('x', encoding='utf-8') as private:
            private.write(database.owner_password + '\n')
        write_new(profile, dict(schemaVersion=1, host='127.0.0.1', port=lab.port,
                                database=database.name, user=database.owner, passwordFile=str(password_file)))
        backup = output / 'backup'
        environment = lab.environment()
        environment['PSModulePath'] = str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/Modules')
        command = [str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'),
                   '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File',
                   str(output / 'operators/New-RackClickDatabaseBackup.ps1'),
                   '-PostgresBinPath', str(lab.pg_bin), '-ProfilePath', str(profile), '-DestinationPath', str(backup)]
        stdout = output / 'native-backup-private.stdout.log'
        with stdout.open('xb') as out, (output / 'native-backup-private.stderr.log').open('xb') as err:
            exported = run_isolated(command, cwd=output, env=environment, stdout=out, stderr=err, timeout=180)
        if exported.returncode:
            fail('rc9_prepare_native_backup_failed')
        receipt = json.loads(stdout.read_text(encoding='utf-8-sig'))
        manifest, manifest_sha = validate_backup(backup, receipt)
        report.update(counts=COUNTS, tableRows=table_counts, importedTables=len(table_counts),
                      publicTableCount=table_count, allImportedColumnsVerified=True, schemaVersionRestored=13,
                      backupPath=str(backup), manifestSha256=manifest_sha,
                      dumpSha256=manifest['dumpSha256'], dumpBytes=manifest['dumpBytes'],
                      sourceBundleSha256=BUNDLE_SHA, sourceBundleManifestSha256=BUNDLE_MANIFEST_SHA,
                      serverDllSha256=SERVER_SHA, originalMetadataArchived=True,
                      fullGlobalMetadataMigrationClaimed=False)
        report['code'] = 'rc9_prepare_backup_validated_cleanup_pending'
    except Exception as error:
        report['code'] = str(error) if isinstance(error, PreparationError) else 'rc9_prepare_failed_private_evidence_retained'
        with (output / 'exception-private.log').open('x', encoding='utf-8') as private:
            private.write(traceback.format_exc())
        raise
    finally:
        if lab is not None:
            lab.close()
            if lab.running or (lab.data / 'postmaster.pid').exists():
                fail('rc9_prepare_lab_stop_not_confirmed')
            with socket.socket() as probe:
                probe.settimeout(1)
                if probe.connect_ex(('127.0.0.1', lab.port)) == 0:
                    fail('rc9_prepare_lab_port_still_open')
            report['laboratoryStopped'] = True
        after = {str(path.relative_to(ROOT)): sha256(path) for path in pointers if path.is_file()}
        report['qaPointersUnchanged'] = pointer_hashes == after
        if not report['qaPointersUnchanged']:
            fail('rc9_prepare_qa_pointer_changed')
        write_new(output / 'PREPARACION.json', report)
    report.update(valid=True, success=True, exitCode=0, code='rc9_native_restore_backup_prepared')
    write_new(output / 'RESULTADO.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'RackClick-backup-all.json')
    parser.add_argument('--bundle', type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        answer = prepare(args.source, args.bundle, args.output)
    except Exception as error:
        code = str(error) if isinstance(error, PreparationError) else 'rc9_prepare_failed_private_evidence_retained'
        answer = dict(valid=False, success=False, exitCode=2, code=code)
    print(json.dumps(answer, ensure_ascii=True, separators=(',', ':')))
    return answer['exitCode']


if __name__ == '__main__':
    raise SystemExit(main())
