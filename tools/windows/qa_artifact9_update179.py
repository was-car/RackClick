"""Closed173 ->179 artifacts, SAME schema9 database, stopped before and after.

No installation, migration, grants, dump/restore, auth or SQL writes. An error
can restore the previous config only during this operation while XID is intact.
There is deliberately no later rollback CLI and no promise after user activity.
"""
import argparse
from dataclasses import dataclass
import hashlib
import http.client
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import NO_WINDOW, free_port
from pg_lab_recovery import sha256
from qa_schema5_candidate import checked_path
from qa_schema5_switch import atomic_bytes
from qa_schema6_source import artifact_manifest, app_stopped
from qa_schema_candidate import snapshot
from qa_schema_switch import (profile_lock, qa_module, pg_running, stop_application,
                              activity_watermark, require_unchanged_activity)
from qa_schema9_switch173 import start_private_pg173, require_temporary_pg_mode
from windows_job import run_isolated
from qa_artifact9_source179 import (Source9, UpdateError, load_source, load_target,
                                   CHANGED_FIELDS, require_config_change)


def save(path, value):
    atomic_bytes(path, (json.dumps(value, indent=2) + '\n').encode('utf-8'))


def copy_matches(version, target):
    if {'server': artifact_manifest(version / 'server'), 'frontend': artifact_manifest(version / 'frontend')} != target.expected:
        raise UpdateError('copied_complete_pair_differs')


def verify_ready(directory, cfg, target):
    if not qa_module().ready(directory, cfg):
        raise UpdateError('updated_readiness_unconfirmed')
    connection = http.client.HTTPConnection('127.0.0.1', cfg['webPort'], timeout=15)
    try:
        connection.request('GET', '/app.js')
        response = connection.getresponse()
        if response.status != 200 or hashlib.sha256(response.read()).hexdigest() != target.expected['frontend']['app.js']:
            raise UpdateError('served_bundle_differs')
    finally:
        connection.close()


class OwnedRuntime179:
    def __init__(self, directory, cfg, pointer, *, real=False):
        self.directory, self.cfg, self.pointer, self.real = directory, cfg, pointer, real
        self.owned = False
        self.process = None
        self.launch = None

    def quiet(self):
        app_stopped(self.directory, self.cfg['webPort'])
        if pg_running(self.directory):
            raise UpdateError('foreign_or_uncertain_pg_active')

    def start_pg(self):
        self.quiet()
        self.owned = True  # pg_ctl can start PG and subsequently fail or time out.
        self.launch = {'kind': 'pg-control', 'phase': 'attempted'}
        start_private_pg173(self.directory)
        require_temporary_pg_mode(self.directory, self.cfg)

    def start_app(self, config, target):
        self.quiet()  # A rejected foreign process never grants ownership.
        command = [sys.executable, '-B', str(Path(__file__).resolve()), '_supervise',
                   '--source', str(self.directory), '--pointer', str(self.pointer), '--config', str(config)]
        if self.real:
            command.append('--real-restored')
        with (self.directory / 'artifact9-supervisor-private.log').open('ab') as output:
            self.owned = True
            self.launch = {'kind': 'job-supervisor', 'phase': 'attempted'}
            try:
                self.process = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=output,
                    stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
            except Exception:
                self.owned = False
                raise
            self.launch.update(phase='child-created', supervisorPid=self.process.pid)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise UpdateError('owned_supervisor_start_failed')
            if qa_module().ready(self.directory, self.cfg):
                require_temporary_pg_mode(self.directory, self.cfg)
                verify_ready(self.directory, self.cfg, target)
                return
            time.sleep(.1)
        raise UpdateError('owned_supervisor_start_timeout')

    def stop(self):
        if not self.owned:
            return
        if self.process is not None:
            stop_application(self.directory, self.cfg)
            self.process.wait(timeout=30)
        else:
            app_stopped(self.directory, self.cfg['webPort'])
            if pg_running(self.directory):
                qa_module().control(self.directory, 'stop')
        self.quiet()
        self.owned = False
        self.process = None
        self.launch['phase'] = 'stopped-confirmed'


def validate_worker(directory, pointer, config, *, real=False):
    """Validate closed profile, exact pairs, unchanged DB fields and sealed files."""
    directory, pointer, config = checked_path(directory), checked_path(pointer), checked_path(config)
    if (directory.parent != ROOT / '.local/labs' or
            not re.fullmatch(r'manual-qa-rc9-schema9-[0-9a-f]{32}', directory.name) or
            config.parent.parent != directory / 'versions' or
            not re.fullmatch('[0-9a-f]{32}', config.parent.name) or
            config.name not in ('preview-config.json', 'selected-config.json')):
        raise UpdateError('worker_identity_invalid')
    expected_pointer = ROOT / '.local/qa-rc9/current.json' if real else directory / 'artifact9-home/current.json'
    if pointer != expected_pointer or json.loads(pointer.read_bytes()) != {'directory': str(directory)}:
        raise UpdateError('worker_profile_differs')
    version = config.parent
    inputs_path = checked_path(version / 'sealed-inputs.json')
    if checked_path(version / 'sealed-inputs.sha256').read_text(encoding='ascii').strip() != sha256(inputs_path):
        raise UpdateError('worker_inputs_seal_differs')
    inputs = json.loads(inputs_path.read_bytes())
    if set(inputs) != {'previous-config.json', 'preview-config.json', 'selected-config.json'} or any(
            sha256(checked_path(version / name)) != digest for name, digest in inputs.items()):
        raise UpdateError('worker_private_inputs_changed')
    previous = json.loads((version / 'previous-config.json').read_bytes())
    selected = json.loads((version / 'selected-config.json').read_bytes())
    cfg = json.loads(config.read_bytes())
    original_art = checked_path(previous.get('artifactDirectory', directory))
    if original_art != directory and original_art.parent != directory / 'versions':
        raise UpdateError('worker_previous_artifact_path_invalid')
    baseline, target = load_source(), load_target()
    copy_matches(original_art, baseline); copy_matches(version, target)
    require_config_change(previous, selected)
    if (previous.get('directory') != str(directory) or previous.get('profile') != 'rc9' or
            previous.get('host') != '127.0.0.1' or type(previous.get('webPort')) is not int or
            type(previous.get('pgPort')) is not int or not 1 <= previous['pgPort'] <= 65535 or
            not 1 <= previous['webPort'] <= 65535 or previous['webPort'] == previous['pgPort'] or
            real and previous['webPort'] != 52346 or selected.get('artifactDirectory') != str(version) or
            selected.get('dllSha256') != target.expected['server']['RackClick.Server.dll'] or
            selected.get('bundleSha256') != target.expected['frontend']['app.js'] or
            previous.get('dllSha256') != baseline.expected['server']['RackClick.Server.dll'] or
            previous.get('bundleSha256') != baseline.expected['frontend']['app.js']):
        raise UpdateError('worker_configuration_differs')
    current_bytes = checked_path(directory / 'manual-qa.json').read_bytes()
    if config.name == 'preview-config.json':
        if (current_bytes != (version / 'previous-config.json').read_bytes() or
                {k: v for k, v in cfg.items() if k != 'webPort'} != {k: v for k, v in selected.items() if k != 'webPort'} or
                type(cfg.get('webPort')) is not int or not 1 <= cfg['webPort'] <= 65535 or
                cfg['webPort'] in (previous['webPort'], previous['pgPort'])):
            raise UpdateError('worker_preview_scope_differs')
    elif cfg != selected or current_bytes != config.read_bytes():
        raise UpdateError('worker_selected_scope_differs')
    meta = json.loads(checked_path(directory / 'lab.json').read_bytes())
    if (meta.get('path') != str(directory) or meta.get('host') != '127.0.0.1' or
            meta.get('postgresql') != '17' or meta.get('port') != cfg['pgPort'] or
            directory.name != 'manual-qa-rc9-schema9-' + meta.get('id', '!')):
        raise UpdateError('worker_cluster_metadata_differs')
    rows = [r for r in meta['databases'] if r['name'] == cfg.get('database') and r['label'] == 'manual-qa-rc9']
    from qa_schema9_source173 import read_database
    if len(rows) != 1 or read_database(directory, rows[0], cfg['pgPort']).connection(cfg['pgPort']) != cfg.get('connection'):
        raise UpdateError('worker_database_identity_differs')
    return directory, cfg


def worker(directory, pointer, config, *, real=False, supervise=False):
    directory, cfg = validate_worker(directory, pointer, config, real=real)
    if supervise:
        command = [sys.executable, '-B', str(Path(__file__).resolve()), '_worker',
                   '--source', str(directory), '--pointer', str(pointer), '--config', str(config)]
        if real:
            command.append('--real-restored')
        with (directory / 'artifact9-worker-private.log').open('ab') as output:
            done = run_isolated(command, cwd=ROOT, stdout=output, stderr=output)
        if done.returncode:
            raise UpdateError('worker_failed')
    else:
        qa = qa_module()
        normal_control = qa.control
        def private_control(owned_directory, action):
            if checked_path(owned_directory) != directory:
                raise UpdateError('worker_pg_scope_differs')
            if action == 'start':
                start_private_pg173(directory)
                require_temporary_pg_mode(directory, cfg)
            else:
                normal_control(directory, action)
        qa.control = private_control  # New module instance; historical file unchanged.
        qa.serve(directory, cfg)


@dataclass
class Result179:
    source: object
    version: Path
    journal: Path
    state: str = 'validated'


def update(directory, pointer, *, real=False, hook=None):
    initial = Source9(directory, pointer, real=real)
    if initial.pg_running():
        raise UpdateError('source9_pg_already_active')
    target = load_target()
    with profile_lock(initial.pointer):
        source = Source9(directory, pointer, real=real)
        if source.original_hashes != initial.original_hashes or source.pointer_bytes != initial.pointer_bytes:
            raise UpdateError('source9_changed_before_lock')
        runtime = OwnedRuntime179(source.directory, source.cfg, source.pointer, real=real)
        runtime.quiet()
        version = checked_path(source.directory / 'versions' / uuid.uuid4().hex)
        journal = source.directory / ('artifact9-update-' + uuid.uuid4().hex + '.json')
        result = Result179(source, version, journal)
        state = dict(state='validated', schema=9, transition='173-179', activationConfirmed=False,
            targetManifestSha256=sha256(target.manifest), sourceInputHashes=source.original_hashes,
            pointerSha256=sha256(source.pointer), previousConfigSha256=sha256(source.directory / 'manual-qa.json'))
        reference = before = old_history = old_oid = None
        selected = False
        selected_bytes = source.config_bytes
        version_inputs = None

        def checkpoint(name):
            result.state = state['state'] = name
            state['ownedLaunch'] = runtime.launch
            save(journal, state)
            if hook:
                hook(name, result)

        def verify_readonly():
            require_unchanged_activity(source.directory, source.cfg, reference)
            if (snapshot(source.sql) != before or source.check_schema9() != old_history or
                    source.sql('SELECT oid FROM pg_database WHERE datname=current_database()') != old_oid):
                raise UpdateError('rows_history_or_database_oid_changed')
            require_unchanged_activity(source.directory, source.cfg, reference)

        def verify_version():
            if version_inputs is None:
                raise UpdateError('version_private_inputs_missing')
            copy_matches(version, target)
            if {name: sha256(checked_path(version / name)) for name in version_inputs} != version_inputs:
                raise UpdateError('version_private_inputs_changed')

        try:
            checkpoint('validated')
            runtime.start_pg()
            old_history = source.check_schema9()
            before = snapshot(source.sql)
            old_oid = source.sql('SELECT oid FROM pg_database WHERE datname=current_database()')
            reference = activity_watermark(source.directory, source.cfg)  # Exactly once.
            state.update(history=old_history, rows=before, databaseOid=old_oid, activityBaseline=reference)
            runtime.stop()
            version.mkdir(parents=True, exist_ok=False)
            for name in ('server', 'frontend'):
                shutil.copytree(getattr(target, name), version / name)
            new_cfg = dict(source.cfg, artifactDirectory=str(version), dllSha256=target.expected['server']['RackClick.Server.dll'],
                           bundleSha256=target.expected['frontend']['app.js'])
            require_config_change(source.cfg, new_cfg)
            selected_bytes = (json.dumps(new_cfg, indent=2) + '\n').encode('utf-8')
            atomic_bytes(version / 'previous-config.json', source.config_bytes)
            atomic_bytes(version / 'selected-config.json', selected_bytes)
            preview_cfg = dict(new_cfg, webPort=free_port())
            while preview_cfg['webPort'] in (source.cfg['webPort'], source.cfg['pgPort']):
                preview_cfg['webPort'] = free_port()
            save(version / 'preview-config.json', preview_cfg)
            inputs = {name: sha256(version / name) for name in ('previous-config.json', 'preview-config.json', 'selected-config.json')}
            save(version / 'sealed-inputs.json', inputs)
            atomic_bytes(version / 'sealed-inputs.sha256', (sha256(version / 'sealed-inputs.json') + '\n').encode('ascii'))
            version_inputs = {**inputs, 'sealed-inputs.json': sha256(version / 'sealed-inputs.json'),
                              'sealed-inputs.sha256': sha256(version / 'sealed-inputs.sha256')}
            verify_version(); target.validate(); source.unchanged()
            state.update(versionDirectory=str(version), versionInputHashes=version_inputs,
                         selectedConfigSha256=hashlib.sha256(selected_bytes).hexdigest())
            checkpoint('prepared')
            runtime.cfg = preview_cfg
            runtime.start_app(version / 'preview-config.json', target)
            verify_readonly()
            runtime.stop()
            runtime.cfg = source.cfg
            source.unchanged(); target.validate(); verify_version()
            checkpoint('before_config')
            source.unchanged(); runtime.quiet(); verify_version()
            atomic_bytes(source.directory / 'manual-qa.json', selected_bytes)
            selected = True
            checkpoint('after_config')
            runtime.cfg = new_cfg
            runtime.start_app(version / 'selected-config.json', target)
            checkpoint('after_start')
            verify_readonly()
            source.unchanged(selected_bytes, quiet=False); target.validate(); verify_version()
            runtime.stop()
            runtime.start_pg()
            try:
                verify_readonly()
            finally:
                runtime.stop()
            source.unchanged(selected_bytes); runtime.quiet()
            state.update(activationConfirmed=True, leftRunning=False, databaseReconstructed=False,
                         pointerUnchanged=True, stopConfirmed=True)
            checkpoint('committed')
            return result
        except Exception as error:
            state['failureCode'] = getattr(error, 'code', 'artifact9_internal_failure')
            recovered = False
            try:
                runtime.stop(); runtime.quiet()
                source.unchanged(selected_bytes if selected else source.config_bytes)
                target.validate()
                if version_inputs is not None:
                    verify_version()
                if reference is not None:
                    runtime.cfg = source.cfg
                    runtime.start_pg()
                    try:
                        verify_readonly()
                    finally:
                        runtime.stop()
                elif selected:
                    raise UpdateError('activity_reference_missing')
                source.unchanged(selected_bytes if selected else source.config_bytes)
                runtime.quiet()
                if selected:
                    atomic_bytes(source.directory / 'manual-qa.json', source.config_bytes)
                source.unchanged()
                recovered = True
            except Exception as blocker:
                state['recoveryBlocker'] = getattr(blocker, 'code', 'rollback_verification_uncertain')
                try:
                    runtime.stop()
                except Exception:
                    pass
            quiet = False
            try:
                runtime.quiet()
                quiet = not runtime.owned
            except Exception:
                pass
            result.state = state['state'] = 'rolled_back' if recovered and quiet else 'recovery_required'
            state.update(activationConfirmed=False, leftRunning=False if quiet else None,
                         stopConfirmed=quiet, ownedLaunch=runtime.launch)
            try:
                save(journal, state)
            except Exception:
                raise UpdateError('artifact9_journal_unconfirmed', result) from None
            raise UpdateError(result.state, result) from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('update', '_supervise', '_worker'))
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--pointer', type=Path, required=True)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--real-restored', action='store_true')
    args = parser.parse_args()
    try:
        if args.action == 'update':
            if args.config is not None:
                raise UpdateError('update_config_override_not_supported')
            result = update(args.source, args.pointer, real=args.real_restored)
            print(json.dumps(dict(state=result.state, schema=9, activationConfirmed=True,
                leftRunning=False, databaseReconstructed=False, pointerUnchanged=True)))
        else:
            if args.config is None:
                raise UpdateError('worker_config_required')
            worker(args.source, args.pointer, args.config, real=args.real_restored, supervise=args.action == '_supervise')
        return 0
    except Exception as error:
        print(json.dumps(dict(state=getattr(error, 'code', 'artifact9_validation_failed'), schema=9,
                              activationConfirmed=False, leftRunning=None)), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
