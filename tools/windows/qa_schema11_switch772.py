"""Stopped, closed 592/schema10 ->772/schema11 copy/selection and guarded rollback.

Real operations require the coordinator's separate operational GO. All launches
are private and owned; no authentication, technical application DML or deletion.
"""
from dataclasses import dataclass
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import NO_WINDOW, free_port, toolchain
from pg_lab_recovery import sha256
from qa_schema5_candidate import checked_path
from qa_schema5_switch import atomic_bytes
from qa_schema6_source import app_stopped
from qa_schema_switch import profile_lock, qa_module, pg_running, stop_application, read_owner
from windows_job import run_isolated
from qa_schema11_source772 import Source592, Schema11Error, load_target
from qa_schema11_candidate772 import (prepare, load_prepared, verify_source, save,
                                    PREPARED, validate_seal)


@dataclass
class Result772:
    source: object
    candidate: object
    journal: Path
    state: str = 'validated'


def start_private_pg772(directory):
    """Temporary option for an already validated, quiet, operation-owned start.

    Never edits postgresql.conf. Normal Qa-Local start gets its normal settings.
    Wraparound/other activity may still advance XID: existing guards must reject.
    """
    directory = checked_path(directory)
    with (directory / 'schema11-control-private.log').open('ab') as output:
        subprocess.run([str(toolchain()['postgresql'].parent / 'pg_ctl.exe'), 'start',
            '-D', str(directory / 'data'), '-w', '-t', '60', '-l', str(directory / 'postgres.log'),
            '-o', '-c autovacuum=off'], stdout=output, stderr=output, stdin=subprocess.DEVNULL,
            creationflags=NO_WINDOW, timeout=90, check=True)


def require_temporary_pg_mode(directory, cfg):
    if read_owner(directory, cfg, 'SHOW autovacuum') != 'off':
        raise Schema11Error('runtime772_temporary_autovacuum_mode_unconfirmed')


class OwnedRuntime:
    """A failed launch grants ownership only after this operation attempts it."""
    def __init__(self, directory, cfg):
        self.directory, self.cfg = directory, cfg
        self.owned = False
        self.process = None
        self.launch = None

    def quiet(self):
        app_stopped(self.directory, self.cfg['webPort'])
        if pg_running(self.directory):
            raise Schema11Error('runtime772_foreign_or_uncertain_pg_active')

    def start_pg(self):
        self.quiet()
        self.owned = True  # pg_ctl can start PG, then report failure/timeout.
        self.launch = {'kind': 'pg-control', 'phase': 'attempted'}
        start_private_pg772(self.directory)
        require_temporary_pg_mode(self.directory, self.cfg)

    def start_app(self, *, preview=False):
        self.quiet()  # Reject pre-existing PG/app WITHOUT granting ownership.
        command = [sys.executable, '-B', str(ROOT / 'tools/windows/qa_schema11_update772.py'),
                   '_supervise', '--candidate', str(self.directory)]
        if preview:
            command.append('--preview')
        with (self.directory / 'schema11-supervisor-private.log').open('ab') as output:
            self.launch = {'kind': 'job-supervisor', 'phase': 'attempted'}
            self.owned = True
            try:
                self.process = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=output,
                    stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
            except Exception:
                # Popen did not create a child; it cannot own a foreign start.
                self.owned = False
                raise
            self.launch.update(phase='child-created', supervisorPid=self.process.pid)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise Schema11Error('runtime772_supervisor_start_failed')
            if qa_module().ready(self.directory, self.cfg):
                require_temporary_pg_mode(self.directory, self.cfg)
                verify_ready(self.directory, self.cfg)
                return
            time.sleep(.1)
        raise Schema11Error('runtime772_supervisor_start_timeout')

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


def verify_ready(directory, cfg):
    if not qa_module().ready(directory, cfg):
        raise Schema11Error('candidate772_readiness_unconfirmed')
    connection = http.client.HTTPConnection('127.0.0.1', cfg['webPort'], timeout=15)
    try:
        connection.request('GET', '/health/ready')
        response = connection.getresponse()
        if response.status != 200 or json.loads(response.read()) != {'status': 'ready', 'schemaVersion': 11}:
            raise Schema11Error('candidate772_readiness_schema_differs')
        connection.request('GET', '/app.js')
        response = connection.getresponse()
        if response.status != 200 or hashlib.sha256(response.read()).hexdigest() != cfg['bundleSha256']:
            raise Schema11Error('candidate772_served_bundle_differs')
    finally:
        connection.close()


def candidate_source(candidate, pointer, *, real=False, selected=False):
    source = Source592(Path(candidate.record['sourceDirectory']), pointer, real=real,
                       selected=candidate.directory if selected else None)
    if (str(pointer) != candidate.record['sourcePointer'] or source.hashes != candidate.record['sourceInputHashes'] or
            source.config_bytes != (candidate.directory / 'source-manual-qa.json').read_bytes()):
        raise Schema11Error('candidate772_source_binding_changed')
    if not selected and source.pointer_bytes.decode('utf-8') != candidate.record['sourcePointerBytes']:
        raise Schema11Error('candidate772_original_pointer_changed')
    return source


def prepare_operation(directory, pointer, *, real=False, hook=None):
    initial = Source592(directory, pointer, real=real)
    if initial.pg_running():
        raise Schema11Error('source592_pg_already_active')
    target = load_target()
    with profile_lock(initial.pointer):
        source = Source592(directory, pointer, real=real)
        if source.hashes != initial.hashes or source.pointer_bytes != initial.pointer_bytes:
            raise Schema11Error('source592_changed_before_lock')
        runtime = OwnedRuntime(source.directory, source.cfg)
        journal = source.directory / ('schema11-prepare-' + uuid.uuid4().hex + '.json')
        result = Result772(source, None, journal)
        state = dict(state='validated', sourceSchema=10, candidateSchema=11, activated=False,
                     sourceInputHashes=source.hashes, targetManifestSha256=sha256(target.manifest))
        try:
            save(journal, state)
            if hook:
                hook('validated', result)
            source.unchanged(); target.validate()
            runtime.start_pg()
            candidate = result.candidate = prepare(source, target)
            runtime.stop()
            candidate.validate_static()
            source.unchanged(); runtime.quiet()
            state.update(state='prepared', candidateDirectory=str(candidate.directory), leftRunning=False,
                         sourcePgStopConfirmed=True, candidatePgStopConfirmed=not pg_running(candidate.directory))
            if not state['candidatePgStopConfirmed']:
                raise Schema11Error('prepared772_stop_unconfirmed')
            save(journal, state); result.state = 'prepared'
            return result
        except Exception as error:
            if result.candidate is None and getattr(error, 'result', None) is not None:
                result.candidate = error.result
            state['failureCode'] = getattr(error, 'code', 'prepare772_internal_failure')
            quiet = False
            candidate_quiet = result.candidate is None
            try:
                runtime.stop(); runtime.quiet(); source.unchanged()
                quiet = True
            except Exception as blocker:
                state['recoveryBlocker'] = getattr(blocker, 'code', 'source592_stop_or_identity_uncertain')
            if result.candidate is not None:
                try:
                    result.candidate.close()
                    cfg = result.candidate.cfg or source.cfg
                    OwnedRuntime(result.candidate.directory, cfg).quiet()
                    candidate_quiet = True
                except Exception:
                    state['candidateRecoveryBlocker'] = 'candidate772_failed_stop_unconfirmed'
            result.state = state['state'] = 'preparation_failed' if quiet and candidate_quiet else 'recovery_required'
            state.update(activated=None, leftRunning=False if quiet and candidate_quiet else None)
            state['sourcePgStopConfirmed'] = quiet and not runtime.owned
            state['candidatePgStopConfirmed'] = candidate_quiet
            if result.candidate:
                state['candidateDirectory'] = str(result.candidate.directory)
            try:
                save(journal, state)
            except Exception:
                raise Schema11Error('prepare772_journal_unconfirmed', result) from None
            raise Schema11Error(result.state, result) from None


def validate_operation(directory, pointer, candidate_directory, *, real=False, selected=False):
    """Static validation only; no launch, HTTP, login or SQL. Not a live DB test."""
    candidate = load_prepared(candidate_directory)
    if checked_path(directory) != checked_path(candidate.record['sourceDirectory']):
        raise Schema11Error('explicit_source592_differs')
    with profile_lock(checked_path(pointer)):
        source = candidate_source(candidate, checked_path(pointer), real=real, selected=selected)
        OwnedRuntime(source.directory, source.cfg).quiet()
        OwnedRuntime(candidate.directory, candidate.cfg).quiet()
        candidate.validate_static()
        return candidate


def _verify_source_stopped(source, candidate, runtime):
    runtime.start_pg()
    try:
        verify_source(source, candidate.record)
    finally:
        runtime.stop()


def _verify_candidate_stopped(candidate, runtime):
    runtime.start_pg()
    try:
        candidate.verify_rows_and_activity()
    finally:
        runtime.stop()


def _guarded_restore(source, candidate, source_runtime, target_runtime, selected_bytes):
    """Restore only exact original10 pointer, with both branches unchanged/quiet."""
    target_runtime.stop(); source_runtime.stop()
    target_runtime.quiet(); source_runtime.quiet()
    source.unchanged(pointer=False); candidate.validate_static()
    expected = selected_bytes if selected_bytes is not None else candidate.record['sourcePointerBytes'].encode('utf-8')
    if source.pointer.read_bytes() != expected:
        raise Schema11Error('rollback772_pointer_identity_changed')
    _verify_source_stopped(source, candidate, source_runtime)
    _verify_candidate_stopped(candidate, target_runtime)
    source.unchanged(pointer=False); candidate.validate_static()
    source_runtime.quiet(); target_runtime.quiet()
    if source.pointer.read_bytes() != expected:
        raise Schema11Error('rollback772_pointer_changed_before_restore')
    if selected_bytes is not None:
        atomic_bytes(source.pointer, candidate.record['sourcePointerBytes'].encode('utf-8'))


def activate(directory, pointer, candidate_directory, *, real=False, hook=None):
    candidate = load_prepared(candidate_directory)
    if checked_path(directory) != checked_path(candidate.record['sourceDirectory']):
        raise Schema11Error('explicit_source592_differs')
    pointer = checked_path(pointer)
    with profile_lock(pointer):
        source = candidate_source(candidate, pointer, real=real)
        source_runtime = OwnedRuntime(source.directory, source.cfg)
        target_runtime = OwnedRuntime(candidate.directory, candidate.cfg)
        source_runtime.quiet(); target_runtime.quiet()
        journal = candidate.directory / ('schema11-activation-' + uuid.uuid4().hex + '.json')
        result = Result772(source, candidate, journal)
        state = dict(state='validated', activated=False, sourceSchema=10, candidateSchema=11,
            preparedSha256=sha256(candidate.directory / PREPARED), targetManifestSha256=sha256(candidate.target.manifest),
            sourceActivityBaseline=candidate.record['sourceActivityBaseline'],
            candidateActivityBaseline=candidate.record['candidateActivityBaseline'])
        selected_bytes = None

        def checkpoint(name):
            result.state = state['state'] = name
            state['sourceLaunch'] = source_runtime.launch
            state['targetLaunch'] = target_runtime.launch
            save(journal, state)
            if hook:
                hook(name, result)

        try:
            checkpoint('validated')
            _verify_source_stopped(source, candidate, source_runtime)
            _verify_candidate_stopped(candidate, target_runtime)
            checkpoint('prepared')
            preview_cfg = preview_configuration(candidate)
            target_runtime.cfg = preview_cfg
            target_runtime.start_app(preview=True)
            candidate.verify_rows_and_activity()
            target_runtime.stop()
            target_runtime.cfg = candidate.cfg
            _verify_candidate_stopped(candidate, target_runtime)
            source.unchanged(); candidate.validate_static()
            checkpoint('before_pointer')
            source.unchanged(); source_runtime.quiet(); target_runtime.quiet(); candidate.validate_static()
            content = (json.dumps({'directory': str(candidate.directory)}) + '\n').encode('utf-8')
            atomic_bytes(pointer, content)
            selected_bytes = content
            checkpoint('after_pointer')
            target_runtime.start_app()
            checkpoint('after_start')
            candidate.verify_rows_and_activity(); candidate.validate_static()
            if pointer.read_bytes() != selected_bytes:
                raise Schema11Error('candidate772_pointer_changed_after_start')
            target_runtime.stop()
            # Check after confirmed shutdown as well as during readiness.
            _verify_candidate_stopped(candidate, target_runtime)
            source.unchanged(pointer=False); source_runtime.quiet(); target_runtime.quiet()
            if pointer.read_bytes() != selected_bytes:
                raise Schema11Error('candidate772_final_pointer_changed')
            state.update(activated=True, leftRunning=False, sourcePreserved=True,
                         sourcePgStopConfirmed=True, candidatePgStopConfirmed=True)
            checkpoint('committed')
            return result
        except Exception as error:
            state['failureCode'] = getattr(error, 'code', 'activation772_internal_failure')
            recovered = False
            try:
                _guarded_restore(source, candidate, source_runtime, target_runtime, selected_bytes)
                recovered = True
            except Exception as blocker:
                state['recoveryBlocker'] = getattr(blocker, 'code', 'rollback772_verification_uncertain')
                for runtime in (target_runtime, source_runtime):
                    try:
                        runtime.stop()
                    except Exception:
                        pass
            result.state = state['state'] = 'rolled_back' if recovered else 'recovery_required'
            state.update(activated=None, leftRunning=None,
                         sourceLaunch=source_runtime.launch, targetLaunch=target_runtime.launch)
            for label, runtime in (('source', source_runtime), ('candidate', target_runtime)):
                try:
                    runtime.quiet(); state[label + 'PgStopConfirmed'] = not runtime.owned
                except Exception:
                    state[label + 'PgStopConfirmed'] = False
            if not all(state[k] for k in ('sourcePgStopConfirmed', 'candidatePgStopConfirmed')):
                result.state = state['state'] = 'recovery_required'
            else:
                state['leftRunning'] = False
            state['selectedSchema'] = observed_selection(source, candidate)
            try:
                save(journal, state)
            except Exception:
                raise Schema11Error('activation772_journal_unconfirmed', result) from None
            raise Schema11Error(result.state, result) from None


def rollback(directory, pointer, candidate_directory, *, real=False):
    """Explicit rollback after quiet activation; refuses any later activity."""
    candidate = load_prepared(candidate_directory)
    if checked_path(directory) != checked_path(candidate.record['sourceDirectory']):
        raise Schema11Error('explicit_source592_differs')
    pointer = checked_path(pointer)
    with profile_lock(pointer):
        source = candidate_source(candidate, pointer, real=real, selected=True)
        source_runtime, target_runtime = OwnedRuntime(source.directory, source.cfg), OwnedRuntime(candidate.directory, candidate.cfg)
        journal = candidate.directory / ('schema11-rollback-' + uuid.uuid4().hex + '.json')
        result = Result772(source, candidate, journal)
        state = dict(state='validated', activated=None, sourceSchema=10, candidateSchema=11)
        save(journal, state)
        try:
            _guarded_restore(source, candidate, source_runtime, target_runtime, source.pointer_bytes)
            result.state = state['state'] = 'rolled_back'
            state.update(sourcePgStopConfirmed=True, candidatePgStopConfirmed=True, leftRunning=False, selectedSchema=10)
            save(journal, state)
            return result
        except Exception as error:
            state['recoveryBlocker'] = getattr(error, 'code', 'rollback772_verification_uncertain')
            for runtime in (target_runtime, source_runtime):
                try:
                    runtime.stop()
                except Exception:
                    pass
            result.state = state['state'] = 'recovery_required'
            state.update(selectedSchema=observed_selection(source, candidate), leftRunning=None)
            for label, runtime in (('source', source_runtime), ('candidate', target_runtime)):
                try:
                    runtime.quiet(); state[label + 'PgStopConfirmed'] = not runtime.owned
                except Exception:
                    state[label + 'PgStopConfirmed'] = False
            if all(state[k] for k in ('sourcePgStopConfirmed', 'candidatePgStopConfirmed')):
                state['leftRunning'] = False
            try:
                save(journal, state)
            except Exception:
                raise Schema11Error('rollback772_journal_unconfirmed', result) from None
            raise Schema11Error('recovery_required', result) from None


def observed_selection(source, candidate):
    try:
        value = source.pointer.read_bytes()
        if value == candidate.record['sourcePointerBytes'].encode('utf-8'):
            return 10
        if json.loads(value) == {'directory': str(candidate.directory)}:
            return 11
    except Exception:
        pass
    return None


def preview_configuration(candidate):
    path = candidate.directory / 'preview-manual-qa.json'
    source_cfg = json.loads((candidate.directory / 'source-manual-qa.json').read_bytes())
    forbidden = (candidate.cfg['webPort'], candidate.cfg['pgPort'], source_cfg['pgPort'])
    if path.exists():
        cfg = json.loads(checked_path(path).read_bytes())
        if (set(cfg) != set(candidate.cfg) or
                {k: v for k, v in cfg.items() if k != 'webPort'} != {k: v for k, v in candidate.cfg.items() if k != 'webPort'} or
                type(cfg.get('webPort')) is not int or not 1 <= cfg['webPort'] <= 65535 or
                cfg['webPort'] in forbidden):
            raise Schema11Error('candidate772_preview_configuration_changed')
        return cfg
    cfg = dict(candidate.cfg, webPort=free_port())
    while cfg['webPort'] in forbidden:
        cfg['webPort'] = free_port()
    save(path, cfg)
    return cfg


def worker(candidate_directory, *, supervise=False, preview=False):
    candidate = load_prepared(candidate_directory)
    cfg = preview_configuration(candidate) if preview else candidate.cfg
    if supervise:
        command = [sys.executable, '-B', str(ROOT / 'tools/windows/qa_schema11_update772.py'),
                   '_worker', '--candidate', str(candidate.directory)]
        if preview:
            command.append('--preview')
        with (candidate.directory / 'schema11-worker-private.log').open('ab') as output:
            done = run_isolated(command, cwd=ROOT, stdout=output, stderr=output)
        if done.returncode:
            raise Schema11Error('candidate772_worker_failed')
    else:
        qa = qa_module()
        normal_control = qa.control
        def private_control(directory, action):
            if action == 'start':
                start_private_pg772(directory)
                require_temporary_pg_mode(directory, cfg)
            else:
                normal_control(directory, action)
        # This freshly loaded module instance belongs only to the worker. The
        # historical file and all normal QA starts remain unchanged.
        qa.control = private_control
        qa.serve(candidate.directory, cfg)
