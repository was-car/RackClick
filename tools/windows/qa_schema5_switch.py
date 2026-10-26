"""Synthetic Lab-only schema4 ->5/6 selection coordinator; never a QA updater.

Consumes an already prepared53 copy. No preparation, migration, existing profile,
supervisor/service control, stable URL or external cluster is accepted here.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import Lab
from pg_lab_recovery import LabRecovery, sha256
from qa_schema5_candidate import PreparedCopy, checked_path, history, snapshot, sql_read


class SwitchError(RuntimeError):
    def __init__(self, code, result=None):
        super().__init__(code)
        self.code, self.result = code, result


def atomic_bytes(path, content):
    checked_path(path)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('xb') as output:
            output.write(content); output.flush(); os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save(path, value):
    atomic_bytes(path, (json.dumps(value, indent=2) + '\n').encode('utf-8'))


def quiet(lab, source, prepared):
    names = {source.name, prepared.database.name, prepared.recovered.name}
    if any(s.database.name in names and s.process.poll() is None for s in lab.servers):
        raise SwitchError('fixture_application_active')


def identities(lab, source, prepared):
    # Reject manual/foreign objects before walking or reading private files.
    if (not isinstance(lab, Lab) or lab.directory.name.startswith(('manual-', 'qa-')) or
            not isinstance(prepared, PreparedCopy) or prepared.lab is not lab):
        raise SwitchError('new_synthetic_fixture_required')
    checked_path(lab.directory)
    recovery = LabRecovery(lab)
    for database in (source, prepared.database, prepared.recovered):
        recovery._database(database)
    directory = checked_path(prepared.directory)
    if directory.parent != lab.directory or not directory.name.startswith(f'schema{prepared.candidate.schema}-'):
        raise SwitchError('prepared_directory_invalid')
    if prepared.baseline.schema != 4 or prepared.candidate.schema not in (5, 6):
        raise SwitchError('prepared_pair_invalid')
    for label, distribution in [('baseline4', prepared.baseline), (f'candidate{prepared.candidate.schema}', prepared.candidate)]:
        if (checked_path(distribution.server) != directory / label / 'server' or
                checked_path(distribution.frontend) != directory / label / 'frontend'):
            raise SwitchError('prepared_artifact_path_invalid')
        distribution.validate()
    journal = checked_path(directory / 'preparation-private.json')
    metadata = json.loads(journal.read_text(encoding='utf-8'))
    if (metadata.get('state') != 'prepared' or metadata.get('activated') is not False or
            metadata.get('scope') != 'new-synthetic-lab-only' or
            metadata.get('sourceSchema') != 4 or metadata.get('candidateSchema') != prepared.candidate.schema or
            metadata.get('sourceDatabase') != source.name or metadata.get('database') != prepared.database.name or
            metadata.get('recovered') != prepared.recovered.name):
        raise SwitchError('prepared_identity_invalid')
    paths = [journal]
    for db in (source, prepared.database, prepared.recovered):
        paths += [checked_path(db.directory / name) for name in ('credentials.json', 'owner.pgpass')]
    return metadata, {p.relative_to(lab.directory).as_posix(): sha256(p) for p in paths}


def selection(lab, source, prepared, schema, generation):
    db, distribution = (source, prepared.baseline) if schema == 4 else (prepared.database, prepared.candidate)
    return {'scope': 'synthetic-schema5-switch', 'labId': lab.id, 'generation': generation,
            'schema': schema, 'database': db.name,
            'server': str(distribution.server), 'frontend': str(distribution.frontend)}


def create_profile(lab, source, prepared):
    """New fixture-only profile. Never infer a source from missing pointers."""
    metadata, inputs = identities(lab, source, prepared)
    quiet(lab, source, prepared)
    directory = checked_path(lab.directory / 'switch5-home')
    if directory.exists():
        raise SwitchError('profile_already_exists')
    directory.mkdir()
    generation = uuid.uuid4().hex
    source_selection = selection(lab, source, prepared, 4, generation)
    profile = {'scope': 'synthetic-schema5-switch', 'labId': lab.id, 'generation': generation,
               'preparedDirectory': str(prepared.directory), 'sourceSelection': source_selection,
               'privateInputHashes': inputs}
    save(directory / 'profile.json', profile)
    save(directory / 'current.json', source_selection)
    return directory / 'current.json'


def validate_profile(lab, source, prepared, pointer):
    pointer = checked_path(pointer)
    if pointer != lab.directory / 'switch5-home/current.json' or not pointer.is_file():
        raise SwitchError('explicit_fixture_pointer_required')
    profile_path = checked_path(pointer.parent / 'profile.json')
    profile_bytes, pointer_bytes = profile_path.read_bytes(), pointer.read_bytes()
    profile = json.loads(profile_bytes)
    metadata, inputs = identities(lab, source, prepared)
    if (profile.get('scope') != 'synthetic-schema5-switch' or profile.get('labId') != lab.id or
            profile.get('preparedDirectory') != str(prepared.directory) or
            profile.get('privateInputHashes') != inputs or
            profile.get('sourceSelection') != selection(lab, source, prepared, 4, profile.get('generation')) or
            json.loads(pointer_bytes) != profile['sourceSelection']):
        raise SwitchError('profile_source_identity_changed')
    return profile, profile_bytes, pointer_bytes, metadata


@contextmanager
def profile_lock(lab, pointer):
    pointer = checked_path(pointer)
    if pointer != lab.directory / 'switch5-home/current.json':
        raise SwitchError('explicit_fixture_pointer_required')
    lock_path = checked_path(pointer.parent / 'control.lock')
    with lock_path.open('a+b') as lock:
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise SwitchError('profile_busy') from None
        try:
            yield
        finally:
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def safe_activity(value):
    if (not isinstance(value, dict) or not isinstance(value.get('xmax'), str) or
            not value['xmax'].isascii() or not value['xmax'].isdigit() or
            not 0 < int(value['xmax']) < 2**64 or value.get('xip') != []):
        raise SwitchError('activity_unconfirmed')
    return {'xmax': str(int(value['xmax'])), 'xip': []}


def activity_watermark(lab, database):
    """Read-only xid8 boundary for this cluster; never allocate an XID to measure."""
    try:
        value = json.loads(sql_read(lab, database,
            "SELECT json_build_object('xmax',pg_snapshot_xmax(s)::text,'xip',"
            "ARRAY(SELECT pg_snapshot_xip(s)::text)) FROM (SELECT pg_current_snapshot() s) q"))
        return safe_activity(value)
    except Exception:
        raise SwitchError('activity_unconfirmed') from None


def require_unchanged_activity(lab, database, baseline):
    if baseline is None:
        raise SwitchError('activity_baseline_missing')
    if activity_watermark(lab, database) != safe_activity(baseline):
        raise SwitchError('activity_changed')


def unchanged_rows(lab, source, prepared, metadata):
    if (snapshot(lab, source) != metadata['sourceSnapshot'] or
            snapshot(lab, prepared.recovered) != metadata['sourceSnapshot'] or
            snapshot(lab, prepared.database) != metadata['candidateSnapshot']):
        raise SwitchError('fixture_rows_changed')
    old = history(lab, source, prepared.baseline)
    if (history(lab, prepared.recovered, prepared.baseline) != old or
            history(lab, prepared.database, prepared.candidate)[:4] != old):
        raise SwitchError('fixture_history_changed')


@dataclass
class SwitchResult:
    pointer: Path
    journal: Path
    prepared: object
    state: str = 'validated'
    server: object = None


def switch(lab, source, prepared, pointer, *, hook=None):
    """Select prepared5/6, or restore source4 only with proof of no later activity.

    Source starts stopped and stays stopped. Success returns our running5 handle
    on a new temporary loopback URL; caller closes its Lab. No real QA profile or
    supervisor/stable-port switch is implemented. Hooks are synthetic test faults.
    """
    try:
        initial = validate_profile(lab, source, prepared, pointer)
        pointer = checked_path(pointer)
        with profile_lock(lab, pointer):
            profile, profile_bytes, before_pointer, metadata = validate_profile(lab, source, prepared, pointer)
            if (profile_bytes, before_pointer) != initial[1:3]:
                raise SwitchError('profile_changed_before_lock')
            quiet(lab, source, prepared)
            unchanged_rows(lab, source, prepared, metadata)
            # Preparation writes have already committed; capture ONCE before any serving.
            baseline = activity_watermark(lab, prepared.database)
            journal = pointer.parent / ('selection-' + uuid.uuid4().hex + '.json')
            result = SwitchResult(pointer, journal, prepared)
            state = {'state': 'validated', 'scope': 'synthetic-schema5-switch', 'activated': False,
                     'utc': datetime.now(timezone.utc).isoformat(), 'activityBaseline': baseline,
                     'initialPointerSha256': hashlib.sha256(before_pointer).hexdigest()}
            after_pointer = None
            swapped = False

            def checkpoint(name):
                result.state = state['state'] = name
                save(journal, state)
                if hook: hook(name, result)

            def unchanged_inputs():
                if checked_path(pointer.parent / 'profile.json').read_bytes() != profile_bytes:
                    raise SwitchError('profile_changed')
                _, current = identities(lab, source, prepared)
                if current != profile['privateInputHashes']:
                    raise SwitchError('private_inputs_changed')

            try:
                checkpoint('before_pointer')
                unchanged_inputs()
                quiet(lab, source, prepared)
                require_unchanged_activity(lab, prepared.database, baseline)
                if pointer.read_bytes() != before_pointer:
                    raise SwitchError('pointer_changed_before_selection')
                after_pointer = (json.dumps(selection(lab, source, prepared, prepared.candidate.schema, profile['generation']), indent=2) + '\n').encode('utf-8')
                atomic_bytes(pointer, after_pointer)
                swapped = True
                checkpoint('after_pointer')
                result.server = lab.start_server(prepared.database, dll=prepared.candidate.dll,
                                                 frontend=prepared.candidate.frontend)
                if result.server.request('GET', '/health/ready').status != 200:
                    raise SwitchError('candidate_not_ready')
                response = result.server.request('GET', '/app.js')
                if response.status != 200 or hashlib.sha256(response.body).hexdigest() != prepared.candidate.expected['frontend']['app.js']:
                    raise SwitchError('candidate_frontend_differs')
                checkpoint('after_start')
                unchanged_inputs()
                require_unchanged_activity(lab, prepared.database, baseline)
                if pointer.read_bytes() != after_pointer:
                    raise SwitchError('pointer_changed_after_selection')
                state['activated'] = True
                checkpoint('committed')
                return result
            except Exception as failure:
                state['failureCode'] = failure.code if isinstance(failure, SwitchError) else 'internal_or_synthetic_failure'
                rollback_safe, quiet_confirmed = False, False
                try:
                    if result.server:
                        result.server.close()
                        if result.server.process.poll() is None:
                            raise SwitchError('candidate_stop_unconfirmed')
                    quiet(lab, source, prepared)
                    quiet_confirmed = True
                    unchanged_inputs()
                    require_unchanged_activity(lab, prepared.database, baseline)
                    unchanged_rows(lab, source, prepared, metadata)
                    require_unchanged_activity(lab, prepared.database, baseline)
                    if pointer.read_bytes() != (after_pointer if swapped else before_pointer):
                        raise SwitchError('pointer_recovery_identity_changed')
                    if swapped: atomic_bytes(pointer, before_pointer)
                    if pointer.read_bytes() != before_pointer:
                        raise SwitchError('pointer_recovery_unconfirmed')
                    rollback_safe = True
                except Exception as blocker:
                    state['recoveryBlocker'] = blocker.code if isinstance(blocker, SwitchError) else 'recovery_verification_uncertain'
                state['activated'] = False
                state['candidateStopConfirmed'] = quiet_confirmed
                state['pointerBeforeSha256'] = hashlib.sha256(before_pointer).hexdigest()
                state['pointerSelectedSha256'] = hashlib.sha256(after_pointer).hexdigest() if after_pointer else None
                try:
                    state['pointerObservedSha256'] = sha256(checked_path(pointer))
                except Exception:
                    state['pointerObservedSha256'] = None
                result.state = state['state'] = 'rolled_back' if rollback_safe else 'recovery_required'
                try:
                    save(journal, state)
                except Exception:
                    raise SwitchError('recovery_journal_unconfirmed', result) from None
                raise SwitchError(result.state, result) from None
    except SwitchError:
        raise
    except Exception:
        raise SwitchError('fixture_validation_failed') from None
