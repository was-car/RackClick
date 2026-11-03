"""Approved RC9 schema7 -> schema7 artifacts only, stopped before/after.

No migrate/bootstrap/dump/restore, database creation, authentication or SQL writes.
Real mode is explicit and needs the coordinator's separate operational GO.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import Database, NO_WINDOW, free_port, toolchain
from pg_lab_recovery import sha256
from qa_schema6_source import Source4, PRIVATE_FILES, artifact_manifest, app_stopped
from qa_schema6_real_candidate import load_target, history
from qa_schema_candidate import snapshot
from qa_schema5_candidate import checked_path
from qa_schema5_switch import atomic_bytes
from qa_schema_switch import (profile_lock, qa_module, pg_running, start_supervisor,
    stop_application, activity_watermark, require_unchanged_activity)
from windows_job import run_isolated

# Only the coordinator's frozen public manifest may be added here. No arbitrary
# --manifest/--hash acceptance and no DEFAULT_DLL or mutable frontend/dist.
APPROVED60 = ('evidence/s1-20261017/tres-tandas-60/CANDIDATA60.json',
              '2f4bacaa2f4c5596d6f5d7f4a0ef2d9dd2067902d0cd790b74ce3933b64efccd')
APPROVED61 = ('evidence/s1-20261017/tres-tandas-61/CANDIDATA61.json',
              'd14e799e6a4a0f5bb2624be336dba53b06793a37d064b6f997a7e231b6d9ffc7')
APPROVED62 = ('evidence/s1-20261017/tres-tandas-62/CANDIDATA62.json',
              'ba9654b0228f4278b157f3ac568d46595ffb5d8b98a27a47ff78564f71def3e9')
APPROVED68 = ('evidence/s1-20261017/seis-tandas-63-68/CANDIDATA68-FINAL02.json',
              '8ad1b29ff15126e8401278529108e437f944b6cb7730a737846c864d8e2c6aaa')
APPROVED83 = ('evidence/s1-20261017/quince-tandas-69-83/CANDIDATA83-FINAL02.json',
              '941f15309ab553179533ab7a91d1d5c1ddcab693ace9d2c604d32749eaf1bcb3')
APPROVED98 = ('evidence/s1-20261017/quince-tandas-84-98/CANDIDATA98.json',
              'b3a171983f5540b9d77ff0faad6ae02c4482669039c093051e4f9259a391f7f6')
APPROVED59 = ('evidence/s1-20261017/quince-tandas-55-59/CANDIDATA7.json',
              'c5447d77c903bb5a9fc51d7add3ba6f3295ae37904e69a0db08ab26d9716d332')
APPROVED113 = ('evidence/s1-20261017/quince-tandas-99-113/CANDIDATA113-FINAL02.json', 'db9d96af6508a4436f43cceb0fdfd55fb57992a7b938de0fa9aeaee05f794376')
APPROVED128 = ('evidence/s1-20261017/quince-tandas-114-128/CANDIDATA128.json', 'e02d3e490863b2dff14b01f9ca0f4c581e8cd87cd76d9a1ae36563ede3ac68bd')
CHANGED_FIELDS = {'artifactDirectory', 'dllSha256', 'bundleSha256'}


@dataclass(frozen=True)
class ApprovedTransition:
    key: str
    source: int
    target: int


LEGACY = ApprovedTransition('59-60', 59, 60)
TRANSITION61 = ApprovedTransition('60-61', 60, 61)
TRANSITION62 = ApprovedTransition('61-62', 61, 62)
TRANSITION68 = ApprovedTransition('62-68', 62, 68)
TRANSITION83 = ApprovedTransition('68-83', 68, 83)
TRANSITION98 = ApprovedTransition('83-98', 83, 98)
TRANSITION113 = ApprovedTransition('98-113', 98, 113)
TRANSITION128 = ApprovedTransition('113-128', 113, 128)


def resolve_transition(key):
    for transition in (LEGACY, TRANSITION61, TRANSITION62, TRANSITION68, TRANSITION83, TRANSITION98, TRANSITION113, TRANSITION128):
        if key == transition.key:
            return transition
    raise UpdateError('transition_not_approved')


def require_transition(transition):
    if transition is not resolve_transition(transition.key):
        raise UpdateError('transition_not_approved')
    return transition


def approved_pin(revision):
    pin = {59: APPROVED59, 60: APPROVED60, 61: APPROVED61, 62: APPROVED62, 68: APPROVED68, 83: APPROVED83, 98: APPROVED98, 113: APPROVED113, 128: APPROVED128}.get(revision)
    if not pin:
        raise UpdateError(f'target{revision}_pin_pending')
    return pin


class UpdateError(RuntimeError):
    def __init__(self, code, result=None):
        super().__init__(code)
        self.code, self.result = code, result


def save(path, value):
    atomic_bytes(path, (json.dumps(value, indent=2) + '\n').encode('utf-8'))


def require_same_sql7(candidate, baseline):
    sql = lambda tree: {k: v for k, v in tree['server'].items() if k.startswith('database/')}
    if sql(candidate) != sql(baseline):
        raise UpdateError('schema7_sql_must_be_identical')


def require_config_change(previous, selected):
    missing = object()
    changed = {key for key in previous.keys() | selected.keys()
               if previous.get(key, missing) != selected.get(key, missing)}
    if not changed or not changed <= CHANGED_FIELDS:
        raise UpdateError('selected_configuration_differs')
    return changed


@dataclass
class Target60:
    """Historical four-argument API; revision60 remains the default."""
    manifest: Path
    server: Path
    frontend: Path
    expected: dict
    revision: int = 60

    def validate(self):
        pin = approved_pin(self.revision)
        prefix = f'target{self.revision}'
        if self.manifest != ROOT / pin[0] or sha256(checked_path(self.manifest)) != pin[1]:
            raise UpdateError(prefix + '_manifest_not_approved')
        data = json.loads(self.manifest.read_text(encoding='utf-8'))
        if (self.server != ROOT / Path(data['serverDll']).parent or self.frontend != ROOT / data['frontend'] or
                self.expected != data['distributions']):
            raise UpdateError(prefix + '_identity_changed')
        actual = {'server': artifact_manifest(self.server), 'frontend': artifact_manifest(self.frontend)}
        if actual != self.expected or len(actual['server']) != 16 or len(actual['frontend']) != 18:
            raise UpdateError(prefix + '_complete_pair_differs')
        # The historical helper and its schema7 pin stay unchanged.
        baseline = load_historical59().expected
        require_same_sql7(actual, baseline)
        if actual == baseline:
            raise UpdateError(prefix + '_has_no_artifact_change')
        return actual


def load_historical59():
    path = ROOT / APPROVED59[0]
    if sha256(checked_path(path)) != APPROVED59[1]:
        raise UpdateError('source59_manifest_not_approved')
    target = load_target(7)
    if target.manifest_path != path:
        raise UpdateError('source59_manifest_not_approved')
    return target


def load_distribution(revision):
    if revision == 59:
        return load_historical59()
    pin = approved_pin(revision)
    manifest = ROOT / pin[0]
    if sha256(checked_path(manifest)) != pin[1]:
        raise UpdateError(f'target{revision}_manifest_not_approved')
    data = json.loads(manifest.read_text(encoding='utf-8'))
    target = Target60(manifest, ROOT / Path(data['serverDll']).parent, ROOT / data['frontend'], data['distributions'], revision)
    target.validate()
    return target


def load_target60():
    return load_distribution(60)


def load_target61():
    return load_distribution(61)


def transition_pair(transition):
    require_transition(transition)
    source, target = load_distribution(transition.source), load_distribution(transition.target)
    require_same_sql7(target.expected, source.expected)
    if target.expected == source.expected:
        raise UpdateError('transition_has_no_artifact_change')
    return source, target


class Source7(Source4):
    """Reuse only read-only SQL/cluster identity methods; do not widen Source4."""
    def __init__(self, directory, pointer, *, real=False, transition=LEGACY):
        try:
            self.transition = require_transition(transition)
            self.directory, self.pointer = checked_path(directory), checked_path(pointer)
            if (self.directory.parent != ROOT / '.local/labs' or
                    not re.fullmatch(r'manual-qa-rc9-schema7-[0-9a-f]{32}', self.directory.name)):
                raise UpdateError('source7_directory_invalid')
            allowed = ROOT / '.local/qa-rc9/current.json' if real else self.directory / 'artifact7-home/current.json'
            if self.pointer != allowed:
                raise UpdateError('explicit_source7_profile_required')
            self.pointer_bytes = self.pointer.read_bytes()
            if json.loads(self.pointer_bytes) != {'directory': str(self.directory)}:
                raise UpdateError('source7_pointer_differs')
            self.config_bytes = checked_path(self.directory / 'manual-qa.json').read_bytes()
            self.cfg = json.loads(self.config_bytes)
            self.meta = json.loads(checked_path(self.directory / 'lab.json').read_text(encoding='utf-8'))
            c, m = self.cfg, self.meta
            if (c.get('directory') != str(self.directory) or c.get('profile') != 'rc9' or
                    c.get('host') != '127.0.0.1' or m.get('host') != '127.0.0.1' or
                    m.get('path') != str(self.directory) or m.get('postgresql') != '17' or
                    self.directory.name != 'manual-qa-rc9-schema7-' + m.get('id', '!') or
                    c.get('pgPort') != m.get('port') or
                    any(type(c.get(k)) is not int or not 1 <= c[k] <= 65535 for k in ('pgPort', 'webPort')) or
                    c['pgPort'] == c['webPort'] or real and c['webPort'] != 52346):
                raise UpdateError('source7_configuration_invalid')
            rows = [r for r in m['databases'] if r['name'] == c.get('database') and r['label'] == 'manual-qa-rc9']
            if len(rows) != 1:
                raise UpdateError('source7_database_membership_invalid')
            row = rows[0]
            if (not re.fullmatch(r'rc_[0-9a-f]{12}', row['name']) or
                    row['owner'] != 'rc_m_' + row['name'][3:] or row['runtime'] != 'rc_a_' + row['name'][3:]):
                raise UpdateError('source7_database_identity_invalid')
            dbdir = checked_path(self.directory / row['name'])
            cred = json.loads(checked_path(dbdir / 'credentials.json').read_text(encoding='utf-8'))
            self.db = Database(row['name'], row['owner'], cred['ownerPassword'], row['runtime'], cred['runtimePassword'], dbdir)
            if (cred != dict(database=self.db.name, owner=self.db.owner, ownerPassword=self.db.owner_password,
                    runtime=self.db.runtime, runtimePassword=self.db.runtime_password) or
                    c['connection'] != self.db.connection(c['pgPort']) or
                    checked_path(dbdir / 'owner.pgpass').read_text(encoding='utf-8') !=
                    f'127.0.0.1:{c["pgPort"]}:{self.db.name}:{self.db.owner}:{self.db.owner_password}\n'):
                raise UpdateError('source7_private_connection_invalid')
            self.baseline = load_distribution(self.transition.source)
            self.art = checked_path(c.get('artifactDirectory', self.directory))
            if self.art != self.directory and self.art.parent != checked_path(self.directory / 'versions'):
                raise UpdateError('source7_artifact_directory_invalid')
            if (c.get('dllSha256') != self.baseline.expected['server']['RackClick.Server.dll'] or
                    c.get('bundleSha256') != self.baseline.expected['frontend']['app.js'] or
                    self.artifacts() != self.baseline.expected):
                raise UpdateError(f'source7_complete_pair{self.transition.source}_differs')
            checked_path(self.directory / 'data')
            self.pg_bin = toolchain()['postgresql'].parent
            self.admin_passfile = checked_path(self.directory / 'admin.pgpass')
            admin = self.admin_passfile.read_text(encoding='utf-8').splitlines()
            if len(admin) != 1 or not admin[0].startswith(f'127.0.0.1:{c["pgPort"]}:*:rc_lab_admin:') or not admin[0].split(':', 4)[-1]:
                raise UpdateError('source7_admin_passfile_invalid')
            self.inputs = [self.directory / 'lab.json', dbdir / 'credentials.json', dbdir / 'owner.pgpass', self.admin_passfile]
            self.inputs += [self.directory / name for name in PRIVATE_FILES]
            self.hashes = {p.relative_to(self.directory).as_posix(): sha256(checked_path(p)) for p in self.inputs}
            app_stopped(self.directory, c['webPort'])
        except UpdateError:
            raise
        except Exception:
            raise UpdateError('source7_validation_failed') from None

    def unchanged(self, expected_config=None, *, quiet=True):
        if {p.relative_to(self.directory).as_posix(): sha256(checked_path(p)) for p in self.inputs} != self.hashes:
            raise UpdateError('source7_immutable_inputs_changed')
        if self.pointer.read_bytes() != self.pointer_bytes or self.artifacts() != self.baseline.expected:
            raise UpdateError('source7_pointer_or_artifacts_changed')
        expected_config = self.config_bytes if expected_config is None else expected_config
        if checked_path(self.directory / 'manual-qa.json').read_bytes() != expected_config:
            raise UpdateError('source7_configuration_changed')
        if quiet:
            app_stopped(self.directory, self.cfg['webPort'])

    def check_schema7(self):
        self.check_cluster_identity()
        if self.sql('SELECT current_database();SELECT current_user;SHOW port') != f'{self.db.name}\n{self.db.owner}\n{self.cfg["pgPort"]}':
            raise UpdateError('source7_running_identity_differs')
        return history(self.sql, self.art / 'server', 7)


def copy_matches(version, target):
    if {'server': artifact_manifest(version / 'server'), 'frontend': artifact_manifest(version / 'frontend')} != target.expected:
        raise UpdateError('copied_complete_pair_differs')


def verify_ready(directory, cfg, target):
    import http.client
    if not qa_module().ready(directory, cfg):
        raise UpdateError('updated_ready_unconfirmed')
    connection = http.client.HTTPConnection('127.0.0.1', cfg['webPort'], timeout=20)
    try:
        connection.request('GET', '/app.js')
        response = connection.getresponse()
        if response.status != 200 or hashlib.sha256(response.read()).hexdigest() != target.expected['frontend']['app.js']:
            raise UpdateError('served_bundle_differs')
    finally:
        connection.close()


def preview_worker(directory, config, supervise=False, *, real=False, transition=LEGACY):
    require_transition(transition)
    directory, config = checked_path(directory), checked_path(config)
    if (directory.parent != ROOT / '.local/labs' or
            not re.fullmatch(r'manual-qa-rc9-schema7-[0-9a-f]{32}', directory.name) or
            config.name != 'preview-config.json' or config.parent.parent != directory / 'versions' or
            not re.fullmatch('[0-9a-f]{32}', config.parent.name)):
        raise UpdateError('preview_identity_invalid')
    pointer = ROOT / '.local/qa-rc9/current.json' if real else directory / 'artifact7-home/current.json'
    if json.loads(checked_path(pointer).read_bytes()) != {'directory': str(directory)}:
        raise UpdateError('preview_profile_differs')
    cfg = json.loads(config.read_text(encoding='utf-8'))
    original = json.loads(checked_path(directory / 'manual-qa.json').read_text(encoding='utf-8'))
    baseline, target = transition_pair(transition)
    # Revalidate the original source pair in the child process as well.
    original_art = checked_path(original.get('artifactDirectory', directory))
    copy_matches(original_art, baseline)
    copy_matches(config.parent, target)
    if (cfg.get('directory') != str(directory) or cfg.get('profile') != 'rc9' or cfg.get('host') != '127.0.0.1' or
            type(cfg.get('webPort')) is not int or not 1 <= cfg['webPort'] <= 65535 or
            cfg['webPort'] in (original['webPort'], original['pgPort']) or cfg.get('artifactDirectory') != str(config.parent) or
            cfg.get('dllSha256') != target.expected['server']['RackClick.Server.dll'] or
            cfg.get('bundleSha256') != target.expected['frontend']['app.js'] or
            {k:v for k,v in cfg.items() if k not in CHANGED_FIELDS | {'webPort'}} !=
            {k:v for k,v in original.items() if k not in CHANGED_FIELDS | {'webPort'}}):
        raise UpdateError('preview_configuration_differs')
    if supervise:
        with (directory / 'artifact7-worker.log').open('ab') as output:
            command = [sys.executable, '-B', str(Path(__file__).resolve()), '_worker',
                '--source', str(directory), '--config', str(config), '--transition', transition.key]
            if real:
                command.append('--real-restored')
            result = run_isolated(command, cwd=ROOT, stdout=output, stderr=output)
        if result.returncode:
            raise UpdateError('preview_worker_failed')
    else:
        qa_module().serve(directory, cfg)


def start_native(directory, cfg, on_launch, on_child, config=None, *, real=False, transition=LEGACY):
    """Prechecks precede ownership; callback records the actual launch attempt.

    Stable worker is the unchanged historical JobObject supervisor. Preview uses
    the same JobObject API with a separate private config, never rewriting the
    stable manual-qa.json merely to select a temporary port.
    """
    require_transition(transition)
    if pg_running(directory):
        raise UpdateError('launch_pg_already_active')
    try:
        app_stopped(directory, cfg['webPort'])
    except Exception:
        raise UpdateError('launch_application_already_active') from None
    if config is None:
        command = [sys.executable, '-B', str(ROOT / 'tools/windows/qa_schema_switch.py'), '_supervise',
            '--profile', 'rc9', '--source', str(directory)]
    else:
        command = [sys.executable, '-B', str(Path(__file__).resolve()), '_supervise',
            '--source', str(directory), '--config', str(config), '--transition', transition.key]
        if real:
            command.append('--real-restored')
    with (directory / 'artifact7-supervisor.log').open('ab') as output:
        on_launch()
        child = subprocess.Popen(command, cwd=ROOT, stdout=output,
            stderr=output, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
        on_child(child)
    try:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise UpdateError('native_start_failed')
            if qa_module().ready(directory, cfg):
                return child
            time.sleep(.1)
        raise UpdateError('native_start_timeout')
    except Exception:
        (directory / 'stop.request').touch()
        try:
            child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            child.terminate(); child.wait(timeout=15)
        raise UpdateError('native_start_unconfirmed') from None


@dataclass
class Result:
    source: object
    version: Path
    journal: Path
    state: str = 'validated'


def update(directory, pointer, *, real=False, hook=None, transition=LEGACY):
    require_transition(transition)
    initial = Source7(directory, pointer, real=real, transition=transition)
    if initial.pg_running():
        raise UpdateError('source7_pg_already_active')
    _, target = transition_pair(transition)
    with profile_lock(initial.pointer):
        source = Source7(directory, pointer, real=real, transition=transition)
        if source.hashes != initial.hashes or source.config_bytes != initial.config_bytes or source.pointer_bytes != initial.pointer_bytes:
            raise UpdateError('source7_changed_before_lock')
        if source.pg_running():
            raise UpdateError('source7_pg_already_active')
        version = checked_path(source.directory / 'versions' / uuid.uuid4().hex)
        journal = source.directory / ('artifact7-update-' + uuid.uuid4().hex + '.json')
        result = Result(source, version, journal)
        state = dict(state='validated', schema=7, transition=transition.key, activated=False, targetManifestSha256=sha256(target.manifest),
            sourceInputHashes=source.hashes, pointerSha256=sha256(source.pointer), previousConfigSha256=sha256(source.directory / 'manual-qa.json'))
        baseline = before = old_history = None
        selected = False
        owned = False
        active_cfg = source.cfg
        selected_bytes = source.config_bytes
        version_inputs = None
        process = None

        def checkpoint(name):
            result.state = state['state'] = name
            save(journal, state)
            if hook:
                hook(name, result)

        def stop_owned():
            nonlocal owned, process
            if owned:
                stop_application(source.directory, active_cfg)
                if process:
                    process.wait(timeout=30)
                if pg_running(source.directory):
                    raise UpdateError('owned_pg_stop_unconfirmed')
                app_stopped(source.directory, active_cfg['webPort'])
                owned = False
                process = None
                state['ownedLaunch']['phase'] = 'stopped-confirmed'

        def start_pg():
            nonlocal owned
            if pg_running(source.directory):
                raise UpdateError('pg_became_active_outside_update')
            owned = True  # pg_ctl may start and then fail/timeout
            state['ownedLaunch'] = {'kind': 'pg-control', 'phase': 'attempted', 'dataDirectory': str(source.directory / 'data')}
            qa_module().control(source.directory, 'start')
            source.check_cluster_identity()

        def launch_application(cfg, preview_config=None):
            nonlocal owned, process
            def on_launch():
                nonlocal owned
                owned = True
                state['ownedLaunch'] = {'kind': 'job-supervisor', 'phase': 'attempted', 'dataDirectory': str(source.directory / 'data')}
            def on_child(child):
                nonlocal process
                process = child
                state['ownedLaunch'].update(phase='child-created', supervisorPid=child.pid)
            # A pre-existing PG/app rejection calls neither callback: it cannot
            # grant this update ownership merely because we intended a start.
            try:
                return start_native(source.directory, cfg, on_launch, on_child, preview_config, real=real, transition=transition)
            except Exception as error:
                if not owned:
                    state['launchRejectedBeforeCreation'] = getattr(error, 'code', 'prelaunch_check_failed')
                raise

        def verify_readonly():
            if baseline is None:
                raise UpdateError('activity_reference_missing')
            require_unchanged_activity(source.directory, source.cfg, baseline)
            if snapshot(source.sql) != before or source.check_schema7() != old_history:
                raise UpdateError('rows_or_history_changed')
            require_unchanged_activity(source.directory, source.cfg, baseline)

        def verify_version():
            if version_inputs is None:
                raise UpdateError('version_inputs_missing')
            copy_matches(version, target)
            if {name: sha256(checked_path(version / name)) for name in version_inputs} != version_inputs:
                raise UpdateError('version_private_inputs_changed')

        try:
            checkpoint('validated')
            start_pg()
            old_history = source.check_schema7()
            before = snapshot(source.sql)
            baseline = activity_watermark(source.directory, source.cfg)
            state.update(history=old_history, rows=before, activityBaseline=baseline)
            stop_owned()
            version.mkdir(parents=True, exist_ok=False)
            for name in ('server', 'frontend'):
                shutil.copytree(getattr(target, name), version / name)
            new_cfg = dict(source.cfg, artifactDirectory=str(version), dllSha256=target.expected['server']['RackClick.Server.dll'],
                bundleSha256=target.expected['frontend']['app.js'])
            require_config_change(source.cfg, new_cfg)
            selected_bytes = (json.dumps(new_cfg, indent=2) + '\n').encode('utf-8')
            atomic_bytes(version / 'previous-config.json', source.config_bytes)
            preview_cfg = dict(new_cfg, webPort=free_port())
            while preview_cfg['webPort'] in (source.cfg['webPort'], source.cfg['pgPort']):
                preview_cfg['webPort'] = free_port()
            save(version / 'preview-config.json', preview_cfg)
            version_inputs = {name: sha256(version / name) for name in ('previous-config.json', 'preview-config.json')}
            verify_version(); target.validate(); source.unchanged()
            state.update(versionDirectory=str(version), selectedConfigSha256=hashlib.sha256(selected_bytes).hexdigest())
            checkpoint('prepared')
            active_cfg = preview_cfg
            process = launch_application(preview_cfg, version / 'preview-config.json')
            verify_ready(source.directory, preview_cfg, target)
            verify_readonly()
            stop_owned()
            active_cfg = source.cfg
            source.unchanged(); target.validate(); verify_version()
            checkpoint('before_config')
            source.unchanged()
            atomic_bytes(source.directory / 'manual-qa.json', selected_bytes)
            selected = True
            checkpoint('after_config')
            active_cfg = new_cfg
            process = launch_application(new_cfg)
            checkpoint('after_start')
            verify_ready(source.directory, new_cfg, target)
            verify_readonly()
            source.unchanged(selected_bytes, quiet=False); target.validate(); verify_version()
            stop_owned()
            # Catch activity between the last live read and confirmed shutdown.
            start_pg()
            try:
                verify_readonly()
            finally:
                stop_owned()
            source.unchanged(selected_bytes)
            if pg_running(source.directory):
                raise UpdateError('final_pg_stop_unconfirmed')
            state.update(activated=True, leftRunning=False, databaseReconstructed=False, pointerUnchanged=True, stopConfirmed=True)
            checkpoint('committed')
            return result
        except Exception as error:
            state['failureCode'] = getattr(error, 'code', 'update_internal_failure')
            recovered = False
            try:
                stop_owned()
                if pg_running(source.directory):
                    raise UpdateError('foreign_or_uncertain_pg_running')
                source.unchanged(selected_bytes if selected else source.config_bytes)
                target.validate()
                if version_inputs is not None:
                    verify_version()
                if baseline is not None:
                    start_pg()
                    try:
                        verify_readonly()
                    finally:
                        stop_owned()
                elif selected:
                    raise UpdateError('activity_reference_missing')
                if selected:
                    atomic_bytes(source.directory / 'manual-qa.json', source.config_bytes)
                source.unchanged()
                recovered = True
            except Exception as blocker:
                state['recoveryBlocker'] = getattr(blocker, 'code', 'recovery_verification_uncertain')
                if owned:
                    try:
                        stop_owned()
                    except Exception:
                        pass
            quiet = False
            try:
                quiet = not pg_running(source.directory)
                app_stopped(source.directory, source.cfg['webPort'])
            except Exception:
                quiet = False
            if owned or not quiet:
                recovered = False
            state.update(activated=False, stopConfirmed=quiet and not owned)
            result.state = state['state'] = 'rolled_back' if recovered else 'recovery_required'
            try:
                save(journal, state)
            except Exception:
                raise UpdateError('recovery_journal_unconfirmed', result) from None
            raise UpdateError(result.state, result) from None


def main(default_transition=LEGACY):
    require_transition(default_transition)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('update', '_supervise', '_worker'))
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--pointer', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--real-restored', action='store_true')
    parser.add_argument('--transition', choices=(LEGACY.key, TRANSITION61.key, TRANSITION62.key, TRANSITION68.key, TRANSITION83.key, TRANSITION98.key, TRANSITION113.key, TRANSITION128.key), default=default_transition.key)
    args = parser.parse_args()
    try:
        transition = resolve_transition(args.transition)
        if default_transition is not LEGACY and transition is not default_transition:
            raise UpdateError('entrypoint_transition_mismatch')
        if args.action == 'update':
            if args.pointer is None:
                raise UpdateError('explicit_pointer_required')
            result = update(args.source, args.pointer, real=args.real_restored, transition=transition)
            print(json.dumps({'state': result.state, 'schema': 7, 'leftRunning': False, 'databaseReconstructed': False}))
        else:
            if args.config is None:
                raise UpdateError('preview_config_required')
            preview_worker(args.source, args.config, args.action == '_supervise', real=args.real_restored, transition=transition)
        return 0
    except Exception as error:
        print(json.dumps({'state': getattr(error, 'code', 'update_validation_failed'), 'activated': False}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
