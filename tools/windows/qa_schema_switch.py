"""Explicit RC9 lab schema switch with the public QA command byte lock.

No implicit preparation, external dumps, file-only rollback or foreign process
termination. The CLI requires an existing source and pointer; fixtures use a
private pointer, never the real QA profile. Raw logs/journals stay private.
"""
import argparse
import importlib.util
import json
import msvcrt
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import Database, NO_WINDOW, free_port, toolchain
from qa_schema_candidate import (prepare, checked_path, artifacts, sha256, save, snapshot,
    SOURCE_DLL, SOURCE_BUNDLE, CANDIDATE_DLL, CANDIDATE_BUNDLE, PRIVATE_FILES, CandidateError)
from windows_job import run_isolated


def qa_module():
    spec = importlib.util.spec_from_file_location('explicit_qa_switch', ROOT / 'tools/windows/Qa-Local.py')
    qa = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qa)
    return qa


class SwitchError(RuntimeError):
    def __init__(self, code, result=None):
        super().__init__(code)
        self.code, self.result = code, result


@dataclass
class SwitchResult:
    source: Path
    candidate: object
    journal: Path
    state: str


@contextmanager
def profile_lock(pointer):
    lock_path = checked_path(Path(pointer).parent / 'control.lock')
    with lock_path.open('a+b') as lock:
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise SwitchError('profile_busy') from None
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def validate(source, pointer):
    """Read-only identity validation before any stop request or cluster control."""
    try:
        source, pointer = checked_path(source), checked_path(pointer)
        labs = (ROOT / '.local/labs').resolve()
        if source.parent != labs or not source.name.startswith('manual-qa-rc9-'):
            raise SwitchError('source_identity_invalid')
        home = pointer.parent
        if (pointer.name != 'current.json' or not pointer.is_file() or
                home != (ROOT / '.local/qa-rc9').resolve() and not
                (home.parent == source and home.name == 'switch-home')):
            raise SwitchError('pointer_identity_invalid')
        pointer_bytes = pointer.read_bytes()
        if json.loads(pointer_bytes)['directory'] != str(source):
            raise SwitchError('pointer_source_mismatch')
        cfg_path = checked_path(source / 'manual-qa.json')
        cfg_bytes = cfg_path.read_bytes()
        cfg = json.loads(cfg_bytes)
        meta = json.loads(checked_path(source / 'lab.json').read_text(encoding='utf-8'))
        if (cfg['directory'] != str(source) or cfg.get('profile') != 'rc9' or
                cfg['host'] != '127.0.0.1' or meta['host'] != '127.0.0.1' or
                meta['path'] != str(source) or meta['postgresql'] != '17' or
                source.name != 'manual-qa-rc9-' + meta['id'] or cfg['pgPort'] != meta['port'] or
                any(type(cfg.get(k)) is not int or not 1 <= cfg[k] <= 65535 for k in ('webPort', 'pgPort')) or
                cfg['webPort'] == cfg['pgPort'] or cfg['dllSha256'] != SOURCE_DLL or cfg['bundleSha256'] != SOURCE_BUNDLE):
            raise SwitchError('source_identity_invalid')
        rows = [r for r in meta['databases'] if r['name'] == cfg['database'] and r['label'] == 'manual-qa-rc9']
        if len(rows) != 1:
            raise SwitchError('source_database_invalid')
        row = rows[0]
        import re
        if (not re.fullmatch(r'rc_[0-9a-f]{12}', row['name']) or
                row['owner'] != 'rc_m_' + row['name'][3:] or row['runtime'] != 'rc_a_' + row['name'][3:]):
            raise SwitchError('source_database_invalid')
        db_dir = checked_path(source / row['name'])
        cred = json.loads(checked_path(db_dir / 'credentials.json').read_text(encoding='utf-8'))
        db = Database(row['name'], row['owner'], cred['ownerPassword'], row['runtime'], cred['runtimePassword'], db_dir)
        if (cred != dict(database=db.name, owner=db.owner, ownerPassword=db.owner_password,
                runtime=db.runtime, runtimePassword=db.runtime_password) or cfg['connection'] != db.connection(cfg['pgPort']) or
                checked_path(db_dir / 'owner.pgpass').read_text(encoding='utf-8') !=
                f'127.0.0.1:{cfg["pgPort"]}:{db.name}:{db.owner}:{db.owner_password}\n'):
            raise SwitchError('source_credentials_invalid')
        for name in PRIVATE_FILES:
            if not checked_path(source / name).is_file():
                raise SwitchError('source_private_file_missing')
        checked_path(source / 'data')
        for name in ('server.lock', 'ready.json', 'stop.request'):
            checked_path(source / name)
        art = checked_path(cfg.get('artifactDirectory', source))
        if art != source and art.parent != checked_path(source / 'versions'):
            raise SwitchError('source_artifact_path_invalid')
        artifact_hashes = artifacts(art / 'server', art / 'frontend', SOURCE_DLL, SOURCE_BUNDLE)
        return source, pointer, cfg, cfg_bytes, pointer_bytes, artifact_hashes
    except SwitchError:
        raise
    except Exception:
        raise SwitchError('source_validation_failed') from None


def pg_running(directory):
    pg = toolchain()['postgresql'].parent / 'pg_ctl.exe'
    code = subprocess.run([str(pg), 'status', '-D', str(directory / 'data')],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW, timeout=15).returncode
    if code not in (0, 3):
        raise SwitchError('cluster_status_uncertain')
    return code == 0


def stop_application(directory, cfg, timeout=90):
    qa = qa_module()
    if qa.running(directory):
        (directory / 'stop.request').touch()
        deadline = time.monotonic() + timeout
        while qa.running(directory):
            if time.monotonic() >= deadline:
                raise SwitchError('application_stop_unconfirmed')
            time.sleep(.1)
    with socket.socket() as sock:
        sock.settimeout(.5)
        if sock.connect_ex(('127.0.0.1', cfg['webPort'])) == 0:
            raise SwitchError('web_port_still_occupied')
    if pg_running(directory):
        qa.control(directory, 'stop')
    if pg_running(directory):
        raise SwitchError('cluster_stop_unconfirmed')


def start_supervisor(directory, cfg, timeout=90):
    qa = qa_module()
    if qa.running(directory) or pg_running(directory):
        raise SwitchError('application_already_running')
    with (directory / 'switch-supervisor.log').open('ab') as output:
        child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '_supervise',
            '--profile', 'rc9', '--source', str(directory)], cwd=ROOT,
            stdout=output, stderr=output, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise SwitchError('supervisor_start_failed')
            if qa.ready(directory, cfg):
                return child
            time.sleep(.1)
        raise SwitchError('supervisor_start_timeout')
    except Exception:
        (directory / 'stop.request').touch()
        try:
            child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            # This process handle was created by this call; its private job owns
            # only the new worker/descendants. No PID/name-based selection.
            child.terminate()
            child.wait(timeout=15)
        raise SwitchError('supervisor_start_failed') from None


def read_owner(directory, cfg, command):
    meta = json.loads((directory / 'lab.json').read_text(encoding='utf-8'))
    row = next(r for r in meta['databases'] if r['name'] == cfg['database'])
    env = dict(os.environ, PGCLIENTENCODING='UTF8', PGPASSFILE=str(directory / row['name'] / 'owner.pgpass'))
    result = subprocess.run([str(toolchain()['postgresql'].parent / 'psql.exe'), '-X', '-q', '-w', '-At',
        '-v', 'ON_ERROR_STOP=1', '-h', '127.0.0.1', '-p', str(cfg['pgPort']), '-U', row['owner'], '-d', row['name']],
        input='BEGIN READ ONLY;\n' + command + ';\nCOMMIT;', text=True, encoding='utf-8', capture_output=True,
        env=env, creationflags=NO_WINDOW, timeout=60)
    if result.returncode:
        raise SwitchError('snapshot_read_failed')
    return result.stdout.strip()


def _safe_activity(value):
    if (not isinstance(value, dict) or not isinstance(value.get('xmax'), str) or
            not value['xmax'].isascii() or not value['xmax'].isdigit() or
            not 0 < int(value['xmax']) < 2 ** 64):
        raise SwitchError('candidate_activity_unconfirmed')
    if value.get('xip') != []:
        raise SwitchError('candidate_activity_in_progress')
    return {'xmax': str(int(value['xmax'])), 'xip': []}


def activity_watermark(directory, cfg):
    """Conservative cluster-wide xid8 boundary; this read assigns no XID.

    Never use pg_current_xact_id(), which would allocate the very activity being
    measured. Background/locking transactions can block rollback conservatively.
    """
    try:
        value = json.loads(read_owner(directory, cfg,
            "SELECT json_build_object('xmax',pg_snapshot_xmax(s)::text,'xip',"
            "ARRAY(SELECT pg_snapshot_xip(s)::text)) FROM (SELECT pg_current_snapshot() s) q"))
    except Exception:
        raise SwitchError('candidate_activity_read_unconfirmed') from None
    return _safe_activity(value)


def require_unchanged_activity(directory, cfg, baseline):
    if baseline is None:
        raise SwitchError('candidate_activity_baseline_missing')
    baseline = _safe_activity(baseline)
    current = _safe_activity(activity_watermark(directory, cfg))
    if current != baseline:
        raise SwitchError('candidate_activity_changed')
    return current


def atomic_bytes(path, content):
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('xb') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def switch(source, pointer, *, hook=None):
    initial = validate(source, pointer)
    source, pointer = initial[:2]
    with profile_lock(pointer):
        current = validate(source, pointer)
        if current[3:] != initial[3:]:
            raise SwitchError('source_changed_before_lock')
        source, pointer, cfg, cfg_bytes, pointer_bytes, source_artifacts = current
        source_files = [source / 'manual-qa.json', source / 'lab.json',
                        source / cfg['database'] / 'credentials.json', source / cfg['database'] / 'owner.pgpass',
                        *(source / name for name in PRIVATE_FILES)]
        source_hashes = {str(path): sha256(checked_path(path)) for path in source_files}
        qa = qa_module()
        original_running = qa.running(source)
        if original_running and not qa.ready(source, cfg):
            raise SwitchError('source_supervisor_identity_unconfirmed')
        journal = source / ('schema-switch-' + uuid.uuid4().hex + '.json')
        state = dict(state='validated', originalRunning=original_running, sourceDirectory=str(source),
                     sourceConfigSha256=sha256(source / 'manual-qa.json'), sourcePointerSha256=sha256(pointer),
                     sourceArtifacts=source_artifacts, sourcePrivateInputHashes=source_hashes, activated=False)
        save(journal, state)
        result = SwitchResult(source, None, journal, 'validated')
        candidate, swapped, candidate_pointer, prepared_snapshot = None, False, None, None
        candidate_cfg_bytes = None
        preparation_failed = False
        activity_baseline = None

        def checkpoint(name):
            result.state = state['state'] = name
            save(journal, state)
            if hook:
                hook(name, result)

        def source_unchanged():
            checked_path(source / 'data')
            if (source_hashes != {str(path): sha256(checked_path(path)) for path in source_files} or
                    source.joinpath('manual-qa.json').read_bytes() != cfg_bytes or
                    artifacts(checked_path(cfg.get('artifactDirectory', source)) / 'server',
                              checked_path(cfg.get('artifactDirectory', source)) / 'frontend', SOURCE_DLL, SOURCE_BUNDLE) != source_artifacts):
                raise SwitchError('source_recovery_identity_changed')

        try:
            stop_application(source, cfg)
            checkpoint('source_stopped')
            qa.control(source, 'start')
            try:
                candidate = result.candidate = prepare(source)
            except CandidateError as error:
                preparation_failed = True
                candidate = result.candidate = error.candidate
                if candidate:
                    state['candidateDirectory'] = str(candidate.lab.directory)
                raise
            state['candidateDirectory'] = str(candidate.lab.directory)
            prepared_snapshot = json.loads(candidate.journal.read_text(encoding='utf-8'))['candidateSnapshot']
            candidate_cfg_bytes = (candidate.lab.directory / 'manual-qa.json').read_bytes()
            candidate.close()
            qa.control(source, 'stop')
            # Capture once, after all preparation writes have committed and the
            # owning cluster has stopped cleanly, before any preview/serving.
            qa.control(candidate.lab.directory, 'start')
            try:
                activity_baseline = activity_watermark(candidate.lab.directory, candidate.cfg)
            finally:
                qa.control(candidate.lab.directory, 'stop')
            state['activityBaseline'] = activity_baseline
            checkpoint('prepared')
            # Validate the real supervisor/server pair on a new, unpublished
            # loopback port before switching the stable URL/pointer.
            temp_cfg = dict(candidate.cfg, webPort=free_port())
            while temp_cfg['webPort'] in (cfg['webPort'], cfg['pgPort'], candidate.cfg['pgPort']):
                temp_cfg['webPort'] = free_port()
            atomic_bytes(candidate.lab.directory / 'manual-qa.json', json.dumps(temp_cfg).encode('utf-8'))
            try:
                process = start_supervisor(candidate.lab.directory, temp_cfg)
                stop_application(candidate.lab.directory, temp_cfg)
                process.wait(timeout=30)
            finally:
                atomic_bytes(candidate.lab.directory / 'manual-qa.json', candidate_cfg_bytes)
            qa.control(candidate.lab.directory, 'start')
            try:
                require_unchanged_activity(candidate.lab.directory, candidate.cfg, activity_baseline)
                if snapshot(lambda sql: read_owner(candidate.lab.directory, candidate.cfg, sql)) != prepared_snapshot:
                    raise SwitchError('candidate_changed_before_commit')
                require_unchanged_activity(candidate.lab.directory, candidate.cfg, activity_baseline)
            finally:
                qa.control(candidate.lab.directory, 'stop')
            source_unchanged()
            if pointer.read_bytes() != pointer_bytes:
                raise SwitchError('pointer_changed_before_commit')
            if (candidate.lab.directory / 'manual-qa.json').read_bytes() != candidate_cfg_bytes:
                raise SwitchError('candidate_config_changed_before_commit')
            artifacts(candidate.lab.directory / 'server', candidate.lab.directory / 'frontend', CANDIDATE_DLL, CANDIDATE_BUNDLE)
            checkpoint('before_pointer')
            candidate_pointer = json.dumps({'directory': str(candidate.lab.directory.resolve())}).encode('utf-8')
            atomic_bytes(pointer, candidate_pointer)
            swapped = True
            checkpoint('after_pointer')
            start_supervisor(candidate.lab.directory, candidate.cfg)
            checkpoint('after_start')
            state['activated'] = True
            checkpoint('committed')
            return result
        except Exception:
            rollback_safe = False
            candidate_quiet = True
            try:
                if candidate:
                    try:
                        if preparation_failed:
                            # prepare30 may retain an unfinished Lab without a
                            # usable manual-qa config. Its own close must confirm
                            # cleanup before any source resumption is considered.
                            candidate.close()
                            if candidate.lab.data.exists() and pg_running(candidate.lab.directory):
                                raise SwitchError('unfinished_candidate_stop_unconfirmed')
                        else:
                            # Candidate may own the stable web port. Stop it first.
                            stop_application(candidate.lab.directory, candidate.cfg)
                            if candidate_cfg_bytes is None or (candidate.lab.directory / 'manual-qa.json').read_bytes() != candidate_cfg_bytes:
                                raise SwitchError('candidate_recovery_identity_changed')
                            artifacts(candidate.lab.directory / 'server', candidate.lab.directory / 'frontend', CANDIDATE_DLL, CANDIDATE_BUNDLE)
                            qa.control(candidate.lab.directory, 'start')
                            try:
                                require_unchanged_activity(candidate.lab.directory, candidate.cfg, activity_baseline)
                                candidate_unchanged = prepared_snapshot is not None and snapshot(
                                    lambda sql: read_owner(candidate.lab.directory, candidate.cfg, sql)) == prepared_snapshot
                                require_unchanged_activity(candidate.lab.directory, candidate.cfg, activity_baseline)
                            finally:
                                qa.control(candidate.lab.directory, 'stop')
                            if not candidate_unchanged:
                                raise SwitchError('candidate_has_later_writes')
                    except Exception:
                        candidate_quiet = False
                        raise
                # Even an uncertain candidate cleanup must not skip attempting
                # to stop the identified source cluster we started for backup.
                stop_application(source, cfg)
                source_unchanged()
                expected_pointer = candidate_pointer if swapped else pointer_bytes
                if pointer.read_bytes() != expected_pointer:
                    raise SwitchError('pointer_recovery_identity_changed')
                if swapped:
                    atomic_bytes(pointer, pointer_bytes)
                if original_running:
                    start_supervisor(source, cfg)
                rollback_safe = True
            except Exception:
                if not candidate_quiet:
                    try:
                        stop_application(source, cfg)
                    except Exception:
                        pass
                # Preserve both branches and the existing pointer. No file-only
                # rollback, inferred success, or foreign process termination.
                pass
            state['activated'] = False
            state['candidateCleanupConfirmed'] = candidate_quiet
            result.state = state['state'] = 'rolled_back' if rollback_safe else 'recovery_required'
            try:
                save(journal, state)
            except Exception:
                raise SwitchError('recovery_journal_unconfirmed', result) from None
            raise SwitchError(result.state, result) from None


def worker(directory, supervise=False):
    directory = checked_path(directory)
    if directory.parent != (ROOT / '.local/labs').resolve() or not directory.name.startswith('manual-qa-rc9-'):
        raise SwitchError('worker_identity_invalid')
    cfg = json.loads((directory / 'manual-qa.json').read_text(encoding='utf-8'))
    if cfg.get('directory') != str(directory) or cfg.get('profile') != 'rc9' or cfg.get('host') != '127.0.0.1':
        raise SwitchError('worker_identity_invalid')
    if supervise:
        with (directory / 'switch-worker.log').open('ab') as output:
            result = run_isolated([sys.executable, '-B', str(Path(__file__).resolve()), '_worker',
                '--profile', 'rc9', '--source', str(directory)], cwd=ROOT, stdout=output, stderr=output)
        if result.returncode:
            raise SwitchError('worker_failed')
    else:
        qa_module().serve(directory, cfg)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('switch', '_supervise', '_worker'))
    parser.add_argument('--profile', choices=('rc9',), required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--pointer', type=Path)
    args = parser.parse_args()
    try:
        if args.action != 'switch':
            worker(args.source, args.action == '_supervise')
        else:
            if args.pointer is None:
                raise SwitchError('explicit_pointer_required')
            result = switch(args.source, args.pointer)
            print(json.dumps({'state': result.state, 'activated': True}))
        return 0
    except Exception as error:
        code = error.code if isinstance(error, SwitchError) else 'switch_failed'
        print(json.dumps({'state': code, 'activated': False}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
