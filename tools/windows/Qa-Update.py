"""Reversible artifact-only update of stopped rc9 QA. Never modifies its database."""
import argparse
import hashlib
import importlib
import json
import msvcrt
import os
from pathlib import Path
import shutil
import socket
import uuid

qa = importlib.import_module('Qa-Local')


def atomic_config(directory, value):
    target = directory / 'manual-qa.json'
    temporary = directory / 'manual-qa.update.tmp'
    with temporary.open('w', encoding='utf-8') as output:
        json.dump(value, output, indent=2)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, target)


def install(directory, cfg, server_source, frontend_source, dll_hash, bundle_hash):
    # Called only under the profile command lock after confirming both processes stopped.
    qa.artifact_directory(directory, cfg)
    if hashlib.sha256((server_source / 'RackClick.Server.dll').read_bytes()).hexdigest() != dll_hash or hashlib.sha256((frontend_source / 'app.js').read_bytes()).hexdigest() != bundle_hash:
        raise RuntimeError('Candidate differs from reviewed hashes')
    version = directory / 'versions' / uuid.uuid4().hex
    version.mkdir(parents=True, exist_ok=False)
    shutil.copytree(server_source, version / 'server')
    shutil.copytree(frontend_source, version / 'frontend')
    new_cfg = cfg | {'artifactDirectory': str(version), 'dllSha256': dll_hash, 'bundleSha256': bundle_hash}
    qa.artifact_directory(directory, new_cfg)
    # Originals are retained. A crash before atomic replacement leaves the prior config active.
    (version / 'previous-config.json').write_bytes((directory / 'manual-qa.json').read_bytes())
    atomic_config(directory, new_cfg)
    return version


def rollback(directory, cfg):
    version = qa.artifact_directory(directory, cfg, verify=False)
    if version == directory.resolve():
        raise RuntimeError('No previous artifact version')
    previous = json.loads((version / 'previous-config.json').read_text(encoding='utf-8'))
    for key in ('directory', 'profile', 'host', 'webPort', 'pgPort', 'database', 'connection'):
        if previous.get(key) != cfg.get(key):
            raise RuntimeError('Previous configuration belongs to another QA')
    qa.artifact_directory(directory, previous)
    atomic_config(directory, previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('rc9',), required=True)
    parser.add_argument('--dll-sha256')
    parser.add_argument('--bundle-sha256')
    parser.add_argument('--no-schema-change', action='store_true', required=True)
    parser.add_argument('--rollback', action='store_true')
    args = parser.parse_args()
    qa.configure(args.profile)
    with (qa.HOME / 'control.lock').open('a+b') as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        directory, cfg = qa.load()
        if qa.running(directory) or qa.healthy(cfg):
            raise RuntimeError('Stop only restored QA before updating artifacts')
        with socket.socket() as probe:
            probe.settimeout(1)
            if probe.connect_ex(('127.0.0.1', cfg['pgPort'])) == 0:
                raise RuntimeError('QA PostgreSQL must also be stopped')
        if args.rollback:
            rollback(directory, cfg)
        else:
            if not args.dll_sha256 or not args.bundle_sha256:
                parser.error('Both reviewed artifact hashes required')
            install(directory, cfg, qa.DEFAULT_DLL.parent, qa.ROOT / 'development/frontend/dist', args.dll_sha256, args.bundle_sha256)
    print('QA rc9 artifacts changed; database/accounts/original QA untouched. Start with INICIAR-QA-RESTAURADO.cmd.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('QA update failed: ' + type(error).__name__ + '; no database changes.')
        raise SystemExit(1)
