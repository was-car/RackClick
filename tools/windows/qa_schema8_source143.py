"""Closed source128/schema7 and target143/schema8 contracts. Validation only.

No CLI overrides for manifests, digests, schemas or distributions. Source reads
are inherited READ ONLY helpers; constructing this object never starts PG.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import Database, toolchain
from pg_lab_recovery import sha256
from qa_schema5_candidate import checked_path
from qa_schema6_source import Source4, PRIVATE_FILES, artifact_manifest, app_stopped
from qa_schema6_real_candidate import history

SOURCE_MANIFEST = ROOT / 'evidence/s1-20261017/quince-tandas-114-128/CANDIDATA128.json'
SOURCE_SHA256 = 'e02d3e490863b2dff14b01f9ca0f4c581e8cd87cd76d9a1ae36563ede3ac68bd'
TARGET_MANIFEST = ROOT / 'evidence/s1-20261017/quince-tandas-129-143/CANDIDATA143-FINAL02.json'
# Set only to the coordinator's frozen public manifest SHA after its review.
TARGET143 = ('evidence/s1-20261017/quince-tandas-129-143/CANDIDATA143-FINAL02.json', '734bc6efd781c385138ab3162d70a08c3ea92b621e6ed9145f58106790ea17c1')
NEW_TABLES = frozenset(('user_catalog_favorites', 'user_catalog_favorite',
                        'user_catalog_favorite_operation'))


class Schema8Error(RuntimeError):
    def __init__(self, code, result=None):
        super().__init__(code)
        self.code, self.result = code, result


@dataclass(frozen=True)
class Distribution143:
    schema: int
    server: Path
    frontend: Path
    expected: dict
    manifest: Path

    def validate(self):
        if self.schema == 7:
            path, pin = SOURCE_MANIFEST, SOURCE_SHA256
        elif self.schema == 8:
            path, pin = target_pin()
        else:
            raise Schema8Error('only_closed_schema7_to8_supported')
        if not isinstance(pin, str) or not re.fullmatch('[0-9a-f]{64}', pin):
            raise Schema8Error('target143_pin_pending')
        if self.manifest != path or sha256(checked_path(path)) != pin:
            raise Schema8Error('closed_manifest_not_approved')
        value = json.loads(path.read_text(encoding='utf-8'))
        if self.schema == 8 and value.get('schema') != 8:
            raise Schema8Error('target143_manifest_schema_differs')
        if (self.server != checked_path(ROOT / Path(value['serverDll']).parent) or
                self.frontend != checked_path(ROOT / value['frontend']) or
                self.expected != value['distributions']):
            raise Schema8Error('closed_distribution_identity_changed')
        if not self.server.is_relative_to(ROOT / '.local/candidates') or not self.frontend.is_relative_to(ROOT / '.local/candidates'):
            raise Schema8Error('frozen_candidate_distribution_required')
        actual = {'server': artifact_manifest(self.server), 'frontend': artifact_manifest(self.frontend)}
        if actual != self.expected:
            raise Schema8Error('complete_closed_distribution_differs')
        sqls = sorted(n for n in actual['server'] if n.startswith('database/'))
        if (len(sqls) != self.schema or any(not re.fullmatch(r'database/[0-9]{3}-[a-z0-9-]+\.sql', n) for n in sqls) or
                [int(Path(n).name[:3]) for n in sqls] != list(range(1, self.schema + 1))):
            raise Schema8Error('closed_sql_sequence_differs')
        if self.schema == 8:
            old = load_source().expected
            if any(actual['server'].get(n) != v for n, v in old['server'].items() if n.startswith('database/')):
                raise Schema8Error('historical_sql001_007_changed')
            for name in ('Npgsql.dll', 'RackClick.Server.deps.json', 'RackClick.Server.runtimeconfig.json'):
                if actual['server'].get(name) != old['server'].get(name):
                    raise Schema8Error('dependency_or_runtime_pin_changed')
            if actual['frontend'].get('app.css') != old['frontend'].get('app.css'):
                raise Schema8Error('approved_css_changed')
        return actual


def _load(schema, path, pin):
    if not isinstance(pin, str) or not re.fullmatch('[0-9a-f]{64}', pin):
        raise Schema8Error('target143_pin_pending')
    if sha256(checked_path(path)) != pin:
        raise Schema8Error('closed_manifest_not_approved')
    value = json.loads(path.read_text(encoding='utf-8'))
    distribution = Distribution143(schema, checked_path(ROOT / Path(value['serverDll']).parent),
        checked_path(ROOT / value['frontend']), value['distributions'], path)
    distribution.validate()
    return distribution


def load_source():
    return _load(7, SOURCE_MANIFEST, SOURCE_SHA256)


def load_target():
    path, pin = target_pin()
    return _load(8, path, pin)


def target_pin():
    if (not isinstance(TARGET143, tuple) or len(TARGET143) != 2 or
            TARGET143[0] != TARGET_MANIFEST.relative_to(ROOT).as_posix()):
        raise Schema8Error('target143_pin_pending')
    return TARGET_MANIFEST, TARGET143[1]


class Source128(Source4):
    """Reuse only read-only SQL/cluster methods, with a separate closed identity.

    selected is used solely to validate the exact prepared8 pointer on rollback;
    it never permits a different source distribution or a different profile.
    """
    def __init__(self, directory, pointer, *, real=False, selected=None):
        try:
            self.directory, self.pointer = checked_path(directory), checked_path(pointer)
            if (self.directory.parent != ROOT / '.local/labs' or
                    not re.fullmatch(r'manual-qa-rc9-schema7-[0-9a-f]{32}', self.directory.name)):
                raise Schema8Error('source128_directory_invalid')
            allowed = ROOT / '.local/qa-rc9/current.json' if real else self.directory / 'schema8-home/current.json'
            if self.pointer != allowed:
                raise Schema8Error('explicit_source128_profile_required')
            self.real = real
            self.pointer_bytes = self.pointer.read_bytes()
            expected = self.directory if selected is None else checked_candidate_directory(selected)
            if json.loads(self.pointer_bytes) != {'directory': str(expected)}:
                raise Schema8Error('source128_pointer_differs')
            cfg_path = checked_path(self.directory / 'manual-qa.json')
            self.config_bytes = cfg_path.read_bytes()
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
                raise Schema8Error('source128_configuration_invalid')
            rows = [r for r in m['databases'] if r['name'] == c.get('database') and r['label'] == 'manual-qa-rc9']
            if len(rows) != 1:
                raise Schema8Error('source128_database_membership_invalid')
            self.db = read_database(self.directory, rows[0], c['pgPort'])
            if c['connection'] != self.db.connection(c['pgPort']):
                raise Schema8Error('source128_private_connection_invalid')
            self.baseline = load_source()
            self.art = checked_path(c.get('artifactDirectory', self.directory))
            if self.art != self.directory and self.art.parent != checked_path(self.directory / 'versions'):
                raise Schema8Error('source128_artifact_directory_invalid')
            if (c.get('dllSha256') != self.baseline.expected['server']['RackClick.Server.dll'] or
                    c.get('bundleSha256') != self.baseline.expected['frontend']['app.js'] or
                    self.artifacts() != self.baseline.expected):
                raise Schema8Error('source128_complete_pair_differs')
            checked_path(self.directory / 'data')
            self.pg_bin = toolchain()['postgresql'].parent
            self.admin_passfile = checked_path(self.directory / 'admin.pgpass')
            admin = self.admin_passfile.read_text(encoding='utf-8').splitlines()
            if len(admin) != 1 or not admin[0].startswith(f'127.0.0.1:{c["pgPort"]}:*:rc_lab_admin:') or not admin[0].split(':', 4)[-1]:
                raise Schema8Error('source128_admin_passfile_invalid')
            self.inputs = [cfg_path, self.directory / 'lab.json', self.db.directory / 'credentials.json',
                           self.db.directory / 'owner.pgpass', self.admin_passfile]
            self.inputs += [self.directory / n for n in PRIVATE_FILES]
            self.hashes = {p.relative_to(self.directory).as_posix(): sha256(checked_path(p)) for p in self.inputs}
            app_stopped(self.directory, c['webPort'])
        except Schema8Error:
            raise
        except Exception:
            raise Schema8Error('source128_validation_failed') from None

    def check_schema7(self):
        self.check_cluster_identity()
        if self.sql('SELECT current_database();SELECT current_user;SHOW port') != f'{self.db.name}\n{self.db.owner}\n{self.cfg["pgPort"]}':
            raise Schema8Error('source128_running_identity_differs')
        return history(self.sql, self.art / 'server', 7)

    def unchanged(self, *, pointer=True, quiet=True):
        if {p.relative_to(self.directory).as_posix(): sha256(checked_path(p)) for p in self.inputs} != self.hashes:
            raise Schema8Error('source128_immutable_inputs_changed')
        if self.artifacts() != self.baseline.expected:
            raise Schema8Error('source128_artifacts_changed')
        if pointer and self.pointer.read_bytes() != self.pointer_bytes:
            raise Schema8Error('source128_pointer_changed')
        if quiet:
            app_stopped(self.directory, self.cfg['webPort'])


def checked_candidate_directory(directory):
    directory = checked_path(directory)
    if (directory.parent != ROOT / '.local/labs' or
            not re.fullmatch(r'manual-qa-rc9-schema8-[0-9a-f]{32}', directory.name)):
        raise Schema8Error('candidate143_directory_invalid')
    return directory


def read_database(directory, row, port):
    name = row['name']
    if (not re.fullmatch(r'rc_[0-9a-f]{12}', name) or row['owner'] != 'rc_m_' + name[3:] or
            row['runtime'] != 'rc_a_' + name[3:]):
        raise Schema8Error('database143_role_identity_invalid')
    private = checked_path(directory / name)
    cred = json.loads(checked_path(private / 'credentials.json').read_text(encoding='utf-8'))
    db = Database(name, row['owner'], cred['ownerPassword'], row['runtime'], cred['runtimePassword'], private)
    if (not db.owner_password or not db.runtime_password or
            cred != dict(database=name, owner=db.owner, ownerPassword=db.owner_password,
                         runtime=db.runtime, runtimePassword=db.runtime_password) or
            checked_path(private / 'owner.pgpass').read_text(encoding='utf-8') !=
            f'127.0.0.1:{port}:{name}:{db.owner}:{db.owner_password}\n'):
        raise Schema8Error('database143_credentials_invalid')
    return db
